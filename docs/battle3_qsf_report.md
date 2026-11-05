# battle3 · QSF 补引号收紧 + `！` 后漏识补形 + 分类器入库 —— 交付报告

> 任务：`t13 — battle3：QSF 补引号收紧 + ！后漏识补形 + 分类器入库`
> 执行：竖排工程师　日期：2026-11-04/05　工作目录：`/opt/test`
> 基线：工作树（HEAD `20d327e` + battle1/battle2 未提交改动）
> 依据：`docs/battle2_punct_audit.md`（v2.1：B=84 / C=234）、`docs/battle2_acceptance.md`、`docs/battle2_acceptance_r2.md`
> **修订 v2（t16，按 t14 复核 F1–F4）**：非正文过滤器收紧（竖排默认/横排 include、多关键词+页型特征、p82/p915 误伤披露）；
> p1365 改判 C_fixed（B=5）；五书口径改为可复现的默认 33 / include 38（删除旧的混合口径 34）
> 产物：`output/wz7_full/wz7_full_v31.pdf`（md5 `b062381b4649acbd1ea849a17fbf52d3`，1748 页）
> 不 commit / 不 push；产品代码只改 `src/pipelines/build_vert.py`；新增 `src/tools/punct_classify.py` 与单测

---

## 0. 结论（先行）

| 验收项 | 目标 | 实测 | 结论 |
|---|---|---|---|
| wz7 B 类（v31 复测） | ≤10（目标 0） | **5** | ✅（剩余 5 条逐条给根因，§6） |
| p620 `！」` 后补 `﹂` | 必须补回 | **已补回**：`…沒下稍！﹂` | ✅（§5） |
| `！/？` 后漏识抽样 | ≥10 处、修复率 ≥80% | **126 处，render_fixed 121（96.0%）** | ✅（§5.2） |
| wz7 verify_vert | PASS | 1748=1748 / 931,008 字 / 整页丢失 0 / 越界 0+0 | ✅ |
| wz6 零回归 | `vert.tex` md5 `ae9d2f52…` + verify PASS | **`ae9d2f52…` 逐字节相同** + PASS（231=231 / 97.2%） | ✅ |
| 分类器入库 | `src/tools/punct_classify.py`（含 CLI） | 已入库，纯仓库文件可复现 | ✅ |
| pytest | ≥562 | **590 passed**（562 + 28 新单测，含 F1/F2 回归） | ✅ |
| 不 commit / 产品代码范围 | 只 build_vert.py + 新审计工具 | 符合（见 §10 changedPaths） | ✅ |

**一句话**：QSF 补引号从「见尾墨就补」收紧为「**引号对未闭合 + 源墨在末字附近 + 句末标点（。！？；）后**」，
修掉双 `﹂﹂`、`：﹂`、词中 `﹂`；`！` 后补形覆盖 p620 型；wz7 B 从 **56 → 5**（默认口径；`--include-nonbody` 10），
全五书默认口径 **84 → 33**（横排 28 条属其他管线，见 §6.2；include 口径 38）；
wz7 字符量 930,754 → 931,008（+254，211 页逐页可解释），wz6 零回归，pytest 590。

> **v31 provenance（R3）**：t14 已用当前 `build_vert.py` 完整重建，产物与 v31 **逐页文本/行 bbox 0 差异**、audit 类计数相同（见 `docs/battle3_acceptance.md`）；本轮 t16/t17 未重复全量重建，v31 md5 `b062381b…` 作为交付基线。

---

## 1. 问题与根因（改前）

battle2 v2.1 的 B=84：wz7 56 / wz3 20 / wz4 6 / wz1 1 / mgfdmg 1。wz7 的 56 条主因三类：

| # | 现象 | 根因（实测） |
|---|---|---|
| 1 | 双 `﹂﹂`（p760/p1100/p1499/p623…） | QSF 只按「源图尾墨 corner」补字，**不看文本层该对引号是否已闭合**；合并列/短列的槽底落在列中段时，尾墨是列中某个 `」` 的墨 → 再补一个 |
| 2 | `：﹂`（p230/p343/p359/p630…） | §1.0d「行首闭括号回上一列」把下一列首的 `」` 机械归到**上一行**；上一行是 `但見：` 这类短列时产出 `：﹂`（且下一列首变成 `：`） |
| 3 | 词中 `﹂`（p922 `西﹂門`、p760 等） | QSF 补字落在**列中段**的源墨上（槽底/列中段错位），补字位置不校验「末字附近」 |
| 4 | C 类 p620 型（`！` 后漏 `﹂`） | QSF 触发条件只有末字 `。`/`一`，**`！？；` 后的列末格不取样** |

