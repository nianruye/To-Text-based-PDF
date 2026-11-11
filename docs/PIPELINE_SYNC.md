# 流水线同步（当前主线，2026-11-11）

> 本文件原名 Hermes PDF Pipeline 同步文档（2026-06-21，v13/Web 时代）。
> **v13/Web(localhost:8765) 已历史化**；当前唯一端到端主线是 `src/tools/scan2pdf.py`。
> 架构详见 [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md)；门禁/契约见 [spec/00_system_architecture.md](../spec/00_system_architecture.md)。

---

## 一、当前流水线

```
源PDF
  → ocr_book.py（layout + spotting；批量/断点/JSONL）
  → raw JSONL
  → coords/lines + layout.json
  → corrected_text（可选）
  → scan2pdf.py
       ├─ 横排：fit_positional.py 两趟 → build_geom / build_classic → xelatex
       └─ 竖排：build_vert.py → uplatex + dvipdfmx
  → verify_geom.py / verify_vert.py
  → quality_gate.py
  → 交付 PDF + .report.json + .calib.json（横排）+ .gate.json
```

### 入口

```bash
# 推荐：端到端（已有 OCR 数据，--skip-ocr）
/usr/bin/python3 src/tools/scan2pdf.py \
  --input source_pdf/<book>.pdf --book <book> \
  --out output/<book>/<book>.pdf \
  --data-dir data/<book> --skip-ocr --force

# 需要图片/版面：显式 --layout（或 LAYOUT_FIGS=1）
/usr/bin/python3 src/tools/scan2pdf.py ... --layout

# 人工文本校正：--corrected-text（缺省自动读 data/<book>/corrected_text.json）
/usr/bin/python3 src/tools/scan2pdf.py ... --corrected-text data/<book>/corrected_text.json
```

- OCR 新书：去掉 `--skip-ocr`，由 scan2pdf 调 `ocr_book.py`（layout/spotting/both）。
- 横排单链：`fit_positional.py`/`fit_positional_classic.py`（生产推荐仍走 scan2pdf）。
- 竖排单链：`build_vert.py`（生产推荐走 scan2pdf，便于统一 verify/gate/report）。

---

## 二、当前组件（替代旧清单）

| 层 | 当前文件 | 职责 |
|---|---|---|
| 编排 | `src/tools/scan2pdf.py` | preflight/判书型/OCR/数据/LAYJSON/corrected_text/构建/verify/gate/report |
| OCR | `src/tools/ocr_book.py` | PaddleOCR-VL API、分批/断点、JSONL、coords/lines/layout.json 转换 |
| 横排校准 | `src/calibration/fit_common.py` + `fit_positional*.py` | 两趟 pass1/pass2；pass2 交付无 GMPG |
| 横排渲染 | `src/pipelines/build_geom.py` / `build_classic.py` | geom/classic；LAYJSON/图片/校正文本消费 |
| 竖排渲染 | `src/pipelines/build_vert.py` | 标定/槽格/配平/渲染 |
| 共享 | `src/utils/geometry.py` 等 | 标定/转义/页码/图块/缺字 |
| 验证 | `src/test/verify_geom.py` / `verify_vert.py` | 横/竖 PASS/FAIL + 指标 |
| 门禁 | `src/tools/quality_gate.py` | gate sidecar/verdict/reasons/calib/multi_format |
| 审计 | `.report.json` / `.calib.json` / `.gate.json` | 编排/标定/门禁 sidecar |

---

## 三、当前关键输出/字段

- `<out>.report.json`：input_sha/book_type/pipeline/data/layout/corrected_text/fix/build/gate/calib/exit；
- `<out>.calib.json`（横排）：`horizontal-calib-v1`，含 estimator/fallback/ink、cw/measure/font/baseline/coverage/selfcheck/render；
- `<out>.gate.json`：verdict/verdict_effective/reasons/metrics/calib_warnings/calib_fail/multi_format；
- 交付 PDF：默认无 GMPG；图片/整页叠加需显式 `--layout`。

---

## 四、当前已知限制

1. **图片验收需显式 `--layout`**（或 `LAYOUT_FIGS=1`）；默认 scan2pdf 不自动传 LAYJSON，不出图。
2. **p10 丛书目录作者列**未做（LAYOUT_TOC 仅 p11 aside，S8 残留）。
3. **横排 S4 行数 1:1**：逻辑行口径 ghbq 84.4%，目标 ≥95 未达；build 行合并/受控断行待续。
4. **横排 pitch/页高/overflow**：ghbq gate PASS 96.8%，但 S4 目标（pitch≥99/页高<2/overflow0）未达；fallback 只修满行假设。
5. **竖排验证不进 CI**：本地跑 `verify_vert.py --src-pdf`，证据贴报告。
6. **旧 v13/Web**：`build_pdf_v13.py`、`localhost:8765`、`run_spotting_ocr.py` 仅历史，不再作为主线。
7. **校正文本**：默认自动读 `data/<book>/corrected_text.json`；无文件零回归；行数/坐标不变。
8. **多纸型**：gate 的 multi_format 禁止 auto pass（review_required），不是未实现。

---

## 五、历史说明（v13/Web）

旧文档中的以下内容仅作历史参考，不再按此排障：

- `build_pdf_v13.py` 的 `SRC,OUT,...` argv / Web upload 流程；
- `run_spotting_ocr.py`（由 `ocr_book.py` 取代）；
- `http://localhost:8765` FastAPI Web；
- 固定 12pt/25 字/44.3mm 边距等 v13 参数（当前横排由 geometry 自标定）。

历史归档入口：[docs/battle1_horizontal.md](battle1_horizontal.md)、[docs/scan2pdf_v1.md](scan2pdf_v1.md)（新章节).
