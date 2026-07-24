#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""missing_chars 缺字检测测试。

核心测试点（spec: spec/modern/wz3_subhead_missingchar.md）：
- detect_missing 检测空引号""(引文内字缺,OCR 识为空),排除相邻引用("A""B")。

运行：
    /usr/bin/python3 -m pytest src/test/unit/test_missing_chars.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from utils.missing_chars import detect_missing

import pytest


def test_detect_zuokong():
    """'作""'(引文内空)检测缺字,偏移=空引号起始。"""
    # 作=0, "=1, "=2 -> 空引号 idx=1, prev='作'(非引号)=缺字
    assert detect_missing('作""') == [1]


def test_detect_no_adjacent_quotes():
    """'X"古"或"丄"Y' 相邻引用不检测(中间有字,无相邻"")。"""
    assert detect_missing('即为农器之"耒"') == []
    assert detect_missing('"古"或"丄"') == []


def test_detect_none():
    """无缺字文本返回空。"""
    assert detect_missing('无缺字的普通正文') == []
    assert detect_missing('') == []


def test_detect_multiple():
    """多个缺字都检测。'作""，曰""' -> [1, 5]。"""
    # 作=0,"=1,"=2,，=3,曰=4,"=5,"=6
    assert detect_missing('作""，曰""') == [1, 5]


def test_detect_sentence_boundary():
    """句号后的"" 前字符是句号(非引号)=缺字(罗振玉...作""模式)。"""
    # p68 L32: '...作""，罗氏释之曰：'
    t = '而知也。罗振玉于甲骨文中得一"爰"字，作""，罗氏释之曰：'
    m = detect_missing(t)
    assert len(m) == 1  # 作"" 一处缺字
    assert t[m[0]:m[0]+2] == '""'  # 偏移指向空引号


def test_detect_adjacent_quote_not_missing():
    """'。""跖" 句号+引号+引号+字:前字符是句号(非引号)=缺字? 不,这是相邻引用边界。
    实际 p25 '功。""跖"、"蹊" 的 "" 是上引收尾+下引开头=相邻,但前字符是句号。
    此情况按"前字符非引号"判为缺字(保守,宁可贴图也不丢字)。"""
    # 这种边界情况: ""  前是句号,判缺字(可能误判,但保守)
    t = '劳罢而寡功。""跖"'
    m = detect_missing(t)
    # "" 前是句号(非引号) -> 判缺字(保守策略)
    assert len(m) >= 1
