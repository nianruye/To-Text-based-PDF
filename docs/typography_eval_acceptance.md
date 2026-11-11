# 排版评测契约 + verify_typography 独立验收（t240）

> 验收人：验证评审员（独立复跑/复算；不采信实现者数字）
> 对象：t238 spec `TYPOGRAPHY_EVAL.md` + t239 `verify_typography.py` / gate 接线
> 日期：2026-11-11 20:05–20:40；分支 `feat/s4-line-metric`（HEAD `fc86ce8`，t238/t239 未提交）
> 结论：**FAIL（F1 spec §5.1 11 条 + §5.2 6 条未逐条落地；F2 现有产物 p97 hard 越界）**；红/绿双侧、门禁零回归、pytest 均通过。
> 未改实现/数据、未 commit。独立报告本文件 + `docs/scan2pdf_acceptance.md` 小节。

## 1. 契约命令（红侧）

```bash
/usr/bin/python3 src/test/verify_typography.py output/ghbq_full/ghbq_title_toc.pdf \
  --src-pdf source_pdf/ghbq.pdf --lines output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json \
  --json /tmp/acc_typog.json
# exit=1（预期红侧）
```

JSON 摘要：`verdict=FAIL`、`exit=1`、`pages=104`、`body_lines=2086`、`compliance_rate=0.980825`、`counts={violations:45, hard:39, render_introduced:1, waived:1, non_body_pages:1}`、`by_rule={gb51_dot_line_start:1, hard_span_overlap:5, toc_font_inconsistent:2, toc_cont_indent:2, toc_pagenum_align:1, hard_text_out_of_page:34}`。

### 1.1 红侧 5 项（全部抓到）

| 项 | 证据 |
|---|---|
| span 重叠 gap<0 | p11 `hard_span_overlap` gap **−8.32 / −11.65 / −8.32**；p12 gap **−8.14 ×2** |
| 同级字号不一致 | p11/p12 `toc_font_inconsistent`（p11 `[16.4,22.9]`） |
| 续行未对齐 | p11/p12 `toc_cont_indent`（p11 x0 `[94.6,145.8,149.6,154.1,162.6,174.3]`） |
| 页码列不齐 | p11 `toc_pagenum_align`（x1 `[134.1,149.6]`） |
| p5 `—北京` | p5 `gb51_dot_line_start`，char=`—`，**attribution=render_introduced**，severity=fail |

### 1.2 绿侧（不得误伤，均通过）

- p10 `——毛泽东关于党不变质思想探寻`：`waived=[{rule_id:5.1.1,page:10,char:"—",attribution:source_inherent}]`，未计入 fail。
- p104 元数据页：`non_body_pages=[104]`，整页 L2/L3 豁免（L1 页数/字符量仍判）。
- wz2（古籍）：当前构建 typography `PASS`、`violations=0`、`hard=0`、`render=0`；③ 层不 fail。
- 决策 A：L1 hard fail；L2 仅 warn；L3 仅 `render_introduced` fail（p5）；`source_inherent` waived；实现的分支逻辑与验收一致。

## 2. 门禁回归

| 书 | 接入后 gate | 接入前 | typography sidecar |
|---|---|---|---:|
| ghbq | 104=104、PASS、pitch 97.9%、overflow 0 | 同 | FAIL（红侧产品；L1+L3） |
| wz4 | 677/554341、PASS 99.5 | 同 | FAIL（render 6；L3） |
| wz1 | 222/137390、PASS 98.3 | 同 | WARN |
| wz2 | 6/1469、REJECT 66.7 | 同 | PASS |

- **gate verdict 均未因 typography 改变**（scan2pdf 只附加 `report.typography`/sidecar，quality_gate 组件不参与既有 geom 结论）。
- ghbq report：`gate.verdict=PASS`、`typography.verdict=FAIL`；满足「不改变既有结论」，但 typography 自身对红侧产品 fail 属预期。

## 3. spec 与实现一致性（FAIL）

- spec `TYPOGRAPHY_EVAL.md` §2.1 列 **5.1.1–5.1.11（11 条）**、§2.2 列 **5.2.1–5.2.6（6 条）**，要求逐条机检/违规命名。
- 实现 `src/test/verify_typography.py` 实际规则名只有：
  - L1：`hard_span_overlap`、`hard_text_out_of_page`、`hard_page_1to1`
  - L2：`toc_font_inconsistent`、`toc_cont_indent`、`toc_pagenum_align`
  - L3：`gb51_dot_line_start`（5.1.1）、`gb51_open_line_end`（5.1.7）
