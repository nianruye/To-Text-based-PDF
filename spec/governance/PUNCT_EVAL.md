# PUNCT_EVAL.md — 标点/结构识别能力评测契约（v1.3）

> **状态**：planned（本文件只定义契约；评测器/gold 实现与标定在 t111 及后续）
> **类型**：governance（跨书、跨管线公共评测契约）
> **依据**：[PUNCTUATION.md](PUNCTUATION.md)（GB/T 15834—2011 可执行规则表，v2.1）、[PIPELINE_BEHAVIOR.md](PIPELINE_BEHAVIOR.md)
> **关联实现（后续）**：`src/tools/punct_eval.py`、`data/punct_eval/`（gold 数据，代码/判据/数据分离）
> **版本**：v1.3（2026-11-08；t138 新增评测口径 B）—— v1.1 = GB/T 16 类映射 + 竖/横形态 + 多段引文；v1.2 = 20 页最小集 + 可选 dash 2 页专项扩展；v1.3 = 阅读序标点序列（无坐标）作为能力主指标，A 口径保留为 provisional
> **v1.3 修订原因**：用户选择「阅读序标点序列」方案（口径 B）；字格级 A 因 OCR 文本定字格与源书错位（92.9% 到不了）只作 provisional；B 以产物阅读序文本 + gold 转录文本对齐，不依赖 gold 字格坐标
> **变更边界**：只改本 spec；不改产品代码、数据、渲染行为；不含书/页白名单；阈值不是书的参数

---

## 0. 目的、边界与不可违背项

### 0.1 目的

`verify_vert` 只测页数/字符量/越界，测不出**标点与结构识别能力**；抽样交付验收不可累积、不可比较。
本 spec 定义一套**书无关**、可重复、可比较的标点/结构评测：

1. 以 GB/T 15834—2011 的 16 个标点类为全集，逐类给出评测映射（in-scope / out-of-scope / 扩展类）；
2. 统一 gold 数据格式（判据、数据、代码分离）；
3. 统一指标、位置容差、三档阈值与跨书门禁；
4. 明确 v1.1 评测范围：in-scope 的句读/引号/括号/破折号/省略号/书名号 + 既有 ring 扩展；
5. 把多段引文（PUNCTUATION §4.8.3.5）写入评测口径，避免把合法的跨段开引号判成漏检。

### 0.2 边界（不做的事）

1. **不评价 GB/T 禁则本身**；避头尾/配对审计属于 [PUNCTUATION.md](PUNCTUATION.md) + `punct_audit.py`。
2. **不以国标重排**；本项目按源书还原，源书自身形态是 A 类事实，不作为缺陷。
3. **v1.1 不评段落边界**；段落边界是 v2 扩展类。
4. **v1.1 不接自动修复**；只输出指标、三档结论与门禁；自动落库由后续流水线消费。
5. **不含任何书/页白名单**；所有页面来自 gold 数据；评测器不得写具体书页号/硬编码页面集合。
6. **阈值不是书的参数**；初始阈值仅为经验起点，必须经 t111 跨书标定后版本化；不得把某本书的最优值当通用值。
7. **源图形态优先**；源书使用旧式/混用形态（如「」与﹁﹂、〈〉与︿﹀）必须被接受，不得因“非国标形态”判错。

### 0.3 判据/数据/代码分离

| 层 | 放什么 | 不放什么 |
|---|---|---|
| 判据（spec / evaluator 常量） | 类别枚举、匹配规则、容差、阈值公式、form 归一化 | 某本书页号/某页标点清单/某页 crop |
| 数据（gold/dataset） | page/column/char_pos/class/value/form/bbox/crop/evidence、split | 把页面写进 evaluator |
| 代码（`punct_eval.py`） | 读取、匹配、统计、输出、门禁比较 | 书专属阈值、页面白名单、人工结论 |

---

## 1. 术语与坐标口径

### 1.1 逻辑单位

- **page**：1-based 源页；gold 与产物按页序 1:1 对齐（沿用 `verify_vert` 口径）。
- **column**：竖排的列 / 横排的行；统一称 **logical column**。
- **axis**：`vertical`（竖排，文本沿 y 推进、列右起）/`horizontal`（横排，文本沿 x 推进、行下移）。
- **char_pos**：该 logical column 内 **0-based 字符位置**（不含空白）。
- **cell**：该字符在源图/产物中的字格；`coords/lines` 的 bbox + 文本长度推导：
  - 竖排 `step_y=(y1-y0)/nchar`，`step_x` 用列宽；横排 `step_x=(x1-x0)/nchar`，`step_y` 用行高；
  - 无法推导 → 同页同轴 median step；仍不可得 → bbox fallback（§1.2）。

### 1.2 位置容差（硬口径）

位置匹配必须同时满足：

1. 同 `page`、同 `column`、同 class group；
2. **字格中心归一化距离**：`dx=|cx-gx|/step_x`，`dy=|cy-gy|/step_y`；
   **`dx ≤ 0.5` 且 `dy ≤ 0.5`（±0.5 格）**；横排/竖排同口径；
3. 无可靠 step：bbox 中心距 ≤ 0.5×估计格距，且 **bbox IoU ≥ 0.5**；不可得 → `position_unscorable`，进 manual，不硬判 FP/FN；
4. 一对一匹配；最近优先；同距按 page/column/char_pos/class 稳定排序；跨页/跨列不匹配。

> 位置容差是**字格**容差，不是页级容忍。页边界 carry/多段引文由 gold 显式标，不能因页边界自动放宽位置。

---

## 2. GB/T 16 类 → 评测类映射

### 2.1 映射表（16 个 GB/T 标点类）

> 本表按 GB/T 16 个标点类（点号 7 + 标号 9）列。PUNCTUATION §1 另列**分隔号**一行；
> 本 spec 将其作为 §2.4 的**扩展行**（不混入 16 类计数），见下。

