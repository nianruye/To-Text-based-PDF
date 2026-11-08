# punct_eval 序列口径（阅读序，无坐标）· v1.3

> 任务：t139 实现 → t142/t144/t146 修复 — 按 PUNCT_EVAL v1.3 实现 `punct_eval.py --mode sequence`，v51 基线
> 执行：竖排工程师　日期：2026-11-08
> 证据：`src/tools/punct_bench.py`、`src/tools/punct_eval.py`、`src/test/unit/test_punct_bench.py`、`tmp_vert/bench/seq_v51.json/.csv`、`cell_v51.json/.csv`
> 约束：只读评测；不改产品代码/data；未 commit；无 token/网络/API。

## 0. v51 基线（mode=sequence，B 口径）

- 页集：content gold 中 `book=wz7` 的 **8 页**（57/97/159/704/705/830/898/1718）；`unscorable_pages=[]`；`reading_order.excluded_furniture=1`。
- **overall：TP 652 / FP 38 / FN 34 → precision 0.9449、recall 0.9504；order_swaps 0**。

| 类 | TP | FP | FN | P | R |
|---|---|---|---|---|---|
| comma | 246 | 2 | 2 | 0.9919 | 0.9919 |
| period | 127 | 8 | 9 | 0.9407 | 0.9338 |
| quote_open | 65 | 2 | 4 | 0.9701 | 0.9420 |
| quote_close | 58 | 10 | 8 | 0.8529 | 0.8788 |
| colon | 53 | 11 | 5 | 0.8281 | 0.9138 |
| bracket_present | 31 | 3 | 4 | 0.9118 | 0.8857 |
| ring | 23 | 0 | 0 | 1.0 | 1.0 |
| question | 16 | 0 | 0 | 1.0 | 1.0 |
| enumeration_comma | 13 | 1 | 1 | 0.9286 | 0.9286 |
| semicolon / exclamation | 10 / 10 | 0 | 0 | 1.0 | 1.0 |
| dash | 0 | 1 | 1 | 0.0 | 0.0 |

- 类型混淆：`quote_open>quote_close: 1`；`order_swaps=0`。

### 与 A（cell）口径并列 + ab_diff

- `--mode cell`（旧口径 A，provisional）：`cell_v51.json` 36 items（demo punct gold），TP 35/FP 0/FN 1 → P 1.000 / R 0.9722。
- **A/B 页集不同**（A=36 条 demo gold 的 3 页；B=8 页 wz7 content gold），不可直接比较；`ab_diff.page_sets_differ=true`。
- `ab_diff.by_class`：`quote_open −0.058`、`quote_close −0.1212`；`gt5pp` 3 条（`class/delta/causes=['page_set_diff']`）。
- sequence 默认加载 `tmp_vert/bench/cell_v51.json`（不存在时 `ab_diff.note` 显式提示）；`--ab-cell-json` 可覆盖。

## 1. §6.4.7 输出字段（已补齐）

```
schema_version=punct-eval-v1.3  mode=sequence  method=B_sequence
dataset_id=punct-eval-b-20p      gold_source=content_gold(t111/provisional)  normalization=content-N0
by_class = per_class（同值）      by_page[]={page,tp,fp,fn,precision,recall,order_swaps,reading_order}
reading_order={pages,unscorable,excluded_furniture}
ab_diff={cell_json,page_sets_differ,note,by_class,gt5pp[{class,delta,causes}]}
gate={status:"provisional", thresholds_version:"v1.2", auto_enabled:false}
errors=[]（reading_order 不可判页会在此登记 kind=reading_order）
```

- cell 口径同样保留 `mode=cell` 并新增 `method=A_cell`；CSV 首列 `mode`。
- `order_swaps` 定义（JSON `order_swaps_definition`）：**同 gap 多 tokens 按序列配对并计逆序**；跨 gap 由单调 gap map 保证非逆序（恒 0）。单测 `test_order_swaps_same_gap`：gold `甲「」乙` vs pred `甲」「乙` → swaps ≥1。

## 2. 阅读序重建（§6.4.2，书无关）

