#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从生成的 PDF 提取结构化 Markdown。

按字号相对正文反推结构(通用化, 不再硬编码绝对阈值):
  body = 全书正文字号众数(排除页眉/脚注区)
  >= body+8pt = 大标题(part/title) -> #
  >= body+3pt = 节标题(section)     -> ##
  >= body+2pt = 小节(subsection)     -> ###
  其余 = 正文(body)

按 y 位置分页,同页内按 y 排序。正文按缩进分段(x0 差异),段首缩进去掉。
脚注用 [^N] 引用。

用法: /usr/bin/python3 pdf2md.py [in.pdf] [out.md]
"""
import fitz, sys, re, os, statistics

PDF = sys.argv[1] if len(sys.argv) > 1 else 'output/wz1/wz1_geom_optimized.pdf'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'output/wz1/wz1.md'

doc = fitz.open(PDF)

# ── 第一遍: 统计全书正文字号(众数) ──
# 取每页"主体字号"= 页中部(y 在 15%~85%)行的字号众数, 全书取中位。
page_body_sizes = []
for pgi in range(min(len(doc), 200)):   # 采样前 200 页足够(字号体系全书一致)
    d = doc[pgi].get_text('dict')
    ph = doc[pgi].rect.height
    sizes = []
    for blk in d.get('blocks', []):
        for ln in blk.get('lines', []):
            spans = ln.get('spans', [])
            if not spans:
                continue
            y0, y1 = ln['bbox'][1], ln['bbox'][3]
            if y0 < ph * 0.15 or y0 > ph * 0.85:
                continue   # 排除页眉/页码/脚注区
            txt = ''.join(s.get('text', '') for s in spans).strip()
            if not txt or txt.startswith('GMPG'):
                continue
            sizes.append(max(s.get('size', 0) for s in spans))
    if sizes:
        # 众数
        from collections import Counter
        page_body_sizes.append(Counter(round(s, 1) for s in sizes).most_common(1)[0][0])
BODY = statistics.median(page_body_sizes) if page_body_sizes else 10.0
print(f"[pdf2md] 正文字号(众数中位) = {BODY:.1f}pt; 标题阈值 #≥{BODY+8:.1f} ##≥{BODY+3:.1f} ###≥{BODY+2:.1f}")

md_lines = []
fn_counter = [0]
for pgi in range(len(doc)):
    pg = doc[pgi]
    d = pg.get_text('dict')
    hrules = []
    for dr in pg.get_drawings():
        r = dr.get('rect')
        if r and r.height < 2 and r.width > 50:
            hrules.append(r.y0)
    lines = []
    for blk in d.get('blocks', []):
        for ln in blk.get('lines', []):
            spans = ln.get('spans', [])
            if not spans:
                continue
            x0, y0, x1, y1 = ln['bbox']
            sz = max(s.get('size', 0) for s in spans)
            txt = ''.join(s.get('text', '') for s in spans).strip()
            if not txt or y1 - y0 <= 0.5:
                continue
            if txt.startswith('GMPG'):
                continue
            lines.append((y0, x0, sz, txt))
    lines.sort()
    hrule_y = min(hrules) if hrules else 9999
    page_body = []
    page_footnotes = []
    for y0, x0, sz, txt in lines:
        if y0 > hrule_y and sz < BODY - 1.5:
            page_footnotes.append(txt)
        elif sz < BODY - 2 and y0 < hrule_y:
            continue   # 页眉(小于正文的小字)
        else:
            page_body.append((y0, x0, sz, txt))
    prev_x0 = None
    for y0, x0, sz, txt in page_body:
        if sz >= BODY + 8:
            md_lines.append(f'\n# {txt}\n')
        elif sz >= BODY + 3:
            md_lines.append(f'\n## {txt}\n')
        elif sz >= BODY + 2:
            md_lines.append(f'\n### {txt}\n')
        else:
            if prev_x0 is not None and abs(x0 - prev_x0) > 15:
                md_lines.append('')   # 缩进变化=新段
            md_lines.append(txt)
            prev_x0 = x0
    for fn in page_footnotes:
        fn_counter[0] += 1
        md_lines.append(f'\n[^{fn_counter[0]}]: {fn}')
    md_lines.append('\n---\n')   # 分页

md = '\n'.join(md_lines)
md = re.sub(r'\n{4,}', '\n\n\n', md)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(md)
print(f"完成: {len(doc)}页 -> {OUT} ({len(md)}字)")