| # | GB/T 类别 | 横排形式（含源书混用） | 竖排形式 | 评测类 | v1.1 范围 | 理由 |
|---|---|---|---|---|---|---|
| 1 | 句号 | 。（旧式 ．） | 同形 | `period` | **in-scope** | 单字符、位置+值可评；句读基础 |
| 2 | 问号 | ？ | 同形 | `question` | **in-scope** | 同上 |
| 3 | 叹号 | ！ | 同形 | `exclamation` | **in-scope** | 同上 |
| 4 | 逗号 | ， | 同形 | `comma` | **in-scope** | 同上 |
| 5 | 顿号 | 、 | 同形 | `enumeration_comma` | **in-scope** | 同上 |
| 6 | 分号 | ； | 同形 | `semicolon` | **in-scope** | 同上 |
| 7 | 冒号 | ： | 同形 | `colon` | **in-scope** | 同上 |
| 8 | 引号（双/单） | “ ” ‘ ’；源书「」『』 | ﹃﹄﹁﹂ | `quote_open` / `quote_close` | **in-scope** | 方向/配对可评；横竖混用均认 |
| 9 | 括号（圆/方/六角/方头） | （）〔〕【】［］ | ︵︶︹︺ | `bracket_present` / `bracket_type` | **in-scope** | presence 与类型分开；源书竖笔/OCR 可判 |
| 10 | 破折号 | ——（两字） | 同形（竖线由渲染规则） | `dash` | **in-scope** | 位置+长度可评；与连接号分开 |
| 11 | 省略号 | ……（六点） | 同形 | `ellipsis` | **in-scope** | 位置+长度可评；与句读同列 |
| 12 | 书名号（双/单） | 《》〈〉 | ︽︾︿﹀ | `booktitle_open` / `booktitle_close` | **in-scope** | 方向/配对+类型可评；与引号分开 |
| 13 | 连接号 | - / — / ~ | 同形 | `connector` | **out-of-scope（v2）** | 与破折号/一字线同形歧义；仅靠文本/单一墨线难判，v2 需上下文+源图规则 |
| 14 | 间隔号 | · | 同形 | `interpunct` | **out-of-scope（v2）** | 微小标记，OCR/文本层常丢失；需高分辨率源墨判据 |
| 15 | 着重号 | 字下点 | 字右点 | `emphasis_dot` | **out-of-scope（不评）** | 非字符标记，PDF 文本层无独立字符；需墨迹版式层，属于 v2/版面保真 |
| 16 | 专名号 | 字下直线 | 字左直线 | `proper_name_line` | **out-of-scope（不评）** | 非字符标记（线段），文本层不可检索；属于 v2/版面保真 |

**in-scope 统计**：12 个 GB/T 类（1–12）；**out-of-scope**：4 个 GB/T 类（13–16，v2 或明确不评）。
另有 **ring** 扩展类（非 GB/T）保留在 v1.1；**paragraph_boundary** 扩展类 v2（§2.4）。

### 2.2 类与值枚举（v1.1）

| class | 中文 | value（示例） | 备注 |
|---|---|---|---|
| `period` | 句号 | `。` | 竖/横同值 |
| `question` | 问号 | `？` | 同上 |
| `exclamation` | 叹号 | `！` | 同上 |
| `comma` | 逗号 | `，` | 同上 |
| `enumeration_comma` | 顿号 | `、` | 同上 |
| `semicolon` | 分号 | `；` | 同上 |
| `colon` | 冒号 | `：` | 同上 |
| `quote_open` | 引号开 | `「`/`『`/`﹁`/`﹃`/`“`/`‘` | 按 `form` 记录实际形 |
| `quote_close` | 引号闭 | `」`/`』`/`﹂`/`﹄`/`”`/`’` | 同上 |
| `bracket_present` | 括号有 | `true` | 只判有无 |
| `bracket_type` | 括号类型 | `（）`/`〔〕`/`︵︶`/`︹︺`/`【】`/`［］` | 扩展类型须版本化 |
| `dash` | 破折号 | `——`/`—` | 长度单列 |
| `ellipsis` | 省略号 | `……`/`…` | 长度单列 |
| `booktitle_open` | 书名开 | `《`/`〈`/`︽`/`︿` | 与引号分开 |
| `booktitle_close` | 书名闭 | `》`/`〉`/`︾`/`﹀` | 同上 |
| `connector` | 连接号 | `-`/`—`/`~` | out-of-scope（v2） |
| `interpunct` | 间隔号 | `·` | out-of-scope（v2） |
| `emphasis_dot` | 着重号 | `true`（字下/字右点） | 不评（非字符） |
| `proper_name_line` | 专名号 | `true`（字下/字左线） | 不评（非字符） |
| `separator` | 分隔号（PUNCTUATION 补充） | `/`/`／` | out-of-scope 扩展 |
| `ring` | 圈码（**扩展，非 GB/T**） | `①`… / `number` | v1.1 保留 |
| `paragraph_boundary` | 段落边界（**扩展，v2**） | `before_char`/`after_char` | v1.1 不计分 |

- 句读类 value 必须**逐类精确匹配**；`。` 与 `．` 不互认（源书旧式按 gold value 记，评测器不重排）。
- `quote_open/close`、`booktitle_open/close` 必须方向正确；`bracket_present/type` 的 presence 与 type 分开评。
- `dash` 与 `connector` 不混类：`——` 必为 dash；单 `—` 在 v1.1 不评（connector/dash 歧义，见 §2.1 13）。
- `ellipsis` 与句读分开；省略点数量按 value/长度判，不把 `……` 当两个句号。
- **form** 是实际形态，不是类别；`form` 不改变 class/value 的正确性（§2.3）。

### 2.3 竖排 / 横排 / 混用形态覆盖

评测器**必须同时接受**下列形式；gold 的 `form` 记录源书实际形，`value` 保留实际字形：

| 类 | 横排形（含源书混用） | 竖排形 |
|---|---|---|
| 引号 | `“ ”`、`‘ ’`；源书 `「」`、`『』` | `﹃ ﹄`、`﹁ ﹂` |
| 括号 | `（）`、`〔〕`、`【】`、`［］` | `︵︶`、`︹︺` |
| 书名号 | `《》`、`〈〉` | `︽︾`、`︿﹀` |
| 破折号 | `——` | 同字符（渲染为竖线；文本层仍 `—`） |
| 省略号 | `……` | 同字符 |
| 句读 | 。？，、；： | 同字符（竖排置于字下/偏右，文本层同） |

- **form 枚举**：`horizontal` / `vertical`；混用源书按实际字符记录（如竖排书用 `「」` 时 `form=horizontal`，`form_source=source_mixed` 为可选诊断字段）。
- **form 不罚**：同一 `class/value` 下，横排形 vs 竖排形不互判错；form 差异只计入 **form_accuracy** 诊断（非 auto 门禁），
  因为源书/OCR 实际混用是事实；**方向/配对错误**才计错。
- **括号/书名号形态归一化**：`（）` 与 `︵︶` 为同类型不同 form；`《》` 与 `︽︾` 同理；类型正确但 form 不同 → TP，
  form_accuracy 记一次差异；不得把 source 的横排混用判为 type error。
- **句读**：竖排/横排同字符；无 form 差异。
- **省略号/破折号**：竖排同字符；长度按沿文本轴 bbox 计算，form 只影响轴。

### 2.4 扩展类（非 GB/T 16 类）

| class | 来源 | 位置 | v1.1 |
|---|---|---|---|
| `ring` | 圈码（非 GB/T 标点） | 数字/序号位置 | **extension-in-scope**：保留 v1.0 的 ring 指标（position/value）；不属于 GB/T 16 类 |
| `paragraph_boundary` | 段落/诗/角色边界（非标点） | 边界前后 char_pos | **extension-v2**：v1.3 不评分；schema 预留 |
| `separator` | PUNCTUATION §1 补充行（分隔号） | 字符位置 | **out-of-scope（v2）**：`/` 与路径/合文歧义，需上下文 |

