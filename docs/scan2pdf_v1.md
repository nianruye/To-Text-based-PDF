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

## 20. t179：横排标定审计（calib.json + 自检 warnings）

- **build_geom**：`calibrate()` 新增审计字段（DPI 残差/coverage/source_of_page_size/cw 样本/full 样本/pitch 样本/font&baseline source），并在 TOC 校准后写 `<out>.calib.json`（`CALIB_OUT` 可覆盖路径、`CALIB_BOOK` 给 book slug；默认路径 `<out>.calib.json`）。
- **JSON**：schema `horizontal-calib-v1`，字段含 book/src_pdf/sha256/pages/dpi/page_size/cw/measure/font/baseline/margin/toc_params/coverage/source_of_page_size/warnings/selfcheck/env；字段规则见 spec §4。
- **自检**：spec §3 清单落地；warnings 形如 `{code,severity,detail,source}`，同时 stderr 打印 `[calib] WARN ...`；`selfcheck.verdict = pass|warn|fail`；默认不阻断构建（`HORIZ_CALIB_STRICT` 预留未强制）。
- **scan2pdf**：报告含 `calib` 块（读取 `<out>.calib.json`）；gate 侧车带 `calib` 摘要 + `calib_warnings`（作为非阻断 reasons `calib_warn:<code>`），不改变 gate 结论/退出码。
- **单测**：`test_horizontal_calib.py` 4 例（schema、warn 分支、pages fail、写盘 roundtrip）→ 4 passed。
- **E2E**：
  - ghbq 4 页：dpi=138、page 595×868（src_pdf）、font=16.6、baseline/font=2.072（warn）；gate PASS，calib_warn=3。
  - ghbq 104 页：dpi=139、page 603×870（coords）、font=16.5、warn=baseline_font_ratio_out；gate PASS。
  - wz4 677 页：dpi=144（残差 0.09）、page 418×634、font=10.7、warnings=[]、selfcheck=pass；gate PASS pitch 99.6%。
- **已知**：wz4 首 20 页子集构建 gate pitch 83.3% REJECT（TOC 页占位；非 calib 问题），全书 PASS；spec 参考基线 wz4 DPI 144（任务描述的 ≈138 为 ghbq 实测值）。

### 20.1 t182 修复（render 回填 / bp 单位 / 验收文字）

- **render 回填**：`geometry.product_render()` 从产物 PDF 取 `page_pt/font_pt/pitch_pt`；`build_geom` 末尾回填（单趟也描述真实渲染）；scan2pdf 再回填 `render.pass` 与 `selfcheck.pitch_error_pct=100-verify_geom.pitch_ok_pct`（`pitch_error_source=verify_geom`）。
- **单位**：`page_size.unit=bp`、`render.unit=bp`（PDF bp；与源 PDF pt 差 ×0.996264）；spec §4 已同步。
- **spec §2.2**：补「coverage>1 允许至 1.02，属 DPI 估计/坐标边界误差」。
- **验收文字更正**：docs/scan2pdf_acceptance.md 增 t182 节：wz4 full **144/coords/10.7**；ghbq 4p **138/src/16.6**；ghbq full **139/coords/16.5**（两书 full 与 spec §5 一致）。
- **E2E fixture**：`FONT_SCALE=3` → build rc=0 不阻断，calib `font_out_of_range` 报警，render 段存在。
- 实测 ghbq full：render `600.75×866.75bp / font 16.44 / pitch 34.21 / pass=true`；`selfcheck.pitch_error_pct=3.2`（verify_geom 96.8%）。

### 20.2 t184：TOC 自检 + FAIL 兜底 + sidecar 措辞

- **TOC 自检**：新增 `toc_low_sample`（`toc_samples<3`）、`toc_foot_x_out`（`foot_x` 桶对须 0≤x0<x1≤1）、`toc_title_max_out`（`title_max∈[10,80]`）；均 warn，写 `calib.warnings`。
- **FAIL 兜底（按 captain 裁决，不改 build 退出码）**：spec §3.2 改为「FAIL 项 = stderr + calib.warnings + selfcheck.verdict=fail；**构建不阻断（exit 0）**，由 scan2pdf/gate 兜底」；scan2pdf 读 calib 后把 FAIL 项写 gate reasons `calib_fail:<code>`，不自动 PASS（PASS→MANUAL_ONLY，review_required=true）。
- **sidecar 措辞（F5）**：gate 侧车顶层是 `calib` 块（含 `warnings`/`warnings_codes` 与 `calib_warnings`/`calib_fail` code 列表）；`report.gate.calib_warnings` 为 report 内列表；sidecar 不再声称“只带 calib_warnings”。
- **spec §4.2** 删除示例 `date_local`（§4.1 要求无时间戳）；字段表同步删除。
- 验证：ghbq 104 页 toc_samples=1 → 新增 `toc_low_sample` warn；渲染不变性（逐页文本/字符/关键页像素）与 gate 数字另行复跑记录。

