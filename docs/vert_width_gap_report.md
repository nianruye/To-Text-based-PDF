# 竖排字宽压缩收尾报告（taskJ2）：`\scalebox` 泄漏修复 + 列内空隙（空格）还原

> 项目：/opt/test　样本：wz6《毛泽东选集》第二卷（繁体竖排扫描书，231 页）
> 关联 spec：[spec/vertical/07_glyph_width_gaps.md](../spec/vertical/07_glyph_width_gaps.md)（A+B 契约与锚点）、
> [spec/vertical/02_tate_layout.md](../spec/vertical/02_tate_layout.md)（列位/列顶基准）
> 产物：`output/wz6/wz6_vert_full.pdf`（231 页，留档 `output/wz6/wz6_vert_full.pdf.bak_taskJ2` = 修前）
> 附件：`data/wz6/wz6_gaps_detected.json`（空隙检出清单）、`tmp_vert/taskJ2/`（探针 + 对照图）

## 0. 摘要

| 项 | 修前（taskJ） | 修后（taskJ2） |
|---|---|---|
| `verify_vert` 退出码 | **FAIL**（矢量图形越界 4 个，p157，最深 0.82pt） | **PASS**（页数 231:1 / 字符量 97.2% / span 0 / **矢量 0** / 页幅 0.00%） |
| 字模横向压缩 | `\scalebox{K}[1]`（dvipdfmx 逆矩阵舍入泄漏 CTM） | `\special{pdf:literal direct q K 0 0 1 0 0 cm ... Q}`（图形状态栈精确还原，零残差） |
| 逐字墨迹面积（thr150） | p10 203.3 / p14 205.2 / p100 197.3 | p10 **202.8** / p14 **205.1** / p100 **197.2**（源书 205.6 / 202.8 / 192.1 → −1.4% / +1.1% / +2.7%） |
| 列内空隙还原 | 代码在但未全书跑 | 全书 **75 处 / 90 格 / 58 页**；p14/p15「問：/答：」4 处全中（对照图） |
| 测试 | 222 项（= 基线 209 + taskJ 新 13） | **225 项全绿**（unit + invariants；本次新增 3 项泄漏回归锁） |

一句话：**压缩本身保留（覆盖率不变），把「怎么压」从 `\scalebox` 换成自写的 `q/cm/Q`，泄漏根因消除；
B 项（列内空格）从源图墨迹 DP 反推并全书落地。**

---

## 1. A 项：`\scalebox` 泄漏 —— 根因、证据、修法

### 1.1 症状（任务书给的回归）

```
越界: span 0 个 / 矢量图形 4 个（容忍 0.5pt；涉及 1 页）
  [越界] p157 span 0 draw 4 最深 0.82pt
         draw bbox=[-0.8, 284.7, 572.6, 284.7]      <- 上/下外框横线左端越出页左缘 0.8pt
```

全书 231 页只有 p157 越界 —— 因为它的界行线实测左端恰好 = 0.0pt（其余页有余量），
且它是字数最多的页之一（累积量最大）。**这是"暴露"而不是"来源"**：泄漏本身页页都有。

### 1.2 根因（读驱动宏 + 内容流实证）

`graphicx` 在 dvipdfmx 驱动里（`/usr/share/texlive/texmf-dist/tex/latex/graphics-def/dvipdfmx.def` L240-255）：

```tex
\def\Gscale@start{\special{pdf:btrans}\special{x:scale \Gscale@x\GPT@space\Gscale@y}}
\def\Gscale@end{\special{pdf:etrans}}
```

dvipdfmx 把这一对展开成「平移到锚点 · 缩放 · 平移回」，`etrans` 时用**数值逆矩阵**还原，
而逆矩阵只印 **6 位有效数字**。实测内容流（探针 `tmp_vert/taskJ2/probe_stream.py`，n=2 字）：

```
q 1 0 0 1 72 1173.33 cm
  ... 1 0 0 1 7.701 -270.814 cm .87 0 0 1 0 0 cm 1 0 0 1 -7.701 270.814 cm BT /F1 32.9767 Tf 7.701 -270.814 Td[<3387>]TJ ET
      1 0 0 1 7.701 -270.814 cm 1.14943 0 0 1 0 0 cm 1 0 0 1 -7.701 270.814 cm      <- 1/0.87 = 1.149425… 印成 1.14943
```

