# PAGE_IMAGE_LAYOUT.md — LAYJSON 输入 + 图片/图块 passthrough 契约（v1）

> **状态**：implemented（2026-11-10，t192；LAYJSON 接线 + image/chart/footer_image 裁图 passthrough；开关默认关）
> **类型**：governance（横排 geom；不适用于竖排）
> **依据**：[../ghbq_adapt_tasks.md](../../docs/ghbq_adapt_tasks.md) S1/S7、[../ghbq_adapt_findings.md](../../docs/ghbq_adapt_findings.md) B1
> **现有锚点**：`src/pipelines/build_geom.py` L295-331（`LAYJSON/_figs/_fig_titles`）、L340-349（`PAGE_IMAGE_*`）、L813-858（图页/figrow）、`src/utils/image_blocks.py`；`src/utils/page_numbers.py::infer_lay_numbers`；`src/tools/ocr_book.py`（缺 LAYJSON 转换）
> **版本**：v1.1（2026-11-10）—— 实现 LAYJSON 接线 + 图块 passthrough；v1.0 契约保留
> **纪律**：书无关；判据不含书目；ghbq/wz4 只作参考基线；不 commit

---

## 0. 目的、边界与现状

### 0.1 目的

当前扫描书还原会丢图片：ghbq 源书 **103/104 页含整页/大图扫描图像**，产物只剩 7 个约 32×41px 小图；封面照、p2 条形码、图版页不可辨（B1 high）。同时 layout raw（`doc_title/paragraph_title/number/aside_text/image/figure_title/chart/...`）完全未接线，标题/页码/目录也只能靠启发式。

本 spec 定义两块契约：

1. **LAYJSON 输入**：layout raw JSONL → `layout.json`（页 key、blocks、bbox 坐标、页序、缺失回退）；
2. **图片/图块 passthrough**：封面/图版整页叠加、正文图块裁源图贴回、文字避让，**文本层保持可搜索且不删字**；
3. 开关默认关与**零回归**；
4. 可执行的参考资料验收（ghbq p1/p2/p10/图版页、wz4 gate 不变）。

### 0.2 边界（不做的事）

- 本文件不实现 `convert_layout_json()`/`build_geom` 改动；只锁契约。
- 不做像素级复刻；目标是「封面/图版可辨、正文图块位置正确、文字不丢」。
- 不把 ghbq 的 p1/p2/p10 页号写进判据；它们只出现在 §5 参考基线与 §6 验收样例。
- 不改竖排 `build_vert.py`；LAYJSON 与 `PAGE_IMAGE_*` 仅横排 geom/classic 共享层（classic 若接入需同样开关）。
- 不引入新 API；LAYJSON 来自现有 OCR layout raw。

### 0.3 现有能力/缺口（源码事实，2026-11-10）

| 能力 | 位置 | 现状 |
|---|---|---|
| LAYJSON `layout.json` 读取 | `build_geom.py` L304-311 | 期望 **list**，每页 `prunedResult.parsing_res_list`；`block_label=image/figure_title` 填 `_figs/_fig_titles` |
| `PAGE_IMAGE_PAGES`/`PREFIX` | L340/349、L932-934 | **手工页白名单**整页贴原图（`p<key>.png`）；默认空 |
| `extract_figs`/`in_figure`/`figrow` | `image_blocks.py`、L825-858、L1286-1302 | 正文图块裁源图 + 流内 figrow；默认依赖 `_figs` |
| layout 标题 | L351-363、L972 | `LAYOUT_HEADINGS=1` 才启用；默认 0 |
| layout 页码 | `page_numbers.infer_lay_numbers` | 可读 number；依赖 LAYJSON list |
| **缺** | `ocr_book.py` | 无 layout JSONL→`layout.json` 转换；无页 key/jobs 对齐 |
| **缺** | 开关/默认 | `LAYOUT_FIGS`/`PAGE_IMAGE_FULL_RATIO`/`PAGE_IMAGE_TEXT_MODE` 未定义 |
| **缺** | 文本层 | 现有 `in_figure` **跳过**图块内 OCR 行 → 会删字；本契约要求保留 |

---

## 1. LAYJSON 输入契约

