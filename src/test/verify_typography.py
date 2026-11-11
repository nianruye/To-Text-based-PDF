#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_typography.py — 排版校验器（TYPOGRAPHY_EVAL v1，t239）。

三层：L1 强制 fail / L2 源书保真指标（provisional，不阻断）/ L3 GB 参考（默认 warn，仅 render_introduced fail）。
"""
import argparse
import json
import os
import re
import sys

START_PROHIBIT = set('，。、；：？！）】》」』”’…—·')
OPEN_END = set('（【《「『“‘')
TOC_PAGE_RE = re.compile(r'[.．·…]{3,}\s*\d{1,4}\s*$')
NUM_ONLY = re.compile(r'^\d{1,4}$')
NUM_PREFIX = re.compile(r'^\d{1,4}(?:[.．、]\s*)?(?=\S|$)')
GB51_RULES = {
    '5.1.1': 'gb51_dot_line_start', '5.1.2': 'gb51_question_exclaim_cell',
    '5.1.3': 'gb51_quote_bracket_break', '5.1.4': 'gb51_dash_break',
    '5.1.5': 'gb51_ellipsis_break', '5.1.6': 'gb51_connector_cell',
    '5.1.7': 'gb51_interpunct_cell', '5.1.9': 'gb51_separator_cell',
    '5.1.10': 'gb51_lineend_halfwidth',
}
EXEMPT_GB51 = {'5.1.8': 'not_machine_checkable_from_text_layer',
               '5.1.11': 'permissive_clause'}
# t244：每条规则显式字符类，禁止跨规则复用
DOT_SET = set('。，、；：')
Q_SET = set('？！')
PAIR_OPEN = set('“‘「『（〔【《〈')
PAIR_CLOSE = set('”’」』）〕】》〉')
DASH_SET = set('—')
ELL_SET = set('…')
CONN_SET = set('-～')
INTER_SET = set('·')
SEP_SET = set('/')
PUNCT_END_SET = DOT_SET | Q_SET | PAIR_OPEN | PAIR_CLOSE | DASH_SET | ELL_SET | CONN_SET | INTER_SET | SEP_SET
CLOSE_SET = PAIR_CLOSE
GB52_RULES = {
    '5.2.1': 'gb52_dot_position', '5.2.2': 'gb52_quote_bracket_position',
    '5.2.3': 'gb52_dash_ellipsis_vertical', '5.2.4': 'gb52_dot_cell',
    '5.2.5': 'gb52_column_edges', '5.2.6': 'gb52_latin_digit_position',
}
META_KEYS = ("anna's archive", 'document generated', 'filesize', 'md5',
             'pdg_dir_name', 'total_pages', 'pdf_generation')


def _lines(page):
    out = []
    for b in page.get_text('dict').get('blocks', []):
        for l in b.get('lines', []):
            txt = ''.join(s.get('text', '') for s in l.get('spans', [])).strip()
            if not txt:
                continue
            out.append(dict(text=txt, bbox=list(l['bbox']), spans=list(l.get('spans', []))))
    return out


def _span_violations(lines):
    """① span 重叠：TOC 页码/序号 span 与标题 span 负 gap。"""
    v = []
    for li, line in enumerate(lines):
        spans = [s for s in line['spans'] if s.get('text', '').strip()]
        spans.sort(key=lambda s: s['bbox'][0])
        for a, b in zip(spans, spans[1:]):
            ta = a.get('text', '').strip()
            if not re.fullmatch(r'\d{1,4}[.．、]', ta):
                continue
            gap = b['bbox'][0] - a['bbox'][2]   # 标题左缘 − 序号右缘（负=重叠）
            if gap < -5.0:   # 页码/序号右缘越过标题左缘（>5pt 才判 span 重叠）
                v.append(dict(rule_id='L1.1', name='hard_span_overlap', layer='L1',
                              page=line.get('page'), line=li, severity='fail',
                              span=ta, gap=round(gap, 2),
                              bbox=[round(x, 1) for x in a['bbox']],
                              other_bbox=[round(x, 1) for x in b['bbox']],
                              message='TOC number span overlaps title (gap %.2fpt)' % gap))
    return v


def _toc_page(lines):
    n = sum(1 for l in lines if TOC_PAGE_RE.search(l['text']))
    n += sum(1 for l in lines if NUM_PREFIX.match(l['text'].strip()))
    return n >= 5


def _toc_metrics(lines, page):
    out = []
    entry_sizes = []
    cont_x = []
    pn_right = []
    for li, l in enumerate(lines):
        t = l['text'].strip()
        sizes = [round(s.get('size', 0), 1) for s in l['spans']
                 if s.get('text', '').strip() and not re.fullmatch(r'\d{1,4}', s.get('text', '').strip())]
        for s in l['spans']:
            st = s.get('text', '').strip()
            if NUM_ONLY.fullmatch(st) and s.get('size', 99) <= 14:
                pn_right.append((li, round(s['bbox'][2], 1)))
        if not sizes:
            continue
        if (NUM_PREFIX.match(t)
                and not re.match(r'^(?:\d+\s*)?[一二三四五六七八九十]+[“"‘\s]', t)):
            entry_sizes.append((li, max(sizes)))
        # 续行/标题缩进：收集标题类 span 的 x0（含与序号同行的标题 span）
        if not NUM_ONLY.fullmatch(t) and not TOC_PAGE_RE.search(t):
            xs = [round(s['bbox'][0], 1) for s in l['spans']
                  if s.get('text', '').strip() and s.get('size', 0) >= 14
                  and not re.fullmatch(r'\d{1,4}[.．、]?', s.get('text', '').strip())]
            if xs:
                cont_x.append((li, min(xs)))
            elif not NUM_PREFIX.match(t):
                cont_x.append((li, round(l['bbox'][0], 1)))
        for s in l['spans']:
            st = s.get('text', '').strip()
            if NUM_ONLY.fullmatch(st) and s.get('size', 99) <= 14:
                pn_right.append((li, round(s['bbox'][2], 1)))
    if entry_sizes:
        vals = sorted(set(v for _, v in entry_sizes))
        if len(vals) >= 2 and max(vals) - min(vals) > 5:
            out.append(dict(rule_id='L2.1', name='toc_font_inconsistent', layer='L2',
                            page=page, severity='warn', values=vals,
                            message='same-level TOC entry font sizes differ: %s' % vals))
    if len(cont_x) >= 2:
        xs = sorted(set(x for _, x in cont_x))
        if max(xs) - min(xs) > 20:
            out.append(dict(rule_id='L2.2', name='toc_cont_indent', layer='L2',
                            page=page, severity='warn', values=xs,
                            message='TOC continuation x0 differs: %s' % xs))
    if len(pn_right) >= 2:
        rs = sorted(set(r for _, r in pn_right))
        if max(rs) - min(rs) > 8:
            out.append(dict(rule_id='L2.3', name='toc_pagenum_align', layer='L2',
                            page=page, severity='warn', values=rs,
                            message='TOC page-number right edges differ: %s' % rs))
    return out


def _source_map(src_lines):
    if not src_lines:
        return {}
    return {str(k): [str(x) for x in v] for k, v in src_lines.items()}


def _attribute_text(page, text, src_pages, page_text=''):
    """返回 (attribution, source_line)。源 OCR 同页同行/同前缀匹配。"""
    rows = src_pages.get(str(page), [])
    if not rows:
        return 'unknown', None
    norm = ''.join(text.split())
    for r in rows:
        if ''.join(r.split()) == norm:
            return 'source_inherent', r
    pref = norm[:8]
    for r in rows:
        if pref and ''.join(r.split()).startswith(pref):
            return 'source_inherent', r
    # t244：源页存在但行对齐失败 → unknown（不升级 fail，避免把源书特性判成渲染引入）
    return 'unknown', None



def _emit_gb(rule_id, name, page, li, char, text, src_pages, page_text,
             severity='warn', bbox=None, line_x=None, pos='start'):
    if rule_id in ('5.1.1', '5.1.2', '5.1.3', '5.1.4', '5.1.5', '5.1.6', '5.1.7', '5.1.9'):
        attr, src_line = _attribute_edge(page, text, char, src_pages, pos)
    else:
        attr, src_line = _attribute_text(page, text, src_pages, page_text)
    if attr == 'source_inherent':
        return None, dict(rule_id=rule_id, name=name, page=page + 1, line=li,
                          char=char, attribution=attr, source_line=(src_line or '')[:80])
    sev = 'fail' if attr == 'render_introduced' else severity
    d = dict(rule_id=rule_id, name=name, layer='L3', page=page + 1, line=li,
             char=char, text=text[:80], attribution=attr, severity=sev,
             message='GB %s char %r (%s)' % (rule_id, char, attr))
    if bbox is not None:
        d['bbox'] = [round(x, 1) for x in bbox]
    if line_x is not None:
        d['line_x_min'] = round(line_x[0], 1); d['line_x_max'] = round(line_x[1], 1)
    return d, None


def _visual_line(l):
    """按可见字形 x 坐标重建视觉行：返回 text/first/last 及 bbox/行 x 范围。"""
    sps = [s for s in l.get('spans', []) if s.get('text', '').strip()]
    sps.sort(key=lambda s: (s['bbox'][0], s['bbox'][2]))
    text = ''.join(s.get('text', '') for s in sps).strip()
    if not sps or not text:
        return text, None, None, None, None, l['bbox'][0], l['bbox'][2]
    fs = next((s for s in sps if s.get('text', '').strip()), sps[0])
    ls = sps[-1]
    fch = fs['text'].strip()[0]
    lch = ls['text'].strip()[-1]
    fb = fs['bbox']; lb = ls['bbox']
    # 单字符 span 用原 bbox；多字符按首/末字近似 1/N 宽
    nf = max(1, len(fs['text'].strip())); nl = max(1, len(ls['text'].strip()))
    fbox = [fb[0], fb[1], fb[0] + (fb[2]-fb[0])/nf, fb[3]]
    lbox = [lb[2] - (lb[2]-lb[0])/nl, lb[1], lb[2], lb[3]]
    return text, fch, fbox, lch, lbox, l['bbox'][0], l['bbox'][2]


def _is_nonbody_page(page_text, pno, page_image):
    if pno in page_image:
        return True
    hits = sum(1 for k in META_KEYS if k in page_text)
    if hits >= 3:
        return True
    # 版权/CIP 元数据页：整页非正文（避免 ISBN 条/上架建议越界误伤）
    if 'isbn' in page_text and ('图书在版编目' in page_text or '上架建议' in page_text):
        return True
    return False


def _attribute_edge(page, text, edge_char, src_pages, pos='start'):
    """行首/行末字符归因：源同页行存在；exact 同位置字符不同→render；前缀相似但源首字符不同→render；否则 unknown。"""
    rows = src_pages.get(str(page), [])
    if not rows:
        return 'unknown', None
    norm = ''.join(text.split())
    for r in rows:
        rn = ''.join(str(r).split())
        if rn == norm:
            src_edge = rn[:1] if pos == 'start' else rn[-1:]
            return ('source_inherent', r) if src_edge == edge_char else ('render_introduced', r)
    core = re.sub(r'^[^\u4e00-\u9fff]+', '', norm)
    core = re.sub(r'^[0-9①-⑳\u20e3\u20dd\s]+', '', core)
    for r in rows:
        rn = ''.join(str(r).split())
        rc = re.sub(r'^[^\u4e00-\u9fff]+', '', rn)
        rc = re.sub(r'^[0-9①-⑳\u20e3\u20dd\s]+', '', rc)
        if core and len(core) >= 6 and (core in rc or rc[:8] == core[:8]):
            src_edge = rn[:1] if pos == 'start' else rn[-1:]
            return ('source_inherent' if src_edge == edge_char else 'render_introduced'), r
    return 'unknown', None


def _general_overlap(lines):
    """M1（spec 方向）：跨视觉行 span 重叠，面积 >0.02×min；同视觉行/标点组不判。"""
    out = []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            for sa in lines[i].get('spans', []):
                for sb in lines[j].get('spans', []):
                    ta, tb = sa.get('text', '').strip(), sb.get('text', '').strip()
                    if not ta or not tb:
                        continue
                    # 标点组内嵌（如 ' 与 ,）不判 L1
                    if all(c in PUNCT_END_SET for c in ta) or all(c in PUNCT_END_SET for c in tb):
                        continue
                    ax0, ay0, ax1, ay1 = sa['bbox']; bx0, by0, bx1, by1 = sb['bbox']
                    # 相邻行盒天然重叠（行高 > 行距）：y0 明显错开即视为正常行，不判 L1
                    _ah = ay1 - ay0; _bh = by1 - by0
                    if _ah > 0 and _bh > 0 and abs(ay0 - by0) > 0.40 * min(_ah, _bh):
                        continue
                    iw = min(ax1, bx1) - max(ax0, bx0); ih = min(ay1, by1) - max(ay0, by0)
                    if iw <= 0 or ih <= 0:
                        continue
                    amin = min((ax1-ax0)*(ay1-ay0), (bx1-bx0)*(by1-by0)) or 1
                    if iw * ih < 0.02 * amin:
                        continue
                    out.append(dict(rule_id='L1.1', name='hard_span_overlap', layer='L1',
                                    page=lines[i].get('page'), line=i, other_line=j, severity='fail',
                                    span=ta[:20], other_span=tb[:20],
                                    bbox=[round(x, 1) for x in sa['bbox']],
                                    other_bbox=[round(x, 1) for x in sb['bbox']],
                                    message='cross-line span overlap'))
    return out[:20]


def _gb51_violations(lines, page, src_pages, page_text, page_width):
    """§5.1 九条机检（t244：显式字符类，禁止跨规则复用）。"""
    out, waived = [], []
    for li, l in enumerate(lines):
        t = l['text'].strip()
        if not t:
            continue
        _vt, first, _fb, last, _lb, _lx0, _lx1 = _visual_line(l)
        _bbox = _fb if first is not None else None
        _line_x = (_lx0, _lx1)
        rules = []

        def add(rid, ch):
            if rid not in [r[0] for r in rules]:
                rules.append((rid, ch))
        # t245：行首判据只用视觉左端字形；行末句读合法，不得判行首
        if first in DOT_SET:
            add('5.1.1', first)
        if first in Q_SET:
            add('5.1.2', first)
        if first in PAIR_CLOSE or last in PAIR_OPEN:
            add('5.1.3', first if first in PAIR_CLOSE else last)
        if first in DASH_SET:
            add('5.1.4', first)
            # t244：p5 兼容口径——真实行首破折号同时保留 dot_line_start 命名
            add('5.1.1', first)
        if first in ELL_SET:
            add('5.1.5', first)
        if first in CONN_SET:
            add('5.1.6', first)
        if first in INTER_SET:
            add('5.1.7', first)
        if first in SEP_SET:
            add('5.1.9', first)
        for sp in l['spans']:
            st = sp.get('text', '').strip()
            if not st:
                continue
            size = float(sp.get('size') or 0) or 1.0
            w = sp['bbox'][2] - sp['bbox'][0]
            if re.fullmatch(r'[？！]{2,}', st) and w > 1.15 * size:
                add('5.1.2', st[0])
            if re.fullmatch(r'[—]{2,}', st) and w > 1.15 * size:
                add('5.1.4', st[0])
            if re.fullmatch(r'[…]{2,}', st) and w > 1.15 * size:
                add('5.1.5', st[0])
            if re.fullmatch(r'[-～]{2,}', st) and w > 1.15 * size:
                add('5.1.6', st[0])
            if len(st) == 1 and st in PUNCT_END_SET and w < 0.5 * size:
                add('5.1.10', st)
        seen = set()
        for rid, ch in rules:
            if rid in seen:
                continue
            seen.add(rid)
            v, w = _emit_gb(rid, GB51_RULES[rid], page, li, ch, t, src_pages, page_text,
                            bbox=(_fb if ch == first else _lb), line_x=_line_x)
            if v: out.append(v)
            if w: waived.append(w)
    return out, waived


def _gb52_violations(lines, page, book_type):
    """§5.2 六条竖排机检：vertical/ancient 分支只出 warn（决策 A gating）。"""
    out = []
    for li, l in enumerate(lines):
        t = l['text'].strip()
        if not t:
            continue
        first, last = t[0], t[-1]
        checks = []
        _vfirst = first in (DOT_SET | Q_SET | PAIR_CLOSE | DASH_SET | ELL_SET | INTER_SET | SEP_SET)
        if _vfirst:
            checks.append('5.2.5')
        if first in PAIR_CLOSE or last in PAIR_OPEN:
            checks.append('5.2.2')
        if first in DASH_SET or last in DASH_SET or first in ELL_SET or last in ELL_SET:
            checks.append('5.2.3')
        for sp in l['spans']:
            st = sp.get('text', '').strip()
            if not st:
                continue
            size = float(sp.get('size') or 0) or 1.0
            w = sp['bbox'][2] - sp['bbox'][0]
            h = sp['bbox'][3] - sp['bbox'][1]
            if st[0] in PUNCT_END_SET and (w > 1.15 * size or h > 1.15 * size):
                checks.append('5.2.4')
            if re.match(r'[0-9A-Za-z]', st) and h < 0.5 * size:
                checks.append('5.2.6')
            if st[0] in PUNCT_END_SET:
                checks.append('5.2.1')
        for rid in dict.fromkeys(checks):
            out.append(dict(rule_id=rid, name=GB52_RULES[rid], layer='L3',
                            page=page + 1, line=li, char=first, text=t[:60],
                            attribution='vertical_stat', severity='warn',
                            message='GB %s vertical statistic' % rid))
    return out

def run(args):
    import fitz
    src = fitz.open(args.src_pdf) if args.src_pdf and os.path.exists(args.src_pdf) else None
    pdf = fitz.open(args.pdf)
    src_pages = json.load(open(args.lines, encoding='utf-8')) if args.lines and os.path.exists(args.lines) else {}
    page_image = set()
    if args.page_image_pages:
        for x in args.page_image_pages.split(','):
            if x.strip().isdigit(): page_image.add(int(x.strip()) - 1)
    violations = []
    waived = []
    non_body = []
    m1_diag = []
    body_lines = 0
    compliant = 0
    for pno in range(len(pdf)):
        lines = _lines(pdf[pno])
        for l in lines: l['page'] = pno + 1
        page_text = ' '.join(l['text'] for l in lines).lower()
        is_nonbody = _is_nonbody_page(page_text, pno, page_image)
        if is_nonbody:
            non_body.append(pno + 1)
            continue
        _is_toc = _toc_page(lines)
        # t255：同视觉行内 span 不判 L1（CJK/标点天然内嵌）；TOC 负 gap 保留为 L2 诊断
        if _is_toc:
            for _v in _span_violations(lines):
                _v = dict(_v); _v['layer'] = 'L2'; _v['severity'] = 'warn'; _v['name'] = 'toc_number_overlap'
                violations.append(_v)
        # t255：M1 为诊断级（不参与 fail）；TYPOGRAPHY_M1=1 时单列报告
        if os.environ.get('TYPOGRAPHY_M1') == '1' and not _is_toc:
            m1_diag += _general_overlap(lines)
        # L1 文本越界（可打印区 ± 容差；p97 类严重页统计全部 span，普通页跳过短标点/页码）
        pr = pdf[pno].rect
        _tol = max(2.0, 0.02 * min(pr.width, pr.height))
        _outside = []
        for li, l in enumerate(lines):
            for sp in l['spans']:
                b = sp['bbox']
                if (b[2] < pr.x0 - _tol or b[0] > pr.x1 + _tol or
                        b[3] < pr.y0 - _tol or b[1] > pr.y1 + _tol):
                    _outside.append((li, sp))
        _severe = len(_outside) >= 5
        for li, sp in _outside:
            _st = sp.get('text', '').strip()
            if not _severe and (re.fullmatch(r'\d{1,4}', _st) or len(_st) <= 3):
                continue
            violations.append(dict(rule_id='L1.2', name='hard_text_out_of_page',
                                   layer='L1', page=pno + 1, line=li,
                                   severity='fail', span=_st[:20],
                                   bbox=[round(x, 1) for x in sp['bbox']],
                                   message='text span outside page rect'))
            if not _severe:
                break
        # L2 TOC
        if _is_toc:
            violations += _toc_metrics(lines, pno + 1)
        if args.book_type in ('vertical', 'ancient'):
            # ③ 层降为统计：只记录，不 fail
            pass
        # L3 GB：横排 §5.1 / 竖排 §5.2（gating）
        if args.book_type == 'vertical':
            violations += _gb52_violations(lines, pno, args.book_type)
        elif args.book_type == 'ancient':
            pass
        else:
            gv, gw = _gb51_violations(lines, pno, src_pages, page_text, pdf[pno].rect.width)
            violations += gv; waived += gw
        body_lines += len(lines)
        # 合规率口径：L3 渲染引入 fail 行；L1 硬约束单列（hard 计数），不压 L3 合规率
        bad_lines = {v['line'] for v in violations
                     if v.get('page') == pno + 1 and v.get('layer') == 'L3'
                     and v.get('severity') == 'fail'}
        compliant += max(0, len(lines) - len(bad_lines))
    # L1 页数 1:1（有源时）
    if src is not None and len(pdf) != len(src):
        violations.append(dict(rule_id='L1.5', name='hard_page_1to1', layer='L1',
                               page=0, line=0, severity='fail',
                               message='output pages %d != source pages %d' % (len(pdf), len(src))))
    # 计数
    hard_fail = [v for v in violations if v.get('layer') == 'L1' and v.get('severity') == 'fail']
    render_fail = [v for v in violations if v.get('layer') == 'L3' and v.get('attribution') == 'render_introduced']
    by_rule = {}
    by_attr = {}
    for v in violations:
        by_rule[v['name']] = by_rule.get(v['name'], 0) + 1
        by_attr[v.get('attribution', 'n/a')] = by_attr.get(v.get('attribution', 'n/a'), 0) + 1
    fail = bool(hard_fail or render_fail)
    report = dict(
        tool='verify_typography', version='v1', pdf=args.pdf, src_pdf=args.src_pdf,
        book_type=args.book_type, pages=len(pdf), body_lines=body_lines,
        compliant_lines=compliant,
        compliance_rate=(round(compliant / body_lines, 6) if body_lines else None),
        verdict=('FAIL' if fail else ('WARN' if violations else 'PASS')),
        exit=1 if fail else 0,
        counts=dict(violations=len(violations), hard=len(hard_fail),
                    render_introduced=len(render_fail), waived=len(waived),
                    non_body_pages=len(non_body), m1_diagnostic=len(m1_diag)),
        diagnostics=dict(M1=m1_diag),
        by_rule=by_rule, by_attribution=by_attr,
        violations=violations, waived=waived, non_body_pages=non_body,
        gate_effect='none',  # t250：工具 exit 与门禁 verdict 分离；scan2pdf/quality_gate 不据此改 gate
        known_issues=['p97_horizontal_overflow'] if any(v.get('page') == 97 for v in hard_fail) else [],
        layers=dict(hard=('fail' if hard_fail else 'pass'), L1=['M2', 'M5'],
                    fidelity=('warn' if any(v['layer'] == 'L2' for v in violations) else 'metric'),
                    gb=('fail' if render_fail else ('warn' if any(v['layer'] == 'L3' for v in violations) else 'pass'))),
    )
    if args.json:
        json.dump(report, open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('[typography] pages=%d lines=%d compliance=%s verdict=%s violations=%d hard=%d render=%d waived=%d non_body=%d' % (
        len(pdf), body_lines, report['compliance_rate'], report['verdict'], len(violations),
        len(hard_fail), len(render_fail), len(waived), len(non_body)))
    for v in violations[:12]:
        print('  %s p%s l%s %s %s %s gap=%s %s' % (
            v.get('layer'), v.get('page'), v.get('line'), v.get('name'),
            v.get('char', ''), v.get('severity'), v.get('gap', ''), v.get('message', '')))
    return report['exit']


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('--src-pdf', default='')
    ap.add_argument('--lines', default='')
    ap.add_argument('--coords', default='')
    ap.add_argument('--json', default='')
    ap.add_argument('--book-type', default='horizontal', choices=['horizontal', 'vertical', 'ancient'])
    ap.add_argument('--page-image-pages', default='')
    args = ap.parse_args(argv)
    try:
        return run(args)
    except Exception as e:
        print('[typography] ERROR %s' % e, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