于是**每字**在 CTM 里留下残差

```
ρ = 0.87 × 1.14943 = 1.0000041        （x 方向，绕该字锚点）
```

N 字累积 = ρ^N。实测标定（`probe_big.py`，N=2000 字 + 页尾两条规则线，put 0..574pt）：

| 模式 | 页尾规则线实际区间（期望 0.00..571.86bp） |
|---|---|
| 不压缩（plain） | 0.00..571.86 ✓ |
| `\scalebox`（现状） | **−2.34..574.29**（左右都越出页缘） |
| 本报告新写法 | 0.00..571.86 ✓（与 plain 逐值相同） |

p157 的同一对照（`/tmp/tj2_p157_*.pdf`，全书同参构建）：`XSCALE=1.0` → `[0.00..571.86]`；
`XSCALE=0.87`（scalebox）→ `[−0.82..572.58]`；新写法 → `[0.00..571.86]`（连 11 条界行线位置都逐值相同）。
对该页所有竖线做仿射拟合得泄漏变换 **x' = 1.002689·x − 0.81**（y 不变，与 yscale=1 一致）。

### 1.3 修法：自写 PDF 算子 `q`/`cm`/`Q`（精确还原）

```tex
\put(x,y){\special{pdf:literal direct q 0.87 0 0 1 0 0 cm}<字号+字>\special{pdf:literal direct Q}}
```

- `pdf:literal direct …`（等价 `pdf:code`）按 dvipdfmx 手册**原样插入算子、不附加任何 q/cm/Q**
  （dvipdfmx-special.pdf §"pdf:literal direct"；`xfakebold.sty` 同源用法）。
- **`Q` 是图形状态栈的精确还原（不是数值逆）** → 残差恒 0，与字数无关（N=2000 实测）。
- 缩放中心 = dvipdfmx 的 DVI 原点（1in = 72bp，页面坐标 x=72）→ 写入坐标需反解：
  `目标页坐标 X → \put 值 = (X − 72)/K + 72`（K=1 时退化为 X）。标定见 `probe_literal.py`/`probe_anchor.py`：
  目标 X=52.697 应写 49.813，实测墨迹左缘 52.69 ✓；三态（plain / 新 / 旧 scalebox）**墨迹中心逐字对照**：
  新实现与旧 `\scalebox` 的墨迹位置、墨宽**完全相同**（K=0.87 时宽 28.69 vs plain 32.98）。
- 调用方语义不变：`_put_tex` 传入的 x = 缩放后字盒**左缘**的目标页坐标（`col_puts` 里 `x_put = xc − K·F/2`），
  与 `\scalebox` 的左缘锚点同构 → 全部列位/标点挤格/字号保护的既有成果不动。
- `\usepackage{graphicx}` 随之下线（全文已无 `\scalebox`/`\resizebox`/`\rotatebox`/`\includegraphics`）。

**为什么不用其它方案**（都试过/算过）：
`\resizebox` 走同一个 `\Gscale@start/@end`（同泄漏）；`\pdfxform` 是 pdfTeX 专有（uplatex 无）；
选 K 使 1/K 落在 6 位内（仅 K=0.8 可行，覆盖率会掉 8%，超出 ±2% 约束）；
换窄体字模（`fc-list` 实测系统只有 Noto Sans/Serif CJK 全角方体，无长体/窄体备选）。

### 1.4 单元测试锁定（`src/test/unit/test_vert_width_gap.py`，新增 3 项 + 改 3 项）

- `test_put_tex_scales_horizontally`：断言新格式（q/cm/Q）与反解后的 put x。
- `test_put_tex_uses_no_graphicx_scalebox`：**回归锁** —— 输出中绝不出现
  `scalebox`/`btrans`/`etrans`/`x:scale`/`resizebox`。
- `test_put_tex_x_compensation_roundtrip` / `test_put_tex_k_printed_matches_inversion`：
  put x 反解回页坐标 = 传入目标（±0.06pt 打印精度）。

---

## 2. B 项：列内空隙（源书空一格）还原

### 2.1 检出方法（DP，比任务书单点阈值更稳）

