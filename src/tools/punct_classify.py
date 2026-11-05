#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""punct_classify.py — 标点审计条目的 A/B/C 归因（GB/T 15834—2011 审计第二部分）

把 punct_audit.py 的条目按「A 源书自身 / B 产物引入 / C OCR 漏识 / C_fixed / K / O / D」分类。

v2（t6 修订，对应 t5 findings F1–F3/F4–F8）：
  F1 源位置闸门：line_start / line_end / pair_split 的 A 判定不再只看「字符是否在 OCR 行里」，
     而是要求产物行首/末的文本前缀/后缀与**同页某 OCR 行的行首/行末**一致（NFKC+竖排形态归一）：
       · 前缀/后缀命中 -> A（源书该行的边界就是它）
       · 只在 OCR 行中间出现 / 完全不在 -> B（产物断行把它甩到边界）
     竖排同口径（OCR 行 = 列文本）；OCR 把列首/行首的「一」误读、渲染端改回引号的 -> C_fixed（误读修复）。
  F2 破折号：dash_lead（—— 行首）legal -> D_legal（不计违规）；单个 — 行首 -> D_ambiguous（只报告）；
     §5.1.6 只对连接号（~ - 等）计 line_start。
  F3 carry：punct_audit 只在「对偶符落在相邻页边界行/列（或相邻段末/首行）」时给 carry -> K（valid）；
     否则给 carry_hint=weak（相邻页有对偶符但不在边界）/none（相邻页无对偶符）-> K_weak / K_invalid（单独列，不计 A/B）。
  其他：pair_balance unmatched_open 无 carry -> O 残差；unmatched_close 按对齐 equal/delete -> A/B。
用法：
  /usr/bin/python3 src/tools/punct_classify.py \
      --audit <punct_audit.json> --pdf <product.pdf> --lines <ocr_lines.json> \
      --mode h|v [--coords <ocr_coords.json>] [--src-pdf <source.pdf>] \
      --out <classified.json> [--diff-out <punct_diff.json>] [--label 书名]

