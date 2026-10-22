# 竖排书排版 Spec 索引

竖排（繁体/古籍竖排）书还原（`src/pipelines/build_vert.py`）。竖排是系统的**一等文档类型**，
与古籍（`build_classic.py`）/现代书籍（`build_geom.py`）并列，见 [00_system_architecture.md](../00_system_architecture.md)。

**样本**：wz6 =《毛泽东选集》第二卷（繁体竖排扫描书，231 页）
**产物**：`output/wz6/wz6_vert_full.pdf`（231 页，= 源书页数）
**完整实现报告**：`docs/vert_v2_report.md`（v2 增量）+ `docs/vert_v2_task.md`（v1.4 参数语义）

## 无版框书（#29）实现锚点

无版框路径（NF）与「有版框」路径共用同一套函数，开关 = `NF_MODE`（`FRAME_REF is None`，§1.975）。
taskP / taskP2 为该路径新增/修正的锚点：

| 项 | 锚点 | 说明 |
|---|---|---|
| 逐页门限 / 去印刷线 / 伪版心 | §1.06 L625-755（`_nf_ink_gray` L627/`_nf_lines` L651/`_nf_delines` L672/`_nf_ink` L690/`_nf_box` L702）、§1.975 L1720-1966（`nf_body_rows` L1777/`nf_join_rows` L1784/`nf_short_cols` L1801/`nf_fill_bands` L1821/`nf_edges` L1866/`_nf_fix_page` L1855/`_nf_clamp_box` L1952） | 版心夹回纸幅（taskP2）、短列证据补带（taskP2） |
| 伪槽格统计 / 行槽配平 | §1.98 L2027-2118（`_slots_of_edges` L2105）、L2152-2200（`_metrics_finish` L2152）、`_align_rows_slots` L2286、`page_rows` L2367（taskP2: NF 页注行数不得超过注槽数 +1） |
| 列渲染 / 夹取 / 兜底 | `col_puts` L3790、`_pv_clamp_on` L3729、`_put_tex` L435、`_nf_hrow_page` L2570/`_nf_hrow_puts` L2586（横排页兜底）、`_nf_rescue_rows` L2619（残余列补救）、`page_puts` L2714（taskP2: 列框兜底重排）、`page_puts_loose` L2821 |
| 逐页纸型 / 右缘 | 建排主循环 L3770-3795（taskP2: 小开本页右缘按本页纸宽夹取） |
| **短列检出 / 标点占格 / 引號修剪**（taskS） | §1.0a0 L157-165（`PUNCT_CELL`/`_punct_own`）、§1.976 L1813-2077（`NF_SB_*`/`_big_hm` L1947/`_sb_ref_hm` L1962/`_sb_band` L1976/`nf_short_bands` L2030/`_sb_pitch` L2067）、`_trim_marks` L2408、调用点 `_nf_frame` L2316 / `_metrics_finish` / `page_puts` L3113、标定 `_calib_punct_cell` L4440 |
| **标点墨迹口径**（taskT） | §1.956：`_calib_own_marks` L4614（占格书标点样本按格内墨心取）、`_calib_punct_ink` L4420（NF 用探针渲染实测墨心）、`_calib_src_page(...marks=False)` L4652/L4723（第一趟只收槽格记录）、标定执行 L4908（(b0) 先定 `PUNCT_CELL`）/ L4995（(c2) `PUNCT_INK` 口径） |

## Spec 文件

