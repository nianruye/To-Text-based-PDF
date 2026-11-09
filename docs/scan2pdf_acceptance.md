# scan2pdf v1 独立验收（t158 · round 3）

> 验收人：验证评审员（独立验证方）　日期：2026-11-08 23:19–23:45
> 对象：t157（多纸型口径：REJECT 不降级 + review_required / multi_format_note）
> 基线：HEAD `84d6b95`（未 commit）；**未改实现/数据、未 commit**
> 证据：`src/tools/scan2pdf.py`（`c011f3a2…`）、`test_scan2pdf.py`（`7e94e6e9…`）、`tmp_vert/scan2pdf/out_wz6.*`、`/tmp/t158/`

---

## 0. 结论

**PASS**（按 captain 调整后的多纸型口径）：

- **多纸型判定（wz7）**：`gate.verdict_effective=REJECT`（**非 AUTO_PASS**，REJECT 保持）、`review_required=true`、`multi_format_note` 非空且含纸型分布（892.5×1323:610 / 705×1083.8:582 / 921.8×1439.2:554 / 921.8×1416.8:1 / 921.8×1434.0:1）；`multi_format` 块含 `auto_pass_forbidden=true / severity=>=MANUAL_ONLY / paper_distribution`。→ **合格**（REJECT 更严，不弱化）。
- **wz6（单纸型）**：维持 **MANUAL_ONLY**、`review_required=false`、`multi_format=null`；exit 7。
- **wz6 dry-run 等价**：spotting 同源数据（mode=spotting）、fix=none/0；231 页、**68412 字符 = 基线**、**213/231 页文本相同**（总字符相等，页幅一致）；verify **PASS（97.2%、越界 0、丢失 0）**；gate MANUAL_ONLY + `.gate.json/.md` 生成。
- **wz7 dry-run**：spotting 同源、fix=canonical_wz7；5 页构建、gate REJECT、exit 8；分布写入 report。
- **失败矩阵**：缺输入 2 / 外部 out 已存在 3（dummy 未改）/ 缺 token 5 / 页数不匹配 6（out 未生成）/ 坏 data 6（out 未生成）。
- **新书守卫**：fakebook `fix.path=None/source=none/VERT_MISSED_FIX=0`、`review_required=false`；wz7 canonical fix 加载。
- **gate F1/F2**：字段与 t151 一致（含 `expect_low/version/metrics/verdict/reasons`）；punct failures 无零样本类；`must_pass_status=not_applicable`、`must_pass_fail_items=[]`。
- pytest **18 passed**。

---

## 1. PASS/FAIL 总表

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | wz6 dry-run 构建 + gate；产物与基线内容等价 | **PASS** | 231 页、68412 字符=基线、213/231 页同文（18 页小差异、总字符相等）、页幅一致；verify PASS 97.2%/0；gate MANUAL_ONLY |
| 2 | 书型 wz6/wz7 正确；wz7 多纸型判定 + 分布 | **PASS（调整口径）** | wz6 vertical/framed；wz7 vertical/no_frame/multi=True；`verdict_effective=REJECT`、`review_required=true`、`multi_format_note` 含分布 → 合格（非 AUTO_PASS） |
| 3 | 失败矩阵 ≥4；exit 2–8；out 不覆盖 | **PASS** | 2/3/5/6/6；外部 out 保持 dummy；失败时 out 未生成 |
| 4 | 新书守卫 0；wz7 fix 加载 | **PASS** | fakebook fix=None/0；wz7 `canonical_wz7` + `VERT_MISSED_FIX=docs/vert_taskF_missed_fix.json` |
| 5 | gate JSON 与 t151 一致；F1/F2 已修 | **PASS** | keys 含 expect_low/version/metrics/verdict/reasons；punct 零样本类不出现；must_pass not_applicable 且坐标清空 |
| 6 | 报告 docs/scan2pdf_acceptance.md；不改实现/数据；不 commit | **PASS** | 本文件；只读；未 commit（HEAD `84d6b95`） |

---

