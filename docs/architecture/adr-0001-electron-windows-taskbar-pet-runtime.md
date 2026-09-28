# ADR-0001: Electron Windows Taskbar Pet Runtime

## Status

Accepted

## Date

2026-08-25

## Last Verified

2026-08-25

## Decision Makers

- Project owner
- Technical Director

## Summary

The M0 vertical slice will use Electron 43.2.0 to render Firefly's approved
human-right animation as a transparent, click-through Windows taskbar overlay.
M0 is intentionally limited to the primary display's bottom taskbar and the
manifest's exact 164-frame timing; SAM remains out of scope until its mixed
canvas sizes and missing anchor contract are resolved.

## Engine Compatibility

| Field | Value |
|-------|-------|
| **Engine** | Electron 43.2.0 (Windows x64 desktop runtime) |
| **Domain** | Core / UI / Rendering / Animation / Input |
| **Knowledge Risk** | HIGH - current Electron APIs must be verified against Electron 43.2.0 |
| **References Consulted** | Electron `BrowserWindow`, `screen`, and `protocol` API documentation; electron-builder configuration and portable target documentation |
| **Post-Cutoff APIs Used** | `BrowserWindow`, `setAlwaysOnTop`, `setIgnoreMouseEvents`, `screen` display events, `protocol.registerSchemesAsPrivileged`, `protocol.handle` |
| **Verification Required** | Transparent composition, above-taskbar z-order, click-through, display metric repositioning, custom-protocol path containment, and portable-package resource resolution on Windows 11 |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | None |
| **Enables** | M0 human-right taskbar overlay vertical slice |
| **Blocks** | SAM runtime integration until a complete SAM placement contract exists |
| **Ordering Note** | Validate M0 performance and placement before adding another character state, direction, interaction mode, or installer target. |

## Context

### Problem Statement

The repository contains approved Firefly animation assets and review videos but
does not yet contain an executable taskbar-pet runtime. The next milestone must
prove that the approved human animation can play at the correct taskbar position,
remain transparent and click-through, and ship as a runnable Windows artifact.

### Current State

- Node.js 24 is installed locally.
- Electron 43.2.0 and electron-builder 26.15.3 are available in the local npm
  cache and have already been used for a separate Windows Codex-pet application.
- No .NET SDK, Godot editor, or Unity editor is installed.
- The approved manifest reports `PASS` and defines 164 human frames, 10.95
  seconds of exact per-frame durations, a 160 x 144 canvas, a right anchor at
  `(64, 120)`, and no interpolation between distant poses.
- The approved assets and their review videos must not be regenerated or
  redesigned for this slice.

### Constraints

- Windows x64 is the only M0 target.
- M0 supports only the primary display with a bottom, non-auto-hidden taskbar.
- M0 includes only `human-module-sword/right/frames`; left-facing and all SAM
  assets are excluded from the package.
- The manifest's `frame_durations_ms` array is authoritative. A nominal 15 FPS
  value must never replace the individual durations.
- Pixel art must use nearest-neighbour presentation with no crossfade.
- The pet must not take keyboard focus, appear in Alt+Tab, or block clicks.
- Renderer code must not receive Node.js access.

### Requirements

- Render all 164 right-facing RGBA PNG frames in manifest order.
- Hold authored frame 000 for 60 seconds, play the exact 10,950 ms manifest
  timeline once, then repeat that rest/play schedule without cumulative drift.
- Render at 1x: the 160 x 144 authored canvas stays a 160 x 144 DIP window.
- Place anchor `(64, 120)` at the horizontal centre of the primary work area
  and on the primary work area's bottom edge.
- Remain transparent, above the taskbar where the overscan overlaps it, and
  click-through for the entire M0 session.
- Recalculate placement when primary display bounds, work area, or scale factor
  changes.
- Produce an unpacked Windows directory for QA before producing a portable EXE.

## Decision

Use a small Electron 43.2.0 application with strict main/renderer separation.
The main process owns the native window, taskbar placement, asset protocol,
single-instance lifecycle, and tray exit command. The sandboxed renderer owns
only manifest-driven decoding and canvas playback.

The authoritative runtime configuration is
`assets/data/taskbar_pet_runtime_v1.json`, validated by
`assets/data/taskbar_pet_runtime_v1.schema.json`. The approved production
manifest remains unchanged.

### Architecture

```text
approved production manifest + right PNG frames
                    |
                    v
         allowlisted pet-asset:// protocol
                    |
                    v
+---------------- Electron main process ----------------+
| BrowserWindow | primary work-area placement | Tray/Quit |
+---------------------------+----------------------------+
                            |
                 sandboxed renderer boundary
                            |
                            v
+---------------- Electron renderer --------------------+
| manifest adapter -> cumulative timeline -> frame cache |
|                     -> transparent 1x canvas            |
+--------------------------------------------------------+
```

### Key Interfaces

