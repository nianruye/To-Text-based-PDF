#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t192：LAYJSON image 块裁剪 + 开关/缺失回退的可执行单测。"""
import json
import os
import sys
import tempfile
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'src' / 'tools'))
import ocr_book as ob
import scan2pdf as s2p
from utils import image_blocks as ib
from _loader import load


def _src(path):
    d = fitz.open()
    p = d.new_page(width=300, height=400)
    p.draw_rect(fitz.Rect(20, 100, 280, 300), color=(1, 0, 0), fill=(1, 0, 0))
    d.save(path); d.close(); return path


def test_layout_image_category_preserved():
    with tempfile.TemporaryDirectory() as tmp:
        src = _src(os.path.join(tmp, 'src.pdf')); os.makedirs(os.path.join(tmp, 'raw'))
        page = dict(prunedResult=dict(width=600, height=800, parsing_res_list=[
            dict(block_label='image', block_content='', block_bbox=[0, 200, 600, 500]),
            dict(block_label='chart', block_content='', block_bbox=[400, 600, 580, 760])]))
        with open(os.path.join(tmp, 'raw', 'layout_000.json'), 'w', encoding='utf-8') as f:
            f.write(json.dumps(dict(result=dict(layoutParsingResults=[page])), ensure_ascii=False) + '\n')
        p, n = ob.convert_layout_json(tmp, src, 'x', {'layout_000': dict(pages=[0])})
        blocks = json.load(open(p, encoding='utf-8'))[0]['blocks']
        assert [b['category'] for b in blocks] == ['image', 'chart']


def test_extract_figs_crops_source_bbox():
    with tempfile.TemporaryDirectory() as tmp:
        src = _src(os.path.join(tmp, 'src.pdf'))
        ctx = dict(_figs={'0': [[0, 200, 600, 500]]}, SRC=src, LDPI=142.0)
        out = ib.extract_figs('0', ctx)
        assert len(out) == 1 and os.path.getsize(out[0][0]) > 0
        im = fitz.open(out[0][0])
        assert im[0].rect.width > 0 and im[0].rect.height > 0
        im.close()


def test_layout_missing_falls_back():
    with tempfile.TemporaryDirectory() as tmp:
        src = _src(os.path.join(tmp, 'src.pdf'))
        assert s2p.find_layout('', tmp, 'x', src)[2] == 'missing'


def test_layout_toc_page_detection():
    ns = load('build_geom.py', {'_layout_toc_page'})
    f = ns['_layout_toc_page']
    assert f([{'block_label': 'header', 'block_content': '目录'}])
    assert f([{'block_label': 'header', 'block_content': 'CONTENTS'}])
    assert f([{'block_label': 'aside_text', 'block_content': '2\n3\n11'}])
    assert not f([{'block_label': 'text', 'block_content': '正文'}])
    assert not f([{'block_label': 'aside_text', 'block_content': '书名'}])


def test_image_page_full_ratio_boundary():
    ns = load('build_geom.py', {'_image_page_full'},
              mocks={'PAGE_IMAGE_FULL_RATIO': 0.40})
    f = ns['_image_page_full']
    assert not f(0.399)
    assert f(0.40)       # >= 边界
    assert f(0.401)
    assert not f(0.5, 0.55)
    assert f(0.55, 0.55)
