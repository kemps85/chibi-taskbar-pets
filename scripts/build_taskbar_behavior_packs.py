"""Build the deterministic v1 taskbar behavior packs for Miyabi and Firefly.

The pack is intentionally asset-only: it writes right-facing RGBA frames and
manifests that instruct the runtime to mirror those frames for the left side.
Approved chibi sprites are reused as the identity source; all small behavior
changes are nearest-neighbour/pixel transforms or restrained pixel cues.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from process_pixel_sprite_sheet import remove_edge_background


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (160, 144)
ANCHOR_RIGHT = (64, 120)
FEET_Y = 143
FPS_REVIEW = 30
SEED = 20260825

MIYABI_BODY = ROOT / "assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png"
MIYABI_IDLE_SHEET = ROOT / "assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/source/idle-signature-sheet-v3-no-rear-scabbard.png"
FIREFLY_BODY = ROOT / "assets/generated/pixel-chibi/production-v2/firefly/layered-v3-clean/layers/firefly-body-fixed.png"
FIREFLY_SMOOTH = ROOT / "assets/generated/pixel-chibi/production-v2/firefly/idle-sequences/production-v2-smooth/human-module-sword"
FIREFLY_SMOOTH_MANIFEST = ROOT / "assets/generated/pixel-chibi/production-v2/firefly/idle-sequences/production-v2-smooth/firefly-idle-animation-manifest.json"
RUNTIME_PACK_ROOT = ROOT / "assets/runtime/taskbar-pet/clip-packs"

MIYABI_REFS = [
    "tmp/miyabi-model-preview/front.png",
    "tmp/miyabi-model-preview/three_quarter.png",
    "assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/hip-rise-crescent-slash-v3/references/weapon-drawn-detail.png",
    "assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/hip-rise-crescent-slash-v3/references/weapon-overview.png",
    "assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png",
]
FIREFLY_REFS = [
    "assets/generated/pixel-chibi/production-v2/firefly/layered-v3-clean/layers/firefly-body-fixed.png",
    "assets/generated/pixel-chibi/production-v2/firefly/idle-sequences/production-v2-smooth/human-module-sword/right/frames",
]


def repo_path(path: Path) -> str:
    """Store portable repository-relative paths in generated metadata."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_image(image: Image.Image) -> str:
    return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    return image.getchannel("A").getbbox()


def align_frame_baseline(frame: Image.Image) -> Image.Image:
    """Translate an approved frame without scaling it to the shared anchor."""
    frame = frame.convert("RGBA")
    bounds = alpha_bbox(frame)
    if bounds is None:
        raise ValueError("Cannot align an empty frame")
    shift_y = FEET_Y - bounds[3]
    if shift_y == 0:
        return frame
    aligned = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    aligned.alpha_composite(frame, (0, shift_y))
    return aligned


def alpha_border_count(image: Image.Image) -> int:
    a = image.getchannel("A")
    values = [a.getpixel((x, 0)) for x in range(image.width)]
    values += [a.getpixel((0, y)) for y in range(image.height)]
    values += [a.getpixel((image.width - 1, y)) for y in range(image.height)]
    return sum(1 for value in values if value)


def fit_sprite(image: Image.Image, *, max_height: int = 124, max_width: int = 148) -> Image.Image:
    image = image.convert("RGBA")
    bounds = alpha_bbox(image)
    if bounds is None:
        raise ValueError("Cannot fit an empty sprite")
    image = image.crop(bounds)
    scale = min(max_height / image.height, max_width / image.width, 1.0)
    if scale != 1.0:
        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.NEAREST)
    return image


def place_sprite(sprite: Image.Image, *, dx: int = 0, dy: int = 0, max_height: int = 124, max_width: int = 148) -> tuple[Image.Image, tuple[int, int]]:
    sprite = fit_sprite(sprite, max_height=max_height, max_width=max_width)
    bounds = alpha_bbox(sprite)
    assert bounds is not None
    # Align the visual alpha center to the shared right-authored anchor.
    x = ANCHOR_RIGHT[0] - round((bounds[0] + bounds[2]) / 2) + dx
    # Keep all feet on the shared taskbar line.  The dy argument remains in
    # the pose API for future upper-body-only offsets, but must not move the
    # ground contact itself.
    y = FEET_Y - bounds[3]
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.alpha_composite(sprite, (x, y))
    return canvas, (x, y)


