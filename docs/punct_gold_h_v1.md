
## t274 最终基线（2026-11-12，最终产物 ghbq_final_v2）

- gold_sha256：`8423a6a8fa2f0a156c8aad1aa45a37d486c30c16c1943b1e6dde02d7352a2df4`
- product_sha256：`56d53fda6a190b0172fa856abea09d6184e947a1f09500bb23b701c5fe36b7b1`
- ghbq 8页：TP282/FP51/FN40 **P0.8468/R0.8758**（旧 244/51/78 P0.8271/R0.7578）
- unscorable=[]；order_swaps=1；by_class 见 `docs/ghbq_baseline_v2.md`
- 注意：该产物为 **no-go 候选**（p31–39 ASCII形态回退、p86 等 worse 页14）；不替换旧基线。

## t264 修订（2026-11-12，取代本文件旧基线数字）

- gold 已修 F2：ASCII `()` 归一为全角 `（）`（bracket_present）；《》仍按 spec 为 booktitle，不冒充 bracket。
- gold 已修 F3：uncertain 改为正文位置级（每页 1 条，pos 指向该页实际引号/标点）。
- 最终 gold_sha256：`8423a6a8fa2f0a156c8aad1aa45a37d486c30c16c1943b1e6dde02d7352a2df4`。
- **最终基线（以此为准）**：ghbq TP244/FP51/FN78 P0.8271 R0.7578；wz4 TP447/FP123/FN99 P0.7842 R0.8187。
- 与 t262 独立复跑差异：gold 括号归一化后 wz4 bracket 从 0 列变为 7 条，故不是旧数字；详见 `docs/punct_h_fn_rootcause.md`。
- F1 的旧数字（ghbq 0.8136/0.7477、wz4 0.7474/0.8008）已作废，不再使用。
# 横排标点 gold v1（provisional）与首份横排基线（t261）

## 页集（固定）

**ghbq 8 页**：p14（开篇章标题+正文）、p15（开篇正文，异常序号页）、p23（中段正文，异常序号页）、p27（中段正文，异常序号页）、p30（中段正文）、p50（中段正文）、p80（书末正文）、p100（书末正文）。
**wz4 8 页**：p10（开篇“写作说明”正文）、p50（开篇正文）、p100（中段正文）、p200（中段正文）、p500（中段正文）、p341（**脚注页/已知异常页**）、p400（书末正文）、p600（书末正文）。

选择理由：均为正文页（有标点、非封面/版权/图版页）；覆盖开篇/中段/书末；ghbq 含 p15/p23/p27 三个序号异常页，wz4 含 p341 脚注异常页。

## 转录方法与限制（重要）

- 源图：`source_pdf/<book>.pdf` 渲染 200dpi 到 `/tmp/gold_h/<book>_p####.png`（裁片路径在报告末尾）。
- **未打开** `output/` 产物 PDF、任何 `_ocr_*` lines、任何 `punct_eval` 产物作为转录参考。
- 实际流程：源图 200dpi → **独立 tesseract chi_sim（psm6）基线** → 全角标点归一化 → 对标题/引号/明显错字做人工订正（`浆病→弊病` 等）。
- **这不是逐字人工复核的 gold**：tesseract 仍有错字、引号配对错误；每页 `uncertain` 已登记引号配对歧义（每页 1 处）。因此本文件标记为 **provisional**，可用于首份量化基线，不能用作最终阈值标定。

## 每页标点计数（gold）

| 书-页 | glyphs | period | comma | colon | semicolon | quote_open | quote_close | enumeration_comma | booktitle | other | uncertain |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ghbq p14 | 392 | 6 | 14 | 0 | 0 | 3 | 1 | 1 | 0 | 0 | 1 |
| ghbq p15 | 480 | 9 | 15 | 1 | 0 | 11 | 4 | 0 | 1 | 0 | 1 |
| ghbq p23 | 438 | 6 | 12 | 0 | 0 | 12 | 6 | 0 | 2 | 0 | 1 |
| ghbq p27 | 456 | 11 | 13 | 1 | 0 | 8 | 5 | 1 | 2 | 0 | 1 |
| ghbq p30 | 423 | 10 | 15 | 0 | 0 | 7 | 6 | 2 | 2 | 0 | 1 |
| ghbq p50 | 465 | 9 | 21 | 2 | 0 | 6 | 4 | 1 | 0 | ellipsis 2 | 1 |
| ghbq p80 | 495 | 10 | 26 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 1 |
| ghbq p100 | 466 | 11 | 17 | 2 | 0 | 7 | 4 | 1 | 0 | 0 | 1 |
| wz4 p10 | 634 | 13 | 20 | 1 | 0 | 9 | 3 | 7 | 2 | question3 | 1 |
| wz4 p50 | 928 | 20 | 34 | 5 | 2 | 7 | 4 | 1 | 7 | question1 | 1 |
| wz4 p100 | 857 | 14 | 25 | 3 | 0 | 2 | 1 | 1 | 4 | question1 | 1 |
| wz4 p200 | 891 | 18 | 41 | 0 | 0 | 3 | 2 | 0 | 3 | 0 | 1 |
| wz4 p500 | 834 | 18 | 32 | 1 | 0 | 5 | 3 | 1 | 5 | 0 | 1 |
| wz4 p341 | 885 | 18 | 31 | 3 | 0 | 2 | 1 | 4 | 5 | question1 | 1 |
| wz4 p400 | 887 | 14 | 35 | 4 | 1 | 2 | 3 | 0 | 5 | question1 | 1 |
| wz4 p600 | 889 | 17 | 38 | 3 | 2 | 6 | 5 | 0 | 8 | question1 | 1 |

