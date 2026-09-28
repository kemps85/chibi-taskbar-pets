# Miyabi Final-Blow Slash v1 - QA Evidence

Date: 2026-08-25

## Scope

- Recreate the feel of the supplied Miyabi final-blow cut as a pixel-chibi taskbar-pet attack.
- Preserve the approved `layered-v6-clean` Miyabi body and weapon pixels.
- Build the attack in a separate output directory with transparent overscan, deterministic right/left assets, and review media.

## Result

- Output: `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/final-blow-slash-v1/`
- Canvas: `288x160` RGBA.
- Timeline: 132 frames at 60 FPS, 2.2 seconds.
- Hit-stop: 8 frames, 0.133333 seconds.
- Directional assets: 132 right-facing frames and 132 exact mirrored left-facing frames.
- Clean recovery: frames 117-131 contain only the immutable body on a transparent canvas.
- Review video: H.264, 1280x520, 60 FPS, 132 frames, 2.2 seconds.

## Checks run

- `py -3 -m py_compile scripts/build_miyabi_final_blow_slash.py`: PASS.
- Full deterministic rebuild from `layered-v6-clean/layers/miyabi-body-fixed.png`: PASS.
- Generated QA JSON status: PASS.
- Frame count, zero-padded ordering, `288x160` dimensions: PASS.
- Pixel-exact left/right mirror comparison for all 132 pairs: PASS.
- Copied body/source pixel equality and fixed body position `(80,20)`: PASS.
- Final 15 clean-idle frames exactly match the immutable body on transparent overscan: PASS.
- Key swing/hit frames have no full-canvas alpha matte: PASS.
- `ffprobe` duration, dimensions, rate, and frame count: PASS.
- Contact sheet visual inspection: PASS for readable cyan crescent, white core, hit-stop hold, shards, fade, and unclipped overscan.

## Approval boundary

The attack is an asset-review v1 only. It has not been connected to the Electron taskbar-pet runtime; wait for the user's visual approval or correction first.
