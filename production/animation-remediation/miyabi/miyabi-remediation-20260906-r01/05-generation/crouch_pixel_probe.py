from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(r"C:\Users\ASUS\Documents\ChatGPT\Game")
C=ROOT/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01'
OUT=ROOT/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/05-generation/crouch-probe';OUT.mkdir(parents=True,exist_ok=True)
src=Image.open(C/'sleep_enter/frame-004.png').convert('RGBA')
for name,scale,dx,dy in [('crouch_a',.88,-2,0),('crouch_b',.78,-4,3),('crouch_c',.70,-6,6)]:
 im=src.copy(); lower=src.crop((0,76,128,144)); lower=lower.resize((128,round(68*scale)),Image.Resampling.NEAREST); mask=Image.new('L',(160,144),0); ImageDraw.Draw(mask).rectangle((0,76,127,143),fill=255); im.paste((0,0,0,0),(0,76,128,144),mask.crop((0,76,128,144))); im.alpha_composite(lower,(dx,76+dy)); im.save(OUT/(name+'.png'))
# current sequence contact
items=[('frame3',Image.open(C/'sleep_enter/frame-003.png').convert('RGBA')),('crouch_a',Image.open(OUT/'crouch_a.png').convert('RGBA')),('crouch_b',Image.open(OUT/'crouch_b.png').convert('RGBA')),('crouch_c',Image.open(OUT/'crouch_c.png').convert('RGBA')),('rest',Image.open(C/'sleep_enter/frame-006.png').convert('RGBA'))]
out=Image.new('RGBA',(640*5,612),(226,226,226,255));d=ImageDraw.Draw(out)
for i,(label,im) in enumerate(items):out.alpha_composite(im.resize((640,576),Image.Resampling.NEAREST),(i*640,28));d.text((i*640+8,6),label,fill='magenta')
out.save(OUT/'contact-4x.png')
