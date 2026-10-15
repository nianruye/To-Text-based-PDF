#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskM：竖排参数自标定（§1.955 列数 / §1.956 源图+探针 -> 排版参数）的纯函数测试。

被测实现：`src/pipelines/build_vert.py`
  · §1.955 `_calib_ncol_page` / `_calib_ncol_pick`      —— 版框列数(内框宽÷列距 + 界行线条数)
  · §1.956 `_calib_xscale` / `_calib_punct_size` / `_calib_punct_pos` / `_calib_br_forms`
                                                        —— 面积比 / 标点字号 / 标点摆位 / 括号分档
  · §1.956 `_calib_match_small`                         —— 小字预测位置 ↔ 实测标记 单调配对(DP)
  · §1.956 `_calib_med` / `_calib_p75` / `_calib_corpus` / `_calib_apply` / `_parse_br_map`
  · `CALIB_DEF` 兜底表与代码里各常量默认值的一致性(标定失效时的兜底口径)
用 _loader 从脚本里 ast 提取纯函数(不 import fitz/scipy、不跑 upLaTeX、不读源图)。

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_calib.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_FUNCS = ['_calib_med', '_calib_p75', '_calib_corpus', '_parse_br_map', '_calib_apply',
          '_calib_ncol_page', '_calib_ncol_pick', '_calib_match_small',
          '_calib_xscale', '_calib_punct_size', '_calib_punct_pos', '_calib_br_forms']
_CONSTS = ['CALIB_DEF', 'CALIB_DEF_BR', 'CALIB_F_MIN', 'BR_FAMILY', 'FAM_FORMS', 'FAM_OF_FORM',
           'VERT_FORMS', 'PUNCT_HANG', '_CALIB_ENV', 'CALIB_N_PAGE', 'CALIB_RARE_PAGE',
           'XSCALE', 'PUNCT_SIZE', 'PUNCT_DX', 'PUNCT_DY', 'GAP_HANG', 'BR_SIZE', 'BR_SIZE_DEF',
           'INK_RATIO', 'INK_ASC', 'NOTE_INK_RATIO', 'NOTE_INK_MAX', 'N_COL_FRAME', 'CALIB_F_DEF']

# 各常量对应的 env 覆盖名(与代码里 _CALIB_ENV 之外的定义处一致)
_ENVS = ['VERT_XSCALE', 'VERT_PUNCT_SIZE', 'VERT_PUNCT_DX', 'VERT_PUNCT_DY', 'VERT_GAP_HANG',
         'VERT_BR_SIZE', 'VERT_BR_SIZE_MAP', 'VERT_INK_RATIO', 'VERT_INK_ASC',
         'VERT_NOTE_INK_RATIO', 'VERT_NOTE_INK_MAX', 'VERT_NCOL_FRAME']


@pytest.fixture(scope='module')
def ns():
    return load('build_vert.py', _FUNCS, _CONSTS)


# ---------- A. 版框列数(§1.955) ----------
class TestNCol:
    def test_frame_dict(self, ns):
        """正常版框: 内框 521.4pt / 列距 43.45pt = 12 列; 13 条细线 -> n②=12; 实测线跨距同 -> n③=12"""
        g = {'in_l': 36.3, 'in_r': 557.7, 'pitch': 43.45,
             'thin': [36.3 + i * 43.45 for i in range(13)]}
        assert ns['_calib_ncol_page'](g) == (12, 12, 12)

    def test_other_column_count(self, ns):
        """别的书: 10 列版框(内框 400pt / 列距 40pt) -> 12 不是普适常数, 标定必须测出来"""
        g = {'in_l': 50.0, 'in_r': 450.0, 'pitch': 40.0, 'thin': [50.0 + i * 40 for i in range(11)]}
        assert ns['_calib_ncol_page'](g) == (10, 10, 10)

    def test_unmeasurable(self, ns):
        """无版框 / 列距异常 / 细线太少 -> None(调用方回落兜底 12)"""
        assert ns['_calib_ncol_page'](None) is None
        assert ns['_calib_ncol_page']({'in_l': 0, 'in_r': 100, 'pitch': 2.0, 'thin': [1, 2, 3, 4, 5, 6]}) is None
        assert ns['_calib_ncol_page']({'in_l': 0, 'in_r': 500, 'pitch': 43.0, 'thin': [1, 2, 3]}) is None

    def test_pick_prefers_agreement(self, ns):
        """①内框宽÷列距 与 ③实测线跨距÷列距 一致者优先(两条独立口径互证)"""
        n, why = ns['_calib_ncol_pick']([(12, 11, 12), (12, 12, 12), (11, 12, 11)])
        assert n == 12 and '①=③' in why

    def test_pick_falls_back_to_line_count(self, ns):
        """①③ 全不一致时退 ②(界行线条数-1) 的众数"""
        n, why = ns['_calib_ncol_pick']([(12, 11, 13), (11, 11, 13)])
        assert n == 11 and '②' in why

    def test_pick_empty(self, ns):
        n, why = ns['_calib_ncol_pick']([])
        assert n is None


