#!/usr/bin/env python3
"""跑 PP-OCRv6 API(returnWordBox=True),存字级文字+字级box+行级score。
VL字≠v6字 + v6逐字score低 = 双确认古字。"""
import json, os, sys, time, threading, requests, fitz
from concurrent.futures import ThreadPoolExecutor

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
TOKEN = open("/tmp/paddle_token").read().strip()
HEADERS = {"Authorization": "bearer " + TOKEN}
MODEL = "PP-OCRv6"
DPI = 200
WORKERS = 8

def ocr_page(png_path, retries=2):
    PAYLOAD = {"model": MODEL, "optionalPayload": json.dumps({
        "useDocOrientationClassify": False, "useDocUnwarping": False,
        "useTextlineOrientation": False, "returnWordBox": True})}
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
            txts = pr.get("rec_texts", []); polys = pr.get("rec_polys", [])
            scores = pr.get("rec_scores", [])
            word_boxes = pr.get("text_word_boxes", [])
            words = pr.get("text_word", [])
            out = []
            for i, t in enumerate(txts):
                poly = polys[i] if i < len(polys) else None
                score = float(scores[i]) if i < len(scores) else 0.0
                wb = word_boxes[i] if i < len(word_boxes) else []
                ww = words[i] if i < len(words) else []
                if poly and isinstance(poly, list) and len(poly) >= 4:
                    out.append([
                        [[round(c, 1) for c in p] for p in poly[:4]],
                        round(score, 3), t, ww, wb
                    ])
            return out
        except Exception as e:
            last = e; time.sleep(5)
    raise last

def main():
    SRC = sys.argv[1] if len(sys.argv) > 1 else "source_pdf/wz3.pdf"
    OUT = sys.argv[2] if len(sys.argv) > 2 else "data/wz3/wz3_v6_wordbox.json"
    doc = fitz.open(SRC); n = doc.page_count
    print(f"[PP-OCRv6 wordbox] 渲染 {n} 页...")
    png_paths = []
    for pi in range(n):
        doc[pi].get_pixmap(dpi=DPI).save(f"/tmp/wb_{pi:03d}.png")
        png_paths.append(f"/tmp/wb_{pi:03d}.png")
        if (pi+1) % 50 == 0 or pi+1 == n: print(f"  rendered {pi+1}/{n}")
    doc.close()
    print(f"OCR {n} 页 (x{WORKERS})...")
    all_data = {}; done = [0]; failed = []; lock = threading.Lock()
    def worker(pi):
        try: res = ocr_page(png_paths[pi])
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
    print(f"完成: {n}页 {total}行 -> {OUT}")
    if failed: print(f"  失败 {len(failed)} 页: {failed[:5]}")

if __name__ == "__main__":
    main()
