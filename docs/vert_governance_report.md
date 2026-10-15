# 竖排纳入治理门禁报告

> 任务简报：`docs/vert_governance_task.md`　完成日期：2026-10-15
> 范围：把已完成的竖排管线（`src/pipelines/build_vert.py`，v2 全书 231 页）纳入项目**治理门禁**——
> 跨管线契约（`spec/governance/PIPELINE_BEHAVIOR.md`）、根 `AGENTS.md`（测试要求 / spec 对账 / DoD / issue 清单）、CI 评估、状态账本同步。
> **未改任何代码逻辑**（`build_vert.py` / 横排管线 / `src/test/*` 测试均未改）、**未动四书数据**、未 `git reset`、未 commit（主控统一提交）。

## 一、做了什么

| # | 交付物 | 状态 |
|---|---|---|
| 1 | `spec/governance/PIPELINE_BEHAVIOR.md`：新增「竖排管线（build_vert.py）」章节（契约 V1-V9 + 实测基线 + CI 结论）；验收标准表加 verify_vert 行；实现锚点表加 build_vert/verify_vert 两行；兼容影响矩阵加 7 条竖排行 + 矩阵结论 | 完成 |
| 2 | 根 `AGENTS.md`：§1 竖排分类差异 3 点；§3 加 verify_vert 行 + 实测证据 + 不进 CI 备注 + 退出码坑；§4 加第 4 条（竖排 spec 关联）+ 清单 3 条；§5 DoD 加竖排项；§6 登记竖排 issue #18-#27 + 来源对照表；§7 补「竖排不在 CI 状态检查内」 | 完成 |
| 3 | CI 评估（只评估，**未改 `.github/workflows/ci.yml`**）：结论 = 竖排验证不进 CI，维持本地 PR 前手动跑；理由与备选方案见第三节 | 完成 |
| 4 | `spec/README.md`：governance 区 + implemented 区同步（PIPELINE_BEHAVIOR 说明改为横排 6 契约 + 竖排 V1-V9；新增本报告条目；术语表补 `VERT_*`） | 完成 |
| 5 | 本报告 | 完成 |

**顺带修正（超出简报字面，属同表事实错误，已在下方标注）**：`AGENTS.md` §3/§4/§5 原写「146 测试（unit 133 + invariants 13）」，
实测为 **201（unit 188 + invariants 13）**（命令与输出见第四节）。该数字就在本次要改的测试要求表内，且与竖排行并列会自相矛盾，故一并改为实测值。

## 二、竖排契约逐条源码核对结果（含行号）

核对对象：`src/pipelines/build_vert.py`（924 行，工作区与 HEAD `ff4b5b7` 一致，`git status` 无改动）+ `src/test/verify_vert.py`（268 行）。
核对方法：`grep -n` 全量列举 `os.environ` / `sys.argv` / `import` / `subprocess` + 逐行阅读全文；核对脚本留在 `tmp_vert/gov_*.sh`（5 个，清单见第六节，未入库）。

### 2.1 argv（契约 V1）

| 事实 | 源码依据 | 核对结论 |
|---|---|---|
| `SL CO OUT` 必填、`SRC` 可选 | L13 `SL = sys.argv[1]; CO = sys.argv[2]; OUT = sys.argv[3]`；L14 `SRC = sys.argv[4] if len(sys.argv) > 4 else None` | 顺序与 geom/classic **一致**；**三项无默认值**（geom/classic 有默认值）；SRC 缺省是 `None`（非 `''`） |
| SRC 缺省 = 静默关闭 4 项墨迹特性 | L102 SPECIAL 需 `src_doc is not None`；L396 V_FRAME 同；L669 RIGHT_INK 同；L699 DEROT_ON + L746 `if not DEROT_ON or src_doc is None: return None` | 4 项（书眉页码边注 / 版框线 / 右缘复测 / 旋转页还原），**不报错、退出码仍 0** |
| 无 argparse | L11 只有 `import json, sys, os, subprocess, statistics, re` | 参数缺失走 `IndexError`，无 usage 提示 |

### 2.2 env（契约 V2）：grep 全量 12 个，全部有默认值分支

