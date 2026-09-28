# Frame specification status

`frame-specs.json` contains one row per current stable-pack frame (90 rows) with the required timing/canvas/identity/motion fields. It is deliberately marked `DRAFT_BLOCKED_NOT_GENERATION_READY`.

The frame contract is not complete until the missing current annotated pose guide, previous/next approved pose, and landmark coordinates are supplied for each clip. The null fields are blockers, not permission to guess. No imagegen request has been made.

Known contract locks: 160x144 canvas, origin top-left, +X right, +Y down, placement anchor `(64,120)`, ground line `y=143`, right-authored frames, runtime mirror left. The anchor is not a foot coordinate.

Required confirmations before generation:

- walk: contact/pass/support poses;
- hunger/eat: exact gesture and food/tea prop semantics;
- sleep cue/enter/loop/wake: approved rest side, support sequence, weapon placement, and settle pose;
- spirit tail: approved Vô Vĩ start/return anchor and route;
- identity: user approval of the master and weapon placement contract.
