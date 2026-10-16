#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskU：①OCR 把竖排引號读成汉字「一」的**源图墨迹形状判别** + ②`_trim_marks` 的引號字口径。

被测实现：`src/pipelines/build_vert.py`
  · §1.997 `_qfx_class` —— 墨块形状 -> dash(一) / open(﹁) / close(﹂) / None(不改)
  · §1.997 `_qfx_runbox` —— 墨块形状统计(w/h/vmax/vmed/hpos/vpos)
  · §1.976 `_trim_marks` ④ —— 文本首/末字是引號时**不剔**列首/列尾那条小墨

实测来源（wz7 源页 354 与全书 79 处判定，见 docs/vert_quote_toc_report.md）：
  · ﹁ 墨块 19.0x9.1pt，竖画在右端(vpos 0.94)、横画在顶端(hpos 0.07-0.11)
  · ﹂ 墨块 18.0-20.5x8.5-10.5pt，竖画在左端(vpos 0.04-0.11)、横画在底端(hpos 0.76-0.86)
  · 一  墨块 15-23x2.4-3.5pt（只有一条横线，墨高 = 笔画粗）
  · 并字长 run（「一」与下一字墨相碰）h≈0.87x字高 —— 必须排除（实测源页 30 的「一入」）

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_taskU.py -v
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_NS_BASE = dict(
    QFIX_MIN_RATIO=0.25, QFIX_W_RATIO=0.45, QFIX_VPOS=0.70, QFIX_HPOS=0.60,
    QFIX_MAX_RATIO=0.60,
    PUNCT_HANG={'。', '，', '、', '：', '；', '？', '！'},
    QFIX_QFAM=set('「」『』'),
)
_FUNCS = ['_qfx_class', '_qfx_runbox', '_trim_marks']


def _ns(**over):
    d = dict(_NS_BASE)
    d.update(over)
    return load('build_vert.py', _FUNCS, const_names=(), mocks=d)


def _ink_page(cols, W=200, H=400, scale=2):
    """构造源图墨迹布尔图: cols = [(x0pt, x1pt, [(top_pt, bot_pt)])]。"""
    import numpy as np
    m = np.zeros((int(H * scale), int(W * scale)), bool)
    for x0, x1, runs in cols:
        for t, b in runs:
            m[int(t * scale):int(b * scale), int(x0 * scale):int(x1 * scale)] = True
    return m


# ---------- A. 形状判别(§1.997 _qfx_class) ----------
class TestQfxClass:
    H_CHAR = 23.0

    def _st(self, w, h, vmax, hpos, vpos, vmed=1.5, hmed=3.0):
        return {'w': w, 'h': h, 'vmax': vmax, 'vmed': vmed, 'hmax': w, 'hmed': hmed,
                'vpos': vpos, 'hpos': hpos, 'x0': 0.0, 'x1': w}

    def test_dash_is_yi(self):
        """汉字「一」: 墨高 3.0 = 笔画厚(vmax 同值), 无竖画 -> dash(不改)。"""
        ns = _ns()
        assert ns['_qfx_class'](self._st(23.0, 3.0, 3.0, 0.43, 0.90), self.H_CHAR) == 'dash'

    def test_open_quote(self):
        """﹁(实测 wz7 p354): 19.7x9.1, 竖画右端 vpos 0.94, 横画顶端 hpos 0.10。"""
        ns = _ns()
        assert ns['_qfx_class'](self._st(19.7, 9.1, 9.1, 0.10, 0.94, vmed=1.44), self.H_CHAR) == 'open'

    def test_close_quote(self):
        """﹂(实测 wz7 p354): 18.0x9.8, 竖画左端 vpos 0.04, 横画底端 hpos 0.82。"""
        ns = _ns()
        assert ns['_qfx_class'](self._st(18.0, 9.8, 9.8, 0.82, 0.04, vmed=2.16), self.H_CHAR) == 'close'

    def test_merged_run_rejected(self):
        """并字长 run(「一」+下一字相碰, h=0.87x字高) -> None(实测源页 30「一入」误判来源)。"""
        ns = _ns()
        assert ns['_qfx_class'](self._st(21.5, 20.0, 20.0, 0.89, 0.30), self.H_CHAR) is None

    def test_punct_and_fragment_rejected(self):
        """逗号(4.5x7.4, 又小又窄) -> None; 碎墨(1x1) -> dash(墨高 < 0.25 字高, 不改)。"""
        ns = _ns()
        assert ns['_qfx_class'](self._st(4.5, 7.4, 7.4, 0.53, 0.48), self.H_CHAR) is None
        assert ns['_qfx_class'](self._st(1.0, 1.0, 1.0, 0.5, 0.5), self.H_CHAR) == 'dash'

    def test_ambiguous_shape_not_changed(self):
        """竖/横笔位置不构成直角形(vpos/hpos 都居中) -> None(**不改**): 判据宁少改不误改。
        例: 大字页里的「一」(字高 40pt, 墨高 12 已过 0.25 门槛, 但既非横线判定也非直角形)。"""
        ns = _ns()
        st = self._st(30.0, 12.0, 12.0, 0.5, 0.6, vmed=11.0)
        assert ns['_qfx_class'](st, 40.0) is None

    def test_none_shape(self):
        ns = _ns()
        assert ns['_qfx_class'](None, self.H_CHAR) is None
        assert ns['_qfx_class'](self._st(20, 9, 9, 0.5, 0.5), 0.0) is None


