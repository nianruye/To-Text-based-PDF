# punct_bench v1 · 标点/内容评测器（spec §7 实现）

> 任务：t112 — 实现 `punct_eval.py` 评测器（gold + 产物 PDF → 每类指标表），并在 v51 上跑首个基线
> 执行：竖排工程师　日期：2026-11-08
> 证据：`src/tools/punct_bench.py`（实现）+ `src/tools/punct_eval.py`（spec §7 CLI 入口，转发同一实现）+ `src/test/unit/test_punct_bench.py` + `tmp_vert/bench/`
> 约束：只读评测；不改 build_vert/verify_vert；不联网/不调 API；未 commit。

## 0. 命名与交付

| 项 | 路径 | 说明 |
|---|---|---|
| 实现 | `src/tools/punct_bench.py` | 全部逻辑（gold 读取/预测抽取/匹配/指标/内容 CER/JSON+CSV） |
| spec §7 CLI | `src/tools/punct_eval.py` | **同一实现**的入口转发（`punct_eval.py --gold --pdf --coords --lines --out-json --out-csv`） |
| 单测 | `src/test/unit/test_punct_bench.py` | 4 用例（完美/漏检+误插/方向错+括号类型/内容 CER） |
| 基线 | `tmp_vert/bench/v51_metrics.json/.csv`、`v48_metrics.json/.csv` | v48/v51 各一份（含内容指标版 `v51_metrics_with_content.json`） |
| 验收命令用 gold | `src/test/bench/punct_gold_v1.json` | demo gold 副本（t111 真实 gold 到位后替换为 data/punct_eval/ 并更新命令） |

> 说明：captain 明确 spec 文件名用 `punct_eval.py`；为避免两套实现，逻辑写在 `punct_bench.py`，`punct_eval.py` 仅转发。

## 1. 算法

1. **gold**：读 spec §4 schema（`{schema_version, dataset, items[]}`；items 字段 page/column/char_pos/class/value/bbox/cell/pair_id/axis…）。
2. **预测抽取**（产物 PDF + coords/lines，与 verify_vert 同源）：
   - 每页每列：`text`（lines）+ bbox（coords）→ 字格 `step_y=(y1-y0)/n`、`step_x=x1-x0`、cell 中心；
   - 逐字扫描：`「﹁『『` → quote_open；`」﹂』﹄` → quote_close；`〔︹` → 找同列闭括号：有名字 → bracket_type（name=括号内文本），空 → bracket_present；`—–―` 连续段 → dash（length_pt）；U+E100-E1FF/①②… → ring（number）。
3. **匹配**（spec §1.2）：同 page、同 column、**同类组**（quote_open/close 归 quote 组；bracket_present/type 归 bracket 组）；字格中心 `dx≤0.5 且 dy≤0.5`；无 cell 时 bbox IoU≥0.5 fallback；一对一最近优先，同距离同类优先（组内 class 匹配加 0.02 惩罚，防 bracket_present 抢 bracket_type）；跨页/跨列不匹配。
4. **指标**：每类 TP/FP/FN、position precision/recall、false_insertion_rate、miss_rate；quote 另出 direction_accuracy；bracket_type 出 type_accuracy；dash 出 length_median/p95_error；ring 出 value_accuracy；overall 汇总。
5. **内容指标**：读 content gold（`{items:[{page,text}]}` 或 page→text）；CER = 字级编辑距离/真值字数；按 difflib opcodes 拆 **missing（漏）/wrong（错）/extra（多）**；gold 中 `?` 视为存疑字，**不计分**（从 gold 去掉，单列 `doubt_chars`）。
6. **输出**：JSON（`overall`/`by_class`/`by_page`/`errors`（未匹配 gold 逐条 reason）/`gate`（v1 `unscored`）/`content`）+ CSV 长表（`split,class,page,metric,value`）。
7. **范围**：只对 **gold 覆盖的页** 打分（页面来自数据，评测器无白名单）；空 gold 时退化为全预测页（仅测试边界）。

## 2. 接口

```bash
# spec §7（gold 由 t111 产在 data/punct_eval/；本机 demo 用 tmp_vert/bench/demo_gold.json）
/usr/bin/python3 src/tools/punct_eval.py \
  --gold tmp_vert/bench/demo_gold.json \
  --pdf output/wz7_full/wz7_full_v51.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --content-gold tmp_vert/bench/demo_content_gold.json \
  --book wz7 \
  --out-json tmp_vert/bench/v51_metrics.json --out-csv tmp_vert/bench/v51_metrics.csv
```