任务书判据「列内相邻字墨迹间距 > 1.3× 该列中位步进」在源书上**不可直接用**（见 2.4 复核）：
源书字距紧、相邻字常相碰并成一个 run，挤格标点的墨又落在格缝上 —— 单看间距/顶差两类假象都会骗过。
实现（`build_vert.py` §1.0b `fit_gaps`，纯函数）用**结构对齐 DP**：

- 状态 `(字符下标, run 下标, 已插格数)`；字符的**预测墨顶** = `槽墨顶 + (格号 + 已插格 + 0.85×挤格?) × 步进`；
- 转移：匹配 run（代价 = 顶差/步进的平方）、并进上一 run（粘连）、跳字（OCR 多字，贵）、
  挤格标点不参与匹配（源书冒号墨心与本渲染位置不一致，参与会把整列带偏）、跳过 run、**插一格**；
- 收口：末字格号 vs「槽实测墨迹跨度折合格数」（必须减墨高，否则每列都误判一处）；
- 逐格校验：空格格内不得有 run 顶（把「排版空格」与「OCR 漏字」分开，后者不补）；
- 插入点若落在挤格标点之前，后移到标点之后（源书标点紧跟上字字脚）；
- 渲染：该格**只推进不落墨**（`col_puts` 的 `gap_at`），并计入排版格数（步进按真实格数均分）。

### 2.2 全书结果（`data/wz6/wz6_gaps_detected.json`）

```
n_gap 75 / n_cell 90 / npage 58 / vscale 0.87
每页条目数：1 条/页 ×45、2 条 ×9、3 条 ×4（余为同列多格）
插入格数分布：extra=1 ×62、extra=2 ×12、extra=4 ×1
「問/答」开头列：9 处
```

样例（首 4 条）：

| 页 | 列 x0 | 步进 | 插入 | 列文本头 |
|---|---|---|---|---|
| 14 | 184.5 | 31.00 | 第 2 字前 1 格 | 問：假如戰爭拖得很長日本沒有完全戰敗… |
| 14 | 97.5 | 31.25 | 第 2 字前 1 格 | 答：不能中國共產黨和全國人民一樣… |
| 15 | 541.2 | 31.00 | 第 2 字前 1 格 | 問：照你的意見，這次解放戰爭… |
| 15 | 498.0 | 31.00 | 第 2 字前 1 格 | 答：我們的戰略方針，應該是使用我們的主力… |

### 2.3 验收样例（p14/p15 問：/答： 后应有空格）

对照图（上=源书扫描、下=本产物，同一页区裁剪）：
`tmp_vert/taskJ2/img/gapcmp_p14_x184.png`、`gapcmp_p14_x98.png`、`gapcmp_p15_x541.png`、`gapcmp_p15_x498.png`
—— 源书「問：」后一格空白，产物同样留出该格，其后「假如戰爭拖…」逐字对齐 ✓（4/4）。

### 2.4 独立复核：做了什么、结果如何、局限在哪（如实记录）

**核不了的部分**：用三种**不复用 DP** 的独立口径在源图上重测，都因源书本身的性质失效：

1. 「相邻墨迹 run 间距 > 1.3× 中位步进」：源书字距紧 → 正常相邻字的间距 ≈ 0，
   有空格处间距 ≈ 0.7~1.0 步进（**小于** 1.3×步进）→ 判据在源侧根本触发不了（0 命中）。
2. 「run 顶差 > 1.3× 中位步进」：粘连长 run 的顶差也 ≈ 2 步进 → 与真空格同形（正是 DP 要解决的分辨问题）。
3. 「逐格墨迹占比 < 5%」：源书相邻字墨迹**越格相碰**，把格栅平移半个格后每格占比都是 0.12~0.24
   （连已视觉确认的 p14/p15 空白格也一样）→ 单格阈值无法在源侧分辨（格栅与墨迹的相位无法独立定准）。

**能核的部分**（对齐式复核 `tmp_vert/taskJ2/verify_gaps.py`：产物侧找我们留的空白格 →
与源图列剖面互相关求纵向位移 → 量源图同位置墨迹）：

