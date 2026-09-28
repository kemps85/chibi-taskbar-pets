# Sleep-cue candidate continuity review

Candidate: `miyabi-remediation-20260906-r01-sleep-cue-v1`
Status: **TECHNICAL CANDIDATE — USER APPROVAL PENDING**

## Scope of this candidate

This candidate addresses one issue only: the current cue's disconnected/synthetic Z treatment and weak drowsy read. It keeps the identity master, weapon, feet, canvas, anchor, and timing unchanged.

- 8 frames × 150 ms = 1,200 ms.
- Right-authored 160x144; runtime mirrors left.
- Frames 000–001: standing hold.
- Frames 002–005: controlled eyelid closure with a three-pixel ear-tip softening.
- Frames 006–007: open-eye recovery to the standing destination.
- No plate, food, Z symbol, breath effect, slash, or new prop.

## Evidence

- Full light/checker contacts: `contact-light-4x.png`, `contact-checker-4x.png`.
- Approach triplet: `triplet-approach-4x.png`.
- Recovery triplet: `triplet-recover-4x.png`.
- Transparent playback: `preview-1x.apng`.
- Candidate manifest/QA/provenance: `manifest.json`, `qa.json`, `provenance.json`.

## OBSERVED

- Body silhouette, weapon grip, feet baseline, and placement remain stable across all frames.
- Eye cue reads as neutral → half-lidded → closed → recovered without a detached overlay.
- The candidate has no partial alpha and no border alpha.
- No limb or weapon teleport was observed in the two triplets.

## LIMITATION

The candidate has no explicit shoulder/cape secondary motion; the only secondary response is the bounded ear-tip softening. It is therefore a technical cue candidate, not a final animation approval. If Astra requires a visible shoulder settle, it must be specified before adding pixels.

## Decision

- Identity/weapon continuity: PASS for candidate.
- Alpha/placement: PASS for candidate.
- Cue readability: PASS for technical candidate.
- Secondary motion completeness: LIMITED/PENDING.
- User approval: PENDING.
- Stable pack integration: NOT PERFORMED.
