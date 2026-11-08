# content_eval v1 · 内容 CER 两栏 + 回归 must-pass（PDF-only / t132 修复版）

> 任务：t122 → t125 → t128 → **t132 repair**：按 CONTENT_EVAL v1.1 与 t130 审查修复 `_counts` 拆分/输出块、去静默回退、删死代码
> 执行：竖排工程师　日期：2026-11-08
> 证据：`src/tools/content_eval.py`、`src/test/unit/test_content_eval.py`、`tmp_vert/bench/content_v51_pdf.json/.csv`
> 约束：只读评测；不改产品代码/data；未 commit；无 token/网络/API。

## 0. 结论（v51 基线，t111 真 gold）

| 指标 | v51（8 个 wz7 gold 页） |
|---|---|
| **with_punct** | gold 3,912 字 / 距离 **376** / **CER 0.0961**；I=109、D=49、S=218 |
| **han_only** | gold 3,226 字 / 距离 **184** / **CER 0.0570**；I=96、D=40、S=48 |
| must-pass · missing_char_confirmed（64） | **64 / 64 = 1.000** ✅ |
| must-pass · battle4_ring（54） | **54 / 54 = 1.000** ✅ |
| **must_pass** | **True**（REGRESSION_BLOCKED 维持撤销） |
| diagnostic · t97（3 条真，i=26 已剔） | **0 / 3**（`status=unmaterialized`，118 外推未 materialize） |
| diagnostic · missing_char_all（160） | 70 / 160 = 0.4375（只诊断） |

> gold 已由 t111 落到 `data/punct_eval/content_gold_v1.json`（20 页混合：8 wz6 + 8 wz7 + 4 heldout，list 格式）；v51 按 `book=wz7` 过滤后评 **8 页**。均按页独立，不跨页拼接。

## 1. 指标（spec §3/§4，t132 修复）

1. **N0 归一化**：NFC → 去空白 → 不繁简/异体（`--normalize none` 默认）；`variant`/`simp` 仅对照列。
2. **`_counts` → `_edit_ops`（确定性 DP）**：按 Levenshtein 1/1/1 回填 **I（插入）/D（删除）/S（替换）**：
   - 不等长替换：`S = min(len_a, len_b)`，差额计入 I 或 D（不再把整段算成 `wrong`）；
   - `dist = I + D + S`；`N = len(gold)`；`CER = dist/N`；**N=0 → `cer=null`**（不记 0）。
3. **`?` 同位屏蔽（spec §3.1-5）**：gold `?` 删除；pred 在**同一序位**删除一个字符（若存在）；`doubt_chars` 计数。
4. **输出块**：overall/by_page 均含 `gold_chars/edit_distance/cer/insertions/deletions/substitutions` + `insertion_rate/deletion_rate/substitution_rate`（兼容旧 `missing/wrong/extra` 别名）；另出 `normalization_audit`（`normalization_id=N0_default`、`unicode_version`、`strip_whitespace`、`variant_map:null`、`t2s:false`、`doubt_mask:same_cell`、gold/pred 归一化 sha256）。
5. **PDF-only**：CER 与回归只读产物 PDF（`fitz rawdict` 逐字符+bbox）；**无 lines 回退**。`--lines` 仅为 argv 兼容保留（不参与计算）。
6. **失败语义**：PDF 不存在/gold 不可读 → exit 2；PDF 解析异常或无文本 → **exit 3（unscored）**，不得回退 lines。

## 2. 回归（spec §4.4 v1.1，PDF 口径）

| 集合 | selector | 数量 | 检查（PDF） | v51 |
|---|---|---|---|---|
| `missing_char_confirmed` | `missing_char` 且 `shape`+`complete` | 64 | `(source_x,source_y)±20pt` 邻域字符==期望 `ch`；缺失时 PDF 页文本 fallback | **64/64** |
| `battle4_ring` | `ring_fix` 以 `battle4:` 开头 | 54 | `±20pt` 圈码字符（cp/①–⑳/㉑–㉟/㊱–㊿）或 `○+数字`（全/半角归一）；位置漂移时页级值 fallback | **54/54** |

- `must_pass = (64/64 且 54/54)`；v51 True；gate：`missing_ok=True, ring_ok=True, verdict=CONTENT_AUTO_PASS, by_split={wz7: must_pass=True}`。
- **位置口径 vs 页级 fallback（单列计数）**：
  - missing_char：`position_hits=45/64`、`fallback_hits=19/64`（期望位置 = fix `col` 列框 x 中心 + 行首 y + pos×step，用 lines 行文本长度算 step，不依赖 source_x/y）；
  - battle4_ring：**逐书中位标定 offset = (+0.36, −2.54)pt**（5 个页级已知圈号样本拟合）后，`position_hits=54/54`、`fallback_hits=0`——此前 49/54 靠 fallback 是**源坐标↔产物坐标的尺度/偏移问题**，不是产物错。
