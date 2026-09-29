#!/usr/bin/env python3
"""Painted-legs walk generator (approach "painted-legs").

Upper body = locked master idle/k1.png with the legs erased, animated with the
rig bob / trailing-hair displacement from scripts/build_pet_clip.py.
Legs = procedurally painted tapered capsules along two-bone IK chains
(hip -> knee -> ankle) with colour ramps sampled from the master (row-run
shading, light from the upper-left, 1 px outline), plus the master's own
shoe/boot sprite pasted rigidly at the ankle (column-sheared about the toe for
toe-off, about the heel for toe-up).

Planted feet move -4.8 px per 100 ms frame in canvas space (the runtime moves
the sprite +48 px/s), so they stay fixed in world space.

    python scripts/build_painted_walk.py   # -> tmp/gait/painted-legs/<char>/ previews + frames
"""

from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "tmp/gait/painted-legs"
CHAR_ROOT = ROOT / "assets/generated/pixel-chibi/imagegen-v1"
PAL_ROOT = ROOT / "assets/references/imagegen-inputs"

_spec = importlib.util.spec_from_file_location("build_pet_clip", ROOT / "scripts/build_pet_clip.py")
bpc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bpc)

W, H = 160, 144
N_FRAMES = 8
# Body bob / trailing-hair lag per walk pose (low at contact, high at passing).
WALK_RIG_FRAMES = [
    {"bob": 0, "trail_bob": -1, "trail_dx": -1}, {"bob": 0, "trail_bob": 0, "trail_dx": -2},
    {"bob": -1, "trail_bob": 0, "trail_dx": -1}, {"bob": -1, "trail_bob": -1, "trail_dx": -1},
] * 2
FRAME_MS = 100
SPEED = 48.0                       # runtime translation, px/s
STEP = SPEED * FRAME_MS / 1000.0   # 4.8 px per frame
HALF = STEP * N_FRAMES / 2         # 19.2 px stance travel (= step length)
APPROACH = "painted-legs"


def rnd(v: float) -> int:
    """Consistent round-half-up (never banker's rounding)."""
    return int(math.floor(v + 0.5))


def rgb(h: str) -> tuple[int, int, int, int]:
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255)


