#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 census_ring_digit.py 的圈码检出合并进 docs/vert_taskF_missed_fix.json

口径（taskH / battle1 P0-a）：
  · 保留任务E 的人工条目（dash 1 + ring 36；number 由源图裁片人工判读）；
  · **丢弃旧的 how=ring_digit 条目**，从本次普查结果整体重建（判据/测量口径统一，
    避免旧版 164 条与新检出混用两套几何）；
  · 每个普查命中 -> situation=1（数字已在 OCR 文本尾，渲染端把尾部数字 1:1 换成圈码占位）；
    若同页同列已有人工条目（bbox 四项差之和 < 3pt）-> 保留人工条目、跳过（number 优先）；
  · number > 50：Unicode 无标准圈码，渲染端走「○ + 小号数字」；仍登记以便统计。

用法：
  /usr/bin/python3 src/tools/merge_ring_digit.py            # 写回 docs/vert_taskF_missed_fix.json
  /usr/bin/python3 src/tools/merge_ring_digit.py --check    # 只打印差异，不写盘
  /usr/bin/python3 src/tools/merge_ring_digit.py --census tmp_vert/cj5/census_v2_dpi600.json --out /tmp/x.json
"""
import argparse
import json
import os
import shutil

FIX = 'docs/vert_taskF_missed_fix.json'
CENSUS = 'tmp_vert/cj5/ring_digit_census.json'
REPORT = 'tmp_vert/cj5/merge_report.json'


def bbox_dist(a, b):
    return sum(abs(float(x) - float(y)) for x, y in zip(a, b))


def circled_cp(n):
    if 1 <= n <= 20:
        return 0x2460 + n - 1
    if 21 <= n <= 35:
        return 0x3251 + n - 21
    if 36 <= n <= 50:
        return 0x32B1 + n - 36
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--census', default=CENSUS)
    ap.add_argument('--fix', default=FIX)
    ap.add_argument('--out', default='')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    census = json.load(open(args.census, encoding='utf-8'))
    old = json.load(open(args.fix, encoding='utf-8'))
    items = old.get('items') or []
    keep = [it for it in items if not (it.get('class') == 'ring' and it.get('how') == 'ring_digit')]
    manual_ring = [it for it in keep if it.get('class') == 'ring']
    n_old_digit = len(items) - len(keep)
    print('旧清单: %d 项（ring_digit %d / 保留 %d，其中人工 ring %d + dash %d）'
          % (len(items), n_old_digit, len(keep), len(manual_ring), len(keep) - len(manual_ring)))
    print('普查命中: %d 处 / %d 页' % (len(census), len(set(h['page'] for h in census))))

    new, skipped = [], []
    for h in census:
        hb = [h['x0'], h['y0'], h['x1'], h['y1']]
        dup = None
        for it in manual_ring:
            if int(it['page']) != int(h['page']):
                continue
            if bbox_dist(it['col'], hb) < 3.0:
                dup = it
                break
        if dup is not None:
            skipped.append(dict(page=h['page'], row=h['row'], num=h['num'],
                                manual=dup.get('number'), situation=dup.get('situation')))
            continue
        n = int(str(h['num']).translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        cp = circled_cp(n)
        new.append(dict(page=h['page'], col=[round(v, 1) for v in hb],
                        **{'class': 'ring'}, number=n, situation=1,
                        source_x=round(h['ax'] + h['w'] / 2.0, 1),
                        source_y=round(h['ay'] + h['h'] / 2.0, 1),
                        text=str(h['text'])[-16:], how='ring_digit',
                        measure=dict(w=h['w'], h=h['h'], hole=h['hole'], edge=h['edge'], ctr=h['ctr'],
                                     fill=h['fill'], ar=h['ar'], crit=h.get('crit', 'v2'),
                                     dpi=int(os.environ.get('VERT_RING_DPI') or 600)),
                        cp=('U+%04X' % cp) if cp else None))
    out_items = keep + new
    # 排序：page, x 从右到左（竖排列序），便于人工核对
    out_items.sort(key=lambda it: (int(it['page']), -float(it['col'][0])))
    out = dict(old)
    out['items'] = out_items
    out['ring_digit_merge'] = dict(
        source='census_ring_digit.py',  # 判据版本/参数见 census 输出头
        n_census=len(census), n_new=len(new), n_kept_manual=len(skipped),
        n_ring_total=sum(1 for it in out_items if it.get('class') == 'ring'),
        n_ring_gt50=sum(1 for it in out_items if it.get('class') == 'ring' and int(it.get('number') or 0) > 50),
        note='number 取自 OCR 文本尾数字；>50 无 Unicode 圈码，渲染端画 ○+小号数字')
    print('合并: 保留人工/占位 %d + 新增 ring_digit %d = %d 项（ring 共 %d / >50 共 %d）'
          % (len(keep), len(new), len(out_items), out['ring_digit_merge']['n_ring_total'],
             out['ring_digit_merge']['n_ring_gt50']))
    print('因人工条目覆盖而跳过: %d 处（number 一致: %s）'
          % (len(skipped), all(int(s['manual'] or 0) == int(s['num']) for s in skipped)))
    st = dict(n_census=len(census), n_new=len(new), n_skipped=len(skipped),
              skipped=skipped, n_ring_total=out['ring_digit_merge']['n_ring_total'])
    if args.check:
        print('(--check: 未写盘)')
        return 0
    if not args.out:
        bak = FIX + '.bak_ringdigit_v2'
        if not os.path.exists(bak):
            shutil.copy2(FIX, bak)
            print('备份 -> %s' % bak)
    dst = args.out or FIX
    json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(st, open(REPORT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('写入 %s；合并报告 -> %s' % (dst, REPORT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
