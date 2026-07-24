#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""纯函数测试加载器。

背景：build_pdf_v13.py / build_geom.py / build_classic.py 都是脚本式顶层执行
(import 即触发 fitz.open / json.load / xelatex，且顶层 import fitz / opencc)，
无法用 ``import`` 方式加载其中的纯函数来测试。

本模块用 ``ast`` 从源文件**只提取目标函数 + 它们依赖的纯常量**，编译到隔离
namespace，不执行模块顶层副作用，从而在不 import fitz / opencc、不调用 xelatex、
不读 JSON 的前提下测试纯函数。不修改任何业务代码。

提取的常量必须是纯的（re.compile / dict / set / str.maketrans 等）；非纯全局
(如 FONT 依赖数据加载、_t2s 依赖 opencc) 由调用方通过 mocks 注入。
"""
import ast
import re
import os
import statistics
import warnings
from pathlib import Path

# src/test/unit/_loader.py -> parents[2] = src/
_SRC = Path(__file__).resolve().parents[2]
_PIPES = _SRC / 'pipelines'


class MockT2S:
    """opencc.OpenCC('t2s') 的最小 mock。

    opencc 未安装，``_has_trad`` 依赖的 ``_t2s`` 用此 mock 注入。内置繁->简
    字典覆盖测试用例字符；``convert`` 返回简体串，``_has_trad`` 据此判断
    ``convert(t) != t``（含繁体则 True）。仅用于验证 _has_trad 的逻辑契约，
    不保证与真实 opencc 字典完全一致。
    """
    _D = str.maketrans({
        '書': '书', '論': '论', '學': '学', '價': '价', '勞': '劳',
        '業': '业', '龍': '龙', '產': '产', '島': '岛', '條': '条',
        '發': '发', '為': '为', '圖': '图', '國': '国', '會': '会',
        '來': '来', '節': '节', '過': '过', '還': '还', '開': '开',
        '關': '关', '見': '见', '說': '说', '話': '话', '語': '语',
        '詞': '词', '買': '买', '賣': '卖', '費': '费', '資': '资',
        '潤': '润', '馬': '马',
    })

    def convert(self, t):
        return t.translate(self._D)


# 注入到提取 namespace 的安全模块（业务函数引用 re / os / statistics）
_BASE_NS = {'re': re, 'os': os, 'statistics': statistics}


def _assign_names(node):
    """Assign 节点的目标名列表（只取简单 Name 赋值）。"""
    return [t.id for t in node.targets if isinstance(t, ast.Name)]


def _exec_node(node, src_path, ns):
    """把单个顶层节点包装成 Module 编译并 exec 到 ns。"""
    mod = ast.Module([node], type_ignores=[])
    ast.fix_missing_locations(mod)
    # 提取的函数 docstring 可能含无效转义序列（如 \s），编译时触发
    # DeprecationWarning，与测试无关，静默之。
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', DeprecationWarning)
        exec(compile(mod, str(src_path), 'exec'), ns)


def load(filename, func_names, const_names=(), mocks=None):
    """从 ``pipelines/<filename>`` 提取指定函数+常量到隔离 namespace。

    参数:
        filename: pipelines/ 下的文件名（如 'build_geom.py'）。
        func_names: 要提取的函数名集合/列表。
        const_names: 要提取的模块级常量名（必须是纯常量）。
        mocks: 额外注入 namespace 的 {名: 值}（如 {'FONT': 10.0, '_t2s': MockT2S()}）。

    返回:
        namespace dict，含所提取的函数与常量，可直接 ``ns['func_name']`` 取用。

    注意:
        先 exec 常量再 exec 函数（函数默认参数可能引用常量，如
        ``_eff_chars(t, pw=PUNCT_WEIGHT)``）。exec 会自动注入 __builtins__，
        故 float / int / str / len / ord 等内置可用。
    """
    p = _PIPES / filename
    tree = ast.parse(p.read_text(encoding='utf-8'))
    ns = dict(_BASE_NS)
    if mocks:
        ns.update(mocks)

    funcs = set(func_names)
    consts = set(const_names)

    # 先常量：函数默认参数求值依赖常量已就位
    for node in tree.body:
        if isinstance(node, ast.Assign) and (set(_assign_names(node)) & consts):
            _exec_node(node, p, ns)

    # 再函数
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in funcs:
            _exec_node(node, p, ns)

    return ns
