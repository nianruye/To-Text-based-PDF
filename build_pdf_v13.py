#!/usr/bin/env python3
"""Build PDF v13 — use PaddleOCR layout detection for heading detection.
OCR labels provide paragraph_title/doc_title markers (more accurate than
structural rules). Spotting provides coordinates. Combine for better layout.
"""
import json, os, re, subprocess, sys, statistics, fitz

SRC_PDF = sys.argv[1] if len(sys.argv) > 1 else "/opt/test/优化前.pdf"
OUT_PDF = sys.argv[2] if len(sys.argv) > 2 else "/opt/test/最终版_v13.pdf"
SPOTTING_LINES = sys.argv[3] if len(sys.argv) > 3 else "/opt/test/spotting_lines.json"
SPOTTING_COORDS = sys.argv[4] if len(sys.argv) > 4 else "/opt/test/spotting_coords.json"
SPOTTING_TITLES = sys.argv[5] if len(sys.argv) > 5 else ""  # OCR标题集合文件（可选）
MARKDOWN_FILE = sys.argv[6] if len(sys.argv) > 6 else ""

FN_CIRCLE = set('①②③④⑤⑥⑦⑧⑨⑩')

def clean_text(text):
    return text.lstrip("‖‖| \t")

# 引号归一化映射表：各种引号变体 → 统一形式（用于标题文本匹配）
_QUOTE_MAP = str.maketrans({
    '"': '"',  # " ASCII
    '“': '"',  # " 左弯引号 → "
    '”': '"',  # " 右弯引号 → "
    '‘': "'",       # ' 左单引号
    '’': "'",       # ' 右单引号
    '、': '、',  # 、
})

def normalize_text(text):
    """归一化文本用于匹配：去空白 + 统一引号。
    OCR 逐行数据和 block 标题文本可能空格/引号不同，归一化后才能匹配。"""
    # 去掉所有空白字符
    s = re.sub(r'\s+', '', text)
    # 统一引号
    s = s.translate(_QUOTE_MAP)
    return s

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

def is_toc_entry(t):
    """Detect TOC (table of contents) entries: lines with leader dots + page number."""
    return bool(re.search(r'[…\.]{2,}\s*\d{1,4}\s*$', t.strip()))

def is_body_fragment(t):
    """Short body text fragments (paragraph endings) ending with sentence punctuation
    or a footnote marker. Real headings rarely end with 。！？ or ①②③."""
    s = t.strip()
    if not (s and len(s) <= 10):
        return False
    return s[-1] in '。！？；：…' or s[-1] in FN_CIRCLE

def is_toc_entry_start(t):
    """Detect the start of a new TOC entry (for flushing no-number continuations)."""
    s = t.strip()
    return bool(re.match(
        r'^(第[一二三四五六七八九十百千零\d]+[章节部分编篇]'
        r'|专题[一二三四五六七八九十\d]+'
        r'|附录|参考文献|后记|前言|序言|绪论'
        r'|[（(]?[一二三四五六七八九十\d]+[)）、.．])', s))

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

# 加载 OCR 版面分析提取的标题文本集合（如果有）
spot_titles = set()
if SPOTTING_TITLES and os.path.exists(SPOTTING_TITLES):
    titles_data = json.load(open(SPOTTING_TITLES))
    # titles_data 可能是全局 set/list，或按页的 dict
    if isinstance(titles_data, dict):
        # 每页的标题列表
        for pg, title_list in titles_data.items():
            for title in title_list:
                spot_titles.add(normalize_text(title))
    else:
        # 全局标题集合
        for title in titles_data:
            spot_titles.add(normalize_text(title))
    if spot_titles:
        print(f"OCR titles loaded: {len(spot_titles)} titles for matching")

# Compute SCALE: the ratio converting OCR pixel coords → PDF pt coords.
# Two OCR paths exist (see run_spotting_ocr.py):
#   1. Direct PDF upload: OCR coords are in the API's internal render space,
#      which matches the embedded image → use img_w / PW_PT.
#   2. PNG conversion (200 DPI): when the PDF has non-bitonal (JPEG) images,
#      pages are rendered to PNG at 200 DPI first, so OCR coords are in that
#      larger space (≈ PW_PT × 200/72). The embedded image is a *different*
#      resolution and CANNOT be used here.
# Detection: if OCR max-X exceeds the embedded image width by >10%, OCR ran
# on a PNG render. Use the Y-axis ratio (text reaches near page bottom) since
# PNG renders have uniform X/Y DPI.
tmp_doc = fitz.open(SRC_PDF)
first_img = tmp_doc[0].get_images(full=True)
img_w = first_img[0][2] if first_img else 0
img_h = first_img[0][3] if first_img else 0
tmp_doc.close()

page_width_px = max(max(pt[0] for pt in poly) for polys in spot_coords.values() for poly in polys if poly)
page_height_px = max(max(pt[1] for pt in poly) for polys in spot_coords.values() for poly in polys if poly)

if img_w > 0 and page_width_px > img_w * 1.10:
    # PNG-conversion path: coords are in a uniform-DPI render, derive SCALE
    # from the full page extent (Y is most reliable — footers/page numbers sit
    # near the bottom edge; X text rarely reaches the right margin).
    SCALE = page_height_px / PH_PT if page_height_px > 0 else 2.78
    print(f"PNG-conversion OCR detected: OCR {page_width_px:.0f}x{page_height_px:.0f} "
          f"exceeds embedded {img_w}x{img_h}; SCALE={SCALE:.3f} (from Y/page-height)")
else:
    SCALE = img_w / PW_PT if img_w > 0 else 2.0
    print(f"Direct-upload OCR: SCALE={SCALE:.3f} (from embedded image {img_w}px)")

# ── Identify content pages (skip covers, CIP, front matter) ──
# A content page has: many full-width body text lines with consistent spacing.
# Cover/CIP pages have few wide lines, structured fields, or very large fonts.
def is_content_page(key):
    """True if this page has actual running body text (not cover/CIP/front matter)."""
    pg_lines = spot_lines.get(key, [])
    pg_polys = spot_coords.get(key, [])
    full_width_lines = 0  # lines spanning >60% of page width
    body_text_chars = 0
    for i, l in enumerate(pg_lines):
        t = l.strip()
        if not t or len(t) < 5: continue
        if is_page_number(t) or is_footnote_start(t): continue
        if '学习理论' in t: continue
        if i >= len(pg_polys) or not pg_polys[i]: continue
        xs = [p[0] for p in pg_polys[i]]
        w = max(xs) - min(xs)
        # No per-line h (height) filter: cover titles are already excluded
        # because centered/short cover lines don't span >55% page width.
        if w > page_width_px * 0.55:
            full_width_lines += 1
            body_text_chars += len(t)
    # fw>=9 excludes CIP/copyright pages (typically fw<=8) while keeping
    # sparse content pages (PDF3 page 9 has fw=9, a real content page).
    return full_width_lines >= 9 and body_text_chars > 100

content_page_keys = [k for k in sorted(spot_lines.keys(), key=int) if is_content_page(k)]
print(f"Content pages: {len(content_page_keys)}/{len(spot_lines)} "
      f"(keys {content_page_keys[0] if content_page_keys else '?'}..{content_page_keys[-1] if content_page_keys else '?'})")

