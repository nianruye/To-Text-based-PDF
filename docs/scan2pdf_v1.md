# scan2pdf v1 · 扫描书一键还原（判书型 → 数据 → 构建 → 门禁）

> 任务：t152 — 按 `docs/scan2pdf_design.md`（t115）实现 scan2pdf.py + ocr_book.py，接入门禁；顺手修 gate F1/F2 呈现层
> 执行：竖排工程师　日期：2026-11-09
> 证据：`src/tools/scan2pdf.py`、`src/tools/ocr_book.py`、`src/test/unit/test_scan2pdf.py`、`tmp_vert/scan2pdf/`
> 约束：不改 verify_vert/punct_eval/content_eval 判据；未 commit；dry-run 不调 API。

## 0. 结论（dry-run，wz6 / wz7）

| 命令 | 书型 | 构建 | 门禁 | exit |
|---|---|---|---|---|
| wz6 全量 `--skip-ocr --data-dir data/wz6` | vertical / has_frame / 595.28×1245.31 / multi=False | 231 页，`build_vert`（VERT_MISSED_FIX=0） | **REJECT**（verify 95.0%、越界 span 29；punct MANUAL、content REJECT） | **8** |
| wz7 `--pages 1-5` | vertical / no_frame / 892.5×1323 / **multi=True** | 5 页 | **REJECT**（verify PASS 5=5；punct 0 FN=686 因 gold 页 57… 不在 1-5；content unscored） | **8** |

- 产物：`tmp_vert/scan2pdf/out_wz6.pdf` + `.gate.json/.md` + `.report.json`；`out_wz7_dry.pdf` 同。
- wz6 dry-run 用**当前 HEAD** 重建，与冻结基线（`output/wz6/wz6_vert_full.pdf`，verify PASS）不同：当前构建 29 处越界 span、字符量 95.0% → 门禁 REJECT 属**如实结果**（不是 scan2pdf 链路故障）；基线/新构建差异另案。
- wz7 混合纸型已按设计**不静默按主导纸型**：报告 `book_type.multi_format=true`，结论至少 MANUAL_ONLY（本次 punct/content 已 REJECT）。5 页 dry-run 只验证链路，不作质量结论。

## 1. 接口

```bash
/usr/bin/python3 src/tools/scan2pdf.py \
  --input source_pdf/<book>.pdf --book <book> --out <out.pdf> \
  [--data-dir data/<book>] [--skip-ocr] \
  [--ocr-mode auto|layout|spotting] [--pipeline auto|vert|geom] \
  [--token-file /tmp/paddle_token] [--pages 1-5] [--force] [--report <path>]
```

- `--skip-ocr` + `--data-dir`：直接复用 `*_coords*.json` / `*_lines*_patched.json`（找不到则 exit 4），**不调 API**。
- 未 `--skip-ocr`：调用 `ocr_book.py`（A=layout+ocr、B=spotting；分批 50 页、4 次退避重试、`jobs.json` 断点续跑；token 只读）。
- `--pages`：切 coords/lines + 源 PDF 子集，用于 dry-run/局部验证。
- `--force`：允许覆盖 `--out`（默认已存在则 exit 3）。

## 2. 步骤 0–10（实现映射）

| 步 | 内容 | 失败码 |
|---|---|---|
| 0 | 参数/输入校验 | 2 |
| 1 | 书型判断（优先复用 t115 探针缓存 `tmp_vert/scan2pdf/probe_<book>.json`，无缓存则页面尺寸+矢量/图像长直线启发式） | 2 |
| 2 | 数据准备（skip-ocr 复用 / OCR） | 4 / 5 |
| 3 | 新书 fix 守卫：`VERT_MISSED_FIX=0`；仅 `--data-dir`/`data/<book>/` 内存在 `*fix*.json` 时启用 | — |
| 4 | 选管线：竖→`build_vert`，横→`build_geom`（argv: lines coords out src；`VERT_TMP` 隔离） | — |
| 5 | 构建到临时文件（失败不覆盖 `--out`） | 6 |
| 6 | 页数 1:1 校验（源/切片 vs 产物） | 6 |
| 7 | 原子移动落盘 | — |
| 8 | 门禁：`quality_gate.py` → `<out>.gate.json/.md`（`--src-pdf`/`--content-gold`） | — |
| 9 | 多纸型注记（至少 MANUAL_ONLY） | — |
| 10 | 结论文档 `<out>.report.json` + exit 码 | — |

## 3. 失败矩阵（exit）

| 码 | 含义 |
|---|---|
| 0 | AUTO_PASS（门禁通过） |
| 2 | 用法/输入不存在/书型判断失败 |
| 3 | `--out` 已存在（未 `--force`） |
| 4 | 数据缺失（coords/lines 不存在；OCR 完成但缺转换） |
| 5 | OCR 失败（token 缺失/API/批处理失败） |
| 6 | 构建失败或页数不 1:1 |
| 7 | partial：门禁 MANUAL_ONLY |
| 8 | reject：门禁 REJECT（文件仍生成，供人工审阅） |

## 4. 书型判断（书无关）

- 优先 `probe_<book>.json`（t115 探针：paper/orientation/frame/multi_format）；无缓存回退：页面尺寸聚类（±5pt 合并）、矢量长线 + 图像暗像素长直线（竖排看左右、横排看上下边带）、宽高比定轴。
- wz6：vertical / has_frame=True / 595.28×1245.31 / multi=False；wz7：vertical / no_frame / 892.5×1323 / **multi=True**（892.5×1323、705×1083.8、921.8×1443）。
- 结果写入 `<out>.report.json.book_type`；多纸型时结论不会 AUTO_PASS。

