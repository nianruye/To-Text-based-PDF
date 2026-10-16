# AGENTS.md - 项目治理结构

> 本文件定义 issue 分类、分支命名、测试要求、spec 对账规则和完成定义。
> 所有 PR 必须遵守。spec 状态账本见 [spec/README.md](spec/README.md)。

## 1. issue 分类

| 类别 | 标签 | 含义 | 处理流程 |
|---|---|---|---|
| 局部 bug | `local-bug` | 单文件内部逻辑错误，不影响其他文件的行为契约 | fix 分支 -> 改代码 -> 跑 201 测试 -> verify_geom（竖排则 verify_vert） |
| 设计变更 | `design-change` | 改变管线行为（转义规则/临时文件路径/字号公式等） | 先写/改 spec -> spec 确认 -> 测试更新 -> 实现 -> baseline diff |
| 公共接口或兼容影响 | `api-compat` | 改变 argv 顺序/env 默认值/JSON 结构/GMPG 格式/tmp 路径等跨文件契约 | 必须更新 spec/governance/PIPELINE_BEHAVIOR.md -> 全链验证（两条管线 + verify + baseline） |
| 多 issue 同根因 | `root-cause` | 多个表面 issue 源于同一耦合机制 | 先分析根因（coupling_analysis.md）-> 统一方案 -> 分步实施 |

**竖排（`build_vert.py`）适用同一分类**，差异三点：

1. 回归口径不同：竖排不做 pitch/坐标类校验（竖排的「行」是列），改用 `verify_vert.py`（页数 1:1 / 字符量 / 越界）——见 §3。
2. 竖排验证**只能本地跑**（CI 无法执行，理由见 §3 备注），所以竖排 PR 的验证证据必须由提交者在本地跑出并贴进 PR 描述。
3. 竖排与横排**零代码耦合**（不 import `src/utils/*`、env 命名空间不相交、临时文件不重名、不用 GMPG），横竖互不波及；
   但竖排的 argv/env/产物命名属跨管线契约，改动要更新 `spec/governance/PIPELINE_BEHAVIOR.md` 的「竖排管线（build_vert.py）」章节。

## 2. 分支命名

| 前缀 | 用途 | 示例 |
|---|---|---|
| `fix/` | 局部 bug 修复 | `fix/classic-esc-double-backslash` |
| `feat/` | 新功能 | `feat/paper-pipeline` |
| `refactor/` | 重构（不改行为） | `refactor/step7-extract-heading-core` |
| `spec/` | 纯 spec 文档 | `spec/governance-pipeline-behavior` |

## 3. 测试要求

| 层 | 命令 | 何时跑 | 拦什么 |
|---|---|---|---|
| unit 196 | `/usr/bin/python3 -m pytest src/test/unit -v` | 每次 commit | 转义契约 + 纯函数 + `build_vert` 进程级行为（退出码/临时目录） |
| invariants 13 | `/usr/bin/python3 -m pytest src/test/invariants -v` | 每次 commit | 结构不变量 |
| verify_geom 退出码 | `VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py <out.pdf> <coords> <lines>` | PR 合并前（横排） | pitch/溢出/缺页回归 |
| verify_vert 退出码 | `/usr/bin/python3 src/test/verify_vert.py <out.pdf> <coords.json> <lines.json> --src-pdf source_pdf/<book>.pdf` | PR 合并前（竖排，**本地跑**） | 页数 1:1 / 逐页字符量 / 越界（文本 span + 矢量图形）/ 页幅回归 |
| baseline diff | 重跑快照 -> diff `src/test/snapshots/baseline_*.json` | 重构后 | 量化指标漂移 |

> 系统有两个 python：`python3` 命中 mineru venv（无 fitz），`/usr/bin/python3` 有 fitz/opencc/xelatex。测试必须用 `/usr/bin/python3`。

**竖排验证（verify_vert）备注**：

