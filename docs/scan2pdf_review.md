# scan2pdf v1 终审（t154 → t159 修复 → t160 round-2）

> 审查人：质量审查员（独立第三方，不参与实现）　日期：2026-11-08 23:33–23:55
> 对象：t152（scan2pdf v1 + ocr_book）+ t153 验收 + t155/t157/t159 修复
> 依据：`docs/scan2pdf_design.md`（t115 原设计 + §2.2 + §10 t159 契约登记）、`docs/scan2pdf_acceptance.md`
> **Round-2 结论：PASS（有条件）** —— t159 已按设计契约修复首轮 F1/F2/F3/F4/F5/F6；主流程、退出码、fix 守卫、报告审计、前导/mixed 登记均实测通过；残留 1 条 **resume 复用键不完整（medium）** 与若干低风险项，不阻断本轮验收，但建议产品发布前修。

---

## 1. 复跑（任务给定命令）

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz6.pdf --book wz6 \
  --out tmp_vert/scan2pdf/review_wz6.pdf --data-dir data/wz6 --skip-ocr
# [scan2pdf] 输出已存在且为本工具产物：默认不覆盖（resume 复用）；--force 才重建
# [scan2pdf] 书型: vertical, has_frame=True, size=[595.28, 1245.31], multi_format=False
# [scan2pdf] wz6: book_type=vertical gate=MANUAL_ONLY exit=0
# 实际 exit=0
```

- 门禁：verify **PASS**（231/231、97.2%、越界 0、丢失 0）；punct MANUAL（data_missing 0.5244）；content REJECT（0.1371）→ **MANUAL_ONLY**（可交付，按 §2.2 code 0）。
- 单测：`pytest src/test/unit/test_scan2pdf.py -q` → **19 passed**。
- 复跑命中 resume 复用（未重建，gate 重跑 4.3s），report `resume=true`、`resume_note` 显式；**--force 强制重建**验证见 §3。

---

## 2. t159 修复项验证（首轮 findings → 现状）

| 首轮 id | 状态 | 证据 |
|---|---|---|
| **F1 书专属 fix 映射** | **已修** | `grep '金瓶梅\|wz6\|wz7\|CANONICAL' src/tools/scan2pdf.py` **0 命中**；仅 `--fix`（显式）/ data-dir `fix_pointer.json` / per-book `*fix*.json`（source=book_data）；wz6/wz7/testbook 实测 `fix={path:null, source:'none', sha256:''}`、`VERT_MISSED_FIX=0`；wz7 不再加载 docs 修复 |
| **F2 退出码** | **已修** | 实现与设计 §2.2/§10.2 一致：0 成功（AUTO/MANUAL）、2 输入/out 已存、3 OCR/数据、4 书型、5 build、6 verify、7 REJECT、8 UNSCORED/需人工；实测 wz6 MANUAL→**0**、wz7 REJECT→**7**、缺输入→2、外部 out→2、缺数据→3 |
| **F3 覆盖/--force** | **已修** | 外部 out → exit 2（未覆盖）；本工具产物默认不覆盖、仅重跑门禁（resume=true + note）；`--force` 才重建（wz7 --force 实测 exit 7、report.resume=None） |
| **F4 报告审计** | **已修** | report 含 `input_sha256`、`steps`（data/fix_guard/book_type/build/publish/gate + elapsed_ms）、`fix{path,source,sha256}`、`build.cmd`（成功构建时）、`data{source,mode,coords,lines,sha}`；`preflight`、`mixed_axis_supported`、`v1_limitations` |
| **F5 前导** | **已修** | 新书 `book_type.source='computed'` + `confidence` + `preflight={pages:6,basis:'page-size/aspect',confidence:'low',note:…}`（testbook 实测）；缓存命中 source=probe_cache |
| **F6 mixed** | **已登记** | v1 不做 mixed 判定：report `mixed_axis_supported=false` + `v1_limitations`；设计 §10.5 登记；多纸型 wz7 实测 `multi_format=true`、`review_required=true`、`verdict_effective=REJECT`、REJECT 保持 exit 7（§10.2） |
| OCR 契约 | **已锁定** | `test_ocr_mode_contract`：A=`useLayoutDetection=True,promptLabel='ocr'`、B=`False,'spotting'`、6 页 1 批；声明「模式复用、代码独立」 |

设计文档同步：§2.2 退出码表 + §10（10.1 fix / 10.2 退出码 / 10.3 覆盖 / 10.4 审计 / 10.5 fallback/mixed）已由 t159 回填；与 §3 步骤表/§7 失败矩阵**一致**（未发现自相矛盾）。

---

## 3. 独立抽样

### 3.1 书型判断（2 例 + 1 新书）
- **wz6**：`vertical, has_frame=True, 595.28×1245.31, multi_format=False`（probe_cache, conf 1.0）→ build_vert ✓。
- **wz7**：`vertical, no_frame, 892.5×1323, multi_format=True`（sizes 610/582/554/+2 页）→ `review_required=true`、`auto_pass_forbidden=true`、`verdict_effective=REJECT`、exit 7 ✓。
- **testbook**（无缓存、无书专属）：`source=computed`、`confidence=1.0`、`preflight={pages:6,basis:'page-size/aspect',confidence:'low',note:'新书建议先跑 6 页前导…'}`，fix=none，build_vert 成功，gate MANUAL_ONLY → exit 0 ✓（证明无书专属路径、fallback 前导生效）。

### 3.2 失败矩阵（4 例）
| 场景 | 实测 |
|---|---|
| 缺输入 | **exit 2**，不建 out |
| 外部 out 已存在 | **exit 2**，未覆盖 |
| `--data-dir` 无数据 | **exit 3** |
| 构建/页数（单测 `test_page_mismatch_exit6`） | **exit 6**，不落 out |

### 3.3 gate 报告（1 例）
- wz6 `review_wz6.pdf.gate.json`：含 version/metrics{verify,punct,content}/verdict/reasons/gate{verify_pass,punct_verdict,content_verdict,data_missing,top_failures}/thresholds/expect_low；`.md` 可读；punct 零样本类不出现；must_pass_status=not_applicable、fail_items=[]；over_limit_pages 带 page/column/char_pos/gold_char/product_char → **可作交付报告** ✓。

### 3.4 --force 重建
- wz7 `--force`：未走 resume，`VERT_MISSED_FIX=0`、fix source=none、构建+门禁全跑、exit 7（REJECT）✓。

---

## 4. 残留 findings

| id | severity | problem | requiredFix |
|---|---|---|---|
| **R1** | **medium** | **resume 复用键不完整**：只比较 `book` + `input_sha256`（scan2pdf.py:441-443），**不比较 fix sha / data(coords/lines) sha / mode / pipeline / --pages**。实测：wz7 的 out 由 t154 用 `docs/vert_taskF_missed_fix.json` 构建，本轮无 --force 复用时 report 写 `fix.source=none`（与产物实际构建配置不符）→ 交付报告 provenance 失真；同理换 data-dir/pages 也会误复用 | resume 复用键加入 fix sha、coords/lines sha、mode、pipeline、pages 子集；任一不同 → 退出 2（提示 --force）或自动重建；report 记录构建时的 fix/data 快照而非当前配置 |
| **R2** | low | design §2.2 标题仍为「退出码（建议）」，而 §10.2 声明「以 §2.2 为准」且测试锁定 | 标题改为「契约」并去掉"建议" |
| **R3** | low | ocr_book 采用「模式复用、代码独立」，src 内仍无共享 run_batches（双实现漂移风险） | 后续抽共享模块或补契约回归频率 |
| **R4** | low | 成功构建时 `build.cmd` 入 report，resume 复用路径 build 被 skipped，cmd 为空（信息可接受但需 R1 修后保证 provenance） | 与 R1 一并处理 |
| **R5** | low | `--pages` 子集模式下 `input_sha256` 仍是整本 PDF hash，复用键无法区分不同页子集 | 并入 R1 |

> 首轮 F1/F2/F3/F4/F5/F6 均已修复并有测试/实测；上述为残留增强项。

---

## 5. 产品形态（上传 PDF → 还原 PDF + 报告）

- **CLI 明确** ✓：`--input/--out/--book/--data-dir/--skip-ocr/--pipeline/--ocr-mode/--token-file/--pages/--force/--fix/--report`。
- **退出码语义** ✓：与设计 §2.2 一致（0 成功含 MANUAL 可交付；2 输入/out；3 OCR/数据；4 书型；5 build；6 verify；7 REJECT；8 需人工）。
- **产物三件套** ✓：`out.pdf` + `out.gate.json/.md` + `out.report.json`；report 可审计（hash/steps/elapsed），失败不覆盖 out；REJECT 仍产出候选供审阅（exit 7）。
- **限制已登记** ✓：多纸型 review_required、mixed v1 不支持、OCR 转换（A/B→coords）v1 未接、阈值 provisional。

---

## 6. 结论

**Round-2 verdict：PASS（有条件）**。

- **通过**：t159 已按设计 §2.2/§10 修复首轮 F1–F6；主流程/repro/--force/失败矩阵/书型（含新书 computed+preflight）/gate 报告/审计字段/无书专属路径均实测通过；19 单测通过；设计文档已回填并与实现一致（§2.2/§10）。
- **条件**：R1（resume 复用键缺 fix/data/pipeline/pages，provenance 可失真，medium）建议**产品发布前**修复；R2–R5 低风险。
- 建议：修 R1 后用「不同 fix/data 配置 + 同名 out」复跑验证拒绝复用；再用 heldout 横排书（wz2/wz4）跑一次，确认 build_geom 路径与书型 fallback。

---

## 7. 复现

```bash
cd /opt/test
# 任务给定
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz6.pdf --book wz6 \
  --out tmp_vert/scan2pdf/review_wz6.pdf --data-dir data/wz6 --skip-ocr        # exit 0
