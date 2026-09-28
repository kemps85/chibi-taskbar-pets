import json, sys, numpy as np
from PIL import Image
G='assets/generated/pixel-chibi/imagegen-v1/'
F=lambda pose,ms,**k:{'pose':pose,'ms':ms,**k}
K,BL='idle/k1.png','idle/k2_blink.png'


def blink_mask(c):
    """Paste only the eye band of the imagegen blink onto k1: face = largest light-skin blob."""
    from scipy import ndimage
    k=np.asarray(Image.open(G+c+'/idle/k1.png').convert('RGBA')); b=np.asarray(Image.open(G+c+'/idle/blink_raw.png').convert('RGBA'))
    r,g,bb=[k[...,i].astype(int) for i in range(3)]
    skin=(k[...,3]>0)&(r>215)&(g>180)&(bb>150)&(r>=bb+8)
    top=np.nonzero((k[...,3]>0).any(1))[0].min(); skin[top+55:]=False
    lab,n=ndimage.label(skin); sz=ndimage.sum(skin,lab,range(1,n+1)); face=lab==(int(np.argmax(sz))+1)
    ys,xs=np.nonzero(face); fy0,fy1,fx0,fx1=ys.min(),ys.max(),xs.min(),xs.max()
    y0,y1=fy0-2,fy1+5; x0,x1=fx0-1,fx1+2
    out=k.copy(); out[y0:y1,x0:x1]=b[y0:y1,x0:x1]; Image.fromarray(out,'RGBA').save(G+c+'/idle/k2_blink.png'); return (x0,y0,x1,y1)


def crescent(**k):
    return dict(type='crescent', **k)


