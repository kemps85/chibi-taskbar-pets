# Vô Vĩ candidate continuity review

Candidate: `miyabi-remediation-20260906-r01-spirit-tail-v1`
Status: **TECHNICAL CANDIDATE — USER APPROVAL PENDING**

## Construction

- Source: existing `layered-v6-clean/right/frames/frame-00..31.png` companion sequence.
- Source is not a slash asset and no slash choreography/effect was added.
- Each 128x128 source frame is alpha-composited once onto a transparent 160x144 canvas at offset `(4,19)`.
- No resize, color change, frame reordering, smoothing, or generator execution.
- Timing: 32 frames × 90 ms = 2,880 ms.
- Segments: enter `0–12`, loop `13–24`, exit `25–31`.
- Runtime contract: right-authored, exact horizontal mirror for left, placement anchor `(64,120)`, ground line `y=143`.

## Review evidence

- Full light contact sheet: `contact-light-2x.png`.
- Full dark contact sheet: `contact-dark-2x.png`.
- Full checker contact sheet: `contact-checker-2x.png`.
- Triplets: `triplet-enter-breakdown-4x.png`, `triplet-loop-seam-4x.png`, `triplet-exit-breakdown-4x.png`, `triplet-exit-to-enter-4x.png`.
- Exact-duration playback: `preview-light-1x.mp4`, transparent `preview-1x.apng`.
- Alpha timeline: `alpha-timeline.json`.
- Source provenance and output hashes: `provenance.json`.
- Frame specification: `04-frame-specs/spirit-tail-source-spec.json`.

## OBSERVED

- Body and weapon stay visually fixed across the contact sheet; Vô Vĩ is the only moving layer.
- Enter visibility grows from hidden/near-hidden through a continuous path toward the hover region.
- Hover remains bounded around the high right side; no arbitrary reverse-frame jump is present.
- Exit returns toward the start anchor and reaches the hidden state before frame 000.
- Exit-to-enter triplet shows the body unchanged and the companion absent at both ends.
- No non-zero canvas border alpha; candidate union bbox is `[22,24,113,143]`.
- Source companion contains partial alpha on selected scaled/fade frames. This is tied to the source's explicit scale/opacity path, not a new post-process. It remains subject to visual approval rather than being silently quantized.

## INFERRED

- This candidate is a stronger continuity baseline than the stable 16-frame pack because it preserves the already-authored 32-frame companion path instead of fabricating an exit by `[7,5,3,0]` reuse.
- The exact user-approved Vô Vĩ semantic/anchor is still not documented as a separate approval record; candidate remains pending.

## FAIL/LOCK DECISION

- **Source continuity:** PASS for technical candidate review.
- **Identity/weapon lock:** PASS against the inspected layered-v6 source lock.
- **Alpha policy:** REVIEW/PENDING because intentional companion partial-alpha behavior must be accepted as part of the source path.
- **User approval:** PENDING.
- Stable pack integration: **not performed**.
