# 交付状态（Deliverables）

> 生成日期：2026-11-16 · master `6ce1464f9`（含 PR #22–#41）
> 本目录每本书一个 PDF，命名 `<book>.pdf`。原产物路径见下表「来源」。

---

## 一、可直接交付（7 本，门禁 PASS）

| 书 | 源页 | 产物页 | 大小 | 门禁 | pitch | 来源 |
|---|---:|---:|---:|---|---:|---|
| **ghbq** | 104 | 104 | 3.4 MB | **PASS** | 98.9% | `output/final_v3/ghbq_v3.pdf` |
| **wz1** | 222 | 222 | 3.2 MB | **PASS** | 98.3% | `output/final_v3/wz1_v3.pdf` |
| **wz4** | 677 | 677 | 2.5 MB | **PASS** | 99.5% | `output/final_v3/wz4_v3.pdf` |
| **wz8** | 762 | 762 | 6.3 MB | **PASS** | 95.8% | `output/uploaded/wz8_final2.pdf` |
| **wz8_1** | 77 | 77 | 0.6 MB | **PASS** | 98.7% | `output/uploaded/wz8_1_bold.pdf` |
| **wz9** | 82 | 82 | 2.3 MB | **PASS** | **100.0%** | `output/uploaded/wz9_final.pdf` |
| **wz10** | 60 | 60 | 29.6 MB | **PASS** | 95.2% | `output/uploaded/wz10_toc2.pdf` |

> wz8 是**零调优新书**（标定全兜底，实测字宽 15.41pt）；wz8_1 / wz9 / wz10 同为
> 上传路径产出的新书。**页数全部 1:1。**

---

## 二、可交付但有已知限制（2 本，门禁 REJECT）

| 书 | 源页 | 产物页 | 大小 | 门禁 | pitch | 限制 |
|---|---:|---:|---:|---|---:|---|
| wz3 | 850 | 850 | 6.7 MB | REJECT | 79.1% | 行距偏松（详见下） |
| wz2 | 783 | 783 | 5.3 MB | REJECT | 74.7% | 行距偏松 + 页码错位 |

**缺陷性质**：**页数 1:1、内容完整、可全文搜索**；仅「行距保真度」未达门禁 85% 阈值。
中位 pitch 误差仅 **0.7%**（wz3），问题集中在约 20% 的页（书眉短页 / 章标题页）。

诊断与 7 轮追踪记录：[docs/pitch_gscale_rootcause.md](../docs/pitch_gscale_rootcause.md) · AGENTS #55/#59。

---

## 三、竖排（2 本）

| 书 | 源页 | 产物页 | 大小 | 门禁 | 说明 |
|---|---:|---:|---:|---|---|
| wz6 | 231 | 231 | 1.2 MB | MANUAL_ONLY | 数据缺失（`data_missing`）|
| wz7 | 1748 | 1748 | 104.6 MB | REJECT | 标点回归（`punct_regression`）|

竖排管线与横排**零代码耦合**，验证走 `verify_vert.py`（页数 1:1 / 字符量 / 越界 / 页幅）。

---

## 四、门禁口径

| verdict | 含义 | 处置 |
|---|---|---|
| `PASS` | 全部硬指标达标 | 可交付 |
| `PASS_WITH_DRIFT` | 页数差 ≤ 允许值 | 可交付，差异需知悉 |
| `MANUAL_ONLY` | 数据缺失或内容超人工阈值 | 需人工确认 |
| `REJECT` | 硬指标未达标 | 不可交付，需修 |

**横排硬指标**（`verify_geom`）：页数 1:1、pitch ≥85%、页高误差 <5%、底部占位 <8%、overflow 0。

---

## 五、复现命令

