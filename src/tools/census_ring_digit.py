#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""普查漏掉的第二类圈码：格子里被 OCR 的「数字」占住的 ring

判据与任务E同源（径向剖面），只是**放开「该格必须有 OCR 字符」这条排除**：
  列框最后一格 / 第一格里 OCR 文本是数字（0-9 / ０-９，1-2 位）
  且源图那一格是圆环（有洞 + 圈内空 + 四边有墨）
-> 这些是「圈码被 OCR 读成普通数字」，应当 1:1 换成 ①-⑳
"""
import json
import re
import sys

import numpy as np
import fitz
from scipy import ndimage

LINES = 'data/wz7_full/wz7_full_spotting_lines_patched.json'
COORDS = 'data/wz7_full/wz7_full_spotting_coords.json'
SRC = 'source_pdf/wz7.pdf'
P0, P1 = int(sys.argv[1]) if len(sys.argv) > 1 else 1, int(sys.argv[2]) if len(sys.argv) > 2 else 1748

sl = json.load(open(LINES, encoding='utf-8'))
co = json.load(open(COORDS, encoding='utf-8'))
src = fitz.open(SRC)
DIG = re.compile(r'[0-9\uff10-\uff19]+$')

cands = []
for k in sl:
    pi = int(k) + 1
    if not (P0 <= pi <= P1):
        continue
    rows = sl[k] or []
    boxes = co.get(k) or []
    for i, t in enumerate(rows):
        t = str(t).replace('\n', '')
        if not t or i >= len(boxes):
            continue
        m = DIG.search(t)
        if not m:
            continue
        num = m.group()
        if len(num) > 2:
            continue
        # 纯 0（'0'/'00'）= OCR 把「〇」读成数字，是页码/卷次，不是圈码
        if num.strip('0\uff10') == '':
            continue
        xs = [q[0] / 2.0 for q in boxes[i]]
        ys = [q[1] / 2.0 for q in boxes[i]]
        cands.append(dict(page=pi, row=i, text=t, num=num, n=len(t),
                          x0=min(xs), x1=max(xs), y0=min(ys), y1=max(ys)))

print('列尾是数字的列: %d 处 / %d 页' % (len(cands), len(set(c['page'] for c in cands))))

# 本页真实步进：取 n>=8 的长列的「框高/字数」中位。
#   短列（如 '。12' 3 字）的框高/字数 不是步进（p1684 行14: 13.4 vs 真实 18.5），
#   按它开窗口会把 18.7pt 的圆环裁掉。
def _page_step(k):
    st = []
    for t, p in zip(sl.get(k, []), co.get(k, []) or []):
        t = str(t).replace('\n', '')
        if len(t) < 8 or not p:
            continue
        ys = [q[1] / 2.0 for q in p]
        st.append((max(ys) - min(ys)) / len(t))
    if not st:
        return None
    st.sort()
    return st[len(st) // 2]


def ring_at(c, page_step=None):
    """量列尾最后一格的圆环特征"""
    step = page_step or ((c['y1'] - c['y0']) / max(1, c['n']))
    pg = src[c['page'] - 1]
    ya = c['y1'] - step
    clip = fitz.Rect(max(0, c['x0'] - 1), ya, min(pg.rect.width, c['x1'] + 1), c['y1'] + 1)
    if clip.height < 3 or clip.width < 3:
        return None
    pm = pg.get_pixmap(clip=clip, dpi=600)
    a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)
    g = a[:, :, :3].mean(axis=2)
    m = g < (float(np.median(g)) - 20)
    lab, n = ndimage.label(m)
    if n == 0:
        return None
    best = None
    for sl_ in ndimage.find_objects(lab):
        if sl_ is None:
            continue
        ys_, xs_ = sl_
        hh, ww = ys_.stop - ys_.start, xs_.stop - xs_.start
        if hh < 6 or ww < 6:
            continue
        sub = m[ys_.start:ys_.stop, xs_.start:xs_.stop]
        H, W = sub.shape
        def q(a0, a1, b0, b1):
            b = sub[int(a0*H):max(int(a1*H), int(a0*H)+1), int(b0*W):max(int(b1*W), int(b0*W)+1)]
            return float(b.mean()) if b.size else 1.0
        ctr = q(.35, .65, .35, .65)
        edge = min(q(.2,.8,0,.2), q(.2,.8,.8,1.), q(0,.2,.2,.8), q(.8,1.,.2,.8))
        # 洞
        filled = ndimage.binary_fill_holes(sub)
        hole = float((filled & ~sub).sum()) / float(sub.size)
        ar = ww / float(hh)
        # ★ 2026-10-24 修正：原来要求 ctr < 0.35（圈心要空），把「圈里装着数字」的圈码
        #   整类排除了（用户实测 p1684 x222/x155/x122 三处源书有圈，中心填充 0.5-0.6）。
        #   改为只看「有没有洞 + 填充不过高 + 尺寸是一整格」。
        side_pt = ww * 72.0 / 600.0
        # ctr 的**下界**才是区分量（不是上界）：圈里装着数字 -> 中心有墨 ctr>=0.15；
        #   「〇」写的页码 / 口日等字形 -> 中心全空 ctr=0.00（全书实测 11 处假阳全是这样）
        score = ((hole >= 0.10) and (ctr >= 0.15) and (sub.mean() <= 0.78)
                 and (0.6 <= ar <= 1.7) and (14.0 <= side_pt <= 23.0))
        if score and (best is None or hh * ww > best[0]):
            best = (hh * ww, dict(ctr=round(ctr,2), edge=round(edge,2), hole=round(hole,2),
                                  ar=round(ar,2), k=72.0/600.0, hh=round(hh*72.0/600,1)))
    return best[1] if best else None

hits = []
_pstep_cache = {}
for c in cands:
    _k = str(c['page'] - 1)
    if _k not in _pstep_cache:
        _pstep_cache[_k] = _page_step(_k)
    r = ring_at(c, _pstep_cache[_k])
    if r:
        hits.append(dict(c, **r))
print()
print('其中源图列尾格是圆环的: %d 处 / %d 页'
      % (len(hits), len(set(h['page'] for h in hits))))
from collections import Counter
print('  涉及页: %s' % sorted(Counter(h['page'] for h in hits).items())[:25])
print()
print('  前 20 处:')
for h in hits[:20]:
    print('    p%-5d 行%-3d 列尾数字 %-4r 环 ctr%.2f edge%.2f hole%.2f ar%.2f  文本 %r'
          % (h['page'], h['row'], h['num'], h['ctr'], h['edge'], h['hole'], h['ar'], h['text'][-16:]))
json.dump(hits, open('tmp_vert/cj5/ring_digit_census.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print()
print('明细 -> tmp_vert/cj5/ring_digit_census.json')
src.close()
