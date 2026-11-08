#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""content_eval v1.1 单测：两栏 CER、归一化、must-pass 64+54、diagnostic 不影响 verdict。"""
import json
import os
import sys
import tempfile
import fitz

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'tools'))
import content_eval as ce  # noqa: E402

COLBOX = [5, 5, 15, 200]


def _run(gold_text, pred_text, normalize='none', fix=None, t97=None, lines_text=None, pdf_text=None):
    with tempfile.TemporaryDirectory() as tmp:
        lines = {'0': [lines_text if lines_text is not None else pred_text]}
        coords = {'0': [[[10, 10], [30, 10], [30, 400], [10, 400]]]}
        lp = os.path.join(tmp, 'l.json'); cp = os.path.join(tmp, 'c.json'); gp = os.path.join(tmp, 'g.json')
        json.dump(lines, open(lp, 'w', encoding='utf-8'), ensure_ascii=False)
        json.dump(coords, open(cp, 'w', encoding='utf-8'))
        json.dump({'items': [{'page': 1, 'text': gold_text}]}, open(gp, 'w', encoding='utf-8'), ensure_ascii=False)
        pdf = os.path.join(tmp, 'o.pdf'); d = fitz.open()
        pg = d.new_page(width=200, height=400)
        try:
            pg.insert_text((10, 10), pdf_text if pdf_text is not None else pred_text, fontname='china-s', fontsize=8)
        except Exception:
            pg.insert_text((10, 10), pdf_text if pdf_text is not None else pred_text, fontsize=8)
        d.save(pdf)
        out = os.path.join(tmp, 'out.json'); csvp = os.path.join(tmp, 'out.csv')
        fp = os.path.join(tmp, 'fix.json')
        json.dump(fix if fix is not None else {'items': []}, open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
        tp = os.path.join(tmp, 't97.json')
        json.dump(t97 if t97 is not None else [], open(tp, 'w', encoding='utf-8'), ensure_ascii=False)
        args = ['--gold', gp, '--pdf', pdf, '--coords', cp, '--lines', lp, '--normalize', normalize,
                '--out', out, '--out-csv', csvp, '--regression-fix', fp, '--t97-meta', tp]
        assert ce.main(args) == 0
        size = os.path.getsize(csvp)
        return json.load(open(out, encoding='utf-8')), size


def _must_pass_fix(drop_one=False):
    mc = [dict(**{'class': 'missing_char'}, page=1, col=COLBOX, pos=i, ch='甲', shape={}, complete=True)
          for i in range(64)]
    ring = [dict(**{'class': 'ring'}, page=1, col=COLBOX, pos=64 + i, number=1, cp='U+2460',
                  ring_fix='battle4:t%d' % i) for i in range(54)]
    if drop_one:
        mc[0]['ch'] = '乙'  # 产物不含 -> fail
    return {'items': mc + ring}


# 1. 两栏：漏标点
def test_two_columns_missing_punct():
    r, _ = _run('甲，乙', '甲乙')
    assert r['content']['overall']['with_punct']['cer'] == round(1 / 3, 4)
    assert r['content']['overall']['han_only']['cer'] == 0.0


# 2. 错字
def test_wrong_char():
    r, _ = _run('甲丙', '甲丁')
    assert r['content']['overall']['with_punct']['wrong'] == 1
    assert r['content']['overall']['with_punct']['cer'] == 0.5


# 3. 多字
def test_extra_char():
    r, _ = _run('甲', '甲乙')
    assert r['content']['overall']['with_punct']['extra'] == 1
    assert r['content']['overall']['with_punct']['cer'] == 1.0


# 4. 异体归一对照
def test_variant_normalization():
    r, _ = _run('爲', '為', normalize='variant')
    assert r['content']['by_page'][0]['normalized_variant']['cer'] == 0.0


# 5. 繁简归一对照
def test_simp_normalization():
    r, _ = _run('為', '为', normalize='simp')
    assert r['content']['by_page'][0]['normalized_simp']['cer'] == 0.0


# 6. 存疑字
def test_doubt_excluded():
    # ? 同位屏蔽：gold '甲?乙' -> '甲乙'；pred 同位（index1）也删 -> '甲' -> CER 0.5
    r, _ = _run('甲?乙', '甲乙')
    assert r['content']['doubt_chars'] == 1
    assert r['content']['overall']['with_punct']['cer'] == 0.5


# 7. must-pass 64+54 全过
def test_must_pass_all_green():
    r, _ = _run('甲' * 64, '甲' * 64 + '①' * 54, fix=_must_pass_fix())
    reg = r['regression']
    assert reg['must_pass_items']['missing_char_confirmed']['total'] == 64
    assert reg['must_pass_items']['missing_char_confirmed']['passed'] == 64
    assert reg['must_pass_items']['battle4_ring']['total'] == 54
    assert reg['must_pass_items']['battle4_ring']['passed'] == 54
    assert reg['must_pass'] is True


# 8. must-pass 失败（缺一条）
def test_must_pass_failed():
    r, _ = _run('甲' * 64, '甲' * 64 + '①' * 54, fix=_must_pass_fix(drop_one=True))
    assert r['regression']['must_pass_items']['missing_char_confirmed']['passed'] == 63
    assert r['regression']['must_pass'] is False


# 9. diagnostic 不影响 verdict
def test_diagnostic_does_not_affect_verdict():
    t97 = [{'i': 1, 'page': 1, 'b': 'v', 'a': 'V'}]
    r, _ = _run('甲' * 64, '甲' * 64 + '①' * 54, fix=_must_pass_fix(), t97=t97)
    assert r['diagnostics']['typo_t97']['materialized_rate'] == 0.0
    assert r['diagnostics']['typo_t97']['status'] == 'unmaterialized'
    assert r['regression']['must_pass'] is True


# 10. CSV
def test_csv_written():
    r, size = _run('甲，乙', '甲乙')
    assert size > 0


# 11. 产物 PDF 有字、lines 无 -> must-pass 必须通过（防回退到 lines 口径）
def test_must_pass_uses_pdf_not_lines():
    r, _ = _run('甲' * 64, '', fix=_must_pass_fix(),
                lines_text='', pdf_text='甲' * 64 + '①' * 54)
    assert r['regression']['must_pass_items']['missing_char_confirmed']['passed'] == 64
    assert r['regression']['must_pass_items']['battle4_ring']['passed'] == 54
    assert r['regression']['must_pass'] is True


# 12. 不等长替换拆分：S=1, I=1, D=0
def test_unequal_replace_split():
    r, _ = _run('甲乙', '甲丙丁')
    st = r['content']['overall']['with_punct']
    assert st['substitutions'] == 1
    assert st['insertions'] == 1
    assert st['deletions'] == 0
    assert st['edit_distance'] == 2 and st['cer'] == 1.0


# 13. N=0：CER 记 null（不得记 0）
def test_n_zero_cer_null():
    r, _ = _run('?', '甲')
    st = r['content']['overall']['with_punct']
    assert st['gold_chars'] == 0
    assert st['cer'] is None
    assert r['content']['overall']['han_only']['cer'] is None


# 14. 产物 PDF 无文本 -> exit 3（不得回退 lines）
def test_empty_pdf_exit3():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        gp = os.path.join(tmp, 'g.json'); cp = os.path.join(tmp, 'c.json'); lp = os.path.join(tmp, 'l.json')
        json.dump({'items': [{'page': 1, 'text': '甲'}]}, open(gp, 'w', encoding='utf-8'), ensure_ascii=False)
        json.dump({'0': [[[10, 10], [30, 10], [30, 400], [10, 400]]]}, open(cp, 'w', encoding='utf-8'))
        json.dump({'0': ['甲']}, open(lp, 'w', encoding='utf-8'), ensure_ascii=False)
        pdf = os.path.join(tmp, 'o.pdf'); d = fitz.open(); d.new_page(width=200, height=400); d.save(pdf)
        out = os.path.join(tmp, 'o.json')
        args = ['--gold', gp, '--pdf', pdf, '--coords', cp, '--lines', lp, '--out', out,
                '--regression-fix', os.path.join(tmp, 'fix.json'), '--t97-meta', os.path.join(tmp, 't.json')]
        json.dump({'items': []}, open(os.path.join(tmp, 'fix.json'), 'w', encoding='utf-8'))
        json.dump([], open(os.path.join(tmp, 't.json'), 'w', encoding='utf-8'))
        assert ce.main(args) == 3


# 15. `?` 屏蔽：按 gold 中 ? 的序位删除 pred 同序位字符（断言屏蔽后字符串）
def test_doubt_mask_strings():
    assert ce._apply_doubt_mask('甲?乙', '甲乙丙') == ('甲乙', '甲丙', 1)
    assert ce._apply_doubt_mask('?甲', 'X甲') == ('甲', '甲', 1)
    assert ce._apply_doubt_mask('甲??乙', '甲乙丙丁') == ('甲乙', '甲丁', 2)
    assert ce._apply_doubt_mask('甲乙', '甲乙') == ('甲乙', '甲乙', 0)


# t148：竖排形归一诊断（N0 主列不变，诊断列 CER=0）
def test_vertical_form_diagnostic():
    r, _ = _run('「甲」', '﹁甲﹂')
    assert r['content']['overall']['with_punct']['cer'] > 0
    assert r['content']['by_page'][0]['normalized_vertical']['cer'] == 0.0
    assert r['content']['vertical_form']['with_punct']['cer'] == 0.0
