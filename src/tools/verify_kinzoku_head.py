#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E1 重做：从全部 3100 处里随机抽 30，直接量该列**首格**的源图墨迹

判据（不依赖「找上一段」）：
  取该列首格 = 列框顶部 1 个步进高、整列宽
  量该格墨量占比与形状：
    标点（，。：」）   墨量占格 10-35%，墨迹偏居一角/较小
    汉字              墨量占格 35-65%
  若首格墨量与同列其它格的「汉字格」明显不同（偏少）= 源书首格确实是标点
"""
import json
import random

import numpy as np
import fitz

LINES = 'data/wz7_full/wz7_full_spotting_lines_patched.json'
COORDS = 'data/wz7_full/wz7_full_spotting_coords.json'
SRC = 'source_pdf/wz7.pdf'
BAD_HEAD = '，。：、；」』！？…·'

sl = json.load(open(LINES, encoding='utf-8'))
co = json.load(open(COORDS, encoding='utf-8'))

cases = []
for k in sl:
    for i, t in enumerate(sl[k] or []):
        t = str(t).replace('\n', '')
        if not t or t[0] not in BAD_HEAD:
            continue
        boxes = co.get(k) or []
        if i >= len(boxes):
            continue
        xs = [q[0] / 2.0 for q in boxes[i]]
        ys = [q[1] / 2.0 for q in boxes[i]]
        cases.append(dict(page=int(k) + 1, ch=t[0], text=t[:16], n=len(t),
                          x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys)))

print('全部列首标点 %d 处 / %d 页' % (len(cases), len(set(c['page'] for c in cases))))
random.seed(20261024)
sample = random.sample(cases, 30)
src = fitz.open(SRC)

print()
print('  页    首字  步进  首格墨量  后续格墨量(中位)  首/后  判定')
rows = []
for c in sorted(sample, key=lambda z: z['page']):
    step = (c['y1'] - c['y0']) / max(1, c['n'])
    pg = src[c['page'] - 1]
    inkm = []
    for gi in range(min(c['n'], 8)):
        ya = c['y0'] + gi * step
        yb = ya + step
        if yb > pg.rect.height:
            break
        clip = fitz.Rect(max(0, c['x0'] - 1), ya, min(pg.rect.width, c['x1'] + 1), yb)
        if clip.height < 2 or clip.width < 2:
            break
        pm = pg.get_pixmap(clip=clip, dpi=500)
        a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)
        g = a[:, :, :3].mean(axis=2)
        inkm.append(float((g < (float(np.median(g)) - 20)).mean()))
    if len(inkm) < 2:
        print('  p%-5d %s   格数不足，跳过' % (c['page'], c['ch']))
        continue
    first = inkm[0]
    rest = float(np.median(inkm[1:]))
    ratio = first / rest if rest > 1e-6 else 9.9
    verdict = '源书首格确是标点' if ratio < 0.75 else '首格墨量像汉字 -> 可疑'
    rows.append(ratio)
    print('  p%-5d %s  %5.1f %8.3f %12.3f %8.2f  %s'
          % (c['page'], c['ch'], step, first, rest, ratio, verdict))

print()
ok = [r for r in rows if r < 0.75]
print('  首格墨量明显小于后续格（<0.75）: %d / %d = %.0f%%'
      % (len(ok), len(rows), 100.0 * len(ok) / max(1, len(rows))))
src.close()
