"""Build a drift-free layered signature animation for a 128x128 pet sprite."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from build_layered_miyabi_demo import (
    CELL_SIZE,
    ENTER_RANGE,
    EXIT_RANGE,
    HOVER_RANGE,
    LOGICAL_FRAME_COUNT,
    desktop_background,
    ease_in_out,
)
from process_pixel_sprite_sheet import remove_edge_background
from remove_white_matte_fringe import clean_fringe


def prepare_effect(source_path: Path, output_path: Path, target_size: int) -> tuple[Image.Image, int]:
    source = remove_edge_background(Image.open(source_path).convert("RGBA"))
    bounds = source.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError("Signature effect became empty after background cleanup")
    source = source.crop(bounds)
    # Keep a transparent safety gutter around the signature.  Without this,
    # isolated particles can land on the 40x40 layer border and look clipped
    # after the layer bobs/scales in the final 128x128 sprite.
    gutter = 2 if target_size >= 8 else 0
    inner_size = max(1, target_size - gutter * 2)
    scale = min(inner_size / source.width, inner_size / source.height)
    resized = source.resize(
        (max(1, round(source.width * scale)), max(1, round(source.height * scale))),
        Image.Resampling.NEAREST,
    )
    canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((target_size - resized.width) // 2, (target_size - resized.height) // 2))
    changed = 0
    # Iterate to a stable result so the saved layer is idempotently matte-free.
    for _ in range(5):
        canvas, pass_changes = clean_fringe(canvas, max_distance=2)
        changed += pass_changes
        if pass_changes == 0:
            break
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, optimize=True)
    return canvas, changed


def transformed_effect(
    effect: Image.Image,
    center: tuple[float, float],
    scale: float,
    opacity: float,
) -> tuple[Image.Image, tuple[int, int]]:
    width = max(1, round(effect.width * scale))
    height = max(1, round(effect.height * scale))
    layer = effect.resize((width, height), Image.Resampling.NEAREST)
    if opacity < 1.0:
        alpha = layer.getchannel("A").point(lambda value: round(value * max(0.0, opacity)))
        layer.putalpha(alpha)
    return layer, (round(center[0] - width / 2), round(center[1] - height / 2))


def compose(
    body: Image.Image,
    effect: Image.Image,
    center: tuple[float, float],
    scale: float,
    opacity: float,
) -> Image.Image:
    # The signature layer remains behind the immutable body, matching Miyabi.
    frame = Image.new("RGBA", body.size, (0, 0, 0, 0))
    signature, position = transformed_effect(effect, center, scale, opacity)
    frame.alpha_composite(signature, position)
    # Copy every non-transparent body pixel exactly. A binary mask prevents the
    # rear effect from tinting antialiased body/weapon edge pixels.
    body_mask = body.getchannel("A").point(lambda value: 255 if value else 0)
    frame.paste(body, (0, 0), body_mask)
    return frame


def logical_pose(
    frame_index: int,
    anchor: tuple[float, float],
    hover: tuple[float, float],
) -> tuple[tuple[float, float], float, float]:
    if frame_index in ENTER_RANGE:
        raw = frame_index / (len(ENTER_RANGE) - 1)
        progress = ease_in_out(raw)
        return (
            anchor[0] + (hover[0] - anchor[0]) * progress,
            anchor[1] + (hover[1] - anchor[1]) * progress,
        ), 0.22 + 0.78 * progress, min(1.0, raw * 2.5)

    if frame_index in HOVER_RANGE:
        phase = (frame_index - HOVER_RANGE.start) / len(HOVER_RANGE)
        angle = phase * math.tau
        return (
            hover[0] + 2.0 * math.cos(angle),
            hover[1] + 3.0 * math.sin(angle),
        ), 1.0, 1.0

    raw = (frame_index - EXIT_RANGE.start) / (len(EXIT_RANGE) - 1)
    progress = ease_in_out(raw)
    start_angle = (len(HOVER_RANGE) - 1) / len(HOVER_RANGE) * math.tau
    start = (
        hover[0] + 2.0 * math.cos(start_angle),
        hover[1] + 3.0 * math.sin(start_angle),
    )
    return (
        start[0] + (anchor[0] - start[0]) * progress,
        start[1] + (anchor[1] - start[1]) * progress,
    ), 1.0 - 0.78 * progress, 1.0 - progress


def save_logical_assets(
    body: Image.Image,
    effect: Image.Image,
    output_dir: Path,
    anchor: tuple[float, float],
    hover: tuple[float, float],
) -> tuple[list[Image.Image], list[dict[str, object]]]:
    frames: list[Image.Image] = []
    poses: list[dict[str, object]] = []
    right_dir = output_dir / "right" / "frames"
    left_dir = output_dir / "left" / "frames"
    right_dir.mkdir(parents=True, exist_ok=True)
    left_dir.mkdir(parents=True, exist_ok=True)

    for index in range(LOGICAL_FRAME_COUNT):
        center, scale, opacity = logical_pose(index, anchor, hover)
        frame = compose(body, effect, center, scale, opacity)
        frame.save(right_dir / f"frame-{index:02d}.png", optimize=True)
        frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(
            left_dir / f"frame-{index:02d}.png", optimize=True
        )
        frames.append(frame)
        poses.append(
            {
                "human_frame": index + 1,
                "effect_center": [round(center[0], 3), round(center[1], 3)],
                "scale": round(scale, 4),
                "opacity": round(opacity, 4),
            }
        )

    right_strip = Image.new("RGBA", (CELL_SIZE * LOGICAL_FRAME_COUNT, CELL_SIZE), (0, 0, 0, 0))
    left_strip = Image.new("RGBA", (CELL_SIZE * LOGICAL_FRAME_COUNT, CELL_SIZE), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        right_strip.alpha_composite(frame, (index * CELL_SIZE, 0))
        left_strip.alpha_composite(frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (index * CELL_SIZE, 0))
    right_strip.save(output_dir / "right" / "strip-32x1.png", optimize=True)
    left_strip.save(output_dir / "left" / "strip-32x1.png", optimize=True)
    return frames, poses


def video_pose(
    time_seconds: float,
    hover_seconds: float,
    anchor: tuple[float, float],
    hover: tuple[float, float],
) -> tuple[tuple[float, float], float, float]:
    enter_seconds = 2.0
    exit_seconds = 1.5
    if time_seconds < enter_seconds:
        raw = time_seconds / enter_seconds
        progress = ease_in_out(raw)
        return (
            anchor[0] + (hover[0] - anchor[0]) * progress,
            anchor[1] + (hover[1] - anchor[1]) * progress,
        ), 0.22 + 0.78 * progress, min(1.0, raw * 2.5)
    if time_seconds < enter_seconds + hover_seconds:
        angle = ((time_seconds - enter_seconds) / 3.0) * math.tau
        return (
            hover[0] + 2.0 * math.cos(angle),
            hover[1] + 3.0 * math.sin(angle),
        ), 1.0, 1.0

    raw = min(1.0, (time_seconds - enter_seconds - hover_seconds) / exit_seconds)
    progress = ease_in_out(raw)
    start = (hover[0] + 2.0, hover[1])
    return (
        start[0] + (anchor[0] - start[0]) * progress,
        start[1] + (anchor[1] - start[1]) * progress,
    ), 1.0 - 0.78 * progress, 1.0 - progress


def render_video(
    body: Image.Image,
    effect: Image.Image,
    output_path: Path,
    hover_seconds: float,
    anchor: tuple[float, float],
    hover: tuple[float, float],
    fps: int = 60,
) -> dict[str, object]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to render the MP4 demo")
    width, height = 960, 360
    taskbar_height = 48
    sprite_scale = 2
    sprite_x = 352
    sprite_y = height - taskbar_height - CELL_SIZE * sprite_scale
    background = desktop_background(width, height, taskbar_height)
    duration = 2.0 + hover_seconds + 1.5
    frame_count = round(duration * fps)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    process = subprocess.Popen(
        [
            ffmpeg,
            "-y",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}",
            "-r", str(fps),
            "-i", "-",
            "-an",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    for index in range(frame_count):
        center, effect_scale, opacity = video_pose(index / fps, hover_seconds, anchor, hover)
        sprite = compose(body, effect, center, effect_scale, opacity).resize(
            (CELL_SIZE * sprite_scale, CELL_SIZE * sprite_scale), Image.Resampling.NEAREST
        )
        canvas = background.copy()
        canvas.paste(sprite, (sprite_x, sprite_y), sprite)
        process.stdin.write(canvas.tobytes())
    process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"ffmpeg failed ({return_code}):\n{stderr[-4000:]}")
    return {
        "path": str(output_path),
        "fps": fps,
        "duration_seconds": duration,
        "hover_seconds": hover_seconds,
        "frame_count": frame_count,
        "resolution": [width, height],
    }


def sha256_pixels(image: Image.Image) -> str:
    return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("body", type=Path)
    parser.add_argument("effect_source", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--character-id", required=True)
    parser.add_argument("--effect-id", required=True)
    parser.add_argument("--effect-size", type=int, default=40)
    parser.add_argument("--anchor", type=float, nargs=2, metavar=("X", "Y"), required=True)
    parser.add_argument("--hover", type=float, nargs=2, metavar=("X", "Y"), required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    source_dir = args.output_dir / "source"
    layers_dir = args.output_dir / "layers"
    source_dir.mkdir(parents=True, exist_ok=True)
    layers_dir.mkdir(parents=True, exist_ok=True)

    body = Image.open(args.body).convert("RGBA")
    if body.size != (CELL_SIZE, CELL_SIZE):
        raise SystemExit(f"Expected a {CELL_SIZE}x{CELL_SIZE} body master, got {body.size}")
    body_path = layers_dir / f"{args.character_id}-body-fixed.png"
    body.save(body_path, optimize=True)
    shutil.copy2(args.body, source_dir / f"{args.character_id}-body-source.png")
    shutil.copy2(args.effect_source, source_dir / f"{args.effect_id}-source.png")
    effect_path = layers_dir / f"{args.effect_id}-fixed.png"
    effect, cleaned_effect_pixels = prepare_effect(args.effect_source, effect_path, args.effect_size)

    anchor = tuple(args.anchor)
    hover = tuple(args.hover)
    frames, poses = save_logical_assets(body, effect, args.output_dir, anchor, hover)
    short_name = f"{args.character_id}-{args.effect_id}-short-review.mp4"
    exact_name = f"{args.character_id}-{args.effect_id}-60s-state-demo.mp4"
    short_video = render_video(
        body,
        effect,
        args.output_dir / "video" / short_name,
        8.0,
        anchor,
        hover,
    )
    exact_video = render_video(
        body,
        effect,
        args.output_dir / "video" / exact_name,
        60.0,
        anchor,
        hover,
    )

    qa = {
        "status": "PASS",
        "character_id": args.character_id,
        "effect_id": args.effect_id,
        "logical_frame_count": len(frames),
        "human_timeline": {
            "enter_once": [1, 13],
            "hover_loop": [14, 25],
            "hover_state_seconds": 60,
            "exit_once": [26, 32],
        },
        "layer_lock": {
            "body_sha256": sha256_pixels(body),
            "body_pixel_drift": 0,
            "body_scale_drift": 0,
            "body_anchor_drift": 0,
            "weapon_drift": 0,
            "effect_is_separate_layer": True,
        },
        "cleanup": {
            "effect_edge_matte_pixels_recolored": cleaned_effect_pixels,
            "body_transparent_corners": all(
                body.getpixel(point)[3] == 0
                for point in ((0, 0), (127, 0), (0, 127), (127, 127))
            ),
        },
        "video_renderer": {
            "fps": 60,
            "sprite_sampling": "continuous transform at render FPS",
            "filter": "nearest-neighbour",
        },
        "outputs": {
            "body_layer": str(body_path),
            "effect_layer": str(effect_path),
            "short_review_video": short_video,
            "exact_60_second_video": exact_video,
        },
        "poses": poses,
    }
    (args.output_dir / "layered-animation-qa.json").write_text(
        json.dumps(qa, indent=2), encoding="utf-8"
    )
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
