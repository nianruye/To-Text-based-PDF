# wz2/wz3 pitch 分页子集诊断（t307，no-go）

## 先纠正

`get_text().splitlines()` 会把同一视觉行在宽间隙处拆行，**行数比不能作为根因**。本文件改用 verify_geom 的 y 聚类 `--json` 逐页 dump。

dump：
- `output/rebuild_v2/wz2_dump.json`（783页）
- `output/rebuild_v2/wz3_dump.json`（850页）

## 权威口径

| 书 | 可比较页 | pitch 失败页 | 失败率 | pitch |
|---|---:|---:|---:|---:|
| wz2 | 764 | 174 | 22.8% | **74.7% FAIL** |
| wz3 | 767 | 160 | 20.9% | **79.1% FAIL** |

结论与 captain 一致：**分页子集问题**，不是全书行距/折行。

## 失败页 vs 正常页特征

wz2：
- `blank`（输出底占位比源高 >8%）：失败页 73/104（70.2%），正常页仅 31/660。
- 失败页源 pitch 中位 **28.01**，输出中位 **28.60**（Δ+0.95）；正常页源32.67/out32.54（Δ−0.15）。
- 失败页常见源首行：CIP/版权页、注文（`〔一〇〕…`）、短页/章末。
wz3：
- 失败页源 pitch 中位 **22.81**，输出中位 **25.74**（Δ+3.19）；正常页22.81/22.66。
- 失败页大量是 `中国古代经济史稿` 书眉页、章标题页、注文页。
- `blank` 失败率 6/14；`n_eq` 失败率40/213。

| 特征 | wz2 失败率 | wz3 失败率 |
|---|---:|---:|
| blank | 70.2% | 42.9% |
| n_eq=False | 33.0% | 18.8% |
| overflow | 75.0% | 28.6% |
| body_shift | 50.0% | 26.3% |

## 根因判断

- 失败页不是单一「PER_PAGE_PITCH 没命中」：`PER_PAGE_PITCH=1` 复测 wz2 仍 74.7%。
- 也非单一字号/版心：t306 已试 font14.6/measure524-545，仅77%左右。
- 失败页集中在 **非纯正文页**：CIP/版权、章标题/书眉、脚注注文、短页/章末。verify `_body_lines` 从这些页抽取的「正文行」与 build 的页级 `_pp`/行高口径不一致；输出在这些页被压缩或注文行参与中位，导致 pitch 比较失败。
- wz3 另有 `中国古代经济史稿` 书眉页大量进入可比集合，书眉/章标题行拉低源 pitch，而输出行距按其字号计算，Δ+3pt。

## 修复尝试

- `PER_PAGE_PITCH=1`：wz2 74.7% 不变。
- `HORIZ_FONT_MEASURE=14.6` / `HORIZ_MEASURE=524,545`：77.2-77.4%，未达。
- `_pos_sscale` 下限 0.62→0.92：pitch 74.7% 不变（已恢复 0.62）。

**未达 wz2≥90、wz3≥90；未放宽 verify 阈值。**

## 产物/裁片

- `output/rebuild_v2/wz2_fix2.pdf`（783页，74.7 FAIL）
- `/tmp/wz3_fix2.pdf` = `wz3_fix.pdf`（850页，79.1 FAIL）
- 失败/正常页裁片：`output/rebuild_v2/wz2_p31_src.png`/`wz2_p31_out.png`、`wz3_p12_*`、`wz3_p13_*`。

未改 gold/punct_eval；构建串行；未 push/commit。
