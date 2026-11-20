#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版面判定层：纯文本/行判定函数（从 build_geom 抽出，行为保持不变）。

- 9 个函数：_heading_core/_head_level/_toc_level/_is_toc_entry/
  _is_figline/_is_bodyline/_is_weakfig/_layout_title_level/page_pitch
- page_pitch 需构建上下文（co/sl/page_px_h/dpi），由 configure() 注入；
  其余函数无副作用。
"""
import re
import statistics
import opencc

TOC_ENTRY_RE = re.compile(r'[.·…．⋯]{2,}\s*\d{1,4}(?:\s*[-—–~]\s*\d{1,4})?\s*$')
co = {}
sl = {}
page_px_h = 0.0
DPI = 200.0
PITCH_RATIO = 1.0   # coords 行距修正系数（源图投影标定，见 geometry.calibrate / AGENTS #67）
def configure(*, co, sl, page_px_h, dpi, pitch_ratio=1.0):
    globals().update(co=co, sl=sl, page_px_h=page_px_h, DPI=dpi, PITCH_RATIO=pitch_ratio)
_t2s = opencc.OpenCC('t2s')
def _has_trad(t):
    return _t2s.convert(t) != t

def _heading_core(t):
    t = t.strip()
    t = re.sub(r'^第[一二三四五六七八九十百千零\d]+(?:部分|[章节编篇])', '', t)
    t = re.sub(r'^[（(]?[一二三四五六七八九十\d]+[)）]?[、.．：\s]*', '', t)
    t = t.strip('[]【】()（）…·.　 ')
    return re.sub(r'\s+', '', t)

def _head_level(t, is_big):
    # 标题分级(决定字号档):分标题(超大行高)/节标题(编号或[引言]类)/大标题(其余)
    if is_big: return 'part'
    if t and (t[0].isdigit() or t[0] in '[【(（'): return 'section'
    return 'title'

def _toc_level(t):
    # 目录条目层级(决定缩进):部分/附录/导论=0, 章/节=1, 一/二/1.=2 → 还原源目录大小标题缩进
    s = t.strip()
    if re.match(r'^第[一二三四五六七八九十百千零\d]+(?:部分|编|篇)', s) or s.startswith(('附录', '导论', '总序', '后记', '前言')): return 0
    if re.match(r'^第[一二三四五六七八九十百千零\d]+[章节]', s): return 1
    if re.match(r'^[一二三四五六七八九十]+', s) or re.match(r'^[（(]?[一二三四五六七八九十\d]+[)）]', s) or re.match(r'^\d+[.．、]', s): return 2
    return 1

def _is_toc_entry(f):
    if TOC_ENTRY_RE.search(f['t']): return True
    fr = f.get('frags')
    return bool(fr) and any(t.strip().isdigit() for t, _ in fr) and any(not t.strip().isdigit() for t, _ in fr)

def _is_figline(t):
    if not t: return False
    if '�' in t: return True
    if re.fullmatch(r'[^a-z一-鿿]*', t) and re.search(r'[A-Z]', t): return True   # 纯大写(K.MARX/WAGES)
    if re.fullmatch(r'[\d\s./\-*,.]+', t) and 1 <= len(t) <= 8: return True         # 价格码 2)/12/35
    if _has_trad(t): return True                                                     # 繁体书影(書籍理/馬克思著)
    return False

def _is_bodyline(t):
    '简体正文/说明/标题/页眉——含简体CJK 即作书影带边界(繁体不算);长英文句也算'
    if len(t) < 3: return False
    if not re.search(r'[一-鿿]', t): return bool(re.search(r'[a-z]', t)) and len(t) >= 20
    if _has_trad(t): return False
    return True

def _is_weakfig(t):
    '含小写短英文行(书影封面 Wages,/Price/and/Profit/PROGRESS Publishers);纯数字不算(ISBN尾号)'
    if re.search(r'[一-鿿]', t) or _is_figline(t) or _is_bodyline(t): return False
    if not re.search(r'[A-Za-z]', t): return False
    return 1 <= len(t) < 30

def _layout_title_level(t):
    """LAYJSON paragraph_title 文本 -> 层级（只影响缩进/字重，不改字号）。
    L1: 中文数字+空格/全角空格；L2: N./N．；L3: 无编号短句。"""
    t = (t or '').strip()
    if re.match(r'^[一二三四五六七八九十]+(?:[ \u3000“”‘’]|$)', t):
        return 1
    if re.match(r'^\d+[.．]', t):
        return 2
    return 3

def page_pitch(key):
    """该页源【正文类行】相邻 y_center 差的中位(pt);样本<4 或超 [10,45]pt → None(回退全局)。
    口径与 verify _body_lines 对齐:行高在页中位 0.6~1.6× 内(保留夹注小字行,不剔除)。
    关键:全文夹注页(每行正文间夹小字注),若用 h≥0.82×H_BODY 把夹注剔除,正文行相邻 y 差
    变成"跨夹注"的 2× 间距→pitch 翻倍(35pt)→输出行距翻倍→溢出 split。保留夹注行后量到
    真实行间距(18pt)。脚注/页码大间隙由 <=1.8×m0 过滤掉。"""
    polys = co.get(key, []); txts = sl.get(key, [])
    L = []
    for i, poly in enumerate(polys):
        if not poly:
            continue
        t = (txts[i] if i < len(txts) else '').strip()
        if not t:
            continue
        ys = [p[1] for p in poly]
        yt, yb = min(ys), max(ys)
        yc = (yt + yb) / 2
        if not (0.06 * page_px_h < yc < 0.90 * page_px_h):
            continue
        L.append((yc, yb - yt))
    if len(L) < 4:
        return None
    # verify 口径:行高在页中位 0.6~1.6× 内(保留夹注小字;脚注大间隙由后面 <=1.8×m0 滤)
    medh = statistics.median([h for _, h in L])
    body = [yc for yc, h in L if 0.6 * medh <= h <= 1.6 * medh]
    if len(body) < 4:
        return None
    body.sort()
    diffs = [b - a for a, b in zip(body, body[1:]) if b - a > 20.0]   # 滤小间距(<20px=页码紧贴篇名/夹注双行),用正文/篇名行距(目录页篇名间距30-34pt)
    if not diffs:
        return None
    m0 = statistics.median(diffs)
    # 不再因行距方差大回退:split_polys 拆分后逐 poly 的 step 不均,会令多页 pstdev 偏大,
    # 但这些页的中位 pitch 仍与源一致(实测 99.8%≈verify src_pitch)。原方差过滤(pstdev>0.4*m0)
    # 误杀 wz3 的 315 页 -> 回退全局 pitch -> pitch 达标率掉。改用中位 pitch,方差大的页也生效。
    # 目录页/标题页行距虽乱,但 verify comparable 已排除;此处取中位不会比回退全局更差。
    pitch_px = statistics.median([d for d in diffs if d <= 1.8 * m0]) or m0
    pt = pitch_px * 72.0 / DPI
    # AGENTS #67：coords 行距系统性偏大（源图投影实测 wz3 +6.8% / wz2 +7.7%）。
    # 正文排版由**逐页 _pp** 主导（PER_PAGE_PITCH），BASELINE 只作回退 →
    # 修正必须放在这里，才能实际改变产物行距。
    _pr = globals().get('PITCH_RATIO', 1.0)   # 单测隔离 namespace 无此全局
    if _pr > 1.0001:
        pt = pt / _pr
    return round(pt, 2) if 10.0 <= pt <= 45.0 else None
