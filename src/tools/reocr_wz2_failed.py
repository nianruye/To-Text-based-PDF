#!/usr/bin/env python3
"""定向重 OCR:wz2 第一轮因 API 瞬时限流(400)失败的空页。
只处理仍空的页(幂等,可重跑),降并发(4)+加大重试退避避开限流,合并回原 json。"""
import json, os, time, threading, fitz
from concurrent.futures import ThreadPoolExecutor
import run_spotting_ocr as ocr   # 复用 _ocr_png_page(OCR_LAYOUT=0 → spotting)

SRC = '/opt/test/wz2.pdf'
LINES = '/opt/test/wz2_spotting_lines.json'
COORDS = '/opt/test/wz2_spotting_coords.json'
LABELS = '/opt/test/wz2_spotting_lines_labels.json'

lines = json.load(open(LINES))
coords = json.load(open(COORDS))
labels = json.load(open(LABELS))
empty = [int(k) for k, l in lines.items() if isinstance(l, list) and len(l) == 0]
print(f'[重OCR] {len(empty)} 个空页,4 并发,每页最多 5 次重试')

doc = fitz.open(SRC)
pngs = {}
for i in empty:
    pix = doc[i].get_pixmap(dpi=200)
    p = f'/tmp/wz2_retry_{i}.png'; pix.save(p); pngs[i] = p
doc.close()
print(f'[重OCR] 渲染完成,开始 OCR')

lock = threading.Lock(); done = [0]; still_failed = []
def worker(i):
    pl, pp, pb = [], [], []
    for attempt in range(5):
        try:
            pl, pp, pb = ocr._ocr_png_page(pngs[i])
            if pl:
                break
        except Exception:
            if attempt < 4:
                time.sleep(10 * (attempt + 1))   # 10/20/30/40/50s 退避,等限流窗口过
            else:
                pl, pp, pb = [], [], []
    with lock:
        lines[str(i)] = pl; coords[str(i)] = pp; labels[str(i)] = pb
        done[0] += 1
        if not pl:
            still_failed.append(i)
        if done[0] % 10 == 0 or done[0] == len(empty):
            print(f'  {done[0]}/{len(empty)} (仍失败 {len(still_failed)})')
    try:
        os.remove(pngs[i])
    except OSError:
        pass

with ThreadPoolExecutor(max_workers=4) as ex:
    list(ex.map(worker, empty))

json.dump(lines, open(LINES, 'w'), ensure_ascii=False, indent=2)
json.dump(coords, open(COORDS, 'w'), ensure_ascii=False, indent=2)
json.dump(labels, open(LABELS, 'w'), ensure_ascii=False, indent=2)
nempty = sum(1 for l in lines.values() if isinstance(l, list) and len(l) == 0)
print(f'[重OCR] 完成。剩余空页: {nempty}', still_failed)
