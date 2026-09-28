# Taskbar Pet — Miyabi & Firefly Behavior Pack v1

## Purpose and scope

This pack defines the visual language for the **160 x 144 px** taskbar-pet
animations of Hoshimi Miyabi and Firefly. It covers a readable silhouette,
state poses, and timing ranges; it does not prescribe a single mandatory
choreography. The pet must feel quietly alive at rest and only become
spectacular for a short character-signature action.

**Source visual references**

- Miyabi model: `tmp/miyabi-model-preview/front.png` and
  `tmp/miyabi-model-preview/three_quarter.png`.
- Miyabi weapon: `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/hip-rise-crescent-slash-v3/references/`.
- Approved Miyabi chibi body: `assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/layered-v6-clean/layers/miyabi-body-fixed.png`.
- Approved Firefly body: `assets/generated/pixel-chibi/production-v2/firefly/layered-v3-clean/layers/firefly-body-fixed.png`.

## Shared taskbar rules

- Work on a **right-facing 160 x 144 master**; generate the left-facing
  animation by an exact horizontal pixel mirror. Never redraw the opposite
  direction independently.
- Feet sit on a shared baseline at y=143. Keep the body inside the central
  96 x 128 px safe area in ordinary states; a signature VFX may overscan only
  in its travel direction.
- Use hard, nearest-neighbour pixel edges. No opaque background, soft matte,
  desktop-wide shake, or full-screen flash.
- Default loops are low-amplitude: a 1–2 px vertical settle, a 1 px hair/cape
  response, and one small prop response are enough. A character must not
  bounce continuously or wave at the user.
- Timing ranges below assume 10–12 fps authored pixel poses, with optional
  rendering interpolation. Holds and pauses are intentional; do not add
  in-between motion merely to make an action busy.
- Suggested output names follow
  `[category]_[name]_[variant]_[size].png`, for example
  `char_miyabi_stand_right_160x144.png` and
  `char_miyabi_stand_left_160x144.png`.

## Character identity locks

### Hoshimi Miyabi

Miyabi must read at a glance as the approved chibi, not a generic fox girl:

- **Head:** tall dark fox ears, long straight black hair with heavy back mass,
  and small, calm red eyes. Ears and hair are the highest silhouette points.
- **Clothing:** muted **teal asymmetric coat/cape** with the broad draped
  left panel, warm gold trim, a white shirt with a thin **black tie** (no red bow), a **black
  pleated skirt**, **black tights and black heeled ankle boots** (per the 3D model). Teal is a garment plane, not a blue glow.
- **Arm:** the viewer-right arm is the prominent segmented dark mechanical
  armored arm, including its red ring accent; it must not be replaced with a
  plain sleeve.
- **Weapon:** retain the correct mechanical sheathed katana: dark curved
  scabbard, wrapped handle, angular guard/hardware, paper shide accents, and
  restrained cyan edge/ribbon accents. Do not substitute a smooth fantasy
  longsword, a second rear scabbard, or a generic glowing rod.
- **Temperament:** precise, composed, economical. Even sleepy or hungry poses
  should look contained rather than hyperactive.

### Firefly

Firefly retains the currently approved **white-hair school-uniform** chibi
silhouette: large pale hair mass with green accents, bright teal-green eyes,
dark school-uniform panels with light trim, pale legs/boots, and her slim
cyan-edged weapon. Her visual energy is warm, gentle, and hopeful; do not
replace her with SAM armor in these everyday 160 x 144 pet states. Any small
SAM/hologram cue remains a secondary, translucent prop and never obscures her
face or makes a second full character silhouette.

## State pose and timing direction

