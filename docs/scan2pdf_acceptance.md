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


---

# OCR E2E 验收：ghbq 20-23（t173）

> 对象：t172（OCR raw→coords/lines 转换 + scan2pdf 接线）
> 日期：2026-11-09 18:21–18:40；**只写本报告、未改实现/数据、未 commit**（HEAD `516871f`）
> 证据：`src/tools/ocr_book.py`（`ae9848a0…`）、`scan2pdf.py`（`d47c4971…`）、`test_ocr_book.py`（`0010a1f3…`）、`output/test_ghbq/*`、`/tmp/t173/*`

## OCR.1 PASS/FAIL

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | ghbq 20-23 真 OCR（新 data-dir）：双模式成功；书型→horizontal；geom exit 0；gate PASS（4=4、pitch ≥99%） | **PASS** | 独立新目录 `/tmp/t173/_ocr_ghbq`：layout/spotting job **id 均与 t172 不同**（1132217563… / 1132218261…）；4 页；book_type 修正 **horizontal**；pipeline=geom、exit 0；gate **PASS pitch 100%、4=4、review_required=false** |
| 2 | 转换核对：≥5 行 raw rec_text 与产物逐字一致；2 条 poly 坐标换算 | **PASS** | page20 抽 5 行 raw rec_text 全部 **exact in product text**（5/5）；poly0/1：`scale=2*src_page/pruned`（595.28/1191、867.73/1736）→ 换算结果与 coords **逐值相等**（144.111→144.06 等） |
| 3 | 页号追溯：jobs.json pages 与 manifest 一致；key 0-based（20-23→19-22） | **PASS** | jobs：layout/spotting pages 均 `[19,20,21,22]`；manifest batches 两批同值、source_pages=104；coords/lines keys **19–22** |
| 4 | verify_geom 独立（--src-pdf）rc=0；resume 也能生成 coords/lines | **PASS** | `verify_geom --src-pdf` rc=0：4=4、pitch 100%（样本 4）；删除 coords/lines 后同命令 resume（无 --force）→ 两文件**重新生成**（18:24）、gate PASS、exit 0 |
| 5 | 报告追加；不改实现；不 commit | **PASS** | 本节；只改本文件；未改实现/数据；未 commit（HEAD `516871f`） |

## OCR.2 实测数据

- 书型：source page 595.28×867.73；OCR pruned 1191×1736；初判 vertical → **coords_boxes 修正 horizontal**。
- 构建：geom→fit_positional 两趟；4 页；exit 0；gate sidecar：verdict PASS、pitch 100%、pages 4=4、split 0、overflow 0、review_required=false。
- 转换：`scale_x=2*595.28/1191≈0.9996`、`scale_y=2*867.73/1736≈0.9997`；poly0 raw `[144.111,267.344]`→conv `[144.06,267.26]`（=2×pt）；poly1 同。
- 文本：page20 抽取 5 行 raw rec_text 全部逐字出现在产物文本层（未做归一化，5/5 exact）。
- 页号：jobs/manifest `[19,20,21,22]`、coords/lines keys 19–22（0-based 对齐）。
- resume：删除转换文件 → 重跑（无 --force）→ coords/lines 重新生成、gate PASS。

## OCR.3 复现 / 字节绑定

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/test_ghbq/acc_ghbq4.pdf --pages 20-23 --token-file /tmp/paddle_token --force
# exit 0；4 页；horizontal；gate PASS（pitch 100%、4=4）
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  output/test_ghbq/acc_ghbq4.pdf output/test_ghbq/_ocr_ghbq/ghbq_spotting_coords.json \
  output/test_ghbq/_ocr_ghbq/ghbq_spotting_lines.json --src-pdf source_pdf/ghbq.pdf
# rc=0 PASS（4=4、pitch 100%）
/usr/bin/python3 -m pytest src/test/unit/test_ocr_book.py src/test/unit/test_scan2pdf.py -q  # 33 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/ocr_book.py` | `ae9848a01262bb079cd345fab63340d28dad074d8335d235c642c1ee7b76e216` |
| `src/tools/scan2pdf.py` | `d47c4971b8c24034a4ced336417884eb5233cecf77ba8e0ea30c37634947ba5a` |
| `src/test/unit/test_ocr_book.py` | `0010a1f3c2f368edd60f59a0a552f1585cd11e99d32d45d3bbf43a30ca77917c` |
| `src/test/unit/test_scan2pdf.py` | `b611cc5051bd9d3e13fc68fb4e6b0ae87f0d7bfd132020a507433e3e65c7cf01` |
| HEAD | `516871f`（未 commit） |

## OCR.4 结论

**t173 验收通过（PASS）**：新目录独立真 OCR（job id 与 t172 不同）双模式成功，书型 horizontal、geom exit 0、gate PASS（4=4、pitch 100%）；转换坐标（2×pt 比例）与 raw 逐值一致、5/5 文本逐字入产物、页号 0-based 追溯一致；verify_geom --src-pdf rc=0；resume 能重新生成 coords/lines；pytest 33。


---

# JSONL 解析修复验收：ghbq 104 页（t176）

> 对象：t175（OCR raw JSONL 解析 + ghbq 104 页全书回归）
> 日期：2026-11-09 18:45–19:05；**只写本报告、未改实现/数据、未 commit**（HEAD `516871f`）
> 证据：`src/tools/ocr_book.py`（`0e049043…`）、`test_ocr_book.py`（`d5e94c40…`）、`output/ghbq_full/*`、`/tmp/t176/`

