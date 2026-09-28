# NEXT-SESSION — Miyabi animation remediation

Run: `miyabi-remediation-20260906-r01`

## Current state

- Goal status: **IN PROGRESS** (not complete).
- Current gate: Gate 3 broad identity/semantic/orientation approval is recorded; candidate animation continuity and candidate approval remain open. Gate 2 evidence is complete for the prioritized source defects.
- No stable Miyabi pack, Firefly pack, behavior config, runtime config, generator, or optimizer was changed. The renderer received one isolated nearest-neighbor patch; its pre-patch copy is preserved.
- No commit, push, publish, reset, clean, stash, or packaging was performed.
- No slash v1–v5 asset or choreography was used.

## Baseline and integrity

- Branch: `codex/game-studio-5.6`.
- Baseline manifest: `00-baseline/baseline-manifest.json` (337 file entries).
- Baseline recheck before renderer patch: `00-baseline/baseline-integrity-recheck.txt`; result PASS, 337/337 entries unchanged. Post-patch invariants: `00-baseline/invariants-after-renderer-patch.txt`; result PASS, 336/336 non-renderer entries unchanged.
- Canonical high-level baseline hashes:
  - `assets/runtime/taskbar-pet/clip-packs/miyabi/v1/manifest.json`: `c77290910bb373fecb065c8d513775267bd050de871a1ae174f6fbb9a8e677c3`
  - `assets/runtime/taskbar-pet/clip-packs/firefly/v1/manifest.json`: `1ae2d5411ec1f53a20e09511518a6c6fd9dbb3fca3cd5b1fed76bbb4ce45d318`
  - `assets/data/taskbar_pet_behavior_v1.json`: `e0bc3260ec486cdfe8013ca817a535a67d65e020c294618496e1e4de3a1ec20f`
  - `assets/data/taskbar_pet_runtime_v1.json`: `ef6a240765896f6d4c477fc3d0a89edff1b0e248a129c06faa1743fbb2a82799`
- `src/taskbar-pet/renderer.js`: `6f69e847f03b250e36fb44c6fb2dcb622a89056a25fe31f0b4edaa29cac99799`
- Current renderer after isolated nearest-neighbor patch: `71b179f07d3eb4852027e821b63f17ed91a512e8f316bb05c94a6677a87550b4`.
- Post-candidate recheck: `00-baseline/post-candidate-integrity-recheck.txt`; PASS, 337/337 baseline entries checked, renderer matches the recorded patched hash, and all 240 Firefly entries remain unchanged.

## Candidate progress

