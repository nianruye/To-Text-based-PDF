#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""普查漏掉的第二类圈码：格子里被 OCR 的「数字」占住的 ring

判据与任务E同源（径向剖面），只是**放开「该格必须有 OCR 字符」这条排除**：
  列框最后一格 / 第一格里 OCR 文本是数字（0-9 / ０-９，1-2 位）
  且源图那一格是圆环（外径 ≈ 一整格、圈心装着数字）
-> 这些是「圈码被 OCR 读成普通数字」，应当 1:1 换成 ①-⑳ / Unicode 圈码字形。

判据版本（env `VERT_RING_CRIT`，默认 v2）：
  v1（旧，2026-10-24 commit 31da624，**一键回退用**）
      hole>=0.10 且 ctr>=0.15 且 fill<=0.78 且 0.6<=ar<=1.7 且 14<=边长<=23pt
      缺陷：两位数把圈心填满 -> binary_fill_holes 找不到洞 -> 49/50/51/52… 整类漏检
  v2（本轮重标定，默认）
      **去掉 hole 必要条件**，改用「主块（面积最大的连通域）宽高尺寸窗」区分：
        w ∈ [14.5, 19.5]pt 且 h ∈ [11.5, 19.5]pt
      （圈码实测 15.0-18.8 × 12.7-18.0；普通数字字形 8-13pt / 手写页码块
       14.2×20.3、14.6×17.0、17.2×21.0+ —— w_lo=14.5 与最接近的反例 14.24 留约 0.3pt 余量）
      另加 edge>=0.20（四边最薄边带有墨）：真圈最小 0.42(600dpi)/0.24(900dpi)，
      手写页码 p1127 的「2」只有 0.10 -> 与尺寸窗互为独立闸门。
      另加 ctr>=0.15（圈里必须有墨，挡「〇」页码空圈）、fill<=0.85（挡实心团块）、
      0.6<=ar<=1.7。
      尺寸窗下界对 h 放宽到 11.5：短列（OCR 行框只有 1.2 格）窗口会裁掉圈顶 2-3pt，
      实测真圈码 h 最低 12.7，不是判据噪声。

双向标定（v2，全书 1-1748，600dpi）：
  正例  p1704 r5/r8/r10/r13 (49)、r14/r15/r16 (50)、p1705 r0 (50)/r15 (51)、
        p1706 r1-r17 (51×10 / 52×15)、p1684 (⑪⑫)、p1685 (⑬⑭) 全部报出
  反例  p5/p323/p410/p424/p484/p495/p561/p1108/p1127/p1171 的普通数字（含手写页码
        「49」「10」「8」「V.1」「V.2」「859.49」）全部 0 处
  全书  352 处 / 50 页（全在年表段 1684-1741；段外 0）
        v1（hole>=0.10）184 处 / 42 页，段外 0；
        v1 只把 hole 放宽到 0 得 353 处 / 54 页、段外 4 处假阳（p424/p484/p495/p1127r2）
  增量解释：v1 的 hole 门槛恰好只让「圈心还留洞」的宽数字圈过检，
        两位数圈（49/50/51/52…）圈心被数字填满 hole 0.03-0.10 被整类拒掉；
        v2 用尺寸窗后把 168 个两位数圈补回（含 p1704-1706 的 49/50/51/52），
        同时段外 14 个普通数字候选仍全部拒绝。

用法：
  /usr/bin/python3 src/tools/census_ring_digit.py 1700 1730     # 小范围标定
  /usr/bin/python3 src/tools/census_ring_digit.py 1 1748        # 全书
  VERT_RING_CRIT=v1 ...                                         # 旧判据（回退验证）
  VERT_RING_DPI=900 ...                                         # 900dpi 复核
  VERT_RING_DUMP=1 ...                                          # 落全部候选明细
明细 -> tmp_vert/cj5/ring_digit_census.json（命中）
        tmp_vert/cj5/ring_digit_cands.json（VERT_RING_DUMP=1 时：全部候选 + 主块特征）