# ------------------------------------------------------------------ characters
# Coordinates are continuous: pixel (x, y) covers [x, x+1) x [y, y+1).
CHARS = {
    "firefly": {
        # erase every leg pixel below the skirt hem (sword/hand box x<=53 untouched)
        "erase": [(54, 95, 92, 144)],
        "clip_top": 95,          # legs only visible from this row (+bob, skirt bobs)
        "clip_bobs": True,
        "ground": {"L": 130, "R": 129},
        "len": 30.3,             # hip->ankle bone length (thigh = shin = len/2)
        # width (incl. outline) along the leg, as fraction of hip->ankle (measured on k1)
        "profile": [(0.0, 11), (0.18, 11), (0.25, 10), (0.35, 9.2), (0.45, 9), (0.55, 8.6),
                    (0.65, 8.4), (0.75, 7.2), (0.85, 5.8), (0.95, 6), (1.2, 6)],
        "legs": {
            # hip is under the skirt; ankle = where the master sock meets the shoe
            "R": {"hip": (77.0, 91.0), "ankle": (75.0, 121.0), "neutral_dx": -3.0,
                  "shoe_box": (70, 121, 87, 132), "near": False},
            "L": {"hip": (65.0, 91.0), "ankle": (58.0, 121.0), "neutral_dx": 8.0,
                  "shoe_box": (53, 121, 64, 132), "near": True},
        },
        "bands": [
            # (s_from, s_to, ramp name) by arc length from the hip
            (-99, 13.4, "skin"), (13.4, 14.6, "cuff"), (14.6, 99, "sock"),
        ],
        "ramps": {
            "skin": {"L": "#6d3928", "R": "#7e4f37",
                     "fill": [(0.2, "#e0c9a7"), (0.52, "#feecd6"), (0.72, "#f7d8b8"), (0.87, "#d6af97"), (1.01, "#c59677")]},
            "cuff": {"L": "#6c7076", "R": "#48484d",
                     "fill": [(0.3, "#eae4e2"), (0.72, "#ded7d3"), (1.01, "#bdb6b4")]},
            "sock": {"L": "#6c7076", "R": "#48484d",
                     "fill": [(0.22, "#fefdfc"), (0.6, "#f2eeed"), (0.8, "#ded7d3"), (1.01, "#d0c8c8")]},
        },
        "knee_shade": "#d0c8c8",
        "hem_shadow": None,
        "swing": {"x": [-5.5, 0.5, 6.5], "lift": [2, 3, 1], "heel": [2, 0, -1]},
        "stance_heel": [0, 0, 0, 1, 3],
    },
    "miyabi": {
        "erase": [(40, 129, 90, 144), (49, 128, 58, 129), (63, 128, 72, 129)],
        "clip_top": 128,         # hem is below the rig pivot, so it never bobs
        "clip_bobs": False,
        "ground": {"L": 142, "R": 142},
        "len": 25.0,
        "profile": [(0.0, 8), (0.8, 8), (0.9, 7.2), (1.2, 7.2)],
        "legs": {
            "R": {"hip": (66.5, 106.0), "ankle": (66.5, 131.0), "neutral_dx": -3.0,
                  "shoe_box": (61, 131, 76, 143), "near": False},
            "L": {"hip": (53.5, 106.0), "ankle": (53.5, 131.0), "neutral_dx": 4.0,
                  "shoe_box": (46, 131, 61, 143), "near": True},
        },
        "bands": [(-99, 99, "tights")],
        "ramps": {
            "tights": {"L": "#232426", "R": "#111215",
                       "fill": [(0.2, "#8e564d"), (0.75, "#724941"), (1.01, "#5c2417")]},
            "hem": {"L": "#16191b", "R": "#111215",
                    "fill": [(0.3, "#5c2417"), (1.01, "#29150e")]},
        },
        "knee_shade": None,
        "hem_shadow": "hem",     # first visible row under the hem is in the skirt's shadow
        "swing": {"x": [-5.5, 0.5, 6.5], "lift": [2, 3, 1], "heel": [2, 0, -1]},
        "stance_heel": [0, 0, 0, 1, 2],
    },
    "evanescia": {
        "cutout": True, "cut_top": 109,
        "erase": [(50, 105, 86, 144)], "clip_top": 105, "clip_bobs": True,
        "ground": {"L": 142, "R": 142}, "len": 27.0,
        "profile": [(0.0, 8), (0.6, 7), (1.0, 6), (1.2, 6)],
        "legs": {"R": {"hip": (74.0, 100.0), "ankle": (73.0, 127.0), "neutral_dx": -3.0, "shoe_box": (66, 127, 84, 143), "near": False},
                 "L": {"hip": (61.0, 100.0), "ankle": (58.0, 127.0), "neutral_dx": 4.0, "shoe_box": (51, 127, 65, 143), "near": True}},
        "bands": [(-99, 99, "tights")], "auto_ramps": {"tights": (118, 58, 66)},
        "knee_shade": None, "hem_shadow": None,
        "swing": {"x": [-5.5, 0.5, 6.5], "lift": [2, 3, 1], "heel": [2, 0, -1]}, "stance_heel": [0, 0, 0, 1, 2],
    },
    "robin": {
        "cutout": True, "cut_top": 121,
        "erase": [(52, 117, 86, 144)], "clip_top": 117, "clip_bobs": True,
        "ground": {"L": 142, "R": 142}, "len": 22.0,
        "profile": [(0.0, 8), (0.5, 7), (1.0, 5), (1.2, 5)],
        "legs": {"R": {"hip": (76.0, 110.0), "ankle": (75.0, 131.0), "neutral_dx": -3.0, "shoe_box": (69, 131, 85, 143), "near": False},
                 "L": {"hip": (60.0, 110.0), "ankle": (58.0, 131.0), "neutral_dx": 4.0, "shoe_box": (52, 131, 67, 143), "near": True}},
        "bands": [(-99, 99, "stocking")], "auto_ramps": {"stocking": (122, 55, 65)},
        "knee_shade": None, "hem_shadow": None,
        "swing": {"x": [-5.5, 0.5, 6.5], "lift": [2, 3, 1], "heel": [2, 0, -1]}, "stance_heel": [0, 0, 0, 1, 2],
    },
    "remielle-dan": {
        "cutout": True,
        "erase": [(53, 111, 85, 144)], "clip_top": 111, "clip_bobs": True,
        "behind": [(44, 108, 57, 121), (44, 121, 54, 134), (81, 104, 92, 134)],
        "ground": {"L": 142, "R": 142}, "len": 29.0,
        "profile": [(0.0, 10), (0.3, 9), (0.7, 7), (1.0, 6), (1.2, 6)],
        "legs": {"R": {"hip": (75.0, 104.0), "ankle": (74.0, 133.0), "neutral_dx": -3.0, "shoe_box": (68, 133, 84, 143), "near": False},
                 "L": {"hip": (60.0, 104.0), "ankle": (58.0, 133.0), "neutral_dx": 4.0, "shoe_box": (51, 133, 65, 143), "near": True}},
        "bands": [(-99, 99, "stocking")], "auto_ramps": {"stocking": (124, 56, 64)},
        "knee_shade": None, "hem_shadow": None,
        "swing": {"x": [-5.5, 0.5, 6.5], "lift": [2, 3, 1], "heel": [2, 0, -1]}, "stance_heel": [0, 0, 0, 1, 2],
    },
    "ye-shunguang": {
        "erase": [(58, 110, 92, 144)], "clip_top": 110, "clip_bobs": False, "cutout": True, "cut_skin_only": True,
        "ground": {"L": 142, "R": 142}, "len": 23.0,
        "profile": [(0.0, 9), (1.0, 8), (1.2, 8)],
        "legs": {"R": {"hip": (79.0, 108.0), "ankle": (79.0, 131.0), "neutral_dx": -3.0, "shoe_box": (72, 130, 88, 143), "near": False},
                 "L": {"hip": (61.0, 108.0), "ankle": (61.0, 131.0), "neutral_dx": 4.0, "shoe_box": (54, 130, 69, 143), "near": True}},
        "bands": [(-99, 99, "boot")], "auto_ramps": {"boot": (129, 56, 67)},
        "knee_shade": None, "hem_shadow": None,
        "swing": {"x": [-5.5, 0.5, 6.5], "lift": [2, 3, 1], "heel": [2, 0, -1]}, "stance_heel": [0, 0, 0, 1, 2],
    },
    # long skirt: only the ankles and heels below the hem move
    "ye-shunguang-red": {
        "erase": [(50, 134, 90, 144)], "clip_top": 134, "clip_bobs": False,
        "shear": {"box": (58, 112, 94, 134), "split_x": 69},
        "ground": {"L": 142, "R": 142}, "len": 23.0,
        "profile": [(0.0, 5), (1.0, 5), (1.2, 5)],
        "legs": {"R": {"hip": (78.0, 112.0), "ankle": (77.0, 135.0), "neutral_dx": -3.0, "shoe_box": (71, 135, 85, 143), "near": False},
                 "L": {"hip": (60.0, 112.0), "ankle": (59.0, 135.0), "neutral_dx": 4.0, "shoe_box": (53, 135, 66, 143), "near": True}},
        "bands": [(-99, 99, "skin")], "auto_ramps": {"skin": (135, 56, 61)},
        "knee_shade": None, "hem_shadow": None,
        "swing": {"x": [-4.5, 0.5, 5.5], "lift": [1, 2, 1], "heel": [2, 0, -1]}, "stance_heel": [0, 0, 0, 1, 2],
    },
}
CHARS["ye-shunguang-white"] = CHARS["ye-shunguang"]
CHARS["ye-shunguang-red-white"] = CHARS["ye-shunguang-red"]
CONTACT_FRAME = {"R": 0, "L": 4}   # far leg (viewer-right) strikes first


