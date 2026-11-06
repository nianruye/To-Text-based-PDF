# 16 · missing_char 缺字/标点串 1:1 插入（battle6–9）

> 状态：**implemented**（battle6–9，2026-11-05/06）
> 实现：`src/pipelines/build_vert.py` §1.0a5 / `_apply_missed_fix` / `_relocate_missing`
> 数据：`docs/vert_taskF_missed_fix.json`（默认 `VERT_MISSED_FIX`；`=0` 关闭）
> 报告：`docs/battle6_missing_chars.md`（缺字普查）、`docs/battle7_missing_chars.md`（58 汉字）、
> `docs/battle8_quotes.md`（72 引号）、`docs/battle9_census.md`（16 条普查）、`docs/battle9_fix.md`（p57/p186/p147）、
> `docs/battle9d_census_fix.md`（6 条复核）、`docs/battle9e_acceptance.md` / `docs/battle9e_review.md`（v40 验收/终审）
> 关联 spec：[08 标点竖排形态](08_punct_vertical_forms.md)、[13 引號/TOC](13_vert_quotes_toc.md)、[15 破折号](15_vert_dash_rule.md)

## 16.1 目标与边界

**目标**：把 OCR **漏识、但源图确有墨迹**的字/标点串按 `pos` 1:1 插回文本层（不改变已有字的字位/字号/列位口径）。
`ch` 允许 **1–2 字符**（契约值）：汉字（battle7 + battle9 普查）、引号（battle8b）、标点串（battle9：
`——` / `」。` / `」，`）。不插圈码（走 ring）；`——` 的 dash 边界见 §16.4.1。

当前 fix JSON 的数据规模、按 source 的构成、各批次增量见 **§16.10 参考基线**；t24 遗留条目仍按同一
`missing_char` 分支插入，新条目必须按 §16.2/§16.5 带证据。

**非目标**：不做 OCR 全文重写；不做列框外「整字漏识」的自动插入（battle6 已证明列框外几乎不存在整字漏识）；
不做异体字归一化（由 `src/tools/variant_norm.py` 在候选阶段处理）。

## 16.2 数据契约（`docs/vert_taskF_missed_fix.json`）

文件顶层：`{"source": str, "note": str, "items": [...], "ring_digit_merge": {...}}`。
`items` 中 `class="missing_char"` 的条目，**公共字段**：

| 字段 | 类型 | 必填 | 含义 |
|---|---|---|---|
| `class` | str | 是 | 固定 `"missing_char"`（与 `ring` / `dash` 并列） |
| `page` | int | 是 | 1-based 源页号（与 `data/*_spotting_lines.json` 的 key=`page-1` 对应） |
| `col` | [x0,y0,x1,y1] | 是 | 该列 OCR 框（**PDF pt，页左上原点**）；`_apply_missed_fix` 把 OCR coords（144dpi px）`/2` 后与当前列框做**小容差**匹配（容差实现默认见 §16.10 参数默认） |
| `pos` | int | 是 | 插入点：在该列 OCR 文本中的 **0-based** 字符下标（插入到 `text[pos]` 之前） |
| `ch` | str | 是 | 要插入的字符/串，**长度 1–2（契约值）**（按原样插入，字符增量 = `len(ch)`）；双字符实例：`——`、`」。`、`」，`（数据条数见 §16.10） |
| `side` | str | 是（可为 `""`） | 源图侧别（左右页/列侧）；当前数据取值见 §16.10 |
| `source` | str | 是 | 证据/来源：`api_strip`（battle7 汉字）、`api_strip_quote`（battle8b 引号）、`api_strip_census`（battle9 普查汉字）、`api_strip_punct`（battle9 标点串） |
| `confidence` | str | 是 | 人工/流程置信级别；当前数据取值见 §16.10 |
| `ratio` | number | 是 | API 复核置信度（0–1），仅记录，不参与插入判据 |
| `exp_len` | int | 是 | 该列 OCR 文本长度（`len(text)`）；用于核对插入后长度 = `exp_len + len(ch)`（**不是固定按 1 计**） |
| `text` | str | 是 | 该列 **原始 OCR 文本**（重定位上下文；`_relocate_missing` 用左/右各 N 字，N 为实现默认、可参数化，见 §16.10） |
| `api` | str | 是 | 同一列的 API 复核文本（含目标字；引号/标点类还用于说明重判） |
| `crop` | str | 是 | 源图证据裁片路径（相对仓库根）：battle7 在 `tmp_vert/battle6/all_insert_crops/`、battle8b 在 `tmp_vert/battle8/quote_crops/`、battle9 在 `tmp_vert/battle9/{d_fix,fix}/` |
| `cell` | [x0,y0,x1,y1] | 是 | 该字/标点串在源图上的单元格（**PDF pt**），裁片/角形/线宽判据的输入 |
| `note` | str | 否 | 标点串（punct）源墨依据备注（punct 条有；其余可无） |
| `feat` | dict | 引号必填 | 角形特征：`{w,h,fill,left,right,top,bottom,corner,side,ends}`（`api_strip_quote`）；census 用 `shape`、punct 当前无（可后续补） |
| `verdict` | str | 引号必填 | `close-ok` / `reclass-close` / `open-ok`（`api_strip_quote`）；census/punct 无 |
| `strip` | str | battle7 汉字必填 | 行条带图（`tmp_vert/battle6/all25/strips/`）；battle9 census 无 strip（以 crop/cell/shape/complete 为证据）；t24 遗留条目无 |
| `shape` | dict | 汉字必填 | `{w,h,fill}`（完整字块判据）；battle7 与 battle9 census 有，quote/punct 无 |
| `complete` | bool | 汉字必填 | `true` = 完整字块（<0.55 步进/碎片不落库；0.55 为实现默认、可自标定，见 §16.10；**参考值，非判据**）；battle7 与 battle9 census 有，quote/punct 无；t24 遗留条目无 |

