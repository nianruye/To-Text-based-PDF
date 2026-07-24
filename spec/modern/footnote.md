# Spec: 脚注

## 目标
识别①②③...脚注，分界线后小字渲染，续行归脚注区。

## 方案
- 识别：行首 in `FN_CIRCLE`（①②③④⑤⑥⑦⑧⑨⑩）
- 续行：①出现后，后续不以①开头但属脚注区的行（`in_fn` 状态）
- 渲染：`\hrule` 分界线 + `FONT_SM`（=FONT×0.78）小字
- 高度估算：`hrule≈9pt + 每行 FONT_SM×1.2×LINESPREAD`（位置还原 _fn_h 用）

## 输入
- spotting 行文字、y0
- `FN_CIRCLE` 集合
- `FONT_SM`、`LINESPREAD`

## 输出
- 脚注 hrule 分界线 + 小字
- 脚注续行归脚注区

## 约束
- ①脚注单独渲染（不进正文 flow）
- 分界线后小字

## 测试点
- wz1 脚注 ① 分界线
- 脚注续行
