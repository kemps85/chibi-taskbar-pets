import json
from pathlib import Path
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
run=root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01'
files=[run/'05-generation/imagegen-sleep-enter-wake-provenance.json',run/'05-generation/imagegen-eat-key-provenance.json',run/'05-generation/imagegen-sleep-enter-frame-004-breakdown-provenance.json',run/'06-continuity/candidate-review-index.json',root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/full-pack/clip-packs/miyabi/v1/manifest.json']
for p in files:
 json.loads(p.read_text(encoding='utf-8')); print('JSON PASS',p)
for p in [run/'05-generation/imagegen-sleep-enter-wake-provenance.json',run/'05-generation/imagegen-eat-key-provenance.json']:
 t=p.read_text(encoding='utf-8'); print('placeholder?', 'REPLACE_' in t, p.name)
