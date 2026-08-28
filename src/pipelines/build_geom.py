#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_geom.py — seg2 原型:PaddleOCR spotting 行级 → 逐行还原(书风格)。
按 bbox 行高/位置/内容分类:标题(高)、正文(中)、脚注(矮)、页眉(顶部)、页码(底部数字)。
各类不同字号;页码走 \setcounter 页脚、页眉走顶部小字;正文逐行固定 + 按缩进分段(首行缩进2em)。
字号/版心/行距从满行几何推导。不需 MinerU。
用法: python3 build_geom.py [spotting_lines] [spotting_coords] [out.pdf]
环境: PAGENUM_GLOBAL_TABLE / PAGENUM_OFFSET (页码继承)
"""
import json, sys, statistics, subprocess, os, shutil, re, opencc
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from utils.tex_escape import escape_latex
from utils.geometry import calibrate
from utils.page_numbers import load_pntab, infer_lay_numbers, PN_RE
from utils import image_blocks as _img
from utils import missing_chars as _mc
from _latex_preamble import build_latex

SL = sys.argv[1] if len(sys.argv) > 1 else '/opt/test/wz1p108_spotting_lines.json'
CO = sys.argv[2] if len(sys.argv) > 2 else '/opt/test/wz1p108_spotting_coords.json'
OUT = sys.argv[3] if len(sys.argv) > 3 else '/tmp/seg2_line.pdf'
SRC = sys.argv[4] if len(sys.argv) > 4 else ''   # 源 PDF(图页/乱码页贴原图用)
DPI = 200

sl = json.load(open(SL, encoding='utf-8'))
co = json.load(open(CO, encoding='utf-8'))

_G = calibrate(sl, co, DPI, src_pdf=SRC)
DPI = _G['DPI']   # 自适应后的真实 dpi(coords 尺度随 API 批次漂移 200/142)
PAGE_W, PAGE_H = _G['PAGE_W'], _G['PAGE_H']
cw = _G['cw']; MEASURE_POLY = _G['MEASURE_POLY']; OVERBOUND = _G['OVERBOUND']
MEASURE = _G['MEASURE']; FONT = _G['FONT']; MARGIN = _G['MARGIN']
BASELINE = _G['BASELINE']; LINESPREAD = _G['LINESPREAD']; FONT_SM = _G['FONT_SM']
H_BODY = _G['H_BODY']; PUNCT_WEIGHT = _G['PUNCT_WEIGHT']; USE_REGION = _G['USE_REGION']
REGION_FONT_SCALE = _G['REGION_FONT_SCALE']; page_px = _G['page_px']
print(f"[几何] cw={cw} measure={MEASURE} font={FONT} baseline={BASELINE} 小字{FONT_SM} 正文行高{H_BODY:.0f}px")

pn_off = int(os.environ.get('PAGENUM_OFFSET', '0'))
pntab = load_pntab()
TOC_ENTRY_RE = re.compile(r'[.·…．]{2,}\s*\d{1,4}\s*$')   # 目录条目:"标题....页码"(点引导+数字)→ 不是标题,是目录正文
FN_CIRCLE = set('①②③④⑤⑥⑦⑧⑨⑩')
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
_toc_file = os.environ.get('TOC_HEADING_MAP', '') or '/tmp/toc_map.json'   # 默认全量 wz1 TOC(env 可覆盖)
toc_map = json.load(open(_toc_file, encoding='utf-8')) if _toc_file and os.path.exists(_toc_file) else {}
if not toc_map:
    # 自动提取:扫描目录页(>=5 个 TOC_ENTRY_RE 行)→ 剥尾部"…页码"→ _heading_core 入表。
    # 内容页标题 _heading_core 命中即识别为标题(序号剥后匹配,抗 OCR 空格差异)。
    for _k in sl:
        _lines = [l.strip() for l in sl.get(_k, [])]
        _n_dot = sum(1 for l in _lines if TOC_ENTRY_RE.search(l))
        _n_pair = sum(1 for i in range(len(_lines) - 1) if _lines[i] and not re.fullmatch(r'\s*\d{1,4}\s*', _lines[i]) and re.fullmatch(r'\s*\d{1,4}\s*', _lines[i + 1]))
        if _n_dot < 5 and _n_pair < 5:
            continue
        for _i, _l in enumerate(_lines):
            if not _l:
                continue
            if TOC_ENTRY_RE.search(_l):
                _title = TOC_ENTRY_RE.sub('', _l).strip()
            elif not re.fullmatch(r'\s*\d{1,4}\s*', _l) and _i + 1 < len(_lines) and re.fullmatch(r'\s*\d{1,4}\s*', _lines[_i + 1]):
                _title = _l   # 2 行式:标题行 + 下行纯页码
            else:
                continue
            _title = _title.strip(' .·…．:：')
            _c = _heading_core(_title)
            if len(_c) >= 2:
                toc_map[_c] = True
    if toc_map:
        print(f"[toc_map] 自动提取 {len(toc_map)} 个目录标题(未设 TOC_HEADING_MAP)")
page_px_h = PAGE_H * DPI / 72

# ── 改动1:按页实测行距(PER_PAGE_PITCH=1)──
# 全局单值 LINESPREAD 对单规制书(wz1)只差~3%,但对多规制书(wz2:正文/注疏/卷首字号行距各异)
# 会把大行距页压成小行距 → 底部大片空白。按页从源相邻正文行 y_center 差的中位数反推该页
# linespread,使输出行距=源行距。默认关(wz1 现状零变);样本不足/超正常带的页回退全局 BASELINE。
PER_PAGE_PITCH = os.environ.get('PER_PAGE_PITCH', '') in ('1', 'true', 'True')

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
    return round(pt, 2) if 10.0 <= pt <= 45.0 else None

def _filter_pn_ocr(pn_ocr, prev_pn):
    """pn_ocr 单调性过滤:与上一页页码差>2(突变)则弃用(目录页 p11=29 误识),连续则采用。
    prev_pn=None(首页/封面后首个)时直接采用。无外部页码表(LAYJSON/PAGENUM_GLOBAL_TABLE)时
    用 OCR 读到的底部数字页码,但目录页 OCR 会把目录里的页号误识为页码(突变),需滤掉。"""
    if not pn_ocr:
        return ''
    if prev_pn is None:
        return pn_ocr
    try:
        cur = int(pn_ocr)
    except ValueError:
        return ''
    if prev_pn - 1 <= cur <= prev_pn + 2:   # 连续(允许-1/+2:跳过空页/重号)
        return pn_ocr
    return ''   # 突变弃用
# ── 位置还原两趟校准:单趟估高有每页方差(字体混合)→ 溢出与空白不可兼得。
# pass1 导出各页估高(POS_EST_LOG),用标记量实测高;pass2 读入比值(POS_RATIO_TABLE)校正估高 → 精确压到刚好一页。
_pos_ratio = {}
_rt = os.environ.get('POS_RATIO_TABLE', '')
if _rt and os.path.exists(_rt):
    _pos_ratio = json.load(open(_rt, encoding='utf-8'))
_pos_est = {}
# 页眉→正文 / 标题→正文 间距(从 spotting y 推导,匹配源)
hdr_gaps = []; head_gaps = []
for _k in sl:
    _polys = co.get(_k, [])
    _items = []
    for _i in range(min(len(_polys), len(sl[_k]))):
        _t = sl[_k][_i].strip()
        if not _t or not _polys[_i]: continue
        _ys = [p[1] for p in _polys[_i]]
        _items.append((min(_ys), max(_ys), _t))
    _items.sort()
    for _j in range(len(_items) - 1):
        _y0a, _y1a, _ta = _items[_j]; _y0b, _y1b, _tb = _items[_j + 1]
        _gap = _y0b - _y1a
        if not (3 < _gap < 80): continue
        if _j == 0 and len(_ta) < 30 and _y0a < page_px_h * 0.06:
            hdr_gaps.append(_gap)
        if _heading_core(_ta) in toc_map:
            head_gaps.append(_gap)
HDR_GAP = round(statistics.median(hdr_gaps) * 72 / DPI, 1) if hdr_gaps else 6
HEAD_GAP = round(statistics.median(head_gaps) * 72 / DPI, 1) if head_gaps else 8
print(f"[几何] ... 页眉间距={HDR_GAP}pt 标题间距={HEAD_GAP}pt 行距={BASELINE}pt")

def _math_to_plain(m):
    # $...$ 内的 LaTeX 数学 → 纯文本(OCR 数学语法不可靠,不用真数学模式防 xelatex 报错)
    s = m.group(1)
    s = re.sub(r'\\frac\{([^{}]*)\}\{([^{}]*)\}', r'\1/\2', s)   # \frac{a}{b} → a/b
    s = re.sub(r'\\([a-zA-Z]+)', r'\1', s)                      # \command → command(去反斜杠)
    return s.replace('{', '').replace('}', '')                      # 残余花括号去掉

def _esc_chars(s):
    '通用 LaTeX 转义:委托 utils.tex_escape.escape_latex(mode=geom)'
    return escape_latex(s, 'geom')

def esc(t):
    # 纯上标标记 $ ^{[八五]} $ / $ ^{①} $(行中夹注/脚注引用)→ 占位符保护,通用转义后还原为 \textsuperscript{内容}
    # 其他 $...$(分数 \frac 等)→ 纯文本。必须在通用转义前处理(否则 \frac 反斜杠先被删 → 字面 "frac" 泄漏)
    _sup = []
    def _dollar(m):
        inner = m.group(1)
        ms = re.match(r'^\s*\^{(.+?)}\s*$', inner)   # 纯上标:整段 $...$ 只有 ^{X}
        if ms:
            _sup.append(ms.group(1)); return '\x01SUP%d\x01' % (len(_sup) - 1)
        return _math_to_plain(m)
    t = re.sub(r'\$([^$]*)\$', _dollar, t)
    t = t.replace('$', '')   # 残余孤立 $(OCR 用 $ 包数学,真实货币符罕见)
    # 裸 [CJK序数/数字](无 $^{}$ 包裹的校注标记,如"始元六年[二]")→ 同样占位为上标 〔〕。全书有 1086 个这种(OCR 未包 $),否则按字面满号 [] 渲染
    def _bare(m):
        _sup.append(m.group(0)); return '\x01SUP%d\x01' % (len(_sup) - 1)
    t = re.sub(r'^\[[一二三四五六七八九〇○\d]{1,4}\]', lambda m: m.group(0).replace('[','〔').replace(']','〕'), t)   # 行首注释序号[X]→〔X〕白括号(不上标,与〔二〕〔三〕一致)
    t = re.sub(r'(?<=\S)[〔【[]([一二三四五六七八九〇○\d]{1,4})[】〕\]]', _bare, t)   # [X]/〔X〕/【X】前有文字=校注标记->上标   # [X]前有文字(非行首)=校注标记→上标〔X〕;行首[X]前无→序号不转(OCR 识〔一〕为[一])
    t = _esc_chars(t)
    _mscale = float(os.environ.get('MARKER_SCALE', '0.55'))   # 上标字号比例(0.7=\textsuperscript默认);调到匹配源的 marker 占宽(源 marker 宽→文字挤紧→带标记行字距差更小)
    for i, raw in enumerate(_sup):
        _raw = raw.replace('[', '〔').replace(']', '〕')   # OCR 把源的〔〕白括号识成[]方括号,转回(wz2 校注标记是〔一〕〔二〕...)
        t = t.replace('\x01SUP%d\x01' % i, '{\\smash{\\raisebox{0.6ex}{\\fontsize{%.1fpt}{%.1fpt}\\selectfont %s}}}' % (FONT*_mscale, FONT*_mscale*1.1, _esc_chars(_raw)))   # smash零高(不撑高行框)+显式字号(MARKER_SCALE 调占宽匹配源)
    return t

# 标题序号前缀拆分:序号(第X部分/章/节、(一)、一、1.等)与内容分离,中间插 \quad 空隙。
# OCR 常把序号与内容连在一起无空格(如"(二)被收录著作集"),渲染时补回视觉间隔。
_HEADING_PREFIX_RE = re.compile(r'^(第[一二三四五六七八九十百千零\d]+(?:部分|[章节编篇])|[（(]?[一二三四五六七八九十]+[)）]?[、.．：\s]?(?!百|千|万|亿)|[（(]?\d+[)）]?[、.．：\s])')
def _split_heading(t):
    m = _HEADING_PREFIX_RE.match(t.strip())
    if m:
        rest = t.strip()[m.end():].lstrip()
        if rest:
            return m.group(1), rest
    return '', t
def _esc_heading(t):
    _pre, _rest = _split_heading(t)
    if _pre:
        _pre = _pre.rstrip()
        if _pre and _pre[-1] in '、.．：':
            return esc(_pre) + esc(_rest)   # 序号已带分隔标点(顿号/点号),本身即分隔,不再叠加空隙
        return esc(_pre) + '\\quad ' + esc(_rest)
    return esc(t)

TERMINAL = set('。！？!?.?）)】」』"\'…')

# 位置还原(POSITIONAL=1):每行按源 y 增量定位(\vspace 补足行距),页面填满如源。默认关——wz1 等已有数据的 y 尺度未必适配,用开关隔离
USE_POS = os.environ.get('POSITIONAL', '') in ('1', 'true', 'True')

_TRAD = set('書論學價勞業龍產島條發為圖國會來節過還開關見說話語詞買賣費資潤寰焉戀誌')
# 书影带检测(无 LAYJSON 版面 JSON 时,从 OCR 行内容+分布推断书影 bbox):
# 整页扫描图的书影页,OCR 把书影里文字也识出(大写/繁体/外文短行)。用 opencc 区分简体
# 正文(=body 边界)与繁体书影;纯大写/含繁/数字符号=fig,含小写短英文=weakfig。body 行之间
# (或首body前/末body后)的 fig+weakfig 连续段(>=2行,y跨>=80px)=书影带。带内 OCR 行跳过
# (不识别图里文字),带外行渲染(上下文字保留),带区域裁源图贴回。
_t2s = opencc.OpenCC('t2s')
def _has_trad(t):
    return _t2s.convert(t) != t
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
# 图块映射(从 PaddleOCR 版面 JSON 提取 image 块 bbox;坐标在 layout DPI~142px 空间)
LAYJSON = os.environ.get('LAYJSON', '')
LDPI = 142.0   # layout 渲染 DPI(bbox 坐标尺度;200dpi 渲染裁剪时 bbox×200/142)
_figs = {}
_fig_titles = {}   # figure_title block(图说明)bbox,用于图下方说明行居中
_IMG_CTX = dict(co=co, sl=sl, PN_RE=PN_RE, page_px_h=page_px_h, _figs=_figs, _fig_titles=_fig_titles, SRC=SRC, LDPI=LDPI, _is_bodyline=_is_bodyline, _is_figline=_is_figline, _is_weakfig=_is_weakfig)
def detect_fig_bands(key): return _img.detect_fig_bands(key, _IMG_CTX)
def extract_figs(key): return _img.extract_figs(key, _IMG_CTX)
def in_figure(x0, y0, w, h, key, text=''): return _img.in_figure(x0, y0, w, h, key, text, _IMG_CTX)
def in_figcaption(x0, y0, w, h, key): return _img.in_figcaption(x0, y0, w, h, key, _IMG_CTX)
if LAYJSON and os.path.exists(LAYJSON):
    _ld = json.load(open(LAYJSON, encoding='utf-8'))
    for _pi, _pg in enumerate(_ld):
        _fl = [_b['block_bbox'] for _b in _pg.get('prunedResult',{}).get('parsing_res_list',[]) if _b.get('block_label')=='image' and _b.get('block_bbox')]
        if _fl: _figs[str(_pi)] = _fl
        _ft = [_b['block_bbox'] for _b in _pg.get('prunedResult',{}).get('parsing_res_list',[]) if _b.get('block_label')=='figure_title' and _b.get('block_bbox')]
        if _ft: _fig_titles[str(_pi)] = _ft
    print(f"[图块] 加载 {len(_figs)} 页含图块, {len(_fig_titles)} 页含图说明(figure_title)")
# 书影带(无 LAYJSON 时从 OCR 推断)填 _figs:坐标转 142dpi 空间(同 LAYJSON block_bbox),
# 复用 extract_figs 裁源图 / in_figure 跳带内行 / figrow 按源 y 插入贴图
if SRC:   # 启发式补 LAYJSON 漏检页(只对图页/乱码页跑,防 wz2 注释页繁体校注/目录页码误判书影带)
    _nb = 0
    for _k in sl:
        if _k in _figs: continue
        _ne = [l.strip() for l in sl.get(_k, []) if l.strip()]
        _n = len(_ne)
        if _n == 0: continue
        _cap = sum(1 for l in _ne if re.search(r'[A-Z]{4,}', l))
        _fffd = any('�' in l for l in _ne)
        _trad = sum(1 for l in _ne for c in l if c in _TRAD)
        _single = sum(1 for l in _ne if len(l) <= 2 and not l.isdigit())
        _is_gar = (_cap >= 5) or (_cap >= 3 and _cap/_n > 0.3) or _fffd or (_trad >= 5 and _n < 15) or (_single >= 8 and _n < 15)
        if not _is_gar: continue   # 非图页不跑(防文字页误判书影带→figrow 贴图破坏排版)
        _bands = detect_fig_bands(_k)
        if _bands:
            _figs[_k] = [[x0*LDPI/DPI, y0*LDPI/DPI, x1*LDPI/DPI, y1*LDPI/DPI] for (y0, y1, x0, x1) in _bands]
            _nb += 1
    if _nb: print(f"[书影带] {_nb} 页从 OCR 推断图块(补 LAYJSON 漏检)")
# 标题块映射(LAYOUT_HEADINGS=1 启用:用版面模型 doc_title/paragraph_title 标签驱动标题检测,带 # 级别)。默认关,启发式兜底——不影响未开启的书(wz1 等)
USE_LAY_HEAD = os.environ.get('LAYOUT_HEADINGS', '') in ('1', 'true', 'True')
_TITLE_CJK = 'song' if os.environ.get('FONT_TITLE', 'hei') == 'song' else 'heiti'   # 章标题字体: hei=黑体(默认) / song=宋体(源书章标题为宋体时, 如 mgfdmg)
_SUBTITLE_CJK = 'song' if os.environ.get('FONT_SUBTITLE', 'hei') == 'song' else 'heiti'   # 节标题字体: hei=黑体(默认, mgfdmg 节标题黑体) / song=宋体
def _hf(f):
    '按标题档选字体: part/title=章字体, section=节字体'
    return _SUBTITLE_CJK if f.get('tier') == 'section' else _TITLE_CJK
_PAGE_IMG_PAGES = set(int(x) for x in os.environ.get('PAGE_IMAGE_PAGES', '').split(',') if x.strip())   # 贴图页(封面/扉页/版权页): 直接渲染原扫描图
_TOC_LEVELS = []
_toc_rules_f = os.environ.get('TOC_RULES', '')
if _toc_rules_f and os.path.exists(_toc_rules_f):
    try:
        _TOC_LEVELS = [(re.compile(_r['pattern']), _r['level']) for _r in json.load(open(_toc_rules_f)).get('levels', [])]
        print(f'[TOC_RULES] 目录级别规则 {len(_TOC_LEVELS)} 条: ' + ', '.join(f"{lvl}:{pat.pattern}" for pat, lvl in _TOC_LEVELS))
    except Exception as _e:
        print(f'[TOC_RULES] 加载失败: {_e}')
_PAGE_IMG_PREFIX = os.environ.get('PAGE_IMAGE_PREFIX', '')
_head_blocks = {}   # page_key -> [(bbox_142dpi, #级别)]
if USE_LAY_HEAD and LAYJSON and os.path.exists(LAYJSON):
    try: _ld
    except NameError: _ld = json.load(open(LAYJSON, encoding='utf-8'))
    for _pi, _pg in enumerate(_ld):
        _hb = []
        for _b in _pg.get('prunedResult',{}).get('parsing_res_list',[]):
            if _b.get('block_label') in ('doc_title','paragraph_title','title') and _b.get('block_bbox'):
                _c = _b.get('block_content', '')
                _lvl = len(_c) - len(_c.lstrip('#'))   # 前导 # 数 = 级别(doc_title=1, ##目录=2, ####章名=4)
                if _lvl == 0: _lvl = 3   # 无 # 标记的 title 块默认中等
                _hb.append((_b['block_bbox'], _lvl))
        if _hb: _head_blocks[str(_pi)] = _hb
    print(f"[标题·layout] 加载 {len(_head_blocks)} 页含标题块(LAYOUT_HEADINGS=1,layout 优先+启发式补充)")
def _layout_head_level(x0, y0, w, h, key):
    '该行中心落在某 layout 标题块内 → 返回 # 级别;否则 None。缩放 _s=DPI/LDPI: 行坐标尺度=自适应 DPI(wz1 200dpi), 块尺度=LDPI≈142 → 1.408; 同批次书(mgfdmg 141/142)≈1。±8px 容差兜噪声'
    if key not in _head_blocks: return None
    cx, cy = x0 + w/2, y0 + h/2; _s = DPI/LDPI; _tol = 8   # 容差:142dpi 下行距~28px,8px 够不到相邻正文行
    for _bb, _lvl in _head_blocks[key]:
        if _bb[0]*_s - _tol <= cx <= _bb[2]*_s + _tol and _bb[1]*_s - _tol <= cy <= _bb[3]*_s + _tol: return _lvl
    return None
# 边栏旁注(竖排书名/卷名 aside_text):eso-pic 绝对定位贴回边栏。每页清叠加防累积
_asides = {}   # page_key -> [(content, bbox_142dpi)]
if LAYJSON and os.path.exists(LAYJSON):
    try: _ld
    except NameError: _ld = json.load(open(LAYJSON, encoding='utf-8'))
    for _pi, _pg in enumerate(_ld):
        _as = [(_b.get('block_content', ''), _b['block_bbox']) for _b in _pg.get('prunedResult',{}).get('parsing_res_list',[]) if _b.get('block_label')=='aside_text' and _b.get('block_bbox')]
        if _as: _asides[str(_pi)] = _as
    if _asides: print(f"[旁注] 加载 {len(_asides)} 页含边栏旁注(竖排贴回)")
# aside 补全:用目录篇名匹配截断的 content(layout OCR 漏字,如 '卷第一本议第'→'卷第一 本议第一')
_aside_titles = set()
for _k in sl:
    _lines = [l.strip() for l in sl.get(_k, []) if l.strip()]
    _n_pair = sum(1 for i in range(len(_lines)-1) if _lines[i] and not _lines[i].isdigit() and _lines[i+1].isdigit())
    if _n_pair < 5: continue   # 目录页(篇名+页码 对>=5)
    for _l in _lines:
        if re.search(r'第[一二三四五六七八九十百]+', _l) and 2 <= len(_l) <= 8:   # 篇名含"第X"(本议第一/力耕第二)
            _aside_titles.add(_l)
def _fix_aside(content):
    c = content.replace('\n', '').replace(' ', '').strip()
    m = re.match(r'^卷第[一二三四五六七八九十百零\d]+', c)
    prefix = m.group(0) if m else ''
    rest = c[len(prefix):]
    if prefix and rest and len(rest) >= 2:
        for title in _aside_titles:
            if title.startswith(rest) and len(title) > len(rest):   # 前缀匹配(本议第→本议第一)
                return prefix + ' ' + title
    return content
_fixed = 0
for _k in list(_asides):
    _new = []
    for _c, _bb in _asides[_k]:
        _fc = _fix_aside(_c)
        if _fc != _c: _fixed += 1
        _new.append((_fc, _bb))
    _asides[_k] = _new
if _asides and _fixed: print(f"[旁注] 补全 {_fixed} 页截断 aside(用目录篇名匹配)")
_lay_numbers = infer_lay_numbers(LAYJSON)
def is_garbage_page(lines):
    # 图页/乱码页:大量全大写拉丁(书影封面)、U+FFFD、或大量繁体字(简体书出现繁体=竖排/装饰 OCR 乱码,如"書道論語主列焉")
    ne = [l.strip() for l in lines if l.strip()]
    n = len(ne)
    if n == 0: return False
    cap = sum(1 for l in ne if re.search(r'[A-Z]{4,}', l))
    cap_ratio = cap / n
    fffd = any('�' in l for l in ne)
    trad = sum(1 for l in ne for c in l if c in _TRAD)
    single = sum(1 for l in ne if len(l) <= 2 and not l.isdigit())   # 单字行(竖排书名 OCR 成一字一行)
    # cap 要求占比>30%(防正文页 MEGA 等缩写 cap=4/25 误伤);trad/single 要求行少 n<15(书影页行少,防大纲页 single=8/35 误伤)
    return (cap >= 5) or (cap >= 3 and cap_ratio > 0.3) or fffd or (trad >= 5 and n < 15) or (single >= 8 and n < 15)
def render_src_page(k):
    import fitz
    _d = fitz.open(SRC); _pix = _d[int(k)].get_pixmap(dpi=200); _p = f'/tmp/srcpage_{k}.png'; _pix.save(_p); _d.close(); return _p

pages_tex = []
# 预扫描:各级标题字号 = 该级行高中位 × FONT/H_BODY(同级同字号,抗 OCR poly 噪声——
# 同级节标题 poly 在 39–56px 乱跳,按单个 poly 算会导致 3.和4. 字号不一)
_bleft = MARGIN * DPI / 72; _bright = (PAGE_W - MARGIN) * DPI / 72; _inset = page_px * 0.06
_lvl_h = {'part': [], 'title': [], 'section': []}
for _k in sl:
    _polys = co.get(_k, [])
    for _i, _l in enumerate(sl[_k]):
        _t = _l.strip()
        if not _t or _i >= len(_polys) or not _polys[_i]: continue
        _xs = [p[0] for p in _polys[_i]]; _ys = [p[1] for p in _polys[_i]]
        _x0, _h, _y0, _w = min(_xs), max(_ys)-min(_ys), min(_ys), max(_xs)-min(_xs)
        if PN_RE.fullmatch(_t) and _y0 > page_px_h*0.80: continue
        if _y0 < page_px_h*0.06 and len(_t) < 30: continue
        if _y0 > page_px_h*0.95 and (_w/page_px) < 0.50: continue   # 水印(极底部窄行)——不滤会混进 title 级拉低中位
        if TOC_ENTRY_RE.search(_t): continue   # 目录条目(点引导+页码)不算标题,否则污染标题字号中位
        _core = _heading_core(_t)
        _cen = (_x0 > _bleft + _inset) and (_x0 + _w < _bright - _inset) and (_w/page_px < 0.85)
        _big = _h > H_BODY * 1.8
        if not ((bool(_core) and len(_core) >= 2 and _core in toc_map) or _cen or _big): continue
        if _h <= H_BODY * 1.1: continue   # 只统计比正文高的真标题;前言/版权页居中文字是正文行高,会污染字号中位
        _lvl_h[_head_level(_t, _big)].append(_h)
tier_size = {lvl: round(statistics.median(hs) * FONT / H_BODY, 1) if hs else FONT for lvl, hs in _lvl_h.items()}
print(f"[标题字号] 分{tier_size.get('part','—')}pt 大{tier_size.get('title','—')}pt 节{tier_size.get('section','—')}pt (按级行高中位,同级同号)")
# 页眉共识:统计各页页眉(顶部 y<5% 行,按 x 合并),频次≥3=规范页眉。OCR 偶有拆分/截断/混噪声("历史考"缺"证"、"与党总"前缀),用共识校正
def page_header_raw(key):
    '从原始 OCR 行(未经视觉合并)取页眉:顶部 y<5% 行按 x 合并。避免视觉合并把多片段页眉("第一部分"+"历史考")因负x间隙乱序拼接'
    _frags = []; _cl = co.get(key, [])
    _pn_local = globals().get('PN_RE') or re.compile(r'^\d+$')   # 单元测试隔离 namespace 无全局 PN_RE
    for _i, _t in enumerate(sl[key]):
        _t = _t.strip()
        if not _t or _i >= len(_cl) or not _cl[_i]: continue
        _ys = [p[1] for p in _cl[_i]]; _xs = [p[0] for p in _cl[_i]]
        # 排除纯数字行(书眉式页码在页顶左右角, 混入拼接致每页不同 → 共识失败, 页眉漏识别)
        if min(_ys) < page_px_h * 0.10 and len(_t) < 30 and not _pn_local.fullmatch(_t):
            _frags.append((min(_xs), _t))
    _frags.sort()
    return ''.join(_t for _, _t in _frags) if _frags else ''
_hdr_count = {}
for _key in sl:
    _m = page_header_raw(_key)
    if _m: _hdr_count[_m] = _hdr_count.get(_m, 0) + 1
CANON_HDRS = [t for t, c in _hdr_count.items() if c >= 3]
print(f"[页眉共识] {len(CANON_HDRS)} 个规范页眉")
def _match_canon_hdr(t):
    """文本是否匹配共识页眉(difflib ratio>0.8)。is_hdr 共识兜底用:
    顶部行(0.06-0.10 页高)匹配共识页眉也判页眉(覆盖 wz3 6%边缘页眉 y0==0.06*pph 漏判),
    非共识(扉页文字如 wz1 '中央编译局文库')不误判进 flow 正常渲染。"""
    if not CANON_HDRS:
        return False
    import difflib
    return max(difflib.SequenceMatcher(None, t, _c).ratio() for _c in CANON_HDRS) > 0.8


_PPSCORE_FILE = os.environ.get('PPSCORE_FILE', '')
_ppocrv6_scores = {}
if _PPSCORE_FILE and os.path.exists(_PPSCORE_FILE):
    _ppocrv6_scores = json.load(open(_PPSCORE_FILE, encoding='utf-8'))
    _low = sum(1 for v in _ppocrv6_scores.values() for _, s, _ in v if s < 0.85)
    print(f"[PP-OCRv6 score] 加载 {len(_ppocrv6_scores)} 页, 低分(<0.85) {_low} 行(整行贴图)")

# VL vs PP-OCRv6 wordbox 对比(VL有v6无+v6频<20=古字识错),单字贴图
_VLV6DIFF_FILE = os.environ.get('VLV6DIFF_FILE', '')
_vl_v6_diff = {}
if _VLV6DIFF_FILE and os.path.exists(_VLV6DIFF_FILE):
    _vl_v6_diff = json.load(open(_VLV6DIFF_FILE, encoding='utf-8'))
    _diff_total = sum(len(v) for v in _vl_v6_diff.values())
    print(f"[VL vs v6] 加载 {len(_vl_v6_diff)} 页, {_diff_total} 字(单字贴图)")


def _esc_with_missing(t, f, key):
    """esc(t) + 缺字贴图:1)VL≠v6单字贴图 2)行级低score整行贴图 3)空引号""单字贴图。"""
    esc_t = esc(t)
    if not SRC:
        return esc_t
    import os
    _od = '/tmp/missing_chars'; os.makedirs(_od, exist_ok=True)
    # 1) VL≠v6 单字贴图(VL有v6无+v6频<20=古字识错,用v6 word_box精确定位)
    if _vl_v6_diff:
        for _ci, _vl_c, _wb, _poly in _vl_v6_diff.get(key, []):
            if _ci < len(t) and t[_ci] == _vl_c:   # VL 行第 _ci 字仍是要替换的字
                try:
                    # 用 v6 word_box 剪源图(精确单字位置)
                    _xs = [_wb[0], _wb[2]]; _ys = [_wb[1], _wb[3]]
                    _bbox = [[min(_xs), min(_ys)], [max(_xs), min(_ys)], [max(_xs), max(_ys)], [min(_xs), max(_ys)]]
                    _img = _mc.crop_row(SRC, int(key), _bbox, _od)   # crop_row 接受 4 点 poly
                    # 在 esc_t 里找第 _ci 个CJK字替换为图
                    _cjk_idx = 0
                    for _j, _ch in enumerate(esc_t):
                        if ord(_ch) > 0x2e80:
                            if _cjk_idx == _ci:
                                esc_t = esc_t[:_j] + '\\raisebox{-2pt}{\\includegraphics[height=%spt]{%s}}' % (f.get('fnt', FONT), _img) + esc_t[_j + len(_ch):]
                                break
                            _cjk_idx += 1
                    else:
                        continue
                    return esc_t
                except Exception:
                    pass
    # 2) 行级低 score 整行贴图(PP-OCRv6 行级<0.85=整行识错古字)
    if _ppocrv6_scores:
        for _poly, _score, _ in _ppocrv6_scores.get(key, []):
            if _score < 0.85:
                _ys = [p[1] for p in _poly]
                if min(_ys) - 10 <= f.get('y0', 0) <= max(_ys) + 10:
                    try:
                        _img = _mc.crop_row(SRC, int(key), _poly, _od)
                        return '\\raisebox{-2pt}{\\includegraphics[height=%spt]{%s}}' % (f.get('fnt', FONT), _img)
                    except Exception:
                        pass
    # 3) 空引号单字贴图(原有)
    miss_t = _mc.detect_missing(t)
    if not miss_t:
        return esc_t
    miss_esc = _mc.detect_missing(esc_t)   # esc_t 偏移(替换用)
    if len(miss_t) != len(miss_esc):
        return esc_t   # 不对应(esc 改引号?安全跳过)
    import os
    _od = '/tmp/missing_chars'; os.makedirs(_od, exist_ok=True)
    _fx, _fy, _fw = f.get('x0', 0), f.get('y0', 0), f.get('w', 0)
    _poly = [[_fx, _fy], [_fx + _fw, _fy], [_fx + _fw, _fy + H_BODY], [_fx, _fy + H_BODY]]
    for i in range(len(miss_t) - 1, -1, -1):   # 从后往前替换(避免偏移变)
        try:
            _img = _mc.crop_char(SRC, int(key), _poly, miss_t[i], t, _od)
            esc_t = esc_t[:miss_esc[i]] + '\\raisebox{-2pt}{\\includegraphics[height=%spt]{%s}}' % (f.get('fnt', FONT), _img) + esc_t[miss_esc[i] + 2:]
        except Exception:
            pass   # 剪图失败跳过(保留空引号,不阻断渲染)
    return esc_t
_MARKER_RE = re.compile(r'\$\s*\^?\s*\{?\s*\[[^\]]*\]\s*\}?\s*\$|\[[一二三四五六七八九〇○\d]{1,4}\]')   # 校注标记($ ^{[八五]} $ / 裸[八五])——上标小字,占宽远小于全角,字号标定时先剥掉不计数
def _eff_chars(t, pw=PUNCT_WEIGHT):
    '有效字数:先剥校注标记,CJK 字=1、标点/拉丁/数字=pw(默认0.2)。源标点压缩不计全宽 + 标记是上标小字,纯 len(t) 会偏大→字号偏小'
    return sum(1.0 if ord(c) > 0x2e80 else pw for c in _MARKER_RE.sub('', t))
def detect_regions(rows):
    '按 poly 行高把本页正文/注释候选行分 2 簇(正文高、注释矮),每簇按"区域内满行有效字数中位"标定字号(字少→大、字多→小),钳 [FONT×1.0, FONT×1.4] 防字数过小化。返回 {tag:{font,width}},给每行打 r["region"]。'
    out = {}
    cand = []
    for r in rows:
        if r.get('is_figrow') or not r.get('t'): continue
        t = r['t'].strip(); y0 = r.get('y0', 0); w = r.get('w', 0)
        if PN_RE.fullmatch(t) and y0 > page_px_h * 0.80: continue                       # 页码(底部数字)
        if y0 < page_px_h * 0.06 and len(t) < 30: continue                              # 页眉(顶部)
        if y0 > page_px_h * 0.95 and (w / page_px if page_px else 0) < 0.50: continue    # 水印(极底窄行)
        if t[0] in FN_CIRCLE: continue                                                  # ①脚注(单独渲染,不进区域)
        if r.get('h', 0) < 8: continue
        cand.append(r)
    if not cand:
        return out
    hs = sorted(r['h'] for r in cand)
    med = statistics.median(hs)
    gaps = sorted([(hs[i+1] - hs[i], i) for i in range(len(hs) - 1)], reverse=True)
    two = None
    if gaps and gaps[0][0] >= 0.30 * med:   # 有明显高度间隙 → 尝试双簇(正文满行 vs 注释)
        gi = gaps[0][1]; thr = (hs[gi] + hs[gi+1]) / 2
        lo = [r for r in cand if r['h'] < thr]; hi = [r for r in cand if r['h'] >= thr]
        if lo and hi:
            lo_h = statistics.median(r['h'] for r in lo); hi_h = statistics.median(r['h'] for r in hi)
            lo_eff = statistics.median(_eff_chars(r['t']) for r in lo); hi_eff = statistics.median(_eff_chars(r['t']) for r in hi)
            # 有效双区:矮簇明显更矮(高比<0.70=真字号差)且矮簇字显著更密(≥1.2×,注释字密)——否则是"正文满行 vs 正文段末短行"的伪分裂,归单区
            if lo_h / hi_h < 0.70 and lo_eff >= hi_eff * 1.20:
                two = {'body': hi, 'note': lo}
    groups = two if two else {('body' if med >= H_BODY else 'note'): cand}
    for tag, lines in groups.items():
        ws = [r['w'] for r in lines if r.get('w')]; maxw = max(ws) if ws else 0
        full = [r for r in lines if r['w'] > 0.80 * maxw] if maxw else lines
        width_pt = (statistics.median([r['w'] for r in full]) if full else MEASURE) * 72.0 / DPI
        out[tag] = {'font': _REGION_FONT.get(tag, FONT), 'width': round(max(MEASURE * 0.6, min(width_pt, MEASURE * 1.05)))}   # 字号查全局 _REGION_FONT(不逐页算→相邻页一致)
        for r in lines:
            r['region'] = tag
    return out
def calc_global_fonts():
    '全书预扫描各页分簇(复用 detect_regions 的判据),累积正文/注释满行有效字数 → 全局统一字号(相邻页一致,不逐页跳变)。固定字距模式下字号须让满行(字+压缩标点)装下版心。'
    be, ne = [], []
    for _key in sl:
        _polys = co.get(_key, [])
        _rows = []
        for _i, _t in enumerate(sl[_key]):
            _t = _t.strip()
            if _i < len(_polys) and _polys[_i] and len(_t) > 3:
                _ys = [p[1] for p in _polys[_i]]; _xs = [p[0] for p in _polys[_i]]
                _rows.append({'t': _t, 'x0': min(_xs), 'h': max(_ys)-min(_ys), 'y0': min(_ys), 'w': max(_xs)-min(_xs)})
        detect_regions(_rows)   # 副作用:给 _rows 各行打 r['region'](复用 detect_regions 的分簇判据)
        for _tag in ('body', 'note'):
            _lines = [r for r in _rows if r.get('region') == _tag]
            if not _lines: continue
            _ws = [r['w'] for r in _lines if r.get('w')]; _maxw = max(_ws) if _ws else 0
            _full = [r for r in _lines if r['w'] > 0.80 * _maxw] if _maxw else _lines
            _effs = [_eff_chars(r['t'], 0.0) for r in (_full or _lines)]   # 纯 CJK 计数(标点=0):源标点压缩不计全宽,纯字数算字号更准→字号更大
            if _effs:
                (be if _tag == 'body' else ne).append(statistics.median(_effs))
    bf = round(max(FONT, min(MEASURE / statistics.median(be) * REGION_FONT_SCALE, FONT * 1.4)), 1) if be else round(FONT * 1.3, 1)
    nf = round(max(FONT, min(MEASURE / statistics.median(ne) * REGION_FONT_SCALE, bf * 0.82)), 1) if ne else round(FONT, 1)
    print(f"[区域字号-全局] 正文={bf}pt 注释={nf}pt (按全书满行字数中位,相邻页一致)")
    return {'body': bf, 'note': nf}
_REGION_FONT = {}   # 先定义空(calc_global_fonts 内部 detect_regions 会读它,用 FONT 兜底)
_REGION_FONT = calc_global_fonts() if USE_REGION else {'body': FONT * 1.3, 'note': FONT}
# 正文/注释两类全局字号(PAGE_FONT=1 时用,不按页波动):预扫描全书正文页/注释页满行字数中位 → 统一字号
# (原按页 cw 算致每页字号不同:p11 22.3/p12 19.5/p14 20.3;源应统一,OCR cw 波动是噪声)
if os.environ.get('PAGE_FONT', '') in ('1', 'true', 'True'):
    _BODY_CWS, _NOTE_CWS, _page_cw, _page_h, _page_seq_start, _page_seq_mid = [], [], {}, {}, {}, {}
    for _pk in sl:
        _ppolys = co.get(_pk, []); _ptxts = sl.get(_pk, [])
        _prows = []
        for _pi in range(min(len(_ppolys), len(_ptxts))):
            _pt = _ptxts[_pi].strip()
            if not _pt or not _ppolys[_pi]: continue
            _ys = [p[1] for p in _ppolys[_pi]]; _xs = [p[0] for p in _ppolys[_pi]]
            if min(_ys) < page_px_h * 0.06 and len(_pt) < 30: continue   # 页眉
            if min(_ys) > page_px_h * 0.95: continue   # 页码
            if min(_xs) > page_px * 0.90 or max(_xs) < page_px * 0.10: continue   # 侧栏 aside
            _prows.append({'t': _pt, 'w': max(_xs)-min(_xs), 'h': max(_ys)-min(_ys)})
        _pph = [r['h'] for r in _prows if r['h']]
        _pphm = statistics.median(_pph) if _pph else H_BODY
        _ppws = [r['w'] for r in _prows if r['w']]
        _ppmaxw = max(_ppws) if _ppws else 0
        _ppfull = [len(_MARKER_RE.sub('', r['t']).strip()) for r in _prows if r['w'] > 0.8 * _ppmaxw]
        _ppcw = statistics.median(_ppfull) if _ppfull else cw
        _page_cw[_pk] = _ppcw
        _page_h[_pk] = _pphm
        _ns=0; _nm=0
        for _r in _prows:
            _rt=_r.get('t','')
            if re.match(r'^[〔【[]', _rt): _ns+=1   # 行首〔X)/[X]/【X】=注释序号
            elif re.search(r'[〔【[]([一二三四五六七八九〇\d]{1,4})[】〕\]]', _rt): _nm+=1   # 行中校注标记
        _page_seq_start[_pk]=_ns; _page_seq_mid[_pk]=_nm
        if _pphm > H_BODY * 1.1: _BODY_CWS.append(_ppcw)   # 正文行高大(>1.1×H_BODY)→大字;else 注释(cw 临界不准,如 p5 cw29 行高89 vs p6 cw28 行高63)
        else: _NOTE_CWS.append(_ppcw)
    _BODY_CW = statistics.median(_BODY_CWS) if _BODY_CWS else cw
    _NOTE_CW = statistics.median(_NOTE_CWS) if _NOTE_CWS else cw
    BODY_FONT = round(MEASURE / _BODY_CW, 1) if _BODY_CW else FONT
    NOTE_FONT = round(MEASURE / _NOTE_CW, 1) if _NOTE_CW else FONT
    print(f"[字号·两类] 正文={BODY_FONT}pt(满行{_BODY_CW:.0f}字,{len(_BODY_CWS)}页) 注释={NOTE_FONT}pt(满行{_NOTE_CW:.0f}字,{len(_NOTE_CWS)}页)")
else:
    BODY_FONT = NOTE_FONT = FONT
_prev_pn = None   # 跨页页码(单调性过滤 pn_ocr 用,排除目录页误识)
for key in sorted(sl.keys(), key=int):
    _pp = page_pitch(key) if PER_PAGE_PITCH else None   # 提前算源 pitch(flush 用 bl=_pp,绕过 \linespread 对大字不生效致 pitch 偏小)
    # 图页/乱码页(书影封面等 OCR 只识零星大写/繁体,主体是图片)→ 整页贴源原图
    if SRC and is_garbage_page(sl.get(key, [])) and key not in _figs:   # 有书影带的页走带处理(裁图块+保留上下文字),不整页贴
        gk = str(int(key) + pn_off); pn = pntab.get(gk, '')
        _src_img = render_src_page(key)
        body = [f'\\setcounter{{page}}{{{pn}}}' if pn else '\\thispagestyle{empty}', '\\ClearShipoutPictureFG', '\\ClearShipoutPictureBG']
        if os.environ.get('VERIFY_MARK', '') in ('1', 'true', 'True'):
            body.append('\\AddToShipoutPictureFG{\\put(1,1){\\fontsize{2pt}{2pt}\\selectfont GMPG' + str(int(key)) + 'ZZ}}')
        body.append('\\AddToShipoutPictureBG{\\put(0,0){\\includegraphics[width=\\paperwidth,height=\\paperheight,keepaspectratio]{' + _src_img + '}}}')
        body.append('\\null\\par\\newpage')
        pages_tex.append('\n'.join(body))
        print(f"  p{int(key)+1} 图页→整页贴原图")
        continue
    # 该页的图块(提取贴原图,不整页贴;OCR 文字落在图块内的跳过=图非文字)
    _page_figs = extract_figs(key)
    gk = str(int(key) + pn_off); pn_ext = pntab.get(gk, ''); pn_ocr = ''
    rows = []
    for i in range(len(sl[key])):
        t = sl[key][i].strip()
        if not t: continue
        poly = co.get(key, [None]*len(sl[key]))[i] if i < len(co.get(key, [])) else None
        if poly:
            xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
            y0 = min(ys)
            if PN_RE.fullmatch(t) and y0 > page_px_h * 0.80:
                pn_ocr = re.sub(r'[^\d]', '', t)   # OCR 检测到的页码(底部数字)→ 直接用,无需外部表/offset
            if _page_figs and in_figure(min(xs), y0, max(xs)-min(xs), max(ys)-min(ys), key, t):
                continue   # 落在图块内的 OCR 行 = 图内容(非文字),跳过
            if (min(xs) > page_px * 0.90 or max(xs) < page_px * 0.10) and not PN_RE.fullmatch(t.strip()):
                continue   # 侧栏 running head(古籍卷/篇名边栏,在极左/右页边),跳过——否则同 y 与正文合并撑高行→误判大标题污染。保留纯数字(右对齐的目录页码/页码)
            _is_fc = bool(_fig_titles.get(key)) and in_figcaption(min(xs), y0, max(xs)-min(xs), max(ys)-min(ys), key)
            rows.append({'t': t, 'x0': min(xs), 'h': max(ys)-min(ys), 'y0': y0, 'w': max(xs)-min(xs), 'is_figcaption': _is_fc})
        else:
            rows.append({'t': t, 'x0': 0, 'h': 0, 'y0': 0, 'w': 0})
    # 图块按 y 分行(y 重叠>50%=同行并排书影)→ 作为流内标记按源 y 插入 rows。渲染时 \includegraphics 预留真实图高,图把下方文字推到图后(不再绝对叠加致压字/挤页)
    if _page_figs:
        _fig_rows = []
        for _fp, _bb in sorted(_page_figs, key=lambda fb: (fb[1][1], fb[1][0])):
            _fy0 = _bb[1]*200/LDPI; _fy1 = _bb[3]*200/LDPI
            _placed = False
            for _row in _fig_rows:
                _ov = min(_fy1, _row['y1']) - max(_fy0, _row['y0'])
                if _ov > 0.5 * min(_fy1-_fy0, _row['y1']-_row['y0']):
                    _row['figs'].append((_fp, _bb)); _row['y0'] = min(_row['y0'], _fy0); _row['y1'] = max(_row['y1'], _fy1); _placed = True; break
            if not _placed:
                _fig_rows.append({'y0': _fy0, 'y1': _fy1, 'figs': [(_fp, _bb)]})
        for _row in _fig_rows:
            rows.append({'t': '', 'x0': 0, 'h': 0, 'y0': _row['y0'], 'w': 0, 'is_figrow': True, 'figs': _row['figs']})
    # 合并同一视觉行的 OCR 片段:紧邻(<0.3字高)=拆分同一元素→合并文本;大间隙=分立元素(如"第四部分"+"经典著作选编")→保留多片段各自源位置
    rows.sort(key=lambda r: (r['y0'], r['x0']))
    _m = []
    for r in rows:
        if _m:
            p = _m[-1]
            yov = min(r['y0']+r['h'], p['y0']+p['h']) - max(r['y0'], p['y0'])
            if min(r['h'], p['h']) > 0 and yov > 0.5 * min(r['h'], p['h']):   # y 范围重叠>50% → 同一视觉行
                gap = r['x0'] - (p['x0'] + p['w'])
                if 'frags' not in p: p['frags'] = [(p['t'], p['x0'])]   # 记各片段原始(文字,x0px),渲染时按源 x 绝对定位
                if gap < H_BODY * 0.3:   # 紧邻 = OCR 拆分 -> 文本合并
                    if gap < 0:  # r 在 p 左侧(y 略低但 x 更左) -> 前插保阅读序
                        p['frags'][-1] = (r['t'] + p['frags'][-1][0], r['x0'])
                    else:
                        p['frags'][-1] = (p['frags'][-1][0] + r['t'], p['frags'][-1][1])
                    p['t'] = p['frags'][-1][0]   # 同步更新文本,防单片段渲染丢字
                else:                      # 大间隙 = 分立元素 -> 单独片段
                    p['frags'].append((r['t'], r['x0']))
                nx0 = min(p['x0'], r['x0']); nx1 = max(p['x0']+p['w'], r['x0']+r['w'])
                p['x0'] = nx0; p['w'] = nx1-nx0; p['y0'] = min(p['y0'], r['y0']); p['h'] = max(p['h'], r['h'])
                continue
        _m.append(r)
    rows = _m
    _reg = detect_regions(rows) if USE_REGION else {}   # 区域化:正文/注释分簇 + 每簇字号(字数标定)。空=未开,走原 PAGE_FONT
    if USE_REGION and len(_reg) > 1:
        print(f"  p{int(key)+1} 混合页 区域 " + ' '.join(f"{t}:{d['font']}pt" for t, d in sorted(_reg.items())))
    # 每页字号(PAGE_FONT=1):正文页与注释页字号不同。按"本页每行有效字数"定 PF = 版心/有效字数 → N×PF ≤ 版心(行必落版心内,不溢出)。默认关(wz1 已按全局调好)
    if os.environ.get('PAGE_FONT', '') in ('1', 'true', 'True'):
        # 正文/注释两类全局字号(不按页波动):按预扫描的 spotting cw 判正文(少字大字)/注释(多字小字)
        _phm = _page_h.get(key, H_BODY)
        _pcw = _page_cw.get(key, cw)
        _nss = _page_seq_start.get(key, 0)   # 行首序号(注释页特征)
        _nsm = _page_seq_mid.get(key, 0)     # 行中标记(正文页特征)
        if 27 <= _pcw <= 31:   # 前言
            PF = round(MEASURE / _pcw, 1)
        elif _nss >= 2:   # 行首序号多=注释页(注释跟在正文后,序号在行首)
            PF = round(NOTE_FONT * (_NOTE_CW / max(_pcw, 1)), 1)   # 按满行修正(p15 34字->13.8)
        elif _nsm >= 5:   # 行中标记多=正文页(校注标记 $^{[X]}$ 在行中)
            PF = round(BODY_FONT * (_BODY_CW / max(_pcw, 1)), 1)   # 按满行修正(p14 23字->20.4)
        else:   # 行高判兜底
            PF = round((BODY_FONT if _phm > H_BODY * 1.1 else NOTE_FONT) * ((_BODY_CW if _phm > H_BODY * 1.1 else _NOTE_CW) / max(_pcw, 1)), 1)
        _pm = PF / FONT
    else:
        _pm = 1.0
    PF = round(FONT * _pm, 1)   # 本页正文字号(PAGE_FONT 关时=FONT)
    _pn_ocr_use = _filter_pn_ocr(pn_ocr, _prev_pn)
    pn = _lay_numbers.get(key) or pn_ext or _pn_ocr_use   # layout number > 外部表 > OCR页码(单调性过滤后,弃目录页误识)
    if pn and str(pn).isdigit():
        _prev_pn = int(pn)   # 更新跨页页码(供下页单调性判定)
    elif pn_ocr and not _pn_ocr_use:
        _prev_pn = None   # 突变弃用(目录页误识):重置 prev,允许下页重新起步(序列断裂后恢复连续,否则 prev 卡住致后续全弃用)
    body = [f'\\setcounter{{page}}{{{pn}}}' if pn else '\\thispagestyle{empty}', '\\ClearShipoutPictureFG', '\\ClearShipoutPictureBG']   # 清上页旁注叠加+图页背景(防 \AddToShipoutPictureBG 累积泄漏到后续页)
    if os.environ.get('VERIFY_MARK', '') in ('1', 'true', 'True'):
        # 验证专用源页标记:零流式footprint 的 shipout 叠加,盖在本源页的每张物理页(含溢出续页)左下角。
        # verify_geom.py 按 GMPG<key> 把输出页归组到源页 → 一源页对多输出页 = 溢出。不影响正式输出(默认关)。
        body.append('\\AddToShipoutPictureFG{\\put(1,1){\\fontsize{2pt}{2pt}\\selectfont GMPG' + str(int(key)) + 'ZZ}}')
    # 边栏旁注(竖排):按源 bbox 绝对定位贴回边栏(短栈竖排字符),偶数页书名/奇数页卷篇名
    for _content, _bb in _asides.get(key, []):
        _cx1, _cy1, _cx2, _cy2 = [c*72/LDPI for c in _bb]
        _chars = [c for c in esc(_content) if c.strip()]   # 竖排:每字一行(\shortstack)
        if not _chars: continue
        _vstack = '\\shortstack{' + '\\\\\\\\'.join(_chars) + '}'
        _y_bot = PAGE_H - _cy2   # \put 原点在页左下,旁注 bbox 底
        body.append('\\AddToShipoutPictureFG{\\put(%.1f,%.1f){\\fontsize{%spt}{%spt}\\selectfont %s}}' % (_cx1, _y_bot, FONT_SM, round(FONT_SM*1.6,1), _vstack))   # baselineskip×1.6:竖排字间留空(源 aside 字间有空,默认×1.05 太紧)
    if int(key) in _PAGE_IMG_PAGES:   # 贴图页: 原扫描图 shipout 背景整页铺满(含边距, 不占流不溢出), 估高=页高
        _pos_est[str(int(key))] = PAGE_H
        body.append('\\AddToShipoutPictureBG{\\includegraphics[width=%.1fpt,height=%.1fpt]{%s%d.png}}' % (PAGE_W, PAGE_H, _PAGE_IMG_PREFIX, int(key)))
        body.append('\\thispagestyle{empty}\\par\\null\\newpage'); pages_tex.append('\n'.join(body)); continue
    if not rows:
        body.append('\\null'); body.append('\\par\\newpage'); pages_tex.append('\n'.join(body)); continue
    h_body = H_BODY   # 用全局正文行高(单页全标题时 per-page 中位会失真)
    body_left_px = MARGIN * DPI / 72; body_right_px = (PAGE_W - MARGIN) * DPI / 72; inset = page_px * 0.06
    # 分类
    headers = []; footnotes = []; flow = []   # headers 稍后由 page_header_raw+共识吸附覆写
    in_fn = False   # 脚注续行:①出现后,后续行(不以①开头)也归脚注
    for r in rows:
        if r.get('is_figrow'):
            flow.append({'is_figrow': True, 'figs': r['figs'], 'fnt': FONT, 'is_head': False, 'x0': 0, 'w': 0, 't': '', 'align': 'l', 'y0': r.get('y0', 0)})
            continue
        t, x0, h, y0, w = r['t'], r['x0'], r['h'], r['y0'], r['w']
        is_pn = bool(PN_RE.fullmatch(t)) and (y0 > page_px_h * 0.80 or y0 < page_px_h * 0.10)   # 底部常规页码 + 顶部书眉式页码(源书页码在页眉左右角)
        is_hdr = (not is_pn) and bool(CANON_HDRS) and len(t) < 30 and (y0 < page_px_h * 0.06 or (y0 < page_px_h * 0.10 and _match_canon_hdr(t)))   # 页眉:顶部6% 或 6-10%匹配共识页眉(覆盖wz3 6%边缘 y0==0.06*pph 漏判,排除扉页非共识)。CANON_HDRS 空(无共识页眉的书,如 mgfdmg 词典式页眉凑不成共识)=顶部行是紧凑版心的正文首行,不当页眉(否则正文缺行+页眉区乱拼接)
        w_ratio = w / page_px if page_px else 0
        is_wm = (not is_pn) and (not is_hdr) and y0 > page_px_h * 0.95 and w_ratio < 0.50   # 水印:极底部(页码96%之下)+窄行(<50%页宽)。几何判定,不用关键词(OCR乱识+正文含"理论"会误杀)
        if is_pn: continue                       # 页码 → setcounter 页脚
        if is_wm: continue                       # 水印 → 滤掉
        if is_hdr: continue   # 页眉 → 跳过(稍后用原始行 page_header_raw 合并+共识校正,避免视觉合并乱序)
        is_fn = bool(t) and t[0] in FN_CIRCLE
        if is_fn:
            in_fn = True
            footnotes.append({'t': t, 'w': w}); continue        # 脚注 → 单独渲染(分界线后)
        if in_fn:
            footnotes.append({'t': t, 'w': w}); continue        # 脚注续行(不以①开头但属脚注区)
        core = _heading_core(t)
        is_centered = (x0 > body_left_px + inset) and (x0 + w < body_right_px - inset) and (w_ratio < 0.85)   # 居中元素:左右各内缩 → 书名/作者/[引言]/各节标题(源里都居中,非左对齐)
        _char_w_pt = (w * 72.0 / DPI) / max(len(t.strip()), 1)   # 估测每字 pt 宽(poly 宽/字数):正文≈FONT,大标题≈22pt
        is_big = h > H_BODY * 1.5 and (bool(r.get('frags')) or _char_w_pt > FONT * 1.8)   # 超大行高→大标题;但排除 OCR poly 高度膨胀的长正文行(如参考文献 h~80px 触发>1.8,但字宽≈正文 10pt=非大字)。多片段标题(第X部分+名)或字宽>正文1.8倍才算
        is_tall = h > H_BODY * 1.1   # 比正文高(真标题);前言/版权页居中文字是正文行高→不算标题,按居中正文渲染
        is_subhead = bool(re.match(r'^[（(][一二三四五六七八九十]+[)）]', t.strip())) and w < MEASURE * DPI / 72 * 0.85   # (一)(二) 类三级小标题(行高=正文,靠内容模式识别);加 w_ratio<0.85 排除满宽正文条目(p67 (一)满宽=正文,非标题)
        _sh_pre, _sh_rest = _split_heading(t)
        is_subhead_cn = bool(_sh_pre) and bool(_sh_rest) and _sh_pre[0] in '一二三四五六七八九十' and len(core) >= 2 and len(t.strip()) < 25 and not re.search(r'[。！？]$', t.strip())   # 中文数字序号小标题(无括号,"一X/二X..."行高仅略>正文,is_tall 1.1×卡不住):短行<25+非句号结尾+core>=2 防"一致/一种"等正文"一"字词误伤;_sh_pre[0]中文数字排除"(010)"电话/阿拉伯序号
        is_head_heur = ((bool(core) and len(core) >= 2 and core in toc_map) or is_big or (is_centered and is_tall) or is_subhead or is_subhead_cn or (h > H_BODY and len(t.strip()) < 8 and not re.search(r'[。！？]$', t.strip()))) and not TOC_ENTRY_RE.search(t)   # 启发式(目录条目不算标题);LAYOUT_HEADINGS 开时仅作无 layout 书的兜底;居中短行(h>H_BODY+len<8+非句尾)如'序言'也判标题
        _lay_lvl = _layout_head_level(x0, y0, w, h, key) if USE_LAY_HEAD else None   # layout 版面标签(LAYOUT_HEADINGS=1 时),级别=#数
        is_head = (_lay_lvl is not None) if USE_LAY_HEAD else is_head_heur   # 开关开=layout 独占(层级一致);关=启发式(不影响 wz1 等)
        if is_head and flow and flow[-1].get('is_figrow'):
            is_head = False   # 图块正下方的单行(图说明,常含书名如"《工资、价格和利润》法文版")=非标题 → 降正文(保留居中渲染)
        if is_head:
            _tier = None
            if _TOC_LEVELS:   # 目录规则优先: 编号格式定级别(如 "一、"=part, "1."=section)
                for _tp, _tlvl in _TOC_LEVELS:
                    if _tp.match(t):
                        _tier = _tlvl; break
            if _tier is None:   # 回退: layout 级别→档; 无 layout 走启发式
                _tier = ('part' if _lay_lvl <= 1 else ('title' if _lay_lvl == 2 else 'section')) if _lay_lvl is not None else _head_level(t, is_big)
            _rf = (_reg.get(r.get('region'), {}).get('font', FONT) / FONT) if (USE_REGION and r.get('region')) else _pm   # 区域化:标题按其区域字号比缩放(注释区标题也小);否则本页 pm
            head_size = round(tier_size.get(_tier, FONT) * _rf, 1)
        else:
            head_size = _reg.get(r.get('region'), {}).get('font', PF) if USE_REGION else PF   # 区域化:正文用其区域字号(混合页正文大字/注释小字各拿对的);否则本页 PF
        _is_fc = r.get('is_figcaption')
        if _is_fc: is_head = False; head_size = PF   # 图说明非标题,正文字号
        flow.append({'t': t, 'fnt': head_size, 'is_head': is_head, 'tier': _tier if is_head else None, 'align': 'c' if (is_centered or is_big or _is_fc) else 'l', 'x0': x0, 'w': w, 'frags': r.get('frags'), 'y0': y0, 'region': r.get('region'), 'is_figcaption': _is_fc})
    # 分行目录(wz2):标题行 + 紧随的纯页码行 配对成目录条目(源标题/页码分两行,与 wz1 同行格式不同)。≥5 对=目录页
    _npairs = sum(1 for i in range(len(flow)-1) if (not PN_RE.fullmatch(flow[i]['t'].strip())) and PN_RE.fullmatch(flow[i+1]['t'].strip()))
    if _npairs >= 5:
        _nf = []; _i = 0
        while _i < len(flow):
            _f = flow[_i]
            if _i+1 < len(flow) and PN_RE.fullmatch(flow[_i+1]['t'].strip()) and not PN_RE.fullmatch(_f['t'].strip()):
                _mrg = dict(_f)
                _mrg['frags'] = [(_f['t'].strip(), _f.get('x0', 0)), (flow[_i+1]['t'].strip(), flow[_i+1].get('x0', 0))]   # frags=[(标题,x),(页码,x)] → flush 的 dotfill 渲染
                _mrg['is_head'] = False; _mrg['fnt'] = FONT; _mrg['align'] = 'l'
                _nf.append(_mrg); _i += 2
            else:
                _nf.append(_f); _i += 1
        flow = _nf
    if sum(1 for f in flow if f['is_head']) > 4:   # 一页>4标题 = 列表页(目录/编委/索引),非散文→全降级正文(否则每条标题字号+间距撑爆页)
        for f in flow: f['is_head'] = False; f['fnt'] = FONT
    if sum(1 for f in flow if (TOC_ENTRY_RE.search(f['t']) or (f.get('frags') and any(_t.strip().isdigit() for _t,_ in f['frags'])))) > 5:   # 目录页:多条带页码 → 全降级(章节标题也按 title+dotfill+页码 渲染)
        for f in flow: f['is_head'] = False; f['fnt'] = FONT
    # figrow 正下方的短行(书影版本说明/图说明)→ 居中:LAYJSON figure_title 只覆盖部分页,用"图底 150px 内紧邻短行"兜底
    _last_fy1 = None
    for f in flow:
        if f.get('is_figrow'):
            _last_fy1 = max(fb[1][3]*200/LDPI for fb in f['figs']) if f.get('figs') else None
        elif _last_fy1 is not None and f.get('y0') is not None:
            if 0 < f['y0'] - _last_fy1 < 150 and len(f.get('t', '').strip()) < 30:
                f['is_figcaption'] = True; f['align'] = 'c'; f['is_head'] = False
            _last_fy1 = None   # 只标紧邻首行(后续行是正文,不居中)
    # 页眉:原始行合并(page_header_raw)→ 共识吸附(OCR 拆分/截断/混噪声,如"第一部分"+"历史考"→"第一部分历史考证"、"与党总…读本"→"马克思…读本")
    _hm = page_header_raw(key)
    if _hm and CANON_HDRS:
        import difflib
        _best, _best_r = _hm, 0.0
        for _can in CANON_HDRS:
            _r = difflib.SequenceMatcher(None, _hm, _can).ratio()
            if _r > _best_r: _best_r, _best = _r, _can
        headers = [_best] if _best_r >= 0.6 else []   # 无共识匹配(正文首行 y 6-10% 误入拼接, 如 wz4 p5) → 不渲染页眉, 正文行在 flow 正常渲染
    else:
        headers = []
    is_divider = bool(flow) and all(f['is_head'] for f in flow) and not footnotes   # 仅标题无正文/脚注=分隔页(分标题页)→标题垂直居中(源在页中,非顶部)
    _toc_ref = min((f['x0'] for f in flow if _is_toc_entry(f) and f.get('x0', 0) > 0), default=0)   # 目录条目最左 x0(层级缩进基准)
    _toc_shift = max(0.0, (body_left_px - _toc_ref) * 72.0 / DPI) if _toc_ref > 0 else 0.0   # 目录整体左移量(源目录从 ~52px 起,正文边距 128px → 左移 ~27pt 匹配源绝对位置)
    # 页眉(顶部小字,居中 + 下方分界线)
    for t in headers:
        body.append('{\\fontsize{' + str(FONT_SM) + 'pt}{' + str(round(FONT_SM*1.2,1)) + 'pt}\\selectfont \\centerline{' + esc(t) + '}}')
        body.append('\\vspace{2pt}\\hrule')   # 页眉下方分界线(源 running head 样式)
        if not USE_POS:
            body.append('\\vspace{' + str(HDR_GAP) + 'pt}')   # 页眉→正文间距(非位置还原时加;POSITIONAL 由 top_vs 给,不重复→否则首行下移 HDR_GAP 溢出)
    # 正文流:按 x0 缩进分段 + 逐行固定 + 分类字号
    x0s = sorted(f['x0'] for f in flow)
    body_left = x0s[len(x0s)//4] if x0s else 0
    indent_thr = (FONT * 2) * DPI / 72 * 0.6
    # 标题续行传播:标题未以句末标点收尾 + 下一行非新段缩进 → 续行继承标题(换行的标题续行无(一)标记,否则被当正文字号/字体不一)
    for i in range(len(flow) - 1):
        _c = flow[i]
        if _c['is_head'] and not _c.get('is_cont') and _c['t'].rstrip() and _c['t'].rstrip()[-1] not in TERMINAL:
            _n = flow[i+1]
            if not _n['is_head'] and _n['x0'] <= body_left + indent_thr:
                _n['is_head'] = True; _n['is_cont'] = True; _n['fnt'] = _c['fnt']; _n['align'] = 'l'   # is_cont=续行,不触发新段(与标题同段,行间无空隙)
    # ── 位置还原溢出控制:预扫描本页位置化总高,超版心 → 先压空白(顶偏移+段间隙),压光再收 strut ──
    # 位置还原按源 y 落位(顶偏移 + 段间隙)保留结构性留白 → 消除底部空白;但内容+留白超版心会溢成多页(wz1 73页)。
    # 此预扫描用与发射同一 para-start 规则估总高,得两个缩放因子:_pos_gscale(空白)、_pos_sscale(strut,仅万不得已)。
    _pos_gscale = 1.0; _pos_sscale = 1.0; _top_vs = 0.0
    if USE_POS and flow and not is_divider and not USE_REGION:
        _fy = next((f['y0'] for f in flow if f.get('y0', 0) > 0), 0)   # 含 figrow(书影带可能是页首元素,排除会误取下文 y0→top_vs 巨大溢出)
        _hdr_h = (FONT_SM * 1.2 + 2.4) if headers else 0   # 有页眉:页眉行高+vspace2+hrule0.4,减去防正文下移溢出
        _top_vs = max(0.0, _fy * 72.0 / DPI - 12.0 - _hdr_h) if _fy else 0.0   # 源首行 y − 版心顶距(top=12pt)
        _strut_h = 0.0; _gap_h = 0.0; _pv = None
        for f in flow:
            if f.get('is_figrow'):
                if f['figs']:
                    _fy0 = min(fb[1][1]*200/LDPI for fb in f['figs'])
                    if _pv is not None and _fy0 > _pv:
                        _g = (_fy0 - _pv) * 72.0 / DPI - round(FONT*1.2, 1)
                        _gap_h += max(0.0, min(_g, FONT*2.5))   # figrow 落位 vspace(与渲染一致,防估高漏算致 ratio 失准溢出)
                    _gap_h += max((fb[1][3]-fb[1][1])*72/LDPI for fb in f['figs'])
                    _pv = max(fb[1][3]*200/LDPI for fb in f['figs'])   # 图底作下段基准(与渲染 prev_y 一致)
                continue
            _isps = (f['x0'] > body_left + indent_thr and not f['is_head']) or (f['is_head'] and not f.get('is_cont'))
            if _isps and _pv is not None and f.get('y0', 0) > _pv:
                _g = (f.get('y0', 0) - _pv) * 72.0 / DPI - round(f['fnt']*1.2, 1)
                _gap_h += max(0.0, min(_g, f['fnt']*2.5))   # 段间隙(与 flush 同口径:钳到 fnt×2.5)
            _strut_h += round(f['fnt'] * 1.34 * LINESPREAD, 1)   # 逐行 advance≈fnt×1.34×全局 linespread(保守估:略高于实测→防溢出;残余过压由 POS_FILL 目标回填)
            _pv = f.get('y0', _pv)
        _fn_h = (9 + len(footnotes) * round(FONT_SM*1.2, 1)) if footnotes else 0.0   # 脚注:hrule≈9 + 每行 FONT_SM×1.2×linespread
        _TEXTH = PAGE_H - 42
        _total = _top_vs + _strut_h + _gap_h + _fn_h
        _pos_est[str(int(key))] = round(_total, 1)   # 导出原始估高(pass1)
        _total *= _pos_ratio.get(str(int(key)), 1.0)  # pass2:按实测/估比校正每页方差
        # 保守估高偏大 ~13%(strut/baselineskip max 交互),故填充目标 _FILL 设 >1:把估高压到 _FILL×版心,
        # 实高≈_FILL/1.13×版心。_FILL≈1.08 → 实高≈0.95×版心:不溢出且底部空白最小。POS_FILL 可调。
        _FILL = float(os.environ.get('POS_FILL', '1.08'))
        _cap = _TEXTH * _FILL
        if _total > _cap:
            _white = _top_vs + _gap_h; _need = _total - _cap
            if _white > 0 and _need < _white:
                _pos_gscale = max(0.0, (_white - _need) / _white)   # 压空白(顶偏移+段间隙)即可收进一页
            else:
                _pos_gscale = 0.0   # 空白压光仍超 → 再按比例收 strut(下限 0.62,防字挤成一坨)
                _rem = _cap - _fn_h
                if _strut_h > 0:
                    _pos_sscale = max(0.62, min(1.0, _rem / _strut_h))
    if is_divider:
        body.append('\\vspace*{\\fill}')   # 分隔页:顶部填充(标题垂直居中)
    elif USE_POS and _top_vs * _pos_gscale > 1:
        body.append('\\vspace*{%.1fpt}' % (_top_vs * _pos_gscale))   # 首行落到源 y0(按 gscale 收缩防溢)
    para = []
    prev_y = [None]   # 页级上一行 y0(跨段位置还原:段间 \vspace 用)
    def flush():
        if not para: return
        if USE_POS and prev_y[0] is not None and para[0].get('y0', 0) > prev_y[0] and not os.environ.get('REGION_LAYOUT','') in ('1','true','True'):
            _gap = (para[0]['y0'] - prev_y[0]) * 72.0 / DPI - round(para[0]['fnt']*1.2, 1)   # 段间位置还原(非区域化):距上段末行的源 y 间隙(\\ 只给 fnt×1.2,补差值)。REGION_LAYOUT 时跳过——strut 已给均匀行距=源,源段间无额外间隙,再加 vspace 会叠加→溢页
            _gap = max(0.0, min(_gap, para[0]['fnt']*2.5)) * _pos_gscale   # ×gscale:溢出页按比例收段间隙
            if _gap > 0.5: body.append('\\vspace{%.1fpt}' % _gap)
        if (not USE_POS) and any(f['is_head'] for f in para):
            body.append('\\vspace{' + str(HEAD_GAP) + 'pt}')   # 标题段前间距(源标题上下都有空隙);位置还原时改由源 y 增量给出,不加
        for j, f in enumerate(para):
            prev_y[0] = f.get('y0', prev_y[0])   # 更新页级上一行 y0(跨段位置还原用)
            fnt = f['fnt']
            if USE_POS:
                if _pp and PF > 13:   # 大字(wz2 15.7):\linespread 对 makebox 大字不生效→bl=源pitch 直接设 baselineskip;小字(wz1 10.1)走原 \linespread(pitch=strut+墨高 凑巧准)
                    bl = round((_pp - 2.0) * _pos_sscale, 1)   # -2pt 补偿:大字 pitch=strut+墨高 比 bl 大2pt(实测输出pitch=源+2),减2让 pitch=源(消溢出)
                else:
                    bl = round(fnt * 1.34 * _pos_sscale, 1)
                _strut = '\\rule{0pt}{%.1fpt}' % round(bl - fnt*0.13, 1)   # strut 定 makebox 行盒高度→hbox 堆叠 pitch=strut+descender≈bl。校准:\rule{0pt}{31}→pitch34。\\[X]/\par 在逐行 group 失效或破坏分页,strut 是唯一可靠旋钮
            else:
                bl = round(fnt*1.2, 1); _strut = ''
            brk = ' \\\\' if j < len(para)-1 else ''
            if f['is_head']:
                frags = f.get('frags')
                if frags and len(frags) > 1:
                    # 多片段标题连续排版:拼接全部片段文本,按 align 走普通标题渲染。
                    # 旧:各片段按源 x 绝对定位(\rlap);片段 x0 < 版心左被 max(0,·) 钳到 0,片段间
                    # 相对间距被压缩 -> 渲染字号下片段宽超出被压的间距 -> 同行字符重叠
                    # (wz3 p40 章标题 28pt / p47 两片同钳 0 完全重叠 83pt)。
                    # 章标题("第三章"+"周代之“封建”")本就是连续文字,逐片定位价值低;
                    # 表格行(帝号|光武…)拼接丢列位但不重叠(列位还原属表格支持,留待后续)。
                    _ht = ''.join(_txt for _txt, _ in frags)
                    _nat_w = sum((1.0 if ord(c) > 0x2e80 else 0.5) for c in _ht) * fnt   # 自然宽(CJK 1em/拉丁 0.5em)
                    if _nat_w >= 0.85 * MEASURE:   # 拼接后超宽(表格行多片拼接)-> makebox[s] 收缩齐版心,防溢出/折行变高
                        body.append('{\\fontsize{' + str(fnt) + 'pt}{' + str(bl) + 'pt}\\selectfont \\makebox[\\textwidth][s]{{\\CJKfamily{' + _hf(f) + '}' + _esc_heading(_ht) + '}}' + brk + '}')
                    elif f.get('align') == 'c':   # 源里居中 -> 居中(读源位置,非统一规则)
                        body.append('{\\fontsize{' + str(fnt) + 'pt}{' + str(bl) + 'pt}\\selectfont \\makebox[\\textwidth][c]{{\\CJKfamily{' + _hf(f) + '}' + _esc_heading(_ht) + '}}' + brk + '}')
                    else:                       # 源里左对齐 -> 左对齐
                        body.append('{\\fontsize{' + str(fnt) + 'pt}{' + str(bl) + 'pt}\\selectfont {\\CJKfamily{' + _hf(f) + '}' + _esc_heading(_ht) + '}' + brk + '}')
                elif f.get('align') == 'c':   # 源里居中 → 居中(读源位置,非统一规则)
                    body.append('{\\fontsize{' + str(fnt) + 'pt}{' + str(bl) + 'pt}\\selectfont \\makebox[\\textwidth][c]{{\\CJKfamily{' + _hf(f) + '}' + _esc_heading(f['t']) + '}}' + brk + '}')
                else:                       # 源里左对齐 → 左对齐
                    body.append('{\\fontsize{' + str(fnt) + 'pt}{' + str(bl) + 'pt}\\selectfont {\\CJKfamily{' + _hf(f) + '}' + _esc_heading(f['t']) + '}' + brk + '}')
                continue
            if f.get('is_figcaption'):   # 图说明(figure_title block)→ 居中,不查行宽(短行也居中)
                body.append('{\\fontsize{' + str(fnt) + 'pt}{' + str(bl) + 'pt}\\selectfont \\makebox[\\textwidth][c]{' + _strut + _esc_with_missing(f['t'], f, key) + '}' + brk + '}')
                continue
            _wr = (f['w'] / page_px) if page_px else 1   # 行宽占版心比
            if (not f['is_head']) and f.get('align') == 'c' and f.get('region') != 'note' and _wr >= 0.70:   # 仅"正文区满宽居中段"(前言/版权,w_ratio≥0.70)居中;**注释区行永不居中**(注释应左对齐ragged),短行(<0.70)也跳过→makebox[l]。修注释段末/中行被 is_centered 误判居中
                _cnat = sum((1.0 if ord(c) > 0x2e80 else 0.5) for c in f['t']) * fnt   # 自然字宽
                _cmb = 'c' if _cnat < MEASURE * 0.90 else 's'   # 仅明显窄于版心(≤90%)才居中;否则 [s] 收缩——[c] 居中长内容会两侧均等溢出(x0 负、x1 超)
                body.append('{\\fontsize{' + str(fnt) + 'pt}{' + str(bl) + 'pt}\\selectfont \\makebox[\\textwidth][' + _cmb + ']{' + _esc_with_missing(f['t'], f, key) + '}' + brk + '}')
                continue
            _toc = None
            if not f['is_head']:
                _m = re.match(r'^(.*\S)\s*[.·…．]{2,}\s*(\d{1,4})\s*$', f['t'])   # 形态①:一行"title……页码"
                if _m: _toc = (_m.group(1), _m.group(2))
                elif f.get('frags'):   # 形态②:title 片段 + 页码片段(分开的同 y poly,合并后成多片段)
                    _nums = [_t for _t, _ in f['frags'] if _t.strip().isdigit()]
                    _titles = [_t for _t, _ in f['frags'] if not _t.strip().isdigit()]
                    if _nums and _titles: _toc = (' '.join(_titles), _nums[-1])
            if _toc and sum(1.0 if ord(c) > 0x2e80 else 0.5 for c in _toc[0]) * fnt > MEASURE * 0.75:
                _toc = None   # "标题"过长(>75%版心)→ 非真目录条目(内容页被 ……数字 误检),改走正文 makebox[s](收缩不溢出);真目录标题短(篇名)不受影响
            if _toc:   # 目录条目:整体左移 _toc_shift(匹配源绝对宽度)+ 按源 x0 相对缩进 + 标题 + 点引导(\dotfill)+ 页码右
                _ind = '\\hspace*{' + ('%.1f' % max(0, (f.get('x0', 0) - _toc_ref) * 72 / DPI)) + 'pt}'
                if _toc_shift > 0.5:
                    _pre = '\\noindent\\hspace*{-' + ('%.1f' % _toc_shift) + 'pt}'; _box = '\\makebox[\\dimexpr\\textwidth+' + ('%.1f' % _toc_shift) + 'pt\\relax]'
                else:
                    _pre = ''; _box = '\\makebox[\\textwidth]'
                body.append('{\\fontsize{' + str(fnt) + 'pt}{' + str(bl) + 'pt}\\selectfont ' + _pre + _box + '{' + _strut + _ind + esc(_toc[0]) + '\\,\\dotfill\\,' + esc(_toc[1]) + '}' + brk + '}')
                continue
            # 缩进按源 x0 还原(弃写死 2em): 段首行缩进=源 x0-版心左, 段内行悬挂缩进同源。
            # 容差 6px(=0.5字@200dpi, OCR x0 噪声)内归 0; 短行自然留白右侧, 与源书一致。
            _ix_px = f.get('x0', 0) - body_left
            if _ix_px < 6:
                _ix_px = 0
            indent = ('\\hspace*{%.1fpt}' % (_ix_px * 72.0 / DPI)) if _ix_px > 0 else ''
            _nat_w = sum((1.0 if ord(c) > 0x2e80 else 0.5) for c in f['t']) * fnt   # 自然字宽(CJK 1em/拉丁 0.5em);用字数非 poly 宽(多片段合并会撑大 poly→短标题误判满行被拉伸)
            _grid = os.environ.get('GRID_PITCH', '') in ('1', 'true', 'True')   # 固定字距(旧 GRID_PITCH 开关,makebox[l]);USE_REGION 改用 CJKglue plus 0em 实现等价固定字距(见前导 _cjk_glue)
            if _nat_w >= 0.85 * MEASURE:
                _mb = 'l' if _grid else 's'   # 默认 makebox[s];固定字距靠 CJKglue plus 0em(不拉伸)实现——满行收缩齐右、短行自然 ragged,字距恒定≈字号
                body.append('{\\fontsize{' + str(fnt) + 'pt}{' + str(bl) + 'pt}\\selectfont \\makebox[\\textwidth][' + _mb + ']{' + _strut + indent + _esc_with_missing(f['t'], f, key) + '}' + brk + '}')
            else:   # 短行/段末 → makebox[l](左对齐满宽框,与满行同构 hbox);不套 makebox 会让纯文本行与 makebox 行纵向堆叠行距不同→段末短行处行距塌缩
                body.append('{\\fontsize{' + str(fnt) + 'pt}{' + str(bl) + 'pt}\\selectfont \\makebox[\\textwidth][l]{' + _strut + indent + _esc_with_missing(f['t'], f, key) + '}' + brk + '}')
        body.append('\\par')
        if (not USE_POS) and any(f['is_head'] for f in para):   # 标题段后加间距(匹配源);位置还原时由源 y 增量给
            body.append('\\vspace{' + str(HEAD_GAP) + 'pt}')
    _i = 0
    while _i < len(flow):
        f = flow[_i]
        if f.get('is_figrow'):
            if para: flush(); para = []
            # 位置还原:figrow 落到源 y0(补与上段末行的 y 间隙);图占真实图高,后续文字按图底 y 续位。
            # 不补/不更新 prev_y → 下段 \vspace 按源 y 差跨过图高重复计入 → 巨大空白溢出多页
            if USE_POS and prev_y[0] is not None:
                _fy0 = min(fb[1][1]*200/LDPI for fb in f['figs'])
                _g = (_fy0 - prev_y[0]) * 72.0 / DPI - round(FONT*1.2, 1)
                if _g > 0.5: body.append('\\vspace{%.1fpt}' % (_g * _pos_gscale))
            _fr = sorted(f['figs'], key=lambda fb: fb[1][0])   # 按 x 排:并排书影从左到右
            _parts = []; _cursor = MARGIN   # x 光标(pt),从版心左起
            for _fp, _bb in _fr:
                _fx1, _fx2 = _bb[0]*72/LDPI, _bb[2]*72/LDPI
                _fs = max(0.85, min(_pos_sscale, _pos_ratio.get(str(int(key)), 1.0), _pos_gscale))   # 溢出页图随 strut/ratio/gscale 缩(内容满页 gscale<1 时图也压,消1行微溢;不溢页均=1 不缩)
                _W0 = (_fx2 - _fx1) * _fs; _H0 = (_bb[3]-_bb[1])*72/LDPI * _fs
                _left = max(MARGIN, _fx1)   # 源左缘(≥版心左)
                _gap = max(0.0, _left - _cursor)
                _parts.append('\\hspace*{%.1fpt}\\includegraphics[width=%.1fpt,height=%.1fpt]{%s}' % (_gap, _W0, _H0, _fp))
                _cursor = _left + _W0
            body.append('\\par\\noindent' + ''.join(_parts) + '\\par')   # 一行内并排,预留最大图高(图把后续文字推到图后)
            prev_y[0] = max(fb[1][3]*200/LDPI for fb in f['figs'])   # 图底源 y(200dpi)作下段基准,防 \vspace 跨图高重复
            _i += 1; continue
        f['is_para_start'] = f['x0'] > body_left + indent_thr and not f['is_head']
        _en_ratio = sum(1 for c in f['t'] if ord(c) < 128 and c.isalpha()) / max(len(f['t']), 1)
        if (not f['is_head']) and _en_ratio > 0.4:   # 英文为主的行(参考文献等):合成可换行段落,不套 makebox,允许 xelatex 断词(避免溢出)
            if para: flush(); para = []
            _en = [f['t']]; _en_y = f.get('y0', 0)
            while _i+1 < len(flow) and not flow[_i+1]['is_head'] and (sum(1 for c in flow[_i+1]['t'] if ord(c) < 128 and c.isalpha()) / max(len(flow[_i+1]['t']), 1)) > 0.4:
                _i += 1; _en.append(flow[_i]['t']); _en_y = flow[_i].get('y0', _en_y)
            _bl = round(f['fnt']*1.2, 1)
            body.append('{\\fontsize{' + str(f['fnt']) + 'pt}{' + str(_bl) + 'pt}\\selectfont ' + ' '.join(esc(_t) for _t in _en) + '}\\par')
            prev_y[0] = _en_y   # 英文段末行 y0(位置还原基准,防下段/figrow \vspace 跨英文段重复计入→溢出)
            _i += 1; continue
        if (f['is_para_start'] or (f['is_head'] and not f.get('is_cont'))) and para:
            flush(); para = []
        para.append(f)
        _i += 1
    flush()
    if is_divider:
        body.append('\\vspace*{\\fill}')   # 分隔页底部填充(配合顶部 fill → 标题垂直居中)
    # 脚注区(分界线 + 小字,匹配源;满行也两端对齐)
    if footnotes:
        body.append('\\vspace{6pt}\\hrule width 0.3\\textwidth\\vspace{3pt}')
        fbl = round(FONT_SM*1.2, 1)
        body.append('{\\linespread{1}\\fontsize{' + str(FONT_SM) + 'pt}{' + str(fbl) + 'pt}\\selectfont')   # 脚注区整体 \\linespread{1},防全局行距倍数撑大脚注 pitch
        for ft in footnotes:
            inner = esc(ft['t'])
            _fnat = sum((1.0 if ord(c) > 0x2e80 else 0.5) for c in ft['t']) * FONT_SM
            if _fnat >= 0.85 * MEASURE:
                body.append('\\renewcommand{\\CJKglue}{\\hskip 0.25em plus 1em}\\makebox[\\textwidth][s]{' + inner + '}\\par')
            else:
                body.append(inner + '\\par')
        body.append('}')   # 关闭脚注组,恢复正文 \\linespread
    body.append('\\par\\newpage')
    page_tex = '\n'.join(body)
    # ── 改动1:本页行距基准 _lsb —— PER_PAGE_PITCH 时按源实测 pitch 反推,否则全局 LINESPREAD ──
    _lsb = LINESPREAD
    _pp_applied = False   # 本页是否用了 per-page 源 pitch(用了则不可收缩——收缩会扭曲源行距)
    if PER_PAGE_PITCH and _pp:   # _pp 已在主循环开头算(提前给 flush 用 bl=_pp)
        _lsb = round(_pp / (PF * 1.2), 3)   # _lsb 供预扫描参考(实际 bl=_pp 已含 pitch)
        _pp_applied = True
    if flow and not is_divider:   # 密集页(目录/名单/索引,行数超版)自适应行距:源本就排得密,按比例收紧 linespread
        _fig_h = sum((max((fb[1][3]-fb[1][1])*72/LDPI for fb in f['figs']) if f['figs'] else 0) for f in flow if f.get('is_figrow'))   # 图块预留高度(固定,不随 linespread 缩)
        fixed = (HDR_GAP if headers else 0) + sum(2*HEAD_GAP for f in flow if f['is_head']) + (12 if footnotes else 0) + _fig_h   # 不随 linespread 缩放的固定间距(标题前后各一个 HEAD_GAP)+ 图高
        scalable = (FONT_SM*1.2*_lsb if headers else 0) + sum(f['fnt']*1.2*_lsb for f in flow if not f.get('is_figrow')) + (len(footnotes)*FONT_SM*1.2 if footnotes else 0)   # 随 linespread 缩放的行高(图块除外)
        est_h = fixed + scalable
        TEXT_H = PAGE_H - 42   # top12 + bottom30
        ls_final = 1.0 if (_pp_applied and PF > 13) else _lsb   # 大字 pp: bl=源pitch 已含行距,linespread=1;小字(wz1)走 \linespread
        if (not _pp_applied) and _npairs < 5 and est_h > TEXT_H * 0.95 and scalable > 0:   # 目录页(_npairs>=5)不收缩(行距一致,跟 p7 同);仅密集非目录页收紧
            ls_final = max(1.0, _lsb * (TEXT_H*0.85 - fixed) / scalable)   # 解 ls 使 fixed+scalable×(ls/_lsb)=TEXT_H×0.85;留15%余量防 xelatex 实际行高(~10%)超估
        # _pp_applied(per-page 源 pitch 已生效)时跳过 uniform-pitch 收缩:POSITIONAL 按源 y 落位 + ratio 表已控制填充,
        # 此处按 nlines×pitch 估高会误判密集页溢出→把源 pitch(19.3)压成 12-15→pitch 达标率崩。
        # 非 per-page 路径(全局 LINESPREAD)保留收缩:密集页收紧行距防 split(ratio 表 + 收缩协同)。
        # 行距根因(最小实验铁证): \linespread 包裹时若未设字号,页面 baselineskip=默认10pt×1.2×ls,
        # 而 ls 按本书字号 PF 反推 → 误差因子 10/PF (wz4: 10/7.7=1.29 → 12.8→16.6; wz1 凑巧 PF≈10 故准)。
        # 修: 包裹时先声明 \fontsize{PF}, 页面 baselineskip=PF×1.2×ls=源 pitch。
        _pf_fs = '{\\fontsize{' + str(PF) + 'pt}{' + str(round(PF * 1.2, 1)) + 'pt}'
        if PER_PAGE_PITCH:
            page_tex = _pf_fs + '\\linespread{' + ('%.3f' % ls_final) + '}\\selectfont ' + page_tex + '}'   # 按页 pitch:每页都包(基准=源 pitch,溢出再收紧)
        elif ls_final < _lsb:
            page_tex = _pf_fs + '\\linespread{' + ('%.3f' % ls_final) + '}\\selectfont ' + page_tex + '}'   # 原行为:仅溢出页收紧
    pages_tex.append(page_tex)

if os.environ.get('POS_EST_LOG'):
    json.dump(_pos_est, open(os.environ['POS_EST_LOG'], 'w'))   # 导出各源页位置化估高,供 fit_positional 两趟校准

latex = build_latex('geom', PAGE_W, PAGE_H, MARGIN, USE_REGION, LINESPREAD, pages_tex)
tex_path = '/tmp/seg2_line.tex'
open(tex_path, 'w', encoding='utf-8').write(latex)
subprocess.run(['xelatex', '-interaction=nonstopmode', '-output-directory=/tmp', tex_path], capture_output=True)
_src = '/tmp/seg2_line.pdf'
if os.path.exists(_src):
    if os.path.abspath(_src) != os.path.abspath(OUT): shutil.copy(_src, OUT)
    print(f"[完成] {OUT}")
else:
    print("[失败] xelatex 未生成 PDF,查 /tmp/seg2_line.log")
