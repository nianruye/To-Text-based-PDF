#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_vert.py — 竖排繁体书还原 v1 (流式竖排)
用法: /usr/bin/python3 src/pipelines/build_vert.py <lines.json> <coords.json> <out.pdf> [src.pdf]
env:  VERT_PAGES=3-12    只输出指定页(1-based, 如 '3-12' 或 '3,5')
      VERT_SKIP_SPECIAL=1  跳过书眉/页码/边注(默认1)
管线: OCR(2x=144dpi px) -> 参数拟合(tarticle 竖排) -> uplatex+dvipdfmx -> PDF
"""
import json, sys, os, subprocess, statistics, re

SL = sys.argv[1]; CO = sys.argv[2]; OUT = sys.argv[3]
SRC = sys.argv[4] if len(sys.argv) > 4 else None
PAGES_ENV = os.environ.get('VERT_PAGES', '')
TMP = os.environ.get('VERT_TMP', '/opt/test/tmp_vert/run')
os.makedirs(TMP, exist_ok=True)

sl = json.load(open(SL)); co = json.load(open(CO))
keys = sorted(sl.keys(), key=int)

# ---------- 1) 参数拟合 ----------
def col_stats(k):
    """每列: (x0,x1,y0,y1,t)"""
    out = []
    for t, p in zip(sl.get(k, []), co.get(k, [])):
        if not p: continue
        xs = [q[0] for q in p]; ys = [q[1] for q in p]
        out.append((min(xs), max(xs), min(ys), max(ys), t.strip()))
    return out

all_rows = {k: col_stats(k) for k in keys}

def is_body_col(x0, x1, y0, y1, t):
    """v1.1 列分类(wz6 规则): 正文/标题进流; 书眉/页码(x0>1100 且短)与左侧小字边注(x0<100 且小字号)排除"""
    h = y1 - y0; L = len(t)
    if h < 300 or L < 2: return False
    if x0 > 1100 and h < 300: return False       # 书眉/页码(最右列短行)
    if x0 < 100 and h / L < 55: return False      # 左侧小字边注
    return True

# 正文列统计(is_body_col 过滤)
body_h = []; body_fs = []; body_w = []
body_x0 = []; body_top = []; body_right = []
for k in keys:
    for x0,x1,y0,y1,t in all_rows[k]:
        if is_body_col(x0,x1,y0,y1,t):
            h = y1-y0
            body_h.append(h); body_fs.append(h/len(t)); body_w.append(x1-x0)
            body_x0.append(x0); body_top.append(y0); body_right.append(x1)

H_col = statistics.median(body_h) if body_h else 1780          # 列高 px
FS_px = statistics.median(body_fs) if body_fs else 35.5*2       # 字距 px
TOP = statistics.median(body_top) if body_top else 600          # 天头 px
RIGHT = max(body_right) if body_right else 1180                 # 版心右缘 px

# 列距(相邻列 x0 差的中位)
pitches = []
for k in keys[:40]:
    rows_b = [r for r in all_rows[k] if is_body_col(*r)]
    xs = sorted(set(r[0] for r in rows_b), reverse=True)
    for a, b in zip(xs, xs[1:]):
        if 60 < a-b < 160: pitches.append(a-b)
PITCH_px = statistics.median(pitches) if pitches else 94

# 每页列数
ncols = [sum(1 for r in all_rows[k] if is_body_col(*r)) for k in keys]
NCOL = int(statistics.median([n for n in ncols if n >= 5]) if any(n>=5 for n in ncols) else 11)

FS = round(FS_px/2.0, 1)          # pt
PITCH = round(PITCH_px/2.0, 1)    # pt
HCOL = round(H_col/2.0, 1)
TTOP = round(TOP/2.0, 1)
RIGHT_p = RIGHT/2.0
TW_pt = HCOL                       # textwidth = 列高
TH_pt = round(NCOL*PITCH + 12, 1)  # textheight = 列区横向容量(最大列数×列距+余量)
TM_pt = round(TTOP - 102, 1)       # topmargin = 天头-102
OM_pt = round(RIGHT_p - TH_pt - 70, 1)  # 右缘定位拟合: 右缘 = 70 + om + textheight (e10c/exp13/bv 三点回归)
page_w = 595.3; page_h = 1244.1
# 页面尺寸: 从 src.pdf 精确取
if SRC:
    import fitz
    d = fitz.open(SRC)
    page_w = round(d[0].rect.width, 1); page_h = round(d[0].rect.height, 1)

print('[竖排拟合] 字号%.1fpt 列距%.1fpt 列高%.1fpt 天头%.1fpt 右缘%.1fpt 列数%d 页%.1f×%.1f' % (
    FS, PITCH, HCOL, TTOP, RIGHT_p, NCOL, page_w, page_h))

# ---------- 2) 每页内容 ----------
def page_tex(k):
    """一页: 正文列(从右到左)逐列渲染, \\par 强制断列(列断点=源书)"""
    rows = [r for r in all_rows[k] if is_body_col(*r)]
    rows.sort(key=lambda r: -r[0])   # x0 降序 = 右到左
    segs = []
    for x0, x1, y0, y1, t in rows:
        cw = max(1.0, x1-x0)               # 字宽 px
        step = (y1-y0)/max(1, len(t))      # 字步进 px
        fmax = PITCH * 0.92                # 字号上限: 字宽不得超列距(防侵占邻列)
        if step > 1.3 * cw:                # 字距宽(如大标题): 字号≈步进/2(封顶), 字间1全角空格
            f = round(max(20.0, min(fmax, step/2.0)), 1)
            t = '\u3000'.join(list(t))
        else:
            f = round(max(20.0, min(fmax, step/2.0)), 1)
        t = t.replace('%', r'\%').replace('#', r'\#').replace('&', r'\&').replace('_', r'\_')
        segs.append('{\\fontsize{%spt}{%spt}\\selectfont %s\\par}' % (f, PITCH, t))
    return '\n'.join(segs)

sel = []
if PAGES_ENV:
    for part in PAGES_ENV.split(','):
        if '-' in part:
            a, b = part.split('-'); sel += list(range(int(a), int(b)+1))
        else:
            sel.append(int(part))
    sel = [s for s in sel if 1 <= s <= len(keys)]
else:
    sel = list(range(1, len(keys)+1))

w = page_w * 1.00375; h = page_h * 1.00375   # bp 换算
preamble = r'''\documentclass[10pt]{tarticle}
\usepackage[unicode]{pxchfon}
\setminchofont[3]{NotoSerifCJK-Regular.ttc}
\setgothicfont[3]{NotoSansCJK-Regular.ttc}
\setlength{\parindent}{0pt}
\setlength{\textwidth}{%(TW)spt}
\setlength{\textheight}{%(TH)spt}
\setlength{\topmargin}{%(TM)spt}
\setlength{\oddsidemargin}{%(OM)spt}
\setlength{\evensidemargin}{%(OM)spt}
\special{papersize=%(PW)spt,%(PH)spt}
\pagestyle{empty}
\begin{document}
''' % {'TW': TW_pt, 'TH': TH_pt, 'TM': TM_pt, 'OM': OM_pt, 'PW': round(w,1), 'PH': round(h,1)}

parts = [preamble]
for i, pg in enumerate(sel):
    k = keys[pg-1]
    parts.append('%% ===== 源第 %d 页 (key %s) =====' % (pg, k))
    body = page_tex(k)
    parts.append('\\null' if not body else body)
    parts.append('\\newpage')
parts.append('\\end{document}\n')

tex_path = os.path.join(TMP, 'vert.tex')
open(tex_path, 'w', encoding='utf8').write('\n'.join(parts))
print('[tex] %s (页 %s)' % (tex_path, sel))

# ---------- 3) 编译 ----------
r = subprocess.run(['uplatex', '-interaction=nonstopmode', 'vert.tex'], cwd=TMP, capture_output=True, text=True)
r2 = subprocess.run(['dvipdfmx', 'vert.dvi'], cwd=TMP, capture_output=True, text=True)
dvi_pdf = os.path.join(TMP, 'vert.pdf')
if os.path.exists(dvi_pdf):
    os.replace(dvi_pdf, OUT)
    print('[完成] %s' % OUT)
else:
    print('[失败] uplatex rc=%s dvipdfmx rc=%s' % (r.returncode, r2.returncode))
    print(r.stdout[-1500:])
