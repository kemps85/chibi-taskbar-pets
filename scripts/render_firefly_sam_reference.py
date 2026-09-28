"""Render transparent turntable references from the locally supplied SAM PMX.

Run through Blender, not the regular Python interpreter:

    blender.exe --background --python scripts/render_firefly_sam_reference.py

The renders are reference-only inputs for the hand-cleaned pixel sprite pipeline.
They are not shipped game assets.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
import bpy_extras.io_utils as io_utils
from mathutils import Vector


ROOT = Path(r"C:\Users\ASUS\Documents\ChatGPT\Game")
MODEL = Path(
    r"C:\Users\ASUS\Downloads\星穹铁道—流萤·春日手信_by_崩坏：星穹铁道_948486d4ddcc6988bd90019585983d7a"
    r"\萨姆·春日手信\萨姆·春日手信(修）.pmx"
)
OUTPUT = ROOT / "assets" / "references" / "character-equipment" / "firefly" / "sam-turntable"
MMD_TOOLS = Path(
    r"C:\Users\ASUS\AppData\Roaming\Blender Foundation\Blender\5.1"
    r"\extensions\user_default"
)


def register_mmd_tools() -> None:
    # mmd_tools 5.1 calls this helper during registration; Blender 4.1 lacks it.
    if not hasattr(io_utils, "poll_file_object_drop"):
        io_utils.poll_file_object_drop = lambda _context: True
    sys.path.insert(0, str(MMD_TOOLS))
    import mmd_tools  # type: ignore

    mmd_tools.register()


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_model() -> None:
    if not MODEL.exists():
        raise FileNotFoundError(MODEL)
    bpy.ops.mmd_tools.import_model(
        filepath=str(MODEL),
        scale=0.08,
        types={"MESH", "ARMATURE"},
        clean_model=True,
    )


def mesh_bounds() -> tuple[Vector, Vector]:
    corners: list[Vector] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        corners.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not corners:
        raise RuntimeError("Imported PMX contains no mesh bounds")
    minimum = Vector((min(p.x for p in corners), min(p.y for p in corners), min(p.z for p in corners)))
    maximum = Vector((max(p.x for p in corners), max(p.y for p in corners), max(p.z for p in corners)))
    return minimum, maximum


def point_camera(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def add_area_light(name: str, location: tuple[float, float, float], energy: float, size: float) -> None:
    data = bpy.data.lights.new(name=name, type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    bpy.context.collection.objects.link(obj)
    point_camera(obj, Vector((0.0, 0.0, location[2] * 0.42)))


def configure_scene(center: Vector, extent: Vector) -> bpy.types.Object:
    scene = bpy.context.scene
    # Workbench texture mode is intentionally used here.  The supplied PMX was
    # authored for MMD toon shaders; Blender's Eevee import blows those
    # materials out to nearly white, while Workbench preserves the texture map
    # and makes the armour segmentation readable for pixel-art reference.
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.resolution_percentage = 100
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "TEXTURE"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.curvature_ridge_factor = 1.5
    scene.display.shading.curvature_valley_factor = 1.25

    world = bpy.data.worlds.new("Reference World") if not scene.world else scene.world
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.055, 0.065, 0.085, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35

    radius = max(extent.x, extent.y, extent.z)
    add_area_light("Key", (center.x - radius, center.y - radius * 1.4, center.z + radius), 1800, radius)
    add_area_light("Fill", (center.x + radius, center.y - radius * 0.4, center.z + radius * 0.25), 950, radius)
    add_area_light("Rim", (center.x, center.y + radius * 1.2, center.z + radius * 0.8), 1400, radius * 0.8)

    camera_data = bpy.data.cameras.new("Reference Camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(extent.z * 1.12, extent.x * 1.35, extent.y * 1.35)
    camera = bpy.data.objects.new("Reference Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    return camera


def render_views(camera: bpy.types.Object, center: Vector, extent: Vector) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    distance = max(extent.x, extent.y, extent.z) * 2.6
    views = {
        "front-neg-y": Vector((center.x, center.y - distance, center.z)),
        "front-pos-y": Vector((center.x, center.y + distance, center.z)),
        "right-three-quarter": Vector((center.x + distance * 0.72, center.y - distance, center.z)),
        "left-three-quarter": Vector((center.x - distance * 0.72, center.y - distance, center.z)),
        "right-profile": Vector((center.x + distance, center.y, center.z)),
    }
    for name, location in views.items():
        camera.location = location
        point_camera(camera, center)
        bpy.context.scene.render.filepath = str(OUTPUT / f"sam-{name}.png")
        bpy.ops.render.render(write_still=True)


def main() -> None:
    reset_scene()
    register_mmd_tools()
    import_model()
    minimum, maximum = mesh_bounds()
    center = (minimum + maximum) * 0.5
    extent = maximum - minimum
    camera = configure_scene(center, extent)
    render_views(camera, center, extent)
    print(f"Rendered SAM references to {OUTPUT}")


if __name__ == "__main__":
    main()
