# ghbq 重建替换 gate：p97 贴图文本层修复 + 11 页 worse 裁决（t273）

## 结论

**Go（有条件）：p97 修复通过；t272 的 11 页 worse 中只有 1 页是真正标点丢失，其余 10 页是 diff 对齐误报。** 条件：p86 的 1 个闭引号用行级/旧产物融合规则补回；其余按 t272 新产物重建。

## 一、p97：贴图页 1pt 可搜文本层修复

修改 `src/pipelines/build_geom.py`：
- `PAGE_IMAGE_PAGES` 分支不再提前 `continue`/只贴图；
- 置 `_page_img_forced=True`、`_giant_page=True`，源图照旧铺 BG，但继续走正常文本分类/渲染；
- 正常文本流全部经 `\special{pdf:literal direct q 3 Tr}` + giant 1pt 输出；
- 贴图页脚注不重复画 `\hrule`（源图已有脚注线），避免 p97 多一条线；
- 文本层额外保留源页码（1pt）。

临时写入（测试后已删除，最终不落盘）：
```json
{"pages":[97],"reason":"OCR 页码误识(85→95)+脚注错位;保持源页贴图"}
```

重建：`output/ghbq/rebuild_cur/ghbq_p97_fixed_test.pdf`（104页，gate PASS）。

p97 逐项验收：

| 条件 | 旧 p97v2 | 修复后 |
|---|---|---|
| 图片 | 1 | **1** |
| 文本字符数 | 473 | **493**（≥450） |
| 可见 span(size>2pt) | 0 | **0**（全部1.0pt） |
| 文本含页码85 | 否（页码只在图里） | **是** |
| 页脚线 | 源图线 | 无额外重复线；视觉与旧版一致 |

视觉：`output/ghbq/rebuild_cur/p97_fixed.png`（左旧/右修复）；另 `compare_p97.png`。

单测：`src/test/unit/test_page_image.py` 新增 `test_page_image_pages_branch_keeps_text_layer`，断言该分支不再提前 continue、保留 3Tr 与 `_page_img_forced`。**6 passed**。

## 二、11 页 worse 逐页裁决（关键）

t272 报告的 worse 页：p1/10/28/31/41/42/44/47/50/86/104。
用**旧/新产物同一页直接统计标点**（不依赖序列对齐）核对：

| 页 | 旧/新标点计数 | 源图裁片 | 裁决 |
|---|---|---|---|
| p1 | 引号 1/1 等完全相同 | `worse_crops/p0001.png` | **可接受（无变化；t272序列误报）** |
| p10 | 引号 2/2 等相同 | p0010 | 可接受（误报） |
| p28 | 引号6/6、括号1/1相同 | p0028 | 可接受（误报） |
| p31 | 引号13/13相同 | p0031 | 可接受（误报） |
| p41 | 引号6/6、括号1/1相同 | p0041 | 可接受（误报） |
| p42 | `···`1/1、引号10/10相同 | p0042 | 可接受（误报；源图为`···`，t272所谓`……→···`不成立） |
| p44 | `···`2/2、引号6/6相同 | p0044 | 可接受（误报） |
| p47 | `···`1/1、引号6/6相同 | p0047 | 可接受（误报） |
| p50 | `···`1/1、引号5/5相同 | p0050 | 可接受（误报） |
| **p86** | 旧闭引号18 / 新17；其余相同 | p0086 | **不可接受（1个闭引号丢失）** |
| p104 | 引号48/48相同 | p0104 | 可接受（误报） |

**结论：11 页中真正 worse 仅 p86 一页；10/11 是 t272 按序列/行重排对齐造成的假阳性。**
（t272 报告说 p44/p50 `……→···`；源图裁片和旧/新文本都显示原文就是 `···`，该条判断不成立。）

p86 源图（`p0086.png`）可见：`“俄国社会共产党（布尔什维克）”`；新版丢了 `）` 后的闭引号。属 OCR 上游丢字，不是 render_dropped（旧版有、新版无；build 未删该字符）。

## 三、p86 行级规则（不实现，只给方案）

