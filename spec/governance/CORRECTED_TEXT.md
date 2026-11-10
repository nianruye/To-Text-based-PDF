# CORRECTED_TEXT.md — 每书文本校正表契约（v1）

> **状态**：implemented（t203：`src/tools/corrected_text.py::apply_corrected_text` + scan2pdf `--corrected-text`/默认 data/<book>；report 审计；ghbq p3 验收）
> **类型**：governance（横排 geom/classic 共享；不改变 OCR/坐标算法）
> **依据**：`docs/ghbq_adapt_tasks.md` D1（封面/艺术字人工校正）、`docs/ghbq_adapt_findings.md` A4（p3「马尔巴乔夫」→「戈尔巴乔夫」）、`docs/scan2pdf_review.md` t201 残留 R2
> **纪律**：书无关；数据按 `<book>` 定位；无校正文件零回归；不 commit

---

## 0. 目的与非目标

### 0.1 目的

OCR 对扫描书封面、艺术字、书名页、特殊字形常会读错（如 ghbq p3 标题「马尔巴乔夫」应为「戈尔巴乔夫」）。这类错误**无法靠坐标/字体/规则修复**，必须人工校正文本。

本 spec 定义系统级能力：

1. 每书一份 JSON 校正表（page_key + line_index → 整行文本）；
2. 在 OCR lines 加载后、构建前替换对应行文本，**坐标/行数/页面结构不变**；
3. `--corrected-text PATH` CLI + 默认 `data/<book>/corrected_text.json` 自动发现；
4. report 可审计（path/sha/替换条数/跳过/警告）；
5. 无校正文件时**零回归**。

### 0.2 非目标

- 不做 OCR 自动纠错/语言模型纠错；只消费人工表。
- 不修改 coords、页数、页码、图块、字体/字号、行距、gate 判据。
- 不支持插入/删除行、合并/拆分页、整页替换；行数必须不变。
- 不把书目写进代码；数据文件路径由 `--book` 参数拼接。
- 不改变已交付的默认构建（无文件/无 flag 时）。

---

## 1. 文件位置与 CLI

### 1.1 默认路径

```
data/<book>/corrected_text.json
```

- `<book>` = scan2pdf `--book` 参数；代码只做 `os.path.join('data', book, 'corrected_text.json')`，**不得**含 `if book == ...`。
- 默认路径存在 → 自动启用，report `source=book_data`。
- 默认路径不存在 → `enabled=false`，不产生任何文本替换。

### 1.2 显式 CLI

```
scan2pdf.py ... --corrected-text PATH
```

- 显式路径优先于默认路径；report `source=explicit`。
- 相对路径按当前工作目录解析；绝对路径直接用。
- `PATH` 不存在/不可读/JSON 解析失败 → **usage error（exit 2）**，不得静默忽略。
- 默认路径存在但 JSON 解析失败/根结构非法 → **data error（exit 2）**；不得静默跳过（避免“以为校正了”）。
- 未知 page/line 索引、单条 value 非法 → **warn 跳过**（不 fail）；详见 §4。

### 1.3 传递位置

- 校正应用在 `scan2pdf` 的 lines 加载之后、`slice_inputs()`/构建之前；把**校正后的 lines JSON**（临时文件）传给 build 与 verify。
- `build_geom.py`/`build_classic.py` 不新增必选参数；直接构建用户需自行传入已校正的 lines（本 spec 的 CLI 入口是 scan2pdf）。
- 不修改原 `coords`/`lines` 源文件；临时 patched lines 在本次构建临时目录内。

---

## 2. JSON schema

### 2.1 根结构

```json
{
  "_comment": "ghbq p3 封面 OCR 校正（示例）",
  "2": {
    "0": "戈尔巴乔夫与",
    "1": "“人道的民主的社会主义”"
  }
}
```

