#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""删掉「闭引号后紧跟单个 —」（第二轮）

用户逐处核对源图确认：21 处源书都没有破折号，只是 ﹂ 的方角被 OCR 读成 —。
与第一轮已删的 1019 处「』——」（双破折号）同机制，只是那次读了两个。

第一轮：fix_vert_dash_misread.py —— 删「闭引号 + ——」1019 处
本轮：  删「闭引号 + 单个 —」21 处

只动紧跟闭引号的那个，其它位置的 — 一律不碰。
"""
import io
import json
import os
import shutil

P = '/opt/test/data/wz7_full/wz7_full_spotting_lines_patched.json'
BAK = P + '.bak_pre_dashfix1'
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('备份 ->', BAK)

CLOSE = ('\u300d', '\u300f', '\ufe42', '\ufe43')   # 」』﹂﹄
D = '\u2014'

d = json.load(io.open(P, encoding='utf-8'))
n = 0
pages = {}
for k in sorted(d.keys(), key=lambda z: int(z)):
    rows = d[k] or []
    out = []
    for t in rows:
        s = str(t).replace('\n', '')
        orig = s
        for c in CLOSE:
            while c + D in s and c + D + D not in s:      # 只删单个，双的已被第一轮删掉
                s = s.replace(c + D, c, 1)
                n += 1
        if s != orig:
            pages[int(k) + 1] = pages.get(int(k) + 1, 0) + 1
        out.append(s)
    d[k] = out

print()
print('删除「闭引号 + 单个 —」: %d 处' % n)
print('涉及页数: %d' % len(pages))
print('涉及页: %s' % sorted(pages))
print('减少字符: %d' % n)

json.dump(d, io.open(P, 'w', encoding='utf-8'), ensure_ascii=False)
print()
print('已写回', P)

left = 0
for k in d:
    for t in (d[k] or []):
        s = str(t)
        for c in CLOSE:
            left += s.count(c + D)
print('复核 剩余「闭引号 + —」: %d（应为 0）' % left)
# 剩余 — 总数
tot = sum(str(t).count(D) for k in d for t in (d[k] or []))
print('数据层剩余 — 总数: %d' % tot)