## JSONL.1 PASS/FAIL

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 独立验证 JSONL 解析：合成 JSONL（2 对象 3 页）与等价单 JSON，转换结果 keys/文本/坐标一致 | **PASS** | 合成 jobs.pages=[5,6,7]：JSONL（2 对象：2 页+1 页）与单 JSON 均得 keys **5/6/7**、lines `{5:甲,6:乙,7:丙}`；coords **逐值相等**（scale=2.0） |
| 2 | 全书回归：ghbq 104 页转换 coords/lines 各 104（keys 0..103）；scan2pdf --skip-ocr 构建 104 页、gate PASS（pitch ≥95%、split 0） | **PASS** | coords/lines **104/104**、keys **0..103**；scan2pdf `--skip-ocr --force` exit 0、pipeline geom、**104=104**、gate **PASS pitch 96.8%**、split 0、missing 0、review_required=false |
| 3 | JSONL 行数与页数关系；页序与全局 key 对齐 | **PASS** | spotting_000/001：**13 行 = 13 对象 = 50 页**（12×4+2）；spotting_002：1 行/4 页；layout 同构；jobs pages 0–49 / 50–99 / 100–103；manifest source_pages=104；coords keys 0..103 顺序对齐 |
| 4 | 报告追加；不改实现；不 commit | **PASS** | 本节；只改本文件；未改实现/数据；未 commit（HEAD `516871f`） |

## JSONL.2 实测数据

- JSONL 结构：50 页批返回 13 行 JSON，前 12 对象各 4 页、末对象 2 页（12×4+2=50）；4 页批为单行单对象。
- 转换：`_load_json_objects` 逐行解析并拼接 layoutParsingResults；单 JSON 兼容；coords/lines 104 页。
- 构建/门禁：`scan2pdf --skip-ocr --data-dir output/ghbq_full/_ocr_ghbq --force` → exit 0、104 页；gate `pitch 96.8%`（样本 94）、pages 104=104、split 0、missing 0、blank 2、overflow 25（均 ≤ 阈值，PASS）。
- 独立 `verify_geom --src-pdf`：rc=0 PASS（104=104、pitch 96.8%、split 0）。
- 单测：`test_ocr_book.py` **5 passed**；`test_ocr_book + test_scan2pdf` **35 passed**。

## JSONL.3 复现 / 字节绑定

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/acc_ghbq_full.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
# exit 0；104 页；gate PASS（pitch 96.8%、104=104、split 0）
/usr/bin/python3 -m pytest src/test/unit/test_ocr_book.py -q   # 5 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/ocr_book.py` | `0e04904366c35c37070b79c77dff654abebd03243a6d8ba5f8afb02b19ae8055` |
| `src/tools/scan2pdf.py` | `d47c4971b8c24034a4ced336417884eb5233cecf77ba8e0ea30c37634947ba5a` |
| `src/test/unit/test_ocr_book.py` | `d5e94c40ec4e8901ab5adeb3daae972d905c7c4a5d9bb1465941b8ad7a326d7f` |
| `output/ghbq_full/acc_ghbq_full.pdf` | md5 `084033d84493449f2bd3c9e0dd3ada3c` |
| HEAD | `516871f`（未 commit） |

## JSONL.4 结论

**t176 验收通过（PASS）**：JSONL（2 对象 3 页）与单 JSON 转换逐值一致；ghbq 104 页全书转换 coords/lines 各 104（keys 0..103），scan2pdf --skip-ocr 104=104、gate PASS（pitch 96.8%、split 0）；JSONL 行/页关系与页序对齐正确；pytest 5/35 passed。

**低风险备注**：全书 gate 的 blank 2 / overflow 25 仍在 PASS 阈值内（pitch 96.8% ≥95%），建议后续目视抽检这 25 页占位。


---

# 横排标定审计验收（t180）

> 对象：t179（HORIZONTAL_CALIB 实现：`<out>.calib.json` + 自检 warnings + scan2pdf 接入）
> 日期：2026-11-09 21:19–21:55；**只写本报告、未改实现/数据、未 commit**（HEAD `abacb9c`）
> 证据：`src/utils/geometry.py`（`8fc9c4d7…`）、`build_geom.py`（`9a92b541…`）、`scan2pdf.py`（`3f2beb95…`）、`test_horizontal_calib.py`（`af7318ab…`）、`spec/governance/HORIZONTAL_CALIB.md`（`1df6161c…`）、`tmp/t180/*`

## CAL.1 PASS/FAIL

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 复跑 ghbq 4 页 + wz4 20 页，`<out>.calib.json` 存在且 schema 完整 | **PASS** | ghbq full (104p)、ghbq 4p、wz4 20p、wz4 full 四份 calib：22 个顶层必填字段 + 8 个嵌套对象必填子字段**零缺失**；schema=`horizontal-calib-v1`、status=measured |
| 2 | 数值：wz4 dpi≈138、page_size 来自 src（覆盖率<95% 降级）、font≈10.7；ghbq 同口径；对照 spec §5 | **FAIL（任务前提数值写反）** | 实际：**wz4 full = 144 / coords / font 10.7 / baseline 17.8 / coverage 0.9991**（与 spec §5 一致，非 138/src）；**wz4 20p 子集 = 143 / coords / 11.3 / coverage 1.006**；**ghbq full = 139 / coords / 16.5 / 34.2 / coverage 1.013**（与 spec §5 一致）；**ghbq 4p = 138 / src_pdf / 16.6 / coverage 0.9239 degraded**——验收文字里的「138 + src 降级」是 **ghbq 4p** 而非 wz4（F3） |
| 3 | 自检 warn 分支（DPI 偏差/FONT 越界/BASELINE/FONT 越界/coverage 降级）出现且不阻断；正常书 warnings=[] | **PASS** | 单测 `test_selfcheck_warn_branches` 造出 `dpi_residual_large`/`font_out_of_range`/`baseline_font_ratio_out`/`page_size_overcoverage`/`page_size_coverage_low`/measure/margin/cw/pitch/full 全部分支且 verdict=warn；真实 `PAGE_COVERAGE_THRESHOLD=1.02` 构建 → warnings `[baseline_font_ratio_out,page_size_coverage_low]`、**build rc=0、104 页、gate PASS**；ghbq 自然 baseline warn 不阻断；wz4 full warnings=[]、selfcheck pass |
| 4 | scan2pdf report calib 块与 sidecar 一致；gate 不因 calib 警告误判 REJECT | **PASS** | `acc_ghbq_calib.pdf.report.json.calib` 与 `.calib.json` 字段逐项一致（font 16.5 / baseline 34.2 等）；report/gate sidecar verdict **PASS**、`reasons=['calib_warn:baseline_font_ratio_out']`、`calib_warnings=['baseline_font_ratio_out']`、exit 0 |
| 5 | 报告追加；不改实现；不 commit | **PASS** | 本节；只改本文件；未改实现/数据；未 commit |

