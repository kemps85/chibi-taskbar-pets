# Miyabi Hip-Rise Crescent Slash v3 - QA Evidence

Date: 2026-08-25

## Corrected intent

- Miyabi faces screen-right throughout the authored master.
- She begins kneeling on one knee with the handle forward/right and the saya extending rearward/left.
- The right hand grips the handle immediately by the guard; the left hand controls the saya mouth.
- She rises to standing and makes a one-handed upward `gyaku-kesa` cut from the hip toward 1 o'clock.
- The bright cutting edge leads on the upper-left side of the up-right blade; the dark serrated spine trails on the lower-right side.
- Exactly one large vertical `)` crescent appears at far right, open toward Miyabi, with its lower tip near the ground.

## Real-world motion grounding

- All Japan Kendo Federation document library: `https://www.kendo.or.jp/knowledge/library/`.
- ZNKR Iai Instructional Considerations (2022), Gohon-me Kesa-giri: turn the saya downward-left, cut upward along 7 o'clock to 1 o'clock, and finish with the right fist above/right of the right shoulder.
- The same guidance requires a normal grip at the fuchi with no protruding index finger. The v3 silhouette keeps the wrist aligned and separates the right-hand draw from the left-hand sayabiki action.

## Output

- Package: `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/hip-rise-crescent-slash-v3/`.
- Canvas: 512x192 RGBA.
- Timeline: 156 frames, 60 FPS, 2.6 seconds.
- Hit-stop: 8 frames / 0.133 seconds.
- Right master plus exact mirrored left set: 156 frames per direction.
- Review video: H.264, 1280x520, 60 FPS, 156 frames, 2.6 seconds.

## Checks run

- Python syntax compile: PASS.
- Deterministic rebuild: PASS.
- Generated QA JSON status: PASS.
- Frame count, zero-padded ordering and 512x192 dimensions: PASS.
- Pixel-exact left mirror validation: PASS, 0 mismatches.
- Transparent canvas border: PASS, 0 non-transparent border pixels.
- Clean final frames: PASS.
- Charge/release body scale delta: 0 px.
- One far-right crescent: PASS; lower tip y=168.
- Source split keeps the complete rearward scabbard in release and removes the former floating duplicate from charge.
- Procedural release-blade redraw visually inspected at nearest-neighbour zoom: bright edge upper-left/leading, dark spine lower-right/trailing.
- No PMX file copied into the output package.

## Approval boundary

This v3 is the current visual-review candidate. It is not connected to the Electron taskbar-pet runtime until the user approves the review video.
