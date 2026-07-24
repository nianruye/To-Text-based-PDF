# Spec: 附录排版

## 目标
附录区（附录一~七）还原源书版式：标题编号与名称分开（"附录一 佚文"非"附录一佚文"）；引文出处小标题识别（司马迁史记/四库全书总目提要等）；引文（大字）与案注（小字）字号区分；案注续行用小字；案注->引文段间留白；左边缩进对齐、右边满行齐右/段末 ragged。

## 方案

### 附录标题分开（\rlap 防重叠）
- 多片段标题 frags（"附录一"+"佚文"分立，y 重叠合并）按源 x 绝对定位 \rlap
- frags 数据结构 (text, x0px, wpx)，渲染前 sorted(frags, key=x0)（左到右，防 rows 按 y0 排序致左右反转）
- 防重叠：逐片段算渲染宽 len×fnt×1.1，若本片段左 < 上一片段右 + 0.8字宽则推开
- 效果：间隙 0 -> 29pt（0.8字宽）

### 附录区检测
- 预扫描找第一个"附录X"大字标题：re.match(r'^附录[一二三四五六七八九十]', t) and h > H_BODY×1.5
- h 阈值排除目录页小字（p10目录"附录一"h=66px ≈ H_BODY vs p585标题 h=143px > 1.5×H_BODY）
- 标记 _appendix_start，主循环 _in_appendix = int(key) >= _appendix_start
- 案注规则只对 _in_appendix 生效（正文区"案："已在注释页 14.6pt 不受影响）

### 小标题识别（LAYOUT_HEADINGS=1）
- PaddleOCR-VL JSON 的 paragraph_title block（content 前导 # 数=级别，##### 司马迁史记=5级）
- _layout_head_level 按 bbox 匹配 spotting 行（JSON 142dpi ×200/142 转 200dpi，±8px 容差）
- is_head = (_lay_lvl is not None) or is_head_heur（layout 优先，坐标不匹配回退启发式，防 p11 正文标题丢失）
- section 字号 = max(tier_size[section]×_rf, PF×1.12)（强制比正文大 12%，否则按 per-page 缩放后 ≈ 注释字号不突出）

### 案注小字 + 续行识别
- 案注段首（"案：/又案："开头）head_size = FONT_SM（12.2 ≈ 引文×0.7，源行高比 0.72）
- 案注段状态机 _in_an：案首设 _in_an=True，续行 gap=y0-_an_prev_y
  - gap > 45pt = 新引文段（段间留白，佚文条目间）退出 _in_an
  - gap < 45pt = 案注续行用 FONT_SM
- 依据：源案注续行 gap=30pt（同段行距） vs 引文段首 gap=60-65pt（段间留白）

### 案注->引文段间留白（bl 修复）
- 根因：案注行 bl=_pp(源pitch=31.7) ≈ vspace(30)，LaTeX 行距 max(bl,自然间距) 用 bl 主导，\vspace 被 \baselineskip 吞
- 修复：flush bl 判断 `fnt > 13`（非 PF > 13）--案注/校注小字（fnt=12.2/8.6 < 13）用 bl=fnt×1.34(16.3)，正文/注释大字用 bl=_pp
- 效果：p586 案注->引文间隔 30 -> 60pt（≈源 62pt）
- LaTeX 机制：\vspace/\vskip/\vspace*/\vbox 都会被 \baselineskip 吞（若 bl≈vspace）；解决让 bl < vspace

### 附录缩进 + 右对齐
- 引文段首 indent = \hspace{2em}（x0=99）
- 案注段首 indent = 2×BODY_FONT pt（2em×正文字号，x0=99）
- 案注续行 indent = 2×BODY_FONT pt（is_an_cont 标记，与案首对齐 x0=99）
- 右对齐：满行 \makebox[s] 两端对齐（CJKglue plus 0.35em 拉伸齐右）；段末短行 \makebox[l] 左对齐（ragged，不拉伸字距）

## 输入
- spotting 行 x0/y0/行高/文字
- PaddleOCR-VL JSON（paragraph_title block，142dpi bbox）
- H_BODY（全局正文行高中位）
- BODY_FONT/NOTE_FONT/FONT_SM（PAGE_FONT 模式）

## 输出
- 附录标题编号+名称分开（间隙 0.8 字宽）
- 小标题 16.4pt（>正文 14.6）
- 引文 17.3pt（正文页）/ 15.1pt（注释页）；案注 12.2pt
- 案注续行 12.2pt；案注->引文段间留白 60pt
- 引文/案注/续行 x0=99 左对齐；满行 x1=533 齐右，段末 ragged

## 约束
- 附录区检测 h 阈值 1.5×H_BODY（排除目录页）
- 案注规则只 _in_appendix 生效（正文区不动）
- is_head_heur 回退（LAYOUT_HEADINGS 坐标不匹配时）
- 小字 bl=fnt×1.34（fnt<13），防 \baselineskip 吞 vspace
- 段末短行 [l] ragged（不拉伸字距，古籍标准）

## 测试点
- 7 个附录标题全分开（附录一佚文 -> 附录一+佚文，间隙 0.8 字宽）
- 附录小标题识别 63 个（司马迁史记等 16.4pt）
- 案注 12.2pt（引文 17.3/15.1 > 案注 12.2）
- 案注续行 12.2pt（gap<45pt）
- 案注->引文段间留白 60pt（≈源 62）
- 引文/案注/续行 x0=99 对齐
- 正文区"案："不受影响（p32 又案 15.6pt 保持）
- 17/17 测试全过，783 页 0 溢出
