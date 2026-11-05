#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""punct_audit.py — 标点符号禁则/配对审计器（GB/T 15834—2011）

规则表（可执行口径）：spec/governance/PUNCTUATION.md
关联报告：docs/battle2_punct_audit.md

用法：
  /usr/bin/python3 src/tools/punct_audit.py <out.pdf> --mode h|v [--coords coords.json] \
      [--json out.json] [--md out.md] [--label 书名] [--max-items 50] [--pages 1-100]

检查项（kind -> 条款）：
  line_start     行/列首字符是禁则字符            §5.1.1/5.1.2/5.1.3/5.1.6/5.1.7/5.1.9
  line_end       行/列末字符是禁则字符            §5.1.3/5.1.9
  pair_split     配对符前一半在行/列末、后一半在行/列首（带 pair 类型） §5.1.3
  dash_lead      行/列首是破折号「——」：legal（§4.10.3.9/§4.10.3.10，不计违规）/
                 ambiguous（单个「—」无法判破折号还是一字线，只报告）
  dash_split     破折号被行/列边界拆开（含跨页）   §5.1.4
  ellipsis_split 省略号被行/列边界拆开（含跨页）   §5.1.5
  trail_width    横排行末全角标点未压缩（报告项） §5.1.10
  pair_balance   未配对的 open/close（页内栈；跨页 carry 单独标） §4.8.3.5/§5.1.3

carry 口径（不计入违规，单独登记）：
  · 行/列位于页边界或横排段边界，且相邻单元的首/末字符与本字符构成**同一对的延续**
    -> carry='page'/'paragraph' + carry_evidence='pair_continuation'
  · 仅位于边界但无配对延续证据 -> carry='' （照常计违规）；同时记 boundary_hint 供报告复核

