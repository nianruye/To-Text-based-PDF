#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VERT_MISSED_FIX_MIN_PAGES（小书保护阈值）测试（t56/battle12）。

覆盖：
- 默认 1000：小书（wz6 231 页）整类跳过 missing_char（不插入）；
- 显式 0：允许插入（小书也走插入分支）；
- 边界 = 页数：len(keys) >= 阈值 时插入（大书不受影响的分支同源）。
运行：/usr/bin/python3 -m pytest src/test/unit/test_missed_fix_min_pages.py -v
"""
import json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
LINES = os.path.join(ROOT, 'data/wz6/wz6_spotting_lines.json')
COORDS = os.path.join(ROOT, 'data/wz6/wz6_spotting_coords.json')
SRC = os.path.join(ROOT, 'source_pdf/wz6.pdf')
BUILD = os.path.join(ROOT, 'src/pipelines/build_vert.py')


def _book():
    co = json.load(open(COORDS, encoding='utf-8'))
    li = json.load(open(LINES, encoding='utf-8'))
    n_pages = len(li)
    for k in co:
        for b, t in zip(co[k], li.get(k) or []):
            if b and t:
                xs = [q[0] / 2.0 for q in b]; ys = [q[1] / 2.0 for q in b]
                return int(k) + 1, [min(xs), min(ys), max(xs), max(ys)], str(t), n_pages
    raise RuntimeError('no column')


def _run(tmpdir, tag, min_pages=None):
    pg, col, text, _ = _book()
    fix = os.path.join(tmpdir, 'fix_%s.json' % tag)
    json.dump({'items': [{'class': 'missing_char', 'page': pg,
                          'col': [round(x, 1) for x in col], 'pos': 1, 'ch': '測',
                          'text': text, 'source': 'test'}]},
              open(fix, 'w', encoding='utf-8'), ensure_ascii=False)
    out = os.path.join(tmpdir, 'out_%s.pdf' % tag)
    vt = os.path.join(tmpdir, 'vt_%s' % tag)
    env = dict(os.environ, VERT_TMP=vt, VERT_MISSED_FIX=fix)
    if min_pages is not None:
        env['VERT_MISSED_FIX_MIN_PAGES'] = str(min_pages)
    r = subprocess.run([sys.executable, BUILD, LINES, COORDS, out, SRC],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout[-800:], r.stderr[-800:])
    import fitz
    d = fitz.open(out)
    txt = ''.join(c for c in d[pg - 1].get_text() if not c.isspace())
    return r.stdout, txt


def test_default_skips_small_book(tmp_path):
    """默认阈值 1000：wz6 231 页 -> missing_char 整类跳过（灌入 0 处 / 跳过 1）。"""
    log, txt = _run(str(tmp_path), 'def')
    assert '灌入 0 处' in log, log[-500:]
    assert '跳过 1' in log, log[-500:]
    assert '測' not in txt


def test_zero_disables_guard(tmp_path):
    """显式 0：关闭小书保护 -> 插入生效（灌入 1 处，页面文本出现 測）。"""
    log, txt = _run(str(tmp_path), 'zero', min_pages=0)
    assert '灌入 1 处' in log, log[-500:]
    assert 'missing_char 1' in log, log[-500:]
    assert '測' in txt


def test_boundary_equal_pages(tmp_path):
    """边界 = 页数（231）：len(keys) >= 阈值 -> 插入（大书不受影响同源）。"""
    _, _, _, n_pages = _book()
    log, txt = _run(str(tmp_path), 'eq', min_pages=n_pages)
    assert '灌入 1 处' in log, log[-500:]
    assert '測' in txt
