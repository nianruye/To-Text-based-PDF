#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""battle6/t26 判定：8 槽页（槽宽 100 API 坐标）-> API 文本 vs OCR 文本。

- 归一化：variant_norm（opencc t2tw + 自建）；
- 去空白：API/OCR 文本先剥空白（列条带换行/空格不算插入）；
- 端部插入（条带上下 1.2 步上下文造成，pos=0 或 pos=len）不计；
- 内部单字插入记 true_insert；替换若归一化后等值记 variant（本脚本并入 same/other）；
- 输出 tmp_vert/battle6/api_pilot_25.json。
"""
import argparse, json, difflib, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from variant_norm import norm_text, norm_char

PUN = '「」『』（），。、；：！？…—〇'

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--items', default='tmp_vert/battle6/pilot25_items.json')
    ap.add_argument('--polys', default='tmp_vert/battle6/api_pilot_25_polys.json')
    ap.add_argument('--out', default='tmp_vert/battle6/api_pilot_25.json')
    a = ap.parse_args()
    items = json.load(open(a.items, encoding='utf-8'))
    D = json.load(open(a.polys, encoding='utf-8'))
    slots = []
    for b in D:
        if not b.get('ok'):
            continue
        for p in b['pages']:
            s = [''] * 8
            for t, pl in zip(p['texts'], p['polys']):
                if not pl:
                    continue
                cx = sum(q[0] for q in pl) / len(pl)
                k = min(7, max(0, int(cx / 100.0)))
                s[k] += t
            slots.extend(s)
    rows = []
    for i, it in enumerate(items):
        api = slots[i] if i < len(slots) else ''
        cls, ch, ratio, pos = judge(it['text'], api)
        rows.append(dict(id=it['id'], page=it['page'], col=it['col'], text=it['text'],
                         api=strip_ws(api), cls=cls, ch=ch, pos=pos, ratio=round(ratio, 3),
                         n=it['n'], cells=it['cells']))
    from collections import Counter
    cnt = Counter(r['cls'] for r in rows)
    ins = [r for r in rows if r['cls'] == 'true_insert']
    han = [r for r in ins if r['ch'] and not re.match('[' + PUN + r']', r['ch'])]
    out = dict(n_items=len(items), classes=dict(cnt),
               insert_rate=round(len(ins) / max(1, len(rows)), 4),
               hanzi_insert_rate=round(len(han) / max(1, len(rows)), 4),
               n_insert=len(ins), n_hanzi=len(han), items=rows)
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(cnt), ensure_ascii=False), 'insert', len(ins), 'hanzi', len(han),
          'rate', out['insert_rate'], 'hanzi_rate', out['hanzi_insert_rate'])

if __name__ == '__main__':
    main()
