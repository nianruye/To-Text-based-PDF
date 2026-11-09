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
| 门禁 | t163 前为 skipped（`horizontal_gate_not_wired`）；**t163 后已接入 verify_geom**（本行为历史记录） |
| exit | **8（manual）** |

**结论（v1 横排是否可用）**：`build_geom` 在 wz2 6 页 dry-run **可构建**（页数 1:1、有文本层），但 **横排 verify/quality 门禁未接入**，v1 不能自动判定/交付；
t163 后横排已接 verify_geom（带 --src-pdf）；exit 8 为当时未接门禁的历史结果。

## 13. 复用语义说明（替代 §0 旧表述）

- 外部 out：不覆盖 → exit 2；
- 本工具产物：**默认不覆盖**；完整键匹配时复用并重跑门禁（`resume=true` + `resume_note` 完整键），不匹配 → exit 2；
- `--force` 才重建/覆盖。

---

## 14. 横排修复（#37，t163）

- **构建入口**：geom 分支不再直调 `build_geom.py`，改调 `src/calibration/fit_positional.py`（两趟：pass1 测高 + pass2 ratio 重渲染；argv `lines coords out src`）。
- **横排门禁**：构建后跑 `verify_geom.py`（`VERIFY_PITCH_FLOOR=85`，并传 `--src-pdf` 以启用 DPI 自适应），结果写入 `gate{tool=verify_geom,pass_,pitch_ok_pct,pages,pages_src,blank_pages,overflow_pages}`；失败 → exit 6。
- **wz4 全量（677 页）**：fit_positional 构建成功；scan2pdf gate **PASS**：pitch 99.6%、页数 677=677、空白 32 / 溢出 6（gate 值）；exit 0。历史 `output/wz4/wz4_optimized.pdf` 文本层页数一致、文本差异 0（同 677 页）。
- **wz2 6 页回归**：geom 构建成功，gate PASS，exit 0。
- **⚠ DPI 契约差异**：wz4 的 `data/wz4/*_spotting_coords.json` 当前为 **144dpi 尺度**（max y 1268px / 页高 635pt），`calibrate` 自适应 DPI=144；因此
  `verify_geom` 必须带 `--src-pdf source_pdf/wz4.pdf` 才按 144 判（PASS 99.6%）。**不带 `--src-pdf` 时 verify 默认 DPI=200**，会把正确产物判成 pitch 0%（历史 `wz4_optimized.pdf` 之所以裸命令 PASS，是旧代码按 200dpi 渲染、字号物理偏小 28%）。
  结论：#37 的构建/门禁已修复；外部裸 `verify_geom` 命令需补 `--src-pdf`（battle1 文档原本就带），或由 verify 自动探测——属契约口径，需 captain/用户裁决。

## 15. t163 裁决后的替代验收（wz4）

依据 captain 裁决（契约 verify 命令必须带 `--src-pdf`；历史 200dpi 文本一致不再要求）：

| 项 | 结果 |
|---|---|
| a. verify_geom（带 --src-pdf，floor=85） | **PASS**：677=677、pitch 99.6%、split 0 |
| b. 文本总量对账 | 产物 **560,324** 字 vs OCR lines **546,893** 字 = **1.0246**（≥99%） |
| c. 5 页目视 | 1/18/100/400/677：无跨页溢出、行大致对位；已知 p1 封面图未贴回、目录字体间距差异、正文底部占位偏紧 |
| d. wz2 6 页回归 | fit_positional + verify_geom gate **PASS**，exit 0 |
| e. 历史对照 | 旧 200dpi（7.7pt，物理偏小 28%）vs 新 144dpi（10.7pt），674/677 页/39,028 字差异**属预期**，不要求一致 |
| 单测 | test_scan2pdf + test_quality_gate **44 passed** |

- 证据：`tmp_vert/scan2pdf/wz4_acceptance_recheck.md` + `crops/wz4_p*_vs.png`。

## 16. t167：横排契约同步 + gate sidecar（F1/F3）

### 16.1 F1：全仓 verify_geom 调用统一带 `--src-pdf`

