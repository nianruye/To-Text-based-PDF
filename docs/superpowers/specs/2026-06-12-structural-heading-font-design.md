# 结构规则标题检测与字体分配设计

**日期**：2026-06-12
**状态**：已确认，待实现
**目标文件**：`/opt/test/build_pdf_v13.py`

## 背景（Context）

当前 PDF 优化系统使用 CNN 字体分类器（ResNet-18）来识别扫描件中的字体（songti/heiti/kaiti/fangsong），
并据此检测标题和分配字体。该分类器在合成训练数据上 val_acc=99.22%，但在真实扫描 PDF 上不可靠：

- `一"恩格斯问题"与科学社会主义`（真实楷体）→ 被分类为 songti conf=0.991
- `中得到进一步说明...`（真实宋体正文）→ 被分类为 heiti conf=0.99

**根本原因**：合成训练数据与真实扫描件存在域偏差（domain gap）。即使 VLM 也无法在扫描图像中
可靠区分楷体/宋体/黑体。分类器的不可靠导致：
1. 正文被误判为 heiti → 通过 font-style heading detection 被错误提升为标题
2. 标题字体分配错误（如楷体标题被渲染为宋体）

**解决方向**：放弃字体分类器，改用**结构规则**检测标题并分配字体。一套覆盖常见中文文档
标题模式的规则集（不针对单一本书硬编码，也不追求不现实的"全通用自动适配"）。

## 目标

1. 正文不再被误判为 heiti 标题
2. 编号/章节标题正确检测，字体按层级分配（heiti/kaiti）
3. 覆盖常见中文书籍/期刊标题模式
4. 扫描件和带文本层 PDF 统一适用

## 设计概览

用**结构信号**（文本模式、视觉高度、居中位置）替代字体分类器。
检测命中标题后，按信号类型查表分配字体。

- 正文 → 默认 songti（`\setCJKmainfont`，不再用分类器切换）
- L1/L2 编号标题 → heiti（`\CJKfamily{heiti}`）
- L3 中文数字标题 / 高大行 / 居中短行 / Markdown → kaiti（`\CJKfamily{kaiti}`）

## 模式库

| 层级 | 模式（正则） | 字体 | 举例 |
|------|-------------|------|------|
| L1 | `^第[一二三四五六七八九十百千零\d]+[章节部分编篇]` | heiti | 第一章、第3节、第二部分 |
| L2 | `^[\d]+(\.[\d]+)+` | heiti | 1.1、2.3.1 |
| L2 | `^[\d]+[.．、]` | heiti | 1.、2. |
| L2 | `^专题[一二三四五六七八九十\d]+` | heiti | 专题一、专题2 |
| L3 | `^[一二三四五六七八九十]+[.．、"""]` | kaiti | 一"、二、 |
| L3 | `^[(（][一二三四五六七八九十\d]+[)）]` | kaiti | （一）、(2) |
| FB | coord_heading（高度比） | kaiti | — |
| FB | 居中短行 | kaiti | — |

**不使用无编号关键词列表**（附录/参考文献等）——固定列表脆弱且易误匹配。
无编号标题靠**结构信号**（高大/居中）检测，而非枚举关键词。

## 检测优先级（从高到低）

第一个命中的信号决定该行的标题等级与字体。

| 优先级 | 信号 | 条件 | md_level | 字体 |
|--------|------|------|----------|------|
| 1 | Running header | `is_header`（页眉区） | 0 | —（页眉渲染） |
| 2 | Markdown | 在 `md_headings` 列表 | 按源 | kaiti |
| 3 | Footnote | `is_footnote_start(t)` | — | —（脚注渲染） |
| 4 | L1 章节模式 | 见模式库 | 2 | heiti |
| 5 | L2 小节模式 | 见模式库 | 2 | heiti |
| 6 | L3 中文数字模式 | 见模式库 | 2 | kaiti |
| 7 | coord_heading | 高度比 > `COORD_HEADING_RATIO` | 2 | kaiti |
| 8 | 居中短行 | 中心偏差 < 页宽 10% & `len<20` | 2 | kaiti |
| 9 | 无命中 | 正文 | — | songti |

