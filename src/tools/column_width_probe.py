#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""源书墨迹栏宽 vs 产物栏宽（150dpi，OCR行x±15pt）。"""
import argparse,json,statistics,fitz
from collections import Counter
SRC={'ghbq':'source_pdf/ghbq.pdf','wz1':'source_pdf/wz1.pdf','wz4':'source_pdf/wz4.pdf','wz10':'uploads/wz10.pdf'}
CO={'ghbq':'output/ghbq_full/_ocr_ghbq/ghbq_spotting_coords.json','wz1':'data/wz1/wz1_spotting_coords.json','wz4':'data/wz4/wz4_spotting_coords.json','wz10':'output/uploaded/_ocr_wz10/wz10_spotting_coords.json'}
LI={'ghbq':'output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json','wz1':'data/wz1/wz1_spotting_lines.json','wz4':'data/wz4/wz4_spotting_lines.json','wz10':'output/uploaded/_ocr_wz10/wz10_spotting_lines.json'}
DPI={'ghbq':139,'wz1':200,'wz4':144,'wz10':132}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--books',default='ghbq,wz1,wz4,wz10');ap.add_argument('--json',default='');a=ap.parse_args();out={}
 for b in a.books.split(','):
  co=json.load(open(CO[b]));sl=json.load(open(LI[b]));src=fitz.open(SRC[b]);prod=fitz.open(f'deliverables/{b}.pdf');vals=[]
  for k in list(co)[:100]:
   ik=int(k)
   if ik>=src.page_count or ik>=prod.page_count:continue
   pix=src[ik].get_pixmap(dpi=150);W,H=pix.width,pix.height;im=pix.samples;nc=pix.n;sc=150.0/DPI[b]
   for i,t in enumerate(sl[k]):
    if i>=len(co[k]) or not co[k][i] or len(t.strip())<10:continue
    xs=[q[0] for q in co[k][i]];ys=[q[1] for q in co[k][i]];x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys)
    a0=max(0,int((x0-15/ (72/DPI[b]))*sc));b0=min(W,int((x1+15/(72/DPI[b]))*sc));ay=max(0,int(y0*sc));by=min(H,int(y1*sc));mn=mx=None
    for yy in range(ay,by):
     row=yy*W*nc
     for xx in range(a0,b0):
      ii=row+xx*nc
      if im[ii]<170 or im[ii+1]<170 or im[ii+2]<170:mn=xx if mn is None else min(mn,xx);mx=xx if mx is None else max(mx,xx)
    if mn is not None and mx is not None and mx>mn:vals.append((mx-mn)/150*72)
  # product width modes
  L=[];R=[]
  for p in prod:
   for bl in p.get_text('dict')['blocks']:
    for l in bl.get('lines',[]):
     t=''.join(s['text'] for s in l['spans']).strip()
     if len(t)>20:L.append(round(l['bbox'][0]));R.append(round(l['bbox'][2]))
  lm=Counter(L).most_common(1)[0][0] if L else None;rm=Counter(R).most_common(1)[0][0] if R else None
  out[b]={'src_median':round(statistics.median(vals),1) if vals else None,'src_n':len(vals),'prod_left':lm,'prod_right':rm,'prod_width':(rm-lm) if lm and rm else None}
  print(b,out[b]);src.close();prod.close()
 if a.json:json.dump(out,open(a.json,'w'),ensure_ascii=False,indent=1)
if __name__=='__main__':main()