# wz7（多纸型/REJECT/无 fix）
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz7.pdf --book wz7 \
  --out tmp_vert/scan2pdf/review_wz7.pdf --data-dir data/wz7_full --skip-ocr --pages 1-3   # exit 7
# 新书（computed + preflight + 无书专属）
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz6.pdf --book testbook \
  --out /tmp/s2p_tb.pdf --data-dir data/wz6 --skip-ocr                          # exit 0
# 失败矩阵
/usr/bin/python3 src/tools/scan2pdf.py --input /tmp/nonexistent.pdf --book wx --out /tmp/x2.pdf --skip-ocr  # 2
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz6.pdf --book wz6 --out /tmp/s2p_ext2.pdf --data-dir data/wz6 --skip-ocr  # 2
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz6.pdf --book wz6 --out /tmp/s2p_data.pdf --data-dir /tmp/emptydir --skip-ocr  # 3
# 单测
/usr/bin/python3 -m pytest src/test/unit/test_scan2pdf.py -q    # 19 passed
```

| 文件 | sha256 |
|---|---|
| `src/tools/scan2pdf.py` | `06d11ea619b46e2685a173a475a7d41f75836ffc3fa2e258bb8153af283ef2f1` |
| `src/tools/ocr_book.py` | `2a45cfa88538408237dab391ad95dd90be0f12a4ffe68b7095a4a0f384561077` |
| `docs/scan2pdf_design.md` | §2.2 + §10（t159 回填） |
| HEAD | `84d6b95`（未 commit） |

---

# 附：#37 横排修复终审（t165 round-2）

> 审查人：质量审查员　日期：2026-11-09 02:44–03:05
> 对象：t163（#37 修复）+ t164 验收 + t166 交付 + t167/t168 修复与验收
> 依据：`AGENTS.md` #37、`docs/scan2pdf_v1.md` §14–§16、`docs/scan2pdf_acceptance.md`
> **结论：PASS（有条件）** —— 根因（geom 分支直调 build_geom 单趟）已由「geom→fit_positional 两趟」关闭；verify_geom 带 `--src-pdf` 接入、floor=85；wz4 全量 677 页 PASS（pitch 99.6%）、wz2 6 页 PASS；无书专属分支；失败码语义未变；AGENTS #37=implemented、docs 已记录。残留 1 条 medium（横排分支未走多纸型 review_required）+ 3 条 low。

## 0. 复跑（任务给定命令）

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out tmp_vert/scan2pdf/review_wz4_fix.pdf --data-dir data/wz4 --skip-ocr
# [scan2pdf] 书型: vertical, has_frame=False, size=[418.4, 631.9], multi_format=False
# [scan2pdf] 书型修正（OCR 框长宽比）: horizontal
# [scan2pdf] 构建: fit_positional.py (pipeline=geom, VERT_MISSED_FIX=0)
# [scan2pdf] wz4: pipeline=geom gate=PASS exit=0
# 实际 exit=0（全量 677 页构建，约 3–4 分钟）
```

