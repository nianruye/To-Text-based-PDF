#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""battle6/t27：候选集全量 16 批提交/轮询/解析（存 texts+polys；token 只读）。"""
import argparse, json, os, time
import requests

JOB = 'https://paddleocr.aistudio-app.com/api/v2/ocr/jobs'
PAYLOAD = {"model": "PaddleOCR-VL-1.6", "optionalPayload": json.dumps({
    "useLayoutDetection": False, "promptLabel": "spotting", "temperature": 0,
    "minPixels": 147384, "maxPixels": 2822400, "repetitionPenalty": 1, "topP": 1,
    "layoutShapeMode": "auto", "useDocUnwarping": False, "useDocOrientationClassify": False})}

def submit(path, h):
    last = None
    for att in range(4):
        try:
            with open(path, 'rb') as f:
                r = requests.post(JOB, headers=h, data=PAYLOAD, files={'file': f}, timeout=600)
            r.raise_for_status(); return r.json()['data']['jobId'], att
        except Exception as e:
            last = e; time.sleep(8 * (att + 1))
    raise last

def poll(jid, h, timeout=1800):
    t0 = time.time()
    while True:
        r = requests.get(JOB + '/' + jid, headers=h, timeout=60); r.raise_for_status()
        d = r.json()['data']
        if d['state'] == 'done': return d['resultUrl']['jsonUrl']
        if d['state'] == 'failed': raise RuntimeError(d.get('errorMsg', '?'))
        if time.time() - t0 > timeout: raise TimeoutError(jid)
        time.sleep(4)

def parse(url):
    r = requests.get(url, timeout=600); r.raise_for_status()
    pages = []
    for line in r.text.strip().split('\n'):
        if not line.strip(): continue
        res = json.loads(line)['result']
        for lpr in (res.get('layoutParsingResults') or []):
            pr = lpr.get('prunedResult') or {}
            sr = pr.get('spotting_res') or lpr.get('spotting_res') or {}
            pages.append(dict(texts=sr.get('rec_texts') or [], polys=sr.get('rec_polys') or []))
    return pages

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', default='wz7')
    ap.add_argument('--out-dir', default=None, help='默认 tmp_vert/battle6（wz7）/ tmp_vert/{book}')
    ap.add_argument('--plan', default=None, help='默认 {out-dir}/all_plan.json')
    ap.add_argument('--out', default=None, help='默认 {out-dir}/api_candidates_all_raw.json')
    a = ap.parse_args()
    out_dir = a.out_dir or ('tmp_vert/battle6' if a.book == 'wz7' else f'tmp_vert/{a.book}')
    a.plan = a.plan or os.path.join(out_dir, 'all_plan.json')
    a.out = a.out or os.path.join(out_dir, 'api_candidates_all_raw.json')
    h = {'Authorization': 'bearer ' + open('/tmp/paddle_token').read().strip()}
    plan = json.load(open(a.plan, encoding='utf-8'))
    out = {'batches': [], 'n_cols': plan['n_items']}
    for b in plan['batches']:
        t0 = time.time()
        rec = dict(batch=b['batch'], pdf=b['pdf'], pages=b['pages'])
        try:
            jid, retries = submit(b['pdf'], h)
            url = poll(jid, h); pages = parse(url)
            rec.update(job=jid, retries=retries, api_pages=len(pages), ok=True,
                       elapsed=round(time.time() - t0, 1), page_data=pages)
        except Exception as e:
            rec.update(ok=False, error=type(e).__name__ + ': ' + str(e), elapsed=round(time.time() - t0, 1))
        out['batches'].append(rec)
        print('batch', rec['batch'], 'ok', rec.get('ok'), 'pages', rec.get('api_pages'),
              'elapsed', rec['elapsed'], flush=True)
        json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False)
    print('done', sum(1 for x in out['batches'] if x.get('ok')), '/', len(out['batches']))

if __name__ == '__main__':
    main()
