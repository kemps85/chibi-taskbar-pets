import sys,bpy
from pathlib import Path
ROOT=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game');sys.path.insert(0,str(ROOT/'scripts'));import render_miyabi_taskbar_reference as ref
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);ref.register_mmd_tools();root,arm=ref.import_pmx('星见雅.pmx')
names=['センター','下半身','上半身','上半身1','腰','左足','左ひざ','左足首','左つま先','右足','右ひざ','右足首','右つま先','左足ＩＫ','右足ＩＫ','左つま先ＩＫ','右つま先ＩＫ']
for n in names:
 b=arm.data.bones.get(n);p=arm.pose.bones.get(n)
 if b: print(n.encode('unicode_escape').decode(), 'head',tuple(round(v,4) for v in b.head),'tail',tuple(round(v,4) for v in b.tail),'parent',b.parent.name.encode('unicode_escape').decode() if b.parent else None,'constraints',[(c.type,c.name.encode('unicode_escape').decode()) for c in p.constraints] if p else None)