- 门禁（`review_wz4_fix.pdf.gate.json`）：tool=verify_geom、verdict=**PASS**、reasons=[]、pitch_floor=85、**pitch 99.6%**、pages **677=677**、split 0、missing 0、blank 32、overflow 6、exit 0；`.gate.md` 可读。
- 独立复跑 `verify_geom --src-pdf`（不走 scan2pdf）：`VERIFY_PITCH_FLOOR=85 … --src-pdf source_pdf/wz4.pdf` → **rc=0 PASS**（与 gate 一致）。
- report：pipeline=geom、fix source=none（VERT_MISSED_FIX=0）、steps=[data,fix_guard,book_type,build(rc=0),publish,gate(PASS)]、input_sha256 记录。

## 1. 根因与实现对照（#37）

| #37 根因/验收点 | 实现 | 结论 |
|---|---|---|
| geom 分支直调 build_geom **单趟**→无高度校准 | `build_pdf` geom 分支改调 `src/calibration/fit_positional.py`：pass1 `fill=99` 渲染测高 → ratio 表 → pass2 `fill=0.95` 重渲（`fit_common.main('build_geom')`） | ✓ 两趟 |
| fit_positional argv/env | cmd `[lines, coords, out_tmp, src_pdf]`，与 fit_common `SL=argv1,CO=argv2,OUT=argv3,SRC=argv4` **一致**；env 仅设 VERT_*（geom 不读），无污染 | ✓ |
| 无书专属分支 | `grep 'wz4\|wz2\|wz6\|wz7\|book ==' src/tools/scan2pdf.py` **0 命中**；wz4 走 build_type 修正 + fit_positional，wz2 同路径 | ✓ |
| verify_geom 接入 + 阈值来自 floor/契约 | `run_verify_geom(pdf,coords,lines,floor=None,src_pdf=...)`：floor 默认 `VERIFY_PITCH_FLOOR`=85，env 传递；**带 `--src-pdf`**（DPI 自适应）；usage/help 已标「必须带」 | ✓ |
| 失败码语义不变 | EXIT={ok:0,usage:2,out_exists:2,data_missing:3,ocr:3,book:4,build:5,verify:6,reject:7,partial:8,manual:8}，与设计 §2.2 一致；页数不 1:1→verify(6)、构建失败→5、数据→3；geom 分支 verify fail→6 | ✓ |
| gate 横排判定与竖排对齐 | 写 `<out>.gate.json/.md`：version/book/mode/tool/verdict/reasons/metrics{pitch_floor,pitch_ok_pct,pages,pages_src,split,missing,blank_pages,overflow_pages,exit}+gate；**与竖排 quality_gate 的 schema_version/pdf_sha256/thresholds_source/expect_low/verdict 词表不完全相同**（见 R2） | 部分（R2） |

## 2. 独立抽样

### 2.1 wz4 3 页对照（源图/历史产物/新产物）
`tmp_vert/scan2pdf/t165_wz4_compare.png`（p1/p100/p677 × src/hist/new）：
- p1：源为封面图；hist/new 均无封面图（文本层重建），属 #37 已知残留（t166 已登记「封面图未贴回」）；new 文本位置正常。
- p100：源正文页；new 文本完整、行距与页幅正常、无跨页/出界；与 hist 行宽/断行略有差异（200dpi→144dpi 的预期，t166/t168 waiver）。
- p677：后记；new 与 hist 文本一致（difflib ratio 1.000）。
- 文本量（fitz get_text）：new 603,844 vs hist 634,103 = **0.9523**；p100 页 ratio 0.964、p677 1.000、p1 0.813（封面文本差异）——与 t166/t168 登记的 DPI 变更口径一致。

### 2.2 wz2 6 页回归
`scan2pdf --book wz2 --data-dir data/wz2 --skip-ocr --pages 1-6` → **exit 0**、书型修正 horizontal、fit_positional 构建、gate **PASS**（pitch 100%、6/6、blank 0、overflow 0）。

### 2.3 文档/状态
- `AGENTS.md` #37 状态 = **implemented**（含 t163 根因与验收描述）；§3 verify_geom 行已标「必须带 --src-pdf（wz4=144dpi）」。
- `docs/scan2pdf_v1.md` §14 横排修复、§15 交付结论、§16 契约同步 + gate sidecar 均已记录。

## 3. 残留 findings

