#!/usr/bin/env python3
"""Step 1: Full spotting OCR on 20 pages."""

import json, os, re, sys, time, tempfile, shutil, threading, requests, fitz
from concurrent.futures import ThreadPoolExecutor

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

BATCH_SIZE = 90  # PaddleOCR-VL API 单次 ≤100 页,留余量防收紧
PNG_OCR_WORKERS = 8  # 扫描书 PNG 逐页 OCR 并发度(API 限流时调低)


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


def _ocr_png_page(png_path):
    """上传单页 PNG → 轮询 → 下载 jsonl → 解析版面块。
    返回 (lines, polys, labels)。保留 PNG 路径原有的 bbox/dict 坐标转换逻辑。"""
    with open(png_path, "rb") as f:
        r = requests.post(JOB_URL, headers=HEADERS, data=PAYLOAD, files={"file": f})
    r.raise_for_status()
    job_id = r.json()["data"]["jobId"]
    while True:
        rr = requests.get(JOB_URL + "/" + job_id, headers=HEADERS)
        rr.raise_for_status()
        state = rr.json()["data"]["state"]
        if state == "done":
            jsonl_url = rr.json()["data"]["resultUrl"]["jsonUrl"]
            break
        elif state == "failed":
            raise RuntimeError("PNG OCR failed: " + rr.json()["data"].get("errorMsg", "unknown"))
        time.sleep(2)
    rr = requests.get(jsonl_url)
    rr.raise_for_status()
    pl, pp, pb = [], [], []
    for line in rr.text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        result = json.loads(line)["result"]
        lpr_list = result.get("layoutParsingResults", [])
        if not lpr_list:
            continue
        pr = lpr_list[0].get("prunedResult", {})
        blocks = pr.get("parsing_res_list", [])
        for blk in blocks:
            label = blk.get("block_label", "text")
            content = blk.get("block_content", "")
            poly_pts = blk.get("block_polygon_points") or blk.get("block_bbox")
            if content:
                pl.append(content)
                pb.append(label)
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
    return pl, pp, pb


def _ocr_png_page_with_retry(png_path, retries=2, backoff=5):
    """单页 PNG OCR 带重试(网络错/API 5xx/failed 状态)。耗尽抛最后异常。"""
    last = None
    for attempt in range(retries + 1):
        try:
            return _ocr_png_page(png_path)
        except Exception as e:
            last = e
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
    raise last


def process_pdf_via_png(filepath):
    """扫描书路径:渲染每页 PNG → 并发上传 OCR → 合并。
    主线程串行渲染(fitz 非线程安全),ThreadPoolExecutor 并发上传/轮询/解析。
    单页失败重试后仍失败则置空 + 记录 + 继续(不因一页废全本)。"""
    doc = fitz.open(filepath)
    n = doc.page_count

    # 阶段1: 主线程串行渲染所有页为 PNG(fitz 非线程安全)
    print(f"Rendering {n} pages @200dpi (serial)...")
    png_paths = []
    for pi in range(n):
        pix = doc[pi].get_pixmap(dpi=200)
        png_path = f"/tmp/spotting_page_{pi:03d}.png"
        pix.save(png_path)
        png_paths.append(png_path)
        if (pi + 1) % 25 == 0 or pi + 1 == n:
            print(f"  rendered {pi + 1}/{n}")
    doc.close()

    # 阶段2: 并发上传/轮询/解析
    all_lines, all_coords, all_labels = {}, {}, {}
    failed = []
    done = [0]
    lock = threading.Lock()

    def worker(pi):
        try:
            pl, pp, pb = _ocr_png_page_with_retry(png_paths[pi])
        except Exception as e:
            pl, pp, pb = [], [], []
            with lock:
                failed.append((pi, str(e)[:80]))
        with lock:
            all_lines[str(pi)] = pl
            all_coords[str(pi)] = pp
            all_labels[str(pi)] = pb
            done[0] += 1
            if done[0] % 10 == 0 or done[0] == n:
                print(f"  OCR {done[0]}/{n}")
        try:
            os.unlink(png_paths[pi])
        except OSError:
            pass

    print(f"OCR {n} pages (x{PNG_OCR_WORKERS} workers)...")
    with ThreadPoolExecutor(max_workers=PNG_OCR_WORKERS) as ex:
        list(ex.map(worker, range(n)))

    total = sum(len(v) for v in all_lines.values())
    titles = sum(sum(1 for l in v if "title" in l) for v in all_labels.values())
    print(f"PNG OCR done: {n} pages, {total} lines, {titles} titles, {len(failed)} failed")
    if failed:
        print(f"⚠️ 失败页(已置空): {failed}")
    return all_lines, all_coords, all_labels


def split_pdf_batches(filepath):
    """用 fitz 把 filepath 切成 ≤BATCH_SIZE 页的临时 PDF。
    返回 (batches, tmp_dir):batches=[(tmp_path, batch_start, batch_len), ...]。
    tmp_dir 由调用方负责清理。"""
    src = fitz.open(filepath)
    n = src.page_count
    batches = []
    tmp_dir = tempfile.mkdtemp(prefix="ocr_batch_")
    for start in range(0, n, BATCH_SIZE):
        end = min(start + BATCH_SIZE, n)
        out_doc = fitz.open()
        out_doc.insert_pdf(src, from_page=start, to_page=end - 1)
        tmp_path = os.path.join(tmp_dir, f"batch_{start:05d}.pdf")
        out_doc.save(tmp_path)
        out_doc.close()
        batches.append((tmp_path, start, end - start))
    src.close()
    return batches, tmp_dir