- 根必须是 **object**。
- 可选 `_comment`：string 或 string 数组；仅审计，不参与替换。
- 其余 key 必须是 **page_key（0-based 的十进制字符串）**；value 必须是 object。
- 任何以 `_` 开头的 key 保留给元数据（如 `_comment`），不得当作页。

### 2.2 page/line key

- `page_key`：**0-based**，与 OCR lines/coords 的全局页 key 一致（`lines['0']` 是源第 1 页）。
- `line_index`：**0-based**，等于 `lines[page_key]` 数组下标，与 `coords[page_key][line_index]` 一一对应。
- key 必须是十进制整数字符串；`"02"` 与 `"2"` 视为不同（实现可用 `int` 归一，但必须在 report 记录；建议 canonical 写 `"2"`）。
- 不允许用 1-based 页码/行号；文档/示例必须明确 0-based。

### 2.3 value

- 必须是 **string**，表示**替换后的整行文本**（不是 diff/片段）。
- 不得为空串或纯空白（空行无法保持“行文本”语义；要删字请写空字符串以外的显式校正，行数仍不变）。
- 允许保留原有空格/全半角/引号；按原样写入 lines，构建按当前转义规则渲染。
- 不新增/删除换行；一行仍是一行（行数不变）。
- 同一 page/line 只应用一次，不做级联/二次校正。

### 2.4 行数不变（硬约束）

对每个被校正页：

```
len(patched_lines[page_key]) == len(original_lines[page_key])
```

- 表只替换已有下标的值，不能 append/remove。
- 实现必须在应用后断言；行数变化 → **data error（exit 2）**，不得继续构建。

---

## 3. 应用时机、优先级与数据流

### 3.1 时机

```
source PDF
  → OCR (layout/spotting) 或 --data-dir
  → coords/lines 加载
  → [corrected_text 加载 + 校验 + 替换 lines]
  → 可选 --pages 切片（先校正后切片；page/line 仍按全局 0-based）
  → build_geom / build_classic
  → verify_geom / gate
```

- 校正发生在 **lines 加载后、构建前**；build 看到的就是校正后的文本。
- `coords`、源 PDF 页数、`lines` 页数/行数、页码表、layJSON 均不变。
- `--pages` 子集：先对完整 lines 应用校正，再按全局 `page_key` 切片；不得对切片后的局部行号重新编号。

### 3.2 优先级

```
corrected_text > OCR lines 原文
```

- 校正后的整行替换 OCR 行；build 的换行/标题/字号/行距逻辑只消费该行文本，不改其坐标。
- 若同一行同时存在 OCR 文本、missing-char 修复、`--fix` 规则：**校正文本是行文本的最终值**；坐标/行数仍由 OCR/coords 决定，missing-char 只在未校正行生效（避免二次插入改变字符数）。
- 被校正文本必须进入 PDF 可搜索文本层；不得只改视觉/图片。
- 不改变 `coords` 与行 bbox；行对齐仍按原坐标。

### 3.3 报告

`<out>.report.json` 顶层增加：

```json
"corrected_text": {
  "enabled": true,
  "path": "data/<book>/corrected_text.json",
  "source": "explicit|book_data",
  "sha256": "<file sha256>",
  "pages": ["2"],
  "replaced": 2,
  "skipped": 0,
  "warnings": [],
  "line_counts": {"2": {"before": 2, "after": 2}}
}
```

- 无文件/无 flag：
```json
"corrected_text": {"enabled": false, "path": null, "source": "disabled", "replaced": 0, "skipped": 0}
```
- `sha256`：校正文件内容 hash（不是 patched lines hash）。
- `replaced`：实际替换的行数；`skipped`：未知页/行/非法 value 的跳过数。
- `warnings`：数组，元素含 `code`（`unknown_page`/`unknown_line`/`invalid_page`/`invalid_line`/`invalid_value`/`newline_in_value`）、`page`、`line`（可空）、`message`。
- 同一 warnings 同步写 stderr（用户可见）；未知项不 fail。
- `line_counts` 只记录被校正页，证明行数未变。

