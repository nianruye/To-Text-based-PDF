# PIPELINE_BEHAVIOR.md - 管线行为契约 spec

> **状态**：implemented
> **类型**：governance（跨管线公共契约）
> **关联文件**：build_geom.py / build_classic.py / build_pdf_v13.py / fit_common.py / verify_geom.py / utils/*（横排）　+　build_vert.py / verify_vert.py（竖排，见「竖排管线（build_vert.py）」章节）
> **分析来源**：[docs/coupling_analysis.md](../../docs/coupling_analysis.md) / [docs/pipeline_audit.md](../../docs/pipeline_audit.md) / [docs/vert_governance_report.md](../../docs/vert_governance_report.md)（竖排章节的源码核对记录）
> **契约 1-6 + 验收 + 锚点 + 兼容影响矩阵** = 横排（geom / classic / v13）；**「竖排管线（build_vert.py）」章节** = 竖排（V1-V9）

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

## 竖排管线（build_vert.py）

> **范围**：`src/pipelines/build_vert.py`（单脚本，958 行 @ 竖排收尾修复；锚点见 V9）+ `src/test/verify_vert.py`（验证 harness，268 行）。
> **机制分部 spec**：[spec/vertical/](../vertical/)（01 engine / 02 tate_layout / 03 marginalia / 04 frame_lines / 05 pagenum_sequence / 06 derot）。
> **本节事实全部逐条对照源码行号核对**（核对依据与命令见 [docs/vert_governance_report.md](../../docs/vert_governance_report.md) 第二节）。
> **结论先写**：竖排与横排**零代码耦合** —— 不 import `src/utils/*`、env 命名空间不相交、临时文件不重名、不使用 GMPG；
> 唯一共享是 **OCR spotting JSON 格式与数据源**（V3）。所以「改横排不波及竖排、改竖排不波及横排」；但**接口层**
> （argv / env / JSON / 产物命名）改动仍属 api-compat，必须同步本节。

### V1 命令行参数（argv）：与 geom/classic 同序，但无默认值

| argv | 变量 | 语义 | 默认值 |
|---|---|---|---|
| 1 | SL | spotting_lines.json 路径 | **无**（缺 → `IndexError`，非 0 退出） |
| 2 | CO | spotting_coords.json 路径 | **无** |
| 3 | OUT | 输出 PDF 路径 | **无** |
| 4 | SRC | 源 PDF 路径（可选） | `None` |

**源码证据**：L15 `SL = sys.argv[1]; CO = sys.argv[2]; OUT = sys.argv[3]`；L16 `SRC = sys.argv[4] if len(sys.argv) > 4 else None`。

**逐条核对出的差异（勿凭印象）**：

1. **位置顺序与 geom/classic 一致**（都是 `SL CO OUT [SRC]`），不是另一套顺序。
2. **默认值不同**：geom/classic 三项都有默认值（`/opt/test/wz1p108_*.json` / `/tmp/seg2_line.pdf` / SRC=`''`），竖排三项**全无默认**，且 SRC 缺省是 `None` 而非 `''`（无 argparse、无 usage 提示）。
3. **SRC 缺省 = 降级 + 显式警告**：`src_doc is None` 会关掉 **4 项**墨迹特性 —— 书眉/页码/边注（L121）、版框线（L415）、版心右缘墨迹复测（L689，回退 OCR 拟合值 594.9pt）、旋转坐标系页还原（L719 + L766 提前返回）。
   **不报错、退出码仍 0**；但启动时向 **stderr** 逐条打印这 4 项警告（#18：3 参数调试调用不再静默降级，见 V6）。

### V2 环境变量（env）：42 个，全 `VERT_` 前缀

| env | 默认值 | 读取位置 | 缺失/缺省后果 |
|---|---|---|---|
| VERT_PAGES | `''` = 全书 | L17（解析 L1873-1882） | 输出全部页；**范围外页号被静默丢弃**；非法格式（非数字/区间反了）→ `ValueError` |
| VERT_TMP | **`/tmp/vert_<OUT 文件名 stem>_run`**（#20 已修，原 `/opt/test/tmp_vert/run`） | L23（默认值）/ L36（`makedirs`） | 按**产物名 stem** 分离 -> 并发跑不同产物不共用目录；显式设置则用给的值（**空串等同未设**）；不存在则创建 |
| VERT_SPECIAL | `'1'`（开） | L493 | 书眉/页码/边注渲染（**需 SRC**，否则强制关） |
| VERT_FRAME | `'1'`（开） | L810 | 版框线渲染（需 SRC） |
| VERT_LINE_COV | `0.55` | L811 | 界行线覆盖率主阈值（float()，非数字 → `ValueError`） |
| VERT_LINE_COV_LO | `0.30` | L812 | 淡界行线栅格兜底阈值（须 < 主阈值才生效） |
| VERT_H_COV | `0.45` | L813 | 横线判据阈值 |
| VERT_JIE_LOG | `'0'`（关） | L818 | 界行线逐页日志 |
| VERT_FRAME_DEBUG | `'0'`（关） | L819 | 版框检测诊断日志 |
| VERT_FRAME_GAP | `3.2` | L816 | **兜底值**：外粗线缺测时的「外粗线—内细线」空隙量（pt）；有实测一律用实测 |
| VERT_FRAME_TH | `3.4` | L817 | **兜底值**：外粗线厚度（pt，缺测时用） |
| VERT_NCOL_FRAME | 未设 → **标定趟 A 实测**（内框宽÷列距 + 界行线条数互证）；不可测 → 12 | L1081（`N_COL_FRAME`） | 版框内框列数；**别的书不是 12 列**，故默认走标定 |
| VERT_NCOL | 未设 → 每页正文列数的 **90 分位**；无样本回退 11 | L464 | 自动列容量；设为空串等同未设（falsy）；非整数 → `ValueError` |
| VERT_RIGHT_INK | `'1'`（开） | L1152 | 版心右缘墨迹复测；`0` = 回退 OCR 拟合值 594.9pt（需 SRC） |
| VERT_DEROT | `'1'`（开） | L1182 | 旋转坐标系页还原（另需 SRC） |
| VERT_FRAME_LAYOUT | `'1'`（开） | L1293 | 框驱动排版（逐页版框/槽格/列位；需 SRC，`0` = 回退流式排版） |
| VERT_XSCALE | 未设 → **标定值**（源书单字「墨面积/墨高²」比）；不可测 → 0.87 | L117 | 字模横向压缩系数（`1.0` = 不压缩；**`or` 取值，空串等同未设**；float() 非数字 → `ValueError`） |
| VERT_PUNCT_SIZE | 未设 → **标定值**；不可测 → 0.62 | L57 | 标点字号 / 正文字号（挤格标点单独字号） |
| VERT_PUNCT_DX | 未设 → **标定值**；不可测 → 0.81 | L58 | 标点墨心 x = 槽左缘 + DX × 格距 |
| VERT_PUNCT_DY | 未设 → **标定值**；不可测 → 0.85 | L59 | 标点墨心 y = 前字格顶 + DY × 步进 |
| VERT_GAP_HANG | 未设 → **标定值**（墨顶口径）；不可测 → 0.85 | L163 | 挤格标点墨顶相对本字格顶的偏移（× 步进）；DP 预测项 |
| VERT_BR_SIZE | 未设 → **标定值**（各括号族折中尺寸的中位）；不可测 → 0.66 | L345 | 竖排括号字号 / 正文字号（无分档时的默认） |
| VERT_BR_SIZE_MAP | 未设 → 标定值（有则用之，无样本的族回落 VERT_BR_SIZE） | L347 | 按字形覆盖：`︗:0.55,︹:0.49`（逗号分隔，非法项跳过） |
| VERT_BR | `'1'`（开） | L344 | 括号竖排形态替换总开关 |
| VERT_INK_RATIO | 未设 → **探针标定值**（像素口径）；不可测 → 0.88 | L1290 | 单字墨高 / 字号（中位口径，字号←墨高换算用） |
| VERT_INK_ASC | 未设 → **探针标定值**；不可测 → 0.94 | L1291 | 墨顶距基线 = ASC × 字号 |
| VERT_NOTE_INK_RATIO | 未设 → **探针标定值**（注文语料）；不可测 → 0.88 | L599 | 注文字号反推用的墨高比 |
| VERT_NOTE_INK_MAX | 未设 → **fontTools 轮廓口径**的本书用字墨高上界；不可测 → 0.94 | L605 | 满字墨高上限（字号保护用） |
| VERT_NOTE_STEP_RATIO | `0.85` | L597 | 边注/正文 步进比**上限判据**（非书常数：wz6 实测比 0.69，余量 18%；别的书偏紧时用本 env 放宽） |
| VERT_FONT | `NotoSerifCJK-Regular.ttc` | L1977 | 正文字体文件（pxchfon/DVIPDFMX 经 kpathsea 查找；标定趟用同名字体做探针与 fontTools 几何） |
| VERT_GFONT | `NotoSansCJK-Regular.ttc` | L1978 | gothic 字体（数学模式 `\mathgt` 用） |
| VERT_BOLD | `0`（关） | L128 | 墨迹加粗描边线宽（pt，taskL-e；`0` = 输出与不设时逐字节相同） |
| VERT_GAP | `'1'`（开） | L162 | 列内空隙（源书空一格）DP 检测；`0` = 关闭该步（回退到「不补格」渲染） |
| VERT_GAP_REPORT | 未设 → `$VERT_TMP/gaps_detected.json` | L2756 | 空隙检出清单落盘路径（`or` 取值，空串等同未设；验收实例：`data/wz6/wz6_gaps_detected.json`） |
| VERT_GAP_DEBUG | `'0'`（关） | L286 / L288 | 空隙 DP 逐列诊断日志（打印 T0/B/步进/预测/实测/代价） |
| VERT_LOOSE_DEBUG | `'0'`（关） | L1860 | 无版框页兜底行（`page_puts_loose`）诊断日志 |
| VERT_CALIB_PAGES | `16` | L1090 | 标定趟源图侧均布抽样页数（`VERT_CALIB_PAGES=4` 可快速预检） |
| VERT_CALIB_RARE_PAGES | `8` | L2070 | 稀有括号定向补抽页数上限（按缺样本的族分配） |
| VERT_CALIB_REPORT | 未设 → `$VERT_TMP/vert_calib.json` | L2682 | 标定结果落盘路径（含标定值/兜底值/生效值/原始统计） |
| VERT_CALIB_CACHE | 未设（= 每次都重标） | L2511 | 指定 json 则**跳过源图侧与探针**直接用其中的 `values`（同书反复调试用；跨书复用不在契约内） |
| VERT_CALIB_ONLY | `0`（关） | L2693 | `1` = 只跑标定并打印对账表后 `exit 0`（不建排），供新书预检/排障 |
| VERT_CALIB_DEBUG | `0`（关） | L2051 | `1` = 打印探针逐字与源图小字样本明细；`2` = 另打印逐槽 run/文本（最多 8 条） |

> 行号为 **2026-10-15（taskM 自标定改造后）快照**（`grep -n "environ.get('VERT_"`）；`build_vert.py` 新增段落后会整体偏移，**以符号名 grep 为准**。

**布尔类取值的语义**（同一写法 `os.environ.get(k, 默认) not in ('0','false','False')`）：
只有字符串 `0` / `false` / `False` 判**关**，**其它任何值（含空串 `VERT_FRAME=`）都判开**
（例外：`VERT_XSCALE` / `VERT_GAP_REPORT` / `VERT_TMP` / `VERT_CALIB_REPORT` 等用 `or` 取值 —— 空串等同未设）。

**标定类 env 的优先级（taskM 契约）**：**显式 env > 标定值 > 兜底值**。
设了对应的 `VERT_*` 就完全不采纳标定结果（对账表「来源」列标 `env`），未设则用标定值（标 `标定`），
标定不可用时用代码兜底值（标 `兜底`）。据此，**同一份源书 + 同一字体 + 不设任何标定 env 时, 产物可复现**
（实测两次构建（不同 `PYTHONHASHSEED`）`vert.tex` 逐字节相同、逐页 4x 灰度像素全等）。

**与横排 env 的关系**：横排 16 个共享 env + v13 独立 5 个**均无 `VERT_` 前缀**，竖排 42 个**全 `VERT_` 前缀** → 命名空间零交集，
不存在 [coupling_analysis.md](../../docs/coupling_analysis.md) 里「16 env 透传」那类隐式耦合（root-cause #15 不覆盖竖排）。

### V3 输入 JSON：与横排同一格式（唯一共享契约）

- `lines`：`{page_key: [line_str, ...]}`；`coords`：`{page_key: [poly|None, ...]}`（结构与横排契约 3 相同；px 尺度见 V5）。
- 竖排只读这两个文件（L19）；`data/wz6/` 下的 `*_labels.json` / `*_markdown.json`，**竖排不读**。
- key 排序 `sorted(sl.keys(), key=int)`（L20），与横排同规则（字符串数字 key 按 int 升序）。
- **key 集合口径差异（核对发现）**：`build_vert` 只用 **lines** 的 key（L20）；`verify_vert` 取 **coords ∪ lines 的并集**（verify_vert L59）。
  两文件 key 不一致时会先以「页数不 1:1」暴露（wz6 两文件同为 231 个 key，未触发）。

### V4 GMPG 标记：竖排不适用（N/A）

- `build_vert.py` 不写 `GMPG<key>ZZ`（全文 grep 无命中）；`verify_vert.py` 不解析 GMPG。
- 页-源页对齐改用**页序 1:1**：输出第 i 页 ↔ 排序后第 i 个 OCR key（verify_vert L164-171）。
- 后果：一旦页序错乱（多页/少页/乱序），页数 1:1 立即 FAIL；代价是**跨页内容错位检测不到**（逐页只比字符量）。
- 横排的 GMPG 三方契约（渲染端 <-> verify_geom + fit_common）与竖排**无任何关系**。

### V5 坐标空间与页幅

| 项 | 竖排（build_vert） | 横排（geom/classic）对照 |
|---|---|---|
| OCR 坐标尺度 | **2x px = 144dpi**；pt = px ÷ 2（拟合 L75-79；墨迹换算 L180/L189/L286） | 200dpi；pt = px × 72/200 |
| 页幅来源 | **从 SRC PDF 读真页尺寸**（fitz，L87-91）；SRC 缺省时用常量 595.3×1244.1pt（L84） | 从 coords 极值推导（geometry.py L17-19） |
| 页幅落地 | `\paperheight/\paperwidth`（L886-887，pt）+ `\special{papersize}`（L888；bp = pt × 1.00375，L851） | xelatex geometry |
| 页幅校验 | `verify_vert --src-pdf`：输出纸型 vs 源书**众数**纸幅，相对差 ≤ 0.5%（verify_vert L256-257） | `verify_geom` 逐页 |

> 竖排右缘公式 `右缘 = 70 + \oddsidemargin + \textheight`（L83）依赖精确页高 —— 纸型错了整页列位全错，所以页幅校验在竖排属硬项（需显式给 `--src-pdf` 才启用，建议必开）。

### V6 产物与临时文件命名

| 路径 | 写入者 | 说明 |
|---|---|---|
| argv[3] `OUT` | L2785 `os.replace(TMP/vert.pdf, OUT)` | **脚本不派生产物名**；`output/<book>/<book>_vert_*.pdf` 是**调用方约定**（实例：`_full.pdf` 全书 / `_preview.pdf` 预览 / `_notes_check.pdf` 边注核对） |
| `$VERT_TMP`（默认 `/tmp/vert_<OUT stem>_run`） | L23（默认值）/ L36（`makedirs`） | **按输出文件名 stem 分离**（#20 已修）；显式 `VERT_TMP` 覆盖之（空串等同未设） |
| `$VERT_TMP/vert.tex` | L2768-2769 | 中间产物（tex 全文落盘，可复查） |
| `$VERT_TMP/vert.dvi` -> `vert.pdf` | L2772 uplatex / L2773 dvipdfmx | `vert.pdf` 成功后 `os.replace` 到 OUT，不留副本 |
| `$VERT_TMP/vert.aux` / `vert.log` | uplatex | 不清理 |
| `$VERT_GAP_REPORT`（默认 `$VERT_TMP/gaps_detected.json`） | L2752-2766 | **空隙检出清单**（JSON：`n_gap`/`n_cell`/`npage`/`vscale` + 逐条 `page`/`x0`/`ncell`/`extra`/`step`/`text`/`at`）；验收实例 `data/wz6/wz6_gaps_detected.json` |
| `$VERT_CALIB_REPORT`（默认 `$VERT_TMP/vert_calib.json`） | L2680-2691 | **标定结果**（JSON：`pages_sampled`/`pages_used`/`font`/`font_resolved`/`probe`/`n_col_frame`/`br_size`/`values`（标定值）/`fallback`/`effective`）；taskM 新增 |
| `$VERT_TMP/calib_probe/probe.{tex,dvi,pdf,log}` | L2385-2449 `_calib_probe` | **标定探针**（用主 preamble + 逐字 `\put` 渲染 2 页参考字形，供像素口径测墨高/墨心）；taskM 新增，每次构建覆盖写 |

**不冲突性（grep 核对）**：竖排不写 `/tmp/seg2_line.*`、`/tmp/srcpage_*.png`、`/tmp/fig_*.png`、`/tmp/toc_map.json`
-> 与 issue #10（geom/classic 临时文件同名并发冲突）**无关**。

**并发（#20 已修）**：默认临时目录按产物名分离 —— 实测两个并发实例（输出 `conc_1.pdf` / `conc_2.pdf`）分别写 `/tmp/vert_conc_1_run/` 与 `/tmp/vert_conc_2_run/`，均退出码 0。
**同名产物**并发仍会共用 `vert.*` -> 需显式 `VERT_TMP` 分开（属预期，与横排 #10 的「路径分 build_name」同方案）。

**退出码（#18 已修，判据实测标定）**：输入文件缺失（lines/coords/src）-> stderr 显式报错 + `sys.exit(1)`；
编译失败 -> `sys.exit(1)`（L2784-2794）；正常路径 `sys.exit(0)`（L2787）。**失败判据不能只看 rc**：实测正常成功编译的
uplatex **rc 也是 1** —— 唯一报错是类加载期「KANJI Encoding scheme `JT1' unknown.」（preamble L1986 已注明无法在文档内拦截，
upLaTeX 下该命令本就被忽略）。故判据 = `dvipdfmx` rc≠0 **或** `vert.pdf` 未生成 **或** uplatex 输出里有**该容忍项之外**的 `!` 报错行
（nonstopmode 下真出错照样出 PDF，只查产物存在会漏判）。SRC 缺省（3 参数调试调用）-> 只警告、退出码仍 0。
**门禁规定不变：竖排 PASS/FAIL 只看 `verify_vert.py` 的退出码** —— 构建成功不等于产物合格（页数/字符量/越界只能由 verify_vert 判）。
锁定测试：`src/test/unit/test_build_vert_cli.py`（8 项：正常 0 / 输入缺失 1 / 编译失败 1 / 只容忍 JT1 / 临时目录分离与覆盖 / 3 参数警告）。

### V7 横竖有意差异对照（逐条核对，不是假设）

| 维度 | 横排（geom/classic/v13） | 竖排（build_vert） | 一致? |
|---|---|---|---|
| 引擎链 | xelatex + xeCJK | **upLaTeX + tarticle + pxchfon + Noto CJK**（L872-912） | 有意不同 |
| 主参数顺序 | `SL CO OUT [SRC]` | `SL CO OUT [SRC]` | **一致** |
| 主参数默认值 | 有 | **无** | 不同 |
| 验证脚本参数顺序 | `out coords lines` | `out coords lines`（verify_vert L141-143） | **一致** |
| 验证指标 | pitch/占位/溢出/缺页（verify_geom） | 页数/字符量/越界/页幅（verify_vert） | 有意不同 |
| 坐标 DPI | 200 | **144（2x px）** | 有意不同 |
| 页幅来源 | coords 极值推导 | **SRC PDF 真页尺寸** | 有意不同 |
| 页眉/页码机制 | LaTeX 流内（`\vspace` / 页脚） | eso-pic `\put` 逐字绝对定位（源图墨迹实测） | 有意不同 |
| 页-源页标记 | GMPG | **无**（页序 1:1） | 有意不同 |
| 校准驱动 | fit_positional(_classic).py 两趟 | **无**（几何由源书直接拟合，单趟） | 有意不同 |
| 转义实现 | `utils/tex_escape.py`（三模式） | **脚本内联第三套**（L207/L309/L855，只处理 `% # & _`）-> issue #11 的 `_esc_chars` 分叉**不覆盖竖排** | 不同 |
| 共享模块 | `utils/*` 4 个 | **不 import 任何 `src/utils/*`** | **零共享** |
| 共享数据 | OCR spotting JSON（lines/coords） | 同左 | **唯一共享** |

### V8 验收标准（verify_vert.py）

| 硬项 | 判据 | wz6 实测（2026-10-15 重跑，退出码 0 = PASS） |
|---|---|---|
| 页数 1:1 | 输出页数 == OCR key 数（verify_vert L164-165、L247-248） | 231 = 231 |
| 逐页字符量 | 非预期差异页 0（`--char-tol` 默认 80；预期差异页自动识别） | 非预期 0 / 预期 2（p74 幻觉长行、p231 水印页） |
| 整页丢失 | 输出 0 字且源 ≥ 30 字的页 = 0（L192-193、L254-255） | 0 |
| 越界（文本 span + 矢量图形） | 超出页 rect 且 > `--bbox-tol`（0.5pt）的个数 = 0（L198-202、L249-250） | span 0 / 矢量 0 |
| 页幅（需 `--src-pdf`） | 输出纸型 vs 源书众数纸幅相对差 ≤ 0.5%（L256-257） | 0.00% / 0.00% |
| 退出码 | 0 = PASS / 1 = FAIL（L246-264） | 0 |

> 字符量总计（输出 68016 / OCR 69998 = 97.2%）**只打印，不作为 PASS 判据** —— 判据是逐页与非预期页数。

**预期差异页自动识别（不硬编码页号，verify_vert L130-136）**：噪声页 = 非空白字 ≥ `--noise-min-char`(30) 且 CJK 占比 < `--cjk-min`(0.5)；
幻觉长行页 = 单条 OCR 行 ≥ `--long-row`(80) 字；`--expect-low` 可显式追加（与自动识别取并集）。wz6 命中 p74 / p231。

**verify_vert 无 env 依赖**（不 import os），全部参数走 argparse；位置参数顺序与 verify_geom 一致，
另有 `--src-pdf --char-tol --bbox-tol --cjk-min --noise-min-char --long-row --expect-low --top --json`。

### V9 实现锚点（build_vert.py @ taskM 自标定改造，2794 行）

| 模块 | 行号 | 说明 |
|---|---|---|
| argv/env 入口 | L15-40 | 4 个 argv + 输入校验（#18）+ TMP 目录创建（#20 默认按 OUT stem） |
| §1.0 挤格标点 | L41-86 | `PUNCT_HANG` L48 / `PUNCT_ASCII` L51 / `PUNCT_INK` L53 / `PUNCT_SIZE·DX·DY` L57-59 / `_norm_punct` L61 / `n_cells` L71 / `char_cells` L75 |
| §1.0a 字模横向压缩 | L87-118 | `PAGE_ORIGIN_BP` L116 / `XSCALE` L117 / `_put_tex` L137 |
| §1.0a2 墨迹加粗 | L119-151 | `BOLD_W` L128 / `_vb` L130 |
| §1.0b 列内空隙 | L152-297 | `GAP_ON` L162 / `GAP_HANG` L163 / DP 代价 L164-172 / `_gap_log` L174 / `fit_gaps` L176 |
| §1.0c 标点竖排形态 | L298-364 | `VERT_FORMS` L314 / `VERT_METRICS` L322 / `_parse_br_map` L331 / `BR_ON·BR_SIZE_DEF·BR_SIZE` L344-347 / `_br_put` L349 |
| §1.0d 列拆分归位 | L365-398 | `BR_OPEN_OF` L376 / `fix_split_brackets` L378 / 应用点 L405-415 |
| §1 参数拟合 | L399-486 | `col_stats` L400 / `is_body_col` L425 / FS·PITCH·HCOL·TTOP·RIGHT_p L466-470 / `NCOL` L464 / textwidth·textheight·topmargin·oddsidemargin L470-474 |
| §1.8 书眉 + 页码 | L487-589 | `special_rows` L497 / `src_gray` L516 / `ink_extent` L526 / `special_tex` L554 / `X_CAL`·`Y_CAL` L494-495 |
| §1.9 边注 | L590-711 | `NOTE_STEP_RATIO` L597 / `NOTE_INK_RATIO` L599 / `NOTE_INK_MAX` L605 / `note_rows` L607 / `note_cols` L622 / `note_tex` L681 |
| §1.87 页码序列纠正 | L712-799 | `pn_parse` L727 / `pn_text` L746 / `pn_sequence_fix` L750；全局 `PN_FIX` L794 |
| §1.95 版框线 | L800-1079 | `V_FRAME_GAP`·`V_FRAME_TH` L816-817 / `N_COL_FRAME` L822 / `_runs` L824 / `_grid_fit` L833 / `_bar_px` L899 / `frame_geom` L909 / `frame_tex` L1050 |
| §1.955 标定趟 A（列数） | L1080-1144 | `CALIB_N_PAGE` L1090 / `_calib_ncol_page` L1093 / `_calib_ncol_pick` L1108 / `CALIB_SAMP` L1126 / 驱动 L1127-1143 |
| §1.96 版心右缘墨迹复测 | L1145-1166 | 抽样约 12 页版框内右线中位 = 563.1pt（`VERT_RIGHT_INK`） |
| §1.97 旋转页还原 | L1167-1272 | `_ink_char_cols` L1186 / `_lin_fit` L1216 / `derot_rows` L1226（只替换本页 `all_rows`） |
| §1.98 框驱动排版 | L1273-1906 | `INK_RATIO`·`INK_ASC` L1290-1291 / `_slot_runs` L1295 / `_ink_bands` L1313 / `_grid_from_bands` L1326 / `page_metrics` L1346 / `_align_rows_slots` L1447 / `page_rows` L1521 / `col_puts` L1604 / `page_puts` L1687 / `page_puts_loose` L1751 / `note_puts_frame` L1866 |
| §2 每页正文列（流式回退） | L1907-1968 | `page_tex` L1908（列块总宽受内框约束） |
| 页选择 | L1957-1967 | `VERT_PAGES` 解析（范围外静默丢弃） |
| 字体选择 + preamble | L1969-2022 | `VERT_FONT`·`VERT_GFONT` L1977-1978 / tarticle + pxchfon + JY1/JT1 补丁 + eso-pic |
| §1.956 标定趟 B（参数） | L2023-2696 | `CALIB_DEF` L2054 / `_calib_xscale` L2095 / `_calib_punct_size` L2105 / `_calib_punct_pos` L2115 / `_calib_br_forms` L2124 / `_calib_font_geom` L2171 / `_calib_match_small` L2219 / `_calib_src_page` L2278 / `_calib_probe` L2385 / 应用·对账·落盘 L2452-2696 |
| §2.5 空隙清单落盘 | L2752-2766 | `_gap_log` JSON（`VERT_GAP_REPORT`） |
| 装配 + 编译 | L2697-2794 | `\newpage` 分隔（末页不加）/ uplatex L2773 / dvipdfmx L2774 / 产物搬移 + `exit(0)` / 失败判据与 `exit(1)` |

> 行号为 **2026-10-15（taskM 改造后）** 实测；`build_vert.py` 新增段落后会整体偏移，**以符号名 grep 为准**
> （`grep -n '^# ---------- '` / `grep -n '^def '`）。竖排 spec 分部锚点见 [spec/vertical/README.md](../../spec/vertical/README.md)。

### 实测基线（2026-10-15 重跑核对）

- **构建**：`VERT_TMP=/tmp/gov_vert_full ... build_vert.py data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/gov_vert_full.pdf source_pdf/wz6.pdf` -> 退出码 0，**231 页耗时 11 秒**（本机）。
- **复现性**：重跑产物与 `output/wz6/wz6_vert_full.pdf` **逐页文本、页幅、矢量图形数（4075）全等**（文件 1 字节差为 PDF 元数据）-> 验证结论不依赖某个被冻结的旧产物。
- **拟合参数（日志首行）**：字号 34.4pt / 列距 47.6pt / 列高 863.7pt / 天头 318.6pt / 右缘 563.1pt（OCR 拟合 594.9pt 经墨迹复测修正）/ 列容量 13 / 页 595.3×1245.3pt。
- **验收**：`verify_vert` PASS —— 231:1 / 68016÷69998 = 97.2% / 越界 span 0 + 矢量 0 / 页幅相对差 0.00%。
- 注：日志条数类统计（书眉 107 / 页码 122 / 边注 65 / 版框 228 页 / 页码纠正 18 处）已在竖排收尾修复中独立复核并同步进 `spec/vertical/*`（治理遗留 R1 关闭）。
  旧值 121 / 64 的来源已定位：那是**关掉 `VERT_DEROT`** 时的计数（p159 旋转页少 1 条页码 + 1 条边注）；页码纠正 18 处与 derot 开关无关（两种配置都 18）。
  统计脚本与输出见 [docs/vert_fix18_20_27_report.md](../../docs/vert_fix18_20_27_report.md)。

### CI 结论（竖排验证不进 CI）

竖排验证**不接入 `.github/workflows/ci.yml`**，维持「本地 PR 合并前手动跑」（理由与备选方案见
[docs/vert_governance_report.md](../../docs/vert_governance_report.md) 第三节）。要点：竖排验证的输入（`output/` 产物、`data/wz6` OCR 数据）
按仓库策略不入库（`.gitignore` 的 `*.pdf` / `output/` + `data/wz6` 未跟踪），且重建需要 upLaTeX 栈（`texlive-lang-japanese` 等）与源 PDF 58MB，
与现有「不依赖 xelatex/GPU 的最小 CI」定位不符。

---

## 验收标准

| 标准 | 命令 | 通过条件 |
|---|---|---|
| unit 纯函数 | `/usr/bin/python3 -m pytest src/test/unit` | 188 passed |
| invariants 不变量 | `/usr/bin/python3 -m pytest src/test/invariants` | 13 passed |
| verify_geom 硬约束 | `/usr/bin/python3 src/test/verify_geom.py <out> <coords> <lines>` | exit=0（页数1:1/split 0/missing 0） |
| verify_geom pitch | `VERIFY_PITCH_FLOOR=85 ... verify_geom.py ...` | exit=0（wz1 pitch 89.5%） |
| baseline diff | 重跑快照 -> diff `baseline_*.json` | pitch/页数/空白/溢出 无意外漂移 |
| **verify_vert 竖排硬约束**（见 V8） | `/usr/bin/python3 src/test/verify_vert.py <out.pdf> <coords> <lines> --src-pdf source_pdf/<book>.pdf` | exit=0（页数 1:1 / 非预期缺字页 0 / 整页丢失 0 / 越界 span+矢量 0；wz6 实测 231 页 97.2% 越界 0/0）|

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
| 竖排管线 | `pipelines/build_vert.py` | 924 行 | 单脚本：无校准驱动、不 import `utils/*`（契约 V1-V6，锚点 V9） |
| 竖排校验 | `test/verify_vert.py` | 268 行 | 页数/字符量/越界/页幅 + 退出码（无 GMPG、无 env，验收 V8） |
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
| **竖排行** `pipelines/build_vert.py` | **仅竖排管线** -> verify_vert(wz6)；**不波及横排任何环节**（无 unit/invariants 覆盖） | verify_vert 退出码 + 逐页字符量/越界（本地跑，不进 CI） |
| **竖排行** `test/verify_vert.py` | 竖排验证 harness -> 所有竖排验证调用 | 退出码行为 + wz6 基线（231 页 / 97.2% / 越界 0+0） |
| **竖排行** `VERT_*`（42 个 env） | 仅竖排；与横排 env 命名空间**零交集**（无透传、无隐式共享） | 无 unit 覆盖 -> 改动后重跑 verify_vert + 抽样对照源墨迹 |
| **竖排行** upLaTeX + tarticle + pxchfon + Noto CJK 栈 | 仅竖排（横排走 xelatex + xeCJK） | build_vert 编译日志零错 + 页幅/字形抽查 |
| **竖排行** OCR spotting JSON（`data/<book>/*_spotting_{lines,coords}.json`） | **三管线共读同一格式 = 横竖唯一共享契约** | 横排：verify_geom（GMPG/pitch）；竖排：verify_vert（页数/字符量） |
| **竖排行** `utils/tex_escape.py` 等 4 个共享模块 | geom + classic（**竖排不 import**） | unit + invariants + verify_geom；**对竖排零影响** |
| **竖排行** GMPG 格式 | geom + classic 渲染端 <-> verify_geom + fit_common（**竖排不参与**） | verify_geom split > 0 = FAIL；竖排 N/A（V4） |

**矩阵结论**：竖排与横排的回归面**互不重叠** —— 竖排改动只需竖排自证（verify_vert + 抽样对照），横排改动对竖排零影响，反之亦然。
唯一需要两边同时确认的是**共享数据层**（OCR spotting JSON 格式，V3）与**文档接口层**（argv/env/产物命名，V1/V2/V6）：任何一侧改这些 = api-compat，必须同步本节。
