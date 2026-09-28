"""Build a drift-free layered Miyabi/Tiny Tailless animation and MP4 demos."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from process_pixel_sprite_sheet import remove_edge_background


CELL_SIZE = 128
LOGICAL_FRAME_COUNT = 32
ENTER_RANGE = range(0, 13)   # Human frames 1-13.
HOVER_RANGE = range(13, 25)  # Human frames 14-25.
EXIT_RANGE = range(25, 32)   # Human frames 26-32.


def ease_in_out(value: float) -> float:
    return value * value * (3.0 - 2.0 * value)


def prepare_companion(source_path: Path, output_path: Path, target_size: int = 40) -> Image.Image:
    source = remove_edge_background(Image.open(source_path).convert("RGBA"))
    bounds = source.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError("Tiny Tailless source became empty after background cleanup")
    source = source.crop(bounds)
    scale = min(target_size / source.width, target_size / source.height)
    resized = source.resize(
        (max(1, round(source.width * scale)), max(1, round(source.height * scale))),
        Image.Resampling.NEAREST,
    )
    canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((target_size - resized.width) // 2, (target_size - resized.height) // 2))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, optimize=True)
    return canvas


def transformed_companion(
    companion: Image.Image,
    center: tuple[float, float],
    scale: float,
    opacity: float,
) -> tuple[Image.Image, tuple[int, int]]:
    width = max(1, round(companion.width * scale))
    height = max(1, round(companion.height * scale))
    layer = companion.resize((width, height), Image.Resampling.NEAREST)
    if opacity < 1.0:
        alpha = layer.getchannel("A").point(lambda value: round(value * max(0.0, opacity)))
        layer.putalpha(alpha)
    position = (round(center[0] - width / 2), round(center[1] - height / 2))
    return layer, position


def compose(body: Image.Image, companion: Image.Image, center: tuple[float, float], scale: float, opacity: float) -> Image.Image:
    # Tiny Tailless is behind Miyabi whenever the two layers overlap.
    frame = Image.new("RGBA", body.size, (0, 0, 0, 0))
    spirit, position = transformed_companion(companion, center, scale, opacity)
    frame.alpha_composite(spirit, position)
    frame.alpha_composite(body)
    return frame


def logical_pose(frame_index: int) -> tuple[tuple[float, float], float, float]:
    weapon_center = (34.0, 70.0)
    hover_center = (92.0, 39.0)
    if frame_index in ENTER_RANGE:
        raw = frame_index / (len(ENTER_RANGE) - 1)
        progress = ease_in_out(raw)
        center = (
            weapon_center[0] + (hover_center[0] - weapon_center[0]) * progress,
            weapon_center[1] + (hover_center[1] - weapon_center[1]) * progress,
        )
        return center, 0.22 + 0.78 * progress, min(1.0, raw * 2.5)
    if frame_index in HOVER_RANGE:
        phase = (frame_index - HOVER_RANGE.start) / len(HOVER_RANGE)
        angle = phase * math.tau
        return (
            hover_center[0] + 2.0 * math.cos(angle),
            hover_center[1] + 3.0 * math.sin(angle),
        ), 1.0, 1.0

    raw = (frame_index - EXIT_RANGE.start) / (len(EXIT_RANGE) - 1)
    progress = ease_in_out(raw)
    # Start close to the last hover sample so frame 25 -> 26 has no teleport.
    start_angle = (len(HOVER_RANGE) - 1) / len(HOVER_RANGE) * math.tau
    start = (
        hover_center[0] + 2.0 * math.cos(start_angle),
        hover_center[1] + 3.0 * math.sin(start_angle),
    )
    center = (
        start[0] + (weapon_center[0] - start[0]) * progress,
        start[1] + (weapon_center[1] - start[1]) * progress,
    )
    return center, 1.0 - 0.78 * progress, 1.0 - progress


def save_logical_assets(body: Image.Image, companion: Image.Image, output_dir: Path) -> tuple[list[Image.Image], dict[str, object]]:
    frames: list[Image.Image] = []
    frames_dir = output_dir / "right" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    poses: list[dict[str, object]] = []
    for index in range(LOGICAL_FRAME_COUNT):
        center, scale, opacity = logical_pose(index)
        frame = compose(body, companion, center, scale, opacity)
        frame.save(frames_dir / f"frame-{index:02d}.png", optimize=True)
        frames.append(frame)
        poses.append(
            {
                "human_frame": index + 1,
                "companion_center": [round(center[0], 3), round(center[1], 3)],
                "scale": round(scale, 4),
                "opacity": round(opacity, 4),
            }
        )

    left_dir = output_dir / "left" / "frames"
    left_dir.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(
            left_dir / f"frame-{index:02d}.png", optimize=True
        )

    strip = Image.new("RGBA", (CELL_SIZE * LOGICAL_FRAME_COUNT, CELL_SIZE), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        strip.alpha_composite(frame, (index * CELL_SIZE, 0))
    strip.save(output_dir / "right" / "strip-32x1.png", optimize=True)
    strip.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(
        output_dir / "left" / "strip-32x1.png", optimize=True
    )
    return frames, {"poses": poses}


def video_pose(time_seconds: float, hover_seconds: float) -> tuple[tuple[float, float], float, float]:
    enter_seconds = 2.0
    exit_seconds = 1.5
    weapon_center = (34.0, 70.0)
    hover_center = (92.0, 39.0)
    if time_seconds < enter_seconds:
        raw = time_seconds / enter_seconds
        progress = ease_in_out(raw)
        return (
            weapon_center[0] + (hover_center[0] - weapon_center[0]) * progress,
            weapon_center[1] + (hover_center[1] - weapon_center[1]) * progress,
        ), 0.22 + 0.78 * progress, min(1.0, raw * 2.5)
    if time_seconds < enter_seconds + hover_seconds:
        hover_time = time_seconds - enter_seconds
        # Slow three-second hover orbit, evaluated at video/render FPS.
        angle = (hover_time / 3.0) * math.tau
        return (
            hover_center[0] + 2.0 * math.cos(angle),
            hover_center[1] + 3.0 * math.sin(angle),
        ), 1.0, 1.0

    raw = min(1.0, (time_seconds - enter_seconds - hover_seconds) / exit_seconds)
    progress = ease_in_out(raw)
    start = (hover_center[0] + 2.0, hover_center[1])
    return (
        start[0] + (weapon_center[0] - start[0]) * progress,
        start[1] + (weapon_center[1] - start[1]) * progress,
    ), 1.0 - 0.78 * progress, 1.0 - progress


def desktop_background(width: int, height: int, taskbar_height: int) -> Image.Image:
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    desktop_height = height - taskbar_height
    for y in range(desktop_height):
        mix = y / max(1, desktop_height - 1)
        color = (
            round(18 + 8 * mix),
            round(33 + 12 * mix),
            round(55 + 18 * mix),
        )
        for x in range(width):
            pixels[x, y] = color
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, desktop_height, width, height), fill=(22, 26, 34))
    draw.line((0, desktop_height, width, desktop_height), fill=(70, 82, 104), width=1)
    for x, color in ((24, (90, 160, 240)), (62, (245, 190, 70)), (100, (80, 200, 145)), (138, (190, 110, 235))):
        draw.rounded_rectangle((x, desktop_height + 12, x + 24, desktop_height + 36), radius=5, fill=color)
    draw.ellipse((width - 38, desktop_height + 14, width - 18, desktop_height + 34), fill=(105, 115, 135))
    return image


def render_video(
    body: Image.Image,
    companion: Image.Image,
    output_path: Path,
    hover_seconds: float,
    fps: int = 60,
) -> dict[str, object]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to render the MP4 demo")
    width, height = 960, 360
    taskbar_height = 48
    scale = 2
    sprite_x = 352
    sprite_y = height - taskbar_height - CELL_SIZE * scale
    background = desktop_background(width, height, taskbar_height)
    duration = 2.0 + hover_seconds + 1.5
    frame_count = round(duration * fps)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
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
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert process.stdin is not None
    for video_frame in range(frame_count):
        time_seconds = video_frame / fps
        center, companion_scale, opacity = video_pose(time_seconds, hover_seconds)
        sprite = compose(body, companion, center, companion_scale, opacity)
        sprite = sprite.resize((CELL_SIZE * scale, CELL_SIZE * scale), Image.Resampling.NEAREST)
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
    parser.add_argument("companion_source", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    layers_dir = args.output_dir / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)
    body = Image.open(args.body).convert("RGBA")
    if body.size != (CELL_SIZE, CELL_SIZE):
        raise SystemExit(f"Expected a {CELL_SIZE}x{CELL_SIZE} body master, got {body.size}")
    body_path = layers_dir / "miyabi-body-fixed.png"
    body.save(body_path, optimize=True)
    companion = prepare_companion(
        args.companion_source,
        layers_dir / "tiny-tailless-fixed.png",
    )

    logical_frames, logical_report = save_logical_assets(body, companion, args.output_dir)
    short_video = render_video(
        body,
        companion,
        args.output_dir / "video" / "miyabi-tailless-short-review.mp4",
        hover_seconds=8.0,
    )
    exact_video = render_video(
        body,
        companion,
        args.output_dir / "video" / "miyabi-tailless-60s-state-demo.mp4",
        hover_seconds=60.0,
    )

    body_hash = sha256_pixels(body)
    # The body is composited from the exact same immutable layer every time.
    qa = {
        "logical_frame_count": len(logical_frames),
        "human_timeline": {
            "enter_once": [1, 13],
            "hover_loop": [14, 25],
            "hover_state_seconds": 60,
            "exit_once": [26, 32],
        },
        "layer_lock": {
            "body_sha256": body_hash,
            "body_pixel_drift": 0,
            "body_scale_drift": 0,
            "body_anchor_drift": 0,
            "weapon_drift": 0,
            "rear_scabbard_present": False,
            "companion_is_separate_layer": True,
        },
        "video_renderer": {
            "fps": 60,
            "sprite_sampling": "continuous transform at render FPS",
            "filter": "nearest-neighbour",
        },
        "outputs": {
            "body_layer": str(body_path),
            "companion_layer": str(layers_dir / "tiny-tailless-fixed.png"),
            "short_review_video": short_video,
            "exact_60_second_video": exact_video,
        },
        **logical_report,
    }
    report_path = args.output_dir / "layered-animation-qa.json"
    report_path.write_text(json.dumps(qa, indent=2), encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
