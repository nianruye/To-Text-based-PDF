#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""corrected_text.py — 每书文本校正表（CORRECTED_TEXT.md v1）。

数据：`{"<page_key 0-based>": {"<line_index 0-based>": "整行校正文本"}, "_comment": ...}`
应用：只替换已有行文本；未知页/行/非法 value → warn 跳过；行数不变。
"""
import hashlib
import json
import os


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def apply_corrected_text(lines, path, source='book_data'):
    """返回 (patched_lines, stats)。

    path 不存在/None → enabled=False（不报错；显式缺失由调用方决定 exit 2）。
    坏 JSON / 根非 object / 行数变化 → 抛 ValueError（调用方 exit 2）。
    未知 page/line / value 非非空 string → warn 跳过。
    """
    stats = dict(enabled=False, path=path, source=('disabled' if not path else source),
                 sha256=None, pages=[], pages_count=0, replaced=0, applied=0,
                 skipped=0, warnings=[], warn=[], line_counts={})
    if not path or not os.path.exists(path):
        return lines, stats
    try:
        doc = json.load(open(path, encoding='utf-8'))
    except Exception as e:
        raise ValueError('corrected_text JSON 解析失败: %s' % e)
    if not isinstance(doc, dict):
        raise ValueError('corrected_text 根必须是 object')
    patched = {str(k): list(v) for k, v in lines.items()}
    before = {k: len(v) for k, v in patched.items()}
    touched = set()

    def warn(code, page, line, message):
        stats['warnings'].append(dict(code=code, page=str(page),
                                      line=(line if line is not None else None),
                                      message=message))
        stats['skipped'] += 1

    for pk, entries in doc.items():
        if str(pk).startswith('_'):
            continue
        if not str(pk).isdigit():
            warn('invalid_page', pk, None, '非十进制页 key')
            continue
        key = str(int(pk))
        if key not in patched:
            warn('unknown_page', pk, None, '页 key 不在 OCR lines 中')
            continue
        if not isinstance(entries, dict):
            warn('invalid_page', pk, None, '页 value 不是 object')
            continue
        for li, val in entries.items():
            if str(li).startswith('_'):
                continue
            try:
                idx = int(li)
            except Exception:
                warn('invalid_line', pk, li, 'line key 非十进制')
                continue
            if idx < 0 or idx >= len(patched[key]):
                warn('unknown_line', pk, idx, '行索引超出该页行数')
                continue
            if not isinstance(val, str) or not val.strip():
                warn('invalid_value', pk, idx, 'value 非非空字符串')
                continue
            if '\n' in val or '\r' in val:
                warn('newline_in_value', pk, idx, '校正值不得含换行')
                continue
            patched[key][idx] = val
            stats['applied'] += 1
            touched.add(key)
    for k in before:
        if len(patched[k]) != before[k]:
            raise ValueError('corrected_text 改变了页 %s 行数' % k)
    stats['warn'] = list(stats['warnings'])
    stats['replaced'] = stats['applied']
    stats['pages'] = sorted(touched, key=lambda x: int(x))
    stats['pages_count'] = len(stats['pages'])
    stats['line_counts'] = {k: {'before': before[k], 'after': len(patched[k])}
                            for k in stats['pages']}
    stats.update(enabled=True, sha256=_sha256(path))
    return patched, stats