### 20.3 单测口径更正（t186）

- 实测：`test_horizontal_calib.py` **6 passed**、`test_scan2pdf.py` **30 passed**（t185 时点）；两者合计 **36 passed**。
- t184 报告写「6 passed（+scan2pdf **35** passed）」有误：35 = `test_ocr_book 5 + test_scan2pdf 30`（旧合并口径），并不含 calib 6；按本书口径应为 **6 / 30 / 36**。
- t186 新增 F2 单测 `test_geom_calib_fail_forces_manual` 后：test_scan2pdf **31 passed**，与 calib 6 合计 **37 passed**。

## 21. t188：交付产物 GMPG 清理（fit_common pass2）

- **根因**：`fit_common.render()` 两趟都强制 `VERIFY_MARK=1`；pass2 是交付 PDF，于是每页 1 处 2pt `GMPG<k>ZZ` 进入文本层（可搜索/复制）。实测：ghbq 104 页 **104 处**、wz4 677 页 **677 处**、历史 `wz4_optimized.pdf` 677 处。
- **修复**：`render(..., verify_mark=True)`；`main()` pass1 `verify_mark=True`（`measure_heights()` 需要 GMPG 归组），pass2 `verify_mark=False`（并显式 `env.pop('VERIFY_MARK')`，继承 shell env 也不会泄漏）。geom/classic 共用 `fit_common.main`，两路径同源生效。
- **交付口径**：交付 PDF 的 `get_text()` 中 `GMPG` = **0**；pass1 仍有标记（仅临时 pass1.pdf）。两趟 ratio 表/页数/正文文本不变（见下）。
- **verify 对齐**：`verify_geom` 在输出无 GMPG 时走「按序号 1:1」回退（源码已有路径，t188 补真 PDF 单测）；1:1 页数下正确，门禁数字不变。
  - **边界（F3，已知不可检出）**：若出现「一源页溢出成多页」与「整页缺失」数量恰好抵消（n_out==n_src），无标记模式无法察觉；需要强保证时用 `VERIFY_MARK=1` 单独渲一份带标记副本做对齐核查（交付物仍不带标记）。
- **E2E（本地构建）**：
  - ghbq 104 页：`ghbq_nomark.pdf` **GMPG=0**、104=104、gate **PASS pitch 96.8%**；与旧 `ghbq_full.pdf` 去掉 GMPG 行后逐页文本 **0 diff**（字符 47,059→46,233，差 826 = 104 条 GMPG 行；含换行计数为 49,262→48,332，差 930 = 826+104 换行。两种口径均可，勿混用）。
  - wz4 677 页：`wz4_nomark.pdf` **GMPG=0**、677=677、gate **PASS pitch 99.6%**；与旧 `review_wz4_calib3.pdf`（677 处 GMPG）去掉 GMPG 行后逐页文本 **0 diff**。
  - 历史 `wz4_optimized.pdf` 也有 677 处，说明是旧 fit_common 的长期泄漏，不是本次新引入。
- **单测**：`test_fit_common_cleanup.py` + `test_fit_common_verify_mark.py` **6 passed**；覆盖 pass1/pass2 env（含 shell 继承）、classic 同源、无标记真 PDF 的 `verify_geom` 1:1 回退。

## 22. t192：LAYJSON 接线 + 图片/图块 passthrough

