# CONTENT_EVAL.md — 内容准确率评测契约（v1.1）

> **状态**：planned（本文件只定义契约；gold/评测器/阈值由 t111/t112 及后续实现）
> **类型**：governance（跨书、跨管线公共评测契约）
> **依据**：[PUNCT_EVAL.md](PUNCT_EVAL.md)（标点评测；内容评测与其并列）、[PUNCTUATION.md](PUNCTUATION.md)、[PIPELINE_BEHAVIOR.md](PIPELINE_BEHAVIOR.md)
> **关联实现（后续）**：`src/tools/punct_bench.py --content-gold`（现有 CER 原型）、`src/tools/content_eval.py`（规划）、`data/content_eval/`（gold/regression 数据）
> **版本**：v1.1（2026-11-08；t124 按用户决定修订回归门禁）—— v1.0 定义指标/归一化/回归清单/门禁；v1.1 将 t97 的 118 条外推错字降为诊断项，must-pass 改为 64 缺字 + 54 ring；**不改产品代码或渲染行为**
> **v1.1 修订原因**：用户选择 B 方案——优先可跑、覆盖后补；A 方案（materialize 118 后升为 must-pass）保留为 v2 升级路径。

---

## 0. 目的、边界与不可违背项

### 0.1 目的

`verify_vert` 的字符量/越界不能回答“内容对不对”；`punct_bench` 里虽有 CER/漏/错/多，但没有正式口径、归一化、回归清单和跨书门禁。
本 spec 定义一套**书无关、可重复、可审计**的内容准确率评测：

1. CER（字级编辑距离/真值字数，含插入/删除/替换分解）、漏字率、错字率、多字率；
2. **含标点**与**只算汉字**两栏；
3. gold 转录格式（`page/text/存疑字?/异体原样`）；
4. 归一化口径（必须评分前固定、可审计）；
5. must-pass 回归清单（64 确认缺字 + 54 battle4 ring）；118/4 只作诊断；
6. v1 20 页 gold + 回归；v2 全书系统抽样；
7. 跨书门禁（wz6/wz7/heldout）与不退化规则。

### 0.2 边界（不做的事）

1. **不做标点/结构评测**；标点归 [PUNCT_EVAL.md](PUNCT_EVAL.md)，内容评测只看字符序列。
2. **不按国标重排**；源书异体/旧字形/旧式标点原样进入 gold，归一化只按 §3 的固定 profile。
3. **不把“OCR候选”当“已确认错字”**；118 条 t97 外推只作诊断（§4.4）；只有 A 方案 materialize 后才考虑升 must-pass。
4. **不做自动修复**；v1 只输出指标/回归/gate；修复由后续流水线消费。
5. **不含书/页白名单**；页面来自 gold/采样清单数据；评测器不得写具体书页号。
6. **阈值不是书的参数**；初始 CER 阈值仅经验值，t111 跨书标定后版本化；不得把某本书最优值当通用值。

### 0.3 判据/数据/代码分离

| 层 | 放什么 | 不放什么 |
|---|---|---|
| 判据（spec/evaluator） | 指标定义、Levenshtein 成本、归一化 profile、阈值公式 | 具体书页/某页正文/某页 crop |
| 数据（gold/regression） | page/text/doubt/exclude/evidence；回归条目 | 把页面写进 evaluator |
| 代码 | 读取、归一化、编辑距离、统计、回归检查、输出 | 书专属阈值/页面白名单 |

---

## 1. 术语

- **page**：1-based 源页；gold 与产物按页序对齐。
- **gold text**：源页的**内容转录**（body + headings；排除页眉/页码/页脚/图像说明等重复家具，见 §2.3）。
- **doubt char**：gold 中无法确认的字符，用 `?` 标记；另在 `doubt_chars` 给位置/原因。
- **normalized text**：gold/pred 经固定 profile（§3）后的字符序列；所有指标只在其上计算。
- **Han**：CJK 统一表意文字（U+3400–4DBF、U+4E00–9FFF、U+F900–FAFF）；不包含标点、数字、拉丁、圈码。
- **N**：normalized gold 的字数（with_punct 或 han_only，见 §3.4）。

---

## 2. Gold 转录格式

