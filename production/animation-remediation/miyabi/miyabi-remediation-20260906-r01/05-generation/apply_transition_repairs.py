from pathlib import Path
from PIL import Image, ImageDraw
import shutil, hashlib, json
ROOT=Path(r"C:\Users\ASUS\Documents\ChatGPT\Game")
RUN=ROOT/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01'
CAND=ROOT/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01'
OUT=RUN/'05-generation/transition-repair'
BACK=OUT/'before'; OUT.mkdir(parents=True,exist_ok=True); BACK.mkdir(parents=True,exist_ok=True)
source=CAND/'sleep_enter/frame-004.png'
rest_sleep=CAND/'sleep_enter/frame-006.png'
rest_wake=CAND/'wake/frame-002.png'
for p in [CAND/'sleep_enter/frame-005.png', CAND/'wake/frame-003.png']:
    target=BACK/p.parent.name
    target.mkdir(parents=True,exist_ok=True)
    shutil.copy2(p,target/p.name)

def bridge(base_path, dy, name):
    base=Image.open(base_path).convert('RGBA'); src=Image.open(source).convert('RGBA')
    # Explicit pose repair: retain grounded rest lower-body and weapon, replace only upper body/head/cape using the approved leaning key.
    mask=Image.new('L',(160,144),0); d=ImageDraw.Draw(mask)
    d.polygon([(39,28),(78,22),(103,37),(111,63),(108,95),(99,108),(38,108),(30,84),(33,50)],fill=255)
    shifted=Image.new('RGBA',(160,144),(0,0,0,0)); shifted.alpha_composite(src,(0,dy))
    result=base.copy(); result.paste(shifted,(0,0),mask)
    result.save(OUT/(name+'.png'))
    return result
sleep=bridge(rest_sleep,11,'sleep-enter-frame-005-bridge')
wake=bridge(rest_wake,16,'wake-frame-003-bridge')
sleep.save(CAND/'sleep_enter/frame-005.png'); wake.save(CAND/'wake/frame-003.png')
meta={
 'status':'CANDIDATE_ONLY',
 'method':'hard-pixel segmented pose bridge; no alpha blend, no smoothing, no whole-sprite squash',
 'source_frame':str(source),
 'base_frames':{'sleep_enter':str(rest_sleep),'wake':str(rest_wake)},
 'outputs':{},
 'constraints':['preserve grounded lower body and weapon until the explicit pickup/recovery key','replace only upper-body/head/cape region','nearest-neighbor pixel placement','stable source/master untouched']
}
for p in [OUT/'sleep-enter-frame-005-bridge.png',OUT/'wake-frame-003-bridge.png',CAND/'sleep_enter/frame-005.png',CAND/'wake/frame-003.png']:
    meta['outputs'][str(p)]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
(OUT/'provenance.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
# Contact of the repaired ranges.
items=[('sleep_enter previous',Image.open(BACK/'sleep_enter/frame-005.png').convert('RGBA')),('sleep_enter repaired',sleep),('sleep_loop frame000',Image.open(CAND/'sleep_loop/frame-000.png').convert('RGBA')),('wake previous',Image.open(BACK/'wake/frame-003.png').convert('RGBA')),('wake repaired',wake),('wake frame004',Image.open(CAND/'wake/frame-004.png').convert('RGBA'))]
out=Image.new('RGBA',(640*3,612*2),(220,220,220,255));d=ImageDraw.Draw(out)
for i,(label,im) in enumerate(items):
    out.alpha_composite(im.resize((640,576),Image.Resampling.NEAREST),(i%3*640,i//3*612+28)); d.text((i%3*640+8,i//3*612+6),label,fill='magenta')
out.save(OUT/'contact-4x.png')
print('TRANSITION_REPAIRS_APPLIED')
