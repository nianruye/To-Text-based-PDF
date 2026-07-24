#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页码处理共享模块。PAGENUM_GLOBAL_TABLE 加载 + layout number 连续推断。

bit-exact 复制 build_geom/build_classic L34-36 + L378-400 逻辑（两管线一致）。
PAGENUM_GLOBAL_TABLE 默认路径行为不变（未设/不存在返回 {}）。
"""
import os
import json
import re

PN_RE = re.compile(r'[·•.]?\s*\d{1,4}\s*[·•.]?$')


def load_pntab():
    """从 PAGENUM_GLOBAL_TABLE env 加载页码表 {key: pagenum}。未设/不存在返回 {}。"""
    pn_file = os.environ.get('PAGENUM_GLOBAL_TABLE', '')
    return json.load(open(pn_file, encoding='utf-8')) if pn_file and os.path.exists(pn_file) else {}


def infer_lay_numbers(lay_path):
    """layout number block + 连续推断补全。返回 {page_key: pagenum_str}。

    从 LAYJSON 的 number block 提取页码，再前后向连续推断（±1）补全缺失页
    （spotting pn_ocr 误识目录页码如 p7'158'，layout number 更准）。
    lay_path 未设/不存在返回 {}。
    """
    if not lay_path or not os.path.exists(lay_path):
        return {}
    _ld = json.load(open(lay_path, encoding='utf-8'))
    lay_numbers = {}
    for _pi, _pg in enumerate(_ld):
        for _b in _pg.get('prunedResult', {}).get('parsing_res_list', []):
            if _b.get('block_label') == 'number':
                _c = _b.get('block_content', '').strip()
                if _c.isdigit(): lay_numbers[str(_pi)] = _c
    _all_nkeys = sorted([str(i) for i in range(len(_ld))], key=int)
    for _ in range(5):
        for i in range(len(_all_nkeys) - 1, -1, -1):
            k = _all_nkeys[i]
            if int(k) < 10 or k in lay_numbers: continue
            if i + 1 < len(_all_nkeys) and _all_nkeys[i + 1] in lay_numbers:
                _nxt = int(lay_numbers[_all_nkeys[i + 1]])
                if _nxt > 1: lay_numbers[k] = str(_nxt - 1)
        for i, k in enumerate(_all_nkeys):
            if int(k) < 10 or k in lay_numbers: continue
            if i > 0 and _all_nkeys[i - 1] in lay_numbers:
                lay_numbers[k] = str(int(lay_numbers[_all_nkeys[i - 1]]) + 1)
    if lay_numbers: print(f"[页码] layout number {len(lay_numbers)} 页(含连续推断补全)")
    return lay_numbers