- **缺失 §5.1 的 5.1.2/5.1.3/5.1.4/5.1.5/5.1.6/5.1.8/5.1.9/5.1.10/5.1.11（9 条）**；**§5.2 的 5.2.1–5.2.6（6 条）完全没有实现**（vertical/ancient 分支直接 `pass`，只降统计）。
- 因此「§5.1 十一条 + §5.2 六条逐条落地」不成立；L3/gating 的契约覆盖度不足（F1 blocker）。
- 另：`spec/README.md` 仍标 **planned**（t239 已实现），状态未同步（F3 low）。

## 4. 意外 hard 越界（F2）

- p97 有 **34 个非短 span 完全越出页幅**（x1 最大 **4160.6pt**，页宽 600.75pt），如 `邓小平同志在` x0=607.6、`“坚持四项基本原则”` x0=731.6；全部判 `L1.2 hard_text_out_of_page`。
- 这不是误报：span 实际落在纸外；同一段在 t232 前产物 `acc_ghbq_s4final.pdf` 也存在（x1=4160.6），属既有产品缺陷，t239 工具正确抓到。
- 现有 `verify_geom` 只按纵向 overflow 判 0，未覆盖横向越界；typography 接入后 gate 仍 PASS（因未参与判定）。建议单独修 p97 横向版式，或明确 L1 是否应升级 gate。

## 5. 单测

- `test_verify_typography.py`：**8 passed**（含 hard overlap、TOC metrics、attribution、real red、wz4/wz2 gating、quality_gate 组件）。
- 全量 unit：**759 passed**（192.5s）。
- 缺陷：单测覆盖了已实现的判据，但**未覆盖缺失的 §5.1 其余 9 条与 §5.2 6 条**；无法证明契约全量落地。

## 6. 结论

**t240 FAIL（F1）**：红侧 5 项、绿侧 p10/p104/wz2、门禁零回归、pytest 759 全绿均通过；但 spec 的 §5.1 11 条仅实现 2 条、§5.2 6 条完全未实现，不满足「逐条落地」。需补齐 15 条规则（含竖排 5.2）与对应单测后再验；另 p97 横向越界为既有产品缺陷，需单独处理。

---

## 7. t242 修复与 RED 基线（2026-11-11）

### 7.1 规则落地口径（与 captain 裁定一致）

- **§5.1 实现 9 条**：5.1.1/5.1.2/5.1.3/5.1.4/5.1.5/5.1.6/5.1.7/5.1.9/5.1.10；
  **2 条豁免**：5.1.8 `not_machine_checkable_from_text_layer`（着重号/专名号属墨迹层，PDF 文本层无信息，v2 源图墨迹再做）、
  5.1.11 `permissive_clause`（许可压缩，不产生违规）。
- **§5.2 实现 6 条**：5.2.1 句读下方偏右 / 5.2.2 引号括号形式与方向 / 5.2.3 破折号等下方居中 /
  5.2.4 占格 / 5.2.5 列首列末禁则 / 5.2.6 数字西文方向；vertical/ancient 只出 `warn` 统计（决策 A gating）。
- 合计 **15 条机检 + 2 条豁免**；规则名见 `verify_typography.py` 的 `GB51_RULES` / `GB52_RULES` / `EXEMPT_GB51`，
  单测 `test_rule_inventory_15_plus_2_exempt` / `test_gb52_six_rules_emitted` 锁定。

### 7.2 RED 基线（ghbq_title_toc.pdf，t242 命令）

`verify_typography` 仍 **exit=1**；必须保留以下 5 项（t239 红侧清单）：

| 项 | 实测（JSON） |
|---|---|
| ① span 重叠 | p11 `hard_span_overlap` gap **-8.32/-11.65**；p12 **-8.14** |
| ② 同级字号不一致 | p11 `toc_font_inconsistent` [16.4,22.9] |
| ③ 续行未对齐 | p11 `toc_cont_indent` 94.6/149.6 |
| ④ 页码列右缘 | p11 `toc_pagenum_align` 134.1/149.6 |
| ⑤ p5 `—北京` | p5 `gb51_dot_line_start` + `gb51_dash_break`，attribution=render_introduced |

绿侧不变：p10 `——毛泽东…` → `source_inherent` waived；p104 → `non_body_page`；wz2 ancient → L3 不 fail。

### 7.3 p12 目录续页（补 1）

- 根因：`_toc_pre_flow` 原先只在 flow 含 `CONTENTS` 时启用（p11），p12 续页仍走旧点线/字号混排。
- 修复：目录页判定改为 `_TOC_PAGE`（含新扩展的续页 p12）；`_toc_pre_flow` 的候选门从 `_cand<3` 放宽到
  `_cand<3 且 _raww<3` 才放弃，使 p12「独立页码行 + 标题行」也走三栏/条目版式；另对目录页向前扩展
  条目形态页（p11/p12）。
- 结果：p12 的 **hard_span_overlap 已消失**，不再出现点线；序号-标题 gap ≥1pt（页面页码片段与标题分离）；
  仍保留 L2 字号/续行统计（provisional，不 fail）。

