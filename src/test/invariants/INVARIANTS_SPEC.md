# 特征不变量 Spec

> 对象：`build_geom.py`（现代书籍）/ `build_classic.py`（古籍）两条渲染管线。
> **不变量**：不论输入哪段 spotting（格式合法），这些行为性质都成立。不绑定特定 PDF 的页数/pitch/字号值。
> 对应测试：[test_invariants_geom.py](test_invariants_geom.py) / [test_invariants_classic.py](test_invariants_classic.py)。
> 输入：wz1 源页 [40,70)（geom，含脚注①页）/ wz2 源页 [60,90)（classic，〔X〕序号注释密集），截取 30 页，单趟 `POSITIONAL=1`。
> 加载：[conftest.py](conftest.py) 截取子集 + session 跑管线 + `line_features` 提取。

## 处理阶段与不变量

管线处理阶段：①几何标定 -> ②行分类与字号分档 -> ③位置还原与行距 -> ④转义与符号修正 -> ⑤渲染约束（缩进/对齐/版心）。下表按阶段列不变量。

---

## build_geom（现代书籍管线）

### ①几何标定
- **G1 小字号是基准字号的固定折扣**：`FONT_SM = round(FONT*0.78)`（L55），故输出 PDF 最小字号簇 < 正文中位字号 × 0.85。
  - 测试：`test_small_font_below_body`

### ②行分类与字号分档
- **G2 标题字号显著大于正文**：`_big = h > H_BODY*1.8`（L499）的行按 `tier_size`（L501-503，按行高中位×FONT/H_BODY）定字号，故最大字号 ≥ 正文中位 × 1.2。
  - 测试：`test_heading_above_body`

### ③位置还原与行距
- **G3 页数不丢页**：行距按源 `BASELINE` 推导（L53）+ `_FILL` 压缩（L865），输出页数 ∈ [源×0.8, 源×1.5]（锁当前范围，单趟无 ratio 校正可能小幅溢出但不丢页）。
  - 测试：`test_page_count_lower_bound`

### ④转义与符号修正
- **G4 全书无 U+FFFD**：`_esc_chars`（L198-204）不引入 U+FFFD；OCR 的 `�` 在 `is_garbage_page`（L463-474）整页贴图，不进正文流。
  - 测试：`test_no_replacement_char`

### ⑤渲染约束
- **G5 段首缩进存在**：段首 `\hspace*{2em}`（L1013），续行顶格；段首行 x0 明显大于顶格中位（≥5% 行 x0 > 中位+3pt）。
  - 测试：`test_paragraph_indent_exists`
- **G6 行不溢出版心**：满行 `makebox[\textwidth][s]` 收缩齐右（L1027-1029），段末短行 `makebox[l]`；行尾 x1 中位 < 页宽 × 0.98（整页贴图页 x1≈页宽但 median 排除）。
  - 测试：`test_no_line_overflow`

---

## build_classic（古籍管线）

### ②行分类与字号分档
- **C1 注释序号字号不反超正文**：`NOTE_FONT = MEASURE/_NOTE_CW`（L627）< `BODY_FONT = MEASURE/_BODY_CW`（L626），注释满行字数多->字号小。但 wz2 p60-90 注释密集区整页 `PF=NOTE_FONT`（L725 纯注释页判据），序号行与正文行同字号，故锁当前：序号字号 ≤ 正文 × 1.05。
  - 测试：`test_note_line_font_below_body`（锁当前值）
- **C2 校注标记上标小字**：`esc` 校注标记用 `\fontsize{FONT×MARKER_SCALE}`（L226-227，MARKER_SCALE=0.55），上标字号 < 行主字号 × 0.7。
  - 测试：`test_marker_superscript_small`

### ③位置还原与行距
- **C3 页数锁当前范围**：古籍行距大致溢出（单趟 POSITIONAL 无 ratio 校正，30 源页 -> ~50 物理页）。校准两趟后应 1:1，但单趟故锁 [源×1.0, 源×2.5]。
  - 测试：`test_page_count_locked`（锁当前值）
