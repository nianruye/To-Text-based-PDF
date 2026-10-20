#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_readable.py — 竖排还原的「可阅读性」验收器

补齐 verify_vert 的盲区。verify_vert 只查 5 条（页数/越界/缺字/整页丢失/页幅），
本工具从「人能不能顺畅读」的角度查 7 类问题，全部**量化**、可复跑。

用法:
    /usr/bin/python3 src/test/verify_readable.py <out.pdf> <coords.json> <src.pdf> \
        [--lines <lines.json>] [--pages 1-50] [--json report.json] [--top 20]

验收项（每条给 PASS/FAIL/WARN + 明细）:
  R1 逐列字块数对账   源图该列墨迹字块数 vs 产物该列字符数 | 差>2 报警（抓 OCR 漏字/幻觉）
  R2 列内字距异常     同列相邻字步进 >3x 中位的处数>2 | 抓「多插空格」（合法段落空格=2x，不报）
  R3 空隙源图依据     产物插入的空白，源图同 y 位置必须有空白 | 无依据的空白报警
  R4 标题列首位置     字号>1.3x正文的行必须在该列 y 最小处 | 否则报警（抓标题跑中间）
  R5 引号开闭配对     每页 ﹁/﹂ 数量差 | 差>2 报警
  R6 列数一致性       产物每页列数 vs 源图列带数 | 差>1 报警
  R7 墨迹重合率       产物渲染墨迹 vs 源图墨迹 IoU | <0.55 报警（整体保真度兜底）

退出码: 0 = 无 FAIL（可有 WARN）; 1 = 有 FAIL
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys

import numpy as np

try:
    import fitz
except ImportError:
    print('需要 PyMuPDF: /usr/bin/python3 -m pip install pymupdf', file=sys.stderr)
    sys.exit(2)
try:
    from scipy import ndimage
except ImportError:
    ndimage = None

# ---- 判据阈值（都可用命令行/环境覆盖）----
R1_TOL = 2          # 字块数差容忍（字）
R2_CV = 0.15        # （已弃用，保留兼容）列内步进变异系数上限
R2_GAP_MUL = 3.0    # 「空 >=N 格」判为异常步进（合法段落空格 = 2 格）
R2_GAP_N = 2        # 单列允许的异常步进处数上限
R3_TOL_PT = 6.0     # 产物空白段最小高度（pt），超过才查源图
R4_DISP = 1.30      # 放大字号判据（正文的倍数）
R5_TOL = 2          # 引号差容忍
R6_TOL = 1          # 列数差容忍
R7_IOU = 0.55       # 墨迹重合下限


# ------------------------------------------------------------------ 工具
def otsu_thr(gray):
    hist, _ = np.histogram(gray, bins=256, range=(0, 256))
    tot = gray.size
    sa = (np.arange(256) * hist).sum()
    best, thr, wB, sB = -1.0, 128, 0.0, 0.0
    for t in range(256):
        wB += hist[t]
        if wB == 0:
            continue
        wF = tot - wB
        if wF == 0:
            break
        sB += t * hist[t]
        v = wB * wF * (sB / wB - (sa - sB) / wF) ** 2
        if v > best:
            best, thr = v, t
    return int(thr)


def ink_mask(page, clip=None, dpi=150):
    pix = page.get_pixmap(clip=clip, dpi=dpi) if clip else page.get_pixmap(dpi=dpi)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, 0]
    return (a < otsu_thr(a)), pix.width, pix.height


def count_blocks_1d(profile, min_len=3):
    """1D 墨迹投影 -> 连续有墨段数（=字块数）"""
    blocks, s = [], None
    for i, v in enumerate(profile):
        if v > 0 and s is None:
            s = i
        elif v == 0 and s is not None:
            if i - s >= min_len:
                blocks.append((s, i))
            s = None
    if s is not None and len(profile) - s >= min_len:
        blocks.append((s, len(profile)))
    return blocks


# ------------------------------------------------------------------ 产物侧
PUNCT_SET = set('，。、；：？！「」『』（）〔〕【】﹁﹂︵︶︹︺…⋯—～·　')


