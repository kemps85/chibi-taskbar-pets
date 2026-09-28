import math,sys,bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(r"C:\Users\ASUS\Documents\ChatGPT\Game");OUT=ROOT/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/03-motion/native-rest-probe/ik-sweep';sys.path.insert(0,str(ROOT/'scripts'));import render_miyabi_taskbar_reference as ref
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
 if name=='zneg': mv('足ＩＫ.L',(0,0,-.55));mv('足ＩＫ.R',(0,0,-.55))
 elif name=='zpos': mv('足ＩＫ.L',(0,0,.55));mv('足ＩＫ.R',(0,0,.55))
 elif name=='yneg': mv('足ＩＫ.L',(0,-.55,0));mv('足ＩＫ.R',(0,-.55,0))
 elif name=='ypos': mv('足ＩＫ.L',(0,.55,0));mv('足ＩＫ.R',(0,.55,0))
 elif name=='xwide': mv('足ＩＫ.L',(.55,0,0));mv('足ＩＫ.R',(-.55,0,0))
 elif name=='crouch':
  mv('センター',(0,0,-.22));mv('足ＩＫ.L',(.2,0,-.45));mv('足ＩＫ.R',(-.2,0,-.45));rot('下半身',(25,0,0));rot('上半身',(18,0,0));rot('上半身1',(18,0,0));rot('首',(10,0,0));rot('頭',(12,0,0))
 elif name=='crouch2':
  mv('センター',(0,0,-.35));mv('足ＩＫ.L',(.25,0,-.7));mv('足ＩＫ.R',(-.25,0,-.7));rot('下半身',(35,0,0));rot('上半身',(25,0,0));rot('上半身1',(25,0,0));rot('首',(15,0,0));rot('頭',(18,0,0))
 elif name=='fold':
  mv('センター',(0,0,-.25));mv('足ＩＫ.L',(.35,0,-.75));mv('足ＩＫ.R',(-.10,0,-.75));rot('下半身',(40,0,8));rot('上半身',(28,0,12));rot('上半身1',(28,0,12));rot('首',(15,0,2));rot('頭',(20,0,0))
 bpy.context.view_layer.update()
OUT.mkdir(parents=True,exist_ok=True);setup()
for n in ['zneg','zpos','yneg','ypos','xwide','crouch','crouch2','fold']:
 pose(n);bpy.context.scene.render.filepath=str(OUT/f'{n}.png');bpy.ops.render.render(write_still=True)
print('IK_SWEEP_DONE',OUT)
