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

---

# 附：横排标定审计终审（t181，HORIZONTAL_CALIB）

> 审查人：质量审查员　日期：2026-11-09 21:37–22:05
> 对象：t179（calib.json + 自检 warnings）+ t180 验收 + t182/t183 修复
> 依据：`spec/governance/HORIZONTAL_CALIB.md`、`docs/scan2pdf_v1.md` §20、`docs/scan2pdf_acceptance.md`（t183）
> **结论：needs_revision（FAIL）** —— 字段/容差/渲染不变性均实测通过，但**自检与 §3 契约有两处未落地**：§3.2 FAIL 不产生非零退出码（仅记录），§3.1 #10/#11 的 TOC 参数区间与 TOC 样本 <3 未校验（ghbq toc_samples=1 实测无该 warning）；另有 spec 示例 date_local 与实现矛盾、报告措辞「gate.calib_warnings」与实际字段不符。修复面小（补 2 条自检 + 对齐 1 条款/措辞），但当前不能称「契约一致」。

## 0. 复跑（任务给定命令）

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_calib.pdf \
  --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
# [scan2pdf] ghbq: pipeline=geom gate=PASS exit=0
```

- ghbq 104 页：exit 0、gate **PASS**（pitch **96.8%**、104=104、split 0）、`calib.json` 1970 B、gate sidecar 2514 B；`pytest test_horizontal_calib test_scan2pdf` → **35 passed**。
- wz4 677 页（补充独立构建）：exit 0、gate **PASS**（pitch **99.6%**、677=677）；独立 `verify_geom --src-pdf` rc=0 PASS；`calib.json` warnings=[]、selfcheck=pass。

## 1. 与 spec 契约对照

| spec | 实现/实测 | 结论 |
|---|---|---|
| §2.1 DPI（value/source/residual/expected；残差≤5） | ghbq 139/coords+src/res 0.298；wz4 144/coords+src/res 0.094 | ✓ |
| §2.2 页面尺寸（coverage_x/y、threshold、source_of_page_size；>1.02 才 warn） | ghbq 603×870（coords，cov 1.013/1.003）；wz4 418×634（cov 0.9991/0.9988）；无 overcoverage warn | ✓ |
| §2.3–2.6 cw/measure/font/baseline/margin/font_sm/h_body | ghbq：cw25、measure 461/413/1.115、font16.5、baseline34.2(ratio2.073)、margin95；wz4：cw28、font10.7、baseline17.8(1.664)、margin59 | ✓ |
| §4.2 字段清单 | 23 顶层键齐全（dpi/page_size/render/cw/measure/font/baseline/margin_pt/font_sm_pt/h_body_px/toc_params/coverage/source_of_page_size/warnings/selfcheck/env/created_by…）；`render` page/font/pitch/pass/unit 齐全 | ✓（除 F4 date_local） |
| §4.1 可复现（sha256+版本，无时间戳） | 无 date_local/时间戳；sha256 记录 | ✓ |
| §3.1 #1/#2/#12 FAIL 项 | pages_mismatch/empty_input/source_of_page_size_missing → severity=fail（代码审查） | ✓（级别正确） |
| §3.2 FAIL 不静默（退出码） | **build_geom 无 sys.exit；fail 仅写 warnings/selfcheck + stderr，退出码仍 0** | **✗ F1** |
| §3.1 #10 TOC 参数（font_line/foot_x/title_max 区间） | 仅校验 font_line（0.9–1.8×font）；foot_x/title_max 未校验 | **✗ F2** |
| §3.1 #11 样本量（full<5/pitch<10/TOC<3） | full/pitch 已校验；**TOC<3 未校验**——ghbq toc_samples=1 无对应 warning | **✗ F3** |
| §3.1 #3 pitch<3% | selfcheck pitch_error 3.2%（ghbq，verify_geom 回填）/0.4%（wz4） | ✓ |
| 书无关 | 无 `if book==`；§5 参考基线仅在 spec/文档，代码无书表 | ✓ |

## 2. 渲染行为不变（关键验收）

- **ghbq 104 页**：新 calib 产物 vs 上一版全量产物 → 逐页文本 **104/104 相同**、总字符 49,262=49,262、p1/p51/p104 **像素相同**；md5 差异仅 PDF 元数据/ID（`8f4d1468` vs `b52c1481`）。
- **wz4 677 页**：新 calib 产物 vs t165 产物 → 逐页文本 **677/677 相同**、总字符 603,844=603,844、p1/p101/p677 **像素相同**。
- gate：ghbq PASS 96.8%、wz4 PASS 99.6%，与 calib 前一致 → **calib 输出不改变渲染/门禁结论** ✓。

## 3. warnings 语义

- ghbq：1 条 `baseline_font_ratio_out`（severity=warn，2.073∉[1.2,2.0]）→ selfcheck.verdict=warn；report/gate reasons `calib_warn:baseline_font_ratio_out`，**gate 仍 PASS、exit 0**（非阻断）✓。
- wz4：warnings=[]、selfcheck=pass、gate reasons=[] ✓。
- FONT_SCALE=3 fixture：build rc=0 + `font_out_of_range` warn（不阻断）✓（t182 单测）。

## 4. findings（must-fix）

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F1** | **medium** | §3.2「FAIL 不静默：stdout + warnings + **退出码**」未落地：build_geom 对 severity=fail（pages_mismatch/empty_input/source_of_page_size_missing）只打印+写 JSON，进程仍 exit 0；`HORIZ_CALIB_STRICT` 也未实现（spec 标“规划”可接受，但不能替代 §3.2 现行 FAIL 退出码） | 二选一：①fail 时 build_geom 非零退出（或至少 scan2pdf 映射为 exit≠0）；②修订 spec §3.2 为「构建不阻断，由 verify/scan2pdf gate 兜底」并经 captain 确认；同时把 docs §20「spec §3 清单落地」改为如实描述 |
| **F2** | low | §3.1 #10 要求校验 `font_line/foot_x/title_max` 区间；实现只校验 font_line（0.9–1.8×font），foot_x/title_max 无检查 | 补 foot_x∈[0,1] 桶对/ title_max 合理区间检查（warn），或 spec 注明本轮只校验 font_line |
| **F3** | low | §3.1 #11 要求 `TOC<3` → WARN；实现无该检查——ghbq `toc_samples=1` 实测无 toc 相关 warning | 补 `toc_low_sample`（warn），并在 calib 输出中体现 |
| **F4** | low | spec §4.2 示例含 `"date_local"`，但 §4.1 要求“无时间戳”，实现按 §4.1 不输出 → 示例与实现矛盾 | 删示例字段或标 optional/注明由调用方填 |
| **F5** | low | t179/t183/docs §20 称「gate 侧车带 calib_warnings」，实际 sidecar 顶层是 `calib` 块，`calib_warnings` 列表仅在 `report.gate`；sidecar 只通过 reasons `calib_warn:*` 体现 | 把 warnings code 列表也写入 sidecar（`calib.warnings` 已有）并统一措辞，或修正文档表述 |

## 5. 结论

**t181 终审 verdict：needs_revision（FAIL）**。

- **通过**：schema/字段/容差（DPI 残差、coverage、font/baseline、render bp、单位）与 §2/§4 基本一致；warn 非阻断语义正确（ghbq baseline 2.073/gate PASS）；书无关；**渲染不变性**（ghbq 104/104、wz4 677/677 文本与像素一致，gate 96.8%/99.6% PASS）实测成立；35 单测通过。
- **不通过**：F1（FAIL 退出码未落地，medium）、F2/F3（TOC 自检缺 2 条）、F4/F5（文档/字段措辞）——与「自检/容差与契约一致」的验收标准不符。
- 修复建议：最小改动 = 补 TOC 两条 warn + 对齐 §3.2（实现退出码或修订 spec）+ 清理 date_local/calib_warnings 表述；随后以 ghbq 104 页 + wz4 677 页复跑确认渲染与门禁数字不变。

## 6. 复现

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_calib.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/review_wz4_calib.pdf --data-dir data/wz4 --skip-ocr --force
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py output/wz4/review_wz4_calib.pdf \
  data/wz4/wz4_spotting_coords.json data/wz4/wz4_spotting_lines.json --src-pdf source_pdf/wz4.pdf  # rc0
/usr/bin/python3 -m pytest src/test/unit/test_horizontal_calib.py src/test/unit/test_scan2pdf.py -q  # 35 passed
```

| 文件 | sha256 / 说明 |
|---|---|
| `src/utils/geometry.py` | `817c83a649a836eeec5d9b15c20590adca9970fa3e2067e54a05c04004b41204`（geometry.py） |
| `src/tools/scan2pdf.py` | `385db39254288e215fa5e11e55a6b946761e54eba7b972141a1d7f5e908455c0` |
| `output/ghbq_full/review_ghbq_calib.pdf.calib.json` | 1970 B；dpi139/page603×870/font16.5/baseline34.2 warn |
| `output/wz4/review_wz4_calib.pdf.calib.json` | 1922 B；dpi144/page418×634/font10.7/warnings=[] |
| HEAD | `abacb9c`（未 commit） |

---

# 附：横排标定审计 round-2 终审（t185，t184 修复 F1–F5）

