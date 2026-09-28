"""Post-process GPT imagegen sprite frames into palette-locked 160x144 pixel art.

Subcommands:
  init     Build the locked palette, locked master and 1024x1024 imagegen input
           for one character from its approved 160x144 master frame.
  process  Convert one raw imagegen output into a locked 160x144 frame, align it
           to the previous approved frame, and run consistency QA.

See production/art-direction/imagegen-frame-protocol.md for the workflow.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ART_W, ART_H = 160, 144
BASELINE_Y = 143
INPUT_SIZE = 1024
INPUT_SCALE = 6
INPUT_ORIGIN = ((INPUT_SIZE - ART_W * INPUT_SCALE) // 2, (INPUT_SIZE - ART_H * INPUT_SCALE) // 2)
KEY_RGB = (255, 0, 255)
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_ROOT = REPO_ROOT / "assets" / "references" / "imagegen-inputs"


# ---------------------------------------------------------------- colour space

def srgb_to_oklab(rgb: np.ndarray) -> np.ndarray:
    """Convert uint8/float sRGB (..., 3) to OKLab (..., 3)."""
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    lms = c @ np.array([
        [0.4122214708, 0.2119034982, 0.0883024619],
        [0.5363325363, 0.6806995451, 0.2817188376],
        [0.0514459929, 0.1073969566, 0.6299787005],
    ])
    lms = np.cbrt(lms)
    return lms @ np.array([
        [0.2104542553, 1.9779984951, 0.0259040371],
        [0.7936177850, -2.4285922050, 0.7827717662],
        [-0.0040720468, 0.4505937099, -0.8086757660],
    ])


def nearest_palette_index(lab: np.ndarray, palette_lab: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return nearest palette index and OKLab distance for each (..., 3) colour."""
    flat = lab.reshape(-1, 3)
    d = np.linalg.norm(flat[:, None, :] - palette_lab[None, :, :], axis=2)
    idx = d.argmin(axis=1)
    return idx.reshape(lab.shape[:-1]), d[np.arange(len(flat)), idx].reshape(lab.shape[:-1])


# ------------------------------------------------------------------- palette

def kmeans(points: np.ndarray, k: int, seed: int = 7, iterations: int = 40) -> np.ndarray:
    """Deterministic k-means++ on (n, 3) points; returns (k', 3) centres."""
    k = min(k, len(np.unique(points, axis=0)))
    rng = np.random.default_rng(seed)
    centres = [points[rng.integers(len(points))]]
    for _ in range(1, k):
        d = np.min(np.linalg.norm(points[:, None] - np.array(centres)[None], axis=2), axis=1) ** 2
        if d.sum() == 0:
            break
        centres.append(points[rng.choice(len(points), p=d / d.sum())])
    centres = np.array(centres)
    for _ in range(iterations):
        labels = np.linalg.norm(points[:, None] - centres[None], axis=2).argmin(axis=1)
        updated = np.array([points[labels == i].mean(axis=0) if np.any(labels == i) else centres[i]
                            for i in range(len(centres))])
        if np.allclose(updated, centres):
            break
        centres = updated
    return centres


def build_palette(master: Image.Image, colors: int, accent_threshold: float, accent_colors: int) -> np.ndarray:
    """Build an sRGB palette: k-means body colours plus protected small accents
    (eyes, ribbons) that a global quantiser would otherwise merge away."""
    rgba = np.asarray(master.convert("RGBA"))
    opaque = rgba[..., 3] >= 128
    rgb = rgba[..., :3][opaque].astype(np.float64)
    lab = srgb_to_oklab(rgb)
    centres = kmeans(lab, colors)
    _, dist = nearest_palette_index(lab, centres)
    outliers = lab[dist > accent_threshold]
    if len(outliers) >= 2:
        centres = np.vstack([centres, kmeans(outliers, accent_colors, seed=11)])
    # Replace each OKLab centre with the closest real master colour so the
    # palette only contains colours the artist actually used.
    idx, _ = nearest_palette_index(centres, lab)
    palette = np.unique(rgb[idx.reshape(-1)].astype(np.uint8), axis=0)
    return palette


