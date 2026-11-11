#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t254：M2 任一边越出可打印区 → hard（合成 fixture，hermetic）。"""
import importlib.util
import json
import os
import sys
import types

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
_spec = importlib.util.spec_from_file_location('vt_m2_test', os.path.join(ROOT, 'src/test/verify_typography.py'))
vt = importlib.util.module_from_spec(_spec)
sys.modules['vt_m2_test'] = vt
_spec.loader.exec_module(vt)


def _args(pdf, json_path):
    return types.SimpleNamespace(pdf=pdf, src_pdf='', lines='', coords='', json=json_path,
                                 book_type='horizontal', page_image_pages='')


def _make_pdf(path, texts):
    import fitz
    d = fitz.open(); p = d.new_page(width=200, height=200)
    for text, x, y in texts:
        p.insert_text((x, y), text, fontsize=10)
    d.save(path); d.close()


def _run(tmp_path, texts):
    pdf = str(tmp_path / 'm2.pdf'); js = str(tmp_path / 'm2.json')
    _make_pdf(pdf, texts)
    vt.run(_args(pdf, js))
    return json.load(open(js, encoding='utf-8'))


def test_right_edge_10pct_hard(tmp_path):
    r = _run(tmp_path, [('ABCDEFGHIJK', 190, 50)])
    assert r['counts']['hard'] >= 1
    assert any(v['name'] == 'hard_text_out_of_page' for v in r['violations'])


def test_left_top_bottom_edges_hard(tmp_path):
    for texts in ([('ABCDEFGHIJK', -40, 50)], [('ABCDEFGHIJK', 20, 1)], [('ABCDEFGHIJK', 20, 230)]):
        r = _run(tmp_path, texts)
        assert any(v['name'] == 'hard_text_out_of_page' for v in r['violations']), texts


def test_fully_outside_hard(tmp_path):
    r = _run(tmp_path, [('ABCDEFGHIJK', 300, 50)])
    assert any(v['name'] == 'hard_text_out_of_page' for v in r['violations'])


def test_inside_tolerance_not_hard(tmp_path):
    r = _run(tmp_path, [('ABCDEFGHIJK', 20, 100)])
    assert r['counts']['hard'] == 0


def test_nonbody_requires_three_features():
    assert not vt._is_nonbody_page('isbn 图书在版编目 上架建议 简介正文', 0, set())
    assert vt._is_nonbody_page("anna's archive md5 total_pages", 0, set())


def test_edge_pos_end_uses_source_tail():
    spans = [dict(text='正文“', bbox=[10, 10, 80, 40], size=16, origin=(10, 40))]
    line = dict(text='正文“', bbox=[10, 10, 80, 40], spans=spans, page=1)
    v, w = vt._gb51_violations([line], 0, {'0': ['正文“']}, '', 200)
    assert not [x for x in v if x['rule_id'] == '5.1.3']
    assert [x for x in w if x['rule_id'] == '5.1.3']
