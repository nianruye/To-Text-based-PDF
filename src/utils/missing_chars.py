#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""缺字检测 + 源 PDF 剪字图模块。

OCR 识不出的甲骨文/金文字,行文本里是空引号""(如 p68 '作""'),
渲染会丢字。本模块检测空引号位置,从源 PDF 剪对应字图,供 build_geom 贴回。

行级 OCR 无单字 poly,按字符偏移估算 x(粗略,CJK 字宽不均,可能偏 1-2 字)。
"""
import os

# 全角引号(双 U+201C/D + 单 U+2018/9)+ 半角双,用于检测空引号
QUOTES = '"“”‘’'


def detect_missing(t):
    """检测空引号缺字(引文内字缺,OCR 识为空"")。

    返回缺字的字符偏移列表(空引号起始 idx)。
    判定: 相邻两个引号(中间无字) + 前字符非引号 = 缺字。
    排除相邻引用("A""B" 的 "" 前字符是引号=相邻引用,非缺字)。
    边界(。""跖" 前是句号)保守判为缺字(宁可贴图也不丢字)。

    Args:
        t: 行文本(已转义或未转义均可,引号不被 LaTeX 转义)
    Returns:
        list of int, 空引号起始偏移
    """
    missing = []
    for i in range(len(t) - 1):
        if t[i] in QUOTES and t[i + 1] in QUOTES:
            prev = t[i - 1] if i > 0 else ''
            if prev not in QUOTES:   # 前字符非引号=缺字(非相邻引用)
                missing.append(i)
    return missing


def crop_char(src_pdf, page_idx, poly, char_idx, t, out_dir, dpi=200):
    """从源 PDF 剪缺字 bbox 的 PNG。

    行内定位: x = poly_x0 + char_idx * 字宽(字宽=poly_w/len(t))。
    poly 是 OCR 200dpi px 坐标,转 pt(×72/200)后作 fitz clip。

    Args:
        src_pdf: 源 PDF 路径
        page_idx: 页号(0-indexed)
        poly: 行 poly [[x0,y0],[x1,y0],[x1,y1],[x0,y1]] (200dpi px)
        char_idx: 缺字(空引号)在 t 中的字符偏移
        t: 行文本
        out_dir: PNG 输出目录
        dpi: 源 PDF 渲染 dpi(默认 200,与 OCR 一致)
    Returns:
        PNG 路径
    """
    import fitz   # 延迟 import,detect_missing 测试不需 fitz
    x0, y0 = poly[0][0], poly[0][1]
    x1, y1 = poly[2][0], poly[2][1]   # poly[2]=右下
    poly_w = x1 - x0
    char_w = poly_w / max(len(t), 1)   # CJK 字宽估算(粗略)
    cx = x0 + char_idx * char_w
    k = 72.0 / dpi   # px -> pt
    bbox = fitz.Rect(cx * k, y0 * k, (cx + char_w) * k, y1 * k)
    doc = fitz.open(src_pdf)
    pix = doc[page_idx].get_pixmap(clip=bbox, dpi=dpi)
    out = os.path.join(out_dir, 'mc_%s_%s.png' % (page_idx, char_idx))
    pix.save(out)
    doc.close()
    return out


def crop_row(src_pdf, page_idx, poly, out_dir, dpi=200):
    """剪整行 poly 的 PNG(整行贴图用:低 score 行整行贴源图保留古字原貌)。

    poly 是 PP-OCRv6 行 poly(200dpi px),转 pt 后作 fitz clip 剪整行。
    """
    import fitz   # 延迟 import
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    k = 72.0 / dpi   # px -> pt
    bbox = fitz.Rect(x0 * k, y0 * k, x1 * k, y1 * k)
    doc = fitz.open(src_pdf)
    pix = doc[page_idx].get_pixmap(clip=bbox, dpi=dpi)
    out = os.path.join(out_dir, 'row_%s_%s.png' % (page_idx, int(y0)))
    pix.save(out)
    doc.close()
    return out
