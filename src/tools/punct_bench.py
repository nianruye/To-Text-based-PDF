#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""punct_bench v1.1：GB/T 标点全集评测器（spec/governance/PUNCT_EVAL.md v1.1 §7）。

覆盖：句读 7 类、引号（单/双、横/竖形态）、括号（圆/方/六角/方头）、破折号、省略号、
书名号（双/单）、圈码（extension）、段落边界（v2 预留，v1 不计分）；兼容 v1 旧 gold。
只读评测；不联网/不调 API；不改产物。
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
import difflib

# ---------------- 类与形态 ----------------
SENTENCE = {
    '。': 'period', '．': 'period',
    '？': 'question', '！': 'exclamation',
    '，': 'comma', '、': 'enumeration_comma',
    '；': 'semicolon', '：': 'colon',
}
QUOTE_OPEN = set('“「『﹁﹃')
QUOTE_CLOSE = set('”」』﹂﹄')
BRACKET_OPEN = set('（〔【［︵︹')
BRACKET_CLOSE = set('）〕】］︶︺')
BOOK_OPEN = set('《〈︽︿')
BOOK_CLOSE = set('》〉︾﹀')
DASH_CHARS = set('—–―')
ELLIPSIS_CHARS = set('…⋯')
VERTICAL_FORMS = set('﹁﹂﹃﹄︵︶︹︺︽︾︿﹀')
RING_RANGES = ((0xE100, 0xE1FF), (0x2460, 0x24FF), (0x2776, 0x2793))
BRACKET_KIND = {'（': '（）', '︵': '（）', '〔': '〔〕', '︹': '〔〕',
                '【': '【】', '［': '［］'}
OUT_OF_SCOPE = {'connector', 'interpunct', 'emphasis_dot', 'proper_name_line', 'separator'}

GB_CLASS = {
    'period': '句号', 'question': '问号', 'exclamation': '叹号', 'comma': '逗号',
    'enumeration_comma': '顿号', 'semicolon': '分号', 'colon': '冒号',
    'quote_open': '引号', 'quote_close': '引号',
    'bracket_present': '括号', 'bracket_type': '括号',
    'dash': '破折号', 'ellipsis': '省略号',
    'booktitle_open': '书名号', 'booktitle_close': '书名号',
    'ring': '圈码(扩展)', 'paragraph_boundary': '段落(扩展)',
}

def form_of(ch):
    return 'vertical' if ch in VERTICAL_FORMS else 'horizontal'

def canon(ch):
    table = {'﹁': '「', '﹂': '」', '﹃': '『', '﹄': '』',
             '︵': '（', '︶': '）', '︹': '〔', '︺': '〕',
             '︽': '《', '︾': '》', '︿': '〈', '﹀': '〉',
             '．': '。', '–': '—', '―': '—', '⋯': '…'}
    return table.get(ch, ch)

def _sha(path):
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''):
                h.update(b)
        return h.hexdigest()
    except OSError:
        return ''

def _ring_number(ch):
    o = ord(ch)
    if 0xE100 <= o <= 0xE1FF: return o - 0xE100
    if 0x2460 <= o <= 0x24FF: return o - 0x2460 + 1
    if 0x2776 <= o <= 0x2793: return o - 0x2776 + 1
    return None

def _norm_text(t):
    return ''.join((t or '').split())

def _edit_distance(a, b):
    if a == b: return 0
    la, lb = len(a), len(b)
    if not la: return lb
    if not lb: return la
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * lb
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[lb]

def load_coords_lines(coords_path, lines_path):
    return json.load(open(coords_path, encoding='utf-8')), json.load(open(lines_path, encoding='utf-8'))

def _bbox_of(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)

def _mk(base, cls, value, **kw):
    d = dict(base); d.update({'class': cls, 'value': value}); d.update(kw); return d

