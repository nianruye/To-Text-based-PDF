# punct_eval 序列 gap ±1 容差（t263）

> 只改评测配对；不改 gold、不改产品渲染、不改 `punct_fn_audit` 归因；未 commit。

## 1. 问题复现

t260 发现 wz7 8 页 34 FN 中：
- `fn_004 p57 quote_close`：产物文本层有 `」`
- `fn_011 p159 period`：产物文本层有 `。`

原 `sequence_eval` 只在同一 anchor gap key 内配对；当 anchor 映射边界抖动时，标点落到相邻 gap → gold 侧 FN、pred 侧 FP。

## 2. 修法

`punct_bench.sequence_eval`：
- **同 gap 优先**（原有逻辑不变）。
- 同 gap 无同类/同组候选时，允许 `g2-1` / `g2+1` 的同类/同组候选；每命中一次计 `gap_tolerance`，并记录 `gap_tolerance_pairs`。
- 不改变 anchor 对齐、值/类型判定、FP 定义；不改变 gold。

## 3. 修前后（wz7 8 页，命令见 §6）

| 指标 | 修前 | 修后 | 变化 |
|---|---:|---:|---:|
| TP | 652 | **656** | +4 |
| FP | 38 | **34** | -4 |
| FN | 34 | **30** | -4 |
| P | 0.9449 | **0.9507** | +0.0058 |
| R | 0.9504 | **0.9563** | +0.0059 |

`gap_tolerance=4`。配对记录：
- p57 gap401 quote_close（fn004）
- p57 gap401 enumeration_comma（同页额外真配对）
- p830 gap203→209 period
- p830 gap203→209 quote_close

**与预期 +2 不一致的原因**：除点名 2 条外，±1 还回收 p57 enumeration_comma 与 p830 的 period/quote_close（共 2 条额外 TP）；不是 FP 增加，FP 反而 38→34。
**fn011 p159 period 未修复**：该处 pred period 在 gap152、gold 在 gap166，`gap_map` 在 166 附近无 key，超出 ±1 容差；属 anchor 映射缺失（非相邻 gap 抖动），需更宽的锚点对齐/文本重定位，不在本轮 ±1 范围。报告如实登记。

## 4. 单测

`src/test/unit/test_punct_bench.py` 新增：
- `test_sequence_gap_tolerance_plus_minus_one`：gold `甲「乙」丙` vs pred `甲「乙丙」` → TP2/FP0/FN0，`gap_tolerance=1`
- `test_sequence_gap_tolerance_no_extra_fp`：gold `甲乙` vs pred `甲「乙` → 仍 1 FP、无 TP、`gap_tolerance=0`

既有 **34 passed**（含序列/阅读序/配对/端到端）。

## 5. 横排

t261 的横排 gold 未就绪，**跳过**横排回归；本修改只在 sequence eval 的 gap 候选回退，cell 口径与 reading_order 不变。

## 6. 复现

```bash
/usr/bin/python3 src/tools/punct_eval.py --mode sequence \
  --gold data/punct_eval/content_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --book wz7 --out /tmp/seq_fix.json --out-csv /tmp/seq_fix.csv
# TP656/FP34/FN30 P0.9507 R0.9563
```

## 7. spec 影响

`spec/governance/PUNCT_EVAL.md` §6.4.7 原写「gap 不做 ±1 容差」，与实现修订冲突；已改为「同 gap 优先，同 gap 无候选才允许 ±1，报告记录 gap_tolerance」，并保留「其余跨 gap 仍 FP/FN」。这是口径修订，不是静默实现变更。