# ── Parse markdown structure ──
md_headings, md_fns = parse_markdown_structure(MARKDOWN_FILE)
# Filter MD headings: only keep those that appear on content pages (avoid cover false positives)
content_text_set = set()
for k in content_page_keys:
    for l in spot_lines[k]:
        t = l.strip()
        if t and len(t) > 3:
            content_text_set.add(re.sub(r'\s+', '', t)[:30])
filtered_headings = set()
for h_text, level in md_headings:
    h_norm = re.sub(r'\s+', '', h_text)[:30]
    # Skip false positives: headings should not be complete sentences
    # Real headings are short (<30 chars) and don't end with punctuation
    if len(h_norm) > 25 and any(p in h_text for p in '。！？，、；：,…—–'):
        continue
    # Keep heading if its text appears on a content page
    for ct in content_text_set:
        if h_norm in ct or ct in h_norm:
            filtered_headings.add((h_text, level))
            break
if filtered_headings:
    md_headings = filtered_headings
print(f"MD headings found: {len(md_headings)} (filtered from source)")
if md_headings:
    for h, lv in sorted(md_headings, key=lambda x: x[1])[:5]:
        print(f"  {'#'*lv} {h[:50]}")

# ── Text layer detection for PDFs with embedded OCR ──
# Some PDFs have an OCR text layer (HiddenHorzOCR etc.) that provides
# layout parameters in pt units directly, bypassing the SCALE-dependent
# calculations. We detect such PDFs and extract precise layout metrics.
src_doc = fitz.open(SRC_PDF)
_text_layer_params = {}
text_block_counts = [len([b for b in src_doc[i].get_text('dict')['blocks'] if b['type']==0]) for i in range(len(src_doc))]
has_text_layer = statistics.median(text_block_counts) > 5
if has_text_layer:
    print(f"Text layer detected: median {statistics.median(text_block_counts):.0f} text blocks/page → using text layer for layout params")
    # Extract layout from text layer (all in pt, no SCALE needed)
    tl_sizes = []      # body text font sizes
    tl_lefts = []      # body text x0 positions
    tl_rights = []     # body text x1 positions
    tl_y_gaps = []     # line spacing (y gap between consecutive body lines)
    tl_header_y = []   # header y positions (top of page)
    tl_fn_y = []       # footnote y positions (bottom of page)
    tl_header_sizes = []  # header font sizes (from text layer, in pt)
    tl_fn_sizes = []      # footnote font sizes (from text layer, in pt)
    tl_fn_y_gaps = []     # footnote line spacing (y gap, in pt)

    for page_idx in range(len(src_doc)):
        page = src_doc[page_idx]
        blocks = page.get_text('dict')['blocks']
        lines_info = []
        for block in blocks:
            if block['type'] != 0: continue
            for line in block.get('lines', []):
                text = ''.join(s['text'] for s in line['spans'])
                size = statistics.median([s['size'] for s in line['spans']]) if line['spans'] else 10
                bbox = line['bbox']
                lines_info.append((bbox[1], bbox[0], bbox[2], size, text))  # y, x0, x1, size, text

        lines_info.sort(key=lambda x: (x[0], x[1]))  # sort by y then x
        prev_y = None
        prev_fn_y = None

        for y, x0, x1, size, text in lines_info:
            # Skip headers (y < 80pt, short text) — collect their font sizes
            if y < 80 and len(text) < 30:
                tl_header_y.append(y)
                tl_header_sizes.append(size)
                continue
            # Skip page numbers (bottom of page, short number-like)
            if y > PH_PT - 60 and re.match(r'^[·•‧]?\s*\d{1,4}\s*[·•‧]?$', text.strip()):
                continue
            # Skip footnotes (y > 650pt, contains ①②③ or is citation text) — collect sizes + gaps
            if y > PH_PT * 0.75 and (any(c in text for c in '①②③④⑤⑥⑦⑧⑨⑩') or '马克思' in text and '卷' in text):
                tl_fn_y.append(y)
                tl_fn_sizes.append(size)
                if prev_fn_y is not None and y > prev_fn_y:
                    tl_fn_y_gaps.append(y - prev_fn_y)
                prev_fn_y = y
                continue
            # Non-footnote lines in footnote region: reset prev_fn_y tracking
            if y > PH_PT * 0.75:
                prev_fn_y = None

            # Body text
            if size > 10:  # only body-sized text
                tl_sizes.append(size)
                tl_lefts.append(x0)
                tl_rights.append(x1)
                if prev_y and y > prev_y:
                    tl_y_gaps.append(y - prev_y)
                prev_y = y

    if tl_sizes:
        _text_layer_params['FONT_SIZE'] = round(statistics.median(tl_sizes))
        _text_layer_params['MARGIN_PT'] = round(statistics.median(tl_lefts))
        _text_layer_params['TARGET'] = round(statistics.median([r - l for l, r in zip(tl_lefts, tl_rights)]))
        _text_layer_params['LINE_GAP'] = statistics.median(tl_y_gaps) if tl_y_gaps else 27
        _text_layer_params['BODY_STRETCH'] = round(_text_layer_params['LINE_GAP'] / (_text_layer_params['FONT_SIZE'] * 1.2), 2)
        _text_layer_params['BODY_STRETCH'] = max(1.4, min(1.8, _text_layer_params['BODY_STRETCH']))
        # Header and footnote font sizes from text layer (in pt, no SCALE involved)
        _text_layer_params['HEADER_FONT_SIZE'] = round(statistics.median(tl_header_sizes)) if tl_header_sizes else 10
        _text_layer_params['FN_FONT_SIZE'] = round(statistics.median(tl_fn_sizes)) if tl_fn_sizes else 10
        _text_layer_params['FN_BASELINE'] = round(statistics.median(tl_fn_y_gaps)) if tl_fn_y_gaps else round(statistics.median(tl_fn_sizes) * 1.5) if tl_fn_sizes else 16
        _text_layer_params['use_kaiti'] = False  # disable 楷体 in text-layer mode

        # ── Extract heading font size and alignment from text layer ──
        # Headings have significantly larger font size than body text.
        # Scan all pages for lines in body area (y > 80pt) with size > body_median + 3pt.
        _body_median = statistics.median(tl_sizes)
        _tl_heading_sizes = []
        _tl_heading_x_rights = []
        _tl_heading_lines = {}  # page_key -> [(text, size, y, x_right, bold, italic, font)]
        for _pg_idx in range(len(src_doc)):
            _pg = src_doc[_pg_idx]
            _heading_entries = []
            for _blk in _pg.get_text('dict')['blocks']:
                if _blk['type'] != 0: continue
                for _ln in _blk.get('lines', []):
                    _txt = ''.join(s['text'] for s in _ln['spans']).strip()
                    _sz = statistics.median([s['size'] for s in _ln['spans']]) if _ln['spans'] else 10
                    _bb = _ln['bbox']
                    _yy, _xx0, _xx1 = _bb[1], _bb[0], _bb[2]
                    if _yy > 80 and _sz > _body_median + 3 and _txt:
                        # Detect bold/italic from span flags and font names
                        _is_bold = False
                        _is_italic = False
                        _first_font = ''
                        for _s in _ln['spans']:
                            _sflags = _s.get('flags', 0)
                            if _sflags & (1 << 4):  # bit 4 = bold
                                _is_bold = True
                            if _sflags & (1 << 1):  # bit 1 = italic
                                _is_italic = True
                            _fn = _s.get('font', '')
                            if not _first_font:
                                _first_font = _fn
                            _fn_lower = _fn.lower()
                            if any(kw in _fn_lower for kw in ['bold', 'heiti', '黑体', 'heavy', 'demi']):
                                _is_bold = True
                            if any(kw in _fn_lower for kw in ['italic', 'oblique', '楷体', 'kaiti']):
                                _is_italic = True
                        _tl_heading_sizes.append(_sz)
                        _tl_heading_x_rights.append(_xx1)
                        _heading_entries.append((_txt[:30], _sz, _yy, _xx1, _is_bold, _is_italic, _first_font))
            _tl_heading_lines[str(_pg_idx)] = _heading_entries
        if _tl_heading_sizes:
            _text_layer_params['HEADING_FONT_SIZE'] = round(statistics.median(_tl_heading_sizes))
            _median_xr = statistics.median(_tl_heading_x_rights)
            _text_layer_params['HEADING_ALIGN'] = 'right' if _median_xr > PW_PT * 0.85 else 'left'
        else:
            _text_layer_params['HEADING_FONT_SIZE'] = _text_layer_params['FONT_SIZE']
            _text_layer_params['HEADING_ALIGN'] = 'left'
        _text_layer_params['heading_lines'] = _tl_heading_lines
        _bold_count = sum(1 for _pg in _tl_heading_lines.values() for e in _pg if e[4])
        print(f"  Text layer: HEADING_FONT={_text_layer_params['HEADING_FONT_SIZE']}pt HEADING_ALIGN={_text_layer_params['HEADING_ALIGN']} ({len(_tl_heading_sizes)} heading lines, {_bold_count} bold)")

        # Also compute SCALE correction: spotting x0 vs text layer x0
        # This calibrates the spotting coordinates to match text layer positions
        # Quick extraction of spotting body x0s (full version is computed later)
        _quick_spot_x0s = []
        for k in content_page_keys:
            for i, line in enumerate(spot_lines.get(k, [])):
                t = line.strip()
                if not t or len(t) < 5: continue
                if is_page_number(t) or is_footnote_start(t): continue
                polys = spot_coords.get(k, [])
                if i >= len(polys) or not polys[i]: continue
                xl = min(p[0] for p in polys[i])
                if xl < page_width_px * 0.4:
                    _quick_spot_x0s.append(xl)
        if tl_lefts and _quick_spot_x0s:
            tl_median_left = statistics.median(tl_lefts)  # in pt
            spot_median_left = statistics.median(_quick_spot_x0s)  # in px
            _text_layer_scale = spot_median_left / tl_median_left
            print(f"  Text layer: FONT={_text_layer_params['FONT_SIZE']}pt MARGIN={_text_layer_params['MARGIN_PT']}pt TARGET={_text_layer_params['TARGET']}pt LINE_GAP={_text_layer_params['LINE_GAP']:.1f}pt")
            print(f"  Text layer: HEADER_FONT={_text_layer_params['HEADER_FONT_SIZE']}pt FN_FONT={_text_layer_params['FN_FONT_SIZE']}pt use_kaiti={_text_layer_params['use_kaiti']}")
            print(f"  Text layer: reference SCALE={_text_layer_scale:.3f} (spotting x0={spot_median_left:.0f}px / tl x0={tl_median_left:.0f}pt) — keeping original SCALE for coords")