| # | env | 行号 | 默认（源码写法） | 核对要点 |
|---|---|---|---|---|
| 1 | VERT_PAGES | L15 | `''` | 解析 L841-849；**范围外页号静默丢弃**（L847 `1 <= s <= len(keys)`）；坏格式 -> `ValueError` |
| 2 | VERT_TMP | L16 | `/opt/test/tmp_vert/run` | L17 `makedirs(exist_ok=True)`；默认值**硬编码项目根绝对路径** |
| 3 | VERT_NCOL | L73 | 未设 -> 每页正文列数 90 分位（`_nc[min(len-1, int(0.9*len))]`），无样本 -> 11 | 用 `or` 取默认：**空串等同未设**；非整数 -> `ValueError` |
| 4 | VERT_SPECIAL | L102 | `'1'` | 布尔式；需 SRC |
| 5 | VERT_FRAME | L396 | `'1'` | 布尔式；需 SRC |
| 6 | VERT_LINE_COV | L397 | `0.55` | `float()`；L562 要求 `V_LINE_COV_LO < V_LINE_COV` 才启用兜底 |
| 7 | VERT_LINE_COV_LO | L398 | `0.30` | 同上 |
| 8 | VERT_H_COV | L399 | `0.45` | `float()` |
| 9 | VERT_JIE_LOG | L404 | `'0'` | 布尔式（日志） |
| 10 | VERT_FRAME_DEBUG | L405 | `'0'` | 布尔式（日志） |
| 11 | VERT_RIGHT_INK | L669 | `'1'` | 布尔式；需 SRC |
| 12 | VERT_DEROT | L699 | `'1'` | 布尔式；另需 SRC（L746） |

**布尔类统一写法**（L102/396/404/405/669/699）：`os.environ.get(k, 默认) not in ('0','false','False')`
-> 只有 `0` / `false` / `False` 判关，**其它任何值（含空串）判开**（契约 V2 已写明，属易误用点）。
**命名空间核对**：横排 16 共享 env + v13 独立 5 个均无 `VERT_` 前缀；竖排 12 个全 `VERT_` 前缀 -> 零交集（对照 root-cause #15 的「16 env 透传」耦合，竖排不适用）。

### 2.3 产物与临时文件（契约 V6）

| 事实 | 源码依据 | 核对结论 |
|---|---|---|
| 只落一个产物 `OUT` | L920 `os.replace(TMP/vert.pdf, OUT)` | **脚本不派生产物名**；`output/<book>/<book>_vert_*.pdf` 是调用约定 |
| 中间文件 | L911-912（`vert.tex`）、L916（uplatex -> `vert.dvi`）、L917（dvipdfmx -> `vert.pdf`）、L922-924（`vert.aux/log` 不清理） | 全在 `$VERT_TMP` 下；全跑后实测 TMP 只剩 `vert.aux/dvi/log/tex`（`vert.pdf` 已 `os.replace` 走），与「不留副本」一致 |
| 与横排临时文件不重名 | grep `seg2_line` / `srcpage_` / `fig_` / `toc_map` 在 build_vert.py 均无命中 | 与 issue #10 无关 |
| **并发缺口** | 未设不同 `VERT_TMP` 的并行构建共用 `vert.*` | 新发现 -> 登记 #20 |
| **退出码缺口** | 全文无 `sys.exit`；L922-924 失败分支只 print | **编译失败退出码仍 0** -> 新发现，登记 #18；门禁改用 verify_vert 退出码 |

### 2.4 与横排的差异（契约 V7 对照表，逐条核对）

- **一致**：主参数顺序 `SL CO OUT [SRC]`（L13-14 vs geom L19-22）；验证脚本参数顺序 `out coords lines`（verify_vert L141-143 vs verify_geom L124-133）。
- **有意不同**：引擎（upLaTeX+tarticle+pxchfon，L852-892 vs xelatex+xeCJK）；坐标 DPI（**144 = 2x px**，pt = px÷2，L75-79/180/189/286 vs 200dpi）；页幅来源（SRC PDF 真页尺寸 L87-91 vs coords 极值推导）；页眉页码机制（eso-pic `\put` 逐字绝对定位 vs LaTeX 流）；GMPG（竖排无 vs 横排三方契约）；校准驱动（无 vs fit_positional 两趟）。
- **零代码共享（逐条核对）**：`build_vert.py` 的 import 全量 = `json sys os subprocess statistics re`（L11）+ 函数内 `fitz`（L88/129）、`numpy`（L128/228/497）、`scipy.ndimage`（L139/229/707）——**不 import `src/utils/*`，不 import `src/calibration/*`**。转义是脚本内联第三套（L188/L290/L836，只处理 `% # & _`），故 issue #11 的 `_esc_chars` 分叉**不覆盖竖排**。
- **唯一共享**：OCR spotting JSON 格式与 PaddleOCR-VL 数据源（契约 V3）；竖排只读 `lines`/`coords` 两个文件（L19），`*_labels.json` / `*_markdown.json` 不读。

