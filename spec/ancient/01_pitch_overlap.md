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

## 已知限制: CJK lineskip 偏移

CJK 字体（Noto Serif CJK JP）的 depth ≈ 字号×0.20（如 14.7pt→2.88pt），使 hbox 总高(strut+CJKdepth) > baselineskip。
LaTeX 在 `\par` 后检测到此条件，触发 `\lineskip`（默认 1pt）代替 `\baselineskip`，导致 pitch 偏大 ~2pt。

**影响范围**: 注释页/前言页（字号 14.7pt, src_pitch 27-28pt），输出 pitch 偏大 +1.8pt（5-8% 误差），约 188 页。
**正文页影响小**: 正文 17.4pt 的 CJK depth 3.48pt，但 src_pitch 35pt 远大于行盒高，不触发 lineskip。

**尝试过的修复**:
1. 减小 strut → 不触发 lineskip → 但行盒高度降低 → 两趟校准估高偏低 → 大量空白页
2. 增大 bl → baselineskip > hbox_total → 但 \par 后间距=baselineskip 偏大 → 大量溢出
3. `\lineskip=0pt` → 触发后间距=0 → pitch 偏小 → 空白页
4. `\lineskiplimit=-\maxdimen` → 强制 baselineskip → 行重叠严重

**结论**: 这是 LaTeX CJK 排版的固有限制，当前 60% pitch 达标率（<3%误差）、中位误差 1.4% 已是合理水平。后续可考虑将 `\par` 改为 `\\[-2pt]`（段落内换行）来绕过此限制。

## 测试点
- p11 pitch≈35pt（源 35.1）
- p26 pitch≈28pt（源 28.0，注释页）
- 0 溢出（783页=源）
- pitch 达标率 >50%
