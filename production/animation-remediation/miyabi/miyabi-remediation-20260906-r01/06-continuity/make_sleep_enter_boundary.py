from PIL import Image,ImageDraw
from pathlib import Path
paths=[
Path(r'C:\Users\ASUS\Documents\ChatGPT\Game\assets\runtime\taskbar-pet\clip-packs\miyabi\v1\clips\sleep_enter\right\frames\frame-003.png'),
Path(r'C:\Users\ASUS\Documents\ChatGPT\Game\assets\runtime\taskbar-pet\clip-packs\miyabi\v1\clips\sleep_enter\right\frames\frame-004.png'),
Path(r'C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\05-generation\sleep-enter-frame-005-candidate.png'),
Path(r'C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\05-generation\sleep-enter-frame-004-candidate.png'),
]
out=Image.new('RGBA',(160*4*4,160*4),(226,226,226,255))
for i,p in enumerate(paths):
 im=Image.open(p).convert('RGBA'); cell=Image.new('RGBA',(160,160),(226,226,226,255)); cell.alpha_composite(im,(0,0)); ImageDraw.Draw(cell).text((2,1),p.stem,fill=(180,0,120,255)); out.alpha_composite(cell.resize((640,640),Image.Resampling.NEAREST),(i*640,0))
out.save(r'C:\Users\ASUS\Documents\ChatGPT\Game\production\animation-remediation\miyabi\miyabi-remediation-20260906-r01\06-continuity\sleep-enter-boundary-003-004-005-006-4x.png')
