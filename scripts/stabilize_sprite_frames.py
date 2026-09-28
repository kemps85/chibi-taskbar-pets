"""Lock a sprite sequence to a stable foot pivot and export FPS previews."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def foot_anchor(image: Image.Image, sample_height: int = 20) -> tuple[float, int]:
    alpha = image.getchannel("A")
    bounds = alpha.getbbox()
    if bounds is None:
        raise ValueError("Cannot anchor an empty frame")
    bottom = bounds[3] - 1
    xs: list[int] = []
    for y in range(max(0, bottom - sample_height), bottom + 1):
        for x in range(image.width):
            if alpha.getpixel((x, y)):
                xs.append(x)
    return (min(xs) + max(xs)) / 2, bottom


def gif_durations(frame_count: int, fps: int) -> list[int]:
    return [
        (round((index + 1) * 100 / fps) - round(index * 100 / fps)) * 10
        for index in range(frame_count)
    ]


def save_direction(
    frames: list[Image.Image],
    output_dir: Path,
    preview_fps: list[int],
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        frame.save(frames_dir / f"frame-{index:02d}.png", optimize=True)

    width, height = frames[0].size
    strip = Image.new("RGBA", (width * len(frames), height), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        strip.alpha_composite(frame, (index * width, 0))
    strip_path = output_dir / "strip-32x1.png"
    strip.save(strip_path, optimize=True)

    previews: dict[str, str] = {}
    for fps in preview_fps:
        path = output_dir / f"preview-32frames-{fps}fps.gif"
        frames[0].save(
            path,
            save_all=True,
            append_images=frames[1:],
            duration=gif_durations(len(frames), fps),
            loop=0,
            disposal=2,
            transparency=0,
        )
        previews[str(fps)] = str(path)
    return {"frames": str(frames_dir), "strip": str(strip_path), "previews": previews}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_frames", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--anchor-x", type=float, default=54)
    parser.add_argument("--anchor-bottom", type=int, default=123)
    parser.add_argument("--preview-fps", type=int, nargs="+", default=[16, 20, 24])
    args = parser.parse_args()

    paths = sorted(args.input_frames.glob("frame-*.png"))
    if len(paths) != 32:
        raise SystemExit(f"Expected 32 frames, found {len(paths)}")

    stabilized: list[Image.Image] = []
    offsets: list[dict[str, object]] = []
    for index, path in enumerate(paths):
        source = Image.open(path).convert("RGBA")
        source_x, source_bottom = foot_anchor(source)
        offset_x = round(args.anchor_x - source_x)
        offset_y = args.anchor_bottom - source_bottom
        target = Image.new("RGBA", source.size, (0, 0, 0, 0))
        target.alpha_composite(source, (offset_x, offset_y))
        stabilized.append(target)
        offsets.append(
            {
                "frame": index,
                "source_anchor": [source_x, source_bottom],
                "offset": [offset_x, offset_y],
            }
        )

    left = [frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for frame in stabilized]
    outputs = {
        "right": save_direction(stabilized, args.output_dir / "right", args.preview_fps),
        "left": save_direction(left, args.output_dir / "left", args.preview_fps),
    }
    report = {
        "frame_count": len(stabilized),
        "pivot": {"foot_center_x": args.anchor_x, "bottom_y": args.anchor_bottom},
        "preview_fps": args.preview_fps,
        "outputs": outputs,
        "offsets": offsets,
    }
    (args.output_dir / "stabilization-qa.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
