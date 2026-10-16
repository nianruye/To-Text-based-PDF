#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_vert.py — 竖排书还原验证 harness（对标横排 verify_geom.py）。

竖排管线的版式量（pitch/版心占位）与横排不可比：竖排的「行」是列、内容沿 y 方向推进，
源 OCR 的坐标还可能落在旋转坐标系里（见 spec/vertical/06_derot.md）。所以竖排验证换一套
与渲染机制无关、对源书 1:1 的四项硬指标：

  a) 页数 1:1       重建 PDF 页数 == OCR lines/coords 的 key 数（对齐按页序：build_vert 按 key 升序出页）
  b) 逐页字符量对照  重建每页提取文本 vs OCR lines 该页字数和；差 > --char-tol（默认 80 字）报警
  c) 越界检查        全书逐文本 span + 逐矢量图形 bbox 必须落在页内 [0,W]x[0,H]（容忍 --bbox-tol pt）
  d) 退出码          0=PASS / 1=FAIL + 汇总报告；--json 落盘逐页明细

已知预期差异页（OCR 幻觉页 / 水印页）**不硬编码页号**，按「该页 OCR 内容特征」自动识别：
  · OCR 噪声页   —— 水印/非中文页：非空白字符 >= --noise-min-char(默认 30) 且 CJK 占比 < --cjk-min(默认 0.5)
                    （实测 wz6 p231 = Anna's Archive 元数据页，重建后按设计无正文）
  · OCR 幻觉长行 —— 页内存在单条 OCR 行 >= --long-row(默认 80) 字：竖排单列满列也就 40 字上下，
                    这种框是多块合并/图例幻觉，build_vert 的 is_body_col 按设计排除（实测 wz6 p74）
也可以用 --expect-low 显式声明预期差异页（1-based 页号，逗号分隔），与自动识别取并集。

用法：
  /usr/bin/python3 src/test/verify_vert.py <out.pdf> <coords.json> <lines.json> \
      [--src-pdf source_pdf/wz6.pdf] [--char-tol 80] [--bbox-tol 0.5] [--expect-low 74,231] [--json 报告.json]

实测（wz6 全书 231 页）：
  /usr/bin/python3 src/test/verify_vert.py output/wz6/wz6_vert_full.pdf \
      data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json --src-pdf source_pdf/wz6.pdf
