# 横排 OCR 参数对照实验（t265）

## 结论

**参数路线有效，推荐 D 组：`max_pixels=5644800 + unwarp=1`。**

- D：TP **288** / FP **51** / FN **34**，P **0.8496**，R **0.8944**
- A（当前默认）：TP 197 / FP 52 / FN 125，P 0.7912，R 0.6118
- D vs A：P **+5.84pp**、R **+28.26pp**（P 不降）；满足「P 不降 >1pp + R 提 ≥3pp」判定线。
- D vs t264 现有产物基线（P0.8271/R0.7578）：P **+2.25pp**、R **+13.66pp**；仍满足判定线（但 A 新识别与旧 lines 不完全同口径，见限制）。

**推荐 `data/ghbq/ocr_params.json` 内容（本次只写报告，未创建 data 文件）：**

```json
{"max_pixels": 5644800, "min_pixels": 147384, "orientation": 0, "unwarp": 1, "layout_shape": "auto"}
```

## 实验设计（4 组，仅 8 页）

gold：`src/test/bench/content_gold_h_v1.json`，ghbq p14/15/23/27/30/50/80/100；gold_sha `8423a6a8…`。
每组一次 spotting OCR（8 页一个 batch）；**未批量跑全书**。

| 组 | 参数（只改一个变量） | jobId | 完成时间 |
|---|---|---|---|
| A | max_pixels=2822400, unwarp=0（默认） | 114045971188326400 | 00:58:19 |
| B | max_pixels=5644800（2×）, unwarp=0 | 114046124667449344 | 00:58:50 |
| C | max_pixels=2822400, unwarp=1 | 114046124335665152 | 00:59:17 |
| D | max_pixels=5644800, unwarp=1 | 114046124453232640 | 00:59:06 |

命令（可复跑）：

```bash
# A
/usr/bin/python3 src/tools/ocr_book.py --book ghbq --input source_pdf/ghbq.pdf \
  --out-dir output/ghbq/ocr_param_exp/A --pages 14,15,23,27,30,50,80,100 \
  --pages-per-batch 8 --mode spotting --token-file /tmp/paddle_token
# B
... --out-dir output/ghbq/ocr_param_exp/B ... --ocr-max-pixels 5644800
# C
... --out-dir output/ghbq/ocr_param_exp/C ... --ocr-unwarp 1
# D
... --out-dir output/ghbq/ocr_param_exp/D ... --ocr-max-pixels 5644800 --ocr-unwarp 1
```

成本：4 组 × 1 次 API 调用（8 页/次），无全书批量；单组墙钟约 25–40 秒（A 00:58:19、B 00:58:50、C 00:59:17、D 00:59:06，B/C/D 并行提交）。

## 文本级评测口径

用 gold 的 8 页文本与每组 `ghbq_spotting_lines.json` 按 0-based 页 key 拼接，调 `punct_bench.sequence_eval`（与 punct_eval 同一个序列配对实现），**绕过渲染**。
t264 已实测横排 `render_dropped=0`，因此 lines 上的标点 ≈ 产物标点；本实验不重建产物、不改 punct_eval 口径。

## 总体对照

| 组 | TP | FP | FN | P | R | ΔP vs A | ΔR vs A |
|---|---:|---:|---:|---:|---:|---:|---:|
| A 默认 | 197 | 52 | 125 | 0.7912 | 0.6118 | — | — |
| B max2x | 286 | 53 | 36 | 0.8437 | 0.8882 | +5.25 | +27.64 |
| C unwarp | 226 | 50 | 96 | 0.8188 | 0.7019 | +2.76 | +9.01 |
| **D max2x+unwarp** | **288** | **51** | **34** | **0.8496** | **0.8944** | **+5.84** | **+28.26** |

**D 最优**；B 次优；C 的 unwarp 单项只带来小幅提升。

## 按类对照（TP/FP/FN）

| 类 | A | B | C | D |
|---|---|---|---|---|
| comma | 42/2/91 | 130/3/3 | 70/1/63 | **131/2/2** |
| period | 68/4/4 | 68/4/4 | 69/3/3 | 69/3/3 |
| quote_open | 40/13/20 | 40/13/20 | 40/13/20 | 40/13/20 |
| quote_close | 30/24/6 | 30/24/6 | 30/24/6 | 30/24/6 |
| colon | 4/0/2 | 6/0/0 | 4/0/2 | 6/0/0 |
| enumeration_comma | 6/7/0 | 6/7/0 | 6/7/0 | 6/7/0 |
| booktitle_open | 3/1/0 | 3/1/0 | 3/1/0 | 3/1/0 |
| booktitle_close | 3/1/1 | 3/1/1 | 3/1/1 | 3/1/1 |
| bracket_present | 0/0/1 | 0/0/1 | 0/0/1 | 0/0/1 |
| ellipsis | 1/0/0 | 0/0/1 | 1/0/0 | 0/0/1 |

