# 16 · missing_char 缺字 1:1 插入（battle6–8）

> 状态：**implemented**（battle6/8b，2026-11-05/06）
> 实现：`src/pipelines/build_vert.py` §1.0a5 / `_apply_missed_fix` / `_relocate_missing`
> 数据：`docs/vert_taskF_missed_fix.json`（默认 `VERT_MISSED_FIX`；`=0` 关闭）
> 报告：`docs/battle6_missing_chars.md`（缺字普查）、`docs/battle7_missing_chars.md`（58 汉字）、`docs/battle8_quotes.md`（72 引号）
> 关联 spec：[08 标点竖排形态](08_punct_vertical_forms.md)、[13 引號/TOC](13_vert_quotes_toc.md)、[15 破折号](15_vert_dash_rule.md)

## 16.1 目标与边界

**目标**：把 OCR **漏识、但源图确有墨迹**的单字 1:1 插回文本层（不改变已有字的字位/字号/列位口径）。
只插入**源图有证据**的字：汉字（battle7 的 58 条，`source=api_strip`）与引号（battle8b 的 72 条，
`source=api_strip_quote`）。不插破折号/圈码/标点（它们分别走 §1.0a4 dash rule、ring 机制、QSF）。

当前 fix JSON 的 `missing_char` 共 **141 条** = 58 汉字（battle7）+ 72 引号（battle8b）+ **11 条 t24 既有**
（`「`5/`」`4/`。`3/`一`1/`媽`1，历史条目，**无证据字段**；不在 battle7/8b 的 58/72 审计范围，仍按同一 `missing_char`
分支插入；其存在不影响本 spec 的字段/证据判据——新条目必须按 §16.2/§16.5 带证据）。

**非目标**：不做 OCR 全文重写；不做列框外「整字漏识」的自动插入（battle6 已证明列框外几乎不存在整字漏识）；
不做异体字归一化（由 `src/tools/variant_norm.py` 在候选阶段处理）。

## 16.2 数据契约（`docs/vert_taskF_missed_fix.json`）

文件顶层：`{"source": str, "note": str, "items": [...], "ring_digit_merge": {...}}`。
`items` 中 `class="missing_char"` 的条目，**公共字段**：

| 字段 | 类型 | 必填 | 含义 |
|---|---|---|---|
| `class` | str | 是 | 固定 `"missing_char"`（与 `ring` / `dash` 并列） |
| `page` | int | 是 | 1-based 源页号（与 `data/*_spotting_lines.json` 的 key=`page-1` 对应） |
| `col` | [x0,y0,x1,y1] | 是 | 该列 OCR 框（px，144dpi 源图坐标）；`_apply_missed_fix` 用它与当前行列框 ±0.6 匹配 |
| `pos` | int | 是 | 插入点：在该列 OCR 文本中的 **0-based** 字符下标（插入到 `text[pos]` 之前） |
| `ch` | str | 是 | 要插入的字符；只允许单字符（当前数据：汉字 58 / `」` 70 / `「` 2） |
| `side` | str | 是（可为 `""`） | 源图侧别（左右页/列侧），当前数据统一 `""` |
| `source` | str | 是 | 证据/来源：`api_strip`（battle7 汉字，行条带 API + 源图裁片）或 `api_strip_quote`（battle8b 引号，源图角形重判） |
| `confidence` | str | 是 | 人工/流程置信级别：当前 `high` |
| `ratio` | number | 是 | API 复核置信度（0–1），仅记录，不参与插入判据 |
| `exp_len` | int | 是 | 该列 OCR 文本长度（`len(text)`），用于核对插入后长度 +1 |
| `text` | str | 是 | 该列 **原始 OCR 文本**（重定位上下文；`_relocate_missing` 用左 8 + 右 8） |
| `api` | str | 是 | 同一列的 API 复核文本（含目标字；引号类还用于说明重判） |
| `crop` | str | 是 | 源图证据裁片路径（相对仓库根；56 汉字在 `tmp_vert/battle6/all_insert_crops/`，引号在 `tmp_vert/battle8/quote_crops/`） |
| `cell` | [x0,y0,x1,y1] | 是 | 该字在源图上的单元格（px），裁片/角形判据的输入 |
| `feat` | dict | 汉字/引号均建议 | 形状/角形特征：汉字 `{w,h,fill}`；引号 `{w,h,fill,left,right,top,bottom,corner,side,ends}` |
| `verdict` | str | 引号必填 | `close-ok` / `reclass-close` / `open-ok`（引号类） |
| `strip` | str | 汉字必填（t24 既有 11 条无） | 行条带图（`tmp_vert/battle6/all25/strips/`）；引号类无此字段（以 `crop+cell+feat` 为证据） |
| `shape` | dict | 汉字必填（t24 既有 11 条无） | `{w,h,fill}`（完整字块判据） |
| `complete` | bool | 汉字必填（t24 既有 11 条无） | `true` = 完整字块（<0.55 步进/碎片不落库）；引号类无此字段 |

