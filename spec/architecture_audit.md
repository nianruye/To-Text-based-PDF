# architecture_audit.md - 架构审计报告

> **范围**：`/opt/test/src/` 下三管线 + 两校准 + 共享模块，只读分析，未修改任何源码。
> **代码状态**：Step 1-6 重构（tex_escape/geometry/page_numbers/image_blocks/_latex_preamble/fit_common 抽取）+ 9 个 bug 修复（#1-#9）后。行号基于当前代码。
> **声明**：只描述现状，不含重构方案。每条发现标注源码行号。

---

## 0. 已知能力缺口：竖排古籍

> 当前三条管线均只支持横排输出（xelatex 默认方向）。如果遇到竖排古籍（文字从右到左、列从右到左排列），现有管线无法处理。竖排需要独立的文字方向控制（`\rotatebox` 逐字或 `vertcjk` 包）、列序反转、天头/地脚注释定位--这些是架构层面未覆盖的能力，不是现有管线的 bug。

| 维度 | 横排（当前支持） | 竖排（未覆盖） |
|---|---|---|
| 文字方向 | xelatex 默认左到右 | 需 `\rotatebox` 逐字 90° 或 `vertcjk` 包 |
| 列序 | 行从左到右、从上到下 | 列从右到左、每列从上到下 |
| 页眉/页脚 | 顶部/底部（y < 5% / y > 80%） | 天头/地脚（竖排页的上下边） |
| 旁注 | 边栏竖排 `\shortstack`（classic L723-729） | 竖排页的左右栏（位置完全不同） |
| 夹注 | 行间小字（classic L801-818 案注状态机） | 列间小字（x 方向而非 y 方向） |
| pitch 测量 | 相邻行 y_center 差（verify_geom L66） | 相邻列 x_center 差 |

**影响**：wz2（盐铁论）当前是横排夹注本（文字横排、注释夹在行间），build_classic 能处理。但如遇纯竖排古籍（如宋刻本影印），三条管线均无法输出正确排版。

> **状态更新（2026-10-15）**：竖排缺口已补齐 —— 新增竖排管线 `src/pipelines/build_vert.py`
> （upLaTeX + tarticle 列流右起，wz6 全书 231 页 1:1），文档见 [vertical/](vertical/README.md)。
> 本节上述「未覆盖」描述保留为审计时点记录。

---

## 1. 每条管线的 public API / 入口清单

### 1.1 build_pdf_v13.py（旧管线 / 重排，2056 行）-- 已归档

- **入口**：无 `__main__` 守卫，脚本式顶层执行（L154 `fitz.open(SRC_PDF)`、L2038 写 tex、L2042 xelatex 均在顶层）。
- **argv**（L8-14）：

| argv | 变量 | 默认值 | 行号 |
|---|---|---|---|
| 1 | SRC_PDF | `/opt/test/优化前.pdf` | L8 |
| 2 | OUT_PDF | `/opt/test/最终版_v13.pdf` | L9 |
| 3 | SPOTTING_LINES | `/opt/test/spotting_lines.json` | L10 |
| 4 | SPOTTING_COORDS | `/opt/test/spotting_coords.json` | L11 |
| 5 | SPOTTING_TITLES | `''`（可选） | L12 |
| 6 | MARKDOWN_FILE | `''`（可选） | L13 |
| 7 | PAGE_NUMBERS_JSON | `''`（可选） | L14 |

- **环境变量**（8 个）：

| VAR | 默认值 | 行号 |
|---|---|---|
| LINE_LEVEL | `''`（=='1' 行级输入） | L17 |
| PAGENUM_GLOBAL_TABLE | `''` | L709 |
| PAGENUM_OFFSET | `'0'` | L710 |
| GEOM_FONT | 覆盖 FONT_SIZE | L759-760 |
| GEOM_TARGET | 覆盖 TARGET | L761-762 |
| GEOM_STRETCH | 覆盖 BODY_STRETCH | L766-767 |
| TOC_HEADING_MAP_OUT | `''`（导出） | L1299 |
| TOC_HEADING_MAP | `''`（导入） | L1302 |

