#!/usr/bin/env python3
"""extract_page_numbers.py
精准裁切每页页码行(y94-100%)+ dpi400 高分辨率,单独 OCR 提取印刷页码。

为什么需要: 全页 spotting OCR 对页脚小字识别率仅 ~43%(水印竞争 + 字号小)。
精准裁切页码行后,页码占图片主体,识别率显著提升(但极淡页仍可能漏,需后处理插值)。

用法:
  python3 extract_page_numbers.py 输入.pdf 输出.json [--bottom 0.06] [--top 0.94] [--dpi 400] [--pages 0-29]

输出: {key(str): 页码(str)}  例 {"0":"50","7":"3","13":"2",...}
"""
import json, re, sys, time, os, requests, fitz

TOKEN_FILE = "/tmp/paddle_token"
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
MODEL = "PaddleOCR-VL-1.6"

INPUT_PDF = sys.argv[1] if len(sys.argv) > 1 else "/opt/test/优化前3.pdf"
OUT_JSON = sys.argv[2] if len(sys.argv) > 2 else "/opt/test/page_numbers3.json"
TOP_RATIO = 0.94    # 裁切起点(页码行 y≈98%, 水印 y≈100%, 排除正文)
BOTTOM_RATIO = 0.0  # 裁切终点偏移(0=到页底)
DPI = 400
PAGES = None
SPOTTING_LINES_FILE = ""
SPOTTING_COORDS_FILE = ""

i = 3
def _val(arg, idx):
    return arg.split("=", 1)[1] if "=" in arg else (sys.argv[idx+1], idx+1)[0]
while i < len(sys.argv):
    a = sys.argv[i]
    if a.startswith("--top"):
        v = a.split("=",1)[1] if "=" in a else sys.argv[i+1]; TOP_RATIO = float(v); i += 1 + (0 if "=" in a else 1); continue
    if a.startswith("--bottom"):
        v = a.split("=",1)[1] if "=" in a else sys.argv[i+1]; BOTTOM_RATIO = float(v); i += 1 + (0 if "=" in a else 1); continue
    if a.startswith("--dpi"):
        v = a.split("=",1)[1] if "=" in a else sys.argv[i+1]; DPI = int(v); i += 1 + (0 if "=" in a else 1); continue
    if a.startswith("--pages"):
        v = a.split("=",1)[1] if "=" in a else sys.argv[i+1]
        s, e = v.split("-"); PAGES = range(int(s), int(e)+1); i += 1 + (0 if "=" in a else 1); continue
    if a.startswith("--spotting-lines"):
        v = a.split("=",1)[1] if "=" in a else sys.argv[i+1]; SPOTTING_LINES_FILE = v; i += 1 + (0 if "=" in a else 1); continue
    if a.startswith("--spotting-coords"):
        v = a.split("=",1)[1] if "=" in a else sys.argv[i+1]; SPOTTING_COORDS_FILE = v; i += 1 + (0 if "=" in a else 1); continue
    i += 1

tok = open(TOKEN_FILE).read().strip()
HEADERS = {"Authorization": "bearer " + tok}
PAYLOAD = {"model": MODEL, "optionalPayload": json.dumps({
    "useLayoutDetection": False, "promptLabel": "spotting", "temperature": 0})}
WATERMARK = "学习理论"


def ocr_image(png_path, timeout_sec=60):
    """上传 → 轮询 → 返回纯文本行列表(去水印)。单页最多等 timeout_sec。"""
    with open(png_path, "rb") as f:
        r = requests.post(JOB_URL, headers=HEADERS, data=PAYLOAD, files={"file": f}, timeout=30)
    r.raise_for_status()
    job_id = r.json()["data"]["jobId"]
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        rr = requests.get(JOB_URL + "/" + job_id, headers=HEADERS, timeout=15)
        st = rr.json()["data"]["state"]
        if st == "done":
            url = rr.json()["data"]["resultUrl"]["jsonUrl"]; break
        if st == "failed":
            print(f"    [OCR failed]"); return []
        time.sleep(2)
    else:
        print(f"    [OCR timeout {timeout_sec}s]"); return []
    rr = requests.get(url, timeout=30); rr.raise_for_status()
    rows = []
    for line in rr.text.strip().split("\n"):
        line = line.strip()
        if not line: continue
        result = json.loads(line)["result"]
        lpr = result.get("layoutParsingResults", [])
        blocks = lpr[0].get("prunedResult", {}).get("parsing_res_list", []) if lpr else []
        for blk in blocks:
            sr = blk.get("spotting_res")
            if sr and sr.get("rec_texts"):
                rows.extend(sr["rec_texts"])
            else:
                for raw in blk.get("block_content", "").split("\n"):
                    if raw.strip(): rows.append(raw.strip())
    return rows


