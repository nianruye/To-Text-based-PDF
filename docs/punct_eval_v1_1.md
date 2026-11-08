# punct_eval v1.1 · 国标标点全集评测扩展

> 任务：t120 — 按 PUNCT_EVAL v1.1（t119）把评测器扩到 GB/T 全标点类别，兼容旧 gold，v51 实跑基线
> 执行：竖排工程师　日期：2026-11-08
> 证据：`src/tools/punct_bench.py`（实现）+ `src/tools/punct_eval.py`（CLI 入口）+ `src/test/unit/test_punct_bench.py`（12 例）+ `tmp_vert/bench/`（demo gold v1.1 / v2_baseline / v11_metrics）
> 约束：只写上述路径；不改产品代码/data/output；未 commit；无 token/网络/API。

## 0. 类映射（GB/T 16 类 + 扩展）

| GB/T 类 | 评测类 | 横排形 | 竖排形 | v1.1 |
|---|---|---|---|---|
| 句号 | `period` | 。（．） | 同形 | in-scope |
| 问号 | `question` | ？ | 同形 | in-scope |
| 叹号 | `exclamation` | ！ | 同形 | in-scope |
| 逗号 | `comma` | ， | 同形 | in-scope |
| 顿号 | `enumeration_comma` | 、 | 同形 | in-scope |
| 分号 | `semicolon` | ； | 同形 | in-scope |
| 冒号 | `colon` | ： | 同形 | in-scope |
| 引号 | `quote_open`/`quote_close` | “”‘’「」『』 | ﹁﹂﹃﹄ | in-scope |
| 括号 | `bracket_present`/`bracket_type` | （）〔〕【】［］ | ︵︶︹︺ | in-scope |
| 破折号 | `dash` | —— | 同形 | in-scope |
| 省略号 | `ellipsis` | ……（…） | 同形 | in-scope |
| 书名号 | `booktitle_open`/`booktitle_close` | 《》〈〉 | ︽︾︿﹀ | in-scope |
| 连接号/间隔号/着重号/专名号 | `connector`/`interpunct`/`emphasis_dot`/`proper_name_line` | — | — | **out-of-scope**（评测器遇 gold 中这些类直接跳过，不计分） |
| ring（扩展） | `ring` | ①②③ / U+E100+ | 同形 | extension-in-scope |
| 段落边界（扩展） | `paragraph_boundary` | — | — | v2（v1 不计分，gold 出现也不进指标） |

- **形态归一**：`canon()` 把竖排形（﹁﹂﹃﹄︵︶︹︺︽︾︿﹀）、旧式句号 `．`、`–/―`、`⋯` 归一到横排/标准形；`form` 字段记录实际形（vertical/horizontal），`form_accuracy` 仅诊断不罚（spec §2.3）。
- **括号类型**：预测带 `btype`（（）/〔〕/【】/［］），`type_accuracy` 先按 `btype` 比，旧 gold 无 btype 时退回 name 比较（兼容）。

## 1. 指标（v1.1）

- 句读 7 类：per-class position P/R + **value_accuracy**（canon 后比值，`．`≈`。` 不算错）；竖/横同值。
- 引号：direction_accuracy（开/闭）、form_accuracy（诊断）、pair 逻辑保留（v1.1 未计 pair P/R，见局限）。
- 书名号：direction_accuracy + form 诊断。
- 括号：`bracket_present` P/R；`bracket_type` 的 **type_accuracy**（圆/方/六角/方头；竖形归并）。
- 破折号/省略号：position P/R + length_median/p95_error。
- ring：value_accuracy。
- **多段引文（spec §2.5）**：gold 带 `quote_group_id`/`paragraph_index`/`paragraph_count`/`is_final_paragraph`：
  - 非最后段缺闭号 → `errors.reason=valid_carry_non_final_paragraph`，**不计 FN**；
  - 最后段缺闭号 → FN；
  - 非最后段出现闭号 → `structural.unexpected_close` 计数；
  - `structural.multi_para_validity = 合法多段组 / 多段组总数`。
- **按 GB 类别汇总**：JSON 增加 `by_gb_class`（句号/问号/…/引号/括号/破折号/省略号/书名号/圈码）tp/fp/fn/precision/recall。
- 输出 JSON（schema_version `punct-eval-v1.1`，overall/by_class/by_gb_class/structural/by_page/errors/gate/content）+ CSV 长表。

## 2. 兼容性

