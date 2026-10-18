# 项目代码逻辑（架构梳理）

> 最后核对：2026-10-18，对照实际代码（行数/入口/依赖实测）。
> 本文件回答一个问题：**从一份扫描 PDF，到一份可搜索的还原 PDF，代码是怎么走的。**

---

## 0. 一句话总览

```
扫描 PDF ──OCR──> 行文本 + 坐标(JSON) ──> 【横排链】或【竖排链】 ──> 还原 PDF ──> verify 退出码
                                            ↑ 两条链零代码耦合
```

**两条链完全隔离**：

| | 横排链 | 竖排链 |
|---|---|---|
| 入口 | `src/calibration/fit_positional.py` | `src/pipelines/build_vert.py` |
| TeX 引擎 | **xelatex** + ctex | **uplatex** + tarticle + pxchfon |
| 共享代码 | `src/utils/*` | **零**（不 import `src/utils/*`）|
| 共享数据 | 只有 OCR JSON 格式 | 同左 |
| 验证 | `src/test/verify_geom.py`（pitch/溢出/缺页）| `src/test/verify_vert.py`（页数/字符量/越界）|

**唯一共享的东西是 OCR JSON 的格式**——这是刻意的设计（见 `docs/coupling_analysis.md`）。

---

## 1. OCR 层（两条链共用）

### `src/ocr/run_spotting_ocr.py`（526 行）

调 PaddleOCR-VL-1.6 的云 API（`paddleocr.aistudio-app.com`），**两种模式**：

| 模式 | 开关 | 输出 | 特点 |
|---|---|---|---|
| **spotting**（行级）| `OCR_LAYOUT=0` | 每行文本 + `rec_polys` 坐标 | **有坐标**（排版必需），但**系统性丢符号** |
| **layout**（整页）| `OCR_LAYOUT=1`（默认）| 合并块文本 + 标签 | **符号全**，但**没有行级坐标** |

输出 4 个文件：`*_lines.json`（页→行文本）、`*_coords.json`（页→行 poly）、`*_labels.json`、`*_markdown.json`。

> **关键认知**：两种模式各有缺口，所以要配合用（见 §4 符号补全）。

### 其他 OCR 相关

- `src/ocr/pdf2md.py` — 还原 PDF → Markdown（RAG 用）
- `src/ocr/run_md_layout.py` — layout 模式的 markdown 提取
- `src/ocr/run_ppocrv6_scores.py` / `run_char_score_all.py` — 逐字置信度

---

## 2. 横排链（wz1 / wz3 / wz4 / mgfdmg 四书回归）

### 入口与结构

```
fit_positional.py          (3 行, wrapper: main('build_geom'))
fit_positional_classic.py  (3 行, wrapper: main('build_classic'))
        ↓ 都调
fit_common.py              (95 行, 两趟校准驱动)  ← 真正的逻辑在这里
        ↓ 参数化选择 build_name
build_geom.py (1355 行) 或 build_classic.py (1021 行)
        ↓ 生成 tex → xelatex ×2
还原 PDF
        ↓
verify_geom.py (338 行)
```

**`fit_common.main(build_name)`** 做两趟：

1. **第一趟**：按源书 pitch/字号粗拟合 → 调 `build_*` 渲染出中间 PDF
2. **第二趟**：用中间 PDF 的实测（行位置/字号/溢出）精修参数 → 再渲染

**为什么两趟**：单趟只能按 OCR 盒长拟合，而 OCR 盒对边缘小字偏差 18-40pt；第二趟用真实渲染结果反推才准。

### `build_geom.py` vs `build_classic.py`

- **`build_geom`**：主链（`fit_positional.py` 走它），**逐页跟随源 pitch**（`PER_PAGE_PITCH`）
- **`build_classic`**：变体（escape 规则不同——`_esc_chars` 双反斜杠，见 issue #1）

> `build_pdf_v13.py`（2055 行）是**第三个变体**，argv 顺序不同（`SRC,OUT,...` vs 横排的 `SL,CO,OUT,SRC`），属历史遗留。

### 渲染方式

```
OCR 坐标 → split_polys 拆行片段 → 逐行估算字号/间距 → tex 逐行 \rlap 绝对定位
        → xelatex → verify_geom 量实际 pitch → 不达标调参再渲染
```

---

## 3. 竖排链（wz6 毛选 231 页 / wz7 金瓶梅 1748 页）

### 完整链路

