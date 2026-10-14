# 竖排架构正式化任务简报（给 Claude Code）

> 项目：/opt/test（PDF 排版还原系统）。背景：竖排繁体书管线 `src/pipelines/build_vert.py` 已完成 v2（wz6 全书 231 页，完整报告见 `docs/vert_v2_report.md`），但**架构文档 / spec / 回归验证尚未正式化**——本任务把竖排"扶正"为系统的一等公民类型（对标 ancient/modern）。

## 参考材料（先读）

- `docs/vert_v2_report.md` — 竖排 v2 完整报告（**本任务 spec 的主要素材**）
- `/root/.claude/projects/-opt-test/memory/vert_pipeline_eso_pic_pitfalls.md` — 你上一轮写的坑笔记（eso-pic 带星版/墨迹实测/JY1 修法）
- `spec/00_system_architecture.md` — 系统架构（类型分类表 / 共享基础 / 各类型专属逻辑）
- `spec/ancient/README.md` + `01-08`、`spec/modern/README.md` — **spec 格式的参考样本**
- `spec/README.md` — 状态账本（governance/planned/implemented/archived 四区）
- `docs/cards/01_架构梳理行动卡.md` L81-82 — 当时记录的"竖排能力缺口"原文
- `src/test/verify_geom.py` — 横排验证脚本（**`verify_vert.py` 的结构参考**）

## 任务（四件）

### 1. 架构文档补竖排条目
`spec/00_system_architecture.md`：
- "文档类型分类"表加一行（位置在古籍/现代之后）：
  `| **竖排书（繁体/古籍竖排）** | 列序右起、天头/地脚、界行线、边注 | src/pipelines/build_vert.py | ✅ 已实现（wz6 231页） |`
- "各类型专属逻辑"加"竖排书"小节：引擎链（upLaTeX + tarticle + pxchfon[unicode] + Noto Serif CJK TC[3] + dvipdfmx）、tate 参数语义、右缘公式、eso-pic 带星版、墨迹实测定位、derot_rows、版框线、页码序列纠正——**从 docs/vert_v2_report.md 提炼，不要长篇复制**

### 2. 新建 spec/vertical/（对标 ancient/modern 的组织）
- `spec/vertical/README.md`：索引 + 状态表（各分部 spec 的 implemented 状态 + 实现锚点）
- 分部 spec（按机制分，素材来自 docs/vert_v2_report.md + memory 笔记）：
  - `01_engine.md` — 引擎链选型（实验记录：xelatex/bxjscls 无 tate ✗、platex 丢繁体字 ✗、**upLaTeX+tarticle+pxchfon ✓**）+ JY1/JT1 报错修法（disablejfam + JY2 重建 mincho，逐像素 0 差异）
  - `02_tate_layout.md` — tate 参数语义（`\textwidth`=列高、`\textheight`=列区横向容量、**右缘 = 70 + `\oddsidemargin` + `\textheight`**、改 th 必须同步 om、`\par` 必须在 `\fontsize` 组内、papersize×1.00375）
  - `03_marginalia.md` — 书眉/页码/边注（**eso-pic 必须用带星版** `\AddToShipoutPictureFG*`（无星=逐页累积重画）、边缘小字坐标必须源图墨迹实测（OCR bbox 偏 18-40pt）、字号=单字墨高/0.875、步进取组件顶距中位）
  - `04_frame_lines.md` — 版框线（双边：外粗 2.5-4.5pt + 空隙 + 内细 0.5-1.5pt；界行线判据列墨占比>0.55；订口侧扫描只剩内细线、逐页左右交替；横线横跨整幅纸面；淡线栅格拟合兜底 0.25 阈值）
  - `05_pagenum_sequence.md` — 页码序列纠正（分段 + 等差数列拟合 + 邻页插值、PN_TOL=2 放过 ±1、实测纠正 19 处、像素级字形复核方法）
  - `06_derot.md` — 旋转坐标系修复（现象：OCR 把竖排页当横排，行框 1833×47px、坐标超页宽 2 倍；修法 derot_rows：横看行判据 → 源图墨迹字列聚类 → 双向最小二乘取残差小者 → 文本方向中位标定）
