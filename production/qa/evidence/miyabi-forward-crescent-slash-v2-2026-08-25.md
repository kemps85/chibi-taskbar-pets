# Miyabi Forward-Crescent Slash v2 - QA Evidence

Date: 2026-08-25

## Corrected intent

- Miyabi kneels on one knee and visibly braces before attacking.
- Her right hand grips the sword hilt; her left hand controls the scabbard; no hand rests on the blade.
- The release contains exactly one drawn sword plus one empty scabbard.
- The attack is one detached semicircular wave traveling forward, not a circular aura or overhead ring around Miyabi.

## Model grounding

- Local PMX reference inspected at `C:\Users\ASUS\Downloads\qOXyji3wYu`.
- Character PMX: 27,086 vertices, 436 bones, 23 materials.
- Weapon PMX: 4,008 vertices, 17 bones, 3 materials.
- Grounded visual cues: teal coat, black pleated skirt, asymmetrical armored right arm, dark mechanical katana/scabbard, cyan accents and ribbon.
- No `.pmx` file was copied into the generated output and the animation has no PMX runtime dependency.

## Output

- Package: `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/final-blow-slash-v2/`
- Canvas: 384x160 RGBA.
- Timeline: 156 frames, 60 FPS, 2.6 seconds.
- Readable kneeling brace: 0.616667 seconds.
- Hit-stop: 0.133333 seconds.
- Right master plus exact mirrored left set: 156 frames per direction.
- Review video: H.264, 1280x520, 60 FPS, 156 frames, 2.6 seconds.

## Checks run

- Python syntax compile: PASS.
- Full deterministic rebuild from the approved standing sprite and two model-grounded pose sources: PASS.
- Generated QA JSON status: PASS.
- Frame count, zero-padded ordering and 384x160 dimensions: PASS.
- Pixel-exact mirror validation for all 156 pairs: PASS.
- Transparent canvas border: 0 non-transparent border pixels across every frame.
- Final 15 frames exactly match the approved standing body on a transparent canvas.
- Charge top y=8; release top y=8; character scale delta=0 px.
- No PMX files in the output package.
- Contact-sheet and key-frame visual review: PASS for one-knee brace, right-hand hilt grip, one-sword/one-scabbard release, one forward traveling crescent, and unclipped overscan.

## Approval boundary

This v2 is the current visual-review candidate. It is not connected to the Electron taskbar-pet runtime until the user approves it.
