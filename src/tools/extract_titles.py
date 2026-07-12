#!/usr/bin/env python3
"""从 OCR 版面分析数据提取标题文本集合。
输入: layout 版 lines + labels
输出: ocr_titles.json (按页的标题文本列表)
"""
import json, sys

def extract_titles(lines_file, labels_file, out_file):
    lines = json.load(open(lines_file))
    labels = json.load(open(labels_file))

    titles_by_page = {}
    total = 0
    for pg in sorted(labels.keys(), key=int):
        page_titles = []
        lbls = labels.get(pg, [])
        txts = lines.get(pg, [])
        for i, lbl in enumerate(lbls):
            if 'title' in lbl and i < len(txts):
                page_titles.append(txts[i])
                total += 1
        titles_by_page[pg] = page_titles

    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(titles_by_page, f, ensure_ascii=False, indent=2)

    print(f'{out_file}: {total} titles across {len(titles_by_page)} pages')
    # 打印所有标题
    for pg, titles in titles_by_page.items():
        for t in titles:
            print(f'  key={pg}: {t[:60]}')

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('用法: extract_titles.py <lines_file> <labels_file> <out_file>')
        sys.exit(1)
    extract_titles(sys.argv[1], sys.argv[2], sys.argv[3])