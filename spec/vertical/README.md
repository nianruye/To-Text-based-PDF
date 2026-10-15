# 竖排书排版 Spec 索引

竖排（繁体/古籍竖排）书还原（`src/pipelines/build_vert.py`）。竖排是系统的**一等文档类型**，
与古籍（`build_classic.py`）/现代书籍（`build_geom.py`）并列，见 [00_system_architecture.md](../00_system_architecture.md)。

**样本**：wz6 =《毛泽东选集》第二卷（繁体竖排扫描书，231 页）
**产物**：`output/wz6/wz6_vert_full.pdf`（231 页，= 源书页数）
**完整实现报告**：`docs/vert_v2_report.md`（v2 增量）+ `docs/vert_v2_task.md`（v1.4 参数语义）

## Spec 文件

| 编号 | 文件 | 功能 | 实现锚点（build_vert.py） | 验收 |
|---|---|---|---|---|
| 01 | [engine.md](01_engine.md) | 引擎链选型（upLaTeX + tarticle + pxchfon + Noto TC）+ JY1/JT1 报错修法 | preamble L872-912、编译 L936-937 | 编译零报错、字形与源书同款 |
| 02 | [tate_layout.md](02_tate_layout.md) | tate 参数语义（textwidth/textheight/右缘公式）+ 列参数拟合 + 断列 | L64-113 参数拟合、L811-858 `page_tex`、L682-702 右缘复测 | 列数/列位/断点与源书一致 |
| 03 | [marginalia.md](03_marginalia.md) | 书眉/页码/边注（eso-pic 带星版 + 墨迹实测定位） | L125-213（书眉页码）、L215-315（边注） | 位置 vs 源墨迹、无重叠发虚 |
| 04 | [frame_lines.md](04_frame_lines.md) | 版框线（双边外框 + 界行线 + 淡线栅格兜底） | L405-680（常量/`_grid_fit`/`frame_geom`/`frame_tex`） | 内框/界行线 vs 源墨迹 |
| 05 | [pagenum_sequence.md](05_pagenum_sequence.md) | 页码序列拟合纠正（分段等差 + 邻页插值） | L317-403（`pn_parse`/`pn_text`/`pn_sequence_fix`） | 纠正记录逐条复核 |
| 06 | [derot.md](06_derot.md) | OCR 旋转坐标系页还原（`derot_rows`） | L704-808（`_ink_char_cols`/`_lin_fit`/`derot_rows`） | 旋转页列位/字号 vs 源书 |

## 架构

```
source_pdf/wz6.pdf --(OCR, 官方 API)--> data/wz6/wz6_spotting_{lines,coords}.json  (2x px = 144dpi)
                                          |
                                          v
                     src/pipelines/build_vert.py   (单脚本, 无独立校准驱动)
                       1) 参数拟合(列高/字号/列距/天头/右缘)          §1
                       2) 书眉/页码 墨迹实测 -> eso-pic \put           §1.8  [03]
                       3) 边注 墨迹实测字列 -> eso-pic \put            §1.9  [03]
                       4) 页码序列拟合纠正                            §1.87 [05]
                       5) 版框线检测 -> eso-pic \rule                 §1.95 [04]
                       6) 版心右缘墨迹复测                            §1.96 [02]
                       7) 旋转坐标系页还原(仅该页)                    §1.97 [06]
                                          |
                                   tarticle tex
                                          v
                          uplatex -> dvipdfmx -> output/wz6/*.pdf     [01]
                                          |
                                          v
                     src/test/verify_vert.py  (页数1:1 / 逐页字符量 / 越界 / 退出码)
```

## 与横排管线的关系（共享 / 专属）

| 项 | 横排（geom/classic） | 竖排（build_vert） |
|---|---|---|
| 引擎 | xelatex + xeCJK | **upLaTeX + tarticle + pxchfon**（横排那套无 tate） |
| 几何标定 | 满行宽 ÷ 满行字数 = 字号 | 列长(OCR 盒高) ÷ 字数 = 字号；列距 = 相邻列 x0 差中位 |
| 主排版流 | 行流 + `\vspace` 位置还原 | **列流**：每列 `{\fontsize{字号}{列距}...\par}`，`\par` 出列 |
| 边栏元素 | aside 竖排 shortstack | eso-pic `\put` 逐字绝对定位（墨迹实测坐标） |
| 验证脚本 | `verify_geom.py`（pitch/页高/占位） | `verify_vert.py`（页数/字符量/越界） |
| 共享 | OCR 数据格式（lines/coords JSON）、PaddleOCR-VL 数据源 | 同左 |
| 代码共享 | `src/utils/`（tex_escape / geometry / page_numbers / image_blocks） | **无**：`build_vert.py` 是单脚本，不 import `src/utils/`，转义在脚本内联实现（转义契约与横排不同源，横排的 `_esc_chars` 分叉 issue 不覆盖竖排） |

