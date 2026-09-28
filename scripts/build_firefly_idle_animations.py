"""Build Firefly's module/sword idle and full SAM transformation cycle.

The script keeps the generated art as a small set of reviewed key poses, then
adds deterministic pixel VFX, exact timing, directional mirroring and 60 FPS
review videos. Runtime assets remain compact: the SAM's 60 second stay is a
32-frame loop plus a repeat duration, not 3,600 duplicated PNG files. Firefly's
human animation uses a denser authored cadence so it stays crisp without the
double-exposure look produced by alpha-crossfading distant poses.
"""

from __future__ import annotations

import argparse
from collections import deque
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw

from build_layered_miyabi_demo import desktop_background
from process_pixel_sprite_sheet import remove_edge_background
from remove_white_matte_fringe import clean_fringe


CELL = 128
HUMAN_CANVAS_WIDTH = 160
HUMAN_CANVAS_HEIGHT = 144
HUMAN_ANCHOR_RIGHT = (64, 120)
HUMAN_ANCHOR_LEFT = (HUMAN_CANVAS_WIDTH - HUMAN_ANCHOR_RIGHT[0], HUMAN_ANCHOR_RIGHT[1])
HUMAN_DURATION = 10.95
HUMAN_LOGICAL_FPS = 15
SAM_HOVER_LOGICAL_FRAMES = 32
SAM_HOVER_LOGICAL_FPS = 16
SAM_ACTIVATION_SECONDS = 1.2
SAM_ASSEMBLY_SECONDS = 2.4
SAM_DEPLOY_SECONDS = 0.9
SAM_LANDING_SECONDS = 1.8
SAM_CAPE_OFF_SECONDS = 0.9
SAM_SHOULDER_FIRE_OFF_SECONDS = 0.6
SAM_SWORDS_OFF_SECONDS = 0.8
SAM_ARMOR_OFF_SECONDS = 2.5
SAM_RESTORED_HOLD_SECONDS = 0.8

# Source-space boxes deliberately overlap the nominal 4x2 grid when a sword
# crosses a cell boundary.  Each box is still isolated from the neighbouring
# character body.  The anchor maps the character's baseline into (64, 120).
POSE_SPECS = [
    ((35, 175, 305, 590), (160, 575)),
    ((345, 175, 610, 590), (475, 575)),
    ((615, 155, 905, 625), (770, 575)),
    ((885, 175, 1254, 625), (1070, 575)),
    ((15, 735, 435, 1110), (155, 1090)),
    ((405, 730, 710, 1145), (550, 1110)),
    ((695, 730, 990, 1145), (840, 1110)),
    ((950, 730, 1254, 1145), (1100, 1110)),
]
SOURCE_TO_SPRITE_SCALE = 0.278

HUMAN_PHASES = [
    ("module-ready", 0.0, 0.8, 0),
    ("module-burnout", 0.8, 2.0, 1),
    ("module-gone-gap", 2.0, 2.16, 2),
    ("half-sword-forming", 2.16, 3.1, 2),
    ("full-sword-windup", 3.1, 3.9, 3),
    ("single-forward-slash", 3.9, 4.28, 4),
    ("return-to-guard", 4.28, 5.05, 5),
    ("mote-approach", 5.05, 6.15, 5),
    ("mote-inspection", 6.15, 7.65, 5),
    ("mote-fade-before-retraction", 7.65, 8.25, 5),
    ("tip-to-hilt-retraction", 8.25, 9.75, 6),
    ("module-restored", 9.75, HUMAN_DURATION, 7),
]


def stable_cleanup(image: Image.Image) -> Image.Image:
    result = image.convert("RGBA")
    for _ in range(8):
        result, changed = clean_fringe(result, max_distance=2)
        if changed == 0:
            break
    return result


def keep_subject_and_mote(image: Image.Image) -> Image.Image:
    """Remove disconnected neighbouring-cell debris while retaining the mote."""
    result = image.copy()
    alpha = result.getchannel("A")
    pixels = alpha.load()
    seen: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    width, height = result.size
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0 or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            component: list[tuple[int, int]] = []
            while queue:
                px, py = queue.popleft()
                component.append((px, py))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = px + dx, py + dy
                        if (
                            0 <= nx < width
                            and 0 <= ny < height
                            and pixels[nx, ny] > 0
                            and (nx, ny) not in seen
                        ):
                            seen.add((nx, ny))
                            queue.append((nx, ny))
            components.append(component)
    if not components:
        return result
    subject = max(components, key=len)
    keep = set(subject)
    for component in components:
        if component is subject:
            continue
        x0 = min(point[0] for point in component)
        x1 = max(point[0] for point in component) + 1
        y0 = min(point[1] for point in component)
        y1 = max(point[1] for point in component) + 1
        center = ((x0 + x1) / 2, (y0 + y1) / 2)
        if len(component) <= 100 and 78 <= center[0] <= 100 and 45 <= center[1] <= 72:
            keep.update(component)
    rp = result.load()
    for y in range(height):
        for x in range(width):
            if rp[x, y][3] and (x, y) not in keep:
                rp[x, y] = (0, 0, 0, 0)
    return result


def load_keyposes(source_path: Path, output_dir: Path) -> list[Image.Image]:
    source = remove_edge_background(Image.open(source_path).convert("RGBA"))
    poses: list[Image.Image] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, (box, anchor) in enumerate(POSE_SPECS):
        crop = source.crop(box)
        width = max(1, round(crop.width * SOURCE_TO_SPRITE_SCALE))
        height = max(1, round(crop.height * SOURCE_TO_SPRITE_SCALE))
        crop = crop.resize((width, height), Image.Resampling.NEAREST)
        local_anchor = (
            round((anchor[0] - box[0]) * SOURCE_TO_SPRITE_SCALE),
            round((anchor[1] - box[1]) * SOURCE_TO_SPRITE_SCALE),
        )
        position = (
            HUMAN_ANCHOR_RIGHT[0] - local_anchor[0],
            HUMAN_ANCHOR_RIGHT[1] - local_anchor[1],
        )
        # Human action frames have horizontal overscan. The old 128 px cell
        # clipped the outer slash arc at x=127 even though the source crop still
        # contained those pixels. Character scale and baseline stay unchanged.
        canvas = Image.new(
            "RGBA", (HUMAN_CANVAS_WIDTH, HUMAN_CANVAS_HEIGHT), (0, 0, 0, 0)
        )
        canvas.alpha_composite(crop, position)
        canvas = stable_cleanup(canvas)
        if index in (2, 4, 5, 6, 7):
            canvas = keep_subject_and_mote(canvas)
        canvas.save(output_dir / f"keypose-{index + 1:02d}.png", optimize=True)
        poses.append(canvas)
    return poses


def pose_motion(
    image: Image.Image,
    *,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
    shear: float = 0.0,
    dx: float = 0.0,
    dy: float = 0.0,
    pivot: tuple[float, float] = (64.0, 120.0),
) -> Image.Image:
    """Apply a crisp, baseline-anchored affine tween to a reviewed pose."""
    px, py = pivot
    cx = px - scale_x * px + shear * py + dx
    cy = py - scale_y * py + dy
    coefficients = (
        1.0 / scale_x,
        shear / (scale_x * scale_y),
        -cx / scale_x - shear * cy / (scale_x * scale_y),
        0.0,
        1.0 / scale_y,
        -cy / scale_y,
    )
    return image.transform(
        image.size,
        Image.Transform.AFFINE,
        coefficients,
        resample=Image.Resampling.NEAREST,
        fillcolor=(0, 0, 0, 0),
    )


