"""Build the README showcase GIFs from the published runtime clip packs.

    python scripts/build_readme_media.py

Writes docs/media/lineup-walk.gif (every character walking) and docs/media/signature-<char>.gif.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "assets/runtime/taskbar-pet/clip-packs"
OUT = ROOT / "docs/media"
LINEUP = ["miyabi", "firefly", "evanescia", "robin", "remielle-dan",
          "ye-shunguang", "ye-shunguang-white", "ye-shunguang-red", "ye-shunguang-red-white"]
SIGNATURES = {"miyabi": None, "firefly": (0, 70), "evanescia": None, "robin": None,
              "remielle-dan": None, "ye-shunguang-red": None}
KEY = (255, 0, 255)


def clip(character: str, clip_id: str) -> tuple[list[Image.Image], list[int], int]:
    manifest = json.loads((PACKS / character / "v2/manifest.json").read_text(encoding="utf-8"))
    if clip_id == "signature":
        clip_id = manifest["signature"]["clip"]
    meta = manifest["clips"][clip_id]
    frames = [Image.open(PACKS / character / "v2" / meta["frames"] / f"frame-{i:03d}.png").convert("RGBA")
              for i in range(meta["frame_count"])]
    return frames, meta["frame_durations_ms"], meta["right_anchor"]["y"]


def to_gif_frame(img: Image.Image) -> Image.Image:
    """Quantise the opaque pixels to 255 colours and reserve index 255 for transparency.

    Transparency is decided from alpha, never by colour, so pink/violet art cannot be merged into it.
    """
    alpha = np.asarray(img.split()[3]) > 127
    rgb = np.asarray(img.convert("RGB")).copy()
    if alpha.any():
        rgb[~alpha] = rgb[alpha][0]           # fill the background with an existing art colour
    pal = Image.fromarray(rgb).quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    idx = np.asarray(pal).copy()
    idx[~alpha] = 255
    out = Image.fromarray(idx, "P")
    palette = (pal.getpalette() or [])[:255 * 3]
    palette += [0, 0, 0] * (255 - len(palette) // 3) + list(KEY)
    out.putpalette(palette)
    out.info["transparency"] = 255
    return out


def save_gif(frames: list[Image.Image], durations: list[int], path: Path) -> None:
    gif = [to_gif_frame(f) for f in frames]
    gif[0].save(path, save_all=True, append_images=gif[1:], duration=durations, loop=0,
                disposal=2, transparency=255, optimize=False)
    print(path.relative_to(ROOT), f"{path.stat().st_size // 1024} KB")


def lineup(scale: int = 2, per_row: int = 5) -> None:
    walks = {c: clip(c, "walk") for c in LINEUP}
    # crop every canvas to the shared vertical band that holds the characters, feet on one line
    top, bottom = 22, 144
    cell_w, cell_h = 116, bottom - top
    rows = (len(LINEUP) + per_row - 1) // per_row
    n = 16
    frames = []
    for i in range(n):
        sheet = Image.new("RGBA", (cell_w * per_row * scale, cell_h * rows * scale), (0, 0, 0, 0))
        for k, c in enumerate(LINEUP):
            fr, _, anchor_y = walks[c]
            dy = 142 - anchor_y                       # Firefly stands on row 130: drop her onto the shared line
            cell = Image.new("RGBA", (160, 144), (0, 0, 0, 0))
            cell.alpha_composite(fr[i % len(fr)], (0, dy))
            cell = cell.crop((18, top, 18 + cell_w, bottom)).resize((cell_w * scale, cell_h * scale), Image.NEAREST)
            sheet.alpha_composite(cell, ((k % per_row) * cell_w * scale, (k // per_row) * cell_h * scale))
        frames.append(sheet)
    save_gif(frames, [60] * n, OUT / "lineup-walk.gif")


def signatures(scale: int = 2) -> None:
    for c, window in SIGNATURES.items():
        frames, durations, _ = clip(c, "signature")
        if window:
            frames, durations = frames[window[0]:window[1]], durations[window[0]:window[1]]
        big = [f.resize((160 * scale, 144 * scale), Image.NEAREST) for f in frames]
        save_gif(big, durations, OUT / f"signature-{c}.gif")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    lineup()
    signatures()