> 审查人：质量审查员　日期：2026-11-09 21:50–22:20
> 对象：t184（修 t181 F1–F5）
> 依据：`spec/governance/HORIZONTAL_CALIB.md`、`docs/scan2pdf_v1.md` §20.2、t181 终审报告
> **结论：needs_revision（FAIL）** —— F2/F3/F4/F5 与代码侧 F1（fail→gate calib_fail/MANUAL_ONLY）实测**已修**，渲染零变化；但 **t184 报告称「spec §3.2 已按 captain 方案②修订」与实测不符**：`spec/governance/HORIZONTAL_CALIB.md` §3.2 仍写「FAIL 不静默：stdout + warnings + **退出码**」，与 §6（不阻断）及 docs §20.2 自相矛盾。按「报告说的与实测不符」标 **F1 high**（改 1 段文档即可），另 test 数字/覆盖为 low。

## 0. 复跑

- **ghbq 104 页**（`review_ghbq_calib2.pdf`）：exit 0、gate **PASS**（pitch **96.8%**、104=104）；calib warnings = `[baseline_font_ratio_out, toc_low_sample]`（**toc_low_sample 新增生效**，ghbq toc_samples=1）；selfcheck.verdict=warn。
- **wz4 677 页**（`review_wz4_calib2.pdf`）：exit 0、gate **PASS**（pitch **99.6%**、677=677）；warnings=[]、selfcheck=pass（toc_samples=11）。
- 单测：`test_horizontal_calib` **6 passed**、`test_scan2pdf` **30 passed**（合计 36）。
- 渲染零变化（逐页文本 + 关键页像素 + 字符）：
  - ghbq calib2 vs t181 calib vs t177 full：**104/104 页文本相同**、字符 49,262（去空白 44,739）、p1/51/104 像素相同；
  - wz4 calib2 vs t181 calib vs t165：**677/677 页文本相同**、字符 603,844（去空白 560,324）、p1/101/677 像素相同。

## 1. F1–F5 修复核对

| 项 | t184 声明 | 实测 | 结论 |
|---|---|---|---|
| **F1** | spec §3.2 按 captain 方案②修订；FAIL→gate reasons `calib_fail:<code>`，PASS→MANUAL_ONLY | 代码 ✓（scan2pdf.py L663-676：`_cf`→reasons `calib_fail:*`、v_ok 时 ve=MANUAL_ONLY/exit=8/review_required=True）；sidecar 有 `calib_fail`；**spec §3.2 原文未改**（L228 仍「+ 退出码」），与 §6 L439「不阻断」+ docs §20.2 矛盾 | **✗ F1（high）** |
| F2 | 补 toc_foot_x_out / toc_title_max_out | geometry.py L296-304：foot_x 桶对 0≤x0<x1≤1、title_max∈[10,80]，均 warn | ✓ |
| F3 | 补 toc_low_sample（toc_samples<3） | geometry.py L285-288；ghbq toc_samples=1 → warnings 含 `toc_low_sample` | ✓ |
| F4 | spec §4.2 删 date_local | `grep date_local spec/` = 0；字段与 §4.1 无时间戳一致 | ✓ |
| F5 | sidecar calib 块含 warnings/warnings_codes + calib_warnings/calib_fail | gate.json：`calib.warnings`、`calib.warnings_codes`、`calib_warnings`、`calib_fail` 均在；reasons `calib_warn:*`；docs §20.2 措辞已对齐 | ✓ |

## 2. 独立抽样（数值/语义）

- ghbq：dpi139（res 0.298）、page603×870（cov 1.013/1.003）、cw25、font16.5、baseline34.2（ratio 2.073→warn）、margin95、toc_samples1（→warn）；warn 不阻断（gate PASS、exit 0、refiew_required=false）。
- wz4：dpi144（res 0.094）、page418×634、font10.7、baseline17.8（1.664）、toc_samples11、warnings=[]、selfcheck=pass。
- 无书专属分支（`if book==`/书表 = 0；spec §5 参考基线未入代码）。

## 3. findings（must-fix）

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F1** | **high** | **t184 报告称「spec §3.2 按 captain 方案②修订」，但 spec §3.2 原文未改**：仍为「FAIL 不静默：stdout + calib.json.warnings[] + **退出码**；不得用兜底值假装成功」，与 §6（L439「fail 项写 selfcheck.verdict=fail，不阻断」）及 docs §20.2（「spec §3.2 改为…构建不阻断（exit 0）」）自相矛盾；属「把没修的写成修了」 | 按 captain 方案②实际修订 spec §3.2：删「+ 退出码」，改为「FAIL 项 = stderr + calib.warnings + selfcheck.verdict=fail；构建不阻断（exit 0），由 scan2pdf/gate 兜底（reasons `calib_fail:*`、PASS→MANUAL_ONLY）」；并与 §6 措辞统一 |
| **F2** | low | 新增「FAIL→gate calib_fail→PASS 转 MANUAL_ONLY」路径**无单测**（`grep calib test_scan2pdf` = 0）；当前只有代码审查+正常路径实测（ghbq/wz4 均无 fail 项，未触发） | 在 test_scan2pdf 加一例：伪造 `calib.json` warnings 含 severity=fail → 断言 reasons `calib_fail:*`、verdict_effective=MANUAL_ONLY、exit=8、review_required=true |
| **F3** | low | t184 报告「6 passed（+scan2pdf **35** passed）」与实测不符：test_scan2pdf **30 passed**（36 = 6+30；35 是 test_ocr_book+test_scan2pdf 的旧口径） | 更正报告数字（或说明合并口径） |

## 4. 结论

**t185 终审 verdict：needs_revision（FAIL）**。

- **通过**：F2/F3/F4/F5 全部实测修复；F1 的代码侧（calib_fail→gate/MANUAL_ONLY）实现正确；ghbq（96.8%）/wz4（99.6%）gate PASS、渲染零变化（文本/字符/像素）；warnings 非阻断语义正确；无书专属分支。
- **不通过**：**F1（high）**——spec §3.2 未按 t184 声明修订，契约仍与实现/§6/§20.2 矛盾（报告-实测不符）；F2/F3 low。
- 修复面：改 spec §3.2 一段 + 补 1 条 scan2pdf 单测 + 更正 t184 报告数字；随后只需复跑 ghbq/wz4（渲染与 gate 数字应不变）即可通过。