### 1.1 原始输入

- 来源：现有 OCR layout raw：`output/<book>/_ocr_<book>/raw/layout_*.json`（或 `data/<book>/` 下）。
- 格式可能是 **JSONL**：每行一个 API 对象（`result.layoutParsingResults[]`），而不是单 JSON（t175 已为 spotting 修复；layout 同）。
- 每个 `layoutParsingResults[]` 页含：
  - `prunedResult.width/height`（layout 像素坐标尺度）；
  - `prunedResult.parsing_res_list[]`：`block_label`、`block_content`、`block_bbox`、`block_order`、`group_id`、`score`（可选）；
  - `layout_det_res.boxes` 可选（仅审计，不用于主契约）。
- 页序由 **`jobs.json` 的 `pages`** 决定，**不是 raw 行号**；无 jobs 时按批内顺序回退并 **WARN**（不得静默）。

### 1.2 转换器（规划）

`ocr_book.convert_layout_json(raw_dir, out_dir, book, jobs_path)`：

1. 用 `_load_json_objects`（单 JSON/JSONL 兼容）读取所有 raw；
2. 按文件/行/对象顺序拼接 `layoutParsingResults`；
3. 按 `jobs[key].pages` 的全局 0-based 页列表对页；页数不等 → 不生成 LAYJSON（fallback）；
4. 写 `<out_dir>/<book>_layout.json`（canonical v1，§1.3）；
5. 写 `<out_dir>/layout_manifest.json`：`raw_files`、`pages`、`source_pages`、`layout_pages`、`converted_sha256`、`warnings`；
6. **layout raw 缺失/坏 JSON/页数不齐** → 不生成 canonical；scan2pdf 记 `layout=missing/malformed`，构建走 no-LAYJSON 现状（§1.6）。

### 1.3 canonical `layout.json`（v1）

```json
{
  "schema_version": "layout-json-v1",
  "source": "output/ghbq_full/_ocr_ghbq/raw",
  "source_pages": 104,
  "pages": [
    {
      "key": "0",
      "page": 1,
      "width": 1191,
      "height": 1733,
      "bbox_space": "layout_px_top_left",
      "blocks": [
        {"category": "doc_title", "label": "doc_title", "bbox": [109,252,1043,438],
         "text": "戈尔巴乔夫与\n“人道的民主的社会主义”", "order": 2, "group": 1, "score": 0.81},
        {"category": "image", "label": "image", "bbox": [0,663,1191,1470],
         "text": "", "order": null, "group": 3, "score": 0.92}
      ]
    }
  ]
}
```

- **key**：0-based 字符串，等于 OCR 全局页 key；**page** 为 1-based 源页；两者 `page = int(key)+1`。
- **pages 按 key 升序**；key 不得重复/跳号；页数必须 = `source_pages`。
- **width/height**：该页 layout 坐标尺度（px）；缺失时用 `layout_dpi` 或 `142` 兜底，并在 `warnings` 记录。
- **blocks**：按 `block_order`（有）→ `bbox` y/x（无）稳定排序；`category` 是规范化枚举（§1.4），`label` 保留 raw。
- **text**：`block_content` 原样（含换行）；image/figure/chart/footer_image 等可为空。
- **order/group/score** 可空；不参与判据，仅供审计/排序。

### 1.4 block category 枚举

| category | 来源 label（典型） | 用途 |
|---|---|---|
| `doc_title` | doc_title | 标题层级 |
| `paragraph_title`/`title` | paragraph_title/title | 标题层级 |
| `text` | text | 正文 |
| `content` | content | 目录/正文块（保留） |
| `header`/`footer`/`number` | header/footer/number | 页眉/页脚/页码 |
| `aside_text` | aside_text | 旁注/目录页码列 |
| `image`/`figure` | image/figure | 大图/图版（passthrough） |
| `chart` | chart | 条形码/图表（passthrough） |
| `footer_image`/`header_image` | footer_image/header_image | 页脚/页眉图像（条形码/装饰） |
| `figure_title` | figure_title | 图说明（文字保留） |
| `table`/`algorithm`/`seal`/`other` | 同名/未知 | 仅审计；不默认 passthrough |

