from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(r"C:\Users\ASUS\Documents\ChatGPT\Game")
CAND=ROOT/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01'
OUT=ROOT/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/05-generation/transition-repair/refined-probe';OUT.mkdir(parents=True,exist_ok=True)
src=Image.open(CAND/'sleep_enter/frame-004.png').convert('RGBA')

def make(base_path,dy,name):
 b=Image.open(base_path).convert('RGBA'); shifted=Image.new('RGBA',(160,144),(0,0,0,0));shifted.alpha_composite(src,(0,dy))
 mask=Image.new('L',(160,144),0);d=ImageDraw.Draw(mask)
 d.polygon([(49,24),(77,22),(101,36),(108,62),(105,92),(98,106),(53,106),(50,89),(52,69),(48,51)],fill=255)
 # keep the source left hand/weapon out of this bridge; base frame owns the weapon trajectory.
 b.paste(shifted,(0,0),mask);b.save(OUT/(name+'.png'));return b
items=[]
for name,dy in [('sleep_dy8',8),('sleep_dy11',11),('wake_dy12',12),('wake_dy16',16)]:
 base=CAND/'sleep_enter/frame-006.png' if name.startswith('sleep') else CAND/'wake/frame-002.png';items.append((name,make(base,dy,name)))
out=Image.new('RGBA',(640*4,612),(220,220,220,255));d=ImageDraw.Draw(out)
for i,(label,im) in enumerate(items):out.alpha_composite(im.resize((640,576),Image.Resampling.NEAREST),(i*640,28));d.text((i*640+8,6),label,fill='magenta')
out.save(OUT/'contact-4x.png')