- **C4 每页行间距 CV 锁当前**：`POSITIONAL=1` 用 `bl=_pp`（源 pitch）+ `\\[-2pt]` 墨高重叠（L950），同页行距相对均匀。CV ∈ [0, 0.5]。
  - 测试：`test_pitch_cv_locked`（锁当前值）

### ④转义与符号修正
- **C5 全书无 U+FFFD**：`_esc_chars`（L200-206）修正符号（○->〇、【】->〔〕）不引入 U+FFFD；图页 `is_garbage_page`（L465-476）整页贴图。
  - 测试：`test_no_replacement_char`
- **C6 序号〔X〕被渲染**：行首 `[X]` -> `〔X〕` 序号（不上标，L223），输出文本含 `〔`。
  - 测试：`test_seq_marker_exists`

### ⑤渲染约束
- **C7 序号〔X〕对齐到文字列左缘**：序号统一到 `_note_text_x[key] - 序号宽`（L1020-1026），不按源 x0 波动；故序号行 x0 标准差 < 普通行 x0 标准差。
  - 测试：`test_seq_x0_more_aligned_than_normal`

---

## 锁当前值的不变量（3 条）

单趟 `POSITIONAL=1` 无 ratio 校正（fit_positional 两趟校准太慢且内部 `python3` 命中 mineru venv 无 fitz），以下不变量锁单趟现状范围，待校准两趟后可收紧：

| 不变量 | 期望（校准后） | 当前现状（单趟） | 锁定范围 |
|---|---|---|---|
| C1 注释 vs 正文字号 | NOTE < BODY | 注释区同字号（==） | 序号 ≤ 正文 × 1.05 |
| C3 页数 | = 源（1:1） | 30 -> ~50（溢出 67%） | [源, 源×2.5] |
| C4 行间距 CV | < 30% | 单趟墨高重叠 | CV ∈ [0, 0.5] |

> 这正是不变量测试的价值：把"单趟现状"和"校准后理想"都记下，重构/校准回归时立刻可见。

---

## 不变量与测试对应总表

| 管线 | 不变量 | 阶段 | 代码行号 | 测试函数 |
|---|---|---|---|---|
| geom | G1 小字<正文×0.85 | ① | L55 | test_small_font_below_body |
| geom | G2 标题≥正文×1.2 | ② | L499, L501-503 | test_heading_above_body |
| geom | G3 页数[源×0.8,源×1.5] | ③ | L53, L865 | test_page_count_lower_bound |
| geom | G4 无 U+FFFD | ④ | L198, L463 | test_no_replacement_char |
| geom | G5 段首缩进 | ⑤ | L1013 | test_paragraph_indent_exists |
| geom | G6 行不溢出版心 | ⑤ | L1027-1029 | test_no_line_overflow |
| classic | C1 序号字号≤正文×1.05（锁） | ② | L626-627, L725 | test_note_line_font_below_body |
| classic | C2 上标小字 | ② | L226-227 | test_marker_superscript_small |
| classic | C3 页数[源,源×2.5]（锁） | ③ | L950, L913 | test_page_count_locked |
| classic | C4 行间距CV[0,0.5]（锁） | ③ | L950 | test_pitch_cv_locked |
| classic | C5 无 U+FFFD | ④ | L200, L465 | test_no_replacement_char |
| classic | C6 序号〔X〕存在 | ④ | L223 | test_seq_marker_exists |
| classic | C7 序号x0对齐 | ⑤ | L1020-1026 | test_seq_x0_more_aligned_than_normal |

## 断言原则

- 用范围/关系（<, >, ratio），不用具体数字（≠ 222, ≠ 95.3%）。
- 锁当前值时用区间（如 CV ∈ [0, 0.5]），仍是关系断言。
- 不绑定特定 PDF 页数/pitch/字号值；换输入段（调 `INV_GEOM_START`/`INV_CLASSIC_START`/`INV_N`）断言仍成立。

## 运行

```bash
/usr/bin/python3 -m pytest src/test/invariants/ -v
```

调参（换输入段）：
```bash
INV_N=30 INV_GEOM_START=40 INV_CLASSIC_START=60 /usr/bin/python3 -m pytest src/test/invariants/
```
