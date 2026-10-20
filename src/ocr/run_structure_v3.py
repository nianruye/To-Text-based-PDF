#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PP-StructureV3 全书扫描 — 取「检测框 + 逐行置信度」作为第二数据源

用途(不改现有渲染链路, 只产出数据):
  1. dt_polys / rec_polys : 文本**检测框**(行级) —— 我们的 spotting 会漏掉短列/小字列
     (实测 p53: 它检出「導讀」「詞話章回目錄」「詞話第一冊目錄」三列, spotting 完全没有)
  2. rec_scores           : 逐行置信度 —— 我们现在完全没有, 可用来砍幻觉
     (实测 p53: 「福」0.029 / 「Y」0.142 / 「0」0.06 全是垃圾)

输出: data/<book>/<book>_ps3.json
      { "页号(1-based)": {"texts": [...], "scores": [...], "polys": [[[x,y],...], ...]}, ... }
      坐标为源图 px(= pt x 2, 与 spotting_coords 同口径)

用法:
  /usr/bin/python3 src/ocr/run_structure_v3.py <src.pdf> <out.json> [--from 1] [--to 1748] [--batch 40]
可断点续跑: 已存在于 out.json 的页会跳过。
"""
import argparse
import json
import os
import sys
import time

import fitz
import requests

TOKEN_FILE = '/tmp/paddle_token'
JOB_URL = 'https://paddleocr.aistudio-app.com/api/v2/ocr/jobs'
MODEL = 'PP-StructureV3'


def payload():
    return {'model': MODEL, 'optionalPayload': json.dumps({
        'use_doc_preprocessor': False,
        'use_textline_orientation': False,
        'use_seal_recognition': False,
        # 表格/公式识别对「行框 + 文字 + 置信度」无用, 关掉明显提速
        'use_table_recognition': False,
        'use_formula_recognition': False,
        'use_chart_recognition': False,
        'use_region_detection': True,
        'format_block_content': True,
        'markdown_ignore_labels': ['number', 'footnote', 'header', 'header_image',
                                  'footer', 'footer_image', 'aside_text'],
    })}


def submit(pdf_path, tok):
    h = {'Authorization': 'bearer ' + tok}
    with open(pdf_path, 'rb') as f:
        r = requests.post(JOB_URL, headers=h, data=payload(), files={'file': f}, timeout=600)
    if r.status_code >= 400:
        raise RuntimeError('提交失败 %s %s' % (r.status_code, r.text[:300]))
    job = (r.json().get('data') or {}).get('jobId')
    if not job:
        raise RuntimeError('无 jobId: %s' % str(r.json())[:300])
    return job, h


def wait(job, h, timeout_s=3600):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        time.sleep(3)
        d = requests.get(JOB_URL + '/' + job, headers=h, timeout=120).json().get('data') or {}
        st = d.get('state')
        if st == 'done':
            return (d.get('resultUrl') or {}).get('jsonUrl')
        if st in ('failed', 'error'):
            raise RuntimeError('任务失败: %s' % str(d)[:300])
    raise RuntimeError('超时')


def fetch(url):
    """返回 {页号(相对 1-based): {texts, scores, polys}}"""
    txt = requests.get(url, timeout=1200).text
    out = {}
    gp = 0                      # 全局页号(跨 JSONL 行累加) —— 每行的 i 都从 0 重置, 直接用它会把
    for line in txt.strip().split('\n'):   # 后一页覆盖前一页(实测 5 页只收回 1 页)
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        res = o.get('result') or {}
        lprs = res.get('layoutParsingResults') or []
        if lprs:
            for lr in lprs:
                pr = lr.get('prunedResult') or {}
                ocr = pr.get('overall_ocr_res') or {}
                gp += 1
                if ocr.get('rec_texts'):
                    out[gp] = {'texts': ocr.get('rec_texts') or [],
                               'scores': ocr.get('rec_scores') or [],
                               'polys': ocr.get('rec_polys') or ocr.get('dt_polys') or []}
            continue
        for orr in res.get('ocrResults') or []:
            pr = orr.get('prunedResult') or {}
            gp += 1
            if pr.get('rec_texts'):
                out[gp] = {'texts': pr.get('rec_texts') or [],
                           'scores': pr.get('rec_scores') or [],
                           'polys': pr.get('rec_polys') or pr.get('dt_polys') or []}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--from', dest='p0', type=int, default=1)
    ap.add_argument('--to', dest='p1', type=int, default=0)
    ap.add_argument('--batch', type=int, default=40)
    a = ap.parse_args()

    tok = open(TOKEN_FILE).read().strip()
    doc = fitz.open(a.src)
    n = len(doc)
    if a.p1 <= 0 or a.p1 > n:
        a.p1 = n
    existing = {}
    if os.path.exists(a.out):
        existing = json.load(open(a.out, encoding='utf-8'))
        print('[续跑] 已有 %d 页' % len(existing))

    p = a.p0
    while p <= a.p1:
        q = min(p + a.batch - 1, a.p1)
        todo = [x for x in range(p, q + 1) if str(x) not in existing]
        if not todo:
            p = q + 1
            continue
        lo, hi = min(todo), max(todo)
        tmp = '/tmp/ps3_chunk.pdf'
        sub = fitz.open()
        sub.insert_pdf(doc, from_page=lo - 1, to_page=hi - 1)
        sub.save(tmp)
        sub.close()
        t0 = time.time()
        try:
            job, h = submit(tmp, tok)
            url = wait(job, h)
            got = fetch(url)
        except Exception as e:
            print('[p%d-%d] 失败: %s -> 拆半重试' % (lo, hi, e))
            if hi - lo < 2:
                p = q + 1
                continue
            a.batch = max(1, (hi - lo + 1) // 2)
            continue
        for rel, v in got.items():
            gp = lo + rel - 1
            if str(gp) not in existing:
                existing[str(gp)] = v
        json.dump(existing, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False)
        print('[p%d-%d] %d 页 %.0fs  累计 %d 页'
              % (lo, hi, len(got), time.time() - t0, len(existing)), flush=True)
        p = q + 1
    doc.close()
    print('[完成] %s  共 %d 页' % (a.out, len(existing)))


if __name__ == '__main__':
    main()
