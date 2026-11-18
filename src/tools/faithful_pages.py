#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""faithful_pages.py — 依 verify_geom 的逐页判据选出「需要保真回退」的页。

判据与门禁**完全同源**：直接消费 `verify_geom.py --json` 的逐页 `p_err`
（= |out_pitch − src_pitch| / src_pitch，逐页中位行距比），
`p_err >= tol_pitch` 且 `comparable` 的页即入选。

这样「选中页 == 门禁失败页」，贴图后 pitch 必然上升，且阈值单调。

用法
  # 一步到位（内部跑 verify_geom 拿 JSON）
  /usr/bin/python3 src/tools/faithful_pages.py --book wz3 \
      --pdf deliverables/wz3.pdf \
      --coords data/wz3/wz3_linelevel_spotting_coords.json \
      --lines data/wz3/wz3_linelevel_spotting_lines.json \
      --src-pdf source_pdf/wz3.pdf [--tol-pitch 0.03] [--write-config]

  # 复用已有 JSON（调试用，省一次全量校验）
  /usr/bin/python3 src/tools/faithful_pages.py --book wz3 --from-json /tmp/wz3_verify.json
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY = '/usr/bin/python3'


def run_verify(pdf, coords, lines, src_pdf, tol_pitch, out_json):
    cmd = [PY, os.path.join(ROOT, 'src/test/verify_geom.py'), pdf, coords]
    if lines:
        cmd.append(lines)
    if src_pdf:
        cmd += ['--src-pdf', src_pdf]
    cmd += ['--tol-pitch', str(tol_pitch), '--json', out_json]
    print('[faithful] ' + ' '.join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(out_json):
        raise SystemExit(f'[faithful] verify_geom 未产出 JSON: {out_json}')


def select(doc, tol_pitch):
    rows = doc.get('rows') or []
    bad = []
    for r in rows:
        if not r.get('comparable', True):
            continue          # 门禁不计入判定的页，贴图无意义
        pe = r.get('p_err')
        if pe is not None and pe >= tol_pitch:
            bad.append(int(r['page']))
    return sorted(set(bad))


def write_config(book, pages):
    cfg_dir = os.path.join(ROOT, 'config', 'books')
    os.makedirs(cfg_dir, exist_ok=True)
    path = os.path.join(cfg_dir, book + '.json')
    cfg = {}
    if os.path.exists(path):
        try:
            cfg = json.load(open(path, encoding='utf-8'))
        except Exception:
            cfg = {}
    if pages:
        cfg['faithful_pages'] = pages
        cfg['_comment_faithful'] = '由 src/tools/faithful_pages.py 依 verify_geom 的逐页 p_err 生成，勿手改'
    else:
        cfg.pop('faithful_pages', None)
    json.dump(cfg, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'[faithful] 已写入 {path}')
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True)
    ap.add_argument('--pdf', default='')
    ap.add_argument('--coords', default='')
    ap.add_argument('--lines', default='')
    ap.add_argument('--src-pdf', default='')
    ap.add_argument('--from-json', default='')
    ap.add_argument('--tol-pitch', type=float, default=0.03)
    ap.add_argument('--write-config', action='store_true')
    ap.add_argument('--out-json', default='/tmp/faithful_verify.json')
    a = ap.parse_args()

    if a.from_json:
        doc = json.load(open(a.from_json, encoding='utf-8'))
    else:
        if not (a.pdf and a.coords):
            raise SystemExit('需要 --pdf 与 --coords（或用 --from-json）')
        run_verify(a.pdf, a.coords, a.lines, a.src_pdf, a.tol_pitch, a.out_json)
        doc = json.load(open(a.out_json, encoding='utf-8'))

    total = int(doc.get('n_out') or doc.get('n_src') or len(doc.get('rows') or []))
    bad = select(doc, a.tol_pitch)
    est_mb = round(len(bad) * 0.30, 1)
    print(f"[faithful] {a.book}: 共 {total} 页 | 选中 {len(bad)} 页 ({100.0*len(bad)/max(1,total):.1f}%) | 预估 {est_mb} MB (300KB/页)")
    if bad:
        head = ', '.join(str(x) for x in bad[:25])
        print(f'[faithful] 前 25 页: {head}{" …" if len(bad) > 25 else ""}')
    if a.write_config:
        write_config(a.book, bad)
    return 0


if __name__ == '__main__':
    sys.exit(main())
