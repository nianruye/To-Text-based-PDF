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
    _DPI0 = DPI
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
    # DPI 自适应: max y(页底, 分位法 P95/P99 落在版心底系统性偏低) 反推真实 dpi。
    # 保护: 剔除 >页高×1.15 的噪声 poly(OCR 偶发越界)后取最大。
    _all_y = [p[1] for _k in co for _poly in co.get(_k, []) if _poly for p in _poly if len(p) >= 2]
    _dpi_residual = None
    if _all_y and _ah:
        _cap = _ah * 1.15 * DPI / 72   # 噪声上限(该 DPI 假设下页高 1.15 倍)
        _ymax_c = max((y for y in _all_y if y <= _cap), default=max(_all_y))
        _dpi_r = round(_ymax_c * 72 / _ah)
        if abs(_dpi_r - DPI) > 5:
            print(f"[DPI] 自适应 {DPI}→{_dpi_r} (coords max y={_ymax_c}px / 页高{_ah:.0f}pt)", flush=True)
            DPI = _dpi_r
        _dpi_residual = abs(DPI - _ymax_c * 72 / _ah)
    # 页面尺寸从 coords 推导（占位 405,633，coords 覆盖；与 OCR 坐标一致）
    _ymax = max((p[1] for _k in co for _poly in co.get(_k, []) if _poly for p in _poly if len(p) >= 2), default=0)
    _xmax = max((p[0] for _k in co for _poly in co.get(_k, []) if _poly for p in _poly if len(p) >= 2), default=0)
    _coords_w, _coords_h = (round(_xmax * 72 / DPI), round(_ymax * 72 / DPI)) if _xmax and _ymax else (405, 633)
    PAGE_W, PAGE_H = _coords_w, _coords_h
    _coverage_x = _coverage_y = None
    _coverage_threshold = float(os.environ.get('PAGE_COVERAGE_THRESHOLD', '0.95'))
    _src_w = _src_h = None
    _source_page = 'coords_no_src' if not (src_pdf and _aw) else 'coords'
    _coverage_degraded = not bool(src_pdf and _aw)
    # 自适应: 大边距书用实际页尺寸
    if src_pdf and _aw:
        try:
            coverage = PAGE_W / _aw if _aw > 0 else 1.0
            thresh = _coverage_threshold
            _src_w, _src_h = round(_aw), round(_ah)
            _coverage_x = round(coverage, 4)
            _coverage_y = round(PAGE_H / _ah, 4) if _ah else None
            if coverage < thresh:
                print(f"[页尺寸] 来源=src_pdf(覆盖率{coverage:.0%}<{thresh:.0%}), 实际{_aw:.0f}x{_ah:.0f}pt 替代 coords 推导{PAGE_W}x{PAGE_H}pt", flush=True)
                PAGE_W, PAGE_H = round(_aw), round(_ah)
                _source_page = 'src_pdf'; _coverage_degraded = True
            else:
                print(f"[页尺寸] 来源=coords(覆盖率{coverage:.0%}>={thresh:.0%}), {PAGE_W}x{PAGE_H}pt(实际{_aw:.0f}x{_ah:.0f}pt)", flush=True)
                _source_page = 'coords'; _coverage_degraded = False
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
    _pitch_med = statistics.median(pitches) * 72 / DPI if pitches else None
    BASELINE = round(_pitch_med, 1) if _pitch_med is not None else round(FONT*1.5, 1)
    LINESPREAD = round(BASELINE / (FONT * 1.2), 3)
    FONT_SM = round(FONT * 0.78, 1)
    H_BODY = statistics.median(heights) if heights else 36
    PUNCT_WEIGHT = float(os.environ.get('PUNCT_WEIGHT', '0.2'))
    USE_REGION = os.environ.get('REGION_LAYOUT', '') in ('1', 'true', 'True')
    REGION_FONT_SCALE = float(os.environ.get('REGION_FONT_SCALE', '1.03'))
    _full_n = len(full)
    _eligible = len(widths)
    return dict(PAGE_W=PAGE_W, PAGE_H=PAGE_H, DPI=DPI, cw=cw, MEASURE_POLY=MEASURE_POLY,
                OVERBOUND=OVERBOUND, MEASURE=MEASURE, FONT=FONT, MARGIN=MARGIN,
                BASELINE=BASELINE, LINESPREAD=LINESPREAD, FONT_SM=FONT_SM, H_BODY=H_BODY,
                PUNCT_WEIGHT=PUNCT_WEIGHT, USE_REGION=USE_REGION,
                REGION_FONT_SCALE=REGION_FONT_SCALE, page_px=page_px,
                dpi_initial=_DPI0, dpi_residual=_dpi_residual,
                dpi_source=('coords+src' if (src_pdf and _ah) else 'default'),
                coords_width_pt=_coords_w, coords_height_pt=_coords_h,
                src_width_pt=_src_w, src_height_pt=_src_h,
                coverage_x=_coverage_x, coverage_y=_coverage_y,
                coverage_threshold=_coverage_threshold,
                coverage_degraded=bool(_coverage_degraded),
                source_of_page_size=_source_page,
                cw_sample_n=_full_n, cw_source='coords',
                full_lines=_full_n, full_ratio=round(_full_n / _eligible, 3) if _eligible else 0.0,
                font_scale=float(os.environ.get('FONT_SCALE', '1.0')),
                font_source=('env' if os.environ.get('FONT_SCALE') else 'formula'),
                baseline_source=('coords' if pitches else 'fallback'),
                pitch_sample_n=len(pitches), pitch_median_pt=round(_pitch_med, 3) if _pitch_med is not None else None)


