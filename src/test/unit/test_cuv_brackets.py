#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""曲牌空括号对（t70/battle14）纯函数测试。

从 build_vert.py 抽取 `_is_cuv_name` / `_fix_cuv_brackets` 及常量，覆盖：
- 裸曲牌名识别（含页码「一四」排除、带标点/唱：排除）；
- 空括号对移到前一列曲牌名两侧（move）；
- 无相邻曲牌名 -> 删除（del）；
- 括号对不在列首（pos>2）即使前一行像名字也不移（防误移，p58 反例）。
运行：/usr/bin/python3 -m pytest src/test/unit/test_cuv_brackets.py -v
"""
import ast, os, re
import fitz
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
BUILD = os.path.join(ROOT, 'src/pipelines/build_vert.py')


def _load():
    src = open(BUILD, encoding='utf-8').read()
    tree = ast.parse(src)
    nodes = []
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name in ('_is_cuv_name', '_fix_cuv_brackets', '_fix_bare_cuv_names', '_fix_yi_after_name', '_yi_name_text_mode', '_yi_name_action', '_yi_cell_comps', '_collapse_quote_noise'):
            nodes.append(n)
        elif isinstance(n, ast.Assign):
            names = [t.id for t in n.targets if isinstance(t, ast.Name)]
            if any(x in ('_CUV_EMPTY_PAIRS', '_CUV_NAME_RE', '_CUV_PAGENUM', '_CUV_CHAPTER_RE', '_YI_LEGIT_WORDS') for x in names):
                nodes.append(n)
    ns = {'re': re, 'fitz': fitz, 'np': np}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), BUILD, 'exec'), ns)
    return ns


def test_name_filter():
    ns = _load()
    assert ns['_is_cuv_name']('桂枝香')
    assert ns['_is_cuv_name']('尾聲')
    assert not ns['_is_cuv_name']('一四')          # 页码行
    assert not ns['_is_cuv_name']('董嬌兒唱：')     # 带标点
    assert not ns['_is_cuv_name']('〔鎖南枝〕')     # 已带括号
    assert not ns['_is_cuv_name']('這是七個字的句子')


def test_move_brackets_to_prev_name():
    ns = _load()
    log = []
    rows, log = ns['_fix_cuv_brackets'](['桂枝香', '（）「楊花心性'], 704, log)
    assert rows[0] == '〔桂枝香〕'
    assert rows[1] == '「楊花心性'
    assert len(log) == 1 and log[0]['kind'] == 'move' and log[0]['pair'] == '（）'


def test_delete_without_name():
    ns = _load()
    log = []
    rows, log = ns['_fix_cuv_brackets'](['兒扯爺女扯娘', '一家兒。〔〕」'], 640, log)
    assert rows[1] == '一家兒。」'
    assert log and log[0]['kind'] == 'del'


def test_pos_gate_no_move_when_mid_column():
    ns = _load()
    log = []
    rows, log = ns['_fix_cuv_brackets'](['一四', '沈璟的「博笑記」（）更由於'], 58, log)
    assert rows[0] == '一四'                       # 页码行不被包
    assert '（）' not in rows[1] and log[0]['kind'] == 'del'


def test_bare_cuv_name_wrap_and_page_number_exclusion():
    ns = _load()
    if '_fix_bare_cuv_names' not in ns:
        import pytest; pytest.skip('function not extracted')
    rows, log = ns['_fix_bare_cuv_names'](['董嬌兒唱：', '紅綉鞋', '一個兒投東去'], 705, [])
    assert rows[1] == '〔紅綉鞋〕'
    assert log and log[0]['kind'] == 'barewrap'
    # 书眉「金瓶梅」+ 页码行「一四五」：不得包
    rows2, log2 = ns['_fix_bare_cuv_names'](['金瓶梅', '一四五'], 100, [])
    assert rows2[0] == '金瓶梅' and not log2
    # 章节标题不包
    rows3, log3 = ns['_fix_bare_cuv_names'](['第四十六回', '元夜遊行遇雪雨'], 727, [])
    assert rows3[0] == '第四十六回' and not log3


def test_name_yi_uses_ink_corner():
    ns = _load()
    if '_fix_yi_after_name' not in ns:
        import pytest; pytest.skip('function not extracted')
    co = [[[0, 0], [10, 0], [10, 100], [0, 100]]] * 2
    # 角形+合法词「一壁厢」 -> 插入 ﹁ 保留 一（p679 回归）
    ns['_yi_cell_comps'] = lambda *a, **k: [(20.0, 6.0)]
    out, log = ns['_fix_yi_after_name'](['紅綉鞋', '一壁厢舞着'], co, 679, object(), [])
    assert out[1].startswith('﹁一壁厢') and log and log[0]['kind'] == 'name_yi_ins'
    # 角形 + 非合法词 -> 1:1 替换
    out2, log2 = ns['_fix_yi_after_name'](['紅綉鞋', '一水面上鴛鴦'], co, 703, object(), [])
    assert out2[1].startswith('﹁水面上') and log2 and log2[0]['kind'] == 'name_yi'
    # 无角形墨 -> 不动
    ns['_yi_cell_comps'] = lambda *a, **k: []
    out3, log3 = ns['_fix_yi_after_name'](['紅綉鞋', '一壁厢舞着'], co, 679, object(), [])
    assert out3[1].startswith('一壁厢') and not log3


def test_yi_name_text_mode_keeps_legit_yi():
    ns = _load()
    if '_yi_name_text_mode' not in ns:
        ns['_yi_name_text_mode'] = None
    assert ns['_yi_name_text_mode']('一壁厢舞着唱着') == 'insert'   # p679 合法「一」
    assert ns['_yi_name_text_mode']('一個兒投東去') == 'insert'
    assert ns['_yi_name_text_mode']('一到如今瑤琴絃斷') == 'insert'
    assert ns['_yi_name_text_mode']('一水面上鴛鴦一對') == 'replace'  # 角形即 ﹁
    assert ns['_yi_name_text_mode']('呀！減盡了花容') == 'replace'


def test_collapse_quote_noise_positive_and_negative():
    ns = _load()
    f = ns['_collapse_quote_noise']
    # 正例：空对收敛（三种上下文）
    assert f('…花慵戴。﹁﹂﹁一') == '…花慵戴。」﹁一'      # 后接引号 -> 留闭号
    assert f('！﹁﹂那裡藏') == '！」「那裡藏'               # 句末+文字 -> 交换 」「
    assert f('。﹁﹂︹調笑令︺') == '。」︹調笑令︺'           # 名前后 -> 留闭号
    assert f('「」冷清清') == '「冷清清'
    assert f('﹂﹂') == '﹂'
    # 反例：合法配对 ﹂﹁（闭+开）不得删
    assert f('！」「那裡') == '！」「那裡'
    assert f('﹂﹁') == '﹂﹁'
    assert f('…﹂﹁感皇恩') == '…﹂﹁感皇恩'


def test_name_in_quotes_becomes_bracket():
    ns = _load()
    if '_fix_bare_cuv_names' not in ns:
        import pytest; pytest.skip('function not extracted')
    rows, log = ns['_fix_bare_cuv_names'](['「感皇恩」', '「呀！只落得'], 692, [])
    assert rows[0] == '〔感皇恩〕'
    assert any(e['kind'] == 'name_in_quotes' for e in log)


def test_inline_quote_noise_in_cuv_pass():
    ns = _load()
    if '_fix_cuv_brackets' not in ns:
        import pytest; pytest.skip('function not extracted')
    rows, log = ns['_fix_cuv_brackets'](['…花慵戴。﹁﹂﹁一東甌令花慵戴'], 692, [])
    assert '﹁﹂' not in rows[0]
    assert any(e['kind'] == 'inline_quote' for e in log)


def test_p692_product_rows_cleanup():
    """产品级回归：p692 真实 OCR 行经文本规则后 ﹁﹂ 无残留、感皇恩/東甌令/針線廂 均带〔〕。"""
    import json
    ns = _load()
    LI = json.load(open(os.path.join(ROOT, 'data/wz7_full/wz7_full_spotting_lines_patched.json'), encoding='utf-8'))
    rows = [str(t) for t in LI['691']]
    log = []
    rows, _ = ns['_fix_bare_cuv_names'](rows, 692, log)
    rows, _ = ns['_fix_cuv_brackets'](rows, 692, log)
    joined = ''.join(rows)
    assert '﹁﹂' not in joined
    for name in ('感皇恩', '東甌令', '針線廂'):
        assert ('〔' + name + '〕') in joined, name
