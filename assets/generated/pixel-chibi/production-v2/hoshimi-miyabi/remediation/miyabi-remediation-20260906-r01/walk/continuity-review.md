# Walk candidate continuity review

Candidate: `miyabi-remediation-20260906-r01-walk-v1`
Status: **TECHNICAL CANDIDATE — USER APPROVAL PENDING**

## Scope of this candidate

This candidate addresses the confirmed detached walk fragments only. It does not change gameplay speed, behavior selection, canvas, identity master, weapon design, or mirror policy.

- 8 frames × 100 ms = 800 ms.
- Right-authored 160x144; runtime mirrors left.
- Contact/pass cycle uses only connected lower-leg/boot crops from the identity master.
- The synthetic floating dark/cyan walk accents are removed.
- One raised pose is allowed to leave the foot baseline by one pixel; every other frame retains at least one y=143 contact.

## Evidence

- Full light/checker contacts: `contact-light-4x.png`, `contact-checker-4x.png`.
- Lower-leg triplet: `legs-contact-pass-8x.png`.
- Transparent playback: `preview-1x.apng`.
- Duration playback: `preview-light-1x.mp4`; `playback-ffprobe.txt`.
- Candidate manifest/QA/provenance: `manifest.json`, `qa.json`, `provenance.json`.

## OBSERVED

- No detached walk accents remain.
- The body, weapon, hair, and cape silhouette remain stable and connected.
- Frames 000–002 and 004–007 retain y=143 contact; frame 003 is the one-pixel raised/downbeat pose.
- All frames are 160x144 RGBA with zero partial alpha and zero border alpha.
- Foot displacement is bounded to 3 px horizontally and 2 px vertically; no limb teleport is visible in the lower-leg triplet.

## LIMITATION

The current candidate moves only the lower legs/boots. Cape lag, hip/torso weight shift, and weapon secondary response are not yet authored. This is therefore a targeted source-layer candidate, not final animation approval. Adding secondary motion must be a separate bounded pass.

## Decision

- Fragment/silhouette correction: PASS for technical candidate.
- Foot/contact continuity: PASS with one deliberate raised pose.
- Weapon/cape secondary motion: LIMITED/PENDING.
- User approval: PENDING.
- Stable pack integration: NOT PERFORMED.
