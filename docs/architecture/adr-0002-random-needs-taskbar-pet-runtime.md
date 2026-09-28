# ADR-0002: Random Needs-Driven Taskbar Pet Runtime

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

M1 replaces the fixed rest/play cadence with a deterministic, testable behavior
scheduler for only Miyabi and Firefly. The pet alternates bounded taskbar walks
with short pauses and weighted eligible actions, while real-time hunger and
sleepiness can raise cues or preempt the ordinary cadence at defined safe
boundaries.

## Engine Compatibility

| Field | Value |
|-------|-------|
| **Engine** | Electron 43.2.0 behavior layer over ADR-0001 |
| **Domain** | Core / Animation / Input / UI |
| **Knowledge Risk** | LOW - behavior policy is pure data and deterministic JavaScript; Electron is only the host clock and tray-signal boundary |
| **References Consulted** | `docs/architecture/adr-0001-electron-windows-taskbar-pet-runtime.md`; approved Firefly and Miyabi animation QA manifests |
| **Post-Cutoff APIs Used** | None in the behavior contract |
| **Verification Required** | Seed replay, real-time need accrual, cancellation boundaries, work-area clamping, runtime mirroring, and clip-pack validation |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001 |
| **Enables** | M1 random locomotion, character-specific actions, hunger cue, sleep cycle, and future tray `feed` signal |
| **Blocks** | M1 runtime enablement until both character clip packs satisfy the 160 x 144 right-master contract |
| **Ordering Note** | Implement the clip-pack validator and deterministic pure scheduler before connecting renderer, tray, or wall-clock effects. |

## Context

### Problem Statement

M0 proves a single Firefly animation in a transparent window, but a desktop pet
must not repeat one fixed sequence forever. M1 needs varied movement and actions
without becoming nondeterministic in tests, and it needs hunger and sleepiness
that progress according to elapsed time rather than render frames.

### Current State

- ADR-0001 and `taskbar_pet_runtime_v1.json` define the Electron window host.
- Firefly's approved module/sword sequence already uses a 160 x 144 canvas,
  right anchor `(64, 120)`, 164 frames, and exact per-frame durations.
- Miyabi's existing spirit/companion sequence uses 128 x 128 production frames
  with enter, loop, and exit regions. It must be repacked, not stretched, into
  the new 160 x 144 clip contract with an explicit anchor.
- Existing generated directories commonly contain pre-rendered left frames.
  M1 does not load them; left presentation is an exact runtime mirror of the
  approved right master.
- Required walk, need-cue, and sleep clips are not yet guaranteed to exist for
  both characters. A character remains disabled until its complete pack passes.

### Constraints

- Behavior scope is exactly `miyabi` and `firefly`.
- There is no fixed character-action order.
- Locomotion targets must keep the complete 160 x 144 canvas inside the primary
  work area, including a small edge inset.
- Randomness must be fully seedable and replayable.
- Actions with enter/exit continuity are atomic once their enter phase begins.
- Hunger is never cleared by showing a cue; only a `feed` signal clears it.
- A sleep cycle includes cue, enter, a random 8-12 minute sleep loop, and wake.
- Asset timing remains authored data. The behavior scheduler may choose a clip
  or loop duration, but it may not retime authored frames.

## Decision

Create a pure behavior controller driven by
`assets/data/taskbar_pet_behavior_v1.json`. It consumes elapsed wall time,
current need values, action history, cooldown deadlines, current position, a
validated character clip pack, and one explicit RNG state. It emits commands
such as `walkTo`, `playClip`, `playSegmentedClip`, `showHungerCue`, `sleep`, and
`face`, but never accesses Electron or the DOM directly.

The ordinary cadence is structural rather than scripted:

```text
choose bounded random target
        -> walk facing travel direction
        -> random short pause
        -> weighted choice among currently eligible actions
        -> repeat with a new random target
```

The chosen action is not predetermined. Cooldowns, recent-repeat penalties,
clip availability, and need urgency change the candidate weights at every
decision.

### Architecture

