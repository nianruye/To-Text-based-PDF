#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""src/pipelines 纯函数单元测试。

约束：
- 纯 Python，不 import fitz/pymupdf，不调用 xelatex，不读文件系统。
- 通过 _loader.py 用 ast 提取目标函数到隔离 namespace，绕开模块顶层副作用。
- 不修改任何业务代码。

运行（pytest 装在系统 python，非 mineru venv）：
    /usr/bin/python3 -m pytest src/test/unit/ -v
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from _loader import load, MockT2S
from utils.tex_escape import escape_latex

import pytest

# 提取的业务函数源码中个别字符串含无效转义序列（如 \s 在非 raw 串里），
# 编译时触发 DeprecationWarning，属业务源码问题、与测试无关，全局静默。
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


# ----------------------------------------------------------------------
# fixtures：每个源文件提取一次（module 级缓存）
# ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def v13():
    """build_pdf_v13.py 纯函数。"""
    return load(
        'build_pdf_v13.py',
        func_names={'clean_text', 'normalize_text', 'escape_tex',
                    'escape_body', 'is_page_number', '_heading_core'},
        const_names={'_QUOTE_MAP', 'FN_CIRCLE'},
    )


@pytest.fixture(scope="module")
def classic():
    """build_classic.py 纯函数。esc 引用全局 FONT，注入固定值 10.0。"""
    return load(
        'build_classic.py',
        func_names={'_esc_chars', 'esc', '_math_to_plain', '_split_heading'},
        const_names={'_HEADING_PREFIX_RE'},
        mocks={'FONT': 10.0, 'escape_latex': escape_latex},
    )


@pytest.fixture(scope="module")
def geom():
    """build_geom.py 纯函数。_has_trad 引用全局 _t2s，注入 MockT2S（opencc 未装）。"""
    return load(
        'build_geom.py',
        func_names={'_heading_core', '_head_level', '_eff_chars', '_has_trad'},
        const_names={'_MARKER_RE', 'FN_CIRCLE'},
        mocks={'_t2s': MockT2S(), 'escape_latex': escape_latex, 'PUNCT_WEIGHT': 0.2},
    )


# ======================================================================
# build_pdf_v13.py
# ======================================================================

class TestCleanText:
    """clean_text(text)：去掉 text 左侧的竖线(|、‖)、空格、制表符。

    实现：text.lstrip("‖‖| \\t")，字符集含 ‖(U+2016)、|、空格、\\t。
    只去左侧，右侧不动。全角空格(U+3000)不在集合内。
    """

    @pytest.mark.parametrize("inp,exp", [
        ("‖第一章", "第一章"),
        ("|标题", "标题"),
        ("  缩进", "缩进"),
        ("\t制表", "制表"),
        ("标题‖", "标题‖"),       # 右侧不去
        ("‖|", ""),                # 全是可去字符
        ("", ""),                  # 空串
        ("　全角", "　全角"),       # 全角空格不去
        ("normal", "normal"),
    ])
    def test_clean_text(self, v13, inp, exp):
        assert v13['clean_text'](inp) == exp

    def test_clean_text_none_raises(self, v13):
        # None.lstrip -> AttributeError
        with pytest.raises(AttributeError):
            v13['clean_text'](None)


class TestNormalizeText:
    """normalize_text(text)：去所有空白 + 引号归一化。

    实现：re.sub(r'\\s+','',text) 再 translate(_QUOTE_MAP)。
    双引号(ASCII " / “ / ”) -> 统一为同一字符；单引号(‘ ’) -> ASCII '；、不变。
    """

    @pytest.mark.parametrize("inp,exp", [
        ("a b", "ab"),
        ("  ", ""),
        ("", ""),
        ("a\tb\nc", "abc"),
        ("、", "、"),
    ])
    def test_normalize_basic(self, v13, inp, exp):
        assert v13['normalize_text'](inp) == exp

    def test_normalize_quotes_unified(self, v13):
        # 所有双引号归一为同一种字符，单引号归一为 ASCII '，无空白
        out = v13['normalize_text']('“a” “b” ‘c’')
        assert ' ' not in out
        assert "'" in out                       # 单引号归一为 ASCII '
        double_quotes = [c for c in out if c in '“”"']
        assert len(set(double_quotes)) == 1     # 双引号全部统一为同一种

    def test_normalize_none_raises(self, v13):
        with pytest.raises(TypeError):
            v13['normalize_text'](None)


