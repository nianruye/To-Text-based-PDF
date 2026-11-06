#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""battle6/t27：候选集全量判定 + 汉字/标点清单 + 完整字块校验 + Wilson CI。"""
import argparse, json, difflib, os, re, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from variant_norm import norm_text, norm_char

PUN = '「」『』（），。、；：！？…—〇【】〔〕《》〈〉︗︘︹︺︽︾︿﹀'

def strip_ws(s):
    return re.sub(r'\s+', '', s or '')

def judge(ocr, api):
    on = norm_text(strip_ws(ocr)); an = norm_text(strip_ws(api))
    if not an:
        return 'nonchar', None, 0.0, None
    if on == an:
        return 'same', None, 1.0, None
    ins = []; rep = []; edge = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, on, an).get_opcodes():
        if tag == 'insert':
            if i1 == 0 or i1 == len(on):
                edge += 1
            else:
                ins.append((i1, an[j1:j2]))
        elif tag == 'replace':
            for k in range(min(i2 - i1, j2 - j1)):
                rep.append((on[i1 + k], an[j1 + k]))
    ratio = difflib.SequenceMatcher(None, on, an).ratio()
    if not ins and not rep and edge <= 2 and abs(len(an) - len(on)) <= 2:
        return 'same', None, ratio, None
    if len(ins) == 1 and len(ins[0][1]) == 1:
        return 'true_insert', ins[0][1], ratio, ins[0][0]
    if len(ins) == 1 and len(ins[0][1]) <= 2:
        return 'true_insert', ins[0][1], ratio, ins[0][0]
    if rep and all(norm_char(a) == norm_char(b) for a, b in rep) and not ins:
        return 'variant', None, ratio, None
    return 'other', None, ratio, None

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - r) / d), min(1.0, (c + r) / d))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', default='wz7')
    ap.add_argument('--out-dir', default=None, help='默认 tmp_vert/battle6（wz7）/ tmp_vert/{book}')
    ap.add_argument('--items', default=None, help='默认 {out-dir}/all_items.json')
    ap.add_argument('--raw', default=None, help='默认 {out-dir}/api_candidates_all_raw.json')
    ap.add_argument('--out', default=None, help='默认 {out-dir}/api_candidates_all.json')
    ap.add_argument('--src', default=None, help='默认 source_pdf/{book}.pdf')
    ap.add_argument('--crops-dir', default=None, help='默认 {out-dir}/all_insert_crops')
    a = ap.parse_args()
    out_dir = a.out_dir or ('tmp_vert/battle6' if a.book == 'wz7' else f'tmp_vert/{a.book}')
    a.items = a.items or os.path.join(out_dir, 'all_items.json')
    a.raw = a.raw or os.path.join(out_dir, 'api_candidates_all_raw.json')
    a.out = a.out or os.path.join(out_dir, 'api_candidates_all.json')
    a.src = a.src or f'source_pdf/{a.book}.pdf'
    a.crops_dir = a.crops_dir or os.path.join(out_dir, 'all_insert_crops')
    items = json.load(open(a.items, encoding='utf-8'))
    raw = json.load(open(a.raw, encoding='utf-8'))
    import fitz
    from PIL import Image
    src = fitz.open(a.src)
    os.makedirs(a.crops_dir, exist_ok=True)
    slots = []
    for b in raw['batches']:
        if not b.get('ok'): continue
        for p in b['page_data']:
            s = [''] * 8
            for t, pl in zip(p['texts'], p['polys']):
                if not pl: continue
                cx = sum(q[0] for q in pl) / len(pl)
                k = min(7, max(0, int(cx / 100.0)))
                s[k] += t
            slots.extend(s)
    rows = []
    for i, it in enumerate(items):
        api = slots[i] if i < len(slots) else ''
        cls, ch, ratio, pos = judge(it['text'], api)
        rec = dict(id=it['id'], page=it['page'], col=it['col'], text=it['text'],
                   api=strip_ws(api), cls=cls, ch=ch, pos=pos, ratio=round(ratio, 3),
                   n=it['n'], cells=it['cells'], strip=it.get('strip'), cell=None,
                   crop=None, complete=None)
        if cls == 'true_insert' and pos is not None:
            step = (it['col'][3] - it['col'][1]) / max(1, it['cells'])
            p = max(0, min(it['cells'] - 1, pos))
            ya = it['col'][1] + p * step
            r = fitz.Rect(it['col'][0], ya, it['col'][2], ya + step)
            pm = src[it['page'] - 1].get_pixmap(clip=r, dpi=300)
            arr = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)[:, :, :3].mean(axis=2).astype(np.float32)
            m = arr < (np.median(arr) - 25)
            from scipy import ndimage
            lab, nn = ndimage.label(m)
            best = None
            for j, s in enumerate(ndimage.find_objects(lab), 1):
                if s is None: continue
                hh = s[0].stop - s[0].start; ww = s[1].stop - s[1].start
                if hh < 4 or ww < 4: continue
                if best is None or hh * ww > best[0]: best = (hh * ww, hh, ww, float((lab[s] == j).mean()))
            rec['cell'] = [round(it['col'][0], 1), round(ya, 1), round(it['col'][2], 1), round(ya + step, 1)]
            cp = os.path.join(a.crops_dir, '%05d.png' % it['id'])
            Image.fromarray(arr.astype(np.uint8)).resize((96, 96), Image.LANCZOS).save(cp)
            rec['crop'] = cp
            if best:
                _, hh, ww, fill = best
                hpt = hh * 72.0 / 300.0; wpt = ww * 72.0 / 300.0
                rec['complete'] = bool(hpt >= 0.55 * step and wpt >= 0.45 * step and 0.05 <= fill <= 0.7)
                rec['shape'] = dict(w=round(wpt, 1), h=round(hpt, 1), fill=round(fill, 3))
        rows.append(rec)
    from collections import Counter
    cnt = Counter(r['cls'] for r in rows)
    ins = [r for r in rows if r['cls'] == 'true_insert']
    han = [r for r in ins if r['ch'] and len(r['ch']) == 1 and 0x3400 <= ord(r['ch']) <= 0x9FFF]
    han_ok = [r for r in han if r.get('complete')]
    punct = [r for r in ins if r['ch'] and (not (len(r['ch']) == 1 and 0x3400 <= ord(r['ch']) <= 0x9FFF))]
    lo, hi = wilson(len(han_ok), len(rows))
    out = dict(n_items=len(items), classes=dict(cnt),
               n_insert=len(ins), n_hanzi=len(han), n_hanzi_complete=len(han_ok),
               n_punct=len(punct),
               hanzi_rate=round(len(han_ok) / max(1, len(rows)), 4),
               hanzi_ci=[round(lo, 4), round(hi, 4)],
               hanzi_list=[dict(page=r['page'], col=r['col'], cell=r.get('cell'), ch=r['ch'],
                                pos=r['pos'], confidence=r['ratio'], complete=r.get('complete'),
                                shape=r.get('shape'), crop=r.get('crop'), strip=r.get('strip'),
                                text=r['text'], api=r['api']) for r in han_ok],
               punct_list=[dict(page=r['page'], col=r['col'], cell=r.get('cell'), ch=r['ch'],
                                pos=r['pos'], confidence=r['ratio'], crop=r.get('crop'),
                                strip=r.get('strip'), text=r['text'], api=r['api']) for r in punct],
               items=rows)
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(cnt), ensure_ascii=False), 'insert', len(ins), 'hanzi', len(han),
          'hanzi_complete', len(han_ok), 'punct', len(punct), 'rate', out['hanzi_rate'], 'CI', out['hanzi_ci'])

if __name__ == '__main__':
    main()
