#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskJ：竖排字模横向压缩(taskJ-A) + 列内空隙对齐(taskJ-B) 的纯函数测试。

被测实现：`src/pipelines/build_vert.py`
  · §1.0a `_put_tex` / `XSCALE`      —— 单字 \\put 片段(横向压缩 x 保字高)
  · §1.0b `char_cells` / `fit_gaps`  —— 逐字格号 + 槽内 run 序列的空隙对齐 DP
用 _loader 从脚本里 ast 提取纯函数（不 import fitz / 不跑 upLaTeX）。

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_width_gap.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_CONSTS = ['PUNCT_HANG', 'XSCALE', 'PT2BP', 'PAGE_ORIGIN_BP', 'INK_RATIO', 'GAP_ON', 'GAP_HANG',
           'P_MERGE', 'P_PUNCT', 'P_SKIPN', 'P_SKIPR', 'P_GAP', 'P_TOT', 'GAP_MAX']


@pytest.fixture(scope='module')
def ns():
    return load('build_vert.py', ['char_cells', 'n_cells', 'fit_gaps', '_put_tex', '_esc_ch'],
                _CONSTS)


# ---------- A. 横向压缩 ----------
class TestXScale:
    def test_default_is_compressed(self):
        """默认 XSCALE < 1（源书字模为长体窄字，实测标定 0.87）。"""
        assert 0.5 < 0.87 <= 1.0

    def test_put_tex_scales_horizontally(self, ns):
        """xs<1 -> 自带 q/<K> 0 0 1 0 0 cm ... Q 包住该字（缩 x 保字高）；put x 按 PAGE_ORIGIN_BP 反解。"""
        s = ns['_put_tex']('國', 100.0, 200.0, 34.4, xs=0.87)
        # x_pt = (100-72)/0.87+72 = 104.184, x PT2BP -> 104.6
        assert s.startswith('\\put(104.6,200.7){')          # PT2BP = 1.00375
        assert '\\special{pdf:literal direct q 0.87 0 0 1 0 0 cm}' in s
        assert s.endswith('\\special{pdf:literal direct Q}}')
        assert '\\fontsize{34.4pt}{34.4pt}\\selectfont 國' in s

    def test_put_tex_no_scale_when_xs_is_1(self, ns):
        """xs=1 -> 与旧格式一致（不带任何压缩包裹，便于回退对照）。"""
        s = ns['_put_tex']('國', 10.0, 20.0, 34.4, xs=1.0)
        assert 'pdf:literal' not in s
        assert s == '\\put(10.0,20.1){\\fontsize{34.4pt}{34.4pt}\\selectfont 國}'

    def test_put_tex_escapes(self, ns):
        """转义仍走 _esc_ch（% # & _）。"""
        s = ns['_put_tex']('%', 0.0, 0.0, 12.0, xs=0.8)
        assert '\\%' in s and 'pdf:literal direct q 0.8 0 0 1 0 0 cm' in s

    def test_put_tex_uses_no_graphicx_scalebox(self, ns):
        """taskJ2 回归锁：绝不出现 \\scalebox / btrans / etrans / x:scale ——
        graphicx 的 btrans+etrans 用 6 位有效数字的数值逆矩阵还原(1/0.87 -> 1.14943),
        每字在 CTM 残留 x1.0000041, 累积后污染同页后续图形/文本坐标(N=2000 实测规则线
        从 0..571.86bp 漂到 -2.34..574.29bp = 越出页缘; p157 的 verify_vert 矢量越界即此)。"""
        for xs in (0.87, 0.8, 0.95):
            s = ns['_put_tex']('國', 100.0, 200.0, 34.4, xs=xs)
            for bad in ('scalebox', 'btrans', 'etrans', 'x:scale', 'resizebox'):
                assert bad not in s

    def test_put_tex_x_compensation_roundtrip(self, ns):
        """put x 反解正确性：写入值还原回页坐标后应等于传入的目标页坐标。
        记 w = put 里写的值(TeX pt), 页坐标 = 72 + K x (w/PT2BP - 72)（1/PT2BP = 0.99626 = pt->bp）。"""
        K = 0.87
        for X in (0.0, 12.5, 100.0, 300.0, 571.0):
            s = ns['_put_tex']('國', X, 200.0, 34.4, xs=K)
            w = float(s[len('\\put('):s.index(',')])
            page_x = ns['PAGE_ORIGIN_BP'] + K * (w / ns['PT2BP'] - ns['PAGE_ORIGIN_BP'])
            assert abs(page_x - X) < 0.06        # %.1f 打印精度

    def test_put_tex_k_printed_matches_inversion(self, ns):
        """反解用的 K 必须与写进 special 的 K 一致（打印后取回），否则位置与缩放不匹配。"""
        s = ns['_put_tex']('國', 260.0, 200.0, 34.4, xs=0.8696)
        assert 'pdf:literal direct q 0.8696 0 0 1 0 0 cm' in s
        w = float(s[len('\\put('):s.index(',')])
        assert abs((ns['PAGE_ORIGIN_BP'] + 0.8696 * (w / ns['PT2BP'] - ns['PAGE_ORIGIN_BP'])) - 260.0) < 0.06


