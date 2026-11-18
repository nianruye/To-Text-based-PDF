#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""垂直布局单页探针：源 OCR 行 vs 产物 PDF 行，按文本配对并比较行间距。

用法:
  /usr/bin/python3 src/tools/vlayout_probe.py --book wz3 --pages 22,24,26 \
    --pdf deliverables/wz3.pdf --coords data/wz3/wz3_linelevel_spotting_coords.json \
    --lines data/wz3/wz3_linelevel_spotting_lines.json --dpi 200 [--json /tmp/vl.json]
"""
import argparse, json, re, statistics, sys, unicodedata
import fitz

RED = '\033[31m'; RESET = '\033[0m'

def norm(s):
    s = unicodedata.normalize('NFKC', str(s or ''))
    s = re.sub(r'[.·…．]{2,}', '', s)
    return re.sub(r'\s+', '', s)

def line_h(poly):
    ys = [q[1] for q in poly]; return (max(ys) - min(ys)) if ys else 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True)
    ap.add_argument('--pages', required=True, help='1-based, comma separated')
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--coords', required=True)
    ap.add_argument('--lines', required=True)
    ap.add_argument('--dpi', type=float, default=200.0)
    ap.add_argument('--json', default='')
    a = ap.parse_args()
    co = json.load(open(a.coords, encoding='utf-8'))
    sl = json.load(open(a.lines, encoding='utf-8'))
    doc = fitz.open(a.pdf)
    pages = [int(x) for x in a.pages.split(',') if x.strip()]
    out = {'book': a.book, 'pdf': a.pdf, 'dpi': a.dpi, 'pages': []}

    # 相邻页文本用于书眉重复判定
    def page_texts(k):
        return [str(t).strip() for t in sl.get(str(k), []) if str(t).strip()]
    for p in pages:
        key = str(p - 1)
        adj = set()
        for _k in (p - 2, p, p + 1):
            adj.update(norm(t) for t in page_texts(_k))
        src = []
        for i, t in enumerate(sl.get(key, [])):
            poly = co.get(key, [])[i] if i < len(co.get(key, [])) else None
            if not poly or not str(t).strip(): continue
            ys = [q[1] for q in poly]; xs = [q[0] for q in poly]
            src.append({'i': i, 't': str(t).strip(), 'n': norm(t),
                        'y': min(ys) * 72.0 / a.dpi, 'x': min(xs) * 72.0 / a.dpi,
                        'h': line_h(poly)})
        src.sort(key=lambda r: (r['y'], r['x']))
        body_h = statistics.median([r['h'] for r in src]) if src else 0
        for r in src:
            if re.match(r'^第[一二三四五六七八九十百千零\d]+[章节编篇]', r['t']) or (body_h and r['h'] > 1.5 * body_h):
                r['type'] = '标题'
            elif r['n'] in adj or (r['y'] < 0.10 * doc[p - 1].rect.height and r['h'] < 1.1 * body_h):
                r['type'] = '书眉'
            else:
                r['type'] = '正文'
        # 产物行
        prod = []
        for b in doc[p - 1].get_text('dict')['blocks']:
            for l in b.get('lines', []):
                t = ''.join(s.get('text', '') for s in l.get('spans', [])).strip()
                if t: prod.append({'t': t, 'n': norm(t), 'y': l['bbox'][1], 'page_y': l['bbox'][1]})
        prod.sort(key=lambda r: r['y'])
        used = set()
        for r in src:
            hit = [j for j, q in enumerate(prod) if j not in used and q['n'] == r['n']]
            if not hit:
                cand = [(j, q) for j, q in enumerate(prod) if j not in used and (r['n'] in q['n'] or q['n'] in r['n']) and len(r['n']) >= 4]
                hit = [min(cand, key=lambda z: abs(z[1]['y'] - r['y']))[0]] if cand else []
            if hit:
                j = min(hit, key=lambda j: abs(prod[j]['y'] - r['y']))
                used.add(j); r['prod_y'] = prod[j]['y']; r['prod_t'] = prod[j]['t']; r['matched'] = True
            else:
                r['matched'] = False; r['prod_y'] = None
        unmatched = [q for j, q in enumerate(prod) if j not in used and q['y'] > 0.10 * doc[p - 1].rect.height]
        paired = [r for r in src if r['matched']]
        gaps = []
        for a1, b1 in zip(paired, paired[1:]):
            ds = b1['y'] - a1['y']; dp = b1['prod_y'] - a1['prod_y']
            gaps.append({'from': a1['t'][:20], 'to': b1['t'][:20], 'src': round(ds, 1),
                         'prod': round(dp, 1), 'dev': round(dp - ds, 1)})
        devs = [abs(g['dev']) for g in gaps]
        maxdev = max(devs) if devs else 0.0
        status = 'PASS' if maxdev <= 3.0 else 'FAIL'
        print(f'\n{a.book} p{p}  源{len(src)}行 / 产物{len(prod)}行 / 配对{len(paired)}')
        print('  源  : ' + ' '.join(f"[{r['y']:.1f} {r['type']}]" for r in src[:10]))
        print('  产物: ' + ' '.join(f"[{r['prod_y']:.1f}]" if r['matched'] else '[未配]' for r in paired[:10]))
        if gaps:
            print('  间距: 源 ' + '/'.join(f"{g['src']:.1f}" for g in gaps[:8]) +
                  ' | 产物 ' + '/'.join(f"{g['prod']:.1f}" for g in gaps[:8]) +
                  ' | 偏差 ' + '/'.join(f"{g['dev']:+.1f}" for g in gaps[:8]))
        for r in src:
            if not r['matched']:
                print(f'  未配对源行: y={r["y"]:.1f} {r["type"]} {r["t"][:40]!r}')
        if unmatched:
            print('  产物多出行: ' + '; '.join(f"y={q['y']:.1f} {q['t'][:28]!r}" for q in unmatched[:6]))
        flag = f'{RED}FAIL{RESET}' if status == 'FAIL' else 'PASS'
        print(f'  汇总: 最大偏差 {maxdev:.1f}pt  {flag} (≤3pt)')
        out['pages'].append({'page': p, 'rows': src, 'unmatched_product': unmatched,
                             'gaps': gaps, 'max_dev': maxdev, 'status': status})
    doc.close()
    if a.json:
        json.dump(out, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return 0 if all(q['status'] == 'PASS' for q in out['pages']) else 1

if __name__ == '__main__':
    sys.exit(main())
