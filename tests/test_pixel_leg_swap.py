import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "pixel_leg_swap.py"
spec = importlib.util.spec_from_file_location("pixel_leg_swap", SCRIPT)
pls = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pls
spec.loader.exec_module(pls)


def passing_pose() -> np.ndarray:
    img = np.zeros((144, 160, 4), np.uint8)
    img[60:100, 50:90] = (60, 60, 60, 255)      # skirt/body
    img[100:143, 55:63] = (240, 240, 240, 255)  # standing leg (viewer-left), reaches the baseline
    img[100:130, 70:78] = (200, 200, 200, 255)  # lifted leg (viewer-right)
    img[130:134, 70:82] = (20, 20, 20, 255)     # its shoe points right
    return img


def test_swap_moves_lift_to_other_leg_and_keeps_pixels():
    src = passing_pose()
    out = pls.swap_legs(src, (50, 100, 95, 143), 101, lifted_behind=False)
    assert np.array_equal(out[:100], src[:100])                   # body untouched
    assert out[142, 70:78, 3].all() and not out[142, 55:63, 3].any()  # standing leg now on the right hip
    assert out[131, 55:67, 3].all() and out[131, 55, 0] == 20        # lifted leg + right-pointing shoe on the left
    assert (out[..., 3] > 0).sum() == (src[..., 3] > 0).sum()      # nothing lost or invented