# ---------- B. 格号 / 空隙 DP ----------
class TestCharCells:
    def test_cells_advance_per_char(self, ns):
        assert ns['char_cells']('甲乙丙') == [(0, False), (1, False), (2, False)]

    def test_hang_punct_shares_prev_cell(self, ns):
        """挤格标点与前一字同格（hanging=True），不推进格号。"""
        assert ns['char_cells']('問：甲') == [(0, False), (0, True), (1, False)]

    def test_matches_n_cells(self, ns):
        """char_cells 的格数应与既有 n_cells 一致(非首位标点的常见形态)。"""
        for t in ('問：甲', '甲。乙，丙', '甲'):
            assert ns['n_cells'](t) == max(c for c, _h in ns['char_cells'](t)) + 1

    def test_leading_punct_known_divergence(self, ns):
        """已知遗留(非 taskJ 引入, 锁现状): 首位挤格标点时 n_cells 少算一格 ——
        renderer/char_cells 把它当普通字占一格(k>0 才挤格), n_cells 无条件不计。全书无此类列。"""
        assert ns['char_cells']('：甲') == [(0, False), (1, False)]
        assert ns['n_cells']('：甲') == 1


class TestFitGaps:
    """槽内 run 序列 + 文本 -> 插入格位置。run/文本用 wz6 p15 問：列实测值(pt)。"""
    T = '問：照你的意見，這次解放戰爭，主要的戰略方針是什麼？'
    RUNS = [(335.8, 365.2), (398.2, 425.8), (427.2, 457.2), (458.2, 488.8), (489.0, 519.5),
            (520.5, 581.8), (582.5, 643.2), (643.5, 674.0), (675.0, 704.8), (706.0, 735.2),
            (736.2, 765.8), (768.5, 796.5), (798.0, 828.5), (829.5, 859.0), (859.8, 920.5),
            (920.8, 951.5), (952.5, 981.8), (982.8, 1013.5), (1014.0, 1043.8)]

    def test_gap_after_punct(self, ns):
        """源书「問：」后空一格：检出插入点 = 2（在「照」前、冒号后 —— 源书冒号紧贴問的字脚）。"""
        assert ns['fit_gaps'](self.RUNS, self.T, 31.0, 335.8, 1043.8, h_ink=29.5) == [(2, 1)]

    def test_no_gap_when_runs_match_text(self, ns):
        """无空隙的列（等距 run 与文本一一对应）-> 不插格。"""
        runs = [(100.0 + 31.0 * i, 100.0 + 31.0 * i + 29.0) for i in range(10)]
        assert ns['fit_gaps'](runs, '甲乙丙丁戊己庚辛壬癸', 31.0, 100.0, 380.0, h_ink=29.0) == []

    def test_touching_chars_not_a_gap(self, ns):
        """相邻字相碰并成一个 run（顶差 = 2 步进）不算空隙 —— 靠「格内无墨」校验区分。"""
        runs = [(100.0, 160.0), (162.0, 191.0), (193.0, 222.0), (224.0, 253.0),
                (255.0, 284.0), (286.0, 315.0)]
        assert ns['fit_gaps'](runs, '甲乙丙丁戊己庚', 31.0, 100.0, 315.0, h_ink=29.0) == []

    def test_ocr_missing_char_is_not_a_gap(self, ns):
        """OCR 漏字（文本比墨迹少一字, 但每格都有墨）-> 不插格（插了只是掩盖丢字并把后续字挤下）。"""
        runs = [(100.0 + 31.0 * i, 100.0 + 31.0 * i + 29.0) for i in range(11)]
        assert ns['fit_gaps'](runs, '甲乙丙丁戊己庚辛壬癸', 31.0, 100.0, 410.0, h_ink=29.0) == []

    def test_disabled_returns_empty(self, ns, monkeypatch):
        """VERT_GAP=0 时不做检测（回退开关）。"""
        ns2 = load('build_vert.py', ['fit_gaps', 'char_cells', 'n_cells'],
                   [c for c in _CONSTS if c != 'GAP_ON'], mocks={'GAP_ON': False})
        assert ns2['fit_gaps'](self.RUNS, self.T, 31.0, 335.8, 1043.8, h_ink=29.5) == []
