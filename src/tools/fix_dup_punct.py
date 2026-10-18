#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C2 类：跨列重复标点（前一行以标点结尾、本行以同一标点开头）量化 + 修复"""
import argparse
import json

PUNCT = '，。、；：？！'
QUOTES = '「」『』﹁﹂'
BOUND = PUNCT + QUOTES


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--show', type=int, default=20)
    a = ap.parse_args()

    data = json.load(open(a.src, encoding='utf-8'))
    hits = []
    for k, rows in data.items():
        if not isinstance(rows, list) or len(rows) < 2:
            continue
        for i in range(1, len(rows)):
            prev = str(rows[i - 1])
            cur = str(rows[i])
            if not prev.strip() or not cur.strip():
                continue
            if prev[-1] in PUNCT and cur[0] == prev[-1]:
                hits.append((int(k) + 1, i, prev[-1], prev[-14:], cur[:14]))

    print('=== C2 类：跨列重复标点 ===')
    print('命中处数: %d  涉及页: %d' % (len(hits), len({h[0] for h in hits})))
    from collections import Counter
    c = Counter(h[2] for h in hits)
    print('按标点分布: %s' % dict(c.most_common()))
    print()
    print('=== 样例（前 %d）===' % a.show)
    for p, i, ch, pv, cu in hits[:a.show]:
        print('  p%-6d row%-3d  %r 重复  前行尾: …%s | 本行首: %s…' % (
            p, i, ch, pv, cu))
    print()
    if a.apply and hits:
        n = 0
        for k, rows in data.items():
            if not isinstance(rows, list) or len(rows) < 2:
                continue
            for i in range(1, len(rows)):
                prev = str(rows[i - 1])
                cur = str(rows[i])
                if prev.strip() and cur.strip() and prev[-1] in PUNCT and cur[0] == prev[-1]:
                    data[k][i] = cur[1:]
                    n += 1
        json.dump(data, open(a.dst, 'w', encoding='utf-8'), ensure_ascii=False)
        print('已删除 %d 处重复标点，写入 %s' % (n, a.dst))
    else:
        print('（dry-run）')


if __name__ == '__main__':
    main()
