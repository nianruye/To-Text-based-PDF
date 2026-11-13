#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t232/t235: ghbq 目录页码前置、续行缩进、同级字号、页码右对齐。"""
import os
import re
import pytest
import fitz

PDF = ('output/ghbq_full/ghbq_title_toc3.pdf' if os.path.exists('output/ghbq_full/ghbq_title_toc3.pdf') else 'output/ghbq_full/ghbq_title_toc2.pdf')


@pytest.fixture(scope='module')
def doc():
    if not os.path.exists(PDF):
        pytest.skip('ghbq_title_toc2.pdf 未构建（构建门禁另跑）')
    d = fitz.open(PDF)
    yield d
    d.close()


def _spans(page):
    out = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                t = s['text'].strip()
                if t:
                    out.append((t, s['bbox'], s['size']))
    return out


def test_p11_no_page_number_glue(doc):
    text = doc[10].get_text()
    for bad in ('112.', '211.', '263.'):
        assert bad not in text, (bad, text)


def test_p11_page_before_title(doc):
    lines = [l.strip() for l in doc[10].get_text().splitlines() if l.strip()]
    assert any(re.match(r'^2\s+一', l) for l in lines), lines
    assert any(re.match(r'^11\s+2\.', l) for l in lines), lines
    assert any(re.match(r'^21\s+二', l) for l in lines), lines


def test_p11_page_column_right_aligned(doc):
    pages = [(t, b) for t, b, sz in _spans(doc[10]) if t.isdigit() and sz < 13]
    assert len(pages) >= 5, pages
    x1s = [b[2] for _, b in pages]
    assert max(x1s) - min(x1s) <= 1.0, pages


def test_p11_section_font_same(doc):
    sizes = [sz for t, b, sz in _spans(doc[10]) if re.match(r'^[123]\.', t)]
    assert len(sizes) >= 4, sizes
    assert max(sizes) - min(sizes) <= 0.5, sizes


def test_p11_continuation_x_matches_title_text(doc):
    spans = _spans(doc[10])
    # 每个续行/标题文字的 x0 应与同一条目首行标题文字 x0 差 <=2pt
    for cont in ('形成与发展', '和准备', '及纲领主张', '多元化'):
        c = [b for t, b, sz in spans if t == cont]
        assert c, cont
        # 取该续行前最近一条更宽（标题首行）span
        ci = next(i for i, (t, b, sz) in enumerate(spans) if t == cont)
        prev = [spans[i] for i in range(ci) if spans[i][2] >= 16.4 and not spans[i][0].isdigit()]
        assert prev, cont
        first = prev[-1][1]
        assert abs(c[0][0] - first[0]) <= 2.0, (cont, c[0], first)


def test_p11_seq_title_gap_char_level(doc):
    """D: 序号末字符 -> 标题首可见字形（不是 span bbox，标题 span 可带前导空格）。"""
    raw = doc[10].get_text('rawdict')
    gaps = {}
    for b in raw['blocks']:
        for l in b.get('lines', []):
            spans = l.get('spans', [])
            for i, s in enumerate(spans):
                chars = s.get('chars', [])
                txt = ''.join(c['c'] for c in chars).strip()
                if not re.match(r'^[123]\.', txt) or i + 1 >= len(spans):
                    continue
                last = next((c for c in reversed(chars) if c['c'].strip()), None)
                nxt = next((c for c in spans[i+1].get('chars', []) if c['c'].strip()), None)
                if last is None or nxt is None:
                    continue
                gap = nxt['bbox'][0] - last['bbox'][2]
                key = 'quote' if nxt['c'] in '“"‘' else 'cjk'
                gaps[key] = gap
                break
    assert 'quote' in gaps and gaps['quote'] >= 1.0, gaps
    assert 'cjk' in gaps and gaps['cjk'] >= 1.0, gaps


def test_p97_giant_ocr_page_within_measure(doc):
    """p97: OCR 整页并行行经整页贴图兜底后，所有文本 span x1 仍在版心右缘内。"""
    pdf3 = 'output/ghbq_full/ghbq_title_toc3.pdf'
    if not os.path.exists(pdf3):
        pytest.skip('ghbq_title_toc3.pdf 未构建')
    d3 = fitz.open(pdf3)
    page = d3[96]
    x1 = max(s['bbox'][2] for b in page.get_text('dict')['blocks']
             for l in b.get('lines', []) for s in l['spans'])
    assert x1 <= 506.75 + 2.0, x1
    d3.close()


def test_layout_title_level_mapping():
    """t277: paragraph_title 前缀 -> L1/L2/L3（只影响层级，不改字号）。"""
    from _loader import load
    ns = load('build_geom.py', {'_layout_title_level'})
    f = ns['_layout_title_level']
    assert f('一 “人道的民主的社会主义”理论和路线的形成与发展') == 1
    assert f('三“人道的民主的社会主义”主要理论观点') == 1
    assert f('四 几点结论') == 1
    assert f('1.“人道的民主的社会主义”理论与路线的酝酿和准备') == 2
    assert f('2. 否定现实社会主义') == 2
    assert f('群众性集会和游行示威此起彼伏') == 3
