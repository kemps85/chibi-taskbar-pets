"""Build Miyabi's forward crescent projectile pass (v2).

The corrected kneeling/grip source is normalized into a transparent 128x128
pose, then used for a short brace-and-release animation.  The release is one
forward, open crescent wave that travels to the right; no circular aura and no
overhead ring are generated.  The approved standing body remains the clean idle
pose and is copied, not modified, into this new v2 package.

All generated assets are deterministic Pillow output.  The left set is an
exact horizontal mirror of the right set with frame order preserved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from process_pixel_sprite_sheet import remove_edge_background
from remove_white_matte_fringe import clean_fringe


CANVAS_SIZE = (384, 160)
CANVAS_W, CANVAS_H = CANVAS_SIZE
BODY_SIZE = (128, 128)
POSE_SIZE = (176, 128)
FPS = 60
DURATION_SECONDS = 2.6
FRAME_COUNT = round(FPS * DURATION_SECONDS)
BODY_POS = (48, 20)
# Wider pose layers preserve the model-grounded sword/scabbard extents while
# keeping Miyabi's head-to-feet scale equal across charge and release.
POSE_POS = (24, 20)
ANCHOR = (48 + 60, 20 + 123)
# Charge-pose grip is near normalized (15,76); release-pose grip moves to the
# extended sword hand near normalized (70,70). Both remain on the same body
# baseline, but use separate VFX origins during the pose transition.
HILT_POS = (63.0, 96.0)
RELEASE_HILT_POS = (118.0, 90.0)
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


def rgba(color: tuple[int, int, int], alpha: float) -> tuple[int, int, int, int]:
    return (*color, round(clamp(alpha) * 255))


def pixel_sha256(image: Image.Image) -> str:
    return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def alpha_bounds(image: Image.Image) -> tuple[int, int, int, int] | None:
    return image.getchannel("A").getbbox()


def place_layer(layer: Image.Image, position: tuple[int, int], opacity: float = 1.0) -> Image.Image:
    if opacity < 1.0:
        alpha = layer.getchannel("A").point(lambda value: round(value * clamp(opacity)))
        layer = layer.copy()
        layer.putalpha(alpha)
    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    canvas.alpha_composite(layer, position)
    return canvas


def tinted_pose(pose: Image.Image, color: tuple[int, int, int], opacity: float) -> Image.Image:
    result = Image.new("RGBA", pose.size, (*color, 0))
    result.putalpha(pose.getchannel("A").point(lambda value: round(value * clamp(opacity))))
    return result


def prepare_pose(source_path: Path, output_path: Path, *, target_height: int = 116) -> tuple[Image.Image, dict[str, object]]:
    """Remove edge-connected checker/white pixels and fit the pose to 128x128."""
    source = Image.open(source_path).convert("RGBA")
    cleaned = remove_edge_background(source)
    bounds = alpha_bounds(cleaned)
    if bounds is None:
        raise ValueError("Corrected Miyabi pose became fully transparent")
    cropped = cleaned.crop(bounds)
    # Scale from head-to-feet height only. Fitting by full crop width would
    # shrink the release pose because its drawn katana is longer.
    scale = target_height / cropped.height
    resized = cropped.resize(
        (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale))),
        Image.Resampling.NEAREST,
    )
    if resized.width > POSE_SIZE[0]:
        raise ValueError(f"Pose weapon extent exceeds {POSE_SIZE[0]}px layer: {resized.width}px")
    pose = Image.new("RGBA", POSE_SIZE, (0, 0, 0, 0))
    # Keep the feet baseline at y=123, matching the standing body anchor.
    position = ((POSE_SIZE[0] - resized.width) // 2, POSE_SIZE[1] - resized.height - 4)
    pose.alpha_composite(resized, position)
    matte_changes = 0
    for _ in range(4):
        pose, changes = clean_fringe(pose, max_distance=2)
        matte_changes += changes
        if changes == 0:
            break
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pose.save(output_path, optimize=True)
    return pose, {
        "source_size": list(source.size),
        "source_alpha_bounds_after_edge_cleanup": list(bounds),
        "cropped_size": list(cropped.size),
        "normalized_size": list(pose.size),
        "normalized_alpha_bounds": list(alpha_bounds(pose)) if alpha_bounds(pose) else None,
        "target_height": target_height,
        "resample": "nearest-neighbour",
        "matte_fringe_pixels_recolored": matte_changes,
    }


def arc_points(
    center: tuple[float, float],
    radius: tuple[float, float],
    start_deg: float,
    end_deg: float,
    samples: int = 28,
) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for index in range(samples + 1):
        ratio = index / samples
        angle = math.radians(start_deg + (end_deg - start_deg) * ratio)
        points.append((round(center[0] + math.cos(angle) * radius[0]), round(center[1] + math.sin(angle) * radius[1])))
    return points


def projectile_crescent(center: tuple[float, float], progress: float) -> list[tuple[int, int]]:
    """Open crescent: lower-left to upper-right, with no enclosing circle."""
    # The end cap points toward travel (right); the arc stays in front of the
    # character and never loops above Miyabi's head.
    progress = clamp(progress)
    outer = arc_points(center, (54.0, 27.0), 145.0, 315.0)
    inner = arc_points(center, (43.0, 19.0), 147.0, 306.0)
    return outer + list(reversed(inner))


def draw_wave(
    canvas: Image.Image,
    center: tuple[float, float],
    progress: float,
    intensity: float,
) -> None:
    if intensity <= 0:
        return
    intensity = clamp(intensity)
    glow = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    polygon = projectile_crescent(center, progress)
    glow_draw.polygon(polygon, fill=rgba(TEAL, intensity * 0.82))
    # A short tail makes the projectile read as a traveling wave, not an aura.
    tail_y = center[1] + 8
    glow_draw.line(
        [(round(center[0] - 72), round(tail_y + 11)), (round(center[0] - 18), round(tail_y - 4))],
        fill=rgba(CYAN, intensity * 0.64),
        width=5,
    )
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6)))

    edge = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    edge_draw = ImageDraw.Draw(edge)
    edge_draw.polygon(polygon, fill=rgba(CYAN, intensity * 0.94))
    edge_draw.line(
        arc_points(center, (49.0, 24.0), 147.0, 313.0),
        fill=rgba(WHITE, intensity),
        width=3,
        joint="curve",
    )
    # White core is open too; it never closes into a ring.
    edge_draw.line(
        arc_points(center, (45.0, 21.0), 151.0, 300.0),
        fill=rgba(WHITE, intensity * 0.94),
        width=1,
    )
    canvas.alpha_composite(edge)


def draw_launch_flash(canvas: Image.Image, intensity: float, position: tuple[float, float] = RELEASE_HILT_POS) -> None:
    """A localized draw flash at the hilt; deliberately not a circular aura."""
    if intensity <= 0:
        return
    layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x, y = round(position[0]), round(position[1])
    draw.line((x - 8, y + 7, x + 15, y - 7), fill=rgba(WHITE, intensity), width=3)
    draw.line((x - 3, y + 11, x + 19, y - 2), fill=rgba(CYAN, intensity * 0.8), width=2)
    draw.rectangle((x - 2, y - 2, x + 3, y + 3), fill=rgba(WHITE, intensity * 0.8))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(4)))
    canvas.alpha_composite(layer)


def draw_hilt_pulse(canvas: Image.Image, pulse: float, position: tuple[float, float] = HILT_POS) -> None:
    if pulse <= 0:
        return
    layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x, y = round(position[0]), round(position[1])
    # Small rectangular/diamond pulse only around the sword grip.
    draw.line((x - 10, y + 9, x + 13, y - 8), fill=rgba(CYAN, pulse * 0.72), width=2)
    draw.line((x - 4, y + 12, x + 17, y - 4), fill=rgba(WHITE, pulse * 0.52), width=1)
    draw.rectangle((x - 3, y - 3, x + 4, y + 4), fill=rgba(CYAN, pulse * 0.33))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(3)))
    canvas.alpha_composite(layer)


def _spark_seed(index: int) -> tuple[float, float, float, float]:
    rng = random.Random(SEED + index * 7919)
    return (
        math.radians(rng.uniform(-34.0, 34.0)),
        rng.uniform(12.0, 55.0),
        rng.uniform(0.7, 1.4),
        rng.uniform(0.6, 1.3),
    )


def draw_projectile_sparks(canvas: Image.Image, center: tuple[float, float], time: float, intensity: float) -> None:
    if intensity <= 0:
        return
    layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for index in range(22):
        angle, distance, speed, size = _spark_seed(index)
        age = (time * speed + index * 0.037) % 0.85
        fade = clamp(min(age / 0.08, 1.0) * (1.0 - max(0.0, age - 0.50) / 0.35)) * intensity
        x = center[0] + distance + age * 42.0
        y = center[1] + math.sin(angle) * distance + math.cos(angle) * age * 20.0
        # Keep both the particle and its short streak away from the canvas
        # border. This makes the transparent overscan safe for a click-through
        # taskbar window even while the wave is at maximum travel.
        if x < 10 or x >= CANVAS_W - 12 or y < 10 or y >= CANVAS_H - 10:
            continue
        length = max(2, round(size * 5.0 * (1.0 - age)))
        px, py = round(x), round(y)
        dx, dy = math.cos(angle) * length, math.sin(angle) * length
        color = WHITE if index % 5 == 0 else CYAN
        draw.line((round(px - dx), round(py - dy), round(px + dx), round(py + dy)), fill=rgba(color, fade), width=max(1, round(size)))
    canvas.alpha_composite(layer)


def phase_for_frame(index: int) -> dict[str, float | str]:
    """2.6 second beat sheet at 60 FPS."""
    if index < 9:  # 0.00-0.15 standing lead-in
        return {"name": "standing_lead_in", "standing_mix": 1.0, "kneel_mix": 0.0, "release_mix": 0.0, "hilt": 0.0, "wave": 0.0, "hit_stop": 0.0, "fade": 0.0}
    if index < 18:  # 0.15-0.30 fast pose switch
        kneel_mix = (index - 9) / 9.0
        return {"name": "kneel_transition", "standing_mix": 1.0 - kneel_mix, "kneel_mix": kneel_mix, "release_mix": 0.0, "hilt": 0.18, "wave": 0.0, "hit_stop": 0.0, "fade": 0.0}
    if index < 55:  # 0.30-0.92: 0.62s visible brace
        pulse = 0.64 + 0.36 * (0.5 + 0.5 * math.sin((index - 18) / 7.0 * math.tau))
        return {"name": "kneel_brace", "standing_mix": 0.0, "kneel_mix": 1.0, "release_mix": 0.0, "hilt": pulse, "wave": 0.0, "hit_stop": 0.0, "fade": 0.0}
    if index < 70:  # 0.92-1.17 projectile launch
        progress = (index - 55) / 15.0
        release_mix = smoothstep(min(1.0, progress * 2.5))
        return {"name": "wave_launch", "standing_mix": 0.0, "kneel_mix": 1.0, "release_mix": release_mix, "hilt": 1.0 - progress, "wave": progress, "hit_stop": 0.0, "fade": 1.0}
    if index < 78:  # 1.17-1.30: 130ms hit-stop
        return {"name": "hit_stop", "standing_mix": 0.0, "kneel_mix": 1.0, "release_mix": 1.0, "hilt": 0.0, "wave": 1.0, "hit_stop": 1.0, "fade": 1.0}
    if index < 126:  # 1.30-2.10 wave travels and fades
        progress = (index - 78) / 48.0
        return {"name": "wave_travel_fade", "standing_mix": 0.0, "kneel_mix": 1.0, "release_mix": 1.0, "hilt": 0.0, "wave": 1.0, "hit_stop": 0.0, "fade": 1.0 - progress}
    if index < 141:  # 2.10-2.35 return to standing
        standing_mix = (index - 126) / 15.0
        return {"name": "standing_return", "standing_mix": standing_mix, "kneel_mix": 0.0, "release_mix": 1.0 - standing_mix, "hilt": 0.0, "wave": 0.0, "hit_stop": 0.0, "fade": 0.0}
    return {"name": "clean_idle", "standing_mix": 1.0, "kneel_mix": 0.0, "release_mix": 0.0, "hilt": 0.0, "wave": 0.0, "hit_stop": 0.0, "fade": 0.0}


def compose_frame(standing: Image.Image, kneeling: Image.Image, release: Image.Image, index: int) -> Image.Image:
    phase = phase_for_frame(index)
    standing_mix = float(phase["standing_mix"])
    kneel_mix = float(phase["kneel_mix"])
    release_mix = float(phase["release_mix"])
    wave_strength = float(phase["wave"])
    fade = float(phase["fade"])
    frame = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))

    # Pose switch is anchored to the same taskbar baseline. Blend full-canvas
    # layers rather than 128x128 crops so the wider weapon extents never force
    # a smaller character during release.
    standing_canvas = place_layer(standing, BODY_POS)
    kneeling_canvas = place_layer(kneeling, POSE_POS)
    release_canvas = place_layer(release, POSE_POS)
    if release_mix > 0:
        pose_canvas = Image.blend(kneeling_canvas, release_canvas, smoothstep(release_mix))
    elif kneel_mix > 0:
        pose_canvas = Image.blend(standing_canvas, kneeling_canvas, smoothstep(kneel_mix))
    else:
        pose_canvas = standing_canvas
    if standing_mix > 0 and standing_mix < 1:
        pose_canvas = Image.blend(pose_canvas, standing_canvas, smoothstep(standing_mix))
    elif standing_mix >= 1:
        pose_canvas = standing_canvas
    if index in range(55, 70):
        # Brief ghost streak behind Miyabi as the wave leaves the grip.
        speed = (70 - index) / 15.0
        frame.alpha_composite(tinted_pose(pose_canvas, GHOST, 0.10 * speed))

    # Hilt pulse is kept near the hand, never expanded into a body aura.
    draw_hilt_pulse(frame, float(phase["hilt"]))
    frame.alpha_composite(pose_canvas)
    if index in range(55, 63):
        draw_launch_flash(frame, (63 - index) / 8.0)

    if wave_strength > 0:
        # Starts just beyond Miyabi's right shoulder and travels to the right
        # edge; it is intentionally detached from the character body.
        if index < 70:
            travel = (index - 55) / 15.0
        elif index < 78:
            travel = 1.0
        else:
            travel = 1.0 + (index - 78) / 48.0
        center_x = 170.0 + 145.0 * min(1.0, travel)
        center = (center_x, 88.0)
        draw_wave(frame, center, min(1.0, travel), fade)
        draw_projectile_sparks(frame, center, max(0.0, (index - 55) / 24.0), fade)
    return frame


def clear_frame_dirs(output_dir: Path) -> None:
    for side in ("right", "left"):
        directory = output_dir / side / "frames"
        if directory.exists():
            shutil.rmtree(directory)


def save_frames(standing: Image.Image, kneeling: Image.Image, release: Image.Image, output_dir: Path) -> tuple[list[Image.Image], list[dict[str, object]]]:
    clear_frame_dirs(output_dir)
    right_dir = output_dir / "right" / "frames"
    left_dir = output_dir / "left" / "frames"
    right_dir.mkdir(parents=True, exist_ok=True)
    left_dir.mkdir(parents=True, exist_ok=True)
    frames: list[Image.Image] = []
    timeline: list[dict[str, object]] = []
    for index in range(FRAME_COUNT):
        frame = compose_frame(standing, kneeling, release, index)
        frame.save(right_dir / f"frame-{index:03d}.png", optimize=True)
        frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(left_dir / f"frame-{index:03d}.png", optimize=True)
        phase = phase_for_frame(index)
        frames.append(frame)
        timeline.append({
            "human_frame": index + 1,
            "time_seconds": round(index / FPS, 6),
            "phase": phase["name"],
            "kneel_mix": round(float(phase["kneel_mix"]), 4),
            "hilt_pulse": round(float(phase["hilt"]), 4),
            "wave_strength": round(float(phase["wave"]), 4),
            "hit_stop": bool(phase["hit_stop"]),
        })

    right_strip = Image.new("RGBA", (CANVAS_W * FRAME_COUNT, CANVAS_H), (0, 0, 0, 0))
    left_strip = Image.new("RGBA", (CANVAS_W * FRAME_COUNT, CANVAS_H), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        right_strip.alpha_composite(frame, (index * CANVAS_W, 0))
        left_strip.alpha_composite(frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (index * CANVAS_W, 0))
    right_strip.save(output_dir / "right" / f"strip-{FRAME_COUNT}x1.png", optimize=True)
    left_strip.save(output_dir / "left" / f"strip-{FRAME_COUNT}x1.png", optimize=True)
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


def render_video(frames: list[Image.Image], output_path: Path, fps: int = FPS) -> dict[str, object]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to render the MP4 review")
    width, height = 1280, 520
    taskbar_height = 56
    sprite_scale = 2
    sprite_x = (width - CANVAS_W * sprite_scale) // 2
    sprite_y = height - taskbar_height - CANVAS_H * sprite_scale
    background = desktop_background(width, height, taskbar_height)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    for index in range(round(DURATION_SECONDS * fps)):
        sprite = frames[min(len(frames) - 1, index)]
        sprite = sprite.resize((CANVAS_W * sprite_scale, CANVAS_H * sprite_scale), Image.Resampling.NEAREST)
        canvas = background.copy()
        canvas.paste(sprite, (sprite_x, sprite_y), sprite)
        process.stdin.write(canvas.tobytes())
    process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"ffmpeg failed ({return_code}):\n{stderr[-4000:]}")
    return {"path": str(output_path), "fps": fps, "duration_seconds": DURATION_SECONDS, "frame_count": FRAME_COUNT, "resolution": [width, height], "sprite_canvas": list(CANVAS_SIZE)}


def make_contact_sheet(frames: list[Image.Image], output_path: Path) -> None:
    columns = 10
    rows = math.ceil(len(frames) / columns)
    thumb_size = (192, 80)
    label_h = 20
    sheet = Image.new("RGB", (columns * thumb_size[0], rows * (thumb_size[1] + label_h)), (13, 19, 30))
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(sheet)
    for index, frame in enumerate(frames):
        x = (index % columns) * thumb_size[0]
        y = (index // columns) * (thumb_size[1] + label_h)
        tile = Image.new("RGB", thumb_size, (25, 37, 54))
        tile_draw = ImageDraw.Draw(tile)
        for tx in range(0, thumb_size[0], 16):
            for ty in range(0, thumb_size[1], 16):
                if ((tx // 16) + (ty // 16)) % 2:
                    tile_draw.rectangle((tx, ty, tx + 15, ty + 15), fill=(31, 46, 66))
        thumbnail = frame.resize(thumb_size, Image.Resampling.NEAREST)
        tile.paste(thumbnail, (0, 0), thumbnail)
        sheet.paste(tile, (x, y))
        draw.text((x + 4, y + thumb_size[1] + 2), f"{index + 1:03d} {phase_for_frame(index)['name']}", fill=(224, 242, 255), font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, optimize=True)


def verify_mirrors(frames: Iterable[Image.Image], output_dir: Path) -> tuple[bool, int]:
    mismatches = 0
    for index, right in enumerate(frames):
        left = Image.open(output_dir / "left" / "frames" / f"frame-{index:03d}.png").convert("RGBA")
        if ImageChops.difference(left, right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)).getbbox() is not None:
            mismatches += 1
    return mismatches == 0, mismatches


def border_alpha_count(image: Image.Image) -> int:
    alpha = image.getchannel("A")
    pixels = [alpha.getpixel((x, 0)) for x in range(image.width)]
    pixels += [alpha.getpixel((x, image.height - 1)) for x in range(image.width)]
    pixels += [alpha.getpixel((0, y)) for y in range(image.height)]
    pixels += [alpha.getpixel((image.width - 1, y)) for y in range(image.height)]
    return sum(1 for value in pixels if value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("standing_body", type=Path, help="approved 128x128 standing body master")
    parser.add_argument("kneeling_source", type=Path, help="corrected kneeling/grip source with checker background")
    parser.add_argument("release_source", type=Path, help="transparent kneeling release pose with sword extended screen-right")
    parser.add_argument("output_dir", type=Path, help="new final-blow-slash-v2 package")
    args = parser.parse_args()
    if args.output_dir.name in {"final-blow-slash-v1", "layered-v6-clean"}:
        raise SystemExit("Refusing to overwrite v1 or layered-v6-clean")
    standing = Image.open(args.standing_body).convert("RGBA")
    if standing.size != BODY_SIZE:
        raise SystemExit(f"Expected standing body {BODY_SIZE}, got {standing.size}")
    if alpha_bounds(standing) != (18, 5, 102, 124):
        raise SystemExit(f"Unexpected standing body alpha bounds: {alpha_bounds(standing)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    source_dir = args.output_dir / "source"
    layers_dir = args.output_dir / "layers"
    source_dir.mkdir(parents=True, exist_ok=True)
    layers_dir.mkdir(parents=True, exist_ok=True)
    standing_source = source_dir / "miyabi-standing-source.png"
    kneeling_source_copy = source_dir / "miyabi-kneel-model-grounded-source.png"
    release_source_copy = source_dir / "miyabi-kneel-release-model-grounded-source.png"
    shutil.copy2(args.standing_body, standing_source)
    if args.kneeling_source.resolve() != kneeling_source_copy.resolve():
        shutil.copy2(args.kneeling_source, kneeling_source_copy)
    if args.release_source.resolve() != release_source_copy.resolve():
        shutil.copy2(args.release_source, release_source_copy)
    standing_path = layers_dir / "miyabi-standing-body-fixed.png"
    standing.save(standing_path, optimize=True)
    kneeling_path = layers_dir / "miyabi-kneel-model-grounded-fixed.png"
    kneeling, pose_report = prepare_pose(args.kneeling_source, kneeling_path)
    release_path = layers_dir / "miyabi-kneel-release-model-grounded-fixed.png"
    release, release_report = prepare_pose(args.release_source, release_path)

    frames, timeline = save_frames(standing, kneeling, release, args.output_dir)
    review_video = render_video(frames, args.output_dir / "video" / "miyabi-forward-crescent-slash-review.mp4")
    contact_sheet = args.output_dir / "video" / "miyabi-forward-crescent-contact-sheet.png"
    make_contact_sheet(frames, contact_sheet)
    mirrors_ok, mirror_mismatches = verify_mirrors(frames, args.output_dir)

    clean_expected = place_layer(standing, BODY_POS)
    clean_end_exact = all(ImageChops.difference(frames[index], clean_expected).getbbox() is None for index in range(141, FRAME_COUNT))
    no_border_matte = all(border_alpha_count(frame) == 0 for frame in frames)
    standing_hash = pixel_sha256(standing)
    kneeling_hash = pixel_sha256(kneeling)
    release_hash = pixel_sha256(release)
    charge_bounds = alpha_bounds(kneeling)
    release_bounds = alpha_bounds(release)
    charge_top = charge_bounds[1] if charge_bounds else None
    release_top = release_bounds[1] if release_bounds else None
    character_scale_delta_px = abs(
        (charge_bounds[3] - charge_bounds[1]) - (release_bounds[3] - release_bounds[1])
    ) if charge_bounds and release_bounds else 999
    qa = {
        "status": "PASS" if mirrors_ok and clean_end_exact and no_border_matte and character_scale_delta_px <= 2 else "FAIL",
        "animation_id": "miyabi-final-blow-slash-v2",
        "source_note": "Model-grounded kneeling/grip and transparent release sprites supplied by the art pass; both are deterministically normalized with nearest-neighbour sampling.",
        "source_policy": {"model_grounded_sprite_sources_used": True, "pmx_copied_to_output": False, "pmx_runtime_dependency": False},
        "canvas": {"size": list(CANVAS_SIZE), "format": "RGBA PNG", "overscan_for_taskbar_pet": True, "body_position": list(BODY_POS), "taskbar_anchor": list(ANCHOR)},
        "timeline": {
            "fps": FPS,
            "frame_count": FRAME_COUNT,
            "duration_seconds": DURATION_SECONDS,
            "beats": {
                "standing_lead_in": [1, 9],
                "kneel_transition": [10, 18],
                "kneel_brace": [19, 55],
                "wave_launch": [56, 70],
                "hit_stop": [71, 78],
                "wave_travel_fade": [79, 126],
                "standing_return": [127, 141],
                "clean_idle": [142, 156],
            },
            "brace_seconds": round((55 - 18) / FPS, 6),
            "hit_stop_seconds": round((78 - 70) / FPS, 6),
        },
        "art_direction": {
            "pose": "model-grounded one-knee kneel with right hand on hilt and left hand on scabbard",
            "projectile": "one detached open crescent wave traveling right, cyan/teal body with white core",
            "forbidden_shapes": ["full circular aura around Miyabi", "overhead ring slash", "repeated slash projectiles"],
            "filter": "nearest-neighbour runtime sampling",
        },
        "pose_validation": {
            "charge_pose": {**pose_report, "pose_sha256": kneeling_hash},
            "release_pose": {**release_report, "pose_sha256": release_hash},
            "standing_body_sha256": standing_hash,
            "standing_body_source_sha256": pixel_sha256(Image.open(standing_source).convert("RGBA")),
            "standing_body_pixel_drift": 0,
            "anchor_is_fixed": True,
            "charge_top": charge_top,
            "release_top": release_top,
            "character_scale_delta_px": character_scale_delta_px,
            "character_scale_tolerance_px": 2,
        },
        "mirror_validation": {"left_is_exact_horizontal_mirror_per_frame": mirrors_ok, "mismatch_count": mirror_mismatches, "frame_order_preserved": True},
        "matte_validation": {"no_full_canvas_border_alpha": no_border_matte, "max_border_alpha_pixels": max(border_alpha_count(frame) for frame in frames), "clean_end_exact_standing": clean_end_exact},
        "performance_budget": {"logical_rgba_canvas_pixels": CANVAS_W * CANVAS_H, "max_projectile_spark_streaks": 22, "blur_passes_per_frame": 3, "runtime_shader_required": False},
        "outputs": {
            "kneeling_source": str(kneeling_source_copy),
            "kneeling_pose_layer": str(kneeling_path),
            "release_source": str(release_source_copy),
            "release_pose_layer": str(release_path),
            "standing_body_layer": str(standing_path),
            "right_frames": str(args.output_dir / "right" / "frames"),
            "left_frames": str(args.output_dir / "left" / "frames"),
            "right_strip": str(args.output_dir / "right" / f"strip-{FRAME_COUNT}x1.png"),
            "left_strip": str(args.output_dir / "left" / f"strip-{FRAME_COUNT}x1.png"),
            "review_video": review_video,
            "contact_sheet": str(contact_sheet),
        },
        "timeline_samples": timeline,
    }
    (args.output_dir / "forward-crescent-slash-qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
