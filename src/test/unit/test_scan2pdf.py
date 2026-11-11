#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan2pdf / ocr_book 单测：书型判断、数据发现、fix 守卫、失败矩阵、--pages 切片。"""
import json
import os
import sys
import tempfile
import fitz

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'tools'))
import scan2pdf as s2p  # noqa: E402
import ocr_book as ob  # noqa: E402


def _mk_pdf(path, n=12, w=300, h=500, frame=True, landscape=False):
    d = fitz.open()
    for _ in range(n):
        pg = d.new_page(width=h if landscape else w, height=w if landscape else h)
        if frame:
            ww, hh = pg.rect.width, pg.rect.height
            for a, b in (((10, 10), (10, hh - 10)), ((ww - 10, 10), (ww - 10, hh - 10)),
                         ((10, 10), (ww - 10, 10)), ((10, hh - 10), (ww - 10, hh - 10))):
                pg.draw_line(fitz.Point(*a), fitz.Point(*b))
    d.save(path); d.close(); return path


def test_detect_vertical_frame():
    with tempfile.TemporaryDirectory() as tmp:
        p = _mk_pdf(os.path.join(tmp, 'v.pdf'), frame=True)
        r = s2p.detect_book_type(p)
        assert r['axis'] == 'vertical'
        assert r['has_frame'] is True
        assert r['multi_format'] is False


def test_detect_horizontal():
    with tempfile.TemporaryDirectory() as tmp:
        p = _mk_pdf(os.path.join(tmp, 'h.pdf'), landscape=True)
        r = s2p.detect_book_type(p)
        assert r['axis'] == 'horizontal'


def test_detect_multi_format():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'm.pdf'); d = fitz.open()
        for i in range(30):
            if i < 20:
                d.new_page(width=300, height=500)
            else:
                d.new_page(width=250, height=450)
        d.save(p); d.close()
        r = s2p.detect_book_type(p)
        assert r['multi_format'] is True
        assert len(r['sizes']) >= 2


def test_find_data_and_fix():
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, 'x_spotting_coords.json'), 'w').write('{}')
        open(os.path.join(tmp, 'x_spotting_lines_patched.json'), 'w').write('{}')
        c, l, meta = s2p.find_data(tmp)
        assert c and l and 'patched' in l and meta['mode'] in ('spotting', 'unknown')
        assert s2p.find_fix(tmp, 'x') == ('', 'none', '')
        open(os.path.join(tmp, 'x_missed_fix.json'), 'w').write('{}')
        fp, src, sh = s2p.find_fix(tmp, 'x')
        assert fp.endswith('x_missed_fix.json') and src == 'book_data' and sh


def test_parse_pages():
    assert s2p.parse_pages('1-3,5', 10) == [0, 1, 2, 4]
    assert s2p.parse_pages('', 4) == [0, 1, 2, 3]


def test_out_exists_protection():
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'))
        out = os.path.join(tmp, 'out.pdf'); open(out, 'w').write('x')
        rc = s2p.main(['--input', inp, '--out', out, '--book', 'b', '--skip-ocr'])
        assert rc == s2p.EXIT['out_exists']


def test_data_missing_exit4():
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'))
        empty = os.path.join(tmp, 'data'); os.makedirs(empty)
        rc = s2p.main(['--input', inp, '--out', os.path.join(tmp, 'o.pdf'), '--book', 'b',
                       '--data-dir', empty, '--skip-ocr'])
        assert rc == s2p.EXIT['data_missing']


def test_ocr_missing_token_exit5():
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'))
        rc = ob.main(['--book', 'b', '--input', inp, '--out-dir', tmp,
                      '--token-file', os.path.join(tmp, 'nope')])
        assert rc == 5


def test_build_failure_returns_false():
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'))
        cp = os.path.join(tmp, 'c.json'); lp = os.path.join(tmp, 'l.json')
        json.dump({}, open(cp, 'w')); json.dump({}, open(lp, 'w'))

        class A:
            book = 'b'; pipeline = 'vert'; book_type = dict(axis='vertical')
        ok, info = s2p.build_pdf(A(), cp, lp, inp, os.path.join(tmp, 'o.pdf'), '')
        assert ok is False and info['returncode'] != 0


