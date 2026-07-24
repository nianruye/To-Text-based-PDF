#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多行 poly 拆分为单行 poly 的预处理模块。

PaddleOCR-VL spotting 有时将多行文字合并为一个 poly（段落级而非行级），
导致校准的 cw=chars/行 被高估、FONT 偏小（如 wz3: cw=122, FONT=3.6pt）。
本模块将高 poly（h > 预估单行高的 1.5 倍）按几何自洽公式拆分为单行 poly，
文本按字符数近似均分（优先在标点处断开），子 poly 在原始 y 范围内均匀堆叠。

公式: n = round(sqrt(h * chars * K / w))
  推导自 n=chars/cw 且 n=h/pitch 且 pitch=FONT*1.2 且 cw=w/(FONT*2.778)
  K 默认 0.7（CJK 字体方度~1.0 + baselineskip~1.2 的合参）。
"""

import json
import re


_PUNKS = set('，。；：、！？）】》」』""''%.;:!)')
_TAG = re.compile(r'<[^>]+>')


def split_text(text, n):
    """将文本近似均分为 n 份，优先在 CJK 标点处断开。

    Args:
        text: 待拆分文本
        n: 目标份数

    Returns:
        list of str, 长度 n（最后一份可能为空则合并到前一份）。
    """
    text = text.strip()
    if n <= 1 or not text:
        return [text]
    total = len(text)
    chunks = []
    start = 0
    for i in range(n - 1):
        remaining = n - len(chunks)  # 剩余份数
        if remaining <= 1:
            break
        # 自适应 target：剩余文本均分
        base = (total - start) / remaining
        target = int(start + base)
        best = target
        # 在 target 前后寻找最近的标点（搜索范围：base/2 字内）
        search_range = max(1, int(base / 2))
        for d in range(search_range + 1):
            for pos in (target + d, target - d):
                if start < pos < total and text[pos - 1] in _PUNKS:
                    best = pos
                    break
            else:
                continue
            break
        # 避免空块：best 不能等于 start
        if best <= start:
            best = min(start + 1, total)
        chunks.append(text[start:best])
        start = best
    # 最后一块
    if start < total:
        chunks.append(text[start:])
    return chunks


def clean_html(text):
    """移除 HTML 标签（OCR 输出的表格页可能含 <table><tr><td> 标记）。"""
    if '<' in text and '>' in text:
        return _TAG.sub(' ', text)
    return text


def split_multiline(sl_dict, co_dict, labels_dict=None, K=0.7):
    """将多行合并的 poly 拆分为单行 poly。

    对每个 poly，计算目标行数 n = round(sqrt(h * chars * K / w))。
    n > 1 时按字符数拆分文本，在原始 y 范围内均匀堆叠子 poly。

    Args:
        sl_dict: spotting lines dict (key -> list of str)，每个元素为一行文本
        co_dict: spotting coords dict (key -> list of list of [x,y])，每个元素为 4 点 poly
        labels_dict: 可选，spotting labels dict (key -> list of str)，与 sl 一一对应
        K: 几何合参，默认 0.7。值越大 n 越多（行越短）；0 等价于不拆分

    Returns:
        (new_sl, new_co, new_labels) 或 (new_sl, new_co) 若未提供 labels_dict。
        key 不变，每个 key 内的行数增加。
    """
    if labels_dict is None:
        labels_dict = {}

    new_sl, new_co, new_labels = {}, {}, {}
    split_count = 0

    for key in sl_dict:
        lines = sl_dict[key]
        polys = co_dict.get(key, [])
        labels = labels_dict.get(key, [])
        nl, np_, nlb = [], [], []

        for i, text in enumerate(lines):
            poly = polys[i] if i < len(polys) else None
            lab = labels[i] if i < len(labels) else 'text'

            # 不需要拆分的情况
            if not poly or len(poly) < 2:
                nl.append(text); np_.append(poly); nlb.append(lab)
                continue

            ys = [p[1] for p in poly]
            xs = [p[0] for p in poly]
            h = max(ys) - min(ys)
            w = max(xs) - min(xs)

            if w < 5 or len(text.strip()) < 2:
                nl.append(text); np_.append(poly); nlb.append(lab)
                continue

            # 清理 HTML 标签
            text = clean_html(text)
            n = max(1, round((h * len(text.strip()) * K / w) ** 0.5))

            if n <= 1:
                nl.append(text); np_.append(poly); nlb.append(lab)
                continue

            # 拆分文本 + 堆叠子 poly
            chunks = split_text(text, n)
            y0, y1 = min(ys), max(ys)
            x0, x1 = min(xs), max(xs)
            step = (y1 - y0) / len(chunks)

            for j, chunk in enumerate(chunks):
                cy0 = y0 + j * step
                cy1 = y0 + (j + 1) * step
                # 4 角 poly: 左上、右上、右下、左下
                nl.append(chunk)
                np_.append([[x0, cy0], [x1, cy0], [x1, cy1], [x0, cy1]])
                nlb.append(lab)

            split_count += 1

        new_sl[key] = nl
        new_co[key] = np_
        new_labels[key] = nlb

    total_before = sum(len(v) for v in sl_dict.values())
    total_after = sum(len(v) for v in new_sl.values())
    print(f'[split_polys] K={K} 拆分{split_count}个多行poly, {total_before}行→{total_after}行')

    if labels_dict:
        return new_sl, new_co, new_labels
    return new_sl, new_co