"""
import json
import os
import re
import sys

import numpy as np
import fitz
from scipy import ndimage

from ring_judge import judge_v1 as _judge_v1, judge_v2 as _judge_v2

LINES = 'data/wz7_full/wz7_full_spotting_lines_patched.json'
COORDS = 'data/wz7_full/wz7_full_spotting_coords.json'
SRC = 'source_pdf/wz7.pdf'
P0, P1 = int(sys.argv[1]) if len(sys.argv) > 1 else 1, int(sys.argv[2]) if len(sys.argv) > 2 else 1748

# ---- 判据参数（全部可 env 覆盖；v1 一键回退） ----
CRIT = (os.environ.get('VERT_RING_CRIT') or 'v2').strip().lower()
DPI = int(os.environ.get('VERT_RING_DPI') or 600)
# v2: 主块尺寸窗（pt）。w 是圈的外径（竖排里水平方向），h 是沿列方向；短列窗口会裁掉圈顶，
#     故 h 下界比 w 下界松 3.5pt（实测真圈码 h_min=12.7，v1 靠 hole 也检不到它们）。
W_LO = float(os.environ.get('VERT_RING_W_LO') or 14.5)
W_HI = float(os.environ.get('VERT_RING_W_HI') or 19.5)
H_LO = float(os.environ.get('VERT_RING_H_LO') or 11.5)
H_HI = float(os.environ.get('VERT_RING_H_HI') or 19.5)
CTR_MIN = float(os.environ.get('VERT_RING_CTR_MIN') or 0.15)
EDGE_MIN = float(os.environ.get('VERT_RING_EDGE_MIN') or 0.20)   # 四边最薄边带有墨（圈的外框）
FILL_MAX = float(os.environ.get('VERT_RING_FILL_MAX') or 0.85)
AR_LO = float(os.environ.get('VERT_RING_AR_LO') or 0.6)
AR_HI = float(os.environ.get('VERT_RING_AR_HI') or 1.7)
# v1（旧判据，回退用）
HOLE_MIN = float(os.environ.get('VERT_RING_HOLE_MIN') or 0.10)
V1_SIZE_LO = float(os.environ.get('VERT_RING_V1_SIZE_LO') or 14.0)
V1_SIZE_HI = float(os.environ.get('VERT_RING_V1_SIZE_HI') or 23.0)
# 判据实现集中在 src/tools/ring_judge.py（纯函数，单测锁定）；这里只做 env -> 参数
_PJ = dict(w_lo=W_LO, w_hi=W_HI, h_lo=H_LO, h_hi=H_HI, edge_min=EDGE_MIN,
           ctr_min=CTR_MIN, fill_max=FILL_MAX, ar_lo=AR_LO, ar_hi=AR_HI)
_PJ1 = dict(hole_min=HOLE_MIN, size_lo=V1_SIZE_LO, size_hi=V1_SIZE_HI,
            ctr_min=CTR_MIN, fill_max=0.78, ar_lo=AR_LO, ar_hi=AR_HI)

sl = json.load(open(LINES, encoding='utf-8'))
co = json.load(open(COORDS, encoding='utf-8'))
src = fitz.open(SRC)
DIG = re.compile(r'[0-9\uff10-\uff19]+$')

cands = []
for k in sl:
    pi = int(k) + 1
    if not (P0 <= pi <= P1):
        continue
    rows = sl[k] or []
    boxes = co.get(k) or []
    for i, t in enumerate(rows):
        t = str(t).replace('\n', '')
        if not t or i >= len(boxes):
            continue
        m = DIG.search(t)
        if not m:
            continue
        num = m.group()
        if len(num) > 2:
            continue
        # 纯 0（'0'/'00'）= OCR 把「〇」读成数字，是页码/卷次，不是圈码
        if num.strip('0\uff10') == '':
            continue
        xs = [q[0] / 2.0 for q in boxes[i]]
        ys = [q[1] / 2.0 for q in boxes[i]]
        cands.append(dict(page=pi, row=i, text=t, num=num, n=len(t),
                          x0=min(xs), x1=max(xs), y0=min(ys), y1=max(ys)))

print('判据=%s dpi=%d%s' % (CRIT, DPI,
      ('  w[%.1f,%.1f] h[%.1f,%.1f] edge>=%.2f ctr>=%.2f fill<=%.2f ar[%.2f,%.2f]'
       % (W_LO, W_HI, H_LO, H_HI, EDGE_MIN, CTR_MIN, FILL_MAX, AR_LO, AR_HI)) if CRIT == 'v2'
      else ('  hole>=%.2f 边长[%.1f,%.1f]' % (HOLE_MIN, V1_SIZE_LO, V1_SIZE_HI))))
print('列尾是数字的列: %d 处 / %d 页' % (len(cands), len(set(c['page'] for c in cands))))

# 本页真实步进：取 n>=8 的长列的「框高/字数」中位。
#   短列（如 '。12' 3 字）的框高/字数 不是步进（p1684 行14: 13.4 vs 真实 18.5），
#   按它开窗口会把 18.7pt 的圆环裁掉。
def _page_step(k):
    st = []
    for t, p in zip(sl.get(k, []), co.get(k, []) or []):
        t = str(t).replace('\n', '')
        if len(t) < 8 or not p:
            continue
        ys = [q[1] / 2.0 for q in p]
        st.append((max(ys) - min(ys)) / len(t))
    if not st:
        return None
    st.sort()
    return st[len(st) // 2]


def ring_at(c, page_step=None):
    """量列尾最后一格的圆环特征。返回 (best, 全部候选主块特征)。
    窗口口径不变（v1/v2 同）：列末 **1 格** = [y1-step, y1]（step = 本页长列步进中位）；
    历史实测「列末 2 格」会让检出变少（184->156），窗口不动。"""
    step = page_step or ((c['y1'] - c['y0']) / max(1, c['n']))
    pg = src[c['page'] - 1]
    ya = c['y1'] - step
    clip = fitz.Rect(max(0, c['x0'] - 1), ya, min(pg.rect.width, c['x1'] + 1), c['y1'] + 1)
    if clip.height < 3 or clip.width < 3:
        return None, None
    pm = pg.get_pixmap(clip=clip, dpi=DPI)
    a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)
    g = a[:, :, :3].mean(axis=2)
    m = g < (float(np.median(g)) - 20)
    lab, n = ndimage.label(m)
    if n == 0:
        return None, None
    kk = 72.0 / DPI
    best = None
    comps = []
    for idx, sl_ in enumerate(ndimage.find_objects(lab), start=1):
        if sl_ is None:
            continue
        ys_, xs_ = sl_
        hh, ww = ys_.stop - ys_.start, xs_.stop - xs_.start
        if hh < 6 or ww < 6:
            continue
        sub = (lab[ys_, xs_] == idx)
        H, W = sub.shape
        def q(a0, a1, b0, b1):
            b = sub[int(a0*H):max(int(a1*H), int(a0*H)+1), int(b0*W):max(int(b1*W), int(b0*W)+1)]
            return float(b.mean()) if b.size else 1.0
        ctr = q(.35, .65, .35, .65)
        edge = min(q(.2,.8,0,.2), q(.2,.8,.8,1.), q(0,.2,.2,.8), q(.8,1.,.2,.8))
        # 洞（v1 的必要条件；v2 只记录，不参与判据）
        filled = ndimage.binary_fill_holes(sub)
        hole = float((filled & ~sub).sum()) / float(sub.size)
        ar = ww / float(hh)
        fill = float(sub.mean())
        w_pt, h_pt = ww * kk, hh * kk
        feat = dict(w=round(w_pt, 2), h=round(h_pt, 2), area=round(w_pt * h_pt, 2),
                    ctr=round(ctr, 3), edge=round(edge, 3), hole=round(hole, 3),
                    ar=round(ar, 3), fill=round(fill, 3),
                    # 页绝对坐标（pt，左上原点）：供裁图/人工复核
                    ax=round(clip.x0 + xs_.start * kk, 2), ay=round(clip.y0 + ys_.start * kk, 2))
        if CRIT == 'v1':
            ok = _judge_v1(w_pt, h_pt, hole, ctr, fill, ar, _PJ1)
        else:
            ok = _judge_v2(w_pt, h_pt, edge, ctr, fill, ar, _PJ)
        comps.append(dict(feat, ok=bool(ok)))
    comps.sort(key=lambda d: -d['area'])
    # ★ 判据只看**主块**（面积最大的连通域），不是「任一通过的分量」。
    #   实测 p5 的「V.1」手写页码：主块 15.0x27.0（h 超窗）但窗口里另有 15.7x20.3 的碎片，
    #   若允许「任一通过」就会假阳（2026-10-24 首版 v2 实测 353 处 / 段外 1 处，即此）。
    #   圈码的物理形态是「一圈+圈内数字连成一片」的主块（250-270pt²），远大于邻字（~100pt²）。
    if comps and comps[0]['ok']:
        best = (0, dict(comps[0], crit=CRIT, k=kk, hh=round(comps[0]['h'], 1)))
    return (best[1] if best else None), comps


hits = []
allrows = []
_pstep_cache = {}
for c in cands:
    _k = str(c['page'] - 1)
    if _k not in _pstep_cache:
        _pstep_cache[_k] = _page_step(_k)
    r, comps = ring_at(c, _pstep_cache[_k])
    rec = dict(c, step=round(_pstep_cache[_k], 2) if _pstep_cache[_k] else None,
               ncomp=len(comps or []), main=(comps[0] if comps else None))
    allrows.append(rec)
    if r:
        hits.append(dict(c, **r))
print()
print('其中源图列尾格是圆环的: %d 处 / %d 页'
      % (len(hits), len(set(h['page'] for h in hits))))
from collections import Counter
print('  涉及页: %s' % sorted(Counter(h['page'] for h in hits).items())[:25])
print()
print('  前 20 处:')
for h in hits[:20]:
    print('    p%-5d 行%-3d 列尾数字 %-4r 环 ctr%.2f edge%.2f hole%.2f fill%.2f w%.1f h%.1f  文本 %r'
          % (h['page'], h['row'], h['num'], h['ctr'], h['edge'], h['hole'], h['fill'], h['w'], h['h'],
             h['text'][-16:]))

# 段外（年表段 1682-1741 之外）命中单独打印 —— 双向标定要求这里是 0
_out = [h for h in hits if not (1682 <= h['page'] <= 1741)]
print()
print('段外命中(应为 0): %d 处 %s' % (len(_out), [(h['page'], h['row'], h['num']) for h in _out[:20]]))
json.dump(hits, open('tmp_vert/cj5/ring_digit_census.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
if os.environ.get('VERT_RING_DUMP') not in (None, '', '0'):
    json.dump(allrows, open('tmp_vert/cj5/ring_digit_cands.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('候选明细 -> tmp_vert/cj5/ring_digit_cands.json')
print()
print('明细 -> tmp_vert/cj5/ring_digit_census.json')
src.close()