class TestEscapeTex:
    """escape_tex(text)：标准 LaTeX 转义，**保留** \\ { }。

    \\ -> \\textbackslash{}, { -> \\{, } -> \\}, & % # $ _ ~ ^ 各自转义。
    """

    @pytest.mark.parametrize("inp,exp", [
        ("a%b", "a\\%b"),
        ("a_b", "a\\_b"),
        ("{x}", "\\{x\\}"),
        ("100%", "100\\%"),
        ("$5", "\\$5"),
        ("a#b&c", "a\\#b\\&c"),
        ("plain", "plain"),
        ("中文", "中文"),
        ("", ""),
    ])
    def test_escape_tex(self, v13, inp, exp):
        assert v13['escape_tex'](inp) == exp

    def test_escape_tex_backslash(self, v13):
        # \\ -> \textbackslash{}，但其中的 {} 被后续 {/} 规则二次转义 -> \{\}
        assert v13['escape_tex']('a\\b') == r'a\textbackslash{}b'  # #2 修复：占位符防二次转义

    def test_escape_tex_none_raises(self, v13):
        with pytest.raises(AttributeError):
            v13['escape_tex'](None)


class TestEscapeBody:
    """escape_body(text)：escape_tex + 处理 $...$ 内联标记。

    $^{x}$ -> \\textsuperscript{x}（内容经 escape_tex）；
    $\\frac{a}{b}$ 等数学 -> 纯文本 a/b 后转义；孤立 $ -> \\$。
    """

    @pytest.mark.parametrize("inp,exp", [
        ("plain text", "plain text"),
        ("a%b", "a\\%b"),
        ("", ""),
    ])
    def test_escape_body_plain(self, v13, inp, exp):
        assert v13['escape_body'](inp) == exp

    def test_escape_body_superscript(self, v13):
        assert v13['escape_body']('a $^{[八五]}$ b') == 'a \\textsuperscript{[八五]} b'

    def test_escape_body_frac(self, v13):
        assert v13['escape_body']('$\\frac{1}{3}$') == '1/3'

    def test_escape_body_math_cmd(self, v13):
        assert v13['escape_body']('$\\alpha$') == 'alpha'

    def test_escape_body_isolated_dollar(self, v13):
        # 单个 $（无闭合 $...$）走 escape_tex，$ -> \$
        assert v13['escape_body']('price $5') == 'price \\$5'

    def test_escape_body_none_raises(self, v13):
        with pytest.raises(TypeError):
            v13['escape_body'](None)


class TestIsPageNumber:
    """is_page_number(t)：页码判定。

    正则 ^[·•‧]?\\s*\\d{1,4}\\s*[·•‧]?$ 命中，或纯 ^\\d{1,4}$ 且 len<=4。
    """

    @pytest.mark.parametrize("inp,exp", [
        ("123", True),
        ("12", True),
        ("1", True),
        ("·45·", True),
        ("  12  ", True),     # 前后空白
        ("12345", False),     # 5 位
        ("abc", False),
        ("12a", False),
        ("", False),
    ])
    def test_is_page_number(self, v13, inp, exp):
        assert v13['is_page_number'](inp) == exp

    def test_is_page_number_none_raises(self, v13):
        with pytest.raises(AttributeError):
            v13['is_page_number'](None)


# ======================================================================
# build_classic.py
# ======================================================================

class TestEscChars:
    """_esc_chars(s)：通用 LaTeX 转义，**删除** \\ { }。

    \\ -> ''，{ -> ''，} -> ''；% & # _ ^ ~ 转义为**单反斜杠**形式（\% 等）；○ -> 〇；【 -> 〔，】 -> 〕；圈码 ①..⑩ -> \\textcircled{N}
    （单反斜杠，来自 _CIRC）；省略号归一化：⋯⋯/⋯ -> …，…… -> ....，… -> .。
    """

    @pytest.mark.parametrize("inp,exp", [
        ("a%b", r"a\%b"),             # 转义为单反斜杠（修复双反斜杠 bug）
        ("{x}", "x"),                  # 花括号删除
        ("a\\b", "a\\b"),              # 单反斜杠保留（_esc_chars 只删双反斜杠 \\）
        (r"a\\b", "ab"),               # 双反斜杠 -> 删除
        ("○", "〇"),
        ("【注】", "〔注〕"),
        ("①", r"\textcircled{1}"),     # 圈码单反斜杠
        ("⑩", r"\textcircled{10}"),
        ("plain", "plain"),
        ("", ""),
        ("…", "."),                    # 省略号归一化为半角点
    ])
    def test_esc_chars(self, classic, inp, exp):
        assert classic['_esc_chars'](inp) == exp

    def test_esc_chars_none_raises(self, classic):
        with pytest.raises(AttributeError):
            classic['_esc_chars'](None)


