#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_geom.py — 版面还原验证 harness。
逐页量「输出 PDF」与「源(OCR spotting coords 为准)」的 4 项 1:1 指标:
  ① 页数是否 1:1
  ② 每页正文块高 (out vs src) 相对误差
  ③ 每页正文行数 (out vs src)
  ④ 每页正文相邻行 pitch 中位 (out vs src) 相对误差
另测输出页的空白/溢出:
  · 空白: 输出正文块底 明显高于 源块底 (内容排不满 → 页底空白)
  · 溢出: 输出正文块底 越过 源块底 + 阈 (内容超版心)

判据(默认): 抽样页 行数 100% 相等、页高误差 <5%、pitch 误差 <3% → 通过。

用法:
  python3 verify_geom.py <out.pdf> <src_spotting_coords.json> [src_spotting_lines.json] [--src-pdf wz1.pdf] [--dpi 200] [--sample N] [--json 报告.json]

指标口径对 src / out 完全对称:同一套「正文行」过滤(去页眉页码带 + 行高≈页中位)。
输出 PDF 用 bbox 几何(不依赖文字可复制),CJK 字体无 ToUnicode 也能量。
"""
import sys, json, statistics, argparse, re
import fitz  # PyMuPDF

MARK_RE = re.compile(r'GMPG(\d+)ZZ')


def _median(xs):
    return statistics.median(xs) if xs else 0.0


def _content_extent(lines, page_h, page_w):
    """内容纵向占位:排除页眉带(<4%)、页码(底部窄短行)后,首个文本行顶 y 与末个文本行底 y。
    这是「填充/空白/溢出」的直接信号——不区分正文/脚注,只看内容占了多高。"""
    L = [l for l in lines if 0.02 * page_h < l[2] < 0.98 * page_h]
    # 排除页码:很靠底(>92%)且很窄(<15% 页宽)的短行
    L = [l for l in L if not (l[2] > 0.92 * page_h and (l[5] - l[4]) < 0.15 * page_w)]
    if not L:
        return 0.0, 0.0
    return min(l[0] for l in L), max(l[1] for l in L)


def _body_lines(lines, page_h):
    """lines: [(y_top,y_bot,y_center,height,x_left,x_right), ...] in pt.
    return (body_sorted_by_y, pitch_pt, block_h_pt, top_y, bot_y, n).
    正文行 = y_center 在 [6%,90%] 页高内(去页眉/页码) + 行高在页中位 0.6~1.6× 内。"""
    cand = [l for l in lines if 0.06 * page_h < l[2] < 0.90 * page_h]
    if len(cand) < 3:
        return [], 0.0, 0.0, 0.0, 0.0, len(cand)
    med_h = _median([l[3] for l in cand])
    body = [l for l in cand if 0.6 * med_h <= l[3] <= 1.6 * med_h]
    if len(body) < 2:
        body = cand
    body.sort(key=lambda l: l[2])
    diffs = [b[2] - a[2] for a, b in zip(body, body[1:]) if b[2] - a[2] > 1.0]
    # 去段落/小标题偶发大间距:仅保留 <= 1.8× 原始中位 的相邻差,再取中位 = 主行距
    if diffs:
        m0 = _median(diffs)
        pitch = _median([d for d in diffs if d <= 1.8 * m0]) or m0
    else:
        pitch = 0.0
    top_y = min(l[0] for l in body)
    bot_y = max(l[1] for l in body)
    return body, pitch, bot_y - top_y, top_y, bot_y, len(body)


def src_pages(coords, lines, dpi):
    """从 spotting coords 提取每页正文几何(px→pt)。返回 {key: metrics}。"""
    k2pt = 72.0 / dpi
    out = {}
    for key in sorted(coords, key=lambda k: int(k)):
        polys = coords[key]
        txts = lines.get(key, []) if lines else [""] * len(polys)
        page_h = None  # 源页高从 poly 最大 y 估(与 out 页高比对时用真实 PDF 高覆盖)
        L = []
        maxy = 0.0
        for i, poly in enumerate(polys):
            if not poly:
                continue
            t = (txts[i] if i < len(txts) else "").strip()
            if not t:
                continue
            ys = [p[1] for p in poly]; xs = [p[0] for p in poly]
            yt, yb = min(ys) * k2pt, max(ys) * k2pt
            L.append((yt, yb, (yt + yb) / 2, yb - yt, min(xs) * k2pt, max(xs) * k2pt))
            maxy = max(maxy, max(ys) * k2pt)
        out[key] = {"lines": L, "maxy_pt": maxy}
    return out


def out_pages(pdf_path):
    """从输出 PDF 每页提取行级 bbox(pt) + 源页标记(GMPG<key>ZZ,若 VERIFY_MARK 渲染)。"""
    doc = fitz.open(pdf_path)
    pages = []
    for pg in doc:
        R = pg.rect
        L = []
        d = pg.get_text("dict")
        for blk in d.get("blocks", []):
            for ln in blk.get("lines", []):
                x0, y0, x1, y1 = ln["bbox"]
                if y1 - y0 <= 0.5:
                    continue
                L.append((y0, y1, (y0 + y1) / 2, y1 - y0, x0, x1))
        m = MARK_RE.search(pg.get_text("text"))
        pages.append({"lines": L, "page_h": R.height, "page_w": R.width,
                      "mark": int(m.group(1)) if m else None})
    doc.close()
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_pdf")
    ap.add_argument("src_coords")
    ap.add_argument("src_lines", nargs="?", default="")
    ap.add_argument("--src-pdf", default="")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--sample", type=int, default=0, help="只抽前 N 页(0=全书)")
    ap.add_argument("--json", default="")
    ap.add_argument("--tol-height", type=float, default=0.05)
    ap.add_argument("--tol-pitch", type=float, default=0.03)
    a = ap.parse_args()

    coords = json.load(open(a.src_coords, encoding="utf-8"))
    lines = json.load(open(a.src_lines, encoding="utf-8")) if a.src_lines else {}
    src = src_pages(coords, lines, a.dpi)
    out = out_pages(a.out_pdf)

    src_keys = sorted(src, key=lambda k: int(k))
    n_src, n_out = len(src_keys), len(out)
    print(f"页数: 源 OCR {n_src} 页  |  输出 PDF {n_out} 页  |  {'✓ 1:1' if n_src == n_out else '✗ 不一致'}")

    # 对齐:优先用源页标记(GMPG<key>)把输出物理页归组到源页;无标记则退回按序号 1:1
    marked = [p for p in out if p["mark"] is not None]
    use_mark = len(marked) >= 0.5 * len(out) and len(marked) > 0
    out_by_key = {}
    if use_mark:
        for p in out:
            if p["mark"] is not None:
                out_by_key.setdefault(p["mark"], []).append(p)
        print(f"对齐: 源页标记 (GMPG),{len(out_by_key)} 源页 → {len(out)} 物理页;"
              f"溢出成多页的源页 {sum(1 for v in out_by_key.values() if len(v) > 1)} 个")
    else:
        for i, p in enumerate(out):
            if i < n_src:
                out_by_key[int(src_keys[i])] = [p]
        print("对齐: 按序号 1:1 (输出未含 GMPG 标记,建议用 VERIFY_MARK=1 重渲以精确对齐)")

    keys_iter = src_keys[:a.sample] if a.sample else src_keys
    N = len(keys_iter)

    def combined_body(pgs, ph):
        """一源页的多张物理页:合并正文行数 + 行距(各页内相邻差汇总取中位)。"""
        n_tot, diffs = 0, []
        for op in pgs:
            b, _, _, _, _, n = _body_lines(op["lines"], ph)
            n_tot += n
            b.sort(key=lambda l: l[2])
            diffs += [y - x for (x, y) in ((a2[2], b2[2]) for a2, b2 in zip(b, b[1:])) if y - x > 1.0]
        if diffs:
            m0 = _median(diffs); pitch = _median([d for d in diffs if d <= 1.8 * m0]) or m0
        else:
            pitch = 0.0
        return n_tot, pitch

    rows = []
    for key in keys_iter:
        ik = int(key)
        og = out_by_key.get(ik, [])
        if not og:
            rows.append({"key": key, "page": ik + 1, "missing": True, "comparable": False,
                         "out_pages": 0, "n_eq": False, "h_err": None, "p_err": None,
                         "bot_gap": None, "blank": False, "overflow": False})
            continue
        n_out_pages = len(og)
        ph, pw = og[0]["page_h"], og[0]["page_w"]
        sb, sp, sh, st, sbot, sn = _body_lines(src[key]["lines"], ph)
        s_top, s_bot = _content_extent(src[key]["lines"], ph, pw)
        comparable = sn >= 8 and 10.0 <= sp <= 45.0

        if n_out_pages == 1:
            ob, opitch, oh, ot, obot, on = _body_lines(og[0]["lines"], ph)
            o_top, o_bot = _content_extent(og[0]["lines"], ph, pw)
            h_err = abs(oh - sh) / sh if sh > 0 else None
            bot_gap = (s_bot - o_bot) / ph if (s_bot > 0 and o_bot > 0) else None
            blank = bot_gap is not None and bot_gap > 0.08
            overflow = (o_bot > 0 and s_bot > 0 and o_bot > s_bot + 0.03 * ph) or (o_bot > 0.97 * ph)
        else:
            # 源页溢成多张物理页 = 溢出(版面还原失败:应 1 页)。行数/pitch 用合并值,页高/占位不计。
            on, opitch = combined_body(og, ph)
            h_err = None; bot_gap = None; blank = False; overflow = True
            oh = None; o_bot = None
        p_err = abs(opitch - sp) / sp if sp > 0 else None
        rows.append({
            "key": key, "page": ik + 1, "out_pages": n_out_pages, "missing": False,
            "src_n": sn, "out_n": on, "n_eq": sn == on,
            "src_h": round(sh, 1), "out_h": None if oh is None else round(oh, 1),
            "h_err": None if h_err is None else round(h_err, 3),
            "src_pitch": round(sp, 2), "out_pitch": round(opitch, 2),
            "p_err": None if p_err is None else round(p_err, 3),
            "s_bot": round(s_bot, 1), "o_bot": None if o_bot is None else round(o_bot, 1),
            "bot_gap": None if bot_gap is None else round(bot_gap, 3),
            "blank": blank, "overflow": overflow, "comparable": comparable,
        })

    dense = [r for r in rows if r["comparable"]]
    def pct(pred, pool):
        pool = [r for r in pool if pred(r) is not None]
        if not pool: return 0.0, 0
        ok = sum(1 for r in pool if pred(r))
        return ok / len(pool) * 100, len(pool)

    n_eq_pct, _ = pct(lambda r: r["n_eq"], dense)
    h_ok_pct, h_pool = pct(lambda r: None if r["h_err"] is None else r["h_err"] < a.tol_height, dense)
    p_ok_pct, p_pool = pct(lambda r: None if r["p_err"] is None else r["p_err"] < a.tol_pitch, dense)
    fill_ok_pct, fill_pool = pct(lambda r: None if r["bot_gap"] is None else abs(r["bot_gap"]) < 0.08, dense)
    blank_n = sum(1 for r in dense if r["blank"])
    split_n = sum(1 for r in rows if r.get("out_pages", 1) > 1)   # 溢成多物理页的源页(全量)
    over_n = sum(1 for r in dense if r["overflow"])
    miss_n = sum(1 for r in rows if r.get("missing"))

    print(f"\n== 聚合(可比正文页 {len(dense)}/{N};排除分隔/图/标题/扉页 {N-len(dense)}) ==")
    print(f"  行数 1:1 相等   : {n_eq_pct:.1f}%")
    print(f"  页高误差 <{a.tol_height:.0%}   : {h_ok_pct:.1f}%  (样本 {h_pool},排除溢出分页)")
    print(f"  pitch 误差 <{a.tol_pitch:.0%}  : {p_ok_pct:.1f}%  (样本 {p_pool})")
    print(f"  底部占位 <8% 偏差: {fill_ok_pct:.1f}%   空白页 {blank_n}  溢出页(占位) {over_n}")
    print(f"  ▶ 溢成多物理页的源页(全量): {split_n}   缺失页: {miss_n}")
    hs = [r['h_err'] for r in dense if r['h_err'] is not None]
    ps = [r['p_err'] for r in dense if r['p_err'] is not None]
    bs = [r['bot_gap'] for r in dense if r['bot_gap'] is not None]
    if dense:
        print(f"  中位: 页高误差 {_median(hs):.1%} | pitch 误差 {_median(ps):.1%} | "
              f"底部占位偏差 {_median(bs):+.1%}" if hs and ps and bs else "  (可比样本不足)")

    worst = sorted([r for r in dense if r["bot_gap"] is not None],
                   key=lambda r: -abs(r["bot_gap"]))[:12]
    print("\n== 底部占位偏差最大的 12 页(可比正文页;+空白 −溢出) ==")
    print("  page key  src_n out_n op  s_bot  o_bot  gap%   src_p out_p p_err  flags")
    for r in worst:
        fl = ("空白" if r["blank"] else "") + ("溢出" if r["overflow"] else "")
        print(f"  {r['page']:>4} {r['key']:>4}  {r['src_n']:>4} {r['out_n']:>4} {r.get('out_pages',1):>2}  "
              f"{r['s_bot']:>6} {str(r['o_bot']):>6}  {r['bot_gap']:+.2f}  "
              f"{r['src_pitch']:>5} {r['out_pitch']:>5} {str(r['p_err']):>5}  {fl}")

    # 溢出成多页的源页(版面还原硬失败),单列
    splits = sorted([r for r in rows if r.get("out_pages", 1) > 1], key=lambda r: -r["out_pages"])[:10]
    if splits:
        print("\n== 溢成多物理页的源页 top10(应为 1 页/源页) ==")
        print("  page key  out_pages src_n out_n src_p out_p")
        for r in splits:
            print(f"  {r['page']:>4} {r['key']:>4}   {r['out_pages']:>3}    "
                  f"{r.get('src_n','?'):>4} {r.get('out_n','?'):>4}  {r.get('src_pitch','?'):>5} {r.get('out_pitch','?'):>5}")

    if a.json:
        json.dump({"n_src": n_src, "n_out": n_out, "rows": rows,
                   "agg": {"n_eq_pct": n_eq_pct, "h_ok_pct": h_ok_pct, "p_ok_pct": p_ok_pct,
                           "fill_ok_pct": fill_ok_pct, "blank": blank_n, "overflow": over_n,
                           "split": split_n, "missing": miss_n, "comparable": len(dense)}},
                  open(a.json, "w"), ensure_ascii=False, indent=1)
        print(f"\n报告 → {a.json}")


if __name__ == "__main__":
    main()
