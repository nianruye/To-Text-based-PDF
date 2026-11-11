# HORIZONTAL_CALIB.md — 横排几何标定契约（v1）

> **状态**：implemented（t179 审计/t208 S4 fallback：`calibrate()` 低 full_ratio 兜底 + 审计字段；`build_geom.py` 输出 `<out>.calib.json`；scan2pdf 报告 `calib` 块）
> **类型**：governance（横排 geom/classic 共享；跨书、跨纸型）
> **依据**：`src/utils/geometry.py::calibrate()`、`src/pipelines/build_geom.py`、`src/pipelines/build_classic.py`、`src/calibration/fit_common.py`、`src/test/verify_geom.py`
> **对标**：[../vertical/09_calibration.md](../vertical/09_calibration.md)（竖排标定契约）
> **版本**：v1.0（2026-11-09；初始契约，未改产品代码）
> **纪律**：判据/数据分离；决策逻辑不含书目；各书实测值只进参考基线；不 commit

---

## 0. 目的与边界

### 0.1 目的

横排标定目前散落在 `geometry.calibrate()` 的局部规则里：DPI 自适应、页尺寸覆盖率、`cw/MEASURE/FONT/BASELINE` 等有公式、有 env、有兜底，但**没有统一契约、没有自检、没有每书基线 JSON**；换书时只能靠 stdout 和报告口径判断“这次标定是否可信”。

本 spec 定义：

1. 标定项清单：来源、公式、可覆盖 env、合理区间/容差；
2. 自检清单与 warn/fail 语义（默认 warn 不阻断）；
3. 每书 `<book>.calib.json` 契约（审计/回归）；
4. 参考基线（wz1/wz4/ghbq 实测，仅数据，不作判据）；
5. 与竖排 `09_calibration.md` 的对照。

### 0.2 不做的事

- 不改 `calibrate()` 公式/默认值/产物（本任务只写 spec）；
- 不把某本书的 `FONT/BASELINE/DPI` 写成通用判据；
- 不引入新的 OCR/API 调用；
- 不覆盖 `vertical/09_calibration.md`（竖排用源图墨迹标定，横排用 coords/PDF 统计，二者不互相替代）。

### 0.3 当前实现锚点（2026-11-09）

| 项 | 位置 |
|---|---|
| 标定函数 | `src/utils/geometry.py::calibrate(sl, co, DPI=200, src_pdf='')` |
| 横排几何调用 | `src/pipelines/build_geom.py` L29-36（`_G=calibrate(...)`） |
| 古籍横排调用 | `src/pipelines/build_classic.py` L31-38（同一 `calibrate`，单趟；生产入口两趟校准） |
| 两趟校准 | `src/calibration/fit_common.py::main(build_name)`（pass1 估高 + pass2 ratio 表） |
| 目录参数 | `build_geom.py` L484-539（`_TOC_CAL`：`font_line/foot_x/title_max`） |
| 验证 | `src/test/verify_geom.py`（pitch/overflow/missing；**必须 `--src-pdf`**） |

---

## 1. 输入 / 输出 / 优先级

### 1.1 输入

| 输入 | 必需 | 说明 |
|---|---|---|
| `sl`（spotting lines） | ✓ | `{key: [行文本,...]}`；与 coords 同页序 |
| `co`（spotting coords） | ✓ | `{key: [[[x,y],...],...]}`；行 poly |
| `src_pdf` | 推荐 | 实际页幅、DPI 反推、页尺寸覆盖率；缺失时降级（§2.2/§5） |
| `DPI` 初值 | ✓ | 入口默认 200；用于 DPI 自适应的起始假设 |
| env | 选 | 见各标定项；**显式 env > 标定值 > 兜底值**（沿用竖排 09 的优先级） |

### 1.2 输出

- 每次标定 stdout 对账表（`PAGE_W/PAGE_H/DPI/cw/MEASURE/FONT/BASELINE/MARGIN` + 覆盖率/来源）；
- 规划落盘：`<data-dir>/<book>.calib.json`（§4）或 `tmp_vert/calib/<book>.calib.json`；
- `calib.json` 是**数据/审计文件**，不是构建输入；是否作为缓存由后续实现决定。

### 1.3 书无关与判据/数据分离

- `calibrate()` 的公式只使用：coords 统计、src PDF 页幅/样本、env 默认值；**不得出现书名/页号/某书表**。
- 本文 §5 的参考基线（wz1/wz4/ghbq）只用于观察/回归；**不得**写成 `if book=='...'` 或阈值分支。
- 每书 JSON 是数据；阈值是契约常数（可 env 覆盖）；两者不混。

