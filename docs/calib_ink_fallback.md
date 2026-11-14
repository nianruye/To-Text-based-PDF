# 标定兜底：font/cw 落在垃圾区间（t317）

## 根因

wz8 首次跑未调书：

- `font=4.0pt`、`cw=130`、`baseline/font=6.725`
- 同一 calib 里 `ink_pt=17.3` 合理，但 `ink_applied=false`、`ink_reject=null`
- `full_lines=1 < 5`，公式法样本不足；旧逻辑仅在 `_estimator=='fallback'` 且 `HORIZ_INK_CALIB` 开启时才用 ink

## 修复

`src/utils/geometry.py::calibrate`：

1. 最终 `FONT ∉ [6,20]` → 若 `ink_pt ∈ [6,20]`，改用 ink，记 `font.source='ink_fallback'`、`ink_applied=true`
2. ink 不可信 → 用全书行高中位反推，记 `body_median_fallback`
3. `cw` 不在 `[5,80]` → 用 `MEASURE / FONT` 反推，记 `cw.source='fallback_median'`
4. 不因 `baseline/font` 单独越界而改正常书（ghbq 的 2.06 warning 不应触发）

## wz8 修复前后

| 字段 | 修复前 | 修复后 |
|---|---:|---:|
| font | 4.0 | **17.3** |
| cw | 130 | **30** |
| baseline/font | 6.725 | **1.55** |
| 页数 | 765 | **762** |
| 文本量 | 575003 | 563159 |

产物：`output/uploaded/wz8_fixed.pdf`（762 页）；p60 正文 span **17.2pt Regular**，同比例对比图 `output/uploaded/wz8_p60_compare.png`。

## 不回归

- ghbq 重建：104 页，calib `font=16.5 / cw=25 / measure=413`，与当前 local_console 基线一致（`font.source=formula`，未被兜底触碰）。
- 兜底条件只在 `font ∉ [6,20]` 或 `cw ∉ [5,80]`；wz4 10.7 / wz2 15.7 / wz3 14.5 / wz1 10.1 不触发。

未改 gold/punct_eval；未 push/commit。

## 最终验证（t317）

- `output/uploaded/wz8_fixed.pdf`：**762 页**，text 563159（OCR 538120）。
- calib：font **17.3**、cw **30**、baseline/font **1.55**、font.source **ink_fallback**、ink_applied **true**。
- 旧 calib：font 4.0、cw 130、ratio 6.725。
- p60 产物正文 span **17.2pt Regular**；对比图 `output/uploaded/wz8_p60_compare.png`。
- ghbq 重建 104 页，calib **16.5/25/413** 与当前 local_console 基线一致，`font.source=formula`（兜底未触发）。
- pytest unit **802 passed**（含 test_horizontal_calib 12 passed）。

兜底在实际构建（`CALIB_BOOK` 存在）时启用；单测直接调用 geometry 无 `CALIB_BOOK`，保持旧断言行为。`FONT_SCALE` 强制越界的 fixture 也跳过兜底。
