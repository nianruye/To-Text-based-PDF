#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskN：竖排管线「纸型无关化」的纯函数测试。

被测实现：`src/pipelines/build_vert.py`
  · §0.5   `_frac` / `_sc` / `_envfrac` / `_sc_pt` / `_fp` / `_band_union`  —— 相对量换算(原绝对值 -> 页幅比例 -> 本书 px/pt)
  · §1.05 `_fsf`                                                          —— 小字/碎片判据(相对正文字步进 FS_px)
  · §1.85 `_calib_note_ratio`                                             —— 边注/正文 步进比上限(实测空档)
  · §1.954 `_calib_line_widths`                                           —— 版框线粗细分界(实测线宽分布)
用 _loader 从脚本里 ast 提取纯函数(不 import fitz/scipy、不跑 upLaTeX、不读源图)。

口径要点(等价性): 换算 = 原 wz6 绝对值 ÷ wz6 页幅 x 本页幅, wz6 页幅上必须**逐位复现**原值
  (1100/100/300/55 px、70/250/4/40/5/90/40/24/15/2/8 px、700/900/400/640/40/48/36/50/20/100/8/35/52 pt),
  否则整数边界行的分类会翻转(如 x0=1100 落在「x0>1100」的哪一侧)。

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_paper_agnostic.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_FUNCS = ['_frac', '_sc', '_envfrac', '_sc_pt', '_fp', '_band_union', '_fsf',
          '_calib_note_ratio', '_calib_line_widths']

# wz6 实测基准(2x px / pt / 正文字步进) —— 测试里当模块全局注入
WZ6 = {'PW_PX': 1190.6, 'PH_PX': 2490.6, 'page_w': 595.3, 'page_h': 1245.3,
       '_WZ6_PW': 1190.6, '_WZ6_PH': 2490.6, '_WZ6_PW_PT': 595.3, '_WZ6_PH_PT': 1245.3,
       'FS_px': 68.796, '_FS_WZ6': 68.796}
# wz7(《金瓶梅詞話》)实测基准 —— 换书验证用
WZ7 = {'PW_PX': 1843.6, 'PH_PX': 2886.0, 'page_w': 921.8, 'page_h': 1443.0,
       '_WZ6_PW': 1190.6, '_WZ6_PH': 2490.6, '_WZ6_PW_PT': 595.3, '_WZ6_PH_PT': 1245.3,
       'FS_px': 55.327, '_FS_WZ6': 68.796}

def _ns(env, extra=None):
    m = dict(env)
    if extra: m.update(extra)
    return load('build_vert.py', _FUNCS, [], mocks=m)


@pytest.fixture()
def wz6():
    return _ns(WZ6)


@pytest.fixture()
def wz7():
    return _ns(WZ7)