**字段族（按 source）**：

| source | 证据字段族 |
|---|---|
| `api_strip` | battle7：crop + cell + strip + shape + complete；t24 遗留无证据（条数见 §16.10） |
| `api_strip_quote` | crop + cell + feat（corner）+ verdict |
| `api_strip_census` | crop + cell + shape + complete（无 strip） |
| `api_strip_punct` | crop + cell + note（源墨依据；当前未填 feat/verdict/complete/shape，后续补按引号族扩展） |

**数据不变量**（落库脚本负责，渲染端只读）：
- 同一 `(page, pos)` 不得出现不同 `ch`；同一 `ch` 不得在同一 `(page, pos)` 重复；`ch` 长度必须 1–2；
- 去重键 `(page, col±2pt, pos, ch)`；已存在目标字（`target-at-pos`）或与既有条目重复（`dup-existing`）时**不落库**；
- 每条的 `crop` 必须存在；引号类 `feat.corner=true`；汉字类（battle7/census）`complete=true`；
- 插入增量 = `len(ch)`（1 或 2），不假定固定按 1 计。

## 16.3 插入机制

1. **开关/输入**：`VERT_MISSED_FIX` 未设 → 默认 `docs/vert_taskF_missed_fix.json`（存在才启用）；
   `=0/off/false` 关闭；文件缺失 → 关闭。见 `build_vert.py` L313–320 `MISSED_FIX`。
2. **分组与列匹配**（`_apply_missed_fix` L512 起）：按 `(page, tuple(col))` 分组；对每组的每个 missing_char，
   在当前页 `sl[k]` 的列框中找 `(min x/2, min y/2, max x/2, max y/2)` 与 `col` 各分量差 ≤ 小容差的列（实现默认见 §16.10）。
   未匹配 → 跳过并打 `[漏识元素] p… 未匹配` 日志。
3. **排序**：同一列内的 missing_char 按 `pos` 升序（`_miss`，L547），保证多次插入按文本顺序进行。
4. **重定位**（`_relocate_missing` L480）——插入点按**当前行文本**重算，三步：
   - ① **上下文子串匹配**：取 `text` 的 `[pos-8, pos)`（左 8）与 `[pos, pos+8)`（右 8）作为上下文；
     先试 `cur.find(左+右)`，再退化为左/右单侧；命中则插入点 = 命中位置 + 左段长度。
     （`text` 是原始 OCR 行；`cur` 是当前行。行首字符未被移走时命中 `pos`，**no-op**。）
   - ② **回退 `pos − shift`**：匹配不到时，用 `shift` = 该行被 `fix_split_brackets` 移走的行首字符数
     （`_br_shift` L983–988，由 `_br_fix` 按 `(页索引, 行索引)` 汇总）；`0 ≤ pos−shift ≤ len(cur)` 时采用。
   - ③ **越界 → 跳过并记日志**：`[漏识元素] p… missing_char 重定位失败(pos=… shift=…) -> 跳过`；
     **宁少插一字，不错位插**。