### 2.1 顶层

```json
{
  "schema_version": "content-eval-v1",
  "dataset": {
    "id": "content-eval-v1-20p",
    "split": "wz6|wz7|heldout",
    "book_class": "has_frame|no_frame|heldout",
    "source_sha256": "<source pdf sha256>",
    "page_count": 20,
    "normalization_id": "N0_default",
    "gold_version": "2026-11-08.1",
    "frozen": true
  },
  "items": [
    {
      "page": 1,
      "scope": "body+headings",
      "text": "……源文轉錄，保留異體……",
      "doubt_chars": [
        {"pos": 12, "char": "?", "reason": "源墨模糊/OCR 不确定"}
      ],
      "exclude": [
        {"type": "header", "text": "金瓶梅"},
        {"type": "page_number", "text": "一四二"}
      ],
      "source": "source_pdf#p1",
      "crop": "crops/p1_body.png",
      "evidence": {"type": "manual", "reviewer": "R1", "reason": "人工转录 + 源图复核"}
    }
  ]
}
```

### 2.2 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `page` | ✓ | 1-based 源页 |
| `scope` | ✓ | v1 固定 `body+headings`；不含页眉/页码/页脚/图注/边注 |
| `text` | ✓ | 源文转录；**保留异体/旧字形/旧式标点**；不自动繁简/异体归一 |
| `doubt_chars` | 选 | 存疑字列表；`pos` 相对 `text`（0-based，含 `?`），`char` 固定 `?`，`reason` 记录 |
| `exclude` | 选 | 该页重复家具（header/page_number/footer/caption/marginalia）的文本；用于从产物中过滤；数据驱动，不硬编码 |
| `source` | ✓ | 源 PDF/页/裁片来源 |
| `crop` | 选 | 源图证据裁片；`source_ink`/manual 建议提供 |
| `evidence` | ✓ | `manual` / `source_ink` / `ocr_context` / `derived`；含 reviewer/reason 或 ink 特征 |
| `notes` | 选 | 歧义、版本、校订说明；不得写书页白名单 |

### 2.3 内容范围

- `text` 包含：正文、诗/词行、章题/小节标题、角色提示（“某某唱：”）、曲牌名/括号内文字；
- 不包含：书眉/页眉、页码、页脚/catchword、图像说明、边注（除非 `scope` 扩展，v2）；
- **页内顺序**：按源书阅读序（竖排右起列/横排行）拼接；保留源文标点/换行；
- **跨页**：gold 按页存储，不把跨页句子拼成一项；CER 也按页计算（跨页合并另有 PUNCT_EVAL/结构评测）。

### 2.4 存疑字与异体

- `text` 中不确定字符用 `?`，并在 `doubt_chars` 记录 `pos/char:"?"/reason`；
- `?` 不是正文内容：评分时从 gold 与 pred 的对应位置**屏蔽**（§3.5），`doubt_chars` 计数另报；
- **异体字原样**：`爲/為`、`眞/真`、`敎/教`、`綉/繡` 等按源书实际字形写入 `text`；默认**不归一**；
- 若需归一，只能使用 §3.3 的显式 profile，并在报告同时给 N0 与 profile 双结果；auto 门禁用 N0。

---

## 3. 归一化口径（评分前固定、可审计）

### 3.1 默认 profile `N0_default`

按以下顺序对 gold 与 pred 同时应用，**评分前只应用一次**：

1. **Unicode NFC**（只做组合字符规范化，不做繁简/异体映射）；
2. **删除所有空白**：空格、Tab、换行、全角空格 U+3000、段落空行；换行不产生字符、不产生边界；
3. **保留所有标点/符号/圈码/异体/繁体字形**；不做 OpenCC/繁简/异体替换；
4. **不跨页拼接**；每页独立；
5. **`?` 屏蔽**：gold `?` 从 CER 中删除，同时在 pred 同 `column/char_pos` 位置屏蔽一个字符（若存在）；`doubt_chars` 计数；
6. **页码/页眉/页脚**只在 gold `exclude` 指定时从产物中剔除；不按位置硬编码。

### 3.2 可审计记录

每次评分必须输出：