---

## 2. 标定项清单（逐项）

> 记号：`n=len(co)`；`H_src`/`W_src` = 源 PDF 抽样页中位页高/宽（pt）；coords 坐标单位由 `DPI` 换算为 pt；`page_px=PAGE_W*DPI/72`。

### 2.1 DPI（坐标尺度自适应）

| 项 | 内容 |
|---|---|
| 来源 | coords 的 y 最大值（页底） + src PDF 实际页高；目标是把 coords 像素尺度反推为真实 dpi |
| 规则（现行） | `cap = 1.15 * H_src * DPI0 / 72`；`ymax = max(y ≤ cap)`；`dpi_r = round(ymax*72/H_src)`；若 `|dpi_r - DPI0| > 5` 则 `DPI=dpi_r`，否则保留 `DPI0` |
| 保护 | 剔除超出 `cap` 的越界 poly（OCR 噪声）；无 src 时不反推 |
| 合理区间 | **72–600**；`dpi_r` 为整数 dpi |
| env | **当前**：无独立 env（入口 `DPI` 参数=200）；**规划** `HORIZ_DPI`（显式覆盖，优先级最高） |
| 兜底 | 无 src / 无有效 y → `DPI0=200`，日志明示 |
| 容差 | **`dpi_residual = |DPI - ymax*72/H_src| ≤ 5`**；若显式 `HORIZ_DPI_EXPECTED` 给出，`|DPI - expected| ≤ 5` |
| 输出 | `dpi`、`dpi_source=coords+src|default`、`dpi_residual`、`dpi_rounded∈Z` |

> 注意：`DPI=139`（ghbq）不是“偏离 200 失败”，而是**坐标系真实 dpi**；自检比的是反推残差/显式期望，不是入口默认值。

### 2.2 页面尺寸（coords vs src 覆盖率规则）

| 项 | 内容 |
|---|---|
| 来源 | coords 最大 x/y ×72/DPI；src PDF 抽样页中位宽/高 |
| 抽样 | src：`range(0,n,max(1,n//10))` 中位；coords：全量 poly 最大 x/y |
| 规则（现行） | `PAGE_W=round(xmax*72/DPI)`，`PAGE_H=round(ymax*72/DPI)`；若 src 可用：`coverage_x=PAGE_W/W_src`；`coverage_x < PAGE_COVERAGE_THRESHOLD（默认0.95）` → 用 `W_src,H_src` 中位；否则用 coords |
| 审计（新增） | `coverage_y=PAGE_H/H_src`；记录 `coverage={x,y}`；`coverage_x>1.02 or coverage_y>1.02` → **warn `page_size_overcoverage`**（当前公式只查 `<`，不自动改）；**coverage>1 允许至 1.02，属 DPI 估计/坐标边界误差**（≤1.02 不告警） |
| env | `PAGE_COVERAGE_THRESHOLD`（默认 0.95） |
| 合理区间 | `PAGE_W/PAGE_H ∈ [100,2000]pt`；`coverage_x/coverage_y ∈ [0.5,1.5]` 作为 sanity |
| 兜底 | 无 src/无有效坐标 → `405×633`（现行占位）；无 src 时 `source_of_page_size=coords_no_src` |
| 容差 | coords 与 src 中位差 ≤1.5% 或明确覆盖率阈值；超过记录来源 |
| 输出 | `page_size{w_pt,h_pt}`, `coverage{x_ratio,y_ratio,threshold,degraded}`, `source_of_page_size=coords|src_pdf|fallback|coords_no_src` |

**降级记录**：`coverage_x<0.95` 时 `degraded=true,warn=page_size_coverage_low`；无 src 时 `degraded=true` 但不阻断（日志明示）。

### 2.3 `cw`（满行字数）

| 项 | 内容 |
|---|---|
| 来源 | 行文本长度与行 poly 宽；仅 `len(text)>8` 且 coords 存在 |
| 规则 | `maxw=max(widths)`；`full=[len(t) for w,c if w>0.80*maxw]`；`cw=round(median(full))`；无 full → **30** |
| env | `HORIZ_CW`（显式字数，高于 fallback/full_line）；`HORIZ_FONT_MEASURE`（显式字号 pt） |
| 合理区间 | **1–100**；全文书常见 20–50；`cw<5` 或 `>80` → warn |
| 兜底 | 30（无满行/全空） |
| 容差 | 与满行样本中位相差 ≤2 字；`full` 样本 <5 行 → warn `cw_low_sample` |
| 输出 | `cw`, `cw_sample_n`, `cw_source=coords|default|env` |

**低 full_ratio 兜底（t208 / S4）**：