else:
    print(f"No text layer detected (median {statistics.median(text_block_counts):.0f} text blocks/page) → using spotting-based params")

src_doc.close()

# ── Source-derived detection thresholds ──
# Scan content page lines only, classify as heading or body, collect geometry.
# All thresholds below are computed from THIS document's actual data.
_src_heading_hs = []      # px heights of heading lines
_src_heading_widths = []  # px widths of heading lines
_src_body_hs = []         # px heights of body lines
_src_body_widths = []     # px widths of body lines (excl. footnotes/page-nums)
for k in content_page_keys:
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
for k in content_page_keys:
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
# Floor: OCR height noise on scanned pages is typically <20%, so a body line may
# read up to ~1.15x the body average purely from noise. Real headings are ≥30%
# taller. Floor the dynamic ratio at 1.25 to suppress body-text false positives
# (e.g. "思想的有害影响" r=1.14, "命的。"③ r=1.10) while keeping genuine tall
# headings (e.g. "导论" r=1.32, "写作的时代背景及其问题意识" r=1.45).
COORD_HEADING_RATIO = max(COORD_HEADING_RATIO, 1.25)
# Min heading width: below min actual heading width (rejects narrow body continuation lines)
MIN_HEADING_WIDTH = (min(_src_heading_widths) * 0.8) if _src_heading_widths else page_width_px * 0.35
print(f"Source-derived thresholds: heading_ratio={COORD_HEADING_RATIO:.3f} min_heading_w={MIN_HEADING_WIDTH:.0f}px")

# ── Dynamic parameters (from content pages only) ──
BODY_LEFT = 0
body_x0s = []
for k in content_page_keys:
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
for k in content_page_keys:
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
for k in content_page_keys:
    for i, line in enumerate(spot_lines[k]):
        t = line.strip()
        if not t or len(t) < 5: continue
        if is_page_number(t) or is_footnote_start(t): continue
        polys = spot_coords.get(k, [])
        if i < len(polys) and polys[i] and min(p[0] for p in polys[i]) > page_width_px * 0.4: continue
        cjk = sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalnum())
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
for k in content_page_keys:
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
for k in content_page_keys:
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

# Use detected body width as TARGET, not fixed margins.
# Source documents have varying margins — forcing TARGET = PW - 40pt
# causes text to stretch beyond the original layout.
# Fall back to PW_PT - 40pt only if detection fails.
if body_widths_pt:
    TARGET = int(body_widths_pt[int(len(body_widths_pt)*0.9)])
else:
    TARGET = int(PW_PT - 40)
TARGET = max(TARGET, int(PW_PT * 0.70))  # minimum 70% of page width
MARGIN_PT = (PW_PT - TARGET) / 2
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
# Use page number from first content page as START_PAGE
_first_content_key = content_page_keys[0] if content_page_keys else None
if _first_content_key and _first_content_key in page_numbers:
    START_PAGE = int(page_numbers[_first_content_key])
elif page_numbers:
    START_PAGE = int(list(page_numbers.values())[0])

