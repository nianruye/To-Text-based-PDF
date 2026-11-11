# OCR 参数化独立验收报告（t212）

> 验收人：验证评审员（独立复跑/复算；不参与实现）
> 对象：t219 / t209（OCR 5 参数化 + 页脚条带重 OCR 实验）
> 日期：2026-11-11 13:31–14:10（Asia/Shanghai）
> 结论：**FAIL（F1 零回归 gate 未保持不变；F2 构建非确定性）**；参数化/审计/实验数据本身基本可用，见 §6 发现。
> 环境：`/usr/bin/python3`；工作树 HEAD `70a9d70`（含未提交的并行 t208 geometry/S4 改动与 t219 改动）。
> 未改实现/数据；未 commit。新增本报告 + `docs/scan2pdf_acceptance.md` 追加一节。

## 1. 参数化与优先级

| 参数 | 默认 | CLI | 每书 `data/<book>/ocr_params.json` |
|---|---|---|---|
| max_pixels | 2822400 | `--ocr-max-pixels` | `max_pixels`/`maxPixels` |
| min_pixels | 147384 | `--ocr-min-pixels` | `min_pixels`/`minPixels` |
| orientation | 0 | `--ocr-orientation` | `orientation`/`useDocOrientationClassify` |
| unwarp | 0 | `--ocr-unwarp` | `unwarp`/`useDocUnwarping` |
| layout_shape | auto | `--ocr-layout-shape` | `layout_shape`/`layoutShapeMode` |

**独立复算（临时 root，不写 data/）**：book 文件 `maxPixels=4000000, orientation=1, unwarp=1, layoutShapeMode=rect` + CLI `max_pixels=5000000` →
`max_pixels=5000000(source=cli)`、`orientation/unwarp/layout_shape=book_data`、`min_pixels=147384(default)`、sha 长度 64。**优先级 CLI > book > default 成立。**

**默认 payload**：`ocr_book.payload(True,'ocr')` 与旧字典（minPixels 147384/maxPixels 2822400/layoutShapeMode auto/useDocUnwarping false/useDocOrientationClassify false）**逐字节相等**；显式传 `dict(OCR_DEFAULTS)` 亦相等。单测 `test_payload_default_equals_head` 覆盖。

**审计记录（现有 t219 产物）**：每批 `jobs.json` 含 `state/jobId/pages/params`；`manifest.json` 同含 `params/jobId`；`ocr_params_effective.json` 含 `params/sources/path/sha256`。实测：

| 实验目录 | max_pixels | orientation | jobId | effective sources |
|---|---|---|---|---|
| `tmp_vert/t219/ocr_strip` | 4000000 | 0 | `113871012101722112` | max_pixels=cli，其余 default |
| `tmp_vert/t219/ocr_mp282_ori0` | 2822400 | 0 | `113871176647737344` | max/orientation=cli |
| `tmp_vert/t219/ocr_mp282_ori1` | 2822400 | 1 | `113871456832237568` | max/orientation=cli |
| `tmp_vert/t219/ocr_mp400_ori0` | 4000000 | 0 | `113871553141051392` | max/orientation=cli |
| `tmp_vert/t219/ocr_mp400_ori1` | 4000000 | 1 | `113871687459438592` | max/orientation=cli |

> **F4（低）**：契约命令是 `--skip-ocr`，该路径 report `ocr_params=null/ocr_jobs=null`（不触发 OCR）；OCR 路径的 report 字段由 `test_scan2pdf_report_ocr_params_and_jobid` 覆盖（fake OCR：`params.max_pixels=4000000`、`ocr_jobs['spotting_000']='JOB123'`）。文档应注明「report 字段仅在 OCR 跑批时出现」。

## 2. 构建零回归（关键）

测试方法：对同一工作树分别跑「不传新参数」与「显式传 5 个默认值」，并另用 `git archive HEAD`（HEAD=70a9d70，**不含未提交 t208/t219**）构建干净基线。**必须固定 `PYTHONHASHSEED=0`**（t219 报告已注明）。

| 对比（seed=0） | 页数 | chars (nospace) | 逐页文本 diff | gate |
|---|---|---|---|---|
| 当前树 不传参数 | 104 | 43913 | — | **95.9%** |
| 当前树 显式默认 | 104 | 43913 | **0/104** | **95.9%** |
| 干净 HEAD ghbq | 104 | 43913 | 0/104 | **96.8%** |
| 当前树 wz4 | 677 | 554341 | — | **99.4%** |
| 干净 HEAD wz4 | 677 | 554341 | 0/677 | **99.6%** |

