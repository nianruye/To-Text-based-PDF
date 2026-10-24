#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务F：把任务E普查的 37 处漏识元素灌进渲染端（§1.0a5）。

被测实现：`src/pipelines/build_vert.py`
  · `_ring_ins_num` / `RING_INS_BASE` —— 圈码占位 chr(0xE100+n) -> n
  · `_ring_put` —— 句末圈码: ≤50 用 Unicode 圈码字形; >50 用 ○ + 小号数字
  · `_apply_missed_fix` —— 灌入清单: dash 列首插 2 个 DASH_INS、ring 情形①替换尾部数字、
    情形②列尾追加、页号越界跳过

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_taskF.py -v
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_CONSTS = ['DASH_CHARS', 'DASH_INS', 'RING_INS_BASE', 'RING_SIZE',
           'XSCALE', 'PT2BP', 'PAGE_ORIGIN_BP', 'DASH_RULE_W_RAW', 'DASH_RULE_W', 'INK_ASC', 'BOLD_W',
           'VERT_FORMS', 'VERT_METRICS', 'BR_ON', 'BR_SIZE_DEF', 'BR_SIZE']
_FUNCS = ['_put_tex', '_esc_ch', '_vb', '_br_put', '_ring_ins_num', '_ring_put',
          '_apply_missed_fix']
# _CIRCLED_CP 由模块里的 for 循环生成, ast 加载器不执行循环 -> 测试注入同值表
_CIRCLED = {}
for _n in range(1, 21):
    _CIRCLED[_n] = 0x2460 + _n - 1
for _n in range(21, 36):
    _CIRCLED[_n] = 0x3251 + _n - 21
for _n in range(36, 51):
    _CIRCLED[_n] = 0x32B1 + _n - 36


@pytest.fixture(scope='module')
def ns():
    return load('build_vert.py', _FUNCS, _CONSTS,
                mocks={'page_h': 400.0, '_CIRCLED_CP': _CIRCLED, 'json': json,
                       'keys': ['0', '1'], 'sl': {}, 'co': {}})


# ---------- A. 占位解析 ----------
class TestRingInsNum:
    def test_placeholder(self, ns):
        assert ns['RING_INS_BASE'] == 0xE100
        assert ns['_ring_ins_num'](chr(0xE100 + 8)) == 8
        assert ns['_ring_ins_num'](chr(0xE100 + 77)) == 77

    def test_normal_char(self, ns):
        for ch in '孟⑩7○—':
            assert ns['_ring_ins_num'](ch) is None


# ---------- B. 圈码渲染 ----------
class TestRingPut:
    def test_unicode_circled(self, ns):
        """≤50: 用 Unicode 圈码字形(⑩), 字号 RING_SIZE×F, 整圆(xs=1, 无压缩), 线心/格心对齐。

        字号从 RING_SIZE 推导(不写死): 源书圈外径 17pt / Noto 圈码墨高 0.93em
        -> 字号 18.3pt @ 正文步进 19.3pt -> RING_SIZE = 0.948 ~ 0.95。
        """
        F = 20.0
        Fr = round(F * float(ns['RING_SIZE']), 1)
        puts = ns['_ring_put'](10, 200.0, 100.0, F)
        assert len(puts) == 1
        s = puts[0]
        assert '⑩' in s
        assert '\\fontsize{%.1fpt}{%.1fpt}' % (Fr, Fr) in s
        assert 'cm}' not in s                     # xs=1 -> 没有 q/...cm 压缩
        # x = 列心 - Fr/2
        assert '\\put(%.1f,' % ((200.0 - Fr / 2.0) * ns['PT2BP']) in s
        # y = page_h - (格心 + 0.38*Fr)
        assert '%.1f' % ((400.0 - (100.0 + 0.380 * Fr)) * ns['PT2BP']) in s

    def test_composite_over_50(self, ns):
        """77 无 Unicode 圈码 -> ○ + 两个小号数字(文本层 3 字)。"""
        puts = ns['_ring_put'](77, 200.0, 100.0, 20.0)
        assert len(puts) == 3
        assert '○' in puts[0]
        assert '7' in puts[1] and '7' in puts[2]
        assert '\\fontsize{9.0pt}{9.0pt}' in puts[1]

    def test_other_numbers(self, ns):
        """21-35 / 36-50 的圈码码位也应命中 Unicode 路径。"""
        assert '㉛' in ns['_ring_put'](31, 200.0, 100.0, 20.0)[0]
        assert '㊲' in ns['_ring_put'](37, 200.0, 100.0, 20.0)[0]


