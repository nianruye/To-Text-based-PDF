#!/usr/bin/env python3
"""容器内跑: 逐字 score 验证(古字识错检测)。"""
from paddleocr import PaddleOCR
import sys

png = sys.argv[1] if len(sys.argv) > 1 else '/tmp/page.png'
ocr = PaddleOCR(use_angle_cls=False, lang='ch', use_gpu=False)
result = ocr.ocr(png, cls=False)

ancient = '笃寽郛爰骰曶罗梁卖'
print("含古字候选的字(逐字 score):")
for line in result[0]:
    text, line_score, char_scores = line[1]
    for c, s in zip(text, char_scores):
        if c in ancient:
            print(f"  '{c}' score={s:.4f} 行score={line_score:.4f} {text[:30]!r}")

print("\n最低逐字 score 15 字:")
chars = []
for line in result[0]:
    text, _, cs = line[1]
    for c, s in zip(text, cs):
        chars.append((s, c, text[:15]))
for s, c, t in sorted(chars)[:15]:
    print(f"  score={s:.4f} '{c}' 行={t!r}")