## 2. wz6 dry-run 对照

| 项 | scan2pdf | 冻结基线 | 判定 |
|---|---|---|---|
| 数据 | `wz6_spotting_coords.json` + `wz6_spotting_lines.json`（mode=spotting） | — | ✓ 同源 |
| 页数 | 231 | 231 | ✓ |
| 字符数 | **68412** | 68412 | ✓ |
| 页文本相同 | **213/231**（18 页小差异，总字符相等） | — | ✓ 等价（小差异属 HEAD vs 冻结基线） |
| 页幅 | 一致 | 一致 | ✓ |
| verify | PASS（97.2%、越界 0、丢失 0） | PASS | ✓ |
| gate | MANUAL_ONLY（data_missing + content_over_manual） | — | ✓ exit 7 |

## 3. wz7 多纸型（captain 调整口径）

| 字段 | 实测 |
|---|---|
| `gate.verdict_effective` | **REJECT**（非 AUTO_PASS） |
| `review_required` | **true** |
| `multi_format_note` | 非空，含「REJECT 更严、不弱化」+ 纸型分布 + review_required 说明 |
| `multi_format.auto_pass_forbidden` | true |
| `multi_format.severity` | `>=MANUAL_ONLY` |
| `paper_distribution` | 892.5×1323:610 / 705×1083.8:582 / 921.8×1439.2:554 / 921.8×1416.8:1 / 921.8×1434.0:1 |
| exit | 8（REJECT） |

→ 满足「不得 AUTO_PASS + multi_format_note 有内容 + review_required=true」；REJECT 保持 REJECT 符合裁定。

## 4. 失败矩阵

| # | 反例 | exit | out |
|---|---|---|---|
| 1 | 缺输入 PDF | **2** | 未生成 |
| 2 | 外部 out 已存在（dummy） | **3** | 保持 dummy |
| 3 | 缺 token（不 --skip-ocr） | **5** | 未生成 |
| 4 | 页数不匹配（200 vs 231） | **6** | 未生成 |
| 5 | 坏 data（lines 非法 JSON） | **6** | 未生成 |

## 5. 新书守卫 / fix

- fakebook：`data.mode=spotting`；`fix.path=None, source=none, VERT_MISSED_FIX=0`；`review_required=false, multi_format=null`；5 页构建成功（exit 7）。
- wz7：`fix.path=/opt/test/docs/vert_taskF_missed_fix.json, source=canonical_wz7`；构建日志 `VERT_MISSED_FIX=...`；multi 三字段并存。

## 6. 门禁报告（t151 对照）

- `out_wz6.pdf.gate.json` keys：`schema_version/book/pdf_sha256/thresholds_source/thresholds/verify/punct/content/gate/expect_low/version/metrics/verdict/reasons`。
- verify：PASS（231/231、97.2%、越界 0、丢失 0）。
- F1/F2：punct failures 无零样本类；`must_pass_status=not_applicable`、`must_pass_fail_items=[]`；`over_limit_pages` 10 页带定位。

## 7. 复现 / 字节绑定

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz6.pdf --book wz6 \
  --out tmp_vert/scan2pdf/out_wz6.pdf --data-dir data/wz6 --skip-ocr
# -> verify PASS / gate MANUAL_ONLY / exit 7
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz7.pdf --book wz7 \
  --out tmp_vert/scan2pdf/out_wz7_dry.pdf --data-dir data/wz7_full --skip-ocr --pages 1-5
# -> gate REJECT + review_required=true + multi_format_note / exit 8
/usr/bin/python3 -m pytest src/test/unit/test_scan2pdf.py -q    # 18 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/scan2pdf.py` | `c011f3a2f3ecb7ddc715d020658023c38554f0db355521de8e89bddafeba0dba` |
| `src/test/unit/test_scan2pdf.py` | `7e94e6e9c4d09bfcf90ed87643581963aafa922db3b3dd31279e7f8a874ebe3e` |
| `output/wz6/wz6_vert_full.pdf` | md5 `99bef17b73d0afbc2d616e301511a182` |
| HEAD | `84d6b95`（未 commit） |