# ------------------------------------------------------------------ gait
def foot_state(cfg: dict, leg: str, i: int) -> dict:
    k = (i - CONTACT_FRAME[leg]) % N_FRAMES
    base = cfg["legs"][leg]["neutral_dx"]
    if k <= 4:  # stance: contact (k=0) .. toe-off (k=4); foot fixed in world
        off = HALF / 2 - STEP * k
        return {"k": k, "planted": True, "dx": base + off, "lift": 0, "heel": cfg["stance_heel"][k]}
    j = k - 5
    sw = cfg["swing"]
    return {"k": k, "planted": False, "dx": base + sw["x"][j], "lift": sw["lift"][j], "heel": sw["heel"][j]}


# ------------------------------------------------------------------ shoe sprite
def extract_shoe(master: np.ndarray, box) -> tuple[np.ndarray, int, int]:
    x0, y0, x1, y1 = box
    spr = master[y0:y1, x0:x1].copy()
    return spr, x0, y0


def shear_shoe(spr: np.ndarray, heel: int) -> tuple[np.ndarray, np.ndarray]:
    """Column shear. heel>0 lifts the heel (left) pivoting on the toe (right);
    heel<0 lifts the toe pivoting on the heel. Returns (sprite padded on top, shift per column)."""
    h, w = spr.shape[:2]
    cols = np.where(spr[..., 3].max(axis=0) > 0)[0]
    c0, c1 = int(cols.min()), int(cols.max())
    shift = np.zeros(w, int)
    for c in range(w):
        if heel > 0:
            shift[c] = rnd(heel * (c1 - c) / max(1, c1 - c0))
        elif heel < 0:
            shift[c] = rnd(-heel * (c - c0) / max(1, c1 - c0))
    shift = np.clip(shift, 0, None)   # empty columns outside the shoe must not shift negatively
    pad = int(shift.max())
    out = np.zeros((h + pad, w, 4), np.uint8)
    for c in range(w):
        out[pad - shift[c]: pad - shift[c] + h, c] = spr[:, c]
    return out, shift


# ------------------------------------------------------------------ IK + painting
def ik(hip, ankle, total):
    hx, hy = hip
    ax, ay = ankle
    d = math.hypot(ax - hx, ay - hy)
    l1 = l2 = total / 2
    ex, ey = (ax - hx) / d, (ay - hy) / d
    if d >= total:  # out of reach -> straight (stretched) leg
        return (hx + ex * d / 2, hy + ey * d / 2), d / 2, d / 2
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    px, py = hx + ex * a, hy + ey * a
    knee = (px + h * ey, py - h * ex)  # perpendicular with +x component: knee bends forward
    return knee, l1, l2


