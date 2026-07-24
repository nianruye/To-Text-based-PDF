#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_geom 页眉识别 + 页码 pn_ocr 单调性测试。

约束：
- 纯 Python，不 import fitz/opencc，不调用 xelatex，不读文件系统。
- 通过 _loader.py 用 ast 提取目标函数到隔离 namespace。

核心测试点（spec: spec/modern/wz3_header_pagenum.md）：
- page_header_raw 应捕获 y0 在 5-6% 的页眉（wz3 页眉在 5.6%，原 0.05 阈值漏）。
- _filter_pn_ocr 应弃用突变页码（目录页 p11=29 误识），采用连续页码。

运行：
    /usr/bin/python3 -m pytest src/test/unit/test_header_pagenum.py -v
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from _loader import load

import pytest

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _poly(y0, h=30, x0=400, x1=900):
    """4 点 poly（y0=顶 y, h=行高）。page_header_raw 用 min(y) 判定, y0 即 min_y。"""
    return [[x0, y0], [x1, y0], [x1, y0 + h], [x0, y0 + h]]


@pytest.fixture(scope="module")
def geom_ns():
    """提取 page_header_raw + _filter_pn_ocr，注入 co/sl/page_px_h。"""
    return load('build_geom.py',
                func_names={'page_header_raw', '_filter_pn_ocr'},
                mocks={'co': {}, 'sl': {}, 'page_px_h': 2438.0, 'DPI': 200})


def test_page_header_raw_captures_6pct_header(geom_ns):
    """页眉 y0=5.6%(136px/2438) 应被 page_header_raw 捕获。

    wz3 页眉在 5-6%，原阈值 0.05(121.9px) 漏掉 6% 的页眉。
    改动1(0.05->0.06, 阈值 146.3px)后捕获。此用例改动前 FAIL。"""
    phr = geom_ns['page_header_raw']
    geom_ns['page_px_h'] = 2438.0
    # 页眉 y0=136(5.6%), 正文 y0=317(13%)
    geom_ns['co'] = {'1': [_poly(136, h=61), _poly(317, h=71)]}
    geom_ns['sl'] = {'1': ['第二章周民族之来源及其初期生活情态', '思辑用光，弓矢斯张']}
    v = phr('1')
    assert v == '第二章周民族之来源及其初期生活情态', f"5.6% 页眉应被捕获, 实得 {v!r}"


def test_page_header_raw_ignores_body_line(geom_ns):
    """正文行 y0=13%(317px) 不被当页眉。"""
    phr = geom_ns['page_header_raw']
    geom_ns['page_px_h'] = 2438.0
    geom_ns['co'] = {'1': [_poly(317, h=71)]}   # 只正文, 无页眉
    geom_ns['sl'] = {'1': ['思辑用光，弓矢斯张']}
    assert phr('1') == ''


def test_page_header_raw_merges_fragments_by_x(geom_ns):
    """多片段页眉('第一部分'+'历史考证')按 x 合并(共识校正前提)。"""
    phr = geom_ns['page_header_raw']
    geom_ns['page_px_h'] = 2438.0
    # 两片段同 y0=120(4.9%), 不同 x
    geom_ns['co'] = {'1': [_poly(120, h=40, x0=400, x1=600), _poly(120, h=40, x0=650, x1=900)]}
    geom_ns['sl'] = {'1': ['第一部分', '历史考证']}
    assert phr('1') == '第一部分历史考证'


def test_filter_pn_ocr_consecutive_adopted(geom_ns):
    """连续页码(1,2,3)被采用。"""
    fp = geom_ns['_filter_pn_ocr']
    assert fp('1', None) == '1'   # 首页(prev=None)采用
    assert fp('2', 1) == '2'      # 连续
    assert fp('3', 2) == '3'


def test_filter_pn_ocr_jump_discarded(geom_ns):
    """突变页码(4->29)被弃用(目录页 p11=29 误识)。"""
    fp = geom_ns['_filter_pn_ocr']
    assert fp('29', 4) == ''      # 4->29 突变, 弃用
    assert fp('158', 7) == ''     # 目录页码误识, 弃用


def test_filter_pn_ocr_empty(geom_ns):
    """空 pn_ocr 返回空。"""
    fp = geom_ns['_filter_pn_ocr']
    assert fp('', None) == ''
    assert fp('', 5) == ''
