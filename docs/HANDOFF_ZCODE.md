# 项目交接文档（给 ZCode）

> 本文档目标是让接手的 AI/开发者**不依赖对话历史**即可继续本项目。
> 项目仓库：`/opt/test`（WSL Ubuntu-22.04，Windows UNC 路径 `\\wsl.localhost\Ubuntu-22.04\opt\test`）

---

## 1. 项目是什么

**通用扫描书 PDF 还原系统**：任意扫描版书籍自动完成
`OCR → 排版还原 → 质量验证 → 双线 md 产出`，输出与源书 1:1 页数、还原字体/层级/行距的电子 PDF + 供 RAG 用的精品 Markdown。

一句话验收标准：**零特例、四本书全自动通过；修一本书不许弄坏另一本（拒绝"修一本坏一本"）**。

### 管线流程

```
source_pdf/<书>.pdf（扫描件）
  ├─ ① OCR 行级:  src/ocr/run_spotting_ocr.py   → data/<书>/<书>_spotting_{lines,coords}.json
  ├─ ② 版面分析:  src/ocr/run_md_layout.py      → <书>_layout_raw.json (LAYJSON) + 精品 md
  ├─ ③ 排版还原:  src/calibration/fit_positional.py (两趟校准, 底层 build_geom) → output/<书>/<书>_final.pdf
  ├─ ④ 质量验证:  src/test/verify_geom.py       → 页数 1:1 / pitch 误差 / 溢出 / 缺页 / PASS-FAIL
  └─ 辅助工具:    src/tools/ (字体分类/贴图页检测/目录规则提取)
一键脚本: optimize_book.py（--page-images / --toc-rules / --md-layout）
```

## 2. 铁律（违反必翻车）

1. **一律用 `/usr/bin/python3`**，不用 PATH 上的 `python3`（会命中缺 opencc 的 mineru venv）。
2. **排版入口只能是 `fit_positional.py`**（两趟校准），不要直接跑 `build_geom.py`。
3. **多本书必须串行**（并行互相覆盖 `/tmp/seg2_line.pdf`）。
4. **verify 必须带 `VERIFY_PITCH_FLOOR=85`**。
5. **坐标尺度**：coords 的 DPI 随 OCR API 批次漂移（200/142/144 dpi），系统已做 DPI 自适应（`geometry.py` calibrate，max y+1.15 反推）。所有绝对尺寸（字号/缩进/行距）都经 DPI 换算，改几何代码时必须意识到单位是 px@真实DPI。
6. **标题判定权威链**（build_geom）：`LAYJSON 版面标签(LAYOUT_HEADINGS=1) > 目录编号规则(TOC_RULES) > toc_map 目录条目(模糊匹配≥0.72) > (一)(二)模式(is_subhead) > 启发式`。任何一环判定的标题，档位(tier)必须一致，否则同板块字体混用（这是用户最高优先级要求之一）。
7. **测试必须跑**：`/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q`（201 个）。
8. git 改动立即 commit（有被外部工具 git reset 冲掉的历史教训）。

## 3. 四本书现状（2026-08-29 最终验证）