## CAL.2 captain 追加：ghbq 绝对字号/行距 vs 源图墨迹

**结论：产物物理尺寸与源图一致（≤3.7%），convert_raw_dir 的 2×pt scale 公式没有错；calib.json 与最终 fit_positional 产物自洽。17.8pt 是 wz4 的基线，不是 ghbq。**

| 项 | 源图实测 | 产物实测 | 误差 |
|---|---|---|---|
| ghbq p20 行距（行中心投影） | **33.0pt**（300dpi 渲染 2481×3616 / 19 bands；native 1442×2102 同 33.02） | **34.21pt** | **+3.7%** |
| ghbq p20 墨带高（≈字高） | **16.08pt**（native 15.69） | span 字号 **16.44pt** | **+2.2%** |
| ghbq p101 行距 / 墨带高 | **33.0 / 16.32pt** | **34.21 / 16.44pt** | +3.7% / +0.7% |
| ghbq 页幅 | 源 595.28×867.73pt | 600.75×866.75pt | 宽 +0.9% / 高 −0.1% |
| wz4 full 行距 / 字号 | （源同量级） | **17.98 / 10.66pt** | 与 calib 17.8/10.7 匹配 |

- **源图尺度确认**：ghbq 嵌入图 1442×2102（595×868pt → 2.42px/pt≈174dpi，不是 300dpi 原图；300dpi 渲染是 2481×3616）。按 300dpi 渲染并用 4.17px/pt 换算，行距 33.0pt、墨带高 16.1pt——与产物 34.2/16.44 同量级；captain 的 16.8pt/10–11pt 很可能是**把墨带高当行距**（16.8≈墨带高）或用了 150dpi 渲染却按 300dpi 换算（正好减半），不是源书真实字号。
- **2×pt 换算验证**：pruned 1191×1736 vs 原图 1442×2102（0.826×）；raw poly × `2*pdf_w/pruned_w` 得 legacy 2×pt。把 pruned 页渲染到 1191px 宽后叠 raw poly，**poly 与首行墨迹逐像素对齐**；行宽 887.3 units → 443.5pt（24 字≈18.5pt/字含标点），与源墨迹一致。→ scale 公式正确。
- **DPI 139 的含义**：legacy coords 名义 2 units/pt（≈144dpi），139 是 calibrate 由行 y 范围（非整页）反推的值，导致 FONT 16.5 略高于源墨带 16.1（+2.5%）；不是 174dpi 源图尺度错误。
- **17.8pt 归属**：wz4 calib BASELINE=17.8、wz4 产物行距 17.98；ghbq calib BASELINE=34.2、产物 34.21。captain 的「37px@150dpi=17.76pt」精确等于 **wz4** 行距，不是 ghbq。

## CAL.3 发现（must-fix / 低风险）

- **F1（中，must-fix）单趟 `build_geom.py` 的 `<out>.calib.json` 不描述该 out 的真实渲染**：直接跑 build_geom ghbq → calib `139/16.5/34.2`，但该 PDF 实测行距 **20.65pt**（单趟压缩进版心）；只有 fit_positional 两趟最终产物才是 34.21。当前 build_geom 默认写 `<out>.calib.json`，用户会误读。建议：calib 增加 `render{page_pt,font_pt,pitch_pt,pass}`（由产物 PDF 回填）或只在 fit_positional pass2 写/覆盖；`selfcheck.pitch_error_pct` 同样应由 verify_geom 回填（当前用 calibrate 中位，ghbq 0.114 vs verify 0.7%）。
- **F2（低）`page_size.*_pt` 单位是 TeX bp，不是 PDF pt**：ghbq 603×870（calib）→ PDF 600.75×866.75（×0.996264）；wz4 418×634→416.44×631.63。字段名 `_pt` 易误解，建议加 `unit=bp` 或同时给 `render_page_pt`。
- **F3（低）任务验收数值前提写反**：wz4 实为 144/coords/10.7；138/src/16.6 是 ghbq 4p；已在上表按实际值核对（spec §5 与 full 版本一致）。
- **F4（低）coverage>1 语义**：ghbq 1.013 表示 coords 页 603bp 比源 595pt 宽 1.3%，在 `[0.5,1.5]` sanity 内、且低于 >1.02 的 overcoverage warn 阈值，不告警合理；降级分支 ghbq 4p（0.9239<0.95）正确切到 src_pdf 并写 `page_size_coverage_low`。
- **F5（低）warn 样本覆盖**：单测覆盖全部分支；真实构建仅验证了 coverage 降级与自然 baseline warn；DPI/FONT 越界建议补一条端到端 fixture（当前函数级足够）。