| 编号 | 文件 | 功能 | 实现锚点（build_vert.py） | 验收 |
|---|---|---|---|---|
| 01 | [engine.md](01_engine.md) | 引擎链选型（upLaTeX + tarticle + pxchfon + Noto TC）+ JY1/JT1 报错修法 | preamble L3049、编译 L3906-3928 | 编译零报错、字形与源书同款 |
| 02 | [tate_layout.md](02_tate_layout.md) | tate 参数语义（textwidth/textheight/右缘公式）+ 列参数拟合 + 断列 | L485-568 参数拟合、L2978-3038 `page_tex`、L1633-1652 右缘复测、L2027-2366 框驱动 §1.98（槽格/列位/列顶数据驱动） | 列数/列位/断点与源书一致 |
| 03 | [marginalia.md](03_marginalia.md) | 书眉/页码/边注（eso-pic 带星版 + 墨迹实测定位；门限全部相对量 §0.5/§1.05） | L760-870（书眉页码：`special_rows` L770/`ink_extent` L801/`special_tex` L833）、L871-1037（边注：`_calib_note_ratio` L879/`note_rows` L929/`note_cols` L945/`note_tex` L1005） | 位置 vs 源墨迹、无重叠发虚 |
| 04 | [frame_lines.md](04_frame_lines.md) | 版框线（双边外框 + 界行线 + 淡线栅格兜底；几何区间/线宽判据相对化） | L1126-1435（常量/`_grid_fit` L1181/`frame_geom` L1258/`frame_tex` L1404）+ §1.954 L1436-1496（线宽自标定） | 内框/界行线 vs 源墨迹 |
| 05 | [pagenum_sequence.md](05_pagenum_sequence.md) | 页码序列拟合纠正（分段等差 + 邻页插值） | L1038-1125（`pn_parse` L1053/`pn_text` L1072/`pn_sequence_fix` L1076） | 纠正记录逐条复核 |
| 06 | [derot.md](06_derot.md) | OCR 旋转坐标系页还原（`derot_rows`） | L1614-1719（`_ink_char_cols` L1633/`_lin_fit` L1663/`derot_rows` L1673） | 旋转页列位/字号 vs 源书 |
| 07 | [07_glyph_width_gaps.md](07_glyph_width_gaps.md) | 字模横向压缩（A，q/cm/Q 精确还原，**不用 `\scalebox`**）+ 列内空隙还原（B，`fit_gaps` DP）+ **taskP2 实测文本框夹取**（§1.0a3）+ **taskD 破折号源图墨迹实测竖线**（§1.0a4） | §1.0a L168-199（`XSCALE`/`PAGE_ORIGIN_BP`/`_put_tex` L435）、§1.0a2 L200-217（`BOLD_W`/`_vb`）、§1.0a3 L218-237（`TXTBOX_*`/`_txtbox_clamp_y` L234）、§1.0a4 L303-433（`DASH_*` L303-315 / `_dash_rule_on` L318 / `_dash_runs` L329 / `_dash_ink_seg` L347 / `_dash_rule_tex` L415 / `_fg_origin_shift` L427）、§1.0b L260-405（`char_cells` L156/`fit_gaps` L284）、`col_puts` L3790、落盘 L3887 | 逐字墨迹面积 vs 源书 ≤5%、空隙检出清单、`verify_vert` PASS |
| 08 | [08_punct_vertical_forms.md](08_punct_vertical_forms.md) | 标点竖排形态（括号 → U+FE35…U+FE40 + 墨心回格心）+ OCR 列拆分归位（行首闭括号回上一列） | §1.0c L406-472（`VERT_FORMS`/`VERT_METRICS`/`BR_SIZE`/`_br_put` L459）、§1.0d L473-506（`BR_OPEN_OF`/`fix_split_brackets` L486 + 应用点 L517-528）、§1.9 `note_tex` L1005 | p3 对照图 + 抽查 ≥5 页 + `verify_vert` PASS |
| 09 | [09_calibration.md](09_calibration.md) | **参数自标定 + 纸型无关化**（建排前从源图墨迹 + OCR + 字体文件测出本书参数：列数/字宽压缩/标点/括号/字体绑定组；所有「绝对量」门限改相对页幅/字步进 §8） | §0.5 L41-121、§1.05 L591-620、§1.85 L879-877、§1.954 L1436-1496、§1.955 L1497-1565、§1.96a L1566-1591、§1.956 L3093-3884（字体几何 L3255、源图样本 L3362、探针 L3469）；测试 `test_vert_calib.py` + `test_vert_paper_agnostic.py` | wz6 对账表（`N_COL_FRAME` 精确 12、`XSCALE` 0.863）+ 等价性 21 项 0.0000% + wz7 预检（列数 16/纸型/安全降级）+ `verify_vert` PASS |
| 10 | [10_west_latin_fax.md](10_west_latin_fax.md) | **西文行侧排 / 标题署名行 / 影印页整页贴图**（只 NF 路径）：纯西文行判据 + 逐词/逐片实测落位 + 拉丁 TFM 字体口径 + 破折号单独成片；大字号行按源图墨迹实测渲染；影印页两道独立闸 + 整页贴源图（原始 JPEG 零重编码） | §1.995 L3093-3926（见上一节锚点表）；测试 `test_vert_taskR.py` | p29 西文行逐词对账（Δ沿起 0.00pt）+ 源页 5-28 全部贴图 + 未命中页不误判（分离度 3.8 倍）+ `verify_vert` PASS |
| 11 | [11_short_col_punct_cell.md](11_short_col_punct_cell.md) | **短列检出（又曰：类低覆盖短列）** + **标点占格口径按本书标定** + 引號类小墨修剪：覆盖率分母换成「本行自身墨迹窗」+ 密度/字高三道判据；`PUNCT_CELL` 由源图逐槽反推（wz7=1 占格 / wz6=0 挤格） | §1.0a0 L157、§1.976 L1813-2077、`_trim_marks` L2408、`col_puts` 标点推进、`_calib_punct_cell` L4415；测试 `test_vert_taskS.py` | key54 两个 `又曰：` 落位 Δ≤2pt、空隙 4/5 列与源书同位置同格数、wz7 300 页 PASS（字符量 98.2%→98.4%）、wz6 逐字节零回归 |
| 12 | [12_punct_ink_calib.md](12_punct_ink_calib.md) | **标点墨迹口径标定**（尺寸/格内位置/锚点）：`PUNCT_CELL` 提前到采样之前 + 占格书标点样本按「格内墨心」取（不再靠 DP 预测，否则命中前字笔画碎片）+ 不做尺寸窗筛选（保 `！：；？`）+ NF 的 `PUNCT_INK` 改用探针渲染实测墨心（与 tate 实际字形同源） | §1.956 采样/标定：L4614 `_calib_own_marks`、L4420 `_calib_punct_ink`、L4652/L4723 `_calib_src_page(marks=False)`、L4908 (b0)、L4995 (c2)；消费端 `col_puts` L2833；测试 `test_vert_taskT.py` | 15 页 1717 条双侧实测：标点墨心绝对位置差 −11.25pt→**−0.25pt**、相对前字 −10.00→**+1.00pt**、墨高差 0.00pt；wz7 300 页 PASS（字符量 128683 与基线逐页相同）、wz6 逐字节零回归 |
| 15 | [15_vert_dash_rule.md](15_vert_dash_rule.md) | **竖排破折号 = 源图墨迹实测的一条连续竖线**（taskD / R2）：相邻两个 `—` = 源图同一墨块 -> 一条 rule；线长/线位/线心/线宽全实测；文本层保留原 `—`（3 Tr 不可见）；读不到墨段 -> 兜底每字 1.0 step 并登记 | §1.0a4 L303-433（`DASH_*` L303-315 / `_dash_rule_on` L318 / `_dash_runs` L329 / `_dash_ink_seg` L347 / `_dash_rule_tex` L415 / `_fg_origin_shift` L427）、`_put_tex(invisible=)` L435、`col_puts` L3790（`_rule_h` L3909）；测试 `test_vert_dash_rule.py` | p57 产物 80.00pt=**1.255 step**（源图 1.259）、线位 Δ≤0.25pt、空隙 **0.00pt**；p29 逐字节不变；wz6 md5 `ae9d2f52` 零回归 + `all` 模式逐书实测 1.85-1.98；**506 测试全绿** |