## 5. 复现

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_calib2.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/review_wz4_calib2.pdf --data-dir data/wz4 --skip-ocr --force
grep -n "退出码" spec/governance/HORIZONTAL_CALIB.md   # 仍命中 L228 → F1
/usr/bin/python3 -m pytest src/test/unit/test_horizontal_calib.py src/test/unit/test_scan2pdf.py -q  # 36 passed
```

| 文件 | sha256 / 说明 |
|---|---|
| `spec/governance/HORIZONTAL_CALIB.md` | 23,222 B / mtime 21:45（§3.2 未改） |
| `src/utils/geometry.py` | `266366a4a126503e58eef080ea75c8f9050c17838c8bc8f773f3b00bd72be5ff`（calib_selfcheck TOC 三项） |
| `src/tools/scan2pdf.py` | `38c0cef9905223ae7b6d71e2978d73cefb37d2497bf3742314fa65103cf60f63`（calib_fail → MANUAL_ONLY） |
| `output/ghbq_full/review_ghbq_calib2.pdf.gate.json` | PASS / calib_warnings 2 / calib_fail [] |
| `output/wz4/review_wz4_calib2.pdf.calib.json` | warnings=[] / selfcheck=pass |
| HEAD | `abacb9c`（未 commit） |

---

# 附：横排标定审计 round-3 终审（t187，t186 修复 F1–F3）

> 审查人：质量审查员　日期：2026-11-09 22:00–22:25
> 对象：t186（修 t185 F1–F3）
> 依据：`spec/governance/HORIZONTAL_CALIB.md`、`docs/scan2pdf_v1.md` §20.2/§20.3、t185 终审
> **结论：PASS** —— t185 的 F1/F2/F3 均已真实落地：spec §3.2 已按 captain 决策改写（`grep 退出码` = 0）；新增 `test_geom_calib_fail_forces_manual` 覆盖「calib fail→gate calib_fail→PASS 降 MANUAL_ONLY/exit 8/review_required」；docs §20.3 单测口径已更正。ghbq 104 页（96.8%）/wz4 677 页（99.6%）gate PASS 且渲染零变化。无新 blocker。

## 0. F1–F3 核对

| 项 | 声明 | 实测 | 结论 |
|---|---|---|---|
| **F1** | spec §3.2 按 captain 写法替换；`grep 退出码` = 0 | `grep -c 退出码 spec/governance/HORIZONTAL_CALIB.md` = **0**；§3.2 现文：「FAIL 项 = stdout + calib.warnings[] + selfcheck.verdict=fail；**构建不阻断（exit 0）**，由 scan2pdf/gate 兜底：calib_fail:<code>、PASS→MANUAL_ONLY（review_required=true）」；与 §6「fail 项写 selfcheck.verdict=fail，不阻断」及 docs §20.2 一致 | ✓ 已修 |
| **F2** | 新增 test_geom_calib_fail_forces_manual（test_scan2pdf.py） | 测试存在且为真实 `main()` 流程：monkeypatch build_pdf（写含 severity=fail warnings 的 calib）+ run_verify_geom（PASS）→ 断言 `rc=EXIT['manual']`、gate.reasons 含 `calib_fail:pages_mismatch`、`verdict_effective=MANUAL_ONLY`、`review_required=True`、`calib_fail=['pages_mismatch']`；**通过** | ✓ 已修 |
| **F3** | docs §20.3 更正 test 数字 | §20.3：calib **6** / scan2pdf **30**（t185 时点）=36；t184 的「6+35」中 35=ocr_book 5+scan2pdf 30；加 F2 后 scan2pdf **31**、合计 **37**；实测 `pytest test_horizontal_calib test_scan2pdf` → **37 passed** | ✓ 已修 |

## 1. 独立复跑

- **ghbq 104 页**（`review_ghbq_calib3.pdf`）：exit 0、gate **PASS**（pitch **96.8%**、104=104）；calib warnings `[baseline_font_ratio_out, toc_low_sample]`、selfcheck=warn；`calib_fail=[]`、reasons 两条 `calib_warn:*`；**文本 104/104 页与 calib2 相同**。
- **wz4 677 页**（`review_wz4_calib3.pdf`）：exit 0、gate **PASS**（pitch **99.6%**、677=677）；warnings=[]、selfcheck=pass（toc_samples=11）、`calib_fail=[]`、reasons=[]；**文本 677/677 页相同、字符 603,844 相同、p1/p101/p677 像素相同**。
- 单测：**37 passed**（calib 6 + scan2pdf 31）。
- spec 一致性：`date_local` 仍不存在（§4.1 无时间戳）；§4.2 无该字段；§2/§3 容差未变；无书专属分支（`if book==`/书表 = 0）。

## 2. warnings 语义（最终态）

- warn（baseline_font_ratio_out / toc_low_sample）：写 calib.warnings + stderr + sidecar `calib.warnings`/`calib_warnings` + reasons `calib_warn:*`，**gate PASS/exit 0 不变** ✓。
- FAIL（如 pages_mismatch）：**不阻断 build（exit 0）**，但 scan2pdf gate 写 `calib_fail:<code>` 且 PASS→MANUAL_ONLY/exit 8/review_required=true（F2 单测 + code 双证）✓；与 captain 决策、spec §3.2、docs §20.2 一致。
- `HORIZ_CALIB_STRICT` 仍为 spec 标注的「规划」项（未强制）——如实保留，不阻塞。

## 3. 渲染不变性

- ghbq：calib3 vs calib2 → 104/104 页文本相同；calib2 vs t177 full 已证像素相同（上一轮），本轮文本一致 → 渲染零变化。
- wz4：calib3 vs calib2 → 677/677 页文本相同、字符 603,844 相同、3 页像素相同；calib2 vs t181/t165 已证一致。
- 两书 gate 数字保持 96.8% / 99.6% PASS，与 calib 前相同 ✓。

## 4. 残留（非阻断）

| id | severity | problem | 建议 |
|---|---|---|---|
| R1 | low | `HORIZ_CALIB_STRICT` 仅记录 env，未实现（spec 标“规划”） | 保持登记；实现时按 spec §3.2 升级 WARN→FAIL 并退出 |
| R2 | low | calib_fail 单测为 monkeypatch 流程（不跑真实 build_geom） | 已有真实 E2E（ghbq/wz4）覆盖正常路径，可接受 |

## 5. 结论

**t187 终审 verdict：PASS**。

- **通过**：F1（spec §3.2 已真实改写、无“退出码”残留）、F2（fail→MANUAL_ONLY 单测断言四项全）、F3（test 口径 37 与实际一致）；ghbq/wz4 gate PASS 且渲染零变化；字段/自检/容差与契约一致；warn/fail 语义与 captain 决策一致；无书专属分支。
- **结论**：横排标定审计（HORIZONTAL_CALIB v1 + calib.json + selfcheck + gate 兜底）可收口；R1/R2 为后续低风险项。

## 6. 复现

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_calib3.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/review_wz4_calib3.pdf --data-dir data/wz4 --skip-ocr --force
grep -c "退出码" spec/governance/HORIZONTAL_CALIB.md          # 0
/usr/bin/python3 -m pytest src/test/unit/test_horizontal_calib.py src/test/unit/test_scan2pdf.py -q  # 37 passed
```

| 文件 | sha256 |
|---|---|
| `spec/governance/HORIZONTAL_CALIB.md` | `3e0c2f02d240a97b29d6632282a2bb275aa0502b3433c7460cb5c491c400609f` |
| `src/utils/geometry.py` | `266366a4a126503e58eef080ea75c8f9050c17838c8bc8f773f3b00bd72be5ff` |
| `src/tools/scan2pdf.py` | `38c0cef9905223ae7b6d71e2978d73cefb37d2497bf3742314fa65103cf60f63` |
| `src/test/unit/test_scan2pdf.py` | `3c727a5f9e346d37f1407d716d70c3a136c204776a519474c579a9b4b984bb2e` |
| `src/test/unit/test_horizontal_calib.py` | `3f2ac0e6be6218859040495511848790f7ba70a383a08eab69ccfc700ae25656` |
| HEAD | `abacb9c`（未 commit） |

---

# 附：GMPG 泄漏修复终审（t190，t188/t189）

> 审查人：质量审查员　日期：2026-11-09 23:43–00:05
> 对象：t188（fit_common pass2 去 VERIFY_MARK）+ t189 独立验收
> 依据：`AGENTS.md` #42、`docs/scan2pdf_v1.md` §21、t189 验收报告
> **结论：PASS（有条件）** —— 根因/修复正确（pass1 带标记、pass2 交付不带），ghbq/wz4 交付 GMPG=0、gate 数字不变、文本/渲染不变；无标记回退在 1:1 下正确，溢出页由「页数 1:1」硬约束兜住。残留：docs §21 的 E2E 字符数与实测不符（low）、PIPELINE_BEHAVIOR 契约待补（low）。

## 0. 复跑（任务给定命令）

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_nomark.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
# [scan2pdf] ghbq: pipeline=geom gate=PASS exit=0
```

- **ghbq**：104 页、**GMPG span = 0**（旧 104）、104=104、gate **PASS pitch 96.8%**、exit 0；calib `render` 600.75×866.75 / font 16.44 / pitch 34.21（与 t187 一致）。
- **wz4**（补充独立构建）：677 页、**GMPG = 0**（旧 677）、677=677、gate **PASS pitch 99.6%**；calib render 416.44×631.63 / font 10.66 / pitch 17.67（与 t189 一致）。
- 单测：`test_fit_common_verify_mark` 4 + `test_fit_common_cleanup` 2 + `test_scan2pdf` 31 → **37 passed**。

## 1. 根因与修复核对

| 项 | 实测 |
|---|---|
| 根因 | `fit_common.render()` 原两趟都 `env['VERIFY_MARK']='1'`；pass2 即交付物 → 每页 1 处 `GMPG<k>ZZ` 进文本层（ghbq 104、wz4 677、历史 wz4_optimized 677） |
| 修复 | `render(..., verify_mark=True)`：pass1 `True`（`measure_heights` 归组需要）、pass2 `False` 且 **`env.pop('VERIFY_MARK')`**（继承 shell 也不泄漏）；`main()` 两处调用一致（L88/L105） |
| classic 路径 | 共用 `fit_common.main`，同一 render → 同源生效；单测 `test_render_verify_mark_env` 断言两趟 `[True, False]`，`test_main_two_passes` 覆盖 build_geom/build_classic |
| 交付口径 | 交付 PDF `get_text` 无 `GMPG`；pass1 临时 PDF 仍有标记（不交付） |

## 2. 独立抽检（文本/渲染不变性）

- **文本**：删除 `GMPG<k>ZZ` + 空白归一后逐页对比旧产物 → **ghbq 0/104、wz4 0/677 页差异**。
- **像素**：ghbq p1/p51/p104、wz4 p1/p101/p677 的差异像素仅落在页底标记区（ghbq y≈1800/1806@150dpi、wz4 y≈874/876@150dpi，x 页左缘）→ 标记移除，正文渲染不变。
- **字符差**：ghbq 旧 raw **49,262** → 新 **48,332**，差 **930 = 826（104×8 字符 GMPG）+104 换行**，可解释（wz4 同构）。
- **校准值**：两书 calib `render`/page/dpi/font/pitch 与修复前一致；ratio 表未暴露变化，页数/pitch 不变。

## 3. 风险审查（无标记回退）

- `verify_geom`：无标记时走「按序号 1:1」回退（`out_by_key[src_keys[i]] = out[i]`）；页数 1:1 是其**硬约束**（`n_src != n_out` → 退出码 FAIL），因此**溢出页**（一个源页渲成多物理页）会先被页数不 1:1 拦截，不会静默错配。
- 边界：若「一页溢出 + 另一页丢失」恰好抵消使 n_out==n_src，回退按序号会错位；marked 模式可检出「源页溢成多物理页/缺页」，无标记模式不能。属低风险残留（构建本身按 1 源页 1 页架构，且 gate 的 pitch/页高会异常）；建议后续在 PIPELINE_BEHAVIOR 注明「交付无标记，溢出检测依赖页数 1:1」。
- 无标记对 gate 数字无影响：ghbq/wz4 的 `verify_geom` 独立跑均 rc=0，数字与带标记时一致（96.8%/99.6%）。

## 4. 文档/AGENTS 一致性

- `AGENTS.md` #42 与实现/实测一致（根因、修复、ghbq 104/wz4 677、历史 wz4_optimized 677）。
- `docs/scan2pdf_v1.md` §21 与实现一致；**但 E2E 字符数「47,059→46,233」与实测不符**：当前所有 104 页 ghbq 产物 raw 均为 49,262 → 新 48,332（见 F1）。
- `spec/governance/PIPELINE_BEHAVIOR.md` 尚未补「VERIFY_MARK 仅 pass1 / 交付无 GMPG」契约（t188 已登记后续；属 api-compat 必改项，见 F2）。

## 5. findings

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F1** | low | docs §21 E2E 字符数写「ghbq 47,059→46,233」，实测当前 ghbq 104 页产物为 **49,262→48,332**（差 930=826+104 换行）；数字来源不明/口径不一 | 按实测更正 §21（或注明统计口径） |
| **F2** | low | PIPELINE_BEHAVIOR 未补「VERIFY_MARK 仅 pass1、交付无 GMPG、无标记时 verify 按序号 1:1 且溢出由页数硬约束兜底」——env/产物文本层属 api-compat 契约 | 后续单开 spec 同步（AGENTS §4 清单要求） |
| **F3** | low | 无标记回退下「溢出+缺页抵消」边界无法检出（marked 模式可） | 文档注明；如需强保证，可保留「verify 用带标记副本」的选项 |

## 6. 结论

**t190 终审 verdict：PASS（有条件）**。

- **通过**：根因关闭（pass2 不再设 VERIFY_MARK，含 shell 继承）；ghbq/wz4 交付 GMPG=0、gate 数字与页数不变；文本归一后 0 diff、像素差仅标记区；classic 同源生效；verify_geom 1:1 回退正确且溢出由硬约束拦截；37 单测通过。
- **条件**：F1（docs 数字）、F2（PIPELINE_BEHAVIOR 契约）为低风险跟进；F3 文档注明即可。

## 7. 复现

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_nomark.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/review_wz4_nomark.pdf --data-dir data/wz4 --skip-ocr --force
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py output/ghbq_full/review_ghbq_nomark.pdf \
  output/ghbq_full/_ocr_ghbq/ghbq_spotting_coords.json output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json \
  --src-pdf source_pdf/ghbq.pdf        # rc 0；原文「对齐: 按序号 1:1」
/usr/bin/python3 -m pytest src/test/unit/test_fit_common_verify_mark.py src/test/unit/test_fit_common_cleanup.py src/test/unit/test_scan2pdf.py -q  # 37 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/calibration/fit_common.py` | `8883395b932f594308f9492efa95b5b23d54acf7863404578a16b68f2280ca0e` |
| `output/ghbq_full/review_ghbq_nomark.pdf` | md5 `c88d768a7d30fc9d888a09876b33dd0a` / 104 页 / GMPG 0 |
| `output/wz4/review_wz4_nomark.pdf` | md5 `5a3f0daa3346713cd834edc6f559b300` / 677 页 / GMPG 0 |
| HEAD | `00a44f7`（未 commit） |