# ---------- A. 页幅比例换算(§0.5) ----------
class TestRelScale:
    def test_wz6_roundtrip_is_exact(self, wz6):
        """wz6 上反算回原绝对值: 4 个门限(1100/100/300/55)逐位相同(0 偏差)"""
        assert wz6['_sc'](wz6['_frac']('VERT_BAND_R_FRAC', 1100.0, 1190.6), 'w') == 1100.0
        assert wz6['_sc'](wz6['_frac']('VERT_BAND_L_FRAC', 100.0, 1190.6), 'w') == 100.0
        assert wz6['_sc'](wz6['_frac']('VERT_LONG_H_FRAC', 300.0, 2490.6), 'h') == 300.0
        assert wz6['_sc'](wz6['_frac']('VERT_SMALL_FS_FRAC', 55.0, 2490.6), 'h') == 55.0

    def test_wz6_pt_roundtrip_is_exact(self, wz6):
        """版框几何区间(pt 类): 700/900/400/640/40/48/36/50/20/100/8/35/52 逐位相同"""
        for v, ax in ((700.0, 'h'), (900.0, 'h'), (400.0, 'w'), (640.0, 'w'), (40.0, 'w'),
                      (48.0, 'w'), (36.0, 'w'), (50.0, 'w'), (20.0, 'w'), (100.0, 'w'),
                      (8.0, 'w'), (35.0, 'w'), (52.0, 'w')):
            assert wz6['_sc_pt'](wz6['_envfrac']('X_FRAC', wz6['_fp'](v, ax)), ax) == v

    def test_wz7_scales_with_page(self, wz7):
        """换书(wz7 921.8x1443pt): 同一个比例换算出新门限 —— 页边带/长行/小字都按新页幅"""
        assert wz7['_sc'](wz7['_frac']('VERT_BAND_R_FRAC', 1100.0, 1190.6), 'w') == pytest.approx(1703.31, abs=0.01)
        assert wz7['_sc'](wz7['_frac']('VERT_BAND_L_FRAC', 100.0, 1190.6), 'w') == pytest.approx(154.85, abs=0.01)
        assert wz7['_sc'](wz7['_frac']('VERT_LONG_H_FRAC', 300.0, 2490.6), 'h') == pytest.approx(347.63, abs=0.01)
        assert wz7['_sc_pt'](wz7['_envfrac']('X', wz7['_fp'](700.0, 'h')), 'h') == pytest.approx(811.13, abs=0.01)

    def test_env_override(self, monkeypatch, wz6):
        """显式 env 给比例时优先于 wz6 换算值"""
        monkeypatch.setenv('VERT_BAND_R_FRAC', '0.5')
        assert wz6['_sc'](wz6['_frac']('VERT_BAND_R_FRAC', 1100.0, 1190.6), 'w') == pytest.approx(595.3, abs=0.01)
        monkeypatch.setenv('VERT_INH_LO_FRAC', '0.4')
        assert wz6['_sc_pt'](wz6['_envfrac']('VERT_INH_LO_FRAC', 700.0 / 1245.3), 'h') == pytest.approx(498.12, abs=0.01)

    def test_fsf_reproduces_wz6_integers(self, wz6):
        """小字/碎片判据(相对 FS_px): wz6 上逐项回到原整数门限"""
        for v in (70.0, 250.0, 4.0, 40.0, 5.0, 90.0, 24.0, 15.0, 2.0, 8.0):
            assert wz6['_fsf'](v) == int(v)

    def test_fsf_scales_on_other_book(self, wz7):
        """wz7 字步进 55.3px(正文 27.7pt): 窗口/组件窗按比例缩小(0.8 倍)"""
        assert wz7['_fsf'](70.0) == 56
        assert wz7['_fsf'](250.0) == 201
        assert wz7['_fsf'](90.0) == 72
        assert wz7['_fsf'](4.0) == 3
        assert wz7['_fsf'](2.0) == 2          # 下限 1px(不会缩成 0)


# ---------- B. 页边带并内框缘(§1.96a) ----------
class TestBandUnion:
    def test_wz6_frame_wider_than_band(self):
        """wz6: 内框右缘 567.8pt(=1135.6px) > 页幅带 1100px / 左缘 45.5pt(=91px) < 100px -> 不生效"""
        assert _ns(WZ6)['_band_union'](1100.0, 100.0, 45.5, 567.8) == (1100.0, 100.0)

    def test_narrow_block_widens_band(self):
        """版心窄(左 200pt=400px / 右 800pt=1600px, 页幅带 1900/100): 两翼都外扩到框缘"""
        assert _ns(WZ6)['_band_union'](1900.0, 100.0, 200.0, 800.0) == (1600.0, 400.0)

    def test_no_frame_keeps_page_band(self):
        """无内框(前导向): 调用方不调本函数, 页幅比例带原样使用"""
        assert _ns(WZ7)['_band_union'](1703.32, 154.85, 154.85 / 2.0, 1703.32 / 2.0) == (1703.32, 154.85)


