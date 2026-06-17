# OCR 版面分析标题检测改进说明

**改进日期**：2026-06-17
**核心改进**：启用 PaddleOCR 版面分析，用 OCR 标题标记直接判断标题，取代易受 OCR 噪声影响的"高度比"间接判断

---

## 一、背景与问题

### 之前方案的局限

原方案用**结构规则 + 视觉高度比**判断标题：
- `coord_heading`：高度比 > 1.25
- `centered`：居中 + 高度比 > 1.1
- `L3 无分隔符`：高度比 > 1.15

**问题**：扫描件 OCR 把字体高度差异"吃掉"，导致：
- 标题和正文高度差很小（如 `二科学社会主义...` 高度比仅 1.097）
- 长标题被拆成多行（如 `第一章《社会主义...》` + `写作的时代背景...`）
- 弯引号编码问题（如 `一"恩格斯问题"`，已用正则修复但脆弱）

### 解决方向

PaddleOCR 的 `useLayoutDetection` 模块能**直接识别标题区域**，输出标签：
- `paragraph_title`：段落标题
- `doc_title`：文档标题
- `header`：页眉
- `text`：正文
- `footnote`：脚注

用这些标签作为 ground truth，比间接的"高度比"更可靠。

---

## 二、改进方案

### 2.1 OCR 调用启用版面分析

`run_spotting_ocr.py`：

```python
# 修改前
"useLayoutDetection": False,

# 修改后
"useLayoutDetection": True,  # 启用版面分析，获取标题标记
```

启用后输出新结构（`parsing_res_list`），每个 block 包含：
- `block_label`：类型标签（标题/正文/脚注等）
- `block_content`：文本内容
- `block_polygon_points`：坐标

### 2.2 提取标题文本集合

新增 `extract_titles.py`，从 layout 数据提取所有标题文本：

```bash
python3 extract_titles.py <lines_file> <labels_file> <out_file>
```

输出 `ocr_titles2.json` / `ocr_titles3.json`（按页的标题文本列表）。

### 2.3 build_pdf_v13.py 集成

#### 新增参数

```python
SPOTTING_TITLES = sys.argv[5] if len(sys.argv) > 5 else ""  # OCR标题集合文件
```

#### 新增归一化函数

```python
def normalize_text(text):
    """去空白 + 统一引号，用于标题文本匹配"""
    s = re.sub(r'\s+', '', text)
    s = s.translate(_QUOTE_MAP)  # 弯引号→直引号
    return s
```

统一处理 OCR 不同来源的空格/引号差异。

#### OCR 标题检测（优先级最高）

```python
if spot_titles and not is_header and not is_footnote_start(t):
    _norm_t = normalize_text(t)
    if _norm_t in spot_titles:
        # 完整匹配
        md_level = 2
        _heading_signal = 'ocr_title'
        _ocr_target_title = _norm_t
    elif len(_norm_t) >= 10:
        # 前缀匹配：处理长标题被拆成多行的情况
        for _otitle in spot_titles:
            if len(_otitle) > len(_norm_t) + 5 and _otitle.startswith(_norm_t):
                md_level = 2
                _heading_signal = 'ocr_title'
                _ocr_target_title = _otitle
                break
```

#### 续行合并增加 OCR titles 目标

`Markdown-based merge` 块增加 OCR titles 作为 merge 目标：

```python
# 1. 优先用 Markdown headings
for h_text, level in md_headings:
    ...

# 2. 如果无 Markdown，检查 OCR titles（前缀匹配时记录的）
if not target_h_norm and _ocr_target_title:
    target_h_norm = _ocr_target_title
```

---

## 三、检测优先级（更新后）

| 优先级 | 检测方式 | 条件 | 适用 |
|--------|---------|------|------|
| 1 | **OCR 标题匹配** | 行文本（或前缀）匹配 OCR 标题集合 | 所有 PDF（有 labels 时） |
| 2 | coord_heading | 高度比 > 1.25（扫描件） | PDF2/PDF3 |
| 3 | Text-layer heading | 文本层字体大小 | PDF1 |
| 4 | Structural heading | 文本模式正则（L1/L2/L3） | 所有 PDF |

OCR 标题匹配优先级最高，因为它最准确（直接来自版面分析）。其他方式作为 fallback。

---

## 四、解决的问题案例

### 案例1：高度比不够的标题

```
原文：二科学社会主义"科学性"的理论内涵和思想实质
高度比：1.097（< 1.15 阈值）
```

**之前**：不满足任何检测条件 → 渲染为正文
**现在**：OCR 标题匹配 → 渲染为 kaiti 标题 ✅

### 案例2：长标题被拆成多行

```
旧逐行 OCR：
  line0: 第一章《社会主义从空想到科学的发展》
  line1: 写作的时代背景及其问题意识

OCR 完整标题：第一章《社会主义从空想到科学的发展》写作的时代背景及其问题意识
```

**之前**：line0 单独渲染为标题，line1 渲染为正文（空行）
**现在**：前缀匹配识别 line0 为标题开头 + 续行合并 → 完整标题 ✅

