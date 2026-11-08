# scan2pdf 一键入口设计 + 书型判断探针

> 任务：t115（第 3 步）—「上传一本 PDF → 出一份还原 PDF」的设计与可行性探针。
> 状态：**设计 + 本地探针**；未实现 `scan2pdf.py`，未改产品代码/数据，未调用 OCR API，未 commit。
> 样书：`source_pdf/wz6.pdf`（231 页）、`source_pdf/wz7.pdf`（1748 页）。
> 探针产物：`tmp_vert/scan2pdf/probe_booktype.py`、`probe_wz6.json`、`probe_wz7.json`、`probe_results.csv`、`crops/`。

---

## 0. 结论（先行）

1. **一键入口可行**，但必须把「书型判断」拆成 **本地页幅/框线探针 + OCR 前导样本的方向判断**；不能只看第一页（封面/扉页会把框线、方向判错）。
2. **两本样书的书型判断正确**：
   - **wz6**：竖排、有框、595.28×1245.31pt（210×439.3mm，custom 肖像）→ `vert`；6/6 样本页框线、6/6 竖排；置信度 1.0。
   - **wz7**：竖排、无框、主导页 892.5×1323pt（314.9×466.7mm，custom 肖像）→ `vert`；6/6 样本页无框线（0/6），5/5 有效样本页竖排（p699 无 OCR 框，unscorable）；置信度 1.0。
   - **wz7 是混合纸型**：892.5×1323 610 页、705×1083.8 582 页、921.8×1439.2 554 页等 5 个尺寸组；主导只占 **34.9%**。一键入口必须报 `paper_mixed`，不能把主导页当全书唯一纸型。
3. **横排判断**只在**页级**验证：wz6 p159（6 框）、wz7 p397（37 框）OCR 行框方向为 horizontal；两本样书都没有**整本横排书**，所以横排书型仍是未验证项（需 heldout 横排书）。
4. **OCR 成本可控**：A+B 双模式 = 2×页数；wz7 1748 页 → 3496 API 页（40k/天配额的 **8.7%**），按 t87 实测 4 并行墙钟约 **45–65 分钟**；全书构建约 30 分钟；总计约 **1.5–2 小时/1748 页**。
5. **最大实现风险不是 OCR**，而是三处「书专属默认值」：`build_vert` 默认加载 `docs/vert_taskF_missed_fix.json`（wz7 修复数据）、`VERT_*` 参数、以及 `build_classic` 的两趟校准。scan2pdf 必须显式 `--data-dir` 每书隔离；**任意新书默认 `VERT_MISSED_FIX=0`**，只有本数据目录存在 per-book fix 时才启用。

---

## 1. 现有入口与数据依赖（已阅读）

### 1.1 构建入口

| 管线 | 入口 | argv | 关键依赖 | 适用 |
|---|---|---|---|---|
| 竖排 | `src/pipelines/build_vert.py` | `<lines.json> <coords.json> <out.pdf> [src.pdf]` | OCR 行文本 + 列 poly；`src.pdf` 用于页幅/书眉/页码/版框/贴图；env `VERT_*` | 竖排、有框/无框（自动降级） |
| 横排（几何） | `src/pipelines/build_geom.py` | `[spotting_lines] [spotting_coords] [out.pdf] [src.pdf]` | 行 bbox/行高/位置/文本；`src.pdf` 图页/乱码页贴原图 | 现代横排 |
| 横排（古籍） | `src/pipelines/build_classic.py` | 直接跑=单趟；生产入口 `fit_positional_classic.py` 两趟 | 同上；classic 字号/版式 | 古籍横排；**v1 不自动选** |
| 布局 OCR 变体 | `src/pipelines/build_pdf_v13.py` | `<src.pdf> <out.pdf> <spotting_lines> <spotting_coords> [titles] [markdown] [pagenums]` | 需要 A(layout) 标题/pages + B(spotting) 坐标 | v1 不进入 auto；作为 legacy/手工 |

### 1.2 OCR 工具现状（关键）

