# Hunger cue candidate continuity review

Candidate: `miyabi-remediation-20260906-r01-hunger-cue-v1`
Status: `TECHNICAL_PARTIAL_PASS_USER_APPROVAL_PENDING`

## Scope of this candidate

This candidate fixes only the source-layer/identity separation: it places the unchanged identity master on the 160x144 canvas and preserves only the existing food-area pixels from the stable hunger source. No new food, utensil, effect, body redraw, scale, rotation, behavior, or timing was introduced.

## Passes

- Identity body, weapon, feet, palette, and canvas remain unchanged from the identity master.
- Food-area cue stays in its existing authored region and retains per-frame source timing.
- No border alpha; no whole-sprite translation or scale.
- Right-authored storage remains compatible with runtime mirroring.

## Known limitation / not accepted

The identity body does not yet perform the proposed look/restraint gesture. This is deliberate because exact eye/hand choreography is still approval-gated. Therefore this is not a final animation pass and must not replace the stable hunger clip.

## Review result

- Technical narrow-scope check: PASS.
- Motion intent completeness: PENDING.
- User approval: PENDING.
- Stable integration: NOT ALLOWED.