```
data/<book>/<book>_spotting_lines.json      ← 行文本（OCR spotting）
data/<book>/<book>_spotting_coords.json     ← 行坐标
data/<book>/<book>_layout_lines.json        ← 整页文本（OCR layout，符号全）
        ↓
① src/tools/patch_vert_symbols.py           ← 符号补全（layout 的符号补 spotting 的缺）
        ↓ 产出 <book>_spotting_lines_patched.json（坐标不动）
② src/pipelines/build_vert.py               ← 主体（5766 行）
        ↓ vert.tex → uplatex ×2 → dvipdfmx
③ src/test/verify_vert.py (286 行)          ← 验证 + PASS/FAIL 退出码
```

### `build_vert.py` 内部分层（按执行顺序）

| 段 | 职责 |
|---|---|
| **§0 环境/输入校验** | argv（`SL CO OUT [SRC]`）、`VERT_TMP` 按产物名分离、退出码分级（#18）|
| **§1 参数层** | **42 个 `VERT_*` env**，显式值优先；内置兜底表 |
| **§1.9 标定趟 A** | 列数：内框宽÷列距 / 界行线条数−1 / 最外两线跨距 → 三口径取众数 |
| **§1.95 标定趟 B** | 源图墨迹 + OCR + 字体三源标定：`XSCALE`（字宽压缩）、`PUNCT_SIZE/CELL/DX/DY`、`GAP_HANG`、`BR_SIZE`（按括号族）、`INK_RATIO/ASC`、`VERT_METRICS`、`PUNCT_INK` |
| **§1.96 版框/纸张** | 有版框书：外粗线/内细线/界行线检测；无版框书（`NF_MODE`）：伪版心 = 正文行墨迹包围盒 |
| **§1.97 槽格** | 有框：界行线定列；NF：`_ink_bands` 列带 + `_align_rows_slots`。**短列检出**（覆盖率分母 = 该行自身墨迹窗，§1.976）|
| **§1.98 行↔槽配平** | 动态规划：位置先验 + 墨迹跨度代价 + 两种口径取字数多者 |
| **§1.99 特殊元素** | 书眉/页码/边注/影印页贴图/标题署名/西文行/横排页兜底/目录页补救 |
| **§1.995 西文与大字** | 拉丁 TFM 字体（半角比例宽度）、破折号逐条实测定长、标题/署名字号放大 |
| **§1.996 标点** | 竖排形态码位（`（）→︵︶`、`「」→﹁﹂`）、占格/挤格（`PUNCT_CELL`）、墨心定位 |
| **§1.997 引号修复** | OCR 把竖排引号读成「一」→ 按源图墨迹形状判回（taskU，79 处，误改率 0）|
| **§1.998 渲染** | 逐字 `\put` 到格位、横向压缩（`q/K cm` 精确变换，不用 scalebox）、页码序列纠正 |
| **§1.999 编译** | uplatex ×2 + dvipdfmx，失败 → exit 1 |

### 竖排的两个核心概念

**① 槽格（slot grid）**——源书每页的"格子"。竖排书每列是一个槽，槽内从上往下填字。

- **有版框书**（wz6）：界行线直接给出列边界
- **无版框书**（wz7）：伪版心 = 墨迹包围盒，伪槽格 = 列带（`cov=0.12`），格边界 = 相邻带心中点

**② 标定的意义**——所有几何参数从**源图墨迹 + OCR + 字体文件**三源实测，不写死某本书的值。这就是"换书即用"的实现方式。

**③ 渲染方式**——**逐字绝对定位**（不是流式排版）。因为要跟源书对位，不能让 TeX 自己决定字在哪。

---

## 4. 工具层（`src/tools/`）

| 工具 | 用途 |
|---|---|
| **`patch_vert_symbols.py`** | **符号补全**：layout 的符号 + spotting 的坐标，difflib 对齐，只补符号集内字符（引号/括号/句读标点），**几何不动** |
| `classify_fonts.py` / `sample_font_rows.py` | 字体识别抽样 |
| `analyze_pitch.py` / `analyze_fontsize.py` | pitch / 字号统计 |
| `extract_page_numbers.py` / `extract_titles.py` / `extract_toc_rules.py` | 页码 / 标题 / 目录规则抽取 |
| `check_overlap.py` | 渲染后字符视觉重叠检测（横排盲区补充）|
| `test_ocr_orientation.py` | OCR 方向自动纠正实验（待 token 实跑）|
| `mineru_*` | MinerU 对比评估 |

---

## 5. 共享层（`src/utils/`，仅横排用）

