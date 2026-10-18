#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_tounicode_circled 的纯函数测试"""
import importlib.util
import pathlib

import pytest

_TOOL = pathlib.Path(__file__).resolve().parents[2] / 'tools' / 'fix_tounicode_circled.py'


def _load():
    spec = importlib.util.spec_from_file_location('ftc', _TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ftc = _load()


class TestPlan:
    """_plan(u, allowed, run) -> 目标码位 或 None"""

    def test_dingbat_remapped_when_circled_used(self):
        # 源书用 ①，产物映成 ➀ -> 改回 ①
        assert ftc._plan(0x2780, {'①', '甲'}) == 0x2460

    def test_no_change_when_source_uses_dingbat(self):
        # 源书真的用了 ➀ -> 不动
        assert ftc._plan(0x2780, {'➀', '甲'}) is None

    def test_no_change_when_neither_present(self):
        assert ftc._plan(0x2780, {'甲', '乙'}) is None

    def test_non_dingbat_untouched(self):
        assert ftc._plan(0x4E00, {'一'}) is None

    def test_range_requires_all_circled(self):
        # 连续 3 个码位 ➀➁➂ -> 要求 ①②③ 都在源集里
        assert ftc._plan(0x2780, {'①', '②', '③'}, run=3) == 0x2460
        assert ftc._plan(0x2780, {'①', '②'}, run=3) is None


class TestPatchCmap:
    """实际改写的三种 CMap 形态"""

    def test_bfrange_triplet(self):
        # 实测 wz7: <0397> <03A0> <2780> 是 ①..⑩ 的 CID
        cmap = (b'1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n'
                b'2 beginbfrange\n<0397> <03A0> <2780>\n<03A1> <03A4> <246A>\n'
                b'endbfrange\n')
        allowed = set('①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭')
        stats = []
        out = ftc.patch_cmap(cmap, allowed, stats)
        assert b'<0397> <03A0> <2460>' in out, '①..⑩ 的 range 应改到 U+2460'
        assert b'<03A1> <03A4> <246A>' in out, '⑪..⑭ 本来就对, 不许动'
        assert len(stats) == 1

    def test_bfchar_single(self):
        cmap = b'1 beginbfchar\n<0919> <2780>\nendbfchar\n'
        allowed = {'①'}
        stats = []
        out = ftc.patch_cmap(cmap, allowed, stats)
        assert b'<0919> <2460>' in out
        assert len(stats) == 1

    def test_untouched_when_source_has_dingbat(self):
        cmap = b'1 beginbfchar\n<0919> <2780>\nendbfchar\n'
        stats = []
        out = ftc.patch_cmap(cmap, {'➀'}, stats)
        assert b'<0919> <2780>' in out and not stats

    def test_normal_chars_untouched(self):
        cmap = b'2 beginbfchar\n<0001> <4E00>\n<0002> <4E8C>\nendbfchar\n'
        stats = []
        out = ftc.patch_cmap(cmap, {'一', '二'}, stats)
        assert out == cmap and not stats
