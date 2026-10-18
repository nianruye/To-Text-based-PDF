#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正 PDF 文本层的圆圈数字码位（dvipdfmx ToUnicode 反向映射错）

背景（实测）：
  Noto Serif CJK 的 5 个 face 都把 U+2460(①) 与 U+2780(➀) 映射到**同一个字形**（cid00919）。
  dvipdfmx 生成 ToUnicode 时反向查表命中 U+2780，于是：
    · 画出来的字形是空心 ①（实测墨迹密度 19.9%；实心➀ 会是 45-60%）—— 视觉正确
    · 文本层是 U+2780 → 复制 / 搜索 / RAG 索引拿到 ➀
  build_vert.py 的 vert.tex 里是字面的 ①（已核实），所以问题只在 ToUnicode。

实测 wz7 的 CMap（xref 6647, NotoSerifCJKjp-Regular）：
  <0397> <03A0> <2780>   -> codes 0x0397..0x03A0 顺序映到 U+2780..U+2789（➀..➉）**错**
  <0397>..<03A0> 正是 ①..⑩ 的 CID；应映到 U+2460..2469
  <03A1> <03A4> <246A>   -> ⑪..⑭ **本来就对**（Noto 只把 ①..⑩ 与丁巴特共用字形）

修法（数据驱动，不猜）：
  读 OCR 源行 JSON 得到本书真正用到的字符集 S。对每个 ToUnicode 映射：
    bfchar  <code> <u>          —— u 是丁巴特、且 u 不在 S、而对应圆圈数字在 S -> 改成圆圈数字
    bfrange <lo> <hi> <u>       —— 同上，且要求整段对应圆圈数字都在 S
    bfrange <lo> <hi> [<u1>..]  —— 逐个元素判
  只改「源书确实用了、却被映错」的码位；源书真用丁巴特的场合一律不动。

用法:
  /usr/bin/python3 src/tools/fix_tounicode_circled.py <in.pdf> <lines.json> [-o out.pdf] [--dry-run]
