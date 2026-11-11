# TYPOGRAPHY_EVAL.md — 排版评测契约（v1）

> **状态**：implemented（t239/t242/t244/t245/t250；工具 `src/test/verify_typography.py`）
> **类型**：governance（横排/竖排/古籍共用；只评「产物排版几何」，不改渲染）
> **依据**：GB/T 15834—2011《标点符号用法》（`docs/15834-2011-gbt-e-300.pdf`）§5；`docs/scan2pdf_review.md` t201；`src/test/verify_geom.py`、`src/test/verify_vert.py`
> **兄弟 spec**：[PUNCTUATION.md](PUNCTUATION.md)（标点用法/配对）、[PUNCT_EVAL.md](PUNCT_EVAL.md)（标点识别率）、[CONTENT_EVAL.md](CONTENT_EVAL.md)（内容 CER）
> **纪律**：判据/数据分离；书无关；不把某书违规写成硬编码；不 commit

---

## 0. 目的、边界、术语

### 0.1 目的

把「排版是否还原」变成**可校验、可归因、不误伤特殊版式**的评测契约。回答三件事：

1. 哪些排版错误**任何书都不能接受**（强制层）；
2. 产物相对**源书**保真到什么程度（源书保真层，自校准）；
3. 国标 GB/T 15834 §5 的禁则/占格**哪些能判、怎么归因、何时才允许 fail**（规范参考层）。

### 0.2 非目标

- 不做 OCR 纠错/语言模型改写（`CORRECTED_TEXT.md` 管）；
- 不重算标点**用法/配对**（`PUNCTUATION.md`）与**识别率**（`PUNCT_EVAL.md`）；
- 不替代 `verify_geom`/`verify_vert` 的页数、pitch、overflow、越界硬门禁；
- 不用国标硬卡古籍夹注、竖排特殊版式、影印页、目录三栏等**源书自身版式**；
- 不要求渲染器改排版（本 spec 只定义评测；修复由后续任务按归因处理）。

### 0.3 术语

| 术语 | 定义 |
|---|---|
| 参与判定行 | 产物 PDF 文本行中，属于**正文/目录/标题等可读文本**、且未被 `non_body_page` 豁免的行 |
| 合规行 | 参与判定行中，无「未豁免违规」的行 |
| 排版合规率 | `合规行 / 参与判定行`（按行计；不按字符加权） |
| 违规 | 一条「规则 ID + 位置 + 元素 + 归因」记录 |
| 归因 | `source_inherent` / `render_introduced` / `non_body_page`（§4） |
| 书型 | `horizontal` 现代横排 / `vertical` 竖排 / `ancient` 古籍特征 / `photocopy` 影印页 |
| 源书基准 | 同一页 OCR lines + coords（必要时 layout blocks）；不跨书硬编码 |

---

## 1. 三层判据（必须同时存在）

### L1 强制层（恒 `fail`，任何书型）

| ID | 判据 | 机检 | 粒度 | 失败命名 |
|---|---|---|---|---|
| M2 | 文本越界 | span bbox 越出页面可打印区（页幅 ± 容差），或越出 `PAGE_IMAGE` 贴图页可视区 | span | `hard_text_out_of_page` |
| M5 | 页数不 1:1 | 输出页数 ≠ 源 OCR 页数（含 split/missing） | 全书 | `hard_page_1to1` |

- L1 与 `verify_geom`/`verify_vert` 重叠部分**只报一次**：见 §7。
- L1 是唯一**不受决策 A 降级**的层；任何归因（含 `source_inherent`）都不能豁免 L1。

### 1.1 L1 范围与重叠边界（t255）

- L1 仅保留 **M2 bbox 越出可打印区 / M5 页数 1:1** 两条。
- **M3 页码错位**由 `verify_geom`/`verify_vert` 的页数/占位校验负责；**M4 字符丢失/重复**由 `verify_vert` 字符量、`verify_geom` 行数校验负责，排版工具**不重复实现**，避免口径打架。
- v1.1 若要加 M3/M4，须先解决与 verify 的口径去重并在本 spec 版本化。
- **M5 子集行为（正确）**：当产物是 `--pages` 子集而传入全书 lines 时，`hard_page_1to1` 会触发——这是 M5 的正确行为；scan2pdf 的 `--pages` 经 `slice_inputs` 传切片 lines，pipeline 场景不会误报。

