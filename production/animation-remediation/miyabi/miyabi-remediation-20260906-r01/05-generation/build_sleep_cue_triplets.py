from pathlib import Path
from PIL import Image,ImageDraw
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
cand=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/sleep_cue'; frames=cand/'right/frames'
for label,ids in {'approach':[0,2,4],'recover':[3,5,7]}.items():
 out=Image.new('RGB',(640*3,576),(246,246,246)); d=ImageDraw.Draw(out)
 for j,i in enumerate(ids):
  im=Image.open(frames/f'frame-{i:03d}.png').convert('RGBA').resize((640,576),Image.Resampling.NEAREST); bg=Image.new('RGBA',(640,576),(246,246,246,255)); bg.alpha_composite(im); out.paste(bg.convert('RGB'),(j*640,0)); d.text((j*640+8,8),f'{i:03d} / {i*150}ms',fill=(0,0,0))
 out.save(cand/f'triplet-{label}-4x.png')
print(cand)