"""
import argparse
import collections
import json
import sys

import fitz  # PyMuPDF


def _nchar(t):
    """非空白字符数（与渲染端「字数」口径一致）"""
    return sum(1 for c in t if not c.isspace())


def _is_cjk(c):
    o = ord(c)
    return (0x3400 <= o <= 0x4DBF) or (0x4E00 <= o <= 0x9FFF) or (0xF900 <= o <= 0xFAFF)


def _cjk_ratio(t):
    """CJK 字符占非空白字符的比例（判「这页根本不是中文正文」：水印/英文元数据页）"""
    t2 = ''.join(c for c in t if not c.isspace())
    if not t2:
        return 0.0
    return sum(1 for c in t2 if _is_cjk(c)) / len(t2)


def ocr_pages(coords, lines):
    """OCR 侧每页统计。返回 (keys 按页序, {key: 统计})。
    key 集合取 coords/lines 并集（任一侧缺页都要暴露，不能只看单侧）。"""
    keys = sorted(set(coords) | set(lines), key=int)
    out = {}
    for k in keys:
        txts = [t for t in lines.get(k, []) if t and t.strip()]
        joined = ''.join(txts)
        out[k] = {
            "nchar": _nchar(joined),
            "nrow": len(txts),
            "max_row": max((_nchar(t) for t in txts), default=0),
            "cjk": _cjk_ratio(joined),
            "npoly": sum(1 for p in coords.get(k, []) if p),
        }
    return keys, out


def out_pages(pdf_path, bbox_tol):
    """重建 PDF 侧每页统计：提取文本字数 + 逐 span/矢量图形越界计数。
    越界口径：bbox 超出页 rect 的量 > bbox_tol(pt) 才算（PDF 坐标零头/描边半宽不误报）。"""
    doc = fitz.open(pdf_path)
    pages = []
    for pi, pg in enumerate(doc):
        R = pg.rect
        nchar = nspan = over_span = 0
        worst_span = 0.0
        samples = []
        # 用 "dict"(非 "rawdict"): rawdict 的 span 无 "text" 键(文字在 chars 里), 逐 span 取字会全空
        for blk in pg.get_text("dict").get("blocks", []):
            for ln in blk.get("lines", []):
                for sp in ln.get("spans", []):
                    nspan += 1
                    nchar += _nchar(sp.get("text", ""))
                    x0, y0, x1, y1 = sp["bbox"]
                    ov = max(-x0, -y0, x1 - R.width, y1 - R.height)
                    if ov > bbox_tol:
                        over_span += 1
                        worst_span = max(worst_span, ov)
                        if len(samples) < 4:
                            samples.append(("span", [round(v, 1) for v in sp["bbox"]],
                                            sp.get("text", "")[:16]))
        ndraw = over_draw = 0
        worst_draw = 0.0
        for d in pg.get_drawings():
            ndraw += 1
            x0, y0, x1, y1 = d["rect"]
            ov = max(-x0, -y0, x1 - R.width, y1 - R.height)
            if ov > bbox_tol:
                over_draw += 1
                worst_draw = max(worst_draw, ov)
                if len(samples) < 4:
                    samples.append(("draw", [round(v, 1) for v in d["rect"]], ""))
        pages.append({"page": pi + 1, "w": round(R.width, 2), "h": round(R.height, 2),
                      "nchar": nchar, "nspan": nspan, "ndraw": ndraw,
                      "over_span": over_span, "over_draw": over_draw,
                      "worst_over": round(max(worst_span, worst_draw), 2), "samples": samples})
    doc.close()
    return pages


def src_paper(pdf_path):
    """源 PDF 纸型：众数页幅(竖排依赖精确页高: 右缘 = 70 + om + textheight) + 非众数页清单 + 逐页页幅"""
    doc = fitz.open(pdf_path)
    per = [(round(p.rect.width, 2), round(p.rect.height, 2)) for p in doc]
    n = doc.page_count
    doc.close()
    if not per:
        return None, [], n
    modal, cnt = collections.Counter(per).most_common(1)[0]
    odd = [{"page": i + 1, "size": s} for i, s in enumerate(per) if s != modal]
    return {"size": modal, "count": cnt, "per_page": per}, odd, n


def expected_reason(o, a):
    """该页是否属「非版式还原目标页」（OCR 幻觉/水印）。返回原因串或 None。"""
    if o["nchar"] >= a.noise_min_char and o["cjk"] < a.cjk_min:
        return "OCR 噪声页(非中文: CJK 占比 %.2f)" % o["cjk"]
    if o["max_row"] >= a.long_row:
        return "OCR 幻觉长行页(单行 %d 字)" % o["max_row"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_pdf")
    ap.add_argument("src_coords")
    ap.add_argument("src_lines", nargs="?", default="")
    ap.add_argument("--src-pdf", default="", help="源 PDF：校验输出页幅 == 源书纸型(竖排依赖精确页高)")
    ap.add_argument("--char-tol", type=int, default=80, help="逐页字符量差异报警阈值(字)")
    ap.add_argument("--bbox-tol", type=float, default=0.5, help="越界容忍(pt)；超出量 > 此值才算越界")
    ap.add_argument("--cjk-min", type=float, default=0.5, help="OCR 噪声页判据: CJK 占比下限")
    ap.add_argument("--noise-min-char", type=int, default=30, help="OCR 噪声页判据: 最少非空白字符数")
    ap.add_argument("--long-row", type=int, default=80, help="OCR 幻觉长行判据: 单条 OCR 行最少字数")
    ap.add_argument("--expect-low", default="", help="显式声明预期差异页(1-based, 逗号分隔), 与自动识别取并集")
    ap.add_argument("--top", type=int, default=12, help="明细表列出差异最大的 N 页")
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    coords = json.load(open(a.src_coords, encoding="utf-8"))
    lines = json.load(open(a.src_lines, encoding="utf-8")) if a.src_lines else {}
    keys, src = ocr_pages(coords, lines)
    out = out_pages(a.out_pdf, a.bbox_tol)
    explicit = set()
    if a.expect_low.strip():
        explicit = {int(x) for x in a.expect_low.replace("，", ",").split(",") if x.strip()}

    # ---- a) 页数 1:1 ----
    n_src, n_out = len(keys), len(out)
    print(f"页数: 源 OCR {n_src} 页  |  输出 PDF {n_out} 页  |  {'✓ 1:1' if n_src == n_out else '✗ 不一致'}")

    # ---- b) 逐页字符量对照（按页序对齐） ----
    rows = []
    tot_out = tot_src = 0
    for i, pg in enumerate(out):
        k = keys[i] if i < n_src else None
        s = src.get(k, {"nchar": 0, "nrow": 0, "max_row": 0, "cjk": 0.0, "npoly": 0})
        tot_out += pg["nchar"]; tot_src += s["nchar"]
        why = expected_reason(s, a) if k is not None else None
        rows.append({
            "page": i + 1, "key": k, "out_n": pg["nchar"], "src_n": s["nchar"],
            "diff": abs(pg["nchar"] - s["nchar"]), "src_row": s["nrow"], "src_max_row": s["max_row"],
            "src_cjk": round(s["cjk"], 3), "src_poly": s["npoly"],
            "over_span": pg["over_span"], "over_draw": pg["over_draw"], "worst_over": pg["worst_over"],
            "samples": pg["samples"], "expected": why,
        })
    ratio = tot_out / tot_src * 100 if tot_src else 0.0
    print(f"字符量: 输出 {tot_out} / OCR {tot_src} = {ratio:.1f}%")

    big = [r for r in rows if r["diff"] > a.char_tol]
    bad_char = [r for r in big if r["page"] not in explicit and not r["expected"]]
    exp_char = [r for r in big if r["page"] in explicit or r["expected"]]
    for r in exp_char:
        why = r["expected"] or "命令行声明(--expect-low)"
        print(f"  [预期差异] p{r['page']} 输出 {r['out_n']} / OCR {r['src_n']} (差 {r['diff']}) — {why}")
    # 整页丢失：OCR 有内容而重建 0 字（硬失败，除非该页属预期差异页）
    lost = [r for r in rows if r["out_n"] == 0 and r["src_n"] >= 30
            and r["page"] not in explicit and not r["expected"]]
    print(f"  差异 > {a.char_tol} 字的页: {len(big)} 个（预期 {len(exp_char)} / 非预期 {len(bad_char)}）；"
          f"整页丢失(0 字)页: {len(lost)} 个")

    # ---- c) 越界检查 ----
    ov_pages = [r for r in rows if r["over_span"] or r["over_draw"]]
    n_ov_span = sum(r["over_span"] for r in rows)
    n_ov_draw = sum(r["over_draw"] for r in rows)
    print(f"越界: span {n_ov_span} 个 / 矢量图形 {n_ov_draw} 个（容忍 {a.bbox_tol:g}pt；"
          f"涉及 {len(ov_pages)} 页）")
    for r in ov_pages[:a.top]:
        print(f"  [越界] p{r['page']} span {r['over_span']} draw {r['over_draw']} 最深 {r['worst_over']}pt")
        for kind, bbox, txt in r["samples"][:2]:
            print(f"         {kind} bbox={bbox} {txt}")

    # ---- 页幅（可选：需 --src-pdf） ----
    paper = None
    if a.src_pdf:
        paper, odd, n_sp = src_paper(a.src_pdf)
        if paper:
            pw, ph = paper["size"]
            ow = out[0]["w"] if out else 0.0     # 输出全书统一纸型（竖排按单一纸型渲染）
            oh = out[0]["h"] if out else 0.0
            dw = abs(ow - pw) / pw if pw else 0.0
            dh = abs(oh - ph) / ph if ph else 0.0
            print(f"页幅: 源书众数 {pw}x{ph}pt（{paper['count']}/{n_sp} 页）  |  输出首页 {ow}x{oh}pt  "
                  f"|  相对差 {dw:.2%}/{dh:.2%}")
            # 逐页页幅比对(taskO): 混纸型书(同一册里多种开本)输出本就该逐页不同 —— 只比众数会把
            #   正确的逐页纸型判成失败(实测 wz7: 24 页里 8 页 922x1437 + 16 页 705x1084)。
            #   门限仍是 0.5%(与原有判据一致); 逐页最大相对差成为 FAIL 判据。
            per = paper.get("per_page") or []
            dw = dh = 0.0
            bad_pg = []
            for i, o in enumerate(out):
                if i >= len(per): break
                sw, sh = per[i]
                if not sw or not sh: continue
                if (sw, sh) != (pw, ph): continue      # 源书非众数页: 按既有契约(输出单纸型)不判
                _dw = abs(o["w"] - sw) / sw; _dh = abs(o["h"] - sh) / sh
                if max(_dw, _dh) > 0.005:
                    bad_pg.append((i + 1, sw, sh, o["w"], o["h"]))
                dw = max(dw, _dw); dh = max(dh, _dh)
            print(f"  逐页页幅(众数纸型页, 输出页 i vs 源页 i) 最大相对差 {dw:.2%}/{dh:.2%}"
                  + (f"; 不符 {len(bad_pg)} 页: "
                     + ", ".join("p%d 源%gx%g 输出%gx%g" % b for b in bad_pg[:6]) if bad_pg else "  ✓ 相符"))
            if odd:
                print(f"  源书非众数页幅 {len(odd)} 页（输出按源书逐页页幅渲染, 见上行逐页对账）: "
                      + ", ".join("p%d %sx%s" % (o["page"], o["size"][0], o["size"][1]) for o in odd[:6]))
    else:
        dw = dh = 0.0

    # ---- 明细表 ----
    top = sorted(rows, key=lambda r: -r["diff"])[:a.top]
    print(f"\n== 字符量差异最大的 {len(top)} 页 ==")
    print("  page key  out_n  src_n  diff  src行数 最长行 CJK占比  标记")
    for r in top:
        flag = "预期" if (r["page"] in explicit or r["expected"]) else ("超阈" if r["diff"] > a.char_tol else "")
        print(f"  {r['page']:>4} {str(r['key']):>4} {r['out_n']:>6} {r['src_n']:>6}  {r['diff']:>4}  "
              f"{r['src_row']:>5} {r['src_max_row']:>5}  {r['src_cjk']:>6.2f}  {flag}")

    if a.json:
        json.dump({"n_src": n_src, "n_out": n_out, "char_out": tot_out, "char_src": tot_src,
                   "paper": paper, "rows": rows,
                   "agg": {"big_diff_pages": len(big), "expected_diff_pages": len(exp_char),
                           "unexpected_diff_pages": len(bad_char), "lost_pages": len(lost),
                           "over_span": n_ov_span, "over_draw": n_ov_draw,
                           "over_pages": len(ov_pages)}},
                  open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n报告 → {a.json}")

    # ---- d) 退出码 ----
    fails = []
    if n_src != n_out:
        fails.append(f"页数不 1:1: 源 {n_src} vs 输出 {n_out}")
    if n_ov_span or n_ov_draw:
        fails.append(f"越界 {n_ov_span} span / {n_ov_draw} 图形（容忍 {a.bbox_tol:g}pt）")
    if bad_char:
        fails.append("非预期大幅缺字页 %d 个: %s"
                     % (len(bad_char), ",".join("p%d(差%d)" % (r["page"], r["diff"]) for r in bad_char[:8])))
    if lost:
        fails.append("整页丢失(0 字) %d 页: %s" % (len(lost), ",".join("p%d" % r["page"] for r in lost[:8])))
    if a.src_pdf and paper and max(dw, dh) > 0.005:
        fails.append(f"页幅(逐页 vs 源书)相对差超阈: 最大 {dw:.2%}/{dh:.2%}")
    if fails:
        print("\n== 退出码 FAIL ==")
        for f in fails:
            print(f"  [FAIL] {f}")
        sys.exit(1)
    print("\n== 退出码 PASS ==")
    sys.exit(0)


if __name__ == "__main__":
    main()