### 1.2 M1 诊断级（t255）

- 跨视觉行 span bbox 重叠在真实 CJK 书上天然高发（wz2 实测 9k+：行盒高 > 行距、标点盒内嵌），不能作为 fail 判据。
- 实现保留 `_general_overlap`（跨视觉行、面积 > `0.02×min`、同视觉行/标点组不判），但**默认关闭**；`TYPOGRAPHY_M1=1` 时输出单列 `diagnostics.M1` / `counts.m1_diagnostic`，**不计入 violations/hard/exit**。
- 后续改进方向：用墨迹/字形级几何（源图墨迹、glyph 轮廓）替代 bbox；解决后再讨论是否升 L1。
- 因此 `layers.L1` 报告只列 **M2/M5**。

### L2 源书保真层（核心指标，自校准，不阻断）

以**源书自身**为基准，测产物与源的相对偏差；不做跨书绝对阈值。

| ID | 指标 | 机检口径 | 粒度 | 默认阈值（provisional） |
|---|---|---|---|---|
| F1 | 行位偏差 | 同行/同列文本行中心 vs 源 OCR 行中心（按行对齐；无 GMPG 时按阅读序稳定匹配） | 行 | 中位 ≤ 3% 页高，P95 ≤ 8% |
| F2 | 字号比例 | 产物 span 字号 / 源 OCR 行高映射字号；同页同段落内相对关系 | 行/段 | 中位 0.9–1.1 |
| F3 | 缩进关系 | 段首行 x 缩进 vs 源段首缩进（相对版心宽） | 段 | 差 ≤ 1 字步进 |
| F4 | 行距/pitch | 与 `verify_geom` 的 pitch 指标同口径，不重复计算 | 行对 | 见 verify_geom |
| F5 | 页幅/占位 | 页幅、版心、首末行占位 vs 源 | 页 | 中位 ≤ 3%，P95 ≤ 8% |

- L2 输出**指标 + 分位数**，默认**不阻断**；阈值 provisional，待 gold 标定后版本化。
- L2 的基准数据来自 OCR lines/coords + 源 PDF 页幅；缺失源时只报 `not_available`，不得用默认值假装通过。

### L3 规范参考层（GB/T 15834—2011 §5，gating）

- 默认 `warn` + 报告；**只有归因为 `render_introduced` 的禁则违规升级 `fail`**（决策 A，§3）。
- 按书型 gating（§5）：横排现代书启用；竖排按 §5.2；古籍/影印页按 §5 降级/豁免。
- 每条规则有独立 ID、粒度、违规命名；同一行多规则命中分别计数（合规率按行去重）。

---

## 2. GB/T 15834—2011 §5 可执行判据

> 下列「规则摘要」按 §5 条序归纳，**不替代国标原文**；机检算法与粒度是评测契约。原文见 `docs/15834-2011-gbt-e-300.pdf` §5。
>
> **命名以实现为准（t250）**：实现 `src/test/verify_typography.py` 的 `GB51_RULES`/`GB52_RULES` 为唯一规则名账本；本表 ID 为条序，名称差异见下表映射（避免 spec/实现再漂）。

| 条序 | 实现名 |
|---|---|
| 5.1.1 | `gb51_dot_line_start` |
| 5.1.2 | `gb51_question_exclaim_cell` |
| 5.1.3 | `gb51_quote_bracket_break` |
| 5.1.4 | `gb51_dash_break` |
| 5.1.5 | `gb51_ellipsis_break` |
| 5.1.6 | `gb51_connector_cell` |
| 5.1.7 | `gb51_interpunct_cell` |
| 5.1.9 | `gb51_separator_cell` |
| 5.1.10 | `gb51_lineend_halfwidth` |
| 5.2.1-5.2.6 | `gb52_*`（6 条，见实现） |


### 2.1 §5.1 横排（11 条）

