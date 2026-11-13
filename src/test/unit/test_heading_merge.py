#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t232: 标题续行（OCR 折行）整块字体/字号一致。"""
import os
import pytest
import fitz

PDF = 'output/ghbq_full/ghbq_title_toc.pdf'


@pytest.fixture(scope='module')
def doc():
    if not os.path.exists(PDF):
        pytest.skip('ghbq_title_toc.pdf 未构建（构建门禁另跑）')
    d = fitz.open(PDF)
    yield d
    d.close()


def test_p14_title_continuation_unified_font(doc):
    lines = []
    for b in doc[13].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            if t.startswith('一') or t.startswith('成与发展'):
                lines.append((t, [(s['font'], round(s['size'], 1)) for s in l['spans']]))
    assert len(lines) >= 2, lines
    # 同一标题块：两行字体与字号一致（不得半行宋体半行黑体）
    assert lines[0][1] == lines[1][1], lines
