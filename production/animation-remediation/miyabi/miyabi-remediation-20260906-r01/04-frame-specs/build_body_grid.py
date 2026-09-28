from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game'); src=Image.open(root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png').convert('RGBA')
# show source with coordinate ticks around lower body, enlarged nearest
s=8; im=src.crop((25,85,85,128)).resize((60*s,43*s),Image.Resampling.NEAREST); d=ImageDraw.Draw(im)
for x in range(0,61,5): d.line((x*s,0,x*s,43*s),fill=(80,130,200),width=1); d.text((x*s+2,2),str(25+x),fill=(20,50,120))
for y in range(0,44,5): d.line((0,y*s,60*s,y*s),fill=(80,130,200),width=1); d.text((2,y*s+2),str(85+y),fill=(20,50,120))
im.save(root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/04-frame-specs/pose-guides/body-lower-grid.png')
print('saved')
