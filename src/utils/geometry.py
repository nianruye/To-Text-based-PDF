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
    # x 方向与上方 y 的 1.15 噪声保护对齐：单个离群 poly 会把页宽放大
    # （wz3 实测 x_max=2427 而 p99.9=1555 → 874pt vs 真实 595pt，+47%；AGENTS #66）
    _ymax = max((p[1] for _k in co for _poly in co.get(_k, []) if _poly for p in _poly if len(p) >= 2), default=0)
    _all_x = [p[0] for _k in co for _poly in co.get(_k, []) if _poly for p in _poly if len(p) >= 2]
    if _aw and _all_x:
        _capx = _aw * 1.15 * DPI / 72          # 与 y 同口径：页宽 1.15 倍以上的视为噪声
        _kept = [x for x in _all_x if x <= _capx]
        if len(_kept) < len(_all_x):
            print(f"[页尺寸] 剔除 x 离群点 {len(_all_x) - len(_kept)} 个 (>{_capx:.0f}px, 页宽{_aw:.0f}pt×1.15)",
                  flush=True)
        _xmax = max(_kept, default=max(_all_x))
    else:
        _xmax = max(_all_x, default=0)
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
            if coverage < thresh or coverage > 1.0 / thresh:
                # 双向退化：推导偏小 OR 偏大都用 src_pdf 实际页尺寸（AGENTS #66）
                # 注意 _source_page 必须保持 'src_pdf'（枚举白名单，见 L418 与 test_horizontal_calib）
                _dir = '偏小' if coverage < thresh else '偏大'
                print(f"[页尺寸] 来源=src_pdf({_dir}, 覆盖率{coverage:.2f} 越界"
                      f"[{thresh:.2f},{1.0/thresh:.2f}]), 实际{_aw:.0f}x{_ah:.0f}pt 替代 coords 推导{PAGE_W}x{PAGE_H}pt", flush=True)
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
    _full_n = len(full)
    _eligible = len(widths)
    _full_ratio = round(_full_n / _eligible, 4) if _eligible else 0.0
    _fb_thresh = float(os.environ.get('HORIZ_FALLBACK_RATIO', '0'))
    OVERBOUND = float(os.environ.get('OVERBOUND', '1.115'))
    # 低 full_ratio 兜底（S4/A1）：满行样本 <10% 时，maxw/中位满行估计不稳（ghbq 50/1770=2.8%）。
    # 用全部合格行的 P90 行宽 + 行字数中位；MEASURE 取实测行宽（不再除 OVERBOUND），
    # 避免旧公式把版心压窄 1.115 倍导致二次换行。高 full_ratio 走原公式（零变化）。
    _estimator = 'full_line'
    _ov_book = None
    # COLW_RATIO 默认关: 仅当本书的坐标尺度可信时才用「按书 OCR/ink 比值」。
    # wz8 实测坐标过覆盖 2.8%(612 vs 源书 595), 固定 1.115 恰好抵消该错误;
    # 换成按书比值后 MEASURE 552 vs 525 → 断行全变 → pitch 96.3→60.6。
    # 现改为按书选项 config/books/<book>.json 的 colw_ratio 启用（AGENTS #57）。
    if src_pdf and os.environ.get('COLW_RATIO', '0') not in ('0','false','False'):
        try:
            import fitz as _fz
            _doc = _fz.open(src_pdf); _rats = []
            for _k in list(sl)[:80]:
                _polys = co.get(_k, []); _pi = int(_k)
                if _pi >= _doc.page_count: continue
                _pix = _doc[_pi].get_pixmap(dpi=150); _W,_H=_pix.width,_pix.height; _im=_pix.samples; _nc=_pix.n
                _sc=150.0/DPI; _mw=max([max(q[0] for q in _pp)-min(q[0] for q in _pp) for _pp in _polys if _pp] or [1])
                for _i,_poly in enumerate(_polys):
                    if not _poly or _i >= len(sl[_k]) or len(sl[_k][_i].strip()) < 10: continue
                    _xs=[q[0] for q in _poly]; _ys=[q[1] for q in _poly]; _pw=max(_xs)-min(_xs)
                    if _pw < 0.8*_mw: continue
                    _ax=max(0,int((min(_xs)-20/(72.0/DPI))*_sc)); _bx=min(_W,int((max(_xs)+20/(72.0/DPI))*_sc)); _ay=max(0,int(min(_ys)*_sc)); _by=min(_H,int(max(_ys)*_sc)); _mn=_mx=None
                    for _yy in range(_ay,_by):
                        _row=_yy*_W*_nc
                        for _xx in range(_ax,_bx):
                            _ii=_row+_xx*_nc
                            if _im[_ii]<170 or _im[_ii+1]<170 or _im[_ii+2]<170:
                                _mn=_xx if _mn is None else min(_mn,_xx); _mx=_xx if _mx is None else max(_mx,_xx)
                    if _mn is not None and _mx is not None and _mx>_mn:
                        _iw=(_mx-_mn)/150.0*72
                        if _iw>1: _rats.append((_pw*72.0/DPI)/_iw)
            if len(_rats) >= 50:
                _ov_book = round(statistics.median(_rats), 4)
                print(f"[标定·overbound] {len(_rats)} 条 OCR/ink 中位 {_ov_book}", flush=True)
            else:
                print(f"[标定·overbound] 样本不足({len(_rats)}) 回退 1.115", flush=True)
        except Exception as _oe:
            print(f"[标定·overbound] 失败 {_oe} 回退 1.115", flush=True)
    _fb = None
    if _eligible and _full_ratio < _fb_thresh:
        _sw = sorted(widths)
        _w90 = _sw[min(len(_sw)-1, int(round(0.9 * (len(_sw)-1))))]   # P90 行宽(px)
        _cmed = int(round(statistics.median(chars)))
        cw = _cmed if _cmed > 0 else 30
        MEASURE_POLY = round(_w90 * 72 / DPI)
        MEASURE = MEASURE_POLY
        _estimator = 'fallback'
        _fb = dict(threshold=_fb_thresh, sample_n=_eligible, width_px=round(_w90,1),
                   width_pt=MEASURE_POLY, char_median=_cmed)
        print(f"[标定·fallback] full_ratio={_full_ratio:.3f}<{_fb_thresh:.2f} → "
              f"cw={cw} measure={MEASURE}pt (P90行宽{_w90:.1f}px, 行数{_eligible})", flush=True)
    else:
        cw = int(statistics.median([c for w, c in full])) if full else 30
        MEASURE_POLY = round(statistics.median([w for w, c in full]) * 72 / DPI) if full else round(PAGE_W*0.8)
        MEASURE = round(MEASURE_POLY / (_ov_book or OVERBOUND))
    # 显式覆盖优先（HORIZ_CW 字数；HORIZ_FONT_MEASURE 字号 pt）。
    _cw_env = os.environ.get('HORIZ_CW', '').strip()
    if _cw_env:
        try:
            _cw_v = int(float(_cw_env))
            if _cw_v > 0: cw = _cw_v
        except ValueError:
            pass
    FONT = round(MEASURE / cw * float(os.environ.get('FONT_SCALE', '1.0')), 1)
    _font_env = os.environ.get('HORIZ_FONT_MEASURE', '').strip()
    if _font_env:
        try:
            _fv = float(_font_env)
            if _fv > 0: FONT = round(_fv, 1)
        except ValueError:
            pass
    # S4-R2: fallback 字号与墨高交叉验证（poly 高度中位 / 0.88）。
    _ink_font = round(statistics.median(heights) * 72.0 / DPI / 0.88, 1) if heights else None
    _ink_applied = False
    _ink_reject = None
    if (_estimator == 'fallback' and _ink_font
        and not os.environ.get('HORIZ_FONT_MEASURE') and not os.environ.get('HORIZ_CW')
        and os.environ.get('HORIZ_INK_CALIB', '0') not in ('0', 'false', 'False')):
        if abs(FONT - _ink_font) / max(_ink_font, 0.1) > 0.20:
            if 6.0 <= _ink_font <= 20.0:
                print(f"[标定·ink] fallback font={FONT} vs ink={_ink_font} (>20%) -> 用 ink", flush=True)
                FONT = _ink_font
                _ink_applied = True
            else:
                # 无收益/越界：ink 估计落在 FONT 合理区间外（ghbq ink=23.5），保留 fallback 并记录
                print(f"[标定·ink] fallback font={FONT} vs ink={_ink_font} (>20%) 但 ink∉[6,20] -> 保留 fallback", flush=True)
                _ink_reject = 'out_of_range'
    MARGIN = max(12.0, round((PAGE_W - MEASURE) / 2))   # 下限保护: 页宽异常时防负值/巨型 margin
    pitches = []
    for _k in sl:
        _polys = co.get(_k, [])
        _ys = sorted(min(p[1] for p in _polys[i]) for i in range(min(len(_polys), len(sl[_k]))) if _polys[i] and sl[_k][i].strip())
        for a, b in zip(_ys, _ys[1:]):
            if 10 < b - a < 80: pitches.append(b - a)
    _pitch_med = statistics.median(pitches) * 72 / DPI if pitches else None
    # PITCH_MEASURE（AGENTS #67）：coords 行距系统性偏大（wz3 +6.8% / wz2 +7.7% / ghbq +3.0% / wz1 +2.8%，
    # 由「源图水平投影行带中心距」与「墨迹行带」两份独立证据确认）。
    # 行框 padding 上下抵消、行高/字号比也不随书稳定 → 唯一可靠做法是**直接量源图**。
    # 抽样 8 页（正文页），用水平投影找行带、算相邻中心距中位；与 coords 行距的比值即修正系数。
    _pitch_ratio_out = 1.0   # 只用于 BASELINE；page_pitch 从 BASELINE 派生（防双重修正）
    if _pitch_med is not None and src_pdf and os.environ.get('PITCH_MEASURE', '1') not in ('0', 'false', 'False'):
        try:
            import fitz as _fz
            import numpy as _np
            _doc = _fz.open(src_pdf)
            # 取中部正文页（跳过封面/目录/前后附）
            _n = _doc.page_count
            _cand = [int(_n * f) for f in (0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60)]
            _mds = []
            for _pi in _cand:
                if _pi >= _n:
                    continue
                _pix = _doc[_pi].get_pixmap(dpi=150)
                _arr = _np.frombuffer(_pix.samples, dtype=_np.uint8).reshape(_pix.height, _pix.width, _pix.n)
                _bw = _arr[:, :, :3].mean(axis=2) < 128
                _proj = _bw.sum(axis=1)
                _thr = max(2, 0.004 * _bw.shape[1])
                _bands = []
                _in = False
                for _y, _v in enumerate(_proj):
                    if _v > _thr and not _in:
                        _st = _y; _in = True
                    elif _v <= _thr and _in:
                        if _y - _st >= 4:
                            _bands.append((_st, _y))
                        _in = False
                _mg = []
                for _a, _b2 in _bands:
                    if _mg and _a - _mg[-1][1] <= 3:
                        _mg[-1] = (_mg[-1][0], _b2)
                    else:
                        _mg.append((_a, _b2))
                _cs = [(_a + _b2) / 2 * 72.0 / 150 for _a, _b2 in _mg]
                _d = [_b2 - _a for _a, _b2 in zip(_cs, _cs[1:]) if 10 < _b2 - _a < 80]
                if len(_d) >= 8:
                    _mds.append(statistics.median(_d))
            _doc.close()
            if len(_mds) >= 3:
                _pitch_scan = statistics.median(_mds)
                _pr = _pitch_med / _pitch_scan if _pitch_scan > 0 else 1.0
                # 只在偏差 2%~20% 区间内修正（超出多为量测失败/异常书，保守不动）
                if 1.02 <= _pr <= 1.20:
                    print(f"[标定·行距] 源图投影实测 {_pitch_scan:.2f}pt vs coords {_pitch_med:.2f}pt"
                          f" → 修正 ÷{_pr:.3f} ({len(_mds)} 页)", flush=True)
                    _pitch_source = 'src_scan'
                    _pitch_ratio_out = _pr   # 只用于 page_pitch（正文）；BASELINE 保持 coords 原值
                else:
                    print(f"[标定·行距] 源图 {_pitch_scan:.2f} vs coords {_pitch_med:.2f}"
                          f" → 比值 {_pr:.3f} 超出 [1.02,1.20], 不修正", flush=True)
                    _pitch_source = 'coords'
            else:
                _pitch_source = 'coords'
        except Exception as _pe:
            print(f"[标定·行距] 源图量测失败({_pe}), 用 coords 口径", flush=True)
            _pitch_source = 'coords'
    else:
        _pitch_source = 'coords'
    BASELINE = round(_pitch_med, 1) if _pitch_med is not None else round(FONT*1.5, 1)
    _font_source = ('env' if (os.environ.get('HORIZ_FONT_MEASURE') or os.environ.get('FONT_SCALE')) else ('fallback_ink' if _ink_applied else ('fallback' if _estimator == 'fallback' else 'formula')))
    _cw_source = ('env' if os.environ.get('HORIZ_CW') else ('fallback' if _estimator == 'fallback' else 'coords'))
    # t317：样本不足/公式失效时，font / baseline/font / cw 可能落到垃圾区间；
    # 只要同一份标定里的 ink_font 可信，就用它兜底（不改变已有正常书）。
    _ratio = (BASELINE / FONT) if FONT else 0
    _bad_font = (not (6.0 <= FONT <= 20.0))
    _bad_cw = (not (5 <= cw <= 80))
    if (os.environ.get('HORIZ_INK_FALLBACK', '0') not in ('0','false','False')
        or (os.environ.get('CALIB_BOOK') and not os.environ.get('FONT_SCALE'))) and _bad_font:
        _charw_pt = None
        try:
            _cand = [w / c * 72.0 / DPI for w, c in zip(widths, chars) if c > 0 and w > 0]
            if _cand:
                _charw_pt = round(statistics.median(_cand), 2)
        except Exception:
            pass
        if _charw_pt and 6.0 <= _charw_pt <= 20.0:
            print(f"[标定·fallback] font={FONT} → char_width={_charw_pt}", flush=True)
            FONT = _charw_pt; _font_source = 'ink_charwidth_fallback'; _ink_applied = True
        elif _ink_font and 6.0 <= _ink_font / 1.42 <= 20.0:
            _f2 = round(_ink_font / 1.42, 1)
            print(f"[标定·fallback] font={FONT} → ink/1.42={_f2}", flush=True)
            FONT = _f2; _font_source = 'ink_fallback'; _ink_applied = True
        if _font_source.startswith('ink_') or _font_source == 'body_median_fallback':
            # 标定走兜底的新书：禁用防溢出 strut 压缩，否则 27→24.9 行距双峰
            os.environ['HORIZ_NO_SSHRINK'] = '1'
        else:
            _fb_body = round(statistics.median(heights) * 72.0 / DPI / 0.88, 1) if heights else FONT
            if 6.0 <= _fb_body <= 20.0:
                print(f"[标定·fallback] font={FONT} → body_median={_fb_body}", flush=True)
                FONT = _fb_body; _font_source = 'body_median_fallback'
            else:
                _font_source = 'fallback_untrusted'
        _ratio = (BASELINE / FONT) if FONT else 0
    if FONT and _bad_cw:
        _cw_new = int(round(MEASURE / FONT)) if FONT else cw
        if 5 <= _cw_new <= 80:
            cw = _cw_new; _cw_source = 'fallback_median'
            print(f"[标定·fallback] cw → {cw} (measure={MEASURE}, font={FONT})", flush=True)
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
                PITCH_RATIO=_pitch_ratio_out, PITCH_SOURCE=_pitch_source,
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
                cw_sample_n=_full_n, cw_source=_cw_source,
                full_lines=_full_n, full_ratio=_full_ratio,
                estimator=_estimator, fallback_threshold=_fb_thresh,
                fallback_sample_n=(_fb or {}).get('sample_n'),
                fallback_width_pt=(_fb or {}).get('width_pt'),
                fallback_char_median=(_fb or {}).get('char_median'),
                measure_source=('fallback_uncut' if _estimator == 'fallback' else 'full_line_overbound'),
                font_scale=float(os.environ.get('FONT_SCALE', '1.0')),
                font_source=_font_source,
                ink_font=_ink_font, ink_applied=_ink_applied, ink_reject=_ink_reject,
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
        'cw_source': g.get('cw_source', 'coords'),
        'measure': {
            'poly_pt': g.get('MEASURE_POLY'),
            'source': g.get('measure_source', 'full_line_overbound'),
            'pt': g.get('MEASURE'),
            'overbound': g.get('OVERBOUND'),
        },
        'font': {
            'pt': g.get('FONT'),
            'scale': g.get('font_scale', 1.0),
            'source': g.get('font_source', 'formula'),
            'ink_pt': g.get('ink_font'),
            'ink_applied': bool(g.get('ink_applied')),
            'ink_reject': g.get('ink_reject'),
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
            'estimator': g.get('estimator', 'full_line'),
            'fallback_threshold': g.get('fallback_threshold'),
            'fallback_sample_n': g.get('fallback_sample_n'),
            'fallback_width_pt': g.get('fallback_width_pt'),
            'fallback_char_median': g.get('fallback_char_median'),
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
