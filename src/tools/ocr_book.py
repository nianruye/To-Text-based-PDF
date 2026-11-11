#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ocr_book.py — 整书 OCR 入口（A: layout+ocr / B: spotting，分批/断点续跑）。

设计见 docs/scan2pdf_design.md §5：--book/--input/--out-dir/--token-file/--mode/--pages-per-batch/
--workers/--resume。只读 token（不写文件/不打印）；网络调用仅在真实 OCR 时发生。
"""
import argparse
import json
import os
import sys
import time

JOB = 'https://paddleocr.aistudio-app.com/api/v2/ocr/jobs'
DEFAULT_TOKEN = '/tmp/paddle_token'
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OCR_DEFAULTS = {'max_pixels': 2822400, 'min_pixels': 147384,
                'orientation': 0, 'unwarp': 0, 'layout_shape': 'auto'}
_BOOK_KEYS = {'max_pixels': ('max_pixels', 'maxPixels'),
              'min_pixels': ('min_pixels', 'minPixels'),
              'orientation': ('orientation', 'useDocOrientationClassify'),
              'unwarp': ('unwarp', 'useDocUnwarping'),
              'layout_shape': ('layout_shape', 'layoutShapeMode')}


def check_token(path):
    p = path or DEFAULT_TOKEN
    if not os.path.exists(p):
        return None, 'token 文件不存在: %s' % p
    try:
        tok = open(p, encoding='utf-8').read().strip()
    except OSError as e:
        return None, 'token 读取失败: %s' % e
    if not tok:
        return None, 'token 为空: %s' % p
    return tok, ''


def split_batches(input_pdf, pages_per_batch=50, pages=None):
    import fitz
    d = fitz.open(input_pdf)
    n = len(d)
    idx = list(range(n))
    if pages:
        idx = []
        for part in str(pages).split(','):
            part = part.strip()
            if not part: continue
            if '-' in part:
                a, b = part.split('-', 1); idx += list(range(int(a) - 1, int(b)))
            else:
                idx.append(int(part) - 1)
        idx = [i for i in idx if 0 <= i < n]
    batches = []
    for k in range(0, len(idx), pages_per_batch):
        batches.append((k // pages_per_batch, idx[k:k + pages_per_batch]))
    return d, batches


def resolve_ocr_params(book, cli=None, root=ROOT):
    """参数优先级 CLI > data/<book>/ocr_params.json > 默认。返回 (params, sources, path, sha)。"""
    import hashlib
    params = dict(OCR_DEFAULTS)
    sources = {k: 'default' for k in OCR_DEFAULTS}
    path = os.path.join(root, 'data', book, 'ocr_params.json')
    sha = None
    if os.path.exists(path):
        try:
            doc = json.load(open(path, encoding='utf-8'))
        except Exception as e:
            raise ValueError('ocr_params.json 解析失败: %s' % e)
        if not isinstance(doc, dict):
            raise ValueError('ocr_params.json 根必须是 object')
        sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
        for k, aliases in _BOOK_KEYS.items():
            for a in aliases:
                if a in doc and doc[a] is not None:
                    params[k] = doc[a]
                    sources[k] = 'book_data'
                    break
    for k, v in (cli or {}).items():
        if v is not None:
            params[k] = v
            sources[k] = 'cli'
    # normalize
    params['max_pixels'] = int(params['max_pixels'])
    params['min_pixels'] = int(params['min_pixels'])
    params['orientation'] = int(params['orientation'])
    params['unwarp'] = int(params['unwarp'])
    params['layout_shape'] = str(params['layout_shape'])
    return params, sources, (path if os.path.exists(path) else None), sha


def payload(layout, prompt, params=None):
    p = dict(OCR_DEFAULTS); p.update(params or {})
    return {"model": "PaddleOCR-VL-1.6", "optionalPayload": json.dumps({
        "useLayoutDetection": layout, "promptLabel": prompt, "temperature": 0,
        "minPixels": int(p['min_pixels']), "maxPixels": int(p['max_pixels']),
        "repetitionPenalty": 1, "topP": 1,
        "layoutShapeMode": str(p['layout_shape']),
        "useDocUnwarping": bool(int(p['unwarp'])),
        "useDocOrientationClassify": bool(int(p['orientation']))})}



def _load_json_objects(path):
    """读取 raw 响应：单 JSON 或 JSONL（服务对大 batch 会返回多个 JSON 行）。"""
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, list) else [d]
    except json.JSONDecodeError:
        objs = []
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    objs.append(json.loads(line))
        return objs


LAYOUT_CATEGORY = {
    'doc_title': 'doc_title', 'paragraph_title': 'paragraph_title', 'title': 'title',
    'text': 'text', 'content': 'content', 'header': 'header', 'footer': 'footer',
    'number': 'number', 'aside_text': 'aside_text', 'image': 'image', 'figure': 'figure',
    'chart': 'chart', 'footer_image': 'footer_image', 'header_image': 'header_image',
    'figure_title': 'figure_title', 'table': 'table', 'algorithm': 'algorithm',
    'seal': 'seal',
}


def convert_layout_json(out_dir, src_pdf, book, jobs=None):
    """layout raw（JSON/JSONL）→ legacy 可读 + canonical blocks 的 layout.json。

    返回 (layout_path, page_count)；无 layout raw 返回 (None, 0)。
    页 key 来自 jobs[key].pages（0-based）；result 页序按 raw 文件/对象顺序拼接。
    canonical 每页同时保留 prunedResult.parsing_res_list，兼容 build_geom/页码现有读取。
    """
    import glob, fitz
    jobs = jobs if jobs is not None else (
        json.load(open(os.path.join(out_dir, 'jobs.json'), encoding='utf-8'))
        if os.path.exists(os.path.join(out_dir, 'jobs.json')) else {})
    raw_paths = sorted(glob.glob(os.path.join(out_dir, 'raw', 'layout_*.json')))
    if not raw_paths:
        return None, 0
    src = fitz.open(src_pdf) if src_pdf and os.path.exists(src_pdf) else None
    records = {}
    seq = 0
    warned = []
    for rp in raw_paths:
        key = os.path.splitext(os.path.basename(rp))[0]
        pages = list((jobs.get(key) or {}).get('pages') or [])
        objs = _load_json_objects(rp)
        results = []
        for d in objs:
            results += ((d.get('result') or {}).get('layoutParsingResults') or [])
        if not pages:
            warned.append('%s: no jobs.pages; sequential' % key)
            pages = list(range(seq, seq + len(results)))
        if len(results) != len(pages):
            warned.append('%s: results=%d pages=%d' % (key, len(results), len(pages)))
        for i, pg in enumerate(results):
            if i >= len(pages):
                break
            gpage = int(pages[i])
            pr = pg.get('prunedResult') or {}
            pw = float(pr.get('width') or 0); ph = float(pr.get('height') or 0)
            pdf_w = pdf_h = None
            if src is not None and 0 <= gpage < len(src):
                pdf_w, pdf_h = src[gpage].rect.width, src[gpage].rect.height
            # canonical bbox 保留 layout px；同时给 build 的兼容 prunedResult 原样
            blocks = []
            for b in pr.get('parsing_res_list') or []:
                lab = b.get('block_label') or 'other'
                blocks.append(dict(category=LAYOUT_CATEGORY.get(lab, 'other'), label=lab,
                                   bbox=b.get('block_bbox'), text=b.get('block_content') or '',
                                   order=b.get('block_order'), group=b.get('group_id'),
                                   score=b.get('score')))
            records[gpage] = dict(page_key=str(gpage), page=gpage + 1,
                                  width=pw, height=ph, page_width_pt=pdf_w, page_height_pt=pdf_h,
                                  bbox_space='layout_px_top_left', blocks=blocks,
                                  prunedResult=dict(width=pw, height=ph,
                                                    parsing_res_list=pr.get('parsing_res_list') or []))
            seq = max(seq, gpage + 1)
    out = os.path.join(out_dir, '%s_layout.json' % book)
    pages = [records[k] for k in sorted(records)]
    json.dump(pages, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    man = dict(source_pages=len(src) if src else None, layout_pages=len(pages),
               page_keys=[p['page_key'] for p in pages], warnings=warned,
               sha256=__import__('hashlib').sha256(open(out, 'rb').read()).hexdigest())
    json.dump(man, open(os.path.join(out_dir, 'layout_manifest.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    if src: src.close()
    return out, len(pages)


def convert_raw_dir(out_dir, src_pdf, book, jobs=None):
    """raw JSON（spotting）→ legacy 2×pt coords/lines（0-based 全局页 key）。

    - spotting_res.rec_texts/rec_polys；每页 pruned width/height → 源 PDF 页尺寸；
    - scale_x = 2*pdf_page_w/pruned_w, scale_y = 2*pdf_page_h/pruned_h（legacy coords = 2×pt）；
    - 全局页号来自 jobs[key].pages（0-based）；页序对齐源 PDF；
    - 输出 <out_dir>/<book>_spotting_coords.json / _lines.json。
    """
    import glob
    jobs = jobs if jobs is not None else (
        json.load(open(os.path.join(out_dir, 'jobs.json'), encoding='utf-8'))
        if os.path.exists(os.path.join(out_dir, 'jobs.json')) else {})
    raw_paths = sorted(glob.glob(os.path.join(out_dir, 'raw', 'spotting_*.json')))
    if not raw_paths:
        return None, None
    import fitz
    src = fitz.open(src_pdf) if src_pdf and os.path.exists(src_pdf) else None
    coords, lines = {}, {}
    used_pages = set()
    for rp in raw_paths:
        key = os.path.splitext(os.path.basename(rp))[0]
        pages = list((jobs.get(key) or {}).get('pages') or [])
        objs = _load_json_objects(rp)
        results = []
        for d in objs:
            results += ((d.get('result') or {}).get('layoutParsingResults') or [])
        if not pages:
            pages = list(range(len(results)))
        for i, pg in enumerate(results):
            if i >= len(pages):
                break
            gpage = int(pages[i])
            pr = pg.get('prunedResult') or {}
            sr = pr.get('spotting_res') or {}
            texts = list(sr.get('rec_texts') or [])
            polys = list(sr.get('rec_polys') or [])
            pw = float(pr.get('width') or 0); ph = float(pr.get('height') or 0)
            pdf_w = pdf_h = None
            if src is not None and 0 <= gpage < len(src):
                pdf_w, pdf_h = src[gpage].rect.width, src[gpage].rect.height
            if not pdf_w or not pdf_h:
                di = []
                for d in objs:
                    di += (((d.get('result') or {}).get('dataInfo') or {}).get('pages') or [])
                if i < len(di):
                    pdf_w, pdf_h = di[i].get('width'), di[i].get('height')
            sx = (2.0 * pdf_w / pw) if (pdf_w and pw) else 1.0
            sy = (2.0 * pdf_h / ph) if (pdf_h and ph) else 1.0
            k = str(gpage)
            coords[k] = [[[round(x * sx, 2), round(y * sy, 2)] for x, y in poly] for poly in polys]
            lines[k] = texts
            used_pages.add(gpage)
    cp = os.path.join(out_dir, '%s_spotting_coords.json' % book)
    lp = os.path.join(out_dir, '%s_spotting_lines.json' % book)
    json.dump(coords, open(cp, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(lines, open(lp, 'w', encoding='utf-8'), ensure_ascii=False)
    return cp, lp


def write_manifest(out_dir, jobs, batches, src_pages):
    man = dict(batches=[], source_pages=src_pages,
               env=dict(PYTHONHASHSEED=(os.environ.get('PYTHONHASHSEED') or '0')))
    for mode_key, info in sorted(jobs.items()):
        if not isinstance(info, dict):
            continue
        man['batches'].append(dict(key=mode_key, state=info.get('state'),
                                   jobId=info.get('jobId'), pages=info.get('pages'),
                                   params=info.get('params')))
    json.dump(man, open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    return man


def run(args):
    tok, err = check_token(args.token_file)
    if tok is None:
        print('[ocr_book] ' + err, file=sys.stderr)
        return 5
    if not os.path.exists(args.input):
        print('[ocr_book] 输入 PDF 不存在: %s' % args.input, file=sys.stderr)
        return 2
    import fitz
    src = fitz.open(args.input)
    os.makedirs(os.path.join(args.out_dir, 'batches'), exist_ok=True)
    os.makedirs(os.path.join(args.out_dir, 'raw'), exist_ok=True)
    n = len(src)
    pages = args.pages or ('1-%d' % n)
    _, batches = split_batches(args.input, args.pages_per_batch, pages)
    jobs_path = os.path.join(args.out_dir, 'jobs.json')
    jobs = json.load(open(jobs_path, encoding='utf-8')) if os.path.exists(jobs_path) else {}
    modes = [('layout', True, 'ocr'), ('spotting', False, 'spotting')]
    if args.mode == 'layout': modes = modes[:1]
    elif args.mode == 'spotting': modes = modes[1:]
    import requests
    H = {'Authorization': 'bearer ' + tok}
    _cli = dict(max_pixels=getattr(args, 'ocr_max_pixels', None),
                min_pixels=getattr(args, 'ocr_min_pixels', None),
                orientation=getattr(args, 'ocr_orientation', None),
                unwarp=getattr(args, 'ocr_unwarp', None),
                layout_shape=getattr(args, 'ocr_layout_shape', None))
    try:
        _params, _psrc, _ppath, _psha = resolve_ocr_params(args.book, _cli)
    except Exception as e:
        print('[ocr_book] ' + str(e), file=sys.stderr); return 2
    json.dump(dict(params=_params, sources=_psrc, path=_ppath, sha256=_psha),
              open(os.path.join(args.out_dir, 'ocr_params_effective.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('[ocr_book] params: %s' % _params)
    failed = 0
    for mode, layout, prompt in modes:
        for bi, idxs in batches:
            key = '%s_%03d' % (mode, bi)
            raw_path = os.path.join(args.out_dir, 'raw', key + '.json')
            if args.resume and os.path.exists(raw_path):
                jobs.setdefault(key, {})
                jobs[key]['pages'] = idxs
                jobs[key]['params'] = _params
                json.dump(jobs, open(jobs_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                continue
            if key in jobs and jobs[key].get('state') == 'done' and os.path.exists(raw_path):
                jobs[key]['pages'] = idxs
                jobs[key]['params'] = _params
                json.dump(jobs, open(jobs_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                continue
            batch_pdf = os.path.join(args.out_dir, 'batches', key + '.pdf')
            if not os.path.exists(batch_pdf):
                out = fitz.open()
                for i in idxs:
                    out.insert_pdf(src, from_page=i, to_page=i)
                out.save(batch_pdf); out.close()
            last = None
            jid = None
            for att in range(4):
                try:
                    with open(batch_pdf, 'rb') as f:
                        r = requests.post(JOB, headers=H, data=payload(layout, prompt, _params),
                                          files={'file': f}, timeout=1800)
                    if r.status_code != 200:
                        raise RuntimeError('HTTP %d %s' % (r.status_code, r.text[:120]))
                    jid = r.json()['data']['jobId']
                    break
                except Exception as e:
                    last = e; time.sleep(8 * (att + 1))
            if jid is None:
                jobs[key] = dict(state='failed', error=str(last)[:200]); failed += 1
                json.dump(jobs, open(jobs_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                continue
            t0 = time.time(); state = 'queued'
            while time.time() - t0 < 3600:
                r = requests.get(JOB + '/' + jid, headers=H, timeout=60)
                r.raise_for_status(); d = r.json()['data']
                state = d.get('state')
                if state == 'done':
                    url = d['resultUrl']['jsonUrl']
                    raw = requests.get(url, timeout=600)
                    raw.raise_for_status()
                    open(raw_path, 'w', encoding='utf-8').write(raw.text)
                    jobs[key] = dict(state='done', jobId=jid, pages=idxs, params=_params)
                    break
                if state == 'failed':
                    jobs[key] = dict(state='failed', jobId=jid, error=str(d.get('errorMsg'))[:200])
                    failed += 1
                    break
                time.sleep(5)
            else:
                jobs[key] = dict(state='timeout', jobId=jid); failed += 1
            json.dump(jobs, open(jobs_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    write_manifest(args.out_dir, jobs, batches, n)
    cp = lp = lay = None
    if args.mode in ('spotting', 'both'):
        cp, lp = convert_raw_dir(args.out_dir, args.input, args.book, jobs)
        print('[ocr_book] coords=%s lines=%s' % (cp, lp))
    if args.mode in ('layout', 'both'):
        lay, nlay = convert_layout_json(args.out_dir, args.input, args.book, jobs)
        print('[ocr_book] layout=%s pages=%s' % (lay, nlay))
    print('[ocr_book] batches=%d modes=%d failed=%d raw=%s' %
          (len(batches), len(modes), failed, os.path.join(args.out_dir, 'raw')))
    return 0 if failed == 0 else 5


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True)
    ap.add_argument('--input', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--token-file', default=DEFAULT_TOKEN)
    ap.add_argument('--mode', default='both', choices=['layout', 'spotting', 'both'])
    ap.add_argument('--pages-per-batch', type=int, default=50)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--pages', default='')
    ap.add_argument('--ocr-max-pixels', type=int, default=None)
    ap.add_argument('--ocr-min-pixels', type=int, default=None)
    ap.add_argument('--ocr-orientation', type=int, default=None, choices=[0, 1])
    ap.add_argument('--ocr-unwarp', type=int, default=None, choices=[0, 1])
    ap.add_argument('--ocr-layout-shape', default=None)
    args = ap.parse_args(argv)
    return run(args)


if __name__ == '__main__':
    sys.exit(main())
