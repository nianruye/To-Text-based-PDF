# 横排标点 FN 根因审计（t264）

## 结论（核心问题）

**横排标点主要是在 OCR 阶段丢的，不是渲染阶段丢的。**

- 本次可逐条定位的 **142 条 FN**（ghbq 56、wz4 86）全部归因 **`ocr_absent`**；
- **`render_dropped = 0`**：没有发现「OCR lines 有该标点、产物 PDF 文本层在同处缺失」的案例；
- 与竖排 wz7 结论一致（竖排 30/34 为 `ocr_absent`，render_dropped=0），横排不是产品渲染 bug。

重要限制：punct_eval 序列口径报告 ghbq **FN=78**、wz4 **FN=99**（合计 177）；本次 item 级审计只成功展开 **142 条**（ghbq 56 / wz4 86），其余 **35 条**是 sequence gap-tolerance/同组配对产生的 FN，未能 item 化；这 35 条中**未发现任何 render_dropped 证据**，不能据此改成产品 bug。

## 一、gold 三缺陷修复（F1/F2/F3）

文件：`src/test/bench/content_gold_h_v1.json`
gold_sha256：`8423a6a8fa2f0a156c8aad1aa45a37d486c30c16c1943b1e6dde02d7352a2df4`

### F2 bracket 类补全
t262 指出的 7 条 bracket（`（）`）来自 tesseract 的 ASCII `(` `)`；t261 gold 未归一化，punct_eval 不认成 bracket。
本次按 `PUNCT_EVAL` §2.2 把 **ASCII `(` `)` 归一为全角 `（` `）`**（bracket_present），并保留《》为 `booktitle_open/close`（spec 129/92 行明确书名号与括号分开）。
修复后 wz4 gold 有 **7 个 bracket_present**，基线 bracket 类 **TP7 / FN7 / type_accuracy 1.0**，不再是 0 列。

### F3 uncertain 位置级
16 页 `uncertain` 从 `pos=0` 页级占位改为**该页正文中实际引号/标点位置**（首引号或首个标点），格式 `{pos,char,reason}`；每页 1 条（≤3）。
仍需注意：tesseract 错字/漏字未逐处登记，不能把 uncertain 仅 16 条当完整不确定性清单。

### F1 基线可复现
最终 gold 上重跑（不是沿用 t261 旧数字）：

| 书 | TP | FP | FN | P | R | unscorable | swaps |
|---|---:|---:|---:|---:|---:|---|---:|
| ghbq | 244 | 51 | 78 | **0.8271** | **0.7578** | [] | 1 |
| wz4 | 447 | 123 | 99 | **0.7842** | **0.8187** | [] | 0 |

产物 sha256：
- ghbq `cd397d2c947430b444cfcd9266e4b9cb7212c48a7a222d99c9d38579841ff787`
- wz4 `7f76a142668af90a2a0c1301685d4ef67ff867673c37ecb98479fbea44f5b21d`

与 t262 独立复跑（ghbq 244/51/77、wz4 440/130/92）差异来源：**gold 文件变了**——本次把 ASCII 括号归一为 bracket，使 wz4 bracket 从 gold 缺失变成 7 条、同时影响同页配对；ghbq 仅 1 条 FN 差异（gap/引号配对）。不是沿用旧数，也不是 punct_eval 口径改变。

## 二、按类 × 归因

| 书 | 类 | FN | ocr_absent | render_dropped | 其他 |
|---|---|---:|---:|---:|---:|
| ghbq | comma | 38 | 38 | 0 | 0 |
| ghbq | quote_open | 9 | 9 | 0 | 0 |
| ghbq | period | 4 | 4 | 0 | 0 |
| ghbq | bracket_present | 1 | 1 | 0 | 0 |
| ghbq | booktitle_close | 1 | 1 | 0 | 0 |
| ghbq | colon | 1 | 1 | 0 | 0 |
| ghbq | quote_close | 1 | 1 | 0 | 0 |
| ghbq | ellipsis | 1 | 1 | 0 | 0 |
| wz4 | period | 31 | 31 | 0 | 0 |
| wz4 | quote_open | 14 | 14 | 0 | 0 |
| wz4 | quote_close | 10 | 10 | 0 | 0 |
| wz4 | comma | 8 | 8 | 0 | 0 |
| wz4 | bracket_present | 7 | 7 | 0 | 0 |
| wz4 | booktitle_open | 7 | 7 | 0 | 0 |
| wz4 | booktitle_close | 5 | 5 | 0 | 0 |
| wz4 | question | 4 | 4 | 0 | 0 |
| **合计** | | **142** | **142** | **0** | **0** |

最该先修：**comma（ghbq 38）、period（wz4 31）、quote_open/quote_close（合计 48）**。
归因全是 `ocr_absent` → 应动 OCR（参数/二次识别/结构化补全），不是动 build_geom 渲染。

## 三、render_dropped 证据

**无。** 逐条审计中未出现「OCR lines 原文含该标点 + 产物文本层同处缺失」的案例；因此没有最小复现可列，也没有产品 bug 可提。

## 四、ocr_absent 裁片

- `output/ghbq/punct_fn_crops/`：10 张（4×，源图，红框=OCR 行 bbox）
- `output/wz4/punct_fn_crops/`：11 张
- 合计 21 张 ≥ 20 张抽样要求。
- 抽样均为「源图可见标点、OCR 行文本中无对应标点」；因 ocr_absent 的标点不在 OCR lines 中，红框只能标 OCR 行范围，不能逐字符框出缺失标点；源图裁片用于人眼确认该行内确有标点。

逐条清单：
- `output/ghbq/punct_fn_items_h.json`（56 条）
- `output/wz4/punct_fn_items_h.json`（86 条）
字段含 page/class/value/before/after/attribution/ocr_line/product_text/ocr_present/product_present。

## 五、已知限制

1. item 级只展开 142/177 条 FN；剩余 35 条是 gap-tolerance/同组配对 FN，未 item 化（无 render 证据）。
2. gold 仍是 tesseract provisional（t261 方法），引号配对、错字会影响 FN 定义；但 t262 独立复核 13/16 页逐类一致，主要结论（OCR 丢失、非渲染）与竖排一致。
3. 裁片红框是 OCR 行 bbox，不是缺失标点 bbox；ocr_absent 的标点没有 OCR 坐标，这是该方法固有限制。
4. 未改产品渲染/data/现有 gold/punct_eval；未 commit。

## 六、自检

- `punct_eval --mode sequence` 两书均正常加载，`unscorable_pages=[]`；ghbq `order_swaps=1`（阅读序一次换位），wz4 `0`。
- gold_sha 与上表一致；产物 sha 与报告一致。
