from __future__ import annotations
import csv, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

repo = Path(__file__).resolve().parents[5]
pack = repo / 'assets' / 'runtime' / 'taskbar-pet' / 'clip-packs' / 'miyabi' / 'v1'
out = Path(__file__).resolve().parent
manifest = json.loads((pack / 'manifest.json').read_text(encoding='utf-8'))
font = ImageFont.load_default()

def checker(w, h, size=8):
    im = Image.new('RGBA', (w,h), (215,215,215,255)); d=ImageDraw.Draw(im)
    for y in range(0,h,size):
        for x in range(0,w,size):
            if ((x//size)+(y//size))%2: d.rectangle((x,y,x+size-1,y+size-1), fill=(245,245,245,255))
    return im

def composite(src, bg):
    b = bg.copy().convert('RGBA')
    b.alpha_composite(src.convert('RGBA'))
    return b.convert('RGB')

rows=[]
for clip, spec in manifest['clips'].items():
    fdir = pack / spec['frames']
    frames = sorted(fdir.glob('frame-*.png'))
    actual = len(frames)
    durations = spec['frame_durations_ms']
    accum=0
    first=None; last=None
    for i,p in enumerate(frames):
        with Image.open(p) as im0:
            im=im0.convert('RGBA')
            alpha=im.getchannel('A')
            bbox=alpha.getbbox()
            extrema=alpha.getextrema()
            data=list(alpha.getdata())
            partial=sum(1 for a in data if 0<a<255)
            opaque=sum(1 for a in data if a==255)
            border=max(alpha.getpixel((x,y)) for x,y in [(x,0) for x in range(im.width)]+[(x,im.height-1) for x in range(im.width)]+[(0,y) for y in range(im.height)]+[(im.width-1,y) for y in range(im.height)])
            if i==0: first=bbox
            if i==actual-1: last=bbox
            rows.append({'clip':clip,'frame_id':p.stem,'path':str(p.resolve()),'actual_index':i,'duration_ms':durations[i] if i<len(durations) else None,'timestamp_ms':accum,'canvas_w':im.width,'canvas_h':im.height,'alpha_bbox':list(bbox) if bbox else None,'alpha_pixels':sum(1 for a in data if a),'opaque_pixels':opaque,'partial_alpha_pixels':partial,'alpha_min':extrema[0],'alpha_max':extrema[1],'border_max_alpha':border})
        accum += durations[i] if i<len(durations) else 0
    # Three-background contact sheet; nearest-neighbor 4x
    scale=4; tile_w=160*scale; tile_h=144*scale+22
    for bg_name, bg_color in [('light',(248,248,248,255)),('dark',(28,32,42,255)),('checker',None)]:
        cols=4; rows_n=(actual+cols-1)//cols
        sheet=Image.new('RGB',(cols*tile_w,rows_n*tile_h),(40,40,40))
        for i,p in enumerate(frames):
            with Image.open(p) as im0: src=im0.convert('RGBA')
            bg = checker(160,144) if bg_color is None else Image.new('RGBA',(160,144),bg_color)
            tile=composite(src,bg).resize((tile_w,tile_h-22),Image.Resampling.NEAREST)
            x=(i%cols)*tile_w; y=(i//cols)*tile_h
            sheet.paste(tile,(x,y)); d=ImageDraw.Draw(sheet); d.text((x+4,y+tile_h-19),f'{i:03d}  t={sum(durations[:i]) if i<len(durations) else "?"}ms',font=font,fill='white')
        sheet.save(out/f'contact-{clip}-{bg_name}-4x.png')
    # one-pixel strip on checker at 1x, then 4x
    strip=Image.new('RGBA',(actual*160,144),(0,0,0,0))
    for i,p in enumerate(frames):
        with Image.open(p) as im0: strip.alpha_composite(im0.convert('RGBA'),(i*160,0))
    strip.convert('RGB').save(out/f'strip-{clip}-1x.png')
    strip.resize((strip.width*4,strip.height*4),Image.Resampling.NEAREST).convert('RGB').save(out/f'strip-{clip}-4x.png')

with (out/'frame-metrics.json').open('w',encoding='utf-8') as f: json.dump(rows,f,ensure_ascii=False,indent=2)
with (out/'inventory.csv').open('w',encoding='utf-8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0].keys())); writer.writeheader(); writer.writerows(rows)
summary=[]
for clip,spec in manifest['clips'].items():
    cr=[r for r in rows if r['clip']==clip]
    summary.append({'clip':clip,'frames_expected':spec['frame_count'],'frames_actual':len(cr),'timing_ms':sum(spec['frame_durations_ms']),'loop_policy':spec['loop_policy'],'canvas':f"{manifest['canvas']['width']}x{manifest['canvas']['height']}",'start_frame':cr[0]['frame_id'],'end_frame':cr[-1]['frame_id'],'start_bbox':cr[0]['alpha_bbox'],'end_bbox':cr[-1]['alpha_bbox'],'source':str(pack.resolve())})
with (out/'clip-inventory.json').open('w',encoding='utf-8') as f: json.dump(summary,f,ensure_ascii=False,indent=2)
print('generated', len(rows), 'frame rows in', out)
for s in summary: print(s['clip'], s['frames_actual'], s['timing_ms'], s['loop_policy'], s['start_frame'], s['end_frame'])

