# src/ 暗中耦合分析报告

> **范围**：`/opt/test/src/` 下全部 .py 文件，只读分析，未修改任何源码。
> **方法**：3 个并行分析代理逐文件深读 + grep 提取行号级信息。
> **目的**：揭示文件间靠环境变量、subprocess、共享数据格式、argv 约定暗中耦合的机制，为安全重构提供风险地图。

---

## 1. 依赖图

### 1.1 文件依赖关系（import + subprocess）

```
                         ┌── import ──> utils/tex_escape.py (叶子,无import)
                         ├── import ──> utils/geometry.py (import os,statistics)
                         ├── import ──> utils/page_numbers.py (import os,json,re)
fit_positional.py (3行) ─┤    ┌── import ──> utils/image_blocks.py (条件import fitz,PIL)
  main('build_geom') ────┼──> fit_common.py (90行) ── subprocess ──> build_geom.py ── subprocess ──> xelatex
                         │    │  render(build_name)                     │
fit_positional_classic   │    │  L23: ../pipelines/<build_name>.py      ├── import ──> _latex_preamble.py (叶子)
  (3行)                  ┘    │  L26: subprocess.run(python3 _build)     │
       main('build_classic')─┘                                         │
                                                          build_classic.py ── subprocess ──> xelatex
                                                          (import L13-17 与 geom 完全一致)

build_pdf_v13.py ── subprocess ──> xelatex     【src/ 内零入边，仅 archive/ 调】

conftest.py ── subprocess ──> build_geom.py / build_classic.py (测试 fixture)
test_pure_funcs.py ── AST 提取 ──> build_geom/classic/v13 (非 import，不执行)
verify_geom.py ── 无 subprocess，仅 fitz 读 PDF
```

### 1.2 逐文件依赖清单

| 文件 | 依赖（import） | 依赖（subprocess） |
|---|---|---|
| fit_common.py | sys,os,json,subprocess,re,statistics,tempfile,fitz | `python3 ../pipelines/<build_name>.py` (L23-26) |
| fit_positional.py (3行) | fit_common.main | - |
| fit_positional_classic.py (3行) | fit_common.main | - |
| build_geom.py | utils.tex_escape/geometry/page_numbers/image_blocks + _latex_preamble (L13-17) | xelatex (L932) |
| build_classic.py | 同 build_geom (L13-17 逐行一致) | xelatex (L1021) |
| build_pdf_v13.py | json,os,re,subprocess,sys,statistics,fitz; 条件: unicodedata(L1065), predict(L1132) | xelatex (L2043) |
| _latex_preamble.py | 无（纯叶子） | - |
| tex_escape.py | 无（纯叶子） | - |
| geometry.py | os, statistics | - |
| page_numbers.py | os, json, re | - |
| image_blocks.py | 条件: fitz, PIL.Image | - |
| conftest.py | json,os,subprocess,time,pathlib,pytest; 条件: fitz | `/usr/bin/python3 src/pipelines/build_geom.py`(L132) / `build_classic.py`(L141) |
| verify_geom.py | sys,json,statistics,argparse,re,os,fitz | 无 |
| test_pure_funcs.py | _loader.load/MockT2S, utils.tex_escape.escape_latex, pytest | AST-load(非import): build_pdf_v13/build_classic/build_geom |

### 1.3 特别标注

**fit_positional.py / fit_positional_classic.py 的重复**
- 已消除：原 97×2=194 行，现 3+3+90=96 行（fit_common 共享，build_name 参数化）。
- fit_common.py:90行 `render(build_name)` L23 拼路径 `../pipelines/<build_name>.py`，L26 `subprocess.run(['python3', _build, SL, CO, out_pdf, SRC])`。
- 下游：fit_positional -> fit_common.render(build_name='build_geom') -> subprocess `build_geom.py`；fit_positional_classic -> fit_common.render(build_name='build_classic') -> subprocess `build_classic.py`。