```latex
\centering 第一章《社会主义从空想到科学的发展》\\
写作的时代背景及其问题意识\par
```

### 案例3：弯引号标题

```
原文：一"恩格斯问题"与科学社会主义
```

**之前**：需要修复正则加入 Unicode 弯引号（脆弱）
**现在**：OCR 标题匹配（normalize_text 统一引号）→ 直接识别 ✅

---

## 五、使用方法

### 5.1 重新跑 OCR（启用版面分析）

```bash
# PDF2
python3 run_spotting_ocr.py "/opt/test/优化前2.pdf" \
  "/opt/test/spotting_lines2_layout.json" \
  "/opt/test/spotting_coords2_layout.json"

# PDF3
python3 run_spotting_ocr.py "/opt/test/优化前3.pdf" \
  "/opt/test/spotting_lines3_layout.json" \
  "/opt/test/spotting_coords3_layout.json"
```

自动生成：
- `spotting_lines2_layout.json`：文本内容
- `spotting_coords2_layout.json`：坐标
- `spotting_lines2_layout_labels.json`：版面标签

### 5.2 提取标题集合

```bash
python3 extract_titles.py \
  spotting_lines2_layout.json \
  spotting_lines2_layout_labels.json \
  ocr_titles2.json
```

### 5.3 构建 PDF（用旧逐行数据 + 新标题集合）

```bash
python3 build_pdf_v13.py \
  "/opt/test/优化前2.pdf" \
  "/opt/test/成果_v13_PDF2_final.pdf" \
  "/opt/test/spotting_lines2.json" \       # 旧逐行数据（渲染用）
  "/opt/test/spotting_coords2.json" \      # 旧逐行数据（渲染用）
  "/opt/test/ocr_titles2.json"             # 新标题集合（标题检测用）
```

**注意**：渲染用旧逐行数据（粒度匹配），标题检测用新 OCR 标题集合。

---

## 六、为什么用旧逐行数据渲染？

新版面分析按"块"输出（一个 text block = 一整段正文），与构建脚本的"逐行渲染"粒度不兼容：
- 旧 OCR：每页 ~30 个逐行 block（适合逐行排版、stretch）
- 新版面分析：每页 ~11 个 block（整段正文无法逐行排版）

**方案**：
- **渲染**：用旧逐行 OCR 数据（spotting_lines2.json + coords）
- **标题检测**：用新 OCR 标题集合（ocr_titles2.json，文本匹配）

两者通过 `normalize_text` 归一化后文本匹配关联。

---

## 七、验证结果

### PDF2（30页）

| 标题 | 字体 | 状态 |
|------|------|------|
| `二科学社会主义"科学性"的理论内涵和思想实质` | kaiti | ✅ |
| `一"恩格斯问题"与科学社会主义` | kaiti | ✅ |
| `专题一恩格斯与科学社会主义的"科学性"` | heiti | ✅ |
| `专题二从必然王国到"自由王国"...` | heiti | ✅ |
| `专题三恩格斯关于未来社会基本特征...` | heiti | ✅ |

### PDF3（29页）

| 标题 | 字体 | 状态 |
|------|------|------|
| `第一章《社会主义从空想到科学的发展》写作的时代背景及其问题意识` | heiti | ✅（续行合并） |
| `一澄清杜林思想对19世纪后半期德国工人党思想的有害影响` | kaiti | ✅（续行合并） |
| `二驳斥杜林对马克思学说的歪曲，重塑马克思恩格斯...` | kaiti | ✅ |

### 成果文件

```
/opt/test/成果_v13_PDF2_final.pdf  30页  0错误
/opt/test/成果_v13_PDF3_final.pdf  29页  0错误
```

---

## 八、改进对比总结

| 方面 | 改进前 | 改进后 |
|------|--------|--------|
| 标题检测依据 | 结构规则 + 高度比（间接） | OCR 版面分析标签（直接） |
| 低高度比标题 | 漏检（如 1.097） | ✅ 准确识别 |
| 多行拆分标题 | 需手动续行合并 | ✅ 前缀匹配自动合并 |
| 弯引号 | 需修复正则 | ✅ normalize_text 统一 |
| 鲁棒性 | 受 OCR 高度噪声影响 | ✅ 不依赖高度 |

---

## 九、Git 提交

```
647606b feat: OCR layout detection for heading identification
- run_spotting_ocr.py: useLayoutDetection=True
- extract_titles.py: 新增标题提取工具
- build_pdf_v13.py: SPOTTING_TITLES + normalize_text + 前缀匹配 + merge
- ocr_titles2/3.json: 标题集合数据
```

---

## 十、未来工作

- 可考虑用新版面分析数据**完全替代**旧逐行数据（需修改渲染逻辑支持整段正文）
- 可提取 OCR 的 `block_label` 区分标题层级（如 `title` vs `paragraph_title`）映射不同字体
- 对 PDF1（带文本层）也可应用 OCR 标题匹配作为补充