# ---------- C. 灌入清单 ----------
def _poly(x0, y0, x1, y1):
    # OCR coords 单位 2x px; 传入 pt -> x2
    return [[x0 * 2, y0 * 2], [x1 * 2, y0 * 2], [x1 * 2, y1 * 2], [x0 * 2, y1 * 2]]


class TestApplyMissedFix:
    def _run(self, ns, tmp_path, items, sl, co, keys):
        p = tmp_path / 'fix.json'
        p.write_text(json.dumps({'items': items}, ensure_ascii=False), encoding='utf-8')
        ns['keys'] = keys
        ns['sl'] = sl
        ns['co'] = co
        st = ns['_apply_missed_fix'](str(p))
        return st, sl

    def test_dash_prepend(self, ns, tmp_path):
        sl = {'0': ['孟州充軍。']}
        co = {'0': [_poly(340.5, 248.2, 361.6, 398.9)]}
        st, sl = self._run(ns, tmp_path, [{
            'page': 1, 'col': [340.5, 248.2, 361.6, 398.9], 'class': 'dash',
            'insert_dash': 2, 'text': '孟州充軍。'}], sl, co, ['0'])
        assert st['dash'] == 1
        assert sl['0'][0] == ns['DASH_INS'] * 2 + '孟州充軍。'

    def test_ring_situation1_replace(self, ns, tmp_path):
        sl = {'0': ['句子。11']}
        co = {'0': [_poly(100, 100, 120, 300)]}
        st, sl = self._run(ns, tmp_path, [{
            'page': 1, 'col': [100, 100, 120, 300], 'class': 'ring',
            'number': 11, 'situation': 1, 'text': '句子。11'}], sl, co, ['0'])
        assert st['ring1'] == 1
        assert sl['0'][0] == '句子。' + chr(0xE100 + 11)

    def test_ring_situation2_append(self, ns, tmp_path):
        sl = {'0': ['孟州充軍。']}
        co = {'0': [_poly(340.5, 248.2, 361.6, 398.9)]}
        st, sl = self._run(ns, tmp_path, [{
            'page': 1, 'col': [340.5, 248.2, 361.6, 398.9], 'class': 'ring',
            'number': 10, 'situation': 2, 'text': '孟州充軍。'}], sl, co, ['0'])
        assert st['ring2'] == 1
        assert sl['0'][0] == '孟州充軍。' + chr(0xE100 + 10)

    def test_page_out_of_range_skipped(self, ns, tmp_path):
        """wz6（231 页）跑同一份 wz7 清单 -> 页号越界全部跳过, 文本不变。"""
        sl = {'0': ['使用。']}
        co = {'0': [_poly(0, 0, 10, 10)]}
        st, sl = self._run(ns, tmp_path, [{
            'page': 1683, 'col': [340.5, 248.2, 361.6, 398.9], 'class': 'ring',
            'number': 10, 'situation': 2, 'text': '孟州充軍。'}], sl, co, ['0'])
        assert st['skip'] == 1
        assert sl['0'][0] == '使用。'

    def test_column_not_matched_skipped(self, ns, tmp_path):
        sl = {'0': ['abc']}
        co = {'0': [_poly(0, 0, 10, 100)]}
        st, sl = self._run(ns, tmp_path, [{
            'page': 1, 'col': [340.5, 248.2, 361.6, 398.9], 'class': 'ring',
            'number': 10, 'situation': 2, 'text': '孟州充軍。'}], sl, co, ['0'])
        assert st['skip'] == 1
        assert sl['0'][0] == 'abc'
