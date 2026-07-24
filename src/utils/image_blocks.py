#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""书影图块检测共享模块。detect_fig_bands/extract_figs/in_figure/in_figcaption。

bit-exact 复制 build_geom/build_classic 逻辑（两管线一致）。
函数接收 ctx（dict）避免模块级依赖：ctx 含 co/sl/PN_RE/page_px_h/_figs/_fig_titles/
SRC/LDPI + _is_bodyline/_is_figline/_is_weakfig（辅助函数引用，留管线）。
不读 LAYJSON（_figs/_fig_titles 由管线加载后传入 ctx）。
"""


def detect_fig_bands(key, ctx):
    '该页书影带 [(y0,y1,x0,x1) 200dpi px];body 行之间/前/后的 fig+weakfig 连续段(>=2,y跨>=80)'
    co, sl = ctx['co'], ctx['sl']
    PN_RE, page_px_h = ctx['PN_RE'], ctx['page_px_h']
    _is_bodyline, _is_figline, _is_weakfig = ctx['_is_bodyline'], ctx['_is_figline'], ctx['_is_weakfig']
    polys = co.get(key, []); txts = sl.get(key, []); items = []
    for i in range(min(len(polys), len(txts))):
        t = txts[i].strip()
        if not t or not polys[i]: continue
        ys = [p[1] for p in polys[i]]; xs = [p[0] for p in polys[i]]
        items.append({'t': t, 'y0': min(ys), 'y1': max(ys), 'x0': min(xs), 'x1': max(xs)})
    if len(items) < 4: return []
    for r in items:
        r['body'] = _is_bodyline(r['t']); r['fig'] = _is_figline(r['t']); r['wf'] = _is_weakfig(r['t'])
    items.sort(key=lambda r: r['y0'])
    def _pn(r): return bool(PN_RE.fullmatch(r['t'].strip())) and r['y0'] > page_px_h * 0.80
    def _ft(r): return (r['fig'] or r['wf']) and not _pn(r)
    body_idx = [i for i, r in enumerate(items) if r['body']]
    bands = []
    def _mk(seg):
        if len(seg) < 2: return None
        if sum(1 for r in seg if _ft(r)) < 2: return None
        y0 = min(r['y0'] for r in seg); y1 = max(r['y1'] for r in seg)
        if y1 - y0 < 80: return None
        return (y0, y1, min(r['x0'] for r in seg), max(r['x1'] for r in seg))
    for a, b in zip(body_idx, body_idx[1:]):
        bd = _mk(items[a+1:b])
        if bd: bands.append(bd)
    if body_idx:
        bd = _mk([r for r in items[:body_idx[0]] if not _pn(r)])
        if bd: bands.append(bd)
        bd = _mk([r for r in items[body_idx[-1]+1:] if not _pn(r)])
        if bd: bands.append(bd)
    bands.sort()
    return bands


def extract_figs(key, ctx):
    '提取该页所有图块(裁源图 200dpi),返回 [(png路径, layout_px_bbox)]'
    _figs, SRC, LDPI = ctx['_figs'], ctx['SRC'], ctx['LDPI']
    import fitz
    from PIL import Image
    if key not in _figs or not SRC: return []
    _d = fitz.open(SRC); _pix = _d[int(key)].get_pixmap(dpi=200); _img = Image.frombytes('RGB',[_pix.width,_pix.height],_pix.samples); _d.close()
    _s = 200.0/LDPI
    _out = []
    for _i, _bb in enumerate(_figs[key]):
        _c = _img.crop([max(0,int(v*_s)) for v in _bb])
        _p = f'/tmp/fig_{key}_{_i}.png'; _c.save(_p); _out.append((_p, _bb))
    return _out


def in_figure(x0, y0, w, h, key, text, ctx):
    '该行(200dpi px)中心是否落在某图块内(layout bbox×200/142);或在图纵向带内且无CJK'
    _figs, LDPI = ctx['_figs'], ctx['LDPI']
    if key not in _figs: return False
    cx, cy = x0 + w/2, y0 + h/2; _s = 200.0/LDPI
    _has_cjk = any('一' <= c <= '鿿' for c in text)
    for _bb in _figs[key]:
        _fx0, _fy0, _fx2, _fy2 = _bb[0]*_s, _bb[1]*_s, _bb[2]*_s, _bb[3]*_s
        if _fx0 <= cx <= _fx2 and _fy0 <= cy <= _fy2: return True
        if _fy0 <= cy <= _fy2 and not _has_cjk: return True
    return False


def in_figcaption(x0, y0, w, h, key, ctx):
    '该行(200dpi px)中心是否落在 figure_title block(图说明)bbox 内 -> 居中渲染'
    _fig_titles, LDPI = ctx['_fig_titles'], ctx['LDPI']
    if key not in _fig_titles: return False
    cx, cy = x0 + w/2, y0 + h/2; _s = 200.0/LDPI
    for _bb in _fig_titles[key]:
        if _bb[0]*_s <= cx <= _bb[2]*_s and _bb[1]*_s <= cy <= _bb[3]*_s: return True
    return False
