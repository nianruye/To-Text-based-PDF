# 横排标点 gold v1 矛盾集裁决（t262）

> 验收人：验证评审员；对象：t261 `content_gold_h_v1.json`（16 页，tesseract provisional）与 t261 基线
> 日期：2026-11-12 00:47–02:05；**只读审查，不改 gold/产品/punct_eval，未 commit**
> 结论：**FAIL（F1 基线不可复现；F2 bracket 类系统性漏记/抽样覆盖不足；F3 uncertain 无定位）**。
> 回答：横排 R 0.75 vs 竖排 0.95 的差距**不能全部归因于 gold**；即使按样本修正，真实 R 仍约 0.75–0.83，显著低于 0.95。

## 1. 矛盾集与基线复核（F1 blocker）

按 t261 的命令独立重跑（同一产物 sha256、同一 gold、同一 coords/lines）：

```bash
# ghbq
/usr/bin/python3 src/tools/punct_eval.py --mode sequence \
  --gold src/test/bench/content_gold_h_v1.json \
  --pdf output/ghbq_full/ghbq_p97v2.pdf \
  --coords output/ghbq_full/_ocr_ghbq/ghbq_spotting_coords.json \
  --lines output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json \
  --book ghbq --out-json /tmp/t262_ghbq_eval.json
# wz4 同理：output/wz4/wz4_s4.pdf + data/wz4/wz4_spotting_{coords,lines}.json
```

| 书 | t261 报告 | 独立复跑 | 差异 |
|---|---|---|---|
| ghbq | TP240 / FP55 / FN81；P **0.8136** / R **0.7477** | TP**244** / FP**51** / FN**77**；P **0.8271** / R **0.7601** | +4 / −4 / −4 |
| wz4 | TP426 / FP144 / FN106；P **0.7474** / R **0.8008** | TP**440** / FP**130** / FN**92**；P **0.7719** / R **0.8271** | +14 / −14 / −14 |

- 产物 sha256 与 t261 报告完全一致（ghbq `cd397d2c…`、wz4 `7f76a142…`）；gold 当前每页标点计数与 t261 报告表一致。
- 已排除 `PYTHONHASHSEED`（0/1/42 结果相同）、raw/noquote/quote-par 变体；均无法复现 t261 数字。
- 最可能原因：**t261 报告是 gold 最终引号/人工订正前的旧评测结果**（报告与 gold 同时间落盘但未重跑），或评测使用了未落盘的中间 gold。无论哪种，**t261 基线不可作为可信基线**（F1）。
- 因此「FN/FP 数量与 t261 一致」不成立；矛盾集只能按独立复跑的 244/51/77（ghbq）与 440/130/92（wz4）为准。

## 2. 16 页独立源图转写核对

源图：`/tmp/gold_h/<book>_p####.png`（200dpi，与 t261 相同 16 页）。独立重新跑 tesseract（psm6）+ 全角归一化 + ASCII 引号按奇偶配对；不读取 t261 文本作为转写结果，仅用于逐页对照。

| 页 | t261 标点计数（P/C/Co/…） | 本次独立计数 | 差异 |
|---|---|---|---|
| ghbq p14 | 6/14/0 | 6/14/0 | 无 |
| ghbq p15 | 9/15/1 | 9/15/1 | 无 |
| ghbq p23 | 6/12/0 | 6/12/0 | 无 |
| ghbq p27 | 11/13/1 | 11/13/1 | 无 |
| ghbq p30 | 10/15/0 | 11/15/0 | period +1（ASCII 小数点） |
| ghbq p50 | 9/21/2 | 9/21/2 | 无 |
| ghbq p80 | 10/26/0 | 11/26/0 | period +1（`3.5` 小数点） |
| ghbq p100 | 11/17/2 | 11/17/2 | 无 |
| wz4 p10 | 13/20/1 | 14/20/1 | period +1（ASCII 点） |
| wz4 p50 | 20/34/5 | 21/34/5 | period +1 |
| wz4 p100 | 14/25/3 | 16/25/3 | period +2 |
| wz4 p200 | 18/41/0 | 18/41/0 | 无 |
| wz4 p500 | 18/32/1 | 18/32/1 | 无 |
| wz4 p341 | 18/31/3 | 22/31/3 | period +4 |
| wz4 p400 | 14/35/4 | 15/35/4 | period +1 |
| wz4 p600 | 17/38/3 | 17/38/3 | 无 |

