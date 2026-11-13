# ghbq 标题定稿：Bold + v12 基线（t285）

## 结论：**GO**（标题 Bold 生效，门禁与 v11 持平/不回退）

- `paragraph_title` L1/L2/L3 均为 **NotoSansCJKjp-Bold**：p61 L1 18.7pt、p15 L2 16.5pt、p33 L1 18.7/L2 16.5、p14/84 L1 18.7。
- 与源书粗黑体匹配；单 span、无重复叠印（非假粗）。
- v3 同口径对照（同一 `lines_corrected.json`）：

| 产物 | pitch<3% | 页高<5% | 底部占位<8% |
|---|---:|---:|---:|
| v3 | 97.9% | 30.9% | 97.9% |
| v12 | **98.9%** | **29.8%** | **97.9%** |

- v12 达标：pitch≥98.9、页高≥29.8、底部占位≥97.9、104=104、overflow0、line1to1 PASS、退出码 PASS。

## 字重证据

- 修改前（v11）：`NotoSansCJKjp-Regular`，18.7/16.5pt。
- 修改后（v12）：`NotoSansCJKjp-Bold`，18.7/16.5pt；命令：
  `/usr/bin/python3 -c "import fitz; ... p[60] ..."` → `[(18.7,'NotoSansCJKjp-Bold'),(18.7,'NotoSansCJKjp-Bold')]`
- 实现：标题 `_hbold='\\bfseries'` 放在 `\CJKfamily{heiti}` **之前**（顺序反了会落到 NotoSerif）；仅 `lay_head`（paragraph_title）生效，doc_title 不强制。
- 未用多重描边/重复叠印。

## 保留项

- 字号分层：L1=18.7、L2/L3=16.5；p1 封面 `戈尔巴乔夫与`37.1、`王正泉`19.5；p3 扉页 357.9 居中；p13 页码；p33 空格；p1 封面图。
- 12 处目标仍标题；L3 抽样裁片在 `output/ghbq/heading_crops/`。
- `p61/p15/p33` 三版裁片：`p0061_{source,v3,v12}.png`、`p0015_*`、`p0033_*`。

## 回归

- wz1 222=222 diff[]；wz4 677 gate PASS（33页形态 diff 为 t276 接受项）；wz2 历史 66.7% 不处理。
- pytest：test_toc 8 passed；全量（待最终）815 passed。
- p97 image1/493字/1pt/vis0/85；GMPG0。

## 定稿

- 新基线：`output/ghbq_full/ghbq_final_v12.pdf`
- sha256 `553c5c8ab2da62fa2ac1574634c68c9d8f32b8dd75a815d682202d55e9096064`
- 已同步 `docs/ghbq_baseline_v2.md`、`docs/punct_gold_h_v1.md`。

## 可提交文件清单（captain 统一提交）

1. `src/pipelines/build_geom.py`（标题 Bold + L1 分层）
2. `src/tools/scan2pdf.py`（通用标题守卫，t279）
3. `src/test/unit/test_toc_layout.py`（层级测试）
4. `docs/ghbq_headings.md`
5. `docs/ghbq_baseline_v2.md`
6. `docs/punct_gold_h_v1.md`

不提交 output/；不 commit（captain 统一）。
