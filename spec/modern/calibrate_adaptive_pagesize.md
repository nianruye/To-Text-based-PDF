# Spec: calibrate 自适应改造（通用 PDF 还原系统）

> 状态：planned ｜ 类型：design-change + api-compat ｜ 负责：Claude Code
> 目标：让 `calibrate` 按书自适应页尺寸与行距来源，wz1/wz3 不回归、wz4 达标，不再"修一本坏一本"。

---

## 1. 背景与问题

当前 `src/utils/geometry.py 的 calibrate()` 用**全书统一逻辑**推导页尺寸（PAGE_W/PAGE_H）和行距（BASELINE），套用到所有页。三本书实测差异巨大（密度差 4 倍、边距差异大），单一逻辑失效：

| 书 | 行/页 | 实际页 pt | coords 推导 pt | 文字覆盖率 |
|---|---|---|---|---|
| wz1 | 24.3 | 405×634 | 405×633 | **100%** |
| wz3 | 7.5 | 595×877 | 603×878 | **101%** |
| wz4 | 31.2 | 418×635 | 301×457 | **72%** ⚠️ |

**前次改动（calibrate 加 src_pdf）的教训**：一刀切用实际页尺寸替代 coords 推导——
- wz4（覆盖 72%）修对了页框 ✅，但**行距被错误地随页框缩放 29%**（12.78→16.5pt）→ pitch 0%
- wz1（覆盖 100%，coords 本来就准）被换后回归（pitch 97.3%→61.4%）
- wz3（覆盖 101%）行高被放大成 186px，完全错误

**根因两条**：
1. 页尺寸来源没有按"文字覆盖率"自适应选择
2. 行距（BASELINE/pitch）与页框尺寸**本无关**（应来自 OCR 行 y 间距统计），却被错误地随页框缩放

---

## 2. 设计原则（不可妥协）

- **P1 行距独立**：pitch/BASELINE 永远来自 OCR coords 的行 y 间距中位数统计，**绝不随页框缩放而缩放**。
- **P2 页尺寸自适应**：按文字覆盖率选来源——覆盖率高（coords 可靠）用 coords，覆盖率低（大边距）用 src_pdf 实际页尺寸。
- **P3 防回归**：wz1 pitch ≥97.3%（带原 env）是硬基线，任何改动 wz1/wz3 不得变差。
- **P4 不引入新硬编码书特例**：自适应逻辑必须基于可计算的统计量（覆盖率/百分位），不得 if book==wz4。

---

## 3. 具体改动

### 3.1 `calibrate(sl, co, DPI=200, src_pdf='')` 页尺寸自适应
```python
# 伪代码
coords_pw, coords_ph = 从 coords xmax/ymax 推导(现有逻辑)
coverage = coords_pw / actual_pw   (src_pdf 提供时)
if src_pdf 提供 且 coverage < COVERAGE_THRESHOLD:  # 大边距书
    PAGE_W, PAGE_H = fitz 读 src_pdf 实际页尺寸
else:                                              # coords 可靠(含无 src_pdf)
    PAGE_W, PAGE_H = coords_pw, coords_ph
```
- `COVERAGE_THRESHOLD` 默认 **0.95**（env `PAGE_COVERAGE_THRESHOLD` 可调）
- src_pdf 页尺寸取**多页中位数**（如前 50 页每隔 10 页取 rect 的中位 width/height），不用单页（防首页特殊）
- **决策日志**：打印 `页尺寸来源=src_pdf(覆盖72%)` 或 `=coords(覆盖100%)`，便于排障

### 3.2 行距（BASELINE）与页框解耦（修 wz4 pitch 0% 的关键）
- BASELINE 仍按现有逻辑 = coords 行 y 间距中位数 ×72/DPI（wz4 实测 12.82pt，wz1 19.01pt，wz3 22.68pt——样本充足稳定）
- **审查 LINESPREAD / 行高 / FONT 的任何一处是否乘了页尺寸缩放因子**，全部移除——行距计算只允许依赖 coords 行高统计与 FONT，不允许乘 (PAGE_H_src / PAGE_H_coords) 之类
- 验收：wz4 输出行距应 ≈12.78pt（实测源行距），不是 16.5pt

### 3.3 满行筛选改百分位（抗超宽行，附带改进）
- 现有 `full = w > 0.80*maxw`：个别超宽行（表格/标题/跨栏）抬高 maxw，把真满行筛掉
- 改为 `full = w > 0.80 * P90(widths)`（P90 抗离群），env `FULL_WIDTH_PCT` 可调默认 90
- 影响：MEASURE_POLY/cw 更稳健，对 wz3 这种有跨栏/表格的书尤其重要

