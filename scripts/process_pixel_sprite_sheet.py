"""Normalize an AI sprite grid into taskbar-pet production assets.

The generator sometimes bakes a pale checkerboard into its PNG.  This script
removes only pale, edge-connected pixels, preserving enclosed whites in the
character, then exports fixed-size cells with nearest-neighbour resampling.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from PIL import Image


def is_background(pixel: tuple[int, int, int, int]) -> bool:
    red, green, blue, _ = pixel
    return min(red, green, blue) >= 225 and max(red, green, blue) - min(red, green, blue) <= 12


def remove_edge_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    queue: deque[tuple[int, int]] = deque()
    visited = bytearray(width * height)

    def enqueue(x: int, y: int) -> None:
        index = y * width + x
        if not visited[index] and is_background(pixels[x, y]):
            visited[index] = 1
            queue.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)
    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while queue:
        x, y = queue.popleft()
        red, green, blue, _ = pixels[x, y]
        pixels[x, y] = (red, green, blue, 0)
        if x:
            enqueue(x - 1, y)
        if x + 1 < width:
            enqueue(x + 1, y)
        if y:
            enqueue(x, y - 1)
        if y + 1 < height:
            enqueue(x, y + 1)

    return rgba


def alpha_bounds(image: Image.Image) -> tuple[int, int, int, int] | None:
    return image.getchannel("A").getbbox()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--rows", type=int, default=4)
    parser.add_argument("--cell-size", type=int, default=128)
    parser.add_argument("--fps", type=int, default=16)
    args = parser.parse_args()

    source = Image.open(args.source).convert("RGBA")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = args.output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    x_edges = [round(index * source.width / args.columns) for index in range(args.columns + 1)]
    y_edges = [round(index * source.height / args.rows) for index in range(args.rows + 1)]
    frames: list[Image.Image] = []
    report_frames: list[dict[str, object]] = []

    for row in range(args.rows):
        for column in range(args.columns):
            crop_box = (
                x_edges[column],
                y_edges[row],
                x_edges[column + 1],
                y_edges[row + 1],
            )
            cell = source.crop(crop_box)
            cell = remove_edge_background(cell)
            cell = cell.resize((args.cell_size, args.cell_size), Image.Resampling.NEAREST)
            frame_number = len(frames)
            frame_path = frames_dir / f"frame-{frame_number:02d}.png"
            cell.save(frame_path, optimize=True)
            bounds = alpha_bounds(cell)
            report_frames.append(
                {
                    "frame": frame_number,
                    "path": str(frame_path),
                    "alpha_bounds": list(bounds) if bounds else None,
                    "transparent_corners": [
                        cell.getpixel((0, 0))[3] == 0,
                        cell.getpixel((args.cell_size - 1, 0))[3] == 0,
                        cell.getpixel((0, args.cell_size - 1))[3] == 0,
                        cell.getpixel((args.cell_size - 1, args.cell_size - 1))[3] == 0,
                    ],
                }
            )
            frames.append(cell)

    normalized_sheet = Image.new(
        "RGBA",
        (args.columns * args.cell_size, args.rows * args.cell_size),
        (0, 0, 0, 0),
    )
    strip = Image.new(
        "RGBA",
        (len(frames) * args.cell_size, args.cell_size),
        (0, 0, 0, 0),
    )
    for index, frame in enumerate(frames):
        normalized_sheet.alpha_composite(
            frame,
            ((index % args.columns) * args.cell_size, (index // args.columns) * args.cell_size),
        )
        strip.alpha_composite(frame, (index * args.cell_size, 0))

    sheet_path = args.output_dir / "sheet-4x4.png"
    strip_path = args.output_dir / "strip-16x1.png"
    preview_path = args.output_dir / "preview-16fps.gif"
    report_path = args.output_dir / "qa-report.json"
    normalized_sheet.save(sheet_path, optimize=True)
    strip.save(strip_path, optimize=True)
    frames[0].save(
        preview_path,
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / args.fps),
        loop=0,
        disposal=2,
        transparency=0,
    )

    report = {
        "source": str(args.source),
        "source_size": list(source.size),
        "grid": {"columns": args.columns, "rows": args.rows},
        "frame_count": len(frames),
        "cell_size": [args.cell_size, args.cell_size],
        "fps": args.fps,
        "all_corners_transparent": all(all(item["transparent_corners"]) for item in report_frames),
        "outputs": {
            "sheet": str(sheet_path),
            "strip": str(strip_path),
            "preview": str(preview_path),
        },
        "frames": report_frames,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
