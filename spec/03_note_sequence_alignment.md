# Spec: 注释序号-文字分列对齐

## 目标
注释页序号〔X〕统一在序号列（x0=_note_text_x - 序号宽），文字紧接序号，续行统一在文字列（x0=_note_text_x）。

## 背景
- 源注释版式：序号列 + 文字列，序号行文字和续行都在文字列对齐
- build_geom 之前整行从序号 x0 渲染（文字不在文字列）
- OCR 识〔X〕为 [X]，需匹配两种

## 方案
### _note_text_x 计算
- 预扫描注释页（_page_seq_start>=2）续行 x0 中位 -> 文字列 x0（pt）

### 序号行渲染
- 序号〔X〕占自然宽（len(序号)×字号，不用 \rlap，防重叠）
- _seq_x = (_note_text_x - _seq_w) - MARGIN（序号在文字列左缘）
- 文字紧接〔X〕（makebox 剩余宽，满行 [s] 齐右/短行 [l] 左对齐）
- OCR [X] 和〔X〕都匹配

### 续行渲染
- indent = _note_text_x - MARGIN（统一文字列，不按源 x0 波动）

## 输入
- spotting 序号行（〔X〕/[X] + 文字）
- _note_text_x[key]（文字列 x0）
- _page_seq_start[key]（是否注释页）

## 输出
- 序号行：〔X〕x0=_note_text_x-_seq_w + 文字紧接
- 续行：x0=_note_text_x（统一）
- 序号+文字不重叠

## 约束
- 只注释页（_page_seq_start>=2）分列
- 正文/前言 indent=0 或 is_para_start 2em
- 满行 makebox[s] 齐右，短行 makebox[l]
- 不影响 pitch/溢出

## 测试点
- p15〔一〕x0=45、〔二〕x0=45、〔三〕x0=45（统一）
- p15 续行 x0=89（统一文字列）
- p15 序号+文字不重叠（span 连续）
- p24〔六四〕x1=533（齐右）
