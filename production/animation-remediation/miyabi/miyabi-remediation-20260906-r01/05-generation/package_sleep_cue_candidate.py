import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
run=root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01'
cand=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/sleep_cue'
frames=cand/'right/frames'; files=sorted(frames.glob('frame-*.png'))
hashes=[]; metrics=[]
for p in files:
 data=p.read_bytes(); im=Image.open(p).convert('RGBA'); a=im.getchannel('A'); vals=list(a.getdata()); bbox=a.getbbox(); hashes.append({'frameId':p.stem,'path':str(p),'sha256':hashlib.sha256(data).hexdigest()}); metrics.append({'frameId':p.stem,'bbox':list(bbox) if bbox else None,'partialAlphaPixels':sum(0<x<255 for x in vals),'maxBorderAlpha':max(max(a.getpixel((x,0)),a.getpixel((x,143))) for x in range(160))})
manifest={'candidateId':'miyabi-remediation-20260906-r01-sleep-cue-v1','characterId':'miyabi','clip':'sleep_cue','status':'CANDIDATE_USER_APPROVAL_PENDING','canvas':{'width':160,'height':144},'authoredDirection':'right','mirror':'runtime-horizontal-exact','placementAnchor':[64,120],'groundLineY':143,'frameCount':8,'frameDurationMs':150,'totalDurationMs':1200,'loopPolicy':'once','frames':'sleep_cue/right/frames'}
(cand/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
qa={'candidateId':manifest['candidateId'],'status':'CANDIDATE_USER_APPROVAL_PENDING','frames':metrics,'unionBBox':[min(m['bbox'][0] for m in metrics),min(m['bbox'][1] for m in metrics),max(m['bbox'][2] for m in metrics),max(m['bbox'][3] for m in metrics)],'totalPartialAlphaPixels':sum(m['partialAlphaPixels'] for m in metrics),'maxBorderAlpha':max(m['maxBorderAlpha'] for m in metrics),'notes':['body/weapon/feet remain from identity master','only narrow eye/ear pixels changed','no new prop or effect']}
(cand/'qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
prov={'candidateId':manifest['candidateId'],'createdUtc':datetime.now(timezone.utc).isoformat(),'tool':'deterministic-Pillow-pixel-edit','imagegen':{'used':False},'sourceIdentity':str(root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png'),'sourceIdentitySha256':hashlib.sha256((root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png').read_bytes()).hexdigest(),'operations':['place unchanged identity body on transparent 160x144 at (4,19)','frames 2-5: replace only eye-color pixels with skin and draw one-pixel eyelid line','frames 2-5: remove three one-pixel ear-tip pixels for bounded ear softening','no scaling','no rotation','no palette-wide edit'],'outputHashes':hashes,'approvalStatus':'PENDING'}
(cand/'provenance.json').write_text(json.dumps(prov,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
ims=[Image.open(frames/f'frame-{i:03d}.png').convert('RGBA') for i in range(8)]
ims[0].save(cand/'preview-1x.apng',save_all=True,append_images=ims[1:],duration=150,loop=0,format='PNG')
print(cand)
print(json.dumps({'frames':len(files),'union':qa['unionBBox'],'partial':qa['totalPartialAlphaPixels'],'border':qa['maxBorderAlpha']}))
