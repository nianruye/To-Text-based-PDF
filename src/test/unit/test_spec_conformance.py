#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""spec-实现一致性守卫（t215）：本季新 spec 的可断言条款。"""
import os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def _read(rel):
    return open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _tokens(text):
    # t226 F3：完整 token 集合（不做子串匹配，避免 replaced→replacedX 假阴性）
    return set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', text))


def _has_token(tok, text):
    return tok in _tokens(text)


def test_corrected_text_report_fields():
    spec = _read('spec/governance/CORRECTED_TEXT.md')
    src = _read('src/tools/corrected_text.py')
    for tok in ('replaced', 'pages', 'line_counts', 'warnings', 'source', 'sha256'):
        assert _has_token(tok, spec), 'spec 缺字段 %s' % tok
        assert _has_token(tok, src), '实现缺字段 %s（spec 声明但缺失）' % tok


def test_horizontal_calib_selfcheck_codes():
    spec = _read('spec/governance/HORIZONTAL_CALIB.md')
    src = _read('src/utils/geometry.py')
    codes = ['pages_mismatch', 'empty_input', 'source_of_page_size_missing',
             'dpi_residual_large', 'font_out_of_range', 'baseline_font_ratio_out',
             'page_size_overcoverage', 'page_size_coverage_low', 'pitch_low_sample',
             'full_sample_low', 'cw_out_of_range', 'measure_out_of_range',
             'margin_out_of_range', 'toc_low_sample', 'toc_foot_x_out',
             'toc_title_max_out']
    assert 'selfcheck' in spec and '自检' in spec, 'spec 缺自检条款'
    for c in codes:
        assert _has_token(c, src), 'selfcheck 码缺失: %s' % c


def test_page_image_layout_env_defaults():
    spec = _read('spec/governance/PAGE_IMAGE_LAYOUT.md')
    src = _read('src/pipelines/build_geom.py')
    for env in ('LAYOUT_HEADINGS', 'LAYOUT_FIGS', 'LAYOUT_TOC',
                'PAGE_IMAGE_PAGES', 'PAGE_IMAGE_FULL_RATIO'):
        assert _has_token(env, spec), 'spec 缺 env: %s' % env
        assert _has_token(env, src), '实现缺 env: %s' % env
    for env, default in (('LAYOUT_HEADINGS', ''), ('LAYOUT_FIGS', ''), ('LAYOUT_TOC', ''),
                         ('PAGE_IMAGE_PAGES', ''), ('PAGE_IMAGE_FULL_RATIO', '0.40')):
        pat = r"os\.environ\.get\('%s',\s*'%s'\)" % (env, re.escape(default))
        assert re.search(pat, src), 'env 默认值不符: %s=%r' % (env, default)


def test_scan2pdf_report_top_level_keys():
    src = _read('src/tools/scan2pdf.py')
    assert 'report = dict(' in src
    for frag in ("tool='scan2pdf'", "version='v1'", 'book=args.book',
                 'input=args.input', 'out=args.out', 'input_sha256=',
                 'steps=[]', 'exit=None'):
        assert frag in src, 'report 顶层键缺失: %s' % frag


def test_token_matcher_rejects_distinct_value():
    # fixture 说明：t226 用完整 token，不拿子串；`APPLIED_X`/`replacedX` 均不应匹配 `replaced`。
    assert not _has_token('replaced', 'APPLIED_X')
    assert not _has_token('replaced', 'replacedX')
    assert _has_token('replaced', 'reported replaced count')
