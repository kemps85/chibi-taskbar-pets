# Taskbar Pet M0 QA Evidence - 2026-08-25

## Scope

Windows primary-display bottom-taskbar vertical slice using only Firefly's
approved human-right animation. Approved asset files were not regenerated.

## Asset checks

- Manifest status: `PASS`.
- Human frames: 164 contiguous RGBA PNGs at 160x144.
- Exact authored durations total 10,950 ms.
- Review videos decode successfully and match their manifest probes.
- SAM is excluded because its canvases and anchors do not yet form one runtime contract.

## Runtime behavior

- Runtime render scale: 1x (160x144 DIP).
- Observed window on the current 125% DPI display: 200x180 physical pixels.
- Position: centred on the primary bottom taskbar with anchor `(64,120)` on the work-area baseline.
- Window extended style observed: `0x8280028`.
- Win32 `WindowFromPoint` probe at the visible pet returned the underlying window, not the pet window: click-through PASS.
- Runtime exited with code 0 through the QA clean-exit route.
- Visual proof: `tmp/taskbar-pet-review/runtime-overlay-proof-1x-final.png`.

## Idle schedule

- Initial/resting pose: authored frame 000.
- Rest between animation plays: 60,000 ms.
- Animation play: one complete 164-frame / 10,950 ms authored sequence.
- Unit coverage checks the rest boundary, every real frame boundary across multiple loops, and return to rest without accumulated drift.

## Commands and results

- `npm test`: 12 passed, 0 failed.
- `npm run smoke`: PASS after the first predecoded frame rendered.
- `npm audit --offline`: 0 vulnerabilities at the time checked.
- `scripts/build_taskbar_pet.ps1`: PASS.
- `scripts/validate_taskbar_pet_package.ps1`: structural package validation PASS; packaged `--smoke` PASS.

## Preliminary performance sample

- Sample: 12.03 seconds after warm-up.
- Electron processes: 4.
- Combined working set: approximately 376.1 MB.
- CPU: approximately 1.57% of total eight-logical-processor capacity (12.6% of one core).
- Process exit: 0.

This short sample is diagnostic only. It exceeds the provisional 200 MB working-set budget but does not replace the ADR-required two clean 10-minute measurements.

## Open release risks

1. The exact generated manifest and 164 runtime PNGs are still untracked, so clean-clone packaging is not reproducible.
2. The full performance exit gate has not been run.
3. Portable/installer release is intentionally deferred until those gates are resolved.
