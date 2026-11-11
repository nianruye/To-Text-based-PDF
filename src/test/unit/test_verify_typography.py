#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_typography 单测（t239）：判据/归因/gating + 真实红绿 fixture（缺失则 skip）。"""
import importlib.util
import json
import os
import sys
import types

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
_spec = importlib.util.spec_from_file_location('vt_verify_typography_under_test', os.path.join(ROOT, 'src/test/verify_typography.py'))
vt = importlib.util.module_from_spec(_spec)
# t246：唯一模块名 + 注册 sys.modules，避免全量 suite 同名模块缓存冲突
sys.modules['vt_verify_typography_under_test'] = vt
_spec.loader.exec_module(vt)


def _line(spans, page=1):
    bbox = [min(s['bbox'][0] for s in spans), min(s['bbox'][1] for s in spans),
            max(s['bbox'][2] for s in spans), max(s['bbox'][3] for s in spans)]
    return dict(text=''.join(s['text'] for s in spans), bbox=bbox, spans=spans, page=page)


def _span(text, x0, y0, x1, y1, size=16.4):
    return dict(text=text, bbox=[x0, y0, x1, y1], size=size, origin=(x0, y1))


def test_hard_span_overlap_negative_gap():
    spans = [_span('1.', 134.1, 228.9, 154.1, 252.1, 16.4),
             _span(' 标题', 145.8, 217.6, 300.0, 264.6, 16.4)]
    v = vt._span_violations([_line(spans)])
    assert v and v[0]['name'] == 'hard_span_overlap' and abs(v[0]['gap'] + 8.32) < 0.05


def test_toc_font_indent_pagenum():
    lines = [
        _line([_span('1.', 134.1, 228.9, 154.1, 252.1, 16.4), _span(' 甲', 145.8, 217.6, 300, 264.6, 16.4)]),
        _line([_span('2.', 162.6, 230.4, 174.3, 295.9, 22.9), _span(' 乙', 174.3, 230.4, 300, 295.9, 22.9)]),
        _line([_span('续行', 94.6, 252.7, 140.5, 318.1, 22.9)]),
        _line([_span('续行2', 149.6, 300, 200, 340, 22.9)]),
        _line([_span('2', 143.3, 190.8, 149.6, 208.9, 12.9)]),
        _line([_span('3', 127.8, 232.9, 134.1, 251.0, 12.9)]),
    ]
    names = {v['name']: v for v in vt._toc_metrics(lines, 11)}
    assert 'toc_font_inconsistent' in names and 16.4 in names['toc_font_inconsistent']['values'] and 22.9 in names['toc_font_inconsistent']['values']
    assert 'toc_cont_indent' in names and 94.6 in names['toc_cont_indent']['values'] and 149.6 in names['toc_cont_indent']['values']
    assert 'toc_pagenum_align' in names and {134.1, 149.6} <= set(names['toc_pagenum_align']['values'])


def test_attribution_source_inherent_and_render():
    src = {'9': ['——毛泽东关于党不变质思想探寻', '正文'],
           '4': ['—北京:社会科学文献出版社, 2012.7']}
    a1, _ = vt._attribute_text(9, '——毛泽东关于党不变质思想探寻', {'9': ['——毛泽东关于党不变质思想探寻']}, '')
    assert a1 == 'source_inherent'
    a2, _ = vt._attribute_text(4, '—北京: 社会科学文献出版社, 2012.7', src, '图书在版编目 (cip) 数据')
    assert a2 == 'source_inherent'  # t250：源同位置同字符，不得 CIP 特判为 render


def _args(pdf, src='', lines='', book_type='horizontal'):
    return types.SimpleNamespace(pdf=pdf, src_pdf=src, lines=lines, coords='', json='',
                                 book_type=book_type, page_image_pages='')






def test_quality_gate_component_decision_a():
    import sys
    sys.path.insert(0, os.path.join(ROOT, 'src/tools'))
    import quality_gate as qg
    c = qg.typography_component(dict(verdict='FAIL', compliance_rate=0.9, body_lines=10,
                                     counts=dict(hard=1, render_introduced=2),
                                     layers=dict(hard='fail', gb='fail')))
    assert c['fail'] and 'typography_hard' in c['reasons'] and 'typography_render_introduced' in c['reasons']
    c2 = qg.typography_component(dict(verdict='WARN', compliance_rate=1.0, body_lines=10,
                                      counts=dict(hard=0, render_introduced=0)))
    assert not c2['fail'] and c2['warn']


