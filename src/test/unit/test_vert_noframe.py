#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskO：无版框书支持（#29）的纯函数测试。

被测实现：`src/pipelines/build_vert.py`
  · §1.975 `nf_body_rows`     —— 本页正文行(本页页幅比例的长行; 不按「左带小字」丢行)
  · §1.975 `nf_join_rows`     —— OCR 插进去的换行拼回(只 NF: 曲牌/小字標題 + 正文 被拆成两行)
  · §1.975 `nf_edges`         —— 墨迹列带 -> 伪槽格边界(相邻带心中点, 首末外扩半列距)
  · §1.975 `nf_fill_bands`    —— 残余墨迹补短列(列带数 < 行数时整列会被丢)
  · §1.975 `nf_fit` / `nf_fit_align` —— OCR 帧 -> 源图帧 的仿射标定(尺度用相邻间距比中位)
  · §1.06 `_nf_ink_gray`      —— 逐页 Otsu 阈值(灰底扫描用固定 150 会把灰晕算成墨迹)
  · §1.06 `_nf_page_px` / `_nf_thr`   —— 逐页纸型 + 逐页门限(混纸型书)
  · §1.956 `_calib_xscale_w`  —— XSCALE 的宽高比口径(NF 用: 面积口径随二值化阈值漂移)
用 _loader 从脚本里 ast 提取纯函数(不 import fitz/scipy、不跑 upLaTeX、不读源图)。

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_noframe.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_FUNCS = ['nf_body_rows', 'nf_join_rows', 'nf_edges', 'nf_fill_bands', 'nf_fit', 'nf_fit_align',
          '_nf_ink_gray', '_nf_page_px', '_nf_thr', '_calib_xscale_w', '_calib_med', '_runs',
          '_band_union']
# 说明: BAND_*/LONG_H_*/FRAG_OVL/页幅/_NF/_nf_cache 都是**由函数算出来或需按用例改**的全局量,
#   统一用 mocks 注入(它们不是 ast 的纯字面量赋值, 直接从源码 exec 会缺依赖函数)。
_CONSTS = ['NF_MIN_COL', 'NF_COV', 'NF_FIT_K', 'NF_FIT_RES', 'PT_PER_PX']


class _Doc:
    """src_doc 最小 mock: page_count + 每页 rect。"""
    def __init__(self, sizes):
        self.page_count = len(sizes)
        self._sz = sizes

    def __getitem__(self, i):
        class _P:
            def __init__(self, s):
                class _R:
                    def __init__(self, w, h):
                        self.width, self.height = w, h
                self.rect = _R(*s)
        return _P(self._sz[i])


WZ6_PAGE = (595.3, 1245.3)
WZ7 = dict(PW_PX=1843.6, PH_PX=2886.0, page_w=921.8, page_h=1443.0, PT_PER_PX=2.0,
           LONG_H_FRAC=300.0 / 2490.6, BAND_R_PX=1843.6 * (1100.0 / 1190.6),
           BAND_L_PX=1843.6 * (100.0 / 1190.6), LONG_H_PX=2886.0 * (300.0 / 2490.6),
           FRAG_OVL_PX=24.0, NF_MIN_COL=3, NF_COV=0.12, NF_FIT_K=(0.7, 1.6), NF_FIT_RES=0.5,
           _NF={'on': True}, _nf_cache={})


def _ns(extra=None, doc=None):
    m = dict(WZ7)
    if extra: m.update(extra)
    m['src_doc'] = doc
    m['keys'] = ['0', '1', '2']
    ns = load('build_vert.py', _FUNCS, _CONSTS, m)
    return ns


# ---------- A. 正文行筛选(§1.975) ----------
class TestBodyRows:
    def test_long_rows_only(self):
        """长行(本页页高 x 0.120453 = 347.6px)才算正文列; 页码/书眉/残片被挡"""
        ns = _ns()
        rows = [(100, 200, 300, 2500, '正' * 40),      # 长行 ✓
                (100, 200, 300, 600, '短'),             # h=300 < 347.6 ✗
                (100, 200, 300, 2500, '')]              # 空文本 ✗
        out = ns['nf_body_rows'](rows, 2886.0)
        assert [r[4] for r in out] == ['正' * 40]

    def test_small_left_row_kept(self):
        """**不**按「左带小字」丢行: 无版框书的左侧就是正文列(实测 wz7 最左列 OCR x0=76px 会被旧判据丢)"""
        ns = _ns()
        rows = [(76.0, 250.0, 300.0, 2500.0, '正' * 44)]
        assert len(ns['nf_body_rows'](rows, 2886.0)) == 1

    def test_page_height_scales(self):
        """门限按**本页**页高算: h=300 的行在小开本页(2168px, 门限 261)算长行, 在大开本页
        (2886px, 门限 347.6)不算 —— 混纸型书必须逐页取页幅, 否则分类翻转。"""
        ns = _ns()
        rows = [(100, 200, 300, 600, '正' * 20)]        # h=300
        assert len(ns['nf_body_rows'](rows, 2168.0)) == 1
        assert ns['nf_body_rows'](rows, 2886.0) == []


