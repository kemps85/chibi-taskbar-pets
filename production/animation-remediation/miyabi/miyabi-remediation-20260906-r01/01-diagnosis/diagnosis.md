# Miyabi remediation — diagnosis (Gate 2 evidence)

Run: `miyabi-remediation-20260906-r01`

## Evidence boundary

- `OBSERVED`: source PNGs, generated contact sheets, metrics, and current source code were inspected in this run.
- `REPORTED`: the user reports visible holes, jitter, abrupt silhouette changes, and unapproved animation.
- `INFERRED`: causes below are inferred only where the current generator/runtime structure matches the observed output.
- `UNKNOWN`: no user-approved final Miyabi activity reference has been found for the exact eating prop/gesture or the exact sleep/spirit choreography. No candidate is treated as approved.

The old stable-pack `qa.json` PASS is structural evidence only. It does not override the visual defects below.

## Clip inventory

| Clip | Frames actual | Timing | Loop | Canvas | Start/end | Source |
|---|---:|---:|---|---|---|---|
| idle | 8 | 3,600 ms (450 ms each) | loop | 160x144 | frame-000 / frame-007 | `assets/runtime/taskbar-pet/clip-packs/miyabi/v1` |
| walk | 8 | 800 ms (100 ms each) | loop | 160x144 | frame-000 / frame-007 | same |
| hunger_cue | 8 | 1,200 ms (150 ms each) | once | 160x144 | frame-000 / frame-007 | same |
| eat | 12 | 1,920 ms (160 ms each) | once | 160x144 | frame-000 / frame-011 | same |
| sleep_cue | 8 | 1,200 ms (150 ms each) | once | 160x144 | frame-000 / frame-007 | same |
| sleep_enter | 10 | 1,200 ms (120 ms each) | once | 160x144 | frame-000 / frame-009 | same |
| sleep_loop | 12 | 3,000 ms (250 ms each) | loop | 160x144 | frame-000 / frame-011 | same |
| wake | 8 | 800 ms (100 ms each) | once | 160x144 | frame-000 / frame-007 | same |
| spirit_tail | 16 | 2,880 ms (180 ms each) | segmented enter/loop/exit | 160x144 | frame-000 / frame-015 | same |

## Source alpha result

`frame-metrics.json` reports 90/90 Miyabi frames as 160x144 RGBA, with no partial-alpha pixels and no non-zero alpha on the outer canvas border. Therefore, a literal anti-aliased alpha fringe or border matte was **not observed** in this source set. The visible “rỗ” complaint is currently evidenced as disconnected/missing silhouette regions and detached parts, not as proof that every transparent hole is erroneous. Internal gaps must remain possible design gaps until identity review says otherwise.

## Defect register

### D-01 — Walk has detached lower-body fragments

- **Defect ID:** D-01
- **Clip:** `walk`
- **Frame IDs/timestamp:** `frame-000` through `frame-007`; 100 ms per frame, 800 ms loop
- **Observed output:** the light/dark contact sheets show alternating dark strokes below the skirt/feet and small cyan/dark points at the sides. These read as floating limbs or particles instead of a connected contact/pass/airborne walk.
- **Expected output:** a readable walk cycle with explicit contact, passing, and recovery poses; feet remain attached to the body and the weapon remains attached to the hand/body.
- **Evidence:** `01-diagnosis/contact-walk-light-4x.png`, `01-diagnosis/contact-walk-dark-4x.png`; current generator `scripts/build_taskbar_behavior_packs.py` around `draw_walk_cue()` (lines 213–234).
- **Source PNG or runtime:** source PNG and generator output; source-layer defect.
- **Classification:** joint continuity, pose, silhouette, secondary motion.
- **Confidence:** high for the detached fragments; medium for the exact intended foot choreography.
- **Smallest proposed correction:** remove the synthetic detached walk accents and author connected leg/contact poses. Do not change behavior speed or mirror semantics.

### D-02 — Sleep enter rotates/crops the whole sprite and detaches weapon treatment

