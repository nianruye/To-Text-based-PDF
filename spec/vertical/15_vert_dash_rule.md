# 15. 竖排破折号 = 源图墨迹实测的一条连续竖线（taskD / R2）

状态：**implemented**
实现：`src/pipelines/build_vert.py` §1.0a4（L291–474：常量 L323–341 / `_dash_rule_on` L353 / `_dash_runs` L364 /
`_dash_ink_seg` L382 / `_dash_rule_tex` L455 / `_fg_origin_shift` L469）+ `_put_tex` L625 /
`col_puts` L4021（逐组实测，`_rule_h` L4140）
测试：`src/test/unit/test_vert_dash_rule.py`（32 项）；报告 [docs/vert_dash_rule_report.md](../../docs/vert_dash_rule_report.md)

## 1. 目标（用户反馈）

用户拿 wz7《金瓶梅詞話》p57（「論金瓶梅這部書——導讀」）对照源书：

1. 「但是真的破折号 应该是一个竖线 ，但是你给我的PDF中是两个横线  如p57」；
2. 「源书就是一条竖线 而不是两条竖线拼接的」；
3. R2 复核追加：「这个长度 是不是盖到字了」—— R1 每字画满一格，源书墨线实测远短于两格（具体数值见 §9.1）。

## 2. 契约 A：相邻破折号 = 源图同一个墨块（`_dash_runs`）

- **输入**：`col_puts` 的列文本 `t` + 逐字格号 `k_of`（与渲染循环同一套推进规则）。
- **判据**：`t[i]` 是破折号类（`DASH_CHARS` = `—`U+2014 / `―`U+2015 / `–`U+2013），
  且 `t[i+1]` 也是、格号连续（`k_of[i+1] = k_of[i]+1`）。
- **输出**：`[(ci0, ci1, k0, nd)]`。中间被 `fit_gaps` 插了空格的两个 `—` **不是**一组。
- **理由**：OCR 把源书的**一个标点墨块**读成相邻两个 `—` 字符；按字符各画一条必然 2 格长。

## 3. 契约 B：线长/线位/线宽全部从源图墨迹实测（`_dash_ink_seg`）

- **读取窗口**：本列列心 `xc` ± 0.35×step（x）；本组格区 `[T+k0·step, T+(k0+nd)·step]` ± 0.5×step（y）。
  源图墨迹 = `_frame_ink(pi, g)`（NF 页逐页 Otsu，有版框页固定 150，与既有路径同源）。
- **找线**：逐像素列找**最长连续墨段**；候选须同时满足（都是比值，env 可覆盖）：
  1. 段长 ∈ [`DASH_SEG_LO`, `DASH_SEG_HI`] × (step × nd)（0.45-1.70；挡笔画碎片/并字长 run）；
  2. 段与**本组格区**的重叠 ≥ `DASH_SEG_OVL` × 段长（0.75；挡上下邻字的笔画）；
  3. 线宽（同段覆盖 ≥0.5 的连续墨列）≤ `DASH_W_MAX` × step（0.35；挡字画笔/粘连）；
  4. 线心距列心 ≤ `DASH_X_TOL` × step（0.25；挡错列/字画笔）。
  取满足条件的最长段。
- **输出**：`{y0, y1, xc, w, ratio}` —— y0/y1 = 墨段起止、xc = 墨列中心、w = 墨列宽、ratio = (y1-y0)/step，
  **全部是源图墨迹实测值**（pt，页左上原点），不用 step / F / INK_ASC 推算位置。
- **参考比值** `DASH_LEN_RATIO`（参数默认；wz7 p57 实测见 §9.3）只用于日志/验收对照，不参与画线。

## 4. 契约 C：一条线 + 文本层保留（`_dash_rule_tex` / `_put_tex`）

- **画线**：每组画**一条** `\rule`：高度 = `y1-y0`；线心 = 实测 `xc`；
  底端落在源图 `y1`（put y = `page_h - y1 - FG 原点偏移`，见 §5）；线宽优先用**源图实测线宽**
  （`VERT_DASH_RULE_W=src`）；兜底默认参数见 §9.3（参考值，非判据）。