- `src/tools/api_candidates_all_build.py` / `api_candidates_all_run.py` / `api_pilot_*` 是**候选条带**（missing-cell）批处理，**不是**整书整页 OCR；`--book` 可参数化，但输入是候选列，不是原书页。
- 整书 A 模式的参考实现是 `tmp_vert/battle19/run_batches.py`：50 页/批、4 次退避、断点续跑、每批 raw JSONL；实测 wz7 1748 页 35 批，API 合计 3456s≈58min，4 并行墙钟≈32min，配额 4.4%。
- battle17 实测：A（layout+ocr）正文 LCS 1.000、引号 10/9、曲牌括号 4/7；B（spotting）几何/列 poly 可靠但引号全变「一」；**推荐 A+B**（A 文、B 几何）。
- **设计缺口**：现有 `src/tools` 没有「任意 PDF → A/B 整书 OCR → coords/lines」的通用批处理；scan2pdf 需要一个薄封装（暂命名 `src/tools/ocr_book.py`，本任务不实现），复用 `run_batches.py` 的提交/轮询/落盘模式。

### 1.3 数据契约（与 build 入口对齐）

```
data/<book>/
  raw/A_batch_XXX.jsonl          # A layout+ocr 原始结果（可选）
  raw/B_batch_XXX.jsonl          # B spotting 原始结果（构建必需）
  jobs.json                      # batch -> jobId/页码范围/重试/状态（断点）
  <book>_spotting_lines.json     # B: {key: [列文本,...]}，key=页序 0-based
  <book>_spotting_coords.json    # B: {key: [[[x,y]...], ...]}，列 poly
  <book>_spotting_lines_patched.json  # 本数据目录的可选 per-book 修正（不是 wz7 全局文件）
  <book>_layout_lines.json       # A: 块/行文本（质量/证据，不直接给 vert 几何）
  <book>_layout_coords.json      # A: 块 bbox
  <book>_layout_markdown.json    # A: markdown（可选，标题/内容证据）
```

- `build_vert` 读 `lines/coords`；key 从 0 开始，按 key 升序页序。
- `coords` 的尺度与源页相关（历史 OCR 2x px@144dpi；现有 API 批次可能不同）；build 入口/校准自行处理。
- **页数 1:1** 是硬契约：`len(lines)==len(coords)==源 PDF 页数`；缺页不补空、必须失败/重跑。

### 1.4 已发现的书专属默认值（必须隔离）

1. `build_vert.py` 默认 `VERT_MISSED_FIX=docs/vert_taskF_missed_fix.json`（仓库内 wz7 修复数据；`MISSED_FIX_MIN_PAGES=1000`）。
   **新书 >1000 页会误套 wz7 的缺失字/圈码/引号修复**。scan2pdf 必须：
   - 默认 `VERT_MISSED_FIX=0`；
   - 只有 `data/<book>/<book>_missed_fix.json` 存在时才设为该文件；
   - 报告里记录 fix 文件 hash。
2. `build_vert` 的 `VERT_*` 有 wz6 实测兜底（paper-agnostic 已相对化），但 `VERT_PAGES`、`VERT_SPECIAL`、`VERT_FAX` 等会影响输出；scan2pdf 只设必要值，不复制 wz7 调参。
3. `build_classic` 的生产入口是两趟校准壳 `fit_positional_classic.py`；v1 auto **不选 classic**，避免无书型分类器时误用。
4. 质量评测的 gold/回归（PUNCT_EVAL/CONTENT_EVAL）是 **20/22 页基准 + per-book fix**；任意新书没有 gold 时必须 `UNSCORED/MANUAL_ONLY`，不能伪造 PASS。

---

## 2. scan2pdf.py 接口设计

```bash
/usr/bin/python3 src/tools/scan2pdf.py \
  --input book.pdf \
  --out out.pdf \
  --book name \
  [--ocr-mode auto|layout|spotting] \
  [--pipeline auto|vert|geom] \
  [--data-dir data/name] \
  [--token-file /tmp/paddle_token] \
  [--work-dir tmp_vert/scan2pdf/name] \
  [--pages 1-20] \
  [--resume] \
  [--dry-run] \
  [--keep-work]
```

