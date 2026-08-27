#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Layout 模式跑一遍, 出精品 Markdown(知识库用)。

与主管线(spotting 行级 → 排版还原 PDF)互补: 本脚本用 layout 版面模式
(useLayoutDetection=True)调 PaddleOCR-VL, VL 做块级标题分类/段落合并/
表格识别/图片URL, 输出结构完整、适合 RAG 知识库分块检索的 Markdown。

用法:
    OCR_LAYOUT=1 /usr/bin/python3 -u src/ocr/run_md_layout.py <in.pdf> <out.md>

产物: <out.md> = 各页 API 原生 markdown 按页拼接, 页间以 --- 分隔。
无排版还原(line/coords), 仅取 markdown 字段。

说明:
- 复用 run_spotting_ocr 的上传/轮询/防限流/切批机制
- 强制 layout 模式(不管 OCR_LAYOUT env), 但 run_spotting_ocr 内部仍存
  lines/coords(块级, 本脚本忽略), 只拿 markdown
"""
import sys, os, json, io

ROOT = '/opt/test'
sys.path.insert(0, os.path.join(ROOT, 'src', 'ocr'))
os.environ['OCR_LAYOUT'] = '1'   # 强制 layout 版面模式
import run_spotting_ocr as r

# 覆盖输入/输出: 用临时 lines 路径(布局块级, 本脚本不用), md 走显式路径
IN_PDF = sys.argv[1]
OUT_MD = sys.argv[2]
r.INPUT_PDF = IN_PDF
r.OUT_LINES = '/tmp/md_layout_lines.json'
r.OUT_COORDS = '/tmp/md_layout_coords.json'

def main():
    lines_data, coords_data, labels_data, markdown_data = r.process_pdf(IN_PDF)
    print(f"[md_layout] {len(markdown_data)} 页 markdown, 拼接 → {OUT_MD}", flush=True)
    parts = []
    for k in sorted(markdown_data.keys(), key=int):
        parts.append(markdown_data[k])
    body = '\n\n---\n\n'.join(parts)
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write(body)
    print(f"[md_layout] 完成: {len(markdown_data)} 页 → {OUT_MD} ({len(body)}字)", flush=True)

if __name__ == '__main__':
    main()
