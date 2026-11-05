#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""圈码判据（纯函数，无 IO / 无 fitz），供 census_ring_digit.py 与单测共用。

物理对象（竖排）：圈码 = **一个整格大小的紧凑墨块**（圆环 + 圈内数字连成一片），
外径约 15-19pt（wz7 实测），而普通数字字形 8-13pt、两字竖叠 w≈13pt。

v1（旧，2026-10-24 commit 31da624）:  hole>=0.10 当必要条件
    缺陷：两位数把圈心填满 -> binary_fill_holes 找不到洞 -> 49/50/51/52 整类漏检。
v2（本轮，battle1 P0-a）: 去掉 hole，改「主块宽高尺寸窗 + 四边有墨」：
    w ∈ [14.5,19.5]pt，h ∈ [11.5,19.5]pt（短列窗口裁掉圈顶，h 下界松 3pt），
    edge >= 0.20（四边最薄边带有墨），ctr >= 0.15（圈里有墨，挡「〇」空圈），
    fill <= 0.85（挡实心块），0.60 <= w/h <= 1.70。

全部阈值可由调用方传入 p（dict），默认值即 wz7 标定值；`census_ring_digit.py` 用 env 覆盖。
"""

# 默认阈值（wz7 实测标定；改这里 = 改默认口径）
P_V1 = dict(hole_min=0.10, size_lo=14.0, size_hi=23.0,
            ctr_min=0.15, fill_max=0.78, ar_lo=0.6, ar_hi=1.7)
P_V2 = dict(w_lo=14.5, w_hi=19.5, h_lo=11.5, h_hi=19.5,
            edge_min=0.20, ctr_min=0.15, fill_max=0.85, ar_lo=0.6, ar_hi=1.7)


def _p(p, base):
    if not p:
        return base
    d = dict(base)
    d.update({k: v for k, v in p.items() if v is not None})
    return d


def judge_v1(w, h, hole, ctr, fill, ar, p=None):
    """v1（旧判据，回退用）：hole 必要条件 + 边长 14-23pt（只量 w，与旧实现一致）。"""
    q = _p(p, P_V1)
    return bool(hole >= q['hole_min'] and ctr >= q['ctr_min'] and fill <= q['fill_max']
                and q['ar_lo'] <= ar <= q['ar_hi'] and q['size_lo'] <= w <= q['size_hi'])


def judge_v2(w, h, edge, ctr, fill, ar, p=None):
    """v2（本轮）：主块尺寸窗（w/h）+ 四边有墨 + 形态 sanity；**不看 hole**。"""
    q = _p(p, P_V2)
    return bool(q['w_lo'] <= w <= q['w_hi'] and q['h_lo'] <= h <= q['h_hi']
                and edge >= q['edge_min'] and ctr >= q['ctr_min']
                and fill <= q['fill_max'] and q['ar_lo'] <= ar <= q['ar_hi'])
