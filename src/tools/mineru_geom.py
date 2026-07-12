#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mineru_geom.py — 从 MinerU 输出提取逐行几何(字数/位置)+ 分部分面积/行高。
只取 MinerU 的【几何结构】(不用其文字作输出),用于驱动"逐行字数还原 + 面积定字号"。

用法: python3 mineru_geom.py <middle.json> <content_list.json> <out.json>
"""
import json, sys, statistics

def extract(middle_path, cl_path):
    mid = json.load(open(middle_path, encoding='utf-8'))
    cl = json.load(open(cl_path, encoding='utf-8'))
    result = {}
    for page_idx, pinfo in enumerate(mid['pdf_info']):
        lines = []
        for pb in pinfo.get('para_blocks', []):
            btype = pb.get('type', 'text')
            for ln in pb.get('lines', []):
                bb = ln.get('bbox')
                if not bb or len(bb) < 4: continue
                txt = ''.join(s.get('content', '') for s in ln.get('spans', []))
                # 只取字数(长度),不存 MinerU 文字本身
                lines.append({
                    'chars': len(txt), 'y': round(bb[1], 1),
                    'x0': round(bb[0], 1), 'w': round(bb[2]-bb[0], 1),
                    'h': round(bb[3]-bb[1], 1), 'type': btype,
                })
        # 分部分面积(content_list type + bbox)
        sections = {}
        page_num = None
        for it in cl:
            if it.get('page_idx') != page_idx: continue
            t = it.get('type', 'text'); bb = it.get('bbox')
            area = (bb[2]-bb[0])*(bb[3]-bb[1]) if bb and len(bb) >= 4 else 0
            d = sections.setdefault(t, {'area': 0.0, 'count': 0, 'h_list': []})
            d['area'] += area; d['count'] += 1
            if bb and len(bb) >= 4: d['h_list'].append(round(bb[3]-bb[1], 1))
            if t == 'page_number':
                page_num = (it.get('text') or '').strip()
        # 满行正文 cw / 行高 / measure(用于字号)
        body = [l for l in lines if l['type'] == 'text' and l['chars'] > 5]
        full_cw = body_h = body_measure = 0
        if body:
            max_w = max(l['w'] for l in body)
            full = [l for l in body if l['w'] > 0.80 * max_w]   # 满行(≥80%最宽)
            if full:
                full_cw = int(statistics.median([l['chars'] for l in full]))
                body_h = round(statistics.median([l['h'] for l in full]), 1)
                body_measure = round(statistics.median([l['w'] for l in full]), 1)
        # 行高按部分(字号来源)
        sec_h = {t: round(statistics.median(d['h_list']), 1) if d['h_list'] else 0
                 for t, d in sections.items()}
        result[str(page_idx)] = {
            'L': len(lines),
            'line_chars': [l['chars'] for l in lines],   # 逐行字数(切分 PaddleOCR 文字用)
            'full_cw': full_cw, 'body_h': body_h, 'body_measure': body_measure,
            'sections': {t: {'area': round(d['area']), 'count': d['count']} for t, d in sections.items()},
            'sec_h': sec_h,
            'page_number': page_num,
        }
    return result

if __name__ == '__main__':
    mid = sys.argv[1]; cl = sys.argv[2]; out = sys.argv[3]
    res = extract(mid, cl)
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # 概览
    cws = [v['full_cw'] for v in res.values() if v['full_cw']]
    hs = [v['body_h'] for v in res.values() if v['body_h']]
    ms = [v['body_measure'] for v in res.values() if v['body_measure']]
    print(f"页数 {len(res)}")
    if cws: print(f"满行字数 cw: 中位={statistics.median(cws):.0f} 范围={min(cws)}-{max(cws)}")
    if hs: print(f"正文行高: 中位={statistics.median(hs):.1f}pt → 字号≈{statistics.median(hs)/1.2:.1f}pt")
    if ms: print(f"正文 measure: 中位={statistics.median(ms):.0f}pt")
    if cws and ms: print(f"交叉验证 measure/cw={statistics.median(ms)/statistics.median(cws):.1f}pt (应≈行高)")
    # 抽一页
    for k in ['3', '6']:
        if k in res:
            v = res[k]; print(f"\npage {k}: L={v['L']} cw={v['full_cw']} 行高={v['body_h']} measure={v['body_measure']} 页码={v['page_number']}")
            print(f"  逐行字数(前12): {v['line_chars'][:12]}")
            print(f"  分面积: {v['sections']}")
