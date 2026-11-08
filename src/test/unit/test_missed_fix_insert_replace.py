#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""battle19b：missing-fix 的 insert/replace 两类单测（wz7 小书守卫 + 实际插入/替换）。"""
import json, os, subprocess, sys, tempfile
import fitz

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
BUILD = os.path.join(ROOT, 'src/pipelines/build_vert.py')
LI = json.load(open(os.path.join(ROOT, 'data/wz6/wz6_spotting_lines.json'), encoding='utf-8'))
CO = json.load(open(os.path.join(ROOT, 'data/wz6/wz6_spotting_coords.json'), encoding='utf-8'))


def _fix_json(tmp, row_text, box_pt, mode):
    if mode == 'insert':
        items = [dict({'class': 'insert'}, **_item(row_text, box_pt, 'insert'))]
    else:
        items = [dict({'class': 'replace'}, **_item(row_text, box_pt, 'replace'))]
    p = os.path.join(tmp, 'fix.json')
    json.dump({'items': items}, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    return p


def _item(row_text, box_pt, mode):
    base = dict(page=1, col=box_pt, side='', source='test', confidence='high', text=row_text)
    if mode == 'insert':
        base.update(pos=0, ch='「')
    else:
        base.update(pos=1, current=row_text[1], new='換')
    return base


def _build(tmp, fixpath, min_pages=None):
    env = dict(os.environ, VERT_TMP=tmp, VERT_MISSED_FIX=fixpath)
    if min_pages is not None:
        env['VERT_MISSED_FIX_MIN_PAGES'] = str(min_pages)
    out = os.path.join(tmp, 'o.pdf')
    r = subprocess.run([sys.executable, BUILD, os.path.join(ROOT, 'data/wz6/wz6_spotting_lines.json'),
                        os.path.join(ROOT, 'data/wz6/wz6_spotting_coords.json'), out,
                        os.path.join(ROOT, 'source_pdf/wz6.pdf')],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout[-800:], r.stderr[-800:])
    return out


def _page_text(pdf):
    d = fitz.open(pdf)
    return ''.join(c for c in d[0].get_text() if not c.isspace())


def test_insert_and_replace_applied():
    k = '0'
    row = str(LI[k][0]); b = CO[k][0]
    xs = [q[0] / 2 for q in b]; ys = [q[1] / 2 for q in b]
    box = [min(xs), min(ys), max(xs), max(ys)]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = _build(tmp, _fix_json(tmp, row, box, 'insert'), 0)
        t = _page_text(pdf)
        assert ('「' + row[:3]) in t or ('﹁' + row[:3]) in t, t[:80]
        pdf2 = _build(tmp, _fix_json(tmp, row, box, 'replace'), 0)
        t2 = _page_text(pdf2)
        assert (row[:1] + '換' + row[2:4]) in t2, t2[:80]


def test_small_book_guard_skips_insert():
    k = '0'
    row = str(LI[k][0]); b = CO[k][0]
    xs = [q[0] / 2 for q in b]; ys = [q[1] / 2 for q in b]
    box = [min(xs), min(ys), max(xs), max(ys)]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = _build(tmp, _fix_json(tmp, row, box, 'insert'))   # 默认 1000 页阈值
        t = _page_text(pdf)
        assert ('「' + row[:3]) not in t and ('﹁' + row[:3]) not in t


def test_two_inserts_same_column_order():
    """同列两条 insert（pos 3 与 pos 0）：必须降序应用，结果 = 「ABC」…（不能错位）。"""
    k = '0'
    row = str(LI[k][0]); b = CO[k][0]
    xs = [q[0] / 2 for q in b]; ys = [q[1] / 2 for q in b]
    box = [min(xs), min(ys), max(xs), max(ys)]
    with tempfile.TemporaryDirectory() as tmp:
        items = [dict({'class': 'insert'}, page=1, col=box, pos=0, ch='「', text=row),
                 dict({'class': 'insert'}, page=1, col=box, pos=3, ch='」', text=row)]
        p = os.path.join(tmp, 'fix.json')
        json.dump({'items': items}, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
        pdf = _build(tmp, p, 0)
        t = _page_text(pdf)
        assert (('「' + row[:3] + '」' + row[3:5]) in t
                or ('﹁' + row[:3] + '﹂' + row[3:5]) in t), t[:80]


def test_insert_close_quote_gate():
    """battle23 M1：闭号族守卫 + 源墨闭号数闸门（产物局部已有闭号 -> 拒插）。"""
    k = '0'
    row = str(LI[k][0]); b = CO[k][0]
    xs = [q[0] / 2 for q in b]; ys = [q[1] / 2 for q in b]
    box = [min(xs), min(ys), max(xs), max(ys)]
    with tempfile.TemporaryDirectory() as tmp:
        # 源墨闭号数 0（= 不可能），产物局部闭号数 0 >= 0 -> 拒绝
        items = [dict({'class': 'insert'}, page=1, col=box, pos=0, ch='」', text=row, src_ink_quotes=0)]
        p = os.path.join(tmp, 'fix.json')
        json.dump({'items': items}, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
        pdf = _build(tmp, p, 0)
        t = _page_text(pdf)
        assert '﹂' not in t[:4] and '」' not in t[:4], t[:40]
        # 源墨闭号数 2 -> 产物 0 < 2 -> 允许
        items = [dict({'class': 'insert'}, page=1, col=box, pos=0, ch='」', text=row, src_ink_quotes=2)]
        json.dump({'items': items}, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
        pdf = _build(tmp, p, 0)
        t = _page_text(pdf)
        assert ('﹂' in t[:4] or '」' in t[:4]), t[:40]
