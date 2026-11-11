# ghbq 标题续行 / 目录三栏版式独立验收（t233）

> 验收人：验证评审员（独立构建/量 span；不采信实现者数字）
> 日期：2026-11-11 19:20–19:50；分支 `feat/s4-line-metric`（HEAD `fc86ce8`，t232 未提交）
> 产物：`output/ghbq_full/acc_title_toc.pdf`（独立构建）；对照 `ghbq_title_toc.pdf`（t232）
> 结论：**FAIL（F1 p11 三项硬判据全不达标；F2 TOC 单测拦不住回退）**；p14 标题已修好，门禁/三书零回归成立。
> 未改实现/数据；临时红/绿测试后产物已复原（md5 `49eec22c…`）；未 commit。

## 1. 独立构建 / 门禁

```bash
PYTHONHASHSEED=0 /usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/acc_title_toc.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
# exit 0

VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py output/ghbq_full/acc_title_toc.pdf \
  output/ghbq_full/_ocr_ghbq/ghbq_spotting_coords.json output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json \
  --src-pdf source_pdf/ghbq.pdf
# 104=104；line_1to1 100%；pitch 97.9%；overflow 0；gate PASS
```

| 指标 | 实测 | 门槛 |
|---|---:|---:|
| 页数 | 104/104 | 104=104 PASS |
| line_1to1 | 100.0% | ≥95% PASS |
| pitch | 97.9% | ≥97.9% PASS |
| overflow | 0 | 0 PASS |
| gate | PASS | PASS |

## 2. p14 章标题（PASS）

`p14` 同一 block（bbox `75.2,174.9–525.5,268.9`）含 2 行；两行均 **NotoSansCJKjp-Regular / 22.52pt**，无半行宋体；两行中心 x≈300.35，页中心 297.6（差 2.7pt，视觉居中）。
→ **单一标题块、整块同字体（黑体族）、居中**：PASS。

## 3. p11 目录三项硬判据（FAIL）

在 `acc_title_toc.pdf` / `ghbq_title_toc.pdf` 的 p11 上量 span 坐标（两产物一致）：

| # | 判据 | 实测 | 结论 |
|---|---|---|---|
| 1 | 续行 x0 与首行标题 x0 差 ≤2pt | `路线的形成与发展` x0=94.6 vs 首行标题 x0=149.6（Δ55.0）；`论证` 94.6 vs 162.6（Δ68.0）；`论观点及纲领主张` 94.6 vs 149.6（Δ55.0）；`改造”` 94.6 vs 174.3（Δ79.7） | **FAIL** |
| 2 | 同级节条目 `1./2./3.` 字号差 ≤0.5pt | `3 1.`/`15 3.`/`24 2.` = **16.4pt**；`11 2.`/`21 1.`/`26 3.` = **22.9pt**（Δ6.5） | **FAIL** |
| 3 | 页码 span `x1` 统一（差 ≤1pt） | `3`/`15`/`24` = **134.1**；`2`/`11`/`21`/`21`/`26` = **149.6**（Δ15.5） | **FAIL** |

- 页码与条目号粘连：`112.`/`211.`/`263.` 均 **不存在**（PASS）；但上述对齐/字号问题仍在。
- 竖线：p11 有 drawings x=136.3/151.8 的短竖线，页码在标题左侧；但页码右边界不齐、续行缩进缺失，未达到「左栏 + 竖线」的版式要求。

## 4. 目录续行合并

续行文字确实进入上一 block（不在顶层单独成条），但**缩进 x0=94.6 与首行标题不一致**（见 §3-1）；「已并入上一条目」只在文本层/块层成立，版式层未缩进对齐 → 按 captain 硬判据 FAIL。

## 5. 零回归（与 t232 声明一致）

| 书 | 当前构建 | 对照基线 | 逐页文本 diff | gate |
|---|---|---:|---:|---:|
| wz4 | 677 / 554,341 | 677 / 554,341 | **0** | PASS 99.5 = 99.5 |
| wz1 | 222 / 137,390 | 222 / 137,390 | **0** | PASS 98.3 = 98.3 |
| wz2 | 6 / 1,469 | 6 / 1,469 | **0** | REJECT 66.7（基线同为已知阻断） |

ghbq vs t232 前一版（`acc_ghbq_s4final.pdf`）文本变化页：**`[11,14,33,61]`**；t232 声明含 p5/p11/p14/p33/p56/p61，实测 p5/p56 无 diff（次要声明偏差，F3）。

## 6. 单测红/绿（F2）

- 新增 `test_heading_merge.py` + `test_toc_layout.py`：默认 **3 passed**；全量 unit **748 passed**。
- **标题红侧**：`TITLE_CONT=0` 重建 → `test_heading_merge` **1 failed**（有效）。
- **目录红侧**：`TOC_PRE=0` 重建 → `test_toc_layout` **5 passed**（**无效**，拦不住回退）。
- 红/绿后已恢复 `ghbq_title_toc.pdf`，md5 复原 `49eec22c…`。
- 单测缺陷：只断言「页码在行首/无粘连」，**未断言续行缩进、同级字号、页码 x1 对齐**（正是本轮失败项）。

## 7. 发现