- **LAYJSON**：`ocr_book.convert_layout_json()` 将 layout raw（JSON/JSONL）转 `<out>/<book>_layout.json`：页 key 由 jobs.pages，块含 category/bbox/text；`layout_manifest.json` 记页数/sha。`scan2pdf.find_layout()` 优先已存在文件，否则从 raw 自动生成；`--ocr-mode auto/layout` 接线，report 记录 `layout` path/pages/source/sha。
- **build_geom**：`LAYOUT_FIGS=1` 加载 `image/figure/chart/footer_image/header_image`；`_lay_bbox_142()` 逐页按 src/layout 尺度换算；图块用 `\AddToShipoutPictureBG`（不占流、不翻页）；`LAYOUT_HEADINGS` 默认 **0**（本 E2E 不开，保 pitch 96.8）；`LAYOUT_TOC` 对 p11 aside 接线，p10 作者列待 S8。
- **E2E ghbq（104 页，`--skip-ocr --data-dir output/ghbq_full/_ocr_ghbq --force`；**图片验收需显式 `--layout`（或 LAYOUT_FIGS=1），默认命令不传 LAYJSON/不出图**）**：
  - LAYJSON **104 页**；p1 图块 2（封面照片 1653×1121 + 页脚图 680×93）、p2 条形码 `chart` 429×343、p3 图版 1653×1136 均进入 PDF 图像对象；
  - 文本非空白字符 **43,913** vs 无图版 **43,913（0，不减）**；`GMPG=0`；页数 **104=104**；p11/p12/p104 逐字等于默认（TOC aside 已跳过、layout 页码只用直接 number）；
  - gate **PASS**，pitch **96.8%**（LAYOUT_HEADINGS 默认 0；标题能力可显式开，本 E2E 不改变正文分页）。
- **零回归**：
  - wz4 不传 LAYJSON：677=677、字符 **554,341** 与 t188 无图版完全相同、gate PASS **99.6%**；
  - wz2 6 页：6=6、gate PASS **100%**；
  - 无 LAYJSON 时不出现图块加载日志。
- **单测**：`test_ocr_book` converter（JSONL/页序/blocks/legacy）+ `test_scan2pdf` find_layout missing/converted + `test_page_image` category/crop/fallback；**41 passed**（test_ocr_book+test_scan2pdf+test_page_image）。
- **残留**：p10 作者列仍待 S8；`LAYOUT_TOC` 仅 p11 aside；p2 ISBN span 与 chart 顶 8pt 条带（1287pt²，<5% span 面积）保持可见，重复来自源图本身（F5 登记）。

## 23. t199：整页叠加 PAGE_IMAGE_FULL_RATIO（p1/p3）

- **实现**：`LAYOUT_FIGS=1` 时按 `_lay_img_cov`（image/figure/chart/header_image/footer_image 并集面积 / layout 页面积）判定；`>= PAGE_IMAGE_FULL_RATIO`（默认 0.40）触发 `_page_img_full`：
  - `render_src_page(key)` 生成源页整页 raster，`\AddToShipoutPictureBG` 按 `PAGE_W×PAGE_H` 铺满（图像 1654×2407 / 页 600.8×866.8）；
  - 本页文本 span 全 `3 Tr`（不可见、可搜、字符不减少）；
  - 未达阈值页保持原图块裁贴 + 图外文字可见。
- **实测 ghbq（104 页，`--layout`）**：p1 覆盖率 **0.466**、p3 **0.470** → 整页叠加；p2 chart 覆盖率 **0.037** 不触发、条形码仍可见、文字 type0；p1 源图含正确标题「戈尔巴乔夫」，p3 源图复制封面。p1/p3 texttrace 全 **type3**；p2 type0；文本 **43,913** = 默认（不减少）；GMPG **0**；104=104；gate **PASS 96.8%**。
- **默认零回归**：不传 LAYJSON 时 `_page_img_full` 不启用；ghbq 104/104 与 HEAD 逐页文本 0 diff，wz4 677/chars554341/gate99.6，wz2 6/gate100。
- **单测**：`test_image_page_full_ratio_boundary` 覆盖 0.399/0.40/0.401 与 ratio 覆盖边界；`test_page_image` 5 passed。

## 24. t203：每书文本校正 corrected_text