> **已归档**：src/ 内孤立（零 import / 零 subprocess 调用），未接入 5 个共享模块（tex_escape/geometry/page_numbers/image_blocks/_latex_preamble），无 invariants/verify_geom/baseline 保护。12 项独有功能（见 §6）作为参考实现存档，不再维护。如需独有能力，开 issue 提取逻辑到 geom/classic 或新管线。

### 1.2 build_geom.py / build_classic.py（argv + env 完全一致）

- **入口**：均无 `__main__` 守卫，脚本式顶层执行。classic docstring 仍自称 `build_geom.py`（L4，#9 修复未生效）。
- **argv**（L19-22）：

| argv | 变量 | 默认值 |
|---|---|---|
| 1 | SL | `/opt/test/wz1p108_spotting_lines.json` |
| 2 | CO | `/opt/test/wz1p108_spotting_coords.json` |
| 3 | OUT | `/tmp/seg2_line.pdf` |
| 4 | SRC | `''`（可选） |

- **环境变量**（16 个共享 + 经 geometry.py 4 个 + 经 page_numbers.py 2 个）：

| VAR | 默认值 | 位置 |
|---|---|---|
| OVERBOUND | `'1.115'` | geometry.py L33 |
| FONT_SCALE | `'1.0'` | geometry.py L35 |
| PUNCT_WEIGHT | `'0.2'` | geometry.py L47 |
| REGION_LAYOUT | `''` | geometry.py L48 |
| REGION_FONT_SCALE | `'1.03'` | geometry.py L49 |
| PAGENUM_GLOBAL_TABLE | `''` | page_numbers.py L17 |
| PAGENUM_OFFSET | `'0'` | L37 |
| TOC_HEADING_MAP | `''`->`/tmp/toc_map.json` | L63 |
| PER_PAGE_PITCH | `''` | L95 |
| POS_RATIO_TABLE | `''` | L137 |
| MARKER_SCALE | `'0.55'` | L193 |
| POSITIONAL | `''` | L221 |
| LAYJSON | `''` | L251 |
| LAYOUT_HEADINGS | `''` | L289 |
| PAGE_FONT | `''` | L476/584 |
| VERIFY_MARK | `''` | L519/604 |
| POS_FILL | `'1.08'` | L751 |
| POS_EST_LOG | `''` | L921 |
| GRID_PITCH | `''` | L833 |

### 1.3 校准驱动 fit_common.py

- **入口**：`if __name__ == '__main__'` 由 fit_positional.py / fit_positional_classic.py（各 3 行壳）调用 `main('build_geom'/'build_classic')`。
- **argv**（L12-13）：`SL` `CO` `OUT` `SRC?`（与 geom/classic 同序）。
- **环境变量**（L17-20 设给子进程）：`POSITIONAL=1`（强制）、`VERIFY_MARK=1`（强制）、`POS_EST_LOG`、`POS_RATIO_TABLE`、`POS_FILL`（默认 `'0.95'`，L88）。
- **隐式传递**：`env = dict(os.environ)`（L17）子进程继承父全部 env + 叠加。

---

## 2. 职责板块拆分（6 板块 × 3 管线）

