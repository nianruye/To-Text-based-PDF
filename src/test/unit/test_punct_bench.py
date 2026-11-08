#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""punct_bench v1.1 指标单测（≥8 例：GB/T 全类、竖排形态、多段引文、句读值错、旧 gold 兼容）。"""
import json
import os
import sys
import tempfile
import fitz

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'tools'))
import punct_bench as pb  # noqa: E402


def _coords_lines(texts):
    coords = {}; lines = {}
    for k, cols in enumerate(texts):
        coords[str(k)] = []; lines[str(k)] = []
        for ci, t in enumerate(cols):
            x0 = 60 + ci * 40
            coords[str(k)].append([[x0, 100], [x0 + 25, 100], [x0 + 25, 400], [x0, 400]])
            lines[str(k)].append(t)
    return coords, lines


def _cell(coords, page_key, col, pos, n):
    xs = [q[0] for q in coords[page_key][col]]; ys = [q[1] for q in coords[page_key][col]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    step = (y1 - y0) / max(1, n)
    return [round((x0 + x1) / 2, 2), round(y0 + (pos + 0.5) * step, 2), round(x1 - x0, 2), round(step, 2)]


def _gold_item(texts, page, col, pos, cls, value, extra=None):
    coords, _ = _coords_lines(texts)
    c = _cell(coords, str(page - 1), col, pos, len(texts[page - 1][col]))
    item = dict(id='g-%d-%d-%d-%s' % (page, col, pos, cls), page=page, column=col, char_pos=pos,
                **{'class': cls}, value=value,
                bbox=[c[0] - 12, c[1] - 12, c[0] + 12, c[1] + 12], cell=c, axis='vertical',
                evidence={'type': 'manual', 'source': 'unit'}, crop='crops/x.png')
    if extra:
        item.update(extra)
    return item


def _run(gold, texts, content=None, mode='cell'):
    with tempfile.TemporaryDirectory() as tmp:
        coords, lines = _coords_lines(texts)
        cp = os.path.join(tmp, 'c.json'); lp = os.path.join(tmp, 'l.json'); gp = os.path.join(tmp, 'g.json')
        json.dump(coords, open(cp, 'w', encoding='utf-8'), ensure_ascii=False)
        json.dump(lines, open(lp, 'w', encoding='utf-8'), ensure_ascii=False)
        json.dump(gold, open(gp, 'w', encoding='utf-8'), ensure_ascii=False)
        pdf = os.path.join(tmp, 'o.pdf'); d = fitz.open(); d.new_page(width=400, height=600).insert_text((10, 10), 'x'); d.save(pdf)
        out = os.path.join(tmp, 'out.json')
        args = ['--gold', gp, '--pdf', pdf, '--coords', cp, '--lines', lp, '--out-json', out, '--mode', mode]
        if content is not None:
            cpath = os.path.join(tmp, 'cg.json'); json.dump(content, open(cpath, 'w', encoding='utf-8'), ensure_ascii=False)
            args += ['--content-gold', cpath]
        assert pb.main(args) == 0
        return json.load(open(out, encoding='utf-8'))


def _g(items):
    return {'schema_version': 'punct-eval-v1.1', 'dataset': {'id': 'unit', 'split': 'wz7'}, 'items': items}


# 1. v1 旧 gold 兼容（4 类）
def test_old_gold_compat_quotes():
    texts = [['「甲」乙']]
    gold = _g([_gold_item(texts, 1, 0, 0, 'quote_open', '「'),
               _gold_item(texts, 1, 0, 2, 'quote_close', '」')])
    r = _run(gold, texts)
    assert r['overall']['position_precision'] == 1.0
    assert r['by_class']['quote_open']['direction_accuracy'] == 1.0


# 2. 句读（period）位置+值
def test_sentence_period_position_value():
    texts = [['甲。乙']]
    gold = _g([_gold_item(texts, 1, 0, 1, 'period', '。')])
    r = _run(gold, texts)
    assert r['by_class']['period']['tp'] == 1
    assert r['by_class']['period']['value_accuracy'] == 1.0


# 3. 句读值错（comma vs enumeration_comma：FN+FP）
def test_sentence_value_error():
    texts = [['甲、乙']]
    gold = _g([_gold_item(texts, 1, 0, 1, 'comma', '，')])
    r = _run(gold, texts)
    assert r['by_class']['comma']['fn'] == 1
    assert r['by_class']['enumeration_comma']['fp'] == 1


# 4. 竖排引号形态（﹁﹂）与 form
def test_vertical_quote_form():
    texts = [['﹁甲﹂乙']]
    gold = _g([_gold_item(texts, 1, 0, 0, 'quote_open', '﹁', {'form': 'vertical'}),
               _gold_item(texts, 1, 0, 2, 'quote_close', '﹂', {'form': 'vertical'})])
    r = _run(gold, texts)
    assert r['by_class']['quote_open']['tp'] == 1
    assert r['by_class']['quote_open']['form_accuracy'] == 1.0


# 5. 横排/竖排混用（“” vs 「」：direction 对、form 不罚）
def test_horizontal_mixed_form():
    texts = [['“甲”乙']]
    gold = _g([_gold_item(texts, 1, 0, 0, 'quote_open', '「', {'form': 'vertical'}),
               _gold_item(texts, 1, 0, 2, 'quote_close', '」', {'form': 'vertical'})])
    r = _run(gold, texts)
    assert r['by_class']['quote_open']['direction_accuracy'] == 1.0
    assert r['by_class']['quote_open']['form_accuracy'] == 0.0  # 仅诊断


# 6. 书名号（《》）
def test_booktitle_pair():
    texts = [['《甲》乙']]
    gold = _g([_gold_item(texts, 1, 0, 0, 'booktitle_open', '《'),
               _gold_item(texts, 1, 0, 2, 'booktitle_close', '》')])
    r = _run(gold, texts)
    assert r['by_class']['booktitle_open']['tp'] == 1
    assert r['by_class']['booktitle_close']['direction_accuracy'] == 1.0


# 7. 省略号（……）
def test_ellipsis_length():
    texts = [['甲……乙']]
    gold = _g([_gold_item(texts, 1, 0, 1, 'ellipsis', '……', {'length_pt': 150.0})])
    r = _run(gold, texts)
    assert r['by_class']['ellipsis']['tp'] == 1
    assert r['by_class']['ellipsis']['length_median_error'] >= 0


# 8. 多段引文：非最后段缺闭号不判 FN
def test_multi_paragraph_carry_no_fn():
    # 第 1 段只有开号，第 2 段开号+闭号
    texts = [['「甲', '「乙」']]
    gold = _g([
        _gold_item(texts, 1, 0, 0, 'quote_open', '「', {'quote_group_id': 'g1', 'paragraph_index': 0, 'paragraph_count': 2, 'is_final_paragraph': False}),
        _gold_item(texts, 1, 1, 0, 'quote_open', '「', {'quote_group_id': 'g1', 'paragraph_index': 1, 'paragraph_count': 2, 'is_final_paragraph': True}),
        _gold_item(texts, 1, 1, 2, 'quote_close', '」', {'quote_group_id': 'g1', 'paragraph_index': 1, 'paragraph_count': 2, 'is_final_paragraph': True}),
    ])
    r = _run(gold, texts)
    assert r['overall']['fn'] == 0
    assert r['structural']['multi_para_validity'] == 1.0


# 9. 多段引文：中间段闭号 -> unexpected_close
def test_multi_paragraph_unexpected_close():
    texts = [['「甲」', '「乙」']]
    gold = _g([
        _gold_item(texts, 1, 0, 0, 'quote_open', '「', {'quote_group_id': 'g1', 'paragraph_index': 0, 'paragraph_count': 2, 'is_final_paragraph': False}),
        _gold_item(texts, 1, 0, 2, 'quote_close', '」', {'quote_group_id': 'g1', 'paragraph_index': 0, 'paragraph_count': 2, 'is_final_paragraph': False}),
        _gold_item(texts, 1, 1, 0, 'quote_open', '「', {'quote_group_id': 'g1', 'paragraph_index': 1, 'paragraph_count': 2, 'is_final_paragraph': True}),
    ])
    r = _run(gold, texts)
    assert r['structural']['unexpected_close'] == 1


# 10. 括号类型错（圆括号 vs 方括号 gold）
def test_bracket_type_mismatch():
    texts = [['（甲）乙']]
    gold = _g([_gold_item(texts, 1, 0, 0, 'bracket_type', '〔〕', {'name': '甲'})])
    r = _run(gold, texts)
    assert r['by_class']['bracket_type']['tp'] == 1
    assert r['by_class']['bracket_type']['type_accuracy'] == 0.0


# 11. 圈码
def test_ring_value():
    texts = [['甲③乙']]
    gold = _g([_gold_item(texts, 1, 0, 1, 'ring', '3')])
    r = _run(gold, texts)
    assert r['by_class']['ring']['tp'] == 1
    assert r['by_class']['ring']['value_accuracy'] == 1.0


# 12. 内容 CER + 存疑字
def test_content_cer_doubt():
    texts = [['甲丙丁']]
    gold = _g([])
    r = _run(gold, texts, {'items': [{'page': 1, 'text': '甲乙丙?丁'}]})
    c = r['content']
    assert c['doubt_chars'] == 1 and c['edit_distance'] == 1 and abs(c['cer'] - 0.25) < 1e-6


# ===================== v1.3 序列口径单测 =====================
def _chars(items):
    return [(c, (x, y, x + 10, y + 10)) for c, x, y in items]


def test_reading_order_vertical_right_to_left():
    chars = _chars([('甲', 200, 100), ('乙', 200, 120), ('丙', 100, 100), ('丁', 100, 120)])
    assert pb.reading_order(chars, 300, 300, 'vertical') == '甲乙丙丁'


def test_reading_order_horizontal():
    chars = _chars([('甲', 100, 100), ('乙', 120, 100), ('丙', 100, 120), ('丁', 120, 120)])
    assert pb.reading_order(chars, 300, 300, 'horizontal') == '甲乙丙丁'


def test_reading_order_excludes_header_footer():
    """页边带内页码式短列剔除；正文列保留。"""
    chars = _chars([('一二', 50, 5), ('甲', 200, 100), ('乙', 200, 120), ('三', 80, 290)])
    assert pb.reading_order(chars, 300, 300, 'vertical') == '甲乙'


def test_sequence_perfect():
    r = pb.sequence_eval('甲「乙」丙', '甲「乙」丙')
    assert r['per_class']['quote_open']['tp'] == 1
    assert r['per_class']['quote_close']['tp'] == 1
    assert r['overall']['fn'] == 0 and r['overall']['fp'] == 0


def test_sequence_missed_quote():
    r = pb.sequence_eval('甲「乙」丙', '甲乙丙')
    assert r['per_class']['quote_open']['fn'] == 1
    assert r['per_class']['quote_close']['fn'] == 1


def test_sequence_false_insertion():
    r = pb.sequence_eval('甲乙丙', '甲「乙」丙')
    assert r['per_class']['quote_open']['fp'] == 1


def test_sequence_type_error_confusion():
    r = pb.sequence_eval('甲，乙', '甲、乙')
    assert r['confusion'].get('comma>enumeration_comma') == 1
    assert r['per_class']['comma']['fn'] == 1
    assert r['per_class']['enumeration_comma']['fp'] == 1


def test_transpositions():
    assert pb._transpositions([(0, 0), (1, 1)]) == 0
    assert pb._transpositions([(0, 2), (1, 1), (2, 0)]) == 3


def test_sequence_vertical_form_normalization():
    r = pb.sequence_eval('甲「乙」丙', '甲﹁乙﹂丙')
    assert r['per_class']['quote_open']['tp'] == 1
    assert r['per_class']['quote_close']['tp'] == 1


def test_sequence_empty_text():
    r = pb.sequence_eval('', '')
    assert r['overall'] == dict(tp=0, fp=0, fn=0, precision=0.0, recall=0.0)
    assert r['order_swaps'] == 0


def test_sequence_main_end_to_end():
    """横排合成 PDF：gold 转录与产物一致 -> 引号 TP。"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, 'o.pdf'); d = fitz.open(); pg = d.new_page(width=300, height=200)
        pg.insert_text((10, 50), '甲「乙」丙', fontname='china-s', fontsize=12)
        d.save(pdf)
        gp = os.path.join(tmp, 'g.json')
        json.dump([{'book': 'wz7', 'page': 1, 'axis': 'horizontal', 'text': '甲「乙」丙'}],
                  open(gp, 'w', encoding='utf-8'), ensure_ascii=False)
        cp = os.path.join(tmp, 'c.json'); json.dump({}, open(cp, 'w', encoding='utf-8'))
        lp = os.path.join(tmp, 'l.json'); json.dump({}, open(lp, 'w', encoding='utf-8'))
        out = os.path.join(tmp, 'o.json')
        assert pb.main(['--mode', 'sequence', '--gold', gp, '--pdf', pdf, '--coords', cp, '--lines', lp,
                        '--book', 'wz7', '--out', out]) == 0
        r = json.load(open(out, encoding='utf-8'))
        assert r['mode'] == 'sequence'
        assert r['per_class']['quote_open']['tp'] == 1


# ===================== t142 修复单测 =====================
def test_identical_text_end_punct():
    """匹配块到达串尾：串尾标点也要配对（补 len(anchor)->len(anchor) 映射）。"""
    r = pb.sequence_eval('甲乙」', '甲乙」')
    assert r['per_class']['quote_close']['tp'] == 1
    assert r['per_class']['quote_close']['fn'] == 0


def test_vertical_page_number_column_excluded():
    """左右边带 8% 且整列为纯中文页码 -> 排除。"""
    chars = _chars([('一二三', 290, 100), ('甲', 200, 100), ('乙', 200, 120)])
    # 一二三 在右边缘（x=290/300），整列纯数字 -> 排；正文列保留
    assert pb.reading_order(chars, 300, 300, 'vertical') == '甲乙'


def test_vertical_header_like_column_excluded():
    """通用页眉模式（第X回，长度 <=6）在页边带内整列排除（书无关）。"""
    chars = _chars([('第一回', 290, 100), ('甲', 200, 100), ('乙', 200, 120)])
    assert pb.reading_order(chars, 300, 300, 'vertical') == '甲乙'


def test_book_specific_header_not_special_cased():
    """无通用家具特征的短列（如书名）不得因书名正则被剔除（书无关）。"""
    chars = _chars([('金瓶梅', 10, 100), ('甲', 200, 100), ('乙', 200, 120)])
    assert '金瓶梅' in pb.reading_order(chars, 300, 300, 'vertical')


def test_roman_page_number_excluded():
    """页边带内罗马数字页码（xii）剔除。"""
    chars = _chars([('xii', 290, 100), ('甲', 200, 100), ('乙', 200, 120)])
    assert pb.reading_order(chars, 300, 300, 'vertical') == '甲乙'


def test_body_column_in_band_not_removed():
    """正文长列（>6 字）即使中心在边带内也不得误剔。"""
    body = '甲乙丙丁戊己庚辛壬癸'
    chars = _chars([(body, 10, 100), ('辛', 200, 100), ('壬', 200, 120)])
    assert body in pb.reading_order(chars, 300, 300, 'vertical')


def test_order_swaps_same_gap():
    """同 gap 多 tokens 按序列配对：gold 「」 vs pred 」「 -> 1 次逆序。"""
    r = pb.sequence_eval('甲「」乙', '甲」「乙')
    assert r['order_swaps'] >= 1


def test_ab_diff_block_present():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, 'o.pdf'); d = fitz.open(); pg = d.new_page(width=300, height=200)
        pg.insert_text((10, 50), '甲，乙', fontname='china-s', fontsize=12); d.save(pdf)
        gp = os.path.join(tmp, 'g.json')
        json.dump([{'book': 'wz7', 'page': 1, 'axis': 'horizontal', 'text': '甲，乙'}],
                  open(gp, 'w', encoding='utf-8'), ensure_ascii=False)
        cp = os.path.join(tmp, 'c.json'); json.dump({}, open(cp, 'w', encoding='utf-8'))
        lp = os.path.join(tmp, 'l.json'); json.dump({}, open(lp, 'w', encoding='utf-8'))
        out = os.path.join(tmp, 'o.json')
        assert pb.main(['--mode', 'sequence', '--gold', gp, '--pdf', pdf, '--coords', cp, '--lines', lp,
                        '--book', 'wz7', '--out', out]) == 0
        r = json.load(open(out, encoding='utf-8'))
        assert 'ab_diff' in r and r['ab_diff']['page_sets_differ'] is True


# t144：类型错计数（gold 类只 1 FN；pred 类 1 FP；gold 类不得再计 FP）
def test_type_mismatch_fp_fn_counts():
    r = pb.sequence_eval('甲，乙', '甲。乙')
    assert r['per_class']['comma']['fp'] == 0
    assert r['per_class']['comma']['fn'] == 1
    assert r['per_class']['period']['fp'] == 1
    assert r['confusion'].get('comma>period') == 1