5. **写入**：`sl[k][idx] = cur[:pos] + ch + cur[pos:]` —— 按 `ch` 原样插入；字符增量 = **`len(ch)`**
   （单字符增量 1、双字符增量 2；**按 `len(ch)` 计**，数据实例见 §16.10）；不改其他字/列位/字号。
   双字符 `ch` 必须连续插入（dash rule 依赖相邻两个 `—` 成组）。
6. **小书保护**：页数 < **小书阈值**（实现默认见 §16.10 参数默认；换书需参数化）时整类跳过，避免同号页误插；wz6 零回归的硬条件。
7. **统计**：`[漏识元素] 灌入 … missing_char N / 跳过 M`（L596）。

## 16.4 何时不插（渲染端 + 数据端）

- `complete != true`（battle7/census 汉字类；碎片/噪声/字头字尾）；
- `verdict` 不属于 `close-ok/reclass-close/open-ok`（引号类；`no-corner`/`other`/误判不落库）；
- 目标位置已有同一字符（`target-at-pos`）或与既有条目重复（`dup-existing`）→ 数据端不落库；
- 列框未匹配 / 重定位失败 → 渲染端跳过（日志）；
- wz6 等小于小书阈值的页书 → 整类跳过（阈值见 §16.10）；
- 圈码 → 不属于 missing_char（走 ring）。

### 16.4.1 dash 与 missing_char 边界

- `class=dash` 的 `DASH_INS` 只做**列首前置**占位（行首破折号），**不适用于列中/标题行**（p57 是标题行内的
  `——`，不是列首）。
- 列中/标题行的 `——` 走 `class=missing_char`（`source=api_strip_punct`，`ch='——'`；实例见 §16.10）：
  先插两个 `—` 到文本层（可搜、字符 +2），再由 §1.0a4 的 `_dash_runs`（相邻 + 格号连续）成组 →
  `_dash_ink_seg` 从源墨实测 → `_dash_rule_tex` 画**一条** rule；文本层 `—` 以 `3 Tr` 不可见。
- 验收：punct 条目 `dash_segments` **1 组**、PDF **恰 1 条竖线**、与 class=dash 不重复画线（p57 实测数值见 §16.10）。
- battle8 的 `——` 复核结论见 §16.10；**不得**把 `——` 写成 `class=dash`（列首前置会错位）；
  fix JSON **允许** `ch='——'`（p57 实例）。

## 16.5 证据要求

- 每条必须有 `crop`（源图裁片）；按 source 的证据族：
  - `api_strip`（battle7）：crop + strip + shape + complete；t24 遗留条目无证据；
  - `api_strip_quote`：crop + cell + feat（角形方向/尺寸）+ verdict；
  - `api_strip_census`（battle9）：crop + cell + complete + shape（无 strip）；
  - `api_strip_punct`（battle9）：crop + cell + note（源墨依据；具体测量值见 §16.10）；无 feat/verdict/complete/shape。
- 裁片从 `source_pdf/<book>.pdf` 的 `cell` 处**高倍**裁出（倍率按源扫描分辨率选择；建议值见 §16.10 参数默认）；引号类必须能看出 **L 形/⌐ 形**角笔；
  汉字类必须是完整字块；p57 需 `dash_segments` + PDF 竖线双证。
- 每个 evidence 路径必须存在；门禁按批抽样（各批抽样数见 §16.10）。

## 16.6 与其它机制的交互 / 不重复保证

| 机制 | 交互 | 不重复保证 |
|---|---|---|
| `fix_split_brackets`（§1.0d，L902–957） | 先归位行首闭括号（行文本变短）→ `_br_shift` 记录移走数；missing_char 后插入并按当前行重定位 | 重定位三步（§16.3）保证行首被移走 1 字时 pos 不变错；实测例见 §16.10 |
| QSF（§1.998 / taskCM，L6374 起） | missing_char 在 QSF 之前灌入；QSF 只在列尾 `。` 等做 1:1 替换/补字 | QSF 规则未改；决策记录与上一基线逐条相同（实测计数/页码见 §16.10），无新增「闭合还补」；无同位置双引号 |
| dash rule（§1.0a4，L291–452） | `class=dash` **仅列首前置** `DASH_INS`；`class=missing_char` 的 `——`（punct 族）按 §16.4.1 画一条线；`_dash_runs`/`_dash_ink_seg`/`_dash_rule_tex` 只对文本中相邻 `—` 生效 | battle8 46 个 `——` 无一是 class=dash（43 引号重判、3 no-corner 不插）；battle9 p57 `——` 走 missing_char，dash_segments 1 组、PDF 1 条线；fix JSON 允许 `ch='——'`（p57 1 条）；不重复画线 |
| ring（§1.0a5 的 ring 分支 + `_ring_put` L460） | `class=ring` 用 `RING_INS`/圈码字形；missing_char 不处理圈码数字 | ring 与 missing_char 分属不同 class（计数见 §16.10）；无 ring 被写成 missing_char |
| punct/census 族 | census（shape/complete）+ punct（crop/cell/note）与汉字/引号同 class，用 `source` 区分 | 无 other/nonchar 条被写成 missing_char；误判/重复项不落（实例见 §16.10） |
| 去重 | 数据端按 `(page, col±2pt, pos, ch)` 去重；渲染端同列按 pos 排序 | 同 page/pos 异字 = 0；同 ch 同 pos 重复 = 0；`target-at-pos`/`dup-existing` 跳过；ch 长度 1–2 |