### 2.5 验收判据（契约 V8）与 verify_vert 核对

| 判据 | verify_vert 行号 | 类型 |
|---|---|---|
| 页数 1:1 | L164-165、L247-248 | 硬 |
| 逐页字符量（`--char-tol` 80，仅非预期页计入 FAIL） | L185-195、L251-253 | 硬 |
| 整页丢失（输出 0 字且源 ≥ 30 字） | L192-193、L254-255 | 硬 |
| 越界（span + 矢量图形，`--bbox-tol` 0.5pt） | L198-202、L249-250 | 硬 |
| 页幅 vs 源书众数（需 `--src-pdf`，相对差 ≤ 0.5%） | L209-219、L256-257 | 硬（可选开启） |
| 退出码 0/1 | L246-264 | - |
| 预期差异页自动识别（CJK 占比 / 最长行，不硬编码页号） | L130-136；阈值 `--noise-min-char` 30 / `--cjk-min` 0.5 / `--long-row` 80（L147-149） | - |
| 字符量总计（68016/69998 = 97.2%） | L182-183 | **只打印，不参与退出码** |

**key 集合口径差异（核对发现，已在契约 V3 记录）**：`build_vert` 用 `sorted(sl.keys(), key=int)`（L20，只 lines）；
`verify_vert` 用 `sorted(set(coords) | set(lines), key=int)`（verify_vert L59，并集）。wz6 两文件同为 231 key，未触发。

## 三、CI 评估（结论 + 理由 + 备选，未改 ci.yml）

### 3.1 事实盘点（核对命令见 `tmp_vert/gov_ci_audit.sh`、`tmp_vert/gov_timing.sh`）

| 项 | 事实 |
|---|---|
| CI 现状 | `.github/workflows/ci.yml` 仅两个 job：`lint`（`ruff check src/ --exit-zero`，**不阻断**）、`test-cases`（`pymupdf` + `test_cases.py`，但基线 PDF `output/成果_wz2_classic_latest.pdf` 被 `.gitignore` 的 `*.pdf`/`output/` 排除且未跟踪 -> **实际每次都 skip**）。CI **不跑 pytest、不跑 verify_geom、不跑 verify_vert** |
| 注 1 | `AGENTS.md` #12 写「ci.yml 设 PATH=/usr/bin」，实测 ci.yml **无 PATH 设置**（本任务未改，如实记录） |
| 竖排验证输入 | `output/wz6/wz6_vert_full.pdf`（789,075 B，**未跟踪**）+ `data/wz6/*_spotting_{coords,lines}.json`（648,889 + 237,705 B，**未跟踪**；`data/wz6` 全目录 1.2MB）。`data/wz1/wz2/wz3` 已跟踪，`data/wz6` 未跟踪 |
| 可选输入 | `source_pdf/wz6.pdf`（58,291,722 B，未跟踪，仓库策略不入库） |
| 重建所需工具链 | upLaTeX：`texlive-binaries`（`/usr/bin/euptex`）+ **`texlive-lang-japanese`**（`tarticle.cls` / `pxchfon.sty`，本机 installed-size 374,858 KB ≈ 366MB）+ `texlive-latex-recommended`（`eso-pic.sty`）+ **`fonts-noto-cjk`**（NotoSerif/Sans CJK ttc，91MB）；python：`pymupdf` + `numpy` + `scipy` |
| 重建耗时（实测） | 231 页全书 **11 秒**（本机，2026-10-15）；6 页预览 1 秒 |
| verify_vert 自身依赖 | **仅 PyMuPDF**（import 只有 argparse/collections/json/sys/fitz）——不需要 upLaTeX / numpy / scipy |
| 仓库体量 | 已跟踪 627 文件 / 94MB（`source_pdf/` 476MB、`output/` 484MB 均不在库内） |

### 3.2 结论

**竖排验证不进 CI**（`ci.yml` 保持原样，本任务未改一行）；竖排 PR 由提交者**本地**跑 `verify_vert.py` 并把输出贴进 PR 描述。

理由（按权重）：

