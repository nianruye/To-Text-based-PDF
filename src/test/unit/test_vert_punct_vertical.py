#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskK：竖排括号形态（§1.0c）+ OCR 列拆分归位（§1.0d）的纯函数测试。

被测实现：`src/pipelines/build_vert.py`
  · §1.0c `VERT_FORMS` / `VERT_METRICS` / `BR_SIZE` / `_br_put` —— 括号 -> 竖排码位 + 字号 + 墨心回格心
  · §1.0d `BR_OPEN_OF` / `fix_split_brackets`        —— 行首闭括号归位上一列（竖排禁则）
  · §1.0a `_put_tex`                                  —— 括号经 §1.0c 后仍不得引入 scalebox/btrans/etrans
用 _loader 从脚本里 ast 提取纯函数（不 import fitz / 不跑 upLaTeX）。

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_punct_vertical.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_CONSTS = ['VERT_FORMS', 'VERT_METRICS', 'BR_ON', 'BR_SIZE_DEF', 'BR_SIZE', 'BR_OPEN_OF',
           'XSCALE', 'PT2BP', 'PAGE_ORIGIN_BP', 'INK_RATIO',
           # taskL: _put_tex 现在会调 _vb(墨迹加粗包装) —— 提取它及其常量(默认关闭, 本文件断言不受影响)
           'BOLD_W']
_FUNCS = ['_br_put', 'fix_split_brackets', '_put_tex', '_esc_ch', '_vb']


@pytest.fixture(scope='module')
def ns():
    return load('build_vert.py', _FUNCS, _CONSTS)


# ---------- A. 形态表 ----------
class TestVertForms:
    def test_all_mapped_codepoints_have_metrics(self, ns):
        """每个横排括号都映射到竖排码位，且该码位在 VERT_METRICS 里有墨迹参数（否则摆位会 KeyError）。"""
        VF, VM = ns['VERT_FORMS'], ns['VERT_METRICS']
        assert len(VF) >= 10
        for k, v in VF.items():
            assert len(k) == 1 and len(v) == 1
            assert v in VM, '缺 %s 的墨迹参数' % v

    def test_metrics_are_plausible(self, ns):
        """墨迹宽高 ∈ (0,1) em、墨心 ∈ (0,1) em、且宽高与「墨心 ± 半宽高」自洽。"""
        for g, (w, h, cx, cy) in ns['VERT_METRICS'].items():
            assert 0.2 < w < 1.0 and 0.1 < h < 0.6, g
            assert 0.0 < cx < 1.0 and 0.0 < cy < 1.0, g

    def test_open_close_pairs_are_mirrored(self, ns):
        """开口形墨心在 em 盒下半（cy 小）、闭口形在上半（cy 大）—— 源书实测的配对设计。"""
        VM = ns['VERT_METRICS']
        for a, b in [('︵', '︶'), ('﹁', '﹂'), ('﹃', '﹄'), ('︗', '︘'), ('︹', '︺'), ('︽', '︾')]:
            assert VM[a][3] < 0.3 < VM[b][3], (a, b)
            # 同族开/闭形的墨宽墨高一致（源书同款字形镜像）
            assert abs(VM[a][0] - VM[b][0]) < 0.01 and abs(VM[a][1] - VM[b][1]) < 0.01

    def test_bracket_size_smaller_than_body(self, ns):
        """竖排括号字号 < 正文（源书实测括号墨高仅约 0.23 倍字高）。"""
        assert 0.4 <= ns['BR_SIZE_DEF'] <= 0.9
        for v in ns['BR_SIZE'].values():
            assert 0.3 <= v <= 0.9


# ---------- B. _br_put ----------
class TestBrPut:
    def test_bracket_maps_to_vertical_form(self, ns):
        """（ -> ︵，字号 ×BR_SIZE_DEF，且 x/y 按墨心校正。"""
        g, F2, x2, y2 = ns['_br_put']('（', 100.0, 200.0, 34.4, xs=0.87)
        assert g == '︵'
        assert F2 == pytest.approx(round(34.4 * ns['BR_SIZE_DEF'], 1))
        w, h, cx, cy = ns['VERT_METRICS']['︵']
        assert x2 == pytest.approx(100.0 + 0.87 * (34.4 / 2 - cx * F2))
        assert y2 == pytest.approx(200.0 + 34.4 / 2 - cy * F2)

    def test_open_close_shift_directions(self, ns):
        """开口形墨心在盒底 -> 需上移更多；闭口形墨心在盒顶 -> 上移很少（两者差 ~13pt @34.4pt）。"""
        _g1, _f1, _x1, y_open = ns['_br_put']('（', 0.0, 0.0, 34.4, xs=0.87)
        _g2, _f2, _x2, y_close = ns['_br_put']('）', 0.0, 0.0, 34.4, xs=0.87)
        assert y_open > y_close                      # \put y 自页底起算: 值大 = 更靠上
        assert (y_open - y_close) == pytest.approx(
            (ns['VERT_METRICS']['︶'][3] - ns['VERT_METRICS']['︵'][3])
            * round(34.4 * ns['BR_SIZE_DEF'], 1), abs=0.05)

    def test_non_bracket_untouched(self, ns):
        """非括号字符原样返回（不动既有行为: 正文/标点挤格路径必须一字不变）。"""
        for ch in ('國', '。', '，', 'A', '　', '一'):
            assert ns['_br_put'](ch, 12.5, 34.5, 33.3) == (ch, 33.3, 12.5, 34.5)

    def test_type_specific_size(self, ns):
        """【】〔〕 源书实测更小 -> 字号低于默认（表里有分类型覆盖）。"""
        _g, F2, _x, _y = ns['_br_put']('【', 0.0, 0.0, 34.4)
        assert F2 < round(34.4 * ns['BR_SIZE_DEF'], 1)

    def test_disable_flag_keeps_original(self, ns):
        """VERT_BR=0 时必须完全等价于旧行为（回退对照用）。"""
        ns['BR_ON'] = False
        try:
            assert ns['_br_put']('（', 10.0, 20.0, 30.0) == ('（', 30.0, 10.0, 20.0)
        finally:
            ns['BR_ON'] = True


