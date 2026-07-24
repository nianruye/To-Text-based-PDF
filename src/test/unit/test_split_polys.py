#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""split_polys 纯函数单元测试。

验证 split_text / clean_html / split_multiline 的核心契约。
模块无 import 副作用(re/json 只建常量),直接 import 测试。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from utils.split_polys import split_text, clean_html, split_multiline


class TestSplitText:
    """split_text: 文本按标点均分"""

    def test_single(self):
        """n=1 时返回原文本"""
        assert split_text('abc', 1) == ['abc']
        assert split_text('', 1) == ['']

    def test_two_equal(self):
        """n=2 均分"""
        r = split_text('12345678', 2)
        assert len(r) == 2
        assert ''.join(r) == '12345678'

    def test_punctuation_preferred(self):
        """优先在标点处断"""
        r = split_text('一二三，四五六。七八九', 2)
        assert len(r) == 2
        # 应该在第一个标点( ，)或第二个标点( 。)处断,不应在字中间
        assert not r[0].endswith('四')  # 避免断在"三，四"中间

    def test_five_way(self):
        """n=5, 全长中文"""
        text = '这是一个测试句子。这是第二个句子，看看效果怎么样。继续加字。还有。最后。'
        r = split_text(text, 5)
        assert len(r) == 5
        reconstructed = ''.join(r)
        assert reconstructed == text

    def test_english_text(self):
        """英文+标点(.;)"""
        r = split_text('Hello world. This is a test; more text here.', 3)
        assert len(r) == 3
        assert ''.join(r) == 'Hello world. This is a test; more text here.'


class TestCleanHtml:
    """clean_html: HTML 标签移除"""

    def test_no_html(self):
        assert clean_html('普通文本') == '普通文本'

    def test_remove_tag(self):
        r = clean_html('<table><tr><td>京兆</td><td>郑</td></tr></table>')
        assert '<' not in r
        assert '京兆' in r
        assert '郑' in r

    def test_remove_with_attrs(self):
        r = clean_html('<td colspan="2">封邑</td>')
        assert '<' not in r
        assert '封邑' in r


class TestSplitMultiline:
    """split_multiline: 核心拆分逻辑"""

    def test_no_split_for_short(self):
        """矮 poly(单行高)不拆分"""
        sl = {'0': ['正文行内容']}
        co = {'0': [[[0, 0], [400, 0], [400, 40], [0, 40]]]}  # h=40px
        nsl, nco = split_multiline(sl, co, K=0.7)
        assert nsl['0'] == ['正文行内容']
        assert len(nco['0']) == 1

    def test_split_by_formula(self):
        """高 poly 按公式拆分。h=296px,chars=149,w=1302px
        公式: n = round(sqrt(296*149*0.7/1302)) = round(sqrt(23.7)) = 5
        """
        text = '李著中国经济史稿分先秦两汉、魏晋南北朝隋唐、宋元明三册，全书着重阐述。'
        text += '在说明封建社会生产关系变化中，著者十分重视政治与经济相互作用的关系。'
        text += '特别是历代王朝在权利分配上的种种表现。'  # ~149 chars
        sl = {'0': [text]}
        h = 296; w = 1302
        co = {'0': [[[0, 0], [w, 0], [w, h], [0, h]]]}
        nsl, nco = split_multiline(sl, co, K=0.7)
        # n = round(sqrt(296*len(text)*0.7/1302))，取决于实际 text 长度
        assert len(nsl['0']) >= 4  # 至少 4 份

    def test_preserves_key_order(self):
        """key 不变且顺序保留"""
        sl = {'0': ['a'], '2': ['b'], '1': ['c']}
        co = {
            '0': [[[0,0],[10,0],[10,10],[0,10]]],
            '2': [[[0,0],[10,0],[10,30],[0,30]]],
            '1': [[[0,0],[10,0],[10,10],[0,10]]],
        }
        nsl, nco = split_multiline(sl, co, K=0.7)
        assert list(nsl.keys()) == ['0', '2', '1']

    def test_labels_forwarded(self):
        """labels 正确透传"""
        sl = {'0': ['正文行']}
        co = {'0': [[[0,0],[400,0],[400,100],[0,100]]]}
        lb = {'0': ['header']}
        nsl, nco, nlb = split_multiline(sl, co, lb, K=0.7)
        # h=100,w=400,chars=3: n=sqrt(100*3*0.7/400)=sqrt(0.525)=1, 不拆分
        assert nsl['0'] == ['正文行']
        assert nlb['0'] == ['header']