**build_geom.py / build_classic.py 的共享逻辑**
- import 共享模块**完全一致**（L13-17 逐行相同）：`utils.tex_escape.escape_latex`、`utils.geometry.calibrate`、`utils.page_numbers.{load_pntab,infer_lay_numbers,PN_RE}`、`utils.image_blocks as _img`、`_latex_preamble.build_latex`。
- **不 import 对方**--grep 全仓无 `import build_geom` / `import build_classic` 的跨管线引用。共享逻辑靠 utils/* 与 _latex_preamble 抽出，非靠 import 对方。
- 两者都 subprocess 调 xelatex（geom L932 / classic L1021）。

**build_pdf_v13.py 是否还被依赖**
- **在 src/ 内完全孤立**：无任何 src/ 文件 import 它，也无任何 src/ 文件 subprocess 调用它。
- 唯一的真实调用者在 src/ 之外：`archive/app/services/processor.py:405-406` subprocess 调 `/opt/test/build_pdf_v13.py`（archive 已归档）。
- src/ 内仅被 `test/unit/test_pure_funcs.py` 经 `_loader.load()` AST 提取纯函数（非 import，不执行顶层副作用）。
- 自身 subprocess 调 xelatex（L2043），有条件 `from predict import`（L1132，predict 仅存在于 `archive/font_classifier/predict.py`，src/ 内无法解析）。
- 结论：旧管线，已被 build_geom/build_classic 取代，src/ 活跃流程中不再被调用。

### 1.4 孤立文件清单（无被依赖 / 无入边）

**完全孤立（含旧管线，需关注）**
- `pipelines/build_pdf_v13.py` - src/ 内零入边，仅 archive/ 调用

**入口脚本 / 工具（设计上无入边，正常）**
- `calibration/fit_positional.py`、`calibration/fit_positional_classic.py` - 薄壳入口
- `tools/analyze_fontsize.py`、`tools/analyze_pitch.py`、`tools/extract_page_numbers.py`、`tools/extract_titles.py`、`tools/mineru_eval.py`、`tools/mineru_geom.py`、`tools/reocr_wz2_failed.py`
- `ocr/run_spotting_ocr.py` - 仅被 reocr_wz2_failed import
- `test/test_cases.py`、`test/verify_geom.py`、`test/invariants/test_invariants_*.py`、`test/unit/test_pure_funcs.py`

**有入边（非孤立）**
- fit_common(←fit_positional*)、build_geom/build_classic(←fit_common subprocess、←conftest subprocess)、_latex_preamble/tex_escape/geometry/page_numbers/image_blocks(←两管线)、run_spotting_ocr(←reocr_wz2_failed)、conftest(←两 invariants 测试)、_loader(←test_pure_funcs)。

---

## 2. 状态地图

### 2.1 环境变量（16 个重点）

| 环境变量 | 默认值 | 缺失后果 | 共享? | 读取位置 |
|---|---|---|---|---|
| LAYJSON | `''` | 无版面块，走启发式兜底 | geom+classic 共享 | geom:258 / classic:256 |
| PAGE_FONT | `''` | BODY_FONT=NOTE_FONT=FONT，无双字号 | 共享 | geom:481,589,610 / classic:483,595,617 |
| POSITIONAL | `''` | USE_POS=False，不做位置还原 | 共享（fit_common 强制 '1'） | geom:221 / classic:223 |
| PER_PAGE_PITCH | `''` | 全用全局 LINESPREAD | 共享 | geom:95 / classic:96 |
| LAYOUT_HEADINGS | `''` | USE_LAY_HEAD=False，仅启发式标题 | 共享 | geom:294 / classic:296 |
| OVERBOUND | `'1.115'` | 用 1.115 | 共享（经 geometry） | utils/geometry.py:33 |
| FONT_SCALE | `'1.0'` | 用 1.0 | 共享（经 geometry） | utils/geometry.py:35 |
| PUNCT_WEIGHT | `'0.2'` | 用 0.2 | 共享（经 geometry） | utils/geometry.py:47 |
| REGION_LAYOUT | `''` | USE_REGION=False | 共享 | utils/geometry.py:48 + geom:775,823 / classic:773,825 |
| REGION_FONT_SCALE | `'1.03'` | 用 1.03 | 共享（经 geometry） | utils/geometry.py:49 |
| PAGENUM_GLOBAL_TABLE | `''` | pntab={}，退回 OCR/layout number | 共享（经 page_numbers） | utils/page_numbers.py:17 |
| PAGENUM_OFFSET | `'0'` | offset=0 | 共享 | geom:37 / classic:37 / v13:711 |
| TOC_HEADING_MAP | `''` -> `/tmp/toc_map.json` | 两级回退：先试 /tmp/toc_map.json，再自动扫描 | 共享 | geom:63 / classic:64 / v13:1303 |
| POS_FILL | 管线 `'1.08'` / fit `'0.95'` | 管线单趟用 1.08；fit pass2 用 0.95 | 共享（fit_common 覆写） | geom:756,804 / classic:804 / fit_common:89 |
| VERIFY_MARK | `''` | 不注入 GMPG 标记；verify 退回按序号 1:1 | 共享（fit_common 强制 '1'） | geom:524,609,630,926 / classic:545,610,630,1015 |
| POS_EST_LOG | `''` | 不导出估高 JSON | 共享（fit_common 设） | geom:926-927 / classic:1015-1016 |
| POS_RATIO_TABLE | `''` | _pos_ratio={}，无每页比值校正 | 共享（fit_common 设） | geom:137 / classic:139 |

**其余环境变量**

| 环境变量 | 默认值 | 归属 |
|---|---|---|
| MARKER_SCALE | `'0.55'` | 共享 |
| GRID_PITCH | `''` | 共享 |
| LINE_LEVEL | `''` | v13 独立 |
| GEOM_FONT / GEOM_TARGET / GEOM_STRETCH | (无) | v13 独立 |
| TOC_HEADING_MAP_OUT | (无) | v13 独立 |
| VERIFY_PITCH_FLOOR / VERIFY_HEIGHT_FLOOR / VERIFY_N_EQ_FLOOR / VERIFY_BLANK_MAX | `'0'`/`'0'`/`'0'`/`'inf'` | verify 独立 |
| OCR_LAYOUT | `'1'` | OCR 独立 |
| INV_N / INV_GEOM_START / INV_CLASSIC_START | `'30'`/`'40'`/`'60'` | 测试独立 |

**隐式 env 传递（关键设计）**：`fit_common.py:17` `env = dict(os.environ)` 子进程继承父进程全部 env，再叠加 `POSITIONAL=1`、`VERIFY_MARK=1`、`POS_EST_LOG`、`POS_RATIO_TABLE`、`POS_FILL`。所以两管线的几何/版面 env 全部透传。`conftest.py:108` 同样 `dict(os.environ)` 后叠加 `PER_PAGE_PITCH=1`、`POSITIONAL=1`。

### 2.2 文件系统读写

**两管线共享约定（geom + classic 同名同结构）**

| 路径 | R/W | 说明 | 冲突? |
|---|---|---|---|
| `argv[1/2]` spotting lines/coords | R | 约定 wz1=data/wz1/、wz2=data/wz2/ | - |
| `argv[3]` OUT (默认 `/tmp/seg2_line.pdf`) | W | 最终 PDF | - |
| `argv[4]` SRC (源 PDF) | R | 图页贴原图 | - |
| `/tmp/seg2_line.tex` | W | **geom+classic 共用同名** | **并发冲突** |
| `/tmp/seg2_line.pdf` | W | xelatex 输出 | **并发冲突** |
| `/tmp/srcpage_{k}.png` | W+R | 源页栅格化 | **并发冲突** |
| `/tmp/fig_{key}_{i}.png` | W | 图块裁剪 | - |
| `/tmp/toc_map.json` | R | v13 写，geom/classic 读（跨管线传递点） | - |
| `$LAYJSON` | R | 版面 JSON | - |
| `$POS_EST_LOG` | W | 估高导出（fit_common 建 fitpos_*/est.json） | 安全（隔离） |
| `$POS_RATIO_TABLE` | R | 比值表 | - |
| `$PAGENUM_GLOBAL_TABLE` | R | 全量页码表 | - |