---

# 附：LAYJSON + 图片 passthrough 终审（t194，t192/t193 + t195/t196）

> 审查人：质量审查员　日期：2026-11-10 21:33–22:05
> 对象：t192（LAYJSON 接线 + 图片 passthrough）+ t193 验收 + t195/t196 修复
> 依据：`spec/governance/PAGE_IMAGE_LAYOUT.md`、`docs/scan2pdf_v1.md` §22、`AGENTS.md` #43/#44
> **结论：needs_revision（FAIL）** —— LAYJSON schema/页序/坐标换算/默认关/零回归均实测通过，图片 passthrough 在 p1/p2/p3 生效；但 **开启 LAYOUT_FIGS（或 --layout）后，目录页 aside 页码列被当旁注重复渲染**（p11/p104，--layout 时 p12 也重复），文本层多出数字串、版面重复；另 p3 图版页整页文字被 3 Tr 全隐藏（源页可见标题不可见）。两项需修。

## 0. 复跑

- **默认（任务给定命令，无 --layout）** `review_ghbq_img.pdf`：104 页、GMPG 0、layout `disabled`、gate PASS 96.8%、104=104；与 t190 `review_ghbq_nomark.pdf` 逐页文本 **0 diff**、字符相同（默认关零回归 ✓）。
- **`--layout`**（`review_ghbq_img_figs2.pdf`）：104 页、LAYJSON 104 页（sha `5fda796f…`）、图片页 p1/p2/p3/p4/p23/p29/p37/p100/p102、GMPG 0、gate PASS 96.8%、104=104；p1 封面、p2 条形码、p3 图版照片可见；非空白字符 43,954（默认 43,913，不减少）。
- **`LAYOUT_FIGS=1` only**（`review_ghbq_figs_only.pdf`）：同样图片页、gate PASS 96.8%；文本与默认 diff 页 = **[11, 104]**。
- **wz4 默认**（无 LAYJSON）：677 页、GMPG 0、layout disabled、gate PASS 99.6%；与 t190 nomark 文本 **0 diff**、非空白字符 554,341 相同（零回归 ✓）。

## 1. 契约核对（t191 spec）

| 契约 | 实测 |
|---|---|
| layout.json schema（page_key/page/width/height/page_width_pt/height/bbox_space/blocks/prunedResult） | 104 页、list、字段齐全；blocks 5/页起；`jobs.pages` 0-based 页序 ✓ |
| bbox 换算逐页 src/layout 尺度 | p1 image block [0,663,1191,1470] ×(595.28/1191) → 产物图 rect [0,330.2,593.0,732.2]，误差 ≤2.5pt ✓ |
| 开关默认关 | 默认 `layout disabled`、无图块/旁注日志；wz4/ghbq 文本与旧版 0 diff ✓ |
| 图块 passthrough | p1 封面 1 图、p2 条形码 1 图、p3 图版 1 图、p4 1 图；坐标与源图并排一致 ✓ |
| 文本层不删 | 图内文字改 3 Tr（可搜），无删字；非空白字符 43,913→43,954 ✓ |
| 无书专属分支 | `grep ghbq/wz4/wz2` 于 scan2pdf/ocr_book/build_geom（非注释）0 命中 ✓ |

## 2. findings

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F1** | **high** | **目录页 aside 页码列重复渲染**：`LAYOUT_FIGS=1` 时 p11 末尾多出 `26123111521212426`（= again 2,3,11,15,21,21,24,26）、p104 多 `92`；`--layout` 时 p12 再多 `2334043494951566572727886`。视觉上 p11 左侧出现页码列**且**条目内联页码保留 → 重复；文本层被污染（字符 +32/+41） | TOC 页（header=目录/CONTENTS 或 aside 为纯数字列）跳过 aside 渲染，或与条目内联页码去重；`aside_text` 只在非 TOC 页启用；补单测锁定 p11/p12/p104 文本与默认一致 |
| **F2** | medium | **p3 图版页整页文字 3 Tr**（含 layout 中在 image bbox 上方的 doc_title）→ 源页可见标题在产物中不可见（over-hide）；texttrace p3 types={3:18} | image-page 策略改为「仅隐藏与 image bbox 相交/图内 span」，图外标题保持可见；p3 标题应可见 |
| **F3** | low | p1 `footer_image`（出版社 logo，layout bbox [333,1559,823,1626]）未贴回：blocks 有 2 图，产物 p1 仅 1 图 | 补 footer_image 图块裁贴或登记为已知限制 |
| **F4** | low | `PAGE_IMAGE_LAYOUT.md` §4 仍写「默认关=不传 LAYJSON」，与实现（`--layout` 显式开 / env 可开）措辞未同步（t195 已登记） | 同步 spec §4 |
| **F5** | low | p2 ISBN span 与 chart 顶重叠 1287pt²（源页本身重复叠放）；视觉无碍 | 登记即可 |
| **F6** | low | 图片验收需显式 `--layout`（任务默认命令不含）；默认构建无图 | 验收命令/文档注明「图片需 --layout」 |
| **F7** | low | p10 丛书目录作者列未做（LAYOUT_TOC 仅 p11 aside；S8 残留） | 留给 S8 |

## 3. 风险/说明

- **零回归成立**：默认（不传 LAYJSON）ghbq/wz4 与旧版逐页文本 0 diff、页数/pitch/gate 不变；仅显式开启 layout 才引入图块/旁注路径。
- **F1 是开关路径的缺陷**，不影响默认交付；但 `--layout` 正是图片验收所用产物，且污染 TOC 文本层，需修复后才能把 LAYOUT_FIGS 作为可用特性。
- **F2** 属可见性策略：文本没删（可搜），但源页标题不可见，与「图版页与源图并排」不符。

## 4. 结论

**t194 终审 verdict：needs_revision（FAIL）**。

- **通过**：LAYJSON 转换/页序/坐标、开关默认关、默认零回归（ghbq/wz4 0 diff）、图片 passthrough（p1 封面/p2 条形码/p3 图版）、GMPG 0、gate 96.8%/99.6%、文本不减少、无书专属分支。
- **不通过**：F1（high，TOC aside 页码重复/文本污染）、F2（medium，p3 全页 3 Tr 过度隐藏）；F3–F7 low。
- 建议修复：F1 在 TOC 页禁用 aside 渲染/去重 + 单测 p11/p12/p104；F2 按 bbox 相交隐藏；同步 spec §4（F4）；补 footer_image（F3）。

## 5. 复现

