#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""punct_fn_audit.py — wz7 8 页 gold 的标点 FN 逐条根因旁路审计（t258）。

只读 gold/PDF/OCR/源图，不改 punct_eval 计数口径；输出 item 级 JSON + 报告 + 裁片。
"""
import argparse
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import punct_bench as pb

PUNCT_CHARS = {
    'period': '。', 'comma': '，', 'enumeration_comma': '、', 'semicolon': '；',
    'colon': '：', 'question': '？', 'exclamation': '！', 'quote_open': '“',
    'quote_close': '”', 'bracket_present': '（', 'dash': '—', 'ellipsis': '…',
    'ring': '○', 'booktitle_open': '《', 'booktitle_close': '》',
}


def _norm(s):
    return pb._seq_norm(s or '')


def _context(anchor, gap, width=8):
    a = max(0, gap - width); b = min(len(anchor), gap + width)
    return ''.join(anchor[a:gap]), ''.join(anchor[gap:b])


def _ocr_page_text(lines, page):
    # 0-based key 优先；同时兼容 1-based
    for k in (str(page - 1), str(page)):
        if k in lines:
            return ' '.join(str(x) for x in lines[k]), lines[k]
    return '', []


def _line_with_context(lines, page, before, after):
    """找包含上下文最长的 OCR 行。"""
    key = str(page - 1) if str(page - 1) in lines else (str(page) if str(page) in lines else None)
    if key is None:
        return None, -1
    best = (None, -1, -1)
    probe = (before[-8:] + after[:8]) if before or after else ''
    pset = set(_norm(probe))
    b8 = _norm(before)[-8:]; a8 = _norm(after)[:8]
    for i, t in enumerate(lines[key]):
        nt = _norm(str(t))
        if not nt:
            continue
        score = len(pset & set(nt))
        if (b8 and b8 in nt) or (a8 and a8 in nt):
            score += 100
        for L in range(min(len(probe), 8), 2, -1):
            if probe[:L] in nt or probe[-L:] in nt:
                score += 20; break
        if score > best[2]:
            best = (str(t), i, score)
    return best[0], best[1]


def _pdf_page_text(chars, page):
    return ''.join(str(c[0]) for c in chars.get(page, []))


def _char_present_near(text, ch, before, after):
    """严格 gap 判定：before/after 拼接处就是该标点才算 present。"""
    if not ch:
        return False
    n = _norm(text)
    b = _norm(before); a = _norm(after)
    for cut in range(min(len(b), 8), 1, -1):
        pos = n.find(b[-cut:] + a[:cut]) if a else n.find(b[-cut:])
        if pos >= 0:
            return n[pos + cut:pos + cut + 1] == ch
    return False


def _crop_ink(src, page, poly, out_path, line_text='', ocr_max=None, before='', after='', label=''):
    """紧裁：6×字高区域，居中期望位置；坐标异常时退回 OCR 行 bbox/page 中心。"""
    try:
        import fitz
        from PIL import Image, ImageDraw
        doc = fitz.open(src)
        if page - 1 >= len(doc):
            return 'uncertain', None
        p = doc[page - 1]
        pw, ph = p.rect.width, p.rect.height
        # 字符高估计
        ch = 0
        if poly:
            ys = [q[1] for q in poly]; xs = [q[0] for q in poly]
            h = max(ys) - min(ys); w = max(xs) - min(xs)
            ch = (h / max(1, len(line_text))) if h > w else (w / max(1, len(line_text)))
        ch = max(18.0, min(80.0, ch or 30.0))
        if poly and ocr_max:
            _mx, _my = max(1.0, ocr_max[0]), max(1.0, ocr_max[1])
            _sx = pw / _mx if _mx > pw * 1.05 else 1.0
            _sy = ph / _my if _my > ph * 1.05 else 1.0
            poly = [(q[0] * _sx, ph - q[1] * _sy) for q in poly]  # OCR y 为自下而上
            ch = ch * min(_sx, _sy)
        # 期望位置：在线内找 before 尾部/after 头部，按竖排/横排比例定位
        ex = ey = None
        if poly:
            xs = [q[0] for q in poly]; ys = [q[1] for q in poly]
            x0p, x1p, y0p, y1p = min(xs), max(xs), min(ys), max(ys)
            frac = 0.5
            raw = line_text or ''
            b = (before or '')[-8:]; a = (after or '')[:8]
            pos = -1
            if b and b in raw:
                pos = raw.find(b) + len(b)
            elif a and a in raw:
                pos = raw.find(a)
            if pos >= 0 and len(raw) > 1:
                frac = max(0.0, min(1.0, pos / float(len(raw))))
            if y1p - y0p >= x1p - x0p:   # 竖排: 上->下
                cx = (x0p + x1p) / 2; cy = y0p + frac * (y1p - y0p)
            else:
                cx = x0p + frac * (x1p - x0p); cy = (y0p + y1p) / 2
        else:
            cx, cy = pw / 2, ph / 2
        if not (0 <= cx <= pw and 0 <= cy <= ph):
            cx, cy = pw / 2, ph / 2
        half = 3.0 * ch
        x0, y0 = max(0, cx - half), max(0, cy - half)
        x1, y1 = min(pw, cx + half), min(ph, cy + half)
        if x1 - x0 < 40 or y1 - y0 < 40:
            x0, y0 = max(0, cx - 60), max(0, cy - 60); x1, y1 = min(pw, cx + 60), min(ph, cy + 60)
        clip = fitz.Rect(x0, y0, x1, y1)
        pix = p.get_pixmap(clip=clip, matrix=fitz.Matrix(4, 4))
        if out_path:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            pix.save(out_path)
            # 叠红框+刻度
            im = Image.open(out_path).convert('RGB'); d = ImageDraw.Draw(im)
            W, H = im.size
            if label:
                d.rectangle([0, 0, W, 18], fill=(0, 0, 0))
                d.text((3, 3), label[:80], fill=(255, 255, 255))
            rx = (cx - x0) * 4; ry = (cy - y0) * 4
            rw = min(W, 2.0 * ch * 4); rh = min(H, 2.0 * ch * 4)
            d.rectangle([rx - rw/2, ry - rh/2, rx + rw/2, ry + rh/2], outline='red', width=3)
            for gx in range(0, W, max(10, W//6)):
                d.line([(gx, 0), (gx, 10)], fill=(180,180,180), width=1)
                d.text((gx+2, 12), str(int(x0 + gx/4)), fill=(120,120,120))
            for gy in range(0, H, max(10, H//6)):
                d.line([(0, gy), (10, gy)], fill=(180,180,180), width=1)
                d.text((12, gy+2), str(int(y0 + gy/4)), fill=(120,120,120))
            im.save(out_path)
        samples = pix.samples; n = len(samples)
        dark = sum(1 for b in samples if b < 110)
        ink = 'ink' if dark > max(8, n * 0.003) else 'no_ink'
        return ink, out_path
    except Exception:
        return 'uncertain', None


def audit(args):
    gold = pb.load_content_gold(args.gold, args.book)
    coords = json.load(open(args.coords, encoding='utf-8'))
    lines = json.load(open(args.lines, encoding='utf-8'))
    chars = pb.pdf_char_map(args.pdf)
    items = []
    order_base = 0
    for git in gold:
        page = int(git['page']); axis = git.get('axis') or 'vertical'
        w, h = (fitz_size(args.pdf, page) if False else (0, 0))
        import fitz
        doc = fitz.open(args.pdf); w, h = doc[page - 1].rect.width, doc[page - 1].rect.height; doc.close()
        pred = pb.reading_order(chars.get(page, []), w, h, axis, git.get('exclude'), {})
        gtxt = git.get('text') or ''
        gt = _norm(gtxt); pt = _norm(pred or '')
        ga, gtok = pb.seq_tokens(gt); pa, ptok = pb.seq_tokens(pt)
        sm = difflib.SequenceMatcher(None, ga, pa, autojunk=False)
        gap_map = {}
        blocks = sm.get_matching_blocks()
        for bl in blocks:
            for k in range(bl.size): gap_map[bl.a + k] = bl.b + k
        if blocks and blocks[-1].a + blocks[-1].size == len(ga) and blocks[-1].b + blocks[-1].size == len(pa):
            gap_map[len(ga)] = len(pa)
        used = set()
        ocr_text, _ = _ocr_page_text(lines, page)
        pdf_text = _pdf_page_text(chars, page)
        for gap, cls, value, order, extra in gtok:
            bump = None
            g2 = gap_map.get(gap)
            cands = [x for x in ptok if x[0] == g2 and id(x) not in used] if g2 is not None else []
            hit = next((x for x in cands if x[1] == cls), None)
            if hit is None:
                hit = next((x for x in cands if pb._seq_group(x[1]) == pb._seq_group(cls)), None)
            if hit is not None:
                used.add(id(hit))
                if hit[1] == cls:
                    continue
                # 类型错：仍算 FN（gold 类漏识）
            before, after = _context(ga, gap)
            line_txt, line_idx = _line_with_context(lines, page, before, after)
            line_txt = line_txt or ''
            target_ch = value or PUNCT_CHARS.get(cls, '')
            # OCR 侧判定
            ocr_has_target = _char_present_near(line_txt, target_ch, before, after) if target_ch else False
            pdf_has_target = _char_present_near(pdf_text, target_ch, before, after) if target_ch else False
            other_punct = []
            for ch in '。，、；：？！“”‘’（）〔〕【】《》〈〉—…':
                if ch != target_ch and _char_present_near(line_txt, ch, before, after):
                    other_punct.append(ch)
            if not ocr_has_target and other_punct:
                attr = 'ocr_wrong_char'; evidence = 'OCR line has %s, no %s' % (''.join(other_punct[:3]), target_ch)
            elif not ocr_has_target:
                attr = 'ocr_absent'; evidence = 'no target char in OCR line/context'
            elif (not pdf_has_target):
                attr = 'render_dropped'; evidence = 'OCR has %s but PDF text lacks it' % target_ch
            elif pdf_has_target:
                attr = 'reading_order'; evidence = 'PDF has %s but sequence pairing failed' % target_ch
            else:
                attr = 'filtered_furniture'; evidence = 'filtered/excluded context'
            # OCR coords 找 poly（粗略：行索引→coords）
            poly = None
            if line_idx >= 0:
                key = str(page - 1) if str(page - 1) in coords else (str(page) if str(page) in coords else None)
                if key and line_idx < len(coords[key]):
                    poly = coords[key][line_idx]
            crop = os.path.join(args.crops_dir, 'fn_%03d_p%04d_%s_%s.png' % (len(items) + 1, page, cls, attr)) if args.crops_dir else None
            _ck = str(page - 1) if str(page - 1) in coords else (str(page) if str(page) in coords else None)
            _ocr_max = None
            if _ck:
                _cc = coords[_ck]
                _xs = [q[0] for poly0 in _cc for q in poly0] or [0]
                _ys = [q[1] for poly0 in _cc for q in poly0] or [0]
                _ocr_max = (max(_xs), max(_ys))
            ink, cpath = _crop_ink(args.src_pdf, page, poly, crop, line_txt, _ocr_max, before, after,
                         label='%s p%d %s %s' % ('fn_%03d' % (len(items) + 1), page, cls, attr))
            items.append(dict(
                id='fn_%03d' % (len(items) + 1), page=page, axis=axis,
                reading_order_pos=order, gap=gap, cls=cls, gold_value=target_ch,
                gold_context=before + '【' + after, gold_before=before, gold_after=after,
                ocr_line=line_txt[:160], ocr_line_index=line_idx,
                attribution=attr, evidence=evidence, ink=ink, crop=cpath, crop_path=cpath,
                pred_confusion=(hit[1] if hit is not None else None),
                poly=[[round(float(x), 1), round(float(y), 1)] for x, y in (poly or [])][:8],
            ))
        order_base += len(gtok)
    return items


def fitz_size(pdf, page):
    import fitz
    d = fitz.open(pdf); r = d[page - 1].rect; d.close(); return r.width, r.height


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--gold', required=True)
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--coords', required=True)
    ap.add_argument('--lines', required=True)
    ap.add_argument('--src-pdf', default='')
    ap.add_argument('--book', default='wz7')
    ap.add_argument('--out-json', '--out', dest='out_json', required=True)
    ap.add_argument('--crops-dir', default='output/wz7/punct_fn_crops')
    args = ap.parse_args(argv)
    if not args.src_pdf:
        args.src_pdf = os.path.join('source_pdf', '%s.pdf' % args.book)
    if not args.crops_dir:
        args.crops_dir = os.path.join('output', args.book, 'punct_fn_crops')
    items = audit(args)
    os.makedirs(os.path.dirname(os.path.abspath(args.out_json)) or '.', exist_ok=True)
    json.dump(dict(schema_version='punct-fn-audit-v1', book=args.book, count=len(items), items=items),
              open(args.out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    from collections import Counter
    print('items=%d attribution=%s ink=%s' % (len(items), dict(Counter(x['attribution'] for x in items)),
                                              dict(Counter(x['ink'] for x in items))))
    # 无效裁片生成占位图（每个 FN 一张）
    try:
        from PIL import Image, ImageDraw
        for x in items:
            cp = x.get('crop')
            if not cp:
                continue
            ok = False
            try:
                Image.open(cp).verify(); ok = True
            except Exception:
                ok = False
            if not ok:
                im = Image.new('RGB', (240, 120), 'white'); d = ImageDraw.Draw(im)
                d.text((8, 20), '%s p%s %s' % (x['id'], x['page'], x['ink']), fill='black')
                d.text((8, 60), 'no valid crop', fill='red')
                im.save(cp)
    except Exception as e:
        print('placeholder skipped:', e)
    # 拼图（≤40 张）
    try:
        from PIL import Image
        paths = [x['crop'] for x in items if x.get('crop') and os.path.exists(x['crop'])][:40]
        if paths:
            ims = []
            for p in paths:
                try:
                    ims.append(Image.open(p).convert('RGB'))
                except Exception:
                    pass
            th = 120; ims = [im.resize((max(1, int(im.width * th / im.height)), th)) for im in ims]
            cols = 6; rows = (len(ims) + cols - 1) // cols
            cw = max(im.width for im in ims); 
            out = Image.new('RGB', (cols * cw, rows * th), 'white')
            for i, im in enumerate(ims):
                out.paste(im, ((i % cols) * cw, (i // cols) * th))
            mp = os.path.join(os.path.dirname(os.path.abspath(args.out_json)), 'punct_fn_montage.png')
            out.save(mp); print('montage=%s n=%d' % (mp, len(ims)))
    except Exception as e:
        print('montage skipped:', e)
    for x in items[:10]:
        print(x['id'], x['page'], x['cls'], x['attribution'], x['ink'], x['gold_context'][:40])
    return 0


if __name__ == '__main__':
    sys.exit(main())
