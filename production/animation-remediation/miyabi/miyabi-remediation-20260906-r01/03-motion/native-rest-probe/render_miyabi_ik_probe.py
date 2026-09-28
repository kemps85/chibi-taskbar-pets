import math,sys,bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game');OUT=ROOT/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/03-motion/native-rest-probe/ik';sys.path.insert(0,str(ROOT/'scripts'));import render_miyabi_taskbar_reference as ref
ARM=None;CHAR=None;WEAPON=None;WARM=None
def rot(n,v):ref.rotate(ARM,n,v)
def mv(n,v):ref.move(ARM,n,v)
def setup():
 global ARM,CHAR,WEAPON,WARM
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);ref.register_mmd_tools();CHAR,ARM=ref.import_pmx('星见雅.pmx');WEAPON,WARM=ref.import_pmx('武器.pmx');ref.create_arm_ik(ARM);CHAR.rotation_euler[2]=math.radians(-12);WEAPON.location=(-.02,.18,.72);WEAPON.rotation_euler=(math.radians(4),math.radians(-7),math.radians(-7))
 for n in ('Bn_katana_burst01','Bn_katana_burst02','Bn_katana_burst03','Bn_katana_burst04','Bn_katana_burst','Bn_katana_burst_eye','Bn_PET','Bn_PET_EYE'):
  b=WARM.pose.bones.get(n)
  if b:b.scale=(.001,.001,.001)
 ref.configure_scene();c=bpy.context.scene.camera;c.data.ortho_scale=2.35;c.location.z+=.02;ref.point_at(c,Vector((0,0,.72)))
def base():
 ref.pose_stand(ARM);CHAR.location=(0,0,0);CHAR.rotation_euler=(0,0,math.radians(-12));WEAPON.location=(-.02,.18,.72);WEAPON.rotation_euler=(math.radians(4),math.radians(-7),math.radians(-7))
def v(name):
 base()
 if name=='ik_a':
  mv('センター',(0,0,-.10));mv('足ＩＫ.L',(.18,0,-.18));mv('足ＩＫ.R',(-.18,0,-.18))
 if name=='ik_b':
  mv('センター',(0,0,-.10));mv('足ＩＫ.L',(.18,.22,-.14));mv('足ＩＫ.R',(-.18,.22,-.14))
 if name=='ik_c':
  mv('センター',(0,0,-.15));mv('足ＩＫ.L',(.18,.42,-.18));mv('足ＩＫ.R',(-.18,.42,-.18))
 if name=='ik_d':
  mv('センター',(0,0,-.12));mv('足ＩＫ.L',(.30,.28,-.22));mv('足ＩＫ.R',(-.05,.28,-.22));rot('下半身',(15,0,-6));rot('上半身',(12,0,7));rot('上半身1',(12,0,7))
 if name=='ik_e':
  mv('センター',(-.06,0,-.15));mv('足ＩＫ.L',(.35,.45,-.30));mv('足ＩＫ.R',(-.05,.45,-.30));rot('下半身',(20,0,-8));rot('上半身',(16,0,8));rot('上半身1',(16,0,8));rot('首',(8,0,-3));rot('頭',(10,0,-4))
 if name=='ik_f':
  mv('センター',(-.12,0,-.20));mv('足ＩＫ.L',(.38,.65,-.35));mv('足ＩＫ.R',(-.08,.65,-.35));rot('下半身',(25,0,-10));rot('上半身',(20,0,10));rot('上半身1',(20,0,10));rot('首',(10,0,-3));rot('頭',(12,0,-5))
 bpy.context.view_layer.update()
OUT.mkdir(parents=True,exist_ok=True)
setup()
for n in ['ik_a','ik_b','ik_c','ik_d','ik_e','ik_f']:
 v(n);bpy.context.scene.render.filepath=str(OUT/f'{n}.png');bpy.ops.render.render(write_still=True)
print('IK_PROBE_DONE',OUT)
