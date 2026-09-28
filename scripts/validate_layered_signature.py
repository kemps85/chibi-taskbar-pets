"""Independently validate a layered 32-frame signature animation output."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from remove_white_matte_fringe import clean_fringe


LOGICAL_FRAMES = 32
REVIEW_INDICES = [0, 4, 8, 12, 13, 17, 21, 24, 25, 28, 31]


def ffprobe_video(path: Path) -> dict[str, object]:
    raw = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,nb_read_frames:format=duration",
            "-of",
            "json",
            str(path),
        ],
        text=True,
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


def make_contact_sheet(root: Path, character_id: str, effect_id: str) -> Path:
    cell_width, cell_height = 384, 360
    sheet = Image.new("RGB", (cell_width * 4, cell_height * 3), (22, 35, 52))
    draw = ImageDraw.Draw(sheet)
    for slot, index in enumerate(REVIEW_INDICES):
        frame = Image.open(root / "right" / "frames" / f"frame-{index:02d}.png").convert("RGBA")
        frame = frame.resize((256, 256), Image.Resampling.NEAREST)
        column, row = slot % 4, slot // 4
        x = column * cell_width + 64
        y = row * cell_height + 54
        sheet.paste(frame, (x, y), frame)
        draw.text((column * cell_width + 6, row * cell_height + 5), str(index + 1), fill=(255, 220, 64))
    output = root / "video" / f"{character_id}-{effect_id}-logical-contact-sheet.png"
    sheet.save(output, optimize=True)
    return output


def validate(root: Path) -> dict[str, object]:
    builder_report = json.loads((root / "layered-animation-qa.json").read_text(encoding="utf-8"))
    character_id = builder_report["character_id"]
    effect_id = builder_report["effect_id"]
    body_path = root / "layers" / f"{character_id}-body-fixed.png"
    effect_path = root / "layers" / f"{effect_id}-fixed.png"
    body = Image.open(body_path).convert("RGBA")
    effect = Image.open(effect_path).convert("RGBA")
    body_pixels = list(body.getdata())
    body_opaque = [pixel[3] > 0 for pixel in body_pixels]

    body_overlay_pixel_violations = 0
    mirror_failures: list[int] = []
    dimension_failures: list[int] = []
    missing_frames: list[int] = []
    for index in range(LOGICAL_FRAMES):
        right_path = root / "right" / "frames" / f"frame-{index:02d}.png"
        left_path = root / "left" / "frames" / f"frame-{index:02d}.png"
        if not right_path.exists() or not left_path.exists():
            missing_frames.append(index + 1)
            continue
        right = Image.open(right_path).convert("RGBA")
        left = Image.open(left_path).convert("RGBA")
        if right.size != (128, 128) or left.size != (128, 128):
            dimension_failures.append(index + 1)
        for keep, actual, expected in zip(body_opaque, right.getdata(), body_pixels):
            if keep and actual != expected:
                body_overlay_pixel_violations += 1
        if left.tobytes() != right.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes():
            mirror_failures.append(index + 1)

    _, remaining_body_fringe = clean_fringe(body, max_distance=2)
    _, remaining_effect_fringe = clean_fringe(effect, max_distance=2)
    effect_bounds = effect.getchannel("A").getbbox()
    if effect_bounds is None:
        effect_gutter = None
    else:
        effect_gutter = {
            "left": effect_bounds[0],
            "top": effect_bounds[1],
            "right": effect.width - effect_bounds[2],
            "bottom": effect.height - effect_bounds[3],
        }

    videos = {path.name: ffprobe_video(path) for path in sorted((root / "video").glob("*.mp4"))}
    video_failures: list[str] = []
    for name, expected_frames, expected_duration in (
        (f"{character_id}-{effect_id}-short-review.mp4", 690, 11.5),
        (f"{character_id}-{effect_id}-60s-state-demo.mp4", 3810, 63.5),
    ):
        data = videos.get(name)
        if data is None:
            video_failures.append(f"missing:{name}")
        elif not (
            data["r_frame_rate"] == "60/1"
            and data["nb_read_frames"] == expected_frames
            and abs(data["duration"] - expected_duration) < 0.001
        ):
            video_failures.append(f"metadata:{name}")

    gutter_failure = effect_gutter is None or min(effect_gutter.values()) < 2
    failures = any(
        (
            body_overlay_pixel_violations,
            mirror_failures,
            dimension_failures,
            missing_frames,
            remaining_body_fringe,
            remaining_effect_fringe,
            video_failures,
            gutter_failure,
        )
    )
    contact_sheet = make_contact_sheet(root, character_id, effect_id)
    report = {
        "status": "FAIL" if failures else "PASS",
        "character_id": character_id,
        "effect_id": effect_id,
        "body_overlay_pixel_violations": body_overlay_pixel_violations,
        "left_right_mirror_failures": mirror_failures,
        "dimension_failures": dimension_failures,
        "missing_frames": missing_frames,
        "remaining_body_fringe_recolor_candidates": remaining_body_fringe,
        "remaining_effect_fringe_recolor_candidates": remaining_effect_fringe,
        "logical_frames": LOGICAL_FRAMES,
        "body_bbox": list(body.getchannel("A").getbbox() or ()),
        "effect_bbox": list(effect_bounds or ()),
        "effect_transparent_gutter": effect_gutter,
        "effect_gutter_failure": gutter_failure,
        "videos": videos,
        "video_failures": video_failures,
        "contact_sheet": str(contact_sheet),
    }
    (root / "cleanup-and-drift-validation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    report = validate(args.output_dir)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