- `optimize_book.py`（第 4 步验证）→ `verify_geom.py out coords lines --src-pdf <src_pdf>`；
- `src/test/README.md`（已带）与 `src/test/snapshots/README.md`（wz1/youhua/wz2 三例）、`docs/HANDOFF_20261024.md`（两处）、`docs/wz4_build_geom_fix_任务简报.md` 示例命令均补 `--src-pdf`；
- 注明原因：**缺省 DPI=200，各书 OCR 数据 DPI 不同（wz4=144dpi），不带会把正确产物误判 pitch 0%**；
- `src/test/verify_geom.py` 的 usage 与 `--src-pdf` help 已注明「必带」；AGENTS §3 契约同步（captain 裁决）。

### 16.2 F3：横排 `<out>.gate.json` / `.gate.md`

geom 构建 + verify_geom 后写 sidecar（与竖排 quality_gate **核心字段对齐**，非全 schema）：

```
<out>.gate.json: version=quality-gate-v1  book  mode=geom  tool=verify_geom
  verdict=PASS|REJECT  reasons=[...]
  metrics={pitch_floor,pitch_ok_pct,pages,pages_src,split,missing,blank_pages,overflow_pages,exit,stdout_tail}
  gate={...同上+reasons}
<out>.gate.md: 结论/tool/pitch/pages/split/overflow/reasons 摘要
```

- reasons 语义：`verify_geom_fail`、`pitch_below_floor`、stdout 中 FAIL 行；PASS 时为空；
- 不再只有 `report.gate` 内嵌。

### 16.3 验证（wz4 deliver / wz2 / 单测）

| 项 | 结果 |
|---|---|
| wz4 `scan2pdf`（geom→fit_positional 两趟） | exit 0，677 页；`<out>.gate.json`：verdict **PASS**、tool verify_geom、pitch **99.6%**、pages 677=677、split 0、overflow 6 |
| `verify_geom --src-pdf source_pdf/wz4.pdf`（floor 85） | rc=0 **PASS**：pitch 99.6%、677=677、split 0 |
| wz2 6 页 | geom build + gate PASS，exit 0 |
| pytest（test_scan2pdf + test_quality_gate） | **44 passed** |

## 17. t169：geom 多纸型 review_required（R1）+ 措辞（R2）

- **R1**：geom 分支与竖排同语义：`book_type.multi_format=true` → `review_required=true`、`auto_pass_forbidden=true`、`multi_format_note`（含纸型分布）；`verdict_effective`：`PASS → MANUAL_ONLY`（exit 8），**`REJECT` 保持 REJECT**（exit 6）；`<out>.gate.json`/`.md` 增 `review_required/auto_pass_forbidden/multi_format/verdict_effective` 并写入 md 摘要。
- 实测：wz4（单纸型）`wz4_r1.pdf` gate **PASS**、`review_required=false`、pitch 99.6%、677=677、split 0；wz2 6 页 gate PASS、`review_required=false`；单测 **30 passed**（新增多纸型 PASS→MANUAL_ONLY、REJECT 保持、单纸型 false、md 字段）。
- **R2**：横排 sidecar 与竖排为**核心字段对齐**（非全 schema）：横排无 `schema_version`/`pdf_sha256`/`thresholds_source`/`expect_low`，`verdict` 词表 `PASS|REJECT`（effective 才 `MANUAL_ONLY`）；竖排为 `AUTO_PASS|MANUAL_ONLY|REJECT` + 质量阈值内嵌。上层统一读 `verdict/verdict_effective/review_required/reasons/tool/pitch/pages/overflow`。

## 18. t172：OCR raw→coords/lines 转换 + ghbq 真 OCR E2E

### 18.1 转换（ocr_book.convert_raw_dir）