| id | severity | problem | requiredFix |
|---|---|---|---|
| **R1** | **medium** | **geom 分支未走多纸型/effective_verdict**：`if args.pipeline_resolved == 'geom'` 直接写 gate 并返回 PASS/REJECT，未调用 `multi_format_clause`/`effective_verdict`（竖排路径有）。多纸型横排书会得到 PASS 而无 `review_required=true`/`auto_pass_forbidden`（设计 §10.2 要求所有书） | geom 分支也应用 `multi_format_clause`：review_required/auto_pass_forbidden 写入 report/gate；AUTO→MANUAL、REJECT 保持 |
| **R2** | low | 横排 gate JSON 与竖排 quality_gate schema 仅**部分**对齐：缺 `schema_version/pdf_sha256/thresholds_source/expect_low`，metric 键名 `blank_pages/overflow_pages` vs 竖排 `blank/overflow`，verdict 词表 PASS/REJECT vs AUTO_PASS/MANUAL_ONLY/REJECT | 统一 gate schema（或加 `mode` 分支说明）；t167「与竖排对齐」表述宜改为「核心字段对齐」 |
| **R3** | low | 书型初始按宽高比把 wz4（418×632 肖像）判 vertical，再由「OCR 框长宽比」修正为 horizontal；无 OCR 数据的横排书可能误判 | fallback 记录 low confidence + preflight；建议对「竖排但 OCR 框宽≈1.5×高」的修正加单测说明 |
| **R4** | low | 文本量与历史产物 0.9523（t166/t168 已裁定 200→144dpi 预期，登记 waiver） | 保持登记；若未来要求逐页文本一致，另起 issue |
| **R5** | low | `verify_geom` 缺省 DPI=200 仍存在（scan2pdf 已正确传 --src-pdf；但外部直接调用仍易踩坑） | 保持 usage/README 的「必须带」提示；可考虑缺省改为 auto（需 spec 变更） |

## 4. 结论

**#37 终审 verdict：PASS（有条件）**。

- **通过**：根因关闭（geom→fit_positional 两趟）；verify_geom 接入且 floor/`--src-pdf` 来自契约；wz4 全量 677 页 gate PASS（pitch 99.6%、677=677、split 0）、独立 verify_geom rc=0；wz2 6 页 PASS；无书专属分支；失败码语义未变；AGENTS #37=implemented；docs §14–§16 记录完整；与历史产物/源图 3 页对照无跨页溢出（封面图缺失为已知残留）。
- **条件**：R1（横排多纸型未应用 review_required，medium）建议在 v1 收口前修；R2–R5 为低风险/登记项。
- 建议：修 R1 后用一本多纸型横排书验证 report/gate 的 review_required；并以 `verify_geom --src-pdf` 作为 PR 门禁命令（AGENTS §3 已更新）。

## 5. 复现

```bash
cd /opt/test
# 任务给定
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out tmp_vert/scan2pdf/review_wz4_fix.pdf --data-dir data/wz4 --skip-ocr   # exit 0
# 独立 verify（不进 scan2pdf）
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  tmp_vert/scan2pdf/review_wz4_fix.pdf data/wz4/wz4_spotting_coords.json \
  data/wz4/wz4_spotting_lines.json --src-pdf source_pdf/wz4.pdf               # rc 0 PASS
# wz2 6 页
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz2.pdf --book wz2 \
  --out /tmp/wz2_6p.pdf --data-dir data/wz2 --skip-ocr --pages 1-6             # exit 0
# 对照图
# tmp_vert/scan2pdf/t165_wz4_compare.png（p1/p100/p677 × src/hist/new）
```

| 文件 | sha256 / 说明 |
|---|---|
| `src/tools/scan2pdf.py` | `34750bd6bc7ee77ff9e2974233921b60170ee8c8c74ed4cb377729eb9a38ade1` |
| `src/test/verify_geom.py` | `834ff6f499d35f72ca681d1ac487dabe4862c00f47fc12dc94ebc777d021c865` |
| `tmp_vert/scan2pdf/review_wz4_fix.pdf` | 2,597,505 B / 677 页（本终审产物） |
| `tmp_vert/scan2pdf/review_wz4_fix.pdf.gate.json` | 1,102 B / PASS（pitch 99.6%） |
| HEAD | `56bcaeb`（未 commit） |

---

# 附：geom 分支多纸型语义终审（t171 round-3，R1/R2）

> 审查人：质量审查员　日期：2026-11-09 03:02–03:25
> 对象：t169（#37 R1/R2 修复）+ t170 验收
> 依据：t165 附章 R1/R2、`docs/scan2pdf_v1.md` §16.2/§17、`docs/scan2pdf_acceptance.md`
> **结论：PASS（有条件）** —— geom 分支已与竖排同语义（多纸型 PASS→MANUAL_ONLY、REJECT 保持、review_required/auto_pass_forbidden/分布 note 写入 report 与 sidecar）；单纸型 wz4 行为不变；wz2 构建正常；30 单测通过；无书专属分支。残留为低风险：多纸型横排无真实书 E2E、schema 仍非全对齐（已登记）、geom 的 AUTO_PASS 分支为死代码、跨轴 REJECT 退出码 6 vs 7 属轴语义差异。

