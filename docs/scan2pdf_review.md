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
