#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""目录页列序精确校验: 「第X回」序号必须随 x 递减而**严格递增**

修正: 前一版把原始 float x 与 round(x,1) 集合比较 -> 每列拼出空串 -> 全书 0 命中(假阴性)。

判据(目录页天然硬约束, 不依赖模糊相似度):
  ① 从产物每列文本抽「第X回」并转成整数
  ② 列按 x 降序(阅读序)排列, 序号必须严格递增
  ③ OCR 侧同法算出应有序列, 两侧对照

退出码 0=全单调 / 1=有逆序(可作门禁)
"""
import argparse
import re
import sys

CN = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
RE = re.compile(r'第([一二三四五六七八九十百]+)回')


def cn2int(s):
    if s == '十':
        return 10
    if '十' in s:
        hi, _b, lo = s.partition('十')
        return (CN.get(hi, 1) if hi else 1) * 10 + (CN.get(lo, 0) if lo else 0)
    return CN.get(s, 0)


def to_cols(doc, pi, tol=20.0):
    pg = doc[pi]
    ch = []
    for b in pg.get_text('rawdict')['blocks']:
        for ln in b.get('lines', []):
            for sp in ln.get('spans', []):
                for c in sp.get('chars', []):
                    if not c['c'].isspace():
                        ch.append((round(c['origin'][0], 1), c['c'], c['origin'][1]))
    if len(ch) < 20:
        return [], 0
    xs = sorted(set(x for x, _c, _y in ch))
    g = []
    for x in xs:
        if g and x - g[-1][-1] <= tol:
            g[-1].append(x)
        else:
            g.append([x])
    cols = []
    for gg in g:
        gs = set(gg)
        mem = [(c, y) for x, c, y in ch if x in gs]
        mem.sort(key=lambda z: z[1])
        cols.append((gg[0], u''.join(m[0] for m in mem)))
    cols.sort(key=lambda z: -z[0])
    return cols, len(ch)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('--pages', default='')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()

    import fitz
    doc = fitz.open(a.pdf)
    pages = ([int(x) for x in a.pages.split(',') if x.strip()]
             if a.pages else list(range(1, len(doc) + 1)))
    bad, checked = [], 0
    for p in pages:
        cols, n = to_cols(doc, p - 1)
        if not cols:
            continue
        seq = []
        for x, t in cols:
            m = RE.search(t)
            if m:
                seq.append((x, cn2int(m.group(1)), m.group(0), t[:28]))
        if len(seq) < 5:
            continue
        checked += 1
        nums = [s[1] for s in seq]
        inv = [(i, nums[i], nums[i + 1]) for i in range(len(nums) - 1)
               if nums[i + 1] < nums[i]]
        if inv:
            bad.append((p, len(seq), nums))
            if a.verbose:
                print('p%-5d %d 列, 逆序 %d 处' % (p, len(seq), len(inv)))
                for x, num, lab, t in seq:
                    print('    x%6.1f  #%-3d %-7s %s' % (x, num, lab, t))
    print()
    print('目录页: %d 页 (>=5 个「第X回」)' % checked)
    print('列序逆序: %d 页' % len(bad))
    for b in bad[:40]:
        print('   p%-5d %d列 序列: %s' % (b[0], b[1], b[2][:18]))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