def eased(progress: float) -> float:
    progress = max(0.0, min(1.0, progress))
    return progress * progress * (3.0 - 2.0 * progress)


def remove_baked_mote(image: Image.Image) -> Image.Image:
    """Remove the detached source-sheet mote so timeline order is controllable."""
    result = image.copy()
    alpha = result.getchannel("A")
    pixels = alpha.load()
    seen: set[tuple[int, int]] = set()
    clear: set[tuple[int, int]] = set()
    width, height = result.size
    for start_y in range(height):
        for start_x in range(width):
            if not pixels[start_x, start_y] or (start_x, start_y) in seen:
                continue
            queue = deque([(start_x, start_y)])
            seen.add((start_x, start_y))
            component: list[tuple[int, int]] = []
            while queue:
                x, y = queue.popleft()
                component.append((x, y))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if (
                            0 <= nx < width
                            and 0 <= ny < height
                            and pixels[nx, ny]
                            and (nx, ny) not in seen
                        ):
                            seen.add((nx, ny))
                            queue.append((nx, ny))
            x0 = min(x for x, _ in component)
            x1 = max(x for x, _ in component)
            y0 = min(y for _, y in component)
            y1 = max(y for _, y in component)
            center = ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
            if len(component) <= 140 and 78 <= center[0] <= 108 and 42 <= center[1] <= 78:
                clear.update(component)
    rp = result.load()
    for x, y in clear:
        rp[x, y] = (0, 0, 0, 0)
    return result


def fading_mote(draw: ImageDraw.ImageDraw, center: tuple[int, int], tick: int, visibility: float) -> None:
    """Draw the green light shrinking to nothing before sword retraction."""
    visibility = max(0.0, min(1.0, visibility))
    if visibility <= 0.02:
        return
    x, y = center
    alpha = max(1, round(255 * visibility))
    draw.point((x, y), fill=(224, 255, 164, alpha))
    if visibility > 0.28:
        draw.point((x + 1, y), fill=(128, 255, 117, alpha))
        draw.point((x, y + 1), fill=(78, 232, 145, alpha))
    if visibility > 0.62 and tick % 3 == 0:
        draw.point((x - 2, y - 1), fill=(62, 220, 155, round(alpha * 0.8)))


def human_authored_frame(
    poses: list[Image.Image],
    phase: str,
    progress: float,
    tick: int,
) -> Image.Image:
    """Draw one crisp human frame without crossfading distant silhouettes."""
    progress = max(0.0, min(1.0, progress))
    motion = eased(progress)
    breathing = -1 if math.sin(tick * math.tau / 20.0) > 0.72 else 0

    if phase == "module-ready":
        frame = pose_motion(poses[0], dy=breathing)
    elif phase == "module-burnout":
        # The body and module remain a single readable silhouette while the
        # procedural fire grows. This avoids the old doubled face/hair edges.
        frame = pose_motion(poses[0], dy=breathing)
        draw = ImageDraw.Draw(frame)
        flame_path(draw, (86, 60), (48, 72), motion * 0.7, tick, density=16)
        pixel_flame(draw, 84, 61, tick, strength=max(2, round(2 + motion * 6)))
        if progress > 0.55:
            pixel_flame(draw, 76, 68, tick + 4, strength=max(2, round(motion * 4)))
    elif phase == "module-gone-gap":
        # The reviewed half-sword pose is used as a stable body, but the blade
        # starts fully erased. Fire crosses hands only after the module is gone.
        reveal = max(0.0, (progress - 0.48) / 0.52)
        frame = retract_sword(poses[2], 1.0 - reveal * 0.42, tick)
        draw = ImageDraw.Draw(frame)
        flame_path(draw, (82, 61), (40, 79), motion, tick, density=20)
        pixel_flame(draw, 40, 79, tick, strength=5)
    elif phase == "half-sword-forming":
        keep_fraction = 0.42 + 0.58 * motion
        frame = retract_sword(poses[3], 1.0 - keep_fraction, tick)
        draw = ImageDraw.Draw(frame)
        sword_start, sword_end = detect_human_sword_axis(poses[3])
        front = (
            round(sword_start[0] + (sword_end[0] - sword_start[0]) * keep_fraction),
            round(sword_start[1] + (sword_end[1] - sword_start[1]) * keep_fraction),
        )
        pixel_flame(draw, front[0], front[1], tick, strength=3)
        flame_path(draw, (round(sword_start[0]), round(sword_start[1])), front, 1.0, tick, density=18)
    elif phase == "full-sword-windup":
        # First compress the standing guard toward the crouched slash pose,
        # then complete the anticipation using the slash drawing itself. Both
        # halves stay opaque and crisp—there is never a double-exposed body.
        if progress < 0.68:
            local = eased(progress / 0.68)
            frame = pose_motion(
                poses[3],
                scale_x=1.0 + 0.10 * local,
                scale_y=1.0 - 0.10 * local,
                shear=-0.035 * local,
                dx=2.0 * local,
            )
        else:
            local = eased((progress - 0.68) / 0.32)
            frame = pose_motion(
                poses[4],
                scale_x=0.90 + 0.10 * local,
                scale_y=1.08 - 0.08 * local,
                dx=-3.0 * (1.0 - local),
            )
            draw = ImageDraw.Draw(frame)
            for index in range(8):
                draw.point((84 + index * 4, 92 - index), fill=(70, 224, 211, 150))
    elif phase == "single-forward-slash":
        arc = math.sin(progress * math.pi)
        frame = pose_motion(
            poses[4],
            scale_x=1.0 + 0.035 * arc,
            scale_y=1.0 - 0.025 * arc,
            dx=round(-2 + 5 * motion),
        )
        draw = ImageDraw.Draw(frame)
        for index in range(12):
            x = 76 + ((tick * 4 + index * 7) % 49)
            y = 82 + ((index * 5 - tick * 2) % 20)
            draw.point((x, y), fill=(70, 224, 211, 180))
    elif phase == "return-to-guard":
        if progress < 0.48:
            local = eased(progress / 0.48)
            frame = pose_motion(
                poses[4],
                scale_x=1.0 - 0.08 * local,
                scale_y=1.0 + 0.08 * local,
                dx=3.0 * (1.0 - local),
            )
        else:
            local = eased((progress - 0.48) / 0.52)
            frame = pose_motion(remove_baked_mote(poses[5]), dy=round(2 * (1.0 - local)))
        # No mote is allowed here: Firefly must finish returning to guard first.
        frame = remove_baked_mote(frame)
    elif phase == "mote-approach":
        frame = pose_motion(remove_baked_mote(poses[5]), dy=breathing)
        draw = ImageDraw.Draw(frame)
        # The light starts far to screen-right, follows a shallow curved path,
        # and only reaches Firefly's open hand at the end of this phase.
        mote_x = round(112 + (91 - 112) * motion)
        mote_y = round(45 + (61 - 45) * motion + math.sin(progress * math.tau) * 3)
        sparkle_mote(draw, (mote_x, mote_y), tick)
    elif phase == "mote-inspection":
        frame = pose_motion(remove_baked_mote(poses[5]), dy=breathing)
        draw = ImageDraw.Draw(frame)
        hover_x = 91 + (1 if tick % 10 in (0, 1, 2) else 0)
        hover_y = 61 + (-1 if tick % 12 in (0, 1, 2, 3) else 0)
        sparkle_mote(draw, (hover_x, hover_y), tick)
    elif phase == "mote-fade-before-retraction":
        frame = pose_motion(remove_baked_mote(poses[5]), dy=breathing)
        draw = ImageDraw.Draw(frame)
        fading_mote(draw, (91, 61), tick, 1.0 - motion)
    elif phase == "tip-to-hilt-retraction":
        # The green light is already completely gone before this branch starts.
        frame = retract_sword(remove_baked_mote(poses[5]), motion, tick)
    elif phase == "module-restored":
        if progress < 0.5:
            local = progress / 0.5
            frame = retract_sword(remove_baked_mote(poses[5]), 1.0, tick)
            draw = ImageDraw.Draw(frame)
            pixel_flame(draw, 40 + round(9 * local), 75 - round(7 * local), tick, strength=max(2, round(6 - local * 2)))
        else:
            local = (progress - 0.5) / 0.5
            frame = pose_motion(remove_baked_mote(poses[7]), dy=breathing)
            draw = ImageDraw.Draw(frame)
            if local < 0.78:
                pixel_flame(draw, 49, 68, tick, strength=max(1, round(4 * (1.0 - local))))
    else:
        raise ValueError(f"Unknown human phase: {phase}")
    return stable_cleanup(frame)


