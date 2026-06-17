#!/usr/bin/env python3
"""Step 1: Full spotting OCR on 20 pages."""

import json, os, re, sys, time, requests, fitz

TOKEN_FILE = "/tmp/paddle_token"
INPUT_PDF = sys.argv[1] if len(sys.argv) > 1 else "/opt/test/优化前.pdf"
OUT_LINES = sys.argv[2] if len(sys.argv) > 2 else "/opt/test/spotting_lines.json"
OUT_COORDS = sys.argv[3] if len(sys.argv) > 3 else "/opt/test/spotting_coords.json"
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
MODEL = "PaddleOCR-VL-1.6"

tok = open(TOKEN_FILE).read().strip()
HEADERS = {"Authorization": "bearer " + tok}
PAYLOAD = {
    "model": MODEL,
    "optionalPayload": json.dumps({
        "useLayoutDetection": True,  # 启用版面分析，获取标题标记和字体信息
        "promptLabel": "spotting",
        "temperature": 0,
    }),
}


def parse_spotting_line(raw_line):
    raw_line = raw_line.strip()
    if not raw_line:
        return None, None
    m = re.match(
        r'^(\d+\.?\d*),(\d+\.?\d*)\s+(\d+\.?\d*),(\d+\.?\d*)\s+'
        r'(\d+\.?\d*),(\d+\.?\d*)\s+(\d+\.?\d*),(\d+\.?\d*):\s*(.+)$',
        raw_line
    )
    if m:
        coords = [float(m.group(i)) for i in range(1, 9)]
        poly = [
            [coords[0], coords[1]], [coords[2], coords[3]],
            [coords[4], coords[5]], [coords[6], coords[7]],
        ]
        return poly, m.group(9).strip()
    if not re.match(r'^\d', raw_line):
        return None, raw_line
    return None, None


def extract_from_block(block):
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
            poly, txt = parse_spotting_line(raw_line)
            if txt:
                lines.append(txt)
                polys.append(poly)
            elif raw_line.strip():
                lines.append(raw_line.strip())
                polys.append(None)
    return lines, polys


def needs_png_conversion(filepath):
    """Check if PDF has non-bitonal images (JPEG, etc.) that spotting API can't handle."""
    doc = fitz.open(filepath)
    for pi in range(min(3, doc.page_count)):
        for img in doc[pi].get_images(full=True):
            bpc = img[2]   # bits per component
            filt = img[8]  # filter/compression
            if bpc > 1 or (filt and 'DCT' in str(filt)):
                doc.close()
                return True
    doc.close()
    return False


def process_pdf_via_png(filepath):
    """Convert PDF pages to PNG, send each to spotting API, merge results.
    启用版面分析后，提取 block_label 识别标题类型。"""
    doc = fitz.open(filepath)
    all_lines, all_coords, all_labels = {}, {}, {}

    for pi in range(doc.page_count):
        page = doc[pi]
        pix = page.get_pixmap(dpi=200)
        png_path = f"/tmp/spotting_page_{pi:03d}.png"
        pix.save(png_path)

        print(f"Page {pi+1}/{doc.page_count}: uploading PNG {pix.width}x{pix.height}...")
        with open(png_path, "rb") as f:
            r = requests.post(JOB_URL, headers=HEADERS, data=PAYLOAD, files={"file": f})
        r.raise_for_status()
        job_id = r.json()["data"]["jobId"]

        # Poll
        while True:
            rr = requests.get(JOB_URL + "/" + job_id, headers=HEADERS)
            rr.raise_for_status()
            state = rr.json()["data"]["state"]
            if state == "done":
                jsonl_url = rr.json()["data"]["resultUrl"]["jsonUrl"]
                break
            elif state == "failed":
                raise RuntimeError(f"Page {pi+1} failed: " + rr.json()["data"].get("errorMsg", "unknown"))
            time.sleep(2)

        # Download and parse (启用版面分析后的新格式)
        rr = requests.get(jsonl_url)
        rr.raise_for_status()
        for line in rr.text.strip().split("\n"):
            line = line.strip()
            if not line: continue
            result = json.loads(line)["result"]

            # 从 layoutParsingResults 提取 parsing_res_list
            lpr_list = result.get("layoutParsingResults", [])
            if not lpr_list:
                continue
            pr = lpr_list[0].get("prunedResult", {})
            blocks = pr.get("parsing_res_list", [])

            pl, pp, pb = [], [], []  # texts, polys, labels
            for blk in blocks:
                label = blk.get("block_label", "text")
                content = blk.get("block_content", "")
                poly_pts = blk.get("block_polygon_points") or blk.get("block_bbox")

                if content:
                    pl.append(content)
                    pb.append(label)
                    # 转换 polygon 为标准格式
                    if poly_pts:
                        if isinstance(poly_pts, list) and len(poly_pts) >= 4:
                            # 已经是 polygon 格式
                            pp.append([[round(c, 1) for c in pt] for pt in poly_pts[:4]])
                        elif isinstance(poly_pts, dict) or len(poly_pts) == 4 and isinstance(poly_pts[0], (int, float)):
                            # bbox 格式 [x1, y1, x2, y2]，转换为 polygon
                            x1, y1, x2, y2 = poly_pts[:4]
                            pp.append([[round(x1,1), round(y1,1)], [round(x2,1), round(y1,1)],
                                      [round(x2,1), round(y2,1)], [round(x1,1), round(y2,1)]])
                        else:
                            pp.append(None)
                    else:
                        pp.append(None)

            all_lines[str(pi)] = pl
            all_coords[str(pi)] = pp
            all_labels[str(pi)] = pb

        os.unlink(png_path)
        print(f"  {len(pl)} lines, titles: {sum(1 for l in pb if 'title' in l)}")

    doc.close()
    return all_lines, all_coords, all_labels