```text
wall clock -----> NeedAccumulator ------------------+
tray feed signal -> EventQueue                      |
display bounds --> BoundedTargetPlanner             v
seed/state ------> BehaviorRandom -> WeightedScheduler -> StateArbiter
validated pack --> ClipRegistry --------------------+       |
                                                           v
                                             renderer command stream
```

### Deterministic RNG Contract

The behavior layer owns one `xorshift32` stream. Its serializable state is:

```text
BehaviorRandomState {
  algorithm: "xorshift32"
  stateUint32: uint32, non-zero
  drawCount: uint32
}
```

`create(seed)`, `nextUint32()`, `nextFloat01()`, `uniformInt(min, max)`,
`uniformFloat(min, max)`, and `weightedIndex(weights)` are the only permitted
random surfaces. Seed zero is remapped to `1831565813`. Tests supply an explicit
seed and assert both emitted commands and final RNG state. Production may inject
a cryptographically generated unsigned 32-bit session seed, which must be logged
with the behavior trace. `Math.random()` is forbidden in the behavior layer.

Draw order is part of the contract: target direction, target distance, pause
duration, weighted action, and action-specific duration consume draws only when
that decision is reached. Rejected or ineligible candidates consume no draws.

### Weighted Scheduler

For each eligible candidate:

```text
effectiveWeight = baseWeight
                * cooldownGate
                * recentRepeatMultiplier
                * needMultiplier

cooldownGate = 0 while cooldown is active, otherwise 1
```

The immediately previous action receives multiplier `0.10`. Any other action in
the three-entry recent history receives `0.50`; actions outside that history
receive `1.00`. This discourages repetition without banning it.

Ordinary actions receive a hunger multiplier that falls linearly from `1.00` at
the hunger cue threshold to `0.50` at maximum hunger. Sleep is added as an
eligible action at sleepiness `0.70`; its weight is `1 + 8 * urgency`, where
urgency rises linearly from zero at `0.70` to one at `0.90`. At `0.90`, sleep is
forced at the next safe boundary rather than randomly selected.

### Needs

Need values are normalized to `[0, 1]` and updated from elapsed real milliseconds,
not render frames. Hunger reaches full after 90 awake or sleeping minutes.
Sleepiness reaches full after 120 awake minutes, freezes while asleep, and resets
to `0.05` after wake. On OS resume or persisted-state reload, apply the complete
non-negative elapsed wall-clock delta and clamp each need to one; do not iterate
one tick per missed frame.

At hunger `0.60`, the hunger cue becomes pending and remains pending until a
`feed` signal is processed. The cue displays for 4 seconds and repeats every 20
seconds at threshold, accelerating linearly to every 8 seconds at maximum
hunger. Showing or hiding the cue never changes hunger. A future tray Feed
command emits `feed`; processing it sets hunger to zero and clears queued or
visible hunger cues.

At sleepiness `0.70`, sleep becomes a weighted candidate. At `0.90`, it becomes
forced. Sleep plays `sleep_cue` once, `sleep_enter` once, loops `sleep_loop` for a
uniform random duration from 8 to 12 minutes, then plays `wake` once. A uniform
range has an expected centre of 10 minutes.

### State Priority And Cancellation

Priority, highest first:

1. `shutdown`
2. active `sleep`
3. forced-sleep request
4. queued `feed` signal
5. hunger cue due
6. display-bounds correction
7. atomic character-specific action
8. walk
9. pause or idle

Cancellation rules:

- `shutdown` cancels everything immediately.
- Once `sleep_enter` begins, sleep is atomic through `wake`; only shutdown may
  cancel it. Hunger continues accruing, its cue is hidden, and it reappears
  after wake if still required. A feed signal received during sleep is queued
  and applied immediately after wake.
- Forced sleep cancels pause, idle, or a visible hunger cue immediately. It may
  stop walking at the current bounded anchor. It waits for a character-specific
  action's exit phase so the character cannot be stranded mid-transformation.
- A feed signal cancels pause, idle, or hunger cue at the next frame boundary.
  It queues behind sleep or an atomic character action.
- A display-bounds change clamps the anchor immediately. It may stop a walk but
  does not interrupt an atomic animation.
