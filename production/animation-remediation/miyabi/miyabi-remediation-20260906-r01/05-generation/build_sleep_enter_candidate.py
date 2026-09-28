from pathlib import Path
import shutil


ROOT = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game")
RUN = ROOT / "production/animation-remediation/miyabi/miyabi-remediation-20260906-r01"
STABLE = ROOT / "assets/runtime/taskbar-pet/clip-packs/miyabi/v1/clips/sleep_enter/right/frames"
REST = RUN / "05-generation/sleep-enter-frame-004-candidate.png"
BREAKDOWN = RUN / "05-generation/sleep-enter-frame-005-candidate.png"
OUT = ROOT / "assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/sleep_enter"

if OUT.exists():
    for frame in OUT.glob("frame-*.png"):
        frame.unlink()
OUT.mkdir(parents=True, exist_ok=True)

# Keep only the readable early weight-transfer keys. The old stable frame-005
# is a broken crop with a detached weapon, so it is not copied into the
# candidate. Use one bounded generated breakdown, then hold the compact rest
# key; no crossfade or filtering is used.
for index in range(5):
    shutil.copy2(STABLE / f"frame-{index:03d}.png", OUT / f"frame-{index:03d}.png")
shutil.copy2(BREAKDOWN, OUT / "frame-005.png")
for index in range(6, 10):
    shutil.copy2(REST, OUT / f"frame-{index:03d}.png")
print({"output": str(OUT), "frames": 10, "durationMs": 1200, "stableFrames": "000..004", "generatedBreakdown": "005", "restKeyFrames": "006..009"})
