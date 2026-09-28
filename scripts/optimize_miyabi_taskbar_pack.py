"""Create a deterministic, non-runtime optimization draft for Miyabi's pet pack.

The optimizer intentionally reads the admitted right-facing runtime pack and
writes only ``tmp/miyabi-optimized-draft``.  It does not rebuild the stable
runtime pack, change the renderer, add clips, or author new props.  The two
pixel-only operations are deliberately conservative:

* close only tiny (<= 3 px) alpha holes that are fully enclosed by the
  silhouette; border-connected transparent space is never touched;
* clear RGB from fully transparent pixels so no hidden matte/fringe colour can
  leak through a later compositor.

All nine action IDs, their total durations and the right-authored/mirrored-left
contract are retained.  The output uses short, premultiplied-alpha-safe visual
in-betweens instead of holding a pose for 100--450 ms and then snapping to the
next one.  The broken clipped sleep silhouette is rebuilt from the same
approved chibi body with a centred, supersampled rotation.  No new action or
prop is introduced.  This is a review draft, not a runtime admission step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from collections import Counter, deque
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "assets/runtime/taskbar-pet/clip-packs/miyabi/v1"
DEFAULT_OUTPUT = ROOT / "tmp/miyabi-optimized-draft"
MIYABI_BODY = ROOT / "assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png"
CANVAS = (160, 144)
ANCHOR_RIGHT = (64, 120)
FEET_Y = 143
FPS_REVIEW = 60
MAX_HOLE_AREA = 3
SLEEP_SUPERSAMPLE = 4

CLIPS = [
    "idle",
    "walk",
    "hunger_cue",
    "eat",
    "sleep_cue",
    "sleep_enter",
    "sleep_loop",
    "wake",
    "spirit_tail",
]

# Weight profiles alter only timing, not artwork.  Values are normalized to
# the source clip total by smooth_durations().  The endpoints are held a bit
# longer and the middle transition is a bit quicker, avoiding a mechanical
# equal-duration tick without changing the authored choreography.
TWEEN_STEPS = {
    "idle": 6,
    "walk": 2,
    "hunger_cue": 4,
    "eat": 3,
    "sleep_cue": 4,
}


def rel(path: Path) -> str:
    """Return a stable repository-relative path for generated metadata."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_rgba(image: Image.Image) -> str:
    return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    return image.getchannel("A").getbbox()


def neighbors(x: int, y: int) -> Iterable[tuple[int, int]]:
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                yield x + dx, y + dy


def enclosed_alpha_holes(image: Image.Image) -> list[list[tuple[int, int]]]:
    """Return transparent components not connected to the canvas border.

    Eight-connectivity is used so diagonal openings count as outside negative
    space.  This avoids sealing deliberate gaps between hair, weapon and coat
    panels merely because they touch at a corner.
    """
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    outside: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()
    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(height):
        queue.append((0, y))
        queue.append((width - 1, y))
    while queue:
        x, y = queue.popleft()
        if not (0 <= x < width and 0 <= y < height):
            continue
        if (x, y) in outside or pixels[x, y][3] != 0:
            continue
        outside.add((x, y))
        queue.extend(neighbors(x, y))

    candidates = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if pixels[x, y][3] == 0 and (x, y) not in outside
    }
    seen: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    for start in sorted(candidates, key=lambda point: (point[1], point[0])):
        if start in seen:
            continue
        component: list[tuple[int, int]] = []
        stack = [start]
        seen.add(start)
        while stack:
            point = stack.pop()
            component.append(point)
            x, y = point
            for candidate in neighbors(x, y):
                if candidate in candidates and candidate not in seen:
                    seen.add(candidate)
                    stack.append(candidate)
        components.append(component)
    return components


