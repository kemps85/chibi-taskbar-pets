import json, hashlib
from pathlib import Path
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
run=root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01'
def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
raw=run/'05-generation/raw/sleep-enter-frame-004-breakdown-imagegen.png'
processed=run/'05-generation/sleep-enter-frame-004-breakdown-candidate.png'
refs=[
 root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png',
 root/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/hip-rise-crescent-slash-v3/references/weapon-overview.png',
 run/'04-frame-specs/pose-guides/sleep-enter-frame-004-guide.png',
 root/'assets/runtime/taskbar-pet/clip-packs/miyabi/v1/clips/sleep_enter/right/frames/frame-003.png',
 run/'05-generation/sleep-enter-frame-005-candidate.png',
]
data={
 'tool':'image_gen.imagegen','frame':'sleep_enter/frame-004-breakdown','request_id':None,'model':None,
 'raw_output_path':str(raw),'raw_output_sha256':sha(raw),'raw_output_canvas':[1322,1190],
 'raw_alpha_observation':'checkerboard-looking background was present in the rendered preview; border-connected near-white cleanup was applied',
 'processed_output_path':str(processed),'processed_output_sha256':sha(processed),'processed_output_canvas':[160,144],
 'post_process':['border-connected near-white cleanup','threshold generated alpha at 128','crop to authored bbox','nearest-neighbor normalize within 124x112 logical-pixel budget','place centered with bottom at ground y=143'],
 'references':[{'path':str(p),'sha256':sha(p),'exists':p.exists()} for p in refs],
 'prompt':'''Bạn chỉ thực hiện sleep_enter frame-004, một breakdown trung gian rõ ràng. Không thiết kế lại animation. Identity master quyết định Miyabi; weapon master quyết định kiếm/vỏ; pose guide quyết định frame; previous frame-003 chỉ là điểm xuất phát; next frame-005 candidate chỉ là điểm đến. Giữ thân trên còn phần lớn ở tư thế đứng nghiêng, pelvis hạ một phần ba, một gối bắt đầu gập về trái, đầu về phải, tay chống giữ trọng lượng. Kiếm/vỏ chuyển sang đường chéo thấp, nối với tay và đủ chiều dài. Đây không phải pose nằm/rest cuối. Không crop, squash, rotate toàn sprite, checkerboard baked, food, prop, Vô Vĩ, effect, slash, energy blade, background hoặc camera motion. Output chỉ frame không annotation.''',
 'status':'REJECTED_FOR_WEAPON_CONTINUITY_AND_POSE_BRIDGE',
}
(run/'05-generation/imagegen-sleep-enter-frame-004-breakdown-provenance.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md=f'''# Rejected sleep_enter frame-004 bridge probe

Classification: `Weapon continuity / pose bridge / identity drift risk`
Status: `REJECTED_FOR_CONTINUITY`

## OBSERVED

- The candidate was generated only for the frame-004 bridge after reviewing the current frame-004 → frame-005 boundary.
- After border cleanup and nearest normalization, the frame keeps a full-sized Miyabi-like body, but the sword/sheath read is ambiguous: a horizontal blade-like form extends across the lower silhouette while the previous frame's held weapon is not carried through as a single unambiguous attachment.
- The pose is not a safe one-third-lowered bridge between stable frame-003 and the accepted low-rest frame-005 candidate.

## Decision

- Do not copy this frame into the candidate pack.
- Do not use it as the next imagegen reference.
- Do not hide the boundary with smoothing, crossfade, or extra duplicate frames.
- Pause blind regeneration until the frame-004 weapon trajectory/landmarks are revised.

## Evidence

- Raw: `{raw}`
- Processed rejected output: `{processed}`
- Provenance: `{run/'05-generation/imagegen-sleep-enter-frame-004-breakdown-provenance.json'}`
- Compared boundary: stable `sleep_enter/frame-003` → rejected probe → accepted bounded `sleep_enter/frame-005`.
'''
(run/'06-continuity/sleep-enter-frame-004-breakdown-rejected.md').write_text(md,encoding='utf-8')
print(run/'05-generation/imagegen-sleep-enter-frame-004-breakdown-provenance.json')
print(run/'06-continuity/sleep-enter-frame-004-breakdown-rejected.md')