### 3.4 行高 H_BODY 抗离群
- wz3 行高被算成 186px（错误）。H_BODY 改用**正文中位数**而非全体中位数，或截尾均值（去掉 P95 以上）
- 验收：wz3 正文行高应回归合理（参考历史成功值）

---

## 4. 验收标准（Definition of Done）

### 4.1 功能验收（三本书全过才算完成）
| 书 | 命令 env | 页数 | pitch 达标率 | 行数1:1 | 硬约束 |
|---|---|---|---|---|---|
| **wz1** | 带原 env* | 222/222 | **≥97.3%**（不回归）| ≥基线 | split0 missing0 |
| **wz3** | 默认 | 850/850 | ≥85% | 提升（当前0%）| split0 missing0 |
| **wz4** | 默认 | 677/677 | ≥85% | ≥80% | split0 missing0 |

\* wz1 原 env：
```
LAYJSON="data/wz1/wz1.pdf_by_PaddleOCR-VL-1.6 .json" PER_PAGE_PITCH=1 \
PAGENUM_GLOBAL_TABLE=data/wz1/wz1_full_pagenum.json
```

### 4.2 过程验收
- [ ] 201 测试全绿（`/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q`）
- [ ] verify_geom 三本书退出码 PASS（或 FAIL 项有书面说明可接受）
- [ ] calibrate 决策日志含"页尺寸来源 + 覆盖率"
- [ ] 无 `if 书名` 硬编码特例

### 4.3 spec 对账（AGENTS.md）
- [ ] 本 spec 状态 planned→implemented
- [ ] 改 calibrate 属 api-compat → 更新 `spec/governance/PIPELINE_BEHAVIOR.md`：
  - 新增 env：`PAGE_COVERAGE_THRESHOLD`(默认0.95) / `FULL_WIDTH_PCT`(默认90)
  - calibrate 签名：`src_pdf` 参数语义 = "提供时按覆盖率自适应选择页尺寸来源"
  - 行距来源契约：BASELINE 仅依赖 OCR 行高统计，不随页框缩放

---

## 5. 验证命令（复现/回归用）

```bash
cd /opt/test
# 单测
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q

# wz4
/usr/bin/python3 src/pipelines/build_geom.py data/wz4/wz4_spotting_lines.json \
  data/wz4/wz4_spotting_coords.json output/wz4/wz4_geom_optimized.pdf source_pdf/wz4.pdf
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py output/wz4/wz4_geom_optimized.pdf \
  data/wz4/wz4_spotting_coords.json data/wz4/wz4_spotting_lines.json

# wz1（带原 env）
LAYJSON="data/wz1/wz1.pdf_by_PaddleOCR-VL-1.6 .json" PER_PAGE_PITCH=1 \
PAGENUM_GLOBAL_TABLE=data/wz1/wz1_full_pagenum.json \
  /usr/bin/python3 src/pipelines/build_geom.py data/wz1/wz1_spotting_lines.json \
  data/wz1/wz1_spotting_coords.json output/wz1/wz1_geom_regress.pdf source_pdf/wz1.pdf
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py output/wz1/wz1_geom_regress.pdf \
  data/wz1/wz1_spotting_coords.json data/wz1/wz1_spotting_lines.json

# wz3
/usr/bin/python3 src/pipelines/build_geom.py data/wz3/wz3_spotting_lines.json \
  data/wz3/wz3_spotting_coords.json output/wz3/wz3_geom_regress.pdf source_pdf/wz3.pdf
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py output/wz3/wz3_geom_regress.pdf \
  data/wz3/wz3_spotting_coords.json data/wz3/wz3_spotting_lines.json
```

---

## 6. 关键实测数据（实现时对照）

| 量 | wz1 | wz3 | wz4 | 来源 |
|---|---|---|---|---|
| 实际页 pt | 405×634 | 595×877 | 418×635 | fitz src_pdf |
| coords 推导 pt | 405×633 | 603×878 | 301×457 | coords xmax/ymax |
| 文字覆盖率 | 100% | 101% | **72%** | coords_w/actual_w |
| pitch 中位 | 52.8px=19.0pt | 63.0px=22.7pt | 35.6px=**12.8pt** | coords 行y间距 |
| 行宽 px P50/P90/max | 967/988/1111 | 1294/1340/1678 | 668/679/737 | 满行(>8字) |

**wz4 行距验收锚点**：源行距 12.78pt，输出须 ≈12.8pt（当前错误值 16.5pt = 12.8×1.29，1.29 是旧页框缩放比，必须消除）。

---

## 7. 风险与回退
- 若 wz3 行高仍异常：检查 H_BODY 是否被页尺寸或离群值污染，退回用正文中位数
- 若百分位筛选改变 wz1 行为：wz1 已有 PER_PAGE_PITCH 路径，确认该路径不经过被改的 full 筛选
- 任何一本书不达标：不合并，先回退到改动前，单独诊断该书再继续
