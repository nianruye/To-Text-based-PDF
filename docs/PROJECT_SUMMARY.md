# PDF 排版还原系统 — 项目进度总结

## 项目目标

将扫描型 PDF（图片格式）转换为文字型 PDF，完整还原源文档的排版结构（正文、标题、脚注、页眉、页码等区域的位置和样式）。

**工作目录**：`/opt/test`
**GitHub**：https://github.com/nianruye/To-Text-based-PDF
**测试文件**：
- `wz1.pdf`（205页，单规制排版，正文+脚注）
- `wz2.pdf`（783页，双规制排版，夹注本，排版复杂）
- `优化前.pdf`（马克思价值理论研究，简单排版）
- `优化前2.pdf`（恩格斯与科学社会主义，多级标题）

---

## 核心架构

### 两套方案

| | build_pdf_v13.py（2056行） | build_geom.py（~770行） |
|---|---|---|
| 思路 | 重排（reflow）：OCR → 段落合并 → xelatex 重新断行 | 逐行几何还原：不重排，按 bbox 位置落位 |
| 成熟度 | 生产管线，功能齐全 | 新方案，当前主力开发 |

### 处理流程
```
PDF → PaddleOCR-VL-1.6 spotting → 结构化数据（bbox + 文本）
  → 区域检测（正文/脚注/页眉/标题/页码）
  → 位置还原 + 溢出控制 → xelatex → PDF
```

### OCR 依赖
- PaddleOCR-VL-1.6 API（百度 AI Studio）
- API Token 通过环境变量管理，**不能写死在代码中**
- spotting 模式：逐行获取文本位置和内容

---

## 最新进展（Session d82040a5, 07-02 ~ 07-04）

### 已完成的工作

#### 1. 验证 harness 建立
- `verify_geom.py` — 逐页量输出 vs 源的行数/页高/pitch/占位，含空白+溢出检测
- 支持源页标记对齐（`GMPG` 标记，`VERIFY_MARK=1`），解决溢出页 1:N 对齐问题

#### 2. 基线数据

**wz1 基线（189 张可比正文页）：**

| 指标 | 基线值 | 目标 |
|---|---|---|
| pitch 误差 <3% | 20.6% | >90% |
| 底部占位 <8% 偏差 | 6.3% | >90% |
| 中位底部占位偏差 | +17.5%（输出偏短→空白） | <5% |
| 空白页 | 139/189 | <10 |

**wz2 基线（763 张可比正文页）：**
- pitch 误差中位 40.1%（双规制排版，全局单值 pitch 崩溃）
- 761/763 页空白，中位底部空白 +25.7%
- 源行距双规制：一批 ~17pt，另一批 ~33-44pt

#### 3. 关键发现链

1. **按页 pitch（改动1）** → 渲染层生效但 verify 没变 → 发现混合页（正文+脚注/夹注）小字行数占多，污染了页级 pitch 测量

2. **投影剖面数真实行数** → 前提不成立！OCR 行数完全正确，**没有缺行**

3. **决定性发现**：空白的真凶是**丢失结构性留白**（标题后、章节前的大间隙），不是缺行或密度问题。线性输出把标题和正文挤在一起，丢掉了源文档的结构性间隙 → 内容提前结束 → 底部空白

4. **LINESPREAD bug**：每行 advance 被低估约 1.57×，漏乘了全局 `LINESPREAD`（wz1≈1.568）

#### 4. 最终突破：位置还原 + 两趟校准

**方案**：`USE_POS`（位置还原模式）+ `fit_positional.py` 两趟校准（pass1 渲染→测量实际每页高度→计算 ratio→pass2 按比例压缩）

**wz1 最终结果（07-04，含书影带处理）：**

| 指标 | 值 |
|---|---|
| pitch 误差 <3% | **95.3%** |
| 页高误差中位 | 2.3% |
| 溢成多物理页 | **0** |
| 缺失页 | 0 |
| 页数 | 222（=源） |

**书影页处理**（p28-48 区域，20 页有图）：
- LAYJSON（aistudio layout image block）精确图块 + 启发式 detect_fig_bands 补漏（p45 繁体书影 layout 漏标）
- 上下文字保留 OCR 渲染、书影里文字不识别、图说明居中
- 5 处 POSITIONAL figrow bug 修复 + figrow 图随 gscale/ratio 缩消溢出
- 产物：成果_wz1_rerun8_lay.pdf

---

## 新增/改动的文件

| 文件 | 作用 |
|---|---|
| `verify_geom.py` | 验证 harness：逐页量输出 vs 源的行数/页高/pitch/占位 |
| `build_geom.py` | ①源页标记 `GMPG` ②`page_pitch()` 按页测行距 ③位置还原溢出控制 ④书影带处理（LAYJSON image block + opencc 启发式补漏）⑤图说明居中 ⑥figrow 图随 gscale/ratio 缩消溢 |
| `fit_positional.py` | 两趟校准驱动：pass1 渲染→测量→pass2 按比例压缩 |

---

## 待完成

1. **wz1 完整转换** — ✅ 已完成（222页/0溢出/pitch 95.3%，含书影带处理，产物 成果_wz1_rerun8_lay.pdf）
2. **wz2 适配** — 双规制排版，需要按页/按章节检测行距规制，当前全局单值 pitch 对 wz2 崩溃（40% 误差）
3. **夹注本处理** — wz2 是夹注本（正文行间夹小字双行注），混合页的 pitch 测量需要区分正文行和夹注行
4. **字体识别** — 宋体/楷体/黑体区分，加粗/斜体检测仍不完美
5. **标题层级** — 无序号标题的识别，目录辅助标题定位
6. **标点间距** — 中文标点后的半角空格处理因书而异
7. **Web 端** — 未来需要 Web 上传 PDF → 自动转换的功能

---

## 设计原则

1. **通用性**：不能针对特定 PDF 硬编码参数
2. **区域驱动**：先检测页面各区域，再在各区域内排版
3. **动态适配**：参数通过分析源文档动态计算（中位数等），非固定值
4. **版本控制**：重大改动前存档，通过 git 管理
5. **隐私安全**：API Token 不写入代码

---

## 常用命令

```bash
# 完整流程:spotting OCR(行级) → build_geom 渲染 → fit_positional 两趟校准 → verify

# 1. spotting OCR(需 /tmp/paddle_token,跑一次即可;useLayoutDetection=False 行级)
python3 run_spotting_ocr.py wz1.pdf wz1_spotting_lines.json wz1_spotting_coords.json

# 2. 位置还原 + 两趟校准(主命令;PER_PAGE_PITCH=1 必需,传 SRC=wz1.pdf 贴书影图)
PER_PAGE_PITCH=1 PAGENUM_GLOBAL_TABLE=wz1_full_pagenum.json \
  python3 fit_positional.py wz1_spotting_lines.json wz1_spotting_coords.json 成果_wz1.pdf wz1.pdf

# 3. 带 LAYJSON(aistudio layout 版面分析,精确书影图块;无则启发式 detect_fig_bands 补漏)
LAYJSON="wz1.pdf_by_PaddleOCR-VL-1.6 .json" PER_PAGE_PITCH=1 PAGENUM_GLOBAL_TABLE=wz1_full_pagenum.json \
  python3 fit_positional.py wz1_spotting_lines.json wz1_spotting_coords.json 成果_wz1.pdf wz1.pdf

# 4. 验证 harness(参数顺序:out coords lines --src-pdf)
python3 verify_geom.py 成果_wz1.pdf wz1_spotting_coords.json wz1_spotting_lines.json --src-pdf wz1.pdf --json /tmp/wz1.json
```
