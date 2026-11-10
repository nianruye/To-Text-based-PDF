#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fit_common.py - 位置还原两趟校准驱动（横排 geom/classic 共用，build_name 参数化）。

本模块由原 fit_positional.py / fit_positional_classic.py 的重复实现合并而来（issue #17）；
两个入口仍保留为 3 行薄壳（src/calibration/fit_positional.py / fit_positional_classic.py），
main(build_name) 决定调 build_geom.py 还是 build_classic.py，其余逻辑不变。
POS_FILL 默认 0.95 不变。
"""
import sys, os, json, subprocess, re, statistics, tempfile, shutil
import fitz

SL = sys.argv[1]; CO = sys.argv[2]; OUT = sys.argv[3]
SRC = sys.argv[4] if len(sys.argv) > 4 else ''   # 源 PDF(图页/乱码页整页贴原图)

def render(out_pdf, est_log=None, ratio_table=None, fill=None, build_name='build_geom', verify_mark=True):
    """Render one calibration pass.

    verify_mark=True only for pass1: measure_heights() needs GMPG source-page marks.
    pass2 is the delivery PDF and must not set VERIFY_MARK (delivery text layer is clean);
    explicitly pop it so an inherited shell env cannot leak marks back in.
    """
    env = dict(os.environ)
    env['POSITIONAL'] = '1'
    if verify_mark:
        env['VERIFY_MARK'] = '1'
    else:
        env.pop('VERIFY_MARK', None)
    if build_name == 'build_geom':
        # geom 逐页跟随源 pitch:split_polys 后源 pitch 逐页波动(22-36pt),全局 baselineskip
        # 只能匹配中位附近的页 -> pitch 达标率掉。PER_PAGE_PITCH 让每页按源 pitch 反推 linespread。
        # classic 用独立 page_pitch(inner 口径),不开。setdefault:shell 显式设值时可覆盖。
        env.setdefault('PER_PAGE_PITCH', '1')
    if est_log: env['POS_EST_LOG'] = est_log
    if ratio_table: env['POS_RATIO_TABLE'] = ratio_table
    if fill: env['POS_FILL'] = str(fill)
    import os as _os
    _build = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'pipelines', build_name + '.py')
    cmd = [sys.executable, _build, SL, CO, out_pdf]   # 与 fit_positional 同解释器(原 'python3' 随 PATH 漂移, 用户环境命中 mineru venv 缺 opencc 致 render 失败)
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

def main(build_name):
    tmp = tempfile.mkdtemp(prefix='fitpos_')
    est_log = os.path.join(tmp, 'est.json')
    ratio_tbl = os.path.join(tmp, 'ratio.json')
    p1 = os.path.join(tmp, 'pass1.pdf')

    try:
        print('[pass1] 渲染 + 导出估高...')
        render(p1, est_log=est_log, fill=99, build_name=build_name, verify_mark=True)   # pass1 需要 GMPG 估高
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
        render(OUT, ratio_table=ratio_tbl, fill=os.environ.get('POS_FILL', '0.95'), build_name=build_name,
               verify_mark=False)   # pass2=交付物:不带 GMPG;0.95:估高已校准,留 5% 余量
        print(f'[完成] {OUT}')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # 清理临时目录(#7:成功/异常/SystemExit 均清理)