- **明确定位**：ring、paragraph_boundary 是“结构/版面扩展类”，**不是 GB/T 标点**；不得混入 GB/T 16 类计数。
- **v1.1 in-scope 总量**：12 GB/T 类 + ring 扩展 = 13 个评测类组；out-of-scope 4 GB/T 类 + separator；paragraph v2。

### 2.5 多段引文口径（PUNCTUATION §4.8.3.5）

独立成段引文：

- 只有一段：段首、段尾都有引号；
- 不止一段：**每段开头用开引号，只在最后一段末尾用闭引号**。

评测口径：

1. gold 用 `quote_group_id` 把跨段引号组关联；字段 `paragraph_index`、`paragraph_count`、`is_final_paragraph` 可标。
2. 非最后一段的 `quote_open` **没有闭号不是 FN**；它是合法 carry。只有**最后一段缺闭号**才计 FN。
3. 非最后一段的 open 必须能在下一段开头找到同组 open（或 gold 显式 `valid_carry=true`）；否则按未配对/结构异常登记。
4. 中间段出现闭号 → 记 `unexpected_close`（FP/结构错误），除非 gold 显式注明源书事实。
5. `pair_precision/recall` 只在组级统计：组内最后闭号正确且中间结构合法 → 组配对成功；不按“每段必须闭合”硬判。
6. 新增诊断指标 `multi_para_validity = 合法多段组 / 多段组总数`；不得用单段配对规则覆盖多段。

---

## 3. 指标定义

### 3.1 匹配与混淆

对每个 split、class group：

- `TP`：gold 与 prediction 位置匹配且 class/value（及方向/类型/值）一致；
- `FP`：prediction 未匹配到 gold（位置/类/值/方向/配对/重复预测错）；
- `FN`：gold 未匹配到 prediction（漏检）；
- 位置错但类型正确仍计 FP+FN；错误保留 `gold_id`/`pred_span`/`reason`。

### 3.2 通用位置指标

```
position_precision = TP / (TP + FP)
position_recall    = TP / (TP + FN)
false_insertion_rate = FP / (TP + FP)
miss_rate            = FN / (TP + FN)
```

### 3.3 句读类（7 类）

- 逐类 `period/question/exclamation/comma/enumeration_comma/semicolon/colon` 报 position P/R；
- `value_accuracy = 值正确 / TP`（防止把 `，` 预测成 `、` 等）；
- 竖/横同值；`form` 不参与判错（§2.3）。

### 3.4 引号（含多段）

- 方向正确：匹配的 `quote_open` 是开号、`quote_close` 是闭号；
  `direction_accuracy = 方向正确匹配 / 匹配引号`。
- 单段配对：`pair_precision/recall/F1`。
- 多段：按 §2.5 组级统计；非最后段缺闭号**不计 FN**；最后段缺闭号计 FN；`multi_para_validity` 单列。
- `form_accuracy` 只诊断，不进 auto 门禁。

### 3.5 括号 / 破折号 / 省略号 / 书名号

- 括号：`bracket_present` P/R；`bracket_type` 在 gold-present 匹配位置上的 `type_accuracy` + 混淆矩阵（圆/方/六角/方头/竖形）。
- 破折号：position P/R + `length_median_error`/`length_p95_error`（沿轴长度/step）。
- 省略号：position P/R + 长度误差；`……`/`…` 按 gold value/长度；不与句号混类。
- 书名号：`booktitle_open/close` 方向 + pair P/R/F1；类型（《》/〈〉/︽︾/︿﹀）按 gold form 记录；
  form 不同不罚（§2.3）。

### 3.6 扩展/out-of-scope

- ring：position P/R + value_accuracy（①/1 归一化）；不作为 GB/T 总分的一部分。
- paragraph_boundary：v2 的 boundary P/R/F1（±1 char），v1.1 不计。
- out-of-scope（connector/interpunct/emphasis_dot/proper_name_line/separator）：不进入 v1.3 分数；
  评测器输出 `not_scored` 与原因，不得用 0 分伪装“通过”。

### 3.7 聚合

- 每 split 输出 `overall`（GB/T in-scope class macro）+ `per_class` + `per_page` + `extension`；
- 跨书门禁用 **worst-split**（§5），不用总体均值掩盖某本书退化；
- 固定 4 位小数；JSON/CSV 同值；固定排序（split,class,page）。

---

## 4. Gold 数据格式（JSON）

### 4.1 顶层

```json
{
  "schema_version": "punct-eval-v1.2",
  "dataset": {
    "id": "punct-eval-v1.2-22p",
    "description": "20-page mixed benchmark; pages are data, not evaluator whitelist",
    "split": "wz6|wz7|heldout|mixed",
    "splits": {"wz6": 8, "wz7": 8, "heldout": 4, "extension": 2},
    "book_class": "has_frame|no_frame|heldout|mixed",
    "source_sha256": "<source pdf sha256>",
    "page_count": 22,
    "frozen": true,
    "gold_version": "2026-11-08.3",
    "notes": {
      "page_composition": {
        "base": {"wz6": 8, "wz7": 8, "heldout": 4},
        "extension": {"dash": 2},
        "base_total": 20,
        "extension_total": 2,
        "total": 22
      },
      "extension_reason": "t131: dash coverage needs 2 extra pages; same gold batch, separate extension stratum",
      "heldout_sealed": true
    }
  },
  "items": [ ... ]
}
```

- `page` 由数据提供；评测器不得有页面白名单。
- `split`/`book_class` 只是数据分组；不得把 `wz6/wz7` 书名写进阈值/判据。
- `frozen=true` 的 gold 不用于调阈值；t111 calibration 与 heldout 密封分离。

### 4.2 Item 字段（必填/选填）

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `id` | ✓ | string | 稳定唯一 ID |
| `split` | 选 | enum | `wz6`/`wz7`/`heldout`/`extension`；`dataset.split=mixed` 时**必填**（逐 item 分组） |
| `role` | 选 | enum | `base`/`extension`；22 页混合批必填；extension 页只进扩展层 |
| `extension_axis` | 选 | string | 扩展页专项轴（如 `dash`）；仅 `role=extension` 使用 |
| `page` | ✓ | int | 1-based 源页 |
| `column` | ✓ | int/string | 逻辑列/行 |
| `char_pos` | ✓ | int | 0-based 列内字符位置 |
| `class` | ✓ | enum | §2.2（含 out-of-scope/extension） |
| `value` | ✓ | string/bool/int | §2.2；`bracket_present` 用 `true`；ring 可用 `number` |
| `form` | ✓ | enum | `horizontal` / `vertical`；源书混用按实际形记（见 §2.3/§4.4） |
| `axis` | ✓ | enum | `vertical` / `horizontal`（文本流轴） |
| `bbox` | ✓ | [x0,y0,x1,y1] | 页面坐标 PDF pt |
| `crop` | ✓ | string | 证据裁片相对路径；source_ink/manual 必填 |
| `evidence` | ✓ | object | 见 §4.3 |
| `pair_id` | 选 | string | 引号/括号/书名号配对 ID |
| `quote_group_id` | 选 | string | 多段引文组 ID（§2.5） |
| `paragraph_index` | 选 | int | 多段引文段序（0-based） |
| `paragraph_count` | 选 | int | 多段引文总段数 |
| `is_final_paragraph` | 选 | bool | 是否最后一段（闭号只在此段） |
| `cell` | 选 | [cx,cy,step_x,step_y] | 字格中心/步进 |
| `length_pt` | 选 | float | 破折号/省略号沿轴长度 |
| `number` | 选 | int | 圈码数值 |
| `notes` | 选 | string | 人工判读/歧义；不得写书页白名单 |

