from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
root=Path(r'C:\Users\ASUS\Documents\ChatGPT\Game')
out=root/'production/animation-remediation/miyabi/miyabi-remediation-20260906-r01/04-frame-specs/pose-guides'
out.mkdir(parents=True,exist_ok=True)
W,H=160,144
im=Image.new('RGB',(W,H),(242,242,242)); d=ImageDraw.Draw(im)
# grid and ground
d.line((0,143,159,143),fill=(40,40,40),width=1)
for x in range(0,W,10): d.line((x,0,x,143),fill=(220,220,220),width=1)
for y in range(0,H,10): d.line((0,y,159,y),fill=(220,220,220),width=1)
# approved rest-orientation proposal: feet left, head right, compact leaning support
pts={'heel_L':(18,140),'toe_L':(29,140),'knee_L':(39,133),'knee_R':(51,137),'pelvis':(59,132),'shoulder_L':(77,120),'shoulder_R':(84,117),'elbow':(71,128),'wrist':(62,134),'neck':(89,112),'head':(99,104),'ear_L':(94,95),'ear_R':(104,94),'hilt':(27,126),'weapon_tip':(66,129),'spirit_anchor':(108,119)}
# body action line / skeleton
d.line([pts['heel_L'],pts['knee_L'],pts['pelvis'],pts['shoulder_L'],pts['neck'],pts['head']],fill=(22,110,180),width=2)
d.line([pts['pelvis'],pts['knee_R'],pts['toe_L']],fill=(22,110,180),width=2)
d.line([pts['shoulder_L'],pts['elbow'],pts['wrist']],fill=(180,90,30),width=2)
# coat pool polygon
d.polygon([(43,128),(59,121),(82,116),(87,124),(71,137),(45,142),(29,140)],outline=(22,130,130),fill=(210,235,235))
# head marker
d.ellipse((90,96,108,113),outline=(120,40,120),width=2)
# weapon beside, clearly separate from body
d.line((pts['hilt'][0],pts['hilt'][1],pts['weapon_tip'][0],pts['weapon_tip'][1]),fill=(40,40,40),width=3)
d.line((pts['hilt'][0],pts['hilt'][1]-2,pts['weapon_tip'][0],pts['weapon_tip'][1]-2),fill=(31,155,172),width=1)
# anchor marker
d.ellipse((105,116,111,122),outline=(20,150,80),width=2)
try: f=ImageFont.truetype('segoeui.ttf',7)
except OSError: f=ImageFont.load_default()
labels={'head':'HEAD','pelvis':'PELVIS','support':'GROUND y143','hilt':'WEAPON HILT','spirit_anchor':'VÔ VĨ ANCHOR'}
for key,label in labels.items():
 xy=pts['pelvis'] if key=='pelvis' else pts['hilt'] if key=='hilt' else pts['spirit_anchor'] if key=='spirit_anchor' else pts['head']
 d.text((xy[0]+3,xy[1]-7),label,fill=(0,0,0),font=f)
d.text((3,3),'SLEEP REST PROPOSAL / NOT FINAL ART',fill=(120,0,0),font=f)
d.text((3,11),'feet-left / head-right / protected weapon',fill=(0,0,0),font=f)
path=out/'sleep-rest-frame-000-guide.png'; im.resize((640,576),Image.Resampling.NEAREST).save(path)
print(path)
