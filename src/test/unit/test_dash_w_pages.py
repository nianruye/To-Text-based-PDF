#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dash 线宽按页启用（VERT_DASH_RULE_W_PAGES）纯函数测试（t67/battle13b）。

从 build_vert.py 抽取 `_parse_page_csv` / `_dash_w_src_for` 两个纯函数（不执行整模块），覆盖：
- 默认空页集 = 旧行为（src 时全页生效）；
- 列出 57 = 仅 p57 用 src，其余页默认；
- 多页解析（'57,1683'、中文逗号/空白/非法项容忍）。
运行：/usr/bin/python3 -m pytest src/test/unit/test_dash_w_pages.py -v
"""
import ast, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
BUILD = os.path.join(ROOT, 'src/pipelines/build_vert.py')


def _load_funcs():
    src = open(BUILD, encoding='utf-8').read()
    tree = ast.parse(src)
    nodes = [n for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name in ('_parse_page_csv', '_dash_w_src_for')]
    ns = {'DASH_RULE_W_PAGES': set()}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), BUILD, 'exec'), ns)
    return ns


def test_parse_csv():
    ns = _load_funcs()
    parse = ns['_parse_page_csv']
    assert parse('') == set()
    assert parse(None) == set()
    assert parse('57') == {57}
    assert parse('57,1683') == {57, 1683}
    assert parse(' 57 ， 1683 ,x') == {57, 1683}   # 中文逗号/空白/非法项
    assert parse('57,,57') == {57}


def test_default_empty_is_global_behavior():
    ns = _load_funcs()
    ns['DASH_RULE_W_PAGES'] = set()
    for pg in (31, 57, 1742):
        assert ns['_dash_w_src_for'](pg) is True     # 空 = 旧行为（全页 src）


def test_listed_page_only():
    ns = _load_funcs()
    ns['DASH_RULE_W_PAGES'] = {57}
    assert ns['_dash_w_src_for'](57) is True
    assert ns['_dash_w_src_for'](31) is False
    assert ns['_dash_w_src_for'](1742) is False


def test_multi_pages():
    ns = _load_funcs()
    ns['DASH_RULE_W_PAGES'] = {57, 1683}
    assert ns['_dash_w_src_for'](57) and ns['_dash_w_src_for'](1683)
    assert not ns['_dash_w_src_for'](1742)