# ---------- C. _put_tex 集成（含 taskJ2 回归锁） ----------
class TestPutTexBracket:
    def test_put_tex_emits_vertical_form(self, ns):
        s = ns['_put_tex']('（', 100.0, 200.0, 34.4)
        assert '︵' in s and '（' not in s
        assert '\\fontsize{%.1fpt}' % round(34.4 * ns['BR_SIZE_DEF'], 1) in s

    def test_put_tex_bracket_no_scalebox_leak(self, ns):
        """taskJ2 回归锁: 括号路径同样不得出现 scalebox/btrans/etrans（只用 q/cm/Q 与竖排码位）。"""
        s = ns['_put_tex']('（', 100.0, 200.0, 34.4)
        for bad in ('scalebox', 'btrans', 'etrans', 'x:scale'):
            assert bad not in s
        assert '\\special{pdf:literal direct q 0.87 0 0 1 0 0 cm}' in s

    def test_put_tex_plain_char_unchanged(self, ns):
        """普通字与 taskJ2 实测串逐字相同（无回归）。"""
        s = ns['_put_tex']('國', 100.0, 200.0, 34.4, xs=0.87)
        assert s.startswith('\\put(104.6,200.7){')
        assert '\\fontsize{34.4pt}{34.4pt}\\selectfont 國' in s


# ---------- D. 列拆分归位 ----------
class TestFixSplitBrackets:
    def test_moves_leading_closer_to_prev_row(self, ns):
        """p3 实例: 行首「）」+ 上一行有未闭合「（」 -> 归位上一行行尾。"""
        rows = ['論持久戰', '（一九三八年五月', '）問題的提起', '全民族的']
        out, fx = ns['fix_split_brackets'](rows)
        assert out[1] == '（一九三八年五月）'
        assert out[2] == '問題的提起'
        assert fx == [(2, '）')]

    def test_keeps_total_char_count(self, ns):
        """页内字符总量守恒（不影响 verify_vert 逐页字符量口径）。"""
        rows = ['（一九三八年五月', '）問題的提起', '（一）偉大']
        out, _fx = ns['fix_split_brackets'](rows)
        assert sum(len(t) for t in out) == sum(len(t) for t in rows)

    def test_no_opener_no_move(self, ns):
        """页内没有未闭合的同类开括号 -> 不动（可能是真·跨列引语/OCR 重复，不能瞎搬）。"""
        rows = ['講演錄』一書摘要', '』（三）「一勞資']
        out, fx = ns['fix_split_brackets'](rows)
        assert out == rows and fx == []

    def test_first_row_not_moved(self, ns):
        rows = ['）開頭', '（後面']
        out, fx = ns['fix_split_brackets'](rows)
        assert out == rows and fx == []

    def test_quote_pair(self, ns):
        """「」同规则: p43 实例（行首 」 且上一行有未闭合 「）。"""
        rows = ['主張妥協者的根據就是「先生之志則大矣', '」先生的看法則不']
        out, fx = ns['fix_split_brackets'](rows)
        assert out[0].endswith('」') and out[1] == '先生的看法則不'
        assert len(fx) == 1

    def test_two_closers_in_one_row(self, ns):
        """一行连开两个闭括号（p155「」）」实例）-> 按栈序各归位一次。"""
        rows = ['與黨的任務的決定（甲「乙', '」）這些就是結論']
        out, _fx = ns['fix_split_brackets'](rows)
        assert out[0] == '與黨的任務的決定（甲「乙」）'
        assert out[1] == '這些就是結論'

    def test_nested_balance_not_broken(self, ns):
        """已平衡的行不受影响（无副作用）。"""
        rows = ['（一）偉大抗日戰爭', '「引語」後面', '結尾']
        out, fx = ns['fix_split_brackets'](rows)
        assert out == rows and fx == []