def pick_page_number(rows):
    """从行列表选页码: 排除水印后,纯 1-4 位数字(优先最末,即最底部)。"""
    cands = []
    for t in rows:
        t = t.strip()
        if not t or WATERMARK in t: continue
        if re.fullmatch(r'\d{1,4}', t):
            cands.append(t)
        elif re.fullmatch(r'[·•‧]?\s*\d{1,4}\s*[·•‧]?', t):
            m = re.search(r'\d{1,4}', t)
            if m: cands.append(m.group())
    return cands[-1] if cands else None, cands


def fit_and_fill(page_numbers_ocr, total_pages):
    """拟合页码公式并填充。容忍重复页(连续相同页码)、缺失页(OCR漏识别)、前言区噪声。
    算法:
      1. 检测重复页(连续相同页码)→ 标记为 dup
      2. 找正文起始:连续三点页码递增+1 → 丢弃之前散乱锚点(前言区噪声)
      3. 验证 offset 一致(用逻辑序号)
      4. 用逻辑序号填充正文区
    返回: (filled_dict, dup_keys_set, logic_offset) 或 (None, None, None)"""
    if len(page_numbers_ocr) < 2:
        print("    [拟合失败] 锚点太少(<2)")
        return None, None, None

    sorted_items = sorted(page_numbers_ocr.items(), key=lambda x: int(x[0]))
    keys = [int(k) for k, _ in sorted_items]
    nums = [int(v) for k, v in sorted_items]

    # 1. 检测重复页:连续(按key)页码相同 → 后者为 dup
    dup_keys = set()
    prev_pn = None
    for k, pn in sorted_items:
        if pn == prev_pn:
            dup_keys.add(int(k))
            print(f"    [重复页] key{k}={pn} (与前页相同,疑源PDF重复)")
        prev_pn = pn

    # 2. 找正文起始:连续三点页码递增+1(正文区页码必连续,前言区噪声散乱)
    content_start_idx = None
    for i in range(len(nums) - 2):
        if nums[i+1] == nums[i] + 1 and nums[i+2] == nums[i] + 2:
            content_start_idx = i
            break

    if content_start_idx is None:
        print("    [拟合失败] 找不到连续三点页码递增的正文起始")
        return None, None, None

    # 丢弃前言区噪声(正文起始之前的散乱锚点)
    if content_start_idx > 0:
        discarded_keys = keys[:content_start_idx]
        print(f"    [前言区噪声] 丢弃锚点 key{discarded_keys}(页码散乱非正文)")
        sorted_items = sorted_items[content_start_idx:]
        keys = keys[content_start_idx:]
        nums = nums[content_start_idx:]

    # 3. 正文区锚点(非dup)
    non_dup = [(int(k), int(v)) for k, v in sorted_items if int(k) not in dup_keys]
    start_key = non_dup[0][0]

    # 逻辑序号 = key - start_key - (key之前的重复页数)
    # 重复页消耗页码编号(后续压缩);缺失页(无锚点)不影响逻辑序号
    def logic_idx(key):
        return key - start_key - sum(1 for d in dup_keys if start_key <= d < key)

    # 4. 验证: 每个非dup锚点的 逻辑序号 + offset = 页码
    logic_offset = non_dup[0][1] - logic_idx(start_key)  # start_key 逻辑序号0
    for k, pn in non_dup:
        expected = logic_idx(k) + logic_offset
        if pn != expected:
            print(f"    [拟合失败] key{k} 页码={pn} 但预期={expected}(逻辑序号{logic_idx(k)}+offset{logic_offset})")
            return None, None, None

    print(f"    [拟合成功] 页码 = 逻辑序号 + {logic_offset}, 起始 key{start_key}={non_dup[0][1]}, {len(non_dup)} 有效锚点")
    if dup_keys:
        print(f"    [重复页标记] {sorted(dup_keys)} (输出时隐藏页码)")

    # 5. 填充: 遍历 start_key 到 total_pages
    filled = {}
    for key in range(start_key, total_pages):
        if key in dup_keys:
            continue  # 重复页不输出页码
        filled[str(key)] = str(logic_idx(key) + logic_offset)
    return filled, dup_keys, logic_offset


