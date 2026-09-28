# Taskbar Pet - Next Session

Continue in `C:\Users\ASUS\Documents\ChatGPT\Game` and follow the root `AGENTS.md`.

## Current state

### M1 random Miyabi + Firefly runtime (current)

- M1 now supersedes the fixed M0 one-minute idle schedule for normal runtime behavior.
- The active Windows runtime under `src/taskbar-pet/` supports Miyabi and Firefly only.
- Default/last restored character: Miyabi. Tray commands switch Miyabi/Firefly, Feed the pet, or Quit.
- Pets choose bounded left/right targets, walk, pause, and select eligible actions by seeded weighted random. There is no fixed action sequence.
- Only right-facing sprite frames are stored. Left-facing movement is an exact runtime mirror with the world anchor kept stable.
- Needs are elapsed-time driven:
  - hunger fills in 90 minutes; a 4-second request cue repeats every 20 to 8 seconds without freezing the random scheduler; Feed plays `eat`;
  - sleepiness fills over two awake hours; sleep is cue -> lie down -> sleep loop for 8-12 minutes -> wake.
- Character actions:
  - Miyabi: corrected model-grounded chibi plus segmented `spirit_tail` enter/loop/retract;
  - Firefly: full 164-frame `module_sword` action with authored 10.950-second timing.
- Stable runtime packs:
  - `assets/runtime/taskbar-pet/clip-packs/miyabi/v1/`
  - `assets/runtime/taskbar-pet/clip-packs/firefly/v1/`
- Current deliverables:
  - unpacked: `src/taskbar-pet/dist/win-unpacked/TaskbarPet.exe`
  - portable: `src/taskbar-pet/dist/TaskbarPet-0.1.0-x64.exe`
- Current verification: 37 Node tests PASS, strict behavior schema PASS, both stable packs PASS, development smoke PASS for both characters, packaged contract/smoke PASS, and both characters visually inspected moving in the packaged runtime.
- QA evidence: `production/qa/evidence/taskbar-pet-m1-random-needs-2026-08-25.md`.

- The M0 Windows taskbar overlay vertical slice is implemented under `src/taskbar-pet/` with Electron 43.2.0.
- Runtime contract: `assets/data/taskbar_pet_runtime_v1.json` and matching schema.
- Architecture decision: `docs/architecture/adr-0001-electron-windows-taskbar-pet-runtime.md`.
- Windows build helpers:
  - `scripts/build_taskbar_pet.ps1`
  - `scripts/validate_taskbar_pet_package.ps1`
- Current verified unpacked executable:
  - `src/taskbar-pet/dist/win-unpacked/FireflyTaskbarPet.exe`
  - Build output is ignored by Git and must be rebuilt locally.
- The user requested the pet at half the original runtime size:
  - runtime is now 1x, 160x144 DIP;
  - verified as 200x180 physical pixels on this 125% DPI display;
  - right anchor `(64,120)` remains centred on the taskbar baseline.
- Idle schedule requested by the user:
  - hold authored frame 000 for 60 seconds;
  - play the complete 10.95-second, 164-frame human idle animation once;
  - return to frame 000 and wait another 60 seconds;
  - schedule uses an absolute monotonic clock, so it does not accumulate interval drift.
- M0 stays transparent, topmost, hidden from the taskbar, non-focusable, and click-through. Quit remains available from the tray.
- Final checks in this session:
  - 12 Node tests passed;
  - development smoke passed after the first predecoded authored frame rendered;
  - `win-unpacked` build passed structural validation and packaged smoke;
  - runtime window was visually inspected at 1x and a Win32 hit-test probe confirmed click-through;
  - QA evidence: `production/qa/evidence/taskbar-pet-m0-2026-08-25.md`.

## Miyabi final-blow slash v1