> 竖排脚本目前**不依赖** `src/calibration/fit_positional*.py`（无两趟校准：竖排列位由源书几何直接决定）。

## 当前指标（wz6，231 页）

| 指标 | 值 | 来源 |
|---|---|---|
| 页数 | 231 = 源书 231（1:1） | `verify_vert.py` |
| 逐页字符量 | 输出 68016 / OCR 69998 = 97.2% | `verify_vert.py` |
| 越界 span / 矢量 | 0 / 0 | `verify_vert.py` |
| 预期差异页 | 2 页（OCR 幻觉长行页、水印页，按内容特征自动识别） | `verify_vert.py` |
| 版框 | 228/231 页（12 格 = 13 条线栅格） | build_vert 日志 |
| 书眉 / 页码 / 边注 | 107 / 122 / 65 条 | build_vert 日志（#27 实测复核） |
| 页码序列纠正 | 18 处（拟合 `value = 1.000*page + 176.0`） | build_vert 日志（#27 实测复核） |
| 回归测试 | 209 全绿（unit 196 + invariants 13） | `src/test/` |

> 条数为默认配置（`VERT_DEROT=1`）下的实测值。旧文档记的页码 121 / 边注 64 是**关掉旋转页还原**时的计数
> （p159 旋转页少 1 条页码 + 1 条边注，实测对照见 [docs/vert_fix18_20_27_report.md](../../docs/vert_fix18_20_27_report.md)）；
> 页码序列纠正 18 处与 derot 开关无关（两种配置都 18）。

## 运行

```bash
cd /opt/test
# 全书重建（约 6 分钟: uplatex 编译 231 页）
/usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json \
  output/wz6/wz6_vert_full.pdf source_pdf/wz6.pdf

# 验证（硬指标 PASS/FAIL 退出码）
/usr/bin/python3 src/test/verify_vert.py output/wz6/wz6_vert_full.pdf \
  data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json --src-pdf source_pdf/wz6.pdf

# 只出若干页（快速迭代）
VERT_PAGES=3-8 /usr/bin/python3 src/pipelines/build_vert.py ... output/wz6/wz6_vert_preview.pdf source_pdf/wz6.pdf
```

**环境开关注释**（默认全开；调试用）：

| env | 默认 | 作用 |
|---|---|---|
| `VERT_PAGES` | 全书 | 只输出指定页（`3-12` / `3,5`） |
| `VERT_SPECIAL` | 1 | 书眉/页码/边注渲染（关闭=0；需源 PDF 才能测墨迹） |
| `VERT_FRAME` | 1 | 版框线渲染 |
| `VERT_RIGHT_INK` | 1 | 版心右缘用源图墨迹复测（`0` = 回退 OCR 拟合值） |
| `VERT_DEROT` | 1 | 旋转坐标系页还原 |
| `VERT_NCOL` | 自动 | 列容量（覆盖「最密页」列数） |
| `VERT_LINE_COV` / `VERT_LINE_COV_LO` | 0.55 / 0.30 | 界行线覆盖率主阈值 / 淡线兜底阈值 |
| `VERT_TMP` | `/tmp/vert_<输出文件名 stem>_run` | tex/dvi/pdf 临时目录（按产物名分离，并发不共用；显式设置则用给的值） |
| `VERT_FRAME_DEBUG` / `VERT_JIE_LOG` | 0 | 版框检测诊断 / 界行线日志 |

## 测试点

1. **页数 1:1**（硬）：231 = 231 —— `verify_vert.py` 退出码 0
2. **逐页字符量**：非预期差异页 0（wz6 p74/p231 为预期，见 `verify_vert.py` 的「预期差异页」自动识别机制）
3. **越界**：全书 span/矢量 0 个超出页 rect
4. **免回归**：改动后重跑 `verify_vert.py` + `pytest src/test/unit src/test/invariants`（横排 201 项不受影响）
