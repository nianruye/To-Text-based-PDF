#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""特征测试（不变量）公共 fixture。

策略：
- 截取 wz1/wz2 前 N 页 spotting 数据（lines/coords/LAYJSON/SRC PDF/pagenum）
  到临时目录，避免整本（wz2 783 页）跑 xelatex 过慢。
- session 级单趟跑 build_geom.py / build_classic.py（POSITIONAL=1 让墨高重叠/
  位置还原生效；不跑 fit_positional 两趟校准--太慢且其内部 subprocess 调
  ``python3`` 会命中 mineru venv（无 fitz））。
- 用系统 python /usr/bin/python3（有 fitz/opencc/xelatex），非 mineru venv。

页数类不变量在单趟无 ratio 校正下可能溢出，按"锁当前值"处理。
"""
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path('/opt/test')
DATA = ROOT / 'data'
SRC = ROOT / 'source_pdf'
PIPES = ROOT / 'src' / 'pipelines'
PY = '/usr/bin/python3'                       # 系统 python（有 fitz/opencc）
N = int(os.environ.get('INV_N', '30'))         # 截取页数
GEOM_START = int(os.environ.get('INV_GEOM_START', '40'))      # wz1 正文区起点（含脚注①页 41/48/49/50）
CLASSIC_START = int(os.environ.get('INV_CLASSIC_START', '60'))  # wz2 正文区起点（含〔X〕序号注释）


# ---------- 数据截取 ----------

def _slice_dict_json(inp, outp, n, start=0):
    """dict{页key: ...} -> 取源页 key in [start, start+n)，重映射为 0..n-1。"""
    d = json.load(open(inp, encoding='utf-8'))
    keys = [k for k in d.keys() if str(k).isdigit() and start <= int(k) < start + n]
    keys.sort(key=int)
    sub = {str(int(k) - start): d[k] for k in keys}
    json.dump(sub, open(outp, 'w', encoding='utf-8'), ensure_ascii=False)
    return len(sub)


def _slice_list_json(inp, outp, n, start=0):
    """list[页...] -> 取 [start, start+n)（LAYJSON 按页索引）。"""
    d = json.load(open(inp, encoding='utf-8'))
    sub = d[start:start + n]
    json.dump(sub, open(outp, 'w', encoding='utf-8'), ensure_ascii=False)
    return len(sub)


def _slice_pdf(inp, outp, n, start=0):
    """PDF -> 页 [start, start+n)。"""
    import fitz
    doc = fitz.open(inp)
    new = fitz.open()
    for i in range(start, min(start + n, doc.page_count)):
        new.insert_pdf(doc, from_page=i, to_page=i)
    new.save(outp)
    new.close()
    doc.close()


def _make_bundle(tmpdir, name, lines, coords, src_pdf, lay=None, pagenum=None, start=0):
    d = Path(tmpdir) / name
    d.mkdir(parents=True, exist_ok=True)
    nl = _slice_dict_json(lines, d / 'lines.json', N, start)
    _slice_dict_json(coords, d / 'coords.json', N, start)
    _slice_pdf(src_pdf, d / 'src.pdf', N, start)
    if lay and os.path.exists(lay):
        _slice_list_json(lay, d / 'lay.json', N, start)
    if pagenum and os.path.exists(pagenum):
        _slice_dict_json(pagenum, d / 'pagenum.json', N, start)
    print(f"[bundle] {name}: 源页 [{start},{start + N}) {nl} 页 -> {d}")
    return d


# ---------- bundles（session 级，截取一次） ----------

@pytest.fixture(scope='session')
def geom_bundle(tmp_path_factory):
    return _make_bundle(
        tmp_path_factory.mktemp('inv'), 'geom',
        DATA / 'wz1' / 'wz1_spotting_lines.json',
        DATA / 'wz1' / 'wz1_spotting_coords.json',
        SRC / 'wz1.pdf',
        pagenum=DATA / 'wz1' / 'wz1_full_pagenum.json',
        start=GEOM_START,
    )


@pytest.fixture(scope='session')
def classic_bundle(tmp_path_factory):
    return _make_bundle(
        tmp_path_factory.mktemp('inv'), 'classic',
        DATA / 'wz2' / 'wz2_spotting_lines.json',
        DATA / 'wz2' / 'wz2_spotting_coords.json',
        SRC / 'wz2.pdf',
        lay=DATA / 'wz2' / 'wz2.pdf_by_PaddleOCR-VL-1.6.json',
        start=CLASSIC_START,
    )


# ---------- 跑管线（session 级，只跑一次） ----------

def _run_pipe(script, bundle, out_name, extra_env):
    env = dict(os.environ)
    env['PER_PAGE_PITCH'] = '1'
    env['POSITIONAL'] = '1'          # 位置还原 + 墨高重叠生效（单趟无 ratio 校正）
    env.update(extra_env)
    out = bundle / out_name
    cmd = [PY, str(PIPES / script),
           str(bundle / 'lines.json'), str(bundle / 'coords.json'),
           str(out), str(bundle / 'src.pdf')]
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(ROOT))
    dt = time.time() - t
    assert r.returncode == 0, (
        f"{script} 失败 (rc={r.returncode}):\nSTDOUT:\n{r.stdout[-1500:]}\nSTDERR:\n{r.stderr[-1500:]}")
    assert out.exists(), f"未生成 {out}"
    print(f"[pipe] {script} {dt:.1f}s -> {out}")
    return out


@pytest.fixture(scope='session')
def geom_pdf(geom_bundle):
    env = {}
    pn = geom_bundle / 'pagenum.json'
    if pn.exists():
        env['PAGENUM_GLOBAL_TABLE'] = str(pn)
    return _run_pipe('build_geom.py', geom_bundle, 'geom.pdf', env)


@pytest.fixture(scope='session')
def classic_pdf(classic_bundle):
    env = {'PAGE_FONT': '1', 'LAYOUT_HEADINGS': '1'}
    lay = classic_bundle / 'lay.json'
    if lay.exists():
        env['LAYJSON'] = str(lay)
    return _run_pipe('build_classic.py', classic_bundle, 'classic.pdf', env)


# ---------- 通用特征提取助手（被各测试 import） ----------

def line_features(pdf_path):
    """从输出 PDF 提取每行特征：dict 列表，每行 {page, x0, y0, x1, y1, size, text}。

    size 取行内 span 字号的众数；text 为整行文本。
    """
    import fitz
    doc = fitz.open(pdf_path)
    npages = doc.page_count
    rows = []
    for pno, page in enumerate(doc):
        ph = page.rect.height
        for d in page.get_text('dict')['blocks']:
            if d.get('type') != 0:
                continue
            for ln in d.get('lines', []):
                spans = ln.get('spans', [])
                if not spans:
                    continue
                texts = [s.get('text', '') for s in spans]
                sizes = [s.get('size', 0) for s in spans]
                xs = [s['bbox'][0] for s in spans]
                ys = [s['bbox'][1] for s in spans]
                x1s = [s['bbox'][2] for s in spans]
                y1s = [s['bbox'][3] for s in spans]
                if not sizes:
                    continue
                # 行字号 = 众数（一行内可能混上标小字）
                size = max(set(sizes), key=sizes.count)
                rows.append({
                    'page': pno,
                    'x0': min(xs), 'y0': min(ys),
                    'x1': max(x1s), 'y1': max(y1s),
                    'size': size,
                    'text': ''.join(texts),
                })
    doc.close()
    return rows, npages