| ID | 规则摘要 | 机检算法 | 粒度 | 违规命名 |
|---|---|---|---|---|
| 5.1.1 | 点号（，。、；：？！）不出现在行首 | 取行首非空白字符；∈ START_PROHIBIT 且不是源书同位置同类 → 违规 | 行·字符 | `gb51_dot_line_start` |
| 5.1.2 | 点号在行末/叠用时的占格：点号占一个字符位置，叠用不额外占格 | 统计点号连续 run 的宽度/字步进；宽度 > 1.15×字步进或叠用段宽 ≠ 1×步进 → 违规 | run·字符 | `gb51_dot_cell` |
| 5.1.3 | 后引号/后括号不出现在行首 | 行首字符 ∈ CLOSE_QUOTE/CLOSE_BRACKET → 违规 | 行·字符 | `gb51_close_line_start` |
| 5.1.4 | 破折号、省略号不得跨行断开，占两格且连续 | 行末/行首出现 `—`/`…` 单侧；相邻行拼接后 run 长度与占格不符 → 违规 | 行对·run | `gb51_dash_ellipsis_break` |
| 5.1.5 | 引号/括号/书名号不得跨行断开；后引号/后括号不落行首，前引号/前括号不落行末 | 行末 ∈ OPEN_QUOTE/OPEN_BRACKET 或行首 ∈ CLOSE_QUOTE/CLOSE_BRACKET；配对标点跨行 → 违规 | 行对·字符 | `gb51_pair_break` |
| 5.1.6 | 连接号/间隔号等特殊符号的占格与断行 | 连接号 `-`/`～`/`—` 的 run 长度/宽度 vs 字步进；行末断开 | run·行对 | `gb51_connector_cell` |
| 5.1.7 | 前引号/前括号不出现在行末 | 行末 ∈ OPEN_QUOTE/OPEN_BRACKET → 违规 | 行·字符 | `gb51_open_line_end` |
| 5.1.8 | 标点与相邻汉字/数字的间距不额外占格（全角标点内建空白） | **豁免**：着重号/专名号属墨迹层，PDF 文本层无信息；v2 源图墨迹再做 | — | `not_machine_checkable_from_text_layer` |
| 5.1.9 | 行末标点不悬挂到版心外；标点紧随前字、不单独成行 | 行末标点 bbox 右缘 > 版心右缘；单标点行 → 违规 | 行·span | `gb51_punct_hang` |
| 5.1.10 | 行末全角/半角宽度：行末半角字母/数字与全角标点的宽度关系符合国标 | 行末字符宽度 vs 字步进；`halfwidth_at_full_cell_end`（行末半角后无空格/无标点）→ 违规 | 行·字符 | `gb51_lineend_width` |
| 5.1.11 | 其他行首/行末禁则（空格、控制符、不可见字符） | **豁免**：原文为许可（可适当压缩标点占用空间），不产生违规 | — | `permissive_clause` |

### 2.2 §5.2 竖排（6 条）

| ID | 规则摘要 | 机检算法 | 粒度 | 违规命名 |
|---|---|---|---|---|
| 5.2.1 | 竖排点号位于字格右侧/下方（不压字、不出格） | 点号 span 相对本字格的 x/y 偏移；越出格或与字重叠 > 5% → 违规 | 字符·span | `gb52_dot_position` |
| 5.2.2 | 竖排引号/括号方向与位置（列内右侧、开口朝阅读方向） | 引号/括号 glyph 方向 + 相对前字位置；方向/侧别不符 → 违规 | 字符·span | `gb52_quote_bracket_position` |
| 5.2.3 | 竖排破折号/省略号成竖线、占格、不断列 | 竖线 run 的 y 长/线宽/列内位置；列首/列末断开 → 违规 | run·列对 | `gb52_dash_ellipsis_vertical` |
| 5.2.4 | 竖排标点占一个字符格（叠用不额外占格） | 同 5.1.2 的竖排版（以列步进为字步进） | run·字符 | `gb52_dot_cell` |
| 5.2.5 | 竖排列首/列末禁则（点号/后引号/后括号不落列首；前引号/前括号不落列末） | 列首/列末字符集合；列内顺序 | 列·字符 | `gb52_column_edges` |
| 5.2.6 | 竖排数字/西文/符号位置（不旋转、不横倒、不压格） | span 旋转角/bbox 方向；数字串方向 | span/串 | `gb52_latin_digit_position` |

- 竖排规则仅在 `book_type=vertical` 或页面阅读方向为竖排时启用；横排页不跑 §5.2（防误报）。
- 5.2 规则默认 `warn`；`render_introduced` 且落在正文列时才可升级 `fail`；影印页/贴图页整体豁免。

---

### 2.4 不可机检条款与豁免理由