- 产物侧：插格处逐格墨迹占比 0.03~0.07（近空白）✓（`/tmp/tj2_cells.py` 实测）。
- 源侧：约 **1/4 条目**对齐后墨迹占比 < 0.02（源书那格确实空着）；
  约 **1/3 条目**源书那格有细小墨迹（0.10~0.28）。抽 3 页看图（`tmp_vert/taskJ2/align/al_p31_x240_i20.png` 等）：
  源书该格填的是**未识别的小标记**（夹注/校勘号一类）—— 格数上是"多一格"，内容上是"少一个标记"。

因此对全书的准确表述是：**检出 = "源书该列比 OCR 文本多占一格"**，其中
①真排版空格（問：/答： 这类，样例已确认）→ 我们补空格，与源书一致；
②源书那格是未识别的小标记 → 我们留白：**格数/对齐正确，内容层少一个标记**（该标记属既有链路
`src/tools/patch_vert_symbols.py` 的符号集之外的小图形标记，非本次引入）。

### 2.5 与既有成果的关系

- 补格只改「本列格数与推进」，不动列位/列顶/列底（框驱动基准）、不动标点挤格、不动字号保护；
- `verify_vert` 复测：页数 231:1、字符量 68412/70373 = 97.2%（与修前逐值相同）、越界 0；
- 空隙检出对**双行小字子列不适用**（同槽双列的列几何不可靠），已在 `page_puts` 显式不传 `runs`。

---

## 3. 验收逐条对照

| # | 验收项（任务书） | 结果 |
|---|---|---|
| 1 | `verify_vert` PASS（页数 231:1 / 字符量 / span 越界 0 / **矢量越界 0**） | ✅ 退出码 0；越界 span 0 / 矢量 0；见 §4 复现命令 |
| 2 | 覆盖率保持（p10/p14 ≤ +8%、p100 ≤ +11%，不回退到修前水平） | ✅ 逐字墨迹面积（thr150，标定口径）p10 −1.4% / p14 +1.1% / p100 +2.7%（源书），与修前差 ≤0.5（0.25%）；内框区墨迹占比修前 0.1349/0.1126/0.1135 → 修后 0.1353/0.1130/0.1129（差 ≤0.0006） |
| 3 | B 项：p14/p15 空格还原对照图 + 全书统计落盘 | ✅ 4 处全中（`tmp_vert/taskJ2/img/gapcmp_p1*.png`）；`data/wz6/wz6_gaps_detected.json`（75 处/90 格/58 页） |
| 4 | 209 测试全绿 | ✅ **225 passed**（含 taskJ 13 项 + 本次新增 3 项；invariants 13 全绿） |
| 5 | 报告 `docs/vert_width_gap_report.md` | ✅ 本文件 |

**与任务书数字口径的说明**：任务书引用的「p10 +17.4% → +5.7%」出自另一套覆盖率口径
（源侧阈值/区域定义不同：`measure_ink.py` 有 `page_cov`/`frame_cov`（内框区）/`col_cov_med`（列级）三种，
再把源侧阈值取 110、产物侧 150 —— 我按这几种口径都算了一遍，`+5.7%` 都不能被复现，
故本报告一律给出**可复现的同口径对照**（同一脚本 + 同一阈值 + 修前/修后/源书三列）：

| 口径（thr=150） | p10 源/修前/修后 | p14 | p100 |
|---|---|---|---|
| 逐字墨迹面积（标定口径，spec §5） | 205.6 / 203.3 / **202.8** | 202.8 / 205.2 / **205.1** | 192.1 / 197.3 / **197.2** |
| 内框区墨迹占比 `frame_cov` | 0.1423 / 0.1349 / **0.1353** | 0.1218 / 0.1126 / **0.1130** | 0.1199 / 0.1135 / **0.1129** |
| 列级覆盖中位 `col_cov_med` | 0.2336 / 0.2017 / **0.2009** | 0.2308 / 0.1854 / **0.1854** | 0.2481 / 0.2059 / **0.2058** |

（"修前"= `output/wz6/wz6_vert_full.pdf.bak_taskJ2`，即 taskJ 压缩后、本次泄漏修复前；
再往前 taskH 未压缩版 p10 `frame_cov` = 0.1513 —— 即压缩把该口径从 +6.3% 拉到 −5.2%，
逐字墨迹面积口径则正好落在 −1.4%；两个口径的量级差来自列数/列位与内框面积，不是 ink 量。）
**未为了对齐某个百分比去调参**：K 仍是覆盖率标定值 0.87。