def build_human_logical_frames(poses: list[Image.Image]) -> tuple[list[Image.Image], list[str], list[int]]:
    """Create a dense 15 FPS authored stream inside the 60 FPS container.

    Unlike the old 32-frame stream, these frames use crisp affine in-betweens
    and progressive blade masks. The video repeats each authored pixel frame
    for four display ticks instead of alpha-blending two incompatible poses.
    """
    frames: list[Image.Image] = []
    phases: list[str] = []
    durations_ms: list[int] = []
    tick = 0
    for phase, start, end, _pose in HUMAN_PHASES:
        phase_ms = round((end - start) * 1000)
        count = max(2, round((end - start) * HUMAN_LOGICAL_FPS))
        base_duration, remainder = divmod(phase_ms, count)
        for local in range(count):
            progress = local / max(1, count - 1)
            frames.append(human_authored_frame(poses, phase, progress, tick))
            phases.append(phase)
            durations_ms.append(base_duration + (1 if local < remainder else 0))
            tick += 1
    if sum(durations_ms) != round(HUMAN_DURATION * 1000):
        raise RuntimeError("Human authored frame timing does not match HUMAN_DURATION")
    return frames, phases, durations_ms


def flame_path(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    progress: float,
    tick: int,
    density: int = 12,
) -> None:
    progress = max(0.0, min(1.0, progress))
    count = max(1, round(density * progress))
    colors = [(49, 238, 196, 235), (163, 255, 135, 235), (75, 204, 228, 220)]
    for index in range(count):
        amount = index / max(1, density - 1) * progress
        x = round(start[0] + (end[0] - start[0]) * amount)
        y = round(start[1] + (end[1] - start[1]) * amount)
        x += ((tick + index * 3) % 3) - 1
        y += ((tick * 2 + index) % 5) - 2
        draw.point((x, y), fill=colors[index % len(colors)])
        if index % 4 == 0:
            draw.point((x, y - 1), fill=colors[(index + 1) % len(colors)])