> v1.0 的 `orientation` 字段由 `form` 取代；兼容读取时 `orientation=vertical_form` → `form=vertical`，
> `horizontal_form` → `form=horizontal`；新 gold 只写 `form`。

### 4.3 evidence 类型

| type | 何时用 | 必带 |
|---|---|---|
| `source_ink` | 源图墨迹支持（角形/竖笔/墨线/省略点/圈环） | `crop` + `ink`（尺寸/fill/臂长/长度） |
| `ocr_context` | 文本/上下文可判，源墨未逐条核 | `context`（前后 ≤16 字） |
| `pair` | 配对/多段/连续证据 | `pair_id`/`quote_group_id`/`neighbor_id` |
| `manual` | 人工判读（不可机器化） | `reviewer`（匿名）、`reason` |
| `derived` | 规则推导（不可含书页白名单） | `rule` 名称 |

### 4.4 示例（v1.0 三组，字段按 v1.1 更新）

```json
{
  "schema_version": "punct-eval-v1.2",
  "dataset": {"id": "demo", "split": "heldout", "book_class": "heldout",
    "source_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "page_count": 1, "frozen": false, "gold_version": "demo"},
  "items": [
    {
      "id": "heldout-p1-c3-q7-quote_open", "page": 1, "column": 3, "char_pos": 7,
      "class": "quote_open", "value": "﹁", "form": "vertical", "axis": "vertical",
      "bbox": [610.0, 240.0, 630.0, 260.0], "crop": "crops/demo_q7.png",
      "evidence": {"type": "source_ink", "source": "source_pdf#p1", "confidence": 0.98,
                   "ink": {"w": 20.0, "h": 9.0, "fill": 0.33}},
      "pair_id": "p1-c3-pair-a"
    },
    {
      "id": "heldout-p1-c3-q8-quote_close", "page": 1, "column": 3, "char_pos": 8,
      "class": "quote_close", "value": "﹂", "form": "vertical", "axis": "vertical",
      "bbox": [610.0, 265.0, 630.0, 285.0], "crop": "crops/demo_q8.png",
      "evidence": {"type": "pair", "source": "gold_pair", "confidence": 0.96,
                   "neighbor_id": "heldout-p1-c3-q7-quote_open"},
      "pair_id": "p1-c3-pair-a"
    },
    {
      "id": "heldout-p1-c2-q12-bracket_type", "page": 1, "column": 2, "char_pos": 12,
      "class": "bracket_type", "value": "〔〕", "form": "vertical", "axis": "vertical",
      "bbox": [820.0, 370.0, 845.0, 395.0], "crop": "crops/demo_bracket.png",
      "evidence": {"type": "source_ink", "source": "source_pdf#p1", "confidence": 0.93,
                   "ink": {"vertical_strokes": 2, "w": 24.0, "h": 60.0}},
      "pair_id": "p1-c2-curly"
    },
    {
      "id": "heldout-p1-c5-q30-dash", "page": 1, "column": 5, "char_pos": 30,
      "class": "dash", "value": "——", "form": "vertical", "axis": "vertical",
      "bbox": [300.0, 700.0, 320.0, 780.0], "crop": "crops/demo_dash.png",
      "evidence": {"type": "source_ink", "source": "source_pdf#p1", "confidence": 0.95,
                   "ink": {"length_pt": 80.0, "step_pt": 25.4}},
      "length_pt": 80.0
    }
  ]
}
```

### 4.5 新增示例（3 类：句读 / 书名号 / 省略号）

```json
{
  "schema_version": "punct-eval-v1.2",
  "dataset": {"id": "demo-v11", "split": "heldout", "book_class": "heldout",
    "source_sha256": "1111111111111111111111111111111111111111111111111111111111111111",
    "page_count": 1, "frozen": false, "gold_version": "demo-v11"},
  "items": [
    {
      "id": "demo-p1-c1-q4-comma", "page": 1, "column": 1, "char_pos": 4,
      "class": "comma", "value": "，", "form": "vertical", "axis": "vertical",
      "bbox": [700.0, 420.0, 720.0, 440.0], "crop": "crops/demo_comma.png",
      "evidence": {"type": "ocr_context", "source": "source_pdf#p1",
                   "confidence": 0.99, "context": "…一句，下一句…"}
    },
    {
      "id": "demo-p1-c2-q10-booktitle_open", "page": 1, "column": 2, "char_pos": 10,
      "class": "booktitle_open", "value": "︽", "form": "vertical", "axis": "vertical",
      "bbox": [560.0, 300.0, 580.0, 320.0], "crop": "crops/demo_booktitle.png",
      "evidence": {"type": "source_ink", "source": "source_pdf#p1",
                   "confidence": 0.97, "ink": {"w": 18.0, "h": 20.0, "fill": 0.30}},
      "pair_id": "p1-c2-booktitle-a"
    },
    {
      "id": "demo-p1-c2-q11-booktitle_close", "page": 1, "column": 2, "char_pos": 11,
      "class": "booktitle_close", "value": "︾", "form": "vertical", "axis": "vertical",
      "bbox": [560.0, 325.0, 580.0, 345.0], "crop": "crops/demo_booktitle2.png",
      "evidence": {"type": "pair", "source": "gold_pair", "confidence": 0.97,
                   "neighbor_id": "demo-p1-c2-q10-booktitle_open"},
      "pair_id": "p1-c2-booktitle-a"
    },
    {
      "id": "demo-p1-c6-q40-ellipsis", "page": 1, "column": 6, "char_pos": 40,
      "class": "ellipsis", "value": "……", "form": "vertical", "axis": "vertical",
      "bbox": [410.0, 900.0, 430.0, 955.0], "crop": "crops/demo_ellipsis.png",
      "evidence": {"type": "source_ink", "source": "source_pdf#p1",
                   "confidence": 0.94, "ink": {"length_pt": 50.0, "step_pt": 25.0}},
      "length_pt": 50.0
    }
  ]
}
```

> 示例页号/位置是格式示例，不是基准集页面白名单。
> 多段引文示例省略；字段见 §4.2 `quote_group_id/paragraph_index/paragraph_count/is_final_paragraph`。

### 4.6 基准集页数（v1.2：20 最小 + 专项扩展）

