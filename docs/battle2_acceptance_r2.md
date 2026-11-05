# battle2 第二轮独立验收报告（F1–F8 修订后，v2）

> 验收人：验证评审员（独立验证方，t7）　时间：2026-11-04
> 基线：HEAD `20d327e` + battle1/battle2 未提交改动（工作树）；**未 commit / 未 push**
> 验收对象：t6 对 t4/t5 的修订 —— `spec/governance/PUNCTUATION.md` v2、`src/tools/punct_audit.py` v2、
> `docs/battle2_punct_audit.md` v2、`spec/README.md`（PUNCTUATION 行更新）、`tmp_vert/battle2/punct_classify.py`（v2 分类器）
> 原则：不轻信自述——F1/F2/F3 三项必修逐条回产物/源图核对，工具亲手重跑两遍，数字自己复算。

---

## 0. 验收结论（先行）

**可交用户；可作后续门禁依据（按报告 §9 的 WARN → 门禁路径，先 WARN 后门禁不变）。**
t5 的三项必修（F1 A/B 归因、F2 破折号误报、F3 K 未验证）与 F4–F8 收口**实质关闭**，
本轮复跑与 t6 证据**逐字节一致**、报告数字与 JSON 逐项一致；修订后的审计可作为门禁候选指标（B=84 基线）。

**附 3 项低级别收尾（不阻塞交付/门禁，建议交付前顺手修）：**