- 退出码：0 = 评测完成（不代表达标）；2 = gold/输入不可读；3 = 页面/列无法对齐（预留 manual）。
- 只读；无 token、无网络；20 页量级 < 1s（预测只扫 gold 页）。

## 3. 基线输出（v51，demo gold 36 items：p57/p703/p1179，含内容 p703）

| 指标 | v51 | v48 |
|---|---|---|
| overall position precision / recall | **0.878 / 1.000** | 0.878 / 1.000 |
| false_insertion_rate / miss_rate | 0.122 / 0.000 | 0.122 / 0.000 |
| quote_open TP/FP/FN、direction_accuracy | 18/0/0、1.000 | 18/0/0、1.000 |
| quote_close TP/FP/FN、direction_accuracy | 17/0/0、1.000 | 17/0/0、1.000 |
| bracket_type TP/FP/FN、type_accuracy | 1/5/0、1.000 | 1/5/0、1.000 |
| **内容 p703**：CER / missing / wrong / extra / doubt | **0.0997 / 17 / 14 / 3 / 0** | 0.0997 / 17 / 14 / 3 / 0 |

- `by_class` 里 `bracket_type` 的 5 个 FP = 预测在 gold 页上发现、但 gold 未收录的同名/他名括号（demo gold 只收了 1 个 `滾綉毬`）——真实 t111 gold 不会这样稀疏。
- v48/v51 在 demo gold 上相同（gold 的 p703/1179 引号与括号两版一致；v51 新增的 p1180/其他括号不在 demo gold 里）。

## 4. 单元测试（4 passed）

1. `test_perfect_match_precision_recall`：`「甲」乙` + 2 gold → precision/recall 1.0、direction 1.0；
2. `test_missed_and_false_insertion`：gold 1 条、产物 1 条错位 → recall 0、miss 1；空 gold + 产物引号 → false_insertion_rate 1.0；
3. `test_direction_error_and_bracket_type`：`﹂` vs gold `﹁` → 匹配但 direction_accuracy 0；`〔山坡羊〕` → bracket_type accuracy 1.0；
4. `test_content_cer_and_doubt`：gold `甲乙丙?丁` vs pred `甲丙丁` → doubt 1、gold_chars 4、edit 1、missing 1、CER 0.25。

## 5. 已知局限

- **demo gold**：本轮 t111 的 `data/punct_eval/gold_v1_20p.json` 尚未产出，基线用 **demo gold**（v51 自身 + p703 源文）跑通链路；真实 20 页 gold（8 wz6 + 8 wz7 + 4 heldout）到位后直接替换 `--gold` 即可，指标口径不变。
- **pair P/R / paragraph_boundary**：v1 未实现（spec 列为 v2）；`bracket_present` 在 demo gold 中无条目。
- **dash/ring**：demo gold 的 p57 无 dash 段、ring 页（1682）不在 demo 页 → 两类 TP 为 0；真实 gold 需覆盖。
- **未匹配原因**：当前 `errors` 只给 `no_prediction_in_tolerance`；class/value/direction 错在 `by_class` 的 type/direction accuracy 中体现（不逐条列）。
- **位置容差**：cell 中心 ±0.5 格；无 cell 用 bbox IoU≥0.5 fallback（已实现）；跨页/列不匹配。

## 6. 复现

```bash
/usr/bin/python3 tmp_vert/bench/make_demo_gold.py      # demo gold（仅冒烟；真实 gold 由 t111 提供）
/usr/bin/python3 src/tools/punct_eval.py --gold tmp_vert/bench/demo_gold.json \
  --pdf output/wz7_full/wz7_full_v51.pdf --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --content-gold tmp_vert/bench/demo_content_gold.json \
  --book wz7 --out-json tmp_vert/bench/v51_metrics.json --out-csv tmp_vert/bench/v51_metrics.csv
/usr/bin/python3 -m pytest src/test/unit/test_punct_bench.py -q
```

## 7. 约束

- 未改 build_vert.py / verify_vert.py / data/ / output 产物；评测器只读；未 commit；无 token/网络。