| 层 | split | book_class | 页数 | 用途 |
|---|---|---|---|---|
| base | `wz6` | `has_frame` | 8 | 有框书不退化 |
| base | `wz7` | `no_frame` | 8 | 无框书不退化 |
| base | `heldout` | `heldout` | 4（≥2 本书/风格） | 密封泛化门禁 |
| **base 小计** | | | **20** | v1 最小集；与 v1.0/v1.1 可比 |
| extension | `extension` | 随来源书 | **2**（专项 `dash`） | 补 dash 覆盖；同批 gold，不并入 base split |
| **合计** | | | **22** | 有扩展页时的 v1.2/v1.3 批 |

- **v1 最小值仍是 20 页**（8 wz6 + 8 wz7 + 4 heldout）；专项扩展页是**可选**，不是必须；
- 若某批无扩展页：`page_count=20`，`splits` 只含 base；
- 若某批带扩展页：`page_count=22`，`splits.extension=2`，`notes.page_composition` 必须登记构成与理由（§4.1）；
- 扩展页须来自**非 heldout** 页面；heldout 仍严格 4 页、密封、成员不变；扩展页不得用于调 heldout 阈值/轮换；
- **split 聚合**：base 8/8/4 的 by_split 指标与门禁只由 base 页计算；extension 2 页只进 `extension` 报告层
  （`extension_axis=dash`），**不并入 wz6/wz7/heldout 的聚合**，也不得用扩展页提升某 split 的数值；
- 扩展页可计入**总体 descriptive overall_22**（若报告需要），但该总体不得替代 base split gate；
- 每个 in-scope class 目标 ≥5 个 gold item；extension 页用于补 dash 覆盖，不改变 base 页的 `coverage_gap` 判定；
- 页面由 gold 数据给出；不列具体页号；评测器不得硬编码页面。

### 4.7 口径 B 的 gold（序列转录，无坐标）

B 不读 `gold_v1_20p` 的 item/bbox；输入是**人工转录的阅读序文本**（来自 CONTENT_EVAL 的 `content_gold`，provisional）：

```json
{
  "schema_version": "punct-eval-b-gold-v1",
  "dataset": {
    "id": "punct-eval-b-20p",
    "page_count": 20,
    "page_count_with_extension": 22,
    "source": "content_gold(t111/provisional)",
    "normalization": "content-N0",
    "axis_default": "vertical|horizontal|mixed",
    "notes": "transcription provisional; no gold cell coordinates"
  },
  "pages": [
    {
      "page": 1,
      "axis": "vertical",
      "block_order": ["v1", "v2", "h1"],
      "text": "……含标点的阅读序转录……",
      "exclude": [
        {"type": "header", "text": "金瓶梅"},
        {"type": "page_number", "text": "一四二"}
      ],
      "doubt_chars": [{"pos": 12, "char": "?", "reason": "源墨模糊"}],
      "evidence": {"type": "manual", "reviewer": "R1"}
    }
  ]
}
```

- `text` 必须按**源书阅读序**拼接（竖排右起列→列内上→下；横排上行→行内左→右）；`block_order` 只用于 `mixed` 页的块序，避免评测器猜。
- `exclude` 是数据：页眉/页脚/页码/图注；不能用具体书页白名单替代。
- B gold 与 A gold **不是同一份文件**：`gold_v1_20p`（A）带 column/char_pos/bbox；B gold 只带 page/text/axis/exclude。
- 两套 gold 必须覆盖同一页集（20 或 22）；若页集不同，A/B 对比必须显式标 `page_set_mismatch`，不得直接算差。

---

## 5. 三档阈值与跨书门禁

### 5.1 档位

| 档 | 含义 | 处置 |
|---|---|---|
| **auto** | 达到 auto 阈值；可进自动落库/自动修复候选 | 自动流水线；保留 evidence/crop |
| **manual** | 未达 auto、达 manual | 人工队列，不自动改 |
| **drop** | 未达 manual | 不修/不落库；记录原因 |

### 5.2 初始阈值（v1.2 沿用 v1.1 数值，**均为待 t111 标定的经验值**）

| class/组 | auto（全部满足） | manual（至少达到） | drop |
|---|---|---|---|
| 句读 7 类（period/question/exclamation/comma/enumeration_comma/semicolon/colon） | position P ≥ 0.98，R ≥ 0.96；value_accuracy ≥ 0.99；false insertion ≤ 0.02 | P ≥ 0.92，R ≥ 0.88；value_acc ≥ 0.95 | 其余 |
| `quote_open/close` | P ≥ 0.98，R ≥ 0.95；direction ≥ 0.98；false insertion ≤ 0.02 | P ≥ 0.90，R ≥ 0.85；direction ≥ 0.90 | 其余 |
| 引号 pair | pair P ≥ 0.97，R ≥ 0.94，F1 ≥ 0.95；multi_para_validity ≥ 0.97 | pair P ≥ 0.90，R ≥ 0.85；validity ≥ 0.90 | 其余 |
| `bracket_present` | P ≥ 0.98，R ≥ 0.95；false insertion ≤ 0.02 | P ≥ 0.90，R ≥ 0.85 | 其余 |
| `bracket_type` | type_accuracy ≥ 0.97；P ≥ 0.97，R ≥ 0.95 | type_acc ≥ 0.90；P ≥ 0.90，R ≥ 0.85 | 其余 |
| `dash` | P ≥ 0.98，R ≥ 0.95；length 中位 ≤ 0.10 step；p95 ≤ 0.20 step | P ≥ 0.90，R ≥ 0.85；中位 ≤ 0.20 step | 其余 |
| `ellipsis` | P ≥ 0.98，R ≥ 0.95；length 中位 ≤ 0.15 step | P ≥ 0.90，R ≥ 0.85；中位 ≤ 0.30 step | 其余 |
| `booktitle_open/close` | P ≥ 0.98，R ≥ 0.95；direction ≥ 0.97；pair F1 ≥ 0.95 | P ≥ 0.90，R ≥ 0.85；direction ≥ 0.90 | 其余 |
| `ring`（扩展，非 GB/T） | P ≥ 0.98，R ≥ 0.95；value_accuracy ≥ 0.98 | P ≥ 0.90，R ≥ 0.85；value_acc ≥ 0.95 | 其余 |
| `paragraph_boundary`（v2） | F1 ≥ 0.90，offset ≤1 char | F1 ≥ 0.80 | 其余 |
| out-of-scope（connector/interpunct/emphasis/proper_name/separator） | — | — | **不评/不 auto** |

> `form_accuracy` 只诊断，不进 auto；横/竖混用不是错误。
> 句读/书名号/省略号阈值沿用 v1.1 经验值；t111 用 20 页 base gold（+ 可选 2 页 dash 扩展）校准并版本化。

### 5.3 阈值来源（判据锚点，不是书的阈值）