---

## 4. 校验与错误策略

### 4.1 文件级

| 情形 | 行为 |
|---|---|
| 显式 PATH 不存在/不可读 | usage error（exit 2） |
| 默认路径不存在 | `enabled=false`，继续构建 |
| JSON 语法错误（显式或默认存在） | data/usage error（exit 2）；不构建 |
| 根不是 object | data error（exit 2） |
| 某页 value 不是 object | warn `invalid_page`，跳过该页，继续 |
| 某 line value 不是 string/空/纯空白 | warn `invalid_value`，跳过该条，继续 |
| value 含 `\n`/`\r` | warn `newline_in_value`，跳过该条，继续（行数不变） |
| page_key 非十进制/负数 | warn `invalid_page`，跳过 |
| line_index 非十进制/负数 | warn `invalid_line`，跳过 |
| 行数变化（实现后断言） | data error（exit 2；**不写 warning 码**） |

### 4.2 未知页/行（不 fail）

- `page_key` 不在 OCR lines 中 → warn `unknown_page`，跳过。
- `line_index` 超出该页 `len(lines[page_key])` → warn `unknown_line`，跳过。
- OCR 数据更新导致页/行漂移时，校正表可保留旧项；构建继续，report 明确 skipped。
- 不得因未知项删除/插入行，也不得把校正平移到其他页。

### 4.3 幂等与审计

- 同一输入 + 同一校正表重复构建 → 结果文本/坐标/页数一致。
- 校正文件 sha 改变 → report sha 改变；不缓存旧的 patched lines。
- 报告必须能在不打开 PDF 的情况下回答：用了哪个文件、多少条生效、哪些跳过。

---

## 5. 零回归

对“无 `--corrected-text` 且默认路径不存在”的构建：

1. `.tex`/PDF 文本/字符/页数/bbox/pitch/gate 与基线**逐字节或等价**不变；
2. coords/lines 源文件不被改写；
3. 不产生 patched lines 临时文件（或产生但不被消费也不影响输出）；
4. report 可新增 `corrected_text.enabled=false` 字段（元数据，不属于 PDF 输出）。

必须用现有基线（ghbq 104 / wz4 677 / wz2 6）验证 0 diff；无校正文件不得触发“文本替换”路径。

---

## 6. 书无关

- 代码不得含 `ghbq`/`wz4`/任何书名/页号/行号常量。
- 默认路径只由 `book` 参数拼接；显式路径由用户给。
- 校正表是数据，不是代码；新书只需放 `data/<book>/corrected_text.json`。
- 不把书专属校正写进 `build_geom.py`/`build_classic.py`/`scan2pdf.py`。
- 参考书（ghbq）只用于验收样例，不作为代码判据。

---

## 7. 可执行验收（实现任务用）

### 7.1 ghbq 样例

校正文件（示例，数据文件由实现任务创建）：

```json
{
  "_comment": "ghbq p3 封面 OCR 校正",
  "2": {
    "0": "戈尔巴乔夫与",
    "1": "“人道的民主的社会主义”"
  }
}
```

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/ghbq_ct.pdf --data-dir output/ghbq_full/_ocr_ghbq \
  --skip-ocr --force --corrected-text data/ghbq/corrected_text.json
