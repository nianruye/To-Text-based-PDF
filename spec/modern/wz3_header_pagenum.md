# Spec: wz3 页眉/页码/分界线修复

## 目标
修复 wz3 行级版的三个版面还原问题（以 p36 为例）：
1. 页眉被误识别为标题 -> 正确识别为页眉，不进正文 flow
2. 页眉渲染缺居中/分界线/间距 -> 居中 + hrule 分界线 + 与正文间距
3. 页码没打印 -> 用 OCR 检测的页码（pn_ocr）渲染

## 根因（p36 验证）
1. **页眉判定阈值 0.05 太严**（build_geom 5 处: L380/399/421/487/635 `y0 < page_px_h*0.05`）：
   wz3 页眉在页顶 5-6%（5%占368页、6%占299页），5% 阈值漏掉 6% 的 299 页。
   漏掉的页眉进 flow，"第二章..."符合 _heading_core 被当标题渲染。
2. **页眉渲染 L711-712**：`{\fontsize{FONT_SM}... esc(t)}\par` 左对齐，无 hrule，无居中。
3. **页码弃用 pn_ocr**（L608 `pn = _lay_numbers.get(key) or pn_ext`）：
   wz3 无 LAYJSON（_lay_numbers 空）、无 PAGENUM_GLOBAL_TABLE（pn_ext 空），
   pn_ocr（OCR 读到 '17'）被弃用 -> pn 空 -> \thispagestyle{empty} 无页码。

## 方案

### 改动1: 页眉阈值 0.05 -> 0.06（5 处）
L380, L399, L421, L487, L635 的 `page_px_h * 0.05` -> `0.06`。
- 覆盖 wz3 5-6% 页眉（667/771 页）
- wz1 零误判：wz1 页眉 0-3%、正文首行 7.7%，顶部行无 6% 的

### 改动2: 页眉渲染居中 + hrule 分界线（L711-714）
当前：左对齐 + \par + vspace（非 POSITIONAL）
改为：居中（\centerline）+ \vspace{2pt}\hrule（分界线，总是）+ \vspace{HDR_GAP}（非 POSITIONAL）
POSITIONAL 下 top_vs 给正文落位，hrule 在页眉后，间距由 top_vs 提供。

### 改动3: 页码用 pn_ocr + 单调性（L608 + 循环外 _prev_pn）
- main loop 外定义 `_prev_pn = None`
- L608: `pn = _lay_numbers.get(key) or pn_ext or _pn_ocr_use`
- _pn_ocr_use = pn_ocr 经单调性过滤：若 _prev_pn 非空且 pn_ocr 与 _prev_pn 差>2（突变）则弃用
  （排除目录页 p11 pn_ocr=29 误识，正文页码 p7=1,p8=2,... 连续）
- 用后更新 _prev_pn（仅当 pn 是数字）

## 输入
- wz3 行级 OCR 数据（wz3_linelevel_spotting_*.json）
- page_header_raw + CANON_HDRS 页眉共识（已有）
- pn_ocr（L539-540 OCR 检测底部数字页码，已有）

## 输出
- p36 页眉 '第二章周民族之来源...' 居中 + 下方 hrule + 与正文间距
- p36 页码 '17' 渲染（\setcounter{page}{17}）
- 页眉不再被当标题

## 约束
- 只动页眉阈值（5 处 0.05->0.06）、页眉渲染（L711-714）、页码 pn_ocr（L608 + _prev_pn）
- 不改 _heading_core / _head_level / page_header_raw 共识逻辑
- 不加 fallback；中文注释 + UTF-8，无 emoji
- wz1 无回归（页眉阈值改动对 wz1 零影响，已验证）

## 测试点
- 页眉识别：y0 在 5-6% 的顶部短文本被识别为页眉（is_hdr=True），不进 flow
- pn_ocr 单调性：pn_ocr 突变（如 4->29）被弃用；连续（1,2,3）被采用
- p36 渲染：页眉居中 + hrule + 页码 17
- wz1 无回归：pitch 达标率 ≥97.3%，页眉仍正确识别

## 验收标准
- wz3 p36 页眉居中 + 有分界线 + 页码 17 渲染
- wz3 pitch 达标率不低于 84.8%（无回归）
- wz1 pitch 达标率 ≥97.3%（无回归）
- 全单元测试 PASS
