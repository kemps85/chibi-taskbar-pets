"""Bring Miyabi key poses in line with the official 3D model (render: assets/references/character-equipment/miyabi/body-flat).

- The collar is a white shirt with a thin BLACK tie. Earlier sprites drew a big red bow: it is repainted as shirt and a tie is drawn.
- Tights and ankle boots are BLACK, not brown: brown hues in the leg zone are remapped to neutral dark greys from the palette.

    python scripts/miyabi_model_fixes.py <pose.png> [...]   # rewrites in place
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
PALETTE = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in json.loads(
    (ROOT / "assets/references/imagegen-inputs/miyabi/palette.json").read_text())["colors"]])
TIE, TIE_LIGHT = (26, 24, 28), (70, 70, 76)


def lum(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def bow_to_tie(img: np.ndarray) -> bool:
    rgb, a = img[..., :3].astype(int), img[..., 3] > 0
    red = a & (rgb[..., 0] > 120) & (rgb[..., 0] > rgb[..., 1] * 1.8) & (rgb[..., 0] > rgb[..., 2] * 1.8)
    lab, n = ndimage.label(ndimage.binary_closing(red, iterations=1) & a)
    if not n:
        return False
    sizes = ndimage.sum(red, lab, range(1, n + 1))
    k = int(np.argmax(sizes)) + 1
    if sizes[k - 1] < 25:          # eyes are small red clusters; the bow is the big one
        return False
    ys, xs = np.nonzero(lab == k)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    # shirt colours: light neutral pixels around the bow
    win = rgb[max(0, y0 - 3):y1 + 4, max(0, x0 - 4):x1 + 5].reshape(-1, 3)
    wa = a[max(0, y0 - 3):y1 + 4, max(0, x0 - 4):x1 + 5].reshape(-1)
    light = win[wa & (lum(win) > 190) & (np.ptp(win, axis=1) < 30)]
    shirt = light[np.argsort(lum(light))[len(light) // 2]] if len(light) else np.array([232, 228, 226])
    shade = np.clip(shirt - 28, 0, 255)
    cx = int(round(xs.mean()))
    for y, x in zip(ys, xs):
        img[y, x, :3] = shade if x < cx - 1 else shirt
    for y in range(y0, y1 + 1):   # thin black tie: 3 px knot, then 2 px, tapering to 1 px
        width = 3 if y < y0 + 2 else 2 if y < y1 - 2 else 1
        for dx in range(width):
            x = cx - width // 2 + dx
            if a[y, x]:
                img[y, x, :3] = TIE_LIGHT if (dx == width - 1 and width > 1 and y > y0 + 1) else TIE
    return True


def black_legs(img: np.ndarray, y_from: int) -> int:
    rgb, a = img[..., :3].astype(int), img[..., 3] > 0
    L = lum(rgb)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    brown = a & (r > b + 18) & (r >= g) & (g > b - 5) & (L < 175) & (L > 35) & ~((r > 170) & (g > 140))  # not gold, not skin
    brown[:y_from] = False
    greys = PALETTE[np.ptp(PALETTE, axis=1) < 16]
    glum = lum(greys)
    ys, xs = np.nonzero(brown)
    for y, x in zip(ys, xs):
        target = 14 + 0.42 * L[y, x]
        img[y, x, :3] = greys[np.argmin(np.abs(glum - target))]
    return len(ys)


def main(paths: list[str]) -> int:
    for p in paths:
        img = np.asarray(Image.open(p).convert("RGBA")).copy()
        alpha = img[..., 3] > 0
        top = int(np.nonzero(alpha.any(1))[0].min())
        tie = bow_to_tie(img)
        # leg zone starts well below the face (ears have light-brown insides)
        n = black_legs(img, top + 60)
        Image.fromarray(img, "RGBA").save(p)
        print(f"{p}: tie={'yes' if tie else 'no'} legs_recoloured={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
