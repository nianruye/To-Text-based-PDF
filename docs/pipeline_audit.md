# src/ 代码现状审计报告

> **范围**：`/opt/test/src/` 下全部 .py 文件（重点为三管线 + 两校准），只读分析，未修改任何源码。
> **声明**：只描述现状，不含重构方案，未顺手修 bug。每条发现标注源码行号（grep + Read 复核）。
> **方法**：grep 全扫结构骨架 + 针对性 Read 关键段 + 单元测试/特征测试阶段的行为验证。

---

## 0. 文件清单

| 文件 | 行数 | 角色 |
|---|---|---|
| src/pipelines/build_pdf_v13.py | 2056 | 渲染管线①：旧管线 / 重排 reflow |
| src/pipelines/build_geom.py | 1065 | 渲染管线②：现代书籍，逐行几何还原 |
| src/pipelines/build_classic.py | 1154 | 渲染管线③：古籍，墨高重叠+夹注+旁注 |
| src/calibration/fit_positional.py | 97 | 校准驱动①：现代书籍 |
| src/calibration/fit_positional_classic.py | 97 | 校准驱动②：古籍 |
| src/test/verify_geom.py | 269 | 几何校验（pitch/页高/占位/溢出） |
| src/test/test_cases.py | 325 | 特征测试（21 条，仅 classic） |
| src/test/unit/ | - | 纯函数单元测试（ast 提取，121 passed） |
| src/test/invariants/ | - | 特征不变量测试（截取子集跑管线，13 passed） |
| src/ocr/run_spotting_ocr.py | 397 | PaddleOCR-VL spotting OCR |
| src/tools/*.py | - | 辅助工具（extract_titles/page_numbers、analyze_pitch/fontsize、reocr、mineru_*） |

---

## 1. 每条管线的 public API / 入口清单

### 1.1 build_pdf_v13.py（旧管线 / 重排，2056 行）

- **入口**：无 `if __name__=='__main__'` 守卫，**脚本式顶层执行**（L155 `fitz.open(SRC_PDF)`、L2039 写 tex、L2043 跑 xelatex 均在顶层，import 即触发全流程）。
- **argv**（L8-14）：

| argv | 变量 | 默认值 | 行号 |
|---|---|---|---|
| 1 | SRC_PDF | `/opt/test/优化前.pdf` | L8 |
| 2 | OUT_PDF | `/opt/test/最终版_v13.pdf` | L9 |
| 3 | SPOTTING_LINES | `/opt/test/spotting_lines.json` | L10 |
| 4 | SPOTTING_COORDS | `/opt/test/spotting_coords.json` | L11 |
| 5 | SPOTTING_TITLES | `''`（OCR 标题集合，可选） | L12 |
| 6 | MARKDOWN_FILE | `''`（markdown 结构辅助，可选） | L13 |
| 7 | PAGE_NUMBERS_JSON | `''`（外部页码表，可选） | L14 |

### 1.2 build_geom.py（现代书籍，1065 行）/ build_classic.py（古籍，1154 行）

- **入口**：均无 `__main__` 守卫，脚本式顶层执行。classic docstring 仍自称 `build_geom.py`（L4，copy-paste 未改名）。
- **argv**（两文件相同，L13-16）：

| argv | 变量 | 默认值 | 行号 |
|---|---|---|---|
| 1 | SL | `/opt/test/wz1p108_spotting_lines.json` | L13 |
| 2 | CO | `/opt/test/wz1p108_spotting_coords.json` | L14 |
| 3 | OUT | `/tmp/seg2_line.pdf` | L15 |
| 4 | SRC | `''`（源 PDF，图页/乱码页贴原图） | L16 |

### 1.3 校准驱动 fit_positional.py / fit_positional_classic.py（各 97 行）

- 入口：`if __name__=='__main__': main()` L96-97。
- argv（main L69-94）：`SL`(字号) L16、`CO`(字距) L17、`OUT` L16、`SRC`(可选) L17。
- public 函数：`render` L20-33、`measure_heights` L35-67、`main` L69-94。
- 两文件**字节级近乎相同**，唯一实质差异 `render` L27 调用下游脚本名（`build_geom.py` vs `build_classic.py`）。

---

## 2. 职责板块拆分（6 板块 × 3 管线，行号 v13 / geom / classic）

### 2.1 几何标定（cw/MEASURE/FONT/BASELINE/LINESPREAD）

| 项 | build_pdf_v13.py | build_geom.py | build_classic.py |
|---|---|---|---|
| cw（中位字数） | 无（用 max_cjk L601） | L41 | L41 |
| MEASURE（版心宽） | TARGET L627/L755 | L42-44（÷OVERBOUND） | L42-44 |
| FONT（基准字号） | FONT_SIZE L586（10 分位行高×0.75） | L45（MEASURE/cw×FONT_SCALE） | L45 |
| BASELINE | BASE_SKIP L650（FONT×1.2） | L53（pitches 中位×72/DPI） | L53 |
| LINESPREAD | 无（用 BODY_STRETCH L665） | L54（BASELINE/(FONT×1.2)） | L54 |
| 按页实测 pitch | - | `page_pitch` L123-160 | `page_pitch` L124-160（L156-158 多一次 inner 方差复检） |
| 位置还原 | - | USE_POS L252 + 预扫描 | USE_POS L254 + 预扫描 |

### 2.2 LaTeX 转义（escape_tex/_esc_chars/esc）

| 项 | build_pdf_v13.py | build_geom.py | build_classic.py |
|---|---|---|---|
| 通用转义 | `escape_tex` L41-46（**保留** `\ { }`，转义符单反斜杠 `\%`） | `_esc_chars` L198-204（**删除** `\ { }`，转义符单反斜杠 `r'\%'`） | `_esc_chars` L200-206（删除 `\ { }`，转义符**双反斜杠** `r'\\%'` 疑似 bug） |
| 正文转义（含 $...$） | `escape_body` L48-70 | `esc` L206-228 | `esc` L208-230 |
| 数学 \frac->a/b | `escape_body` 内 L65 | `_math_to_plain` L190-195 | L192-197 |
| 校注标记上标 | `escape_body` L57-59 | `esc` 裸[X] L221-229 + MARKER_SCALE L224 | L223-231 + L226 |
| 圈码①->textcircled | -（FN_CIRCLE 仅判定 L16） | `_CIRC` L197 + `_esc_chars` L200 | L199 + L202 |
| ○->〇 / 【】->〔〕 | - | L200 | L202 |
| 省略号归一化 ⋯⋯/…… | - | **无**（`…` 保留） | L202（`…`->`.` 等） |

### 2.3 标题识别（_heading_core/_head_level/is_heading_by_md）

| 项 | build_pdf_v13.py | build_geom.py | build_classic.py |
|---|---|---|---|
| 核心剥离 | `_heading_core` L1271-1277（末步调 `normalize_text`） | `_heading_core` L67-72（末步 `re.sub(\s+)`） | L67-72（同 geom） |
| 分级 | COORD_HEADING_RATIO L550 + `_head_level`(无) | `_head_level` L73-77 | `_head_level` L73-78（L76 多附录判定） |
| markdown 辅助 | `is_heading_by_md` L134-152 + `parse_markdown_structure` L102-132 | - | - |
| 标题序号拆分 | - | `_split_heading` L233 + `_esc_heading` L240 | L235 + L242 |
| layout 版面标签 | - | `_layout_head_level` L367-374 | L369-376 |

### 2.4 页码处理（PN_RE/PAGENUM_GLOBAL_TABLE）

| 项 | build_pdf_v13.py | build_geom.py | build_classic.py |
|---|---|---|---|
| 页码正则 | `is_page_number` 函数 L72-75 | `PN_RE` 常量 L64 | L64 |
| 全局页码表 | PAGENUM_GLOBAL_TABLE L710 + PAGENUM_OFFSET L711 | L62 | L62 |
| layout number block | - | `_lay_numbers` L412-435 | L410-433 |
| OCR 底部页码 | - | pn_ocr L672 | L673 |

### 2.5 书影图块（detect_fig_bands/in_figure/extract_figs）

| 项 | build_pdf_v13.py | build_geom.py | build_classic.py |
|---|---|---|---|
| 书影带检测 | - | `detect_fig_bands` L286-317 | L288-319 |
| 行落图块判定 | - | `in_figure` L446-455 | L448-457 |
| 裁源图 | - | `extract_figs` L434-445 | L436-447 |
| 图说明居中 | - | `in_figcaption` L456-462 | L458-464 |
| 乱码页整页贴图 | - | `is_garbage_page` L463-474 + `render_src_page` L475 | L465-476 + L477 |
| LAYJSON 图块 | - | L319-332 | L317-330 |

### 2.6 目录页（group_toc_rows/TOC_ENTRY_RE/toc_map）

| 项 | build_pdf_v13.py | build_geom.py | build_classic.py |
|---|---|---|---|
| 目录条目正则 | `is_toc_entry` 函数 L77-79 | `TOC_ENTRY_RE` 常量 L65 | L65 |
| 目录行分组 | `group_toc_rows` L1163（独立函数） | 内联 `_npairs` L778 | L825 |
| toc_map 提取 | `toc_heading_map` L1279-1298（含 level） | `toc_map` L90-115（仅 True） | L88-113 |
| TOC 映射导入/导出 | TOC_HEADING_MAP / _OUT L1300-1305 | TOC_HEADING_MAP L89 | L87 |
| 目录页判定 | `is_toc_page_by_ocr` L270 | _npairs>=5 L779 | L826 |

---

## 3. 函数等价关系矩阵

### 3.1 跨文件同名函数

| 函数 | v13 | geom | classic | 行为是否一致 |
|---|---|---|---|---|
| `_heading_core` | L1271 | L67 | L67 | **不一致**：v13 末步调 `normalize_text`（L1277，引号归一化+去空白），geom/classic 只 `re.sub(r'\s+','',t)`（L72）。单元测试验证：含弯引号“”输入 v13 归一为 ASCII "，geom 保留 |
| `_head_level` | - | L73 | L73 | **不一致**：classic L76 多 `if 附录: return 'part'`；geom 无 |
| `_math_to_plain` | L65（内联于 escape_body） | L190 | L192 | 一致（\frac->{a/b}、\command 去反斜杠、去残余花括号） |
| `_split_heading`/`_esc_heading` | - | L233/L240 | L235/L242 | 一致 |
| `page_pitch` | - | L123 | L124 | **不一致**：classic L156-158 多一次 inner 方差复检；geom L155-156 无 |
| `detect_fig_bands`/`in_figure`/`extract_figs`/`in_figcaption`/`is_garbage_page`/`render_src_page`/`page_header_raw`/`detect_regions`/`calc_global_fonts`/`_eff_chars`/`_fix_aside`/`_layout_head_level` | - | L286/L446/L434/L456/L463/L475/L504/L525/L562/L522/L392/L367 | L288/L448/L436/L458/L465/L477/L506/L527/L564/L524/L394/L369 | 一致（行号平移 -2） |

### 3.2 同职责异名函数

| 职责 | v13 | geom/classic | 差异（单元测试验证） |
|---|---|---|---|
| 通用转义 | `escape_tex` L41 | `_esc_chars` L198/L200 | **语义不同**：v13 保留 `\ { }`（`\{`->`\{`），geom/classic 删除它们（`\`->`''`）；且 v13/geom 转义符单反斜杠 `\%`，classic 双反斜杠 `\\%` |
| 正文转义 | `escape_body` L48 | `esc` L206/L208 | geom/classic 多裸[X] 校注上标 + MARKER_SCALE + 圈码/○/【】 |
| 页码判定 | `is_page_number` L72 | `PN_RE.fullmatch` L64 | v13 多 `^\d{1,4}$ len<=4` 分支；正则主体等价 |
| 目录条目判定 | `is_toc_entry` L77 | `TOC_ENTRY_RE.search` L65 | 等价（leader 点+数字） |
| 标题分级 | COORD_HEADING_RATIO L550 | `_head_level` L73 | 完全不同机制（坐标比例 vs 内容模式） |

### 3.3 两校准驱动等价性

`fit_positional.py` 与 `fit_positional_classic.py` 的 `render`/`measure_heights`/`main` 三函数**完全等价**（同名同签名同实现），唯一差异 `render` L27 调用下游脚本名（`build_geom.py` vs `build_classic.py`）。classic 副本 docstring 仍自称 `fit_positional.py`。

### 3.4 结论

- **geom 与 classic 是 fork 关系**：前 ~800 行高度重合（函数同名、行号平移 -2），差异集中在 classic 古籍特色（附录区 L632-647、案注/注释状态机 L801-818、墨高重叠 `\\[-2pt]` L950、`_head_level` 附录判定 L76、`page_pitch` 方差复检 L156-158、`_esc_chars` 转义双反斜杠+省略号归一化 L202）。
- **v13 与 geom/classic 是分叉关系**：v13 保留较早的重排架构，无位置还原/区域化/书影/旁注；`_heading_core`/转义虽同名同职责但实现已分叉。

---

## 4. 状态地图

### 4.1 环境变量总表

**build_pdf_v13.py**（8 个）：

| VAR | 默认值 | 行号 |
|---|---|---|
| LINE_LEVEL | `''`（=='1' 行级输入） | L17 |
| PAGENUM_GLOBAL_TABLE | `''` | L710 |
| PAGENUM_OFFSET | `'0'` | L711 |
| GEOM_FONT | 覆盖 FONT_SIZE | L760-761 |
| GEOM_TARGET | 覆盖 TARGET | L762-763 |
| GEOM_STRETCH | 覆盖 BODY_STRETCH | L767-768 |
| TOC_HEADING_MAP_OUT | `''`（导出） | L1300 |
| TOC_HEADING_MAP | `''`（导入） | L1303 |

**build_geom.py / build_classic.py**（共用 19 个，行号 geom/classic）：

| VAR | 默认值 | 行号 |
|---|---|---|
| OVERBOUND | `'1.115'` | L43 |
| FONT_SCALE | `'1.0'` | L45 |
| PUNCT_WEIGHT | `'0.2'` | L57 |
| REGION_LAYOUT | `''` | L58 |
| REGION_FONT_SCALE | `'1.03'` | L59 |
| PAGENUM_GLOBAL_TABLE | `''` | L62 |
| PAGENUM_OFFSET | `'0'` | L62 |
| TOC_HEADING_MAP | `'' or /tmp/toc_map.json` | L89/L87 |
| PER_PAGE_PITCH | `''` | L122/L121 |
| POS_RATIO_TABLE | `''` | L165 |
| MARKER_SCALE | `'0.55'` | L224/L226 |
| POSITIONAL | `''` | L254/L252 |
| LAYJSON | `''` | L321/L319 |
| LAYOUT_HEADINGS | `''` | L354/L352 |
| PAGE_FONT | `''` | L592/L590 |
| VERIFY_MARK | `''` | L718/L654 等 |
| POS_FILL | `'1.08'` | L913（位置还原段） |
| POS_EST_LOG | `''`（导出估高，**裸 `os.environ[]` 取值** L1036/L1125） | L1035/L1124 |
| GRID_PITCH | `''` | L947/L1018 |

**校准驱动**：POSITIONAL/VERIFY_MARK 强制 `'1'`、POS_EST_LOG/POS_RATIO_TABLE 透传、POS_FILL 默认 `'0.95'`（fit L93）。

**OCR/tools**：`run_spotting_ocr.py` OCR_LAYOUT 默认 `'1'` L18；读 TOKEN_FILE L14。test_cases.py / verify_geom.py 无环境变量。

### 4.2 文件系统读写路径

**输入**：
- 源 PDF：v13 SRC_PDF(argv1) L155；geom/classic SRC(argv4) L16
- spotting_lines/coords.json：v13 argv3-4 L10-11；geom/classic argv1-2 L13-14
- v13 额外：SPOTTING_TITLES(argv5) L168、MARKDOWN_FILE(argv6) L111、PAGE_NUMBERS_JSON(argv7) L686
- geom/classic 额外：LAYJSON(env) L326、PAGENUM_GLOBAL_TABLE(env) L63、TOC_HEADING_MAP(env) L91、POS_RATIO_TABLE(env) L167
- 校准：读 `est.json` L77、pass1 PDF L38

**输出**：
- tex：geom/classic `/tmp/seg2_line.tex` L1146；v13 `/tmp/xelatex_v13.tex` L2039
- PDF：`/tmp/seg2_line.pdf` L1149 -> `shutil.copy` 到 OUT L1151；v13 直接 OUT_PDF L2043
- geom/classic 临时图：`/tmp/fig_{key}_{i}.png` L444、`/tmp/srcpage_{k}.png` L477
- geom/classic toc_map：`/tmp/toc_map.json` L89（默认）
- 校准：写 `ratio.json` L87、OUT PDF L93、临时目录 `tempfile.mkdtemp(prefix='fitpos_')` L70（**未清理**）
- v13 导出：TOC_HEADING_MAP_OUT(env) L1301

**OCR 产物**：`OUT_LINES`/`OUT_COORDS`/`out_labels` JSON（run_spotting_ocr.py L378-395）

**测试**：test_cases.py 读输出 PDF L300；verify_geom.py 读 coords/lines JSON + PDF，写报告 JSON（仅 `--json`）

### 4.3 外部命令依赖

| 命令 | 调用位置 | 行号 |
|---|---|---|
| `xelatex -interaction=nonstopmode` | geom | L1059 |
| `xelatex -interaction=nonstopmode` | classic | L1148 |
| `xelatex -interaction=nonstopmode` | v13 | L2043 |
| `python3 <build_geom.py\|build_classic.py>` | 两校准驱动 render | fit L28-30 |
| PaddleOCR-VL-1.6 HTTP API | run_spotting_ocr.py L11-12、extract_page_numbers.py L16-17 | （HTTP POST，非本地命令） |

**无** `pdftoppm`/`tesseract`/`mineru` 本地命令调用（mineru_* 仅读已有输出）。三管线用 `fitz`(PyMuPDF) 读 PDF、`PIL` 裁图（geom/classic L437-441）、`opencc` 繁简区分（L265/L267）。

> **坑**：fit_positional render L30 `subprocess` 调 `python3`，若 PATH 中 `python3` 指向 mineru venv（无 fitz/opencc）则失败。特征测试阶段实测需用 `/usr/bin/python3` 或设 PATH。

---

## 5. 可疑行为清单（带行号证据，仅记录不修）

### 5.1 build_pdf_v13.py

| 行号 | 代码片段 | 现象 |
|---|---|---|
| L8-14 | 默认 `优化前.pdf`/`最终版_v13.pdf` | argv 默认值硬编码中文文件名，跨环境不可移植 |
| L42-44 | `escape_tex` 保留 `\ { }`（`\{`->`\{`） | 与 geom/classic `_esc_chars` 删除 `\ { }` 语义相反，同一输入三管线转义结果不同 |
| L139-141 | `norm.replace('"','"').replace('"','"')...` | **identity 替换**（左"->左"、右"->右"），无实际归一化效果，疑为未完成代码 |
| L155 | `doc = fitz.open(SRC_PDF)` 顶层 | 无 `__main__` 守卫，import 即开 PDF 跑全流程，无法被安全 import |
| L586 | `FONT_SIZE = all_line_h[len//10] * 0.75` | 用 10 分位行高估字号，与 geom 的 MEASURE/cw 推导不同口径 |
| L666 | `BODY_STRETCH = max(1.4, min(1.6, ...))` | 魔法区间硬钳，超出区间的真实拉伸被截断 |
| L760-768 | GEOM_FONT/TARGET/STRETCH 覆盖 | 环境变量名带 GEOM_ 前缀，与 geom 管线的 FONT_SCALE/OVERBOUND 命名不一致，易混 |
| L1300-1305 | TOC map 导入/导出 | 导出后立即可能被导入覆盖（同次运行两分支都触发） |
| L2039 | tex 路径写死 `/tmp/xelatex_v13.tex` | 与 geom/classic 的 `/tmp/seg2_line.tex` 不同，命名无统一 |

### 5.2 build_geom.py / build_classic.py

| 行号 | 代码片段 | 现象 |
|---|---|---|
| classic L4 | docstring `build_geom.py - ...` | classic 未随文件改名，copy-paste 遗留 |
| **classic L202** | `_esc_chars` 转义符 `r'\\%'`（双反斜杠） | **疑似 bug**：LaTeX 里 `\\` 是换行、`%` 是注释，`a%b`->`a\\%b` 会换行+注释掉 b。geom L200 用单反斜杠 `r'\%'` 正确。古籍罕含 `%` 故未暴露（单元测试验证） |
| classic L202 | `_esc_chars` 有省略号归一化（`…`->`.`） | geom L200 **无**省略号归一化--两者省略号行为不一致（单元测试验证） |
| geom L155-156 / classic L156-158 | `page_pitch` 方差检查 | classic 对过滤后 inner 再查一次方差，geom 只查过滤前 diffs--两管线 pitch 回退判定口径不同 |
| L18 (两文件) | `PAGE_W, PAGE_H = 405, 633` 占位 | 占位常量，coords 覆盖前若 `_xmax/_ymax` 为 0 则沿用错误尺寸 |
| geom L254 / classic L256 | `line_font` 引用 `FONT_HD` | `FONT_HD` 未定义（grep 全文无赋值），调用必 NameError（疑为死代码/未启用路径） |
| classic L950 | `brk = ' \\\\[-2pt]'` | 墨高重叠硬编码 -2pt，未抽常量，不随字号缩放 |
| classic L904 | `_strut_h += fnt*1.34*LINESPREAD` | 1.34 魔法系数，估高与实际 baselineskip 交互偏大约 13%（注释自述 L911） |
| L1146/L1148 (两文件) | tex/xelatex 路径写死 `/tmp` | 并发或权限受限环境不可用 |
| classic L1125 | `json.dump(_pos_est, open(os.environ['POS_EST_LOG'],'w'))` | `os.environ['POS_EST_LOG']` 用裸 `[]` 取值，未设则 KeyError（L1124 的 if 只判 truthy 但取值用 `[]`） |

### 5.3 校准驱动（fit_positional*.py）

| 行号 | 代码片段 | 现象 |
|---|---|---|
| 两文件 L4/L10 | docstring `fit_positional.py` | classic 版未改名 |
| 两文件 L18 | `DPI = 200` | 定义后未引用，死代码 |
| 两文件 L26 | `import os as _os`（render 内） | 顶部已 import os，重复 |
| 两文件 L70 | `tempfile.mkdtemp(prefix='fitpos_')` | 无 `shutil.rmtree`，临时目录泄漏 |
| 两文件 L80/L83-86 | 注释称"缺失页 ratio=1"，代码只对 `e>0 and a>0` 写入 | 缺失页默认行为耦合下游 |
| 两文件 L48/L64 | `usable = height-42` / `botN-12.0` | 魔法数 42/12 未抽常量，古籍版心边距若不同不自适应 |
| 两文件 L30 | `subprocess.run([...,'python3',...])` | 调 `python3`，若 PATH 命中 mineru venv（无 fitz）则失败 |

### 5.4 测试脚本

| 行号 | 代码片段 | 现象 |
|---|---|---|
| test_cases.py L73 | `test_pitch_rate(coords_path, lines_path, src_pdf)` 形参 | `run_all` L298 只传 pdf，三参为死参 |
| verify_geom.py L116-265 | `main()` | **无 PASS/FAIL 退出码**，CI 无法据 exit code 判回归 |
| verify_geom.py L121 | `--src-pdf` | 声明但未使用 |

---

## 6. build_pdf_v13.py 的独有功能

下列能力只有 v13 具备，geom 与 classic 从架构上做不到（或未实现）：

1. **Markdown 结构辅助标题识别**：argv6 `MARKDOWN_FILE` + `parse_markdown_structure` L102-132（解析 `##` 标题层级 + `$^{①}$` 脚注引用）+ `is_heading_by_md` L134-152（fuzzy 匹配，含 0.7 长度比 substring 匹配）。geom/classic 仅靠 toc_map 自动提取。
2. **OCR 标题集合输入**：argv5 `SPOTTING_TITLES` L12/L168--直接消费外部标题文件。
3. **重排 reflow 拉伸填充**：`BODY_STRETCH` L665（钳[1.4,1.6]）+ `CJK_STRETCH` L669 + `STRETCH_UPPER` L772--段落重排+拉伸填满版心，区别于 geom/classic 的"逐行固定 makebox"。
4. **页面类型分类函数**：`is_content_page` L242、`is_toc_page_by_ocr` L270、`is_body_fragment` L81、`is_toc_entry_start` L89、`is_footnote_start` L98、`fuzzy_key` L1063。
5. **独立 `group_toc_rows` 函数** L1163--目录行分组抽成函数（含 level 输出），geom/classic 全内联。
6. **正文/转义分离**：`escape_body` L48 与 `escape_tex` L41 分离；geom/classic 合并在 `esc`。
7. **TOC 标题映射导出**：`TOC_HEADING_MAP_OUT` L1300--可导出供分片共享，geom/classic 只读不导出。
8. **坐标比例标题判定**：`COORD_HEADING_RATIO` L550/556 + `MIN_HEADING_WIDTH` L558--用源坐标行高/宽比例阈值判标题。
9. **复杂页眉左右分栏**：`DEFAULT_RIGHT_HDR`/`DEFAULT_LEFT_HDR` L841-842、`RIGHT_HDR_FONT`/`LEFT_HDR_FONT` L847-848、`RIGHT_HDR_GAP`/`LEFT_HDR_GAP` L876-877--左右页眉独立标定。
10. **脚注几何独立推导**：`FN_FONT_SIZE` L972、`FN_BASELINE` L980、`FN_INDENT_PT` L992、`FN_STRETCH_UPPER` L1030。
11. **`_body_width_90pt`** L202--90 分位行宽推导，geom/classic 用满行 w>0.80×maxw。
12. **外部页码 JSON**：`PAGE_NUMBERS_JSON` argv7 L14/L686，geom/classic 仅 PAGENUM_GLOBAL_TABLE。

> 反向：geom/classic 独有而 v13 没有的能力见 §2（位置还原 POSITIONAL、PER_PAGE_PITCH、REGION_LAYOUT、LAYJSON 版面、书影带、边栏旁注、墨高重叠、夹注/案注、MARKER_SCALE、opencc 繁简）。

---

## 7. 重构前应补的特征测试（具体场景 + 预期断言类型）

### 7.1 当前覆盖现状

- `test_cases.py` 21 条断言**全部针对 build_classic.py 输出**；v13/geom 零回归保护。
- `src/test/unit/`（纯函数，ast 提取绕开模块顶层副作用，121 passed）已锁转义/`_heading_core` 现状差异。
- `src/test/invariants/`（截取子集跑管线，13 passed）已锁 6 个 geom + 7 个 classic 结构不变量。
- verify_geom 无 PASS/FAIL 退出码，CI 拦不住回归。

### 7.2 第一批应补特征测试

| # | 缺口 | 涉及管线 | 场景 | 预期断言类型 |
|---|---|---|---|---|
| 1 | verify_geom 退出码 | verify_geom.py | 跑校验后 CI 判定 | assertEqual(returncode, 0/1)--前置基础设施 |
| 2 | build_pdf_v13.py 整体回归 | build_pdf_v13.py | 优化前.pdf 一页输出 | tolerance（FONT_SIZE/页数） |
| 3 | fit_positional.py 通用版 | fit_positional.py | pass1->ratio 表生成 | assertEqual（ratio.json key 集合）+ tolerance（比值） |
| 4 | 书影带检测 | geom L286 / classic L288 | 含书影页 | truthy（detect_fig_bands 非空） |
| 5 | 目录页 dotfill 正向 | geom/classic | 目录页 | 正则匹配（`\dotfill` 存在） |
| 6 | 古籍夹注（行内双行小字） | classic | 含夹注页 | tolerance（夹注字号≈正文×0.5） |
| 7 | 墨高重叠 `\\[-2pt]` | classic L950 | 古籍正文行 | assertEqual（tex 含 `\\[-2pt]`） |
| 8 | 引文 frags 绝对定位 | classic | x0>110 引文行 | tolerance（输出 x0≈源 x0） |
| 9 | 跨页连续性 | classic | 段落/序号跨页 | assertEqual（段首不截断） |
| 10 | 页码序列（多页） | classic | 多页页码 | assertEqual（递增序列） |
| 11 | 字体嵌入/ToUnicode 可复制性 | 全管线 | 输出 PDF 文本抽取 | assertEqual（get_text 含预期字串） |
| 12 | verify_geom 指标固化 | verify_geom + 全管线 | h_err/p_err/bot_gap | tolerance（h<5%/p<3%/bot<8%/overflow=0） |
| 13 | 多物理页溢出 split | classic + verify L193-196 | 源页溢成多页 | assertEqual（split 计数） |
| 14 | GMPG 标记对齐 | classic + verify | VERIFY_MARK=1 输出 | 正则匹配（GMPG<key>ZZ 可解析） |
| 15 | classic `_esc_chars` 双反斜杠 bug | classic L202 | 含 `%` 文本 | assertEqual（输出 `\\%`，记录待修） |
| 16 | `line_font` FONT_HD 死路径 | geom L254 / classic L256 | 触发 line_font | 验证是否 NameError（锁定死代码） |

### 7.3 优先级建议

1. **给 verify_geom.py 加 PASS/FAIL 退出码**（L116-265）--前置基础设施。
2. **锁定转义/`_heading_core` 现状差异**--已在 `src/test/unit/` 完成，重构前勿误"统一"。
3. **为 build_pdf_v13.py 补最小特征测试**（#2）--三管线只 classic 有保护。
4. **固化 verify_geom 指标为断言**（#12）。
5. **classic `_esc_chars` 双反斜杠**（#15）--先用测试锁现状，修 bug 时测试转红再转绿。
