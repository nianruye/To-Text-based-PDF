#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Layout 模式跑一遍, 出精品 Markdown(知识库用) + LAYJSON(标题权威判定)。

与主管线(spotting 行级 → 排版还原 PDF)互补: 本脚本用 layout 版面模式
(useLayoutDetection=True)调 PaddleOCR-VL, VL 做块级标题分类/段落合并/
表格识别/图片URL, 输出结构完整、适合 RAG 知识库分块检索的 Markdown。

用法:
    OCR_LAYOUT=1 /usr/bin/python3 -u src/ocr/run_md_layout.py <in.pdf> <out.md> [out_layjson.json]

产物:
- <out.md>: 各页 API 原生 markdown 按页拼接, 页间 --- 分隔
- <out_layjson.json>(可选): LAYJSON 格式(每页 prunedResult.parsing_res_list),
  供 build_geom LAYOUT_HEADINGS=1 标题权威判定(VL doc_title/paragraph_title 标签)

说明:
- 复用 run_spotting_ocr 的上传/轮询/防限流/切批机制
- 强制 layout 模式(不管 OCR_LAYOUT env), 但 run_spotting_ocr 内部仍存
  lines/coords(块级, 本脚本忽略), 只拿 markdown + prunedResult
"""
import sys, os, json

ROOT = '/opt/test'
sys.path.insert(0, os.path.join(ROOT, 'src', 'ocr'))
os.environ['OCR_LAYOUT'] = '1'   # 强制 layout 版面模式
import run_spotting_ocr as r

IN_PDF = sys.argv[1]
OUT_MD = sys.argv[2]
OUT_LAYJSON = sys.argv[3] if len(sys.argv) > 3 else ''
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
    # LAYJSON: 按页序 list, 每元素 = {"prunedResult": {...}} (与 wz1 旧 LAYJSON / build_geom
    # enumerate(_ld) 契约一致: _pg.get('prunedResult',{}).get('parsing_res_list') 取块级标签)
    if OUT_LAYJSON:
        _lay = [{"prunedResult": r._PAGE_RAW[str(i)]} for i in range(len(r._PAGE_RAW))]
        with open(OUT_LAYJSON, 'w', encoding='utf-8') as f:
            json.dump(_lay, f, ensure_ascii=False)
        print(f"[md_layout] LAYJSON: {len(_lay)} 页 → {OUT_LAYJSON}", flush=True)


if __name__ == '__main__':
    main()