class TestEsc:
    """esc(t)：_esc_chars + $...$ 上标/数学 + 裸 [X] 校注上标。

    上标用 \\makebox+\\smash+\\raisebox+\\fontsize 渲染（字号由全局 FONT ×
    MARKER_SCALE 决定，此处 FONT 注入固定 10.0，MARKER_SCALE 默认 0.55）。
    行首 [X] -> 〔X〕 序号（不上标）；行中 [X]（前有文字）-> 上标。
    """

    @pytest.mark.parametrize("inp,exp", [
        ("plain 文本", "plain 文本"),
        ("a%b_c", r"a\%b\_c"),
        ("{x}", "x"),
        ("", ""),
    ])
    def test_esc_plain(self, classic, inp, exp):
        assert classic['esc'](inp) == exp

    def test_esc_frac(self, classic):
        assert classic['esc']('$\\frac{1}{3}$') == '1/3'

    def test_esc_superscript_marker(self, classic):
        # $^{[八五]}$ -> 上标，[八五] -> 〔八五〕，makebox/smash/fontsize
        out = classic['esc']('$^{[八五]}$')
        assert '〔八五〕' in out
        assert '\\makebox' in out
        assert '\\fontsize' in out
        assert '$' not in out and '^' not in out

    def test_esc_bare_marker_inline(self, classic):
        # 行中裸 [二]（前有文字）-> 上标 〔二〕
        out = classic['esc']('始元六年[二]')
        assert '〔二〕' in out
        assert '\\makebox' in out
        assert '[二]' not in out

    def test_esc_line_start_bracket_not_superscript(self, classic):
        # 行首 [一] -> 〔一〕 序号（不上标，无 makebox）
        out = classic['esc']('[一]正文')
        assert out.startswith('〔一〕')
        assert '\\makebox' not in out

    def test_esc_none_raises(self, classic):
        with pytest.raises(TypeError):
            classic['esc'](None)


class TestMathToPlain:
    """_math_to_plain(m)：$...$ 内数学 -> 纯文本。

    \\frac{a}{b} -> a/b；\\command -> command；残余花括号去掉。
    入参是正则 match 对象（group(1) 为 $...$ 内容）。
    """

    @staticmethod
    def _match(inner):
        return re.search(r'\$([^$]*)\$', '$' + inner + '$')

    @pytest.mark.parametrize("inner,exp", [
        ("\\frac{1}{3}", "1/3"),
        ("\\frac{ab}{cd}", "ab/cd"),
        ("\\alpha", "alpha"),
        ("{a}", "a"),
        ("\\sqrt{x}", "sqrtx"),     # \command 去反斜杠 + 残余花括号去掉
        ("plain", "plain"),
    ])
    def test_math_to_plain(self, classic, inner, exp):
        assert classic['_math_to_plain'](self._match(inner)) == exp


class TestSplitHeading:
    """_split_heading(t)：拆标题序号前缀 -> (前缀, 剩余)。

    匹配 第X部分/章/节/编/篇、(一)/一、1. 等；中文数字后接 百/千/万/亿 不匹配。
    不匹配则返回 ('', t)。
    """

    @pytest.mark.parametrize("inp,pre,rest", [
        ("第一部分 引言", "第一部分", "引言"),
        ("（一）概述", "（一）", "概述"),
        ("1. 标题", "1.", "标题"),
        ("正文无序号", "", "正文无序号"),
        ("一百", "", "一百"),        # lookahead 排除（一后接百）
        ("", "", ""),
    ])
    def test_split_heading(self, classic, inp, pre, rest):
        assert classic['_split_heading'](inp) == (pre, rest)

    def test_split_heading_none_raises(self, classic):
        with pytest.raises(AttributeError):
            classic['_split_heading'](None)


# ======================================================================
# build_geom.py
# ======================================================================

