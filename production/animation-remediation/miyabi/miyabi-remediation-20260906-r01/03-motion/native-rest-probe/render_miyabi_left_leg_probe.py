import math,sys,bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(r"C:\Users\ASUS\Documents\ChatGPT\Game");OUT=ROOT/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/03-motion/native-rest-probe/left-leg';sys.path.insert(0,str(ROOT/'scripts'));import render_miyabi_taskbar_reference as ref
ARM=None;CHAR=None;WEAPON=None;WARM=None
def rot(n,v):ref.rotate(ARM,n,v)
def setup():
 global ARM,CHAR,WEAPON,WARM
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);ref.register_mmd_tools();CHAR,ARM=ref.import_pmx('星见雅.pmx');WEAPON,WARM=ref.import_pmx('武器.pmx');ref.create_arm_ik(ARM);CHAR.rotation_euler[2]=math.radians(-12);WEAPON.location=(-.02,.18,.72);WEAPON.rotation_euler=(math.radians(4),math.radians(-7),math.radians(-7))
 for b in ARM.pose.bones:
  for c in b.constraints:
   if c.type=='IK': c.influence=0
 for n in ('Bn_katana_burst01','Bn_katana_burst02','Bn_katana_burst03','Bn_katana_burst04','Bn_katana_burst','Bn_katana_burst_eye','Bn_PET','Bn_PET_EYE'):
  b=WARM.pose.bones.get(n)
  if b:b.scale=(.001,.001,.001)
 ref.configure_scene();c=bpy.context.scene.camera;c.data.ortho_scale=2.35;c.location.z+=.02;ref.point_at(c,Vector((0,0,.72)))
def base():
 ref.pose_stand(ARM);CHAR.location=(0,0,0);CHAR.rotation_euler=(0,0,math.radians(-12));WEAPON.location=(-.02,.18,.72);WEAPON.rotation_euler=(math.radians(4),math.radians(-7),math.radians(-7))
def pose(name):
 base()
 if name=='xneg30': rot('足.L',(-30,0,0));rot('ひざ.L',(60,0,0));rot('足.R',(-30,0,0));rot('ひざ.R',(60,0,0))
 elif name=='xneg60': rot('足.L',(-60,0,0));rot('ひざ.L',(120,0,0));rot('足.R',(-60,0,0));rot('ひざ.R',(120,0,0))
 elif name=='xneg90': rot('足.L',(-90,0,0));rot('ひざ.L',(150,0,0));rot('足.R',(-90,0,0));rot('ひざ.R',(150,0,0))
 elif name=='xneg90_asym': rot('足.L',(-105,0,0));rot('ひざ.L',(150,0,0));rot('足.R',(-75,0,0));rot('ひざ.R',(130,0,0))
 elif name=='xneg90body': rot('足.L',(-90,0,0));rot('ひざ.L',(150,0,0));rot('足.R',(-90,0,0));rot('ひざ.R',(150,0,0));rot('下半身',(0,0,10));rot('上半身',(0,0,8));rot('上半身1',(0,0,8))
 elif name=='rest': rot('足.L',(-105,0,0));rot('ひざ.L',(160,0,0));rot('足.R',(-78,0,0));rot('ひざ.R',(135,0,0));rot('下半身',(0,0,14));rot('上半身',(0,0,10));rot('上半身1',(0,0,10));rot('首',(0,0,-4));rot('頭',(0,0,-6))
 bpy.context.view_layer.update()
setup();OUT.mkdir(parents=True,exist_ok=True)
for n in ['xneg30','xneg60','xneg90','xneg90_asym','xneg90body','rest']:
 pose(n);bpy.context.scene.render.filepath=str(OUT/f'{n}.png');bpy.ops.render.render(write_still=True)
print('LEFT_LEG_DONE',OUT)
