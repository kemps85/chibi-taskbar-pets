# sleep_loop candidate continuity review

Status: `TECHNICAL_PARTIAL_PASS_USER_APPROVAL_PENDING`

## OBSERVED

- 12 frames are present at 160x144, 250 ms each, 3,000 ms total, loop policy.
- Every frame has binary alpha, zero non-transparent border pixels, the same content bbox `(2,35)-(126,143)`, and the same ground contact.
- Frames 0, 1, 2, 6, 7, 8, 9, 10, and 11 are the exact locked rest key. Frames 3–5 move only the trailing-hair contour at x=95..96, y=107..112 by one logical pixel and then recover to the locked key.
- The frame-000 rest key is the bounded sleep-enter frame-004 drawing, selected because it better realizes the user-approved compact feet-left/head-right seated rest with pooled coat and visible protected weapon. It is a candidate rest key, not a user-approved final drawing. Its imagegen output was processed with alpha thresholding plus nearest-neighbor crop/placement; provenance is stored in the run folder.
- The separate frame-006 imagegen attempt was rejected because it produced a 124x85 placement instead of the 124x108 frame-000 placement. It is retained under `06-continuity/sleep-loop-frame-006-defect.md` and is not used.

## REVIEW

- Identity: technical visual check only; broad identity direction is user-approved, actual candidate frame approval is pending.
- Pose: feet-left/head-right compact rest direction matches the user-approved direction. No whole-body translation or squash is used in the candidate sequence.
- Weapon: visible and fixed across the candidate sequence; no slash/effect is present.
- Secondary motion: deliberately limited to a six-row, one-pixel hair-contour diff over three 250 ms frames. This is subtle by design and does not claim a full breathing pass.
- Loop seam: frame-011 equals frame-000; no seam displacement was found.

## Evidence

- Contact sheet: `C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\06-continuity\sleep-loop-contact-4x.png`
- Triplet: `C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\06-continuity\sleep-loop-triplet-000-003-006-4x.png`
- Source spec: `C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\04-frame-specs\sleep-loop-source-spec.json`
- Imagegen provenance: `C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\05-generation\imagegen-sleep-loop-frame-000-provenance.json`

## Gate

Technical candidate check: `PASS_WITH_LIMITATION`.
Animation review: `PENDING USER REVIEW`.
Stable pack integration: `NOT ALLOWED YET`.
