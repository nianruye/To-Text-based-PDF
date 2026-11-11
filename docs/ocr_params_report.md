# OCR 参数化 + 页脚重 OCR 实验（t219）

> 状态：实现 + 实验报告；**不改默认参数**；未 commit。
> 范围：`src/tools/ocr_book.py` / `src/tools/scan2pdf.py` / 单测；本文件独立，不合并 docs/scan2pdf_v1.md / AGENTS.md。

## 1. 参数表

| 参数 | CLI | `data/<book>/ocr_params.json` | 默认 |
|---|---|---|---|
| maxPixels | `--ocr-max-pixels` | `max_pixels` / `maxPixels` | **2822400** |
| minPixels | `--ocr-min-pixels` | `min_pixels` / `minPixels` | **147384** |
| orientation | `--ocr-orientation` (0/1) | `orientation` / `useDocOrientationClassify` | **0** |
| unwarp | `--ocr-unwarp` (0/1) | `unwarp` / `useDocUnwarping` | **0** |
| layoutShape | `--ocr-layout-shape` | `layout_shape` / `layoutShapeMode` | **auto** |

优先级：**CLI > data/<book>/ocr_params.json > 默认**（逐项）。解析函数 `ocr_book.resolve_ocr_params()`；无文件时路径/SHA 为 null。

## 2. 可复现/审计

- `ocr_book` 每批写 `jobs.json`：`state/jobId/pages/params`；`manifest.json` 每批同含 `params/jobId`。
- `<out-dir>/ocr_params_effective.json`：`{params, sources, path, sha256}`（sources 标注 `cli|book_data|default`）。
- `scan2pdf` OCR 后 report 增 `ocr_params`（读 effective）与 `ocr_jobs`（batch→jobId）。
- 默认参数 payload 与 HEAD 等价：单测 `test_payload_default_equals_head` 对旧 payload 字典逐字节相等。
- **`--skip-ocr` 口径**：不执行 OCR 时 report 的 `ocr_params`/`ocr_jobs` 为 **null（缺失）**，不伪造生效参数（当前无 data-dir 回退读取；仅 OCR 运行写 effective/jobs）。
- **确定性 env**：`fit_common.render()`、`scan2pdf` 的 build/verify/OCR 子进程均固定 `PYTHONHASHSEED=0`；report 顶层 `env.PYTHONHASHSEED`、OCR manifest 的 `env.PYTHONHASHSEED` 可审计。
- 两次独立构建（ghbq，当前工作树，同输入）：文本逐页 **0 diff**、gate 均 **95.9%**、chars 43,913；PDF md5 分别 `343aa7a8…` / `d8390a51…`（差异仅 PDF 元数据/ID，文本/门禁一致）。
- 实验 jobId（ghbq 8 页）：
  - footer strip 4.0M：`113871012101722112`
  - full 2.82M/ori0：`113871176647737344`
  - full 2.82M/ori1：`113871456832237568`
  - full 4.0M/ori0：见 `tmp_vert/t219/ocr_mp400_ori0/jobs.json`
  - full 4.0M/ori1：见 `tmp_vert/t219/ocr_mp400_ori1/jobs.json`

## 3. T3：页脚条带重 OCR

- 抽页（0-based key）：`[2, 18, 30, 42, 54, 66, 78, 90]`（1-based 3/19/31/43/55/67/79/91）。
- 页脚条带：源页底部 10%，300dpi 渲染裁切 → 8 页 PDF（595×86.9pt/页）。
- 参数：`maxPixels=4000000`，其余默认；`--mode spotting`。
- 结果：**页码命中 7/7**（page2 封面无页码；其余 7 页全部识别出 layout number：7/19/31/43/55/67/79）；条带 OCR 总字符 13（仅数字/页脚）。
- 对照：layout number 覆盖全书 **97 页**；本实验抽样 7 个有号码页全部命中，未做全书重跑（默认 OCR 的页码缺口 96/104 属于正文页整页识别问题，不是页脚条带不可读）。

## 4. T3b：整页 OCR 参数矩阵（同 8 页）