- **实测证据（2026-10-15，wz6 全书 231 页）**：
  `/usr/bin/python3 src/test/verify_vert.py output/wz6/wz6_vert_full.pdf data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json --src-pdf source_pdf/wz6.pdf`
  -> 退出码 0（PASS）：页数 231 = 231（1:1）/ 字符量 68016÷69998 = 97.2%（非预期差异页 0，整页丢失 0）/ 越界 span 0 + 矢量 0 / 页幅相对差 0.00%。
  同一命令对**重跑产物**（`build_vert.py` 重跑 11 秒生成）同样 PASS，且逐页文本与 `output/wz6/wz6_vert_full.pdf` 全等（复现性）。
- **不进 CI**：竖排验证的输入（`output/` 产物 + `data/wz6` OCR 数据）按仓库策略不入库，重建还需 upLaTeX 栈（`texlive-lang-japanese`）与 58MB 源 PDF，
  与现有「不依赖 xelatex/GPU 的最小 CI」定位不符 -> 竖排 PR 由提交者**本地**跑此命令并把输出贴进 PR 描述。
  评估详情与备选方案见 [docs/vert_governance_report.md](docs/vert_governance_report.md) 第三节；契约见 [spec/governance/PIPELINE_BEHAVIOR.md](spec/governance/PIPELINE_BEHAVIOR.md)「竖排管线」。
- **门禁仍只看 `verify_vert.py` 的退出码**（`build_vert.py` 的退出码在 #18 已修：输入缺失 / 编译失败 -> exit 1，
  3 参数调试调用仍 0；但「构建成功」不等于「产物合格」——页数/字符量/越界只能由 verify_vert 判）。

## 4. spec 对账规则

每个 PR 必须关联至少一条 spec：

1. **新功能**：先写 `spec/<type>/XX_function.md`（状态 planned）-> 实现 -> 状态改 implemented
2. **bug 修复**：关联 `spec/governance/PIPELINE_BEHAVIOR.md` 的相关契约 -> 修 -> 若行为变了则更新契约
3. **重构**：关联 `spec/governance/PIPELINE_BEHAVIOR.md` -> 确认行为不变 -> spec 状态不改
4. **竖排改动**（`src/pipelines/build_vert.py` / `src/test/verify_vert.py`）：关联对应分部 spec `spec/vertical/<分部>.md`
   （01 engine / 02 tate_layout / 03 marginalia / 04 frame_lines / 05 pagenum_sequence / 06 derot）；
   若动了 argv / env / 产物命名，同时更新 `spec/governance/PIPELINE_BEHAVIOR.md` 的「竖排管线（build_vert.py）」章节（契约 V1-V9）。
   注意分部 spec 的实现锚点是**行号**，改 `build_vert.py` 后要同步 `spec/vertical/README.md` 的锚点表。

### PR 合并前 spec 对账清单

- [ ] PR 关联了至少一条 spec（spec 文件路径写在 PR 描述）
- [ ] spec 状态已更新（planned -> implemented / implemented 不变 / archived）
- [ ] 209 测试全绿（unit 196 + invariants 13）
- [ ] 横排改动：verify_geom 退出码 PASS（硬约束：页数 1:1 / split 0 / missing 0；或说明为何 FAIL 可接受）
- [ ] 竖排改动：verify_vert 退出码 PASS（硬约束：页数 1:1 / 整页丢失 0 / 越界 0；本地跑，输出贴 PR 描述）
- [ ] baseline diff 无意外漂移（或说明漂移可接受 + 对照 CURRENT_BEHAVIOR_SPEC.md 判断）
- [ ] 如改了公共接口（argv/env/JSON/GMPG/路径）：`spec/governance/PIPELINE_BEHAVIOR.md` 已更新（横排契约 1-6 / 竖排 V1-V9）
- [ ] 如改了 `src/utils/` 共享模块：两条横排管线都验证（不只验一条）；竖排不 import `src/utils/`，不在影响面内
- [ ] 如改了 GMPG 格式：渲染端 + 校验端 + 校准端三方同步验证（竖排不参与 GMPG）