- 5.1.8 着重号/专名号位置：需要字下/字侧墨迹检测，PDF 文本层无此信息 → `not_machine_checkable_from_text_layer`（v2 源图墨迹）。
- 5.1.11 许可压缩：国标为「可适当压缩」，不是约束 → `permissive_clause`（不产生违规）。
- 因此 §5.1 机检表为 **9 条**（5.1.1/2/3/4/5/6/7/9/10），加 §5.2 六条 = **15 条机检 + 2 条豁免**。

## 3. 严格度策略（决策 A）

### 3.1 三层默认级别

| 层 | 默认级别 | 是否阻断 | 升级条件 |
|---|---|---|---|
| L1 强制 | **fail** | 是（门禁退出码非 0） | 不允许升级/降级 |
| L2 保真 | **metric（不阻断）** | 否 | 阈值 provisional；仅报告，不判 fail |
| L3 国标参考 | **warn** | 否 | **仅 `render_introduced` + 正文页 + 规则在本书型启用** → `fail` |

### 3.2 决策 A（逐字）

- **L3 默认 `warn` + 出报告；只有归因为 `render_introduced` 的禁则违规才升级 `fail`。**
- `source_inherent` **不判罚**（保留违规记录，计入 waived；合规率按「waived=合规」处理）。
- `non_body_page` **整页豁免**（不参与 L3/L2；L1 的页数/字符量仍按全书判）。
- `unknown`（源侧无法对齐/OCR 缺失）→ **warn 不 fail**，要求人工抽样确认，不得默认升级。
- 任何 `fail` 必须携带 `rule_id / page / line / char / attribution / evidence`，便于人工复核。

### 3.3 门禁输出

```json
{
  "typography": {
    "verdict": "pass|warn|fail",
    "compliance_rate": 0.0,
    "body_lines": 0,
    "compliant_lines": 0,
    "violations": [{"rule_id":"5.1.1","name":"gb51_dot_line_start",
                    "page":5,"line":2,"char":"—","attribution":"render_introduced",
                    "severity":"fail","evidence":{"source_line":"...","product_line":"..."}}],
    "waived": [{"rule_id":"5.1.1","pages":[10],"attribution":"source_inherent"}],
    "non_body_pages": [104],
    "layers": {"hard":"pass","fidelity":"metric","gb":"warn"},
    "thresholds_version": "provisional-v1"
  }
}
```

---

## 4. 三类归因（可复现判据）

### 4.1 `source_inherent`（源书自身违规 → 不判罚）

**输入**：源 OCR lines + coords；产物页/行/字符；源页 key（0-based）；行索引或行文本锚点。
**判定**：

1. 同一 `page_key` + 同一 `line_index` 的源行存在，且源行首/行末**同一位置**已出现同字符违规 → 高置信；
2. 行索引因 OCR 合并/拆分不可用：同一页内**同文本前缀（≥8 字）**的源行存在且同位置违规 → 中置信；
3. 仅在源页任意行找到同字符 → 低置信（**不判罚，记 unknown**）。

**置信度要求**：高/中置信才归 `source_inherent`；低置信 → `unknown`。
**例**：ghbq p10 `——毛泽东关于党不变质思想探寻` 源书行首即 `——` → `source_inherent`。

### 4.2 `render_introduced`（源合规、产物违规 → 升级 fail）

**输入**：同 §4.1；另需源行**同位置**的字符/占格证据。
**判定**：

1. 源行存在（高/中置信），且源行首/行末**不是**该违规字符 → `render_introduced`；
2. 源行存在但源字符被 OCR 漏识/替换：需 coords + 源图墨迹抽样确认；无源图证据 → `unknown`，不升级；
3. 产物有、源书完全没有对应行（凭空新增）→ `render_introduced`（高置信，行级）。

**置信度要求**：高/中置信才 fail；低置信 → warn。
**例**：wz4 p138 `。3⃝...` 源行无行首 `。`（`。` 为脚注标记/断行引入）→ `render_introduced`。

### 4.3 `non_body_page`（元数据/水印/来源说明页 → 整页豁免）

**输入**：scan2pdf `book_type`、`PAGE_IMAGE_PAGES`/`_page_img_full()` 结果、layout blocks、页面文本统计。
**判定（任一满足，且高置信）**：

