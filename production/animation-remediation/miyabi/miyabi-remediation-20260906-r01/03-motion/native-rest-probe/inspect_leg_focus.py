import sys,bpy
from pathlib import Path
ROOT=Path(r"C:\Users\ASUS\Documents\ChatGPT\Game");sys.path.insert(0,str(ROOT/'scripts'));import render_miyabi_taskbar_reference as ref
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);ref.register_mmd_tools();root,arm=ref.import_pmx('星见雅.pmx')
keys={'足ＩＫ.L','足ＩＫ.R','足IK親.L','足IK親.R','左足IK親','右足IK親','左足ＩＫ','右足ＩＫ','左足','右足','左ひざ','右ひざ','左足首','右足首','センター','下半身'}
for b in arm.data.bones:
 if b.name in keys:
  print('FOCUS',repr(b.name),tuple(round(v,4) for v in b.head),tuple(round(v,4) for v in b.tail),'parent',repr(b.parent.name if b.parent else None), 'use_connect',b.use_connect)