- **Defect ID:** D-02
- **Clip:** `sleep_enter`
- **Frame IDs/timestamp:** `frame-005` through `frame-009`; 120 ms per frame, 1,200 ms total
- **Observed output:** after the stand/tilt frames, the character becomes a clipped horizontal/partial shape at the bottom/right; a separate dark lump/weapon-like remnant is visible above or away from the body.
- **Expected output:** weight shifts first, then a readable, compact rest pose with support and weapon placement preserved. No body part should disappear because the canvas crop is used as a pose.
- **Evidence:** `01-diagnosis/contact-sleep_enter-light-4x.png`, `01-diagnosis/contact-sleep_enter-dark-4x.png`; inventory bbox changes from `[22,24,106,143]` to `[8,81,111,143]`; generator `make_sleep_enter()` and `body_pose()` (around lines 116–120 and 403–419).
- **Source PNG or runtime:** source PNG; source-layer defect.
- **Classification:** transition, pose, weapon continuity, silhouette.
- **Confidence:** high.
- **Smallest proposed correction:** replace whole-sprite rotation with explicit side-rest key poses and breakdowns on the fixed 160x144 ground contract. Keep the current clip duration unless evidence requires a change.

### D-03 — Sleep loop is not a coherent sleeping silhouette

- **Defect ID:** D-03
- **Clip:** `sleep_loop`
- **Frame IDs/timestamp:** `frame-000` through `frame-011`; 250 ms per frame, 3,000 ms loop
- **Observed output:** the contact sheet shows a thin, clipped horizontal body at the lower/right area with a detached dark lump and intermittent Z marks; support/ground contact is not stable as a compact rest pose.
- **Expected output:** one approved sleep silhouette, stable ground contact, and only small breathing/secondary motion in specified regions. Loop seam must preserve silhouette.
- **Evidence:** `01-diagnosis/contact-sleep_loop-light-4x.png`, `01-diagnosis/contact-sleep_loop-dark-4x.png`; inventory union `[8,81,111,143]`; generator `make_sleep_loop()` around lines 422–429.
- **Source PNG or runtime:** source PNG; source-layer defect.
- **Classification:** pose, ground contact, loop seam, secondary motion.
- **Confidence:** high.
- **Smallest proposed correction:** author a compact rest pose from the identity master, lock support/ground landmarks, and add only bounded breathing/secondary motion.

### D-04 — Wake begins from the broken sleep pose

- **Defect ID:** D-04
- **Clip:** `wake`
- **Frame IDs/timestamp:** `frame-000` through `frame-007`; 100 ms per frame, 800 ms total
- **Observed output:** early frames repeat the clipped horizontal sleep shape; the final standing transition is abrupt and does not show a believable support-to-stand sequence.
- **Expected output:** wake starts at the approved `sleep_loop` end pose, transfers weight through support, rises, and settles at the standing destination.
- **Evidence:** `01-diagnosis/contact-wake-light-4x.png`, `01-diagnosis/contact-wake-dark-4x.png`; generator `make_wake()` around lines 432–450.
- **Source PNG or runtime:** source PNG; source-layer defect.
- **Classification:** transition, pose, joint continuity, recovery.
- **Confidence:** high.
- **Smallest proposed correction:** design wake from the approved sleep-loop end pose; do not assume a time-reversed broken enter is valid.

### D-05 — Eat has disconnected prop/hand/body continuity

- **Defect ID:** D-05
- **Clip:** `eat`
- **Frame IDs/timestamp:** `frame-001` through `frame-011`; 160 ms per frame, 1,920 ms total
- **Observed output:** the body rotates/crops while a dark horizontal object appears at lower-left and a plate remains at far right. The hand, mouth, and prop do not form a stable bite path.
- **Expected output:** one compact, readable bite/tea-like pause using the already implied food-area prop only if that prop is confirmed; hand-to-mouth/prop anchors remain continuous and the end pose can recover.
- **Evidence:** `01-diagnosis/contact-eat-light-4x.png`, `01-diagnosis/contact-eat-dark-4x.png`; generator `draw_eat_cue()` and `make_eat()` around lines 314–338 and 462–478.
- **Source PNG or runtime:** source PNG; source-layer defect.
- **Classification:** prop continuity, pose, joint continuity, transition.
- **Confidence:** high for disconnect; medium for the intended prop because no approval record for the exact food/tea object was found.
- **Smallest proposed correction:** keep the existing prop semantics unchanged until the user confirms them; re-author hand/mouth/prop anchors rather than inventing a new food or effect.

### D-06 — Hunger cue plate/crumbs pop and body response is under-designed

