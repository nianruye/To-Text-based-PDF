#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskD：竖排破折号 -> 整格矢量竖线（§1.0a4）的纯函数测试。

被测实现：`src/pipelines/build_vert.py`
  · `DASH_CHARS` / `DASH_RULE_W` / `DASH_RULE_MODE` / `_dash_rule_on` —— 开关与判据
  · `_put_tex(..., rule_h=...)` —— 不可见原字（3 Tr，文本层保留）+ 满格矢量竖线
契约（用户验收）:
  ① 相邻两破折号画出的竖线首尾**严丝合缝**（高度 = 本列 step，两条拼接无空隙）；
  ② 线宽 = DASH_RULE_W x 字号、线心 = 列心（横向居中）；
  ③ 文本层保留原字 `—`（可搜索 / 字符量不变），画面不可见（3 Tr）；
  ④ `_esc_ch` 不再改破折号字形（西文侧排 `_latin_put` 也走 `_esc_ch`，必须保持横线）。
用 _loader 从脚本里 ast 提取纯函数（不 import fitz / 不跑 upLaTeX）。

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_dash_rule.py -v
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_CONSTS = ['VERT_FORMS', 'VERT_METRICS', 'BR_ON', 'BR_SIZE_DEF', 'BR_SIZE',
           'XSCALE', 'PT2BP', 'PAGE_ORIGIN_BP',
           'DASH_CHARS', 'DASH_RULE_W', 'DASH_RULE_MODE', 'INK_ASC', 'BOLD_W']
_FUNCS = ['_br_put', '_esc_ch', '_vb', '_put_tex', '_dash_rule_on']

_RULE_RE = re.compile(r'\\put\((-?[\d.]+),(-?[\d.]+)\)\{\\rule\[(-?[\d.]+)pt\]'
                      r'\{([\d.]+)pt\}\{([\d.]+)pt\}\}')
_PUT_RE = re.compile(r'\\put\((-?[\d.]+),(-?[\d.]+)\)\{')


@pytest.fixture(scope='module')
def ns():
    return load('build_vert.py', _FUNCS, _CONSTS)


def _rule(ns, s):
    """从 _put_tex 输出里解析矢量竖线参数 -> dict(TeX pt)。"""
    m = _RULE_RE.search(s)
    assert m, '没有 rule 片段: %r' % s
    return {'x': float(m.group(1)), 'y': float(m.group(2)),
            'lift': float(m.group(3)), 'w': float(m.group(4)), 'h': float(m.group(5))}


# ---------- A. 开关判据 ----------
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


# ---------- B. 出字口契约 ----------
class TestPutTexDash:
    def test_dash_not_rewritten_by_esc(self, ns):
        """④ _esc_ch 保持原字（西文侧排也走这里，不能改成竖排码位）。"""
        assert ns['_esc_ch']('—') == '—'
        assert ns['_esc_ch']('―') == '―'
        assert ns['_esc_ch']('–') == '–'

    def test_no_rule_h_keeps_old_output(self, ns):
        """不传 rule_h -> 与旧实现一致（无 rule、无 3 Tr）。"""
        s = ns['_put_tex']('—', 100.0, 200.0, 30.0, xs=0.87)
        assert '\\rule' not in s and '3 Tr' not in s
        assert '—' in s

    def test_rule_geometry(self, ns):
        """② 线宽/线心：w = DASH_RULE_W*F，线心 = 列心 = x + xs*F/2。"""
        F, xs, x, y, step = 40.0, 0.87, 100.0, 200.0, 46.0
        s = ns['_put_tex']('—', x, y, F, xs=xs, rule_h=step)
        r = _rule(ns, s)
        w_exp = ns['DASH_RULE_W'] * F
        assert r['w'] == pytest.approx(w_exp, abs=1e-4)
        # rule 左缘 + 半宽 = 列心（页面 bp -> TeX pt）
        xc_tex = (x + xs * F / 2.0) * ns['PT2BP']
        assert r['x'] + r['w'] / 2.0 == pytest.approx(xc_tex, abs=1e-3)

    def test_rule_height_is_one_cell(self, ns):
        """① 高度 = 本列 step（相邻两格才能无缝拼接）。"""
        F, step = 40.0, 46.0
        r = _rule(ns, ns['_put_tex']('—', 100.0, 200.0, F, rule_h=step))
        assert r['h'] == pytest.approx(step * ns['PT2BP'], abs=1e-4)

    def test_lift_aligns_cell(self, ns):
        """① rule 底端 = 基线下 (step - INK_ASC*F) -> 格区间 [T, T+step] 精确对齐。"""
        F, step = 40.0, 46.0
        r = _rule(ns, ns['_put_tex']('—', 100.0, 200.0, F, rule_h=step))
        lift_exp = (ns['INK_ASC'] * F - step) * ns['PT2BP']
        assert r['lift'] == pytest.approx(lift_exp, abs=1e-4)
        # rule 顶端（TeX 自页底） = put_y + lift + h = put_y + INK_ASC*F*PT2BP
        assert r['y'] + r['lift'] + r['h'] == pytest.approx(
            r['y'] + ns['INK_ASC'] * F * ns['PT2BP'], abs=1e-4)

    def test_consecutive_dashes_tile_without_gap(self, ns):
        """① 核心验收：上下相邻两条 rule 首尾相接（差 = 0，不是两条字符拼接的缝）。"""
        F, xs, step = 40.0, 0.87, 46.0
        y_hi = 200.0                       # 上一字 \put y（自页底向上，故下一字 = y-step）
        s1 = ns['_put_tex']('—', 100.0, y_hi, F, xs=xs, rule_h=step)
        s2 = ns['_put_tex']('—', 100.0, y_hi - step, F, xs=xs, rule_h=step)
        r1, r2 = _rule(ns, s1), _rule(ns, s2)
        # \put y 按 %.2f 打印（每条 ±0.005 TeX pt），故容差取 0.011
        assert r1['y'] - (r2['y'] + r2['h']) == pytest.approx(0.0, abs=0.011)
        # 总高 = 2 个 step（用户验收「线的总高度 ≈ 2 个 step」）
        assert r1['h'] + r2['h'] == pytest.approx(2 * step * ns['PT2BP'], abs=1e-4)
        # 两条线心一致（同一列）
        assert r1['x'] == pytest.approx(r2['x'], abs=1e-6)

    def test_text_layer_kept_invisible(self, ns):
        """③ 文本层保留原字 + 3 Tr 不可见（画面由 rule 画，搜索/字符量不变）。"""
        s = ns['_put_tex']('—', 100.0, 200.0, 40.0, xs=0.87, rule_h=46.0)
        assert '3 Tr' in s
        # 3 Tr 必须包住原字，且原字仍是 U+2014（不是 U+FE31）
        q = s.index('q 3 Tr')
        assert '—' in s[q:]
        assert '︱' not in s
        # 原字的字号/压缩输出不变（文本层位置与旧实现同源）
        assert '\\fontsize{40.0pt}{40.0pt}\\selectfont —' in s

    @pytest.mark.parametrize('ch', ['―', '–'])
    def test_other_dash_codepoints(self, ns, ch):
        """破折号类三个码位都走矢量竖线。"""
        assert '\\rule' in ns['_put_tex'](ch, 100.0, 200.0, 40.0, rule_h=46.0)

    def test_non_dash_ignores_rule_h(self, ns):
        """普通汉字即使传了 rule_h 也不画线（调用方按列传参，不能误伤正文）。"""
        s = ns['_put_tex']('國', 100.0, 200.0, 40.0, rule_h=46.0)
        assert '\\rule' not in s and '3 Tr' not in s
