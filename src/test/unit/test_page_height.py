#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""页高参数化 + 自定义 out-dir 候选测试（t59/battle12 repair）。

背景：三个普查/条带工具曾硬编码 wz7 页高 1443pt；高于 1443 的开本会静默丢页底候选。
覆盖：
- 合成一本 400×1600 的书（页底 y≈1450-1470 有字形墨块）→ census 缺省用源页高，检出 1 个候选；
- 同书显式 --page-height 1443（旧口径）→ 0 个（证明 1443 会丢页底）；
- 自定义 --out-dir + 非 wz7 book：pilot build 的默认候选应取 {out-dir}/missing_cells.json。
运行：/usr/bin/python3 -m pytest src/test/unit/test_page_height.py -v
"""
import json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
CENSUS = os.path.join(ROOT, 'src/tools/census_true_missing.py')
PILOT = os.path.join(ROOT, 'src/tools/api_pilot_build.py')


def _make_tall_book(tmp):
    import fitz
    data = os.path.join(tmp, 'data'); os.makedirs(data, exist_ok=True)
    doc = fitz.open(); page = doc.new_page(width=400, height=1600)
    # 20×20pt 十字块（字形墨块：h/w 6-40、fill≈0.36、无洞 -> census 的 char 类）
    page.draw_rect(fitz.Rect(100, 1458, 120, 1462), color=(0, 0, 0), fill=(0, 0, 0), width=0)
    page.draw_rect(fitz.Rect(108, 1450, 112, 1470), color=(0, 0, 0), fill=(0, 0, 0), width=0)
    src = os.path.join(tmp, 'book.pdf'); doc.save(src); doc.close()
    lines = {'0': ['測' * 68]}
    coords = {'0': [[[200, 200], [240, 200], [240, 2900], [200, 2900]]]}  # px=2×pt: x100-120, y100-1450
    json.dump(lines, open(os.path.join(data, 't_full_spotting_lines_patched.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(coords, open(os.path.join(data, 't_full_spotting_coords.json'), 'w', encoding='utf-8'))
    return data, src


def _census(tmp, data, src, extra):
    out = os.path.join(tmp, 'out.json')
    cmd = [sys.executable, CENSUS, '--book', 't', '--data-dir', data, '--src', src,
           '--out', out, '--crops', os.path.join(tmp, 'crops')] + extra
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout[-800:], r.stderr[-800:])
    return json.load(open(out, encoding='utf-8'))


def test_page_height_uses_source_page(tmp_path):
    """页高 1600（>1443）：缺省用源页高 -> 页底 1450-1470 候选被检出。"""
    data, src = _make_tall_book(str(tmp_path))
    j = _census(str(tmp_path), data, src, [])
    assert j['n'] == 1, j


def test_page_height_override_1443_drops_bottom(tmp_path):
    """显式 --page-height 1443（旧硬编码口径）：yb>1443 -> 页底候选被跳过（0 个）。"""
    data, src = _make_tall_book(str(tmp_path))
    j = _census(str(tmp_path), data, src, ['--page-height', '1443'])
    assert j['n'] == 0, j


def test_custom_out_dir_picks_local_candidates(tmp_path):
    """非 wz7 book + 自定义 --out-dir：pilot build 默认候选应取 {out-dir}/missing_cells.json。"""
    out = os.path.join(str(tmp_path), 'custom'); os.makedirs(out)
    json.dump({'items': [{'page': 1, 'x': 100, 'y0': 100, 'x1': 200, 'y1': 400,
                          'text': '測試文字', 'n': 4, 'cells': 4}]},
              open(os.path.join(out, 'missing_cells.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    cmd = [sys.executable, PILOT, '--book', 'wz6', '--out-dir', out,
           '--cols-per-page', '8', '--pages-per-batch', '10']
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout[-800:], r.stderr[-800:])
    assert os.path.exists(os.path.join(out, 'pilot25_items.json')), r.stdout[-800:]
    items = json.load(open(os.path.join(out, 'pilot25_items.json'), encoding='utf-8'))
    assert len(items) == 1 and items[0]['page'] == 1


def test_all_build_page_height_and_custom_out_dir(tmp_path):
    """api_candidates_all_build：页高用源页高（400×1600 书页底候选不被裁）+ 自定义 out-dir 取本地候选。"""
    import fitz
    out = os.path.join(str(tmp_path), 'allout'); os.makedirs(out)
    doc = fitz.open(); page = doc.new_page(width=400, height=1600)
    page.draw_rect(fitz.Rect(100, 1450, 120, 1462), color=(0, 0, 0), fill=(0, 0, 0), width=0)
    src = os.path.join(str(tmp_path), 'book.pdf'); doc.save(src); doc.close()
    json.dump({'items': [{'page': 1, 'x': 100, 'y0': 1440, 'x1': 120, 'y1': 1462,
                          'text': '測試文字', 'n': 4, 'cells': 4}]},
              open(os.path.join(out, 'missing_cells.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    ALL = os.path.join(ROOT, 'src/tools/api_candidates_all_build.py')
    # 缺省：源页高 1600 -> 条带覆盖 y≈1440-1470；自定义 out-dir 下默认候选 = {out}/missing_cells.json
    cmd = [sys.executable, ALL, '--book', 't', '--src', src, '--out-dir', out,
           '--cols-per-page', '8', '--pages-per-batch', '30']
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout[-800:], r.stderr[-800:])
    items = json.load(open(os.path.join(out, 'all_items.json'), encoding='utf-8'))
    assert len(items) == 1 and items[0]['page'] == 1, items
    from PIL import Image
    h_default = Image.open(items[0]['strip']).height
    # --page-height 1443：条带被裁到 1443 -> 高度更小
    cmd2 = cmd + ['--page-height', '1443']
    r2 = subprocess.run(cmd2, cwd=ROOT, capture_output=True, text=True)
    assert r2.returncode == 0, (r2.stdout[-800:], r2.stderr[-800:])
    items2 = json.load(open(os.path.join(out, 'all_items.json'), encoding='utf-8'))
    h_1443 = Image.open(items2[0]['strip']).height
    assert h_default > h_1443, (h_default, h_1443)