| 板块 | v13 | geom | classic |
|---|---|---|---|
| **几何标定** | 管线内联（L154-156 PW/PH 从 SRC_PDF；L560-665 FONT/MARGIN/STRETCH 推导） | **import 共享** `calibrate()`（L28，geometry.py L14-54） | **import 共享** `calibrate()`（L28，与 geom 一致） |
| **LaTeX 转义** | 管线内联 `escape_tex`（L41-48，占位符防二次转义）+ `escape_body`（L50-72） | **wrapper** `_esc_chars`（L171-173）+ `esc`（L175-197） | **wrapper** `_esc_chars`（L173-175）+ `esc`（L177-199） |
| **标题识别** | 内联 `_heading_core`（L1270-1276，末步 `normalize_text`）+ `is_heading_by_md`（L136-151） | 内联 `_heading_core`（L41-46，末步 `re.sub(\s+)`）+ `_head_level`（L47-51，**无附录**） | 内联 `_heading_core`（L41-46）+ `_head_level`（L47-52，**有附录** L50） |
| **页码处理** | 内联 `is_page_number`（L74-77）；PAGENUM env（L709-715） | **import 共享** `load_pntab/infer_lay_numbers/PN_RE`（L15） | **import 共享**，与 geom 一致 |
| **书影图块** | 无（v13 不处理书影） | **import 共享** `image_blocks`（L16）wrapper L256-259 | **import 共享**，与 geom 一致 L257-260 |
| **目录页** | 内联 `group_toc_rows`（L1162）+ `is_toc_entry`（L79）+ `is_toc_page_by_ocr`（L269） | 内联 `_is_toc_entry`（L59）+ `TOC_ENTRY_RE`（L39）+ toc_map（L63-88） | 内联，与 geom 一致（L60-63, L64-89） |

---

## 3. 函数等价关系矩阵

### 3.1 _esc_chars（v13 escape_tex vs geom/classic wrapper）

| 输入 | v13 `escape_tex` | geom `_esc_chars` | classic `_esc_chars` |
|---|---|---|---|
| `\`（单反斜杠） | `\textbackslash{}`（占位符还原） | `''`（删除） | 保留（只删双反斜杠） |
| `%` `&` `#` `_` | `\%` `\&` `\#` `\_`（单反斜杠） | 同 | 同（#1 修复后统一） |
| `{` `}` | `\{` `\}`（保留） | `''`（删除） | `''`（删除） |
| `○` | 不处理 | `〇` | `〇` |
| `①` | 不处理 | `\textcircled{1}` | `\textcircled{1}` |
| `…` | 不处理 | 不处理 | `.`（省略号归一化） |

**结论**：三套转义行为**仍不一致**（反斜杠/花括号/圈码/省略号各有差异）。#1 修复后 `%&#_` 转义符统一为单反斜杠，但反斜杠删除行为未统一（classic 保留单反斜杠，geom 删单反斜杠）。

### 3.2 _heading_core 末步

- v13（L1276）：`return normalize_text(t)` -> 去空白 + `_QUOTE_MAP` 引号归一化
- geom/classic（L46）：`return re.sub(r'\s+', '', t)`（无引号归一化）

### 3.3 _head_level

- geom（L47-51）：无附录判定
- classic（L47-52）：L50 `if re.match(r'^附录', t.strip()): return 'part'`

### 3.4 page_pitch

- geom（L125-132）：方差检查用全量 `diffs`（含异常大间隙）
- classic（L125-134）：先过滤 `<=1.8*m0` 为 `inner`，再用 `inner` 做方差检查（更鲁棒）

### 3.5 _cjk_glue（_latex_preamble.py L18-23）

| mode | _cjk_glue |
|---|---|
| USE_REGION（两管线一致） | `\hskip 0pt plus 0.05em minus 0.5em` |
| classic（非区域） | `\hskip 0.15em plus 0.35em minus 0.8em` |
| geom（非区域） | `\hskip 0pt plus 0.5em minus 0.4em` |

### 3.6 flush 段间 gap 钳制

- geom（L772）：`min(_gap, fnt*2.5)`
- classic（L820）：`min(_gap, fnt*6)`（古籍段间留白大）

---

## 4. 状态地图

### 4.1 全部环境变量

见 §1.2（geom/classic 16+4+2=22 个）+ §1.1（v13 8 个）+ §1.3（fit_common 5 个设给子进程）。

**隐式传递**：`fit_common.py L17 env = dict(os.environ)` 子进程继承父全部 env。所有几何/版面 env 透传。

### 4.2 文件系统读写

