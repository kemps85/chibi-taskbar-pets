from pathlib import Path
from collections import deque

from PIL import Image


RUN = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01")
SOURCE = RUN / "05-generation/raw/eat-frame-006-imagegen.png"
OUTPUT = RUN / "05-generation/eat-frame-006-body-plate-candidate.png"
STABLE_PLATE = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game\assets\runtime\taskbar-pet\clip-packs\miyabi\v1\clips\eat\right\frames\frame-000.png")


def erase_border_background(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size
    seen: set[tuple[int, int]] = set()
    queue = deque(
        [(x, 0) for x in range(width)]
        + [(x, height - 1) for x in range(width)]
        + [(0, y) for y in range(height)]
        + [(width - 1, y) for y in range(height)]
    )
    while queue:
        x, y = queue.popleft()
        if (x, y) in seen:
            continue
        red, green, blue, _alpha = pixels[x, y]
        if min(red, green, blue) < 210 or max(red, green, blue) - min(red, green, blue) > 55:
            continue
        seen.add((x, y))
        for next_x, next_y in (
            (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1),
            (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1), (x + 1, y + 1),
        ):
            if 0 <= next_x < width and 0 <= next_y < height and (next_x, next_y) not in seen:
                queue.append((next_x, next_y))
    for x, y in seen:
        red, green, blue, _alpha = pixels[x, y]
        pixels[x, y] = (red, green, blue, 0)
    return image


image = erase_border_background(Image.open(SOURCE))
# The raw output separates the character at this bounded crop from the plate.
# The plate is restored from the stable frame-000 semantics, not regenerated.
body = image.crop((202, 168, 823, 1038))
scale = 120 / body.height
body = body.resize((round(body.width * scale), 120), Image.Resampling.NEAREST)
canvas = Image.new("RGBA", (160, 144), (0, 0, 0, 0))
canvas.alpha_composite(body, (64 - body.width // 2, 23))
plate = Image.open(STABLE_PLATE).convert("RGBA")
canvas.alpha_composite(plate, (0, 0))
canvas.save(OUTPUT)
print({"raw": str(SOURCE), "bodyCrop": [202, 168, 823, 1038], "bodySize": body.size, "placed": [64 - body.width // 2, 23], "plateSource": str(STABLE_PLATE), "output": str(OUTPUT)})