**fit_common 临时文件（隔离安全）**

| 路径 | R/W | 说明 |
|---|---|---|
| `tempfile.mkdtemp('fitpos_')/est.json` | W | pass1 估高 |
| `tempfile.mkdtemp('fitpos_')/ratio.json` | W | 比值表 |
| `tempfile.mkdtemp('fitpos_')/pass1.pdf` | W | pass1 PDF |

**v13 独立路径**

| 路径 | R/W | 说明 |
|---|---|---|
| `/tmp/xelatex_v13.tex` | W | v13 tex（不与 geom/classic 冲突） |
| `/tmp/xelatex_v13.pdf` | W | xelatex 输出 |
| `/opt/test/最终版_v13.pdf` | W | v13 OUT 默认 |
| `/opt/test/spotting_lines.json` 等 | R | v13 旧路径（非 data/wz*/） |

### 2.3 外部命令

| 命令 | 位置 | 说明 |
|---|---|---|
| `python3 ../pipelines/build_geom.py` | fit_common.py:24 | fit_positional -> fit_common.render(build_name='build_geom') |
| `python3 ../pipelines/build_classic.py` | fit_common.py:24 | fit_positional_classic -> fit_common.render(build_name='build_classic') |
| `xelatex /tmp/seg2_line.tex` | geom L932 / classic L1021 | **共享同名 tex，并发冲突** |
| `xelatex /tmp/xelatex_v13.tex` | v13 L2043 | 独立 |
| PaddleOCR HTTP API | run_spotting_ocr.py / extract_page_numbers.py | POST https://paddleocr.aistudio-app.com/api/v2/ocr/jobs（非 subprocess） |