- 未知 label → `other`，**不参与 passthrough**，不得因未知块破坏现有文本。

### 1.5 bbox 坐标与换算

原始 bbox 是 **layout 像素坐标，top-left 原点，x→右、y→下**。转源 PDF pt：

```
sx = src_page_width_pt  / layout_width
sy = src_page_height_pt / layout_height
bbox_pt = [x0*sx, y0*sy, x1*sx, y1*sy]
```

- `src_page_*` 取源 PDF 对应页 `rect`（逐页；多纸型书也正确）。
- `layout_width/height` 缺失：`sx=sy=72/layout_dpi`（`layout_dpi` 默认 142，可配置）；缺页尺寸不得猜书。
- bbox 夹取到 `[0, src_w]×[0, src_h]`；负数/越界裁掉并记 `bbox_clamped` warning。
- **不得**用单一 `LDPI=142` 覆盖所有页；ghbq layout width 1191 vs 源 595.28pt 时 `sx≈0.5`，142 只是旧的近似值。
- 现有 `LDPI=142` 代码保留为兼容兜底；新 canonical 用 per-page `sx/sy`。

### 1.6 页序、缺失与 fallback

- `jobs.pages` 是权威页序；每个 raw page 按 jobs 页列表配 key。
- jobs 缺/页数不等：**不生成 canonical LAYJSON**；`warnings` 记录；scan2pdf `layout=missing|mismatch`，构建完全回退到无 LAYJSON 现状（§4.2）。
- canonical LAYJSON 缺失：build 保持现状；不得用 layout 推断图块/标题/页码。
- raw 单 JSON 与 JSONL 等价（t175 `_load_json_objects` 兼容）。

---

## 2. 图片/图块 passthrough 契约

### 2.1 两类 passthrough

| 类型 | 判定 | 渲染 |
|---|---|---|
| **整页叠加（cover/plate）** | `PAGE_IMAGE_PAGES` 显式包含该页（数据覆盖）；或 `LAYOUT_FIGS=1` 且该页 image-like 块面积和 / 页面积 ≥ `PAGE_IMAGE_FULL_RATIO`（默认 0.40） | 源页整页渲染为 **BG**（`\AddToShipoutPictureBG`），OCR 文本层置为 **invisible overlay**（保留可搜） |
| **正文图块** | `LAYOUT_FIGS=1`，`category ∈ {image,figure,chart,footer_image,header_image}` 且非整页 | 按 bbox 裁源页 → 流内 `figrow`/`\includegraphics` 贴回；图块内 OCR 文字 invisible；图外文字正常 |

- **full-page 阈值**：`PAGE_IMAGE_FULL_RATIO` 是页幅比例，不是书目；封面/图版用块面积和（可多个 image 块并集近似）判定。
- **实现锚点（t199）**：`build_geom` 的 `_image_page_full()` + `_page_img_full`；源页 raster 由 `render_src_page(key)` 生成，`\AddToShipoutPictureBG` 整页铺满；本页 `body` 前后 `\special{pdf:literal direct q 3 Tr}`/`Q`，文本层保留。
- `PAGE_IMAGE_PAGES` 是**显式数据覆盖**（0-based key，逗号分隔），不是判据；默认空，不得在代码里写页号。
- `PAGE_IMAGE_PREFIX` 保留现有手工整页图（`p<key>.png`）路径；新自动路径不依赖手工 PNG。
- **图块类别**：`image`/`figure`/`chart`/`footer_image`/`header_image`；`figure_title` 不是图块（文字，保留可见）；`table`/`algorithm`/`seal` 不默认 passthrough。
- **p2 条形码**：layout `chart` 块（ghbq p2 `[793,1319,1102,1566]`）按正文图块贴回，不整页叠加。

### 2.2 视觉层序

1. 源页/图块图像（BG）；
2. 文本层（FG）：图外文字正常可见；图内文字 invisible（`Tr 3`/等价），但仍可提取/搜索；
3. 页眉/页脚/页码保持原规则；不得因图块叠加删除/移动页码。