| 参数 | 默认 | 语义 |
|---|---|---|
| `--input` | 必填 | 源扫描 PDF；只读；校验可打开/未加密/页数>0 |
| `--out` | 必填 | 最终 PDF 路径；先写临时文件，verify 通过后原子替换 |
| `--book` | 必填 | 稳定 slug（`[a-z0-9_-]+`）；数据/工作目录/报告命名；不参与内容判断 |
| `--ocr-mode` | `auto` | `auto`=A+B（推荐）；`layout`=A only（**不能构建**，见 §3）；`spotting`=B only（可构建，引号召回低） |
| `--pipeline` | `auto` | 由探针选 `vert`/`geom`；显式覆盖时记录冲突，不静默改回 |
| `--data-dir` | `data/<book>/` | OCR/中间数据；必须每书隔离；不指向 `data/wz7_full` |
| `--token-file` | `/tmp/paddle_token` | 只读 token；不打印/不落报告；缺失→OCR 前置失败 |
| `--work-dir` | `tmp_vert/scan2pdf/<book>/` | 构建临时/日志/候选 PDF；可清理 |
| `--pages` | 全书 | 调试子集（`1-20`/`1,3,5`）；页数 1:1 校验对子集用子集页数；默认生产必须全书 |
| `--resume` | 开（默认） | 跳过 raw 非空/`jobs.json` 完成的 batch；重跑失败批 |
| `--dry-run` | 关 | 只做本地探针 + 计划（书型/纸型/页数/成本估算），不调 OCR、不写 out |
| `--keep-work` | 关 | 保留中间 PDF/tex/日志；默认保留 report + raw（可追溯），中间大文件可清 |

### 2.1 `--ocr-mode` 的严格语义

- `auto`：A+B。**B 提供 coords/lines/reading geometry；A 提供文本/标题/引号证据**；v1 先保证 B 可构建，A-B 融合只按保守规则（引号/括号/曲牌名；不改 B 的字符顺序），融合冲突进 manual。
- `spotting`：只用 B。可构建，但 battle17 实测引号全变「一」、括号差；质量门禁会显著偏低。
- `layout`：只用 A。**A 的 block bbox 只有 11 块 vs 22 列**（battle17），不能作为 vert 的列几何；scan2pdf 在非 `--dry-run` 时直接 `E_LAYOUT_NO_GEOM`，不生成 PDF。`layout` 仅用于「只取文本/gold/质量」场景。
- 任何模式都不把 token 写进日志；原始 JSONL 不含 token。

### 2.2 退出码（契约）

| code | 含义 | 产物 |
|---|---|---|
| 0 | 成功（verify PASS，quality AUTO/MANUAL 可交付） | `out.pdf` + report |
| 2 | 输入/参数/token/权限 | 无 out；report 写原因 |
| 3 | OCR 失败（重试耗尽/页数不齐/缺页） | raw/jobs 保留；无 out；可 `--resume` |
| 4 | 书型不可判/混用/无几何模式 | 无 out；report 给 probe |
| 5 | build/LaTeX 失败 | candidate/log；无 out；可重跑 |
| 6 | verify 失败（页数/越界/丢失） | `out.candidate.pdf` + report；不替换 out |
| 7 | quality REJECT（punct/content） | `out.candidate.pdf` + report；不替换 out |
| 8 | 需要人工（mixed paper/gold 缺失/UNSCORED） | candidate + report；不自动 |

> 失败时不覆盖用户已有 `--out`：先 `out.tmp`，verify/quality 达标再原子 rename；quality REJECT 保留 `out.candidate.pdf` 供审阅。

---

## 3. 端到端步骤（输入/输出/失败/重试）