可复现：无时间戳/随机；items 按 (page, idx, pos, check) 稳定排序；同一输入同一输出。
"""
import argparse
import hashlib
import json
import os
import statistics
import sys

import fitz

# ---------- 标点集合（GB/T 15834-2011；条款见 spec/governance/PUNCTUATION.md） ----------
# 配对：(open, close, name, clause)
PAIRS = [
    ('（', '）', '圆括号', '§4.9.2'),
    ('(', ')', '圆括号(半角)', '§4.9.2'),
    ('［', '］', '方括号', '§4.9.2'),
    ('[', ']', '方括号(半角)', '§4.9.2'),
    ('〔', '〕', '六角括号', '§4.9.2'),
    ('【', '】', '方头括号', '§4.9.2'),
    ('《', '》', '双书名号', '§4.15.2'),
    ('〈', '〉', '单书名号', '§4.15.2'),
    ('“', '”', '双引号', '§4.8.2'),
    ('‘', '’', '单引号', '§4.8.2'),
    ('「', '」', '角括号(源书常用)', '§4.8.1'),
    ('『', '』', '双角括号(源书常用)', '§4.8.1'),
    ('﹃', '﹄', '双引号(竖排)', '§5.2.3'),
    ('﹁', '﹂', '单引号(竖排)', '§5.2.3'),
    ('︵', '︶', '圆括号(竖排)', '§5.2.3'),
    ('︗', '︘', '方括号(竖排)', 'Unicode 竖排形（GB/T 未明示）'),
    ('︹', '︺', '六角/方头括号(竖排)', 'Unicode 竖排形（GB/T 未明示）'),
    ('︽', '︾', '双书名号(竖排)', 'Unicode 竖排形（GB/T 未明示）'),
    ('︿', '﹀', '单书名号(竖排)', 'Unicode 竖排形（GB/T 未明示）'),
]
PAIR_OF_OPEN = {o: (c, n, cl) for o, c, n, cl in PAIRS}
PAIR_OF_CLOSE = {c: (o, n, cl) for o, c, n, cl in PAIRS}
OPENERS = set(PAIR_OF_OPEN)
CLOSERS = set(PAIR_OF_CLOSE)
ALL_PAIRS = OPENERS | CLOSERS

POINT_MARKS = {'。': '§5.1.1', '，': '§5.1.1', '、': '§5.1.1', '；': '§5.1.1', '：': '§5.1.1',
               '？': '§5.1.2', '！': '§5.1.2',
               # 旧式/异体点号（源书可能用；按同条处理）
               '．': '§5.1.1', '﹐': '§5.1.1', '﹑': '§5.1.1', '﹔': '§5.1.1', '﹕': '§5.1.1',
               '﹖': '§5.1.2', '﹗': '§5.1.2'}
# 破折号 vs 连接号（F2）：§5.1.6 只管连接号「不出现在一行之首」；
# 破折号「——」在行首是合法的（GB/T §4.10.3.9 副标题、§4.10.3.10 出处示例本身就是行首），
# 破折号只受 §5.1.4「不能中间断开」约束（见 dash_split）。
EM_DASH = set('—―')                # 破折号（——；同形的一字线单用时需上下文判定）
CONNECTOR_CHARS = set('~～‐-–')     # 连接号（短横线/浪纹线；一字线「—」与破折号同形，单用时 ambiguous）
DASH_CHARS = EM_DASH | CONNECTOR_CHARS
ELL_CHARS = set('…⋯')               # 省略号
MIDDLE_DOTS = set('·・‧')           # 间隔号 §5.1.7
SLASHES = set('/／')                 # 分隔号 §5.1.9

START_FORBIDDEN = set(POINT_MARKS) | CLOSERS | CONNECTOR_CHARS | MIDDLE_DOTS | SLASHES
END_FORBIDDEN = set(OPENERS) | SLASHES

CLAUSE_START = {}
CLAUSE_START.update(POINT_MARKS)
for _o, _c, _n, _cl in PAIRS:
    CLAUSE_START[_c] = '§5.1.3'
for _c in CONNECTOR_CHARS:
    CLAUSE_START.setdefault(_c, '§5.1.6')
for _c in MIDDLE_DOTS:
    CLAUSE_START[_c] = '§5.1.7'
for _c in SLASHES:
    CLAUSE_START[_c] = '§5.1.9'
CLAUSE_END = {}
for _o, _c, _n, _cl in PAIRS:
    CLAUSE_END[_o] = '§5.1.3'
for _c in SLASHES:
    CLAUSE_END[_c] = '§5.1.9'

TRAIL_WIDTH_MIN = 0.75   # §5.1.10 报告项：行末全角标点 advance/em >= 0.75 -> 未压缩
# 版權/印刷信息页（頁 554/1163 型）不是正文：**仅竖排**审计默认跳过；横排默认纳入（F1 修正：
#   旧判据「关键词 >= 3 次」会把正文页误伤 —— 引文/经文里出现「出版」「印刷」很常见，
#   t14 实测误跳 wz1 30 页 / wz4 265 页 / wz7 p82/p915）。新判据 = 多关键词联合 + 页型/版式特征。
# --include-nonbody 关闭过滤器（两种模式都纳入）。
NONBODY_KW = ('發行', '出版', '印刷', '製版', '裝訂', '經銷', '版權', '局版',
              '定價', '帳戶', '電話', '地址')

def _is_nonbody_page(lines, mode):
    """版權/印刷信息页判据（t16/F1 收紧）。
    条件：①仅竖排（横排默认 include，返回 False）；②页文本命中 >= 3 个**不同**关键词；
    ③页型/版式特征：整页文本 <= 300 字且行数 <= 12（版权页 = 短小页；正文页整页 500-800 字）。
    正文页即使提到「出版/印刷」也会因整页字数被排除（t14 误伤 p82/p915 的回归由字数挡住）。"""
    if mode != 'v':
        return False
    txt = ''.join(l['text'] for l in lines)
    if len([k for k in NONBODY_KW if k in txt]) < 3:
        return False
    if len(txt) > 300:
        return False
    if len(lines) > 12:
        return False
    return True

# 竖排/横排标点形态归一（源 OCR 与产物可能用不同形态；用于源图漏识标记的产物对账）
_NORM_TBL = str.maketrans({'﹁': '「', '﹂': '」', '﹃': '『', '﹄': '』',
                           '︵': '（', '︶': '）', '︽': '《', '︾': '》',
                           '︿': '〈', '﹀': '〉', '︗': '［', '︘': '］',
                           '︹': '〔', '︺': '〕'})
def _norm(s):
    return s.translate(_NORM_TBL)


# ---------- 文本层提取 ----------
def _chars_of(line):
    out = []
    for sp in line['spans']:
        for ch in sp['chars']:
            c = ch['c']
            if c.isspace():
                continue
            out.append(dict(c=c, bbox=[round(v, 2) for v in ch['bbox']],
                            origin=[round(v, 2) for v in ch['origin']],
                            size=round(float(sp['size']), 2)))
    return out


def extract_h(page):
    """横排：rawdict 的 line 序列（block 变化 = 新段）。"""
    out = []
    d = page.get_text('rawdict')
    for bi, b in enumerate(d['blocks']):
        if b.get('type') != 0:
            continue
        for li, ln in enumerate(b['lines']):
            chars = _chars_of(ln)
            if not chars:
                continue
            out.append(dict(block=bi, sub=li, chars=chars,
                            text=''.join(c['c'] for c in chars),
                            bbox=[round(v, 2) for v in ln['bbox']]))
    return out


def extract_v(page):
    """竖排：同页字符按 x 聚类成列（容差 = 0.45×中位字宽），列按 x 从右到左，列内按 y。"""
    chars = []
    d = page.get_text('rawdict')
    for b in d['blocks']:
        if b.get('type') != 0:
            continue
        for ln in b['lines']:
            for sp in ln['spans']:
                for ch in sp['chars']:
                    c = ch['c']
                    if c.isspace():
                        continue
                    chars.append(dict(c=c, bbox=[round(v, 2) for v in ch['bbox']],
                                      origin=[round(v, 2) for v in ch['origin']],
                                      size=round(float(sp['size']), 2)))
    if not chars:
        return []
    widths = [c['bbox'][2] - c['bbox'][0] for c in chars if c['bbox'][2] > c['bbox'][0]]
    medw = statistics.median(widths) if widths else 20.0
    tol = max(4.0, 0.45 * medw)
    chars.sort(key=lambda c: (c['origin'][0], c['origin'][1]))
    clusters = []
    for c in chars:
        if clusters and abs(c['origin'][0] - clusters[-1][-1]['origin'][0]) <= tol:
            clusters[-1].append(c)
        else:
            clusters.append([c])
    cols = []
    for cl in clusters:
        cl.sort(key=lambda c: c['origin'][1])
        xs = [c['origin'][0] for c in cl]
        cols.append(dict(x=round(statistics.median(xs), 2), chars=cl,
                         text=''.join(c['c'] for c in cl),
                         block=0, sub=0,
                         bbox=[min(c['bbox'][0] for c in cl), min(c['bbox'][1] for c in cl),
                               max(c['bbox'][2] for c in cl), max(c['bbox'][3] for c in cl)]))
    cols.sort(key=lambda c: -c['x'])          # 竖排：从右到左
    for i, c in enumerate(cols):
        c['idx'] = i
    return cols


def _ctx(text, pos, width=16):
    a = max(0, pos - width)
    b = min(len(text), pos + width + 1)
    return ('…' if a > 0 else '') + text[a:b] + ('…' if b < len(text) else '')


def _neighbor(page_lines, idx, direction):
    """同页相邻行/列（不跨页）。"""
    j = idx + direction
    if 0 <= j < len(page_lines):
        return page_lines[j]
    return None


# ---------- 源图侧「OCR 漏识的列末标点」检查（--src-pdf + --coords + --lines，竖排） ----------
def _box_pt(p):
    xs = [q[0] / 2.0 for q in p]
    ys = [q[1] / 2.0 for q in p]
    return min(xs), min(ys), max(xs), max(ys)


def _page_step(lines, boxes):
    st = []
    for t, p in zip(lines, boxes):
        t = str(t).replace('\n', '')
        if len(t) < 8 or not p:
            continue
        x0, y0, x1, y1 = _box_pt(p)
        st.append((y1 - y0) / len(t))
    if not st:
        return None
    st.sort()
    return st[len(st) // 2]


def source_miss_scan(src, coords, lines, pages, dpi=600, norm=None):
    """源图侧：OCR 行以 。！？ 结尾且文本尾不是引号 -> 在最后一格里找「宽而扁的横条」
    （竖排闭引号 ﹂/」 的形态：w>=0.55*step、h<=0.45*step、位于格子下半）。
    返回 [{page, ocr_row, text, w,h, x,y}]。"""
    import numpy as np
    from scipy import ndimage
    if norm is None:
        def norm(s):
            return s
    kk = 72.0 / dpi
    allst = []
    for k in lines:
        for t, p in zip(lines[k], coords.get(k, []) or []):
            t = str(t).replace('\n', '')
            if len(t) >= 8 and p:
                x0, y0, x1, y1 = _box_pt(p)
                allst.append((y1 - y0) / len(t))
    allst.sort()
    gstep = allst[len(allst) // 2] if allst else 20.0
    hits = []
    for pno in range(pages[0], pages[1] + 1):
        k = str(pno - 1)
        pl = [str(t).replace('\n', '') for t in (lines.get(k) or [])]
        pb = coords.get(k) or []
        step = _page_step(pl, pb) or gstep
        page = src[pno - 1]
        for i, (t, p) in enumerate(zip(pl, pb)):
            if not t or not p or t[-1] not in '。！？':
                continue
            x0, y0, x1, y1 = _box_pt(p)
            clip = fitz.Rect(x0 - 1, y1 - step * 1.02, x1 + 1, y1 + 1)
            if clip.height < 4 or clip.width < 4:
                continue
            pm = page.get_pixmap(clip=clip, dpi=dpi)
            arr = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)[:, :, :3].mean(axis=2)
            m = arr < (float(np.median(arr)) - 20)
            lab, _n = ndimage.label(m)
            for ci, s in enumerate(ndimage.find_objects(lab), 1):
                if s is None:
                    continue
                yy, xx = s
                w = (xx.stop - xx.start) * kk
                h = (yy.stop - yy.start) * kk
                if w < 0.55 * step or h > 0.55 * step or h < 1.5:
                    continue
                cy = clip.y0 + (yy.start + yy.stop) / 2.0 * kk
                if cy <= clip.y0 + clip.height / 2.0 + 0.05 * step:
                    continue
                hits.append(dict(page=pno, ocr_row=i, text=t[-18:], step=round(step, 2),
                                 w=round(w, 1), h=round(h, 1),
                                 x=round(clip.x0 + xx.start * kk, 1),
                                 y=round(clip.y0 + yy.start * kk, 1)))
                break
    return hits


def _product_has_mark(cols, tail, norm):
    """产物列里是否已有该 OCR 行尾之后的闭引号（QSF/渲染端已补）。"""
    nt = norm(tail)
    for c in cols:
        s = norm(c['text'])
        j = s.find(nt)
        if j < 0:
            continue
        after = s[j + len(nt):]
        if after and (after[0] in CLOSERS):
            return True
    return False


# ---------- 审计 ----------
def audit(pdf_path, mode, coords_path='', label='', max_items=80, pages=None,
          src_pdf='', lines_path='', include_nonbody=False):
    doc = fitz.open(pdf_path)
    md5 = hashlib.md5(open(pdf_path, 'rb').read()).hexdigest()
    coords = None
    if coords_path:
        try:
            coords = json.load(open(coords_path, encoding='utf-8'))
        except Exception as e:
            print('[warn] coords 读取失败: %s' % e, file=sys.stderr)
    if mode == 'v' and src_pdf and (coords is None or not lines_path):
        print('[warn] --src-pdf 需要同时给 --coords 与 --lines 才能做源图侧 OCR 漏识检查；'
              '本次只审计文本层（无 ocr_miss_punct）', file=sys.stderr)
    # 先提取所有页的行/列（跨页 carry 需要前/后页首末）
    all_pages = []
    p0, p1 = 1, len(doc)
    if pages:
        p0, p1 = pages
    for pi in range(p0 - 1, min(p1, len(doc))):
        page = doc[pi]
        all_pages.append(extract_h(page) if mode == 'h' else extract_v(page))
    doc.close()

    items = []
    nonbody_pages = []
    source_hits = []
    if mode == 'v' and src_pdf and coords is not None and lines_path:
        try:
            _lines = {str(k): [str(t).replace('\n', '') for t in v]
                      for k, v in json.load(open(lines_path, encoding='utf-8')).items()}
            source_hits = source_miss_scan(fitz.open(src_pdf), coords, _lines,
                                           (p0, min(p1, len(all_pages) + p0 - 1)), norm=_norm)
            print('[src] OCR 漏识标点候选（源图墨迹）: %d 处 / %d 页'
                  % (len(source_hits), len(set(h['page'] for h in source_hits))))
        except Exception as e:
            print('[warn] 源图侧检查失败: %s' % e, file=sys.stderr)
    pair_counts = {}
    for o, c, n, cl in PAIRS:
        pair_counts[n] = dict(open=0, close=0, clause=cl, forms=[o, c])
    page_meta = []

    def _first_line_of(pi):
        return all_pages[pi][0] if pi < len(all_pages) and all_pages[pi] else None

    def _last_line_of(pi):
        return all_pages[pi][-1] if pi < len(all_pages) and all_pages[pi] else None

    for local_pi, lines in enumerate(all_pages):
        pno = p0 + local_pi
        pi_global = pno - 1
        if not include_nonbody and _is_nonbody_page(lines, mode):
            nonbody_pages.append(pno)
            continue
        page_meta.append(dict(page=pno, n_lines=len(lines),
                              n_ocr_lines=(len(coords.get(str(pi_global), []) or [])
                                           if coords is not None else None)))
        page_stacks = {n: [] for _o, _c, n, _cl in PAIRS}
        prev_line = None
        for i, ln in enumerate(lines):
            text = ln['text']
            if not text:
                continue
            chars = ln['chars']
            nxt = _neighbor(lines, i, +1)
            prv = prev_line
            is_first = (i == 0)
            is_last = (i == len(lines) - 1)
            # ---- carry 判定（同页相邻 -> 跨页邻页首/末）----
            carry_start, ev_start, hint_start = '', '', ''
            if is_first:
                prev = _last_line_of(local_pi - 1) if local_pi > 0 else None
                if prev is not None:
                    hint_start = 'page'
                    c0 = chars[0]['c']
                    if c0 in CLOSERS:
                        want = PAIR_OF_CLOSE[c0][0]
                        if prev['text'] and prev['text'][-1] == want:
                            carry_start, ev_start = 'page', 'pair_continuation'
                else:
                    carry_start = 'page'  # 首页首行：无上页可继承，边界本身合法
            carry_end, ev_end, hint_end = '', '', ''
            if is_last:
                nxtp = _first_line_of(local_pi + 1) if local_pi + 1 < len(all_pages) else None
                if nxtp is not None:
                    hint_end = 'page'
                    cN = chars[-1]['c']
                    if cN in OPENERS:
                        want = PAIR_OF_OPEN[cN][0]
                        if nxtp['text'] and nxtp['text'][0] == want:
                            carry_end, ev_end = 'page', 'pair_continuation'
                else:
                    carry_end = 'page'  # 末页末行
            if mode == 'h':
                blk = ln['block']
                if not is_first and prv is not None and prv['block'] != blk:
                    hint_start = hint_start or 'paragraph'
                    c0 = chars[0]['c']
                    if c0 in CLOSERS and prv['text'] and prv['text'][-1] == PAIR_OF_CLOSE[c0][0]:
                        carry_start, ev_start = 'paragraph', 'pair_continuation'
                if nxt is not None and nxt['block'] != blk:
                    hint_end = hint_end or 'paragraph'
                    cN = chars[-1]['c']
                    if cN in OPENERS and nxt['text'] and nxt['text'][0] == PAIR_OF_OPEN[cN][0]:
                        carry_end, ev_end = 'paragraph', 'pair_continuation'
            # ---- 行/列首禁则 ----
            c0 = chars[0]['c']
            if c0 in EM_DASH:
                # F2：破折号「——」行首合法（§4.10.3.9 副标题 / §4.10.3.10 出处）；
                #    单个「—」与连接号的一字线同形，无法纯文本判定 -> ambiguous 只报告
                doubled = len(text) > 1 and text[1] in EM_DASH
                items.append(dict(check='dash_lead', sub=('legal' if doubled else 'ambiguous'),
                                  page=pno, idx=i, pos=0, char=c0,
                                  context=_ctx(text, 0),
                                  clause=('§4.10.3.9/§4.10.3.10' if doubled else '§5.1.6?'),
                                  carry='', carry_evidence='', boundary_hint='',
                                  bbox=chars[0]['bbox'], line=text[:40], pair=None))
            elif c0 in START_FORBIDDEN:
                is_pair = c0 in PAIR_OF_CLOSE
                items.append(dict(check='pair_split' if is_pair else 'line_start',
                                  page=pno, idx=i, pos=0, char=c0,
                                  context=_ctx(text, 0), clause=CLAUSE_START.get(c0, ''),
                                  carry=carry_start, carry_evidence=ev_start,
                                  boundary_hint=hint_start,
                                  bbox=chars[0]['bbox'], line=text[:40],
                                  pair=(PAIR_OF_CLOSE[c0][1] if is_pair else None)))
            # ---- 行/列末禁则 ----
            cN = chars[-1]['c']
            if cN in END_FORBIDDEN:
                is_pair = cN in PAIR_OF_OPEN
                items.append(dict(check='pair_split' if is_pair else 'line_end',
                                  page=pno, idx=i, pos=len(text) - 1, char=cN,
                                  context=_ctx(text, len(text) - 1), clause=CLAUSE_END.get(cN, ''),
                                  carry=carry_end, carry_evidence=ev_end,
                                  boundary_hint=hint_end,
                                  bbox=chars[-1]['bbox'], line=text[-40:],
                                  pair=(PAIR_OF_OPEN[cN][1] if is_pair else None)))
            # ---- 破折号/省略号跨行（同页） ----
            if nxt is not None and nxt['text']:
                if cN in EM_DASH and nxt['text'][0] in EM_DASH:
                    items.append(dict(check='dash_split', page=pno, idx=i, pos=len(text) - 1,
                                      char=cN, context=_ctx(text, len(text) - 1),
                                      clause='§5.1.4', carry=carry_end,
                                      carry_evidence=ev_end, boundary_hint=hint_end,
                                      bbox=chars[-1]['bbox'], line=text[-40:], pair=None))
                if cN in ELL_CHARS and nxt['text'][0] in ELL_CHARS:
                    items.append(dict(check='ellipsis_split', page=pno, idx=i, pos=len(text) - 1,
                                      char=cN, context=_ctx(text, len(text) - 1),
                                      clause='§5.1.5', carry=carry_end,
                                      carry_evidence=ev_end, boundary_hint=hint_end,
                                      bbox=chars[-1]['bbox'], line=text[-40:], pair=None))
            # ---- 跨页破折号/省略号（页末行 -> 下一页首行） ----
            if is_last:
                nxtp = _first_line_of(local_pi + 1) if local_pi + 1 < len(all_pages) else None
                if nxtp is not None and nxtp['text']:
                    if cN in EM_DASH and nxtp['text'][0] in EM_DASH:
                        items.append(dict(check='dash_split', page=pno, idx=i, pos=len(text) - 1,
                                          char=cN, context=_ctx(text, len(text) - 1),
                                          clause='§5.1.4', carry='page',
                                          carry_evidence='page_break', boundary_hint='page',
                                          bbox=chars[-1]['bbox'], line=text[-40:], pair=None))
                    if cN in ELL_CHARS and nxtp['text'][0] in ELL_CHARS:
                        items.append(dict(check='ellipsis_split', page=pno, idx=i, pos=len(text) - 1,
                                          char=cN, context=_ctx(text, len(text) - 1),
                                          clause='§5.1.5', carry='page',
                                          carry_evidence='page_break', boundary_hint='page',
                                          bbox=chars[-1]['bbox'], line=text[-40:], pair=None))
            # ---- 行末全角标点宽度（§5.1.10，报告项；仅横排） ----
            if mode == 'h' and (cN in POINT_MARKS or cN in CLOSERS):
                bb = chars[-1]['bbox']
                em = chars[-1]['size']
                if em > 1:
                    ratio = (bb[2] - bb[0]) / em
                    if ratio >= TRAIL_WIDTH_MIN:
                        items.append(dict(check='trail_width', page=pno, idx=i, pos=len(text) - 1,
                                          char=cN, context=_ctx(text, len(text) - 1),
                                          clause='§5.1.10', carry=carry_end,
                                          carry_evidence=ev_end, boundary_hint=hint_end,
                                          bbox=bb, line=text[-40:], pair=None,
                                          ratio=round(ratio, 3)))
            # ---- 配对计数 + 页内配对栈 ----
            for ci, c in enumerate(text):
                if c in PAIR_OF_OPEN:
                    name = PAIR_OF_OPEN[c][1]
                    pair_counts[name]['open'] += 1
                    page_stacks[name].append(dict(page=pno, idx=i, pos=ci, char=c,
                                                  context=_ctx(text, ci)))
                elif c in PAIR_OF_CLOSE:
                    name = PAIR_OF_CLOSE[c][1]
                    pair_counts[name]['close'] += 1
                    st = page_stacks[name]
                    if st:
                        st.pop()
                    else:
                        # F3：carry 必须验证「对偶符落在相邻页边界行/列（或相邻段末行）」
                        opener = PAIR_OF_CLOSE[c][0]
                        prev_page = all_pages[local_pi - 1] if local_pi > 0 else None
                        valid, hint = '', ''
                        if i <= 2 and prev_page is not None:
                            pl = prev_page[-1]['text'] if prev_page else ''
                            if pl and pl[-1] == opener:
                                valid = 'page'
                            if not valid and mode == 'h' and i > 0 and lines[i]['block'] != lines[i - 1]['block']:
                                if lines[i - 1]['text'] and lines[i - 1]['text'][-1] == opener:
                                    valid = 'paragraph'
                        if not valid and i <= 2 and prev_page is not None:
                            hint = ('weak' if any(opener in x['text'] for x in prev_page) else 'none')
                        items.append(dict(check='pair_balance', sub='unmatched_close',
                                          page=pno, idx=i, pos=ci, char=c,
                                          context=_ctx(text, ci), clause='§5.1.3',
                                          carry=valid,
                                          carry_evidence=('pair_continuation' if valid else ''),
                                          carry_hint=hint,
                                          boundary_hint=('page' if valid == 'page' else
                                                         ('paragraph' if valid == 'paragraph' else '')),
                                          bbox=(chars[ci]['bbox'] if ci < len(chars) else None),
                                          line=text, pair=name))
            prev_line = ln
        # 页末未配对的 open（页内栈）：靠近页末 -> 可能是合法跨页 carry
        for name, st in page_stacks.items():
            for op in st:
                near_end = op['idx'] >= max(0, len(lines) - 3)
                closer = PAIR_OF_OPEN[op['char']][0]
                nxt_page = all_pages[local_pi + 1] if local_pi + 1 < len(all_pages) else None
                valid, hint = '', ''
                if near_end and nxt_page is not None:
                    fl = nxt_page[0]['text'] if nxt_page else ''
                    if fl and fl[0] == closer:
                        valid = 'page'
                    if not valid and mode == 'h' and op['idx'] + 1 < len(lines):
                        nxt_ln = lines[op['idx'] + 1]
                        if nxt_ln['block'] != lines[op['idx']]['block'] and nxt_ln['text'] and nxt_ln['text'][0] == closer:
                            valid = 'paragraph'
                    if not valid:
                        hint = ('weak' if any(closer in x['text'] for x in nxt_page) else 'none')
                items.append(dict(check='pair_balance', sub='unmatched_open',
                                  page=op['page'], idx=op['idx'], pos=op['pos'], char=op['char'],
                                  context=op['context'], clause='§4.8.3.5/§5.1.3',
                                  carry=valid,
                                  carry_evidence=('pair_continuation' if valid else ''),
                                  carry_hint=hint,
                                  boundary_hint=('page' if valid == 'page' else
                                                 ('paragraph' if valid == 'paragraph' else '')),
                                  bbox=None, line=op['context'], pair=name))
    # ---- 源图漏识标点 -> items（product_has_mark 区分「渲染端已补」/「产物仍缺」） ----
    _sh_by_page = {}
    for h in source_hits:
        _sh_by_page.setdefault(h['page'], []).append(h)
    for h in source_hits:
        local = h['page'] - p0
        cols = all_pages[local] if 0 <= local < len(all_pages) else []
        has = _product_has_mark(cols, h['text'][-10:], _norm)
        # 找最接近的产物列 idx（按文本尾匹配）
        idx = -1
        nt = _norm(h['text'][-10:])
        for c in cols:
            if nt and nt in _norm(c['text']):
                idx = c['idx']
                break
        items.append(dict(check='ocr_miss_punct', sub=('product_missing' if not has else 'render_fixed'),
                          page=h['page'], idx=idx, pos=-1, char='」',
                          context=h['text'], clause='§5.1.3',
                          carry='', carry_evidence='', boundary_hint='',
                          bbox=[h['x'], h['y'], h['x'] + h['w'], h['y'] + h['h']],
                          line=h['text'], pair='单引号(竖排)',
                          ocr_row=h['ocr_row'], product_has_mark=bool(has),
                          mark_w=h['w'], mark_h=h['h']))
    # ---- 统计 ----
    counts = {}
    for it in items:
        k = it['check']
        c = counts.setdefault(k, dict(total=0, n_carry=0, by_clause={}, by_char={}))
        c['total'] += 1
        c['by_clause'][it['clause']] = c['by_clause'].get(it['clause'], 0) + 1
        c['by_char'][it['char']] = c['by_char'].get(it['char'], 0) + 1
        if it.get('carry'):
            c['n_carry'] += 1
    items.sort(key=lambda x: (x['page'], x['idx'], x['pos'], x['check']))
    return dict(meta=dict(pdf=os.path.abspath(pdf_path), md5=md5, mode=mode, label=label,
                          nonbody_pages=nonbody_pages,
                          pages=len(page_meta), pages_audited=[p0, p1],
                          coords=coords_path or '', clauses='GB/T 15834-2011',
                          tool='src/tools/punct_audit.py'),
                lines=dict(n_pages=len(page_meta), n_lines=sum(p['n_lines'] for p in page_meta)),
                pages=page_meta, items=items, counts=counts, pairs=pair_counts)


def render_md(rep, max_items=40):
    m = rep['meta']
    out = []
    out.append('# 标点审计 · %s' % (m['label'] or os.path.basename(m['pdf'])))
    out.append('')
    out.append('- PDF：`%s`' % m['pdf'])
    out.append('- md5：`%s`  |  模式：`%s`  |  页数：%d' % (m['md5'], m['mode'], m['pages']))
    out.append('- 规则：GB/T 15834—2011（`spec/governance/PUNCTUATION.md`）')
    out.append('- 行/列：%d' % rep['lines']['n_lines'])
    out.append('')
    out.append('## 计数')
    out.append('')
    out.append('| 检查项 | 条款 | 总数 | 其中 carry | 字符分布(top8) |')
    out.append('|---|---|---|---|---|')
    clause_of = dict(line_start='§5.1.1/5.1.2/5.1.3/5.1.6/5.1.7/5.1.9',
                     line_end='§5.1.3/5.1.9', pair_split='§5.1.3',
                     dash_lead='§4.10.3.9/§4.10.3.10（legal）/§5.1.6?（ambiguous）',
                     dash_split='§5.1.4', ellipsis_split='§5.1.5',
                     trail_width='§5.1.10', pair_balance='§4.8.3.5/§5.1.3',
                     ocr_miss_punct='§5.1.3（C OCR 漏识）')
    for k in ('line_start', 'line_end', 'pair_split', 'dash_lead', 'dash_split', 'ellipsis_split',
              'trail_width', 'pair_balance', 'ocr_miss_punct'):
        c = rep['counts'].get(k)
        if not c:
            continue
        chars = ', '.join('%s×%d' % (kk, vv) for kk, vv in
                          sorted(c['by_char'].items(), key=lambda t: -t[1])[:8])
        out.append('| `%s` | %s | %d | %d | %s |' % (k, clause_of.get(k, ''), c['total'],
                                                    c['n_carry'], chars))
    out.append('')
    out.append('## 配对计数')
    out.append('')
    out.append('| 对 | 形式 | open | close | 差 | 条款 |')
    out.append('|---|---|---|---|---|---|')
    for n, v in rep['pairs'].items():
        if v['open'] == 0 and v['close'] == 0:
            continue
        out.append('| %s | %s %s | %d | %d | %+d | %s |' % (n, v['forms'][0], v['forms'][1],
                                                          v['open'], v['close'],
                                                          v['open'] - v['close'], v['clause']))
    out.append('')
    out.append('## 明细（按页）')
    out.append('')
    mode = m['mode']
    for k in ('line_start', 'line_end', 'pair_split', 'dash_lead', 'dash_split', 'ellipsis_split',
              'trail_width', 'pair_balance', 'ocr_miss_punct'):
        its = [it for it in rep['items'] if it['check'] == k]
        if not its:
            continue
        out.append('### %s（%d 条）' % (k, len(its)))
        out.append('')
        for it in its[:max_items]:
            sub = ('/' + it['sub']) if it.get('sub') else ''
            out.append('- p%d %s%d `%s` %s%s carry=%s%s ｜ %s' %
                       (it['page'], '列' if mode == 'v' else '行', it['idx'] + 1,
                        it['char'], it['clause'], sub,
                        it.get('carry') or '-',
                        ('(' + it['carry_evidence'] + ')') if it.get('carry_evidence') else '',
                        it['context']))
        if len(its) > max_items:
            out.append('- …（余 %d 条见 JSON）' % (len(its) - max_items))
        out.append('')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description='GB/T 15834-2011 标点禁则/配对审计')
    ap.add_argument('pdf')
    ap.add_argument('--mode', choices=['h', 'v'], required=True)
    ap.add_argument('--coords', default='')
    ap.add_argument('--json', default='')
    ap.add_argument('--md', default='')
    ap.add_argument('--label', default='')
    ap.add_argument('--max-items', type=int, default=40)
    ap.add_argument('--pages', default='', help='只审计前 N 页/区间，如 1-100')
    ap.add_argument('--src-pdf', default='', help='源图 PDF（竖排源图侧 OCR 漏识标点检查用）')
    ap.add_argument('--lines', default='', help='OCR 行 JSON（配合 --src-pdf/--coords）')
    ap.add_argument('--include-nonbody', action='store_true',
                    help='把版權/印刷信息页也纳入审计（默认跳过：頁 554/1163 型）')
    args = ap.parse_args()
    pages = None
    if args.pages:
        a, _, b = args.pages.partition('-')
        pages = (int(a), int(b) if b else int(a))
    rep = audit(args.pdf, args.mode, args.coords, args.label, args.max_items, pages,
                src_pdf=args.src_pdf, lines_path=args.lines, include_nonbody=args.include_nonbody)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        json.dump(rep, open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('JSON -> %s' % args.json)
    if args.md:
        os.makedirs(os.path.dirname(os.path.abspath(args.md)), exist_ok=True)
        open(args.md, 'w', encoding='utf-8').write(render_md(rep, args.max_items))
        print('MD   -> %s' % args.md)
    if not args.json and not args.md:
        print(render_md(rep, args.max_items))
    print('摘要: ' + ' '.join('%s=%d' % (k, v['total']) for k, v in sorted(rep['counts'].items())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