| 类 | 来源 |
|---|---|
| 句读 | PUNCTUATION §1/§3 的 GB/T 形式表 + `punct_audit` 行/列首禁则（只作判据，不重排） |
| 引号 | `_ink_quote_corner`（8–26×4–18pt、fill 0.08–0.80、臂交角）；QSF corner；battle8/14/20 经验 |
| 括号 | bracket shape/名表/竖笔；battle20 271 条 0 落（高 precision 经验） |
| 破折号 | `_dash_ink_seg` 源墨长度/线宽/线心；1.255 step 实测 |
| 省略号 | 源墨点列/长度；无现成机器基线，初始保守 |
| 书名号 | 竖/横形态表 + 源图竖笔/角形；初始保守 |
| ring | 连通域/序列 LNDS/高分辨率读数 |
| 多段引文 | PUNCTUATION §4.8.3.5；组级合法性 |

- 以上只作 **判据来源**；不得把 wz6/wz7 的最优阈值直接写成通用值。t111 在 calibration split 拟合、
  heldout 验证后，以 **spec v1.2** 版本化阈值并附对比表。

### 5.4 跨书门禁（wz6 / wz7 / heldout）

| 档 | 数据 | 角色 |
|---|---|---|
| `wz6` | 有框书 | 有框书不退化 |
| `wz7` | 无框书 | 无框书不退化 |
| `heldout` | ≥2 本书/风格，4 页密封 | 泛化门禁，禁止调参；扩展页禁止来自 heldout |

- 每次改判据/阈值/模型，三档全部重跑；**任一档退化即拒绝**；不得用其他档提升抵消。
- **不退化**（vs frozen baseline）：
  1. worst-split 的 auto 指标下降 ≤ **0.5pp**；
  2. false insertion 上升 ≤ **0.2pp**；
  3. auto 条目数不减少；
  4. drop 条目数不增加；
  5. heldout auto 不下降；heldout 新增 FP 人工复核；
  6. 阈值变更必须附 by_split/by_class 表 + gold hash。
- 结论：`AUTO_PASS`（三档均满足，可自动候选）/ `MANUAL_ONLY`（只人工）/ `REJECT`（任一退化）。
- 三档是数据 split 标签，不是页面白名单；页面由 gold 提供。

---

## 6. 评测器接口（v1.3）

### 6.1 CLI

```bash
# 口径 A（字格位置，provisional）
/usr/bin/python3 src/tools/punct_eval.py --method A \
  --gold data/punct_eval/gold_v1_2_22p.json \
  --pdf output/wz7_full/wz7_full_v50.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --out-json /tmp/punct_eval_A.json --out-csv /tmp/punct_eval_A.csv

# 口径 B（阅读序标点序列，无 gold 坐标；主指标）
/usr/bin/python3 src/tools/punct_eval.py --method B \
  --gold data/punct_eval/punct_sequence_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v50.pdf \
  --out-json /tmp/punct_eval_B.json --out-csv /tmp/punct_eval_B.csv
```

- A 输入：gold JSON（§4）+ 产物 PDF + coords/lines；B 输入：序列 gold（§4.7）+ 产物 PDF，不需要 gold 坐标。
- 输出：`--out-json` 指标表、`--out-csv` 长表（split/class/page/metric/value）。
- `--src-pdf` 只作 evidence 诊断/裁片核对，不参与分类/匹配（防源图泄漏）。
- 退出码：0=评测完成（不等于达标）；2=schema/输入不可读；3=页/列无法对齐（manual）。
- 只读；不改 PDF/data/output；不联网；不 API。

### 6.2 支持范围

- **GB/T in-scope**：句读 7 类、引号 open/close、括号 present/type、破折号、省略号、书名号 open/close。
- **扩展**：ring（extension-in-scope）；paragraph_boundary（v2，v1.3 不评分）。
- **out-of-scope**：connector/interpunct/emphasis_dot/proper_name_line/separator；输出 `not_scored` + 原因；
  不得计 0 后宣称通过。
- **多段引文**：按 §2.5 组级统计；非最后段缺闭号不计 FN。
- **form**：horizontal/vertical/混用均接受；form_accuracy 诊断。
- **v1.3 页数**：base 20（8/8/4，§4.6）+ 可选 extension 2（dash，总22）；A/B 共用同一页集；extension 只进扩展层，不并入 base split。
- **B 口径**：`--method B` 不读 gold 坐标，按 §6.4 重建阅读序/锚点对齐；B 为 v1.3 能力主指标，A 为 provisional。
- **段落边界**：v2；schema 保留。
- **自动修复**：v1.3 不接；B 仅输出指标/诊断，不做修复。

### 6.3 输出 JSON（最小字段）

```json
{
  "schema_version": "punct-eval-v1.2",
  "dataset_id": "punct-eval-v1.2-22p",
  "gold_sha256": "...", "pdf_sha256": "...", "split": "wz7",
  "by_class": {
    "period": {"tp":0,"fp":0,"fn":0,"precision":0.0,"recall":0.0,"value_accuracy":0.0},
    "quote_open": {"precision":0.0,"recall":0.0,"direction_accuracy":0.0},
    "booktitle_close": {"precision":0.0,"recall":0.0,"pair_f1":0.0},
    "ellipsis": {"precision":0.0,"recall":0.0,"length_median_error":0.0}
  },
  "extension": {"ring": {"precision":0.0,"value_accuracy":0.0}},
  "not_scored": {"connector": "out-of-scope-v2", "emphasis_dot": "not-character-mark"},
  "gate": {"verdict": "auto|manual|drop|AUTO_PASS|MANUAL_ONLY|REJECT",
           "by_split": {"wz6":"...","wz7":"...","heldout":"..."},
           "baseline_sha256": "...", "thresholds_version": "v1.2"},
  "errors": [{"gold_id":"...","pred_span":[0,0,0,0],"reason":"position|class|value|direction|pair|duplicate|multi_para"}]
}
```

- CSV 列至少：`split,class,page,metric,value`；与 JSON 同值；稳定排序；无时间戳/随机。
- `gate` 无 baseline 只能 `unscored`，不得 auto。
- out-of-scope 必须列 `not_scored` 及版本/原因，不能隐去。

### 6.4 评测口径 B：阅读序标点序列（无坐标）

口径 B 是 v1.3 的**能力主指标**：不依赖 gold 字格坐标，直接用「产物 PDF 的阅读序文本」与「gold 转录文本」的标点序列对齐。

#### 6.4.1 输入与输出

- **输入**：产物 PDF（`--pdf`）+ B gold 转录（`--gold`，§4.7；来自 `content_gold`，provisional）；
  B **不需要** `--coords`/`--lines` 的 gold 字格；PDF 内部 span 坐标只用于重建阅读序。
- **输出**：
  - 每类标点 `TP/FP/FN`、`precision`、`recall`；
  - 类型混淆矩阵（括号圆/方/六角/方头，书名号双/单，引号单/双等）；
  - 按 page / split / overall 的序列指标；
  - 与口径 A 的逐类差值 `B - A`，以及差值 >5pp 的归因列表；
  - 阅读序不可判页、未对齐锚点、页眉/页脚剔除清单。
- **不输出**：位置 precision/recall（B 无字格位置）；位置由 A 提供。

#### 6.4.2 阅读序重建（书无关）

从产物 PDF 提取 span/line（`get_text("dict")` 的 bbox + text，必要时含 `rawdict` 字符），按页重建：

