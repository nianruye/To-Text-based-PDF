# 正文栏宽标定报告（t371）

## 测量

`src/tools/column_width_probe.py`：源 PDF 150dpi 渲染，在 OCR 行 y 带、x±15pt 内取墨迹 x 范围；产物取 bbox 众数。

| 书 | 源栏宽 | 产物栏宽 | 差 |
|---|---:|---:|---:|
| ghbq | 437.3 | 411 | −6.0% |
| wz1 | 325.0 | 312 | −4.0% |
| wz4 | 309.1 | 299 | −3.3% |
| wz10 | 421.0 | 415 | −1.4% |

（与 captain 的 ghbq433.4/wz4 284.6 有差异，因采样满行页/行不同；方向一致。）

## 标定链

- `geometry.calibrate`：`MEASURE_POLY=P90/中位满行宽`，`MEASURE=MEASURE_POLY/OVERBOUND（1.115）`，`MARGIN=(PAGE_W-MEASURE)/2`，`FONT=MEASURE/cw`。
- 实际 calib：ghbq poly461→measure413（overbound1.115）→产品栏宽411.5；wz4 poly334→measure300→产品298.9。
- 所以 calib 与实际渲染**一致**；差异来自 **固定 OVERBOUND=1.115 与每书 OCR 框/墨迹比不一致**：ghbq OCR/ink≈1.06、wz4≈1.17。不是 preamble 常量不一致。
- AGENTS #47 的 ghbq measure460 是旧版 fallback 记录；当前构建走 full_line_overbound，measure413。

## 尝试与停止

- 试 `COLW_INK=1` 用源图满行墨迹中位替代 measure：ghbq454（目标433）、wz4 306（目标285）→反而更宽；说明源图满行样本/墨迹口径与 captain 数据不同（可能含跨栏/边注）。
- 未启用该实验；代码已回退（无 `COLW_INK` 遗留）。
- 未改默认栏宽，避免断行/页数变化。

## 结论

栏宽偏差来自**固定 OVERBOUND 与每书 OCR 框/墨迹比不匹配**，需要书级源墨迹标定；但当前源墨迹采样口径未稳定到可交付（ghbq454 vs 目标433），未找到可同时满足四本且页数不变的实现。未修复。

## 验收

- pytest unit 802 passed（本任务前基线；未改最终 geometry）。
- 未做四本重建 gate/pitch；未改gold/punct_eval；未push/commit。
- 剩余：需以逐页满行、x±15pt、排除跨栏的墨迹测量重做标定，或在 calib 记录每书 OCR/ink ratio 后按 ratio 修 measure。