- `spirit_tail` candidate: `C:\Users\ASUS\Documents\ChatGPT\Game\assets\generated\pixel-chibi\production-v2\hoshimi-miyabi\remediation\miyabi-remediation-20260906-r01\spirit_tail`
- Candidate contract validation: `07-runtime-qa/candidate-spirit-tail-contract.json`, PASS with 32 frames, 160x144, 2,880 ms, segmented enter/loop/exit.
- Existing runtime payload consumer check: `07-runtime-qa/candidate-runtime-payload.txt`, PASS in-memory only; stable runtime was not redirected.
- Candidate continuity: `spirit_tail/continuity-review.md`; broad Vô Vĩ direction approval is recorded, but actual candidate animation approval remains pending.
- Additional bounded candidates: `walk/continuity-review.md`, `hunger_cue/continuity-review.md`, and `sleep_cue/continuity-review.md`; each passes only its declared technical narrow-scope check and remains pending actual candidate animation approval.
- New bounded `sleep_loop` candidate: `C:\Users\ASUS\Documents\ChatGPT\Game\assets\generated\pixel-chibi\production-v2\hoshimi-miyabi\remediation\miyabi-remediation-20260906-r01\sleep_loop`; 12 x 250 ms, binary alpha, fixed support/weapon, and a 12-pixel trailing-hair secondary-motion mask. Its review is `sleep_loop/continuity-review.md`; candidate animation approval remains pending.
- New bounded `eat` candidate: `C:\Users\ASUS\Documents\ChatGPT\Game\assets\generated\pixel-chibi\production-v2\hoshimi-miyabi\remediation\miyabi-remediation-20260906-r01\eat`; 12 x 160 ms, exact current empty-plate pixels restored, no named food or utensil invented. Its review is `eat/continuity-review.md`; bite/body displacement remains subtle and approval is pending.
- New bounded `sleep_enter` candidate: `C:\Users\ASUS\Documents\ChatGPT\Game\assets\generated\pixel-chibi\production-v2\hoshimi-miyabi\remediation\miyabi-remediation-20260906-r01\sleep_enter`; the old broken late crop is excluded, frames 000..004 are retained, frame 005 is a cleaned generated low-rest breakdown, and frames 006..009 hold the compact rest key. Its review is `06-continuity/sleep-enter-continuity-review.md`; frame 004→005 weapon/pose continuity remains unresolved.
- New bounded `wake` candidate: `C:\Users\ASUS\Documents\ChatGPT\Game\assets\generated\pixel-chibi\production-v2\hoshimi-miyabi\remediation\miyabi-remediation-20260906-r01\wake`; broken stable wake frame-003 is excluded, frame 002 is the generated wake breakdown, and later recovery uses stable frames 004..007. Its review is `06-continuity/wake-continuity-review.md`; boundaries remain pending 1x/duration review.
- Separate full candidate pack: `C:\Users\ASUS\Documents\ChatGPT\Game\assets\generated\pixel-chibi\production-v2\hoshimi-miyabi\remediation\miyabi-remediation-20260906-r01\full-pack\clip-packs\miyabi\v1`; manifest remains `CANDIDATE_USER_APPROVAL_PENDING` and has not been pointed at the stable runtime.
- Candidate frame contracts: `04-frame-specs/walk-source-spec.json`, `04-frame-specs/hunger-source-spec.json`, `04-frame-specs/sleep-cue-source-spec.json`, `04-frame-specs/spirit-tail-source-spec.json`, `04-frame-specs/sleep-loop-source-spec.json`, `04-frame-specs/eat-source-spec.json`, and `04-frame-specs/sleep-enter-frame-005-spec.json`; broad identity/food/rest/Vô Vĩ constraints are now approved, while actual frame/clip acceptance remains pending.
- Failed imagegen probe: `05-generation/failed/sleep_cue-frame-004-imagegen/`; wrong canvas, opaque checkerboard, pose intent not realized.

## Completed evidence

- Source inventory/metrics/contact sheets: `01-diagnosis/clip-inventory.json`, `inventory.csv`, `frame-metrics.json`, `contact-*-light-4x.png`, `contact-*-dark-4x.png`, `contact-*-checker-4x.png`, and 1x/4x strips.
- Diagnosis: `01-diagnosis/diagnosis.md`.
- Identity lock sheet and text: `02-identity/identity-lock-sheet.png`, `identity-master-8x.png`, `identity-lock.md`.
- Motion intent: `03-motion/motion-intent.md`.
- Draft frame contracts: `04-frame-specs/frame-specs.json` (90 rows) and `04-frame-specs/README.md`.
- Runtime evidence and test logs: `07-runtime-qa/runtime-qa.md` and its listed artifacts.
- Renderer patch and regression evidence: `07-runtime-qa/renderer-patch.md`, `00-baseline/renderer.js.prepatch`, `00-baseline/invariants-after-renderer-patch.txt`, and `tests/taskbar-pet/renderer-contract.test.mjs`.
- Fresh post-patch checks: `07-runtime-qa/npm-test-after-renderer-regression-test.txt` (38/38), `npm-validate-assets-after-renderer-patch.txt` (3/3), `npm-smoke-miyabi-final-correct.txt` (Miyabi PASS), and `npm-smoke-firefly-after-renderer-patch.txt` (Firefly PASS).
- Final candidate checks: `07-runtime-qa/candidate-validation-final.txt` (PASS; candidate remains pending) and `07-runtime-qa/candidate-runtime-payload-final.txt` (PASS in-memory contract only).
- Hunger candidate checks: `07-runtime-qa/candidate-validation-with-hunger.txt` and `candidate-runtime-payload-final-with-hunger.txt` (PASS; candidate remains pending); the body gesture is explicitly not accepted yet.
- Sleep-loop candidate checks: `07-runtime-qa/candidate-validation-with-sleep-loop.txt` and `candidate-runtime-payload-final-with-sleep-loop.txt` (PASS; candidate remains pending); the separate imagegen frame-006 probe failed continuity and is explicitly rejected.

