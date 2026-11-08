#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""content_eval：内容 CER 两栏（with_punct / han_only）+ 回归 must-pass（PDF 口径）。

依据 spec/governance/CONTENT_EVAL.md：
- N0: NFC、去空白、不繁简/异体；`?` 同位置屏蔽（gold 删 ?，pred 同序位删一字）；
- CER = (I+D+S)/N（Levenshtein 1/1/1），N=0 → null；
- must-pass = 64 条 missing_char(shape+complete) + 54 条 battle4 ring_fix（读产物 PDF 字符+坐标）；
- t97 4/118 只诊断（i=26 假项剔除）。
只读评测；不联网/不调 API；不改产物。
"""
import argparse, csv, hashlib, json, os, re, sys, unicodedata

VARIANT = {'爲': '為', '裏': '裡', '綉': '繡', '毬': '球', '徧': '遍', '儘': '盡',
           '纔': '才', '於': '于', '麼': '么', '盃': '杯', '喫': '吃', '牠': '它',
           '卽': '即', '旣': '既', '衆': '眾', '敎': '教', '眞': '真', '菴': '庵',
           '竝': '並', '迺': '乃', '筭': '算', '緫': '總', '虗': '虛', '隣': '鄰'}
CJK = re.compile('[\u3400-\u9fff\uf900-\ufaff]')
# 竖排形归一（诊断用，不计入 N0 主列）：竖排引号/括号/书名号/句读形 -> 横排对应形
VERTICAL_FORM = {'﹁': '「', '﹂': '」', '﹃': '『', '﹄': '』',
                 '︵': '（', '︶': '）', '︹': '〔', '︺': '〕',
                 '︽': '《', '︾': '》', '︿': '〈', '﹀': '〉',
                 '．': '。', '–': '—', '―': '—', '⋯': '…'}


def _sha_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def _sha_file(path):
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''):
                h.update(b)
        return h.hexdigest()
    except OSError:
        return ''


def normalize(text, mode='none'):
    t = unicodedata.normalize('NFC', text or '')
    t = ''.join(t.split())
    if mode == 'variant':
        t = ''.join(VARIANT.get(c, c) for c in t)
    elif mode == 'simp':
        try:
            import opencc
            t = opencc.OpenCC('t2s').convert(t)
        except Exception:
            t = ''.join(VARIANT.get(c, c) for c in t)
    return t


def han_only(t):
    return ''.join(c for c in t if CJK.match(c))


def vertical_form(t):
    return ''.join(VERTICAL_FORM.get(c, c) for c in t)


def _edit_ops(gold, pred):
    """确定性 Levenshtein 对齐，返回 (I, D, S, dist)。替换成本 1/1/1。"""
    la, lb = len(gold), len(pred)
    prev = [(j, 0, j, 0) for j in range(lb + 1)]  # (dist, I, D, S)
    for i in range(1, la + 1):
        cur = [(i, 0, i, 0)] + [None] * lb
        for j in range(1, lb + 1):
            if gold[i - 1] == pred[j - 1]:
                best = prev[j - 1]; cur[j] = best
                continue
            cand = []
            d, i_, dd, s = prev[j - 1]; cand.append((d + 1, i_, dd, s + 1))  # substitute
            d, i_, dd, s = prev[j]; cand.append((d + 1, i_, dd + 1, s))      # delete gold
            d, i_, dd, s = cur[j - 1]; cand.append((d + 1, i_ + 1, dd, s))  # insert pred
            cur[j] = min(cand, key=lambda x: (x[0], x[3], x[2], x[1]))
        prev = cur
    dist, ins, dele, sub = prev[lb]
    return ins, dele, sub, dist


def _apply_doubt_mask(gold, pred):
    """N0 §3.1-5：gold 的 ? 删除；pred 按 gold 中 ? 的**原序位**删除（其他字符保留，不截断）。"""
    drop = {i for i, c in enumerate(gold) if c == '?'}
    if not drop:
        return gold, pred, 0
    g2 = ''.join(c for c in gold if c != '?')
    p2 = ''.join(c for k, c in enumerate(pred) if k not in drop)
    return g2, p2, len(drop)


def pdf_chars(pdf_path):
    import fitz
    d = fitz.open(pdf_path)
    out = {}
    for i in range(len(d)):
        chars = []
        raw = d[i].get_text('rawdict')
        for b in raw.get('blocks', []):
            for l in b.get('lines', []):
                for sp in l.get('spans', []):
                    for c in sp.get('chars', []):
                            chars.append((c['c'], tuple(c['bbox'])))
        out[i + 1] = chars
    return out


def pdf_pages_text(chars_map):
    return {p: ''.join(c for c, _ in cs if not c.isspace()) for p, cs in chars_map.items()}


def load_lines(coords_path, lines_path):
    return json.load(open(coords_path, encoding='utf-8')), json.load(open(lines_path, encoding='utf-8'))


def load_gold(path, book=None):
    d = json.load(open(path, encoding='utf-8'))
    if isinstance(d, list):
        raw = d
    elif isinstance(d, dict) and 'items' in d:
        raw = d['items']
    elif isinstance(d, dict):
        raw = [dict(page=int(k), text=v) for k, v in d.items()]
    else:
        raise ValueError('gold 格式不支持: %s' % type(d))
    items = []
    for x in raw:
        if book and x.get('book') and str(x['book']) != str(book):
            continue
        items.append(dict(page=int(x['page']), text=x.get('text') or '',
                          exclude=x.get('exclude') or [], book=x.get('book'), split=x.get('split')))
    return d, items


def content_metrics(gold_items, pages, normalize_mode='none'):
    rows = []
    tot = {m: dict(gold=0, dist=0, ins=0, dele=0, sub=0) for m in ('with_punct', 'han_only')}
    vtot = {m: dict(gold=0, dist=0) for m in ('with_punct', 'han_only')}
    doubt = 0
    for it in sorted(gold_items, key=lambda x: x['page']):
        page = it['page']
        pred_raw = pages.get(page)
        if pred_raw is None:
            return None, None, dict(error='page %d 缺失于产物 PDF' % page)
        gold_raw = normalize(it.get('text') or '', 'none')
        pred_raw = normalize(pred_raw, 'none')
        gold_masked, pred_masked, dn = _apply_doubt_mask(gold_raw, pred_raw)
        doubt += dn
        rec = dict(page=page)
        # 竖排形归一诊断（不改变 N0 主列）
        gv = vertical_form(gold_masked); pv = vertical_form(pred_masked)
        gvh = han_only(vertical_form(gold_masked)); pvh = han_only(vertical_form(pred_masked))
        if gv:
            i2, d2, s2, dist2 = _edit_ops(gv, pv)
            rec['normalized_vertical'] = dict(cer=round(dist2 / len(gv), 4), edit_distance=dist2,
                                               gold_chars=len(gv))
            vtot['with_punct']['gold'] += len(gv); vtot['with_punct']['dist'] += dist2
            if gvh:
                i3, d3, s3, dist3 = _edit_ops(gvh, pvh)
                vtot['han_only']['gold'] += len(gvh); vtot['han_only']['dist'] += dist3
        else:
            rec['normalized_vertical'] = dict(cer=None, edit_distance=0, gold_chars=0)
        for col, gf, pf in (('with_punct', gold_masked, pred_masked),
                            ('han_only', han_only(gold_masked), han_only(pred_masked))):
            if not gf:
                rec[col] = dict(gold_chars=0, pred_chars=len(pf), insertions=0, deletions=0,
                                substitutions=0, edit_distance=0, cer=None, missing=0, wrong=0,
                                extra=0, insertion_rate=None, deletion_rate=None,
                                substitution_rate=None, missing_rate=None, wrong_rate=None,
                                extra_rate=None, cer_note='N=0')
                continue
            ins, dele, sub, dist = _edit_ops(gf, pf)
            rec[col] = dict(gold_chars=len(gf), pred_chars=len(pf), insertions=ins, deletions=dele,
                            substitutions=sub, edit_distance=dist,
                            cer=round(dist / len(gf), 4),
                            missing=dele, wrong=sub, extra=ins,
                            missing_rate=round(dele / len(gf), 4),
                            wrong_rate=round(sub / len(gf), 4),
                            extra_rate=round(ins / len(gf), 4))
            for k, v in (('gold', len(gf)), ('dist', dist), ('ins', ins), ('dele', dele), ('sub', sub)):
                tot[col][k] += v
        # 异体/繁简归一对照（仅诊断，不计分）
        for mode in ('variant', 'simp'):
            gv = normalize(it.get('text') or '', mode)
            pv = normalize(pred_raw, mode)
            gv, pv, _ = _apply_doubt_mask(gv, pv)
            if gv:
                i2, d2, s2, dist2 = _edit_ops(gv, pv)
                rec['normalized_' + mode] = dict(cer=round(dist2 / len(gv), 4), edit_distance=dist2,
                                                 gold_chars=len(gv))
            else:
                rec['normalized_' + mode] = dict(cer=None, edit_distance=0, gold_chars=0)
        rows.append(rec)
    overall = {}
    for col in ('with_punct', 'han_only'):
        x = tot[col]
        if not x['gold']:
            overall[col] = dict(gold_chars=0, edit_distance=0, cer=None, insertions=0, deletions=0,
                                substitutions=0, missing=0, wrong=0, extra=0,
                                insertion_rate=None, deletion_rate=None, substitution_rate=None,
                                missing_rate=None, wrong_rate=None, extra_rate=None, cer_note='N=0')
            continue
        overall[col] = dict(gold_chars=x['gold'], edit_distance=x['dist'],
                            cer=round(x['dist'] / x['gold'], 4),
                            insertions=x['ins'], deletions=x['dele'], substitutions=x['sub'],
                            missing=x['dele'], wrong=x['sub'], extra=x['ins'],
                            insertion_rate=round(x['ins'] / x['gold'], 4),
                            deletion_rate=round(x['dele'] / x['gold'], 4),
                            substitution_rate=round(x['sub'] / x['gold'], 4),
                            missing_rate=round(x['dele'] / x['gold'], 4),
                            wrong_rate=round(x['sub'] / x['gold'], 4),
                            extra_rate=round(x['ins'] / x['gold'], 4))
    vertical = {}
    for col in ('with_punct', 'han_only'):
        x = vtot[col]
        vertical[col] = dict(gold_chars=x['gold'], edit_distance=x['dist'],
                             cer=round(x['dist'] / x['gold'], 4) if x['gold'] else None)
    return overall, rows, dict(doubt_chars=doubt, vertical_form=vertical)


def _ring_candidates(number, cp):
    cands = set()
    if cp.startswith('U+'):
        try: cands.add(chr(int(cp[2:], 16)))
        except Exception: pass
    n = int(number) if number else 0
    if 1 <= n <= 20: cands.add(chr(0x2460 + n - 1))
    elif 21 <= n <= 35: cands.add(chr(0x3251 + n - 21))
    elif 36 <= n <= 50: cands.add(chr(0x32B1 + n - 36))
    return cands


def _near(chars, ch, x, y, tol=20.0):
    if x is None or y is None: return False
    for c, bb in chars:
        cx = (bb[0] + bb[2]) / 2.0; cy = (bb[1] + bb[3]) / 2.0
        if c == ch and abs(cx - x) <= tol and abs(cy - y) <= tol:
            return True
    return False


def _near_ring(chars, number, cp, x, y, tol=20.0):
    target = _ring_candidates(number, cp)
    if x is not None and y is not None:
        for c, bb in chars:
            cx = (bb[0] + bb[2]) / 2.0; cy = (bb[1] + bb[3]) / 2.0
            if abs(cx - x) <= tol and abs(cy - y) <= tol and c in target:
                return c
    text = ''.join(c for c, _ in chars if not c.isspace())
    norm = text.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    if number:
        if re.search('○\\s*' + str(number) + '(?![0-9])', norm):
            return '○' + str(number)
    for c in target:
        if c and c in text: return c
    return ''


def _col_expected_pos(col, pos, row_text):
    """由 fix JSON 的列框（PDF pt）+ 行内 pos 反推期望字符中心（列 x 中心，y0+pos*step）。"""
    if not col or len(col) != 4:
        return None, None
    step = (col[3] - col[1]) / max(1, len(row_text))
    return (col[0] + col[2]) / 2.0, col[1] + (pos + 0.5) * step

def regression_must_pass(fix_path, pdf_chars_map, coords=None, lines=None):
    texts = pdf_pages_text(pdf_chars_map)
    d = json.load(open(fix_path, encoding='utf-8'))
    items = d.get('items') or []
    mc = [x for x in items if x.get('class') == 'missing_char' and 'shape' in x and 'complete' in x]
    ring = [x for x in items if str(x.get('ring_fix') or '').startswith('battle4:')]
    # ring 标定：用页级已知圈号字符位置 vs source_x/y 的中位 offset（逐书；v51 仅 wz7）
    offs = []
    for it in ring:
        page = int(it['page']); cp = it.get('cp') or ''
        if it.get('source_x') is None: continue
        cands = _ring_candidates(it.get('number'), cp)
        for c, bb in pdf_chars_map.get(page, []):
            if c in cands:
                offs.append(((bb[0] + bb[2]) / 2.0 - it['source_x'],
                             (bb[1] + bb[3]) / 2.0 - it.get('source_y')))
                break
    dx = sorted(o[0] for o in offs)[len(offs) // 2] if offs else 0.0
    dy = sorted(o[1] for o in offs)[len(offs) // 2] if offs else 0.0
    mc_out = []
    for it in mc:
        page = int(it['page']); ch = it.get('ch') or ''
        text = texts.get(page, '')
        # 期望位置：fix JSON 的 col（PDF pt）+ pos；行文本长度取 lines/coords 反查，退用页文本
        row_text = ''
        try:
            colbox = it.get('col')
            for ri, pts in enumerate((coords or {}).get(str(page - 1)) or []):
                xs = [q[0] / 2 for q in pts]; ys = [q[1] / 2 for q in pts]
                bx = (min(xs), min(ys), max(xs), max(ys))
                if colbox and all(abs(a - c) <= 0.8 for a, c in zip(bx, colbox)):
                    rows = (lines or {}).get(str(page - 1)) or []
                    row_text = str(rows[ri]) if ri < len(rows) else ''
                    break
        except Exception:
            row_text = ''
        if not row_text:
            row_text = text
        ex, ey = _col_expected_pos(it.get('col'), int(it.get('pos') or 0), row_text)
        pos_hit = bool(ex is not None and _near(pdf_chars_map.get(page, []), ch, ex, ey))
        fb_hit = bool(ch) and ch in text
        ok = pos_hit or fb_hit
        mc_out.append(dict(page=page, pos=it.get('pos'), ch=ch, ok=ok,
                           position_hit=pos_hit, fallback_hit=(not pos_hit and fb_hit),
                           expected_xy=[round(ex, 1), round(ey, 1)] if ex is not None else None,
                           reason='' if ok else 'expected_char_missing'))
    ring_out = []
    for it in ring:
        page = int(it['page']); cp = it.get('cp') or ''
        cal_x = (it.get('source_x') + dx) if it.get('source_x') is not None else None
        cal_y = (it.get('source_y') + dy) if it.get('source_y') is not None else None
        pos_hit = bool(_near_ring(pdf_chars_map.get(page, []), it.get('number'), cp, cal_x, cal_y))
        fb_hit = bool(_near_ring(pdf_chars_map.get(page, []), it.get('number'), cp, None, None))
        ok = pos_hit or fb_hit
        ring_out.append(dict(page=page, pos=it.get('pos'), number=it.get('number'), cp=cp, ok=ok,
                             position_hit=pos_hit, fallback_hit=(not pos_hit and fb_hit),
                             reason='' if ok else 'ring_missing'))
    p1 = sum(1 for x in mc_out if x['ok']); p2 = sum(1 for x in ring_out if x['ok'])
    return dict(missing_char_confirmed=dict(
                    total=len(mc_out), passed=p1,
                    position_hits=sum(1 for x in mc_out if x['position_hit']),
                    fallback_hits=sum(1 for x in mc_out if x['fallback_hit']),
                    rate=round(p1 / len(mc_out), 4) if mc_out else None, items=mc_out),
                battle4_ring=dict(
                    total=len(ring_out), passed=p2,
                    position_hits=sum(1 for x in ring_out if x['position_hit']),
                    fallback_hits=sum(1 for x in ring_out if x['fallback_hit']),
                    calibration_offset=[round(dx, 2), round(dy, 2)], n_offset_samples=len(offs),
                    rate=round(p2 / len(ring_out), 4) if ring_out else None, items=ring_out),
                must_pass=(len(mc_out) == p1 == 64 and len(ring_out) == p2 == 54))

def regression_diagnostics(fix_path, pdf_chars_map, coords, meta_path):
    texts = pdf_pages_text(pdf_chars_map)
    d = json.load(open(fix_path, encoding='utf-8'))
    mcall = [x for x in (d.get('items') or []) if x.get('class') == 'missing_char']
    rows = []
    for it in mcall:
        page = int(it['page']); ch = it.get('ch') or ''
        ok = _near(pdf_chars_map.get(page, []), ch, it.get('source_x'), it.get('source_y')) \
            or (bool(ch) and ch in texts.get(page, ''))
        rows.append(dict(page=page, ch=ch, ok=ok))
    p = sum(1 for x in rows if x['ok'])
    t97 = dict(status='unmaterialized', count=118)
    try:
        meta = json.load(open(meta_path, encoding='utf-8'))
        ids = {1, 15, 36}   # i=26 已确认为假项
        items = []
        for x in meta:
            if x.get('i') not in ids: continue
            page = int(x['page']); expected = x.get('a') or ''
            row = int(x.get('row') or 0)
            ok = False
            try:
                pts = (coords.get(str(page - 1)) or [])[row]
                xs = [q[0] / 2 for q in pts]; ys = [q[1] / 2 for q in pts]
                bx = (min(xs), min(ys), max(xs), max(ys))
                inside = ''.join(c for c, bb in pdf_chars_map.get(page, [])
                                 if bx[0] - 2 <= (bb[0] + bb[2]) / 2 <= bx[2] + 2
                                 and bx[1] - 2 <= (bb[1] + bb[3]) / 2 <= bx[3] + 2)
                ok = bool(expected) and expected in inside
            except Exception:
                ok = False
            items.append(dict(i=x.get('i'), page=page, expected=expected, ok=ok))
        p2 = sum(1 for r in items if r['ok'])
        t97.update(materialized_total=len(items), materialized_passed=p2,
                   materialized_rate=round(p2 / len(items), 4) if items else None, items=items)
    except Exception as e:
        t97['error'] = str(e)
    return dict(missing_char_all=dict(total=len(rows), passed=p, rate=round(p / len(rows), 4) if rows else None),
                typo_t97=t97)


def write_csv(path, rows):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(['book', 'page', 'metric', 'value'])
        for r in rows:
            w.writerow([r.get('book', ''), r.get('page', ''), r.get('metric', ''), r.get('value', '')])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--gold', required=True)
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--coords', required=True)
    ap.add_argument('--lines', required=True)
    ap.add_argument('--book', default='')
    ap.add_argument('--normalize', default='none', choices=['none', 'variant', 'simp'])
    ap.add_argument('--out', default='')
    ap.add_argument('--out-csv', default='')
    ap.add_argument('--regression-fix', default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'docs/vert_taskF_missed_fix.json'))
    ap.add_argument('--t97-meta', default='tmp_vert/battle21b/char_sample_meta.json')
    args = ap.parse_args(argv)
    if not os.path.exists(args.pdf):
        print('[content_eval] PDF 不存在: %s' % args.pdf, file=sys.stderr); return 2
    try:
        gold_doc, gold_items = load_gold(args.gold, args.book)
    except Exception as e:
        print('[content_eval] gold 读取失败: %s' % e, file=sys.stderr); return 2
    try:
        coords, lines = load_lines(args.coords, args.lines)
    except Exception as e:
        print('[content_eval] coords/lines 读取失败: %s' % e, file=sys.stderr); return 2
    try:
        chars_map = pdf_chars(args.pdf)
    except Exception as e:
        print('[content_eval] 产物 PDF 解析失败: %s' % e, file=sys.stderr); return 3
    pages = pdf_pages_text(chars_map)
    if not pages or not any(pages.values()):
        print('[content_eval] 产物 PDF 无文本（unscored，不得回退 lines）', file=sys.stderr); return 3
    overall, rows, extra = content_metrics(gold_items, pages, args.normalize)
    if overall is None:
        print('[content_eval] %s' % extra.get('error'), file=sys.stderr); return 3
    reg = regression_must_pass(args.regression_fix, chars_map, coords, lines) if os.path.exists(args.regression_fix) else None
    diag = regression_diagnostics(args.regression_fix, chars_map, coords, args.t97_meta) if os.path.exists(args.regression_fix) else None
    norm_audit = dict(normalization_id='N0_default', unicode_version=unicodedata.unidata_version,
                      strip_whitespace=True, variant_map=None, t2s=False, doubt_mask='same_cell',
                      gold_normalized_sha256=_sha_text(''.join(normalize(it.get('text') or '') for it in gold_items)),
                      pred_normalized_sha256=_sha_text(''.join(pages.get(it['page'], '') for it in gold_items)))
    res = dict(schema_version='content-eval-v1.1', book=args.book,
               gold_sha256=_sha_file(args.gold), pdf_sha256=_sha_file(args.pdf),
               normalize=args.normalize, normalization_audit=norm_audit,
               content=dict(overall=overall, by_page=rows, doubt_chars=extra['doubt_chars'],
                            vertical_form=extra.get('vertical_form')),
               regression=dict(must_pass_items=reg, must_pass=bool(reg and reg['must_pass'])),
               gate=dict(missing_ok=bool(reg and reg['missing_char_confirmed']['total'] == reg['missing_char_confirmed']['passed']),
                         ring_ok=bool(reg and reg['battle4_ring']['total'] == reg['battle4_ring']['passed']),
                         verdict=('CONTENT_AUTO_PASS' if reg and reg['must_pass'] else 'REGRESSION_BLOCKED'),
                         by_split={'wz7': {'must_pass': bool(reg and reg['must_pass'])}}),
               diagnostics=diag)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or '.', exist_ok=True)
        json.dump(res, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if args.out_csv:
        csv_rows = []
        for col in ('with_punct', 'han_only'):
            for m in ('gold_chars', 'edit_distance', 'cer', 'insertions', 'deletions', 'substitutions',
                      'missing', 'wrong', 'extra', 'insertion_rate', 'deletion_rate', 'substitution_rate'):
                csv_rows.append(dict(book=args.book, page='', metric='%s.%s' % (col, m), value=overall[col][m]))
        for r in rows:
            for col in ('with_punct', 'han_only'):
                csv_rows.append(dict(book=args.book, page=r['page'], metric=col + '.cer', value=r[col]['cer']))
        if reg:
            csv_rows.append(dict(book=args.book, page='', metric='regression.missing_char_confirmed.rate',
                                 value=reg['missing_char_confirmed']['rate']))
            csv_rows.append(dict(book=args.book, page='', metric='regression.battle4_ring.rate',
                                 value=reg['battle4_ring']['rate']))
            csv_rows.append(dict(book=args.book, page='', metric='regression.must_pass', value=reg['must_pass']))
        write_csv(args.out_csv, csv_rows)
    mc = (reg or {}).get('missing_char_confirmed', {}); rr = (reg or {}).get('battle4_ring', {})
    print('[content_eval] with_punct CER=%.4f han_only CER=%.4f | must-pass %s/%s + %s/%s => %s' %
          (overall['with_punct']['cer'] if overall['with_punct']['cer'] is not None else -1,
           overall['han_only']['cer'] if overall['han_only']['cer'] is not None else -1,
           mc.get('passed', '-'), mc.get('total', '-'), rr.get('passed', '-'), rr.get('total', '-'),
           (reg or {}).get('must_pass', '-')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
