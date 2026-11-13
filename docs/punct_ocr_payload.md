# OCR payload 显式化与新旋钮对照（t268）

> 只动 `ocr_book.py` + 单测 + 文档；不改产品渲染/gold/punct_eval；未 commit。
> 数据：ghbq 8 页 gold p14/15/23/27/30/50/80/100（`src/test/bench/content_gold_h_v1.json`）；spotting 模式。

## 1. payload 显式化

`ocr_book.payload()` 现在发送官方 17 字段（`ocr_book.PAYLOAD_FIELDS` 固定顺序），不再依赖服务端默认：

| # | 字段 | 发送值/来源 | 服务端回声（E1） | 结论 |
|---|---|---|---|---|
| 1 | useDocOrientationClassify | `bool(orientation)`，默认 false | 未单列（行为同 false） | 已显式 |
| 2 | useDocUnwarping | `bool(unwarp)`，默认 false | 未单列（行为同 false） | 已显式 |
| 3 | useLayoutDetection | `layout`（spotting=false） | `use_layout_detection=false` | 一致 |
| 4 | useChartRecognition | false | `use_chart_recognition=false` | 一致 |
| 5 | useSealRecognition | false（E2 置 true） | `use_seal_recognition=false/true` | E2 生效但无文本变化 |
| 6 | useOcrForImageBlock | false | `use_ocr_for_image_block=false` | 一致 |
| 7 | mergeTables | true | `merge_layout_blocks=true` | 映射一致 |
| 8 | relevelTitles | false | 未回声 | 被忽略/不暴露 |
| 9 | layoutShapeMode | `layout_shape`，默认 auto（E3=rect） | 未回声；E3 `return_layout_polygon_points=false` | E3 有服务端副作用但无文本变化 |
| 10 | promptLabel | spotting / ocr | 未回声（useLayoutDetection=false 时生效域） | 已显式 |
| 11 | repetitionPenalty | 1 | 未回声 | 服务端默认/未回显 |
| 12 | temperature | 0 | 未回声 | 同上 |
| 13 | topP | 1 | 未回声 | 同上 |
| 14 | minPixels | 147384 | 未回声 | 请求已显式 |
| 15 | maxPixels | 2822400 | 未回声 | 请求已显式 |
| 16 | layoutNms | false | 未回声 | 被忽略/不暴露 |
| 17 | restructurePages | false | 未回声 | 被忽略/不暴露 |

**服务端实际 model_settings（E1）**：
```json
{"use_doc_preprocessor": false, "use_layout_detection": false,
 "use_chart_recognition": false, "use_seal_recognition": false,
 "use_ocr_for_image_block": false, "format_block_content": false,
 "merge_layout_blocks": true,
 "markdown_ignore_labels": ["number","footnote","header","header_image","footer","footer_image","aside_text"],
 "return_layout_polygon_points": true}
```
差异：`mergeTables`→`merge_layout_blocks`；`relevelTitles/layoutNms/restructurePages` 未被服务端回显；`layoutShapeMode` 不直接回显，E3=rect 时 `return_layout_polygon_points` 变为 false；`temperature/topP/minPixels/maxPixels/repetitionPenalty` 不在回声结构中（服务端接受但未返回）。

## 2. 等价性（E0 vs E1，关键）

- E0：旧 10 字段 payload 重跑（同 8 页、同条件）；E1：显式 17 字段（默认值对齐）。
- **lines 逐页逐行完全一致：8/8 页，0 diff**；文本级标点指标完全相同：
  `TP 286 / FP 53 / FN 36 / P 0.8437 / R 0.8882`。
- 结论：显式 17 字段默认值与当前服务端生效行为等价，可安全替换；`mergeTables=true`/`layoutNms=false`/`restructurePages=false` 等值未改变输出。

## 3. 新旋钮 E2/E3

| 组 | 变更（相对 E1） | lines vs E1 | TP | FP | FN | P | R |
|---|---|---|---:|---:|---:|---:|---:|
| E1 | 显式 17 字段基线 | — | 286 | 53 | 36 | 0.8437 | 0.8882 |
| E2 | `useSealRecognition=true` | **0 diff** | 286 | 53 | 36 | 0.8437 | 0.8882 |
| E3 | `layoutShapeMode=rect` | **0 diff** | 286 | 53 | 36 | 0.8437 | 0.8882 |

- E2：服务端回声 `use_seal_recognition=true`，但 lines/标点指标无任何变化 → **对本项目本样本无效**（已排除）。
- E3：`layoutShapeMode=rect` 导致服务端 `return_layout_polygon_points=false`，但 lines/标点指标无变化 → **本样本无效**（已排除；不改变默认 auto）。
- 按类（period/quote/colon/comma/bracket…）E2/E3 与 E1 逐类完全相同（见 `output/ghbq/ocr_payload_exp/*/lines.json` + 评测脚本）。

## 4. 判定线

1. E1 vs E0：**等价**（0 页 diff，P/R 相同）→ 通过。
2. E2/E3：R 提升 0pp（<3pp），P 不变 → **不判可用**；如实记录「两个字段对本项目样本无效，已排除」。
3. 未改默认参数（仍 maxPixels 2822400 / min 147384 / orientation 0 / unwarp 0 / layoutShape auto）；未创建 data 覆盖。

## 5. 输出

- `output/ghbq/ocr_payload_exp/E0/lines.json`（旧 payload 重跑）
- `output/ghbq/ocr_payload_exp/E1/lines.json`（17 字段显式）
- `output/ghbq/ocr_payload_exp/E2/lines.json`（seal=true）
- `output/ghbq/ocr_payload_exp/E3/lines.json`（layoutShape=rect）
- 每组另存 `request_payload.json` / `server_model_settings.json`；jobId 见各组 `jobs.json`（E0 `114056797615874048`、E1 `114057079388958720`、E2/E3 见各自 jobs.json）。

## 6. 复现

```bash
# E1（E0 用旧 payload 重跑；E2 前加 OCR_SEAL_RECOGNITION=1；E3 加 --ocr-layout-shape rect）
/usr/bin/python3 src/tools/ocr_book.py --book ghbq --input source_pdf/ghbq.pdf \
  --out-dir output/ghbq/ocr_payload_exp/E1 --pages 14,15,23,27,30,50,80,100 \
  --pages-per-batch 8 --mode spotting --token-file /tmp/paddle_token
# 文本级评测：gold 8 页文本 + 各组 lines.json，调 punct_bench.sequence_eval
```

## 7. 限制

- 只 8 页、只 ghbq、只 spotting；未验证 layout 模式（`useLayoutDetection=true` 时 `promptLabel` 被忽略，需另测）。
- 服务端只回显部分字段；未回显字段的“实际生效”只能由输出等价性间接证明（E1=E0）。
- 本实验未重建 PDF；t264 已证横排渲染丢标点=0，故 lines 文本级评测≈产物标点。
