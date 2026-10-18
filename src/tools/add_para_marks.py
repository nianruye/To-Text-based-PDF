#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补渲染「段首圈点 ⊙」—— OCR 漏识的段落起首标记

背景（实测 wz7 p43/p44 凡例）：
  源书每个段落开头有一个「圈点」(外圈 + 中心实心点, 结构同 ⊙), 但 PaddleOCR-VL
  把那一格当噪点跳过 -> 文本里没有这个字 -> 管线无从渲染 -> 产物缺失。

为什么能可靠找回来（两条独立证据, 不是猜）：
  几何: ①该列 OCR 框顶比本页其他列顶中位高出 0.6-1.6 个字格（圈点占了一整格, 把列顶推高）
        ②框高 ÷ 本页标准步进 − OCR 字数 ≈ 1（框里有一格的墨迹没有对应文字）
  形状: 那一格的墨迹径向剖面呈「中心实心 → 中空环 → 外圈」双峰
        实测 p43/p44 六处: 中心 100%, 第3环 0-11%, 最外环 85-100%
        误报对照 p77/p1699（笔画密的汉字）: 中心 73%/32%, 无中空环
  实测全书只有 8 个几何候选, 形状筛后 6 个命中（即凡例六段）, 2 个误报被排除。

用法:
  /usr/bin/python3 src/tools/add_para_marks.py <in.pdf> <lines.json> <coords.json> <src.pdf>
        [-o out.pdf] [--dry-run] [--report r.json]