| 路径 | R/W | 说明 | 冲突? |
|---|---|---|---|
| `argv[1/2]` spotting lines/coords | R | 约定 wz1/wz2 路径 | - |
| `/tmp/seg2_line.tex` | W | geom+classic 共用同名 | **并发冲突** |
| `/tmp/seg2_line.pdf` | W | 同上 | **并发冲突** |
| `/tmp/srcpage_{k}.png` | W | 整页贴图 | **并发冲突** |
| `/tmp/fig_{key}_{i}.png` | W | 图块裁剪 | - |
| `/tmp/toc_map.json` | R | v13 写，geom/classic 读 | - |
| `/tmp/xelatex_v13.tex` | W | v13 独立 | 不冲突 |
| `fitpos_*/est.json/ratio.json/pass1.pdf` | W+R | fit_common 隔离 | 安全 |
| `$LAYJSON` / `$PAGENUM_GLOBAL_TABLE` / `$TOC_HEADING_MAP` | R | env 指定 | - |
| `$POS_EST_LOG` / `$TOC_HEADING_MAP_OUT` | W | env 指定 | - |

### 4.3 外部命令

| 命令 | 位置 | 说明 |
|---|---|---|
| `xelatex /tmp/seg2_line.tex` | geom L927 / classic L1016 | **共享同名 tex** |
| `xelatex /tmp/xelatex_v13.tex` | v13 L2042 | 独立 |
| `python3 build_geom/build_classic.py` | fit_common L24 | 子进程校准两趟 |

---

## 5. 可疑行为清单（当前仍存在）

> 9 个已知 bug（#1-#9）已修。#9 classic docstring **replace 未生效**（L4 仍误写 `build_geom.py`），待复查。以下为当前仍存在的可疑行为：

| # | 行号 | 代码 | 现象 |
|---|---|---|---|
| 1 | v13 L154 / geom L25 / classic L25 | 顶层执行，无 `__main__` 守卫 | import 即触发全流程（fitz.open/xelatex），无法安全 import |
| 2 | tex_escape.py L14 | classic `_CLASSIC_PAIRS` 第一对 `('\\\\','')` 只删双反斜杠 | 单反斜杠保留未转义，xelatex 潜在命令解释错误 |
| 3 | v13 L42-48 | `escape_tex` 不处理圈码/○/【】 | `①` 原样输出（xelatex 无字形时乱码） |
| 4 | v13 L77 | `is_page_number` L77 死代码 | `return bool(re.match(r'^\d{1,4}$', s)) and len(s) <= 4` 永不执行（L76 已覆盖） |
| 5 | v13 L81 vs geom L39 | `is_toc_entry` 字符集不同 | v13 `[…\.]` 缺 `·` 和 `．`；geom/classic `[.·…．]` |
| 6 | v13 L76 vs page_numbers.py L12 | `is_page_number` 用 `[·•‧]` vs `PN_RE` 用 `[·•.]` | 页码 bullet 字符覆盖不一致 |
| 7 | geom L129 | `page_pitch` 方差检查含异常值（**设计差异，不修**） | 用全量 `diffs`（含页码大间隙），更易返回 None 回退全局。实测改为 inner 过滤后 pitch 达标率 89.9%->15.4%、空白页 14->85，保守策略对现代书正确 |
| 8 | geom L778-779 / classic L826-827 | `fnt = f['fnt']` 重复赋值 | copy-paste 残留，无害 |
| 9 | classic L4 | docstring 仍误写 `build_geom.py` | #9 修复 replace 未生效，待复查 |
| 10 | v13 L1130 | 硬编码 `/opt/test/font_classifier` | 目录不存在则 ImportError 中断管线 |
| 11 | v13 L1811/1954 | `'_var' in dir()` 检查局部变量 | code smell，`dir()` 在循环内性能差 |
| 12 | v13 L1340-1343 | 页面去重 `prev_body_text == this_body and len > 50` | 有意重复的版权页/扉页会丢页 |
| 13 | classic L878 | 数字片段过滤 `_fi[1] < body_right_px` | geom 无此过滤，classic 多一道边栏页码过滤 |
| 14 | v13 L379 | 脚注检测 `and` 优先级 | `'马克思' in text and '卷' in text` 绑定两条件，需同时含两词 |