## 0. 复跑（任务给定命令）

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out tmp_vert/scan2pdf/review_wz4_r1.pdf --data-dir data/wz4 --skip-ocr
# [scan2pdf] 书型修正（OCR 框长宽比）: horizontal
# [scan2pdf] 构建: fit_positional.py (pipeline=geom, VERT_MISSED_FIX=0)
# [scan2pdf] wz4: pipeline=geom gate=PASS exit=0
# 实际 exit=0（全量 677 页）
```

- `report.json`：exit 0、`review_required=false`、`auto_pass_forbidden=false`、`multi_format=null`、gate PASS（pitch 99.6%、677=677、split 0、blank 32、overflow 6）。
- `gate.json` keys：version/book/mode/tool/**verdict/verdict_effective/review_required/auto_pass_forbidden/multi_format/multi_format_note**/reasons/metrics/gate/note；**PASS / PASS / false / false / null**。
- `gate.md`：首行「结论：PASS（effective=PASS，review_required=False）」+ pitch/pages/split/overflow + 「multi_format：无（单纸型）」可读。
- 单测：`pytest src/test/unit/test_scan2pdf.py -q` → **30 passed**。

## 1. 与竖排语义对照（t165 R1）

| 场景 | 竖排（quality_gate 路径） | geom（本次） | 一致 |
|---|---|---|---|
| 单纸型 PASS | exit 0 | exit 0（wz4/wz2 实测） | ✓ |
| 多纸型 AUTO/PASS | AUTO_PASS→MANUAL_ONLY；PASS 不存在于竖排（quality 三档） | `effective_verdict('PASS',True)` → **MANUAL_ONLY**（实测） | ✓ |
| 多纸型 REJECT | 保持 REJECT（exit 7） | **保持 REJECT**（`('REJECT',True)`→REJECT） | ✓（exit 轴语义见 R4） |
| review_required / auto_pass_forbidden | true（多纸型） | true（多纸型）；`multi_format_clause` 实测含 `paper_distribution='300x500:7页, 250x450:3页'`、severity、acceptance_wording、note | ✓ |
| note 分布 | multi_format_note 含分布 | 同（report + sidecar 均写） | ✓ |
| 单纸型多纸型块 | None | `multi_format_clause(...,False)=None`（实测） | ✓ |

## 2. 代码审查

- **无书专属分支**：`grep -c 'wz4\|wz2\|wz6\|wz7' src/tools/scan2pdf.py` = **0**。
- **单纸型行为不变**：geom 分支单纸型仍 `verdict=PASS`、exit 0（wz4 677 页、wz2 6 页实测）；`effective_verdict(v,False)` 原样返回（实测 PASS/REJECT 均不变）。
- **多纸型分支**：`verdict_effective` 用于 exit 码——`not v_ok`→verify(6)、`ve=='MANUAL_ONLY'`→manual(8)、否则 ok(0)（代码 L602-612）；sidecar 写入 `review_required/auto_pass_forbidden/multi_format/multi_format_note/verdict_effective`，`gate` 子块也含 effective/review_required（L642-648）。
- **单测**：30 passed，含 `effective_verdict('PASS',True)=MANUAL_ONLY`、合成多纸型（300x500/250x450）`review_required=true`+note 含分布、多纸型 REJECT 保持、单纸型 None、md 字段断言（t169/t170 描述一致）。
- **R2 措辞**：`docs/scan2pdf_v1.md` L178/L204 为「**核心字段对齐（非全 schema）**」，列明横排缺 `schema_version/pdf_sha256/thresholds_source/expect_low`、verdict 词表差异；`grep '完全对齐'` = 0。

## 3. 独立抽样

| # | 场景 | 实测 |
|---|---|---|
| 1 | wz4 全量（任务命令） | exit 0、677 页、gate PASS（pitch 99.6%、677=677）、review_required=false、sidecar 可读 |
| 2 | wz2 6 页 | exit 0、6=6、gate PASS（pitch 100%）、review_required=false、sidecar 含新字段 |
| 3 | 多纸型语义（函数级） | `effective_verdict('PASS',True)='MANUAL_ONLY'`、`('REJECT',True)='REJECT'`、单纸型不变；`multi_format_clause` → review_required/auto_pass_forbidden=true、分布串正确 |
| 4 | 单测 | 30 passed |

## 4. 残留 findings（低）

| id | severity | problem | requiredFix |
|---|---|---|---|
| **R1** | low | 多纸型横排**无真实书 E2E**（repo 无多纸型横排源 PDF）；现为合成 book_type + 函数级/单测验证，geom 分支「多纸型→exit 8/6」路径未端到端跑过 | heldout 补一本多纸型横排（或合成 PDF 改名）跑 scan2pdf E2E，断言 exit/review_required/note |
| **R2** | low | 横排 sidecar 与竖排仍非全 schema 对齐（缺 schema_version/pdf_sha256/thresholds_source/expect_low；verdict 词表不同） | 已在 docs §17 登记「核心字段对齐」；如需统一另起 schema 版本 |
| **R3** | low | `effective_verdict` 中 `AUTO_PASS→MANUAL_ONLY` 分支对 geom 为死代码（geom 只产 PASS/REJECT） | 保留兼容（竖排可复用）；注释说明 |
| **R4** | low | 跨轴 REJECT 退出码不同：geom verify 失败=6、竖排 quality REJECT=7 | 属轴语义（verify vs quality）；上层按 tool/verdict 判定即可，文档可补一句 |

## 5. 结论

**t171 终审 verdict：PASS（有条件）**。

- **通过**：t165 R1 关闭（geom 分支与竖排同多纸型语义：PASS→MANUAL_ONLY、REJECT 保持、review_required/auto_pass_forbidden/分布 note 落入 report+sidecar）；R2 措辞已按「核心字段对齐（非全 schema）」修正并登记差异；单纸型 wz4/wz2 行为不变；30 单测通过；无书专属分支。
- **条件**：R1（多纸型横排 E2E 缺失）建议在 v1 收口前用 heldout/合成多纸型 PDF 补一次端到端；R2–R4 为登记/注释级。
- 建议：把「多纸型横排 E2E」列入 heldout 验收清单；后续若统一 gate schema，同步 `docs/scan2pdf_v1.md §17` 与 quality_gate 版本号。

## 6. 复现

```bash
cd /opt/test
# 任务给定（wz4 单纸型）
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out tmp_vert/scan2pdf/review_wz4_r1.pdf --data-dir data/wz4 --skip-ocr      # exit 0
# wz2 6 页
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz2.pdf --book wz2 \
  --out /tmp/t171_wz2_6p.pdf --data-dir data/wz2 --skip-ocr --pages 1-6          # exit 0
