"""Copy painted-legs walk frames into <char>/clips-out/walk and register them in clips-out/manifest.json."""
import json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
for c in sys.argv[1:]:
    src = ROOT / 'tmp/gait/painted-legs' / c
    out = ROOT / 'assets/generated/pixel-chibi/imagegen-v1' / c / 'clips-out'
    dst = out / 'walk'
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    frames = sorted(src.glob('frame-*.png'))
    for f in frames:
        shutil.copy(f, dst / f.name)
    mp = out / 'manifest.json'
    m = json.loads(mp.read_text(encoding='utf-8')) if mp.exists() else {'clips': {}}
    m['clips']['walk'] = {'frame_count': len(frames), 'frame_durations_ms': [100] * len(frames),
                          'loop_policy': 'loop', 'frames': 'walk/frame-{index:000}.png'}
    mp.write_text(json.dumps(m, indent=2) + '\n', encoding='utf-8')
    print(c, 'walk frames', len(frames))
