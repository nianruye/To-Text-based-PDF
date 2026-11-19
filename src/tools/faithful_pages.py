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


def _toc_like(lines):
    """目录页/续页判据：含「目录」标记，或多数行为「条目形」（纯页码 / 带点线 / 章节制式）。"""
    ne = [str(t).strip() for t in lines if str(t).strip()]
    if not ne:
        return False
    if any(('目录' in t) or ('CONTENTS' in t.upper()) for t in ne):
        return True
    import re as _re
    n = 0
    for t in ne:
        if _re.fullmatch(r'\d{1,4}', t):
            n += 1
        elif _re.search(r'[…]{2,}\s*\d{1,4}$', t) or _re.search(r'\.{4,}\s*\d{1,4}$', t):
            n += 1
        elif _re.match(r'^(第[一二三四五六七八九十百千零\d]+[章节编]|[一二三四五六七八九十]+、|\d+[.．、])', t):
            n += 1
    return n >= max(3, int(len(ne) * 0.5))


def toc_pages(lines_json):
    """返回目录页集合（0-based 页 key）。含标记页 + 与之相邻的条目形续页。"""
    import json as _json
    if not lines_json:
        return set()
    L = _json.load(open(lines_json, encoding='utf-8'))
    marked = set()
    like = set()
    for k, v in L.items():
        if _toc_like(v):
            like.add(int(k))
            if any(('目录' in str(t)) or ('CONTENTS' in str(t).upper()) for t in v):
                marked.add(int(k))
    out = set(marked)
    for m in marked:                      # 与标记页连续（±3 页内）的条目形页也算目录
        for d in range(-3, 4):
            if (m + d) in like:
                out.add(m + d)
    return out


def select(doc, tol_pitch, exclude=(), a_dn=3, a_pe=0.20):
    rows = doc.get('rows') or []
    bad = []
    for r in rows:
        if not r.get('comparable', True):
            continue          # 门禁不计入判定的页，贴图无意义
        pg = int(r['page'])
        if (pg - 1) in exclude:   # 目录页必须保持文字层（用户要求：目录不能变成图）
            continue
        pe = r.get('p_err')
        if pe is None:
            continue
        # 只把「结构性失败」的页贴图。仅行距比超标(常见于断行差 1–2 行, 见 AGENTS #60
        # 字宽差 4–6%)的页**版面本身没问题**, 应保持文字层 —— 用户明确要求不要变成图片。
        _dn = abs(int(r.get('src_n') or 0) - int(r.get('out_n') or 0))
        if _dn >= a_dn or pe >= a_pe:
            bad.append(pg)
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
    ap.add_argument('--dn', type=int, default=3, help='行数差 ≥ 此值 才贴图（结构性重排）')
    ap.add_argument('--pe', type=float, default=0.20, help='行距比 ≥ 此值 才贴图（重大版式偏移）')
    ap.add_argument('--write-config', action='store_true')
    ap.add_argument('--keep-toc-image', action='store_true', help='允许目录页也走保真贴图（默认排除）')
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
    _toc = set() if a.keep_toc_image else toc_pages(a.lines)
    if _toc:
        print(f'[faithful] 排除目录页 {len(_toc)} 个（目录必须保持文字层）: {sorted(x + 1 for x in _toc)}')
    bad = select(doc, a.tol_pitch, _toc, a.dn, a.pe)
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
