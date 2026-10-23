#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全书普查「OCR 漏识的占整格元素」（破折号 / 圈码 / 其他符号）—— taskE。

只做普查 + 分类，不改渲染端。判据（三条缺一不可，详见 docs/vert_taskE_census.md）：

  ① 连通域：源图该列框内二值化（逐页 Otsu，与 build_vert 的 NF 路径同口径）后做连通域；
  ② 形状：候选是**首/末格的独立元素**（按 y 重叠聚簇，不能是汉字笔画碎片）；
     · dash：宽 ≤ 7pt、高 ≥ 12pt、高/宽 ≥ 2.5、高 ∈ [0.8,1.8]×该页字步进、fill ≥ 0.45；
     · ring：0.6 ≤ 宽/高 ≤ 1.7、6 ≤ 高 ≤ 40pt、高 ∈ [0.80,1.10]×步进、
             外圈中心空(最大分量中心填充 < 0.35)、有洞(hole ≥ 0.10)、
             圈内有墨(团块中心墨 ≥ 0.03，即圈码里的数字/点)、洞数 ≤ 3、四边最小值 < 0.50
             （方框汉字如「回/日/時」的四边填充更高，被此条挡住）；
     · other：单连通域、高 ∈ [0.85,1.30]×步进、宽 ≤ 0.85×步进、fill ≥ 0.06；
  ③ 位置：候选中心落在该列框的**第一格或最后一格**内（容差 0.3 步进），且是 y 序的第一个/最后一个聚簇；
  ④ OCR 文本对账（形态 + 文本边字）：
     · dash 的边字必须是汉字（`！` 等标点自身的竖条不是漏识；p1683 的边字 = `孟`）；
     · ring 的边字不得是引号/汉字/ASCII；只收 `。！？` 与数字（句尾序号）；末格排除 `，、；：`；
     · 文本边字已经是圈码（⑦/②…）的，说明 OCR 已识别，不报；
     · 方框汉字（回/日/時）靠「四边最小值」与「洞数」挡掉（见 ②）。

字步进：**不用「框高 ÷ 字数」**（p1683 的框含 2 个漏识元素，该式给 30.2 而非 19.3）。
每页取「n ≥ 8 的竖排列的 框高/字数」中位（= 邻列步进中位），无足够样本时回退全书
（n ≥ 8 列）的同一中位。p1683 页 = 19.3pt / 全书 = 25.4pt。

用法:
  /usr/bin/python3 src/tools/census_missed_cells.py --pages 1683-1741 --out /tmp/taskE/cal.json
  /usr/bin/python3 src/tools/census_missed_cells.py --pages 1-1748 --out /tmp/taskE/full.json
  # 可选 --crops DIR: 给每处候选取 48×48pt 源图裁片（审计用）
