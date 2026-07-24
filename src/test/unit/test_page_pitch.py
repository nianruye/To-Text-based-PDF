#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_geom.page_pitch 单元测试。

约束：
- 纯 Python，不 import fitz/opencc，不调用 xelatex，不读文件系统。
- 通过 _loader.py 用 ast 提取 page_pitch 到隔离 namespace，绕开模块顶层副作用。

核心测试点（spec: spec/modern/wz3_pitch_optimization.md）：
- 方差大的页应返回有效 pitch，不应因 pstdev>0.4*m0 过滤回退 None。
  当前 build_geom.page_pitch L129 的方差过滤误杀 wz3 的 315 页 -> 预期 FAIL。

运行：
    /usr/bin/python3 -m pytest src/test/unit/test_page_pitch.py -v
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from _loader import load

import pytest

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _poly(yc, h=30, x0=100, x1=200):
    """构造 4 点 poly（h=行高，yc=中心 y）。page_pitch 用 min/max y 算 yc 与 h。"""
    return [[x0, yc - h / 2], [x1, yc - h / 2], [x1, yc + h / 2], [x0, yc + h / 2]]


@pytest.fixture(scope="module")
def geom_ns():
    """提取 page_pitch，注入其依赖的模块级全局（co/sl/page_px_h/DPI）。
    各测试用例改写 ns['co']/ns['sl'] 构造不同页数据。"""
    return load('build_geom.py', func_names={'page_pitch'},
                mocks={'co': {}, 'sl': {}, 'page_px_h': 2000.0, 'DPI': 200})


def _setup(geom_ns, ycs, page_px_h=2000.0, dpi=200, h=30):
    """填入一页 polys（ycs 为各 poly 中心 y），返回 page_pitch 函数。"""
    geom_ns['page_px_h'] = page_px_h
    geom_ns['DPI'] = dpi
    geom_ns['co'] = {'1': [_poly(yc, h) for yc in ycs]}
    geom_ns['sl'] = {'1': ['行%d' % i for i in range(len(ycs))]}
    return geom_ns['page_pitch']


def test_variance_large_returns_value(geom_ns):
    """方差大的页(pstdev>0.4*m0)应返回有效值,不回退 None。

    diffs=[40,60,100,140], median(m0)=80, pstdev≈38.7 > 0.4*80=32 -> 当前 L129
    方差过滤触发返回 None。删过滤后 pitch_px=median=80 -> pt=80*72/200=28.8 有效。
    此用例在改动前应 FAIL(返回 None),改动后 PASS。"""
    pp = _setup(geom_ns, [200, 240, 300, 400, 540])
    v = pp('1')
    assert v is not None, "方差大的页应返回有效 pitch,不应因方差过滤回退 None"
    assert 10.0 <= v <= 45.0


def test_normal_low_variance_returns_value(geom_ns):
    """正常低方差页返回有效值(确保改动不破坏正常路径)。"""
    pp = _setup(geom_ns, [200, 230, 260, 290, 320])  # diffs=[30,30,30,30] pstdev=0
    v = pp('1')
    assert v is not None, "正常页应返回有效 pitch"
    assert 10.0 <= v <= 45.0


def test_too_few_polys_returns_none(geom_ns):
    """有效 poly <4 返回 None(保留的过滤,改动不应影响)。"""
    pp = _setup(geom_ns, [200, 230, 260])  # 只 3 个
    assert pp('1') is None


def test_pt_out_of_range_returns_none(geom_ns):
    """pitch 换算 pt 超 [10,45] 返回 None(保留的过滤,改动不应影响)。

    diffs=[200,200,200,200] -> pt=200*72/200=72 >45 -> None。"""
    pp = _setup(geom_ns, [200, 400, 600, 800, 1000])
    assert pp('1') is None


def test_returns_value_matches_src_pitch(geom_ns):
    """page_pitch 返回值应接近源行距中位(口径对齐 verify src_pitch)。

    diffs=[40,60] 取中位 50px -> pt=50*72/200=18.0。验证返回值=18.0。"""
    pp = _setup(geom_ns, [200, 240, 300, 350])  # diffs=[40,60,50] median=50
    v = pp('1')
    assert v is not None
    assert abs(v - 18.0) < 0.1
