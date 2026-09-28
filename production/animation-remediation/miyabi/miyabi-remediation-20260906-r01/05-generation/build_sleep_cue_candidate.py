from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
source=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png'
out=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/sleep_cue'
frames=out/'right/frames'; frames.mkdir(parents=True,exist_ok=True)
base=Image.open(source).convert('RGBA')
skin=(254,248,239,255); dark=(4,4,6,255)
# Regions are deliberately narrow and derived from the visible eye pixels in the identity master.
def drowsy_variant(level):
    im=base.copy(); d=ImageDraw.Draw(im)
    if level<=0: return im
    # Clear only the colored eye pixels, then draw a small controlled upper lid.
    if level>=2:
        d.rectangle((46,55,50,58),fill=skin)
        d.rectangle((58,55,63,59),fill=skin)
    else:
        d.rectangle((46,56,49,58),fill=skin)
        d.rectangle((59,57,62,59),fill=skin)
    if level==1:
        d.line((46,55,49,55),fill=dark,width=1)
        d.line((59,56,62,56),fill=dark,width=1)
    else:
        d.line((46,56,50,56),fill=dark,width=1)
        d.line((59,57,63,57),fill=dark,width=1)
        d.point((48,57),fill=dark); d.point((61,58),fill=dark)
        # One-pixel tip reduction is the bounded ear-softening cue; no body scale/rotation.
        for xy in [(67,5),(66,6),(43,7)]:
            d.point(xy,fill=(0,0,0,0))
    return im
levels=[0,0,1,2,2,1,0,0]
for i,level in enumerate(levels):
    canvas=Image.new('RGBA',(160,144),(0,0,0,0)); canvas.alpha_composite(drowsy_variant(level),(4,19)); canvas.save(frames/f'frame-{i:03d}.png')
try: font=ImageFont.truetype('segoeui.ttf',18)
except OSError: font=ImageFont.load_default()
sheet=Image.new('RGB',(160*4*2,144*4),(246,246,246)); d=ImageDraw.Draw(sheet)
for i in range(8):
    im=Image.open(frames/f'frame-{i:03d}.png').resize((640,576),Image.Resampling.NEAREST); bg=Image.new('RGBA',(640,576),(246,246,246,255)); bg.alpha_composite(im); sheet.paste(bg.convert('RGB'),((i%4)*640,(i//4)*576)); d.text(((i%4)*640+8,(i//4)*576+8),f'frame-{i:03d} / {i*150}ms / lid={levels[i]}',fill=(0,0,0),font=font)
sheet.save(out/'contact-light-4x.png')
# checker
check=Image.new('RGB',(640*4,576*2),(235,235,235)); cd=ImageDraw.Draw(check)
for y in range(0,576*2,32):
  for x in range(0,640*4,32):
    if ((x//32)+(y//32))%2: cd.rectangle((x,y,x+31,y+31),fill=(200,200,200))
for i in range(8):
    im=Image.open(frames/f'frame-{i:03d}.png').resize((640,576),Image.Resampling.NEAREST); bg=Image.new('RGBA',(640,576),(0,0,0,0)); bg.alpha_composite(im); check.paste(bg,(i%4*640,i//4*576),bg)
check.save(out/'contact-checker-4x.png')
print(out)
