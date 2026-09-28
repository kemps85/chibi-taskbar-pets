from PIL import Image,ImageDraw
from pathlib import Path
ROOT=Path(r"C:\Users\ASUS\Documents\ChatGPT\Game")
base=ROOT/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/sleep_enter/frame-006.png'
source=ROOT/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/sleep_enter/frame-004.png'
outdir=ROOT/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/03-motion/bridge-probe';outdir.mkdir(parents=True,exist_ok=True)
for name,dy in [('bridge_a',5),('bridge_b',8),('bridge_c',11)]:
 b=Image.open(base).convert('RGBA'); s=Image.open(source).convert('RGBA')
 # Preserve the rest weapon and grounded lower body. Replace only upper body/head/cape with the approved leaning key, shifted down.
 mask=Image.new('L',(160,144),0); d=ImageDraw.Draw(mask)
 d.polygon([(39,28),(78,22),(103,37),(111,63),(108,95),(99,108),(38,108),(30,84),(33,50)],fill=255)
 shifted=Image.new('RGBA',(160,144),(0,0,0,0)); shifted.alpha_composite(s,(0,dy))
 b.paste(shifted,(0,0),mask)
 b.save(outdir/(name+'.png'))
# contact
names=['bridge_a','bridge_b','bridge_c']; imgs=[Image.open(outdir/(n+'.png')).convert('RGBA').resize((640,576),Image.Resampling.NEAREST) for n in names]; out=Image.new('RGBA',(640*3,612),(220,220,220,255)); d=ImageDraw.Draw(out)
for j,im in enumerate(imgs): out.alpha_composite(im,(j*640,28)); d.text((j*640+8,6),names[j],fill='magenta')
out.save(outdir/'contact-4x.png')