## Confirmed source-level defects

- `walk`: detached lower-body/cyan fragments from the current walk cue; D-01.
- `sleep_enter`: whole-sprite rotation/cropping and detached weapon treatment; D-02.
- `sleep_loop`: broken horizontal/rest silhouette and unstable support; D-03.
- `wake`: starts from broken rest pose; D-04.
- `eat`: disconnected hand/prop/body and crop; D-05.
- `hunger_cue`: far-right plate/crumbs with under-designed body response; D-06.
- `spirit_tail`: arbitrary extracted-frame reuse does not prove a continuous Vô Vĩ path; D-07.
- Alpha metrics: no partial-alpha pixels or nonzero border alpha were observed in the 90 stable Miyabi frames. “Rỗ” currently maps to disconnected/missing silhouette evidence, not a blanket instruction to fill transparent gaps.
- Renderer: smoothing was an independent runtime defect and is now patched to hard pixel sampling; regression test passes. Visual effect at desktop DPI is still not a final animation approval.

## Current continuation evidence

- Rechecked the stable sleep/eat/hunger/wake contact sheets and the art-direction contract. The source confirms the broad rest orientation and existing food-area semantics; the user then explicitly approved identity, food semantics, rest orientation, and Vô Vĩ candidate anchors on 2026-09-06.
- Candidate review packet artifacts are indexed at `06-continuity/candidate-review-index.json`, with full key contact `06-continuity/full-candidate-key-contact-4x.png` and duration-bearing per-clip APNGs under the candidate pack `previews` directory. These are review artifacts only; the stable runtime still loads the stable pack.
- The second bounded sleep-enter bridge probe was rejected after direct triplet review because the weapon trajectory was ambiguous/disconnected. Evidence: `06-continuity/sleep-enter-frame-004-breakdown-rejected.md`; no further blind imagegen for this transition until the weapon landmarks/guide are revised.
- Imagegen provenance for the rejected probe is explicit at `05-generation/imagegen-sleep-enter-frame-004-breakdown-provenance.json`; `request_id` and `model` are recorded as null because the tool did not provide them.
- Approval packet: `08-handoff/APPROVAL-REQUEST.md`. A run-local deterministic `hunger_cue` candidate builder was executed; no stable asset was redirected. A bounded `sleep_loop` frame-000 imagegen probe was run after the approval; its opaque checkerboard output was processed into a transparent candidate and remains under technical review.
- Remaining-clip motion proposal: 04-frame-specs/remaining-clips-motion-proposal.md; timing and phase are bounded to the existing manifest, while exact landmarks remain APPROVAL_TBD.
- Coordinate evidence for the current eat/hunger prop separation: 01-diagnosis/eat-hunger-coordinate-compare.png.
- Blocked gate record: `08-handoff/BLOCKED-REASON.md`; resolved by the four user decisions, retained for provenance. It is not evidence that candidate animation is approved.

## User input now recorded

1. `IDENTITY: APPROVE` — use `02-identity/identity-lock-sheet.png` and the body/weapon lock.
2. `FOOD: KEEP` — preserve the current empty plate/food-area semantics; invent no named food or utensil.
3. `REST: APPROVE` — use feet-left/head-right compact rest orientation.
4. `VÔ VĨ: APPROVE` — use the candidate start/return anchors and route in the spirit-tail specification.

`04-frame-specs/frame-specs.json` may now be advanced from direction-blocked to bounded candidate work. Actual candidate clips remain unapproved and must not replace the stable pack. The earlier `sleep_cue/frame-004` probe remains rejected for opaque checkerboard/wrong canvas/pose drift under `05-generation/failed/`.

