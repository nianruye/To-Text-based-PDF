# 墨迹笔画判加粗（t321/t322）

## 判据

- 源页 300dpi 灰度；按 OCR 行 bbox 切行
- 行笔画 = 水平暗游程（灰度<180）中位
- 正文笔画中位 = 行高在页中位 ±10% 的行的笔画中位
- `ratio >= INK_BOLD_RATIO(默认1.30)` 且 `行高/正文中位 ∈[0.90,1.15]` → 加粗
- `ratio <1.15` 常规；1.15–1.30 灰区不判
- 只加 `\bfseries\CJKfamily{heiti}`，字号/位置/行距不变

## t322 收紧（消除误伤）

- 跳过 TOC 页 `key in _TOC_PAGE`
- 排除纯数字/标点、长度<4、页码行、行高偏差>20%
- 同块一致性：命中<2 行整块不判；判出后同 LAYJSON text 块传播
- 仅含 `doc_title + paragraph_title` 的章节页启用

## ghbq 误伤对照

`INK_BOLD=0` vs `1`：

| 项 | INK0 | INK1 |
|---|---:|---:|
| 页数 | 104 | 104 |
| Bold span | 111 | **111** |
| 逐页文本 diff | — | **0 页** |
| p10 页码/目录 | — | **完全不变** |

原 p10 `5` 与目录条目已不再命中；p4 也未变化（严格零 diff）。

## wz8_1 p18

| 行 | 文本 | 笔画px | ratio | 输出 |
|---|---|---:|---:|---|
| 4 | 一殷代种族… | 7.0 | 1.40 | Bold 11.0 |
| 5 | 相对立的… | 7.0 | 1.40 | Bold 11.0 |
| 6 | 素辩证思想… | 同块传播 | — | Bold 11.0 |
| 18 | 根据甲骨文… | — | — | Regular（超块过滤） |

wz8_1：77页，gate PASS，pitch98.7%。

## 其余书

- wz1/wz4/wz3 无 layout.json；wz2 的 doclayout 未在构建中启用 `--layout`；INK_BOLD 不进入。
- ghbq doc_title 页无 paragraph_title，不触发。
- pytest unit **802 passed**。

## 性能

wz8_1 整书（77页）构建：`INK_BOLD=0` **4.99s**，`INK_BOLD=1` **5.15s**，增幅 **+3.2%**（<10%）。仅含 doc_title 的章节页做 300dpi 分析。

## 抽样

- ghbq 全 104 页 INK0/1 逐页 diff **0**，比 30 页抽样更强。
- wz8_1 实际应用加粗：p18 三行（人工核对正确）、p30 一「春秋战国…」子标题；无正文误加粗。
- 原始检测 p18 line18 曾命中，应用层按“首个 text 块”过滤，输出为 Regular。

未改 gold/punct_eval；未 push/commit。
