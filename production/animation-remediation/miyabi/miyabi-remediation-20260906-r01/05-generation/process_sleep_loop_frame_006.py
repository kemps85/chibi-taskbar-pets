from pathlib import Path

from PIL import Image


RUN = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01")
SOURCE = RUN / "05-generation/raw/sleep-loop-frame-006-imagegen.png"
OUTPUT = RUN / "05-generation/sleep-loop-frame-006-candidate.png"


def remove_border_connected_near_white(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size
    seen: set[tuple[int, int]] = set()
    stack = [(x, 0) for x in range(width)] + [(x, height - 1) for x in range(width)]
    stack += [(0, y) for y in range(height)] + [(width - 1, y) for y in range(height)]
    while stack:
        x, y = stack.pop()
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
                stack.append((next_x, next_y))
    for x, y in seen:
        red, green, blue, _alpha = pixels[x, y]
        pixels[x, y] = (red, green, blue, 0)
    return image


image = remove_border_connected_near_white(Image.open(SOURCE).convert("RGBA"))
bbox = image.getchannel("A").getbbox()
if bbox is None:
    raise RuntimeError("no authored pixels after border cleanup")
image = image.crop(bbox)
scale = min(124 / image.width, 112 / image.height)
size = (round(image.width * scale), round(image.height * scale))
image = image.resize(size, Image.Resampling.NEAREST)
canvas = Image.new("RGBA", (160, 144), (0, 0, 0, 0))
x = 64 - image.width // 2
y = 143 - image.height
canvas.alpha_composite(image, (x, y))
canvas.save(OUTPUT)
print({"bbox": bbox, "resized": image.size, "placed": (x, y), "output": str(OUTPUT)})