| # | 步骤 | 输入 | 输出 | 失败/重试 |
|---|---|---|---|---|
| 0 | 输入校验 | `--input` PDF | page_count/page_size/hash；`work/` | 打不开/加密/0 页→exit 2；不 OCR |
| 1 | 本地书型探针（§4） | PDF + 可选已有 OCR coords | `probe.json`：paper/frame/orientation/pipeline | 无法判→exit 4；`--dry-run` 到此结束；10s 级 |
| 2 | OCR 前导（可选但推荐） | 6 页样本（5%–95%） | 前导 lines/coords；方向/框线交叉验证 | 前导失败→继续用本地纸型+人工选 pipeline，或 exit 4；可重试 2 次 |
| 3 | 决定 pipeline | probe + 前导 | `pipeline=vert/geom`，`paper_mode` | 竖/横冲突/混用→exit 4；显式 `--pipeline` 覆盖并记 `override=true` |
| 4 | 整书 OCR A+B | 源 PDF、token、batch=50、workers=4 | `raw/A_batch_*.jsonl`、`raw/B_batch_*.jsonl`、`jobs.json` | 500/网络→4 次指数退避（8s,16s,24s,32s）；超时→exit 3；按 batch 断点续跑 |
| 5 | 解析/落盘 | raw JSONL | `coords/lines`（B）；A layout | 页数≠源页→exit 3；API 页序错→按 page index 对齐并断言；不补空 |
| 6 | 数据装配 | B lines/coords；可选 A 融合 | `*_spotting_*.json`；per-book fix 检查 | 缺列/空页→记录 `coverage`；不伪造；缺页→exit 3 |
| 7 | 构建 | lines/coords/src.pdf；per-book fix | `out.tmp` + tex/log | 编译失败→exit 5；不盲目换管线；保留 log |
| 8 | verify | out.tmp + coords/lines + src | verify JSON/log；页数 1:1/越界/丢失 | 硬失败→exit 6；candidate 保留；不替换 out |
| 9 | 质量门禁 | verify + punct_eval(B) + content_eval（有 gold 时） | quality JSON/markdown；AUTO/MANUAL/REJECT/UNSCORED | 无 gold→UNSCORED/MANUAL；REJECT→exit 7；不自动修 |
| 10 | 发布/report | 全部 | `out.pdf` + `scan2pdf_report.json/md` | 原子 rename；失败保留 candidate；不覆盖 out |

### 3.1 重试/断点规则

- **批级**：每批 50 页；`jobs.json` 记录 `batch_id/from_page/to_page/jobId/status/retries/elapsed/raw_sha`；raw 非空即 done；失败批可单独重跑。
- **重试**：仅网络/HTTP 5xx/轮询超时（4 次，退避 8/16/24/32s）；4xx/token 无效不重试。
- **页级**：API 返回页数与 batch 页数不等→整批失败（不拆页猜）；不生成空页。
- **构建**：LaTeX 失败不自动重试；`--resume` 可重新构建（不改 OCR）。
- **幂等**：相同 `--book/--input` hash + raw 完整 → 不再提交 API；报告记录 input hash。

---

## 4. 书型自动判断探针（本地，已实测）

脚本：`tmp_vert/scan2pdf/probe_booktype.py`；结果：`probe_wz6.json`、`probe_wz7.json`、`probe_results.csv`。
探针只读 source PDF + 已有 OCR coords；**不调 API**。

### 4.1 判断逻辑

1. **纸型**：读全部页 `rect`；按 10pt 分组的页数统计；主导尺寸中位数；`dominant_share`=±1.5% 内页占比；`multi_format = dominant_share < 0.90`；mm/名称（A4/A5/B5/custom）+ portrait/landscape。不把第一页当全书。
2. **框线**：6 个 5%–95% 样本页渲染 100dpi → Canny → HoughLinesP；统计长横/竖线（>0.25×页宽/高）；`(h≥1 and v≥2) or (h≥2 and v≥1)` 记为有框页；书级有框 = ≥60% 样本页；无框 = ≤40%；中间 `ambiguous`。
3. **方向**：读已有 OCR `coords` 的列 poly；每页线框 `h/w` 中位：
   - `median(h/w) > 1.2` → vertical；
   - `median(h/w) < 1/1.2` → horizontal；
   - 其余 mixed；无框→unscorable。
   - 书级：valid 页中 ≥70% 同类 → vertical/horizontal；否则 mixed/unscorable。
4. **路由**：vertical→`build_vert`；horizontal→`build_geom`；mixed/unscorable→exit 4；`build_classic` 不 auto。
5. **框线只作报告/参数**：build_vert 自己按 src 检测版框；探针不硬设 `VERT_FRAME`。

### 4.2 实测结果

| 书 | 页数 | 主导纸型 | 纸型判定 | 方向 | 框线 | pipeline | 置信度 |
|---|---|---|---|---|---|---|---|
| wz6 | 231 | 595.28×1245.31pt（210×439.3mm） | custom 肖像，dominant .996，非 multi | vertical 6/6 | has_frame 6/6 | **vert** | 1.0 |
| wz7 | 1748 | 892.5×1323pt（314.9×466.7mm） | custom 肖像，dominant **.349**，**multi_format=true** | vertical 5/5 valid（p699 unscorable） | no_frame 0/6 | **vert** | 1.0 |

