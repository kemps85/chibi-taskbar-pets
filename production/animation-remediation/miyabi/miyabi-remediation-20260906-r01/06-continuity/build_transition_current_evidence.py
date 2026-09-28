from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(r"C:\Users\ASUS\Documents\ChatGPT\Game")
C=ROOT/'assets/generated/pixel-chibi/production-v2/hoshimi-miyabi/remediation/miyabi-remediation-20260906-r01'
OUT=ROOT/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/06-continuity'
def sheet(name, ids, labels):
    d=C/name; images=[Image.open(d/f'frame-{i:03}.png').convert('RGBA') for i in ids]
    out=Image.new('RGBA',(640*len(images),612),(226,226,226,255));draw=ImageDraw.Draw(out)
    for j,(im,label) in enumerate(zip(images,labels)):
        out.alpha_composite(im.resize((640,576),Image.Resampling.NEAREST),(j*640,28));draw.text((j*640+8,6),label,fill='magenta')
    out.save(OUT/f'{name}-transition-current-4x.png')
sheet('sleep_enter',[3,4,5,6],['frame-003','frame-004','frame-005 repaired','frame-006'])
sheet('wake',[2,3,4,5],['frame-002','frame-003 repaired','frame-004','frame-005'])
