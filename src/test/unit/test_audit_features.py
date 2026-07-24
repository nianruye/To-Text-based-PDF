#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""architecture_audit.md §7 第一批特征测试：锁定 8 个行为差异。

#7（_heading_core v13 vs geom 引号）已在 test_pure_funcs.py TestCrossFuncDivergence 覆盖。
"""
import sys
import os
import statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pipelines'))
from _loader import load
from utils.tex_escape import escape_latex
from utils.geometry import calibrate
from utils.page_numbers import PN_RE
from _latex_preamble import build_latex

import pytest
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture(scope="module")
def v13():
    return load('build_pdf_v13.py',
                func_names={'escape_tex', 'is_page_number'},
                const_names={})


@pytest.fixture(scope="module")
def classic():
    return load('build_classic.py',
                func_names={'_head_level', 'page_pitch'},
                const_names={},
                mocks={'DPI': 200})


@pytest.fixture(scope="module")
def geom():
    return load('build_geom.py',
                func_names={'page_pitch'},
                const_names={},
                mocks={'DPI': 200})


# #1 _esc_chars geom 模式（当前只测了 classic）
class TestEscCharsGeom:
    """geom 模式：单反斜杠删除 + 无省略号归一化（与 classic 差异）。"""

    @pytest.mark.parametrize("inp,exp", [
        ("a\\b", "ab"),                # 单反斜杠删除（classic 保留）
        ("a%b", r"a\%b"),              # 转义单反斜杠（与 classic 一致）
        ("…", "…"),                    # 无省略号归一化（classic -> '.'）
        ("○", "〇"),                   # 与 classic 一致
        ("①", r"\textcircled{1}"),     # 与 classic 一致
    ])
    def test_esc_chars_geom(self, inp, exp):
        assert escape_latex(inp, 'geom') == exp


# #2 escape_tex v13 模式（不处理圈码/○/【】）
class TestEscapeTexV13Extras:
    """v13 escape_tex 不处理圈码/○/【】（与 geom/classic 不同）。"""

    def test_no_circled(self, v13):
        assert v13['escape_tex']('①') == '①'

    def test_no_circle_fix(self, v13):
        assert v13['escape_tex']('○') == '○'

    def test_no_bracket_fix(self, v13):
        assert v13['escape_tex']('【】') == '【】'

    def test_backslash_placeholder(self, v13):
        # #2 修复后：占位符防二次转义
        assert v13['escape_tex']('a\\b') == r'a\textbackslash{}b'


# #3 _head_level classic 模式（有附录判定）
class TestHeadLevelClassic:
    """classic _head_level 有附录判定（geom 无）。"""

    @pytest.mark.parametrize("t,is_big,exp", [
        ("附录一", False, "part"),     # classic L50 附录 -> part
        ("引言", False, "title"),
        ("1 标题", False, "section"),
        ("第一部分", True, "part"),
    ])
    def test_head_level_classic(self, classic, t, is_big, exp):
        assert classic['_head_level'](t, is_big) == exp


# #4 page_pitch geom vs classic 差异
class TestPagePitchDiff:
    """异常大间距时 geom/classic 都返回有效 pitch(中位,1.8*m0 滤掉 outlier)。
    旧版 geom 用方差过滤(pstdev>0.4*m0)对 outlier 返回 None,已移除(误杀 wz3 315 页)。
    classic 仍用 inner 口径;两者都靠 1.8*m0 过滤异常大间距。"""

    @staticmethod
    def _make_data():
        gaps = [30] * 4 + [80] + [30] * 4  # 8 行，中间一个 80px 异常间距
        polys = []
        y = 100
        for gap in gaps:
            polys.append([[50, y], [350, y], [350, y + 15], [50, y + 15]])
            y += gap
        return {'0': polys}, {'0': ['测' * 10] * 9}

    def test_geom_returns_pitch_on_outlier(self, geom):
        """80px outlier 被 1.8*m0(=1.8*30=54) 滤掉,pitch=中位 30px=10.8pt。"""
        co, sl = self._make_data()
        geom['co'] = co
        geom['sl'] = sl
        geom['page_px_h'] = 1000.0
        result = geom['page_pitch']('0')
        assert result is not None
        assert 10.0 <= result <= 45.0
        assert abs(result - 10.8) < 0.1

    def test_classic_returns_pitch_on_outlier(self, classic):
        co, sl = self._make_data()
        classic['co'] = co
        classic['sl'] = sl
        classic['page_px_h'] = 1000.0
        result = classic['page_pitch']('0')
        assert result is not None
        assert 10.0 <= result <= 45.0


# #5 build_latex _cjk_glue per mode
class TestBuildLatexCjkGlue:
    """_cjk_glue 按 mode 分发（classic vs geom vs USE_REGION）。"""

    def test_classic_non_region(self):
        latex = build_latex('classic', 405, 633, 50, False, 1.5, [])
        assert '0.15em plus 0.35em minus 0.8em' in latex

    def test_geom_non_region(self):
        latex = build_latex('geom', 405, 633, 50, False, 1.5, [])
        assert '0pt plus 0.5em minus 0.4em' in latex

    def test_use_region_both_modes(self):
        for mode in ('classic', 'geom'):
            latex = build_latex(mode, 405, 633, 50, True, 1.5, [])
            assert '0pt plus 0.05em minus 0.5em' in latex


# #6 calibrate 几何推导
class TestCalibrate:
    """calibrate 从 coords/sl 推导 cw/MEASURE/FONT/BASELINE。"""

    def test_known_geometry(self):
        # 构造满行 30 字、行距 30px 的 coords/sl
        sl = {'0': ['字' * 30] * 10}
        polys = []
        y = 100
        for _ in range(10):
            polys.append([[50, y], [350, y], [350, y + 15], [50, y + 15]])
            y += 30
        co = {'0': polys}
        g = calibrate(sl, co, DPI=200)
        assert g['cw'] == 30
        assert g['PAGE_W'] > 0
        assert g['MEASURE'] > 0
        assert g['FONT'] > 0
        assert g['BASELINE'] > 0
        assert 10.0 <= g['BASELINE'] <= 45.0
        assert g['LINESPREAD'] > 0
        assert g['page_px'] > 0


# #8 PN_RE vs is_page_number 字符集差异
class TestPNreVsIsPageNumber:
    """PN_RE 用 [·•.] 不含 ‧；v13 is_page_number 用 [·•‧] 认 ‧。"""

    def test_pn_re_no_ideographic_dot(self):
        # PN_RE（geom/classic 用）不认 ‧（U+2506）
        assert PN_RE.fullmatch('‧123') is None
        # 认 · 和 .
        assert PN_RE.fullmatch('·123') is not None

    def test_v13_is_page_number_accepts_ideographic(self, v13):
        # v13 is_page_number 认 ‧（字符集不同）
        assert v13['is_page_number']('‧123') is True
