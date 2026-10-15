# 09 参数自标定（建排前从源图 + OCR 数据 + 字体文件自动测出本书参数）

**状态**：implemented（2026-10-15, taskM）
**实现锚点**：`src/pipelines/build_vert.py` §1.955 `L1080-1143`（列数）+ §1.956 `L2023-2696`（源图/探针/合并/对账/落盘）
**测试**：`src/test/unit/test_vert_calib.py`（28 项，CI 可跑；不依赖源图/网络/uLaTeX）
**报告**：`docs/vert_calib_report.md`（含 wz6 对账表、产物验证、剩余人工依赖清单）

---

## 1. 目标与背景

审计（`docs/vert_calib_task.md` §审计表）发现：竖排管线的**机制**大多通用（列位/列距/版框/页码序列/derot
全部取自源图实测），但有一批常数是**在 wz6 上实测后硬编码的** —— 换一本书必然失准。最危险的是
`N_COL_FRAME=12`：它被用来反推版框内框左右缘（`frame_geom` L1015-1018），列数错 → 内框错 → **全页列位错**。

本 spec 定义「**标定趟**」：建排前跑一次，从

- **源图墨迹**（source PDF 2x 灰度 < 150 的像素）
- **OCR 数据**（lines/coords JSON，用于定位/配列/取字）
- **字体文件**（`VERT_FONT` 指向的 `.ttc`/`.otf`，fontTools 读轮廓几何）

自动测出下列参数，并把结果打印 + 落盘（可缓存复用）。

## 2. 输入 / 输出 / 约束

| 项 | 内容 |
|---|---|
| 输入 | argv[4] `SRC`（源 PDF，可缺省）；OCR lines/coords；`VERT_FONT`（默认 NotoSerifCJK-Regular.ttc） |
| 输出 | ①stdout 对账表（每次构建打印）②`$VERT_TMP/vert_calib.json`（或 `VERT_CALIB_REPORT`）③生效的模块级常量 |
| 抽样 | `CALIB_N_PAGE=16`（`VERT_CALIB_PAGES`）页均布 + 稀有括号定向补抽 ≤8 页（`VERT_CALIB_RARE_PAGES`） |
| 耗时 | **2.3s**（wz6 全书实测；抽样页的 `page_metrics` 会进缓存被渲染复用，故整构建只多约 0.8s：16.9s → 17.7s） |
| 可复现 | 标定结果与产物**与 PYTHONHASHSEED 无关**（逐页像素全等实测）；`_metrics_cache` 在标定后清空 |
| env 优先级 | **显式 env > 标定值 > 兜底值**。设了 env 就完全不采纳标定值（`_calib_apply`） |

## 3. 标定趟流程

```
§1.955 趟 A(必须早于 §1.96 右缘复测)             §1.956 趟 B(晚于 preamble 构造, 早于渲染)
  抽样页 frame_geom                                (a) kpsewhich 解析 VERT_FONT -> fontTools 读轮廓
   ├ ①内框宽÷列距(取整)                             │   -> VERT_METRICS(14 竖排形态) / PUNCT_INK(7 标点)
   ├ ②界行线条数-1                                  │   -> NOTE_INK_MAX(全书用字的轮廓墨高上界)
   └ ③实测最外两条细线跨距÷列距                      (b) 源图侧: 抽样页 -> 槽/行配对 -> 逐字墨迹样本
  取「①=③ 一致页」的众数(两条独立口径互证)          (c) 探针: 用**同一 preamble** 逐字 \put 编译 2 页 PDF
  无一致页 -> ②众数; 都不可测 -> 兜底 12            (d) 组合 -> 各参数(见 §4)
       -> N_COL_FRAME                              (e) VERT_CALIB_CACHE 时可跳过 (b)-(d)
                                                   (f) 清 _metrics_cache -> 应用生效值 -> 对账表 -> 落盘
```

**为什么渲染侧要真编译探针而不只用 fontTools**：「字号 ↔ 墨高」的换算必须落在**像素口径**上
（源书墨高来自扫描二值化，渲染墨高同样来自二值化）。轮廓几何口径系统性偏高：Noto Serif CJK TC
轮廓墨高 0.913em，而 2x 灰度 <150 实测 0.872em（-4.5%）—— 用轮廓值会让全书字号整体偏小。
fontTools 只用于**纯几何量**（墨心位置等，与口径无关），并在日志里与探针结果交叉校验。

## 4. 各参数的口径（公式与实现一一对应）

样本记号：`src_body` = 逐字 `(墨高px, 墨宽px, 墨面积px²)`；`src_small` = 小字 `(字, 类别, 高/正文高中位,
宽/正文高中位, d_top, d_cy, d_cx)`；`probe` = 渲染 `(墨宽em, 墨高em, 墨心x_em, 墨心y_em, 墨面积em², 墨顶距基准线em)`。

