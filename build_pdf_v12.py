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
\\usepackage[margin={MARGIN_MM}mm, paperwidth={PW_MM:.0f}mm, paperheight={PH_MM:.0f}mm]{{geometry}}
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

        # Compute heading height ratio vs body text
        heading_ratio = 1.0
        if i < len(polys) and polys[i]:
            ys = [p[1] for p in polys[i]]
            px_h = max(ys) - min(ys)
            # Estimate body avg height from a few body lines on this page
            body_heights = []
            for j, lj in enumerate(lines):
                tj = lj.strip()
                if not tj or len(tj) < 10: continue
                if j >= len(polys) or not polys[j]: continue
                if min(p[0] for p in polys[j]) > page_width_px * 0.4: continue
                ysj = [p[1] for p in polys[j]]
                body_heights.append(max(ysj) - min(ysj))
                if len(body_heights) >= 5: break
            body_avg = sum(body_heights)/len(body_heights) if body_heights else px_h
            heading_ratio = px_h / body_avg if body_avg > 0 else 1.0

        is_heading = x_left > page_width_px * 0.4 or (i == 0 and len(t) < 25 and not is_footnote_start(t))
        if is_heading:
            if in_fn: result.append('}\\par'); in_fn = False

            # Font size based on height ratio vs body
            if heading_ratio >= 1.2:
                font_cmd = '\\large'  # chapter title: ~14pt
                # Chapter heading: tighter spacing to next element
                spacing = '\\vspace{6pt}'
            elif heading_ratio <= 0.9:
                font_cmd = '\\footnotesize'  # running header: ~10pt
                spacing = '\\vspace{8pt}'
            else:
                font_cmd = '\\normalsize'
                spacing = '\\vspace{8pt}'

            if x_left > page_width_px * 0.35:
                result.append('{' + font_cmd + '\\hfill ' + escape_tex(t) + '\\hfill\\null}\\par' + spacing)
            else:
                result.append('{' + font_cmd + ' ' + escape_tex(t) + '}\\par' + spacing)
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
