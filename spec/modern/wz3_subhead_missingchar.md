# Spec: wz3 (一)(二) 标题误判 + 甲骨文缺字贴图

## 目标
1. p67 (一)(二) 满宽正文条目被 is_subhead 误判标题 -> 加 w_ratio 判定排除
2. p68 等页甲骨文/金文缺字(OCR 识为空引号"") -> 从源 PDF 剪字图贴回

## 根因
1. **is_subhead 误判**：L652 `is_subhead = re.match(r'^[（(][一二三四五六七八九十]+[)）]', t.strip())` 仅看序号模式,不看字体/满宽。p67 (一) h=68≈正文 + w=1255 满宽(=正文),是正文条目非标题,被误判。
2. **缺字丢失**：OCR 识不出的甲骨文/金文字,行文本里是空引号""(如 p68 L32 '作""'),渲染输出空引号,字丢失。OCR 行级 poly 无单字 poly,需按字符偏移估算位置剪源图。

## 方案

### 修复1: is_subhead 加 w_ratio<0.85
L652: `is_subhead = bool(re.match(...)) and w_ratio < 0.85`
满宽(=正文)的(一)(二)是正文条目,标题不满宽。p67 (一) w_ratio>0.85 排除。

### 修复2: 甲骨文缺字贴图(新模块 src/utils/missing_chars.py)
- `detect_missing(t)`: 检测空引号""(引文内字缺),返回[(char_idx, ...)]。排除相邻引用(前字符是引号/标点=相邻,前字符是动词=缺字)。
- `crop_char(src_pdf, page_idx, poly, char_idx, t, out_dir)`: fitz 从源 PDF 剪缺字 bbox PNG。行内定位 x = poly_x0 + char_idx * 字宽(字宽=poly_w/len(t)),bbox=(x, y0, x+字宽, y1)。
- build_geom 渲染: 行内有缺字时, esc(t) 的空引号替换为 `\raisebox{-2pt}{\includegraphics[height=字高pt]{图路径}}`(嵌文字流)。

## 约束
- 修复1 只加 w_ratio<0.85 条件,不改 is_subhead 模式
- 修复2 只处理空引号缺字(OCR 识为空),不处理 OCR 识错字
- 不加 fallback;中文注释+UTF-8,无 emoji
- wz1/wz3 无回归

## 测试点
- is_subhead: 满宽(一)(二)不判标题,不满宽(一)(二)判标题
- detect_missing: '作""'检测缺字, '"古"或"丄"'不检测(相邻引用)
- crop_char: bbox 正确(行内定位 x)
- p67: (一)(二) 正文(sz=14.4)
- p68: L32 甲骨文贴图(空引号->图)
- wz1/wz3 pitch 无回归

## 验收标准
- wz3 p67 (一)(二) 当正文(不当标题)
- wz3 p68 L32 空引号位置贴甲骨文图
- wz3 pitch ≥85%, wz1 pitch ≥96%(无回归)
- 全单元测试 PASS

## 已知局限
- 行内定位粗略(字符偏移估算,CJK 字宽不均,贴图可能偏 1-2 字)
- 缺字检测只处理空引号(OCR 识错字如"茇"替甲骨文无法检测)
- 相邻引用 vs 真缺字靠前字符判定,可能误判