## 特殊行与影印页（§1.995，taskR / taskR2）实现锚点

只 NF 路径调用（有实测版框的书/wz6 不走这一段）—— 「整行西文侧排」「标题/署名行按源图实测渲染」
「影印页整页贴源图」三类版面元素。taskR2 改了其中的西文行口径（拉丁 TFM 字体 + 破折号单独成片 + bp/TeX pt 换算
+ 逐片实测基线），标题署名/影印页判据不变（本轮只复核 + 量化残留）。

| 分部 | 锚点 | 说明 |
|---|---|---|
| §1.995a 西文行 | §1.995 L3093（判据/常量 L3136）、`latin_row` L3154、`_ink_band_at` L3165、`_band_runs4` L3228、`_rot_anchor` L3260、`_latin_groups` L3369、`_align_words_groups` L3384、字体一节 L3431（`_lat_gs` L3438/`_lat_enc` L3451/`_tfm_widths` L3467/`_lat_metrics` L3493）、`_latin_put` L3521、`_lat_pieces` L3540、`_assign_runs` L3554、`_latin_tex` L3587 | taskR2: 拉丁走 ptmr8t（半角/比例 + ASCII 文本层）、破折号单独成片按 run 实测长定字号、源坐标 ×PT2BP、逐片基线 |
| §1.995b 标题署名行 | `_display_put` L3675、`_band_blocked` L3689、`_page_specials` L3697 | 字号/列位/列顶取源图实测；残留 = 竖直落位 +2.0/+8.3pt（见报告 §6 遗留 1） |
| §1.995c 影印页贴图 | `_fax_inkpx` L3807、`fax_decide` L3826、`fax_pages` L3848、`fax_image` L3880、`fax_tex` L3907 | 两道独立闸（每字墨迹面积 ×2.5 且 字数 ×0.5）；命中 70 页（分离度 3.8 倍）；贴图页不重建文本 |

