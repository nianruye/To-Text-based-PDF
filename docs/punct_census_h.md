# 横排标点漏识普查报告（t257）

## 结论（先回答关键问题）

**用当前 `*_spotting_lines.json` 的行级坐标，横排标点漏识的“几何可恢复量”无法给出正比例；已验证可补形候选为 0。**

原因不是源图看不到墨迹，而是输入数据只有 **OCR 行 bbox + 整行字符串**，没有字符级 bbox：
一行内的漏标点（尤其 `1.“…` 的 `“`、句末 `。`）仍落在该行 bbox 内；把行 bbox 当 OCR 解释会全部覆盖，
把行 bbox 按字符串长度收缩又会把行内汉字/英文/PDF 元数据碎片大量误报（见抽样）。
因此本报告只能给出**负结果**：`punct_eval` 的 32 个纯漏识不能靠现有行级几何直接补形；
需要先拿到**字符级 OCR bbox**（或产物 PDF 的实际 span bbox）再做残差。

## 运行

```bash
# ghbq 全 104 页
/usr/bin/python3 src/tools/punct_census.py --book ghbq \
  --pdf source_pdf/ghbq.pdf \
  --lines output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json \
  --coords output/ghbq_full/_ocr_ghbq/ghbq_spotting_coords.json \
  --pages 1-104 --out output/ghbq_full/punct_census.json \
  --crops /tmp/punct_census/ghbq

# wz4 30 页（含 2/5/97/428）
/usr/bin/python3 src/tools/punct_census.py --book wz4 \
  --pdf source_pdf/wz4.pdf --lines data/wz4/wz4_spotting_lines.json \
  --coords data/wz4/wz4_spotting_coords.json \
  --pages 1,2,3,4,5,10,20,30,40,50,60,70,80,90,97,100,150,200,250,300,350,400,420,425,426,427,428,500,600,677 \
  --out output/wz4/punct_census.json --crops /tmp/punct_census/wz4

# wz1 20 页
/usr/bin/python3 src/tools/punct_census.py --book wz1 \
  --pdf source_pdf/wz1.pdf --lines data/wz1/wz1_spotting_lines.json \
  --coords data/wz1/wz1_spotting_coords.json \
  --pages 1,2,5,10,20,40,60,80,100,120,140,160,180,200,210,215,218,220,221,222 \
  --out output/wz1/punct_census.json --crops /tmp/punct_census/wz1
```

单书实测 ghbq 104 页约 20-30 秒、wz4 30 页约 8 秒、wz1 20 页约 6 秒；纯 CPU（fitz+numpy+scipy），无 GPU。

## 结果

| 书 | 页数 | candidates_total | by_class |
|---|---:|---:|---|
| ghbq | 104 | 191 | enumeration_comma 83 / period 108 |
| wz4 | 30 | 0 | — |
| wz1 | 20 | 431 | enumeration_comma 37 / other 151 / semicolon 13 / ring 96 / quote_open 57 / comma 44 / period 31 / quote_close 2 |

数据文件：
- `output/ghbq_full/punct_census.json`
- `output/wz4/punct_census.json`
- `output/wz1/punct_census.json`

## 抽样 30 处逐块核对（源图裁片）

裁片 2x：`/tmp/punct_census/ghbq/*.png`、`/tmp/punct_census/wz1/*.png`；联系表 `ghbq_sheet.png` / `wz1_sheet.png`。

- **ghbq 前 30 处**：全部是 PDF 封面/版权元数据或英文/汉字碎片（`PDF at...`、`Some state...`、`MTM...`），
  **0/30 真标点**。
- **wz1 前 30 处**：全部是汉字笔画/目录词条（`页码数=206`、`出版社`、`封面`、`书名`、`目录` 等），
  **0/30 真标点**。
- 误报根因：行级 bbox 覆盖与按 `font_h×units` 收缩二选一都会失败——
  全 bbox 覆盖 → 行内漏标点不可见；收缩估计 → 行内汉字/英文/元数据被切成碎片。

因此 `by_class` 计数是**几何候选**，不是已确认漏标点；本报告不把它们升级成“可恢复量”。

## 与 gold 对照

横排三书没有 `punct_eval` gold；`punct_eval` 的 34 FN 位于 **wz7 竖排**，不能直接迁到横排坐标。
本条未做 gold 对齐；若后续提供横排 gold（含字符级 bbox/page-line 位置），可直接把本工具的 candidate 与 FN 做最近邻配对。

## 工具限制（必须随工具一起看）

1. OCR 输入只有行 bbox；**行内漏标点无法与汉字笔画区分**。
2. 尺寸窗/版心/图版/页眉页脚判据是相对量（正文字高），但正文字高由行 bbox 中位估计，封面/图表页会偏大。
3. 分类是**单连通域几何**：period/comma/colon/quote 的成对关系未做跨组件聚簇；`ring` 高估明显（wz1 96 条均为汉字部件）。
4. 结论：在当前数据上，**可确认可直接补形的漏标点为 0**；要得到真实可恢复比例，下一步必须产出字符级 OCR bbox
   （或对 `output/<book>/*.pdf` 做 span 级残差），否则任何正数都不可信。

## 判定

- 本工具与报告完成“普查方法 + 反例 + 抽样 + 可复跑”。
- **可恢复量结论：0 个已确认可补形候选 / 输入不足；不能把 32 个纯漏识估算成可由行级几何恢复。**
