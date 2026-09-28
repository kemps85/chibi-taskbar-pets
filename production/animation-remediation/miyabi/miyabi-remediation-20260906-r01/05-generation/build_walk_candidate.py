from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game'); source=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png'; out=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/walk'; frames=out/'right/frames'; frames.mkdir(parents=True,exist_ok=True)
base=Image.open(source).convert('RGBA')
left_box=(42,112,55,125); right_box=(57,112,73,125)
left_crop=base.crop(left_box); right_crop=base.crop(right_box)
# Each tuple is (left x,y, right x,y); only the lower leg/boot regions move.
poses=[(40,112,60,112),(41,112,59,112),(44,111,57,112),(45,111,56,110),(45,112,55,112),(44,111,57,112),(41,112,59,112),(40,111,61,112)]
for i,(lx,ly,rx,ry) in enumerate(poses):
    im=base.copy(); d=ImageDraw.Draw(im)
    d.rectangle(left_box,fill=(0,0,0,0)); d.rectangle(right_box,fill=(0,0,0,0))
    im.alpha_composite(left_crop,(lx,ly)); im.alpha_composite(right_crop,(rx,ry))
    canvas=Image.new('RGBA',(160,144),(0,0,0,0)); canvas.alpha_composite(im,(4,19)); canvas.save(frames/f'frame-{i:03d}.png')
try: font=ImageFont.truetype('segoeui.ttf',18)
except OSError: font=ImageFont.load_default()
sheet=Image.new('RGB',(640*4,576*2),(246,246,246)); d=ImageDraw.Draw(sheet)
for i in range(8):
    im=Image.open(frames/f'frame-{i:03d}.png').resize((640,576),Image.Resampling.NEAREST); bg=Image.new('RGBA',(640,576),(246,246,246,255)); bg.alpha_composite(im); sheet.paste(bg.convert('RGB'),((i%4)*640,(i//4)*576)); d.text(((i%4)*640+8,(i//4)*576+8),f'frame-{i:03d} / {i*100}ms',fill=(0,0,0),font=font)
sheet.save(out/'contact-light-4x.png')
check=Image.new('RGB',(640*4,576*2),(235,235,235)); cd=ImageDraw.Draw(check)
for y in range(0,1152,32):
 for x in range(0,2560,32):
  if ((x//32)+(y//32))%2: cd.rectangle((x,y,x+31,y+31),fill=(200,200,200))
for i in range(8):
 im=Image.open(frames/f'frame-{i:03d}.png').resize((640,576),Image.Resampling.NEAREST); check.paste(im,(i%4*640,i//4*576),im)
check.save(out/'contact-checker-4x.png')
print(out)