"""
import argparse
import json
import os
import re
import sys

# 丁巴特圆圈数字 -> 圆圈数字（Unicode 标准对应）
DINGBAT_TO_CIRCLED = {}
for _i in range(10):
    DINGBAT_TO_CIRCLED[0x2776 + _i] = 0x2460 + _i      # ❶..❿
    DINGBAT_TO_CIRCLED[0x2780 + _i] = 0x2460 + _i      # ➀..➉
    DINGBAT_TO_CIRCLED[0x278A + _i] = 0x2460 + _i      # ➊..➓

RE_BFCHAR = re.compile(r'<([0-9A-Fa-f]{2,4})>\s*<([0-9A-Fa-f]{2,8})>')
RE_BFRANGE = re.compile(r'<([0-9A-Fa-f]{2,4})>\s*<([0-9A-Fa-f]{2,4})>\s*<([0-9A-Fa-f]{2,8})>')
RE_BFRANGE_ARR = re.compile(r'<([0-9A-Fa-f]{2,4})>\s*<([0-9A-Fa-f]{2,4})>\s*\[([^\]]*)\]')


def source_chars(lines_json):
    d = json.load(open(lines_json, encoding='utf-8'))
    s = set()
    for rows in d.values():
        for t in rows:
            s.update(str(t))
    return s


def _plan(u, allowed, run=1):
    """该码位是否应改写 -> 目标码位 或 None"""
    if u not in DINGBAT_TO_CIRCLED:
        return None
    want = DINGBAT_TO_CIRCLED[u]
    if chr(u) in allowed:
        return None                                # 源书真用了丁巴特 -> 不动
    for k in range(run):
        if chr(want + k) not in allowed:
            return None                            # 源书也没用对应圆圈数字 -> 不动
    return want


def patch_cmap(data, allowed, stats):
    txt = data.decode('latin-1')

    # ① bfrange 数组形态:  <lo> <hi> [<u1> <u2> ...]
    def fix_arr(m):
        lo, hi, body = m.group(1), m.group(2), m.group(3)
        items = RE_BFCHAR.findall(body)            # 复用: 单个 <u> 无配对
        raw_items = re.findall(r'<([0-9A-Fa-f]{2,8})>', body)
        out, changed = [], False
        for it in raw_items:
            u = int(it, 16)
            w = _plan(u, allowed)
            if w is not None:
                stats.append((lo + '-' + hi, u, w))
                out.append('<%04X>' % w)
                changed = True
            else:
                out.append('<%s>' % it)
        return '<%s> <%%s> [%s]' % (lo, ' '.join(out)) if changed else m.group(0)
    txt = RE_BFRANGE_ARR.sub(fix_arr, txt)

    # ② bfrange 三元组: <lo> <hi> <u>
    def fix_range(m):
        lo, hi, dst = m.group(1), m.group(2), m.group(3)
        try:
            n = int(hi, 16) - int(lo, 16)
        except ValueError:
            return m.group(0)
        if n < 0 or n > 0x1000:
            return m.group(0)
        u = int(dst, 16)
        w = _plan(u, allowed, run=n + 1)
        if w is None:
            return m.group(0)
        stats.append((lo + '-' + hi, u, w))
        return '<%s> <%s> <%04X>' % (lo, hi, w)
    txt = RE_BFRANGE.sub(fix_range, txt)

    # ③ bfchar 单条: <code> <u>
    def fix_char(m):
        code, tgt = m.group(1), m.group(2)
        u = int(tgt, 16)
        w = _plan(u, allowed)
        if w is None:
            return m.group(0)
        stats.append((code, u, w))
        return '<%s> <%04X>' % (code, w)
    txt = RE_BFCHAR.sub(fix_char, txt)

    return txt.encode('latin-1')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('lines_json')
    ap.add_argument('-o', '--out')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    allowed = source_chars(args.lines_json)
    ding = sorted(c for c in allowed if ord(c) in DINGBAT_TO_CIRCLED)
    circ = sorted(c for c in allowed if 0x2460 <= ord(c) <= 0x2473)
    print('OCR 源字符集: %d 个字  含圆圈数字 %s  含丁巴特 %s'
          % (len(allowed), ''.join(circ) or '(无)', ''.join(ding) or '(无)'))

    import fitz
    doc = fitz.open(args.pdf)
    stats, patched = [], 0
    for xref in range(1, doc.xref_length()):
        try:
            if not doc.xref_is_stream(xref):
                continue
            raw = doc.xref_stream(xref)
        except Exception:
            continue
        if not raw or (b'beginbfchar' not in raw and b'beginbfrange' not in raw):
            continue
        before = len(stats)
        new = patch_cmap(raw, allowed, stats)
        n = len(stats) - before
        if n:
            patched += 1
            print('  CMap xref %-6d 改写 %d 条' % (xref, n))
            if not args.dry_run:
                doc.update_stream(xref, new)

    print()
    print('共改写 %d 个 CMap 流 / %d 条映射' % (patched, len(stats)))
    for code, u, w in stats[:15]:
        print('   code=%-10s U+%04X %s -> U+%04X %s' % (code, u, chr(u), w, chr(w)))
    if len(stats) > 15:
        print('   ...')

    if args.dry_run:
        print('\n(--dry-run: 未写盘)')
        doc.close()
        return 0
    if not stats:
        print('\n无需修改')
        doc.close()
        return 0

    out = args.out or args.pdf
    tmp = out + '.tmp'
    doc.save(tmp, garbage=3, deflate=False)
    doc.close()
    os.replace(tmp, out)
    print('\n✓ 已写入 %s' % out)

    d2 = fitz.open(out)
    left, fixed = [], []
    for i in range(len(d2)):
        for ch in d2[i].get_text():
            if ord(ch) in DINGBAT_TO_CIRCLED:
                left.append((i + 1, ch))
            elif 0x2460 <= ord(ch) <= 0x2473:
                fixed.append((i + 1, ch))
    print('复核: 文本层 丁巴特残留 %d 处 / 圆圈数字 %d 处' % (len(left), len(fixed)))
    if left:
        print('  残留前 10:', left[:10])
    if fixed:
        print('  圆圈前 10:', fixed[:10])
    d2.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
