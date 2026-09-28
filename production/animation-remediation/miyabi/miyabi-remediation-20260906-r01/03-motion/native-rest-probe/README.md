# Blender pose probe — observed evidence

Status: `REFERENCE / CANDIDATE-ONLY`

## OBSERVED

- Local Blender 4.1.1 and the supplied PMX files loaded successfully:
  - `C:\Users\ASUS\Downloads\qOXyji3wYu\星见雅.pmx`
  - `C:\Users\ASUS\Downloads\qOXyji3wYu\武器.pmx`
- The PMX importer exposes the leg IK target bones as `足ＩＫ.L` / `足ＩＫ.R` with parents `左足IK親` / `右足IK親`; the earlier probe used the wrong names and also confused the helper hand IK targets with leg targets.
- Disabling the leg IK constraints and rotating the actual thigh/knee bones around the tested screen-plane axis produced a readable feet-left crouch/rest reference. The `left-leg` contact sheet records this evidence.
- The supplied PMX model is a pose/identity reference only. It is not copied into the stable runtime pack and is not treated as a final pixel-art frame.

## ARTIFACTS

- Corrected IK probe: `render_miyabi_ik_probe.py`
- Manual leg probe: `render_miyabi_manual_leg_probe.py`
- Contact: `left-leg\contact.png`
- Sweep contacts: `ik-sweep\contact.png`, `seat-sweep\contact.png`, `axis\contact.png`

## INFERRED

- A Blender pose guide can make the weight transfer and feet-left rest orientation explicit, but it does not by itself solve the 160x144 pixel-art weapon handoff. The candidate still needs frame-level continuity review.

## UNKNOWN

- Exact user-accepted handoff timing for releasing/placing the katana during sleep entry and picking it up during wake remains unapproved.
