import json,hashlib
from pathlib import Path
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
run=root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01'
def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
guide=run/'04-frame-specs/pose-guides/sleep-enter-frame-005-guide.png'
prev=root/'assets/runtime/taskbar-pet/clip-packs/miyabi/v1/clips/sleep_enter/right/frames/frame-004.png'
nextp=run/'05-generation/sleep-enter-frame-004-candidate.png'
weapon=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/hip-rise-crescent-slash-v3/references/weapon-overview.png'
body=root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png'
spec={
 'specification_revision':'r01-frame005',
 'character':'Miyabi','clip':'sleep_enter','frame_id':'frame-005','timestamp_ms':600,'duration_ms':120,
 'phase':'lowering-to-rest','role':'breakdown','purpose':'Bridge the approved standing lean into the approved compact feet-left/head-right rest key.',
 'identity_reference':{'path':str(body),'sha256':sha(body)},
 'weapon_reference':{'path':str(weapon),'sha256':sha(weapon)},
 'previous_approved_pose':{'path':str(prev),'sha256':sha(prev)},
 'current_annotated_pose_guide':{'path':str(guide),'sha256':sha(guide)},
 'next_approved_pose':{'path':str(nextp),'sha256':sha(nextp)},
 'landmarks':{
  'head':{'previous_xy':[68,61],'current_xy':[72,78],'next_xy':[66,84],'delta_xy':[4,17],'rotation_change':'slight rightward lean','fixed_or_moving':'moving'},
  'shoulders':{'previous_xy':[65,80],'current_xy':[68,97],'next_xy':[63,101],'delta_xy':[3,17],'rotation_change':'lower/right','fixed_or_moving':'moving'},
  'elbows':{'previous_xy':[59,95],'current_xy':[62,113],'next_xy':[58,117],'delta_xy':[3,18],'rotation_change':'fold','fixed_or_moving':'moving'},
  'wrists':{'previous_xy':[54,104],'current_xy':[56,121],'next_xy':[55,125],'delta_xy':[2,17],'rotation_change':'maintain support','fixed_or_moving':'moving'},
  'pelvis':{'previous_xy':[65,111],'current_xy':[66,126],'next_xy':[64,128],'delta_xy':[1,15],'rotation_change':'lower','fixed_or_moving':'moving'},
  'knees':{'previous_xy':[45,126],'current_xy':[43,137],'next_xy':[39,139],'delta_xy':[-2,11],'rotation_change':'fold feet-left','fixed_or_moving':'moving'},
  'heels':{'previous_xy':[35,139],'current_xy':[32,142],'next_xy':[24,143],'delta_xy':[-3,3],'rotation_change':'ground','fixed_or_moving':'fixed'},
  'toes':{'previous_xy':[20,140],'current_xy':[18,142],'next_xy':[12,143],'delta_xy':[-2,2],'rotation_change':'ground','fixed_or_moving':'fixed'},
  'weapon_hilt':{'previous_xy':[88,113],'current_xy':[91,128],'next_xy':[91,129],'delta_xy':[3,15],'rotation_change':'protected, near-horizontal','fixed_or_moving':'moving'},
  'weapon_tip':{'previous_xy':[126,119],'current_xy':[126,135],'next_xy':[126,135],'delta_xy':[0,16],'rotation_change':'near-horizontal','fixed_or_moving':'moving'},
 },
 'weight_and_balance':{'support':'lowered pelvis and support hand; feet contact ground','action_line':'standing lean becomes compact seated lean','primary_motion':'pelvis down, knees fold toward left, head follows with delay','weapon_prop_trajectory':'hilt follows support hand; tip remains visible and does not detach','acceleration_or_deceleration':'controlled lowering, decelerate into rest'},
 'secondary_motion':{'description':'hair/cape settle after torso; no independent translation','onset_delay_ms':40},
 'silhouette_expectation':'compact and continuous; feet-left/head-right; no detached gray weapon fragments; no transparent-hole fill',
 'identity_locks':['approved body and weapon','160x144 canvas','right-authored','feet ground at y=143','empty plate semantics irrelevant to this clip'],
 'canvas':[160,144],'placement_anchor':[64,120],'ground_line_y':143,'authored_direction':'right','mirror_rule':'runtime mirrors right master for left',
 'must_remain_unchanged':['character identity','weapon design/length','ground contact','right-only storage'],
 'must_not_be_invented':['slash','energy effect','new prop','new food','camera move'],
 'output_requirements':['transparent PNG','160x144','binary alpha preferred','nearest pixel edges','no annotation']
}
(run/'04-frame-specs/sleep-enter-frame-005-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(run/'04-frame-specs/sleep-enter-frame-005-spec.json')