1. **排除页眉/页脚/页码/图注**
   - 优先用 gold `exclude`（`header`/`footer`/`page_number`/`caption`）的归一化文本匹配并剔除；
   - 页边带：默认上/下各 **8% 页高** 内，仅剔除「单行/短文本且匹配页面家具」的 span；band 比例是配置，不是书参数；
   - 页码：剔除页边带内符合页码正则（汉字数字/阿拉伯数字/罗马数字，长度 ≤6）的短 span；
   - 正文区内的短行/单字列**不**因短而剔除；图注只按 `exclude`/`caption` 数据剔除。
   - **不得**按具体书页白名单剔除；页面全部来自 gold。
2. **竖排页（axis=vertical）**
   - 按 span 中心 x 聚类分列；列间 gap 阈值用本页 `max(1.2×median glyph height, 0.5×median span height)` 的自适应值；
   - 列按 x **右→左**；列内按 y **上→下**；同列 y 重叠按 x 再排以稳定；
   - 标点与文字同列；标点形态（﹁/「）不改变排序。
3. **横排页（axis=horizontal）**
   - 按 y 聚类分行（行间 gap 用本页中位行高自适应）；行按 y **上→下**；
   - 行内按 x **左→右**；同一行内多 span 拼接；
   - 这是竖排规则的轴向镜像，不是按书硬编码。
4. **混用页（axis=mixed）**
   - 用 gold `block_order` 给块序（如 `["v1","v2","h1"]`）；块内按上面竖/横规则；
   - 无 `block_order` 时按 span 朝向分块（h/w 比 + 字符朝向），跨朝向块序无唯一解 → 该页标 `reading_order_unscorable`，
     不计 TP/FP/FN，列入 `errors.reading_order`，**不得**静默按 x/y 猜；
   - 竖排/横排形态混用不因 `form` 不同判错；form 只作诊断。

#### 6.4.3 对齐：文字锚点，不是标点序列硬配对

1. **归一化**：使用 CONTENT_EVAL 的 `N0`：NFC、去空白、不繁简/异体、不跨页；`?` 为 doubt 掩码，从锚点和标点中都剔除并计数。
2. **锚点序列**：从 gold/pred 的归一化文本中剔除**所有标点/符号**（GB/T 标点 + 竖排形 + 圈码；Unicode `P*` + 显式圈码），
   保留汉字/数字/拉丁作为 anchor；anchor 数量为 0 的页标 `alignment_unscorable`。
3. **锚点对齐**：用 char-level `difflib.SequenceMatcher(autojunk=False)`（或等价 DP）对 gold/pred anchor 做一对一匹配；
   `matching_blocks` 决定 anchor 映射；同分/多解按 `(page, block_start, length)` 稳定排序，保证可复现。
4. **标点落槽**：对每个标点，找它在原文中的「前 anchor / 后 anchor」；用 anchor 映射得到 gold 侧**gap key**
   `(prev_gold_anchor_id, next_gold_anchor_id)`（首/尾用哨兵）；gold 与 pred 的标点只在**同一 gap key** 内配对。
5. **槽内配对**：按原顺序，同类 + 归一化值/类型/方向一致才 TP；同类但值/类型错 → 计 FP+FN 并进混淆矩阵；
   多段引文按 §2.5 的组级规则；括号 presence 与 type 分开；书名号 open/close 按方向；省略号/破折号按 value。
6. **不齐 = FN/FP**：
   - gold 有标点、pred 无匹配 → 该类 FN；
   - pred 有标点、gold 无匹配 → 该类 FP；
   - anchor gap 映射不上（OCR 字符错/多/少）→ 该 gap 内标点全部 unaligned，gold 侧 FN、pred 侧 FP，
     错误原因 `alignment`，不强行跨 gap 配对；
   - **不得**只用标点序列做 `SequenceMatcher` 硬配对；文字锚点是唯一的槽位依据。
7. **gap 不做 ±1 容差**：B 无字格，若允许跨 gap 会把标点错位洗成 TP；跨 gap 一律 FP/FN，并在报告列 `unaligned_gap`。
8. **未对齐原因**：`transcription`（gold 转录错）/`alignment`（锚点错/OCR 字差）/`reading_order`（混用/页边）/`missed`（产物漏检）/
   `false_insert`（产物多标点）/`form`（形态差异，不判错）/`type`（类型混淆）。

#### 6.4.4 指标

- 每类：`TP/FP/FN`、`precision=TP/(TP+FP)`、`recall=TP/(TP+FN)`；`macro` 与按页/按 split 的 micro；
- **类型混淆矩阵**：括号（圆/方/六角/方头/竖形）、书名号（双/单）、引号（单/双、开/闭）；
- 引号/书名号 pair：组级 P/R（多段引文按 §2.5）；括号 presence/type 分开；
- 破折号/省略号：value 与序列位置；不评长度（长度属 A 的坐标/墨线诊断）；
- B **不报 position precision/recall**；位置类结论只能从 A 引用，且 A 为 provisional；
- 统计固定 4 位小数、固定排序；输出 JSON+CSV（`method=B_sequence`）。

#### 6.4.5 与口径 A 的关系

| 口径 | 输入 gold | 依赖 | 定位 |
|---|---|---|---|
| **A 字格位置** | `gold_v1_20p`（column/char_pos/bbox） | 字格坐标/±0.5 格 | **provisional**；OCR 定字格与源书错位时大量不可达（t131 实测 92.9% 到不了） |
| **B 阅读序序列** | `content_gold` 转录（provisional） | 只依赖阅读序 + 文字锚点 | **v1.3 能力主指标**；无坐标、可跑 |

- 两口径使用**不同 gold**：A 用 `gold_v1_20p`，B 用 `content_gold`/B gold；**不得互相替代**，也不得把 A 的坐标 gold 直接喂 B。
- 两口径结果必须**并列报告**：同页集、同归一化、同类别枚举；A/B 结果不可只报一个。
- 同一类 `|B - A| > 5pp` 时，必须列出归因：转录错 / 锚点对齐错 / 阅读序或页边剔除 / 漏检 / 多标点 / 类型混淆 / gold 页集不一致；
  不得用“B 更高”直接宣布 A 错，反之亦然。
- **阈值**：B 先复用 §5.2 的 v1.2 初始阈值为 **provisional**；A/B 均不因 provisional 自动落库；
  **正式阈值标定仍需 v2 gold**（t111/v1.4 后续），在 v2 gold 前 B 只作能力主指标与回归趋势，不启用 auto。
- B 的主指标资格来自“可跑/可比较”，不是“已证明比 A 真”；报告必须写 `provisional=true`。

#### 6.4.6 局限（必须写进报告）