## CAL.4 复现 / 字节绑定

```bash
cd /opt/test
# 契约
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/acc_ghbq_calib.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
# exit 0；gate PASS（calib_warn:baseline_font_ratio_out 不阻断）
# 4 页 / 20 页
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq --out /tmp/t180/ghbq_4.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --pages 20-23 --force
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 --out /tmp/t180/wz4_20.pdf --data-dir data/wz4 --skip-ocr --pages 1-20 --force
/usr/bin/python3 -m pytest src/test/unit/test_horizontal_calib.py -q   # 4 passed（+scan2pdf 34 passed）
```

| 文件 | sha256 / md5 |
|---|---|
| `src/utils/geometry.py` | `8fc9c4d7d3d4e298ff464a3595421b965f7c62873543b805a80ed4e9a2090bb3` |
| `src/pipelines/build_geom.py` | `9a92b5411b94161f733b805d187a1a7243cbc76d875bb9bd1a8e38ebe0f783ba` |
| `src/tools/scan2pdf.py` | `3f2beb95cc4a5da9961e04f02ea6e50f5937e97faacfffd68f4643b4ef0c9fd2` |
| `src/test/unit/test_horizontal_calib.py` | `af7318ab9a8ef49a17f4814bd953926dbc9fc12f7972c9ffeb77454605a56719` |
| `spec/governance/HORIZONTAL_CALIB.md` | `1df6161c14ad9602e10d89d2e973840d5d02ed32e12e6ebbb2fd461a5bdb1a4a` |
| HEAD | `abacb9c`（未 commit） |

## CAL.5 结论

**t180 任务判定 FAIL（F1 must-fix；任务数值前提 F3）**：calib schema/自检 warning/scan2pdf 接入与 gate 非误判均通过；ghbq 物理尺寸与源图一致（行距 +3.7%、字高 +2.2%，≤5%），2×pt scale 公式与 DPI 反推无根因错误，17.8pt 属 wz4。但单趟 build_geom 的 `<out>.calib.json` 与真实渲染不符（34.2 vs 20.65）——按 captain 口径属「calib 输出字段没反映真实渲染参数」的 must-fix；另 page_size 单位 bp 需标注。修复后（render 段或仅 fit_positional 写 calib + 单位标注）再交 t181 终审。

---

## 横排标定验收文字更正（t182）

> 依据 t180 CAL.3 F3 / t182 修复；不改实现结论，只更正数值归属。

- **wz4 全书**：dpi **144** / `source_of_page_size=coords` / font **10.7** / baseline 17.8（与 spec §5 一致；**不是** 138/src）。
- **ghbq 4 页**：dpi **138** / `source_of_page_size=src_pdf`（coverage 0.9239 降级）/ font 16.6。
- **ghbq 全书**：dpi **139** / `coords` / font 16.5（与 spec §5 一致）。
- 原验收文字「wz4 dpi≈138、page_size 来自 src」系把 **ghbq 4p** 的数值写到 wz4 名下；两书 full 版本均与 spec §5 对齐。


---

# 横排标定审计验收（t183 · round 2）

> 对象：t182（calib render 回填 + 单位/文字更正 + FONT_SCALE 越界 fixture）
> 日期：2026-11-09 21:32–21:50；**只写本报告、未改实现/数据、未 commit**（HEAD `abacb9c`）
> 证据：`src/utils/geometry.py`、`build_geom.py`、`scan2pdf.py`、`test_horizontal_calib.py`、`output/ghbq_full/ghbq_calib.pdf*`、`/tmp/t183/*`

## CAL2.1 PASS/FAIL

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 复跑 ghbq 4 页 + wz4 20 页；`<out>.calib.json` 存在且 schema 完整 | **PASS** | ghbq full (104p)、ghbq 4p、wz4 20p、direct build 四份 calib：22 顶层 + `render`（page_pt/font_pt/pitch_pt/pass/unit）全在；`page_size.unit='bp'`；schema=`horizontal-calib-v1` |
| 2 | 数值核对 + spec §5 对照 | **PASS（任务文字已由 t182 更正）** | **wz4 full = 144 / coords / font 10.7 / baseline 17.8 / coverage 0.9991**（spec §5 一致；t182 已更正「wz4≈138/src」）；**ghbq full = 139 / coords / 16.5 / 34.2 / 1.013**（spec §5 一致）；**ghbq 4p = 138 / src_pdf / 16.6 / coverage 0.9239 degraded**；**wz4 20p = 143 / coords / 11.3 / 1.006**；数值与 spec/产物三方向对齐 |
| 3 | 自检 warn 分支出现且不阻断；正常书 warnings=[] | **PASS** | `test_horizontal_calib.py` **5 passed**（含 `test_build_geom_font_scale_out_of_range_not_blocked`：FONT_SCALE=3 真实构建 rc=0、calib `font_out_of_range`、render 段存在）；ghbq 4p 自然 3 warnings（src_pages_diff / baseline_font_ratio_out / page_size_coverage_low）但 **exit 0、gate PASS**；wz4 full warnings=[]、selfcheck pass |
| 4 | report calib 块与 sidecar 一致；gate 不因 calib 警告误判 REJECT | **PASS** | ghbq full/4p：report.calib.render == sidecar.render（pp 600.75×866.75、font16.44、pitch34.21）；ghbq full gate **PASS**（reasons 含 `calib_warn:baseline_font_ratio_out` 但不 reject）；ghbq 4p gate PASS；wz4 20p gate REJECT 的 reasons 是 `verify_geom_fail/pitch_below_floor`（pitch 83.3% TOC 子集），**非 calib 警告** |
| 5 | 报告追加；不改实现；不 commit | **PASS** | 本节；只改本文件；未改实现/数据；未 commit |

