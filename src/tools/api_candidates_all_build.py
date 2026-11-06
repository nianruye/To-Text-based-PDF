#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""battle6/t27：候选集全量（3828 列）-> 上下文列条带 -> 8 列/页 -> 30 页/批（16 批）PDF。

换书：--book wzX（默认 wz7，向后兼容）；其余参数可显式覆盖。
用法：/usr/bin/python3 src/tools/api_candidates_all_build.py --book wz7
"""
import argparse, json, os, io, tempfile
import numpy as np, fitz
from PIL import Image


def _defaults(book):
    return 'tmp_vert/battle6' if book == 'wz7' else f'tmp_vert/{book}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', default='wz7')
    ap.add_argument('--data-dir', default=None,
                    help='保留兼容（本工具不读 OCR 数据，值未使用）')
    ap.add_argument('--src', default=None, help='默认 source_pdf/{book}.pdf')
    ap.add_argument('--fax', default=None, help='默认 /tmp/{book}_v36_run/fax_pages.json')
    ap.add_argument('--candidates', default=None, help='missing_cells.json；默认 tmp_vert/battle6/missing_cells.json（wz7）')
    ap.add_argument('--out-dir', default=None, help='默认 tmp_vert/battle6（wz7）/ tmp_vert/{book}')
    ap.add_argument('--strips-dir', default=None, help='默认 {out-dir}/all25/strips')
    ap.add_argument('--items-out', default=None, help='默认 {out-dir}/all_items.json')
    ap.add_argument('--plan-out', default=None, help='默认 {out-dir}/all_plan.json')
    ap.add_argument('--cols-per-page', type=int, default=8)
    ap.add_argument('--pages-per-batch', type=int, default=30)
    ap.add_argument('--dpi', type=int, default=200)
    ap.add_argument('--ctx', type=float, default=1.2)
    ap.add_argument('--jpeg-quality', type=int, default=85)
    ap.add_argument('--page-height', type=float, default=None,
                    help='页高(pt)；缺省取源页实际高度 src[pg-1].rect.height')
    a = ap.parse_args()
    out_dir = _defaults(a.book)
    # 注：本工具不读 OCR 数据；--data-dir 仅为与其它工具 CLI 对称而保留（值未使用）
    src_pdf = a.src or f'source_pdf/{a.book}.pdf'
    fax_path = a.fax or os.path.join(tempfile.gettempdir(), f'{a.book}_v36_run', 'fax_pages.json')
    out_dir = a.out_dir or out_dir
    cand_path = a.candidates or ('tmp_vert/battle6/missing_cells.json' if a.book == 'wz7'
                                 else os.path.join(out_dir, 'missing_cells.json'))
    strips_dir = a.strips_dir or os.path.join(out_dir, 'all25', 'strips')
    items_out = a.items_out or os.path.join(out_dir, 'all_items.json')
    plan_out = a.plan_out or os.path.join(out_dir, 'all_plan.json')
    os.makedirs(strips_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'all25'), exist_ok=True)

    D = json.load(open(cand_path, encoding='utf-8'))
    fax = set(json.load(open(fax_path))['pages']) if os.path.exists(fax_path) else set()
    cands = [x for x in D['items'] if x['page'] not in fax and x['text']]
    src = fitz.open(src_pdf)
    items = []
    for i, c in enumerate(cands):
        pg = c['page']; x0, y0, x1, y1 = c['x'], c['y0'], c['x1'], c['y1']
        step_pt = (y1 - y0) / max(1, c['cells'])
        _ph = a.page_height or src[pg - 1].rect.height
        ya = max(0, y0 - a.ctx * step_pt); yb = min(_ph, y1 + a.ctx * step_pt)
        r = fitz.Rect(x0 - 2, ya, x1 + 2, yb)
        pm = src[pg - 1].get_pixmap(clip=r, dpi=a.dpi)
        arr = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)[:, :, :3]
        im = Image.fromarray(arr)
        im = im.resize((int(im.width * 1.2), int(im.height * 1.2)), Image.LANCZOS)
        p = '%s/%05d.png' % (strips_dir, i); im.save(p, quality=90)
        items.append(dict(id=i, page=pg, col=[x0, y0, x1, y1], text=c['text'], n=c['n'],
                          cells=c['cells'], step=round(step_pt, 2), strip=p, w=im.width, h=im.height))
    json.dump(items, open(items_out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    pages = [items[i:i + a.cols_per_page] for i in range(0, len(items), a.cols_per_page)]
    batches = []
    for b in range(0, len(pages), a.pages_per_batch):
        bp = pages[b:b + a.pages_per_batch]
        doc = fitz.open()
        for group in bp:
            pg = doc.new_page(width=400, height=600)
            slot = 400.0 / len(group)
            for k, it in enumerate(group):
                im = Image.open(it['strip'])
                scale = min((slot - 8) / im.width, 580.0 / im.height)
                w, h = im.width * scale, im.height * scale
                x0 = k * slot + (slot - w) / 2; y0 = (600 - h) / 2
                buf = io.BytesIO(); im.save(buf, format='JPEG', quality=a.jpeg_quality)
                pg.insert_image(fitz.Rect(x0, y0, x0 + w, y0 + h), stream=buf.getvalue())
        pth = '%s/batch_%02d.pdf' % (os.path.join(out_dir, 'all25'), len(batches))
        doc.save(pth, deflate=True); doc.close()
        batches.append(dict(batch=len(batches), pdf=pth, pages=len(bp)))
        print('batch', len(batches) - 1, 'pages', len(bp), 'cols', sum(len(g) for g in bp))
    json.dump({'n_items': len(items), 'n_pages': len(pages), 'batches': batches},
              open(plan_out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('items', len(items), 'pages', len(pages), 'batches', len(batches))


if __name__ == '__main__':
    main()