# 多纸型语义（函数级）
/usr/bin/python3 - <<'PY'
import sys; sys.path.insert(0,'src/tools'); import scan2pdf as s
print(s.effective_verdict('PASS',True)); print(s.effective_verdict('REJECT',True))
print(s.multi_format_clause('PASS','MANUAL_ONLY',True,[{'size':[300,500],'pages':7},{'size':[250,450],'pages':3}]))
PY
# 单测
/usr/bin/python3 -m pytest src/test/unit/test_scan2pdf.py -q    # 30 passed
```

| 文件 | sha256 / 说明 |
|---|---|
| `src/tools/scan2pdf.py` | `1eb40a86fd4e83c1fb611578befb521cedda57883357bd92332f67c54e150773` |
| `src/test/unit/test_scan2pdf.py` | `b611cc5051bd9d3e13fc68fb4e6b0ae87f0d7bfd132020a507433e3e65c7cf01` |
| `tmp_vert/scan2pdf/review_wz4_r1.pdf` | 2,597,500 B / 677 页（本终审产物） |
| `tmp_vert/scan2pdf/review_wz4_r1.pdf.gate.json` | 1,349 B / PASS / review_required=false |
| HEAD | `56bcaeb`（未 commit） |

---

# 附：OCR E2E 终审（t174，raw→coords/lines + ghbq 真 OCR）

> 审查人：质量审查员　日期：2026-11-09 18:25–18:45
> 对象：t172（OCR raw 转换 + ghbq E2E）+ t173 验收
> 依据：`docs/scan2pdf_v1.md` §18、`docs/scan2pdf_acceptance.md`（t173）
> **结论：PASS（有条件）** —— 转换 scale/页 key/jobs.pages 追溯/两模式 manifest 均实测正确；scan2pdf 接线优先级正确；token 只读不落盘；坐标单位与 verify_geom 口径一致；ghbq 4 页产物 2 页与源图对照文本/行位大致对位；raw 文本命中 79/80=98.75%；repetitionPenalty=1 与 §18.5 记录一致。残留均 low。

## 0. 复跑（任务给定命令）

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/test_ghbq/review_ghbq4.pdf --pages 20-23 --token-file /tmp/paddle_token --force
# [scan2pdf] 书型修正（OCR 框长宽比）: horizontal
# [scan2pdf] 构建: fit_positional.py (pipeline=geom, VERT_MISSED_FIX=0)
# [scan2pdf] ghbq: pipeline=geom gate=PASS exit=0
```

- exit 0；pages 4=4；gate **PASS**（pitch 100%、split 0、blank 0、overflow 0、review_required=false）。
- 独立 `verify_geom --src-pdf`（不进 scan2pdf）→ **rc=0 PASS**（4=4、pitch 100%，DPI 自适应）。
- **独立真 OCR**：另跑 `--out output/test_ghbq/t174fresh/...`（新目录）→ 新 layout/spotting **jobId `113222871381495808` / `113222941396234240`**（与 t172/t173 均不同）、4 页、exit 0、gate PASS pitch 100%——证明非缓存 resmue 也能跑通。

## 1. 转换正确性（t172 实现）

| 检查 | 结果 |
|---|---|
| scale 公式 | 代码 `sx=2*pdf_page_w/pruned_w`（逐页取 `src[gpage].rect` 与 `prunedResult.width/height`）→ ghbq p19：`2*595.28/1191≈0.9996`；**多纸型/逐页尺寸安全**（非全局 scale） |
| poly 值换算 | 抽 p19 前 5 条 poly：`exp=poly*sx/sy` 与 `coords['19']` **逐值差 ≤0.05**（5/5） |
| 文本顺序 | `lines['19'] == raw rec_texts`（20/20，顺序一致） |
| 页 key | jobs pages `[19,20,21,22]`（0-based）→ coords/lines keys **19–22**；`manifest.source_pages=104` 与源 PDF 一致 |
| jobs 追溯 | `jobs.json` layout/spotting 均含 `pages`（resume 也补写）；manifest batches 同步 jobId/pages |
| 缺 jobs 回退 | 无 jobs 时按 `range(len(results))` 推断 0-based 页序（**仅作 fallback**）→ 若外部 raw 是页子集（如 20-23）会误标 0-3（见 F1） |

## 2. scan2pdf 接线 / 单位 / 安全

- **数据源优先级**：OCR 后先找 `--data-dir`，再回退 `<out>/_ocr_<book>/`；ghbq 无 --data-dir 时 report `data.source=ocr, data_dir=.../_ocr_ghbq`，`mode=spotting`，不再报缺 coords/lines ✓；layout raw 不参与构建 ✓。
- **单位一致**：legacy coords=2×pt（与 build_geom/fit_positional、verify_geom 的 coords 口径一致）；verify_geom `--src-pdf` 自适应 DPI（本页 595.28 宽/1191 pruned → 144dpi 量级）→ rc 0、pitch 100%。
- **token 安全**：`ocr_book` 只读 token（check_token 仅返回路径/错误），不写文件、不打印；`grep 4ec51fe5... output/test_ghbq tmp_vert/scan2pdf` → **0 命中**。
- **无书专属分支**：`grep -c ghbq src/tools/ocr_book.py src/tools/scan2pdf.py` = 0/0。

## 3. 独立抽样

### 3.1 ghbq 产物 2 页 vs 源图
`tmp_vert/scan2pdf/t174_ghbq_compare.png`（源 p20/p23 × 产物页）：
- p20：段落/行数与源图基本一致（首行「好，那么这个国家的共产党还有威信吗？」…），行位大致对位；**产物页未见页码「8」**（源图有）——OCR raw 未把页码作为行给出，属内容层小差异（F3 low）。
- p23：首行「就陷入了历史唯心主义的泥坑…」与源一致；行文/换行接近；页码「11」在产物可见。
- 无跨页/出界，无空白页。

### 3.2 raw 文本命中率
- 4 页 raw `rec_texts` 共 **80** 条；在产物完整文本（去空白归一）中 **exact 命中 79/80 = 98.75%**。
- 唯一未命中为一条长引号行（`主化”“公开性”“多元论”和“人道主义”，特别强调了“民`）——疑似产物在行内断行/引号形态差异导致整串不是连续子串；按「归一化片段」检查可视为命中（F2 low）。

### 3.3 repetitionPenalty 热修
- `ocr_book.payload()` 现为 `"repetitionPenalty": 1`；`docs/scan2pdf_v1.md §18.5` 记录「曾写 0 → 改 1」及现象/影响，代码与文档一致 ✓。