```text
RuntimeConfig
  source.manifestPath
  source.framesDirectory
  source.frameDurationsJsonPointer
  display.{targetDisplay, taskbarEdge, renderScale, anchor}

TaskbarPositioner.place(display, config) -> Rectangle
  baselineY = display.workArea.y + display.workArea.height
  anchorWorldX = display.workArea.x + display.workArea.width / 2
  x = round(anchorWorldX - config.anchor.x * config.renderScale)
  y = round(baselineY - config.anchor.y * config.renderScale)
  width = config.canvas.width * config.renderScale
  height = config.canvas.height * config.renderScale

FrameSequencePlayer.frameAt(elapsedMs) -> frameIndex
  cycleTime = elapsedMs modulo (60,000 + sum(frameDurationsMs))
  frameIndex = 0 while cycleTime is inside the 60-second rest interval
  otherwise binary search over cumulative frame-duration boundaries
```

### Implementation Guidelines

1. Pin Electron `43.2.0` and electron-builder `26.15.3` in both
   `package.json` and `package-lock.json`. Do not copy another repository's
   `node_modules` directory.
2. Create a 160 x 144 `BrowserWindow` with `frame: false`,
   `transparent: true`, `backgroundColor: "#00000000"`, `skipTaskbar: true`,
   `resizable: false`, `movable: false`, `focusable: false`, and
   `hasShadow: false`. Keep `contextIsolation: true`, `nodeIntegration: false`,
   and `sandbox: true`.
3. Put the overlay above the Windows taskbar with
   `setAlwaysOnTop(true, "pop-up-menu")`. Do not use the `screen-saver` level.
4. Make M0 permanently click-through with `setIgnoreMouseEvents(true)`. The
   only supported exit route is the main-process tray menu. Do not add global
   mouse hooks or `uiohook`.
5. Obtain the primary display from Electron's `screen` API. Confirm that its
   work area is reduced at the bottom relative to its bounds; otherwise report
   an unsupported taskbar layout instead of guessing. Reposition on
   `display-metrics-changed`, `display-added`, and `display-removed`.
6. Register `pet-asset` as a standard, secure scheme before `app.ready`, then
   serve files with `protocol.handle`. Resolve every request beneath an
   allowlisted asset root and reject traversal or non-manifest file types.
7. Use one transparent canvas. Disable image smoothing and set CSS
   `image-rendering: pixelated`. Predecode only the active right-facing clip;
   do not create 164 visible DOM image nodes.
8. Drive playback with `requestAnimationFrame` and `performance.now()`. Rest
   on frame 000 for 60 seconds between complete animation plays. Draw
   only when the logical frame index changes. On pause or renderer stall,
   recompute from absolute loop time; never run a catch-up loop and never blend.
9. Package source code in ASAR. Use electron-builder `extraResources` for only
   the approved manifest and the 164 human-right frames. Exclude review videos,
   left-facing frames, keyposes, contact sheets, and every SAM directory.
10. Build and validate the unpacked `win-unpacked` directory before building
    the portable EXE. NSIS and MSIX are later release decisions.

## Alternatives Considered

### .NET 10 WPF

- **Description**: A native WPF transparent window with Win32 taskbar interop.
- **Pros**: Lower expected memory footprint and a strong long-term Windows
  desktop fit.
- **Cons**: No .NET SDK is installed, so M0 would first become a toolchain
  acquisition and setup task.
- **Estimated Effort**: Higher for M0.
- **Rejection Reason**: It delays validation of the already-approved animation.
  It remains the fallback if Electron fails the performance exit gate.

### Native Win32 layered window

- **Description**: Render frames with a custom layered HWND and native message
  handling.
- **Pros**: Maximum control over z-order, per-pixel alpha, and input behavior.
- **Cons**: Significantly more interop, rendering, DPI, and packaging code for
  a human-only slice.
- **Estimated Effort**: Much higher.
- **Rejection Reason**: Complexity is disproportionate to the M0 learning goal.

### Godot 4 desktop window

- **Description**: Use a Godot scene and platform window flags.
- **Pros**: Natural sprite-animation authoring if the project later becomes a
  larger game.
- **Cons**: Godot is not installed, the project engine is not configured, and
  Windows shell behavior still needs platform-specific validation.
- **Estimated Effort**: Higher for M0.
- **Rejection Reason**: Adds engine setup without reducing the Windows-overlay
  risk that M0 is meant to test.

## Consequences

### Positive

- A real Windows vertical slice can be built with the available toolchain.
- Approved frame timing and asset provenance remain the source of truth.
- Main/renderer separation keeps native access out of animation code.
- Pure timeline and placement functions remain portable if the window host is
  replaced later.

### Negative

- Electron has a larger baseline memory and package footprint than WPF or
  native Win32.
- M0 deliberately does not support left-facing playback, secondary displays,
  auto-hidden taskbars, vertical/top taskbars, or direct pet interaction.