class TestHeadingCoreGeom:
    """_heading_core(t) [geom]：剥编号/括号/leader点，末步去空白。

    不调 normalize_text（引号不归一化），与 v13 版行为不同。
    """

    @pytest.mark.parametrize("inp,exp", [
        ("第一部分 引言", "引言"),
        ("（一）概述", "概述"),
        ("[引言]", "引言"),
        ("1. 标题", "标题"),
        ("标题  文本", "标题文本"),
        ("", ""),
    ])
    def test_heading_core(self, geom, inp, exp):
        assert geom['_heading_core'](inp) == exp

    def test_heading_core_keeps_quotes(self, geom):
        # geom 不归一化引号，ASCII " 原样保留
        assert geom['_heading_core']('"引"言') == '"引"言'

    def test_heading_core_none_raises(self, geom):
        with pytest.raises(AttributeError):
            geom['_heading_core'](None)


class TestHeadLevelGeom:
    """_head_level(t, is_big) [geom]：标题分级。

    is_big -> 'part'；t[0] 为数字或 [【(（ -> 'section'；否则 'title'。
    geom 版**无附录判定**（classic 版 L76 才有），故 '附录五' -> 'title'。
    空串/None 因 ``t and`` 短路兜底为 'title'，不抛异常。
    """

    @pytest.mark.parametrize("t,is_big,exp", [
        ("第一部分", True, "part"),
        ("1 标题", False, "section"),
        ("[引言]", False, "section"),
        ("（一）", False, "section"),
        ("引言", False, "title"),
        ("附录五", False, "title"),      # geom 无附录判定（与 classic 不同）
    ])
    def test_head_level(self, geom, t, is_big, exp):
        assert geom['_head_level'](t, is_big) == exp

    def test_head_level_empty_fallback(self, geom):
        assert geom['_head_level']('', False) == 'title'

    def test_head_level_none_fallback(self, geom):
        # None and ... 短路，兜底 'title'，不抛异常
        assert geom['_head_level'](None, False) == 'title'


class TestEffChars:
    """_eff_chars(t, pw=PUNCT_WEIGHT)：有效字数。

    先剥校注标记 _MARKER_RE（$^{[X]}$ / 裸 [X]），再统计：
    CJK 字(ord>0x2e80)=1.0，标点/拉丁/数字=pw（默认 PUNCT_WEIGHT=0.2）。
    """

    @pytest.mark.parametrize("inp,exp", [
        ("中文", 2.0),
        ("abc", 0.6),                  # 3 × 0.2
        ("a中b", 1.4),                 # 0.2+1+0.2
        ("中$^{[八五]}$文", 2.0),       # 校注标记剥掉
        ("[八五]文", 1.0),              # 行首 [八五] 标记剥掉，剩 1 CJK
        ("", 0),
    ])
    def test_eff_chars_default(self, geom, inp, exp):
        assert geom['_eff_chars'](inp) == pytest.approx(exp)

    def test_eff_chars_custom_pw(self, geom):
        assert geom['_eff_chars']('abc', 0.5) == 1.5
        assert geom['_eff_chars']('abc', 0.0) == 0.0
        assert geom['_eff_chars']('中文', 0.0) == 2.0   # CJK 不受 pw 影响

    def test_eff_chars_none_raises(self, geom):
        with pytest.raises(TypeError):
            geom['_eff_chars'](None)


class TestHasTrad:
    """_has_trad(t)：_t2s.convert(t) != t 判断是否含繁体。

    _t2s 为 MockT2S（opencc 未安装），内置繁->简字典。繁体字经 convert 后
    变化 -> True；纯简体/ASCII -> False。
    """

    @pytest.mark.parametrize("inp,exp", [
        ("書", True),
        ("书", False),
        ("書論", True),
        ("中文", False),
        ("abc", False),
        ("", False),
        ("马", False),
    ])
    def test_has_trad(self, geom, inp, exp):
        assert geom['_has_trad'](inp) == exp

    def test_has_trad_none_raises(self, geom):
        # MockT2S.convert 用 str.translate，None.translate -> AttributeError
        with pytest.raises(AttributeError):
            geom['_has_trad'](None)


# ======================================================================
# 跨文件对比测试：功能相似函数的差异
# ======================================================================