---

## 2. 修改（`src/pipelines/build_vert.py`）

### 2.1 QSF 收紧（三闸门）

1. **引号对闸门**（`_qsf_pairs_state`）：补字前检查本列文本的引号配对状态 ——
   - 本列含引号且已闭合 → 不补（修双 `﹂﹂`）；
   - 本列无引号字符（引号开在别的列，如 p620「你撇的人…！」）→ 放行，交位置/形状判据；
   - 有未闭合 `「` → 放行。
2. **位置闸门**（`_qsf_pos_ok`）：源墨 run 顶必须落在**本列末字 y ± 2.5 步进**内；列中段的墨 → 不补（修 `：﹂` 型错位、`西﹂門`）。阈值 `VERT_QSF_POS_TOL`。
3. **句末标点扩展**：触发末字从 `。`/`一` 扩到 **`！` `？` `；`**；`一` 的 1:1 替换另加
   ①引号对闭合则不换、②末尾两字都是汉字数字（章回行+页码，如 `…蔣竹山二六一`）不换 —— 分别修 p85 双 `﹂﹂` 与 p305 章回行尾 `﹂`。

### 2.2 行首闭括号归位修正（`fix_split_brackets`）

- 引号（`」』`）在两种情况下**不归位**（按源书保留列首 `」` = 审计 A 类）：
  ①上一行以句末标点结尾（`但見：` 型短列）；②归位后会把禁止行首的标点顶到列首（`」：`、`」、`、`」；`…）。
- 括号（`）〕】》〉`）保持 taskK-B 原行为（回上一列）——**wz6 的 10 处归位全部不变**，故 wz6 `vert.tex` 逐字节相同。
- 回退开关：`VERT_QUOTE_RELOC_ALWAYS=1` → 引号一律回上一列（battle2 口径）。

### 2.3 开关（默认 = 新行为；关掉即 battle2 口径）

| env | 默认 | 作用 |
|---|---|---|
| `VERT_QSF=0` | 1 | 关闭整个 QSF（= battle2 口径） |
| `VERT_QSF_APPEND=0` | 1 | 关闭补字，只保留 1:1 替换 |
| `VERT_QSF_PAIR=0` | 1 | 关闭引号对闸门（不推荐） |
| `VERT_QSF_POS_TOL` | 2.5 | 位置闸门容差（步进数） |
| `VERT_MERGE_QGUARD=0` | 1 | 关闭合并列护栏（`_merge_col_rows`） |
| `VERT_QUOTE_RELOC_ALWAYS=1` | 0 | 引号归位回到 battle2 口径 |

（wz6 有版框书 `_NF['on']=False`：QSF/合并护栏/引号归位新规则全部不触发 → 零回归由结构保证。）

### 2.4 分类器入库

`tmp_vert/battle2/punct_classify.py` → **`src/tools/punct_classify.py`**（保留 CLI/源位置闸门/源图复核），并修两处 C 类检测盲区：
- 合并列（OCR 两行合一列）取**末行行盒**找源图尾墨（先剥产品列末闭引号，最长后缀匹配）；
- QSF 的 1:1「。→ 引号」替换兼容（OCR 行末句末标点被替换后再比一次）。
这两处只修正「源图确实有墨」的漏判（每条 C_fixed 均有源墨证据），不放宽 B；A 口径未动。

---

## 3. 改前/改后数字（wz7，同一 audit/classify 口径）

| 类 | v30（battle2 v2.1） | **v31（battle3）** | 变化 |
|---|---|---|---|
| A 源书自身 | 3,119 | 3,528 | +409（引号归位回源书后，列首 `」` 计 A） |
| **B 产物引入** | **56** | **5** | **−51** |
| C OCR 漏识（产物仍缺） | 234 | 175 | −59（QSF 补形） |
| C_fixed（渲染已补） | 608 | 722 | +114（补形 + 检测修正；含 p1365） |
| K（valid carry） | 3 | 3 | 0 |
| K_weak | 954 | 962 | +8 |
| K_invalid | 31 | 30 | −1 |
| O 未配对 open 残差 | 404 | 360 | −44 |
| D_ambiguous | 1 | 1 | 0 |
| raw pair_split | 265 | 495 | +230（列首 `」` 回源书，A 类） |
| raw line_start | 2,597 | 2,582（include 2,585） | −15 |