> 详细口径/验收见 [10_west_latin_fax.md](10_west_latin_fax.md) 与 [docs/vert_wz7_layout3_report.md](../../docs/vert_wz7_layout3_report.md)。

> 锚点行号为 **2026-10-16（taskR2 后）当前文件**实测（`grep -n '^# ---------- '` / `grep -n '^def '`）；
> 改 `build_vert.py` 后须同步本表。

## 架构

```
source_pdf/wz6.pdf --(OCR, 官方 API)--> data/wz6/wz6_spotting_{lines,coords}.json  (2x px = 144dpi)
                                          |
                                          v
                     src/pipelines/build_vert.py   (单脚本; 标定趟内联, 无外部驱动)
                       -1) 纸型基准: 页幅 + 门限相对量(页边带/长行/小字) §0.5  [09 §8]
                       0a) 线宽标定: 版框线粗细分界(抽样 8 页)          §1.954 [09 §8.4]
                       0b) 标定趟 A: 版框列数 N_COL_FRAME             §1.955 [09]
                       1) 参数拟合(列高/字号/列距/天头/右缘)          §1
                       1b) 小字判据相对量 + 边注步进比自标定           §1.05/§1.85 [09 §8]
                       2) 书眉/页码 墨迹实测 -> eso-pic \put           §1.8  [03]
                       3) 边注 墨迹实测字列 -> eso-pic \put            §1.9  [03]
                       4) 页码序列拟合纠正                            §1.87 [05]
                       5) 版框线检测 -> eso-pic \rule                 §1.95 [04]
                       6) 页边带并内框缘 / 版心右缘墨迹复测            §1.96a/§1.96 [02][09 §8.3]
                       7) 旋转坐标系页还原(仅该页)                    §1.97 [06]
                       8) 标定趟 B: 源图样本 + 字体探针 -> 参数        §1.956 [09]
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
| 几何标定 | 满行宽 ÷ 满行字数 = 字号；`fit_positional*.py` 两趟校准 | 列长(OCR 盒高) ÷ 字数 = 字号；列距 = 相邻列 x0 差中位；**§1.956 标定趟**（源图墨迹 + 字体探针）[09] |
| 主排版流 | 行流 + `\vspace` 位置还原 | **列流**：每列 `{\fontsize{字号}{列距}...\par}`，`\par` 出列 |
| 边栏元素 | aside 竖排 shortstack | eso-pic `\put` 逐字绝对定位（墨迹实测坐标） |
| 验证脚本 | `verify_geom.py`（pitch/页高/占位） | `verify_vert.py`（页数/字符量/越界） |
| 共享 | OCR 数据格式（lines/coords JSON）、PaddleOCR-VL 数据源 | 同左 |
| 代码共享 | `src/utils/`（tex_escape / geometry / page_numbers / image_blocks） | **无**：`build_vert.py` 是单脚本，不 import `src/utils/`，转义在脚本内联实现（转义契约与横排不同源，横排的 `_esc_chars` 分叉 issue 不覆盖竖排） |

> 竖排脚本**不依赖** `src/calibration/fit_positional*.py`：横排那套两趟校准是「逐字/逐行位置拟合」；
> 竖排的列位由源书几何直接决定（无需拟合），而**参数标定**走竖排自己的 §1.955/§1.956 标定趟 [09]。

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
| 回归测试 | **296 全绿**（unit 277 + invariants 13 + taskN 新增 19） | `src/test/` |
| 纸型无关化（taskN） | 21 项门限 wz6 反算 **0.0000%**；产物 tex 逐字节不变；wz7 预检列数 16/纸型 921.8×1443pt/无版框安全降级 | [docs/vert_paper_agnostic_report.md](../../docs/vert_paper_agnostic_report.md) |

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
| `VERT_BAND_R_FRAC` / `VERT_BAND_L_FRAC` / `VERT_LONG_H_FRAC` / `VERT_SMALL_FS_FRAC` | 0.923904 / 0.083991 / 0.120453 / 0.022083 | 页边带右/左、长行、左边注小字的**页幅比例**（换书微调用；默认 = wz6 换算值） |
| `VERT_INK_*_FRAC` / `VERT_FRAG_OVL_FRAC` / `VERT_NOTE_STEP_MIN_FRAC` | wz6 换算 | 小字窗口/组件窗/碎片容差 ÷ 正文字步进 的比例（§1.05） |
| `VERT_THICK_SAMPLE` / `VERT_THICK_MIN` / `VERT_THICK_MAX` | 8 / 2.4 / 6.5 | 线宽标定抽样页数；显式给线宽阈值则跳过标定 |
| `VERT_NOTE_STEP_RATIO` | 自标定（wz6=0.85） | 边注/正文 步进比上限（显式给值则跳过自标定） |
| `VERT_*_FRAC`（版框几何区间族） | wz6 换算 | 内框高/宽窗、栅格列距窗/跨度窗、列距有效下限等（spec 09 §8.5） |

## 测试点

1. **页数 1:1**（硬）：231 = 231 —— `verify_vert.py` 退出码 0
2. **逐页字符量**：非预期差异页 0（wz6 p74/p231 为预期，见 `verify_vert.py` 的「预期差异页」自动识别机制）
3. **越界**：全书 span/矢量 0 个超出页 rect
4. **免回归**：改动后重跑 `verify_vert.py` + `pytest src/test/unit src/test/invariants`（横排 201 项不受影响）

<!-- taskO(#29) 补充: 无版框书路径锚点(2026-10-15) -->
| 分部 | 内容 | 锚点 |
|---|---|---|
| 09_calibration §9 | 无版框书: 伪版心/伪槽格 + 逐页门限/纸型 + OCR 帧标定 + NF 源侧口径 | §1.06 `L596-640`、§1.975 `L1600-1745`、§1.98 NF 分支 `L1940-1960` |
| 07/08(标定侧) | 无框路径的 `XSCALE` 宽高比口径 `_calib_xscale_w` | §1.956 `L2985-2998` |

## taskP（2026-10-16）新增锚点

| 新增函数/常量 | 行号锚点（`src/pipelines/build_vert.py`） |
|---|---|
| `_nf_lines` / `_nf_delines` / `_nf_ink`（印刷线去除） | 见 `## 1.06b` |
| `_nf_box`（框优先伪版心） | §1.06b 之后 |
| `_nf_hrow_page` / `_nf_hrow_puts`（横排页兜底） | §1.975b |
| `_nf_rescue_rows`（短列补救） | §1.975（`page_puts` 内） |
| `_put_tex(clamp=)` / `_pv_clamp_on`（页内夹取） | §1.0a 之后 |
| `NF_ROW_FRAC` / `NF_POS_PRIOR` / `NF_HROW_*` / `FONT_*_FRAC` / `NF_BOX_*` | §1.975 常量块 |