---

## 4. 复现命令

```bash
cd /opt/test
# 全书重建（含空隙检测落盘）
VERT_GAP_REPORT=data/wz6/wz6_gaps_detected.json \
  /usr/bin/python3 src/pipelines/build_vert.py \
    data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json \
    output/wz6/wz6_vert_full.pdf source_pdf/wz6.pdf

# 门禁
/usr/bin/python3 src/test/verify_vert.py output/wz6/wz6_vert_full.pdf \
    data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json --src-pdf source_pdf/wz6.pdf
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q

# 覆盖率（同一脚本三态对照）
/usr/bin/python3 tmp_vert/taskJ/measure_ink.py cov output/wz6/wz6_vert_full.pdf 10,14,100 150
/usr/bin/python3 tmp_vert/taskJ/measure_ink.py cov output/wz6/wz6_vert_full.pdf.bak_taskJ2 10,14,100 150

# 空隙对照图 / 独立复核
/usr/bin/python3 tmp_vert/taskJ2/make_gap_cmp.py data/wz6/wz6_gaps_detected.json \
    output/wz6/wz6_vert_full.pdf source_pdf/wz6.pdf tmp_vert/taskJ2/img 14,15
/usr/bin/python3 tmp_vert/taskJ2/gap_align_cmp.py data/wz6/wz6_gaps_detected.json \
    output/wz6/wz6_vert_full.pdf source_pdf/wz6.pdf tmp_vert/taskJ2/align 31,41,107
/usr/bin/python3 tmp_vert/taskJ2/verify_gaps.py data/wz6/wz6_gaps_detected.json \
    output/wz6/wz6_vert_full.pdf source_pdf/wz6.pdf

# 泄漏探针
/usr/bin/python3 tmp_vert/taskJ2/probe_stream.py     # 内容流: 1.14943 舍入
/usr/bin/python3 tmp_vert/taskJ2/probe_big.py        # N=2000: scalebox -2.34..574.29 vs literal 0.00..571.86
/usr/bin/python3 tmp_vert/taskJ2/probe_anchor.py     # 三态墨迹锚点标定
```

修前产物留档：`output/wz6/wz6_vert_full.pdf.bak_taskJ2`（.bak_taskJ2 后缀 = 本次数据变更前备份）。

---

## 5. 遗留与选项

1. **空隙格内含未识别小标记**（§2.4）：布局正确、内容少一个标记。选项：
   (a) 把该类小标记纳入 `src/tools/patch_vert_symbols.py` 的补全（需先扩符号集与 OCR 对齐规则）；
   (b) 在补空格处按源图墨迹位置画小标记（越出「只排版不改内容」的边界，需用户确认）。
2. **边注/书眉/页码仍未横向压缩**（沿 taskJ 遗留）：它们字号由墨高实测反推、`\put` 绝对定位，
   本轮未动以免回归；若要一致，直接复用 `_put_tex`（同一 K）即可 —— 但会动全书边缘小字的墨迹口径，需重跑基线。
3. **字模仍非完全同款**：K=0.87 是「逐字墨迹面积」口径的解；源书字模本身更窄（宽高比 0.67 vs 我们 0.80），
   若要字形也一致需 K≈0.68，但那样我们会比源书轻 ~20%（源书笔画被印墨/扫描展宽）。
4. **p100 不再压**：逐字墨迹面积口径 p100 已 +2.7%（≤5%）；内框区墨迹占比口径 p100 为 **−5.8%**
   （我们已比源书**浅**），继续压会反向偏离 → 不动。若坚持按另一套口径压，需用户确认口径定义。
5. **未做逐页 K 自适应**：全书单一 K（源书各页墨宽 p25-p75 差 ≤1pt）；换书应按页回归
   （脚本 `tmp_vert/taskJ/measure_char2.py` 可直接出该数）。
6. **`PAGE_ORIGIN_BP = 72` 的适用面**：它是 dvipdfmx 固定的 DVI 原点(1in)在页面坐标的 x，
   与纸型无关（本案 A4 与探针小页都实测 72）。若将来换渲染链（如 xelatex/其它 driver），
   该常量必须重标定 —— 单元测试里有反解回环用例可直接发现（±0.06pt 打印精度）。
