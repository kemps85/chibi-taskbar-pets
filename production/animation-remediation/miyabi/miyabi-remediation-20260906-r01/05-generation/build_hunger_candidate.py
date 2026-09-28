from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
run = root / 'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01'
identity_path = root / 'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png'
stable_frames = root / 'assets/runtime/taskbar-pet/clip-packs/miyabi/v1/clips/hunger_cue/right/frames'
out = root / 'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/hunger_cue'
frames_dir = out / 'right/frames'
frames_dir.mkdir(parents=True, exist_ok=True)
identity = Image.open(identity_path).convert('RGBA')
assert identity.size == (128, 128)

# Keep only the existing food-area pixels from each source frame. The identity
# body is the locked master; no new food, utensil, effect, scale, or rotation.
def make_frame(index: int) -> Image.Image:
    source = Image.open(stable_frames / f'frame-{index:03d}.png').convert('RGBA')
    canvas = Image.new('RGBA', (160, 144), (0, 0, 0, 0))
    canvas.alpha_composite(identity, (4, 19))
    dst = canvas.load(); src = source.load()
    for y in range(144):
        for x in range(110, 160):
            if src[x, y][3] > 0:
                dst[x, y] = src[x, y]
    return canvas

images=[]
for i in range(8):
    im=make_frame(i)
    path=frames_dir/f'frame-{i:03d}.png'
    im.save(path, optimize=True)
    images.append(im)

# Review contact sheets and strips, all nearest-neighbour.
def font():
    try: return ImageFont.truetype('segoeui.ttf', 16)
    except OSError: return ImageFont.load_default()
f=font()
def checker(size):
    im=Image.new('RGBA', size, (235,235,235,255)); d=ImageDraw.Draw(im)
    for y in range(0,size[1],16):
        for x in range(0,size[0],16):
            if ((x//16)+(y//16))%2: d.rectangle((x,y,x+15,y+15),fill=(200,200,200,255))
    return im

def sheet(path, bg, scale=4):
    tile=(160*scale,144*scale); result=Image.new('RGBA',(tile[0]*4,tile[1]*2),(0,0,0,0))
    for i,im in enumerate(images):
        slot=Image.new('RGBA',tile,(0,0,0,0)); slot.alpha_composite(bg.resize(tile,Image.Resampling.NEAREST)); slot.alpha_composite(im.resize(tile,Image.Resampling.NEAREST));
        d=ImageDraw.Draw(slot); d.rectangle((0,0,tile[0]-1,tile[1]-1),outline=(80,80,80,255)); d.text((6,6),f'{i:03d} / {i*150}ms',fill=(0,0,0,255),font=f)
        result.alpha_composite(slot,((i%4)*tile[0],(i//4)*tile[1]))
    result.convert('RGB').save(path)

sheet(out/'contact-light-4x.png', Image.new('RGBA',(160,144),(246,246,246,255)))
sheet(out/'contact-checker-4x.png', checker((160,144)))
strip=Image.new('RGBA',(160*8,144),(0,0,0,0))
for i,im in enumerate(images): strip.alpha_composite(im,(160*i,0))
strip.save(out/'contact-strip-1x.png')
images[0].save(out/'preview-1x.apng',save_all=True,append_images=images[1:],duration=150,loop=0,format='PNG')

metrics=[]; hashes=[]
for i in range(8):
    p=frames_dir/f'frame-{i:03d}.png'; im=Image.open(p).convert('RGBA'); a=im.getchannel('A'); vals=list(a.getdata()); bbox=a.getbbox();
    border=max([a.getpixel((x,0)) for x in range(160)]+[a.getpixel((x,143)) for x in range(160)]+[a.getpixel((0,y)) for y in range(144)]+[a.getpixel((159,y)) for y in range(144)])
    metrics.append({'frameId':p.stem,'bbox':list(bbox) if bbox else None,'partialAlphaPixels':sum(0<x<255 for x in vals),'maxBorderAlpha':border})
    hashes.append({'frameId':p.stem,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
manifest={'candidateId':'miyabi-remediation-20260906-r01-hunger-cue-v1','characterId':'miyabi','clip':'hunger_cue','status':'CANDIDATE_USER_APPROVAL_PENDING','canvas':{'width':160,'height':144},'authoredDirection':'right','mirror':'runtime-horizontal-exact','placementAnchor':[64,120],'groundLineY':143,'frameCount':8,'frameDurationMs':150,'totalDurationMs':1200,'loopPolicy':'once','frames':'hunger_cue/right/frames'}
qa={'candidateId':manifest['candidateId'],'status':manifest['status'],'frames':metrics,'unionBBox':[min(m['bbox'][0] for m in metrics),min(m['bbox'][1] for m in metrics),max(m['bbox'][2] for m in metrics),max(m['bbox'][3] for m in metrics)],'totalPartialAlphaPixels':sum(m['partialAlphaPixels'] for m in metrics),'maxBorderAlpha':max(m['maxBorderAlpha'] for m in metrics),'notes':['identity body is unchanged from master','food-area pixels are copied only from the existing stable hunger source x>=110','no new food, utensil, effect, scale, rotation, or body redraw','body gesture/eye direction remains a declared limitation pending choreography approval']}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
prov={'candidateId':manifest['candidateId'],'createdUtc':datetime.now(timezone.utc).isoformat(),'tool':'deterministic-Pillow-compositor','imagegen':{'used':False},'sourceIdentity':str(identity_path),'sourceIdentitySha256':hashlib.sha256(identity_path.read_bytes()).hexdigest(),'sourceFoodFrames':str(stable_frames),'operations':['place unchanged identity master at (4,19)','copy only existing hunger food-area pixels with x>=110 from each stable source frame','preserve original candidate timing 8x150ms','no scaling','no rotation','no palette-wide edit','no behavior or stable-pack modification'],'outputHashes':hashes,'approvalStatus':'PENDING'}
(out/'provenance.json').write_text(json.dumps(prov,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'out':str(out),'status':'PASS_TECHNICAL_CANDIDATE_PENDING_APPROVAL','frames':8,'partialAlpha':qa['totalPartialAlphaPixels'],'maxBorderAlpha':qa['maxBorderAlpha']},ensure_ascii=False))