> 说明：本册锚点以**函数名**给出（行号随改动漂移，函数名稳定）；分部 spec 的旧行号锚点仍按 §4 规则同步。

## taskQ（2026-10-16）新增锚点：标定的方向 / 对齐相位 / 落地口径

| 分部 | 内容 | 锚点（`src/pipelines/build_vert.py`） |
|---|---|---|
| 09_calibration §12 | OCR→源图**逆映射**（方向契约） | `nf_ocr2src` `L1944` |
| 09_calibration §12.2 | 对齐相位择优（映射后行心域 vs 列心域，残差只作同分次序） | `nf_fit_align` `L1906` |
| 09_calibration §12.3 | 标定落地：窗外扩一个列距 + 列带与标定前同口径 | `_nf_after_fix` `L2027`（调用点 `_nf_frame` `L2056`） |
| 09_calibration §12.4 | 命中率统计与逐页明细落盘 | `_nf_fix_stat` / `_nf_rej` `L1935-1942`、主循环后 §2.6 `L4021` |
| 09_calibration §12.5 | 重试口径按渲染字数择优 | 建排主循环 `L3934-3960`、`page_puts_loose(quiet=)` `L2911` |
| 09_calibration §12（开关） | `NF_FIX_INV` / `NF_FIT_ALIGN_POS` / `NF_FIT_LAND` / `NF_FIT_PAD` / `NF_RETRY_BEST`（四个 `*_INV/ALIGN_POS/LAND/RETRY_BEST` 全关 = taskQ 前行为，tex 逐字节相同） | §1.975 常量块 `L1780-1800` |