- **参数化本身零回归**：不传 vs 显式默认 → 文本/页数/字符/gate 全同（0 diff）。
- **对 HEAD**：文本 0 diff、页数/字符相同，但 **gate 漂移** ghbq 95.9→96.8、wz4 99.4→99.6；归因于工作树未提交的并行 t208（geometry S4 fallback）改动，不是 OCR 参数（`--skip-ocr` 构建不读 OCR 参数）。**验收文字要求 gate 不变 → 未满足（F1）。**
- **非确定性（F2）**：不设 `PYTHONHASHSEED` 时，同参数两次构建实测 gate 93.8% vs 95.9%、6 页文本不同（p7/11/56/59/88/104）。t219 的 43,907/93.8 数据即未固定 seed 的一次结果；必须固定 seed 或修复 build 端 hash 依赖，否则「逐页 0 diff」不可复现。

## 3. 页脚条带重 OCR（T3）

抽页 0-based `[2,18,30,42,54,66,78,90]`（1-based 3/19/31/43/55/67/79/91）；底部 10% @300dpi 8 页 PDF；`max_pixels=4000000`、其余默认、spotting。

| 项 | 独立复算 |
|---|---|
| 条带 lines 页 key | 0..7 |
| 页码命中 | key0 空（封面无页码），key1..7 = **7,19,31,43,55,67,79 → 7/7**（与 `selected.json` expected 一致） |
| 条带总字符 | **13**（仅数字/页脚，与 t219 一致） |
| jobId | `113871012101722112` |

对照：全书 layout number 覆盖 **97/104** 页（t219 报告；本次未重算全书，沿用其数据）。条带实验只证明「这 8 页的页脚数字可读」，**不能直接外推 96→104**；需全量页脚通道实验（F3 建议）。

## 4. 整页参数矩阵（T3b，独立复算）

| 目录 | maxPixels/orientation | lines 字符（含空格） | 非空白字符 | 页码命中 | 校正表一致行（p3） | p3 标题 OCR |
|---|---|---|---|---|---|---|
| ocr_mp282_ori0 | 2.82M / 0 | 3180 | 3180 | 7/7 | 0/2 | 马尔巴乔夫与 / 一人道的… |
| ocr_mp282_ori1 | 2.82M / 1 | **3204** | **3190** | 7/7 | **2/2** | **戈尔巴乔夫与 / “人道的民主的社会主义”** |
| ocr_mp400_ori0 | 4.0M / 0 | 3180 | 3180 | 7/7 | 0/2 | 马尔巴乔夫与 / 一人道的… |
| ocr_mp400_ori1 | 4.0M / 1 | 3180 | 3180 | 7/7 | 0/2 | 马尔巴乔夫与 / 一人道的… |

- 页码命中均 7/7（key0 无页码），与 t219 一致。
- 2.82M+orientation=1 使 p3 两条校正文本 **0/2→2/2**；非空白字符 3180→3190（+10）。
- **F3（低）**：t219 报告表把 ori1 的「字符数」写成 3190（非空白），而其他行 3180 同时等于含空格/非空白；独立复算含空格为 **3204**。应统一口径并注明（建议表头写「非空白字符」，另列含空格字符）。
- maxPixels 4.0M 无额外收益；4.0M+orientation=1 在本样本丢失标题修正（0/2）——与 t219 结论一致。

## 5. 建议（供 captain 决策）

1. **页脚条带重 OCR：值得做专项通道，不进主 OCR 默认**。样本 7/7；全书 layout number 覆盖 97/104，剩余 7 页若确为页脚不可读，可望补到 104/104；需全量实验量化（约 26 批/104 页，API 配额与耗时约为主 OCR 的 1/10–1/5，取决于批量）。风险：条带裁切误差、页码与正文分离、重复计费。
2. **orientation=1：只建议用于标题页/封面页专项**（2.82M 下 p3 校正 0→2/2、+10 非空白字）；不建议全局默认（会增加每批耗时/配额，且 4M+ori1 反例丢失标题）。
3. **maxPixels 4.0M：不建议进默认**（无字符/页码收益）。
4. **默认参数保持不变**；参数化保留为 book/CLI 覆盖即可。**先修 F2（hash 非确定性）**，否则任何 A/B 字符/gate 对比都可能被构建随机性污染；**F1 需等 t208 合并/回退后用干净 HEAD 复跑**。
5. 文档：补 4M 两个 jobId、统一字符口径、注明 `--skip-ocr` report 字段为空、注明必须固定 `PYTHONHASHSEED=0`。

## 6. 发现