## 5. 完成定义（DoD）

一个 issue/PR 算"完成"需满足：

1. 代码改完 + 209 测试全绿（unit 196 + invariants 13）
2. 横排改动：verify_geom 退出码 PASS（硬约束：页数 1:1 / split 0 / missing 0）
3. 竖排改动：verify_vert 退出码 PASS（硬约束：页数 1:1 / 整页丢失 0 / 越界 0；本地跑，命令与输出写进 PR 描述——CI 无法执行，见 §3）
4. spec 状态已更新（spec/README.md 状态账本）
5. PR 描述含：改了什么 / 为什么 / 影响哪些文件 / 测试结果
6. 如有 baseline diff：人判断可接受（写在 PR 描述，对照 CURRENT_BEHAVIOR_SPEC.md）

## 6. 现有 issue 清单

### 局部 bug（local-bug）

| # | issue | 文件:行号 | 状态 |
|---|---|---|---|
| 1 | classic `_esc_chars` 转义符双反斜杠 `r'\\%'`（LaTeX `\\`=换行，应为 `r'\%'`） | `tex_escape.py` _CLASSIC_PAIRS（原 build_classic.py L200） | 已锁定（unit 测试锁现状，待修时测试转红再转绿） |
| 2 | `escape_tex` 二次转义花括号（`\textbackslash{}` 的 `{}` 被后续 `{`/`}` 规则二次转义） | build_pdf_v13.py L42-44 | 已锁定（unit 测试） |
| 3 | v13 `is_heading_by_md` 引号 replace identity（L139-141 无意义代码） | build_pdf_v13.py L139-141 | 待修 |
| 4 | `test_pitch_rate` 死参（coords_path/lines_path/src_pdf 未传入 run_all） | test_cases.py L73 | 待修 |
| 5 | `line_font` 引用未定义 `FONT_HD`（NameError，疑死代码） | build_geom.py L254 / classic L256 | 待修（先验证是否被调用） |
| 6 | classic `POS_EST_LOG` 裸 `os.environ[]` 取值（未设则 KeyError） | build_classic.py L1125 | 待修 |
| 7 | `fit_common` 临时目录泄漏（`tempfile.mkdtemp` 未 `rmtree`） | fit_common.py L66 | 待修 |
| 8 | `DPI=200` 死代码（fit_common 定义未引用） | fit_common.py L14 | 待修 |
| 9 | classic/fit_common docstring 未改名（仍自称 `build_geom.py` / `fit_positional.py`） | build_classic.py L4 / fit_common.py L4 | 待修 |
| 19 | 竖排页码行合并页丢失（OCR 把「书眉+页码」合成 h≥300 的框 -> `special_rows` 按长行丢弃，p3 无页码渲染） | build_vert.py L125-141 | 待修（见 spec/vertical/03_marginalia.md 已知遗留） |

### 设计变更（design-change）