def detect_human_sword_axis(source: Image.Image) -> tuple[tuple[float, float], tuple[float, float]]:
    """Locate the reviewed down-left blade instead of assuming one fixed tip."""
    candidates: list[tuple[int, int]] = []
    for y in range(84, source.height):
        for x in range(0, min(58, source.width)):
            red, green, blue, alpha = source.getpixel((x, y))
            if alpha and blue > red + 8 and green > red + 3:
                candidates.append((x, y))
    if not candidates:
        return (46.0, 88.0), (24.0, 127.0)
    max_y = max(y for _, y in candidates)
    tip_xs = [x for x, y in candidates if y >= max_y - 2]
    hilt_xs = [x for x, y in candidates if 86 <= y <= 94]
    tip_x = sorted(tip_xs)[len(tip_xs) // 2]
    hilt_x = sorted(hilt_xs)[len(hilt_xs) // 2] if hilt_xs else max(x for x, _ in candidates)
    return (float(hilt_x), 88.0), (float(tip_x), float(min(source.height - 1, max_y + 1)))


def retract_sword(source: Image.Image, progress: float, tick: int) -> Image.Image:
    """Erase the remaining half blade from its tip toward the hilt."""
    result = source.copy()
    pixels = result.load()
    start, end = detect_human_sword_axis(source)
    vx, vy = end[0] - start[0], end[1] - start[1]
    length_sq = vx * vx + vy * vy
    keep_fraction = max(0.0, 1.0 - progress)
    front = (
        round(start[0] + vx * keep_fraction),
        round(start[1] + vy * keep_fraction),
    )
    for y in range(result.height):
        for x in range(result.width):
            if pixels[x, y][3] == 0:
                continue
            wx, wy = x - start[0], y - start[1]
            along = (wx * vx + wy * vy) / length_sq
            closest_x = start[0] + along * vx
            closest_y = start[1] + along * vy
            distance = math.hypot(x - closest_x, y - closest_y)
            if 0.02 <= along <= 1.12 and distance <= 10.0 and along > keep_fraction:
                pixels[x, y] = (0, 0, 0, 0)
    draw = ImageDraw.Draw(result)
    if progress < 1.0:
        pixel_flame(draw, front[0], front[1], tick, strength=3)
    return result


def pixel_flame(draw: ImageDraw.ImageDraw, x: int, y: int, tick: int, strength: int = 3) -> None:
    colors = [(51, 255, 194, 255), (44, 214, 190, 255), (169, 255, 142, 255)]
    for index in range(strength + 2):
        phase = (tick + index * 3) % 11
        px = x + ((phase * 5 + index * 2) % 7) - 3
        py = y - index * 3 - (phase % 3)
        color = colors[index % len(colors)]
        draw.point((px, py), fill=color)
        if index < strength:
            draw.point((px + (1 if index % 2 else -1), py + 1), fill=color)


def sparkle_mote(draw: ImageDraw.ImageDraw, center: tuple[int, int], tick: int) -> None:
    x, y = center
    pulse = tick % 8
    draw.point((x, y), fill=(224, 255, 164, 255))
    draw.point((x + 1, y), fill=(128, 255, 117, 255))
    draw.point((x, y + 1), fill=(78, 232, 145, 255))
    if pulse in (0, 1, 4):
        draw.point((x - 2, y - 1), fill=(62, 220, 155, 220))
    if pulse in (2, 5):
        draw.point((x + 2, y + 1), fill=(126, 255, 144, 210))


def erase_rect(image: Image.Image, box: tuple[int, int, int, int]) -> None:
    blank = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    image.paste(blank, (box[0], box[1]))


def sword_corridor_pixel(x: int, y: int) -> bool:
    if y < 58:
        return False
    left_x = 46.0 - 0.55 * (y - 58)
    right_x = 82.0 + 0.55 * (y - 58)
    return min(abs(x - left_x), abs(x - right_x)) <= 8


def energy_pixel(red: int, green: int, blue: int, x: int, y: int) -> bool:
    if not (8 <= y <= 112 and (x < 52 or x > 76)):
        return False
    # The approved SAM carries two long cyan swords.  Their blades stay rigid;
    # only the shoulder fire and cape are allowed to flutter.  Exclude a narrow
    # corridor around each down/outward sword before applying the energy mask.
    if sword_corridor_pixel(x, y):
        return False
    # The cape contains near-white and pale-yellow pixels in addition to cyan,
    # so color alone leaves its outer tips on the armor layer.  Move the safe
    # far-outside cape zones as geometry while preserving arms and sword lanes.
    cape_edge = 30 + max(0, y - 70) * 0.18
    if y >= 60:
        # Pull the pale detached lower cape tips out of the armor layer too.
        # Keep the threshold inside SAM's hands/forearms (roughly x=40..88).
        cape_edge = max(cape_edge, 38 + (y - 60) * 0.08)
    if y >= 45 and (x < cape_edge or x > CELL - cape_edge):
        return True
    chroma = max(red, green, blue) - min(red, green, blue)
    return green >= red + 5 and (blue >= red - 8 or green >= blue) and chroma >= 12


def split_sam_energy(master: Image.Image) -> tuple[Image.Image, Image.Image]:
    base = master.convert("RGBA").copy()
    energy = Image.new("RGBA", master.size, (0, 0, 0, 0))
    bp = base.load()
    ep = energy.load()
    for y in range(master.height):
        for x in range(master.width):
            red, green, blue, alpha = bp[x, y]
            if alpha and energy_pixel(red, green, blue, x, y):
                ep[x, y] = bp[x, y]
                bp[x, y] = (0, 0, 0, 0)
    # Color/geometry separation can leave a handful of detached pale cape
    # pixels.  Move tiny isolated components to the delayed energy layer so
    # the feet-to-head pass contains armor only, with no early cape specks.
    alpha = base.getchannel("A")
    ap = alpha.load()
    visited: set[tuple[int, int]] = set()
    for start_y in range(CELL):
        for start_x in range(CELL):
            if not ap[start_x, start_y] or (start_x, start_y) in visited:
                continue
            stack = [(start_x, start_y)]
            visited.add((start_x, start_y))
            component: list[tuple[int, int]] = []
            while stack:
                x, y = stack.pop()
                component.append((x, y))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if (
                            0 <= nx < CELL
                            and 0 <= ny < CELL
                            and ap[nx, ny]
                            and (nx, ny) not in visited
                        ):
                            visited.add((nx, ny))
                            stack.append((nx, ny))
            if len(component) < 20:
                for x, y in component:
                    ep[x, y] = bp[x, y]
                    bp[x, y] = (0, 0, 0, 0)
    return base, energy


def split_sam_swords(sam_static: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Separate both rigid blades so they never appear as floating tips.

    The armor assembles from Firefly's feet upward.  A plain horizontal wipe
    would expose the low sword tips long before SAM's hands exist.  Keeping the
    blade pixels on their own layer lets the swords extend from each completed
    hand toward the tip only after the armor build has finished.
    """
    armor = sam_static.copy()
    swords = Image.new("RGBA", sam_static.size, (0, 0, 0, 0))
    ap = armor.load()
    sp = swords.load()
    for y in range(58, CELL):
        for x in range(CELL):
            if sword_corridor_pixel(x, y):
                pixel = ap[x, y]
                if pixel[3]:
                    sp[x, y] = pixel
                    ap[x, y] = (0, 0, 0, 0)
    return armor, swords


def reveal_sam_swords(swords: Image.Image, progress: float) -> Image.Image:
    """Reveal rigid swords hilt-to-tip after the armor is complete."""
    local = max(0.0, min(1.0, progress))
    tip_y = round(57 + local * (CELL - 57))
    revealed = swords.copy()
    rp = revealed.load()
    for y in range(CELL):
        if y > tip_y:
            for x in range(CELL):
                rp[x, y] = (0, 0, 0, 0)
    return revealed


def flutter_energy(energy: Image.Image, phase: float) -> Image.Image:
    result = Image.new("RGBA", energy.size, (0, 0, 0, 0))
    for y in range(energy.height):
        # Keep the shoulder roots anchored while the long cape tails receive a
        # wider wave.  The phase is continuous, so a 32-frame loop closes
        # cleanly without a jump.
        amplitude = 0 if y < 24 else (1 if y < 52 else (2 if y < 78 else 4))
        offset = round(amplitude * math.sin(phase * math.tau + y * 0.12))
        row = energy.crop((0, y, energy.width, y + 1))
        result.alpha_composite(row, (offset, y))
    return result


def shoulder_jet(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    direction: int,
    tick: int,
    strength: int,
) -> None:
    """Animate a teal-green jet emitted outward from one SAM shoulder."""
    colors = ((58, 255, 207, 245), (63, 215, 224, 240), (180, 255, 128, 235))
    length = max(0, strength + (tick // 3) % 3)
    for index in range(length):
        wobble = ((tick + index * 5) % 5) - 2
        px = x + direction * (index * 2 + 2)
        py = y - index - wobble // 2
        color = colors[index % len(colors)]
        draw.point((px, py), fill=color)
        if index < strength - 1:
            draw.point((px, py + 1), fill=color)


def sam_hover_frame(
    sam_base: Image.Image,
    sam_energy: Image.Image,
    phase: float,
    tick: int,
) -> Image.Image:
    frame = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    frame.alpha_composite(sam_base)
    frame.alpha_composite(flutter_energy(sam_energy, phase))
    draw = ImageDraw.Draw(frame)
    pixel_flame(draw, 40, 27, tick, strength=4)
    pixel_flame(draw, 88, 28, tick + 5, strength=4)
    shoulder_jet(draw, 40, 28, -1, tick, strength=7)
    shoulder_jet(draw, 88, 28, 1, tick + 5, strength=7)
    if tick % 5 == 0:
        draw.point((35 + tick % 4, 21 - tick % 3), fill=(84, 240, 191, 200))
        draw.point((93 - tick % 4, 22 - (tick + 1) % 3), fill=(151, 255, 150, 190))
    return frame


def sam_landing_frame(
    sam_base: Image.Image,
    sam_energy: Image.Image,
    progress: float,
    tick: int,
) -> Image.Image:
    """Settle cape and shoulder jets while runtime translation lands SAM."""
    progress = max(0.0, min(1.0, progress))
    wind = 1.0 - progress
    frame = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    frame.alpha_composite(sam_base)
    frame.alpha_composite(flutter_energy(sam_energy, (tick / 32.0) * wind))
    draw = ImageDraw.Draw(frame)
    strength = max(1, round(7 - progress * 4))
    pixel_flame(draw, 40, 27, tick, strength=max(1, strength - 2))
    pixel_flame(draw, 88, 28, tick + 5, strength=max(1, strength - 2))
    shoulder_jet(draw, 40, 28, -1, tick, strength=strength)
    shoulder_jet(draw, 88, 28, 1, tick + 5, strength=strength)
    return frame


def assembly_frame(
    human: Image.Image,
    sam_armor: Image.Image,
    progress: float,
    tick: int,
) -> Image.Image:
    progress = max(0.0, min(1.0, progress))
    cutoff = round(124 - progress * 122)
    result = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    human_part = human.copy()
    sam_part = sam_armor.copy()
    hp = human_part.load()
    sp = sam_part.load()
    for y in range(CELL):
        for x in range(CELL):
            if y >= cutoff:
                hp[x, y] = (0, 0, 0, 0)
            else:
                sp[x, y] = (0, 0, 0, 0)
    result.alpha_composite(human_part)
    result.alpha_composite(sam_part)
    # Swords, cape, and shoulder fire are intentionally absent here.  They are
    # deployed only after this feet-to-head armor pass reaches 100%.
    draw = ImageDraw.Draw(result)
    for index in range(34):
        x = 8 + ((index * 13 + tick * 3) % 112)
        y = cutoff + ((index * 5 + tick) % 13) - 6
        if 0 <= y < CELL:
            color = (48, 238, 193, 230) if index % 2 else (166, 255, 133, 235)
            draw.point((x, y), fill=color)
            if index % 3 == 0 and y > 0:
                draw.point((x, y - 1), fill=color)
    # Three rising flame tongues make the bottom-up direction readable even
    # when the armor silhouette is wider than Firefly's human body.
    for offset, x in enumerate((30, 64, 98)):
        pixel_flame(draw, x, min(124, cutoff + 4), tick + offset * 4, strength=4)
    return result


def deploy_sam_energy(
    sam_armor: Image.Image,
    sam_swords: Image.Image,
    sam_energy: Image.Image,
    progress: float,
    tick: int,
) -> Image.Image:
    """Emit cape and shoulder fire only after the armor is fully assembled."""
    progress = max(0.0, min(1.0, progress))
    result = sam_armor.copy()
    result.alpha_composite(reveal_sam_swords(sam_swords, progress))
    revealed = Image.new("RGBA", sam_energy.size, (0, 0, 0, 0))
    source = flutter_energy(sam_energy, progress * 0.35)
    sp = source.load()
    rp = revealed.load()
    shoulders = ((40.0, 28.0), (88.0, 28.0))
    max_distance = 112.0
    for y in range(CELL):
        for x in range(CELL):
            if sp[x, y][3] == 0:
                continue
            distance = min(math.hypot(x - sx, y - sy) for sx, sy in shoulders)
            # A small deterministic dither keeps the emission edge fiery rather
            # than a perfectly circular wipe.
            jitter = ((x * 3 + y * 5 + tick) % 9) - 4
            if distance <= progress * max_distance + jitter:
                rp[x, y] = sp[x, y]
    result.alpha_composite(revealed)
    draw = ImageDraw.Draw(result)
    if progress > 0.0:
        pixel_flame(draw, 40, 28, tick, strength=max(1, round(2 + progress * 5)))
        pixel_flame(draw, 88, 28, tick + 5, strength=max(1, round(2 + progress * 5)))
    for index in range(round(progress * 12)):
        side = -1 if index % 2 == 0 else 1
        x = (40 if side < 0 else 88) + side * (3 + (index * 4) % 24)
        y = 28 + (index * 7 + tick) % 36
        draw.point((x, y), fill=(70, 239, 190, 215))
    return result


def retract_sam_cape(sam_energy: Image.Image, progress: float, tick: int) -> Image.Image:
    """Retract the cape tips back into both shoulders before jets shut off."""
    progress = max(0.0, min(1.0, progress))
    source = flutter_energy(sam_energy, tick / SAM_HOVER_LOGICAL_FRAMES)
    result = Image.new("RGBA", source.size, (0, 0, 0, 0))
    sp = source.load()
    rp = result.load()
    shoulders = ((40.0, 28.0), (88.0, 28.0))
    remaining_radius = (1.0 - eased(progress)) * 112.0
    for y in range(CELL):
        for x in range(CELL):
            if not sp[x, y][3]:
                continue
            distance = min(math.hypot(x - sx, y - sy) for sx, sy in shoulders)
            jitter = ((x * 5 + y * 3 + tick) % 7) - 3
            if distance <= remaining_radius + jitter:
                rp[x, y] = sp[x, y]
    return result


def sam_shutdown_accessory_frame(
    sam_armor: Image.Image,
    sam_swords: Image.Image,
    sam_energy: Image.Image,
    phase: str,
    progress: float,
    tick: int,
) -> Image.Image:
    """Switch off cape, shoulder fire, then swords in the required order."""
    progress = max(0.0, min(1.0, progress))
    frame = sam_armor.copy()
    if phase in ("sam-cape-retract", "sam-shoulder-fire-off"):
        frame.alpha_composite(sam_swords)
    elif phase == "sam-swords-retract":
        frame.alpha_composite(reveal_sam_swords(sam_swords, 1.0 - eased(progress)))

    draw = ImageDraw.Draw(frame)
    if phase == "sam-cape-retract":
        frame.alpha_composite(retract_sam_cape(sam_energy, progress, tick))
        draw = ImageDraw.Draw(frame)
        shoulder_jet(draw, 40, 28, -1, tick, strength=7)
        shoulder_jet(draw, 88, 28, 1, tick + 5, strength=7)
        pixel_flame(draw, 40, 27, tick, strength=4)
        pixel_flame(draw, 88, 28, tick + 5, strength=4)
    elif phase == "sam-shoulder-fire-off":
        strength = max(0, round(7 * (1.0 - eased(progress))))
        if strength:
            shoulder_jet(draw, 40, 28, -1, tick, strength=strength)
            shoulder_jet(draw, 88, 28, 1, tick + 5, strength=strength)
            pixel_flame(draw, 40, 27, tick, strength=max(1, strength // 2))
            pixel_flame(draw, 88, 28, tick + 5, strength=max(1, strength // 2))
    elif phase == "sam-swords-retract":
        # A small flame front moves from each tip toward its hilt while both
        # blades collapse. No cape or shoulder jet may reappear in this phase.
        local = 1.0 - eased(progress)
        tip_y = round(57 + local * (CELL - 57))
        for x in (round(46 - 0.55 * (tip_y - 58)), round(82 + 0.55 * (tip_y - 58))):
            pixel_flame(draw, x, tip_y, tick, strength=3)
    return frame


def disassemble_sam_head_to_feet(
    human: Image.Image,
    sam_armor: Image.Image,
    progress: float,
    tick: int,
) -> Image.Image:
    """Burn armor away from helmet to boots while Firefly reappears."""
    progress = max(0.0, min(1.0, progress))
    cutoff = round(eased(progress) * (CELL - 1))
    human_part = human.copy()
    armor_part = sam_armor.copy()
    hp = human_part.load()
    ap = armor_part.load()
    for y in range(CELL):
        for x in range(CELL):
            if y <= cutoff:
                ap[x, y] = (0, 0, 0, 0)
            else:
                hp[x, y] = (0, 0, 0, 0)
    result = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    result.alpha_composite(armor_part)
    result.alpha_composite(human_part)
    draw = ImageDraw.Draw(result)
    for index in range(38):
        x = 10 + ((index * 17 + tick * 5) % 108)
        y = cutoff + ((index * 7 + tick * 2) % 13) - 6
        if 0 <= y < CELL:
            color = (50, 240, 198, 235) if index % 2 else (174, 255, 131, 235)
            draw.point((x, y), fill=color)
            if index % 4 == 0 and y > 0:
                draw.point((x, y - 1), fill=color)
    for offset, x in enumerate((32, 64, 96)):
        pixel_flame(draw, x, min(CELL - 1, cutoff + 5), tick + offset, strength=4)
    return result


def sam_timeline_frame(
    poses: list[Image.Image],
    sam_base: Image.Image,
    sam_armor: Image.Image,
    sam_swords: Image.Image,
    sam_energy: Image.Image,
    seconds: float,
    hover_seconds: float,
    fps_tick: int,
) -> tuple[Image.Image, str, float]:
    if seconds < SAM_ACTIVATION_SECONDS:
        local = seconds / SAM_ACTIVATION_SECONDS
        pose = poses[0] if local < 0.35 else poses[1]
        frame = pose.copy()
        draw = ImageDraw.Draw(frame)
        pixel_flame(draw, 83, 61, fps_tick, strength=round(2 + local * 5))
        return frame, "module-activation", local
    if seconds < SAM_ACTIVATION_SECONDS + SAM_ASSEMBLY_SECONDS:
        local = (seconds - SAM_ACTIVATION_SECONDS) / SAM_ASSEMBLY_SECONDS
        return assembly_frame(
            poses[1], sam_armor, local, fps_tick
        ), "armor-fire-build-feet-to-head", local
    if seconds < SAM_ACTIVATION_SECONDS + SAM_ASSEMBLY_SECONDS + SAM_DEPLOY_SECONDS:
        local = (
            seconds - SAM_ACTIVATION_SECONDS - SAM_ASSEMBLY_SECONDS
        ) / SAM_DEPLOY_SECONDS
        return deploy_sam_energy(
            sam_armor, sam_swords, sam_energy, local, fps_tick
        ), "swords-shoulder-cape-fire-deploy", local
    hover_start = SAM_ACTIVATION_SECONDS + SAM_ASSEMBLY_SECONDS + SAM_DEPLOY_SECONDS
    if seconds < hover_start + hover_seconds:
        local_seconds = seconds - hover_start
        phase = (local_seconds % 2.0) / 2.0
        return sam_hover_frame(sam_base, sam_energy, phase, fps_tick), "sam-hover", local_seconds
    landing_start = hover_start + hover_seconds
    if seconds < landing_start + SAM_LANDING_SECONDS:
        local = (seconds - landing_start) / SAM_LANDING_SECONDS
        return sam_landing_frame(sam_base, sam_energy, local, fps_tick), "sam-landing", local

    cape_start = landing_start + SAM_LANDING_SECONDS
    if seconds < cape_start + SAM_CAPE_OFF_SECONDS:
        local = (seconds - cape_start) / SAM_CAPE_OFF_SECONDS
        return sam_shutdown_accessory_frame(
            sam_armor, sam_swords, sam_energy, "sam-cape-retract", local, fps_tick
        ), "sam-cape-retract", local

    shoulder_start = cape_start + SAM_CAPE_OFF_SECONDS
    if seconds < shoulder_start + SAM_SHOULDER_FIRE_OFF_SECONDS:
        local = (seconds - shoulder_start) / SAM_SHOULDER_FIRE_OFF_SECONDS
        return sam_shutdown_accessory_frame(
            sam_armor, sam_swords, sam_energy, "sam-shoulder-fire-off", local, fps_tick
        ), "sam-shoulder-fire-off", local

    swords_start = shoulder_start + SAM_SHOULDER_FIRE_OFF_SECONDS
    if seconds < swords_start + SAM_SWORDS_OFF_SECONDS:
        local = (seconds - swords_start) / SAM_SWORDS_OFF_SECONDS
        return sam_shutdown_accessory_frame(
            sam_armor, sam_swords, sam_energy, "sam-swords-retract", local, fps_tick
        ), "sam-swords-retract", local

    armor_start = swords_start + SAM_SWORDS_OFF_SECONDS
    if seconds < armor_start + SAM_ARMOR_OFF_SECONDS:
        local = (seconds - armor_start) / SAM_ARMOR_OFF_SECONDS
        return disassemble_sam_head_to_feet(
            poses[0], sam_armor, local, fps_tick
        ), "sam-armor-burn-head-to-feet", local

    return poses[0].copy(), "firefly-restored", 1.0


def save_directional_frames(frames: list[Image.Image], root: Path, prefix: str) -> None:
    right = root / "right" / "frames"
    left = root / "left" / "frames"
    for directory in (right, left):
        if directory.exists():
            shutil.rmtree(directory)
    right.mkdir(parents=True, exist_ok=True)
    left.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        frame.save(right / f"{prefix}-{index:03d}.png", optimize=True)
        frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(
            left / f"{prefix}-{index:03d}.png", optimize=True
        )


def contact_sheet(frames: list[Image.Image], indices: list[int], output: Path, columns: int = 4) -> None:
    scale = 3
    tile_width = frames[0].width * scale
    tile_height = frames[0].height * scale
    rows = math.ceil(len(indices) / columns)
    sheet = Image.new(
        "RGB", (tile_width * columns, (tile_height + 24) * rows), (20, 32, 48)
    )
    draw = ImageDraw.Draw(sheet)
    for slot, index in enumerate(indices):
        frame = frames[index].resize((tile_width, tile_height), Image.Resampling.NEAREST)
        x = (slot % columns) * tile_width
        y = (slot // columns) * (tile_height + 24)
        sheet.paste(frame, (x, y), frame)
        draw.text((x + 5, y + tile_height + 4), f"frame {index + 1}", fill=(255, 225, 96))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, optimize=True)


def logical_video_provider(
    frames: list[Image.Image],
    phases: list[str],
    durations_ms: list[int],
) -> Callable[[float, int], tuple[Image.Image, str]]:
    cumulative = [0]
    for duration in durations_ms:
        cumulative.append(cumulative[-1] + duration)

    def provider(seconds: float, _tick: int) -> tuple[Image.Image, str]:
        current_ms = min(cumulative[-1] - 1, max(0, round(seconds * 1000)))
        index = 0
        while index + 1 < len(cumulative) and current_ms >= cumulative[index + 1]:
            index += 1
        # Pixel art stays crisp: the 60 FPS container repeats each authored
        # 15 FPS drawing instead of alpha-blending it into the next pose.
        return frames[min(index, len(frames) - 1)], phases[min(index, len(phases) - 1)]

    return provider


def render_video(
    output: Path,
    duration: float,
    provider: Callable[[float, int], tuple[Image.Image, str]],
    placement_provider: Callable[[float, str], tuple[int, int]] | None = None,
    fps: int = 60,
) -> dict[str, object]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")
    width, height, taskbar_height = 960, 360, 48
    background = desktop_background(width, height, taskbar_height)
    sprite_scale = 2
    base_x = 352
    base_y = height - taskbar_height - CELL * sprite_scale
    frame_count = round(duration * fps)
    output.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [
            ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    last_phase = ""
    for index in range(frame_count):
        seconds = index / fps
        sprite, phase = provider(seconds, index)
        last_phase = phase
        sprite = sprite.resize(
            (sprite.width * sprite_scale, sprite.height * sprite_scale),
            Image.Resampling.NEAREST,
        )
        canvas = background.copy()
        # Sub-sprite-pixel placement at render FPS makes hovering smooth even
        # though the game art itself remains crisp nearest-neighbour pixels.
        hover_px = round(2.0 * math.sin(seconds * math.tau / 2.4)) if "hover" in phase else 0
        extra_x, extra_y = placement_provider(seconds, phase) if placement_provider else (0, 0)
        canvas.paste(sprite, (base_x + extra_x, base_y + hover_px + extra_y), sprite)
        draw = ImageDraw.Draw(canvas)
        draw.text((18, 18), f"Firefly | {phase}", fill=(221, 241, 255))
        draw.text((18, 36), f"60 FPS render | {seconds:05.1f}s", fill=(137, 190, 214))
        process.stdin.write(canvas.tobytes())
    process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    code = process.wait()
    if code:
        raise RuntimeError(f"ffmpeg failed ({code}):\n{stderr[-4000:]}")
    return {
        "path": str(output),
        "fps": fps,
        "duration_seconds": duration,
        "frame_count": frame_count,
        "resolution": [width, height],
        "last_phase": last_phase,
    }


def ffprobe(path: Path) -> dict[str, object]:
    raw = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames:format=duration",
            "-of", "json", str(path),
        ], text=True,
    )
    data = json.loads(raw)
    stream = data["streams"][0]
    return {
        "width": stream["width"],
        "height": stream["height"],
        "r_frame_rate": stream["r_frame_rate"],
        "nb_read_frames": int(stream["nb_read_frames"]),
        "duration": float(data["format"]["duration"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("keypose_source", type=Path)
    parser.add_argument("sam_master", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    root = args.output_dir
    keypose_dir = root / "human-module-sword" / "keyposes"
    poses = load_keyposes(args.keypose_source, keypose_dir)
    sam_master = stable_cleanup(Image.open(args.sam_master).convert("RGBA"))
    if sam_master.size != (CELL, CELL):
        raise SystemExit(f"SAM master must be 128x128, got {sam_master.size}")
    sam_layers = root / "sam-transform-hover" / "layers"
    sam_layers.mkdir(parents=True, exist_ok=True)
    sam_master.save(sam_layers / "sam-dual-swords-approved-master.png", optimize=True)
    sam_base, sam_energy = split_sam_energy(sam_master)
    sam_armor, sam_swords = split_sam_swords(sam_base)
    sam_base.save(sam_layers / "sam-armor-and-swords-static.png", optimize=True)
    sam_armor.save(sam_layers / "sam-armor-static.png", optimize=True)
    sam_swords.save(sam_layers / "sam-dual-swords-rigid.png", optimize=True)
    sam_energy.save(sam_layers / "sam-shoulder-flames-and-cape.png", optimize=True)

    human_frames, human_phases, human_frame_durations_ms = build_human_logical_frames(poses)
    human_root = root / "human-module-sword"
    save_directional_frames(human_frames, human_root, "frame")
    contact_sheet(
        human_frames,
        [round(index * (len(human_frames) - 1) / 15) for index in range(16)],
        human_root / "review" / "human-sequence-contact-sheet.png",
    )

    sam_hover_frames = [
        sam_hover_frame(sam_base, sam_energy, index / SAM_HOVER_LOGICAL_FRAMES, index)
        for index in range(SAM_HOVER_LOGICAL_FRAMES)
    ]
    sam_root = root / "sam-transform-hover"
    save_directional_frames(sam_hover_frames, sam_root / "hover-loop", "frame")
    contact_sheet(
        sam_hover_frames,
        [0, 4, 8, 12, 16, 20, 24, 28],
        sam_root / "review" / "sam-hover-contact-sheet.png",
    )

    enter_frames = []
    transform_duration = SAM_ACTIVATION_SECONDS + SAM_ASSEMBLY_SECONDS + SAM_DEPLOY_SECONDS
    for index in range(32):
        seconds = transform_duration * ((index + 0.5) / 32)
        frame, _, _ = sam_timeline_frame(
            poses, sam_base, sam_armor, sam_swords, sam_energy, seconds, 0.0, index
        )
        enter_frames.append(frame)
    save_directional_frames(enter_frames, sam_root / "transform-enter", "frame")
    contact_sheet(
        enter_frames,
        [0, 3, 7, 11, 15, 19, 23, 27, 31],
        sam_root / "review" / "sam-transform-contact-sheet.png",
    )

    landing_frames = [
        sam_landing_frame(sam_base, sam_energy, (index + 0.5) / 32, index)
        for index in range(32)
    ]
    save_directional_frames(landing_frames, sam_root / "landing", "frame")
    contact_sheet(
        landing_frames,
        [0, 4, 8, 12, 16, 20, 24, 28, 31],
        sam_root / "review" / "sam-landing-contact-sheet.png",
    )

    shutdown_duration = (
        SAM_CAPE_OFF_SECONDS
        + SAM_SHOULDER_FIRE_OFF_SECONDS
        + SAM_SWORDS_OFF_SECONDS
        + SAM_ARMOR_OFF_SECONDS
        + SAM_RESTORED_HOLD_SECONDS
    )
    shutdown_count = round(shutdown_duration * HUMAN_LOGICAL_FPS)
    shutdown_frames: list[Image.Image] = []
    shutdown_phase_names: list[str] = []
    shutdown_start = (
        SAM_ACTIVATION_SECONDS
        + SAM_ASSEMBLY_SECONDS
        + SAM_DEPLOY_SECONDS
        + SAM_LANDING_SECONDS
    )
    for index in range(shutdown_count):
        seconds = shutdown_start + shutdown_duration * ((index + 0.5) / shutdown_count)
        frame, phase, _ = sam_timeline_frame(
            poses, sam_base, sam_armor, sam_swords, sam_energy, seconds, 0.0, index
        )
        shutdown_frames.append(frame)
        shutdown_phase_names.append(phase)
    save_directional_frames(shutdown_frames, sam_root / "transform-exit", "frame")
    contact_sheet(
        shutdown_frames,
        [round(index * (len(shutdown_frames) - 1) / 15) for index in range(16)],
        sam_root / "review" / "sam-shutdown-contact-sheet.png",
    )

    human_video = render_video(
        human_root / "video" / "firefly-module-sword-idle-review-60fps.mp4",
        HUMAN_DURATION,
        logical_video_provider(human_frames, human_phases, human_frame_durations_ms),
    )

    def sam_provider(hover_seconds: float) -> Callable[[float, int], tuple[Image.Image, str]]:
        def provider(seconds: float, tick: int) -> tuple[Image.Image, str]:
            frame, phase, _ = sam_timeline_frame(
                poses,
                sam_base,
                sam_armor,
                sam_swords,
                sam_energy,
                seconds,
                hover_seconds,
                tick,
            )
            return frame, phase
        return provider

    def sam_placement(hover_seconds: float) -> Callable[[float, str], tuple[int, int]]:
        landing_start = (
            SAM_ACTIVATION_SECONDS
            + SAM_ASSEMBLY_SECONDS
            + SAM_DEPLOY_SECONDS
            + hover_seconds
        )
        armor_off_start = (
            landing_start
            + SAM_LANDING_SECONDS
            + SAM_CAPE_OFF_SECONDS
            + SAM_SHOULDER_FIRE_OFF_SECONDS
            + SAM_SWORDS_OFF_SECONDS
        )

        def placement(seconds: float, phase: str) -> tuple[int, int]:
            if phase == "sam-landing":
                local = max(0.0, min(1.0, (seconds - landing_start) / SAM_LANDING_SECONDS))
                # 56 screen pixels equals 28 logical sprite pixels: SAM's feet
                # descend from the hover pose to the taskbar.
                return (0, round(56 * eased(local)))
            if phase in ("sam-cape-retract", "sam-shoulder-fire-off", "sam-swords-retract"):
                return (0, 56)
            if phase == "sam-armor-burn-head-to-feet":
                local = max(0.0, min(1.0, (seconds - armor_off_start) / SAM_ARMOR_OFF_SECONDS))
                # SAM and human Firefly use different foot baselines. Lift the
                # composite gradually so restored Firefly stands on, rather
                # than sinks behind, the taskbar.
                return (0, 56 - round(40 * eased(local)))
            if phase == "firefly-restored":
                return (0, 16)
            return (0, 0)

        return placement

    short_hover = 6.0
    shutdown_duration = (
        SAM_CAPE_OFF_SECONDS
        + SAM_SHOULDER_FIRE_OFF_SECONDS
        + SAM_SWORDS_OFF_SECONDS
        + SAM_ARMOR_OFF_SECONDS
        + SAM_RESTORED_HOLD_SECONDS
    )
    short_duration = (
        SAM_ACTIVATION_SECONDS
        + SAM_ASSEMBLY_SECONDS
        + SAM_DEPLOY_SECONDS
        + short_hover
        + SAM_LANDING_SECONDS
        + shutdown_duration
    )
    full_hover = 60.0
    full_duration = (
        SAM_ACTIVATION_SECONDS
        + SAM_ASSEMBLY_SECONDS
        + SAM_DEPLOY_SECONDS
        + full_hover
        + SAM_LANDING_SECONDS
        + shutdown_duration
    )
    sam_short_video = render_video(
        sam_root / "video" / "firefly-sam-transform-short-review-60fps.mp4",
        short_duration,
        sam_provider(short_hover),
        sam_placement(short_hover),
    )
    sam_full_video = render_video(
        sam_root / "video" / "firefly-sam-transform-hover-60s-60fps.mp4",
        full_duration,
        sam_provider(full_hover),
        sam_placement(full_hover),
    )

    mirror_failures: list[str] = []
    for section, count, prefix in (
        (human_root, len(human_frames), "frame"),
        (sam_root / "hover-loop", len(sam_hover_frames), "frame"),
        (sam_root / "transform-enter", len(enter_frames), "frame"),
        (sam_root / "landing", len(landing_frames), "frame"),
        (sam_root / "transform-exit", len(shutdown_frames), "frame"),
    ):
        for index in range(count):
            right = Image.open(section / "right" / "frames" / f"{prefix}-{index:03d}.png").convert("RGBA")
            left = Image.open(section / "left" / "frames" / f"{prefix}-{index:03d}.png").convert("RGBA")
            if left.tobytes() != right.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes():
                mirror_failures.append(f"{section}:{index}")

    video_probe = {
        "human": ffprobe(Path(human_video["path"])),
        "sam_short": ffprobe(Path(sam_short_video["path"])),
        "sam_60s": ffprobe(Path(sam_full_video["path"])),
    }
    transparent_corner_failures = []
    for label, frames in (
        ("human", human_frames),
        ("sam", sam_hover_frames),
        ("enter", enter_frames),
        ("landing", landing_frames),
        ("shutdown", shutdown_frames),
    ):
        for index, frame in enumerate(frames):
            right = frame.width - 1
            bottom = frame.height - 1
            if not all(
                frame.getpixel(point)[3] == 0
                for point in ((0, 0), (right, 0), (0, bottom), (right, bottom))
            ):
                transparent_corner_failures.append(f"{label}:{index}")

    status = "PASS"
    if mirror_failures or transparent_corner_failures or any(
        item["r_frame_rate"] != "60/1" for item in video_probe.values()
    ):
        status = "FAIL"
    manifest = {
        "status": status,
        "character": "firefly",
        "directions": {
            "right": "authored master",
            "left": "exact horizontal mirror of right",
        },
        "human_module_sword_idle": {
            "duration_seconds": HUMAN_DURATION,
            "canvas_size": [HUMAN_CANVAS_WIDTH, HUMAN_CANVAS_HEIGHT],
            "directional_anchors": {
                "right": list(HUMAN_ANCHOR_RIGHT),
                "left": list(HUMAN_ANCHOR_LEFT),
            },
            "overscan_policy": "visual canvas is wider than collision box so slash effects are never clipped",
            "logical_frame_policy": "dense crisp authored frames; no crossfade between distant poses",
            "logical_frame_count": len(human_frames),
            "logical_fps": HUMAN_LOGICAL_FPS,
            "frame_durations_ms": human_frame_durations_ms,
            "render_fps": 60,
            "phases": [
                {"name": name, "start": start, "end": end, "keypose": pose + 1}
                for name, start, end, pose in HUMAN_PHASES
            ],
            "requirements": {
                "module_burns_before_sword": True,
                "half_sword_before_full_sword": True,
                "one_forward_slash": True,
                "return_to_guard_before_mote": True,
                "mote_moves_far_to_near": True,
                "inspection_pause_before_mote_fade": True,
                "mote_fully_gone_before_retraction": True,
                "retraction_direction": "tip-to-hilt",
                "mote_shape": "abstract green light dot, no insect silhouette",
            },
            "video": human_video,
        },
        "sam_transform_hover": {
            "activation_seconds": 1.2,
            "assembly_seconds": 2.4,
            "assembly_direction": "feet-to-head",
            "assembly_vfx": "teal-green flame rises with armor",
            "shoulder_cape_fire_deploy_seconds": 0.9,
            "cape_deploy_order": "only after full armor, emitted from both shoulders",
            "hover_state_seconds": 60.0,
            "hover_loop": {
                "logical_frames": SAM_HOVER_LOGICAL_FRAMES,
                "logical_fps": SAM_HOVER_LOGICAL_FPS,
                "loop_seconds": SAM_HOVER_LOGICAL_FRAMES / SAM_HOVER_LOGICAL_FPS,
                "repeat_count_for_60s": 30,
            },
            "transform_enter_frames": 32,
            "cape_animation": "32-frame closed flutter loop with anchored shoulder roots",
            "shoulder_fire_animation": "animated outward teal-green jets from both shoulders",
            "landing_frames": 32,
            "landing_seconds": SAM_LANDING_SECONDS,
            "landing_motion": "runtime vertical translation of 28 logical pixels to taskbar top",
            "shutdown_order": [
                "cape retracts",
                "shoulder fire shuts off",
                "dual swords retract",
                "armor burns away from head to feet",
                "Firefly restored",
            ],
            "shutdown_timing_seconds": {
                "cape": SAM_CAPE_OFF_SECONDS,
                "shoulder_fire": SAM_SHOULDER_FIRE_OFF_SECONDS,
                "swords": SAM_SWORDS_OFF_SECONDS,
                "armor_head_to_feet": SAM_ARMOR_OFF_SECONDS,
                "restored_hold": SAM_RESTORED_HOLD_SECONDS,
            },
            "transform_exit_frames": len(shutdown_frames),
            "transform_exit_logical_fps": HUMAN_LOGICAL_FPS,
            "post_hover_action": "SAM lands, shuts accessories down in order, then burns head-to-feet back into Firefly",
            "dual_sword_master": str(args.sam_master),
            "short_video": sam_short_video,
            "full_60s_video": sam_full_video,
        },
        "qa": {
            "mirror_failures": mirror_failures,
            "transparent_corner_failures": transparent_corner_failures,
            "video_probe": video_probe,
        },
    }
    (root / "firefly-idle-animation-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    raise SystemExit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