# ---------- B. 小字配对(§1.956 DP) ----------
class TestMatchSmall:
    P = [('punct', 1, '，', 100.0, 'top'), ('brk', 3, '（', 150.0, 'center')]

    def test_exact(self, ns):
        marks = [(99.0, 105.0, 40.0, 4.0, 6.0, 'punct'), (148.0, 153.0, 42.0, 18.0, 5.0, 'brk')]
        got = ns['_calib_match_small'](self.P, marks, 15.0)
        assert [(g[0], g[2]) for g in got] == [(1, 'punct'), (3, 'brk')]

    def test_kind_mismatch_not_paired(self, ns):
        """形态分类不同(扁长条 vs 紧凑块)不配 —— 防止把邻字的横笔画当成标点"""
        marks = [(99.0, 105.0, 40.0, 18.0, 6.0, 'brk')]
        assert [g for g in ns['_calib_match_small']([self.P[0]], marks, 15.0)] == []

    def test_out_of_tolerance(self, ns):
        marks = [(140.0, 146.0, 40.0, 4.0, 6.0, 'punct')]        # 预测 100, 实测 140 -> 超容差
        assert ns['_calib_match_small']([self.P[0]], marks, 15.0) == []

    def test_picks_nearer_of_two(self, ns):
        """两个同形候选, 取更近的那个(DP 代价 = |Δ|/tol)"""
        marks = [(90.0, 96.0, 40.0, 4.0, 6.0, 'punct'), (99.0, 105.0, 40.0, 4.0, 6.0, 'punct')]
        got = ns['_calib_match_small']([self.P[0]], marks, 15.0)
        assert got[0][3][0] == 99.0

    def test_monotone_order(self, ns):
        """文本序与墨迹序都随 y 单调 -> 配对不得交叉"""
        preds = [('punct', 1, '。', 100.0, 'top'), ('punct', 5, '，', 130.0, 'top')]
        marks = [(99.0, 105.0, 40.0, 4.0, 6.0, 'punct'), (129.0, 135.0, 40.0, 4.0, 6.0, 'punct')]
        got = ns['_calib_match_small'](preds, marks, 15.0)
        assert [(g[0], g[3][0]) for g in got] == [(1, 99.0), (5, 129.0)]


# ---------- C. 基本统计工具 ----------
class TestStats:
    def test_med(self, ns):
        assert ns['_calib_med']([3.0, 1.0, 2.0]) == 2.0
        assert ns['_calib_med']([]) is None

    def test_p75_upper_quartile(self, ns):
        """p75 取上四分位(不插值): 8 个样本 -> 第 6 大的(下标 round(0.75*7)=5)"""
        v = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        assert ns['_calib_p75'](v) == 6.0
        assert ns['_calib_p75']([]) is None

    def test_p75_is_robust_to_small_fragments(self, ns):
        """双峰样本(真值 0.24 / 碎片 0.13): p75 落在真值峰上, 中位落在两峰之间(偏低)"""
        v = [0.13, 0.13, 0.13, 0.13, 0.24, 0.24, 0.24, 0.24]
        assert ns['_calib_p75'](v) == 0.24
        assert ns['_calib_med'](v) < 0.24

    def test_corpus_frequency_and_filter(self, ns):
        """语料 = 按字频取前 n 个 CJK 汉字(排除标点/拉丁)"""
        txt = ['國國國人民', 'abc，人民12']
        c = ns['_calib_corpus'](txt, 3)
        assert c[0] == '國' and set(c) == {'國', '人', '民'}

    def test_parse_br_map(self, ns):
        m = ns['_parse_br_map']('︗:0.5, ︘:0.6 , 坏项,：:x')
        assert m == {'︗': 0.5, '︘': 0.6}
        assert ns['_parse_br_map']('') == {}