| # | issue | 影响范围 | 状态 |
|---|---|---|---|
| 10 | `/tmp/seg2_line.*` 并发冲突（geom+classic 同名） | geom L930 + classic L1019 | planned（改路径分 build_name） |
| ~~7~~ | ~~geom `page_pitch` 方差检查含异常值~~ | ~~geom L129~~ | **不修**（设计差异：实测改 inner 后 pitch 89.9%->15.4%，保守策略对现代书正确） |
| 11 | `_esc_chars` 两方分叉（geom 删单反斜杠/classic 删双保留单） | `tex_escape.py` | planned（是否统一需 spec 确认） |
| 21 | 竖排正文列长于版框内框（`\textwidth` 由 OCR 盒长中位拟合 863.7pt，沿文本方向系统性偏松约 8%；实测 p4 正文到 y1171.5 而内框下缘 1113.1） | build_vert.py L99 / spec/vertical/02_tate_layout.md | planned（改动会动全书断列与页数，须重跑基线） |
| 22 | 竖排列距口径差约 9%（全局列距 47.6pt = OCR 列 x0 差中位 vs 源书版框界行线实测 43.5pt；列块自右向左累积偏移，最左列差约 40pt） | build_vert.py L86 / L95 | planned（应以版框界行线列距重拟合） |
| 23 | 竖排逐页版面错位（奇/偶页扫描错位：奇页内框顶 290 / 偶页 315.5；列块用全局拟合值 -> 单页偏差 ±18pt 水平 / ±26pt 垂直） | build_vert.py L101-102（TM_pt / OM_pt） | planned（逐页 `\setlength{\textheight}` 位移探针结果自相矛盾，待查 tate 分页语义） |
| 24 | 竖排界行线 ±1 条（19 页为 10 或 12 条，源书自身缺线/多检一条；未做列距梳状补全） | build_vert.py L670-673 / spec/vertical/04_frame_lines.md | planned |
| 25 | 竖排 OCR 方向参数 `useDocOrientationClassify` 未验证（无 token；验证通过可重跑受影响页 OCR 从源头消除旋转坐标系，`derot_rows` 作为存量数据还原层保留） | src/tools/test_ocr_orientation.py | 待验证（脚本 + 判据已就绪） |
| 26 | `verify_vert` 不覆盖版式保真度（页数/字符量/越界拦得住整页丢失与出页，拦不住列位偏移、字号偏差、界行线 ±1 这类渐进退化） | src/test/verify_vert.py | planned（可加「版框内框/界行线 vs 源图墨迹」抽样对照；会依赖 scipy + 源图） |
| 29 | **无版框书取不到源图侧标定样本**（taskN 新发现）：`_calib_src_page` 复用 §1.98 的**版框槽格**配对，无版框书 `page_metrics` 全 None → `XSCALE`/`PUNCT_SIZE·DX·DY`/`BR_SIZE*`（8 项）回落兜底（= wz6 实测值）→ 无版框书（wz7 类）的字宽压缩与标点/括号字号仍按 wz6 比例渲染 | build_vert.py L3362 `_calib_src_page` / L1258 `frame_geom` | implemented（taskO 无框伪槽格 + taskP 300 页全量：印刷线去除/框优先伪版心/槽内行墨迹下限重试/行槽配平位置先验/短列补救/横排页兜底/页内夹取；**taskP2 300 页验收：`verify_vert` PASS（退出码 0）—— 字符量 99.4%、整页丢失 0、越界 span 0（p104 那 1 条已随「实测文本框夹取」收口）、矢量 0、逐页页幅 0.01%**；taskP2 另收 p35（+128 字，列框兜底重排）/p291（+84 字，NF 注行数加严 + 短列证据补带）与新发现的两页越界（p182 版心夹回纸幅 / p214 小开本页右缘夹本页纸宽），wz6 零回归（tex 逐字节相同 + PASS）；**taskQ 300 页验收：`verify_vert` PASS 保持（页数 300=300 / 字符量 99.5%（99.4% 不降）/ 整页丢失 0 / 越界 span 0 / 矢量 0 / 页幅 0.01%）** —— 收掉 taskP2 两条遗留：①**标定路径命中率 2/250(0.8%) → 221/250(88.4%)**（`_nf_fix_page` 的 OCR→源图**映射方向写反**：`nf_fit` 拟合的是 `OCR = k×源图 + b`，修前却拿 `k×OCR + b` 当结果 → 映射后正文 x 域越出纸幅被「映射后 x 不符」拒掉（224 页，其中 193 页落在纸外），路径整体休眠；修后用**逆映射** `(OCR−b)/k` + `nf_fit_align` 增「映射后行心域 vs 墨迹列心域」**相位择优**（梳状简并：行距 = 1.22×列距 时任何整列错位的残差都 1-2px，245 页里 190 页会选错相位）+ 标定后窗**外扩一个列距**与列带**检测+补齐同口径**（否则边界列被窗缘切掉）；②p24 **82 → 123 字**（「重试口径」改为与框内兜底口径**按渲染字数择优**）；逐页对照 9 页变好/4 页变差（p176/p253/p271 标定后多 1 行判为正文、p214 行碎片标定后如实变短致标定被弃用，均 < 80 字阈值、已逐页给根因与回退开关）；开关 `VERT_NF_FIX_INV` / `VERT_NF_FIT_ALIGN_POS` / `VERT_NF_FIT_LAND` / `VERT_NF_RETRY_BEST`（另 `VERT_NF_FIT_PAD` 为外扩量参数；四个开关全关 = taskP2 口径，tex 逐字节相同）；wz6 零回归（tex 逐字节相同 + PASS）；见 [docs/vert_noframe_report.md](docs/vert_noframe_report.md) + [docs/vert_wz7_300_report.md](docs/vert_wz7_300_report.md)）。原方案（已实施）：加「无框伪槽格」路径 —— 版心 = 正文 OCR 行墨迹包围盒、槽格 = `_ink_bands(cov=0.12)` 列带 + `_align_rows_slots`（与 §1.99 同源），用 `FRAME_REF is None` 开关保证有框书路径不改；见 [docs/vert_paper_agnostic_report.md](docs/vert_paper_agnostic_report.md) §5.3） |

