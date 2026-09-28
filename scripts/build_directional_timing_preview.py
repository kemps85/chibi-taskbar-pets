"""Build right/left 32-frame previews from keyframes and in-betweens."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def save_outputs(frames: list[Image.Image], output_dir: Path, fps: int) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        frame.save(frames_dir / f"frame-{index:02d}.png", optimize=True)

    cell_width, cell_height = frames[0].size
    strip = Image.new("RGBA", (cell_width * len(frames), cell_height), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        strip.alpha_composite(frame, (index * cell_width, 0))

    strip_path = output_dir / "strip-32x1.png"
    preview_path = output_dir / "preview-32frames-16fps.gif"
    strip.save(strip_path, optimize=True)
    # GIF stores time in 10 ms units. Distribute 60/70 ms ticks so the full
    # sequence still averages exactly 16 FPS instead of silently becoming
    # 16.67 FPS through constant-duration rounding.
    frame_durations = [
        (round((index + 1) * 100 / fps) - round(index * 100 / fps)) * 10
        for index in range(len(frames))
    ]
    frames[0].save(
        preview_path,
        save_all=True,
        append_images=frames[1:],
        duration=frame_durations,
        loop=0,
        disposal=2,
        transparency=0,
    )
    return {"strip": str(strip_path), "preview": str(preview_path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_frames", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--inbetween-frames", type=Path)
    parser.add_argument("--fps", type=int, default=16)
    args = parser.parse_args()

    source_paths = sorted(args.input_frames.glob("frame-*.png"))
    if len(source_paths) != 16:
        raise SystemExit(f"Expected 16 source frames, found {len(source_paths)}")

    keyframes = [Image.open(path).convert("RGBA") for path in source_paths]
    if args.inbetween_frames:
        inbetween_paths = sorted(args.inbetween_frames.glob("frame-*.png"))
        if len(inbetween_paths) != 16:
            raise SystemExit(f"Expected 16 in-between frames, found {len(inbetween_paths)}")
        inbetweens = [Image.open(path).convert("RGBA") for path in inbetween_paths]
        right_frames = [frame for pair in zip(keyframes, inbetweens, strict=True) for frame in pair]
        construction = "16 keyframes interleaved with 16 drawn in-between frames"
        final_requirement = "review and manually correct any remaining inconsistent frame"
    else:
        right_frames = [frame.copy() for frame in keyframes for _ in range(2)]
        construction = "16 keyframes held for two ticks"
        final_requirement = "replace held duplicate ticks with 16 drawn in-between frames after timing approval"
    left_frames = [frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for frame in right_frames]

    outputs = {
        "right": save_outputs(right_frames, args.output_dir / "right", args.fps),
        "left": save_outputs(left_frames, args.output_dir / "left", args.fps),
    }
    report = {
        "purpose": "32-frame direction and timing preview",
        "source_unique_keyframes": len(keyframes),
        "prototype_frame_count": len(right_frames),
        "fps": args.fps,
        "clip_duration_seconds": len(right_frames) / args.fps,
        "direction_strategy": "horizontal mirror requested by user",
        "construction": construction,
        "final_art_requirement": final_requirement,
        "outputs": outputs,
    }
    report_path = args.output_dir / "timing-qa.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
