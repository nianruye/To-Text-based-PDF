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
          '_band_union',
          # taskP: 印刷线去除 / 框版心 / 横排页兜底 / 行槽配平位置先验 / 页内夹取
          '_nf_lines', '_nf_delines', '_nf_box', '_nf_hrow_page', '_align_rows_slots',
          '_pv_clamp_on',
          # taskP2: 短列证据补带 / 版心夹回纸幅 / 实测文本框夹取
          'nf_short_cols', '_nf_clamp_box', '_txtbox_clamp_y']
# 说明: BAND_*/LONG_H_*/FRAG_OVL/页幅/_NF/_nf_cache 都是**由函数算出来或需按用例改**的全局量,
#   统一用 mocks 注入(它们不是 ast 的纯字面量赋值, 直接从源码 exec 会缺依赖函数)。
_CONSTS = ['NF_MIN_COL', 'NF_COV', 'NF_FIT_K', 'NF_FIT_RES', 'PT_PER_PX',
           'NF_LINE_CV', 'NF_LINE_RV', 'NF_LINE_VLEN', 'NF_LINE_HLEN', 'n_cells', 'char_cells',
           'NF_BOX_WMIN', 'NF_BOX_HMIN', 'NF_HROW_AR', 'NF_HROW_CHAR', 'NF_POS_PRIOR',
           'NF_FILL_HMIN', 'NF_FILL_NRUN', 'NF_FILL_PAD', 'TXTBOX_C', 'TXTBOX_UP', 'TXTBOX_DN']


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
           FRAG_OVL_PX=24.0, NF_MIN_COL=2, NF_COV=0.12, NF_FIT_K=(0.7, 1.6), NF_FIT_RES=0.5,
           NF_LINE_CV=0.75, NF_LINE_RV=0.45, NF_LINE_VLEN=0.50, NF_LINE_HLEN=0.55,
           NF_BOX_WMIN=0.35, NF_BOX_HMIN=0.35, NF_HROW_AR=2.0, NF_HROW_CHAR=0.60,
           NF_POS_PRIOR=60.0, all_rows={}, _nf_box_cache={}, _nf_ink_cache={},
           PUNCT_HANG={'，', '。', '、', '：', '；'}, VERT_FORMS={},
           n_cells=lambda t: max(1, sum(1 for c in t if c not in {'，', '。', '、', '：', '；'})),
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

    def test_two_bands_ok(self):
        """2 列也能建槽(taskP: 源页 22「题辞」只有 2 列大字, 降 NF_MIN_COL 3->2 前被挡在 NF 外)"""
        ns = _ns()
        e, p = ns['nf_edges']([(100.0, 120.0), (140.0, 160.0)])
        assert e == [90.0, 130.0, 170.0] and p == 40.0

    def test_too_few_bands(self):
        """带数 < 3 -> 不可用(该页交回流式)"""
        ns = _ns()
        assert ns['nf_edges']([(100.0, 120.0)]) == (None, 0.0)


