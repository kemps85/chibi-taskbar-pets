"""Publish an imagegen-v1 character (clips-out/) as a stable runtime clip pack.

    python scripts/build_runtime_pack.py miyabi firefly [--version v2]

Writes assets/runtime/taskbar-pet/clip-packs/<char>/<version>/ in the M1 pack contract
(src/taskbar-pet/m1-runtime.js validateBehaviorPackManifest): right-authored frames only,
clips/<id>/right/frames/frame-NNN.png, schema_version 1, anchor (64, ground row of the character).
The character's `signature` clip is published under its runtime id.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/generated/pixel-chibi/imagegen-v1"
PACKS = ROOT / "assets/runtime/taskbar-pet/clip-packs"
SIGNATURE_ID = {"miyabi": "spirit_tail", "firefly": "module_sword"}
GROUND = {"miyabi": 142, "firefly": 130, "evanescia": 142, "robin": 142, "remielle-dan": 142, "ye-shunguang": 142, "ye-shunguang-white": 142, "ye-shunguang-red": 142, "ye-shunguang-red-white": 142}
REQUIRED = ["idle", "walk", "hunger_cue", "eat", "sleep_cue", "sleep_enter", "sleep_loop", "wake"]


def build(character: str, version: str) -> Path:
    src = SOURCE / character / "clips-out"
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    out = PACKS / character / version
    if out.exists():
        shutil.rmtree(out)
    signature_id = SIGNATURE_ID.get(character, "signature")
    clips = {}
    for name in REQUIRED + ["signature"]:
        meta = manifest["clips"][name]
        clip_id = signature_id if name == "signature" else name
        frames_dir = out / "clips" / clip_id / "right" / "frames"
        frames_dir.mkdir(parents=True)
        for i in range(meta["frame_count"]):
            # Frames are published as authored; the pack's right_anchor.y tells the runtime which
            # row (the character's ground row) sits on the taskbar's top edge.
            shutil.copy(src / name / f"frame-{i:03d}.png", frames_dir / f"frame-{i:03d}.png")
        clips[clip_id] = {
            "frames": f"clips/{clip_id}/right/frames",
            "frame_name_pattern": "frame-{index:000}.png",
            "frame_count": meta["frame_count"],
            "right_anchor": {"x": 64, "y": GROUND[character]},
            "frame_durations_ms": meta["frame_durations_ms"],
            "loop_policy": meta["loop_policy"],
        }
    pack = {
        "status": "PASS",
        "schema_version": 1,
        "pack_id": f"{character}-{version}",
        "character_id": character,
        "canvas": {"width": 160, "height": 144},
        "master_direction": "right",
        "left_rendering": {"strategy": "mirror-right-at-runtime", "anchor_formula": "canvas.width-right_anchor.x"},
        "clip_policy": "right-authored frames only; no stored left frames",
        "source": f"assets/generated/pixel-chibi/imagegen-v1/{character}/clips-out",
        "required_clips": REQUIRED + [signature_id],
        "clips": clips,
        "signature": {"clip": signature_id, "atomic": True},
    }
    (out / "manifest.json").write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("characters", nargs="+")
    ap.add_argument("--version", default="v2")
    args = ap.parse_args(argv)
    for c in args.characters:
        print(build(c, args.version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