---

## 8. 结论

**t158 通过（PASS）**：多纸型口径按 captain 裁定落地（REJECT 保持 + `review_required=true` + `multi_format_note` 含分布，非 AUTO_PASS）；wz6 dry-run 与基线等价、verify PASS；失败矩阵/守卫/fix/gate F1/F2 全过；pytest 18。

**低风险备注**：wz6 与冻结基线 18/231 页极小文本差异（总字符相等，属 HEAD vs 冻结基线）；外部 out 语义 exit 3、本工具产物 resume 显式标注。


---

# R1 复用键 + heldout 横排（t162 · 独立验收）

> 对象：t161（R1 完整复用键 + wz2 heldout）
> 日期：2026-11-08 23:47–00:15；**未改实现/数据、未 commit**（HEAD `84d6b95`）
> 证据：`src/tools/scan2pdf.py`（`9579e31b…`）、`test_scan2pdf.py`（`1e6e6d19…`）、`tmp_vert/scan2pdf/acc_wz2.pdf*`、`/tmp/t162/`

## R1.1 PASS/FAIL

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 复用键：fix/data/pages 任一不同 → exit 2 且 out 未覆盖；完全匹配 → resume=true + resume_note 含完整键 | **PASS** | pages 1-3 → exit 2、mismatch `{"pages":["1-6","1-3"]}`、out md5 `928ea1f9…` **不变**；data 改 coords → exit 2、mismatch `coords_sha256`（99a0…→5cf3…）；--fix → exit 2、mismatch `fix_sha256`（''→bced…）；同键重跑 → exit 8（gate skipped）、`resume=true`、`resume_note` 含 book/input_sha/fix_sha/coords_sha/lines_sha/mode/pipeline/pages、`build.skipped=resume_existing`、out md5 不变 |
| 2 | heldout wz2 dry-run：书型/路由/构建/报告一致 | **PASS** | book_type **horizontal**（computed，`axis_refined_by=coords_boxes`）、has_frame=false、595.3×935、783 页、multi=false；pipeline **geom**、rc **0**、pages_out 6/6；PDF 6 页、页幅 592.8×931.5、page0 文本 20 字（`中华国学文库 中国軍庫 盐铁论校注 王利器校注`）；gate **skipped（horizontal_gate_not_wired）**、exit 8；与报告 `steps`/`gate` 一致 |
| 3 | R2：design §2.2「契约」；单测覆盖复用键；pytest 全绿 | **PASS** | `docs/scan2pdf_design.md` L113「### 2.2 退出码（契约）」；`scan2pdf_v1.md` §11–13；pytest **23 passed** |
| 4 | 报告追加 R1/heldout；不改实现/数据；不 commit | **PASS** | 本节；只读；未 commit |

## R1.2 复用键实测表

| 用例 | 命令差异 | exit | mismatch / resume | out md5 |
|---|---|---|---|---|
| 同键重跑 | 无 | **8**（gate skipped） | resume=true；note 含 8 键；build.skipped=resume_existing | `928ea1f9…`（不变） |
| pages | `--pages 1-3` | **2** | `{"pages":["1-6","1-3"]}` | `928ea1f9…`（不变） |
| data | coords 文件追加空格（sha 变） | **2** | `{"coords_sha256":["99a0…","5cf3…"]}` | `928ea1f9…`（不变） |
| fix | `--fix /tmp/t162/fix.json` | **2** | `{"fix_sha256":["","bced…"]}` | `928ea1f9…`（不变） |

- 键字段：book / input_sha256 / fix_sha256 / coords_sha256 / lines_sha256 / mode / pipeline / pages（8 项全在 `resume_key` 与 note 中）。

## R1.3 heldout wz2（横排）

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz2.pdf --book wz2 \
  --out tmp_vert/scan2pdf/acc_wz2.pdf --data-dir data/wz2 --skip-ocr --pages 1-6