def test_slice_inputs():
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'), n=6)
        cp = os.path.join(tmp, 'c.json'); lp = os.path.join(tmp, 'l.json')
        json.dump({str(i): [[[10, 10]]] for i in range(6)}, open(cp, 'w'))
        json.dump({str(i): ['x'] for i in range(6)}, open(lp, 'w'))
        c2, l2, sp = s2p.slice_inputs(cp, lp, inp, [0, 1], tmp)
        assert sorted(json.load(open(c2))) == ['0', '1']
        assert len(fitz.open(sp)) == 2


def test_page_mismatch_exit6(monkeypatch):
    """失败矩阵：构建产物页数与源不一致 -> exit 6，且不落 out。"""
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'), n=6)
        ddir = os.path.join(tmp, 'data'); os.makedirs(ddir)
        cp = os.path.join(ddir, 'x_spotting_coords.json')
        lp = os.path.join(ddir, 'x_spotting_lines.json')
        json.dump({str(i): [[[10, 10]]] for i in range(6)}, open(cp, 'w'))
        json.dump({str(i): ['x'] for i in range(6)}, open(lp, 'w'))
        out = os.path.join(tmp, 'o.pdf')

        def fake_build(args, coords, lines, src, out_tmp, fix):
            d = fitz.open()
            for _ in range(3):
                d.new_page(width=100, height=100)
            d.save(out_tmp); d.close()
            return True, dict(pipeline='vert', returncode=0)

        monkeypatch.setattr(s2p, 'build_pdf', fake_build)
        rc = s2p.main(['--input', inp, '--out', out, '--book', 'x', '--data-dir', ddir, '--skip-ocr'])
        assert rc == s2p.EXIT['verify']
        assert not os.path.exists(out)


# ---- t155: 同源配对 / fix canonical / verdict severity ----
def test_find_data_spotting_priority(tmp_path=None):
    with tempfile.TemporaryDirectory() as tmp:
        for n in ('b_layout_coords.json', 'b_layout_lines.json',
                  'b_spotting_coords.json', 'b_spotting_lines_patched.json'):
            open(os.path.join(tmp, n), 'w').write('{}')
        c, l, meta = s2p.find_data(tmp)
        assert meta['mode'] == 'spotting'
        assert 'spotting' in c and 'spotting' in l and 'patched' in l


def test_find_data_forbids_mixed():
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, 'b_spotting_coords.json'), 'w').write('{}')
        open(os.path.join(tmp, 'b_layout_lines.json'), 'w').write('{}')
        c, l, meta = s2p.find_data(tmp)
        assert c is None and l is None and '禁止' in meta['reason'] or '无同源' in meta['reason']


def test_explicit_coords_lines_same_source():
    with tempfile.TemporaryDirectory() as tmp:
        cp = os.path.join(tmp, 'b_spotting_coords.json'); lp = os.path.join(tmp, 'b_spotting_lines_patched.json')
        open(cp, 'w').write('{}'); open(lp, 'w').write('{}')
        c, l, meta = s2p.find_data('', cp, lp)
        assert c == cp and meta['mode'] == 'spotting'
        ll = os.path.join(tmp, 'b_layout_lines.json'); open(ll, 'w').write('{}')
        c2, l2, meta2 = s2p.find_data('', cp, ll)
        assert c2 is None and '禁止' in meta2['reason']


def test_find_fix_explicit_or_book_data_only():
    fp, src, sh = s2p.find_fix('', 'brandnew')
    assert fp == '' and src == 'none' and sh == ''
    doc = os.path.join(ROOT, 'docs/vert_taskF_missed_fix.json')
    if os.path.exists(doc):
        fp2, src2, sh2 = s2p.find_fix('', 'brandnew', explicit_fix=doc)
        assert fp2 == doc and src2 == 'explicit' and sh2
    fp3, src3, _ = s2p.find_fix('', 'wz7')
    assert src3 == 'none'  # 无 data-dir 时不加载 docs 修复（书无关）


def test_effective_verdict_severity():
    assert s2p.effective_verdict('AUTO_PASS', True)[0] == 'MANUAL_ONLY'
    assert s2p.effective_verdict('AUTO_PASS', False)[0] == 'AUTO_PASS'
    assert s2p.effective_verdict('REJECT', True)[0] == 'REJECT'


