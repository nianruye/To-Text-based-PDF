# wz2 排版还原 - 处理逻辑与瓶颈分析

## 当前处理逻辑

### 数据流

```
wz2.pdf（783页扫描古籍《盐铁论校注》，夹注本双规制）
  │
  ├─ PaddleOCR-VL spotting（行级OCR）-> 每行文字+bbox（主数据）
  │     wz2_spotting_lines.json + wz2_spotting_coords.json
  │
  ├─ PaddleOCR-VL layout（版面分析）-> image/aside_text/number/标题 block
  │     wz2.pdf_by_PaddleOCR-VL-1.6.json
  │
  └─ build_geom.py（排版还原）-> fit_positional.py（两趟校准）-> 输出PDF
```

### PaddleOCR 提供的数据

| 数据 | 模式 | 内容 | build_geom 用途 |
|---|---|---|---|
| spotting（行级） | useLayoutDetection=False | 每行**文字 + bbox 位置** | 主数据：文字渲染 + 位置还原 |
| layout（版面） | useLayoutDetection=True | image/aside_text/number/figure_title/paragraph_title 等 block | 图块/旁注/页码/图说明 |

### build_geom 排版还原（5步）

#### 1. 几何标定（从 spotting coords）
- 满行宽 ÷ 满行字数 = 字号
- 行高 -> 行距、版心宽

#### 2. 字号分类（PAGE_FONT=1）
- 预扫描全书分**正文/注释/前言**三类：
  - 正文：行高大（>1.1×H_BODY）-> BODY_FONT（满行26字->18pt）
  - 注释：行高小 -> NOTE_FONT（满行32字->14.7pt）
  - 前言：满行27-31 -> 按满行算（16.2pt）

#### 3. 行距（PER_PAGE_PITCH=1）
- 每页 page_pitch() 测源行间距（spotting 行 y 差中位）
- 大字 bl=源pitch，\fontsize{fnt}{bl} 设 baselineskip

#### 4. 位置还原（POSITIONAL=1）
- 每行按源 y 落位（\vspace 补足）
- 两趟校准：pass1 估高 -> ratio -> pass2 压缩

#### 5. 渲染
- 每行 `\makebox[\textwidth][s]{\rule{0pt}{strut}文本} \\`
- strut = bl - fnt×0.13（定行盒高）
- `\\` 堆叠行，行距=行盒高

### 其他处理
- **标题识别**：行高/toc_map/居中启发式
- **校注标记**：[X]/〔X〕 转上标（MARKER_SCALE 0.55）
- **aside 旁注**：layout content + 目录篇名匹配补全
- **页码**：layout number + 连续推断（前后页±1）
- **书影**：layout image block + 裁源图贴回
- **○->〇**：OCR 识 ○（U+25CB）转 〇（U+3007）
- **【】->〔〕**：OCR 误识白括号转换

---

## 瓶颈分析

### 核心矛盾：LaTeX 行距 = 行盒高（hbox 不重叠）

**源 PDF**（扫描古籍）：
- pitch（行间距）= **35pt**
- 行盒高（墨高+间距）= **37pt**
- 墨高**重叠 2pt**（CJK 排版，行间墨色部分重叠，行间距 < 行盒高）

**build_gem**（LaTeX hbox）：
- 行距 = 行盒高（hbox 堆叠，**不重叠**）
- 要 pitch 35 -> 行盒 35 -> 内容矮 2pt/行 -> **空白多**（361页）
- 要行盒 37 -> pitch 37 -> **溢出**（9页）

**矛盾**：源行间距 < 行盒高（墨高重叠），LaTeX 行距=行盒高（不重叠）。**无法同时 pitch 35 + 行盒 37**。

### \linespread 对大字 makebox 不生效

| | 小字（wz1 10.1pt） | 大字（wz2 15.7pt） |
|---|---|---|
| \linespread | ✅ 生效（pitch=fnt×1.2×linespread） | ❌ 不生效 |
| pitch | =baselineskip | =strut+墨高（行盒高） |

大字改用 bl=_pp 绕过，但 pitch 仍=行盒高（strut+墨高），不是 baselineskip。

### strut + 墨高 = pitch

```
pitch = strut + 墨高 = (bl - fnt×0.13) + 墨高
要 pitch=源35: bl = 35 - 墨高 + fnt×0.13 = 33
但行盒高 = strut + 墨高 = 33-2.4+4.4 = 35（内容矮）
要行盒37: strut=32.6, bl=35, 但 pitch=37（溢）
```

**strut 定行盒高，bl 定 baselineskip，但 LaTeX 行距=max(baselineskip, 行盒)=行盒。** strut 和 bl 耦合，无法独立调。

### 预扫描估高偏低

- 预扫描 _strut_h 用 body 行（排标题/页码）
- 实际渲染含标题/页码/aside，高 > 估
- ratio 校正，但 _pos_sscale 基于 est<cap，不压 -> 溢出页没压

### OCR 数据问题（无法修）

| 问题 | 原因 |
|---|---|
| 〔一一〕->〔一〕 | spotting OCR 漏字 |
| aside content 截断 | layout OCR 识不全（补全靠目录匹配） |
| 波浪线/下划线 | OCR 不识别非文字元素 |
| 正文/注释不区分 | layout 都标 text |

---

## 瓶颈本质

**LaTeX 排版引擎的行距模型 ≠ CJK 古籍排版**：
- LaTeX：行距=行盒高（hbox 不重叠，行间距=行高）
- CJK古籍：行间距<行盒高（墨高重叠，行间距=字心距）

build_geom 用 LaTeX hbox 逐行堆叠，无法复现 CJK 的墨高重叠。这是**引擎层面的限制**，不是参数调能解决。

---

## 当前结果对比

| 指标 | v18（bl=_pp） | v27（bl=_pp-2） |
|---|---|---|
| 页数 | 792 | **783（=源）** |
| 溢出 | 9 | **0** |
| pitch | 37（源35，偏大2） | **35（=源，准）** |
| pitch达标 | 33.0% | **40.3%** |
| 空白页 | 151 | 361 |
| 占位达标 | 81.8% | 51.2% |

### trade-off
- **v18**：pitch 偏大2pt（37），内容填满（空白少151），但 9 页溢出
- **v27**：pitch 准（35），0溢出，但空白多361

---

## 解决方向

1. **\offinterlineskip + 每行 \vskip**：手动控行距 35 + 行盒 37（重叠）。风险高（全局影响，分页/脚注可能乱）
2. **负 \vskip 每行**：\\[-2pt] 重叠。注释说逐行 group 失效
3. **改用别的渲染引擎**（如直接用 PDF 库摆字，不用 LaTeX）
4. **接受 trade-off**：v27（0溢出+pitch准+空白多）或 v18（9溢出+空白少）