## 16.7 验收判据（PR 必须）

1. `verify_vert`（带 `--expect-low`）**PASS**：页数 1:1 / 整页丢失 0 / 越界 0+0；字符量相对上一基线 =
   **Σ len(ch)**（新增条目；各批增量见 §16.10）；逐页 diff 与条目一一对应。
2. 逐条落库清单与候选清单（`punct_list`/`hanzi_list`）**一一对应**：无多落/漏落；去重键无冲突；证据 0 缺失。
3. 按批抽样源图裁片：汉字为完整字块、引号为角形、punct 为源墨线/两块墨；插入位置在 v3x/v40 文本层可核（上下文/pos）。
4. **无双引号**：`「「`/`」」`/`﹁﹁` 不新增；`﹂﹂` 不新增；每个插入列内无连续重复引号。
5. **QSF 决策记录不变**（qsf.json items 与上一基线逐条相同）；`pair_balance` 的行级增量须按「行级口径假阳性」解释（源图角墨证据见 §16.10），不得当作产品回归。
6. **dash 边界**：p57 `——` 走 missing_char，`dash_segments` 1 组、PDF 恰 1 条线、无 class=dash 误用/双线；
   p1330 未落库。
7. **wz6 零回归**：`vert.tex` 逐字节 + verify PASS（基线值见 §16.10）。
8. 判据未放宽（`verify_vert.py` 不变）；token 不入库；未 commit 由 captain 统一提交。

## 16.8 跨工具契约判定

`missing_char` 目前**不是跨工具契约**：仓库内只有 `src/pipelines/build_vert.py` 读取该 class；
`src/tools/fix_tounicode_circled.py` 虽然也读同一 fix JSON，但只取 `class == "ring"`（L144–145），
对 missing_char 直接 `continue`。因此本机制不写入 `spec/governance/PIPELINE_BEHAVIOR.md`；
若将来第二个工具开始消费 missing_char，须按 V3 的做法在 PIPELINE_BEHAVIOR 竖排章节补
「字段/去重键/幂等性」契约。

## 16.9 实现锚点（2026-11-06 实测，`grep -n`；build_vert 未改）

| 项 | 当前行 |
|---|---|
| `MISSED_FIX`（默认路径/关闭/缺失处理） | L313–320 |
| `_relocate_missing`（重定位三步） | L480 |
| `_apply_missed_fix`（分组/列匹配/插入） | L512 |
| `missing_char` 排序 | L547 |
| `missing_char` 分支（插入 + 重定位失败日志；`len(ch)` 增量） | L556–570 |
| `_br_fix` 汇总 / `_br_shift` | L969–988 |
| `_MISSED_ST` 调用点 | L988 |
| 灌入统计日志 | L596 |
| `DASH_CHARS` / `DASH_*` 常量 | L321–332 |
| `_dash_rule_on` / `_dash_runs` / `_dash_ink_seg` / `_dash_rule_tex` / `_fg_origin_shift` | L336 / L347 / L365 / L433 / L445 |
| `_put_tex`（`invisible=` / dash 出字口） | L601 |

> 复核实测：`grep -n "def _relocate_missing\|def _apply_missed_fix\|_br_shift\|MISSED_FIX" src/pipelines/build_vert.py`
> 与本表一致（build_vert.py 自 t32 后未改；2026-11-06 复核）。

## 16.10 参考基线（本书实测，仅作参照，不作判据）

> 书目：wz7（竖排扫描书，1748 页）；日期/来源逐行标注。以下数字是本书数据/实测，**不进入 §16.2–§16.7 的判据**；
> 换书必须重新生成 fix JSON 与证据，不能复用这些计数。