# ── 横排标定审计（HORIZONTAL_CALIB.md v1） ─────────────────────────────
def _sha256(path):
    import hashlib
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def build_calib_doc(sl, co, g, src_pdf, book):
    """按 spec HORIZONTAL_CALIB §4 组装 <book>.calib.json（不含 TOC，由 build_geom 补）。"""
    pages = len(sl)
    dpi = int(g.get('DPI') or 200)
    doc = {
        'schema_version': 'horizontal-calib-v1',
        'status': 'measured',
        'book': str(book),
        'src_pdf': src_pdf or '',
        'sha256': _sha256(src_pdf) if src_pdf and os.path.exists(src_pdf) else None,
        'pages': pages,
        'dpi': {
            'value': dpi,
            'source': g.get('dpi_source', 'default'),
            'residual': g.get('dpi_residual'),
            'expected': None,
        },
        'page_size': {
            'width_pt': g.get('PAGE_W'),
            'height_pt': g.get('PAGE_H'),
            'source': g.get('source_of_page_size', 'fallback'),
            'unit': 'bp',
            'coords_width_pt': g.get('coords_width_pt'),
            'coords_height_pt': g.get('coords_height_pt'),
            'src_width_pt': g.get('src_width_pt'),
            'src_height_pt': g.get('src_height_pt'),
        },
        'cw': g.get('cw'),
        'measure': {
            'poly_pt': g.get('MEASURE_POLY'),
            'pt': g.get('MEASURE'),
            'overbound': g.get('OVERBOUND'),
        },
        'font': {
            'pt': g.get('FONT'),
            'scale': g.get('font_scale', 1.0),
            'source': g.get('font_source', 'formula'),
        },
        'baseline': {
            'pt': g.get('BASELINE'),
            'font_ratio': round(g['BASELINE'] / g['FONT'], 3) if g.get('FONT') else None,
            'linespread': g.get('LINESPREAD'),
            'source': g.get('baseline_source', 'coords'),
        },
        'margin_pt': g.get('MARGIN'),
        'font_sm_pt': g.get('FONT_SM'),
        'h_body_px': g.get('H_BODY'),
        'toc_params': {'font_line': None, 'foot_x': None, 'title_max': None,
                       'toc_pages': [], 'source': 'none'},
        'coverage': {
            'x_ratio': g.get('coverage_x'),
            'y_ratio': g.get('coverage_y'),
            'threshold': g.get('coverage_threshold'),
            'degraded': bool(g.get('coverage_degraded')),
            'full_lines': g.get('full_lines'),
            'full_ratio': g.get('full_ratio'),
            'pitch_samples': g.get('pitch_sample_n'),
            'toc_samples': 0,
        },
        'source_of_page_size': g.get('source_of_page_size', 'fallback'),
        'warnings': [],
        'selfcheck': {},
        'env': {
            'PAGE_COVERAGE_THRESHOLD': os.environ.get('PAGE_COVERAGE_THRESHOLD', '0.95'),
            'OVERBOUND': os.environ.get('OVERBOUND', '1.115'),
            'FONT_SCALE': os.environ.get('FONT_SCALE', '1.0'),
            'HORIZ_CALIB_STRICT': os.environ.get('HORIZ_CALIB_STRICT', ''),
        },
        'created_by': 'horizontal-calib-v1',
    }
    selfcheck, warnings = calib_selfcheck(doc, g, sl, co)
    doc['selfcheck'] = selfcheck
    doc['warnings'] = warnings
    return doc


