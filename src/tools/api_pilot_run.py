#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""battle6/t26：25 批试点提交/轮询/解析（token 只读，不落盘）。

用法：/usr/bin/python3 src/tools/api_pilot_run.py --plan tmp_vert/battle6/pilot25_plan.json \
        --out tmp_vert/battle6/api_pilot_25_raw.json
"""
import argparse, json, os, time
import requests, fitz

JOB = 'https://paddleocr.aistudio-app.com/api/v2/ocr/jobs'
PAYLOAD = {"model": "PaddleOCR-VL-1.6", "optionalPayload": json.dumps({
    "useLayoutDetection": False, "promptLabel": "spotting", "temperature": 0,
    "minPixels": 147384, "maxPixels": 2822400, "repetitionPenalty": 1, "topP": 1,
    "layoutShapeMode": "auto", "useDocUnwarping": False, "useDocOrientationClassify": False})}

def submit(path, headers):
    last = None
    for att in range(4):
        try:
            with open(path, 'rb') as f:
                r = requests.post(JOB, headers=headers, data=PAYLOAD, files={'file': f}, timeout=300)
            r.raise_for_status(); return r.json()['data']['jobId'], att
        except Exception as e:
            last = e; time.sleep(8 * (att + 1))
    raise last

def poll(jid, headers, timeout=900):
    t0 = time.time()
    while True:
        r = requests.get(JOB + '/' + jid, headers=headers, timeout=60); r.raise_for_status()
        d = r.json()['data']
        if d['state'] == 'done': return d['resultUrl']['jsonUrl']
        if d['state'] == 'failed': raise RuntimeError(d.get('errorMsg', '?'))
        if time.time() - t0 > timeout: raise TimeoutError(jid)
        time.sleep(3)

def parse(url, n_slots, slot_xs):
    r = requests.get(url, timeout=300); r.raise_for_status()
    pages = []
    for line in r.text.strip().split('\n'):
        if not line.strip(): continue
        res = json.loads(line)['result']
        for lpr in (res.get('layoutParsingResults') or []):
            pr = lpr.get('prunedResult') or {}
            sr = pr.get('spotting_res') or lpr.get('spotting_res') or {}
            texts = sr.get('rec_texts') or []
            polys = sr.get('rec_polys') or []
            slots = [[] for _ in range(n_slots)]
            for t, p in zip(texts, polys):
                if not p or len(p) < 4: continue
                cx = sum(q[0] for q in p[:4]) / 4.0
                # slot 索引按页面 400pt 宽 / n_slots 定位（PDF 用户坐标）
                k = min(n_slots - 1, max(0, int(cx / (400.0 / n_slots))))
                slots[k].append(t)
            pages.append([''.join(s) for s in slots])
    return pages

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', default='wz7')
    ap.add_argument('--out-dir', default=None, help='默认 tmp_vert/battle6（wz7）/ tmp_vert/{book}')
    ap.add_argument('--plan', default=None, help='默认 {out-dir}/pilot25_plan.json')
    ap.add_argument('--out', default=None, help='默认 {out-dir}/api_pilot_25_raw.json')
    a = ap.parse_args()
    out_dir = a.out_dir or ('tmp_vert/battle6' if a.book == 'wz7' else f'tmp_vert/{a.book}')
    a.plan = a.plan or os.path.join(out_dir, 'pilot25_plan.json')
    a.out = a.out or os.path.join(out_dir, 'api_pilot_25_raw.json')
    tok = open('/tmp/paddle_token').read().strip()
    headers = {'Authorization': 'bearer ' + tok}
    plan = json.load(open(a.plan, encoding='utf-8'))
    out = {'batches': [], 'n_cols': plan['n_items']}
    for b in plan['batches']:
        t0 = time.time()
        rec = dict(batch=b['batch'], pdf=b['pdf'], pages=b['pages'])
        try:
            jid, retries = submit(b['pdf'], headers)
            url = poll(jid, headers)
            pages = parse(url, 8, None)
            rec.update(job=jid, retries=retries, api_pages=len(pages), ok=True,
                       elapsed=round(time.time() - t0, 1))
            rec['page_slots'] = pages
        except Exception as e:
            rec.update(ok=False, error=type(e).__name__ + ': ' + str(e), elapsed=round(time.time() - t0, 1))
        out['batches'].append(rec)
        print('batch', rec['batch'], 'ok', rec.get('ok'), 'pages', rec.get('api_pages'),
              'elapsed', rec['elapsed'], flush=True)
        # 每批落盘，避免丢失
        json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False)
    print('done', sum(1 for x in out['batches'] if x.get('ok')), '/', len(out['batches']))

if __name__ == '__main__':
    main()
