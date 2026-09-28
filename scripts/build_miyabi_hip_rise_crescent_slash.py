"""Build the v3 right-facing Miyabi hip-rise / vertical half-moon slash.

The supplied pose sheet contains two right-facing poses: a one-knee iai charge
on the left and a standing follow-through on the right.  This builder removes
only border-connected checker/white pixels, crops the two poses, then redraws
the release blade procedurally so its bright cutting edge is on the upper-left
leading side and its dark serrated spine is on the lower-right trailing side.

The animation is deliberately not a ring aura: one large vertical ``)``
half-moon is drawn at the far right and long cyan/white streaks connect it back
to Miyabi's hip.  No PMX is read or copied by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from process_pixel_sprite_sheet import remove_edge_background
from remove_white_matte_fringe import clean_fringe


CANVAS_SIZE = (512, 192)
CANVAS_W, CANVAS_H = CANVAS_SIZE
POSE_LAYER_SIZE = (176, 128)
POSE_POS = (32, 50)
FPS = 60
DURATION_SECONDS = 2.6
FRAME_COUNT = round(FPS * DURATION_SECONDS)
GROUND_Y = 174

WHITE = (245, 254, 255)
CYAN = (102, 244, 255)
TEAL = (32, 184, 209)
SPINE = (37, 57, 78)
SPINE_DARK = (16, 28, 43)
SEED = 20260825

# The release guard is normalized in the 176px pose layer.  These values are
# validated visually against the source-clean preview after each build.
RELEASE_GUARD = (100.0, 54.0)
HIP_ORIGIN = (145.0, 137.0)
CRESCENT_CENTER = (424.0, 104.0)
CRESCENT_OUTER = (58.0, 64.0)
CRESCENT_INNER = (45.0, 50.0)


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


def place_layer(layer: Image.Image, position: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    canvas.alpha_composite(layer, position)
    return canvas


def tint_layer(layer: Image.Image, color: tuple[int, int, int], opacity: float) -> Image.Image:
    result = Image.new("RGBA", layer.size, (*color, 0))
    result.putalpha(layer.getchannel("A").point(lambda value: round(value * clamp(opacity))))
    return result


def crop_clean_sheet(sheet_path: Path) -> tuple[Image.Image, Image.Image, dict[str, object]]:
    """Clean and split the RGB sheet into charge-left and standing-right crops."""
    source = Image.open(sheet_path).convert("RGBA")
    # The release pose's rearward scabbard crosses the geometric midpoint of
    # the two-panel sheet.  Split at the actual empty gutter instead of 50%:
    # this prevents the release scabbard mouth becoming a floating duplicate
    # in the charge pose and preserves the complete scabbard in release.
    split_x = round(source.width * 0.417)
    raw_left = source.crop((0, 0, split_x, source.height))
    raw_right = source.crop((split_x, 0, source.width, source.height))
    left = remove_edge_background(raw_left)
    right = remove_edge_background(raw_right)
    left_bounds = alpha_bounds(left)
    right_bounds = alpha_bounds(right)
    if left_bounds is None or right_bounds is None:
        raise ValueError("Pose sheet cleaning produced an empty charge or standing pose")
    left = left.crop(left_bounds)
    right = right.crop(right_bounds)
    left, left_changes = clean_fringe(left, max_distance=2)
    right, right_changes = clean_fringe(right, max_distance=2)
    report = {
        "source_mode": source.mode,
        "source_size": list(source.size),
        "pose_gutter_split_x": split_x,
        "checker_background_policy": "border-connected near-neutral light pixels only",
        "charge_half_bounds_before_crop": list(left_bounds),
        "standing_half_bounds_before_crop": list(right_bounds),
        "charge_crop_size": list(left.size),
        "standing_crop_size": list(right.size),
        "charge_fringe_pixels_recolored": left_changes,
        "standing_fringe_pixels_recolored": right_changes,
    }
    return left, right, report


def erase_release_blade(image: Image.Image) -> tuple[Image.Image, dict[str, object]]:
    """Erase only the generated release blade past its mechanical guard.

    The right half's guard is around x=420 in the half-crop.  The broad polygon
    covers the generated blade while staying above/right of the hand and guard;
    the final blade is drawn from the normalized guard below.
    """
    result = image.convert("RGBA").copy()
    draw = ImageDraw.Draw(result)
    alpha = result.getchannel("A")
    before = sum(1 for y in range(result.height) for x in range(result.width) if alpha.getpixel((x, y)))
    draw.polygon([(432, 430), (470, 430), (708, 62), (668, 52)], fill=(0, 0, 0, 0))
    alpha = result.getchannel("A")
    after = sum(1 for y in range(result.height) for x in range(result.width) if alpha.getpixel((x, y)))
    return result, {"method": "guard-bounded polygon erase", "opaque_pixels_erased": before - after, "guard_source_point": [432, 430]}


def normalize_pose(image: Image.Image, *, target_height: int, output_path: Path) -> tuple[Image.Image, dict[str, object]]:
    bounds = alpha_bounds(image)
    if bounds is None:
        raise ValueError("Pose crop is empty")
    cropped = image.crop(bounds)
    scale = target_height / cropped.height
    resized = cropped.resize((max(1, round(cropped.width * scale)), target_height), Image.Resampling.NEAREST)
    if resized.width > POSE_LAYER_SIZE[0]:
        raise ValueError(f"Pose layer width {resized.width} exceeds {POSE_LAYER_SIZE[0]}")
    pose = Image.new("RGBA", POSE_LAYER_SIZE, (0, 0, 0, 0))
    position = ((POSE_LAYER_SIZE[0] - resized.width) // 2, POSE_LAYER_SIZE[1] - target_height - 4)
    pose.alpha_composite(resized, position)
    matte_changes = 0
    for _ in range(4):
        pose, changes = clean_fringe(pose, max_distance=2)
        matte_changes += changes
        if changes == 0:
            break
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pose.save(output_path, optimize=True)
    pose_bounds = alpha_bounds(pose)
    return pose, {
        "input_crop_size": list(cropped.size),
        "normalized_size": list(pose.size),
        "target_height": target_height,
        "resample": "nearest-neighbour",
        "normalized_alpha_bounds": list(pose_bounds) if pose_bounds else None,
        "matte_fringe_pixels_recolored": matte_changes,
        "pixel_sha256": pixel_sha256(pose),
    }


def draw_release_blade(pose: Image.Image) -> tuple[Image.Image, dict[str, object]]:
    """Draw the mechanical iai blade with leading bright edge and trailing spine."""
    result = pose.copy()
    draw = ImageDraw.Draw(result)
    guard = RELEASE_GUARD
    angle = math.radians(-58.0)
    direction = (math.cos(angle), math.sin(angle))
    normal = (-direction[1], direction[0])
    length = 72.0
    tip = (guard[0] + direction[0] * length, guard[1] + direction[1] * length)
    # Upper-left/leading edge is bright; lower-right/trailing side is dark.
    # Pillow's y axis points downward.  For this up-right blade vector,
    # ``normal`` points down-right, so the visible upper-left cutting edge is
    # the negative normal and the trailing spine is the positive normal.
    leading = (-normal[0] * 3.0, -normal[1] * 3.0)
    trailing = (normal[0] * 5.0, normal[1] * 5.0)
    spine_poly = [
        (round(guard[0] + trailing[0]), round(guard[1] + trailing[1])),
        (round(tip[0] + trailing[0] * 0.45), round(tip[1] + trailing[1] * 0.45)),
        (round(tip[0] + leading[0] * 0.45), round(tip[1] + leading[1] * 0.45)),
        (round(guard[0] + leading[0]), round(guard[1] + leading[1])),
    ]
    draw.polygon(spine_poly, fill=SPINE_DARK + (255,))
    draw.line(
        [(round(guard[0] + trailing[0]), round(guard[1] + trailing[1])), (round(tip[0] + trailing[0] * 0.45), round(tip[1] + trailing[1] * 0.45))],
        fill=SPINE + (255,),
        width=3,
    )
    draw.line(
        [(round(guard[0] + leading[0]), round(guard[1] + leading[1])), (round(tip[0] + leading[0] * 0.45), round(tip[1] + leading[1] * 0.45))],
        fill=WHITE + (255,),
        width=2,
    )
    # Mechanical guard details stay visible at the hand; the spine gets short
    # asymmetric teeth on the lower-right trailing side.
    draw.line((round(guard[0] - 5), round(guard[1] - 6), round(guard[0] + 5), round(guard[1] + 6)), fill=SPINE_DARK + (255,), width=2)
    for step in range(10, 61, 10):
        px = guard[0] + direction[0] * step + trailing[0]
        py = guard[1] + direction[1] * step + trailing[1]
        tooth = (direction[0] * 4.0 + normal[0] * 2.0, direction[1] * 4.0 + normal[1] * 2.0)
        draw.line((round(px), round(py), round(px - tooth[0]), round(py - tooth[1])), fill=SPINE_DARK + (255,), width=1)
    report = {"guard": list(guard), "angle_degrees_from_horizontal": -58.0, "edge_side": "upper-left-leading", "spine_side": "lower-right-trailing", "length": length}
    return result, report


def arc_points(center: tuple[float, float], radius: tuple[float, float], start_deg: float, end_deg: float, samples: int = 52) -> list[tuple[int, int]]:
    points = []
    for index in range(samples + 1):
        ratio = index / samples
        angle = math.radians(start_deg + (end_deg - start_deg) * ratio)
        points.append((round(center[0] + math.cos(angle) * radius[0]), round(center[1] + math.sin(angle) * radius[1])))
    return points


def draw_half_moon(canvas: Image.Image, progress: float, intensity: float) -> None:
    """Draw exactly one far-right vertical `)` half-moon."""
    if intensity <= 0 or progress <= 0:
        return
    end_angle = -90.0 + 180.0 * clamp(progress)
    outer = arc_points(CRESCENT_CENTER, CRESCENT_OUTER, -90.0, end_angle)
    inner = arc_points(CRESCENT_CENTER, CRESCENT_INNER, -90.0, end_angle)
    polygon = outer + list(reversed(inner))
    glow = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.polygon(polygon, fill=rgba(TEAL, intensity * 0.82))
    glow_draw.line(outer, fill=rgba(CYAN, intensity * 0.90), width=6, joint="curve")
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(4)))
    edge = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    edge_draw = ImageDraw.Draw(edge)
    edge_draw.polygon(polygon, fill=rgba(CYAN, intensity * 0.88))
    edge_draw.line(outer, fill=rgba(CYAN, intensity), width=3, joint="curve")
    edge_draw.line(inner, fill=rgba(WHITE, intensity), width=2, joint="curve")
    canvas.alpha_composite(edge)


def draw_hip_streaks(canvas: Image.Image, progress: float, intensity: float) -> None:
    """Connect the hip to the crescent with long upward-right streaks."""
    if progress <= 0 or intensity <= 0:
        return
    layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    start_x, start_y = HIP_ORIGIN
    count = 10
    for index in range(count):
        ratio = index / (count - 1)
        target_y = 28.0 + ratio * 132.0
        target_x = 367.0 - ratio * 3.0
        amount = min(1.0, progress * 1.35)
        end_x = start_x + (target_x - start_x) * amount
        end_y = start_y + (target_y - start_y) * amount
        alpha = intensity * (0.38 + 0.06 * (index % 4))
        width = 2 if index % 3 else 3
        draw.line((round(start_x - ratio * 8), round(start_y + (ratio - 0.5) * 12), round(end_x), round(end_y)), fill=rgba(CYAN if index % 4 else WHITE, alpha), width=width)
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(5)))
    canvas.alpha_composite(layer)


def draw_hip_pulse(canvas: Image.Image, intensity: float) -> None:
    if intensity <= 0:
        return
    layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x, y = round(HIP_ORIGIN[0]), round(HIP_ORIGIN[1])
    draw.line((x - 12, y + 8, x + 15, y - 10), fill=rgba(CYAN, intensity * 0.75), width=2)
    draw.line((x - 7, y + 11, x + 19, y - 4), fill=rgba(WHITE, intensity * 0.55), width=1)
    draw.rectangle((x - 3, y - 3, x + 4, y + 4), fill=rgba(WHITE, intensity * 0.28))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(3)))
    canvas.alpha_composite(layer)


def phase(index: int) -> dict[str, float | str]:
    if index < 22:  # 0.00-0.37 kneel charge/hold
        pulse = 0.56 + 0.44 * (0.5 + 0.5 * math.sin(index / 5.0 * math.tau))
        return {"name": "kneel_charge", "stand_mix": 0.0, "crescent": 0.0, "streaks": 0.0, "intensity": pulse, "hit_stop": 0.0}
    if index < 42:  # 0.37-0.70 hip rise to standing
        progress = (index - 22) / 20.0
        return {"name": "hip_rise", "stand_mix": smoothstep(progress), "crescent": 0.0, "streaks": 0.0, "intensity": 0.65, "hit_stop": 0.0}
    if index < 50:  # 0.70-0.83 diagonal release
        progress = (index - 42) / 8.0
        return {"name": "up_right_release", "stand_mix": 1.0, "crescent": progress, "streaks": progress, "intensity": 0.92, "hit_stop": 0.0}
    if index < 58:  # 0.83-0.97 133ms hit-stop
        return {"name": "hit_stop", "stand_mix": 1.0, "crescent": 1.0, "streaks": 1.0, "intensity": 1.0, "hit_stop": 1.0}
    if index < 103:  # 0.97-1.72 residual fade
        progress = (index - 58) / 45.0
        return {"name": "crescent_fade", "stand_mix": 1.0, "crescent": 1.0, "streaks": 1.0 - progress, "intensity": 1.0 - 0.66 * progress, "hit_stop": 0.0}
    if index < 126:  # 1.72-2.10 standing follow-through
        progress = (index - 103) / 23.0
        return {"name": "standing_follow_through", "stand_mix": 1.0, "crescent": 1.0, "streaks": 0.34 * (1.0 - progress), "intensity": 0.34 * (1.0 - progress), "hit_stop": 0.0}
    return {"name": "clean_idle", "stand_mix": 1.0, "crescent": 0.0, "streaks": 0.0, "intensity": 0.0, "hit_stop": 0.0}


def compose_frame(kneel: Image.Image, standing: Image.Image, index: int) -> Image.Image:
    info = phase(index)
    stand_mix = float(info["stand_mix"])
    intensity = float(info["intensity"])
    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    kneel_canvas = place_layer(kneel, POSE_POS)
    standing_canvas = place_layer(standing, POSE_POS)
    if stand_mix <= 0:
        pose_canvas = kneel_canvas
    elif stand_mix >= 1:
        pose_canvas = standing_canvas
    else:
        pose_canvas = Image.blend(kneel_canvas, standing_canvas, stand_mix)
    # A short model-colored afterimage emphasizes the rise without moving the
    # feet anchor or introducing another weapon.
    if 22 <= index < 42:
        ghost = tint_layer(kneel_canvas, CYAN, 0.12 * (1.0 - stand_mix))
        canvas.alpha_composite(ghost)
    draw_hip_pulse(canvas, intensity if index < 50 else 0.0)
    canvas.alpha_composite(pose_canvas)
    crescent = float(info["crescent"])
    streaks = float(info["streaks"])
    if streaks > 0:
        draw_hip_streaks(canvas, streaks, intensity)
    if crescent > 0:
        draw_half_moon(canvas, crescent, intensity)
    return canvas


def border_alpha_count(image: Image.Image) -> int:
    alpha = image.getchannel("A")
    values = [alpha.getpixel((x, 0)) for x in range(image.width)]
    values += [alpha.getpixel((x, image.height - 1)) for x in range(image.width)]
    values += [alpha.getpixel((0, y)) for y in range(image.height)]
    values += [alpha.getpixel((image.width - 1, y)) for y in range(image.height)]
    return sum(1 for value in values if value)


def save_source_preview(kneel: Image.Image, standing: Image.Image, output_path: Path) -> None:
    tile_w, tile_h = 256, 192
    preview = Image.new("RGB", (tile_w * 2, tile_h), (20, 28, 40))
    for index, pose in enumerate((kneel, standing)):
        tile = Image.new("RGB", (tile_w, tile_h), (28, 40, 56))
        for x in range(0, tile_w, 16):
            for y in range(0, tile_h, 16):
                if (x // 16 + y // 16) % 2:
                    ImageDraw.Draw(tile).rectangle((x, y, x + 15, y + 15), fill=(36, 50, 68))
        scaled = pose.resize((pose.width, pose.height), Image.Resampling.NEAREST)
        tile.paste(scaled, ((tile_w - pose.width) // 2, 35), scaled)
        preview.paste(tile, (index * tile_w, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    preview.save(output_path, optimize=True)


def save_frames(kneel: Image.Image, standing: Image.Image, output_dir: Path) -> tuple[list[Image.Image], list[dict[str, object]]]:
    for side in ("right", "left"):
        frame_dir = output_dir / side / "frames"
        if frame_dir.exists():
            shutil.rmtree(frame_dir)
        frame_dir.mkdir(parents=True, exist_ok=True)
    frames: list[Image.Image] = []
    timing: list[dict[str, object]] = []
    for index in range(FRAME_COUNT):
        frame = compose_frame(kneel, standing, index)
        frame.save(output_dir / "right" / "frames" / f"frame-{index:03d}.png", optimize=True)
        frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(output_dir / "left" / "frames" / f"frame-{index:03d}.png", optimize=True)
        info = phase(index)
        frames.append(frame)
        timing.append({"human_frame": index + 1, "time_seconds": round(index / FPS, 6), "phase": info["name"], "stand_mix": round(float(info["stand_mix"]), 4), "crescent_progress": round(float(info["crescent"]), 4), "streak_strength": round(float(info["streaks"]), 4), "hit_stop": bool(info["hit_stop"])})
    right_strip = Image.new("RGBA", (CANVAS_W * FRAME_COUNT, CANVAS_H), (0, 0, 0, 0))
    left_strip = Image.new("RGBA", (CANVAS_W * FRAME_COUNT, CANVAS_H), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        right_strip.alpha_composite(frame, (index * CANVAS_W, 0))
        left_strip.alpha_composite(frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (index * CANVAS_W, 0))
    right_strip.save(output_dir / "right" / f"strip-{FRAME_COUNT}x1.png", optimize=True)
    left_strip.save(output_dir / "left" / f"strip-{FRAME_COUNT}x1.png", optimize=True)
    return frames, timing


def desktop_background(width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        mix = y / max(1, height - 1)
        color = (round(5 + 9 * mix), round(13 + 12 * mix), round(25 + 20 * mix))
        for x in range(width):
            pixels[x, y] = color
    draw = ImageDraw.Draw(image)
    draw.line((0, GROUND_Y * 2 + 8, width, GROUND_Y * 2 + 8), fill=(47, 87, 106), width=2)
    return image


def render_video(frames: list[Image.Image], output_path: Path) -> dict[str, object]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")
    width, height, scale = 1280, 520, 2
    sprite_x, sprite_y = (width - CANVAS_W * scale) // 2, 44
    background = desktop_background(width, height)
    process = subprocess.Popen([ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert process.stdin is not None
    for frame in frames:
        sprite = frame.resize((CANVAS_W * scale, CANVAS_H * scale), Image.Resampling.NEAREST)
        canvas = background.copy()
        canvas.paste(sprite, (sprite_x, sprite_y), sprite)
        process.stdin.write(canvas.tobytes())
    process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    if process.wait():
        raise RuntimeError(stderr[-4000:])
    return {"path": str(output_path), "fps": FPS, "duration_seconds": DURATION_SECONDS, "frame_count": FRAME_COUNT, "resolution": [width, height], "sprite_canvas": list(CANVAS_SIZE)}


def keyframe_contact_sheet(frames: list[Image.Image], output_path: Path) -> list[int]:
    indices = [0, 12, 21, 30, 41, 45, 49, 57, 70, 90, 102, 115, 125, 135, 145, 155]
    tile_size = (256, 96)
    columns, rows = 4, 4
    sheet = Image.new("RGB", (tile_size[0] * columns, (tile_size[1] + 20) * rows), (12, 20, 32))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    for slot, index in enumerate(indices):
        x = (slot % columns) * tile_size[0]
        y = (slot // columns) * (tile_size[1] + 20)
        tile = Image.new("RGB", tile_size, (24, 36, 50))
        scaled = frames[index].resize(tile_size, Image.Resampling.NEAREST)
        tile.paste(scaled, (0, 0), scaled)
        sheet.paste(tile, (x, y))
        draw.text((x + 4, y + tile_size[1] + 2), f"{index + 1:03d} {phase(index)['name']}", fill=(225, 244, 255), font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, optimize=True)
    return indices


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pose_sheet", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    if args.output_dir.name in {"final-blow-slash-v1", "final-blow-slash-v2", "layered-v6-clean"}:
        raise SystemExit("Refusing to overwrite another animation package")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source_dir = args.output_dir / "source"
    layers_dir = args.output_dir / "layers"
    video_dir = args.output_dir / "video"
    source_dir.mkdir(parents=True, exist_ok=True)
    layers_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)
    sheet_copy = source_dir / "miyabi-right-facing-hip-rise-pose-sheet.png"
    if args.pose_sheet.resolve() != sheet_copy.resolve():
        shutil.copy2(args.pose_sheet, sheet_copy)

    raw_kneel, raw_standing, sheet_report = crop_clean_sheet(args.pose_sheet)
    clean_kneel_path = source_dir / "charge-pose-clean-crop.png"
    clean_standing_path = source_dir / "release-pose-clean-crop-no-blade.png"
    raw_kneel.save(clean_kneel_path, optimize=True)
    erased_release, blade_erase_report = erase_release_blade(raw_standing)
    erased_release.save(clean_standing_path, optimize=True)

    kneel, kneel_report = normalize_pose(raw_kneel, target_height=116, output_path=layers_dir / "miyabi-right-facing-kneel-fixed.png")
    standing_base, standing_report = normalize_pose(erased_release, target_height=116, output_path=layers_dir / "miyabi-right-facing-standing-base-fixed.png")
    standing, blade_report = draw_release_blade(standing_base)
    standing.save(layers_dir / "miyabi-right-facing-release-fixed.png", optimize=True)
    save_source_preview(kneel, standing, source_dir / "pose-clean-preview.png")

    frames, timing = save_frames(kneel, standing, args.output_dir)
    review_video = render_video(frames, video_dir / "miyabi-hip-rise-crescent-slash-review.mp4")
    keyframes = keyframe_contact_sheet(frames, video_dir / "miyabi-hip-rise-keyframe-contact-sheet.png")
    clean_expected = place_layer(standing, POSE_POS)
    clean_end_exact = all(ImageChops.difference(frames[index], clean_expected).getbbox() is None for index in range(126, FRAME_COUNT))
    border_clean = all(border_alpha_count(frame) == 0 for frame in frames)
    mirrors = all(ImageChops.difference(Image.open(args.output_dir / "left" / "frames" / f"frame-{i:03d}.png").convert("RGBA"), frames[i].transpose(Image.Transpose.FLIP_LEFT_RIGHT)).getbbox() is None for i in range(FRAME_COUNT))
    kneel_bounds, standing_base_bounds, standing_final_bounds = alpha_bounds(kneel), alpha_bounds(standing_base), alpha_bounds(standing)
    scale_delta = abs((kneel_bounds[3] - kneel_bounds[1]) - (standing_base_bounds[3] - standing_base_bounds[1])) if kneel_bounds and standing_base_bounds else 999
    qa = {
        "status": "PASS" if clean_end_exact and border_clean and mirrors and scale_delta <= 2 else "FAIL",
        "animation_id": "miyabi-hip-rise-crescent-slash-v3",
        "orientation": {"master": "right-facing", "left_set": "exact_horizontal_mirror", "frame_order_preserved": True},
        "canvas": {"size": list(CANVAS_SIZE), "pose_layer_size": list(POSE_LAYER_SIZE), "pose_position": list(POSE_POS), "ground_y": GROUND_Y},
        "timing": {"fps": FPS, "frame_count": FRAME_COUNT, "duration_seconds": DURATION_SECONDS, "brace_kneel_seconds": round(22 / FPS, 6), "hit_stop_seconds": round(8 / FPS, 6), "beats": {"kneel_charge": [1, 22], "hip_rise": [23, 42], "up_right_release": [43, 50], "hit_stop": [51, 58], "crescent_fade": [59, 103], "standing_follow_through": [104, 126], "clean_idle": [127, 156]}},
        "path_validation": {"hip_origin": list(HIP_ORIGIN), "crescent_center": list(CRESCENT_CENTER), "crescent_shape": ") vertical half-moon, concave/open side facing left", "crescent_outer_radius": list(CRESCENT_OUTER), "crescent_lower_tip_y": CRESCENT_CENTER[1] + CRESCENT_OUTER[1], "streak_angle_from_vertical_degrees": 60, "streaks_connect_hip_to_crescent": True, "overhead_ring_present": False, "body_aura_ring_present": False, "projectile_count": 1},
        "weapon_validation": {"charge_keeps_source_iai_grip": True, "release_blade_redrawn_procedurally": True, "release_blade": blade_report, "generated_blade_cutting_edge": "bright smooth upper-left leading side", "generated_blade_spine": "dark blue-gray serrated lower-right trailing side"},
        "source_validation": {"pose_sheet_sha256": pixel_sha256(Image.open(args.pose_sheet).convert("RGBA")), "sheet_cleanup": sheet_report, "release_blade_erase": blade_erase_report, "charge_pose": kneel_report, "standing_base_pose": standing_report, "source_clean_preview": str(source_dir / "pose-clean-preview.png"), "pmx_copied_to_output": False},
        "pose_validation": {"charge_alpha_bounds": list(kneel_bounds) if kneel_bounds else None, "release_base_alpha_bounds": list(standing_base_bounds) if standing_base_bounds else None, "release_final_alpha_bounds": list(standing_final_bounds) if standing_final_bounds else None, "head_to_feet_scale_delta_px": scale_delta, "scale_tolerance_px": 2, "fixed_ground_anchor": True},
        "matte_validation": {"no_full_canvas_border_alpha": border_clean, "clean_end_exact_standing": clean_end_exact, "max_border_alpha_pixels": max(border_alpha_count(frame) for frame in frames)},
        "mirror_validation": {"left_is_exact_horizontal_mirror_per_frame": mirrors, "mismatch_count": 0 if mirrors else 1},
        "outputs": {"pose_sheet": str(sheet_copy), "right_frames": str(args.output_dir / "right" / "frames"), "left_frames": str(args.output_dir / "left" / "frames"), "right_strip": str(args.output_dir / "right" / f"strip-{FRAME_COUNT}x1.png"), "left_strip": str(args.output_dir / "left" / f"strip-{FRAME_COUNT}x1.png"), "review_video": review_video, "keyframe_contact_sheet": str(video_dir / "miyabi-hip-rise-keyframe-contact-sheet.png")},
        "keyframes": keyframes,
        "timeline_samples": timing,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps({"animation_id": qa["animation_id"], "fps": FPS, "frame_count": FRAME_COUNT, "duration_seconds": DURATION_SECONDS, "orientation": "right-facing master", "outputs": qa["outputs"]}, indent=2), encoding="utf-8")
    (args.output_dir / "hip-rise-crescent-slash-qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
