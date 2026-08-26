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
    header_rows = []
    ph = pg.rect.height
    for y0, x0, sz, txt in lines:
        if y0 > hrule_y and sz < BODY - 1.5:
            page_footnotes.append(txt)
        elif y0 < ph * 0.05:
            header_rows.append(txt)   # 页眉区行: 后置分类(真页眉丢弃 / OCR 错置正文归回上页)。阈值5%: 紧凑版心书(mgfdmg 正文首行 y≈40pt=6.7%页高)不误划页眉区
        elif sz < BODY - 2 and y0 < hrule_y:
            continue   # 顶部小字(残留兜底)
        else:
            page_body.append((y0, x0, sz, txt))
    # 页眉区行分类:
    #   - 与本页正文首行重复(词典式页眉=本页首词) 或 短行(≤15字, 书名/章名页眉) → 真页眉, 丢弃
    #   - 其余长行 → OCR 页面分割错置的上页尾段, 归回上一页末尾(插到分页符前)
    _body_first = page_body[0][3] if page_body else ''
    _body_texts = [t for _, _, _, t in page_body]
    for ht in header_rows:
        if len(ht) <= 15:
            continue   # 短行=真页眉(书名/章名)
        # 剥离与正文行重叠的前缀(词典式页眉=本页首词拼在行首, 首词与正文首行重复)
        _rest = ht
        for t in _body_texts:
            _i = 0
            while _i < min(len(_rest), len(t)) and _rest[_i] == t[_i]:
                _i += 1
            if _i >= 8:   # 公共前缀≥8字=真实重叠(非巧合)
                _rest = _rest[_i:].strip()
                break
        if len(_rest) < 8:
            continue   # 剥完所剩无几=纯页眉
        # 错置正文(OCR 页面分割把上页尾段划到本页顶部): 归回上一页末尾(分页符前)
        _pos = len(md_lines)
        for _i in range(len(md_lines) - 1, -1, -1):
            if md_lines[_i].strip() == '---':
                _pos = _i
                break
        # 与插入点上一行(同为错置段)做共同后缀去重: 拼接页眉行尾部常与独立错置行重复
        _nb = md_lines[_pos - 1].strip() if _pos > 0 else ''
        _k = 0
        while _k < min(len(_rest), len(_nb)) and _rest[len(_rest) - 1 - _k] == _nb[len(_nb) - 1 - _k]:
            _k += 1
        if _k >= 12:
            _rest = _rest[:len(_rest) - _k].rstrip()
        if len(_rest) >= 8:
            md_lines.insert(_pos, _rest)
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
