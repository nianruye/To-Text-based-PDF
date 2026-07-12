# Spec: 位置还原两趟校准

## 目标
按源 y 坐标逐行落位（\vspace），两趟校准压缩防溢出。

## 方案
### 位置还原（POSITIONAL=1）
- 每行按源 y0 落位（\vspace* 补足首行 top_vs + 段间 \vspace）
- 段间隙 \vspace = 源y差 - bl（_pp_applied 时减 bl，避免 baselineskip+\vspace 双重计入）
- 预扫描估高 _pos_est（含 figrow 图高 + 段间隙）

### 两趟校准（fit_positional_classic.py）
- pass1：渲染 + 导出 _pos_est（各页估高）
- ratio = 实测高 / 估高
- pass2：带 POS_RATIO_TABLE 重渲（按 ratio 校正）

### 溢出控制
- _pos_gscale（压空白：top_vs + 段间隙）
- _pos_sscale（压 strut：行高）
- POS_FILL=1.08（填充目标=版心×1.08，留余量）
- figrow 图随 min(_pos_sscale, _pos_ratio, _pos_gscale) 缩（防溢出）

## 输入
- spotting 行 y0（200dpi px）
- _pp（page_pitch，源行间距）
- _pos_ratio（pass2 校正比）

## 输出
- 每行按源 y 落位
- 783页（=源，0溢出）
- pitch 达标率 >50%

## 约束
- _pp_applied 时段间隙减 bl（不减 fnt×1.2，避免双重）
- figrow 图高不随 linespread 缩（固定，随 _pos_sscale/ratio/gscale 缩）
- page_pitch 滤小间距 <20px（页码紧贴）+ 方差检测（目录页 None 回退全局）

## 测试点
- 783页（0溢出）
- p26 pitch≈28pt（段间隙减 bl，不双重）
- p11 pitch≈35pt（源 35.1）
- pitch 达标率 >50%