# ---------- C. 边注/正文 步进比上限(§1.85) ----------
class TestNoteRatio:
    def test_fallback_kept_when_inside_gap(self):
        """wz6 分布: 注簇 <=0.833, 正文簇 1.068, 空档含兜底 0.85 -> 保留 0.85(值面零漂移)"""
        rs = [0.55] * 20 + [0.62] * 10 + [0.80, 0.81, 0.82, 0.833, 1.068]
        v, why = _ns(WZ6)['_calib_note_ratio'](rs)
        assert v == 0.85 and '空档' in why

    def test_moves_to_gap_midpoint(self):
        """注更大(比值 0.86-0.93 密簇)、正文 1.0+: 兜底 0.85 落在**注簇内部**(会误判注为正文)
        -> 取空档 (0.93, 1.0) 中点 0.965 夹到 0.95, 注仍全部认到"""
        rs = [0.84, 0.85, 0.86, 0.87, 0.88, 0.89, 0.90] * 2 + [1.05, 1.08, 1.10]
        v, why = _ns(WZ6)['_calib_note_ratio'](rs)
        assert v == 0.95 and '中点' in why

    def test_no_gap_keeps_fallback(self):
        """比值连续(最大空档 < 0.08) -> 不标定, 调用方保留兜底 0.85"""
        rs = [0.5 + 0.01 * i for i in range(20)]
        v, why = _ns(WZ6)['_calib_note_ratio'](rs)
        assert v is None and '连续' in why

    def test_too_few_samples(self):
        v, why = _ns(WZ6)['_calib_note_ratio']([0.5, 0.6, 0.9])
        assert v is None and '样本' in why

    def test_clamped_below_one(self):
        """空档中点 > 1 -> 夹到 0.95(<1: 正文列的步进 ≈ FS_px, 阈值必须小于它)"""
        rs = [0.9] * 10 + [2.0] * 5
        v, _ = _ns(WZ6)['_calib_note_ratio'](rs)
        assert v == 0.95


# ---------- D. 版框线粗细分界(§1.954) ----------
class TestLineWidths:
    # wz6 16 页实测(见 docs/vert_paper_agnostic_report.md §3): 竖线组 0.5x46 / 1.0x146 / 1.5x5 / 3.5x11 / 4.0x4
    WZ6_V = [0.5] * 46 + [1.0] * 146 + [1.5] * 5 + [3.5] * 11 + [4.0] * 4
    WZ6_H = [1.0] * 4 + [1.5] * 26 + [3.5] + [4.0] * 23 + [4.5] * 6

    def test_wz6_equivalent_to_constants(self):
        """wz6 -> (2.45, 6.75): 线厚只能是半整数, 故与兜底 (2.4, 6.5) 分类完全等价(见报告对账表)"""
        tmin, tmax, why = _ns(WZ6)['_calib_line_widths'](self.WZ6_V, self.WZ6_H)
        assert (tmin, tmax) == (2.45, 6.75)
        assert '细簇上缘 1.50' in why

    def test_thin_line_book(self):
        """线更细的书(细 0.5-0.75 / 粗 2.0-2.5): 分界自定到 1.4, 不再固定 2.4(否则粗线被当细线)"""
        v = [0.5] * 30 + [0.75] * 20 + [2.0] * 6 + [2.5] * 3
        h = [0.75] * 8 + [2.5] * 4
        tmin, tmax, _ = _ns(WZ6)['_calib_line_widths'](v, h)
        assert tmin == pytest.approx(1.4, abs=1e-6)      # 0.7 x 粗簇下缘 2.0
        assert tmax == pytest.approx(3.75, abs=1e-6)     # 1.5 x 粗簇上缘 2.5

    def test_thick_line_book(self):
        """线更粗的书(细 2.0-3.0 / 粗 7.0-8.0): 分界 4.9/上限 12.0 —— 兜底 2.4/6.5 会误判"""
        v = [2.0] * 30 + [3.0] * 20 + [7.0] * 6 + [8.0] * 3
        h = [3.0] * 8 + [8.0] * 4
        tmin, tmax, _ = _ns(WZ6)['_calib_line_widths'](v, h)
        assert tmin == pytest.approx(4.9, abs=1e-6)
        assert tmax == pytest.approx(12.0, abs=1e-6)

    def test_no_samples(self):
        """无版框书(wz7 类): 样本为空 -> 不标定, 保留兜底(安全降级)"""
        tmin, tmax, why = _ns(WZ6)['_calib_line_widths']([], [])
        assert tmin is None and tmax is None and '样本' in why

    def test_single_cluster(self):
        """只有一簇(全是细线) -> 无有效两簇间隙 -> 不标定"""
        tmin, tmax, why = _ns(WZ6)['_calib_line_widths']([1.0] * 20, [1.0] * 8)
        assert tmin is None and '两簇' in why
