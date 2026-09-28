"""Normalize one generated character source into a clean 128x128 body master.

The image generator may return either real transparency or a pale baked
checkerboard.  This tool removes only edge-connected pale background pixels,
crops the subject, resizes with nearest-neighbour sampling, grounds the sprite
on a common baseline, and iterates the conservative matte-fringe cleanup until
the saved master is stable.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from process_pixel_sprite_sheet import remove_edge_background
from remove_white_matte_fringe import clean_fringe


CELL_SIZE = 128


def normalize_body(
    source_path: Path,
    output_path: Path,
    max_width: int,
    max_height: int,
    center_x: int,
    bottom: int,
) -> dict[str, object]:
    source = Image.open(source_path).convert("RGBA")
    cleaned_source = remove_edge_background(source)
    source_bounds = cleaned_source.getchannel("A").getbbox()
    if source_bounds is None:
        raise ValueError("Body source became empty after background cleanup")

    subject = cleaned_source.crop(source_bounds)
    scale = min(max_width / subject.width, max_height / subject.height)
    resized_size = (
        max(1, round(subject.width * scale)),
        max(1, round(subject.height * scale)),
    )
    subject = subject.resize(resized_size, Image.Resampling.NEAREST)

    canvas = Image.new("RGBA", (CELL_SIZE, CELL_SIZE), (0, 0, 0, 0))
    x = round(center_x - subject.width / 2)
    y = bottom - subject.height
    if x < 0 or y < 0 or x + subject.width > CELL_SIZE or y + subject.height > CELL_SIZE:
        raise ValueError(
            f"Normalized body does not fit 128x128: position={(x, y)}, size={subject.size}"
        )
    canvas.alpha_composite(subject, (x, y))

    fringe_changes = 0
    cleanup_passes = 0
    for _ in range(8):
        canvas, changed = clean_fringe(canvas, max_distance=2)
        cleanup_passes += 1
        fringe_changes += changed
        if changed == 0:
            break

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, optimize=True)
    output_bounds = canvas.getchannel("A").getbbox()
    alpha_values = sorted(set(canvas.getchannel("A").getdata()))
    report = {
        "status": "PASS",
        "source": str(source_path),
        "output": str(output_path),
        "source_size": list(source.size),
        "source_alpha_bounds_after_background_cleanup": list(source_bounds),
        "output_size": [CELL_SIZE, CELL_SIZE],
        "output_alpha_bounds": list(output_bounds) if output_bounds else None,
        "placement": {
            "max_width": max_width,
            "max_height": max_height,
            "center_x": center_x,
            "bottom": bottom,
            "position": [x, y],
            "resized_subject": list(resized_size),
        },
        "cleanup": {
            "passes": cleanup_passes,
            "fringe_pixels_recolored": fringe_changes,
            "stable": cleanup_passes < 8,
        },
        "transparent_corners": all(
            canvas.getpixel(point)[3] == 0
            for point in ((0, 0), (127, 0), (0, 127), (127, 127))
        ),
        "alpha_value_count": len(alpha_values),
    }
    output_path.with_name(f"{output_path.stem}-qa.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-width", type=int, default=120)
    parser.add_argument("--max-height", type=int, default=119)
    parser.add_argument("--center-x", type=int, default=64)
    parser.add_argument("--bottom", type=int, default=124)
    args = parser.parse_args()
    report = normalize_body(
        args.source,
        args.output,
        args.max_width,
        args.max_height,
        args.center_x,
        args.bottom,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
