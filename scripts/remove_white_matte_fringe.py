"""Remove a light matte halo from a transparent pixel-art sprite.

Only light, near-neutral edge pixels backed by a darker interior are replaced.
Enclosed whites and white objects with a white interior remain untouched.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image


def luminance(pixel: tuple[int, int, int, int]) -> float:
    red, green, blue, _ = pixel
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def edge_distances(image: Image.Image, limit: int) -> list[int]:
    width, height = image.size
    alpha = image.getchannel("A")
    distances = [-1] * (width * height)
    queue: deque[tuple[int, int]] = deque()
    for y in range(height):
        for x in range(width):
            if alpha.getpixel((x, y)) == 0:
                distances[y * width + x] = 0
                queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        distance = distances[y * width + x]
        if distance >= limit:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            index = ny * width + nx
            if distances[index] == -1:
                distances[index] = distance + 1
                queue.append((nx, ny))
    return distances


def clean_fringe(
    image: Image.Image,
    max_distance: int = 2,
    minimum_luminance: float = 105,
    maximum_chroma: int = 28,
) -> tuple[Image.Image, int]:
    source = image.convert("RGBA")
    result = source.copy()
    source_pixels = source.load()
    result_pixels = result.load()
    width, height = source.size
    distances = edge_distances(source, max_distance + 3)
    changed = 0

    for y in range(height):
        for x in range(width):
            index = y * width + x
            distance = distances[index]
            pixel = source_pixels[x, y]
            red, green, blue, alpha = pixel
            if alpha == 0 or not (1 <= distance <= max_distance):
                continue
            current_luminance = luminance(pixel)
            if current_luminance < minimum_luminance:
                continue
            if max(red, green, blue) - min(red, green, blue) > maximum_chroma:
                continue

            candidates: list[tuple[int, float, tuple[int, int, int, int]]] = []
            for radius in range(1, 5):
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        if max(abs(dx), abs(dy)) != radius:
                            continue
                        nx, ny = x + dx, y + dy
                        if not (0 <= nx < width and 0 <= ny < height):
                            continue
                        neighbour = source_pixels[nx, ny]
                        neighbour_distance = distances[ny * width + nx]
                        neighbour_luminance = luminance(neighbour)
                        if (
                            neighbour[3] > 0
                            and neighbour_distance > distance
                            and neighbour_luminance <= current_luminance - 32
                        ):
                            candidates.append((abs(dx) + abs(dy), neighbour_luminance, neighbour))
                if candidates:
                    break
            if not candidates:
                # A genuinely white object has no darker interior and is kept.
                continue
            candidates.sort(key=lambda item: (item[0], item[1]))
            replacement = candidates[0][2]
            result_pixels[x, y] = (replacement[0], replacement[1], replacement[2], alpha)
            changed += 1
    return result, changed


def clean_miyabi_enclosed_matte(image: Image.Image) -> tuple[Image.Image, int]:
    """Clear enclosed white matte pockets while preserving known white details."""
    result = image.convert("RGBA").copy()
    pixels = result.load()
    width, height = result.size
    protected_rectangles = [
        (30, 25, 66, 62),  # Face and eyes.
        (39, 52, 68, 78),  # Shirt/chest detail.
        (58, 57, 82, 90),  # Sleeve emblem.
        (0, 50, 39, 105),  # Tailless paper streamer.
    ]

    def protected(x: int, y: int) -> bool:
        return any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in protected_rectangles)

    changed = 0
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0 or protected(x, y):
                continue
            if min(red, green, blue) < 175 or max(red, green, blue) - min(red, green, blue) > 38:
                continue
            near_transparent = False
            for radius in range(1, 6):
                if any(
                    0 <= x + dx < width
                    and 0 <= y + dy < height
                    and pixels[x + dx, y + dy][3] == 0
                    for dx in range(-radius, radius + 1)
                    for dy in range(-radius, radius + 1)
                    if max(abs(dx), abs(dy)) == radius
                ):
                    near_transparent = True
                    break
            # The outer-right hair cavity is an enclosed remnant of the baked
            # white background, so it also needs explicit semantic admission.
            if near_transparent or (x >= 78 and y <= 90):
                pixels[x, y] = (red, green, blue, 0)
                changed += 1
    return result, changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-distance", type=int, default=2)
    parser.add_argument("--miyabi-cleanup", action="store_true")
    args = parser.parse_args()
    image = Image.open(args.source).convert("RGBA")
    cleaned, changed = clean_fringe(image, max_distance=args.max_distance)
    semantic_changed = 0
    if args.miyabi_cleanup:
        cleaned, semantic_changed = clean_miyabi_enclosed_matte(cleaned)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cleaned.save(args.output, optimize=True)
    print(f"changed_edge_pixels={changed}")
    print(f"cleared_enclosed_matte_pixels={semantic_changed}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
