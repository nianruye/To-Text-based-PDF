#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""几何标定共享模块。从 spotting coords/lines 推导页面尺寸 + 字号/行距。

bit-exact 复制 build_geom/build_classic L19-61 逻辑（两管线逐字符一致）。
返回 dict：PAGE_W/PAGE_H/DPI/cw/MEASURE_POLY/OVERBOUND/MEASURE/FONT/MARGIN/
BASELINE/LINESPREAD/FONT_SM/H_BODY/PUNCT_WEIGHT/USE_REGION/REGION_FONT_SCALE/page_px。
环境变量默认值不变（OVERBOUND=1.115/FONT_SCALE=1.0/PUNCT_WEIGHT=0.2/REGION_FONT_SCALE=1.03）。
"""
import os
import statistics


def calibrate(sl, co, DPI=200):
    """几何标定。sl/co 为 spotting lines/coords（dict）。返回标定结果 dict。"""
    # 页面尺寸从 coords 推导（占位 405,633，coords 覆盖；与 OCR 坐标一致，不从 SRC PDF 读）
    _ymax = max((p[1] for _k in co for _poly in co.get(_k, []) if _poly for p in _poly if len(p) >= 2), default=0)
    _xmax = max((p[0] for _k in co for _poly in co.get(_k, []) if _poly for p in _poly if len(p) >= 2), default=0)
    PAGE_W, PAGE_H = (round(_xmax * 72 / DPI), round(_ymax * 72 / DPI)) if _xmax and _ymax else (405, 633)
    widths, chars, heights = [], [], []
    for key in sl:
        polys = co.get(key, [])
        for i, l in enumerate(sl[key]):
            t = l.strip()
            if len(t) > 8 and i < len(polys) and polys[i]:
                xs = [p[0] for p in polys[i]]; ys = [p[1] for p in polys[i]]
                widths.append(max(xs)-min(xs)); heights.append(max(ys)-min(ys)); chars.append(len(t))
    page_px = PAGE_W * DPI / 72
    maxw = max(widths) if widths else 1
    full = [(w, c) for w, c in zip(widths, chars) if w > 0.80*maxw]
    cw = int(statistics.median([c for w, c in full])) if full else 30
    MEASURE_POLY = round(statistics.median([w for w, c in full]) * 72 / DPI) if full else round(PAGE_W*0.8)
    OVERBOUND = float(os.environ.get('OVERBOUND', '1.115'))
    MEASURE = round(MEASURE_POLY / OVERBOUND)
    FONT = round(MEASURE / cw * float(os.environ.get('FONT_SCALE', '1.0')), 1)
    MARGIN = round((PAGE_W - MEASURE) / 2)
    pitches = []
    for _k in sl:
        _polys = co.get(_k, [])
        _ys = sorted(min(p[1] for p in _polys[i]) for i in range(min(len(_polys), len(sl[_k]))) if _polys[i] and sl[_k][i].strip())
        for a, b in zip(_ys, _ys[1:]):
            if 10 < b - a < 80: pitches.append(b - a)
    BASELINE = round(statistics.median(pitches) * 72 / DPI, 1) if pitches else round(FONT*1.5, 1)
    LINESPREAD = round(BASELINE / (FONT * 1.2), 3)
    FONT_SM = round(FONT * 0.78, 1)
    H_BODY = statistics.median(heights) if heights else 36
    PUNCT_WEIGHT = float(os.environ.get('PUNCT_WEIGHT', '0.2'))
    USE_REGION = os.environ.get('REGION_LAYOUT', '') in ('1', 'true', 'True')
    REGION_FONT_SCALE = float(os.environ.get('REGION_FONT_SCALE', '1.03'))
    return dict(PAGE_W=PAGE_W, PAGE_H=PAGE_H, DPI=DPI, cw=cw, MEASURE_POLY=MEASURE_POLY,
                OVERBOUND=OVERBOUND, MEASURE=MEASURE, FONT=FONT, MARGIN=MARGIN,
                BASELINE=BASELINE, LINESPREAD=LINESPREAD, FONT_SM=FONT_SM, H_BODY=H_BODY,
                PUNCT_WEIGHT=PUNCT_WEIGHT, USE_REGION=USE_REGION,
                REGION_FONT_SCALE=REGION_FONT_SCALE, page_px=page_px)
