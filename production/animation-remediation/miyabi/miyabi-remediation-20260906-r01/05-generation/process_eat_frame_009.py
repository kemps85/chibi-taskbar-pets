from pathlib import Path

from PIL import Image


RUN = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01")
SOURCE = RUN / "05-generation/raw/eat-frame-009-clean.png"
OUTPUT = RUN / "05-generation/eat-frame-009-body-plate-candidate.png"
STABLE_PLATE = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game\assets\runtime\taskbar-pet\clip-packs\miyabi\v1\clips\eat\right\frames\frame-000.png")

source = Image.open(SOURCE).convert("RGBA")
body = source.crop((145, 339, 677, 1124))
pixels = body.load()
for y in range(body.height):
    for x in range(body.width):
        red, green, blue, alpha = pixels[x, y]
        pixels[x, y] = (red, green, blue, 255 if alpha >= 128 else 0)
scale = 120 / body.height
body = body.resize((round(body.width * scale), 120), Image.Resampling.NEAREST)
canvas = Image.new("RGBA", (160, 144), (0, 0, 0, 0))
canvas.alpha_composite(body, (64 - body.width // 2, 23))
canvas.alpha_composite(Image.open(STABLE_PLATE).convert("RGBA"), (0, 0))
canvas.save(OUTPUT)
print({"bodyCrop": [145, 339, 677, 1124], "bodySize": body.size, "placed": [64 - body.width // 2, 23], "output": str(OUTPUT)})
