from PIL import Image,ImageDraw
from pathlib import Path
p=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\03-motion\native-rest-probe')
names=['brace','crouch_x_35','crouch_x_60','crouch_z_60','seated_x_75','seated_x_95','rest_seated']
cellw,cellh=320,288; out=Image.new('RGBA',(cellw*4,cellh*2),(226,226,226,255))
for i,n in enumerate(names):
 im=Image.open(p/f'{n}.png').convert('RGBA'); im.thumbnail((cellw,cellh),Image.Resampling.LANCZOS); x=(i%4)*cellw+(cellw-im.width)//2; y=(i//4)*cellh+(cellh-im.height)//2; out.alpha_composite(im,(x,y)); ImageDraw.Draw(out).text(((i%4)*cellw+4,(i//4)*cellh+4),n,fill=(190,0,120,255))
out.save(p/'contact-2x.png'); print(p/'contact-2x.png')