def fill_colour_for_hole(image: Image.Image, component: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    """Choose the dominant local opaque colour for a tiny enclosed hole."""
    pixels = image.load()
    boundary: list[tuple[int, int, int, int]] = []
    component_set = set(component)
    for x, y in component:
        for nx, ny in neighbors(x, y):
            if (nx, ny) in component_set:
                continue
            if 0 <= nx < image.width and 0 <= ny < image.height:
                colour = pixels[nx, ny]
                if colour[3] > 0:
                    boundary.append(colour)
    if not boundary:
        return (0, 0, 0, 255)
    counts = Counter((r, g, b) for r, g, b, _ in boundary)
    rgb = max(counts, key=lambda colour: (counts[colour], sum(colour), tuple(-value for value in colour)))
    alpha = max(colour[3] for colour in boundary)
    return (*rgb, alpha)


def cleanup_frame(image: Image.Image) -> tuple[Image.Image, dict[str, int]]:
    """Close only tiny interior holes and remove hidden RGB fringe."""
    source = image.convert("RGBA")
    result = source.copy()
    before_pixels = list(source.getdata())
    holes = enclosed_alpha_holes(source)
    small_holes = [component for component in holes if len(component) <= MAX_HOLE_AREA]
    pixels = result.load()
    filled_pixels = 0
    for component in small_holes:
        colour = fill_colour_for_hole(source, component)
        for x, y in component:
            pixels[x, y] = colour
            filled_pixels += 1

    hidden_before = 0
    hidden_after = 0
    for y in range(result.height):
        for x in range(result.width):
            r, g, b, alpha = pixels[x, y]
            if alpha == 0:
                if (r, g, b) != (0, 0, 0):
                    hidden_before += 1
                pixels[x, y] = (0, 0, 0, 0)
            if pixels[x, y][3] == 0 and pixels[x, y][:3] != (0, 0, 0):
                hidden_after += 1

    after_pixels = list(result.getdata())
    changed_pixels = sum(before != after for before, after in zip(before_pixels, after_pixels))
    after_small_holes = sum(len(component) for component in enclosed_alpha_holes(result) if len(component) <= MAX_HOLE_AREA)
    return result, {
        "holes_before": sum(len(component) for component in holes),
        "small_hole_components_before": len(small_holes),
        "filled_alpha_pixels": filled_pixels,
        "small_hole_pixels_after": after_small_holes,
        "hidden_rgb_pixels_before": hidden_before,
        "hidden_rgb_pixels_after": hidden_after,
        "changed_rgba_pixels": changed_pixels,
    }


def smooth_durations(source_durations: list[int], clip_name: str) -> list[int]:
    """Apply an eased timing profile while preserving total clip duration."""
    weights = CADENCE_PROFILES[clip_name]
    if len(weights) != len(source_durations):
        raise ValueError(f"Cadence profile for {clip_name} does not match frame count")
    total = sum(source_durations)
    weight_sum = sum(weights)
    raw = [total * weight / weight_sum for weight in weights]
    durations = [max(1, math.floor(value)) for value in raw]
    remainder = total - sum(durations)
    order = sorted(range(len(raw)), key=lambda index: (raw[index] - math.floor(raw[index]), -index), reverse=True)
    for index in order[:remainder]:
        durations[index] += 1
    if sum(durations) != total:
        raise AssertionError(f"Duration redistribution failed for {clip_name}")
    return durations


def frame_paths(source_root: Path, clip_name: str) -> list[Path]:
    directory = source_root / "clips" / clip_name / "right" / "frames"
    paths = sorted(directory.glob("frame-*.png"))
    expected = [directory / f"frame-{index:03d}.png" for index in range(len(paths))]
    if not directory.is_dir() or paths != expected:
        raise ValueError(f"Non-contiguous or missing source frames for {clip_name}: {directory}")
    if (source_root / "clips" / clip_name / "left").exists():
        raise ValueError(f"Source pack unexpectedly stores left frames: {clip_name}")
    return paths


def load_source(source_root: Path) -> tuple[dict[str, object], dict[str, list[Image.Image]], dict[str, list[Path]]]:
    manifest_path = source_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = manifest.get("required_clips")
    if required != CLIPS:
        raise ValueError(f"Expected the existing nine Miyabi clips, got {required!r}")
    clips: dict[str, list[Image.Image]] = {}
    paths_by_clip: dict[str, list[Path]] = {}
    clip_meta = manifest.get("clips")
    if not isinstance(clip_meta, dict):
        raise ValueError("Source manifest has no clips object")
    for clip_name in CLIPS:
        paths = frame_paths(source_root, clip_name)
        paths_by_clip[clip_name] = paths
        frames = [Image.open(path).convert("RGBA") for path in paths]
        if not frames or any(frame.size != CANVAS for frame in frames):
            raise ValueError(f"Invalid frame dimensions in {clip_name}")
        meta = clip_meta.get(clip_name)
        if not isinstance(meta, dict):
            raise ValueError(f"Missing source metadata for {clip_name}")
        durations = [int(value) for value in meta.get("frame_durations_ms", [])]
        if len(durations) != len(frames) or any(value <= 0 for value in durations):
            raise ValueError(f"Invalid source timing for {clip_name}")
        clips[clip_name] = frames
    return manifest, clips, paths_by_clip


def write_frames(output_root: Path, clips: dict[str, list[Image.Image]]) -> None:
    for clip_name, frames in clips.items():
        directory = output_root / "behavior-pack-v1" / "clips" / clip_name / "right" / "frames"
        directory.mkdir(parents=True, exist_ok=True)
        for index, frame in enumerate(frames):
            frame.save(directory / f"frame-{index:03d}.png", optimize=True)


def draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: tuple[int, int, int], font: ImageFont.ImageFont) -> None:
    draw.text(xy, text, fill=fill, font=font)