- Miyabi's spirit-tail enter/loop/exit and Firefly's module/sword sequence are
  atomic. Ordinary scheduling cannot cancel them.

### Bounded Locomotion

The planner selects uniformly from currently feasible left and right directions,
then selects a travel distance uniformly between 96 and 360 DIP, reduced to the
available distance when near an edge. The full mirrored or unmirrored canvas,
plus a 16 DIP inset, must remain inside the work area. If neither direction can
provide 96 DIP, use the farthest feasible target without leaving bounds.

Movement uses elapsed time at 48 DIP per second and is independent of sprite FPS.
Facing is right for positive travel and left for negative travel. Left visuals
are created by horizontally mirroring the right master around the 160-pixel
canvas; the left anchor is `(160 - rightAnchorX, rightAnchorY)`. After arrival,
pause uniformly for 0.8-2.4 seconds before running the scheduler.

### Character Actions

- **Miyabi**: `spirit_tail` has base weight 2, a 45-second cooldown, and a
  segmented clip: play enter once, loop for a uniformly selected 4-12 seconds,
  then play exit once.
- **Firefly**: `module_sword` has base weight 2 and a 60-second cooldown. It
  plays once using its authored per-frame durations and phases.
- **Both**: `idle` has base weight 5 and no cooldown. Its clip loops for a
  uniformly selected 2-6 seconds. This gives a special action an initial
  `2 / (5 + 2)`, or roughly 29%, share before need and repeat modifiers.

### Clip-Pack Manifest Contract

Each character must provide one separate versioned manifest before it is enabled:

```text
assets/runtime/taskbar-pet/clip-packs/<character>/v1/manifest.json
```

Every pack must conform to this logical structure:

```text
ClipPackManifestV1 {
  schemaVersion: 1
  characterId: "miyabi" | "firefly"
  canvas: { width: 160, height: 144 }
  masterDirection: "right"
  leftRendering: {
    strategy: "mirror-right-at-runtime"
    anchorFormula: "canvas.width-rightAnchor.x"
  }
  clips: {
    <clipId>: {
      framesDirectory: relative path containing only right-master PNGs
      frameNamePattern: "frame-{index:000}.png"
      frameCount: positive integer
      rightAnchor: { x: integer, y: integer }
      timing: exactly one of {
        fps: positive number
        frameDurationsMs: positive integer array with frameCount entries
      }
      loopPolicy: exactly one of {
        { kind: "once" }
        { kind: "loop" }
        { kind: "segmented", enter: inclusive range,
          loop: inclusive range, exit: inclusive range }
      }
    }
  }
}
```

All clips in a character pack use the same 160 x 144 canvas. Padding is allowed;
stretching approved art is not. Only right-master frames are stored. Pre-rendered
left directories are neither inputs nor package payload. Anchors are mandatory
per clip so transitions can preserve the world-space foot point. Exact
`frameDurationsMs` wins over FPS when authored timing is non-uniform.

Required clips for both characters are `idle`, `walk`, `hunger_cue`,
`sleep_cue`, `sleep_enter`, `sleep_loop`, and `wake`. Miyabi additionally
requires segmented `spirit_tail`; Firefly additionally requires once-only
`module_sword`. Runtime enablement fails closed if a required clip, frame,
anchor, timing entry, or loop policy is absent.

## Numeric Tuning Rationale

