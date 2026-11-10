#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fit_common pass1/pass2 VERIFY_MARK 与 verify_geom 无标记回退（t188）。

- pass1 render 必须有 VERIFY_MARK=1（measure_heights 按 GMPG 归组）；
- pass2 是交付产物，必须没有 VERIFY_MARK（继承 shell env 也要移除）；
- classic 路径共用 fit_common.main，同样 pass1=1/pass2=0；
- 不含 GMPG 的 PDF 走 verify_geom「按序号 1:1」回退（真 PDF fixture，不依赖源书）。
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import fitz
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIT_COMMON = ROOT / 'src' / 'calibration' / 'fit_common.py'


def _load_fc():
    old = sys.argv
    sys.argv = ['fit_common.py', 'SL', 'CO', 'OUT']
    try:
        spec = importlib.util.spec_from_file_location('fit_common_mark_under_test', FIT_COMMON)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.argv = old
    return mod


@pytest.fixture(scope='module')
def fc():
    return _load_fc()


def _fake_run(seen, out_path):
    def run(cmd, env=None, capture_output=True, text=True):
        seen.append(dict(env or {}))
        Path(cmd[4]).write_bytes(b'')       # cmd = [python, build, SL, CO, out]
        return subprocess.CompletedProcess(cmd, 0, '', '')
    return run


def test_render_verify_mark_env(fc, monkeypatch, tmp_path):
    """pass1 有 VERIFY_MARK；pass2 即使 shell 有也必须被移除。"""
    monkeypatch.setattr(fc, 'SRC', '')
    monkeypatch.setenv('VERIFY_MARK', '1')
    seen = []
    monkeypatch.setattr(fc.subprocess, 'run', _fake_run(seen, tmp_path / 'out.pdf'))
    out = str(tmp_path / 'pass.pdf')

    fc.render(out, est_log=str(tmp_path / 'est.json'), verify_mark=True)
    assert seen[-1].get('VERIFY_MARK') == '1'

    fc.render(out, ratio_table=str(tmp_path / 'ratio.json'), verify_mark=False)
    assert 'VERIFY_MARK' not in seen[-1], 'pass2 继承了 VERIFY_MARK（GMPG 会泄漏）'


@pytest.mark.parametrize('build_name', ['build_geom', 'build_classic'])
def test_main_marks_only_pass1(fc, monkeypatch, tmp_path, build_name):
    """两趟共享 main：pass1 verify_mark=True、pass2=False（classic 同源）。"""
    marks = []
    monkeypatch.setattr(fc, 'OUT', str(tmp_path / 'out.pdf'))

    def fake_render(out_pdf, est_log=None, ratio_table=None, fill=None, build_name='build_geom', verify_mark=True):
        marks.append(verify_mark)
        if est_log:
            Path(est_log).write_text(json.dumps({'0': 100.0}), encoding='utf-8')
        else:
            assert ratio_table and os.path.exists(ratio_table)
            Path(out_pdf).write_text('', encoding='utf-8')

    monkeypatch.setattr(fc, 'render', fake_render)
    monkeypatch.setattr(fc, 'measure_heights', lambda pdf: {})
    fc.main(build_name)
    assert marks == [True, False], f'{build_name} 两趟 verify_mark 必须 [True, False]: {marks}'


def test_verify_geom_no_mark_falls_back_to_1to1(tmp_path):
    """交付 PDF 无 GMPG 时，verify_geom 走按序号 1:1 回退并 PASS。"""
    pdf = tmp_path / 'no_mark.pdf'
    doc = fitz.open()
    pg = doc.new_page(width=300, height=400)
    for i, text in enumerate(('第一行', '第二行', '第三行')):
        pg.insert_text((50, 100 + i * 24), text, fontsize=10)
    doc.save(str(pdf)); doc.close()

    coords = {'0': [
        [[50, 180], [250, 180], [250, 205], [50, 205]],
        [[50, 228], [250, 228], [250, 253], [50, 253]],
        [[50, 276], [250, 276], [250, 301], [50, 301]],
    ]}
    lines = {'0': ['第一行', '第二行', '第三行']}
    cp = tmp_path / 'coords.json'; lp = tmp_path / 'lines.json'
    cp.write_text(json.dumps(coords, ensure_ascii=False), encoding='utf-8')
    lp.write_text(json.dumps(lines, ensure_ascii=False), encoding='utf-8')
    r = subprocess.run(
        [sys.executable, str(ROOT / 'src/test/verify_geom.py'), str(pdf), str(cp), str(lp),
         '--dpi', '200'],
        capture_output=True, text=True, cwd=str(ROOT), timeout=60)
    out = r.stdout + r.stderr
    assert 'GMPG' not in pdf.read_bytes().decode('latin-1', errors='ignore')
    assert '按序号 1:1' in out, out
    assert r.returncode == 0, out