- **文本层**：组内每个 `—` 仍出 `\put`（原字、原字号、原压缩），用 `3 Tr` 不可见 ->
  可搜索 / 字符量不变 / 与改前文本层逐字节相同。
- **不变量**：字数、格数、step、列位、字号、基线位置全部不变；只多一条矢量图元。

## 5. 契约 D：FG 原点偏移（`_fg_origin_shift`）

- **根因**：前言 `\setlength{\paperheight}{page_h pt}` 把 **bp 数值当 TeX pt**，而物理页高是 `page_h` bp
  （= page_h×PT2BP TeX pt）-> eso-pic FG 原点比页真左下**高** `page_h×(1−1/PT2BP)`。
  数值随页高变化（p57 实测见 §9.1；`page_h×(1−1/PT2BP)` 是相对式）。
- **契约**：源图实测的破折号线要落在**源图绝对 y**，故 put y 减掉该偏移。
  正文/书眉沿用既有 `\put` 约定（不动，避免影响既有对齐）。

## 6. 契约 E：影响面与兜底

| env | 默认 | 含义 |
|---|---|---|
| `VERT_DASH_RULE` | `nf` | `nf` = 只对无版框伪槽格页；`all`/`1`/`on` = 全部竖排列；`0`/`off` = 关 |
| `VERT_DASH_RULE_W` | 见 §9.3 | 线宽/字号；`src` = 用源图实测线宽（参数默认，非判据） |
| `VERT_DASH_LEN_RATIO` | 见 §9.3 | 参考比值（日志/验收对照；参数默认，非判据） |
| `VERT_DASH_SEG_LO/HI/OVL` | `0.45 / 1.70 / 0.75` | 墨段判据（比值，见 §3） |
| `VERT_DASH_X_TOL` / `DASH_W_MAX` | `0.25 / 0.35` | 线心/线宽判据（比值） |
| `VERT_DASH_DBG` / `VERT_DASH_REPORT` | 关 / `TMP/dash_segments.json` | 逐组日志 / 明细落盘 |

- **默认 `nf`**：R1/R2 硬验收都要求有版框书（wz6）`vert.tex` 逐字节零回归；wz6 有 19 个 `—`（9 页）。
- **兜底**：无源 PDF / 找不到合格墨段 -> 每个字符 1.0 step（旧 R1 行为），并在
  `[破折号] ... 未标定, 用兜底` 日志与 `dash_segments.json` 登记（不静默用推算值）。
- **西文侧排不动**：`LAT_DASH` / `_latin_put` 走旋转排版路径，不经过 `_put_tex`；`_esc_ch` 不做字形映射。

## 7. 验收（硬）

- 命令与实测数据见 **§9.2**（p57 线长/线位/线宽/间隙、wz6/wz7/p29 回归、测试数）。
- `src/test/verify_vert.py` **未改**（判据未放宽）；硬约束：p57 一条线 + 线长/线位与源图一致；
  wz6 `vert.tex` 逐字节零回归；wz7 300 页 verify PASS。

## 8. 已知遗留（摘要）

1. **p57 线顶/线底到相邻字墨迹的间隙**无法与源书同时对齐（标题列均摊所致）——实测数值与反证见 §9.4 第 1 条。
2. **线宽**：源图实测宽于默认参数；产物按 R2「先不动」——数值与 `src` 开关见 §9.3 与 §9.4 第 2 条。
3. **数据侧误读**：patched 数据仍有 `——`/`—` 的引号笔画误读——计数见 §9.4 第 3 条；建议单独数据审计。
4. **无源 PDF 的 3 参数调试构建**：整条 NF 绝对定位路径不可用（页回退 v2 流式），破折号按旧字形输出；
   这是任务前行为，不是 R1 兜底。

## 9. 参考基线（本书实测，仅作参照，不作判据）

> 书目：wz7（《金瓶梅詞話》，竖排扫描书，1748 页）；日期/来源逐行标注。以下为实测/参数默认，
> **不进入 §2–§7 的判据**；换书必须重新标定线宽/线长参考值，不能复用本书数字。

