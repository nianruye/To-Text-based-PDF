#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""横排标点漏识普查（t257）: 源图墨迹 - OCR 文本覆盖 -> 标点候选。

方法（书无关，无书名/页码特判）:
  1) 源 PDF 页面栅格化（默认 200dpi 灰度），Otsu 二值化；
  2) 8 连通域；用 OCR 行 bbox（坐标换算到栅格）覆盖的墨迹剔除；
  3) 剩余连通域按「正文字高」尺寸窗 + 正文版心 + 非图版/非页眉页脚筛选；
  4) 按可测几何量分类（period/comma/colon/semicolon/quote_open/quote_close/
     bracket/enumeration_comma/dash/ring/other）；
  5) 输出 JSON + 源图裁片，供人工抽样核对。

用法:
  /usr/bin/python3 src/tools/punct_census.py --book ghbq \
    --pdf source_pdf/ghbq.pdf \
    --lines output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json \
    --coords output/ghbq_full/_ocr_ghbq/ghbq_spotting_coords.json \
    --pages 1-104 --out output/ghbq_full/punct_census.json --crops /tmp/punct_census/ghbq
"""
import argparse
import json
import os
import re
import statistics
import sys

import fitz
import numpy as np
from scipy import ndimage


def parse_pages(spec, n):
    if not spec:
        return list(range(n))
    out = []
    for part in str(spec).split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return [p for p in out if 1 <= p <= n]


def otsu(gray):
    hist = np.bincount(np.asarray(gray).ravel(), minlength=256).astype(float)
    tot = hist.sum(); sm = float((np.arange(256) * hist).sum())
    best, bk, w0, s0 = -1.0, 128, 0.0, 0.0
    for t in range(256):
        w0 += hist[t]; s0 += t * hist[t]; w1 = tot - w0
        if w0 <= 0 or w1 <= 0:
            continue
        v = w0 * w1 * (s0 / w0 - (sm - s0) / w1) ** 2
        if v > best:
            best, bk = v, t
    return bk


def is_cjk(ch):
    return '\u4e00' <= ch <= '\u9fff'


def char_units(s):
    return sum(1.0 if is_cjk(c) or c in '，。；：、“”‘’（）【】《》「」『』—…·' else 0.5 for c in s)


def classify(c):
    """可测几何分类。c: x,y,w,h,fill,hole,near,font_h；返回 class。"""
    w, h, fill = c['w'], c['h'], c['fill']
    ar = h / max(w, 1e-6)
    if c.get('hole', 0) >= 1 and 0.45 <= w / max(h, 1e-6) <= 2.1 and h >= 0.35 * c['font_h']:
        return 'ring'
    if ar >= 2.6 or ar <= 0.38:
        if h >= 1.2 * c['font_h'] and w <= 0.55 * c['font_h']:
            return 'bracket'
        if ar >= 2.6 and w >= 0.55 * c['font_h']:
            return 'dash'
    if 0.55 <= ar <= 1.8 and w <= 0.30 * c['font_h'] and h <= 0.40 * c['font_h']:
        if fill >= 0.45:
            return 'period'
        return 'enumeration_comma'
    if ar >= 1.3 and w <= 0.30 * c['font_h'] and h <= 0.55 * c['font_h']:
        return 'comma'
    if ar <= 0.65 and w >= 0.22 * c['font_h'] and h <= 0.40 * c['font_h']:
        return 'quote_open'
    if ar <= 0.65 and w >= 0.22 * c['font_h'] and h <= 0.55 * c['font_h']:
        return 'quote_close'
    if 0.8 <= ar <= 2.2 and fill < 0.38 and w <= 0.35 * c['font_h']:
        return 'semicolon'
    return 'other'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True)
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--lines', required=True)
    ap.add_argument('--coords', required=True)
    ap.add_argument('--pages', default='')
    ap.add_argument('--out', default='')
    ap.add_argument('--crops', default='')
    ap.add_argument('--dpi', type=int, default=200)
    ap.add_argument('--max-crops', type=int, default=60)
    args = ap.parse_args()

    sl = json.load(open(args.lines, encoding='utf-8'))
    co = json.load(open(args.coords, encoding='utf-8'))
    doc = fitz.open(args.pdf)
    pages = parse_pages(args.pages, doc.page_count)
    if args.crops:
        os.makedirs(args.crops, exist_ok=True)
    by_class = {}
    rows = []
    pages_scanned = 0
    notes = []
    crops_done = 0

    for p1 in pages:
        page = doc[p1 - 1]
        key = str(p1 - 1)
        tlines = sl.get(key, [])
        polys = co.get(key, [])
        pix = page.get_pixmap(dpi=args.dpi, colorspace=fitz.csGRAY, alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
        bw = arr < otsu(arr)
        lab, n = ndimage.label(bw, structure=np.ones((3, 3)))
        objs = ndimage.find_objects(lab)
        # OCR 行 bbox（OCR 坐标 -> 栅格）
        xs_all = [q[0] for poly in polys for q in poly]
        ys_all = [q[1] for poly in polys for q in poly]
        ocr_w = max(xs_all) if xs_all else page.rect.width
        ocr_h = max(ys_all) if ys_all else page.rect.height
        sx = pix.width / max(ocr_w, 1e-6)
        sy = pix.height / max(ocr_h, 1e-6)
        boxes = []
        for poly in polys:
            if not poly:
                continue
            xs = [q[0] for q in poly]; ys = [q[1] for q in poly]
            boxes.append((min(xs) * sx, min(ys) * sy, max(xs) * sx, max(ys) * sy))
        # 正文版心: OCR 行 y 中枢 8%~92%，排除页眉/页脚
        body_boxes = [b for b in boxes if b[1] > pix.height * 0.06 and b[3] < pix.height * 0.94]
        if not body_boxes:
            body_boxes = boxes
        body_y0 = min(b[1] for b in body_boxes); body_y1 = max(b[3] for b in body_boxes)
        body_x0 = min(b[0] for b in body_boxes); body_x1 = max(b[2] for b in body_boxes)
        # 行高/字高: OCR 行 bbox 高中位（仅正文）
        hs = [b[3] - b[1] for b in body_boxes if b[3] > b[1]]
        font_h_px = statistics.median(hs) if hs else max(8.0, pix.height * 0.025)
        font_h_pt = font_h_px * 72.0 / args.dpi
        # 字符覆盖率：按 OCR 行文本估算文字宽度，只覆盖行首到「估算文字宽」；
        # 行尾未被 OCR 文本解释的墨迹（漏标点）才进入残差。
        covboxes = []
        for bi, b in enumerate(boxes):
            if bi < len(tlines):
                _t = tlines[bi]
                _u = sum(1.0 if is_cjk(ch) or ch in '，。；：、“”‘’（）【】《》「」『』—…·' else 0.5 for ch in _t)
                _est = _u * (0.52 * font_h_px)
                _cx1 = min(b[2], b[0] + max(_est, 0.15 * (b[2] - b[0])))
            else:
                _cx1 = b[2]
            covboxes.append((b[0], b[1], _cx1, b[3]))
        # 图版区域（任意 image block）
        img_rects = []
        for blk in page.get_text('dict')['blocks']:
            if blk.get('type') == 1:
                r = blk['bbox']
                img_rects.append((r[0] * args.dpi / 72, r[1] * args.dpi / 72,
                                  r[2] * args.dpi / 72, r[3] * args.dpi / 72))
        pages_scanned += 1
        for i, ob in enumerate(objs):
            if ob is None:
                continue
            y0, y1 = ob[0].start, ob[0].stop
            x0, x1 = ob[1].start, ob[1].stop
            w = x1 - x0; h = y1 - y0
            area = int((lab[ob] == i + 1).sum())
            if area < 8 or w < 2 or h < 2:
                continue
            # 正文/图版/页眉页脚
            cy = (y0 + y1) / 2.0; cx = (x0 + x1) / 2.0
            if cy < body_y0 - 0.5 * font_h_px or cy > body_y1 + 0.5 * font_h_px:
                continue
            if cx < body_x0 - 0.5 * font_h_px or cx > body_x1 + 0.5 * font_h_px:
                continue
            if any(a[0] <= cx <= a[2] and a[1] <= cy <= a[3] for a in img_rects):
                continue
            # 被 OCR 行 bbox 覆盖：不是残差
            covered = any(b[0] - 1 <= cx <= b[2] + 1 and b[1] - 1 <= cy <= b[3] + 1 for b in covboxes)
            if covered:
                continue
            # 尺寸窗（相对正文字高）
            if not (0.18 * font_h_px <= h <= 0.75 * font_h_px and 0.12 * font_h_px <= w <= 0.75 * font_h_px):
                continue
            if area > 0.35 * font_h_px * font_h_px:
                continue
            mask = (lab[ob] == i + 1)
            fill = float(mask.mean())
            c = dict(page=p1, x=round(cx * 72.0 / args.dpi, 2), y=round(cy * 72.0 / args.dpi, 2),
                     w=round(w * 72.0 / args.dpi, 2), h=round(h * 72.0 / args.dpi, 2),
                     fill=round(fill, 3), hole=int(ndimage.binary_fill_holes(mask).sum() - mask.sum() > 2),
                     font_h=font_h_pt, near='', in_body=True)
            # 最近 OCR 行文字
            near = min(body_boxes, key=lambda b: (0 if b[0] <= cx <= b[2] else min(abs(cx-b[0]), abs(cx-b[2]))) + 0.2*abs(cy-(b[1]+b[3])/2))
            # 找对应文本 index（以行内水平位置近似）
            t = ''
            if tlines:
                bi = boxes.index(near) if near in boxes else -1
                if 0 <= bi < len(tlines):
                    t = tlines[bi]
            c['nearest_ocr_char'] = t[:36]
            cls = classify(c)
            c['class'] = cls
            del c['fill']
            by_class[cls] = by_class.get(cls, 0) + 1
            rows.append(c)
            if args.crops and crops_done < args.max_crops:
                z = 2.0
                r = fitz.Rect(c['x'] - 12, c['y'] - 12, c['x'] + 12, c['y'] + 12)
                cp = page.get_pixmap(clip=r, matrix=fitz.Matrix(z, z), alpha=False)
                cp.save(os.path.join(args.crops, '%s_p%04d_%03d.png' % (args.book, p1, crops_done)))
                crops_done += 1
    doc.close()
    out = dict(book=args.book, pages_scanned=pages_scanned, pages=pages,
               candidates_total=len(rows), by_class=by_class,
               by_page=rows,
               notes=['OCR 覆盖用行 bbox（无字符级框）；行内漏标点若仍落在行 bbox 内不会被本普查捕获',
                      '尺寸窗/版心/图版/页眉页脚判据写死为相对正文字高',
                      'candidate 的 nearest_ocr_char 为所在 OCR 行文本前 36 字，不是字符级配对'],
               method=dict(dpi=args.dpi, binary='otsu', connected='8-neighbor',
                           body_y=[round(body_y0*72.0/args.dpi,2), round(body_y1*72.0/args.dpi,2)] if pages_scanned else [],
                           font_h_pt=round(font_h_pt,2) if pages_scanned else 0))
    outpath = args.out or os.path.join('output', args.book, 'punct_census.json')
    os.makedirs(os.path.dirname(outpath) or '.', exist_ok=True)
    json.dump(out, open(outpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ('book', 'pages_scanned', 'candidates_total', 'by_class')}, ensure_ascii=False))
    print('out:', outpath)


if __name__ == '__main__':
    main()