# ---------- D. XSCALE / 标点 / 括号(§1.956) ----------
class TestParams:
    # probe: {字: (墨宽em, 墨高em, 墨心x_em, 墨心y_em, 墨面积em², 墨顶距基准线em)}
    PROBE = {'國': (0.90, 0.90, 0.5, 0.45, 0.30, 0.95), '人': (0.88, 0.88, 0.5, 0.44, 0.28, 0.94),
             '。': (0.26, 0.26, 0.5, 0.38, 0.05, 0.52), '，': (0.15, 0.20, 0.45, 0.35, 0.02, 0.45)}

    def test_xscale_area_ratio(self, ns):
        """K = 源书「墨面积/墨高²」中位 ÷ 渲染同口径中位 —— x 压缩 K 使面积 xK、墨高不变"""
        src = [(30.0, 20.0, 900.0)]                 # a/h² = 900/900 = 1.0
        probe = {'國': (0.9, 0.9, 0.5, 0.45, 0.5, 0.95)}    # 0.5/0.81 = 0.6173
        assert ns['_calib_xscale'](src, probe, ['國']) == 1.62

    def test_xscale_needs_both_sides(self, ns):
        assert ns['_calib_xscale']([], self.PROBE, ['國']) is None
        assert ns['_calib_xscale']([(30.0, 20.0, 900.0)], {}, ['國']) is None

    def test_punct_size(self, ns):
        """源书标点墨高/正文字高 x 渲染正文墨高em/渲染标点墨高em
        -> 0.21(源墨高比中位) x 0.90(正文墨高em) / 0.23(渲染标点墨高em 中位) = 0.822"""
        small = [('，', 'punct', 0.20, 0.10, 0.8, 0.9, 0.8), ('。', 'punct', 0.22, 0.1, 0.8, 0.9, 0.8)]
        assert ns['_calib_punct_size'](small, self.PROBE, 0.90) == 0.822
        assert ns['_calib_punct_size']([], self.PROBE, 0.90) is None

    def test_punct_pos(self, ns):
        small = [('，', 'punct', 0.2, 0.1, 0.80, 0.86, 0.79), ('。', 'punct', 0.2, 0.1, 0.78, 0.84, 0.81)]
        dy, dx, gh = ns['_calib_punct_pos'](small)
        assert (dy, dx, gh) == (0.85, 0.8, 0.79)
        assert ns['_calib_punct_pos']([('（', 'brk', 0.2, 0.5, None, 0.5, 0.5)]) == (None, None, None)

    def test_br_forms_formula(self, ns):
        """s_h = 源高比×正文墨高em/渲染括号墨高em; s_w = 源宽比×正文墨高em/(渲染墨宽em×XSCALE);
        s = sqrt(s_h×s_w)"""
        small = [('（', 'brk', 0.24, 0.60, None, 0.50, 0.50)] * 4
        probe = {'︵': (0.90, 0.30, 0.5, 0.1, 0.1, 0.2), '︶': (0.90, 0.30, 0.5, 0.7, 0.1, 0.8)}
        R = ns['_calib_br_forms'](['︵', '︶'], small, probe, 0.90, 0.90, 0.87)
        s_h = 0.24 * 0.90 / 0.30
        s_w = 0.60 * 0.90 / (0.90 * 0.87)
        assert R['n'] == 4
        assert abs(R['s_h'] - s_h) < 1e-9 and abs(R['s_w'] - s_w) < 1e-9
        assert abs(R['s'] - round((s_h * s_w) ** 0.5, 3)) < 1e-9

    def test_br_forms_position_qc(self, ns):
        """墨心跑到本格外(d_cy=1.2/0.0)= 配到邻格碎片 -> 质检剔除, 样本不足则不给值"""
        good = [('（', 'brk', 0.24, 0.60, None, 0.50, 0.50)] * 4
        bad = [('（', 'brk', 0.48, 0.90, None, 1.20, 0.50)]
        probe = {'︵': (0.90, 0.30, 0.5, 0.1, 0.1, 0.2)}
        R1 = ns['_calib_br_forms'](['︵'], good + bad, probe, 0.9, 0.9, 0.87)
        assert R1['n'] == 4 and abs(R1['src_hh'] - 0.24) < 1e-9      # 坏样本被剔除(不计入估计)
        R2 = ns['_calib_br_forms'](['︵'], bad, probe, 0.9, 0.9, 0.87)
        assert R2['s'] is None                                       # 只剩坏样本 -> 不给值(回落总中位)

    def test_br_forms_low_sample_uses_max(self, ns):
        """样本 1..MIN-1 时取**最大值**(漏检只会把标记测小), >=MIN 时取 p75"""
        probe = {'︵': (0.90, 0.30, 0.5, 0.1, 0.1, 0.2)}
        few = [('（', 'brk', 0.24, 0.60, None, 0.50, 0.50), ('（', 'brk', 0.12, 0.30, None, 0.50, 0.50)]
        R = ns['_calib_br_forms'](['︵'], few, probe, 0.9, 0.9, 0.87)
        assert R['n'] == 2 and abs(R['src_hh'] - 0.24) < 1e-9

    def test_br_forms_ignores_other_families(self, ns):
        """只收属于本族的括号样本(别的族同形不吃)"""
        other = [('「', 'brk', 0.24, 0.60, None, 0.50, 0.50)] * 5
        probe = {'︵': (0.90, 0.30, 0.5, 0.1, 0.1, 0.2)}
        R = ns['_calib_br_forms'](['︵'], other, probe, 0.9, 0.9, 0.87)
        assert R['n'] == 0 and R['s'] is None


