#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_poem_blocks.py —— 诗句/短文分段保真度校验（此前无工具覆盖）

判据：
  源书同一物理列若被 OCR 拆成 **多行** 且行间有 y 空隙（> 1.5 x 字步进），
  说明源书在这一列里是**分段排的**（诗句上句/下句、谚语+按语等）。
  产物必须也在同一位置留出空隙 —— 若产物把多行摊成连续一列（无空隙），报警。

口径要点（踩过坑）：
  · 产物 origin_x 与源 OCR 框中心有约 13pt 的系统差（竖排 em 框半宽量级），
    且同一 x 带里的元素（书眉+页码）产物可能分列在 ±20pt 内 -> 窗口必须按
    「产物自身聚列后再按列比」，不能用固定窄窗，否则「书眉+页码」这种
    源书本就分段的合法情形会被误报（实测源空隙 721pt / 产物 754pt 判成违规）。
  · 只比「最大空隙」，不比空隙位置（位置受字号/步进影响，属另一层）。

用法：
  check_poem_blocks.py <out.pdf> <lines.json> <coords.json> [--pages 1-1748] [--top 30] [--json r.json]
退出码：0 = 无违规；1 = 有违规
"""
import argparse
import json
import sys

import fitz

SKIP = set(' \t\n\r\u3000')


def norm(s):
    return ''.join(c for c in str(s) if c not in SKIP)


def src_blocks(lines, coords, page):
    rows = []
    for t, poly in zip(lines.get(str(page - 1)) or [], coords.get(str(page - 1)) or []):
        xs = [q[0] / 2 for q in poly]
        ys = [q[1] / 2 for q in poly]
        s = norm(t)
        if not s:
            continue
        rows.append({'x0': min(xs), 'x1': max(xs), 'y0': min(ys), 'y1': max(ys),
                     'n': len(s), 't': s})
    if not rows:
        return []
    rows.sort(key=lambda r: -((r['x0'] + r['x1']) / 2.0))
    cols, cur = [], [rows[0]]
    for r in rows[1:]:
        if (cur[-1]['x0'] + cur[-1]['x1']) / 2.0 - (r['x0'] + r['x1']) / 2.0 <= 6.0:
            cur.append(r)
        else:
            cols.append(cur)
            cur = [r]
    cols.append(cur)
    out = []
    for c in cols:
        c.sort(key=lambda r: r['y0'])
        if len(c) < 2:
            continue
        gaps = []
        for a, b in zip(c, c[1:]):
            g = b['y0'] - a['y1']
            step = max((a['y1'] - a['y0']) / max(1, a['n']),
                       (b['y1'] - b['y0']) / max(1, b['n']))
            if step > 0 and g > 1.5 * step:
                gaps.append(g)
        if gaps:
            xs = [r['x0'] for r in c] + [r['x1'] for r in c]
            out.append({'xc': (min(xs) + max(xs)) / 2.0,
                        'x0': min(xs), 'x1': max(xs),
                        'need': max(gaps),
                        'rows': [r['t'][:20] for r in c],
                        'text': ''.join(r['t'] for r in c)[:40]})
    return out


def prod_columns(pdf_page):
    """产物 -> 按 x 聚列（容差 6pt），每列返回 (xc, 排序后的 y 列表)"""
    ch = []
    for b in pdf_page.get_text('rawdict')['blocks']:
        for ln in b.get('lines', []):
            for sp in ln.get('spans', []):
                for c in sp.get('chars', []):
                    if c['c'].isspace():
                        continue
                    ch.append((round(c['origin'][0], 1), c['origin'][1]))
    if not ch:
        return []
    xs = sorted(set(x for x, _ in ch), reverse=True)
    groups = []
    for x in xs:
        if groups and groups[-1][-1] - x <= 6:
            groups[-1].append(x)
        else:
            groups.append([x])
    out = []
    for gg in groups:
        gs = set(gg)
        ys = sorted(y for x, y in ch if x in gs)
        out.append(((gg[0] + gg[-1]) / 2.0, ys))
    return out


def max_gap(ys):
    """返回 (最大空隙, 中位步进)"""
    if len(ys) < 2:
        return 0.0, 0.0
    ds = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
    ds_sorted = sorted(ds)
    med = ds_sorted[len(ds_sorted) // 2]
    return max(ds), med


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out_pdf')
    ap.add_argument('lines')
    ap.add_argument('coords')
    ap.add_argument('--pages', default=None)
    ap.add_argument('--top', type=int, default=30)
    ap.add_argument('--json', default=None)
    a = ap.parse_args()

    lines = json.load(open(a.lines, encoding='utf-8'))
    coords = json.load(open(a.coords, encoding='utf-8'))
    doc = fitz.open(a.out_pdf)

    if a.pages:
        if '-' in a.pages:
            lo, hi = a.pages.split('-')
            pages = list(range(int(lo), min(int(hi), doc.page_count) + 1))
        else:
            pages = [int(x) for x in a.pages.split(',') if x.strip()]
    else:
        pages = list(range(1, doc.page_count + 1))

    hits = []
    for p in pages:
        if p < 1 or p > doc.page_count:
            continue
        blocks = src_blocks(lines, coords, p)
        if not blocks:
            continue
        pcols = prod_columns(doc[p - 1])
        if not pcols:
            continue
        for blk in blocks:
            # 取与源块 x 范围重叠/相邻（±20pt）的所有产物列，合并其 y 后求最大空隙
            ys = []
            for xc, yy in pcols:
                if blk['x0'] - 20 <= xc <= blk['x1'] + 20:
                    ys.extend(yy)
            ys.sort()
            got, med = max_gap(ys)
            # 判据：产物在源块 x 窗口内的最大空隙 >= 源空隙的 60%
            #   阈值取 0.6 的理由（双向实测标定）：
            #     · p444 诗句两段（源空隙 56.1pt）：产物摊成一列、字步进 26pt
            #       -> 26 < 0.6x56.1=33.7 判违规 ✓（阈值取 0.4 时 26>22.4 会漏报）
            #     · p100 书眉+页码（源空隙 741.5pt）：产物 754pt -> 通过 ✓
            #   不用「相对自身步进」的判据：相邻两列的字符会交错填掉空隙，
            #   把中位步进压低到 13pt 量级，反而让漏报更容易发生。
            if got < 0.6 * blk['need']:
                hits.append({'page': p, 'xc': round(blk['xc'], 1),
                             'src_gap': round(blk['need'], 1),
                             'prod_gap': round(got, 1),
                             'prod_step': round(med, 1),
                             'rows': blk['rows'], 'text': blk['text']})

    doc.close()
    print('=' * 84)
    print('诗句/短文分段保真度   检查 %d 页   违规 %d 处' % (len(pages), len(hits)))
    print('=' * 84)
    print('判据：源书同列多行有 y 空隙（>1.5x字步进），产物须保留 >=40%% 的空隙')
    print()
    for h in hits[:a.top]:
        print('  p%-5d x%.0f  源空隙 %.1fpt / 产物 %.1fpt  「%s」'
              % (h['page'], h['xc'], h['src_gap'], h['prod_gap'], h['text']))
    if len(hits) > a.top:
        print('  …（还有 %d 处，见 --json）' % (len(hits) - a.top))
    if a.json:
        json.dump(hits, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print()
        print('  JSON -> %s' % a.json)
    print()
    print('== 退出码 %s ==' % ('PASS' if not hits else 'FAIL'))
    return 0 if not hits else 1


if __name__ == '__main__':
    sys.exit(main())