# ---------- B. 换行拼回(§1.975) ----------
class TestJoinRows:
    def test_join_normal_step(self):
        """曲牌/標題 + 正文 被 OCR 插了换行 -> 拼回(y 跨度/字数 = 常列步进)"""
        ns = _ns()
        rows = [(600, 700, 200, 2200, '正' * 44),                     # 常列: 步进 45.4
                (600, 700, 200, 2200, '甜水令\n' + '文' * 36)]        # 拼回后 39 字 -> 51.3 ≈ 1.13x
        out = ns['nf_join_rows'](rows)
        assert '\n' not in out[1][4] and out[1][4].startswith('甜水令文')
        assert out[0][4] == '正' * 44

    def test_keep_fragment(self):
        """步进明显异常(OCR 把多个块并成一条)的行保持原样 -> 下游按残片丢弃"""
        ns = _ns()
        rows = [(600, 700, 200, 2200, '正' * 44),
                (600, 700, 200, 2200, '殘\n' + '字' * 200)]           # 拼回后步进 ≈ 10 = 0.22x
        out = ns['nf_join_rows'](rows)
        assert '\n' in out[1][4]


# ---------- C. 伪槽格(§1.975) ----------
class TestEdges:
    def test_edges_mid_gap(self):
        """格边界 = 相邻带心中点; 首末外扩半列距 -> 格宽 = 列距(标点摆位 PUNCT_DX 的分母口径)"""
        ns = _ns()
        e, p = ns['nf_edges']([(100.0, 120.0), (140.0, 160.0), (180.0, 200.0)])
        assert p == 40.0
        assert e == [90.0, 130.0, 170.0, 210.0]
        assert [round(b - a, 3) for a, b in zip(e, e[1:])] == [40.0, 40.0, 40.0]

    def test_too_few_bands(self):
        """带数 < 3 -> 不可用(该页交回流式)"""
        ns = _ns()
        assert ns['nf_edges']([(100.0, 120.0), (140.0, 160.0)]) == (None, 0.0)


class TestFillBands:
    def test_fill_short_column(self):
        """短列(墨迹覆盖率低于 cov=0.12)漏检 -> 用残余墨迹补, 使列带数 >= 行数"""
        np = pytest.importorskip('numpy')
        ns = _ns()
        ink = np.zeros((200, 400), dtype=bool)
        ink[:, 40:60] = True          # 长列(满高)
        ink[10:30, 120:140] = True    # 短列(只占 10% 高度) -> cov=0.12 会漏
        bands = [(20.0, 30.0)]        # 只检到第一条(pt; 2x px -> 40-60px)
        out = ns['nf_fill_bands'](ink, bands, 0.0, 200.0, 0.0, 100.0, 2)
        assert len(out) == 2 and out[1][0] >= 55.0

    def test_no_fill_when_enough(self):
        np = pytest.importorskip('numpy')
        ns = _ns()
        ink = np.zeros((200, 400), dtype=bool)
        ink[:, 40:60] = True
        assert ns['nf_fill_bands'](ink, [(20.0, 30.0)], 0.0, 200.0, 0.0, 100.0, 1) == [(20.0, 30.0)]


