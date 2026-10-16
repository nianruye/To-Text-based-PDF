#!/usr/bin/env python3
"""Wz4 稳健直传: 绕过 needs_png_conversion, 逐批落盘 + 批间间隔 + 断点续传。

复用 run_spotting_ocr.py 的切批/上传/轮询/解析逻辑, 但:
- 每批完成立即写盘(崩了不丢)
- 批间 sleep 15s 防 API 限流(400)
- 400 重试退避 30/60/120s
- 重启时检测已完成批次跳过(断点续传)
"""
import sys, os, json, time, tempfile, shutil, fitz

sys.path.insert(0, '/opt/test/src/ocr')
import run_spotting_ocr as r

# 绕过 JPEG 检查: 永远走 PDF 直传路径
r.needs_png_conversion = lambda filepath: False

INPUT_PDF  = '/opt/test/source_pdf/wz4.pdf'
OUT_LINES  = '/opt/test/data/wz4/wz4_spotting_lines.json'
OUT_COORDS = '/opt/test/data/wz4/wz4_spotting_coords.json'
OUT_LABELS = '/opt/test/data/wz4/wz4_spotting_labels.json'

BATCH_SIZE = 90
BATCH_SLEEP = 15      # 批间间隔(防限流)
RETRY_BACKOFF = [30, 60, 120]  # 400/5xx 重试退避

def load_existing():
    """加载已落盘的批结果(断点续传)。返回 (lines, coords, labels) dict."""
    out = {}
    for path in (OUT_LINES, OUT_COORDS, OUT_LABELS):
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                out[path] = json.load(f)
        else:
            out[path] = {}
    return out[OUT_LINES], out[OUT_COORDS], out[OUT_LABELS]

def save_all(lines, coords, labels):
    for path, data in ((OUT_LINES, lines), (OUT_COORDS, coords), (OUT_LABELS, labels)):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("[wz4] Direct PDF upload (skip PNG), batch-by-batch, resume-capable", flush=True)
    lines, coords, labels = load_existing()
    print("[wz4] Existing: %d pages already saved" % len(lines), flush=True)

    src = fitz.open(INPUT_PDF)
    n = src.page_count
    batches = []
    tmp_dir = tempfile.mkdtemp(prefix='wz4_batch_')
    try:
        for start in range(0, n, BATCH_SIZE):
            end = min(start + BATCH_SIZE, n)
            out_doc = fitz.open()
            out_doc.insert_pdf(src, from_page=start, to_page=end - 1)
            p = os.path.join(tmp_dir, 'batch_%05d.pdf' % start)
            out_doc.save(p)
            out_doc.close()
            batches.append((p, start, end - start))
    finally:
        src.close()

    total_batches = len(batches)
    print("[wz4] Split %d pages into %d batches (each <= %d)" % (n, total_batches, BATCH_SIZE), flush=True)

    for i, (p, start, blen) in enumerate(batches, 1):
        gk_start = str(start)
        gk_end = str(start + blen - 1)
        # 断点续传: 该批所有页都已存在则跳过
        if all(str(k) in lines for k in range(start, start + blen)):
            print("[wz4] Batch %d/%d (pages %s-%s) already done, skip" % (i, total_batches, start, start + blen - 1), flush=True)
            continue

        print("[wz4] Batch %d/%d: pages %s-%s (%d pages)" % (i, total_batches, start, start + blen - 1, blen), flush=True)
        if i > 1:
            print("[wz4]   sleeping %ds before upload (rate limit)" % BATCH_SLEEP, flush=True)
            time.sleep(BATCH_SLEEP)

        last_err = None
        ok = False
        for attempt, backoff in enumerate(RETRY_BACKOFF):
            try:
                bl, bc, bbl = r._upload_and_parse(p)
                ok = True
                break
            except Exception as e:
                last_err = e
                print("[wz4]   Batch failed attempt %d: %s" % (attempt + 1, e), flush=True)
                if attempt < len(RETRY_BACKOFF) - 1:
                    print("[wz4]   retrying in %ds..." % backoff, flush=True)
                    time.sleep(backoff)
        if not ok:
            print("[wz4]   FATAL: batch %s failed after %d attempts: %s" % (p, len(RETRY_BACKOFF), last_err), flush=True)
            raise SystemExit(1)

        # 校验页数
        if len(bl) != blen:
            print("[wz4]   FATAL: parse mismatch expected %d got %d" % (blen, len(bl)), flush=True)
            raise SystemExit(1)

        # 合并 + 立即落盘
        for local_k in bl:
            gk = str(start + int(local_k))
            lines[gk] = bl[local_k]
            coords[gk] = bc[local_k]
            labels[gk] = bbl[local_k]
        save_all(lines, coords, labels)
        print("[wz4]   saved pages %s-%s, total now %d pages" % (start, start + blen - 1, len(lines)), flush=True)

    shutil.rmtree(tmp_dir, ignore_errors=True)
    total = sum(len(v) for v in lines.values())
    print("[wz4] DONE: %d pages, %d lines" % (len(lines), total), flush=True)

if __name__ == '__main__':
    main()
