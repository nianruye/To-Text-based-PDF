#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_ocr_orientation.py — OCR 方向分类参数(useDocOrientationClassify)对比试验。

背景（实测，见 spec/vertical/06_derot.md）：
  wz6 p159 源书是竖排页（版框内 4 列小字），但 OCR 服务把整页当**横排**识别，返回的坐标落在
  「页逆时针转 90°」的坐标系里 —— 行框 1833x47px（横看：竖排正文列必纵长，高/宽 ≈ 20），
  页宽方向的值最大 2411px 远超页宽 1191px（= 2x595.3pt）。后果：6 行全部过不了 is_body_col 被丢弃，
  该页整页空白。渲染端已用 derot_rows 数据驱动还原（不硬编码页号），属**事后修补**。
  官方 API 另有**源头根治**参数：optionalPayload 的 useDocOrientationClassify
  （官方文档："automatically identify and correct images rotated by 0°, 90°, 180°, or 270°"）。
  本脚本对同一页分别以 true/false 提交，对比返回的 rec_polys，判定该参数是否真能消除旋转坐标系。

用法（一条命令，token 就绪即用；WSL 重启会清空 /tmp，需重新放 token）：
  echo '<API_TOKEN>' > /tmp/paddle_token
  /usr/bin/python3 src/tools/test_ocr_orientation.py
  /usr/bin/python3 src/tools/test_ocr_orientation.py --pages 159,4 --dpi 200 --json /tmp/orient.json
  /usr/bin/python3 src/tools/test_ocr_orientation.py --render-only     # 无 token 也能跑：只渲染 PNG 并打印页几何

判据（竖排页，阈值与 build_vert.py §1.97 的触发判据同口径）：
  · 横看行     —— 行框宽 > 300px 且 宽 > 2.5x高：正常竖排页的长行必纵长，横看行 = 坐标系被转了 90°
  · 坐标越界   —— 页宽方向最大值 > 提交图页宽 px：说明返回坐标不是「提交图坐标系」
  · 行框高/宽比 h/w 中位：竖排正文列应远大于 1，横看行远小于 1
结论：两档参数各页统计并列打印；true 档「横看行 0 且不越界」= 参数有效（可在 OCR 侧根治）。

