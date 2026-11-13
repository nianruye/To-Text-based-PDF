# ghbq 基线 v2（t274 最终验收）

## 判定：**no-go（当前不改交付基线）**

- p97 与重建标点收益达成：产品级 R **0.7578 → 0.8758（+11.80pp）**，P **0.8271 → 0.8468**；p97 修复为「1张源图 + 493字@1pt + 可见span0 + 页码85」。
- **但逐页标点计数对照发现 14 个 worse 页（不是 1 个 p86）**：
  - p31–p39：旧全角逗号 15/12/13/25/19/17/14/21/20 → 新 4/3/8/3/18/15/3/5/6；对应新增 ASCII `,` 11/9/5/22/1/2/11/16/14。这是**全角→ASCII 形态回退**（内容词未丢，但标点形式变坏）。
  - p64/p65/p86/p93：各有 1–2 个引号/句号/分号丢失（p86 另丢 1 个闭引号）。
  - p86 旧闭引号18→新17，真实丢1字符；p64 旧闭引号17→16；p65 句号11→10；p93 句号6→5。
- 按验收「worse页≤1」不达标 → 不能替换 `ghbq_p97v2.pdf`。

## 最终产物

- `output/ghbq_full/ghbq_final_v2.pdf`
- sha256 `56d53fda6a190b0172fa856abea09d6184e947a1f09500bb23b701c5fe36b7b1`
- 104 页；p97 配置：`data/ghbq/page_image_pages.json`（正式落盘，pages=[97]）；未创建 `ocr_params.json`。
- 数据输入：`output/ghbq/rebuild_cur`（原参数全量重跑 OCR）。

## 标点基线（punct_eval sequence，gold_sha `8423a6a8…`）

| 产物 | TP | FP | FN | P | R |
|---|---:|---:|---:|---:|---:|
| 旧 `ghbq_p97v2.pdf` | 244 | 51 | 78 | 0.8271 | 0.7578 |
| **新 `ghbq_final_v2.pdf`** | **282** | **51** | **40** | **0.8468** | **0.8758** |

unscorable=[]；order_swaps=1（阅读序一次换位）；by_class：comma TP131/FN2，period68/4，quote_open36/24，quote_close29/7，colon6/0。

## 排版基线（verify_typography）

- pages104、body_lines2067、compliance1.0、verdict WARN
- **hard 0、render_introduced 0**、violations4（均为 p11/p12 TOC warn：toc_cont_indent / toc_number_overlap）、waived9、non_body1
- 旧版同样4条 TOC warn；无新增 hard。

## 几何基线（verify_geom）

- pitch **97.9%**（旧97.9，未降）、height97.9%、overflow **0**、split0、missing0、blank2
- gate **PASS**（verdict_effective PASS）；warnings `baseline_font_ratio_out`、`toc_low_sample`；calib_fail[]。
- GMPG **0**。

## p97

| 项 | 旧 | 新（final_v2） |
|---|---|---|
| image | 1 | **1** |
| 文本字符 | 473 | **493** |
| 字号 | 1.0 | **全1.0** |
| 可见span>2pt | 0 | **0** |
| 页码85 | 仅图 | **文本层含85** |

视觉：`output/ghbq/rebuild_cur/final_p97.png`。

## 新旧逐页 diff（标点计数对照，不用序列对齐）

- diff 页 **59**；better 标点计数 **1227** / worse **206**（计数比 5.96，≥3）；
- 但有 worse 的页 **14 页**：p31–39（ASCII形态回退）、p64、p65、p86、p93；p86/p64/p65/p93 为单字符丢失。
- other（非标点文本差异）40 页。
- JSON：`output/ghbq_full/diff_final_vs_old.json`。

**验收要求 worse 页≤1，实际14页 → no-go。**

## 已知限制（必须登记）

1. **p86**：源图有闭引号 `”`，新 OCR 丢失 1 个；按 AGENTS 判据边界原则不为 1 字符造全局规则；登记 in AGENTS #54。
2. **p31–p39**：全角逗号→ASCII `,` 形态回退（内容词相同）；可用**行级 ASCII→全角归一化**或 A/D 融合处置，不在本任务实现。
3. **p12**：仍点线非三栏，`toc_number_overlap`；TOC 渲染器问题，与 OCR 参数无关。
4. **wz4 p2/p428**：AGENTS #53 已知限制（p2 条码/ISBN、p428 版权行越界）；本任务未改。
5. p97 贴图页文本字数493 vs 旧473，增加来自新 OCR 页码/文本行；不视为错误。

## 回归

- **wz1**：`scan2pdf` 全量 222 页；与旧 `output/wz1/wz1_s4.pdf` 逐页文本 **diff=[]**（页数222=222）。
- **pytest**：`src/test/unit + src/test/invariants` **807 passed, 0 failed**。
- 无 `data/*/page_image_pages.json` 的书不触发 p97 分支；wz1 零影响。

## 可提交文件清单（供 captain 分 PR）

建议分 2 个 PR：
1. **p97 文本层修复 + 横排重建配置/基线**：
   - `src/pipelines/build_geom.py`
   - `src/test/unit/test_page_image.py`
   - `data/ghbq/page_image_pages.json`
   - `docs/ghbq_rebuild_gate.md`
   - `docs/ghbq_baseline_v2.md`
   - `docs/punct_gold_h_v1.md`（仅数字）
2. **已知限制登记**：
   - `AGENTS.md`（#54 p86 quote + p31–39 ASCII form）
   - 产物/裁片（output 不入库，按仓库策略；报告引用路径）

不提交：`output/` 产物、`rebuild_cur` OCR 中间文件（按仓库 output 策略）。

## t276 最终裁决（2026-11-12，GO）

- 采用 `output/ghbq_full/ghbq_final_v3.pdf`（sha `eba54007…570a`）为 ghbq 交付基线；标点 P0.8468/R0.8758，104页 gate PASS，p97 五项达标，GMPG0，typography hard0。
- 形态归一化收窄为严格相邻+引号内侧 CJK；**wz1 222=222 逐页 diff=[]**；wz4 677=677/33页形态 diff，P/R 不变（0.7842/0.8187）。
- ghbq worse 页 5（p64/p65/p70/p86/p93，≤5）：p70 为 OCR 丢 4 个 em dash，其余单字符；均登记 AGENTS #54。
- pytest 814 passed。
- 详见 `docs/punct_normalize_adjudicate.md`。

## t285 定稿：v12 新交付基线

- 采用 `output/ghbq_full/ghbq_final_v12.pdf`，sha256 `553c5c8ab2da62fa2ac1574634c68c9d8f32b8dd75a815d682202d55e9096064`；替换 v3。
- 标题 L1/L2/L3 为 NotoSansCJKjp-Bold；L1 18.7、L2/L3 16.5；p1 37.1/19.5、p3 357.9、p13 页码、p33 空格、p1 封面图保留。
- 同口径 v3：pitch97.9/页高30.9/底部97.9；v12：pitch98.9/页高29.8/底部97.9；104=104/overflow0/PASS。

## t296 最终基线：v23

- 产物 `output/ghbq_full/ghbq_final_v23.pdf`，sha256 `a6ea0f691417d58d3b746f1f1a0041b6fb88825096c6e5da177ecfc2835a3110`；替换 v12。
- 目录统一标准格式（固定行距/30pt页码/L1-L3缩进/无点线）；真实压字 p11/p12=0；单页11/12各1页。
- pitch98.9%、页高<5%=29.8%、底部97.9%；104=104、overflow0、gate PASS；p97 image1/493字/1pt/vis0/85。