def body_pose(base: Image.Image, *, dx: int = 0, dy: int = 0, angle: float = 0.0) -> tuple[Image.Image, tuple[int, int]]:
    sprite = base.convert("RGBA")
    if angle:
        sprite = sprite.rotate(angle, resample=Image.Resampling.NEAREST, expand=False, center=(sprite.width // 2, sprite.height - 4))
    return place_sprite(sprite, dx=dx, dy=dy)


def walk_sprite(base: Image.Image, lower_dx: int) -> Image.Image:
    """Shift the lower-body silhouette to make alternating steps readable."""
    source = base.convert("RGBA")
    split_y = 84
    shifted = Image.new("RGBA", source.size, (0, 0, 0, 0))
    shifted.alpha_composite(source.crop((0, 0, source.width, split_y)), (0, 0))
    shifted.alpha_composite(source.crop((0, split_y, source.width, source.height)), (lower_dx, split_y))
    return shifted


def rest_sprite(base: Image.Image, character: str) -> Image.Image:
    """Remove the drawn weapon corridor before a safe sleep/eat pose."""
    sprite = base.convert("RGBA").copy()
    draw = ImageDraw.Draw(sprite)
    if character == "miyabi":
        # The mechanical saya occupies the viewer-left diagonal in the
        # approved standing sprite.  Leave the hand/cape core untouched.
        draw.polygon([(14, 124), (47, 124), (53, 77), (27, 76)], fill=(0, 0, 0, 0))
    else:
        # Firefly's slim cyan sword is removed and redrawn beside the nap.
        draw.polygon([(18, 129), (52, 129), (54, 84), (29, 82)], fill=(0, 0, 0, 0))
    return sprite


def draw_rest_weapon(canvas: Image.Image, character: str) -> None:
    """Draw a short, stowed weapon under the horizontal resting silhouette."""
    draw = ImageDraw.Draw(canvas)
    if character == "miyabi":
        draw.line((8, 137, 43, 137), fill=(18, 27, 39, 255), width=3)
        draw.line((10, 136, 41, 136), fill=(31, 160, 184, 220), width=1)
        draw.rectangle((39, 134, 46, 139), fill=(24, 31, 43, 255))
        draw.point((43, 135), fill=(107, 235, 239, 255))
    else:
        draw.line((8, 137, 44, 137), fill=(27, 49, 62, 255), width=2)
        draw.line((9, 136, 45, 136), fill=(94, 237, 220, 255), width=1)
        draw.point((43, 135), fill=(238, 255, 249, 255))


def rest_pose(base: Image.Image, character: str, *, angle: float, dx: int = 0, max_height: int = 124) -> tuple[Image.Image, tuple[int, int]]:
    """Place a rotated resting sprite while keeping its weapon beside it."""
    sprite = rest_sprite(base, character)
    if angle:
        sprite = sprite.rotate(angle, resample=Image.Resampling.NEAREST, expand=False, center=(sprite.width // 2, sprite.height - 4))
    sprite = fit_sprite(sprite, max_height=max_height, max_width=148)
    bounds = alpha_bbox(sprite)
    assert bounds is not None
    x = ANCHOR_RIGHT[0] - round((bounds[0] + bounds[2]) / 2) + dx
    y = FEET_Y - bounds[3]
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw_rest_weapon(canvas, character)
    canvas.alpha_composite(sprite, (x, y))
    return canvas, (x, y)


def seated_pose(base: Image.Image, character: str, *, angle: float = 0.0, dx: int = 0) -> tuple[Image.Image, tuple[int, int]]:
    """Build a compact seated silhouette with visibly folded lower legs."""
    sprite = rest_sprite(base, character)
    # Remove only the standing shin/foot tail; the skirt/uniform hem remains.
    ImageDraw.Draw(sprite).rectangle((0, 114, sprite.width - 1, sprite.height - 1), fill=(0, 0, 0, 0))
    if angle:
        sprite = sprite.rotate(angle, resample=Image.Resampling.NEAREST, expand=False, center=(sprite.width // 2, sprite.height - 4))
    sprite = fit_sprite(sprite, max_height=116, max_width=148)
    bounds = alpha_bbox(sprite)
    assert bounds is not None
    x = ANCHOR_RIGHT[0] - round((bounds[0] + bounds[2]) / 2) + dx
    y = FEET_Y - bounds[3]
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw_rest_weapon(canvas, character)
    canvas.alpha_composite(sprite, (x, y))
    draw = ImageDraw.Draw(canvas)
    if character == "miyabi":
        leg = (24, 29, 39, 245)
        draw.line((45, 126, 61, 126), fill=leg, width=3)
        draw.line((61, 126, 69, 136), fill=leg, width=3)
        draw.line((74, 126, 89, 126), fill=leg, width=3)
    else:
        leg = (226, 240, 235, 245)
        draw.line((47, 126, 63, 126), fill=leg, width=3)
        draw.line((63, 126, 71, 136), fill=leg, width=3)
        draw.line((76, 126, 91, 126), fill=leg, width=3)
    return canvas, (x, y)


def draw_pixel_z(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple[int, int, int, int], scale: int = 1) -> None:
    """Crisp, hand-pixelled Z glyph; no font rasterization or matte."""
    draw.line((x, y, x + 4 * scale, y), fill=color, width=scale)
    draw.line((x + 4 * scale, y, x, y + 5 * scale), fill=color, width=scale)
    draw.line((x, y + 5 * scale, x + 4 * scale, y + 5 * scale), fill=color, width=scale)


def draw_walk_cue(canvas: Image.Image, character: str, index: int) -> Image.Image:
    """Add alternating foot/arm accents on top of the shifted lower body."""
    result = canvas.copy()
    draw = ImageDraw.Draw(result)
    sign = 1 if index % 2 == 0 else -1
    stride = (index % 4) - 1
    if character == "miyabi":
        dark = (21, 24, 32, 230)
        teal = (31, 154, 171, 220)
        draw.line((49 + sign * 3 + stride, 129, 45 + sign * 5 + stride, 135), fill=dark, width=2)
        draw.line((78 - sign * 3 - stride, 129, 82 - sign * 5 - stride, 135), fill=dark, width=2)
        draw.point((35 - sign * 2, 82), fill=teal)
        draw.point((34 - sign * 2, 84), fill=teal)
        draw.point((91 + sign * 2, 82), fill=teal)
    else:
        pale = (225, 239, 234, 235)
        cyan = (86, 220, 210, 220)
        draw.line((54 + sign * 4 + stride, 127, 50 + sign * 7 + stride, 138), fill=pale, width=2)
        draw.line((79 - sign * 4 - stride, 127, 84 - sign * 7 - stride, 138), fill=pale, width=2)
        draw.point((42 - sign * 2, 82), fill=cyan)
        draw.point((94 + sign * 2, 82), fill=cyan)
    return result


def draw_sleepy_cue(canvas: Image.Image, character: str, index: int) -> Image.Image:
    """Make the pre-sleep gesture legible: eye rub, yawn, and a small Z."""
    result = canvas.copy()
    draw = ImageDraw.Draw(result)
    face_x, face_y = (61, 65) if character == "miyabi" else (63, 66)
    hand = (32, 39, 48, 235) if character == "miyabi" else (143, 208, 195, 235)
    mouth = (40, 28, 40, 235) if character == "miyabi" else (54, 75, 77, 235)
    # A two-pixel hand rises toward the near eye, then drops on the exhale.
    lift = min(index, 7 - index)
    draw.line((face_x - 12, 84 - lift, face_x - 8, 75 - lift), fill=hand, width=2)
    draw.point((face_x - 7, 73 - lift), fill=hand)
    # Open mouth/yawn grows for the middle frames.
    if 2 <= index <= 5:
        draw.rectangle((face_x - 2, face_y + 8, face_x + 2, face_y + 10), fill=mouth)
        draw.point((face_x, face_y + 11), fill=(242, 220, 215, 210))
    if index >= 3:
        draw_pixel_z(draw, 101 + min(index - 3, 2) * 2, 39 - min(index - 3, 2) * 2, (155, 215, 229, 210), 1)
    return result


def horizontal_face_anchor(frame: Image.Image, character: str) -> tuple[int, int]:
    bounds = alpha_bbox(frame)
    if bounds is None:
        return (100, 112)
    # All rest poses use -90deg: the head is the right-hand, lower mass.
    return (min(bounds[2] - 18, 120), min(FEET_Y - 20, bounds[3] - 25))


def draw_sleep_cue(canvas: Image.Image, character: str, index: int, *, z: bool = False) -> Image.Image:
    result = canvas.copy()
    draw = ImageDraw.Draw(result)
    face_x, face_y = horizontal_face_anchor(result, character)
    eye = (42, 32, 42, 240) if character == "miyabi" else (53, 68, 72, 235)
    curl = (31, 37, 48, 225) if character == "miyabi" else (213, 230, 225, 225)
    draw.line((face_x - 7, face_y, face_x - 3, face_y + 1), fill=eye, width=1)
    draw.line((face_x + 1, face_y, face_x + 5, face_y + 1), fill=eye, width=1)
    # A bent knee/boot at the lower edge makes the horizontal silhouette read
    # as a curled side nap rather than a rotated standing pose.
    draw.line((42, 132, 50, 125), fill=curl, width=2)
    draw.line((49, 133, 59, 133), fill=curl, width=2)
    if index % 4 == 1:
        draw.point((face_x - 9, face_y + 6), fill=(163, 212, 220, 130))
    if z:
        draw_pixel_z(draw, max(106, face_x + 5), max(38, face_y - 37), (146, 220, 232, 205), 1)
        if index % 6 == 0:
            draw_pixel_z(draw, max(99, face_x - 2), max(31, face_y - 48), (137, 206, 224, 150), 1)
    return result


def draw_hunger_cue(canvas: Image.Image, character: str, index: int) -> Image.Image:
    """A contained stomach hold plus an unmistakably empty plate."""
    result = canvas.copy()
    draw = ImageDraw.Draw(result)
    if character == "miyabi":
        hand = (25, 31, 42, 245)
        plate = (208, 220, 214, 235)
        accent = (39, 170, 185, 220)
    else:
        hand = (128, 186, 175, 245)
        plate = (218, 239, 231, 235)
        accent = (93, 234, 210, 220)
    sway = -1 if index in (1, 2, 5, 6) else 1
    draw.line((56 + sway, 87, 62 + sway, 94), fill=hand, width=2)
    draw.line((72 + sway, 87, 66 + sway, 94), fill=hand, width=2)
    # Empty plate/bowl at the interaction edge, with three empty crumbs above.
    draw.line((112, 112, 127, 112), fill=plate, width=2)
    draw.line((114, 113, 116, 117), fill=plate, width=1)
    draw.line((125, 113, 123, 117), fill=plate, width=1)
    draw.line((116, 117, 123, 117), fill=plate, width=1)
    draw.point((117, 106), fill=accent)
    draw.point((121, 103), fill=accent)
    draw.point((125, 108), fill=accent)
    if index % 2 == 0:
        draw.point((119, 111), fill=(0, 0, 0, 0))
    return result


def draw_eat_cue(canvas: Image.Image, character: str, index: int, seated: bool) -> Image.Image:
    result = canvas.copy()
    draw = ImageDraw.Draw(result)
    face_x, face_y = (61, 65) if character == "miyabi" else (63, 66)
    hand = (25, 31, 42, 245) if character == "miyabi" else (126, 192, 180, 240)
    food = (239, 197, 87, 250) if character == "miyabi" else (167, 246, 194, 250)
    # Hands lift a bite from the plate toward the mouth, then return.
    phase = index if index <= 5 else 11 - index
    lift = round(phase * 2.2)
    draw.line((72, 95, face_x + 8, 87 - lift), fill=hand, width=2)
    draw.point((face_x + 10, 86 - lift), fill=food)
    draw.point((face_x + 11, 86 - lift), fill=food)
    draw.line((112, 113, 127, 113), fill=(206, 224, 216, 220), width=2)
    draw.line((115, 114, 117, 117), fill=(206, 224, 216, 220), width=1)
    draw.line((124, 114, 122, 117), fill=(206, 224, 216, 220), width=1)
    if 3 <= index <= 8:
        draw.point((face_x - 2, face_y + 8), fill=(242, 223, 215, 220))
    if seated:
        if character == "miyabi":
            draw.line((47, 130, 57, 134), fill=(23, 28, 38, 230), width=2)
            draw.line((75, 134, 85, 130), fill=(23, 28, 38, 230), width=2)
        else:
            draw.line((50, 130, 61, 134), fill=(225, 239, 234, 230), width=2)
            draw.line((77, 134, 89, 130), fill=(225, 239, 234, 230), width=2)
    return result


def draw_behavior_cue(canvas: Image.Image, character: str, state: str, index: int, *, sleepy: float = 0.0, food: bool = False) -> Image.Image:
    """Add only tiny state cues; never draw a second character silhouette."""
    result = canvas.copy()
    draw = ImageDraw.Draw(result)
    if character == "miyabi":
        # Approved 128px body visual eye/hand coordinates after anchor placement.
        face_x, face_y = 61, 65
        eyelid = (22, 27, 34, round(220 * sleepy))
        accent = (208, 91, 66, 230)
        food_color = (231, 181, 69, 220)
    else:
        face_x, face_y = 63, 66
        eyelid = (65, 71, 76, round(190 * sleepy))
        accent = (119, 244, 183, 220)
        food_color = (154, 239, 187, 220)
    if sleepy > 0:
        alpha = eyelid[3]
        draw.line((face_x - 6, face_y, face_x - 1, face_y + round(1 + sleepy)), fill=(*eyelid[:3], alpha), width=1)
        draw.line((face_x + 2, face_y, face_x + 7, face_y + round(1 + sleepy)), fill=(*eyelid[:3], alpha), width=1)
    if state == "sleep_loop" and index % 6 == 0:
        draw.point((face_x + 13, face_y - 8), fill=(*accent[:3], 150))
        draw.point((face_x + 15, face_y - 10), fill=(*accent[:3], 110))
    if food:
        # A restrained two/three-pixel cue at the right-side food area.
        # Keep the cue inside the ordinary x<=128 safe edge; the 160px
        # overscan remains available to signature VFX rather than UI state.
        x = 123 + (index % 2)
        y = 105 - (index % 2)
        draw.rectangle((x, y, x + 2, y + 2), fill=food_color)
        if index % 3 == 1:
            draw.point((x - 2, y + 1), fill=(*food_color[:3], 150))
    return result


def make_stand(base: Image.Image, character: str) -> list[Image.Image]:
    phases = [(0, 0, 0.0), (0, -1, -0.4), (1, -1, -0.7), (1, 0, -0.3), (0, 1, 0.0), (-1, 1, 0.4), (-1, 0, 0.7), (0, 0, 0.4)]
    frames = []
    for dx, dy, angle in phases:
        frame, _ = body_pose(base, dx=dx, dy=dy, angle=angle)
        frames.append(frame)
    return frames


def make_walk(base: Image.Image, character: str) -> list[Image.Image]:
    phases = [(-2, 1.2), (-1, 0.7), (0, 0.2), (1, -0.6), (2, -1.2), (1, -0.7), (0, -0.2), (-1, 0.6)]
    frames = []
    for index, (dx, angle) in enumerate(phases):
        stepped = walk_sprite(base, 3 if index in (1, 2, 3) else -3 if index in (5, 6, 7) else 0)
        frame, _ = body_pose(stepped, dx=dx, angle=angle)
        frames.append(draw_walk_cue(frame, character, index))
    return frames


def make_sleepy_notice(base: Image.Image, character: str) -> list[Image.Image]:
    frames = []
    for i in range(8):
        frame, _ = body_pose(base, dx=0, angle=-0.8 * min(i, 7 - i))
        frame = draw_behavior_cue(frame, character, "sleepy_notice", i, sleepy=min(1.0, i / 4))
        frames.append(draw_sleepy_cue(frame, character, i))
    return frames


def make_sleep_enter(base: Image.Image, character: str) -> list[Image.Image]:
    frames = []
    resting = rest_sprite(base, character)
    for i in range(10):
        t = i / 9
        angle = -90.0 * (t ** 1.35)
        source = base if t < 0.48 else resting
        frame, _ = body_pose(source, dx=round(-3 * t), angle=angle)
        if t > 0.58:
            # Redraw the safe stowed weapon only once the silhouette is
            # horizontal; before that the authored weapon remains visible.
            frame, _ = rest_pose(base, character, angle=angle, dx=round(-3 * t))
            frame = draw_sleep_cue(frame, character, i, z=t > 0.8)
        else:
            frame = draw_behavior_cue(frame, character, "sleep_enter", i, sleepy=t)
        frames.append(frame)
    return frames


def make_sleep_loop(base: Image.Image, character: str) -> list[Image.Image]:
    frames = []
    resting = rest_sprite(base, character)
    breathing = [-89.0, -90.0, -91.0, -90.0, -89.0, -90.0, -91.0, -90.0, -89.0, -90.0, -91.0, -90.0]
    for i, angle in enumerate(breathing):
        frame, _ = rest_pose(resting, character, angle=angle)
        frames.append(draw_sleep_cue(frame, character, i, z=i in (1, 5, 9)))
    return frames


def make_wake(base: Image.Image, character: str) -> list[Image.Image]:
    frames = []
    resting = rest_sprite(base, character)
    for i in range(8):
        t = i / 7
        angle = -90.0 * (1.0 - t) ** 1.15
        if t < 0.52:
            frame, _ = rest_pose(resting, character, angle=angle, dx=round(-2 + 2 * t))
            frame = draw_sleep_cue(frame, character, i, z=False)
        else:
            frame, _ = body_pose(base, dx=round(-2 + 2 * t), angle=angle)
            frame = draw_behavior_cue(frame, character, "wake", i, sleepy=1.0 - t)
            if 3 <= i <= 6:
                draw = ImageDraw.Draw(frame)
                color = (120, 211, 218, 190) if character == "miyabi" else (146, 236, 213, 190)
                draw.line((48, 51, 44, 46), fill=color, width=1)
                draw.line((83, 47, 87, 42), fill=color, width=1)
        frames.append(frame)
    return frames


def make_hungry_notice(base: Image.Image, character: str) -> list[Image.Image]:
    frames = []
    for i in range(8):
        frame, _ = body_pose(base, dx=round(math.sin(i * math.pi / 4) * 1.2), angle=1.5 * math.sin(i * math.pi / 4))
        frame = draw_hunger_cue(frame, character, i)
        frames.append(frame)
    return frames


def make_eat(base: Image.Image, character: str) -> list[Image.Image]:
    frames = []
    for i in range(12):
        # Enter/exit standing bookends a compact seated hold.  During the
        # hold the weapon is removed from the hand and placed beside the pet.
        progress = min(i / 3.0, (11 - i) / 3.0, 1.0)
        progress = max(0.0, progress)
        angle = -8.0 * math.sin(i * math.pi / 11)
        if progress > 0.22:
            # Compact the seated silhouette and fold the lower legs; the
            # weapon is stowed beside the pet during this hold.
            frame, _ = seated_pose(base, character, angle=angle, dx=round(math.sin(i * math.pi / 6)))
            frame = draw_eat_cue(frame, character, i, seated=True)
        else:
            frame, _ = body_pose(base, dx=round(math.sin(i * math.pi / 6)), angle=angle)
            frame = draw_eat_cue(frame, character, i, seated=False)
        frames.append(frame)
    return frames


def extract_spirit_tail_frames(sheet_path: Path, count: int = 12) -> list[Image.Image]:
    source = Image.open(sheet_path).convert("RGBA")
    grid = [0, 313, 627, 940, 1254]
    frames: list[Image.Image] = []
    for index in range(count):
        row, col = divmod(index, 4)
        cell = source.crop((grid[col], grid[row], grid[col + 1], grid[row + 1]))
        clean = remove_edge_background(cell)
        frames.append(place_sprite(fit_sprite(clean, max_height=123, max_width=148))[0])
    return frames


def load_module_sword_frames() -> tuple[list[Image.Image], list[int]]:
    """Load the approved Firefly module-sword clip as real pack frames."""
    frame_dir = FIREFLY_SMOOTH / "right" / "frames"
    paths = sorted(frame_dir.glob("frame-*.png"))
    if not paths:
        raise FileNotFoundError(f"Approved Firefly module_sword frames missing: {frame_dir}")
    frames = [align_frame_baseline(Image.open(path).convert("RGBA")) for path in paths]
    source_manifest = json.loads(FIREFLY_SMOOTH_MANIFEST.read_text(encoding="utf-8"))
    durations = source_manifest.get("human_module_sword_idle", {}).get("frame_durations_ms")
    if not isinstance(durations, list) or len(durations) != len(frames):
        raise ValueError("Approved module_sword timing does not match its frame count")
    durations_int = [int(value) for value in durations]
    if any(value <= 0 for value in durations_int):
        raise ValueError("Approved module_sword timing contains a non-positive duration")
    return frames, durations_int


def write_clip(pack_dir: Path, name: str, frames: list[Image.Image], duration_ms: list[int], loop_mode: str, source: str, notes: str = "") -> dict[str, object]:
    frame_dir = pack_dir / "clips" / name / "right" / "frames"
    if frame_dir.exists():
        shutil.rmtree(frame_dir)
    frame_dir.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        frame.convert("RGBA").save(frame_dir / f"frame-{index:03d}.png", optimize=True)
    return {
        "frame_count": len(frames),
        "frame_durations_ms": duration_ms,
        "duration_seconds": round(sum(duration_ms) / 1000, 3),
        "loop_mode": loop_mode,
        "direction": "right-authored",
        "frames": repo_path(frame_dir),
        "source": source,
        "notes": notes,
    }


def create_contact_sheet(pack_dir: Path, clip_frames: dict[str, list[Image.Image]], references: dict[str, str]) -> Path:
    # Large insets are intentional: sleep/hunger poses must be reviewable at
    # a glance instead of hiding the action in thumbnail-sized 80px tiles.
    tile_w, tile_h = 480, 220
    columns = 2
    rows = math.ceil(len(clip_frames) / columns)
    sheet = Image.new("RGB", (tile_w * columns, tile_h * rows), (42, 55, 70))
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(sheet)
    for slot, (name, frames) in enumerate(clip_frames.items()):
        x, y = (slot % columns) * tile_w, (slot // columns) * tile_h
        draw.text((x + 6, y + 5), name, fill=(225, 242, 255), font=font)
        sample = frames if len(frames) <= 4 else [frames[round(i * (len(frames) - 1) / 3)] for i in range(4)]
        for sample_index, frame in enumerate(sample):
            preview = frame.resize((112, 101), Image.Resampling.NEAREST)
            px = x + 8 + sample_index * 116
            py = y + 30
            sheet.paste(preview, (px, py), preview)
    out = pack_dir / "review" / "behavior-pack-contact-sheet.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)
    return out


def render_review_video(pack_dir: Path, clip_frames: dict[str, list[Image.Image]]) -> dict[str, object]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for review videos")
    width, height = 960, 540
    out = pack_dir / "video" / "behavior-pack-review.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen([ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(FPS_REVIEW), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert process.stdin is not None
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    for name, frames in clip_frames.items():
        for frame in frames:
            screen = Image.new("RGB", (width, height), (7, 15, 28))
            draw = ImageDraw.Draw(screen)
            draw.text((28, 24), name, fill=(229, 244, 255), font=font)
            sprite = frame.resize((480, 432), Image.Resampling.NEAREST)
            screen.paste(sprite, ((width - sprite.width) // 2, 74), sprite)
            for _ in range(3):
                process.stdin.write(screen.tobytes())
    process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    if process.wait():
        raise RuntimeError(stderr[-4000:])
    total_frames = sum(len(frames) * 3 for frames in clip_frames.values())
    return {"path": repo_path(out), "fps": FPS_REVIEW, "frame_count": total_frames, "duration_seconds": round(total_frames / FPS_REVIEW, 3), "resolution": [width, height]}


def qa_pack(pack_dir: Path, manifest: dict[str, object], clip_frames: dict[str, list[Image.Image]]) -> dict[str, object]:
    failures: list[str] = []
    clip_qa: dict[str, object] = {}
    for name, frames in clip_frames.items():
        bboxes = [alpha_bbox(frame) for frame in frames]
        border_counts = [alpha_border_count(frame) for frame in frames]
        dimensions_ok = all(frame.size == CANVAS for frame in frames)
        alpha_ok = all(frame.mode == "RGBA" for frame in frames)
        # PIL alpha bboxes use an exclusive lower edge: a visual foot on the
        # last allowed row (y=143) therefore reports lower == 144.  The
        # generated sprites are aligned so their visual alpha lower edge is
        # exactly FEET_Y (the taskbar contact line), with no pixels beyond it.
        baseline_ok = all(bbox is not None and bbox[3] == FEET_Y for bbox in bboxes)
        if not dimensions_ok or not alpha_ok or not baseline_ok or any(border_counts):
            failures.append(name)
        union_bbox: tuple[int, int, int, int] | None = None
        for bbox in bboxes:
            if bbox is None:
                continue
            union_bbox = bbox if union_bbox is None else (min(union_bbox[0], bbox[0]), min(union_bbox[1], bbox[1]), max(union_bbox[2], bbox[2]), max(union_bbox[3], bbox[3]))
        clip_qa[name] = {
            "frame_count": len(frames),
            "dimensions_ok": dimensions_ok,
            "rgba_ok": alpha_ok,
            "feet_baseline_y": FEET_Y,
            "baseline_ok": baseline_ok,
            "max_border_alpha_pixels": max(border_counts),
            "alpha_bounds_union": list(union_bbox) if union_bbox else None,
        }
    qa = {"status": "PASS" if not failures else "FAIL", "failures": failures, "canvas": list(CANVAS), "anchor_right": list(ANCHOR_RIGHT), "feet_baseline_y": FEET_Y, "mirror_strategy": "render-mirror", "clips": clip_qa}
    (pack_dir / "qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
    return qa


def build_runtime_pack(character: str, generated_pack: Path, runtime_pack: Path, generated_manifest: dict[str, object]) -> dict[str, object]:
    """Admit a self-contained stable pack; never leave loose source paths."""
    if runtime_pack.exists():
        shutil.rmtree(runtime_pack)
    runtime_pack.mkdir(parents=True, exist_ok=True)
    generated_clips = generated_manifest["clips"]
    assert isinstance(generated_clips, dict)
    runtime_clips: dict[str, list[Image.Image]] = {}
    clip_manifest: dict[str, object] = {}
    for clip_name, clip_meta in generated_clips.items():
        if not isinstance(clip_meta, dict) or "frames" not in clip_meta:
            raise ValueError(f"Generated clip {clip_name} has no admitted frames")
        source_dir = generated_pack / "clips" / clip_name / "right" / "frames"
        destination_dir = runtime_pack / "clips" / clip_name / "right" / "frames"
        if not source_dir.is_dir():
            raise FileNotFoundError(f"Stable pack source frames missing: {source_dir}")
        shutil.copytree(source_dir, destination_dir)
        paths = sorted(destination_dir.glob("frame-*.png"))
        frames = [Image.open(path).convert("RGBA") for path in paths]
        runtime_clips[clip_name] = frames
        durations = [int(value) for value in clip_meta["frame_durations_ms"]]
        if clip_name == "spirit_tail":
            loop_policy = "segmented-enter-loop-exit"
        elif clip_meta["loop_mode"] == "loop":
            loop_policy = "loop"
        else:
            loop_policy = "once"
        clip_manifest[clip_name] = {
            "frames": (Path("clips") / clip_name / "right" / "frames").as_posix(),
            "frame_name_pattern": "frame-{index:000}.png",
            "frame_count": len(frames),
            "right_anchor": {"x": ANCHOR_RIGHT[0], "y": ANCHOR_RIGHT[1]},
            "frame_durations_ms": durations,
            "loop_policy": loop_policy,
        }
        if clip_name == "spirit_tail":
            # The admitted signature is authored as a readable appearance,
            # short hover, and retract sequence. Runtime may extend only the
            # middle range while keeping enter/exit atomic.
            clip_manifest[clip_name]["segments"] = {
                "enter": {"start": 0, "end": 7},
                "loop": {"start": 8, "end": 11},
                "exit": {"start": 12, "end": 15},
            }
    stable_manifest: dict[str, object] = {
        "status": "draft",
        "schema_version": 1,
        "pack_id": f"{character}-v1",
        "character_id": character,
        "canvas": {"width": CANVAS[0], "height": CANVAS[1]},
        "master_direction": "right",
        "left_rendering": {"strategy": "mirror-right-at-runtime", "anchor_formula": "canvas.width-right_anchor.x"},
        "clip_policy": "right-authored frames only; no stored left frames",
        "required_clips": ["idle", "walk", "hunger_cue", "eat", "sleep_cue", "sleep_enter", "sleep_loop", "wake", "spirit_tail" if character == "miyabi" else "module_sword"],
        "clips": clip_manifest,
        "signature": {"clip": "spirit_tail" if character == "miyabi" else "module_sword", "atomic": True},
    }
    qa = qa_pack(runtime_pack, stable_manifest, runtime_clips)
    stable_manifest["status"] = qa["status"]
    stable_manifest["qa"] = repo_path(runtime_pack / "qa.json")
    (runtime_pack / "manifest.json").write_text(json.dumps(stable_manifest, indent=2), encoding="utf-8")
    return stable_manifest


def build_character(character: str, pack_dir: Path, runtime_pack: Path) -> dict[str, object]:
    pack_dir.mkdir(parents=True, exist_ok=True)
    if character == "miyabi":
        base_path = MIYABI_BODY
        source_refs = MIYABI_REFS
        base = Image.open(base_path).convert("RGBA")
        display_name = "Hoshimi Miyabi"
        spirit_source = extract_spirit_tail_frames(MIYABI_IDLE_SHEET)
        # Re-time the supplied sheet into enter / hover / retract. The source
        # has a strong appearance but no authored retreat, so the final four
        # frames deliberately walk backwards through earlier clean poses.
        spirit = [spirit_source[index] for index in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 7, 5, 3, 0]]
        module_frames: list[Image.Image] = []
        module_durations: list[int] = []
        signature = {"type": "generated_reference_clip", "source": repo_path(MIYABI_IDLE_SHEET), "clip": "spirit_tail", "frames": len(spirit), "loop_mode": "segmented-enter-loop-exit"}
    else:
        base_path = FIREFLY_BODY
        source_refs = FIREFLY_REFS
        base = Image.open(base_path).convert("RGBA")
        display_name = "Firefly"
        spirit = []
        module_frames, module_durations = load_module_sword_frames()
        signature = {"type": "approved_reference_clip", "source": repo_path(FIREFLY_SMOOTH), "clip": "module_sword", "frames": len(module_frames), "loop_mode": "once"}

    source_dir = pack_dir / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base_path, source_dir / f"{character}-body-approved.png")
    legacy_sheet = source_dir / "miyabi-spirit-tail-reference-sheet.png"
    if legacy_sheet.exists():
        legacy_sheet.unlink()

    clips: dict[str, list[Image.Image]] = {
        "idle": make_stand(base, character),
        "walk": make_walk(base, character),
        "sleep_cue": make_sleepy_notice(base, character),
        "sleep_enter": make_sleep_enter(base, character),
        "sleep_loop": make_sleep_loop(base, character),
        "wake": make_wake(base, character),
        "hunger_cue": make_hungry_notice(base, character),
        "eat": make_eat(base, character),
    }
    durations = {
        "idle": [450] * 8,
        "walk": [100] * 8,
        "sleep_cue": [150] * 8,
        "sleep_enter": [120] * 10,
        "sleep_loop": [250] * 12,
        "wake": [100] * 8,
        "hunger_cue": [150] * 8,
        "eat": [160] * 12,
    }
    loops = {"idle": "loop", "walk": "loop", "sleep_cue": "one_shot", "sleep_enter": "one_shot", "sleep_loop": "loop", "wake": "one_shot", "hunger_cue": "one_shot", "eat": "one_shot"}
    clip_meta: dict[str, object] = {}
    for name, frames in clips.items():
        clip_meta[name] = write_clip(pack_dir, name, frames, durations[name], loops[name], repo_path(base_path), "nearest-neighbour deterministic behavior atom")
    if character == "miyabi":
        clips["spirit_tail"] = spirit
        clip_meta["spirit_tail"] = write_clip(pack_dir, "spirit_tail", spirit, [180] * len(spirit), "segmented-enter-loop-exit", repo_path(MIYABI_IDLE_SHEET), "segmented enter-loop-exit signature frames")
    else:
        clips["module_sword"] = module_frames
        clip_meta["module_sword"] = write_clip(pack_dir, "module_sword", module_frames, module_durations, "one_shot", repo_path(FIREFLY_SMOOTH), "approved production-v2-smooth frames admitted locally")

    contact_sheet = create_contact_sheet(pack_dir, clips, {name: str(meta.get("source", "")) for name, meta in clip_meta.items() if isinstance(meta, dict)})
    review_video = render_review_video(pack_dir, clips)
    manifest: dict[str, object] = {
        "status": "draft",
        "schemaVersion": 1,
        "pack_id": f"{character}-behavior-pack-v1",
        "character": character,
        "display_name": display_name,
        "canvas_size": list(CANVAS),
        "anchor": {"right": list(ANCHOR_RIGHT), "feet_baseline_y": FEET_Y},
        "directions": {"right": "authored master", "left": "render-mirror exact horizontal pixel mirror"},
        "ordinary_safe_area": [32, 15, 128, 143],
        "source_references": source_refs,
        "clip_policy": "right-authored frames only; runtime mirrors left",
        "required_clips": ["idle", "walk", "hunger_cue", "eat", "sleep_cue", "sleep_enter", "sleep_loop", "wake", "spirit_tail" if character == "miyabi" else "module_sword"],
        "clips": clip_meta,
        "signature": signature,
        "review": {"contact_sheet": repo_path(contact_sheet), "video": review_video},
    }
    qa = qa_pack(pack_dir, manifest, clips)
    manifest["status"] = qa["status"]
    manifest["qa"] = repo_path(pack_dir / "qa.json")
    (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    stable_manifest = build_runtime_pack(character, pack_dir, runtime_pack, manifest)
    manifest["runtime_pack_manifest"] = repo_path(runtime_pack / "manifest.json")
    manifest["runtime_pack_status"] = stable_manifest["status"]
    (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "assets/generated/pixel-chibi/production-v2")
    args = parser.parse_args()
    results = {
        "miyabi": build_character("miyabi", args.output_root / "hoshimi-miyabi" / "behavior-pack-v1", RUNTIME_PACK_ROOT / "miyabi" / "v1"),
        "firefly": build_character("firefly", args.output_root / "firefly" / "behavior-pack-v1", RUNTIME_PACK_ROOT / "firefly" / "v1"),
    }
    print(json.dumps({name: {"status": manifest["status"], "runtime_pack_status": manifest["runtime_pack_status"], "manifest": str(args.output_root / ("hoshimi-miyabi" if name == "miyabi" else "firefly") / "behavior-pack-v1" / "manifest.json"), "runtime_manifest": str(RUNTIME_PACK_ROOT / name / "v1" / "manifest.json")} for name, manifest in results.items()}, indent=2))


if __name__ == "__main__":
    main()
