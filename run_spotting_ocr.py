#!/usr/bin/env python3
"""Step 1: Full spotting OCR on 20 pages."""

import json, os, re, sys, time, requests

TOKEN_FILE = "/tmp/paddle_token"
INPUT_PDF = "/opt/test/优化前.pdf"
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
MODEL = "PaddleOCR-VL-1.6"
OUT_LINES = "/opt/test/spotting_lines.json"
OUT_COORDS = "/opt/test/spotting_coords.json"

tok = open(TOKEN_FILE).read().strip()
HEADERS = {"Authorization": "bearer " + tok}
PAYLOAD = {
    "model": MODEL,
    "optionalPayload": json.dumps({
        "useLayoutDetection": False,
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


def process_pdf(filepath):
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
    page_lines, page_coords = {}, {}
    for page_idx, line in enumerate(rr.text.strip().split("\n")):
        line = line.strip()
        if not line:
            continue
        result = json.loads(line)["result"]
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
        page_lines[str(page_idx)] = pl
        page_coords[str(page_idx)] = pp
        print(f"Page {page_idx}: {len(pl)} lines")
    return page_lines, page_coords


if __name__ == "__main__":
    print(f"Spotting OCR: {INPUT_PDF}")
    lines_data, coords_data = process_pdf(INPUT_PDF)
    total = sum(len(v) for v in lines_data.values())
    print(f"Total: {len(lines_data)} pages, {total} lines")
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
    print("Step 1 complete.")
