#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""竖排数据「符号补全」工具(任务C): 用 layout 版面模式 OCR 的整页文本, 给 spotting 行文本补回被丢掉的符号。

背景(实测, 见 docs/vert_readability_report.md):
  · PaddleOCR-VL-1.6 的 spotting 行级模式(useLayoutDetection=False + promptLabel='spotting')提供逐行
    rec_polys(竖排管线必需), 但**系统性丢引号类符号** —— wz6 全书 『 仅 5 次, 而 layout 模式(及源书)
    51 次; p9 单页 A/B/C/D/E 五组参数实验证明: 没有任何单组参数能同时保符号与行级坐标。
  · layout 模式(useLayoutDetection=True)保符号完整, 但只回整块坐标(整页正文 1-2 块), 没有行级 poly。
做法(文本级补全, 几何数据一律不动):
  ① 每页把 layout 的 vertical_text 块按块坐标阅读序(右->左)拼成整页正文串 b;
  ② spotting 的正文行(排除书眉/页码/边注)同样按阅读序拼成 a;
  ③ difflib.SequenceMatcher 模糊对齐 a/b; 对 'insert'/'replace' 段里 **b 有而 a 无** 的字符:
     若属于「符号集」(引号/括号), 插回 a 中该位置所属的那一行;
  ④ 落盘回 lines.json(调用方负责先备份 *.bak_taskI)。只补符号, 不采纳 layout 的其它差异
     (layout 文本自身的句读标点也有丢失, 引入反而更差)。

用法:
  /usr/bin/python3 src/tools/patch_vert_symbols.py <spotting_lines.json> <spotting_coords.json> \
      <layout_lines.json> <layout_coords.json> <layout_labels.json> [--dry] [--out 输出.json]
"""
import difflib
import json
import sys

SYMB = set('『』「」（）〔〕【】〈〉《》“”‘’﹁﹂﹃﹄')     # 要补的「符号集」
BODY_MIN_H = 300          # 正文行的 y 跨度下限(px@2x; 与 build_vert.is_body_col 同口径)
MAX_INS_PG = 40           # 单页补全上限(防对齐异常时灌入垃圾)


def body_rows(lines, coords, key):
    """本页正文行 [(idx, x0, y0, text)]: 剔除书眉/页码(gap 短行)/边注(x0<100 小字); 返回阅读序(右->左)"""
    out = []
    for i, (t, p) in enumerate(zip(lines.get(key, []), coords.get(key, []))):
        if not p: continue
        t = str(t).strip()
        if not t or '\n' in t: continue
        xs = [q[0] for q in p]; ys = [q[1] for q in p]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if y1 - y0 < BODY_MIN_H or len(t) < 2: continue
        if x0 > 1100 and y1 - y0 < 300: continue          # 书眉/页码(最右列短行)
        if x0 < 100 and (y1 - y0) / len(t) < 55: continue  # 左侧小字边注
        out.append((i, x0, y0, t))
    out.sort(key=lambda r: -r[1])                          # 阅读序: 右 -> 左
    return out


def layout_text(lblocks, lcoords, llabels, key):
    """layout 侧整页正文串(只用 vertical_text 块, 阅读序 右->左)"""
    bl = []
    for t, p, lab in zip(lblocks.get(key, []), lcoords.get(key, []), llabels.get(key, [])):
        if lab != 'vertical_text' or not str(t).strip(): continue
        x = max((q[0] for q in p), default=0) if p else 0
        bl.append((x, str(t)))
    bl.sort(key=lambda v: -v[0])
    return ''.join(t for _x, t in bl)


def main():
    sl_path, sc_path, ll_path, lc_path, lb_path = sys.argv[1:6]
    dry = '--dry' in sys.argv
    out_path = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else sl_path
    SL = json.load(open(sl_path, encoding='utf-8'))
    SC = json.load(open(sc_path, encoding='utf-8'))
    LL = json.load(open(ll_path, encoding='utf-8'))
    LC = json.load(open(lc_path, encoding='utf-8'))
    LB = json.load(open(lb_path, encoding='utf-8'))

    tot, cnt, per_page = 0, {}, []
    for key in sorted(SL.keys(), key=int):
        rows = body_rows(SL, SC, key)
        b = layout_text(LL, LC, LB, key)
        if not rows or not b: continue
        a = ''.join(r[3] for r in rows)
        starts, pos = [], 0
        for r in rows:
            starts.append(pos); pos += len(r[3])
        new = [r[3] for r in rows]
        ins_pg = 0
        # 先按行收集 (行内偏移 -> 待插入串): 同一行可能有多次插入, 若边算边改会让后续偏移错位
        pend = {}
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if op == 'insert':
                seg_a, seg_b, off = '', b[j1:j2], i1
            elif op == 'replace':
                seg_a, seg_b, off = a[i1:i2], b[j1:j2], i1
            else:
                continue
            add = [c for c in seg_b if c in SYMB and c not in seg_a]
            if not add: continue
            li = next((k for k in range(len(starts)) if starts[k] > off), len(rows)) - 1
            li = max(0, min(len(rows) - 1, li))
            pend.setdefault(li, []).append((off - starts[li], ''.join(add)))
            ins_pg += len(add)
            for c in add: cnt[c] = cnt.get(c, 0) + 1
        for li, adds in pend.items():
            for inner, s in sorted(adds, key=lambda v: -v[0]):   # 倒序插入: 前面的偏移不受影响
                new[li] = new[li][:inner] + s + new[li][inner:]
        if ins_pg and ins_pg <= MAX_INS_PG:
            for (i, _x, _y, _t), nt in zip(rows, new):
                SL[key][i] = nt
            tot += ins_pg
            per_page.append((int(key) + 1, ins_pg, len(rows)))
        elif ins_pg:
            print('  [跳过] key %s 补全量 %d 超上限(疑对齐异常)' % (key, ins_pg))
    print('补全符号 %d 处, 涉及 %d 页' % (tot, len(per_page)))
    for c, n in sorted(cnt.items(), key=lambda v: -v[1]): print('   %s x%d' % (c, n))
    if per_page:
        print('逐页:', ' '.join('p%d(+%d)' % (p[0], p[1]) for p in per_page[:40]))
    if dry:
        print('[dry] 未写盘'); return
    json.dump(SL, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('已写 %s' % out_path)


if __name__ == '__main__':
    main()
