#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修：冒号列左邻列首的 `一` -> `「`（竖排渲染层映射成 ﹁）

判据（这是「换字」不是「插字」：字符量/格数/版式全不变）：
  ① 该列以冒号结尾（：/ :）
  ② 左邻列（x 更小、y 有重叠、最近的）**首字符是 `一`**
  ③ 源图左邻列首格墨迹：墨量 < VERT_CQ_MAX_INK(0.18) 且 不是细横画（宽高比 < 3）
     —— 真「一」是单横画（宽高比 ~8-11），`﹁` 是直角（宽高比 ~0.9）
  ④ 数据层写 `「`(U+300C)，与既有 666 处对照组同码位（渲染层再映射 ﹁）

墨迹参数（实测标定，见 docs/vert_two_verify.md）：
  对照组(真﹁) 墨量 0.097 宽高比 1.11 | 实验组(首=一) 0.116 / 0.87 | 其它真字 0.238 / 0.81
  闸门 0.18 落在 0.116 与 0.238 之间。
"""
import json
import os
import shutil

import numpy as np
import fitz

LINES = 'data/wz7_full/wz7_full_spotting_lines_patched.json'
COORDS = 'data/wz7_full/wz7_full_spotting_coords.json'
SRC = 'source_pdf/wz7.pdf'
OUTLIST = 'docs/vert_taskG_colon_quote_fix.json'

COLON = '：:'
TARGET = '一'
REPL = '\u300c'          # 「
MAX_INK = float(os.environ.get('VERT_CQ_MAX_INK') or 0.18)
MAX_AR = float(os.environ.get('VERT_CQ_MAX_AR') or 3.0)
DRY = os.environ.get('VERT_CQ_DRY') == '1'

sl = json.load(open(LINES, encoding='utf-8'))
co = json.load(open(COORDS, encoding='utf-8'))
src = fitz.open(SRC)


def first_cell_sig(r):
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
    if m.sum() < 8:
        return dict(ink=0.0, ar=9.9)
    ys, xs = np.where(m)
    hh = (ys.max() - ys.min() + 1) / float(m.shape[0])
    ww = (xs.max() - xs.min() + 1) / float(m.shape[1])
    return dict(ink=float(m.mean()), ar=(ww / hh) if hh > 1e-6 else 9.9)


changes, skipped = [], []
for k in sorted(sl, key=int):
    rows = sl[k] or []
    boxes = co.get(k) or []
    cols = []
    for i, t in enumerate(rows):
        t = str(t).replace('\n', '')
        if not t or i >= len(boxes):
            continue
        xs = [q[0] / 2.0 for q in boxes[i]]
        ys = [q[1] / 2.0 for q in boxes[i]]
        cols.append(dict(i=i, t=t, x0=min(xs), x1=max(xs), y0=min(ys), y1=max(ys)))
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
        if best is None or best['t'][0] != TARGET:
            continue
        rec = dict(page=int(k) + 1, row=best['i'], old=best['t'][:14],
                   colon_col=c['t'][-12:], nx0=best['x0'], nx1=best['x1'],
                   ny0=best['y0'], ny1=best['y1'], nn=len(best['t']))
        s = first_cell_sig(rec)
        if s is None:
            skipped.append(dict(rec, why='无法取首格')); continue
        rec.update(ink=round(s['ink'], 3), ar=round(s['ar'], 2))
        if s['ink'] >= MAX_INK:
            rec['why'] = '墨量 %.3f >= %.2f（像真字）' % (s['ink'], MAX_INK)
            skipped.append(rec); continue
        if s['ar'] >= MAX_AR:
            rec['why'] = '宽高比 %.2f >= %.1f（像真「一」横画）' % (s['ar'], MAX_AR)
            skipped.append(rec); continue
        changes.append(rec)

print('候选（冒号列左邻列首=一）%d 处' % (len(changes) + len(skipped)))
print('  通过墨迹闸门 %d 处' % len(changes))
print('  被闸门拦下 %d 处:' % len(skipped))
for s in skipped:
    print('     p%-5d 行%-3d 墨量%-6s 宽高比%-6s %s  文本 %r'
          % (s['page'], s['row'], s.get('ink'), s.get('ar'), s.get('why', ''), s['old'][:10]))

if DRY:
    print()
    print('[DRY RUN] 未写文件')
    src.close()
    raise SystemExit(0)

if changes:
    bak = LINES + '.bak_pre_colonquote'
    if not os.path.exists(bak):
        shutil.copy2(LINES, bak)
        print('备份 -> %s' % os.path.basename(bak))
    for c in changes:
        k = str(c['page'] - 1)
        t = sl[k][c['row']]
        assert t[0] == TARGET, (c['page'], c['row'], t[:4])
        sl[k][c['row']] = REPL + t[1:]
    json.dump(sl, open(LINES, 'w', encoding='utf-8'), ensure_ascii=False)
    print('已写入 %s' % LINES)

json.dump(dict(total=len(changes), changes=changes, skipped=skipped),
          open(OUTLIST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('清单 -> %s' % OUTLIST)
src.close()
