     1|"""
     2|xelatex-based PDF generator — replaces fitz.insert_textbox with proper CJK typesetting.
     3|- PunctStyle=kaiming (开明式标点挤压)
     4|- Paragraph-aware indentation (only at real paragraph boundaries)
     5|- Auto page numbering matching source
     6|"""
     7|
     8|import os, re, subprocess, tempfile, fitz
     9|from app.models.schemas import PageResult, TextBlock, BlockStyle
    10|
    11|
    12|def _escape_tex(text: str) -> str:
    13|    """Escape LaTeX special chars, protecting \\textsuperscript blocks."""
    14|    parts = re.split(r'(\\textsuperscript\{[^}]+\})', text)
    15|    result = []
    16|    for p in parts:
    17|        if p.startswith('\\textsuperscript'):
    18|            result.append(p)
    19|        else:
    20|            for char, repl in [('\\', '\\textbackslash{}'), ('{', '\\{'), ('}', '\\}'),
    21|                               ('&', '\\&'), ('%', '\\%'), ('#', '\\#'),
    22|                               ('$', '\\$'), ('_', '\\_'), ('~', '\\~{}'),
    23|                               ('^', '\\^{}')]:
    24|                p = p.replace(char, repl)
    25|            result.append(p)
    26|    return ''.join(result)
    27|
    28|
    29|def _detect_start_page(original_pdf: str) -> int:
    30|    """Detect printed page number from first page of source PDF."""
    31|    doc = fitz.open(original_pdf)
    32|    text = doc[0].get_text()
    33|    doc.close()
    34|    m = re.search(r'[•·]\s*(\d{1,4})\s*[•·]', text)
    35|    return int(m.group(1)) if m else 1
    36|
    37|
    38|def generate_enhanced_pdf_xelatex(
    39|    original_pdf_path: str,
    40|    page_results: list[PageResult],
    41|    output_path: str,
    42|) -> str:
    43|    """Generate enhanced PDF with xelatex + xeCJK punctuation compression."""
    44|    
    45|    orig_doc = fitz.open(original_pdf_path)
    46|    page_w_pt = orig_doc[0].rect.width
    47|    page_h_pt = orig_doc[0].rect.height
    48|    orig_doc.close()
    49|
    50|    page_w_mm = round(page_w_pt * 0.3528, 0)
    51|    page_h_mm = round(page_h_pt * 0.3528, 0)
    52|    
    53|    # Compute font size from median block height
    54|    all_heights = []
    55|    for pr in page_results:
    56|        for blk in pr.blocks:
    57|            if len(blk.bbox) == 4 and blk.style == BlockStyle.BODY:
    58|                h = blk.bbox[3] - blk.bbox[1]
    59|                if 5 < h < 200:
    60|                    all_heights.append(h)
    61|    
    62|    if all_heights:
    63|        all_heights.sort()
    64|        median_h_px = all_heights[len(all_heights) // 2]
    65|        scale = pr.height / page_h_pt if pr.height > 0 else 2
    66|        line_height_pt = median_h_px / scale
    67|        font_size = max(9, min(14, round(line_height_pt / 1.7, 1)))
    68|    else:
    69|        font_size = 12.0
    70|        median_h_px = 20  # sensible default
    71|
    72|    # Margin for ~25 chars/line
    73|    chars_per_line = 25
    74|    text_width_pt = chars_per_line * font_size
    75|    margin_mm = round((page_w_pt - text_width_pt) / 2 * 0.3528, 1)
    76|    stretch = round(font_size * 1.8 / {10: 12, 11: 13.6, 12: 14.5}.get(
    77|        int(round(font_size)), 14.5), 2)
    78|    
    79|    start_page = _detect_start_page(original_pdf_path)
    80|
    81|    # Build LaTeX from blocks
    82|    latex_pages = []
    83|    
    84|    for pr in page_results:
    85|        if not pr.was_image_based or pr.is_blank:
    86|            continue
    87|        
    88|        # Sort blocks by reading_order, then y position
    89|        blocks = sorted(pr.blocks, key=lambda b: (b.reading_order, b.bbox[1] if len(b.bbox) >= 4 else 0))
    90|        
    91|        page_lines = []
    92|        para_buf = []  # accumulate text for current paragraph
    93|        
    94|        for blk in blocks:
    95|            text = blk.text.strip()
    96|            if not text:
    97|                continue
    98|            
    99|            # Detect footnotes (small text at page bottom)
   100|            is_footnote = False
   101|            if len(blk.bbox) >= 4 and pr.height > 0:
   102|                y_bottom_pct = blk.bbox[1] / pr.height
   103|                block_h = blk.bbox[3] - blk.bbox[1]
   104|                if y_bottom_pct > 0.75 and block_h < median_h_px * 0.85:
   105|                    is_footnote = True
   106|            
   107|            # Detect page numbers (small centered text at bottom)
   108|            is_page_num = False
   109|            if re.match(r'^\d{1,4}$', text):
   110|                if len(blk.bbox) >= 4:
   111|                    y_bottom = blk.bbox[3] / pr.height
   112|                    x_center = (blk.bbox[0] + blk.bbox[2]) / 2 / pr.width
   113|                    if y_bottom > 0.9 and 0.35 < x_center < 0.65:
   114|                        is_page_num = True
   115|            
   116|            if is_page_num:
   117|                continue  # skip page numbers — handled by xelatex footer
   118|            
   119|            if is_footnote:
   120|                # Flush current paragraph
   121|                if para_buf:
   122|                    page_lines.append('\\hspace{2em}' + ' '.join(para_buf) + '\\\\par')
   123|                    para_buf = []
   124|                # Add footnote
   125|                escaped = _escape_tex(text)
   126|                page_lines.append('\\\\medskip\\\\hrule\\\\smallskip')
   127|                page_lines.append('{\\\\footnotesize ' + escaped + '\\\\par}')
   128|                page_lines.append('\\\\pagebreak')
   129|                continue
   130|            
   131|            if blk.style == BlockStyle.HEADING:
   132|                if para_buf:
   133|                    page_lines.append('\\hspace{2em}' + ' '.join(para_buf) + '\\\\par')
   134|                    para_buf = []
   135|                page_lines.append('\\\\subsection*{' + text + '}')
   136|                continue
   137|            
   138|            # Body text: merge into paragraphs
   139|            # Check if this block starts a new paragraph
   140|            # (looks for sentence-ending punctuation in previous blocks)
   141|            if para_buf and para_buf[-1].strip():
   142|                last_char = para_buf[-1].strip()[-1] if para_buf[-1].strip() else ''
   143|                if last_char in '。！？…）\"' and text:
   144|                    # End of sentence → new paragraph
   145|                    page_lines.append('\\hspace{2em}' + ' '.join(para_buf) + '\\\\par')
   146|                    para_buf = [text]
   147|                else:
   148|                    # Continuation
   149|                    para_buf.append(text)
   150|            else:
   151|                para_buf.append(text)
   152|        
   153|        # Flush remaining paragraph
   154|        if para_buf:
   155|            page_lines.append('\\hspace{2em}' + ' '.join(para_buf) + '\\\\par')
   156|        
   157|        if page_lines:
   158|            latex_pages.append('\n'.join(page_lines))
   159|
   160|    # Write LaTeX and compile
   161|    tex_content = f'''\\documentclass[{int(round(font_size))}pt]{{article}}
   162|\\usepackage{{xeCJK}}
   163|\\usepackage[margin={margin_mm}mm, paperwidth={page_w_mm}mm, paperheight={page_h_mm}mm]{{geometry}}
   164|\\usepackage{{setspace}}
   165|\\usepackage{{fancyhdr}}
   166|\\setmainfont{{Noto Serif CJK SC}}
   167|\\setCJKmainfont{{Noto Serif CJK SC}}
   168|\\xeCJKsetup{{PunctStyle=kaiming}}
   169|\\setlength{{\\parindent}}{{0pt}}
   170|\\setstretch{{{stretch}}}
   171|\\setcounter{{page}}{{{start_page}}}
   172|\\pagestyle{{fancy}}
   173|\\fancyhf{{}}
   174|\\fancyfoot[C]{{\\thepage}}
   175|\\renewcommand{{\\headrulewidth}}{{0pt}}
   176|\\begin{{document}}
   177|{chr(10).join(latex_pages)}
   178|\\end{{document}}
   179|'''
   180|
   181|    # Write to temp file and compile
   182|    tmpdir = tempfile.mkdtemp()
   183|    tex_path = os.path.join(tmpdir, 'output.tex')
   184|    with open(tex_path, 'w', encoding='utf-8') as f:
   185|        f.write(tex_content)
   186|
   187|    result = subprocess.run(
   188|        ['xelatex', '-interaction=nonstopmode', 'output.tex'],
   189|        cwd=tmpdir, capture_output=True, text=True, timeout=120
   190|    )
   191|
   192|    pdf_tmp = os.path.join(tmpdir, 'output.pdf')
   193|    if os.path.exists(pdf_tmp):
   194|        os.replace(pdf_tmp, output_path)
   195|    else:
   196|        raise RuntimeError(f"xelatex failed: {result.stderr[-500:]}")
   197|
   198|    # Cleanup
   199|    for f in os.listdir(tmpdir):
   200|        os.unlink(os.path.join(tmpdir, f))
   201|    os.rmdir(tmpdir)
   202|
   203|    return output_path
   204|