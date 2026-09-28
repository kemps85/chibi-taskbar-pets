from PIL import Image,ImageDraw
from pathlib import Path
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
paths=[
root/'assets/runtime/taskbar-pet/clip-packs/miyabi/v1/clips/sleep_enter/right/frames/frame-003.png',
root/'assets/runtime/taskbar-pet/clip-packs/miyabi/v1/clips/sleep_enter/right/frames/frame-004.png',
root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/05-generation/sleep-enter-frame-005-candidate.png',
root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/05-generation/sleep-enter-frame-004-candidate.png']
canvas=Image.new('RGBA',(160*8,144*8*4),(230,230,230,255))
for i,p in enumerate(paths):
 im=Image.open(p).convert('RGBA'); canvas.alpha_composite(im.resize((1280,1152),Image.Resampling.NEAREST),(0,i*1152))
 ImageDraw.Draw(canvas).text((8,i*1152+8),p.stem,fill=(190,0,120,255))
out=root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/06-continuity/sleep-enter-boundary-vertical-8x.png'; canvas.save(out); print(out)
