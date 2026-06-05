#!/usr/bin/env python3
"""xelatex PDF v10 — v9 fixes: ‖ cleaning, wide-line detection, tighter indent threshold
- Strips OCR artifacts (‖, ‖, |) from all lines
- Detects lines that would overflow \linewidth (mixed CJK/Latin) and skips \mbox
- Raised indent threshold 30→40px to reduce false paragraph indents
- Added \emergencystretch + \hyphenpenalty for better Latin word breaking
"""
import json, os, re, subprocess, sys
import fitz

SRC_PDF = sys.argv[1] if len(sys.argv) > 1 else "/opt/test/优化前.pdf"
OUT_PDF = sys.argv[2] if len(sys.argv) > 2 else "/opt/test/最终版_v10.pdf"
SPOTTING_LINES = "/opt/test/spotting_lines.json"
SPOTTING_COORDS = "/opt/test/spotting_coords.json"
TEX_FILE = "/tmp/xelatex_build_v10.tex"

SCALE = 2.0  # px/pt (max_y / page_height_pt)

END_PUNC = '。！？…）”」』》'
FN_CIRCLE = set('①②③④⑤⑥⑦⑧⑨⑩')

# ── New: OCR artifact cleaning ──
def clean_text(text):
    """Strip OCR artifacts: leading ‖, ‖, |, and whitespace"""
    return text.lstrip("‖―| \t")

def escape_tex(text):
    for char, repl in [('\\', r'\textbackslash{}'), ('{', r'\{'), ('}', r'\}'),
                       ('&', r'\&'), ('%', r'\%'), ('#', r'\#'),
                       ('$', r'\$'), ('_', r'\_'), ('~', r'\~{}'), ('^', r'\^{}')]:
        text = text.replace(char, repl)
    return text

def estimate_pt_width(text, font_size=12.0):
    """Estimate rendered width in pt. CJK ≈ font_size, Latin ≈ font_size*0.5"""
    w = 0.0
    for ch in text:
        if ord(ch) > 0x2000:  # CJK
            w += font_size
        elif ch.isascii() and ch.isalpha():  # Latin
            w += font_size * 0.52
        else:  # punctuation, digits, spaces
            w += font_size * 0.5
    return w

def line_ends_punc(t):
    return any(t.rstrip().endswith(p) for p in END_PUNC) if t else True

def is_page_number(t):
    s = t.strip()
    if re.match(r'^[·•‧]?\s*\d{1,4}\s*[·•‧]?$', s):
        return True
    return bool(re.match(r'^\d{1,4}$', s)) and len(s) <= 4

def is_footnote_start(t):
    s = t.strip()
    return bool(s) and s[0] in FN_CIRCLE

def is_footnote_cont(t):
    s = t.strip()
    if not s: return False
    if re.match(r'^\d{4}[:—\-]', s): return True
    if s.startswith('同上') or s.startswith('参见') or s.startswith('北京'): return True
    if re.match(r'^\d{1,4}[,]\d', s): return True
    return False