**字体分配与检测分离**：命中标题后，按信号查 `get_heading_font(signal)` 得字体命令。
Arabic-based 模式（L1/L2）→ heiti；其余（L3/coord/居中/markdown）→ kaiti。

## 阈值（沿用现有常量）

- `COORD_HEADING_RATIO`：动态计算（PDF2=1.097，每份 PDF 从 OCR 坐标自动推导）
- 居中偏差：< 页宽 10%
- 居中行长度：`len < 20`
- 非缩进判定：`x_left < BODY_LEFT + INDENT_THRESHOLD_PX`
- 模式行长度范围：`3 < len(t) < 45`
- 标题区域下限：`y_pt > HDR_REGION_Y`
- 最小标题宽度：`line_width_px > MIN_HEADING_WIDTH`

## 集成到 build_pdf_v13.py

全部内联修改（方案 A），不新增模块文件。

### 新增辅助函数（在 render loop 之前）

```python
def detect_heading_signal(t, x_left, line_w_px, page_width_px,
                          h, body_h_avg, has_text_layer, md_level,
                          BODY_LEFT, INDENT_THRESHOLD_PX,
                          COORD_HEADING_RATIO, HDR_REGION_Y, MIN_HEADING_WIDTH):
    """结构规则标题检测。返回 (signal_name, md_level) 或 (None, 0)。
    signal ∈ {'L1','L2','L3','coord_heading','centered'}"""
    if not (3 < len(t) < 45 and y_pt > HDR_REGION_Y):
        return None, 0
    # L1/L2/L3 正则匹配（见模式库）...
    # coord_heading: h / body_h_avg > COORD_HEADING_RATIO
    #                and line_w_px > MIN_HEADING_WIDTH
    # centered: |x_left + line_w_px/2 - page_width_px/2| < page_width_px*0.1
    #           and len(t) < 20

def get_heading_font(signal):
    if signal in ('L1', 'L2'):
        return '\\CJKfamily{heiti}'
    return '\\CJKfamily{kaiti}'  # L3, coord_heading, centered
```

### 改动点

| 位置 | 改动 |
|------|------|
| Lines ~1070-1081 | **删除** font-style heading detection 块（分类器导致正文误判为标题的根源） |
| Lines ~1082-1087 | **替换** pattern-based detection → 调用 `detect_heading_signal()`，命中则 `md_level=2` 并记录 `signal` |
| Lines ~1262-1298 | **替换** 分类器字体分配 → `get_heading_font(signal)` 查表 |
| 正文渲染 | **禁用** per-line font classifier 切换，正文统一 songti |

### 与现有逻辑的交互

- `is_running_hdr` 优先级最高，永不被提升为内容标题（保留）
- text-layer heading detection（`has_text_layer` 模式字号对比）保留（仅 PDF1）
- markdown heading 合并逻辑（多行 OCR 拼回完整标题）保留
- `_heading_align`（对齐检测）、`_this_heading_font`（字号）逻辑保留
- 分类器 import（`from predict import ...`）在 build_pdf_v13.py 中移除

## 验证

1. **PDF1（带文本层）**：构建后标题字体应与原文一致，正文 songti
2. **PDF2/3（扫描件）**：
   - `专题一恩格斯与科学社会主义的"科学性"` → heiti ✅
   - `一"恩格斯问题"与科学社会主义` → kaiti ✅
   - `1.作为无产阶级...` → heiti ✅
   - 正文行（如 `中得到进一步说明`）→ songti，不再误判为 heiti/标题 ✅
3. **回归检查**：无正文行被错误提升为标题
4. 构建命令：`python3 /opt/test/build_pdf_v13.py`（按现有入口运行）

## 范围外 / 未来工作

- 不追求"任意文档全通用自动适配"（不现实）
- 不重训字体分类器（域偏差短期内难消除，结构规则已足够）
- 若将来某类文档模式不被覆盖，可向模式库补充正则（函数内集中维护）
- 无编号标题若与正文视觉无异（同高、不居中、无编号、无 Markdown），
  结构规则无法检测——依赖用户提供 Markdown 文件