| maxPixels | orientation | 非空白字符 | 含空格字符 | 页码命中 | 与校正表一致行 | p3 标题 OCR |
|---|---|---|---|---|---|
| 2,822,400 | 0 | **3180** | 3180 | 7/7 | 0/2 | 马尔巴乔夫与 / 一人道的民主的社会主义” |
| 2,822,400 | 1 | **3190** | **3204** | 7/7 | **2/2** | **戈尔巴乔夫与 / “人道的民主的社会主义”** |
| 4,000,000 | 0 | 3180 | 3180 | 7/7 | 0/2 | 马尔巴乔夫与 / 一人道的民主的社会主义” |
| 4,000,000 | 1 | 3180 | 3180 | 7/7 | 0/2 | 马尔巴乔夫与 / 一人道的民主的社会主义” |

结论（**不改默认**）：
- **页脚条带重 OCR 有明确收益**：7/7 页码命中（默认整页对页码 96/104 有缺口，可作为后续“页脚专项重跑”候选）。
- **orientation=1 对标题页有效**：2.82M 下 p3 两条校正文本均被 OCR 正确识别（0→2/2），字符 +10。
- **maxPixels 4.0M 无额外收益**，且 4.0M+orientation=1 本样本丢失标题修正（0/2）；本样本推荐 **2.82M + orientation=1**（标题页场景），不建议全局改默认。
- 页脚条带建议单独作为“重 OCR 通道”实验：4.0M + bottom 10% 裁切，不改主 OCR 默认。

## 5. 零回归（两种口径）

### 5.1 参数化本身零回归（当前工作树）

- 参数只作用于 OCR 请求；`--skip-ocr` 构建路径不读参数 → 不改变 build 输入。
- 固定 `PYTHONHASHSEED=0` 后，ghbq：不传新参数 vs 显式传 5 个默认值 → **104=104、chars 43,913 相同、逐页文本 0 diff、gate 95.9%=95.9%**；两次独立不传参数构建亦 **0 diff/gate 相同**（md5 差异仅 PDF 元数据）。

### 5.2 干净 HEAD 对照（不含 t208/t218 未提交改动）

- 用 `git worktree` HEAD（`70a9d70`）的 `fit_positional.py` + `verify_geom.py` 直接构建/验证当前数据：
  - ghbq 104 页：**pitch 96.8%**、104=104、PASS；
  - wz4 677 页：**pitch 99.6%**、677=677、PASS。
- 当前工作树（含 t208/t218 未提交改动，t221 回退中）scan2pdf 实测 gate：ghbq **95.9%**、wz4 **99.4%**；根因在 `verify_geom.py`/geometry 未提交改动（同一 HEAD 产物用当前 verify → 95.9%，用 HEAD verify → 96.8%），不是 OCR 参数化。t221 落地后应回到 96.8/99.6。
- 验收口径按 captain 指示采用「**参数化本身零回归**」（5.1），并以干净 HEAD 数字（5.2）作目标对照。

## 6. 单测

- `test_ocr_book.py`：10 passed（payload 默认等价、CLI>book>default 优先级、默认无文件、payload 自定义）。
- `test_scan2pdf.py`：35 passed（含 OCR flags 透传、report `ocr_params`/`ocr_jobs` 字段）。
- 合计 **45 passed**（本任务相关）。

## 7. 复现

```bash
# 页脚条带（示例）
/usr/bin/python3 src/tools/ocr_book.py --book ghbq --input tmp_vert/t219/strip8.pdf \
  --out-dir tmp_vert/t219/ocr_strip --mode spotting --pages 1-8 --ocr-max-pixels 4000000 --resume
# 整页矩阵（orientation 0/1 × 2.82M/4.0M）
/usr/bin/python3 src/tools/ocr_book.py --book ghbq --input tmp_vert/t219/full8.pdf \
  --out-dir tmp_vert/t219/ocr_mp282_ori1 --mode spotting --pages 1-8 \
  --ocr-max-pixels 2822400 --ocr-orientation 1 --resume
```
