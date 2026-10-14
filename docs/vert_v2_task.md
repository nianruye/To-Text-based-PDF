# 竖排书还原 v2 任务简报（给 Claude Code）

> 项目：/opt/test — 扫描书排版还原系统。本任务：竖排繁体书（wz6 =《毛泽东选集》第二卷）v2 完善。
> v1.4 已完成并 commit（ddc8761）。本简报含全部实测上下文，请先通读再动手。

## 一、背景与现有实现（v1.4，已验证）

**脚本**：`src/pipelines/build_vert.py`（读 OCR → 生成 tarticle tex → uplatex + dvipdfmx 编译）
**运行**：
```bash
cd /opt/test
VERT_PAGES=3-8 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json \
  output/wz6/wz6_vert_preview.pdf source_pdf/wz6.pdf
```

**引擎链（4 轮实验定案，不要再换）**：
- `upLaTeX`（编译）+ `tarticle.cls`（竖排文档类，默认 tate）+ `pxchfon[unicode]` + `Noto Serif CJK TC`（ttc index=3）+ `dvipdfmx`
- 字体配置：`\setminchofont[3]{NotoSerifCJK-Regular.ttc}`（`[3]`=ttc 子字体索引，JP=0/SC=2/TC=3）
- 禁用：xelatex（bxjscls 无 tate）、platex（pTeX 丢繁体字）

**tate 布局参数语义（与横排不同，实测，勿凭直觉）**：
- `\textwidth` = 列高（列内字数 × 字号）
- `\textheight` = 列区横向容量（列数 × 列距 + 余量）
- `\topmargin` = 天头 − 102pt
- **右缘定位公式：右缘 = 70 + `\oddsidemargin` + `\textheight`** ← 改 th 必须同步改 om，否则列块整体位移出页（曾踩坑：标题排到页面外）
- 页面尺寸：`\special{papersize=W,H}`，值 = 目标 pt × 1.00375（dvipdfmx 按 bp 解析）

**断列控制**：
- 每列：`{\fontsize{字号}{列距}\selectfont 列文本\par}` —— **`\par` 必须在 `\fontsize` 组内**（组外会让新列列距坍缩到 35pt）
- 列内字步进 = 字号（em）；**列距 = \fontsize 第二参数（baselineskip）**
- 大字号列：字号 ≤ 列距 × 0.92（防侵入邻列）；字距宽的标题用"字号 + 字间全角空格"表达

**列分类（现有规则，可复用）**：
- 正文/标题：h > 300px
- 排除书眉/页码：`x0 > 1100 且 h < 300`（当前**跳过不渲染**——v2 要实现）
- 排除左小字边注：`x0 < 100 且 h/字数 < 55`（当前**跳过不渲染**——v2 要实现）

**数据基准**：OCR 坐标 px ÷ 2 = pt（144dpi = 2x）。源书页 595.3 × 1244.1pt。每页 ~12 列、每列 ~25 字、字号 ~34.4pt、列距 ~47.6pt、天头 ~318pt。

## 二、v2 任务（本次目标）

### 1. 书眉（每页右列顶部小字）
- 数据特征：`x0 > 1100`、`h < 300`、非纯数字（如"論持久戰" 4 字 h≈224px、字宽 30px → 小字号）
- 源位置：x 1150-1180px（= 575-590pt），y 1098-1322px（= 549-661pt）
- 渲染：竖排小字（字号≈15pt），绝对定位到版心右上

### 2. 页码（右列中下部）
- 数据特征：`x0 > 1100`、纯数字/汉字数字（如"一八〇"、"一八二"）
- 源位置：x 1148px（=574pt），y 1974-2068px（= 987-1034pt）
- 渲染：竖排小字，绝对定位

### 3. 边注（左侧小字注）
- 数据特征：`x0 < 100 且 h/字数 < 55`（如"*這是毛澤東同志一九三八年…" 35 字 h=1668px）
- 源位置：x 12-104px（= 6-52pt），与正文列同起（y≈700px 起）
- 渲染：竖排小字（字号≈24pt = 正文档 0.67），定位在版心左缘

### 4. 版框线（源书四周双边 + 列间界行线）
- 源书：外边粗框（距页缘 ~2pt）、界行线（列与列之间的细竖线）
- 实现建议：eso-pic 或 picture 环境绘制；先做四周边框，界行线可选（v2 尽力）

### 5. 全书 231 页跑通 + 页数 1:1 验证
- 分页机制：当前每源页 → `\newpage`（预览 OK；全书跑需确认无溢出）
- 注意：p1 封面（扫描图）、p2 空白页需特殊处理（封面建议复用 `PAGE_IMAGE_PAGES` 贴图机制，见 `src/pipelines/build_geom.py` L907）

## 三、实现建议

- **书眉/页码/边注**用 **eso-pic**：`\AddToShipoutPictureFG{\put(x,y){...}}`（build_geom.py 已有大量先例，坐标 = pt，原点页左下 → 注意 y 反转：`y_bottom = page_h - y_top - 内容高`）
- 竖排小字在 \put 内用 `\shortstack{字\\字\\字}` 或 `\fontsize{}{}\selectfont` + 手工断列
- **先做最小验证**：书眉+页码先实现 → 渲染 p4-p8 对比源书 → 确认无误 → 再做边注/版框线/全书
- 每完成一项：渲染对比图（源 vs 重建）保存到 /tmp/
- **验收标准**：
  1. 书眉/页码/边注出现在与源书对应位置（±5pt）
  2. 全书 231 页输出、页数 1:1
  3. 无字符超出页面（检查：`fitz` 逐 span 验证 bbox 在页内）
  4. 文本提取无字符丢失

## 四、环境与工具

- Python：`/usr/bin/python3`（有 fitz）；编译：`uplatex` + `dvipdfmx`
- 预览跑法：`VERT_PAGES=3-8`（env 控制页范围）
- OCR 数据：`data/wz6/wz6_spotting_lines.json`（文本）+ `wz6_spotting_coords.json`（poly 坐标）
- 源书：`source_pdf/wz6.pdf`（231 页）
- 当前产物：`output/wz6/wz6_vert_preview.pdf`（6 页预览，v1.4）
- **验证 PDF 必须用两个手段交叉**：① fitz 提取文本 + bbox 在页内检查 ② pdftoppm 独立渲染看图（fitz 提取到文本 ≠ 肉眼可见！曾发生"文本在但被排到页面外"）

## 五、禁止事项

- 不要改动 `build_geom.py` / `fit_positional.py` / 四书（wz1/wz3/wz4/mgfdmg）的任何数据与产物——那些是已验证的横排回归基线
- 不要 git reset / 强制覆盖已有的 build_vert.py（v1.4 已 commit ddc8761，在其基础上增量改）
- 不要用 heredoc 内联跑复杂 shell（转义坑多）；写独立脚本文件再执行
- `/tmp` 在 WSL 重启后会清空——重要文件放 `/opt/test/tmp_vert/` 或项目内
