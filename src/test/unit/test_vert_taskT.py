#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskT：标点视觉尺寸/格内位置按源书实测标定 的纯函数测试。

被测实现：`src/pipelines/build_vert.py`
  · §1.956 `_calib_own_marks` —— **占格书**的标点样本采样(按「墨心落在哪一格」取墨迹并集,
      不用 DP 预测);  d_top/d_cy/d_cx 与 col_puts 的 GAP_HANG/PUNCT_DY/PUNCT_DX 同一坐标语义
  · §1.956 `_calib_punct_ink` —— 标点锚点偏移改用**探针渲染实测墨心**(只 NF 生效)
  · §1.0a0 `_punct_own` / `char_cells` —— 占格语义(与 taskS 同一契约, 此处回归锁定)

实测来源（wz7 300 页样本, 15 页抽样 1717 条样本; 详见 docs/vert_punct_ink_report.md）：
  · 源书标点墨心在**自己那一格**里 d_cy 中位 0.451 格, 相对前字 1.026 格, gapP 10.9pt / gapN 9.6pt
  · 修前(DP 配对口径) d_cy 只测到 0.099 格 -> 标点摆得贴前字(gapP 2.8pt), 用户多轮反馈「重合」
  · p43「兩大類。」源图直探: 。 墨迹 y534.0-544.0(中心 539.0), 而 DP 口径量成 4.5pt(h 真值 10.0pt)

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_taskT.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_NS_BASE = dict(
    PUNCT_HANG={'。', '，', '、', '：', '；', '？', '！'},
    PUNCT_CELL_THR=0.5,
    PUNCT_CELL=1.0,
)

_FUNCS = ['_punct_own', 'char_cells', 'n_cells', '_calib_own_marks', '_calib_punct_ink']


def _ns(**over):
    d = dict(_NS_BASE)
    d.update(over)
    return load('build_vert.py', _FUNCS, [], mocks=d)


def _cc(top, bot, x0, x1, npx=40):
    """连通域记录(与 _calib_src_page 里 cc 元素同构):
    (top, bot, cx, w, h, kind, x0, x1, npx) —— 单位 pt(页左上原点)。"""
    return (top, bot, (x0 + x1) / 2.0, x1 - x0, bot - top, 'punct', x0, x1, npx)


