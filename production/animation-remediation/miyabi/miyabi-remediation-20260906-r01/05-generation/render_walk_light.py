from pathlib import Path
from PIL import Image
cand=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game\assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/walk'); src=cand/'right/frames'; out=cand/'preview-light-sequence'
for i in range(8):
 im=Image.open(src/f'frame-{i:03d}.png').convert('RGBA'); bg=Image.new('RGBA',(160,144),(246,246,246,255)); bg.alpha_composite(im); bg.convert('RGB').save(out/f'frame-{i:03d}.png')