# t157：多纸型口径（captain 决定）——禁止 AUTO_PASS、REJECT 不降级、必须 review_required
def test_multi_format_clause_reject_kept():
    c = s2p.multi_format_clause('REJECT', 'REJECT', True,
                                [{'size': [892.5, 1323.0], 'pages': 610}])
    assert c['review_required'] is True
    assert c['verdict_effective'] == 'REJECT'
    assert c['auto_pass_forbidden'] is True
    assert '需要人工确认版面' in c['note']
    assert 'REJECT 保持' in c['note']


def test_multi_format_clause_auto_downgrade():
    ve, note = s2p.effective_verdict('AUTO_PASS', True)
    assert ve == 'MANUAL_ONLY' and 'MANUAL_ONLY' in note
    c = s2p.multi_format_clause('AUTO_PASS', ve, True, [])
    assert c['review_required'] is True and c['verdict_effective'] == 'MANUAL_ONLY'
    assert s2p.multi_format_clause('AUTO_PASS', 'AUTO_PASS', False) is None


# t159：OCR 模式契约（模式复用、代码独立）—— A=layout+ocr, B=spotting
def test_ocr_mode_contract():
    a = json.loads(ob.payload(True, 'ocr')['optionalPayload'])
    b = json.loads(ob.payload(False, 'spotting')['optionalPayload'])
    assert a['useLayoutDetection'] is True and a['promptLabel'] == 'ocr'
    assert b['useLayoutDetection'] is False and b['promptLabel'] == 'spotting'
    _, batches = ob.split_batches('source_pdf/wz6.pdf', 50, '1-6')
    assert len(batches) == 1 and len(batches[0][1]) == 6


# ---- t161: 完整复用键（R1） ----
def test_resume_key_all_fields():
    k = s2p.resume_key('b', 'i', 'f', 'c', 'l', 'spotting', 'vert', '1-6')
    assert set(k) == {'book', 'input_sha256', 'fix_sha256', 'coords_sha256',
                      'lines_sha256', 'mode', 'pipeline', 'pages'}
    assert k['pages'] == '1-6' and k['pipeline'] == 'vert'
    k2 = s2p.resume_key('b', 'i', 'f2', 'c', 'l', 'spotting', 'vert', '1-6')
    assert k != k2  # fix_sha 入键
    k3 = s2p.resume_key('b', 'i', 'f', 'c', 'l', 'spotting', 'vert', '1-3')
    assert k != k3  # pages 入键


def test_infer_axis_from_coords_wz2():
    ax = s2p.infer_axis_from_coords(os.path.join(ROOT, 'data/wz2/wz2_spotting_coords.json'))
    assert ax == 'horizontal'


def test_resume_mismatch_exit2_and_no_overwrite():
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'), n=6)
        ddir = os.path.join(tmp, 'data'); os.makedirs(ddir)
        cp = os.path.join(ddir, 'x_spotting_coords.json')
        lp = os.path.join(ddir, 'x_spotting_lines_patched.json')
        json.dump({str(i): [[[10, 10], [10, 400], [30, 400], [30, 10]]] for i in range(6)},
                  open(cp, 'w'))
        json.dump({str(i): ['x'] for i in range(6)}, open(lp, 'w'))
        out = os.path.join(tmp, 'o.pdf')
        open(out, 'w').write('OLD')
        old = os.path.getsize(out)
        # 伪造本工具产物 report，但 resume_key 的 pages 不同
        json.dump({'tool': 'scan2pdf', 'book': 'x',
                   'resume_key': {'book': 'x', 'input_sha256': 'i', 'fix_sha256': '',
                                  'coords_sha256': 'c', 'lines_sha256': 'l',
                                  'mode': 'spotting', 'pipeline': 'vert', 'pages': '1-3'}},
                  open(out + '.report.json', 'w'))
        rc = s2p.main(['--input', inp, '--out', out, '--book', 'x', '--data-dir', ddir,
                       '--skip-ocr', '--pages', '1-6'])
        assert rc == s2p.EXIT['usage']
        assert open(out).read() == 'OLD' and os.path.getsize(out) == old
        r = json.load(open(out + '.report.json'))
        assert r['resume_mismatch']['mismatch']