> **五书口径（t16/F3 修正，两套数字都可复现）**：
> - **默认口径**（工具默认：竖排版權頁过滤开启 + 横排默认 include）：wz7 **5** + wz1 1 + wz3 20 + wz4 **6** + mgfdmg 1 = **33**；
> - **`--include-nonbody` 口径**（五书都纳入版權頁）：wz7 **10**（+p554 3 +p1163 2）+ 横排 28 = **38**。
> 报告旧版写的「34」是「横排 include 28 + wz7 默认 6」的混合口径（且当时过滤器误伤 wz4 265 页），**不可复现，已删除**。
> 横排 28 条的根因见 battle2 附录 A（wz1 p222 dash 断行、wz3/wz4 行首标点断行、mgfdmg 英文撇号），属 `build_geom/classic`，本任务 in-scope 外。

---

## 4. wz7 verify_vert / 字符量逐页解释

```
页数: 1748 = 1748 (1:1) | 字符量: 931,008 / OCR 942,935 = 98.7%
差异 > 80 字的页: 18（预期 18 / 非预期 0）| 整页丢失 0 | 越界 span 0 + 矢量 0 | 退出码 PASS
```

v30 → v31 字符量：930,754 → 931,008（**+254**），涉及 **211 页**（逐页差见 `tmp_vert/battle3/char_diff.json`）：
- 绝大多数页 **+1~+3**：QSF 在 `。！？；` 后补回源图有墨、OCR 漏识的闭引号（补字 699 处，扣除同页替换/回收后净 +254）；
- 极少数页负差：QSF 不再误补（双 `﹂﹂`/词中 `﹂` 被去掉）+ 归位回源书导致列文本重新分配；
- 18 个「>80 字差」页全部是既有的影印页/贴图页预期项（`--expect-low` 登记），未变。

---

## 5. p620 与 `！` 后漏识

### 5.1 p620 对照

| | v30（battle2） | **v31（battle3）** |
|---|---|---|
| 该列文本 | `你撇的人有上稍來沒下稍！` | **`你撇的人有上稍來沒下稍！﹂`** |
| 审计 | `ocr_miss_punct / product_missing` → C | `ocr_miss_punct / render_fixed` → C_fixed |
| 源图证据 | 最后一格闭引号墨条 **22.4×11.2pt**（y568.6） | 同（补字落在该墨位置） |
| 同页伴随 | `李﹂瓶` 词中多一个 `﹂`（B 类候选） | **已消失**（p620 col17 文本与 OCR 一致） |

### 5.2 `！/？` 后漏识抽样（≥10）

v31 audit 的 `ocr_miss_punct` 中 OCR 行尾为 `！/？` 的 **126 处**：**render_fixed 121（96.0%）**、product_missing 5。
样本（前 12，见 `tmp_vert/battle3/wz7_v31.audit.json`）：

| 页 | OCR 行尾 | 源墨 w×h | v31 |
|---|---|---|---|
| p73 | `…優點與成就呢！` | 21.7×10.4 | 已补 |
| p77 | `作什麼？` | 21.0×10.6 | 已补 |
| p78 | `…看他那裡尋去？` | 23.2×10.6 | 已补 |
| p86 | `…尚安所施！` | 21.0×10.6 | 已补 |
| p87 | `…黃河水逆流！` | 20.3×9.0 | 已补 |
| p92 | `…聲名播四方！` | 20.3×9.7 | 已补 |
| p94 | `…怎比泥土基？` | 21.0×9.7 | 已补 |
| p107 | `氣殺英雄小二哥！` | 21.0×11.3 | 已补 |
| p109 | `…賣弄殺偏俏的冤家！` | 21.7×10.6 | 已补 |
| p134 | `藥！` | 21.0×10.4 | 已补 |
| p136 | `…那曉防奸革弊心！` | 21.0×9.7 | 已补 |
| p180 | `…還我香羅帕！` | 21.0×9.7 | 已补 |

5 处 product_missing 的逐条原因：源墨低于 QSF 尺寸/形状判据（碎墨/抗锯齿）或该列不满足引号对/位置闸门 ——
在报告中逐条列出（附录 B），**修复率 96% ≥ 80%**。

---

## 6. 剩余 B=5 逐条根因（不可修/暂不修理由）

