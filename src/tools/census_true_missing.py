#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""battle6/t25 可信真缺字普查（本地、只读源图）：列框外缺字格 + 四类过滤。

输入：data/{book}_full 的 lines/coords + source_pdf/{book}.pdf + 影印页清单（--fax）
判据（缺字格 = 列框上/下一格有墨的格子）：
  F1 影印贴图页（308 页）——按设计不重建文本，整页剔除
  F2 目录/相邻条目误判——同页另一列的框顶/框底落在该格 y 区间(±3pt)且水平距离 ≤1.5 步进
  F3 噪声/非字墨块——最大连通域须 6-40pt 高、fill 0.05-0.70、0.3≤宽高比≤3.5，
     且不是细长竖条（h≥12 且 h/w≥2.5）或圈（hole≥0.10 且 0.6≤w/h≤1.7）
  F4 异体字替换——本工具对「列文本」做 variant_norm 归一化，统计受异体影响的列；
     缺字格本身无文本，异体过滤在 API 复核阶段（col_align 归一化前后）量化
  F5 格内且不压已字——缺字格必须落在本列 x 带内（±2pt），且 y 区间不与列框内文本区重叠
用法（--book 换书；默认 wz7 向后兼容）：
  /usr/bin/python3 src/tools/census_true_missing.py --book wz7 \
      --fax /tmp/{book}_v36_run/fax_pages.json --out tmp_vert/battle6/true_missing.json
  页高：缺省取源页实际高度（src[pg-1].rect.height）；可用 --page-height 显式覆盖（换书/异常纸型）。