---

## 6. build_pdf_v13.py 独有功能（参考实现，已归档）

1. **文本层检测与提取**（L332-486）：`has_text_layer` 判断 PDF 是否有嵌入 OCR 文本层，提取 pt 级精确参数。geom/classic 不读文本层。
2. **Markdown 标题解析**（L104-151）：`parse_markdown_structure` + `is_heading_by_md` 模糊匹配。geom/classic 用 toc_map + 几何启发式。
3. **OCR 标题集合匹配**（L1643-1657）：`SPOTTING_TITLES` 加载版面标题集合。geom/classic 用 `_layout_head_level`。
4. **字体分类器**（L1127-1159）：`predict.py` 的 `detect_font_style` 逐行分类 heiti/kaiti/bold。geom/classic 不做字体分类。
5. **SCALE 双路径检测**（L181-236）：`scale_embedded` vs `scale_yextent`。geom/classic 用固定 DPI=200。
6. **水印检测**（L1061-1125）：频次 + 模糊 key + 关键词。geom/classic 用几何判定（y > 0.95*page_px_h and w_ratio < 0.50）。
7. **运行页眉检测与合并**（L774-884）：`page_headers` + `MERGE_GAP_PX` + `DEFAULT_RIGHT_HDR/LEFT_HDR`。geom/classic 用 `page_header_raw` + `CANON_HDRS`。
8. **脚注参数源推导**（L886-1031）：逐页推导 FN_FONT_SIZE/FN_BASELINE/FN_INDENT_PT 等 8 参数。geom/classic 用固定 FONT_SM。
9. **TOC 标题映射导出/继承**（L1299-1304）：v13 含 level（0/1/2），geom/classic 仅 True。
10. **跨页续行检测**（L1313-1314, L2007-2022）：`_prev_page_body_terminal`。geom/classic 无跨页概念。
11. **几何安全守卫**（L747-756）：`MIN_MARGIN_PT = max(16, PW_PT*0.05)`。geom/classic 无此守卫。
12. **`detect_heading_signal` 结构规则库**（L1394-1465）：L1/L2/L3/coord/centered 五层规则。geom/classic 用 `is_head_heur` 更简洁。

---

## 7. 第一批应补特征测试

| # | 测试场景 | 断言类型 | 锁定行为 |
|---|---|---|---|
| 1 | `_esc_chars` geom 模式 | assertEqual | 单反斜杠删除（`'a\\b'`->`'ab'`）；无省略号归一化（`'…'`->`'…'`） |
| 2 | `escape_tex` v13 模式 | assertEqual | `\`->`\textbackslash{}`（占位符还原）；`①`原样输出（不转 `\textcircled{1}`） |
| 3 | `_head_level` classic 模式 | assertEqual | `附录一`->`'part'`（classic L50）；geom 无此分支->`'title'` |
| 4 | `page_pitch` geom vs classic 差异 | assertIsNone / assertNotNull | 含异常大间距时 geom 返回 None（方差含异常），classic 返回有效 pitch（inner 过滤） |
| 5 | `build_latex` `_cjk_glue` per mode | assertIn | classic `0.15em plus 0.35em minus 0.8em`；geom `0pt plus 0.5em minus 0.4em`；USE_REGION `0pt plus 0.05em minus 0.5em` |
| 6 | `calibrate` 几何推导 | assertEqual + tolerance | 构造已知 coords/sl，断言 cw/MEASURE/FONT/BASELINE |
| 7 | `_heading_core` v13 vs geom 引号 | assertNotEqual | v13 归一化弯引号，geom 保留 |
| 8 | `PN_RE` vs `is_page_number` 字符集 | assertTrue/assertFalse | `PN_RE.fullmatch('‧123')` None vs `is_page_number('‧123')` True |