class TestFillBands:
    def test_fill_short_column(self):
        """短列(墨迹覆盖率低于 cov=0.12)漏检 -> 用残余墨迹补, 使列带数 >= 行数。
        taskP2: 候选要过「文字列证据」(run >= NF_FILL_NRUN) —— 故短列按**逐字 run** 造(4 字 = 4 条):
        实心一整块是碎墨/装饰的形态, 新判据会(且应当)拒绝, 见 test_fill_rejects_solid_blob。"""
        np = pytest.importorskip('numpy')
        ns = _ns()
        ink = np.zeros((200, 400), dtype=bool)
        ink[:, 40:60] = True                      # 长列(满高)
        for y in (10, 30, 50, 70):                # 短列 = 4 个字的 run(只占 ~10% 高度)
            ink[y:y + 12, 120:140] = True
        bands = [(20.0, 30.0)]                    # 只检到第一条(pt; 2x px -> 40-60px)
        out = ns['nf_fill_bands'](ink, bands, 0.0, 200.0, 0.0, 100.0, 2)
        assert len(out) == 2 and out[1][0] >= 55.0

    def test_fill_rejects_solid_blob(self):
        """taskP2: 残余墨迹里的「实心块」(无 run 结构 = 碎墨/装饰/扫描噪点) 不补成正文列"""
        np = pytest.importorskip('numpy')
        ns = _ns()
        ink = np.zeros((200, 400), dtype=bool)
        ink[:, 40:60] = True
        ink[10:30, 120:140] = True                # 一整块 = 1 条长 run < NF_FILL_NRUN
        out = ns['nf_fill_bands'](ink, [(20.0, 30.0)], 0.0, 200.0, 0.0, 100.0, 2)
        assert len(out) == 1

    def test_fill_merges_fragments(self):
        """taskP2: 同列被切成的两段碎片(间隙 <= 4pt)先合并再判宽度 —— 原口径(gap 4px)会把
        7pt+2pt 两段都当候选且都因宽度不足被拒, 真列补不出(实测 wz7 源页 291 的 `三十歲。`)"""
        np = pytest.importorskip('numpy')
        ns = _ns()
        ink = np.zeros((200, 400), dtype=bool)
        ink[:, 40:60] = True
        for y in (10, 30, 50, 70):                # 碎片 A: x 120-127px
            ink[y:y + 12, 120:127] = True
            ink[y:y + 12, 131:138] = True         # 碎片 B: 间隙 4px(8px 合并窗内)
        out = ns['nf_fill_bands'](ink, [(20.0, 30.0)], 0.0, 200.0, 0.0, 100.0, 2)
        assert len(out) == 2
        a, b = out[1]
        assert a <= 60.5 and b >= 68.5            # 合并后覆盖两段(60-69pt)

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


# ---------- taskP: 印刷线去除(§1.06b) ----------
def _np():
    import numpy as np
    return np


def _frame_ink(H=200, W=200):
    """带框页合成墨迹: 粗竖框线 x=10..13 / x=186..189, 粗横线 y=10..13 / y=186..189,
    框内两列文字(每列 4 个 16x16 的「字」)。"""
    np = _np()
    ink = np.zeros((H, W), bool)
    ink[10:14, :] = True
    ink[186:190, :] = True
    ink[:, 10:14] = True
    ink[:, 186:190] = True
    for x0 in (40, 120):
        for y0 in range(40, 160, 30):
            ink[y0:y0 + 16, x0:x0 + 16] = True
    return ink


class TestNfLines:
    def test_find_and_remove_frame_lines(self):
        """框线(又长又直)被识别并删除; 文字笔画保留 —— 不去线则列带/字 run 统计被整页污染"""
        ns = _ns()
        ink = _frame_ink()
        vd, hd = ns['_nf_lines'](ink)
        assert len(vd) == 2 and len(hd) == 2
        clean = ns['_nf_delines'](ink)
        assert ink.sum() - clean.sum() > 0.8 * (10 * 190 * 2)      # 四条线基本被删净
        assert clean[40:56, 40:56].all()                            # 文字笔画原样保留
        assert not clean[:, 186:190].any()                          # 右框线清除

    def test_text_strokes_not_taken_as_lines(self):
        """文字列(窄但**不贯穿**)不算印刷线: 竖笔画覆盖率远低于 NF_LINE_CV"""
        ns = _ns()
        np = _np()
        ink = np.zeros((200, 200), bool)
        for y0 in range(20, 180, 24):                               # 疏排的字, 纵向不连续
            ink[y0:y0 + 12, 60:76] = True
        vd, hd = ns['_nf_lines'](ink)
        assert vd == [] and hd == []
        assert ns['_nf_delines'](ink) is ink                        # 未动(同一对象)


