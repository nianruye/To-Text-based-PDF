#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漏列清单 v2 —— 改用**内容匹配**判定, 不再靠坐标容差

v1 的错: 用 x 中心 + 0.5 列距容差判「漏」, 但两引擎的框宽差异大
         (ps3 的「凡例」w=76 / 「第一回」w=43, 我们约 35-40), 导致
         p53 报 8 条里 6 条是误报(詞話第一冊目錄/詞話章回目錄/第一回 我们都有)。

v2 判据(内容为准, 坐标只用于定位):
  ① 取 ps3 每个框的文本, 去掉点线/标点/空白 得到「核心串」
  ② 该核心串若**出现在本页我们的 OCR 文本里**(子串) -> 不是漏
  ③ 不出现 -> 真·漏(可能是我们读丢的列/行)
  ④ 空文本框单独统计(它没有内容可比, 只能作为「检测到墨」的参考)

页号换算: ps3 是 1-based, lines/coords 是 0-based -> 页 p 用 lines[str(p-1)]
"""
import json
import re

BASE = '/opt/test/data/wz7_full/'
ps3 = json.load(open(BASE + 'wz7_full_ps3.json', encoding='utf-8'))
LI = json.load(open(BASE + 'wz7_full_spotting_lines_patched.json', encoding='utf-8'))
CO = json.load(open(BASE + 'wz7_full_spotting_coords.json', encoding='utf-8'))

DROP = set(u'…⋯.·。、，,．・-—~～_ \t\n\r\u3000:：;；!！?？「」『』()（）[]【】')


def core(s):
    return u''.join(c for c in str(s) if c not in DROP)


out = {}
stats = []
for k in sorted(ps3, key=int):
    p = int(k)
    bk = str(p - 1)
    if bk not in LI:
        continue
    ours = u''.join(core(t) for t in (LI.get(bk) or []))
    if not ours:
        continue
    v = ps3[k]
    miss = []
    for poly, t, s in zip(v.get('polys') or [], v.get('texts') or [], v.get('scores') or []):
        if not poly or len(poly) < 3:
            continue
        c = core(t)
        if len(c) < 3:                     # 太短无法判定(页码/单字), 跳过
            continue
        if c in ours or ours in c:
            continue                       # 我们有这段内容
        # 长串因识别差异可能不是精确子串 -> 退一步用 3-gram 覆盖率
        grams = [c[i:i + 3] for i in range(len(c) - 2)]
        hit = sum(1 for g in grams if g in ours)
        cov = hit / float(len(grams)) if grams else 0.0
        if cov >= 0.6:
            continue                       # 内容基本重合(只是识别差异)
        xs = [q[0] / 2.0 for q in poly]
        ys = [q[1] / 2.0 for q in poly]
        miss.append({'x0': round(min(xs), 1), 'x1': round(max(xs), 1),
                     'y0': round(min(ys), 1), 'y1': round(max(ys), 1),
                     'text': str(t)[:60].replace('\n', ''),
                     'core': c[:40], 'cov': round(cov, 2),
                     'score': round(float(s), 3), 'ps3_w': round(max(xs) - min(xs), 1)})
    if miss:
        miss.sort(key=lambda z: (-(z['x0'] + z['x1']), z['y0']))
        out[str(p)] = miss
        stats.append((p, len(miss)))

json.dump(out, open(BASE + 'wz7_full_missing_cols.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)

print('=== v2 内容匹配 · 漏列清单 ===')
print('  涉及页数 %d | 漏列合计 %d 条' % (len(out), sum(len(x) for x in out.values())))
print()
print('=== 已知页核对 ===')
for p in (43, 53, 54, 55, 563):
    if str(p) in out:
        print('p%-5d 漏 %d 条:' % (p, len(out[str(p)])))
        for m in out[str(p)][:8]:
            print('    x%6.1f-%6.1f y%6.1f-%6.1f cov%.2f 「%s」'
                  % (m['x0'], m['x1'], m['y0'], m['y1'], m['cov'], m['text'][:26]))
    else:
        print('p%-5d 无漏列 ✓' % p)
print()
print('=== 漏列最多的 15 页 ===')
for p, n in sorted(stats, key=lambda z: -z[1])[:15]:
    print('  p%-5d 漏 %2d 条' % (p, n))
print()
from collections import Counter
c = Counter(n for _p, n in stats)
print('=== 分布 ===')
for n in sorted(c)[:10]:
    print('  漏 %d 条: %d 页' % (n, c[n]))
tot_chars = sum(len(m['core']) for x in out.values() for m in x)
print()
print('  漏列涉及字符数合计 ≈ %d' % tot_chars)