- 输入：`<out-dir>/raw/spotting_*.json`（`result.layoutParsingResults[].prunedResult.spotting_res`）；
- `rec_texts/rec_polys` → `coords[<global_page>]` / `lines[<global_page>]`，key 为 **0-based 字符串**；
- 坐标按 **legacy 2×pt**：`scale_x = 2*pdf_page_w/pruned_w`、`scale_y = 2*pdf_page_h/pruned_h`（页尺寸取源 PDF 对应页；缺源时回退 dataInfo）；
- 页序：每批 `jobs[key].pages` 记录全局页号（0-based），转换按该列表对页；无记录时按批内顺序回退；
- 输出 `<out-dir>/<book>_spotting_coords.json` 与 `<book>_spotting_lines.json`；layout raw 只保留，不参与构建。

### 18.2 页号 manifest

- `jobs.json` 每批写 `pages`（全局 0-based 列表）；另写 `<out-dir>/manifest.json`（batches: key/state/jobId/pages + source_pages）；
- 断点续跑/已有 raw 重跑时也补写 pages，保证「批次切片→全局页」可追溯。

### 18.3 scan2pdf 接线

- OCR 完成后先在 `--data-dir`（若给）找 coords/lines，找不到则回退 `<out-dir>/_ocr_<book>/`（转换产物），不再报「缺 coords/lines」；
- `data.mode/reason/coords_sha256/lines_sha256` 记录来源。

### 18.4 ghbq 真 OCR E2E（20–23 页）

命令：`scan2pdf --input source_pdf/ghbq.pdf --book ghbq --out output/test_ghbq/ghbq_pilot4.pdf --pages 20-23 --token-file /tmp/paddle_token`

| 项 | 结果 |
|---|---|
| OCR | A(layout)+B(spotting) 各 1 批 4 页；jobs/manifest pages=[19,20,21,22] |
| 书型 | 初判 vertical（aspect）→ **coords_boxes 修正 horizontal** |
| 构建 | geom→fit_positional 两趟，4 页，exit 0 |
| scan2pdf gate | verify_geom **PASS**：4=4、pitch **100%**、review_required=false（单纸型） |
| 独立 verify_geom --src-pdf | rc=0 PASS（DPI 自适应 138；pitch 100%，页高误差 6.1%） |
| raw vs 产物文本 | 80 行中 **79 行**原样出现在产物文本层（抽样 6 行见报告） |

### 18.5 repetitionPenalty bug（记录）

- 现象：`ocr_book.payload()` 曾把 `repetitionPenalty` 写成 **0**（PaddleOCR 有效范围/语义异常），导致输出重复/异常；
- 修复（captain 热修）：改为 **1**；本任务转换/E2E 均在该修复后验证。

## 19. t175：OCR raw JSONL 解析（大 batch）

- **现象**：ghbq 全书 104 页 OCR（50 页/批）的 raw 响应是 **JSONL**：每批 13 行 × 每行 4 页（最后一行 2 页），`convert_raw_dir` 只按单 JSON 解析 → 转换失败。
- **修复**：`ocr_book._load_json_objects(path)`：先尝试单 JSON（dict/list，兼容旧文件）；`JSONDecodeError` 时逐行 `json.loads`，按**文件内顺序**拼接各对象的 `result.layoutParsingResults`。`convert_raw_dir` 使用拼接后的 results，页序仍由 `jobs[key].pages` 决定。
- **单测**：合成 JSONL（2 对象 / 共 3 页 / jobs.pages=[5,6,7]）→ coords/lines keys 5/6/7、文本顺序正确、scale=1.2；同一内容单 JSON 与 JSONL 转换结果**逐值相等**。
- **全书回归（ghbq 104 页）**：
  - `output/ghbq_full/_ocr_ghbq` raw = 3 批（50+50+4 页，spotting_000/001/002，JSONL 13/13/1 行（50 页批 = 13 行×4 页；4 页批 = 1 行））+ jobs.pages 0..103 + manifest.source_pages=104；
  - 重转换：coords/lines **各 104 页**（keys 0..103）；
  - `scan2pdf --skip-ocr --data-dir output/ghbq_full/_ocr_ghbq --force` → exit 0、geom 构建 104 页、gate **PASS**（**104=104、pitch 96.8%**、split 0、review_required=false）。