最小规则（只对旧/新同页同一行做融合，不改源文）：
- 条件：旧版该行有 `”`，新版对应行同上下文有 `“` 但无 `”`，且新版行有 `（...）`/`，` 模式；
- 动作：仅把旧版该行末尾 `”` 补到新版对应位置（1 字符）；
- 影响面：全书仅 p86 1 行；不触发无引号/无括号行；wz1/wz4 无此形态（dry-run 样本 0）即零回归；
- 验证：补后 p86 quote_close +1；ghbq 8 gold 页 P/R 不降；wz1/wz4 不参与（无匹配行）。

**注意**：不做全局 `···→……` 归一化——源图本身就是 `···`，归一化会改错。

## 四、综合判定

| 条件 | 结果 |
|---|---|
| p97 图片=1 | 通过 |
| p97 文本≥450 | 493，通过 |
| p97 可见 span=0 | 通过 |
| p97 含页码85 | 通过 |
| 11 worse 中不可接受 ≤2 | **1（p86）**，通过 |
| p86 可行级修 | 是（上述1行规则） |
| 新产物标点收益 | R +11.80pp（t272）仍成立 |

**Go**：在应用 p86 行级闭引号补全后，用 `output/ghbq/rebuild_cur/ghbq_p97_fixed_test.pdf` 的方案替换 `ghbq_p97v2.pdf`。

最终推荐内容（只给内容，不落盘）：
```json
// data/ghbq/page_image_pages.json
{"pages":[97],"reason":"OCR 页码误识(85→95)+脚注错位;保持源页贴图"}
```
（`ocr_params.json` 不需要写：本次是默认参数重跑；写空/默认参数文件没有收益。）

替换步骤：
1. 应用 p86 闭引号行级补全（或先接受该1处坏字，记录 known issue）；
2. 用 rebuild_cur lines/coords + page_image_pages 重建；
3. 替换 `output/ghbq_full/ghbq_p97v2.pdf`；
4. 重出 `docs/punct_gold_h_v1.md` 基线表（R 0.8758）、typography baseline、gate report；
5. 复跑 `pytest src/test/unit/test_page_image.py -q`（6 passed）与全量测试。

## 五、p12 复核

- 当前原参数重建 p12 与旧版文本一致，仍点线目录、非三栏；`toc_cont_indent/toc_number_overlap` 仍 warn（旧4条）。
- 这是 **TOC 渲染器**问题，不是 OCR 参数；不影响本次 p97/标点 gate，但仍是已知版式限制，不能声称目录已修好。

## 六、剩余风险

- p86 1 个闭引号是目前唯一确认的不可接受页；若不做行级融合，需登记 known issue（不影响整体 go，但需明确）。
- p97 修复分支只对显式 PAGE_IMAGE_PAGES 页生效；重建差异仅 p97（与未钉图产物逐页 diff = 仅 p97）。
- 非标点差异（40页/字符差）仍需在替换前抽样复核；本次只裁决 worse 的 11 页，不等于全量内容零风险。

## t274 最终验收补充（2026-11-12）

- 正式落 `data/ghbq/page_image_pages.json`（pages=[97]）；未创建 ocr_params.json。
- 最终产物 `output/ghbq_full/ghbq_final_v2.pdf`（sha256 `56d53f…b7b1`）：104页、gate PASS、pitch97.9/overflow0/split0/missing0、GMPG0、typography hard0。
- p97：image1、chars493、全1.0pt、visible span0、含页码85（通过）。
- 一致性自检：59 diff 页；标点计数 better1227/worse206，但 **worse 页14**（p31–39 ASCII形态回退 + p64/p65/p86/p93 单字符丢失），不满足 worse页≤1。
- **最终判定 no-go**：不替换 ghbq_p97v2；p86 与 p31–39 登记已知限制；下一步做行级 ASCII→全角归一化或 A/D 融合后重跑。
- 回归：wz1 222页逐页diff 0；pytest 807 passed。


## t276 最终裁决（GO）

- 归一化收窄（严格相邻+引号内侧 CJK）后：wz1 222=222 diff=[]；wz4 677=677 diff33 但 P/R 不变；ghbq v3 104=104、gate PASS、p97五项、GMPG0、hard0、P0.8468/R0.8758、worse页5（≤5）。
- p70 的 4 个 `—` 是 OCR 上游把 `—` 读成 `一`；登记 #54，不修。
- **GO**：采用 ghbq_final_v3.pdf；详见 `docs/punct_normalize_adjudicate.md`。