# ── Compute body baseline from coordinates ──
def compute_body_baseline(spot_lines, spot_coords, page_width_px):
    """Body baseline = Q1 of left-x from non-bookmark, non-footnote, non-page-number lines"""
    x_values = []
    for k in spot_lines:
        for i, line in enumerate(spot_lines[k]):
            t = line.strip()
            if not t or is_page_number(t): continue
            if is_footnote_start(t): continue
            polys = spot_coords.get(k, [])
            if i >= len(polys): continue
            if not polys[i]: continue
            xs = [p[0] for p in polys[i]]
            left = min(xs)
            if left > page_width_px * 0.4: continue  # bookmark
            x_values.append(left)
    x_values.sort()
    q1 = x_values[len(x_values)//4] if x_values else 0
    return q1


# ── Main ──
doc = fitz.open(SRC_PDF)
PW_PT = doc[0].rect.width
PH_PT = doc[0].rect.height
doc.close()
PW_MM = round(PW_PT * 0.3528, 0)
PH_MM = round(PH_PT * 0.3528, 0)

# Detect start page number
text_p0 = fitz.open(SRC_PDF)[0].get_text()
m = re.search(r'[•·]\s*(\d{1,4})\s*[•·]', text_p0)
START_PAGE = int(m.group(1)) if m else 1

spot_lines = json.load(open(SPOTTING_LINES))
spot_coords = json.load(open(SPOTTING_COORDS))

# Clean all lines of OCR artifacts
for k in spot_lines:
    spot_lines[k] = [clean_text(line) for line in spot_lines[k]]

num_pages = len(spot_lines)
total_lines = sum(len(v) for v in spot_lines.values())
print(f"Source: {SRC_PDF}, start={START_PAGE}, {PW_MM:.0f}x{PH_MM:.0f}mm")
print(f"Spotting: {num_pages} pages, {total_lines} lines")

# Compute page width in px (from coords)
page_width_px = max(
    max(pt[0] for pt in poly)
    for polys in spot_coords.values()
    for poly in polys if poly
)

# Body baseline
BODY_LEFT = compute_body_baseline(spot_lines, spot_coords, page_width_px)

# Font size and margins (data-driven)
FONT_SIZE = 12.0
BODY_RIGHT_PX = max(
    max(pt[0] for pt in poly)
    for k, polys in spot_coords.items()
    for i, poly in enumerate(polys)
    if poly and i < len(spot_lines.get(k, []))
    and spot_lines[k][i].strip()
    and not is_page_number(spot_lines[k][i].strip())
    and min(p[0] for p in poly) < page_width_px * 0.4  # exclude bookmarks
    and not is_footnote_start(spot_lines[k][i].strip())  # exclude fn starts
)
TEXT_WIDTH_PT = (BODY_RIGHT_PX - BODY_LEFT) / SCALE
MARGIN_PT = BODY_LEFT / SCALE
MARGIN_MM = round(MARGIN_PT * 0.3528, 1)

# Stretch (line spacing)
LINE_HEIGHT_PT = 20.0
STRETCH = LINE_HEIGHT_PT / FONT_SIZE

# Width threshold for \mbox skip: if estimated width > 102% of text width, unbox
WIDTH_OVERFLOW_THRESHOLD = TEXT_WIDTH_PT * 1.02

print(f"Body: left={BODY_LEFT}px, right={BODY_RIGHT_PX}px, width={TEXT_WIDTH_PT:.0f}pt")
print(f"Font: {FONT_SIZE}pt, Margin: {MARGIN_MM}mm, Stretch: {STRETCH:.2f}")
print(f"Overflow threshold: {WIDTH_OVERFLOW_THRESHOLD:.0f}pt")

# ── LaTeX header ──
header = f"""\\documentclass[{int(FONT_SIZE)}pt]{{article}}
\\usepackage{{xeCJK}}
\\usepackage[margin={MARGIN_MM}mm, paperwidth={PW_MM:.0f}mm, paperheight={PH_MM:.0f}mm]{{geometry}}
\\usepackage{{setspace}}
\\usepackage{{fancyhdr}}
\\setmainfont{{Noto Serif CJK SC}}
\\setCJKmainfont{{Noto Serif CJK SC}}
\\xeCJKsetup{{PunctStyle=kaiming}}
\\setlength{{\\parindent}}{{0pt}}
\\setstretch{{{STRETCH:.2f}}}
\\setcounter{{page}}{{{START_PAGE}}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\fancyfoot[C]{{\\thepage}}
\\renewcommand{{\\headrulewidth}}{{0pt}}
\\raggedright
\\sloppy
\\emergencystretch=1.5em
\\hyphenpenalty=100
\\exhyphenpenalty=80
\\begin{{document}}
"""

# ── Helper: render a single line with overflow-aware boxing ──
def render_line(text, font_size=FONT_SIZE, allow_break=False):
    """Return LaTeX for one line. If text would overflow, skip \\mbox."""
    est_w = estimate_pt_width(text, font_size)
    if est_w > WIDTH_OVERFLOW_THRESHOLD * (font_size / FONT_SIZE) or allow_break:
        # Line too wide for \mbox — let LaTeX break it
        return escape_tex(text) + '\\\\'
    return '\\mbox{' + escape_tex(text) + '}\\\\'

# ── Render pages ──
all_tex = []
INDENT_THRESHOLD_PX = 40  # raised from 30 to reduce false positives

for key in sorted(spot_lines.keys(), key=int):
    lines = spot_lines[key]
    polys = spot_coords.get(key, [])
    result = []
    in_fn = False

    # Classify + render in one pass
    for i in range(len(lines)):
        t = lines[i].strip()
        if i < len(polys) and polys[i]:
            xs = [p[0] for p in polys[i]]
            x_left = min(xs)
        else:
            x_left = 0

        # 1) Empty line
        if not t:
            result.append('\\medskip')
            continue

        # 2) Page number → skip
        if is_page_number(t):
            continue

        # 3) Bookmark (right-aligned, small font)
        if x_left > page_width_px * 0.4:
            if in_fn:
                result.append('}\\par')
                in_fn = False
            result.append('{\\footnotesize\\hfill ' + escape_tex(t) + '\\hfill\\null}\\par')
            continue

        # 4) Footnote start
        if is_footnote_start(t):
            if in_fn:
                result.append('}\\par')
            result.append('\\medskip\\hrule\\smallskip')
            result.append('{\\footnotesize')
            in_fn = True
            # Footnote lines: use \footnotesize (10pt) for width estimation
            result.append(render_line(t, font_size=10.0))
            continue

        # 5) Footnote continuation — keep ALL lines in footnote mode
        #    Footnotes always appear at page bottom in source; auto-close at
        #    page boundary or next bookmark. The old x_left-based auto-exit
        #    falsely closed footnotes when continuation lines aligned with body
        #    margin, causing Latin-heavy fn lines to render at body size → overflow.
        if in_fn:
            result.append(render_line(t, font_size=10.0))
            continue

        # 6) Body line
        escaped = escape_tex(t)
        indent_px = x_left - BODY_LEFT

        # Paragraph indent detection: indent > INDENT_THRESHOLD_PX → new paragraph
        if indent_px > INDENT_THRESHOLD_PX:
            est_w = estimate_pt_width(t, FONT_SIZE)
            if est_w > WIDTH_OVERFLOW_THRESHOLD:
                result.append('\\hspace{2em}' + escaped + '\\\\')
            else:
                result.append('\\hspace{2em}\\mbox{' + escaped + '}\\\\')
        else:
            est_w = estimate_pt_width(t, FONT_SIZE)
            if est_w > WIDTH_OVERFLOW_THRESHOLD:
                result.append(escaped + '\\\\')
            else:
                result.append('\\mbox{' + escaped + '}\\\\')

    if in_fn:
        result.append('}\\par')
    result.append('\\par\\newpage')
    all_tex.append('\n'.join(result))

latex_body = '\n'.join(all_tex)
latex = header + latex_body + '\n\\end{document}\n'

with open(TEX_FILE, 'w', encoding='utf-8') as f:
    f.write(latex)
print(f"TeX: {len(latex)} chars → {TEX_FILE}")

# Compile
r = subprocess.run(
    ['xelatex', '-interaction=nonstopmode', os.path.basename(TEX_FILE)],
    cwd=os.path.dirname(TEX_FILE), capture_output=True, text=True, timeout=120
)

pdf_tmp = TEX_FILE.replace('.tex', '.pdf')
if os.path.exists(pdf_tmp):
    if os.path.exists(OUT_PDF):
        os.remove(OUT_PDF)
    os.rename(pdf_tmp, OUT_PDF)
    pages = fitz.open(OUT_PDF).page_count
    errs = [l for l in (r.stderr+r.stdout).split('\n') if 'Error' in l]
    print(f"Done: {OUT_PDF} ({pages} pages, {len(errs)} errors)")
else:
    print("xelatex FAILED:")
    for l in (r.stdout+r.stderr).split('\n')[-30:]:
        if l.strip(): print(f"  {l[:150]}")
