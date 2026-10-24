#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""问题一收窄：只比「缺﹁组里首字符是 一 的 134 处」vs 对照组 666 处

已知 OCR 失效模式（AGENTS.md issue #33）：竖排 ﹁ 被读成汉字「一」。
若这 134 处的首格墨迹签名与对照组（确定是 ﹁）一致 -> 它们就是 ﹁ 被误读成 一。
"""
import json
import random

import numpy as np
import fitz

LINES = 'data/wz7_full/wz7_full_spotting_lines_patched.json'
COORDS = 'data/wz7_full/wz7_full_spotting_coords.json'
SRC = 'source_pdf/wz7.pdf'
COLON = '：:'
OPENQ = '﹁「﹃『'

sl = json.load(open(LINES, encoding='utf-8'))
co = json.load(open(COORDS, encoding='utf-8'))

HAVE, YI, OTHER = [], [], []
for k in sl:
    rows = sl[k] or []
    boxes = co.get(k) or []
    cols = []
    for i, t in enumerate(rows):
        t = str(t).replace('\n', '')
        if not t or i >= len(boxes):
            continue
        xs = [q[0] / 2.0 for q in boxes[i]]
        ys = [q[1] / 2.0 for q in boxes[i]]
        cols.append(dict(t=t, x0=min(xs), x1=max(xs), y0=min(ys), y1=max(ys)))
    if len(cols) < 2:
        continue
    for ci, c in enumerate(cols):
        if c['t'][-1] not in COLON:
            continue
        best, bd = None, 1e18
        for cj, n in enumerate(cols):
            if cj == ci or n['x1'] > c['x0'] + 2:
                continue
            ovy = min(c['y1'], n['y1']) - max(c['y0'], n['y0'])
            if ovy <= 0:
                continue
            d = c['x0'] - n['x1']
            if d < bd:
                best, bd = n, d
        if best is None:
            continue
        rec = dict(page=int(k) + 1, n0=best['t'][0], ntext=best['t'][:14],
                   nx0=best['x0'], nx1=best['x1'], ny0=best['y0'], ny1=best['y1'],
                   nn=len(best['t']), ctext=c['t'][-12:])
        if best['t'][0] in OPENQ:
            HAVE.append(rec)
        elif best['t'][0] == '一':
            YI.append(rec)
        else:
            OTHER.append(rec)

print('对照组(首=﹁) %d   实验组(首=一) %d   其它 %d' % (len(HAVE), len(YI), len(OTHER)))

src = fitz.open(SRC)
random.seed(20261024)

def sig(r):
    step = (r['ny1'] - r['ny0']) / max(1, r['nn'])
    pg = src[r['page'] - 1]
    clip = fitz.Rect(max(0, r['nx0'] - 1), r['ny0'],
                     min(pg.rect.width, r['nx1'] + 1), r['ny0'] + step)
    if clip.height < 2 or clip.width < 2:
        return None
    pm = pg.get_pixmap(clip=clip, dpi=600)
    a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)
    g = a[:, :, :3].mean(axis=2)
    m = g < (float(np.median(g)) - 20)
    if m.size == 0:
        return None
    h, w = m.shape
    def q(a0, a1, b0, b1):
        blk = m[int(a0 * h):max(int(a1 * h), int(a0 * h) + 1),
                int(b0 * w):max(int(b1 * w), int(b0 * w) + 1)]
        return float(blk.mean()) if blk.size else 0.0
    c1, c2 = q(0, .5, 0, .5), q(0, .5, .5, 1)
    c3, c4 = q(.5, 1, 0, .5), q(.5, 1, .5, 1)
    ys, xs = np.where(m)
    hh = (ys.max() - ys.min() + 1) / float(h) if len(ys) else 0
    ww = (xs.max() - xs.min() + 1) / float(w) if len(xs) else 0
    return dict(ink=float(m.mean()), bias=(c1 + c2) - (c3 + c4), hh=hh, ww=ww,
                ar=(ww / hh) if hh > 1e-6 else 9.9)

def show(name, pool, n=45):
    samp = random.sample(pool, min(n, len(pool)))
    ss = [s for s in (sig(r) for r in samp) if s]
    if not ss:
        print('  %s 无有效样本' % name); return
    ink = [s['ink'] for s in ss]; bias = [s['bias'] for s in ss]
    ar = [s['ar'] for s in ss]
    print('  %-14s n=%-3d 墨量中位 %.3f | bias 中位 %+.2f | 墨块宽高比 中位 %.2f (范围 %.2f-%.2f)'
          % (name, len(ss), float(np.median(ink)), float(np.median(bias)),
             float(np.median(ar)), min(ar), max(ar)))
    return ss

print()
print('=== 首格源图墨迹签名 ===')
a = show('对照组(真﹁)', HAVE)
b = show('实验组(首=一)', YI)
c = show('其它首字符', OTHER)

print()
print('=== 判读 ===')
if a and b:
    ia = float(np.median([s['ink'] for s in a]))
    ib = float(np.median([s['ink'] for s in b]))
    aa = float(np.median([s['ar'] for s in a]))
    ab = float(np.median([s['ar'] for s in b]))
    print('  墨量  对照组 %.3f vs 实验组 %.3f  差 %.0f%%' % (ia, ib, 100 * abs(ib - ia) / max(ia, 1e-9)))
    print('  宽高比 对照组 %.2f vs 实验组 %.2f' % (aa, ab))
    if abs(ib - ia) / max(ia, 1e-9) < 0.35 and abs(ab - aa) < 0.5:
        print('  -> 两组签名接近：这 134 处很可能是 ﹁ 被 OCR 读成「一」')
    else:
        print('  -> 两组签名不同：这 134 处首格墨像真「一」横画，不是引号')
src.close()