| Value | Meaning | Rationale |
|-------|---------|-----------|
| `1` | Behavior and clip-pack schema version | First stable contract; breaking changes require a new version. |
| `160 x 144` | Logical canvas | Matches the approved Firefly action and provides one transition-safe canvas for both characters. |
| `1831565813` | Zero-seed replacement | Non-zero constant required by xorshift32; fixed value makes zero-seed tests reproducible. |
| `90 min` | Hunger zero-to-full time | Produces an occasional need during a normal desktop session without constant prompting. |
| `120 min` | Awake sleepiness zero-to-full time | Makes full sleep less frequent than hunger and supports long work sessions. |
| `0` | Initial hunger and sleepiness | Starts a new behavior state fully fed and rested; persisted sessions resume their saved values instead. |
| `0.60` | Hunger cue threshold | First cue appears after about 54 minutes from zero hunger. |
| `4 s` | Hunger cue visible time | Long enough to notice without monopolizing the pet. |
| `20 s` | Hunger cue repeat at threshold | Persistent but not continuous interruption. |
| `8 s` | Hunger cue repeat at maximum hunger | Raises urgency while still leaving movement/action windows. |
| `0` | Hunger after feed | A feed signal fully satisfies the need and clears the cue contract. |
| `0.70` | Sleep weighted-eligibility threshold | Sleep can occur naturally after about 84 awake minutes. |
| `0.90` | Forced-sleep threshold | Guarantees sleep around 108 awake minutes if random selection did not choose it. |
| `0.05` | Sleepiness after wake | Avoids an exact-edge zero while still representing a rested pet. |
| `8-12 min` | Sleep-loop duration | Uniform endpoints centre the expected sleep at 10 minutes. |
| `1` | Sleep base weight | Gives newly eligible sleep a small chance before urgency grows or the forced threshold is reached. |
| `8` | Sleep urgency weight gain | Raises sleep weight from 1 to 9 between eligible and forced thresholds. |
| `3` | Recent-action history length | Remembers enough choices to reduce visible repetition without long-term suppression. |
| `0.10` | Immediate-repeat multiplier | Makes direct repeats rare but still possible when few actions are eligible. |
| `0.50` | Recent-repeat multiplier | Softly diversifies the next few choices. |
| `0.50` | Minimum ordinary-action hunger multiplier | High hunger reduces play actions without freezing the pet before Feed exists. |
| `16 DIP` | Work-area edge inset | Prevents transparent overscan from touching screen edges. |
| `96 DIP` | Preferred minimum walk distance | Makes each movement visually meaningful. |
| `360 DIP` | Maximum walk distance | Prevents long cross-screen travel from dominating the cadence. |
| `48 DIP/s` | Walk speed | A 96-360 DIP move takes about 2-7.5 seconds. |
| `0.8-2.4 s` | Post-walk pause | Creates a readable stop without a fixed pause length. |
| `5` | Idle base weight | Keeps neutral behavior the most common individual outcome. |
| `2` | Character-specific action base weight | Gives an initial special-action share of about 29% against idle. |
| `0 s` | Idle cooldown | Idle remains a safe fallback, with repetition controlled by history penalties. |
| `45 s` | Miyabi spirit-tail cooldown | Prevents the signature effect from appearing on every short movement cycle. |
| `4-12 s` | Miyabi spirit-tail loop duration | Shows the loop clearly while varying its hold time. |
| `60 s` | Firefly module/sword cooldown | Its 10.95-second authored action is long, so it needs a longer recurrence gap. |
| `2-6 s` | Idle-loop duration | Adds breathing room without recreating M0's fixed 60-second rest. |

## Alternatives Considered

### Fixed Scripted Timeline

- **Description**: Author a repeating walk/action/sleep script.
- **Pros**: Very simple playback and easy visual review.
- **Cons**: Predictable, ignores dynamic needs, and violates the no-fixed-action
  requirement.
- **Estimated Effort**: Lower initially.
- **Rejection Reason**: It does not produce pet-like behavior.

### Unseeded Random Timers

- **Description**: Use `Math.random()` and independent timers in the renderer.
- **Pros**: Minimal code.
- **Cons**: Nondeterministic tests, race-prone cancellation, and unreplayable bug
  reports.
- **Estimated Effort**: Lower initially, higher debugging cost.
- **Rejection Reason**: Fails maintainability and testability criteria.

### Utility-AI Scoring Without Structural Cadence

- **Description**: Score every possible state continuously and switch to the
  highest score.
- **Pros**: Highly reactive and extensible.
- **Cons**: More tuning complexity, action thrashing risk, and less predictable
  animation continuity for only two characters.
- **Estimated Effort**: Higher.
- **Rejection Reason**: Weighted choice plus explicit priorities is simpler and
  sufficient for M1.

## Consequences

### Positive

