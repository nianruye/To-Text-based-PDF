#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""目录页核对：源 OCR 行 vs 产物 PDF 文本。

用途：回答「这一页目录，源书有什么、我们还原出了什么、丢了什么」。
不依赖渲染路径（普通流/toc_pre/分离式/结构化都适用），只看文本层。

用法：
  /usr/bin/python3 src/tools/toc_check.py <book> <src.pdf> <out.pdf> [--pages 15,16]

输出：
  每页：源行数 / 命中行数 / 缺失行清单 / 产物多出的数字
  汇总：覆盖率 = 命中行 / 源行数
"""
import sys, re, json, argparse, unicodedata
import fitz
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _norm(s: str) -> str:
    """归一化：去空白、全半角统一、点线/省略号归一。"""
    s = unicodedata.normalize('NFKC', s)
    s = re.sub(r'[.·…．]{2,}', '', s)      # 点线
    s = re.sub(r'\s+', '', s)
    s = s.replace('—', '-').replace('–', '-').replace('－', '-')
    return s


def _furniture(t: str, y: float, page_h: float) -> str:
    """判定「版式元素」(不是目录条目): 返回类型或 ''。"""
    tt = str(t).strip()
    if re.fullmatch(r'\d{1,4}', tt):
        return '页码'
    if re.fullmatch(r'目\s*录(\s*\d{1,4})?|CONTENTS?', tt, re.I):
        return '书眉'
    if y and page_h and y < 0.12 * page_h:
        return '书眉区'          # 顶部区域且不像条目
    return ''


def _ocr_coords(book: str, data_dir: str | None):
    cands = []
    if data_dir:
        cands += list(Path(data_dir).glob('*spotting_coords.json'))
    cands += list((ROOT / 'data' / book).glob('*spotting_coords.json'))
    cands += list((ROOT / 'output' / 'uploaded' / f'_ocr_{book}').glob('*spotting_coords.json'))
    cands += list((ROOT / 'output' / f'{book}_full' / f'_ocr_{book}').glob('*spotting_coords.json'))
    for c in cands:
        if c.exists():
            return json.load(open(c, encoding='utf-8'))
    return {}


def _ocr_pages(book: str, data_dir: str | None):
    """找该书的 spotting lines（用于取目录页 OCR 行）。"""
    cands = []
    if data_dir:
        cands += list(Path(data_dir).glob('*spotting_lines.json'))
    cands += list((ROOT / 'data' / book).glob('*spotting_lines.json'))
    cands += list((ROOT / 'output' / 'uploaded' / f'_ocr_{book}').glob('*spotting_lines.json'))
    cands += list((ROOT / 'output' / f'{book}_full' / f'_ocr_{book}').glob('*spotting_lines.json'))
    for c in cands:
        if c.exists():
            return json.load(open(c, encoding='utf-8')), c
    return None, None


def _find_toc_pages(lines: dict) -> list[int]:
    """与 build_geom 同口径：书眉含「目录」的页 + 相邻条目页。"""
    def _rows(k):
        return [str(t).strip() for t in lines.get(k, []) if str(t).strip()]

    mark = [int(k) for k in lines if any(t.startswith('目录') and len(t) <= 6 for t in _rows(k)[:3])]
    if not mark:
        return []
    pages = set(range(min(mark), max(mark) + 1))

    def _like(k):
        n = 0
        for t in _rows(k):
            if (re.fullmatch(r'\d{1,4}', t) or re.match(r'^第[一二三四五六七八九十百千零\d]+[章节编]', t)
                    or re.match(r'^[一二三四五六七八九十]+[、\s]', t)
                    or re.search(r'[.·…．]{2,}\s*\d{1,4}$', t)):
                n += 1
        return n >= 5

    nxt = max(pages) + 1
    while nxt in {int(k) for k in lines} and nxt <= max(mark) + 6 and _like(str(nxt)):
        pages.add(nxt)
        nxt += 1
    return sorted(pages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('book')
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--pages', default='')
    ap.add_argument('--data-dir', default='')
    ap.add_argument('--json', default='')
    a = ap.parse_args()

    lines, lpath = _ocr_pages(a.book, a.data_dir)
    coords = _ocr_coords(a.book, a.data_dir)
    if lines is None:
        print(f'✗ {a.book}: 找不到 spotting_lines')
        return 2

    if a.pages:
        pages = [int(x) - 1 for x in a.pages.split(',')]
    else:
        pages = _find_toc_pages(lines)

    doc = fitz.open(a.out)
    report = []
    tot_src = tot_hit = 0
    for p in pages:
        src_rows = [str(t).strip() for t in lines.get(str(p), []) if str(t).strip()]
        if not src_rows:
            continue
        got = _norm(doc[p].get_text() if p < doc.page_count else '')
        missing = []
        furn = []
        _cy = coords.get(str(p), [])
        _ph = doc[p].rect.height if p < doc.page_count else 1000.0
        for t in src_rows:
            n = _norm(t)
            if not n:
                continue
            if n not in got:
                # 逐字兜底：OCR 行可能被拆成多行/合并，按「去重字符集」判
                if not all(ch in got for ch in set(n)):
                    _iy = next((i for i, x in enumerate(src_rows) if x == t), -1)
                    _yy = min((q[1] for q in _cy[_iy]), default=0) if 0 <= _iy < len(_cy) and _cy[_iy] else 0
                    # coords 是 px、_ph 是 pt，不能直接比。用「本页 coords 的 max y ≈ 页高」做比例：
                    # 免 DPI（各书 138~200 不同），口径与 _furniture 的 y/page_h 判据一致
                    _pmax = max((q[1] for _pl in _cy if _pl for q in _pl), default=0)
                    _rel = (_yy / _pmax) if (_yy and _pmax) else 0
                    k = _furniture(t, _rel * _ph, _ph)
                    (furn if k else missing).append(f'{t} [{k}]' if k else t)
        hit = len(src_rows) - len(missing)
        tot_src += len(src_rows)
        tot_hit += hit
        # 产物多出的数字（源里没有的）
        extra = sorted(set(re.findall(r'\d+', got)) - set(re.findall(r'\d+', ''.join(src_rows))))
        report.append({'page': p + 1, 'src_rows': len(src_rows), 'hit': hit,
                       'missing': missing, 'extra_nums': extra})
        print(f'p{p+1}: 源 {len(src_rows):3d} 行 | 命中 {hit:3d} | 缺 {len(missing):3d}'
              + (f' | 版式元素 {len(furn)}' if furn else '')
              + (f' | 多出数字 {extra[:6]}' if extra else ''))
        for m in missing[:6]:
            print(f'    缺(条目): {m[:50]!r}')
        for m in furn[:4]:
            print(f'    版式元素(忽略): {m[:46]!r}')

    if tot_src:
        print(f'\n合计: {tot_hit}/{tot_src} = {tot_hit / tot_src * 100:.1f}%')
    if a.json:
        json.dump(report, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return 0 if tot_hit == tot_src else 1


if __name__ == '__main__':
    sys.exit(main())