def extract_predictions(coords, lines):
    """逐列文本 -> 标点预测项（GB/T 全集；旧 4 类兼容）。"""
    preds = []
    pages = {}
    for k, rows in lines.items():
        try:
            page = int(k) + 1
        except ValueError:
            continue
        cs = coords.get(k) or []
        pages[page] = []
        for col, text in enumerate(rows):
            text = '' if text is None else str(text)
            page_text = _norm_text(text)
            pages[page].append(page_text)
            if col >= len(cs) or not cs[col]:
                continue
            x0, y0, x1, y1 = _bbox_of(cs[col])
            n = max(1, len(text))
            step_y = (y1 - y0) / n; step_x = x1 - x0; cx = (x0 + x1) / 2.0
            i = 0
            while i < len(text):
                ch = text[i]
                base = dict(page=page, column=col, char_pos=i, axis='vertical', form=form_of(ch),
                            bbox=[round(x0, 2), round(y0 + i * step_y, 2), round(x1, 2),
                                  round(y0 + (i + 1) * step_y, 2)],
                            cell=[round(cx, 2), round(y0 + (i + 0.5) * step_y, 2),
                                  round(step_x, 2), round(step_y, 2)])
                if ch in SENTENCE:
                    preds.append(_mk(base, SENTENCE[ch], ch))
                elif ch in QUOTE_OPEN:
                    preds.append(_mk(base, 'quote_open', ch))
                elif ch in QUOTE_CLOSE:
                    preds.append(_mk(base, 'quote_close', ch))
                elif ch in BOOK_OPEN:
                    preds.append(_mk(base, 'booktitle_open', ch))
                elif ch in BOOK_CLOSE:
                    preds.append(_mk(base, 'booktitle_close', ch))
                elif ch in BRACKET_OPEN:
                    j = i + 1
                    while j < len(text) and text[j] not in BRACKET_CLOSE:
                        j += 1
                    name = text[i + 1:j]
                    btype = BRACKET_KIND.get(ch, '〔〕')
                    if name:
                        preds.append(_mk(base, 'bracket_type', btype, name=name, btype=btype,
                                         pair_id='p%d-c%d-b%d' % (page, col, i)))
                    else:
                        preds.append(_mk(base, 'bracket_present', True, btype=btype,
                                         pair_id='p%d-c%d-b%d' % (page, col, i)))
                elif ch in DASH_CHARS:
                    j = i
                    while j < len(text) and text[j] in DASH_CHARS:
                        j += 1
                    preds.append(_mk(base, 'dash', text[i:j], length_pt=round((j - i) * step_y, 2)))
                    i = j
                    continue
                elif ch in ELLIPSIS_CHARS:
                    j = i
                    while j < len(text) and text[j] in ELLIPSIS_CHARS:
                        j += 1
                    preds.append(_mk(base, 'ellipsis', text[i:j], length_pt=round((j - i) * step_y, 2)))
                    i = j
                    continue
                else:
                    rn = _ring_number(ch)
                    if rn is not None:
                        preds.append(_mk(base, 'ring', str(rn), number=rn))
                i += 1
    return preds, pages

def load_gold(path):
    d = json.load(open(path, encoding='utf-8'))
    return d, d.get('items') or []