class TestCrossFuncDivergence:
    """对比功能相似的函数：相同输入 -> 输出是否一致，不一致的差异在哪。"""

    @pytest.mark.parametrize("inp", [
        "{x}", "a\\b", "○", "【注】", "a%b", "plain", "#",
    ])
    def test_escape_tex_vs_esc_chars(self, v13, classic, inp):
        """escape_tex(v13) vs _esc_chars(classic)。

        核心差异：
        - { }：v13 保留并转义（\\{），classic 删除。
        - \\：v13 单反斜杠 -> \\textbackslash\\{\\}（含二次转义）；classic 单反斜杠保留、双反斜杠删除。
        - ○：v13 不变，classic -> 〇。
        - 【】：v13 不变，classic -> 〔〕。
        - % # _ & 等：v13 单反斜杠转义（\\%），classic 双反斜杠（\\\\%）-> 不一致。
        - plain：两者一致。
        """
        a = v13['escape_tex'](inp)
        b = classic['_esc_chars'](inp)
        if inp == "{x}":
            assert a == r"\{x\}" and b == "x"
        elif inp == "a\\b":
            # v13 单反斜杠 -> \textbackslash\{\}；classic 单反斜杠保留 -> a\b
            assert a == r"a\textbackslash{}b" and b == r"a\b" and a != b  # #2 修复：不再二次转义
        elif inp == "○":
            assert a == "○" and b == "〇"
        elif inp == "【注】":
            assert a == "【注】" and b == "〔注〕"
        elif inp == "a%b":
            # v13 单反斜杠 \%, classic 双反斜杠 \\% -> 不一致
            assert a == r"a\%b" and b == r"a\%b"  # classic 修复后与 v13 一致
        elif inp == "plain":
            assert a == "plain" and b == "plain"          # 一致
        elif inp == "#":
            # v13 单反斜杠 \#, classic 双反斜杠 \\# -> 不一致
            assert a == r"\#" and b == r"\#"  # classic 修复后与 v13 一致

    def test_heading_core_v13_vs_geom_no_quote(self, v13, geom):
        """无引号时 v13 与 geom 的 _heading_core 一致（都剥编号+去空白）。"""
        for inp in ("第一部分 引言", "（一）概述", "标题  文本"):
            assert v13['_heading_core'](inp) == geom['_heading_core'](inp)

    def test_heading_core_v13_vs_geom_quote_diverges(self, v13, geom):
        """含弯引号时两者分叉：v13 经 normalize_text 归一化（“ ” -> "），geom 不动。

        v13 _heading_core 末步调 normalize_text（引号归一+去空白）；
        geom 末步只 re.sub(\\s+)（引号原样）。故含弯引号输入两者输出不同。
        注：ASCII " 在 _QUOTE_MAP 里是 identity，必须用弯引号才能体现差异。
        """
        inp = '“引”言'   # 弯引号 U+201C / U+201D
        a = v13['_heading_core'](inp)
        b = geom['_heading_core'](inp)
        assert b == inp                       # geom 不改引号
        assert a != b                         # v13 归一化引号 -> 不等
        assert a != inp


# ======================================================================
# 超长输入（spec 超长输入节）：10000+ 字符不抛异常，按字符线性处理
# ======================================================================

class TestLongInput:
    """超长字符串不抛异常（Python 字符串无长度限制，转义/正则/统计线性处理）。"""

    LONG = "a%b_中文" * 2000   # 12000 字符

    def test_clean_text_long(self, v13):
        assert v13['clean_text'](self.LONG) == self.LONG    # 无左侧可去字符

    def test_normalize_text_long(self, v13):
        assert len(v13['normalize_text'](self.LONG)) > 0

    def test_escape_tex_long(self, v13):
        out = v13['escape_tex'](self.LONG)
        assert '\\%' in out and '\\_' in out                # 转义生效

    def test_escape_body_long(self, v13):
        assert len(v13['escape_body'](self.LONG)) > 0

    def test_is_page_number_long(self, v13):
        assert v13['is_page_number']('1' * 10000) is False  # 超 4 位

    def test_esc_chars_long(self, classic):
        out = classic['_esc_chars'](self.LONG)
        assert '\%' in out                               # 双反斜杠转义

    def test_esc_long(self, classic):
        assert len(classic['esc'](self.LONG)) > 0

    def test_split_heading_long(self, classic):
        pre, rest = classic['_split_heading'](self.LONG)
        assert isinstance(rest, str)

    def test_heading_core_long(self, geom):
        assert isinstance(geom['_heading_core'](self.LONG), str)

    def test_head_level_long(self, geom):
        assert geom['_head_level'](self.LONG, False) in ('section', 'title')

    def test_eff_chars_long(self, geom):
        assert geom['_eff_chars'](self.LONG) > 0

    def test_has_trad_long(self, geom):
        assert isinstance(geom['_has_trad'](self.LONG), bool)