1. **转录可信度**：`content_gold` 是 provisional 人工转录；gold 错会直接进 B 的 FN/FP，不能当绝对真值；
2. **对齐依赖 anchor**：OCR 多字/少字/异体/合并列会改变 gap；这些位置的标点计 unaligned，B 会低估而非乱配；
3. **阅读序**：混用页无 `block_order` 时不可评；页眉/页脚误剔或漏剔会改变序列；
4. **无位置**：B 不能发现“同类标点放错但仍在同 gap”的错位；定位仍看 A/源图；
5. **形态**：横/竖混用不罚 form，但类型混淆矩阵只按 canonical 类型；form 差异单列；
6. **阈值**：B 阈值 provisional，v2 gold 前不得把 B 分数当最终验收/自动落库依据。

#### 6.4.7 B 输出 JSON（最小字段）

```json
{
  "schema_version": "punct-eval-v1.3",
  "method": "B_sequence",
  "dataset_id": "punct-eval-b-20p",
  "gold_source": "content_gold(t111/provisional)",
  "normalization": "content-N0",
  "by_class": {
    "period": {"tp":0,"fp":0,"fn":0,"precision":0.0,"recall":0.0},
    "quote_open": {"tp":0,"fp":0,"fn":0,"precision":0.0,"recall":0.0},
    "bracket_type": {"tp":0,"fp":0,"fn":0,"precision":0.0,"recall":0.0,"confusion":{}},
    "ellipsis": {"tp":0,"fp":0,"fn":0,"precision":0.0,"recall":0.0}
  },
  "by_page": [{"page":1,"tp":0,"fp":0,"fn":0,"reading_order":"ok|unscorable|excluded"}],
  "reading_order": {"pages":0,"unscorable":0,"excluded_furniture":0},
  "ab_diff": {"by_class": {"period": 0.0}, "gt5pp": [{"class":"period","delta":0.0,"causes":["transcription|alignment|reading_order|missed|false_insert|form|type"]}]},
  "gate": {"status":"provisional", "thresholds_version":"v1.2", "auto_enabled":false},
  "errors": [{"page":1,"kind":"alignment|reading_order|missed|false_insert|type","gold_gap":"...","pred_gap":"...","detail":"..."}]
}
```

- CSV：`method,split,class,page,metric,value`；B 行 `method=B_sequence`；
- `gate.status=provisional`；无 v2 gold 时 `auto_enabled=false`；
- `ab_diff` 必须带 A/B 页集一致性；页集不一致标 `page_set_mismatch`。

---

#### 6.4.8 data_missing 诊断（输入侧判据，provisional）

B 口径下若「gold 有标点、产物文本层缺标点」，必须区分**上游 OCR 缺标点**与**产品回归**：

- 统计每页 `gold_punct`、`input_punct`（OCR lines 文本）、`product_punct`（产物 PDF 文本层）；
- `product_punct/gold_punct ≤ 0.75` 且 `input_punct/gold_punct ≤ 0.75` 且去标点 anchor 相似度中位 `≥ 0.80`
  → **`data_missing`**（上游 OCR 缺标点，不计产品回归；门禁降 MANUAL_ONLY 并注明）；
- `product_punct/gold_punct ≤ 0.75` 但 `input_punct/gold_punct > 0.75` → **`product_regression`**（输入有标点而产物缺，按产品 REJECT）；
- 三个阈值（0.75 / 0.75 / 0.80）为 **t111 标定前 provisional 值**，与 §5.2 阈值同版本登记；不得用于 auto。

## 7. 逐项判定与证据

- 每个 gold item 必须有 evidence；source_ink 必带 crop+ink；ocr_context 必带上下文；manual 必带 reviewer/reason。
- 预测/错误回链 gold_id 或 pred_span；错误原因：position/class/value/direction/pair/duplicate/multi_para。
- 未找到预测是 FN，不是 drop；drop 是阈值档位。
- 一对一匹配；同一 gold 不重复计 TP。
- 源图 crop 只作 evidence/审计，不作预测输入。
- 多段引文必须按 §2.5；不能用单段规则把合法跨段开引号判 FN。

---

## 8. 治理自检

| 检查 | 结果 |
|---|---|
| GB/T 16 类映射 | ✓ §2.1：16 行；12 in-scope + 4 out-of-scope；§2.4 分隔号扩展单列 |
| 句读/书名号/省略号 in-scope | ✓ §2.1/§3.3–3.5/§5.2；per-class P/R/value |
| 竖/横/混用形态 | ✓ §2.3：引号/括号/书名号/破折号/省略号；`form` 记录、不罚 form |
| 多段引文 | ✓ §2.5：跨段 open 不判 FN；最后段缺闭号才 FN；组级 pair |
| gold schema | ✓ §4：class/value/form/pair_id + quote_group_id/paragraph 字段 |
| 3 新增示例 | ✓ §4.5：句读/书名号/省略号 |
| 圈码/段落边界定位 | ✓ §2.4：ring=extension-in-scope，paragraph=v2 extension，非 GB/T |
| 三档/跨书门禁 | ✓ §5：auto/manual/drop；wz6/wz7/heldout；worst-split 不退化 |
| 评测器接口/v1 范围 | ✓ §6：A=gold+PDF+coords/lines；B=PDF+序列gold（无坐标）；base 20 + 可选2页 dash 扩展；12 GB/T + ring |
| B 序列口径 | ✓ §6.4：阅读序重建（x列右→左/y下→上；页眉/页脚剔除；竖横混合）、anchor 对齐、TP/FP/FN/P/R、混淆、A/B 关系 |
| A/B 并列与 >5pp 归因 | ✓ §6.4.5：A provisional、B 主指标；两 gold 不互替；差值 >5pp 列转录/对齐/阅读序/漏检/多标点/类型/gold页集原因 |
| 判据/数据分离、书无关、无页面白名单 | ✓ §0.3/§4/§8；全文无具体书页白名单；阈值非书专属 |

---

## 9. 版本与后续

| 版本 | 内容 | 状态 |
|---|---|---|
| v1.0 | 4 类 + 20 页 + 三档/三书门禁/接口 | 已存在（t110） |
| v1.1 | GB/T 16 类映射、12 in-scope、竖/横混用、多段引文、gold 扩展、3 新示例 | 已存在（t119） |
| v1.2 | 20 页最小集 + 可选 dash 2 页专项扩展（总22）；dataset.notes 登记；扩展不并入 base split/heldout | 已存在（t137） |
| **v1.3（本文件）** | 阅读序标点序列（无坐标）口径 B；B 为能力主指标，A provisional；A/B 并列；阈值仍需 v2 gold | **planned** |
| v1.4（t111） | 20/22 页 B gold/标定、阈值修订、baseline/heldout、评测器实现 | 待做 |
| v2 | paragraph_boundary、connector/interpunct/注视标记、自动修复接入 | 待做 |

**v1.3 交付边界**：本文件只改 spec；评测器/gold/阈值实测由后续任务完成。
**t111 交付物**：`gold_v1_2_22p.json`（schema §4）、`src/tools/punct_eval.py`（§6）、
`docs/punct_eval_baseline_v1.md`（阈值 v1.2 provisional / v1.3 B 口径 + 三档 baseline + heldout + 多段引文样例）。