- **数据**：`data/<book>/corrected_text.json`（0-based page key + 0-based line index → 整行文本；`_comment` 忽略）。
- **应用**：lines 加载后、`--pages` 切片前替换；patched lines 写入 `_scan2pdf_<book>/lines_corrected.json` 后交给 build/verify；coords/页数/页码不变。
- **入口**：`--corrected-text PATH`；缺省 `data/<book>/corrected_text.json` 存在则自动启用。
- **审计（spec §3.3 口径）**：report `corrected_text{enabled,path,source,sha256,pages,pages_count,replaced,skipped,warnings,line_counts}`；`replaced` 为主字段、`applied` 为兼容别名；`pages` 为页 key 数组、`pages_count` 为计数；`line_counts {"2":{"before":2,"after":2}}`；`warnings` 为 `{code,page,line,message}` 对象数组；resume 键用 patched lines sha（保留 `lines_sha256_original`）。
- **warning/校验**：未知页/行/非法 value/含换行 → warn skip 并逐条写 stderr（含 code/page/line）；坏 JSON/根非 object/行数变化 → exit 2（行数变化不写 warning 码）。
- **默认启用**：若 `data/<book>/corrected_text.json` 存在，scan2pdf **默认自动启用**（source=book_data）；不需要时必须显式移走文件（当前无 `--no-corrected-text` 开关）。
- **宽度 sanity（未强制）**：校正值长度/宽度未做 MEASURE 校验；非整页页若显著变长可能溢出/换行，需人工控制；整页 raster 页无视觉影响。
- **校验**：显式缺失/坏 JSON/根非 object/行数变化 → exit 2；未知 page/line/非法 value → warn 跳过；无文件零回归。
- **E2E ghbq**（`data/ghbq/corrected_text.json`，p3 key2 两条）：
  - `--layout` 重建：104=104、gate **PASS 96.8%**、chars 43,913 不变；
  - 产物文本层含「戈尔巴乔夫与」「“人道的民主的社会主义”」，**不含**「马尔巴乔夫」；p3 文本 `戈尔巴乔夫与 / “人道的民主的社会主义”`；
  - 校正 2 条、跳过 0、source=book_data；整页图上仍显示原图（文本层可搜）。
- **默认零回归**：创建校正文件前 `t203_default` vs `t199_default`：104=104、chars 43,913=43,913、逐页文本 **0 diff**、gate 96.8、`corrected_text.enabled=false`。
- **wz4 零回归**（无 corrected_text 文件）：677=677、chars 554,341=554,341、逐页文本 **0 diff**、gate **PASS 99.6%**、`enabled=false`。
- **单测**：`test_corrected_text.py` 6 passed（替换/未知页行/非法值/缺失零回归/坏 JSON/根非 object）；`test_scan2pdf.py` 新增 corrected 进 build + report 审计 1 例（33 passed）。


## 25. t208：S4 行数保真低 full_ratio 兜底（实验结果）

- **实现**：`geometry.calibrate()` 在 `full_ratio < HORIZ_FALLBACK_RATIO`（默认 0.10）时启用 fallback：
  - `cw = median(全部合格行字数)`；`MEASURE_POLY = P90(全部合格行宽)`；`MEASURE = MEASURE_POLY`（不除 OVERBOUND）；
  - `FONT = MEASURE/cw`；审计 `estimator/fallback_sample_n/fallback_width_pt/fallback_char_median`；
  - `HORIZ_CW` / `HORIZ_FONT_MEASURE` 显式覆盖优先；`HORIZ_FALLBACK_RATIO=0` 关闭。
- **ghbq 实测（104 页，fallback）**：
  - calib：cw25、measure460pt、font18.4、full_ratio0.028、estimator=fallback、warnings=[toc_low_sample]（baseline_font_ratio_out 消失）；
  - verify_geom：**行数 1:1 35.1%**（目标≥95，未达）、页高误差<5% 19.1%（中位6.5%，目标<2，未达）、overflow **26**（目标0，未达）、pitch **96.8%**（目标≥99，未达）、104=104。
  - 对照旧公式（无 fallback）：行数35.1%、页高<5% 27.7%、中位5.9%、overflow25、pitch96.8%。
- **结论**：fallback 只去掉 baseline/font 满行假设与 warning，未达到 S4 行数/页高/overflow 目标；根因不在 cw/FONT 单点：产物 `get_text` 的 21 行/17 行差异含 **同一源行被 OCR 片段 x 间隔拆成多个 span**（如 p32 源行6）及版式行高，需要 build_geom 行合并/验证口径另行处理，超出本任务 in-scope（只 geometry）。
- **零回归**：wz4 677/chars554341/diff0/gate99.6；wz2 6/chars1469/diff0/gate100；wz1 222/gate97.8；wz1/wz2/wz4 calib `estimator=full_line`、cw/font 与旧公式一致。
- **单测**：`test_horizontal_calib.py` **10 passed**（fallback/low/full/override/threshold + 原 6 例）。

