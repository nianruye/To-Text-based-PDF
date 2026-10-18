#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C 类修复：删除 OCR 幻觉标点串

现象（用户实测 p86）:
    OCR 行 = '「，；，。」那漢王劉邦原是泗上亭長，提三尺劍…'
    源书那里只有正文，前面并没有 6 个标点。
    全书实测 `；，` 型判据命中 100 列 / 99 页, 典型形态:
        p86  「，；，。」那漢王劉邦原是泗上亭長…
        p88  「，；，。原來雲生從龍，風生從虎…
        p89  。「，；，；…

判据（只用结构，不猜内容）:
    取「标点+引号」的最大连续段; 段内**非引号标点**个数 >= 2 才判为幻觉串。
      · `。」`            (1 个非引号标点) -> 正常收尾，不动
      · `，」「`          (1 个)             -> 不动
      · `「，；，。」`     (4 个)             -> 幻觉串，删
    删的时候保留串首那个**前面紧跟汉字的**单个标点（它是真标点）:
      · `但見：。「，；，；`  -> `但見：`   （`：` 是引出诗句的真冒号）
      · `觀，「，。」：`      -> `觀，`
      · `「，；，。」那漢王…` -> `那漢王…` （串在列首，前面没汉字，整段删）

安全:
    - 只改文本，不动 coords（几何仍按源图）
    - 默认 dry-run，加 --apply 才写盘
    - 逐条打印改动前后的上下文，便于人工核对
"""
import argparse
import json
import re
import sys

PUNCT = '，。、；：？！'
QUOTES = '「」『』﹁﹂'
ALL = PUNCT + QUOTES
RUN = re.compile('[%s]+' % re.escape(ALL))
CJK = re.compile(r'[\u3400-\u9fff]')

MIN_NONQUOTE = 2       # 段内非引号标点 >= 该值 -> 判幻觉


def fix_text(t):
    """-> (新文本, [(原串, 新串)])"""
    changes = []
    out = []
    pos = 0
    for m in RUN.finditer(t):
        seg = m.group()
        nonq = sum(1 for ch in seg if ch in PUNCT)
        if nonq < MIN_NONQUOTE:
            continue
        start, end = m.span()
        before = t[:start]
        keep = ''
        # 串首若是单个非引号标点且紧跟在汉字后 -> 保留它（真标点）
        if seg[0] in PUNCT:
            prev = before[-1] if before else ''
            if CJK.match(prev or ''):
                keep = seg[0]
        out.append(t[pos:start])
        out.append(keep)
        pos = end
        changes.append((seg, keep))
    out.append(t[pos:])
    return ''.join(out), changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--show', type=int, default=18)
    a = ap.parse_args()

    data = json.load(open(a.src, encoding='utf-8'))
    total_cols = 0
    ncol = 0
    npage = set()
    log = []
    dropped = 0
    for k, rows in data.items():
        if not isinstance(rows, list):
            continue
        for i, t in enumerate(rows):
            t = str(t)
            if not t.strip():
                continue
            total_cols += 1
            new, ch = fix_text(t)
            if not ch:
                continue
            ncol += 1
            npage.add(int(k) + 1)
            dropped += len(t) - len(new)
            data[k][i] = new
            log.append((int(k) + 1, i, t, new, ch))

    print('=== C 类修复（OCR 幻觉标点串）===')
    print('扫描列数: %d' % total_cols)
    print('命中列数: %d (%.2f%%)  涉及页: %d' % (
        ncol, ncol / max(1, total_cols) * 100, len(npage)))
    print('删除字符数: %d' % dropped)
    print()
    print('=== 改动样例（前 %d 条）===' % a.show)
    for p, i, old, new, ch in log[:a.show]:
        print('  p%-6d row%-3d  %s' % (p, i, '  '.join('%r->%r' % c for c in ch)))
        print('        原: %s' % old[:64])
        print('        新: %s' % new[:64])
    print()
    if a.apply:
        json.dump(data, open(a.dst, 'w', encoding='utf-8'), ensure_ascii=False)
        print('已写入: %s' % a.dst)
    else:
        print('（dry-run，未写盘；加 --apply 才写入 %s）' % a.dst)


if __name__ == '__main__':
    main()
