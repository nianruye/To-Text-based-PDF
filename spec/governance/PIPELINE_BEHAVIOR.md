# PIPELINE_BEHAVIOR.md - 管线行为契约 spec

> **状态**：implemented
> **类型**：governance（跨管线公共契约）
> **关联文件**：build_geom.py / build_classic.py / build_pdf_v13.py / fit_common.py / verify_geom.py / utils/*
> **分析来源**：[docs/coupling_analysis.md](../../docs/coupling_analysis.md) / [docs/pipeline_audit.md](../../docs/pipeline_audit.md)

---

## 契约 1：命令行参数（argv）

### geom / classic / fit_common（同序）

| argv | 变量 | 语义 | 默认值 |
|---|---|---|---|
| 1 | SL | spotting_lines.json 路径 | `/opt/test/wz1p108_spotting_lines.json` |
| 2 | CO | spotting_coords.json 路径 | `/opt/test/wz1p108_spotting_coords.json` |
| 3 | OUT | 输出 PDF 路径 | `/tmp/seg2_line.pdf` |
| 4 | SRC | 源 PDF 路径（图页贴原图，可选） | `''` |

**证据**：geom L19-22 / classic L19-22 / fit_common L12-13

### build_pdf_v13（不同序）

| argv | 变量 | 语义 | 默认值 |
|---|---|---|---|
| 1 | SRC_PDF | 源 PDF | `/opt/test/优化前.pdf` |
| 2 | OUT_PDF | 输出 PDF | `/opt/test/最终版_v13.pdf` |
| 3 | SPOTTING_LINES | | `/opt/test/spotting_lines.json` |
| 4 | SPOTTING_COORDS | | `/opt/test/spotting_coords.json` |
| 5-7 | TITLES? / MARKDOWN? / PAGE_NUMBERS? | 可选 | `''` |

**证据**：v13 L8-14

### verify_geom（argparse，顺序与管线相反）

| 位置 | 参数 | 语义 |
|---|---|---|
| 1 | out_pdf | 输出 PDF |
| 2 | src_coords | spotting_coords（注意：不是 lines） |
| 3? | src_lines | spotting_lines（可选） |
| -- | --src-pdf, --dpi=200, --sample, --json, --tol-height=0.05, --tol-pitch=0.03 | 可选 |

**证据**：verify_geom.py L124-133

**兼容影响**：改 argv 顺序 = api-compat，必须同步 fit_common 转发逻辑 + verify_geom 调用 + conftest fixture。

---

## 契约 2：环境变量（16 个共享 + v13 独立 5 个）

### 共享 env（geom + classic 一致，经 fit_common 透传）

| env | 默认值 | 读取位置 | 缺失后果 |
|---|---|---|---|
| LAYJSON | `''` | geom L258 / classic L256 | 无版面块，走启发式 |
| PAGE_FONT | `''` | geom L481 | BODY=NOTE=FONT |
| POSITIONAL | `''` | geom L221 | 不做位置还原（fit_common 强制 '1'） |
| PER_PAGE_PITCH | `''` | geom L95 | 全局 LINESPREAD |
| LAYOUT_HEADINGS | `''` | geom L294 | 仅启发式标题 |
| OVERBOUND | `'1.115'` | geometry.py L33 | 用 1.115 |
| FONT_SCALE | `'1.0'` | geometry.py L35 | 用 1.0 |
| PUNCT_WEIGHT | `'0.2'` | geometry.py L47 | 用 0.2 |
| REGION_LAYOUT | `''` | geometry.py L48 | USE_REGION=False |
| REGION_FONT_SCALE | `'1.03'` | geometry.py L49 | 用 1.03 |
| PAGENUM_GLOBAL_TABLE | `''` | page_numbers.py L17 | pntab={} |
| PAGENUM_OFFSET | `'0'` | geom L37 | offset=0 |
| TOC_HEADING_MAP | `''`->`/tmp/toc_map.json` | geom L63 | 两级回退+自动扫描 |
| POS_FILL | `'1.08'`(管线) / `'0.95'`(fit) | geom L756 / fit_common L89 | 单趟 1.08，校准 0.95 |
| VERIFY_MARK | `''` | geom L524 | 不注入 GMPG（fit_common 强制 '1'） |
| POS_EST_LOG | `''` | geom L926 | 不导出估高（fit_common 设） |

### v13 独立 env

| env | 默认值 | 证据 |
|---|---|---|
| LINE_LEVEL | `''` | v13 L17 |
| GEOM_FONT / GEOM_TARGET / GEOM_STRETCH | (无) | v13 L760-768 |
| TOC_HEADING_MAP_OUT | (无) | v13 L1300 |

**兼容影响**：改 env 默认值 = api-compat，必须更新本 spec + 跑两条管线 + baseline diff。

---

## 契约 3：spotting JSON 键结构

### spotting_lines.json

- 结构：`{page_key_str: [line_str, ...]}`
- key = `str(pi)`，0-based 页索引（字符串数字）
- 消费者：`sorted(sl.keys(), key=int)`

### spotting_coords.json

- 结构：`{page_key_str: [poly_or_None, ...]}`
- poly = `[[x,y],[x,y],[x,y],[x,y]]`（4 点多边形，px @ DPI=200）
- list 下标与 spotting_lines[key] 1:1 对齐

### LAYJSON

- 顶层是 list（按页索引，非 dict）
- 每页 dict 含 `prunedResult.parsing_res_list[].{block_label, block_bbox, block_content}`
- block_label: image / figure_title / doc_title / paragraph_title / title / aside_text / number

**兼容影响**：改 JSON 结构 = api-compat，需同步 OCR 生产者（run_spotting_ocr.py）+ 所有消费者。

---

## 契约 4：GMPG 标记格式

- **格式**：`GMPG<数字>ZZ`，数字 = 0-based 源页 key
- **写入**：geom L525/L612、classic L546/L633（VERIFY_MARK=1 时 `\put(1,1){...GMPG<key>ZZ}`）
- **解析**：verify_geom L25 `re.compile(r'GMPG(\d+)ZZ')`、fit_common L38 `re.search(r'GMPG(\d+)ZZ', ...)`
- **契约**：渲染端写，校验/校准端按此归组物理页到源页。一源页对多物理页 = 溢出 = 校准失效。
- **v13 不写 GMPG** -> v13 输出走 verify 时退回按序号 1:1。

**兼容影响**：改 GMPG 格式 = api-compat，必须同步渲染端 + verify + fit_common 三方。

---

## 契约 5：DPI 坐标空间（三套并存）

| 坐标空间 | DPI | 用途 | 换算 |
|---|---|---|---|
| spotting coords | 200 px | 行 bbox | pt = px x 72/200 |
| LAYJSON block_bbox | 142 px | 版面块 | x200/142 转 spotting 空间 |
| PDF 页面 | pt | 输出 | PAGE_W = round(xmax x 72/200) |

**页面尺寸推导**（geometry.py L17-19）：从 coords 极值推导，**不从 SRC PDF 读**。coords 缺失回退 405x633。

**兼容影响**：改 DPI 或坐标换算 = api-compat，波及 geometry + image_blocks + verify_geom。

---

## 契约 6：输出 PDF / 临时文件命名

| 路径 | 写入者 | 共享? | 冲突? |
|---|---|---|---|
| `/tmp/seg2_line.tex` | geom L930 / classic L1019 | geom+classic 同名 | **并发冲突** |
| `/tmp/seg2_line.pdf` | geom L932 / classic L1021 | 同名 | **并发冲突** |
| `/tmp/srcpage_{k}.png` | geom L368 / classic L370 | 同名 | **并发冲突** |
| `/tmp/fig_{key}_{i}.png` | image_blocks.py L60 | 共享 | - |
| `/tmp/toc_map.json` | v13 L1301 写 / geom L63 读 | 跨管线传递 | - |
| `/tmp/xelatex_v13.tex` | v13 L2039 | v13 独立 | 不冲突 |
| `tempfile.mkdtemp('fitpos_')/` | fit_common L66 | 隔离 | 安全 |

**兼容影响**：改 /tmp 路径 = api-compat，需同步 fit_common（subprocess 调用）+ conftest fixture。

---

## 验收标准

| 标准 | 命令 | 通过条件 |
|---|---|---|
| unit 纯函数 | `/usr/bin/python3 -m pytest src/test/unit` | 133 passed |
| invariants 不变量 | `/usr/bin/python3 -m pytest src/test/invariants` | 13 passed |
| verify_geom 硬约束 | `/usr/bin/python3 src/test/verify_geom.py <out> <coords> <lines>` | exit=0（页数1:1/split 0/missing 0） |
| verify_geom pitch | `VERIFY_PITCH_FLOOR=85 ... verify_geom.py ...` | exit=0（wz1 pitch 89.5%） |
| baseline diff | 重跑快照 -> diff `baseline_*.json` | pitch/页数/空白/溢出 无意外漂移 |

---

## 实现锚点

| 模块 | 文件 | 行号 | 说明 |
|---|---|---|---|
| 几何标定 | `utils/geometry.py` | L13-50 | calibrate(sl, co, DPI) 共享 |
| LaTeX 转义 | `utils/tex_escape.py` | L20-35 | escape_latex(text, mode) 三模式 |
| 页码处理 | `utils/page_numbers.py` | L13-50 | load_pntab/infer_lay_numbers/PN_RE |
| 书影图块 | `utils/image_blocks.py` | L14-80 | detect_fig_bands/extract_figs/in_figure/in_figcaption(ctx) |
| LaTeX preamble | `pipelines/_latex_preamble.py` | L16-35 | build_latex(mode, ...) |
| 校准驱动 | `calibration/fit_common.py` | L16-90 | render(build_name)/measure_heights/main(build_name) |
| 现代书籍管线 | `pipelines/build_geom.py` | 930 行 | import 5 共享模块 + wrapper |
| 古籍管线 | `pipelines/build_classic.py` | 1024 行 | import 同 geom + 古籍特色 |
| 旧管线 | `pipelines/build_pdf_v13.py` | 2056 行 | src/ 内孤立 |
| 几何校验 | `test/verify_geom.py` | 303 行 | GMPG 归组 + pitch/溢出/退出码 |
| 单元测试 | `test/unit/test_pure_funcs.py` | 506 行 | ast 提取 12 函数 + 对比 + 超长 |
| 不变量测试 | `test/invariants/test_invariants_*.py` | 6+7 不变量 | 截取子集跑管线 |
| 基线快照 | `test/snapshots/baseline_*.json` | 3 份 | wz1/优化前/wz2 指标 |
| 耦合分析 | `docs/coupling_analysis.md` | - | 依赖图 + 状态地图 + 契约 + 风险因果链 |

---

## 兼容影响矩阵

| 改动文件 | 影响范围 | 拦截点 |
|---|---|---|
| `utils/tex_escape.py` | geom + classic 两管线转义 -> fit_positional + fit_positional_classic 输出 | unit TestEscChars/TestEscapeTex/TestCrossFuncDivergence |
| `utils/geometry.py` | geom + classic 字号/行距/版心 -> 两管线全链 | unit TestEffChars + invariants + verify_geom pitch |
| `utils/page_numbers.py` | geom + classic 页码 -> 两管线页脚 | invariants + verify_geom（split/missing） |
| `utils/image_blocks.py` | geom + classic 图块 -> 两管线图页 | invariants + verify_geom |
| `pipelines/_latex_preamble.py` | geom + classic preamble -> 两管线 PDF | invariants + verify_geom pitch + .tex 抽查 |
| `calibration/fit_common.py` | fit_positional + fit_positional_classic 两校准链 | verify_geom 退出码 + baseline diff |
| `pipelines/build_geom.py` | 仅 geom 管线 -> fit_positional | unit(geom fixture) + invariants(geom) + verify_geom(wz1) |
| `pipelines/build_classic.py` | 仅 classic 管线 -> fit_positional_classic | unit(classic fixture) + invariants(classic) + verify_geom(wz2) |
| `pipelines/build_pdf_v13.py` | src/ 内孤立，无影响 | unit(v13 ast 提取) |
| `test/verify_geom.py` | 验证 harness -> 所有 verify_geom 调用 | 退出码行为 + baseline |
| GMPG 格式 | 渲染端 <-> verify + fit_common 三方 | verify_geom split > 0 = FAIL |
