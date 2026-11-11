# 横排逻辑行口径（t218 / S4-R2）

> 对象：ghbq 行数 1:1 指标（旧 35.1%）与 p32 等页「同一源 OCR 行被 x 间隔拆 span」。
> 状态：口径已实现；ghbq 逻辑行 1:1 = **84.4%**，距 ≥95% 仍有 15 页，build 端行合并待续。

## 1. 口径

**逻辑行**：同一页内 y 中心满足
`|Δy_center| ≤ 0.5 × median(line_height)`
的 span/line 归为一行；bbox 取并集。

- verify：`_logical_lines(lines)` 先对页内文本行聚类，再走原 `_body_lines`/页高/pitch。
- build：一条 OCR spotting 行 = 一条逻辑行；正文不因 OCR 片段 x 间隔拆成多行。超宽行才允许受控断行，并写 `[分片]` 日志。
- 源/输出同一函数/容差；`line_1to1` 为两侧逻辑行数相等页占比。

## 2. 实测（ghbq 104 页）

| 指标 | 旧 span 口径 | 逻辑行口径 | 目标 |
|---|---:|---:|---:|
| 行数 1:1 | 35.1% | **84.4%** | ≥95% |
| 页高误差 <5% | 27.7% | 17.7%（中位6.6%） | 中位<2% |
| overflow | 25 | 26 | 0 |
| pitch | 96.8% | 94.8% | ≥99% |
| 页数 | 104=104 | 104=104 | 1:1 |

- 84.4% 说明「同 y 多 span 合一行」口径修复有效；剩余 15 页输出行数 15/17、17/19 等，源/输出仍差 1-2 行（build 端 OCR 行合并/断行粒度未完全统一）。
- 该 15 页需要 build 侧逐页定位（p2/p14/p23/p33/p38/p46/p56/p61/p63/p68/p85/p87/p91/p96/p98），不是 cw/FONT 单点；本任务未声称达标。

## 3. fallback 交叉验证

- `font_ink = median(poly height)*72/DPI/0.88`。
- ghbq fallback `font_est=18.4` vs `ink=23.5`（差27.7%），但 ink∉[6,20] → 保留18.4，`ink_reject=out_of_range`，calib `ink_pt/ink_applied/ink_reject` 记录。
- `HORIZ_INK_CALIB=0` 关闭；`HORIZ_FALLBACK_RATIO=0` 回旧 full_line。

## 4. 验证命令

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/ghbq_s4r2.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  output/ghbq_full/ghbq_s4r2.pdf output/ghbq_full/_ocr_ghbq/ghbq_spotting_coords.json \
  output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json --src-pdf source_pdf/ghbq.pdf
/usr/bin/python3 -m pytest src/test/unit/test_line_metric.py src/test/unit/test_horizontal_calib.py -q
```

## 5. 单测

- `_logical_lines`：同 y 多 span → 1 行；相邻正文行（34pt, 高20）不合并。
- fallback ink：`ink_font/ink_applied/ink_reject` 字段；ink 越界时保留 fallback。
- verify 指标 `line_1to1` 字段；pytest 14 passed（2 文件合计）。
