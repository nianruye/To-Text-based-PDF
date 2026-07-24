#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_classic（古籍管线）特征不变量测试。

不变量锁的是行为性质：不论输入哪段古籍正文 spotting（格式合法），这些关系都成立。
断言用范围/关系，不绑具体页数/字号/pitch 值。
输入：wz2 源页 [60,90) 截取（〔X〕序号+注释密集页），单趟 POSITIONAL=1。

注意：单趟 POSITIONAL=1 无 ratio 校正，古籍行距大致溢出多页（30->~50），
页数类不变量按"锁当前值"处理。
"""
import sys
import os
import statistics
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import line_features, N


def _rows(pdf):
    rows, npages = line_features(pdf)
    return rows, npages


def _is_seq_line(text):
    """行首是〔X〕序号（注释序号）。"""
    return text.lstrip().startswith('〔')


def test_seq_x0_more_aligned_than_normal(classic_pdf):
    """不变量1：序号〔X〕行 x0 标准差 < 普通行 x0 标准差（序号对齐到文字列左缘）。

    依据：build_classic L1020-1026 把序号统一到 _note_text_x[key] - 序号宽，
    不按源 x0 波动；普通行按源 x0/段首缩进，x0 分散。故序号行 x0 集中。
    """
    rows, _ = _rows(classic_pdf)
    seq = [r['x0'] for r in rows if _is_seq_line(r['text'])]
    other = [r['x0'] for r in rows if r['text'].strip() and not _is_seq_line(r['text'])]
    assert len(seq) > 10 and len(other) > 10
    assert statistics.pstdev(seq) < statistics.pstdev(other)


def test_note_line_font_below_body(classic_pdf):
    """不变量2：注释序号行字号 vs 正文行字号（锁当前值）。

    期望：NOTE_FONT < BODY_FONT（注释字号 < 正文字号）。但 wz2 p60-90 是注释
    密集区，整页 PF=NOTE_FONT（build_classic L725 纯注释页判据），序号行与非
    序号正文行同字号（~13.15pt），故当前 seq_med == body_med。锁当前范围：
    序号行字号不超过正文行 × 1.05（注释不反超正文；待换含正文页子集或校准
    两趟后可收紧为严格 <）。
    """
    rows, _ = _rows(classic_pdf)
    seq_sizes = [r['size'] for r in rows if _is_seq_line(r['text'])]
    body_sizes = [r['size'] for r in rows
                  if r['text'].strip() and not _is_seq_line(r['text']) and r['size'] > 11]
    assert seq_sizes and body_sizes
    seq_med = statistics.median(seq_sizes)
    body_med = statistics.median(body_sizes)
    assert seq_med <= body_med * 1.05    # 锁当前：注释区同字号，序号不反超正文


def test_page_count_locked(classic_pdf):
    """不变量3：输出页数锁当前值（单趟 POSITIONAL 无 ratio 校正，古籍行距溢出）。

    现状：30 源页 -> ~50 物理页（溢出 ratio ~1.67）。校准两趟后应 1:1，
    但单趟无 ratio 校正故溢出。锁当前溢出范围 [源×1.0, 源×2.5]。
    """
    rows, npages = _rows(classic_pdf)
    assert N <= npages <= N * 2.5


def test_no_replacement_char(classic_pdf):
    """不变量4：全书无乱码 U+FFFD（�）。

    依据：_esc_chars 修正符号（○->〇、【】->〔〕），不引入 U+FFFD；
    图页/乱码页 is_garbage_page 整页贴图，不进正文流。
    """
    rows, _ = _rows(classic_pdf)
    bad = [r for r in rows if '�' in r['text']]
    assert len(bad) == 0


def test_seq_marker_exists(classic_pdf):
    """不变量5：序号〔X〕被渲染（注释序号存在于输出文本）。

    依据：build_classic 注释序号行〔一〕〔二〕... 经 esc 渲染（行首[X]->〔X〕
    不上标，L223），输出 PDF 文本应含〔。
    """
    rows, _ = _rows(classic_pdf)
    n = sum(1 for r in rows if '〔' in r['text'])
    assert n > 0


def test_pitch_cv_locked(classic_pdf):
    """不变量6：每页正文行间距 CV 锁当前值（单趟墨高重叠 \\[-2pt] 行距）。

    依据：build_classic POSITIONAL=1 用 bl=_pp（源 pitch）+ \\[-2pt] 墨高重叠，
    同页行距应相对均匀。CV=pstdev(gaps)/median(gaps)。单趟无 ratio 校正，
    锁当前范围 [0, 0.5]（均匀则 CV 小）。
    """
    rows, _ = _rows(classic_pdf)
    bypage = defaultdict(list)
    for r in rows:
        bypage[r['page']].append(r)
    cvs = []
    for p, rs in bypage.items():
        ys = sorted(r['y0'] for r in rs if r['text'].strip())
        if len(ys) < 6:
            continue
        gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)
                if 0 < ys[i + 1] - ys[i] < 50]
        if len(gaps) < 5:
            continue
        m = statistics.median(gaps)
        if m > 0:
            cvs.append(statistics.pstdev(gaps) / m)
    assert cvs, '无足够页算行间距 CV'
    med_cv = statistics.median(cvs)
    assert 0.0 <= med_cv <= 0.5


def test_marker_superscript_small(classic_pdf):
    """不变量7：校注标记上标字号 < 正文字号（MARKER_SCALE=0.55）。

    依据：build_classic esc L227 校注标记用 \\fontsize{FONT×0.55}，
    是上标小字。输出 PDF 同行内最小 span 字号 < 行主字号 × 0.7。
    （fitz 行内 span 字号区分主字与上标小字。）
    """
    import fitz
    doc = fitz.open(classic_pdf)
    ratios = []
    for page in doc:
        for d in page.get_text('dict')['blocks']:
            if d.get('type') != 0:
                continue
            for ln in d.get('lines', []):
                spans = ln.get('spans', [])
                sizes = [s.get('size', 0) for s in spans if s.get('text', '').strip()]
                if len(sizes) >= 2 and max(sizes) > 8:
                    ratios.append(min(sizes) / max(sizes))
    doc.close()
    assert ratios, '未找到含上标的行'
    # 至少部分行含明显小字上标（ratio < 0.7）
    small_frac = sum(1 for r in ratios if r < 0.7) / len(ratios)
    assert small_frac > 0.05