```

验收：

| # | 检查 | 通过条件 |
|---|---|---|
| 1 | 文本层 | `get_text` 含「戈尔巴乔夫与」、不含「马尔巴乔夫与」；p3 可搜 |
| 2 | 坐标/结构 | coords 文件 sha 不变；页数 104=104；行数 1:1；bbox/行数不变 |
| 3 | 字符/门禁 | 字符数按替换前后可解释（同长度替换不变；不同长度差值=替换差）；GMPG=0；gate PASS 96.8% |
| 4 | report | `corrected_text.enabled=true`、path/sha、replaced=2、skipped=0 |
| 5 | 未知项 | 构造 `"999":{"0":"x"}`、`"2":{"999":"x"}` → warn skip、exit 0、无文本变化 |
| 6 | 无文件 | 同书不传 `--corrected-text`、无默认文件 → 与基线逐页文本 0 diff、页数/gate 不变 |
| 7 | 默认路径 | `data/<book>/corrected_text.json` 存在时自动启用，report `source=book_data` |
| 8 | 行数 | 表不能 append/remove；实现断言行数；违反 → exit 2 |

### 7.2 单测（实现任务）

- schema 解析：`_comment`/page/line/整行/空串/非数字 key。
- 应用：临时 lines 3 行，替换 1 行 → 文本变、coords 不变、行数不变。
- 未知 page/line：warn skip、exit 0、report skipped。
- 行数变化：拒绝 exit 2。
- 零回归：无文件时 lines/tex 相同。
- 书无关：`grep ghbq/wz4` 代码 0 命中。

---

## 8. 参考基线（只作验收样例）

- ghbq key2（源 p3）OCR lines：`['马尔巴乔夫与','一人道的民主的社会主义”']`；校正为 `戈尔巴乔夫与` / `“人道的民主的社会主义”`。
- 该页当前整页源图已覆盖视觉（t199）；本契约只修**文本层**，不改图/坐标。
- 仅作样例；判据不含书/页/行常量，代码不得读取该段。

---

## 9. 实现边界与 DoD（后续）

### 9.1 实现拆分

1. `scan2pdf`：`--corrected-text` argparse、默认路径解析、JSON 校验、patched lines 临时文件、report。
2. 工具函数（可放 `scan2pdf` 或共享小模块）：`load_corrected_text()`、`apply_corrected_text(lines, table)`。
3. build/verify 消费 patched lines（不新增 build 必选参数）。
4. 文档：`docs/scan2pdf_v1.md` 新章节 + `AGENTS.md` issue 登记。
5. 单测/E2E 按 §7。

### 9.2 本任务 DoD

- 只新增 `spec/governance/CORRECTED_TEXT.md`；
- 未改 `scan2pdf.py`/`build_geom.py`/数据/产物；未 commit；未调 API。

---

## 10. 书无关自检

| 检查 | 结果 |
|---|---|
| 判据不含书目 | ✓ 仅 schema/路径/索引规则 |
| 数据按 book 定位 | ✓ `data/<book>/corrected_text.json` / `--corrected-text` |
| 无文件零回归 | ✓ §5 |
| 行数不变 | ✓ §2.4/§4.1 |
| 坐标不变 | ✓ §3.1/§3.2 |
| 优先级 | ✓ corrected > OCR；不级联 |
| 审计 | ✓ path/sha/replaced/skipped/warnings |
| 未知项不 fail | ✓ §4.2 |
| 参考书不入代码 | ✓ ghbq 只在 §7/§8 |


---

## 9. 实现锚点（t203）

| 项 | 位置 |
|---|---|
| 应用函数 | `src/tools/corrected_text.py::apply_corrected_text(lines, path, source=...)` → `(patched_lines, stats)` |
| stats | enabled/path/source/sha256/pages/applied/skipped/warnings/line_counts |
| CLI | `src/tools/scan2pdf.py --corrected-text PATH`；缺省 `data/<book>/corrected_text.json` 存在自动用（source=book_data） |
| 应用时机 | lines 加载后、`--pages` 切片前；patched lines 写 `<out 目录>/_scan2pdf_<book>/lines_corrected.json`，进入 build/verify |
| 审计 | report `corrected_text{...}`；resume 键使用 patched lines sha（`data.lines_sha256_original` 保留原值） |
| 错误 | 显式路径缺失 / 坏 JSON / 根非 object / 行数变化 → exit 2；未知页/行/非法 value → warn 跳过 |
| 零回归 | 无文件：`enabled=false`、lines 原样、渲染/门禁/字符不变 |
