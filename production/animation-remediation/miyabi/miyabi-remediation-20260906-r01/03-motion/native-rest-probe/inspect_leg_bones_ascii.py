import sys,bpy
from pathlib import Path
ROOT=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game');sys.path.insert(0,str(ROOT/'scripts'));import render_miyabi_taskbar_reference as ref
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);ref.register_mmd_tools();root,arm=ref.import_pmx('星见雅.pmx')
for b in arm.data.bones:
 n=b.name
 if any(s in n for s in ['足','ひざ','膝','つま先','IK']): print(n.encode('unicode_escape').decode(),tuple(round(v,4) for v in b.head),tuple(round(v,4) for v in b.tail),'parent',b.parent.name.encode('unicode_escape').decode() if b.parent else None)
