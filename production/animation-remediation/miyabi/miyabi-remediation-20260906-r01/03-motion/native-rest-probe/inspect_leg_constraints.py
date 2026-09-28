import sys,bpy
from pathlib import Path
ROOT=Path(r"C:\Users\ASUS\Documents\ChatGPT\Game");sys.path.insert(0,str(ROOT/'scripts'));import render_miyabi_taskbar_reference as ref
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);ref.register_mmd_tools();root,arm=ref.import_pmx('星见雅.pmx')
for b in arm.pose.bones:
 if any(s in b.name for s in ['足','ひざ','つま先','IK']):
  print('BONE',b.name.encode('unicode_escape').decode())
  for c in b.constraints:
   print(' ',c.type,c.name.encode('unicode_escape').decode(),'target',getattr(c.target,'name',None),'sub',getattr(c,'subtarget',None),'chain',getattr(c,'chain_count',None),'influence',c.influence)