### 公共接口或兼容影响（api-compat）

| # | issue | 契约 | 状态 |
|---|---|---|---|
| 12 | `fit_common` subprocess 调 `python3`（PATH 依赖 mineru venv） | fit_common.py L24 | implemented（ci.yml 设 PATH=/usr/bin） |
| 13 | GMPG 格式 `GMPG<key>ZZ` 跨进程契约 | geom/classic 写 <-> verify/fit_common 读 | implemented（spec 锁定） |
| 14 | argv 三套顺序（geom/classic `SL,CO,OUT,SRC` vs v13 `SRC,OUT,...` vs verify `out,coords,lines`） | 三管线入口 | implemented（spec 锁定） |

### 多 issue 同根因（root-cause）

| # | 根因 | 表面 issue | 分析 |
|---|---|---|---|
| 15 | 暗中耦合（16 env 透传 + /tmp 同名 + GMPG 跨进程 + argv 三套 + DPI 三套） | #10/11/12/13/14 | [docs/coupling_analysis.md](docs/coupling_analysis.md) |

### 已归档（archived）

| # | issue | 状态 |
|---|---|---|
| 16 | verify_geom 无 PASS/FAIL 退出码 | 已修（verify_geom.py L274-298 加退出码） |
| 17 | fit_positional/classic 97 行重复 | 已修（合并到 fit_common.py 90+3+3 行） |
| 18 | 竖排 `build_vert.py` 无 PASS/FAIL 退出码（编译失败退出码仍 0） | 已修（退出码分级：输入缺失/编译失败 -> `sys.exit(1)`；SRC 缺省的 3 参数调试调用只警告、仍 0。**判据实测标定：只有已知类加载期 JT1 报错不判失败 —— 正常全书编译 uplatex rc=1**。unit 8 项锁定；见 docs/vert_fix18_20_27_report.md） |
| 20 | 竖排 `VERT_TMP` 同名并发冲突（并行两次构建共用 `vert.tex/dvi/pdf`） | 已修（默认改为 `/tmp/vert_<输出文件名 stem>_run` 按产物名分离；显式 `VERT_TMP` 仍可覆盖。契约 V2/V6 已同步；并发两实例实测路径不同） |
| 27 | 竖排文档数字与实测漂移（页码/边注/纠正处数/L666 注释右缘） | 已修（独立实测重核：书眉 107 / 页码 122 / 边注 65 / 纠正 18 处 / 右缘 563.1pt；`build_vert.py` 注释 + spec/vertical + docs/vert_v2_report.md 已按真值同步） |
| 28 | 竖排参数是 wz6 实测后硬编码（列数 12/字宽压缩 0.87/标点 0.62+0.81+0.85/括号 0.66/字体墨迹比 0.88-0.94）→ 换书/换字体必然失准 | 已修（**建排前自动标定趟**：§1.955 列数（内框宽÷列距 + 界行线条数互证）+ §1.956 源图墨迹 + 字体探针 → 各参数；显式 env 优先、兜底表保留；wz6 对账表 `N_COL_FRAME` 精确 12 / `XSCALE` -0.8%，`verify_vert` PASS + 覆盖率 ×1.009；见 [spec/vertical/09_calibration.md](spec/vertical/09_calibration.md) + [docs/vert_calib_report.md](docs/vert_calib_report.md)）。**taskN 续修（纸型无关化）**：taskM §6 剩余 6 项人工依赖全部改为**相对量**（页边带/长行/左边注小字 = 页幅比例 ∪ 实测内框缘、版框几何区间 = 页宽/页高比例、小字组件窗 = ×正文字步进）+ 2 项自标定（版框线粗细分界、边注/正文步进比上限）；wz6 上 21 项门限反算 **0.0000%**、`vert.tex` 逐字节不变、`verify_vert` PASS；wz7（921.8×1443pt，无版框）预检通过（列数 16/纸型 921×1443/无版框安全降级）；见 [docs/vert_paper_agnostic_report.md](docs/vert_paper_agnostic_report.md) |