```bash
cd /opt/test
# 默认（零回归）
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_img.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
# 图片/LAYJSON
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_img_figs2.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force --layout
# 仅 FIG（隔离 TOC 影响）
LAYOUT_FIGS=1 /usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_figs_only.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
# wz4 默认
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/review_wz4_layoutoff.pdf --data-dir data/wz4 --skip-ocr --force
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/scan2pdf.py` | `0986328f70cf40ad44b0bb1320189eca1b21cf45e68a7c4c2bfc5133524f69a6` |
| `src/tools/ocr_book.py` | `2a2273827036b93203a201045b39ea731f1c25a11b0070c1b43daf825ccfb1b6` |
| `src/pipelines/build_geom.py` | `526dc654b981824c411b021ab5326a237b41e353bdb3eb04a2e614d93e3aeb79` |
| `output/ghbq_full/review_ghbq_img.pdf`（默认） | 104 页 / GMPG 0 / layout disabled |
| `output/ghbq_full/review_ghbq_img_figs2.pdf`（--layout） | 104 页 / 9 页含图 / GMPG 0 |
| `output/wz4/review_wz4_layoutoff.pdf`（默认） | 677 页 / GMPG 0 / 与 t190 0 diff |
| HEAD | `f82cafc`（未 commit） |

---

# 附：LAYJSON + 图片 passthrough round-2 终审（t198，t197 修复 F1–F4/F6）

> 审查人：质量审查员　日期：2026-11-10 21:52–22:20
> 对象：t197（修 t194 F1/F2/F3/F4/F6）
> 依据：`spec/governance/PAGE_IMAGE_LAYOUT.md` §4、`docs/scan2pdf_v1.md` §22、t194 终审
> **结论：PASS（有条件）** —— F1（TOC aside 重复）、F2（p3 过度隐藏）、F3（footer_image）、F4（spec 默认关措辞）、F6（--layout 说明）均实测修复；默认零回归（ghbq/wz4 0 diff）；`--layout` 文本与默认 104/104 一致、p3 标题可见、p1 封面+页脚图/ p2 条码可见；42 单测通过。残留仅 F5/F7 低风险登记项。

## 0. F1–F4/F6 核对

| 项 | 声明 | 实测 | 结论 |
|---|---|---|---|
| **F1** TOC aside 重复 | TOC 页跳过 aside；layout 页码只用直接 number block；p11/p12/p104 文本与默认逐字相同 | `--layout` 产物 vs 默认：**104/104 页文本 0 diff**；p11/p12/p104 无额外数字串；代码 `_TOC_PAGE` 页 `_lay_num=None`、`_asides` 跳过（L996/L1015） | ✓ |
| **F2** p3 过度隐藏 | 去整页 3 Tr；仅相交 >5% 且 >20pt² 的 span 置 3 Tr；doc_title 保持可见 | texttrace：p3 **{0:18}（全可见）**、p1 {0:29,3:9}（标题可见、出版者图内不可见）、p2 {0:371}；代码 L911 相交阈值 | ✓ |
| **F3** footer_image | 恢复裁贴；p1 2 图 | p1 图片数 **2**（封面+页脚 logo）；p2 1、p3 1、p4 2、p23 2、p37 2 等 | ✓ |
| **F4** spec §4 | 默认不自动传 LAYJSON；显式 --layout/env 才传 | spec L232 已写「scan2pdf 默认不自动传 LAYJSON…」；report 默认 `layout=disabled` | ✓ |
| **F6** --layout 说明 | docs 注明图片验收需 --layout | docs §22 L307 已注明 | ✓ |

## 1. 独立复跑

- **默认（任务命令）** `review_ghbq_img2.pdf`：104 页、GMPG 0、layout disabled、gate PASS 96.8、非空白字符 **43,913**；与 t190 `review_ghbq_nomark.pdf` 逐页文本 **0 diff**。
- **`--layout`** `review_ghbq_img2_figs.pdf`：104 页、LAYJSON 104（sha `5fda796f…`）、GMPG 0、gate PASS 96.8、104=104；图片页 p1(2)/p2(1)/p3(1)/p4(2)/p23(2)/p29(1)/p37(2)/p100(1)/p102(1)；非空白字符 **43,913（不减少）**；与默认文本 **0 diff**。
- **独立抽样（源图并排）**：p1 封面照片 + 页脚出版社 logo 均可见；p2 条形码可见（ISBN 细条保持可见）；p3 标题「马尔巴乔夫与 / 一 人道的民主的社会主义」**可见**（源页标题在照片上方，产物同位置）。对照图 `tmp_vert/scan2pdf/t198_img_compare.png`。
- **wz4 默认（无 LAYJSON）** `review_wz4_layoutoff2.pdf`：677 页、GMPG 0、layout disabled、gate PASS 99.6、677=677；与 t190 nomark 文本 **0 diff**、非空白字符 554,341 相同。
- **单测**：`test_page_image` + `test_scan2pdf` + `test_ocr_book` → **42 passed**。
- **无书专属分支**：ghbq/wz4/wz2 等仅出现在注释；无 `if book`/页白名单。

## 2. 残留（非阻断）

| id | severity | problem | 处理 |
|---|---|---|---|
| F5 | low | p2 ISBN span 与 chart 顶重叠 1287pt²（源页本身重复叠放），现保持可见 | 已登记；视觉无碍 |
| F7 | low | p10 丛书目录作者列未做（LAYOUT_TOC 仅 p11；S8 残留） | 留 S8 |
| R1 | low | p3 标题 OCR 仍为「马尔巴乔夫」（源「戈尔巴乔夫」）——属 A4 per-book 校正表，不在本任务范围 | 随 A4 处理 |
| R2 | low | LAYOUT_HEADINGS 默认仍 0（标题块修复 S2 未启），本任务只验证图块/TOC 最小路径 | 随 S2 处理 |

## 3. 结论

**t198 终审 verdict：PASS（有条件）**。

- **通过**：F1/F2/F3/F4/F6 全部实测修复；默认零回归（ghbq 104、wz4 677 文本 0 diff）；`--layout` 文本与默认一致、p1/p2/图版可见、图内文字 3 Tr 不删字、GMPG 0、gate 96.8%/99.6%；坐标换算/schema/页序与 spec 一致；42 单测通过；文档/AGENTS 同步。
- **条件**：F5/F7/R1/R2 为登记项；其中 R1（标题 OCR 错字）由 A4 per-book 校正表处理，R2（LAYOUT_HEADINGS）随 S2。

## 4. 复现

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_img2.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_img2_figs.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force --layout
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/review_wz4_layoutoff2.pdf --data-dir data/wz4 --skip-ocr --force
/usr/bin/python3 -m pytest src/test/unit/test_page_image.py src/test/unit/test_scan2pdf.py src/test/unit/test_ocr_book.py -q  # 42 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/pipelines/build_geom.py` | `7c7258b870defb1d5170a13d01b303a70a5e8b385b6a9064f6384beb0c961607` |
| `src/tools/scan2pdf.py` | `0986328f70cf40ad44b0bb1320189eca1b21cf45e68a7c4c2bfc5133524f69a6` |
| `src/tools/ocr_book.py` | `2a2273827036b93203a201045b39ea731f1c25a11b0070c1b43daf825ccfb1b6` |
| `output/ghbq_full/review_ghbq_img2.pdf`（默认） | md5 `daa0efcb65ece6ac7d8825e6ffb6a35a` / 104 页 |
| `output/ghbq_full/review_ghbq_img2_figs.pdf`（--layout） | md5 `5c239d78cbcd7e12fa0d811469175f54` / 104 页 / 9 页含图 |
| `output/wz4/review_wz4_layoutoff2.pdf`（默认） | md5 `de6f4bdc627ad134688cad6157ef211d` / 677 页 |
| HEAD | `f82cafc`（未 commit） |

---

# 附：整页叠加终审（t201，t199/t200）

> 审查人：质量审查员　日期：2026-11-10 22:22–22:50
> 对象：t199（PAGE_IMAGE_FULL_RATIO 整页叠加）+ t200 验收
> 依据：`spec/governance/PAGE_IMAGE_LAYOUT.md` §2/§4、`docs/scan2pdf_v1.md` §23、`AGENTS.md` #45
> **结论：PASS（有条件）** —— 面积比阈值/整页 raster/全文字 3 Tr/未达阈值页不变均实测成立；p1/p3 与源页并排基本一致；默认零回归（ghbq/wz4 0 diff）；43 单测通过。残留：raster 纵横比拉伸 ~0.8%（低）、p3 文本层仍含 OCR 错字（可见由源图覆盖，A4 处理）、全隐文本的可选中/无障碍语义（低）。

## 0. 复跑（任务给定命令）

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_fullpage.pdf \
  --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force --layout