## 5. 门禁 F1/F2 呈现层修复

- **F1**：punct failures 的 `column/char_pos` 由 `pages_with_fn` 首个失败页回填（不再恒 null）；failures 剔除零样本类（tp+fp+fn==0）。
- **F2**：`must_pass_applicable=false` 时清空坐标列表（`must_pass_fail_items=[]`、`must_pass_items=None`、`must_pass_status=not_applicable`）；content 超限页定位改为**首个字符不一致位置**（column/char_pos/gold_char/product_char）。
- 未改任何判定/阈值（quality gate 单测 18 passed 保持）。

## 6. OCR 入口（ocr_book.py）

- `--book --input --out-dir --token-file --mode layout|spotting|both --pages-per-batch --resume --pages`
- 分批复用 `tmp_vert/battle19/run_batches.py` 同款 payload（A: layout+ocr；B: spotting），`jobs.json` + `raw/` 断点续跑。
- **v1 限制**：B(spotting) 结果 → coords/lines 的转换尚未实现；`--skip-ocr` 复现路径完整，真实 OCR 路径需下一步接转换（本任务 dry-run 不调 API）。

## 7. 单测（11 passed）

书型（竖/横/multi_format/探针缓存）、`find_data`/`find_fix`、`parse_pages`、out 已存在保护（exit 3）、data 缺失（4）、缺 token（5）、构建失败（6）、页数不匹配（6，且不落 out）、`--pages` 切片。

## 8. 已知局限

- **wz6 dry-run 与冻结基线不同**：当前 HEAD 重建 → verify FAIL（29 越界/95.0%），门禁 REJECT；scan2pdf 如实返回 8，不做“掩盖式通过”。
- **wz7 混合纸型**：v1 不静默；需要人工/后续版本决定纸型处理。
- **OCR 转换**：A+B 原始 JSON → coords/lines 转换未实现（v1 仅复用现有数据）。
- **门禁 provisional**：阈值仍为 t111 标定前值，AUTO_PASS 不应作为交付依据。
- **dry-run 5 页**：gold 页（57…）不在子集，punct/content 指标不可比，只看链路。

## 9. 复现

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz6.pdf --book wz6 \
  --out tmp_vert/scan2pdf/out_wz6.pdf --data-dir data/wz6 --skip-ocr            # exit 8（REJECT）
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz7.pdf --book wz7 \
  --out tmp_vert/scan2pdf/out_wz7_dry.pdf --data-dir data/wz7_full --skip-ocr --pages 1-5  # exit 8
/usr/bin/python3 -m pytest src/test/unit/test_scan2pdf.py -q                     # 11 passed
```

## 10. 约束

- 只写 src/tools/scan2pdf.py、src/tools/ocr_book.py、src/tools/quality_gate.py（仅 F1/F2）、src/test/unit/test_scan2pdf.py、docs/scan2pdf_v1.md、tmp_vert/scan2pdf/；未改 verify/punct 判据；未 commit。

---

## 11. R1 复用键（t161）

- resume 复用键 = `book + input_sha256 + fix_sha256 + coords_sha256 + lines_sha256 + mode + pipeline + pages`；
  任一项不同 → **不自动复用**，按「out 已存在」`exit 2`，report 写 `resume_mismatch.mismatch`（逐项 prev/current）与提示（`--force` 或换 `--out`）。
- 匹配 → 复用已有 out（`build.skipped=resume_existing`）并重跑门禁；`resume_note` 写明完整键。
- 实测（wz2）：
  - 构建一次（`--force`）→ out md5 `7cbbaeeb…`；
  - 再用 `--pages 1-3` 复用同名 out → `exit 2`，`mismatch={'pages':['1-6','1-3']}`，out md5 **不变**；
  - 恢复 `--pages 1-6` → 复用（`build.skipped=resume_existing`）、out md5 **不变**、`resume_note` 含完整键、门禁按 pipeline 处理。

## 12. heldout 横排验证：wz2（t161）

| 项 | 结果 |
|---|---|
| 页数/纸型 | 783 页；595.3×935.0（771 页主导）；`multi_format=false`（9/2/1 页为小比例变体） |
| 书型初判 | computed：portrait → vertical（aspect），`has_frame=false` |
| 书型修正 | **OCR 框长宽比（coords_boxes）→ horizontal**（横排框宽≈1.5×高） |
| pipeline | `geom`（build_geom） |
| 构建 | **成功**：`build_geom.py` rc=0，6/6 页，out `out_wz2.pdf`（110,009 B），page0 文本 32 字 |
| 门禁 | **skipped**：`horizontal_gate_not_wired`（quality_gate v1 只接 verify_vert；横排需 verify_geom） |
| exit | **8（manual）** |

**结论（v1 横排是否可用）**：`build_geom` 在 wz2 6 页 dry-run **可构建**（页数 1:1、有文本层），但 **横排 verify/quality 门禁未接入**，v1 不能自动判定/交付；
按 exit 8 人工处理。横排整书验证与 verify_geom 接入留 v2。

## 13. 复用语义说明（替代 §0 旧表述）

- 外部 out：不覆盖 → exit 2；
- 本工具产物：**默认不覆盖**；完整键匹配时复用并重跑门禁（`resume=true` + `resume_note` 完整键），不匹配 → exit 2；
- `--force` 才重建/覆盖。
