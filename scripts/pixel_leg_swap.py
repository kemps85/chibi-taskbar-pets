"""Make the opposite-leg passing pose by swapping the two legs of an approved key pose.

Imagegen cannot tell a chibi's left leg from her right one, so "lift the other
leg" requests come back identical. This moves each leg (every pixel copied, no
redraw) under the other hip, keeping shoe orientation.

  python scripts/pixel_leg_swap.py walk/wk2.png walk/wk2_other.png \
      --region 54,97,96,143 --separate-y 114 --lifted-behind
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

NEIGHBOURS = ((-1, 0), (0, 1), (0, -1), (1, 0))


def split_legs(img: np.ndarray, x0: int, y0: int, x1: int, y1: int, separate_y: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (viewer-left leg, viewer-right leg, all leg pixels) masks.

    Below `separate_y` the legs are separate blobs; they are grown upward
    together (multi-source BFS) so touching thighs split down the middle.
    """
    h, w = img.shape[:2]
    region = np.zeros((h, w), bool)
    region[y0:y1 + 1, x0:x1 + 1] = True
    legs = region & (img[..., 3] > 0)
    label = np.zeros((h, w), int)
    count = 0
    for y in range(separate_y, y1 + 1):
        for x in range(x0, x1 + 1):
            if legs[y, x] and not label[y, x]:
                count += 1
                label[y, x] = count
                queue = deque([(y, x)])
                while queue:
                    cy, cx = queue.popleft()
                    for oy, ox in NEIGHBOURS:
                        ny, nx = cy + oy, cx + ox
                        if separate_y <= ny < h and 0 <= nx < w and legs[ny, nx] and not label[ny, nx]:
                            label[ny, nx] = count
                            queue.append((ny, nx))
    sizes = [(label == c).sum() for c in range(1, count + 1)]
    if len(sizes) < 2:
        raise SystemExit(f"legs are not separate below y={separate_y}")
    keep = np.argsort(sizes)[::-1][:2] + 1
    label[~np.isin(label, keep)] = 0
    queue = deque(zip(*np.nonzero(label)))
    while queue:
        cy, cx = queue.popleft()
        for oy, ox in NEIGHBOURS:
            ny, nx = cy + oy, cx + ox
            if 0 <= ny < h and 0 <= nx < w and legs[ny, nx] and not label[ny, nx]:
                label[ny, nx] = label[cy, cx]
                queue.append((ny, nx))
    a, b = (label == keep[0]), (label == keep[1])
    if np.nonzero(a)[1].mean() > np.nonzero(b)[1].mean():
        a, b = b, a
    return a, b, legs


def swap_legs(img: np.ndarray, region: tuple[int, int, int, int], separate_y: int, lifted_behind: bool) -> np.ndarray:
    left, right, legs = split_legs(img, *region, separate_y)

    def hip_x(mask: np.ndarray) -> float:
        ys, xs = np.nonzero(mask)
        return xs[ys < ys.min() + 3].mean()

    shift = int(round(hip_x(right) - hip_x(left)))
    standing_is_left = np.nonzero(left)[0].max() >= np.nonzero(right)[0].max()
    standing, lifted = (left, right) if standing_is_left else (right, left)
    standing_dx = shift if standing_is_left else -shift
    out = img.copy()
    out[legs] = 0
    layers = [(lifted, -standing_dx), (standing, standing_dx)]
    for mask, dx in (layers if lifted_behind else layers[::-1]):
        ys, xs = np.nonzero(mask)
        out[ys, np.clip(xs + dx, 0, img.shape[1] - 1)] = img[ys, xs]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pose", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--region", required=True, help="x0,y0,x1,y1 containing only the legs (below the hem)")
    parser.add_argument("--separate-y", type=int, required=True, help="first row where the two legs no longer touch")
    parser.add_argument("--lifted-behind", action="store_true", help="draw the lifted leg behind the standing leg")
    args = parser.parse_args(argv)
    img = np.asarray(Image.open(args.pose).convert("RGBA"))
    region = tuple(int(v) for v in args.region.split(","))
    Image.fromarray(swap_legs(img, region, args.separate_y, args.lifted_behind), "RGBA").save(args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