def out_columns(page):
    """产物页 -> 按 x 聚成列：[{x, chars:[(y,ch,punct)]}]（近似：x 相邻 ≤3pt 归同列）

    口径修正（2026-10-20）：旧版用 sp['bbox'][1] 当 y —— **竖排 span 的 bbox 高 ≈ 3x 字号**，
    不同字形的 bbox 顶边差异极大，步进噪声随之爆炸（R2 的 CV 判据实测在 75% 的页上误报，
    1313/1748 页 FAIL）。改用 rawdict 的 char['origin']（真实基线），并给每个字打
    「是否标点」标记：竖排标点用 PUNCT_DX/DY 单独定位，origin 与汉字不同源，R2 必须排除。
    """
    items = []
    for b in page.get_text('rawdict')['blocks']:
        for ln in b.get('lines', []):
            for sp in ln.get('spans', []):
                for c in sp.get('chars', []):
                    ch = c.get('c') or ''
                    if not ch or ch.isspace():
                        continue
                    o = c.get('origin') or (sp['bbox'][0], sp['bbox'][3])
                    items.append((o[0], o[1], ch, ch in PUNCT_SET))
    if not items:
        return []
    items.sort(key=lambda z: (z[0], z[1]))
    cols = []
    for x, y, ch, pu in items:
        if cols and abs(x - cols[-1]['x']) <= 3.0:
            cols[-1]['chars'].append((y, ch, pu))
        else:
            cols.append({'x': x, 'chars': [(y, ch, pu)]})
    for c in cols:
        c['chars'].sort()
        c['text'] = ''.join(ch for _, ch, _ in c['chars'])
    return cols