def width_at(profile, frac):
    fs = [p[0] for p in profile]
    ws = [p[1] for p in profile]
    return float(np.interp(frac, fs, ws))


def paint_leg(cfg, hip, knee, ankle, l1, l2, bob):
    """Return (mask, s_map, outline) for one leg on the full canvas (unclipped)."""
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
    cx, cy = xs + 0.5, ys + 0.5
    total = l1 + l2
    best = np.full((H, W), np.inf)
    s_map = np.zeros((H, W))
    segs = [(hip, knee, 0.0, l1), (knee, ankle, l1, l2)]
    for idx, ((ax, ay), (bx, by), s0, ln) in enumerate(segs):
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy
        t = np.clip(((cx - ax) * vx + (cy - ay) * vy) / L2, 0.0, 1.0)
        if idx == 1:  # let the shin run a little past the ankle, under the shoe
            t = np.clip(((cx - ax) * vx + (cy - ay) * vy) / L2, 0.0, 1.0 + 3.0 / ln)
        if idx == 0:  # thigh continues above the hip under the skirt
            t = np.clip(((cx - ax) * vx + (cy - ay) * vy) / L2, -4.0 / ln, 1.0)
        px, py = ax + t * vx, ay + t * vy
        dist = np.hypot(cx - px, cy - py)
        s = s0 + t * ln
        wv = np.interp(s / total, [p[0] for p in cfg["profile"]], [p[1] for p in cfg["profile"]])
        score = dist - wv / 2
        better = score < best
        best = np.where(better, score, best)
        s_map = np.where(better, s, s_map)
    mask = best < 0
    inside = np.zeros((H + 2, W + 2), bool)
    inside[1:-1, 1:-1] = mask
    interior = mask & inside[:-2, 1:-1] & inside[2:, 1:-1] & inside[1:-1, :-2] & inside[1:-1, 2:]
    outline = mask & ~interior
    return mask, s_map, outline


def colour_leg(cfg, mask, s_map, outline, clip_top, knee, l1, bend):
    out = np.zeros((H, W, 4), np.uint8)
    ramps = cfg["ramps"]

    def band_of(s):
        for a, b, name in cfg["bands"]:
            if a <= s < b:
                return name
        return cfg["bands"][-1][2]

    for y in range(max(0, clip_top), H):
        row = mask[y]
        x = 0
        while x < W:
            if not row[x]:
                x += 1
                continue
            x0 = x
            while x < W and row[x]:
                x += 1
            x1 = x  # run [x0, x1)
            inner = [c for c in range(x0, x1) if not outline[y, c]]
            n = len(inner)
            for c in range(x0, x1):
                name = band_of(s_map[y, c])
                if cfg["hem_shadow"] and y == clip_top:
                    name = cfg["hem_shadow"]
                ramp = ramps[name]
                if outline[y, c]:
                    side = "L" if (c - x0 + 0.5) / (x1 - x0) < 0.5 else "R"
                    out[y, c] = rgb(ramp[side])
                else:
                    f = (inner.index(c) + 0.5) / n
                    for th, col in ramp["fill"]:
                        if f < th:
                            out[y, c] = rgb(col)
                            break
    # knee crease: on a clearly bent knee, shade the interior pixels at the back of the knee
    if cfg.get("knee_shade") and bend > 3.0:
        kx, ky = knee
        for y in range(int(ky) - 1, int(ky) + 2):
            if y < clip_top or y >= H:
                continue
            cols = [c for c in range(W) if mask[y, c] and not outline[y, c]]
            if cols:
                c = cols[0]
                if abs(s_map[y, c] - l1) < 3:
                    out[y, c] = rgb(cfg["knee_shade"])
    return out


def auto_ramp(master: np.ndarray, y: int, x0: int, x1: int) -> dict:
    """Sample an outline+fill ramp from one row of an opaque leg run in the master."""
    row = [(x, tuple(int(v) for v in master[y, x, :3])) for x in range(x0, x1 + 1) if master[y, x, 3] > 0]
    hexc = lambda c: "#%02x%02x%02x" % c
    if len(row) < 3:
        raise SystemExit(f"auto_ramp: no leg run at y={y} x={x0}..{x1}")
    inner = row[1:-1]
    fill = [(round((i + 1) / len(inner), 3) if i < len(inner) - 1 else 1.01, hexc(c)) for i, (_, c) in enumerate(inner)]
    return {"L": hexc(row[0][1]), "R": hexc(row[-1][1]), "fill": fill}


