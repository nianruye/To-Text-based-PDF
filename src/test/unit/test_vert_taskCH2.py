#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskCH2：目录页网格行不得被标题/署名路径认领 的纯函数测试。

被测实现：`src/pipelines/build_vert.py`
  · §1.95x `_toc_grid_layers` —— 原始 OCR 行按 x 心归带后, 查询 x 心所在带的层数
  · §1.95x `nf_toc_shape`     —— 目录页形态判据（列内 >=2 层 + 首层短 + 其余层短）
用 _loader 从脚本里 ast 提取纯函数（不 import fitz / 不跑 upLaTeX）。

实测来源（wz7 源页 48）：
  16 个回 x 一个 x 带、每个带 3 层（回次 5 字 / 回目上句 8 字 / 回目下句 8 字）；
  列距 38.79pt；「玳安嬉遊蝴蝶巷」与「第五十回」「琴童潛聽燕鶯歡」同带（xc 583.7/584.6/584.6）。
  真标题（p45「金瓶梅詞話總目錄」/ p561「詞話第二冊目錄」）各自独立成带（组内 1 行）。

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_taskCH2.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_FUNCS = ['nf_toc_shape', '_toc_seglen', '_toc_grid_layers']
_NS = dict(
    NF_TOC_COL_TOL=0.30, NF_TOC_TOP_MAX=6, NF_TOC_REST_MAX=20.0,
    NF_TOC_MINCOL=6, NF_TOC_TOP_TOL=0.03,
)


def _ns(**over):
    d = dict(_NS)
    d.update(over)
    return load('build_vert.py', _FUNCS, [], mocks=d)


def _row(cx_pt, y0_pt, y1_pt, text):
    """pt 入参 -> px 行(tuple 与 col_stats 同口径: x0,x1,y0,y1,text; px = pt*2)。"""
    return ((cx_pt - 1.0) * 2, (cx_pt + 1.0) * 2, y0_pt * 2, y1_pt * 2, text)


def _toc48like(ncol=16, pitch=39.5, x0=623.0):
    """p48 形态: 每列 3 层(回次 5 字 / 上句 8 字 / 下句 8 字), 三层同 x。"""
    rows = []
    for i in range(ncol):
        cx = x0 - pitch * i
        rows.append(_row(cx, 236.0, 379.0, '回次回次回'))        # 5 字
        rows.append(_row(cx, 408.0, 635.0, '上句上句上句上'))    # 8 字
        rows.append(_row(cx, 637.0, 894.0, '下句下句下句下'))    # 8 字
    return rows


# ---------- A. _toc_grid_layers：网格层数 ----------
class TestTocGridLayers:
    def test_three_layer_column(self):
        """p48: 同 x 带内 3 行 -> 3 层（回次 + 上句 + 下句）。"""
        ns = _ns()
        rows = _toc48like()
        assert ns['_toc_grid_layers'](rows, 623.0 * 2, 0.30 * 39.5 * 2) == 3

    def test_heading_is_single_layer(self):
        """真标题自成一带 -> 1 层（不是网格行, 标题路径可认领）。"""
        ns = _ns()
        rows = _toc48like() + [_row(697.0, 178.0, 377.0, '金瓶梅詞話總目錄')]
        assert ns['_toc_grid_layers'](rows, 697.0 * 2, 0.30 * 39.5 * 2) == 1

    def test_outside_any_band(self):
        ns = _ns()
        assert ns['_toc_grid_layers'](_toc48like(), 4000.0, 0.30 * 39.5 * 2) == 0
        assert ns['_toc_grid_layers']([], 100.0, 20.0) == 0

    def test_tolerance_boundary(self):
        """归带是**相邻心**链式: 差 11pt 同带; 再差 17pt(>tol 11.85) 另起一带。"""
        ns = _ns()
        tol = 0.30 * 39.5 * 2          # = 23.7 px = 11.85 pt
        rows = [_row(600.0, 100.0, 200.0, '甲'),
                _row(611.0, 210.0, 300.0, '乙'),      # 与上一心差 11pt -> 同带
                _row(628.0, 310.0, 400.0, '丙')]      # 与上一心差 17pt -> 另一带
        assert ns['_toc_grid_layers'](rows, 600.0 * 2, tol) == 2
        assert ns['_toc_grid_layers'](rows, 611.0 * 2, tol) == 2
        assert ns['_toc_grid_layers'](rows, 628.0 * 2, tol) == 1


# ---------- B. nf_toc_shape：目录形态判据 ----------
class TestNfTocShape:
    def test_p48_like_table_toc_hits(self):
        """p48: 16 列 x 3 层, 首层 5 字短于其余 8 字 -> 命中。"""
        ns = _ns()
        st = ns['nf_toc_shape'](_toc48like(), 39.5, 2886.0)
        assert st is not None
        assert st['shorttop'] == 16
        assert st['topspread'] == 0.0

    def test_poem_page_two_long_layers_not_toc(self):
        """诗行页: 每列 2 层但两层都是 11 字长行（p640/p969 形态）-> 不命中。"""
        ns = _ns()
        rows = []
        for i in range(18):
            cx = 800.0 - 40.0 * i
            rows.append(_row(cx, 200.0, 550.0, '詩' * 11))
            rows.append(_row(cx, 600.0, 950.0, '句' * 11))
        assert ns['nf_toc_shape'](rows, 40.0, 2886.0) is None

    def test_qupai_short_first_long_rest_not_toc(self):
        """曲牌页: 首层 3 字, 其余层 35 字正文（p1180 形态）-> 不命中。"""
        ns = _ns()
        rows = []
        for i in range(8):
            cx = 760.0 - 40.0 * i
            rows.append(_row(cx, 200.0, 260.0, '滾綉毬'))
            rows.append(_row(cx, 280.0, 1200.0, '正' * 35))
        assert ns['nf_toc_shape'](rows, 40.0, 2886.0) is None

    def test_mincol_threshold(self):
        """形态列 5 条 < 6 -> 不命中（判据不许被单页放宽）。"""
        ns = _ns()
        rows = _toc48like(ncol=5)
        assert ns['nf_toc_shape'](rows, 39.5, 2886.0) is None
        assert ns['nf_toc_shape'](_toc48like(ncol=6), 39.5, 2886.0) is not None

    def test_newline_row_counts_as_layers(self):
        """整列被 OCR 合成一个框（带 \\n）: 按层计, 仍可命中。"""
        ns = _ns()
        rows = []
        for i in range(8):
            cx = 760.0 - 40.0 * i
            rows.append(_row(cx, 200.0, 1200.0, '第一回\n回目上句\n回目下句'))
        st = ns['nf_toc_shape'](rows, 40.0, 2886.0)
        assert st is not None and st['shorttop'] == 8

    def test_topspread_guard(self):
        """首层 y 顶跨 > max(3% 页高, 40pt) -> 不命中（各回次不在同一水平带）。"""
        ns = _ns()
        rows = []
        for i in range(8):
            cx = 760.0 - 40.0 * i
            rows.append(_row(cx, 200.0 + 120.0 * i, 260.0 + 120.0 * i, '回次回次回'))
            rows.append(_row(cx, 700.0, 1100.0, '上句上句上句上'))
        assert ns['nf_toc_shape'](rows, 40.0, 2886.0) is None
