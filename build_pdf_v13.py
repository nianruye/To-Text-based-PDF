#!/usr/bin/env python3
"""Build PDF v13 — use PaddleOCR markdown for structure detection.
MD provides heading levels (##, ###, ####), footnotes, page breaks.
Spotting provides coordinates. Combine both for better layout.
"""
import json, os, re, subprocess, sys, statistics, fitz

SRC_PDF = sys.argv[1] if len(sys.argv) > 1 else "/opt/test/优化前.pdf"
OUT_PDF = sys.argv[2] if len(sys.argv) > 2 else "/opt/test/最终版_v13.pdf"
SPOTTING_LINES = sys.argv[3] if len(sys.argv) > 3 else "/opt/test/spotting_lines.json"
SPOTTING_COORDS = sys.argv[4] if len(sys.argv) > 4 else "/opt/test/spotting_coords.json"
MARKDOWN_FILE = sys.argv[5] if len(sys.argv) > 5 else ""

FN_CIRCLE = set('①②③④⑤⑥⑦⑧⑨⑩')

def clean_text(text):
    return text.lstrip("‖‖| \t")

def escape_tex(text):
    for char, repl in [('\\', r'\textbackslash{}'), ('{', r'\{'), ('}', r'\}'),
                       ('&', r'\&'), ('%', r'\%'), ('#', r'\#'),
                       ('$', r'\$'), ('_', r'\_'), ('~', r'\~{}'), ('^', r'\^{}')]:
        text = text.replace(char, repl)
    return text

def is_page_number(t):
    s = t.strip()
    if re.match(r'^[·•‧]?\s*\d{1,4}\s*[·•‧]?$', s): return True
    return bool(re.match(r'^\d{1,4}$', s)) and len(s) <= 4

def is_footnote_start(t):
    return bool(t.strip()) and t.strip()[0] in FN_CIRCLE

