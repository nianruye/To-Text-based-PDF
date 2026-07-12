#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实证:字号能否可靠识别 + 面积/字数估计量评估。"""
import json, sys, statistics, math
import numpy as np

DPI = 200
PT = 72.0 / DPI  # px -> pt

def load(doc):
    sl = json.load(open(f'/opt/test/{doc}_spotting_lines.json', encoding='utf-8'))
    co = json.load(open(f'/opt/test/{doc}_spotting_coords.json', encoding='utf-8'))
    rows = []
    for key in sl:
        polys = co.get(key, [])
        for i, l in enumerate(sl[key]):
            t = l.strip()
            if i < len(polys) and polys[i] and len(t) >= 1:
                xs = [p[0] for p in polys[i]]; ys = [p[1] for p in polys[i]]
                w = max(xs) - min(xs); h = max(ys) - min(ys)
                cjk = sum(1 for c in t if ord(c) > 0x2e80)  # CJK 字数
                rows.append(dict(page=key, i=i, t=t, x0=min(xs), y0=min(ys),
                                 yc=(min(ys)+max(ys))/2, w=w, h=h, n=len(t), cjk=cjk))
    return sl, co, rows

def kmeans1d(vals, k, iters=100):
    v = np.sort(np.array(vals, float))
    # init centers by quantiles
    centers = np.quantile(v, np.linspace(0.1, 0.9, k))
    for _ in range(iters):
        d = np.abs(v[:, None] - centers[None, :])
        lab = d.argmin(1)
        new = np.array([v[lab == j].mean() if (lab == j).any() else centers[j] for j in range(k)])
        if np.allclose(new, centers): break
        centers = new
    d = np.abs(v[:, None] - centers[None, :]); lab = d.argmin(1)
    return centers, lab, v

def cv(xs):
    xs = [x for x in xs if x > 0]
    if len(xs) < 2: return float('nan')
    return statistics.pstdev(xs) / statistics.mean(xs)