```
normalization_id: N0_default
unicode_version: <runtime>
strip_whitespace: true
variant_map: null
t2s: false
doubt_mask: same_cell
gold_normalized_sha256: ...
pred_normalized_sha256: ...
```

- 归一化函数/映射文件版本与 hash 必须固定；不得在评分中途改 profile；
- 报告必须给出 **gold/pred 归一化后 hash**，使结果可复现；
- `?` 屏蔽规则必须与 gold 位置一致；屏蔽数量 = `doubt_chars` 数。

### 3.3 可选 profile（不用于 auto 门禁）

| profile | 规则 | 用途 |
|---|---|---|
| `N1_variant` | 显式、冻结的异体字映射（如 `爲→為`） | 公平比较不同字形来源；必须给 map id/hash |
| `N2_t2s` | 显式 OpenCC t2s 版本（固定版本/映射） | 只作对照；不得替代 N0 |
| `N3_punct_strip` | 去掉标点（仅诊断） | 不作为 auto 门禁 |

> **默认 N0 不做繁简/异体统一**，因为本项目按源书还原；N1/N2 只作诊断，需在报告中同时给出 N0 与可选 profile 的 CER，
> 且 auto/门禁只看 N0。任何变体映射必须版本化、可审计，不能在某页/某书上开关。

### 3.4 含标点 / 只算汉字两栏

对同一 normalized text 分别计算：

| 栏 | 分母 N | 说明 |
|---|---|---|
| **with_punct** | 所有保留字符（汉字+标点+数字+圈码+拉丁） | 内容 + 标点整体保真；主口径 |
| **han_only** | 仅 Han 字符（§1） | 纯汉字内容准确率；标点不计 |

- 两栏都必须输出；**auto/门禁要求两栏都不退化**；
- `han_only` 不是“去掉标点后重新对齐再算”，而是先过滤 Han 再算编辑距离（口径固定）。

---

## 4. 指标

### 4.1 CER（字级编辑距离）

对 normalized gold `G`、pred `P`：

- 使用 **Levenshtein**，成本：插入=1、删除=1、替换=1；
- 由确定性的最优对齐得到 `I`（插入）、`D`（删除）、`S`（替换）；
- `N = len(G)`；
- `CER = (I + D + S) / N`；`N=0` 时 CER 记 `null`（不得记 0）；

### 4.2 漏字/错字/多字率

```
missing_rate = D / N       # 漏字：gold 有、pred 无
wrong_rate   = S / N       # 错字：gold 与 pred 不同（替换）
extra_rate   = I / N       # 多字：pred 多出
CER          = missing_rate + wrong_rate + extra_rate   # 同分母 N
```

- 三项都要输出；不得只报 CER；
- `S` 是替换；`D/I` 是插入/删除；对齐中 `replace` 长度不等时要拆分为 `S + D/I`（以 Levenshtein 成本为准）；
- 报告可同时给“页级宏平均”和“全书 micro 合计”；**门禁用 micro**（τ 页短页不放大）。

### 4.3 两栏与聚合

| 指标 | with_punct | han_only |
|---|---|---|
| `N/I/D/S/CER` | ✓ | ✓ |
| `missing_rate/wrong_rate/extra_rate` | ✓ | ✓ |
| `doubt_chars` | ✓（两栏同值） | ✓ |

- 按页、按 split、全书聚合；固定排序；
- 以 **micro 合计**作为书/门禁主指标：`ΣI/ΣN` 等，不用页均值掩盖长页；
- 同时给页级分布（中位/P95）用于抽样报告。

### 4.4 回归清单（must-pass + diagnostics）

回归不是“CER 好”；它是**已知内容点的硬断言**。v1.1 分两层：**must-pass（门禁）**与 **diagnostic（只进报告，不进 gate）**。

#### 4.4.1 must-pass（门禁，v1.1 = 64 + 54）

| 集合 | 来源/selector | 数量（v1.1 快照） | 通过条件 |
|---|---|---|---|
| `missing_char_confirmed` | `docs/vert_taskF_missed_fix.json`：`class=missing_char` 且同时有 `shape`/`complete` 字段 | **64** | 每个 expected `ch` 在产物页/列/pos 的 ±0.5 格内出现；缺一即 fail |
| `battle4_ring` | fix JSON 中 `ring_fix` 以 `battle4:` 开头的圈码修正 | **54**（快照） | 产物该位置圈码 number/cp 与 expected 一致；缺一即 fail |

