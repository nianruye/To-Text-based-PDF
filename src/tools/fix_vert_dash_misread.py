#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""删掉 OCR 误读的「闭引号后紧跟 ——」

用户核对源图确认: 那些位置源书没有破折号，`——` 是 OCR 把引号 ﹂ 的直角笔画
（竖臂 + 横臂）各读成了一个 —。

范围: 只删「紧跟闭引号」的，其它位置的 ——（212 处）不动，留待单独核查。
形态:
  …﹂——X      ->  …﹂X
  …」——X      ->  …」X
  …』——X      ->  …』X
  行首 ——（上一行以引号结尾）-> 删行首 ——
"""
import io
import json
import os
import shutil

P = '/opt/test/data/wz7_full/wz7_full_spotting_lines_patched.json'
BAK = P + '.bak_pre_dashfix'

if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('已备份 ->', BAK)

CLOSE = ('\u300d', '\u300f', '\ufe42', '\ufe43')   # 」』﹂﹄
DASH = '\u2014\u2014'

d = json.load(io.open(P, encoding='utf-8'))
n_inline = 0
n_head = 0
pages = {}

keys = sorted(d.keys(), key=lambda z: int(z))
for k in keys:
    rows = d[k] or []
    out = []
    prev_ended_close = False
    for t in rows:
        s = str(t).replace('\n', '')
        orig = s
        # ① 行内: 闭引号后紧跟 ——
        for c in CLOSE:
            if c + DASH in s:
                n_inline += s.count(c + DASH)
                s = s.replace(c + DASH, c)
        # ② 行首 ——，且上一行以闭引号结尾
        if prev_ended_close and s.startswith(DASH):
            n_head += 1
            s = s[len(DASH):]
        prev_ended_close = bool(s) and s[-1] in CLOSE
        if s != orig:
            pages[int(k) + 1] = pages.get(int(k) + 1, 0) + 1
        out.append(s)
    d[k] = out

print()
print('行内「引号后 ——」删除: %d 处' % n_inline)
print('行首「——」删除:        %d 处' % n_head)
print('涉及页数: %d' % len(pages))
print('合计删除字符: %d' % (2 * (n_inline + n_head)))

json.dump(d, io.open(P, 'w', encoding='utf-8'), ensure_ascii=False)
print()
print('已写回', P)

# 复核: 再扫一遍还有多少「引号后 ——」
left = 0
for k in d:
    for t in (d[k] or []):
        s = str(t)
        for c in CLOSE:
            left += s.count(c + DASH)
print('复核 剩余「引号后 ——」: %d（应为 0）' % left)
