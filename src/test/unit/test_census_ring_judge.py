#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""battle1 P0-a：圈码判据 v1/v2（`src/tools/ring_judge.py`）的回归锁定。

被测对象是**纯函数**，样本全部是 2026-10-24/25 在 wz7 源图 900dpi/600dpi 的实测值
（见 docs/battle1_vertical_ring.md §3/§4），不读 data/ 与源 PDF，CI 可跑。

契约：
  ① v2 必须报出两位数圈（49/50/51/52）——v1 因 hole 必要条件整类漏检；
  ② v2 必须拒绝段外普通数字/手写页码 8 个实测反例（含同数字「49」的 p1171）；
  ③ v2 不使用 hole（同几何 hole=0 / 0.5 结论相同）；
  ④ 尺寸窗/edge 闸门的边界行为固定；
  ⑤ v1 一键回退口径固定（hole>=0.10 + 边长 14-23，只量 w）。
运行：/usr/bin/python3 -m pytest src/test/unit/test_census_ring_judge.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))

from ring_judge import judge_v1, judge_v2, P_V1, P_V2   # noqa: E402

# ---- wz7 源图实测样本 (w, h, edge, ctr, fill, ar) ----
POS = [
    # 用户报的三页（两位数，hole 0.04-0.15 -> v1 全灭或大半灭）
    ('p1704r5 49', 16.48, 15.76, 0.68, 0.99, 0.69, 1.05, 0.07),
    ('p1704r13 49', 15.76, 15.76, 0.58, 1.00, 0.66, 1.00, 0.09),
    ('p1704r14 50', 16.48, 16.24, 0.64, 0.96, 0.70, 1.01, 0.04),
    ('p1705r0 50', 15.76, 15.76, 0.64, 0.90, 0.68, 1.00, 0.09),
    ('p1705r15 51', 15.76, 16.56, 0.61, 0.71, 0.66, 0.95, 0.11),
    ('p1706r1 51', 15.76, 15.76, 0.69, 0.64, 0.66, 1.00, 0.14),
    ('p1706r7 52', 15.68, 15.76, 0.67, 0.93, 0.69, 1.00, 0.09),
    ('p1706r10 52', 15.76, 15.60, 0.62, 0.88, 0.69, 1.01, 0.08),
    # 老正例（v1 也能报；v2 不得回退）
    ('p1684r2 11', 18.00, 16.16, 0.47, 0.28, 0.53, 1.11, 0.31),
    ('p1685r12 14', 17.20, 16.48, 0.58, 0.59, 0.59, 1.04, 0.24),
]
NEG = [
    # 段外普通数字/手写页码（900dpi 实测，见报告 §3）
    ('p5 V.1', 14.96, 26.96, 0.21, 0.75, 0.45, 0.55, 0.06),
    ('p323 10', 34.48, 29.36, 0.52, 0.13, 0.39, 1.17, 0.40),
    ('p424 8', 14.24, 20.32, 0.62, 0.87, 0.70, 0.70, 0.08),
    ('p484 8', 17.28, 26.96, 0.31, 0.52, 0.53, 0.64, 0.08),
    ('p495 8', 17.28, 20.96, 0.26, 0.84, 0.55, 0.82, 0.04),
    ('p561 V.2', 15.76, 27.12, 0.12, 0.28, 0.50, 0.58, 0.00),
    ('p1108 8', 12.72, 16.56, 0.51, 0.52, 0.56, 0.77, 0.08),
    ('p1127r2 2', 14.56, 16.96, 0.10, 0.74, 0.53, 0.86, 0.05),
    ('p1171 49', 39.76, 31.44, 0.01, 0.40, 0.33, 1.26, 0.07),
]


def test_v2_reports_double_digit_rings_that_v1_misses():
    """① 两位数圈码：v2 必报；其中 hole<0.10 的 v1 必须拒（复现用户 bug 的根因）。"""
    for name, w, h, e, c, f, ar, hole in POS:
        assert judge_v2(w, h, e, c, f, ar), name
    missed = [n for n, w, h, e, c, f, ar, hole in POS if hole < P_V1['hole_min']]
    assert 'p1704r5 49' in missed and 'p1704r14 50' in missed
    for name, w, h, e, c, f, ar, hole in POS:
        if hole < P_V1['hole_min']:
            assert not judge_v1(w, h, hole, c, f, ar), '%s：v1 应因无洞拒掉' % name