def calib_selfcheck(doc, g, sl, co):
    """spec §3 自检。返回 (selfcheck, warnings[{code,severity,detail,source}])。默认 warn 不阻断。"""
    w = []

    def add(code, sev, detail, source='calibrate'):
        w.append(dict(code=code, severity=sev, detail=detail, source=source))

    pages = len(sl)   # 以实际输入为准（doc['pages'] 是生成时的快照）
    src_pages = None
    if doc.get('src_pdf') and os.path.exists(doc['src_pdf']):
        try:
            import fitz
            d = fitz.open(doc['src_pdf']); src_pages = d.page_count; d.close()
        except Exception:
            src_pages = None
    n_co = len(co)
    pages_1to1 = (pages == n_co)
    if pages != n_co:
        add('pages_mismatch', 'fail', 'sl=%d co=%d' % (pages, n_co))
    elif src_pages is not None and pages != src_pages:
        # 页子集构建（--pages）时 src_pdf 仍是全本：只提示，不判失败
        add('src_pages_diff', 'warn', 'sl=%d src=%d（页子集/切片）' % (pages, src_pages))
    if pages == 0 or not any((p for v in co.values() for p in v)):
        add('empty_input', 'fail', 'coords/lines 为空')

    dpi_res = g.get('dpi_residual')
    if dpi_res is not None and abs(float(dpi_res)) > 5:
        add('dpi_residual_large', 'warn', 'residual=%.1f > 5' % float(dpi_res), 'dpi')
    font = g.get('FONT')
    font_ok = font is not None and 6 <= float(font) <= 20
    if not font_ok:
        add('font_out_of_range', 'warn', 'font=%s ∉ [6,20]' % font, 'font')
    ratio = (float(g['BASELINE']) / float(g['FONT'])) if g.get('FONT') and g.get('BASELINE') is not None else None
    ratio_ok = ratio is not None and 1.2 <= ratio <= 2.0
    if not ratio_ok:
        add('baseline_font_ratio_out', 'warn', 'baseline/font=%s ∉ [1.2,2.0]' % (round(ratio, 3) if ratio else None), 'baseline')
    if (g.get('pitch_sample_n') or 0) < 10:
        add('pitch_low_sample', 'warn', 'pitch_samples=%s < 10' % g.get('pitch_sample_n'), 'baseline')
    if (g.get('full_lines') or 0) < 5:
        add('full_sample_low', 'warn', 'full_lines=%s < 5' % g.get('full_lines'), 'cw')
    if not (1 <= (g.get('cw') or 0) <= 100) or (g.get('cw') or 0) < 5 or (g.get('cw') or 0) > 80:
        add('cw_out_of_range', 'warn', 'cw=%s' % g.get('cw'), 'cw')
    W = float(g.get('PAGE_W') or 0); M = float(g.get('MEASURE') or 0)
    if not (0.5 * W <= M <= 0.95 * W):
        add('measure_out_of_range', 'warn', 'measure=%s page_w=%s' % (M, W), 'measure')
    if not (0 <= float(g.get('MARGIN') or 0) <= 0.3 * W):
        add('margin_out_of_range', 'warn', 'margin=%s page_w=%s' % (g.get('MARGIN'), W), 'margin')
    cov_x = g.get('coverage_x'); cov_y = g.get('coverage_y')
    if cov_x is not None and (float(cov_x) > 1.02 or (cov_y is not None and float(cov_y) > 1.02)):
        add('page_size_overcoverage', 'warn', 'coverage_x=%s coverage_y=%s' % (cov_x, cov_y), 'page_size')
    if g.get('coverage_degraded'):
        add('page_size_coverage_low', 'warn', 'coverage_x=%s source=%s' % (cov_x, g.get('source_of_page_size')), 'page_size')
    if doc.get('source_of_page_size') not in ('coords', 'src_pdf', 'fallback', 'coords_no_src'):
        add('source_of_page_size_missing', 'fail', 'source=%s' % doc.get('source_of_page_size'), 'page_size')
    # pitch 自洽（标定阶段样本中位 vs BASELINE；verify_geom 再独立复核）
    pitch_med = g.get('pitch_median_pt')
    pitch_err = None
    if pitch_med and g.get('BASELINE'):
        pitch_err = abs(float(g['BASELINE']) - float(pitch_med)) / float(pitch_med) * 100.0
        if pitch_err >= 3.0:
            add('pitch_error_large', 'warn', 'pitch_error=%.2f%%' % pitch_err, 'baseline')
    # TOC 参数（build_geom 补写后调用时可校验；此处如已填）
    toc = doc.get('toc_params') or {}
    toc_samples = ((doc.get('coverage') or {}).get('toc_samples') or 0)
    if toc_samples < 3:
        add('toc_low_sample', 'warn', 'toc_samples=%s < 3' % toc_samples, 'toc')
    toc_ok = None
    if toc.get('font_line') is not None and font:
        toc_ok = 0.9 * float(font) <= float(toc['font_line']) <= 1.8 * float(font)
        if not toc_ok:
            add('toc_font_line_out', 'warn', 'font_line=%s font=%s' % (toc['font_line'], font), 'toc')
    fx = toc.get('foot_x')
    if fx is not None:
        try:
            fx_ok = (len(fx) == 2 and 0.0 <= float(fx[0]) < float(fx[1]) <= 1.0)
        except Exception:
            fx_ok = False
        if not fx_ok:
            add('toc_foot_x_out', 'warn', 'foot_x=%s ∉ [0,1] 桶对' % (fx,), 'toc')
    tm = toc.get('title_max')
    if tm is not None and not (10 <= int(tm) <= 80):
        add('toc_title_max_out', 'warn', 'title_max=%s ∉ [10,80]' % tm, 'toc')
    sev = [x['severity'] for x in w]
    selfcheck = {
        'pages_1to1': bool(pages_1to1),
        'pitch_error_pct': round(pitch_err, 3) if pitch_err is not None else None,
        'dpi_residual': dpi_res,
        'font_in_range': bool(font_ok),
        'baseline_font_ratio': round(ratio, 3) if ratio is not None else None,
        'coverage_degraded': bool(g.get('coverage_degraded')),
        'toc_in_range': toc_ok,
        'verdict': 'fail' if 'fail' in sev else ('warn' if w else 'pass'),
    }
    return selfcheck, w