def rebuild_behind_legs(cfg: dict, master: np.ndarray) -> np.ndarray:
    """Reconstruct what the master shows *behind* its legs inside the erase box (e.g. wings).

    The master's own legs (neutral IK pose + shoe boxes, grown by 1 px) are removed and every
    removed run that is bounded on both sides by kept pixels is filled from those neighbours,
    so the walking legs never leave a hole in the background.
    """
    legs = np.zeros((H, W), bool)
    for lc in cfg["legs"].values():
        knee, l1, l2 = ik(lc["hip"], lc["ankle"], cfg["len"])
        mask, _, _ = paint_leg(cfg, lc["hip"], knee, lc["ankle"], l1, l2, 0)
        legs |= mask
        x0, y0, x1, y1 = lc["shoe_box"]
        legs[y0:y1, x0:x1] |= master[y0:y1, x0:x1, 3] > 0
    grown = legs.copy()
    grown[1:] |= legs[:-1]; grown[:-1] |= legs[1:]; grown[:, 1:] |= legs[:, :-1]; grown[:, :-1] |= legs[:, 1:]
    out = np.zeros_like(master)
    for x0, y0, x1, y1 in cfg["erase"]:
        for y in range(y0, min(y1, H)):
            row = master[y].copy()
            hole = grown[y] & (np.arange(W) >= x0) & (np.arange(W) < x1)
            row[hole] = 0
            x = x0
            while x < x1:
                if hole[x]:
                    e = x
                    while e < x1 and hole[e]:
                        e += 1
                    left, right = x - 1, e
                    if left >= 0 and right < W and row[left, 3] and master[y, right, 3] and not grown[y, right]:
                        for k in range(x, e):   # nearest-neighbour stretch from both sides
                            row[k] = row[left] if (k - x) < (e - x) / 2 else master[y, right]
                    x = e
                else:
                    x += 1
            out[y, x0:x1] = row[x0:x1]
    return out



def _seg_dist(px, py, a, b):
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    t = np.clip(((px - ax) * vx + (py - ay) * vy) / max(1e-9, vx * vx + vy * vy), 0, 1)
    return np.hypot(px - (ax + t * vx), py - (ay + t * vy))


def cutout_pieces(cfg: dict, master: np.ndarray):
    """Split the master's own leg pixels into thigh/shin pieces per leg (cut-out rig).

    Pixels inside the erase boxes (minus shoe boxes) are assigned to the nearest leg bone within
    `cut_reach` px; anything farther away stays as a static back layer so nothing is lost.
    Returns ({leg: {"thigh": mask, "shin": mask, "hip0", "knee0", "ankle0"}}, static_layer).
    """
    region = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in cfg["erase"]:
        region[y0:y1, x0:x1] = True
    for lc in cfg["legs"].values():
        x0, y0, x1, y1 = lc["shoe_box"]
        region[y0:y1, x0:x1] = False
    region &= master[..., 3] > 0
    hem = np.zeros((H, W), bool)             # skirt hem rows inside the box stay put
    hem[:cfg.get("cut_top", 0)] = True
    hem &= region
    region &= ~hem
    front = np.zeros_like(master)
    if cfg.get("cut_skin_only"):              # garment panels in front of the legs stay put, on top
        r, g, b = (master[..., k].astype(int) for k in range(3))
        skin = (r > 190) & (g > 150) & (b > 120) & (r - b > 25) & (r - g < 70)
        dark = (r + g + b) < 200
        grow = skin.copy()
        grow[1:] |= skin[:-1]; grow[:-1] |= skin[1:]; grow[:, 1:] |= skin[:, :-1]; grow[:, :-1] |= skin[:, 1:]
        leg_px = skin | (dark & grow)
        panel = region & ~leg_px
        front[panel] = master[panel]
        region &= leg_px
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
    px, py = xs + 0.5, ys + 0.5
    reach = cfg.get("cut_reach", 7.0)
    geo, dists = {}, {}
    for leg, lc in cfg["legs"].items():
        knee0, _, _ = ik(lc["hip"], lc["ankle"], cfg["len"])
        dt = _seg_dist(px, py, lc["hip"], knee0)
        ds = _seg_dist(px, py, knee0, lc["ankle"])
        geo[leg] = {"hip0": lc["hip"], "knee0": knee0, "ankle0": lc["ankle"], "dt": dt, "ds": ds}
        dists[leg] = np.minimum(dt, ds)
    legs = list(cfg["legs"])
    nearest = np.where(dists[legs[0]] <= dists[legs[1]], legs[0], legs[1])
    pieces = {}
    taken = np.zeros((H, W), bool)
    for leg in legs:
        g = geo[leg]
        own = region & (nearest == leg) & (dists[leg] <= reach)
        taken |= own
        near_knee = np.hypot(px - g["knee0"][0], py - g["knee0"][1]) <= 1.5
        pieces[leg] = {"thigh": own & ((g["dt"] <= g["ds"]) | near_knee),
                       "shin": own & ((g["ds"] < g["dt"]) | near_knee),
                       "hip0": g["hip0"], "knee0": g["knee0"], "ankle0": g["ankle0"]}
    static = np.zeros_like(master)
    top = max(cfg.get("cut_top", 0), min(b[1] for b in cfg["erase"]))
    seam = np.zeros((H, W), bool)             # a few original rows under the hip seam, behind the legs
    seam[top:top + 4] = True
    keep = (region & ~taken) | hem | (region & seam)
    static[keep] = master[keep]
    return pieces, static, front


