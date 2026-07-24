#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑 PP-OCRv6 拿 rec_scores(识别置信度)。

VL 不给 score,PP-OCRv6 给。低 score 行=古字识错(甲骨文/金文图),
build_geom 据此整行贴图。PP-OCRv6 文字质量差(如"毛尹梁尚币"),只用 score,
文字仍用 VL 结果(VL 最强)。

用法:
    /usr/bin/python3 src/ocr/run_ppocrv6_scores.py source_pdf/wz3.pdf data/wz3/wz3_ppocrv6_scores.json

输出: {key: [[poly4点, score, text], ...]}
"""
import json, os, sys, time, threading, requests, fitz
from concurrent.futures import ThreadPoolExecutor

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
TOKEN = open("/tmp/paddle_token").read().strip()
HEADERS = {"Authorization": "bearer " + TOKEN}
MODEL = "PP-OCRv6"
DPI = 200
WORKERS = 8   # 并发度(API 限流时调低)


def ocr_page(png_path, retries=2):
    """上传单页 PNG -> PP-OCRv6 -> 返回 [[poly4点, score, text], ...]"""
    PAYLOAD = {"model": MODEL, "optionalPayload": json.dumps({
        "useDocOrientationClassify": False, "useDocUnwarping": False, "useTextlineOrientation": False})}
    last = None
    for _ in range(retries + 1):
        try:
            with open(png_path, "rb") as f:
                r = requests.post(JOB_URL, headers=HEADERS, data=PAYLOAD, files={"file": f})
            r.raise_for_status()
            job_id = r.json()["data"]["jobId"]
            while True:
                rr = requests.get(JOB_URL + "/" + job_id, headers=HEADERS)
                rr.raise_for_status()
                st = rr.json()["data"]["state"]
                if st == "done":
                    jsonl_url = rr.json()["data"]["resultUrl"]["jsonUrl"]; break
                if st == "failed":
                    raise RuntimeError(rr.json()["data"].get("errorMsg", "unknown"))
                time.sleep(2)
            rr = requests.get(jsonl_url); rr.raise_for_status()
            lines = [l for l in rr.text.strip().split("\n") if l.strip()]
            if not lines: return []
            result = json.loads(lines[0])["result"]
            ocr = result.get("ocrResults", [])
            if not ocr: return []
            pr = ocr[0].get("prunedResult", {})
            txts = pr.get("rec_texts", []); polys = pr.get("rec_polys", []); scores = pr.get("rec_scores", [])
            out = []
            for i, t in enumerate(txts):
                poly = polys[i] if i < len(polys) else None
                score = float(scores[i]) if i < len(scores) else 0.0
                if poly and isinstance(poly, list) and len(poly) >= 4:
                    out.append([[[round(c, 1) for c in p] for p in poly[:4]], round(score, 3), t])
            return out
        except Exception as e:
            last = e; time.sleep(5)
    raise last


def main():
    SRC = sys.argv[1] if len(sys.argv) > 1 else "source_pdf/wz3.pdf"
    OUT = sys.argv[2] if len(sys.argv) > 2 else "data/wz3/wz3_ppocrv6_scores.json"
    doc = fitz.open(SRC); n = doc.page_count
    print(f"[PP-OCRv6] 渲染 {n} 页 @200dpi(串行)...")
    png_paths = []
    for pi in range(n):
        doc[pi].get_pixmap(dpi=DPI).save(f"/tmp/ppocrv6_{pi:03d}.png")
        png_paths.append(f"/tmp/ppocrv6_{pi:03d}.png")
        if (pi + 1) % 25 == 0 or pi + 1 == n: print(f"  rendered {pi + 1}/{n}")
    doc.close()
    print(f"[PP-OCRv6] OCR {n} 页 (x{WORKERS} workers)...")
    all_data = {}; done = [0]; failed = []; lock = threading.Lock()

    def worker(pi):
        try:
            res = ocr_page(png_paths[pi])
        except Exception as e:
            res = []
            with lock: failed.append((pi, str(e)[:60]))
        with lock:
            all_data[str(pi)] = res; done[0] += 1
            if done[0] % 10 == 0 or done[0] == n: print(f"  OCR {done[0]}/{n}")
        try: os.unlink(png_paths[pi])
        except OSError: pass

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(worker, range(n)))
    json.dump(all_data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    total = sum(len(v) for v in all_data.values())
    low = sum(1 for v in all_data.values() for _, s, _ in v if s < 0.85)
    print(f"[PP-OCRv6] 完成: {n} 页, {total} 行, 低分(<0.85) {low} 行 -> {OUT}")
    if failed: print(f"  失败 {len(failed)} 页: {failed[:5]}")


if __name__ == "__main__":
    main()
