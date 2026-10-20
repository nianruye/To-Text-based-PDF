#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""竖排产物版式审计（taskCI）：列位置错位 / 字压字（列间横向重叠）

设计原则（详见 docs/vert_taskCI_report.md 第二节）：
  不做「产物列 ↔ 源 OCR 行」的内容配对 —— 配对会引入容差、聚类、顺序三个不确定源。
  全部判据都是**单侧绝对判据**：
    A1 列位偏差：每个产物列段的 x 中心 vs 该段 y 跨度内**源图墨迹列带**的最近中心。
       源图墨迹带用覆盖率阈值（>3%）而不是 any()，避免扫描噪点把相邻列连成一带。
       页内取中位偏差做基线，残差 > tol 才算「本页内错位」；整页整体偏移单独报 page_shift。
    A2 强错位（无容差）：产物列段的 x 区间内必须包含至少一个源图墨迹列带的中心。
       对应「列已经偏出半个字宽」，最近带可能已经是邻列 —— A1 会因配到错带而漏报，
       A2 不依赖最近邻，直接判「这段字下面没有源图墨迹列」。
    B 字压字：两个产物列段的 x 盒（em 宽）重叠 > overlap_tol，且 y 跨度重叠 > 30%。
       若两段相对源图墨迹带的偏差都 <= tol（源书自身就这样排），记为 source_faithful，不报。
    C 列内字叠字：段内相邻字 origin y 间距 < 0.8 x 字号（字号被撑大时的兜底判据）。

数据口径（与简报第⑦段一致，写死）：
  · lines/coords（spotting）0-based 索引：页 p 用 str(p-1)
  · OCR coords 单位 px = pt x 2
  · 产物坐标 pt（fitz origin）
  · 本工具不统计字符量（字符量口径见 verify_vert.py）

用法：
  /usr/bin/python3 src/tools/vert_layout_audit.py --pages 48 --verbose
  /usr/bin/python3 src/tools/vert_layout_audit.py            # 全书 -> data/wz7_full/wz7_full_layout_audit.json

