# Hermes PDF Pipeline — 更新同步文档

> 最后更新: 2026-06-21
> 给 Claude Code 的上下文同步：所有改动、已知问题、流水线参数

---

## 一、流水线架构

```
源PDF → run_spotting_ocr.py (spotting) → spotting_lines/coords.json
      → extract_titles.py → ocr_titles.json
      → build_pdf_v13.py (xelatex + xeCJK) → 成果_v13_*.pdf
         (PaddleOCR-VL-1.6 API)
```

**两个入口：**
- **Web 上传** `http://localhost:8765` — FastAPI 后端，上传 PDF 自动跑全流程
- **命令行** `python3 build_pdf_v13.py 输入.pdf 输出.pdf spotting_lines.json spotting_coords.json [ocr_titles.json]` — 直接调用（需先跑 OCR）

---

## 二、已修复的问题（按时间线）

### 1. 标点间距过大（WeasyPrint → xelatex）
- **根因**：WeasyPrint 不支持 `text-spacing-trim`，无法做 CJK 标点挤压
- **修复**：换用 xelatex + `xeCJK` 引擎，`\xeCJKsetup{PunctStyle=kaiming}` 开明式标点挤压
- **文件**：`build_pdf_v13.py`

### 2. CSS `text-align: justify` 拉散标点
- **根因**：WeasyPrint 对 justify 的 CJK 文本在每个字符间均匀分配空白
- **修复**：`text-align: justify` → `text-align: left`

### 3. 每行文字被当作独立段落 → 跨页续文误缩进
- **根因**：OCR markdown 每行末尾都加 `\par`，xelatex 把每行当一段
- **修复 v1**：只在双换行（真实段落边界）处分段，单换行合并为空格
- **修复 v2**：全局 `\parindent=0pt` + 正文段显式 `\hspace{2em}`，跨页首行智能判断是否缩进（不再用 `\everypar` hack，xeCJK 下不生效）

### 4. 脚注标记 `$ ^{①} $` 未转换
- **根因**：`_blocks_to_markdown` 缺少 `clean_ocr_text` 步骤
- **修复**：添加 `_clean_ocr()` 方法，正则 `\$\s*\^\{([^}]+)\}\s*\$` → `<sup>\1</sup>`

### 5. 跨页断句 / 行末不占满
- **根因**：源 PDF 每页 OCR 独立，xelatex 重排后字符宽度不同
- **修复**：`post_process_pages()` — 合并跨页句子片段（从 `build_pdf.py` 移植）

### 6. 页码对齐（正文区页码与源印刷页码逐页精确匹配）
- **修复**：`extract_page_numbers.py` 从 spotting 缓存提取每页底部页码锚点，自动拟合 `页码 = 逻辑序号 + offset`
- **算法**：`逻辑序号 = key − 正文起始key − (key之前的重复页数)` 统一处理三种情况——重复页（隐藏页码、后续压缩）、缺失页（自动填充）、前言区噪声（正文起始检测后丢弃）
- **渲染**：每页 `\setcounter{page}{N}`；无页码页（前言区/重复页）用 `\thispagestyle{empty}` 隐藏页脚
- **验证**：PDF1（35-53）、PDF2（109-138）、PDF3（2-18）三份输出页脚逐页对齐源印刷页码

### 7. 大文档自动分批 OCR（解除 PaddleOCR-VL 单次 ≤100 页限制）
- **根因**：API 单次提交最多 100 页，之前几百页整书需**人工切割**成 <100 页分别跑
- **修复**：两条 OCR 入口（CLI `run_spotting_ocr.py`、web `processor.py`）直接上传路径加自动切片分批
- **算法**：`BATCH_SIZE=90`（留 10 页余量）；`fitz.insert_pdf` 切成 ≤90 页临时 PDF → 逐批上传 → **偏移合并**：全局 key = `batch_start + 切片内局部页号` → `finally` 清理临时目录
- **关键修复**：API 返回 jsonl **1 行 = 1 文档**，`result.layoutParsingResults` 是**页数组**（每元素=一页）。原解析只取 `[0]`（CLI）/ `pl.extend()` 合并所有页（web）—— 多页 PDF 会丢页/全压进 page 0。改 `_parse_page(lpr)` 逐元素解析
- **校验**：每批解析页数必须 `==` 切片页数，否则 raise（防丢页/多页致坐标全错）；3 次重试 + 指数退避
- **进度**（仅 web）：分批时在 10-90 区间按批插值，executor 线程经 `asyncio.run_coroutine_threadsafe` 投递回主 loop
- **边界**：PNG 逐页路径（JPEG 扫描书）天然不限页数，不参与分批；消费层（`build_pdf_v13.py`/`extract_page_numbers.py`）只认全局连续 key，不动
- **验证**：拼接 132 页测试 PDF → 2 批（90+42）→ 132 页 key 连续 0-131，API 接受 90 页大切片