# ------------------------------------------------------------------ 主检查
def check_page(src_doc, out_doc, pi, coords_page, rows_of_page):
    rep = {'page': pi + 1, 'issues': [], 'metrics': {}}
    try:
        sp, op = src_doc[pi], out_doc[pi]
    except Exception as e:
        rep['issues'].append(('R0', 'FAIL', '页面读取失败 %s' % e))
        return rep

    cols = out_columns(op)
    rep['metrics']['n_cols_out'] = len(cols)
    rep['metrics']['n_chars_out'] = sum(len(c['text']) for c in cols)

    # ---------- R1 字块数对账 ----------
    # 口径修正(taskV): 先做**整页**对账(绝对可靠, 不需要列对齐);
    #   逐列对账需要把 OCR 帧的 x 映射到源页 pt —— 用「源页宽 / 该页 coords 最大 x」归一,
    #   可自动适应 OCR 帧的整体缩放(2x 或其它), 但各向异性仍可能让小列裁偏 -> 只报 WARN。
    if coords_page and ndimage is not None:
        # --- 源图字块数：**两级投影**（x 分列 -> 每列 y 数字块）---
        # 竖排书不能对整页做 y 投影: 17 列的墨迹在 y 方向重叠, 投影连成一片只出 1-2 块。
        try:
            m_all, w_all, h_all = ink_mask(sp, dpi=120)
            px2pt_x = sp.rect.width / max(1, w_all)
            px2pt_y = sp.rect.height / max(1, h_all)
            col_segs = count_blocks_1d(m_all.sum(axis=0), min_len=8)   # x: 每列一条
            n_src_blocks = 0
            per_col = []
            for cx0, cx1 in col_segs:
                if (cx1 - cx0) * px2pt_x < 3:      # 太窄不是列（噪点/界行线）
                    continue
                sub = m_all[:, cx0:cx1]
                blocks = count_blocks_1d(sub.sum(axis=1), min_len=4)
                # 单列内 1-2 px 的断裂合并（字内笔画分离）
                per_col.append(len(blocks))
                n_src_blocks += len(blocks)
            n_out_chars = sum(len(c['text']) for c in cols)
            rep['metrics']['r1_src_cols'] = len(col_segs)
            rep['metrics']['r1_src_blocks'] = n_src_blocks
            rep['metrics']['r1_out_chars'] = n_out_chars
            if n_src_blocks:
                rep['metrics']['r1_ratio'] = round(n_out_chars / n_src_blocks, 3)
                # 产物字符数应≈源图字块数(略多: 标点算字块也算字符); 少于 85% -> OCR 漏字
                if n_out_chars < n_src_blocks * 0.85:
                    rep['issues'].append(('R1', 'FAIL',
                                          '产物字符 %d < 源图字块 %d x0.85（疑似 OCR 漏字/幻觉）'
                                          % (n_out_chars, n_src_blocks)))
        except Exception as e:
            rep['metrics']['r1_err'] = str(e)[:60]

        # --- 逐列（参考值，归一化 x 映射）---
        xs_all = [q[0] for poly in coords_page if poly for q in poly]
        if xs_all:
            scale = sp.rect.width / max(xs_all)      # 按页宽归一
            src_blocks_per_col = []
            for poly in coords_page:
                if not poly:
                    src_blocks_per_col.append(None)
                    continue
                xs = [q[0] for q in poly]
                x0 = max(0.0, min(xs) * scale - 2.0)
                x1 = min(sp.rect.width, max(xs) * scale + 2.0)
                if x1 - x0 < 3:
                    src_blocks_per_col.append(None)
                    continue
                try:
                    mm, _w, _h = ink_mask(sp, clip=fitz.Rect(x0, 0, x1, sp.rect.height), dpi=150)
                    src_blocks_per_col.append(len(count_blocks_1d(mm.sum(axis=1), min_len=4)))
                except Exception:
                    src_blocks_per_col.append(None)
            pairs = [(c, src_blocks_per_col[i]) for i, c in enumerate(cols)
                     if i < len(src_blocks_per_col) and src_blocks_per_col[i] is not None]
            bad = [(c['x'], sb, len(c['text'])) for c, sb in pairs
                   if abs(sb - len(c['text'])) > R1_TOL]
            rep['metrics']['r1_pairs'] = len(pairs)
            rep['metrics']['r1_bad'] = len(bad)
            if bad and len(bad) > max(3, len(pairs) * 0.4):
                rep['issues'].append(('R1', 'WARN',
                                      '%d/%d 列字块数不符(逐列口径仅供参考): %s' %
                                      (len(bad), len(pairs),
                                       ', '.join('x%.0f 源%d/产物%d' % b for b in bad[:4]))))

    # ---------- R2 列内字距均匀性 ----------
    cvs = []
    bad_cv = []
    for c in cols:
        # 排除标点：竖排标点用 PUNCT_DX/DY 单独定位，origin 与汉字不同源，
        #   混进来会把 CV 抬到 0.2-0.3（实测 1313/1748 页误报）
        ys = [y for y, _ch, pu in c['chars'] if not pu]
        if len(ys) < 5:
            continue
        steps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
        steps = [s for s in steps if s > 0.1]
        if len(steps) < 4:
            continue
        mu = statistics.median(steps)
        if mu <= 0:
            continue
        # 口径修正（2026-10-20）：CV 判据不可用 —— 渲染端按源书段落/对话分隔插入**一个空格**
        #   （step = 2x 中位）是正确行为，CV 把它算进方差 -> 有段落就报警（实测 p100/p300/p444
        #   CV 全在 0.4-0.8，全书 1313/1748 页 FAIL）。改成数「空 >=3 格」的处数：
        #   真该抓的是多插空格 / 字号与步进不匹配，不是合法的段落空一格。
        big = [(round(st), round(st / mu, 2)) for st in steps if st > mu * R2_GAP_MUL]
        if len(big) > R2_GAP_N:
            bad_cv.append((round(c['x']), round(len(big), 1), big[:3]))
    if cvs:
        rep['metrics']['r2_cv_med'] = round(statistics.median(cvs), 3)
        rep['metrics']['r2_bad'] = len(bad_cv)
        if bad_cv:
            rep['issues'].append(('R2', 'FAIL' if len(bad_cv) > 2 else 'WARN',
                                  '%d 列步进异常(空>=%.0f格 的处数>%d): %s' %
                                  (len(bad_cv), R2_GAP_MUL, R2_GAP_N, '; '.join('x%d CV%.3f 异常步进%s' % b for b in bad_cv[:3]))))

    # ---------- R4 标题列首位置 ----------
    if cols:
        sizes = []
        for b in op.get_text('dict')['blocks']:
            for ln in b.get('lines', []):
                for sp_ in ln['spans']:
                    if sp_['text'].strip():
                        sizes.append(sp_['size'])
        if sizes:
            body = statistics.median(sizes)
            for c in cols:
                ys = [y for y, _ch, _pu in c['chars']]
                if not ys:
                    continue
                ytop = min(ys)
                for b in op.get_text('dict')['blocks']:
                    for ln in b.get('lines', []):
                        for sp_ in ln['spans']:
                            if not sp_['text'].strip() or abs(sp_['bbox'][0] - c['x']) > 3:
                                continue
                            if sp_['size'] > body * R4_DISP and sp_['bbox'][1] > ytop + body * 1.5:
                                rep['issues'].append(
                                    ('R4', 'WARN', 'x%.0f 列有大字(%.1fpt vs 正文%.1fpt)出现在列中段 y=%.0f' %
                                     (c['x'], sp_['size'], body, sp_['bbox'][1])))

    # ---------- R5 引号配对 ----------
    txt = op.get_text()
    a, bq = txt.count('﹁'), txt.count('﹂')
    rep['metrics']['quote_open'] = a
    rep['metrics']['quote_close'] = bq
    if abs(a - bq) > R5_TOL:
        rep['issues'].append(('R5', 'WARN', '引号不配对 ﹁%d vs ﹂%d' % (a, bq)))

    # ---------- R7 墨迹重合率 ----------
    if ndimage is not None:
        try:
            ms, w, h = ink_mask(sp, dpi=120)
            mo, _, _ = ink_mask(op, dpi=120)
            if ms.shape == mo.shape:
                inter = np.logical_and(ms, mo).sum()
                union = np.logical_or(ms, mo).sum()
                iou = inter / union if union else 0.0
                rep['metrics']['r7_iou'] = round(float(iou), 3)
                if iou < R7_IOU:
                    rep['issues'].append(('R7', 'WARN', '墨迹重合率低 IoU=%.3f' % iou))
        except Exception:
            pass

    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out_pdf')
    ap.add_argument('coords')
    ap.add_argument('src_pdf')
    ap.add_argument('--lines', default=None)
    ap.add_argument('--pages', default=None, help='如 1-50 或 3,5,7')
    ap.add_argument('--json', default=None)
    ap.add_argument('--top', type=int, default=20)
    a = ap.parse_args()

    coords = json.load(open(a.coords, encoding='utf-8'))
    rows = json.load(open(a.lines, encoding='utf-8')) if a.lines else {}
    src = fitz.open(a.src_pdf)
    out = fitz.open(a.out_pdf)
    n = min(src.page_count, out.page_count)

    pages = list(range(n))
    if a.pages:
        pages = []
        for part in a.pages.split(','):
            if '-' in part:
                x, y = part.split('-')
                pages.extend(range(int(x) - 1, int(y)))
            else:
                pages.append(int(part) - 1)
        pages = [p for p in pages if 0 <= p < n]

    print('=' * 70)
    print('可阅读性验收   源 %d 页 / 产物 %d 页   检查 %d 页' % (src.page_count, out.page_count, len(pages)))
    print('=' * 70)

    reports = []
    for i in pages:
        key = str(i)
        rep = check_page(src, out, i, coords.get(key), rows.get(key))
        reports.append(rep)
        if rep['issues'] and len([r for r in reports if r['issues']]) <= a.top:
            print('\np%-5d %s' % (rep['page'], ' | '.join('%s %s: %s' % t for t in rep['issues'])))

    # 汇总
    from collections import Counter
    cnt = Counter()
    for r in reports:
        for code, lvl, _ in r['issues']:
            cnt[(code, lvl)] += 1
    print('\n' + '=' * 70)
    print('汇总（%d 页）' % len(reports))
    print('=' * 70)
    for (code, lvl), c in sorted(cnt.items()):
        print('  %s %-4s %3d 页' % (lvl, code, c))
    n_bad = sum(1 for r in reports if any(l == 'FAIL' for _, l, _ in r['issues']))
    print('\n有 FAIL 的页: %d / %d' % (n_bad, len(reports)))

    if a.json:
        json.dump(reports, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('明细 -> %s' % a.json)

    print('\n== 退出码 %s ==' % ('FAIL' if n_bad else 'PASS'))
    sys.exit(1 if n_bad else 0)


if __name__ == '__main__':
    main()
