#!/usr/bin/env python3
"""Wz4 直传 wrapper: 绕过 needs_png_conversion, 强制走路径A(直接上传PDF)。

复用 run_spotting_ocr.py 的 process_pdf() 直传逻辑(自动切批/轮询/重试/页数校验),
仅 monkeypatch needs_png_conversion -> False, 跳过 JPEG 渲染检查。
用 /usr/bin/python3 -u 运行(实时日志)。
"""
import sys, os, json

sys.path.insert(0, '/opt/test/src/ocr')
import run_spotting_ocr as r

# 绕过 JPEG 检查: 永远走 PDF 直传路径
r.needs_png_conversion = lambda filepath: False

INPUT_PDF  = '/opt/test/source_pdf/wz4.pdf'
OUT_LINES  = '/opt/test/data/wz4/wz4_spotting_lines.json'
OUT_COORDS = '/opt/test/data/wz4/wz4_spotting_coords.json'
OUT_LABELS = '/opt/test/data/wz4/wz4_spotting_labels.json'

print(f"[wz4 direct] Direct PDF upload (skip PNG check): {INPUT_PDF}", flush=True)
lines_data, coords_data, labels_data = r.process_pdf(INPUT_PDF)

total = sum(len(v) for v in lines_data.values())
titles_total = sum(sum(1 for l in v if 'title' in l) for v in labels_data.values())
print(f"[wz4 direct] Total: {len(lines_data)} pages, {total} lines, {titles_total} titles", flush=True)

for path, data in ((OUT_LINES, lines_data), (OUT_COORDS, coords_data), (OUT_LABELS, labels_data)):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[wz4 direct] Saved: {path}", flush=True)

print("[wz4 direct] Done.", flush=True)
