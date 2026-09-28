import json
from pathlib import Path
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
run=root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01'
qa=json.loads((root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layered-animation-qa.json').read_text(encoding='utf-8'))
poses=qa['poses']; rows=[]
for i,p in enumerate(poses):
    x,y=p['companion_center']; target=[round(x+4,3),round(y+19,3)]
    prev=poses[i-1] if i>0 else None
    prevxy=[round(prev['companion_center'][0]+4,3),round(prev['companion_center'][1]+19,3)] if prev else None
    nxt=poses[i+1] if i<31 else None
    nxtxy=[round(nxt['companion_center'][0]+4,3),round(nxt['companion_center'][1]+19,3)] if nxt else None
    phase='enter' if i<=12 else 'loop' if i<=24 else 'exit'
    role='keyframe' if i in [0,6,12,13,24,25,31] else 'breakdown'
    rows.append({
      'specificationRevision':'miyabi-remediation-20260906-r01-spirit-source-1',
      'character':'hoshimi-miyabi','clip':'spirit_tail','frameId':f'frame-{i:03d}',
      'timestampMs':i*90,'durationMs':90,'phase':phase,'role':role,
      'purpose':'reuse the existing authored Vô Vĩ companion path without arbitrary frame reversal',
      'identityReference':'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png',
      'weaponReference':'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/hip-rise-crescent-slash-v3/references/weapon-overview.png',
      'previousApprovedPose':f'layered-v6 human frame {i}' if i>0 else 'clip start hidden companion',
      'currentAnnotatedPoseGuide':f'layered-v6 QA human frame {i+1}; companion center source={p["companion_center"]}, scale={p["scale"]}, opacity={p["opacity"]}',
      'nextApprovedPose':f'layered-v6 human frame {i+2}' if i<31 else 'clip end hidden companion',
      'previousPose':prevxy,'currentPose':target,'nextPose':nxtxy,
      'landmarks':{k:{'previousXY':None,'currentXY':None,'nextXY':None,'deltaXY':None,'rotationChange':None,'fixedOrMoving':'fixed-to-layered-v6-body-master'} for k in ['head','shoulders','elbows','wrists','pelvis','knees','heels','toes','weaponHilt','weaponTip']},
      'propCompanionAnchor':{'previousXY':prevxy,'currentXY':target,'nextXY':nxtxy,'deltaXY':[round(target[0]-prevxy[0],3),round(target[1]-prevxy[1],3)] if prevxy else None,'rotationChange':'source-authored companion orientation','fixedOrMoving':'moving'},
      'weightAndBalance':'body fixed; feet baseline y=143',
      'support':'standing body from layered-v6 body lock',
      'actionLine':'companion path only; body remains fixed',
      'primaryMotion':'companion position/scale/opacity from source QA',
      'weaponPropTrajectory':'weapon fixed to body master; companion is separate layer',
      'accelerationDeceleration':'source-authored enter/exit easing; loop bounded hover',
      'secondaryMotion':'companion only',
      'secondaryOnsetDelayMs':0,
      'silhouetteExpectation':'body bbox/weapon unchanged; companion visibility follows source opacity',
      'identityLocks':['body_pixel_drift=0','body_scale_drift=0','body_anchor_drift=0','weapon_drift=0'],
      'canvas':'160x144','placementAnchorXY':[64,120],'groundLineY':143,'authoredDirection':'right','mirrorRule':'runtime mirrors right-authored frame for left',
      'mustRemainUnchanged':['body master','weapon master','behavior semantics','Firefly','right-only storage'],
      'mustNotBeInvented':['slash','shockwave','new effect','new character silhouette','camera movement'],
      'outputRequirements':['RGBA PNG 160x144','transparent background','no resize after composition','hard runtime sampling'],
      'sourceEvidence':{'qaFile':'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layered-animation-qa.json','sourceHumanFrame':i+1,'sourceCanvas':'128x128','compositionOffset':[4,19]},
      'status':'CANDIDATE_SOURCE_SPEC_USER_APPROVAL_PENDING'
    })
out={'run':'miyabi-remediation-20260906-r01','status':'CANDIDATE_SOURCE_SPEC_USER_APPROVAL_PENDING','rows':rows,'sourceLayerLock':qa['layer_lock'],'segments':{'enter':[0,12],'loop':[13,24],'exit':[25,31]}}
(run/'04-frame-specs/spirit-tail-source-spec.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(run/'04-frame-specs/spirit-tail-source-spec.json',len(rows))
