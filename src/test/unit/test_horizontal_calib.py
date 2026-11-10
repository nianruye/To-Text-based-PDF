#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""横排标定审计单测（HORIZONTAL_CALIB.md v1）。"""
import json, os, sys, tempfile
import fitz

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'utils'))
import geometry as geo


def _mk_src(path, n=2, w=300, h=600):
    d = fitz.open()
    for _ in range(n):
        d.new_page(width=w, height=h)
    d.save(path); d.close(); return path


def _synthetic(n=2):
    sl, co = {}, {}
    for i in range(n):
        sl[str(i)] = ['第一行文字足够长用于满行统计', '第二行文字同样足够长用于统计', '第三行文字也足够长用于统计']
        co[str(i)] = [[[20, 20], [260, 20], [260, 36], [20, 36]],
                      [[20, 44], [260, 44], [260, 60], [20, 60]],
                      [[20, 68], [260, 68], [260, 84], [20, 84]]]
    return sl, co


def test_calib_schema_and_values():
    with tempfile.TemporaryDirectory() as tmp:
        src = _mk_src(os.path.join(tmp, 'src.pdf'), 2, 300, 600)
        sl, co = _synthetic(2)
        g = geo.calibrate(sl, co, 200, src_pdf=src)
        doc = geo.build_calib_doc(sl, co, g, src, 'testbook')
        for k in ('schema_version', 'book', 'src_pdf', 'sha256', 'pages', 'dpi', 'page_size',
                  'cw', 'measure', 'font', 'baseline', 'margin_pt', 'font_sm_pt', 'h_body_px',
                  'toc_params', 'coverage', 'source_of_page_size', 'warnings', 'selfcheck', 'env'):
            assert k in doc, k
        assert doc['book'] == 'testbook' and doc['pages'] == 2
        assert doc['dpi']['value'] > 0 and doc['font']['pt'] > 0
        assert doc['source_of_page_size'] in ('coords', 'src_pdf', 'fallback', 'coords_no_src')
        assert doc['selfcheck']['pages_1to1'] is True
        assert isinstance(doc['warnings'], list)


def test_selfcheck_warn_branches():
    with tempfile.TemporaryDirectory() as tmp:
        src = _mk_src(os.path.join(tmp, 'src.pdf'), 2, 300, 600)
        sl, co = _synthetic(2)
        g = geo.calibrate(sl, co, 200, src_pdf=src)
        doc = geo.build_calib_doc(sl, co, g, src, 'x')
        g2 = dict(g)
        g2.update(dpi_residual=10.0, FONT=30.0, BASELINE=70.0, coverage_x=1.3,
                  coverage_y=1.3, coverage_degraded=True, MEASURE=10, PAGE_W=300,
                  MARGIN=200, cw=3, pitch_sample_n=2, full_lines=1,
                  pitch_median_pt=10.0)
        sc, ws = geo.calib_selfcheck(doc, g2, sl, co)
        codes = {w['code'] for w in ws}
        for c in ('dpi_residual_large', 'font_out_of_range', 'baseline_font_ratio_out',
                  'coverage_degraded_check' if False else 'page_size_overcoverage',
                  'page_size_coverage_low', 'measure_out_of_range', 'margin_out_of_range',
                  'cw_out_of_range', 'pitch_low_sample', 'full_sample_low'):
            assert c in codes, (c, codes)
        assert sc['verdict'] == 'warn'


def test_selfcheck_pages_mismatch_fail():
    with tempfile.TemporaryDirectory() as tmp:
        src = _mk_src(os.path.join(tmp, 'src.pdf'), 2, 300, 600)
        sl, co = _synthetic(2)
        g = geo.calibrate(sl, co, 200, src_pdf=src)
        doc = geo.build_calib_doc(sl, co, g, src, 'x')
        sl2 = dict(sl); sl2['2'] = ['多出来的一页']
        sc, ws = geo.calib_selfcheck(doc, g, sl2, co)
        assert any(w['code'] == 'pages_mismatch' and w['severity'] == 'fail' for w in ws)
        assert sc['verdict'] == 'fail'


def test_write_calib_json_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        src = _mk_src(os.path.join(tmp, 'src.pdf'), 2, 300, 600)
        sl, co = _synthetic(2)
        g = geo.calibrate(sl, co, 200, src_pdf=src)
        doc = geo.build_calib_doc(sl, co, g, src, 'x')
        p = os.path.join(tmp, 'x.calib.json')
        geo.write_calib(p, doc)
        got = json.load(open(p, encoding='utf-8'))
        assert got['schema_version'] == 'horizontal-calib-v1'
        assert got['sha256'] and len(got['sha256']) == 64


def test_build_geom_font_scale_out_of_range_not_blocked():
    """E2E fixture：FONT_SCALE 强制字号越界 → build 不阻断，calib 报警，render 回填。"""
    import subprocess
    with tempfile.TemporaryDirectory() as tmp:
        src = _mk_src(os.path.join(tmp, 'src.pdf'), 2, 300, 600)
        sl, co = _synthetic(2)
        lp = os.path.join(tmp, 'lines.json'); cp = os.path.join(tmp, 'coords.json')
        json.dump(sl, open(lp, 'w', encoding='utf-8'), ensure_ascii=False)
        json.dump(co, open(cp, 'w', encoding='utf-8'), ensure_ascii=False)
        out = os.path.join(tmp, 'o.pdf'); calib = out + '.calib.json'
        env = dict(os.environ, FONT_SCALE='3', CALIB_OUT=calib, CALIB_BOOK='fixture')
        p = subprocess.run(['/usr/bin/python3', os.path.join(ROOT, 'src/pipelines/build_geom.py'),
                            lp, cp, out, src], cwd=ROOT, env=env, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr[-800:]
        assert os.path.exists(out) and os.path.exists(calib)
        d = json.load(open(calib, encoding='utf-8'))
        codes = [w['code'] for w in d['warnings']]
        assert 'font_out_of_range' in codes, codes
        assert d['font']['scale'] == 3.0
        assert d['render']['page_pt']['width_pt'] and d['render']['font_pt']
        assert d['render']['unit'] == 'bp'


def test_toc_selfcheck_low_sample_and_range():
    with tempfile.TemporaryDirectory() as tmp:
        src = _mk_src(os.path.join(tmp, 'src.pdf'), 2, 300, 600)
        sl, co = _synthetic(2)
        g = geo.calibrate(sl, co, 200, src_pdf=src)
        doc = geo.build_calib_doc(sl, co, g, src, 'x')
        doc['coverage']['toc_samples'] = 1
        doc['toc_params'] = {'font_line': 20.0, 'foot_x': [0.9, 0.2],
                             'title_max': 5, 'toc_pages': ['0'], 'source': 'geom_toc_cal'}
        sc, ws = geo.calib_selfcheck(doc, g, sl, co)
        codes = {w['code'] for w in ws}
        assert 'toc_low_sample' in codes
        assert 'toc_foot_x_out' in codes
        assert 'toc_title_max_out' in codes