| 项 | 内容 |
|---|---|
| 触发 | `full_ratio = full_lines/eligible < HORIZ_FALLBACK_RATIO`（默认 **0**，env 可调；`0` = 旧 full_line 公式） |
| 估计 | `cw=round(median(全部合格行字数))`；`MEASURE_POLY=round(P90(全部合格行宽px)*72/DPI)`；`MEASURE=MEASURE_POLY`（不再除 `OVERBOUND`，避免满行样本缺失时版心被压窄 1.115×） |
| 字号 | `FONT=round(MEASURE/cw*FONT_SCALE,1)`；`font_source=fallback` |
| 审计 | `estimator=full_line|fallback`、`full_ratio`、`fallback_threshold`、`fallback_sample_n`、`fallback_width_pt`、`fallback_char_median`、`cw_source/measure_source/font_source` |
| 优先级 | `HORIZ_CW`（字数）与 `HORIZ_FONT_MEASURE`（字号 pt）显式覆盖高于 fallback/full_line；full_ratio 高时公式不变 |
| 边界 | 无合格行/样本<2 → 原 30/`PAGE_W*0.8` 兜底并 warn；`HORIZ_FALLBACK_RATIO=0` = 旧公式 |

### 2.4 `MEASURE_POLY` / `MEASURE`（版心宽）

| 项 | 内容 |
|---|---|
| 来源 | 满行 poly 宽中位 ×72/DPI；`OVERBOUND` 安全系数 |
| 规则 | `MEASURE_POLY=round(median(full_widths)*72/DPI)`；`MEASURE=round(MEASURE_POLY/OVERBOUND)`；无 full → `round(PAGE_W*0.8)` |
| env | `OVERBOUND`（默认 1.115）；**规划** `HORIZ_MEASURE` |
| 合理区间 | `MEASURE ∈ [0.5*PAGE_W, 0.95*PAGE_W]`；`OVERBOUND ∈ [1.0,1.5]` |
| 兜底 | `PAGE_W*0.8 // OVERBOUND`；日志记录 |
| 容差 | `MEASURE_POLY` 与满行宽中位差 ≤2pt；`MEASURE` 与 `MEASURE_POLY/OVERBOUND` 精确舍入 |
| 输出 | `measure_poly_pt`, `measure_pt`, `overbound`, `measure_sample_n` |

### 2.5 `FONT`（正文字号 pt）

| 项 | 内容 |
|---|---|
| 来源 | 版心宽 / 满行字数 × `FONT_SCALE` |
| 规则 | `FONT=round(MEASURE/cw*FONT_SCALE,1)`；`FONT_SCALE` 默认 1.0 |
| env | `FONT_SCALE`（默认 1.0）；`HORIZ_FONT_MEASURE`（显式字号 pt，优先级最高）；`HORIZ_FONT` 规划 |
| 合理区间 | **`6 ≤ FONT ≤ 20` pt**（本 spec 硬观测区间；书外字号 warn） |
| 兜底 | 计算失败/`cw=0` → `FONT=10.0` 并 warn |
| 容差 | 与 `MEASURE/cw` 差 ≤0.3pt（`FONT_SCALE=1` 时）；`FONT` 保留 1 位小数 |
| 输出 | `font_pt`, `font_scale`, `font_source=formula|env|fallback`（fallback 见 §2.3） |

### 2.6 `MARGIN` / 页边 / 版心

| 项 | 内容 |
|---|---|
| 来源 | `PAGE_W` 与 `MEASURE` |
| 规则 | `MARGIN=round((PAGE_W-MEASURE)/2)`；左右对称，不单独拟合左右边（OCR 行 x 不作为左右边判据） |
| env | **规划** `HORIZ_MARGIN`（单侧覆盖；默认不设） |
| 合理区间 | `0 ≤ MARGIN ≤ 0.3*PAGE_W`；`MARGIN+MEASURE/2 == PAGE_W/2` ±1pt |
| 兜底 | 计算式天然有值；`PAGE_W<MEASURE` → `MARGIN=0,warn` |
| 容差 | ±1pt（取整） |
| 输出 | `margin_pt`, `type_area_pt`（=`MEASURE`），`margin_symmetric=true` |

### 2.7 `BASELINE` / `LINESPREAD`（行距）

