# 项目代码逻辑（架构梳理，2026-11-11）

> 最后核对：2026-11-11，对照当前 `scan2pdf/ocr_book/quality_gate/geometry/LAYJSON/corrected_text` 实现。
> 本文件回答：**从一份扫描 PDF，到一份可搜索、可门禁交付的还原 PDF，代码怎么走。**
> 历史版本（2026-10-18，run_spotting_ocr/build_pdf_v13 Web 主线）已被本文件取代。

---

## 0. 一句话总览

```
扫描 PDF
  → ocr_book（PaddleOCR API：layout + spotting，批量/断点/JSONL）
  → coords/lines + layout.json
  → corrected_text（可选人工校正）
  → scan2pdf 编排
       ├─ 横排：fit_positional 两趟 → build_geom / build_classic → xelatex
       └─ 竖排：build_vert → uplatex + dvipdfmx
  → verify_geom / verify_vert
  → quality_gate
  → 交付 PDF + .report.json + .calib.json（横排）+ .gate.json
```

**横竖两条链仍零代码耦合**（互不 import、env 命名空间不相交、临时文件不重名、GMPG 只属横排）。

| | 横排链 | 竖排链 |
|---|---|---|
| 生产入口 | `src/tools/scan2pdf.py`（推荐）/ `fit_positional.py`（单链） | `src/tools/scan2pdf.py` / `build_vert.py` |
| OCR | `src/tools/ocr_book.py` spotting+layout | 同左 |
| 渲染 | `fit_common` 两趟 → `build_geom`/`build_classic` → xelatex+xeCJK | `build_vert.py` → uplatex+tarticle+dvipdfmx |
| 共享代码 | `src/utils/*` | `src/vert_*`/内置（**不 import src/utils**） |
| 验证 | `verify_geom.py` | `verify_vert.py` |
| 门禁 | `quality_gate.py`（scan2pdf 调用） | 同左 |
| 典型基线 | ghbq 104 / wz4 677 / wz2 6 | wz6 231 / wz7 300 |

---

## 1. OCR 层（当前：`src/tools/ocr_book.py`）

`ocr_book` 取代历史 `src/ocr/run_spotting_ocr.py`（后者仅历史/不再作为主线入口）。

### 1.1 职责

- 调 PaddleOCR-VL-1.6 API（`paddleocr.aistudio-app.com`）；
- 两种模式：
  - **spotting**（`--mode spotting`）：行文本 + `rec_polys`（坐标，排版必需）；
  - **layout**（`--mode layout`）：`layoutParsingResults` 块（标题/图/页码/旁注）；
  - **both**：两模式都跑；
- 分批（默认 50 页/批）、断点续跑（`jobs.json`）、token 只读；
- 大 batch 返回 **JSONL**（1 行 1 对象，多页在 `layoutParsingResults` 数组）解析（`_load_json_objects`）；
- `convert_raw_dir()`：raw → `coords/lines/labels`（legacy 2×pt，全局 0-based key）；
- `convert_layout_json()`：layout raw → `<book>_layout.json`（canonical page_key/blocks/bbox + legacy `prunedResult`）+ `layout_manifest.json`（sha/页数）。

### 1.2 产物

```
data/<book>/<book>_spotting_lines.json
data/<book>/<book>_spotting_coords.json
data/<book>/<book>_spotting_lines_labels.json
data/<book>/<book>_layout.json            # canonical LAYJSON（scan2pdf 生成/复用）
data/<book>/layout_manifest.json          # 页数/sha/warnings
```

> layout 原始 JSONL 在 `_ocr_<book>/raw/layout_*.json`；scan2pdf 在 `--layout`/LAYOUT_* 开启时用 `find_layout()` 生成或复用。

---

## 2. 编排层（当前主线：`src/tools/scan2pdf.py`）

`scan2pdf` 是**唯一的端到端入口**（Web/v13 已历史化）。

### 2.1 主流程（`main()`）

1. **参数/preflight**：输入存在、输出不覆盖（无 `--force`）、`--skip-ocr`/`--data-dir`；
2. **判书型** `detect_book_type()`：axis（横/竖）、版框、纸型、multi_format；OCR 框长宽比二次校正；
3. **数据准备**：
   - `--skip-ocr`：`find_data(data_dir, coords, lines)`（同源 spotting 优先，禁止 spotting/layout 混配）；
   - 否则调 `ocr_book.py`（layout/spotting/both → raw），再 `find_data`；
4. **LAYJSON**（仅显式开启）：`layout_requested()` 为真（`--layout` 或 `LAYOUT_HEADINGS/FIGS/TOC=1`）才 `find_layout()`；默认 `layout=disabled`；
5. **corrected_text**（可选，默认自动）：`data/<book>/corrected_text.json` 存在则替换 lines（coords 不动），写临时 `lines_corrected.json`；
6. **fix 守卫**：`find_fix()`（显式/书数据；不自动加载 docs 下修复）；
7. **构建**：
   - 横排：`fit_positional.py`（两趟：pass1 估高 + pass2 ratio 表，`build_geom`）；`fit_positional_classic.py` → `build_classic`；
   - 竖排：`build_vert.py`；
   - 构建环境传 `LAYJSON/LAYOUT_*/PAGE_IMAGE_*/CALIB_OUT` 等；
