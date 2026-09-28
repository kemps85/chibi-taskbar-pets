import json
from pathlib import Path
from PIL import Image, ImageDraw
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
cand=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/spirit_tail'
frames=cand/'right/frames'
ims=[Image.open(frames/f'frame-{i:03d}.png').convert('RGBA') for i in range(32)]
ims[0].save(cand/'preview-1x.apng',save_all=True,append_images=ims[1:],duration=90,loop=0,format='PNG')
light=cand/'preview-light-sequence'; light.mkdir(exist_ok=True)
for i,im in enumerate(ims):
    bg=Image.new('RGBA',(160,144),(246,246,246,255)); bg.alpha_composite(im); bg.convert('RGB').save(light/f'frame-{i:03d}.png')
triplets={'enter-breakdown':[11,12,13],'loop-seam':[23,24,25],'exit-breakdown':[29,30,31],'exit-to-enter':[30,31,0]}
for label,ids in triplets.items():
    out=Image.new('RGB',(160*4*3,144*4),(246,246,246)); d=ImageDraw.Draw(out)
    for j,i in enumerate(ids):
        tile=Image.new('RGBA',(160*4,144*4),(246,246,246,255)); tile.alpha_composite(ims[i].resize((640,576),Image.Resampling.NEAREST)); out.paste(tile.convert('RGB'),(j*640,0)); d.text((j*640+8,8),f'{i:03d} / {i*90}ms',fill=(0,0,0))
    out.save(cand/f'triplet-{label}-4x.png')
rows=[]
for i,im in enumerate(ims):
    a=im.getchannel('A'); vals=list(a.getdata()); rows.append({'frame':i,'nonzero':sum(x>0 for x in vals),'partial':sum(0<x<255 for x in vals),'sumAlpha':sum(vals)})
(cand/'alpha-timeline.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
print(cand/'preview-1x.apng')
print(cand/'triplet-exit-to-enter-4x.png')