| 项 | 内容 |
|---|---|
| 来源 | 同页相邻行 y 间距（coords） |
| 规则 | 每页按行 y 升序；`10 < Δy < 80`（px）取样本；`BASELINE=round(median(Δy)*72/DPI,1)`；无样本 → `round(FONT*1.5,1)` |
| env | **规划** `HORIZ_BASELINE`（显式覆盖） |
| 合理区间 | `BASELINE/FONT ∈ [1.2,2.0]`；`BASELINE ∈ [FONT, FONT*2.2]` |
| 兜底 | `FONT*1.5`；`pitch_sample_n<10` → warn |
| 容差 | `LINESPREAD=round(BASELINE/(FONT*1.2),3)`；与源行距中位差 ≤3%（由 verify pitch 复核） |
| 输出 | `baseline_pt`, `linespread`, `pitch_sample_n`, `baseline_source=coords|fallback|env` |

### 2.8 `FONT_SM` / `H_BODY`（小字与正文字高）

| 项 | 内容 |
|---|---|
| 来源 | `FONT*0.78`；行 poly 高度中位 |
| 规则 | `FONT_SM=round(FONT*0.78,1)`；`H_BODY=median(heights)`（px；无样本 → 36） |
| env | 无（派生量）；`HORIZ_FONT_SM` 规划 |
| 合理区间 | `FONT_SM ∈ [0.6*FONT, 0.9*FONT]`；`H_BODY > 0` |
| 兜底 | `H_BODY=36px`；`FONT_SM=FONT*0.78` |
| 容差 | 与公式差 ≤0.1pt |
| 输出 | `font_sm_pt`, `h_body_px` |

### 2.9 目录参数（`font_line` / `foot_x` / `title_max`）

| 项 | 内容 |
|---|---|
| 来源 | 扫描目录页（`_TOC_PAGE`）的标题行/页脚/条目长度分布 |
| TOC 页判定 | 页内含“目录/目錄”标记，或 ≥5 条 `TOC_ENTRY_RE`（点引导+页码）；`toc_pages` 记录页 key |
| `font_line` | TOC 标题行字号中位 ×1.15（≥3 行）；否则 `FONT*1.25` |
| `foot_x` | 页脚 x 中心按页面桶聚类；`(max(0,b-5)/100, min(95,b+10)/100)`；无可信簇 → `(0.15,0.85)` |
| `title_max` | TOC 标题字数 q80（≥10 条）→ `max(10,q80)`；否则 14 |
| env | **规划** `HORIZ_TOC_FONT_LINE` / `HORIZ_TOC_FOOT_X` / `HORIZ_TOC_TITLE_MAX`（当前用硬编码局部规则，未接 env） |
| 合理区间 | `font_line ∈ [FONT*0.9,FONT*1.8]`；`0≤foot_x0<foot_x1≤1`；`10≤title_max≤80` |
| 兜底 | `font_line=FONT*1.25`、`foot_x=(0.15,0.85)`、`title_max=14`；无 TOC → 三项 `null` + `toc_pages=[]` |
| 容差 | 与 TOC 样本中位差 ≤10%；无 TOC 不判 error |
| 输出 | `toc_params{font_line,foot_x,title_max,toc_pages,source}` |

### 2.10 覆盖率/样本量

| 项 | 内容 |
|---|---|
| 来源 | 满行样本、pitch 样本、TOC 样本、src 抽样 |
| 规则 | 记录 `lines_total/lines_full/full_ratio`、`pitch_sample_n`、`toc_sample_n` |
| 降级 | `full_ratio<0.3` 或 `full<5` → `coverage_degraded=true`；`pitch_sample_n<10` → `baseline_degraded=true`；TOC 样本不足 → `toc_degraded=true` |
| 输出 | `coverage{full_lines,full_ratio,pitch_samples,toc_samples,degraded,estimator,fallback_threshold,fallback_sample_n,fallback_width_pt,fallback_char_median}` |

---

## 3. 自检清单与 warn/fail 语义

### 3.1 自检表