# ---------- E. 兜底表 / env 优先级 ----------
class TestFallback:
    def test_calib_def_matches_code_defaults(self, monkeypatch):
        """CALIB_DEF 的兜底值必须与代码里各常量的**默认值**一致(不设 env 时) —— 否则标定失效时
        的兜底口径与对账表的「兜底值」列都会失真。"""
        for e in _ENVS:
            monkeypatch.delenv(e, raising=False)
        live = load('build_vert.py', [], _CALIB_DEF_KEYS + ['BR_SIZE', 'N_COL_FRAME'])
        for k in _CALIB_DEF_KEYS:
            assert abs(live[k] - _CALIB_DEF_REF[k]) < 1e-9, k
        assert live['BR_SIZE'] == {'︗': 0.55, '︘': 0.55, '︹': 0.49, '︺': 0.49}
        assert live['N_COL_FRAME'] == 12

    def test_apply_env_wins(self, ns, monkeypatch):
        """显式 env 优先于标定值: 来源标 env, 生效值是**定义处取到的 env 值**(这里 ns 是在设 env
        之前提取的, 故 XSCALE=0.87 默认值), 且标定值不写回全局"""
        monkeypatch.setenv('VERT_XSCALE', '0.95')
        v, src = ns['_calib_apply']('XSCALE', 0.86)
        assert src == 'env' and v == ns['XSCALE'] == 0.87

    def test_apply_calibrated(self, ns, monkeypatch):
        """无 env 时用标定值, 并写回全局; 标定值为 None 时用兜底表"""
        monkeypatch.delenv('VERT_PUNCT_SIZE', raising=False)
        v, src = ns['_calib_apply']('PUNCT_SIZE', 0.66)
        assert (v, src) == (0.66, '标定') and ns['PUNCT_SIZE'] == 0.66
        v2, src2 = ns['_calib_apply']('PUNCT_SIZE', None)
        assert src2 == '兜底' and v2 == ns['CALIB_DEF']['PUNCT_SIZE']

    def test_br_map_env_override(self, monkeypatch):
        """VERT_BR_SIZE_MAP 按类覆盖 BR_SIZE(标定/兜底之外的人工口子)"""
        monkeypatch.setenv('VERT_BR_SIZE_MAP', '︗:0.55,︹:0.49')
        ns2 = load('build_vert.py', _FUNCS, _CONSTS)
        assert ns2['BR_SIZE'] == {'︗': 0.55, '︹': 0.49, '︘': 0.55, '︺': 0.49}


# CALIB_DEF 的键 -> 代码里对应常量名(用于兜底一致性校验)
_CALIB_DEF_KEYS = ['XSCALE', 'PUNCT_SIZE', 'PUNCT_DX', 'PUNCT_DY', 'GAP_HANG', 'BR_SIZE_DEF',
                   'INK_RATIO', 'INK_ASC', 'NOTE_INK_RATIO', 'NOTE_INK_MAX']
_CALIB_DEF_REF = {'XSCALE': 0.87, 'PUNCT_SIZE': 0.62, 'PUNCT_DX': 0.81, 'PUNCT_DY': 0.85,
                  'GAP_HANG': 0.85, 'BR_SIZE_DEF': 0.66, 'INK_RATIO': 0.88, 'INK_ASC': 0.94,
                  'NOTE_INK_RATIO': 0.88, 'NOTE_INK_MAX': 0.94}
