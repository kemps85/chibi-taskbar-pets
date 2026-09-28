import json, sys
from pathlib import Path
from PIL import Image
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
pack=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/full-pack/clip-packs/miyabi/v1'
manifest=json.loads((pack/'manifest.json').read_text(encoding='utf-8'))
errors=[]; clip_reports={}
if manifest.get('status')!='CANDIDATE_USER_APPROVAL_PENDING': errors.append('candidate status missing')
if manifest.get('canvas') != {'width':160,'height':144}: errors.append('canvas mismatch')
if manifest.get('master_direction')!='right': errors.append('master direction mismatch')
if manifest.get('left_rendering',{}).get('strategy')!='mirror-right-at-runtime': errors.append('mirror contract mismatch')
if manifest.get('clips',{}).get('spirit_tail',{}).get('frame_count') != 32: errors.append('spirit frame count mismatch')
for cid in manifest.get('required_clips',[]):
    clip=manifest['clips'].get(cid)
    if not clip: errors.append(f'missing clip {cid}'); continue
    directory=pack/clip['frames']; paths=sorted(directory.glob('frame-*.png'))
    count=clip['frame_count']
    if len(paths)!=count: errors.append(f'{cid}: expected {count} files, got {len(paths)}')
    durations=clip['frame_durations_ms']
    if len(durations)!=count or any((not isinstance(x,int) or x<=0) for x in durations): errors.append(f'{cid}: duration vector invalid')
    if cid=='spirit_tail':
        seg=clip.get('segments',{}); ranges=[(v['start'],v['end']) for v in seg.values()]
        if ranges != [(0,12),(13,24),(25,31)]: errors.append(f'{cid}: segments invalid {ranges}')
    bboxes=[]; partial=0; border=0; bad=[]
    for p in paths:
        try: im=Image.open(p).convert('RGBA')
        except Exception as exc: errors.append(f'{cid}: unreadable {p.name}: {exc}'); continue
        if im.size!=(160,144): bad.append(f'{p.name}:size={im.size}')
        a=im.getchannel('A'); b=a.getbbox(); bboxes.append(list(b) if b else None)
        vals=list(a.getdata()); partial += sum(0<x<255 for x in vals)
        for x in range(160): border=max(border,a.getpixel((x,0)),a.getpixel((x,143)))
        for y in range(144): border=max(border,a.getpixel((0,y)),a.getpixel((159,y)))
    if bad: errors.extend([f'{cid}: {x}' for x in bad])
    clip_reports[cid]={'files':len(paths),'frameCount':count,'durationMs':sum(durations),'loopPolicy':clip['loop_policy'],'partialAlphaPixels':partial,'maxBorderAlpha':border,'unionBBox':([min(b[0] for b in bboxes if b),min(b[1] for b in bboxes if b),max(b[2] for b in bboxes if b),max(b[3] for b in bboxes if b)] if any(bboxes) else None)}
report={'status':'PASS' if not errors else 'FAIL','candidateStatus':manifest.get('status'),'pack':str(pack),'errors':errors,'clips':clip_reports,'note':'Technical candidate validation only; no user approval and no stable integration.'}
out=root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/07-runtime-qa/candidate-spirit-tail-contract.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
if errors: sys.exit(1)