- **F1（高，must-fix）p11 三项硬判据全失败**：续行 x0 差 55–79.7pt；同级字号 16.4/22.9 混跳；页码 x1 134.1/149.6。t232 未达验收，t235 需修。
- **F2（中）TOC 单测拦不住回退**：`TOC_PRE=0` 仍 5 passed；需补续行缩进/字号一致/页码 x1 断言。
- **F3（低）变化页声明偏差**：ghbq 实测变化页 [11,14,33,61]，声明含 p5/p56；不影响三书零回归。
- p14 标题、门禁、三书文本零回归均通过。

## 8. 结论

**t233 FAIL**：p14 标题已修好、门禁 104/PASS/pitch97.9/overflow0、三书文本 0 diff；但 p11 三项硬判据（续行缩进 / 同级字号 / 页码右对齐）全部不达标，且 TOC 单测无法拦住回退。需 t235 修复后重验。

---

# t237 round-2 复验（t236）

> 日期：2026-11-11 20:47–21:10；分支 `feat/s4-line-metric`（HEAD `fc86ce8`，t236 未提交）
> 结论：**FAIL（F1 全量 pytest 1 failed：t246 real-red fixture 与 t236 重建产物不一致）**；p14/p11、门禁、零回归、红/绿单测均通过。

## 1. 独立构建（契约）

```bash
PYTHONHASHSEED=0 /usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/ghbq_title_toc.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
# exit 0；104 页
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py output/ghbq_full/ghbq_title_toc.pdf \
  output/ghbq_full/_ocr_ghbq/ghbq_spotting_coords.json output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json \
  --src-pdf source_pdf/ghbq.pdf
# 104=104；line_1to1 100%；pitch 97.9%；overflow 0；gate PASS
```

## 2. p14 标题（PASS）

- 单一 block bbox `75.2,174.9–525.5,268.9`，2 行；
- 两行均 `NotoSansCJKjp-Regular 22.52pt`；
- 行中心 x≈300.35（页中心 297.6，差 2.7pt），无「第一行宋体/第二行黑体」。

## 3. p11 目录（PASS）

| 项 | 实测 |
|---|---|
| 页码 x1 | 全部 **112.6**（PASS，差≤1） |
| 页码位置 | 页码 x1=112.6 < 竖线 x=**114.8**，在左栏 |
| 竖线 | 8 条 drawings x=114.8（PASS） |
| 粘连 | `112.`/`211.`/`263.` 均不存在 |
| 节级字号 | `1./2./3.` 全部 **16.4pt**（差≤0.5） |
| 续行 x0 | `形成与发展` 112.6 vs 标题112.6；`和准备` 134.5 vs 134.4；`及纲领主张`112.6；`多元化`134.5 vs 134.4；`和发展`134.5 vs134.4（差≤0.1） |
| 条目合并 | 续行均在上一 block/条目内，未单独成条 |

> `test_toc_layout` 现使用 `ghbq_title_toc3.pdf`（存在时）；其 7 项断言与上表一致。

## 4. p97 异常行（PASS）

- 契约重建后 p97 最大 span `x1=506.1`（≤版心右缘 506.75+2），不再 4160.6；
- `OCR_GIANT_FALLBACK` 整页贴图兜底生效，104=104、文本可读。

## 5. 门禁 / 零回归

- ghbq：104=104、line_1to1 100%、pitch 97.9%、overflow 0、gate PASS；
- 独立重建 wz4/wz1/wz2 并与 t233 前产物比较：
  - wz4 677/554341、逐页 diff **0**、PASS 99.5；
  - wz1 222/137390、diff **0**、PASS 98.3；
  - wz2 6/1469、diff **0**、REJECT 66.7（已知基线）。

## 6. 单测红/绿

- 默认 `test_heading_merge + test_toc_layout`：PASS（8 项）。
- **标题红侧**：`TITLE_CONT=0` 重建 `ghbq_title_toc.pdf` → `test_heading_merge` **1 failed**（有效）。
- **目录红侧**：`TOC_PRE=0` 重建 `ghbq_title_toc3.pdf` → `test_toc_layout` **6 failed / 1 passed**（有效）。
- 红/绿后已恢复两产物（md5 `88aef4b3…` / `f090992f…`）。
- **全量 pytest：1 failed, 770 passed**：
  - `test_verify_typography.py::test_real_red_ghbq_title_toc` 断言 `-8.32/-11.65`（t232 旧产物）；
  - 契约先重建 t236 的 `ghbq_title_toc.pdf`，现在 p11 gap 只剩 p12 `-8.14`，旧断言失败。

## 7. 发现

- **F1（高，must-fix）real-red fixture 路径冲突**：t246 测试把 `ghbq_title_toc.pdf` 当固定红侧样品，但 t236 契约会重建同一路径为已修产物 → 全量 pytest 必挂。需改为独立不可变红侧文件（如 `tmp_red_title_toc.pdf` 或 `ghbq_title_toc_bad.pdf`）并在测试中固定。
- **F2（低）** p14 标题中心与页中心差 2.7pt（可接受，记录）。
- p14/p11/p97、门禁、三书零回归、红/绿单测均通过。

## 8. 结论

**t237 FAIL（只因 F1）**：版式/门禁/零回归全部达标；全量 pytest 1 failed 是 real-red 样品路径被 t236 覆盖导致的测试设计缺陷，需修 fixture 后复验。
