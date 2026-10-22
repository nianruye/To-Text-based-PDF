#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskD / taskD-R2：竖排破折号 = 源图墨迹实测的一条连续竖线（§1.0a4）。

被测实现：`src/pipelines/build_vert.py`
  · `_dash_rule_on` / `DASH_RULE_MODE` —— 影响面（默认仅无版框页）
  · `_dash_runs` —— 相邻破折号字符 -> 一组（同一源图墨块）
  · `_dash_ink_seg` —— 在源图该列该格区读竖直墨段 -> y0/y1/线心/线宽（全部实测）
  · `_dash_rule_tex` —— 实测墨段 -> 一条矢量竖线（高度/位置/线心取实测）
  · `_put_tex(rule_h=)` —— **兜底**路径（读不到墨迹时每字 1.0 step，旧 R1 行为）
契约（用户验收 R2）:
  ① 相邻两个 `—` 合成一条线，长度 = **源图墨段实测**（p57 实测 1.26 step，不是 2 step）；
  ② 线顶/线底/线心/线宽从源图墨迹实测，不用 step/F/INK_ASC 推算；
  ③ 文本层保留原 `—`（3 Tr 不可见，可搜索 / 字符量不变）；
  ④ 读不到源图 -> 兜底 1.0 step/字 + 日志（不静默用推算值）；
  ⑤ `_esc_ch` 不改字形（西文侧排也走它）。
