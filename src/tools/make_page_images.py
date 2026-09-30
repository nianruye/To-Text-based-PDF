#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""封面/扉页/版权页检测 + 生成贴图 PNG。

用法:
  python3 src/tools/make_page_images.py <扫描pdf> <lines.json> --out <png目录> [--pages 0,1,2 | --auto] [--dpi 144]
输出:
  <png目录>/p<页号>.png  (贴图页 PNG, 页面实际尺寸 2x)
  <png目录>/pages.json   (贴图页列表)
"""
import sys, os, json, re, subprocess

CPYRIGHT_RE = re.compile(r'(ISBN|出版社|出版发行|印数|定价|版次|第1版|责任编辑|封面设计|登记证号|开本|印刷)')

def detect_pages(sl, co=None, max_scan=8):
    """设计页候选检测(F31): 连续前缀逐页判定。
    设计页特征(OCR 数据驱动): 行宽中位 < 0.5×页宽 且 (行数<12 或 行首x标准差>6%页宽 或 字号变异>2.5×中位)。
    遇第一个非设计页停止(设计页总是书前连续区: 封面/封底/扉页/版权/名单)。
    可选 co=coords 精判; 无 co 时回退版权特征词(旧逻辑)。"""
    import statistics
    keys = sorted(sl.keys(), key=int)
    if co is None:
        # 回退: 旧版权特征词逻辑(不推荐, 无 coords 时用)
        hit = -1
        for pk in range(min(max_scan, len(sl))):
            text = "".join(sl.get(str(pk), []))
            if CPYRIGHT_RE.search(text):
                hit = pk
        if hit < 0:
            hit = min(2, len(sl) - 1)
        return list(range(hit + 1))
    cands = []
    for k in keys[:max_scan]:
        txts = sl.get(k, []); polys = co.get(k, [])
        lines = [(t.strip(), p) for t, p in zip(txts, polys) if t.strip() and p and isinstance(p, list)]
        if not lines:
            cands.append(int(k)); continue
        try:
            page_w = max(max(pp[0] for pp in p) for _, p in lines)
        except Exception:
            cands.append(int(k)); continue
        ws = [max(pp[0] for pp in p) - min(pp[0] for pp in p) for _, p in lines]
        x0s = [min(pp[0] for pp in p) for _, p in lines]
        hs = [max(pp[1] for pp in p) - min(pp[1] for pp in p) for _, p in lines]
        n = len(lines)
        med_w = statistics.median(ws)
        try: x0_std = statistics.pstdev(x0s)
        except Exception: x0_std = 0
        try: medh = statistics.median(hs)
        except Exception: medh = 1
        reasons = []
        if med_w < 0.5 * page_w: reasons.append('窄行宽%.2f' % (med_w/page_w))
        if n < 12: reasons.append('行少%d' % n)
        if x0_std > 0.06 * page_w: reasons.append('行首散%.2f' % (x0_std/page_w))
        if medh and max(hs) > 2.5 * medh: reasons.append('字号变异')
        hit = (med_w < 0.5 * page_w) and (n < 12 or x0_std > 0.06 * page_w or (medh and max(hs) > 2.5 * medh))
        print('  p%d: 行%d 行宽%.2f 行首散%.2f %s → %s' % (int(k), n, med_w/page_w if page_w else 0, x0_std/page_w if page_w else 0, '; '.join(reasons), '设计页' if hit else '文字页'))
        if hit:
            cands.append(int(k))
        else:
            break
    return cands

def main():
    src_pdf, lines_f = sys.argv[1], sys.argv[2]
    out_dir = "output/page_images"
    pages = None
    dpi = 144
    for a in sys.argv[3:]:
        if a.startswith("--out"): out_dir = a.split("=")[1]
        elif a.startswith("--pages"): pages = [int(x) for x in a.split("=")[1].split(",")]
        elif a.startswith("--dpi"): dpi = int(a.split("=")[1])
    os.makedirs(out_dir, exist_ok=True)

    sl = json.load(open(lines_f))
    if pages is None:
        co = None
        if len(sys.argv) > 3:
            for a in sys.argv[3:]:
                if a.startswith("--coords"):
                    co = json.load(open(a.split("=")[1]))
        pages = detect_pages(sl, co)
        print(f"[自动检测] 设计页候选 → 贴图页 {pages}")

    import fitz
    doc = fitz.open(src_pdf)
    for pk in pages:
        pg = doc[pk]
        scale = 2.0   # 页面实际尺寸 2x, 保证清晰
        pix = pg.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB)
        out = f"{out_dir}/p{pk}.png"
        pix.save(out)
        print(f"  p{pk} → {out} ({pix.width}x{pix.height})")
    doc.close()
    json.dump({"pages": pages, "prefix": os.path.abspath(out_dir) + "/p"},
              open(f"{out_dir}/pages.json", "w"))
    print(f"\n贴图配置: PAGE_IMAGE_PAGES={','.join(map(str, pages))} PAGE_IMAGE_PREFIX={os.path.abspath(out_dir)}/p")

if __name__ == "__main__":
    main()