- 页面被 `PAGE_IMAGE_PAGES` 或整页贴图机制标记（影印/封面/图版）；
- 页文本匹配来源说明/元数据特征：`Anna's Archive` / `Document generated by` / `filesize` / `md5` / `pdg_dir_name` / `total_pages` 等（≥3 个特征串同页）；
- layout 中非文本块（image/chart/figure）面积 ≥ 页面 40%，且文本行 < 5 行。

**处理**：整页从 L2/L3 的参与判定行/字符中排除；L1 仍按全书页数/字符量判（不允许整页丢失）。
**例**：ghbq p104 Anna's Archive JSON（20 行）→ `non_body_page`，13 条 `”` 行首不判罚；wz2 p783 同型（17 行）。

### 4.4 归因优先级

`non_body_page` > `source_inherent` > `render_introduced` > `unknown`；同一违规只能有一个归因。

---

## 5. 书型 gating

| 书型/特征 | L2 | L3 §5.1 | L3 §5.2 | 处理 |
|---|---|---|---|---|
| `horizontal` 现代书 | 启用 | **启用（warn）** | 禁用 | 默认；render_introduced 才 fail |
| `vertical` 竖排书 | 启用 | 禁用 | **启用（warn/统计）** | 按列评测；render_introduced 才 fail |
| 古籍特征（夹注小字/无版框/竖排/双行注） | 启用 | 禁用/仅统计 | 统计（warn） | 夹注小字、行内双行注不按现代点号禁则判罚 |
| 影印页（整页贴图） | 豁免 | 豁免 | 豁免 | `PAGE_IMAGE_PAGES`/`_page_img_full` 标记；只保 L1 页数 |
| 目录三栏/页码前置（如 ghbq TOC） | 启用 | 启用但 `number` 类块单独规则 | 禁用 | 三栏页码不算点号违规；栏内点号仍可判 |

- 书型来源复用 scan2pdf `book_type`（`axis`/`has_frame`/`multi_format`）+ 页面级 `PAGE_IMAGE` 机制；不得用书名硬编码。
- `multi_format` 书按页判定：每页取该页 book_type/特征；混合页不静默按主导类型。
- gating 配置作为评测输入（`book_type` JSON + 页面特征），不得写进渲染器。

---

## 6. 指标定义

### 6.1 排版合规率（主指标）

```
participating_lines = body_lines - non_body_lines
compliant_lines = participating_lines - render_introduced_violation_lines
compliance_rate = compliant_lines / participating_lines   （0 行 → null，不判 pass）
```

- 违规行按**行**去重（同一行多规则只扣一次）；`source_inherent` waived 行**计入合规**。
- 分母不含 non_body 行；`unknown` 行计入分母并标记 `low_confidence`。
- 输出分规则计数、分归因计数、分书型计数。

### 6.2 违规分类计数

```
violations_by_rule = {rule_id: count}
violations_by_attribution = {source_inherent: n, render_introduced: n, non_body_page: n, unknown: n}
```

### 6.3 保真层指标（L2）

- `line_y_err_pct` 中位/P95；`font_ratio` 中位/P95；`indent_err_em` 中位/P95；`pitch_ok_pct`（复用 verify_geom）；`page_fill_err_pct`。
- 输出 `not_available` 当源数据缺失；不得用默认阈值假装通过。

---

## 7. 与现有验证的边界（不重复计算）

| 检查 | 归属 | 本 spec 处理 |
|---|---|---|
| 页数 1:1、split/missing | `verify_geom` / `verify_vert` | L1-M5 只引用其结果，不重算 |
| pitch / 行距 | `verify_geom` | L2-F4 直接引用，不重算 |
| overflow / 文本越界 | `verify_geom` | L1-M2 复用，不重复计数 |
| 竖排字符量/越界 | `verify_vert` | L1-M2 复用；字符量由 verify_vert 负责；竖排 L3 只看列位/方向 |
| 标点用法/配对 | `PUNCTUATION.md` | 本 spec 只看**行首/行末/占格/跨行**几何，不判用法 |
| 标点识别率 | `PUNCT_EVAL.md` | 本 spec 不评 OCR 识别，只评产物排版 |
| 内容 CER | `CONTENT_EVAL.md` | 本 spec 不评内容；字符丢失由 verify_vert 负责 |

