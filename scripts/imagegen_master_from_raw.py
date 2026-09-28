"""Turn a raw imagegen master (magenta background, ~6x pixel grid) into a 160x144 source frame
for `imagegen_postprocess.py init` (which then builds the character palette and locked master).

    python scripts/imagegen_master_from_raw.py <raw.png> <out.png> [--ground 142] [--center-x 72]
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
from PIL import Image

_spec = importlib.util.spec_from_file_location("imagegen_postprocess", Path(__file__).with_name("imagegen_postprocess.py"))
pp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = pp
_spec.loader.exec_module(pp)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw")
    ap.add_argument("out")
    ap.add_argument("--ground", type=int, default=142, help="row the lowest pixel (feet) lands on")
    ap.add_argument("--center-x", type=float, default=None, help="x of the body centre; default keeps the imagegen position")
    args = ap.parse_args(argv)
    raw = np.asarray(Image.open(args.raw).convert("RGB"))
    bg = pp.key_mask(raw)
    expected = pp.INPUT_SCALE * raw.shape[1] / pp.INPUT_SIZE
    scale = pp.find_scale(raw, bg, expected * 0.9, expected * 1.1)
    if abs(scale - expected) / expected > 0.06:
        scale = expected
    origin = (pp.INPUT_ORIGIN[0] * raw.shape[1] / pp.INPUT_SIZE, pp.INPUT_ORIGIN[1] * raw.shape[0] / pp.INPUT_SIZE)
    grid = pp.Grid(scale, *origin)
    grid, _ = pp.refine_phase(raw, bg, grid, np.zeros((pp.ART_H, pp.ART_W), bool), np.ones((pp.ART_H, pp.ART_W)), 0, 0.0)
    rgb, alpha = pp.sample_grid(raw, bg, grid, max(0, int(grid.scale * 0.25)))
    alpha, _ = pp.remove_specks(alpha, 6)
    ys, xs = np.nonzero(alpha)
    dy = args.ground - ys.max()
    dx = 0 if args.center_x is None else int(round(args.center_x - xs.mean()))
    out = np.zeros((pp.ART_H, pp.ART_W, 4), np.uint8)
    ty, tx = ys + dy, xs + dx
    ok = (ty >= 0) & (ty < pp.ART_H) & (tx >= 0) & (tx < pp.ART_W)
    out[ty[ok], tx[ok], :3] = rgb[ys[ok], xs[ok]]
    out[ty[ok], tx[ok], 3] = 255
    Image.fromarray(out, "RGBA").save(args.out)
    print(f"{args.out}: scale {grid.scale:.2f}, shift ({dx},{dy}), clipped {int((~ok).sum())} px, height {ys.max() - ys.min() + 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