# ---------- B. 墨块形状统计(§1.997 _qfx_runbox) ----------
class TestQfxRunbox:
    def test_corner_shape(self):
        """一个「﹁」形墨块(横画 20x2 + 竖画 2x9 在右端) -> h≈9, vpos≈1, hpos≈0。"""
        import numpy as np
        ns = _ns()
        # 横画: y 0-2 全宽; 竖画: x 18-20, y 0-9
        ink = np.zeros((40, 40), bool)
        ink[0:2, 0:20] = True
        ink[0:9, 18:20] = True
        st = ns['_qfx_runbox'](ink, 0.0, 10.0, 0.0, 12.0, 2.0)
        assert st is not None
        assert abs(st['h'] - 4.5) < 0.6          # 9px / 2 = 4.5pt
        assert abs(st['w'] - 10.0) < 0.6
        assert st['vpos'] > 0.8                  # 竖画在右端
        assert st['hpos'] < 0.3                  # 横画在顶端

    def test_empty_window(self):
        ns = _ns()
        assert ns['_qfx_runbox'](np.zeros((40, 40), bool), 0.0, 10.0, 0.0, 10.0, 2.0) is None


# ---------- C. 引號字不剔(_trim_marks ④) ----------
class TestTrimMarksQuote:
    K = 22.5

    def test_leading_quote_kept(self):
        """文本首字是引號(OCR 读对) -> 列首那条小墨就是该引號自己的墨, **不剔**(列顶 330.5)。"""
        ns = _ns()
        keep = [(330.5, 340.0), (347.0, 371.0), (373.0, 397.0)]
        assert ns['_trim_marks'](keep, '「宿盡閒', self.K, 25.0) == (330.5, 397.0)

    def test_trailing_quote_kept(self):
        """文本末字是引號 -> 列尾小墨保留(列底 62.5)。"""
        ns = _ns()
        keep = [(0.0, 22.5), (25.0, 47.5), (52.0, 62.5)]
        assert ns['_trim_marks'](keep, '甲乙」', self.K, 25.0) == (0.0, 62.5)

    def test_double_quote_kept(self):
        ns = _ns()
        keep = [(330.5, 340.0), (347.0, 371.0), (373.0, 397.0)]
        assert ns['_trim_marks'](keep, '『宿盡閒', self.K, 25.0) == (330.5, 397.0)

    def test_quote_dropped_by_ocr_still_trimmed(self):
        """OCR 把引號**读丢**的列(文本首字是真汉字) -> 仍按旧口径剔除(列顶 347.0) —— ④ 只认文本侧。"""
        ns = _ns()
        keep = [(330.5, 340.0), (347.0, 371.0), (373.0, 397.0)]
        assert ns['_trim_marks'](keep, '宿盡閒', self.K, 25.0) == (347.0, 397.0)
