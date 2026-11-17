#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""源图墨迹 vs 产物 span 的每字宽度比（≥3书，正文+目录）。"""
import argparse, json, statistics, fitz

SRC={'ghbq':'source_pdf/ghbq.pdf','wz1':'source_pdf/wz1.pdf','wz10':'uploads/wz10.pdf'}
CO={'ghbq':'output/ghbq_full/_ocr_ghbq/ghbq_spotting_coords.json','wz1':'data/wz1/wz1_spotting_coords.json','wz10':'output/uploaded/_ocr_wz10/wz10_spotting_coords.json'}
LI={'ghbq':'output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json','wz1':'data/wz1/wz1_spotting_lines.json','wz10':'output/uploaded/_ocr_wz10/wz10_spotting_lines.json'}
DPI={'ghbq':139,'wz1':200,'wz10':132}
def norm(s): return ''.join(c for c in s if c.isalnum() or '\u4e00' <= c <= '\u9fff')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--books',default='ghbq,wz1,wz10'); ap.add_argument('--json',default=''); a=ap.parse_args()
    out={}
    for b in a.books.split(','):
        co=json.load(open(CO[b])); sl=json.load(open(LI[b])); prod=fitz.open(f'deliverables/{b}.pdf'); src=fitz.open(SRC[b]); rows=[]
        for k in list(co)[:200]:
            ik=int(k)
            if ik>=prod.page_count or ik>=src.page_count: continue
            pix=src[ik].get_pixmap(dpi=150); W,H=pix.width,pix.height; img=pix.samples; nc=pix.n
            sm={}
            for i in range(min(len(co[k]),len(sl[k]))):
                if co[k][i] and sl[k][i].strip(): sm.setdefault(norm(sl[k][i]), co[k][i])
            for bl in prod[ik].get_text('dict')['blocks']:
                for l in bl.get('lines',[]):
                    t=''.join(s['text'] for s in l['spans']); nn=norm(t)
                    if len(nn)<8 or nn not in sm: continue
                    poly=sm[nn]; xs=[q[0] for q in poly]; ys=[q[1] for q in poly]
                    x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys); sc=150.0/DPI[b]
                    ax=max(0,int(x0*sc)); bx=min(W,int(x1*sc)); ay=max(0,int(y0*sc)); by=min(H,int(y1*sc)); mn=mx=None
                    for yy in range(ay,by):
                        row=yy*W*nc
                        for xx in range(ax,bx):
                            i=row+xx*nc
                            if img[i]<170 or img[i+1]<170 or img[i+2]<170:
                                mn=xx if mn is None else min(mn,xx); mx=xx if mx is None else max(mx,xx)
                    if mn is None or mx is None or mx<=mn: continue
                    sw=(mx-mn)/150.0*72; ow=l['bbox'][2]-l['bbox'][0]
                    if sw<=0: continue
                    rows.append({'page':ik+1,'chars':len(nn),'src_w':round(sw,2),'out_w':round(ow,2),'ratio':round(ow/sw,4),'text':nn[:24]})
        vals=[r['ratio'] for r in rows]
        out[b]={'dpi':DPI[b],'n':len(rows),'median':round(statistics.median(vals),4) if vals else None,
                'p10':round(statistics.quantiles(vals,n=10)[0],4) if len(vals)>=10 else None,
                'p90':round(statistics.quantiles(vals,n=10)[8],4) if len(vals)>=10 else None,'rows':rows}
        print(b,'dpi',DPI[b],'n',len(rows),'median',out[b]['median'],'p10/p90',out[b]['p10'],out[b]['p90'])
        prod.close(); src.close()
    if a.json: json.dump(out,open(a.json,'w'),ensure_ascii=False,indent=1)
if __name__=='__main__': main()
