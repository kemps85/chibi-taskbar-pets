import json, shutil
from pathlib import Path
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
stable=root/'assets/runtime/taskbar-pet/clip-packs/miyabi/v1'
spirit=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/spirit_tail/right/frames'
sleep_cue=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/sleep_cue/right/frames'
walk=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/walk/right/frames'
hunger=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/hunger_cue/right/frames'
sleep_loop=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/sleep_loop'
eat=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/eat'
sleep_enter=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/sleep_enter'
wake=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/wake'
out=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01/full-pack/clip-packs/miyabi/v1'
if out.exists(): shutil.rmtree(out)
out.mkdir(parents=True)
for name in ['clips','qa.json']:
    src=stable/name; dst=out/name
    if src.is_dir(): shutil.copytree(src,dst,dirs_exist_ok=True)
    else: shutil.copy2(src,dst)
for clip_name, source_dir, count in [('spirit_tail', spirit, 32), ('sleep_cue', sleep_cue, 8), ('walk', walk, 8), ('hunger_cue', hunger, 8), ('sleep_loop', sleep_loop, 12), ('eat', eat, 12), ('sleep_enter', sleep_enter, 10), ('wake', wake, 8)]:
    target=out/f'clips/{clip_name}/right/frames'
    shutil.rmtree(target)
    target.mkdir(parents=True)
    for i in range(count): shutil.copy2(source_dir/f'frame-{i:03d}.png',target/f'frame-{i:03d}.png')
manifest=json.loads((stable/'manifest.json').read_text(encoding='utf-8'))
manifest['status']='CANDIDATE_USER_APPROVAL_PENDING'
manifest['pack_id']='miyabi-remediation-r01-candidate-pack'
manifest['clips']['spirit_tail']['frame_count']=32
manifest['clips']['spirit_tail']['frame_durations_ms']=[90]*32
manifest['clips']['spirit_tail']['segments']={'enter':{'start':0,'end':12},'loop':{'start':13,'end':24},'exit':{'start':25,'end':31}}
manifest['qa']='candidate-qa.json'
manifest['candidate_review']='../spirit_tail/continuity-review.md'
manifest['candidate_reviews']={
    'walk':'../walk/continuity-review.md',
    'hunger_cue':'../hunger_cue/continuity-review.md',
    'eat':'../eat/continuity-review.md',
    'sleep_cue':'../sleep_cue/continuity-review.md',
    'sleep_enter':'../sleep_enter/continuity-review.md',
    'sleep_loop':'../sleep_loop/continuity-review.md',
    'wake':'../wake/continuity-review.md',
    'spirit_tail':'../spirit_tail/continuity-review.md'
}
manifest['clips']['sleep_loop']['frame_count']=12
manifest['clips']['sleep_loop']['frame_durations_ms']=[250]*12
manifest['clips']['sleep_loop']['loop_policy']='loop'
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
qa={'status':'CANDIDATE_USER_APPROVAL_PENDING','sources':['../spirit_tail/qa.json','../sleep_cue/qa.json','../walk/qa.json','../hunger_cue/qa.json'],'note':'Technical candidate only; not an approval or stable-pack manifest.'}
(out/'candidate-qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(out)
print('frame counts', {name:len(list((out/f'clips/{name}/right/frames').glob('frame-*.png'))) for name in manifest['required_clips']})
