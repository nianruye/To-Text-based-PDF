#!/usr/bin/env python3
"""taskO: wz7 建排产物 vs 源书 逐页对账(列数/列距/字高/每列字数/墨迹覆盖率)。
源侧与产物侧同一套口径(2x 灰度、逐页 Otsu、墨迹列带/字 run)。
用法: metrics_nf.py <out.pdf> <src.pdf> <out_page0based 列表, 逗号分隔> <src_page0based 列表>
"""
import statistics, sys
import fitz
import numpy as np


def gray(doc, i, sc=2.0):
    p = doc[i]
    pix = p.get_pixmap(matrix=fitz.Matrix(sc, sc), colorspace=fitz.csGRAY)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()


def otsu(a):
    h = np.bincount(np.asarray(a).ravel(), minlength=256).astype(float)
    tot = h.sum(); sm = float((np.arange(256) * h).sum())
    best, bk, w0, s0 = -1.0, 128, 0.0, 0.0
    for t in range(256):
        w0 += h[t]; s0 += t * h[t]
        w1 = tot - w0
        if w0 <= 0 or w1 <= 0: continue
        v = w0 * w1 * (s0 / w0 - (sm - s0) / w1) ** 2
        if v > best: best, bk = v, t
    return bk


def runs(mask, gap=2):
    out = []; i0 = None; n = len(mask)
    for i, v in enumerate(mask):
        if v and i0 is None: i0 = i - gap
        elif not v and i0 is not None:
            if i - gap > i0: out.append((max(0, i0), i - gap))
            i0 = None
    if i0 is not None and n > i0: out.append((max(0, i0), n))
    return out


def analyze(a, cov=0.12):
    """2x 灰度页 -> 版面统计(dict)。版心 = 全部墨迹(去扫描边条)包围盒。"""
    ink = a < otsu(a)
    H, W = ink.shape
    # 去四边 2% 的扫描边条
    m = ink[int(H * 0.02):int(H * 0.98), int(W * 0.02):int(W * 0.98)]
    if not m.any(): return None
    ys = np.where(m.any(axis=1))[0]; xs = np.where(m.any(axis=0))[0]
    it, ib = ys[0], ys[-1]; il, ir = xs[0], xs[-1]
    sub = m[it:ib + 1, il:ir + 1]
    colc = sub.mean(axis=0)
    bands = [(a2, b2) for a2, b2 in runs(colc > cov, 4) if b2 - a2 >= 16]
    cs = [(a2 + b2) / 2.0 for a2, b2 in bands]
    ds = [y - x for x, y in zip(cs, cs[1:]) if 8 < y - x < 400]
    pitch = statistics.median(ds) if ds else 0.0
    hh, st, nch = [], [], []
    for a2, b2 in bands:
        sl = sub[:, a2:b2 + 1].any(axis=1)
        rs = [(x, y) for x, y in runs(sl, 1) if y - x >= 8]
        if len(rs) < 3: continue
        hs = sorted(y - x for x, y in rs)
        hh.append(hs[len(hs) // 2])
        cc = sorted((x + y) / 2.0 for x, y in rs)
        dd = sorted(d for d in (cc[i + 1] - cc[i] for i in range(len(cc) - 1)) if d < 200)
        if dd: st.append(dd[len(dd) // 2])
        nch.append(len(rs))
    return {'w': W / 2.0, 'h': H / 2.0, 'ncol': len(bands), 'pitch': pitch / 2.0,
            'hm': (statistics.median(hh) / 2.0 if hh else 0), 'step': (statistics.median(st) / 2.0 if st else 0),
            'ntxt': (statistics.median(nch) if nch else 0), 'cov': float(sub.mean()),
            'bb': (il / 2.0, it / 2.0, ir / 2.0, ib / 2.0)}


if __name__ == '__main__':
    do = fitz.open(sys.argv[1]); ds = fitz.open(sys.argv[2])
    op = [int(x) for x in sys.argv[3].split(',')]; sp = [int(x) for x in sys.argv[4].split(',')]
    print('%-4s %-4s | %-24s | %-24s | %s' % ('出页', '源页', '产物 列/列距/字高/步进/中位字数', '源书 同', '覆盖率 产/源  页幅'))
    rows = []
    for oi, si in zip(op, sp):
        A = analyze(gray(do, oi)); B = analyze(gray(ds, si))
        if not A or not B: continue
        rows.append((oi, si, A, B))
        print('%-4d %-4d | %4d %6.1f %5.1f %6.1f %5s | %4d %6.1f %5.1f %6.1f %5s | %.3f/%.3f  %.0fx%.0f/%.0fx%.0f%s' % (
            oi + 1, si + 1, A['ncol'], A['pitch'], A['hm'], A['step'], A['ntxt'],
            B['ncol'], B['pitch'], B['hm'], B['step'], B['ntxt'], A['cov'], B['cov'],
            A['w'], A['h'], B['w'], B['h'],
            '' if abs(A['w'] - B['w']) < 1.5 and abs(A['h'] - B['h']) < 1.5 else '  <<纸型不符'))
    if rows:
        print('中位: 列数 产 %.0f / 源 %.0f | 列距 %.2f/%.2f | 字高 %.2f/%.2f | 覆盖率 %.3f/%.3f' % (
            statistics.median(r[2]['ncol'] for r in rows), statistics.median(r[3]['ncol'] for r in rows),
            statistics.median(r[2]['pitch'] for r in rows), statistics.median(r[3]['pitch'] for r in rows),
            statistics.median(r[2]['hm'] for r in rows), statistics.median(r[3]['hm'] for r in rows),
            statistics.median(r[2]['cov'] for r in rows), statistics.median(r[3]['cov'] for r in rows)))