**wz7 纸型分布（前 3）**：892.5×1323 610 页 / 705×1083.8 582 页 / 921.8×1439.2 554 页。
→ 不能把 892.5×1323 当全书唯一纸型；scan2pdf 必须报 `paper_mixed`，构建时要么按主尺寸并标 MANUAL，要么后续按纸型分组/逐页。

**框线证据**（示例）：wz6 p12 `h=5,v=29`、p92 `h=11,v=28`；wz7 p87/350/1049/1398/1661 `h=0,v=0`；wz7 p699 有 2 条长竖线但不足 3 边→判无框。wz7 p10 扉页另有装饰框（未进入 6 页样本），说明**页级框线 ≠ 全书有框**；报告保留例外说明。

**页级横排检查**（验证方向分支，不代表横排书）：

| 书 | 页 | OCR 框数 | median h/w | 判定 | 页级框线 |
|---|---|---|---|---|---|
| wz6 | p159 | 6 | 0.052 | horizontal | true |
| wz7 | p397 | 37 | 0.733 | horizontal | true |

> 两个样书都没有整本横排书；`horizontal_page_check` 只证明「页级横排」可判。横排书型要等 heldout 横排书，不能把 p397 当横排书样本。

### 4.3 探针的失败/降级

- OCR coords 缺失：方向 `unscorable` → 仍需前导 OCR 或用户 `--pipeline`；不猜。
- 首尾封面/扉页不参与方向/框线样本（5%–95%）；若全书 <20 页，回退到中间 6 页并报告 `small_book=true`。
- 纸型多组：`paper_mixed`；构建 v1 用主导尺寸 + `MANUAL_ONLY`（见 §6），不静默。
- 框线 ambiguous：不影响 pipeline，但报告 `frame=ambiguous`，build_vert 自行检测；不阻断。

---

## 5. OCR 数据准备（复用 batch + 参数化 --book）

### 5.1 现状与封装

- **已有**：`api_*` 的提交/轮询/解析/重试代码（`submit`/`poll`/`parse`）、`tmp_vert/battle19/run_batches.py` 的 50 页/批 + 4 并行 + 断点续跑 + 每批 raw JSONL。
- **缺口**：`api_*` 面向候选条带，不是整书整页；需要 `src/tools/ocr_book.py`（本任务只设计，不实现）。
- **建议 CLI**：
```bash
/usr/bin/python3 src/tools/ocr_book.py --book name --src book.pdf \
  --mode A+B --data-dir data/name --token-file /tmp/paddle_token \
  --pages-per-batch 50 --workers 4 --resume
```
- **A payload**：`useLayoutDetection=True, promptLabel='ocr'`；**B payload**：`useLayoutDetection=False, promptLabel='spotting'`；其余同 `run_batches.py`。
- **A+B**：同一页分别提交 A、B；B 产出 `lines/coords`；A 产出 layout/markdown/引号证据；**B 为构建几何主源**，A 只按保守规则补证据。
- **`--book` 参数化**：路径全部 `data/<book>/`，禁止复用 `data/wz7_full`；raw/jobs 每书独立。
- **解析**：A 按 `layoutParsingResults→...`；B 按 `spotting_res→rec_texts/rec_polys`；按 API 返回页序与 batch 页码核对；页数不等→整批失败。
- **断点**：raw 非空/ jobs status=done 即跳过；每个 batch 原子写 `jobs.json`；崩溃只重提未完成批。
- **清毒**：token 只从 `--token-file` 读；报告只写 token 来源路径（可选）和 hash，不写值。

### 5.2 成本/配额（基于已有实测，不新增 API 调用）

| 项 | wz7（1748 页） | 说明 |
|---|---|---|
| A+B API 页 | **3496** | 2×页数 |
| 配额占比 | **8.7%**（40k/天） | 1,748×2/40,000 |
| batch/并行 | 35×2 批 / 4 workers | 50 页/批 |
| A+B API 合计 | ≈6912s≈**115min** | 按 t87 A 3456s×2 |
| A+B 墙钟 | **≈45–65min** | 4 并行（t87 A 32min；A+B 约 2×） |
| 构建 | ≈30min | 全书 build_vert 量级 |
| verify/quality | ≈5–10min | 20 页 gold + verify |
| **总计** | **≈1.5–2h** | 不含人工审阅 |

