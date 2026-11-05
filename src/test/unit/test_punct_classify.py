#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QSF 补引号判据 + 标点归因分类器 单测（battle3 / t13）。

QSF 的三个纯判据函数在 src/pipelines/build_vert.py 里，但该文件 import 即执行整本书的构建
（argparse + 10 分钟渲染），不能直接 import。这里用 AST 抽取目标函数、在受控 globals 里 exec ——
只测纯函数，不触发构建。

覆盖的 bug 场景（battle2 B 类）：
  ① 双 ﹂﹂：文本层该对引号已闭合（`「甲。」`）时不得再补；
  ② p620「！」后漏识 `﹂`：末字是 ！且本列没有引号字符（引号开在别的列）时要允许补；
  ③ 「：﹂」/「西﹂門」：源墨 run 在列中段（离末字 > 2.5 步进）时位置闸门必须拒绝；
  ④ 「一 -> ﹂」1:1 替换仍保留；
  ⑤ A/B 源位置闸门（punct_classify.boundary_ok）与 OCR 误读「一」修复（misread_fix_ok）。
"""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BUILD_VERT = ROOT / 'src' / 'pipelines' / 'build_vert.py'


def _load_qsf():
    """从 build_vert.py 抽取 QSF 纯函数（不执行模块顶层代码）。"""
    src = BUILD_VERT.read_text(encoding='utf-8')
    tree = ast.parse(src)
    want = {'_qsf_pairs_state', '_qsf_decide', '_qsf_pos_ok'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in want]
    assert {n.name for n in nodes} == want, 'QSF 纯函数缺失: %r' % (want - {n.name for n in nodes})
    g = {
        'QSF_APPEND': True, 'QSF_PAIR_GUARD': True, 'QSF_POS_TOL': 2.5,
        '_qsf_stat': {'pair_skip': 0},
        '_QSF_OPENERS': set('「﹁『﹃'), '_QSF_CLOSERS': set('」﹂』﹄'),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(BUILD_VERT), 'exec'), g)
    return g


QSF = _load_qsf()


class TestQsfPureJudge:
    def test_pair_state_closed(self):
        assert QSF['_qsf_pairs_state']('「甲。」') == (0, True)

    def test_pair_state_open(self):
        assert QSF['_qsf_pairs_state']('「甲。') == (1, True)

    def test_pair_state_no_quote(self):
        # p620 型：本列只有「！」、引号开在别的列 -> 不能因「无引号」就判成已闭合
        assert QSF['_qsf_pairs_state']('你撇的人有上稍來沒下稍！') == (0, False)

    def test_decide_skips_closed_pair(self):
        # ① 双 ﹂﹂：本列引号已闭合 -> 不得再补
        assert QSF['_qsf_decide']('。', 'corner', 'ring', '「甲。」') is None

    def test_decide_appends_after_bang_cross_column(self):
        # ② p620：末字 ！+ 本列无引号（引号跨列）-> 允许补
        assert QSF['_qsf_decide']('！', 'corner', 'other', '你撇的人有上稍來沒下稍！') == 'append'

    def test_decide_appends_after_bang_open_pair(self):
        assert QSF['_qsf_decide']('！', 'corner', 'other', '「甲！') == 'append'

    def test_decide_skips_bang_closed_pair(self):
        assert QSF['_qsf_decide']('！', 'corner', None, '「甲！」') is None

    def test_decide_keeps_yi_replace(self):
        # ④ OCR 把引号读成「一」-> 1:1 替换仍保留（taskCM 口径）
        assert QSF['_qsf_decide']('一', 'corner', None, '甲') == 'replace'

    def test_decide_period_without_ring_replaces(self):
        assert QSF['_qsf_decide']('。', 'corner', 'other', '甲') == 'replace'

    def test_pos_gate_accepts_tail_ink(self):
        # top=300, n=40, step=25 -> 末字 y=1275；源墨 y=1250 在末字附近（2.5 步进内）
        assert QSF['_qsf_pos_ok'](1250.0, 300.0, 40, 25.0) is True

    def test_pos_gate_rejects_mid_column_ink(self):
        # ③ 源墨 y=800 在列中段（比末字高 19 步进）-> 拒绝，防「：﹂」/「西﹂門」
        assert QSF['_qsf_pos_ok'](800.0, 300.0, 40, 25.0) is False

    def test_pos_gate_empty_column(self):
        assert QSF['_qsf_pos_ok'](100.0, 300.0, 0, 25.0) is False


class TestClassifyGate:
    """punct_classify 的源位置闸门（battle2 F1 回归）。"""

    @classmethod
    def setup_class(cls):
        pytest.importorskip('fitz')
        sys.path.insert(0, str(ROOT / 'src' / 'tools'))
        import punct_classify
        cls.pc = punct_classify

    def test_boundary_ok_source_line_start(self):
        assert self.pc.boundary_ok('start', '，恰與此同（見', ['，恰與此同（見金石']) is True

    def test_boundary_rejects_char_mid_line(self):
        # F1：字符在 OCR 行中间 -> 不是源行首 -> B
        assert self.pc.boundary_ok('start', '，恰與此同（見', ['金文耒彝作“”，恰與此同']) is False

    def test_boundary_ok_end(self):
        assert self.pc.boundary_ok('end', '……百年情。', ['「色膽如天怕甚事，鴛幃雲雨百年情。']) is True

    def test_misread_fix_yi_to_quote(self):
        # OCR 把列首 ﹁ 读成「一」-> 渲染端改回引号 -> C_fixed（不计 B）
        assert self.pc.misread_fix_ok('start', '「悶把幃屏來靠', ['一悶把幃屏來靠，和衣強睡倒。']) is True


class TestNonbodyFilter:
    """t16/F1：版權/印刷信息页过滤器收紧（多关键词 + 页型/版式特征；横排默认 include）。

    回归页（t14 实测误伤）：
      · wz4 p138/p190（正文页，含「出版」等词）
      · wz1 p30（正文页）
      · wz7 p82（註文「出版與研究半月刊/時報文化出版公司出版」）/ p915（经文「印刷」×3）
    这些页都必须 _is_nonbody_page == False；只有 p554/p1163 型短行版權页才是 True。
    """

    @classmethod
    def setup_class(cls):
        pytest.importorskip('fitz')
        sys.path.insert(0, str(ROOT / 'src' / 'tools'))
        import punct_audit
        cls.pa = punct_audit

    @staticmethod
    def _lines(texts):
        return [{'text': t} for t in texts]

    def test_colophon_page_vertical(self):
        lines = self._lines(['發行人：張三', '印刷：某印刷廠', '製版：某製版公司',
                             '帳戶：１２３４５６', '電話：０２－２７００', '地址：台北市'])
        assert self.pa._is_nonbody_page(lines, 'v') is True

    def test_horizontal_default_includes(self):
        # 横排默认不启用过滤器（「横排默认 include」）—— 即使长得像版權頁也返回 False
        lines = self._lines(['發行人：張三', '印刷：某印刷廠', '製版：某製版公司', '帳戶：１２３'])
        assert self.pa._is_nonbody_page(lines, 'h') is False

    def test_body_page_with_publish_words(self):
        # wz4 p138/p190、wz1 p30 型：正文长行提到「出版/印刷」-> 不能当版权页
        lines = self._lines(['……无產階級專政’”。③这个思想的表述，给无产阶級專政提供了理论依据……',
                             '……人民出版社出版，新華書店發行，二〇一六年第一版……'])
        assert self.pa._is_nonbody_page(lines, 'v') is False

    def test_wz7_p82_p915_body_pages(self):
        # p82 註文（出版與研究半月刊 / 時報文化出版公司出版）与 p915（经文「印刷」×3）都是正文页
        p82 = self._lines(['……《出版與研究半月刊》第 12 期，時報文化出版公司出版，一九九〇年……]'])
        p915 = self._lines(['……印刷術傳入歐洲後，印刷工人與印刷所的公會制度逐漸形成，……]'])
        assert self.pa._is_nonbody_page(p82, 'v') is False
        assert self.pa._is_nonbody_page(p915, 'v') is False

    def test_short_page_with_few_keywords_not_skipped(self):
        lines = self._lines(['發行人：張三', '電話：０２'])
        assert self.pa._is_nonbody_page(lines, 'v') is False

    def test_many_lines_not_skipped(self):
        lines = self._lines(['發行', '印刷', '製版'] + ['短行'] * 25)
        assert self.pa._is_nonbody_page(lines, 'v') is False


class TestMarkRowPick:
    """t16/F2：末行行盒选择 —— OCR 尾误读「一/0/〇」也要能匹配（p1365 假 B 的根因）。"""

    @classmethod
    def setup_class(cls):
        pytest.importorskip('fitz')
        sys.path.insert(0, str(ROOT / 'src' / 'tools'))
        import punct_classify
        cls.pc = punct_classify

    def test_misread_yi_tail(self):
        # p1365：OCR `…自防。一`（引号误读成一），产品 `…自防。﹂` -> 必须选中该行
        assert self.pc._pick_mark_row('……不若病前能自防。﹂', ['……不若病前能自防。一']) == 0

    def test_misread_yi_tail_not_fallback(self):
        # p1365 实况（R2 加强）：产品列 = 两 OCR 行合并 `與其病後能求藥，不若病前能自防。﹂`；
        # 真末行是第 2 行且尾随误读「一」。旧后缀候选（原样/剥句末标点）全不中 → 回退「最相似行」
        # 选中第 1 行（错）；新逻辑剥「一」后命中第 2 行。本用例在回退旧实现时必红。
        rows = ['與其病後能求藥，', '不若病前能自防。一']
        assert self.pc._pick_mark_row('與其病後能求藥，不若病前能自防。﹂', rows) == 1

    def test_misread_zero_tail(self):
        assert self.pc._pick_mark_row('……百年情。﹂', ['……百年情。〇']) == 0

    def test_plain_period_tail(self):
        assert self.pc._pick_mark_row('……百年情。﹂', ['……百年情。']) == 0

    def test_prefers_last_row_box(self):
        rows = ['上一行文字', '……不若病前能自防。']
        assert self.pc._pick_mark_row('……不若病前能自防。﹂', rows) == 1

    def test_product_tail_closer_stripped(self):
        assert self.pc._pick_mark_row('「甲」乙。﹂', ['「甲」乙。']) == 0