**数据不变量**（落库脚本负责，渲染端只读）：
- 同一 `(page, pos)` 不得出现不同 `ch`；同一 `ch` 不得在同一 `(page, pos)` 重复；
- 去重键 `(page, col±2pt, pos, ch)`；已存在目标字（`target-at-pos`）或与既有条目重复（`dup-existing`）时**不落库**；
- 每条的 `crop` 必须存在；引号类 `feat.corner=true`；汉字类 `complete=true`；
- 不同 `source` 的字段族见上表（`strip/shape/complete` 与 `feat/verdict` 二选一）。

## 16.3 插入机制

1. **开关/输入**：`VERT_MISSED_FIX` 未设 → 默认 `docs/vert_taskF_missed_fix.json`（存在才启用）；
   `=0/off/false` 关闭；文件缺失 → 关闭。见 `build_vert.py` L313–320 `MISSED_FIX`。
2. **分组与列匹配**（`_apply_missed_fix` L512 起）：按 `(page, tuple(col))` 分组；对每组的每个 missing_char，
   在当前页 `sl[k]` 的列框中找 `(min x/2, min y/2, max x/2, max y/2)` 与 `col` 各分量差 ≤0.6 的列。
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
5. **写入**：`sl[k][idx] = cur[:pos] + ch + cur[pos:]`（1:1 插入，不改其他字/列位/字号）。
6. **小书保护**：`len(keys) < 1000` 时整类跳过（wz6 231 页不读 missing_char，避免同号页误插；wz6 零回归的硬条件）。
7. **统计**：`[漏识元素] 灌入 … missing_char N / 跳过 M`（L596）。

## 16.4 何时不插（渲染端 + 数据端）

- `complete != true`（汉字类；碎片/噪声/字头字尾）；
- `verdict` 不属于 `close-ok/reclass-close/open-ok`（引号类；`no-corner`/`other`/误判不落库）；
- 目标位置已有同一字符（`target-at-pos`）或与既有条目重复（`dup-existing`）→ 数据端不落库；
- 列框未匹配 / 重定位失败 → 渲染端跳过（日志）；
- wz6 等 `len(keys) < 1000` 的小页书 → 整类跳过；
- `ch` 为 `—`/`——`/圈码/多字符 → 不属于 missing_char（分别走 dash/ring；battle8 的 46 个 `——` 中 43 个按
  引号重判为 `」`，3 个 no-corner 不插，**fix JSON 中无 `ch="——"`**）。

## 16.5 证据要求

- 每条必须有 `crop`（源图裁片）；汉字类另有 `strip`/`shape`/`complete`，引号类另有 `feat`（角形方向/尺寸）与 `verdict`。
- 裁片从 `source_pdf/<book>.pdf` 的 `cell` 处 8×（或 ≥600dpi）裁出；引号类必须能看出 **L 形/⌐ 形**角笔
  （闭引号左竖+底横；开引号右竖+顶横），不能是长横破折号；汉字类必须是完整字块（非碎片/并字/噪点）。
- 每个 evidence 路径必须存在；门禁抽查 ≥10 条（battle7 24 条、battle8b 12 条自裁 + 全量 72 条位置核对）。

## 16.6 与其它机制的交互 / 不重复保证

