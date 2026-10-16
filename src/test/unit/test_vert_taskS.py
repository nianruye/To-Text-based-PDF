#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskS：短列(低覆盖率短行)不得被静默丢弃 + 标点占格口径 的纯函数测试。

被测实现：`src/pipelines/build_vert.py`
  · §1.0a0 `PUNCT_CELL` / `n_cells` / `char_cells` —— 标点「占格 / 挤格」两口径的格号
  · §1.976 `_sb_band` / `nf_short_bands` / `_sb_pitch` / `_sb_ref_hm` / `_big_hm`
            —— 短列的 OCR 列框检出(覆盖率分母换成「本行墨迹窗」)
  · §1.98  `_trim_marks` —— 槽首/槽尾引號类小墨的剔除(否则列位与空隙锚点整体偏一格)
用 _loader 从脚本里 ast 提取纯函数（不 import fitz / 不跑 upLaTeX）。

实测来源（wz7 样本 idx54 = 源页 354）：
  · 「又曰：」列 x415.8-427.3 / 543.4-561.4，字 run 墨高 19.5pt，页参照 23.0pt，整页版心覆盖率仅 0.024
  · 诗引號「 9.5pt 小墨、紧贴首字上方 7pt；闭引號 」10.5pt

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_taskS.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_NS_BASE = dict(
    PUNCT_HANG={'。', '，', '、', '：', '；', '？', '！'},
    PUNCT_CELL_THR=0.5,
    NF_SB_COV=0.05, NF_SB_DEN=0.12, NF_SB_PADX=0.80, NF_SB_PADY=1.50,
    NF_SB_RATIO=(0.5, 1.35), NF_SB_OWN=True, NF_SLOT_DBG=False,
    NF_MIN_COL=2, NF_COV=0.12, LONG_H_FRAC=0.12, NF_ROW_FRAC=0.05, N_COL_FRAME=12,
    INK_RATIO=0.866, _calib_med=lambda v: sorted(v)[len(v) // 2],
)

_FUNCS = ['n_cells', 'char_cells', '_punct_own', '_big_hm', '_trim_marks',
          '_sb_band', '_sb_pitch', '_sb_ref_hm', '_band_stats', '_runs']


def _ns(**over):
    d = dict(_NS_BASE)
    d.update(over)
    return load('build_vert.py', _FUNCS, [], mocks=d)


# ---------- A. 标点占格口径(§1.0a0) ----------
class TestPunctCell:
    """挤格(PUNCT_CELL=0, wz6 口径) vs 占格(PUNCT_CELL=1, 实测 wz7)。"""

    def test_hang_does_not_advance(self):
        ns = _ns(PUNCT_CELL=0.0)
        assert ns['n_cells']('問：甲') == 2                    # ：挤在問的格内
        assert ns['char_cells']('問：甲') == [(0, False), (0, True), (1, False)]

    def test_own_advances_one_cell(self):
        ns = _ns(PUNCT_CELL=1.0)
        assert ns['n_cells']('問：甲') == 3
        assert ns['char_cells']('問：甲') == [(0, False), (1, True), (2, False)]

    def test_n_cells_matches_char_cells_both_models(self):
        """两口径下 n_cells 都必须等于 char_cells 的格数 —— 否则列长/步进算错。"""
        for pc in (0.0, 1.0):
            ns = _ns(PUNCT_CELL=pc)
            for t in ('問：甲', '甲。乙，丙', '甲', '又曰：'):
                assert ns['n_cells'](t) == max(c for c, _h in ns['char_cells'](t)) + 1

    def test_leading_punct_divergence_locked(self):
        """已知遗留(两口径同, 不在本任务范围): 首位标点被当普通字占一格, n_cells 不计 —— 锁现状。"""
        ns = _ns(PUNCT_CELL=0.0)
        assert ns['char_cells']('：甲') == [(0, False), (1, False)]
        assert ns['n_cells']('：甲') == 1

    def test_threshold_is_binary(self):
        """格号是整数, 判据只能二选一: < 0.5 -> 挤格, >= 0.5 -> 占格。"""
        assert _ns(PUNCT_CELL=0.49)['_punct_own']() is False
        assert _ns(PUNCT_CELL=0.5)['_punct_own']() is True


# ---------- B. 字高口径(§1.976) ----------
class TestBigHm:
    """_big_hm = run 高的 75 分位: 既挡标点碎片(小), 也挡并字长 run(大)。"""

    def test_punct_fragments_ignored(self):
        """「又曰：」实测 4 条 run: 又 19.5 / 曰 19.0 / 冒号两点 4.5+4.5。
        全 run 中位 11.75 -> 字号会被算成 13.6pt(真值 ~22); 75 分位 = 19.5 正确。"""
        rs = [(221.5, 241.0), (246.0, 265.0), (274.0, 278.5), (282.5, 287.0)]
        assert _ns()['_big_hm'](rs) == 19.5

    def test_merged_run_ignored(self):
        """并字长 run(相邻两字相碰)会抬高「最大 run 的某一比例」口径: 实测宿盡閒花列
        最大 run 48pt(萬萬并字)而真字 run 22.5pt -> 75 分位仍取 22.5 一档。"""
        rs = [(0.0, 22.5), (25.0, 47.5), (50.0, 98.0), (100.0, 122.5), (125.0, 147.0)]
        assert _ns()['_big_hm'](rs) == 47.5 - 25.0                # 22.5(75 分位仍在字 run 上)

    def test_long_column_equivalent_to_median(self):
        """长列(标点是少数)两种口径差 <= 2% —— 只在短列上分道。"""
        rs = [(i * 25.0, i * 25.0 + 22.5) for i in range(17)]
        rs[4] = (100.0, 108.5)                                   # 一个标点碎片
        assert _ns()['_big_hm'](rs) == 22.5


# ---------- C. 引號修剪(§1.98) ----------
class TestTrimMarks:
    K = 22.5          # 字 run 墨高

    def test_leading_quote_trimmed(self):
        """槽首「 (9.5pt, 紧贴首字 7pt<0.5 步进) -> 字列顶取首字顶 347.0。"""
        keep = [(330.5, 340.0), (347.0, 371.0), (373.0, 397.0)]
        assert _ns()['_trim_marks'](keep, '宿盡閒', self.K, 25.0) == (347.0, 397.0)

    def test_trailing_quote_trimmed(self):
        """槽尾 」 紧贴末字(间隙 < 0.5 步进)且前一条是字 run -> 剔, 列底取末字墨底。"""
        keep = [(0.0, 22.5), (25.0, 47.5), (52.0, 62.5)]
        assert _ns()['_trim_marks'](keep, '甲乙丙', self.K, 25.0) == (0.0, 47.5)

    def test_trailing_quote_after_punct_kept_locked(self):
        """已知遗留(锁现状): 源书列末形如 [字][。][」] 时, 」 与末字之间隔着一个标点
        (实测 15.5pt > 0.5 步进) -> 判据不剔, 该列列底多出约半格(渲染后被拉长约 5%)。
        属「OCR 未识别引號」的连带影响(内容缺失, 不是判据误判), 见报告 §6。"""
        keep = [(0.0, 22.5), (25.0, 47.5), (55.0, 63.5), (75.0, 85.5)]
        assert _ns()['_trim_marks'](keep, '甲，乙丙', self.K, 25.0) == (0.0, 85.5)

    def test_trailing_punct_kept(self):
        """文本末字是挤格标点 -> 尾端小 run 就是它, 保留(否则列末端被截短一格)。"""
        keep = [(0.0, 22.5), (25.0, 47.5), (50.0, 74.0), (75.0, 83.0)]
        assert _ns()['_trim_marks'](keep, '甲乙丙，', self.K, 25.0) == (0.0, 83.0)

    def test_leading_punct_kept(self):
        keep = [(0.0, 8.0), (10.0, 32.5)]
        assert _ns()['_trim_marks'](keep, '，甲乙', self.K, 25.0) == (0.0, 32.5)

    def test_colon_dots_not_trimmed(self):
        """「又曰：」的冒号点: 前一条 run 也是小字(另一个点) -> 不是引號, 不剔。"""
        keep = [(221.5, 241.0), (246.0, 265.0), (274.0, 278.5), (282.5, 287.0)]
        assert _ns()['_trim_marks'](keep, '又曰：', 19.5, 20.75) == (221.5, 287.0)

    def test_small_char_not_trimmed_when_detached(self):
        """正文里的「小墨字」(一二三的分离笔画)与邻字有整格间距 -> 不剔(阈值 0.5 步进挡住)。"""
        keep = [(0.0, 3.0), (20.0, 42.5)]
        assert _ns()['_trim_marks'](keep, '一二', self.K, 25.0) == (0.0, 42.5)


# ---------- D. 短列检出(§1.976) ----------
def _ink_page(cols, W=600, H=1000, scale=2):
    """构造源图墨迹布尔图: cols = [(x0pt, x1pt, [(top_pt, bot_pt)])], 单位 pt(2x px 内部)。"""
    import numpy as np
    m = np.zeros((int(H * scale), int(W * scale)), bool)
    for x0, x1, runs in cols:
        for t, b in runs:
            m[int(t * scale):int(b * scale), int(x0 * scale):int(x1 * scale)] = True
    return m


def _col_runs(n, top0, step, h=22.5):
    return [(top0 + i * step, top0 + i * step + h) for i in range(n)]


class TestShortBands:
    """三条判据(wz7 源页 354 实测): 短列 = 3 字列、字高 19.5(参照 23.0)、整页版心覆盖率 0.024。"""

    IL, IR, IT, IB = 30.0, 570.0, 60.0, 940.0
    ROWS = [(700.0, 740.0, 300.0, 900.0, '主列甲' * 20)]     # 占位: body 行(px 口径 x2)

    def _page(self, extra_cols):
        # 长列(供参照字高) + 短列
        cols = [(120.0, 142.0, _col_runs(30, 80.0, 25.0)),
                (160.0, 182.0, _col_runs(30, 80.0, 25.0))]
        cols += extra_cols
        return _ink_page(cols)

    def test_short_column_detected(self):
        """3 字短列(墨高 19.5, 与页参照同档) -> 检出, 位置取窗内墨迹实测。"""
        ink = self._page([(400.0, 414.0, [(200.0, 219.5), (224.0, 243.0), (252.0, 256.5)])])
        ns = _ns()
        r = (790.0, 840.0, 390.0, 500.0, '又曰：')            # OCR 行盒(px; x 心≈407pt)
        got = ns['_sb_band'](ink, r, [], self.IL, self.IR, self.IT, self.IB, 45.0, 22.5)
        assert got is not None
        a, b, hb = got
        assert 398.0 <= a <= 402.0 and 412.0 <= b <= 416.0     # 落位 = 窗内墨迹实测
        assert abs(hb - 19.5) < 0.6

    def test_noise_specks_rejected(self):
        """页边碎墨/噪点: 窗内有墨点(能过覆盖率与密度), 但「字高」都不在字档 -> 不收。"""
        ink = self._page([(400.0, 414.0, [(200.0, 204.0), (240.0, 244.0), (280.0, 284.0)])])
        ns = _ns()
        r = (790.0, 840.0, 390.0, 500.0, '又曰：')
        assert ns['_sb_band'](ink, r, [], self.IL, self.IR, self.IT, self.IB, 45.0, 22.5) is None

    def test_wrong_height_rejected(self):
        """有墨但不是字(印刷竖线/表格线残段: 贯穿整列的竖长 run) -> 竖线列判据挡下。"""
        ink = self._page([(400.0, 412.0, [(120.0, 700.0)])])
        ns = _ns()
        r = (790.0, 840.0, 390.0, 500.0, '又曰：')
        assert ns['_sb_band'](ink, r, [], self.IL, self.IR, self.IT, self.IB, 45.0, 22.5) is None

    def test_occupied_band_skipped(self):
        """与已用列带重叠 -> 不收(不叠字)。"""
        ink = self._page([(400.0, 414.0, _col_runs(20, 200.0, 25.0))])
        ns = _ns()
        r = (790.0, 840.0, 390.0, 500.0, '又曰：')
        assert ns['_sb_band'](ink, r, [(398.0, 416.0)], self.IL, self.IR,
                              self.IT, self.IB, 45.0, 22.5) is None

    def test_pitch_from_bands(self):
        ns = _ns()
        assert abs(ns['_sb_pitch']([(80.0, 100.0), (125.0, 145.0), (170.0, 190.0), (215.0, 235.0)],
                                   0.0, 400.0) - 45.0) < 0.6

    def test_pitch_fallback_without_samples(self):
        ns = _ns(N_COL_FRAME=12)
        assert abs(ns['_sb_pitch']([], 0.0, 480.0) - 40.0) < 0.1

    def test_ref_hm_from_page_columns(self):
        """参照字高 = 已检列带里像正文列的(nr>=5)字 run 中位。
        注: 版心(y 60-1240)比正文块高 -> 单列墨覆盖率 ~0.44 < 0.6, 不会被 _band_stats 当竖线剔掉
        (真实页同理: 实测 wz7 列覆盖率 0.3-0.5)。"""
        ink = _ink_page([(100.0, 122.0, _col_runs(20, 300.0, 25.0, h=23.0)),
                         (140.0, 162.0, _col_runs(20, 300.0, 25.0, h=21.0))], H=1300)
        ns = _ns()
        ref = ns['_sb_ref_hm'](ink, [(100.0, 122.0), (140.0, 162.0)], 60.0, 1240.0)
        assert abs(ref - 22.0) < 1.5