> taskQ 只改 `nf_fit_align` 的**择优**与标定的**应用/落地**（不改拟合公式、不改任何输出判据），
> 故 02 tate_layout / 03 marginalia / 04 frame_lines 三个分部的锚点无需改写；上表行号以函数名为准
> （`build_vert.py` 的行号随改动漂移）。

## taskU（2026-10-17）新增锚点：引號误识判别 / 引號占格 / 目录页

| 分部 | 内容 | 锚点（`src/pipelines/build_vert.py`） |
|---|---|---|
| 13_vert_quotes_toc §2 | 引號误识判别（形状三判据 + 墨高上限 + 位置闸门 + fit_gaps `_align` 旁路） | §1.997 `_qfx_runbox` / `_qfx_class` / `_qfx_slot_runs` / `nf_fix_quotes`（主循环调用点：`_page_specials` 之后） |
| 13_vert_quotes_toc §2 | 逐候选/修正清单/召回对账落盘 | §2.52（`qfix.json`） |
| 13_vert_quotes_toc §3 | 引號占格口径：文本首/末字是引號时**不剔**列首/列尾小墨 | §1.976 `_trim_marks` ④（常量 `QFIX_QFAM` 定义在其前） |
| 13_vert_quotes_toc §4 | 目录页：补救列带补 `runs` + y 统计窗 = 伪版心 ∪ 该行 OCR y 带 + 适配判据开关 | `_nf_rescue_rows`（`_ynwin`）/ `page_puts` 的 `ok`（`TOC_RESCUE_OK`，默认 0） |
| 13_vert_quotes_toc（开关） | `VERT_QFIX` / `VERT_QFIX_MAX_RATIO` / `_MIN_RATIO` / `_W_RATIO` / `_VPOS` / `_HPOS` / `_POS_LO` / `_POS_HI` / `_DOUBLE` / `_DBG` / `_REPORT` / `VERT_TOC_RESCUE_OK` | §1.997 / §1.98 常量块 |
| 13_vert_quotes_toc §7 | 目录页独立分支（taskCH/CH2）：原始行形态判定 + `_toc_puts` 按 (x 带, y 层) 渲染；目录网格行不得被标题路径认领 | §1.95x `nf_toc_shape` / `_toc_grid_layers` / `_toc_puts`；`_page_specials` 的 `g['toc']` 护栏；`page_puts` 开头 `g['toc']` 分支 |

