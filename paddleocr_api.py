#!/usr/bin/env python3
"""
PaddleOCR-VL API Pipeline v3 — via AI Studio HTTP API
No local PaddleOCR install needed. Sends PDF directly, gets Markdown back.
"""
import json, time, sys, os
import requests

API_BASE = "https://dfrf39q5w1zctfyd.aistudio-app.com"
TOKEN_FILE = "/tmp/paddle_token"
TOKEN = open(TOKEN_FILE).read().strip()
INPUT_PDF = "/opt/test/优化前.pdf"
MARKS_FILE = "/opt/test/paddleocr_markdown.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
}

def api_get(path, params=None):
    r = requests.get(f"{API_BASE}{path}", headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def api_post(path, data=None, files=None):
    r = requests.post(f"{API_BASE}{path}", headers=HEADERS, data=data, files=files, timeout=30)
    r.raise_for_status()
    return r.json()

# Step 1: Upload PDF
print("Step 1: Uploading PDF...")
with open(INPUT_PDF, "rb") as f:
    result = api_post("/api/upload", files={"file": ("优化前.pdf", f, "application/pdf")})
file_id = result.get("file_id") or result.get("id") or result.get("data", {}).get("id")
print(f"  File uploaded: {file_id}")

# Step 2: Submit document parsing task
print("Step 2: Submitting document parsing task (PaddleOCR-VL-1.6)...")
task = api_post("/api/tasks/parse_document", data={
    "file_id": file_id,
    "model": "PaddleOCR-VL-1.6",
    "prettify_markdown": "true",
})
job_id = task.get("job_id") or task.get("id") or task.get("data", {}).get("id")
print(f"  Job created: {job_id}")

# Step 3: Poll until done
print("Step 3: Polling job status...")
for i in range(60):
    status = api_get(f"/api/tasks/{job_id}/status")
    state = status.get("state") or status.get("status") or status.get("data", {}).get("state", "")
    print(f"  Poll {i+1}: {state}")
    if state in ("completed", "done", "success"):
        break
    if state in ("failed", "error"):
        print(f"  ERROR: {status}")
        sys.exit(1)
    time.sleep(5)

# Step 4: Get results
print("Step 4: Fetching results...")
result = api_get(f"/api/tasks/{job_id}/result")
print(f"  Result keys: {list(result.keys())}")

# Extract markdown from each page
pages = result.get("pages") or result.get("data", {}).get("pages") or []
print(f"  Pages returned: {len(pages)}")

markdown_data = {}
for i, page in enumerate(pages):
    page_num = str(i + 1)
    md = page.get("markdown") or page.get("text") or page.get("content") or ""
    markdown_data[page_num] = md
    print(f"  Page {page_num}: {len(md)} chars")

with open(MARKS_FILE, "w", encoding="utf-8") as f:
    json.dump(markdown_data, f, ensure_ascii=False, indent=2)

total = sum(len(v) for v in markdown_data.values())
print(f"\n✅ Saved {len(markdown_data)} pages, {total} chars → {MARKS_FILE}")