**竖排 issue 来源对照**（#18-#27）：

| 来源 | 对应 issue |
|---|---|
| `docs/vert_arch_report.md` §四 遗留 1（OCR 方向参数未验证） | #25 |
| `docs/vert_arch_report.md` §四 遗留 2（验证不覆盖版式保真度） | #26 |
| `docs/vert_arch_report.md` §四 遗留 5（`build_vert.py` 预存在遗留） | #21 / #22 / #23 / #24 |
| `spec/vertical/03_marginalia.md` 已知遗留（页码行合并页） | #19 |
| 本次治理任务源码核对/重跑**新发现** | #18（退出码 0）/ #20（VERT_TMP 并发）/ #27（文档数字漂移） |

> `docs/vert_arch_report.md` 的遗留 3（spec 锚点随行号漂移）已写入本文件 §4 第 4 条；遗留 4（竖排未纳入治理文件）即本次治理任务。

## 7. Branch Protection 设置指南

仓库 `nianruye/To-Text-based-PDF` 的 master 分支保护设置：

1. GitHub 仓库 -> **Settings** -> **Branches** -> **Add branch protection rule**
2. Branch name pattern: `master`
3. 勾选以下规则：
   - **Require a pull request before merging**
     - Required approvals: `1`（至少 1 人审批）
   - **Require status checks to pass before merging**
     - 搜索并勾选 CI jobs: `lint`、`test-cases`
     - 勾选 **Require branches to be up to date before merging**
   - **Require conversation resolution before merging**（所有评论须解决）
4. **Save changes**

设置效果：
- push 直接到 master 被阻止，必须走 PR
- PR 的 CI（lint + test-cases）全绿才能合并
- 至少 1 人审批
- 所有 review 评论须标记 resolved
- **竖排验证不在 CI 状态检查内**（`verify_vert` 只能本地跑，见 §3 备注）-> 竖排 PR 的验证证据靠 PR 描述人工核对

## 8. Commit 信息规范

格式：`<type>: <描述> [Refs/Closes #<issue>]`

| type | 用途 | 示例 |
|---|---|---|
| `feat` | 新功能 | `feat: 新增论文管线公式识别 (#42)` |
| `fix` | bug 修复 | `fix: classic _esc_chars 双反斜杠转义 Closes #1` |
| `refactor` | 重构（不改行为） | `refactor: 抽取 heading_core 共享模块` |
| `test` | 测试 | `test: 补 escape_tex 超长输入用例` |
| `docs` | 文档 | `docs: 更新 coupling_analysis.md 依赖图` |

规则：
- 描述用中文（与项目一致）
- 关联 issue：`Refs #N`（参考）或 `Closes #N`（关闭）
- 一个 commit 只做一件事（原子提交）
- 重构 commit 不含行为变化（`refactor:` 不改输出）
