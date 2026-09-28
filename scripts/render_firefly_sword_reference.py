"""Render the user-supplied Firefly sword PMX as transparent identity references."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy
import bpy_extras.io_utils as io_utils
from mathutils import Vector


ROOT = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game")
MODEL = Path(
    r"C:\Users\ASUS\Downloads\星穹铁道—流萤·春日手信_by_崩坏：星穹铁道_948486d4ddcc6988bd90019585983d7a"
    r"\星穹铁道—流萤·春日手信\剑.pmx"
)
OUTPUT = ROOT / "assets" / "references" / "character-equipment" / "firefly" / "sword-turntable"
MMD_TOOLS = Path(
    r"C:\Users\ASUS\AppData\Roaming\Blender Foundation\Blender\5.1"
    r"\extensions\user_default"
)


def register_mmd_tools() -> None:
    if not hasattr(io_utils, "poll_file_object_drop"):
        io_utils.poll_file_object_drop = lambda _context: True
    sys.path.insert(0, str(MMD_TOOLS))
    import mmd_tools  # type: ignore

    mmd_tools.register()


def bounds() -> tuple[Vector, Vector]:
    points: list[Vector] = []
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        raise RuntimeError("Sword PMX contains no mesh")
    return (
        Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))),
        Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))),
    )


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    register_mmd_tools()
    bpy.ops.mmd_tools.import_model(
        filepath=str(MODEL), scale=0.08, types={"MESH", "ARMATURE"}, clean_model=True
    )

    low, high = bounds()
    center = (low + high) * 0.5
    extent = high - low
    radius = max(extent.x, extent.y, extent.z)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "TEXTURE"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.view_settings.look = "AgX - Medium High Contrast"

    camera_data = bpy.data.cameras.new("Sword Reference Camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = radius * 1.16
    camera = bpy.data.objects.new("Sword Reference Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera

    OUTPUT.mkdir(parents=True, exist_ok=True)
    distance = radius * 2.5
    views = {
        "front-neg-y": Vector((center.x, center.y - distance, center.z)),
        "front-pos-y": Vector((center.x, center.y + distance, center.z)),
        "three-quarter": Vector((center.x + distance * 0.65, center.y - distance, center.z)),
        "profile": Vector((center.x + distance, center.y, center.z)),
    }
    for name, position in views.items():
        camera.location = position
        look_at(camera, center)
        scene.render.filepath = str(OUTPUT / f"firefly-sword-{name}.png")
        bpy.ops.render.render(write_still=True)
    print(f"Rendered Firefly sword references to {OUTPUT}")


if __name__ == "__main__":
    main()