| # | 残留 | 证据 | 影响 |
|---|---|---|---|
| **R1** | F5 只修到「审计用配对表」（spec §2），**§1 形态表仍**把 `︗︘/︹︺/︽︾/︿﹀` 竖排形挂 §5.2.3 | `PUNCTUATION.md` L48-56 仍写 `§4.9.2 / §5.2.3`；§2 表已改「Unicode 竖排形（GB/T 未明示）」 | 文档级；不影响审计行为（审计用 §2） |
| **R2** | 报告 §9 门禁阈值单位错：写「≤ 0.1 处/**百页**；B=84 对应 0.10/百页」 | B=84 ÷ 3,904 页 = **2.15/百页**；0.10 是 84÷83,300 行 = **0.10/百行（列）** | 影响门禁阈值表述；数字本身对 |
| **R3** | 报告 §4.3/§5.1 未交代 v1 B 项 wz7 p967 line_start 在 v2 改判 A（净数已含） | OCR 行 `。「一擲一點紅…` 以「。」开头 → v2 A 正确、v1 B 是误判；v2 line_start B 由 2 变 16 = −1（p967）+15（新增） | 账目精度；不影响总数 |

**一句话实测**：A **4,157** / B **84** / C **234** / C_fixed **608** / K **3** / K_weak **1,441** / K_invalid **74** / O **1,636** /
D_legal **5** / D_ambiguous **5** / R **19,122**；五书 JSON 两次运行 md5 逐对相同且与 t6 证据**逐字节相同**；
15 条 t5 误分（含 wz3 p25 / wz4 p138 源图确证）**全部改判 B**；10 条行首破折号**全部移出违规**；
K 的 1,515 条 weak/none 由本人独立实现核对 **1,515/1,515 一致**，3 条 valid 逐条验到相邻页对偶符；
附录 C 的 74 条无对偶清单**逐页与本人独立统计完全一致**；pytest **562 passed**；产品代码零改动。

---

## 1. PASS/FAIL 总表（逐项 + 实测）

| # | 验收项 | 结论 | 实测（本报告重跑/复核） |
|---|---|---|---|
| 1 | F1：15 条误分 + 2 条源图确证案例改判正确，B 数字与修订理由一致 | **PASS** | 15 条横排 line_start（wz3 9 / wz4 6）全部 A→B，含 p25/p138；另 p570 + p850×3 pair_split A→B；B 36→84 的逐项分解与实测一致（wz3 +13 / wz4 +6 / wz7 +29；wz1/mgfdmg 不变）；A 4,208→4,157；A 未被洗白（横排 26 条、竖排 2,833 条 A 均命中 OCR 行首/末；3 条「相似行兜底」经 OCR 行核对均合理） |
| 2 | F2：行首破折号假阳 ≥7 处清零/改判，规则与 GB/T 原文一致 | **PASS** | 10 条全部移出 line_start → `dash_lead`（5 legal / 5 ambiguous）；wz1/wz3/wz4/wz7 均已无行首 `—` 的 line_start；mgfdmg p204 新增 `~`（§5.1.6）为 A；GB/T §5.1.6（连接号）/§4.10.3.9/§4.10.3.10（破折号示例）逐字核对一致；报告 §5.2/§7.1 已更正 |
| 3 | F3：K 有对偶验证，74 条无对偶拆分口径正确 | **PASS** | K(valid)=3（p520 列17 / p581 列0 / p901 列2，逐条验到相邻页首/末列对偶符）；K_weak=1,441、K_invalid=74；本人独立实现「相邻页是否有对偶符」核对 **1,515/1,515 一致**；附录 C 的 74 条**逐页与本人统计完全一致**（wz1 1 页 2 条、wz3 31 页 32 条、wz4 4、mgfdmg 5、wz7 26 页 31 条） |
| 4 | F4–F8 逐项确认关闭 | **PASS（F5 附 R1 残留）** | F4：spec §8.2 已删 `quote_continuation`（仅版本说明出现）、§10 明确未实现；F5：§2 配对表改标 + 17 类/19 条口径已统一（**§1 形态表残留见 R1**）；F6：`--label` 写入 meta、报告给出两套命令 md5（本人实测 no-label `86d9323e…` vs label `c2caec60…`）；F7：p620 伴随项改称 punct_diff 诊断、不在 B=84；F8：抽样统一 1-based + idx（如 `列 11（idx10）`） |
| 5 | 复跑 punct_audit 两次 JSON md5 相同，报告数字一致；规则条款号再审 ≥6 条 | **PASS** | 五书两次运行 md5 逐对相同：wz1 `c2caec60…`、wz3 `78ccb53e…`、wz4 `3855ec2a…`、mgfdmg `4c308eb9…`、wz7 `2b63b4a8…`；均等于 t6 证据文件；报告 §4.1/§4.2/§4.3 数字与 JSON 逐项一致（§3/§4）；GB/T 再审 10 条（§5.1.1/5.1.3/5.1.4/5.1.5/5.1.6/5.2.3/5.2.6/4.10.3.9/4.10.3.10/4.8.3.5） |
| 6 | 纪律：仅审计侧文件改动、产品代码零改动、pytest 562 passed、不 commit | **PASS** | `git status` 与 t5 结束态相同：只多 `spec/governance/PUNCTUATION.md`、`src/tools/punct_audit.py`、`docs/battle2_punct_audit.md`（untracked）+ `spec/README.md`（PUNCTUATION 行 v2 更新）+ `tmp_vert/battle2/`（gitignore 证据）；产品代码 mtime 未变（build_vert 10-24、verify_* 10-18、fit_common 00:37 battle1）；`pytest` **562 passed**；`git log` 仍 `20d327e` |
| 7 | 记录 SHA-256 清单并复述 battle1 字节绑定 | **PASS** | 23 文件逐文件 SHA-256 + 总哈希 **`d00a87cded43376a93d7ab1f877a942951dd34ec29049879d6d53a44bfe1e20a`**；battle1 20 文件中 **19 个字节未变**（与 t5 清单逐项相同），仅 `spec/README.md` 为 t6 审计侧更新（v2 账本行）；四书重建产物 vs t3 `/tmp/battle1/after` **textdiff 0 / boxdiff 0**（§9） |
| 8 | `docs/battle2_acceptance_r2.md` 含 PASS/FAIL 总表、原始输出、遗留风险、明确结论 | **PASS** | 本文件 |

---

## 2. F1 复核（A/B 源位置闸门）

### 2.1 工具/分类器

- `src/tools/punct_audit.py`：`line_start`/`pair_split` 的原始条目不再区分 A/B（工具只产原始检查项）；
- `tmp_vert/battle2/punct_classify.py`（v2）：A 判定改为 `boundary_ok(side, pn, ocr_n)` ——
  违规字符须等于**最相似 OCR 行**的行首/末字符，或等于同页某相似行（ratio≥0.45）的行首/末字符；
  否则 B。竖排同口径（OCR 行 = 列文本）；OCR 首字「一」误读、渲染端改回引号 → C_fixed。

### 2.2 t5 点名的 15 条误分 + 2 条源图确证案例：全部改判 B

| # | 书/页/行 | 字符 | 上下文 | v1 | v2（实测 cls） | 备注 |
|---|---|---|---|---|---|---|
| 1 | wz3 p25 行12 | `，` | `，恰与此同（见` | A | **B** | t5 源图确证：源书同一行连续 |
| 2 | wz3 p68 行37 | `，` | `，罗氏释之曰：` | A | **B** | 源 OCR 行长句 `…作“”，罗氏释之曰：`，逗号在行中 |
| 3 | wz3 p95 行3 | `；` | `；` | A | **B** | |
| 4 | wz3 p112 行22 | `。` | `。观此，知以田为征发之标准…` | A | **B** | |
| 5 | wz3 p157 行29 | `。` | `。` | A | **B** | |
| 6 | wz3 p348 行10 | `。` | `。` | A | **B** | |
| 7 | wz3 p794 行6 | `。` | `。` | A | **B** | |
| 8 | wz3 p817 行7 | `。` | `。` | A | **B** | |
| 9 | wz3 p843 行34 | `。` | `。` | A | **B** | |
| 10 | wz4 p138 行12 | `。` | `。3⃝这个思想的表述…` | A | **B** | t5 源图确证：源书 `。` 在行中 |
| 11 | wz4 p190 行18 | `。` | `。3⃝列宁进而认为：` | A | **B** | |
| 12 | wz4 p378 行20 | `。` | `。2⃝列宁认为…` | A | **B** | |
| 13 | wz4 p382 行3 | `。` | `。1⃝` | A | **B** | |
| 14 | wz4 p544 行12 | `。` | `。2⃝事实证明…` | A | **B** | |
| 15 | wz4 p668 行21 | `。` | `。3⃝私有财产的意志…` | A | **B** | |

另 4 条 pair_split 同因改判 B：wz3 p570 `》`、wz3 p850 `”`×3（元数据页噪声，报告 §7.2 已标注）→
故 wz3 B 7→20（+13）、wz4 B 0→6（+6），与修订理由一致。

### 2.3 A 未被洗白（源位置闸门反向核对）

- 横排 A 的 line_start/pair_split 共 **26 条**（wz1 3 / wz3 20 / wz4 2 / mgfdmg 1）：**26/26 严格命中**
  最相似 OCR 行的首/末字符（0 条依赖「相似行兜底」）。
- 竖排 wz7 A 的 line_start/pair_split 共 **2,836 条**：2,833 严格命中；**3 条**靠「同页相似行（ratio≥0.45）」
  兜底 —— 逐条查 OCR 行均合理（不是洗白）：
  - p117 idx0 `，`：OCR 行 1 = `，王婆定十件挨光計`（源列首确实是「，」）；
  - p967 idx10 `。`：OCR 行 17 = `。「一擲一點紅，紅梅花對白梅花。`（源列首确实是「。」；
    **v1 曾把这条判 B，v2 判 A 是纠正**——见 R3）；
  - p1678 idx4 `﹂`：OCR 行 5 = `」三尺利刀着頂上，`（源列首是「」」）。
- 反向抽验 B 样本：wz3 p25/p68/p138 三条均回源图/OCR 行确认是产物断行 → B 正确。

---

## 3. F2 复核（破折号 vs 连接号）

### 3.1 规则与 GB/T 原文一致

- §5.1.6 原文「**连接号**……不出现在一行之首」——只管连接号；
- §4.10.3.9 示例 `飞向太平洋 / ———我国新型号运载火箭发射目击记`、§4.10.3.10 示例 `…… / ———范仲淹`，
  **破折号本身就在行首**；
- spec v2 S4 只列连接号 `- ~ ～ ‐ –`，S4b 明确「破折号——行首合法」，`dash_lead` 分 legal/ambiguous。

### 3.2 t5 点名的 7 处（+同族 3 处）全部移出违规

| # | 书/页 | 文本 | v2 检查项 | v2 cls | 实测 |
|---|---|---|---|---|---|
| 1 | wz3 p542 | `——由租庸调至两税` | dash_lead | D_legal | 审计 JSON `sub=legal`，不再 line_start |
| 2 | wz3 p711 | `——海上对外贸易` | dash_lead | D_legal | 同上 |
| 3 | wz3 p773 | `——由两税至一条鞭` | dash_lead | D_legal | 同上 |
| 4 | wz3 p824 | `——止纳系官五户丝户：纳` | dash_lead | D_legal | 同上 |
| 5 | wz4 p4 | `——马克思主义政治学原理` | dash_lead | D_legal | 同上 |
| 6 | wz4 p4 | `—上海：上海人民出版社,2016` | dash_lead | D_ambiguous | `sub=ambiguous` |
| 7 | wz1 p54 | `—西方学者对马克思劳动价值论的质疑` | dash_lead | D_ambiguous | 同上 |
| 8 | wz7 p29 | `—Wereceivebutwhatwegive.—Coleridge` | dash_lead | D_ambiguous | 同上 |
| 9 | wz1 p208 | `—瑞士代表的支持。因此，` | dash_lead | D_ambiguous | 同上 |
| 10 | wz1 p222 | `—《马克思恩格斯全集》历史考证版` | dash_lead | D_ambiguous | 同上（与 dash_split B 同一缺陷第二半） |

- 四书 + wz7 的 `line_start` 中**已无** `—`（实测：wz1 2 条、wz3 29、wz4 8、mgfdmg 1、wz7 2597 均无 `—`）；
  `dash_lead` 合计 10 条（wz1 3 / wz3 4 / wz4 2 / wz7 1）。
- 新增检出 mgfdmg p204 `~`（浪纹线）→ line_start §5.1.6 A（源 OCR 行首 `~28%`，实测确认）。
- 报告 §5.2 已把上述 10 条列为 D 类；§7.1 A 抽样 12 条**不再包含**这 10 条（p542/p4/p54 只出现在 §5.2 D 表）。

---

## 4. F3 复核（K carry 对偶验证）

### 4.1 数字（本人从 audit JSON 直接统计，不经分类器）

```
K(valid) = 3    wz7 p520 列17 / p581 列0 / p901 列2
K_weak   = 1441 wz1 16 / wz3 307 / wz4 155 / mgfdmg 9 / wz7 954
K_invalid= 74   wz1 2 / wz3 32 / wz4 4 / mgfdmg 5 / wz7 31
合计 3+1441+74 = 1518（= v1 的 K 总数；pair_balance 另 3,104 条离边界 >3 行/列，归 O 或 A/B）
```

- 与报告 §4.2/§5.3 逐项一致；wz7 3+954+31 = 988 = 本人 t5 独立统计的 wz7 K 数。

### 4.2 3 条 valid carry 逐条验到相邻页对偶符

- p520 列17 unmatched_open `﹁` → p521 首列以 `﹂鄭愛香笑道…` 开头 ✔
- p581 列0 unmatched_close `﹂` → p580 末列以 `…賁四道：﹁` 结尾 ✔
- p901 列2 unmatched_close `﹂` → p900 末列以 `…因此說﹁` 结尾 ✔

### 4.3 1,515 条 weak/none 由本人独立实现核对（不是读 t6 结论）

用与 t5 相同的独立判据（相邻页全文是否含同类型对偶符）对 1,441+74 条逐条核对：**match 1,515 / mismatch 0**。
附录 C 的 74 条按书页清单与本人独立统计**逐页完全一致**（含 wz7 空相邻页 p510/p1577 也在其中）。

---

## 5. F4–F8 逐项

| # | 结论 | 实测 |
|---|---|---|
| **F4** | 关闭 | `grep quote_continuation spec/governance/PUNCTUATION.md` 仅命中版本说明；§8.2 表已无该项；§8.2 表格与报告 §10 均写明「多段引文未实现判定、未配对 open 归 O 残差」 |
| **F5** | 关闭（§2 审计表）；**§1 形态表残留 R1** | §2 配对表第 14-17 行已改「Unicode 竖排形（GB/T 未明示）」，并写明「17 类 + 2 条半角变体 = 工具 19 条」；但 §1 形态表 L48-56 仍写 `§4.9.2 / §5.2.3`（R1，低级别） |
| **F6** | 关闭 | `--label` 写入 meta（实测 no-label `86d9323e…` vs `--label wz1` `c2caec60…`）；报告 §3.3/§11 写清「两次运行必须同参数（含 label）」并给两套命令 |
| **F7** | 关闭 | 报告 §7.3 改称「B 类候选（punct_diff 诊断，未计入禁则类 B=84 / 附录 A）」；实测 p620 伴随项确为 punct_diff，不在 B=84/附录 A |
| **F8** | 关闭 | §7.1/§7.2 全部用 1-based + `（idx N）`；如 `列 11（idx10）`、`行 12（idx11）`；与 JSON idx 一致 |

---

## 6. 工具复跑与数字一致性

### 6.1 两次运行 md5（我亲手跑两遍，与 t6 证据逐字节对比）

| 书 | 我的运行 A | 我的运行 B | t6 证据文件 |
|---|---|---|---|
| wz1 | `c2caec60798a89b3e11538f10f93e8f1` | 同 | 同 |
| wz3 | `78ccb53e143579fe79569c2d04b9b4a7` | 同 | 同 |
| wz4 | `3855ec2a3c552595a217f46e4ee6f2a8` | 同 | 同 |
| mgfdmg | `4c308eb9e9d114fed535d184b87f01de` | 同 | 同 |
| wz7（`--label wz7-v30`） | `2b63b4a80f0015db18a5c3d33a1488ab` | 同 | 同 |

分类器输出 md5 也与 t6 证据逐字节相同：wz1 `96d2c8eb…`、wz3 `028fb231…`、wz4 `1191c054…`、
mgfdmg `3b31e695…`、wz7 `13fd3267…`。

**任务书 Verify 命令**（不带 `--coords/--lines`）两次均 `06dd0d6fe1ec5bd058533dabdf236652`，
输出 4,706 项（line_start 2,597 / pair_balance 1,841 / pair_split 265 / line_end 2 / dash_lead 1），
并打印 `[warn] --src-pdf 需要同时给 --coords 与 --lines…`（不误报 C）——与报告 §3.3 一致。

### 6.2 报告数字 vs 我的分类结果（逐格一致）

| 书 | A | B | C | C_fixed | K | K_weak | K_invalid | O | D_legal | D_ambiguous |
|---|---|---|---|---|---|---|---|---|---|---|
| wz1 | 58 | 1 | 0 | 0 | 0 | 16 | 2 | 21 | 0 | 3 |
| wz3 | 798 | 20 | 0 | 0 | 0 | 307 | 32 | 895 | 4 | 0 |
| wz4 | 144 | 6 | 0 | 0 | 0 | 155 | 4 | 278 | 1 | 1 |
| mgfdmg | 38 | 1 | 0 | 0 | 0 | 9 | 5 | 38 | 0 | 0 |
| wz7 | 3,119 | 56 | 234 | 608 | 3 | 954 | 31 | 404 | 0 | 1 |
| **合计** | **4,157** | **84** | **234** | **608** | **3** | **1,441** | **74** | **1,636** | **5** | **5** |

原始命中：line_start **2,637** / line_end **2** / pair_split **270** / dash_lead **10** / dash_split **1** /
ellipsis_split **1** / pair_balance **4,622** / ocr_miss **704** / trail_width **19,122**；punct_diff **31,351**
（= 1,041+23,115+4,438+620+2,137，全部与报告一致）。涉及页数 A 1,851 / B 67 / C 199 / C_fixed 388 /
K 3 / K_weak 1,185 / K_invalid 67 / O 1,078 —— 与报告 §4.2 一致。
附录 A B 全量 **84** 行（按书 1/20/6/1/56）；附录 D **10** 行（wz1 3 / wz3 4 / wz4 2 / wz7 1）。

### 6.3 规则条款再审（GB/T 原文）

独立提取 `docs/15834-2011-gbt-e-300.pdf` 逐字复核：§5.1.1（点号行首）、§5.1.3（前后半引号/括号）、
§5.1.4（破折号不拆）、§5.1.5（省略号不拆）、§5.1.6（**连接号**行首）、§5.2.3（竖排引号/圆括号）、
§5.2.6（竖排继承）、§4.10.3.9/§4.10.3.10（副标题/出处破折号，示例本身行首）、§4.8.3.5（多段引文）——
**10 条条款号与原文一致**，spec v2 的映射（含破折号/连接号分离）正确。

---

## 7. 审计对象与数字来源

- 四书重建产物 `tmp_vert/battle2/rebuild/{wz1,wz3,wz4,mgfdmg}.pdf` 与 t3 `/tmp/battle1/after` 逐页
  textdiff 0 / boxdiff 0（本报告实测）；wz7 v30 md5 `b8bb2dc49103ee3a72405da194a92d7d` 未变。
- 产品代码零改动：`build_vert.py`（mtime 10-24）、`verify_vert.py`/`verify_geom.py`（10-18）、
  battle1 的 `fit_common.py`（00:37）等 mtime 均未变；未 commit（HEAD 仍 `20d327e`）。
- 审计侧改动仅：`spec/governance/PUNCTUATION.md`（untracked，v2）、`src/tools/punct_audit.py`（untracked，v2）、
  `docs/battle2_punct_audit.md`（untracked，v2）、`spec/README.md`（PUNCTUATION 行 v2 文本更新）、
  `tmp_vert/battle2/punct_classify.py`（gitignore 证据目录；sha256 `8f0230a3…`）。

---

## 8. 纪律检查

| 项 | 结果 |
|---|---|
| 工作树 diff 仅审计侧文件 | **PASS**：与 t5 结束态相比，只多 3 个 untracked（spec/tool/report）+ spec/README 的 PUNCTUATION 行更新 + tmp_vert 证据；无其它路径变化 |
| 产品代码零改动 | **PASS**：`src/pipelines/build_vert.py` 等 mtime 未变；battle1 的 4 个实现文件 diff 与 t5 一致 |
| pytest | **PASS**：`562 passed, 836 warnings in 17.54s`，EXIT=0 |
| 不 commit / 不 push | **PASS**：`git log --oneline -1` = `20d327e`（未变） |
| 无调试残留 | **PASS**：v2 工具/分类器无 TODO/FIXME/pdb/breakpoint；`ruff check --select F821,E9 src/tools/punct_audit.py` = All checks passed |
| spec/README 账本 | **PASS**：governance 行 PUNCTUATION 已更新为 v2（含分类器/报告链接） |
| census 755 | **PASS**：`-rwxr-xr-x`，内容 sha256 未变（`e5ac6017…`） |

---

## 9. 内容绑定（SHA-256 清单 + battle1 字节）

### 9.1 当前工作树 SHA-256（23 文件，总哈希）

battle1 20 文件（与 t5 清单逐项对比：**19 个字节未变**）：

| 文件 | SHA-256 |
|---|---|
| AGENTS.md | `5ae1ab398e97313d6078a7c001877f96ee39a8a6e4285ca648cb1a37731b0ab2` |
| docs/vert_taskF_missed_fix.json | `66d31ce8643e9b233edab0d47d1732c55e82782d935e25665fd2ca08bedfaeb1` |
| docs/vert_taskH_ring2digit.md | `94ab98c06bf8b2f8db5fbf5aaa30de6f01a9ceb9729ed26f104d2f4b8a864e76` |
| **spec/README.md（t6 审计侧更新）** | `aed08e3e9daabb695cdc491531b2f4dc285cb57e05326c82d450a963582a864a` |
| src/calibration/fit_common.py | `5403cbd5610563dc6099c81b7955347c9c585e5f61eb61329f1dd4e196682a8c` |
| src/pipelines/build_classic.py | `7fadb5607d9f4f79c86133c8edf3fd969900974b0f780d024e7664a2bb2c946f` |
| src/pipelines/build_pdf_v13.py | `9f206e3d50374cc51c294a017c0d517eabe88e84a1f801d3fd606fe95c721b61` |
| src/test/test_cases.py | `54544be741e5d5b571745235f8403f9bee5777e83c9d3704b61fd717d74688ff` |
| src/test/unit/PURE_FUNC_SPEC.md | `a554423811a39af2247d77755ca0d1f6ba46b198476c405e09cc50f0871234b4` |
| src/test/unit/test_audit_features.py | `7d0f1f6d83426e0e02a71187a888dbf0a4321d9c6e40f74fc1d93a26a8b03e50` |
| src/test/unit/test_pure_funcs.py | `1b49e943c67624424af6675064c9c8ba13b6f8ce9c0b6f4022e66e4276b1a681` |
| src/tools/census_ring_digit.py | `e5ac601748d9fb228cb96ca5fd621efce016d46b4ce0e844418a309dc3ad845e` |
| src/utils/tex_escape.py | `e10b776c7ddfc6b501f3ba49f096fdda5549a3770a65ff1a4e37a88e06377a07` |
| docs/battle1_horizontal.md | `858c9fd2ff584945347b297ef15d4ca1a3194ddec6d09215874805a9e757b416` |
| docs/battle1_vertical_ring.md | `16ffd7c038a3a8bf762a6d9b30a8f6852ad0e7455d6b01b5a4438ce894ae17bc` |
| src/test/unit/test_census_ring_judge.py | `22797a1a8d2034095a1aee52f111efd1c10366110af162166a99b40580d70dd2` |
| src/test/unit/test_fit_common_cleanup.py | `9a3d3175ec32f898bbf0697182779b09e07d7e96f3b0dcfcab62d1b7ec0226f9` |
| src/tools/merge_ring_digit.py | `596aed8bcc87a329762f85c05b96230b106b9c27be999840ca5a8ae56dbef79b` |
| src/tools/ring_judge.py | `56f819e6f1602f916b7491b96dc43acd7a6e6c92e1f414c72a727a41a8be8e82` |
| docs/battle1_acceptance.md | `edbe6e8aac508650635325fb7fba2067d5a888424276f1f4a08e5717500b7b0f` |

t4/t6 审计侧文件（3 个，v2）：

| 文件 | SHA-256 |
|---|---|
| spec/governance/PUNCTUATION.md | `527105f681c8bf0ec24bdb7b0d67361a7035a5a20f3555704879efb490c044a7` |
| src/tools/punct_audit.py | `ea465dcd81645d3090e8b49a3abe63bf38d265c02017fe8f8a2032072d594e6c` |
| docs/battle2_punct_audit.md | `27b192ba7a733bdecd70ad55d0b144b0d22c8b850b1cd9067bb58c1ba9e83a65` |

**总哈希**（按 `sha256  path` 排序后拼接再 sha256）：
`d00a87cded43376a93d7ab1f877a942951dd34ec29049879d6d53a44bfe1e20a`（23 文件；清单 JSON `/tmp/acceptance3/sha256_manifest.json`）。

### 9.2 battle1 字节绑定复述

- **battle1 已验收的 20 个文件：19 个字节未变**（上表除 `spec/README.md` 外全部与 t5 清单相同）；
  `spec/README.md` 的差异 = t6 审计侧更新 PUNCTUATION 账本行为 v2（git diff 只有该行与既有行，无删除其它内容）；
- **功能绑定**：t6 未重跑四书，但四书重建产物（t4 生成，20:13–20:17）与 t3 验收产物（00:32–00:36）逐页
  **textdiff 0 / boxdiff 0**（wz1 222=222、wz3 850=850、wz4 677=677、mgfdmg 407=407）——battle1 行为未变；
- `census_ring_digit.py` 内容 sha256 `e5ac6017…` 未变（仅 755 权限，t4 已恢复）。

---

## 10. 遗留风险与低级别收尾项

1. **R1（低）**：spec §1 形态表 L48-56 仍把 `︗︘/︹︺/︽︾/︿﹀` 的竖排形挂 §5.2.3；§2（审计用）已改。
   建议把这 5 行的「条款」列改为「§4.9.2 / §4.15.2（横排）；竖排形 GB/T 未明示」。
2. **R2（低）**：报告 §9 门禁阈值「≤ 0.1 处/百页；B=84 对应 0.10/百页」单位错：84÷3,904 页 = **2.15/百页**，
   0.10 是 84÷83,300 行/列 = **0.10/百行（列）**。建议改为「≤0.1 处/百行（列）（v2 B=84 对应 0.10/百行）」
   或「≤2.2/百页」。
3. **R3（低）**：报告 §4.3/§5.1 未说明 v1 B 项 wz7 p967 line_start 在 v2 改判 A（OCR 行以「。」开头，v2 正确）。
   净数已含（line_start B 2→16 = −1+15），建议补一句。
4. **A/B 分类器不在仓库内**（`tmp_vert/battle2/punct_classify.py`，gitignore）：当前按任务 in-scope 约束
   「仅 src/tools/punct_audit.py 入库」可以接受（报告 §3.1 已声明），但这是**长期复现风险**：
   仓库单独 checkout 只能复现原始检查项（audit JSON），不能复现 A/B/C/K/K_weak/K_invalid。
   建议 battle3 把分类器正式纳入 `src/tools/`（或把分类逻辑并入 punct_audit 的 `--classify`）。
5. **门禁阈值本身**：B=84 是修订后的基线，报告建议「battle3 修完 QSF 插入 + 横排断行 + 元数据/撇号豁免后趋 0」；
   本轮不改变这一路径，只确认 B 现在是「不被低估」的指标。
6. **噪声页**：wz3 p850（元数据 JSON 引号，B 类 10 条）与 mgfdmg p325（英文撇号）仍在 B=84 内；
   报告 §7.2/§9 建议页级白名单——门禁正式启用前应落地，否则 B 永远无法趋 0。

---

## 11. 未验证 / 不可验证项

- 未逐处复核附录 A 的 84 条 B、附录 C 的 74 条（只按书页与本人独立统计对齐；其中附录 C 逐页完全一致）；
- 未逐处复核 C 类 234 处（只抽验 p620 与报告 §7.3 样本 12 处）；
- 未重跑四书 build（产物与 t3 产物 0 差异已作功能绑定；verify_geom 数字沿用 t4/t6 报告）；
- 未在另一本竖排书上验证该判据（只有 wz7；wz6 不参与标点审计）；
- 未验证分类器在「OCR 行合并/切分」极端页的比例（横排 26 条 A 全 strict；竖排 3 条兜底已逐条核）。

---

## 12. 复现命令（本报告用）

```bash
cd /opt/test
A=/tmp/acceptance3/audit
# 1) 五书各跑两遍（与 t6 命令/参数一致）
for b in wz1 wz3 wz4 mgfdmg; do
  for r in a b; do
    /usr/bin/python3 src/tools/punct_audit.py tmp_vert/battle2/rebuild/$b.pdf --mode h \
      --json $A/${b}_${r}.json --md $A/${b}_${r}.md --label $b
  done
done
for r in a b; do
  /usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v30.pdf --mode v \
    --coords data/wz7_full/wz7_full_spotting_coords.json \
    --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
    --src-pdf source_pdf/wz7.pdf --json $A/wz7_${r}.json --md $A/wz7_${r}.md --label wz7-v30
done
md5sum $A/*.json        # 对照 t6：c2caec60/78ccb53e/3855ec2a/4c308eb9/2b63b4a8
# 2) 任务书 Verify 命令（不带 coords/lines）
/usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v30.pdf --mode v \
  --src-pdf source_pdf/wz7.pdf --json /tmp/verify_a.json    # 06dd0d6f…，两次相同
# 3) A/B/C 归因（v2 分类器）
for b in wz1 wz3 wz4 mgfdmg; do
  /usr/bin/python3 tmp_vert/battle2/punct_classify.py --audit $A/${b}_a.json \
    --pdf tmp_vert/battle2/rebuild/$b.pdf --lines <该书 OCR lines> --mode h \
    --out /tmp/acceptance3/classified/$b.json --label $b
done
/usr/bin/python3 tmp_vert/battle2/punct_classify.py --audit $A/wz7_a.json \
  --pdf output/wz7_full/wz7_full_v30.pdf --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --mode v --coords data/wz7_full/wz7_full_spotting_coords.json --src-pdf source_pdf/wz7.pdf \
  --out /tmp/acceptance3/classified/wz7.json --label wz7
# 4) 本报告作者的独立核对脚本（未入库）
/usr/bin/python3 /tmp/acceptance3/...   # A 的 strict/loose 统计、K 1,515 条独立核对、附录 C 对齐（逻辑见正文）
# 5) 测试与纪律
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q    # 562 passed
git status --porcelain; git log --oneline -1; ls -l src/tools/census_ring_digit.py
```

日志/证据（`/tmp/acceptance3/`）：`logs/*.log`、`audit/*.json|md`、`classified/*.json`、`sha256_manifest.json`；
分类器证据 `tmp_vert/battle2/punct_classify.py`（sha256 `8f0230a3…`）。

---

## 13. 验收结论

- **t6（F1–F8 修订）：通过。** F1 A/B 源位置闸门真关闭（15 条 + 2 条源图确证全部改判 B；A 未被洗白）、
  F2 破折号误报真关闭（10 条移出违规，与 GB/T 原文一致）、F3 K 真关闭（3 valid / 1,441 weak / 74 invalid，
  与本人独立统计 1,515/1,515 一致）；F4/F6/F7/F8 关闭，F5 在审计用表关闭（§1 形态表残留 R1）。
- **可交用户**：作为 WARN 审计交付（工具可复现、数字与 JSON 一致、p620 C 类与 B 类缺陷清单可用）；
- **可作门禁依据**：B=84 已是「不被低估」的禁则类基线，按报告 §9 的 WARN → battle3 后 B→0 路径执行；
  启用前需先修 R1/R2（都在文档/阈值表述层，不动工具逻辑）。
- **建议**：让 t6 顺手收 R1（spec 一行）、R2（报告阈值单位）、R3（账目说明）；R4（分类器入库）与
  噪声页白名单放到 battle3 一并处理。

> 本报告只写实测；未 commit / 未 push / 未改实现代码。唯一写入仓库的文件是 `docs/battle2_acceptance_r2.md`。
