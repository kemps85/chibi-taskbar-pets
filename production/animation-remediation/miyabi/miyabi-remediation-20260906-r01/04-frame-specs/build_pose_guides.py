from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
out=root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/04-frame-specs/pose-guides'; out.mkdir(exist_ok=True)
source=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png'
body=Image.open(source).convert('RGBA')
try: font=ImageFont.truetype('segoeui.ttf',18)
except OSError: font=ImageFont.load_default()
def checker(w,h,cell=16):
    im=Image.new('RGB',(w,h),(228,228,228)); d=ImageDraw.Draw(im)
    for y in range(0,h,cell):
      for x in range(0,w,cell):
        if ((x//cell)+(y//cell))%2: d.rectangle((x,y,x+cell-1,y+cell-1),fill=(198,198,198))
    return im

def make(name,title,notes,marks):
    s=4; W,H=160*s,144*s; im=checker(W,H); d=ImageDraw.Draw(im)
    body4=body.resize((128*s,128*s),Image.Resampling.NEAREST); im.paste(body4,(4*s,19*s),body4)
    d.rectangle((0,0,W-1,H-1),outline=(30,90,160),width=3)
    d.line((0,143*s,W,143*s),fill=(180,60,60),width=3)
    d.text((8,8),title,font=font,fill=(20,40,90))
    d.text((8,34),notes,font=font,fill=(20,40,90))
    for x,y,tx,kind in marks:
      X,Y=x*s,y*s
      if kind=='point': d.ellipse((X-5,Y-5,X+5,Y+5),fill=(255,220,0),outline=(0,0,0),width=2)
      elif kind=='arrow': d.line((X-28,Y-28,X,Y),fill=(30,100,230),width=5); d.polygon([(X,Y),(X-14,Y-4),(X-4,Y-14)],fill=(30,100,230))
      d.text((X+8,Y-10),tx,font=font,fill=(20,40,90))
    im.save(out/name)
make('sleep-cue-frame-004-guide.png','CANDIDATE GUIDE — sleep_cue frame-004','Keep identity/weapon/feet fixed; restrained drowsy cue only.',[(66,51,'head/face fixed','point'),(54,40,'ear softens 1px','arrow'),(82,40,'ear softens 1px','arrow'),(67,72,'shoulder settle +1','arrow'),(64,143,'ground y=143','point')])
make('walk-frame-001-guide.png','CANDIDATE GUIDE — walk frame-001','Short deliberate contact pose; no detached accents; weapon follows hip.',[(53,122,'rear contact','point'),(72,122,'front lift','point'),(67,75,'hip path','arrow'),(97,95,'cape delay','arrow'),(64,143,'ground y=143','point')])
print(out)
