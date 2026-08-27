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


def calibrate(sl, co, DPI=200, src_pdf=''):
    """几何标定。sl/co 为 spotting lines/coords（dict）。返回标定结果 dict。

    DPI 自适应: coords 实际尺度随 API 批次漂移(实测 200dpi 与 ~142dpi 两档),
    用 coords P95 y 与 src_pdf 实际页高反推真实 DPI, 修正绝对尺寸
    (字宽/缩进/行距 0.71 倍偏小问题, 用户可见的"缩进没还原"根因)。

    src_pdf 提供时按文字覆盖率自适应选页尺寸来源:
    - 覆盖率 >= PAGE_COVERAGE_THRESHOLD(默认0.95): 用 coords 推导(与 OCR 坐标一致,原行为)
    - 覆盖率 < 阈值(大边距书,如 wz4 文字仅覆盖72% → coords 推导页框偏小28% → 溢出翻倍):
      用 src_pdf 实际页尺寸(多页中位,防首页特殊)。
    行距(BASELINE)仍只依赖 coords 行 y 间距统计,不随页框缩放。
    """
    # src_pdf 先行读取(DPI 自适应 + 页尺寸自适应共用)
    _aw = _ah = None
    if src_pdf:
        import fitz
        try:
            doc = fitz.open(src_pdf)
            n = doc.page_count
            idxs = list(range(0, n, max(1, n // 10)))
            _aw = statistics.median(doc[i].rect.width for i in idxs)
            _ah = statistics.median(doc[i].rect.height for i in idxs)
            doc.close()
        except Exception as e:
            print(f"[页尺寸] src_pdf 读取失败({e})", flush=True)
    # DPI 自适应: P95 y(抗页码/噪声) 反推真实 dpi
    _all_y = [p[1] for _k in co for _poly in co.get(_k, []) if _poly for p in _poly if len(p) >= 2]
    if _all_y and _ah:
        _ymax95 = sorted(_all_y)[int(len(_all_y) * 0.95)]
        _dpi_r = round(_ymax95 * 72 / _ah)
        if abs(_dpi_r - DPI) > 5:
            print(f"[DPI] 自适应 {DPI}→{_dpi_r} (coords P95 y={_ymax95}px / 页高{_ah:.0f}pt)", flush=True)
            DPI = _dpi_r
    # 页面尺寸从 coords 推导（占位 405,633，coords 覆盖；与 OCR 坐标一致）
    _ymax = max((p[1] for _k in co for _poly in co.get(_k, []) if _poly for p in _poly if len(p) >= 2), default=0)
    _xmax = max((p[0] for _k in co for _poly in co.get(_k, []) if _poly for p in _poly if len(p) >= 2), default=0)
    PAGE_W, PAGE_H = (round(_xmax * 72 / DPI), round(_ymax * 72 / DPI)) if _xmax and _ymax else (405, 633)
    # 自适应: 大边距书用实际页尺寸
    if src_pdf and _aw:
        try:
            coverage = PAGE_W / _aw if _aw > 0 else 1.0
            thresh = float(os.environ.get('PAGE_COVERAGE_THRESHOLD', '0.95'))
            if coverage < thresh:
                print(f"[页尺寸] 来源=src_pdf(覆盖率{coverage:.0%}<{thresh:.0%}), 实际{_aw:.0f}x{_ah:.0f}pt 替代 coords 推导{PAGE_W}x{PAGE_H}pt", flush=True)
                PAGE_W, PAGE_H = round(_aw), round(_ah)
            else:
                print(f"[页尺寸] 来源=coords(覆盖率{coverage:.0%}>={thresh:.0%}), {PAGE_W}x{PAGE_H}pt(实际{_aw:.0f}x{_ah:.0f}pt)", flush=True)
        except Exception as e:
            print(f"[页尺寸] 自适应失败({e}), 回退 coords 推导 {PAGE_W}x{PAGE_H}pt", flush=True)
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
