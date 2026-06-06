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
FONT_SIZE = max(10, min(16, FONT_SIZE))

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

norm = [x for x in body_x0s if abs(x - BODY_LEFT) < 30]
indented = [x for x in body_x0s if x > BODY_LEFT + 15]
norm_center = statistics.median(norm) if norm else BODY_LEFT
indented_center = statistics.median(indented) if indented else BODY_LEFT + 50
INDENT_THRESHOLD_PX = max(20, (indented_center - norm_center) * 0.5)
INDENT_PT = INDENT_THRESHOLD_PX / SCALE

all_body_gaps = []
for k in spot_lines:
    prev_y = None
    for i, line in enumerate(spot_lines[k]):
        t = line.strip()
        if not t or is_page_number(t) or is_footnote_start(t): continue
        polys = spot_coords.get(k, [])
        if i >= len(polys) or not polys[i]: continue
        if min(p[0] for p in polys[i]) > page_width_px * 0.4: continue
        y = min(p[1] for p in polys[i]) / SCALE
        if prev_y is not None and y > prev_y:
            all_body_gaps.append(y - prev_y)
        prev_y = y
all_body_gaps.sort()
med_gap = statistics.median(all_body_gaps) if all_body_gaps else 20
BASE_SKIP = FONT_SIZE * 1.2
BODY_STRETCH = max(1.0, min(1.8, round(med_gap / BASE_SKIP, 2)))