def _center(item):
    if item.get('cell'):
        c = item['cell']
        return c[0], c[1], max(1e-6, c[2]), max(1e-6, c[3])
    b = item.get('bbox') or [0, 0, 0, 0]
    return (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0, max(1e-6, b[2] - b[0]), max(1e-6, b[3] - b[1])

def _iou(a, b):
    x0 = max(a[0], b[0]); y0 = max(a[1], b[1]); x1 = min(a[2], b[2]); y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0: return 0.0
    inter = (x1 - x0) * (y1 - y0)
    area = max(1e-9, (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)
    return inter / area

def _group(cls):
    if cls in ('quote_open', 'quote_close'): return 'quote'
    if cls in ('bracket_present', 'bracket_type'): return 'bracket'
    if cls in ('booktitle_open', 'booktitle_close'): return 'booktitle'
    return cls  # 句读/破折号/省略号/ring 各自成组

def match_items(gold_items, preds, tol=0.5):
    preds_by = {}
    for p in preds:
        preds_by.setdefault((p['page'], p['column'], _group(p['class'])), []).append(p)
    used = set(); pairs = []; unmatched = []
    for g in sorted(gold_items, key=lambda x: (x.get('page', 0), str(x.get('column', '')), x.get('char_pos', 0), x.get('class', ''))):
        if g.get('class') in OUT_OF_SCOPE or g.get('class') == 'paragraph_boundary':
            continue
        gk = (g.get('page'), g.get('column'), _group(g.get('class')))
        cands = [p for p in preds_by.get(gk, []) if id(p) not in used]
        gcx, gcy, gsx, gsy = _center(g)
        best = None
        for p in cands:
            pcx, pcy, psx, psy = _center(p)
            dx = abs(pcx - gcx) / max(gsx, psx, 1e-6)
            dy = abs(pcy - gcy) / max(gsy, psy, 1e-6)
            dist = max(dx, dy)
            ok = dist <= tol or _iou(g.get('bbox') or [0, 0, 0, 0], p.get('bbox') or [0, 0, 0, 0]) >= 0.5
            if not ok: continue
            score = dist + (0.02 if p.get('class') != g.get('class') else 0.0)
            if best is None or score < best[0]:
                best = (score, p)
        if best:
            used.add(id(best[1])); pairs.append((g, best[1]))
        else:
            unmatched.append(dict(gold_id=g.get('id'), page=g.get('page'), column=g.get('column'),
                                  char_pos=g.get('char_pos'), cls=g.get('class'),
                                  reason='no_prediction_in_tolerance'))
    fps = [p for p in preds if id(p) not in used]
    return pairs, unmatched, fps

def compute_metrics(items, pairs, unmatched, fps):
    by = {}
    def bump(cls):
        by.setdefault(cls, dict(tp=0, fp=0, fn=0, dir_ok=0, dir_total=0, type_ok=0, type_total=0,
                                value_ok=0, value_total=0, len_errors=[], form_ok=0, form_total=0))
    for g, p in pairs:
        gc, pc = g.get('class'), p.get('class')
        bump(pc); by[pc]['tp'] += 1
        if gc in ('quote_open', 'quote_close', 'booktitle_open', 'booktitle_close'):
            by[pc]['dir_total'] += 1
            if gc == pc: by[pc]['dir_ok'] += 1
        if pc == 'bracket_type':
            by[pc]['type_total'] += 1
            gb = str(g.get('btype') or g.get('value') or '')
            pb = str(p.get('btype') or '')
            if gb in BRACKET_KIND.values() or gb in ('（）', '〔〕', '【】', '［］'):
                ok = (gb == pb)
            else:
                ok = str(p.get('name') or '') == str(g.get('name') or '')
            if ok:
                by[pc]['type_ok'] += 1
        if pc in SENTENCE.values():
            by[pc]['value_total'] += 1
            if canon(str(p.get('value'))) == canon(str(g.get('value'))):
                by[pc]['value_ok'] += 1
        if pc in ('dash', 'ellipsis'):
            gl = g.get('length_pt') or 0; pl = p.get('length_pt') or 0
            if gl: by[pc]['len_errors'].append(abs(pl - gl))
        if pc == 'ring':
            by[pc]['value_total'] += 1
            if str(p.get('value')) == str(g.get('value')): by[pc]['value_ok'] += 1
        # form 诊断（不罚）
        by[pc]['form_total'] += 1
        if g.get('form') and p.get('form') and g.get('form') == p.get('form'):
            by[pc]['form_ok'] += 1
    # 多段引文：非最后段缺闭号不计 FN
    for u in unmatched:
        gc = u.get('cls'); bump(gc)
        if gc == 'quote_close':
            g = next((x for x in items if x.get('id') == u.get('gold_id')), {})
            if g.get('quote_group_id') and g.get('is_final_paragraph') is False:
                u['reason'] = 'valid_carry_non_final_paragraph'; continue
        by[gc]['fn'] += 1
    for p in fps:
        pc = p.get('class'); bump(pc); by[pc]['fp'] += 1
    # 多段结构：中间段闭号 unexpected_close
    groups = {}
    for g in items:
        qg = g.get('quote_group_id')
        if qg and g.get('class') in ('quote_open', 'quote_close'):
            groups.setdefault(qg, []).append(g)
    unexpected = 0; multi_total = 0; multi_ok = 0
    for qg, gs in groups.items():
        pcount = max((x.get('paragraph_count') or 1) for x in gs)
        if pcount <= 1: continue
        multi_total += 1
        closes = [x for x in gs if x.get('class') == 'quote_close']
        bad = False
        for x in closes:
            if x.get('is_final_paragraph') is False:
                unexpected += 1; bad = True
        if not bad: multi_ok += 1
    def score(st):
        tp, fp, fn = st['tp'], st['fp'], st['fn']
        out = dict(tp=tp, fp=fp, fn=fn,
                   precision=round(tp / (tp + fp), 4) if tp + fp else 0.0,
                   recall=round(tp / (tp + fn), 4) if tp + fn else 0.0,
                   false_insertion_rate=round(fp / (tp + fp), 4) if tp + fp else 0.0,
                   miss_rate=round(fn / (tp + fn), 4) if tp + fn else 0.0)
        if st['dir_total']: out['direction_accuracy'] = round(st['dir_ok'] / st['dir_total'], 4)
        if st['type_total']: out['type_accuracy'] = round(st['type_ok'] / st['type_total'], 4)
        if st['value_total']: out['value_accuracy'] = round(st['value_ok'] / st['value_total'], 4)
        if st['len_errors']:
            errs = sorted(st['len_errors'])
            out['length_median_error'] = round(errs[len(errs) // 2], 2)
            out['length_p95_error'] = round(errs[min(len(errs) - 1, int(len(errs) * 0.95))], 2)
        if st['form_total']: out['form_accuracy'] = round(st['form_ok'] / st['form_total'], 4)
        return out
    res = {k: score(v) for k, v in by.items()}
    structural = dict(unexpected_close=unexpected, multi_para_groups=multi_total,
                      multi_para_validity=round(multi_ok / multi_total, 4) if multi_total else 0.0)
    return res, structural

def by_gb(by_class):
    out = {}
    for cls, st in by_class.items():
        gb = GB_CLASS.get(cls, cls)
        agg = out.setdefault(gb, dict(tp=0, fp=0, fn=0))
        for k in ('tp', 'fp', 'fn'): agg[k] += st.get(k, 0)
    for gb, st in out.items():
        tp, fp, fn = st['tp'], st['fp'], st['fn']
        st['precision'] = round(tp / (tp + fp), 4) if tp + fp else 0.0
        st['recall'] = round(tp / (tp + fn), 4) if tp + fn else 0.0
    return out

def eval_content(content_gold, pages):
    items = content_gold.get('items') if isinstance(content_gold, dict) else None
    if items is None:
        items = [dict(page=int(k), text=v) for k, v in (content_gold or {}).items()]
    rows = []; tot_dist = tot_len = 0
    miss = wrong = extra = doubt = 0
    for it in sorted(items, key=lambda x: int(x['page'])):
        page = int(it['page']); gold = _norm_text(it.get('text') or '')
        pred = ''.join(pages.get(page) or [])
        doubt += gold.count('?'); gold = gold.replace('?', '')
        sm = difflib.SequenceMatcher(None, gold, pred, autojunk=False)
        dist = sum(max(i1 - i0, j1 - j0) for tag, i0, i1, j0, j1 in sm.get_opcodes() if tag != 'equal')
        m = w = e = 0
        for tag, i0, i1, j0, j1 in sm.get_opcodes():
            if tag == 'replace': w += max(i1 - i0, j1 - j0)
            elif tag == 'delete': m += i1 - i0
            elif tag == 'insert': e += j1 - j0
        miss += m; wrong += w; extra += e
        tot_dist += dist; tot_len += len(gold)
        rows.append(dict(page=page, gold_chars=len(gold), pred_chars=len(pred), edit_distance=dist,
                         cer=round(dist / len(gold), 4) if gold else 0.0, missing=m, wrong=w, extra=e))
    return dict(gold_chars=tot_len, edit_distance=tot_dist, cer=round(tot_dist / tot_len, 4) if tot_len else 0.0,
                missing=miss, wrong=wrong, extra=extra, doubt_chars=doubt, by_page=rows)

def write_csv(path, rows, mode='cell'):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['mode', 'split', 'class', 'page', 'metric', 'value'])
        for r in rows:
            w.writerow([mode, r.get('split', ''), r.get('class', ''), r.get('page', ''),
                        r.get('metric', ''), r.get('value', '')])

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--gold', required=True)
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--coords', required=True)
    ap.add_argument('--lines', required=True)
    ap.add_argument('--out-json', default='')
    ap.add_argument('--out-csv', default='')
    ap.add_argument('--src-pdf', default='')
    ap.add_argument('--book', default='')
    ap.add_argument('--content-gold', default='')
    ap.add_argument('--out', default='')
    ap.add_argument('--mode', default=None, choices=['cell', 'sequence'])
    ap.add_argument('--ab-cell-json', default='')
    args = ap.parse_args(argv)
    mode = args.mode
    if mode is None:
        # 自动判别：gold 是内容转录（有 text 无 class）-> sequence；否则 cell
        try:
            _g = json.load(open(args.gold, encoding='utf-8'))
            _raw = _g if isinstance(_g, list) else _g.get('items', [])
            mode = 'cell' if any('class' in x for x in _raw) else 'sequence'
        except Exception:
            mode = 'cell'
    args.mode_resolved = mode
    if mode == 'sequence':
        return sequence_main(args)
    out_json = args.out_json or args.out
    try:
        gold, items = load_gold(args.gold)
    except Exception as e:
        print('[punct_eval] gold 读取失败: %s' % e, file=sys.stderr); return 2
    try:
        coords, lines = load_coords_lines(args.coords, args.lines)
    except Exception as e:
        print('[punct_eval] coords/lines 读取失败: %s' % e, file=sys.stderr); return 2
    if not os.path.exists(args.pdf):
        print('[punct_eval] PDF 不存在: %s' % args.pdf, file=sys.stderr); return 2
    preds, pages = extract_predictions(coords, lines)
    gold_pages = {it.get('page') for it in items}
    if not gold_pages:
        gold_pages = {p.get('page') for p in preds}
    preds = [p for p in preds if p.get('page') in gold_pages]
    # 旧 gold（v1，4 类）兼容：仅评 v1 类组，避免新增句读/省略号被误计 FP
    if str(gold.get('schema_version') or '') == 'punct-eval-v1':
        old_groups = {'quote', 'bracket', 'dash', 'ring'}
        preds = [p for p in preds if _group(p.get('class')) in old_groups]
    pairs, unmatched, fps = match_items(items, preds)
    by_class, structural = compute_metrics(items, pairs, unmatched, fps)
    tp, fp, fn = len(pairs), len(fps), sum(1 for u in unmatched if u.get('reason') != 'valid_carry_non_final_paragraph')
    overall = dict(tp=tp, fp=fp, fn=fn,
                   position_precision=round(tp / (tp + fp), 4) if tp + fp else 0.0,
                   position_recall=round(tp / (tp + fn), 4) if tp + fn else 0.0,
                   false_insertion_rate=round(fp / (tp + fp), 4) if tp + fp else 0.0,
                   miss_rate=round(fn / (tp + fn), 4) if tp + fn else 0.0)
    ds = gold.get('dataset') or {}
    res = dict(schema_version='punct-eval-v1.1', mode='cell', method='A_cell', dataset_id=ds.get('id', ''),
               gold_sha256=_sha(args.gold), pdf_sha256=_sha(args.pdf),
               split=ds.get('split', ''), book=args.book, overall=overall,
               by_class=by_class, by_gb_class=by_gb(by_class), structural=structural,
               by_page=[], errors=[dict(gold_id=u['gold_id'], reason=u['reason'], page=u['page'],
                                        column=u['column'], char_pos=u['char_pos'], cls=u['cls']) for u in unmatched],
               gate=dict(verdict='unscored', thresholds_version='v1.1', baseline_sha256=''))
    page_stats = {}
    for g, p in pairs:
        page_stats.setdefault(g.get('page'), dict(tp=0, fp=0, fn=0))['tp'] += 1
    for u in unmatched:
        if u.get('reason') == 'valid_carry_non_final_paragraph': continue
        page_stats.setdefault(u['page'], dict(tp=0, fp=0, fn=0))['fn'] += 1
    for p in fps:
        page_stats.setdefault(p['page'], dict(tp=0, fp=0, fn=0))['fp'] += 1
    res['by_page'] = [dict(page=k, **page_stats[k]) for k in sorted(page_stats)]
    if args.content_gold and os.path.exists(args.content_gold):
        try:
            res['content'] = eval_content(json.load(open(args.content_gold, encoding='utf-8')), pages)
        except Exception as e:
            res['content_error'] = str(e)
    csv_rows = []
    split = res['split']
    for cls, st in sorted(by_class.items()):
        for metric in ('tp', 'fp', 'fn', 'precision', 'recall', 'false_insertion_rate', 'miss_rate',
                       'direction_accuracy', 'type_accuracy', 'value_accuracy', 'form_accuracy',
                       'length_median_error', 'length_p95_error'):
            if metric in st:
                csv_rows.append(dict(split=split, **{'class': cls}, page='', metric=metric, value=st[metric]))
    for metric in ('position_precision', 'position_recall', 'false_insertion_rate', 'miss_rate', 'tp', 'fp', 'fn'):
        csv_rows.append(dict(split=split, **{'class': 'overall'}, page='', metric=metric, value=overall[metric]))
    if 'content' in res:
        for metric in ('gold_chars', 'edit_distance', 'cer', 'missing', 'wrong', 'extra', 'doubt_chars'):
            csv_rows.append(dict(split=split, **{'class': 'content'}, page='', metric=metric, value=res['content'][metric]))
    for metric in ('unexpected_close', 'multi_para_groups', 'multi_para_validity'):
        csv_rows.append(dict(split=split, **{'class': 'structural'}, page='', metric=metric, value=structural[metric]))
    if out_json:
        os.makedirs(os.path.dirname(os.path.abspath(out_json)) or '.', exist_ok=True)
        json.dump(res, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if args.out_csv:
        write_csv(args.out_csv, csv_rows, mode='cell')
    print('[punct_eval] items=%d matched=%d fp=%d fn=%d precision=%.3f recall=%.3f' %
          (len(items), tp, fp, fn, overall['position_precision'], overall['position_recall']))
    return 0

if __name__ == '__main__':
    sys.exit(main())


# ===================== v1.3 序列口径（阅读序，无坐标） =====================
SEQ_CANON = {'﹁': '「', '﹂': '」', '﹃': '『', '﹄': '』',
             '︵': '（', '︶': '）', '︹': '〔', '︺': '〕',
             '︽': '《', '︾': '》', '︿': '〈', '﹀': '〉',
             '．': '。', '–': '—', '―': '—', '⋯': '…'}
PAGE_NUM_RE = re.compile(r'^[0-9０-９○〇一二三四五六七八九十百千]+$')
ROMAN_RE = re.compile(r'^[IVXLCDMivxlcdm]{1,6}$')
HEADER_RE = re.compile(r'^(第[0-9０-９一二三四五六七八九十百千]{1,6}[回章节節頁页卷]|卷[0-9０-９一二三四五六七八九十百千]{1,6}|上卷|下卷|目錄|目录)$')


def _seq_norm(t):
    t = unicodedata.normalize('NFC', t or '')
    t = ''.join(t.split())
    return ''.join(SEQ_CANON.get(c, c) for c in t)


def pdf_char_map(pdf_path):
    """产物 PDF 逐页字符+bbox：{page: [(char, (x0,y0,x1,y1))]}（1-based page）。"""
    import fitz
    d = fitz.open(pdf_path)
    out = {}
    for i in range(len(d)):
        chars = []
        for b in d[i].get_text('rawdict').get('blocks', []):
            for l in b.get('lines', []):
                for sp in l.get('spans', []):
                    for c in sp.get('chars', []):
                        chars.append((c['c'], tuple(c['bbox'])))
        out[i + 1] = chars
    return out


def _is_furniture(text):
    """页面家具判定（书无关）：页码/罗马数字/章节页眉模式；长度 ≤6。"""
    t = (text or '').strip()
    if not t or len(t) > 6:
        return False
    if PAGE_NUM_RE.match(t) or ROMAN_RE.match(t):
        return True
    if HEADER_RE.match(t):
        return True
    return False


def reading_order(chars, page_w, page_h, axis='vertical', exclude=None, stats=None):
    """产物 PDF 字符 -> 阅读序文本（§6.4.2）。
    聚类阈值 = max(1.2×中位字高, 0.5×中位 span 高)（本实现 span=单字符 bbox，故 1.2×中位字高）。
    家具剔除：gold exclude 文本；或【短 span（≤6 字）且中心在 8% 页边带内且匹配页码/页眉模式】。
    正文区短列/入带长列不剔除。"""
    if axis not in ('vertical', 'horizontal'):
        return None
    excl = set(exclude or [])
    keep = []
    for c, bb in chars:
        cx = (bb[0] + bb[2]) / 2.0; cy = (bb[1] + bb[3]) / 2.0
        keep.append((c, bb, cx, cy))
    if not keep:
        return ''
    med_w = sorted(max(1e-6, bb[2] - bb[0]) for _, bb, _, _ in keep)[len(keep) // 2]
    med_h = sorted(max(1e-6, bb[3] - bb[1]) for _, bb, _, _ in keep)[len(keep) // 2]
    # §6.4.2 公式：tol = max(1.2×median glyph height, 0.5×median span height)
    # 竖排字形旋转：glyph height 取字符 bbox 宽（沿列方向），span 高取 bbox 高
    glyph_h = med_w if axis == 'vertical' else med_h
    span_h = med_h
    tol = max(1.2 * glyph_h, 0.5 * span_h)
    # 防并列护栏：按本页列心（行心）间距中位估计 pitch，tol 不超过 0.75×pitch
    axis_coords = sorted({round(x[2] if axis == 'vertical' else x[3], 1) for x in keep})
    gaps = [b - a for a, b in zip(axis_coords, axis_coords[1:]) if (b - a) > 5.0]
    if gaps:
        gaps.sort()
        pitch = gaps[len(gaps) // 2]
        tol = min(tol, 0.75 * pitch)
    band_x = (0.08 * page_w, 0.92 * page_w)
    band_y = (0.08 * page_h, 0.92 * page_h)
    excluded_furniture = [0]
    if stats is not None:
        stats.setdefault('excluded_furniture', 0)

    def in_band(cx, cy):
        return cx < band_x[0] or cx > band_x[1] or cy < band_y[0] or cy > band_y[1]

    if axis == 'vertical':
        keep.sort(key=lambda x: (-x[2], x[3]))
        cols = []
        for item in keep:
            if cols and abs(item[2] - cols[-1][0]) <= tol:
                cols[-1][1].append(item)
            else:
                cols.append([item[2], [item]])
        out = []
        for cx, col in cols:
            col.sort(key=lambda x: (x[3], x[2]))
            text = ''.join(c for c, _, _, _ in col)
            if text in excl:
                excluded_furniture[0] += 1; continue
            cy = sum(cy for _, _, _, cy in col) / len(col)
            if in_band(cx, cy) and len(text) <= 6 and _is_furniture(text):
                excluded_furniture[0] += 1; continue
            out.append(text)
        if stats is not None:
            stats['excluded_furniture'] = excluded_furniture[0]
        return ''.join(out)
    else:
        keep.sort(key=lambda x: (x[3], x[2]))
        rows = []
        for item in keep:
            if rows and abs(item[3] - rows[-1][0]) <= tol:
                rows[-1][1].append(item)
            else:
                rows.append([item[3], [item]])
        out = []
        for cy, row in rows:
            row.sort(key=lambda x: x[2])
            text = ''.join(c for c, _, _, _ in row)
            if text in excl:
                excluded_furniture[0] += 1; continue
            cx = sum(cx for _, _, cx, _ in row) / len(row)
            if in_band(cx, cy) and len(text) <= 6 and _is_furniture(text):
                excluded_furniture[0] += 1; continue
            out.append(text)
        if stats is not None:
            stats['excluded_furniture'] = excluded_furniture[0]
        return ''.join(out)


def _class_of(ch):
    if ch in QUOTE_OPEN: return 'quote_open'
    if ch in QUOTE_CLOSE: return 'quote_close'
    if ch in BOOK_OPEN: return 'booktitle_open'
    if ch in BOOK_CLOSE: return 'booktitle_close'
    if ch in BRACKET_OPEN or ch in BRACKET_CLOSE: return 'bracket_present'
    if ch in DASH_CHARS: return 'dash'
    if ch in ELLIPSIS_CHARS: return 'ellipsis'
    if ch in SENTENCE: return SENTENCE[ch]
    if _ring_number(ch) is not None: return 'ring'
    return None


def seq_tokens(text):
    """文本 -> (anchors, tokens)：anchors=非标点字符；tokens=[(gap, class, value, order, extra)]。"""
    anchors = []
    tokens = []
    gap = 0
    i = 0
    while i < len(text):
        ch = text[i]
        cls = _class_of(ch)
        if cls is None:
            anchors.append(ch); gap += 1; i += 1; continue
        if cls == 'dash' or cls == 'ellipsis':
            j = i
            while j < len(text) and _class_of(text[j]) == cls:
                j += 1
            tokens.append((gap, cls, text[i:j], len(tokens), {}))
            i = j
            continue
        extra = {}
        if cls == 'bracket_present':
            btype = BRACKET_KIND.get(ch, '〔〕')
            extra['btype'] = btype
        tokens.append((gap, cls, ch, len(tokens), extra))
        i += 1
    return ''.join(anchors), tokens


def _group(cls):
    if cls in ('quote_open', 'quote_close'): return 'quote'
    if cls in ('booktitle_open', 'booktitle_close'): return 'booktitle'
    if cls == 'bracket_present': return 'bracket'
    return cls


def _seq_group(cls):
    if cls in SENTENCE.values():
        return 'sentence'
    return _group(cls)


def _transpositions(pairs):
    """pairs: [(gold_order, pred_order)]；返回逆序对数（顺序错位）。"""
    n = len(pairs)
    cnt = 0
    for i in range(n):
        for j in range(i + 1, n):
            if pairs[i][1] > pairs[j][1]:
                cnt += 1
    return cnt


def sequence_eval(gold_text, pred_text):
    """阅读序序列评测（无坐标）：锚点对齐 + 标点 gap 配对。返回 dict。"""
    g = _seq_norm(gold_text)
    p = _seq_norm(pred_text)
    g_anchor, g_tokens = seq_tokens(g)
    p_anchor, p_tokens = seq_tokens(p)
    sm = difflib.SequenceMatcher(None, g_anchor, p_anchor, autojunk=False)
    gap_map = {}
    blocks = sm.get_matching_blocks()
    for bl in blocks:
        for k in range(bl.size):
            gap_map[bl.a + k] = bl.b + k
    # 匹配块到达串尾：补 len(g_anchor)->len(p_anchor)，让串尾标点也能配对
    if blocks and blocks[-1].a + blocks[-1].size == len(g_anchor) and blocks[-1].b + blocks[-1].size == len(p_anchor):
        gap_map[len(g_anchor)] = len(p_anchor)
    used = set(); pairs = []; per = {}; confusion = {}; gap_tol = 0; gap_tol_pairs = []
    def bump(cls):
        return per.setdefault(cls, dict(tp=0, fp=0, fn=0, value_ok=0, value_total=0, type_ok=0, type_total=0))
    for gap, cls, value, order, extra in g_tokens:
        bump(cls)
        g2 = gap_map.get(gap)
        cands = []
        if g2 is not None:
            cands = [pt for pt in p_tokens if pt[0] == g2 and id(pt) not in used]
        hit = None
        for cand in cands:
            if cand[1] == cls:
                hit = cand; break
        if hit is None:
            for cand in cands:
                if _seq_group(cand[1]) == _seq_group(cls):
                    confusion[(cls, cand[1])] = confusion.get((cls, cand[1]), 0) + 1
                    hit = cand; break
        # t263：同 gap 无可用候选时，允许 ±1 gap（仅当同 gap 完全无候选）
        if hit is None and g2 is not None:
            for _d in (-1, 1):
                _cands = [pt for pt in p_tokens if pt[0] == g2 + _d and id(pt) not in used]
                hit = next((x for x in _cands if x[1] == cls), None)
                if hit is None:
                    hit = next((x for x in _cands if _seq_group(x[1]) == _seq_group(cls)), None)
                if hit is not None:
                    gap_tol += 1
                    gap_tol_pairs.append(dict(gold_gap=gap, gold_cls=cls, pred_gap=hit[0], pred_cls=hit[1]))
                    break
        if hit is not None:
            used.add(id(hit))
            pairs.append((order, hit[3]))
            if hit[1] == cls:
                per[cls]['tp'] += 1
            else:
                # 类型错：只给 pred 类 1 FP、gold 类 1 FN（gold 类不再计 FP）
                bump(hit[1])['fp'] += 1
                per[cls]['fn'] += 1
            # value / type 诊断
            if cls in SENTENCE.values() or cls == 'ring':
                per[cls]['value_total'] += 1
                if str(hit[2]) == str(value):
                    per[cls]['value_ok'] += 1
            if cls == 'bracket_present' and hit[4].get('btype'):
                per[cls]['type_total'] += 1
                if hit[4]['btype'] == extra.get('btype'):
                    per[cls]['type_ok'] += 1
        else:
            per[cls]['fn'] += 1
    for pt in p_tokens:
        if id(pt) in used: continue
        bump(pt[1])['fp'] += 1
    for cls, st in per.items():
        tp, fp, fn = st['tp'], st['fp'], st['fn']
        st['precision'] = round(tp / (tp + fp), 4) if tp + fp else 0.0
        st['recall'] = round(tp / (tp + fn), 4) if tp + fn else 0.0
        if st['value_total']:
            st['value_accuracy'] = round(st['value_ok'] / st['value_total'], 4)
        if st['type_total']:
            st['type_accuracy'] = round(st['type_ok'] / st['type_total'], 4)
    tp = sum(st['tp'] for st in per.values()); fp = sum(st['fp'] for st in per.values())
    fn = sum(st['fn'] for st in per.values())
    return dict(per_class=per,
                overall=dict(tp=tp, fp=fp, fn=fn,
                             precision=round(tp / (tp + fp), 4) if tp + fp else 0.0,
                             recall=round(tp / (tp + fn), 4) if tp + fn else 0.0),
                confusion={'%s>%s' % k: v for k, v in confusion.items()},
                order_swaps=_transpositions(pairs),
                n_pairs=len(pairs), gap_tolerance=gap_tol, gap_tolerance_pairs=gap_tol_pairs)


def sequence_main(args):
    import fitz
    gold_items = load_content_gold(args.gold, args.book)
    out = dict(schema_version='punct-eval-v1.3', mode='sequence', method='B_sequence',
               dataset_id='punct-eval-b-20p', gold_source='content_gold(t111/provisional)',
               normalization='content-N0', book=args.book,
               gold_sha256=_sha(args.gold), pdf_sha256=_sha(args.pdf),
               pages=[], by_page=[], unscorable_pages=[],
               per_class={}, by_class={}, overall=dict(tp=0, fp=0, fn=0),
               confusion={}, order_swaps=0,
               order_swaps_definition='同 gap 多 tokens 按序列配对并计逆序；跨 gap 由单调 gap map 保证非逆序（恒 0）',
               reading_order={'pages': 0, 'unscorable': 0, 'excluded_furniture': 0},
               gap_tolerance=0, gap_tolerance_pairs=[],
               gate=dict(status='provisional', thresholds_version='v1.2', auto_enabled=False),
               errors=[])
    try:
        d = fitz.open(args.pdf)
        dims = {i + 1: (d[i].rect.width, d[i].rect.height) for i in range(len(d))}
    except Exception as e:
        print('[punct_eval] PDF 读取失败: %s' % e, file=sys.stderr); return 3
    chars = pdf_char_map(args.pdf)
    agg = {}
    for it in gold_items:
        page = int(it['page']); axis = it.get('axis') or 'vertical'
        w, h = dims.get(page, (0, 0))
        stats = {}
        pred = reading_order(chars.get(page, []), w, h, axis, it.get('exclude'), stats)
        out['reading_order']['excluded_furniture'] += stats.get('excluded_furniture', 0)
        if pred is None:
            out['unscorable_pages'].append(dict(page=page, reason='reading_order_unscorable', axis=axis))
            out['errors'].append(dict(page=page, kind='reading_order', detail='axis=%s' % axis))
            continue
        r = sequence_eval(it.get('text') or '', pred)
        out['by_page'].append(dict(page=page, axis=axis, reading_order='ok', **r['overall'], order_swaps=r['order_swaps']))
        for cls, st in r['per_class'].items():
            tgt = agg.setdefault(cls, dict(tp=0, fp=0, fn=0, value_ok=0, value_total=0, type_ok=0, type_total=0))
            for k in ('tp', 'fp', 'fn'):
                tgt[k] += st[k]
            for k in ('value_ok', 'value_total', 'type_ok', 'type_total'):
                if k in st: tgt[k] += st[k]
        for k, v in r['confusion'].items():
            out['confusion'][k] = out['confusion'].get(k, 0) + v
        out['order_swaps'] += r['order_swaps']
        out['gap_tolerance'] += r.get('gap_tolerance', 0)
        _gtp = r.get('gap_tolerance_pairs', [])
        for _p in _gtp: _p = _p.setdefault('page', page) if isinstance(_p, dict) else None
        out['gap_tolerance_pairs'] += _gtp
    for cls, st in agg.items():
        tp, fp, fn = st['tp'], st['fp'], st['fn']
        st['precision'] = round(tp / (tp + fp), 4) if tp + fp else 0.0
        st['recall'] = round(tp / (tp + fn), 4) if tp + fn else 0.0
        if st['value_total']: st['value_accuracy'] = round(st['value_ok'] / st['value_total'], 4)
        if st['type_total']: st['type_accuracy'] = round(st['type_ok'] / st['type_total'], 4)
    out['per_class'] = agg
    out['by_class'] = agg
    out['reading_order']['pages'] = len(out['by_page'])
    out['reading_order']['unscorable'] = len(out['unscorable_pages'])
    # A/B 差异（|B-A|>5pp）：cell 结果可选；无论是否提供都声明页集差异
    cell_path = args.ab_cell_json or 'tmp_vert/bench/cell_v51.json'
    ab = dict(cell_json=(cell_path if os.path.exists(cell_path) else None), page_sets_differ=True,
              note='A=36 条 demo punct gold（3 页）；B=8 页 wz7 content gold；页集不同，逐类差仅参考',
              by_class={}, gt5pp=[])
    if not os.path.exists(cell_path):
        ab['note'] += '；默认 cell_v51.json 不存在，A 对照未加载（可用 --ab-cell-json 指定）'
    if os.path.exists(cell_path):
        try:
            cell = json.load(open(cell_path, encoding='utf-8'))
            cb = cell.get('by_class') or {}
            for cls, st in agg.items():
                c = cb.get(cls) or {}
                for m in ('precision', 'recall'):
                    if m in c and m in st:
                        d = round(st[m] - c[m], 4)
                        ab['by_class'][cls] = d
                        if abs(d) > 0.05:
                            ab['gt5pp'].append(dict(**{'class': cls}, metric=m, cell=c[m], seq=st[m],
                                                    delta=d, diff_pp=round(d * 100, 2),
                                                    causes=['page_set_diff']))
        except Exception as e:
            ab['error'] = str(e)
    out['ab_diff'] = ab
    out['overall'] = dict(tp=sum(s['tp'] for s in agg.values()), fp=sum(s['fp'] for s in agg.values()),
                          fn=sum(s['fn'] for s in agg.values()))
    if out['overall']['tp'] + out['overall']['fp']:
        out['overall']['precision'] = round(out['overall']['tp'] / (out['overall']['tp'] + out['overall']['fp']), 4)
    if out['overall']['tp'] + out['overall']['fn']:
        out['overall']['recall'] = round(out['overall']['tp'] / (out['overall']['tp'] + out['overall']['fn']), 4)
    if args.out or args.out_json:
        p = args.out_json or args.out
        os.makedirs(os.path.dirname(os.path.abspath(p)) or '.', exist_ok=True)
        json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if args.out_csv:
        rows = []
        for cls, st in sorted(out['per_class'].items()):
            for m in ('tp', 'fp', 'fn', 'precision', 'recall', 'value_accuracy', 'type_accuracy'):
                if m in st:
                    rows.append(dict(mode='sequence', cls=cls, page='', metric=m, value=st[m]))
        for m in ('tp', 'fp', 'fn', 'precision', 'recall'):
            if m in out['overall']:
                rows.append(dict(mode='sequence', cls='overall', page='', metric=m, value=out['overall'][m]))
        write_csv(args.out_csv, rows, mode='sequence')
    print('[punct_eval:sequence] pages=%d unscorable=%d tp=%d fp=%d fn=%d P=%.3f R=%.3f swaps=%d' %
          (len(out['by_page']), len(out['unscorable_pages']), out['overall']['tp'], out['overall']['fp'],
           out['overall']['fn'], out['overall'].get('precision', 0), out['overall'].get('recall', 0),
           out['order_swaps']))
    return 0


def load_content_gold(path, book=None):
    d = json.load(open(path, encoding='utf-8'))
    raw = d if isinstance(d, list) else (d.get('items') if isinstance(d, dict) and 'items' in d else [])
    items = []
    for x in raw:
        if book and x.get('book') and str(x['book']) != str(book):
            continue
        if 'text' not in x:
            continue
        items.append(x)
    return items