# [scan2pdf] ghbq: pipeline=geom gate=PASS exit=0
```

- ghbq：104 页、GMPG **0**、layout 104、gate **PASS pitch 96.8%**、104=104；非空白字符 **43,913**（=默认，不减少）。
- **p1**：源页 raster 1654×2407，rect **(0,0,600.8,866.8)** 覆盖整页；文本 38 字符全 **type3**（get_text 保留，可搜）。
- **p3**：raster 1654×2415，rect (0,0,600.8,866.8)；文本 18 字符全 **type3**。
- **p2**：chart 429×343（rect 394.9,657.0–548.7,780.0）不触发；文本全 **type0**；与 `PAGE_IMAGE_FULL_RATIO=0.99` 版一致。
- 未达阈值版（`PAGE_IMAGE_FULL_RATIO=0.99`）：p1 2 图/1400+ 文本可见、p3 标题可见；与 fullpage 版 **104/104 页文本全等（0 diff）**。
- wz4 默认（无 LAYJSON）：677 页、GMPG 0、layout disabled、gate PASS 99.6、677=677；与 t190 nomark **文本 0 diff**、字符 554,341 相同。
- 单测：`test_page_image` 5 + `test_scan2pdf` + `test_ocr_book` → **43 passed**。
- 目视对照（`tmp_vert/scan2pdf/t201_fullpage_compare.png`）：p1/p3 与源页**基本逐像素一致**；p2 与 ratio0.99 版一致（条形码可见、正文重排）。

## 1. 契约/代码核对

| 契约（spec §2/§4） | 实测 |
|---|---|
| 面积比 = image/figure/chart/header_image/footer_image 并集 / 页面积 | `_lay_img_cov` 并集；p1 cov 0.466、p3 0.470、p2 0.037（数据决定，非书/页白名单） ✓ |
| 阈值 `PAGE_IMAGE_FULL_RATIO` 默认 0.40，env 可覆盖 | L298 默认 0.40；`_image_page_full()` ≥ 比较；0.99 版行为正确 ✓ |
| 整页 raster 尺寸/位置 | p1/p3 rect = 页幅 600.8×866.8，`\AddToShipoutPictureBG` 铺满 ✓ |
| 本页文本全隐 + 可搜 + 字符不减少 | p1/p3 texttrace 全 type3；`get_text` 保留；非空白字符 43,913 = 默认 ✓ |
| 未达阈值页不变 | p2 与 ratio0.99 版图像/文本一致；全页文本 104/104 相同 ✓ |
| 默认关零回归 | 未传 LAYJSON 时 ghbq/wz4 与旧版 0 diff、gate 96.8%/99.6% ✓ |
| 无书专属分支 | `_image_page_full` 只看 cov；grep 书名为注释 ✓ |

## 2. 残留（非阻断）

| id | severity | problem | 处理 |
|---|---|---|---|
| R1 | low | p1/p3 raster 纵横比与页幅差 ~0.8–0.9%（1654×2407 vs 600.8×866.8），轻微拉伸 | t200 已登记「视觉无感」；如需精确可按页幅 crop/scale |
| R2 | low | p3 文本层仍是 OCR 错字「马尔巴乔夫」（可见由源图覆盖，但搜索/复制得到错字） | 随 A4 per-book 校正表处理 |
| R3 | low | 全页文本 type3：文本可搜但不可选中/可见（无障碍/选取语义退化） | 设计取舍，文档已注明「invisible overlay」；可接受 |
| R4 | low | 整页叠加后该页不再有文本重排/字号校准（纯源图） | 设计目的（还原度优先），已登记 |

## 3. 结论

**t201 终审 verdict：PASS（有条件）**。

- **通过**：面积比规则/阈值/整页 raster 尺寸位置/文本全隐可搜/未达阈值页不变全部实测成立；p1/p3 与源页并排基本一致；p2 不变；默认零回归（ghbq/wz4 0 diff、gate 96.8%/99.6%）；43 单测通过；spec §2/§4、docs §23、AGENTS #45 一致；无书专属分支。
- **条件**：R1–R4 为低风险登记项（拉伸/文本层 OCR 错字/不可选中语义/无重排），不阻断收口。

## 4. 复现

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_fullpage.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force --layout
PAGE_IMAGE_FULL_RATIO=0.99 /usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_nofull.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force --layout
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/review_wz4_layoutoff3.pdf --data-dir data/wz4 --skip-ocr --force
/usr/bin/python3 -m pytest src/test/unit/test_page_image.py src/test/unit/test_scan2pdf.py src/test/unit/test_ocr_book.py -q  # 43 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/pipelines/build_geom.py` | `f882c60d14c080b8ff25741dbb0ab99794efe0751fba47c5b385da65cf2b8a6d` |
| `src/test/unit/test_page_image.py` | `a716040827b431e0f7b8f397637d61119626bbce55a799016d39dce555033214` |
| `output/ghbq_full/review_ghbq_fullpage.pdf` | md5 `43e3eca06ba10542f9c966f9510b773f` / 104 页 |
| `output/ghbq_full/review_ghbq_nofull.pdf`（0.99） | md5 `1d8150b8aac43e01dff0ace4cd27f897` / 104 页 |
| `output/wz4/review_wz4_layoutoff3.pdf` | md5 `71de4550b0aab9d7b4f7c0e942f7737d` / 677 页 |
| HEAD | `70a5987`（未 commit） |

---

# 附：corrected_text 每书文本校正终审（t205，t203/t204）

> 审查人：质量审查员　日期：2026-11-10 22:58–23:25
> 对象：t203（corrected_text 通道 + scan2pdf 接入）+ t204 验收
> 依据：`spec/governance/CORRECTED_TEXT.md`（t202 契约）、`docs/scan2pdf_v1.md` §24、`AGENTS.md` #46
> **结论：needs_revision（FAIL）** —— 功能与零回归实测通过（p3 校正、空表/未知项、wz4 无文件 0 diff、39 单测），但 **report 审计字段与 t202 契约 §3.3 不一致**（`pages` 类型、`replaced/applied` 命名、`line_counts` 结构、`warnings` 元素结构、`source` 取值），属「审计字段」验收项不通过；另有 warnings 未写 stderr、换行未校验等 low。

## 0. 复跑

- **默认（任务命令）** `review_ghbq_corrected.pdf`：104 页、GMPG 0、gate **PASS 96.8%**、104=104、nospace **43,913**；p3 文本层 = `戈尔巴乔夫与 / “人道的民主的社会主义”`，全文**无**「马尔巴乔夫」；coords sha `889ade99…` 与报告一致（未变）。
- **空表**（`--corrected-text /tmp/empty_ct.json`）：exit 0、gate 96.8、applied 0；与默认校正版文本 diff **仅 p3**（[3]）→ 校正作用域正确。
- **未知表**（page999 / line2:99 / line2:abc / page:"bad"）：exit 0、gate 96.8、applied 0、**skipped 4**、warnings 4 条；文本与空表版 **104/104 0 diff**。
- **wz4 无校正文件**：677 页、gate **PASS 99.6%**、corrected `enabled=false`、文本与 t190 nomark **0 diff**、nospace 554,341 相同。
- 单测：`test_corrected_text` 6 + `test_scan2pdf` → **39 passed**。
- 代码：应用时机 = lines 加载后、`--pages` 切片前（L569-597 / L666）✓；优先级 explicit > book_data ✓；显式缺失 exit2、默认缺失 disabled ✓；coords/页数/行数不变 ✓；无书专属分支（仅路径按 book 拼接）✓。

## 1. findings（must-fix）

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F1** | **medium** | **report `corrected_text` 审计字段与 spec §3.3 不一致**：① `pages`：spec 为页 key 数组 `["2"]`，实现为计数 `1`；② `replaced`：spec 字段名，实现只给 `applied`（无 `replaced`）；③ `line_counts`：spec 为 `{"2":{"before":2,"after":2}}`，实现为 `{"2":2}`；④ `warnings`：spec 为对象数组 `{code,page,line,message}`，实现为字符串数组（`unknown_page:999` 等）；⑤ 无文件时 `source`：spec 为 `disabled`，实现为 `none`。docs §24 也照实现写成 `applied`，与 spec 冲突 | 二选一并同步 docs：①实现按 spec 输出（`replaced`、`pages` 数组、`line_counts.before/after`、warnings 对象、`source=disabled`）；②修订 spec §3.3 并注明兼容字段（同时更新 docs §24）。审计 schema 是交付契约，不能两套 |
| **F2** | low | spec §3.3 要求「同一 warnings 同步写 stderr（用户可见）」；实测未知表构建日志无任何 corrected_text 警告行（仅汇总一行「跳过 4」） | 应用后把每条 warning 打到 stderr（或至少 warn 列表摘要） |
| **F3** | low | spec §2.3「不新增/删除换行；一行仍是一行」；实现未校验 value 内 `\n`（含换行会改变行语义/渲染） | 校验 `'\n' in val` → warn skip（或 exit2 明确禁止） |
| **F4** | low | spec §3.3 warnings 列出 `line_count_changed` 码，但 §2.4 又要求行数变化 exit2；实现直接 `ValueError`（exit2），不产生该 warning——契约内部不一致 | 统一：exit2 即可（删该 warning 码）或先写 warning 再 exit2 |
| **F5** | low | 校正文本长度/宽度未校验：如 p3 line1 增加一个引号字符；当前 p3 为整页 raster 无视觉影响，但非整页页可能因变长而溢出/换行 | 可选：对非 image-page 的校正行做宽度 sanity（>MEASURE 时 warn）；至少文档注明 |
| **F6** | note | ghbq 默认自动启用 `data/ghbq/corrected_text.json`（默认构建与 HEAD 仅 p3 不同）——符合设计（per-book data），但需在交付说明中标注默认已启用 | 文档注明 |

## 2. 结论

**t205 终审 verdict：needs_revision（FAIL）**。

