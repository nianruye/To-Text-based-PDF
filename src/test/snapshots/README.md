# 回归快照基线

记录当前管线的输出指标作为基线，用于重构前后 diff。**不作为 CI 门禁**（不加入 pytest），由人判断变化是否可接受。

## 用途

重构后重新生成快照 → diff 基线 JSON → 人判断指标变化是回归还是可接受代价。

## 样本

| 基线文件 | 源 PDF | 管线 | 类型 | 说明 |
|---|---|---|---|---|
| baseline_wz1_geom.json | wz1.pdf | build_geom | 现代书籍 | 222 页，脚注+标题层级，现代学术著作基准 |
| baseline_youhua_geom.json | 优化前.pdf | build_geom | 现代书籍 | 20 页，简单排版，现代书籍基准 |
| baseline_wz2_classic.json | wz2.pdf | build_classic | 复杂注释排版 | 783 页，横排夹注本，旁注/墨高重叠/案注/附录 |

> ⚠️ **wz2 是极端案例**（夹注本/附录/案注/旁注），不代表古籍的平均复杂度。它的指标**不应**作为"古籍管线好不好"的唯一判据。后续应至少补一份简单古籍样本作为对照（当前 build_classic 仅有 wz2 一个测试文件）。

## 指标（verify_geom.py 同口径）

| 指标 | 含义 |
|---|---|
| `pitch_ok_pct` | pitch 达标率（误差 <3% 的页占比，%） |
| `pages` | 输出页数（物理页） |
| `overflow_pages` | 溢出页数（源页溢成多物理页） |
| `blank_pages` | 空白页数（底部占位偏差 >8%） |
| `bot_gap_median` | 底部占位偏差中位（%，正=输出短于源/底部留白，负=溢出） |

> 注：`overflow_pages` 取 verify_geom 的 `split`（源页溢成多物理页，校准后应 0 = 1:1）。`agg.overflow`（占位溢出，输出底部超源底部）是另一个概念，记于 `_verify_*.json`，不入基线 5 指标。

## 当前基线指标（2026-07-17，fit_positional 校准两趟）

| 基线 | 管线 | pitch达标率 | 输出页数 | 溢出(split) | 空白页 | 占位偏差中位 |
|---|---|---|---|---|---|---|
| baseline_wz1_geom | build_geom | 89.5% | 222 | 0 | 14 | +2.2% |
| baseline_youhua_geom | build_geom | 65.0% | 20 | 0 | 8 | +6.0% |
| baseline_wz2_classic | build_classic | 58.8% | 783 | 0 | 87 | +3.8% |

观察：
- 三本均 1:1（split=0），校准两趟生效。
- **wz1（现代书主力）** pitch 89.5% 最佳；优化前 20 页样本小、pitch 65% 波动大，作辅助对照。
- **wz2（极端案例）** pitch 58.8%、空白 87--夹注/案注/附录复杂，指标偏低属预期，不作古籍管线唯一判据。
- 对比 spec ancient README 记录（wz2 空白 97 / pitch 59.1%）：当前空白 87（-10）、pitch 58.8%（-0.3pp），代码已有微调。

## 重构后流程

1. **重新生成快照**：重跑生成命令（见下），覆盖 `_out_*.pdf` 与 `_verify_*.json`。
2. **diff 基线 JSON**：对比 `baseline_*.json` 与新 `_verify_*.json` 提取的指标。
3. **人判断**指标变化是否可接受：
   - **wz1 / 优化前（现代书籍基准）**：指标应稳定。pitch 下降 / 溢出增加 / 空白增多 = 回归，需排查。
   - **wz2（极端案例）**：指标变化需人工判断。如 pitch 59.1% → 55% 可能是为修其他问题（如夹注/案注）的可接受代价，不一定是回归。

## 生成命令

> 必须设 `PATH=/usr/bin:/usr/local/bin:/bin`，让 `fit_positional` 内部 `subprocess` 调的 `python3` 命中系统 python（有 fitz/opencc），而非 mineru venv（无 fitz）。

```bash
export PATH=/usr/bin:/usr/local/bin:/bin
cd /opt/test
mkdir -p src/test/snapshots

# [1] wz1 build_geom 校准（222页）
LAYJSON="data/wz1/wz1.pdf_by_PaddleOCR-VL-1.6 .json" PER_PAGE_PITCH=1 PAGENUM_GLOBAL_TABLE=data/wz1/wz1_full_pagenum.json \
  /usr/bin/python3 src/calibration/fit_positional.py \
  data/wz1/wz1_spotting_lines.json data/wz1/wz1_spotting_coords.json \
  src/test/snapshots/_out_wz1_geom.pdf source_pdf/wz1.pdf

# [2] 优化前 build_geom 校准（20页）
PER_PAGE_PITCH=1 /usr/bin/python3 src/calibration/fit_positional.py \
  data/legacy/spotting_lines.json data/legacy/spotting_coords.json \
  src/test/snapshots/_out_youhua_geom.pdf "source_pdf/优化前.pdf"

# [3] wz2 build_classic 校准（783页）
LAYJSON=data/wz2/wz2.pdf_by_PaddleOCR-VL-1.6.json PAGE_FONT=1 PER_PAGE_PITCH=1 LAYOUT_HEADINGS=1 \
  /usr/bin/python3 src/calibration/fit_positional_classic.py \
  data/wz2/wz2_spotting_lines.json data/wz2/wz2_spotting_coords.json \
  src/test/snapshots/_out_wz2_classic.pdf source_pdf/wz2.pdf

# [4] verify_geom 指标（--json 输出原始 JSON）
/usr/bin/python3 src/test/verify_geom.py src/test/snapshots/_out_wz1_geom.pdf \
  data/wz1/wz1_spotting_coords.json data/wz1/wz1_spotting_lines.json \
  --json src/test/snapshots/_verify_wz1.json
/usr/bin/python3 src/test/verify_geom.py src/test/snapshots/_out_youhua_geom.pdf \
  data/legacy/spotting_coords.json data/legacy/spotting_lines.json \
  --json src/test/snapshots/_verify_youhua.json
/usr/bin/python3 src/test/verify_geom.py src/test/snapshots/_out_wz2_classic.pdf \
  data/wz2/wz2_spotting_coords.json data/wz2/wz2_spotting_lines.json \
  --json src/test/snapshots/_verify_wz2.json
```

## 文件清单

- `CURRENT_BEHAVIOR_SPEC.md` - **现状 spec**（第 1 步，定性+分布特征，重构 diff 的语义参照）
- `baseline_wz1_geom.json` / `baseline_youhua_geom.json` / `baseline_wz2_classic.json` — 基线（**保留**，重构 diff 用）
- `_out_*.pdf` — 生成的输出 PDF（临时，可删，仅用于 verify）
- `_verify_*.json` — verify_geom 原始 JSON（临时，可删，基线从中提取）
- `_gen.log` — 生成日志

## 注意

- **不加入 pytest**：快照是人工 diff 工具，非自动门禁。`src/test/snapshots/` 下无 `test_*.py`，pytest 不采集。
- **wz1 LAYJSON 文件名含空格**：实际文件是 `data/wz1/wz1.pdf_by_PaddleOCR-VL-1.6 .json`（1.6 与 .json 间有空格），spec 文档里的无空格路径其实不匹配。
- **基线方式**：用 `fit_positional` 校准两趟（spec 正式运行方式），非单趟。校准后页数应接近 1:1、pitch 达标率稳定。