- 200 页书：A+B 400 API 页=1%；墙钟约 5–10min；构建约 3–5min；总计约 **15–20min**。
- 仅 spotting：成本减半（4.4% 配额、~32min 墙钟），但引号/括号质量差，默认不选。
- 前导 6 页 ×2=12 API 页，<1min；计入上面总量可忽略。
- 配额保护：若 `2×页数 > 0.8×日配额`（>32k 页）→ 拒绝 auto，需拆分/审批；不静默排队。

### 5.3 数据质量与可审计

- 每批 raw + jobs + input SHA；解析后 lines/coords 的页数/总字符数/列数写 report。
- B 的引号/括号问题不掩盖：quality gate 用 PUNCT_EVAL B；A 的文本只在报告/融合候选，不伪造 B 文本。
- per-book fix：`data/<book>/<book>_missed_fix.json` 仅在人工复核后启用；默认 `VERT_MISSED_FIX=0`，绝不加载 `docs/vert_taskF_missed_fix.json`。

---

## 6. 管线选择、构建与质量门禁

### 6.1 路由

```
probe.orientation == vertical   -> build_vert
probe.orientation == horizontal -> build_geom
probe.orientation in (mixed, unscorable) -> exit 4 / 人工
probe.frame: has_frame/no_frame -> 报告；不强制 VERT_FRAME（build_vert 按 src 自检）
paper_mixed: 继续构建 + MANUAL_ONLY；报告 dominant/top sizes
--pipeline 显式: 覆盖探针；记录 override=true；若与 probe 冲突，quality 标记 manual
```

- `build_classic`：v1 **不 auto**（缺少可靠的古籍横排分类器）；需要时人工调用。
- `build_pdf_v13`：v1 不 auto（layout+spotting 组合的历史路径；接口/依赖不同）。

### 6.2 构建命令（竖排示例）

```bash
VERT_MISSED_FIX=0 \
VERT_TMP=<work>/vert_tmp \
/usr/bin/python3 src/pipelines/build_vert.py \
  <data>/<book>_spotting_lines.json \
  <data>/<book>_spotting_coords.json \
  <out.tmp> <input.pdf>
```

- 若 `data/<book>/<book>_missed_fix.json` 存在：`VERT_MISSED_FIX=<该文件>`；报告 hash。
- 横排：`build_geom.py <lines> <coords> <out.tmp> <input.pdf>`；无 fix 注入。
- `--pages` 调试：设置 `VERT_PAGES`，输出页数=子集；verify 用子集页数；生产未设置。
- 构建失败：保留 tex/log；不自动改 pipeline；exit 5。

### 6.3 verify + quality

```bash
# 竖排
/usr/bin/python3 src/test/verify_vert.py <out.tmp> <coords> <lines> --src-pdf <input.pdf> --json <work>/verify.json
# 横排
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py <out.tmp> <coords> <lines>
/usr/bin/python3 src/tools/punct_eval.py --mode sequence --gold <data>/punct_sequence_gold.json --pdf <out.tmp> ...
/usr/bin/python3 src/tools/content_eval.py --gold <data>/content_gold.json --pdf <out.tmp> --coords ... --lines ...
/usr/bin/python3 src/tools/quality_gate.py ...
```

- 任意新书没有 gold：punct/content → `UNSCORED`；**不能 auto**；v1 输出 `MANUAL_ONLY`，报告说明缺 gold。
- 有 per-book gold 时（20 页）才给 punct/content；must-pass 64/54（CONTENT_EVAL v1.1）与 B 口径（PUNCT_EVAL v1.3）均为 provisional，不得用 auto 落库。
- verify 硬约束：页数 1:1、整页丢失 0、越界 0；失败不替换 `--out`。

---

## 7. 失败模式与行为（清单）