> **64 的 selector**：当前 fix JSON 中 `class=missing_char` 且同时有 `shape` 与 `complete` 字段 = **64 条**；
> 这是 battle9d 的「58+6=64 确认口径」在数据里的可审计子集。不是把 160 条 `missing_char` 全算 must-pass。
> **54** 用 `ring_fix` selector（当前 54 条），包含 battle4 的 7 处高置信修正在内；不列具体页号。
> **must-pass 通过率必须是 64/64 + 54/54**；任何一条 fail → `REGRESSION_BLOCKED`，不得 auto/交付。

#### 4.4.2 diagnostic（只报告，不计门禁）

| 诊断项 | 来源 | 数量 | 处置 |
|---|---|---|---|
| `typo_t97_extrapolated` | t97：2,379 替换候选外推 ≈5% | **118**（外推，非逐条确认） | 只进报告/趋势；**不触发** `REGRESSION_BLOCKED`；**不要求 materialize** |
| `typo_t97_sample_confirmed` | t97 66 条样本中的 4 条真 OCR 错字（#01/#15/#26/#36） | **4** | 只进报告/人工观察；同样不计门禁 |

- **118/4 只进报告**：可给“expected 出现/原 wrong 不在”的诊断命中数、按页清单、置信区间；但不参与 auto/manual/drop 判定；
- **118 未 materialize 不再触发 `REGRESSION_BLOCKED`**：v1.1 的评测器只要求 64/54 的 materialized selector；
  118 缺 manifest 时输出 `diagnostics.typo_t97.status = "unmaterialized"`，继续评测/继续门禁；
- 4 条样本确认是真错字，但仍是“抽样确认”，不是全量清单；因此也只作诊断，不升级为 must-pass；
- **不得把 118 当 118 条已确认**；报告必须标注“外推/建议抽审”，不能写成 must-pass 数字。

#### 4.4.3 回归通过口径

1. **must-pass**：`missing_char_confirmed` 64/64 + `battle4_ring` 54/54；**必须全过**；
2. **diagnostic**：118/4 只报告，不参与 pass/fail；
3. 不得新增“已确认 must-pass 点被改回错误”的条目；
4. 任一 must-pass fail → **`REGRESSION_BLOCKED`**；diagnostic fail 不触发；
5. 回归与 CER 分开报告；回归全过但 CER 高仍可能 manual/drop；CER 好但 must-pass fail 直接拒绝。
6. **`REGRESSION_BLOCKED` 仅在 64/54 must-pass fail 时触发**；118/4 diagnostic 永不触发。若 64/54 manifest 缺失，结果为 `unscored`（不得 auto），但不得把 118 计入 blocked 原因。

#### 4.4.4 Manifest 字段与 A/B 方案

```json
{
  "id": "missing-pX-c3-q3-竊",
  "source": "fix_json|battle4|t97",
  "page": 1, "column": 3, "char_pos": 3,
  "kind": "missing_char|ring|typo",
  "expected": "竊",
  "wrong": "",
  "evidence": {"type": "source_ink", "crop": "crops/pX_c3.png", "reviewer": "..."},
  "must_pass": true
}
```

- `must_pass=true` 只允许 64 missing +54 ring（v1.1）；t97 条目 `must_pass=false`，标 `diagnostic`；
- Manifest 是**数据**：页面/条目在 JSON；evaluator 只按 selector/位置匹配，不得写页面白名单；
- **B 方案（v1.1 当前）**：118/4 诊断；门禁 64+54；优先可跑。
- **A 方案（v2 升级路径）**：逐条 materialize 118（可选连同 4 条样本确认）为 `must_pass=true`；
  届时门禁改为 64+118+54（或经复审后的确认子集），并重跑 baseline/heldout；未升级前不得把 A 方案数字写进 v1.1 门禁。

---
---

## 5. 抽样与全量

### 5.1 v1（本契约 v1.1）