### 9.1 p57 真破折号（wz7，2026-10-22/2026-11-06，`docs/vert_dash_rule_report.md` / `docs/battle9_fix.md`）

| 项 | 实测 |
|---|---|
| R1 旧行为（每字满一格） | 2 格 = **127.44pt** |
| 源书墨线 | **80.2pt**（≈1.26 格）；细测 **80.25pt = 1.259 step** |
| 产物线 | **80.00pt = 1.255 step**（∈[1.20,1.32]） |
| 线位 | 产物 rule y **736.50–816.50** vs 源图 **736.50–816.75** → Δy0 **0.00** / Δy1 **−0.25** / 线心 Δ **0.19pt** |
| 连续性 | 沿 y 每 0.5pt **最大空隙 0.00pt**（≤0.5） |
| 线宽 | 源图 **5.25pt**（0.075×F，t42/阈值 110；阈值相关实测 4.56–5.28）；代码 `_dash_ink_seg` 源墨实测 **5.0pt**；产物 **v42 2.78pt**（0.040×F）→ **v44 5.0pt**（`VERT_DASH_RULE_W=src` + `VERT_DASH_RULE_W_PAGES=57` 按页启用；仅 p57 变，见 §9.2） |
| FG 原点偏移 | p57：1437×0.003735 = **5.37pt**（实测 rule put y 与落点差 **5.38**） |
| 邻字间隙 | 源图邻字 **8.25/6.00**（0.129/0.094 step，与源书同值）；产物邻字 **38.87/14.50**（0.610/0.228，标题列均摊） |

### 9.2 回归/验收（wz7/wz6/p29，2026-10-22/2026-11-06，`docs/vert_dash_rule_report.md` / `docs/battle9_fix.md`）

p57 复现命令：`tmp_vert/taskD/verify_r2.py /tmp/r2b_57.pdf source_pdf/wz7.pdf 57 830 63.72`。

```bash
# wz6 构建（默认 nf；all 模式加 VERT_DASH_RULE=all）
VERT_TMP=/tmp/wz6_dash /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_dash.pdf source_pdf/wz6.pdf
md5sum /tmp/wz6_dash/vert.tex    # ae9d2f52…
# wz7 300 页 + 测试
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v35.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

| 项 | 命令 / 口径 | 实测 |
|---|---|---|
| p29 西文侧排 | `VERT_DASH_RULE=0` vs 默认 | `vert.tex` **逐字节相同** |
| wz6 默认 | 全书构建 | `vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d**（= 改动前基线） |
| wz6 `all` | 同上 + `VERT_DASH_RULE=all` | 6 组实测（线长/step **1.85–1.98**，wz6 自己的墨线，非 wz7 的 1.26）+ 3 组兜底；文本层 231/231 页相同；`verify_vert` PASS（231=231 / 97.2% / 越界 0/0） |
| wz7 300 页 | `verify_vert --expect-low <影印页>` | **PASS**（300=300 / 128671÷130732=98.4% / 越界 span 0+矢量 0 / 整页丢失 0）；文本层与 R1 版 300/300 页相同 |
| 测试 | `pytest src/test/unit src/test/invariants -q` | **506 passed**（474 + 32 新增；2026-11-07 全量 **603 passed**） |
| v43（全局 `src`，**作废**） | `VERT_DASH_RULE_W=src`（旧全局口径） | 影响 8 页（31/37/39/57/62/1157/1683/1742）；p1742 22 组变宽 1.5–13.0pt，风险不可接受 → 不交付（见 `docs/battle13_dash_width.md`） |
| **v44（按页启用，交付）** | `VERT_DASH_RULE_W=src VERT_DASH_RULE_W_PAGES=57`；`bash tmp_vert/battle13b/build44.sh` | p57 线宽 **2.784→5.0pt**（y 736.5–816.5 / 长 80.0 / x 830.0 不变）；**v44 vs v42 内容流/绘图逐页 diff 仅 p57**（其余 1747 页 content-stream 逐字节相同）；`verify_vert` **PASS**（1748=1748 / 931,200 与 v42 同 / 18 预期 / 0 / 0+0）；wz6 默认 `ae9d2f52…`；pytest 603 |