width_spread = (body_widths_pt[int(len(body_widths_pt)*0.9)] - body_widths_pt[len(body_widths_pt)//10]) / FONT_SIZE if len(body_widths_pt)>10 else 0.1
CJK_STRETCH = round(max(0.05, min(0.3, width_spread * 0.5)), 2)

MARGIN_PT = BODY_LEFT / SCALE
MARGIN_MM = round(MARGIN_PT * 0.3528, 1)

# Page number detection: find numbers at page bottom from spotting data
page_numbers = {}
for key in spot_lines:
    lines = spot_lines[key]; polys = spot_coords.get(key, [])
    for i, l in enumerate(lines):
        t = l.strip()
        if not t or len(t) > 4: continue
        if not t.isdigit(): continue
        if i >= len(polys) or not polys[i]: continue
        y = max(p[1] for p in polys[i]) / SCALE
        if y > PH_PT * 0.5:  # bottom half of page
            page_numbers[key] = t
            break
START_PAGE = 1  # fallback
if page_numbers:
    vals = sorted(int(v) for v in page_numbers.values())
    print(f"Page numbers detected: {vals[:3]}...{vals[-3:]}")
START_PAGE = int(list(page_numbers.values())[0]) if page_numbers else 1

print(f"FONT={FONT_SIZE}pt TARGET={TARGET}pt INDENT={INDENT_THRESHOLD_PX:.0f}px STRETCH={BODY_STRETCH}")

# ── Auto-detect headers ──
odd_headers = {}; even_headers = {}
for key in sorted(spot_lines.keys(), key=int):
    lines = spot_lines[key]; polys = spot_coords.get(key, [])
    if not lines or not lines[0].strip(): continue
    t0 = lines[0].strip()
    if len(t0) > 25 or is_page_number(t0) or is_footnote_start(t0): continue
    if 0 >= len(polys) or not polys[0]: continue
    y0 = min(p[1] for p in polys[0]) / SCALE; x0 = min(p[0] for p in polys[0]) / SCALE
    if y0 > 50: continue
    if x0 > 200: odd_headers[t0] = odd_headers.get(t0, 0) + 1
    else: even_headers[t0] = even_headers.get(t0, 0) + 1

DEFAULT_ODD_HDR = max(odd_headers, key=odd_headers.get) if odd_headers else ''
DEFAULT_EVEN_HDR = max(even_headers, key=even_headers.get) if even_headers else ''

# Header gaps
odd_gaps = []; even_gaps = []
for key in sorted(spot_lines.keys(), key=int):
    lines = spot_lines[key]; polys = spot_coords.get(key, [])
    hdr_bot = body_y = None
    for i, l in enumerate(lines):
        t = l.strip()
        if not t or is_page_number(t) or is_footnote_start(t): continue
        if i >= len(polys) or not polys[i]: continue
        xs = [p[0] for p in polys[i]]; ys = [p[1] for p in polys[i]]
        xl, yt, yb = min(xs)/SCALE, min(ys)/SCALE, max(ys)/SCALE
        if hdr_bot is None and (xl > 350 or (i==0 and len(t)<25 and yt<50)):
            hdr_bot = yb; continue
        if hdr_bot and body_y is None and xl < 400:
            body_y = yt; break
    if hdr_bot and body_y:
        gap = body_y - hdr_bot
        if int(key) % 2 == 0: odd_gaps.append(gap)
        else: even_gaps.append(gap)
ODD_HDR_GAP = statistics.median(odd_gaps) if odd_gaps else 38
EVEN_HDR_GAP = statistics.median(even_gaps) if even_gaps else 40

# ── LaTeX header ──
TOP_MARGIN_MM = 8.5
header = f"""\\documentclass[{int(FONT_SIZE)}pt]{{article}}
\\usepackage{{xeCJK}}
\\usepackage[top={TOP_MARGIN_MM}mm, bottom={MARGIN_MM}mm, left={MARGIN_MM}mm, right={MARGIN_MM}mm, paperwidth={PW_MM:.0f}mm, paperheight={PH_MM:.0f}mm]{{geometry}}
\\usepackage{{setspace}}
\\usepackage{{fancyhdr}}
\\setmainfont{{Noto Serif CJK SC}}
\\setCJKmainfont{{Noto Serif CJK SC}}
\\xeCJKsetup{{PunctStyle=kaiming}}
\\setlength{{\\parindent}}{{0pt}}
\\setstretch{{{BODY_STRETCH}}}
\\setcounter{{page}}{{{START_PAGE}}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\fancyfoot[C]{{\\large\\thepage}}
\\renewcommand{{\\headrulewidth}}{{0pt}}
\\renewcommand{{\\CJKglue}}{{\\hskip 0pt plus {CJK_STRETCH}em minus 0.02em}}
\\raggedbottom
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

all_texts = {}
all_fuzzy = {}
for k in spot_lines:
    for l in spot_lines[k]:
        t = l.strip()
        if t and len(t) > 3 and not is_page_number(t):
            all_texts[t] = all_texts.get(t, 0) + 1
            fk = fuzzy_key(t)
            all_fuzzy[fk] = all_fuzzy.get(fk, 0) + 1
watermark_texts = set()
for t, cnt in all_texts.items():
    if cnt >= len(spot_lines) * 0.1:
        fk = fuzzy_key(t)
        if all_fuzzy.get(fk, 0) >= len(spot_lines) * 0.2:
            watermark_texts.add(t)
# Also add position-based: bottom 15% of page height
for k in spot_lines:
    for i, l in enumerate(spot_lines[k]):
        t = l.strip()
        if not t or len(t) < 3: continue
        polys = spot_coords.get(k, [])
        if i >= len(polys) or not polys[i]: continue
        y = max(p[1] for p in polys[i]) / SCALE
        if y > PH_PT * 0.65 and not is_page_number(t) and not t[0] in FN_CIRCLE:
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

    for i in range(len(lines)):
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

        # ── MD-based heading detection ──
        md_level = is_heading_by_md(t, md_headings)
        is_header = (x_left > page_width_px * 0.4) or (i == 0 and len(t) < 25 and y_pt < 50)

        # Missing header
        if i == 0 and y_pt > 50 and not is_header:
            hdr_text = DEFAULT_ODD_HDR if int(key) % 2 == 0 else DEFAULT_EVEN_HDR
            if hdr_text:
                gap = ODD_HDR_GAP if int(key) % 2 == 0 else EVEN_HDR_GAP
                if int(key) % 2 == 0:
                    result.append('{\\footnotesize\\hfill ' + escape_tex(hdr_text) + '\\hfill\\null}\\par')
                else:
                    result.append('{\\footnotesize ' + escape_tex(hdr_text) + '}\\par')
                result.append('\\vspace{' + str(int(gap)) + 'pt}')

        is_running_hdr = is_header and not md_level

        if md_level >= 2 or is_running_hdr:
            if in_fn: result.append('}\\par'); in_fn = False

            if md_level >= 3:
                font_cmd = '\\large\\textbf'
            elif md_level == 2:
                font_cmd = '\\large'
            else:
                font_cmd = '\\footnotesize'

            if is_running_hdr:
                if x_left > page_width_px * 0.4:
                    result.append('{' + font_cmd + '\\hfill ' + escape_tex(t) + '\\hfill\\null}\\par')
                else:
                    result.append('{' + font_cmd + ' ' + escape_tex(t) + '}\\par')
            elif md_level >= 2:
                result.append('\\vspace{10pt}\\noindent{' + font_cmd + ' ' + escape_tex(t) + '}\\par\\vspace{6pt}')
            else:
                result.append('{' + font_cmd + ' ' + escape_tex(t) + '}\\par')
            continue

        # Footnote
        if is_footnote_start(t):
            if not fn_rule_added:
                result.append('\\vfill\\smallskip\\hrule\\smallskip')
                result.append('{\\footnotesize')
                fn_rule_added = True
            in_fn = True
            result.append('\\mbox{' + escape_tex(t) + '}\\\\')
            continue

        if in_fn:
            result.append('\\mbox{' + escape_tex(t) + '}\\\\')
            continue

        # Body
        has_indent = (x_left - BODY_LEFT) > INDENT_THRESHOLD_PX
        indent_cmd = '\\hspace*{2em}' if has_indent else ''
        bw = TARGET if not has_indent else (TARGET - INDENT_PT)
        cjk_eq = sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalpha())

        if 20 <= cjk_eq <= 30:
            result.append(indent_cmd + '\\makebox[' + str(int(bw)) + 'pt][s]{' + escape_tex(t) + '}\\\\')
        else:
            result.append(indent_cmd + '\\mbox{' + escape_tex(t) + '}\\\\')

    if in_fn: result.append('}\\par')
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