def process_pdf(filepath):
    """直接上传 PDF（非 PNG 转换路径）。启用版面分析后提取 block_label。"""
    # Check if PDF needs PNG conversion
    if needs_png_conversion(filepath):
        print(f"PDF has non-bitonal images, converting to PNG pages...")
        return process_pdf_via_png(filepath)

    print(f"Uploading: {filepath}")
    with open(filepath, "rb") as f:
        r = requests.post(JOB_URL, headers=HEADERS, data=PAYLOAD, files={"file": f})
    r.raise_for_status()
    job_id = r.json()["data"]["jobId"]
    print(f"Job: {job_id}")
    while True:
        r = requests.get(JOB_URL + "/" + job_id, headers=HEADERS)
        r.raise_for_status()
        d = r.json()
        state = d["data"]["state"]
        if state == "done":
            jsonl_url = d["data"]["resultUrl"]["jsonUrl"]
            print("Done, downloading...")
            break
        elif state == "failed":
            raise RuntimeError("Failed: " + d["data"].get("errorMsg", "unknown"))
        print(f"  state={state}")
        time.sleep(5)
    rr = requests.get(jsonl_url)
    rr.raise_for_status()
    page_lines, page_coords, page_labels = {}, {}, {}
    for page_idx, line in enumerate(rr.text.strip().split("\n")):
        line = line.strip()
        if not line:
            continue
        result = json.loads(line)["result"]

        # 从 layoutParsingResults 提取 parsing_res_list（新格式）
        lpr_list = result.get("layoutParsingResults", [])
        if lpr_list:
            pr = lpr_list[0].get("prunedResult", {})
            blocks = pr.get("parsing_res_list", [])
            pl, pp, pb = [], [], []
            for blk in blocks:
                label = blk.get("block_label", "text")
                content = blk.get("block_content", "")
                poly_pts = blk.get("block_polygon_points") or blk.get("block_bbox")
                if content:
                    pl.append(content)
                    pb.append(label)
                    if poly_pts:
                        if isinstance(poly_pts, list) and len(poly_pts) >= 4 and isinstance(poly_pts[0], list):
                            pp.append([[round(c, 1) for c in pt] for pt in poly_pts[:4]])
                        else:
                            pp.append(None)
                    else:
                        pp.append(None)
        else:
            # 兼容旧格式（未启用版面分析）
            pl, pp = [], []
            for res in result.get("layoutParsingResults", []):
                pr = res.get("layoutParsingResult", {})
                blocks = pr.get("parsing_res_list", [])
                if not blocks:
                    blocks = pr.get("prunedResult", {}).get("parsing_res_list", [])
                if not blocks:
                    blocks = res.get("parsing_res_list", [])
                if blocks:
                    for blk in blocks:
                        bl, bp = extract_from_block(blk)
                        pl.extend(bl)
                        pp.extend(bp)
                else:
                    sr = res.get("spotting_res") or pr.get("spotting_res")
                    if sr:
                        pl.extend(sr.get("rec_texts", []))
                        pp.extend(sr.get("rec_polys", []))
            pb = ["text"] * len(pl)  # 旧格式无 label，默认 text

        page_lines[str(page_idx)] = pl
        page_coords[str(page_idx)] = pp
        page_labels[str(page_idx)] = pb
        titles = sum(1 for l in pb if "title" in l)
        print(f"Page {page_idx}: {len(pl)} lines, titles: {titles}")
    return page_lines, page_coords, page_labels


if __name__ == "__main__":
    print(f"Spotting OCR (layout detection ON): {INPUT_PDF}")
    lines_data, coords_data, labels_data = process_pdf(INPUT_PDF)
    total = sum(len(v) for v in lines_data.values())
    titles_total = sum(sum(1 for l in v if "title" in l) for v in labels_data.values())
    print(f"Total: {len(lines_data)} pages, {total} lines, {titles_total} titles")

    # 输出 lines 和 coords（向后兼容）
    with open(OUT_LINES, "w", encoding="utf-8") as f:
        json.dump(lines_data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {OUT_LINES}")
    cs = {}
    for k, polys in coords_data.items():
        cs[k] = [
            [[round(c, 1) for c in pt] for pt in p] if p else None
            for p in polys
        ]
    with open(OUT_COORDS, "w", encoding="utf-8") as f:
        json.dump(cs, f, ensure_ascii=False, indent=2)
    print(f"Saved: {OUT_COORDS}")

    # 输出 labels（新增：版面分析标签，识别标题类型）
    base, ext = os.path.splitext(OUT_LINES)
    out_labels = base + "_labels" + ext
    with open(out_labels, "w", encoding="utf-8") as f:
        json.dump(labels_data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {out_labels}")
    print("Step 1 complete.")