# ── Parse markdown to extract structure ──
def parse_markdown_structure(md_path):
    """Extract heading levels and footnote markers from PaddleOCR markdown."""
    headings = set()   # set of (heading_text, level)
    fn_markers = set()  # set of footnote reference texts
    body_lines = set()

    if not md_path or not os.path.exists(md_path):
        return headings, fn_markers

    with open(md_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip()
            # Heading: ##, ###, ####
            m = re.match(r'^(#{1,6})\s+(.+)$', line)
            if m:
                level = len(m.group(1))
                text = m.group(2).strip()
                # Remove footnote markers from heading text
                text = re.sub(r'\$\s*\^\{[^}]+\}\s*\$', '', text).strip()
                headings.add((text, level))
                continue
            # Footnote reference: $ ^{①} $
            fn_refs = re.findall(r'\$\s*\^\{([^}]+)\}\s*\$', line)
            for fn in fn_refs:
                fn_markers.add(fn)
            # Body text (skip empty lines)
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('---'):
                body_lines.add(stripped[:50])  # first 50 chars for matching

    return headings, fn_markers

def is_heading_by_md(text, headings_set):
    """Check if text matches a markdown heading (fuzzy match)."""
    clean = re.sub(r'\$\s*\^\{[^}]+\}\s*\$', '', text).strip()
    # Normalize: remove spaces, normalize quotes
    norm = re.sub(r'\s+', '', clean)
    norm = norm.replace('“', '“').replace('”', '”')
    norm = norm.replace('‘', '‘').replace('’', '’')
    norm = norm.replace('＂', '＂')
    for h_text, level in headings_set:
        h_norm = re.sub(r'\s+', '', h_text)
        h_norm = h_norm.replace('“', '“').replace('”', '”')
        if norm == h_norm:
            return level
        if len(norm) > 8 and len(h_norm) > 8:
            shorter = norm if len(norm) < len(h_norm) else h_norm
            longer = h_norm if len(norm) < len(h_norm) else norm
            if len(shorter) / len(longer) > 0.7 and shorter in longer:
                return level
    return 0

# ── Main ──
doc = fitz.open(SRC_PDF)
PW_PT = doc[0].rect.width; PH_PT = doc[0].rect.height
doc.close()
PW_MM = round(PW_PT * 0.3528, 0); PH_MM = round(PH_PT * 0.3528, 0)

spot_lines = json.load(open(SPOTTING_LINES))
spot_coords = json.load(open(SPOTTING_COORDS))
for k in spot_lines:
    spot_lines[k] = [clean_text(l) for l in spot_lines[k]]

# Compute SCALE from image dimensions
tmp_doc = fitz.open(SRC_PDF)
first_img = tmp_doc[0].get_images(full=True)
img_w = first_img[0][2] if first_img else 0
SCALE = img_w / PW_PT if img_w > 0 else 2.0
tmp_doc.close()

page_width_px = max(max(pt[0] for pt in poly) for polys in spot_coords.values() for poly in polys if poly)

# ── Parse markdown structure ──
md_headings, md_fns = parse_markdown_structure(MARKDOWN_FILE)
print(f"MD headings found: {len(md_headings)}")
if md_headings:
    for h, lv in sorted(md_headings, key=lambda x: x[1])[:5]:
        print(f"  {'#'*lv} {h[:50]}")

# ── Source-derived detection thresholds ──
# Scan all OCR lines, classify as heading (matches MD) or body, collect geometry.
# All thresholds below are computed from THIS document's actual data.
_src_heading_hs = []      # px heights of heading lines
_src_heading_widths = []  # px widths of heading lines
_src_body_hs = []         # px heights of body lines
_src_body_widths = []     # px widths of body lines (excl. footnotes/page-nums)
for k in spot_lines:
    for i, line in enumerate(spot_lines[k]):
        t = line.strip()
        if not t or len(t) < 3: continue
        polys = spot_coords.get(k, [])
        if i >= len(polys) or not polys[i]: continue
        xs = [p[0] for p in polys[i]]; ys = [p[1] for p in polys[i]]
        xl, xr, yt, yb = min(xs), max(xs), min(ys), max(ys)
        w = xr - xl; h = yb - yt
        # Skip right-aligned headers, footnotes, page numbers, watermark
        if xl > page_width_px * 0.4: continue
        if is_footnote_start(t) or is_page_number(t): continue
        if is_heading_by_md(t, md_headings):
            _src_heading_hs.append(h)
            _src_heading_widths.append(w)
        elif w > 200 and len(t) > 5:
            _src_body_hs.append(h)
            _src_body_widths.append(w)

# Coordinate-based heading ratio threshold — fully source-derived:
# 1. heading_median_h / body_median_h = how much taller headings are
# 2. body local-ratio P95 = OCR noise level (lines taller than this are NOT noise)
# Take the max: if headings are similar height to body, rely on noise floor.
# This document: heading/body = 1.024, noise_p95 = 1.097 → threshold = 1.10
_src_body_local_ratios = []  # h / local_avg for each body line
for k in spot_lines:
    c = spot_coords.get(k, [])
    for i, line in enumerate(spot_lines[k]):
        t = line.strip()
        if not t or len(t) < 5: continue
        if i >= len(c) or not c[i]: continue
        xs = [p[0] for p in c[i]]; ys = [p[1] for p in c[i]]
        if min(xs) > page_width_px * 0.4: continue
        if is_footnote_start(t) or is_page_number(t): continue
        if is_heading_by_md(t, md_headings): continue
        h = max(ys) - min(ys)
        body_h = []
        for j in range(max(0,i-5), min(len(spot_lines[k]), i+6)):
            if j == i: continue
            tj = spot_lines[k][j].strip()
            if not tj or len(tj) < 3: continue
            if j >= len(c) or not c[j]: continue
            yj = [p[1] for p in c[j]]; xj = [p[0] for p in c[j]]
            if min(xj) > page_width_px * 0.4: continue
            body_h.append(max(yj) - min(yj))
        if body_h:
            _src_body_local_ratios.append(h / (sum(body_h)/len(body_h)))
if _src_body_local_ratios:
    _src_body_local_ratios.sort()
    _noise_p95 = _src_body_local_ratios[int(len(_src_body_local_ratios) * 0.95)]
else:
    _noise_p95 = 1.07
_heading_body_ratio = statistics.median(_src_heading_hs) / statistics.median(_src_body_hs) if _src_heading_hs and _src_body_hs else 1.07
COORD_HEADING_RATIO = max(_heading_body_ratio, _noise_p95)
COORD_HEADING_RATIO = round(COORD_HEADING_RATIO, 3)
# Min heading width: below min actual heading width (rejects narrow body continuation lines)
MIN_HEADING_WIDTH = (min(_src_heading_widths) * 0.8) if _src_heading_widths else page_width_px * 0.35
print(f"Source-derived thresholds: heading_ratio={COORD_HEADING_RATIO:.3f} min_heading_w={MIN_HEADING_WIDTH:.0f}px")

# ── Dynamic parameters ──
BODY_LEFT = 0
body_x0s = []
for k in spot_lines:
    for i, line in enumerate(spot_lines[k]):
        t = line.strip()
        if not t or is_page_number(t) or is_footnote_start(t): continue
        polys = spot_coords.get(k, [])
        if i >= len(polys) or not polys[i]: continue
        xl = min(p[0] for p in polys[i])
        if xl > page_width_px * 0.4: continue
        body_x0s.append(xl)
body_x0s.sort()
BODY_LEFT = body_x0s[len(body_x0s)//4] if body_x0s else 60

all_line_h = []
for k in spot_lines:
    for i, line in enumerate(spot_lines[k]):
        t = line.strip()
        if not t or len(t) < 5: continue
        polys = spot_coords.get(k, [])
        if i >= len(polys) or not polys[i]: continue
        if min(p[0] for p in polys[i]) > page_width_px * 0.4: continue
        all_line_h.append((max(p[1] for p in polys[i]) - min(p[1] for p in polys[i])) / SCALE)
all_line_h.sort()
FONT_SIZE = round(all_line_h[len(all_line_h)//10] * 0.75) if all_line_h else 12
# Font size = \linewidth ÷ max_body_chars, so longest body lines fit without wrapping
max_cjk = 20
body_cjk_list = []
for k in spot_lines:
    for i, line in enumerate(spot_lines[k]):
        t = line.strip()
        if not t or len(t) < 5: continue
        if is_page_number(t) or is_footnote_start(t): continue
        polys = spot_coords.get(k, [])
        if i < len(polys) and polys[i] and min(p[0] for p in polys[i]) > page_width_px * 0.4: continue
        cjk = sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalpha())
        if cjk > 10: body_cjk_list.append(cjk)
        if cjk > max_cjk: max_cjk = cjk
AVAIL_WIDTH = PW_PT - 2 * (BODY_LEFT / SCALE)  # \linewidth in pt
FONT_SIZE = max(10, min(14, round(AVAIL_WIDTH / max_cjk)))
# Stretch threshold: 85% of median body CJK count → only genuine full-width lines get \makebox[s]
if body_cjk_list:
    body_cjk_list.sort()
    _median_cjk = body_cjk_list[len(body_cjk_list)//2]
    STRETCH_THRESHOLD = round(_median_cjk * 0.85)
else:
    STRETCH_THRESHOLD = 25

body_widths_pt = []
for k in spot_lines:
    for i, line in enumerate(spot_lines[k]):
        t = line.strip()
        if not t or is_page_number(t) or is_footnote_start(t): continue
        polys = spot_coords.get(k, [])
        if i >= len(polys) or not polys[i]: continue
        xs = [p[0] for p in polys[i]]
        if min(xs) > page_width_px * 0.4: continue
        body_widths_pt.append((max(xs) - min(xs)) / SCALE)
body_widths_pt.sort()
TARGET = int(body_widths_pt[int(len(body_widths_pt)*0.9)]) if body_widths_pt else 300
TARGET = max(TARGET, int(PW_PT * 0.70))

norm = [x for x in body_x0s if abs(x - BODY_LEFT) < 30]
indented = [x for x in body_x0s if x > BODY_LEFT + 40]
norm_center = statistics.median(norm) if norm else BODY_LEFT
indented_center = statistics.median(indented) if indented else BODY_LEFT + 50
INDENT_THRESHOLD_PX = max(20, (indented_center - norm_center) * 0.5)
INDENT_PT = INDENT_THRESHOLD_PX / SCALE

# Stretch from source body area: body_height ÷ (lines × base_skip)
BASE_SKIP = FONT_SIZE * 1.2
body_area_stretches = []
for k in spot_lines:
    body_ys = []
    for i, line in enumerate(spot_lines[k]):
        t = line.strip()
        if not t or is_page_number(t) or is_footnote_start(t): continue
        polys = spot_coords.get(k, [])
        if i >= len(polys) or not polys[i]: continue
        if min(p[0] for p in polys[i]) > page_width_px * 0.4: continue
        body_ys.append(max(p[1] for p in polys[i]) / SCALE)
    if len(body_ys) > 2:
        h = max(body_ys) - min(body_ys) + FONT_SIZE
        s = h / (len(body_ys) * BASE_SKIP)
        body_area_stretches.append(s)
BODY_STRETCH = round(statistics.median(body_area_stretches), 2) if body_area_stretches else 1.5
BODY_STRETCH = max(1.4, min(1.8, BODY_STRETCH))

width_spread = (body_widths_pt[int(len(body_widths_pt)*0.9)] - body_widths_pt[len(body_widths_pt)//10]) / FONT_SIZE if len(body_widths_pt)>10 else 0.1
CJK_STRETCH = 0  # high stretch so short lines can fill target width

MARGIN_PT = 20  # tight margins for max text width
TARGET = PW_PT - 2 * MARGIN_PT  # \linewidth = target
MARGIN_MM = round(MARGIN_PT * 0.3528, 1)

# Page number: find the bottom-most short number or ·N· on each page
page_numbers = {}
for key in spot_lines:
    lines = spot_lines[key]; polys = spot_coords.get(key, [])
    candidates = []
    for i, l in enumerate(lines):
        t = l.strip()
        if not t or len(t) > 8: continue
        if i >= len(polys) or not polys[i]: continue
        y = min(p[1] for p in polys[i]) / SCALE
        if y < PH_PT * 0.55: continue  # only bottom half
        m = re.match(r'[·•‧]?\s*(\d{1,4})\s*[·•‧]?', t)
        if m:
            candidates.append((y, m.group(1)))
        elif t.isdigit() and len(t) <= 4:
            candidates.append((y, t))
    if candidates:
        candidates.sort(key=lambda x: -x[0])  # lowest on page first
        page_numbers[key] = candidates[0][1]
START_PAGE = 1
if page_numbers:
    vals = sorted(int(v) for v in page_numbers.values())
    print(f"Page numbers: {vals[:3]}...{vals[-3:]}")
START_PAGE = int(list(page_numbers.values())[0]) if page_numbers else 1

print(f"FONT={FONT_SIZE}pt TARGET={TARGET}pt INDENT={INDENT_THRESHOLD_PX:.0f}px STRETCH={BODY_STRETCH}")

# ── Auto-detect headers per page ──
# For each page, record: header text, position (left/right), line height (pt)
# MERGE_GAP_PT: header lines with inter-line gap < this (in pt) are considered
# a split header and merged. Derived from median header line height.
_hdr_h_pts = []
for key in sorted(spot_lines.keys(), key=int):
    polys_h = spot_coords.get(key, [])
    for i, l in enumerate(spot_lines[key]):
        t = l.strip()
        if not t or is_page_number(t) or is_footnote_start(t): continue
        if i >= len(polys_h) or not polys_h[i]: continue
        ys = [p[1] for p in polys_h[i]]; xs = [p[0] for p in polys_h[i]]
        if min(ys) / SCALE > 50: break
        if min(xs) > page_width_px * 0.4 or len(t) < 30:
            _hdr_h_pts.append((max(ys) - min(ys)) / SCALE)
            break
MERGE_GAP_PT = round(statistics.median(_hdr_h_pts) * 0.8) if _hdr_h_pts else 8
MERGE_GAP_PX = MERGE_GAP_PT * SCALE  # convert to pixels for raw coordinate comparison

# Preliminary header region threshold: top ~12% of page (scales with page size)
# Refined later as HDR_REGION_Y after computing header gaps
_HDR_REGION_INITIAL = PH_PT * 0.12

page_headers = {}  # key → {'text': str, 'pos': 'left'|'right', 'h_pt': float}
for key in sorted(spot_lines.keys(), key=int):
    page_lines = spot_lines[key]; polys = spot_coords.get(key, [])
    header_region_lines = []  # collect consecutive header-region lines for merging
    for i, l in enumerate(page_lines):
        t = l.strip()
        if not t or is_page_number(t) or is_footnote_start(t): continue
        if i >= len(polys) or not polys[i]: continue
        xs = [p[0] for p in polys[i]]; ys = [p[1] for p in polys[i]]
        x_left = min(xs); y_top = min(ys) / SCALE
        y_bot = max(ys) / SCALE
        h_pt = (max(ys) - min(ys)) / SCALE
        if y_top > _HDR_REGION_INITIAL: break
        pos = 'right' if x_left > page_width_px * 0.4 else 'left'
        # Header-like: at header position (right side) or narrower than typical body
        # Derived: use median of heading widths as boundary (headers are narrower than body)
        _hdr_like_max_w = statistics.median(_src_heading_widths) if _src_heading_widths else PW_PT * 0.6
        line_w_px = max(xs) - min(xs)
        is_hdr_like = (x_left > page_width_px * 0.4) or line_w_px < _hdr_like_max_w
        if header_region_lines:
            prev = header_region_lines[-1]
            # Gap between previous header bottom and this line top (in px)
            gap_px = min(ys) - prev['y_bot_raw']
            # Only merge if gap < dynamic threshold and also header-like
            if gap_px > MERGE_GAP_PX or not is_hdr_like:
                break
        elif not is_hdr_like:
            break
        header_region_lines.append({'text': t, 'pos': pos, 'h_pt': h_pt,
                                    'x_left': x_left, 'idx': i, 'y_bot_raw': max(ys)})
        if len(header_region_lines) >= 3: break  # max 3 header lines to merge
    if header_region_lines:
        # Merge split headers: if multiple lines in header region, combine them
        merged_text = ''.join(hl['text'] for hl in header_region_lines)
        # Use the position from the first line (determines left/right alignment)
        h0 = header_region_lines[0]
        page_headers[key] = {'text': merged_text, 'pos': h0['pos'], 'h_pt': h0['h_pt'],
                             'merge_indices': set(hl['idx'] for hl in header_region_lines)}

# Defaults
right_hdr = {}; left_hdr = {}
for k, v in page_headers.items():
    if v['pos'] == 'right': right_hdr[v['text']] = right_hdr.get(v['text'], 0) + 1
    else: left_hdr[v['text']] = left_hdr.get(v['text'], 0) + 1
DEFAULT_RIGHT_HDR = max(right_hdr, key=right_hdr.get) if right_hdr else ''
DEFAULT_LEFT_HDR = max(left_hdr, key=left_hdr.get) if left_hdr else ''
RIGHT_HDR_H = statistics.median([v['h_pt'] for v in page_headers.values() if v['pos']=='right']) if right_hdr else 8
LEFT_HDR_H = statistics.median([v['h_pt'] for v in page_headers.values() if v['pos']=='left']) if left_hdr else 9

# Header gaps: distance from header bottom to body text start, per position
right_gaps = []; left_gaps = []
for key in sorted(spot_lines.keys(), key=int):
    page_lines = spot_lines[key]; polys = spot_coords.get(key, [])
    hdr_info = page_headers.get(key)
    if not hdr_info: continue
    hdr_bot = body_y = None
    for i, l in enumerate(page_lines):
        t = l.strip()
        if not t or is_page_number(t) or is_footnote_start(t): continue
        if i >= len(polys) or not polys[i]: continue
        xs = [p[0] for p in polys[i]]; ys = [p[1] for p in polys[i]]
        xl, yt, yb = min(xs)/SCALE, min(ys)/SCALE, max(ys)/SCALE
        if hdr_bot is None and (xl > page_width_px*0.3 or (i==0 and len(t)<30 and yt<_HDR_REGION_INITIAL)):
            hdr_bot = yb; continue
        if hdr_bot and body_y is None and xl < page_width_px*0.4:
            body_y = yt; break
    if hdr_bot and body_y:
        gap = body_y - hdr_bot
        if hdr_info['pos'] == 'right': right_gaps.append(gap)
        else: left_gaps.append(gap)
RIGHT_HDR_GAP = statistics.median(right_gaps) if right_gaps else 38
LEFT_HDR_GAP = statistics.median(left_gaps) if left_gaps else 40
# Min header gap floor: half a body line height (dynamic, scales with font size)
HDR_GAP_MIN = round(FONT_SIZE * 0.6) if FONT_SIZE else 6

# Refined header region threshold: header bottom + 1.5× gap, derived from source
_hdr_bot_pts = [v['h_pt'] for v in page_headers.values()]
_hdr_gap_approx = statistics.median(right_gaps + left_gaps) if (right_gaps or left_gaps) else 38
HDR_REGION_Y = (statistics.median(_hdr_bot_pts) if _hdr_bot_pts else 10) + _hdr_gap_approx * 1.5
print(f"Headers: RIGHT='{DEFAULT_RIGHT_HDR}' h={RIGHT_HDR_H:.1f}pt  LEFT='{DEFAULT_LEFT_HDR}' h={LEFT_HDR_H:.1f}pt")

# ── Per-page footnote gap from source ──
page_fn_gap = {}  # key → gap in pt between body end and footnote start
for key in sorted(spot_lines.keys(), key=int):
    page_lines = spot_lines[key]; polys = spot_coords.get(key, [])
    fn_start = None
    for i, l in enumerate(page_lines):
        t = l.strip()
        if t and is_footnote_start(t):
            fn_start = i; break
    if fn_start is None: continue
    # Body last line y
    body_last_y = None
    for i in range(fn_start - 1, -1, -1):
        t = page_lines[i].strip()
        if not t or len(t) <= 3 or is_page_number(t): continue
        if i < len(polys) and polys[i]:
            body_last_y = max(p[1] for p in polys[i]) / SCALE
        break
    # Footnote first line y
    fn_first_y = None
    if fn_start < len(polys) and polys[fn_start]:
        fn_first_y = min(p[1] for p in polys[fn_start]) / SCALE
    if body_last_y and fn_first_y:
        page_fn_gap[key] = max(10, fn_first_y - body_last_y)

FN_GAP_DEFAULT = statistics.median(list(page_fn_gap.values())) if page_fn_gap else 18
print(f"Footnote gaps: per-page={len(page_fn_gap)} pages, default={FN_GAP_DEFAULT:.0f}pt")

# ── Dynamic footnote params from source ──
fn_line_heights = []   # line height in pt
fn_line_gaps = []      # baseline-to-baseline gap in pt
fn_marker_xs = []      # ① lines x_left in px
fn_cont_xs = []        # continuation lines x_left in px
body_left_xs = []      # body text x_left in px
fn_char_densities = [] # pt per CJK char

for key in sorted(spot_lines.keys(), key=int):
    page_lines = spot_lines[key]; polys = spot_coords.get(key, [])
    fn_start = None
    for i, l in enumerate(page_lines):
        t = l.strip()
        if t and is_footnote_start(t):
            fn_start = i; break
    if fn_start is None: continue

    # Body text left x (first few body lines)
    for i in range(len(page_lines)):
        t = page_lines[i].strip()
        if not t or len(t) < 5: continue
        if i >= len(polys) or not polys[i]: continue
        poly = polys[i]
        xl = min(p[0] for p in poly)
        if xl > page_width_px * 0.5: continue
        if not is_page_number(t) and not is_footnote_start(t):
            body_left_xs.append(xl)
            break

    prev_yb = None
    for i in range(fn_start, len(page_lines)):
        t = page_lines[i].strip()
        if not t: continue
        if is_page_number(t): continue
        if '学习理论' in t: continue
        if i >= len(polys) or not polys[i]: continue
        poly = polys[i]
        xl = min(p[0] for p in poly)
        yt = min(p[1] for p in poly) / SCALE
        yb = max(p[1] for p in poly) / SCALE
        h = yb - yt
        w = (max(p[0] for p in poly) - min(p[0] for p in poly)) / SCALE

        fn_line_heights.append(h)
        if is_footnote_start(t):
            fn_marker_xs.append(xl)
        else:
            fn_cont_xs.append(xl)
        if prev_yb is not None:
            fn_line_gaps.append(yt - prev_yb)
        prev_yb = yb

        cjk = sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalpha())
        if cjk > 15:
            fn_char_densities.append(w / cjk)

# Compute dynamic params
FN_FONT_SIZE = round(statistics.median(fn_line_heights) * 0.78) if fn_line_heights else 6
FN_BASELINE = round((statistics.median(fn_line_heights) + statistics.median(fn_line_gaps)) if fn_line_heights and fn_line_gaps else FN_FONT_SIZE * 1.5)

body_x_median = statistics.median(body_left_xs) if body_left_xs else BODY_LEFT
marker_x_median = statistics.median(fn_marker_xs) if fn_marker_xs else body_x_median + 40
FN_INDENT_PX = max(0, marker_x_median - body_x_median)
FN_INDENT_PT = round(FN_INDENT_PX / SCALE)

if fn_char_densities:
    fn_em = statistics.median(fn_char_densities)
    fn_glue_em = max(0.02, (fn_em - FN_FONT_SIZE) / FN_FONT_SIZE)
    FN_CJK_GLUE_BASE = f"{fn_glue_em:.2f}"
    FN_CJK_GLUE = f"{fn_glue_em:.2f}em plus {fn_glue_em:.2f}em"
else:
    FN_CJK_GLUE_BASE = "0.08"
    FN_CJK_GLUE = "0.08em plus 0.08em"

# Footnote stretch threshold: justify full-width footnote lines like body text
fn_cjk_list = []
for k in spot_lines:
    in_fn_block = False
    for i, line in enumerate(spot_lines[k]):
        t = line.strip()
        if not t: continue
        if is_footnote_start(t):
            in_fn_block = True
        elif is_page_number(t):
            in_fn_block = False; continue
        if not in_fn_block: continue
        cjk = sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalpha())
        if cjk > 10: fn_cjk_list.append(cjk)
if fn_cjk_list:
    fn_cjk_list.sort()
    FN_STRETCH_THRESHOLD = round(fn_cjk_list[len(fn_cjk_list)//2] * 0.85)
else:
    FN_STRETCH_THRESHOLD = 24

print(f"Footnote params: font={FN_FONT_SIZE}pt baseline={FN_BASELINE}pt indent={FN_INDENT_PT}pt CJKglue={FN_CJK_GLUE}")

# ── LaTeX header ──
TOP_MARGIN_MM = 8.5
header = f"""\\documentclass[{int(FONT_SIZE)}pt]{{article}}
\\usepackage{{xeCJK}}
\\usepackage[top={TOP_MARGIN_MM}mm, bottom=15mm, left={MARGIN_MM}mm, right={MARGIN_MM}mm, paperwidth={PW_MM:.0f}mm, paperheight={PH_MM:.0f}mm]{{geometry}}
\\usepackage{{setspace}}
\\usepackage{{fancyhdr}}
\\setmainfont{{Noto Serif CJK SC}}
\\setCJKmainfont{{Noto Serif CJK SC}}
\\setCJKsansfont{{Noto Sans CJK SC}}
\\setCJKfamilyfont{{kaiti}}{{AR PL KaitiM GB}}
\\xeCJKsetup{{PunctStyle=kaiming}}
\\setlength{{\\parindent}}{{0pt}}
\\linespread{{{BODY_STRETCH}}}
\\setlength{{\\footskip}}{{30pt}}
\\setcounter{{page}}{{{START_PAGE}}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\fancyfoot[C]{{\\large\\thepage}}
\\renewcommand{{\\headrulewidth}}{{0pt}}
\\renewcommand{{\\CJKglue}}{{\\hskip 0pt plus 0.6em minus 0em}}
\\raggedbottom
\\emergencystretch=2em
\\tolerance=500
\\begin{{document}}
"""

# ── Detect watermark/footer lines (same text on >20% pages, fuzzy match) ──
def fuzzy_key(text):
    """Normalize text for fuzzy matching."""
    t = text.strip().replace('"', '').replace('"', '').replace('"', '')
    t = t.replace(''', '').replace(''', '')
    t = t.replace(' ', '')
    return t[:20]  # first 20 chars as key

# Watermarks: short repeated text in lower half, appearing on >25% pages
watermark_texts = set()
text_bottom_count = {}
for k in spot_lines:
    seen_this_page = set()
    polys = spot_coords.get(k, [])
    for i, l in enumerate(spot_lines[k]):
        t = l.strip()
        if not t or len(t) < 3 or len(t) > 30: continue
        if is_page_number(t) or is_footnote_start(t): continue
        if i < len(polys) and polys[i]:
            y = max(p[1] for p in polys[i]) / SCALE
            if y < PH_PT * 0.55: continue
        if t in seen_this_page: continue
        seen_this_page.add(t)
        text_bottom_count[t] = text_bottom_count.get(t, 0) + 1
for t, cnt in text_bottom_count.items():
    if cnt >= len(spot_lines) * 0.25:
        watermark_texts.add(t)
if watermark_texts:
    print(f"Watermark filter: {len(watermark_texts)} patterns")

# ── Render ──
all_tex = []
prev_body_text = None

for key in sorted(spot_lines.keys(), key=int):
    lines = spot_lines[key]; polys = spot_coords.get(key, [])
    result = []

    this_body = ''.join(l.strip() for l in lines if l.strip() and not is_page_number(l.strip()) and not is_footnote_start(l.strip()))
    is_duplicate = (prev_body_text == this_body) and len(this_body) > 50
    prev_body_text = this_body
    if is_duplicate:
        result.append('\\addtocounter{page}{-1}')

    # Set page number to source value
    src_pn = page_numbers.get(key, '')
    if src_pn:
        result.append('\\setcounter{page}{' + src_pn + '}')

    fn_rule_added = False; in_fn = False
    body_buf = []

    def flush_body():
        if not body_buf: return
        paras = []; cur = []
        for item in body_buf:
            if item['indent'] and cur:
                paras.append(cur); cur = []
            cur.append(item)
        if cur: paras.append(cur)
        for para in paras:
            for idx, item in enumerate(para):
                prefix = '\\hspace*{2em}' if item['indent'] else ''
                txt = item['text']
                cjk_count = item['cjk']
                # Only stretch genuine full-width lines (CJK > STRETCH_THRESHOLD).
                # Short/partial lines like "科学性"的理论实质集中概括为：" (CJK≈22)
                # should keep natural spacing, not be stretched to \linewidth.
                if cjk_count > STRETCH_THRESHOLD:
                    result.append('\\makebox[\\linewidth][s]{' + prefix + escape_tex(txt) + '}\\par')
                else:
                    result.append(prefix + escape_tex(txt) + '\\par')
        body_buf.clear()

    skip_lines = set()
    # Get merged header indices for this page — skip those lines in render loop
    hdr_merge = page_headers.get(key, {}).get('merge_indices', set())
    for i in range(len(lines)):
        if i in skip_lines: continue
        # Skip lines that are part of a merged header (already rendered with first line)
        if i in hdr_merge and i > min(hdr_merge): continue
        t = lines[i].strip()
        if t in watermark_texts: continue
        t = lines[i].strip()
        if not t or t in watermark_texts: continue
        if i < len(polys) and polys[i]:
            xs = [p[0] for p in polys[i]]; ys = [p[1] for p in polys[i]]
            x_left, y_pt = min(xs), min(ys)/SCALE
            # Bottom 10% of page, not a page number → likely watermark/footer
            if y_pt > PH_PT * 0.88 and not is_page_number(t) and not is_footnote_start(t):
                continue
        else:
            x_left, y_pt = 0, 99

        if is_page_number(t): continue

        # ── Footnote continuation (must be BEFORE heading detection) ──
        if in_fn and not is_footnote_start(t):
            cjk_fn = sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalpha())
            if cjk_fn > FN_STRETCH_THRESHOLD:
                result.append('\\makebox[\\linewidth][s]{' + escape_tex(t) + '}\\par')
            else:
                result.append(escape_tex(t) + '\\par')
            continue

        # ── MD-based heading detection ──
        md_level = is_heading_by_md(t, md_headings)
        is_header = (x_left > page_width_px * 0.4) or (i == 0 and len(t) < 25 and y_pt < 50)

        # Coordinate-based heading: line height > 1.15x body avg + short + not at page top
        coord_heading = False
        if i < len(polys) and polys[i] and not is_header and not is_footnote_start(t):
            ys_h = [p[1] for p in polys[i]]
            xs_h = [p[0] for p in polys[i]]
            h = max(ys_h) - min(ys_h)
            line_width_px = max(xs_h) - min(xs_h)
            # Get body avg height from surrounding lines
            body_hs = []
            for j in range(max(0,i-5), min(len(lines), i+6)):
                if j == i: continue
                tj = lines[j].strip()
                if not tj or len(tj) < 5: continue
                if j >= len(polys) or not polys[j]: continue
                if min(p[0] for p in polys[j]) > page_width_px * 0.4: continue
                body_hs.append(max(p[1] for p in polys[j]) - min(p[1] for p in polys[j]))
            if body_hs:
                body_h_avg = sum(body_hs) / len(body_hs)
                ratio = h / body_h_avg if body_h_avg > 0 else 1.0
                # Reject narrow short lines at body-left position (e.g. continuation "命的。"③)
                # Real headings span wider; narrow short lines at body-left are body continuations
                min_heading_width = MIN_HEADING_WIDTH
                if (ratio > COORD_HEADING_RATIO and 3 < len(t) < 28 and y_pt > HDR_REGION_Y
                        and line_width_px > min_heading_width):
                    coord_heading = True
                    md_level = max(md_level, 2)  # treat as ## level

        # Missing header: if first body line is y>50, add default header from source position
        if i == 0 and y_pt > HDR_REGION_Y and not is_header:
            hdr_info = page_headers.get(key)
            if hdr_info:
                hdr_text = hdr_info['text']
                hdr_pos = hdr_info['pos']
            else:
                if int(key) % 2 == 0:
                    hdr_text = DEFAULT_RIGHT_HDR; hdr_pos = 'right'
                else:
                    hdr_text = DEFAULT_LEFT_HDR; hdr_pos = 'left'
            hdr_gap = RIGHT_HDR_GAP if hdr_pos == 'right' else LEFT_HDR_GAP
            hdr_size = round(RIGHT_HDR_H * 0.75) if hdr_pos == 'right' else round(LEFT_HDR_H * 0.75)
            if hdr_text:
                if hdr_pos == 'right':
                    result.append('{\\fontsize{' + str(hdr_size) + 'pt}{1em}\\selectfont\\hfill ' + escape_tex(hdr_text) + '}\\par\\normalsize')
                else:
                    result.append('{\\fontsize{' + str(hdr_size) + 'pt}{1em}\\selectfont ' + escape_tex(hdr_text) + '}\\par\\normalsize')
                result.append('\\vspace{' + str(max(int(hdr_gap), HDR_GAP_MIN)) + 'pt}')

        is_running_hdr = is_header and not md_level

        if md_level >= 2 or is_running_hdr or coord_heading:
            flush_body()
            if in_fn: result.append('}'); in_fn = False

            # Compute height ratio for THIS heading line
            heading_ratio = 1.0
            if i < len(polys) and polys[i]:
                ys_h = [p[1] for p in polys[i]]
                h_h = max(ys_h) - min(ys_h)
                body_hs = []
                for j in range(max(0,i-5), min(len(lines), i+6)):
                    if j == i: continue
                    tj = lines[j].strip()
                    if not tj or len(tj) < 3: continue
                    if j >= len(polys) or not polys[j]: continue
                    if min(p[0] for p in polys[j]) > page_width_px * 0.4: continue
                    body_hs.append(max(p[1] for p in polys[j]) - min(p[1] for p in polys[j]))
                body_avg = sum(body_hs)/len(body_hs) if body_hs else h_h
                heading_ratio = h_h / body_avg if body_avg > 0 else 1.0

            # Font size from heading ratio × body FONT_SIZE (relative scaling)
            # Ensures headings scale correctly relative to body text in our output
            heading_font_size = max(FONT_SIZE, round(FONT_SIZE * heading_ratio))

            # Merge consecutive heading lines: OCR may split a long heading into
            # multiple spotting lines. Strategy: use markdown headings as ground truth.
            # If the OCR text is a prefix of a markdown heading, merge subsequent OCR
            # lines until the markdown heading is fully covered.
            heading_lines = [t]
            norm_t = re.sub(r'\s+', '', t).replace('“', '“').replace('”', '”').replace('‘', '‘').replace('’', '’')
            target_h_norm = None
            for h_text, level in md_headings:
                h_norm = re.sub(r'\s+', '', h_text).replace('“', '“').replace('”', '”')
                # OCR text is a strict prefix of a markdown heading
                if len(norm_t) > 8 and len(h_norm) > len(norm_t) and h_norm.startswith(norm_t):
                    target_h_norm = h_norm
                    break
            if target_h_norm:
                accumulated = norm_t
                j = i + 1
                while j < len(lines) and accumulated != target_h_norm:
                    tj = lines[j].strip()
                    if not tj or len(tj) < 2: break
                    if is_page_number(tj) or is_footnote_start(tj): break
                    norm_tj = re.sub(r'\s+', '', tj).replace('“', '“').replace('”', '”')
                    new_acc = accumulated + norm_tj
                    if target_h_norm.startswith(new_acc):
                        heading_lines.append(tj)
                        skip_lines.add(j)
                        accumulated = new_acc
                        j += 1
                    else:
                        break

            if is_running_hdr:
                # Use merged header text from page_headers if available
                hdr_info = page_headers.get(key)
                if hdr_info and i == min(hdr_merge) if hdr_merge else i == 0:
                    # This is the primary header line — use merged text
                    hdr_render_text = hdr_info['text'] if hdr_info else t
                else:
                    hdr_render_text = t
                # Consistent font size: use same formula for all headers
                hdr_pos = 'right' if x_left > page_width_px * 0.4 else 'left'
                hdr_size = round(RIGHT_HDR_H * 0.75) if hdr_pos == 'right' else round(LEFT_HDR_H * 0.75)
                hdr_gap = RIGHT_HDR_GAP if hdr_pos == 'right' else LEFT_HDR_GAP
                if hdr_pos == 'right':
                    result.append('{\\fontsize{' + str(hdr_size) + 'pt}{1em}\\selectfont\\hfill ' + escape_tex(hdr_render_text) + '}\\par\\normalsize')
                else:
                    result.append('{\\fontsize{' + str(hdr_size) + 'pt}{1em}\\selectfont ' + escape_tex(hdr_render_text) + '}\\par\\normalsize')
                result.append('\\vspace{' + str(max(int(hdr_gap), HDR_GAP_MIN)) + 'pt}')
            elif md_level >= 2 or coord_heading:
                # Merge heading lines into one continuous text; LaTeX wraps naturally
                # at the heading font size, matching the source document's layout.
                heading_text = ''.join(heading_lines)
                result.append('\\par\\vspace{10pt}\\noindent{\\CJKfamily{kaiti}\\fontsize{' + str(heading_font_size) + 'pt}{' + str(round(heading_font_size*1.5)) + 'pt}\\selectfont ' + escape_tex(heading_text) + '}\\par\\vspace{6pt}\\normalfont\\normalsize')
            else:
                heading_text = ''.join(heading_lines)
                result.append('{\\CJKfamily{kaiti}\\fontsize{' + str(heading_font_size) + 'pt}{1em}\\selectfont ' + escape_tex(heading_text) + '}\\par\\normalfont\\normalsize')
            continue

        # Footnote
        if is_footnote_start(t):
            flush_body()
            if not fn_rule_added:
                fn_gap = page_fn_gap.get(key, FN_GAP_DEFAULT)
                result.append('\\vspace{' + str(int(fn_gap)) + 'pt}\\hrule\\vspace{3pt}')
                # All footnote params dynamically computed from source document
                # CJK glue with generous stretch so \makebox[s] can fill \linewidth
                # Short lines use \par (single-line paragraph) so stretch is unused
                result.append('{\\fontsize{' + str(FN_FONT_SIZE) + 'pt}{' + str(FN_BASELINE) + 'pt}\\selectfont\\renewcommand{\\CJKglue}{\\hskip ' + FN_CJK_GLUE_BASE + 'em plus 1em}')
                fn_rule_added = True
            in_fn = True
            # ① lines: indented from body left (dynamically computed from source x coords)
            cjk_fn = sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalpha())
            if cjk_fn > FN_STRETCH_THRESHOLD:
                result.append('\\makebox[\\linewidth][s]{\\hspace{' + str(FN_INDENT_PT) + 'pt}' + escape_tex(t) + '}\\par')
            else:
                result.append('\\hspace{' + str(FN_INDENT_PT) + 'pt}' + escape_tex(t) + '\\par')
            continue

        # Body — buffer for paragraph grouping
        body_buf.append({
            'text': t, 'indent': (x_left - BODY_LEFT) > INDENT_THRESHOLD_PX,
            'cjk': sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalpha())
        })

    flush_body()
    if in_fn: result.append('}')
    result.append('\\par\\newpage')
    all_tex.append('\n'.join(result))

latex_body = '\n'.join(all_tex)
latex = header + latex_body + '\n\\end{document}\n'

with open('/tmp/xelatex_v13.tex', 'w', encoding='utf-8') as f:
    f.write(latex)
print(f"TeX: {len(latex)} chars")

r = subprocess.run(['xelatex', '-interaction=nonstopmode', '/tmp/xelatex_v13.tex'],
    cwd='/tmp', capture_output=True, text=True, timeout=120)

pdf_tmp = '/tmp/xelatex_v13.pdf'
if os.path.exists(pdf_tmp):
    if os.path.exists(OUT_PDF): os.remove(OUT_PDF)
    os.rename(pdf_tmp, OUT_PDF)
    pages = fitz.open(OUT_PDF).page_count
    errs = [l for l in (r.stderr+r.stdout).split('\n') if 'Error' in l]
    print(f"Done: {OUT_PDF} ({pages} pages, {len(errs)} errors)")
else:
    print("xelatex FAILED:")
    for l in (r.stdout+r.stderr).split('\n')[-20:]:
        if l.strip(): print(f"  {l[:150]}")