- **20 页 gold**（t111）：8 wz6 + 8 wz7 + 4 heldout（与 PUNCT_EVAL 同 split；具体页由数据给）。
- **回归清单**：§4.4 must-pass **64 + 54**；118/4 只作 diagnostic（不要求 materialize，不计门禁）。
- 指标：每页/每 split/总体 CER（两栏）、I/D/S、doubt；must-pass **64/64 + 54/54**；118/4 诊断另列。
- v1 不要求全书 CER；v1 的 20 页 gold 是**内容准确率**的基线，不是全书抽样。

### 5.2 v2（全书抽样）

- **系统抽样**：每 20 页抽 1 页（`page_id % 20 == 1` 的**数据清单**，由 sampling manifest 给；不在 evaluator 硬编码），
  v2 至少 20 页，目标 ≈1748/20≈**88 页**；按书/部分层（首卷/中卷/末卷/影印页区）各保底。
- **分层**：start/mid/end + 影印/图像页作为独立 stratum；图像页按“无正文”标记，不参与 CER 分母；
- **回归**：全书 must-pass **64+54** 仍逐条检查；118/4 仅诊断（若 v2 升 A 方案才把 118 纳入 must-pass）；
- **全量可选**：若人工/预算允许，全书 1748 页 CER；否则抽样页必须在 manifest 固定，不能事后挑页；
- **报告**：抽样页清单、每层页数、置信区间（Wilson/ bootstrap）与未覆盖页说明。

---

## 6. 跨书门禁

### 6.1 三档

| split | 书类 | 角色 |
|---|---|---|
| `wz6` | 有框书 | 不退化 |
| `wz7` | 无框书 | 不退化 |
| `heldout` | ≥2 本未见书/风格 | 泛化；禁止调参 |

- split 是数据标签，不是页面白名单；heldout 页密封；轮换规则同 PUNCT_EVAL §5。
- 任何内容修复/模型/规则改动必须三档重跑；**任一档退化即拒绝**，不得用其他档提升抵消。

### 6.2 初始阈值（v1.1，**待 t111 标定**）

| 指标 | auto | manual | drop |
|---|---|---|---|
| `CER_with_punct` | ≤ 0.020 | ≤ 0.050 | > 0.050 |
| `CER_han_only` | ≤ 0.015 | ≤ 0.040 | > 0.040 |
| `missing_rate` | ≤ 0.010 | ≤ 0.030 | > 0.030 |
| `wrong_rate` | ≤ 0.010 | ≤ 0.030 | > 0.030 |
| `extra_rate` | ≤ 0.005 | ≤ 0.020 | > 0.020 |
| must-pass 回归 | **64/64 + 54/54** | 同左（不允许部分） | 任一 fail → REGRESSION_BLOCKED / REJECT |
| diagnostic 118/4 | 只报告 | 只报告 | **不计门禁**；未 materialize 不触发 REGRESSION_BLOCKED |

- 阈值为**通用起点**，不是 wz6/wz7 的最优值；t111 用 20 页 gold 标定，t111 报告给 baseline 后修订 v1.2；
- 两栏阈值独立；auto 需要两栏都满足 + must-pass 64/54 全过；118/4 diagnostic 不参与；
- 单页 gold 少于 200 字（短页/诗页）不单独 auto；split 页数<4 不 auto。

### 6.3 不退化（vs frozen baseline）

1. worst-split `CER_with_punct` / `CER_han_only` 上升 ≤ **0.2pp**；
2. `missing_rate/wrong_rate/extra_rate` 上升 ≤ **0.2pp**；
3. must-pass 条目数不得减少（64/54）；任何 must-pass fail 即 `REGRESSION_BLOCKED`；118/4 诊断不计；
4. heldout 两栏 CER 不得上升；heldout 新增 must-pass fail 直接阻断；118/4 诊断不阻断；
5. 阈值变更必须附 baseline/候选的 by_split/by_class/page 表与 gold/regression hash；
6. 无 baseline 时只能 `unscored/manual`，不得 auto。

- 结论：`CONTENT_AUTO_PASS` / `CONTENT_MANUAL_ONLY` / `CONTENT_REJECT` / `REGRESSION_BLOCKED`。
- 与 PUNCT_EVAL §6 并列，不互相替代；PUNCT 不退化不能抵消 CONTENT 退化，反之亦然。

