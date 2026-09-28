# Taskbar Pet M1 random-needs QA evidence

## Scope

- Characters: Miyabi and Firefly only.
- Miyabi appearance is grounded in the local PMX previews and corrected chibi master.
- Right-facing frames are the only stored master; left-facing rendering is a runtime mirror.
- The abandoned Miyabi slash experiments are not referenced by runtime, config, or stable packs.

## Behavior contract

- Weighted seeded random selection; no fixed authored action sequence and no `Math.random` surface.
- Bounded taskbar walking: 96-360 DIP targets, 48 DIP/s, 0.8-2.4 s pauses.
- Hunger accrues over 90 minutes. The 4 s request cue repeats at a data-driven 20-8 s cadence without blocking ordinary behavior; tray `Feed` plays the authored eat one-shot.
- Sleepiness accrues over two awake hours. Sleep runs `sleep_cue -> sleep_enter -> sleep_loop -> wake`; the loop lasts uniformly 8-12 minutes.
- Miyabi `spirit_tail` has explicit enter/loop/exit ranges. Firefly `module_sword` remains active for all 164 authored frames (10.950 s).

## Asset verification

- `assets/runtime/taskbar-pet/clip-packs/miyabi/v1/manifest.json`: PASS.
- `assets/runtime/taskbar-pet/clip-packs/firefly/v1/manifest.json`: PASS.
- Both packs: RGBA, 160x144, transparent border, baseline 143, right anchor (64,120), contiguous zero-padded frames.
- No stored `left` frame directory.
- Stable manifest validation rejects missing mirror, loop-policy, or segmented-range fields.

## Automated verification

- Python behavior-pack rebuild and QA: PASS for both characters.
- Behavior JSON + strict Draft 2020-12 schema: PASS.
- Node syntax checks: PASS.
- `npm test`: 37 passed, 0 failed.
- `npm audit` during clean build: 0 vulnerabilities.
- Development smoke: Miyabi PASS; Firefly PASS.
- Windows unpacked build: PASS.
- Packaged contract validation and packaged smoke: PASS.
- Portable build: `src/taskbar-pet/dist/TaskbarPet-0.1.0-x64.exe`.

## Direct runtime inspection

- Packaged window measured 160x144 DIP at taskbar origin y=870 on the current primary display.
- Miyabi packaged runtime moved from x=880 to x=980 in a five-second sample.
- Firefly packaged runtime moved from x=880 to x=1241 in a five-second sample.
- Both characters were visually inspected in the packaged runtime; the final running selection was restored to Miyabi.

## Remaining gate

- The previous Electron memory sample exceeded the provisional 200 MB budget. This M1 functional pass does not replace the required clean two-run, ten-minute performance gate.