"""
import argparse
import json
import os
import statistics
import sys
from collections import Counter

import fitz
import numpy as np
from scipy import ndimage

DEFAULT_SRC = '/opt/test/source_pdf/wz7.pdf'
DEFAULT_CO = '/opt/test/data/wz7_full/wz7_full_spotting_coords.json'
DEFAULT_SL = '/opt/test/data/wz7_full/wz7_full_spotting_lines_patched.json'
Z = 2.0                      # 渲染 2px/pt（= OCR 坐标 2x px 同一坐标系）
MIN_AREA = 25                # 连通域最小面积(px²): 排噪点
QUOTE = set('「」『』﹁﹂﹄﹃〈〉《》【】')
# dash 的边字必须是汉字; ring 的边字只收句末标点/数字
RING_EDGE_OK = set('。！？')
RING_EDGE_BAD_LAST = set('，、；：')


def otsu(gray):
    """逐页 Otsu 阈值（与 build_vert._nf_ink_gray 同算法）。"""
    hist = np.bincount(np.asarray(gray).ravel(), minlength=256).astype(float)
    tot = hist.sum()
    sm = float((np.arange(256) * hist).sum())
    best, bk, w0, s0 = -1.0, 128, 0.0, 0.0
    for t in range(256):
        w0 += hist[t]
        s0 += t * hist[t]
        w1 = tot - w0
        if w0 <= 0 or w1 <= 0:
            continue
        v = w0 * w1 * (s0 / w0 - (sm - s0) / w1) ** 2
        if v > best:
            best, bk = v, t
    return bk


def box_pt(p):
    """OCR 四点多边形(2x px) -> (x0,y0,x1,y1) pt。"""
    xs = [q[0] for q in p]
    ys = [q[1] for q in p]
    return min(xs) / 2.0, min(ys) / 2.0, max(xs) / 2.0, max(ys) / 2.0


def is_cjk(ch):
    return '一' <= ch <= '鿿'


def center_ink(mask, frac=0.35):
    """组件 bbox 中心区域(半径 frac×min(H,W)/2)的墨占比(0-1)。"""
    ys, xs = np.where(mask)
    if not len(ys):
        return 0.0
    c = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    H, W = c.shape
    if H < 4 or W < 4:
        return 0.0
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt((yy - H / 2.0) ** 2 + (xx - W / 2.0) ** 2)
    mk = r < min(H, W) / 2.0 * frac
    return float(c[mk].mean()) if mk.any() else 0.0


def hole_ratio(mask):
    """最大分量的洞面积 / bbox 面积（环 > 0）。"""
    ys, xs = np.where(mask)
    if not len(ys):
        return 0.0
    c = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return float((ndimage.binary_fill_holes(c) & ~c).mean())


def ring_stats(mask):
    """环候选外圈统计 -> (radius_cv, holes, side_min)。
    radius_cv = 墨点到 bbox 中心距离的标准差 / rmax；方框/汉字通常更大。
    side_min = bbox 四条 15% 边带的最小填充（圆环 ~0.34-0.38，方框汉字 ~0.5+）。"""
    ys, xs = np.where(mask)
    if not len(ys):
        return 9.9, 0, 0.0
    c = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    H, W = c.shape
    if H < 4 or W < 4:
        return 9.9, 0, 0.0
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt((yy - H / 2.0) ** 2 + (xx - W / 2.0) ** 2)
    rmax = min(H, W) / 2.0
    rr = r[c]
    cv = float(rr.std() / max(1e-6, rmax))
    holes = int(ndimage.label(ndimage.binary_fill_holes(c) & ~c)[1])
    e = max(1, int(round(0.15 * min(H, W))))
    sides = [c[:e, :].mean(), c[-e:, :].mean(), c[:, :e].mean(), c[:, -e:].mean()]
    return cv, holes, float(min(sides))


def clusters_of(comps):
    """连通域按 y 区间重叠(≥50% 较小者)聚成「元素」。汉字部件因此不再单独成候选。"""
    comps = sorted(comps, key=lambda c: c['y0'])
    groups = []
    for c in comps:
        placed = False
        for g in groups:
            ov = min(g['y1'], c['y1']) - max(g['y0'], c['y0'])
            if ov > 0.5 * min(g['y1'] - g['y0'], c['y1'] - c['y0']):
                g['comps'].append(c)
                g['y0'] = min(g['y0'], c['y0']); g['y1'] = max(g['y1'], c['y1'])
                g['x0'] = min(g['x0'], c['x0']); g['x1'] = max(g['x1'], c['x1'])
                placed = True
                break
        if not placed:
            groups.append({'comps': [c], 'x0': c['x0'], 'x1': c['x1'],
                           'y0': c['y0'], 'y1': c['y1']})
    # 合并后产生的新重叠再迭代合并
    changed = True
    while changed:
        changed = False
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                a, b = groups[i], groups[j]
                ov = min(a['y1'], b['y1']) - max(a['y0'], b['y0'])
                if ov > 0.5 * min(a['y1'] - a['y0'], b['y1'] - b['y0']):
                    a['comps'] += b['comps']
                    a['y0'] = min(a['y0'], b['y0']); a['y1'] = max(a['y1'], b['y1'])
                    a['x0'] = min(a['x0'], b['x0']); a['x1'] = max(a['x1'], b['x1'])
                    groups.pop(j); changed = True; break
            if changed:
                break
    for g in groups:
        g['w'] = g['x1'] - g['x0']; g['h'] = g['y1'] - g['y0']
        g['area'] = sum(c['area'] for c in g['comps'])
        g['fill'] = g['area'] / max(1.0, g['w'] * g['h'] * Z * Z)
    return groups


def global_step(co, sl):
    """全书字步进基准 = n≥8 竖排列的「框高/字数」中位（不渲染）。"""
    rs = []
    for k in co:
        for t, p in zip(sl.get(k, []), co.get(k, [])):
            if not p:
                continue
            x0, y0, x1, y1 = box_pt(p)
            n = len(str(t).replace('\n', ''))
            if n >= 8 and y1 > y0 and (y1 - y0) >= 1.6 * (x1 - x0):
                rs.append((y1 - y0) / n)
    return statistics.median(rs) if rs else 25.0


def page_step(cols, gstep):
    """本页字步进 = n≥8 列的「框高/字数」中位（邻列步进中位）；样本不足回退全书值。"""
    rs = []
    for x0, y0, x1, y1, t in cols:
        n = len(t)
        H = y1 - y0
        if n >= 8 and H > 0:
            r = H / n
            if 0.5 * gstep <= r <= 1.6 * gstep:
                rs.append(r)
    return statistics.median(rs) if len(rs) >= 3 else gstep


def detect_page(pi, co, sl, gstep, src_doc, crops_dir=None, dbg=False):
    """一页 -> 候选列表。"""
    key = str(pi)
    if key not in co:
        return []
    cols = []
    for t, p in zip(sl.get(key, []), co.get(key, [])):
        if not p:
            continue
        t = str(t).replace('\n', '')
        x0, y0, x1, y1 = box_pt(p)
        if y1 - y0 < 20 or x1 - x0 < 6:
            continue
        if (y1 - y0) < 1.6 * (x1 - x0):          # 非竖排列（横排/表格行/西文侧排）
            continue
        if sum(1 for ch in t if is_cjk(ch)) < 0.5 * max(1, len(t)):
            continue                              # 西文/拉丁行不是本任务对象（p29）
        cols.append((x0, y0, x1, y1, t))
    if not cols:
        return []
    step = page_step(cols, gstep)
    p = src_doc[pi]
    pix = p.get_pixmap(matrix=fitz.Matrix(Z, Z), colorspace=fitz.csGRAY)
    gray = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width).copy()
    thr = otsu(gray)
    ink = gray < thr
    H, W = ink.shape
    out = []
    for x0, y0, x1, y1, t in cols:
        n = len(t)
        if n < 1:
            continue
        px0, py0 = int(round(x0 * Z)), int(round(y0 * Z))
        px1, py1 = int(round(x1 * Z)), int(round(y1 * Z))
        pad = int(round(0.30 * step * Z))
        cx0, cy0 = max(0, px0 - pad), max(0, py0 - pad)
        cx1, cy1 = min(W, px1 + pad), min(H, py1 + pad)
        if cx1 <= cx0 or cy1 <= cy0:
            continue
        lab, nc = ndimage.label(ink[cy0:cy1, cx0:cx1], structure=np.ones((3, 3)))
        comps = []
        for i in range(1, nc + 1):
            m = lab == i
            area = int(m.sum())
            if area < MIN_AREA:
                continue
            ys, xs = np.where(m)
            bx0, bx1 = cx0 + xs.min(), cx0 + xs.max() + 1
            by0, by1 = cy0 + ys.min(), cy0 + ys.max() + 1
            ccx = (bx0 + bx1) / 2.0 / Z
            if not (x0 - 4 <= ccx <= x1 + 4):
                continue
            comps.append({'m': m, 'area': area, 'x0': bx0 / Z, 'x1': bx1 / Z,
                          'y0': by0 / Z, 'y1': by1 / Z,
                          'w': (bx1 - bx0) / Z, 'h': (by1 - by0) / Z})
        if len(comps) < 2:
            continue
        groups = clusters_of(comps)
        if len(groups) < 2:
            continue
        gs = sorted(groups, key=lambda g: g['y0'])
        for g, pos in ((gs[0], 'first'), (gs[-1], 'last')):
            ccy = (g['y0'] + g['y1']) / 2.0
            tol = 0.30 * step
            if pos == 'first' and not (y0 - tol <= ccy <= y0 + step + tol):
                continue
            if pos == 'last' and not (y1 - step - tol <= ccy <= y1 + tol):
                continue
            w, h = g['w'], g['h']
            if w <= 0 or h <= 0:
                continue
            hr = h / step
            big = max(g['comps'], key=lambda c: c['area'])
            cm = None
            for c in g['comps']:
                cm = c['m'].copy() if cm is None else (cm | c['m'])
            ctr_all = center_ink(cm)
            hole = hole_ratio(big['m'])
            ctr_big = center_ink(big['m'], frac=0.22)
            rcv, nh, smin_big = ring_stats(big['m'])
            edge = t[-1] if pos == 'last' else t[0]
            cls = None
            if (w <= 7 and h >= 12 and h / max(w, 0.1) >= 2.5 and 0.8 <= hr <= 1.8
                    and g['fill'] >= 0.45 and is_cjk(edge)):
                cls = 'dash'
            elif (0.6 <= w / max(h, 0.1) <= 1.7 and 6 <= h <= 40 and 0.80 <= hr <= 1.10
                  and ctr_big < 0.35 and hole >= 0.10 and ctr_all >= 0.03
                  and nh <= 3 and smin_big < 0.50
                  and edge not in QUOTE and not is_cjk(edge)
                  and (edge in RING_EDGE_OK or edge.isdigit())
                  and not (pos == 'last' and edge in RING_EDGE_BAD_LAST)):
                # OCR 已识别成圈码(⑦/②...)的：该元素就是文本边字, 不算漏识
                if ('①' <= edge <= '⓿' or '㉑' <= edge <= '㉟'
                        or '㊱' <= edge <= '㊿'):
                    continue
                cls = 'ring'
            # other 类（非 dash/非 ring 的占格符号）经双向标定**无可信判据**：
            #   松判据找到的 6 处（p393「了」等）全是汉字整字/部件；要可靠区分需要 OCR 逐字框。
            #   本任务只报 dash/ring 两类；JSON 仍保留 class 字段（other 计数 = 0）。
            # 如需复查: 把下面三行取消注释即可（会引入汉字部件假阳，见报告 §7）。
            # elif (len(g['comps']) == 1 and 0.85 <= hr <= 1.30
            #       and 0.45 <= w / step <= 0.55 and g['fill'] >= 0.10 and is_cjk(edge)):
            #     cls = 'other'
            if cls is None:
                continue
            rec = {'page': pi + 1, 'x': round((g['x0'] + g['x1']) / 2, 1),
                   'y': round(g['y0'], 1), 'w': round(w, 1), 'h': round(h, 1),
                   'class': cls, 'text': t, 'cell': pos,
                   'col': [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                   'step': round(step, 2), 'hr': round(hr, 2),
                   'fill': round(g['fill'], 2), 'ncomp': len(g['comps']),
                   'ctr': round(ctr_all, 2), 'hole': round(hole, 2),
                   'rcv': round(rcv, 3), 'nh': nh}
            out.append(rec)
            if dbg:
                print('  [%s] p%d x%.1f y%.1f w%.1f h%.1f %s edge=%r text=%r'
                      % (cls, pi + 1, rec['x'], rec['y'], w, h, pos, edge, t[:12]))
            if crops_dir:
                cx, cy = rec['x'], rec['y'] + h / 2.0
                pix = p.get_pixmap(matrix=fitz.Matrix(6, 6),
                                   clip=fitz.Rect(cx - 24, cy - 24, cx + 24, cy + 24),
                                   colorspace=fitz.csGRAY)
                pix.save(os.path.join(crops_dir, 'p%d_%s_x%.0f_y%.0f.png'
                                      % (pi + 1, cls, rec['x'], rec['y'])))
    return out


def parse_pages(s):
    if '-' in s:
        a, b = s.split('-', 1)
        return int(a), int(b)
    return int(s), int(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=DEFAULT_SRC)
    ap.add_argument('--coords', default=DEFAULT_CO)
    ap.add_argument('--lines', default=DEFAULT_SL)
    ap.add_argument('--pages', default='1-1748')
    ap.add_argument('--out', default='')
    ap.add_argument('--crops', default='')
    ap.add_argument('--dbg', action='store_true')
    a = ap.parse_args()
    co = json.load(open(a.coords, encoding='utf8'))
    sl = json.load(open(a.lines, encoding='utf8'))
    gstep = global_step(co, sl)
    print('[字步进] 全书基准 %.3fpt (n>=8 竖排列 框高/字数 中位)' % gstep)
    lo, hi = parse_pages(a.pages)
    src = fitz.open(a.src)
    if a.crops:
        os.makedirs(a.crops, exist_ok=True)
    res = []
    t0 = __import__('time').time()
    for pi in range(lo - 1, min(hi, src.page_count)):
        res += detect_page(pi, co, sl, gstep, src, crops_dir=a.crops or None, dbg=a.dbg)
        if (pi + 1 - lo) % 100 == 99:
            print('  ... p%d, 候选 %d, %.0fs' % (pi + 1, len(res), __import__('time').time() - t0))
    src.close()
    cnt = Counter(r['class'] for r in res)
    print('[普查] 页 %d-%d 候选 %d: dash %d / ring %d / other %d'
          % (lo, hi, len(res), cnt.get('dash', 0), cnt.get('ring', 0), cnt.get('other', 0)))
    for c in ('dash', 'ring', 'other'):
        xs = [r for r in res if r['class'] == c]
        print('    %-5s %3d 处 / %d 页' % (c, len(xs), len(set(r['page'] for r in xs))))
    if a.out:
        json.dump(res, open(a.out, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
        print('[普查] 落盘 %s' % a.out)


if __name__ == '__main__':
    main()
