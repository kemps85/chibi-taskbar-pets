import json
from pathlib import Path
from PIL import Image
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
run='miyabi-remediation-20260906-r01'
stable=root/'assets/runtime/taskbar-pet/clip-packs/miyabi/v1/clips/hunger_cue/right/frames'
rows=[]
phases=['neutral','look-breakdown','look-key','gesture-breakdown','gesture-peak','recovery','settle','neutral-recovery']
roles=['keyframe','breakdown','keyframe','breakdown','keyframe','recovery','settle','recovery']
for i in range(8):
 im=Image.open(stable/f'frame-{i:03d}.png').convert('RGBA'); a=im.getchannel('A'); pts=[]
 for y in range(144):
  for x in range(110,160):
   if a.getpixel((x,y))>0: pts.append((x,y))
 bbox=[min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts)+1,max(y for x,y in pts)+1] if pts else None
 fixed={k:{'previousXY':'identity-fixed','currentXY':'identity-fixed','nextXY':'identity-fixed','deltaXY':[0,0],'rotationChange':0,'fixedOrMoving':'fixed'} for k in ['head','shoulders','elbows','wrists','pelvis','knees','heels','toes','weaponHilt','weaponTip']}
 fixed['propCompanionAnchor']={'previousXY':'source food-area anchor','currentXY':bbox,'nextXY':'next source food-area anchor','deltaXY':'source-authored cue only','rotationChange':'none','fixedOrMoving':'moving'}
 rows.append({'specificationRevision':f'{run}-hunger-cue-1','character':'hoshimi-miyabi','clip':'hunger_cue','frameId':f'frame-{i:03d}','timestampMs':i*150,'durationMs':150,'phase':phases[i],'role':roles[i],'purpose':'retain existing food-area semantics while removing disconnected body redraw','identityReference':str(root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png'),'weaponReference':str(root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/hip-rise-crescent-slash-v3/references/weapon-overview.png'),'previousApprovedPose':'identity master / prior hunger phase','currentAnnotatedPoseGuide':'APPROVAL_TBD','nextApprovedPose':'identity master / next hunger phase','previousPose':'identity master fixed','currentPose':{'body':'identity master fixed','foodAreaBBox':bbox,'bodyGesture':'APPROVAL_TBD'},'nextPose':'next listed phase','landmarks':fixed,'weightAndBalance':'feet remain on ground; no whole-body translate','support':'identity master feet at y=143','actionLine':'contained look toward existing food area','primaryMotion':'food-area cue remains source-authored; body gesture pending approval','weaponPropTrajectory':'weapon fixed in this candidate','accelerationDeceleration':'source timing preserved at 150ms per frame','secondaryMotion':'body/eye restraint gesture pending approval','secondaryOnsetDelayMs':None,'silhouetteExpectation':'identity silhouette unchanged; no detached non-food fragments','identityLocks':['body scale fixed','weapon fixed','palette fixed','hair/cape fixed'],'canvas':'160x144','placementAnchorXY':[64,120],'groundLineY':143,'authoredDirection':'right','mirrorRule':'runtime mirrors right','mustRemainUnchanged':['behavior semantics','Firefly','clip duration','food-area source semantics'],'mustNotBeInvented':['new food','utensil','slash','effect','body fragment'],'outputRequirements':['RGBA PNG 160x144','transparent background','hard pixel edges','no annotation'],'status':'CANDIDATE_SOURCE_SPEC_USER_APPROVAL_PENDING'})
out=run_dir=root/'production/animation-remediation/miyabi'/run/'04-frame-specs/hunger-source-spec.json'
out.write_text(json.dumps({'run':run,'status':'CANDIDATE_SOURCE_SPEC_USER_APPROVAL_PENDING','clip':'hunger_cue','rows':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(out)
