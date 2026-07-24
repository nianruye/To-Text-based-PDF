# 现代书籍排版 Spec 索引

现代书籍专用排版还原（`src/pipelines/build_geom.py` + `src/calibration/fit_positional.py`）。

**状态**：⚠️ 已实现但缺独立分部 spec（本文件为总 spec，覆盖核心功能）

## Spec 文件

| 编号 | 文件 | 功能 |
|---|---|---|
| 01 | [footnote.md](footnote.md) | 脚注（①分界线 + 小字 + 续行） |
| 02 | [header_pagenum.md](header_pagenum.md) | 页眉（共识吸附）+ 页码（\setcounter + 补全） |
| 03 | [heading_hierarchy.md](heading_hierarchy.md) | 标题层级（行高 + toc_map + 居中） |
| 04 | [toc_page.md](toc_page.md) | 目录页（dotfill + 页码右对齐 + 左移） |

## 架构

```
源 PDF -> PaddleOCR-VL spotting(行级) + layout(版面)
  -> src/pipelines/build_geom.py(排版还原)
    -> src/calibration/fit_positional.py(两趟校准,可选)
  -> 输出 PDF
```

## 行距机制（与古籍差异）

现代书用 `\linespread`（小字生效，pitch=fnt×1.2×linespread）；古籍用 `bl=_pp`（大字 \linespread 不生效，直接设 baselineskip）。

- `BASELINE = median(pitches) × 72 / DPI`（源行距中位）
- `LINESPREAD = BASELINE / (FONT × 1.2)`
- 正文行距 = FONT × 1.2 × LINESPREAD = BASELINE

## 核心功能

### 1. 脚注
- 识别：行首 ①②③...（`FN_CIRCLE`）+ 分界线后续行（不以①开头但属脚注区）
- 渲染：`\hrule` 分界线 + `FONT_SM` 小字（=FONT×0.78）
- 高度：`hrule≈9pt + 每行 FONT_SM×1.2×linespread`（位置还原估高用）

### 2. 页眉
- 识别：`y0 < page_px_h × 0.05`（页顶5%）+ `len(t) < 30`
- 共识吸附：`page_header_raw` 提取原始行 -> `CANON_HDRS`（出现≥3次的规范页眉）-> OCR 拆分/截断/混噪声校正（如"第一部分"+"历史考"->"第一部分历史考证"）
- 渲染：顶部小字 `FONT_SM`

### 3. 页码
- 识别：`PN_RE`（数字）+ `y0 > page_px_h × 0.80`（底部）
- 渲染：`\setcounter{page}{N}`（LaTeX 页脚，不占版心）
- 补全：`pntab`（页码表，PAGENUM_GLOBAL_TABLE）+ 连续推断（前后页±1）

### 4. 标题层级
- 识别：行高 > 正文（`is_big`/`is_tall`）+ `toc_map` 命中（目录篇名）+ 居中
- 分级：`_head_level` -> part（超大行高）/ section（编号/[引言]）/ title（其余）
- 字号：`tier_size` 按 tier 档（分/大/节）
- 续行：标题未以句末标点收尾 + 下行 x0 在 body_left 附近 -> is_cont 继承字号

### 5. 目录页
- 识别：`TOC_ENTRY_RE`（标题....页码）行 ≥5 = 目录页 -> 全降级（章节标题也按 dotfill 渲染）
- 渲染：标题 + `\dotfill` + 页码右对齐（`\makebox[\textwidth]`）
- 层级缩进：`_toc_level`（部分/附录=0，章/节=1，一/二=2）
- 左移：`_toc_shift`（源目录从 ~52px 起，正文边距 128px -> 左移匹配源绝对位置）

### 6. 水印过滤
- 识别：`y0 > page_px_h × 0.95`（极底）+ `w_ratio < 0.50`（窄行）
- 几何判定（不用关键词，OCR 乱识 + 正文含"理论"会误杀）

## 输入
- spotting 行 x0/y0/行高/文字
- layout JSON（image/aside_text/number 等）
- pntab（页码表，PAGENUM_GLOBAL_TABLE）
- toc_map（目录标题，TOC_HEADING_MAP 或自动提取）

## 输出
- 正文段首缩进 2em
- 脚注 hrule + 小字
- 页眉顶部小字（共识校正）
- 页码 \setcounter
- 标题分级字号 + 居中
- 目录 dotfill + 页码右对齐

## 约束
- 页眉共识需 ≥3 次出现（CANON_HDRS）
- 目录页判定 ≥5 条 TOC_ENTRY
- 水印几何判定（不用关键词）
- 行距用 \linespread（小字生效）

## 测试点
- wz1（222页）：pitch 95% / 0 溢出
- 脚注 ① 分界线
- 页眉共识校正
- 页码补全
- 标题层级字号
- 目录 dotfill

## 运行

```bash
cd /opt/test && LAYJSON="data/wz1/wz1.pdf_by_PaddleOCR-VL-1.6.json" \
  PER_PAGE_PITCH=1 PAGENUM_GLOBAL_TABLE=data/wz1/wz1_full_pagenum.json \
  python3 src/calibration/fit_positional.py \
  data/wz1/wz1_spotting_lines.json data/wz1/wz1_spotting_coords.json \
  output/out.pdf source_pdf/wz1.pdf
```

## 与古籍（build_classic.py）的差异

| 项 | 现代书（build_geom）| 古籍（build_classic）|
|---|---|---|
| 行距 | \linespread（小字生效）| bl=_pp（大字直接设）|
| 墨高重叠 | 无 | \\[-2pt]（行距=行盒-2）|
| 字号分类 | 按页 cw | 正文/注释两类全局（PAGE_FONT）|
| 旁注 | 无 | aside 竖排 + 补全 |
| 校注标记 | 无 | 〔X〕上标 |
| CJKglue | plus 0.35em（拉伸短行）| 同 |
