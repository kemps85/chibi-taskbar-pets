from PIL import Image
from pathlib import Path
RUN=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01')
source=RUN/'05-generation/raw/sleep-enter-frame-004-breakdown-imagegen.png'; out=RUN/'05-generation/sleep-enter-frame-004-breakdown-candidate.png'
im=Image.open(source).convert('RGBA'); w,h=im.size; pix=im.load(); seen=set(); stack=[]
for x in range(w): stack.extend([(x,0),(x,h-1)])
for y in range(h): stack.extend([(0,y),(w-1,y)])
while stack:
 x,y=stack.pop()
 if (x,y) in seen: continue
 r,g,b,a=pix[x,y]
 if min(r,g,b)<210 or max(r,g,b)-min(r,g,b)>55: continue
 seen.add((x,y))
 for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1),(x-1,y-1),(x+1,y-1),(x-1,y+1),(x+1,y+1)):
  if 0<=nx<w and 0<=ny<h and (nx,ny) not in seen: stack.append((nx,ny))
for x,y in seen:
 r,g,b,a=pix[x,y]; pix[x,y]=(r,g,b,0)
bbox=im.getchannel('A').getbbox()
if bbox is None: raise RuntimeError('no authored pixels after border cleanup')
im=im.crop(bbox); scale=min(124/im.width,112/im.height); im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.NEAREST)
canvas=Image.new('RGBA',(160,144),(0,0,0,0)); pos=(64-im.width//2,143-im.height); canvas.alpha_composite(im,pos); canvas.save(out)
print({'bbox':bbox,'resized':im.size,'placed':pos,'output':str(out),'removed_border_pixels':len(seen)})