- **Defect ID:** D-06
- **Clip:** `hunger_cue`
- **Frame IDs/timestamp:** `frame-000` through `frame-007`; 150 ms per frame, 1,200 ms total
- **Observed output:** the plate/bowl and crumbs occupy the far-right area (union reaches x=128) while the character is almost static; the cue reads as a detached prop rather than a deliberate glance/restraint gesture.
- **Expected output:** the existing hunger meaning remains, with a controlled cue in which character, hand/face response, and food-area prop appear/disappear intentionally.
- **Evidence:** `01-diagnosis/contact-hunger_cue-light-4x.png`, `01-diagnosis/contact-hunger_cue-dark-4x.png`; generator `draw_hunger_cue()` around lines 286–311.
- **Source PNG or runtime:** source PNG; source-layer defect.
- **Classification:** timing, prop continuity, pose.
- **Confidence:** high for visible separation; medium for exact approved cue gesture.
- **Smallest proposed correction:** preserve behavior semantics and existing prop meaning, lock the prop anchor, and author a small look/hand response. Do not add a new prop.

### D-07 — Vô Vĩ path and segmented seam are not proven continuous

- **Defect ID:** D-07
- **Clip:** `spirit_tail`
- **Frame IDs/timestamp:** `frame-007` through `frame-015`; 180 ms per frame, current segmented enter/loop/exit
- **Observed output:** the contact sheet shows abrupt changes in effect visibility/shape; the sequence visibly thins/disappears and then returns. The current pack is assembled from 12 extracted source frames and arbitrary reverse/reuse indices `[0,1,2,3,4,5,6,7,8,9,10,11,7,5,3,0]`, so exit trajectory is not proven.
- **Expected output:** Vô Vĩ appears from the defined anchor, follows a continuous hover path, and retracts along an explicit path without pop; enter/loop/exit remain atomic under the current runtime contract.
- **Evidence:** `01-diagnosis/contact-spirit_tail-light-4x.png`, `01-diagnosis/contact-spirit_tail-checker-4x.png`; `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layered-animation-qa.json` contains a separate companion path with center/scale/opacity samples; generator `extract_spirit_tail_frames()` and spirit index assembly around lines 482–490 and 687–696.
- **Source PNG or runtime:** source PNG plus generator composition; source/sequence defect.
- **Classification:** trajectory, transition/loop seam, secondary motion.
- **Confidence:** high for lack of proven continuous exit; medium for the exact user-approved Vô Vĩ route.
- **Smallest proposed correction:** use the explicit companion path as a reference, recompose right-authored frames without arbitrary frame reuse, and validate enter/loop/exit at real durations.

### D-08 — Renderer enables smoothing for Miyabi

- **Defect ID:** D-08
- **Clip:** all Miyabi clips at runtime
- **Frame IDs/timestamp:** runtime-dependent; renderer configuration is static
- **Observed output:** **not yet isolated as a fresh Miyabi runtime screenshot** in this run. The code sets `imageSmoothingEnabled = true` for Miyabi.
- **Expected output:** pixel-art source is displayed with hard nearest-neighbor edges; runtime filtering must not be used to conceal source defects.
- **Evidence:** `src/taskbar-pet/renderer.js` lines 53–58; fresh runtime smoke only proves a Firefly frame rendered, not Miyabi visual quality.
- **Source PNG or runtime:** runtime-only configuration; output effect still requires targeted runtime capture.
- **Classification:** runtime-only rendering.
- **Confidence:** high for the code setting; not yet complete for its visible effect on this machine/DPI.
- **Smallest proposed correction:** if targeted runtime capture confirms filtering, change only the smoothing setting to false and run Firefly regression. Do not crossfade or add smoothing elsewhere.

## Gate 2 status

**PASS for evidence-backed prioritization; FAIL for any claim that the animation is repaired.** The minimum source-layer defects and their correction layers are identified. Identity and exact activity choreography remain approval/confirmation work.

## D-08 follow-up — runtime sampling patch

`src/taskbar-pet/renderer.js` was changed in one isolated patch: both characters now use `imageSmoothingEnabled = false` and `imageSmoothingQuality = "low"`, matching the nearest-neighbor contract. The pre-patch file is preserved at `00-baseline/renderer.js.prepatch`. A regression test was added at `tests/taskbar-pet/renderer-contract.test.mjs`; the fresh suite is 38/38 PASS. This resolves the code-level setting defect, but does not approve any Miyabi source clip or prove final visual quality at every DPI.