| 参数 | 口径（公式） | 源侧测量 | 渲染侧测量 | 兜底值 / env | 实现 |
|---|---|---|---|---|---|
| `N_COL_FRAME` | 内框宽 ÷ 列距 取整（②③ 交叉校验） | `frame_geom` 的 `thin`/`pitch`/`in_l`/`in_r` | — | 12 / `VERT_NCOL_FRAME` | `_calib_ncol_page`/`_calib_ncol_pick` L1093-1124 |
| `XSCALE` | **墨面积/墨高²**（源中位 ÷ 渲染中位） | 逐字 `a/h²`（单体字 run） | 探针逐字 `a_em/h_em²` | 0.87 / `VERT_XSCALE` | `_calib_xscale` L2095 |
| `PUNCT_SIZE` | (源标点墨高/正文字高) × (渲染正文字高em ÷ 渲染标点墨高em) | 挤格标点连通域墨高 / 本槽正文墨高中位 | 探针 `，。、；：？！` 墨高 em 中位 | 0.62 / `VERT_PUNCT_SIZE` | `_calib_punct_size` L2105 |
| `PUNCT_DY` | 源标点**墨心**相对**前字格顶**的偏移 ÷ 步进 | 同上一批样本 | — | 0.85 / `VERT_PUNCT_DY` | `_calib_punct_pos` L2115 |
| `GAP_HANG` | 源标点**墨顶**相对前字格顶的偏移 ÷ 步进（同一次统计，与 PUNCT_DY 同源） | 同上 | — | 0.85 / `VERT_GAP_HANG` | 同上 |
| `PUNCT_DX` | 源标点**墨心**相对**槽左缘**的偏移 ÷ 格距 | 同上 | — | 0.81 / `VERT_PUNCT_DX` | 同上 |
| `BR_SIZE_DEF` | 各括号族「宽高同时最接近」缩放的中位 | 各族括号（连通域、形态+位置质检）墨高比/墨宽比 | 探针竖排形态墨高/墨宽 em | 0.66 / `VERT_BR_SIZE` | `_calib_br_forms` L2124 |
| `BR_SIZE[字形]` | `sqrt(s_h × s_w)`；`s_h` 只对高、`s_w` 对宽（含 `XSCALE` 还原） | 同上（按族合并开/闭形） | 同上 | 兜底表 / `VERT_BR_SIZE_MAP` | 同上 |
| `INK_RATIO` | 探针正文语料「墨高 ÷ 字号」中位（像素口径） | — | 探针 24 个高频正文汉字 | 0.88 / `VERT_INK_RATIO` | `_calib_probe` L2385 + (d) |
| `INK_ASC` | 探针正文语料「墨顶距基准线 ÷ 字号」中位 | — | 同上 | 0.94 / `VERT_INK_ASC` | 同上 |
| `NOTE_INK_RATIO` | 探针注文语料同 INK_RATIO（样本不足回落正文语料） | 注行文本取字频 | 探针 ≤12 个小字 | 0.88 / `VERT_NOTE_INK_RATIO` | 同上 |
| `NOTE_INK_MAX` | **轮廓口径**下本书全部用字的墨高最大值（保守：轮廓 ≥ 像素实测约 6%） | 全书用字集合 | fontTools `BoundsPen` | 0.94 / `VERT_NOTE_INK_MAX` | `_calib_font_geom(maxh_chars=…)` L2171 |
| `VERT_METRICS` | 竖排码位在 em 盒内的 `(墨宽, 墨高, 墨心x, 墨心y)` | — | fontTools 轮廓 bbox ÷ upem（.ttc 取名字含 `TC` 的面） | 内置 14 项表 | `_calib_font_geom` L2171 + (a) |
| `PUNCT_INK` | 标点墨心相对 `\put` 锚点的偏移（em，y 向上为正） | — | fontTools 同上 | 内置 7 项表 | 同上 |

**样本口径细节**

- 源侧窗口一律与 §1.98 同源：槽窗口 = 网格槽 **内缩 3.5pt**（槽两侧就是界行线，不内缩会把线算进字墨迹）；
  阈值 2x 灰度 < 150；y 区间取本槽实测顶/底外扩 5pt。
- **单体字**判据：run 高 ∈ [0.8, 1.25] × 本槽 run 高中位（并字 ≈2×、标点 ≈0.2× 都被排除）。
- **小字（标点/括号）**用**二维连通域**而非槽的 y 投影：挤格标点的 y 区间常落在前字的墨迹区间内
  （实测 p15「問：」：标点墨迹 x552-554/y357-364 被「問」的 y 投影吞掉）→ 投影法永远配不上标点。
  形态分类：`w ≥ 1.8h` = 扁长条（括号）/ 否则紧凑块（标点）；两者只与同类预测配对。
