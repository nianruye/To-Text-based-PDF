#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify 补第 6 条判据: 列序单调性 (v3, 用 coords 把 OCR 行并成列)

verify_vert 现有 5 条判据(页数/字符量/越界/整页丢失/页幅)只验「字在不在」,
**拦不住列位置错乱** —— p54 三列互换位置时 379/381 字、越界 0, 全部 PASS。

v1/v2 的错: 拿产物整列比 OCR **未合并的单行**(4-7 字) -> 相似度全 < 0.5 被过滤 -> p54 漏报。
v3: 用 spotting_coords 的 x 把 OCR 行按 x 分带、带内 y 升序**合并成列**, 两侧同口径。

退出码: 0 = 无交叉; 1 = 有交叉(可作为门禁)
"""
import argparse
import json
import sys
from collections import Counter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('lines')
    ap.add_argument('coords')
    ap.add_argument('--pages', default='')
    ap.add_argument('--min-sim', type=float, default=0.45)
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--tol', type=float, default=20.0)
    a = ap.parse_args()

    import fitz
    LI = json.load(open(a.lines, encoding='utf-8'))
    CO = json.load(open(a.coords, encoding='utf-8'))
    doc = fitz.open(a.pdf)
    pages = ([int(x) for x in a.pages.split(',') if x.strip()]
             if a.pages else list(range(1, len(doc) + 1)))

    bad = []
    for p in pages:
        rows = LI.get(str(p - 1)) or []
        cos = CO.get(str(p - 1)) or []
        if not rows or not cos:
            continue
        # ---- OCR 侧: 用 poly 的 x0(pt) 分带, 带内 y 升序拼 ----
        orows = []
        for t, poly in zip(rows, cos):
            s = u''.join(c for c in str(t) if not c.isspace())
            if not s:
                continue
            try:
                x0 = min(q[0] for q in poly) / 2.0
                y0 = min(q[1] for q in poly) / 2.0
            except Exception:
                continue
            orows.append((x0, y0, s))
        if len(orows) < 2:
            continue
        oxs = sorted(set(round(r[0], 1) for r in orows))
        og = []
        for x in oxs:
            if og and x - og[-1][-1] <= a.tol:
                og[-1].append(x)
            else:
                og.append([x])
        ocol = []
        for gg in og:
            gs = set(gg)
            mem = [r for r in orows if round(r[0], 1) in gs]
            mem.sort(key=lambda z: z[1])
            ocol.append((gg[0], u''.join(m[2] for m in mem)))
        ocol.sort(key=lambda z: -z[0])

        # ---- 产物侧 ----
        pg = doc[p - 1]
        pch = []
        for b in pg.get_text('rawdict')['blocks']:
            for ln in b.get('lines', []):
                for sp in ln.get('spans', []):
                    for c in sp.get('chars', []):
                        if not c['c'].isspace():
                            pch.append((c['origin'][0], c['c'], c['origin'][1]))
        if len(pch) < 20:
            continue
        pxs = sorted(set(round(x, 1) for x, _c, _y in pch))
        hg = []
        for x in pxs:
            if hg and x - hg[-1][-1] <= a.tol:
                hg[-1].append(x)
            else:
                hg.append([x])
        pcol = []
        for gg in hg:
            gs = set(gg)
            mem = [(c, y) for x, c, y in pch if x in gs]
            mem.sort(key=lambda z: z[1])
            pcol.append((gg[0], u''.join(m[0] for m in mem)))
        pcol.sort(key=lambda z: -z[0])
        if len(pcol) < 3 or len(ocol) < 2:
            continue

        # ---- 每列找最佳 OCR 列, 检查下标单调 ----
        idxs = []
        for _x, ptxt in pcol:
            cp = Counter(ptxt)
            best, bi = 0.0, -1
            for i, (_ox, otxt) in enumerate(ocol):
                co = Counter(otxt)
                inter = sum((cp & co).values())
                sim = inter / float(max(1, max(sum(cp.values()), sum(co.values()))))
                if sim > best:
                    best, bi = sim, i
            idxs.append((bi, best))
        seq = [i for i, s in idxs if i >= 0 and s >= a.min_sim]
        if len(seq) < 3:
            continue
        nx = sum(1 for u, v in zip(seq, seq[1:]) if v < u)
        if nx:
            bad.append((p, nx, len(pcol), len(ocol)))
            if a.verbose:
                print('p%-5d 交叉 %d 处 (产物 %d 列 / OCR %d 列)'
                      % (p, nx, len(pcol), len(ocol)))
                for k, (x, t) in enumerate(pcol):
                    bi, sim = idxs[k]
                    print('    x%6.1f sim%.2f -> OCR#%-3s %s' % (x, sim, bi, t[:26]))
    print()
    print('列序交叉页: %d 页' % len(bad))
    for b in bad[:30]:
        print('   p%-5d 交叉%d处 产物%d列/OCR%d列' % b)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