退出码：0 = 试验完成（结论见 stdout）；2 = 缺 token（本地文件未就绪）。
"""
import argparse
import json
import os
import sys
import time

import fitz  # PyMuPDF
import requests

TOKEN_FILE = "/tmp/paddle_token"
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
MODEL = "PaddleOCR-VL-1.6"
DEF_SRC_PDF = "source_pdf/wz6.pdf"
DEF_PAGES = "159"
HZ_W_MIN = 300.0      # 「长行」判据: 行框宽下限 px(同 build_vert §1.97)
HZ_RATIO = 2.5        # 「横看」判据: 宽 > 2.5x高
HZ_MIN_ROWS = 3       # build_vert 的触发条件: 横看行 >= 3 条


def render_page(src_pdf, page_no, dpi, outdir):
    """源 PDF 指定页(1-based)渲染 PNG。返回 (png 路径, 页宽 px, 页高 px, 页宽 pt, 页高 pt)。
    坐标口径: API 返回的 rec_polys 与**提交图**同像素空间(px), 页宽 px = pt x dpi/72。"""
    doc = fitz.open(src_pdf)
    if not (1 <= page_no <= doc.page_count):
        raise SystemExit("[错误] 页码 %d 超出源 PDF 页数 %d" % (page_no, doc.page_count))
    page = doc[page_no - 1]
    pix = page.get_pixmap(dpi=dpi)
    os.makedirs(outdir, exist_ok=True)
    png = os.path.join(outdir, "wz6_p%03d_%ddpi.png" % (page_no, dpi))
    pix.save(png)
    w_pt, h_pt = page.rect.width, page.rect.height
    doc.close()
    return png, pix.width, pix.height, w_pt, h_pt


def submit(png_path, orient_flag, token):
    """提交单张 PNG 到 PaddleOCR-VL spotting 接口, 返回 (rec_texts, rec_polys)。
    orient_flag: useDocOrientationClassify 取值(True/False) —— 唯一变化量, 其余载荷与
    src/ocr/run_spotting_ocr.py 一致(spotting 行级: useLayoutDetection=False + promptLabel=spotting)。"""
    payload = {
        "model": MODEL,
        "optionalPayload": json.dumps({
            "useLayoutDetection": False,          # spotting 行级: 取 rec_texts + rec_polys
            "promptLabel": "spotting",
            "temperature": 0,
            "useDocOrientationClassify": bool(orient_flag),
        }),
    }
    headers = {"Authorization": "bearer " + token}
    with open(png_path, "rb") as f:
        r = requests.post(JOB_URL, headers=headers, data=payload, files={"file": f})
    r.raise_for_status()
    job_id = r.json()["data"]["jobId"]
    while True:
        rr = requests.get(JOB_URL + "/" + job_id, headers=headers)
        rr.raise_for_status()
        state = rr.json()["data"]["state"]
        if state == "done":
            jsonl_url = rr.json()["data"]["resultUrl"]["jsonUrl"]
            break
        if state == "failed":
            raise RuntimeError("OCR 失败: " + rr.json()["data"].get("errorMsg", "unknown"))
        time.sleep(3)
    rr = requests.get(jsonl_url)
    rr.raise_for_status()
    texts, polys = [], []
    for line in rr.text.strip().split("\n"):
        if not line.strip():
            continue
        result = json.loads(line)["result"]
        for lpr in result.get("layoutParsingResults", []):
            pr = lpr.get("prunedResult", {})
            sr = pr.get("spotting_res") or lpr.get("spotting_res") or {}
            for i, t in enumerate(sr.get("rec_texts", [])):
                texts.append(t)
                polys.append(sr["rec_polys"][i] if i < len(sr.get("rec_polys", [])) else None)
    return texts, polys


def poly_stats(texts, polys, page_w_px):
    """返回 (行数, 横看行数, 长行数, 越界行数, 最大 x, 高/宽比中位)。polys 为 4 点框(px)。"""
    rows = []
    for t, p in zip(texts, polys):
        if not p or len(p) < 4:
            continue
        xs = [q[0] for q in p]
        ys = [q[1] for q in p]
        rows.append((max(xs) - min(xs), max(ys) - min(ys), max(xs), t))
    lng = [r for r in rows if r[0] > HZ_W_MIN]
    hz = [r for r in lng if r[0] > HZ_RATIO * max(1.0, r[1])]
    over = [r for r in rows if r[2] > page_w_px]
    ratios = sorted(r[1] / r[0] for r in lng if r[0] > 0)
    return {
        "n": len(rows), "n_long": len(lng), "n_hz": len(hz), "n_over": len(over),
        "max_x": round(max((r[2] for r in rows), default=0.0), 1),
        "hw_med": round(ratios[len(ratios) // 2], 3) if ratios else None,
        "long_text_max": max((len(r[3]) for r in lng), default=0),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-pdf", default=DEF_SRC_PDF)
    ap.add_argument("--pages", default=DEF_PAGES, help="页号, 逗号分隔(1-based); 默认 159(旋转页) + 建议加一页正常页对照")
    ap.add_argument("--dpi", type=int, default=200, help="渲染 dpi(坐标口径 = 提交图 px)")
    ap.add_argument("--outdir", default="/tmp/vert_orient", help="PNG 输出目录")
    ap.add_argument("--render-only", action="store_true", help="只渲染 PNG 并打印页几何(无 token 时可跑)")
    ap.add_argument("--json", default="", help="试验结果落盘 json")
    a = ap.parse_args()
    pages = [int(x) for x in a.pages.replace("，", ",").split(",") if x.strip()]

    if a.render_only:
        print("[render-only] 源 %s -> %s dpi=%d (坐标口径 = 提交图 px)" % (a.src_pdf, a.outdir, a.dpi))
        for pg in pages:
            png, w_px, h_px, w_pt, h_pt = render_page(a.src_pdf, pg, a.dpi, a.outdir)
            print("  p%-4d %s  %dx%d px  (%.1f x %.1f pt)" % (pg, png, w_px, h_px, w_pt, h_pt))
        print("[render-only] 完成（未提交 API）。token 就绪后去掉 --render-only 跑对比试验。")
        sys.exit(0)

    if not os.path.exists(TOKEN_FILE):
        print("[错误] 缺 %s（PaddleOCR API token）。WSL 重启会清空 /tmp。" % TOKEN_FILE)
        print("       放好 token:  echo '<API_TOKEN>' > %s" % TOKEN_FILE)
        print("       无 token 时可先跑: /usr/bin/python3 %s --render-only" % sys.argv[0])
        sys.exit(2)
    token = open(TOKEN_FILE).read().strip()

    res = {"src_pdf": a.src_pdf, "dpi": a.dpi, "pages": {}}
    for pg in pages:
        png, w_px, h_px, w_pt, h_pt = render_page(a.src_pdf, pg, a.dpi, a.outdir)
        print("\n===== p%d  %s  %dx%d px (%.1f x %.1f pt) =====" % (pg, png, w_px, h_px, w_pt, h_pt))
        entry = {}
        for flag in (False, True):
            t0 = time.time()
            try:
                texts, polys = submit(png, flag, token)
                st = poly_stats(texts, polys, w_px)
            except Exception as e:
                print("  useDocOrientationClassify=%-5s -> 提交失败: %s" % (str(flag), e))
                entry[str(flag)] = {"error": str(e)}
                continue
            st["secs"] = round(time.time() - t0, 1)
            st["texts"] = texts
            entry[str(flag)] = st
            print("  useDocOrientationClassify=%-5s 行%d 长行%d 横看行%d 越界行%d 最大x%.0f 高/宽比中位%s 最长长行%d字 (%.1fs)"
                  % (flag, st["n"], st["n_long"], st["n_hz"], st["n_over"], st["max_x"],
                     st["hw_med"], st["long_text_max"], st["secs"]))
            for t in texts[:4]:
                print("        %s" % t[:60].replace("\n", "\\n"))
        f, t_ = entry.get("False"), entry.get("True")
        if f and t_ and "error" not in f and "error" not in t_:
            rot_f = f["n_hz"] >= HZ_MIN_ROWS and f["n_over"] > 0
            fix_t = t_["n_hz"] == 0 and t_["n_over"] == 0
            if not rot_f:
                verdict = ("本页 false 档未复现旋转(%d 横看行/越界 %d 行) —— 该页不是旋转页, 换页或对比文本差异"
                           % (f["n_hz"], f["n_over"]))
            elif fix_t:
                verdict = ("参数有效: false 档复现旋转坐标系(%d 横看行/越界 %d 行), true 档已消除"
                           % (f["n_hz"], f["n_over"]))
            else:
                verdict = ("参数未消除旋转: true 档仍有 %d 横看行 / %d 越界行" % (t_["n_hz"], t_["n_over"]))
            entry["verdict"] = verdict
            print("  [结论] %s" % verdict)
        res["pages"][str(pg)] = entry

    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\n结果 -> %s" % a.json)
    sys.exit(0)


if __name__ == "__main__":
    main()