### 9.3 参数默认（参考值，非判据）

| 参数 | 默认/参考 | 说明 |
|---|---|---|
| `VERT_DASH_RULE_W` | **0.040×F** | 兜底线宽；`src` 时用源图实测宽度（p57 实测 **5.0pt**，0.0718×F；t42 外部实测 5.25pt=0.075×F（阈值相关）；300 页中位 0.0559×F）。**默认不变** |
| `VERT_DASH_RULE_W_PAGES` | **空**（= 全局行为） | 逗号分隔页号（如 `57,1683`）：仅这些页在 `src` 模式下用源墨实测宽度，其余页仍 `0.040×F`。wz7 构建脚本 `tmp_vert/battle13b/build44.sh` 用 `VERT_DASH_RULE_W=src VERT_DASH_RULE_W_PAGES=57`（只动 p57） |
| `VERT_DASH_LEN_RATIO` | **1.26** | 参考比值（日志/验收对照，不参与画线） |
| `VERT_DASH_SEG_LO/HI/OVL` | 0.45 / 1.70 / 0.75 | 墨段判据（无量纲比值） |
| `VERT_DASH_X_TOL` / `DASH_W_MAX` | 0.25 / 0.35 | 线心/线宽判据（无量纲比值） |

### 9.4 已知遗留的实测证据（wz7，2026-11-06，`docs/vert_dash_rule_report.md`）

1. **p57「线顶/线底到相邻字墨迹的间隙」无法与源书同时对齐**（R2 验收 1 的第二个条件）。
   反证（实测）：产物标题列 `書` 墨底 **697.6** / `導` 墨顶 **831.0**（间隙 133.4pt = **2.093 step**）；
   源图 `書` 墨底 **728.25** / `導` 墨顶 **822.5**（间隙 94.25pt = **1.479 step**）。
   源书线长 1.259 + 两间隙 0.223 = 1.482 step，正好填满源书 1.479 step 的间隙；
   产物间隙 2.093 step 比它多 **0.611 step（39pt）**。线长固定 1.20-1.32 step 时，
   两间隙不可能同时落在源书 ±0.05 step 内（所需 1.478 step ≪ 可用 2.093 step）。
   根因是标题列把 11 个 OCR 字符**均摊**（产物書比源书高 30.6pt），属 §1.995 标题署名行的既有版式，
   不在本任务范围。本实现把线放在**源图绝对位置**（Δ≤0.25pt）——与源图墨块逐点一致、且不压字。
   若要同时满足间隙，需把标题列改成逐字源图定位（另一项版式任务）。
2. **线宽**：源图 t42 实测 5.25pt（p57，0.075×F，阈值 110）/ 0.0559×F（300 页中位），代码 `_dash_ink_seg` 自测 **5.0pt**；
   默认仍 0.040×F（2.78pt，行为不变）。**v44 起 wz7 构建脚本用 `VERT_DASH_RULE_W=src` + `VERT_DASH_RULE_W_PAGES=57`**
   → 仅 p57 线宽 **5.0pt**（= src 实测值；t42 的 5.25 为阈值 110 外部测量，本机阈值 90–150 得 4.56–5.28，
   按 5.0±0.3 接受）；其余 14 个 dash 页保持 0.040×F。换书按本书源墨重测，并按页列出需要 `src` 的页。
3. **数据侧误读**：patched 数据仍有 88 对 `——` + 87 个单 `—`；其中「闭引号/句号后紧跟」的
   与 p59/p118 实测源图无破折号（引号 ﹂ 的笔画被读成 `—`），与已删的 1019 处同类。
   这类位置源图测不到合格竖线 -> 走兜底并登记；建议单独做数据审计。
4. **无源 PDF 的 3 参数调试构建**：整条 NF 绝对定位路径不可用（页回退 v2 流式），破折号按旧字形输出；
   这是任务前行为，不是 R1 兜底。