def extract_from_spotting(spotting_lines_file, spotting_coords_file):
    """从全页OCR缓存(spotting)提取每页底部页码锚点。
    规则:每页找 y最大(最底部)且为短数字行(·35·/40/·53·等,长度≤6)。
    返回: page_numbers dict"""
    import json, re
    lines = json.load(open(spotting_lines_file))
    coords = json.load(open(spotting_coords_file))
    page_numbers = {}
    print(f"从 spotting 缓存提取页码锚点: {spotting_lines_file}", flush=True)
    for key in sorted(lines.keys(), key=int):
        L = lines[key]; C = coords[key]
        cands = []
        for l, poly in zip(L, C):
            if not poly: continue
            t = l.strip()
            m = re.search(r'[·•.]?\s*(\d{1,4})\s*[·•.]?\s*$', t)
            if not m: continue
            if len(t) > 6: continue  # 排除正文数字行(页码行短)
            ys = [pt[1] for pt in poly]
            cands.append((max(ys), m.group(1), t))
        cands.sort(reverse=True)  # 最底部在前
        pn = cands[0][1] if cands else None
        if pn: page_numbers[key] = pn
        print(f"  page {key}: {pn} (原文={cands[0][2] if cands else '—'})", flush=True)
    print(f"提取 {len(page_numbers)}/{len(lines)} 页锚点", flush=True)
    return page_numbers


def main():
    doc = fitz.open(INPUT_PDF)
    total = doc.page_count
    doc.close()

    # 选数据源:优先 spotting 缓存(全页OCR已识别页码),否则裁切重OCR
    if SPOTTING_LINES_FILE and os.path.exists(SPOTTING_LINES_FILE):
        print(f"使用 spotting 缓存: {SPOTTING_LINES_FILE} + {SPOTTING_COORDS_FILE}", flush=True)
        page_numbers_ocr = extract_from_spotting(SPOTTING_LINES_FILE, SPOTTING_COORDS_FILE)
    else:
        rng = list(PAGES) if PAGES is not None else list(range(total))
        page_numbers_ocr = {}
        print(f"精准裁切 y{TOP_RATIO:.0%}-{1-BOTTOM_RATIO:.0%} + dpi{DPI},处理 {len(rng)}/{total} 页", flush=True)
        doc2 = fitz.open(INPUT_PDF)
        for pi in rng:
            page = doc2[pi]; r = page.rect
            clip = fitz.Rect(0, r.height * TOP_RATIO, r.width, r.height * (1 - BOTTOM_RATIO))
            pix = page.get_pixmap(dpi=DPI, clip=clip)
            png_path = f"/tmp/pn_page_{pi:03d}.png"
            pix.save(png_path)
            rows = ocr_image(png_path)
            pn, all_nums = pick_page_number(rows)
            if pn: page_numbers_ocr[str(pi)] = pn
            nonwm = [t for t in rows if WATERMARK not in t][:3]
            print(f"  page {pi}: 页码={pn}  候选={all_nums}  文本={nonwm}", flush=True)
        doc2.close()

    # 自动拟合并填充(容忍重复页)
    print(f"\n提取 {len(page_numbers_ocr)} 页锚点,开始拟合...", flush=True)
    page_numbers_final, dup_keys, logic_offset = fit_and_fill(page_numbers_ocr, total)
    if page_numbers_final is None:
        page_numbers_final = page_numbers_ocr
        print("拟合失败,仅输出锚点(需人工检查)", flush=True)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(page_numbers_final, f, ensure_ascii=False, indent=2)
    print(f"\n保存: {OUT_JSON} ({len(page_numbers_final)} 页)", flush=True)

    # 预览完整页码序列
    print("完整页码序列:")
    for pi in range(total):
        print(f"  page {pi}: {page_numbers_final.get(str(pi), '—')}")


if __name__ == "__main__":
    main()
