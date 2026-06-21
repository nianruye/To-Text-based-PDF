
See PIPELINE_SYNC.md for full context. Key points:

1. PDF rendering now uses xelatex (not WeasyPrint) — PunctStyle=kaiming for CJK punctuation compression
2. Paragraph-aware indentation: only real paragraph breaks indent, cross-page continuations don't
3. Page numbers auto-detected from source PDF
4. build_pdf_v13.py is the main entry point; run with: python3 build_pdf_v13.py input.pdf output.pdf spotting_lines.json spotting_coords.json [ocr_titles.json] (argv: 1=src 2=out 3=spotting_lines 4=spotting_coords 5=ocr_titles 6=markdown)
5. OCR via run_spotting_ocr.py (spotting mode, line-level) → cached as spotting_*.json; titles via extract_titles.py → ocr_titles*.json; clean_markdown handles $ ^{①} $ → <sup>①</sup>
6. Web app at localhost:8765 uses API-based PaddleOCR (no local model needed)
7. Three LaTeX tricks: \parindent=0pt + \hspace{2em} for explicit paragraph indent (not \everypar hack), \xeCJKsetup{PunctStyle=kaiming} for punctuation compression, \setcounter{page}{N} for page numbering
8. post_process_pages merges cross-page sentence fragments; TOC pages use dedicated group_toc_rows() for text↔page-number pairing with dotfill