---

## 三、关键参数（自动推导）

| 参数 | 来源 | 值 |
|---|---|---|
| 起始页码 | 源 PDF 第一页文本（正则 `[•·]\s*\d+\s*[•·]`） | 35 |
| 页面尺寸 | `fitz.open()[0].rect` | 194×297mm |
| 字号 | 固定（可从 OCR block heights 推导） | 12pt |
| 边距 | `(page_width - 25*font_size)/2` | 44.3mm |
| 行距 | `setstretch{1.49}` ≈ `line-height: 1.8` | 1.49 |
| 每行字数 | 固定 | ~25字 |

---

## 四、文件清单

### 核心流水线
- `build_pdf_v13.py` — xelatex 渲染流水线（自动参数版，目录页用 group_toc_rows 配对；argv[7]=页码表，无页码页隐藏页脚）
- `run_spotting_ocr.py` — PaddleOCR-VL-1.6 API 调用（spotting 逐行模式）
- `extract_titles.py` — 从 layout 版面标签提取标题集合
- `extract_page_numbers.py` — 从 spotting 缓存提取页码锚点，自动拟合线性公式（容忍重复页/缺失页/前言区噪声），输出 page_numbers*.json
- `spotting_lines*.json` / `spotting_coords*.json` — OCR 行级文本+坐标缓存
- `ocr_titles{2,3}.json` — 标题集合（标题检测用）
- `page_numbers{1,2}.json` / `page_numbers3_final.json` — 页码表（key→印刷页码）

### Web 应用（`/opt/test/app/`）
- `main.py` — FastAPI 路由（upload, websocket, download）
- `services/processor.py` — **已重写**：API OCR + subprocess xelatex，零重依赖
- `services/pdf_generator_xelatex.py` — xelatex 渲染函数（备用，当前走 subprocess）
- `config.py` — 路径/限制配置
- `templates/index.html` — 前端上传界面

---

## 五、已知限制

1. **页数不严格对齐**：xelatex 重排后页数可能与源 PDF 不同（PDF1 源20→输出19页），但正文区**页码已逐页对齐源印刷页码**（重复页/缺失页/前言区自动处理）
2. **依赖 xelatex**：需 `apt install texlive-xetex texlive-latex-extra texlive-lang-chinese fonts-noto-cjk`
3. **OCR API 配额**：每天 40,000 页（AI Studio），Token 在 `/tmp/paddle_token`
4. **样式**：加粗/斜体/表格等未处理，只关注正文+脚注+标题

---

## 六、换 PDF 步骤

**Web 方式**：打开 `http://localhost:8765`，上传即可

**命令行方式**：
```bash
# 1) 跑 OCR（spotting 逐行，可选 layout 版面标签做标题检测）
python3 run_spotting_ocr.py 输入.pdf spotting_lines.json spotting_coords.json

# 2) 提取标题集合（如需 OCR 标题检测）
python3 extract_titles.py spotting_lines.json spotting_lines_labels.json ocr_titles.json

# 3) 提取页码（复用全页OCR缓存，自动拟合；容忍重复页/缺失页/前言区噪声）
python3 extract_page_numbers.py 输入.pdf page_numbers.json \
  --spotting-lines spotting_lines.json --spotting-coords spotting_coords.json

# 4) 渲染（argv[5]=ocr_titles  argv[6]=markdown  argv[7]=page_numbers.json）
python3 build_pdf_v13.py 输入.pdf 输出.pdf spotting_lines.json spotting_coords.json ocr_titles.json "" page_numbers.json
```

---

## 七、xelatex 排版修复三件套

```latex
% ① 标点挤压
\xeCJKsetup{PunctStyle=kaiming}

% ② 页首缩进控制（全局零缩进 + 显式指定）
\setlength{\parindent}{0pt}
% 正文段需缩进时用 \hspace{2em}，跨页续文首行用 \noindent

% ③ 页码对齐源文档
\setcounter{page}{35}
```