| 失败 | 检测 | 行为 | 重试/降级 |
|---|---|---|---|
| PDF 打不开/加密/0 页 | 步骤 0 | exit 2，不 OCR | 无 |
| 缺 token/无权限 | 步骤 4 前 | exit 2，不提交任何 batch | 无；提示 token 路径 |
| token 失效/401 | API 返回 | exit 2；jobs 不标 done | 不重试 4xx |
| OCR 5xx/网络 | submit/poll | 4 次退避；批失败保留 job 状态 | 重跑失败批；`--resume` |
| OCR 轮询超时（3600s） | 步骤 4 | 标失败；不解析半批 | 可重提该批 |
| API 返回页数≠batch 页数 | 解析 | 整批失败，不补空页 | 重提该批 |
| 书型 mixed/unscorable | 步骤 1/2 | exit 4；写 probe | 人工 `--pipeline`；不静默 |
| 书型误判（显式冲突） | 步骤 3 | 探针 vs `--pipeline` 冲突 → 报告 override；quality manual | 不自动改 |
| 横排书误选 vert | 构建/verify 可能不报 | 用 probe+前导；失败不盲目换 geom；exit 4/5 | 人工复核源页 |
| 纸型 multi_format | 步骤 1 | `paper_mixed=true`；用主导尺寸 + MANUAL_ONLY；报告 top sizes | v2 按纸型分组/逐页 |
| `--ocr-mode=layout` 但非 dry-run | 步骤 3 | `E_LAYOUT_NO_GEOM` exit 4 | 改用 auto/spotting |
| 缺页/页数不 1:1 | 步骤 6/8 | exit 3/6；no out | 重跑 OCR；不伪造空页 |
| 构建/LaTeX 失败 | 步骤 7 | exit 5；candidate/log 保留 | 人工/重跑；不换管线 |
| verify 硬失败 | 步骤 8 | exit 6；`out.candidate.pdf`；不替换 out | 人工 |
| quality REJECT | 步骤 9 | exit 7；candidate/report；不替换 out | 人工；不自动修 |
| quality UNSCORED（无 gold） | 步骤 9 | exit 8 / MANUAL；可交付候选，不宣称 PASS | 建 per-book gold |
| 误套 wz7 fix | 配置检查 | 默认 `VERT_MISSED_FIX=0`；只允许 per-book fix | 立即停止构建 |
| 磁盘/权限 | 任一步 | exit 2/5；保留 jobs/raw | 修复后 resume |
| 输出已存在 | 发布 | 不覆盖；`--force` 未在 v1 接口中；默认拒绝 | 用户显式换 out |

---

## 8. 实现拆分与验收（后续任务，不在本轮）

1. **P1 本地探针**：`scan2pdf.py --dry-run` 输出 paper/frame/orientation/pipeline（复用本轮 `probe_booktype.py`）；验收：wz6/wz7 与 `probe_results.csv` 一致；<10s。
2. **P2 OCR 封装**：`ocr_book.py` A/B/A+B、50 页/批、4 并行、resume；验收：wz7 1748 页页数 1:1，raw/jobs 可重跑；**不新增 wz7 专属路径**。
3. **P3 构建/门禁**：pipeline 路由 + `VERT_MISSED_FIX=0` 默认 + verify/quality + 原子发布；验收：wz6/wz7 与现有输出逐页/文本/门禁对齐（wz7 使用现有数据时不重新 OCR）。
4. **P4 任意书**：无 gold 时 MANUAL_ONLY；有 per-book gold 时 content/punct；混合纸型 v2 分组。
5. **P5 观测**：report JSON/markdown：input hash、页数、probe、OCR 模式/batch/耗时/配额、fix hash、build cmd、verify/quality、exit code。

**本轮已完成的验收**：管线/OCR 入口梳理；接口；书型探针 wz6/wz7 实测；成本；失败清单；设计文档。**未实现、未调 API、未改产品代码/数据、未 commit。**

---

## 9. 局限与待决

1. **无横排整书样书**：horizontal 仅页级验证（wz6 p159 / wz7 p397）；横排书型/`build_geom` 自动路由未验证。
2. **wz7 混合纸型**：v1 只能主导尺寸 + MANUAL；逐页/分组构建需要产品改动，不在本任务。
3. **A+B 融合**：battle17 推荐 A 文本+B 几何；v1 设计保留保守融合，但实现需单测；未融合时 B 的引号偏弱。
4. **无通用 OCR 整书工具**：`ocr_book.py` 需新写；现有 `api_*` 只覆盖候选条带。
5. **质量 gold 缺省**：任意新书无 gold → UNSCORED/MANUAL；不能把 wz7 的 fix/gold 套到新书。
6. **成本/配额**为既有实测外推（t87/t87 A+B 推算），未在本任务新增 API 调用；实际以 jobs elapsed/账单为准。