## CAL2.2 F1/F2/F3/F4/F5 修复核对

- **F1（must-fix）已修 —— render 回填**：
  - 单趟 `build_geom` ghbq：calib `font=16.5/baseline=34.2`，`render={page 600.75×866.75, font 16.44, pitch **20.65**, pass=null, unit=bp}` → 与直跑 PDF 实测 20.65 一致（不再把 34.2 冒充渲染）。
  - fit_positional/scan2pdf ghbq full：`render={page 600.75×866.75, font 16.44, pitch **34.21**, pass=true}`、`selfcheck.pitch_error_pct=3.2`、`pitch_error_source=verify_geom` → 与产物实测 34.21/16.44 一致。
  - wz4 20p：render pitch 18.52 = 产物 18.54，pass=false（pitch 83.3% 子集如实反映）。
- **F2（单位）已修**：`page_size.unit='bp'`、`render.unit='bp'`；spec §4 示例同步（603bp→600.75pt 不再被误读）。
- **F3（文字）已修**：docs 增 t182 更正节（wz4 full 144/coords；ghbq 4p 138/src；ghbq full 139/coords）。
- **F4（coverage>1）已补**：spec §2.2 明确「coverage>1 允许至 1.02，属 DPI 估计/坐标边界误差」；ghbq 1.013 不告警合理。
- **F5（E2E fixture）已补**：`test_build_geom_font_scale_out_of_range_not_blocked` 真实构建 FONT_SCALE=3 → rc0 + calib warning + render 段。

## CAL2.3 复现 / 字节绑定

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/ghbq_calib.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
# exit 0；104 页；gate PASS（pitch 96.8%）；calib render pitch 34.21/font 16.44/pass true
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 --out /tmp/t183/wz4_20.pdf --data-dir data/wz4 --skip-ocr --pages 1-20 --force
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq --out /tmp/t183/ghbq_4.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --pages 20-23 --force
/usr/bin/python3 -m pytest src/test/unit/test_horizontal_calib.py -q   # 5 passed（+scan2pdf 35 passed）
```

| 文件 | sha256 / md5 |
|---|---|
| `src/utils/geometry.py` | `8fc9c4d7…` 系（t182 后另有改动，以本轮报告复算为准） |
| `src/pipelines/build_geom.py` | 同上（render 回填） |
| `src/tools/scan2pdf.py` | 同上（render.pass/pitch_error_source） |
| `src/test/unit/test_horizontal_calib.py` | 5 passed（含 FONT_SCALE fixture） |
| `output/ghbq_full/ghbq_calib.pdf` | render pitch 34.21 / font 16.44 / page 600.75×866.75 |
| HEAD | `abacb9c`（未 commit） |

## CAL2.4 结论

**t183 验收通过（PASS）**：t182 的 F1（render 回填）/F2（单位）/F3（文字）/F4（coverage 说明）/F5（E2E fixture）全部实测关闭；schema 完整、warnings 非阻断、report/sidecar 一致、gate 不因 calib 警告误判；ghbq 产物物理尺寸与源图仍 ≤3.7%（t180 已核）。**低风险备注**：wz4 20p 子集 render.pass=false/pitch_error 16.7% 属 TOC 页子集（t179 已登记，非 calib 缺陷）；直接 build_geom 的 `render.pass=null`（只有 scan2pdf 能填 true/false），建议后续文档注明。


---

# GMPG 泄漏修复验收（t189）

> 对象：t188（fit_common pass2 移除 VERIFY_MARK，交付产物无 GMPG）
> 日期：2026-11-09 23:34–23:55；**只写本报告、未改实现/数据、未 commit**（HEAD `00a44f7`）
> 证据：`src/calibration/fit_common.py`（`8883395b…`）、`test_fit_common_verify_mark.py`（`85df09c5…`）、`test_fit_common_cleanup.py`（`9081d73d…`）、`output/ghbq_full/acc_ghbq_nomark.pdf*`、`output/wz4/acc_wz4_nomark.pdf*`

## GMPG.1 PASS/FAIL

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 重建 ghbq 104 + wz4 677：`get_text()` GMPG **0**（逐页），页数不变 | **PASS** | ghbq **104=104**、GMPG total **0**（含 GMPG 页 **0**）；wz4 **677=677**、GMPG total **0**（0 页）；旧产物对照 ghbq 104 处/104 页、wz4 677 处/677 页 |
| 2 | 与修复前产物比，除 GMPG 行外逐页文本相同（字符差可解释） | **PASS** | 逐页逐字（删除 `GMPG<k>ZZ`+空白归一）**0 diff**（ghbq 0/104、wz4 0/677）；原始字符差 ghbq **930 = 826（104 个标记 7–9 字符）+104 换行**、wz4 **6660 = 5983（677 标记）+677 换行**，完全可解释 |
| 3 | verify_geom --src-pdf rc=0 PASS，pitch 不变；确认「按序号 1:1」回退 | **PASS** | ghbq rc=0：104=104、pitch **96.8%**；wz4 rc=0：677=677、pitch **99.6%**；stdout 均含 `对齐: 按序号 1:1 (输出未含 GMPG 标记,建议用 VERIFY_MARK=1 重渲以精确对齐)` |
| 4 | scan2pdf gate PASS、exit 0；calib render 仍正确 | **PASS** | ghbq exit0、gate PASS 96.8%、warnings=[baseline_font_ratio_out,toc_low_sample]、calib_fail=[]；wz4 exit0、gate PASS 99.6%、warnings=[]/calib_fail=[]；render：ghbq 600.75×866.75/font16.44/pitch34.21/pass，wz4 416.44×631.63/font10.66/pitch17.67/pass（实测 34.21/17.62，均吻合） |
| 5 | 单测：两趟 env 断言；pytest 全绿 | **PASS** | `test_fit_common_verify_mark.py` 4 passed（pass1 `[True,False]`、pass2 移除继承 shell 的 VERIFY_MARK、classic 同源、真 PDF 无标记回退「按序号 1:1」）；`test_fit_common_cleanup` 2 + `test_scan2pdf` 31 + `test_horizontal_calib` 6 = **43 passed**；全量 unit **717 passed**（184.64s） |
| 6 | 报告追加；不改实现；不 commit | **PASS** | 本节；只改本文件；未改实现/数据；未 commit（HEAD `00a44f7`） |

## GMPG.2 复现 / 字节绑定

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/acc_ghbq_nomark.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/acc_wz4_nomark.pdf --data-dir data/wz4 --skip-ocr --force
# 均 exit 0；ghbq 104 页 / wz4 677 页
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py output/wz4/acc_wz4_nomark.pdf \
  data/wz4/wz4_spotting_coords.json data/wz4/wz4_spotting_lines.json --src-pdf source_pdf/wz4.pdf
# rc=0 PASS：677=677、pitch 99.6%、按序号 1:1 回退
/usr/bin/python3 -m pytest src/test/unit/test_fit_common_verify_mark.py -q   # 4 passed
/usr/bin/python3 -m pytest src/test/unit -q                                # 717 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/calibration/fit_common.py` | `8883395b932f594308f9492efa95b5b23d54acf7863404578a16b68f2280ca0e` |
| `src/test/unit/test_fit_common_verify_mark.py` | `85df09c52d7fa2a9af1e037a85288c16f3f0479f34dbdaa391c0c919bd86fe0b` |
| `src/test/unit/test_fit_common_cleanup.py` | `9081d73dadf310a65c273d052b4cecbb21ae86a25722c57267a5e40b14f24fdf` |
| `output/ghbq_full/acc_ghbq_nomark.pdf` | md5 `44eb50ee1780529abf23c09a3223b25e` |
| `output/wz4/acc_wz4_nomark.pdf` | md5 `69845cc69e77ea7d0d5d25fa33aa7db1` |
| HEAD | `00a44f7`（未 commit） |