用 _loader 从脚本里 ast 提取纯函数（不 import fitz / 不跑 upLaTeX）。

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_dash_rule.py -v
"""
import re
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_CONSTS = ['VERT_FORMS', 'VERT_METRICS', 'BR_ON', 'BR_SIZE_DEF', 'BR_SIZE',
           'XSCALE', 'PT2BP', 'PAGE_ORIGIN_BP',
           'DASH_CHARS', 'DASH_RULE_W_RAW', 'DASH_RULE_W', 'DASH_RULE_MODE',
           'DASH_LEN_RATIO', 'DASH_SEG_LO', 'DASH_SEG_HI', 'DASH_SEG_OVL',
           'DASH_X_TOL', 'DASH_W_MAX', 'DASH_DBG', 'INK_ASC', 'BOLD_W']
_FUNCS = ['_br_put', '_esc_ch', '_vb', '_put_tex', '_dash_rule_on',
          '_dash_runs', '_dash_ink_seg', '_dash_rule_tex', '_fg_origin_shift']

_RULE_RE = re.compile(r'\\put\((-?[\d.]+),(-?[\d.]+)\)\{\\rule(?:\[(-?[\d.]+)pt\])?'
                      r'\{([\d.]+)pt\}\{([\d.]+)pt\}')


@pytest.fixture(scope='module')
def ns():
    return load('build_vert.py', _FUNCS, _CONSTS, mocks={'page_h': 400.0})


def _rule(ns, s):
    """从 _put_tex / _dash_rule_tex 输出里解析竖线参数 -> dict(TeX pt; lift 可缺省)。"""
    m = _RULE_RE.search(s)
    assert m, '没有 rule 片段: %r' % s
    return {'x': float(m.group(1)), 'y': float(m.group(2)),
            'lift': float(m.group(3)) if m.group(3) is not None else 0.0,
            'w': float(m.group(4)), 'h': float(m.group(5))}


def _fake_ink(shape=(800, 800), blocks=()):
    """合成源图墨迹 bool 图(2x px)。blocks = [(x0,x1,y0,y1)] px 区间。"""
    a = np.zeros(shape, dtype=bool)
    for x0, x1, y0, y1 in blocks:
        a[y0:y1, x0:x1] = True
    return a


def _pt(p):
    return int(round(p * 2.0))


# ---------- A. 影响面 ----------
class TestDashRuleOn:
    def _m(self, virtual):
        return {'g': {'virtual': virtual}}

    def test_default_is_nf_only(self, ns):
        """默认 nf：无版框伪槽格页开，有版框页(wz6)关（有版框书 vert.tex 零回归）。"""
        assert ns['DASH_RULE_MODE'] == 'nf'
        assert ns['_dash_rule_on'](self._m(True)) is True
        assert ns['_dash_rule_on'](self._m(False)) is False
        assert ns['_dash_rule_on'](None) is False

    @pytest.mark.parametrize('mode', ['all', '1', 'on'])
    def test_all_modes_force_on(self, ns, mode):
        ns['DASH_RULE_MODE'] = mode
        try:
            assert ns['_dash_rule_on'](self._m(False)) is True
        finally:
            ns['DASH_RULE_MODE'] = 'nf'

    @pytest.mark.parametrize('mode', ['0', 'off', 'false', 'False', ''])
    def test_off_modes_disable(self, ns, mode):
        ns['DASH_RULE_MODE'] = mode
        try:
            assert ns['_dash_rule_on'](self._m(True)) is False
        finally:
            ns['DASH_RULE_MODE'] = 'nf'


# ---------- B. 相邻破折号 -> 一组 ----------
class TestDashRuns:
    def test_pair_is_one_run(self, ns):
        """两个相邻 `—`（格号连续）-> 一组（同一源图墨块）。"""
        assert ns['_dash_runs']('論書——導讀', [0, 1, 2, 3, 4, 5]) == [(2, 3, 2, 2)]

    def test_three_is_one_run(self, ns):
        assert ns['_dash_runs']('———', [0, 1, 2]) == [(0, 2, 0, 3)]

    def test_gap_between_dashes_splits_runs(self, ns):
        """fit_gaps 在两组之间插了空格(格号不连续) -> 不是一组。"""
        assert ns['_dash_runs']('——', [0, 2]) == [(0, 0, 0, 1), (1, 1, 2, 1)]

    def test_non_dash_text_ignored(self, ns):
        assert ns['_dash_runs']('國——國', [0, 1, 2, 3]) == [(1, 2, 1, 2)]
        assert ns['_dash_runs']('國國', [0, 1]) == []


# ---------- C. 源图墨迹实测 ----------
class TestDashInkSeg:
    # 页面坐标: xc=200, step=50, 格区 y 100..200 (两个字符 -> 100pt)
    XC, STEP, YC0, YC1 = 200.0, 50.0, 100.0, 200.0

    def _seg(self, ns, blocks, xc=None, step=None):
        ink = _fake_ink(blocks=blocks)
        ns['src_doc'] = object()
        ns['_frame_ink'] = lambda pi, g: ink
        return ns['_dash_ink_seg'](0, {'virtual': True}, xc or self.XC,
                                   step or self.STEP, self.YC0, self.YC1, 2)

    def test_line_measured(self, ns):
        """竖直墨段 (x 195-205, y 130-180) -> y0/y1/线心/线宽全实测。"""
        seg = self._seg(ns, [(_pt(195), _pt(205), _pt(130), _pt(180))])
        assert seg is not None
        assert seg['y0'] == pytest.approx(130.0, abs=0.5)
        assert seg['y1'] == pytest.approx(180.0, abs=0.5)
        assert seg['ratio'] == pytest.approx(1.0, abs=0.02)
        assert seg['xc'] == pytest.approx(200.0, abs=0.5)
        assert seg['w'] == pytest.approx(10.0, abs=1.0)

    def test_length_not_cell_count(self, ns):
        """源书线只占 1.26 格(63pt) -> 实测 63pt, 不是 2 格 100pt。"""
        seg = self._seg(ns, [(_pt(195), _pt(205), _pt(118.5), _pt(181.5))])
        assert seg is not None
        assert seg['y1'] - seg['y0'] == pytest.approx(63.0, abs=0.5)
        assert seg['ratio'] == pytest.approx(1.26, abs=0.02)

    def test_neighbor_stroke_rejected(self, ns):
        """邻字笔画(大部分在本组格区之外)不算破折号线。"""
        seg = self._seg(ns, [(_pt(195), _pt(205), _pt(20), _pt(90))])
        assert seg is None

    def test_wide_block_rejected(self, ns):
        """过宽墨块(字/粘连)不是细线。"""
        seg = self._seg(ns, [(_pt(170), _pt(230), _pt(130), _pt(180))])
        assert seg is None

    def test_off_center_rejected(self, ns):
        """线心离列心太远(错列/字画笔)不算。"""
        seg = self._seg(ns, [(_pt(225), _pt(235), _pt(130), _pt(180))])
        assert seg is None

    def test_short_stroke_rejected(self, ns):
        """太短的竖段(标点/引号笔画)不是破折号线。"""
        seg = self._seg(ns, [(_pt(195), _pt(205), _pt(140), _pt(160))])
        assert seg is None

    def test_no_source_pdf(self, ns):
        ns['src_doc'] = None
        assert ns['_dash_ink_seg'](0, {'virtual': True}, 200.0, 50.0, 100.0, 200.0, 2) is None
        ns['src_doc'] = object()


# ---------- D. 实测墨段 -> 矢量竖线 ----------
class TestDashRuleTex:
    # seg 为源图实测值(bp): y 100..180, 线心 x200, 源图线宽 5
    SEG = {'y0': 100.0, 'y1': 180.0, 'xc': 200.0, 'w': 5.0, 'ratio': 1.6}

    def test_geometry_from_source(self, ns):
        """高度 = y1-y0（实测），put y = page_h - y1 - FG 偏移（源图绝对位置），线心 = 实测 xc。"""
        r = _rule(ns, ns['_dash_rule_tex'](self.SEG, 40.0))
        k = ns['PT2BP']
        shift = ns['_fg_origin_shift']()
        assert r['h'] == pytest.approx(80.0 * k, abs=1e-4)
        assert r['y'] == pytest.approx((400.0 - 180.0 - shift) * k, abs=1e-2)
        assert r['lift'] == 0.0
        w_exp = ns['DASH_RULE_W'] * 40.0 * k          # 线宽(bp) -> TeX pt
        assert r['w'] == pytest.approx(w_exp, abs=1e-4)
        assert r['x'] + r['w'] / 2.0 == pytest.approx(200.0 * k, abs=1e-2)

    def test_fg_origin_shift_is_page_relative(self, ns):
        """FG 原点偏移 = page_h×(1−1/PT2BP)（p57 1437pt -> 5.37pt）。"""
        shift = ns['_fg_origin_shift']()
        assert shift == pytest.approx(400.0 * (1.0 - 1.0 / ns['PT2BP']), abs=1e-9)
        assert shift > 0.0

    def test_src_width_mode(self, ns):
        """VERT_DASH_RULE_W='src' -> 直接用源图实测线宽。"""
        old = ns['DASH_RULE_W_RAW']
        ns['DASH_RULE_W_RAW'] = 'src'
        try:
            r = _rule(ns, ns['_dash_rule_tex'](self.SEG, 40.0))
            assert r['w'] == pytest.approx(5.0 * ns['PT2BP'], abs=1e-4)
        finally:
            ns['DASH_RULE_W_RAW'] = old


# ---------- E. 兜底路径（读不到源图时）----------
class TestFallbackPutTex:
    def test_dash_not_rewritten_by_esc(self, ns):
        """⑤ _esc_ch 保持原字（西文侧排也走这里，不能改成竖排码位）。"""
        assert ns['_esc_ch']('—') == '—'
        assert ns['_esc_ch']('―') == '―'
        assert ns['_esc_ch']('–') == '–'

    def test_no_rule_h_keeps_old_output(self, ns):
        """不传 rule_h -> 与旧实现一致（无 rule、无 3 Tr）。"""
        s = ns['_put_tex']('—', 100.0, 200.0, 30.0, xs=0.87)
        assert '\\rule' not in s and '3 Tr' not in s
        assert '—' in s

    def test_fallback_rule_geometry(self, ns):
        """兜底：线宽/线心/高度 = 1 格 step（旧 R1 行为）。"""
        F, xs, x, y, step = 40.0, 0.87, 100.0, 200.0, 46.0
        r = _rule(ns, ns['_put_tex']('—', x, y, F, xs=xs, rule_h=step))
        assert r['w'] == pytest.approx(ns['DASH_RULE_W'] * F, abs=1e-4)
        assert r['h'] == pytest.approx(step * ns['PT2BP'], abs=1e-4)
        xc_tex = (x + xs * F / 2.0) * ns['PT2BP']
        assert r['x'] + r['w'] / 2.0 == pytest.approx(xc_tex, abs=1e-3)
        lift_exp = (ns['INK_ASC'] * F - step) * ns['PT2BP']
        assert r['lift'] == pytest.approx(lift_exp, abs=1e-4)

    def test_fallback_consecutive_dashes_tile(self, ns):
        """兜底路径：相邻两字各 1.0 step，首尾相接（无源图时的旧行为）。"""
        F, xs, step = 40.0, 0.87, 46.0
        y_hi = 200.0
        r1 = _rule(ns, ns['_put_tex']('—', 100.0, y_hi, F, xs=xs, rule_h=step))
        r2 = _rule(ns, ns['_put_tex']('—', 100.0, y_hi - step, F, xs=xs, rule_h=step))
        assert r1['y'] - (r2['y'] + r2['h']) == pytest.approx(0.0, abs=0.011)
        assert r1['h'] + r2['h'] == pytest.approx(2 * step * ns['PT2BP'], abs=1e-4)

    def test_text_layer_kept_invisible(self, ns):
        """③ 文本层保留原字 + 3 Tr 不可见（画面由 rule 画，搜索/字符量不变）。"""
        s = ns['_put_tex']('—', 100.0, 200.0, 40.0, xs=0.87, rule_h=46.0)
        assert '3 Tr' in s
        q = s.index('q 3 Tr')
        assert '—' in s[q:]
        assert '︱' not in s
        assert '\\fontsize{40.0pt}{40.0pt}\\selectfont —' in s

    def test_invisible_only_has_no_rule(self, ns):
        """源图实测路径：只出不可见文本层，不画兜底线。"""
        s = ns['_put_tex']('—', 100.0, 200.0, 40.0, xs=0.87, invisible=True)
        assert '3 Tr' in s and '\\rule' not in s
        assert '—' in s

    @pytest.mark.parametrize('ch', ['―', '–'])
    def test_other_dash_codepoints(self, ns, ch):
        assert '\\rule' in ns['_put_tex'](ch, 100.0, 200.0, 40.0, rule_h=46.0)

    def test_non_dash_ignores_rule_h(self, ns):
        """普通汉字即使传了 rule_h 也不画线（调用方按列传参，不能误伤正文）。"""
        s = ns['_put_tex']('國', 100.0, 200.0, 40.0, rule_h=46.0)
        assert '\\rule' not in s and '3 Tr' not in s