def test_rule_inventory_15_plus_2_exempt():
    assert len(vt.GB51_RULES) == 9
    assert len(vt.GB52_RULES) == 6
    assert set(vt.EXEMPT_GB51) == {'5.1.8', '5.1.11'}
    assert vt.EXEMPT_GB51['5.1.8'] == 'not_machine_checkable_from_text_layer'
    assert vt.EXEMPT_GB51['5.1.11'] == 'permissive_clause'


def test_gb52_six_rules_emitted():
    spans = [_span('。', 10, 10, 25, 40, 20), _span('“', 30, 10, 45, 40, 20),
             _span('—', 50, 10, 55, 60, 20)]
    spans2 = [_span('1', 60, 10, 70, 15, 20), _span('“', 70, 10, 90, 40, 20)]
    lines = [_line(spans), _line(spans2)]
    got = vt._gb52_violations(lines, 0, 'vertical')
    assert set(v['rule_id'] for v in got) == {'5.2.1', '5.2.2', '5.2.3', '5.2.4', '5.2.5', '5.2.6'}
    assert all(v['severity'] == 'warn' and v['attribution'] == 'vertical_stat' for v in got)


def _sp(text, x0=10, x1=30, y0=10, y1=40, size=20):
    return _span(text, x0, y0, x1, y1, size)


def test_separator_rule_only_slash():
    # 反例：，。；：、” 不得报 5.1.9；只有 / 报
    for ch in '，。；：、”':
        v, _ = vt._gb51_violations([_line([_sp(ch), _sp('正文', 40, 10, 80, 40)])], 0, {}, '', 600)
        assert not [x for x in v if x['rule_id'] == '5.1.9'], ch
    v, _ = vt._gb51_violations([_line([_sp('/'), _sp('正文', 40, 10, 80, 40)])], 0, {}, '', 600)
    assert [x for x in v if x['rule_id'] == '5.1.9']


def test_lineend_halfwidth_only_punctuation():
    # 反例：行末数字/字母不报 5.1.10（仅标点；宽度判据）
    for st in '0123abcXYZ':
        v, _ = vt._gb51_violations([_line([_sp(st, 10, 10, 25, 40)])], 0, {}, '', 600)
        assert not [x for x in v if x['rule_id'] == '5.1.10'], st
    # 正例：行末全角标点宽度 <0.5×size（不越界）
    v, _ = vt._gb51_violations([_line([_sp('。', 10, 10, 15, 40)])], 0, {}, '', 600)
    assert [x for x in v if x['rule_id'] == '5.1.10']


def test_dot_rule_not_quotes():
    # 反例：行首 “ 属 5.1.3，不属 5.1.1
    v, _ = vt._gb51_violations([_line([_sp('正文', 10, 10, 40, 40), _sp('“', 45, 10, 60, 40)])], 0, {}, '', 600)
    assert not [x for x in v if x['rule_id'] == '5.1.1']



def test_line_end_dot_is_legal():
    # ① 句读在行末（…多党制」。）不得报 dot_line_start
    line = _line([_sp('“我们不应当像魔鬼怕烧香那样害怕多党制”。', 154.3, 10, 509.0, 40)])
    v, _ = vt._gb51_violations([line], 0, {}, '', 600)
    assert not [x for x in v if x['rule_id'] == '5.1.1']


def test_line_start_dot_reports():
    # ② 句读在行首才报
    line = _line([_span('。正文', 10, 10, 80, 40)])
    v, _ = vt._gb51_violations([line], 0, {}, '', 600)
    assert [x for x in v if x['rule_id'] == '5.1.1']


def test_span_order_uses_visual_x_order():
    # ③ span 列表顺序与 x 序不一致：右端句号先入列表，左端引号才是视觉行首
    spans = [_span('”。', 480, 10, 509, 40), _span('“正文', 154, 10, 480, 40)]
    line = _line(spans)
    v, _ = vt._gb51_violations([line], 0, {}, '', 600)
    assert not [x for x in v if x['rule_id'] == '5.1.1']


