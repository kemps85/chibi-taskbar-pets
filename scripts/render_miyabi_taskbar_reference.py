"""Render native-model Miyabi taskbar reference poses through Blender.

Run with Blender 4.1, not regular Python. The supplied PMX files stay outside
the repository; only transparent reference PNGs are written into tmp/.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
import bpy_extras.io_utils as io_utils
from mathutils import Vector


ROOT = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game")
MODEL_ROOT = Path(r"C:\Users\ASUS\Downloads\qOXyji3wYu")
OUTPUT = ROOT / "tmp" / "miyabi-taskbar-native-reference"
MMD_TOOLS = Path(
    r"C:\Users\ASUS\AppData\Roaming\Blender Foundation\Blender\5.1"
    r"\extensions\user_default"
)
IK_TARGETS: dict[str, bpy.types.Object] = {}


def register_mmd_tools() -> None:
    if not hasattr(io_utils, "poll_file_object_drop"):
        io_utils.poll_file_object_drop = lambda _context: True
    sys.path.insert(0, str(MMD_TOOLS))
    import mmd_tools  # type: ignore

    mmd_tools.register()


def import_pmx(filename: str) -> tuple[bpy.types.Object, bpy.types.Object]:
    before = set(bpy.context.scene.objects)
    bpy.ops.mmd_tools.import_model(
        filepath=str(MODEL_ROOT / filename),
        scale=0.08,
        types={"MESH", "ARMATURE"},
        clean_model=True,
    )
    added = [obj for obj in bpy.context.scene.objects if obj not in before]
    root = next(obj for obj in added if obj.type == "EMPTY" and obj.parent is None)
    armature = next(obj for obj in added if obj.type == "ARMATURE")
    return root, armature


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def configure_scene() -> bpy.types.Object:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 576
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = True
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "TEXTURE"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.curvature_ridge_factor = 1.8
    scene.display.shading.curvature_valley_factor = 1.5
    scene.display.shading.show_specular_highlight = True
    scene.render.image_settings.color_mode = "RGBA"

    camera_data = bpy.data.cameras.new("Taskbar Camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.0
    camera = bpy.data.objects.new("Taskbar Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (2.7, -5.2, 1.02)
    point_at(camera, Vector((0.0, 0.0, 0.83)))
    scene.camera = camera
    return camera


def reset_pose(armature: bpy.types.Object) -> None:
    for bone in armature.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)


def create_arm_ik(armature: bpy.types.Object) -> None:
    for side, x in (("L", 0.30), ("R", -0.30)):
        target = bpy.data.objects.new(f"HandTarget.{side}", None)
        target.location = (x, -0.08, 0.74)
        bpy.context.collection.objects.link(target)
        pole = bpy.data.objects.new(f"ElbowPole.{side}", None)
        pole.location = (x * 2.1, 0.04, 0.98)
        bpy.context.collection.objects.link(pole)
        wrist = armature.pose.bones[f"手首.{side}"]
        constraint = wrist.constraints.new("IK")
        constraint.target = target
        constraint.pole_target = pole
        constraint.chain_count = 5
        constraint.iterations = 64
        IK_TARGETS[side] = target


def rotate(armature: bpy.types.Object, bone_name: str, xyz_deg: tuple[float, float, float]) -> None:
    bone = armature.pose.bones.get(bone_name)
    if bone is None:
        raise KeyError(bone_name)
    bone.rotation_mode = "XYZ"
    bone.rotation_euler = tuple(math.radians(value) for value in xyz_deg)


def move(armature: bpy.types.Object, bone_name: str, xyz: tuple[float, float, float]) -> None:
    bone = armature.pose.bones.get(bone_name)
    if bone is None:
        raise KeyError(bone_name)
    bone.location = xyz


def pose_stand(armature: bpy.types.Object) -> None:
    reset_pose(armature)
    armature.pose.bones["頭"].scale = (1.18, 1.18, 1.18)
    IK_TARGETS["L"].location = (0.30, -0.08, 0.73)
    IK_TARGETS["R"].location = (-0.30, -0.08, 0.73)
    rotate(armature, "上半身1", (0, 0, -2))
    rotate(armature, "頭", (0, 0, 3))
    rotate(armature, "足.L", (0, 0, -2))
    rotate(armature, "足.R", (0, 0, 2))


def pose_brace(armature: bpy.types.Object) -> None:
    pose_stand(armature)
    move(armature, "センター", (0.0, 0.0, -0.08))
    rotate(armature, "下半身", (0, 0, -7))
    rotate(armature, "上半身", (3, 0, 9))
    rotate(armature, "上半身1", (4, 0, 10))
    IK_TARGETS["L"].location = (-0.22, -0.18, 0.76)
    IK_TARGETS["R"].location = (-0.42, -0.18, 0.78)
    rotate(armature, "足.L", (9, 0, -12))
    rotate(armature, "ひざ.L", (18, 0, 0))
    rotate(armature, "足.R", (-8, 0, 10))
    rotate(armature, "ひざ.R", (22, 0, 0))
    rotate(armature, "頭", (-2, 0, -8))


def pose_sleepy(armature: bpy.types.Object) -> None:
    pose_stand(armature)
    move(armature, "センター", (0.0, 0.0, -0.04))
    rotate(armature, "上半身", (8, 0, 6))
    rotate(armature, "上半身1", (10, 0, 8))
    rotate(armature, "首", (13, 0, -3))
    rotate(armature, "頭", (16, 0, -5))
    IK_TARGETS["L"].location = (0.18, -0.20, 0.86)
    IK_TARGETS["R"].location = (-0.18, -0.20, 0.88)


def render_pose(name: str, pose_fn, character_armature: bpy.types.Object) -> None:
    pose_fn(character_armature)
    bpy.context.view_layer.update()
    bpy.context.scene.render.filepath = str(OUTPUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)


def main() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    register_mmd_tools()
    character_root, character_armature = import_pmx("星见雅.pmx")
    weapon_root, weapon_armature = import_pmx("武器.pmx")
    ghost_root, _ghost_armature = import_pmx("幽灵.pmx")
    create_arm_ik(character_armature)

    character_root.rotation_euler[2] = math.radians(-12)
    weapon_root.location = (-0.02, 0.18, 0.72)
    weapon_root.rotation_euler = (math.radians(4), math.radians(-7), math.radians(-7))
    for bone_name in (
        "Bn_katana_burst01", "Bn_katana_burst02", "Bn_katana_burst03",
        "Bn_katana_burst04", "Bn_katana_burst", "Bn_katana_burst_eye",
        "Bn_PET", "Bn_PET_EYE",
    ):
        bone = weapon_armature.pose.bones.get(bone_name)
        if bone:
            bone.scale = (0.001, 0.001, 0.001)
    ghost_root.location = (0.54, 0.14, 0.86)
    ghost_root.scale = (0.78, 0.78, 0.78)
    ghost_root.hide_render = True
    for child in ghost_root.children_recursive:
        child.hide_render = True

    configure_scene()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    render_pose("stand", pose_stand, character_armature)
    render_pose("brace", pose_brace, character_armature)
    render_pose("sleepy", pose_sleepy, character_armature)
    print(f"Rendered Miyabi native references to {OUTPUT}")


if __name__ == "__main__":
    main()