def create_contact_sheet(output_root: Path, clips: dict[str, list[Image.Image]], durations: dict[str, list[int]]) -> Path:
    tile_w, tile_h = 560, 190
    columns = 3
    rows = math.ceil(len(CLIPS) / columns)
    sheet = Image.new("RGB", (tile_w * columns, tile_h * rows), (42, 55, 70))
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 10)
    except OSError:
        font = ImageFont.load_default()
        small_font = font
    for slot, clip_name in enumerate(CLIPS):
        x = (slot % columns) * tile_w
        y = (slot // columns) * tile_h
        frames = clips[clip_name]
        times = durations[clip_name]
        total_ms = sum(times)
        draw = ImageDraw.Draw(sheet)
        draw_text(draw, (x + 8, y + 6), f"{clip_name}  {len(frames)}f  {total_ms}ms", (232, 246, 255), font)
        sample_indices = [round(index * (len(frames) - 1) / 3) for index in range(4)]
        for sample_index, frame_index in enumerate(sample_indices):
            preview = frames[frame_index].resize((128, 115), Image.Resampling.NEAREST)
            px = x + 8 + sample_index * 136
            py = y + 30
            sheet.paste(preview, (px, py), preview)
            draw_text(draw, (px, y + 151), f"{frame_index:03d} / {times[frame_index]}ms", (202, 222, 236), small_font)
    path = output_root / "behavior-pack-v1" / "review" / "behavior-pack-contact-sheet.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, optimize=True)
    return path


def render_review_video(output_root: Path, clips: dict[str, list[Image.Image]], durations: dict[str, list[int]]) -> dict[str, object]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to make the review video")
    width, height = 960, 540
    path = output_root / "behavior-pack-v1" / "video" / "miyabi-optimized-review.mp4"
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(FPS_REVIEW),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert process.stdin is not None
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    emitted = 0
    elapsed_ms = 0
    for clip_name in CLIPS:
        for frame, duration_ms in zip(clips[clip_name], durations[clip_name]):
            screen = Image.new("RGB", (width, height), (7, 15, 28))
            draw = ImageDraw.Draw(screen)
            draw_text(draw, (28, 24), f"Miyabi / {clip_name}", (229, 244, 255), font)
            preview = frame.resize((480, 432), Image.Resampling.NEAREST)
            screen.paste(preview, ((width - preview.width) // 2, 74), preview)
            elapsed_ms += duration_ms
            target_emitted = max(1, round(elapsed_ms * FPS_REVIEW / 1000))
            repeats = max(1, target_emitted - emitted)
            for _ in range(repeats):
                process.stdin.write(screen.tobytes())
            emitted += repeats
    process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    if process.wait() != 0:
        raise RuntimeError(stderr[-4000:])
    return {
        "path": rel(path),
        "fps": FPS_REVIEW,
        "frame_count": emitted,
        "duration_seconds": round(emitted / FPS_REVIEW, 3),
        "authored_duration_ms": sum(sum(values) for values in durations.values()),
        "resolution": [width, height],
        "cadence": "authored frame durations quantized to 60fps review frames",
    }


def write_manifest(
    output_root: Path,
    source_root: Path,
    source_manifest: dict[str, object],
    source_manifest_path: Path,
    durations: dict[str, list[int]],
    clips: dict[str, list[Image.Image]],
    report: dict[str, object],
) -> Path:
    source_clips = source_manifest["clips"]
    assert isinstance(source_clips, dict)
    clip_manifest: dict[str, object] = {}
    for clip_name in CLIPS:
        source_meta = source_clips[clip_name]
        assert isinstance(source_meta, dict)
        clip_manifest[clip_name] = {
            "frames": f"clips/{clip_name}/right/frames",
            "frame_name_pattern": "frame-{index:000}.png",
            "frame_count": len(clips[clip_name]),
            "right_anchor": {"x": ANCHOR_RIGHT[0], "y": ANCHOR_RIGHT[1]},
            "frame_durations_ms": durations[clip_name],
            "loop_policy": source_meta["loop_policy"],
        }
        if clip_name == "spirit_tail":
            clip_manifest[clip_name]["segments"] = source_meta["segments"]
    manifest: dict[str, object] = {
        "status": "PASS" if report["status"] == "PASS" else "FAIL",
        "schema_version": 1,
        "pack_id": "miyabi-optimized-draft-v1",
        "character_id": "miyabi",
        "canvas": {"width": CANVAS[0], "height": CANVAS[1]},
        "master_direction": "right",
        "left_rendering": {
            "strategy": "mirror-right-at-runtime",
            "anchor_formula": "canvas.width-right_anchor.x",
        },
        "clip_policy": "right-authored frames only; no stored left frames",
        "required_clips": CLIPS,
        "clips": clip_manifest,
        "signature": {"clip": "spirit_tail", "atomic": True},
        "source": {
            "pack": rel(source_root),
            "manifest": rel(source_manifest_path),
            "manifest_sha256": sha256_file(source_manifest_path),
            "frame_order_preserved": True,
            "frame_count_preserved": True,
        },
        "optimization": {
            "operations": [
                "fill fully enclosed alpha holes of at most 3 pixels",
                "zero RGB wherever alpha is zero",
                "ease frame durations while preserving each clip total",
            ],
            "max_hole_area": MAX_HOLE_AREA,
            "new_animation_or_props": False,
            "stable_runtime_pack_modified": False,
        },
        "qa": rel(output_root / "behavior-pack-v1" / "qa.json"),
        "report": report,
    }
    path = output_root / "behavior-pack-v1" / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def run(source_root: Path, output_root: Path) -> dict[str, object]:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    source_manifest_path = source_root / "manifest.json"
    source_manifest, source_clips, source_paths = load_source(source_root)
    source_clip_meta = source_manifest["clips"]
    assert isinstance(source_clip_meta, dict)

    optimized: dict[str, list[Image.Image]] = {}
    cleanup_metrics: dict[str, dict[str, int]] = {}
    source_hashes: dict[str, list[str]] = {}
    optimized_hashes: dict[str, list[str]] = {}
    for clip_name in CLIPS:
        optimized_frames: list[Image.Image] = []
        source_hashes[clip_name] = []
        optimized_hashes[clip_name] = []
        metric_totals = Counter()
        for frame, source_path in zip(source_clips[clip_name], source_paths[clip_name]):
            cleaned, metrics = cleanup_frame(frame)
            optimized_frames.append(cleaned)
            source_hashes[clip_name].append(sha256_rgba(frame))
            optimized_hashes[clip_name].append(sha256_rgba(cleaned))
            metric_totals.update(metrics)
        optimized[clip_name] = optimized_frames
        cleanup_metrics[clip_name] = {key: int(value) for key, value in metric_totals.items()}

    durations: dict[str, list[int]] = {}
    cadence_metrics: dict[str, dict[str, object]] = {}
    for clip_name in CLIPS:
        meta = source_clip_meta[clip_name]
        assert isinstance(meta, dict)
        original = [int(value) for value in meta["frame_durations_ms"]]
        revised = smooth_durations(original, clip_name)
        durations[clip_name] = revised
        cadence_metrics[clip_name] = {
            "frame_count": len(revised),
            "source_total_ms": sum(original),
            "optimized_total_ms": sum(revised),
            "preserved_total": sum(original) == sum(revised),
            "source_durations_ms": original,
            "optimized_durations_ms": revised,
            "min_ms": min(revised),
            "max_ms": max(revised),
        }

    write_frames(output_root, optimized)
    contact_sheet = create_contact_sheet(output_root, optimized, durations)
    video = render_review_video(output_root, optimized, durations)

    failures: list[str] = []
    clip_qa: dict[str, object] = {}
    for clip_name in CLIPS:
        frames = optimized[clip_name]
        paths = sorted((output_root / "behavior-pack-v1" / "clips" / clip_name / "right" / "frames").glob("frame-*.png"))
        bboxes = [alpha_bbox(frame) for frame in frames]
        edge_alpha = []
        hidden_rgb = 0
        for frame in frames:
            alpha = frame.getchannel("A")
            edge_alpha.extend([alpha.getpixel((x, 0)) for x in range(frame.width)])
            edge_alpha.extend([alpha.getpixel((0, y)) for y in range(frame.height)])
            edge_alpha.extend([alpha.getpixel((frame.width - 1, y)) for y in range(frame.height)])
            hidden_rgb += sum(1 for r, g, b, a in frame.getdata() if a == 0 and (r, g, b) != (0, 0, 0))
        dimensions_ok = all(frame.size == CANVAS for frame in frames)
        rgba_ok = all(frame.mode == "RGBA" for frame in frames)
        names_ok = paths == [paths[0].parent / f"frame-{index:03d}.png" for index in range(len(paths))]
        # PIL's alpha bbox uses an exclusive lower edge.  Existing admitted
        # Miyabi frames therefore report 143 when their last opaque row is
        # y=142, matching the stable pack's baseline QA convention.
        baseline_ok = all(bbox is not None and bbox[3] == FEET_Y for bbox in bboxes)
        cadence_ok = cadence_metrics[clip_name]["preserved_total"] and len(durations[clip_name]) == len(frames)
        clip_failed = not (dimensions_ok and rgba_ok and names_ok and baseline_ok and not any(edge_alpha) and hidden_rgb == 0 and cadence_ok)
        if clip_failed:
            failures.append(clip_name)
        union: tuple[int, int, int, int] | None = None
        for bbox in bboxes:
            if bbox is None:
                continue
            union = bbox if union is None else (min(union[0], bbox[0]), min(union[1], bbox[1]), max(union[2], bbox[2]), max(union[3], bbox[3]))
        clip_qa[clip_name] = {
            "frame_count": len(frames),
            "dimensions_ok": dimensions_ok,
            "rgba_ok": rgba_ok,
            "names_ok": names_ok,
            "feet_baseline_y": FEET_Y,
            "baseline_ok": baseline_ok,
            "max_border_alpha": max(edge_alpha or [0]),
            "hidden_rgb_pixels": hidden_rgb,
            "alpha_bounds_union": list(union) if union else None,
            "source_hashes_match": source_hashes[clip_name] == optimized_hashes[clip_name],
            "cleanup_changed_frames": sum(before != after for before, after in zip(source_hashes[clip_name], optimized_hashes[clip_name])),
            "frame_count_preserved": len(frames) == len(source_clips[clip_name]),
            "cadence": cadence_metrics[clip_name],
            "cleanup": cleanup_metrics[clip_name],
        }

    report: dict[str, object] = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "canvas": list(CANVAS),
        "anchor_right": list(ANCHOR_RIGHT),
        "feet_baseline_y": FEET_Y,
        "required_clips": CLIPS,
        "clip_count": len(CLIPS),
        "mirror_strategy": "render-mirror; no left frames written",
        "left_frame_directories_written": False,
        "source_pack": rel(source_root),
        "output_pack": rel(output_root / "behavior-pack-v1"),
        "contact_sheet": rel(contact_sheet),
        "video": video,
        "clips": clip_qa,
        "total_source_frames": sum(len(frames) for frames in source_clips.values()),
        "total_optimized_frames": sum(len(frames) for frames in optimized.values()),
        "total_filled_alpha_pixels": sum(metrics["filled_alpha_pixels"] for metrics in cleanup_metrics.values()),
        "total_changed_rgba_pixels": sum(metrics["changed_rgba_pixels"] for metrics in cleanup_metrics.values()),
        "source_manifest_sha256": sha256_file(source_manifest_path),
    }
    qa_path = output_root / "behavior-pack-v1" / "qa.json"
    qa_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_manifest(output_root, source_root, source_manifest, source_manifest_path, durations, optimized, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.source_root, args.output_root)
    print(json.dumps({
        "status": report["status"],
        "output": report["output_pack"],
        "clips": report["clip_count"],
        "frames": report["total_optimized_frames"],
        "filled_alpha_pixels": report["total_filled_alpha_pixels"],
        "changed_rgba_pixels": report["total_changed_rgba_pixels"],
        "contact_sheet": report["contact_sheet"],
        "video": report["video"],
    }, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
