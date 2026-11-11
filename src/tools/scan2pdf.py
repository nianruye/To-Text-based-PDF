#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan2pdf.py — 扫描书一键还原 v1（判书型 → 数据准备 → 构建 → 门禁 → 报告）。

设计：docs/scan2pdf_design.md（t115）。步骤 0–10；失败矩阵 exit 2–8；失败不覆盖 --out。
--skip-ocr + --data-dir：直接复用现有 coords/lines（不调 API）。
新书默认 VERT_MISSED_FIX=0；仅 data/<book>/ 或 --data-dir 内存在 fix JSON 时才启用。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))
PUNCT_GOLD = os.path.join(ROOT, 'data/punct_eval/punct_gold_v1.json')
CONTENT_GOLD = os.path.join(ROOT, 'data/punct_eval/content_gold_v1.json')

# 退出码 = docs/scan2pdf_design.md §2.2（设计契约；t159 对齐）
EXIT = dict(ok=0, usage=2, out_exists=2, data_missing=3, ocr=3, book=4,
            build=5, verify=6, reject=7, partial=8, manual=8)


def sha256(path):
    import hashlib
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''):
                h.update(b)
        return h.hexdigest()
    except OSError:
        return ''


def log(msg):
    print('[scan2pdf] ' + msg)


def detect_book_type(pdf, sample=12, book=None):
    """书型判断（书无关）：axis / has_frame / 纸型 / multi_format。"""
    import fitz
    # 优先复用 t115 书型探针缓存（data-driven；无 OCR 时 orientation/frame 的可靠来源）
    if book:
        cand = [os.path.join(ROOT, 'tmp_vert/scan2pdf/probe_%s.json' % book),
                os.path.join(ROOT, 'data/%s/probe_booktype.json' % book)]
        for cp in cand:
            if os.path.exists(cp):
                try:
                    pr = json.load(open(cp, encoding='utf-8'))
                    return dict(axis=pr.get('orientation', {}).get('label', 'vertical'),
                                has_frame=pr.get('frame', {}).get('label') == 'has_frame',
                                page_size=[pr.get('paper', {}).get('width_pt'),
                                           pr.get('paper', {}).get('height_pt')],
                                pages=pr.get('pages'),
                                multi_format=bool(pr.get('paper', {}).get('multi_format')),
                                sizes=pr.get('paper', {}).get('top_sizes', []),
                                confidence=pr.get('confidence', 1.0), source='probe_cache',
                                preflight=dict(pages=6, basis='probe_cache', confidence='high',
                                               note='t115 探针缓存（6 页前导）'))
                except Exception:
                    pass
    d = fitz.open(pdf)
    n = len(d)
    sizes = {}
    keys = []
    for i in range(n):
        r = d[i].rect
        found = None
        for k in keys:
            if abs(k[0] - r.width) <= 5 and abs(k[1] - r.height) <= 5:
                found = k; break
        if found is None:
            found = (round(r.width, 1), round(r.height, 1)); keys.append(found)
        sizes[found] = sizes.get(found, 0) + 1
    dom = max(sizes, key=sizes.get)
    multi = False
    if n >= 20:
        multi = sum(1 for c in sizes.values() if c / n >= 0.05) >= 2
    ratio = dom[0] / dom[1] if dom[1] else 0
    axis = 'horizontal' if ratio > 1.05 else 'vertical'
    frame_pages = 0
    checked = 0
    for i in sorted(set([0, n // 2, n - 1] + list(range(min(sample, n))))):
        if i >= n: continue
        checked += 1
        try:
            drawings = d[i].get_drawings()
        except Exception:
            drawings = []
        lines = 0
        for dr in drawings:
            for item in dr.get('items', []):
                if item[0] == 'l' and len(item) >= 3:
                    p1, p2 = item[1], item[2]
                    if abs(p1.x - p2.x) > 0.6 * dom[0] or abs(p1.y - p2.y) > 0.6 * dom[1]:
                        lines += 1
        if lines >= 2:
            frame_pages += 1
    has_frame = bool(checked and frame_pages / checked >= 0.5)
    if not has_frame:
        # 扫描页无矢量线：用页面图像暗像素长直线估计版框（书无关；numpy 缺失则跳过）
        try:
            import numpy as np
            hit = 0; nchk = 0
            for i in sorted(set([0, n // 2, n - 1] + list(range(min(6, n))))):
                if i >= n: continue
                pix = d[i].get_pixmap(dpi=72)
                arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                gray = arr[:, :, :3].mean(axis=2) if pix.n >= 3 else arr[:, :, 0]
                dark = gray < 128
                h, w = gray.shape
                rows_idx = [i for i in range(h) if dark[i].mean() > 0.60]
                cols_idx = [j for j in range(w) if dark[:, j].mean() > 0.60]
                nchk += 1
                top = any(i < 0.12 * h for i in rows_idx); bottom = any(i > 0.88 * h for i in rows_idx)
                left = any(j < 0.14 * w for j in cols_idx); right = any(j > 0.86 * w for j in cols_idx)
                if axis == 'vertical':
                    if left and right:
                        hit += 1
                else:
                    if top and bottom:
                        hit += 1
            if nchk and hit / nchk >= 0.5:
                has_frame = True
        except Exception:
            pass
    return dict(axis=axis, has_frame=has_frame, page_size=list(dom), pages=n,
                multi_format=multi, sizes=[{'size': list(k), 'pages': v} for k, v in
                                           sorted(sizes.items(), key=lambda kv: -kv[1])],
                confidence=1.0 if not multi else 0.6, source='computed',
                preflight=dict(pages=min(6, n), basis='page-size/aspect',
                               confidence='low',
                               note='新书建议先跑 6 页前导（人工确认书型/纸型）再定 pipeline'))


def _mode_of(name):
    n = os.path.basename(name).lower()
    if 'spotting' in n: return 'spotting'
    if 'layout' in n: return 'layout'
    return 'unknown'


def _stem(name):
    n = os.path.basename(name)
    for tag in ('_spotting_coords', '_spotting_lines_patched', '_spotting_lines',
                '_layout_coords', '_layout_lines_patched', '_layout_lines',
                '_coords', '_lines_patched', '_lines'):
        if tag in n:
            return n.split(tag)[0]
    return os.path.splitext(n)[0]


def infer_axis_from_coords(coords_path, sample=6):
    """用 OCR 框长宽比判轴（书无关）：横排行框宽>>高；竖排列框高>>宽。返回 horizontal/vertical/None。"""
    try:
        import statistics
        co = json.load(open(coords_path, encoding='utf-8'))
        ws, hs = [], []
        for k in list(co)[:sample]:
            for pts in (co.get(k) or []):
                if not pts: continue
                xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                w = max(xs) - min(xs); h = max(ys) - min(ys)
                if w > 0 and h > 0:
                    ws.append(w); hs.append(h)
        if len(ws) < 5:
            return None
        mw, mh = statistics.median(ws), statistics.median(hs)
        if mw > 1.5 * mh: return 'horizontal'
        if mh > 1.5 * mw: return 'vertical'
    except Exception:
        pass
    return None


def resume_key(book, input_sha, fix_sha, coords_sha, lines_sha, mode, pipeline, pages):
    return dict(book=book, input_sha256=input_sha, fix_sha256=fix_sha,
                coords_sha256=coords_sha, lines_sha256=lines_sha,
                mode=mode, pipeline=pipeline, pages=pages or '')


def find_data(data_dir, coords=None, lines=None):
    """coords/lines 同源配对：spotting 优先、禁止 layout/spotting 混配。
    返回 (coords, lines, meta)；meta 记录 mode/reason。"""
    import glob
    meta = dict(mode=None, reason='', mixed_forbidden=True, coords=None, lines=None)
    if coords or lines:
        if not (coords and lines):
            meta['reason'] = '显式 --coords/--lines 必须同时给出'
            return None, None, meta
        if not (os.path.exists(coords) and os.path.exists(lines)):
            meta['reason'] = '显式 coords/lines 不存在'
            return None, None, meta
        mc, ml = _mode_of(coords), _mode_of(lines)
        if mc != ml:
            meta['reason'] = '禁止混配：coords=%s lines=%s' % (mc, ml)
            return None, None, meta
        if _stem(coords) != _stem(lines):
            meta['reason'] = '非同源：stem %s vs %s' % (_stem(coords), _stem(lines))
            return None, None, meta
        meta.update(mode=mc, reason='显式 --coords/--lines（同源 %s）' % mc,
                    coords=coords, lines=lines)
        return coords, lines, meta
    if not data_dir or not os.path.isdir(data_dir):
        meta['reason'] = 'data-dir 不存在'
        return None, None, meta
    cs = sorted(glob.glob(os.path.join(data_dir, '*coords*.json')))
    ls = sorted(glob.glob(os.path.join(data_dir, '*lines*patched*.json'))) or \
         sorted(glob.glob(os.path.join(data_dir, '*lines*.json')))
    # spotting 优先：同 stem 的 spotting coords/lines
    for c in cs:
        if _mode_of(c) != 'spotting': continue
        for l in ls:
            if _mode_of(l) == 'spotting' and _stem(c) == _stem(l):
                meta.update(mode='spotting', reason='spotting 同源配对优先（%s）' % _stem(c),
                            coords=c, lines=l)
                return c, l, meta
    # 回退：同 stem 的 layout / unknown 配对（仍禁止 spotting/layout 混配）
    for c in cs:
        for l in ls:
            if _mode_of(c) == _mode_of(l) or 'unknown' in (_mode_of(c), _mode_of(l)):
                if _stem(c) == _stem(l):
                    meta.update(mode=_mode_of(c), reason='同源配对（%s，非 spotting）' % _stem(c),
                                coords=c, lines=l)
                    return c, l, meta
    meta['reason'] = '无同源 coords/lines 配对（禁止 layout/spotting 混配）'
    return None, None, meta


def find_fix(data_dir, book, explicit_fix=''):
    """fix 守卫（书无关，设计 §5.3）：
    - --fix <path> 显式用户 opt-in（source=explicit）
    - data-dir（含 data/<book>/）内 per-book fix / fix_pointer.json（source=book_data）
    - 否则 none（VERT_MISSED_FIX=0）；**绝不加载 docs 下修复、无书名映射**。
    返回 (path, source, sha256)。"""
    import glob
    if explicit_fix:
        if not os.path.exists(explicit_fix):
            return '', 'explicit_missing', ''
        return explicit_fix, 'explicit', sha256(explicit_fix)
    cands = []
    if data_dir and os.path.isdir(data_dir):
        ptr = os.path.join(data_dir, 'fix_pointer.json')
        if os.path.exists(ptr):
            try:
                pj = json.load(open(ptr, encoding='utf-8'))
                rel = pj.get('fix') or pj.get('path')
                if rel:
                    fp = rel if os.path.isabs(rel) else os.path.join(data_dir, rel)
                    if os.path.exists(fp):
                        return fp, 'book_data', sha256(fp)
            except Exception:
                pass
        for base in (data_dir, os.path.join(data_dir, book)):
            if os.path.isdir(base):
                cands += glob.glob(os.path.join(base, '*missed*fix*.json'))
                cands += glob.glob(os.path.join(base, '*fix*.json'))
    if cands:
        fp = sorted(set(cands))[0]
        return fp, 'book_data', sha256(fp)
    return '', 'none', ''


def layout_requested(args):
    """默认关：只有显式 --layout 或 LAYOUT_HEADINGS/FIGS/TOC 非 0 才读/传 LAYJSON。"""
    if getattr(args, 'layout', False):
        return True
    for k in ('LAYOUT_HEADINGS', 'LAYOUT_FIGS', 'LAYOUT_TOC'):
        if os.environ.get(k, '').lower() in ('1', 'true', 'toc'):
            return True
    return False


def find_layout(data_dir, ocr_dir, book, src_pdf, jobs_path=None):
    """找 canonical layout.json；若无但有 layout raw，则用 ocr_book.convert_layout_json 生成。"""
    import glob
    cands = []
    for d in [data_dir, ocr_dir]:
        if d and os.path.isdir(d):
            cands += [os.path.join(d, '%s_layout.json' % book),
                      os.path.join(d, '%s_layout.json' % book.replace('-', '_'))]
    for p in cands:
        if os.path.exists(p):
            try:
                n = len(json.load(open(p, encoding='utf-8')))
            except Exception:
                n = 0
            return p, n, 'existing'
    if not ocr_dir or not os.path.isdir(ocr_dir):
        return None, 0, 'missing'
    if not glob.glob(os.path.join(ocr_dir, 'raw', 'layout_*.json')):
        return None, 0, 'missing'
    try:
        import ocr_book
        p, n = ocr_book.convert_layout_json(ocr_dir, src_pdf, book)
        return p, n, 'converted'
    except Exception as e:
        return None, 0, 'error:%s' % e


def parse_pages(pages, n):
    if not pages:
        return list(range(n))
    out = []
    for part in str(pages).split(','):
        part = part.strip()
        if not part: continue
        if '-' in part:
            a, b = part.split('-', 1); out += list(range(int(a) - 1, int(b)))
        else:
            out.append(int(part) - 1)
    return [i for i in out if 0 <= i < n]


def slice_inputs(coords_path, lines_path, src_pdf, idxs, tmpdir):
    """按页子集切 coords/lines + 源 PDF（dry-run --pages）。"""
    import fitz
    coords = json.load(open(coords_path, encoding='utf-8'))
    lines = json.load(open(lines_path, encoding='utf-8'))
    sc = {str(i): coords[str(i)] for i in idxs if str(i) in coords}
    sl = {str(i): lines[str(i)] for i in idxs if str(i) in lines}
    cp = os.path.join(tmpdir, 'coords_slice.json'); lp = os.path.join(tmpdir, 'lines_slice.json')
    json.dump(sc, open(cp, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(sl, open(lp, 'w', encoding='utf-8'), ensure_ascii=False)
    sp = os.path.join(tmpdir, 'src_slice.pdf')
    d = fitz.open()
    for i in idxs:
        d.insert_pdf(fitz.open(src_pdf), from_page=i, to_page=i)
    d.save(sp); d.close()
    return cp, lp, sp


def parse_verify_geom(stdout):
    import re
    out = dict(pages=None, pages_src=None, pitch_ok_pct=None, height_ok_pct=None,
               blank_pages=None, overflow_pages=None, verdict=None)
    t = stdout or ''
    m = re.search(r'页数:\s*源 OCR\s*(\d+)\s*页\s*\|\s*输出 PDF\s*(\d+)\s*页', t)
    if m:
        out['pages_src'] = int(m.group(1)); out['pages'] = int(m.group(2))
    m = re.search(r'pitch 误差 <3%\s*:\s*([0-9.]+)%', t)
    if m: out['pitch_ok_pct'] = float(m.group(1))
    m = re.search(r'底层占位|底部占位 <8% 偏差:\s*([0-9.]+)%', t)
    if m: out['height_ok_pct'] = float(m.group(1))
    m = re.search(r'空白页\s*(\d+)\s*溢出页\(占位\)\s*(\d+)', t)
    if m:
        out['blank_pages'] = int(m.group(1)); out['overflow_pages'] = int(m.group(2))
    m = re.search(r'== 退出码 (PASS|FAIL) ==', t)
    if m: out['verdict'] = m.group(1)
    return out


def run_verify_geom(pdf, coords, lines, floor=None, src_pdf=None):
    import os
    floor = floor if floor is not None else float(os.environ.get('VERIFY_PITCH_FLOOR', '85'))
    env = dict(os.environ); env['VERIFY_PITCH_FLOOR'] = str(floor)
    env.setdefault('PYTHONHASHSEED', '0')
    cmd = ['/usr/bin/python3', os.path.join(ROOT, 'src/test/verify_geom.py'), pdf, coords, lines]
    if src_pdf and os.path.exists(src_pdf):
        cmd += ['--src-pdf', src_pdf]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=ROOT, env=env)
    m = parse_verify_geom(p.stdout + '\n' + p.stderr)
    m.update(exit=p.returncode, floor=floor,
             stdout_tail='\n'.join((p.stdout or '').strip().splitlines()[-4:]))
    m['pass_'] = bool(p.returncode == 0 and m.get('verdict') == 'PASS')
    return m



def attach_typography(report, args, lines_path):
    """t239：排版评测（不改变几何门禁；决策 A 语义在 verify_typography 内）。"""
    try:
        tool = os.path.join(ROOT, 'src/test/verify_typography.py')
        if not os.path.exists(tool):
            return
        outj = args.out + '.typography.json'
        bt = 'vertical' if (args.book_type or {}).get('axis') == 'vertical' else 'horizontal'
        cmd = ['/usr/bin/python3', tool, args.out, '--json', outj, '--book-type', bt]
        if args.src_pdf if hasattr(args, 'src_pdf') else False:
            cmd += ['--src-pdf', args.src_pdf]
        if lines_path:
            cmd += ['--lines', lines_path]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, PYTHONHASHSEED='0'))
        if os.path.exists(outj):
            report['typography'] = json.load(open(outj, encoding='utf-8'))
        else:
            report['typography'] = dict(tool='verify_typography', error='no report', rc=p.returncode)
    except Exception as e:
        report['typography'] = dict(tool='verify_typography', error=str(e))

def build_pdf(args, coords, lines, src_pdf, out_tmp, fix_path):
    pipeline = getattr(args, 'pipeline_resolved', None) or args.pipeline
    if pipeline == 'auto':
        pipeline = 'vert' if args.book_type['axis'] == 'vertical' else 'geom'
    if pipeline == 'vert':
        script = os.path.join(ROOT, 'src/pipelines/build_vert.py')
        cmd = ['/usr/bin/python3', script, lines, coords, out_tmp, src_pdf]
    else:
        # 横排 canonical：#37 —— fit_positional 两趟（pass1 测高 + pass2 ratio 重渲染）
        script = os.path.join(ROOT, 'src/calibration/fit_positional.py')
        cmd = ['/usr/bin/python3', script, lines, coords, out_tmp, src_pdf]
    env = dict(os.environ)
    env['VERT_TMP'] = os.path.join(tempfile.gettempdir(), 'scan2pdf_%s' % args.book)
    env['VERT_MISSED_FIX'] = fix_path if fix_path else '0'
    # 可复现：build 端稳定 hash（消除 set/dict 顺序导致的文本差异）
    env.setdefault('PYTHONHASHSEED', '0')
    # LAYJSON / 图片 passthrough：只有本次 scan2pdf 显式拿到 layout 才开启；默认构建不读
    _lay = getattr(args, 'layout_json', '') or ''
    if _lay and pipeline == 'geom':
        env['LAYJSON'] = _lay
        env.setdefault('LAYOUT_HEADINGS', '0')
        env.setdefault('LAYOUT_FIGS', '1' if getattr(args, 'layout', False) else '0')
        env.setdefault('LAYOUT_TOC', '1' if getattr(args, 'layout', False) else '0')
        env.setdefault('PAGE_IMAGE_FULL_RATIO', '0.40')
        env.setdefault('PAGE_IMAGE_TEXT_MODE', 'auto')
    # 横排标定审计：build_geom 写 <out>.calib.json（fit_positional 两趟共用最终路径）
    if pipeline == 'geom':
        _o = getattr(args, 'out', None)
        if _o:
            env['CALIB_OUT'] = _o + '.calib.json'
        env['CALIB_BOOK'] = args.book
    log('构建: %s (pipeline=%s, VERT_MISSED_FIX=%s)' % (os.path.basename(script), pipeline,
                                                       fix_path or '0'))
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, cwd=ROOT, env=env)
    ok = p.returncode == 0 and os.path.exists(out_tmp) and os.path.getsize(out_tmp) > 0
    return ok, dict(pipeline=pipeline, returncode=p.returncode, cmd=' '.join(cmd),
                    stdout_tail='\n'.join((p.stdout or '').strip().splitlines()[-8:]),
                    stderr_tail='\n'.join((p.stderr or '').strip().splitlines()[-8:]))


def effective_verdict(verdict, multi_format):
    """severity 口径：多纸型至少 MANUAL_ONLY（不 AUTO_PASS）。
    说明：severity ≥ MANUAL_ONLY 表示 MANUAL_ONLY 与 REJECT 都满足；REJECT 更严、不被弱化。"""
    if not multi_format:
        return verdict, ''
    if verdict == 'AUTO_PASS':
        return 'MANUAL_ONLY', ('多纸型：AUTO_PASS 降为 MANUAL_ONLY（severity ≥ MANUAL_ONLY；'
                               '不静默按主导纸型）')
    if verdict == 'PASS':
        return 'MANUAL_ONLY', ('多纸型：横排 PASS 降为 MANUAL_ONLY（review_required=true；'
                               '不静默按主导纸型）')
    if verdict == 'MANUAL_ONLY':
        return verdict, '多纸型：维持 MANUAL_ONLY（severity ≥ MANUAL_ONLY）'
    return verdict, '多纸型：维持 REJECT（severity ≥ MANUAL_ONLY，REJECT 更严、不弱化）'


def multi_format_clause(gate_verdict, verdict_effective, multi_format, paper_sizes=None):
    """多纸型口径块（captain 决定）：禁止 AUTO_PASS；REJECT 保持（不降级掩盖真问题）；
    多纸型必须人工复核。"""
    if not multi_format:
        return None
    sizes = paper_sizes or []
    def _wh(x):
        sz = x.get('size') if isinstance(x, dict) else None
        w = x.get('width_pt') if isinstance(x, dict) else None
        h = x.get('height_pt') if isinstance(x, dict) else None
        if w is None and isinstance(sz, (list, tuple)) and len(sz) >= 2:
            w, h = sz[0], sz[1]
        return w, h
    dist = ', '.join('%sx%s:%s页' % (_wh(s)[0], _wh(s)[1], s.get('pages'))
                     for s in sizes[:5] if isinstance(s, dict))
    return dict(detected=True, gate_verdict=gate_verdict, verdict_effective=verdict_effective,
                auto_pass_forbidden=True, review_required=True, severity='>=MANUAL_ONLY',
                paper_sizes=sizes[:5], paper_distribution=dist,
                acceptance_wording='不 AUTO_PASS；多纸型必须 review_required=true（MANUAL_ONLY 或 REJECT 均可，REJECT 更严）',
                note=('多纸型（%s）：需要人工确认版面；REJECT 保持为 REJECT（真实 punct/content 缺陷，不降级掩盖）'
                      % (dist or '未记录纸型分布')))


def call_gate(args, pdf, coords, lines, src_pdf, gate_out):
    cmd = ['/usr/bin/python3', os.path.join(ROOT, 'src/tools/quality_gate.py'),
           '--book', args.book, '--pdf', pdf, '--coords', coords, '--lines', lines,
           '--gold', PUNCT_GOLD, '--out', gate_out]
    if os.path.exists(CONTENT_GOLD):
        cmd += ['--content-gold', CONTENT_GOLD]
    if src_pdf and os.path.exists(src_pdf):
        cmd += ['--src-pdf', src_pdf]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=ROOT)
    verdict = None
    if os.path.exists(gate_out):
        try:
            verdict = json.load(open(gate_out, encoding='utf-8')).get('verdict')
        except Exception:
            verdict = None
    return p.returncode, verdict, '\n'.join((p.stdout or '').strip().splitlines()[-3:])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--book', required=True)
    ap.add_argument('--ocr-mode', default='auto', choices=['auto', 'layout', 'spotting'])
    ap.add_argument('--layout', action='store_true', help='显式启用 LAYJSON（默认关；也可用 LAYOUT_HEADINGS/FIGS/TOC=1）')
    ap.add_argument('--pipeline', default='auto', choices=['auto', 'vert', 'geom'])
    ap.add_argument('--data-dir', default='')
    ap.add_argument('--coords', default='')
    ap.add_argument('--fix', default='')
    ap.add_argument('--corrected-text', default='', help='每书文本校正 JSON；缺省 data/<book>/corrected_text.json 存在则自动用')
    ap.add_argument('--lines', default='')
    ap.add_argument('--skip-ocr', action='store_true')
    ap.add_argument('--token-file', default='/tmp/paddle_token')
    ap.add_argument('--pages', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--ocr-pages-per-batch', type=int, default=50)
    ap.add_argument('--ocr-max-pixels', type=int, default=None)
    ap.add_argument('--ocr-min-pixels', type=int, default=None)
    ap.add_argument('--ocr-orientation', type=int, default=None, choices=[0, 1])
    ap.add_argument('--ocr-unwarp', type=int, default=None, choices=[0, 1])
    ap.add_argument('--ocr-layout-shape', default=None)
    ap.add_argument('--report', default='')
    args = ap.parse_args(argv)
    args.layout_json = ''
    args.layout = bool(getattr(args, 'layout', False))
    report = dict(tool='scan2pdf', version='v1', book=args.book, input=args.input, out=args.out,
                  input_sha256=sha256(args.input), steps=[], exit=None,
                  book_type=None, data=None, build=None, gate=None,
                  env=dict(PYTHONHASHSEED='0'))
    import time
    _t0 = time.time()

    def step(name, **kw):
        report['steps'].append(dict(name=name, elapsed_ms=int((time.time() - _t0) * 1000), **kw))
    if not os.path.exists(args.input):
        log('输入不存在: %s' % args.input); report['exit'] = EXIT['usage']
        return EXIT['usage']
    if os.path.exists(args.out) and not args.force:
        rep = args.out + '.report.json'
        resume = False
        try:
            prev = json.load(open(rep, encoding='utf-8'))
            resume = prev.get('tool') == 'scan2pdf' and prev.get('book') == args.book
        except Exception:
            resume = False
        if resume:
            log('输出已存在且为本工具产物：默认不覆盖（resume 复用）；--force 才重建')
            report['resume'] = True
        else:
            log('输出已存在（--force 才覆盖）: %s' % args.out); report['exit'] = EXIT['out_exists']
            return EXIT['out_exists']
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or '.', exist_ok=True)
    # 步骤 1：书型
    try:
        bt = detect_book_type(args.input, book=args.book)
    except Exception as e:
        log('书型判断失败: %s' % e); report['exit'] = EXIT['usage']
        return EXIT['usage']
    args.book_type = bt
    report['book_type'] = bt
    report['preflight'] = bt.get('preflight')
    report['mixed_axis_supported'] = False
    report['v1_limitations'] = ['mixed 书型未实现（仅 probe/前导后人工判）',
                                '多纸型不 AUTO_PASS、review_required=true',
                                'LAYJSON 图片 passthrough v1：自动整页/正文图块、文字 invisible 待实现（开关默认关）']
    log('书型: %s, has_frame=%s, size=%s, multi_format=%s' %
        (bt['axis'], bt['has_frame'], bt['page_size'], bt['multi_format']))
    # 步骤 2：数据
    if args.skip_ocr:
        coords, lines, dmeta = find_data(args.data_dir, args.coords or None, args.lines or None)
        if not coords or not lines:
            log('数据配对失败: %s' % dmeta.get('reason')); report['exit'] = EXIT['data_missing']
            report['data'] = dict(source='skip-ocr', data_dir=args.data_dir, reason=dmeta.get('reason'))
            return EXIT['data_missing']
        data = dict(source='skip-ocr', data_dir=args.data_dir, coords=coords, lines=lines,
                    mode=dmeta.get('mode'), reason=dmeta.get('reason'),
                    coords_sha256=sha256(coords), lines_sha256=sha256(lines))
        step('data', source='skip-ocr', mode=dmeta.get('mode'))
    else:
        ocr_out = os.path.join(os.path.dirname(os.path.abspath(args.out)), '_ocr_' + args.book)
        cmd = ['/usr/bin/python3', os.path.join(ROOT, 'src/tools/ocr_book.py'),
               '--book', args.book, '--input', args.input, '--out-dir', ocr_out,
               '--token-file', args.token_file, '--mode', args.ocr_mode if args.ocr_mode != 'auto' else 'both',
               '--pages-per-batch', str(args.ocr_pages_per_batch), '--resume']
        if args.pages: cmd += ['--pages', args.pages]
        for _flag, _val in (('--ocr-max-pixels', getattr(args, 'ocr_max_pixels', None)),
                            ('--ocr-min-pixels', getattr(args, 'ocr_min_pixels', None)),
                            ('--ocr-orientation', getattr(args, 'ocr_orientation', None)),
                            ('--ocr-unwarp', getattr(args, 'ocr_unwarp', None)),
                            ('--ocr-layout-shape', getattr(args, 'ocr_layout_shape', None))):
            if _val is not None:
                cmd += [_flag, str(_val)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=7200, cwd=ROOT,
                           env=dict(os.environ, PYTHONHASHSEED='0'))
        if p.returncode != 0:
            log('OCR 失败（exit %d）' % p.returncode); report['exit'] = EXIT['ocr']
            report['ocr'] = dict(returncode=p.returncode, tail=(p.stdout + p.stderr)[-800:])
            return EXIT['ocr']
        dpath = args.data_dir or ocr_out
        coords, lines, dmeta = find_data(dpath, args.coords or None, args.lines or None)
        if (not coords or not lines) and dpath != ocr_out:
            coords, lines, dmeta = find_data(ocr_out, args.coords or None, args.lines or None)
        if not coords or not lines:
            log('OCR 完成但缺 coords/lines（检查 ocr_book 转换）'); report['exit'] = EXIT['data_missing']
            return EXIT['data_missing']
        data = dict(source='ocr', data_dir=args.data_dir or ocr_out, coords=coords, lines=lines,
                    mode=dmeta.get('mode'), reason=dmeta.get('reason'),
                    coords_sha256=sha256(coords), lines_sha256=sha256(lines),
                    ocr_mode=args.ocr_mode, pages_per_batch=args.ocr_pages_per_batch)
        _ep = os.path.join(ocr_out, 'ocr_params_effective.json')
        if os.path.exists(_ep):
            try:
                report['ocr_params'] = json.load(open(_ep, encoding='utf-8'))
            except Exception as e:
                report['ocr_params'] = {'error': str(e)}
        _jp = os.path.join(ocr_out, 'jobs.json')
        if os.path.exists(_jp):
            try:
                report['ocr_jobs'] = {k: v.get('jobId') for k, v in
                                      json.load(open(_jp, encoding='utf-8')).items()
                                      if isinstance(v, dict)}
            except Exception:
                pass
        step('data', source='ocr', ocr_mode=args.ocr_mode, batch=args.ocr_pages_per_batch)
    report['data'] = data
    # 每书文本校正（CORRECTED_TEXT）：OCR lines 加载后、--pages 切片前应用
    _ct_tmpdir = os.path.join(os.path.dirname(os.path.abspath(args.out)), '_scan2pdf_' + args.book)
    os.makedirs(_ct_tmpdir, exist_ok=True)
    _ct_arg = getattr(args, 'corrected_text', '') or ''
    _ct_path = _ct_arg or os.path.join(ROOT, 'data', args.book, 'corrected_text.json')
    _ct_source = 'explicit' if _ct_arg else 'book_data'
    if _ct_arg and not os.path.exists(_ct_path):
        log('--corrected-text 路径不存在: %s' % _ct_path); report['exit'] = EXIT['usage']
        return EXIT['usage']
    if not os.path.exists(_ct_path):
        report['corrected_text'] = dict(enabled=False, path=None, source='disabled',
                                        sha256=None, pages=[], pages_count=0,
                                        replaced=0, applied=0, skipped=0,
                                        warnings=[], warn=[], line_counts={})
    else:
        try:
            import importlib.util as _ilu
            _spec = _ilu.spec_from_file_location('corrected_text', os.path.join(ROOT, 'src/tools/corrected_text.py'))
            _ctmod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_ctmod)
            _lines_doc = json.load(open(lines, encoding='utf-8'))
            _patched, _cstats = _ctmod.apply_corrected_text(_lines_doc, _ct_path, source=_ct_source)
        except Exception as e:
            log('corrected_text 失败: %s' % e); report['exit'] = EXIT['usage']
            return EXIT['usage']
        report['corrected_text'] = _cstats
        for _w in _cstats.get('warnings') or []:
            print('[corrected_text] WARN %s page=%s line=%s: %s' % (
                _w.get('code'), _w.get('page'), _w.get('line'), _w.get('message')),
                file=sys.stderr, flush=True)
        if _cstats.get('applied'):
            _ct_lines = os.path.join(_ct_tmpdir, 'lines_corrected.json')
            json.dump(_patched, open(_ct_lines, 'w', encoding='utf-8'), ensure_ascii=False)
            data['lines_sha256_original'] = data.get('lines_sha256')
            data['lines'] = _ct_lines
            data['lines_sha256'] = sha256(_ct_lines)
            lines = _ct_lines
            log('corrected_text: %d 条（%d 页，跳过 %d）' % (
                _cstats['applied'], _cstats.get('pages_count', 0), _cstats['skipped']))
    # LAYJSON：layout mode/auto 时生成/查找；spotting 不使用
    if layout_requested(args):
        _ocr_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), '_ocr_' + args.book)
        _lay, _nlay, _lsrc = find_layout(args.data_dir, _ocr_dir, args.book, args.input)
        if _lay:
            args.layout_json = _lay
            report['layout'] = dict(path=_lay, pages=_nlay, source=_lsrc, sha256=sha256(_lay))
            log('LAYJSON: %s (%s 页, %s)' % (_lay, _nlay, _lsrc))
        else:
            report['layout'] = dict(path=None, pages=0, source=_lsrc, requested=True)
    else:
        report['layout'] = dict(path=None, pages=0, source='disabled', requested=False)
    # 书型二次判定：无探针缓存时用 OCR 框长宽比（横排/竖排）修正
    if bt.get('source') == 'computed':
        ax = infer_axis_from_coords(data['coords'])
        if ax:
            bt['axis'] = ax
            bt['axis_refined_by'] = 'coords_boxes'
            args.book_type = bt
            report['book_type'] = bt
            log('书型修正（OCR 框长宽比）: %s' % ax)
    # 管线解析（resume 键用）
    pipeline = args.pipeline if args.pipeline != 'auto' else ('vert' if bt['axis'] == 'vertical' else 'geom')
    args.pipeline_resolved = pipeline
    report['pipeline'] = pipeline
    # 步骤 3：新书 fix 守卫
    fix, fix_source, fix_sha = find_fix(args.data_dir, args.book, args.fix)
    if fix_source == 'explicit_missing':
        log('--fix 路径不存在: %s' % args.fix); report['exit'] = EXIT['usage']
        return EXIT['usage']
    report['fix'] = dict(path=fix or None, source=fix_source, sha256=fix_sha,
                         VERT_MISSED_FIX=fix or '0')
    step('fix_guard', source=fix_source, sha256=fix_sha)
    # 输出复用（默认不覆盖）：本工具产物 + book/input 匹配 -> 跳过构建，只重跑门禁
    resume_existing = False
    key = resume_key(args.book, report['input_sha256'], fix_sha,
                     data.get('coords_sha256', ''), data.get('lines_sha256', ''),
                     data.get('mode'), args.pipeline_resolved, args.pages)
    report['resume_key'] = key
    if report.get('resume'):
        try:
            prev = json.load(open(args.out + '.report.json', encoding='utf-8'))
            pk = prev.get('resume_key') or {}
            diff = {k: (pk.get(k), key.get(k)) for k in key if pk.get(k) != key.get(k)}
            resume_existing = bool(pk) and not diff
            if not resume_existing:
                log('复用键不匹配：拒绝覆盖（--force 重建或换 --out）')
                report['resume_mismatch'] = dict(mismatch=diff, prev_key=pk or None,
                                                 note='复用键 = book+input_sha+fix_sha+coords_sha+lines_sha+mode+pipeline+pages')
                report['exit'] = EXIT['usage']
                rp0 = args.report or (args.out + '.report.json')
                json.dump(report, open(rp0, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                return EXIT['usage']
        except Exception:
            resume_existing = False
    if resume_existing:
        report['resume_note'] = ('复用键匹配（book+input_sha+fix_sha+coords_sha+lines_sha+mode+pipeline+pages）：'
                                 '默认不覆盖、复用已有 out；--force 才重建')
    step('book_type', axis=bt['axis'], multi_format=bt['multi_format'])
    # --pages 子集
    tmpdir = os.path.join(os.path.dirname(os.path.abspath(args.out)), '_scan2pdf_' + args.book)
    os.makedirs(tmpdir, exist_ok=True)
    src_for_verify = args.input
    if args.pages:
        import fitz
        n = len(fitz.open(args.input))
        idxs = parse_pages(args.pages, n)
        coords, lines, src_for_verify = slice_inputs(coords, lines, args.input, idxs, tmpdir)
        report['pages'] = args.pages
    # 步骤 4-6：构建到临时文件（失败不覆盖 out）
    if resume_existing:
        report['build'] = dict(skipped='resume_existing', reason='默认不覆盖已有本工具产物；--force 才重建')
        step('build', skipped='resume_existing')
    else:
        out_tmp = os.path.join(tmpdir, 'build_' + os.path.basename(args.out))
        ok, binfo = build_pdf(args, coords, lines, args.input, out_tmp, fix)
        report['build'] = binfo
        if not ok:
            log('构建失败（exit %s）' % binfo.get('returncode')); report['exit'] = EXIT['build']
            return EXIT['build']
        step('build', cmd=binfo.get('cmd'), returncode=binfo.get('returncode'))
        # 步骤 7：页数 1:1 校验
        try:
            import fitz
            n_out = len(fitz.open(out_tmp)); n_src = len(fitz.open(src_for_verify))
        except Exception:
            n_out = n_src = 0
        report['pages_out'] = n_out; report['pages_src'] = n_src
        if n_out != n_src:
            log('页数不 1:1: %d vs %d' % (n_out, n_src)); report['exit'] = EXIT['verify']
            return EXIT['verify']
        # 步骤 8：原子落盘（构建+页数通过后）
        shutil.move(out_tmp, args.out)
        step('publish')
    # 步骤 9：门禁（竖向 verify_vert / 横排 verify_geom）
    if args.pipeline_resolved == 'geom':
        vm = run_verify_geom(args.out, coords, lines, src_pdf=args.input)
        report['gate'] = dict(horizontal=True, tool='verify_geom',
                              pitch_floor=vm.get('floor'), pass_=vm.get('pass_'),
                              exit=vm.get('exit'), pages=vm.get('pages'),
                              pages_src=vm.get('pages_src'),
                              pitch_ok_pct=vm.get('pitch_ok_pct'),
                              height_ok_pct=vm.get('height_ok_pct'),
                              blank_pages=vm.get('blank_pages'),
                              overflow_pages=vm.get('overflow_pages'),
                              stdout_tail=vm.get('stdout_tail'))
        v_ok = bool(vm.get('pass_'))
        report['gate']['verdict'] = 'PASS' if v_ok else 'REJECT'
        ve, vnote = effective_verdict(report['gate']['verdict'], bt['multi_format'])
        report['gate']['verdict_effective'] = ve
        report['review_required'] = bool(bt['multi_format'])
        report['auto_pass_forbidden'] = bool(bt['multi_format'])
        report['multi_format'] = multi_format_clause(report['gate']['verdict'], ve,
                                                     bt['multi_format'], bt.get('sizes'))
        if bt['multi_format']:
            report['multi_format_note'] = ((vnote + '；') if vnote else '') + \
                (report['multi_format'] or {}).get('note', '')
        if not v_ok:
            code = EXIT['verify']
        elif ve == 'MANUAL_ONLY':
            code = EXIT['manual']
        else:
            code = EXIT['ok']
        report['gate']['exit'] = code
        report['verdict_effective'] = ve
        report['exit'] = code
        step('gate', verdict=ve, exit=code)
        # 横排 gate JSON/markdown（与竖排 quality_gate 输出对齐：reasons/tool/pitch/pages/overflow）
        pages_n = vm.get('pages') or 0; pages_src = vm.get('pages_src') or 0
        reasons = []
        if not v_ok:
            reasons.append('verify_geom_fail')
            if vm.get('pitch_ok_pct') is not None and vm.get('floor') is not None:
                if float(vm['pitch_ok_pct']) < float(vm['floor']):
                    reasons.append('pitch_below_floor')
            for line in (vm.get('stdout_tail') or '').splitlines():
                if 'FAIL' in line:
                    reasons.append(line.strip()[:160])
        gm = dict(book=args.book, mode='geom', tool='verify_geom',
                  pitch_floor=vm.get('floor'), pitch_ok_pct=vm.get('pitch_ok_pct'),
                  pages=pages_n, pages_src=pages_src,
                  split=(0 if pages_n == pages_src else max(0, pages_n - pages_src)),
                  missing=0 if v_ok else None,
                  blank_pages=vm.get('blank_pages'), overflow_pages=vm.get('overflow_pages'),
                  exit=vm.get('exit'), stdout_tail=vm.get('stdout_tail'))
        calib = None
        _cpath = args.out + '.calib.json'
        if os.path.exists(_cpath):
            try:
                calib = json.load(open(_cpath, encoding='utf-8'))
            except Exception as e:
                calib = {'error': str(e)}
        report['calib'] = calib
        _cw = ([w.get('code') for w in (calib or {}).get('warnings', [])]
               if isinstance(calib, dict) and not calib.get('error') else [])
        _cf = ([w.get('code') for w in (calib or {}).get('warnings', [])
                if w.get('severity') == 'fail']
               if isinstance(calib, dict) and not calib.get('error') else [])
        report['gate']['calib_warnings'] = _cw
        report['gate']['calib_fail'] = _cf
        if _cw:
            reasons = reasons + ['calib_warn:%s' % c for c in _cw]
        if _cf:
            reasons = reasons + ['calib_fail:%s' % c for c in _cf]
            # F1（t184）：FAIL 项不静默——不阻断构建，但 gate 不自动 PASS（MANUAL_ONLY 复核）
            if v_ok:
                ve = 'MANUAL_ONLY'
                code = EXIT['manual']
                report['gate']['verdict_effective'] = ve
                report['gate']['exit'] = code
                report['verdict_effective'] = ve
                report['exit'] = code
                report['review_required'] = True
        # F1/F2：render 由产物 PDF 回填；pitch_error_pct 由 verify_geom 回填
        if isinstance(calib, dict) and not calib.get('error'):
            try:
                from utils.geometry import update_calib_render
                _pe = (100.0 - float(vm['pitch_ok_pct'])) if vm.get('pitch_ok_pct') is not None else None
                _doc = update_calib_render(_cpath, args.out, pass_=v_ok, pitch_error_pct=_pe)
                if _doc:
                    calib = _doc; report['calib'] = calib
            except Exception as _ce:
                log('calib render 回填失败（不阻断）: %s' % _ce)
        _csum = None
        if isinstance(calib, dict) and not calib.get('error'):
            _csum = {k: calib.get(k) for k in ('schema_version', 'dpi', 'page_size',
                                               'font', 'baseline', 'coverage',
                                               'source_of_page_size', 'selfcheck',
                                               'warnings')}
            _csum['warnings_codes'] = _cw
        gate_doc = dict(version='quality-gate-v1', book=args.book, mode='geom',
                        tool='verify_geom', verdict=report['gate']['verdict'],
                        calib=_csum,
                        verdict_effective=ve,
                        review_required=bool(bt['multi_format']) or bool(_cf),
                        auto_pass_forbidden=bool(bt['multi_format']),
                        calib_warnings=_cw, calib_fail=_cf,
                        multi_format=report.get('multi_format'),
                        multi_format_note=report.get('multi_format_note'),
                        reasons=reasons, metrics=gm, gate=dict(**gm, reasons=reasons,
                                                             verdict_effective=ve,
                                                             review_required=bool(bt['multi_format']) or bool(_cf)),
                        note='横排门禁：verify_geom（必须带 --src-pdf 自适应 DPI）；核心字段与竖排对齐（非全 schema）')
        gp = args.out + '.gate.json'
        json.dump(gate_doc, open(gp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        md = ['# 横排质量门禁 · %s' % args.book, '',
              '- 结论：**%s**（effective=%s，review_required=%s）' % (
                  report['gate']['verdict'], ve, bool(bt['multi_format'])),
              '- tool：verify_geom（--src-pdf 自适应 DPI，pitch floor=%s）' % vm.get('floor'),
              '- pitch：%s%% / pages：%s=%s / split：%s / overflow：%s' % (
                  vm.get('pitch_ok_pct'), pages_n, pages_src, gate_doc['metrics']['split'],
                  vm.get('overflow_pages')),
              '- reasons：%s' % (', '.join(reasons) if reasons else '（无）'),
              '- multi_format：%s' % (report.get('multi_format_note') or '无（单纸型）'),
              '- calib：%s' % (
                  ('verdict=%s warnings=%s fail=%s' % ((calib or {}).get('selfcheck', {}).get('verdict'),
                                                       ','.join(_cw) if _cw else '无',
                                                       ','.join(_cf) if _cf else '无'))
                  if isinstance(calib, dict) and not calib.get('error') else '缺失')]
        open(os.path.splitext(gp)[0] + '.md', 'w', encoding='utf-8').write('\n'.join(md) + '\n')
        report['gate']['json'] = gp
        report['gate']['reasons'] = reasons
        rp = args.report or (args.out + '.report.json')
        attach_typography(report, args, lines)
        json.dump(report, open(rp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('[scan2pdf] %s: pipeline=geom gate=%s exit=%d report=%s' %
              (args.book, report['gate']['verdict'], code, rp))
        return code
    gate_out = args.out + '.gate.json'
    rc, verdict, tail = call_gate(args, args.out, coords, lines, src_for_verify, gate_out)
    report['gate'] = dict(json=gate_out, md=os.path.splitext(gate_out)[0] + '.md',
                          verdict=verdict, returncode=rc, tail=tail)
    step('gate', verdict=verdict, returncode=rc)
    # 步骤 10：结论（退出码 = 设计 §2.2）
    ve, vnote = effective_verdict(verdict, bt['multi_format'])
    comp = report.get('gate') or {}
    reasons = set(comp.get('reasons') or [])
    unscored = ('UNSCORED' in str(comp.get('punct_verdict')) or
                'UNSCORED' in str(comp.get('content_verdict')) or
                'no_content_metrics' in reasons)
    if 'verify_fail' in reasons:
        code = EXIT['verify']
    elif verdict == 'REJECT':
        code = EXIT['reject']
    elif unscored:
        code = EXIT['manual']
    elif ve in ('AUTO_PASS', 'MANUAL_ONLY') and not bt['multi_format']:
        code = EXIT['ok']
    else:
        code = EXIT['manual']
    report['gate']['verdict_effective'] = ve
    report['gate']['exit'] = code
    report['multi_format'] = multi_format_clause(verdict, ve, bt['multi_format'], bt.get('sizes'))
    report['review_required'] = bool(bt['multi_format'])
    if bt['multi_format']:
        mf = report['multi_format']
        report['multi_format_note'] = ((vnote + '；') if vnote else '') + mf['note']
        report['multi_format_note'] += '；verdict_effective=%s、review_required=true 三者并存：门禁有真问题 + 多纸型需人工' % ve
    report['exit'] = code
    if report.get('resume'):
        report['resume_note'] = ('复用键匹配（book+input_sha+fix_sha+coords_sha+lines_sha+mode+pipeline+pages）：'
                                 '默认不覆盖、复用已有 out 并重跑门禁；--force 才重建')
    rp = args.report or (args.out + '.report.json')
    json.dump(report, open(rp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('[scan2pdf] %s: book_type=%s gate=%s exit=%d report=%s' %
          (args.book, bt['axis'], verdict, code, rp))
    return code


if __name__ == '__main__':
    sys.exit(main())
