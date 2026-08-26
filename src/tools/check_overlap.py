#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检测输出 PDF 的字符视觉重叠。

背景: build_geom/build_classic 渲染的 PDF 里, 多片段行(frags)按源 x 绝对定位
(\\rlap{\\hspace*{}}), 当渲染字号>源字号时片段宽度超出定位间距 → 字体重叠。
201 项单测与 verify_geom 均不检测此类问题(检测盲区), 本工具补齐。

用法:
    /usr/bin/python3 src/tools/check_overlap.py <out.pdf> [<out.pdf> ...]

输出: 每个 PDF 的跨行(同 y)重叠统计 + 明细。重叠阈值默认 2pt,
CHECK_OVERLAP_MIN 环境变量可调。

口径:
- 同 y(±2pt) 的两个独立 line 的 x 范围重叠 > 阈值 → 报告。
  多片段 rlap 定位的行在 fitz 提取时表现为同 y 多个独立 line。
- 行内 span 重叠(如 \\textcircled 圈套数字的合法视觉设计)不报,
  避免 ⃝ 类 false positive。

退出码: 0=无重叠, 1=有重叠(供 CI/verify 串联)。
"""
import fitz
import os
import sys

MIN_OV = float(os.environ.get('CHECK_OVERLAP_MIN', '2.0'))


def scan(pdf_path):
    d = fitz.open(pdf_path)
    bad = []
    for pi in range(len(d)):
        rows = []
        for b in d[pi].get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            for l in b.get("lines", []):
                txt = "".join(s["text"] for s in l["spans"])
                rows.append((l["bbox"], txt))
        rows.sort(key=lambda r: (round(r[0][1]), r[0][0]))
        for i in range(len(rows)):
            b0, t0 = rows[i]
            for j in range(i + 1, min(i + 6, len(rows))):
                b1, t1 = rows[j]
                if abs(b1[1] - b0[1]) > 2.0:
                    break
                ov = min(b0[2], b1[2]) - max(b0[0], b1[0])
                if ov > MIN_OV:
                    bad.append((pi + 1, round(b0[1]), round(ov, 1),
                                t0[:20], t1[:20],
                                round(b0[0], 1), round(b0[2], 1),
                                round(b1[0], 1), round(b1[2], 1)))
    return bad


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    n_bad = 0
    for path in sys.argv[1:]:
        bad = scan(path)
        n_bad += len(bad)
        print(f"=== {path} ===")
        print(f"同y跨行重叠(>{MIN_OV}pt): {len(bad)} 处")
        for pi, y, ov, t0, t1, x00, x01, x10, x11 in bad[:50]:
            print(f"  p{pi} y={y} 重叠{ov}pt |{t0}||{t1}| x:{x00}-{x01} vs {x10}-{x11}")
        if len(bad) > 50:
            print(f"  ... 共 {len(bad)} 处")
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())
