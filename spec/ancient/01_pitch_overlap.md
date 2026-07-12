# Spec: 墨高重叠 + 位置还原

## 目标
还原古籍 CJK 排版的"墨高重叠"（行间距 < 行盒高），并按源 y 坐标逐行落位。

## 背景
- 源 PDF（扫描古籍）：pitch（行间距）=35pt，行盒高=37pt，墨高重叠 2pt
- LaTeX hbox 行距=行盒高（不重叠），要 pitch 35 必须行盒 35（内容矮->空白），要行盒 37 必须 pitch 37（溢出）
- 矛盾：pitch 准 + 行盒满不可兼得

## 方案
- `bl = _pp`（源 pitch，行盒高=37）
- `brk = \\[-2pt]`（每行行距-2pt = baselineskip-2 = 35 = 源 pitch）
- 行盒高 37（strut+墨高），行距 35（\\[-2pt]），重叠 2pt（模拟 CJK 墨高重叠）

## 输入
- spotting coords（每行 y 坐标，200dpi px）
- page_pitch(key)（源行间距，px->pt）

## 输出
- 每行 `\fontsize{fnt}{bl} \makebox[...]{\rule{0pt}{strut}文本} \\[-2pt]`
- pitch=源pitch-2+2=源pitch（准）
- 行盒=源行盒（满）

## 约束
- 只大字页（PF>13）用 \\[-2pt]；小字（wz1）走 \linespread
- 不影响正文/注释字号分类
- \\[-2pt] 在 makebox 后（不在 group 内），生效

## 测试点
- p11 pitch≈35pt（源 35.1）
- p26 pitch≈28pt（源 28.0，注释页）
- 0 溢出（783页=源）
- pitch 达标率 >50%
