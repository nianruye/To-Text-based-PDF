#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quality_gate.py — 统一质量门禁 v1（PUNCT_EVAL §5.2/§6.4.5 + CONTENT_EVAL §6.2/§6.3）。

输入：verify_vert（页数/字符量/越界）+ punct_eval（序列口径 B，cell 口径 A 可选）+ content_eval（两栏 CER + must-pass）。
输出：JSON（分项指标 + 判定 + 失败明细 top-N）与 markdown 摘要；三档 AUTO_PASS / MANUAL_ONLY / REJECT。
阈值全部来自 spec（书无关），wz6/wz7 同一套；不改 verify_vert.py / punct_eval.py 判据；只读评测。
"""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'tools'))

# ---- 阈值（spec 锚点；不得书专属）----
PUNCT_TIERS = {
    'sentence': dict(auto=(0.98, 0.96), manual=(0.92, 0.88)),
    'quote_open': dict(auto=(0.98, 0.95), manual=(0.90, 0.85)),
    'quote_close': dict(auto=(0.98, 0.95), manual=(0.90, 0.85)),
    'bracket_present': dict(auto=(0.98, 0.95), manual=(0.90, 0.85)),
    'bracket_type': dict(auto=(0.97, 0.95), manual=(0.90, 0.85)),
    'dash': dict(auto=(0.98, 0.95), manual=(0.90, 0.85)),
    'ellipsis': dict(auto=(0.98, 0.95), manual=(0.90, 0.85)),
    'booktitle_open': dict(auto=(0.98, 0.95), manual=(0.90, 0.85)),
    'booktitle_close': dict(auto=(0.98, 0.95), manual=(0.90, 0.85)),
    'ring': dict(auto=(0.98, 0.95), manual=(0.90, 0.85)),
}
SENTENCE = {'period', 'question', 'exclamation', 'comma', 'enumeration_comma', 'semicolon', 'colon'}
CONTENT_TIERS = dict(
    auto=dict(cer_with_punct=0.020, cer_han_only=0.015, missing=0.010, wrong=0.010, extra=0.005),
    manual=dict(cer_with_punct=0.050, cer_han_only=0.040, missing=0.030, wrong=0.030, extra=0.020),
)
THRESHOLDS_SOURCE = ('PUNCT_EVAL v1.3 §5.2 + §6.4.8(data_missing) + CONTENT_EVAL v1.1 §6.2/§6.3'
                     '（t111 标定前的 provisional 值）')
DATA_MISSING_TIERS = dict(product_punct_ratio=0.75, input_punct_ratio=0.75, anchor_ratio=0.80)
TOP_N = 10


def sha(path):
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''):
                h.update(b)
        return h.hexdigest()
    except OSError:
        return ''


def _tier_for(cls):
    return PUNCT_TIERS['sentence' if cls in SENTENCE else cls]


def judge_punct(by_class, data_missing=False):
    """按 §5.2 三档：全部 auto -> AUTO；全部 >=manual -> MANUAL；任一低于 manual -> REJECT。
    data_missing=True（上游 OCR 缺标点）时降为 MANUAL 并注明，不归因渲染层。"""
    if not by_class:
        return 'UNSCORED', ['no_punct_class'], []
    auto_ok = manual_ok = True
    fail = []
    for cls, st in sorted(by_class.items()):
        tier = _tier_for(cls)
        if tier is None:
            continue
        p = st.get('precision', 0.0); r = st.get('recall', 0.0)
        if (st.get('tp', 0) + st.get('fp', 0) + st.get('fn', 0)) == 0:
            continue
        if not (p >= tier['auto'][0] and r >= tier['auto'][1]):
            auto_ok = False
        if not (p >= tier['manual'][0] and r >= tier['manual'][1]):
            manual_ok = False
            fail.append(dict(kind='punct', cls=cls, precision=p, recall=r,
                             need=dict(auto=tier['auto'], manual=tier['manual'])))
    if data_missing and not auto_ok:
        return 'MANUAL', ['data_missing'], fail
    if auto_ok:
        return 'AUTO', [], fail
    if manual_ok:
        return 'MANUAL', ['punct_below_auto'], fail
    return 'REJECT', ['punct_regression'], fail


def judge_content(metrics):
    """CONTENT_EVAL §6.2：两栏 CER + 三率 + must-pass 64/54。"""
    if not metrics:
        return 'UNSCORED', ['no_content_metrics'], []
    reasons, fail = [], []
    mp_ok = bool(metrics.get('must_pass')) or (metrics.get('must_pass_applicable') is False)
    if not mp_ok:
        reasons.append('must_pass_regression')
    wp = metrics.get('with_punct') or {}; ho = metrics.get('han_only') or {}

    def get(d, k):
        v = d.get(k)
        return None if v is None else float(v)

    def tier_ok(values, tier):
        for k, lim in tier.items():
            v = values.get(k)
            if v is None: continue
            if v > lim: return False
        return True
    vals_auto = dict(cer_with_punct=get(wp, 'cer'), cer_han_only=get(ho, 'cer'),
                     missing=get(wp, 'missing_rate'), wrong=get(wp, 'wrong_rate'),
                     extra=get(wp, 'extra_rate'))
    vals_manual = dict(vals_auto)
    if mp_ok and tier_ok(vals_auto, CONTENT_TIERS['auto']):
        return 'AUTO', [], fail
    if mp_ok and tier_ok(vals_manual, CONTENT_TIERS['manual']):
        return 'MANUAL', ['content_below_auto'], fail
    reasons.append('content_over_manual')
    fail.append(dict(kind='content', cer_with_punct=vals_auto['cer_with_punct'],
                     cer_han_only=vals_auto['cer_han_only'], must_pass=metrics.get('must_pass')))

    def rate(d, k):
        return d.get(k) or 0
    return 'REJECT', reasons, fail


def combine(v_ok, p_verdict, c_verdict, p_reasons=None, c_reasons=None):
    """三档合成：verify FAIL -> REJECT；任一 REJECT -> REJECT；任一 MANUAL/UNSCORED -> MANUAL_ONLY；全 AUTO -> AUTO_PASS。"""
    reasons = []
    if not v_ok:
        return 'REJECT', ['verify_fail']
    if p_verdict == 'REJECT' or c_verdict == 'REJECT':
        return 'REJECT', (p_reasons or []) + (c_reasons or []) + ['component_reject']
    if p_verdict in ('MANUAL', 'UNSCORED') or c_verdict in ('MANUAL', 'UNSCORED'):
        return 'MANUAL_ONLY', ['manual_tier']
    if p_verdict == 'AUTO' and c_verdict == 'AUTO':
        return 'AUTO_PASS', []
    return 'MANUAL_ONLY', ['unscored']


def parse_verify_stdout(text):
    out = dict(pass_=None, pages=None, pages_src=None, chars_ratio=None, overflow_span=None,
               overflow_vec=None, page_loss=None)
    m = re.search(r'源 OCR\s*(\d+)\s*页.*?输出 PDF\s*(\d+)\s*页', text)
    if not m:
        m = re.search(r'页数[^\d]*(\d+)\s*[=:]\s*(\d+)', text)
    if m:
        out['pages_src'] = int(m.group(1)); out['pages'] = int(m.group(2))
        out['pass_'] = int(m.group(1)) == int(m.group(2))
    m = re.search(r'字符量[^\n]*?(\d+(?:\.\d+)?)\s*%', text)
    if m: out['chars_ratio'] = float(m.group(1))
    m = re.search(r'越界[^\n]*?span\s*[*:：]?\s*(\d+)', text)
    if m: out['overflow_span'] = int(m.group(1))
    m = re.search(r'矢量\s*[*:：]?\s*(\d+)', text)
    if m: out['overflow_vec'] = int(m.group(1))
    m = re.search(r'整页丢失[^\n]*?页[:：]\s*(\d+)', text)
    if not m:
        m = re.search(r'整页丢失\s*[*:：]?\s*(\d+)', text)
    if m: out['page_loss'] = int(m.group(1))
    return out


def resolve_expect_low(book):
    """默认读 data/<book>/<book>_expect_low.txt（兼容 <book>_full 数据目录）；CLI --expect-low 优先。"""
    cands = [
        os.path.join(ROOT, 'data', book, book + '_expect_low.txt'),
        os.path.join(ROOT, 'data', book + '_full', book + '_full_expect_low.txt'),
        os.path.join(ROOT, 'data', book + '_full', book + '_expect_low.txt'),
    ]
    for c in cands:
        if os.path.exists(c):
            txt = ','.join(x.strip() for x in open(c, encoding='utf-8').read().split(',') if x.strip())
            return txt, c
    return '', None


def run_verify_vert(pdf, coords, lines, book, src_pdf='', expect_low=''):
    cmd = ['/usr/bin/python3', os.path.join(ROOT, 'src', 'test', 'verify_vert.py'), pdf, coords, lines]
    if src_pdf and os.path.exists(src_pdf):
        cmd += ['--src-pdf', src_pdf]
    if expect_low:
        cmd += ['--expect-low', expect_low]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=ROOT)
    except Exception as e:
        return dict(exit=-1, stdout='', stderr=str(e), **parse_verify_stdout(''))
    txt = p.stdout + '\n' + p.stderr
    m = parse_verify_stdout(txt)
    m.update(exit=p.returncode, stdout=p.stdout, stderr=p.stderr)
    m['pass_'] = bool(p.returncode == 0 and (m.get('pass_') is not False)
                      and (m.get('overflow_span') in (None, 0)) and (m.get('page_loss') in (None, 0)))
    return m


def _run_tool(py_func, args):
    """调用同进程评测器，捕获 stdout（评测器 print 到 stdout）。"""
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        rc = py_func(args)
    return rc, buf.getvalue().strip()


def detect_data_missing(content_gold, pdf, book, lines=None):
    """上游数据缺陷诊断：gold 有标点而产物文本层几乎无标点，但去标点 anchor 高度相似 -> OCR 缺标点，非渲染层。"""
    import difflib
    try:
        import fitz
        import punct_bench
    except Exception:
        return None
    d = json.load(open(content_gold, encoding='utf-8'))
    raw = d if isinstance(d, list) else d.get('items', [])
    items = [x for x in raw if x.get('book') in (None, book)]
    if not items:
        return None
    doc = fitz.open(pdf)
    rows = []
    gp_total = pp_total = ip_total = 0
    for it in items:
        pg = int(it['page'])
        if pg > len(doc):
            continue
        prod = ''.join(ch for ch in doc[pg - 1].get_text() if not ch.isspace())
        gold = ''.join(ch for ch in (it.get('text') or '') if not ch.isspace())
        inp = ''.join(str(x) for x in ((lines or {}).get(str(pg - 1)) or []) if x)
        gp = sum(1 for ch in gold if punct_bench._class_of(ch) is not None)
        pp = sum(1 for ch in prod if punct_bench._class_of(ch) is not None)
        ip = sum(1 for ch in inp if punct_bench._class_of(ch) is not None)
        ga = ''.join(ch for ch in gold if punct_bench._class_of(ch) is None)
        pa = ''.join(ch for ch in prod if punct_bench._class_of(ch) is None)
        ratio = difflib.SequenceMatcher(None, ga, pa, autojunk=False).ratio() if ga or pa else 0.0
        gp_total += gp; pp_total += pp; ip_total += ip
        rows.append(dict(page=pg, gold_punct=gp, input_punct=ip, product_punct=pp,
                         anchor_ratio=round(ratio, 4)))
    if not rows:
        return None
    ratios = sorted(r['anchor_ratio'] for r in rows)
    med = ratios[len(ratios) // 2]
    ratio_p = pp_total / max(1, gp_total)
    ratio_i = ip_total / max(1, gp_total)
    base_ok = bool(gp_total >= 3 and med >= DATA_MISSING_TIERS['anchor_ratio'])
    missing = bool(base_ok and ratio_p <= DATA_MISSING_TIERS['product_punct_ratio']
                   and ratio_i <= DATA_MISSING_TIERS['input_punct_ratio'])
    product_regression = bool(base_ok and ratio_p <= DATA_MISSING_TIERS['product_punct_ratio']
                              and ratio_i > DATA_MISSING_TIERS['input_punct_ratio'])
    classification = 'data_missing' if missing else ('product_regression' if product_regression else 'ok')
    return dict(missing=missing, classification=classification, gold_punct=gp_total,
                input_punct=ip_total, product_punct=pp_total,
                product_punct_ratio=round(ratio_p, 4), input_punct_ratio=round(ratio_i, 4),
                anchor_ratio_median=round(med, 4),
                pages=[r for r in rows if r['gold_punct'] - r['product_punct'] > 0][:20],
                note=('gold 有标点、输入 OCR 与产物文本层均缺标点且 anchor 相似 -> 上游 OCR 缺标点（非渲染层）'
                      if missing else ('输入 OCR 有标点但产物缺 -> 产品回归（渲染/文本层）'
                                       if product_regression else '')))
    

def locate_first_diff(page, gold_items, pdf, lines):
    """定位超限页第一个差异：返回 column/char_pos（gold 字符序位）与两侧字符。"""
    import difflib
    it = next((x for x in gold_items if int(x['page']) == int(page)), None)
    if not it:
        return dict(column=None, char_pos=None)
    gold = ''.join(ch for ch in (it.get('text') or '') if not ch.isspace())
    try:
        import fitz
        prod = ''.join(ch for ch in fitz.open(pdf)[int(page) - 1].get_text() if not ch.isspace())
    except Exception:
        prod = ''
    a0 = 0
    n = min(len(gold), len(prod))
    while a0 < n and gold[a0] == prod[a0]:
        a0 += 1
    if a0 == len(gold) == len(prod):
        return dict(column=None, char_pos=None)
    gc = gold[a0] if a0 < len(gold) else ''
    pc = prod[a0] if a0 < len(prod) else ''
    col = None
    try:
        rows = (lines or {}).get(str(int(page) - 1)) or []
        cum = 0
        for ri, row in enumerate(rows):
            rn = ''.join(ch for ch in str(row) if not ch.isspace())
            if cum + len(rn) > a0:
                col = ri
                break
            cum += len(rn)
    except Exception:
        col = None
    return dict(column=col, char_pos=a0, gold_char=gc, product_char=pc)


def locate_punct_missing(page, gold_items, pdf, lines):
    """定位该页第一个「gold 有、产物缺」的标点：column/char_pos（gold 字符序位）。"""
    it = next((x for x in gold_items if int(x['page']) == int(page)), None)
    if not it:
        return dict(column=None, char_pos=None)
    gold = ''.join(ch for ch in (it.get('text') or '') if not ch.isspace())
    try:
        import fitz
        prod = ''.join(ch for ch in fitz.open(pdf)[int(page) - 1].get_text() if not ch.isspace())
    except Exception:
        prod = ''
    import punct_bench
    from collections import Counter
    need = Counter(ch for ch in gold if punct_bench._class_of(ch) is not None)
    have = Counter(ch for ch in prod if punct_bench._class_of(ch) is not None)
    for i, ch in enumerate(gold):
        if punct_bench._class_of(ch) is None:
            continue
        if have[ch] < need[ch]:
            col = None
            try:
                rows = (lines or {}).get(str(int(page) - 1)) or []
                cum = 0
                for ri, row in enumerate(rows):
                    rn = ''.join(c2 for c2 in str(row) if not c2.isspace())
                    if cum + len(rn) > i:
                        col = ri; break
                    cum += len(rn)
            except Exception:
                col = None
            return dict(column=col, char_pos=i, gold_char=ch)
    return dict(column=None, char_pos=None)


def resolve_punct_gold(path):
    """gold 缺失时回退到仓库内 demo gold（并在输出记录），不写 data。"""
    if path and os.path.exists(path):
        return path, False
    alt = os.path.join(ROOT, 'src', 'test', 'bench', 'punct_gold_v1.json')
    if os.path.exists(alt):
        return alt, True
    return path, False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True)
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--coords', required=True)
    ap.add_argument('--lines', required=True)
    ap.add_argument('--gold', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--content-gold', default=os.path.join(ROOT, 'data/punct_eval/content_gold_v1.json'))
    ap.add_argument('--src-pdf', default='')
    ap.add_argument('--expect-low', default='')
    ap.add_argument('--top-n', type=int, default=TOP_N)
    args = ap.parse_args(argv)
    if not os.path.exists(args.pdf):
        print('[quality_gate] PDF 不存在: %s' % args.pdf, file=sys.stderr)
        return 2
    try:
        lines_local = json.load(open(args.lines, encoding='utf-8'))
    except Exception:
        lines_local = {}
    gold_items_local = []
    try:
        gd0 = json.load(open(args.content_gold, encoding='utf-8')) if os.path.exists(args.content_gold) else []
        raw0 = gd0 if isinstance(gd0, list) else gd0.get('items', [])
        gold_items_local = [x for x in raw0 if x.get('book') in (None, args.book)]
    except Exception:
        gold_items_local = []
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or '.', exist_ok=True)
    tmpdir = os.path.dirname(os.path.abspath(args.out))
    res = dict(schema_version='quality-gate-v1', book=args.book,
               pdf_sha256=sha(args.pdf), thresholds_source=THRESHOLDS_SOURCE,
               thresholds=dict(punct=PUNCT_TIERS, content=CONTENT_TIERS),
               verify=None, punct=None, content=None, gate=None)
    # 1) verify_vert
    src = args.src_pdf or os.path.join(ROOT, 'source_pdf', args.book + '.pdf')
    el, el_path = (args.expect_low, 'cli') if args.expect_low else resolve_expect_low(args.book)
    vm = run_verify_vert(args.pdf, args.coords, args.lines, args.book, src, el)
    res['expect_low'] = dict(pages=el, source=el_path)
    res['verify'] = dict(exit=vm.get('exit'), pass_=vm.get('pass_'), pages=vm.get('pages'),
                         pages_src=vm.get('pages_src'), chars_ratio=vm.get('chars_ratio'),
                         overflow_span=vm.get('overflow_span'), overflow_vec=vm.get('overflow_vec'),
                         page_loss=vm.get('page_loss'), src_pdf=(src if os.path.exists(src) else None),
                         stdout_tail='\n'.join((vm.get('stdout') or '').strip().splitlines()[-6:]))
    # 2) punct sequence（B，主）
    pseq = None
    if os.path.exists(args.content_gold):
        import punct_bench
        seq_out = os.path.join(tmpdir, '_punct_seq_%s.json' % args.book)
        rc, log = _run_tool(punct_bench.main, ['--mode', 'sequence', '--gold', args.content_gold,
                                               '--pdf', args.pdf, '--coords', args.coords,
                                               '--lines', args.lines, '--book', args.book,
                                               '--out', seq_out])
        if rc == 0 and os.path.exists(seq_out):
            s = json.load(open(seq_out, encoding='utf-8'))
            pseq = dict(mode='sequence', method=s.get('method'), gold_source=s.get('gold_source'),
                        overall=s.get('overall'), by_class=s.get('by_class'),
                        by_page=s.get('by_page'), errors=s.get('errors'),
                        reading_order=s.get('reading_order'), log=log)
    # 3) punct cell（A，可选；gold 缺失回退 demo 并记录）
    gold_path, fallback = resolve_punct_gold(args.gold)
    pcell = None
    try:
        import punct_bench
        cell_out = os.path.join(tmpdir, '_punct_cell_%s.json' % args.book)
        rc, log = _run_tool(punct_bench.main, ['--mode', 'cell', '--gold', gold_path, '--pdf', args.pdf,
                                              '--coords', args.coords, '--lines', args.lines,
                                              '--book', args.book, '--out-json', cell_out])
        if rc == 0 and os.path.exists(cell_out):
            c = json.load(open(cell_out, encoding='utf-8'))
            pcell = dict(mode='cell', method=c.get('method'), gold=gold_path, gold_fallback=fallback,
                         overall=c.get('overall'), by_class=c.get('by_class'), log=log)
    except Exception as e:
        pcell = dict(mode='cell', error=str(e))
    # punct 判定：B 主，A 仅参考（若 B 无则用 A）
    pun = pseq or pcell or {}
    p_by = pun.get('by_class') or {}
    dm = detect_data_missing(args.content_gold, args.pdf, args.book, lines_local) if os.path.exists(args.content_gold) else None
    p_verdict, p_reasons, p_fail = judge_punct(p_by, bool(dm and dm.get('missing')))
    if dm and dm.get('classification') == 'product_regression':
        p_reasons = list(dict.fromkeys(p_reasons + ['product_regression']))
    p_by_page = (pseq or {}).get('by_page') or []
    seq_errors = (pseq or {}).get('errors') or []
    err_by_page = {}
    for e in seq_errors:
        if isinstance(e, dict):
            err_by_page.setdefault(e.get('page'), []).append(e.get('kind') or e.get('detail'))
    fail_pages = []
    for p in p_by_page:
        if (p.get('fn') or 0) <= 0:
            continue
        loc = locate_punct_missing(p['page'], gold_items_local, args.pdf, lines_local)
        fail_pages.append(dict(page=p['page'], tp=p.get('tp'), fp=p.get('fp'), fn=p.get('fn'),
                               precision=p.get('precision'), recall=p.get('recall'),
                               column=loc.get('column'), char_pos=loc.get('char_pos'),
                               gold_char=loc.get('gold_char'), errors=err_by_page.get(p['page'], [])))
    fail_pages = fail_pages[:args.top_n]
    p_fail = [f for f in p_fail if (f.get('tp', 0) + f.get('fp', 0) + f.get('fn', 0)) > 0]
    for f in p_fail:
        f['pages'] = [p['page'] for p in fail_pages]
        if fail_pages and (f.get('column') is None):
            f['column'] = fail_pages[0].get('column')
        if fail_pages and (f.get('char_pos') is None):
            f['char_pos'] = fail_pages[0].get('char_pos')
    res['punct'] = dict(sequence=pseq, cell=pcell, verdict=p_verdict, reasons=p_reasons,
                        failures=p_fail[:args.top_n], by_page=p_by_page, errors=seq_errors,
                        pages_with_fn=fail_pages, data_missing=dm)
    # 4) content_eval（两栏 CER + must_pass）
    cm = None
    if os.path.exists(args.content_gold):
        import content_eval
        c_out = os.path.join(tmpdir, '_content_%s.json' % args.book)
        rc, log = _run_tool(content_eval.main, ['--gold', args.content_gold, '--pdf', args.pdf,
                                                '--coords', args.coords, '--lines', args.lines,
                                                '--book', args.book, '--out', c_out])
        if rc == 0 and os.path.exists(c_out):
            c = json.load(open(c_out, encoding='utf-8'))
            cm = dict(by_page=c.get('content', {}).get('by_page'),
                      vertical_form=c.get('content', {}).get('vertical_form'),
                      with_punct=c.get('content', {}).get('overall', {}).get('with_punct'),
                      han_only=c.get('content', {}).get('overall', {}).get('han_only'),
                      must_pass=c.get('regression', {}).get('must_pass'),
                      must_pass_items=c.get('regression', {}).get('must_pass_items'),
                      diagnostics=c.get('diagnostics'), log=log)
    if cm is not None:
        try:
            import fitz
            npages = len(fitz.open(args.pdf))
            mps = (cm.get('must_pass_items') or {}).get('missing_char_confirmed', {}).get('items') or []
            rps = (cm.get('must_pass_items') or {}).get('battle4_ring', {}).get('items') or []
            pages = [it.get('page') for it in (mps + rps) if it.get('page')]
            frac = (sum(1 for p in pages if p <= npages) / len(pages)) if pages else 0.0
            cm['must_pass_applicable'] = frac >= 0.9
            cm['must_pass_page_coverage'] = round(frac, 4)
        except Exception:
            cm['must_pass_applicable'] = True
    c_verdict, c_reasons, c_fail = judge_content(cm or {})
    over_pages = []
    mp_fail_items = []
    if cm:
        wpm = CONTENT_TIERS['manual']
        gold_items = []
        try:
            gd = json.load(open(args.content_gold, encoding='utf-8'))
            raw = gd if isinstance(gd, list) else gd.get('items', [])
            gold_items = [x for x in raw if x.get('book') in (None, args.book)]
        except Exception:
            gold_items = []
        for pg in (cm.get('by_page') or []):
            wp = pg.get('with_punct') or {}
            if wp.get('cer') is not None and wp['cer'] > wpm['cer_with_punct']:
                loc = locate_first_diff(pg.get('page'), gold_items, args.pdf, lines_local)
                over_pages.append(dict(page=pg.get('page'), cer_with_punct=wp['cer'], **loc))
        if cm.get('must_pass_applicable') is False:
            cm['must_pass_status'] = 'not_applicable'
            cm['must_pass_fail_items'] = []
            cm['must_pass_items'] = None
            cm['must_pass_items_cleared'] = True
        else:
            for kind in ('missing_char_confirmed', 'battle4_ring'):
                for it in ((cm.get('must_pass_items') or {}).get(kind, {}) or {}).get('items', []):
                    if it.get('ok'): continue
                    mp_fail_items.append(dict(kind=kind, page=it.get('page'),
                                              ch=it.get('ch') or it.get('cp'),
                                              char_pos=it.get('pos'), column=it.get('col'),
                                              expected=it.get('ch') or it.get('cp'), reason=it.get('reason')))
        for f in c_fail:
            f['over_limit_pages'] = over_pages[:args.top_n]
            f['must_pass_fail_items'] = mp_fail_items[:args.top_n]
    res['content'] = dict(metrics=cm, verdict=c_verdict, reasons=c_reasons,
                          failures=c_fail[:args.top_n], over_limit_pages=over_pages[:args.top_n],
                          must_pass_fail_items=mp_fail_items[:args.top_n])
    # 5) 合成
    v_ok = bool(res['verify'].get('pass_'))
    verdict, reasons = combine(v_ok, p_verdict, c_verdict, p_reasons, c_reasons)
    if dm and dm.get('missing') and v_ok and verdict == 'REJECT':
        verdict = 'MANUAL_ONLY'
        reasons = list(dict.fromkeys(['data_missing'] + [r for r in reasons if r != 'component_reject']))
    if dm and dm.get('classification') == 'product_regression':
        verdict = 'REJECT' if not v_ok else verdict
        reasons = list(dict.fromkeys(reasons + ['product_regression']))
    top = []
    for f in p_fail[:args.top_n]:
        top.append(f)
    for f in c_fail[:args.top_n]:
        top.append(f)
    if not v_ok:
        top.insert(0, dict(kind='verify', exit=res['verify'].get('exit'),
                           overflow_span=res['verify'].get('overflow_span'),
                           page_loss=res['verify'].get('page_loss'),
                           stdout_tail=res['verify'].get('stdout_tail')))
    wp = (cm or {}).get('with_punct') or {}; ho = (cm or {}).get('han_only') or {}
    s_o = (pseq or {}).get('overall') or {}
    res['version'] = 'quality-gate-v1'
    res['metrics'] = dict(
        verify=dict(pass_=v_ok, pages=res['verify'].get('pages'), pages_src=res['verify'].get('pages_src'),
                    chars_ratio=res['verify'].get('chars_ratio'),
                    overflow_span=res['verify'].get('overflow_span'),
                    page_loss=res['verify'].get('page_loss')),
        punct=dict(precision=s_o.get('precision'), recall=s_o.get('recall'), tp=s_o.get('tp'),
                   fp=s_o.get('fp'), fn=s_o.get('fn'), verdict=p_verdict),
        content=dict(cer_with_punct=wp.get('cer'), cer_han_only=ho.get('cer'),
                     must_pass=(cm or {}).get('must_pass'), verdict=c_verdict))
    res['verdict'] = verdict
    res['reasons'] = reasons
    res['gate'] = dict(verdict=verdict, reasons=reasons, verify_pass=v_ok,
                       punct_verdict=p_verdict, content_verdict=c_verdict,
                       data_missing=bool(dm and dm.get('missing')),
                       top_failures=top[:args.top_n],
                       note='B=punct sequence（provisional）；A=cell 仅参考；content 阈值待 t111 标定；data_missing=上游 OCR 缺标点')
    json.dump(res, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # markdown 摘要
    md = render_markdown(res)
    md_path = os.path.splitext(args.out)[0] + '.md'
    open(md_path, 'w', encoding='utf-8').write(md)
    print('[quality_gate] %s: verify=%s punct=%s content=%s -> %s' %
          (args.book, 'PASS' if v_ok else 'FAIL', p_verdict, c_verdict, verdict))
    return 0


def render_markdown(r):
    v = r['verify']; p = r['punct']; c = r['content']; g = r['gate']
    wp = (c.get('metrics') or {}).get('with_punct') or {}
    ho = (c.get('metrics') or {}).get('han_only') or {}
    s = (p.get('sequence') or {}).get('overall') or {}
    lines = [
        '# 质量门禁报告 · %s' % r['book'], '',
        '- **结论：%s**' % g['verdict'],
        '- 原因：`%s`' % ', '.join(g['reasons']), '',
        '| 分项 | 结果 |', '|---|---|',
        '| verify_vert | %s（exit=%s, 页数=%s/%s, 字符量=%s%%, 越界 span=%s, 整页丢失=%s） |' % (
            'PASS' if v.get('pass_') else 'FAIL', v.get('exit'), v.get('pages'), v.get('pages_src'),
            v.get('chars_ratio'), v.get('overflow_span'), v.get('page_loss')),
        '| punct（sequence B） | %s：P=%s R=%s TP/FP/FN=%s/%s/%s |' % (
            p.get('verdict'), s.get('precision'), s.get('recall'), s.get('tp'), s.get('fp'), s.get('fn')),
        '| content（两栏 CER） | %s：with_punct=%s, han_only=%s, must_pass=%s |' % (
            c.get('verdict'), wp.get('cer'), ho.get('cer'), (c.get('metrics') or {}).get('must_pass')), '',
        '阈值来源：%s' % r['thresholds_source'], '',
    ]
    if g.get('top_failures'):
        lines += ['## 失败明细（top-%d）' % len(g['top_failures']), '']
        for f in g['top_failures']:
            lines.append('- `%s`' % json.dumps(f, ensure_ascii=False)[:300])
        lines.append('')
    lines += ['_由 quality_gate.py 生成；不改判据、不联网。_']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    sys.exit(main())
