# 结构规则标题检测与字体分配 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用结构规则（文本模式 + 视觉高度 + 居中位置）替代字体分类器，实现标题检测和字体分配。

**Architecture:** 在 build_pdf_v13.py 中内联添加两个辅助函数（detect_heading_signal, get_heading_font），删除/替换分类器相关代码块，正文统一使用 songti 字体。

**Tech Stack:** Python, PyMuPDF (fitz), LaTeX/xelatex, xeCJK 宏包

---

## 文件结构

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `/opt/test/build_pdf_v13.py` | Modify | 添加辅助函数，删除/替换分类器代码 |

---

### Task 1: 添加辅助函数 detect_heading_signal 和 get_heading_font

**Files:**
- Modify: `/opt/test/build_pdf_v13.py` (在 render loop 之前，约 line 943)

- [ ] **Step 1: 在 body_buf 定义之前（约 line 943）插入辅助函数**

找到 `body_buf = []` 这一行（约 line 944），在其上方插入以下代码：

```python
    # ══ Structural heading detection (replaces font classifier) ══
    # Pattern library for Chinese document headings
    def detect_heading_signal(t, x_left, line_w_px, page_width_px,
                              h, body_h_avg, y_pt,
                              COORD_HEADING_RATIO, HDR_REGION_Y, MIN_HEADING_WIDTH):
        """结构规则标题检测。
        返回 (signal_name, md_level) 或 (None, 0)。
        signal ∈ {'L1','L2','L3','coord_heading','centered'}"""
        # Basic filters: length, not in header region
        if not (3 < len(t) < 45 and y_pt > HDR_REGION_Y):
            return None, 0
        
        # L1: 第X章/节/部分/编/篇 (chapter-level, highest)
        if re.match(r'^第[一二三四五六七八九十百千零\d]+[章节部分编篇]', t):
            return 'L1', 2
        
        # L2: X.X hierarchical numbers (e.g., 1.1, 2.3.1)
        if re.match(r'^[\d]+(\.[\d]+)+', t):
            return 'L2', 2
        
        # L2: Arabic numeral + separator (e.g., 1., 2．)
        if re.match(r'^[\d]+[.．、]', t):
            return 'L2', 2
        
        # L2: 专题X (topic markers)
        if re.match(r'^专题[一二三四五六七八九十\d]+', t):
            return 'L2', 2
        
        # L3: Chinese numeral + separator (e.g., 一"、二、)
        if re.match(r'^[一二三四五六七八九十]+[.．、"""]', t):
            return 'L3', 2
        
        # L3: Chinese numeral in parens (e.g., （一）、(2))
        if re.match(r'^[(（][一二三四五六七八九十\d]+[)）]', t):
            return 'L3', 2
        
        # coord_heading: visually tall line (height ratio)
        if body_h_avg > 0 and h / body_h_avg > COORD_HEADING_RATIO and line_w_px > MIN_HEADING_WIDTH:
            return 'coord_heading', 2
        
        # centered short line: centered + short
        x_center = x_left + line_w_px / 2
        page_center = page_width_px / 2
        if abs(x_center - page_center) < page_width_px * 0.1 and len(t) < 20:
            return 'centered', 2
        
        return None, 0
    
    def get_heading_font(signal):
        """signal → CJK font command."""
        if signal in ('L1', 'L2'):
            return '\\CJKfamily{heiti}'
        return '\\CJKfamily{kaiti}'  # L3, coord_heading, centered
```

- [ ] **Step 2: 保存文件，确认语法无误**

运行快速语法检查：
```bash
python3 -c "import ast; ast.parse(open('/opt/test/build_pdf_v13.py').read())" && echo "Syntax OK"
```

Expected: `Syntax OK`

---

### Task 2: 删除 font-style heading detection 代码块

**Files:**
- Modify: `/opt/test/build_pdf_v13.py:1070-1081`

- [ ] **Step 1: 删除 lines 1070-1081 的 font-style heading detection 块**

找到以下代码块并删除：

```python
        # ── Font-style heading detection (scan PDFs) ──
        # For non-text-layer PDFs, use the pre-classified font style to detect
        # subheadings: heiti/bold + short + non-indented → likely a heading.
        if not has_text_layer and md_level == 0 and not coord_heading and not is_header and not is_footnote_start(t) and y_pt > HDR_REGION_Y:
            _pre_style = line_font_styles.get(key, {}).get(i)
            if _pre_style and _pre_style.get('confidence', 0) > 0.8:
                _fam = _pre_style.get('family', 'songti')
                _bold = _pre_style.get('bold', False)
                _is_non_indented = x_left < BODY_LEFT + INDENT_THRESHOLD_PX
                if ((_fam == 'heiti' or _bold) and 3 < len(t) < 45 and _is_non_indented):
                    md_level = 2  # treat as subheading
```

删除后该位置应直接进入 Pattern-based detection 块。

