# Miyabi Traveling Energy-Blade Slash v5 - QA Evidence

Date: 2026-08-25

## Corrected intent

- Remove the accidental second sword completely.
- Replace the water-hose silhouette with one curved, pointed, asymmetric dao-like energy-blade head.
- Treat the energy between Miyabi and the head as delayed afterimage only: faint at the slash origin and increasingly visible toward the moving head.
- Keep the effect white/cyan/ice-blue/deep-blue only; no purple Hollow effect.

## Output

- Package: `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/energy-blade-slash-v5/`.
- Canvas: 512x192 RGBA.
- Timeline: 156 frames, 60 FPS, 2.6 seconds.
- Right master plus exact mirrored left set: 156 frames per direction.
- Review video: H.264, 1280x520, 60 FPS, 156 frames, 2.6 seconds.

## Checks run

- Python syntax compile: PASS.
- Deterministic generated QA status: PASS.
- Frame count and 512x192 dimensions: PASS.
- Pixel-exact left mirror: PASS, 0 mismatches.
- Transparent canvas border: PASS, 0 non-transparent border pixels.
- Final clean standing frames: PASS.
- Original-blade erase mask: 10,030 alpha pixels removed; 0 residual alpha pixels remain in the source blade corridor.
- Nearest-neighbour erasure zoom visually inspected: the after panel contains only hand/guard and an empty transparent blade corridor.
- Final source preview visually inspected: exactly one procedural katana blade.
- Dao head: curved, pointed, asymmetric; no vertical cap.
- Trail: maximum four irregular cyan ribbons plus three detached navy streaks; no uniform filled wedge.
- Visibility gradient: mean peak alpha 23.768 at origin versus 49.68 near the head.
- Contact-sheet close-up visually inspected for a sharp moving head, negative space between ribbons and delayed head-first fade.

## Approval boundary

This v5 is the current visual-review candidate. It is not connected to the Electron runtime until the user approves the review video.