## Next exact steps after confirmation

1. Revise the `sleep_enter` frame-004 weapon trajectory/landmarks before any further generation; do not use the rejected probe or hide the boundary with filtering/crossfade.
2. Finish bounded continuity review of `eat`, `sleep_enter`, `wake`, `sleep_loop`, `spirit_tail`, and the earlier `walk`/`hunger_cue`/`sleep_cue` candidates at 1x and true durations.
3. If the candidate survives visual review, present static master, key/breakdown frames, 1x previews, contact sheets, change list, and limitations for explicit candidate animation approval.
4. Run candidate Electron QA only through an isolated staging override or after approval; do not point the stable runtime at the pending pack.
5. Only after approval, rehash baseline, scoped-backup affected files, integrate minimal Miyabi-only changes, recheck Firefly/behavior hashes, then run runtime QA.

## Rollback boundary

No integration has happened. The current safe rollback is to stop using the run artifacts; stable/source files are untouched. If integration later occurs, compare each target file against the baseline hash before restoring and stop on any conflict.
















## Continuation checkpoint — 2026-09-06

### OBSERVED this continuation

- User decisions recorded: `IDENTITY APPROVE`, `FOOD KEEP`, `REST APPROVE`, `VÔ VĨ APPROVE`. These remain broad direction approvals, not approval of the candidate sequence.
- Blender 4.1.1 loaded the local Miyabi, weapon, and Vô Vĩ PMX references. The leg probe corrected the actual PMX target names and produced a feet-left crouch/rest reference at `03-motion\native-rest-probe\left-leg\contact.png`.
- A bounded hard-pixel bridge was applied only to candidate `sleep_enter/frame-005.png` and `wake/frame-003.png`. The bridge uses the approved leaning key over the grounded rest base; no alpha blend, smoothing, whole-sprite squash, or whole-sprite rotation was used. Previous candidate frames are preserved under `05-generation\transition-repair\before`.
- Candidate pack was rebuilt and validated: 9 required clips, expected counts/durations/segments, no candidate border alpha. Candidate manifest remains `CANDIDATE_USER_APPROVAL_PENDING`.
- The actual Electron loader rendered the candidate via a temporary QA-only loader override. Right sleep-enter, left mirror, and right Vô Vĩ captures exist under `07-runtime-qa`. The temporary QA source was restored; `src\taskbar-pet\main.mjs` equals its pre-QA backup hash.
- Final stable checks after restoration: full test 38/38 PASS, asset validation 3/3 PASS, stable Miyabi smoke PASS, stable Firefly smoke PASS, post-candidate integrity PASS, Firefly 240/240 entries unchanged. No Electron process remains.

### INFERRED / LIMITS

- The hard-pixel bridges reduce the original full-sprite pop, but the single-frame weapon release/pickup trajectory is not proven as fully continuous. `sleep_enter` and `wake` remain `TECHNICAL_PARTIAL_PASS` pending 1x and duration-accurate review.
- Candidate runtime loading is proven for the bounded captures only; it is not visual animation acceptance and does not certify every clip or natural random behavior.

### Exact next step

1. User reviews the candidate packet: `06-continuity\full-candidate-key-contact-4x.png`, `sleep_enter-transition-current-4x.png`, `wake-transition-current-4x.png`, and the duration-bearing APNG previews.
2. If accepted, record explicit candidate animation approval for the named clips, rehash stable baseline, then integrate only the approved Miyabi candidate and run final runtime QA.
3. If rejected, revise the affected pose guide/landmarks, not the renderer and not Firefly; do not run blind imagegen again for the transition.

### Do not do

- Do not overwrite `assets\runtime\taskbar-pet\clip-packs\miyabi\v1` while candidate approval is pending.
- Do not edit Firefly, behavior semantics, random selection, hunger/sleep timing, mirror policy, or abandoned slash assets.
- Do not delete the rejected bridge probes or source masters.