| 机制 | 交互 | 不重复保证 |
|---|---|---|
| `fix_split_brackets`（§1.0d，L902–957） | 先归位行首闭括号（行文本变短）→ `_br_shift` 记录移走数；missing_char 后插入并按当前行重定位 | 重定位三步（§16.3）保证行首被移走 1 字时 pos 不变错；实测 p1241/p1399 由「依依不/茶筍」纠正为「依不依/筍茶」 |
| QSF（§1.998 / taskCM，L6374 起） | missing_char 在 QSF 之前灌入；QSF 只在列尾 `。` 等做 1:1 替换/补字 | QSF 规则未改；battle8b 的 qsf.json **925 条 items 与 v37 逐条相同**（append 696/replace 229）；插入引号只改变 2 页的配对状态（p866 恢复「一」、p928 ﹂→一），无新增「闭合还补」；无同位置双引号 |
| dash rule（§1.0a4，L291–452） | `class=dash` 走 `DASH_INS`/`_dash_rule_*`；`class=missing_char` 只插 `ch`，绝不插 `—` | 46 个 `——` 无一按破折号落库；43 个按引号重判（`verdict=reclass-close`），3 个 no-corner 不插；fix JSON 无 `ch=——` |
| ring（§1.0a5 的 ring 分支 + `_ring_put` L460） | `class=ring` 用 `RING_INS`/圈码字形；missing_char 不处理圈码数字 | 367 条 ring 与 141 条 missing_char 分属不同 class；无 ring 被写成 missing_char |
| 去重 | 数据端按 `(page, col±2pt, pos, ch)` 去重；渲染端同列按 pos 排序 | 同 page/pos 异字 = 0；同 ch 同 pos 重复 = 0；`target-at-pos`/`dup-existing` 跳过 |

## 16.7 验收判据（PR 必须）

1. `verify_vert`（带 `--expect-low`）**PASS**：页数 1:1 / 整页丢失 0 / 越界 0+0；字符量相对上一基线 = 落库条数
   （battle7：+57；battle8b：+72；逐页 diff 与条目一一对应）。
2. 逐条落库清单与候选清单（`punct_list`/`hanzi_list`）**一一对应**：无多落/漏落；去重键无冲突；证据 0 缺失。
3. 抽 ≥10 条源图裁片：汉字为完整字块、引号为角形；插入位置在 v3x 文本层可核（上下文/pos）。
4. **无双引号**：`「「`/`」」`/`﹁﹁` 不新增；`﹂﹂` 不新增；每个插入列内无连续重复引号。
5. **QSF 决策记录不变**（qsf.json items 与上一基线逐条相同）；`pair_balance` 若因行中插入闭引号 +1，
   须按「行级口径假阳性」解释（源图 11/11 有角墨），不得当作产品回归。
6. **wz6 零回归**：`vert.tex` md5 `ae9d2f5259e12cff19e680b2a771b37d` 逐字节 + verify PASS（231=231 / 越界 0+0）。
7. 判据未放宽（`verify_vert.py` 不变）；token 不入库；未 commit 由 captain 统一提交。

## 16.8 跨工具契约判定

`missing_char` 目前**不是跨工具契约**：仓库内只有 `src/pipelines/build_vert.py` 读取该 class；
`src/tools/fix_tounicode_circled.py` 虽然也读同一 fix JSON，但只取 `class == "ring"`（L144–145），
对 missing_char 直接 `continue`。因此本机制不写入 `spec/governance/PIPELINE_BEHAVIOR.md`；
若将来第二个工具开始消费 missing_char，须按 V3 的做法在 PIPELINE_BEHAVIOR 竖排章节补
「字段/去重键/幂等性」契约。

## 16.9 实现锚点（2026-11-06 实测，`grep -n`）

| 项 | 当前行 |
|---|---|
| `MISSED_FIX`（默认路径/关闭/缺失处理） | L313–320 |
| `_relocate_missing`（重定位三步） | L480 |
| `_apply_missed_fix`（分组/列匹配/插入） | L512 |
| `missing_char` 排序 | L547 |
| `missing_char` 分支（插入 + 重定位失败日志） | L556–570 |
| `_br_fix` 汇总 / `_br_shift` | L969–988 |
| `_MISSED_ST` 调用点 | L988 |
| 灌入统计日志 | L596 |

> 复核实测：`grep -n "def _relocate_missing\|def _apply_missed_fix\|_br_shift\|MISSED_FIX" src/pipelines/build_vert.py`
> 与本表一致（见 PR 描述）。
