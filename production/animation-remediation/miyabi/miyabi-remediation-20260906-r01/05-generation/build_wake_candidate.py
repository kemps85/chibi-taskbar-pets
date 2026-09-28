from pathlib import Path
import shutil


ROOT = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game")
RUN = ROOT / "production/animation-remediation/miyabi/miyabi-remediation-20260906-r01"
STABLE = ROOT / "assets/runtime/taskbar-pet/clip-packs/miyabi/v1/clips/wake/right/frames"
REST = RUN / "05-generation/sleep-enter-frame-004-candidate.png"
MID = RUN / "05-generation/wake-frame-004-candidate.png"
OUT = ROOT / "assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/wake"

if OUT.exists():
    for frame in OUT.glob("frame-*.png"):
        frame.unlink()
OUT.mkdir(parents=True, exist_ok=True)

for index in range(2):
    shutil.copy2(REST, OUT / f"frame-{index:03d}.png")
shutil.copy2(MID, OUT / "frame-002.png")
for output_index, stable_index in ((3, 4), (4, 5), (5, 6), (6, 7), (7, 7)):
    shutil.copy2(STABLE / f"frame-{stable_index:03d}.png", OUT / f"frame-{output_index:03d}.png")
print({"output": str(OUT), "frames": 8, "durationMs": 800, "restFrames": "000..001", "generatedBreakdown": "002", "supportReleaseFrames": "003..004", "standRecoveryFrames": "005..007"})