- A topmost overlay must be tested against fullscreen applications and Windows
  shell restarts before release scope expands.

### Neutral

- The 60 FPS review video is QA evidence, not a runtime asset. Runtime playback
  uses the authored PNG sequence and exact manifest durations.
- M0 is a production-candidate slice, but acceptance does not automatically
  approve SAM or broader desktop-pet scope.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Electron idle footprint exceeds the utility's budget | Medium | High | Enforce the exit gate before adding scope; keep renderer and assets minimal. |
| Transparent window renders below or behind the taskbar | Medium | High | Use `pop-up-menu` topmost level and verify on the target Windows build. |
| Overlay blocks clicks | Low | High | Keep M0 permanently in ignore-mouse-events mode and test clicks on desktop, app windows, and taskbar controls. |
| Asset protocol escapes its root | Low | High | Canonicalize, allowlist extensions, verify containment, and test traversal attempts. |
| DPI or work-area change misplaces the pet | Medium | Medium | Recompute from Electron display metrics and test live scale/taskbar changes. |
| Approved asset directories remain untracked | High | High | Do not claim reproducible packaging until source assets or a provenance-bearing package input are admitted. |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|---------------|--------|
| Idle CPU | No runtime | 1-3% average on the target machine | <= 3% average during a clean 10-minute run |
| Working set | No runtime | 100-180 MB | <= 200 MB after the first complete loop |
| Cold launch to first visible frame | No runtime | 1-2 seconds | <= 2.0 seconds |
| Timeline drift | No runtime | Absolute-clock selection; no cumulative drift | 0 cumulative drift; selected frame must match manifest time at every sampled checkpoint |
| Runtime asset payload | No runtime | Manifest plus 164 right-facing PNGs | No left, SAM, review-video, or contact-sheet payload in M0 |

### Performance Exit Gate

If any hard budget above is exceeded in two consecutive clean runs after one
bounded profiling and optimization pass, stop Electron scope expansion. Do not
add SAM, interaction, auto-start, or installer work. Record the evidence and
write a superseding ADR for a .NET/WPF host after installing a supported .NET
SDK; preserve the manifest adapter, timeline math, and placement tests as the
migration contract.

## Migration Plan

1. Add and validate the runtime configuration and schema without changing the
   approved production manifest.
2. Implement pure manifest, timeline, and placement modules with unit tests.
3. Implement the secure asset protocol and transparent BrowserWindow.
4. Run unpacked visual, click-through, timing, and performance QA.
5. Only after all M0 gates pass, build and validate the portable EXE.

**Rollback plan**: Remove the Electron host while retaining the runtime config,
manifest contract, and pure tests. Use their interfaces as the acceptance
contract for a WPF or native Win32 replacement.

## Validation Criteria

- [ ] The app loads only the approved `PASS` manifest and 164 human-right PNGs.
- [ ] Frame selection rests on frame 000 for 60 seconds, then matches all 164
      manifest duration boundaries for one 10,950 ms play without crossfade or
      cumulative drift.
- [ ] The 1x sprite anchor remains centred on the primary bottom taskbar after
      display work-area or scale-factor changes.
- [ ] Desktop icons, another application, and taskbar controls remain clickable
      through both opaque and transparent parts of the overlay.
- [ ] No pet window appears in the Windows taskbar or Alt+Tab list and it never
      takes keyboard focus.
- [ ] The unpacked build and portable EXE both resolve their assets without
      accessing paths outside the packaged resource root.
- [ ] All performance budgets pass in two consecutive clean runs.

## SAM Deferral Contract

SAM is explicitly excluded from M0. Its transform-enter frames use a 160 x 144
canvas, while hover, landing, and transform-exit use 128 x 128 canvases. The
current manifest does not provide directional anchors for those SAM clips or a
single runtime placement contract across canvas transitions. SAM work may begin
only after a reviewed data contract defines, for every clip:

- directional anchor coordinates;
- logical canvas and reference origin;
- normalized duration or exact per-frame durations;
- hover and landing translation relative to the taskbar baseline; and
- transition rules that prevent visible jumps between 160 x 144 and 128 x 128.

## GDD Requirements Addressed

Foundational - no GDD requirement. Enables the executable Windows taskbar-pet
vertical slice while constraining M0 to the approved Firefly human-right asset
contract.

## Related

- `production/session-state/NEXT-SESSION.md`
- `assets/generated/pixel-chibi/production-v2/firefly/idle-sequences/production-v2-smooth/firefly-idle-animation-manifest.json`
- `assets/data/taskbar_pet_runtime_v1.json`
- `assets/data/taskbar_pet_runtime_v1.schema.json`
- https://www.electronjs.org/docs/latest/api/browser-window
- https://www.electronjs.org/docs/latest/api/screen
- https://www.electronjs.org/docs/latest/api/protocol
- https://www.electron.build/docs/contents/
- https://www.electron.build/nsis/
