# 任务：修复 build_geom 对 wz4（小字密排书）的排版溢出

## 目标
`src/pipelines/build_geom.py` 排版 wz4，输出 PDF 页数应 ≈ 源 677 页（当前 1322 页，溢出翻倍），verify_geom 达标（页数 1:1 / split 0 / missing 0 / pitch ≥85%）。

## 已就绪数据（OCR 已完成，勿重跑）
- 行级文字：`/opt/test/data/wz4/wz4_spotting_lines.json`（677 页 / 21091 行，平均 31.2 行/页）
- 逐行坐标：`/opt/test/data/wz4/wz4_spotting_coords.json`（21091 个 poly，None 0%）
- 源 PDF：`/opt/test/source_pdf/wz4.pdf`（677 页，1744×2634 高清扫描，小字密排）

## 复现命令
```bash
cd /opt/test
/usr/bin/python3 src/pipelines/build_geom.py \
  data/wz4/wz4_spotting_lines.json \
  data/wz4/wz4_spotting_coords.json \
  output/wz4/wz4_geom_optimized.pdf \
  source_pdf/wz4.pdf
```

## 验证命令
```bash
cd /opt/test
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q   # 需 201 全过
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  output/wz4/wz4_geom_optimized.pdf \
  data/wz4/wz4_spotting_coords.json \
  data/wz4/wz4_spotting_lines.json
```

## 当前异常（修复前）
```
[几何] cw=28 measure=216 font=7.7 baseline=12.8 正文行高28px
[toc_map] 自动提取 242 个目录标题
[页眉共识] 0 个规范页眉
输出 1322 页 vs 源 677 页（每页溢出拆成 ~2 页）
verify: 行数1:1 仅 14.8%, pitch 达标率 11.3%（阈值85%）, 底部占位偏差中位 +3.5%
```

## 实测几何真值（677 页满行统计，供校准对照）
- 满行宽度中位 **668px @200dpi ≈ 240pt**，但 `calibrate` 算出 `measure=216`（偏低 24pt）
- 满行字数中位 28 字，字宽中位 23.4px ≈ 8.4pt
- 源书小字密排：正文行高约 28px ≈ 10pt，31 行/页

## 疑似方向（供参考，需自验）
1. `src/utils/geometry.py` 的 `calibrate`：`full` 筛选用 `w > 0.80*maxw`，个别超宽行（表格/标题）抬高 `maxw`，把真满行筛掉 → MEASURE_POLY 偏低。建议改百分位（如 P90）替代 max。
2. 密排书行距紧，`BASELINE`/`LINESPREAD` 推导可能失真。
3. `页眉共识 0 个`：页眉行混入正文，多占行数加剧溢出。

## 约束（AGENTS.md）
- 改 `calibrate`/几何标定属 **api-compat**：须更新 `spec/governance/PIPELINE_BEHAVIOR.md`，跑 201 测试全绿，verify_geom 达标。
- **防回归**：wz1（222页/24.3行每页/正常密度）和 wz3（850页/7.5行每页/稀疏书）不能因本次改动回归——calibrate 改动需对 wz1/wz3 也验证页数 1:1。
- 测试一律用 `/usr/bin/python3`（非 `python3`，后者命中 mineru venv 无 fitz）。
