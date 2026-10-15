#!/usr/bin/env python3
"""taskO: 源页 vs 产物页 并排对照图。
用法: side_by_side.py <out.pdf> <src.pdf> <out_page_idx> <src_page_idx> <out.png> [scale]"""
import sys
import fitz
import numpy as np
from PIL import Image

out, src, oi, si, dst = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
sc = float(sys.argv[6]) if len(sys.argv) > 6 else 0.5


def render(doc, i, sc):
    p = doc[i]
    pix = p.get_pixmap(matrix=fitz.Matrix(sc, sc), colorspace=fitz.csGRAY)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()


d1 = fitz.open(src); d2 = fitz.open(out)
a = render(d1, si, sc); b = render(d2, oi, sc)
h = max(a.shape[0], b.shape[0]); w = a.shape[1] + b.shape[1] + 20
img = np.full((h, w), 255, dtype=np.uint8)
img[:a.shape[0], :a.shape[1]] = a
img[:b.shape[0], a.shape[1] + 20:a.shape[1] + 20 + b.shape[1]] = b
Image.fromarray(img).save(dst)
print('saved %s (src %dx%d | out %dx%d)' % (dst, a.shape[1], a.shape[0], b.shape[1], b.shape[0]))