def test_v2_rejects_out_of_year_table_ordinary_digits():
    """② 段外 9 个实测反例全部 0（含同数字「49」的 p1171 与最接近的 p1127r2）。"""
    for name, w, h, e, c, f, ar, hole in NEG:
        assert not judge_v2(w, h, e, c, f, ar), name


def test_v2_ignores_hole():
    """③ hole 不再是判据：同几何 hole=0/0.05/0.5 结论相同。"""
    w, h, e, c, f, ar = 16.48, 15.76, 0.68, 0.99, 0.69, 1.05
    assert judge_v2(w, h, e, c, f, ar)
    # v1 对同一几何：hole 0.00/0.05 拒、0.10/0.50 过（旧口径的可分性只来自「有没有洞」）
    assert not judge_v1(w, h, 0.00, c, f, ar)
    assert not judge_v1(w, h, 0.05, c, f, ar)
    assert judge_v1(w, h, 0.10, c, f, ar)
    assert judge_v1(w, h, 0.50, c, f, ar)


def test_v2_boundaries():
    """④ 尺寸窗 / edge / ctr / fill / ar 的边界（含 600dpi 真圈最小值）。"""
    assert judge_v2(16.0, 16.0, 0.60, 0.90, 0.70, 1.00)
    # 真圈最窄 14.96、最短 12.72、最小 edge 0.237（900dpi）
    assert judge_v2(14.96, 12.72, 0.237, 0.28, 0.53, 1.11)
    # w 窗
    assert judge_v2(14.50, 16.0, 0.60, 0.90, 0.70, 1.00)
    assert not judge_v2(14.49, 16.0, 0.60, 0.90, 0.70, 1.00)
    assert judge_v2(19.50, 16.0, 0.60, 0.90, 0.70, 1.00)
    assert not judge_v2(19.51, 16.0, 0.60, 0.90, 0.70, 1.00)
    # h 窗
    assert judge_v2(16.0, 11.50, 0.60, 0.90, 0.70, 1.00)
    assert not judge_v2(16.0, 11.49, 0.60, 0.90, 0.70, 1.00)
    assert judge_v2(16.0, 19.50, 0.60, 0.90, 0.70, 1.00)
    assert not judge_v2(16.0, 19.51, 0.60, 0.90, 0.70, 1.00)
    # edge 闸门
    assert judge_v2(16.0, 16.0, 0.20, 0.90, 0.70, 1.00)
    assert not judge_v2(16.0, 16.0, 0.199, 0.90, 0.70, 1.00)
    # ctr / fill / ar
    assert not judge_v2(16.0, 16.0, 0.60, 0.149, 0.70, 1.00)
    assert not judge_v2(16.0, 16.0, 0.60, 0.90, 0.851, 1.00)
    assert not judge_v2(16.0, 16.0, 0.60, 0.90, 0.70, 0.59)
    assert not judge_v2(16.0, 16.0, 0.60, 0.90, 0.70, 1.71)


def test_judge_params_override():
    """⑤ 阈值全部可由调用方覆盖（census 用它接 env；回退/换书标定都走这里）。"""
    assert not judge_v2(16.0, 16.0, 0.10, 0.90, 0.70, 1.00)
    assert judge_v2(16.0, 16.0, 0.10, 0.90, 0.70, 1.00, p=dict(edge_min=0.05))
    assert judge_v2(14.0, 16.0, 0.60, 0.90, 0.70, 1.00, p=dict(w_lo=14.0))
    assert judge_v1(16.0, 16.0, 0.05, 0.90, 0.70, 1.00, p=dict(hole_min=0.00))
    assert P_V2['edge_min'] == 0.20 and P_V1['hole_min'] == 0.10