（quote/booktitle 因 tesseract 配对不稳定出现开闭数不等；这是 uncertain 的直接证据，不掩盖。）

## 首份横排标点基线（punct_eval --mode sequence）

产物 sha256：
- ghbq `output/ghbq_full/ghbq_p97v2.pdf` = `cd397d2c947430b444cfcd9266e4b9cb7212c48a7a222d99c9d38579841ff787`
- wz4 `output/wz4/wz4_s4.pdf` = `7f76a142668af90a2a0c1301685d4ef67ff867673c37ecb98479fbea44f5b21d`

| 书 | 页 | TP | FP | FN | P | R | unscorable | order_swaps |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| ghbq | 8 | 240 | 55 | 81 | **0.8136** | **0.7477** | [] | 1 |
| wz4 | 8 | 426 | 144 | 106 | **0.7474** | **0.8008** | [] | 0 |

### ghbq by_class

| 类 | TP | FP | FN | P | R |
|---|---:|---:|---:|---:|---:|
| period | 68 | 4 | 4 | 0.9444 | 0.9444 |
| comma | 94 | 2 | 39 | 0.9792 | 0.7068 |
| colon | 5 | 0 | 1 | 1.0 | 0.8333 |
| enumeration_comma | 6 | 7 | 0 | 0.4615 | 1.0 |
| quote_open | 36 | 14 | 24 | 0.72 | 0.60 |
| quote_close | 25 | 26 | 11 | 0.4902 | 0.6944 |
| booktitle_open/close | 3/3 | 1/1 | 0/1 | 0.75 | 1.0/0.75 |
| ellipsis | 0 | 0 | 1 | 0 | 0 |

### wz4 by_class

| 类 | TP | FP | FN | P | R |
|---|---:|---:|---:|---:|---:|
| period | 99 | 36 | 33 | 0.7333 | 0.75 |
| comma | 241 | 10 | 15 | 0.9602 | 0.9414 |
| colon | 18 | 2 | 2 | 0.9 | 0.9 |
| semicolon | 5 | 0 | 0 | 1.0 | 1.0 |
| enumeration_comma | 14 | 21 | 0 | 0.4 | 1.0 |
| quote_open | 16 | 14 | 20 | 0.5333 | 0.4444 |
| quote_close | 9 | 25 | 13 | 0.2647 | 0.4091 |
| booktitle_open/close | 9/11 | 13/11 | 12/7 | 0.409/0.5 | 0.429/0.611 |
| question | 4 | 0 | 4 | 1.0 | 0.5 |
| ring/other | 0 | 5 | 0 | 0 | 0 |

## 与 wz7 竖排基线对比

竖排 wz7 8 页（历史序列口径）：P **0.9449** / R **0.9504**。
横排首份：ghbq P **0.8136** / R **0.7477**；wz4 P **0.7474** / R **0.8008**。
横排明显更低，主要损失在 **quote_open/quote_close、booktitle、enumeration_comma**，与 t257/t259 的“漏识/字形差异”结论一致。

## 自检

- `unscorable_pages=[]`（两书）
- `order_swaps`：ghbq **1**（OCR 行/列阅读序一次换位；wz4 0）。序列口径允许换位计数，但本 gold 为行序文本，未做逐 sw​ap 修正；报告如实登记。
- `uncertain` 总计 **16 页各 1 处**（≤3/页），全部为引号配对歧义；但 tesseract 的错字/漏字未逐处登记，这是 provisional 的主要限制。

## 已知限制

1. 本 gold 不是人工逐字复核；tesseract 错字、漏字、引号配对错误会直接影响 P/R，尤其 quote/bracket 类。
2. ghbq p15/p23/p27 是异常序号页/标题页，行切分与阅读序可能受 OCR 影响；ghbq order_swaps=1。
3. 未做人工裁片逐页对照；若用于最终阈值，必须先按 `uncertain`/抽样复核，或换成人工转录。
4. 未修改产品、data、现有 gold、punct_eval 口径；未 commit。

## 源图裁片路径

`/tmp/gold_h/ghbq_p0014.png` … `/tmp/gold_h/ghbq_p0100.png`；`/tmp/gold_h/wz4_p0010.png` … `/tmp/gold_h/wz4_p0600.png`（200dpi，源 PDF 渲染）。

## t276 最终基线（GO）

- product_sha256：`eba54007fae8f4739c9778b1c369d943b1dfc3bb703773d9074a67fa90ec570a`
- ghbq 8页：TP282/FP51/FN40 **P0.8468/R0.8758**（与 v2 标点相同；v3 修了形态）
- gold_sha256：`8423a6a8fa2f0a156c8aad1aa45a37d486c30c16c1943b1e6dde02d7352a2df4`
- 产物 `output/ghbq_full/ghbq_final_v3.pdf`；worse页5（p70等），已在 AGENTS #54 登记。
