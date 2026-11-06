#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""battle6/t26 试建：从 missing_cells 候选均匀抽 2000 列 -> 上下文列条带 -> 8 列/页 -> 25 批 PDF。"""
import json, os, io
import numpy as np, fitz
from PIL import Image
LI = json.load(open('data/wz7_full/wz7_full_spotting_lines_patched.json', encoding='utf-8'))
CO = json.load(open('data/wz7_full/wz7_full_spotting_coords.json', encoding='utf-8'))
SRC = 'source_pdf/wz7.pdf'
OUT = 'tmp_vert/battle6/pilot25'
FAX = '/tmp/wz7_v36_run/fax_pages.json'

def main():
    os.makedirs(OUT + '/strips', exist_ok=True)
    D = json.load(open('tmp_vert/battle6/missing_cells.json', encoding='utf-8'))
    fax = set(json.load(open(FAX))['pages']) if os.path.exists(FAX) else set()
    cands = [x for x in D['items'] if x['page'] not in fax and x['text']]
    # 均匀抽样 2000
    step = max(1, len(cands) // 2000)
    sample = cands[::step][:2000]
    src = fitz.open(SRC)
    items = []
    for i, c in enumerate(sample):
        pg = c['page']; x0, y0, x1, y1 = c['x'], c['y0'], c['x1'], c['y1']
        step_pt = (y1 - y0) / max(1, c['cells'])
        ya = max(0, y0 - 1.2 * step_pt); yb = min(1443, y1 + 1.2 * step_pt)
        r = fitz.Rect(x0 - 2, ya, x1 + 2, yb)
        pm = src[pg - 1].get_pixmap(clip=r, dpi=200)
        a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)[:, :, :3]
        im = Image.fromarray(a)
        im = im.resize((int(im.width * 1.2), int(im.height * 1.2)), Image.LANCZOS)
        p = '%s/strips/%04d.png' % (OUT, i)
        im.save(p, quality=90)
        items.append(dict(id=i, page=pg, ci=c.index if 'index' in c else None, col=[x0, y0, x1, y1],
                          text=c['text'], n=c['n'], cells=c['cells'], step=round(step_pt, 2),
                          strip=p, w=im.width, h=im.height))
    json.dump(items, open('tmp_vert/battle6/pilot25_items.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # 8 列/页，25 批 × 10 页
    PER_PAGE = 8; PER_BATCH = 10
    pages = [items[i:i + PER_PAGE] for i in range(0, len(items), PER_PAGE)]
    batches = []
    for b in range(0, len(pages), PER_BATCH):
        bp = pages[b:b + PER_BATCH]
        doc = fitz.open()
        for pi, group in enumerate(bp):
            pg = doc.new_page(width=400, height=600)
            slot = 400.0 / len(group)
            for k, it in enumerate(group):
                im = Image.open(it['strip'])
                scale = min((slot - 8) / im.width, 580.0 / im.height)
                w, h = im.width * scale, im.height * scale
                x0 = k * slot + (slot - w) / 2; y0 = (600 - h) / 2
                buf = io.BytesIO(); im.save(buf, format='JPEG', quality=85)
                pg.insert_image(fitz.Rect(x0, y0, x0 + w, y0 + h), stream=buf.getvalue())
        pth = '%s/batch_%02d.pdf' % (OUT, len(batches))
        doc.save(pth, deflate=True); doc.close()
        batches.append(dict(batch=len(batches), pdf=pth, pages=len(bp), first=len(batches) * PER_BATCH * PER_PAGE))
        print('batch', len(batches) - 1, 'pages', len(bp), 'cols', sum(len(g) for g in bp))
    json.dump({'n_items': len(items), 'n_pages': len(pages), 'batches': batches},
              open('tmp_vert/battle6/pilot25_plan.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('items', len(items), 'pages', len(pages), 'batches', len(batches))

if __name__ == '__main__':
    main()