1. **输入不在库内**：竖排验证的输入（产物 PDF + OCR JSON）都不在仓库——`output/` 与 `*.pdf` 被 `.gitignore`，`data/wz6` 未跟踪。CI 里没有可验对象；要靠 CI 出对象就得先重建。
2. **重建的门槛与现有 CI 定位不符**：重建需 upLaTeX 栈（`texlive-lang-japanese` 约 366MB + 字体 91MB）+ 58MB 源 PDF + numpy/scipy，而现有 CI 明确「不依赖 xelatex / GPU」的最小定位（注释写在 ci.yml L3-4）。虽然**重建本身只要 11 秒**（不是耗时问题），但资产与工具链代价相对「只读 PDF 的验证」不划算。
3. **产物入库会造成「假绿」**：把 `output/wz6/wz6_vert_full.pdf` 提交进库，CI 验的是那份**冻结的旧产物**，代码改动后不重建也能 PASS —— 拦不住真正的管线回归，反而给出虚假的通过信号。
4. **竖排验证本地化与横排一致**：横排的 `verify_geom.py` 同样不在 CI（CI 连 pytest 都不跑），竖排并未被特殊对待；门禁强度没有净下降。

### 3.3 备选方案（若要「机器门禁」，供主控决策 —— 本任务未实施）

| 方案 | 成本 | 能拦什么 | 拦不住什么 |
|---|---|---|---|
| A. 现状：本地手动跑 | 0 | 全部竖排硬项（提交者自觉） | 忘记跑 / 跑错产物 |
| B. 把 `output/wz6/wz6_vert_full.pdf` + `data/wz6/*_spotting_{coords,lines}.json`（合计约 1.7MB）入库（或 Git LFS），在现有 `test-cases` job 里加一条 verify_vert（复用已装的 pymupdf） | 改 ci.yml ~8 行 + 破例入库 1.7MB | 提交的**基线产物**被损坏/替换（如误生成预览版覆盖全书） | 代码改动后的重建回归（不重建就验不出） |
| C. CI 重建 + 验证（apt 装 upLaTeX 栈 + Noto CJK 字体 + 提供 58MB 源 PDF 给 `build_vert`，它必须读真源 PDF） | 重（工具链 450MB+ 未含 texlive 基础包 + 资产 58MB + 每 PR 重建 11 秒） | 全部（真回归） | - |

建议：**维持 A**；若目标是「防误提交坏产物」，可选 B（成本低且与现有 `test-cases` 同构）；C 不建议（代价远超收益，且与仓库「数据/产物不入库」策略冲突）。

## 四、实测证据

### 4.1 verify_vert（写进 `AGENTS.md` §3 的命令，逐字实测）

```bash
/usr/bin/python3 src/test/verify_vert.py output/wz6/wz6_vert_full.pdf \
  data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json \
  --src-pdf source_pdf/wz6.pdf --json /tmp/vert_gov_verify.json
```

```
页数: 源 OCR 231 页  |  输出 PDF 231 页  |  ✓ 1:1
字符量: 输出 68016 / OCR 69998 = 97.2%
  [预期差异] p74 输出 263 / OCR 405 (差 142) — OCR 幻觉长行页(单行 137 字)
  [预期差异] p231 输出 0 / OCR 896 (差 896) — OCR 噪声页(非中文: CJK 占比 0.00)
  差异 > 80 字的页: 2 个（预期 2 / 非预期 0）；整页丢失(0 字)页: 0 个
越界: span 0 个 / 矢量图形 0 个（容忍 0.5pt；涉及 0 页）
页幅: 源书众数 595.28x1245.31pt（116/231 页）  |  输出 595.27x1245.33pt  |  相对差 0.00%/0.00%
  （此处略去一行「源书非众数页幅 115 页」与字符量差异最大 12 页明细表）

== 退出码 PASS ==
```

脚本退出码 = 0（`echo $?` 实测）。

### 4.2 复现性（验证结论不依赖某个冻结产物）

```bash
VERT_TMP=/tmp/gov_vert_full /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/gov_vert_full.pdf source_pdf/wz6.pdf
# -> 退出码 0，231 页耗时 11 秒
```

- 重跑产物 vs `output/wz6/wz6_vert_full.pdf`：**231 页逐页文本全等、页幅全等、矢量图形数 4075 = 4075、全书文本字符数 136924 = 136924**（文件大小 789,074 vs 789,075 B，差 1 字节为 PDF 元数据）。
- 对重跑产物跑同一条 verify_vert 命令：同样 PASS（231:1 / 97.2% / 越界 0/0 / 页幅 0.00%）。
- 拟合参数（本次日志首行）：字号 34.4pt / 列距 47.6pt / 列高 863.7pt / 天头 318.6pt / 右缘 563.1pt（OCR 拟合 594.9 -> 墨迹实测修正）/ 列容量 13 / 页 595.3×1245.3pt。

