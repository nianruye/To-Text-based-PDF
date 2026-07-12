# Spec: 旁注补全 + 页码补全 + 书影带处理

## 目标
补全 OCR 截断的 aside 旁注内容；补全缺失页码；处理书影图片块。

## 方案
### aside 旁注补全
- layout JSON aside_text block_content（OCR 截断，如"卷第一本议第"少"一"）
- 用目录篇名匹配：剥"卷第X"前缀，剩余匹配目录篇名（"本议第" -> "本议第一"）
- _fix_aside(content) -> 补全
- shortstack 竖排渲染，baselineskip×1.6（字间留空）

### 页码补全
- layout number block（OCR 识别的页码）-> _lay_numbers
- 连续推断：后向优先（后页-1），前向兜底（前页+1）；封面/目录页（key<10）不补
- pn 优先 _lay_numbers（spotting pn_ocr 误识目录页码如"158"）

### 书影带处理
- LAYJSON image block -> _figs（图块 bbox，142dpi）
- extract_figs 裁源图 200dpi
- in_figure 跳过图块内 OCR 行（不识别图里文字）
- figrow 按源 y 插入贴图 + strut（行盒高=图高）
- 图说明（figure_title + figrow 后紧邻短行）居中
- 启发式 detect_fig_bands 补 LAYJSON 漏检（只 is_garbage_page 跑，防文字页误判）

## 输入
- layout JSON（aside_text/number/image/figure_title block）
- spotting 行（文字 + bbox）
- 目录篇名（_aside_titles，从目录页提取）
- 源 PDF（裁图）

## 输出
- aside 补全内容（如"卷第一 本议第一"）
- 页码 _lay_numbers[key]（含连续推断）
- 书影图块 figrow 贴回 + 图说明居中

## 约束
- aside 补全只对截断 content（匹配目录篇名前缀）
- 页码补全 key<10 不补（封面/目录）
- detect_fig_bands 只 is_garbage_page 跑（防文字页误判）
- figrow 图随 gscale/ratio 缩（防溢出）

## 测试点
- p11/p15 aside "卷第一本议第一"（7字，补"一"）
- p11/p15 页码 1/5（补全）
- p32 〔一〇九〕（○->〇）
- wz1 p28-48 书影贴图 + 图说明居中
