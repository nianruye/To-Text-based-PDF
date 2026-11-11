#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t275: CJK 上下文 ASCII 标点归一化。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from utils.tex_escape import normalize_cjk_punct


def test_cjk_both_sides():
    out, ch = normalize_cjk_punct('中国,世界')
    assert out == '中国，世界' and len(ch) == 1


def test_number_latin_untouched():
    for s in ('3.5', 'a,b', '1987.', 'A.', 'abc:def', '12:30'):
        out, ch = normalize_cjk_punct(s)
        assert out == s and ch == [], s


def test_already_fullwidth_idempotent():
    for s in ('中国，世界', '甲；乙', '他说：“好！”'):
        out1, ch1 = normalize_cjk_punct(s)
        out2, ch2 = normalize_cjk_punct(out1)
        assert out1 == s and out2 == s and ch1 == [] and ch2 == []


def test_line_edges_untouched():
    for s in (',中国', '中国,', ',', '中国 , 世界'):
        out, _ = normalize_cjk_punct(s)
        # 行首/行尾孤立；中间空格隔开后左右仍是CJK时按设计替换
        if s == '中国 , 世界':
            assert out == '中国 , 世界'
        else:
            assert out == s, s


def test_mixed_cjk_latin_boundary_locked():
    # 右邻拉丁：不换；右邻CJK：换（明确锁边界）
    assert normalize_cjk_punct('他说,OK')[0] == '他说,OK'
    assert normalize_cjk_punct('他说,好的')[0] == '他说，好的'


def test_idempotent_plain():
    s = '甲,乙;丙:丁?戊!己.庚'
    out1, _ = normalize_cjk_punct(s)
    out2, _ = normalize_cjk_punct(out1)
    assert out1 == out2 == '甲，乙；丙：丁？戊！己。庚'


def test_line_edge_context():
    # 行尾/行首的 ASCII 标点可用上一/下一行邻字归一化
    assert normalize_cjk_punct('例如,', right_context='虽')[0] == '例如，'
    assert normalize_cjk_punct('例如,', right_context='O')[0] == '例如,'
    assert normalize_cjk_punct(',中国', left_context='前')[0] == '，中国'
