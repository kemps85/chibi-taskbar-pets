from pathlib import Path
from PIL import Image,ImageDraw
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game'); cand=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/walk'; frames=cand/'right/frames'
for label,ids in {'contact-pass':[0,2,4],'seam':[6,7,0]}.items():
 out=Image.new('RGBA',(80*8*3,55*8),(246,246,246,255)); d=ImageDraw.Draw(out)
 for j,i in enumerate(ids):
  im=Image.open(frames/f'frame-{i:03d}.png').crop((34,96,86,144)).resize((52*8,48*8),Image.Resampling.NEAREST); bg=Image.new('RGB',im.size,(246,246,246)); bg.paste(im.convert('RGB'),(0,0),im); out.paste(bg,(j*52*8,0)); d.text((j*52*8+8,8),f'{i:03d}',fill=(0,0,0))
 out.convert('RGB').save(cand/f'legs-{label}-8x.png')
print(cand)
