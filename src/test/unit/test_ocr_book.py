#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ocr_book 单测：页号记录 / raw→coords/lines（legacy 2×pt）/ manifest。"""
import json, os, sys, tempfile
import fitz

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'tools'))
import ocr_book as ob


def _mk_src(path, sizes):
    d = fitz.open()
    for w, h in sizes:
        d.new_page(width=w, height=h)
    d.save(path); d.close(); return path


def _raw_page(pw, ph, polys, texts):
    return dict(prunedResult=dict(width=pw, height=ph,
                                  spotting_res=dict(rec_polys=polys, rec_texts=texts)),
                markdown={'text': '', 'images': []})


def test_convert_raw_dir_two_pages_scale_and_order():
    with tempfile.TemporaryDirectory() as tmp:
        src = _mk_src(os.path.join(tmp, 'src.pdf'), [(300, 600), (300, 600)])
        os.makedirs(os.path.join(tmp, 'raw'))
        raw = dict(result=dict(layoutParsingResults=[
            _raw_page(500, 1000, [[[100, 100], [200, 100], [200, 150], [100, 150]]], ['甲']),
            _raw_page(500, 1000, [[[50, 50], [150, 50], [150, 90], [50, 90]]], ['乙']),
        ]))
        json.dump(raw, open(os.path.join(tmp, 'raw', 'spotting_000.json'), 'w'), ensure_ascii=False)
        jobs = {'spotting_000': dict(state='done', pages=[1, 0])}  # 全局页映射/顺序
        cp, lp = ob.convert_raw_dir(tmp, src, 'x', jobs)
        co = json.load(open(cp, encoding='utf-8'))
        ln = json.load(open(lp, encoding='utf-8'))
        # scale_x = 2*300/500 = 1.2; scale_y = 2*600/1000 = 1.2
        assert co['1'][0][0] == [120.0, 120.0]
        assert co['0'][0][0] == [60.0, 60.0]
        assert ln['1'] == ['甲'] and ln['0'] == ['乙']
        assert list(co) == ['1', '0']


def test_convert_raw_dir_without_jobs_infers_pages():
    with tempfile.TemporaryDirectory() as tmp:
        src = _mk_src(os.path.join(tmp, 'src.pdf'), [(300, 600), (300, 600)])
        os.makedirs(os.path.join(tmp, 'raw'))
        raw = dict(result=dict(layoutParsingResults=[
            _raw_page(500, 1000, [[[0, 0], [10, 0], [10, 10], [0, 10]]], ['A']),
            _raw_page(500, 1000, [[[0, 0], [10, 0], [10, 10], [0, 10]]], ['B']),
        ]))
        json.dump(raw, open(os.path.join(tmp, 'raw', 'spotting_000.json'), 'w'), ensure_ascii=False)
        cp, lp = ob.convert_raw_dir(tmp, src, 'x', {})
        assert sorted(json.load(open(cp, encoding='utf-8'))) == ['0', '1']


def test_write_manifest_and_split_pages():
    with tempfile.TemporaryDirectory() as tmp:
        src = _mk_src(os.path.join(tmp, 'src.pdf'), [(100, 100)] * 5)
        _, batches = ob.split_batches(src, 2, '2-5')  # 0-based 1..4 -> 2 batches
        assert len(batches) == 2
        man = ob.write_manifest(tmp, {'spotting_000': dict(state='done', jobId='j', pages=[1, 2])},
                                batches, 5)
        assert man['batches'][0]['pages'] == [1, 2]
        assert json.load(open(os.path.join(tmp, 'manifest.json')))['source_pages'] == 5


# ---- t175: JSONL（大 batch 服务返回多行 JSON） ----
def _raw_obj(pages):
    return dict(result=dict(layoutParsingResults=pages))


def _page(pw, ph, poly, text):
    return dict(prunedResult=dict(width=pw, height=ph,
                                  spotting_res=dict(rec_polys=[poly], rec_texts=[text])))


def test_convert_jsonl_objects_three_pages():
    with tempfile.TemporaryDirectory() as tmp:
        src = _mk_src(os.path.join(tmp, 'src.pdf'), [(300, 600)] * 8)
        os.makedirs(os.path.join(tmp, 'raw'))
        poly = [[10, 10], [110, 10], [110, 60], [10, 60]]
        objs = [_raw_obj([_page(500, 1000, poly, '甲'), _page(500, 1000, poly, '乙')]),
                _raw_obj([_page(500, 1000, poly, '丙')])]
        with open(os.path.join(tmp, 'raw', 'spotting_000.json'), 'w', encoding='utf-8') as f:
            for o in objs:
                f.write(json.dumps(o, ensure_ascii=False) + '\n')
        jobs = {'spotting_000': dict(state='done', pages=[5, 6, 7])}
        cp, lp = ob.convert_raw_dir(tmp, src, 'x', jobs)
        co = json.load(open(cp, encoding='utf-8')); ln = json.load(open(lp, encoding='utf-8'))
        assert list(co) == ['5', '6', '7']
        assert ln == {'5': ['甲'], '6': ['乙'], '7': ['丙']}
        # scale = 2*300/500 = 1.2
        assert co['5'][0][0] == [12.0, 12.0]
        assert co['7'][0][0] == [12.0, 12.0]


def test_single_json_and_jsonl_equivalent():
    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        src1 = _mk_src(os.path.join(t1, 'src.pdf'), [(300, 600)] * 8)
        src2 = _mk_src(os.path.join(t2, 'src.pdf'), [(300, 600)] * 8)
        poly = [[10, 10], [110, 10], [110, 60], [10, 60]]
        pages = [_page(500, 1000, poly, '甲'), _page(500, 1000, poly, '乙'),
                 _page(500, 1000, poly, '丙')]
        jobs = {'spotting_000': dict(state='done', pages=[5, 6, 7])}
        for tmp, jsonl in ((t1, False), (t2, True)):
            os.makedirs(os.path.join(tmp, 'raw'))
            p = os.path.join(tmp, 'raw', 'spotting_000.json')
            if jsonl:
                with open(p, 'w', encoding='utf-8') as f:
                    for chunk in (pages[:2], pages[2:]):
                        f.write(json.dumps(_raw_obj(chunk), ensure_ascii=False) + '\n')
            else:
                json.dump(_raw_obj(pages), open(p, 'w', encoding='utf-8'), ensure_ascii=False)
        c1, l1 = ob.convert_raw_dir(t1, src1, 'x', jobs)
        c2, l2 = ob.convert_raw_dir(t2, src2, 'x', jobs)
        assert json.load(open(c1)) == json.load(open(c2))
        assert json.load(open(l1)) == json.load(open(l2))