# exit 8（gate skipped）；pipeline=geom；build_geom rc=0；6/6 页
```

- 书型：**horizontal**（computed 初判 vertical → `coords_boxes` 修正；has_frame=false；595.3×935；783 页；multi=false；confidence 1.0；preflight 6 页 low）。
- 构建：`build_geom.py` rc **0**、out **110011 B**、6 页、页幅 592.8×931.5、page0 文本 20 字（含页眉/标题/署名）→ **geom 未失败**（不存在参数错）。
- 门禁：`skipped`（`horizontal_gate_not_wired`：v1 quality_gate 仅接 verify_vert）→ exit 8；v1 不自动交付横排，符合设计。

## R1.4 发现（低）

- **F1（低/中）**：复用键**不匹配时仍改写 `<out>.report.json`**（写入本次 mismatch 的 prev_key），导致后续合法重跑可能对「被改写后的 prev_key」再次 mismatch（本次实测：pages 1-3 mismatch 后，紧接着 1-6 重跑被误判 mismatch）。建议 mismatch 时**保留原 report**（或写 `<out>.mismatch.json`），只读记录；不影响本轮验收项（out 未覆盖、exit 2 正确）。


---

# #37 横排修复验收（t168 · round 2）

> 对象：t167（F1 `--src-pdf` 契约同步 + F3 横排 gate sidecar）
> 日期：2026-11-09 02:41–03:05；**只写本报告、未改实现/数据、未 commit**（HEAD `56bcaeb`）
> 证据：`src/tools/scan2pdf.py`（`34750bd6…`）、`test_scan2pdf.py`（`e198f79d…`）、`verify_geom.py`（`834ff6f4…`）、`tmp_vert/scan2pdf/wz4_deliver.pdf*`、`/tmp/t168/`

## t168.1 PASS/FAIL

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | wz4 全量 677 页；`verify_geom`（floor=85）PASS（pitch ≥99%、1:1、split 0、missing 0） | **PASS** | scan2pdf exit 0（resume 复用，677 页）；`verify_geom ... --src-pdf` rc=0：**677=677、pitch 99.6%（样本 671）、split 0、missing 0**；文本 560,324 / OCR 546,893 = 1.0246 |
| 2 | 历史 `wz4_optimized.pdf` vs 新产物：页数一致、逐页文本差异 ≤极小、页幅一致 | **PASS（t166 waiver）** | 页数 677=677；页幅 416.4×631.6 vs 416.4×632.6（Δ1pt）；文本 3/677 页相同、560,324 vs 596,004（median ratio 0.9647）→ 非「≤极小」；t166 已裁定 200dpi→144dpi 预期差异、不再要求一致（F2 waiver） |
| 3 | 横排门禁：gate JSON 不再 skipped；映射 pitch/溢出/页数、reasons 可读 | **PASS** | **`<out>.gate.json` + `.gate.md` 已生成**：version/book/mode/tool=verify_geom/verdict=PASS/reasons=[]/metrics{pitch_floor=85, pitch_ok_pct=99.6, pages=677, pages_src=677, split=0, missing=0, blank=32, overflow=6, exit=0}/gate；md 可读（结论/工具/pitch/pages/split/overflow/reasons） |
| 4 | wz2 6 页回归成功；两次同输入一致 | **PASS** | 两次 exit 0；6 页、1511 字全等、页幅一致；gate PASS（pitch 100%、6/6、blank 0、overflow 0） |
| 5 | 单测：fit_positional 调用/横排 gate/失败码；pytest 全绿；报告追加 | **PASS** | 单测存在（fit_positional、geom gate pass/fail、parse verify_geom）；pytest `test_scan2pdf + test_quality_gate` → **44 passed**；本节即报告追加 |
| 6 | 只写 docs/scan2pdf_acceptance.md；不改实现/数据；不 commit | **PASS** | 只改本文件；未改实现/数据；未 commit（HEAD `56bcaeb`） |

## t168.2 F1/F3 修复核对

- **F1（--src-pdf 契约）已修**：`verify_geom.py` usage/help 标注「必须带（缺省 200dpi 会误判，如 wz4=144dpi）」；`src/test/snapshots/README.md`、`docs/HANDOFF_20261024.md`、根 `optimize_book.py`（L148）均含 `--src-pdf`；任务契约命令也已带该参数 → 本轮 rc=0 PASS。
- **F3（gate sidecar）已修**：`<out>.gate.json`（1,102 B）含 `version/book/mode/tool/verdict/reasons/metrics/gate/note`；`<out>.gate.md`（201 B）可读；pitch/pages/split/overflow 全映射，`reasons=[]`（PASS）。

## t168.3 复现 / 字节绑定

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4   --out tmp_vert/scan2pdf/wz4_deliver.pdf --data-dir data/wz4 --skip-ocr
# exit 0（resume 复用；677 页；gate PASS）
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py tmp_vert/scan2pdf/wz4_deliver.pdf   data/wz4/wz4_spotting_coords.json data/wz4/wz4_spotting_lines.json --src-pdf source_pdf/wz4.pdf
# rc=0 PASS：677=677、pitch 99.6%、split 0、missing 0
/usr/bin/python3 -m pytest src/test/unit/test_scan2pdf.py src/test/unit/test_quality_gate.py -q  # 44 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/scan2pdf.py` | `34750bd6bc7ee77ff9e2974233921b60170ee8c8c74ed4cb377729eb9a38ade1` |
| `src/test/unit/test_scan2pdf.py` | `e198f79d749ededb92324f1dc99d95b525d891fb7a74ec80c2e85a85a8785565` |
| `src/test/verify_geom.py` | `834ff6f499d35f72ca681d1ac487dabe4862c00f47fc12dc94ebc777d021c865` |
| `tmp_vert/scan2pdf/wz4_deliver.pdf` | md5 `7625ff5b5a00459a500588fe3d466f73` |
| `output/wz4/wz4_optimized.pdf` | md5 `0966ace43b42b66ac4997faa7ccf2e17` |
| HEAD | `56bcaeb`（未 commit） |