- 同一硬约束只在一个门禁里判 fail：`verify_geom/verify_vert` 仍是页数/pitch/overflow 的**唯一 fail 源**；typography eval 输出 `hard` 仅作镜像，不二次退出。
- **工具 exit 与 gate verdict 分离（t250）**：`verify_typography.py` 自身 exit=1 仅表示排版报告 FAIL（供人工/独立任务）；`scan2pdf`/`quality_gate` 只附 `typography` 分项，**不改变既有 geometry gate verdict**（report 显式 `gate_effect=none`）。

---

## 8. 实测基线（2026-11-11；参考值，非判据）

### 8.1 命令

```bash
# 产物文本行（fitz dict lines）；同一脚本量行首/行末
/usr/bin/python3 - <<'PY'
import fitz
START=set('，。、；：？！）】》」』”’…—·')
for p in ('output/ghbq_full/ghbq_corrected.pdf',
          'tmp_vert/scan2pdf/wz4_calib.pdf',
          '/tmp/t238_wz2_full.pdf'):
    d=fitz.open(p); n=0; v={}
    for pg in d:
        for b in pg.get_text('dict').get('blocks',[]):
            for l in b.get('lines',[]):
                t=''.join(s.get('text','') for s in l.get('spans',[])).strip()
                if not t: continue
                n+=1
                if t[0] in START: v[t[0]]=v.get(t[0],0)+1
    print(p,n,v)
PY
# wz2 全量产物临时构建（t208 未回退时 gate 可能 REJECT；本表只用文本行）
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz2.pdf --book wz2 \
  --out /tmp/t238_wz2_full.pdf --data-dir data/wz2 --skip-ocr --force
```

### 8.2 基线表

| 书 | 产物页 | 文本行 | 非正文页（行） | 参与行 | 违规（行首/行末） | 归因 | 合规率 |
|---|---|---|---|---|---|---|---|
| ghbq | 104 | 2102 | p104（20） | 2082 | 行首：`—`×2、`”`×13；行末 0 | `—` p5 render / p10 source；`”`13 全在 p104 non_body | **2081/2082 = 99.952%** |
| wz4 | 677 | 22961 | 0 | 22961 | 行首：`—`×2、`。`×6、`·`×2；行末 0 | `—`×2、`·`×2 source（p4/p183/p353）；`。`×6 render（p138/p190/p378/p382/p544/p668） | **22955/22961 = 99.974%** |
| wz2 | 783 | 32622 | p783（17） | 32605 | 行首：`·`×1、`。`×2、`”`×1、p783 `”`×12；行末 0 | `·` p136 source；`。` p263/p300 render；`”` p320 render；p783 12 条 non_body | **32602/32605 = 99.991%** |

### 8.3 归因核对与差异说明

- ghbq `—`2：p5 `—北京: …` 源行无对应行首（render_introduced，按决策 A 应 fail）；p10 `——毛泽东…` 源书目录行首即 `——`（source_inherent，不判罚）。`”`13 全在 p104 Anna's Archive JSON（non_body_page，整页豁免）。
- wz4 `—`2/`·`2：源 CIP/目录/正文行首已存在（source_inherent）；`。`6：源行无行首 `。`（脚注标记/断行引入）→ render_introduced（若源图核实为源书自身，可降级为 source_inherent）。
- wz2 `·`1（p136 史记引文行首）source_inherent；`。`2（p263/p300）与 `”`1（p320）源行无同位置 → render_introduced；p783 JSON 12 条 non_body。
- **行末违规实测 0**（ghbq/wz4/wz2）。任务初稿提到 ghbq 行末 `/`×1；当前产物（`ghbq_corrected.pdf`）未复现，疑为旧产物/行合并口径差异；本表按当前产物记录，待 v1.1 复核。
- 初稿 wz4 行数 22,239 / `。`×3 与本次 22,961 / `。`×6 不同：当前产物含 t208 前构建差异；本表为**当前产物 + 当前提取口径**（fitz line，非 span 行），基线版本需在实现时冻结。

---

## 9. 与兄弟 spec 的关系