## GMPG.3 结论

**t189 验收通过（PASS）**：交付产物 GMPG **0**（逐页），页数/文本（除标记行）/pitch/gate 全部不变；verify_geom 无标记按序号 1:1 回退且 PASS；calib render 与产物实测一致；两趟 env 单测与全量 unit 717 passed。无 must-fix；建议后续把 `VERIFY_MARK` 用途写入 PIPELINE_BEHAVIOR（t188 已登记待同步）。


---

# LAYJSON + 图片 passthrough 验收（t193）

> 对象：t192（LAYJSON 接线 + 图片/图块 passthrough）
> 日期：2026-11-10 21:03–21:25；**只写本报告、未改实现/数据、未 commit**（HEAD `f82cafc`）
> 证据：`src/pipelines/build_geom.py`（`a1160b5d…`）、`src/tools/ocr_book.py`（`2a227382…`）、`test_page_image.py`（`5f140040…`）、`spec/governance/PAGE_IMAGE_LAYOUT.md`（`70060c7a…`）、`output/ghbq_full/acc_ghbq_img.pdf*`、`output/wz4/acc_wz4_nojson.pdf*`、`tmp_vert/scan2pdf/t193_p2_compare.png` / `t193_p3_compare.png`

## LAY.1 PASS/FAIL

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | LAYJSON：页 key/页序/jobs 对齐、JSONL 兼容；抽样 bbox 与 raw pruned 一致（≤1px） | **PASS** | layout 104 页、keys **0..103** 顺序；jobs layout pages `[0..49]` 等、manifest `layout_pages=104/source_pages=104/warnings=[]`；raw layout_000 为 **13 对象→50 页** JSONL，转换正常；p0/p1/p2 抽样 blocks bbox 与 raw `block_bbox` **maxerr=0.00px**（≤1px） |
| 2 | ghbq：p1 封面照可见、p2 条形码可见、≥2 图版页可见（与源并排）；chars ≥现状、GMPG=0、104=104、gate 96.8 不降 | **FAIL（p3 图内文字可见）** | 图像：p1 2 图（1653×1121 封面 + 680×93 页脚）、p2 条形码 429×343、p3 图版 1653×1136 均嵌入；chars **43,945 ≥ 43,913**（+32）、GMPG **0**、104=104、gate **PASS 96.8%**。**但 p3 两条 doc_title 文本 span 为 type 0（可见）且落在 image rect 内**：`马尔巴乔夫与` 重叠 7804pt²、`一人道的民主的社会主义”` 重叠 6825pt²，直接压在照片上（OCR 错字可见）；源页 title 在照片上方白区，产物标题被流式下移进图内 → 违反 spec §2「图内文字 invisible」 |
| 3 | 零回归：wz4 不传 LAYJSON → 文本/页数/gate 99.6 与 HEAD 一致；wz2 6 页 PASS | **PASS** | wz4：677=677、chars **554,341 = 旧产物**、逐页文本 **全等**、gate PASS 99.6、layout 0 页；wz2 6 页 exit0、gate PASS 100%（layout 0） |
| 4 | 开关默认关：不传 LAYJSON/不开开关时输出与 HEAD 相同（至少文本+页数+门禁） | **PASS（直跑）/ FAIL（scan2pdf 自动 LAYJSON）** | 直跑 `build_geom` 无 LAYJSON、flags=0：104 页、48,332 chars，与 t183 旧直跑 **逐页文本全等**；但 scan2pdf `LAYOUT_FIGS=0 LAYOUT_TOC=0 LAYOUT_HEADINGS=0`（仍自动传 LAYJSON）→ 104 页、chars **43,916 vs 旧 43,913（+3）**：p11 `...26`→`...261`、p104 `"false"`→`"false92"`（layout 页码/数字混入）→ 默认关不等价（F3） |
| 5 | 单测：converter/图块裁剪/回退；pytest 全绿；报告追加；不改实现；不 commit | **PASS** | `test_page_image.py` **3 passed**、`test_ocr_book+test_scan2pdf` **38 passed**（相关 41）；全量 unit **722 passed**；本节为报告追加；未改实现/数据；未 commit |

