# ghbq 原参数重跑重建：文本级 0.8882 vs 产品级 0.7578 落差验证（t272）

## 结论

**「按原参数重跑 OCR → 重建」确实能大幅提升产品级标点：R 0.7578 → 0.8758（+11.8pp），P 0.8271 → 0.8468（+1.97pp）。**

但新产物**不能直接替换** `ghbq_p97v2.pdf`：
- **p97 硬约束 FAIL**：新产物 p97 = 正常文本重排（image0、字号9.96–16.54pt），旧版 = 整页源图 image1 + 全文本1pt；钉图后 image1 但文本层 **0 字**；
- 94/59 页 diff 的严格逐页分类：better 18 / worse 11（X/Y=1.64，未达 3:1），非标点差异 40 页 / 87 字符；
- 因此结论是 **OCR 漂移收益真实，但产品替换需先修 p97 贴图与文本层**。

## 一、重跑（原参数，不改任何参数）

命令：

```bash
/usr/bin/python3 src/tools/ocr_book.py --book ghbq --input source_pdf/ghbq.pdf \
  --out-dir output/ghbq/rebuild_cur --pages 1-104 --pages-per-batch 10 \
  --mode spotting --token-file /tmp/paddle_token

/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq/rebuild_cur/ghbq_rebuild.pdf \
  --data-dir output/ghbq/rebuild_cur --skip-ocr --force
```

- payload：当前 `OCR_DEFAULTS`（max_pixels=2822400, min_pixels=147384, orientation=0, unwarp=0, layout_shape=auto）；**未使用 D 组/2×**。
- OCR 104 页：首轮 11 个 10 页 batch，其中 2 个服务 500；重试 2 个 + 补 p50/p70 两页；**共 14 次 API 调用**；墙钟约 7 分钟（02:00–02:07）。
- 构建：`fit_positional` two-pass，exit0；104 页。

## 二、产品级标点（同 gold/同口径）

gold：`src/test/bench/content_gold_h_v1.json`（sha `8423a6a8…`）；punct_eval sequence；ghbq 8 gold 页。

| 产物 | TP | FP | FN | P | R |
|---|---:|---:|---:|---:|---:|
| 旧 `ghbq_p97v2.pdf`（t264） | 244 | 51 | 78 | 0.8271 | **0.7578** |
| **新 `ghbq_rebuild.pdf`** | **282** | **51** | **40** | **0.8468** | **0.8758** |
| Δ | +38 | 0 | −38 | +1.97pp | **+11.80pp** |

by_class（新产物）：
- comma TP131/FP2/FN2（旧基线 comma TP94/FP?/FN?；新 comma 召回 0.985）
- quote_open 36/14/24；quote_close 29/22/7（与旧基线基本相同）
- period 68/4/4；colon 6/0/0；enumeration 6/7/0；bracket 0/0/1；ellipsis 0/0/1

**判定：新产物 R +11.8pp ≥ +5pp，零成本重跑收益成立。**

## 三、13pp 落差溯源（必须回答）

| 口径 | P | R | 说明 |
|---|---:|---:|---|
| 旧 OCR lines（11-09）文本级 | 0.8239 | **0.7702** | 旧 OCR 本身差 |
| 新 OCR lines 文本级 | 0.8437 | **0.8882** | 今天重跑（与 repeat1 完全一致） |
| 旧产物产品级 | 0.8271 | **0.7578** | 旧 lines + 构建 |
| 新产物产品级 | 0.8468 | **0.8758** | 新 lines + 构建 |

量化：
1. **旧 OCR 比今天差：+11.80pp**（0.7702→0.8882）——这是 13pp 落差的主因。
2. **构建/装配固定损失约 −1.24pp**（旧 0.7702→0.7578；新 0.8882→0.8758，两边几乎同幅）——来自产品级 reading-order/家具剔除/序列 gap 配对，不是 render_dropped；t264 的 render_dropped=0 仍成立。
3. **产品级 vs 文本级不是同一口径**：产品级少 1.24pp，而不是 13pp；把 0.7578 与 0.8882 直接比是把「旧 OCR 差」误算进「构建差」。

## 四、门禁与硬约束

新产物：
- 页数 **104 = 104**；gate **PASS**；pitch **97.9%**（旧97.9）、height97.9、overflow **0**、split0、missing0、blank2。
- typography：hard **0**、render **0**、compliance1.0；p11/p12 `toc_cont_indent`/`toc_number_overlap` warn 4 条（旧4条，无新增 hard）。
- GMPG：**0**。
- 字符量：旧 raw48149 / nospace43841；新 raw **47630** / nospace **43815**（raw −519，nospace −26）；p97 差异见下。
- **p97：
  - 旧：image1 + 文本 473 字，字号 1.0pt；页码85（图像）；
  - 新：image0 + 正常文本491字，字号9.96/12.85/16.54；页码85（文本层）；
  - 临时写 `data/ghbq/page_image_pages.json` 钉图重建：image1，但文本层 **0字**；不满足旧版「图+1pt文本」；
  - 对比图：`output/ghbq/rebuild_cur/compare_p97.png`、`compare_p97_pinned.png`。
- p12：新/旧文本基本一致，仍点线非三栏（TOC 渲染器问题，与本次 OCR 无关）；`toc_number_overlap` 仍存在（旧4条warn之一）。

## 五、新旧逐页 diff 定性

输出：`output/ghbq/rebuild_cur/diff_old_vs_rebuild.json`。

- diff 页 **59**（不是 94；94 是 D 组，本任务原参数不是 D）。
- 标点序列严格分类：**better 18 / worse 11**，X/Y **1.64**（未达 3:1）。
- 非标点差异 **40 页 / 87 字符**；字符总量 raw −519（主要 p97 文本层差异/行重排）。
- 典型 better：comma ASCII→全角（p14/p20/p80 等）；worse：p44/p50 `……→···`、p86 引号/逗号丢失、p28/p41 括号丢失、p104 引号/逗号重排；p97 归 other/p97 特例。
- 说明：严格序列分类会低估产品级 comma 收益（许多标点变化嵌在行重排/非标点 edit 中）；产品级 punct_eval 才是有坐标/阅读序的权威结论。

## 六、最终建议

**不要立即替换交付基线**，但保留重建收益：
1. 先把 p97 恢复为「整页贴图 + 可搜1pt文本 + 页码85」——当前贴图机制只回图不回文本，是产品侧缺口；
2. 修 p12 TOC 三栏/点线（旧问题，与新 OCR 无关）；
3. 修完后用 `output/ghbq/rebuild_cur/ghbq_spotting_lines.json` + `ghbq_spotting_coords.json` 重建，替换 `ghbq_p97v2.pdf`；
4. 重出基线：`docs/punct_gold_h_v1.md` 表（R 0.8758）、typography baseline、gate/report；
5. 若 p97/p12 不能先修，则**维持旧产物**，只把新 lines 作为下一次构建的输入，不发布。

## 七、自检

- 新产物 104=104，gate PASS，pitch97.9/overflow0/split0/missing0，GMPG0，typography hard0。
- 产品级 R .8758，明确高于旧 .7578 +11.8pp；落差主因是旧 OCR 差 +11.8pp，构建固定损失 −1.24pp。
- p97 硬约束 FAIL；因此**不建议直接替换**。
- 未改代码/gold/punct_eval；临时 page_image_pages.json 已删除；未 commit。
