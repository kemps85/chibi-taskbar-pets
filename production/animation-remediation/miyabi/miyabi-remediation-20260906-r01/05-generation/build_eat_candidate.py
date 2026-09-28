from pathlib import Path

from PIL import Image


ROOT = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game")
RUN = ROOT / "production/animation-remediation/miyabi/miyabi-remediation-20260906-r01"
OUT = ROOT / "assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/eat"
IDENTITY = ROOT / "assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png"
PLATE = ROOT / "assets/runtime/taskbar-pet/clip-packs/miyabi/v1/clips/eat/right/frames/frame-000.png"
KEYS = {
    "approach": RUN / "05-generation/eat-frame-003-body-plate-candidate.png",
    "bite": RUN / "05-generation/eat-frame-006-body-plate-candidate.png",
    "recovery": RUN / "05-generation/eat-frame-009-body-plate-candidate.png",
}

if OUT.exists():
    for frame in OUT.glob("frame-*.png"):
        frame.unlink()
OUT.mkdir(parents=True, exist_ok=True)

base = Image.new("RGBA", (160, 144), (0, 0, 0, 0))
base.alpha_composite(Image.open(IDENTITY).convert("RGBA"), (4, 19))
base.alpha_composite(Image.open(PLATE).convert("RGBA"), (0, 0))
approach = Image.open(KEYS["approach"]).convert("RGBA")
bite = Image.open(KEYS["bite"]).convert("RGBA")
recovery = Image.open(KEYS["recovery"]).convert("RGBA")

# Existing 12 x 160 ms contract. Key poses are held deliberately; no crossfade
# or filtering is used to hide a transition. This remains a candidate pending
# visual continuity review.
sequence = [base, base, approach, approach, bite, bite, bite, bite, recovery, recovery, recovery, base]
for index, frame in enumerate(sequence):
    frame.save(OUT / f"frame-{index:03d}.png")
print({"output": str(OUT), "frames": len(sequence), "durationMs": len(sequence) * 160, "mapping": ["base", "base", "approach", "approach", "bite", "bite", "bite", "bite", "recovery", "recovery", "recovery", "base"]})
