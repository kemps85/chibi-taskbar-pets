from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
p=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\04-frame-specs\pose-guides\sleep-enter-frame-005-guide.png')
W,H,S=160,144,4
im=Image.new('RGBA',(W*S,H*S),(248,248,248,255)); d=ImageDraw.Draw(im)
for x in range(0,W+1,8): d.line((x*S,0,x*S,H*S),fill=(220,220,220,255),width=1)
for y in range(0,H+1,8): d.line((0,y*S,W*S,y*S),fill=(220,220,220,255),width=1)
# frame-005 is the bounded halfway-to-rest breakdown: lower pelvis, fold both knees toward feet-left, keep head-right, weapon protected.
d.line((0,143*S,W*S,143*S),fill=(190,0,0,255),width=2)
pts={'head':(72,78),'shoulders':(68,97),'elbow':(62,113),'wrist':(56,121),'pelvis':(66,126),'knees':(43,137),'heels':(32,142),'toes':(18,142),'weapon_hilt':(91,128),'weapon_tip':(126,135)}
colors={'head':(180,0,180,255),'shoulders':(0,140,140,255),'elbow':(255,128,0,255),'wrist':(255,128,0,255),'pelvis':(0,130,80,255),'knees':(30,60,220,255),'heels':(30,60,220,255),'toes':(30,60,220,255),'weapon_hilt':(255,128,0,255),'weapon_tip':(255,128,0,255)}
for a,b in [('head','shoulders'),('shoulders','elbow'),('elbow','wrist'),('shoulders','pelvis'),('pelvis','knees'),('knees','heels'),('heels','toes'),('weapon_hilt','weapon_tip')]:
    d.line((pts[a][0]*S,pts[a][1]*S,pts[b][0]*S,pts[b][1]*S),fill=colors[a],width=2*S)
for k,(x,y) in pts.items():
    c=colors[k]; d.ellipse(((x*S-4*S,y*S-4*S),(x*S+4*S,y*S+4*S)),outline=c,width=2*S)
    d.text((x*S+5*S,y*S-5*S),k,fill=c)
d.text((4,4),'SLEEP_ENTER FRAME-005 / MID-LOWER BREAKDOWN',fill=(180,0,0,255))
d.text((4,20),'feet-left/head-right; pelvis down; knees fold; weapon stays attached; no rotate/crop/squash',fill=(0,0,0,255))
im.save(p)
print(p)
