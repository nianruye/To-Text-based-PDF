#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""删掉剩余的「——」（第三轮，用户逐处看源图确认全都没有破折号）

三轮汇总:
  第一轮  闭引号 + ——        1019 处  (fix_vert_dash_misread.py)
  第二轮  闭引号 + 单个 —       24 处  (fix_vert_dash_single.py)
  第三轮  剩余全部 ——          88 处  (本脚本)

剩 63 个单个 — 不动 —— 它们不在本轮核对范围内（p31 銓釋—苦孝說 /
p60 四十五—一六一七 这类，可能是源书的间隔号/占位），另出一张图核对。
"""
import io
import json
import os
import shutil

P = '/opt/test/data/wz7_full/wz7_full_spotting_lines_patched.json'
BAK = P + '.bak_pre_dashfix2'
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('备份 ->', BAK)

DD = '\u2014\u2014'
d = json.load(io.open(P, encoding='utf-8'))
n = 0
pages = {}
for k in sorted(d.keys(), key=lambda z: int(z)):
    out = []
    for t in (d[k] or []):
        s = str(t).replace('\n', '')
        c = s.count(DD)
        if c:
            n += c
            pages[int(k) + 1] = pages.get(int(k) + 1, 0) + c
            s = s.replace(DD, '')
        out.append(s)
    d[k] = out

print()
print('删除「——」: %d 对' % n)
print('涉及页数: %d' % len(pages))
print('减少字符: %d' % (2 * n))

json.dump(d, io.open(P, 'w', encoding='utf-8'), ensure_ascii=False)
print('已写回', P)

tot = sum(str(t).count('\u2014') for k in d for t in (d[k] or []))
print()
print('复核 剩余 —— 对: %d（应为 0）' % sum(str(t).count(DD) for k in d for t in (d[k] or [])))
print('剩余单个 —  : %d 个' % tot)
