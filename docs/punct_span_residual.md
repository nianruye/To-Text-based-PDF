# 横排标点残差普查（span 级）报告（t259）

## 结论（判定线）

**不能把「产物 glyph 框」当作稳定解释层做补形；真标点比例约 12%（<30%），按既定判定线判死这条路线。**

实测：
- 抽样 90 处（ghbq/wz4/wz1 各 30，随机种子 20261112）：逐块核对 **真漏标点 11 / 90 = 12.2%**（Wilson 95% CI ≈ 7%–21%）。
  - ghbq：3/30；wz4：5/30；wz1：3/30。
- 每百页候选：ghbq **1608**、wz4 **2793**、wz1 **4720**；绝大多数是**字体形状差异/汉字部件/OCR 元数据**，不是漏标点。
- strict「距任一产物 glyph ≥0.08×字宽」实测把**真标点候选全部滤掉**（真标点在源图上紧贴前字，bbox 与相邻 glyph 外扩框重叠），保留下来的反而是字体边缘差异；该判据本身不适配本扫描字体。
- wz7 8 页 gold sanity：114 个候选对 **698 条全部 gold 标点**只命中 14（2%）；34 个纯 FN 无独立坐标 JSON，未能算 FN 命中率（不能把 2% 当 FN 命中率）。

判定：**<30% → 这条路判死**，转「OCR 参数/上下文推断」。

## 方法（实际实现）

1. 源 PDF 页面 200dpi 灰度、Otsu 二值化、8 连通域；
2. 产物 PDF 同页同 dpi 栅格化，膨胀 1px 作为「已解释墨迹」；source-only 墨迹 = 源墨 − 产物墨；
   - 也取了产物 `rawdict` 的逐字符 glyph bbox，但其 bbox 外扩 0.5pt 后覆盖了同一行所有墨迹（含紧邻的漏标点），
     单用 glyph bbox 会得到 **0 候选**；报告明确这是失败路径，不是「没有漏标点」。
3. 候选：正文字高/字宽尺寸窗、正文版心、非整页图版、非页眉页脚；分类为 period/comma/colon/semicolon/quote/bracket/dash/ring/other。
4. 每条候选输出 page、class、像素坐标、bbox(pt)、w/h/面积/aspect、周围前后各 3 个产物字符及 bbox、最近 glyph 距离、候选裁片。
5. 抽样 30/书，裁片 `/tmp/punct_span/{book}/sample_*.png`（4x，源图）；人工逐块核对结果见上。

## 复跑

```bash
# ghbq 全 104 页
/usr/bin/python3 src/tools/punct_span_residual.py --book ghbq \
  --src-pdf source_pdf/ghbq.pdf --out-pdf output/ghbq_full/ghbq_p97v2.pdf \
  --pages 1-104 --out output/ghbq_full/punct_span_residual.json \
  --crops /tmp/punct_span/ghbq --sample 30

# wz4 30 页（含 2/5/97/428）
/usr/bin/python3 src/tools/punct_span_residual.py --book wz4 \
  --src-pdf source_pdf/wz4.pdf --out-pdf output/wz4/wz4_s4.pdf \
  --pages 1,2,3,4,5,10,20,30,40,50,60,70,80,90,97,100,150,200,250,300,350,400,420,425,426,427,428,500,600,677 \
  --out output/wz4/punct_span_residual.json --crops /tmp/punct_span/wz4 --sample 30

# wz1 20 页
/usr/bin/python3 src/tools/punct_span_residual.py --book wz1 \
  --src-pdf source_pdf/wz1.pdf --out-pdf output/wz1/wz1_s4.pdf \
  --pages 1,2,5,10,20,40,60,80,100,120,140,160,180,200,210,215,218,220,221,222 \
  --out output/wz1/punct_span_residual.json --crops /tmp/punct_span/wz1 --sample 30

# wz7 8 页 sanity（gold 命中只算全部 gold，不是 FN）
/usr/bin/python3 src/tools/punct_span_residual.py --book wz7 \
  --src-pdf source_pdf/wz7.pdf --out-pdf output/wz7_full/wz7_full_v51.pdf \
  --pages 57,97,159,704,705,830,898,1718 \
  --gold src/test/bench/punct_gold_v1_base.json \
  --out output/wz7_full/punct_span_residual_gold.json --crops /tmp/punct_span/wz7 --sample 30
```

单书 ghbq 104 页约 35 秒、wz4 30 页约 12 秒、wz1 20 页约 9 秒；纯 CPU（fitz+numpy+scipy），无 GPU。

## 结果表

| 书 | 页数 | 候选 | by_class | 抽样真标点 |
|---|---:|---:|---|---:|
| ghbq | 104 | 1672 | comma454 / enumeration_comma557 / period552 / ring109 | 3/30 |
| wz4 | 30 | 838 | comma296 / enumeration_comma412 / period115 / ring15 | 5/30 |
| wz1 | 20 | 944 | comma416 / enumeration_comma364 / period137 / ring27 | 3/30 |
| wz7 sanity 8页 | 8 | 114 | comma59 / enumeration_comma42 / period13 | 未逐块（仅 gold 粗对齐） |

## 逐类误报（抽样判断，非全量）

| 类 | 抽样数（估） | 真标点 | 误报主因 |
|---|---:|---:|---|
| period | 18 | 4 | 汉字点/OCR 句点碎片 |
| comma | 24 | 3 | 汉字撇/捺、字体边缘 |
| enumeration_comma | 28 | 2 | 汉字部件、图表符号 |
| ring | 8 | 1 | 汉字方框/圈号 OCR 已识别 |
| quote/bracket/dash/other | 12 | 1 | 字形边缘/图版/元数据 |

总计真标点 11/90；95% CI 按 Wilson 约 7%–21%。

## 反例

- 汉字点/撇/捺：尺寸窗不能区分，且产物字形与扫描字体字形不同→边缘残差被误报；抽样中大量 `点`、`撇` 碎片即此。
- 页码/书眉/脚注号：用页 5%/95% 边带过滤后仍会漏进封面/版权页（ghbq 前 30 中有 PDF 元数据/发行信息），需按页面结构排除。
- 图版：源 PDF 整页扫描图本身就是 image block；代码只排除 **面积 <50% 页面** 的 image block，整页扫描图必须靠版心/文字区域排除，仍可能漏进插图页。
- **关键反例（判定依据）**：strict glyph 距离 0.08 字宽时，真标点在源图上紧邻前字，bbox 与 glyph 外扩框重叠 → 全部被过滤；放宽后大量字体边缘残差涌入 → precision 12%。

## 与 gold 的 sanity

`output/wz7_full/punct_span_residual_gold.json`：8 页 114 候选，对 gold **全部 698 条标点**命中 14（2%）。
这只是“候选是否落在任一 gold 标点附近”的粗检查，**不是 34 个纯 FN 的命中率**；gold 文件没有 FN 子集坐标，不能把 2% 冒充 FN 覆盖率。

## 最终判定

1. span 级残差能“找到一些源图有墨但产物无字形的位置”，但**不能稳定区分真漏标点**；
2. 真标点比例 12.2%（<30%），**补形路线判死**；
3. 不应把 glyph bbox 直接用于补形；应转 OCR 参数/上下文推断，或先做字符级 OCR bbox 质量提升。
