# Remaining Miyabi clips — bounded motion proposal

Status: `PROPOSAL_NOT_APPROVED_NOT_GENERATION_READY`

This document advances timing, phase, and continuity planning without inventing a prop, changing behavior semantics, or generating frames. Exact landmark XY values remain approval-gated. Do not use this document as an imagegen packet until the approval values in `08-handoff/APPROVAL-REQUEST.md` are supplied.

## Fixed contract

- Canvas: 160x144 logical pixels.
- Right-authored master; runtime mirrors left.
- Placement anchor: `(64,120)`; ground line: `y=143`.
- Stable frame counts and durations are preserved: hunger 8x150ms, eat 12x160ms, sleep_enter 10x120ms, sleep_loop 12x250ms, wake 8x100ms.
- Weapon remains the approved sheathed mechanical katana; no slash, energy blade, shockwave, or new action.

## Proposed choreography, pending approval

### hunger_cue — 8 frames / 1200 ms / once

Observed contract: keep the existing empty food-area/plate semantics. The cue must not invent a named food or utensil.

| Frame | Time | Role | Proposed pose/continuity | Exact XY |
| ---: | ---: | --- | --- | --- |
| 000 | 0ms | Keyframe | Same approved standing identity; food-area cue absent or at its authored start. | APPROVAL_TBD |
| 001 | 150ms | Breakdown | Eyes/face turn minimally toward food area; feet and weapon fixed. | APPROVAL_TBD |
| 002 | 300ms | Keyframe | Small contained look/torso response; no scale change. | APPROVAL_TBD |
| 003 | 450ms | Hold | Restraint hand/arm gesture begins; weapon grip unchanged. | APPROVAL_TBD |
| 004 | 600ms | Keyframe | Gesture peak; plate/food-area cue remains attached to its authored anchor. | APPROVAL_TBD |
| 005 | 750ms | Recovery | Hand returns; head returns toward neutral. | APPROVAL_TBD |
| 006 | 900ms | Settle | Body settles without translating the whole sprite. | APPROVAL_TBD |
| 007 | 1050ms | Recovery | Neutral destination; no pop on exit. | APPROVAL_TBD |

### eat — 12 frames / 1920 ms / once

Observed contract: preserve the existing empty food-area/plate-like semantics until `FOOD` is confirmed. One compact bite/tea-like pause; no new utensil.

| Frame | Time | Role | Proposed pose/continuity | Exact XY |
| ---: | ---: | --- | --- | --- |
| 000 | 0ms | Keyframe | Enter from hunger/standing destination; weapon clear. | APPROVAL_TBD |
| 001 | 160ms | Breakdown | Hand begins toward existing food area; body remains supported. | APPROVAL_TBD |
| 002 | 320ms | In-between | Hand/prop moves on one continuous arc toward mouth. | APPROVAL_TBD |
| 003 | 480ms | Keyframe | Hand reaches mouth; no detached prop. | APPROVAL_TBD |
| 004 | 640ms | Hold | Compact bite/tea-like pause; face remains identity-locked. | APPROVAL_TBD |
| 005 | 800ms | Recovery | Hand leaves mouth with the same prop attachment. | APPROVAL_TBD |
| 006 | 960ms | In-between | Hand travels back toward food area. | APPROVAL_TBD |
| 007 | 1120ms | Keyframe | Hand reaches food area; plate stays fixed. | APPROVAL_TBD |
| 008 | 1280ms | Hold | Brief contained satisfaction response; no new effect. | APPROVAL_TBD |
| 009 | 1440ms | Recovery | Hand returns toward resting position. | APPROVAL_TBD |
| 010 | 1600ms | Settle | Weapon and arm settle without teleport. | APPROVAL_TBD |
| 011 | 1760ms | Keyframe | Return destination matches next standing/idle pose. | APPROVAL_TBD |

### sleep_enter — 10 frames / 1200 ms / once

Observed orientation proposal only: feet toward viewer-left, head/body toward viewer-right, ground contact retained. This is not an approval of the current broken source.