SIG={
 'evanescia': lambda: [F(K,300),F('signature/sg1.png',300,fx=[{'type':'sparkle','x':62,'y':104,'r':8,'t':0.1,'color':'pink','count':4}]),F('signature/sg1.png',200,bob=1)]
   +[F('signature/sg2.png',90,fx=[crescent(cx=120+((i*13)%25)-6,cy=80+((i*7)%21)-10,r=22+(i%3)*4,a0=-130+i*47,a1=-20+i*47,thickness=4,colors='pink',progress=1.0)]) for i in range(7)]
   +[F('signature/sg2.png',220,fx=[crescent(cx=124,cy=80,r=30,a0=-110,a1=60,thickness=6,colors='pink',progress=1.0)])]
   +[F('signature/sg2.png',140,fx=[crescent(cx=124,cy=80,r=30,a0=-110,a1=60,thickness=6,colors='pink',decay=d,shard_at=0.5)]) for d in (0.3,0.6,0.9)]
   +[F('signature/sg1.png',200),F('signature/sg1.png',160,fx=[{'type':'sparkle','x':62,'y':104,'r':8,'t':0.5,'color':'pink','count':3}]),F(K,300),F(BL,120),F(K,300)],
 'robin': lambda: [F(K,300),F(BL,120),F(K,200)]
   +[F('signature/sg1.png',250,bob=-(i%2),fx=[{'type':'notes','x':88,'y':66,'t':i*0.07,'count':4},{'type':'sparkle','x':78,'y':30,'r':14,'t':i*0.1,'color':'gold','count':5}]) for i in range(24)]
   +[F(K,200),F(BL,120),F(K,400)],
 'remielle-dan': lambda: [F(K,300),F(BL,120),F(K,250),F(K,150,fx=[{'type':'sparkle','x':70,'y':105,'r':16,'t':0.1,'color':'white','count':5}])]
   +[F('signature/sg1.png',240,bob=-(i%2),fx=[{'type':'sparkle','x':80,'y':110,'r':22,'t':i*0.12,'color':'white','count':4},{'type':'feathers','x0':50,'x1':110,'y0':95,'t':i*0.08,'count':3,'fall':40}]) for i in range(9)]
   +[F(K,150,fx=[{'type':'sparkle','x':70,'y':60,'r':20,'t':0.4,'color':'white','count':6}])]
   +[F('signature/sg2.png',240,bob=-(i%2),fx=[{'type':'sparkle','x':80,'y':45,'r':26,'t':i*0.1,'color':'white' if i%2 else 'pink','count':5},{'type':'feathers','x0':40,'x1':120,'y0':35,'t':i*0.07,'count':4,'fall':70}]) for i in range(11)]
   +[F('signature/sg3.png',900,fx=[{'type':'sparkle','x':76,'y':88,'r':10,'t':0.3,'color':'pink','count':3}]),F('signature/sg3.png',400,bob=1),F(K,300),F(BL,120),F(K,300)],
 'ye-shunguang': lambda: (lambda CASE,RING: [F(K,300),F(K,110,fx=[{'type':'sparkle','x':103,'y':100,'r':14,'t':0.1,'color':'pink','count':5}]),F(K,110,props=CASE,fx=[{'type':'sparkle','x':103,'y':100,'r':18,'t':0.5,'color':'white','count':5}]),
    F('signature/sg1.png',600),F('signature/sg1.png',250,bob=1)]
   +[F('signature/sg1.png',90,fx=[RING(rise=r,t=0.0)]) for r in (0.15,0.35,0.55,0.75,1.0)]
   +[F('signature/sg1.png',200,fx=[RING(t=0.03)])]
   +[F('signature/sg2.png',110,props=CASE,bob=-(i%2),fx=[RING(t=0.06+i*0.07),{'type':'ribbon','x':72,'y':88-i//3,'rx':32,'ry':10,'t':i*0.15,'length':2.2}]) for i in range(12)]
   +[F('signature/sg3.png',130,props=CASE,fx=[RING(t=0.9+i*0.05,fade=(i+1)/7),{'type':'ribbon','x':68,'y':80,'rx':26,'ry':8,'t':2.0+i*0.2,'length':max(0.4,1.6-i*0.2)}]) for i in range(7)]
   +[F('signature/sg3.png',700,props=CASE),F(K,300,props=CASE),F(K,110,fx=[{'type':'sparkle','x':103,'y':100,'r':18,'t':0.7,'color':'pink','count':5}]),F(BL,120),F(K,300)])(
   [{'from':'signature/case.png','bare':'signature/empty.png','pivot':[100,100],'angle':0,'at':[100,100]}],
   lambda **k: {'type':'sword_ring','cx':70,'cy':122,'rx':46,'ry':8,'count':7,'length':28,**k}),
 'ye-shunguang-white': lambda: (lambda CASE,RING: [F(K,300),F(K,110,fx=[{'type':'sparkle','x':103,'y':100,'r':14,'t':0.1,'color':'pink','count':5}]),F(K,110,props=CASE,fx=[{'type':'sparkle','x':103,'y':100,'r':18,'t':0.5,'color':'white','count':5}]),
    F('signature/sg1.png',600),F('signature/sg1.png',250,bob=1)]
   +[F('signature/sg1.png',90,fx=[RING(rise=r,t=0.0)]) for r in (0.15,0.35,0.55,0.75,1.0)]
   +[F('signature/sg1.png',200,fx=[RING(t=0.03)])]
   +[F('signature/sg2.png',110,props=CASE,bob=-(i%2),fx=[RING(t=0.06+i*0.07),{'type':'ribbon','x':72,'y':88-i//3,'rx':32,'ry':10,'t':i*0.15,'length':2.2}]) for i in range(12)]
   +[F('signature/sg3.png',130,props=CASE,fx=[RING(t=0.9+i*0.05,fade=(i+1)/7),{'type':'ribbon','x':68,'y':80,'rx':26,'ry':8,'t':2.0+i*0.2,'length':max(0.4,1.6-i*0.2)}]) for i in range(7)]
   +[F('signature/sg3.png',700,props=CASE),F(K,300,props=CASE),F(K,110,fx=[{'type':'sparkle','x':103,'y':100,'r':18,'t':0.7,'color':'pink','count':5}]),F(BL,120),F(K,300)])(
   [{'from':'signature/case.png','bare':'signature/empty.png','pivot':[100,100],'angle':0,'at':[100,100]}],
   lambda **k: {'type':'sword_ring','cx':70,'cy':122,'rx':46,'ry':8,'count':7,'length':28,**k}),
 'ye-shunguang-red': lambda: (lambda CASE,RING: [F(K,300),F(K,110,fx=[{'type':'sparkle','x':103,'y':100,'r':14,'t':0.1,'color':'pink','count':5}]),F(K,110,props=CASE,fx=[{'type':'sparkle','x':103,'y':100,'r':18,'t':0.5,'color':'white','count':5}]),
    F('signature/sg1.png',600),F('signature/sg1.png',250,bob=1)]
   +[F('signature/sg1.png',90,fx=[RING(rise=r,t=0.0)]) for r in (0.15,0.35,0.55,0.75,1.0)]
   +[F('signature/sg1.png',200,fx=[RING(t=0.03)])]
   +[F('signature/sg2.png',110,props=CASE,bob=-(i%2),fx=[RING(t=0.06+i*0.07),{'type':'ribbon','x':72,'y':88-i//3,'rx':32,'ry':10,'t':i*0.15,'length':2.2}]) for i in range(12)]
   +[F('signature/sg3.png',130,props=CASE,fx=[RING(t=0.9+i*0.05,fade=(i+1)/7),{'type':'ribbon','x':68,'y':80,'rx':26,'ry':8,'t':2.0+i*0.2,'length':max(0.4,1.6-i*0.2)}]) for i in range(7)]
   +[F('signature/sg3.png',700,props=CASE),F(K,300,props=CASE),F(K,110,fx=[{'type':'sparkle','x':103,'y':100,'r':18,'t':0.7,'color':'pink','count':5}]),F(BL,120),F(K,300)])(
   [{'from':'signature/case.png','bare':'signature/empty.png','pivot':[100,100],'angle':0,'at':[100,100]}],
   lambda **k: {'type':'sword_ring','cx':70,'cy':122,'rx':46,'ry':8,'count':7,'length':28,**k}),
 'ye-shunguang-red-white': lambda: (lambda CASE,RING: [F(K,300),F(K,110,fx=[{'type':'sparkle','x':103,'y':100,'r':14,'t':0.1,'color':'pink','count':5}]),F(K,110,props=CASE,fx=[{'type':'sparkle','x':103,'y':100,'r':18,'t':0.5,'color':'white','count':5}]),
    F('signature/sg1.png',600),F('signature/sg1.png',250,bob=1)]
   +[F('signature/sg1.png',90,fx=[RING(rise=r,t=0.0)]) for r in (0.15,0.35,0.55,0.75,1.0)]
   +[F('signature/sg1.png',200,fx=[RING(t=0.03)])]
   +[F('signature/sg2.png',110,props=CASE,bob=-(i%2),fx=[RING(t=0.06+i*0.07),{'type':'ribbon','x':72,'y':88-i//3,'rx':32,'ry':10,'t':i*0.15,'length':2.2}]) for i in range(12)]
   +[F('signature/sg3.png',130,props=CASE,fx=[RING(t=0.9+i*0.05,fade=(i+1)/7),{'type':'ribbon','x':68,'y':80,'rx':26,'ry':8,'t':2.0+i*0.2,'length':max(0.4,1.6-i*0.2)}]) for i in range(7)]
   +[F('signature/sg3.png',700,props=CASE),F(K,300,props=CASE),F(K,110,fx=[{'type':'sparkle','x':103,'y':100,'r':18,'t':0.7,'color':'pink','count':5}]),F(BL,120),F(K,300)])(
   [{'from':'signature/case.png','bare':'signature/empty.png','pivot':[100,100],'angle':0,'at':[100,100]}],
   lambda **k: {'type':'sword_ring','cx':70,'cy':122,'rx':46,'ry':8,'count':7,'length':28,**k}),
}
PIV={'evanescia':104,'robin':116,'remielle-dan':110,'ye-shunguang':126,'ye-shunguang-white':126,'ye-shunguang-red':126,'ye-shunguang-red-white':126}
for c in (sys.argv[1:] or SIG):
    box=blink_mask(c)
    p=G+c+'/clips.json'; s=json.load(open(p,encoding='utf-8'))
    s['clips']={
     'idle':{'loop_policy':'loop','frames':[F(K,400),F(BL,120),F(K,580),F(K,500,bob=-1,trail_bob=0),F(K,700,bob=-1),F(K,500,trail_bob=-1),F(K,1200)]},
     'hunger_cue':{'loop_policy':'once','frames':[F(K,200),F('hunger/hk1.png',160,bob=1,trail_bob=0),F('hunger/hk1.png',200,trail_bob=1),F('hunger/hk1.png',520),F(BL,140),F(K,120)]},
     'eat':{'loop_policy':'once','frames':[F(K,120),F('eat/ek1.png',380),F('eat/ek2.png',300),F('eat/ek2.png',200,bob=1),F('eat/ek1.png',300),F('eat/ek2.png',250),F('eat/ek2.png',150,bob=1),F(BL,140),F(K,160)]},
     'sleep_cue':{'loop_policy':'once','frames':[F(K,200),F(BL,140),F('sleep/sc1.png',360),F('sleep/sc1.png',400,bob=1,trail_bob=0),F('sleep/sc1.png',500,bob=1)]},
     'sleep_enter':{'loop_policy':'once','frames':[F('sleep/sc1.png',150,bob=1),F('sleep/sk0.png',300),F('sleep/sk0.png',150,bob=1),F('sleep/sk1.png',300),F('sleep/sk2.png',300)]},
     'sleep_loop':{'loop_policy':'loop','rig':{'carried':[]},'frames':[F('sleep/sk2.png',500,bob=1,pivot_y=PIV[c]),F('sleep/sk2.png',1000,bob=1,pivot_y=PIV[c]),F('sleep/sk2.png',500,pivot_y=PIV[c]),F('sleep/sk2.png',1000,pivot_y=PIV[c])]},
     'wake':{'loop_policy':'once','frames':[F('sleep/sk2.png',80),F('sleep/sk1.png',150),F('sleep/sk0.png',200),F(K,150,bob=1,trail_bob=1),F(K,150,trail_bob=1,trail_dx=-1),F(K,120)]},
     'signature':{'loop_policy':'once','frames':SIG[c]()},
    }
    open(p,'w',encoding='utf-8').write(json.dumps(s,indent=2,ensure_ascii=False)+'\n')
    print(c,'blink box',box,'signature ms',sum(f['ms'] for f in s['clips']['signature']['frames']))