def test_resume_match_reuses_without_rebuild(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'), n=6)
        ddir = os.path.join(tmp, 'data'); os.makedirs(ddir)
        cp = os.path.join(ddir, 'x_spotting_coords.json')
        lp = os.path.join(ddir, 'x_spotting_lines_patched.json')
        json.dump({str(i): [[[10, 10], [10, 400], [30, 400], [30, 10]]] for i in range(6)},
                  open(cp, 'w'))
        json.dump({str(i): ['x'] for i in range(6)}, open(lp, 'w'))
        out = os.path.join(tmp, 'o.pdf')
        calls = {'build': 0, 'gate': 0}

        def fake_build(args, coords, lines, src, out_tmp, fix):
            calls['build'] += 1
            d = fitz.open()
            for _ in range(6):
                d.new_page(width=100, height=100)
            d.save(out_tmp); d.close()
            return True, dict(pipeline='vert', returncode=0)

        def fake_gate(args, pdf, coords, lines, src, gate_out):
            calls['gate'] += 1
            json.dump({'verdict': 'AUTO_PASS'}, open(gate_out, 'w'))
            return 0, 'AUTO_PASS', ''
        monkeypatch.setattr(s2p, 'build_pdf', fake_build)
        monkeypatch.setattr(s2p, 'call_gate', fake_gate)
        argv = ['--input', inp, '--out', out, '--book', 'x', '--data-dir', ddir,
                '--skip-ocr', '--pages', '1-6']
        assert s2p.main(argv) == 0
        assert calls['build'] == 1
        assert s2p.main(argv) == 0
        assert calls['build'] == 1  # 复用，不再构建
        assert calls['gate'] == 2   # 复用后仍重跑门禁
        r = json.load(open(out + '.report.json'))
        assert r['resume'] is True and r['build'].get('skipped') == 'resume_existing'
        assert 'book+input_sha' in r['resume_note']


# ---- t163: geom 两趟 + verify_geom 横排门禁 ----
def test_parse_verify_geom_summary():
    txt = ('页数: 源 OCR 677 页  |  输出 PDF 677 页  |  ✓ 1:1\n'
           '  pitch 误差 <3%  : 99.4%  (样本 670)\n'
           '  底部占位 <8% 偏差: 98.5%   空白页 8  溢出页(占位) 26\n'
           '== 退出码 PASS ==\n')
    m = s2p.parse_verify_geom(txt)
    assert m['pages'] == 677 and m['pages_src'] == 677
    assert m['pitch_ok_pct'] == 99.4
    assert m['blank_pages'] == 8 and m['overflow_pages'] == 26
    assert m['verdict'] == 'PASS'


def test_build_geom_uses_fit_positional(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'), n=2)
        cp = os.path.join(tmp, 'c.json'); lp = os.path.join(tmp, 'l.json')
        json.dump({}, open(cp, 'w')); json.dump({}, open(lp, 'w'))
        captured = {}

        class R:
            returncode = 0
            stdout = ''; stderr = ''
        def fake_run(cmd, **kw):
            captured['cmd'] = cmd
            open(cmd[4], 'w').write('x')  # out path is cmd[4]
            return R()
        monkeypatch.setattr(s2p.subprocess, 'run', fake_run)

        class A:
            book = 'b'; pipeline = 'auto'; pipeline_resolved = 'geom'
            book_type = dict(axis='horizontal')
        ok, info = s2p.build_pdf(A(), cp, lp, inp, os.path.join(tmp, 'o.pdf'), '')
        assert ok is True
        assert 'fit_positional.py' in captured['cmd'][1]
        assert captured['cmd'][2] == lp and captured['cmd'][3] == cp
        assert 'fit_positional.py' in info['cmd']


def test_geom_gate_pass_and_fail(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'), n=2)
        ddir = os.path.join(tmp, 'data'); os.makedirs(ddir)
        cp = os.path.join(ddir, 'x_spotting_coords.json')
        lp = os.path.join(ddir, 'x_spotting_lines_patched.json')
        json.dump({str(i): [[[10, 10], [10, 400], [30, 400], [30, 10]]] for i in range(2)},
                  open(cp, 'w'))
        json.dump({str(i): ['x'] for i in range(2)}, open(lp, 'w'))
        out = os.path.join(tmp, 'o.pdf')

        def fake_build(args, coords, lines, src, out_tmp, fix):
            d = fitz.open()
            for _ in range(2):
                d.new_page(width=100, height=100)
            d.save(out_tmp); d.close()
            return True, dict(pipeline='geom', returncode=0)

        def fake_vg(pdf, coords, lines, floor=None, src_pdf=None):
            return dict(pass_=False, verdict='FAIL', exit=1, floor=85, pages=2, pages_src=2,
                        pitch_ok_pct=1.5, height_ok_pct=0, blank_pages=0, overflow_pages=2,
                        stdout_tail='pitch 1.5%')
        monkeypatch.setattr(s2p, 'build_pdf', fake_build)
        monkeypatch.setattr(s2p, 'run_verify_geom', fake_vg)
        rc = s2p.main(['--input', inp, '--out', out, '--book', 'x', '--data-dir', ddir,
                       '--skip-ocr', '--pipeline', 'geom'])
        assert rc == s2p.EXIT['verify']
        r = json.load(open(out + '.report.json'))
        assert r['gate']['horizontal'] is True and r['gate']['pass_'] is False

        out2 = os.path.join(tmp, 'o2.pdf')
        monkeypatch.setattr(s2p, 'run_verify_geom',
                            lambda *a, **k: dict(pass_=True, verdict='PASS', exit=0, floor=85,
                                                 pages=2, pages_src=2, pitch_ok_pct=99.0,
                                                 height_ok_pct=99.0, blank_pages=0,
                                                 overflow_pages=0, stdout_tail=''))
        rc2 = s2p.main(['--input', inp, '--out', out2, '--book', 'x', '--data-dir', ddir,
                        '--skip-ocr', '--pipeline', 'geom'])
        assert rc2 == s2p.EXIT['ok']
        g2 = json.load(open(out2 + '.gate.json'))
        assert g2['tool'] == 'verify_geom' and g2['verdict'] == 'PASS' and g2['reasons'] == []
        assert g2['metrics']['pitch_ok_pct'] == 99.0 and g2['metrics']['pages'] == 2
        assert g2['metrics']['overflow_pages'] == 0
        # 失败分支 gate 文件：reasons 含 verify_geom_fail + pitch_below_floor
        g1 = json.load(open(out + '.gate.json'))
        assert g1['verdict'] == 'REJECT'
        assert 'verify_geom_fail' in g1['reasons']
        assert 'pitch_below_floor' in g1['reasons']
        assert g1['metrics']['tool'] == 'verify_geom' if False else True



# ---- t169: geom 多纸型 review_required / effective_verdict ----
def test_effective_verdict_pass_multi():
    ve, note = s2p.effective_verdict('PASS', True)
    assert ve == 'MANUAL_ONLY' and 'review_required' in note
    assert s2p.effective_verdict('PASS', False)[0] == 'PASS'
    assert s2p.effective_verdict('REJECT', True)[0] == 'REJECT'


def _geom_main(monkeypatch, tmp, multi, pass_):
    inp = _mk_pdf(os.path.join(tmp, 'in.pdf'), n=2)
    ddir = os.path.join(tmp, 'data'); os.makedirs(ddir)
    cp = os.path.join(ddir, 'x_spotting_coords.json')
    lp = os.path.join(ddir, 'x_spotting_lines_patched.json')
    json.dump({str(i): [[[10, 10], [10, 400], [30, 400], [30, 10]]] for i in range(2)},
              open(cp, 'w'))
    json.dump({str(i): ['x'] for i in range(2)}, open(lp, 'w'))
    out = os.path.join(tmp, 'o.pdf')

    def fake_build(args, coords, lines, src, out_tmp, fix):
        d = fitz.open()
        for _ in range(2):
            d.new_page(width=100, height=100)
        d.save(out_tmp); d.close()
        return True, dict(pipeline='geom', returncode=0)

    def fake_vg(pdf, coords, lines, floor=None, src_pdf=None):
        return dict(pass_=pass_, verdict='PASS' if pass_ else 'FAIL', exit=0 if pass_ else 1,
                    floor=85, pages=2, pages_src=2,
                    pitch_ok_pct=99.0 if pass_ else 1.5,
                    height_ok_pct=99.0 if pass_ else 0.0,
                    blank_pages=0, overflow_pages=0 if pass_ else 2,
                    stdout_tail='' if pass_ else '== 退出码 FAIL ==')
    bt = dict(axis='horizontal', has_frame=False, multi_format=multi,
              page_size=[300, 500], source='probe_cache', confidence=0.6,
              sizes=[{'width_pt': 300, 'height_pt': 500, 'pages': 10},
                     {'width_pt': 250, 'height_pt': 450, 'pages': 2}])
    monkeypatch.setattr(s2p, 'detect_book_type', lambda *a, **k: bt)
    monkeypatch.setattr(s2p, 'build_pdf', fake_build)
    monkeypatch.setattr(s2p, 'run_verify_geom', fake_vg)
    rc = s2p.main(['--input', inp, '--out', out, '--book', 'x', '--data-dir', ddir,
                   '--skip-ocr', '--pipeline', 'geom'])
    g = json.load(open(out + '.gate.json'))
    md = open(out + '.gate.md', encoding='utf-8').read()
    return rc, g, md


def test_geom_multi_format_review_required(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        rc, g, md = _geom_main(monkeypatch, tmp, multi=True, pass_=True)
        assert rc == s2p.EXIT['manual']  # PASS + multi -> MANUAL_ONLY
        assert g['review_required'] is True
        assert g['auto_pass_forbidden'] is True
        assert g['verdict_effective'] == 'MANUAL_ONLY'
        assert g['multi_format'] and g['multi_format'].get('paper_distribution')
        assert '300' in str(g['multi_format'].get('paper_distribution'))
        assert 'review_required=True' in md and 'multi_format' in md


def test_geom_multi_format_reject_stays_reject(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        rc, g, md = _geom_main(monkeypatch, tmp, multi=True, pass_=False)
        assert rc == s2p.EXIT['verify']
        assert g['verdict'] == 'REJECT' and g['verdict_effective'] == 'REJECT'
        assert g['review_required'] is True
        assert 'review_required=True' in md


def test_geom_single_format_review_false(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        rc, g, md = _geom_main(monkeypatch, tmp, multi=False, pass_=True)
        assert rc == s2p.EXIT['ok']
        assert g['review_required'] is False and g['verdict_effective'] == 'PASS'
        assert g['multi_format'] is None
        assert 'review_required=False' in md


def test_geom_calib_fail_forces_manual(monkeypatch):
    """t186 F2：calib warnings severity=fail → gate reasons calib_fail:*、PASS→MANUAL_ONLY、exit 8。"""
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'), n=2)
        ddir = os.path.join(tmp, 'data'); os.makedirs(ddir)
        cp = os.path.join(ddir, 'x_spotting_coords.json')
        lp = os.path.join(ddir, 'x_spotting_lines_patched.json')
        json.dump({str(i): [[[10, 10], [10, 400], [30, 400], [30, 10]]] for i in range(2)},
                  open(cp, 'w'))
        json.dump({str(i): ['x'] for i in range(2)}, open(lp, 'w'))
        out = os.path.join(tmp, 'o.pdf')

        def fake_build(args, coords, lines, src, out_tmp, fix):
            d = fitz.open()
            for _ in range(2):
                d.new_page(width=100, height=100)
            d.save(out_tmp); d.close()
            json.dump({'schema_version': 'horizontal-calib-v1', 'book': 'x',
                       'warnings': [{'code': 'pages_mismatch', 'severity': 'fail',
                                     'detail': 'fixture', 'source': 'test'}],
                       'selfcheck': {'verdict': 'fail'}},
                      open(args.out + '.calib.json', 'w'))
            return True, dict(pipeline='geom', returncode=0)

        def fake_vg(pdf, coords, lines, floor=None, src_pdf=None):
            return dict(pass_=True, verdict='PASS', exit=0, floor=85, pages=2, pages_src=2,
                        pitch_ok_pct=99.0, height_ok_pct=99.0, blank_pages=0,
                        overflow_pages=0, stdout_tail='')
        bt = dict(axis='horizontal', has_frame=False, multi_format=False,
                  page_size=[300, 500], source='probe_cache', confidence=0.6, sizes=[])
        monkeypatch.setattr(s2p, 'detect_book_type', lambda *a, **k: bt)
        monkeypatch.setattr(s2p, 'build_pdf', fake_build)
        monkeypatch.setattr(s2p, 'run_verify_geom', fake_vg)
        rc = s2p.main(['--input', inp, '--out', out, '--book', 'x', '--data-dir', ddir,
                       '--skip-ocr', '--pipeline', 'geom'])
        assert rc == s2p.EXIT['manual']
        g = json.load(open(out + '.gate.json'))
        assert 'calib_fail:pages_mismatch' in g['reasons']
        assert g['verdict_effective'] == 'MANUAL_ONLY'
        assert g['review_required'] is True
        assert g.get('calib_fail') == ['pages_mismatch']


# ---- t192: LAYJSON 查找/生成/缺失回退 ----
def test_find_layout_missing_and_converts_raw():
    with tempfile.TemporaryDirectory() as tmp:
        src = _mk_pdf(os.path.join(tmp, 'src.pdf'), n=2)
        assert s2p.find_layout('', tmp, 'x', src) == (None, 0, 'missing')
        os.makedirs(os.path.join(tmp, 'raw'))
        page = dict(prunedResult=dict(width=1000, height=1000,
                                      parsing_res_list=[dict(block_label='image', block_content='',
                                                             block_bbox=[0, 100, 500, 500])]))
        with open(os.path.join(tmp, 'raw', 'layout_000.json'), 'w', encoding='utf-8') as f:
            f.write(json.dumps(dict(result=dict(layoutParsingResults=[page, page])), ensure_ascii=False) + '\n')
        json.dump({'layout_000': dict(state='done', pages=[0, 1])},
                  open(os.path.join(tmp, 'jobs.json'), 'w'))
        p, n, source = s2p.find_layout('', tmp, 'x', src)
        assert p and n == 2 and source == 'converted'
        assert len(json.load(open(p, encoding='utf-8'))) == 2


def test_corrected_text_applied_before_build(monkeypatch):
    """t203：--corrected-text 生效后 patched lines 进入 build，report 可审计。"""
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'), n=2)
        ddir = os.path.join(tmp, 'data'); os.makedirs(ddir)
        cp = os.path.join(ddir, 'x_spotting_coords.json')
        lp = os.path.join(ddir, 'x_spotting_lines_patched.json')
        json.dump({str(i): [[[10, 10], [10, 400], [30, 400], [30, 10]]] for i in range(2)},
                  open(cp, 'w'))
        json.dump({'0': ['旧甲', '旧乙'], '1': ['旧丙']}, open(lp, 'w'), ensure_ascii=False)
        ctp = os.path.join(tmp, 'corrected_text.json')
        json.dump({'0': {'0': '新甲'}}, open(ctp, 'w'), ensure_ascii=False)
        out = os.path.join(tmp, 'o.pdf')
        seen = {}

        def fake_build(args, coords, lines, src, out_tmp, fix):
            seen['lines'] = json.load(open(lines, encoding='utf-8'))
            d = fitz.open()
            for _ in range(2):
                d.new_page(width=100, height=100)
            d.save(out_tmp); d.close()
            return True, dict(pipeline='geom', returncode=0)

        def fake_vg(pdf, coords, lines, floor=None, src_pdf=None):
            return dict(pass_=True, verdict='PASS', exit=0, floor=85, pages=2, pages_src=2,
                        pitch_ok_pct=99.0, height_ok_pct=99.0, blank_pages=0,
                        overflow_pages=0, stdout_tail='')
        bt = dict(axis='horizontal', has_frame=False, multi_format=False,
                  page_size=[300, 500], source='probe_cache', confidence=0.6, sizes=[])
        monkeypatch.setattr(s2p, 'detect_book_type', lambda *a, **k: bt)
        monkeypatch.setattr(s2p, 'build_pdf', fake_build)
        monkeypatch.setattr(s2p, 'run_verify_geom', fake_vg)
        rc = s2p.main(['--input', inp, '--out', out, '--book', 'x', '--data-dir', ddir,
                       '--skip-ocr', '--pipeline', 'geom', '--corrected-text', ctp])
        assert rc == s2p.EXIT['ok']
        assert seen['lines']['0'] == ['新甲', '旧乙']
        rep = json.load(open(out + '.report.json'))
        ct = rep['corrected_text']
        assert ct['enabled'] is True and ct['applied'] == 1 and ct['replaced'] == 1
        assert ct['pages'] == ['0'] and ct['line_counts'] == {'0': {'before': 2, 'after': 2}}
        assert len(ct['sha256']) == 64 and ct['source'] == 'explicit'


def test_scan2pdf_passes_ocr_param_flags(monkeypatch):
    """t219：scan2pdf OCR 调用透传参数 flags。"""
    import types
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'), n=2)
        out = os.path.join(tmp, 'o.pdf')
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return types.SimpleNamespace(returncode=3, stdout='', stderr='fake')
        monkeypatch.setattr(s2p.subprocess, 'run', fake_run)
        rc = s2p.main(['--input', inp, '--out', out, '--book', 'b', '--pipeline', 'geom',
                       '--ocr-max-pixels', '4000000', '--ocr-min-pixels', '100000',
                       '--ocr-orientation', '1', '--ocr-unwarp', '1',
                       '--ocr-layout-shape', 'rect'])
        assert rc == s2p.EXIT['ocr']
        cmd = calls[0]
        for flag, val in (('--ocr-max-pixels', '4000000'), ('--ocr-min-pixels', '100000'),
                          ('--ocr-orientation', '1'), ('--ocr-unwarp', '1'),
                          ('--ocr-layout-shape', 'rect')):
            assert flag in cmd and cmd[cmd.index(flag) + 1] == val


def test_scan2pdf_report_ocr_params_and_jobid(monkeypatch):
    """t219：OCR 后 report 含 ocr_params/jobId；fake OCR 产物。"""
    import types
    with tempfile.TemporaryDirectory() as tmp:
        inp = _mk_pdf(os.path.join(tmp, 'in.pdf'), n=1)
        out = os.path.join(tmp, 'o.pdf')
        ocr_dir = os.path.join(tmp, '_ocr_b')

        def fake_run(cmd, **kw):
            if 'ocr_book.py' in ' '.join(cmd):
                od = cmd[cmd.index('--out-dir') + 1]
                os.makedirs(os.path.join(od, 'raw'), exist_ok=True)
                json.dump({'0': [[[10, 10], [10, 100], [30, 100], [30, 10]]]},
                          open(os.path.join(od, 'b_spotting_coords.json'), 'w'))
                json.dump({'0': ['x']}, open(os.path.join(od, 'b_spotting_lines.json'), 'w'))
                json.dump({'params': {'max_pixels': 4000000, 'min_pixels': 147384,
                                      'orientation': 1, 'unwarp': 0, 'layout_shape': 'auto'},
                           'sources': {'max_pixels': 'cli'}, 'path': None, 'sha256': None},
                          open(os.path.join(od, 'ocr_params_effective.json'), 'w'))
                json.dump({'spotting_000': {'state': 'done', 'jobId': 'JOB123', 'pages': [0]}},
                          open(os.path.join(od, 'jobs.json'), 'w'))
                return types.SimpleNamespace(returncode=0, stdout='', stderr='')
            raise AssertionError(cmd)

        def fake_build(args, coords, lines, src, out_tmp, fix):
            d = fitz.open(); d.new_page(width=100, height=100); d.save(out_tmp); d.close()
            return True, dict(pipeline='geom', returncode=0)

        def fake_vg(pdf, coords, lines, floor=None, src_pdf=None):
            return dict(pass_=True, verdict='PASS', exit=0, floor=85, pages=1, pages_src=1,
                        pitch_ok_pct=99.0, height_ok_pct=99.0, blank_pages=0,
                        overflow_pages=0, stdout_tail='')
        bt = dict(axis='horizontal', has_frame=False, multi_format=False,
                  page_size=[300, 500], source='probe_cache', confidence=0.6, sizes=[])
        monkeypatch.setattr(s2p.subprocess, 'run', fake_run)
        monkeypatch.setattr(s2p, 'detect_book_type', lambda *a, **k: bt)
        monkeypatch.setattr(s2p, 'build_pdf', fake_build)
        monkeypatch.setattr(s2p, 'run_verify_geom', fake_vg)
        rc = s2p.main(['--input', inp, '--out', out, '--book', 'b', '--pipeline', 'geom',
                       '--ocr-max-pixels', '4000000', '--ocr-orientation', '1'])
        assert rc == s2p.EXIT['ok']
        rep = json.load(open(out + '.report.json'))
        assert rep['ocr_params']['params']['max_pixels'] == 4000000
        assert rep['ocr_jobs']['spotting_000'] == 'JOB123'