**无** `os.system` / `os.popen` 调用。

### 2.4 共享 vs 独立状态总结

| 维度 | 共享（geom+classic 一致） | 独立 |
|---|---|---|
| 几何标定 | `utils/geometry.calibrate()` 5 env | - |
| 页码继承 | `utils/page_numbers` | - |
| 版面 env | 11 个两边逐字符一致 | - |
| TOC 传递 | `/tmp/toc_map.json` | - |
| 临时文件 | `/tmp/seg2_line.*` 同名（冲突） | - |
| 校准驱动 | fit_common 参数化 | - |
| LaTeX 转义 | - | escape_latex(mode='geom'/'classic') 差异 |
| preamble | - | build_latex(mode) _cjk_glue 差异 |
| 业务逻辑 | - | classic 多附录/案注/墨高重叠；geom 无 |
| 输入数据 | - | wz1 vs wz2 各自传参 |
| 第三管线 v13 | - | 完全独立 env + /tmp 路径 |
| OCR 链路 | - | run_spotting_ocr 独立 |
| 验证 | verify_geom 通用 | 阈值按样本设 |

---

## 3. 隐藏契约清单

### 3.1 命令行参数约定（三套，顺序不同）

| 管线 | argv[1] | argv[2] | argv[3] | argv[4] | argv[5-7] | 证据 |
|---|---|---|---|---|---|---|
| geom/classic | SL(lines) | CO(coords) | OUT | SRC? | - | geom:19-22 / classic:19-22 |
| fit_common | SL | CO | OUT | SRC? | - | fit_common:12-13 |
| **v13** | **SRC_PDF** | **OUT_PDF** | SPOTTING_LINES | SPOTTING_COORDS | TITLES?/MARKDOWN?/PAGE_NUMBERS? | v13:8-14 |
| verify_geom | out_pdf | **src_coords** | src_lines? | --src-pdf 等 | argparse | verify:124-133 |

**关键差异**：
- geom/classic/fit_common 的 SL,CO,OUT,SRC 同序（fit_common 能直接转发）。
- v13 的 argv[1] 是 SRC_PDF（不是 SL），OUT 在 argv[2]（不是 argv[3]），7 个参数。
- verify_geom 的 argv[2] 是 src_coords（不是 src_lines），与管线 SL,CO 顺序相反，调用时易错位。

### 3.2 spotting JSON 键结构

**spotting_lines.json**（生产者 run_spotting_ocr.py:197）
- 结构：`{page_key_str: [line_str, ...]}`
- key = `str(pi)`，pi 是 0-based 页索引（字符串数字，如 "0","107"）
- 消费者一律 `sorted(sl.keys(), key=int)`（geom:517）或 `sorted(coords, key=lambda k: int(k))`（verify:82）

**spotting_coords.json**（生产者 run_spotting_ocr.py:198,382-388）
- 结构：`{page_key_str: [poly_or_None, ...]}`
- poly = 4 点多边形 `[[x,y],[x,y],[x,y],[x,y]]`（每点 `round(c,1)`）；缺失行对应 `None`
- **list 下标与 spotting_lines[key] 1:1 对齐**（geom:535-538）

**LAYJSON**（geom:265-271 / classic:267-272）
- 顶层是 **list**（按页位置索引），不是 dict：`for _pi, _pg in enumerate(_ld)`
- 每页 dict：`_pg.get('prunedResult',{}).get('parsing_res_list',[])` -> block 列表
- block 字段：`block_label`（image/figure_title/doc_title/paragraph_title/title/aside_text/number）、`block_bbox`（[x0,y0,x1,y1]）、`block_content`（文本）

### 3.3 三套 DPI 坐标空间