| # | 页 | 检查 | 文本 | 根因 | 处置 |
|---|---|---|---|---|---|
| 1 | p888 | pair_balance | `﹂﹁雁兒落帶得勝令﹂…` | 曲牌名行 OCR 为 `」「雁兒落帶得勝令`（连续两个闭引号），渲染/归位后行内引号与 OCR 行不完全对齐 | 曲牌/标题行边界，源书自身引号用法；不硬修 |
| 2 | p1247 | pair_balance | `…光油油﹂` | 下一 OCR 行首 `」（）…` 的闭引号被归位到本列尾（kinsoku），源墨在下一列首 → 审计记 B | 归位规则权衡项；`VERT_QUOTE_RELOC_ALWAYS=1` 可回退 |
| 3 | p1247 | pair_balance | `…俊英﹂！` | 同上（`」` 归位 + 后随 `！`） | 同上 |
| 4 | p1247 | pair_balance | `…花弄影﹂` | 同上（`」〔〕…` 行） | 同上 |
| 5 | p1382 | line_start | `：證一賢妻休悲…` | 列首 `：`（上一列引号归位/行拆分后的边界） | 归位规则权衡项；同上 |

> **p1365 已改判 C_fixed（t16/F2）**：源图末格有清晰 `﹂` 墨迹（`/tmp/acceptance5/p1365_endcell.png`），
> OCR 行尾 `…自防。一`（引号误读成「一」）；分类器旧后缀只剥句末标点、未剥误读「一」→ 取错行盒 → 误记 B。
> 修 `_pick_mark_row`（后缀同时试 `一0〇`）后，该条归 **C_fixed**，故 B=5。
>
> 目标「B≤10」达成（默认 5 / include 10）。剩余 5 条的共同点是**源书自身曲牌行/引号归位取舍**，
> 不影响正文语义；已全部列入人工复核清单。

## 6.2 横排 28 条（in-scope 外，保持 battle2 数字）

wz3 20（line_start/pair_split 断行）+ wz4 6（line_start `。`）+ wz1 1（dash_split）+ mgfdmg 1（英文撇号 `’`）= **28**：
均属 `build_geom/build_classic` 的断行/断列，本轮产品代码范围不含横排管线，未改；修法见 battle2 报告 §5.2/§7.2。
默认口径合计 **33**（28 + wz7 5）；`--include-nonbody` 合计 **38**（28 + wz7 10）。

---

## 7. wz6 零回归

```
VERT_TMP=/tmp/wz6_final2_run /usr/bin/python3 src/pipelines/build_vert.py \
    data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json \
    /tmp/wz6_final2.pdf source_pdf/wz6.pdf
md5sum /tmp/wz6_final2_run/vert.tex -> ae9d2f5259e12cff19e680b2a771b37d  ✓ 与基线逐字节相同
verify_vert -> 231=231 / 68412÷70373=97.2% / 差异>80 字页 2（预期 2 / 非预期 0）/ 整页丢失 0 /
               越界 span 0 + 矢量 0 / 退出码 PASS
```

原因：wz6 是有版框书（`_NF['on']=False`），QSF/合并护栏/引号归位新规则全部不触发；括号归位保持原行为。

---

## 8. 分类器入库与复现

- 工具：`src/tools/punct_classify.py`（`--audit/--pdf/--lines/--mode/--coords/--src-pdf/--out/--diff-out/--label`）。
- 只用仓库文件复现：
```bash
/usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v31.pdf --mode v \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --json tmp_vert/battle3/wz7_v31.audit.json --label wz7-v31
/usr/bin/python3 src/tools/punct_classify.py --audit tmp_vert/battle3/wz7_v31.audit.json \
  --pdf output/wz7_full/wz7_full_v31.pdf \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --mode v \
  --coords data/wz7_full/wz7_full_spotting_coords.json --src-pdf source_pdf/wz7.pdf \
  --out tmp_vert/battle3/wz7_v31.classified.json --label wz7-v31
```
- **版權/印刷信息页过滤器（t16/F1 收紧）**：仅**竖排默认**启用（横排 `--mode h` 默认 include，`_is_nonbody_page` 直接返回 False）；
  判据 = ≥3 个**不同**关键词（發行/出版/印刷/製版/裝訂/經銷/版權/局版/定價/帳戶/電話/地址）+ 页型特征（整页 ≤300 字且 ≤12 行）。
  `--include-nonbody` 关闭过滤器（两种模式都纳入）。本轮默认跳过 **p554 / p1163**（版權頁，共 5 条 B；include 口径下 wz7 B 10）。
  **旧版过滤器误伤披露（F4）**：旧判据「关键词 ≥3 次」曾把正文页 **p82**（註文「出版與研究半月刊/時報文化出版公司出版」）与
  **p915**（经文「印刷」×3）也跳过；新判据按整页字数（p82 183 字但只有 1 个关键词；p915 777 字）已把它们放回正文。
  这两页的 A/O 在旧默认口径被漏计（旧 A 3525 / O 356），修正后默认 = include = **A 3528 / O 360**。