（P=period，C=comma，Co=colon；其余类经 ASCII 引号配对后逐类相等；booktitle/enumeration 也一致。）

### 2.1 11 个 period 差异逐处裁决

均为 tesseract 输出的 **ASCII `.`** 被本次天真归一化为 `。`，源图实际是小数点/分隔点/西文点，**t261 保留 `.` 是对的**：

| 页 | 上下文 | 源图裁片 | 裁决 |
|---|---|---|---|
| ghbq p30 | `纲领性声明 .` / 多处英文点 | `/tmp/t262_crops_conflict/ghbq_p30_*.png` | t261 对 |
| ghbq p80 | `3.5 万党员` | `/tmp/t262_crops_conflict/ghbq_p80_1.png` | t261 对（3.5） |
| wz4 p10 | `……根本属性. 意识` | `/tmp/t262_crops_conflict/wz4_p10_*.png` | t261 对（西文点） |
| wz4 p50 | `行政形式 . 立法形式` | `/tmp/t262_crops_conflict/wz4_p50_*.png` | t261 对 |
| wz4 p100 | `内容的. 抽象的. 荒诞无移` | `/tmp/t262_crops_conflict/wz4_p100_2.png` | t261 对（点分隔） |
| wz4 p341 | `资产阶级. 小资` / `党章. 党纲` / `完整的. 善于` / `影响。最有…` | `/tmp/t262_crops_conflict/wz4_p341_*.png` | t261 对（大部分是 `.`；`影响。` 需人工复核） |
| wz4 p400 | `民主”.@` | `/tmp/t262_crops_conflict/wz4_p400_7.png` | t261 对（`.@` 注码） |

**结论**：16 页逐类标点计数在「引号按奇偶配对 + ASCII 点不误归为 `。`」后与 t261 **全部一致**；t261 的 period/comma/colon/enumeration/booktitle 计数可信。

## 3. 抽样裁决（155 条，六类）

样本：每页 8 条 + 补足 colon/quote/bracket，共 **155 条**；裁片 `/tmp/t262_crops/*.png`，按 4×4 拼图 `/tmp/t262_sheets/sheet_01..10.png`。

| 类 | 样本数 | 与 t261 一致 | gold 缺失/错 | 一致率 |
|---|---:|---:|---:|---:|
| comma | 57 | 57 | 0 | 100% |
| period | 31 | 30 | 1（`3.5` 等 ASCII 点，t261 对） | 96.8% |
| colon | 15 | 15 | 0 | 100% |
| quote_open | 15 | 11 | 4（裁片红框错位，行上下文可见引号） | 73.3%→复核后15/15 |
| quote_close | 15 | 10 | 5（同上） | 66.7%→复核后15/15 |
| bracket（含 booktitle） | 15 | 8 | **7 全缺** | **53.3%** |
| enumeration_comma | 6 | 4 | 2（行映射误） | 66.7%→复核后6/6 |
| question/other | 1 | 1 | 0 | 100% |

- **bracket 类系统性缺失**：product 有 `（）` 的 7 处样本（wz4 p100/p341/p600 等），t261 gold **一个都没有**（gold 表也无 bracket 列）。这是 tesseract 漏识/归一化未补，属 **gold 系统性错误**；不是抽样噪声。
- quote 4+5 处经裁片上下文复核为**行/坐标映射误**（源图有引号，gold 也有该行引号），不是 gold 错；但自动一致性算法把它们记为 gold_missing，说明按行对齐的自动裁决不可靠。
- enumeration 2 处同理。
- 有效一致率（人工复核后）：**148/155 = 95.5%**，刚过 95% 线；但 **bracket 类 0/7 全错**，且 bracket 样本仅 7 条（<15 的硬要求），不能据此判整体 PASS。
- 155 条裁片/拼图均落盘；逐条状态在 `/tmp/t262_sample_status.json`（含 consistent/gold_missing）。

