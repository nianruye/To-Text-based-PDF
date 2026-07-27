#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VL vs PP-OCRv6 wordbox 对比,生成单字贴图数据。

VL 有 v6 无(同行) + v6 频次<20 + sim>0.85 = 古字识错候选。
用 v6 的 word_boxes(字级 box)精确定位,单字贴图。

输出: {key: [[vl_char_idx, vl_char, v6_word_box, vl_line_poly], ...]}
vl_char_idx: VL 行文字中的字符偏移(用于 esc_t 替换)
vl_char: VL 识错的字
v6_word_box: 该字附近的 v6 字级 box [x1,y1,x2,y2](200dpi px)
vl_line_poly: VL 行 poly(用于 crop_char 行内定位)
"""
import json, os
from collections import Counter

def edit_sim(a, b):
    if not a or not b: return 0
    m, n = len(a), len(b)
    if abs(m-n) > max(m,n)*0.3: return 0
    dp = [[0]*(n+1) for _ in range(m+1)]
    for i in range(m+1): dp[i][0] = i
    for j in range(n+1): dp[0][j] = j
    for i in range(1, m+1):
        for j in range(1, n+1):
            dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+(0 if a[i-1]==b[j-1] else 1))
    return 1 - dp[m][n] / max(m, n)

PUNCT = set('，。；：、！？）】》」』""\'\'%.;:!)|(【[]{}()《》-…～·\-_#=+*<>/?\"\'…·')

vl_co = json.load(open('data/wz3/wz3_linelevel_spotting_coords.json'))
vl_sl = json.load(open('data/wz3/wz3_linelevel_spotting_lines.json'))
v6 = json.load(open('data/wz3/wz3_v6_wordbox.json'))

# v6 字频
v6_freq = Counter()
for v in v6.values():
    for _, _, text, words, _ in v:
        for w in words:
            for c in w:
                if len(c) == 1 and ord(c) > 0x2e80:
                    v6_freq[c] += 1

out = {}
for k in vl_sl:
    v6_lines = v6.get(k, [])
    if not v6_lines: continue
    page_diffs = []
    for vi, poly in enumerate(vl_co.get(k, [])):
        if not poly: continue
        vl_text = vl_sl[k][vi].strip()
        if not vl_text or len(vl_text) < 3: continue
        vl_y0 = min(p[1] for p in poly)
        best = None; best_dy = 999
        for v6_poly, v6_score, v6_text, v6_words, v6_wb in v6_lines:
            if not v6_poly: continue
            v6_y0 = min(p[1] for p in v6_poly)
            dy = abs(v6_y0 - vl_y0)
            if dy < best_dy and dy < 30:
                best_dy = dy
                best = (v6_poly, v6_score, v6_text, v6_words, v6_wb)
        if not best: continue
        v6_poly, v6_score, v6_text, v6_words, v6_wb = best
        sim = edit_sim(vl_text, v6_text)
        if sim < 0.85: continue
        v6_set = set(v6_text)
        # 去 CJK 字计数(vl_text 中的 CJK 字序号 -> 对应 v6 word_box)
        cjk_idx = 0
        for ci, vl_c in enumerate(vl_text):
            if len(vl_c) == 1 and ord(vl_c) > 0x2e80 and vl_c not in PUNCT:
                if vl_c not in v6_set and v6_freq.get(vl_c, 0) < 20:
                    # 找 v6 word_box(用 cjk_idx 近似对应 v6 的第 cjk_idx 个字 box)
                    wb = v6_wb[cjk_idx] if cjk_idx < len(v6_wb) else (v6_wb[-1] if v6_wb else None)
                    page_diffs.append([ci, vl_c, wb, [[p[0], p[1]] for p in poly[:4]]])
                cjk_idx += 1
    if page_diffs:
        out[k] = page_diffs

OUT_FILE = 'data/wz3/wz3_vl_v6_diff.json'
json.dump(out, open(OUT_FILE, 'w', encoding='utf-8'), ensure_ascii=False)
total = sum(len(v) for v in out.values())
print(f'完成: {len(out)} 页, {total} 字 -> {OUT_FILE}')
# p68 验证
p68 = out.get('67', [])
print(f'p68: {len(p68)} 字')
for ci, vl_c, wb, poly in p68:
    print(f'  pos{ci} {vl_c!r} box={wb}')
