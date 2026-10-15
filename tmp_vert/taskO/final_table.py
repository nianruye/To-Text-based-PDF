#!/usr/bin/env python3
"""taskO 最终对账表: 源书(墨迹) vs 产物(文本) 逐页 列数/每列字数/列距/字高/覆盖率。"""
import statistics, sys, fitz, numpy as np
MAP=[(i,i) for i in range(24)]
SRC=[20,21,22,23,24,25,26,27,60,61,62,63,64,65,66,67,80,81,82,83,84,85,86,87]
def gray(d,i):
    p=d[i].get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csGRAY)
    return np.frombuffer(p.samples,dtype=np.uint8).reshape(p.height,p.width)
def otsu(a):
    h=np.bincount(a.ravel(),minlength=256).astype(float); tot=h.sum(); sm=float((np.arange(256)*h).sum())
    best=-1;bk=128;w0=s0=0.0
    for t in range(256):
        w0+=h[t]; s0+=t*h[t]; w1=tot-w0
        if w0<=0 or w1<=0: continue
        v=w0*w1*(s0/w0-(sm-s0)/w1)**2
        if v>best: best,bk=v,t
    return bk
def runs(m,gap=2):
    out=[];i0=None;n=len(m)
    for i,v in enumerate(m):
        if v and i0 is None: i0=i-gap
        elif not v and i0 is not None:
            if i-gap>i0: out.append((max(0,i0),i-gap))
            i0=None
    if i0 is not None and n>i0: out.append((max(0,i0),n))
    return out
def src_stats(a):
    ink=a<otsu(a); H,W=ink.shape
    m=ink[int(H*.02):int(H*.98), int(W*.02):int(W*.98)]
    ys=np.where(m.any(axis=1))[0]; xs=np.where(m.any(axis=0))[0]
    sub=m[ys[0]:ys[-1]+1, xs[0]:xs[-1]+1]
    bands=[(x,y) for x,y in runs(sub.mean(axis=0)>0.12,4) if y-x>=16]
    cs=[(x+y)/2 for x,y in bands]; ds=[b-a for a,b in zip(cs,cs[1:]) if 8<b-a<400]
    hh=[];nn=[]
    for x,y in bands:
        rs=[(p,q) for p,q in runs(sub[:,x:y+1].any(axis=1),1) if q-p>=8]
        if len(rs)<3: continue
        hs=sorted(q-p for p,q in rs); hh.append(hs[len(hs)//2]); nn.append(len(rs))
    return len(bands), (statistics.median(ds)/2 if ds else 0), (statistics.median(hh)/2 if hh else 0), (statistics.median(nn) if nn else 0), float(sub.mean())
def out_stats(p):
    ch=[]
    for b in p.get_text('rawdict')['blocks']:
        for l in b.get('lines',[]):
            for s in l['spans']:
                fs=s['size']; x=l['bbox'][0]
                for c in s['chars']: ch.append((round(c['origin'][0],1), c['c'], fs))
    cols=[]
    for x,c,fs in sorted(ch,key=lambda t:(-t[0],t[1])):
        for col in cols:
            if abs(col['x']-x)<8: col['n']+=1; break
        else: cols.append({'x':x,'n':1,'fs':fs})
    xs=sorted(c['x'] for c in cols); ds=[a-b for a,b in zip(xs,xs[1:])]
    R=p.rect; pix=p.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csGRAY)
    a=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width)
    ink=a<otsu(a); H,W=ink.shape
    m=ink[int(H*.02):int(H*.98), int(W*.02):int(W*.98)]
    ys=np.where(m.any(axis=1))[0]; xs2=np.where(m.any(axis=0))[0]
    sub=m[ys[0]:ys[-1]+1, xs2[0]:xs2[-1]+1]
    return len(cols), (statistics.median(ds) if ds else 0), statistics.median([c['fs'] for c in cols]), float(sub.mean())
do=fitz.open(sys.argv[1]); ds=fitz.open(sys.argv[2])
print('%-4s %-4s | %-34s | %-34s'%('出页','源页','源书 列/列距/字高/每列字/覆盖率','产物 列/列距/字号/每列字/覆盖率'))
acc=[]
for oi,si in enumerate(SRC):
    A=src_stats(gray(ds,si)); B=out_stats(do[oi])
    print('%-4d %-4d | %4d %6.1f %5.1f %5.0f %.3f | %4d %6.1f %5.1f %5.0f %.3f'%(
        oi+1, si+1, A[0],A[1],A[2],A[3],A[4], B[0],B[1],B[2],0,B[3]))
    acc.append((A,B))
print('中位 | %4.0f %6.1f %5.1f %.3f | %4.0f %6.1f %5.1f %.3f'%(
    statistics.median(a[0] for a,b in acc), statistics.median(a[1] for a,b in acc),
    statistics.median(a[2] for a,b in acc), statistics.median(a[4] for a,b in acc),
    statistics.median(b[0] for a,b in acc), statistics.median(b[1] for a,b in acc),
    statistics.median(b[2] for a,b in acc), statistics.median(b[3] for a,b in acc)))
