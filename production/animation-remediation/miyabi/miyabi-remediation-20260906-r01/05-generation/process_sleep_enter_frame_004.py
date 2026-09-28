from pathlib import Path

from PIL import Image


RUN = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01")
SOURCE = RUN / "05-generation/raw/sleep-enter-frame-004-imagegen.png"
OUTPUT = RUN / "05-generation/sleep-enter-frame-004-candidate.png"

image = Image.open(SOURCE).convert("RGBA")
pixels = image.load()
for y in range(image.height):
    for x in range(image.width):
        red, green, blue, alpha = pixels[x, y]
        pixels[x, y] = (red, green, blue, 255 if alpha >= 128 else 0)
bbox = image.getchannel("A").getbbox()
if bbox is None:
    raise RuntimeError("no authored pixels")
image = image.crop(bbox)
scale = min(124 / image.width, 112 / image.height)
image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.NEAREST)
canvas = Image.new("RGBA", (160, 144), (0, 0, 0, 0))
canvas.alpha_composite(image, (64 - image.width // 2, 143 - image.height))
canvas.save(OUTPUT)
print({"sourceBBox": bbox, "resized": image.size, "placed": [64 - image.width // 2, 143 - image.height], "output": str(OUTPUT)})
