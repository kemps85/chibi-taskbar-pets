# Miyabi motion intent — activity clips

Run: `miyabi-remediation-20260906-r01`

These are motion contracts, not approval. Timing totals stay equal to the current stable manifest unless a later frame specification proves a consumer-compatible change. Random selection, needs logic, cooldowns, mirror, and action names are unchanged.

## Global locks

- Right-authored frames only; renderer mirror handles left.
- Canvas `160x144`, ground `y=143`, placement anchor `(64,120)`.
- No whole-sprite squash/stretch or whole-sprite rotation for a pose transition.
- Weapon remains attached to its declared hand/body anchor or is deliberately placed in an explicitly specified rest location; never teleport.
- Secondary motion follows primary motion with a declared delay; no decorative movement without a cause.

## Clip contracts

### idle — 8 × 450 ms, loop, 3,600 ms

- Start/end: same standing destination and same readable silhouette.
- Support: the documented standing support; feet remain on `y=143`.
- Primary: restrained weight/torso or head micro-adjustment only; no full-body vertical breathing translation.
- Weapon: grip/scabbard attachment fixed unless a specific approved micro-shift is specified.
- Secondary: tiny hair/coat response only after primary change, bounded and loop-safe.
- Must not invent: wave, slash, draw, large expression, new effect.

### walk — 8 × 100 ms, loop, 800 ms

- Key poses: contact, down, passing, up, opposite contact, then mirrored progression to loop seam.
- Support: contact foot is stable in each contact pose; no unexplained foot slide.
- Primary: pelvis/torso follow the step; legs are connected drawings, not detached accents.
- Weapon: follows body/hand with small delayed response; length/orientation stays identity-consistent.
- Secondary: coat/hair/arm response trails the step by a small, explicit delay.
- Must not change behavior movement speed or add a combat action.

### hunger_cue — 8 × 150 ms, once, 1,200 ms

- Meaning: retain the existing hunger cue, not a new action.
- Proposed readable arc: neutral start → controlled look/attention toward food area → small restraint/hand response → recover to the next behavior pose.
- Prop: keep existing food-area semantics only; prop anchor/visibility must be explicit. Do not invent food.
- Secondary: none unless tied to the small gesture; no prop pop.

### eat — 12 × 160 ms, once, 1,920 ms

- Meaning: one compact bite/tea-like pause, based on the current art-direction intent and existing food-area cue; exact approved prop is pending confirmation.
- Proposed arc: approach/prepare → lift or hand-to-mouth bite → brief hold → return/recover.
- Hand, mouth, and prop are linked landmarks across every frame.
- The plate/food-area object, if retained, stays in a fixed declared anchor; it cannot remain far away while the hand teleports.
- End pose must connect to the next behavior action.
- Must not add food, steam, magic, slash, or an unapproved utensil.

### sleep_cue — 8 × 150 ms, once, 1,200 ms

- Meaning: restrained drowsiness cue before entering rest.
- Proposed arc: standing neutral → small eyelid/head/attention change → controlled settle toward enter start.
- Hands and weapon remain present and attached.
- Z/sleep symbol, if retained, must have authored appearance timing and not pop as an unrelated detached mark.

### sleep_enter — 10 × 120 ms, once, 1,200 ms

- Start: exact standing end of `sleep_cue`.
- Primary: shift weight/support first; lower pelvis/torso; bend knees/hips; place or protect weapon explicitly; settle into approved rest side.
- Support: declared hip/foot/hand support stays coherent while lowering.
- Secondary: hair/coat follows the body with delay, not an independent teleport.
- End: exact `sleep_loop` start pose.
- Must not rotate the whole sprite inside a fixed canvas or crop it to imply lying down.

### sleep_loop — 12 × 250 ms, loop, 3,000 ms

- Start/end: same compact sleeping silhouette and ground contact.
- Primary: hold the approved rest pose.
- Secondary: small breathing or hair/cloth movement in named regions only, with no ground-contact change.
- Weapon: visible/protected at its declared rest anchor.
- Must not move the whole character vertically or squash the body.

### wake — 8 × 100 ms, once, 800 ms

- Start: exact `sleep_loop` end pose.
- Primary: release support → raise torso/pelvis → recover knees/feet → stand → settle.
- Weapon: remains attached/protected through the support transfer.
- End: exact standing destination used by `idle`/behavior.
- Do not assume simple reverse playback unless every support/weight landmark matches.

### spirit_tail — current stable total 2,880 ms; segmented enter/loop/exit

- Meaning: Vô Vĩ appears → follows a defined hover path → returns to its origin; no combat.
- Start/end: body remains stable; spirit visibility starts/ends at the declared companion anchor.
- Enter: position/scale/opacity move continuously from hidden origin to hover path.
- Loop: bounded hover with explicit spacing and no discontinuous visibility.
- Exit: reverse/return path is authored explicitly; no deletion or arbitrary reused frames.
- Body/weapon: remain unchanged unless an approved secondary response is specified.
- Runtime: preserve atomic segmented semantics; do not alter scheduler behavior.

## Motion gate

A clip is not a candidate pass until its frame-by-frame spec, frame triplets, contact sheet, and duration-accurate playback all agree. This document alone is not evidence of completion.