---

## 10. t159 契约对齐（实现回填，captain 决定）

本节把实现与设计对齐；**设计是契约**，下述条目为 t154 终审 F1–F4 的处理结果。

### 10.1 per-book fix（F1）

- **删除**任何 `CANONICAL_FIX` / 书名→`docs/vert_taskF_missed_fix.json` 映射（违反 §5.3「绝不加载 docs 修复」与书无关原则）。
- 只允许两种来源：
  1. `--fix <path>`：**用户显式 opt-in**（调用方传 wz7 canonical 也走这里）；
  2. `data-dir`（含 `data/<book>/`）内存在 `*fix*.json`，或 `data-dir/fix_pointer.json` 指向该 fix。
- report：`fix={path, source: explicit|book_data|none, sha256}`；无来源时 `VERT_MISSED_FIX=0`。
- 契约测试：`find_fix('', 'wz7')` 在无 data-dir 时返回 `none`（不加载 docs）。

### 10.2 退出码（F2，设计 §2.2 为准）

| code | 含义 | 实现映射 |
|---|---|---|
| 0 | 成功（verify PASS；quality AUTO_PASS **或 MANUAL_ONLY** 可交付） | `ok` |
| 2 | 输入/参数/token/输出已存在（未 `--force`） | `usage`/`out_exists` |
| 3 | OCR 失败 / 数据缺失（重试耗尽、页数不齐、缺 coords/lines） | `ocr`/`data_missing` |
| 4 | 书型不可判/混用/无几何模式 | `book` |
| 5 | build/LaTeX 失败 | `build` |
| 6 | verify 失败（页数/越界/丢失）或页数不 1:1 | `verify` |
| 7 | quality **REJECT**（punct/content） | `reject` |
| 8 | 需要人工（UNSCORED、mixed paper/multi_format、gold 缺失） | `manual` |

- 多纸型：`review_required=true`；AUTO→MANUAL（可交付）；**REJECT 保持 REJECT（exit 7）**，不用多纸型掩盖真问题。
- 与旧实现差异：MANUAL_ONLY 由 `exit 7` 改为 **`exit 0`**（设计 §2.2）；verify 失败由 `exit 8` 改为 **`exit 6`**。

### 10.3 输出已存在（F3）

- **外部 out** 不覆盖 → `exit 2`（未 `--force`）。
- **本工具产物**重跑：默认**不覆盖**；若 report 的 book/input_sha256 匹配，则**复用**已有 out、只重跑门禁（`build.skipped=resume_existing`），
  report 写 `resume=true` + `resume_note='默认不覆盖（未重建）；report.resume=true 仅提示；--force 才重建'`。
- `--force` 才真正重建/覆盖。

### 10.4 报告可审计字段（F4）

`report` 至少包含：`input_sha256`、`fix.sha256`、`build.cmd`、`steps`（name/elapsed_ms，含 data/book_type/build/gate）、
`data.source/mode/coords_sha256/lines_sha256`（OCR 时含 `ocr_mode`、`pages_per_batch`）、`book_type`（含 `source=probe_cache|computed`、`confidence`、`multi_format`）、
`gate.verdict/verdict_effective/exit`、`review_required`、`multi_format_note`、`exit`。

### 10.5 fallback / 前导 / mixed（F5/F6）

- 无探针缓存时 `book_type.source=computed`、`confidence≤0.6`，并写
  `preflight={pages:6, basis:page-size/aspect, confidence:low, note:新书建议先跑 6 页前导人工确认}`；
  有缓存时 `source=probe_cache`、`preflight.confidence=high`。
- **v1 不做 mixed 判定**：`mixed_axis_supported=false` 写入 report 与 `v1_limitations`；mixed/unscorable → exit 4（人工 `--pipeline`），不静默猜。
- OCR：`ocr_book.py` 声明「模式复用、代码独立」（A=layout+ocr，B=spotting；payload/分批/重试/断点语义与 t87 一致），
  契约测试锁定 payload 的 `useLayoutDetection/promptLabel` 与 6 页分批。
