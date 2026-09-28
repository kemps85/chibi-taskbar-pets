# Miyabi Energy-Surge Slash v4 - QA Evidence

Date: 2026-08-25

## Corrected intent

- Preserve the right-facing kneel, real-world iai grip, rearward saya, standing rise, up-right cut and correctly oriented cutting edge from v3.
- Replace the detached semicircle with one connected, ground-hugging energy surge matching the user's video reference.
- Treat the purple vertical object in the video as the Hollow target being cut, not as part of Miyabi's attack. V4 therefore authors no purple target or impact pillar.

## Reference reading

- The inspected sequence starts with a thin blue line, blooms white, then becomes a dense cyan/ice-blue volume that remains connected to the cut while racing along the ground.
- The leading front is a torn, bright white/cyan crest. Long layered flow bands and a deep-blue frosty wake fill the space behind it.
- The later purple seam belongs to the target Hollow and is excluded from the standalone pet attack.

## Output

- Package: `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/energy-surge-slash-v4/`.
- Canvas: 512x192 RGBA.
- Timeline: 156 frames, 60 FPS, 2.6 seconds.
- Hit-stop: 8 frames / 0.133 seconds.
- Right master plus exact mirrored left set: 156 frames per direction.
- Review video: H.264, 1280x520, 60 FPS, 156 frames, 2.6 seconds.

## Checks run

- Python syntax compile: PASS.
- Deterministic build QA status: PASS.
- Frame count and 512x192 dimensions: PASS.
- Pixel-exact left mirror: PASS, 0 mismatches.
- Transparent canvas border: PASS, 0 non-transparent border pixels.
- Final clean standing frames: PASS.
- Surge connection: PASS; one filled volume runs from hip origin x=145 to far-right front x=486.
- Ground-hugging baseline: y=171.
- Detached ring and overhead ring: absent.
- Impact treatment: white/cyan split flash only; no purple target or pillar authored.
- Review contact sheet visually inspected for thin cut line, explosive bloom, connected surge race, shredded crest and residual blue wake.

## Approval boundary

This v4 is the current visual-review candidate. It is not connected to the Electron runtime until the user approves the review video.
