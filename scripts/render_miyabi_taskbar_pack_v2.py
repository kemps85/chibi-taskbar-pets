"""Render a complete Miyabi taskbar pack from the user's local PMX models.

This is a Blender 4.1 script. It renders at 4x the runtime canvas so the final
Pillow pass can downsample clean antialiased RGBA frames to 160x144.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game")
RAW_ROOT = ROOT / "tmp" / "miyabi-taskbar-v2-raw"
sys.path.insert(0, str(ROOT / "scripts"))
import render_miyabi_taskbar_reference as ref  # type: ignore


CHARACTER_ROOT: bpy.types.Object
CHARACTER_ARMATURE: bpy.types.Object
WEAPON_ROOT: bpy.types.Object
GHOST_ROOT: bpy.types.Object
GHOST_EYE: bpy.types.Object
ONIGIRI_ROOT: bpy.types.Object


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def smooth(value: float) -> float:
    value = clamp01(value)
    return value * value * (3.0 - 2.0 * value)


def pulse(value: float) -> float:
    return math.sin(value * math.tau)


def add_rotation(bone_name: str, xyz_deg: tuple[float, float, float]) -> None:
    bone = CHARACTER_ARMATURE.pose.bones.get(bone_name)
    if not bone:
        return
    bone.rotation_euler = tuple(
        bone.rotation_euler[index] + math.radians(xyz_deg[index])
        for index in range(3)
    )


def set_recursive_visible(root: bpy.types.Object, visible: bool) -> None:
    root.hide_render = not visible
    for child in root.children_recursive:
        child.hide_render = not visible


def base_pose() -> None:
    ref.pose_stand(CHARACTER_ARMATURE)
    CHARACTER_ROOT.location = (0.0, 0.0, 0.0)
    CHARACTER_ROOT.rotation_euler = (0.0, 0.0, math.radians(-12.0))
    CHARACTER_ROOT.scale = (1.0, 1.0, 1.0)
    WEAPON_ROOT.location = (-0.02, 0.18, 0.72)
    WEAPON_ROOT.rotation_euler = (math.radians(4), math.radians(-7), math.radians(-7))
    ref.IK_TARGETS["L"].location = (0.30, -0.08, 0.73)
    ref.IK_TARGETS["R"].location = (-0.30, -0.08, 0.73)
    set_recursive_visible(GHOST_ROOT, False)
    set_recursive_visible(ONIGIRI_ROOT, False)


def pose_idle(t: float) -> None:
    base_pose()
    breath = pulse(t)
    CHARACTER_ROOT.location.z = 0.008 * (0.5 + 0.5 * breath)
    CHARACTER_ROOT.rotation_euler.z += math.radians(0.7 * breath)
    add_rotation("上半身1", (0.9 * breath, 0.0, 0.7 * breath))
    add_rotation("頭", (-0.7 * breath, 0.0, -0.8 * breath))
    ref.IK_TARGETS["L"].location.x += 0.009 * breath
    ref.IK_TARGETS["R"].location.x -= 0.008 * breath


def pose_walk(t: float) -> None:
    base_pose()
    stride = pulse(t)
    bounce = abs(math.sin(t * math.tau))
    CHARACTER_ROOT.location.z = 0.018 * bounce
    CHARACTER_ROOT.rotation_euler.z += math.radians(1.2 * stride)
    add_rotation("足.L", (0.0, 0.0, 15.0 * stride))
    add_rotation("ひざ.L", (0.0, 0.0, 7.0 * max(0.0, -stride)))
    add_rotation("足.R", (0.0, 0.0, -15.0 * stride))
    add_rotation("ひざ.R", (0.0, 0.0, 7.0 * max(0.0, stride)))
    ref.IK_TARGETS["L"].location.x += 0.055 * stride
    ref.IK_TARGETS["R"].location.x -= 0.055 * stride
    ref.IK_TARGETS["L"].location.z += 0.018 * max(0.0, -stride)
    ref.IK_TARGETS["R"].location.z += 0.018 * max(0.0, stride)
    add_rotation("上半身1", (0.0, 0.0, -2.0 * stride))


def pose_sleep_cue(t: float) -> None:
    base_pose()
    droop = smooth(min(1.0, t * 2.1))
    sway = pulse(t)
    ref.move(CHARACTER_ARMATURE, "センター", (0.0, 0.0, -0.035 * droop))
    add_rotation("上半身", (8.0 * droop, 0.0, 3.0 * sway))
    add_rotation("上半身1", (7.0 * droop, 0.0, 2.0 * sway))
    add_rotation("首", (9.0 * droop, 0.0, -2.0 * sway))
    add_rotation("頭", (13.0 * droop, 0.0, -3.0 * sway))
    ref.IK_TARGETS["L"].location = (0.21, -0.17, 0.83)
    ref.IK_TARGETS["R"].location = (-0.17, -0.17, 0.87 + 0.02 * sway)


def apply_sleep_pose(amount: float, breathe: float = 0.0) -> None:
    base_pose()
    amount = smooth(amount)
    # First crouch, then rotate the complete rig and sheathed weapon together.
    crouch = smooth(min(1.0, amount / 0.48))
    lie = smooth(max(0.0, (amount - 0.38) / 0.62))
    ref.move(CHARACTER_ARMATURE, "センター", (0.0, 0.0, -0.18 * crouch))
    add_rotation("上半身", (12.0 * crouch, 0.0, 8.0 * crouch))
    add_rotation("上半身1", (12.0 * crouch, 0.0, 5.0 * crouch))
    add_rotation("頭", (10.0 * crouch, 0.0, -7.0 * crouch))
    add_rotation("足.L", (0.0, 0.0, -18.0 * crouch))
    add_rotation("ひざ.L", (0.0, 0.0, 28.0 * crouch))
    add_rotation("足.R", (0.0, 0.0, 14.0 * crouch))
    add_rotation("ひざ.R", (0.0, 0.0, 34.0 * crouch))
    ref.IK_TARGETS["L"].location = (0.13, -0.16, 0.72)
    ref.IK_TARGETS["R"].location = (-0.10, -0.16, 0.78)
    CHARACTER_ROOT.rotation_euler.y = math.radians(82.0 * lie)
    CHARACTER_ROOT.rotation_euler.z = math.radians(-12.0 + 5.0 * lie)
    CHARACTER_ROOT.location.x = -0.38 * lie
    CHARACTER_ROOT.location.z = 0.21 * lie + 0.006 * breathe * lie
    # Keep the sheathed katana horizontal beside Miyabi instead of letting the
    # parent's lie-down rotation turn it into a vertical spike.
    WEAPON_ROOT.rotation_euler.y = math.radians(-7.0 - 82.0 * lie)
    WEAPON_ROOT.location.z = 0.72 - 0.12 * lie


def pose_sleep_enter(t: float) -> None:
    apply_sleep_pose(t)


def pose_sleep_loop(t: float) -> None:
    apply_sleep_pose(1.0, pulse(t))
    add_rotation("頭", (1.4 * pulse(t), 0.0, 0.0))


def pose_wake(t: float) -> None:
    apply_sleep_pose(1.0 - t)


def pose_hunger(t: float) -> None:
    base_pose()
    ache = 0.5 + 0.5 * pulse(t)
    ref.move(CHARACTER_ARMATURE, "センター", (0.0, 0.0, -0.025 * ache))
    add_rotation("上半身", (7.0 + 3.0 * ache, 0.0, -3.0))
    add_rotation("上半身1", (5.0 + 2.0 * ache, 0.0, 2.0))
    add_rotation("頭", (5.0, 0.0, -4.0))
    ref.IK_TARGETS["L"].location = (0.10, -0.20, 0.90)
    ref.IK_TARGETS["R"].location = (-0.10, -0.20, 0.89)


def pose_eat(t: float) -> None:
    base_pose()
    set_recursive_visible(ONIGIRI_ROOT, True)
    # Clear three readable phases: raise, bite/hold, lower.
    if t < 0.32:
        lift = smooth(t / 0.32)
    elif t < 0.72:
        lift = 1.0
    else:
        lift = 1.0 - smooth((t - 0.72) / 0.28)
    chew = math.sin(max(0.0, t - 0.32) * math.tau * 4.0) if 0.32 <= t <= 0.82 else 0.0
    ref.IK_TARGETS["R"].location = (-0.22 + 0.13 * lift, -0.22, 0.78 + 0.49 * lift)
    ref.IK_TARGETS["L"].location = (0.14, -0.18, 0.92)
    add_rotation("頭", (-3.0 * lift + 1.5 * chew, 0.0, 3.0 * lift))
    add_rotation("上半身1", (2.0 * lift, 0.0, -2.0 * lift))


def pose_spirit(t: float) -> None:
    base_pose()
    # Vô Vĩ is the actual horned orb model, never a biological fox tail.
    if t < 0.30:
        emerge = smooth(t / 0.30)
    elif t < 0.70:
        emerge = 1.0
    else:
        emerge = 1.0 - smooth((t - 0.70) / 0.30)
    set_recursive_visible(GHOST_ROOT, emerge > 0.015)
    GHOST_ROOT.scale = (0.72 * emerge, 0.72 * emerge, 0.72 * emerge)
    GHOST_ROOT.location = (
        0.18 + 0.48 * emerge,
        0.10,
        0.90 + 0.19 * emerge + 0.025 * pulse(t * 1.5),
    )
    GHOST_ROOT.rotation_euler = (0.0, math.radians(10.0 * pulse(t)), math.radians(-10.0 + 14.0 * pulse(t)))
    add_rotation("頭", (0.0, 0.0, -8.0 * emerge))
    ref.IK_TARGETS["R"].location.x -= 0.04 * emerge


CLIPS = {
    "idle": (12, pose_idle),
    "walk": (12, pose_walk),
    "sleep_cue": (10, pose_sleep_cue),
    "sleep_enter": (16, pose_sleep_enter),
    "sleep_loop": (12, pose_sleep_loop),
    "wake": (16, pose_wake),
    "hunger_cue": (10, pose_hunger),
    "eat": (14, pose_eat),
    "spirit_tail": (20, pose_spirit),
}


def create_onigiri() -> bpy.types.Object:
    root = bpy.data.objects.new("OnigiriRoot", None)
    bpy.context.collection.objects.link(root)
    bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.067, radius2=0.052, depth=0.105)
    rice = bpy.context.object
    rice.name = "OnigiriRice"
    rice.parent = root
    rice.rotation_euler = (math.radians(90), 0.0, math.radians(90))
    material = bpy.data.materials.new("Onigiri Rice")
    material.diffuse_color = (0.92, 0.92, 0.88, 1.0)
    rice.data.materials.append(material)
    bpy.ops.mesh.primitive_cube_add(scale=(0.035, 0.012, 0.035))
    nori = bpy.context.object
    nori.name = "OnigiriNori"
    nori.parent = root
    nori.location = (0.0, -0.055, -0.025)
    nori_material = bpy.data.materials.new("Onigiri Nori")
    nori_material.diffuse_color = (0.018, 0.025, 0.023, 1.0)
    nori.data.materials.append(nori_material)
    root.parent = ref.IK_TARGETS["R"]
    root.location = (0.0, -0.03, 0.0)
    return root


def prepare_models() -> None:
    global CHARACTER_ROOT, CHARACTER_ARMATURE, WEAPON_ROOT, GHOST_ROOT, GHOST_EYE, ONIGIRI_ROOT
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    ref.register_mmd_tools()
    CHARACTER_ROOT, CHARACTER_ARMATURE = ref.import_pmx("星见雅.pmx")
    WEAPON_ROOT, weapon_armature = ref.import_pmx("武器.pmx")
    GHOST_ROOT, _ghost_armature = ref.import_pmx("幽灵.pmx")
    ref.create_arm_ik(CHARACTER_ARMATURE)
    for name in ("HandTarget.L", "HandTarget.R", "ElbowPole.L", "ElbowPole.R"):
        obj = bpy.data.objects[name]
        obj.parent = CHARACTER_ROOT

    WEAPON_ROOT.parent = CHARACTER_ROOT
    WEAPON_ROOT.location = (-0.02, 0.18, 0.72)
    WEAPON_ROOT.rotation_euler = (math.radians(4), math.radians(-7), math.radians(-7))
    for bone_name in (
        "Bn_katana_burst01", "Bn_katana_burst02", "Bn_katana_burst03",
        "Bn_katana_burst04", "Bn_katana_burst", "Bn_katana_burst_eye",
        "Bn_PET", "Bn_PET_EYE",
    ):
        bone = weapon_armature.pose.bones.get(bone_name)
        if bone:
            bone.scale = (0.001, 0.001, 0.001)

    GHOST_ROOT.parent = CHARACTER_ROOT
    for obj in [GHOST_ROOT, *GHOST_ROOT.children_recursive]:
        if obj.type == "MESH":
            for slot in obj.material_slots:
                if slot.material:
                    slot.material.diffuse_color = (0.025, 0.034, 0.048, 1.0)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.038)
    GHOST_EYE = bpy.context.object
    GHOST_EYE.name = "GhostRedEye"
    GHOST_EYE.parent = GHOST_ROOT
    GHOST_EYE.location = (0.0, -0.105, 0.048)
    red = bpy.data.materials.new("Ghost Red Eye")
    red.diffuse_color = (0.75, 0.025, 0.02, 1.0)
    GHOST_EYE.data.materials.append(red)

    ONIGIRI_ROOT = create_onigiri()
    camera = ref.configure_scene()
    camera.data.ortho_scale = 2.10
    camera.location.z += 0.03
    ref.point_at(camera, Vector((0.0, 0.0, 0.86)))


def render_all() -> None:
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    for clip_name, (count, pose_fn) in CLIPS.items():
        clip_dir = RAW_ROOT / clip_name
        clip_dir.mkdir(parents=True, exist_ok=True)
        for index in range(count):
            output_path = clip_dir / f"frame-{index:03d}.png"
            if output_path.exists():
                continue
            t = index / count
            pose_fn(t)
            bpy.context.view_layer.update()
            bpy.context.scene.render.filepath = str(output_path)
            bpy.ops.render.render(write_still=True)
        print(f"Rendered {clip_name}: {count} frames")


def main() -> None:
    prepare_models()
    render_all()
    print(f"Rendered native Miyabi taskbar pack to {RAW_ROOT}")


if __name__ == "__main__":
    main()