## t168.4 结论

**t168 验收通过（PASS）**：F1（契约 `--src-pdf`）与 F3（横排 gate sidecar/reasons）已修并实测；wz4 全量 677 页构建 + `verify_geom --src-pdf` **PASS 99.6%**（1:1、split 0、missing 0）；横排 gate PASS 且 sidecar 字段齐全；wz2 6 页两次一致 PASS；pytest 44。历史产物文本差异按 t166 waiver（F2 低风险保留）。


---

# #37 R1 多纸型横排语义验收（t170）

> 对象：t169（geom 分支多纸型 review_required + R2 措辞）
> 日期：2026-11-09 02:58–03:20；**只写本报告、未改实现/数据、未 commit**（HEAD `56bcaeb`）
> 证据：`src/tools/scan2pdf.py`（`1eb40a86…`）、`test_scan2pdf.py`（`b611cc50…`）、`tmp_vert/scan2pdf/acc_wz4_r1.pdf*`、`/tmp/t170/`

## R1.1 PASS/FAIL

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 多纸型横排语义：review_required=true、auto_pass_forbidden=true、note 含分布；effective 规则（PASS→MANUAL_ONLY，REJECT 保持） | **PASS** | 合成 `book_type`（300x500:7 页 + 250x450:3 页）：`multi_format_clause` → review_required=true、auto_pass_forbidden=true、note/paper_distribution 含两纸型分布；`effective_verdict('PASS',True)='MANUAL_ONLY'`、`('REJECT',True)='REJECT'`、单纸型 PASS/REJECT 不变；pytest 单测 30 passed |
| 2 | wz4 单纸型回归：sidecar review_required=false、verdict PASS、pitch 99.6% 不变；wz2 6 页 PASS | **PASS** | wz4 exit 0、677 页；`acc_wz4_r1.pdf.gate.json`：verdict PASS、review_required=false、auto_pass_forbidden=false、multi_format=null、pitch_ok_pct=**99.6**、pages 677=677、split 0、missing 0、overflow 6、blank 32；wz2 6 页 exit 0、gate PASS（pitch 100%）、review_required=false |
| 3 | `<out>.gate.json/.md` 字段齐全（新增 review_required/multi_format）；无书专属分支 | **PASS** | sidecar keys：version/book/mode/tool/verdict/verdict_effective/review_required/auto_pass_forbidden/multi_format/multi_format_note/reasons/metrics/gate/note；md 首行含 `effective=PASS，review_required=False` + `multi_format：无（单纸型）`；`grep wz4|wz2|wz6|wz7 scan2pdf.py` 0 命中 |
| 4 | R2 措辞：不再声称「与竖排完全对齐」，差异列明 | **PASS** | `docs/scan2pdf_v1.md` L178/L204 改为「**核心字段对齐（非全 schema）**」，列明差异：横排无 schema_version/pdf_sha256/thresholds_source/expect_low；verdict 词表 PASS|REJECT（effective 才 MANUAL_ONLY）vs 竖排 AUTO_PASS|MANUAL_ONLY|REJECT；`grep 完全对齐` = 0 |
| 5 | 报告追加 R1 验收；不改实现；不 commit | **PASS** | 本节；只改本文件；未改实现/数据；未 commit（HEAD `56bcaeb`） |