| 书目 | 日期 | 来源 | 实测数据 |
|---|---|---|---|
| wz7 | 2026-11-06 | `docs/battle7_missing_chars.md`、`docs/battle8_quotes.md`、`docs/battle9_census.md`、`docs/battle9_fix.md`、`docs/battle9d_census_fix.md` | `missing_char` 共 **150 条** = 69 `api_strip`（58 battle7 + 11 t24 遗留）+ 72 `api_strip_quote` + 6 `api_strip_census` + 3 `api_strip_punct`；`ch` 为 **147 条单字符 + 3 条双字符**（`——` / `」。` / `」，`） |
| wz7 | 2026-11-06 | `docs/battle7_missing_chars.md` / `battle8_quotes.md` / `battle9d_census_fix.md` | 字符量增量：battle7 **+57**、battle8b **+72**、battle9 **+12**（3 条 ×2 + 6 条 ×1）；v40 产物 **931,190** 字（v38 931,178 +12） |
| wz7 | 2026-11-06 | `docs/battle8_quotes.md`、`docs/battle9_fix.md` | QSF 决策记录 **925 条 items**（append 696 / replace 229 / pair_skip 32）与 v37 逐条相同；p866 恢复「一」、p928 ﹂→一；p57/p186/p147 三条 punct 实例；p1330/p1560 不落 |
| wz7 | 2026-11-06 | `docs/battle8_quotes.md` | battle8 的 **46 个 `——`**：43 个按角形重判为 `」`（`verdict=reclass-close`），3 个 no-corner 不插；无一按 `class=dash` 落库 |
| wz7 | 2026-11-06 | `docs/battle9e_review.md`、`docs/battle9e_acceptance.md` | v40 verify PASS：1748=1748 / 931,190 / 差异>80 字页 18（预期 18）/ 整页丢失 0 / 越界 0+0；p57 `dash_segments` 1 组、PDF 1 条线；v40→v38 9 页 +12 |
| wz7 | 2026-11-05/06 | `docs/battle7_missing_chars.md`、`docs/battle8_quotes.md`、`docs/battle9d_census_fix.md` | 抽样复核数量：battle7 **24 条**、battle8b **12 条**自裁 + 全量 **72 条**位置核对、battle9 **16 条**自裁 |
| wz6 | 2026-11-06 | `docs/battle9e_review.md` | 零回归基线：`vert.tex` md5 `ae9d2f5259e12cff19e680b2a771b37d` 逐字节、verify PASS（231=231 / 97.2% / 差异 2 预期 / 0 / 0+0）；pytest 590 |
| wz7 | 2026-11-06 | `docs/battle9e_review.md`（t33/t43） | 重定位实测：p1241/p1399 由「依依不/茶筍」纠正为「依不依/筍茶」；`side` 全为 `""`、`confidence` 全为 `high` |
| wz7 | 2026-11-05/06 | `docs/battle4_ring_digits.md`、`docs/battle9d_census_fix.md` | ring **367** 条与 missing_char **150** 条分属不同 class（ring 数据见 spec 18；本 spec 不重复其判据） |
| wz7 | 2026-11-06 | `docs/battle9_fix.md` | p57 punct：线长 **79.5/80.25pt**、线宽 **5.25pt**；产物 **80.0pt / 1.255 step / w_src 5.0 / step 63.72 / x 830.005 / y 736.497–816.497 / 线宽 2.784（0.040×F）**；p147 ﹂**18.7×7.7** + 逗号 **4.5×6.8**；p186 ﹂**20.2×9.0** + 。**7.5×8.2** |

### 16.10.1 实现默认参数（参考值，非判据）

| 参数 | 实现默认 | 说明 |
|---|---|---|
| 列框匹配容差 | 0.6 pt | 运行时匹配；换书可参数化 |
| 重定位上下文长度 | 左 8 + 右 8 字 | 子串匹配窗口；可参数化 |
| 小书保护阈值 | 1000 页 | 小于该页数整类跳过；换书需参数化 |
| 完整字块门槛 | 0.55 × 步进 | `complete` 判定；应由源图/字步进自标定 |
| 裁片倍率 | 8×（或 ≥600dpi） | 取证建议倍率，不是判据 |
| 去重列框容差 | ±2 pt | 数据端去重键；可参数化 |
| 取证抽样 | ≥10 条/批（实现建议） | 按条目比例抽样；不是判据 |