- [ ] **Step 2: 语法检查**

```bash
python3 -c "import ast; ast.parse(open('/opt/test/build_pdf_v13.py').read())" && echo "Syntax OK"
```

---

### Task 3: 替换 pattern-based subheading detection 为结构规则调用

**Files:**
- Modify: `/opt/test/build_pdf_v13.py:1082-1087` (删除后约 line 1070)

- [ ] **Step 1: 替换原有的 pattern-based detection 代码块**

找到以下代码块（删除 Task 2 后位置可能上移）：

```python
        # ── Pattern-based subheading detection (scan PDFs) ──
        # Lines like "1.xxx" or "2.xxx" that are short and
        # not in the header region are likely numbered subheadings.
        if not has_text_layer and md_level == 0 and not coord_heading and not is_header and not is_footnote_start(t) and y_pt > HDR_REGION_Y:
            if re.match(r'^[0-9]+[.．、]', t) and 5 < len(t) < 50:
                md_level = 2  # treat as subheading
```

替换为：

```python
        # ── Structural heading detection (all PDFs) ══
        # Use pattern library + visual signals to detect headings.
        # Replaces font classifier-based detection.
        if md_level == 0 and not is_header and not is_footnote_start(t):
            # Compute body height average for coord_heading detection
            body_hs = []
            for j in range(max(0,i-5), min(len(lines), i+6)):
                if j == i: continue
                tj = lines[j].strip()
                if not tj or len(tj) < 5: continue
                if j >= len(polys) or not polys[j]: continue
                if min(p[0] for p in polys[j]) > page_width_px * 0.4: continue
                body_hs.append(max(p[1] for p in polys[j]) - min(p[1] for p in polys[j]))
            body_h_avg = sum(body_hs) / len(body_hs) if body_hs else h
            
            # Call structural detection function
            _sig, _mlvl = detect_heading_signal(
                t, x_left, line_w_px, page_width_px,
                h, body_h_avg, y_pt,
                COORD_HEADING_RATIO, HDR_REGION_Y, MIN_HEADING_WIDTH
            )
            if _sig:
                md_level = _mlvl
                _heading_signal = _sig  # store for font lookup later
            else:
                _heading_signal = None
```

- [ ] **Step 2: 语法检查**

```bash
python3 -c "import ast; ast.parse(open('/opt/test/build_pdf_v13.py').read())" && echo "Syntax OK"
```

---

### Task 4: 替换 heading font 分配逻辑

**Files:**
- Modify: `/opt/test/build_pdf_v13.py:1262-1298`

- [ ] **Step 1: 找到 heading font 分配代码块**

搜索包含 `# Image-based font detection` 的注释块，约 lines 1262-1298。该块使用 `line_font_styles` 或直接调用 classifier 来设置 `_hfont`。

- [ ] **Step 2: 替换 classifier-based font 分配为结构规则查表**

将整个 `if not _heading_bold and not _heading_italic:` 块（约 lines 1262-1298）替换为：

```python
                # ══ Structural font assignment (replaces font classifier) ══
                # Use heading signal from structural detection to set font.
                if not _heading_bold and not _heading_italic:
                    # Get font from structural signal (if available)
                    if '_heading_signal' in dir() and _heading_signal:
                        _hfont = get_heading_font(_heading_signal)
                    elif coord_heading:
                        # Fallback: coord_heading always → kaiti
                        _hfont = '\\CJKfamily{kaiti}'
                    else:
                        # Default: kaiti for headings
                        _hfont = '\\CJKfamily{kaiti}'
```

注意：这段代码需要放在 heading 渲染块中，位置在 `_hfont` 默认赋值（约 line 1226）之后、style prefix（约 line 1299）之前。

- [ ] **Step 3: 确认原有 _hfont 默认值保留**

原有的 line 1226：
```python
_hfont = '\\rmfamily' if (has_text_layer and not _text_layer_params.get('use_kaiti', True)) else '\\CJKfamily{kaiti}'
```
这行需要保留，作为 fallback。结构规则查表在其后覆盖。

- [ ] **Step 4: 语法检查**

```bash
python3 -c "import ast; ast.parse(open('/opt/test/build_pdf_v13.py').read())" && echo "Syntax OK"
```

---

### Task 5: 正文字体统一为 songti（禁用 per-line classifier）

**Files:**
- Modify: `/opt/test/build_pdf_v13.py:1346-1351`

- [ ] **Step 1: 找到 body_buf.append 代码**

搜索 `body_buf.append({...})`，约 lines 1347-1352。

- [ ] **Step 2: 修改 font_family 为固定 songti**

将：
```python
        _lf = line_font_styles.get(key, {}).get(i, {})
        body_buf.append({
            'text': t, 'indent': (x_left - BODY_LEFT) > INDENT_THRESHOLD_PX,
            'cjk': sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalpha()),
            'font_family': _lf.get('family', 'songti'),
            'bold': _lf.get('bold', False),
        })
```

