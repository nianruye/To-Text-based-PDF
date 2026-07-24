# Spec: 目录页排版

## 目标
目录页：标题 + 点引导 + 页码右对齐，层级缩进，整体左移匹配源位置。

## 方案

### 识别
- `TOC_ENTRY_RE`：`[.·…．]{2,}\s*\d{1,4}\s*$`（标题....页码）
- 目录页判定：TOC_ENTRY 行 ≥5 -> 全降级（章节标题也按 dotfill 渲染）
- frags 形态：标题片段 + 页码片段（同 y 分开 poly，合并后多片段）

### 渲染
- `\makebox[\textwidth]{标题 \dotfill 页码}`（点引导 + 页码右对齐）
- 整体左移：`_toc_shift`（源目录从 ~52px 起，正文边距 128px -> 左移匹配源绝对位置）
  - `\noindent\hspace*{-toc_shift}\makebox[\dimexpr\textwidth+toc_shift\relax]`
- 层级缩进：`_toc_level`
  - 部分/附录/导论=0，章/节=1，一/二/1.=2
  - `\hspace*{indent}` 按 x0 相对基准

### 标题过长保护
- `_toc[0]`（标题）字宽 > 75% 版心 -> 非真目录条目（内容页被 ……数字 误检）-> 改走正文 makebox[s]

## 输入
- spotting 行文字、x0
- `TOC_ENTRY_RE`、`body_left_px`
- `_toc_ref`（目录条目最左 x0）

## 输出
- 目录条目 dotfill + 页码右对齐
- 层级缩进
- 整体左移匹配源

## 约束
- 目录页判定 ≥5 条 TOC_ENTRY
- 标题过长（>75%版心）非目录条目
- 页码右对齐（\makebox[\textwidth]）

## 测试点
- wz1 目录页 dotfill
- 页码右对齐
- 层级缩进
- 左移匹配源