- A separate, non-destructive remake of the supplied Miyabi final-blow cut was built at:
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/final-blow-slash-v1/`
- The approved Miyabi body from `layered-v6-clean` remains unchanged. The new attack uses procedural VFX layers on a `288x160` transparent overscan canvas.
- Timing is `132` authored PNG frames at `60 FPS` (`2.2s`): hilt glow, charge, swing flash, `0.133s` hit-stop, cyan/teal crescent and shards, residual fade, then 15 completely clean idle frames.
- Right-facing is the master; all 132 left-facing frames are exact horizontal mirrors with matching frame order.
- Review media:
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/final-blow-slash-v1/video/miyabi-final-blow-slash-review.mp4`
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/final-blow-slash-v1/video/miyabi-final-blow-contact-sheet.png`
- Rebuild script: `scripts/build_miyabi_final_blow_slash.py`.
- QA evidence: `production/qa/evidence/miyabi-final-blow-slash-v1-2026-08-25.md`.

## Miyabi forward-crescent slash v2 (rejected)

- User correction: Miyabi must drop to one knee, visibly brace/charge, then release exactly one semicircular slash projectile forward. The old circular-overhead v1 is retained only for comparison.
- Current output:
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/final-blow-slash-v2/`
- Local appearance reference was inspected from `C:\Users\ASUS\Downloads\qOXyji3wYu`:
  - `星见雅.pmx`: 27,086 vertices, 436 bones;
  - `武器.pmx`: 4,008 vertices, 17 bones;
  - the PMX/model files were not copied into the project output and are not a runtime dependency.
- The model-grounded pose now matches the teal coat, black pleated skirt, asymmetrical armored right arm, dark mechanical katana/scabbard, and cyan ribbon/accent language.
- Hand/weapon rules:
  - charge: right hand grips the hilt; left hand stabilizes the scabbard; neither hand touches the blade;
  - release: exactly one drawn sword in the right hand and one empty scabbard in the left hand; no duplicate hilt or second sword.
- Animation: `156` frames at `60 FPS` (`2.6s`) on a transparent `384x160` overscan canvas.
- Timing: 0.15s standing lead-in, 0.15s kneel transition, 0.617s readable brace, one wave launch, 0.133s hit-stop, forward travel/fade, standing recovery, then 15 exact clean-idle frames.
- Charge and release character top both resolve to y=8 with `0 px` scale delta; the wider `176x128` pose layer preserves the full weapon without shrinking Miyabi.
- Review media:
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/final-blow-slash-v2/video/miyabi-forward-crescent-slash-review.mp4`
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/final-blow-slash-v2/video/miyabi-forward-crescent-contact-sheet.png`
- Rebuild script: `scripts/build_miyabi_forward_crescent_slash.py`.
- QA evidence: `production/qa/evidence/miyabi-forward-crescent-slash-v2-2026-08-25.md`.

The user rejected v2 because Miyabi faced the wrong way, the body did not read as a kneel-to-standing hip cut, and the weapon handling/design was inaccurate. Keep it only as historical comparison.

## Miyabi hip-rise crescent slash v3 (rejected VFX)

- Current output:
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/hip-rise-crescent-slash-v3/`
- Motion was re-grounded against real ZNKR/AJKF iaido guidance, using the upward `gyaku-kesa` path from 7 o'clock to 1 o'clock:
  - charge faces screen-right, kneels on one knee, handle forward/right and saya rearward/left;
  - right hand grips the handle at the guard while the left hand controls the saya mouth and performs sayabiki;
  - Miyabi rises to standing and finishes with the right fist above/right of the right shoulder;
  - the bright cutting edge is now on the upper-left leading side of the up-right blade, with the dark serrated spine on the lower-right trailing side.
- Weapon visuals are grounded in the user's close-up references: industrial guard and pommel, dark wrapped handle, fingerprint/eye details, white shide and long dark scabbard.
- Animation: `156` frames at `60 FPS` (`2.6s`) on a transparent `512x192` canvas.
- Exactly one large vertical `)` half-moon appears at the far right, open to the left, with long cyan/white streaks connecting from the hip; its lower tip reaches y=168 near the ground line.
- Right-facing is the authored master; all left-facing frames are exact horizontal mirrors.
- Review media:
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/hip-rise-crescent-slash-v3/video/miyabi-hip-rise-crescent-slash-review.mp4`
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/hip-rise-crescent-slash-v3/video/miyabi-hip-rise-keyframe-contact-sheet.png`
- Rebuild script: `scripts/build_miyabi_hip_rise_crescent_slash.py`.
- QA evidence: `production/qa/evidence/miyabi-hip-rise-crescent-slash-v3-2026-08-25.md`.

The user accepted neither the detached half-moon nor its interpretation. The pose/weapon corrections remain useful, but the reference attack is a continuous ground-hugging energy surge rather than a separate `)` projectile.

## Miyabi energy-surge slash v4 (rejected VFX)

- Current output:
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/energy-surge-slash-v4/`
- V4 preserves the corrected v3 pose and weapon handling, including the real-world iaido grip, rearward saya, rise from one knee, and correctly oriented cutting edge.
- The VFX was rebuilt from frame-by-frame inspection of the user's supplied video segment:
  - a thin initial blue cut line;
  - a white-hot bloom at the blade/hip;
  - one dense, continuous white/cyan/ice-blue surge connected from Miyabi to the far-right front;
  - a widening ground-hugging volume with deep-blue wake, layered flow bands, shredded leading crest, frost ripples and shards;
  - a white/cyan split flash and blue residual wake.