> taskU 的引號判别只走**无版框伪槽格页**（`m['g']['virtual']`），有版框书（wz6）不在影响面内
> （实测 `vert.tex` md5 逐字节相同）；`_trim_marks` ④ 同理（该函数只被 `page_puts` 调用）。
> 目录页的补救路径改动默认关，开启会丢字（见 13 §4）。行号以函数名为准。

## taskD（2026-10-22）新增锚点：竖排破折号 = 源图墨迹实测的一条连续竖线（R2）

| 分部 | 内容 | 锚点（`src/pipelines/build_vert.py`，当前行号） |
|---|---|---|
| 15_vert_dash_rule §2 | 破折号常量与开关判据（`nf` 默认只无版框页 / `all` / `0`） | `DASH_CHARS` L303、`DASH_RULE_W_RAW` L304、`DASH_RULE_W` L305、`DASH_RULE_MODE` L306、比值常量 L309-315、`_dash_rule_on` L318 |
| 15_vert_dash_rule §2 | 相邻破折号成组（文本相邻 + 格号连续） | `_dash_runs` L329 |
| 15_vert_dash_rule §3 | 源图读墨：列心±0.35step × 格区±0.5step 找最长竖直墨段 -> y0/y1/线心/线宽 | `_dash_ink_seg` L347 |
| 15_vert_dash_rule §4 | 一条 rule（高度=实测 y1−y0、线心=实测 xc、线宽=DASH_RULE_W×F 或 src） | `_dash_rule_tex` L415 |
| 15_vert_dash_rule §5 | FG 原点偏移修正 `page_h×(1−1/PT2BP)` | `_fg_origin_shift` L427 |
| 15_vert_dash_rule §4 | 出字口：原字 `3 Tr` 不可见（`invisible=True`）/ 兜底 `rule_h` | `_put_tex` L435 |
| 15_vert_dash_rule §6 | 逐组实测 + 兜底：`col_puts` 预扫格号 -> `_dash_runs` -> `_dash_ink_seg` -> `_dash_rule_tex` | `col_puts` L3790（`_rule_h` L3909） |
| 15_vert_dash_rule §1 | 旧 U+FE31 方案已删除（`VERT_DASH_MAP` / `VERT_VERT_DASH`）；`_esc_ch` 恢复纯转义 | `_esc_ch` L3723 |
| 15_vert_dash_rule 验收 | 测量脚本（不进库） | `tmp_vert/taskD/verify_r2.py` |

> taskD 的矢量线只在 `_dash_rule_on(m)` 为真时启用；默认 `nf` = 仅 `m['g']['virtual']` 页，
> 有版框书（wz6）默认输出不受影响（`vert.tex` md5 逐字节相同）；`VERT_DASH_RULE=all` 在 wz6 上
> 按 wz6 自己的源图墨迹实测（线长/step 1.85-1.98，证明无本书绑定）。
> 西文侧排走 `_latin_put`，不经过 `_put_tex`；`_esc_ch` 也不再改字形。
