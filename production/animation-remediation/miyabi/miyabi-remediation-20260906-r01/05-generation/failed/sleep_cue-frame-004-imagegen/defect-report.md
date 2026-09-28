# Failed imagegen candidate — sleep_cue frame-004

Status: **REJECTED — not usable as a frame asset**

Tool output: `C:\Users\ASUS\.codex\generated_images\01a0733e-2630-7bf1-97dc-8c0f2a76683d\exec-d79ae53f-3f93-40a2-9edb-ba6521490184.png`
Workspace copy: `output.png`

Observed:

- Output is 1115x1411 rather than the required 160x144 logical canvas.
- Alpha is fully opaque: checkerboard was baked into RGB; transparent pixels = 0.
- The requested restrained drowsy cue was not clearly realized; eyes/standing pose remained effectively identity-like.
- It therefore cannot enter a clip, be used as a next-frame reference, or be post-processed to conceal the failure.

Action: locked as failed evidence. No stable asset was changed. Do not use this frame as an imagegen reference.
