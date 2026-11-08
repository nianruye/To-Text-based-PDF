#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quality_gate 单测：三档判定、verify 解析、合成逻辑（薄封装，不跑真实 PDF）。"""
import json, os, sys
import fitz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import quality_gate as qg


def _punct(cls, p, r):
    return {cls: dict(tp=10, fp=0, fn=0, precision=p, recall=r)}


def test_verify_parse_pass():
    txt = '页数: 源 OCR 231 页  |  输出 PDF 231 页  |  ✓ 1:1\n字符量: 输出 68016 / OCR 69998 = 97.2%\n越界: span 0 个 / 矢量图形 0 个\n整页丢失(0 字)页: 0 个'
    m = qg.parse_verify_stdout(txt)
    assert m['pages'] == 231 and m['pages_src'] == 231
    assert m['chars_ratio'] == 97.2
    assert m['overflow_span'] == 0 and m['page_loss'] == 0


def test_judge_punct_auto():
    v, reasons, fail = qg.judge_punct(_punct('comma', 0.99, 0.97))
    assert v == 'AUTO' and fail == []


def test_judge_punct_manual():
    v, reasons, fail = qg.judge_punct(_punct('comma', 0.93, 0.90))
    assert v == 'MANUAL' and 'punct_below_auto' in reasons


def test_judge_punct_reject():
    v, reasons, fail = qg.judge_punct(_punct('comma', 0.50, 0.50))
    assert v == 'REJECT' and 'punct_regression' in reasons and fail


def test_judge_content_auto():
    m = dict(with_punct=dict(cer=0.010, missing_rate=0.0, wrong_rate=0.0, extra_rate=0.0),
             han_only=dict(cer=0.008), must_pass=True)
    v, _, _ = qg.judge_content(m)
    assert v == 'AUTO'


def test_judge_content_manual():
    m = dict(with_punct=dict(cer=0.030, missing_rate=0.0, wrong_rate=0.0, extra_rate=0.0),
             han_only=dict(cer=0.020), must_pass=True)
    v, reasons, _ = qg.judge_content(m)
    assert v == 'MANUAL' and 'content_below_auto' in reasons


def test_judge_content_reject_cer_over():
    m = dict(with_punct=dict(cer=0.090, missing_rate=0.0, wrong_rate=0.0, extra_rate=0.0),
             han_only=dict(cer=0.010), must_pass=True)
    v, reasons, fail = qg.judge_content(m)
    assert v == 'REJECT' and 'content_over_manual' in reasons and fail


def test_judge_content_reject_must_pass():
    m = dict(with_punct=dict(cer=0.010, missing_rate=0.0, wrong_rate=0.0, extra_rate=0.0),
             han_only=dict(cer=0.008), must_pass=False)
    v, reasons, _ = qg.judge_content(m)
    assert v == 'REJECT' and 'must_pass_regression' in reasons


def test_judge_content_must_pass_not_applicable():
    m = dict(with_punct=dict(cer=0.010, missing_rate=0.0, wrong_rate=0.0, extra_rate=0.0),
             han_only=dict(cer=0.008), must_pass=False, must_pass_applicable=False)
    v, _, _ = qg.judge_content(m)
    assert v == 'AUTO'


def test_combine_verify_fail_reject():
    v, reasons = qg.combine(False, 'AUTO', 'AUTO')
    assert v == 'REJECT' and 'verify_fail' in reasons


def test_combine_auto_pass():
    v, reasons = qg.combine(True, 'AUTO', 'AUTO')
    assert v == 'AUTO_PASS' and reasons == []


def test_combine_manual_only():
    v, reasons = qg.combine(True, 'MANUAL', 'AUTO')
    assert v == 'MANUAL_ONLY' and 'manual_tier' in reasons


def test_combine_component_reject():
    v, reasons = qg.combine(True, 'REJECT', 'AUTO', p_reasons=['punct_regression'])
    assert v == 'REJECT' and 'punct_regression' in reasons