- 输入：产物 PDF（fitz `rawdict` 逐字符 + bbox），不读 gold 坐标。
- **聚类阈值按 spec 公式**：`tol = max(1.2 × median glyph height, 0.5 × median span height)`；竖排字形旋转，glyph height 取字符 bbox **宽**（沿列方向），span 高取 bbox 高。列按 x 右→左、列内 y 上→下；横排 y 行上→下、行内 x 左→右。
- **家具剔除（书无关）**：`gold exclude` 文本；或【**短 span（≤6 字）且中心在 8% 页边带内且匹配通用页面家具模式**】：
  - 页码：阿拉伯/汉字数字/圈码 `PAGE_NUM_RE`，**罗马数字 `ROMAN_RE`**（长度 ≤6）；
  - 页眉：通用 `第X回/第X章/第X節/第X頁/第X卷/卷X/上卷/下卷/目錄`。
- **不按书/页白名单剔除**；`金瓶梅` 等书名不再有专用正则（已删除），短列仅在匹配上述通用模式且位于边带时剔除。
- 正文长列（>6 字）即使中心在边带内也**不**剔除；正文区短列不因短剔除（单测覆盖）。
- mixed / 其他无 `block_order` → `unscorable_pages` + `errors[kind=reading_order]`（不静默猜）。

## 3. 对齐（§6.4.3）

1. 去标点得 anchor（gold/pred 同时），N0 + 竖排形归一（﹁→「、︵→（、︽→《 等）；
2. `SequenceMatcher(autojunk=False)` → gap map（最后匹配块同时到串尾时补 `len(g)→len(p)`）；
3. 标点 token 记 `(gap, class, value, order)`；同 gap 同 class → **TP**；同族异类 → **confusion + pred 类 1 FP + gold 类 1 FN**；无法映射/无同类 → FN；pred 未配对 → FP；
4. 不做标点序列硬配对、不做 ±1 gap 容错；`order_swaps` 见上。

## 4. 单测（32 passed）

新增/关键用例：竖排列序、横排行序、页眉页脚/页码剔除、罗马数字页码、**书名短列不特判**、**正文入带不误剔**、完美/漏检/误插/类型错（comma→period：comma fp0/fn1、period fp1）、同 gap 逆序、串尾标点、竖排形归一、空页、端到端合成 PDF、ab_diff 字段。

## 5. 版面差异登记

- 家具剔除由「逐字符页边带过滤」改为「**仅剔短家具 span**」（spec §6.4.2）：v51 TP 634→**652**、FN 52→**34**（此前被逐字符过滤掉的边缘正文列/标点回补），`excluded_furniture=1`。
- 若要求 A/B **列数一致**逐类严格比较，需另修版面（产品管线页眉/页码检测），不在本任务范围；A/B 差异已按 `page_set_diff` 登记。

## 6. 已知局限

- **B gold provisional**：content gold 22 页混合（其中 wz7 8 页）；heldout（wz2/wz4）不在 v51 产物内，本轮无法评测；正式阈值需 v2 gold。
- **阅读序**：mixed/竖横混排无 block_order → unscorable；极端倾斜/并字列聚类可能出错（本 8 页 unscorable=0，未逐页人工核对）。
- **dash**：v51 文本层 `—` + `3 Tr`，sequence 只读文本层；gold 转录破折号写法不同 → dash 1 FP/1 FN（v2 再约定）。
- **类型混淆**仅同族异类；跨族按 FP+FN。
- **gold 转录错字**直接进 FN/FP，无可信度加权。

## 7. 复现

```bash
/usr/bin/python3 src/tools/punct_eval.py --mode sequence --gold data/punct_eval/content_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --book wz7 \
  --out tmp_vert/bench/seq_v51.json --out-csv tmp_vert/bench/seq_v51.csv \
  --ab-cell-json tmp_vert/bench/cell_v51.json   # 默认已加载
/usr/bin/python3 -m pytest src/test/unit/test_punct_bench.py -q   # 32 passed
```

## 8. 约束

- 只写 src/tools/punct_bench.py、src/tools/punct_eval.py、src/test/unit/test_punct_bench.py、docs/punct_eval_sequence.md、tmp_vert/bench/；未改产品代码/data；未 commit。
