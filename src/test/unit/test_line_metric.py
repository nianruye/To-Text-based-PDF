#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t218：逻辑行口径单测（同 y 多 span 合一行；verify 输出 line_1to1）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'test'))
import verify_geom as vg


def _ln(y, h=20, x0=10, x1=100):
    return (y, y + h, y + h / 2.0, h, x0, x1)


def test_logical_lines_merge_same_y_spans():
    L = [_ln(100), _ln(100, x0=110, x1=180), _ln(140), _ln(180), _ln(220)]
    out = vg._logical_lines(L)
    assert len(out) == 4
    assert out[0][4] == 10 and out[0][5] == 180   # 同 y 两 span 的 x 并集
    assert [round(x[2], 1) for x in out] == [110.0, 150.0, 190.0, 230.0]


def test_logical_lines_do_not_merge_adjacent_pitch():
    # 行高 20，容差 10；相距 34 的正文行不应合并
    L = [_ln(100), _ln(134), _ln(168)]
    assert len(vg._logical_lines(L)) == 3


def test_logical_lines_empty():
    assert vg._logical_lines([]) == []


def test_content_extent_uses_shared_href_for_both_sides():
    # 同一 y 中心、源 poly 高 20 / 输出 bbox 高 52：extent 必须同口径
    src = (90, 110, 100, 20, 10, 100)
    out = (74, 126, 100, 52, 10, 100)
    assert vg._content_extent([src], 800, 600, 20) == (90, 110)
    assert vg._content_extent([out], 800, 600, 20) == (90, 110)
    # 不传 h_ref 时才回到各自 bbox（向后兼容/诊断用）
    assert vg._content_extent([out], 800, 600) == (74, 126)


def test_toc_like_detection():
    assert vg._toc_like(['目录', '1 第一编', '2 第二编', '3 第三编', '4 第四编', '5 第五编'])
    assert vg._toc_like(['1 忧患百姓忧患党', '2 俄国十月革命', '3 苏联解体', '4 戈尔巴乔夫', '5 结论'])
    assert not vg._toc_like(['1991年苏联的解体震惊世界', '义运动产生了深远影响', '尔巴乔夫与苏联解体'])


def test_s4_p2_rewrap_does_not_add_body_line():
    # p2 fixture：源 12 行；输出把一行在引号处拆成同 y 两 span，逻辑行仍 12
    src = [_ln(100 + i*34) for i in range(12)]
    out = [_ln(100 + i*34) for i in range(12)]
    out[4] = _ln(236, x0=10, x1=120)
    out.insert(5, _ln(236, x0=100, x1=220))
    tol = 10.0
    assert len(vg._logical_lines(out, tol)) == 12
    assert vg._body_lines(vg._logical_lines(out, tol), 800, 600)[5] == 12



def test_s4_p2_p5_output_fixture_if_built():
    # 集成 fixture：有 ghbq S4 产物时锁定 p2/p5 行粒度（无产物时跳过，保持 CI 可移植）
    import os
    import pytest
    import fitz
    pdf = 'output/ghbq_full/ghbq_s4final.pdf'
    if not os.path.exists(pdf):
        pytest.skip('ghbq S4 fixture not built')
    d = fitz.open(pdf)
    try:
        assert len(d[1].get_text().splitlines()) == 18   # p2 引号 rewrap 不再增加逻辑正文行
        assert len(d[4].get_text().splitlines()) == 34   # p5 CIP 34 条字段保粒度
    finally:
        d.close()