- **F1（高，must-fix）零回归 gate 不成立**：当前树 vs 干净 HEAD，ghbq gate 95.9 vs 96.8、wz4 99.4 vs 99.6；文本/页数/字符相同。归因未提交 t208 geometry 改动，但验收要求「gate 不变」未满足 → 不能签收；需先合入/回退 t208 后复跑，或把验收口径改为「参数化本身零回归」。
- **F2（中，must-fix）构建非确定性**：不设 `PYTHONHASHSEED=0` 时同输入两次 gate 93.8/95.9、6 页文本不同；t219 的 43,907 数据不可复现。需固定 seed 或消除 build 端 hash 依赖。
- **F3（低）实验字符口径不一致**：2.82M+ori1 含空格 3204 / 非空白 3190；报告写 3190 未注明口径。
- **F4（低）`--skip-ocr` report 的 ocr_params/ocr_jobs 为 null**：契约命令无法直接看到审计字段；应注明或增加从 `ocr_params_effective.json` 读取的回退。
- **F5（低）4.0M 两组 jobId 未写进报告 §2**（只在 jobs.json）；建议补齐。

## 7. 复现 / 字节绑定

```bash
cd /opt/test
PYTHONHASHSEED=0 /usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/acc_ghbq_ocrparams.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
PYTHONHASHSEED=0 /usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out /tmp/t212/defs_seed0.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force \
  --ocr-max-pixels 2822400 --ocr-min-pixels 147384 --ocr-orientation 0 --ocr-unwarp 0 --ocr-layout-shape auto
# 两者 0 diff、chars 43913、gate 95.9
/usr/bin/python3 -m pytest src/test/unit/test_ocr_book.py -q   # 10 passed
/usr/bin/python3 -m pytest src/test/unit/test_ocr_book.py src/test/unit/test_scan2pdf.py -q  # 45 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/ocr_book.py` | `abb2dcc9ff1eb2079f95d4479ec7c01e01d28a95ed2f29799f5e7657c187be6c` |
| `src/tools/scan2pdf.py` | `4a476377ecba5b3dc5949b505c1bcef37e6516a1122946b5e4c8870aa977b067` |
| `src/test/unit/test_ocr_book.py` | `471fc8dabd9d20767b7ac1e3f30196c44361fa96926dd72022b63df990e44219` |
| `output/ghbq_full/acc_ghbq_ocrparams.pdf` | md5 `a3b1bac26dd967cd7e4d7070b1096c9b` |
| 干净 HEAD | `70a9d70`（t208/t219 未提交） |

## 8. 结论

**t212 FAIL**：参数优先级/默认 payload 等价/审计记录/实验可复现性基本成立，页脚条带 7/7、orientation=1 对标题页 0→2/2 已独立复算；但（F1）当前树相对干净 HEAD 的 gate 未保持不变（95.9 vs 96.8 / 99.4 vs 99.6，文本/字符/页数相同，归因 t208），（F2）未固定 `PYTHONHASHSEED` 时构建不可复现（6 页文本差、gate 93.8/95.9）。修复/合入 t208 + 固定 seed 后复验即可签收；实验数据本身无 must-fix（仅 F3 文档口径）。

---

## 9. t268：payload 显式 17 字段

`ocr_book.payload()` 已从 10 字段扩展为官方 17 字段（`ocr_book.PAYLOAD_FIELDS`）：
`useDocOrientationClassify, useDocUnwarping, useLayoutDetection, useChartRecognition, useSealRecognition, useOcrForImageBlock, mergeTables, relevelTitles, layoutShapeMode, promptLabel, repetitionPenalty, temperature, topP, minPixels, maxPixels, layoutNms, restructurePages`。

默认值对齐 ghbq raw `model_settings` 实测：orientation/unwarp/layoutDetection/chart/seal/ocrForImageBlock/relevel/layoutNms/restructurePages=false，mergeTables=true，layoutShapeMode=auto，promptLabel 由模式决定，repetitionPenalty=1，temperature=0，topP=1，minPixels=147384，maxPixels=2822400。

服务端回声（E1）：
- 一致：`use_layout_detection=false`、`use_chart_recognition=false`、`use_seal_recognition=false`、`use_ocr_for_image_block=false`、`merge_layout_blocks=true`；
- 未回显/被忽略：`relevelTitles`、`layoutNms`、`restructurePages`、`temperature/topP/minPixels/maxPixels/repetitionPenalty`；
- `useSealRecognition=true`（E2）会回显 true，但本样本 lines 无变化；
- `layoutShapeMode=rect`（E3）不直接回显，但 `return_layout_polygon_points` 变 false，lines 仍无变化。

等价性：E0（旧 10 字段）vs E1（显式 17）8/8 页 lines **0 diff**，标点 P/R 相同（TP286/FP53/FN36, P0.8437/R0.8882）。详见 `docs/punct_ocr_payload.md`。