- **通过**：替换时机/优先级/未知项 warn-skip/显式缺失 exit2/默认无文件 disabled；coords 不变、行数不变、104=104、GMPG 0、gate 96.8；p3 文本层校正且唯一差异页；空表/未知表等价；wz4 无校正 0 diff/gate 99.6；39 单测；功能上正确。
- **不通过**：F1（审计字段与 spec 不一致，medium）——`pages`/`replaced`/`line_counts`/`warnings`/`source` 五处不符；F2–F5 low。
- 修复建议：F1 优先（实现或 spec 二选一，并同步 docs §24）；F2 补 stderr；F3 加换行校验；F4 统一契约；F5 文档注明。

## 3. 复现

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_corrected.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force --layout
echo '{}' > /tmp/empty_ct.json
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_ctempty.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force --layout --corrected-text /tmp/empty_ct.json
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/review_wz4_ct.pdf --data-dir data/wz4 --skip-ocr --force
/usr/bin/python3 -m pytest src/test/unit/test_corrected_text.py src/test/unit/test_scan2pdf.py -q  # 39 passed
```

| 文件 | sha256 / 说明 |
|---|---|
| `src/tools/corrected_text.py` | `c312e737a84432d5a5a02a0ab5839c349ffd6d7e91021f5649a245f344ee4abb` |
| `src/tools/scan2pdf.py` | `0d602e609e7dda7e152b92cd4d6e70b7401e7df0aba062f1efe24fe11ecb4a85` |
| `data/ghbq/corrected_text.json` | sha `77da1526…`（p3 两条） |
| `output/ghbq_full/review_ghbq_corrected.pdf` | 104 页 / gate 96.8 / p3 已校正 |
| `output/wz4/review_wz4_ct.pdf` | 677 页 / gate 99.6 / corrected disabled |
| HEAD | `70fe1a7`（未 commit） |

---

# 附：corrected_text round-2 终审（t207，t206 修复 F1–F6）

> 审查人：质量审查员　日期：2026-11-10 23:12–23:40
> 对象：t206（修 t205 F1–F6）
> 依据：`spec/governance/CORRECTED_TEXT.md` §3.3/§4.1、`docs/scan2pdf_v1.md` §24、`AGENTS.md` #46
> **结论：PASS（有条件）** —— F1 审计字段已对齐 spec（replaced/pages 数组/line_counts before-after/warnings 对象/source=disabled）；F2 stderr 逐条、F3 换行校验、F4 契约统一、F5/F6 文档均实测；ghbq p3 校正、wz4 零回归、40 单测通过。残留仅「spec 最小示例 vs 实现超集字段」等 low。

## 0. F1–F6 核对

| 项 | 声明 | 实测 | 结论 |
|---|---|---|---|
| **F1** 审计字段 | replaced 主字段（applied 别名）、pages 页 key 数组 + pages_count、line_counts before/after、warnings 对象、无文件 source=disabled | ghbq report：`pages ["2"]`、`replaced 2`、`line_counts {"2":{"before":2,"after":2}}`、`warnings []`、source=book_data；wz4 无文件 `source=disabled`、pages [] | ✓ |
| **F2** stderr | 每条 warning 逐条打印 | 未知表：stderr **4 行** `[corrected_text] WARN unknown_page/unknown_line/invalid_line/invalid_page …`；newline 表 1 行 | ✓ |
| **F3** 换行 | `\n`/`\r` → newline_in_value warn skip | newline 表 skipped=1、warning `{code:newline_in_value,page:"2",line:0,message:"校正值不得含换行"}` | ✓ |
| **F4** 契约统一 | 行数变化 ValueError→exit2；spec 删除 line_count_changed | `grep line_count_changed spec` = 0；spec §4.1 注明；代码 ValueError | ✓ |
| **F5/F6** 文档 | 宽度 sanity 未强制、默认自动启用 | docs §24 已注明「宽度 sanity（未强制）」与「默认启用（无 --no-corrected-text）」 | ✓ |

## 1. 独立复跑

- **ghbq 默认校正**（任务命令）：104 页、GMPG 0、gate **PASS 96.8%**、nospace **43,913**；p3 文本层 = `戈尔巴乔夫与 / “人道的民主的社会主义”`，全文无「马尔巴乔夫」；coords sha 不变（`889ade99…`）。
- **未知表**（page999/line2:99/line2:abc/page:bad）：exit 0、skipped **4**、warnings **4 对象**（code/page/line/message 齐全）、stderr 4 行；文本与默认 0 diff。
- **换行表**（line0 含 `\n`）：exit 0、skipped 1、`newline_in_value`、stderr 1 行。
- **wz4 无校正**：677 页、gate **PASS 99.6%**、`source=disabled`、与 t190 nomark **文本 0 diff**、nospace 554,341。
- **单测**：`test_corrected_text` + `test_scan2pdf` → **40 passed**。
- 代码：应用时机（lines 加载后、--pages 前）/优先级（explicit>book_data）/行数不变/coords 不变/无书专属分支（仅 data/<book> 路径拼接）保持 ✓。

## 2. 残留（非阻塞）

| id | severity | problem | 处理 |
|---|---|---|---|
| R1 | low | spec 无文件示例为最小集（enabled/path/source/replaced/skipped），实现输出超集（pages/pages_count/applied/warn/line_counts/sha256）；`applied` 为 replaced 兼容别名 | 超集无害；文档已注明别名；如需严格可在 spec 标注「实现可含兼容别名」 |
| R2 | low | 校正文本长度/宽度未强制 sanity（非整页页显著变长可能溢出） | docs §24 已注明「需人工控制」；可选后续加 warn |
| R3 | low | 默认自动启用 `data/<book>/corrected_text.json`，无 `--no-corrected-text` 开关；移走文件才能关闭 | docs 已注明；建议后续加显式关闭开关 |
| R4 | note | p3 可见标题由整页源图 raster 提供，文本层为校正文本；两者已一致（视觉=源图，搜索=校正） | 设计预期 |

## 3. 结论

**t207 终审 verdict：PASS（有条件）**。

- **通过**：F1–F6 全部实测修复；审计字段与 spec §3.3 对齐（replaced/pages 数组/line_counts before-after/warnings 对象/source=disabled）；未知项/换行 warn-skip + stderr；行数变化 exit2 契约统一；ghbq p3 文本层校正、coords/行数不变、104=104、GMPG 0、gate 96.8；wz4 无校正 0 diff/gate 99.6；40 单测；文档/AGENTS #46 一致；无书专属分支。
- **条件**：R1–R3 为 low（超集字段/宽度 sanity/无显式关闭开关），文档已注明，不阻断收口。

## 4. 复现

```bash
cd /opt/test
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_corrected2.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force --layout
printf '{"2": {"0": "戈尔巴\\n乔夫"}}' > /tmp/newline_ct.json
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/review_ghbq_ctnl.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force --layout --corrected-text /tmp/newline_ct.json
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/review_wz4_ct2.pdf --data-dir data/wz4 --skip-ocr --force
/usr/bin/python3 -m pytest src/test/unit/test_corrected_text.py src/test/unit/test_scan2pdf.py -q  # 40 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/corrected_text.py` | `fcd674382b22a48fc29cbe7fd48b8cb267b88e6253deabbe36565898abe2a402` |
| `src/tools/scan2pdf.py` | `a8e09154376d949f802952d03d54e493bff15f2de4d00786078802bf0538f14f` |
| `output/ghbq_full/review_ghbq_corrected2.pdf` | md5 `f2c2ba5e0b4249159f6c026e593d9d10` / 104 页 |
| `output/wz4/review_wz4_ct2.pdf` | md5 `0998ecfe360f83a35c856861c4d5e68f` / 677 页 |
| HEAD | `70fe1a7`（未 commit） |

---

# 附：结构性守卫终审（t217，t215/t216 + t226）

> 审查人：质量审查员　日期：2026-11-11 13:56–14:30
> 对象：t215（E2E 冒烟 + spec 一致性 + 架构守卫）+ t226 修复（F2/F3/F4）
> 依据：`docs/scan2pdf_v1.md` §26（含 §26.5）、`AGENTS.md` #49/#50、t226/t227 证据
> **结论：PASS（有条件）** —— 三类守卫均实测可拦截（红/绿双侧 reviewer 独立复现）；E2E 三环（已有 data-dir→构建→gate）成立（ghbq 20-23 exit0/PASS100/pages4，两次一致；坏 data-dir exit1 带 reason+日志尾）；一致性/架构守卫覆盖 spec 字段与 fit_positional 入口。**任务给定 verify 样例 wz4 1-6 在干净 HEAD 与当前树均 exit6/pitch 50%**（前端页/目录页，非守卫缺陷），需换例/注明；t208 已知阻断（wz2 1-6、HORIZ_FALLBACK_RATIO 默认 0 vs spec 0.10）仍待 t221。

## 0. 复跑（任务给定 verify + 补充）

- **wz4 1-6（任务 verify 命令）**：当前树 `exit=6 gate=REJECT pitch=50.0 pages=6`，reason `verify_geom_fail,pitch_below_floor`；**干净 HEAD（worktree 70a9d70）同命令同结果 exit6/pitch50** → 该 6 页为前端/TOC 类，不可作 E2E 通验样例（非 t215/t226 回归）。
- **ghbq 20-23（脚本文档样例）**：`exit=0 gate=PASS pitch=100.0 pages=4`，run1/run2 一致（summary `(repeatable)`）。
- **坏 data-dir**：`exit=1`，summary `reason=scan2pdf_rc=3` + 日志尾「数据配对失败: data-dir 不存在」。
- **守卫测试**：`test_spec_conformance` + `test_architecture_guard` → **7 passed**。
- 全量：`test_spec_conformance` 5 例 + `test_architecture_guard` 2 例覆盖 §26.2/§26.3 条款。

