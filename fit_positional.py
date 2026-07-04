#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fit_positional.py — 位置还原两趟校准驱动。
单趟估高有每页方差(字体混合)→ 溢出与空白不可兼得。本驱动:
  pass1: 渲染(POS + 标记 + 导出估高),用 GMPG 标记量每源页【实测位置化高度】。
  校准 : ratio[key] = 实测高 / 估高 → 修正 build_geom 每页估高的系统+方差偏差。
  pass2: 带 ratio 表重渲 → 估高精确 → 压缩量刚好 → 不溢出且底部空白最小。

用法: python3 fit_positional.py <spotting_lines> <spotting_coords> <out.pdf> [extra env passthrough...]
环境: 透传给 build_geom(FONT_SCALE/OVERBOUND/PAGENUM_* 等);本驱动强制 POSITIONAL=1 VERIFY_MARK=1。
"""
import sys, os, json, subprocess, re, statistics, tempfile
import fitz

SL = sys.argv[1]; CO = sys.argv[2]; OUT = sys.argv[3]
SRC = sys.argv[4] if len(sys.argv) > 4 else ''   # 源 PDF(图页/乱码页整页贴原图)
DPI = 200

def render(out_pdf, est_log=None, ratio_table=None, fill=None):
    env = dict(os.environ)
    env['POSITIONAL'] = '1'; env['VERIFY_MARK'] = '1'
    if est_log: env['POS_EST_LOG'] = est_log
    if ratio_table: env['POS_RATIO_TABLE'] = ratio_table
    if fill: env['POS_FILL'] = str(fill)
    cmd = ['python3', 'build_geom.py', SL, CO, out_pdf]
    if SRC: cmd.append(SRC)
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if not os.path.exists(out_pdf):
        sys.stderr.write(r.stdout[-2000:] + r.stderr[-2000:]); raise SystemExit('render 失败')
    return r

def measure_heights(pdf):
    """按 GMPG 标记把物理页归到源页,量每源页【实测位置化内容高度】(pt)。
    溢出成 N 页的源页:高 ≈ (N-1)×可用版心 + 末页内容底 - 顶。"""
    doc = fitz.open(pdf)
    from collections import OrderedDict
    groups = OrderedDict()
    for i, pg in enumerate(doc):
        m = re.search(r'GMPG(\d+)ZZ', pg.get_text('text'))
        k = m.group(1) if m else None
        groups.setdefault(k, []).append(i)
    heights = {}
    for k, idxs in groups.items():
        if k is None: continue
        usable = doc[idxs[0]].rect.height - 42   # top12 + bottom30
        # 每张物理页的内容顶/底(去页眉<2%/页码底部窄短行,与 verify 同口径)
        def extent(pi):
            pg = doc[pi]; H = pg.rect.height; W = pg.rect.width; ys = []
            for blk in pg.get_text('dict')['blocks']:
                for ln in blk.get('lines', []):
                    x0, y0, x1, y1 = ln['bbox']
                    if y1 - y0 <= 0.5: continue
                    yc = (y0 + y1) / 2
                    if not (0.02 * H < yc < 0.98 * H): continue
                    if yc > 0.92 * H and (x1 - x0) < 0.15 * W: continue   # 页码
                    ys.append((y0, y1))
            if not ys: return 0.0, 0.0
            return min(a for a, _ in ys), max(b for _, b in ys)
        top0, _ = extent(idxs[0])
        _, botN = extent(idxs[-1])
        h = (len(idxs) - 1) * usable + max(0.0, botN - 12.0)   # 顶从版心顶12算
        heights[k] = round(h, 1)
    doc.close()
    return heights

def main():
    tmp = tempfile.mkdtemp(prefix='fitpos_')
    est_log = os.path.join(tmp, 'est.json')
    ratio_tbl = os.path.join(tmp, 'ratio.json')
    p1 = os.path.join(tmp, 'pass1.pdf')

    print('[pass1] 渲染 + 导出估高...')
    render(p1, est_log=est_log, fill=99)   # FILL 极大 → pass1 几乎不压缩,量自然高度
    est = json.load(open(est_log))
    actual = measure_heights(p1)

    # ratio = 实测/估高;仅对有效页(两者>0)。缺失页 ratio=1。
    ratio = {}
    diffs = []
    for k, e in est.items():
        a = actual.get(k, 0.0)
        if e > 0 and a > 0:
            ratio[k] = round(a / e, 3); diffs.append(a / e)
    json.dump(ratio, open(ratio_tbl, 'w'))
    if diffs:
        print(f'[校准] {len(diffs)} 页 ratio: 中位{statistics.median(diffs):.3f} '
              f'[{min(diffs):.2f},{max(diffs):.2f}]  (实测/估高;>1=估低,<1=估高)')

    print('[pass2] 带 ratio 表重渲...')
    render(OUT, ratio_table=ratio_tbl, fill=os.environ.get('POS_FILL', '0.95'))   # 0.95:估高已校准,留 5% 余量→0 溢出且空白最小(wz1 实测)
    print(f'[完成] {OUT}')

if __name__ == '__main__':
    main()