格式：TP/FP/FN。关键变化全在 **comma**：A 的 OCR 输出把大量中文逗号吐成 ASCII `,`，D 输出全角 `，`（gold 全角），comma TP 42→131、FN 91→2；quote 完全不变。

## 8 页 × 组总体（TP/FP/FN, P/R）

| 页 | A | B | C | D |
|---|---|---|---|---|
| 14 | 13/1/12 .93/.52 | 24/1/1 .96/.96 | 13/1/12 .93/.52 | 24/1/1 .96/.96 |
| 15 | 22/8/20 .73/.52 | 36/8/6 .82/.86 | 35/8/7 .81/.83 | 36/8/6 .82/.86 |
| 23 | 22/10/16 .69/.58 | 31/11/7 .74/.82 | 21/10/17 .68/.55 | 31/11/7 .74/.82 |
| 27 | 28/7/13 .80/.68 | 37/7/4 .84/.90 | 29/6/12 .83/.71 | 38/6/3 .86/.93 |
| 30 | 25/7/17 .78/.60 | 35/7/7 .83/.83 | 26/6/16 .81/.62 | 36/6/6 .86/.86 |
| 50 | 42/3/2 .93/.95 | 41/3/3 .93/.93 | 42/3/2 .93/.95 | 41/3/3 .93/.93 |
| 80 | 21/6/27 .78/.44 | 43/6/5 .88/.90 | 38/6/10 .86/.79 | 43/6/5 .88/.90 |
| 100 | 24/10/18 .71/.57 | 39/10/3 .80/.93 | 22/10/20 .69/.52 | 39/10/3 .80/.93 |

## 错误分析（A vs D）

A→D 共 **71 行**有标点差异，可逐条列出 **20 条**（其余为同页同型重复；本次取 20 条）：
- **15 条 comma 变好**：源图有 `，`，A 输出 ASCII `,`（不被算中文逗号），D 输出全角 `，`。示例 p14 line6 `此,问题`→`此，问题`（Δ+2）；p15 line1 `政时,苏联`→`政时，苏联`（Δ+3）。
- **1 条 ellipsis 变坏**：p50 line11 `……`→`···`（Δ−2）；这是 D 的副作用，需在二次识别融合中回退。
- **quote/period/bracket 无变化**：D 并非普遍改善所有类，主要修的是「小标点被识别成 ASCII / 漏识」的中文逗号。

裁片：`output/ghbq/ocr_param_exp/crops/`，**21 张** 4× 源图，红框为 OCR 行 bbox；覆盖 19 个 comma 变好行 + 1 个 ellipsis 变坏行（共 20 行；21 张裁片含重复保留）。因 D 对 quote/period 无差异，无法给「每类 5 张」的 quote 裁片；报告如实登记为无变化类。

**为什么 max_pixels 影响 comma**：提高切图分辨率后，小字号逗号的轮廓完整进入识别窗，模型不再用 ASCII `,` 代替全角 `，`；unwarp 对倾斜页有额外小收益（C 单独 R +9pp），组合 D 最好。该解释与 A/D 的实际字符形态差异一致。

## 限制与下一步

1. A 组是新调用的默认 OCR，不是 t264 产物里的旧 lines：A 的 comma 大量为 ASCII，导致 A P/R 低于 t264 旧基线；跨实验比较须以「同一次 A」为准，报告已同时给出 D vs t264。
2. 本实验只 8 页、只 ghbq；未验证 wz4，也未重建产物。D 推荐先写 `data/ghbq/ocr_params.json` 做 8 页小重建，再跑 punct_eval 确认（本任务不改 data）。
3. quote 类完全未改善（TP/FN 不变）；若继续走 OCR，需要二次识别融合或专门 prompt，不是单靠 max_pixels。
4. ellipsis 在 D 变差 2 字符，建议融合时优先保留 A 的 `……`。
5. 未改产品代码/data/gold/punct_eval；未 commit。

## 自检

- 4 组都完成，`jobs.json` state=done，jobId 见上表。
- 文本级 `sequence_eval` 对 gold 8 页正常；本实验不涉及 `unscorable_pages`/`order_swaps`（这些属于产物评测）。
- 结果文件：`output/ghbq/ocr_param_exp/{A,B,C,D}/ghbq_spotting_lines.json`。
