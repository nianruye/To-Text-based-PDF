#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""corrected_text 单测（CORRECTED_TEXT.md v1）。"""
import json, os, sys, tempfile
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'tools'))
import corrected_text as ct


def _lines():
    return {'0': ['旧甲', '旧乙'], '2': ['旧丙']}


def _write(tmp, doc):
    p = os.path.join(tmp, 'corrected_text.json')
    json.dump(doc, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    return p


def test_replace_and_stats():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, {'_comment': 'x', '2': {'0': '新丙'}, '0': {'1': '新乙'}})
        patched, st = ct.apply_corrected_text(_lines(), p)
        assert patched['2'] == ['新丙'] and patched['0'] == ['旧甲', '新乙']
        assert st['enabled'] and st['applied'] == 2 and st['replaced'] == 2
        assert st['pages'] == ['0', '2'] and st['pages_count'] == 2
        assert st['skipped'] == 0 and len(st['sha256']) == 64
        assert st['line_counts'] == {'0': {'before': 2, 'after': 2},
                                     '2': {'before': 1, 'after': 1}}


def test_unknown_page_and_line_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, {'9': {'0': 'x'}, '0': {'5': 'x'}})
        patched, st = ct.apply_corrected_text(_lines(), p)
        assert patched == _lines()
        assert st['applied'] == 0 and st['skipped'] == 2
        codes = [w['code'] for w in st['warnings']]
        assert 'unknown_page' in codes and 'unknown_line' in codes
        assert st['warnings'][0]['page'] == '9'


def test_invalid_value_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, {'0': {'0': '', '1': 123}})
        patched, st = ct.apply_corrected_text(_lines(), p)
        assert patched == _lines() and st['skipped'] == 2
        assert all(w['code'] == 'invalid_value' for w in st['warnings'])


def test_missing_file_disabled_zero_regression():
    lines = _lines()
    patched, st = ct.apply_corrected_text(lines, '/nonexistent/x.json')
    assert patched == lines and st['enabled'] is False and st['applied'] == 0


def test_bad_json_raises():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, 'bad.json'); open(p, 'w').write('{not json')
        try:
            ct.apply_corrected_text(_lines(), p)
            assert False, 'should raise'
        except ValueError:
            pass


def test_root_not_object_raises():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, ['x'])
        try:
            ct.apply_corrected_text(_lines(), p)
            assert False, 'should raise'
        except ValueError:
            pass


def test_newline_in_value_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, {'0': {'0': '甲\n乙'}})
        patched, st = ct.apply_corrected_text(_lines(), p)
        assert patched == _lines() and st['skipped'] == 1
        assert st['warnings'][0]['code'] == 'newline_in_value'
