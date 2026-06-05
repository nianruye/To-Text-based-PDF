#!/usr/bin/env python3
"""xelatex PDF v11 — natural CJK paragraph justification
- Groups body lines into paragraphs, lets xelatex handle line-breaking + justification
- Narrower textwidth (~365pt) to match natural CJK text metrics
- Removes \raggedright and \mbox for body text
- Footnotes/bookmarks/page-numbers unchanged
"""
import json, os, re, subprocess, sys
import fitz

SRC_PDF = sys.argv[1] if len(sys.argv) > 1 else "/opt/test/优化前.pdf"
OUT_PDF = sys.argv[2] if len(sys.argv) > 2 else "/opt/test/最终版_v11.pdf"
SPOTTING_LINES = "/opt/test/spotting_lines.json"
SPOTTING_COORDS = "/opt/test/spotting_coords.json"
TEX_FILE = "/tmp/xelatex_build_v11.tex"

SCALE = 2.0
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
    if re.match(r'^[·•‧]?\s*\d{1,4}\s*[·•‧]?$', s):
        return True
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

# ── Main ──
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
FONT_SIZE = 12.0

MARGIN_PT = BODY_LEFT / SCALE
MARGIN_MM = round(MARGIN_PT * 0.3528, 1)
RIGHT_MARGIN_MM = MARGIN_MM  # symmetric margins

LINE_HEIGHT_PT = 20.0; STRETCH = LINE_HEIGHT_PT / FONT_SIZE
INDENT_THRESHOLD_PX = 40