# ---------- taskP: 横排页判据(§1.975b) ----------
class TestHrowPage:
    def test_horizontal_rows(self):
        """行盒宽扁(w/h>=2)且占本页字数 60% 以上 -> 判横排页(字表/版权页)"""
        ns = _ns()
        rows = {'0': [(100, 1300, 50, 90, '嘀颗蛀炉鲈粮坟棍') , (100, 1300, 200, 240, '商類怪爐鱸糧墳褲')]}
        ns['all_rows'] = rows
        out = ns['_nf_hrow_page']('0', 0)
        assert len(out) == 2

    def test_vertical_page_not_hrow(self):
        """竖排正文页(行盒高瘦)不误判"""
        ns = _ns()
        ns['all_rows'] = {'0': [(100, 200, 50, 2500, '正' * 40)]}
        assert ns['_nf_hrow_page']('0', 0) == []

    def test_few_horizontal_rows_not_page(self):
        """横排行字数占比不足(竖排页里夹一行横排说明)不判横排页"""
        ns = _ns()
        ns['all_rows'] = {'0': [(100, 1300, 50, 90, '短行'),
                                (100, 200, 100, 2500, '正' * 60)]}
        assert ns['_nf_hrow_page']('0', 0) == []


# ---------- taskP: 行/槽配平的位置先验 ----------
# ---------- taskP: 页内夹取开关 ----------
class TestClampOn:
    def test_virtual_only(self):
        """只伪槽格页夹取(有版框书 wz6 不走 -> 逐位不变)"""
        ns = _ns()
        assert ns['_pv_clamp_on']({'g': {'virtual': True}}) is True
        assert ns['_pv_clamp_on']({'g': {'in_l': 40.0}}) is False
        assert ns['_pv_clamp_on'](None) is False


# ---------- F. taskP2: 版心夹回纸幅 / 短列计数 / 实测文本框夹取 ----------
class TestTaskP2Box:
    def test_clamp_box_inside(self):
        """版心本就在纸内 -> 原样返回"""
        ns = _ns()
        assert ns['_nf_clamp_box'](50.0, 800.0, 100.0, 1200.0, 892.5, 1323.0) == \
            (50.0, 800.0, 100.0, 1200.0)

    def test_clamp_box_out_of_page(self):
        """行盒整段越出纸(实测源页 182: y -138.8) -> 夹回纸内(否则槽统计全在纸外)"""
        ns = _ns()
        il, ir, it, ib = ns['_nf_clamp_box'](-20.0, 950.0, -138.8, 900.0, 892.5, 1323.0)
        assert il == 0.0 and ir == 892.5
        assert it == 0.0 and ib == 900.0          # 负的版心顶被夹到 0, 其余不动

    def test_clamp_box_degenerate(self):
        """夹后与纸几乎不相交(< 8pt) -> None(该页不建伪槽格, 交回流式)"""
        ns = _ns()
        assert ns['_nf_clamp_box'](-50.0, -45.0, 100.0, 400.0, 892.5, 1323.0) is None

    def test_txtbox_clamp_keeps_box_inside(self):
        """taskP2-①: 夹取用**实测文本框**比例 —— 盒顶可达 put + C + UP x F(远大于 em 盒的 0.94F),
        夹后盒顶/盒底都必须落在页内(这正是 p104 ﹁ 越界 5.93pt 的根因)。"""
        ns = _ns()
        C, UP, DN = ns['TXTBOX_C'], ns['TXTBOX_UP'], ns['TXTBOX_DN']
        page = 1323.0
        for F in (9.3, 26.0, 40.0):
            y = ns['_txtbox_clamp_y'](page + 50.0, F, page)          # 想放到页外
            assert y + C + UP * F <= page + 1e-9
            y2 = ns['_txtbox_clamp_y'](-50.0, F, page)
            assert y2 + C - DN * F >= -1e-9

    def test_short_cols_count(self):
        """补带目标 = 长行数 + 版心内短列数(实测源页 291 的 `三十歲。` 4 字短列是真列)"""
        ns = _ns()
        long_row = (100.0, 700.0, 200.0, 2000.0, '正文长行')      # px(2x): 高 1800px
        short_in = (560.0, 640.0, 220.0, 420.0, '三十歲。')        # 高 200px < LONG_H_FRAC x 页高
        outside = (560.0, 640.0, 3960.0, 4040.0, '页码')           # 版心外(页外)
        body = [long_row]
        # 版心 pt: x 0-900, y 90-1000; rows 是 px(2x)
        assert ns['nf_short_cols']([long_row, short_in, outside], body, 0.0, 900.0, 90.0, 1000.0,
                                   2886.0) == 1