## 4. 转录纪律核查

1. **gold 是否照抄产物**：16 页 gold 文本与产物文本层均**不相同**（去空白相似度 0.931–0.996；无逐字全等页）。没有「逐字照抄」证据；但 t261 的 tesseract 输出与产物 OCR 都可能受同一源图影响，不能完全排除间接污染。
2. **uncertain 条目**：16 页 `uncertain` 均为 `{pos:0,char:“,reason:“tesseract 引号配对存在歧义…”}`，只有 **1 个页级占位**，没有具体位置/上下文；无法按「抽查 5 处具体 uncertain」核验，属**登记不合格**（F3）。源图上引号确实存在配对歧义，但登记方式不足以支持复核。
3. **系统性漏记模式**：product 有、gold 无的 bracket 全部缺失（7/7），且 gold 标点表没有 bracket 行；说明 gold 对括号类**系统性漏记**。这与 tesseract 不识别/不归一化括号一致，不能证明参考了产物，但证明 gold 不能作为 bracket 类基准。
4. 引号类 t261 已做 ASCII→全角配对，但与产物引号仍有大量 FP/FN；属 tesseract 配对/OCR 差异，需人工 gold。

## 5. 修正后的基线区间

以独立复跑为下界（t261 报告更低，取 min），以「样本有效错误率 4.5%（7/155，全是 bracket）」为上界修正：

- 召回上限：`R_high = R + (1−R)×0.045`
  - ghbq：0.7601 + 0.2399×0.045 = **0.7709**
  - wz4：0.8271 + 0.1729×0.045 = **0.8349**
- 下界取 t261 报告：ghbq **0.7477**、wz4 **0.8008**。

| 书 | t261 R | 修正区间 R | 竖排 wz7 R |
|---|---:|---:|---:|
| ghbq | 0.7477 | **[0.748, 0.771]** | 0.9504 |
| wz4 | 0.8008 | **[0.801, 0.835]** | 0.9504 |

**结论**：即使把样本中可确认的 gold 错误全部修正，横排 R 仍 ≤0.835，和竖排 0.9504 差 **0.115 以上**；「横排比竖排差」成立，但 t261 的绝对值不可靠（基线本身不可复现）。

## 6. 建议

1. **需人工 gold**：t261 gold 不能作最终阈值。建议重做 16 页人工逐字标点 gold（括号/引号必须逐处看源图），工作量估算：16 页 × 约 800 字 = 1.28 万字，标点约 1,900 个；转录 15 min/页 = 4h，复核/裁片裁决 4h，合计 **约 1 人日**；若只做 8 页分层抽样，**约 0.5 人日**。
2. 人工 gold 完成前，横排基线只报 **区间**，不报单点 P/R；bracket 类单列，不与竖排直接比。
3. 修 t261 报告：用最终 gold 重跑 punct_eval 并记录 gold sha256；当前报告数字与交付 gold 不匹配（F1）。
4. t261 uncertain 必须写到具体 `{page,line,char,bbox}`，不得用页级占位（F3）。

## 7. 裁决

**FAIL（F1/F2/F3）**：
- F1 blocker：t261 基线不可复现（TP/FP/FN 差 4 和 14），报告数字与交付 gold 不匹配；不能作为「横排真比竖排差多少」的定量依据。
- F2 high：bracket 类 7/7 系统性缺失，gold 对括号无覆盖；抽样一致性 95.5% 刚过线但 bracket 类 0%，不能判 PASS。
- F3 medium：uncertain 为页级占位（pos=0），无法逐处复核。
- 结论：横排真实 R 区间 ghbq [0.748,0.771]、wz4 [0.801,0.835]，仍显著低于竖排 0.9504；需人工 gold（约 1 人日）后再定阈值。
