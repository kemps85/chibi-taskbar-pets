import math,sys,bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(r"C:\Users\ASUS\Documents\ChatGPT\Game");OUT=ROOT/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/03-motion/native-rest-probe/seat-sweep';sys.path.insert(0,str(ROOT/'scripts'));import render_miyabi_taskbar_reference as ref
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
def pose(name):
 base()
 if name=='sit_a':
  mv('センター',(0,0,-.20));mv('足ＩＫ.L',(-.35,0,-.25));mv('足ＩＫ.R',(-.55,0,-.25))
 if name=='sit_b':
  mv('センター',(0,0,-.28));mv('足ＩＫ.L',(-.45,0,-.4));mv('足ＩＫ.R',(-.7,0,-.4))
 if name=='sit_c':
  mv('センター',(0,0,-.35));mv('足ＩＫ.L',(-.55,0,-.55));mv('足ＩＫ.R',(-.85,0,-.55))
 if name=='sit_d':
  mv('センター',(0,0,-.20));mv('足ＩＫ.L',(-.25,0,-.55));mv('足ＩＫ.R',(-.65,0,-.55));rot('下半身',(20,0,0));rot('上半身',(16,0,0));rot('上半身1',(16,0,0));rot('首',(10,0,0));rot('頭',(12,0,0))
 if name=='sit_e':
  mv('センター',(0,0,-.28));mv('足ＩＫ.L',(-.3,0,-.7));mv('足ＩＫ.R',(-.72,0,-.7));rot('下半身',(30,0,0));rot('上半身',(23,0,0));rot('上半身1',(23,0,0));rot('首',(15,0,0));rot('頭',(18,0,0))
 if name=='sit_f':
  mv('センター',(0,0,-.30));mv('足ＩＫ.L',(-.35,0,-.85));mv('足ＩＫ.R',(-.9,0,-.85));rot('下半身',(40,0,0));rot('上半身',(28,0,0));rot('上半身1',(28,0,0));rot('首',(18,0,0));rot('頭',(20,0,0))
 bpy.context.view_layer.update()
OUT.mkdir(parents=True,exist_ok=True);setup()
for n in ['sit_a','sit_b','sit_c','sit_d','sit_e','sit_f']:
 pose(n);bpy.context.scene.render.filepath=str(OUT/f'{n}.png');bpy.ops.render.render(write_still=True)
print('SEAT_SWEEP_DONE',OUT)