退出码恒为 0（审计工具，不是门禁；门禁仍是 verify_vert.py）。
"""
import argparse
import json
import os
import statistics
import sys
import time

import fitz
import numpy as np

# 挤格标点：不占整格，落位口径与正文不同（见 build_vert.py §1.0），不参与列几何
PUNCT = set('。，、；：？！︒︑')
# 页码数字（汉字数字 + 阿拉伯数字）：短数码列不参与列位判据（源书页码位置本就有 ±10pt 级漂移）
NUMCH = set('〇一二三四五六七八九十百千零壹贰叁肆伍陆柒捌玖拾佰仟0123456789')
# 中文数字（目录「第X回」识别用）
CN = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}

DEFAULT_PDF = '/opt/test/output/wz7_full/wz7_full_v6.pdf'
DEFAULT_SRC = '/opt/test/source_pdf/wz7.pdf'
DEFAULT_LINES = '/opt/test/data/wz7_full/wz7_full_spotting_lines_patched.json'
DEFAULT_COORDS = '/opt/test/data/wz7_full/wz7_full_spotting_coords.json'
DEFAULT_OUT = '/opt/test/data/wz7_full/wz7_full_layout_audit.json'


def is_cjk(c):
    """CJK 汉字/假名（列几何的核心字符）。标点、引號、括号、拉丁字母全部排除。"""
    o = ord(c)
    if 0x3040 <= o <= 0x30FF:            # 平假名/片假名（含 ・ ー，后文按标点剔除）
        return o != 0x30FB
    return (0x3400 <= o <= 0x4DBF) or (0x4E00 <= o <= 0x9FFF) \
        or (0xF900 <= o <= 0xFAFF)


def is_numeric_text(t):
    return bool(t) and all(c in NUMCH for c in t)


def otsu_threshold(a):
    """灰度图 Otsu 阈值（与 build_vert.py `_nf_ink_gray` 同口径：wz7 灰底纸必须自适应）。"""
    h = np.bincount(a.ravel(), minlength=256).astype(float)
    tot = h.sum()
    sm = float((np.arange(256) * h).sum())
    best, bk, w0, s0 = -1.0, 128, 0.0, 0.0
    for t in range(256):
        w0 += h[t]
        s0 += t * h[t]
        w1 = tot - w0
        if w0 <= 0 or w1 <= 0:
            continue
        v = w0 * w1 * (s0 / w0 - (sm - s0) / w1) ** 2
        if v > best:
            best, bk = v, t
    return bk


def runs_of(mask, min_len=1):
    """布尔序列 -> [(start, end)]（含端点）。"""
    out, s = [], None
    for i, v in enumerate(mask):
        if v and s is None:
            s = i
        elif not v and s is not None:
            if i - s >= min_len:
                out.append((s, i - 1))
            s = None
    if s is not None and len(mask) - s >= min_len:
        out.append((s, len(mask) - 1))
    return out


def source_ink(src_doc, pi):
    """源页 2x 灰度墨迹布尔图（Otsu + 去印刷直线），坐标系 px（= pt x 2）。
    去线口径与 build_vert.py `_nf_delines` 一致：竖线墨占比 >0.75 且跨度 >=0.5 页高；
    横线墨占比 >0.45 且跨度 >=0.55 页宽。避免版框/表格线在 x 投影里连成满宽墨带。"""
    pg = src_doc[pi]
    pix = pg.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY, alpha=False)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()
    ink = a < otsu_threshold(a)
    H, W = ink.shape
    if H >= 8 and W >= 8:
        colc = ink.mean(axis=0)
        for x0, x1 in runs_of(colc > 0.75, 3):
            ys = np.where(ink[:, x0:x1 + 1].any(axis=1))[0]
            if len(ys) and ys[-1] - ys[0] + 1 >= 0.5 * H:
                ink[:, max(0, x0 - 1):x1 + 2] = False
        rowc = ink.mean(axis=1)
        for y0, y1 in runs_of(rowc > 0.45, 2):
            xs = np.where(ink[y0:y1 + 1, :].any(axis=0))[0]
            if len(xs) and xs[-1] - xs[0] + 1 >= 0.55 * W:
                ink[max(0, y0 - 1):y1 + 2, :] = False
    return ink


def product_columns(pg):
    """产物页 -> 竖排列段列表。
    只取 CJK 字体里的汉字/假名（西文旋转行、标点、引號全部排除）。
    ① 按 origin x 聚类（tol 3pt；同一列内不同字号的 origin x 差 <= ~2pt）；
    ② 列内按 origin y 排序，y 间隔 > 1.7 x 字号中位处切成「列段」（目录页的回次/回目上下句、
       正文页的诗歌分栏都会自然分开；空一格处也切开，便于逐段比对 y 跨度）。"""
    ch = []
    for b in pg.get_text('rawdict')['blocks']:
        for ln in b.get('lines', []):
            for sp in ln.get('spans', []):
                font = sp.get('font') or ''
                if 'CJK' not in font:
                    continue
                for c in sp.get('chars', []):
                    t = c.get('c') or ''
                    if not t or t.isspace() or not is_cjk(t):
                        continue
                    ch.append((c['origin'][0], c['origin'][1], sp['size'], t))
    if not ch:
        return []
    xs = sorted(set(round(z[0], 2) for z in ch))
    groups = []
    for x in xs:
        if groups and x - groups[-1][-1] <= 3.0:
            groups[-1].append(x)
        else:
            groups.append([x])
    cols = []
    for gg in groups:
        lo, hi = gg[0] - 0.01, gg[-1] + 0.01
        mem = sorted([z for z in ch if lo <= z[0] <= hi], key=lambda z: z[1])
        if not mem:
            continue
        fs = statistics.median(z[2] for z in mem)
        cur = [mem[0]]
        for z in mem[1:]:
            if z[1] - cur[-1][1] > 1.7 * fs:
                cols.append(cur)
                cur = [z]
            else:
                cur.append(z)
        cols.append(cur)
    segs = []
    for ss in cols:
        n = len(ss)
        x0 = min(z[0] for z in ss)
        x1 = max(z[0] + z[2] for z in ss)
        f = statistics.median(z[2] for z in ss)
        steps = [ss[i + 1][1] - ss[i][1] for i in range(n - 1)]
        text = ''.join(z[3] for z in ss)
        seg = {
            'x0': round(x0, 2), 'x1': round(x1, 2), 'xc': round((x0 + x1) / 2.0, 2),
            'yt': round(min(z[1] - z[2] for z in ss), 2),
            'yb': round(max(z[1] for z in ss), 2),
            'n': n, 'text': text, 'font': round(f, 2),
            'numeric': is_numeric_text(text),
            'step_min': round(min(steps), 2) if steps else None,
            'size_max': round(max(z[2] for z in ss), 2),
            # 同一 x 簇（= 同一产物列）的段共享 col 键；列位判据按**整列**取 y 并集后比一次，
            # 避免源书列本身沿 y 有轻微倾斜时把同一列的各段判成不同偏差（实测 p622 段间 dev 漂 15pt）
            'col': round(x0, 1),
        }
        intras = []
        for i, d in enumerate(steps):
            lim = 0.8 * max(ss[i][2], ss[i + 1][2])
            if d < lim:
                intras.append({'i': i, 'a': ss[i][3], 'b': ss[i + 1][3],
                               'step': round(d, 2), 'size': round(lim / 0.8, 2)})
        seg['intra'] = intras
        segs.append(seg)
    return segs


def source_bands(cum, H, W, y0, y1, cov=0.03, min_px=4, merge_px=6):
    """源图墨迹在 y 跨度 [y0,y1] 内的 x 列带 -> [(x0_pt, x1_pt, center_pt)]。
    用 y 向累加和做 O(W) 投影；覆盖率阈值 3%（扫描噪点覆盖率实测 0.002-0.007，被挡掉）；
    带内空 <=3pt 的缝合并（字间空隙），跨列的白缝 ~9-11pt 不会被合并。"""
    a = int(max(0, min(H - 1, round(y0 * 2))))
    b = int(max(a + 1, min(H, round(y1 * 2))))
    colsum = cum[b - 1].astype(np.int32)
    if a > 0:
        colsum = colsum - cum[a - 1]
    cov_arr = colsum / float(b - a)
    rr = runs_of(cov_arr > cov, min_px)
    mg = []
    for r in rr:
        if mg and r[0] - mg[-1][1] <= merge_px:
            mg[-1] = (mg[-1][0], r[1])
        else:
            mg.append(r)
    out = []
    for x0, x1 in mg:
        if x1 - x0 + 1 < min_px:
            continue
        out.append(((x0) / 2.0, (x1 + 1) / 2.0, ((x0 + x1 + 1) / 2.0) / 2.0))
    return out


def load_ocr(lines_path, coords_path):
    with open(lines_path, encoding='utf-8') as f:
        lines = json.load(f)
    with open(coords_path, encoding='utf-8') as f:
        coords = json.load(f)
    return lines, coords


def norm_text(t):
    """标注用归一化：只保留汉字/假名/数字，去掉标点、引號、空白、换行。"""
    return ''.join(c for c in str(t) if is_cjk(c) or c in NUMCH)


def ocr_rows_for_page(lines, coords, p):
    """页 p（1-based）-> [(x0,x1,y0,y1,text)] pt。lines/coords 是 0-based，故取 str(p-1)。"""
    key = str(p - 1)
    out = []
    for t, poly in zip(lines.get(key) or [], coords.get(key) or []):
        if not poly or len(poly) < 3:
            continue
        xs = [q[0] / 2.0 for q in poly]
        ys = [q[1] / 2.0 for q in poly]
        out.append((min(xs), max(xs), min(ys), max(ys), str(t)))
    return out


def annotate_entry(seg, rows):
    """给命中列段补「源书上下文」（仅标注用，不参与任何判据）。
    ① 归一化文本精确相等 -> 找到源 OCR 行；
    ② 找不到则退化为子串包含（仅当共同汉字 >= 4），用于 p465 这类「一条 OCR 行被拆成多段」；
    ③ 同一源列（行心 x 差 <= 3pt）的所有行文本作为 column_rows；
       其中匹配「第X回」的行作为 entry（p48 的玳安行 -> 第五十回）。"""
    nt = norm_text(seg['text'])
    if not nt:
        return None
    hit = None
    for r in rows:
        if norm_text(r[4]) == nt:
            hit = r
            break
    if hit is None:
        best = 0
        for r in rows:
            nr = norm_text(r[4])
            if len(nt) >= 4 and (nt in nr or nr in nt):
                common = len(set(nt) & set(nr))
                if common > best:
                    best, hit = common, r
    if hit is None:
        return None
    xc = (hit[0] + hit[1]) / 2.0
    col_rows = sorted([r for r in rows if abs((r[0] + r[1]) / 2.0 - xc) <= 3.0],
                      key=lambda r: r[2])
    col_texts = [r[4].replace('\n', '') for r in col_rows]
    entry = None
    import re
    re_cn = re.compile(r'第([一二三四五六七八九十百]+)回')
    for t in col_texts:
        m = re_cn.search(t)
        if m:
            entry = m.group(0)
            break
    return {
        'source_row': hit[4].replace('\n', '')[:40],
        'source_row_x': [round(hit[0], 1), round(hit[1], 1)],
        'column_rows': [t[:28] for t in col_texts],
        'entry': entry,
    }


def page_layout_kind(rows):
    """源 OCR 行形态 -> 'vertical' / 'horizontal' / 'unknown'。
    横排页（现代附録字表/版权页/序言横排）的「列」在 y 方向，本工具全部判据（竖排列几何）
    不适用；整页跳过并在汇总里单列，避免把横向行距当成字压字（实测 p1163）。"""
    ars, wide = [], 0
    for r in rows:
        w, h = r[1] - r[0], r[3] - r[2]
        if w <= 0 or h <= 0 or len(r[4]) < 2:
            continue
        ar = w / h
        ars.append(ar)
        if ar > 1.6:
            wide += 1
    if not ars:
        return 'unknown'
    if statistics.median(ars) > 1.5 or wide > 0.5 * len(ars):
        return 'horizontal'
    return 'vertical'


def audit_page(pg, src_doc, pi, rows, tol, overlap_tol, verbose=False):
    """单页审计 -> (segments, columns, page_median, hits, counters)。"""
    kind = page_layout_kind(rows)
    if kind == 'horizontal':
        return [], [], None, [], {'segments': 0, 'columns': 0, 'bands_pages': 0,
                                  'horizontal': 1}
    segs = product_columns(pg)
    if not segs:
        return segs, [], None, [], {'segments': 0, 'columns': 0, 'bands_pages': 0}
    ink = source_ink(src_doc, pi)
    H, W = ink.shape
    cum = np.cumsum(ink, axis=0, dtype=np.int32)
    # 先按产物列（同一 x 簇）聚合：列位偏差以整列为单位比一次（源书列沿 y 的轻微倾斜
    # 不再被逐段放大成假命中）；重合/列内叠字仍按段判。
    # 源带取**本页全部列段的 y 并集**内的 x 投影：逐列按自身 y 取带时，列尾超出源书该列
    # y 范围（实测 p269 页边章节条的尾段比源墨迹低 250pt）会把邻列当成最近带 -> dev -624 假命中。
    y_all0 = min(s['yt'] for s in segs) - 2.0
    y_all1 = max(s['yb'] for s in segs) + 2.0
    bands_full = source_bands(cum, H, W, y_all0, y_all1)
    groups = {}
    for s in segs:
        groups.setdefault(s['col'], []).append(s)
    cols = []
    for key, ss in groups.items():
        x0 = min(z['x0'] for z in ss)
        x1 = max(z['x1'] for z in ss)
        yt = min(z['yt'] for z in ss)
        yb = max(z['yb'] for z in ss)
        xc = statistics.median(z['xc'] for z in ss)
        bands = bands_full
        g = {'col': key, 'x0': round(x0, 2), 'x1': round(x1, 2), 'xc': round(xc, 2),
             'yt': round(yt, 2), 'yb': round(yb, 2), 'segs': ss,
             'bands_n': len(bands), 'band': None, 'band_alt': None,
             'dev': None, 'band_inside': False}
        if bands:
            # 优先取「中心落在本列 x 区间内」的带；没有才取最近带（此时 A2 强错位必报）。
            inside = [z for z in bands if x0 - 0.5 <= z[2] <= x1 + 0.5]
            g['band_inside'] = bool(inside)
            pool = inside if inside else bands
            b = min(pool, key=lambda z: abs(z[2] - xc))
            others = [z for z in bands if z is not b]
            if others:
                alt = min(others, key=lambda z: abs(z[2] - xc))
                g['band_alt'] = [round(alt[0], 1), round(alt[1], 1), round(alt[2], 1)]
            g['band'] = [round(b[0], 1), round(b[1], 1), round(b[2], 1)]
            g['dev'] = round(xc - b[2], 2)
        cols.append(g)
    # 段 -> 列 dev 的映射（重合判据的「源书自身重合」豁免要用）
    col_of = {}
    for g in cols:
        for s in g['segs']:
            s['col_dev'] = g['dev']
            col_of[id(s)] = g
    eligible = [g for g in cols
                if any(s['n'] >= 4 and not s['numeric'] for s in g['segs'])]
    for g in cols:
        g['eligible'] = any(s['n'] >= 4 and not s['numeric'] for s in g['segs'])
    devs = [g['dev'] for g in eligible if g['dev'] is not None]
    med = statistics.median(devs) if devs else None
    hits = []
    for g in eligible:
        # 该列里最长的合格段作为代表文本（用于标注/报告）
        rep = max((s for s in g['segs'] if s['n'] >= 4 and not s['numeric']),
                  key=lambda z: z['n'])
        if g['dev'] is not None:
            resid = g['dev'] - med if (med is not None and len(devs) >= 3) else g['dev']
            g['resid'] = round(resid, 2)
            pos = abs(resid) > tol
        else:
            resid = None
            g['resid'] = None
            pos = False
        strong = not g['band_inside']          # A2: 列 x 区间内无源带中心（无容差）
        if pos or strong:
            h = {'type': 'position', 'page': pi + 1,
                 'x0': g['x0'], 'x1': g['x1'], 'xc': g['xc'],
                 'yt': g['yt'], 'yb': g['yb'], 'n': rep['n'],
                 'font': rep['font'], 'text': rep['text'][:40],
                 'texts': [s['text'][:28] for s in sorted(g['segs'], key=lambda z: z['yt'])],
                 'position': pos, 'strong': strong,
                 'dev': g['dev'], 'page_median': round(med, 2) if med is not None else None,
                 'resid': (round(resid, 2) if resid is not None else None),
                 'source_band': g['band'], 'source_band_alt': g['band_alt'],
                 'bands_n': g['bands_n']}
            ann = annotate_entry(rep, rows)
            if ann:
                h.update(ann)
            if not h.get('entry'):
                # 同一列的各段都试一次，取第一个能定位到「第X回」的
                for s in g['segs']:
                    if s is rep:
                        continue
                    ann = annotate_entry(s, rows)
                    if ann and ann.get('entry'):
                        h.update(ann)
                        break
            hits.append(h)
    # B 列间字压字
    cand = [s for s in segs if s['n'] >= 2 and not s['numeric']]
    for i in range(len(cand)):
        a = cand[i]
        for j in range(i + 1, len(cand)):
            b = cand[j]
            ovx = min(a['x1'], b['x1']) - max(a['x0'], b['x0'])
            ovy = min(a['yb'], b['yb']) - max(a['yt'], b['yt'])
            hmin = min(a['yb'] - a['yt'], b['yb'] - b['yt'])
            if ovx <= overlap_tol or ovy <= 0.3 * hmin:
                continue
            # 源书自身就这么排（两列都贴着各自源列带）-> 不算产物错位
            ad, bd = a.get('col_dev'), b.get('col_dev')
            faithful = (ad is not None and bd is not None
                        and abs(ad) <= tol and abs(bd) <= tol)
            h = {'type': 'overlap', 'page': pi + 1,
                 'x_overlap': round(ovx, 2), 'y_overlap': round(ovy, 2),
                 'source_faithful': faithful,
                 'a': {'x0': a['x0'], 'x1': a['x1'], 'yt': a['yt'], 'yb': a['yb'],
                       'text': a['text'][:40], 'dev': ad},
                 'b': {'x0': b['x0'], 'x1': b['x1'], 'yt': b['yt'], 'yb': b['yb'],
                       'text': b['text'][:40], 'dev': bd}}
            if not faithful:
                ann = annotate_entry(a, rows)
                if ann:
                    h['a'].update(ann)
                ann = annotate_entry(b, rows)
                if ann:
                    h['b'].update(ann)
                hits.append(h)
            else:
                hits.append(h)
    # C 列内字叠字
    for s in segs:
        for it in s['intra']:
            hits.append({'type': 'intra', 'page': pi + 1,
                         'x0': s['x0'], 'x1': s['x1'],
                         'yt': s['yt'], 'yb': s['yb'], 'text': s['text'][:40],
                         'a': it['a'], 'b': it['b'],
                         'step': it['step'], 'size': it['size']})
    cnt = {'segments': len(segs), 'columns': len(cols),
           'eligible': len(eligible), 'bands_pages': 1}
    return segs, cols, med, hits, cnt


def main():
    ap = argparse.ArgumentParser(description='竖排产物版式审计（列位置错位 / 字压字）')
    ap.add_argument('--pdf', default=DEFAULT_PDF)
    ap.add_argument('--src', default=DEFAULT_SRC)
    ap.add_argument('--lines', default=DEFAULT_LINES)
    ap.add_argument('--coords', default=DEFAULT_COORDS)
    ap.add_argument('--out', default=DEFAULT_OUT)
    ap.add_argument('--pages', default='', help='逗号分隔的 1-based 页号；缺省 = 全书')
    ap.add_argument('--tol', type=float, default=6.0, help='列位残差阈值(pt)，默认 6')
    ap.add_argument('--overlap-tol', type=float, default=2.0, help='列间 x 重叠阈值(pt)，默认 2')
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--no-json', action='store_true')
    a = ap.parse_args()

    doc = fitz.open(a.pdf)
    src_doc = fitz.open(a.src)
    lines, coords = load_ocr(a.lines, a.coords)
    if a.pages:
        pages = [int(x) for x in a.pages.split(',') if x.strip()]
    else:
        pages = list(range(1, len(doc) + 1))
    t0 = time.time()
    page_records = []
    page_summaries = []
    all_hits = {'position': [], 'overlap': [], 'overlap_faithful': [], 'intra': []}
    page_shift = []
    dev_all = []
    n_seg = 0
    n_cols = 0
    n_audited = 0
    n_bands_pages = 0
    n_horizontal = 0
    horizontal_pages = []
    for k, p in enumerate(pages):
        if not (1 <= p <= len(doc)):
            print('[跳过] p%d 超出 PDF 页数 %d' % (p, len(doc)), file=sys.stderr)
            continue
        pi = p - 1
        rows = ocr_rows_for_page(lines, coords, p)
        segs, cols, med, hits, cnt = audit_page(doc[pi], src_doc, pi, rows,
                                                a.tol, a.overlap_tol, a.verbose)
        n_seg += len(segs)
        n_cols += cnt.get('columns', 0)
        if segs:
            n_audited += 1
        if cnt.get('bands_pages'):
            n_bands_pages += 1
        if cnt.get('horizontal'):
            n_horizontal += 1
            horizontal_pages.append(p)
        if med is not None:
            dev_all.extend(g['dev'] for g in cols if g.get('eligible') and g['dev'] is not None)
            if abs(med) > 4.0 and cnt.get('eligible', 0) >= 3:
                page_shift.append({'page': p, 'median_dev': round(med, 2),
                                   'n': cnt.get('eligible', 0)})
        if segs:
            page_summaries.append({
                'page': p, 'segments': len(segs), 'columns': len(cols),
                'median_dev': round(med, 2) if med is not None else None,
                'position': sum(1 for h in hits if h['type'] == 'position'),
                'strong': sum(1 for h in hits if h['type'] == 'position' and h['strong']),
                'overlap': sum(1 for h in hits
                               if h['type'] == 'overlap' and not h.get('source_faithful')),
                'intra': sum(1 for h in hits if h['type'] == 'intra'),
            })
        if hits:
            real = [h for h in hits if h['type'] != 'overlap' or not h.get('source_faithful')]
            for h in hits:
                if h['type'] == 'position':
                    all_hits['position'].append(h)
                elif h['type'] == 'overlap':
                    all_hits['overlap_faithful' if h.get('source_faithful') else 'overlap'].append(h)
                elif h['type'] == 'intra':
                    all_hits['intra'].append(h)
            if real:
                page_records.append({'page': p,
                                     'median_dev': round(med, 2) if med is not None else None,
                                     'segments': len(segs), 'hits': real})
            if a.verbose:
                print('p%d: 列段 %d，命中 %d（列位 %d / 强错位 %d / 重合 %d / 列内叠字 %d），页中位偏差 %s'
                      % (p, len(segs), len(real),
                         sum(1 for h in hits if h['type'] == 'position'),
                         sum(1 for h in hits if h['type'] == 'position' and h['strong']),
                         sum(1 for h in hits if h['type'] == 'overlap' and not h.get('source_faithful')),
                         sum(1 for h in hits if h['type'] == 'intra'),
                         ('%+.2f' % med) if med is not None else '-'))
                for h in real:
                    if h['type'] == 'position':
                        tag = '列位' + ('/强错位' if h['strong'] else '')
                        ctx = (' [%s]' % h['entry']) if h.get('entry') else ''
                        _bands = ('%.1f' % h['source_band'][2]) if h['source_band'] else '无'
                        if h.get('source_band_alt'):
                            _bands += ' (次近带 %.1f)' % h['source_band_alt'][2]
                        print('  [%s]%s x%.1f-%.1f y%.1f-%.1f n%d 字号%.1f %r 偏差%s 源带%s'
                              % (tag, ctx,
                                 h['x0'], h['x1'], h['yt'], h['yb'], h['n'], h['font'],
                                 h['text'],
                                 ('%+.1f' % h['dev']) if h['dev'] is not None else 'NA',
                                 _bands))
                        if h.get('column_rows'):
                            print('         源列: %s' % ' | '.join(h['column_rows']))
                    elif h['type'] == 'overlap':
                        print('  [重合] %r(x%.1f-%.1f y%.1f-%.1f) <-> %r(x%.1f-%.1f y%.1f-%.1f) '
                              'x重叠%.1fpt y重叠%.1fpt'
                              % (h['a']['text'], h['a']['x0'], h['a']['x1'], h['a']['yt'], h['a']['yb'],
                                 h['b']['text'], h['b']['x0'], h['b']['x1'], h['b']['yt'], h['b']['yb'],
                                 h['x_overlap'], h['y_overlap']))
                        for side in ('a', 'b'):
                            if h[side].get('entry'):
                                print('         %s 条目: %s' % (side, h[side]['entry']))
                    elif h['type'] == 'intra':
                        print('  [列内叠字] %r x%.1f y%.1f-%.1f 「%s」->「%s」步进%.1f < 字号%.1f'
                              % (h['text'], h['x0'], h['yt'], h['yb'], h['a'], h['b'],
                                 h['step'], h['size']))
        if (k + 1) % 100 == 0:
            print('[进度] %d/%d 页，%.1fs' % (k + 1, len(pages), time.time() - t0), file=sys.stderr)

    dev_abs = sorted(abs(d) for d in dev_all)
    dev_signed = sorted(dev_all)
    def pct(arr, q):
        if not arr:
            return None
        i = min(len(arr) - 1, max(0, int(round(q * (len(arr) - 1)))))
        return round(arr[i], 2)
    hist = {}
    for d in dev_all:
        b = int(d // 2) * 2
        hist['%d..%d' % (b, b + 2)] = hist.get('%d..%d' % (b, b + 2), 0) + 1
    pos_hits = all_hits['position']
    pos_cols = [h for h in pos_hits if h['position']]
    strong_cols = [h for h in pos_hits if h['strong']]
    out = {
        'meta': {
            'pdf': a.pdf, 'src': a.src,
            'pages_requested': len(pages), 'pages_audited': n_audited,
            'pages_horizontal_skipped': n_horizontal,
            'horizontal_pages': horizontal_pages,
            'pages_with_bands': n_bands_pages,
            'segments': n_seg, 'columns_total': n_cols,
            'tol_pt': a.tol, 'overlap_tol_pt': a.overlap_tol,
            'elapsed_s': round(time.time() - t0, 1),
        },
        'summary': {
            'position_hits': len(pos_cols),
            'strong_hits': len(strong_cols),
            'position_or_strong_columns': len(pos_hits),
            'pages_with_position': len(set(h['page'] for h in pos_hits)),
            'overlap_hits': len(all_hits['overlap']),
            'overlap_faithful': len(all_hits['overlap_faithful']),
            'pages_with_overlap': len(set(h['page'] for h in all_hits['overlap'])),
            'intra_hits': len(all_hits['intra']),
            'pages_with_hits': len(page_records),
            'pages_with_page_shift': len(page_shift),
            'dev_abs_p50': pct(dev_abs, 0.5),
            'dev_abs_p90': pct(dev_abs, 0.9),
            'dev_abs_p95': pct(dev_abs, 0.95),
            'dev_abs_p99': pct(dev_abs, 0.99),
            'dev_abs_max': round(dev_abs[-1], 2) if dev_abs else None,
            'dev_signed_p50': pct(dev_signed, 0.5),
            'dev_histogram': dict(sorted(hist.items())),
        },
        'page_shift': page_shift,
        'hits': all_hits,
        'pages': page_records,
        'page_summaries': page_summaries,
    }
    print()
    print('=== 版式审计汇总 ===')
    print('  审计页 %d / 请求 %d；列 %d / 段 %d；有源带页 %d；横排页跳过 %d'
          % (n_audited, len(pages), n_cols, n_seg, n_bands_pages, n_horizontal))
    print('  列位异常列: %d（其中强错位 %d）| 涉及页 %d'
          % (len(pos_hits), len(strong_cols), len(set(h['page'] for h in pos_hits))))
    print('  列间重合: %d 处（页 %d）| 源书自身重合 %d | 列内叠字: %d 处'
          % (len(all_hits['overlap']), len(set(h['page'] for h in all_hits['overlap'])),
             len(all_hits['overlap_faithful']), len(all_hits['intra'])))
    print('  页级整体偏移(|中位|>4pt): %d 页' % len(page_shift))
    print('  列位偏差分布: p50 %.2f / p90 %.2f / p95 %.2f / p99 %.2f / max %.2f pt'
          % (pct(dev_abs, 0.5) or 0, pct(dev_abs, 0.9) or 0, pct(dev_abs, 0.95) or 0,
             pct(dev_abs, 0.99) or 0, out['summary']['dev_abs_max'] or 0))
    if not a.no_json:
        os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print('  JSON -> %s' % a.out)
    print('  耗时 %.1fs' % (time.time() - t0))
    doc.close()
    src_doc.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