def write_calib(path, doc):
    import json as _json
    _json.dump(doc, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return path


def product_render(pdf_path):
    """从产物 PDF 回填渲染参数（单位 PDF bp）：page_pt/font_pt/pitch_pt/pass。"""
    import fitz, statistics
    out = {'page_pt': {'width_pt': None, 'height_pt': None},
           'font_pt': None, 'pitch_pt': None, 'pass': None, 'unit': 'bp'}
    try:
        d = fitz.open(pdf_path)
    except Exception:
        return out
    if len(d) == 0:
        d.close(); return out
    idx = list(range(0, len(d), max(1, len(d) // 10)))
    out['page_pt']['width_pt'] = round(statistics.median(d[i].rect.width for i in idx), 2)
    out['page_pt']['height_pt'] = round(statistics.median(d[i].rect.height for i in idx), 2)
    sizes, pitches = [], []
    for i in idx:
        lines = []
        for b in d[i].get_text('dict').get('blocks', []):
            for l in b.get('lines', []):
                if l.get('spans'):
                    sizes += [s.get('size', 0) for s in l['spans']]
                    lines.append(l['bbox'][1])
        lines.sort()
        pitches += [b - a for a, b in zip(lines, lines[1:]) if 4 < b - a < 120]
    d.close()
    if sizes:
        out['font_pt'] = round(statistics.median(sizes), 2)
    if pitches:
        out['pitch_pt'] = round(statistics.median(pitches), 2)
    return out


def update_calib_render(path, pdf_path, pass_=None, pitch_error_pct=None):
    """build_geom/scan2pdf 回填 render；pass/pitch_error_pct 由 verify_geom 侧给。"""
    import json as _json
    try:
        doc = _json.load(open(path, encoding='utf-8'))
    except Exception:
        return None
    r = product_render(pdf_path)
    if pass_ is not None:
        r['pass'] = bool(pass_)
    if pitch_error_pct is not None:
        doc.setdefault('selfcheck', {})['pitch_error_pct'] = round(float(pitch_error_pct), 3)
        doc['selfcheck']['pitch_error_source'] = 'verify_geom'
    doc['render'] = r
    _json.dump(doc, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return doc