## 4. 残留 findings（均 low）

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F1** | low | 缺 jobs.json 时 `convert_raw_dir` 回退 `range(len(results))` 推断 0-based 页序；外部 raw 若来自页子集（如 20-23）会误标 0-3 → 坐标/文本错页 | 回退时打印 WARN 并在 manifest 标 `inferred_pages=true`；或要求 jobs 缺失时显式 `--pages` 指定 |
| **F2** | low | raw 文本命中 98.75%（79/80）；唯一 miss 为长引号行（行内断行/引号形态），按整串 exact 判定偏严 | 命中率改「去空白+按行片段」归一化统计，报告注明口径 |
| **F3** | low | 产物 p20 未见页码「8」（源图有）；OCR raw 未把它作为行，属内容层小差异 | 可在 OCR 前导/后处理补页码行，或在 E2E 报告登记「页码不保证」 |
| **F4** | low | `used_pages` 仅记录未断言；多批 raw 若页重叠会静默覆盖同 key | 转换时检测重复 gpage 并 WARN/失败 |

## 5. 结论

**t174 终审 verdict：PASS（有条件）**。

- **通过**：raw→coords/lines 转换（逐页 scale、polys 值、文本顺序）、jobs.pages 0-based 追溯、manifest（batches+source_pages）、resume 补写；scan2pdf 数据源优先级（--data-dir → `_ocr_<book>`）；token 只读不落盘；坐标单位与 verify_geom 一致（rc=0、pitch 100%）；ghbq 4 页 E2E（含**新 jobId 的独立真 OCR**）exit 0/gate PASS；2 页目视文本/行位大致对位；raw 命中 79/80；repetitionPenalty 文档一致；33 单测通过。
- **条件**：F1–F4 为低风险健壮性/口径注释项；建议 F1 在外部 raw 场景补 WARN，F2 明确统计口径。
- 建议：把「页子集 + 无 jobs 的外部 raw」加入单测；后续多纸型横排 E2E（t171 R1）与本 OCR E2E 合并为 heldout 清单。

## 6. 复现

```bash
cd /opt/test
# 任务给定
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/test_ghbq/review_ghbq4.pdf --pages 20-23 --token-file /tmp/paddle_token --force  # exit 0
# 独立真 OCR（新目录/新 jobId）
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/test_ghbq/t174fresh/review_ghbq4.pdf --pages 20-23 --token-file /tmp/paddle_token --force
# 独立 verify
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py output/test_ghbq/review_ghbq4.pdf \
  output/test_ghbq/_ocr_ghbq/ghbq_spotting_coords.json output/test_ghbq/_ocr_ghbq/ghbq_spotting_lines.json \
  --src-pdf source_pdf/ghbq.pdf                                                     # rc 0 PASS
# 单测
/usr/bin/python3 -m pytest src/test/unit/test_ocr_book.py src/test/unit/test_scan2pdf.py -q  # 33 passed
```

| 文件 | sha256 / 说明 |
|---|---|
| `src/tools/ocr_book.py` | `ae9848a01262bb079cd345fab63340d28dad074d8335d235c642c1ee7b76e216` |
| `src/tools/scan2pdf.py` | `d47c4971b8c24034a4ced336417884eb5233cecf77ba8e0ea30c37634947ba5a` |
| `src/test/unit/test_ocr_book.py` | `0010a1f3c2f368edd60f59a0a552f1585cd11e99d32d45d3bbf43a30ca77917c` |
| `src/test/unit/test_scan2pdf.py` | `b611cc5051bd9d3e13fc68fb4e6b0ae87f0d7bfd132020a507433e3e65c7cf01` |
| `output/test_ghbq/review_ghbq4.pdf` | 4 页（本终审产物，gate PASS） |
| `output/test_ghbq/t174fresh/review_ghbq4.pdf` | 4 页（独立真 OCR，新 jobId） |
| HEAD | `516871f`（未 commit） |

---

# 附：OCR JSONL 解析修复终审（t177，#40 / ghbq 104 页）

> 审查人：质量审查员　日期：2026-11-09 18:47–19:05
> 对象：t175（JSONL 修复正式化）+ t176 验收
> 依据：`AGENTS.md` #40、`docs/scan2pdf_v1.md` §19、`docs/scan2pdf_acceptance.md`（t176）
> **结论：PASS（有条件）** —— JSONL 逐行解析/页序/单 JSON 兼容实测正确；ghbq 104 页全书重转换 coords/lines 各 104、gate PASS（104=104、pitch 96.8%）；无书专属分支；35 单测通过。残留：**docs §19 的「13/13/2 行」与实测「13/13/1 行」不符**（low，须改一处文档）+ 25 页 overflow 占位诊断建议抽检 + 图片不保留属已知限制。

## 0. 复跑（任务给定命令）

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_full.pdf \
  --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
