from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image


RUN = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01")
SOURCE = RUN / "05-generation/sleep-enter-frame-004-candidate.png"
OUT = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game\assets\generated\pixel-chibi\production-v2\hoshimi-miyabi\remediation\miyabi-remediation-20260906-r01\sleep_loop")

for old in OUT.glob("*.png"):
    old.unlink()
OUT.mkdir(parents=True, exist_ok=True)

base = Image.open(SOURCE).convert("RGBA")
if base.size != (160, 144):
    raise RuntimeError(f"unexpected source canvas: {base.size}")


def hair_sway(image: Image.Image, outward: bool) -> Image.Image:
    result = image.copy()
    pixels = result.load()
    # A deliberately tiny, named trailing-hair contour mask. The support,
    # feet, torso, face, coat body, and weapon are not touched.
    for y in range(113, 119):
        if outward:
            source = image.getpixel((86, y))
            if source[3] == 255:
                pixels[86, y] = (0, 0, 0, 0)
                pixels[87, y] = source
        else:
            source = image.getpixel((86, y))
            pixels[86, y] = source
            pixels[87, y] = (0, 0, 0, 0)
    return result


# 12 x 250 ms = 3,000 ms. Holds dominate; the only motion is a three-frame
# one-pixel hair-contour inhale/settle, returning to the exact base at frame 6.
outward_frames = {3, 4, 5}
for index in range(12):
    frame = hair_sway(base, index in outward_frames)
    frame.save(OUT / f"frame-{index:03d}.png")

print(json.dumps({"source": str(SOURCE), "output": str(OUT), "frames": 12, "durationMs": 3000, "secondaryMask": "trailing hair x=86..87, y=113..118", "outwardFrames": sorted(outward_frames)}, indent=2))
