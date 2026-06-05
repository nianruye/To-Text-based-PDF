#!/usr/bin/env python3
"""Test different promptLabel values to check character-level detection."""
import json, requests, sys

TOKEN_FILE = "/tmp/paddle_token"
if __import__('os').path.exists(TOKEN_FILE):
    tok = open(TOKEN_FILE).read().strip()
else:
    tok = "REDACTED_PADDLEOCR_TOKEN"  # fallback

HEADERS = {"Authorization": "bearer " + tok}
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
INPUT_PDF = "/opt/test/优化前.pdf"

LABELS_TO_TEST = ["spotting"]  # focus on working mode, check granularity

print("Testing promptLabel values for character-level detection...")
print(f"Model: PaddleOCR-VL-1.6, File: {INPUT_PDF}\n")

for label in LABELS_TO_TEST:
    payload = {
        "model": "PaddleOCR-VL-1.6",
        "optionalPayload": json.dumps({
            "useLayoutDetection": False,
            "promptLabel": label,
            "temperature": 0,
        }),
    }

    try:
        print(f"Testing promptLabel='{label}'...")
        with open(INPUT_PDF, "rb") as f:
            r = requests.post(JOB_URL, headers=HEADERS, data=payload, files={"file": f}, timeout=30)

        if r.status_code == 200:
            job_id = r.json()["data"]["jobId"]
            # Poll briefly
            import time
            for _ in range(30):
                rr = requests.get(JOB_URL + "/" + job_id, headers=HEADERS, timeout=10)
                state = rr.json()["data"]["state"]
                if state == "done":
                    jsonl_url = rr.json()["data"]["resultUrl"]["jsonUrl"]
                    result = requests.get(jsonl_url, timeout=10)
                    lines = result.text.strip().split("\n")
                    if lines:
                        first_page = json.loads(lines[0])
                        res = first_page.get("result", {})
                        # Dump full structure of first layoutParsingResult
                        parsing = res.get("layoutParsingResults", [{}])
                        if parsing:
                            lpr = parsing[0].get("layoutParsingResult", {})
                            blocks = lpr.get("parsing_res_list", []) or lpr.get("prunedResult", {}).get("parsing_res_list", [])
                            if blocks:
                                for blk in blocks:
                                    sr = blk.get("spotting_res", {})
                                    texts = sr.get("rec_texts", [])
                                    polys = sr.get("rec_polys", [])
                                    if texts:
                                        avg_len = sum(len(t) for t in texts) / len(texts)
                                        print(f"  ✅ promptLabel='{label}': {len(texts)} segments, avg {avg_len:.1f} chars/segment")
                                        for t in texts[:5]:
                                            print(f"      '{t}'")
                                        if texts:
                                            min_len = min(len(t) for t in texts)
                                            max_len = max(len(t) for t in texts)
                                            print(f"      Length range: {min_len}-{max_len} chars")
                                        break
                            else:
                                sr = res.get("spotting_res") or (parsing[0].get("spotting_res") if parsing else None)
                                if sr:
                                    texts = sr.get("rec_texts", [])
                                    print(f"  ✅ (alt) {len(texts)} segments, avg {sum(len(t) for t in texts)/len(texts):.1f} chars/segment")
                                else:
                                    print(f"  ⚠️ Unknown format. Full keys: {list(res.keys())}")
                                    # Dump first level structure
                                    for k, v in res.items():
                                        if isinstance(v, list):
                                            print(f"     {k}: list[{len(v)}]")
                                            if v: print(f"       [0] keys: {list(v[0].keys()) if isinstance(v[0], dict) else type(v[0])}")
                                        elif isinstance(v, dict):
                                            print(f"     {k}: dict keys={list(v.keys())[:5]}")
                                        else:
                                            print(f"     {k}: {type(v).__name__}")
                        else:
                            print(f"  ⚠️ No layoutParsingResults")
                    break
                elif state == "failed":
                    print(f"  ❌ Job failed: {rr.json()['data'].get('errorMsg', 'unknown')}")
                    break
                time.sleep(3)
        else:
            print(f"  ❌ HTTP {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    print()

print("Done testing.")
