#!/usr/bin/env python3
"""xelatex PDF v12 — restored to version before footnote width/glue changes
- Body: \makebox[300pt][s] for 20-25 char lines
- CJK glue: 0.22em, stretch: 1.8
- Footnotes: one \hrule per page, \mbox line-by-line
- Headers, page numbers, duplicate detection, paragraph indent
"""
import json, os, re, subprocess, sys
import fitz

SRC_PDF = sys.argv[1] if len(sys.argv) > 1 else "/opt/test/优化前.pdf"
OUT_PDF = sys.argv[2] if len(sys.argv) > 2 else "/opt/test/最终版_v12.pdf"
SPOTTING_LINES = "/opt/test/spotting_lines.json"
SPOTTING_COORDS = "/opt/test/spotting_coords.json"
TEX_FILE = "/tmp/xelatex_build_v12.tex"

SCALE = 2.0
FN_CIRCLE = set('①②③④⑤⑥⑦⑧⑨⑩')
FONT_SIZE = 12.0
INDENT_THRESHOLD_PX = 40
TARGET = 300
INDENT_PT = 24

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

def compute_body_baseline(spot_lines, spot_coords, page_width_px):
    x_values = []
    for k in spot_lines:
        for i, line in enumerate(spot_lines[k]):
            t = line.strip()
            if not t or is_page_number(t): continue
            if is_footnote_start(t): continue
            polys = spot_coords.get(k, [])
            if i >= len(polys) or not polys[i]: continue
            xs = [p[0] for p in polys[i]]
            left = min(xs)
            if left > page_width_px * 0.4: continue
            x_values.append(left)
    x_values.sort()
    return x_values[len(x_values)//4] if x_values else 0

doc = fitz.open(SRC_PDF)
PW_PT = doc[0].rect.width; PH_PT = doc[0].rect.height
doc.close()
PW_MM = round(PW_PT * 0.3528, 0); PH_MM = round(PH_PT * 0.3528, 0)

text_p0 = fitz.open(SRC_PDF)[0].get_text()
m = re.search(r'[•·]\s*(\d{1,4})\s*[•·]', text_p0)
START_PAGE = int(m.group(1)) if m else 1

spot_lines = json.load(open(SPOTTING_LINES))
spot_coords = json.load(open(SPOTTING_COORDS))
for k in spot_lines:
    spot_lines[k] = [clean_text(l) for l in spot_lines[k]]

page_width_px = max(max(pt[0] for pt in poly) for polys in spot_coords.values() for poly in polys if poly)
BODY_LEFT = compute_body_baseline(spot_lines, spot_coords, page_width_px)
MARGIN_PT = BODY_LEFT / SCALE
MARGIN_MM = round(MARGIN_PT * 0.3528, 1)

print(f"Source: {SRC_PDF}, start={START_PAGE}, {PW_MM:.0f}x{PH_MM:.0f}mm, margin={MARGIN_MM}mm")

header = f"""\\documentclass[{int(FONT_SIZE)}pt]{{article}}
\\usepackage{{xeCJK}}
\\usepackage[top=8.5mm, bottom=18.8mm, left={MARGIN_MM}mm, right={MARGIN_MM}mm, paperwidth={PW_MM:.0f}mm, paperheight={PH_MM:.0f}mm]{{geometry}}
\\usepackage{{setspace}}
\\usepackage{{fancyhdr}}
\\setmainfont{{Noto Serif CJK SC}}
\\setCJKmainfont{{Noto Serif CJK SC}}
\\xeCJKsetup{{PunctStyle=kaiming}}
\\setlength{{\\parindent}}{{0pt}}
\\setstretch{{1.67}}
\\setcounter{{page}}{{{START_PAGE}}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\fancyfoot[C]{{\\textperiodcentered\\ \\thepage\\ \\textperiodcentered}}
\\renewcommand{{\\headrulewidth}}{{0pt}}
\\renewcommand{{\\CJKglue}}{{\\hskip 0pt plus 0.22em minus 0.02em}}
\\tolerance=500
\\begin{{document}}
"""

# ── Auto-detect running headers from source OCR ──
odd_headers = {}; even_headers = {}
for key in sorted(spot_lines.keys(), key=int):
    lines = spot_lines[key]; polys = spot_coords.get(key, [])
    if not lines or not lines[0].strip(): continue
    t0 = lines[0].strip()
    if len(t0) > 25 or is_page_number(t0) or is_footnote_start(t0): continue
    if 0 >= len(polys) or not polys[0]: continue
    y0 = min(p[1] for p in polys[0]) / SCALE
    x0 = min(p[0] for p in polys[0]) / SCALE
    if y0 > 50: continue  # not a header
    if x0 > 200:  # right-aligned → odd page
        odd_headers[t0] = odd_headers.get(t0, 0) + 1
    else:  # left-aligned → even page
        even_headers[t0] = even_headers.get(t0, 0) + 1

DEFAULT_ODD_HEADER = max(odd_headers, key=odd_headers.get) if odd_headers else ''
DEFAULT_EVEN_HEADER = max(even_headers, key=even_headers.get) if even_headers else ''
print(f"Detected odd header: '{DEFAULT_ODD_HEADER}' ({len(odd_headers)} variants)")
print(f"Detected even header: '{DEFAULT_EVEN_HEADER}' ({len(even_headers)} variants)")

# ── Auto-detect header-to-body gaps ──
odd_gaps = []; even_gaps = []; chapter_gaps = []
for key in sorted(spot_lines.keys(), key=int):
    lines = spot_lines[key]; polys = spot_coords.get(key, [])
    k = int(key)
    hdr_bot = None; body_y = None
    for i, l in enumerate(lines):
        t = l.strip()
        if not t or is_page_number(t) or is_footnote_start(t): continue
        if i >= len(polys) or not polys[i]: continue
        xs = [p[0] for p in polys[i]]; ys = [p[1] for p in polys[i]]
        xl, yt, yb = min(xs)/SCALE, min(ys)/SCALE, max(ys)/SCALE

        if hdr_bot is None and (xl > 350 or (i==0 and len(t)<25 and yt<50)):
            hdr_bot = yb; continue
        if hdr_bot is not None and body_y is None and xl < 400:
            body_y = yt; break

    if hdr_bot and body_y:
        gap = body_y - hdr_bot
        if k in [5,6]: chapter_gaps.append(gap)
        elif k % 2 == 0: odd_gaps.append(gap)
        else: even_gaps.append(gap)

import statistics
ODD_HDR_GAP = statistics.median(odd_gaps) if odd_gaps else 38
EVEN_HDR_GAP = statistics.median(even_gaps) if even_gaps else 40
CHAPTER_GAP = statistics.median(chapter_gaps) if chapter_gaps else 8
print(f"Header gaps: odd={ODD_HDR_GAP:.0f}pt, even={EVEN_HDR_GAP:.0f}pt, chapter={CHAPTER_GAP:.0f}pt")

all_tex = []
prev_body_text = None

for key in sorted(spot_lines.keys(), key=int):
    lines = spot_lines[key]
    polys = spot_coords.get(key, [])
    result = []

    this_body = ''.join(l.strip() for l in lines if l.strip() and not is_page_number(l.strip()) and not is_footnote_start(l.strip()))
    is_duplicate = (prev_body_text == this_body) and len(this_body) > 50
    prev_body_text = this_body
    if is_duplicate:
        result.append('\\addtocounter{page}{-1}')

    fn_rule_added = False
    in_fn = False

    for i in range(len(lines)):
        t = lines[i].strip()
        if i < len(polys) and polys[i]:
            x_left = min(p[0] for p in polys[i])
        else:
            x_left = 0

        if not t: continue
        if is_page_number(t): continue

        # Heading detection
        y_pt = min(p[1] for p in polys[i]) / SCALE if i < len(polys) and polys[i] else 99
        is_heading = x_left > page_width_px * 0.4 or (i == 0 and len(t) < 25 and not is_footnote_start(t) and y_pt < 50)

        # Missing header: add standard running header
        if i == 0 and y_pt > 50 and not is_page_number(t) and not is_heading:
            header_text = DEFAULT_ODD_HEADER if int(key) % 2 == 0 else DEFAULT_EVEN_HEADER
            if header_text:
                gap = ODD_HDR_GAP if int(key) % 2 == 0 else EVEN_HDR_GAP
                if int(key) % 2 == 0:
                    result.append('{\\footnotesize\\hfill ' + escape_tex(header_text) + '\\hfill\\null}\\par')
                else:
                    result.append('{\\footnotesize ' + escape_tex(header_text) + '}\\par')
                result.append('\\vspace{' + str(int(gap)) + 'pt}')

        if is_heading:
            if in_fn: result.append('}\\par'); in_fn = False

            # Compute height ratio vs body text
            heading_ratio = 1.0
            src_right_margin = 0
            if i < len(polys) and polys[i]:
                ys = [p[1] for p in polys[i]]
                xs = [p[0] for p in polys[i]]
                px_h = max(ys) - min(ys)
                src_right_margin = (PW_PT - max(xs)/SCALE)
                # Body avg height
                body_heights = []
                for j, lj in enumerate(lines):
                    tj = lj.strip()
                    if not tj or len(tj) < 5: continue
                    if j >= len(polys) or not polys[j]: continue
                    if min(p[0] for p in polys[j]) > page_width_px * 0.4: continue
                    body_heights.append(max(p[1] for p in polys[j]) - min(p[1] for p in polys[j]))
                    if len(body_heights) >= 5: break
                body_avg = sum(body_heights)/len(body_heights) if body_heights else px_h
                heading_ratio = px_h / body_avg if body_avg > 0 else 1.0

            # Font size: map ratio to LaTeX command
            if heading_ratio >= 1.25:
                font_cmd = '\\Large'
            elif heading_ratio >= 1.15:
                font_cmd = '\\large'
            elif heading_ratio >= 0.85:
                font_cmd = '\\normalsize'
            else:
                font_cmd = '\\footnotesize'

            # Use median gap for this page type
            pn = int(key)
            if pn in [5, 6]: src_gap = CHAPTER_GAP
            elif pn % 2 == 0: src_gap = ODD_HDR_GAP
            else: src_gap = EVEN_HDR_GAP

            # Alignment
            if x_left > page_width_px * 0.35:
                box_rm = src_right_margin - MARGIN_PT
                if box_rm >= 0:
                    result.append('{' + font_cmd + '\\makebox[\\linewidth][r]{' + escape_tex(t) + '\\hspace*{' + str(int(box_rm)) + 'pt}}\\par}')
                else:
                    result.append('{' + font_cmd + '\\hfill ' + escape_tex(t) + '\\hspace*{' + str(int(src_right_margin)) + 'pt}\\mbox{}}\\par')
            else:
                result.append('{' + font_cmd + ' ' + escape_tex(t) + '}\\par')

            if src_gap > 4:
                result.append('\\vspace{' + str(int(src_gap)) + 'pt}')
            continue

        if is_footnote_start(t):
            # Collect all lines of this footnote
            fn_lines = [t]
            i += 1
            while i < len(lines):
                nt = lines[i].strip()
                if not nt or is_page_number(nt) or is_footnote_start(nt): break
                if i < len(polys) and polys[i]:
                    nxs = [p[0] for p in polys[i]]
                    if min(nxs) <= page_width_px * 0.4 and (min(nxs) - BODY_LEFT) > INDENT_THRESHOLD_PX: break
                fn_lines.append(nt); i += 1

            fn_text = ''.join(fn_lines)
            if not fn_rule_added:
                result.append('\\smallskip\\hrule\\smallskip')
                result.append('{\\def\\baselinestretch{2.1}\\footnotesize\\parbox{' + str(TARGET) + 'pt}{')
                fn_rule_added = True
            else:
                # Separate footnotes with newline within the same parbox
                result.append('\\par\\vskip 2pt')
            result.append(escape_tex(fn_text))
            in_fn = True
            continue

        if in_fn:
            continue

        has_indent = (x_left - BODY_LEFT) > INDENT_THRESHOLD_PX
        indent_cmd = '\\hspace*{2em}' if has_indent else ''
        bw = TARGET if not has_indent else (TARGET - INDENT_PT)
        cjk_eq = sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalpha())
        if 20 <= cjk_eq <= 25:
            result.append(indent_cmd + '\\makebox[' + str(bw) + 'pt][s]{' + escape_tex(t) + '}\\\\')
        else:
            result.append(indent_cmd + '\\mbox{' + escape_tex(t) + '}\\\\')

    if in_fn: result.append('}\\par}')
    result.append('\\par\\newpage')
    all_tex.append('\n'.join(result))

latex_body = '\n'.join(all_tex)
latex = header + latex_body + '\n\\end{document}\n'

with open(TEX_FILE, 'w', encoding='utf-8') as f:
    f.write(latex)
print(f"TeX: {len(latex)} chars → {TEX_FILE}")

r = subprocess.run(['xelatex', '-interaction=nonstopmode', os.path.basename(TEX_FILE)],
    cwd=os.path.dirname(TEX_FILE), capture_output=True, text=True, timeout=120)

pdf_tmp = TEX_FILE.replace('.tex', '.pdf')
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