输出：classified.json（原条目 + cls/why 字段）；--diff-out 另写 punct_diff 诊断项。
同一输入同一输出（无时间戳/随机；按 audit items 原序）。
"""
import difflib
import json
import os
import sys
import unicodedata
from collections import Counter

sys.path.insert(0, 'src/tools')
import fitz
from punct_audit import extract_h, extract_v, _norm, OPENERS, CLOSERS

PUNCT_ALL = set('。，、；：？！．﹐﹑﹔﹕﹖﹗') | set('（）〔〕【】《》〈〉「」『』“”‘’﹁﹂﹃﹄︵︶︗︘︹︺︽︾︿﹀') \
            | set('—―–‐-…⋯·・‧/／') \
            | set(',.;:?!)][(<>"\'/')   # NFKC 归一后的半角形态（normalize 后比较）
MISREAD_FIRST = set('一0〇')
WIDE, FLAT = 0.5, 0.6      # 源图最后一格「宽而扁」闭引号墨条（×step）


def norm(s):
    return _norm(unicodedata.normalize('NFKC', s))


def _ctx(s, i, w=16):
    a = max(0, i - w)
    b = min(len(s), i + w + 1)
    return ('…' if a > 0 else '') + s[a:b] + ('…' if b < len(s) else '')


def _best_ocr(pn, ocr_n):
    best, bestr = None, -1.0
    for t in ocr_n:
        r = difflib.SequenceMatcher(None, pn, t).ratio()
        if r > bestr:
            bestr, best = r, t
    return best, bestr


def boundary_ok(side, pn, ocr_n):
    """F1 源位置闸门（字符级）：违规字符必须等于**最相似 OCR 行**的行首/末字符，
    或等于同页某一相似行（ratio>=0.45）的行首/末字符（排除 OCR 行合并/切分）。
    这正是 t5 F1 的要求：「字符不在源行首/末而产物出现在行首/末 -> B」。"""
    if not pn:
        return False
    ch = pn[0] if side == 'start' else pn[-1]
    best, bestr = _best_ocr(pn, ocr_n)
    if best:
        bch = best[0] if side == 'start' else best[-1]
        if bch == ch:
            return True
    for t in ocr_n:
        if not t:
            continue
        if (t[0] if side == 'start' else t[-1]) != ch:
            continue
        if difflib.SequenceMatcher(None, pn, t).ratio() >= 0.45:
            return True
    return False


def misread_fix_ok(side, pn, ocr_n):
    """OCR 把行首/列首的「一」误读成汉字、渲染端按墨迹改回引号 -> C_fixed（不计 B）。"""
    if not pn:
        return False
    if side == 'start':
        if pn[0] not in OPENERS | CLOSERS:
            return False
        rest = pn[1:min(12, len(pn))]
        return any(len(t) > len(rest) and t[0] in MISREAD_FIRST and t[1:1 + len(rest)] == rest
                   for t in ocr_n)
    if pn[-1] not in OPENERS | CLOSERS:
        return False
    rest = pn[max(0, len(pn) - 12):-1]
    return any(len(t) > len(rest) and t[-1] in MISREAD_FIRST and t[-1 - len(rest):-1] == rest
               for t in ocr_n)


def _pick_mark_row(pl, ocr_texts):
    """产品列文本 -> 末行 OCR 行下标（用于取源图末格行盒）。纯函数，便于单测。
    后缀候选：原样 / 剥句末标点 / 剥句末标点+误读「一0〇」；取最长命中；全不中回退最相似行。"""
    pn = norm(pl).rstrip('」』﹂﹄')
    best, best_len = None, -1
    for i, t in enumerate(ocr_texts):
        tn = norm(t)
        for cand in (tn, tn.rstrip('。！？；'), tn.rstrip('一0〇'), tn.rstrip('。！？；一0〇')):
            if cand and pn.endswith(cand) and len(cand) > best_len:
                best, best_len = i, len(cand)
                break
    if best is None and ocr_texts:
        best = max(range(len(ocr_texts)),
                   key=lambda i: difflib.SequenceMatcher(None, norm(pl), norm(ocr_texts[i])).ratio())
    return best


def source_last_cell_mark(book, page, idx, mode, plines, lines, co, src_doc, cache):
    """F3/§5.2：产物该行/列末若是闭引号，核源图最后一格是否有「宽而扁」横条。
    返回 (w,h) 或 None。只对末字符是闭符的项有意义。"""
    if not plines or not (0 <= idx < len(plines)):
        return None
    pl = plines[idx]
    if not pl or pl[-1] not in CLOSERS:
        return None
    key = (page, idx)
    if key in cache:
        return cache[key]
    ocr = lines.get(str(page - 1), [])
    coords = co.get(str(page - 1), []) if co else []
    cands = [(i, t) for i, t in enumerate(ocr) if t]
    if not cands or not coords:
        cache[key] = None
        return None
    # t13：合并列（OCR 两行合成一列）的补字在**末行**行盒下方 —— 先找产品列文本的
    #   最长后缀行（= 该列最后一条 OCR 行），找不到再按相似度选。否则会拿第一行的
    #   行盒去找尾格墨，漏判 QSF 的合法补形（C_fixed 被误记 B）。
    # 末行行盒选择（t16/F2）：产品列末字是闭引号时先剥掉；OCR 末行可能尾随句末标点或被误读的
    #   「一/0/〇」（例 p1365：OCR `…自防。一`、产品 `…自防。﹂`），三种候选后缀都要试，
    #   否则后缀不匹配会回退「最相似行」取错行盒 -> 源墨漏检 -> C_fixed 误记 B。
    k = _pick_mark_row(pl, [t for _i, t in cands])
    best = cands[k] if k is not None else None
    box = coords[best[0]] if best[0] < len(coords) else None
    if not box:
        cache[key] = None
        return None
    xs = [q[0] / 2.0 for q in box]; ys = [q[1] / 2.0 for q in box]
    x0, _y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    sts = []
    for t, pp in zip(ocr, coords):
        t = str(t).replace('\n', '')
        if len(t) >= 8 and pp:
            yy = [q[1] / 2.0 for q in pp]
            sts.append((max(yy) - min(yy)) / len(t))
    sts.sort()
    step = sts[len(sts) // 2] if sts else 25.0
    import numpy as np
    from scipy import ndimage
    clip = fitz.Rect(x0 - 1, y1 - step * 1.02, x1 + 1, y1 + 1)
    pm = src_doc[page - 1].get_pixmap(clip=clip, dpi=600)
    a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)[:, :, :3].mean(axis=2)
    m = a < (float(np.median(a)) - 20)
    lab, _ = ndimage.label(m)
    kk = 72.0 / 600.0
    out = None
    for i, s in enumerate(ndimage.find_objects(lab), 1):
        if s is None:
            continue
        yy, xx = s
        w = (xx.stop - xx.start) * kk
        h = (yy.stop - yy.start) * kk
        if w >= WIDE * step and 1.0 <= h <= FLAT * step:
            out = (round(w, 1), round(h, 1))
            break
    cache[key] = out
    return out


def classify(items, plines, ocr_lines, book, page, mode, lines, co, src_doc, cache):
    out = []
    ocr_n = [norm(t) for t in ocr_lines]
    for it in items:
        k = it['check']
        if k == 'trail_width':
            out.append(dict(it, cls='R', why='§5.1.10 报告项'))
            continue
        if k == 'ocr_miss_punct':
            out.append(dict(it, cls=('C' if it.get('sub') == 'product_missing' else 'C_fixed'),
                            why='源图有墨、OCR 文本无、' + ('产物缺' if it.get('sub') == 'product_missing' else '渲染端已补')))
            continue
        if k == 'dash_lead':
            legal = it.get('sub') == 'legal'
            out.append(dict(it, cls=('D_legal' if legal else 'D_ambiguous'),
                            why=('破折号在行首合法(§4.10.3.9/4.10.3.10)' if legal
                                 else '单个 — 无法判破折号/一字线，只报告')))
            continue
        idx = it.get('idx', -1)
        if not (0 <= idx < len(plines)):
            out.append(dict(it, cls='?', why='product line not found'))
            continue
        pn = norm(plines[idx])
        if k == 'pair_balance':
            if it.get('carry'):
                out.append(dict(it, cls='K', why='相邻页/段边界有同类型对偶符（合法 carry）'))
                continue
            hint = it.get('carry_hint')
            if hint == 'weak':
                out.append(dict(it, cls='K_weak', why='相邻页有对偶符但不在边界行/列（弱证据）'))
                continue
            if hint == 'none':
                out.append(dict(it, cls='K_invalid', why='相邻页完全没有同类型对偶符（不成立 carry）'))
                continue
            if it.get('sub') == 'unmatched_open':
                out.append(dict(it, cls='O', why='未配对 open 残差（多段引文合法 / 缺闭引号见 C）'))
                continue
            # unmatched_close：char 是否只在产物行（delete 块）-> B；否则 A
            best, bestr = _best_ocr(pn, ocr_n)
            ops = difflib.SequenceMatcher(None, pn, best or '').get_opcodes() if best else []
            ci = it.get('pos', 0)
            tag = None
            for op in ops:
                if op[1] <= ci < op[2]:
                    tag = op[0]
                    break
            if tag == 'delete':
                mk = source_last_cell_mark(book, page, idx, mode, plines, lines, co, src_doc, cache)
                if mk:
                    out.append(dict(it, cls='C_fixed', why='源图最后一格有宽扁横条 %s，OCR 漏、渲染端补' % (mk,)))
                else:
                    out.append(dict(it, cls='B', why='闭符只在产物行（OCR 行无）且源图最后一格无闭引号墨条'))
            else:
                out.append(dict(it, cls='A', why='闭符在同页 OCR 行文本内（源书自身配对/跨页残留）'))
            continue
        if k in ('dash_split', 'ellipsis_split'):
            ch = it['char']
            joiner = ch + ch
            if any(joiner in t for t in ocr_n):
                out.append(dict(it, cls='B', why='源 OCR 行内两连字符相邻，产物拆到两行'))
            else:
                out.append(dict(it, cls='A', why='源书自身在两行边界'))
            continue
        # line_start / line_end / pair_split：F1 源位置闸门
        pos = it.get('pos', 0)
        side = 'start' if pos <= 0 else 'end'
        if boundary_ok(side, pn, ocr_n):
            out.append(dict(it, cls='A', why='产物行首/末文本与某 OCR 行首/末一致（源书边界）'))
        elif misread_fix_ok(side, pn, ocr_n):
            out.append(dict(it, cls='C_fixed', why='OCR 把行首/末引号误读成汉字，渲染端按墨迹改回'))
        else:
            best, bestr = _best_ocr(pn, ocr_n)
            ch = it.get('char', '')
            present = any(norm(ch) in t for t in ocr_n)
            out.append(dict(it, cls='B',
                            why=('字符在 OCR 行中间（不在源行首/末）：产物断行甩到边界' if present
                                 else '字符不在 OCR 行：渲染端插入'),
                            align_ratio=round(bestr, 3)))
    return out


def punct_diff(plines, ocr_lines, page, ratio_min=0.35):
    out = []
    ocr_n = [norm(t) for t in ocr_lines]
    for idx, pfull in enumerate(plines):
        pn = norm(pfull)
        if not pn:
            continue
        best, bestr = _best_ocr(pn, ocr_n)
        if best is None or bestr < ratio_min:
            continue
        for tag, a0, a1, b0, b1 in difflib.SequenceMatcher(None, pn, best).get_opcodes():
            if tag == 'delete':
                for j in range(a0, a1):
                    if pn[j] in PUNCT_ALL:
                        out.append(dict(check='punct_diff', sub='insert', page=page, idx=idx, pos=j,
                                        char=pn[j], context=_ctx(pn, j), clause='§5.1.3', carry='',
                                        cls='B', why='产物有、OCR 行无（渲染端插入/重复；诊断项）',
                                        align_ratio=round(bestr, 3)))
            elif tag == 'insert':
                for j in range(b0, b1):
                    if best[j] in PUNCT_ALL:
                        out.append(dict(check='punct_diff', sub='delete', page=page, idx=idx, pos=-1,
                                        char=best[j], context=_ctx(best, j), clause='§5.1.3', carry='',
                                        cls='B', why='OCR 行有、产物行无（产物丢标点；诊断项）',
                                        align_ratio=round(bestr, 3)))
    return out



def main():
    import argparse
    ap = argparse.ArgumentParser(description='标点审计条目 A/B/C 归因')
    ap.add_argument('--audit', required=True, help='punct_audit.py 输出的 JSON')
    ap.add_argument('--pdf', required=True, help='产物 PDF')
    ap.add_argument('--lines', required=True, help='OCR 行 JSON')
    ap.add_argument('--mode', choices=['h', 'v'], required=True)
    ap.add_argument('--coords', default='', help='OCR coords JSON（竖排源图复核用）')
    ap.add_argument('--src-pdf', default='', help='源图 PDF（竖排源图复核用）')
    ap.add_argument('--out', required=True, help='归因结果 JSON')
    ap.add_argument('--diff-out', default='', help='punct_diff 诊断项 JSON（可选）')
    ap.add_argument('--label', default='')
    args = ap.parse_args()

    rep = json.load(open(args.audit, encoding='utf-8'))
    lines = {str(k): [str(t).replace('\n', '') for t in v]
             for k, v in json.load(open(args.lines, encoding='utf-8')).items()}
    co = json.load(open(args.coords, encoding='utf-8')) if args.coords else None
    doc = fitz.open(args.pdf)
    pages_plines = {}
    for pi in range(len(doc)):
        ls = extract_h(doc[pi]) if args.mode == 'h' else extract_v(doc[pi])
        pages_plines[pi + 1] = [ln['text'] for ln in ls]
    doc.close()
    src_doc = fitz.open(args.src_pdf) if (args.mode == 'v' and args.src_pdf) else None
    cache = {}
    by_page = {}
    for it in rep['items']:
        by_page.setdefault(it['page'], []).append(it)
    out, diff = [], []
    for pg, its in sorted(by_page.items()):
        out += classify(its, pages_plines.get(pg, []), lines.get(str(pg - 1), []),
                        args.label or args.pdf, pg, args.mode, lines, co, src_doc, cache)
        diff += punct_diff(pages_plines.get(pg, []), lines.get(str(pg - 1), []), pg)
    out += diff
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump(out, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if args.diff_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.diff_out)), exist_ok=True)
        json.dump(diff, open(args.diff_out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    c = Counter(x.get('cls') for x in out if x['check'] not in ('trail_width', 'punct_diff'))
    print('%s: items=%d diff=%d ?=%d' % (args.label or args.pdf, len(out), len(diff),
                                          c.get('?', 0)))
    print('classes:', dict(c))
    return 0


if __name__ == '__main__':
    sys.exit(main())