def test_l3_report_has_bbox_and_line_range():
    line = _line([_span('。正文', 10, 10, 80, 40)])
    v, _ = vt._gb51_violations([line], 0, {}, '', 600)
    hit = [x for x in v if x['rule_id'] == '5.1.1'][0]
    assert 'bbox' in hit and hit['line_x_min'] == 10 and hit['line_x_max'] == 80


def test_synthetic_red_gap_font_cont_pagenum():
    # 合成红侧：span 负 gap + TOC 字号/续行/页码列
    l1 = _line([_span('1.', 134.1, 228.9, 154.1, 252.1, 16.4),
                _span(' 标题', 145.8, 217.6, 300, 264.6, 16.4)])
    assert vt._span_violations([l1])[0]['gap'] == -8.3
    l2 = _line([_span('2.', 162.6, 230.4, 174.3, 295.9, 22.9),
                _span(' 标题', 174.3, 230.4, 300, 295.9, 22.9)])
    l3 = _line([_span('续行', 94.6, 252.7, 140.5, 318.1, 22.9)])
    l4 = _line([_span('续行2', 149.6, 300, 200, 340, 22.9)])
    l5 = _line([_span('2', 143.3, 190.8, 149.6, 208.9, 12.9)])
    l6 = _line([_span('3', 127.8, 232.9, 134.1, 251.0, 12.9)])
    names = {v['name']: v for v in vt._toc_metrics([l1, l2, l3, l4, l5, l6], 11)}
    assert names['toc_font_inconsistent']['values'] == [16.4, 22.9]
    assert 94.6 in names['toc_cont_indent']['values'] and 149.6 in names['toc_cont_indent']['values']
    assert {134.1, 149.6} <= set(names['toc_pagenum_align']['values'])


def test_synthetic_render_and_source_attribution():
    # source 同页不同首字符 → render；相同 → source
    assert vt._attribute_edge(0, '。正文内容足够长', '。', {'0': ['正文内容足够长']})[0] == 'render_introduced'
    assert vt._attribute_edge(0, '——正文内容足够长', '—', {'0': ['——正文内容足够长']})[0] == 'source_inherent'


def test_synthetic_nonbody_requires_three_features():
    assert not vt._is_nonbody_page('md5 only', 0, set())
    assert vt._is_nonbody_page('md5 filesize total_pages', 0, set())
    assert vt._is_nonbody_page('plain body', 4, {4})


def test_general_overlap_cross_line_only():
    l1 = _line([_span('第一行文字', 10, 10, 120, 40)])
    l2 = _line([_span('第二行文字', 20, 20, 130, 50)])
    assert vt._general_overlap([l1, l2])
    same = _line([_span('标题文字', 10, 10, 100, 40), _span('重叠', 80, 10, 120, 40)])
    assert not vt._general_overlap([same])


def test_m1_diagnostic_not_counted(tmp_path, monkeypatch):
    import fitz
    pdf = str(tmp_path / 'm1.pdf')
    d = fitz.open(); p = d.new_page(width=300, height=300)
    p.insert_text((20, 50), 'ABCDEFGH', fontsize=20)
    p.insert_text((22, 52), 'IJKLMNOP', fontsize=20)
    d.save(pdf); d.close()
    monkeypatch.setenv('TYPOGRAPHY_M1', '1')
    ns = _args(pdf); ns.json = str(tmp_path / 'm1.json')
    vt.run(ns)
    r = json.load(open(ns.json, encoding='utf-8'))
    assert 'M1' in r['diagnostics'] and r['layers']['L1'] == ['M2', 'M5']
    assert r['counts']['hard'] == 0


def test_subset_pages_triggers_m5(tmp_path):
    import fitz
    src = str(tmp_path / 'src.pdf'); out = str(tmp_path / 'out.pdf')
    for path, n in ((src, 2), (out, 1)):
        d = fitz.open()
        for _ in range(n): d.new_page(width=100, height=100).insert_text((10, 20), 'x', fontsize=10)
        d.save(path); d.close()
    ns = _args(out, src); ns.json = str(tmp_path / 'm5.json')
    vt.run(ns)
    r = json.load(open(ns.json, encoding='utf-8'))
    assert any(v['name'] == 'hard_page_1to1' for v in r['violations'])