| State | Miyabi | Firefly | Suggested timing |
| --- | --- | --- | --- |
| **Stand** | Weight quiet and centered; one coat hem/hair-tip response, weapon remains securely sheathed. Red eyes stay level. | Relaxed upright stance; hair and skirt settle once, weapon rests down and away from the face. | 3.2–4.8 s loop; 6–10 authored poses. |
| **Walk** | Short, deliberate step. Cape panel lags one pose, sheathed weapon follows the hip without swinging across the body. | Light two-step with a gentle hair delay; weapon stays a clean diagonal/downward silhouette. | 0.70–1.00 s per cycle; 6–8 poses. |
| **Sleepy** | Eyelids lower, ear angle softens 1–2 px, shoulders settle. A small restrained exhale is preferable to a yawn. | Half-lidded eyes, hair settles forward a little, a tiny hand-to-chest or weapon-rest adjustment. | 1.4–2.2 s one-shot, then return to stand or sleep. |
| **Sleep** | Compact seated/leaning rest with coat pooled but weapon protected and visible; ears droop slightly, not flat. | Small seated/leaning nap, pale hair forming the readable outer mass; cyan weapon safely beside her. | Enter 0.9–1.4 s; 2.4–3.6 s breathing loop. |
| **Wake** | Ears rise first, eyes open, then one firm coat/hair settle. No startled jump. | Hair lifts/settles, eyes brighten, then a small upright reset. | 0.55–0.90 s one-shot. |
| **Hungry** | One brief look toward food area, then a small gloved-hand/armored-hand restraint gesture; no begging. | Curious lean and small bright-eye cue, with hands kept near the body. | 0.9–1.4 s one-shot; leave a quiet hold before another state. |
| **Eat** | One compact bite/tea-like pause with a tiny satisfied eye-soften; sheathed weapon remains clear. | A neat two-bite rhythm and one small happy eye/shoulder response; no oversized chewing loop. | 1.5–2.3 s one-shot or sparse 2.6–3.2 s loop. |

## Character-signature actions

### Miyabi — Crescent unsheath

The action is a compact version of her controlled draw-cut, not a continuous
combat combo. Start from the sheathed mechanical weapon; the hilt/guard is the
origin. Use a short body stillness, a cyan-white blade core, and a single
forward crescent that clears in the travel direction.

- **Timing:** charge 0.00–0.30 s; draw/snap 0.30–0.42 s; full crescent with
  80–100 ms hit-stop at 0.42–0.62 s; broken ribbon/shard decay 0.62–1.05 s;
  return cleanly by 1.30 s.
- **Hierarchy:** white-hot 1–2 px blade core and the pointed leading head are
  primary; cyan/teal crescent is secondary; deep-blue afterimage and a few
  shards are tertiary. The head is sharp and curved, never a flat vertical
  cap or a filled water-hose triangle.
- **Character readability:** retain the face, teal cape asymmetry, armored
  right arm, and feet baseline. The VFX supplies the force; do not scale or
  warp the approved body/weapon artwork.

### Firefly — SAM henshin (user direction, 2026-09-28)

Prop rule: **the module turns into the sword**. Firefly never holds the module and the sword at the same time. Ordinary states hold only the module, gazed at like a hand mirror; when both hands are busy (eat, sleep) the module is put away with a small green flame puff. Module and sword designs follow the official 3D models (`assets/references/character-equipment/firefly/{module,sword}-flat/`, rendered by `scripts/render_pmx_reference.py`).

Sequence (~32 s, one-shot):
1. Henshin pose with the module held out (`signature/h1`).
2. Green flame clings to her silhouette and climbs from the feet; everything it passes is SAM armour; the module dissolves into the flame (`a1n`).
3. The flame re-forms in the open palm and grows into a sword (`a1s_clean`, hilt → tip).
4. Toss: the sword spins up, flashes, and falls back as two swords into both hands while the flame reshapes SAM into the flight pose (`a2_hover`).
5. Lift-off with thruster plumes, hover, the two swords dissolve tip → hilt, landing.
6. A green vortex peels the armour away from the feet up and converges into the module in Firefly's hand.
7. The module summons her sword (`ks`), she holds it, then it folds back into the module; she returns to idle.

Built by `scripts/build_pet_clip.py` (FX `flame_hug`, `thrust`, `vortex`, `poof`; frame keys `wipe_to` with ragged fronts, `lift`, `dissolve`, `props`).

## Behavior variety, not fixed choreography

The table and signature descriptions define **pose atoms and bounds**, not a
frame-exact playlist. Select one compatible atom per trigger, vary the hold
within the stated range, and let the pet return to a quiet stand before the
next notable gesture. Avoid chaining hungry, eat, wake, and signature actions
into a performance routine. In particular, a signature action needs a long
cooldown and must never become the default idle loop.

## Review checklist

- At thumbnail scale, can the viewer identify Miyabi by fox ears, black hair,
  teal asymmetrical cape, black pleats, armored right arm, and mechanical
  sheathed katana?
- At thumbnail scale, can the viewer identify Firefly by white hair,
  school-uniform silhouette, green eyes, and slim cyan-edged weapon?
- Are left frames exact mirrors of right masters, feet aligned to y=143, and
  all ordinary states inside the safe area?
- Does every action have one readable accent rather than many competing ones?
- Does the pet return to stillness without an overacted or repetitive loop?
