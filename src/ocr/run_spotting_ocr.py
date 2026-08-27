#!/usr/bin/env python3
"""Step 1: Full spotting OCR on 20 pages."""

import json, os, re, sys, time, tempfile, shutil, threading, requests, fitz
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

TOKEN_FILE = "/tmp/paddle_token"
INPUT_PDF = sys.argv[1] if len(sys.argv) > 1 else "/opt/test/优化前.pdf"
OUT_LINES = sys.argv[2] if len(sys.argv) > 2 else "/opt/test/spotting_lines.json"
OUT_COORDS = sys.argv[3] if len(sys.argv) > 3 else "/opt/test/spotting_coords.json"
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
MODEL = "PaddleOCR-VL-1.6"

tok = open(TOKEN_FILE).read().strip()
HEADERS = {"Authorization": "bearer " + tok}
# OCR_LAYOUT=0 → spotting 行级(useLayoutDetection=False → 行级 rec_texts+rec_polys,无版面分类)
# 默认(1/未设)→ layout 版面分析(段落合并块 + block_label 标题分类,旧行为)
_USE_LAYOUT = os.environ.get('OCR_LAYOUT', '1') not in ('0', 'false', 'False', '')
PAYLOAD = {
    "model": MODEL,
    "optionalPayload": json.dumps({
        "useLayoutDetection": _USE_LAYOUT,
        "promptLabel": "spotting",   # 仅 useLayoutDetection=False 时生效 → 行级
        "temperature": 0,
    }),
}
print(f"[OCR模式] useLayoutDetection={_USE_LAYOUT} ({'layout版面(合并块+分类)' if _USE_LAYOUT else 'spotting行级'})")

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
    """Check if PDF has embedded non-bitonal illustration images that the
    spotting API can't handle when uploaded directly.

    判定逻辑:
    - 整页扫描图(单图覆盖率 >= FULLPAGE_COVERAGE): PDF 直传 OK,VL API 内部
      会栅格化,实测 wz1-wz4 扫描书直传均正确。不走 PNG 逐页(慢一个量级)。
    - 文字版 PDF 里嵌的彩色/JPEG 插图(覆盖率 < 阈值): 直传会干扰版面,转 PNG。

    注意: get_images(full=True) 返回 (xref, smask, width, height, bpc,
    colorspace, alt-cs, name, filter, referencer)。bpc 在索引 4,不是 2
    (历史 bug: 误把 width 当 bpc,导致任何宽图都误判为需转 PNG)。
    """
    FULLPAGE_COVERAGE = 0.90   # 单图覆盖页面 >=90% 视为整页扫描图
    doc = fitz.open(filepath)
    try:
        for pi in range(min(3, doc.page_count)):
            page = doc[pi]
            page_area = page.rect.width * page.rect.height
            for img in page.get_images(full=True):
                xref = img[0]
                bpc = img[4]          # bits per component (索引4,非2)
                filt = img[8]         # filter/compression
                is_color = bpc > 1 or (filt and 'DCT' in str(filt))
                if not is_color:
                    continue          # 二值/灰度图不影响,跳过
                # 彩色/JPEG 图: 看覆盖率,整页扫描图 → 直传,嵌入插图 → 转 PNG
                try:
                    rects = page.get_image_rects(xref)
                except Exception:
                    rects = []
                coverage = 0.0
                if page_area > 0 and rects:
                    coverage = max((r.width * r.height) / page_area for r in rects)
                if coverage < FULLPAGE_COVERAGE:
                    return True       # 嵌入插图 → 需转 PNG
        return False                  # 全是整页扫描图(或无彩图) → 直传
    finally:
        doc.close()

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
        blocks = pr.get("parsing_res_list", []) if _USE_LAYOUT else []  # spotting 模式跳过版面块(其扁平 bbox 会触发解析 bug),走 spotting_res 行级
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
        if not blocks:   # spotting 模式(useLayoutDetection=False):无版面块,用 spotting_res 行级 rec_texts+rec_polys
            sr = pr.get("spotting_res") or lpr_list[0].get("spotting_res") or {}
            if isinstance(sr, dict) and sr.get("rec_texts"):
                for i, txt in enumerate(sr["rec_texts"]):
                    pl.append(txt); pb.append("text")
                    poly = sr["rec_polys"][i] if i < len(sr.get("rec_polys", [])) else None
                    pp.append([[round(c, 1) for c in pt] for pt in poly[:4]]
                              if poly and isinstance(poly, list) and len(poly) >= 4 else None)
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


