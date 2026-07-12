# Spec: 正文缩进 + 字距 + 标题续行

## 目标
正文段首缩进 2em；字距不收缩到 0（不字挨字）；标题续行不误传正文。

## 方案
### 正文缩进
- is_para_start = x0 > body_left + 10（>版心左+10 = 段首缩进）
- indent = \hspace{2em}（正文段首）
- 注释页 indent = _note_text_x - MARGIN（文字列）
- 前言/正文 indent = 2em if is_para_start else ''

### 字距（CJKglue）
- base 0.15em（字距 2.6pt，不挨字）
- plus 0.35em（拉伸短行）
- minus 0.1em（收缩满行，最小 0.05em 防负）
- 非区域化（USE_REGION 关）

### 标题续行传播
- 标题末尾中文数字/数字 -> 不传播（篇名完整，如"本议第一"后的"惟"不当标题）
- 续行 x0 >= body_left - 10（排除 x0 << 版心左的行，如前言 p5 第2行 x0=47）
- 标题末尾 in TERMINAL -> 不传播

## 输入
- spotting 行 x0、行高、文字
- body_left（MARGIN×DPI/72）
- _page_seq_start（是否注释页）

## 输出
- 正文段首 x0=MARGIN+2em
- 续行 x0=MARGIN
- 注释续行 x0=_note_text_x
- 字距 >= 0.05em

## 约束
- is_para_start 阈值 body_left+10（不用 indent_thr，太高达 238px 漏判）
- CJKglue 非区域化
- 标题续行只对 is_head 且 not is_cont

## 测试点
- p11 '惟' x0=99（缩进 2em）、'良、文学语' x0=65（续行）
- p5 '《中华国学文库》...' sz=16.1（正文，非标题）
- p15 序号行 x0=45、续行 x0=89
- 字距 >= 0（不重叠）
