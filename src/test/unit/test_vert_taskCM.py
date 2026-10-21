#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskCM：列尾闭引号 ﹂ 被 OCR 读成「。」/「一」的格位形状纠错（§1.998）。

被测实现：`src/pipelines/build_vert.py`
  · `_qsf_analyze` / `_qsf_classify` —— 单字形墨迹 -> bar/corner/ring/other（阈值 = 8 个
    已标真值反推值，见 tmp_vert/cj5/shape_clf2.py，**不许改**）
  · `_qsf_decide` —— 尾格形状 + 文本末字 -> replace/append/None
  · `_qsf_col_xrun` / `_qsf_runs_wide` / `_qsf_tail_runs` / `_qsf_run_feat` / `_qsf_pick_tail`
    —— 取样：先按「离槽中心最近的墨迹 x-run」认列（槽格有整列偏移），再在列内取 y-run，
    从下往上找第一条小墨，裁成单字形后分类
  · `_qsf_plan` —— 运行入口（QSF_ON 开关 + 统计 + 日志）

实测来源（wz7 源页 444，600dpi 灰度图，见 tmp_vert/cj5/quote_shape_truth.json）：
  · ﹂ 墨迹 19.5-20.5 x 8.5-9.5pt，四角极差 0.72-0.76、中心 0.00（直角）
  · 。 墨迹 7.5 x 7.0pt，四角极差 0.15-0.19、中心 0.03（圆环）
  · 一 墨迹 22.5 x 3.0pt，宽高比 7.5（长横）

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_taskCM.py -v
"""
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_FUNCS = ['_qsf_analyze', '_qsf_classify', '_qsf_decide', '_qsf_run_feat',
          '_qsf_pick_tail', '_qsf_runs_wide', '_qsf_tail_runs', '_qsf_col_xrun',
          '_qsf_win_x', '_qsf_plan', '_slot_runs', '_runs']
_CONSTS = ['QSF_ON', 'QSF_DBG', 'QSF_APPEND', 'QSF_MIN_PIX', 'QSF_MIN_RUN', 'QSF_TAIL_DN',
           'QSF_BAR_AR', 'QSF_BAR_H', 'QSF_CORNER_SPREAD', 'QSF_CORNER_MAX',
           'QSF_CORNER_CTR', 'QSF_RING_CTR', 'QSF_RING_EDGE', 'QSF_PAD_X', 'QSF_MIN_GLYPH',
           'QSF_MIN_W', 'QSF_MAX_W', 'QSF_MIN_AR', 'QSF_MAX_AR',
           '_qsf_stat', '_qsf_log']
_SC = 2.0


def _ns(ink=None, **over):
    """提取被测函数到隔离 namespace；ink 供 _qsf_plan 的 _frame_ink mock。"""
    mocks = {'page_h': 200.0, '_NF': {'on': True}, 'src_doc': object()}
    if ink is not None:
        mocks['_frame_ink'] = lambda pi, g: ink
    mocks.update(over)
    return load('build_vert.py', _FUNCS, const_names=_CONSTS, mocks=mocks)


def _blank(w=120, h=200, sc=_SC):
    return np.zeros((int(h * sc), int(w * sc)), bool)


def _box(g, x0, x1, y0, y1, sc=_SC):
    g[int(y0 * sc):int(y1 * sc), int(x0 * sc):int(x1 * sc)] = True
    return g


def _glyph_corner(g, x0, y0, w=20.0, h=9.5, sc=_SC):
    """直角引号 ﹂：左竖臂 + 底横臂（与源页 444 实测同形）。"""
    _box(g, x0, x0 + 1.8, y0, y0 + h, sc)          # 竖臂
    _box(g, x0, x0 + w, y0 + h - 2.5, y0 + h, sc)  # 底横臂
    return g


def _glyph_ring(g, x0, y0, d=7.5, sc=_SC):
    """句号 。：闭合圆环（中心空）。"""
    h = int((d + 4) * sc)
    yy, xx = np.mgrid[0:h, 0:h]
    cy = cx = h / 2.0
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    rr = d * sc / 2.0
    sub = (r >= rr * 0.62) & (r <= rr)
    g[int(y0 * sc):int(y0 * sc) + h, int(x0 * sc):int(x0 * sc) + h] |= sub
    return g


def _glyph_bar(g, x0, y0, w=22.5, h=3.0, sc=_SC):
    """汉字「一」：单条长横。"""
    return _box(g, x0, x0 + w, y0, y0 + h, sc)


class TestShapeClassify:
    """形状判据（阈值 = 8 个真值反推，不改）。"""

    def test_corner(self):
        ns = _ns()
        f = ns['_qsf_analyze'](_glyph_corner(_blank(), 2, 2))
        cls, desc = ns['_qsf_classify'](f, 25.5, _SC)
        assert cls == 'corner', desc

    def test_ring(self):
        ns = _ns()
        f = ns['_qsf_analyze'](_glyph_ring(_blank(), 2, 2))
        cls, desc = ns['_qsf_classify'](f, 25.5, _SC)
        assert cls == 'ring', desc

    def test_bar(self):
        ns = _ns()
        f = ns['_qsf_analyze'](_glyph_bar(_blank(), 2, 2))
        cls, desc = ns['_qsf_classify'](f, 25.5, _SC)
        assert cls == 'bar', desc

    def test_dense_cjk_is_other(self):
        """密笔画汉字（填满）不能被误判成引号/句号。"""
        ns = _ns()
        f = ns['_qsf_analyze'](_box(_blank(60, 60), 2, 42, 2, 42))
        cls, desc = ns['_qsf_classify'](f, 25.5, _SC)
        assert cls == 'other', desc

    def test_min_ink_rejects_empty(self):
        ns = _ns()
        assert ns['_qsf_analyze'](np.zeros((40, 40), bool)) is None


class TestDecide:
    """尾格形状 + 末字 -> 动作。"""

    def test_yi_corner_replace(self):
        """OCR「一」+ 尾格直角 = 闭引号误读 -> 1:1 换。"""
        assert _ns()['_qsf_decide']('一', 'corner', 'ring') == 'replace'

    def test_period_corner_prev_ring_append(self):
        """末字「。」且前一条墨是句号环 = 源书「。﹂」-> 补一字（不动既有句号）。"""
        assert _ns()['_qsf_decide']('。', 'corner', 'ring') == 'append'

    def test_period_corner_prev_other_replace(self):
        """末字「。」+ 尾格直角、前条不是句号 -> 句号本身是引号误读 -> 1:1 换。"""
        assert _ns()['_qsf_decide']('。', 'corner', 'other') == 'replace'

    def test_period_ring_noop(self):
        """真句号 -> 不动（负向：不能把句号改成引号）。"""
        assert _ns()['_qsf_decide']('。', 'ring', 'other') is None

    def test_yi_bar_noop(self):
        """真「一」-> 不动。"""
        assert _ns()['_qsf_decide']('一', 'bar', 'other') is None

    def test_append_switch_off(self):
        """VERT_QSF_APPEND=0 -> 补字降级为 1:1 替换（开关否定面）。"""
        ns = _ns()
        ns['QSF_APPEND'] = False
        assert ns['_qsf_decide']('。', 'corner', 'ring') == 'replace'


class TestTailSampling:
    """取样：槽格整列偏移 + 列尾淡墨 + 碎墨噪点。"""

    def _page(self, with_quote=True, with_speck=False):
        g = _blank(120, 200)
        # 正文列: 墨迹 x20-45, 三块; 槽格故意右移 10pt(x0=30,x1=55)
        for y in (20, 50, 80):
            _box(g, 20, 45, y, y + 22)
        _glyph_ring(g, 30, 108)                 # 句号环
        if with_quote:
            _glyph_corner(g, 20, 122)           # 淡墨闭引号(在槽底之下)
        if with_speck:
            _box(g, 25, 28, 135, 139.5)         # 3x4.5pt 碎墨(会被尺寸 sanity 排掉)
        return g

    def _sl(self):
        return {'x0': 30.0, 'x1': 55.0, 'top': 20.0, 'bot': 106.0}

    def test_pick_tail_finds_quote_below_slot_bot(self):
        """槽 x 带偏 +11pt、引号在槽底之外 0.9 步进 -> 仍能按「离槽中心最近的列」认出引号。"""
        ns = _ns()
        p = ns['_qsf_pick_tail'](self._page(with_quote=True), self._sl(), 25.5)
        assert p is not None
        runs, idx, cls, feat, desc, prev = p
        assert cls == 'corner', desc
        assert prev == 'ring'
        assert 120.0 <= runs[idx][0] <= 124.0

    def test_pick_tail_true_period(self):
        """没有引号时尾格 = 句号环 -> ring（负向：不许改真句号）。"""
        ns = _ns()
        p = ns['_qsf_pick_tail'](self._page(with_quote=False), self._sl(), 25.5)
        assert p is not None
        assert p[2] == 'ring'

    def test_pick_tail_skips_speck(self):
        """列尾下方 2 步进内的碎墨判 other 后继续往上找 -> 仍取到引号。"""
        ns = _ns()
        p = ns['_qsf_pick_tail'](self._page(with_quote=True, with_speck=True), self._sl(), 25.5)
        assert p is not None
        runs, idx, cls, feat, desc, prev = p
        assert cls == 'corner', desc
        assert runs[idx][0] < 130.0

    def test_run_feat_rejects_speck(self):
        """单字形尺寸 sanity：2.5x4pt 碎墨即便四角特征像 corner 也判 other。"""
        ns = _ns()
        sl = {'x0': 20.0, 'x1': 45.0}
        cls, f, desc = ns['_qsf_run_feat'](
            self._page(with_quote=False, with_speck=True), sl, (135.0, 139.5), 25.5)
        assert cls == 'other' and '碎墨' in desc

    def test_tail_runs_step_zero(self):
        ns = _ns()
        assert ns['_qsf_tail_runs'](self._page(), self._sl(), 0.0) == []


class TestPlan:
    """运行入口：开关 + replace/append + 日志。"""

    def _mk(self, with_quote=True, qsf_on=True, append=True):
        ink = TestTailSampling()._page(with_quote=with_quote)
        ns = _ns(ink)
        ns['QSF_ON'] = qsf_on
        ns['QSF_APPEND'] = append
        ns['_qsf_stat'].update({'cand': 0, 'corner': 0, 'replace': 0, 'append': 0,
                                'ring': 0, 'bar': 0, 'other': 0, 'norun': 0})
        ns['_qsf_log'].clear()
        return ns

    def test_plan_append_period(self):
        ns = self._mk()
        r = ns['_qsf_plan'](0, TestTailSampling()._sl(), 25.5, {'g': {}}, '。')
        assert r is not None and r['action'] == 'append'
        assert ns['_qsf_stat']['append'] == 1
        assert ns['_qsf_log'][0]['page'] == 1

    def test_plan_replace_yi(self):
        ns = self._mk()
        r = ns['_qsf_plan'](0, TestTailSampling()._sl(), 25.5, {'g': {}}, '一')
        assert r is not None and r['action'] == 'replace'
        assert ns['_qsf_stat']['replace'] == 1

    def test_plan_ring_noop(self):
        ns = self._mk(with_quote=False)
        assert ns['_qsf_plan'](0, TestTailSampling()._sl(), 25.5, {'g': {}}, '。') is None
        assert ns['_qsf_stat']['cand'] == 1

    def test_switch_off_noop(self):
        """VERT_QSF=0 等价：开关关掉时整段不执行（否定面）。"""
        ns = self._mk(qsf_on=False)
        assert ns['_qsf_plan'](0, TestTailSampling()._sl(), 25.5, {'g': {}}, '。') is None
        assert ns['_qsf_stat']['cand'] == 0

    def test_env_switch_parsed(self):
        """VERT_QSF=0 在模块加载时被解析成 QSF_ON=False。"""
        os.environ['VERT_QSF'] = '0'
        try:
            ns = _ns()
        finally:
            os.environ.pop('VERT_QSF', None)
        assert ns['QSF_ON'] is False

    def test_env_append_off_parsed(self):
        os.environ['VERT_QSF_APPEND'] = '0'
        try:
            ns = _ns()
        finally:
            os.environ.pop('VERT_QSF_APPEND', None)
        assert ns['QSF_APPEND'] is False