| 书 | 源 PDF | 数据 | 页数/pitch | 字体体系（视觉+用户确认） | 排版 env |
|---|---|---|---|---|---|
| wz1 | source_pdf/wz1.pdf | data/wz1/wz1_spotting_*.json（旧 LAYJSON `data/wz1/wz1.pdf_by_PaddleOCR-VL-1.6 .json`，注意文件名带空格） | 222/222, 97.2% PASS | 章黑/节黑/**三级楷**(AR PL KaitiM GB)/正文宋 | `LAYOUT_HEADINGS=1 LAYJSON="data/wz1/wz1.pdf_by_PaddleOCR-VL-1.6 .json" PAGENUM_GLOBAL_TABLE=data/wz1/wz1_full_pagenum.json FONT_SUBTITLE=kai` |
| wz3 | source_pdf/wz3.pdf | data/wz3/wz3_linelevel_spotting_*.json（**必须用 linelevel**，原始数据 cw=122 多行合并不可用） | 850/850, 79.6% FAIL（**历史固有**，split_polys 估算拆分致坐标噪声；重 OCR 有望 95%+，见待办） | 编宋/章黑/节黑/正文宋 | 无特殊 env（默认全黑体标题） |
| wz4 | source_pdf/wz4.pdf | data/wz4/wz4_spotting_*.json | 677/677, 99.4% PASS | 章黑/节黑/正文宋 | 无特殊 env |
| mgfdmg | **source_pdf/wz5.pdf**（书名≠文件名！） | data/mgfdmg/mgfdmg_spotting_*.json + mgfdmg_layout_raw.json | 407/407, 98.7% PASS | 章宋/节黑/正文宋 | `LAYOUT_HEADINGS=1 LAYJSON=data/mgfdmg/mgfdmg_layout_raw.json PAGE_IMAGE_PAGES=0,1,2 PAGE_IMAGE_PREFIX=/tmp/page_imgs/p FONT_TITLE=song FONT_SUBTITLE=hei TOC_RULES=/tmp/mgfdmg_toc_rules.json` |

### 每本书排版+验证完整命令

```bash
# wz1
LAYOUT_HEADINGS=1 LAYJSON="data/wz1/wz1.pdf_by_PaddleOCR-VL-1.6 .json" \
PAGENUM_GLOBAL_TABLE=data/wz1/wz1_full_pagenum.json FONT_SUBTITLE=kai \
timeout 550 /usr/bin/python3 src/calibration/fit_positional.py \
  data/wz1/wz1_spotting_lines.json data/wz1/wz1_spotting_coords.json \
  output/wz1/wz1_final.pdf source_pdf/wz1.pdf
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  output/wz1/wz1_final.pdf data/wz1/wz1_spotting_coords.json data/wz1/wz1_spotting_lines.json --src-pdf source_pdf/wz1.pdf

# wz3（linelevel）
timeout 550 /usr/bin/python3 src/calibration/fit_positional.py \
  data/wz3/wz3_linelevel_spotting_lines.json data/wz3/wz3_linelevel_spotting_coords.json \
  output/wz3/wz3_final.pdf source_pdf/wz3.pdf
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  output/wz3/wz3_final.pdf data/wz3/wz3_linelevel_spotting_coords.json \
  data/wz3/wz3_linelevel_spotting_lines.json --src-pdf source_pdf/wz3.pdf

# wz4（无特殊 env）
timeout 550 /usr/bin/python3 src/calibration/fit_positional.py \
  data/wz4/wz4_spotting_lines.json data/wz4/wz4_spotting_coords.json \
  output/wz4/wz4_final.pdf source_pdf/wz4.pdf

# mgfdmg（源=wz5.pdf！）
LAYOUT_HEADINGS=1 LAYJSON=data/mgfdmg/mgfdmg_layout_raw.json \
PAGE_IMAGE_PAGES=0,1,2 PAGE_IMAGE_PREFIX=/tmp/page_imgs/p \
FONT_TITLE=song FONT_SUBTITLE=hei TOC_RULES=/tmp/mgfdmg_toc_rules.json \
timeout 550 /usr/bin/python3 src/calibration/fit_positional.py \
  data/mgfdmg/mgfdmg_spotting_lines.json data/mgfdmg/mgfdmg_spotting_coords.json \
  output/mgfdmg/mgfdmg_final.pdf source_pdf/wz5.pdf
```

**产物**：`output/<书>/<书>_final.pdf`（wz1 为 `wz1_v7.pdf` 最新）；Windows 副本在 `C:\Users\xyp\Downloads\*_最终*.pdf`。

## 4. 已完成功能（git log 全景，最新 commit 在顶）

```
3bf6f69 run_md_layout LAYJSON 存盘 dict→list 契约修复
68b7ba1 标题档位一致性: LAYJSON 标题块+(一)(二)模式即 section 档(修 p23 黑体/楷体混用) + classify_fonts 对比法
0dbd32a FONT_TITLE/FONT_SUBTITLE 支持 kai 楷体(补 AR PL KaitiM GB)
0e86301 (一)(二) 模式强制 section 档
362e6c3 (一)(二) 三级标题整类修复(is_subhead 纳入 LAYOUT 兜底 + 字数比判据, 50 个全识别)
109411d wz1 标题/目录五修(layout优先+目录兜底/容差16/目录长条目页码/空格enspace/目录层级字号+一级黑体)
4bb9dca 标题判定目录权威化(is_subhead_cn toc_map 验证 + toc_map 模糊匹配≥0.72)
9d5f82e TOC_RULES 目录定标题级别 + extract_toc_rules.py
9d42869 optimize_book --page-images
1048845 贴图页机制 + FONT_TITLE/FONT_SUBTITLE + 字体分类工具链(sample_font_rows+classify_fonts)
a5abd0c JP→SC 字体 + PunctStyle=kaiming 开明标点
39118b2 书眉式页码页修复(页眉拼接排除页码/顶部页码is_pn/共识匹配≥0.6)
737db94 DPI 反推 max y+1.15(四书 DPI 全对)
1bdef04 DPI 自适应 + verify --dpi 0
3b20eb3 方案A 标题权威化 + 方案B 缩进按源x0还原
f7245cd optimize_book --md-layout
```

## 5. 待办 / 遗留问题（按优先级）

### P0 用户最关心
1. **wz3 pitch 79.6% → 95%+**：根因 = 旧 OCR 数据 cw=122（多行合并）→ split_polys 估算拆分→坐标噪声。解法 = 用现在的 `run_spotting_ocr.py` **重跑 wz3 OCR**（管线已修复，wz4/mgfdmg 用它出 cw≈25-30 干净行级）。成本 850 页额度（用户一天 4 万页，不敏感）。建议先跑 3 页切片验证 cw 正常再全书。
2. **标题误判清零（可选）**：wz1 有 ~13 处疑似正文误判标题（p163"选"——记马克思…"、p1 扉页文字、p3 版权页字段）。用户说"判断错了没关系，一致性最重要"，此条可暂缓，但可加"目录验证收紧"再砍一轮。

### P1 机制完善
3. **错字校对通道（未开始）**：OCR 错字率 0.5-2%，用户明确要求降低（影响知识库质量）。方向：低置信度字符定向 DeepSeek 纠错（memory 有 DeepSeek 处理文本的 system prompt 要求：强调"不是聊天机器人，只输出处理结果"）。
4. **字体分类工具**：视觉模型对"印刷楷体 vs 宋体"不可靠（对比法有改善但不稳定），宋/黑可靠。可考虑更高分辨率裁剪 + 多轮投票。
5. **新书一键流程**：optimize_book.py 已覆盖 OCR→排版→verify，但字体配置（FONT_TITLE/FONT_SUBTITLE）目前要人工跑 classify_fonts 后填。可考虑把 classify_fonts 结果自动回填。

### P2
6. 目录"条目+页码"被 OCR 拆两行是历史问题（已配对处理，但个别书可能还有漏）。
7. wz1 旧 LAYJSON 是官网旧流程产物（块坐标偏差/标签不一致已用容差+兜底消化），有条件可重跑 wz1 的 LAYJSON。

## 6. 关键文件索引

| 文件 | 作用 |
|---|---|
| src/calibration/fit_positional.py | 入口（3 行，调 fit_common） |
| src/calibration/fit_common.py | 两趟校准核心（render/measure_heights/ratio 表） |
| src/pipelines/build_geom.py | **排版主引擎**（1145 行：flow 构建/tier 判定/字体档/目录渲染/贴图页/页眉共识） |
| src/pipelines/_latex_preamble.py | LaTeX 前导（字体家族 heiti/song/kai + kaiming 标点） |
| src/utils/geometry.py | calibrate：DPI 反推/版心/字号/行高 |
| src/test/verify_geom.py | 质量验证（页数/pitch/溢出/缺页，--dpi 0 自适应） |
| src/ocr/run_spotting_ocr.py | 行级 OCR（_PAGE_RAW 收集 layout 原始块） |
| src/ocr/run_md_layout.py | layout 版面分析 + LAYJSON + 精品 md |
| src/tools/classify_fonts.py | 字体分类（抽样→DeepSeek-Vision→按类投票；对比法） |
| src/tools/sample_font_rows.py | 字体抽样裁剪 v5 |
| src/tools/make_page_images.py | 封面/扉页/版权页检测→贴图 PNG |
| src/tools/extract_toc_rules.py | 目录页定位+编号规则提取 |
| optimize_book.py | 一键脚本（--page-images/--toc-rules/--md-layout） |
| docs/coupling_analysis.md | 暗中耦合分析（#15 根因文档） |
| AGENTS.md | 项目治理（issue 分类/测试要求/spec 对账/DoD） |

## 7. 踩坑清单（前人血泪）

1. **`python3` vs `/usr/bin/python3`**：前者命中 mineru venv（无 opencc/fitz），渲染静默失败。
2. **sed/heredoc 转义被 git-bash 吞**：一律 write_file 写 Python 脚本再执行。
3. **`\CJKfamily{song}`/`{kai}` 未定义**会整书标题丢失：新字体家族必须先在 `_latex_preamble.py` 补 `\setCJKfamilyfont`。
4. **fit_common 的 subprocess 用 `env=dict(os.environ)`**：新 env 变量传得进 build_geom，但 fit 主进程 stdout 会吞 build_geom 的 print（debug 要直接跑 build_geom）。
5. **贴图页用 includegraphics 会溢出**：必须 shipout 背景整页铺（不占流）。
6. **DeepSeek-Vision API max_tokens 太小（30）**：推理模型 reasoning_tokens 吃光 budget 返回空 content，用 300。
7. **DeepSeek API key 读取**：Hermes `.env` 在 `C:\Users\xyp\AppData\Local\hermes\.env`（WSL 里是 `/mnt/c/Users/xyp/AppData/Local/hermes/.env`），不是 WSL `~`。
8. **fitz PNG 保存 CMYK compression error**：裁剪图用 PIL 保存。
9. **坐标 px/pt 混用**：OCR coords 是 px@真实DPI，fitz 是 pt，换算是 ×72/DPI。
10. **标题判定"修一个坏一个"**：任何判定改动必须四本书全跑（防回归铁律）。
11. **wz1 LAYJSON 文件名带空格**：`data/wz1/wz1.pdf_by_PaddleOCR-VL-1.6 .json`（`.json` 前有空格），命令里必须引号包裹。
12. **mgfdmg 的源 PDF 是 wz5.pdf**（书名≠文件名）。

## 8. 用户偏好（重要）

- 中文交流；成本不敏感（PaddleOCR 额度一天 4 万页）。
- **排版还原 PDF 自己阅读**，Markdown（layout 精品版）上传知识库做 RAG。
- 会亲自翻 PDF 并给出版式级反馈（行距/字距/标题识别/字体），反馈案例要**修整类**而不是修单个。
- **最高优先级：一个 PDF 内部各板块字体一致**（同类标题必须同字体同字号）；判断错误可接受，但错要整类错。
- 目标：通用系统，拒绝"修一本坏一本"；四本书零特例。
- 代码分工习惯：有实测根因的小改动直接修；复杂开放诊断写任务简报转交。

---

*文档生成：2026-08-29，git HEAD = 3bf6f69*