- **旧 gold（schema_version `punct-eval-v1`，4 类）仍能跑**：评测器检测 v1 时把预测过滤回旧类组（quote/bracket/dash/ring），复现 v1 口径（`v11_metrics.json`：36 items、precision 0.857 / recall 1.000）。
- 旧 gold 的 `quote_open/close`、`bracket_present/type`、`dash`、`ring` 类名不变；新增类只在 v1.1 gold 中出现。
- CLI 不变：`--gold --pdf --coords --lines --out-json --out-csv [--content-gold] [--src-pdf] [--book]`（`--out` 为兼容别名）。
- `paragraph_boundary` / out-of-scope 类：gold 中出现则跳过，不产生 TP/FP/FN。

## 3. 单测（12 passed）

| # | 用例 | 断言 |
|---|---|---|
| 1 | 旧 gold 引号 | P/R=1.0、direction=1.0 |
| 2 | 句号位置+值 | tp=1、value_accuracy=1.0 |
| 3 | 句读值错（gold `，` vs 产物 `、`） | comma FN=1 + enumeration_comma FP=1 |
| 4 | 竖排引号 ﹁﹂ | tp=1、form_accuracy=1.0 |
| 5 | 横排混用 “” vs 「」 | direction=1.0、form_accuracy=0.0（仅诊断） |
| 6 | 书名号 《》 | tp=1、direction=1.0 |
| 7 | 省略号 …… | tp=1、length_median_error 存在 |
| 8 | 多段引文（非最后段缺闭号） | FN=0、multi_para_validity=1.0 |
| 9 | 多段引文（中间段闭号） | unexpected_close=1 |
| 10 | 括号类型错（圆 vs 方） | type_accuracy=0.0 |
| 11 | 圈码 ③ | value_accuracy=1.0 |
| 12 | 内容 CER | doubt=1、CER=0.25 |

## 4. v51 实跑基线（demo gold v1.1，p57/p703/p1179）

- `tmp_vert/bench/v2_baseline.json`（+ CSV）：**205 items**（comma 79 / period 45 / quote_open 18 / quote_close 17 / enumeration_comma 14 / colon 9 / question 7 / bracket_type 7 / semicolon 5 / exclamation 2 / booktitle 1+1）。
- overall **precision 1.000 / recall 1.000**（gold 由 v51 自身生成，作冒烟；t111 真实 gold 到位后替换）。
- 句读各类 value_accuracy 1.0；引号 direction/form 1.0；括号 type 1.0；书名号 direction 1.0。
- `structural`：unexpected_close 0、multi_para_groups 0（demo 页无多段组）。
- 内容 p703：CER 0.0997（missing 17 / wrong 14 / extra 3 / doubt 0）。
- 旧 gold 兼容：`tmp_vert/bench/v11_metrics.json`（36 items、P 0.857 / R 1.000）。

## 5. 已知局限

- **demo gold**：t111 的 `data/punct_eval/` 20 页 gold 尚未就绪；本轮用 v51 自身生成 demo v1.1 gold 验证链路，真实 gold 到位后替换 `--gold` 即可（口径不变）。
- **pair P/R/F1**：v1.1 只实现方向 + 多段结构；单段/组级 pair P/R/F1 未输出（spec §3.4 的 pair 指标留待 t111 gold + baseline 后补）。
- **form_accuracy**：仅诊断，未纳入 auto 门禁；`form` 字段在 gold 中缺省时不上报。
- **括号类型**：竖排 `︵︶/︹︺` 与横排 `（）/〔〕` 归并；`【】/［］` 仅从预测侧识别（demo 无样本）。
- **段落边界**：v2 扩展，v1.1 不评。

## 6. 复现

```bash
# v1.1 demo gold（p57/p703/p1179，GB/T 全集类别）
/usr/bin/python3 tmp_vert/bench/make_demo_gold_v11.py
/usr/bin/python3 src/tools/punct_eval.py --gold tmp_vert/bench/demo_gold_v11.json \
  --pdf output/wz7_full/wz7_full_v51.pdf --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --content-gold tmp_vert/bench/demo_content_gold.json --book wz7 \
  --out-json tmp_vert/bench/v2_baseline.json --out-csv tmp_vert/bench/v2_baseline.csv
# 旧 gold 兼容
/usr/bin/python3 src/tools/punct_eval.py --gold src/test/bench/punct_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --book wz7 \
  --out tmp_vert/bench/v11_metrics.json
/usr/bin/python3 -m pytest src/test/unit/test_punct_bench.py -q   # 12 passed
```