| 模块 | 职责 |
|---|---|
| `geometry.py` | 几何基础（bbox/poly 运算）|
| `split_polys.py` | 一个 OCR 行拆成多个片段（横排多片段行）|
| `tex_escape.py` | LaTeX 转义（`_CLASSIC_PAIRS` 等，见 issue #1/#11）|
| `page_numbers.py` | 页码识别 |
| `missing_chars.py` | 缺字检测/替换 |
| `image_blocks.py` | 图页检测（整页贴原图）|

> **竖排不 import 这些**——它的几何/转义都在 `build_vert.py` 里自带。

---

## 6. 测试体系

| 层 | 命令 | 拦什么 |
|---|---|---|
| **unit（414 项）** | `pytest src/test/unit -v` | 转义契约 / 纯函数 / `build_vert` 退出码 / 标定回落 / 各任务专项 |
| **invariants（13 项）** | `pytest src/test/invariants -v` | 结构不变量（如"脚注字号 < 正文字号"）|
| **verify_geom** | `VERIFY_PITCH_FLOOR=85 python3 src/test/verify_geom.py <out.pdf> <coords> <lines>` | pitch 达标率 / 溢出 / 缺页 |
| **verify_vert** | `python3 src/test/verify_vert.py <pdf> <coords> <lines> --src-pdf <src>` | 页数 1:1 / 逐页字符量 / **越界（span + 矢量）** / 页幅 |
| **baseline diff** | 重跑快照 → diff `src/test/snapshots/baseline_*.json` | 量化指标漂移 |

**竖排专项单测**（按任务命名，锁住每次修复）：

`test_vert_calib.py`(28) / `test_vert_noframe.py`(496 行) / `test_vert_taskR.py` / `test_vert_taskS.py` / `test_vert_taskT.py` / `test_vert_taskU.py` / `test_vert_paper_agnostic.py` / `test_vert_punct_vertical.py` / `test_vert_width_gap.py` / `test_build_vert_cli.py`

---

## 7. 数据约定

### 文件命名

```
data/<book>/<book>_spotting_lines.json     # OCR spotting 行文本（"0" → ["行0","行1",...]）
data/<book>/<book>_spotting_coords.json    # 同结构，值是 poly [[x,y],...]（2x px 坐标系）
data/<book>/<book>_layout_lines.json       # OCR layout 整页块
data/<book>/<book>_layout_coords.json
data/<book>/<book>_layout_lines_labels.json
data/<book>/<book>_spotting_lines_patched.json   # 符号补全后（坐标不动）
```

### 临时目录约定

- 横排：`/tmp/seg2_line.*`（**已知并发问题 #10，未修**）
- 竖排：`/tmp/vert_<输出文件名 stem>_run`（**已修 #20**，按产物名分离）

### 产物

- `output/<book>/` — 正式产物（不入库）
- `tmp_vert/` — 实验目录（**git 忽略**）

---

## 8. 已知的历史包袱（改代码前必看）

| 位置 | 问题 |
|---|---|
| `build_geom.py` L254 / `build_classic.py` L256 | `line_font` 引用未定义 `FONT_HD`（疑死代码，#5）|
| `build_classic.py` L1125 | `POS_EST_LOG` 裸 `os.environ[]`（未设则 KeyError，#6）|
| `fit_common.py` L66 | `tempfile.mkdtemp` 未 `rmtree`（临时目录泄漏，#7）|
| `fit_common.py` L14 | `DPI=200` 死代码（#8）|
| `build_geom.py` L930 / `build_classic.py` L1019 | `/tmp/seg2_line.*` 并发冲突（#10，planned）|
| `tex_escape.py` | `_esc_chars` 两方分叉（geom 删单反斜杠 / classic 删双保留单，#11）|
| `build_pdf_v13.py` L42-44 | `escape_tex` 二次转义花括号（#2）|

---

## 9. 一句话记住每条链

**横排**：`fit_positional.py` → `fit_common` 两趟校准 → `build_geom` 生成 tex → xelatex → `verify_geom`

**竖排**：`run_spotting_ocr`（两种模式）→ `patch_vert_symbols`（补符号）→ `build_vert.py`（标定→槽格→配平→渲染）→ `verify_vert`

**共同铁律**：
1. 参数必须**数据驱动自标定**（禁止写死某本书的实测值）
2. **验证器判据不许放宽**（`verify_*.py` 是只读的）
3. 改竖排必须同时验 **wz6 的 `vert.tex` 逐字节不变** + **wz7 verify PASS**