## 26. 结构性守卫（t215）：E2E 冒烟 + 规格一致性 + 架构守卫

### 26.1 E2E 冒烟脚本

```bash
bash scripts/e2e_smoke.sh \
  --book ghbq --input source_pdf/ghbq.pdf \
  --data-dir output/ghbq_full/_ocr_ghbq \
  --out /tmp/e2e_ghbq.pdf [--pages 20-23]
```

- 参数：`--book/--input/--data-dir/--out` 必填，`--pages` 可选（小样本）。
- 流程：`scan2pdf --skip-ocr --force` → 读 `<out>.report.json` / `<out>.gate.json` → 输出一行 summary：
  `[e2e] book=... out=... exit=... gate=... pitch=... pages=...`
- 失败语义：scan2pdf 非 0 **或** gate 非 PASS/AUTO_PASS/MANUAL_ONLY → 脚本退出 1；参数缺失/未知参数 → exit 2。
- 实测：ghbq 20–23 页 `exit=0 gate=PASS pitch=100.0 pages=4`；坏 data-dir → exit 1（scan2pdf exit 3）。

### 26.2 规格一致性测试（`test_spec_conformance.py`）

守的是「spec 声明 ≠ 实现」：
- `CORRECTED_TEXT` report 字段（replaced/pages/line_counts/warnings/source/sha256）在 spec 与实现同时存在；
- `HORIZONTAL_CALIB` selfcheck 码表（pages_mismatch/empty_input/source_of_page_size_missing/dpi_residual_large/font_out_of_range/baseline_font_ratio_out/page_size_overcoverage/page_size_coverage_low/pitch_low_sample/full_sample_low/cw_out_of_range/measure_out_of_range/margin_out_of_range/toc_low_sample/toc_foot_x_out/toc_title_max_out）实现齐备，spec 含自检条款；
- `PAGE_IMAGE_LAYOUT` env 名与默认值（LAYOUT_HEADINGS/FIGS/TOC、PAGE_IMAGE_PAGES、PAGE_IMAGE_FULL_RATIO=0.40）；
- `scan2pdf` report 顶层键（tool/version/book/input/out/input_sha256/steps/exit）。

任一 spec 声明但实现缺失 → test fail。

### 26.3 架构守卫（`test_architecture_guard.py`）

- `scan2pdf.build_pdf` 的 geom 分支必须调用 `src/calibration/fit_positional.py`，且该函数体内**不得**出现 `build_geom.py`（防再退化为单趟交付）；
- `fit_positional.py` 薄壳必须存在且复用 `fit_common.main('build_geom')`（两趟校准入口唯一）。

违规 → test fail，阻止「入口不唯一/绕过两趟校准」再次发生。

### 26.4 运行

```bash
/usr/bin/python3 -m pytest src/test/unit/test_spec_conformance.py \
  src/test/unit/test_architecture_guard.py -q
```

### 26.5 t226：E2E 确定性 / 重复性 / 失败摘要 / 守卫 token 精确化

- **构建确定性**：`scripts/e2e_smoke.sh` 顶部 `export PYTHONHASHSEED=0`；同一命令连续跑 **2 次**（`--repeat` 默认 2），断言两次 exit/pages/gate/pitch 一致；不一致 → 退出 1。不设 seed 不再作为验收场景。
- **失败摘要**：失败时 summary 含 `reason=`（gate reasons 前两条），并打印 scan2pdf 日志最后 **20 行**，便于定位。
- **守卫 token**：`test_spec_conformance.py` 改为完整 token 集合匹配（`\b...\b`），不做子串；fixture 用 `APPLIED_X`/`REPLACED_TOK` 验证 `replaced` 不误匹配。红/绿双侧：临时把 spec `replaced→REPLACED_TOK` → 测试 FAIL；恢复 → 7 passed。
- **E2E 已知阻断（t208 未回退，t221 处理中）**：当前树 `wz2 --pages 1-6` → exit 6 / gate REJECT / pitch **66.7%**；干净 HEAD（worktree `70a9d70`）同数据 → exit 0 / gate PASS / pitch **100%**、6=6。ghbq 4 页当前树与 HEAD 均 PASS 100%（4 页）。t221 回退后应回到 wz2 PASS 100。
- 复跑：ghbq 命令两次均 exit0/PASS100/pages4；坏 data-dir exit1 且 summary 带 reasons/log tail。
