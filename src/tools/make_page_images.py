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

def detect_pages(sl, max_scan=10):
    """检测前 max_scan 页中版权特征页; 返回 0 到最后一个特征页的连续页号列表(含封面/扉页)"""
    hit = -1
    for pk in range(min(max_scan, len(sl))):
        text = "".join(sl.get(str(pk), []))
        if CPYRIGHT_RE.search(text):
            hit = pk
    if hit < 0:
        hit = min(2, len(sl) - 1)   # 默认前 3 页(封面/扉页/版权)
    return list(range(hit + 1))

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
        pages = detect_pages(sl)
        print(f"[自动检测] 版权特征页 → 贴图页 {pages}")

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
