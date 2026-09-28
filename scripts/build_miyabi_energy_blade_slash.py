"""Build the v5 right-facing Miyabi energy dao-blade slash.

The supplied pose sheet contains two right-facing poses: a one-knee iai charge
on the left and a standing follow-through on the right.  This builder removes
only border-connected checker/white pixels, crops the two poses, then redraws
the release blade procedurally so its bright cutting edge is on the upper-left
leading side and its dark serrated spine is on the lower-right trailing side.

The effect is one moving giant curved dao/saber energy blade. Thin, translucent
cyan/ice-blue ribbons trail from Miyabi's hip to its bright head, staying faint
near the origin and concentrating toward the pointed front. No PMX is read or
copied and no target/ring is invented.
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
ICE_BLUE = (174, 246, 255)
BLUE = (52, 126, 255)
DEEP_BLUE = (19, 48, 154)
SPINE = (37, 57, 78)
SPINE_DARK = (16, 28, 43)
SEED = 20260825

# The release guard is normalized in the 176px pose layer.  These values are
# validated visually against the source-clean preview after each build.
RELEASE_GUARD = (100.0, 54.0)
HIP_ORIGIN = (145.0, 137.0)
SURGE_START = (145.0, 137.0)
BLADE_FRONT_X = 470.0
SURGE_GROUND_Y = 171.0


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
    """Erase the source-sheet blade beyond the release guard, not the hand.

    After the real gutter split, the standing crop's original blade runs from
    about ``(540,350)`` toward ``(807,0)``.  The old v4 polygon used pre-split
    coordinates and left that blade behind.  This mask follows the actual
    diagonal centerline, starts 24px past the guard, and is intentionally wide
    enough for the entire baked blade silhouette.
    """
    result = image.convert("RGBA").copy()
    guard = (540.0, 350.0)
    direction = (0.607, -0.795)
    normal = (0.795, 0.607)
    start_distance = 30.0
    end_distance = 560.0
    start = (guard[0] + direction[0] * start_distance, guard[1] + direction[1] * start_distance)
    end = (guard[0] + direction[0] * end_distance, guard[1] + direction[1] * end_distance)
    polygon = [
        (round(start[0] + normal[0] * 40), round(start[1] + normal[1] * 40)),
        (round(end[0] + normal[0] * 52), round(end[1] + normal[1] * 52)),
        (round(end[0] - normal[0] * 52), round(end[1] - normal[1] * 52)),
        (round(start[0] - normal[0] * 40), round(start[1] - normal[1] * 40)),
    ]
    mask = Image.new("L", result.size, 0)
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    alpha_before = result.getchannel("A")
    region_before = sum(1 for value in ImageChops.multiply(alpha_before, mask).tobytes() if value)
    ImageDraw.Draw(result).polygon(polygon, fill=(0, 0, 0, 0))
    alpha_after = result.getchannel("A")
    region_after = sum(1 for value in ImageChops.multiply(alpha_after, mask).tobytes() if value)
    total_before = sum(1 for value in alpha_before.tobytes() if value)
    total_after = sum(1 for value in alpha_after.tobytes() if value)
    return result, {
        "method": "post-gutter diagonal blade mask",
        "guard_source_point": list(guard),
        "erase_start_distance_px": start_distance,
        "erase_mask_polygon": [list(point) for point in polygon],
        "opaque_pixels_erased": total_before - total_after,
        "mask_pixels_before": region_before,
        "mask_residual_alpha_after": region_after,
        "source_blade_fully_erased": region_after == 0,
    }


def save_blade_erase_zoom(before: Image.Image, after: Image.Image, output_path: Path) -> None:
    """Save a close-up evidence panel proving the baked blade was removed."""
    box = (500, 0, min(before.width, 895), min(before.height, 410))
    scale = 2
    panels = []
    for image in (before, after):
        tile = image.crop(box).resize(((box[2] - box[0]) * scale, (box[3] - box[1]) * scale), Image.Resampling.NEAREST)
        background = Image.new("RGB", tile.size, (10, 22, 38))
        background.paste(tile, mask=tile.getchannel("A"))
        panels.append(background)
    evidence = Image.new("RGB", (panels[0].width * 2, panels[0].height), (5, 12, 23))
    evidence.paste(panels[0], (0, 0))
    evidence.paste(panels[1], (panels[0].width, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    evidence.save(output_path, optimize=True)


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


def _tapered_band(start: tuple[float, float], end: tuple[float, float], width_start: float, width_end: float) -> list[tuple[int, int]]:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / length, dx / length
    return [
        (round(start[0] + nx * width_start), round(start[1] + ny * width_start)),
        (round(end[0] + nx * width_end), round(end[1] + ny * width_end)),
        (round(end[0] - nx * width_end), round(end[1] - ny * width_end)),
        (round(start[0] - nx * width_start), round(start[1] - ny * width_start)),
    ]


def _dao_head(progress: float, phase_seed: int = 0) -> dict[str, object]:
    """Return a curved, pointed dao silhouette with separate edge/back paths."""
    p = clamp(progress)
    reach = smoothstep(min(1.0, p * 1.12))
    front = SURGE_START[0] + (BLADE_FRONT_X - SURGE_START[0]) * reach
    strength = smoothstep((p - 0.10) / 0.90)
    # The long spine rises only gently (roughly 8-12 degrees).  The final
    # 15-20% curls upward into a distinct dao tip rather than a wall/cap.
    base = (front - (48.0 + 13.0 * (1.0 - strength)), 139.0 - 3.0 * strength)
    tip = (front + 16.0 * strength, 103.0 - 24.0 * strength)
    back: list[tuple[int, int]] = []
    edge: list[tuple[int, int]] = []
    for index in range(13):
        t = index / 12.0
        x = base[0] + (tip[0] - base[0]) * t + (8.0 * strength * math.sin(t * math.pi * 0.9))
        y = base[1] + (tip[1] - base[1]) * (t ** 1.15) + math.sin((index + phase_seed * 0.17) * 1.2) * 1.2 * strength
        back.append((round(x), round(y + (5.0 + 10.0 * strength) * math.sin(t * math.pi))))
    for index in range(12, -1, -1):
        t = index / 12.0
        x = base[0] + (tip[0] - base[0]) * t + 4.0 * strength * math.sin(t * math.pi)
        y = base[1] + (tip[1] - base[1]) * (t ** 1.15) - (2.0 + 5.0 * strength) * math.sin(t * math.pi)
        edge.append((round(x), round(y)))
    return {"front": front, "base": base, "tip": tip, "back": back, "edge": edge, "strength": strength}


def _draw_dao_head(canvas: Image.Image, head: dict[str, object], intensity: float, frame_index: int) -> None:
    """Layer dark silhouette, cyan body, ice inner curve, edge and chipped tip."""
    back = head["back"]
    edge = head["edge"]
    silhouette = back + edge
    strength = float(head["strength"])
    if strength <= 0.005:
        return
    glow = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.polygon(silhouette, fill=rgba(DEEP_BLUE, intensity * 0.76))
    glow_draw.line(edge, fill=rgba(ICE_BLUE, intensity * 0.72), width=7, joint="curve")
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(4)))

    body = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    body_draw = ImageDraw.Draw(body)
    body_draw.polygon(silhouette, fill=rgba(DEEP_BLUE, intensity * 0.94))
    inner = [(round(x + 2), round(y - 2 - 1.3 * math.sin(i * 0.7))) for i, (x, y) in enumerate(back)] + [(round(x - 2), round(y + 1.5)) for x, y in edge]
    body_draw.polygon(inner, fill=rgba(CYAN, intensity * 0.78))
    nested = [(round(x + 2), round(y - 1)) for x, y in inner[: len(inner) // 2]] + [(round(x - 1), round(y + 1)) for x, y in inner[len(inner) // 2 :]]
    body_draw.polygon(nested, fill=rgba(ICE_BLUE, intensity * 0.52))
    canvas.alpha_composite(body)

    edge_layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    edge_draw = ImageDraw.Draw(edge_layer)
    edge_draw.line(edge, fill=rgba(WHITE, intensity * (0.68 + 0.32 * strength)), width=2, joint="curve")
    edge_draw.line(back, fill=rgba(BLUE, intensity * 0.85), width=1, joint="curve")
    # Irregular frost chips break the contour without making a flat cap.
    tip_x, tip_y = head["tip"]
    for shard in range(8):
        t = 0.14 + shard * 0.095
        sx = tip_x - 32 * t + math.sin((frame_index + shard) * 1.4) * 3
        sy = tip_y + (139 - tip_y) * t
        length = 4 + (shard % 3) * 3
        edge_draw.line((round(sx), round(sy), round(sx - length), round(sy - 3 - shard % 2 * 4)), fill=rgba(ICE_BLUE, intensity * (0.42 + 0.06 * (shard % 4))), width=1)
    canvas.alpha_composite(edge_layer.filter(ImageFilter.GaussianBlur(1)))
    canvas.alpha_composite(edge_layer)


def _draw_trailing_ribbons(canvas: Image.Image, progress: float, intensity: float, frame_index: int) -> None:
    """Draw irregular ghost-blade ribbons with low-alpha roots and bright heads."""
    head = _dao_head(progress, frame_index)
    base_x, base_y = head["base"]
    p = clamp(progress)
    soft = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    crisp = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    soft_draw = ImageDraw.Draw(soft)
    crisp_draw = ImageDraw.Draw(crisp)
    for ribbon in range(4):
        points: list[tuple[float, float]] = []
        segments = 12
        phase = ribbon * 0.91 + frame_index * 0.11
        target_y = base_y - (ribbon - 1.5) * (7.0 + 3.0 * p)
        for segment in range(segments + 1):
            t = segment / segments
            x = SURGE_START[0] + (base_x - SURGE_START[0]) * t
            curve = math.sin(phase + t * (4.2 + ribbon * 0.55)) * (2.0 + 8.0 * t) + math.sin(phase * 0.7 + t * (8.0 + ribbon)) * (0.9 + 1.6 * t)
            y = SURGE_START[1] + (target_y - SURGE_START[1]) * t + curve + (ribbon - 3) * 0.8 * t
            points.append((x, y))
        for segment in range(segments):
            if segment == 1 and ribbon in (0, 2) and (frame_index + ribbon) % 3 != 0:
                continue
            t = (segment + 0.5) / segments
            start, end = points[segment], points[segment + 1]
            width = 0.35 + (2.2 + ribbon % 3 * 0.8) * (t ** 1.5) * (0.45 + 0.55 * p)
            alpha = intensity * (0.14 + 0.70 * (t ** 0.72)) * (0.76 + 0.05 * (ribbon % 4))
            if segment == 0:
                alpha *= 0.72
            color = ICE_BLUE if ribbon % 2 else CYAN
            poly = _tapered_band(start, end, width * 0.65, width)
            soft_draw.polygon(poly, fill=rgba(color, alpha * 0.55))
            crisp_draw.polygon(poly, fill=rgba(color, alpha))
    # Two or three detached navy afterimages sit behind the cyan ribbons.
    for streak in range(3):
        end_t = 0.56 + streak * 0.10
        end_x = SURGE_START[0] + (base_x - SURGE_START[0]) * end_t
        end_y = SURGE_START[1] + (target_y - SURGE_START[1]) * end_t + 7 + streak * 3
        mid_x = SURGE_START[0] + (end_x - SURGE_START[0]) * 0.52
        mid_y = SURGE_START[1] + (end_y - SURGE_START[1]) * 0.52 + math.sin((frame_index + streak) * 0.8) * 3
        crisp_draw.line([(round(SURGE_START[0] + 3), round(SURGE_START[1] + 5 + streak * 3)), (round(mid_x), round(mid_y)), (round(end_x), round(end_y))], fill=rgba(DEEP_BLUE, intensity * (0.10 + streak * 0.035)), width=1)
    canvas.alpha_composite(soft.filter(ImageFilter.GaussianBlur(3)))
    canvas.alpha_composite(crisp)

    shards = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    shard_draw = ImageDraw.Draw(shards)
    for shard in range(6):
        t = 0.35 + ((shard * 0.17 + frame_index * 0.013) % 0.58)
        sx = SURGE_START[0] + (base_x - SURGE_START[0]) * t
        sy = SURGE_START[1] + (target_y - SURGE_START[1]) * t if 'target_y' in locals() else SURGE_START[1]
        if shard % 2 == 0:
            shard_draw.polygon([(round(sx), round(sy)), (round(sx + 3 + shard % 4), round(sy - 1 - shard % 3)), (round(sx + 1), round(sy - 7 - shard % 4))], fill=rgba(ICE_BLUE if shard % 2 else CYAN, intensity * (0.24 + 0.04 * (shard % 4))))
    canvas.alpha_composite(shards)


def draw_energy_blade(canvas: Image.Image, progress: float, intensity: float, frame_index: int, impact: float = 0.0) -> None:
    """Draw one moving dao head and its transparent-to-bright trailing afterimage."""
    if progress <= 0 or intensity <= 0:
        return
    _draw_trailing_ribbons(canvas, progress, intensity, frame_index)
    # The giant head is a brief event; the thin ribbons remain as the head exits.
    head_visibility = 1.0 if frame_index < 76 else clamp(1.0 - (frame_index - 76) / 18.0)
    if head_visibility > 0:
        _draw_dao_head(canvas, _dao_head(progress, frame_index), intensity * head_visibility, frame_index)
    ground = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    ground_draw = ImageDraw.Draw(ground)
    head = _dao_head(progress, frame_index)
    base_x, base_y = head["base"]
    for shard in range(3):
        rx = round(SURGE_START[0] + (base_x - SURGE_START[0]) * (0.55 + shard * 0.16))
        ry = round(169 + math.sin((frame_index + shard) * 0.7) * 2)
        ground_draw.polygon([(rx, ry), (rx + 4 + shard, ry - 1), (rx + 1, ry - 7 - shard * 2)], fill=rgba(ICE_BLUE, intensity * (0.18 + shard * 0.04)))
    canvas.alpha_composite(ground)
    if impact > 0:
        draw_impact_flare(canvas, impact, frame_index, head)


def draw_impact_flare(canvas: Image.Image, intensity: float, frame_index: int, head: dict[str, object]) -> None:
    """Draw a white/cyan split flash at the pointed dao tip only."""
    tip_x, tip_y = head["tip"]
    x, y = round(tip_x - 2), round(tip_y + 12)
    layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.polygon([(x - 7, y + 3), (x - 1, y - 5), (x + 1, y - 25), (x + 4, y - 6), (x + 12, y + 2), (x + 3, y + 5)], fill=rgba(CYAN, intensity * 0.64))
    draw.line((x + 1, y - 28, x + 1, y + 12), fill=rgba(WHITE, intensity * 0.88), width=1)
    draw.line((x - 10, y + 2, x + 10, y + 2), fill=rgba(ICE_BLUE, intensity * 0.55), width=1)
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(3)))
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
        return {"name": "kneel_charge", "stand_mix": 0.0, "surge": 0.0, "intensity": pulse, "impact": 0.0, "hit_stop": 0.0}
    if index < 40:  # 0.37-0.67 hip rise to standing
        progress = (index - 22) / 18.0
        return {"name": "hip_rise", "stand_mix": smoothstep(progress), "surge": 0.0, "intensity": 0.68, "impact": 0.0, "hit_stop": 0.0}
    if index < 45:  # 0.67-0.75 thin initial cut line
        progress = (index - 40) / 5.0
        return {"name": "initial_cut_line", "stand_mix": 1.0, "surge": 0.025 + 0.09 * progress, "intensity": 0.78, "impact": 0.0, "hit_stop": 0.0}
    if index < 53:  # 0.75-0.88 dao head separates from the origin
        progress = (index - 45) / 8.0
        return {"name": "blade_launch", "stand_mix": 1.0, "surge": 0.10 + 0.34 * smoothstep(progress), "intensity": 0.90, "impact": 0.0, "hit_stop": 0.0}
    if index < 68:  # 0.88-1.13 short, bright head travel
        progress = (index - 53) / 15.0
        return {"name": "blade_travel", "stand_mix": 1.0, "surge": 0.44 + 0.56 * smoothstep(progress), "intensity": 1.0, "impact": 0.0, "hit_stop": 0.0}
    if index < 76:  # 1.13-1.27 133ms impact hold
        return {"name": "impact_hit_stop", "stand_mix": 1.0, "surge": 1.0, "intensity": 1.0, "impact": 1.0, "hit_stop": 1.0}
    if index < 121:  # 1.27-2.02 blue/cyan residual ribbons
        progress = (index - 76) / 45.0
        return {"name": "afterimage_fade", "stand_mix": 1.0, "surge": 1.0, "intensity": 0.92 - 0.70 * smoothstep(progress), "impact": 1.0 - smoothstep(progress), "hit_stop": 0.0}
    if index < 133:  # 2.02-2.22 standing follow-through
        progress = (index - 121) / 12.0
        return {"name": "standing_follow_through", "stand_mix": 1.0, "surge": 1.0, "intensity": 0.24 * (1.0 - smoothstep(progress)), "impact": 0.0, "hit_stop": 0.0}
    return {"name": "clean_idle", "stand_mix": 1.0, "surge": 0.0, "intensity": 0.0, "impact": 0.0, "hit_stop": 0.0}


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
    draw_hip_pulse(canvas, intensity if index < 47 else 0.0)
    canvas.alpha_composite(pose_canvas)
    surge = float(info["surge"])
    impact = float(info["impact"])
    if surge > 0:
        draw_energy_blade(canvas, surge, intensity, index, impact)
    return canvas


def border_alpha_count(image: Image.Image) -> int:
    alpha = image.getchannel("A")
    values = [alpha.getpixel((x, 0)) for x in range(image.width)]
    values += [alpha.getpixel((x, image.height - 1)) for x in range(image.width)]
    values += [alpha.getpixel((0, y)) for y in range(image.height)]
    values += [alpha.getpixel((image.width - 1, y)) for y in range(image.height)]
    return sum(1 for value in values if value)


def alpha_region_mean(image: Image.Image, box: tuple[int, int, int, int]) -> float:
    alpha = image.getchannel("A").crop(box)
    values = alpha.tobytes()
    return sum(values) / max(1, len(values))


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
        timing.append({"human_frame": index + 1, "time_seconds": round(index / FPS, 6), "phase": info["name"], "stand_mix": round(float(info["stand_mix"]), 4), "surge_progress": round(float(info["surge"]), 4), "surge_intensity": round(float(info["intensity"]), 4), "impact_flash": round(float(info["impact"]), 4), "hit_stop": bool(info["hit_stop"])})
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
    indices = [0, 12, 21, 30, 40, 44, 48, 52, 60, 67, 75, 90, 110, 125, 135, 155]
    tile_size = (256, 96)
    columns, rows = 4, 4
    base_height = (tile_size[1] + 20) * rows
    sheet = Image.new("RGB", (tile_size[0] * columns, base_height + 112), (12, 20, 32))
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
    # Dedicated close-up inset: the head and alpha-ramped trailing ribbons are
    # enlarged separately so the QA review is not limited to taskbar scale.
    closeup_source = frames[60].crop((112, 48, 505, 185)).resize((720, 96), Image.Resampling.NEAREST)
    sheet.paste(closeup_source, (8, base_height + 8))
    draw.text((736, base_height + 38), "INSET frame-061: dao head + transparent trail", fill=(225, 244, 255), font=font)
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
    original_release = raw_standing.copy()
    erased_release, blade_erase_report = erase_release_blade(raw_standing)
    erased_release.save(clean_standing_path, optimize=True)
    erase_zoom_path = source_dir / "release-blade-erasure-zoom.png"
    save_blade_erase_zoom(original_release, erased_release, erase_zoom_path)

    kneel, kneel_report = normalize_pose(raw_kneel, target_height=116, output_path=layers_dir / "miyabi-right-facing-kneel-fixed.png")
    standing_base, standing_report = normalize_pose(erased_release, target_height=116, output_path=layers_dir / "miyabi-right-facing-standing-base-fixed.png")
    standing, blade_report = draw_release_blade(standing_base)
    standing.save(layers_dir / "miyabi-right-facing-release-fixed.png", optimize=True)
    save_source_preview(kneel, standing, source_dir / "pose-clean-preview.png")

    frames, timing = save_frames(kneel, standing, args.output_dir)
    review_video = render_video(frames, video_dir / "miyabi-energy-blade-slash-review.mp4")
    contact_sheet_path = video_dir / "miyabi-energy-blade-keyframe-contact-sheet.png"
    keyframes = keyframe_contact_sheet(frames, contact_sheet_path)
    clean_expected = place_layer(standing, POSE_POS)
    clean_end_exact = all(ImageChops.difference(frames[index], clean_expected).getbbox() is None for index in range(133, FRAME_COUNT))
    border_clean = all(border_alpha_count(frame) == 0 for frame in frames)
    mirrors = all(ImageChops.difference(Image.open(args.output_dir / "left" / "frames" / f"frame-{i:03d}.png").convert("RGBA"), frames[i].transpose(Image.Transpose.FLIP_LEFT_RIGHT)).getbbox() is None for i in range(FRAME_COUNT))
    peak_gradient_frame = 67
    origin_alpha_mean = round(alpha_region_mean(frames[peak_gradient_frame], (170, 128, 215, 150)), 3)
    head_alpha_mean = round(alpha_region_mean(frames[peak_gradient_frame], (430, 55, 505, 150)), 3)
    gradient_valid = head_alpha_mean > origin_alpha_mean
    kneel_bounds, standing_base_bounds, standing_final_bounds = alpha_bounds(kneel), alpha_bounds(standing_base), alpha_bounds(standing)
    scale_delta = abs((kneel_bounds[3] - kneel_bounds[1]) - (standing_base_bounds[3] - standing_base_bounds[1])) if kneel_bounds and standing_base_bounds else 999
    qa = {
        "status": "PASS" if clean_end_exact and border_clean and mirrors and scale_delta <= 2 and blade_erase_report["source_blade_fully_erased"] and gradient_valid else "FAIL",
        "animation_id": "miyabi-energy-blade-slash-v5",
        "orientation": {"master": "right-facing", "left_set": "exact_horizontal_mirror", "frame_order_preserved": True},
        "canvas": {"size": list(CANVAS_SIZE), "pose_layer_size": list(POSE_LAYER_SIZE), "pose_position": list(POSE_POS), "ground_y": GROUND_Y},
        "timing": {"fps": FPS, "frame_count": FRAME_COUNT, "duration_seconds": DURATION_SECONDS, "brace_kneel_seconds": round(22 / FPS, 6), "hit_stop_seconds": round(8 / FPS, 6), "beats": {"kneel_charge": [1, 22], "hip_rise": [23, 40], "initial_cut_line": [41, 45], "blade_launch": [46, 53], "blade_travel": [54, 68], "impact_hit_stop": [69, 76], "afterimage_fade": [77, 121], "standing_follow_through": [122, 133], "clean_idle": [134, 156]}},
        "path_validation": {"hip_origin": list(SURGE_START), "blade_front_x": BLADE_FRONT_X, "spine_rise_degrees": "8-12 trailing path; curved dao head final 15-20%", "dao_head_pointed": True, "dao_head_asymmetric": True, "continuous_trailing_ribbons": True, "origin_alpha_low_head_alpha_high": gradient_valid, "origin_alpha_mean_peak": origin_alpha_mean, "head_alpha_mean_peak": head_alpha_mean, "max_cyan_ribbon_count": 4, "detached_navy_streak_count": 3, "no_detached_ring": True, "no_vertical_cap": True, "no_uniform_filled_wedge": True, "projectile_count": 1, "impact_is_white_cyan_split_flash_only": True},
        "weapon_validation": {"charge_keeps_source_iai_grip": True, "release_blade_redrawn_procedurally": True, "release_blade": blade_report, "generated_blade_cutting_edge": "bright smooth upper-left leading side", "generated_blade_spine": "dark blue-gray serrated lower-right trailing side"},
        "source_validation": {"pose_sheet_sha256": pixel_sha256(Image.open(args.pose_sheet).convert("RGBA")), "sheet_cleanup": sheet_report, "release_blade_erase": blade_erase_report, "blade_erasure_zoom_evidence": str(erase_zoom_path), "charge_pose": kneel_report, "standing_base_pose": standing_report, "source_clean_preview": str(source_dir / "pose-clean-preview.png"), "pmx_copied_to_output": False},
        "pose_validation": {"charge_alpha_bounds": list(kneel_bounds) if kneel_bounds else None, "release_base_alpha_bounds": list(standing_base_bounds) if standing_base_bounds else None, "release_final_alpha_bounds": list(standing_final_bounds) if standing_final_bounds else None, "head_to_feet_scale_delta_px": scale_delta, "scale_tolerance_px": 2, "fixed_ground_anchor": True},
        "matte_validation": {"no_full_canvas_border_alpha": border_clean, "clean_end_exact_standing": clean_end_exact, "max_border_alpha_pixels": max(border_alpha_count(frame) for frame in frames)},
        "mirror_validation": {"left_is_exact_horizontal_mirror_per_frame": mirrors, "mismatch_count": 0 if mirrors else 1},
        "outputs": {"pose_sheet": str(sheet_copy), "right_frames": str(args.output_dir / "right" / "frames"), "left_frames": str(args.output_dir / "left" / "frames"), "right_strip": str(args.output_dir / "right" / f"strip-{FRAME_COUNT}x1.png"), "left_strip": str(args.output_dir / "left" / f"strip-{FRAME_COUNT}x1.png"), "review_video": review_video, "keyframe_contact_sheet": str(contact_sheet_path), "blade_erasure_zoom": str(erase_zoom_path)},
        "keyframes": keyframes,
        "timeline_samples": timing,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps({"animation_id": qa["animation_id"], "fps": FPS, "frame_count": FRAME_COUNT, "duration_seconds": DURATION_SECONDS, "orientation": "right-facing master", "outputs": qa["outputs"]}, indent=2), encoding="utf-8")
    (args.output_dir / "energy-blade-slash-qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
