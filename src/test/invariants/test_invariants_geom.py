#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_geom（现代书籍管线）特征不变量测试。

不变量锁的是行为性质：不论输入哪段正文 spotting（格式合法），这些关系都成立。
断言用范围/关系，不绑具体页数/字号/pitch 值。
输入：wz1 源页 [40,70) 截取（含脚注①页 41/48/49/50），单趟 POSITIONAL=1。
"""
import sys
import os
import statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import line_features, N
import fitz


def _rows(pdf):
    rows, npages = line_features(pdf)
    return rows, npages


def test_small_font_below_body(geom_pdf):
    """不变量1：小字（脚注/页眉 FONT_SM=FONT×0.78）字号 < 正文中位字号 × 0.85。

    依据：build_geom L55 FONT_SM=round(FONT*0.78)，脚注/页眉用小字，
    正文用 FONT，二者字号比 ≈0.78 < 0.85。
    """
    rows, _ = _rows(geom_pdf)
    sizes = [r['size'] for r in rows]
    assert min(sizes) < statistics.median(sizes) * 0.85


def test_heading_above_body(geom_pdf):
    """不变量2：标题最大字号 ≥ 正文中位字号 × 1.2。

    依据：build_geom L499 _big = h > H_BODY*1.8，标题字号 tier_size 按行高
    推导（L501），明显大于正文。
    """
    rows, _ = _rows(geom_pdf)
    sizes = [r['size'] for r in rows]
    assert max(sizes) >= statistics.median(sizes) * 1.2


def test_paragraph_indent_exists(geom_pdf):
    """不变量3：段首缩进存在--正文行 x0 上四分位 > 下四分位且差距足够。

    依据：build_geom L1013 段首 \\hspace*{2em}，续行顶格；段首 x0 > 续行 x0，
    差距 ≈2em（~正文2字宽）。
    """
    rows, _ = _rows(geom_pdf)
    x0s = [r['x0'] for r in rows if r['text'].strip()]
    assert len(x0s) > 10
    med = statistics.median(x0s)
    # 段首缩进 2em -> x0 明显大于顶格中位；段首行占少数（每段1行）但应存在一定比例
    indented = sum(1 for x in x0s if x > med + 3)
    assert indented > len(x0s) * 0.05    # 至少 5% 行是段首缩进


def test_page_count_lower_bound(geom_pdf):
    """不变量4：输出页数 ≥ 源页数 × 0.8（内容不丢失）。

    依据：行距按源 BASELINE 推导，不应大量压缩成更少页；少量溢出可接受，
    但不应丢页。锁当前范围 [源×0.8, 源×1.5]。
    """
    rows, npages = _rows(geom_pdf)
    assert npages >= N * 0.8
    assert npages <= N * 1.5


def test_no_replacement_char(geom_pdf):
    """不变量5：全书无乱码 U+FFFD（�）。

    依据：_esc_chars 不引入 U+FFFD；OCR 的 � 在 is_garbage_page 整页贴图，
    不进正文流。输出文本不应含 U+FFFD。
    """
    rows, _ = _rows(geom_pdf)
    bad = [r for r in rows if '�' in r['text']]
    assert len(bad) == 0


def test_no_line_overflow(geom_pdf):
    """不变量6：正文行不溢出版心--行尾 x1 中位 < 页宽 × 0.98。

    依据：build_geom makebox[\\textwidth][s] 收缩齐右，满行不超版心；
    段末短行 makebox[l] 也不超。整页贴图页 x1≈页宽但属图页，median 排除。
    """
    rows, npages = _rows(geom_pdf)
    doc = fitz.open(geom_pdf)
    pw = doc[0].rect.width
    doc.close()
    x1_med = statistics.median(r['x1'] for r in rows)
    assert x1_med < pw * 0.98