print(f"Source: {SRC_PDF}, start={START_PAGE}, {PW_MM:.0f}x{PH_MM:.0f}mm")
print(f"Margins: {MARGIN_MM}mm, Font: {FONT_SIZE}pt, Stretch: {STRETCH:.2f}")

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
\\tolerance=500
\\emergencystretch=0.5em
\\begin{{document}}
"""

# ── Pre-scan: detect cross-page paragraph continuations ──
sorted_keys = sorted(spot_lines.keys(), key=int)
page_continues = {}

def get_last_body_line(page_key):
    for line in reversed(spot_lines[page_key]):
        t = line.strip()
        if t and not is_page_number(t) and not is_footnote_start(t):
            return t
    return ''

def get_first_body_indent(page_key):
    polys = spot_coords.get(page_key, [])
    for i, line in enumerate(spot_lines[page_key]):
        t = line.strip()
        if not t or is_page_number(t) or is_footnote_start(t): continue
        if i < len(polys) and polys[i]:
            left = min(p[0] for p in polys[i])
            if left <= page_width_px * 0.4:
                return left - BODY_LEFT
    return 999

CHAPTER_MARKERS = ('第一部分', '第四章', '第', '马克思价值理论', '马克思主义')

for idx, key in enumerate(sorted_keys):
    if idx >= len(sorted_keys) - 1:
        page_continues[key] = False
        continue
    next_key = sorted_keys[idx + 1]
    last = get_last_body_line(key)
    ends_punc = last and last[-1] in '。！？…》）』」'
    next_indent = get_first_body_indent(next_key)
    next_is_cont = next_indent <= INDENT_THRESHOLD_PX
    next_first = ''
    for line in spot_lines[next_key]:
        t = line.strip()
        if t and not is_page_number(t):
            next_first = t
            break
    next_is_header = any(next_first.startswith(m) for m in CHAPTER_MARKERS) if next_first else False
    page_continues[key] = (not ends_punc) and next_is_cont and not next_is_header

# ── Render ──
all_tex = []

for key in sorted_keys:
    lines = spot_lines[key]
    polys = spot_coords.get(key, [])
    result = []
    in_fn = False
    items = []
    for i in range(len(lines)):
        t = lines[i].strip()
        if i < len(polys) and polys[i]:
            x_left = min(p[0] for p in polys[i])
        else:
            x_left = 0
        items.append({'text': t, 'x_left': x_left, 'idx': i})

    # Render with paragraph grouping for body text
    i = 0
    fn_rule_added = False  # only one \hrule per page
    while i < len(items):
        item = items[i]; t = item['text']; x_left = item['x_left']

        if not t:
            result.append('\\medskip')
            i += 1; continue
        if is_page_number(t):
            i += 1; continue

        # Bookmark
        if x_left > page_width_px * 0.4:
            result.append('{\\footnotesize\\hfill ' + escape_tex(t) + '\\hfill\\null}\\par')
            i += 1; continue

        # Footnote start — group this footnote's lines into a paragraph
        if is_footnote_start(t):
            # Collect all lines belonging to this footnote
            fn_lines = [t]
            i += 1
            while i < len(items):
                it = items[i]; tt = it['text'].strip()
                if not tt or is_page_number(tt) or is_footnote_start(tt) or it['x_left'] > page_width_px * 0.4:
                    break
                fn_lines.append(tt)
                i += 1

            fn_text = ''.join(fn_lines)
            if not fn_rule_added:
                result.append('\\smallskip\\hrule\\smallskip')
                fn_rule_added = True
            result.append('{\\footnotesize ' + escape_tex(fn_text) + '\\par}')
            in_fn = True
            continue

        # Not a footnote start, but we might be in footnote mode from earlier
        # (this shouldn't happen with the grouping above, but be safe)
        if in_fn:
            i += 1; continue

        # ── Body text: group into paragraph(s), merging short ones ──
        para_lines = []
        para_start_i = i
        while i < len(items):
            it = items[i]; tt = it['text'].strip()
            if not tt or is_page_number(tt) or is_footnote_start(tt) or it['x_left'] > page_width_px * 0.4:
                break
            # Check if this is a new paragraph (indented)
            if para_lines and (it['x_left'] - BODY_LEFT) > INDENT_THRESHOLD_PX:
                # Check if breaking here would leave a very short last line
                current_text = ''.join(para_lines)
                cjk = sum(1 for c in current_text if ord(c) > 0x2000)
                est = cjk / 37.0
                frac = est - int(est)
                if 0 < frac < 0.5 and est < 2.0 and est > 1.0:
                    # Merging: skip the indent break, continue collecting
                    pass
                else:
                    break
            para_lines.append(tt)
            i += 1

        if para_lines:
            para_text = ''.join(para_lines)
            has_indent = (items[para_start_i]['x_left'] - BODY_LEFT) > INDENT_THRESHOLD_PX

            # Check if this is the last body paragraph & page continues cross-page
            remaining_body = False
            for j in range(i, len(items)):
                it2 = items[j]; tt2 = it2['text'].strip()
                if tt2 and not is_page_number(tt2) and not is_footnote_start(tt2) \
                   and it2['x_left'] <= page_width_px * 0.4:
                    remaining_body = True
                    break
            crosses_page = page_continues.get(key, False) and not remaining_body

            if crosses_page and len(para_lines) > 1:
                # Cross-page continuation: keep line-by-line to match source
                for li, line in enumerate(para_lines):
                    prefix2 = '\\hspace{2em}' if (li == 0 and has_indent) else ''
                    result.append(prefix2 + '\\mbox{' + escape_tex(line) + '}\\\\')
            else:
                prefix = '\\hspace{2em}' if has_indent else ''
                result.append(prefix + escape_tex(para_text) + '\\par')

    result.append('\\par\\newpage')
    all_tex.append('\n'.join(result))

latex_body = '\n'.join(all_tex)
latex = header + latex_body + '\n\\end{document}\n'

with open(TEX_FILE, 'w', encoding='utf-8') as f:
    f.write(latex)
print(f"TeX: {len(latex)} chars → {TEX_FILE}")

r = subprocess.run(
    ['xelatex', '-interaction=nonstopmode', os.path.basename(TEX_FILE)],
    cwd=os.path.dirname(TEX_FILE), capture_output=True, text=True, timeout=120
)

pdf_tmp = TEX_FILE.replace('.tex', '.pdf')
if os.path.exists(pdf_tmp):
    if os.path.exists(OUT_PDF): os.remove(OUT_PDF)
    os.rename(pdf_tmp, OUT_PDF)
    pages = fitz.open(OUT_PDF).page_count
    errs = [l for l in (r.stderr+r.stdout).split('\n') if 'Error' in l]
    print(f"Done: {OUT_PDF} ({pages} pages, {len(errs)} errors)")
else:
    print("xelatex FAILED:")
    for l in (r.stdout+r.stderr).split('\n')[-30:]:
        if l.strip(): print(f"  {l[:150]}")