"""
import argparse
import json
import os
import statistics
import sys

DING = 0x2299          # ⊙
FONT_PATH = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'

# 判据阈值（全部相对量，不写死某本书的绝对值）
RISE_LO, RISE_HI = 0.55, 1.70      # 列首高出本页列顶中位的格数区间
EXTRA_LO, EXTRA_HI = 0.60, 1.60    # 框内格数 − OCR字数 的区间
MIN_COLS, MIN_CHARS = 5, 8         # 页内最少列数 / 列最少字数（统计与判据的样本下限）
# 形状阈值（实测标定, 见下）:
#   真圈点 p43×3 + p44×3: 中心 100%, 第3环 1-14%, 最外环 70-100%
#   误报 p77(汉字):        中心  73%, 第3环   54%, 最外环  47%
#   误报 p1699(汉字「酒」): 中心  32%, 第3环   62%, 最外环  51%
#   -> 中心填充是主判据(两类 100% vs 73%/32%, 间隔拉开); 第3环中空是辅证;
#      最外环只作下限兜底, 不能设太高(p43 段2/段3 只有 70%/74%, 设 80 会误杀真圈点)。
CENTER_MIN = 90.0                  # 中心区填充下限(%)
RING3_MAX = 20.0                   # 第 3 环（0.4-0.6 半径）填充上限(%) —— 中空
OUTER_MIN = 55.0                   # 最外环填充下限(%)


def boxes(LI, CO, k):
    out = []
    for t, poly in zip(LI.get(k) or [], CO.get(k) or []):
        try:
            xs = [q[0] for q in poly]
            ys = [q[1] for q in poly]
        except Exception:
            continue
        out.append((min(xs) / 2.0, max(xs) / 2.0, min(ys) / 2.0, max(ys) / 2.0, str(t)))
    return out


def shape(pix, cell_pt, dpi):
    """列首那格的径向剖面 -> dict 或 None"""
    import numpy as np
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    ink = img[:, :, 0].astype(np.int16) < 150
    if not ink.any():
        return None
    ys, xs = np.where(ink)
    sub = ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    H, W = sub.shape
    if H < 8 or W < 8:
        return None
    cy, cx = H / 2.0, W / 2.0
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    rmax = min(H, W) / 2.0
    band = []
    for k in range(5):
        m = (r >= rmax * k / 5.0) & (r < rmax * (k + 1) / 5.0)
        band.append(100.0 * sub[m].sum() / max(1, m.sum()))
    cm = r < rmax * 0.22
    center = 100.0 * sub[cm].sum() / max(1, cm.sum())
    return dict(band=band, center=center)


def detect(pdf_src, LI, CO):
    """返回 [(page1based, x0, x1, y_mark_pt, cell_pt)]"""
    import fitz
    src = fitz.open(pdf_src)
    hits = []
    for k in sorted(LI.keys(), key=lambda x: int(x)):
        bs = boxes(LI, CO, k)
        if len(bs) < MIN_COLS:
            continue
        steps = [(b[3] - b[2]) / len(b[4].replace('\n', ''))
                 for b in bs if len(b[4].replace('\n', '')) >= MIN_CHARS]
        if len(steps) < 3:
            continue
        ps = statistics.median(steps)
        if ps <= 0:
            continue
        tops = statistics.median(b[2] for b in bs)
        p = int(k) + 1
        for x0, x1, y0, y1, t in bs:
            s = t.replace('\n', '')
            n = len(s)
            if n < MIN_CHARS:
                continue
            extra = (y1 - y0) / ps - n
            if not (EXTRA_LO <= extra <= EXTRA_HI):
                continue
            rise = (tops - y0) / ps
            if not (RISE_LO <= rise <= RISE_HI):
                continue
            try:
                pix = src[p - 1].get_pixmap(
                    clip=fitz.Rect(x0, y0 - 2, x1, y0 + ps + 2), dpi=400)
            except Exception:
                continue
            f = shape(pix, ps, 400)
            if not f:
                continue
            b = f['band']
            if (f['center'] >= CENTER_MIN and b[2] <= RING3_MAX and b[4] >= OUTER_MIN):
                hits.append((p, x0, x1, y0, ps,
                             dict(rise=round(rise, 2), extra=round(extra, 2),
                                  center=round(f['center']), band=[round(v) for v in b],
                                  text=s[:12])))
    src.close()
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('lines_json')
    ap.add_argument('coords_json')
    ap.add_argument('src_pdf')
    ap.add_argument('-o', '--out')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report')
    args = ap.parse_args()

    LI = json.load(open(args.lines_json, encoding='utf-8'))
    CO = json.load(open(args.coords_json, encoding='utf-8'))
    hits = detect(args.src_pdf, LI, CO)
    print('段首圈点命中: %d 处 / %d 页' % (len(hits), len(set(h[0] for h in hits))))
    for p, x0, x1, y0, ps, info in hits:
        print('  p%-5d x%.1f-%.1f y%.1f 格%.1f  高%.2f格 多%.2f格 中心%d%% 径向%s  %s'
              % (p, x0, x1, y0, ps, info['rise'], info['extra'],
                 info['center'], '/'.join(str(v) for v in info['band']), info['text']))
    if args.report:
        json.dump([{'page': h[0], 'x0': h[1], 'x1': h[2], 'y': h[3], 'cell': h[4],
                    **h[5]} for h in hits], open(args.report, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('  报告 -> %s' % args.report)

    if args.dry_run or not hits:
        print('\n(--dry-run / 无命中, 未写盘)')
        return 0

    import fitz
    doc = fitz.open(args.pdf)
    font = fitz.Font(fontfile=FONT_PATH + '') if os.path.exists(FONT_PATH) else None
    n_put = 0
    for p, x0, x1, y0, ps, info in hits:
        pg = doc[p - 1]
        cell = ps
        # ⊙ 画在这一格的中心：x 用该列中心，y 用格中心
        cx = (x0 + x1) / 2.0
        cy = y0 + cell / 2.0
        size = cell * 0.92
        try:
            if font is not None:
                tw = font.text_length(chr(DING), fontsize=size)
                pg.insert_text((cx - tw / 2.0, cy + size * 0.34), chr(DING),
                               fontsize=size, fontfile=FONT_PATH, fontname='NotoSerif',
                               render_mode=0)
            else:
                pg.insert_text((cx - size * 0.3, cy + size * 0.34), chr(DING), fontsize=size)
            n_put += 1
        except Exception as e:
            print('  p%d 写入失败: %s' % (p, e))
    out = args.out or args.pdf
    tmp = out + '.tmp'
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, out)
    print('\n✓ 已补画 %d 处圈点 -> %s' % (n_put, out))

    d2 = fitz.open(out)
    tot = sum(1 for i in range(len(d2)) for ch in d2[i].get_text() if ord(ch) == DING)
    print('复核: 文本层 ⊙ 计数 %d' % tot)
    d2.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