def _parse_page(lpr):
    """从单个 layoutParsingResults 元素解析一页的 (lines, polys, labels)。
    API 返回的 result.layoutParsingResults 是页数组,每元素=一页。
    新格式:prunedResult.parsing_res_list(含 block_label)。回退 spotting_res。"""
    pr = lpr.get("prunedResult", {}) if isinstance(lpr, dict) else {}
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
    # 回退:无版面块时用 spotting_res(未开版面分析的旧格式)
    if not pl:
        sr = pr.get("spotting_res") or (lpr.get("spotting_res") if isinstance(lpr, dict) else None)
        if sr and isinstance(sr, dict) and sr.get("rec_texts"):
            pl = list(sr.get("rec_texts", []))
            pp = list(sr.get("rec_polys", []))
            pb = ["text"] * len(pl)
    return pl, pp, pb


def _upload_and_parse(pdf_path):
    """上传单个 PDF(≤BATCH_SIZE 页)→ 轮询 → 解析 jsonl。
    返回 (lines, coords, labels), key = 切片内局部页号 str(0-indexed)。"""
    print(f"Uploading: {pdf_path}")
    with open(pdf_path, "rb") as f:
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
    lines, coords, labels = {}, {}, {}
    raw_lines = [l for l in rr.text.strip().split("\n") if l.strip()]
    # jsonl 每行=一个文档;result.layoutParsingResults 是页数组,每元素=一页
    page_counter = 0
    for line in raw_lines:
        result = json.loads(line)["result"]
        lpr_list = result.get("layoutParsingResults", [])
        for lpr in lpr_list:
            pl, pp, pb = _parse_page(lpr)
            lines[str(page_counter)] = pl
            coords[str(page_counter)] = pp
            labels[str(page_counter)] = pb
            titles = sum(1 for x in pb if "title" in x)
            print(f"  page {page_counter}: {len(pl)} lines, titles: {titles}")
            page_counter += 1
    return lines, coords, labels


def _upload_and_parse_with_retry(batch_pdf, retries=3, backoff=10):
    """单批上传+解析,失败重试(指数退避)。覆盖网络错/API 5xx/state==failed。"""
    last = None
    for attempt in range(1, retries + 1):
        try:
            return _upload_and_parse(batch_pdf)
        except Exception as e:
            last = e
            print(f"  Batch failed (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(backoff * attempt)
    raise RuntimeError(f"Batch {batch_pdf} failed after {retries} attempts: {last}")


def process_pdf(filepath):
    """直接上传 PDF(非 PNG 转换路径)。启用版面分析提取 block_label。
    >BATCH_SIZE 页时自动切片分批,合并时全局 key = batch_start + 局部页号。"""
    # Check if PDF needs PNG conversion
    if needs_png_conversion(filepath):
        print(f"PDF has non-bitonal images, converting to PNG pages...")
        return process_pdf_via_png(filepath)

    n = fitz.open(filepath).page_count
    if n <= BATCH_SIZE:
        # 单批:局部 key 即全局 key(batch_start=0),零行为变化
        print(f"Single batch: {n} pages (≤ {BATCH_SIZE})")
        bl, bc, bbl = _upload_and_parse_with_retry(filepath)
        if len(bl) != n:
            raise RuntimeError(f"Parse mismatch: expected {n} pages, got {len(bl)}")
        return bl, bc, bbl

    # 多批:切片 → 逐批上传+校验 → 偏移合并
    print(f"PDF has {n} pages > {BATCH_SIZE}, splitting into batches...")
    batches, tmp_dir = split_pdf_batches(filepath)
    all_lines, all_coords, all_labels = {}, {}, {}
    total = len(batches)
    try:
        for i, (batch_pdf, batch_start, batch_len) in enumerate(batches, 1):
            print(f"=== Batch {i}/{total}: pages {batch_start}-{batch_start + batch_len - 1} ===")
            bl, bc, bbl = _upload_and_parse_with_retry(batch_pdf)
            # 校验:解析页数必须 == 切片页数,否则丢页/多页导致坐标全错
            if len(bl) != batch_len:
                raise RuntimeError(
                    f"Batch parse mismatch at pages {batch_start}-{batch_start+batch_len-1}: "
                    f"expected {batch_len} pages, got {len(bl)}")
            # 偏移合并:全局页号 = batch_start + 局部页号
            for local_k in bl:
                gk = str(batch_start + int(local_k))
                all_lines[gk] = bl[local_k]
                all_coords[gk] = bc[local_k]
                all_labels[gk] = bbl[local_k]
            print(f"  merged {len(bl)} pages → global keys {batch_start}-{batch_start+len(bl)-1}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return all_lines, all_coords, all_labels


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
