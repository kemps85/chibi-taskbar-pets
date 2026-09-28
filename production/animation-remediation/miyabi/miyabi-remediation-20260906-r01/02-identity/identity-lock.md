# Miyabi identity lock — remediation candidate

Run: `miyabi-remediation-20260906-r01`

## Status

- **TECHNICAL IDENTITY CHECK:** PASS for the inspected local master/reference set.
- **USER APPROVAL:** PENDING.
- No historical filename, old `qa.json` PASS, or existing `approved`/`clean` label is treated as user approval.

## Master and provenance

- Candidate pixel identity master: `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png`.
- Candidate master hash (fresh bytes): `9be92312af1b4d43858548bc16f8e444b4a6e2c4ec28cd8c4e85f4a9b5217e6a`.
- Existing layered source right frame: `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/right/frames/frame-00.png`; it is a reference for the body/companion composition, not an approval of the current activity animation.
- Model references inspected: `tmp/miyabi-model-preview/front.png`, `tmp/miyabi-model-preview/three_quarter.png`.
- Weapon references inspected: `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/hip-rise-crescent-slash-v3/references/weapon-overview.png` and `weapon-drawn-detail.png`.
- The slash experiment directories are reference-only here. No slash choreography, crescent, energy blade, shockwave, or combat animation is used.

## Required identity locks

| Region | Must remain | Evidence/status |
|---|---|---|
| Head | Chibi proportions; tall dark fox ears; face scale stable | `OBSERVED` in local model and pixel master |
| Hair | Long dark hair mass with stable silhouette | `OBSERVED` |
| Clothing | Teal asymmetrical coat/cape, gold trim, white shirt/black tie, black pleated skirt | `OBSERVED`/`REPORTED` by art-direction doc |
| Arm | Viewer-right segmented dark mechanical armored arm with red-ring accent | `OBSERVED` in model refs and pixel master |
| Weapon | Dark curved sheathed katana/scabbard; wrapped handle, angular guard/hardware, shide; no invented blade | `OBSERVED` in weapon refs; exact activity placement remains to be authored |
| Temperament | Composed, restrained idle/activity gestures | `REPORTED` design intent; no large new gestures |
| Palette | Existing dark/teal/gold/red/cyan family; no palette redesign | `OBSERVED` |
| Pixel density | Hard pixel edges and consistent logical pixel scale | `OBSERVED`; no scaling/smoothing as an art fix |

## Allowed simplification at 160x144

- Preserve the identity-bearing silhouette blocks and weapon read.
- Simplify sub-pixel facial, hair, coat-fold, and hardware details that cannot survive the small canvas.
- Do not fill every internal transparent gap: spaces between hair/arm/body/weapon can be intentional.
- Do not add food, effects, slash trails, or accessories to compensate for missing detail.
- Do not change body scale between frames to fake motion.

## Coordinate contract

- Canvas: `160x144` logical pixels.
- Origin: top-left; +X right; +Y down.
- Right-authored master.
- Placement anchor: `(64,120)`; this is **not** the foot coordinate.
- Ground line: `y=143`.
- Runtime mirrors the right master for left direction.
- Existing behavior, random selection, hunger/sleep thresholds, cooldowns, and mirror policy are locked.

## Identity sheet artifacts

- `02-identity/identity-lock-sheet.png`: inspected reference sheet with nearest-neighbor pixel master and model/weapon references.
- `02-identity/identity-master-8x.png`: 8x nearest-neighbor pixel-master view.
- `02-identity/body-master-8x-light.png`: 8x light-background view.
- `02-identity/body-approved-8x-light.png`: existing source comparison view; not an approval claim.
- `02-identity/right-idle-00-8x-light.png`: stable-pack first-frame comparison view.

## Open identity questions before integration

1. Confirm the pixel master above is the identity to use for the repaired activity clips.
2. Confirm the current hunger/eat food-area meaning and whether the existing empty plate/bite-like prop is retained. No new food prop will be invented without confirmation.
3. Confirm the intended rest-side and Vô Vĩ start/return anchor if the current source path is not the approved choreography.
