import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_pet_clip.py"
spec = importlib.util.spec_from_file_location("build_pet_clip", SCRIPT)
bpc = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bpc
spec.loader.exec_module(bpc)

RIG = {"pivot_y": 122, "trailing": {"attach_x": 52, "reach_x": 30, "start_y": 60, "reach_y": 50, "end_y": 126}}


def pose() -> Image.Image:
    im = Image.new("RGBA", (160, 144), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((52, 30, 80, 122), fill=(24, 96, 104, 255))   # body
    d.rectangle((20, 60, 52, 118), fill=(24, 24, 28, 255))    # trailing hair
    d.rectangle((56, 123, 62, 143), fill=(70, 50, 40, 255))   # legs
    d.rectangle((70, 123, 76, 143), fill=(70, 50, 40, 255))
    return im


@pytest.fixture()
def clip_root(tmp_path):
    (tmp_path / "idle").mkdir()
    pose().save(tmp_path / "idle" / "k1.png")
    return tmp_path


def run(root: Path, frames: list[dict], loop: str = "loop") -> list[np.ndarray]:
    spec_ = {"character": "test", "rig": RIG, "clips": {"c": {"loop_policy": loop, "frames": frames}}}
    path = root / "clips.json"
    path.write_text(json.dumps(spec_))
    assert bpc.main([str(path), "--no-preview"]) == 0
    manifest = json.loads((root / "clips-out" / "manifest.json").read_text())
    assert manifest["clips"]["c"]["frame_durations_ms"] == [f["ms"] for f in frames]
    return [np.asarray(Image.open(root / "clips-out" / "c" / f"frame-{i:03d}.png")) for i in range(len(frames))]


def test_bob_lifts_body_but_keeps_feet(clip_root):
    base, up = run(clip_root, [{"pose": "idle/k1.png", "ms": 100}, {"pose": "idle/k1.png", "ms": 100, "bob": -1}])
    assert np.array_equal(base[123:], up[123:])                  # feet planted
    assert up[29, 60, 3] > 0 and base[29, 60, 3] == 0            # head moved up one pixel
    assert abs(int((up[..., 3] > 0).sum()) - int((base[..., 3] > 0).sum())) < 40


def test_trailing_hair_moves_only_behind_body(clip_root):
    base, lag = run(clip_root, [{"pose": "idle/k1.png", "ms": 100},
                                {"pose": "idle/k1.png", "ms": 100, "trail_dx": -2}])
    assert np.array_equal(base[:, 53:], lag[:, 53:])             # body untouched
    assert lag[110, 18, 3] > 0 and base[110, 18, 3] == 0         # hair tip swung back
    assert not np.array_equal(base, lag)


def test_rejects_offsets_that_lose_parts(clip_root):
    with pytest.raises(SystemExit):
        run(clip_root, [{"pose": "idle/k1.png", "ms": 100, "trail_dx": -60}])


def test_fx_drawn_inside_canvas(clip_root):
    frames = run(clip_root, [
        {"pose": "idle/k1.png", "ms": 100,
         "fx": [{"type": "crescent", "cx": 90, "cy": 90, "r": 30, "a0": 200, "a1": 330, "progress": 1.0}]},
        {"pose": "idle/k1.png", "ms": 100,
         "fx": [{"type": "glint", "x0": 90, "y0": 120, "x1": 95, "y1": 60, "progress": 1.0, "motes": 0.2}]},
    ], loop="once")
    assert (frames[0][..., :3] == (255, 255, 255)).all(axis=2).sum() > 5
    assert (frames[1][..., :3] == (255, 255, 255)).all(axis=2).sum() >= 1