```bash
# ── 横排：调优书（已有 OCR 数据）
/usr/bin/python3 src/tools/scan2pdf.py \
  --input source_pdf/ghbq.pdf --book ghbq \
  --out /tmp/ghbq.pdf --data-dir output/ghbq_full/_ocr_ghbq \
  --skip-ocr --layout --force

# ── 横排：上传的新书（OCR 数据在 output/uploaded/_ocr_<book>/）
/usr/bin/python3 src/tools/scan2pdf.py \
  --input uploads/wz9.pdf --book wz9 \
  --out /tmp/wz9.pdf --data-dir output/uploaded/_ocr_wz9 \
  --skip-ocr --pipeline geom --layout --allow-page-drift 2 --force

# ── 竖排
/usr/bin/python3 src/tools/scan2pdf.py \
  --input source_pdf/wz6.pdf --book wz6 \
  --out /tmp/wz6.pdf --data-dir data/wz6 \
  --skip-ocr --pipeline vert --force

# ── 门禁复算（横排；必须带 --src-pdf，否则 DPI 推算错）
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  <产物.pdf> <coords.json> <lines.json> --src-pdf source_pdf/<book>.pdf
```

**构建必须串行** —— 并行会因 `/tmp` 同名临时文件互相覆盖（实测 wz4 产出 0 页、wz3 12 页）。

---

## 六、每书专属配置（`config/books/<book>.json`）

| 书 | 配置 | 作用 |
|---|---|---|
| wz9 | `footnote_wrap` / `structured_toc_pages:[18]` / `toc_bold_ink` | 脚注折行、英文目录结构化、目录按墨迹判加粗 |
| wz10 | `toc_split_pagenum_pages:[15,16]` | 目录「页码独占行」配对 |

> 这些是**数据驱动的每书选项**，代码里不含书名（AGENTS #57）。

---

## 七、系统能力边界（如实声明）

> **真实定位：「7 本调优/新建书 + 一套能跑通新书的通用路径」，不是「上传任意 PDF 都完美」。**

- 新书能拿到：页数 1:1、内容完整可搜、门禁报告、降级页清单
- 新书可能缺少：与调优书相当的 pitch 精度（95~100%）；每本新书仍可能暴露 1–2 类新排版问题
- 已知限制清单：`AGENTS.md` #53/#54/#55/#59

架构评估与改造路线：[docs/architecture_assessment.md](../docs/architecture_assessment.md)

## 2026-11-17 更新（本会话 24 个 PR）

### 全库统一修复（与书无关）
| 项 | 内容 | PR |
|---|---|---|
| 缺字符 `□◎★` | 几何符号归 CJK 字体（此前**所有书**里都是空白 + 文本层 U+FFFF）| #49 / #59 |
| 标题字号采样上限 | `_h > H_BODY×4` 丢弃（挡竖排封面/图注污染全书标题）| #46 |
| 分隔页按源 y | 不再强制垂直居中 | #46 |

**全库验证**（8 本串行重建，逐页文本比对）：页数全部 1:1，**U+FFFF 全为 0**，
每处文本差异均为缺字符恢复。

### 目录（TOC）
- wz10 专项 15 项修复（配对/缩进/字号/加粗/行距/折行/页码）
- **通用规律**：目录条目字号 ≈ 正文字号（三本实测：wz10 16.92/17.4、wz3 12.96/14.5、wz1 7.20/10.1）
  → 两条 TOC 路径的字号全部改为 `FONT` 倍数（PR #62 / #63）
- 架构说明：[../docs/toc_form_paths.md](../docs/toc_form_paths.md)

### 图文混排
- XY-cut 空间分区 + 侧区绝对定位（PR #47）+ 图注对齐 layout 块（PR #50）
- 仅 wz10 启用（`col_split`），wz8/ghbq 的同类页待逐书开启验证

### 仍未解决
- wz2/wz3 pitch（74.7% / 79.1%）：15 项诊断已记录，根因未找到（7 轮假设全部证伪）
- 目录「按页自动选路」：实测对 wz1/wz3 更差，已回退，保留按书配置
