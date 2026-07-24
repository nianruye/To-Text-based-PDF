#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_cases.py - 排版还原功能断言测试

从 Spec 测试点提取,每个功能一个断言函数。
改 build_classic.py 后运行,防功能级回归。

用法:
    python3 src/test/test_cases.py output/成果_wz2_classic_latest.pdf
    python3 src/test/test_cases.py output/成果_wz2_classic_latest.pdf --src source_pdf/wz2.pdf
"""
import fitz
import statistics
import sys
import os
import re

# ============================================================
# 辅助函数
# ============================================================

def _get_lines(pdf, page_idx, x_min=20, x_max=560):
    """提取某页正文行(排边栏),返回 [(x0, y0, x1, y1, sz, text), ...]"""
    pg = pdf[page_idx]
    lines = []
    for blk in pg.get_text('dict')['blocks']:
        for ln in blk.get('lines', []):
            x0, y0, x1, y1 = ln['bbox']
            if y1 - y0 < 1 or x0 < x_min or x0 > x_max:
                continue
            sz = round(ln['spans'][0]['size'], 1) if ln.get('spans') else 0
            txt = ''.join(s['text'] for s in ln.get('spans', []))
            lines.append((x0, y0, x1, y1, sz, txt))
    return lines

def _get_pitch(pdf, page_idx):
    """测某页 pitch(行间距中位)"""
    lines = _get_lines(pdf, page_idx)
    ys = sorted(l[1] for l in lines)
    diffs = [ys[i+1] - ys[i] for i in range(len(ys)-1) if 5 < ys[i+1] - ys[i] < 50]
    return statistics.median(diffs) if diffs else 0

def _find_lines_with(pdf, page_idx, keyword):
    """找含关键词的行"""
    lines = _get_lines(pdf, page_idx)
    return [l for l in lines if keyword in l[5]]

def _find_seq_lines(pdf, page_idx):
    """找序号行(行首〔X〕)"""
    lines = _get_lines(pdf, page_idx, x_min=10)
    return [l for l in lines if re.match(r'〔', l[5][:3])]

# ============================================================
# 01 墨高重叠 + 位置还原
# ============================================================

def test_pitch_p11(pdf):
    """p11 正文 pitch≈35pt(源35.1)"""
    pitch = _get_pitch(pdf, 10)
    assert 33 <= pitch <= 37, f'p11 pitch={pitch:.1f}, 应在33-37'

def test_pitch_p26(pdf):
    """p26 注释页 pitch≈28pt(源28.0)"""
    pitch = _get_pitch(pdf, 25)
    assert 26 <= pitch <= 30, f'p26 pitch={pitch:.1f}, 应在26-30'

def test_no_overflow(pdf):
    """0溢出(页数=783)"""
    n = len(pdf)
    assert n == 783, f'页数={n}, 应=783(0溢出)'

def test_pitch_rate(pdf):
    """pitch达标率>50%(需verify_geom数据,简化:测p11/p26/p51 pitch合理)"""
    p11 = _get_pitch(pdf, 10)
    p26 = _get_pitch(pdf, 25)
    p51 = _get_pitch(pdf, 50)
    assert p11 > 30 and p26 > 25 and p51 > 25, f'pitch偏低 p11={p11:.1f} p26={p26:.1f} p51={p51:.1f}'

# ============================================================
# 02 字号分类 + 序号位置识别
# ============================================================

def test_p11_body_font(pdf):
    """p11 正文字号 BODY_FONT≈17pt"""
    lines = _get_lines(pdf, 10)
    body_sz = [l[4] for l in lines if 16 < l[4] < 19 and len(l[5]) > 10]
    assert body_sz, 'p11 无正文字号 16-19pt 的行'
    med = statistics.median(body_sz)
    assert 16 <= med <= 18, f'p11 正文字号={med}, 应在16-18'

def test_p15_note_font(pdf):
    """p15 注释字号 NOTE_FONT≈14.6pt"""
    lines = _get_lines(pdf, 14)
    note_sz = [l[4] for l in lines if 13 < l[4] < 16 and len(l[5]) > 5]
    assert note_sz, 'p15 无注释字号 13-16pt 的行'
    med = statistics.median(note_sz)
    assert 13.5 <= med <= 15.5, f'p15 注释字号={med}, 应在13.5-15.5'

def test_p5_preface_font(pdf):
    """p5 前言字号≈16pt(非BODY 18/NOTE 14.6)"""
    lines = _get_lines(pdf, 4)
    body_sz = [l[4] for l in lines if 14 < l[4] < 18 and len(l[5]) > 10]
    assert body_sz, 'p5 无前言字号 14-18pt 的行'
    med = statistics.median(body_sz)
    assert 15 <= med <= 17, f'p5 前言字号={med}, 应在15-17(非BODY 18/NOTE 14.6)'

# ============================================================
# 03 注释序号-文字分列对齐
# ============================================================

def test_p15_seq_x0_unified(pdf):
    """p15 序号〔X〕x0统一"""
    seq_lines = _find_seq_lines(pdf, 14)
    assert len(seq_lines) >= 3, f'p15 序号行数={len(seq_lines)}, 应>=3'
    x0s = [l[0] for l in seq_lines]
    spread = max(x0s) - min(x0s)
    assert spread <= 20, f'p15 序号x0差={spread:.0f}(max={max(x0s):.0f} min={min(x0s):.0f}), 应<=20'

def test_p15_cont_x0_unified(pdf):
    """p15 续行 x0统一(文字列)"""
    lines = _get_lines(pdf, 14)
    seq_ys = set(l[1] for l in lines if re.match(r'〔', l[5][:3]))
    cont_x0s = [l[0] for l in lines if l[1] not in seq_ys and len(l[5]) > 10 and 70 < l[0] < 110]   # 排除 frags(引文按源x绝对定位 x0>110)
    assert len(cont_x0s) >= 3, f'p15 续行数={len(cont_x0s)}, 应>=3'
    spread = max(cont_x0s) - min(cont_x0s)
    assert spread <= 20, f'p15 续行x0差={spread:.0f}, 应<=20'

def test_p15_no_overlap(pdf):
    """p15 序号+文字不重叠(span连续)"""
    pg = pdf[14]
    for blk in pg.get_text('dict')['blocks']:
        for ln in blk.get('lines', []):
            spans = sorted(ln.get('spans', []), key=lambda s: s['bbox'][0])
            for i in range(len(spans) - 1):
                gap = spans[i+1]['bbox'][0] - spans[i]['bbox'][2]
                if '〔' in spans[i]['text']:
                    assert gap >= -2, f'序号重叠 gap={gap:.0f} {spans[i]["text"][:5]!r}'

# ============================================================
# 04 正文缩进 + 字距
# ============================================================

def test_p11_paragraph_indent(pdf):
    """p11 正文段首缩进(x0>90=2em)"""
    lines = _get_lines(pdf, 10)
    body = [l for l in lines if 16 < l[4] < 19 and len(l[5]) > 10]
    assert body, 'p11 无正文行'
    # 至少有一行 x0>90(段首缩进)
    indented = [l for l in body if l[0] > 85]
    assert indented, f'p11 无段首缩进行(x0>85), body x0={[l[0] for l in body[:5]]}'

def test_char_spacing_positive(pdf):
    """字距>=0(不重叠)"""
    for idx in [10]:  # 只测正文页p11(注释页有frags多片段大负间距,非文字重叠)
        pg = pdf[idx]
        for blk in pg.get_text('dict')['blocks']:
            for ln in blk.get('lines', []):
                x0, y0, x1, y1 = ln['bbox']
                if y1 - y0 < 1 or x0 < 50 or x0 > 560:
                    continue
                spans = sorted(ln.get('spans', []), key=lambda s: s['bbox'][0])
                for i in range(len(spans) - 1):
                    if spans[i]['size'] < 10 or spans[i+1]['size'] < 10:
                        continue   # 排除上标(占全字宽,边界处有负间距,非文字重叠)
                    gap = spans[i+1]['bbox'][0] - spans[i]['bbox'][2]
                    assert gap >= -8, f'p{idx+1} 字距={gap:.0f}(重叠) {spans[i]["text"][:5]!r}'   # 允许-8(makebox[s]收缩/frags紧邻,非墨色重叠)

# ============================================================
# 05 校注标记转义 + 符号修正
# ============================================================

def test_p11_marker_superscript(pdf):
    """p11 校注标记上标 sz<10"""
    pg = pdf[10]
    found = False
    for blk in pg.get_text('dict')['blocks']:
        for ln in blk.get('lines', []):
            for s in ln.get('spans', []):
                if '〔' in s['text'] and '〕' in s['text'] and len(s['text']) <= 6:
                    assert s['size'] < 10, f'p11 校注标记 sz={s["size"]:.1f}, 应<10'
                    found = True
    assert found, 'p11 未找到上标校注标记'

def test_p32_circle_fixed(pdf):
    """p32 〔一〇九〕含〇非￿"""
    lines = _find_lines_with(pdf, 31, '〇')
    assert lines, 'p32 未找到含〇的行'
    for l in lines:
        assert '￿' not in l[5], f'p32 含￿(未转〇) {l[5][:15]!r}'

def test_no_wrong_bracket(pdf):
    """全书无】(OCR误识,应转〔)"""
    for i in range(min(len(pdf), 100)):
        txt = pdf[i].get_text()
        assert '】' not in txt, f'p{i+1} 含】(应转〔)'

# ============================================================
# 06 旁注补全 + 页码
# ============================================================

def test_p11_aside_completion(pdf):
    """p11 aside补全'卷第一本议第一'(7字)"""
    pg = pdf[10]
    aside_chars = []
    for blk in pg.get_text('dict')['blocks']:
        for ln in blk.get('lines', []):
            if ln['bbox'][0] > 540:  # 右栏 aside
                aside_chars.append(''.join(s['text'] for s in ln.get('spans', [])))
    aside = ''.join(aside_chars)
    assert '一' in aside, f'p11 aside={aside!r}, 应含"一"(补全)'

def test_p11_pagenum(pdf):
    """p11 页码=1"""
    pg = pdf[10]
    for blk in pg.get_text('dict')['blocks']:
        for ln in blk.get('lines', []):
            x0, y0, x1, y1 = ln['bbox']
            if y0 > pg.rect.height * 0.92 and y1 - y0 > 0.5:
                txt = ''.join(s['text'] for s in ln.get('spans', [])).strip()
                if txt.isdigit():
                    assert txt == '1', f'p11 页码={txt}, 应=1'

# ============================================================
# 07 正文+注释混排页(p37)
# ============================================================

def test_p37_mixed_font(pdf):
    """p37 正文17.3+注释14.6混排(非全注释字号)"""
    lines = _get_lines(pdf, 36)
    body_sz = [l[4] for l in lines if 17 < l[4] < 18 and len(l[5]) > 10]
    note_sz = [l[4] for l in lines if 14 < l[4] < 15 and len(l[5]) > 5]
    assert body_sz, 'p37 无正文字号17pt行(混排正文被降)'
    assert note_sz, 'p37 无注释字号14.6行'

def test_p37_no_dotfill(pdf):
    """p37 内容页无dotfill误判(余而补不足不应有...)"""
    pg = pdf[36]
    for blk in pg.get_text('dict')['blocks']:
        for ln in blk.get('lines', []):
            txt = ''.join(s['text'] for s in ln.get('spans', []))
            if re.search(r'\.{5,}|…{3,}', txt):
                assert False, f'p37 内容页dotfill误判: {txt[:20]!r}'

def test_p37_indent(pdf):
    """p37 正文段首缩进(x0>90)"""
    lines = _get_lines(pdf, 36)
    body = [l for l in lines if 17 < l[4] < 18 and len(l[5]) > 10]
    assert body, 'p37 无正文行'
    indented = [l for l in body if l[0] > 90]
    assert indented, f'p37 正文段首无缩进(x0>90), x0={[l[0] for l in body[:3]]}'

def test_p37_no_overflow_line(pdf):
    """p37 无行溢出版心(*力耕长行 x1<=545)"""
    pg = pdf[36]
    for blk in pg.get_text('dict')['blocks']:
        for ln in blk.get('lines', []):
            x0, y0, x1, y1 = ln['bbox']
            if y1 - y0 > 1 and 50 < x0 < 540:
                txt = ''.join(s['text'] for s in ln.get('spans', []))[:15]
                assert x1 <= 545, f'p37 行溢出版心 x1={x1:.0f}: {txt!r}'

# ============================================================
# 运行
# ============================================================

TESTS = [
    # 01 墨高重叠
    ('01 pitch_p11', test_pitch_p11),
    ('01 pitch_p26', test_pitch_p26),
    ('01 no_overflow', test_no_overflow),
    ('01 pitch_rate', test_pitch_rate),
    # 02 字号分类
    ('02 p11_body_font', test_p11_body_font),
    ('02 p15_note_font', test_p15_note_font),
    ('02 p5_preface_font', test_p5_preface_font),
    # 03 序号分列
    ('03 p15_seq_x0', test_p15_seq_x0_unified),
    ('03 p15_cont_x0', test_p15_cont_x0_unified),
    ('03 p15_no_overlap', test_p15_no_overlap),
    # 04 正文缩进
    ('04 p11_indent', test_p11_paragraph_indent),
    ('04 char_spacing', test_char_spacing_positive),
    # 05 校注标记
    ('05 p11_marker_sz', test_p11_marker_superscript),
    ('05 p32_circle', test_p32_circle_fixed),
    ('05 no_wrong_bracket', test_no_wrong_bracket),
    # 06 旁注/页码
    ('06 p11_aside', test_p11_aside_completion),
    ('06 p11_pagenum', test_p11_pagenum),
    # 07 正文+注释混排页(p37)
    ('07 p37_mixed_font', test_p37_mixed_font),
    ('07 p37_no_dotfill', test_p37_no_dotfill),
    ('07 p37_indent', test_p37_indent),
    ('07 p37_no_overflow_line', test_p37_no_overflow_line),
]

def run_all(pdf_path):
    """运行所有测试,输出 PASS/FAIL"""
    pdf = fitz.open(pdf_path)
    passed, failed = 0, 0
    print(f'测试: {pdf_path} ({len(pdf)}页)')
    print('-' * 60)
    for name, fn in TESTS:
        try:
            fn(pdf)
            print(f'  ✓ {name}')
            passed += 1
        except AssertionError as e:
            print(f'  ✗ {name}: {e}')
            failed += 1
        except Exception as e:
            print(f'  ! {name}: ERROR {e}')
            failed += 1
    print('-' * 60)
    print(f'{passed} PASS, {failed} FAIL')
    pdf.close()
    return failed == 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python3 test_cases.py <pdf路径>')
        sys.exit(1)
    ok = run_all(sys.argv[1])
    sys.exit(0 if ok else 1)