# [scan2pdf] 书型修正（OCR 框长宽比）: horizontal
# [scan2pdf] 构建: fit_positional.py (pipeline=geom, VERT_MISSED_FIX=0)
# [scan2pdf] ghbq: pipeline=geom gate=PASS exit=0
```

- exit 0；**104=104**；gate **PASS**（pitch **96.8%**、split 0、missing 0、blank 2、overflow 25、review_required=false）。
- 独立 `verify_geom --src-pdf`（不进 scan2pdf）→ **rc=0 PASS**（104=104、pitch 96.8%）。
- 单测：`pytest test_ocr_book test_scan2pdf -q` → **35 passed**。

## 1. JSONL 解析（#40）

| 检查 | 结果 |
|---|---|
| 实际 raw 结构 | `spotting_000.json` **13 行/13 对象/50 页**；`spotting_001` 同为 13/50；`spotting_002` **1 行/1 对象/4 页**（文件 21,993 字符、`json.loads` 可整读）；layout 同构 |
| 解析实现 | `_load_json_objects`：先 `json.load`（单 JSON/数组兼容），`JSONDecodeError` 时逐行 `json.loads`；`convert_raw_dir` 按对象出现顺序拼接 `layoutParsingResults` |
| 合成等价（独立复验） | JSONL（2 对象 3 页）+ jobs.pages=[5,6,7] 与同内容单 JSON → coords/lines keys **5/6/7**、**逐值相等**、文本顺序正确 |
| 页序 | `lines['0']` == raw 第 1 对象第 1 页 `rec_texts`（7/7 行）；keys 0..103 连续、与 jobs.pages 0..103 对齐 |
| jobs/manifest | jobs 3 批（layout/spotting 各 000/001/002，pages 0–49/50–99/100–103）；manifest 6 batch + `source_pages=104` |
| 单 JSON 兼容 | 旧 4 页 E2E raw（单 JSON）路径未被破坏；`json.load` 分支直接返回 |

## 2. 全书回归

- 重转换：`ghbq_spotting_coords.json` / `_lines.json` **各 104 页**（keys 0..103），lines 共 **1,986** 行。
- scan2pdf 全量：exit 0、geom 104 页、gate PASS（104=104、pitch 96.8%、split 0、missing 0）、`review_required=false`；`<out>.gate.json/.md` 可读。
- 无书专属分支：`grep -c ghbq src/tools/ocr_book.py src/tools/scan2pdf.py` = **0/0**。

## 3. 独立抽样（源图对照）

- `tmp_vert/scan2pdf/t177_ghbq_full_compare.png`（p1/p104 × 源/产物）：
  - p1：标题/副标题/作者/出版社文本对位；**封面照片未保留**（OCR 文本重建不嵌图，已知限制，同 wz4 p1）。
  - p104：源为 DuXiu 元数据页，产物文本内容一致（行宽/换行不同）；非书正文页，属源文件自带页。
- 诊断页复看 `t177_ghbq_overflow.png`（p2/p13/p59 × 源/产物）：
  - p2 为短页（摘要+ISBN/定价），verify_geom 归「空白」是底部占位口径，非内容缺失；**条形码图片未保留**（同图片限制）；
  - p13/p59 正文与源一致、无可见出页/截断；25 页「溢出（占位）」样本未见真实越界，但建议按 t176 提示抽检全部 25 页。

## 4. 文档一致性

- `AGENTS.md` #40：50 页批 13 行×4 页、逐行解析、单 JSON 兼容、104 页回归数字——与实现/实测一致。
- `docs/scan2pdf_v1.md` §19：解析/单测/104 页回归描述一致；**唯一不符**：§19 写「spotting_000/001/002，JSONL **13/13/2 行**」，实测第三批为 **1 行**（13/13/1）→ 见 F1。

## 5. 残留 findings

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F1** | **low**（建议立即改） | docs §19 的「JSONL 13/13/2 行」与实测不符（spotting_002 = **1 行/1 对象/4 页**；50 页批才是 13 行=12×4+2 页） | 改 §19 为「13/13/1 行」（或写每批行数=ceil(页数/4)）；AGENTS #40 无需改 |
| **F2** | low | gate PASS 但 **overflow 25 页**（占位口径）+ 页高误差 <5% 仅 27.7%；抽样 p13/p59 未见真实越界，但未逐页核 | 抽检 25 页（可批量渲染缩略图）；若占位偏差属 DPI/边距口径，登记说明 |
| **F3** | low | 图片不保留（ghbq p1 封面照片、p2 条形码）；OCR 文本重建的已知限制，文档未在 ghbq 验收段明示 | 在 docs/scan2pdf_v1 限制段补「图片/条形码不嵌入」；或列入后续 issue |
| **F4** | low | `_load_json_objects` 以 `JSONDecodeError` 区分单 JSON/JSONL；畸形单 JSON 会落入逐行解析并抛行级错误（诊断信息偏弱） | 可在异常信息中带文件名/行号；非阻断 |
| **F5** | low | verify_geom「空白 2 页」实为短页（p2/p5 底部占位 0），非内容丢失 | 登记口径说明即可 |

## 6. 结论

**t177 终审 verdict：PASS（有条件）**。

- **通过**：JSONL 逐行解析与拼接、jobs.pages 页序、单 JSON 兼容（合成等价 + 实际 raw 13/13/1 对象）；ghbq 全书 104 页重转换 coords/lines 各 104（keys 0..103）；scan2pdf 全量 exit 0、gate PASS（104=104、pitch 96.8%、split 0）；独立 verify_geom rc=0；无书专属分支；35 单测通过；AGENTS #40 与实现一致。
- **条件**：F1（docs §19 行数笔误）应改；F2（25 页 overflow 抽检）/F3（图片限制登记）为低风险跟进。
- 建议：heldout 清单补「大 batch（>4 页/对象）JSONL」+「50 页批末行 2 页」的回归样例；ghbq 全量产物可作为 OCR E2E 基线登记（md5 `b52c1481…`）。

## 7. 复现

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_full.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py output/ghbq_full/review_ghbq_full.pdf \
  output/ghbq_full/_ocr_ghbq/ghbq_spotting_coords.json output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json \
  --src-pdf source_pdf/ghbq.pdf                                   # rc 0 PASS
python - <<'PY'  # JSONL/单 JSON 等价 + raw 对象/页
import sys; sys.path.insert(0,'src/tools'); import ocr_book as ob
print(len(ob._load_json_objects('output/ghbq_full/_ocr_ghbq/raw/spotting_000.json')))  # 13
print(len(ob._load_json_objects('output/ghbq_full/_ocr_ghbq/raw/spotting_002.json')))  # 1
PY
/usr/bin/python3 -m pytest src/test/unit/test_ocr_book.py src/test/unit/test_scan2pdf.py -q   # 35 passed
```

| 文件 | sha256 / 说明 |
|---|---|
| `src/tools/ocr_book.py` | `0e04904366c35c37070b79c77dff654abebd03243a6d8ba5f8afb02b19ae8055` |
| `src/tools/scan2pdf.py` | `d47c4971b8c24034a4ced336417884eb5233cecf77ba8e0ea30c37634947ba5a` |
| `src/test/unit/test_ocr_book.py` | `d5e94c40ec4e8901ab5adeb3daae972d905c7c4a5d9bb1465941b8ad7a326d7f` |
| `output/ghbq_full/review_ghbq_full.pdf` | 104 页（本终审产物；md5 `b52c14815bf57478218783bbd53af9e6`） |
| HEAD | `516871f`（未 commit） |
