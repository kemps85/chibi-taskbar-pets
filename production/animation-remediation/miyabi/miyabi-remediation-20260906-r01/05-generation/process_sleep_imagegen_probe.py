from PIL import Image
from pathlib import Path
p=Path(r'C:\Users\ASUS\.codex\generated_images\01a0733e-2630-7bf1-97dc-8c0f2a76683d\exec-470d420a-d119-4616-b8a3-8e6eab8edad5.png')
im=Image.open(p).convert('RGBA'); w,h=im.size; pix=im.load(); seen=set(); stack=[]
for x in range(w): stack += [(x,0),(x,h-1)]
for y in range(h): stack += [(0,y),(w-1,y)]
while stack:
 x,y=stack.pop()
 if (x,y) in seen: continue
 r,g,b,a=pix[x,y]
 if min(r,g,b)<210 or max(r,g,b)-min(r,g,b)>55: continue
 seen.add((x,y))
 for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1),(x-1,y-1),(x+1,y-1),(x-1,y+1),(x+1,y+1)):
  if 0<=nx<w and 0<=ny<h and (nx,ny) not in seen: stack.append((nx,ny))
for x,y in seen: pix[x,y]=(pix[x,y][0],pix[x,y][1],pix[x,y][2],0)
bbox=im.getchannel('A').getbbox(); im=im.crop(bbox)
scale=min(124/im.width,112/im.height); size=(round(im.width*scale),round(im.height*scale)); im=im.resize(size,Image.Resampling.NEAREST)
canvas=Image.new('RGBA',(160,144),(0,0,0,0)); x=64-im.width//2; y=143-im.height; canvas.alpha_composite(im,(x,y))
out=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\05-generation\raw-sleep-rest-frame-000-candidate.png'); canvas.save(out); print('bbox',bbox,'resized',im.size,'placed',(x,y),out)