| 坐标空间 | DPI | 用途 | 换算 |
|---|---|---|---|
| spotting coords | 200 px | 行 bbox | pt = px x 72/200 |
| LAYJSON block_bbox | 142 px | 版面块 | x200/142 转 spotting 空间 |
| PDF 页面 | pt | 输出 | PAGE_W = round(xmax x 72/200) |

**页面尺寸推导**（geometry.py:17-19）：`_xmax/_ymax` = 全部 coords poly 的最大 x/y（px），`PAGE_W,H = round(_xmax*72/DPI)` pt；无 coords 时回退 `(405,633)`。**不从 SRC PDF 读**（geom:19 注释：源 PDF 实际尺寸可能与 OCR coords 空间不一致）。

### 3.4 GMPG 标记格式

- **格式**：`GMPG<数字>ZZ`，数字 = 0-based 源页 key
- **写入端**：build_geom.py（L525,L612）、build_classic.py（L546,L633）
  - 门控：`os.environ.get('VERIFY_MARK','') in ('1','true','True')`
  - 渲染：`\AddToShipoutPictureFG{\put(1,1){\fontsize{2pt}{2pt}\selectfont GMPG<key>ZZ}}`
  - `<key>` = `str(int(key))`（0-based 源页索引）
- **解析端**：
  - verify_geom.py:25 `MARK_RE = re.compile(r'GMPG(\d+)ZZ')`；L116 `MARK_RE.search(pg.get_text("text"))`；`int(m.group(1))` = 源页 key
  - fit_common.py:38 `re.search(r'GMPG(\d+)ZZ', pg.get_text('text'))`
- **契约**：渲染端在每张物理页左下角 (1,1) 写源页 key；校验/校准端按此把物理页归组回源页。一源页对多物理页 = 溢出 = 校准失效。fit_common 强制 `env['VERIFY_MARK']='1'`（L18）保证量高阶段总有标记。**v13 不写 GMPG**，故 v13 输出走 verify 时退回按序号 1:1（verify:159）。

### 3.5 输出 PDF 命名约定

| 项 | 路径 | 证据 |
|---|---|---|
| geom/classic OUT 默认 | `/tmp/seg2_line.pdf` | geom:21 / classic:21 |
| geom/classic tex | `/tmp/seg2_line.tex` | geom:930 / classic:1019 |
| geom/classic xelatex 产物 | `/tmp/seg2_line.pdf` -> `shutil.copy(OUT)` | geom:932-935 / classic:1021-1024 |
| geom/classic 日志 | `/tmp/seg2_line.log` | xelatex 自动生成 |
| v13 OUT 默认 | `/opt/test/最终版_v13.pdf` | v13:9 |
| v13 tex | `/tmp/xelatex_v13.tex` | v13:2039 |
| v13 xelatex 产物 | `/tmp/xelatex_v13.pdf` -> `os.rename(OUT_PDF)` | v13:2043-2049 |
| fit_common OUT | `argv[3]`（无默认，必填） | fit_common:12 |
| fit_common 中间产物 | `tempfile.mkdtemp('fitpos_')/pass1.pdf`/`est.json`/`ratio.json` | fit_common:66-69 |

**共享 /tmp 产物（并发冲突点）**：
- `/tmp/seg2_line.{tex,pdf,log}` -- geom 与 classic 共用同一硬编码路径，不分 build_name
- `/tmp/toc_map.json` -- 默认 TOC_HEADING_MAP 落点
- `/tmp/fig_<key>_<i>.png` -- 图块裁剪
- `/tmp/srcpage_<key>.png` -- 源页栅格化

---

## 4. 单文件改动风险因果链

### 4.1 改 build_classic.py 的 _esc_chars

```
build_classic.py:_esc_chars (wrapper -> escape_latex(mode='classic'))
  -> esc() 调 _esc_chars -> 转义输出变
    -> /tmp/seg2_line.tex 内容变
      -> xelatex 编译 -> 输出 PDF 文本/行宽变
        -> fit_common.measure_heights 量高变 (GMPG 归组不变，内容高变)
          -> ratio 表变 -> pass2 压缩变 -> 最终 PDF 页数/pitch 变
            -> verify_geom pitch 达标率变 -> 基线 diff 变
```
**拦截点**：unit TestEscChars/TestEsc（转义契约）+ invariants 13（结构不变量）+ verify_geom 退出码（pitch）