- The detached `)` ring is completely removed.
- Purple is not part of Miyabi's effect: it belongs to the Hollow target in the video, so v4 contains no invented purple target or purple impact pillar.
- Animation: `156` frames at `60 FPS` (`2.6s`) on a transparent `512x192` canvas.
- Right-facing is the authored master; all left-facing frames are exact horizontal mirrors.
- Review media:
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/energy-surge-slash-v4/video/miyabi-energy-surge-slash-review.mp4`
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/energy-surge-slash-v4/video/miyabi-energy-surge-keyframe-contact-sheet.png`
- Rebuild script: `scripts/build_miyabi_energy_surge_slash.py`.
- QA evidence: `production/qa/evidence/miyabi-energy-surge-slash-v4-2026-08-25.md`.

The user rejected v4 because its flat filled triangle, parallel lines and vertical front cap read as a water hose rather than a sword cut. V4 also exposed a source-preprocessing error that left the original generated blade beside the procedural blade.

## Miyabi traveling energy-blade slash v5 (abandoned)

- Current output:
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/energy-blade-slash-v5/`
- The double-blade source bug is fixed. The complete original generated blade is erased after the non-50% pose-sheet split, then exactly one corrected procedural katana blade is added. The erasure corridor reports 0 residual alpha pixels.
- The energy attack now separates into:
  - a curved, pointed, asymmetric dao-like white/cyan energy-blade head traveling screen-right;
  - at most four irregular cyan ribbons and three detached deep-blue streaks following behind;
  - a left-to-right visibility gradient: faint/thin at the hip origin, progressively more opaque and brighter immediately behind the moving head;
  - head-first fade followed by delayed ribbon dissipation.
- Removed: vertical front cap, solid cyan triangle, uniform water-jet fill, ruler-like equal streaks, purple/Hollow effects and detached rings.
- Animation: `156` frames at `60 FPS` (`2.6s`) on a transparent `512x192` canvas.
- Right-facing is the authored master; all left-facing frames are exact horizontal mirrors.
- Review media:
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/energy-blade-slash-v5/video/miyabi-energy-blade-slash-review.mp4`
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/energy-blade-slash-v5/video/miyabi-energy-blade-keyframe-contact-sheet.png`
  - `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/energy-blade-slash-v5/source/release-blade-erasure-zoom.png`
- Rebuild script: `scripts/build_miyabi_energy_blade_slash.py`.
- QA evidence: `production/qa/evidence/miyabi-energy-blade-slash-v5-2026-08-25.md`.

The user explicitly abandoned this Miyabi slash direction. Do not revise, integrate or resume v1-v5 unless the user later asks to restart it.

## Known limits and next work

- M0 supports only the primary display with a visible bottom taskbar.
- SAM remains deferred: its clips mix 160x144 and 128x128 canvases and do not yet define a complete anchor/placement contract.
- The required generated manifest and 164 PNG inputs are still untracked; a clean clone cannot reproduce the package until those exact approved inputs are admitted to version control or a versioned asset package.
- Preliminary 12-second sampling measured about 376 MB combined working set across four Electron processes. This exceeds the provisional 200 MB budget, but it is not the required two clean 10-minute gate runs. Do not expand Electron scope before completing that gate or revising the host decision.
- M1 functional/runtime QA is complete, but the two clean 10-minute performance gate runs are still outstanding.

## Resume instruction

The Miyabi slash experiment is abandoned and has no current review candidate. Do not wire v1-v5 into the Electron runtime and do not continue this direction unless the user explicitly restarts it. M1 random Miyabi + Firefly behavior is the active baseline. If no new feature is requested, run the full performance gate before SAM, autostart, or installer work.