def apply_palette(rgb: np.ndarray, alpha: np.ndarray, palette: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Map opaque pixels to palette. Returns RGBA, index map (-1 = clear), mean error."""
    idx, err = nearest_palette_index(srgb_to_oklab(rgb), srgb_to_oklab(palette))
    idx = np.where(alpha, idx, -1)
    out = np.zeros(rgb.shape[:2] + (4,), np.uint8)
    out[alpha, :3] = palette[idx[alpha]]
    out[alpha, 3] = 255
    return out, idx, float(err[alpha].mean()) if alpha.any() else 0.0


# ------------------------------------------------------------ io helpers

def to_input_canvas(frame: Image.Image) -> Image.Image:
    """Place a 160x144 RGBA frame on the 1024x1024 magenta imagegen canvas at 6x."""
    art = Image.new("RGBA", (ART_W, ART_H), KEY_RGB + (255,))
    art.alpha_composite(frame.convert("RGBA"))
    canvas = Image.new("RGB", (INPUT_SIZE, INPUT_SIZE), KEY_RGB)
    canvas.paste(art.convert("RGB").resize((ART_W * INPUT_SCALE, ART_H * INPUT_SCALE), Image.NEAREST), INPUT_ORIGIN)
    return canvas


def load_palette(path: Path) -> np.ndarray:
    data = json.loads(path.read_text(encoding="utf-8"))
    return np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in data["colors"]], np.uint8)


def character_dir(root: Path, character: str) -> Path:
    return root / character


# --------------------------------------------------------- raw → art grid

def key_mask(rgb: np.ndarray) -> np.ndarray:
    """True where a raw pixel is the magenta background (including soft fringe)."""
    r, g, b = (rgb[..., i].astype(np.int16) for i in range(3))
    pure = (r > 150) & (b > 150) & (g < 120) & (np.abs(r - b) < 90)
    # Resampled edges blend magenta into the sprite (e.g. black hair -> dark purple).
    fringe = (r - g > 60) & (b - g > 60) & (np.abs(r - b) < 60)
    return pure | fringe


@dataclass
class Grid:
    scale: float
    ox: float
    oy: float


def sample_grid(rgb: np.ndarray, bg: np.ndarray, grid: Grid, window: int) -> tuple[np.ndarray, np.ndarray]:
    """Sample every art cell from a central window; returns (rgb, opaque)."""
    h, w = bg.shape
    ys = grid.oy + (np.arange(ART_H) + 0.5) * grid.scale
    xs = grid.ox + (np.arange(ART_W) + 0.5) * grid.scale
    off = np.arange(-window, window + 1)
    yy = np.clip(np.rint(ys[:, None, None, None] + off[None, None, :, None]), 0, h - 1).astype(int)
    xx = np.clip(np.rint(xs[None, :, None, None] + off[None, None, None, :]), 0, w - 1).astype(int)
    yy, xx = np.broadcast_arrays(yy, xx)
    patch_bg = bg[yy, xx].reshape(ART_H, ART_W, -1)
    patch_rgb = rgb[yy, xx].reshape(ART_H, ART_W, -1, 3).astype(np.float64)
    inside = (ys[:, None] >= 0) & (ys[:, None] < h) & (xs[None, :] >= 0) & (xs[None, :] < w)
    opaque = (patch_bg.mean(axis=2) < 0.5) & inside
    masked = np.where(patch_bg[..., None], np.nan, patch_rgb)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        colour = np.nanmedian(masked, axis=2)
    colour = np.nan_to_num(colour, nan=0.0)
    return colour.astype(np.uint8), opaque


def reconstruction_error(rgb: np.ndarray, bg: np.ndarray, grid: Grid) -> float:
    """Downsample on a candidate grid, paint cells back over the raw pixels, and
    measure the error. The true pixel grid reproduces edges best."""
    h, w = bg.shape
    ys, xs = np.where(~bg)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    cyc = np.clip(np.rint(grid.oy + (np.arange(ART_H) + 0.5) * grid.scale).astype(int), 0, h - 1)
    cxc = np.clip(np.rint(grid.ox + (np.arange(ART_W) + 0.5) * grid.scale).astype(int), 0, w - 1)
    colour = rgb[cyc[:, None], cxc[None, :]]
    opaque = sample_alpha(bg, grid)
    py =np.floor((np.arange(y0, y1) - grid.oy) / grid.scale).astype(int)
    px = np.floor((np.arange(x0, x1) - grid.ox) / grid.scale).astype(int)
    valid = ((py >= 0) & (py < ART_H))[:, None] & ((px >= 0) & (px < ART_W))[None, :]
    cy, cx = np.clip(py, 0, ART_H - 1)[:, None], np.clip(px, 0, ART_W - 1)[None, :]
    painted = colour[cy, cx].astype(np.float64)
    painted_bg = ~opaque[cy, cx] | ~valid
    raw = rgb[y0:y1, x0:x1].astype(np.float64)
    raw_bg = bg[y0:y1, x0:x1]
    colour_err = np.abs(painted - raw).sum(axis=2)
    err = np.where(painted_bg == raw_bg, np.where(raw_bg, 0.0, colour_err), 255.0)
    return float(err.mean())


def refine_phase(rgb: np.ndarray, bg: np.ndarray, grid: Grid, ref_alpha: np.ndarray, weight: np.ndarray,
                 max_dx: int, scale_span: float = 0.14) -> tuple[Grid, int]:
    """Pick the scale and sub-cell phase that best reconstruct the raw image (the true
    pixel grid), then re-fit the x shift. Independent of which parts are present."""
    ys, xs = np.where(~bg)
    cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
    candidates = []
    for s in np.arange(grid.scale - scale_span, grid.scale + scale_span + 0.001, 0.035) if scale_span else [grid.scale]:
        # Keep the sprite centre on the same art cell while the scale changes.
        base_ox = cx - (cx - grid.ox) / grid.scale * s
        base_oy = cy - (cy - grid.oy) / grid.scale * s
        steps = np.linspace(-0.5, 0.5, 6, endpoint=False) * s
        candidates += [Grid(float(s), base_ox + fx, base_oy + fy) for fx in steps for fy in steps]
    best_grid = min(candidates, key=lambda g: reconstruction_error(rgb, bg, g))
    alpha = sample_alpha(bg, best_grid)
    best_dx = max(range(-max_dx, max_dx + 1),
                  key=lambda dx: iou(shift_to_baseline(alpha[..., None], alpha, dx)[1], ref_alpha, weight))
    return best_grid, best_dx


def find_scale(rgb: np.ndarray, bg: np.ndarray, lo: float, hi: float) -> float:
    """Art-pixel size of the raw image from the image alone (best reconstruction),
    so whole-pose changes such as sitting are not judged against a standing reference."""
    ys, xs = np.where(~bg)
    cx, bottom = (xs.min() + xs.max()) / 2, ys.max() + 1

    def best(scales: np.ndarray, phases: int) -> float:
        scored = []
        for s in scales:
            for px in np.linspace(0, s, phases, endpoint=False):
                for py in np.linspace(0, s, phases, endpoint=False):
                    grid = Grid(float(s), cx - ART_W * s / 2 + px, bottom - ART_H * s + py)
                    scored.append((reconstruction_error(rgb, bg, grid), float(s)))
        return min(scored)[1]

    coarse = best(np.arange(lo, hi + 1e-6, 0.1), 3)
    return best(np.arange(coarse - 0.1, coarse + 0.1001, 0.025), 4)


def shift_to_baseline(arr: np.ndarray, alpha: np.ndarray, dx: int, baseline: int = BASELINE_Y) -> tuple[np.ndarray, np.ndarray]:
    """Shift so the lowest opaque row lands on `baseline` and x moves by dx."""
    rows = np.where(alpha.any(axis=1))[0]
    dy = baseline - rows.max() if len(rows) else 0
    out = np.zeros_like(arr)
    out_a = np.zeros_like(alpha)
    src_y = slice(max(0, -dy), min(ART_H, ART_H - dy))
    dst_y = slice(max(0, dy), min(ART_H, ART_H + dy))
    src_x = slice(max(0, -dx), min(ART_W, ART_W - dx))
    dst_x = slice(max(0, dx), min(ART_W, ART_W + dx))
    out[dst_y, dst_x] = arr[src_y, src_x]
    out_a[dst_y, dst_x] = alpha[src_y, src_x]
    return out, out_a


def iou(a: np.ndarray, b: np.ndarray, weight: np.ndarray | None = None) -> float:
    w = np.ones(a.shape) if weight is None else weight
    union = ((a | b) * w).sum()
    return float(((a & b) * w).sum() / union) if union else 1.0


def register(rgb: np.ndarray, bg: np.ndarray, ref_alpha: np.ndarray, ref_rgb: np.ndarray, keep: np.ndarray,
             scale: float | None, max_dx: int, scale_range: tuple[float, float] = (5.4, 6.6)) -> tuple[Grid, int, float]:
    """Find grid scale/phase and horizontal shift that best overlay the reference.

    Scoring counts pixels whose colour matches the reference, not just the
    silhouette, so a missing part (e.g. a dropped weapon) cannot be "covered"
    by picking a larger scale. Horizontal placement is anchored on the head,
    which imagegen rarely drops, instead of the leftmost pixel.
    """
    ys, xs = np.where(~bg)
    if len(ys) == 0:
        raise ValueError("raw image has no foreground after removing the #FF00FF key")
    bottom, top = ys.max() + 1, ys.min()
    head_raw = xs[ys < top + (bottom - top) * 0.3].mean()
    ref_rows, ref_cols = np.where(ref_alpha)
    r_top, r_bottom = ref_rows.min(), ref_rows.max() + 1
    head_ref = ref_cols[ref_rows < r_top + (r_bottom - r_top) * 0.3].mean()
    ref_rgb = ref_rgb.astype(np.int16)
    weight = np.where(keep, 1.0, 0.25)
    h, w = bg.shape

    def search(scales: np.ndarray, best: tuple[Grid, int, float]) -> tuple[Grid, int, float]:
        for s in scales:
            for p in np.linspace(-0.5, 0.5, 5, endpoint=False) * s:
                grid = Grid(float(s), float(head_raw - (head_ref + 0.5) * s + p), float(bottom - ART_H * s + p))
                cy = np.clip(np.rint(grid.oy + (np.arange(ART_H) + 0.5) * s).astype(int), 0, h - 1)
                cx = np.clip(np.rint(grid.ox + (np.arange(ART_W) + 0.5) * s).astype(int), 0, w - 1)
                alpha = sample_alpha(bg, grid)
                if not alpha.any():
                    continue
                colour = rgb[cy[:, None], cx[None, :]].astype(np.int16)
                for dx in range(-max_dx, max_dx + 1):
                    shifted_rgb, shifted = shift_to_baseline(colour, alpha, dx)
                    match = shifted & ref_alpha & (np.abs(shifted_rgb - ref_rgb).sum(axis=2) < 90)
                    union = ((shifted | ref_alpha) * weight).sum()
                    score = float((match * weight).sum() / union) if union else 0.0
                    if score > best[2]:
                        best = (grid, dx, score)
        return best

    best = (Grid(INPUT_SCALE, *INPUT_ORIGIN), 0, -1.0)
    if scale:
        return search(np.array([scale]), best)
    best = search(np.arange(scale_range[0], scale_range[1] + 0.001, 0.1), best)
    return search(np.arange(best[0].scale - 0.1, best[0].scale + 0.101, 0.02), best)


def sample_alpha(bg: np.ndarray, grid: Grid) -> np.ndarray:
    """Fast centre-point opacity sample used during registration."""
    h, w = bg.shape
    ys = np.rint(grid.oy + (np.arange(ART_H) + 0.5) * grid.scale).astype(int)
    xs = np.rint(grid.ox + (np.arange(ART_W) + 0.5) * grid.scale).astype(int)
    inside = ((ys >= 0) & (ys < h))[:, None] & ((xs >= 0) & (xs < w))[None, :]
    return inside & ~bg[np.clip(ys, 0, h - 1)[:, None], np.clip(xs, 0, w - 1)[None, :]]


# ------------------------------------------------------------------- cleanup

def components(alpha: np.ndarray) -> list[list[tuple[int, int]]]:
    seen = np.zeros_like(alpha)
    comps = []
    for y, x in zip(*np.where(alpha)):
        if seen[y, x]:
            continue
        queue, comp = deque([(y, x)]), []
        seen[y, x] = True
        while queue:
            cy, cx = queue.popleft()
            comp.append((cy, cx))
            for ny in range(cy - 1, cy + 2):
                for nx in range(cx - 1, cx + 2):
                    if 0 <= ny < ART_H and 0 <= nx < ART_W and alpha[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((ny, nx))
        comps.append(comp)
    return comps


def shift_array(arr: np.ndarray, dx: int, dy: int, fill) -> np.ndarray:
    out = np.full_like(arr, fill)
    src_y = slice(max(0, -dy), min(arr.shape[0], arr.shape[0] - dy))
    dst_y = slice(max(0, dy), min(arr.shape[0], arr.shape[0] + dy))
    src_x = slice(max(0, -dx), min(arr.shape[1], arr.shape[1] - dx))
    dst_x = slice(max(0, dx), min(arr.shape[1], arr.shape[1] + dx))
    out[dst_y, dst_x] = arr[src_y, src_x]
    return out


def snap_to_reference(new_idx: np.ndarray, ref_idx: np.ndarray, keep: np.ndarray, palette: np.ndarray,
                      tolerance: float, radius: int = 3) -> tuple[int, int]:
    """Integer shift that minimises perceptual changes in the regions that must stay fixed."""
    lab = srgb_to_oklab(palette)
    best, best_cost = (0, 0), None
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            cand = shift_array(new_idx, dx, dy, -1)
            a, r = cand >= 0, ref_idx >= 0
            both = a & r
            dist = np.zeros(cand.shape)
            dist[both] = np.linalg.norm(lab[cand[both]] - lab[ref_idx[both]], axis=1)
            cost = int((((a != r) | (dist > tolerance)) & keep).sum())
            if best_cost is None or cost < best_cost or (cost == best_cost and abs(dx) + abs(dy) < sum(map(abs, best))):
                best, best_cost = (dx, dy), cost
    return best


def remove_specks(alpha: np.ndarray, min_size: int) -> tuple[np.ndarray, int]:
    comps = sorted(components(alpha), key=len, reverse=True)
    out = alpha.copy()
    removed = 0
    for comp in comps[1:]:
        if len(comp) < min_size:
            for y, x in comp:
                out[y, x] = False
            removed += len(comp)
    return out, removed


# ------------------------------------------------------------------------ QA

def parse_regions(values: list[str]) -> np.ndarray:
    """Build a mask of art-pixel regions where change is allowed."""
    allow = np.zeros((ART_H, ART_W), bool)
    for value in values:
        if value == "all":
            allow[:] = True
            continue
        x0, y0, x1, y1 = (int(v) for v in value.split(","))
        allow[max(0, y0):min(ART_H, y1 + 1), max(0, x0):min(ART_W, x1 + 1)] = True
    return allow


def colour_groups(palette: np.ndarray, tolerance: float) -> np.ndarray:
    """Group near-identical palette colours (e.g. three almost-black hair tones)."""
    lab = srgb_to_oklab(palette)
    groups = np.arange(len(palette))
    dist = np.linalg.norm(lab[:, None] - lab[None], axis=2)
    for i in range(len(palette)):
        for j in range(i + 1, len(palette)):
            if dist[i, j] <= tolerance:
                groups[groups == groups[j]] = groups[i]
    return groups


def drift_mask(new_idx: np.ndarray, ref_idx: np.ndarray, palette: np.ndarray, tolerance: float) -> np.ndarray:
    """Pixels with no perceptually matching reference pixel in their 3x3 neighbourhood.
    One-pixel resampling jitter is tolerated; missing or redrawn parts are not."""
    lab = srgb_to_oklab(palette)
    new_a = new_idx >= 0
    matched = np.zeros(new_idx.shape, bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ref = shift_array(ref_idx, dx, dy, -1)
            ref_a = ref >= 0
            both = new_a & ref_a
            dist = np.full(new_idx.shape, np.inf)
            dist[both] = np.linalg.norm(lab[new_idx[both]] - lab[ref[both]], axis=1)
            matched |= (~new_a & ~ref_a) | (dist <= tolerance)
    # A reference pixel that vanished must also count, even if the new pixel is clear nearby.
    lost = np.zeros(new_idx.shape, bool)
    ref_a = ref_idx >= 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            lost |= shift_array(new_idx, dx, dy, -1) >= 0
    return ~matched | (ref_a & ~lost)


def run_qa(new_idx: np.ndarray, ref_idx: np.ndarray, allow: np.ndarray, map_error: float,
           specks_removed: int, limits: argparse.Namespace, palette: np.ndarray, raw_bg: np.ndarray) -> dict:
    new_a, ref_a = new_idx >= 0, ref_idx >= 0
    keep = ~allow
    checks = []

    def check(name: str, ok: bool, detail: str, severity: str = "fail") -> None:
        checks.append({"check": name, "ok": bool(ok), "severity": severity, "detail": detail})

    m = 2
    raw_edge = (~raw_bg[:m]).any() or (~raw_bg[:, :m]).any() or (~raw_bg[:, -m:]).any()
    art_edge = new_a[0, :].any() or new_a[:, 0].any() or new_a[:, -1].any()
    check("not_cropped_by_canvas", not (raw_edge or art_edge),
          "character touches the raw image border (cropped by imagegen)" if raw_edge
          else "opaque pixels touch the 160x144 edge" if art_edge else "inside canvas")

    drift = drift_mask(new_idx, ref_idx, palette, limits.change_tolerance) & keep
    clusters = [c for c in components(drift) if len(c) >= limits.min_drift_cluster]
    changed = sum(len(c) for c in clusters)
    ref_keep_area = max(1, int((ref_a & keep).sum()))
    frac = changed / ref_keep_area
    largest = max((len(c) for c in clusters), default=0)
    check("only_allowed_regions_changed", frac <= limits.max_outside_change,
          f"{changed} px in {len(clusters)} drift clusters outside allowed regions "
          f"({frac:.1%} of kept area, limit {limits.max_outside_change:.0%}; largest cluster {largest} px; "
          f"{int(drift.sum()) - changed} scattered px ignored)")

    groups = colour_groups(palette, limits.group_tolerance)
    ref_groups = np.where(ref_a, groups[np.maximum(ref_idx, 0)], -1)
    new_groups = np.where(new_a, groups[np.maximum(new_idx, 0)], -1)
    lost_parts = []
    for g in np.unique(groups):
        ref_count = int(((ref_groups == g) & keep).sum())
        if ref_count < limits.min_color_pixels:
            continue
        new_count = int(((new_groups == g) & keep).sum())
        if new_count < ref_count * limits.min_color_ratio:
            hex_color = "#%02x%02x%02x" % tuple(palette[g])
            lost_parts.append(f"{hex_color}: {ref_count}->{new_count}")
    check("no_colour_group_lost", not lost_parts,
          "possible missing part: " + ", ".join(lost_parts) if lost_parts else "all colour groups kept")

    area_ratio = new_a.sum() / max(1, ref_a.sum())
    check("area_stable", abs(area_ratio - 1) <= limits.max_area_change,
          f"opaque area ratio {area_ratio:.2f} (limit ±{limits.max_area_change:.0%})",
          "warn" if allow.all() else "fail")

    check("style_close_to_palette", map_error <= limits.max_palette_error,
          f"mean OKLab error {map_error:.3f} (limit {limits.max_palette_error})", "warn")
    check("no_stray_pixels", specks_removed == 0, f"{specks_removed} stray px removed", "warn")

    passed = all(c["ok"] for c in checks if c["severity"] == "fail")
    return {"passed": passed, "checks": checks}


def qa_image(ref: np.ndarray, imagegen: np.ndarray, final: np.ndarray, ref_idx: np.ndarray, new_idx: np.ndarray,
             allow: np.ndarray, palette: np.ndarray, tolerance: float) -> Image.Image:
    s = 4
    bg = (30, 36, 48, 255)
    drift = drift_mask(new_idx, ref_idx, palette, tolerance)
    diff = np.zeros((ART_H, ART_W, 4), np.uint8)
    diff[...] = bg
    new_a, ref_a = new_idx >= 0, ref_idx >= 0
    dim = (imagegen[..., :3].astype(np.float64) * 0.35 + 30).astype(np.uint8)
    diff[new_a, :3] = dim[new_a]
    diff[drift & ref_a & ~new_a] = (255, 60, 60, 255)
    diff[drift & new_a & ~ref_a] = (60, 255, 90, 255)
    diff[drift & new_a & ref_a] = (255, 210, 60, 255)
    labels = ("reference", "imagegen (locked)", "final (composited)", "drift: red lost / green new / yellow recoloured")
    panels = []
    for arr in (ref, imagegen, final, diff):
        panel = Image.new("RGBA", (ART_W, ART_H), bg)
        panel.alpha_composite(Image.fromarray(arr, "RGBA"))
        panels.append(panel.resize((ART_W * s, ART_H * s), Image.NEAREST))
    sheet = Image.new("RGBA", (ART_W * s * len(panels), ART_H * s), bg)
    for i, panel in enumerate(panels):
        sheet.paste(panel, (i * ART_W * s, 0))
    draw = ImageDraw.Draw(sheet)
    ys, xs = np.where(allow)
    if len(ys) and not allow.all():
        for i in range(1, len(panels)):
            offset = i * ART_W * s
            draw.rectangle((offset + xs.min() * s, ys.min() * s, offset + (xs.max() + 1) * s - 1, (ys.max() + 1) * s - 1),
                           outline=(120, 170, 255, 255))
    for i, label in enumerate(labels):
        draw.text((i * ART_W * s + 6, 6), label, fill=(255, 255, 255, 255))
    return sheet


def coordinate_grid(frame: Image.Image, s: int = 6) -> Image.Image:
    """Enlarged frame with a labelled 10-pixel grid for reading --allow coordinates."""
    margin = 28
    sheet = Image.new("RGBA", (ART_W * s + margin, ART_H * s + margin), (30, 36, 48, 255))
    sheet.alpha_composite(frame.convert("RGBA").resize((ART_W * s, ART_H * s), Image.NEAREST), (margin, margin))
    draw = ImageDraw.Draw(sheet)
    for x in range(0, ART_W + 1, 10):
        colour = (255, 255, 255, 110) if x % 50 else (255, 210, 60, 200)
        draw.line((margin + x * s, margin, margin + x * s, margin + ART_H * s), fill=colour)
        draw.text((margin + x * s + 2, 4), str(x), fill=(255, 255, 255, 255))
    for y in range(0, ART_H + 1, 10):
        colour = (255, 255, 255, 110) if y % 50 else (255, 210, 60, 200)
        draw.line((margin, margin + y * s, margin + ART_W * s, margin + y * s), fill=colour)
        draw.text((2, margin + y * s + 2), str(y), fill=(255, 255, 255, 255))
    return sheet


# ------------------------------------------------------------------ commands

def cmd_init(args: argparse.Namespace) -> int:
    master = Image.open(args.source).convert("RGBA")
    if master.size != (ART_W, ART_H):
        raise SystemExit(f"master must be {ART_W}x{ART_H}, got {master.size}")
    palette = build_palette(master, args.colors, args.accent_threshold, args.accent_colors)
    rgba = np.asarray(master)
    alpha = rgba[..., 3] >= 128
    locked, _, err = apply_palette(rgba[..., :3], alpha, palette)
    out_dir = character_dir(Path(args.input_root), args.character)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "palette.json").write_text(json.dumps({
        "character": args.character,
        "source": str(Path(args.source).resolve().relative_to(REPO_ROOT)).replace("\\", "/")
        if Path(args.source).resolve().is_relative_to(REPO_ROOT) else str(args.source),
        "colors": ["#%02x%02x%02x" % tuple(c) for c in palette],
    }, indent=2) + "\n", encoding="utf-8")
    locked_img = Image.fromarray(locked, "RGBA")
    locked_img.save(out_dir / "master_locked.png")
    to_input_canvas(locked_img).save(out_dir / "master_input_1024.png")
    coordinate_grid(locked_img).save(out_dir / "master_grid.png")
    print(f"{args.character}: {len(palette)} colours, mean mapping error {err:.3f} -> {out_dir}")
    return 0


def cmd_process(args: argparse.Namespace) -> int:
    palette_path = Path(args.palette) if args.palette else character_dir(Path(args.input_root), args.character) / "palette.json"
    palette = load_palette(palette_path)
    ref_img = Image.open(args.reference).convert("RGBA")
    if ref_img.size != (ART_W, ART_H):
        raise SystemExit(f"reference must be a processed {ART_W}x{ART_H} frame")
    ref = np.asarray(ref_img)
    ref_alpha = ref[..., 3] >= 128
    _, ref_idx, _ = apply_palette(ref[..., :3], ref_alpha, palette)
    allow = parse_regions(args.allow)

    raw = np.asarray(Image.open(args.raw).convert("RGB"))
    bg = key_mask(raw)
    # Imagegen may return a different canvas size (e.g. 1254 instead of 1024);
    # the art-pixel size scales with it.
    expected_scale = INPUT_SCALE * raw.shape[1] / INPUT_SIZE
    scale_range = (args.scale_range[0] * expected_scale / INPUT_SCALE, args.scale_range[1] * expected_scale / INPUT_SCALE)
    scale = args.scale
    regridded = False
    if not scale:
        detected = find_scale(raw, bg, *scale_range)
        # Whole-pose edits often keep the character's on-canvas size but redraw it on a
        # finer pixel grid. Sampling that grid would enlarge her versus other frames,
        # so fall back to the input scale to keep the character size constant.
        regridded = abs(detected - expected_scale) / expected_scale > 0.06
        scale = expected_scale if regridded else None
    grid, dx, score = register(raw, bg, ref_alpha, ref[..., :3], ~allow, scale, args.max_shift, scale_range)
    grid, dx = refine_phase(raw, bg, grid, ref_alpha, np.where(allow, 0.25, 1.0), args.max_shift,
                            0.0 if regridded or args.scale else 0.14)
    window = max(0, int(grid.scale * 0.25))
    rgb, alpha = sample_grid(raw, bg, grid, window)
    alpha, specks = remove_specks(alpha, args.min_component)
    rgb, alpha = shift_to_baseline(rgb, alpha, dx, args.baseline)
    locked, new_idx, err = apply_palette(rgb, alpha, palette)
    snap = (0, 0)
    if not allow.all():
        snap = snap_to_reference(new_idx, ref_idx, ~allow, palette, args.change_tolerance)
        new_idx = shift_array(new_idx, *snap, -1)
        locked = shift_array(locked, *snap, 0)

    qa = run_qa(new_idx, ref_idx, allow, err, specks, args, palette, bg)
    qa["checks"].append({"check": "pixel_grid_preserved", "ok": not regridded, "severity": "warn",
                         "detail": f"sampled at {grid.scale:.2f} raw px per art pixel (input {expected_scale:.2f}); "
                                   + ("imagegen redrew on a different pixel grid - sampled at the input scale "
                                      "to keep character size; check fine details by eye" if regridded else "grid kept")})
    composite = not allow.all() and not args.no_composite
    final = locked.copy()
    if composite:
        # Outside the change list the previous approved frame is kept verbatim,
        # so imagegen cannot drop or redraw any part it was not asked to change.
        ref_locked, _, _ = apply_palette(ref[..., :3], ref_alpha, palette)
        final = np.where(allow[..., None], locked, ref_locked)
    qa.update({"raw": str(args.raw), "reference": str(args.reference), "composited": composite,
               "registration": {"scale": round(grid.scale, 3), "origin": [round(grid.ox, 1), round(grid.oy, 1)],
                                "shift_x": dx, "overlap": round(score, 3), "snap": list(snap)},
               "allowed_regions": args.allow})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame = Image.fromarray(final, "RGBA")
    frame.save(out.with_suffix(".png"))
    to_input_canvas(frame).save(out.with_name(out.stem + "_next_input.png"))
    qa_image(ref, locked, final, ref_idx, new_idx, allow, palette, args.change_tolerance).save(
        out.with_name(out.stem + "_qa.png"))
    out.with_name(out.stem + "_qa.json").write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")

    status = "PASS" if qa["passed"] else "FAIL"
    print(f"{status} {out.with_suffix('.png')}")
    for c in qa["checks"]:
        mark = "ok " if c["ok"] else ("WARN" if c["severity"] == "warn" else "FAIL")
        print(f"  [{mark}] {c['check']}: {c['detail']}")
    return 0 if qa["passed"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-root", default=str(DEFAULT_INPUT_ROOT))
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="build locked palette/master/imagegen input")
    init.add_argument("--character", required=True)
    init.add_argument("--source", required=True, help="approved 160x144 RGBA master frame")
    init.add_argument("--colors", type=int, default=48)
    init.add_argument("--accent-threshold", type=float, default=0.06)
    init.add_argument("--accent-colors", type=int, default=10)
    init.set_defaults(func=cmd_init)

    proc = sub.add_parser("process", help="lock and QA one raw imagegen frame")
    proc.add_argument("--character", required=True)
    proc.add_argument("--raw", required=True, help="raw imagegen output (magenta background)")
    proc.add_argument("--reference", required=True, help="previous approved processed 160x144 frame")
    proc.add_argument("--out", required=True, help="output path stem, e.g. .../walk/wk1")
    proc.add_argument("--palette")
    proc.add_argument("--allow", action="append", default=[],
                      help="art-pixel region x0,y0,x1,y1 allowed to change (repeatable) or 'all'")
    proc.add_argument("--scale", type=float, help="force art-pixel size in the raw image")
    proc.add_argument("--scale-range", type=float, nargs=2, default=[5.4, 6.6], metavar=("MIN", "MAX"),
                      help="art-pixel sizes to search, for a 1024px output (scaled with the actual output width)")
    proc.add_argument("--baseline", type=int, default=BASELINE_Y,
                      help="row the lowest opaque pixel lands on (use the feet row when a prop such as a sword tip hangs lower)")
    proc.add_argument("--max-shift", type=int, default=12)
    proc.add_argument("--min-component", type=int, default=6)
    proc.add_argument("--max-outside-change", type=float, default=0.04)
    proc.add_argument("--change-tolerance", type=float, default=0.05,
                      help="OKLab distance below which two palette colours count as unchanged")
    proc.add_argument("--min-drift-cluster", type=int, default=5,
                      help="connected drifted pixels smaller than this are resampling noise, not a changed part")
    proc.add_argument("--group-tolerance", type=float, default=0.1,
                      help="OKLab distance for merging palette colours into part groups in the lost-part check")
    proc.add_argument("--no-composite", action="store_true",
                      help="keep imagegen pixels outside --allow regions instead of the reference pixels")
    proc.add_argument("--min-color-pixels", type=int, default=12)
    proc.add_argument("--min-color-ratio", type=float, default=0.5)
    proc.add_argument("--max-area-change", type=float, default=0.15)
    proc.add_argument("--max-palette-error", type=float, default=0.05)
    proc.set_defaults(func=cmd_process)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
