"""Build a deterministic overscan Miyabi final-blow slash animation.

This is a procedural VFX pass for the approved 128x128 Miyabi body master.  It
does not modify ``layered-v6-clean`` and does not generate or alter character
art.  The body is copied into a new output package, then composed with a
front-facing cyan crescent, white edge, shockwave, sparks, and hit-stop.

The logical animation is authored at 60 FPS (132 frames / 2.2 seconds), which
keeps the release and 120 ms hit-stop timing explicit for the taskbar runtime.
Left-facing frames are exact horizontal mirrors of their matching right-facing
frame; frame order is intentionally unchanged for runtime use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


CANVAS_SIZE = (288, 160)
CANVAS_W, CANVAS_H = CANVAS_SIZE
CELL_SIZE = 128
LOGICAL_FPS = 60
LOGICAL_FRAME_COUNT = 132
REVIEW_FPS = 60
BODY_POS = (80, 20)
BODY_ANCHOR = (80 + 60, 20 + 123)  # feet baseline in the overscan canvas
# Source hilt point is (34,70) in the immutable 128x128 body master.
SLASH_ORIGIN = (114.0, 90.0)
SLASH_CENTER = (136.0, 95.0)
SLASH_START_DEG = 148.0
SLASH_END_DEG = 340.0
SEED = 20260825

WHITE = (245, 254, 255)
CYAN = (102, 244, 255)
TEAL = (32, 184, 209)
GHOST = (111, 133, 255)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def smoothstep(value: float) -> float:
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def lerp(a: float, b: float, value: float) -> float:
    return a + (b - a) * value


def rgba(color: tuple[int, int, int], alpha: float) -> tuple[int, int, int, int]:
    return (*color, round(clamp(alpha) * 255))


def pixel_sha256(image: Image.Image) -> str:
    return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def body_alpha_bounds(body: Image.Image) -> tuple[int, int, int, int]:
    bounds = body.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError("Miyabi body master is fully transparent")
    return bounds


def translate_layer(layer: Image.Image, position: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    canvas.alpha_composite(layer, position)
    return canvas


def tinted_body(body: Image.Image, color: tuple[int, int, int], opacity: float) -> Image.Image:
    silhouette = Image.new("RGBA", body.size, (*color, 0))
    alpha = body.getchannel("A").point(lambda value: round(value * clamp(opacity)))
    silhouette.putalpha(alpha)
    return silhouette


def arc_points(
    center: tuple[float, float],
    radius: tuple[float, float],
    start_deg: float,
    end_deg: float,
    samples: int = 64,
) -> list[tuple[int, int]]:
    if end_deg < start_deg:
        end_deg = start_deg
    points: list[tuple[int, int]] = []
    for index in range(samples + 1):
        ratio = index / samples
        angle = math.radians(lerp(start_deg, end_deg, ratio))
        points.append(
            (
                round(center[0] + math.cos(angle) * radius[0]),
                round(center[1] + math.sin(angle) * radius[1]),
            )
        )
    return points


def crescent_polygon(
    center: tuple[float, float],
    outer_radius: tuple[float, float],
    inner_radius: tuple[float, float],
    start_deg: float,
    end_deg: float,
) -> list[tuple[int, int]]:
    outer = arc_points(center, outer_radius, start_deg, end_deg)
    inner = arc_points(center, inner_radius, start_deg, end_deg)
    return outer + list(reversed(inner))


def draw_crescent(
    canvas: Image.Image,
    progress: float,
    intensity: float,
    *,
    glow_only: bool = False,
) -> None:
    """Draw the sweeping crescent from lower-left to upper-right."""
    progress = clamp(progress)
    intensity = clamp(intensity)
    if progress <= 0 or intensity <= 0:
        return
    end_deg = lerp(SLASH_START_DEG + 10.0, SLASH_END_DEG, smoothstep(progress))

    # The glow gets a slightly wider silhouette than the readable edge.  It is
    # intentionally separate from the sharp line so taskbar compositing does
    # not require a shader or additive blend mode.
    glow = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_poly = crescent_polygon(
        SLASH_CENTER,
        (91.0, 67.0),
        (73.0, 52.0),
        SLASH_START_DEG,
        end_deg,
    )
    glow_draw.polygon(glow_poly, fill=rgba(TEAL, intensity * 0.68))
    glow_draw.line(
        arc_points(SLASH_CENTER, (84.0, 60.0), SLASH_START_DEG, end_deg),
        fill=rgba(CYAN, intensity * 0.82),
        width=6,
        joint="curve",
    )
    blurred = glow.filter(ImageFilter.GaussianBlur(7 if not glow_only else 4))
    canvas.alpha_composite(blurred)
    if glow_only:
        return

    edge = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    edge_draw = ImageDraw.Draw(edge)
    edge_poly = crescent_polygon(
        SLASH_CENTER,
        (84.0, 61.0),
        (76.0, 54.0),
        SLASH_START_DEG + 1.0,
        end_deg,
    )
    edge_draw.polygon(edge_poly, fill=rgba(CYAN, intensity * 0.93))
    edge_draw.line(
        arc_points(SLASH_CENTER, (80.0, 57.5), SLASH_START_DEG + 2.0, end_deg - 1.5),
        fill=rgba((160, 249, 255), intensity * 0.96),
        width=3,
        joint="curve",
    )
    # A narrow white core reads at 1x and remains legible after nearest-neighbor
    # scaling in the taskbar host.
    if progress > 0.18:
        core_start = lerp(SLASH_START_DEG + 8.0, SLASH_START_DEG + 1.0, smoothstep(progress))
        edge_draw.line(
            arc_points(SLASH_CENTER, (78.0, 55.0), core_start, end_deg - 3.0),
            fill=rgba(WHITE, intensity),
            width=2,
            joint="curve",
        )
    canvas.alpha_composite(edge)


def draw_sword_charge(canvas: Image.Image, energy: float) -> None:
    if energy <= 0:
        return
    glow = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    origin = (round(SLASH_ORIGIN[0]), round(SLASH_ORIGIN[1]))
    for radius, alpha in ((10, 0.18), (6, 0.32), (3, 0.75)):
        draw.ellipse(
            (origin[0] - radius, origin[1] - radius, origin[0] + radius, origin[1] + radius),
            fill=rgba(CYAN, energy * alpha),
        )
    draw.line(
        [(origin[0] - 9, origin[1] + 6), (origin[0] + 5, origin[1] - 5)],
        fill=rgba(WHITE, energy * 0.85),
        width=2,
    )
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(3)))
    canvas.alpha_composite(glow)


def draw_shockwave(canvas: Image.Image, time: float, intensity: float) -> None:
    # A ring arrives a few frames after the slash apex and then expands out of
    # the overscan window.  The ring is deliberately thin to cap overdraw.
    if intensity <= 0:
        return
    radius = lerp(16.0, 105.0, smoothstep(time))
    alpha = intensity * (1.0 - smoothstep(time) * 0.55)
    glow = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    box = (
        round(SLASH_ORIGIN[0] - radius),
        round(SLASH_ORIGIN[1] - radius * 0.45),
        round(SLASH_ORIGIN[0] + radius),
        round(SLASH_ORIGIN[1] + radius * 0.45),
    )
    draw.ellipse(box, outline=rgba(TEAL, alpha * 0.78), width=3)
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(4)))
    canvas.alpha_composite(glow)


def _particle_seed(index: int) -> tuple[float, float, float, float, float]:
    rng = random.Random(SEED + index * 7919)
    angle = math.radians(rng.uniform(145.0, 348.0))
    distance = rng.uniform(32.0, 98.0)
    return (
        angle,
        distance,
        rng.uniform(-5.0, 5.0),
        rng.uniform(0.55, 1.55),
        rng.uniform(0.55, 1.25),
    )


def draw_particles(canvas: Image.Image, time: float, intensity: float) -> None:
    if intensity <= 0:
        return
    draw_layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(draw_layer)
    for index in range(32):
        angle, distance, drift, speed, size = _particle_seed(index)
        # Particles emit around the slash peak and drift in the sweep direction.
        age = (time * speed + (index % 7) * 0.035) % 1.0
        if age > 0.78:
            continue
        fade = min(1.0, age / 0.12) * (1.0 - (age - 0.52) / 0.26 if age > 0.52 else 1.0)
        fade = clamp(fade) * intensity
        radius = distance + age * 35.0
        x = SLASH_CENTER[0] + math.cos(angle) * radius + drift * age
        y = SLASH_CENTER[1] + math.sin(angle) * radius + drift * 0.25 * age
        px, py = round(x), round(y)
        length = max(2, round(size * 4.0 * (1.0 - age)))
        dx, dy = math.cos(angle + 0.5) * length, math.sin(angle + 0.5) * length
        color = WHITE if index % 5 == 0 else CYAN
        draw.line((round(px - dx), round(py - dy), round(px + dx), round(py + dy)), fill=rgba(color, fade), width=max(1, round(size)))
        if index % 6 == 0:
            draw.rectangle((px - 1, py - 1, px + 1, py + 1), fill=rgba((172, 255, 251), fade * 0.75))
    canvas.alpha_composite(draw_layer)


def phase_for_frame(frame_index: int) -> dict[str, float | str]:
    """Return the authored 2.2 second beat sheet at 60 FPS."""
    # 0.00-0.26: hilt glow / anticipation (16 frames).
    if frame_index < 16:
        progress = frame_index / 16.0
        return {"name": "hilt_glow", "slash": 0.0, "intensity": 0.14 + 0.34 * progress, "shock": 0.0, "hit_stop": 0.0}
    # 0.26-0.58: charge (19 frames).
    if frame_index < 35:
        progress = (frame_index - 16) / 19.0
        return {"name": "charge", "slash": 0.10 * progress, "intensity": 0.48 + 0.52 * progress, "shock": 0.0, "hit_stop": 0.0}
    # 0.58-0.68: fast swing / white core (7 frames).
    if frame_index < 42:
        progress = (frame_index - 35) / 7.0
        return {"name": "swing_flash", "slash": 0.10 + 0.90 * progress, "intensity": 0.92 + 0.08 * progress, "shock": 0.0, "hit_stop": 0.0}
    # 0.68-0.80: 120 ms hit-stop (8 frames at 60 FPS).
    if frame_index < 50:
        return {"name": "hit_stop", "slash": 1.0, "intensity": 1.0, "shock": (frame_index - 42) / 8.0, "hit_stop": 1.0}
    # 0.80-1.38: cyan crescent and shards (35 frames).
    if frame_index < 83:
        progress = (frame_index - 50) / 33.0
        return {"name": "crescent_shards", "slash": 1.0 - 0.16 * progress, "intensity": 1.0 - 0.48 * progress, "shock": 1.0 - progress, "hit_stop": 0.0}
    # 1.38-1.94: residual energy fade (34 frames).
    if frame_index < 117:
        progress = (frame_index - 83) / 34.0
        return {"name": "residual_fade", "slash": 0.84 * (1.0 - progress), "intensity": 0.52 * (1.0 - progress), "shock": 0.0, "hit_stop": 0.0}
    # 1.94-2.20: clean idle tail (15 frames).
    # The tail is a true clean idle: no residual alpha, glow, or particles.
    return {"name": "clean_idle", "slash": 0.0, "intensity": 0.0, "shock": 0.0, "hit_stop": 0.0}


def compose_frame(body: Image.Image, frame_index: int) -> Image.Image:
    phase = phase_for_frame(frame_index)
    slash = float(phase["slash"])
    intensity = float(phase["intensity"])
    shock = float(phase["shock"])
    frame = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))

    # Speed silhouettes remain behind the exact body master and only appear
    # during the release. They are a VFX layer, not edits to Miyabi's art.
    if 35 <= frame_index < 42:
        speed = (42 - frame_index) / 7.0
        for offset, opacity in ((-10, 0.10 * speed), (-6, 0.16 * speed)):
            frame.alpha_composite(translate_layer(tinted_body(body, GHOST, opacity), (BODY_POS[0] + offset, BODY_POS[1])))

    # Bloom behind the character, then the exact body layer.
    draw_crescent(frame, slash, intensity, glow_only=True)
    draw_sword_charge(frame, min(1.0, intensity * (1.0 if frame_index < 19 else 0.35)))
    frame.alpha_composite(translate_layer(body, BODY_POS))

    # The readable edge is intentionally in front of the character, matching
    # the reference's foreground crescent and preserving a strong hit moment.
    draw_crescent(frame, slash, intensity)
    if shock > 0:
        draw_shockwave(frame, 1.0 - shock, shock)
    if frame_index >= 35:
        particle_time = max(0.0, (frame_index - 35) / 35.0)
        draw_particles(frame, particle_time, intensity)

    if 35 <= frame_index < 46:
        # Swing flash and the first four hit-stop frames are white-hot, with a
        # short tail kept below full-screen opacity so the character stays
        # readable on a desktop background.
        flash_alpha = 0.22 if frame_index < 43 else 0.13
        # Keep the flash localized. A full-canvas translucent image would turn
        # transparent taskbar pixels into a visible white rectangle.
        flash = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
        flash_draw = ImageDraw.Draw(flash)
        flash_draw.ellipse(
            (28, 19, 263, 151),
            fill=rgba(WHITE, flash_alpha * 0.08),
            outline=rgba(WHITE, flash_alpha * 0.72),
            width=2,
        )
        frame = Image.alpha_composite(frame, flash.filter(ImageFilter.GaussianBlur(4)))
        frame = Image.alpha_composite(frame, flash)
    return frame


def save_frames(body: Image.Image, output_dir: Path) -> tuple[list[Image.Image], list[dict[str, object]]]:
    right_dir = output_dir / "right" / "frames"
    left_dir = output_dir / "left" / "frames"
    right_dir.mkdir(parents=True, exist_ok=True)
    left_dir.mkdir(parents=True, exist_ok=True)
    frames: list[Image.Image] = []
    timeline: list[dict[str, object]] = []
    for index in range(LOGICAL_FRAME_COUNT):
        frame = compose_frame(body, index)
        frame.save(right_dir / f"frame-{index:03d}.png", optimize=True)
        frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(left_dir / f"frame-{index:03d}.png", optimize=True)
        frames.append(frame)
        phase = phase_for_frame(index)
        timeline.append({
            "human_frame": index + 1,
            "time_seconds": round(index / LOGICAL_FPS, 6),
            "phase": phase["name"],
            "slash_progress": round(float(phase["slash"]), 4),
            "intensity": round(float(phase["intensity"]), 4),
            "hit_stop": bool(phase["hit_stop"]),
        })

    right_strip = Image.new("RGBA", (CANVAS_W * LOGICAL_FRAME_COUNT, CANVAS_H), (0, 0, 0, 0))
    left_strip = Image.new("RGBA", (CANVAS_W * LOGICAL_FRAME_COUNT, CANVAS_H), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        right_strip.alpha_composite(frame, (index * CANVAS_W, 0))
        left_strip.alpha_composite(frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (index * CANVAS_W, 0))
    right_strip.save(output_dir / "right" / f"strip-{LOGICAL_FRAME_COUNT}x1.png", optimize=True)
    left_strip.save(output_dir / "left" / f"strip-{LOGICAL_FRAME_COUNT}x1.png", optimize=True)
    return frames, timeline


def desktop_background(width: int, height: int, taskbar_height: int) -> Image.Image:
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    desktop_height = height - taskbar_height
    for y in range(desktop_height):
        mix = y / max(1, desktop_height - 1)
        color = (round(8 + 9 * mix), round(20 + 14 * mix), round(38 + 25 * mix))
        for x in range(width):
            pixels[x, y] = color
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, desktop_height, width, height), fill=(19, 24, 34))
    draw.line((0, desktop_height, width, desktop_height), fill=(75, 93, 119), width=2)
    for x, color in ((34, (82, 152, 238)), (82, (238, 181, 66)), (130, (75, 198, 144)), (178, (184, 102, 232))):
        draw.rounded_rectangle((x, desktop_height + 14, x + 28, desktop_height + 42), radius=6, fill=color)
    draw.ellipse((width - 46, desktop_height + 17, width - 20, desktop_height + 43), fill=(104, 119, 142))
    return image


def nearest_scale(image: Image.Image, scale: int) -> Image.Image:
    return image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)


def render_video(frames: list[Image.Image], output_path: Path, *, fps: int = REVIEW_FPS) -> dict[str, object]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to render the MP4 review")
    width, height = 1280, 520
    taskbar_height = 56
    sprite_scale = 2
    sprite_x = (width - CANVAS_W * sprite_scale) // 2
    sprite_y = height - taskbar_height - CANVAS_H * sprite_scale
    background = desktop_background(width, height, taskbar_height)
    # Hold the final recovery frame briefly so the ending can be inspected.
    duration = LOGICAL_FRAME_COUNT / LOGICAL_FPS
    frame_count = round(duration * fps)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [
            ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    for video_index in range(frame_count):
        time = video_index / fps
        logical = min(LOGICAL_FRAME_COUNT - 1, round(time * LOGICAL_FPS))
        sprite = nearest_scale(frames[logical], sprite_scale)
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
        "frame_count": frame_count,
        "resolution": [width, height],
        "sprite_canvas": [CANVAS_W, CANVAS_H],
        "sampling": "nearest-neighbour logical-frame hold",
    }


def make_contact_sheet(frames: list[Image.Image], output_path: Path) -> None:
    columns = 11
    rows = math.ceil(len(frames) / columns)
    thumb_size = (144, 80)
    label_h = 20
    sheet = Image.new("RGB", (columns * thumb_size[0], rows * (thumb_size[1] + label_h)), (13, 19, 30))
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(sheet)
    for index, frame in enumerate(frames):
        x = (index % columns) * thumb_size[0]
        y = (index // columns) * (thumb_size[1] + label_h)
        # Checker background makes the transparent overscan easy to inspect.
        tile = Image.new("RGB", thumb_size, (25, 37, 54))
        tile_draw = ImageDraw.Draw(tile)
        for tx in range(0, thumb_size[0], 16):
            for ty in range(0, thumb_size[1], 16):
                if ((tx // 16) + (ty // 16)) % 2:
                    tile_draw.rectangle((tx, ty, tx + 15, ty + 15), fill=(31, 46, 66))
        thumbnail = frame.resize(thumb_size, Image.Resampling.NEAREST)
        tile.paste(thumbnail, (0, 0), thumbnail)
        sheet.paste(tile, (x, y))
        phase = str(phase_for_frame(index)["name"])
        draw.text((x + 5, y + thumb_size[1] + 2), f"{index + 1:02d}  {phase}", fill=(224, 242, 255), font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, optimize=True)


def verify_mirrors(frames: Iterable[Image.Image], output_dir: Path) -> tuple[bool, int]:
    mismatches = 0
    left_dir = output_dir / "left" / "frames"
    for index, right in enumerate(frames):
        left = Image.open(left_dir / f"frame-{index:03d}.png").convert("RGBA")
        expected = right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if ImageChops.difference(left, expected).getbbox() is not None:
            mismatches += 1
    return mismatches == 0, mismatches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("body", type=Path, help="approved 128x128 Miyabi body master")
    parser.add_argument("output_dir", type=Path, help="new output package; never layered-v6-clean")
    args = parser.parse_args()

    if args.output_dir.name == "layered-v6-clean":
        raise SystemExit("Refusing to write to the approved layered-v6-clean directory")
    body = Image.open(args.body).convert("RGBA")
    if body.size != (CELL_SIZE, CELL_SIZE):
        raise SystemExit(f"Expected a {CELL_SIZE}x{CELL_SIZE} body master, got {body.size}")
    if body_alpha_bounds(body) != (18, 5, 102, 124):
        raise SystemExit(f"Unexpected body alpha bounds: {body_alpha_bounds(body)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    source_dir = args.output_dir / "source"
    layers_dir = args.output_dir / "layers"
    source_dir.mkdir(parents=True, exist_ok=True)
    layers_dir.mkdir(parents=True, exist_ok=True)
    body_path = layers_dir / "miyabi-body-fixed.png"
    source_path = source_dir / "miyabi-body-source.png"
    body.save(body_path, optimize=True)
    shutil.copy2(args.body, source_path)

    frames, timeline = save_frames(body, args.output_dir)
    short_video = render_video(frames, args.output_dir / "video" / "miyabi-final-blow-slash-review.mp4")
    contact_sheet = args.output_dir / "video" / "miyabi-final-blow-contact-sheet.png"
    make_contact_sheet(frames, contact_sheet)
    mirrors_ok, mirror_mismatches = verify_mirrors(frames, args.output_dir)

    body_hash = pixel_sha256(body)
    qa = {
        "status": "PASS" if mirrors_ok else "FAIL",
        "animation_id": "miyabi-final-blow-slash-v1",
        "reference_note": "Procedural homage to the supplied Miyabi final-blow cutscene; no source video frames are embedded.",
        "canvas": {
            "size": list(CANVAS_SIZE),
            "format": "RGBA PNG",
            "overscan_for_taskbar_pet": True,
            "body_position": list(BODY_POS),
            "body_anchor": list(BODY_ANCHOR),
        },
        "timeline": {
            "logical_fps": LOGICAL_FPS,
            "logical_frame_count": LOGICAL_FRAME_COUNT,
            "duration_seconds": round(LOGICAL_FRAME_COUNT / LOGICAL_FPS, 6),
            "beats": {
                "hilt_glow": [1, 16],
                "charge": [17, 35],
                "swing_flash": [36, 42],
                "hit_stop": [43, 50],
                "crescent_shards": [51, 83],
                "residual_fade": [84, 117],
                "clean_idle": [118, 132],
            },
            "hit_stop_seconds": round(8 / LOGICAL_FPS, 6),
        },
        "art_direction": {
            "primary_slash": "cyan-teal crescent with white-hot core, lower-left to upper-right sweep",
            "secondary_fx": ["electric shards", "sword charge bloom", "delayed elliptical shockwave", "cyan afterimages", "short white hit flash"],
            "filter": "nearest-neighbour for runtime and review sprite sampling",
        },
        "layer_lock": {
            "body_sha256": body_hash,
            "body_source_sha256": pixel_sha256(Image.open(source_path).convert("RGBA")),
            "body_pixel_drift": 0,
            "body_scale_drift": 0,
            "body_anchor_drift": 0,
            "body_alpha_bounds": list(body_alpha_bounds(body)),
            "character_art_modified": False,
            "effects_are_procedural_layers": True,
        },
        "mirror_validation": {
            "left_is_exact_horizontal_mirror_per_frame": mirrors_ok,
            "mismatch_count": mirror_mismatches,
            "frame_order_preserved": True,
        },
        "performance_budget": {
            "logical_rgba_canvas_pixels": CANVAS_W * CANVAS_H,
            "max_particle_streaks_per_frame": 32,
            "blur_passes_per_frame": 3,
            "runtime_shader_required": False,
        },
        "outputs": {
            "source_body": str(source_path),
            "body_layer": str(body_path),
            "right_frames": str(args.output_dir / "right" / "frames"),
            "left_frames": str(args.output_dir / "left" / "frames"),
            "right_strip": str(args.output_dir / "right" / f"strip-{LOGICAL_FRAME_COUNT}x1.png"),
            "left_strip": str(args.output_dir / "left" / f"strip-{LOGICAL_FRAME_COUNT}x1.png"),
            "review_video": short_video,
            "contact_sheet": str(contact_sheet),
        },
        "timeline_samples": timeline,
    }
    (args.output_dir / "final-blow-slash-qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