- **不得**用白色矩形覆盖图块内文字；不得把图块内 OCR 行从文本流删除。
- 图像缩放保持 bbox 宽高；不得拉伸变形；`keepaspectratio` 只在容器内约束。
- 整页叠加的源图必须来自**源 PDF 对应页**（不是其他页/缩略图）。

### 2.3 文字避让（不删字）

| 位置 | 可见性 | 文本层 |
|---|---|---|
| 图块 bbox 外 | 正常 | 保留 |
| 图块 bbox 内（中心落入） | **invisible** | 保留（可搜/可选） |
| 图块边界跨越 | 按行中心判定；仍保留 | 保留；渲染层不强行裁行 |
| `figure_title`/图说明 | 正常 | 保留 |
| full-page 覆盖页 | 全部 **invisible**（源图已显示文字） | 全部保留 |

- **验收硬条件**：交付 PDF 的非空白字符数不得少于基线（§6）；不得出现“图片后文字消失”。
- 可执行实现建议：在图块内行前/后用 `\special`/`Tr 3` 包裹该行的文本输出；或统一 `PAGE_IMAGE_TEXT_MODE=invisible` 时用 PDF 文本渲染模式 3。**不能只删 `sl` 行**。
- `PAGE_IMAGE_TEXT_MODE`：
  - `auto`（默认）：图内 invisible、图外 visible；
  - `invisible`：全页文本 invisible（用于纯图版页/严格视觉复刻）；
  - `visible`：仅调试；可能与源图文字重叠，不得作为交付默认。

### 2.4 图块裁剪

- 裁切：源页 `get_pixmap(dpi=PAGE_IMAGE_DPI)`（默认 200）→ bbox×sx/sy；保存到 work `<out>.figs/p<key>_<i>.png`。
- 失败（源页缺失/裁剪异常）→ 跳过该图块，**不阻断文本层**；记 `image_crop_fail`。
- 同页多图按 y/x 排序；同 y 并排按 x；figrow 预留真实图高，后续文字后移（避免压字）。
- 图块与文本行重叠时：图块先占位，文本 invisible 保留；不得把文本行移出页。

---

## 3. 目录 layout 驱动（p10 最小契约）

`LAYOUT_TOC=1`（默认 0）时，TOC 页必须由 LAYJSON 驱动，不用纯 OCR 启发式：

1. **TOC 页识别**：`header`/`doc_title` 文本含 `目录`/`CONTENTS`，或 `aside_text` ≥3 个纯数字列；记录 `toc_pages`。
2. **标题**：`header`/`doc_title` 的 `目录/CONTENTS` 用正常标题层级（可见）。
3. **条目/页码/作者列**：
   - `content` 块 → 条目文本/行序；
   - `aside_text` 纯数字块 → 左/右页码列；
   - `number` 块 → 页脚页码；
   - 作者列若 layout 未单列（ghbq p10 author 与书名在同一 `text` 块），**不伪造分列**；S8/B2 另做，本契约只要求「layout 块被消费、页序/条目/页码列不乱」；
4. **p10/p11 验收**：p10 丛书目录用 `doc_title/text` 驱动（作者未单列时登记 S8 残留）；p11 用 `header/content/aside_text` 驱动；不得把作者名拼成条目正文（S8 前登记）。

> 本节的 TOC 最小路径只消费 layout 块；B2 的完整两列版式是后续 S8，不在本 spec 的实现承诺内。

---

## 4. 开关、默认值、零回归

### 4.1 开关

| env | 默认 | 语义 |
|---|---|---|
| `LAYOUT_HEADINGS` | `0` | 用 LAYJSON 标题块；现有开关 |
| `LAYOUT_FIGS` | **`0`** | 用 LAYJSON 图块 passthrough（自动整页/正文图块） |
| `LAYOUT_TOC` | **`0`** | 用 LAYJSON 驱动 TOC 最小路径（§3） |
| `PAGE_IMAGE_PAGES` | `''` | 显式整页贴图 key（0-based，逗号分隔）；**数据覆盖**，不是判据 |
| `PAGE_IMAGE_PREFIX` | `''` | 显式整页图 `p<key>.png` 前缀；现有机制 |
| `PAGE_IMAGE_FULL_RATIO` | `0.40` | 自动整页叠加的 image-like 面积/页面积阈值 |
| `PAGE_IMAGE_TEXT_MODE` | `auto` | `auto|invisible|visible`；§2.3 |
| `PAGE_IMAGE_DPI` | `200` | 裁源图 dpi |
| `LAYJSON` | `''` | canonical 路径；缺省不启用 |

