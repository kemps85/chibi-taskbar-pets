import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "imagegen_postprocess.py"
spec = importlib.util.spec_from_file_location("imagegen_postprocess", SCRIPT)
pp = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pp
spec.loader.exec_module(pp)

MAGENTA = (255, 0, 255)


def synthetic_master() -> Image.Image:
    """Chibi-like test sprite: ears, head, red eyes, teal cape, skirt, feet on y=143."""
    im = Image.new("RGBA", (160, 144), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(48, 30), (54, 10), (60, 30)], fill=(30, 30, 34, 255))
    d.polygon([(68, 30), (74, 10), (80, 30)], fill=(30, 30, 34, 255))
    d.ellipse((44, 24, 84, 64), fill=(24, 24, 28, 255))
    d.rectangle((52, 38, 76, 58), fill=(245, 228, 214, 255))
    d.rectangle((56, 44, 58, 47), fill=(214, 40, 30, 255))
    d.rectangle((68, 44, 70, 47), fill=(214, 40, 30, 255))
    d.rectangle((48, 64, 80, 104), fill=(24, 96, 104, 255))
    d.rectangle((52, 104, 76, 126), fill=(20, 20, 22, 255))
    d.rectangle((54, 126, 60, 143), fill=(70, 50, 40, 255))
    d.rectangle((68, 126, 74, 143), fill=(70, 50, 40, 255))
    d.line((30, 70, 46, 120), fill=(60, 60, 70, 255), width=3)
    return im


def fake_imagegen(frame: Image.Image, scale: float, origin: tuple[int, int], noise: int, seed: int = 3) -> Image.Image:
    """Render like an imagegen output: non-integer scale, bicubic softness, colour noise."""
    art = Image.new("RGBA", frame.size, MAGENTA + (255,))
    art.alpha_composite(frame)
    size = (round(160 * scale), round(144 * scale))
    canvas = Image.new("RGB", (1024, 1024), MAGENTA)
    canvas.paste(art.convert("RGB").resize(size, Image.BICUBIC), origin)
    arr = np.asarray(canvas).astype(np.int16)
    arr += np.random.default_rng(seed).integers(-noise, noise + 1, arr.shape, dtype=np.int16)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


@pytest.fixture()
def workspace(tmp_path):
    master_path = tmp_path / "master.png"
    synthetic_master().save(master_path)
    root = tmp_path / "inputs"
    assert pp.main(["--input-root", str(root), "init", "--character", "test", "--source", str(master_path)]) == 0
    return tmp_path, root, root / "test" / "master_locked.png"


def process(workspace, raw: Image.Image, *extra: str) -> tuple[int, dict, Image.Image]:
    tmp, root, ref = workspace
    raw_path = tmp / "raw.png"
    raw.save(raw_path)
    out = tmp / "out" / "frame"
    code = pp.main(["--input-root", str(root), "process", "--character", "test", "--raw", str(raw_path),
                    "--reference", str(ref), "--out", str(out), *extra])
    qa = json.loads((tmp / "out" / "frame_qa.json").read_text())
    return code, qa, Image.open(tmp / "out" / "frame.png")


def test_init_writes_locked_assets(workspace):
    _, root, ref = workspace
    palette = json.loads((root / "test" / "palette.json").read_text())["colors"]
    assert "#d6281e" in palette  # small red accent must survive quantisation
    assert Image.open(ref).size == (160, 144)
    assert Image.open(root / "test" / "master_input_1024.png").size == (1024, 1024)


def test_recovers_master_from_drifted_scale_and_noise(workspace):
    _, _, ref = workspace
    raw = fake_imagegen(Image.open(ref), scale=6.3, origin=(20, 70), noise=12)
    code, qa, frame = process(workspace, raw)
    assert code == 0, qa
    ref_a = np.asarray(Image.open(ref))[..., 3] > 0
    new_a = np.asarray(frame)[..., 3] > 0
    assert (ref_a ^ new_a).sum() / ref_a.sum() < 0.03
    assert np.asarray(frame)[..., 3].max() == 255
    assert qa["registration"]["scale"] == pytest.approx(6.3, abs=0.1)


def test_missing_part_fails(workspace):
    _, _, ref = workspace
    broken = Image.open(ref).copy()
    ImageDraw.Draw(broken).rectangle((0, 0, 159, 30), fill=(0, 0, 0, 0))  # model dropped the ears
    code, qa, _ = process(workspace, fake_imagegen(broken, 6.0, (32, 80), 6))
    assert code == 1
    failed = {c["check"] for c in qa["checks"] if not c["ok"]}
    assert "only_allowed_regions_changed" in failed or "no_colour_group_lost" in failed


def test_change_inside_allowed_region_passes(workspace):
    _, _, ref = workspace
    blink = Image.open(ref).copy()
    d = ImageDraw.Draw(blink)
    d.rectangle((56, 44, 58, 47), fill=(245, 228, 214, 255))
    d.rectangle((68, 44, 70, 47), fill=(245, 228, 214, 255))
    d.line((56, 46, 58, 46), fill=(24, 24, 28, 255))
    d.line((68, 46, 70, 46), fill=(24, 24, 28, 255))
    raw = fake_imagegen(blink, 6.0, (32, 80), 6)
    assert process(workspace, raw)[0] == 1
    code, qa, _ = process(workspace, raw, "--allow", "52,40,76,50")
    assert code == 0, qa


def test_canvas_crop_fails(workspace):
    _, _, ref = workspace
    # imagegen framed the sprite so the weapon runs off the left border of the output
    raw = fake_imagegen(Image.open(ref), 6.0, (-190, 80), 4)
    code, qa, _ = process(workspace, raw, "--allow", "all")
    assert code == 1
    assert any(c["check"] == "not_cropped_by_canvas" and not c["ok"] for c in qa["checks"])


def test_stray_speck_removed(workspace):
    _, _, ref = workspace
    speck = Image.open(ref).copy()
    ImageDraw.Draw(speck).rectangle((120, 20, 121, 21), fill=(24, 96, 104, 255))
    code, qa, frame = process(workspace, fake_imagegen(speck, 6.0, (32, 80), 4))
    assert code == 0, qa
    assert np.asarray(frame)[18:24, 118:124, 3].max() == 0