# ── Apply text layer params if available (PDFs with embedded OCR) ──
if has_text_layer and _text_layer_params:
    FONT_SIZE = _text_layer_params.get('FONT_SIZE', FONT_SIZE)
    TARGET = _text_layer_params.get('TARGET', TARGET)
    MARGIN_PT = _text_layer_params.get('MARGIN_PT', MARGIN_PT)
    BODY_STRETCH = _text_layer_params.get('BODY_STRETCH', BODY_STRETCH)
    # Unify character spacing: compute threshold from text layer data
    # At FONT_SIZE pt with TARGET pt line width, full line ≈ TARGET/FONT_SIZE chars.
    # Only lines ≥ 80% of full width use \makebox[s]; shorter lines (paragraph
    # endings, headings, short continuations) keep natural spacing.
    _tl_full_line_cjk = round(_text_layer_params['TARGET'] / _text_layer_params['FONT_SIZE'])
    STRETCH_THRESHOLD = round(_tl_full_line_cjk * 0.80)
    MARGIN_MM = round(MARGIN_PT * 0.3528, 1)
    print(f"[Text layer override] FONT={FONT_SIZE}pt TARGET={TARGET}pt MARGIN={MARGIN_PT}pt STRETCH={BODY_STRETCH}")
    print(f"[Text layer override] STRETCH_THRESHOLD={STRETCH_THRESHOLD} (full_line≈{_tl_full_line_cjk} CJK, 80%)")

print(f"FONT={FONT_SIZE}pt TARGET={TARGET}pt INDENT={INDENT_THRESHOLD_PX:.0f}px STRETCH={BODY_STRETCH}")

# ── Auto-detect headers per page (content pages only) ──
# For each content page, record: header text, position (left/right), line height (pt)
# MERGE_GAP_PT: header lines with inter-line gap < this (in pt) are considered
# a split header and merged. Derived from median header line height.
_hdr_h_pts = []
for key in content_page_keys:
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
for key in content_page_keys:
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
        # Header-like: right-aligned OR narrower than 65% of page width
        # Body text typically spans >70% of page width, headers are shorter
        line_w_px = max(xs) - min(xs)
        is_hdr_like = (x_left > page_width_px * 0.4) or line_w_px < page_width_px * 0.65
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
# Header font size: relative to body FONT_SIZE, so headers are proportionally smaller
# Typical book: headers are ~75-80% of body font size
RIGHT_HDR_FONT = max(6, round(FONT_SIZE * 0.8))
LEFT_HDR_FONT = max(6, round(FONT_SIZE * 0.8))
# In text-layer mode, override header fonts with accurate pt values from the
# text layer (running headers are NOT body*0.8 — they have their own size).
if has_text_layer and _text_layer_params:
    RIGHT_HDR_FONT = _text_layer_params.get('HEADER_FONT_SIZE', RIGHT_HDR_FONT)
    LEFT_HDR_FONT = _text_layer_params.get('HEADER_FONT_SIZE', LEFT_HDR_FONT)

# Header gaps: distance from header bottom to body text start, per position
right_gaps = []; left_gaps = []
for key in content_page_keys:
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

# ── Per-page footnote gap from source (content pages) ──
page_fn_gap = {}  # key → gap in pt between body end and footnote start
for key in content_page_keys:
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

for key in content_page_keys:
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

        cjk = sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalnum())
        if cjk > 15:
            fn_char_densities.append(w / cjk)

# Compute dynamic params
FN_FONT_SIZE = round(statistics.median(fn_line_heights) * 0.78) if fn_line_heights else 6
# In text-layer mode, override footnote font with accurate pt value from the
# text layer (SCALE-dependent calculation is inaccurate for PDF1).
if has_text_layer and _text_layer_params:
    FN_FONT_SIZE = _text_layer_params.get('FN_FONT_SIZE', FN_FONT_SIZE)
FN_BASELINE = round((statistics.median(fn_line_heights) + statistics.median(fn_line_gaps)) if fn_line_heights and fn_line_gaps else FN_FONT_SIZE * 1.5)
if has_text_layer and _text_layer_params:
    # Source FN baseline is ~18pt (verified from text layer analysis).
    # Use tighter baseline than text-layer extraction (which includes
    # irregular gaps from citations), so footnotes fit on sparse pages.
    FN_BASELINE = round(FN_FONT_SIZE * 1.5)  # 11pt × 1.5 ≈ 16pt

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
# In text-layer mode, reset footnote CJKglue: the OCR-based glue was computed
# with old FN_FONT_SIZE (6pt) but now overridden to ~11pt. Use body-style glue
# (0 base + stretch) so \makebox[s] can fill width without overflowing.
if has_text_layer and _text_layer_params:
    FN_CJK_GLUE_BASE = "0.00"
    FN_CJK_GLUE = "0.00em plus 0.60em"

# Footnote stretch threshold: justify full-width footnote lines like body text
fn_cjk_list = []
for k in content_page_keys:
    in_fn_block = False
    for i, line in enumerate(spot_lines[k]):
        t = line.strip()
        if not t: continue
        if is_footnote_start(t):
            in_fn_block = True
        elif is_page_number(t):
            in_fn_block = False; continue
        if not in_fn_block: continue
        cjk = sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalnum())
        if cjk > 10: fn_cjk_list.append(cjk)