- `PAGE_IMAGE_FULL_RATIO`/`PAGE_IMAGE_TEXT_MODE`/`PAGE_IMAGE_DPI` 只在 `LAYOUT_FIGS=1` 或 `PAGE_IMAGE_PAGES` 非空时才被消费；默认构建不读取。
- 所有开关默认关/空；**不传 LAYJSON 时现有书输出逐字节不变**。
- **scan2pdf 默认不自动传 LAYJSON**：只有显式 `--layout`，或 `LAYOUT_HEADINGS=1` / `LAYOUT_FIGS=1` / `LAYOUT_TOC=1`（含 `toc`）时才查找/生成/传 LAYJSON；否则 build 完全走无 LAYJSON 现状（report `layout=disabled`）。
- 传 LAYJSON 但 `LAYOUT_HEADINGS=0`、`LAYOUT_FIGS=0`、`LAYOUT_TOC=0`、`PAGE_IMAGE_PAGES` 空时，也**不得改变**现有输出（`_figs`/标题块不得被隐式加载）。
- TOC 页（header 含目录/CONTENTS 或 aside 全纯数字）跳过 `aside_text` 渲染，避免与条目内联页码重复；非 TOC 页才启用 aside。
- `PAGE_IMAGE_PAGES` 显式非空是用户数据覆盖，允许单独启用；报告中必须记录 key/来源。

### 4.2 零回归定义

对 `wz1/wz2/wz4`（无 LAYJSON）以及任何“不传 LAYJSON/开关全关”的构建：

1. `.tex` 逐字节相同（或 PDF 内容流/文本/bbox 等价，若 PDF `/ID`/时间戳导致 md5 差异，报告给等价证据）；
2. `.calib.json` 除 `render` 回填外字段不变；
3. 页数、文本层字符数、pitch/gate 不变；
4. 不得出现任何 `_figs`/`page_image` 日志（开关全关时）。

**contract**：零回归是合入硬条件；不接受“只差图片”或“只差空白”作为默认行为。

---

## 5. 参考基线（只作验收对照，不是判据）

### 5.1 ghbq（横排扫描书，104 页）

- 源 `source_pdf/ghbq.pdf`；layout raw `output/ghbq_full/_ocr_ghbq/raw/layout_*.json`（3 个 JSONL，50+50+4 页）。
- layout block 计数：`text 278 / number 97 / paragraph_title 52 / doc_title 7 / aside_text 5 / content 3 / image 2 / footer_image 2 / footer 2 / header 2 / figure_title 1 / chart 1 / header_image 1 / algorithm 1`。
- **p1**：`image [0,663,1191,1470]`，页面积覆盖 **0.466**；`footer_image` 小块；整页叠加候选。
- **p2**：`chart [793,1319,1102,1566]`（条形码），覆盖 **0.037**；走正文图块，不整页。
- **p3**：`image [0,653,1191,1471]`，覆盖 **0.470**；整页叠加候选。
- **p10**：丛书目录——`doc_title`（丛书名）+ 10 个 `text` 条目（作者与书名同块；S8 作者列待做）；`LAYOUT_TOC` 用 `doc_title/text` 驱动。
- **p11**：本书目录——`header 目录/CONTENTS`、`content` 条目块、`aside_text` 页码列、`number` 页脚；`LAYOUT_TOC` 参考页。
- 源书 103/104 页含整页扫描图；现有产物仅 7 个小图（B1 事实）。
- 上述页号只作验收样例；判据不含页号。

### 5.2 wz4（回归基线）

- 677 页；`verify_geom --src-pdf` gate PASS 99.6%（现有基线）；无 LAYJSON 时输出/字符/页数不得变化。

---

## 6. 可执行验收（实现任务用）

### 6.1 命令（实现后）

