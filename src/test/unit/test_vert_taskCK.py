#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskCK：列内叠字修复的纯函数测试。

被测实现：`src/pipelines/build_vert.py`
  · `_step_chars` —— 步进分类的格数口径：连续拉丁字母串按 1 格计
    （修前按逐字母计数 -> 西文词多的正文列步进被低估成「小字注」）
  · `_band_stats(min_h)` —— 「像字 run」高下限可调；纯数码行（页码）传 1.0，
    否则页码的 2-4pt 细横画被 4pt 下限滤掉、top/bot 只剩半列
  · `special_rows` —— 同列成链的候选不再认领为书眉/页码
    （「第N回」与回目行同 x 带相邻 -> 是正文列的一段，不是书眉）

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_taskCK.py -v
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_FUNCS = ['_step_chars', '_band_stats', '_runs', 'special_rows']


def _ns(**over):
    d = dict(
        NUM_CHARS=set('0123456789〇零一二三四五六七八九十百千'),
        _NF={'on': True},
    )
    d.update(over)
    return load('build_vert.py', _FUNCS, [], mocks=d)


# ---------- A. 步进格数口径 `_step_chars` ----------
class TestStepChars:
    def test_cjk_each_one(self):
        assert _ns()['_step_chars']('金瓶梅') == 3

    def test_latin_run_is_one_cell(self):
        # 「narrative」「art」两个连续字母串 = 2 格；空格/）/) /下 各 1 格
        assert _ns()['_step_chars']('narrative art）)下') == 6

    def test_mixed_column(self):
        assert _ns()['_step_chars']('甲abc乙') == 3

    def test_digits_and_punct_each_one(self):
        assert _ns()['_step_chars']('一九八六，') == 5

    def test_empty_is_at_least_one(self):
        # 分母不得为 0（调用方直接做除法）
        assert _ns()['_step_chars']('') == 1

    def test_p35_row08_step_becomes_plausible(self):
        """实测 p35 row08：57 字 / 2009.6px。逐字母 35.3px，按格 80.4px —— 后者像正文列。"""
        t = 'narrative art）)下，可以分辨的有寓言，包括exemplum allegory,moral fable'
        span_px = 2009.6
        ns = _ns()
        assert abs(span_px / ns['_step_chars'](t) - 80.4) < 0.5
        assert span_px / len(t) < 40.0          # 修前口径（错误地像小字注）


# ---------- B. `_band_stats(min_h)`：细笔画数码 ----------
def _thin_stroke_page():
    """合成墨迹（2x px）：一条 x 10-30px 的列，三条细横画 run：
    y 10.0-13.0pt (3pt) / 30.0-35.5pt (5.5pt) / 50.0-52.0pt (2pt)。"""
    ink = np.zeros((200, 60), dtype=bool)
    ink[20:26, 10:30] = True       # 10.0-13.0pt
    ink[60:71, 10:30] = True       # 30.0-35.5pt
    ink[100:104, 10:30] = True     # 50.0-52.0pt
    return ink


class TestBandStatsMinH:
    def test_default_4pt_drops_thin_strokes(self):
        """修前口径：3pt/2pt 横画被滤掉 -> top/bot 只剩中间那段（半列）。"""
        ns = _ns()
        st = ns['_band_stats'](_thin_stroke_page(), 5.0, 15.0, 0.0, 100.0, pad=0.0)
        assert st['nr'] == 1
        assert abs(st['top'] - 30.0) < 0.6
        assert abs(st['bot'] - 35.5) < 0.6

    def test_min_h_1_keeps_all_strokes(self):
        """数码行口径：top/bot 取全笔画跨度（p70 二六 = 1077.0-1116.5pt 同源）。"""
        ns = _ns()
        st = ns['_band_stats'](_thin_stroke_page(), 5.0, 15.0, 0.0, 100.0, pad=0.0, min_h=1.0)
        assert st['nr'] == 3
        assert abs(st['top'] - 10.0) < 0.6
        assert abs(st['bot'] - 52.0) < 0.6

    def test_min_h_default_equals_explicit_4(self):
        ns = _ns()
        a = ns['_band_stats'](_thin_stroke_page(), 5.0, 15.0, 0.0, 100.0, pad=0.0)
        b = ns['_band_stats'](_thin_stroke_page(), 5.0, 15.0, 0.0, 100.0, pad=0.0, min_h=4.0)
        assert a == b


# ---------- C. `special_rows`：同列成链不认领 ----------
class TestSpecialRowChain:
    ROW_NUM = (68.0, 132.5, 412.8, 690.1, '第四十一回')
    ROW_TITLE = (80.0, 139.0, 699.0, 1712.0, '西門慶與喬大戶結親潘金蓮共李瓶兒鬪氣')

    def test_chapter_number_before_title_is_not_header(self):
        """p667 实测：第N回 y 尾 690.1 与回目行 y 首 699.0 间距 8.9px <= 2.5x步进 -> 正文列一段。"""
        ns = _ns(all_rows={'p': [self.ROW_NUM, self.ROW_TITLE]},
                 _nf_thr=lambda k: (9999.0, 9999.0, 150.0, 10.0))
        assert ns['special_rows']('p') == []

    def test_real_header_still_claimed(self):
        """真正的书眉（右页边带内、同列无相邻长行）必须保持认领。"""
        hd = (1200.0, 1260.0, 460.0, 660.0, '金瓶梅')
        ns = _ns(all_rows={'p': [hd]},
                 _nf_thr=lambda k: (9999.0, 1100.0, 150.0, 10.0))
        out = ns['special_rows']('p')
        assert len(out) == 1 and out[0][0] == 'hd' and out[0][1] == '金瓶梅'

    def test_chain_gate_only_on_nf_path(self):
        """有版框路径(_NF['on']=False)保持原行为：同样的行仍被认领。"""
        ns = _ns(all_rows={'p': [self.ROW_NUM, self.ROW_TITLE]},
                 _nf_thr=lambda k: (9999.0, 9999.0, 150.0, 10.0),
                 _NF={'on': False})
        out = ns['special_rows']('p')
        assert len(out) == 1 and out[0][1] == '第四十一回'
