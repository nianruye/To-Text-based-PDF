#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""架构守卫（t215）：scan2pdf geom 交付必须走 fit_positional，不得直调 build_geom。"""
import os, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def _src(rel):
    return open(os.path.join(ROOT, rel), encoding='utf-8').read()


def test_scan2pdf_geom_uses_fit_positional():
    s = _src('src/tools/scan2pdf.py')
    m = re.search(r'def build_pdf\(.*?\n(?=def )', s, re.S)
    assert m, 'scan2pdf 缺 build_pdf'
    block = m.group(0)
    assert 'fit_positional.py' in block, 'geom 分支未走 fit_positional'
    assert 'build_geom.py' not in block, 'geom 分支不得直调 build_geom 交付'


def test_fit_positional_shim_exists():
    p = os.path.join(ROOT, 'src/calibration/fit_positional.py')
    assert os.path.exists(p), '缺 fit_positional 薄壳'
    s = open(p, encoding='utf-8').read()
    assert 'from fit_common import main' in s, 'fit_positional 未复用 fit_common.main'
    assert "main('build_geom')" in s, 'fit_positional 未声明 build_geom 两趟校准'