- Behavior is varied in production and exactly replayable in tests.
- Need progression is independent of FPS and renderer stalls.
- Asset, behavior, and window-host responsibilities remain separated.
- A single right-master pack halves directional frame payload and prevents
  left/right art drift.

### Negative

- Both characters need new or repacked walk, cue, and sleep assets before M1 can
  be fully enabled.
- Persisted time and queued events require explicit state serialization.
- The scheduler needs trace logging to diagnose why an action was eligible or
  suppressed.

### Neutral

- Hunger cue presentation is persistent/repeating, but feeding remains an
  external signal; the tray UI is deliberately implemented later.
- M1 continues using ADR-0001's primary bottom taskbar limitation.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Required clip pack is incomplete | High | High | Fail closed per character and report every missing clip/anchor/timing field. |
| Repeated actions still feel mechanical | Medium | Medium | Capture seeded traces and tune weights/cooldowns without changing scheduler semantics. |
| Wall clock jumps backward or forward | Medium | Medium | Treat negative delta as zero; apply positive delta once and clamp needs to one. |
| Sleep strands a character mid-action | Low | High | Enforce atomic enter/exit boundaries and forced-sleep queuing. |
| Runtime mirror shifts the foot anchor | Medium | High | Derive left anchor from canvas width and assert invariant world anchor in tests. |
| Hunger cue becomes spammy | Medium | Medium | Bound repeat interval between 20 and 8 seconds and clear only on Feed. |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|---------------|--------|
| Scheduler work | Fixed timeline | One small weighted selection per action cycle | Under 1 ms per decision on target hardware |
| Need update | Not present | Constant-time elapsed-delta calculation | Under 0.1 ms per update |
| Behavior memory | Not present | State, history, cooldowns, trace, RNG | Under 1 MB excluding frame assets |
| Frame payload | Right Firefly action only | One validated right-master pack per enabled character | No packaged left-frame duplication |

## Migration Plan

1. Validate this behavior config and build pure RNG, needs, target-planner,
   scheduler, and state-arbiter tests.
2. Author or repack Miyabi and Firefly into separate 160 x 144 right-master clip
   packs; do not modify approved source assets.
3. Enable one character only after every required clip passes contract checks.
4. Connect command output to the existing Electron renderer and main-process
   tray signal boundary.
5. Run long seeded simulations, live taskbar QA, and real 8-12 minute sleep QA.

**Rollback plan**: Disable `taskbar_pet_behavior_v1.json` and return to the
ADR-0001 M0 cadence. M0 runtime files remain unchanged by this decision.

## Validation Criteria

- [ ] Same config, initial state, event stream, elapsed deltas, and seed produce
      identical commands, choices, and final RNG state.
- [ ] Ten thousand simulated action decisions never choose an ineligible or
      cooldown-blocked action and never leave the canvas outside work bounds.
- [ ] Immediate and recent repeat multipliers match the documented formula.
- [ ] Hunger and sleepiness match elapsed real time across renderer stalls and
      OS resume.
- [ ] Hunger cue repeats until Feed and clears only when Feed is processed.
- [ ] Sleep always orders cue -> enter -> 8-12 minute loop -> wake and respects
      cancellation rules.
- [ ] Miyabi spirit-tail always orders enter -> loop -> exit.
- [ ] Firefly module/sword uses its exact authored frame durations.
- [ ] Left playback uses no left files and preserves the right-master world
      anchor through exact horizontal mirroring.
- [ ] Each enabled character has a complete validated 160 x 144 clip pack.

## GDD Requirements Addressed

Foundational - no GDD requirement. Enables M1 autonomous taskbar-pet behavior
for Miyabi and Firefly.

## Related

- `docs/architecture/adr-0001-electron-windows-taskbar-pet-runtime.md`
- `assets/data/taskbar_pet_behavior_v1.json`
- `assets/data/taskbar_pet_behavior_v1.schema.json`
- `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/animation-state-v3.json`
- `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layered-animation-qa.json`
- `assets/generated/pixel-chibi/production-v2/firefly/idle-sequences/production-v2-smooth/firefly-idle-animation-manifest.json`