def _render_page(args):
    """multiprocessing worker:独立 fitz.open 渲染单页为 JPEG。
    fitz 非线程安全但进程安全,每 worker 独立打开文档。"""
    filepath, pi, out_dir = args
    import fitz as _fitz
    from PIL import Image
    doc = _fitz.open(filepath)
    pix = doc[pi].get_pixmap(dpi=200)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    jpg_path = f"{out_dir}/spotting_page_{pi:03d}.jpg"
    img.save(jpg_path, quality=95)
    doc.close()
    return jpg_path


def process_pdf_via_png(filepath):
    """扫描书路径:渲染每页 JPEG -> 并发上传 OCR -> 合并。
    渲染用 multiprocessing.Pool(fitz 进程安全),上传用 ThreadPoolExecutor。
    OCR_RENDER_SERIAL=1 时回退串行渲染(原行为)。
    单页失败重试后仍失败则置空 + 记录 + 继续(不因一页废全本)。"""
    import multiprocessing
    doc = fitz.open(filepath)
    n = doc.page_count
    doc.close()

    # 阶段1: 渲染所有页为 JPEG
    serial = os.environ.get('OCR_RENDER_SERIAL', '') in ('1', 'true', 'True')
    if serial:
        print(f"Rendering {n} pages @200dpi (serial fallback)...")
        doc = fitz.open(filepath)
        img_paths = []
        for pi in range(n):
            pix = doc[pi].get_pixmap(dpi=200)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            img_path = f"/tmp/spotting_page_{pi:03d}.jpg"
            img.save(img_path, quality=95)
            img_paths.append(img_path)
            if (pi + 1) % 25 == 0 or pi + 1 == n:
                print(f"  rendered {pi + 1}/{n}")
        doc.close()
    else:
        n_workers = min(multiprocessing.cpu_count(), 8)
        print(f"Rendering {n} pages @200dpi (x{n_workers} processes)...")
        with multiprocessing.Pool(n_workers) as pool:
            img_paths = pool.map(_render_page, [(filepath, pi, "/tmp") for pi in range(n)], chunksize=16)
        print(f"  rendered {n}/{n}")

    # 阶段2: 并发上传/轮询/解析
    all_lines, all_coords, all_labels = {}, {}, {}
    failed = []
    done = [0]
    lock = threading.Lock()

    def worker(pi):
        try:
            pl, pp, pb = _ocr_png_page_with_retry(img_paths[pi])
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
            os.unlink(img_paths[pi])
        except OSError:
            pass

    print(f"OCR {n} pages (x{PNG_OCR_WORKERS} workers)...")
    with ThreadPoolExecutor(max_workers=PNG_OCR_WORKERS) as ex:
        list(ex.map(worker, range(n)))

    total = sum(len(v) for v in all_lines.values())
    titles = sum(sum(1 for l in v if "title" in l) for v in all_labels.values())
    print(f"OCR done: {n} pages, {total} lines, {titles} titles, {len(failed)} failed")
    if failed:
        print(f"\u26a0\ufe0f \u5931\u8d25\u9875(\u5df2\u7f6e\u7a7a): {failed}")
    return all_lines, all_coords, all_labels, {}

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
    - spotting 行级模式(useLayoutDetection=False): 优先用 spotting_res 的
      rec_texts+rec_polys(逐行文字+逐行坐标)。parsing_res_list 在此模式下是
      整页拼接块(label=spotting, 无逐行 poly),不能用——否则整页变1行丢坐标。
    - layout 版面模式: 用 parsing_res_list(含 block_label 标题分类)。"""
    pr = lpr.get("prunedResult", {}) if isinstance(lpr, dict) else {}

    # spotting 行级模式: 直接取 spotting_res(与 PNG 路径 _ocr_png_page 逻辑一致)
    if not _USE_LAYOUT:
        sr = pr.get("spotting_res") or (lpr.get("spotting_res") if isinstance(lpr, dict) else None) or {}
        pl, pp, pb = [], [], []
        if isinstance(sr, dict) and sr.get("rec_texts"):
            rec_polys = sr.get("rec_polys", [])
            for i, txt in enumerate(sr["rec_texts"]):
                pl.append(txt)
                pb.append("text")
                poly = rec_polys[i] if i < len(rec_polys) else None
                pp.append([[round(c, 1) for c in pt] for pt in poly[:4]]
                          if poly and isinstance(poly, list) and len(poly) >= 4 else None)
        return pl, pp, pb

    # layout 版面模式: parsing_res_list
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
    lines, coords, labels, markdown = {}, {}, {}, {}
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
            # markdown 字段(API 原生 md, spotting 模式是简单段落合并): 存阅读版副产品
            _md = lpr.get("markdown") if isinstance(lpr, dict) else None
            if isinstance(_md, dict) and isinstance(_md.get("text"), str) and _md["text"].strip():
                markdown[str(page_counter)] = _md["text"]
            titles = sum(1 for x in pb if "title" in x)
            print(f"  page {page_counter}: {len(pl)} lines, titles: {titles}")
            page_counter += 1
    return lines, coords, labels, markdown


def _is_rate_limit(err):
    """判断异常是否 400/429 限流(VL API 连续提交触发)。requests.HTTPError 带
    response.status_code;否则按错误消息关键词兜底。"""
    resp = getattr(err, "response", None)
    if resp is not None and getattr(resp, "status_code", None) in (400, 429):
        return True
    msg = str(err).lower()
    return any(k in msg for k in ("400", "429", "rate limit", "too many", "限流"))


def _upload_and_parse_with_retry(batch_pdf, retries=6, backoff=10):
    """单批上传+解析,失败重试(指数退避)。覆盖网络错/API 5xx/state==failed。
    400/429 限流/队列满: 无限重试(固定 RATE_LIMIT_WAIT 间隔),直到挤进共享队列。
    普通错误: 有限重试(retries 次,backoff*attempt 退避)。"""
    last = None
    attempt = 0
    rl_wait = 60           # 限流退避起始(秒),递增: 60→120→300→600 封顶
    while True:
        attempt += 1
        try:
            return _upload_and_parse(batch_pdf)
        except Exception as e:
            last = e
            is_rl = _is_rate_limit(e)
            if is_rl:
                # 队列满/限流: 无限重试,退避递增等待平台高峰过去(最多10分钟/次)
                print(f"  Batch 队列满/限流 (第{attempt}次), {rl_wait}s 后重试...", flush=True)
                time.sleep(rl_wait)
                rl_wait = min(rl_wait * 2 if rl_wait < 300 else rl_wait + 300, 600)
                continue
            # 普通错误: 有限重试
            print(f"  Batch failed (attempt {attempt}/{retries}): {e}", flush=True)
            if attempt >= retries:
                break
            wait = backoff * attempt
            print(f"  retrying in {wait}s...", flush=True)
            time.sleep(wait)
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
        bl, bc, bbl, bmd = _upload_and_parse_with_retry(filepath)
        if len(bl) != n:
            raise RuntimeError(f"Parse mismatch: expected {n} pages, got {len(bl)}")
        return bl, bc, bbl, bmd

    # 多批:切片 → 逐批上传+校验 → 偏移合并
    # 批间 sleep 防 VL API 400 限流(连续提交触发),OCR_BATCH_SLEEP 可调/置0关闭
    BATCH_SLEEP = float(os.environ.get("OCR_BATCH_SLEEP", "15"))
    print(f"PDF has {n} pages > {BATCH_SIZE}, splitting into batches... (批间 sleep {BATCH_SLEEP}s 防限流)")
    batches, tmp_dir = split_pdf_batches(filepath)
    all_lines, all_coords, all_labels, all_markdown = {}, {}, {}, {}
    total = len(batches)
    try:
        for i, (batch_pdf, batch_start, batch_len) in enumerate(batches, 1):
            print(f"=== Batch {i}/{total}: pages {batch_start}-{batch_start + batch_len - 1} ===")
            if i > 1 and BATCH_SLEEP > 0:
                time.sleep(BATCH_SLEEP)
            bl, bc, bbl, bmd = _upload_and_parse_with_retry(batch_pdf)
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
            for local_k in bmd:
                gk = str(batch_start + int(local_k))
                all_markdown[gk] = bmd[local_k]
            print(f"  merged {len(bl)} pages → global keys {batch_start}-{batch_start+len(bl)-1}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return all_lines, all_coords, all_labels, all_markdown


if __name__ == "__main__":
    print(f"Spotting OCR (layout detection ON): {INPUT_PDF}")
    lines_data, coords_data, labels_data, markdown_data = process_pdf(INPUT_PDF)
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

    # 输出 API 原生 markdown(阅读版副产品, 不参与排版)
    if markdown_data:
        out_md = base + "_markdown" + ext
        with open(out_md, "w", encoding="utf-8") as f:
            json.dump(markdown_data, f, ensure_ascii=False, indent=2)
        print(f"Saved: {out_md}")
    print("Step 1 complete.")