### 7.4 p5 行首破折号（补 2）

- 已在 `build_geom` 对 CIP 页（`_CIP_PAGE`）行首**单个** `—` 做定点去除（双 `—` 保留，源书显式标点不动）；
  重建产物 p5 不再有 `—北京` 行首违规；仅允许 p5 文本变化（逐页 diff 白名单之一）。

### 7.5 p97 横向越界（F2）

- 根因：OCR `ghbq_spotting_lines.json` key="96" 只有 3 行，其中一行 poly 高 **1119px**、427 字，OCR 把整页正文并成一条“行”；
  既有缺陷（t232 前产物同样 x1=4160.6），不是本轮引入。
- 本轮决定：**L1 暂不升级 gate**（captain 裁定：等 p97/p12/p5 修完再定）；`verify_typography` 继续作为独立报告，
  scan2pdf/quality_gate 不因 typography FAIL 改变既有 gate verdict。
- 守卫设计（待实现，非本轮）：单 OCR 行 poly 高 >3× 页字体高或字数 >阈值且 poly 高 >> 单行 → 判「故意并行」；
  ① 按 poly 内 y 分布重聚类切回多行（保文本）；② 切不准 → 整页贴图（复用 PAGE_IMAGE）；开关可回退。
- 已知残留：p97 `hard_text_out_of_page` 仍会出现在 typography 报告中（真实横向越界），不在本轮通过打 p97 特判掩盖。

### 7.6 README 状态

- `spec/README.md` TYPOGRAPHY_EVAL 行由 **planned → implemented**（15 条机检 + 2 条豁免）。

### 7.7 零回归白名单

- ghbq：除 **p5（CIP 单个 — 去除）/ p12（目录续页版式）** 外逐页文本 0 diff；p97 为既有缺陷，不在本轮改文字。
- wz4/wz1/wz2：逐页 diff 应为 []（仅新增 typography 报告字段，不改几何/文本）。


---

## 9. t243 round-2 复验（t242）

> 日期：2026-11-11 20:05–20:40；分支 `feat/s4-line-metric`（HEAD `fc86ce8`，t242 未提交）
> 结论：**FAIL（F1 spec 未同步 2 条豁免；F2 全量 pytest 2 failed）**；红侧 5 项、绿侧 p10/p104/wz2、门禁不变均通过。

### 9.1 规则覆盖（15+2）

- 实现：`GB51_RULES` 9 条 + `GB52_RULES` 6 条 + `EXEMPT_GB51` 2 条（5.1.8/5.1.11）；单测 `test_rule_inventory_15_plus_2_exempt` 断言。
- **但 spec 仍把 5.1.8 写成 `gb51_punct_gap`、5.1.11 写成 `gb51_other_edges`（机检项），未写入豁免** → spec/实现不一致（F1）。docs §7.5 有豁免说明，spec §2.1 表格未同步。

### 9.2 红侧（旧 `ghbq_title_toc.pdf`）

- 契约命令：`typog_t232.json`，**exit=1**；`counts={violations:126, hard:39, render_introduced:83, waived:403, non_body:1}`。
- 5 项全抓到：p11/p12 `hard_span_overlap` gap **−8.32/−11.65/−8.14×2**；`toc_font_inconsistent` p11 `[16.4,22.9]`；`toc_cont_indent`；`toc_pagenum_align` `[134.1,149.6]`；p5 `—` **render_introduced**（5.1.1 + 5.1.4）。
- 新规则还报 `gb51_separator_cell`65、`gb51_lineend_halfwidth`16 等（render 83）；旧产品本身含 TOC/标点缺陷，但数量偏高，建议 gold 标定（F3 低）。

### 9.3 新产物（t242 后独立重建 `/tmp/t243_new.pdf`）

- p5 `—北京` → `北京`，p5 无 render 违规；
- p12 `hard_span_overlap` 消失（by_rule 无 hard_span_overlap），保留 `toc_cont_indent` L2；
- 全书 `render_introduced=0`、`waived=327`、`hard=34`（p97 横向越界）；verdict 仍 FAIL（p97 L1，已知，t242 说明不升级 gate）。
- 说明 t242 的 p5/p12 修复有效；p97 为既有产品缺陷。

### 9.4 绿侧 / 门禁

- p10 `——毛泽东…`：`source_inherent` waived；p104 `non_body_pages=[104]`；
- wz2（6 页、无 src 页数比较）：typography **PASS**，0 violations；
- 契约 wz4：`exit=0`、verdict **WARN**（6169 条 unknown，无 render/hard）；gate 不变；
- ghbq 独立重建 gate **PASS** 104/pitch97.9/overflow0；wz4/wz1/wz2 gate 与之前相同（677/99.5、222/98.3、6/REJECT66.7）。