- diagnostics：t97 只计 3 条真（#1/#15/#36；i=26 假项剔除），位置检查（coords 列 bbox + PDF 字符中心）→ **0/3**；118 外推 `unmaterialized`；`missing_char_all` 160 → 70（只诊断，不参与门禁）。

## 3. 接口

```bash
/usr/bin/python3 src/tools/content_eval.py \
  --gold data/punct_eval/content_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --book wz7 --out tmp_vert/bench/content_v51_pdf.json [--out-csv ...]
# 可选：--normalize none|variant|simp；--regression-fix / --t97-meta
```

- JSON：`content.overall/by_page`（两栏 I/D/S + 率 + cer，N=0 为 null）、`regression.must_pass_items`、`regression.must_pass`、`diagnostics`、`normalization_audit`、`normalize`、`gold_sha256/pdf_sha256`；CSV 长表。
- 只读；无 token/网络；v51（8 页）< 2s。

## 4. 单测（14 passed）

| # | 用例 | 断言 |
|---|---|---|
| 1 | 漏标点两栏 | with_punct CER 1/3、han_only 0 |
| 2 | 错字 | S=1、CER 0.5 |
| 3 | 多字 | I=1、CER 1.0 |
| 4 | 异体归一对照 | normalized_variant CER 0 |
| 5 | 繁简归一对照 | normalized_simp CER 0 |
| 6 | 存疑字同位屏蔽 | doubt=1、CER 0.5（gold/pred 同位各删 1） |
| 7 | must-pass 64+54 全过 | 64/64 + 54/54、True |
| 8 | must-pass 失败 | 63/64 → False |
| 9 | diagnostic 不影响 verdict | t97 0/3 时 must_pass True |
| 10 | CSV | 非空 |
| 11 | 产物有字、lines 无（防回退） | PDF 有 64+54、lines 空 → must_pass True |
| **12** | **不等长替换拆分** | S=1、I=1、D=0、dist=2、CER=1.0 |
| **13** | **N=0** | gold 掩蔽后为空 → `cer is None`（不记 0） |
| **14** | **空 PDF → exit 3** | 产物无文本 → 返回 3（不得回退 lines） |
| **15** | **`?` 屏蔽字符串断言** | `('甲?乙','甲乙丙')→('甲乙','甲丙')`；`('?甲','X甲')→('甲','甲')`；`('甲??乙','甲乙丙丁')→('甲乙','甲丁')`；无 ? 不变 |

## 5. 已知局限

- **gold 覆盖**：t111 gold 为 20 页混合；v51 仅评其中 8 个 wz7 页（wz6/heldout 需对应产物）。
- **坐标标定**：wz7 的 ring 用 5 个页级样本拟合中位 offset（+0.36,−2.54pt）后位置命中 54/54；wz6 的 ~22pt 偏移（t111 F1）尚未用本方法标定（v51 未评 wz6）。missing_char 有 19/64 仍靠页级 fallback（col/pos 反推位置与产物字符中心偏差 >20pt，待逐页标定）。
- **fallback 语义**：`position_hits` 与 `fallback_hits` 单列，must_pass 只要求 ok（位置或 fallback），报告不把 fallback 混入位置命中。
- **t97 3 条**：v51 全未修（diagnostic 0/3），属真实待办。
- **归一化**：`simp` 依赖 opencc（缺失回退 variant 表）；N0 主列不受影响。
- **lines 参数**：仅保留 CLI 兼容，不参与评测。

## 6. 复现

```bash
/usr/bin/python3 src/tools/content_eval.py --gold data/punct_eval/content_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --book wz7 \
  --out tmp_vert/bench/content_v51_pdf.json --out-csv tmp_vert/bench/content_v51_pdf.csv
/usr/bin/python3 -m pytest src/test/unit/test_content_eval.py -q   # 14 passed
```

## 7. 改动与约束

- 改：`src/tools/content_eval.py`（`_edit_ops` 拆分、? 同位屏蔽、N=0 null、PDF-only + exit 3、normalization_audit、删重复/死代码/未用 import）、`src/test/unit/test_content_eval.py`（14 例）、本报告、`tmp_vert/bench/content_v51_pdf.json/.csv`。
- 未改产品代码/data；未 commit。