### 4.2 改 utils/tex_escape.py 的 escape_latex

```
tex_escape.py:escape_latex (共享)
  -> build_geom._esc_chars + build_classic._esc_chars 都受影响 (两管线同时变)
    -> 两条管线输出都变 -> fit_positional + fit_positional_classic 都受影响
      -> 影响面最大（一改波及全链）
```
**拦截点**：unit TestEscChars（classic）+ TestEscapeTex（v13 ast 提取）+ TestCrossFuncDivergence（对比）

### 4.3 改 utils/geometry.py 的 calibrate

```
geometry.py:calibrate (共享)
  -> build_geom + build_classic 的 PAGE_W/FONT/BASELINE/LINESPREAD 都变
    -> 两条管线字号/行距/版心变 -> 输出 PDF 全变
      -> fit_common 量高变 -> ratio 变 -> 最终 PDF 变
```
**拦截点**：unit TestEffChars（PUNCT_WEIGHT 默认参数）+ invariants 13 + verify_geom pitch

### 4.4 改 fit_common.py 的 render

```
fit_common.py:render (共享校准驱动)
  -> fit_positional + fit_positional_classic 都受影响
    -> subprocess 调 build_geom/classic 的 env/参数变
      -> 两管线输出变 -> 两套基线都变
```
**拦截点**：无直接 unit 测试 fit_common；靠 verify_geom 退出码 + baseline diff

### 4.5 改 build_pdf_v13.py

```
build_pdf_v13.py (src/ 内孤立)
  -> src/ 内无任何文件受影响
    -> 仅 archive/app/services/processor.py 调它（已归档）
      -> unit test_pure_funcs.py AST 提取它的纯函数（不执行顶层）
```
**风险最低**：改 v13 不影响 geom/classic/fit 链。但 v13 自身无 invariants/verify_geom 保护（仅 unit 纯函数）。

### 4.6 改 /tmp/seg2_line.tex 路径

```
改 geom L930 tex_path = '/tmp/seg2_line.tex' -> '/tmp/seg2_geom.tex'
  -> xelatex 编译 /tmp/seg2_geom.tex (OK)
  -> 但 classic 仍写 /tmp/seg2_line.tex (未改)
  -> 如果只改一个文件：geom/classic 临时文件分离 (OK)
  -> 但 fit_common 跑两趟：pass1 和 pass2 都调同一 build_name
    -> 同一管线两趟串行，不冲突 (OK)
  -> 风险：遗漏 classic 的同名路径 -> 并发跑 geom+classic 仍冲突
```

### 4.7 改 GMPG 标记格式

```
改 build_geom.py 写 GMPG -> SRC<key>END
  -> verify_geom MARK_RE 仍搜 GMPG -> 匹配失败
    -> verify 退回按序号 1:1 (精度降)
  -> fit_common re.search 仍搜 GMPG -> 匹配失败
    -> measure_heights 无法归组 -> ratio 表空 -> 校准失效 -> 页数溢出
```
**拦截点**：verify_geom 退出码（split > 0 = 校准失效 FAIL）

---

## 5. 耦合机制总结

系统靠以下机制暗中耦合：

| 耦合机制 | 共享者 | 风险 |
|---|---|---|
| 16 个共享 env | geom+classic（经 fit_common 透传） | 改 env 默认值波及两管线 |
| subprocess 调用链 | fit_common -> build_geom/classic | 改 fit_common render 波及两条校准链 |
| GMPG 标记 | 渲染端(geom/classic) <-> 校验端(verify/fit_common) | 改格式导致校准失效 |
| /tmp 同名文件 | geom+classic 共用 seg2_line.* | 并发冲突 |
| spotting JSON 结构 | OCR -> 管线 -> verify | 改 key 结构波及全链 |
| argv 约定 | 三套不同顺序 | 混用脚本时 argv[1] 语义不同 |
| DPI 坐标空间 | 三套 DPI（200/142/pt）并存 | 换算错误致版心错位 |

**最危险的单文件改动**：改 utils/ 共享模块（一改波及两管线全链）和改 GMPG 格式（跨进程契约断裂）。

**最安全**：改 build_pdf_v13.py（src/ 内孤立）。

**改 fit_common**：影响 fit_positional + fit_positional_classic 两条校准链。

**改 geom/classic**：各自只影响自己那条链（但共享 /tmp 文件名是并发隐患）。
