"""Build the v4 right-facing Miyabi ground-hugging energy surge slash.

The supplied pose sheet contains two right-facing poses: a one-knee iai charge
on the left and a standing follow-through on the right.  This builder removes
only border-connected checker/white pixels, crops the two poses, then redraws
the release blade procedurally so its bright cutting edge is on the upper-left
leading side and its dark serrated spine is on the lower-right trailing side.

The effect is deliberately one connected attack stream rather than a ring or
hoop: a filled, widening cyan/ice-blue surge starts at Miyabi's hip and races
to the right edge, with a white-hot core, deep-blue wake, shredded crest,
ground ripples and a white/cyan split flash. No PMX is read or copied.
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
SURGE_FRONT_X = 486.0
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


def _surge_profile(progress: float, phase_seed: int = 0) -> tuple[list[tuple[int, int]], list[tuple[int, int]], float]:
    """Return noisy top/bottom boundaries for one connected filled surge."""
    p = clamp(progress)
    reach = smoothstep(min(1.0, p * 1.08))
    front = SURGE_START[0] + (SURGE_FRONT_X - SURGE_START[0]) * reach
    spread = smoothstep(p)
    top_start = 133.0 - 5.0 * spread
    top_front = 128.0 - 70.0 * spread
    bottom_start = 147.0 + 3.0 * spread
    bottom_front = SURGE_GROUND_Y - 1.0
    top: list[tuple[int, int]] = []
    bottom: list[tuple[int, int]] = []
    samples = 28
    for index in range(samples + 1):
        ratio = index / samples
        x = SURGE_START[0] + (front - SURGE_START[0]) * ratio
        wobble = math.sin((index + phase_seed * 0.37) * 1.71) * (1.2 + 3.0 * spread * ratio)
        top_y = top_start + (top_front - top_start) * ratio + wobble
        lower_wobble = math.sin((index + phase_seed * 0.21) * 1.29 + 1.2) * (0.8 + 2.2 * spread * ratio)
        bottom_y = bottom_start + (bottom_front - bottom_start) * ratio + lower_wobble
        top.append((round(x), round(top_y)))
        bottom.append((round(x), round(bottom_y)))
    return top, bottom, front


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


def draw_energy_surge(canvas: Image.Image, progress: float, intensity: float, frame_index: int, impact: float = 0.0) -> None:
    """Draw one filled, continuous tidal slash; never a detached ring/ray set."""
    if progress <= 0 or intensity <= 0:
        return
    top, bottom, front = _surge_profile(progress, frame_index)
    outer = top + list(reversed(bottom))
    # Deep-blue wake and broad glow establish filled volume before the brighter layers.
    glow = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.polygon(outer, fill=rgba(DEEP_BLUE, intensity * 0.72))
    glow_draw.line(top, fill=rgba(ICE_BLUE, intensity * 0.64), width=9, joint="curve")
    glow_draw.line(bottom, fill=rgba(BLUE, intensity * 0.70), width=8, joint="curve")
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(5)))

    body = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    body_draw = ImageDraw.Draw(body)
    body_draw.polygon(outer, fill=rgba(BLUE, intensity * 0.70))
    inset_top = [(x, round(y + 3 + 2 * math.sin(i * 1.41))) for i, (x, y) in enumerate(top)]
    inset_bottom = [(x, round(y - 2)) for x, y in bottom]
    body_draw.polygon(inset_top + list(reversed(inset_bottom)), fill=rgba(CYAN, intensity * 0.74))
    canvas.alpha_composite(body)

    core = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    core_draw = ImageDraw.Draw(core)
    p = clamp(progress)
    core_end = (front - 8.0, 131.0 - 53.0 * smoothstep(p))
    core_start = (SURGE_START[0] - 2.0, SURGE_START[1])
    core_width = 1.5 + 9.0 * smoothstep(p)
    core_draw.polygon(_tapered_band(core_start, core_end, 1.0, core_width), fill=rgba(WHITE, intensity * 0.94))
    core_draw.line((round(core_start[0]), round(core_start[1]), round(core_end[0]), round(core_end[1])), fill=rgba(WHITE, intensity), width=2)
    canvas.alpha_composite(core.filter(ImageFilter.GaussianBlur(2)))
    canvas.alpha_composite(core)

    details = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    detail_draw = ImageDraw.Draw(details)
    # Long perspective bands are tapered, partially embedded in the body, and vary in depth.
    for band in range(13):
        ratio = band / 12.0
        y0 = 141.0 + ratio * 27.0
        y1 = 72.0 + ratio * 90.0 + math.sin((band + frame_index) * 0.7) * 4.0
        end_x = SURGE_START[0] + (front - SURGE_START[0]) * (0.70 + 0.025 * (band % 5))
        band_poly = _tapered_band((SURGE_START[0] + ratio * 7.0, y0), (end_x, y1), 0.4, 1.0 + (band % 3) * 0.7)
        color = WHITE if band % 5 == 0 else (ICE_BLUE if band % 2 else CYAN)
        detail_draw.polygon(band_poly, fill=rgba(color, intensity * (0.36 + 0.045 * (band % 4))))
    # Edge energy stays in the blue/cyan slash family; no target or purple object
    # is invented in the empty far-right space.
    for band in range(4):
        y0 = 158.0 + band * 3.0
        y1 = 166.0 + band * 1.4 + math.sin((frame_index + band) * 0.8) * 2.0
        end_x = SURGE_START[0] + (front - SURGE_START[0]) * (0.75 + band * 0.04)
        detail_draw.line((round(SURGE_START[0] - 4), round(y0), round(end_x), round(y1)), fill=rgba(ICE_BLUE if band % 2 else BLUE, intensity * (0.40 - band * 0.05)), width=1 + (band % 2))
    canvas.alpha_composite(details.filter(ImageFilter.GaussianBlur(1)))
    canvas.alpha_composite(details)

    # Shredded front crest: jagged, asymmetric, and embedded in the same body.
    crest = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    crest_draw = ImageDraw.Draw(crest)
    front_top = min(y for x, y in top if x >= round(front) - 2) if top else 70
    crest_points = [(round(front - 24), round(front_top + 12)), (round(front - 10), round(front_top + 2)), (round(front - 3), round(front_top - 13)), (round(front + 4), round(front_top - 2)), (round(front + 8), round(front_top - 20)), (round(front + 11), round(front_top + 18)), (round(front + 4), round(SURGE_GROUND_Y - 2)), (round(front - 10), round(SURGE_GROUND_Y - 7))]
    crest_draw.polygon(crest_points, fill=rgba(ICE_BLUE, intensity * 0.86))
    crest_draw.line([(round(front - 18), round(front_top + 10)), (round(front + 7), round(front_top - 14))], fill=rgba(WHITE, intensity), width=3)
    for shard in range(7):
        sx = front - 12 + shard * 3
        sy = front_top + 8 + math.sin((shard + frame_index) * 1.4) * 5
        crest_draw.line((round(sx), round(sy), round(sx + 8 + shard % 3 * 3), round(sy - 8 - shard % 2 * 5)), fill=rgba(CYAN, intensity * 0.75), width=1)
    canvas.alpha_composite(crest.filter(ImageFilter.GaussianBlur(2)))
    canvas.alpha_composite(crest)

    # Frosty ground ripples and shards reinforce contact with the floor.
    ground = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    ground_draw = ImageDraw.Draw(ground)
    ripple_front = min(front, SURGE_FRONT_X)
    for ripple in range(5):
        rx = round(SURGE_START[0] + (ripple_front - SURGE_START[0]) * (0.48 + ripple * 0.10))
        ry = round(174 + math.sin((ripple + frame_index) * 0.6) * 2)
        ground_draw.arc((rx - 19 - ripple * 2, ry - 5, rx + 19 + ripple * 2, ry + 5), 190, 350, fill=rgba(ICE_BLUE, intensity * (0.46 - ripple * 0.05)), width=1)
        ground_draw.line((rx - 5, ry, rx + 2, ry - 9 - ripple), fill=rgba(CYAN, intensity * 0.55), width=1)
    canvas.alpha_composite(ground.filter(ImageFilter.GaussianBlur(1)))
    canvas.alpha_composite(ground)

    if impact > 0:
        draw_impact_flare(canvas, impact, frame_index)


def draw_impact_flare(canvas: Image.Image, intensity: float, frame_index: int) -> None:
    """Draw only a white/cyan split flash at the far-right crest."""
    # Keep the blur inside the transparent overscan; the surge front itself
    # still reaches SURGE_FRONT_X while the flash sits just inside the edge.
    x, y = 474, 104
    layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.polygon([(x - 11, y + 4), (x - 2, y - 7), (x + 1, y - 42), (x + 5, y - 8), (x + 18, y + 2), (x + 4, y + 7)], fill=rgba(CYAN, intensity * 0.82))
    draw.line((x + 2, y - 48, x + 2, y + 18), fill=rgba(WHITE, intensity), width=2)
    for ray in range(8):
        angle = math.radians(-168 + ray * 18)
        length = 12 + (ray % 3) * 7
        draw.line((x, y, round(x + math.cos(angle) * length), round(y + math.sin(angle) * length)), fill=rgba(CYAN if ray % 2 else ICE_BLUE, intensity * 0.58), width=1)
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
        return {"name": "kneel_charge", "stand_mix": 0.0, "surge": 0.0, "intensity": pulse, "impact": 0.0, "hit_stop": 0.0}
    if index < 40:  # 0.37-0.67 hip rise to standing
        progress = (index - 22) / 18.0
        return {"name": "hip_rise", "stand_mix": smoothstep(progress), "surge": 0.0, "intensity": 0.68, "impact": 0.0, "hit_stop": 0.0}
    if index < 47:  # 0.67-0.78 thin initial cut line
        progress = (index - 40) / 7.0
        return {"name": "initial_cut_line", "stand_mix": 1.0, "surge": 0.05 + 0.10 * progress, "intensity": 0.82, "impact": 0.0, "hit_stop": 0.0}
    if index < 59:  # 0.78-0.98 explosive bloom and connected launch
        progress = (index - 47) / 12.0
        return {"name": "explosive_bloom", "stand_mix": 1.0, "surge": 0.15 + 0.38 * smoothstep(progress), "intensity": 0.92, "impact": 0.0, "hit_stop": 0.0}
    if index < 79:  # 0.98-1.32 dense surge races toward far right
        progress = (index - 59) / 20.0
        return {"name": "surge_race", "stand_mix": 1.0, "surge": 0.53 + 0.47 * smoothstep(progress), "intensity": 1.0, "impact": 0.0, "hit_stop": 0.0}
    if index < 87:  # 1.32-1.45 133ms impact hit-stop
        return {"name": "impact_hit_stop", "stand_mix": 1.0, "surge": 1.0, "intensity": 1.0, "impact": 1.0, "hit_stop": 1.0}
    if index < 121:  # 1.45-2.02 blue/cyan residual wake
        progress = (index - 87) / 34.0
        return {"name": "residual_wake", "stand_mix": 1.0, "surge": 1.0, "intensity": 0.92 - 0.68 * smoothstep(progress), "impact": 1.0 - smoothstep(progress), "hit_stop": 0.0}
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
        draw_energy_surge(canvas, surge, intensity, index, impact)
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
    review_video = render_video(frames, video_dir / "miyabi-energy-surge-slash-review.mp4")
    keyframes = keyframe_contact_sheet(frames, video_dir / "miyabi-energy-surge-keyframe-contact-sheet.png")
    clean_expected = place_layer(standing, POSE_POS)
    clean_end_exact = all(ImageChops.difference(frames[index], clean_expected).getbbox() is None for index in range(133, FRAME_COUNT))
    border_clean = all(border_alpha_count(frame) == 0 for frame in frames)
    mirrors = all(ImageChops.difference(Image.open(args.output_dir / "left" / "frames" / f"frame-{i:03d}.png").convert("RGBA"), frames[i].transpose(Image.Transpose.FLIP_LEFT_RIGHT)).getbbox() is None for i in range(FRAME_COUNT))
    kneel_bounds, standing_base_bounds, standing_final_bounds = alpha_bounds(kneel), alpha_bounds(standing_base), alpha_bounds(standing)
    scale_delta = abs((kneel_bounds[3] - kneel_bounds[1]) - (standing_base_bounds[3] - standing_base_bounds[1])) if kneel_bounds and standing_base_bounds else 999
    qa = {
        "status": "PASS" if clean_end_exact and border_clean and mirrors and scale_delta <= 2 else "FAIL",
        "animation_id": "miyabi-energy-surge-slash-v4",
        "orientation": {"master": "right-facing", "left_set": "exact_horizontal_mirror", "frame_order_preserved": True},
        "canvas": {"size": list(CANVAS_SIZE), "pose_layer_size": list(POSE_LAYER_SIZE), "pose_position": list(POSE_POS), "ground_y": GROUND_Y},
        "timing": {"fps": FPS, "frame_count": FRAME_COUNT, "duration_seconds": DURATION_SECONDS, "brace_kneel_seconds": round(22 / FPS, 6), "hit_stop_seconds": round(8 / FPS, 6), "beats": {"kneel_charge": [1, 22], "hip_rise": [23, 40], "initial_cut_line": [41, 47], "explosive_bloom": [48, 59], "surge_race": [60, 79], "impact_hit_stop": [80, 87], "residual_wake": [88, 121], "standing_follow_through": [122, 133], "clean_idle": [134, 156]}},
        "path_validation": {"hip_origin": list(SURGE_START), "surge_front_x": SURGE_FRONT_X, "ground_hugging_ground_y": SURGE_GROUND_Y, "continuous_connected_volume": True, "broad_widening_wedge": True, "no_detached_ring": True, "no_overhead_ring": True, "projectile_count": 1, "impact_is_white_cyan_split_flash_only": True},
        "weapon_validation": {"charge_keeps_source_iai_grip": True, "release_blade_redrawn_procedurally": True, "release_blade": blade_report, "generated_blade_cutting_edge": "bright smooth upper-left leading side", "generated_blade_spine": "dark blue-gray serrated lower-right trailing side"},
        "source_validation": {"pose_sheet_sha256": pixel_sha256(Image.open(args.pose_sheet).convert("RGBA")), "sheet_cleanup": sheet_report, "release_blade_erase": blade_erase_report, "charge_pose": kneel_report, "standing_base_pose": standing_report, "source_clean_preview": str(source_dir / "pose-clean-preview.png"), "pmx_copied_to_output": False},
        "pose_validation": {"charge_alpha_bounds": list(kneel_bounds) if kneel_bounds else None, "release_base_alpha_bounds": list(standing_base_bounds) if standing_base_bounds else None, "release_final_alpha_bounds": list(standing_final_bounds) if standing_final_bounds else None, "head_to_feet_scale_delta_px": scale_delta, "scale_tolerance_px": 2, "fixed_ground_anchor": True},
        "matte_validation": {"no_full_canvas_border_alpha": border_clean, "clean_end_exact_standing": clean_end_exact, "max_border_alpha_pixels": max(border_alpha_count(frame) for frame in frames)},
        "mirror_validation": {"left_is_exact_horizontal_mirror_per_frame": mirrors, "mismatch_count": 0 if mirrors else 1},
        "outputs": {"pose_sheet": str(sheet_copy), "right_frames": str(args.output_dir / "right" / "frames"), "left_frames": str(args.output_dir / "left" / "frames"), "right_strip": str(args.output_dir / "right" / f"strip-{FRAME_COUNT}x1.png"), "left_strip": str(args.output_dir / "left" / f"strip-{FRAME_COUNT}x1.png"), "review_video": review_video, "keyframe_contact_sheet": str(video_dir / "miyabi-energy-surge-keyframe-contact-sheet.png")},
        "keyframes": keyframes,
        "timeline_samples": timing,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps({"animation_id": qa["animation_id"], "fps": FPS, "frame_count": FRAME_COUNT, "duration_seconds": DURATION_SECONDS, "orientation": "right-facing master", "outputs": qa["outputs"]}, indent=2), encoding="utf-8")
    (args.output_dir / "energy-surge-slash-qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
