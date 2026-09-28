# Miyabi candidate animation review — remediation r01

Status: `TECHNICAL CHECKS PASS` / `ANIMATION REVIEW PENDING` / `USER APPROVAL PENDING` / `STABLE INTEGRATION NOT ALLOWED`

## Scope of the recorded approval

The user approved the identity lock, kept the current empty-plate semantics, approved the feet-left/head-right rest orientation, and approved the Vô Vĩ candidate anchors. This does **not** approve these generated candidate clips for stable integration.

## Candidate packet

- Full candidate pack: `C:\Users\ASUS\Documents\ChatGPT\Game\assets\generated\pixel-chibi\production-v2\hoshimi-miyabi\remediation\miyabi-remediation-20260906-r01\full-pack\clip-packs\miyabi\v1`
- Key contact sheet: `C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\06-continuity\full-candidate-key-contact-4x.png`
- Review index and hashes: `C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\06-continuity\candidate-review-index.json`
- Per-clip duration-bearing APNG previews: candidate pack `previews` directory.

## Review flags

- `walk`, `hunger_cue`, `sleep_cue`, and `spirit_tail`: bounded candidates retained with their declared limitations; candidate animation approval is pending.
- `eat`: current empty plate pixels are restored exactly; no food/utensil is invented. Bite/body displacement remains subtle and needs animation review.
- `sleep_loop`: compact rest key is stable across the loop with a small trailing-hair secondary-motion mask; no breathing motion is invented. Review ground contact and seam.
- `sleep_enter`: old detached/cropped late source frames are excluded. Frame 005 now uses a hard-pixel segmented bridge built from the approved leaning key over the grounded rest base. The rejected imagegen bridge remains excluded; the weapon release is still a review item rather than a claimed solved trajectory.
- `wake`: the broken stable rest crop is excluded; frame 003 now uses a hard-pixel lift bridge and later recovery frames remain bounded. Review rest-to-support and weapon pickup continuity at the boundaries.

## Validation

- Candidate structural validator: PASS; expected clip counts/durations/segments and zero nonzero border alpha in the candidate check. Evidence: `07-runtime-qa\candidate-validation-post-transition-repair.txt`.
- Runtime payload contract: PASS in memory only; stable runtime was not redirected. Evidence: `07-runtime-qa\candidate-runtime-payload-post-transition-repair.txt`.
- Stable tests: `npm.cmd test` 38/38 PASS; asset validation 3/3 PASS; Miyabi and Firefly smoke PASS after the isolated nearest-neighbor renderer patch.
- Stable baseline recheck: PASS; Firefly 240 entries unchanged. Evidence: `00-baseline\post-candidate-integrity-recheck.txt`.
- Blender pose evidence: local PMX identity/weapon loaded; corrected leg-target discovery and feet-left crouch reference are preserved under `03-motion\native-rest-probe\README.md` and `left-leg\contact.png`.
- Candidate runtime evidence: the real Electron loader rendered the candidate through a temporary QA-only manifest override; right sleep-enter, left mirror, and right Vô Vĩ desktop captures are under `07-runtime-qa`. The temporary `main.mjs` QA patch was restored before handoff; it is not a production change.

## Required decision before integration

Review the actual candidate sequence at 1x and true clip durations. In particular inspect the repaired sleep-enter and wake triplets and the weapon handoff. If that bridge is not accepted, do not approve the full pack; revise its pose guide/landmarks before any more generation. No stable file may be changed while this status remains pending.
