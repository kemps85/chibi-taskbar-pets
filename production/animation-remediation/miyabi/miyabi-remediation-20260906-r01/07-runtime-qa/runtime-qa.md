# Miyabi runtime QA

Run: `miyabi-remediation-20260906-r01`

## Scope

This run contains forced-action baseline observations, an isolated nearest-neighbor renderer correction, and candidate-only contract checks. It does not modify the production scheduler or prove natural random behavior. Stable Miyabi/Firefly packs and behavior configuration were not changed.

## Baseline commands and observations

1. `npm.cmd run smoke -- --qa-character=miyabi` from `C:\Users\ASUS\Documents\ChatGPT\Game\src\taskbar-pet`
   - Result: PASS; Miyabi first-frame smoke.
   - Evidence: `npm-smoke-miyabi-final-correct.txt`.

2. `npm.cmd run smoke -- --qa-character=firefly` from the same directory
   - Result: PASS; Firefly first-frame smoke.
   - Evidence: `npm-smoke-firefly-after-renderer-patch.txt`.

3. `npm.cmd test` from the same directory
   - Result: PASS, 38/38, including the renderer nearest-neighbor regression test.
   - Evidence: `npm-test-after-renderer-regression-test.txt` and `test-summary-after-renderer-regression-test.txt`.

4. `npm.cmd run validate:assets` from the same directory
   - Result: PASS, 3/3.
   - Evidence: `npm-validate-assets-after-renderer-patch.txt`.

5. `npm.cmd start -- --qa-character=miyabi --qa-action=sleep_enter --qa-direction=right --qa-exit-after-ms=8000`
   - Result: process exited 0; actual desktop capture collected.
   - Evidence: `runtime-miyabi-sleep-enter-right.png` and `runtime-miyabi-sleep-enter-right-pet-crop.png`.
   - Direct observation: the real transparent taskbar window is present at the expected lower-screen placement, but the stable sleep-enter source is a small clipped/detached-looking pose. This agrees with the source contact sheet; it is not a repaired result.

6. `npm.cmd start -- --qa-character=miyabi --qa-action=walk --qa-direction=left --qa-exit-after-ms=6000`
   - Result: process exited 0; actual desktop capture collected.
   - Evidence: `runtime-miyabi-walk-left.png` and `runtime-miyabi-walk-left-pet-crop.png`.
   - Direct observation: Miyabi loaded in the real taskbar overlay for the forced left action. The screenshot is at real desktop/DPI scale; it does not isolate enough detail to certify the mirror silhouette frame-by-frame.

7. `npm.cmd start -- --qa-character=miyabi --qa-action=spirit_tail --qa-direction=right --qa-exit-after-ms=6000` plus a second 5-second attempt
   - Result: captures collected; owned Electron process trees were stopped after capture because the child outlived the npm wrapper.
   - Evidence: `runtime-miyabi-spirit-tail-right.png` and `runtime-miyabi-spirit-tail-right-2s.png`.
   - Limit: the spirit action was not visually isolatable in the desktop captures. Runtime result remains UNKNOWN from this evidence and is not called pass.

## Isolated renderer correction

The shared renderer was patched minimally so every character uses hard pixel sampling:

- `petContext.imageSmoothingEnabled = false`
- `petContext.imageSmoothingQuality = "low"`

The pre-patch source is preserved at `00-baseline/renderer.js.prepatch`. The regression test is `tests/taskbar-pet/renderer-contract.test.mjs`. Firefly smoke and the full test/asset-validation suite pass after the patch. This correction does not change Firefly assets, timing, behavior, mirror, or scheduling.

## Candidate checks and bounded candidate runtime QA (not stable runtime)

The separate full candidate pack contains untouched stable clips plus bounded candidate `walk`, `hunger_cue`, `eat`, `sleep_cue`, `sleep_enter`, `sleep_loop`, `wake`, and `spirit_tail`. Its manifest remains `CANDIDATE_USER_APPROVAL_PENDING`.

- Candidate structural validation: PASS; all clips present, 160x144 frame size, valid durations/segments, and no border alpha in the candidate checks. The report also records partial alpha in untouched legacy clips and the source-derived spirit companion; this remains a visual-review item, not a blanket alpha pass. Evidence: `candidate-validation-final.txt` and `candidate-spirit-tail-contract.json`.
- Existing `m1-runtime.js` validator and payload builder: PASS in memory only for the candidate payload. Evidence: `candidate-runtime-payload-final.txt` and `candidate-runtime-payload.txt`.
- Post-transition candidate structural check: PASS; 9 required clips, expected counts/durations/segments, and no nonzero border alpha. Evidence: `candidate-validation-post-transition-repair.txt` and `candidate-runtime-payload-post-transition-repair.txt`.
- Candidate review packet: `06-continuity/candidate-review-index.json`, `06-continuity/full-candidate-key-contact-4x.png`, and duration-bearing APNG previews under the candidate pack `previews` directory. The `sleep_enter` frame-004 bridge probe is explicitly rejected and is not in the pack.
- Candidate Electron runtime: bounded QA-only run completed through the real Electron loader using a temporary `main.mjs` candidate-pack override. The candidate manifest itself remained `CANDIDATE_USER_APPROVAL_PENDING`; the temporary loader copy was restored before handoff.
- Candidate right sleep-enter desktop captures: `candidate-runtime-sleep-enter-t1200-pet-crop.png` and `candidate-runtime-sleep-enter-t2900-pet-crop.png`. OBSERVED: candidate is present at the expected taskbar placement and reaches the compact rest drawing.
- Candidate left mirror desktop capture: `candidate-runtime-sleep-enter-left-t1700-pet-crop.png`. OBSERVED: the right-authored candidate is rendered mirrored on the left-facing path; no left asset directory was created.
- Candidate right Vô Vĩ desktop captures: `candidate-runtime-spirit-v3-t1400-pet-crop.png` and `candidate-runtime-spirit-v3-t2800-pet-crop.png`. OBSERVED: the candidate body loads and Vô Vĩ is visible in the later capture. Full enter/loop/exit trajectory still requires playback review, so this is not a visual animation pass.
- The first candidate spirit QA attempt exposed an existing QA-only override bug: `segments: undefined` did not remove segmented data, and the payload still rejected segmented ranges. A temporary QA-only copy changed the payload field to `loopMode: "loop"` and removed `segments`; it was not retained in production source. This is recorded as runtime-QA evidence, not a stable behavior change.
- Candidate visual review: narrow technical checks pass for `walk`, `hunger_cue`, `sleep_cue`, and `spirit_tail`; `hunger_cue` deliberately retains a declared body-gesture limitation, while secondary motion, transition/weapon continuity, playback review, and user approval remain pending. See each candidate `continuity-review.md`.

## Runtime QA status

- Candidate loaded in Electron: **YES, bounded QA-only loader override; stable pack was not redirected**.
- Direction/mirror: **observed** for forced baseline walk-left capture; candidate mirror remains unverified in Electron.
- Candidate direction/mirror: **observed** for the candidate left-facing sleep-enter capture; frame-by-frame mirror parity remains a source review item.
- Actual size/DPI: **observed** at desktop capture; detailed source review remains necessary.
- Natural behavior: **not re-certified**.
- Visual animation acceptance: **FAIL/PENDING** because candidate transition/weapon continuity and duration-accurate playback are not yet accepted, and no candidate has user approval. Runtime loading is not the same as visual acceptance.