### 4.3 回归测试（本任务不改代码，确认无扰动）

```bash
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
# -> 201 passed in 2.90s   （unit 188 + invariants 13）
```

### 4.4 日志条数类统计（如实记录，与分部 spec 有漂移，见遗留 R1）

本次重跑日志计数：书眉 107 / 页码 122 / 边注 65 / 版框 228 页（兜底 6 页、跳过 0 页）/ 旋转页修正 1 页 / 页码序列纠正 **18 处**（`spec/vertical/README.md` 记 121 / 64 / 19；书眉 107、版框 228 一致）。

## 五、遗留

1. **R1 竖排分部文档数字与实测漂移**（本次重跑核对发现，已登记 `AGENTS.md` #27，**未改分部 spec**）：
   `spec/vertical/README.md` L66-68 记「书眉/页码/边注 107/121/64 条」「页码序列纠正 19 处」，`spec/vertical/05_pagenum_sequence.md` L3/L55 记 19 处；
   本次实测（产物与已验收版逐页全等）为 **107/122/65** 与 **18 处**；另 `build_vert.py` L666 注释写「真右缘 ≈546pt」而实测与 `spec/vertical/02_tate_layout.md` L44 为 **563.1pt**。
   建议后续单独一个 `docs:` commit 同步（本任务不越界改分部 spec）。
   > **R1 已关闭（2026-10-15 竖排收尾修复）**：三个数字已独立复核并同步进 `spec/vertical/*` 与 `build_vert.py` 注释。
   > 其中页码/边注的旧值 121/64 已定位来源 —— 是**关掉 `VERT_DEROT`** 时的计数（p159 旋转页少 1 条页码 + 1 条边注）；
   > 页码纠正 18 处与 derot 开关无关；右缘真值 = 抽样页内框右线中位 563.1pt。详见 [docs/vert_fix18_20_27_report.md](vert_fix18_20_27_report.md)。
2. **R2 治理文件中的第三方数字**：`AGENTS.md` #12 声称「ci.yml 设 PATH=/usr/bin」，实测 ci.yml 无 PATH 设置（本任务只如实记录，未改该行语义）。
3. **R3 CI 备选方案 B 待主控决策**（第三节 3.3）：是否把竖排基线产物 + OCR JSON 入库以换取机器门禁。
4. **R4 spec 锚点随行号漂移**（`docs/vert_arch_report.md` 遗留 3）：本次新增的契约 V9 锚点表同样基于 `ff4b5b7` 的 924 行；改 `build_vert.py` 后须同步 `spec/vertical/README.md` 与本节（已写入 `AGENTS.md` §4 第 4 条）。
   > **R4 已按该规则执行（2026-10-15 竖排收尾修复）**：`build_vert.py` 现为 958 行；`spec/vertical/*` 与
   > `PIPELINE_BEHAVIOR.md` V9 锚点已全部重算同步。**本文第二节的行号仍是 924 行版的历史记录**（核对基准已写明），查现行锚点请走上述两处。
5. 竖排自身的 6 条工程遗留已按现有格式登记为 issue（`AGENTS.md` §6 #18-#26），其中 #21-#24 是版式保真类（改动会动全书断列/页数，需重跑基线），#18/#20/#27 为本次核对新发现。

## 六、约束遵守声明

- 未改任何代码逻辑：`src/pipelines/build_vert.py`、`src/pipelines/build_geom.py`、`src/pipelines/build_classic.py`、`src/test/**` 均未改
  （本次改动仅 4 个文档文件：`AGENTS.md`、`spec/README.md`、`spec/governance/PIPELINE_BEHAVIOR.md`、本报告；任务开始前工作区已有的无关改动
  —— `:Zone.Identifier` 删除与其它未跟踪目录 —— 一律未触碰）。
- 未动四书数据（`data/wz*`）与 `source_pdf/`；重跑产物写到 `/tmp`，未覆盖 `output/wz6/*`。
- 未改 `.github/workflows/ci.yml`（CI 评估仅出结论与备选）。
- 未 `git reset`、未 commit；改动与新文件已 `git add`，由主控统一提交。
- 核对脚本落在 `tmp_vert/gov_audit.sh`、`tmp_vert/gov_ci_audit.sh`、`tmp_vert/gov_timing.sh`、`tmp_vert/gov_evidence.sh`、`tmp_vert/gov_repro_check.sh`（scratch 目录，未入库）。