8. **verify**：`verify_geom.py --src-pdf`（横排）或 `verify_vert.py --src-pdf`（竖排）；
9. **gate**：`quality_gate.py`（或内部 `call_gate`），读 PDF/coords/lines/calib，写 gate sidecar；
10. **report**：`<out>.report.json`（步骤/输入 sha/data/book_type/pipeline/gate/calib/resume）；
11. **交付**：成功才覆盖 `--out`；失败不覆盖。

### 2.2 产物（sidecar）

| 文件 | 内容 |
|---|---|
| `<out>.report.json` | 编排审计：input_sha、book_type、pipeline、data、layout、corrected_text、fix、build、gate、calib、exit |
| `<out>.calib.json` | 横排标定审计（schema `horizontal-calib-v1`）：DPI/page/cw/measure/font/baseline/margin/coverage/estimator/fallback/ink/selfcheck/warnings/render |
| `<out>.gate.json` | 门禁：verdict/verdict_effective/reasons/metrics（pitch/height/blank/overflow/line_1to1 等）、calib_warnings/calib_fail、multi_format |
| `<out>` | 交付 PDF |

### 2.3 退出码/失败矩阵

`scan2pdf` 不覆盖已有产物（`--force` 外），exit 2 usage/out_exists、3 data/ocr、4 book、5 build、6 verify、7 reject、8 partial/manual。门禁 `PASS→MANUAL_ONLY` 时 `review_required=true`。

---

## 3. 横排链（geom / classic）

### 3.1 入口与结构

```
fit_positional.py          (wrapper: fit_common.main('build_geom'))
fit_positional_classic.py  (wrapper: fit_common.main('build_classic'))
        ↓
fit_common.main(build_name)   ← 两趟校准
        ↓ pass1: build → POS_EST_LOG / POS_RATIO_TABLE
        ↓ pass2: build → 交付 PDF
build_geom.py (主) / build_classic.py (古籍变体)
        ↓ xelatex
verify_geom.py → quality_gate.py
```

**两趟**：pass1 按源 pitch/字号粗拟合、导出估高；pass2 用实测/估高 ratio 表回填，控制溢出与填充。`fit_common.render()` 的 `VERIFY_MARK` 只在 pass1 开，pass2 交付物无 GMPG。

### 3.2 geom vs classic

- `build_geom`：现代书籍主链，逐页跟随源 pitch（`PER_PAGE_PITCH`），标题层级/脚注/目录/页眉；
- `build_classic`：古籍变体（墨高重叠、注释分列、CJKglue 等）；
- 共享 `src/utils/geometry.py`（calibrate/calib audit）、`tex_escape.py`、`page_numbers.py`、`split_polys.py`、`missing_chars.py`、`image_blocks.py`。

### 3.3 LAYJSON / 图片 / corrected_text

- **LAYJSON**：`LAYOUT_HEADINGS=1`（标题块）、`LAYOUT_FIGS=1`（image/figure/chart/footer_image/header_image 裁贴/整页叠加）、`LAYOUT_TOC=1`（TOC aside，TOC 页跳过重复页码）；默认关；`--layout` 显式开；
- **PAGE_IMAGE_***：`PAGE_IMAGE_PAGES/PREFIX` 手工整页贴图；`PAGE_IMAGE_FULL_RATIO=0.40` 自动整页叠加（源页 raster + 文本 3 Tr，可搜）；未达阈值保持图块裁贴；
- **corrected_text**：`--corrected-text` / 默认 `data/<book>/corrected_text.json`；lines 替换、coords/页数/行数不变；report 审计 path/sha/replaced/skipped/warnings/line_counts。

### 3.4 历史说明

- `build_pdf_v13.py` **仅历史**（旧重排/Web 主线，argv `SRC,OUT,...`）；不再作为 scan2pdf 横排分支；
- `run_spotting_ocr.py` **仅历史**；当前 OCR 统一 `ocr_book.py`；
- `/tmp/seg2_line.*` 并发问题仍为已登记历史（#10，未改）。

---

## 4. 竖排链（build_vert）

```
coords/lines → build_vert.py（§1.9/§1.95 标定 → 槽格 → 行槽配平 → 渲染）
  → vert.tex → uplatex ×2 → dvipdfmx → PDF
  → verify_vert.py --src-pdf → quality_gate.py
```

- 有版框书：界行线定列；无版框书：伪版心 + 墨迹列带（`NF_MODE`）；
- 参数全部源图墨迹/OCR/字体自标定（`VERT_*` 显式优先、兜底表）；
- 逐字绝对定位；书眉/页码/边注/版框/旋转页/引號/破折号/短列等按 spec/vertical；
- 验证：页数 1:1 / 逐页字符量 / span+矢量越界 / 页幅；**不进 CI，本地跑**。

