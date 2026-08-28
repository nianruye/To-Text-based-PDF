#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字体分类抽样 v5: OCR px → pt 坐标转换(修空图)。"""
import sys, os, json, tempfile, statistics, re
from PIL import Image

def main():
    src_pdf, lines_f, coords_f = sys.argv[1], sys.argv[2], sys.argv[3]
    out_dir = "/tmp/font_rows"
    DPI = 144
    for a in sys.argv[4:]:
        if a.startswith("--out"): out_dir = a.split("=")[1]
        if a.startswith("--DPI"): DPI = int(a.split("=")[1])
    os.makedirs(out_dir, exist_ok=True)

    sl = json.load(open(lines_f))
    co = json.load(open(coords_f))
    pages = sorted(sl.keys(), key=int)

    PN = re.compile(r'^\d{1,4}$')
    rows = []
    for pk in pages:
        cl = co.get(pk, [])
        for i, t in enumerate(sl[pk]):
            t = t.strip()
            if not t or i >= len(cl) or not cl[i]: continue
            xs = [p[0] for p in cl[i]]; ys = [p[1] for p in cl[i]]
            rows.append((int(pk), i, t, min(xs), min(ys), max(xs), max(ys)))

    hs = sorted(r[6] - r[4] for r in rows if r[6] - r[4] > 5)
    body_h = statistics.median(hs)
    big_thr, small_thr = body_h * 1.35, body_h * 0.75

    all_x1 = sorted(r[5] for r in rows)
    pw = all_x1[int(len(all_x1) * 0.95)]
    margin_l, margin_r = pw * 0.14, pw * 0.86

    page_h = {}
    for pk in pages:
        cl = co.get(pk, [])
        if cl: page_h[int(pk)] = max(p[1] for poly in cl for p in poly)

    cats = {"title": [], "subtitle": [], "body": [], "footnote": [], "header": []}
    for pk, i, t, x0, y0, x1, y1 in rows:
        h = y1 - y0
        ph = page_h.get(pk, 1000)
        if PN.fullmatch(t): continue
        in_body = margin_l < x0 and x1 < margin_r
        if h > big_thr and in_body:
            cx = (x0 + x1) / 2
            punct = sum(1 for c in t if c in '，。、；：')
            if abs(cx - pw / 2) < pw * 0.18 and len(t) <= 24 and punct <= 1:
                cats["title"].append((pk, i, t, x0, y0, x1, y1))
        elif h > body_h * 1.05 and in_body and len(t) <= 12 and re.match(r'^\d{1,2}[\.、．]?[^\d]', t):
            # 节标题: 行高略大 + 短行 + 行首数字编号(如 "1看不见的手")
            cats["subtitle"].append((pk, i, t, x0, y0, x1, y1))
        elif h < small_thr:
            if y0 < ph * 0.10 and in_body:
                cats["header"].append((pk, i, t, x0, y0, x1, y1))
            elif y0 > ph * 0.80 and in_body:
                cats["footnote"].append((pk, i, t, x0, y0, x1, y1))
        elif body_h * 0.85 <= h <= body_h * 1.15 and in_body:
            if (x1 - x0) > pw * 0.55 and len(t) >= 12:
                cats["body"].append((pk, i, t, x0, y0, x1, y1))

    picks = {}
    for cat, items in cats.items():
        items.sort(key=lambda r: len(r[2]), reverse=True)
        chosen, seen_pages = [], set()
        for it in items:
            if it[0] in seen_pages: continue
            chosen.append(it); seen_pages.add(it[0])
            if len(chosen) >= 3: break
        if len(chosen) < 2 and len(items) >= 2:
            chosen = items[:2]
        picks[cat] = chosen

    import fitz
    doc = fitz.open(src_pdf)
    manifest = {}
    for cat, items in picks.items():
        for n, (pk, i, t, x0, y0, x1, y1) in enumerate(items):
            pg = doc[pk]
            k = 72.0 / DPI                     # px → pt
            pad_pt = (y1 - y0) * k * 0.8
            rect = fitz.Rect(0, max(0, y0 * k - pad_pt), pg.rect.width,
                             min(pg.rect.height, y1 * k + pad_pt))
            if rect.height <= 0: 
                print(f"  [skip] {cat} p{pk} rect 高度<=0"); continue
            scale = DPI / 72.0
            clip = pg.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=rect, colorspace=fitz.csRGB)
            img = Image.frombytes("RGB", (clip.width, clip.height), clip.samples)
            out = f"{out_dir}/font_row_{cat}_{n}.png"
            img.save(out)
            manifest[out] = {"cat": cat, "page": pk, "text": t[:30], "x0": round(x0), "y0": round(y0), "h": round(y1-y0, 1)}
            print(f"  [{cat}] p{pk} y={y0:.0f} h={y1-y0:.0f}px  {t[:26]}... → {os.path.basename(out)}")
    doc.close()

    json.dump(manifest, open(f"{out_dir}/samples.json", "w"), ensure_ascii=False, indent=1)
    print(f"\n抽样完成: {len(manifest)} 张图 → {out_dir}")

if __name__ == "__main__":
    main()
