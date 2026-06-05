#!/usr/bin/env python3
"""Quick test: dump spotting result structure to understand character granularity."""
import json, requests, time, os, sys

TOKEN_FILE = "/tmp/paddle_token"
tok = open(TOKEN_FILE).read().strip()
HEADERS = {"Authorization": "bearer " + tok}
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"

payload = {
    "model": "PaddleOCR-VL-1.6",
    "optionalPayload": json.dumps({"useLayoutDetection": False, "promptLabel": "spotting", "temperature": 0}),
}

print("Uploading PDF...")
with open("/opt/test/优化前.pdf", "rb") as f:
    r = requests.post(JOB_URL, headers=HEADERS, data=payload, files={"file": f})
r.raise_for_status()
job_id = r.json()["data"]["jobId"]
print(f"Job: {job_id}")

for t in range(60):
    rr = requests.get(JOB_URL + "/" + job_id, headers=HEADERS)
    state = rr.json()["data"]["state"]
    if state == "done":
        print(f"Done after {t*5}s")
        jsonl_url = rr.json()["data"]["resultUrl"]["jsonUrl"]
        result = requests.get(jsonl_url).text.strip().split("\n")
        # Parse first page
        page0 = json.loads(result[0])["result"]
        lpr = page0["layoutParsingResults"][0]
        pr = lpr.get("prunedResult", {})
        pr_list = pr.get("parsing_res_list", [])

        print(f"\nprunedResult.parsing_res_list: {len(pr_list)} blocks")
        for bi, blk in enumerate(pr_list[:3]):
            sr = blk.get("spotting_res", {})
            texts = sr.get("rec_texts", [])
            polys = sr.get("rec_polys", [])
            cat = blk.get("category", "?")
            print(f"  Block {bi}: category={cat}, {len(texts)} text segments")
            if texts:
                lens = [len(t) for t in texts]
                print(f"    Lengths: min={min(lens)} max={max(lens)} avg={sum(lens)/len(lens):.1f}")
                for ti, t in enumerate(texts[:5]):
                    print(f"    [{ti}] '{t}'")

        # Also check markdown for character-level hints
        md = lpr.get("markdown", "")
        print(f"\nMarkdown: {len(md)} chars, first 200:")
        print(md[:200])
        break
    elif state == "failed":
        print(f"FAILED: {rr.json()['data'].get('errorMsg','?')}")
        sys.exit(1)
    time.sleep(5)