def draw_piece(dst: np.ndarray, master: np.ndarray, mask: np.ndarray, pivot0, pivot1, angle: float) -> None:
    """Rotate the masked master pixels by `angle` (radians) about pivot0 and place pivot0 at pivot1.
    Inverse nearest-neighbour mapping, so the piece never tears."""
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return
    ca, sa = math.cos(angle), math.sin(angle)
    cx, cy = xs + 0.5 - pivot0[0], ys + 0.5 - pivot0[1]
    fx, fy = cx * ca - cy * sa + pivot1[0], cx * sa + cy * ca + pivot1[1]
    x0, x1 = max(0, int(fx.min()) - 2), min(W, int(fx.max()) + 3)
    y0, y1 = max(0, int(fy.min()) - 2), min(H, int(fy.max()) + 3)
    gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float64)
    dx, dy = gx + 0.5 - pivot1[0], gy + 0.5 - pivot1[1]
    sx = np.floor(dx * ca + dy * sa + pivot0[0]).astype(int)
    sy = np.floor(-dx * sa + dy * ca + pivot0[1]).astype(int)
    ok = (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
    hit = np.zeros_like(ok)
    hit[ok] = mask[sy[ok], sx[ok]]
    dst[gy[hit].astype(int), gx[hit].astype(int)] = master[sy[hit], sx[hit]]



def over(dst: np.ndarray, src: np.ndarray, ox: int = 0, oy: int = 0) -> None:
    h, w = src.shape[:2]
    for yy in range(h):
        ty = oy + yy
        if not 0 <= ty < H:
            continue
        for xx in range(w):
            tx = ox + xx
            if 0 <= tx < W and src[yy, xx, 3] > 0:
                dst[ty, tx] = src[yy, xx]


# ------------------------------------------------------------------ build
def build_char(name: str) -> dict:
    cfg = CHARS[name]
    cdir = CHAR_ROOT / name
    spec = json.loads((cdir / "clips.json").read_text(encoding="utf-8"))
    rig = spec["rig"]
    walk = WALK_RIG_FRAMES
    master = np.asarray(Image.open(cdir / "idle/k1.png").convert("RGBA")).copy()
    for rname, (ry, rx0, rx1) in cfg.get("auto_ramps", {}).items():
        cfg.setdefault("ramps", {})[rname] = auto_ramp(master, ry, rx0, rx1)
    palette = {tuple(rgb(h)[:3]) for h in json.loads((PAL_ROOT / name / "palette.json").read_text())["colors"]}

    shoes = {leg: extract_shoe(master, lc["shoe_box"]) for leg, lc in cfg["legs"].items()}
    upper_src = master.copy()
    for x0, y0, x1, y1 in cfg["erase"]:
        upper_src[y0:y1, x0:x1] = 0
    if cfg.get("cutout"):
        pieces, cut_static, cut_front = cutout_pieces(cfg, master)
    shear = cfg.get("shear")
    if shear:   # lower legs / long hem that follow each foot (drawn per frame below)
        sx0, sy0, sx1, sy1 = shear["box"]
        shear_src = np.zeros_like(master)
        shear_src[sy0:sy1, sx0:sx1] = master[sy0:sy1, sx0:sx1]
        upper_src[sy0:sy1, sx0:sx1] = 0
    # master pixels that sit behind the legs inside the erased box (e.g. wing strands) are kept as a back layer
    behind_src = np.zeros_like(master)
    for x0, y0, x1, y1 in cfg.get("behind", []):
        behind_src[y0:y1, x0:x1] = master[y0:y1, x0:x1]
    if cfg.get("behind_fill"):
        behind_src = np.maximum(behind_src, rebuild_behind_legs(cfg, master))

    out_dir = HERE / name
    out_dir.mkdir(parents=True, exist_ok=True)
    frames, feet_log = [], []
    for i in range(N_FRAMES):
        fr = walk[i]
        bob = fr.get("bob", 0)
        rig_frame = {"bob": bob, "trail_bob": fr.get("trail_bob", bob), "trail_dx": fr.get("trail_dx", 0)}
        upper = bpc.warp(upper_src, *bpc.displacement(rig_frame, rig))
        canvas = bpc.warp(behind_src, *bpc.displacement(rig_frame, rig)).copy()
        if cfg.get("cutout"):
            st_layer = bpc.warp(cut_static, *bpc.displacement(rig_frame, rig))
            a = st_layer[..., 3] > 0
            canvas[a] = st_layer[a]
        clip_top = cfg["clip_top"] + (bob if cfg["clip_bobs"] else 0)
        flog = {}
        for leg in ("R", "L"):  # far leg first, near leg on top
            lc = cfg["legs"][leg]
            st = foot_state(cfg, leg, i)
            ox = rnd(st["dx"])
            spr, sx0, sy0 = shoes[leg]
            sheared, shift = shear_shoe(spr, st["heel"])
            pad = sheared.shape[0] - spr.shape[0]
            ank_col = int(math.floor(lc["ankle"][0])) - sx0
            ank_col = min(max(ank_col, 0), len(shift) - 1)
            ax = lc["ankle"][0] + ox
            ay = lc["ankle"][1] - st["lift"] - shift[ank_col]
            hip = (lc["hip"][0], lc["hip"][1] + bob)
            knee, l1, l2 = ik(hip, (ax, ay), cfg["len"])
            # bend = distance of the knee from the straight hip-ankle line
            mx, my = (hip[0] + ax) / 2, (hip[1] + ay) / 2
            bend = math.hypot(knee[0] - mx, knee[1] - my)
            if cfg.get("cutout"):
                pc = pieces[leg]
                ang = lambda a, b: math.atan2(b[1] - a[1], b[0] - a[0])
                t_rot = ang(hip, knee) - ang(pc["hip0"], pc["knee0"])
                s_rot = ang(knee, (ax, ay)) - ang(pc["knee0"], pc["ankle0"])
                leg_rgba = np.zeros((H, W, 4), np.uint8)
                draw_piece(leg_rgba, master, pc["thigh"], pc["hip0"], hip, t_rot)
                draw_piece(leg_rgba, master, pc["shin"], pc["knee0"], knee, s_rot)
            else:
                mask, s_map, outline = paint_leg(cfg, hip, knee, (ax, ay), l1, l2, bob)
                leg_rgba = colour_leg(cfg, mask, s_map, outline, clip_top, knee, l1, bend)
            over(canvas, leg_rgba)
            over(canvas, sheared, sx0 + ox, sy0 - pad - st["lift"])
            flog[leg] = {"shoe_dx": ox, "ankle_x": round(ax, 2), "ankle_y": round(ay, 2),
                         "shoe_left_x": sx0 + ox, "lift": st["lift"], "heel": st["heel"],
                         "planted": st["planted"], "phase_k": st["k"], "knee": [round(knee[0], 1), round(knee[1], 1)]}
        if cfg.get("cutout"):
            fr_layer = bpc.warp(cut_front, *bpc.displacement(rig_frame, rig))
            a = fr_layer[..., 3] > 0
            canvas[a] = fr_layer[a]
        if shear:
            band = bpc.warp(shear_src, *bpc.displacement(rig_frame, rig))
            sx0, sy0, sx1, sy1 = shear["box"]
            # static underlay (garment only, no skin) so the seam between the two legs never opens
            r, g, b = (band[..., k].astype(int) for k in range(3))
            skin = (r > 200) & (g > 170) & (b > 140) & (r - b > 25)
            under = (band[..., 3] > 0) & ~skin & (canvas[..., 3] == 0)
            canvas[under] = band[under]
            for leg in ("R", "L"):   # far leg first
                ox = flog[leg]["shoe_dx"]
                cols = np.arange(W) >= shear["split_x"] if leg == "R" else np.arange(W) < shear["split_x"]
                for y in range(sy0, sy1):
                    t = (y - sy0) / max(1, sy1 - 1 - sy0)          # 0 at the knee band, 1 at the ankle
                    dx, ty = int(round(ox * t)), y
                    if not 0 <= ty < H:
                        continue
                    for x in np.nonzero(cols & (band[y, :, 3] > 0))[0]:
                        tx = x + dx
                        if 0 <= tx < W:
                            canvas[ty, tx] = band[y, x]
        a = upper[..., 3] > 0
        canvas[a] = upper[a]
        frames.append(canvas)
        feet_log.append(flog)
        Image.fromarray(canvas, "RGBA").save(out_dir / f"frame-{i:03d}.png")

    # palette + alpha audit
    viol = 0
    semi = 0
    for f in frames:
        al = f[..., 3]
        semi += int(((al > 0) & (al < 255)).sum())
        for px in f[al > 0][:, :3]:
            if tuple(int(v) for v in px) not in palette:
                viol += 1
    # world slide of planted feet
    slides = {}
    for leg in ("R", "L"):
        c = CONTACT_FRAME[leg]
        worlds = []
        for k in range(5):
            i = c + k
            fl = feet_log[i % N_FRAMES][leg]
            worlds.append(fl["shoe_dx"] + STEP * i)
        slides[leg] = round(max(worlds) - min(worlds), 3)

    make_sheet(frames, out_dir / "sheet.png")
    make_ground(frames, cfg, out_dir / "ground.png", name)
    make_preview(frames, cfg, out_dir / "preview.mp4")

    per_frame = []
    for i, fl in enumerate(feet_log):
        per_frame.append({"frame": i, "t_ms": i * FRAME_MS,
                          "bob": walk[i].get("bob", 0),
                          "viewer_left_near": fl["L"], "viewer_right_far": fl["R"],
                          "planted": [leg for leg in ("L", "R") if fl[leg]["planted"]]})
    return {"frames": per_frame, "max_planted_world_slide_px": max(slides.values()),
            "planted_world_slide_by_leg_px": slides, "palette_violations": viol,
            "semi_transparent_pixels": semi}


# ------------------------------------------------------------------ review outputs
def union_bbox(frames, margin=2):
    a = np.zeros((H, W), bool)
    for f in frames:
        a |= f[..., 3] > 0
    ys, xs = np.where(a)
    return (max(0, xs.min() - margin), max(0, ys.min() - margin), min(W, xs.max() + 1 + margin), min(H, ys.max() + 1 + margin))


def make_sheet(frames, path, scale=4):
    x0, y0, x1, y1 = union_bbox(frames)
    cw, ch = (x1 - x0) * scale, (y1 - y0) * scale
    sheet = Image.new("RGBA", (cw * len(frames) + 4 * (len(frames) - 1), ch), (40, 44, 58, 255))
    for i, f in enumerate(frames):
        im = Image.fromarray(f, "RGBA").crop((x0, y0, x1, y1)).resize((cw, ch), Image.NEAREST)
        tile = Image.new("RGBA", (cw, ch), (72, 78, 98, 255))
        tile.alpha_composite(im)
        sheet.paste(tile, (i * (cw + 4), 0))
    sheet.save(path)


def make_ground(frames, cfg, path, name, scale=3):
    gy = max(cfg["ground"].values())
    top = cfg["clip_top"] - 12
    bot = gy + 3
    rh = (bot - top) * scale
    offs = [rnd(SPEED * i * FRAME_MS / 1000) for i in range(N_FRAMES)]
    strip_w = (W + max(offs) + 10) * scale
    gap = 6
    img = Image.new("RGBA", (strip_w, (rh + gap) * N_FRAMES * 2 + 30), (28, 32, 44, 255))
    d = ImageDraw.Draw(img)
    for block in range(2):
        by = block * ((rh + gap) * N_FRAMES + 30)
        for i, f in enumerate(frames):
            ry = by + i * (rh + gap)
            ox = offs[i] if block == 0 else 0
            crop = Image.fromarray(f, "RGBA").crop((0, top, W, bot)).resize((W * scale, rh), Image.NEAREST)
            for wx in range(0, W + max(offs) + 10, 10):
                d.line([(wx * scale, ry), (wx * scale, ry + rh - 1)], fill=(60, 66, 84, 255) if wx % 50 else (95, 100, 125, 255))
            img.alpha_composite(crop, (ox * scale, ry))
            for g in set(cfg["ground"].values()):
                yy = ry + (g + 1 - top) * scale
                d.line([(0, yy), (strip_w, yy)], fill=(200, 120, 60, 255))
        d.text((4, by + (rh + gap) * N_FRAMES + 8) if block == 0 else (4, by - 22),
               "top: moving at 48px/s (planted feet should stay on the same tick)" if block == 0 else "bottom: in place", fill=(230, 230, 230, 255))
    img.save(path)


def make_preview(frames, cfg, path, scale=4, cycles=3, fps=50):
    dur = N_FRAMES * FRAME_MS / 1000 * cycles
    art_w = W + rnd(SPEED * dur) + 8
    art_w += art_w % 2
    gy = max(cfg["ground"].values()) + 1
    with tempfile.TemporaryDirectory() as tmp:
        n = int(round(dur * fps))
        for k in range(n):
            t = k / fps
            fi = int(t * 1000 // FRAME_MS) % N_FRAMES
            x = rnd(SPEED * t)
            bg = Image.new("RGBA", (art_w * scale, H * scale), (26, 30, 40, 255))
            d = ImageDraw.Draw(bg)
            d.line([(0, gy * scale), (art_w * scale, gy * scale)], fill=(80, 88, 110, 255), width=2)
            for wx in range(0, art_w, 10):
                d.line([(wx * scale, gy * scale), (wx * scale, gy * scale + (10 if wx % 50 else 20))], fill=(120, 128, 150, 255), width=2)
            spr = Image.fromarray(frames[fi], "RGBA").resize((W * scale, H * scale), Image.NEAREST)
            bg.alpha_composite(spr, (x * scale, 0))
            bg.convert("RGB").save(f"{tmp}/{k:05d}.png")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", f"{tmp}/%05d.png",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)


def main(argv: list[str] | None = None) -> int:
    only = set((argv if argv is not None else sys.argv[1:]))
    report = {"approach": APPROACH, "cycle_ms": N_FRAMES * FRAME_MS, "frame_ms": FRAME_MS,
              "speed_px_per_s": SPEED, "step_length_px": HALF, "characters": {}}
    for name in CHARS:
        if only and name not in only:
            continue
        res = build_char(name)
        report["characters"][name] = res
        print(f"{name}: slide {res['max_planted_world_slide_px']} px, palette violations {res['palette_violations']}, semi {res['semi_transparent_pixels']}")
    report["notes"] = NOTES
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


NOTES = []

if __name__ == "__main__":
    raise SystemExit(main())
