#!/usr/bin/env python3
"""容器内跑全书 850 页逐字 score。输出 {key: [[poly, text, line_score, char_scores], ...]}"""
from paddleocr import PaddleOCR
import json, os, time

ocr = PaddleOCR(use_angle_cls=False, lang='ch', use_gpu=False)
out = {}
pages_dir = '/tmp/pages'
t0 = time.time()
for i in range(850):
    png = f'{pages_dir}/{i:03d}.png'
    if not os.path.exists(png):
        continue
    try:
        result = ocr.ocr(png, cls=False)
        lines = []
        if result and result[0]:
            for line in result[0]:
                box = line[0]
                text, line_score, char_scores = line[1]
                lines.append([box, text, float(line_score), [float(s) for s in char_scores]])
        out[str(i)] = lines
    except Exception as e:
        out[str(i)] = []
        print(f'  p{i+1} 失败: {e}')
    if (i + 1) % 10 == 0 or i + 1 == 850:
        elapsed = time.time() - t0
        print(f'  {i+1}/850 ({elapsed:.0f}s)')
json.dump(out, open('/opt/test/data/wz3/wz3_char_scores.json', 'w'), ensure_ascii=False)
total = sum(len(v) for v in out.values())
low = sum(1 for v in out.values() for _, _, _, cs in v for s in cs if s < 0.5)
print(f'完成: {len(out)} 页, {total} 行, 低字score(<0.5) {low} 字 -> wz3_char_scores.json')