def analyze(doc):
    print("="*72)
    print(f"文档 {doc}")
    print("="*72)
    sl, co, rows = load(doc)
    print(f"总行数 {len(rows)}")
    heights = [r['h'] for r in rows]
    print(f"行高(px) min/median/max = {min(heights):.1f}/{statistics.median(heights):.1f}/{max(heights):.1f}")

    # ---- 1. 行高分布聚类 ----
    print("\n[1] 行高聚类 (k=3: 矮=脚注 / 中=正文 / 高=标题)")
    centers, lab, v = kmeans1d(heights, 3)
    order = np.argsort(centers)
    names = ['矮(脚注)', '中(正文)', '高(标题)']
    cluster_info = {}
    for rank, j in enumerate(order):
        hs = v[lab == j]
        med = float(np.median(hs))
        cluster_info[names[rank]] = dict(med_px=med, med_pt=med*PT, n=len(hs),
                                          pct=100*len(hs)/len(v), lo=float(hs.min()), hi=float(hs.max()))
        print(f"  {names[rank]:8s}: 中位高 {med:5.1f}px ({med*PT:4.1f}pt)  占比 {100*len(hs)/len(v):5.1f}%  范围[{hs.min():.0f},{hs.max():.0f}]  n={len(hs)}")
    # 类间分离度
    c_sorted = np.sort(centers)
    seps = [(c_sorted[i+1]-c_sorted[i])/((c_sorted[i+1]+c_sorted[i])/2) for i in range(len(c_sorted)-1)]
    print(f"  相邻类中心相对间隔: {[round(s,2) for s in seps]}  (>0.15 视为可分)")

    # 正文类(中)阈值 用于后续
    body_center = c_sorted[1]
    body_lo, body_hi = body_center*0.85, body_center*1.2  # 与 build_geom line_font 一致
    body_rows = [r for r in rows if body_lo <= r['h'] <= body_hi and r['cjk'] >= 4]

    # ---- 2. 高度估字号 vs MEASURE/cw 估字号 ----
    print("\n[2] 两种字号估计 (仅正文类, n=%d)" % len(body_rows))
    # 方法A: 高度 -> 字号  font = h * PT
    fontA = [r['h']*PT for r in body_rows]
    # 方法B: MEASURE/cw  用满行 width/chars。先取满行(width>0.8*maxw)
    ws = [r['w'] for r in body_rows]; maxw = max(ws) if ws else 1
    full = [r for r in body_rows if r['w'] > 0.80*maxw]
    # 逐行 width/chars (用总字符数 n, 与 build_geom cw=len(t) 一致)
    fontB_per = [r['w']/r['n']*PT for r in full]
    # 全局 build_geom 式: MEASURE = median(full width)*PT ; cw = median(chars) ; FONT = MEASURE/cw
    MEASURE = statistics.median([r['w'] for r in full])*PT
    cw = statistics.median([r['n'] for r in full])
    FONT_global = MEASURE / cw
    medA = statistics.median(fontA)
    medB = statistics.median(fontB_per)
    print(f"  A 高度法:  逐行 font=h*72/DPI  中位={medA:.2f}pt  CV={cv(fontA):.3f}")
    print(f"  B MEASURE/cw(逐行 w/n): 中位={medB:.2f}pt  CV={cv(fontB_per):.3f}")
    print(f"  B 全局 build_geom式: MEASURE={MEASURE:.1f}pt cw={cw:.0f} -> FONT={FONT_global:.2f}pt")
    print(f"  两法中位差: {abs(medA-medB):.2f}pt ({100*abs(medA-medB)/max(medA,medB):.1f}%)")
    print(f"  -> CV 更小者更稳: A={cv(fontA):.3f} vs B={cv(fontB_per):.3f}")

    # ---- 3. 面积/字数 估计量 ----
    print("\n[3] 面积/字数 估字号")
    # 3a 逐行面积/字数: font = sqrt(w*h/n)
    fontC_line = [math.sqrt(r['w']*r['h']/r['n'])*PT for r in body_rows if r['n']>0]
    print(f"  3a 逐行 sqrt(w*h/n):  中位={statistics.median(fontC_line):.2f}pt  CV={cv(fontC_line):.3f}")
    print(f"     vs 高度法A中位 {medA:.2f}pt  偏差 {statistics.median(fontC_line)-medA:+.2f}pt")

    # 3b 区域面积/字数 (用户设想): 取每页正文块外接矩形, area=W*H(含行间距), N=块内总字数
    # 区域高 H = 多行, 因此耦合行距
    reg_font = []; reg_detail = []
    for key in sl:
        rs = [r for r in rows if r['page']==key and body_lo <= r['h'] <= body_hi and r['cjk']>=4]
        if len(rs) < 3: continue
        x0 = min(r['x0'] for r in rs); x1 = max(r['x0']+r['w'] for r in rs)
        y0 = min(r['y0'] for r in rs); y1 = max(r['y0']+r['h'] for r in rs)
        W = x1-x0; H = y1-y0
        N = sum(r['n'] for r in rs)
        f = math.sqrt(W*H/N)*PT
        reg_font.append(f)
        reg_detail.append((key, f, len(rs)))
    if reg_font:
        print(f"  3b 区域外接矩形 sqrt(W*H/N) [含行间距]: 中位={statistics.median(reg_font):.2f}pt  CV={cv(reg_font):.3f}")
        print(f"     vs 高度法A {medA:.2f}pt  偏差 {statistics.median(reg_font)-medA:+.2f}pt ({100*(statistics.median(reg_font)-medA)/medA:+.1f}%)")

    # ---- 4. 字号 vs 行距 独立性 ----
    print("\n[4] 行距(相邻行中心距)与字号 独立测量")
    pitches_all = []
    pitch_ratio = []  # pitch/font 每页
    for key in sl:
        rs = sorted([r for r in rows if r['page']==key and body_lo <= r['h'] <= body_hi and r['cjk']>=4], key=lambda r:r['yc'])
        ycs = [r['yc'] for r in rs]
        pit = [b-a for a,b in zip(ycs, ycs[1:]) if 10 < (b-a) < 80]
        if pit:
            pitches_all += pit
            pf = statistics.median(pit)
            hf = statistics.median([r['h'] for r in rs])
            pitch_ratio.append(pf/hf)  # 行距/行高 = 行距/字号
    if pitches_all:
        BASELINE = statistics.median(pitches_all)*PT
        print(f"  行距(中心距)中位 = {statistics.median(pitches_all):.1f}px = {BASELINE:.2f}pt")
        print(f"  行距/行高 比值(逐页): 中位={statistics.median(pitch_ratio):.3f}  min={min(pitch_ratio):.3f} max={max(pitch_ratio):.3f}  CV={cv(pitch_ratio):.3f}")
        print(f"  -> 若假定固定比(耦合推导),此比的 CV 即误差; CV={cv(pitch_ratio):.3f}")
        # 区域法能否分离字号/行距: 构造两个反例
        print(f"  区域面积耦合示例: area/N = (w/字数)*(行距) ≈ 字宽*行距")
        f_from_area = math.sqrt(statistics.median([r['w']/r['n'] for r in body_rows])* (statistics.median(pitches_all)))*PT
        print(f"     sqrt(字宽*行距)={f_from_area:.2f}pt vs 真字号(高度){medA:.2f}pt -> 被行距抬高 {100*(f_from_area-medA)/medA:+.1f}%")

    return dict(doc=doc, cluster=cluster_info, medA=medA, medB=medB,
                cvA=cv(fontA), cvB=cv(fontB_per),
                reg_med=statistics.median(reg_font) if reg_font else None,
                cvC_line=cv(fontC_line),
                baseline_pt=statistics.median(pitches_all)*PT if pitches_all else None,
                pitch_ratio_med=statistics.median(pitch_ratio) if pitch_ratio else None,
                pitch_ratio_cv=cv(pitch_ratio) if pitch_ratio else None,
                n=len(rows), body_n=len(body_rows))

if __name__ == '__main__':
    res = {}
    for doc in ['wz1', 'wz2']:
        res[doc] = analyze(doc)
    print("\n"+"="*72)
    print("汇总")
    print("="*72)
    for doc in ['wz1','wz2']:
        r = res[doc]
        print(f"{doc}: 正文字号 高度法={r['medA']:.1f}pt(CV{r['cvA']:.3f}) MEASURE/cw={r['medB']:.1f}pt(CV{r['cvB']:.3f}) | "
              f"面积/字数区域法={r['reg_med']:.1f}pt | 行距={r['baseline_pt']:.1f}pt 行距/字号比={r['pitch_ratio_med']:.2f}(CV{r['pitch_ratio_cv']:.3f})")
