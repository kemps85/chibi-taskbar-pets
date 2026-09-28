# eat candidate continuity review

Status: `TECHNICAL_PARTIAL_PASS_USER_APPROVAL_PENDING`

## OBSERVED

- The candidate has 12 frames at 160x144, 160 ms each, 1,920 ms total, once policy.
- The empty plate/food-area pixels are restored from the stable `eat/frame-000` source rather than invented. The candidate adds no named food or utensil.
- The generated body keys were normalized to the same 120px authored body height and ground line y=143. The body frames use hard thresholded alpha; the only partial-alpha pixels are the retained plate pixels from the stable source.
- Frame-003 and frame-006 imagegen key probes were processed separately with recorded provenance. Frame-009 required border-connected black-background removal before processing.

## LIMITATION / DEFECT

- The contact sheet shows identity/weapon continuity is technically bounded, but the hand-to-mouth bite is subtle at 160x144 and the weapon/hand cluster is visually dense. This is not yet a full animation pass.
- The sequence currently holds generated keys rather than having fully authored in-betweens. The exact hand trajectory and bite readability require user animation review; do not claim this clip is final.

## Evidence

- Contact sheet: `C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\06-continuity\eat-contact-4x.png`
- Key triplet: `C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\06-continuity\eat-triplet-000-004-008-011-4x.png`
- Source spec: `C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\04-frame-specs\eat-source-spec.json`
- Key outputs: `C:\Users\ASUS\Documents\ChatGPT\Game\assets\generated\pixel-chibi\production-v2\hoshimi-miyabi\remediation\miyabi-remediation-20260906-r01\eat`
- Provenance: `C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\05-generation\imagegen-eat-frame-006-provenance.json` (frame-003/frame-009 provenance to be added before any approval request)

## Gate

Technical structural check: `PASS_WITH_LIMITATION`.
Animation review: `PENDING USER REVIEW`.
Stable pack integration: `NOT ALLOWED YET`.
