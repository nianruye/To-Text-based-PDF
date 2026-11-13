# D 参数逐页定性 + p97 钉回贴图（t267）

## 结论（no-go）

**D 参数不值得采用。**

- 94 页 diff 逐页定性：**标点变好 17 处 / 变坏 34 处**，X/Y = **0.50**，远低于 3:1 判定线；
- **非标点差异 72 页、字符差 286**（旧 vs D），未证明不引入内容错误；
- p97 用 `data/ghbq/page_image_pages.json` 钉回贴图后 **image=1**，但**文本层为空（0 字）**，不是旧版的「1 张源图 + 全文本 1pt 可搜」；页码 85 只在图像里，不可检索；
- p12 仍是点线非三栏，且 D 版出现 ASCII `,`，比旧版标点更差；
- 因此即使接受 p97 贴图修复，D 的全书 text diff 仍不达标 → **不写 `ocr_params.json`，不写 `page_image_pages.json`**。

## 一、p97 钉回贴图实验

临时写入（实验后已删除；最终不落盘）：

```json
{"pages": [97], "reason": "OCR 页码误识(85→95)+脚注错位;保持源页贴图"}
```

重建：
```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq/ocr_param_exp/D_full/ghbq_D_full_pinned.pdf \
  --data-dir output/ghbq/ocr_param_exp/D_full --skip-ocr --force
```

实测：
- p97 `get_images()` = **1**（源页贴图回来了）
- p97 文本层 `get_text()` = **空**（0 字符）；旧版 p97 是 **1 图 + 468 字 @0.996pt**
- 所以「整页贴图」恢复，但「全文本 ≤1pt 不可见 + 单页码 85」**没有恢复**；页码只能在图里看见，不能搜索。
- 视觉对比：`output/ghbq/ocr_param_exp/D_full/compare_p97_pinned.png`

结论：页级贴图机制能恢复图，但不能恢复旧版的 1pt 文本层；要完全达到旧 p97 行为还需要渲染侧补文本（本任务不改代码），因此 p97 不能算「钉回即等价」。

## 二、94 页 diff 逐页定性

输出：`output/ghbq/diff_old_vs_D.json`（每页 `{page,better,worse,other,chardiff,examples}`）。

方法：逐页 `get_text()` → 提取标点序列（ASCII 标点先归一为全角用于对齐）→ SequenceMatcher：
- better：新插入标点 / ASCII→全角；
- worse：旧标点删除 / 全角→ASCII / 类型替换；
- other：去掉全部标点后的非标点文本差异（错字/字增减/顺序）；
- 字符差：非标点序列的编辑量。

全书汇总：

| 项 | 数量 |
|---|---:|
| diff 页 | 94 |
| 标点变好 X | **17** |
| 标点变坏 Y | **34** |
| X/Y | **0.50**（要求 ≥3） |
| 非标点差异页 Z | **72** |
| 非标点字符差 | **286** |

典型 worse 页：p44（`······` 丢失）、p104（引号/逗号重排、90 字符非标点差）、p42/p47/p50（`···` 代替 `……`）、p86（引号/逗号丢失）、p28/p41（括号丢失）。p97 在 pinned 后文本 0，归 other。

**判定：X/Y=0.50 < 3，且 nonpunct 286/72 页，D 不达标。**

## 三、抽样人眼确认

裁片目录：`output/ghbq/ocr_param_exp/diff_crops/`（29 张，4×，红框=OCR 行 bbox）
- better 10 张：`better_00..09`
- worse 10 张：`worse_00..09`
- other 9 张：`other_00..08`（源页可用样本少 1 张，报告如实登记）

源图与旧/新文本对照已在 `diff_old_vs_D.json` 的 examples；裁片仅给行级上下文，不伪造字符框。人眼可见：
- better 例：旧行 ASCII `,`，新行全角 `，`（如 p80 的逗号）；
- worse 例：`……` → `···`、引号/括号被删（p44/p50/p28）；
- other 例：分页/行序不同导致文本块位移。

## 四、p12 复核

- 旧 p12：点线 + 全角逗号（`5. 否定公有制为主，鼓吹`）。
- D p12：仍点线（非三栏），且 **ASCII 逗号**（`5. 否定公有制为主, 鼓吹`）。
- 因此 p12 的**目录三栏/点线是 TOC 渲染器问题**（与 OCR 参数无关）；**ASCII 逗号是 OCR 侧变差**。D 对 p12 是**净变坏**，不能靠 D 修复目录。
- 对比图：`output/ghbq/ocr_param_exp/D_full/compare_p12.png`

## 五、最终判定与下一步

**D 不可用：**
- X/Y 0.50 < 3；
- nonpunct 286 字符差；
- p97 钉图后文本层为空，未达旧行为；
- p12 标点变坏。

**下一步建议（按优先级）：**
1. 不做 A/D 融合，先修 p12 TOC 三栏（渲染问题，独立于 OCR）；
2. 做逐页 A/D 选择器：只对 A 输出 ASCII 逗号且 D 输出全角逗号的行采用 D，其余保留 A；这是行级融合，不是全书替换；
3. 对 p97 这类「D OCR 读成正常行但页码/脚注错」的页，继续走自动贴图；但需要渲染侧保留 1pt 文本层（当前 pinned 无文本，需产品修复）；
4. 维持现有 `ghbq_p97v2.pdf` 为交付基线，不写 `ocr_params.json`/`page_image_pages.json`。

## 六、自检

- p97 pinned：image1 / text0 / 页码视觉85；不满足旧版文本层。
- 94 页 diff JSON 完整；X17/Y34/Z72。
- 裁片 29 张；p12/p97 对比图 4 张。
- 未改产品代码/data/gold/punct_eval；临时 page_image_pages.json 已删除；未 commit。