"""
import argparse, json, os, statistics, sys, tempfile
import numpy as np
import fitz
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from variant_norm import norm_text

# 模块级占位（勿删：main() 通过 globals 按 --book/--data-dir/--src 覆盖）
LINES = ''
COORDS = ''
SRC = ''

def page_step(ts, bs):
    st = []
    for t, b in zip(ts, bs):
        if not b or len(t) < 8:
            continue
        ys = [q[1] / 2.0 for q in b]
        st.append((max(ys) - min(ys)) / len(t))
    return statistics.median(st) if st else 0.0

def shape_of(m, w_pt, h_pt, step_pt=22.0):
    """返回 (kind, 最大连通域特征)。"""
    lab, n = ndimage.label(m)
    best = None
    for j, s in enumerate(ndimage.find_objects(lab), 1):
        if s is None:
            continue
        hh = s[0].stop - s[0].start; ww = s[1].stop - s[1].start
        if hh < 4 or ww < 4:
            continue
        if best is None or hh * ww > best[0]:
            best = (hh * ww, hh, ww, float((lab[s] == j).mean()), s, j)
    if best is None:
        return 'empty', None
    _, hh, ww, fill, s, j = best
    sub = (lab[s] == j)
    hole = float((ndimage.binary_fill_holes(sub) & ~sub).sum()) / float(sub.size)
    wpt = ww * 72.0 / 300.0; hpt = hh * 72.0 / 300.0
    if hpt >= 12 and wpt <= 5 and hpt / max(wpt, 0.1) >= 2.5:
        kind = 'dash'
    elif 0.6 <= wpt / max(hpt, 0.1) <= 1.7 and 5 <= hpt <= 30 and hole >= 0.10:
        kind = 'ring'
    elif (6 <= hpt <= 40 and 6 <= wpt <= 40 and 0.05 <= fill <= 0.70
          and 0.3 <= wpt / max(hpt, 0.1) <= 3.5
          and hpt >= 0.55 * step_pt and wpt >= 0.45 * step_pt):
        kind = 'char'
    else:
        kind = 'noise'
    return kind, dict(w=round(wpt, 1), h=round(hpt, 1), fill=round(fill, 3), hole=round(hole, 3))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', default='wz7')
    ap.add_argument('--data-dir', default=None, help='默认 data/{book}_full')
    ap.add_argument('--src', default=None, help='默认 source_pdf/{book}.pdf')
    ap.add_argument('--fax', default=None, help='默认 /tmp/{book}_v36_run/fax_pages.json')
    ap.add_argument('--out', default=None, help='默认 tmp_vert/battle6/true_missing.json（wz7）')
    ap.add_argument('--crops', default=None, help='默认 {out-dir}/true_missing_crops')
    ap.add_argument('--dens-min', type=float, default=0.04)
    ap.add_argument('--page-height', type=float, default=None,
                    help='页高(pt)；缺省取源页实际高度 src[pg-1].rect.height')
    a = ap.parse_args()
    data_dir = a.data_dir or f'data/{a.book}_full'
    global LINES, COORDS, SRC
    LINES = os.path.join(data_dir, f'{a.book}_full_spotting_lines_patched.json')
    COORDS = os.path.join(data_dir, f'{a.book}_full_spotting_coords.json')
    SRC = a.src or f'source_pdf/{a.book}.pdf'
    if a.fax is None:
        a.fax = os.path.join(tempfile.gettempdir(), f'{a.book}_v36_run', 'fax_pages.json')
    if a.out is None:
        a.out = ('tmp_vert/battle6/true_missing.json' if a.book == 'wz7'
                 else f'tmp_vert/{a.book}/true_missing.json')
    if a.crops is None:
        a.crops = os.path.join(os.path.dirname(a.out), 'true_missing_crops')
    LI = json.load(open(LINES, encoding='utf-8'))
    CO = json.load(open(COORDS, encoding='utf-8'))
    fax = set()
    if os.path.exists(a.fax):
        fax = set(json.load(open(a.fax))['pages'])
    src = fitz.open(SRC)
    os.makedirs(a.crops, exist_ok=True)
    page_h = a.page_height if a.page_height else None
    items = []
    stats = dict(base=0, fax=0, neighbor=0, noise=0, keep=0, variant_cols=0)
    for pg in range(1, len(LI) + 1):
        k = str(pg - 1)
        if k not in LI:
            continue
        ts = [str(t).replace('\n', '') for t in (LI.get(k) or [])]
        bs = CO.get(k) or []
        step = page_step(ts, bs)
        if step <= 0:
            continue
        # 目录/表格页：短列（n<=8）≥8 列
        n_short = sum(1 for t in ts if t and len(t) <= 8)
        is_toc = n_short >= 8
        for t in ts:
            if t and norm_text(t) != t:
                stats['variant_cols'] += 1
        for ci, (t, b) in enumerate(zip(ts, bs)):
            if not b or not t:
                continue
            xs = [q[0] / 2.0 for q in b]; ys = [q[1] / 2.0 for q in b]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            for side, (ya, yb) in (('top', (y0 - step, y0)), ('bot', (y1, y1 + step))):
                _ph = page_h or src[pg - 1].rect.height
                if ya < 0 or yb > _ph:
                    continue
                stats['base'] += 1
                if pg in fax:
                    stats['fax'] += 1
                    continue
                # F2 目录/相邻条目误判：仅目录页启用，且邻列是短列（TOC 条目）
                claimed = False
                if is_toc:
                    for cj, (t2, b2) in enumerate(zip(ts, bs)):
                        if cj == ci or not b2 or not t2 or len(t2) > 10:
                            continue
                        xs2 = [q[0] / 2.0 for q in b2]; ys2 = [q[1] / 2.0 for q in b2]
                        if abs(min(xs2) - x0) > 1.2 * step and abs(max(xs2) - x1) > 1.2 * step:
                            continue
                        if abs(min(ys2) - ya) <= 4 or abs(max(ys2) - yb) <= 4:
                            claimed = True
                            break
                # 通用：缺字格中心落在另一列框内 -> 该墨属邻列
                if not claimed:
                    cx = (x0 + x1) / 2.0; cy = (ya + yb) / 2.0
                    for cj, (t2, b2) in enumerate(zip(ts, bs)):
                        if cj == ci or not b2 or not t2:
                            continue
                        xs2 = [q[0] / 2.0 for q in b2]; ys2 = [q[1] / 2.0 for q in b2]
                        if min(xs2) - 2 <= cx <= max(xs2) + 2 and min(ys2) <= cy <= max(ys2):
                            claimed = True
                            break
                if claimed:
                    stats['neighbor'] += 1
                    continue
                # 裁片（缺字格）：先用 72dpi 粗筛墨量，再 300dpi 形状
                r = fitz.Rect(x0, ya, x1, yb)
                if r.width < 3 or r.height < 3:
                    continue
                pm0 = src[pg - 1].get_pixmap(clip=r, dpi=72)
                a0 = np.frombuffer(pm0.samples, dtype=np.uint8).reshape(pm0.height, pm0.width, pm0.n)[:, :, :3].mean(axis=2).astype(np.float32)
                if a0.size == 0 or float((a0 < (np.median(a0) - 25)).mean()) < a.dens_min:
                    continue
                pm = src[pg - 1].get_pixmap(clip=r, dpi=300)
                arr = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)[:, :, :3].mean(axis=2).astype(np.float32)
                m = arr < (np.median(arr) - 25)
                dens = float(m.mean())
                if dens < a.dens_min:
                    continue
                kind, feat = shape_of(m, r.width, r.height, step)
                if kind != 'char':
                    stats['noise'] += 1
                    continue
                # F5 格内/不压字：缺字格 x 带已在列内；y 不与列框内文本区重叠（由构造）
                name = 'p%04d_%d_%s.png' % (pg, ci, side)
                from PIL import Image
                Image.fromarray(arr.astype(np.uint8)).resize((96, 96), Image.LANCZOS).save(os.path.join(a.crops, name))
                items.append(dict(page=pg, ci=ci, side=side, x=round(x0, 1), x1=round(x1, 1),
                                  y=round(ya, 1), y1=round(yb, 1), text=t,
                                  step=round(step, 2), dens=round(dens, 3), shape=feat, crop=name))
                stats['keep'] += 1
    json.dump(dict(stats=stats, n=len(items), fax_pages=len(fax), items=items),
              open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(stats, ensure_ascii=False), 'n=', len(items))

if __name__ == '__main__':
    main()