## LAY.2 发现

- **F1（高，must-fix）p3 图内文字可见**：image rect y325–732，文本 span y399–476/453–476 为 type 0；重叠面积 7804/6825pt²；OCR 错字「马尔巴乔夫 / 一人道的…」可见。根因：image BG overlay 不占流，doc_title 流式落点被推入图内；且 t192 残留「PAGE_IMAGE_FULL_RATIO 自动整页阈值未接」（p3 图块面积 818/1736=47% ≥0.40，但仅显式 PAGE_IMAGE_PAGES 生效）。修复建议：按渲染 bbox 与 image rect 相交的文本置 `3 Tr` 不可见（或对 image-page 用整页 overlay + 文本不可见；注意 p1 同约 46% 面积但不能整页 overlay，否则会丢封面标题——按 OCR 文本/图像页判据区分），并加 E2E trace type 断言。
- **F2（低）p2 ISBN 文本与条形码图内文字视觉重复**：chart block 本身 text 空；OCR ISBN 行在 layout chart bbox 之外（下方），但渲染 span bbox 与 chart rect 顶边重叠 1287pt²（8pt 条带），且源页本身既有条形码内 ISBN、又有外部 ISBN 行——重复来自源图，不是文本层复制。可接受；若要求更严，可把与 image rect 相交的文本置隐。
- **F3（中）scan2pdf 自动 LAYJSON 下默认关不等价**：flags 全 0 仍 +3 字符（p11/p104），说明 layout 页码/数字未受 LAYOUT_TOC/HEADINGS 门控；直跑无 LAYJSON 则全等。建议 scan2pdf 在 flags=0 时不自动传 LAYJSON，或 build_geom 的 layout 页码/标题仅在对应开关开启时生效。
- **F4（通过）p1 封面**：title/author 文本在 image rect 上方（y≤290 vs image y≥330，重叠 0），照片可见；重排文字与源图位置/字体有差异但未压图，符合「图外 visible」。
- **F5（低）** p2/p3 对照图：`tmp_vert/scan2pdf/t193_p2_compare.png` / `t193_p3_compare.png`（左源/右产物）。

## LAY.3 复现 / 字节绑定

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/acc_ghbq_img.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/acc_wz4_nojson.pdf --data-dir data/wz4 --skip-ocr --force
/usr/bin/python3 -m pytest src/test/unit/test_page_image.py src/test/unit/test_ocr_book.py src/test/unit/test_scan2pdf.py -q  # 41 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/pipelines/build_geom.py` | `a1160b5da87434419a1a0ddba15152521170f9bbdbb6aca9a628c3818aab6807` |
| `src/tools/ocr_book.py` | `2a2273827036b93203a201045b39ea731f1c25a11b0070c1b43daf825ccfb1b6` |
| `src/test/unit/test_page_image.py` | `5f140040788ecc3481ffd75bf2e49914576f53b15e7c97a6c04a6d1a824059d7` |
| `spec/governance/PAGE_IMAGE_LAYOUT.md` | `70060c7abbca44ed7e4552e243e65efc5349dc321f697a037234b09f437019ce` |
| `output/ghbq_full/acc_ghbq_img.pdf` | md5 `303fd263e4ea2bd0436f23bd78a5e05b` |
| HEAD | `f82cafc`（未 commit） |

## LAY.4 结论

**t193 判定 FAIL（F1 高，p3 图内文字可见）**：LAYJSON 转换/页序/bbox（0px 误差）、ghbq 图像可见、chars+32/GMPG0/104=104/gate96.8、wz4/wz2 零回归、直跑无 LAYJSON 全等、tests 722 均通过；但 p3 产物把可见 OCR 标题压在照片上（type 0，重叠 7804/6825pt²），违反 spec §2「图内文字 invisible」；另 scan2pdf 自动 LAYJSON 下 flags=0 仍 +3 字符（F3）。修复 F1（可见文本置隐/图像页处理）与 F3（layout 门控）后复验。


---

# LAYJSON + 图片 passthrough 验收（t196 · round 2）

> 对象：t195（图内文本 3 Tr / image-page / 默认不传 LAYJSON）
> 日期：2026-11-10 21:24–21:45；**只写本报告、未改实现/数据、未 commit**（HEAD `f82cafc`）
> 证据：`build_geom.py`（`526dc654…`）、`scan2pdf.py`（`0986328f…`）、`ocr_book.py`（`2a227382…`）、`output/ghbq_full/ghbq_img.pdf*`、`/tmp/t196/ghbq_figs.pdf*`、`tmp_vert/scan2pdf/t196_p1/p2/p3_compare.png`

