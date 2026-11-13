#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t259: 标点残差普查（span 级）——产物 PDF glyph 框作解释层。

源图栅格连通域 -> 剔除与产物 PDF 任一 glyph bbox（外扩 0.5pt）重叠的墨块
-> 剩余墨块按正文字高/字宽尺寸窗 + 正文版心 + 图版/页眉页脚过滤 + 距 glyph
>=0.08 字宽筛候选 -> 几何分类 -> JSON/裁片/抽样。

用法:
  /usr/bin/python3 src/tools/punct_span_residual.py --book ghbq \
    --src-pdf source_pdf/ghbq.pdf --out-pdf output/ghbq_full/ghbq_p97v2.pdf \
    --pages 1-104 --out output/ghbq_full/punct_span_residual.json --crops /tmp/punct_span/ghbq
"""
import argparse, json, os, random, re, statistics
import fitz
import numpy as np
from scipy import ndimage

PUNCT = '，。；：、“”‘’（）【】《》「」『』—…·、！？'


def parse_pages(spec, n):
    if not spec: return list(range(1, n + 1))
    out = []
    for p in spec.split(','):
        p = p.strip()
        if not p: continue
        if '-' in p:
            a, b = p.split('-', 1); out += list(range(int(a), int(b) + 1))
        else: out.append(int(p))
    return [x for x in out if 1 <= x <= n]


def otsu(gray):
    hist = np.bincount(np.asarray(gray).ravel(), minlength=256).astype(float)
    tot = hist.sum(); sm = float((np.arange(256) * hist).sum())
    best, bk, w0, s0 = -1.0, 128, 0.0, 0.0
    for t in range(256):
        w0 += hist[t]; s0 += t * hist[t]; w1 = tot - w0
        if w0 <= 0 or w1 <= 0: continue
        v = w0 * w1 * (s0 / w0 - (sm - s0) / w1) ** 2
        if v > best: best, bk = v, t
    return bk


def is_cjk(c): return '\u4e00' <= c <= '\u9fff'


def classify(c):
    w, h, fh, fill, hole = c['w'], c['h'], c['fh'], c['fill'], c['hole']
    ar = h / max(w, 1e-6)
    if hole >= 1 and 0.45 <= w / max(h, 1e-6) <= 2.1 and h >= 0.32 * fh:
        return 'ring'
    if ar >= 2.6 or ar <= 0.38:
        if h >= 1.15 * fh and w <= 0.55 * fh: return 'bracket'
        if ar >= 2.6 and w >= 0.45 * fh: return 'dash'
    if 0.5 <= ar <= 1.8 and w <= 0.30 * fh and h <= 0.40 * fh:
        return 'period' if fill >= 0.42 else 'enumeration_comma'
    if ar >= 1.3 and w <= 0.32 * fh and h <= 0.58 * fh: return 'comma'
    if ar <= 0.70 and 0.22 * fh <= w <= 0.60 * fh and h <= 0.45 * fh: return 'quote_open'
    if ar <= 0.70 and 0.22 * fh <= w <= 0.60 * fh and h <= 0.60 * fh: return 'quote_close'
    if 0.8 <= ar <= 2.2 and fill < 0.38 and w <= 0.36 * fh: return 'semicolon'
    return 'other'


def glyphs_of(page):
    """返回 [(char, bbox, line_idx, char_idx)]；bbox PDF pt。"""
    raw = page.get_text('rawdict')
    out = []
    for bi, blk in enumerate(raw.get('blocks', [])):
        for li, line in enumerate(blk.get('lines', [])):
            for si, span in enumerate(line.get('spans', [])):
                for ci, ch in enumerate(span.get('chars', [])):
                    c = ch.get('c', '')
                    if not c.strip(): continue
                    out.append((c, tuple(ch['bbox']), (bi, li), len(out)))
    return out


def bbox_dist(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return (dx * dx + dy * dy) ** 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True)
    ap.add_argument('--src-pdf', required=True)
    ap.add_argument('--out-pdf', required=True)
    ap.add_argument('--pages', default='')
    ap.add_argument('--out', default='')
    ap.add_argument('--crops', default='')
    ap.add_argument('--dpi', type=int, default=200)
    ap.add_argument('--sample', type=int, default=30)
    ap.add_argument('--seed', type=int, default=20261112)
    ap.add_argument('--gold', default='')
    args = ap.parse_args()

    src = fitz.open(args.src_pdf); out = fitz.open(args.out_pdf)
    pages = parse_pages(args.pages, min(src.page_count, out.page_count))
    if args.crops: os.makedirs(args.crops, exist_ok=True)
    all_c = []; audit = []
    for p1 in pages:
        sp = src[p1 - 1]; op = out[p1 - 1]
        pix = sp.get_pixmap(dpi=args.dpi, colorspace=fitz.csGRAY, alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
        bw = arr < otsu(arr)
        # 解释层：产物 PDF 同 DPI 栅格化；source-only 墨迹 = 源墨 - 产物墨（膨胀1px）
        try:
            opix = op.get_pixmap(dpi=args.dpi, colorspace=fitz.csGRAY, alpha=False)
            oarr = np.frombuffer(opix.samples, dtype=np.uint8).reshape(opix.height, opix.width)
            if oarr.shape != bw.shape:
                import numpy as _np
                oarr = _np.array(fitz.Pixmap(fitz.csGRAY, opix).tobytes()) if False else oarr
            obw = oarr < otsu(oarr)
            obw = ndimage.binary_dilation(obw, iterations=1)
            if obw.shape == bw.shape:
                bw = bw & ~obw
        except Exception as _e:
            pass
        lab, n = ndimage.label(bw, structure=np.ones((3, 3)))
        objs = ndimage.find_objects(lab)
        sx = pix.width / max(sp.rect.width, 1e-6)
        sy = pix.height / max(sp.rect.height, 1e-6)
        gl = glyphs_of(op)
        # glyph 覆盖（外扩0.5pt）
        covered = np.zeros((pix.height, pix.width), dtype=bool)
        for _, bb, _, _ in gl:
            x0 = max(0, int((bb[0] - 0.5) * sx)); x1 = min(pix.width, int((bb[2] + 0.5) * sx) + 1)
            y0 = max(0, int((bb[1] - 0.5) * sy)); y1 = min(pix.height, int((bb[3] + 0.5) * sy) + 1)
            if x1 > x0 and y1 > y0: covered[y0:y1, x0:x1] = True
        # 正文/字号：产物 glyph 统计
        ghs = [bb[3] - bb[1] for _, bb, _, _ in gl if bb[3] > bb[1]]
        gws = [bb[2] - bb[0] for _, bb, _, _ in gl if bb[2] > bb[0]]
        if not ghs: continue
        line_h = float(np.percentile(ghs, 75))
        char_w = float(np.percentile(gws, 60))
        body_y0 = 0.05 * sp.rect.height; body_y1 = 0.95 * sp.rect.height
        # 图版区域（source PDF image blocks）
        img_rects = []
        for blk in sp.get_text('dict')['blocks']:
            if blk.get('type') == 1:
                r = blk['bbox']
                if (r[2]-r[0])*(r[3]-r[1]) < 0.5 * sp.rect.width * sp.rect.height:
                    img_rects.append(r)
        # 页眉页脚：glyph 外 8% 页高
        _dbg = {'objs':0,'uncov':0,'sz':0,'body':0}
        for i, ob in enumerate(objs):
            _dbg['objs'] += 1
            if ob is None: continue
            y0, y1 = ob[0].start, ob[0].stop; x0, x1 = ob[1].start, ob[1].stop
            w = x1 - x0; h = y1 - y0
            if w < 2 or h < 2: continue
            area = int((lab[ob] == i + 1).sum())
            if area < 8: continue
            cy = (y0 + y1) / 2.0; cx = (x0 + x1) / 2.0
            if cy < body_y0 - 0.5 * line_h or cy > body_y1 + 0.5 * line_h: continue
            if cx < 0.03 * sp.rect.width or cx > 0.97 * sp.rect.width: continue
            if any(a[0] - 1 <= cx * 72 / args.dpi <= a[2] + 1 and a[1] - 1 <= cy * 72 / args.dpi <= a[3] + 1 for a in img_rects): continue
            _dbg['uncov'] += 1
            # 尺寸窗
            if not (0.15 * line_h <= h * 72 / args.dpi <= 0.80 * line_h and 0.10 * char_w <= w * 72 / args.dpi <= 0.80 * char_w): continue
            _dbg['sz'] += 1
            if (w * h) * (72 / args.dpi) ** 2 > 0.40 * line_h * char_w: continue
            mask = lab[ob] == i + 1
            fill = float(mask.mean())
            bb_pt = (x0 * 72 / args.dpi, y0 * 72 / args.dpi, x1 * 72 / args.dpi, y1 * 72 / args.dpi)
            dist = min((bbox_dist(bb_pt, g[1]) for g in gl), default=99.0)
            c = dict(page=p1, cls='', x_px=x0, y_px=y0, bbox=[round(v, 2) for v in bb_pt],
                     w=round((x1 - x0) * 72 / args.dpi, 2), h=round((y1 - y0) * 72 / args.dpi, 2),
                     area=round(area * (72 / args.dpi) ** 2, 2), aspect=round(h / max(w, 1), 2),
                     fill=round(fill, 3), hole=int(ndimage.binary_fill_holes(mask).sum() - mask.sum() > 2),
                     fh=line_h, nearest_glyph_dist=round(dist, 2), in_body=True)
            c['cls'] = classify(c)
            # 前后各 3 个产物字符
            near = sorted(gl, key=lambda g: bbox_dist(bb_pt, g[1]))
            c['surround_chars'] = [dict(ch=g[0], bbox=[round(v, 2) for v in g[1]], d=round(bbox_dist(bb_pt, g[1]), 2)) for g in near[:6]]
            c['nearest_ocr_char'] = ''.join(g[0] for g in near[:3])
            all_c.append(c)
        if os.environ.get('PUNCT_SPAN_DBG'): print('DBG', p1, _dbg, 'line_h', line_h, 'char_w', char_w, 'glyphs', len(gl), flush=True)
    # 抽样（确定性）
    rng = random.Random(args.seed)
    sample = sorted(rng.sample(range(len(all_c)), min(args.sample, len(all_c)))) if all_c else []
    # 生成裁片（抽样 + 前30）
    if args.crops and all_c:
        src2 = fitz.open(args.src_pdf)
        for j in sample:
            c = all_c[j]; pg = src2[c['page'] - 1]
            x0, y0, x1, y1 = c['bbox']; pad = max(8, (y1 - y0) * 2)
            clip = fitz.Rect(max(0, x0 - pad), max(0, y0 - pad), min(pg.rect.width, x1 + pad), min(pg.rect.height, y1 + pad))
            p = pg.get_pixmap(clip=clip, matrix=fitz.Matrix(4, 4), alpha=False)
            p.save(os.path.join(args.crops, 'sample_%03d_p%04d.png' % (j, c['page'])))
        src2.close()
    outobj = dict(book=args.book, src_pdf=args.src_pdf, out_pdf=args.out_pdf, pages=pages,
                  pages_scanned=len(pages), candidates_total=len(all_c),
                  by_class={k: sum(1 for c in all_c if c['cls'] == k) for k in sorted(set(c['cls'] for c in all_c))},
                  candidates=all_c, sample_indices=sample,
                  sample=[all_c[j] for j in sample],
                  notes=['解释层=产物 PDF rawdict glyph bbox 外扩0.5pt',
                         '源图栅格在源 PDF 页面坐标系；产物/源页尺寸需一致（不同则需先对齐）',
                         '样本裁片只画源图；glyph 框叠画由审计脚本完成'])
    # gold sanity（可选）：候选最近 gold bbox <= 8pt 计命中
    if args.gold and os.path.exists(args.gold):
        g = json.load(open(args.gold))
        items = [it for it in g.get('items', []) if it.get('book') == args.book]
        gpages = set(pages); items = [it for it in items if it.get('page') in gpages]
        hit = 0; used = set()
        for it in items:
            bb = it.get('bbox')
            if not bb: continue
            for i, c in enumerate(all_c):
                if c['page'] != it['page']: continue
                if bbox_dist(c['bbox'], tuple(bb)) <= 8.0:
                    hit += 1; used.add(i); break
        outobj['gold_check'] = dict(gold=args.gold, gold_items=len(items), candidates=len(all_c),
                                    gold_hit=hit, gold_hit_rate=round(hit / max(1, len(items)), 3),
                                    note='对 gold 全部标点（非仅 FN）；FN 命中需 punct_eval 的 FN 子集')
    opath = args.out or os.path.join('output', args.book, 'punct_span_residual.json')
    os.makedirs(os.path.dirname(opath) or '.', exist_ok=True)
    json.dump(outobj, open(opath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: outobj[k] for k in ('book', 'pages_scanned', 'candidates_total', 'by_class')}, ensure_ascii=False))
    print('out:', opath)


if __name__ == '__main__':
    main()