```bash
LAYOUT_HEADINGS=1 LAYOUT_FIGS=1 LAYOUT_TOC=1 \
LAYJSON=data/ghbq/ghbq_layout.json \
PAGE_IMAGE_FULL_RATIO=0.40 PAGE_IMAGE_TEXT_MODE=auto \
/usr/bin/python3 src/tools/scan2pdf.py \
  --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/ghbq_img.pdf \
  --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
```

- 未传 `LAYJSON` 的 wz4：
```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/wz4.pdf --book wz4 \
  --out output/wz4/wz4_img.pdf --data-dir data/wz4 --skip-ocr --force
```

### 6.2 验收清单

| # | 检查 | 通过条件 |
|---|---|---|
| 1 | p1 封面 | 产物 p1 可见源封面照片/图像（源/产物裁图并排，不要求像素相同；不得只剩空白/小图） |
| 2 | p2 条形码 | 产物 p2 可见条形码区域（`chart` 块裁图；不得被文字/白块覆盖） |
| 3 | 图版页 | layout `image` 覆盖≥`PAGE_IMAGE_FULL_RATIO` 的页可见整页/大图（p3 等参考） |
| 4 | p10/p11 目录 | p10 丛书目录 `doc_title/text`、p11 主目录 `header/content/aside_text` 被消费：标题/条目/页码列不乱；作者列未单列时登记 S8 残留，不得拼进条目正文（若可避免） |
| 5 | 文本层 | 非空白字符数 **不少于**同书基线（无 passthrough 版本）；不得删字；`get_text` 可搜到原 OCR 文本 |
| 6 | GMPG | 交付 PDF `get_text` 中 `GMPG` = **0**（沿用 t188 交付口径） |
| 7 | wz4 零回归 | 页数 677=677；gate PASS 99.6%；文本/字符/`.tex` 与基线等价；无 LAYJSON 时不出现图块日志 |
| 8 | ghbq 默认关 | `LAYOUT_HEADINGS=0 LAYOUT_FIGS=0 LAYOUT_TOC=0` 时与现有 ghbq 构建文本/页数/gate 等价 |
| 9 | 页序/bbox | `layout.json` 页数=104、key 0..103；p1 image bbox 换算到源 pt 误差 ≤1pt（或报告单位证据） |
| 10 | 失败降级 | 坏/缺 LAYJSON 时 fallback 到现状，有 warning，不产生半套图块/标题 |

- 图表/封面“肉眼可辨”以源/产物并排 PNG 为证；报告路径写入 `docs/scan2pdf_v1.md` 后续章节。
- 文本层字符数用 `fitz` 提取、去空白/去 GMPG（t188 后无 GMPG）同口径对比。
- **不得**用“源图像素差”作为唯一判据；不追求逐像素。

---

## 7. 失败模式与降级

| 情形 | 行为 |
|---|---|
| LAYJSON 缺失 | 不启用 layout/图片；现状构建；`layout=missing` warning |
| raw 坏 JSON/JSONL 解析失败 | 不生成 canonical；现状构建；`layout=malformed` |
| layout 页数≠源页/jobs 页数 | 整份 LAYJSON 拒绝；现状构建；`layout=mismatch` |
| block bbox 越界 | 夹取 + `bbox_clamped`；不阻断 |
| 图块裁剪失败/源页缺失 | 跳过该图块；文本层保留；`image_crop_fail` |
| full/body 判定歧义 | 按 `PAGE_IMAGE_FULL_RATIO`；报告 `image_mode=body|full` |
| 图片叠加导致文本不可见 | **不可接受**；不得删字；用 invisible overlay |
| 文本字符数减少 | 验收失败；不得合入 |
| 图块压字/溢出 | 用 figrow 预留图高；仍有溢出→报告，按 gate 失败 |
| `PAGE_IMAGE_PAGES` 与自动判定冲突 | 显式 key 优先；报告 `page_image_override` |

---

## 8. 实现边界与 DoD（后续任务）

### 8.1 实现拆分（后续）