## LAY2.1 PASS/FAIL

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | LAYJSON：页 key/页序/jobs 对齐、JSONL 兼容；blocks bbox 与 raw pruned 一致（≤1px） | **PASS** | layout 104 页 keys 0..103 顺序；raw layout_000 **13 对象→50 页** JSONL；p0/p1/p2 抽样 13 blocks **maxerr=0.00px**；manifest layout_pages=104/source_pages=104/warnings=[] |
| 2 | ghbq：p1 封面照、p2 条形码、≥2 图版页可见；chars ≥现状、GMPG=0、104=104、gate 96.8 | **PASS（需 `--layout` 开启）** | 默认（无 `--layout`）按 t195 F3 layout disabled、无图、chars 43,913 与 HEAD 全等；`--layout`：p1 封面 1653×1121、p2 条形码 429×343、p3 图版 1653×1136 均嵌入；chars **43,954 ≥ 43,913**、GMPG 0、104=104、gate PASS 96.8；**p3 两条 doc_title 现为 type 3（invisible）** |
| 3 | 零回归：wz4 不传 LAYJSON → 文本/页数/gate 99.6 与 HEAD 一致；wz2 6 页 PASS | **PASS** | wz4：677=677、text **逐字全等**（597,184 chars）、gate PASS 99.6、layout disabled；wz2 6 页 gate PASS 100% |
| 4 | 开关默认关：不传 LAYJSON/不开开关时与 HEAD 相同（文本+页数+门禁） | **PASS** | 默认 ghbq：104 页、chars 43,913、**逐页文本与 HEAD 全等**、gate 96.8、layout disabled（report.layout.requested=False）；wz4 同上 |
| 5 | 单测：converter/裁剪/回退；pytest 全绿；报告追加；不改实现；不 commit | **PASS** | `test_ocr_book+test_scan2pdf+test_page_image` **41 passed**；全量 unit **722 passed**；本节报告；未改实现/数据；未 commit |

## LAY2.2 F1/F3 修复核对

- **F1（可见文字压图）已修**：`--layout` 产物 p3 两条 doc_title `get_texttrace().type=3`（不可见），text 层保留（可搜）；p1 标题/作者在 image rect 上方 type0（可见），p1 出版者 span 与 image rect 相交 2432pt² → type3；p2/p3 图均嵌入。
- **F3（默认关）已修**：默认 ghbq/wz4/wz2 均 `layout disabled`，ghbq/wz4 逐页文本与 HEAD **全等**；仅显式 `--layout` 或 LAYOUT_* 非 0 才传 LAYJSON。

## LAY2.3 残留（非阻断）

- **F1（中）p3 标题被过度隐藏**：p3 doc_title 在 layout 中位于 image bbox **上方**（[101,243,1051,451] vs image [0,653,1191,1471]），但 t195 image-page 策略把整页文字置 type3 → 产物 p3 只剩照片，源页上方标题不可见（文本层仍可搜）。严格按 spec §2「图外 visible」应只隐藏与 image rect 相交的 span，或把标题定位回 image 上方；建议后续修。
- **F2（低）p2 ISBN span 仍有 8pt 条带与 chart rect 相交（1287pt²，type0）**；chart block text 空，源页本身同时有条形码内 ISBN 与外部 ISBN 行 → 视觉重复来自源图，不是文本层复制。
- **F3（低）p1 页脚图丢失**：t192 p1 有 2 图（封面+页脚图 680×93），t195 输出仅 1 图（封面）；出版者文字 span 为 type3，p1 页脚 logo 区域空白。验收只要求封面照可见，登记为 passthrough 残留。
- **F4（低）任务契约默认命令不含 `--layout`**：默认构建按设计不启用图片；图片验收需显式 `--layout`（或 LAYOUT_FIGS=1），建议任务/文档写明。
- **F5（低）spec PAGE_IMAGE_LAYOUT §4「默认关=不传 LAYJSON」文字未同步**（t195 已登记，不在其 in-scope）。

## LAY2.4 复现 / 字节绑定

```bash
cd /opt/test
# 默认（layout disabled，与 HEAD 等价）
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/ghbq_img.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
# 图片验收（显式 --layout）
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out /tmp/t196/ghbq_figs.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force --layout
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/acc_wz4_nojson.pdf --data-dir data/wz4 --skip-ocr --force
/usr/bin/python3 -m pytest src/test/unit/test_ocr_book.py src/test/unit/test_scan2pdf.py src/test/unit/test_page_image.py -q  # 41 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/pipelines/build_geom.py` | `526dc654b981824c411b021ab5326a237b41e353bdb3eb04a2e614d93e3aeb79` |
| `src/tools/scan2pdf.py` | `0986328f70cf40ad44b0bb1320189eca1b21cf45e68a7c4c2bfc5133524f69a6` |
| `src/tools/ocr_book.py` | `2a2273827036b93203a201045b39ea731f1c25a11b0070c1b43daf825ccfb1b6` |
| `output/ghbq_full/ghbq_img.pdf`（默认） | md5 `dbf16536a58be03d8aa9a37411c5019d` |
| `/tmp/t196/ghbq_figs.pdf`（--layout） | md5 `5dca8f0b33f01dae04b2dd86086da2c3` |
| `output/wz4/acc_wz4_nojson.pdf` | md5 `1ce8621f16cbb110a222bf4de21fcf88` |
| HEAD | `f82cafc`（未 commit） |

## LAY2.5 结论

**t196 验收通过（PASS）**：LAYJSON 转换（JSONL/页序/bbox 0px）、ghbq 图像 passthrough（p1 封面/p2 条形码/p3 图版，p3 文字全部 type3 不可见）、chars +41/GMPG0/104=104/gate96.8、wz4/wz2 零回归、默认关与 HEAD 逐页全等、tests 41/722 全绿。残留 F1（中，p3 标题过度隐藏）、F2/F3/F4/F5（低）不阻断本轮；建议后续只隐藏与 image rect 相交的文本并补 p1 页脚图。