# ---------- D. OCR 帧 -> 源图帧 仿射标定(§1.975) ----------
class TestFit:
    def test_fit_scale_offset(self):
        """x_ocr = 1.2 x_src - 180(实测 wz7 的 OCR 各向异性缩放 + 偏移)"""
        ns = _ns()
        pairs = [(1.2 * (100 + 80 * i) - 180, 100 + 80 * i) for i in range(10)]
        k, b, rms = ns['nf_fit'](pairs)
        assert abs(k - 1.2) < 1e-6 and abs(b + 180) < 1e-6 and rms < 1e-6

    def test_fit_needs_samples(self):
        ns = _ns()
        assert ns['nf_fit']([(1.0, 1.0), (2.0, 2.0), (3.0, 3.0)]) is None

    def test_align_offset(self):
        """两侧条数不等(端部多一条残片/漏检)时按标配对会整段错位 -> 枚举错位取残差最小"""
        ns = _ns()
        cs = [100.0 + 80 * i for i in range(8)]                 # 源图 8 列
        ro = [1.2 * c - 180 for c in cs[1:]]                    # OCR 少第一列(7 条)
        k, b, rms, pr = ns['nf_fit_align'](cs, ro)
        assert abs(k - 1.2) < 1e-6 and rms < 1e-6 and len(pr) == 7

    def test_align_rejects_bad_scale(self):
        ns = _ns()
        assert ns['nf_fit_align']([100.0 * i for i in range(6)],
                                  [2.5 * 100.0 * i for i in range(6)]) is None


# ---------- E. 逐页阈值/纸型(§1.06) ----------
class TestInkThr:
    def test_otsu_bimodal(self):
        """双峰灰度(纸 ~250 / 墨 ~40, 各带散布) -> 阈值落在两峰之间"""
        np = pytest.importorskip('numpy')
        ns = _ns()
        rng = np.random.RandomState(0)
        a = np.concatenate([rng.randint(230, 255, 4000), rng.randint(20, 70, 4000)]).astype(np.uint8)
        assert 60 <= ns['_nf_ink_gray'](a) < 230

    def test_otsu_gray_scan(self):
        """灰底扫描(纸 185-199 / 墨 30-60, 实测 wz7) -> 阈值 ≈ 120, 远低于 wz6 口径的固定 150"""
        np = pytest.importorskip('numpy')
        ns = _ns()
        rng = np.random.RandomState(1)
        a = np.concatenate([rng.randint(180, 205, 8000), rng.randint(25, 65, 2000)]).astype(np.uint8)
        t = ns['_nf_ink_gray'](a)
        assert 60 < t < 150, '灰底扫描的自适应阈值应落在纸/墨之间' 


class TestPageThr:
    def test_per_page_size(self):
        """逐页纸型: 混纸型书(922x1437 与 705x1084 两种开本)按本页取"""
        doc = _Doc([(922.0, 1437.0), (705.0, 1083.8)])
        ns = _ns(doc=doc)
        assert ns['_nf_page_px'](0) == (1844.0, 2874.0)
        assert ns['_nf_page_px'](1) == (1410.0, 2167.6)

    def test_thr_global_when_off(self):
        """非 NF(有实测版框的书) -> 原全局门限逐位不变"""
        ns = _ns(extra={'_NF': {'on': False}})
        assert ns['_nf_thr']('0') == (WZ7['LONG_H_PX'], WZ7['BAND_R_PX'], WZ7['BAND_L_PX'], 24.0)

    def test_thr_scales_and_union(self):
        """NF: 门限按本页纸型比例缩放, 页边带再并上伪版心缘(§1.96a 同口径)"""
        doc = _Doc([(705.0, 1083.8)])
        cache = {0: {'in_l': 60.0, 'in_r': 620.0}}       # 伪版心缘(pt): 右带取 min(页幅带, 620*2)
        ns = _ns(extra={'_nf_cache': cache}, doc=doc)
        lh, br, bl, fo = ns['_nf_thr']('0')
        assert abs(lh - WZ7['LONG_H_PX'] * 2167.6 / 2886.0) < 1e-6
        # 右带 = min(页幅比例带 1302.6, 伪版心右缘 1240) = 1240; 左带 = max(比例带 118.4, 内框左缘 120) = 120
        assert br == 620.0 * 2.0 and bl == 60.0 * 2.0


# ---------- F. XSCALE 宽高比口径(§1.956) ----------
class TestXscaleW:
    def test_width_ratio(self):
        """源书墨宽/墨高 0.65, 渲染 1.0 -> 0.65(与 taskM 报告的「只对宽 0.65」一致)"""
        ns = _ns()
        src = [(100.0, 65.0, 0.0)] * 5 + [(120.0, 78.0, 0.0)] * 5
        probe = {'甲': (1.0, 1.0, 0.0, 0.0, 0.0, 0.0)}
        assert ns['_calib_xscale_w'](src, probe, ['甲']) == 0.65

    def test_none_when_empty(self):
        ns = _ns()
        assert ns['_calib_xscale_w']([], {}, []) is None
