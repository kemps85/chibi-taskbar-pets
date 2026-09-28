# Sleep-loop frame-006 bounded review

Classification: `Continuity / spacing / identity lock`

## OBSERVED

- The imagegen output is a clean-looking Miyabi rest drawing after border cleanup, but its authored content bbox is `(83,257)-(1249,1057)` in the raw 1322x1190 image.
- After nearest-neighbor processing with the same placement contract, the candidate content is 124x85 at y=58–143.
- The frame-000 candidate content is 124x108 at y=35–143.
- The weapon and feet therefore do not share the approved frame-000 placement contract, and the head/ear silhouette moves by many pixels rather than the requested one-pixel inhale breakdown.

## EXPECTED

Frame-006 must preserve the sleep-loop support and weapon/feet anchors, with only the named upper coat/chest region changing by one logical pixel.

## DECISION

`REJECTED_FOR_CONTINUITY`; do not use this frame as a reference for subsequent generation. The raw output, processed output, and provenance are retained for traceability. No stable asset was changed.

## Minimal repair

Use the approved frame-000 rest key as the identity/placement lock and author only a bounded hair/coat secondary-motion mask. Do not normalize this failed output by non-uniformly scaling it.
