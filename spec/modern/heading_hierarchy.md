# Spec: 标题层级

## 目标
识别标题（行高/toc_map/居中），分级定字号，续行继承。

## 方案

### 识别
- `is_big`：行高 > H_BODY×1.8 + 字宽 > FONT×1.8（排除 poly 膨胀的长正文）
- `is_tall`：行高 > H_BODY×1.1（比正文高）
- `is_centered`：左右各内缩（x0 > body_left+inset 且 x0+w < body_right-inset）
- `core in toc_map`：`_heading_core(t)` 剥序号后命中目录篇名表
- `is_subhead`：(一)(二) 类三级小标题
- `is_head_heur` = is_big or (is_centered and is_tall) or core in toc_map or is_subhead

### 分级（_head_level）
- `part`：is_big（超大行高，分标题）
- `section`：t[0] isdigit 或 [【(（（编号/[引言]类）
- `title`：其余（大标题）

### 字号
- `tier_size`：按 tier 档（分/大/节），源行高中位标定
- `head_size = tier_size[tier] × _rf`（per-page ratio）

### 续行
- 标题未以句末标点收尾（`not in TERMINAL`）+ 未以中文数字收尾（篇名完整）
- 下行 x0 在 body_left 附近（`is_cont`）-> 继承标题字号

## 输入
- spotting 行 x0/y0/行高/文字
- `H_BODY`、`toc_map`、`body_left`
- `tier_size`

## 输出
- 标题分级字号（part/section/title）
- 居中标题
- 续行继承字号

## 约束
- is_big 需行高+字宽双条件（防 poly 膨胀误判）
- 续行 y 差约束（防跨段误传）
- 标题末尾中文数字不传播续行

## 测试点
- wz1 标题层级字号
- 标题居中
- 续行继承