| # | 检查 | 阈值/口径 | 默认级别 | 说明 |
|---|---|---|---|---|
| 1 | 页数 1:1 | `len(sl)==len(co)==src_pages`（若给 src） | **FAIL** | 缺页/多页不可标定；不得补空页 |
| 2 | coords/lines 非空 | `n>0` 且至少 1 行/1 poly | **FAIL** | 无法标定 |
| 3 | pitch 误差 | 产物/源 pitch 中位相对误差 **<3%**（`verify_geom` 复核；标定阶段可先记样本中位） | **WARN** | 默认不阻断；strict 升 FAIL |
| 4 | DPI 反推残差 | `|DPI - ymax*72/H_src| ≤5`（或显式 expected 差 ≤5） | **WARN** | 无 src 时跳过 |
| 5 | FONT 区间 | `6 ≤ FONT ≤ 20` pt | **WARN** | 超出说明字号/版心/样本异常；不阻断 |
| 6 | BASELINE/FONT | `1.2 ≤ BASELINE/FONT ≤ 2.0` | **WARN** | ghbq 实测 2.073 会触发（§6） |
| 7 | 页尺寸覆盖率 | `coverage_x<0.95` → src 降级记录；`coverage_x/y>1.02` → overcoverage warn | **WARN** | 降级必须写 `source_of_page_size` |
| 8 | `MEASURE`/`MARGIN` | `0.5W≤MEASURE≤0.95W`；`0≤MARGIN≤0.3W` | **WARN** | 版心异常 |
| 9 | `cw` | `1≤cw≤100`；`cw<5 or >80` warn | **WARN** | 满行样本异常 |
| 10 | TOC 参数 | `font_line/foot_x/title_max` 区间；无 TOC 跳过 | **WARN** | TOC 不存在不算失败 |
| 11 | 样本量 | `full<5`/`pitch<10`/TOC<3` | **WARN** | 记录 `coverage_degraded` |
| 12 | 页面尺寸来源 | `source_of_page_size` 必须 ∈ {coords,src_pdf,fallback,coords_no_src}；降级时必须有原因 | **FAIL**（未设置） | JSON 契约字段 |

### 3.2 warn/fail 策略

- **默认 `mode=warn`**：除 #1/#2/#12 外，其余一律 WARN；不阻断构建（与现行行为兼容）。
- **`HORIZ_CALIB_STRICT=1`**（规划）：WARN 升为 FAIL，构建前退出；用于新书/基线冻结。
- **FAIL** 不静默：stdout + `calib.json.warnings[]` + `selfcheck.verdict=fail`；**构建不阻断（exit 0）**，由 scan2pdf/gate 兜底：FAIL 项写入 gate `reasons` 的 `calib_fail:<code>`，且该产物由 PASS 降为 MANUAL_ONLY（`review_required=true`），不得静默放行。
- **失败/降级可审计**：每项写 `code`、`severity`、`detail`、`source`；`warnings` 至少包含降级原因。

---

## 4. 每书标定基线 JSON 契约（`<book>.calib.json`）

### 4.1 路径

- 默认：`<data-dir>/<book>.calib.json`；或 `tmp_vert/calib/<book>.calib.json`（实现选择，报告写清）。
- 文件名只由 `book` slug 决定；**不得写死书路径**。
- JSON 是审计/回归文件；同一输入应可复现（sha256 + 版本 + 无时间戳/无随机排序）。

### 4.2 字段

```json
{
  "schema_version": "horizontal-calib-v1",
  "status": "planned|measured|implemented",
  "book": "example",
  "src_pdf": "source_pdf/example.pdf",
  "sha256": "<source pdf sha256>",
  "pages": 123,
  "dpi": {
    "value": 200,
    "source": "coords+src|default|env",
    "residual": 0.2,
    "expected": null
  },
  "page_size": {
    "width_pt": 405,
    "height_pt": 633,
    "source": "coords|src_pdf|fallback|coords_no_src",
    "unit": "bp",
    "coords_width_pt": 405,
    "coords_height_pt": 633,
    "src_width_pt": 405,
    "src_height_pt": 634
  },
  "render": {
    "page_pt": {"width_pt": 403.5, "height_pt": 630.6},
    "font_pt": 10.1,
    "pitch_pt": 17.98,
    "pass": true,
    "unit": "bp"
  },
  "cw": 31,
  "cw_source": "coords|fallback|env",
  "measure": {
    "poly_pt": 349,
    "pt": 313,
    "overbound": 1.115,
    "source": "full_line_overbound|fallback_uncut"
  },
  "font": {
    "pt": 10.1,
    "scale": 1.0,
    "source": "formula|env|fallback"
  },
  "baseline": {
    "pt": 19.0,
    "font_ratio": 1.881,
    "linespread": 1.568,
    "source": "coords|env|fallback"
  },
  "margin_pt": 46,
  "font_sm_pt": 7.9,
  "h_body_px": 40.5,
  "toc_params": {
    "font_line": null,
    "foot_x": null,
    "title_max": null,
    "toc_pages": [],
    "source": "none|geom_toc_cal"
  },
  "coverage": {
    "x_ratio": 1.0,
    "y_ratio": 1.0,
    "threshold": 0.95,
    "degraded": false,
    "full_lines": 120,
    "full_ratio": 0.72,
    "pitch_samples": 400,
    "toc_samples": 0
  },
  "source_of_page_size": "coords|src_pdf|fallback|coords_no_src",
  "warnings": [],
  "selfcheck": {
    "pages_1to1": true,
    "pitch_error_pct": null,
    "dpi_residual": 0.2,
    "font_in_range": true,
    "baseline_font_ratio": 1.881,
    "coverage_degraded": false,
    "toc_in_range": null,
    "verdict": "warn|fail|pass"
  },
  "env": {
    "PAGE_COVERAGE_THRESHOLD": "0.95",
    "OVERBOUND": "1.115",
    "FONT_SCALE": "1.0"
  },
  "created_by": "horizontal-calib-v1"
}
```

### 4.3 字段规则

| 字段 | 必填 | 规则 |
|---|---|---|
| `book` | ✓ | slug；不含路径/空格 |
| `src_pdf` | ✓ | 相对仓库路径（只读源） |
| `sha256` | ✓ | 源 PDF hash；无 src 时 `null` + `source_of_page_size=coords_no_src` |
| `pages` | ✓ | 源页数/coords 页数；1:1 已校验 |
| `dpi` | ✓ | `value/source/residual/expected`；residual 是反推残差，不是“与 200 的差” |
| `page_size` | ✓ | `width/height/source`（coords/src_pdf/fallback/coords_no_src）+ coords/src 原值；审计用 |
| `cw` | ✓ | 满行字数；`cw_source` 可写 `coords/default` |
| `measure` | ✓ | `poly_pt/pt/overbound`；`pt=round(poly/overbound)` |
| `font` | ✓ | `pt/scale/source`；1 位小数 |
| `baseline` | ✓ | `pt/font_ratio/linespread/source` |
| `margin_pt` | ✓ | 对称边距；`type_area` 与 measure 同值 |
| `font_sm_pt/h_body_px` | ✓ | 派生；可为 null（样本不足）时写 `null` + warning |
| `toc_params` | ✓ | 无 TOC 时三个值 null + `source=none`；不得伪造 |
| `coverage` | ✓ | 样本量/覆盖率/降级 |
| `source_of_page_size` | ✓ | 枚举 {coords,src_pdf,fallback,coords_no_src}；与 `page_size.source` 一致 |
| `warnings` | ✓ | `[{code,severity,detail}]`；无则 `[]` |
| `selfcheck` | ✓ | 每项 bool/null + verdict |
| `env` | ✓ | 生效 env 的字符串快照；不含 token/密钥 |

> **JSON 不写 token、不写书页白名单、不写 OCR raw 路径**；只写标定输入来源与统计。

---

## 5. 参考基线（只作数据，不作判据）

> 实测命令：`/usr/bin/python3 -B` 调 `src.utils.geometry.calibrate(sl,co,200,src_pdf=...)`；日期 2026-11-09（Asia/Shanghai）。
> 这些值**不是**通用阈值；换书必须重标，不得在代码里写 `if book=='wz4'`。

| 书 | 数据/source | pages | DPI | 页尺寸(pt) | cw | MEASURE | FONT | BASELINE | BASELINE/FONT | coverage | source_of_page_size | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| wz1 | `data/wz1/wz1_spotting_*` + `source_pdf/wz1.pdf` | 222 | 200 | 405×633 | 31 | 313 | 10.1 | 19.0 | 1.881 | 1.000 | coords | 参考 |
| wz4 | `data/wz4/wz4_spotting_*` + `source_pdf/wz4.pdf` | 677 | 144 | 418×634 | 28 | 300 | 10.7 | 17.8 | 1.664 | 1.000 | coords | 参考；DPI 144 |
| ghbq | `output/ghbq_full/_ocr_ghbq/ghbq_spotting_*` + `source_pdf/ghbq.pdf` | 104 | 139 | 603×870（实际源 595×868） | 25 | 413 | 16.5 | 34.2 | **2.073** | 1.013 | coords | 横向样书；ratio 越 2.0 → **warn**；coverage 1.013 在 1.02 内 |

- `wz1/wz4` 的 DPI 差异（200/144）证明**DPI 必须自适应**，不能固定 200；
- `ghbq` 的 `BASELINE/FONT=2.073` 是自检 WARN 的实测样例（不阻断，但记录）；
- `ghbq` 的 page_size 用 coords（603×870）而非 src（595×868），coverage 1.013；若未来收紧到 `>1.02 warn`，此例仍在容差内；
- `toc_params` 未在这些书的全量数据上抽样，故参考基线不填；实现时按 §2.9 计算并写 JSON。

---

## 6. 与竖排 `09_calibration.md` 的对照

| 维度 | 横排（本 spec） | 竖排 09 |
|---|---|---|
| 输入 | coords/lines + src PDF | 源图墨迹 + OCR + 字体文件 |
| 主要参数 | DPI、页尺寸、cw、MEASURE、FONT、BASELINE、TOC | N_COL_FRAME、XSCALE、PUNCT、BR_SIZE、INK_RATIO 等 |
| 标定触发 | 构建时 `calibrate()` 一次 | 建排前标定趟（多阶段 + 字体探针） |
| 产物 | stdout + `<book>.calib.json`（规划） | `$VERT_TMP/vert_calib.json` |
| 自检 | 页数/DPI/FONT/ratio/覆盖率 | 对账表 + verify_vert + 零回归 |
| 共同点 | 书无关、env 优先、兜底不假装、每书报告 | 同 |

> 横排不因本 spec 改成“源图墨迹标定”；竖排也不复用本 spec 的 coords 公式。两套契约并列。

---

## 7. 实施与验收（后续任务）

### 7.1 实施步骤

1. `calibrate()` 增加 **只读统计输出**（不改变现有返回值/产物）：`coverage_y`、`page_size_source`、`warnings/selfcheck`；
2. 新增 `<book>.calib.json` writer（可选，`--calib-json`/env 开关）；默认行为不变；
3. 自检默认 warn，`HORIZ_CALIB_STRICT=1` 才 fail；
4. `fit_positional` 两趟校准把 pass1/pass2 的 ratio 写入 `calib.json`（`selfcheck.pitch_error_pct` 可由 verify_geom 回填）；
5. 单元测试：合成 coords 覆盖/降级、DPI 反推、页码 1:1、FONT/BASELINE 区间、TOC 参数、JSON schema。

### 7.2 验收（v1 落地时）

- 对 wz1/wz4/ghbq 重跑，`calib.json` 的关键值与本 spec §5 一致（允许 1 位小数/舍入）；
- wz1/wz4 的 `verify_geom --src-pdf` PASS，pitch 与现有基线一致；本 spec 不改产物；
- 合成异常输入（coverage 0.72）→ `source_of_page_size=src_pdf` + 降级 warning；无 src → coords_no_src + warning；
- FONT/BASELINE/FONT/coverage/DPI 自检每条都有 warn/fail 样本；
- 判据中 `grep` 无书名/页号硬编码；参考基线只在文档/JSON，不在公式。

### 7.3 本任务 DoD

本任务**只写 spec**：

- 新增 `spec/governance/HORIZONTAL_CALIB.md`；
- 未改 `src/utils/geometry.py`/`build_geom.py`/`build_classic.py`/数据/产物；
- 未 commit；未调 API；
- 参考基线来自本地只读 `calibrate()` 复算，非新 API。

---

## 8. 已知边界/待决

1. **页尺寸覆盖率现行只查宽**：本 spec 记录 `coverage_y` 并给 overcoverage warn；是否改成 `min(x,y)` 需后续实现 + baseline diff（不得本次静默改）。
2. **ghbq `BASELINE/FONT=2.073`**：超出 [1.2,2.0]；按默认 WARN 不阻断；是否调参/区分短页/标题页需实测，不把 ghbq 值写死。
3. **TOC 参数**：仅在 `build_geom.py` 内计算；`build_classic`/v13 的 TOC 口径不同，本 spec 先锁 geom；classic 后续纳入时须单列。
4. **DPI**：`HORIZ_DPI`/`HORIZ_DPI_EXPECTED` 为规划 env，当前无独立 env；实现前不要声称可覆盖。
5. **pitch 误差**：标定阶段只能先记源行距样本；最终 <3% 需 `verify_geom` 回填，不能在 `calibrate()` 内伪造。
6. **JSON 路径**：`<data-dir>/<book>.calib.json` 与 `tmp_vert/calib/...` 二选一由实现决定，报告写清；不得写到共享 `/tmp` 固定名造成并发冲突。


---

## 6. 实现锚点（t179）

| 项 | 位置 |
|---|---|
| 审计字段 | `src/utils/geometry.py::calibrate()` 返回 `dpi_residual/coverage_x/y/source_of_page_size/cw_sample_n/full_lines/full_ratio/pitch_sample_n/pitch_median_pt/font_source/baseline_source` 等 |
| JSON 组装 | `src/utils/geometry.py::build_calib_doc()`（schema `horizontal-calib-v1`） |
| 自检 | `src/utils/geometry.py::calib_selfcheck()`（spec §3；默认 warn，fail 项写 `selfcheck.verdict=fail`，不阻断） |
| 落盘 | `src/pipelines/build_geom.py` 在 TOC 校准后写 `CALIB_OUT`（默认 `<out>.calib.json`）；`CALIB_BOOK` 由调用方给 |
| scan2pdf | `build_pdf` 设 `CALIB_OUT/CALIB_BOOK`；geom gate 读 `<out>.calib.json` → `report['calib']` + gate `calib_warnings`（非阻断） |
| 单测 | `src/test/unit/test_horizontal_calib.py` 4 例 |

> 注：页子集构建（`--pages`）时 `src_pdf` 仍是全本，`pages` 只与 coords 1:1；`src_pages_diff` 记为 warn（非 fail）。

---

## 8. 逻辑行口径（t218 / S4-R2）

> 目标：消除“同一 OCR 行在 PDF 中被 x 间隔拆成多个 span”对行数 1:1 指标的污染；
> 渲染端与 verify 端使用同一口径。

### 8.1 定义

**逻辑行（logical line）= 同一页内 y 中心落在同一视觉基线的文本行。**

- verify 侧：对页内所有 text span/line 的 `y_center` 升序；相邻 `|Δy_center| ≤ 0.5 × median(line_height)` 归为同一逻辑行；bbox 取并集（top/bottom/x0/x1）。
- build 侧：**一条 OCR spotting 行 = 一条逻辑行**；正文不得因 OCR 行内 x 间隔（片段 gap）拆成多个独立行/span。仅当自然宽度 > 版心时允许受控断行，并在 `[分片]` 日志记录 `page/key/text_len/width`；断行不改变 OCR 行数口径（逻辑行仍以源行为准）。
- 源/输出两侧同一函数、同一容差；`line_1to1 = logical_lines_out == logical_lines_src` 的页占比。

### 8.2 审计

`verify_geom` 输出：
- 人类可读：`line_1to1: <pct>% (logical line)`；
- JSON：`agg.line_1to1`（与 `n_eq_pct` 同值，保留旧字段兼容）。

### 8.3 fallback 字号与墨高交叉验证（t218）

- `font_ink = median(合格行 poly 高度 px) × 72 / DPI / 0.88`。
- 仅 `estimator=fallback` 且无 `HORIZ_CW`/`HORIZ_FONT_MEASURE` 显式覆盖时：
  - `|FONT - font_ink| / font_ink > 0.20` 且 `font_ink ∈ [6,20]` → 用 `font_ink`，`font_source=fallback_ink`，日志 `[标定·ink]`；
  - 差 >20% 但 `font_ink ∉ [6,20]`（ghbq ink=23.5）→ **保留 fallback**，`ink_applied=false`、`ink_reject=out_of_range`，记录“无收益回退”证据；
  - `HORIZ_INK_CALIB` 默认 **0**（关闭 ink 交叉）；`HORIZ_FALLBACK_RATIO` 默认 **0**（旧 full_line 公式）；两者仅在显式设值时启用。
- calib `font` 块增 `ink_pt/ink_applied/ink_reject`。

### 8.4 当前实测（t218）

- ghbq：逻辑行 1:1 **84.4%**（96 可比页），页高<5% 17.7%（中位6.6%）、overflow26、pitch94.8%；目标≥95/<2/0/≥99 **未达**。
- 旧 span 口径 35.1% → 逻辑行口径 84.4% 说明口径修复有效，但剩余 15 页仍是 build 端输出行数与源行数不等（部分页输出多/少 1-2 行）；需后续 build 行合并/受控断行继续处理。
- fallback：ghbq full_ratio0.028、font_est18.4、font_ink23.5、ink_reject=out_of_range → 保留18.4；warnings 只剩 toc_low_sample。
- wz1/wz2/wz4 full_ratio高 → full_line，零回归。

### 8.5 verify overflow/extent 与 TOC 口径（t228）

- `_content_extent(lines, page_h, page_w, h_ref)`：给定 `h_ref`（源页行高中位）时，两侧统一按 `line_center ± h_ref/2` 计算内容顶/底；不直接比较 output text bbox（52.4pt）与 source poly（19.8pt）——那是字形/行盒高度差，不是版面溢出。
- 若 output 正文顶整体比源低 >2% 页高（`body_shift`），且底未越过页幅 97%，按 **layout shift** 记录，不计 overflow；只有越过源底 +3% 且顶未整体下移，或底越过页幅 97%，才计 overflow。
- TOC/目录页（显式 `目录`/`CONTENTS`，或 ≥5 条「编号+短条目」）从 pitch/line 可比样本排除（dotfill 行距不可比）；row 记 `toc=true`。
- 实测（ghbq）：overflow 26→**0**（body_shift 3 页），pitch 95.9→**97.9%**（排除 p10/p11 目录页），line_1to1 97.9%。