## R1.2 合成多纸型证据

```text
effective_verdict('PASS', True)   -> MANUAL_ONLY (多纸型：横排 PASS 降为 MANUAL_ONLY…)
effective_verdict('REJECT', True) -> REJECT      (维持 REJECT，REJECT 更严、不弱化)
effective_verdict('PASS', False)  -> PASS
effective_verdict('REJECT', False)-> REJECT
multi_format_clause('PASS','MANUAL_ONLY',True,[300x500:7,250x450:3])
  review_required=True / auto_pass_forbidden=True
  paper_distribution='300x500:7页, 250x450:3页'
```

- 单测覆盖：多纸型横排 PASS→MANUAL_ONLY、REJECT 保持、review_required/note 分布、单纸型 review_required=false、md 字段断言；`test_scan2pdf.py` **30 passed**。

## R1.3 wz4 / wz2 实测

- wz4（单纸型）：exit **0**、677 页、gate **PASS**（pitch 99.6%、677=677、split 0、missing 0、overflow 6、blank 32）、review_required=false；产物 md5 `b621aac6…`。
- wz2（单纸型）：6 页、exit 0、gate PASS（pitch 100%、6/6）、review_required=false；sidecar 含全部新增字段。

## R1.4 复现 / 字节绑定

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out tmp_vert/scan2pdf/acc_wz4_r1.pdf --data-dir data/wz4 --skip-ocr
# exit 0；677 页；gate PASS；sidecar review_required=false
/usr/bin/python3 -m pytest src/test/unit/test_scan2pdf.py -q   # 30 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/scan2pdf.py` | `1eb40a86fd4e83c1fb611578befb521cedda57883357bd92332f67c54e150773` |
| `src/test/unit/test_scan2pdf.py` | `b611cc5051bd9d3e13fc68fb4e6b0ae87f0d7bfd132020a507433e3e65c7cf01` |
| `tmp_vert/scan2pdf/acc_wz4_r1.pdf` | md5 `b621aac6607609d2d5c04966dc28bddb` |
| HEAD | `56bcaeb`（未 commit） |

## R1.5 结论

**t170 验收通过（PASS）**：geom 多纸型语义与竖排一致（PASS→MANUAL_ONLY、REJECT 保持、review_required/auto_pass_forbidden/note 含分布）；wz4 单纸型 sidecar review_required=false、gate PASS、pitch 99.6% 不变；wz2 6 页 PASS；sidecar/md 字段齐全、无书专属分支；R2 措辞已改「核心字段对齐（非全 schema）」并列差异；pytest 30。

**限制（低）**：多纸型横排路径以「合成 book_type + 函数级/单测」验证（repo 无真实多纸型横排书），未做端到端多纸型 PDF 构建；建议后续用 heldout 多纸型横排书补 E2E。