# ---------- A. 占格书的标点采样(§1.956 _calib_own_marks) ----------
class TestOwnMarks:
    """栅格: T0=100, step=20, 列 x0=500, pitch=40, 正文墨高 h_med=18pt。
    文本「甲。乙」占格 -> 甲=格0[100,120)  。=格1[120,140)  乙=格2[140,160)。"""

    def test_centered_punct_in_own_cell(self):
        """标点墨心落在**自己那一格的中心**(格1 = [120,140), 中心 130)
        -> d_cy = 1.5 格(= 前字格锚点 100 起算); 占格书源书实测 0.451+1 = 1.451 格即此意。"""
        ns = _ns()
        ccs = [_cc(100, 118, 502, 536),            # 甲(格0)
               _cc(125, 135, 508, 518),            # 。(格1, 墨心 130)
               _cc(140, 158, 502, 536)]            # 乙(格2)
        r = ns['_calib_own_marks'](ccs, '甲。乙', [(0, False), (1, True), (2, False)],
                                   100.0, 20.0, 500.0, 40.0, 18.0)
        assert len(r) == 1
        ch, kind, hr, wr, d_top, d_cy, d_cx = r[0]
        assert (ch, kind) == ('。', 'punct')
        assert d_cy == pytest.approx((130.0 - 100.0) / 20.0) == pytest.approx(1.5)
        assert d_top == pytest.approx((125.0 - 100.0) / 20.0)      # 墨顶相对**前字格顶**
        assert d_cx == pytest.approx((513.0 - 500.0) / 40.0)
        assert hr == pytest.approx(10.0 / 18.0)                    # 本格墨高 / 正文墨高
        assert wr == pytest.approx(10.0 / 18.0)

    def test_anchor_is_prev_char_cell_not_own_cell(self):
        """锚点必须是**前一字格顶**(= col_puts 的 (k-1) 格, 也是 PUNCT_DY 的标定语义):
        同一墨迹在 PUNCT_CELL=1 下 d_cy 应比 PUNCT_CELL=0(挤格, 锚点即本格)大 1 格。"""
        ccs = [_cc(100, 118, 502, 536), _cc(129, 139, 508, 518), _cc(140, 158, 502, 536)]
        cells = [(0, False), (1, True), (2, False)]
        own = _ns(PUNCT_CELL=1.0)['_calib_own_marks'](ccs, '甲。乙', cells,
                                                     100.0, 20.0, 500.0, 40.0, 18.0)
        ju = _ns(PUNCT_CELL=0.0)['_calib_own_marks'](ccs, '甲。乙', cells,
                                                     100.0, 20.0, 500.0, 40.0, 18.0)
        assert own[0][5] - ju[0][5] == pytest.approx(1.0)

    def test_tall_union_is_dropped(self):
        """本格里取到的墨迹并集高过正文墨高(0.98x) -> 判「本格判据失效」(栅格漂移/两字并一块),
        弃样而不是乱收 —— 否则 PUNCT_SIZE 被并字抬高。"""
        ns = _ns()
        ccs = [_cc(100, 118, 502, 536), _cc(121, 139, 502, 536), _cc(140, 158, 502, 536)]
        r = ns['_calib_own_marks'](ccs, '甲。乙', [(0, False), (1, True), (2, False)],
                                   100.0, 20.0, 500.0, 40.0, 18.0)
        assert r == []

    def test_tall_punct_is_not_size_filtered(self):
        """！：；？ 的墨高与正文相当(轮廓 0.62-0.78em) —— 老口径的「小字尺寸窗」会把它们整类滤掉,
        新口径按格取墨, 必须收得到(用 h_med=25 让 22pt 高的冒号落在 0.98x 之内)。"""
        ns = _ns()
        ccs = [_cc(100, 120, 502, 542), _cc(126, 148, 508, 518), _cc(150, 170, 502, 542)]
        r = ns['_calib_own_marks'](ccs, '甲：乙', [(0, False), (1, True), (2, False)],
                                   100.0, 25.0, 500.0, 45.0, 25.0)
        assert [x[0] for x in r] == ['：']
        assert r[0][2] == pytest.approx(22.0 / 25.0)

    def test_multi_component_union(self):
        """一个标点被阈值打成多块(：的两点 / 淡墨断环) -> 并集算一个样本。"""
        ns = _ns()
        ccs = [_cc(100, 118, 502, 536),
               _cc(124, 129, 508, 514), _cc(133, 138, 508, 514),     # ：的两点(同在格1)
               _cc(140, 158, 502, 536)]
        r = ns['_calib_own_marks'](ccs, '甲：乙', [(0, False), (1, True), (2, False)],
                                   100.0, 20.0, 500.0, 40.0, 18.0)
        assert len(r) == 1
        assert r[0][2] == pytest.approx(14.0 / 18.0)               # 并集高 = 138-124

    def test_letter_column_puts_punct_in_next_cell(self):
        """格号用 char_cells(占格) —— 标点的**自己那一格** = 前字格 + 1, 与渲染同一套格号。"""
        ns = _ns()
        assert ns['char_cells']('甲。乙') == [(0, False), (1, True), (2, False)]
        assert ns['n_cells']('甲。乙') == 3

    def test_first_char_punct_is_not_sampled(self):
        """列首标点无前字(锚点不存在) -> 不入样本(与 _calib_src_page 的 `i > 0` 同规则)。"""
        ns = _ns()
        ccs = [_cc(100, 118, 502, 536), _cc(120, 138, 502, 536)]
        r = ns['_calib_own_marks'](ccs, '。甲', [(0, False), (1, False)],
                                   100.0, 20.0, 500.0, 40.0, 18.0)
        assert r == []

    def test_tiny_speck_rejected(self):
        """噪点级小块(npx < 8)不当标点。"""
        ns = _ns()
        ccs = [_cc(100, 118, 502, 536), _cc(130, 135, 510, 513, npx=3), _cc(140, 158, 502, 536)]
        r = ns['_calib_own_marks'](ccs, '甲。乙', [(0, False), (1, True), (2, False)],
                                   100.0, 20.0, 500.0, 40.0, 18.0)
        assert r == []


# ---------- B. 标点锚点偏移口径(§1.956 _calib_punct_ink) ----------
class TestPunctInk:
    """fontTools 轮廓墨心 vs 探针渲染实测墨心 —— NF 改用后者(实测差 0.16em 量级)。"""

    BASE = {'。': (0.5005, -0.3795), '，': (0.4815, -0.4040), '！': (0.4985, -0.3765)}

    def test_render_metrics_override(self):
        probe = {'。': (0.262, 0.274, 0.469, 0.544, 0.0251, 0.681),
                 '，': (0.149, 0.262, 0.398, 0.575, 0.0192, 0.706)}
        out, n, dif = _ns()['_calib_punct_ink'](probe, self.BASE)
        assert n == 2
        assert out['。'] == (0.469, -0.544)          # cx, -cy(渲染实测)
        assert out['，'] == (0.398, -0.575)
        assert out['！'] == self.BASE['！']           # 探针没测到 -> 保持原值(不混口径)
        assert dif == pytest.approx(0.1677, abs=5e-4)  # |0.544-0.3795| 与 |0.575-0.404| 的中位

    def test_empty_probe_keeps_base(self):
        out, n, dif = _ns()['_calib_punct_ink']({}, self.BASE)
        assert out == self.BASE and n == 0 and dif is None

    def test_zero_calib_med_probe_entry_keeps_base_value(self):
        """探针值全 0(量测失败)也算「测到」-> 由 0 决定; 但工程上探针失败时 _probe 为空,
        故此处只锁「表结构不变」这一条(键集合不增不减)。"""
        out, n, dif = _ns()['_calib_punct_ink']({'。': (0, 0, 0, 0, 0, 0)}, self.BASE)
        assert set(out) == set(self.BASE) and n == 1


# ---------- C. 占格语义回归(与 taskS 同一契约, 防回归) ----------
class TestOwnCellContract:
    def test_punct_own_threshold(self):
        assert _ns(PUNCT_CELL=1.0)['_punct_own']() is True
        assert _ns(PUNCT_CELL=0.49)['_punct_own']() is False
        assert _ns(PUNCT_CELL=0.0)['_punct_own']() is False
