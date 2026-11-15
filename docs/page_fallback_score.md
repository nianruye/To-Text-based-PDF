# 不可靠页自动降级（t340）

## 规则

- 依据 layout blocks：`vertical_text >= 2` 且 `image >= 1` → 判为手写/影印不可靠页，`_page_img_full=True`，整页贴源图 + 文本 3Tr。
- p5 命中：layout 有 2 个 vertical_text + 1 image；p18 无 vertical_text，且走 structured_toc 特殊路径，不降级。
- fallback 清单写 `<out>.fallback.json`；当前 build 临时路径。

## 样本

| 页 | vertical_text | image | 降级 |
|---|---:|---:|---|
| wz9 p5 | 2 | 1 | 是 |
| wz9 p6/p7/p8 | 0 | 0 | 否 |
| wz9 p18 | 0 | 0 | 否 |
| ghbq p15/p23 | 0 | 0 | 否 |
| wz1 p20 | 0 | 0 | 否 |

## 验收

- 删除 `config/books/wz9.json image_pages` 后，wz9 p5 **1图 + 187字文本层**；p18 41行结构目录；页数82。
- ghbq 104 逐页 diff0。
- 其余书未逐本重跑；规则仅 vertical_text>=2 触发。
- 输出 output/uploaded/wz9_auto.pdf；p5/p18裁片。

未改 gold/punct_eval；未 push/commit。

---

## 追加：三项墨迹信号的实测结论（2026-11-15，captain 实测）

原计划用三项墨迹信号做「手写页检测」，**实测全部不成立**：

### 实测数据（300dpi 灰度）

| 书 | 页 | 类 | 墨迹行带 | OCR 行 | 行比 | 笔画中位 | **笔画 CV** | **乱码率** | **墨覆盖率** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wz9 | 5 | **手写** | 2 | 12 | **6.00** | 5.00 | 0.840 | 0.0000 | 0.069 |
| wz9 | 6 | 印刷 | 17 | 18 | 1.06 | 2.00 | 0.657 | 0.0000 | 0.017 |
| wz9 | 7 | 印刷 | 21 | 21 | 1.00 | 2.00 | 0.561 | 0.0000 | 0.020 |
| wz9 | 8 | 印刷 | 26 | 26 | 1.00 | 2.00 | 0.379 | 0.0000 | 0.023 |
| wz8_1 | 10 | 印刷 | 23 | 23 | 1.00 | 4.00 | **0.828** | 0.0000 | 0.050 |
| wz8_1 | 18 | 印刷 | 21 | 21 | 1.00 | 5.00 | **0.837** | 0.0000 | 0.071 |

**结论**：

| 信号 | 是否可区分 | 原因 |
|---|---|---|
| 笔画宽度方差 | ❌ **不可** | 手写 0.840 vs 印刷 0.379–0.837 —— 印刷页也是扫描件，方差同样大 |
| 乱码率（`�`） | ❌ **无信号** | 全部样本均为 0，OCR 不输出 U+FFFD |
| 墨迹覆盖率 | ❌ **不可** | 手写 0.069 vs 印刷 0.017–0.088 —— 区间重叠 |
| OCR 行 / 墨迹行带 | ⚠️ 可区分但成因偶然 | 6.00 vs 1.00；但手写页墨带只有 2 是因为两本书照片是实心暗块 |

另外：**OCR 原始输出不含任何置信度字段**（`spotting_*.json` 的 `result` 里只有
`layoutParsingResults` / `prunedResult` / `dataInfo`，无 `score`/`confidence`），
所以「按 OCR 置信度判可靠页」这条路也不通。

### 现行判据的真实依据（比原以为的更站得住）

`vertical_text >= 2 且 image >= 1` 的实际含义是：**横排书里出现竖排文字块**。

| 页 | 版面标签 | 为什么该降级 |
|---|---|---|
| wz9 p5 | `vertical_text` ×2（手写内容被读成竖排）+ `image` | 手写稿被当文字重建 → 乱码 |
| wz8 p3 | `vertical_text` ×2（`朱有志主编` 等竖排封面文字）+ `image` | 竖排封面艺术字 → 重建会错 |

**即：版面模型判定该页内容方向与本书主方向不一致 → 该页不可靠 → 整页贴图。**
这是**有原则的判据**，不是巧合。已在代码里把 reason 从 `handwriting_layout`
改名为 `orientation_mismatch`，如实反映依据。

### 仍缺（未做）

1. 降级清单只写 `<out>.fallback.json`，**未进 report/gate**（用户看不到哪几页是图）
2. 只覆盖「方向不一致」一类异常；**乱码页/表格页/公式页**未覆盖
3. 6 本书未逐本重跑（靠「无 layout json 不走该路径」推断无影响）

## 报告可见性（t343）

- report.json：`page_fallback` / `page_fallback_count`；wz9 p5 -> `[{"page":5,"reason":"orientation_mismatch(vt=2,img=1)"}]`。
- gate.md：「整页贴图页」一节；wz9 `p5(orientation_mismatch(vt=2,img=1))；合计 1 页`；ghbq 为「无」。
- stdout：`[scan2pdf] 整页贴图 1 页: 5(orientation_mismatch(vt=2,img=1))`。
- fallback 清单复制到产物同目录 `<out>.fallback.json`。
- ghbq report page_fallback=[]，104页；wz9 82页。
- 产物 output/uploaded/wz9_vis.pdf + report/gate。

---

## 追加：全书保真模式（fidelity_mode）实验结论（2026-11-15）

**动机**：wz2/wz3 的标定/行距不可靠，重排产物行距偏松 11~22%；对这类书，
「扫描件 + 隐形文本层」可能优于「重排但行距错」。

**实现**：`config/books/<book>.json` 的 `{"fidelity_mode": true}` → 全书每页走
`_page_img_full`（源页 raster 背景 + 文字 3Tr 隐形）。复用已有的逐页贴图路径，
只加一个全局开关（`build_geom.py` 一行）。

**实测（wz3，850 页）**：

| 指标 | 结果 | 评价 |
|---|---|---|
| 页数 1:1 | 850 = 850 | ✅ |
| 视觉保真 | 源扫描件本身 | ✅ |
| 文件大小 | **511 MB** | ❌ 过大（正常重排 ~2.8 MB）|
| gate | **REJECT / pitch_below_floor** | ❌ 未解决 |
| 文本层 | 909 字/页，字号 14.45pt | ⚠️ 不是 1pt，且位置仍来自**有问题的标定** |

**结论：当前实现不可交付**，两个硬问题：

1. **体积**：全页 raster 未做 DPI/压缩优化（511MB vs 2.8MB）。
2. **文本层仍用标定后的位置** → gate 仍按错误的行距判失败，且隐形文字与背景图
   **不对齐**（搜索命中位置会偏）。

**要成为可交付的保真模式，还需要**：
- ① raster 降 DPI/JPEG 质量（目标 <100MB / 850 页）
- ② 隐形文本层改为**按源 OCR 坐标原始位置**放置（绕过标定），使文本与背景对齐、
  且 pitch 由构造保证与源一致
- ③ gate 对保真模式改用「页数 1:1 + 文本层与源 OCR 对齐」口径，而不是 span pitch

**已清理**：实验产物与 wz3 配置已删除，工作树恢复。`fidelity_mode` 开关保留
（默认关闭，供后续正式实现使用）。