---

## 5. 共享层

### 5.1 `src/utils/`（仅横排 import）

| 模块 | 职责 |
|---|---|
| `geometry.py` | 几何标定：DPI/页尺寸/cw/MEASURE/FONT/BASELINE/coverage/fallback/ink/calib audit/selfcheck |
| `split_polys.py` | OCR 行拆片段 |
| `tex_escape.py` | LaTeX 转义（geom/classic 差异见 #1/#11） |
| `page_numbers.py` | 页码表/layout number 推断 |
| `missing_chars.py` | 缺字检测/裁图 |
| `image_blocks.py` | 图块/书影带裁图、in_figure |

### 5.2 跨链数据契约

- OCR JSON 格式（page_key → texts/coords）是横竖唯一共享契约；
- LAYJSON canonical（`page_key/page/width/height/page_width_pt/page_height_pt/blocks` + legacy `prunedResult`）只横排消费；
- `corrected_text.json` 只改 lines（0-based page/line），横竖均可在 scan2pdf 层应用；
- `PAGE_IMAGE_*`/`LAYOUT_*` 仅横排 env；竖排 env `VERT_*` 不与横排相交。

---

## 6. 验证/门禁/标定

```
build PDF
  ├─ verify_geom (横排) / verify_vert (竖排)
  │    → PASS/FAIL + 指标 stdout + --json 报告
  ├─ <out>.calib.json (横排 build_geom)
  └─ quality_gate.py
       → <out>.gate.json
       → verdict/verdict_effective/reasons/metrics
       → report.gate + review_required
```

- **verify_geom**：页数 1:1、行数（logical line）、页高、pitch、blank/overflow、split/missing；`--src-pdf` 必带（DPI 自适应）；`line_1to1` 为逻辑行口径（t218）。
- **verify_vert**：页数 1:1、逐页字符量、span/矢量越界、页幅；`--src-pdf`。
- **quality_gate**：横排 gate 读 verify 指标 + calib；calib `warn` → `calib_warn:*` 非阻断，`fail` → `calib_fail:*` 且 PASS→MANUAL_ONLY（review_required）；multi_format 同样禁止 auto pass。
- **calib.json**：`horizontal-calib-v1`；`estimator=full_line|fallback`、`cw_source/measure_source/font_source/ink_*`、coverage、warnings、selfcheck、render（产物回填）。
- **gate sidecar**：`<out>.gate.json`；report 中 gate/calib 块与 sidecar 一致。

---

## 7. 数据约定

```
source_pdf/<book>.pdf
data/<book>/<book>_spotting_lines.json
data/<book>/<book>_spotting_coords.json
data/<book>/<book>_layout.json
data/<book>/corrected_text.json          # 可选
output/<book>/<out>.pdf
output/<book>/<out>.pdf.report.json
output/<book>/<out>.pdf.calib.json       # 横排
output/<book>/<out>.pdf.gate.json
```

- page key 0-based（`lines['0']`=源第1页）；coords legacy 2×pt；layout bbox 按页 src/layout 尺度换算；
- 横排临时：`/tmp/seg2_line.*`（历史并发问题）；竖排临时：`/tmp/vert_<stem>_run`（已按产物名分离）。

---

## 8. 已知限制（当前）

| 限制 | 状态/影响 |
|---|---|
| 图片默认不启用 | 需显式 `--layout`/`LAYOUT_FIGS=1`；默认 scan2pdf 不自动传 LAYJSON |
| p10 丛书目录作者列 | `LAYOUT_TOC` 仅 p11 aside；p10 作者列待 S8 |
| 横排 S4 行数 1:1 | 逻辑行口径 84.4%（ghbq），未达 95%；build 行合并/受控断行待续 |
| 横排 pitch/page/overflow | ghbq gate PASS 96.8%，但 S4 目标（pitch≥99/页高<2/overflow0）未达 |
| 竖排验证不进 CI | 本地跑 verify_vert；证据贴报告 |
| v13/Web | 历史，不再主线 |
| 图/条码 | 已支持 p1 封面/p2 条码/p3 图版；p1 页脚 logo 曾在 t199 前丢失，现由整页叠加覆盖 |
| 校正文本 | p3 OCR 错字可由 corrected_text 修；默认自动读取 data/<book>/corrected_text.json |

---

## 9. 一句话记住每条链

- **横排**：`scan2pdf` → `fit_positional` 两趟 → `build_geom` → `verify_geom` → `quality_gate`
- **竖排**：`scan2pdf` → `build_vert` → `verify_vert` → `quality_gate`
- **共同铁律**：数据驱动自标定；验证器判据不放宽；改竖排必须验 wz6 `vert.tex` 逐字节不变 + wz7 PASS。
