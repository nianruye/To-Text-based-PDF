#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用 PDF 优化(排版还原)一键脚本。

用法:
    /usr/bin/python3 optimize_book.py <source_pdf> [book_name] [--skip-ocr] [--only-ocr]

流程:
    1. OCR (PaddleOCR-VL spotting 行级) → data/<book>/<book>_spotting_{lines,coords}.json
       - 数据已存在则自动跳过(断点续传, --only-ocr 可强制重跑)
    2. 几何体检: calibrate 判 cw, cw>60(多行合并症状)自动 split_polys → linelevel 数据
    3. fit_positional 两趟校准排版 → output/<book>/<book>_optimized.pdf
    4. 验证: verify_geom(页数/pitch 硬约束) + check_overlap(字符重叠)
    5. pdf2md 导出 → output/<book>/<book>.md
    6. 汇总报告

前置:
    /tmp/paddle_token 存在(PaddleOCR 云 API token)
    OCR 限流自动无限重试(已内置), 高峰期(晚8-11点)可能排队较久

示例:
    /usr/bin/python3 optimize_book.py source_pdf/newbook.pdf
    /usr/bin/python3 optimize_book.py source_pdf/newbook.pdf mybook --skip-ocr
"""
import json
import os
import subprocess
import sys

ROOT = '/opt/test'
PY = '/usr/bin/python3'


def run(cmd, env_extra=None, timeout=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    print(f"\n>>> {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=ROOT, env=env, timeout=timeout)
    if r.returncode != 0:
        sys.exit(f"[FAIL] 命令退出码 {r.returncode}: {' '.join(cmd)}")
    return r


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = [a for a in sys.argv[1:] if a.startswith('--')]
    if not args:
        print(__doc__)
        sys.exit(2)
    src_pdf = os.path.abspath(args[0])
    book = args[1] if len(args) > 1 else os.path.splitext(os.path.basename(src_pdf))[0]
    if book.lower().endswith('.pdf'):
        book = book[:-4]   # 书名带不带 .pdf 都行, 自动去后缀
    only_ocr = '--only-ocr' in flags
    skip_ocr = '--skip-ocr' in flags or only_ocr

    if not os.path.exists(src_pdf):
        sys.exit(f"[FAIL] 源 PDF 不存在: {src_pdf}")
    if not os.path.exists('/tmp/paddle_token'):
        sys.exit("[FAIL] 缺 /tmp/paddle_token (PaddleOCR API token), 先放 token 再跑")

    ddir = f'{ROOT}/data/{book}'
    odir = f'{ROOT}/output/{book}'
    os.makedirs(ddir, exist_ok=True)
    os.makedirs(odir, exist_ok=True)

    lines = f'{ddir}/{book}_spotting_lines.json'
    coords = f'{ddir}/{book}_spotting_coords.json'
    lines_ll = f'{ddir}/{book}_linelevel_spotting_lines.json'
    coords_ll = f'{ddir}/{book}_linelevel_spotting_coords.json'
    out_pdf = f'{odir}/{book}_optimized.pdf'
    out_md = f'{odir}/{book}.md'

    # ── 1. OCR ──
    if os.path.exists(lines) and os.path.exists(coords) and not only_ocr:
        print(f"[1/5] OCR 数据已存在, 跳过: {lines}")
    else:
        print("[1/5] OCR (spotting 行级, 限流自动重试, 大书可能 20-60 分钟)...")
        run([PY, 'src/ocr/run_spotting_ocr.py', src_pdf, lines, coords],
            env_extra={'OCR_LAYOUT': '0', 'PYTHONUNBUFFERED': '1'})
        print("[1/5] OCR 完成")

    # ── 2. 几何体检 + 自动拆分 ──
    print("[2/5] 几何体检 (cw 异常自动 split_polys)...")
    probe = subprocess.run([PY, '-c', f'''
import sys, json
sys.path.insert(0, '{ROOT}/src')
from utils.geometry import calibrate
sl = json.load(open("{lines}"))
co = json.load(open("{coords}"))
G = calibrate(sl, co, 200)
print(f"cw={{G['cw']}} FONT={{G['FONT']}} BASELINE={{G['BASELINE']}} 页数={{len(sl)}}")
'''], cwd=ROOT, capture_output=True, text=True)
    print(probe.stdout.strip())
    if probe.returncode != 0:
        sys.exit("[FAIL] 几何体检失败:\n" + probe.stderr)
    cw = float(probe.stdout.split('cw=')[1].split()[0])
    use_lines, use_coords = lines, coords
    if cw > 60:
        print(f"    cw={cw} > 60 (多行合并症状, 如 wz3), 自动 split_polys → linelevel 数据")
        run([PY, '-c', f'''
import sys, json
sys.path.insert(0, '{ROOT}/src')
from utils.split_polys import split_multiline
sl = json.load(open("{lines}"))
co = json.load(open("{coords}"))
ns, nc = split_multiline(sl, co)
json.dump(ns, open("{lines_ll}", "w"), ensure_ascii=False, indent=2)
json.dump(nc, open("{coords_ll}", "w"), ensure_ascii=False, indent=2)
'''])
        use_lines, use_coords = lines_ll, coords_ll
    else:
        print(f"    cw={cw} ≤ 60, 数据正常, 直接排版")

    if only_ocr:
        print("[only-ocr] 完成, 数据已就绪。")
        return

    # ── 3. fit_positional 两趟校准排版 (必须串行!) ──
    print("[3/5] fit_positional 排版 (两趟校准, 串行)...")
    run([PY, 'src/calibration/fit_positional.py', use_lines, use_coords, out_pdf, src_pdf],
        timeout=1800)

    # ── 4. 验证 ──
    print("[4/5] 验证...")
    print("\n--- verify_geom (页数/pitch 硬约束) ---")
    vr = subprocess.run([PY, 'src/test/verify_geom.py', out_pdf, use_coords, use_lines],
                        cwd=ROOT, env=dict(os.environ, VERIFY_PITCH_FLOOR='85'))
    print(f"verify_geom 退出码: {vr.returncode} ({'PASS' if vr.returncode == 0 else 'FAIL — 看上面明细'})")
    print("\n--- check_overlap (字符重叠) ---")
    ov = subprocess.run([PY, 'src/tools/check_overlap.py', out_pdf], cwd=ROOT)
    print(f"check_overlap 退出码: {ov.returncode} ({'无重叠' if ov.returncode == 0 else '有重叠 — 看上面明细'})")

    # ── 5. md 导出 ──
    print("[5/5] pdf2md 导出...")
    run([PY, 'src/ocr/pdf2md.py', out_pdf, out_md])

    print(f"""
╔══════════════════════════════════════╗
║  完成                                 ║
║  PDF:  {out_pdf}
║  MD :  {out_md}
║  验证: verify_geom 退出码 {vr.returncode}, overlap 退出码 {ov.returncode}
╚══════════════════════════════════════╝""")


if __name__ == '__main__':
    main()