## 1. 红/绿双侧（reviewer 独立复现）

| 篡改 | 结果 | 恢复 |
|---|---|---|
| spec `CORRECTED_TEXT` 全部 `replaced` → `REPLACED_TOK` | `test_corrected_text_report_fields` **FAILED**（`_has_token('replaced')` 断言失败） | 恢复后 5 passed；sha `OK` |
| `scan2pdf.build_pdf` geom 块内插入 `# guard tamper: build_geom.py` | `test_scan2pdf_geom_uses_fit_positional` **FAILED**（不得出现 build_geom.py） | 恢复后 2 passed；sha `OK` |

> 注：只替换**单处** `replaced`（其余处仍在）不会红 —— 守卫是「token 是否存在」语义，非逐字段结构断言（见 F2）。

## 2. findings

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F1** | medium | **任务给定 verify 样例不可用**：`wz4 --pages 1-6` 在干净 HEAD 与当前树均 exit6/pitch 50%（前端/目录页），不能作为 E2E 通验；docs §26.1 用的是 ghbq 20-23（PASS100） | 换 verify 样例（ghbq 20-23 或 wz4 非 TOC 页）或在 docs/§26.5 注明前端页子集不适用；当前任务 verify 命令本身应更新 |
| **F2** | low | 守卫是字面/存在性匹配：① 架构守卫在 build_pdf 体内**注释**出现 `build_geom.py` 也会 fail（docs §26.3 确实禁止该子串，属刻意严格，但会误伤说明性注释）；② 一致性测试只查 token 是否存在（单处篡改不红；实现用注释写字段名也可过），不校验字段结构/默认值语义 | 可选：架构守卫改匹配 subprocess argv 构造行/去注释；字段类守卫改用 AST 或断言 report 实际键集合 |
| **F3** | low | `e2e_smoke.sh` cleanup 删除 `<out 目录>/_scan2pdf_<book>`（共享临时目录）；同目录并发不同 out 的两次运行可能互删 | 临时目录按 out 文件名隔离（或 `--keep-tmp` 提示） |
| **F4** | known-blocker（captain 指定，t221） | `HORIZ_FALLBACK_RATIO` 代码默认 **0** vs spec **0.10**；当前树 wz2 1-6 exit6/REJECT、ghbq gate 95.9（HEAD PASS）——docs §26.5 已登记，t221 处理中 | 随 t221 回退/对齐；守卫不掩盖（脚本仍返回非零） |
| **F5** | note | 守卫刻意硬编码文件名（`fit_positional.py`）与 spec token 名：重命名重构会 fail，需同步改守卫+spec（§26.3 契约要求的架构不变量，接受） | 文档注明「重命名需同步守卫」 |

## 3. 结论

**t217 终审 verdict：PASS（有条件）**。

- **通过**：E2E 三环覆盖（已有 data-dir→scan2pdf→report/gate 判定）实测成立；确定性与重复性（PYTHONHASHSEED=0 + 2 次一致）成立；失败摘要含 reason+日志尾；spec 一致性覆盖 CORRECTED_TEXT 字段/CALIB 16 码/PAGE_IMAGE_LAYOUT 5 env 默认/scan2pdf 8 顶层键；架构守卫覆盖 build_pdf 只走 fit_positional + 薄壳复用 fit_common.main；红/绿双侧 reviewer 独立复现；docs §26、AGENTS #49/#50 一致。
- **条件**：F1（verify 样例）需换例/注明；F2/F3 low 可选加固；F4 为 captain 指定已知阻断（t221），本任务不打回。

## 4. 复现

```bash
cd /opt/test
bash scripts/e2e_smoke.sh --book wz4 --input source_pdf/wz4.pdf --data-dir data/wz4 --out /tmp/review_e2e_wz4.pdf --pages 1-6   # 当前树/HEAD 均 exit6 pitch50（F1）
bash scripts/e2e_smoke.sh --book ghbq --input source_pdf/ghbq.pdf --data-dir output/ghbq_full/_ocr_ghbq --out /tmp/review_e2e_ghbq.pdf --pages 20-23  # exit0 PASS100 pages4
bash scripts/e2e_smoke.sh --book wz4 --input source_pdf/wz4.pdf --data-dir /tmp/no_such_dir --out /tmp/e2e_bad.pdf --pages 1-6  # exit1 reason=scan2pdf_rc=3
/usr/bin/python3 -m pytest src/test/unit/test_spec_conformance.py src/test/unit/test_architecture_guard.py -q  # 7 passed
# 红/绿：spec replaced→REPLACED_TOK / scan2pdf geom 块插 build_geom.py → FAILED；恢复后 sha OK
```

| 文件 | sha256 / 说明 |
|---|---|
| `scripts/e2e_smoke.sh` | `0687a4774815f8a8cb90fdba608c254b7725bdb254950df61568b5bad4bda904` |
| `src/test/unit/test_spec_conformance.py` | `0315d1eefad86f08d8e6d0b50168fa2f703a234d4dd4aa017049f9d189b351e8` |
| `src/test/unit/test_architecture_guard.py` | `f3ec07fe837592a8085b6e476a521107cc0581a4adc20cbb515abbe70a3cc664` |
| `src/tools/scan2pdf.py`（当前树） | `d8fda57b083a0af81a13d0afd03c9fe272037b8a796115a0aeb4718569449545` |
| HEAD | `70a9d70`（未 commit；测试篡改均已恢复） |

# 附：排版评测契约 + verify_typography 终审（t241）

> 审查人：质量审查员　日期：2026-11-11 20:53–21:40
> **结论：needs_revision（FAIL）**。完整报告见 [docs/typography_eval_review.md](typography_eval_review.md)。

【must-fix】
- **F1 high**：`render_introduced` 路径几乎不存在（前缀 8 字→source_inherent，否则 unknown；除 CIP 特判外无 render 产出）。实测 wz4 6 条 `。` 行首（spec §8 标 render）当前 **unknown/warn**，不升级 fail → 放水。
- **F2 high**：`non_body_page` 实现为**单关键词**（md5/filesize/total_pages…）即整页豁免（spec §4.3 要求 ≥3 特征）。探针：正文页含 `md5` → body_lines=0、PASS（正文被吞）。
- **F3 high**：L1 仅实现 TOC 序号 overlap + 完全越出页幅 + 页数；**M3 页码错位、M4 字符丢失/重复缺失**，M1 普通 span 重叠不判、M2 部分越界不判。
- **F4 medium**：p5 CIP 单破折号特判与 spec §4.1 相反（源行首本就是 `—` → 应 source_inherent；实现强制 render，注释写明「t239 红侧 p5」）→ 误伤 + 红侧证据失效；单测固化。
- **F5 medium**：spec §2.1 规则 ID/名称与实现大面积不一致（5.1.2/3/4/5/7/9/10）。
- **F6 medium**：spec header/§10 仍 planned、工具路径写 `src/tools/typography_eval.py`（实际 `src/test/verify_typography.py`）；README=implemented；§8 基线未冻结（wz4 6 render vs 当前 unknown）。
- F7 low：§3.1 与 §7 对 L1 exit 自相矛盾；F8 low：GB52 attribution=`vertical_stat` 超出 spec 四类；compliance 1.0 与 277 warn 并存易误读。
- note：PUNCTUATION/PUNCT_EVAL 未被误改 ✓；t242 改 build_geom（CIP 单 `—`）需与「评测不改渲染」边界分离。

【复算】p12 gap −8.14 ✓；p97 越界 607.6>600.75 ✓；p5 源行 `—北京:…` 证实应为 source_inherent ✓。

【结论】工具当前会**漏报真违规**（F1/F2/F3）并**误伤源书特性**（F4），spec 与实现未对齐（F5/F6）；修复后复验。

（t241 补充）**F11 medium**：`test_verify_typography.py` 当前 **1 failed/17 passed**——`test_real_red_ghbq_title_toc` 依赖可变的 `output/ghbq_full/ghbq_title_toc.pdf`（已重建，旧 gap −8.32/−11.65 不再存在），测试非 hermetic；需冻结 fixtures。

（t251 round-2）**verdict = needs_revision**：t250 已修 nonbody≥3/p5 source_inherent/hermetic/spec 命名；但 **M1 与 spec 方向相反且误伤 wz2(19)/wz1(4) 正常相邻 span**（手工复算 64.2%/64.9% min 重叠）、**M3/M4 仍缺**、§12 wz4_s4 hash 不符（实际 `80d537e2…`）、「wz4 exit0」仅不带 lines 成立（带 lines FAIL/exit1）。详见 [docs/typography_eval_review.md](typography_eval_review.md) §6。

（t256 round-3）**verdict = needs_revision**：M1 诊断化/M3M4 文档化/edge p5/nonbody≥3/§12 基线已修；但 **M2 仍只判整段完全越界**（右缘越出 170pt 探针 PASS；p97 同页部分越界 span 漏判，整段越界 43 条才 hard），新增 **ISBN/CIP non_body 启发式未入 spec 且吞 p2 内容页**，edge `pos` 未接线（行末规则误归因）；unit 774 passed、invariants 首跑 2 failed 复跑 13 passed（非确定）。详见 [docs/typography_eval_review.md](typography_eval_review.md) §7。