改为：
```python
        # Body text: default songti (no classifier-based font switching)
        body_buf.append({
            'text': t, 'indent': (x_left - BODY_LEFT) > INDENT_THRESHOLD_PX,
            'cjk': sum(1 for c in t if ord(c) > 0x2000) + sum(0.52 for c in t if c.isascii() and c.isalpha()),
            'font_family': 'songti',  # fixed: no classifier
            'bold': False,  # fixed: no classifier
        })
```

- [ ] **Step 3: 语法检查**

```bash
python3 -c "import ast; ast.parse(open('/opt/test/build_pdf_v13.py').read())" && echo "Syntax OK"
```

---

### Task 6: 运行 build_pdf_v13.py 构建 PDF2/3 并验证

**Files:**
- Run: `/opt/test/build_pdf_v13.py`
- Verify: `/tmp/xelatex_v13.pdf`

- [ ] **Step 1: 运行构建脚本**

```bash
cd /opt/test && python3 build_pdf_v13.py 2>&1 | tail -20
```

Expected: 应输出 `TeX: ... chars` 和 `xelatex` 运行结果，生成 `/tmp/xelatex_v13.pdf`。

- [ ] **Step 2: 验证 PDF 输出存在**

```bash
ls -la /tmp/xelatex_v13.pdf && echo "PDF OK"
```

Expected: 文件存在，大小 > 100KB

- [ ] **Step 3: 检查关键标题字体**

手动或用 pdftotext 检查输出 PDF 中以下内容的字体：

| 原文 | 期望字体 | 验证方法 |
|------|---------|---------|
| `专题一恩格斯与科学社会主义的"科学性"` | heiti (黑体) | 打开 PDF 查看 |
| `一"恩格斯问题"与科学社会主义` | kaiti (楷体) | 打开 PDF 查看 |
| `1.作为无产阶级...` | heiti (黑体) | 打开 PDF 查看 |
| 正文行（如 `中得到进一步说明`）| songti (宋体) | 打开 PDF 查看 |

**手动验证**：打开 `/tmp/xelatex_v13.pdf`，目视检查上述内容的字体样式。

---

### Task 7: 运行 build_pdf_v13.py 构建 PDF1 并验证（带文本层）

**Files:**
- Run: `/opt/test/build_pdf_v13.py` (切换 SRC_PDF 为 PDF1)
- Verify: 输出 PDF

- [ ] **Step 1: 确认 PDF1 配置**

检查 build_pdf_v13.py 中的 SRC_PDF 配置是否可切换为 PDF1（优化前.pdf 或类似）。

如果需要修改源文件路径：
```python
SRC_PDF = '/opt/test/优化前.pdf'  # 或相应路径
```

- [ ] **Step 2: 运行构建**

```bash
cd /opt/test && python3 build_pdf_v13.py 2>&1 | tail -20
```

- [ ] **Step 3: 验证 PDF1 输出**

PDF1 有文本层，标题字体应与原文一致。正文应为 songti。

---

### Task 8: 提交改动

**Files:**
- Commit: `/opt/test/build_pdf_v13.py`

- [ ] **Step 1: 查看改动差异**

```bash
cd /opt/test && git diff build_pdf_v13.py | head -100
```

- [ ] **Step 2: 提交代码**

```bash
cd /opt/test && git add build_pdf_v13.py && git commit -m "feat: structural heading detection (replaces font classifier)

- Add detect_heading_signal() for pattern-based heading detection
- Add get_heading_font() for rule-based font assignment
- L1/L2 (第X章, X.X, 专题X, N.) → heiti
- L3/coord_heading/centered → kaiti
- Delete font-style heading detection block (was causing false positives)
- Body text fixed to songti (no classifier-based switching)"
```

---

## 自查清单

**1. Spec coverage:**
- ✅ L1/L2/L3 pattern detection → Task 1, Task 3
- ✅ coord_heading detection → Task 1, Task 3
- ✅ centered detection → Task 1, Task 3
- ✅ heiti font for L1/L2 → Task 1 (get_heading_font)
- ✅ kaiti font for L3/coord/centered → Task 1 (get_heading_font)
- ✅ Delete font-style heading detection → Task 2
- ✅ Replace heading font assignment → Task 4
- ✅ Body text = songti → Task 5
- ✅ Verification PDF2/3 → Task 6
- ✅ Verification PDF1 → Task 7

**2. Placeholder scan:**
- ✅ 无 TBD/TODO
- ✅ 所有代码块完整
- ✅ 无 "implement later" 或 "add validation"

**3. Type consistency:**
- ✅ detect_heading_signal 返回 (str, int) 或 (None, 0)
- ✅ get_heading_font 返回 str (LaTeX 命令)
- ✅ _heading_signal 变量名一致