1. `ocr_book.convert_layout_json()` + `_load_json_objects` 复用；canonical schema/页序/manifest。
2. `build_geom`：读取 canonical；`LAYOUT_FIGS/LAYOUT_TOC` 开关；`_figs` 只在开关开时加载；full/body 判定；text invisible overlay；正文图块 crop/figrow。
3. `scan2pdf`：`--ocr-mode layout/both` 生成并传 LAYJSON；report 记 `layout_sha/pages/mode`。
4. 测试：schema/页序/bbox 换算/开关零回归/文本字符不减少/真 PDF p1/p2 图形对象检查。
5. 文档：`docs/scan2pdf_v1.md` 新章节 + 参考基线归档。

### 8.2 本任务 DoD

- 只新增 `spec/governance/PAGE_IMAGE_LAYOUT.md`；
- 未改 `build_geom.py`/`ocr_book.py`/数据/产物；未 commit；未调 API；
- 参考基线来自现有 ghbq raw 只读统计。

---

## 9. 书无关自检

| 检查 | 结果 |
|---|---|
| 判据不含书目 | ✓ 阈值/公式通用；ghbq/wz4 只在 §5 参考 |
| 无页白名单作为判据 | ✓ 唯一显式页列表 `PAGE_IMAGE_PAGES` 是用户数据覆盖，默认空；p1/p2/p10 只作验收样例 |
| 不传 LAYJSON 零回归 | ✓ §4.2 硬条件 |
| 文本层不删字 | ✓ §2.3/§6.5 |
| bbox 书无关 | ✓ 逐页源 PDF 页幅换算；不写死 142/595 |
| 失败降级 | ✓ §7 |
| 与竖排分离 | ✓ 不适用 `build_vert.py` |
| 现状兼容 | ✓ canonical 是新增层；旧 list LAYJSON 由适配器兼容，默认不启用 |

> 本 spec 只锁契约；实现任务可据此拆 S1/S7，不改本书专属数据分支。


---

## 10. 实现记录（t192，2026-11-10）

- `ocr_book.convert_layout_json()`：layout raw（JSON/JSONL）→ `<out>/<book>_layout.json`；页 key 由 `jobs.pages`；每页 `page_key/page/width/height/page_width_pt/page_height_pt/blocks`；`prunedResult` legacy 兼容；`layout_manifest.json` 记录页数与 sha。
- `scan2pdf.find_layout()`：优先 existing `layout.json`，否则从 `raw/layout_*.json` 生成；`--ocr-mode auto/layout` 时启用；`build_pdf` 设 `LAYJSON/LAYOUT_HEADINGS/LAYOUT_FIGS/LAYOUT_TOC/PAGE_IMAGE_*`。
- `build_geom`：`LAYOUT_FIGS=1` 加载 image/figure/chart/footer_image/header_image；`_lay_bbox_142()` 按每页 src/layout 尺度换算；图块用 BG overlay（不占流、不翻页）；文本保留（图块内 OCR 行仍按现有 `in_figure` 跳过的情况只限无字符图块）。
- 实现验收（ghbq）：104 页；p1/p3 覆盖率 0.466/0.470 ≥ PAGE_IMAGE_FULL_RATIO=0.40 → 整页源图 + 全文字 3 Tr（p1 源图标题正确、p3 复制封面）；p2 chart 0.037 走正文图块、文字可见；文本 **43,913** = 默认（不减少）；GMPG 0；gate **PASS pitch 96.8%**（见 docs §22/§23）。
- wz4：677=677、字符 554,341 与无 LAYJSON 完全相同、gate PASS 99.6%；wz2 6 页 PASS 100%；无 LAYJSON 不启用 layout/图块。
- **t199 整页叠加**：LAYOUT_FIGS=1 时 image-like 并集覆盖率 ≥ PAGE_IMAGE_FULL_RATIO（默认0.40）→ `render_src_page()` 源页 raster 整页 BG（width=PAGE_W,height=PAGE_H）+ 本页文本 span 全 `3 Tr`（可搜）；未达阈值保持图块裁贴/图外文字可见。p1/p3 触发，p2 不触发。
- 残留：`LAYOUT_TOC` 仅 p11 aside 块接线，p10 作者列仍待 S8；显式 `PAGE_IMAGE_PAGES` 仍可强制整页（手工数据）。