if fn_cjk_list:
    fn_cjk_list.sort()
    FN_STRETCH_THRESHOLD = round(fn_cjk_list[len(fn_cjk_list)//2] * 0.85)
else:
    FN_STRETCH_THRESHOLD = 24

print(f"Footnote params: font={FN_FONT_SIZE}pt baseline={FN_BASELINE}pt indent={FN_INDENT_PT}pt CJKglue={FN_CJK_GLUE}")

# ── LaTeX header ──
TOP_MARGIN_MM = 8.5
header = f"""\\documentclass[{int(FONT_SIZE)}pt]{{extarticle}}
\\usepackage{{xeCJK}}
\\usepackage[top={TOP_MARGIN_MM}mm, bottom=15mm, left={MARGIN_MM}mm, right={MARGIN_MM}mm, paperwidth={PW_MM:.0f}mm, paperheight={PH_MM:.0f}mm]{{geometry}}
\\usepackage{{setspace}}
\\usepackage{{fancyhdr}}
\\setmainfont{{Noto Serif CJK SC}}
\\setCJKmainfont{{Noto Serif CJK SC}}
\\setCJKsansfont{{Noto Sans CJK SC}}
\\setCJKfamilyfont{{kaiti}}{{AR PL KaitiM GB}}
\\setCJKfamilyfont{{heiti}}{{WenQuanYi Zen Hei}}
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
    """Normalize text for fuzzy matching - remove all punctuation/spaces."""
    import unicodedata
    t = text.strip()
    # Remove all punctuation, spaces, and symbols - keep only letters/digits/CJK
    return ''.join(c for c in t if unicodedata.category(c)[0] in ('L', 'N'))[:20]

# Watermarks: short repeated text appearing on >25% pages (frequency-based, not position-based)
# OCR image scaling can make position-based detection unreliable
watermark_texts = set()
text_count_by_page = {}
fuzzy_page_counts = {}
for k in spot_lines:
    seen_this_page = set()
    seen_fuzzy_this_page = set()
    for i, l in enumerate(spot_lines[k]):
        t = l.strip()
        if not t or len(t) < 3 or len(t) > 30: continue
        if is_page_number(t) or is_footnote_start(t): continue
        # Skip lines that look like body text (long full-width lines)
        polys = spot_coords.get(k, [])
        if i < len(polys) and polys[i]:
            w = max(p[0] for p in polys[i]) - min(p[0] for p in polys[i])
            if w > page_width_px * 0.5: continue  # full-width body text
        if t in seen_this_page: continue
        seen_this_page.add(t)
        text_count_by_page[t] = text_count_by_page.get(t, 0) + 1
        fk = fuzzy_key(t)
        if fk not in seen_fuzzy_this_page:
            seen_fuzzy_this_page.add(fk)
            fuzzy_page_counts[fk] = fuzzy_page_counts.get(fk, 0) + 1
# Exclude running page headers from watermark detection — they also appear
# on many pages but are legitimate headers, not watermarks.
_header_texts = set(v['text'] for v in page_headers.values())
# Add watermark if exact count OR fuzzy group count reaches threshold
threshold = len(spot_lines) * 0.25
for t, cnt in text_count_by_page.items():
    if t in _header_texts: continue  # skip known page headers
    fk = fuzzy_key(t)
    if cnt >= threshold or fuzzy_page_counts.get(fk, 0) >= threshold:
        watermark_texts.add(t)
# Also add fuzzy keys for matching OCR variants (quote differences, etc.)
watermark_fuzzy_keys = set()
for wt in watermark_texts:
    watermark_fuzzy_keys.add(fuzzy_key(wt))
if watermark_texts:
    print(f"Watermark filter: {len(watermark_texts)} patterns ({len(watermark_fuzzy_keys)} fuzzy keys)")

# ── Pre-classify font styles for all lines (image-based, for non-text-layer PDFs) ──
line_font_styles = {}  # key -> {line_idx: {family, bold, confidence}}
if not has_text_layer:
    sys.path.insert(0, '/opt/test/font_classifier')
    from predict import detect_font_style, extract_text_crop
    _fc_doc = fitz.open(SRC_PDF)
    _fc_total = 0
    for key in content_page_keys:
        lines_fc = spot_lines.get(key, [])
        polys_fc = spot_coords.get(key, [])
        page_fonts = {}
        for i, t in enumerate(lines_fc):
            t_s = t.strip()
            if not t_s or is_page_number(t_s) or is_footnote_start(t_s):
                continue
            if i >= len(polys_fc) or not polys_fc[i]:
                continue
            xs = [p[0] for p in polys_fc[i]]
            ys = [p[1] for p in polys_fc[i]]
            x0_pt = min(xs) / SCALE
            y0_pt = min(ys) / SCALE
            x1_pt = max(xs) / SCALE
            y1_pt = max(ys) / SCALE
            try:
                crop = extract_text_crop(_fc_doc, int(key), (x0_pt, y0_pt, x1_pt, y1_pt))
                style = detect_font_style(crop)
                page_fonts[i] = style
                _fc_total += 1
            except Exception:
                pass
        line_font_styles[key] = page_fonts
    _fc_doc.close()
    print(f"Font classifier: {_fc_total} lines classified across {len(content_page_keys)} pages")

# ── Render ──
all_tex = []
prev_body_text = None

for key in sorted(spot_lines.keys(), key=int):
    lines = spot_lines[key]; polys = spot_coords.get(key, [])
    result = []

    # Detect TOC pages: these should render ragged (no stretch) to avoid
    # ugly justification of "标题 …… 页码" entries with huge inter-char gaps.
    is_toc_page = (any('目录' in l for l in lines)
                   or sum(1 for l in lines
                          if re.search(r'[…\.]{2,}\s*\d{1,4}\s*$', l.strip())) >= 3)
    _toc_buf = []  # buffered continuation texts awaiting a trailing page number

    this_body = ''.join(l.strip() for l in lines if l.strip() and not is_page_number(l.strip()) and not is_footnote_start(l.strip()))
    is_duplicate = (prev_body_text == this_body) and len(this_body) > 50
    prev_body_text = this_body
    if is_duplicate:
        continue

    # Set page number to source value
    src_pn = page_numbers.get(key, '')
    if src_pn:
        result.append('\\setcounter{page}{' + src_pn + '}')

    # ══ Structural heading detection (replaces font classifier) ══
    def detect_heading_signal(t, x_left, line_w_px, page_width_px,
                              h, body_h_avg, y_pt,
                              COORD_HEADING_RATIO, HDR_REGION_Y, MIN_HEADING_WIDTH):
        """结构规则标题检测。
        返回 (signal_name, md_level) 或 (None, 0)。
        signal ∈ {'L1','L2','L3','coord_heading','centered'}"""
        if not (1 < len(t) < 45 and y_pt > HDR_REGION_Y):
            return None, 0

        # Skip TOC entries: lines with leader dots + page number
        if is_toc_entry(t):
            return None, 0

        # L1: 第X章/节/部分/编/篇 (chapter-level) - must be short to avoid false positives
        if re.match(r'^第[一二三四五六七八九十百千零\d]+[章节部分编篇]', t) and len(t) < 20:
            return 'L1', 2

        # L2: X.X hierarchical numbers (e.g., 1.1, 2.3.1)
        if re.match(r'^[\d]+(\.[\d]+)+', t):
            return 'L2', 2

        # L2: Arabic numeral + separator (e.g., 1., 2．)
        if re.match(r'^[\d]+[.．、]', t):
            return 'L2', 2

        # L2: 专题X (topic markers)
        if re.match(r'^专题[一二三四五六七八九十\d]+', t):
            return 'L2', 2

        # L3: Chinese numeral + separator (e.g., 一"、二、)
        if re.match("^[一二三四五六七八九十]+[.．、\u0022\u201c\u201d\u2018\u2019]", t):
            return 'L3', 2

        # L3: Chinese numeral in parens (e.g., （一）、(2))
        if re.match(r'^[(（][一二三四五六七八九十\d]+[)）]', t):
            return 'L3', 2

        # L3: Chinese numeral without separator (e.g., "二驳斥杜林...", "一澄清杜林...")
        # Requires visual height confirmation (>1.15× body) to avoid body-text false
        # positives like "一般而言...", "一切...".
        if len(t) >= 5 and re.match(r'^[一二三四五六七八九十百]+', t):
            _r3 = h / body_h_avg if body_h_avg > 0 else 1.0
            if _r3 > 1.15:
                return 'L3', 2

        # coord_heading: visually tall line (height ratio)
        # Must be short (real headings are short, not full sentences)
        # Skip body fragments ending with sentence punctuation
        if (body_h_avg > 0 and h / body_h_avg > COORD_HEADING_RATIO
                and line_w_px > MIN_HEADING_WIDTH and len(t) <= 15
                and not is_body_fragment(t)):
            return 'coord_heading', 2

        # centered short line: require BOTH centered AND tall (height ratio > 1.1)
        # to avoid false positives from narrow body text fragments
        x_center = x_left + line_w_px / 2
        page_center = page_width_px / 2
        _r = h / body_h_avg if body_h_avg > 0 else 1.0
        if (abs(x_center - page_center) < page_width_px * 0.1
                and 4 < len(t) <= 15 and _r > 1.1):
            return 'centered', 2

        return None, 0

    def get_heading_font(signal):
        """signal → CJK font command."""
        if signal in ('L1', 'L2'):
            return '\\CJKfamily{heiti}'
        return '\\CJKfamily{kaiti}'

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
                # Font style wrapping for non-default fonts
                _ff = item.get('font_family', 'songti')
                _fb = item.get('bold', False)
                _font_open = ''; _font_close = ''
                if _ff == 'heiti':
                    _font_open = '{\\CJKfamily{heiti}'; _font_close = '}'
                elif _ff == 'kaiti':
                    _font_open = '{\\CJKfamily{kaiti}'; _font_close = '}'
                # fangsong/songti → default (Noto Serif CJK SC), no wrapping needed
                if _fb and not _font_open:
                    _font_open = '{\\bfseries'; _font_close = '}'
                elif _fb:
                    _font_open = _font_open.rstrip('}') + '\\bfseries' + _font_close
                if cjk_count > STRETCH_THRESHOLD and not is_toc_page:
                    result.append('\\makebox[\\linewidth][s]{' + prefix + _font_open + escape_tex(txt) + _font_close + '}\\par')
                else:
                    result.append(prefix + _font_open + escape_tex(txt) + _font_close + '\\par')
        body_buf.clear()

    skip_lines = set()
    # Get merged header indices for this page — skip those lines in render loop
    hdr_merge = page_headers.get(key, {}).get('merge_indices', set())
    for i in range(len(lines)):
        if i in skip_lines: continue
        _heading_signal = None  # Initialize for each line
        # Skip lines that are part of a merged header (already rendered with first line)
        if i in hdr_merge and i > min(hdr_merge): continue
        t = lines[i].strip()
        # Watermark filter: exact match OR fuzzy key match (handles OCR variants)
        if t in watermark_texts or (t and fuzzy_key(t) in watermark_fuzzy_keys): continue
        if not t: continue
        if i < len(polys) and polys[i]:
            xs = [p[0] for p in polys[i]]; ys = [p[1] for p in polys[i]]
            x_left, y_pt = min(xs), min(ys)/SCALE
            # Bottom 10% of page, not a page number → likely watermark/footer
            # But preserve footnote continuation lines (in_fn=True) from being dropped
            if y_pt > PH_PT * 0.88 and not is_page_number(t) and not is_footnote_start(t) and not in_fn:
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
        # Running header detection: based on POSITION (y coordinate + short text),
        # NOT on line index — OCR may place watermark/footer lines before the header.
        # Running headers are ALWAYS at the top of the page, on content pages.
        # Cross-reference with page_headers to avoid false positives (TOC entries,
        # body continuations that happen to be at y < HDR_REGION_Y).
        _line_w_pt = 0
        if i < len(polys) and polys[i]:
            _line_w_pt = (max(p[0] for p in polys[i]) - min(p[0] for p in polys[i])) / SCALE
        _in_hdr_pos = (y_pt < HDR_REGION_Y and key in content_page_keys
                       and (x_left > page_width_px * 0.4
                            or (len(t) < 25 and _line_w_pt < PW_PT * 0.65)))
        _hdr_info = page_headers.get(key)
        _in_hdr_merge = _hdr_info and i in _hdr_info.get('merge_indices', set())
        is_header = _in_hdr_pos and _in_hdr_merge  # must be in detected page_headers

        # Coordinate-based heading: line height > 1.15x body avg + short + not at page top
        # Disabled in text-layer mode: OCR coordinates / SCALE are unreliable and cause
        # full-width body lines to be falsely detected as headings (adding extra vspace).
        coord_heading = False
        if (not has_text_layer and key in content_page_keys and not is_toc_page
                and i < len(polys)
                and polys[i] and not is_header and not is_footnote_start(t)):
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
                # coord_heading: tall line, but MUST be short (real headings are short,
                # not full sentences). Excludes body text with OCR height noise.
                if (ratio > COORD_HEADING_RATIO and 2 <= len(t) <= 15 and y_pt > HDR_REGION_Y
                        and line_width_px > min_heading_width
                        and not is_toc_entry(t) and not is_body_fragment(t)):
                    coord_heading = True
                    md_level = max(md_level, 2)  # treat as ## level

        # ── Text-layer heading detection by font size ──
        # When markdown headings are unavailable (MARKDOWN_FILE empty) or in text-layer
        # mode, use the text layer's actual font sizes to detect headings: lines with
        # size significantly larger than body text are headings.
        if has_text_layer and md_level == 0 and not is_header and not is_footnote_start(t) and y_pt > HDR_REGION_Y:
            _tl_hlines = _text_layer_params.get('heading_lines', {}).get(key, [])
            _norm_t = re.sub(r'\s+', '', t)
            for _ht, _hs, _hy, _hx, _hb, _hi, _hf in _tl_hlines:
                _norm_ht = re.sub(r'\s+', '', _ht)
                if _norm_t == _norm_ht or (_norm_t and _norm_ht and (_norm_t in _norm_ht or _norm_ht in _norm_t)):
                    if _hs > FONT_SIZE + 3:
                        md_level = 2  # treat as ## heading
                    break

        
        # ══ OCR Layout Detection (优先级最高) ══
        # 用 OCR 版面分析提取的标题文本集合，文本匹配判断标题
        # （新版面分析按"块"输出，与逐行索引不对应，故用文本匹配）
        _ocr_target_title = None  # 记录匹配的 OCR 标题（用于后续续行 merge）
        if spot_titles and not is_header and not is_footnote_start(t):
            _norm_t = normalize_text(t)
            if _norm_t in spot_titles:
                md_level = 2
                _heading_signal = 'ocr_title'
                _ocr_target_title = _norm_t  # 记录完整匹配的标题
            elif len(_norm_t) >= 10:
                # 前缀匹配：当前行是某 OCR 标题的开头部分
                # 用于处理旧逐行 OCR 把长标题拆成多行的情况
                for _otitle in spot_titles:
                    if len(_otitle) > len(_norm_t) + 5 and _otitle.startswith(_norm_t):
                        md_level = 2
                        _heading_signal = 'ocr_title'
                        _ocr_target_title = _otitle  # 记录完整标题用于 merge
                        break

        # ── Structural heading detection (all PDFs, 作为 fallback) ══
        # Use pattern library + visual signals to detect headings.
        # Replaces font classifier-based detection.
        # Run even when md_level>0 to allow pattern-based font override.
        # Only on content pages — skip covers, CIP, copyright pages.
        if key in content_page_keys and not is_toc_page and not is_header and not is_footnote_start(t):
            # Compute body height average for coord_heading detection
            body_hs = []
            for j in range(max(0,i-5), min(len(lines), i+6)):
                if j == i: continue
                tj = lines[j].strip()
                if not tj or len(tj) < 5: continue
                if j >= len(polys) or not polys[j]: continue
                if min(p[0] for p in polys[j]) > page_width_px * 0.4: continue
                body_hs.append(max(p[1] for p in polys[j]) - min(p[1] for p in polys[j]))
            body_h_avg = sum(body_hs) / len(body_hs) if body_hs else h

            _sig, _mlvl = detect_heading_signal(
                t, x_left, line_w_px, page_width_px,
                h, body_h_avg, y_pt,
                COORD_HEADING_RATIO, HDR_REGION_Y, MIN_HEADING_WIDTH
            )
            if _sig:
                _heading_signal = _sig  # Always override font signal
                if md_level == 0:  # Only set md_level if not already set
                    md_level = _mlvl
            else:
                # If coord_heading detected but no pattern, use coord_heading signal for font
                if md_level >= 2 and not _heading_signal and coord_heading:
                    _heading_signal = 'coord_heading'

        # Missing header: if first body line is y>50, add default header from source position
        # Only for content pages — skip covers, CIP, and front matter
        if i == 0 and y_pt > HDR_REGION_Y and not is_header and key in content_page_keys:
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
            hdr_size = RIGHT_HDR_FONT if hdr_pos == 'right' else LEFT_HDR_FONT
            if hdr_text:
                if hdr_pos == 'right':
                    result.append('{\\fontsize{' + str(hdr_size) + 'pt}{1em}\\selectfont\\hfill ' + escape_tex(hdr_text) + '}\\par\\normalsize')
                else:
                    result.append('{\\fontsize{' + str(hdr_size) + 'pt}{1em}\\selectfont ' + escape_tex(hdr_text) + '}\\par\\normalsize')
                result.append('\\vspace{' + str(max(int(hdr_gap), HDR_GAP_MIN)) + 'pt}')

        # ── TOC entry rendering: restore source layout (text left, leader dots,
        # page number right-aligned). Merge continuation lines (more-indented
        # wrapped tails) into their entry using x-position. ──
        if is_toc_page and not is_header:
            _toc_m = re.match(r'^(.*?)\s*[…·\.]{2,}\s*(\d{1,4})\s*$', t)
            if _toc_m:
                # Numbered line. Decide: wrap-continuation of the buffer (much
                # more indented) vs a NEW entry (similar/shallower indent, whose
                # own number survived while the buffer's was lost to OCR).
                _WRAP = INDENT_THRESHOLD_PX * 1.5
                if _toc_buf and x_left < _toc_buf[0][1] + _WRAP:
                    # New entry: flush the buffered (number-less) entry first.
                    _sx0 = _toc_buf[0][1]
                    _ind0 = '\\hspace*{2em}' if (_sx0 - BODY_LEFT) > INDENT_THRESHOLD_PX else ''
                    result.append(_ind0 + escape_tex(''.join(b[0] for b in _toc_buf)) + '\\par')
                    _toc_buf = []
                    _toc_text = _toc_m.group(1).rstrip(' …·.')
                    _start_x = x_left
                else:
                    _start_x = _toc_buf[0][1] if _toc_buf else x_left
                    _toc_text = ''.join(b[0] for b in _toc_buf) + _toc_m.group(1).rstrip(' …·.')
                _toc_num = _toc_m.group(2)
                _toc_ind = '\\hspace*{2em}' if (_start_x - BODY_LEFT) > INDENT_THRESHOLD_PX else ''
                result.append(_toc_ind + escape_tex(_toc_text)
                              + '\\dotfill\\nobreak\\makebox[3em][r]{' + _toc_num + '}\\par')
                _toc_buf = []
            else:
                # No-number line: continuation (more indented) vs new entry (same/shallower).
                if _toc_buf and x_left < _toc_buf[-1][1] + INDENT_THRESHOLD_PX:
                    _start_x = _toc_buf[0][1]
                    _toc_ind = '\\hspace*{2em}' if (_start_x - BODY_LEFT) > INDENT_THRESHOLD_PX else ''
                    result.append(_toc_ind + escape_tex(''.join(b[0] for b in _toc_buf)) + '\\par')
                    _toc_buf = []
                _toc_buf.append((t, x_left))
            continue

        # Header-region lines are ALWAYS running headers, never content headings.
        # Markdown heading match is suppressed because running headers often share
        # the same text as section titles (e.g. "导论", "第一部分 历史考证").
        is_running_hdr = is_header

        if is_running_hdr:
            md_level = 0  # suppress heading rendering for header-region lines

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
            # In text-layer mode, use heading font size extracted from text layer
            if has_text_layer:
                heading_font_size = _text_layer_params.get('HEADING_FONT_SIZE', FONT_SIZE)
            else:
                heading_font_size = max(FONT_SIZE, round(FONT_SIZE * heading_ratio))

            # Merge consecutive heading lines: OCR may split a long heading into
            # multiple spotting lines. Strategy: use markdown headings as ground truth.
            # If the OCR text is a prefix of a markdown heading, merge subsequent OCR
            # lines until the markdown heading is fully covered.
            heading_lines = [t]
            norm_t = normalize_text(t)  # 用统一的归一化方式
            target_h_norm = None

            # 1. 优先用 Markdown headings（更精确）
            for h_text, level in md_headings:
                h_norm = normalize_text(h_text)
                # OCR text is a strict prefix of a markdown heading
                if len(norm_t) > 8 and len(h_norm) > len(norm_t) and h_norm.startswith(norm_t):
                    target_h_norm = h_norm
                    break

            # 2. 如果无 Markdown，检查 OCR titles（前缀匹配时记录的）
            if not target_h_norm and '_ocr_target_title' in dir() and _ocr_target_title:
                target_h_norm = _ocr_target_title
            if target_h_norm:
                accumulated = norm_t
                j = i + 1
                while j < len(lines) and accumulated != target_h_norm:
                    tj = lines[j].strip()
                    if not tj or len(tj) < 2: break
                    if is_page_number(tj) or is_footnote_start(tj): break
                    norm_tj = normalize_text(tj)  # 统一归一化方式
                    new_acc = accumulated + norm_tj
                    if target_h_norm.startswith(new_acc):
                        heading_lines.append(tj)
                        skip_lines.add(j)
                        accumulated = new_acc
                        j += 1
                    else:
                        break

            # ── Text-layer subtitle merge ──
            # In text-layer mode, merge subsequent lines that have heading-level
            # font size (e.g. "物和社会职能（形式）" after "第四章").
            # The OCR text layer stores the actual font size per line — if a
            # non-heading OCR line has heading-level size, it's part of the title.
            if has_text_layer and len(heading_lines) == 1:
                _tl_hlines = _text_layer_params.get('heading_lines', {}).get(key, [])
                _heading_size = _text_layer_params.get('HEADING_FONT_SIZE', FONT_SIZE)
                _body_size = FONT_SIZE
                _merge_j = i + 1
                while _merge_j < len(lines):
                    _mt = lines[_merge_j].strip()
                    if not _mt:
                        _merge_j += 1
                        continue  # skip blank lines
                    if is_page_number(_mt) or is_footnote_start(_mt):
                        break
                    # Check if this line has heading-level font size in text layer
                    _norm_mt = re.sub(r'\s+', '', _mt)
                    _is_heading_size = False
                    for _ht, _hs, _hy, _hx, _hb, _hi, _hf in _tl_hlines:
                        _norm_ht = re.sub(r'\s+', '', _ht)
                        if _norm_mt == _norm_ht or _norm_mt in _norm_ht or _norm_ht in _norm_mt:
                            if _hs > _body_size + 3:
                                _is_heading_size = True
                            break
                    if _is_heading_size:
                        heading_lines.append(_mt)
                        skip_lines.add(_merge_j)
                        _merge_j += 1
                    else:
                        break

            # ── Structural heading merge (scan PDFs, no text layer) ──
            # When OCR splits a long heading across lines, merge continuation
            # lines that share the heading's (large) font height. Body text
            # has smaller font height, so it stops the merge — no false merges.
            if not has_text_layer and len(heading_lines) == 1 and i < len(polys) and polys[i]:
                _heading_h = max(p[1] for p in polys[i]) - min(p[1] for p in polys[i])
                _merge_j = i + 1
                while _merge_j < len(lines) and _merge_j - i <= 3:
                    _mt = lines[_merge_j].strip()
                    if not _mt or len(_mt) > 25: break
                    if is_page_number(_mt) or is_footnote_start(_mt): break
                    if _mt[-1] in '。！？': break  # sentence end → body, not heading tail
                    # Stop at any new heading pattern
                    if re.match(r'^第[一二三四五六七八九十百千零\d]+[章节部分编篇]', _mt): break
                    if re.match(r'^[\d]+[.．、]', _mt): break
                    if re.match(r'^专题', _mt): break
                    if re.match(r'^[一二三四五六七八九十]+[.．、""""]', _mt): break
                    # Must share the heading's large font height
                    if _merge_j < len(polys) and polys[_merge_j]:
                        _mh = max(p[1] for p in polys[_merge_j]) - min(p[1] for p in polys[_merge_j])
                        if _mh < _heading_h * 0.85: break
                    heading_lines.append(_mt)
                    skip_lines.add(_merge_j)
                    _merge_j += 1

            if is_running_hdr:
                # Use merged header text from page_headers if available
                hdr_info = page_headers.get(key)
                if hdr_info and i == min(hdr_merge) if hdr_merge else i == 0:
                    hdr_render_text = hdr_info['text'] if hdr_info else t
                else:
                    hdr_render_text = t
                hdr_pos = 'right' if x_left > page_width_px * 0.4 else 'left'
                hdr_size = RIGHT_HDR_FONT if hdr_pos == 'right' else LEFT_HDR_FONT
                hdr_gap = RIGHT_HDR_GAP if hdr_pos == 'right' else LEFT_HDR_GAP
                if hdr_pos == 'right':
                    result.append('{\\fontsize{' + str(hdr_size) + 'pt}{1em}\\selectfont\\hfill ' + escape_tex(hdr_render_text) + '}\\par\\normalsize')
                else:
                    result.append('{\\fontsize{' + str(hdr_size) + 'pt}{1em}\\selectfont ' + escape_tex(hdr_render_text) + '}\\par\\normalsize')
                result.append('\\vspace{' + str(max(int(hdr_gap), HDR_GAP_MIN)) + 'pt}')
            elif md_level >= 2 or coord_heading:
                # Heading rendering - use per-heading font size, alignment, bold/italic from text layer
                _hfont = '\\rmfamily' if (has_text_layer and not _text_layer_params.get('use_kaiti', True)) else '\\CJKfamily{kaiti}'
                # Look up this heading's actual size, alignment, bold/italic from text layer
                _heading_bold = False
                _heading_italic = False
                if has_text_layer:
                    _tl_hlines = _text_layer_params.get('heading_lines', {}).get(key, [])
                    _norm_t = re.sub(r'\s+', '', heading_lines[0])
                    _matched_size = None
                    _matched_xr = None
                    for _ht, _hs, _hy, _hx, _hb, _hi, _hf in _tl_hlines:
                        _norm_ht = re.sub(r'\s+', '', _ht)
                        if _norm_t == _norm_ht or _norm_t in _norm_ht or _norm_ht in _norm_t:
                            _matched_size = _hs
                            _matched_xr = _hx
                            _heading_bold = _hb
                            _heading_italic = _hi
                            break
                    if _matched_size:
                        _this_heading_font = round(_matched_size)  # per-heading font size
                    else:
                        _this_heading_font = heading_font_size  # fallback to global/computed
                    _heading_align = 'right' if (_matched_xr and _matched_xr > PW_PT * 0.85) else \
                                     _text_layer_params.get('HEADING_ALIGN', 'left')
                else:
                    _this_heading_font = heading_font_size
                    # Detect alignment from OCR coordinates for non-text-layer PDFs
                    _x_center = x_left + line_w_px / 2
                    _page_center = page_width_px / 2
                    if abs(_x_center - _page_center) < page_width_px * 0.1:
                        _heading_align = 'center'
                    elif x_left > page_width_px * 0.4:
                        _heading_align = 'right'
                    else:
                        _heading_align = 'left'
                # ══ Structural font assignment (replaces font classifier) ══
                if not _heading_bold and not _heading_italic:
                    if '_heading_signal' in dir() and _heading_signal:
                        _hfont = get_heading_font(_heading_signal)
                    elif coord_heading:
                        _hfont = '\\CJKfamily{kaiti}'
                    else:
                        _hfont = '\\CJKfamily{kaiti}'
                # Style prefix: bold/italic
                _style_prefix = ''
                if _heading_bold:
                    _style_prefix += '\\bfseries'
                if _heading_italic:
                    _style_prefix += '\\itshape'
                # Multi-line headings: preserve separate lines with \\ line breaks
                if len(heading_lines) > 1:
                    heading_text = ('\\\\' + chr(10)).join(escape_tex(hl) for hl in heading_lines)
                else:
                    heading_text = escape_tex(heading_lines[0])
                _hfontsize = '\\fontsize{' + str(_this_heading_font) + 'pt}{' + str(round(_this_heading_font*1.5)) + 'pt}\\selectfont'
                if _heading_align == 'right':
                    result.append('\\par\\vspace{10pt}{' + _hfont + _style_prefix + _hfontsize + '\\raggedleft ' + heading_text + '\\par}\\vspace{6pt}\\normalfont\\normalsize')
                elif _heading_align == 'center':
                    result.append('\\par\\vspace{10pt}{' + _hfont + _style_prefix + _hfontsize + '\\centering ' + heading_text + '\\par}\\vspace{6pt}\\normalfont\\normalsize')
                else:
                    result.append('\\par\\vspace{10pt}\\noindent{' + _hfont + _style_prefix + _hfontsize + ' ' + heading_text + '}\\par\\vspace{6pt}\\normalfont\\normalsize')
            else:
                heading_text = ''.join(heading_lines)
                _hfont = '\\rmfamily' if (has_text_layer and not _text_layer_params.get('use_kaiti', True)) else '\\CJKfamily{kaiti}'
                result.append('{' + _hfont + '\\fontsize{' + str(heading_font_size) + 'pt}{1em}\\selectfont ' + escape_tex(heading_text) + '}\\par\\normalfont\\normalsize')
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
                # Reset \baselinestretch so global linespread doesn't inflate footnote spacing
                result.append('{\\renewcommand{\\baselinestretch}{1.0}\\fontsize{' + str(FN_FONT_SIZE) + 'pt}{' + str(FN_BASELINE) + 'pt}\\selectfont\\renewcommand{\\CJKglue}{\\hskip ' + FN_CJK_GLUE_BASE + 'em plus 1em}')
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
        # Body text: default songti (no classifier-based font switching)
        body_buf.append({
            'text': t, 'indent': (x_left - BODY_LEFT) > INDENT_THRESHOLD_PX,
            'cjk': sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalnum()),
            'font_family': 'songti',
            'bold': False,
        })

    flush_body()
    # Flush any trailing TOC continuation that never got a page number
    if _toc_buf:
        _start_x = _toc_buf[0][1]
        _toc_ind = '\\hspace*{2em}' if (_start_x - BODY_LEFT) > INDENT_THRESHOLD_PX else ''
        result.append(_toc_ind + escape_tex(''.join(b[0] for b in _toc_buf)) + '\\par')
        _toc_buf.clear()
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