- **配对**：文本侧小字（`char_cells` 给格号）→ 预测墨顶/墨心 → 与实测标记做**单调 DP 配对**
  （代价 `|Δ|/tol`，tol = 0.5 步进，跳过代价 1.0）—— 宁缺勿错配。
- **估计量**：括号族用 **p75**（样本 ≥ 4）或 **max**（样本 1-3）；理由：漏检只会把标记测**小**
  （弧被阈值切断成两段、淡墨段掉出阈值），不会测大（上限另有 `h ≤ 0.62×中位` / `w ≤ 0.9×中位` 挡着）。
  实测「（」的样本双峰（0.24 与 0.13 各半），中位落在两峰之间会偏小。
- **稀有括号定向补抽**：均布抽样凑不够样本的族（如 wz6 的 【】〔〕），从 OCR 文本找出含该类括号的页
  **按族分别**补抽（按族名排序保证确定性），只收小字样本、**不收正文样本**（补抽页多为註釋/索引页，
  不代表全书正文用字分布，混进去会把 XSCALE 带偏：实测 0.868 → 0.927）。

## 5. 失败与兜底（不假装自动）

| 情形 | 行为 |
|---|---|
| 无源 PDF（3 参数调试调用） | 只做 fontTools 那部分；源图侧全部回落兜底值，日志明示 |
| `VERT_FONT` 找不到文件（kpsewhich 未命中） | `VERT_METRICS`/`PUNCT_INK` 用兜底表；其余参数不受影响（它们与字体解耦） |
| 字体解析失败（无 cmap/非 ttf-otf） | 同上，日志打印异常类型 |
| 某括号族样本 < 1 | 该族回落 `BR_SIZE_DEF`（本次实测的总中位），日志逐族列出 → 可用 `VERT_BR_SIZE_MAP` 手工覆盖 |
| 版框列数三条估计都不可用 | 回落 12（兜底），日志打印各页估计值 |
| `VERT_CALIB_CACHE` 读取失败 | 打印原因并重新标定 |

**落盘/缓存**

- 每次构建写 `$VERT_TMP/vert_calib.json`（`VERT_CALIB_REPORT` 可改路径）：含抽样页数、字体解析结果、
  探针说明、`n_col_frame`、`br_size`、`values`（标定值）、`fallback`、`effective`。
- `VERT_CALIB_CACHE=<json>`：跳过源图侧与探针（用于同书反复调试；跨书复用不在契约内）。
- `VERT_CALIB_ONLY=1`：只标定不建排（打印对账表后退出），供排障/新书预检。
- `VERT_CALIB_DEBUG=1/2`：打印逐样本明细 / 逐槽 run 与文本（排障用）。

## 6. 验收

1. **对账表**（每次构建打印）：标定值 vs 兜底值 vs 生效值 + 相对差。wz6 实测见报告 §3：
   `N_COL_FRAME` 12（精确）、`XSCALE` 0.863（-0.8%）、`PUNCT_SIZE` 0.658（+6.1%）、
   `PUNCT_DX/DY` -1.4%/-1.2%、`INK_RATIO` 0.872、`INK_ASC` 0.945、`NOTE_INK_MAX` 0.943。
   `BR_SIZE_DEF` 0.763（+15.6%）与 `GAP_HANG` 0.742（-12.7%）为**已知口径差**，报告 §3.2/§3.3 给了归因。
2. **产物不回退**：`verify_vert` PASS（231:1 / 字符量 68412 = 与标定前逐字相同 / span 0 / 矢量 0）；
   内框区墨迹覆盖率 标定后/标定前 = **1.009**（不降），标定后/源书 = 0.960（标定前 0.951）。
3. **测试**：`src/test/unit/test_vert_calib.py` 28 项 + 既有 249 项全绿（277）。
4. **日志可见**：标定趟的每个阶段与最终对账表都在 stdout（见报告 §6 的证据文件）。

## 7. 与既有 spec 的关系

- `01_engine.md`：探针渲染复用主 preamble，字体绑定常量随 `VERT_FONT` 自动重标。
- `02_tate_layout.md`：`N_COL_FRAME` 是槽格（`page_metrics` 的 `n`）与 `_grid_from_bands` 的分母，标定后这些
  结构自动适配别的书。
- `04_frame_lines.md`：§1.955 只读 `frame_geom` 的输出（`thin`/`pitch`），不改版框检测本身。
- `07_glyph_width_gaps.md`：`XSCALE` 与 `GAP_HANG` 的口径在这里定义（面积比 / 墨顶偏移）。
- `08_punct_vertical_forms.md`：`BR_SIZE`/`BR_SIZE_DEF`/`VERT_METRICS`/`PUNCT_INK` 的来源从「taskK 实测硬编码」
  改为「标定 + 兜底表」；`PUNCT_SIZE/DX/DY` 同理。

> 锚点行号为 **2026-10-15** 实测（`grep -n '^# ---------- '`）；改 `build_vert.py` 后须同步 `README.md` 锚点表。
