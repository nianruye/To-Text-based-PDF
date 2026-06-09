"""
API-based PDF processor — replaces local PaddleOCR with PaddleOCR-VL API.
Zero heavy dependencies: only requests + subprocess (xelatex).
"""
import os, subprocess, asyncio, json, tempfile
from app.config import Config
from app.models.schemas import ProgressMessage


class PDFProcessor:
    """Orchestrates API OCR + xelatex rendering pipeline."""

    def __init__(self, config: Config):
        self.config = config

    async def process(self, job_id: str, input_pdf: str, progress_callback=None) -> str:
        work_dir = os.path.join(self.config.upload_dir, job_id)
        os.makedirs(work_dir, exist_ok=True)

        # Stage 1: Run API OCR — get spotting lines + coords + markdown
        await self._emit(progress_callback, job_id, "ocr", 10,
                         message="Running PaddleOCR-VL API...")

        lines_path, coords_path, md_path = await self._run_api_ocr(input_pdf, work_dir)

        await self._emit(progress_callback, job_id, "ocr", 90,
                         message="OCR complete")

        # Stage 2: Generate PDF with build_pdf_v13.py
        await self._emit(progress_callback, job_id, "generating", 0,
                         message="Generating PDF with xelatex...")

        output_path = os.path.join(self.config.output_dir, f"{job_id}_enhanced.pdf")
        os.makedirs(self.config.output_dir, exist_ok=True)

        await self._run_xelatex(input_pdf, output_path, lines_path, coords_path, md_path)

        await self._emit(progress_callback, job_id, "complete", 100,
                         download_url=f"/api/download/{job_id}",
                         message="Complete!")

        return output_path

    async def _run_api_ocr(self, pdf_path: str, work_dir: str):
        """Run spotting OCR and save lines, coords, and markdown files for v13."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run_api_ocr_sync, pdf_path, work_dir)

    def _parse_spotting_block(self, block):
        """Extract lines and polygons from a spotting block (same as run_spotting_ocr.py)."""
        import re
        lines, polys = [], []
        sr = block.get("spotting_res")
        if sr:
            for i, txt in enumerate(sr.get("rec_texts", [])):
                lines.append(txt)
                polys.append(sr["rec_polys"][i] if i < len(sr.get("rec_polys", [])) else None)
            if lines:
                return lines, polys
        content = block.get("block_content", "")
        if content:
            for raw_line in content.split("\n"):
                m = re.match(
                    r'^(\d+\.?\d*),(\d+\.?\d*)\s+(\d+\.?\d*),(\d+\.?\d*)\s+'
                    r'(\d+\.?\d*),(\d+\.?\d*)\s+(\d+\.?\d*),(\d+\.?\d*):\s*(.+)$',
                    raw_line.strip()
                )
                if m:
                    coords = [float(m.group(i)) for i in range(1, 9)]
                    poly = [[coords[0], coords[1]], [coords[2], coords[3]],
                            [coords[4], coords[5]], [coords[6], coords[7]]]
                    polys.append(poly)
                    lines.append(m.group(9).strip())
                elif raw_line.strip():
                    lines.append(raw_line.strip())
                    polys.append(None)
        return lines, polys

    def _run_api_ocr_sync(self, pdf_path: str, work_dir: str):
        """Full spotting OCR with auto PNG conversion for JPEG PDFs."""
        import requests, time, json as json_mod, fitz

        tok_file = "/tmp/paddle_token"
        if not os.path.exists(tok_file):
            raise RuntimeError("PaddleOCR token not found at /tmp/paddle_token")
        tok = open(tok_file).read().strip()

        # Check if PDF has JPEG images → needs per-page PNG conversion
        doc = fitz.open(pdf_path)
        needs_png = False
        for pi in range(min(3, doc.page_count)):
            for img in doc[pi].get_images(full=True):
                if img[2] > 1 or (img[8] and 'DCT' in str(img[8])):
                    needs_png = True; break
            if needs_png: break
        total_pages = doc.page_count
        doc.close()

        if needs_png:
            all_lines, all_coords = self._ocr_via_png(pdf_path, work_dir, total_pages, tok)
        else:
            JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
            headers = {"Authorization": "bearer " + tok}
            payload = {
                "model": "PaddleOCR-VL-1.6",
                "optionalPayload": json_mod.dumps({
                    "useDocOrientationClassify": False, "useDocUnwarping": False,
                    "useChartRecognition": False, "useLayoutDetection": False,
                    "promptLabel": "spotting", "temperature": 0,
                }),
            }
            raw = self._submit_and_poll(JOB_URL, headers, payload, pdf_path)
            all_lines, all_coords = self._parse_jsonl_response(raw)

        return self._save_ocr_files(all_lines, all_coords, work_dir)

    def _submit_and_poll(self, url, headers, payload, file_path):
        """Submit file to OCR API, poll until done, return raw response text."""
        import requests, time
        with open(file_path, "rb") as f:
            r = requests.post(url, headers=headers, data=payload, files={"file": f})
        r.raise_for_status()
        job_id = r.json()["data"]["jobId"]
        while True:
            r = requests.get(url + "/" + job_id, headers=headers)
            r.raise_for_status()
            d = r.json()
            if d["data"]["state"] == "done":
                rr = requests.get(d["data"]["resultUrl"]["jsonUrl"])
                rr.raise_for_status()
                return rr.text
            elif d["data"]["state"] == "failed":
                raise RuntimeError("OCR failed: " + d["data"].get("errorMsg", "unknown"))
            time.sleep(5)

    def _ocr_via_png(self, pdf_path, work_dir, total_pages, tok):
        """Convert each page to PNG, submit individually, merge results."""
        import fitz, os
        JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
        headers = {"Authorization": "bearer " + tok}
        import json as json_mod
        payload = {
            "model": "PaddleOCR-VL-1.6",
            "optionalPayload": json_mod.dumps({
                "useDocOrientationClassify": False, "useDocUnwarping": False,
                "useChartRecognition": False, "useLayoutDetection": False,
                "promptLabel": "spotting", "temperature": 0,
            }),
        }
        doc = fitz.open(pdf_path)
        all_lines, all_coords = {}, {}
        for pi in range(total_pages):
            pix = doc[pi].get_pixmap(dpi=200)
            png_path = os.path.join(work_dir, f"page_{pi:03d}.png")
            pix.save(png_path)
            raw = self._submit_and_poll(JOB_URL, headers, payload, png_path)
            pl, pp = self._parse_jsonl_single_page(raw)
            all_lines[str(pi)] = pl
            all_coords[str(pi)] = pp
            os.unlink(png_path)
        doc.close()
        return all_lines, all_coords

    def _parse_jsonl_single_page(self, raw_text):
        """Parse a single page from JSONL response."""
        import json as json_mod
        pl, pp = [], []
        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if not line: continue
            result = json_mod.loads(line)["result"]
            pl, pp = self._extract_spotting(result, pl, pp)
        pp = [[[round(c, 1) for c in pt] for pt in p] if p else None for p in pp]
        return pl, pp

    def _parse_jsonl_response(self, raw_text):
        """Parse multi-page JSONL response."""
        import json as json_mod
        all_lines, all_coords = {}, {}
        for page_idx, line in enumerate(raw_text.strip().split("\n")):
            line = line.strip()
            if not line: continue
            result = json_mod.loads(line)["result"]
            pl, pp = self._extract_spotting(result, [], [])
            all_lines[str(page_idx)] = pl
            all_coords[str(page_idx)] = [
                [[round(c, 1) for c in pt] for pt in p] if p else None for p in pp
            ]
        return all_lines, all_coords

    def _extract_spotting(self, result, pl, pp):
        """Extract spotting lines and polys from a result dict."""
        for res in result.get("layoutParsingResults", []):
            pr = res.get("layoutParsingResult", {})
            pruned = res.get("prunedResult", {})
            sr = pruned.get("spotting_res") or pr.get("spotting_res") or res.get("spotting_res")
            if sr and isinstance(sr, dict) and sr.get("rec_texts"):
                pl.extend(sr["rec_texts"])
                pp.extend(sr.get("rec_polys", []))
            else:
                blocks = pr.get("parsing_res_list", []) or pruned.get("parsing_res_list", [])
                if not blocks:
                    blocks = res.get("parsing_res_list", [])
                for blk in blocks:
                    bl, bp = self._parse_spotting_block(blk)
                    pl.extend(bl)
                    pp.extend(bp)
        return pl, pp

    def _save_ocr_files(self, all_lines, all_coords, work_dir):
        """Save spotting JSON files and generate markdown. Return file paths."""
        lines_path = os.path.join(work_dir, "spotting_lines.json")
        coords_path = os.path.join(work_dir, "spotting_coords.json")
        with open(lines_path, "w", encoding="utf-8") as f:
            json.dump(all_lines, f, ensure_ascii=False, indent=2)
        with open(coords_path, "w", encoding="utf-8") as f:
            json.dump(all_coords, f, ensure_ascii=False, indent=2)
        md_lines = []
        for k in sorted(all_lines.keys(), key=int):
            for ln in all_lines[k]:
                t = ln.strip()
                if not t: continue
                md_lines.append(t)
            md_lines.append("")
        md_path = os.path.join(work_dir, "ocr_markdown.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
        return lines_path, coords_path, md_path

    def _blocks_to_markdown(self, blocks: list) -> str:
        """Convert API OCR blocks to cleaned markdown with source indentation detection."""
        import re

        max_y2 = max((b.get("block_bbox", [0, 0, 0, 0])[3] for b in blocks), default=0)

        def is_page_number(item):
            content = item.get("block_content", "").strip()
            if not re.match(r'^\d{1,4}$', content):
                return False
            bbox = item.get("block_bbox", [])
            if len(bbox) != 4 or max_y2 <= 0:
                return False
            return (max_y2 - bbox[1]) / max_y2 <= 0.08

        # Detect source indentation: find modal x0 of body text blocks
        body_x0s = []
        for item in blocks:
            label = item.get("block_label", "text")
            bbox = item.get("block_bbox", [])
            if label in ("text", "paragraph_title") and len(bbox) == 4:
                body_x0s.append(bbox[0])
        modal_x0 = None
        if body_x0s:
            from collections import Counter
            rounded = [round(x, -1) for x in body_x0s]
            modal_x0 = Counter(rounded).most_common(1)[0][0]

        def is_indented(item):
            if modal_x0 is None:
                return False
            bbox = item.get("block_bbox", [])
            if len(bbox) != 4:
                return False
            return (bbox[0] - modal_x0) > 15  # 15px threshold

        body_blocks = []
        footnotes = []

        for item in blocks:
            label = item.get("block_label", "text")
            content = item.get("block_content", "").strip()
            if not content:
                continue
            if is_page_number(item):
                continue
            if label == "footnote":
                footnotes.append(content)
            elif label in ("header", "number"):
                continue
            elif label == "paragraph_title":
                body_blocks.append(("h2", content.replace("\n", " ")))
            elif label.startswith("title"):
                body_blocks.append(("h1", content))
            elif label == "section_header":
                body_blocks.append(("h3", content))
            elif label == "table":
                body_blocks.append(("table", content))
            else:
                # Mark if this block is indented in source
                ind = is_indented(item)
                body_blocks.append(("text", content, ind))

        lines = []
        end_punc = "。！？…）\"」』》"
        for item in body_blocks:
            btype = item[0]
            text = item[1]
            indented = item[2] if len(item) > 2 else False
            if btype == "h1":
                lines.append("# " + text)
            elif btype == "h2":
                lines.append("## " + text)
            elif btype == "h3":
                lines.append("### " + text)
            else:
                if lines and not lines[-1].startswith("#"):
                    prev_raw = lines[-1]
                    prev_clean = prev_raw.replace("<indent>", "").strip()
                    prev_was_indented = prev_raw.startswith("<indent>")
                    # Don't merge blocks with different indentation
                    if prev_was_indented == indented and prev_clean \
                       and not any(prev_clean.endswith(p) for p in end_punc):
                        lines[-1] = prev_clean + text
                        continue
                prefix = "<indent>\n" if indented else ""
                lines.append(prefix + text)

        body = "\n\n".join(lines)

        if footnotes:
            fn_lines = ['<div class="footnote">']
            for i, fn in enumerate(footnotes):
                fn_lines.append(fn)
                if i < len(footnotes) - 1:
                    fn_lines.append("<br>")
            fn_lines.append("</div>")
            body += "\n\n" + "\n".join(fn_lines)

        # Fix 1: clean $ ^{①} $ → <sup>①</sup> and other artifacts
        return self._clean_ocr(body)

    async def _run_xelatex(self, input_pdf: str, output_path: str,
                            lines_path: str, coords_path: str, md_path: str):
        """Generate PDF with build_pdf_v13.py."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self._run_xelatex_sync, input_pdf, output_path, lines_path, coords_path, md_path)

    def _run_xelatex_sync(self, input_pdf: str, output_path: str,
                           lines_path: str, coords_path: str, md_path: str):
        """Call build_pdf_v13.py with spotting lines, coords, and markdown."""
        script = "/opt/test/build_pdf_v13.py"
        result = subprocess.run(
            ["python3", script, input_pdf, output_path, lines_path, coords_path, md_path],
            capture_output=True, text=True, timeout=300
        )

        if not os.path.exists(output_path):
            raise RuntimeError(f"xelatex failed:\n{result.stderr[-1000:]}")

    def _spotting_to_markdown(self, content: str) -> str:
        """Convert spotting mode output (\\n\\n-separated lines) to markdown.
        Classifies lines as body/header/footnote/page_number by position."""
        import re

        lines = [l.strip() for l in content.split('\n\n') if l.strip()]
        if not lines:
            return ""

        body_lines = []
        header_lines = []
        footnote_lines = []

        total = len(lines)
        in_footnote = False
        for i, l in enumerate(lines):
            # Page number: last line, digit/· pattern
            if i == total - 1 and re.match(r'^[·•]?\s*\d{1,4}\s*[·•]?$', l):
                continue
            # Detect footnote start: ①②③ pattern, or already in footnote zone
            is_fn_marker = bool(re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩➀➁➂➃➄➅➆➇➈➉]', l))
            if is_fn_marker:
                in_footnote = True
            if in_footnote:
                footnote_lines.append(l)
                continue
            # Header: only the first line, short
            if i == 0 and len(l) < 35:
                header_lines.append(l)
                continue
            body_lines.append(l)

        result = []
        for h in header_lines:
            result.append('## ' + h)

        # Merge body lines into paragraphs (continuation detection)
        end_punc = '。！？…）」』》'
        para = []
        for l in body_lines:
            is_new = False
            if para:
                last = para[-1].strip()
                if last and any(last.endswith(p) for p in end_punc):
                    is_new = True
            if is_new:
                result.append(''.join(para))
                para = [l]
            else:
                para.append(l)
        if para:
            result.append(''.join(para))

        if footnote_lines:
            fn_block = ['<div class="footnote">']
            fn_block.extend(footnote_lines)
            fn_block.append('</div>')
            result.append('\n'.join(fn_block))

        body = '\n\n'.join(result)
        return self._clean_ocr(body)

    def _clean_ocr(self, raw_text: str) -> str:
        """Fix $ ^{①} $ → <sup>①</sup>, dedup, filter noise."""
        import re
        text = raw_text.replace('\\n', '\n')
        text = re.sub(r'\$\s*\^\{([^}]+)\}\s*\$', r'<sup>\1</sup>', text)
        text = re.sub(r'\s+<sup>', '<sup>', text)
        text = re.sub(r'</sup>[ \t]+', '</sup>', text)  # horizontal whitespace only — NOT newlines!
        text = re.sub(
            r'([\u4e00-\u9fff])\n(?![^\u4e00-\u9fff]*[，。；：、！？」』）\}\}\]\n])',
            r'\1', text
        )
        paras = [p.strip() for p in text.split('\n\n') if p.strip()]
        seen = set()
        unique = []
        for p in paras:
            norm = re.sub(r'\s+', '', p)
            if norm and norm not in seen:
                seen.add(norm)
                unique.append(p)
        filtered = []
        for p in unique:
            s = p.strip()
            if re.match(r'^\d{1,4}$', s): continue
            if re.match(r'^[\u4e00-\u9fff]$', s): continue
            if re.match(r'^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]+$', s): continue
            filtered.append(p)
        text = '\n\n'.join(filtered)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    async def _emit(self, callback, job_id, stage, progress, **kwargs):
        if callback:
            await callback(ProgressMessage(
                job_id=job_id, stage=stage, progress=progress, **kwargs
            ))