| Frame | Time | Role | Proposed pose/continuity | Exact XY |
| ---: | ---: | --- | --- | --- |
| 000 | 0ms | Keyframe | Approved standing destination from sleep_cue; weapon attached. | APPROVAL_TBD |
| 001 | 120ms | Breakdown | Weight shifts into the support leg; ears/face remain identity-locked. | APPROVAL_TBD |
| 002 | 240ms | Keyframe | Knees/hips lower; torso stays connected to pelvis. | APPROVAL_TBD |
| 003 | 360ms | Breakdown | Seated support begins; weapon remains visible and protected. | APPROVAL_TBD |
| 004 | 480ms | In-between | Coat/cape folds toward the rest side; no whole-sprite rotation. | APPROVAL_TBD |
| 005 | 600ms | Keyframe | Compact seated/leaning pose; feet path continues toward viewer-left. | APPROVAL_TBD |
| 006 | 720ms | Breakdown | Hips lower toward ground; head remains attached to torso. | APPROVAL_TBD |
| 007 | 840ms | In-between | Lean reaches rest direction; weapon placement remains stable. | APPROVAL_TBD |
| 008 | 960ms | Keyframe | Near-rest pose with ground contact at y=143. | APPROVAL_TBD |
| 009 | 1080ms | Settle | Exact sleep_loop frame-000 destination; no crop/pop. | APPROVAL_TBD |

### sleep_loop — 12 frames / 3000 ms / loop

The support footprint and weapon anchor must remain fixed across the loop. Only breathing/ear/hair secondary motion is proposed.

| Frame | Time | Role | Proposed pose/continuity | Exact XY |
| ---: | ---: | --- | --- | --- |
| 000 | 0ms | Keyframe | Approved rest pose; support and weapon locked. | APPROVAL_TBD |
| 001 | 250ms | In-between | Small inhale; torso/coat rises within 1px. | APPROVAL_TBD |
| 002 | 500ms | Hold | Rest silhouette held. | APPROVAL_TBD |
| 003 | 750ms | Breakdown | Ear/hair softens by at most 1px; ground contact fixed. | APPROVAL_TBD |
| 004 | 1000ms | Keyframe | Breathing peak; weapon does not drift. | APPROVAL_TBD |
| 005 | 1250ms | Hold | Rest silhouette held. | APPROVAL_TBD |
| 006 | 1500ms | In-between | Exhale begins; coat settles. | APPROVAL_TBD |
| 007 | 1750ms | Keyframe | Lowest breathing point; no body teleport. | APPROVAL_TBD |
| 008 | 2000ms | Hold | Rest silhouette held. | APPROVAL_TBD |
| 009 | 2250ms | Breakdown | Ear/hair returns toward frame 000. | APPROVAL_TBD |
| 010 | 2500ms | In-between | Inhale recovery. | APPROVAL_TBD |
| 011 | 2750ms | Settle | Pixel-identical support/weapon seam with frame 000. | APPROVAL_TBD |

### wake — 8 frames / 800 ms / once

Wake must start from the approved sleep_loop rest pose, not from the current broken source frame.

| Frame | Time | Role | Proposed pose/continuity | Exact XY |
| ---: | ---: | --- | --- | --- |
| 000 | 0ms | Keyframe | Same support/rest pose as sleep_loop end. | APPROVAL_TBD |
| 001 | 100ms | Breakdown | Ears begin rising; body support remains grounded. | APPROVAL_TBD |
| 002 | 200ms | Keyframe | Eyes begin opening; head remains attached. | APPROVAL_TBD |
| 003 | 300ms | Breakdown | Torso lifts from support; weapon remains protected. | APPROVAL_TBD |
| 004 | 400ms | In-between | Hips/knees extend; feet follow a continuous path. | APPROVAL_TBD |
| 005 | 500ms | Keyframe | Upright recovery; ears and eyes readable. | APPROVAL_TBD |
| 006 | 600ms | Recovery | Coat/hair settle; no startled jump. | APPROVAL_TBD |
| 007 | 700ms | Settle | Exact standing/idle destination. | APPROVAL_TBD |

## Approval consequence

If any proposed food prop, rest orientation, support, weapon placement, or Vô Vĩ anchor is rejected, only the affected rows are revised. No frames are generated from this proposal yet.