- 每条 spec 标注：状态（implemented）、实现锚点（build_vert.py 的函数名/行号）、验收方法
- `spec/README.md` 状态账本：implemented 区加 `spec/vertical/` 条目

### 3. 固化竖排回归验证脚本 `src/test/verify_vert.py`
对标 `verify_geom.py` 的角色（横排用它，竖排用这个）：
- 用法：`/usr/bin/python3 src/test/verify_vert.py <out.pdf> <coords.json> <lines.json> [--src-pdf source_pdf/wz6.pdf]`
- 检查项（本次验收实际用过的逻辑，固化下来）：
  a. **页数 1:1**（重建 PDF 页数 vs OCR lines key 数）
  b. **逐页字符量对照**（重建每页文本 vs OCR lines 每页字数和；差异 > 80 字报警）
  c. **全书 span bbox 越界检查**（x∈[0,W]、y∈[0,H]）
  d. **PASS/FAIL 退出码**（0/1）+ 汇总报告
- **已知预期差异**要做成可配置白名单（OCR 幻觉行页如 wz6 p74、水印页 p231——不要硬编码页号，用"该页 OCR 内容是否含特定标记/噪声特征"判定，或命令行参数传入预期清单）
- 用 `output/wz6/wz6_vert_full.pdf` + `data/wz6/*.json` **实测跑通**，确认输出 PASS（退出码 0）

### 4. OCR 方向分类参数试验（token 不可用 → 只交付脚本+方案）
- 背景：p159 曾出现"OCR 返回旋转坐标系"（渲染层已用 derot_rows 修复），但 API 有官方根治参数：`optionalPayload` 加 **`useDocOrientationClassify: true`**（官方文档："automatically identify and correct images rotated by 0°, 90°, 180°, or 270°"）
- **当前 /tmp/paddle_token 不存在**（WSL 重启清空）→ 本项**只写脚本**：
  - 新建 `src/tools/test_ocr_orientation.py`：读取 token → 取 source_pdf/wz6.pdf 第 159 页渲染 PNG → 分别用 `useDocOrientationClassify=true/false` 提交 API → 对比返回 rec_polys（判据：行框高/宽比、坐标是否超页宽 1191px）→ 打印结论
  - 脚本要能"一条命令跑"（token 放好即用），并在文件头注释写明用法
- 另外把结论**结论留白**：在 `docs/vert_arch_report.md` 里写明"待 token 就绪后跑此脚本验证"

## 验收标准

1. `spec/00_system_architecture.md` 含竖排行 + 竖排专属逻辑小节
2. `spec/vertical/` 建成（README + 6 个分部 spec），`spec/README.md` 已更新
3. `src/test/verify_vert.py` 存在且**实测 PASS**（退出码 0，贴实际输出）
4. `src/tools/test_ocr_orientation.py` 存在（token 缺失时只交付脚本 + 用法说明）
5. 报告写入 `docs/vert_arch_report.md`
6. **不改横排管线**（build_geom.py / build_classic.py / fit_positional*.py 及其测试）；**不改 build_vert.py 的渲染逻辑**（本任务只做文档/spec/验证脚本）
7. 201 单元/不变量测试保持全绿（改了共享文件才需重跑；本任务基本不动代码）

## 约束

- 不动四书（wz1/wz3/wz4/mgfdmg）数据与产物
- 不 git reset；完成后 `git add` 相关新文件但不 commit（由主控统一提交）
- 复杂 shell 写成脚本文件执行（避免转义坑）
- 报告落盘 `docs/vert_arch_report.md`，内容：做了什么 / 关键决策 / 验证结果 / 遗留