## 8.1 CI WARN 评估

- **不可直接接入现有 CI**：CI 只装 ruff + pymupdf，仓库 `output/`、`data/` 均 gitignore，CI 没有产物 PDF/OCR 数据 → `punct_audit --mode h` 无输入。
- **本地复现命令**（WARN，不阻断）：
  `./src/tools/punct_audit.py <out.pdf> --mode h --json /tmp/punct.json`（横排只需 fitz）；
  竖排需 `--coords/--lines/--src-pdf`（见上）。
- 若要进 CI：需在 `src/test/fixtures/` 放一个小体积合成 PDF 作 smoke（不依赖 output/data），并保持 `--exit-zero` WARN 口径；本轮未做（超出 in-scope）。

---

## 9. 测试

- `pytest src/test/unit src/test/invariants -q` → **590 passed**（562 + 新增 `src/test/unit/test_punct_classify.py` **28 例**）。
- 新增单测覆盖（红→绿）：
  1. 引号对已闭合时 `。` 不补（双 `﹂﹂`）；
  2. `！` 后+本列无引号（p620 跨列）→ 允许补；
  3. `！` 后+本列已闭合 → 不补；
  4. 源墨在列中段 → 位置闸门拒绝（`：﹂`/`西﹂門`）；
  5. `一`→`﹂` 1:1 替换保留；
  6. 源位置闸门 boundary_ok（字符在 OCR 行中 → False）；
  7. OCR 误读「一」→ 引号 → C_fixed（misread_fix_ok）；
  8. **F1 回归**：版權頁（短小页+多关键词）→ 过滤器命中；横排默认 include；wz4 p138/p190、wz1 p30、wz7 p82/p915 型正文页 → 不命中；
  9. **F2 回归**：`_pick_mark_row` 对 OCR 尾误读 `一/0/〇` 的后缀匹配（p1365 实况，多行时选末行而非回退）。

---

## 10. 交付与约束

- 产品代码：**仅 `src/pipelines/build_vert.py`**（QSF 三闸门/归位规则/开关）；
- 新增：`src/tools/punct_classify.py`（分类器入库）、`src/test/unit/test_punct_classify.py`（28 例）、
  `docs/battle3_qsf_report.md`（本报告）；`src/tools/punct_audit.py`（页级非正文白名单 + `--include-nonbody`）；
- 产物：`output/wz7_full/wz7_full_v31.pdf`（gitignore）；证据：`tmp_vert/battle3/`；
- 未 commit / 未 push；横排管线（geom/classic/v13）、calibration、utils、output 源码零改动。

---

## 11. 剩余风险

1. QSF 补字是**形状启发式**（corner/ring/bar + 位置闸门）；p1365 型（OCR 尾误读「一」）已由 F2 修正，仍可能有极淡墨漏补，已列人工复核 5 条。
2. 引号归位规则影响 ~239 处列文本分布（wz7）；`VERT_QUOTE_RELOC_ALWAYS=1` 可回退。wz6 不受影响。
3. 横排 28 条 B 未修（in-scope 外），battle2 已给修法。
4. 版權頁过滤器靠「≥3 个不同关键词 + 整页 ≤300 字/≤12 行」；新增/不同排版的版权页若版式差异大，可能漏判（include 口径可兜底）。
5. 字符量 +254 是补字净增，逐页见 `char_diff.json`；未发现非预期整页差异（verify 18 页全预期）。

---

*报告结束。所有数字均为本机实测；命令、路径、证据文件可复现。*

---

## 附录 B：`！/？` 后仍 product_missing 的 5 条（修复率 121/126 = 96.0%）

| # | 页 | OCR 行尾 | 源墨 w×h (pt) | 未补原因（初判） |
|---|---|---|---|---|
| 1 | p489 | `功名全仗鄧通成！` | 20.3×9.7 | 该列不满足位置/引号对闸门，或尾墨形状被判 other |
| 2 | p833 | `…和你鳳拆鸞，鳳拆鸞！` | 21.7×10.6 | 同上（句末重复短语列） |
| 3 | p968 | `騾馬踏碎了破瓦？` | 21.0×11.3 | 同上 |
| 4 | p1022 | `…果然哥有孝服！` | 21.7×11.3 | 同上 |
| 5 | p1546 | `，,情願嫁上個姐夫！` | 16.6×8.3 | 墨高/尺寸低于 QSF 判据下限（碎墨/淡墨） |

> 这 5 条已登记为下一轮 QSF 取样复核清单（源图墨迹存在但补形未触发；不影响 B 类——它们属于 C 类漏补）。
