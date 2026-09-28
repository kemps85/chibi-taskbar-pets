from __future__ import annotations
import math, sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game'); RUN=ROOT/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01'; OUT=RUN/'03-motion/native-rest-probe'; sys.path.insert(0,str(ROOT/'scripts')); import render_miyabi_taskbar_reference as ref
CHAR_ROOT=None; ARM=None; WEAPON=None; WEAPON_ARM=None
def set_rot(name,xyz): ref.rotate(ARM,name,xyz)
def setup():
 global CHAR_ROOT,ARM,WEAPON,WEAPON_ARM
 bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False); ref.register_mmd_tools(); CHAR_ROOT,ARM=ref.import_pmx('星见雅.pmx'); WEAPON,WEAPON_ARM=ref.import_pmx('武器.pmx'); ref.create_arm_ik(ARM); CHAR_ROOT.rotation_euler[2]=math.radians(-12); WEAPON.location=(-0.02,0.18,0.72); WEAPON.rotation_euler=(math.radians(4),math.radians(-7),math.radians(-7))
 for n in ('Bn_katana_burst01','Bn_katana_burst02','Bn_katana_burst03','Bn_katana_burst04','Bn_katana_burst','Bn_katana_burst_eye','Bn_PET','Bn_PET_EYE'):
  b=WEAPON_ARM.pose.bones.get(n)
  if b: b.scale=(0.001,0.001,0.001)
 ref.configure_scene(); cam=bpy.context.scene.camera; cam.data.ortho_scale=2.35; cam.location.z+=0.02; ref.point_at(cam,Vector((0,0,0.72)))
def base():
 ref.pose_stand(ARM); CHAR_ROOT.location=(0,0,0); CHAR_ROOT.rotation_euler=(0,0,math.radians(-12)); WEAPON.location=(-0.02,0.18,0.72); WEAPON.rotation_euler=(math.radians(4),math.radians(-7),math.radians(-7))
def variant(name):
 base()
 if name=='brace': ref.pose_brace(ARM)
 elif name=='crouch_x_35': ref.move(ARM,'センター',(0,0,-0.10)); set_rot('下半身',(10,0,-7)); set_rot('上半身',(8,0,8)); set_rot('上半身1',(8,0,8)); set_rot('足.L',(35,0,-10)); set_rot('ひざ.L',(45,0,0)); set_rot('足.R',(35,0,10)); set_rot('ひざ.R',(45,0,0)); ref.IK_TARGETS['L'].location=(-0.20,-0.18,0.70); ref.IK_TARGETS['R'].location=(-0.42,-0.18,0.70)
 elif name=='crouch_x_60': ref.move(ARM,'センター',(0,0,-0.14)); set_rot('下半身',(14,0,-7)); set_rot('上半身',(12,0,8)); set_rot('上半身1',(12,0,8)); set_rot('足.L',(55,0,-13)); set_rot('ひざ.L',(65,0,0)); set_rot('足.R',(55,0,13)); set_rot('ひざ.R',(65,0,0)); ref.IK_TARGETS['L'].location=(-0.20,-0.20,0.62); ref.IK_TARGETS['R'].location=(-0.44,-0.20,0.63)
 elif name=='crouch_z_60': ref.move(ARM,'センター',(0,0,-0.14)); set_rot('下半身',(0,0,-15)); set_rot('上半身',(0,0,14)); set_rot('上半身1',(0,0,14)); set_rot('足.L',(0,0,-55)); set_rot('ひざ.L',(0,0,65)); set_rot('足.R',(0,0,55)); set_rot('ひざ.R',(0,0,65)); ref.IK_TARGETS['L'].location=(-0.20,-0.20,0.62); ref.IK_TARGETS['R'].location=(-0.44,-0.20,0.63)
 elif name=='seated_x_75': ref.move(ARM,'センター',(-0.08,0,-0.22)); set_rot('下半身',(18,0,-8)); set_rot('上半身',(16,0,10)); set_rot('上半身1',(16,0,10)); set_rot('首',(8,0,-3)); set_rot('頭',(10,0,-5)); set_rot('足.L',(75,0,-18)); set_rot('ひざ.L',(82,0,0)); set_rot('足.R',(75,0,18)); set_rot('ひざ.R',(82,0,0)); ref.IK_TARGETS['L'].location=(-0.20,-0.20,0.46); ref.IK_TARGETS['R'].location=(-0.46,-0.20,0.48)
 elif name=='seated_x_95': ref.move(ARM,'センター',(-0.10,0,-0.26)); set_rot('下半身',(22,0,-8)); set_rot('上半身',(20,0,11)); set_rot('上半身1',(20,0,11)); set_rot('首',(12,0,-3)); set_rot('頭',(14,0,-5)); set_rot('足.L',(90,0,-18)); set_rot('ひざ.L',(95,0,0)); set_rot('足.R',(90,0,18)); set_rot('ひざ.R',(95,0,0)); ref.IK_TARGETS['L'].location=(-0.20,-0.20,0.40); ref.IK_TARGETS['R'].location=(-0.46,-0.20,0.42)
 elif name=='rest_seated': ref.move(ARM,'センター',(-0.18,0,-0.30)); set_rot('下半身',(28,0,-8)); set_rot('上半身',(25,0,12)); set_rot('上半身1',(25,0,12)); set_rot('首',(15,0,-4)); set_rot('頭',(18,0,-6)); set_rot('足.L',(105,0,-20)); set_rot('ひざ.L',(108,0,0)); set_rot('足.R',(105,0,20)); set_rot('ひざ.R',(108,0,0)); ref.IK_TARGETS['L'].location=(-0.20,-0.20,0.35); ref.IK_TARGETS['R'].location=(-0.46,-0.20,0.37)
 else: raise ValueError(name)
 bpy.context.view_layer.update()
def render():
 OUT.mkdir(parents=True,exist_ok=True)
 for name in ['brace','crouch_x_35','crouch_x_60','crouch_z_60','seated_x_75','seated_x_95','rest_seated']:
  variant(name); bpy.context.scene.render.filepath=str(OUT/f'{name}.png'); bpy.ops.render.render(write_still=True)
 print('PROBE_DONE',OUT)
setup(); render()
