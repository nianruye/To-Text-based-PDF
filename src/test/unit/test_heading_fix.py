#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_geom 页眉共识兜底 _match_canon_hdr 测试。

约束：
- 纯 Python，不 import fitz/opencc，不调用 xelatex。
- 通过 _loader.py 用 ast 提取 _match_canon_hdr 到隔离 namespace。

核心测试点（spec: spec/modern/wz3_heading_fix.md）：
- _match_canon_hdr 应识别匹配共识页眉的顶部行(如 '第四章...'),排除非共识(如扉页 '中央编译局文库')。
- 解决 p54 L0 页眉(6%边缘,匹配共识)被当标题的问题。

运行：
    /usr/bin/python3 -m pytest src/test/unit/test_heading_fix.py -v
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from _loader import load

import pytest

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture(scope="module")
def geom_ns():
    """提取 _match_canon_hdr,注入 CANON_HDRS(模拟 wz3 共识页眉)。"""
    return load('build_geom.py',
                func_names={'_match_canon_hdr'},
                mocks={'CANON_HDRS': [
                    '第四章宗周时期"封建"制度之进展',
                    '中国古代经济史稿',
                    '第二十四章魏晋及南朝赋役制度',
                ]})


def test_match_exact(geom_ns):
    """精确匹配共识页眉 -> True。"""
    assert geom_ns['_match_canon_hdr']('第四章宗周时期"封建"制度之进展') is True


def test_match_fuzzy(geom_ns):
    """近似匹配(OCR 引号/标点差异) ratio>0.8 -> True。"""
    # 去掉引号仍高度相似
    assert geom_ns['_match_canon_hdr']('第四章宗周时期封建制度之进展') is True


def test_no_match_non_canon(geom_ns):
    """非共识文本(扉页/正文) -> False。p54 误判 vs wz1 p2 不误判的关键。"""
    assert geom_ns['_match_canon_hdr']('中央编译局文库') is False
    assert geom_ns['_match_canon_hdr']('语可知)，其第二章云') is False


def test_empty_canon(geom_ns):
    """CANON_HDRS 空 -> False(无共识可匹配,如短章书)。"""
    geom_ns['CANON_HDRS'] = []
    assert geom_ns['_match_canon_hdr']('第四章宗周时期"封建"制度之进展') is False


def test_short_text(geom_ns):
    """短文本(如 '序言')不匹配长共识页眉 -> False(短文本靠居中标题判定,不靠共识)。"""
    geom_ns['CANON_HDRS'] = ['第四章宗周时期"封建"制度之进展', '中国古代经济史稿']
    assert geom_ns['_match_canon_hdr']('序言') is False
