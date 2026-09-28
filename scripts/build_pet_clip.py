"""Build taskbar-pet clips from approved key poses, pixel rig offsets and procedural FX.

Every character pixel is sampled from an approved key pose (integer inverse
displacement), so parts cannot appear, vanish or be redrawn between frames.
Signature FX are drawn procedurally with a fixed palette on top.

  python scripts/build_pet_clip.py assets/generated/pixel-chibi/imagegen-v1/miyabi/clips.json
  python scripts/build_pet_clip.py <clips.json> --only walk,idle
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

ART_W, ART_H = 160, 144


# ---------------------------------------------------------------- rig

def displacement(frame: dict, rig: dict) -> tuple[np.ndarray, np.ndarray]:
    """Integer (dx, dy) field; output(x, y) = pose(x - dx, y - dy).

    `bob` moves everything above `pivot_y` (negative = up). Trailing hair/cape
    (behind her, left of `attach_x`, between `start_y` and `end_y`) follows with
    `trail_bob` / `trail_dx`, weighted 0 at the body and 1 at the tips.
    Boxes in `rig["carried"]` ([x0, y0, x1, y1]) follow `bob` rigidly.
    """
    ys, xs = np.mgrid[0:ART_H, 0:ART_W].astype(np.float64)
    trail = rig["trailing"]
    wx = np.clip((trail["attach_x"] - xs) / trail["reach_x"], 0.0, 1.0)
    wy = np.clip((ys - trail["start_y"]) / trail["reach_y"], 0.0, 1.0)
    w = wx * wy * (ys <= trail.get("end_y", ART_H))
    pivot = frame.get("pivot_y", rig["pivot_y"])
    upper = ys < pivot
    bob, trail_bob = frame.get("bob", 0), frame.get("trail_bob", frame.get("bob", 0))
    dy = np.where(upper, bob * (1 - w) + trail_bob * w, 0.0)
    dx = np.where(upper, frame.get("trail_dx", 0) * w, 0.0)
    # Rigid props held by the body (e.g. a sword crossing the pivot line) move with the bob as one piece.
    for x0, y0, x1, y1 in rig.get("carried", []):
        box = (xs >= x0) & (xs <= x1) & (ys >= y0) & (ys <= y1)
        dy = np.where(box, bob, dy)
        dx = np.where(box, 0.0, dx)
    return np.rint(dx).astype(int), np.rint(dy).astype(int)


def warp(pose: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    ys, xs = np.mgrid[0:ART_H, 0:ART_W]
    return pose[np.clip(ys - dy, 0, ART_H - 1), np.clip(xs - dx, 0, ART_W - 1)]


# ----------------------------------------------------------------- fx

def _put(img: np.ndarray, x: float, y: float, rgba: tuple[int, int, int, int]) -> None:
    xi, yi = int(round(x)), int(round(y))
    if 0 <= xi < ART_W and 0 <= yi < ART_H:
        img[yi, xi] = rgba


CRESCENT_COLOURS = {   # (fresh, decaying) x (core, body, afterimage)
    "cyan": (((255, 255, 255, 255), (120, 235, 245, 255), (40, 90, 170, 230)),
             ((200, 245, 250, 230), (80, 190, 215, 200), (30, 70, 140, 170))),
    "pink": (((255, 255, 255, 255), (255, 150, 190, 255), (190, 40, 80, 230)),
             ((255, 225, 235, 230), (235, 120, 160, 200), (150, 30, 70, 170))),
    "gold": (((255, 255, 255, 255), (255, 220, 120, 255), (190, 120, 40, 230)),
             ((255, 245, 215, 230), (235, 195, 110, 200), (150, 95, 30, 170))),
}


def fx_crescent(img: np.ndarray, fx: dict) -> None:
    """Forward crescent: white-hot core, cyan body, deep-blue afterimage, pointed head.

    progress 0..1 grows the arc from a0 toward a1 (the leading head); decay 0..1
    breaks it into a dimmer ribbon plus a few shards drifting forward.
    """
    cx, cy, r = fx["cx"], fx["cy"], fx["r"]
    a0, a1 = math.radians(fx["a0"]), math.radians(fx["a1"])
    progress, decay = fx.get("progress", 1.0), fx.get("decay", 0.0)
    thickness = fx.get("thickness", 4)
    scheme = CRESCENT_COLOURS[fx.get("colors", "cyan")]
    core, body, after = scheme[0] if decay == 0 else scheme[1]
    steps = int(abs(a1 - a0) * r * 2) + 1
    head = a0 + (a1 - a0) * progress
    for i in range(steps + 1):
        t = i / steps
        a = a0 + (a1 - a0) * t * progress
        # taper: thin tail, thick middle, sharp point at the leading head
        along = t
        width = thickness * math.sin(math.pi * min(1.0, along * 0.9 + 0.1)) * (1 - 0.8 * along ** 6)
        if decay > 0 and (int(along * 17 + decay * 9) % 4 == 0 or along < decay * 0.9):
            continue
        for k in range(int(width) + 1):
            rr = r - k
            colour = core if k == 0 else body if k < max(2, width * 0.6) else after
            _put(img, cx + rr * math.cos(a), cy + rr * math.sin(a), colour)
        if decay == 0:  # afterimage one pixel behind the arc
            _put(img, cx + (r - int(width) - 1) * math.cos(a), cy + (r - int(width) - 1) * math.sin(a), after)
    if decay == 0 and progress >= 1:
        hx, hy = cx + (r + 1) * math.cos(head), cy + (r + 1) * math.sin(head)
        _put(img, hx, hy, core)
    if decay > 0:
        # shards break off at `shard_at` (fraction along the arc) and drift forward
        sa = a0 + (a1 - a0) * fx.get("shard_at", 1.0)
        for j, (ox, oy) in enumerate(((6, -3), (10, 2), (4, 5))):
            if j < 3 - int(decay * 2.5):
                sx = cx + r * math.cos(sa) + ox + decay * 8
                sy = cy + r * math.sin(sa) + oy - decay * 3
                _put(img, sx, sy, body)
                _put(img, sx + 1, sy, after)


def fx_glint(img: np.ndarray, fx: dict) -> None:
    """Mint-white glint travelling along a blade from (x0,y0) to (x1,y1), plus fading motes."""
    x0, y0, x1, y1 = fx["x0"], fx["y0"], fx["x1"], fx["y1"]
    white, mint, teal = (255, 255, 255, 255), (190, 255, 225, 235), (110, 215, 195, 200)
    progress = fx.get("progress")
    if progress is not None:
        length = max(abs(x1 - x0), abs(y1 - y0))
        px, py = x0 + (x1 - x0) * progress, y0 + (y1 - y0) * progress
        for k in range(-4, 5):  # bright streak along the blade, fading at both ends
            t = progress + k / max(1, length)
            if 0 <= t <= 1:
                _put(img, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, white if abs(k) <= 1 else mint if abs(k) <= 3 else teal)
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):  # small cross flare at the glint head
            _put(img, px + ox, py + oy, mint)
        for ox, oy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            _put(img, px + ox, py + oy, teal)
    motes = fx.get("motes")
    if motes is not None:
        # released forward (toward the right, where she faces) from mid-blade, rising and fading
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        alpha = int(235 * (1 - motes))
        for j, (ox, oy) in enumerate(((10, -6), (16, 0), (22, -10))):
            ex, ey = mx + ox + motes * 8 * (j + 1) / 2, my + oy - motes * 10
            for dx_, dy_ in ((0, 0), (1, 0), (0, 1), (1, 1)) if motes < 0.6 else ((0, 0),):
                _put(img, ex + dx_, ey + dy_, (190, 255, 225, alpha) if (dx_, dy_) == (0, 0) else (110, 215, 195, alpha * 2 // 3))


FLAME = ((255, 255, 255, 255), (190, 255, 225, 255), (110, 215, 195, 255), (40, 150, 140, 255))


def _flame_height(x: int, seed: int, tall: int) -> int:
    """Deterministic flickering tongue height for column x (no randomness, so rebuilds are identical)."""
    v = math.sin(x * 0.9 + seed * 1.7) + 0.6 * math.sin(x * 0.37 - seed * 2.3) + 0.4 * math.sin(x * 2.1 + seed)
    return max(1, int(round(tall * (0.55 + 0.25 * v))))


def fx_flame_front(img: np.ndarray, fx: dict) -> None:
    """Green transformation flame along a horizontal front at `y`, only across the silhouette (x0..x1)."""
    y, seed, tall = fx["y"], fx.get("seed", 0), fx.get("height", 9)
    alpha = img[..., 3] > 0
    for x in range(fx.get("x0", 0), fx.get("x1", ART_W)):
        near = alpha[max(0, y - 3):min(ART_H, y + 3), x].any()
        if not near:
            continue
        h = _flame_height(x, seed, tall)
        for k in range(h):
            t = k / max(1, h - 1)
            colour = FLAME[0] if k < 1 else FLAME[1] if t < 0.4 else FLAME[2] if t < 0.8 else FLAME[3]
            _put(img, x, y + 1 - k, colour)
        _put(img, x, y + 2, FLAME[2])


def fx_vortex(img: np.ndarray, fx: dict) -> None:
    """Green flame vortex: ribbons spiralling around a vertical axis (cx) from y0 up to y1."""
    cx, y0, y1, r = fx["cx"], fx["y0"], fx["y1"], fx["r"]
    phase, turns = fx.get("phase", 0.0), fx.get("turns", 2.5)
    fade = fx.get("fade", 0.0)
    for ribbon in range(3):
        for i in range(160):
            t = i / 159
            y = y0 + (y1 - y0) * t
            a = 2 * math.pi * (turns * t + phase + ribbon / 3)
            rr = r * (0.55 + 0.45 * math.sin(math.pi * t))
            if (i + ribbon * 7) % 11 < 11 * fade:
                continue
            x = cx + rr * math.cos(a)
            colour = FLAME[1] if math.sin(a) > 0 else FLAME[3]   # front half bright, back half deep
            _put(img, x, y, colour)
            if math.sin(a) > 0.3:
                _put(img, x, y - 1, FLAME[0] if i % 5 == 0 else FLAME[2])


def fx_thrust(img: np.ndarray, fx: dict) -> None:
    """Small downward green thruster plume under a hovering figure at (x, y)."""
    x, y, length, seed = fx["x"], fx["y"], fx.get("length", 8), fx.get("seed", 0)
    for dx in (-1, 0, 1):
        h = _flame_height(x + dx, seed, length) if dx else length
        for k in range(h):
            t = k / max(1, h - 1)
            _put(img, x + dx, y + k, FLAME[0] if t < 0.2 and dx == 0 else FLAME[1] if t < 0.5 else FLAME[2] if t < 0.85 else FLAME[3])


def _noise(x: int, seed: int) -> float:
    """Deterministic value in [-1, 1] per column/seed."""
    return math.sin(x * 12.9898 + seed * 78.233) * 0.5 + math.sin(x * 0.61 + seed * 1.3) * 0.5


def front_offsets(seed: int, amplitude: int) -> np.ndarray:
    """Ragged per-column offset for a transformation front."""
    return np.array([int(round(amplitude * _noise(x, seed))) for x in range(ART_W)])


def fx_flame_hug(img: np.ndarray, fx: dict) -> None:
    """Green flame that clings to the silhouette around a transformation front.

    Tongues rise from outline pixels within `band` rows above the ragged front at `y`;
    the seam itself glows as broken cracks; a few embers drift above.
    """
    y0, seed, band = fx["y"], fx.get("seed", 0), fx.get("band", 12)
    off = front_offsets(seed, fx.get("ragged", 3))
    alpha = img[..., 3] > 0
    edge = alpha & ~(np.roll(alpha, 1, 0) & np.roll(alpha, -1, 0) & np.roll(alpha, 1, 1) & np.roll(alpha, -1, 1))
    draws = []
    for y in range(max(0, y0 - band), min(ART_H, y0 + 3)):
        for x in np.nonzero(edge[y])[0]:
            fy = y0 + off[x]
            if not (fy - band <= y <= fy + 2):
                continue
            heat = 1 - (fy - y) / band            # hottest near the front
            if _noise(x * 3 + y, seed + 5) < 0.2 - heat:
                continue
            side = -1 if x > 0 and not alpha[y, x - 1] else 1 if x < ART_W - 1 and not alpha[y, x + 1] else 0
            length = 1 + int(round((2 + 3 * heat) * (0.6 + 0.4 * _noise(x + y, seed))))
            for k in range(length):
                t = k / max(1, length - 1)
                colour = FLAME[0] if k == 0 and heat > 0.7 else FLAME[1] if t < 0.4 else FLAME[2] if t < 0.8 else FLAME[3]
                draws.append((x + side * (k // 2), y - k, colour))
    for x in range(ART_W):   # glowing cracks along the seam, only over the body
        fy = y0 + off[x]
        if 0 <= fy < ART_H and alpha[fy, x] and _noise(x, seed + 9) > -0.3:
            draws.append((x, fy, FLAME[1] if _noise(x, seed + 2) > 0.2 else FLAME[2]))
    for j in range(fx.get("embers", 6)):   # embers drifting up
        ex = fx.get("x0", 20) + (fx.get("x1", 140) - fx.get("x0", 20)) * (0.5 + 0.5 * _noise(j * 7, seed))
        ey = y0 - band - 2 - abs(_noise(j * 5, seed + 3)) * 10
        draws.append((ex, ey, FLAME[1] if j % 2 else FLAME[2]))
    for x, y, c in draws:
        _put(img, x, y, c)


def fx_poof(img: np.ndarray, fx: dict) -> None:
    """Small green flame burst where a prop is put away / appears (progress 0..1)."""
    x, y, p = fx["x"], fx["y"], fx.get("progress", 0.5)
    r = 1 + 6 * p
    for k in range(10):
        a = 2 * math.pi * k / 10 + p
        colour = FLAME[0] if p < 0.3 else FLAME[1] if p < 0.6 else FLAME[2] if p < 0.85 else FLAME[3]
        _put(img, x + r * math.cos(a), y + r * math.sin(a) - p * 3, colour)
    if p < 0.5:
        for dx, dy in ((0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)):
            _put(img, x + dx, y + dy, FLAME[0] if (dx, dy) == (0, 0) else FLAME[1])


NOTE = ((255, 236, 160, 255), (230, 180, 80, 255), (170, 130, 230, 255))


def fx_notes(img: np.ndarray, fx: dict) -> None:
    """Musical notes rising and swaying from (x, y); `t` 0..1 moves them up, `count` notes."""
    x0, y0, t = fx["x"], fx["y"], fx.get("t", 0.0)
    for j in range(fx.get("count", 4)):
        phase = (t + j / fx.get("count", 4)) % 1.0
        nx = x0 + 10 * math.sin(phase * 6.3 + j) + (j - 1.5) * 7
        ny = y0 - phase * 40
        colour = NOTE[j % 3]
        if phase > 0.85:
            continue
        for dy in range(4):            # stem
            _put(img, nx + 2, ny - dy, colour)
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 0), (-1, 1)):   # head
            _put(img, nx + dx, ny + dy, colour)
        if j % 2:
            _put(img, nx + 3, ny - 3, colour)   # flag
            _put(img, nx + 4, ny - 2, colour)


FEATHER = ((255, 255, 255, 255), (235, 230, 250, 255), (200, 190, 230, 255))


def fx_feathers(img: np.ndarray, fx: dict) -> None:
    """Glowing feathers drifting down in a band x0..x1 starting at y0; `t` 0..1."""
    x0, x1, y0, t = fx["x0"], fx["x1"], fx["y0"], fx.get("t", 0.0)
    n = fx.get("count", 7)
    for j in range(n):
        phase = (t + j / n) % 1.0
        fx_ = x0 + (x1 - x0) * ((j * 0.618) % 1.0) + 5 * math.sin(phase * 9 + j)
        fy = y0 + phase * fx.get("fall", 60)
        tilt = 1 if math.sin(phase * 9 + j) > 0 else -1
        for k in range(4):
            _put(img, fx_ + tilt * (k // 2), fy + k, FEATHER[min(2, k // 2)])
        _put(img, fx_ + 1, fy + 1, FEATHER[1])


def fx_sparkle(img: np.ndarray, fx: dict) -> None:
    """Four-point twinkles around (x, y) within radius r; `t` animates them."""
    x0, y0, r, t = fx["x"], fx["y"], fx.get("r", 20), fx.get("t", 0.0)
    col = {"gold": (255, 230, 150, 255), "white": (255, 255, 255, 255), "pink": (255, 190, 215, 255)}[fx.get("color", "gold")]
    for j in range(fx.get("count", 6)):
        a = j * 2.4 + t * 3
        d = r * (0.4 + 0.6 * ((j * 0.37 + t) % 1.0))
        cx, cy = x0 + d * math.cos(a), y0 + d * math.sin(a)
        size = 1 + int(2 * abs(math.sin(t * 6 + j)))
        _put(img, cx, cy, (255, 255, 255, 255))
        for k in range(1, size + 1):
            for ox, oy in ((k, 0), (-k, 0), (0, k), (0, -k)):
                _put(img, cx + ox, cy + oy, col)


BURST = ((255, 255, 255, 255), (255, 214, 226, 255), (255, 140, 170, 255), (220, 70, 110, 255))


def fx_burst(img: np.ndarray, fx: dict) -> None:
    """Radial pink star-burst flash at (x, y): `count` rays of length r; progress 0..1 grows then fades."""
    x0, y0, r, p = fx["x"], fx["y"], fx.get("r", 40), fx.get("progress", 0.5)
    n = fx.get("count", 10)
    reach = r * min(1.0, 0.35 + p * 1.3)
    start = r * max(0.0, p - 0.45) * 1.6          # rays detach from the centre as they fade
    for j in range(n):
        a = j * 2 * math.pi / n + 0.37 * (j % 3)
        ln = reach * (0.55 + 0.45 * ((j * 0.618) % 1.0))
        k = start
        while k < ln:
            t = k / max(1.0, ln)
            colour = BURST[0] if t < 0.15 else BURST[1] if t < 0.45 else BURST[2] if t < 0.8 else BURST[3]
            _put(img, x0 + k * math.cos(a), y0 + k * math.sin(a), colour)
            k += 1
    if p < 0.4:
        for ox in range(-2, 3):
            for oy in range(-2, 3):
                if abs(ox) + abs(oy) <= 2:
                    _put(img, x0 + ox, y0 + oy, BURST[0] if abs(ox) + abs(oy) <= 1 else BURST[1])


def fx_ribbon(img: np.ndarray, fx: dict) -> None:
    """Pink glowing ribbon swirling around (x, y) in an ellipse rx x ry; `t` 0..1 rotates it, `length` in radians."""
    x0, y0, rx, ry, t = fx["x"], fx["y"], fx.get("rx", 30), fx.get("ry", 10), fx.get("t", 0.0)
    ln = fx.get("length", 2.4)
    head = t * 2 * math.pi
    steps = int(ln * max(rx, ry) * 1.2)
    for s in range(steps):
        a = head - ln * s / steps
        wob = 2 * math.sin(a * 3 + t * 5)
        x, y = x0 + rx * math.cos(a), y0 + ry * math.sin(a) + wob
        frac = s / steps
        colour = BURST[1] if frac < 0.2 else BURST[2] if frac < 0.7 else BURST[3]
        _put(img, x, y, colour)
        if frac < 0.6:
            _put(img, x, y + 1, BURST[2])


RING_SWORD = ((90, 22, 44, 255), (205, 55, 90, 255), (255, 165, 190, 255), (235, 235, 245, 255))


def fx_sword_ring(img: np.ndarray, fx: dict) -> None:
    """Thin upright red swords circling a figure on an ellipse (cx, cy, rx, ry).

    `t` rotates the ring, `rise` 0..1 lifts them out of the ground, `fade` 0..1 removes them one by one.
    Swords on the far half of the ring are only drawn where the sprite is empty, so they pass behind her.
    """
    cx, cy, rx, ry = fx["cx"], fx["cy"], fx.get("rx", 40), fx.get("ry", 8)
    n, t, length = fx.get("count", 6), fx.get("t", 0.0), fx.get("length", 26)
    rise, fade = fx.get("rise", 1.0), fx.get("fade", 0.0)
    body = img[..., 3] > 0
    for j in range(n):
        if j / n < fade:
            continue
        a = 2 * math.pi * (j / n + t)
        x = cx + rx * math.cos(a)
        base = cy + ry * math.sin(a) + round(1.5 * math.sin(a * 2 + t * 20))   # gentle hover
        behind = math.sin(a) < 0
        visible = int(round(length * rise))

        def put(px, py, c):
            px, py = int(round(px)), int(round(py))
            if 0 <= px < ART_W and 0 <= py < ART_H and not (behind and body[py, px]):
                _put(img, px, py, c)
        for k in range(visible):               # blade (point down), glowing core on the left column
            y = base - k
            put(x, y, RING_SWORD[2] if k > 1 else RING_SWORD[1])
            put(x + 1, y, RING_SWORD[1] if k > 1 else RING_SWORD[0])
        top = base - visible
        if visible > length * 0.7:            # cross-guard, grip and pommel
            for gx in (-1, 0, 1, 2):
                put(x + gx, top, RING_SWORD[3])
            put(x, top - 1, RING_SWORD[0]); put(x + 1, top - 1, RING_SWORD[0])
            put(x, top - 2, RING_SWORD[0]); put(x + 1, top - 2, RING_SWORD[0])
            put(x, top - 3, RING_SWORD[2])


FX = {"sword_ring": fx_sword_ring, "crescent": fx_crescent, "glint": fx_glint, "flame_front": fx_flame_front, "flame_hug": fx_flame_hug, "vortex": fx_vortex, "thrust": fx_thrust, "poof": fx_poof, "notes": fx_notes, "feathers": fx_feathers, "sparkle": fx_sparkle, "burst": fx_burst, "ribbon": fx_ribbon}


def draw_prop(img: np.ndarray, pose: np.ndarray, bare: np.ndarray, pivot: tuple, angle: float, at: tuple) -> None:
    """Draw the pixels that differ between `pose` and `bare` (a held prop, e.g. a sword) as a free sprite,
    rotated by `angle` degrees about `pivot` (its hilt in pose coordinates) and placed with the pivot at `at`.
    Inverse nearest-neighbour mapping so thin blades stay unbroken."""
    diff = np.abs(pose.astype(int) - bare.astype(int)).sum(2) > 0
    ys, xs = np.nonzero(diff)
    if not len(ys):
        return
    radius = int(np.ceil(np.hypot(xs - pivot[0], ys - pivot[1]).max())) + 1
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    for oy in range(-radius, radius + 1):
        for ox in range(-radius, radius + 1):
            sx = int(round(pivot[0] + ox * ca + oy * sa))      # rotate back into pose space
            sy = int(round(pivot[1] - ox * sa + oy * ca))
            if 0 <= sx < ART_W and 0 <= sy < ART_H and diff[sy, sx]:
                _put(img, at[0] + ox, at[1] + oy, tuple(int(v) for v in pose[sy, sx]))


def dissolve(pose: np.ndarray, bare: np.ndarray, hilts: list, progress: float) -> tuple[np.ndarray, list]:
    """Erase the pixels that differ between `pose` and `bare` (e.g. swords) from the tip toward the hilt.

    progress 0 = intact, 1 = gone. Returns the image and the dissolve-front pixels (for sparks).
    """
    diff = (np.abs(pose.astype(int) - bare.astype(int)).sum(2) > 0)
    ys, xs = np.nonzero(diff)
    out = pose.copy()
    if not len(ys):
        return out, []
    d = np.min([np.hypot(xs - hx, ys - hy) for hx, hy in hilts], axis=0)
    # normalise per hilt-region so both blades shrink together
    cut = d.max() * (1 - progress)
    gone = d > cut
    out[ys[gone], xs[gone]] = bare[ys[gone], xs[gone]]
    front = [(x, y) for x, y, dd in zip(xs, ys, d) if cut - 1.5 < dd <= cut]
    return out, front


# --------------------------------------------------------------- build

def build_clip(root: Path, rig: dict, name: str, clip: dict, out_root: Path) -> dict:
    cache: dict[str, np.ndarray] = {}
    out_dir = out_root / name
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("frame-*.png"):
        old.unlink()
    durations = []
    for i, frame in enumerate(clip["frames"]):
        if frame["pose"] not in cache:
            cache[frame["pose"]] = np.asarray(Image.open(root / frame["pose"]).convert("RGBA"))
        for extra in (frame.get("wipe_to"), frame.get("dissolve", {}).get("bare")):
            if extra and extra not in cache:
                cache[extra] = np.asarray(Image.open(root / extra).convert("RGBA"))
        pose = cache[frame["pose"]]
        sparks = []
        if "dissolve" in frame:
            dv = frame["dissolve"]
            pose, sparks = dissolve(pose, cache[dv["bare"]], dv["hilts"], dv["progress"])
        dxy = displacement(frame, rig)
        result = warp(pose, *dxy).copy()
        src_area, out_area = int((pose[..., 3] > 0).sum()), int((result[..., 3] > 0).sum())
        if abs(out_area - src_area) > src_area * 0.03:
            raise SystemExit(f"{name} frame {i}: opaque area {src_area}->{out_area}; rig offset too large")
        if "wipe_to" in frame:
            # transformation wipe: rows past the flame front already show the target pose
            other = warp(cache[frame["wipe_to"]], *dxy)
            rows = np.arange(ART_H)[:, None]
            front = frame["wipe_y"] + front_offsets(frame.get("wipe_seed", 0), frame.get("wipe_ragged", 0))[None, :]
            past = rows >= front if frame.get("wipe_dir", "up") == "up" else rows <= front
            result = np.where(past[..., None], other, result).copy()
        lift = frame.get("lift", 0)
        if lift:
            # whole-sprite flight offset (negative = up); nothing may leave the canvas
            moved = np.zeros_like(result)
            if lift < 0:
                assert not result[:-lift, :, 3].any(), f"{name} frame {i}: lift pushes the sprite off the top"
                moved[:lift] = result[-lift:]
            else:
                moved[lift:] = result[:-lift]
            result = moved
        for pr in frame.get("props", []):
            for extra in (pr["from"], pr["bare"]):
                if extra not in cache:
                    cache[extra] = np.asarray(Image.open(root / extra).convert("RGBA"))
            draw_prop(result, cache[pr["from"]], cache[pr["bare"]], tuple(pr["pivot"]), pr.get("angle", 0), tuple(pr["at"]))
        for x, y in sparks:
            _put(result, x, y + lift, FLAME[0] if (x + y + i) % 3 == 0 else FLAME[1])
        for fx in frame.get("fx", []):
            # FX are attached to the body/blade, so they ride the same bob.
            dy_fx = frame.get("bob", 0) + lift
            shifted = {k: (v + dy_fx if k in ("cy", "y0", "y1", "y") else v) for k, v in fx.items()}
            FX[fx["type"]](result, shifted)
        sx = frame.get("shift_x", 0)
        if sx:
            # horizontal flight offset of the whole composited frame (sprite, props and FX together)
            moved = np.zeros_like(result)
            if sx > 0:
                moved[:, sx:] = result[:, :-sx]
            else:
                moved[:, :sx] = result[:, -sx:]
            result = moved
        Image.fromarray(result, "RGBA").save(out_dir / f"frame-{i:03d}.png")
        durations.append(int(frame["ms"]))
    return {"frame_count": len(durations), "frame_durations_ms": durations,
            "loop_policy": clip["loop_policy"], "frames": f"{name}/frame-{{index:000}}.png"}


def preview(out_root: Path, name: str, meta: dict, scale: int = 4) -> Path:
    frames = [Image.open(out_root / name / f"frame-{i:03d}.png").convert("RGBA") for i in range(meta["frame_count"])]
    fps = 50
    repeats = 3 if meta["loop_policy"] == "loop" else 2
    with tempfile.TemporaryDirectory() as tmp:
        k = 0
        for _ in range(repeats):
            seq = list(zip(frames, meta["frame_durations_ms"]))
            if meta["loop_policy"] != "loop":
                seq.append((frames[-1], 500))
            for f, ms in seq:
                canvas = Image.new("RGBA", (ART_W * scale * 2, ART_H * scale), (30, 36, 48, 255))
                big = f.resize((ART_W * scale, ART_H * scale), Image.NEAREST)
                canvas.alpha_composite(big, (0, 0))
                canvas.alpha_composite(ImageOps.mirror(big), (ART_W * scale, 0))
                rgb = canvas.convert("RGB")
                for _ in range(max(1, round(ms / 1000 * fps))):
                    rgb.save(f"{tmp}/{k:05d}.png")
                    k += 1
        out = out_root / f"{name}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", f"{tmp}/%05d.png",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("clips", type=Path, help="per-character clips.json")
    parser.add_argument("--only", help="comma-separated clip names")
    parser.add_argument("--no-preview", action="store_true")
    args = parser.parse_args(argv)
    spec = json.loads(args.clips.read_text(encoding="utf-8"))
    root = args.clips.parent
    out_root = root / "clips-out"
    wanted = set(args.only.split(",")) if args.only else None
    manifest_path = out_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"clips": {}}
    manifest.update({"character": spec["character"], "canvas": [ART_W, ART_H], "master_direction": "right"})
    for name, clip in spec["clips"].items():
        if wanted and name not in wanted:
            continue
        # A clip may override rig keys (e.g. sleep poses: no carried box, waist pivot).
        meta = build_clip(root, {**spec["rig"], **clip.get("rig", {})}, name, clip, out_root)
        manifest["clips"][name] = meta
        total = sum(meta["frame_durations_ms"])
        video = "" if args.no_preview else f" -> {preview(out_root, name, meta)}"
        print(f"{name}: {meta['frame_count']} frames, {total} ms, {meta['loop_policy']}{video}")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