---

### 6.4 data_missing 输入侧诊断（provisional）

当标点/内容指标偏低时，门禁须先区分「上游 OCR 数据缺失」与「产品/渲染回归」：

- 判据：`product_punct/gold_punct ≤ 0.75`、`input_punct/gold_punct ≤ 0.75`、去标点 anchor 相似度中位 `≥ 0.80`
  → `data_missing`（上游 OCR 缺标点；门禁 MANUAL_ONLY 并注明，不按产品 REJECT）；
- 若 `input_punct/gold_punct > 0.75` 而产物低 → `product_regression`（产品 REJECT）；
- 阈值 0.75/0.80 为 provisional（待 t111 标定），与 §6.2 阈值同源登记。

## 7. 评测器接口（v1 草案）

```bash
/usr/bin/python3 src/tools/content_eval.py \
  --gold data/content_eval/gold_v1_20p.json \
  --regression data/content_eval/regression_v1.json \
  --pdf output/wz7_full/wz7_full_v50.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --out-json /tmp/content_eval.json \
  --out-csv /tmp/content_eval.csv
```

- 输入：gold（§2）、regression manifest（§4.4）、产物 PDF + coords/lines；
- 输出：JSON（normalization、by_page、by_split、two_columns、regression、gate）+ CSV（split,page,metric,value）；
- `--normalization N0_default` 固定；可选 `N1/N2` 只诊断，不能替换 N0 门禁；
- 退出码：0 完成；2 schema/输入不可读；3 页对齐失败；
- 只读；不联网/API；不改 PDF/data/output。
- v1 实现可复用现有 `punct_bench.eval_content` 原型，但必须补：Levenshtein I/D/S、两栏、doubt mask、回归、normalization hash；
  现有 `difflib` 口径只能作参考，不得直接当 v1 最终门禁。

---

## 8. 治理自检

| 检查 | 结果 |
|---|---|
| CER + I/D/S、missing/wrong/extra、两栏 | ✓ §4：CER=(I+D+S)/N；三项 rate；with_punct/han_only 两栏 |
| gold 格式 page/text/存疑字/异体原样 | ✓ §2：text/doubt_chars/?/exclude；异体不归一 |
| 归一化固定可审计 | ✓ §3：N0 顺序、NFC、去空白、不繁简/异体、hash、doubt mask；N1/N2 仅诊断 |
| 64+54 must-pass；118/4 diagnostic | ✓ §4.4：64 selector + 54 ring 硬门禁；118/4 只报告、未 materialize 不 blocked；A 方案 v2 |
| v1 20 页 + v2 全书抽样 | ✓ §5：20 页 gold+回归；v2 每20页抽1、≈88页、分层、manifest |
| 跨书门禁 wz6/wz7/heldout | ✓ §6：CER 阈值/不退化/REGRESSION_BLOCKED；与 PUNCT_EVAL §6 并列 |
| 书无关/无页面白名单/阈值非书专属 | ✓ 全文无具体书页白名单；阈值标注 t111 标定；页面来自数据 |
| 只写 spec | ✓ 本文件只新增 spec；未改产品代码/数据；未 commit |

---

## 9. 版本与后续

| 版本 | 内容 | 状态 |
|---|---|---|
| v1.0 | CER/I/D/S、两栏、N0、64/118/battle4、20页+回归、跨书门禁、接口草案 | 已被 v1.1 取代 |
| **v1.1（本文件）** | B 方案：must-pass=64 缺字+54 ring；118/4 诊断；A 方案留 v2 | **planned** |
| v1.2（t111） | 20页 gold + 64/54 regression materialize + N0 hash + 阈值标定 + baseline | 待做 |
| v2 | 全书抽样/全量、A 方案 materialize 118、N1/N2 对照、自动修复接入 | 待做 |

**t111/t122 交付物**：`data/content_eval/gold_v1_20p.json`、`regression_v1.json`（must-pass 64+54；diagnostic 118/4）、
`src/tools/content_eval.py`、`docs/content_eval_baseline_v1.md`（阈值/两栏/回归/heldout + 归一化 hash）。
本 spec 只锁契约，不实现。
