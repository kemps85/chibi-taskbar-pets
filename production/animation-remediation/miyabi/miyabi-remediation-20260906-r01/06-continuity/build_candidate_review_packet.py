from pathlib import Path
from PIL import Image, ImageDraw
import hashlib, json

ROOT=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
RUN=ROOT/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01'
PACK=ROOT/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/full-pack/clip-packs/miyabi/v1'
OUT=RUN/'06-continuity'
PREV=PACK/'previews'
PREV.mkdir(parents=True,exist_ok=True)
manifest=json.loads((PACK/'manifest.json').read_text(encoding='utf-8'))
clips=manifest['required_clips']

def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def frame_paths(clip):
    c=manifest['clips'][clip]
    d=PACK/c['frames']
    return [d/f'frame-{i:03d}.png' for i in range(c['frame_count'])]

index={'status':'CANDIDATE_USER_APPROVAL_PENDING','pack':str(PACK),'clips':{}}
for clip in clips:
    paths=frame_paths(clip)
    frames=[Image.open(p).convert('RGBA') for p in paths]
    durations=manifest['clips'][clip]['frame_durations_ms']
    apng=PREV/f'{clip}-preview-1x.apng'
    frames[0].save(apng,save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2)
    index['clips'][clip]={
        'frame_count':len(frames),
        'durations_ms':durations,
        'total_duration_ms':sum(durations),
        'preview_1x':str(apng),
        'preview_sha256':sha(apng),
        'frames_sha256':[sha(p) for p in paths],
    }

# Representative key contact: first, midpoint, last, at authored pixel density enlarged nearest.
cell_w,cell_h=160,160
scale=4
bg=(226,226,226,255)
rows=[]
for clip in clips:
    paths=frame_paths(clip)
    picks=sorted(set([0,len(paths)//2,len(paths)-1]))
    row=[]
    for i in picks:
        im=Image.open(paths[i]).convert('RGBA')
        cell=Image.new('RGBA',(cell_w,cell_h),bg)
        cell.alpha_composite(im,(0,0))
        d=ImageDraw.Draw(cell)
        d.rectangle((0,0,cell_w-1,10),fill=(226,226,226,255))
        d.text((2,1),f'{clip} frame-{i:03d}',fill=(180,0,120,255))
        row.append(cell.resize((cell_w*scale,cell_h*scale),Image.Resampling.NEAREST))
    rows.append(row)
canvas=Image.new('RGBA',(cell_w*scale*3,cell_h*scale*len(rows)),(226,226,226,255))
for r,row in enumerate(rows):
    for c,cell in enumerate(row): canvas.alpha_composite(cell,(c*cell_w*scale,r*cell_h*scale))
contact=OUT/'full-candidate-key-contact-4x.png'
canvas.save(contact)
index['key_contact_4x']=str(contact)
index['key_contact_sha256']=sha(contact)

# Current sleep-loop triplet after source switch.
def make_triplet(clip, indices, name):
    imgs=[]
    for i in indices:
        im=Image.open(frame_paths(clip)[i]).convert('RGBA')
        cell=Image.new('RGBA',(160,160),bg); cell.alpha_composite(im,(0,0))
        ImageDraw.Draw(cell).text((2,1),f'{clip} frame-{i:03d}',fill=(180,0,120,255))
        imgs.append(cell.resize((640,640),Image.Resampling.NEAREST))
    out=Image.new('RGBA',(640*len(imgs),640),bg)
    for i,im in enumerate(imgs): out.alpha_composite(im,(i*640,0))
    p=OUT/name; out.save(p); return p
for clip, indices, name in [
    ('sleep_loop',[0,3,6],'sleep-loop-triplet-000-003-006-4x.png'),
    ('sleep_enter',[4,5,6],'sleep-enter-triplet-004-005-006-4x.png'),
    ('wake',[2,3,4],'wake-triplet-002-003-004-4x.png'),
    ('eat',[0,4,8,11],'eat-triplet-000-004-008-011-4x-current.png'),
]:
    p=make_triplet(clip,indices,name); index[name]={'path':str(p),'sha256':sha(p),'frames':indices}

(OUT/'candidate-review-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'contact':str(contact),'previews':str(PREV),'index':str(OUT/'candidate-review-index.json')},ensure_ascii=False,indent=2))