| spec | 管什么 | 本 spec 如何引用 |
|---|---|---|
| `PUNCTUATION.md` | 标点**用法/配对/破折号合法位置**（GB/T 15834 §4/§5 规则表） | 本 spec 只取「行首/行末/占格/跨行」的**几何**部分；用法合法性不重复判 |
| `PUNCT_EVAL.md` | 标点**识别率**（cell/sequence、P/R） | 不评识别；本 spec 的违规若源于 OCR 漏识 → 归因 `unknown`/source，不误判渲染 |
| `CONTENT_EVAL.md` | 内容 CER/缺字 | 不评内容；字符量由 verify_vert 负责 |
| `HORIZONTAL_CALIB.md` | 标定值/审计 | L2 使用其 pitch/字号/覆盖率字段，不重复计算公式 |
| `PAGE_IMAGE_LAYOUT.md` | 图块/整页贴图 | `non_body_page` 与 L1-M2 使用其 `PAGE_IMAGE`/整页覆盖信号 |
| `CORRECTED_TEXT.md` | 人工文本校正 | 校正后文本进入产物；本 spec 不判 OCR 错字 |

---

## 10. 实现锚点（implemented；工具 `src/test/verify_typography.py`）

- 评测工具：`src/test/verify_typography.py`（实现锚点）；输入 `--src-pdf/--lines/--book-type/--page-image-pages/--json`，输出 §3.3 JSON。
- 行提取：优先 `fitz` dict lines；带 GMPG 时用 GMPG 对齐源页，无 GMPG 时按阅读序 1:1。
- 归因：读 OCR lines/coords + 源 PDF 页幅；L2 复用 `verify_geom --json`；L1 复用 verify 结果。
- 接线（后续）：scan2pdf report 增 `typography` 块；质量门禁默认 `warn`，`render_introduced` 才 fail；`--typography-strict` 预留（不默认）。
- 测试：合成本（行首/行末/跨行/叠用/竖排/影印页/源书违规/渲染引入）各 ≥1；红/绿双侧。

---

## 11. 开放问题（待 captain/实现裁决）

1. 行末 `/` 初稿样本未复现：需确认旧产物/OCR 行合并口径，v1.1 再冻结。
2. wz4 `。`×6 的源图核实：脚注标记是否源书自身行首；若源书自身 → 降 source_inherent。
3. `5.1.2/5.1.5` 的叠用占格阈值（1.15×步进）为 provisional，需 gold 标定。
4. `non_body_page` 元数据特征串为参考集合，需按新书扩展但不得写成书名硬编码。
5. L2 阈值 provisional；跨书/跨纸型需按源书分位数自校准。


## 12. v1 冻结基线（t250）

- 工具：`src/test/verify_typography.py` sha256 `55329569785aa3215bb0492a56ff2dbf1eced739c3bdf2c3e7a9e4510b2e5689`（2026-11-11）
- 产品：`output/ghbq_full/ghbq_title_toc2.pdf` md5 `beba0f6c59d9a07515e37501fa09963e`（sha256 `e8ef5ef7…`）
- 产品：`output/wz4/wz4_s4.pdf` md5 `80d537e2b54afbcfd90bdf7901559aa7`（t255 重算；原 `dd011c2a…` 已重建）
- 口径：旧 `ghbq_title_toc.pdf` 仅作历史 RED 样例；v1 基线以本表冻结的以上两产物为准；产物重建即需更新本表并重跑。

### 12.1 已知渲染改动归属与回退（F9）

- p5 CIP 行首单 `—` 去除属 **t242 build_geom 修复**，不属于评测任务；评测任务不改渲染。
- 回退：撤销 `build_geom` 的 CIP 单破折号去除改动（或恢复原行文本）后重建；无独立 env 开关（如需可后续加 `CIP_STRIP_DASH=0`）。

### 12.2 p97 单列跟踪（F10）

- p97 横向越界 34 条为**既有产品缺陷**，由 `hard_text_out_of_page` 正确抓到；评测任务不修改产物。
- 单列跟踪：p97 修复（OCR 整行并行检测/切行或整页贴图）由独立 issue/任务处理；本 spec 不将 L1 纳入 gate。

### 12.3 pipeline 路径 typography 结论（t255 更正）

- `scan2pdf` 实际会向 `verify_typography` 传 `--lines`；此时 **pipeline 路径 typography = FAIL**（wz4 render 6；ghbq p97 hard 等），但 **geometry gate verdict 不变**（report-only）。
- **exit=0 仅指“无源行模式”**（只传 `--src-pdf`、不传 `--lines`，L3 多为 unknown/warn）；带 `--lines` 的真实 pipeline 模式为 FAIL/exit=1。
- M1 为诊断级：默认关闭；`TYPOGRAPHY_M1=1` 输出 `diagnostics.M1`，不计入 violations/hard；`layers.L1` 只列 M2/M5。