### 9.5 pytest（关键失败）

- `test_verify_typography.py` 单独运行 **14 passed**。
- **全量 unit：2 failed, 759 passed**（193.5s）：
  - `test_rule_inventory_15_plus_2_exempt` → `AttributeError: module 'vt' has no attribute 'GB52_RULES'`
  - `test_gb52_six_rules_emitted` → 同样 `vt` 模块缺 `GB52_RULES`
- 说明测试存在**模块隔离/缓存污染**（单跑通过、全跑失败）；验收要求「pytest 全量全绿」未满足（F2）。

### 9.6 结论

**t243 FAIL**：红侧 5 项、绿侧 p10/p104/wz2、门禁不变均通过；但 spec 未同步 5.1.8/5.1.11 豁免（F1），全量 pytest 2 failed（F2）；p97 L1 为已知产品缺陷。需修测试隔离 + spec 豁免条款后复验。

---

## 10. t247 round-3 复验（t246）

> 日期：2026-11-11 20:47–21:10；分支 `feat/s4-line-metric`（HEAD `fc86ce8`，t246 未提交）
> 结论：**PASS**。spec 豁免已同步、全量 784 passed/0 failed、红/绿/门禁全部复现；p97 L1 为已知产品缺陷（不升级 gate）。

### 10.1 spec 一致性（PASS）

- spec §2.1：5.1.8 → `not_machine_checkable_from_text_layer`、5.1.11 → `permissive_clause`（**豁免**），并新增 §2.4 豁免理由；机检 15 条（5.1 九条 + 5.2 六条）。
- 实现 `GB51_RULES` 9 + `GB52_RULES` 6 + `EXEMPT_GB51` 2，与 spec 逐条一致；单测 inventory 锁定。
- 决策 A：L1 hard fail；L2 仅 warn；L3 仅 `render_introduced` fail；source_inherent waived/unknown warn。

### 10.2 红侧（旧 `ghbq_title_toc.pdf`，契约命令）

```bash
/usr/bin/python3 src/test/verify_typography.py output/ghbq_full/ghbq_title_toc.pdf \
  --src-pdf source_pdf/ghbq.pdf --lines output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json \
  --json /tmp/typog_t232.json
# exit=1
```

`verdict=FAIL`、`compliance_rate=0.999521`、`counts={violations:45, hard:39, render_introduced:2, waived:7, non_body:1}`；`by_rule={hard_span_overlap:5, hard_text_out_of_page:34, gb51_dot_line_start:1, gb51_dash_break:1, toc_font_inconsistent:1, toc_cont_indent:2, toc_pagenum_align:1}`。

| 红侧判据 | 证据 |
|---|---|
| span 重叠 gap<0 | p11 −8.32/−11.65/−8.32；p12 −8.14×2 |
| 同级字号不一致 | p11 `toc_font_inconsistent [16.4,22.9]` |
| 续行未对齐 | p11 `toc_cont_indent` |
| 页码列不齐 | p11 `toc_pagenum_align [134.1,149.6]` |
| p5 `—北京` | p5 `gb51_dot_line_start` + `gb51_dash_break`，**render_introduced**，fail |

（t246 收紧规则后 render 83→2，误报显著下降；hard39 中 34 为 p97 既有横向越界。）

### 10.3 绿侧（PASS）

- p10 `——毛泽东…`：waived `source_inherent`；
- p104：`non_body_pages=[104]`；
- wz2（6 页，无 src 页数比较）：typography **PASS**、0 violations；
- wz4 契约：**exit=0**、verdict **WARN**（285 unknown，hard=0/render=0；t246 后由 6169 降至 285）。

### 10.4 门禁回归（PASS）

- 契约 verify_geom：**104=104、line_1to1 100%、pitch 97.9%、overflow 0、退出码 PASS**；
- ghbq 独立重建 gate PASS 104/pitch97.9/overflow0，typography sidecar 不影响 gate；
- wz4 677/554341/PASS99.5、wz1 222/137390/PASS98.3、wz2 6/1469/REJECT66.7，与接入前相同。

### 10.5 pytest（PASS）

- `test_verify_typography.py` 单独 **18 passed**；
- 全量 `src/test/unit + src/test/invariants`：**784 passed, 0 failed**（194.0s）——模块隔离问题已修（GB52_RULES 不再 AttributeError）。

### 10.6 结论

**t247 PASS**：spec 15 条机检 + 2 豁免与实现一致；红侧 5 项全抓到（p5 render_introduced）；绿侧 p10/p104/wz2 不误伤；门禁 104/PASS/pitch97.9/overflow0 与三书不变；全量 784 passed。残留：p97 34 hard 横向越界为既有产品缺陷（独立报告，不升级 gate）。