# ---- t148: expect-low / data_missing / 顶层字段 ----
def test_resolve_expect_low_wz7():
    pages, path = qg.resolve_expect_low('wz7')
    assert pages and path and path.endswith('_expect_low.txt')
    assert '5' in pages.split(',')


def test_judge_punct_data_missing_manual():
    v, reasons, fail = qg.judge_punct(_punct('comma', 0.50, 0.40), data_missing=True)
    assert v == 'MANUAL' and 'data_missing' in reasons


def test_detect_data_missing(tmp_path=None):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, 'o.pdf'); d = fitz.open(); pg = d.new_page(width=400, height=200)
        pg.insert_text((10, 50), '甲乙丙丁戊己庚辛', fontname='china-s', fontsize=12); d.save(pdf)
        gp = os.path.join(tmp, 'g.json')
        json.dump([{'book': 'wz7', 'page': 1, 'axis': 'vertical',
                    'text': '甲乙，丙丁，戊己，庚辛。'}], open(gp, 'w', encoding='utf-8'), ensure_ascii=False)
        r = qg.detect_data_missing(gp, pdf, 'wz7', {})
        assert r and r['missing'] is True and r['classification'] == 'data_missing'
        assert r['product_punct'] == 0 and r['gold_punct'] == 4


def test_main_top_level_fields(tmp_path=None):
    import subprocess, tempfile
    # 用真实 wz6 跑一次（较快）；检查 version/metrics/verdict/reasons/expect_low
    out = 'tmp_vert/gate/_test_gate_wz6.json'
    rc = subprocess.run(['/usr/bin/python3', 'src/tools/quality_gate.py', '--book', 'wz6',
                         '--pdf', 'output/wz6/wz6_vert_full.pdf',
                         '--coords', 'data/wz6/wz6_spotting_coords.json',
                         '--lines', 'data/wz6/wz6_spotting_lines.json',
                         '--gold', 'data/punct_eval/punct_gold_v1.json', '--out', out],
                        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')),
                        capture_output=True, text=True)
    assert rc.returncode == 0
    r = json.load(open(os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')), out), encoding='utf-8'))
    assert r['version'] == 'quality-gate-v1'
    assert r['verdict'] == r['gate']['verdict']
    assert isinstance(r['reasons'], list)
    assert 'verify' in r['metrics'] and 'punct' in r['metrics'] and 'content' in r['metrics']
    assert r['verdict'] == 'MANUAL_ONLY' and 'data_missing' in r['reasons']
    assert r['content']['metrics'].get('must_pass_status') == 'not_applicable'
    assert r['content']['must_pass_fail_items'] == []
    assert r['content']['over_limit_pages']
    assert r['content']['over_limit_pages'][0].get('char_pos') is not None
    assert r['punct']['pages_with_fn']
    assert r['punct']['pages_with_fn'][0].get('char_pos') is not None
    assert r['punct']['data_missing']['input_punct'] == r['punct']['data_missing']['product_punct']


# t150：输入侧判据 —— 输入有标点、产物缺 -> product_regression（不得判 data_missing）
def test_detect_product_regression():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, 'o.pdf'); d = fitz.open(); pg = d.new_page(width=400, height=200)
        pg.insert_text((10, 50), '甲乙丙丁戊己庚辛', fontname='china-s', fontsize=12); d.save(pdf)
        gp = os.path.join(tmp, 'g.json')
        json.dump([{'book': 'wz7', 'page': 1, 'axis': 'vertical',
                    'text': '甲乙，丙丁，戊己，庚辛。'}], open(gp, 'w', encoding='utf-8'), ensure_ascii=False)
        lines = {'0': ['甲乙，丙丁，戊己，庚辛。']}
        r = qg.detect_data_missing(gp, pdf, 'wz7', lines)
        assert r and r['missing'] is False and r['classification'] == 'product_regression'
        assert r['input_punct_ratio'] > 0.75 and r['product_punct_ratio'] == 0.0
