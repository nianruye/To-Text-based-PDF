# AGENTS.md - 项目治理结构

> 本文件定义 issue 分类、分支命名、测试要求、spec 对账规则和完成定义。
> 所有 PR 必须遵守。spec 状态账本见 [spec/README.md](spec/README.md)。

## 1. issue 分类

| 类别 | 标签 | 含义 | 处理流程 |
|---|---|---|---|
| 局部 bug | `local-bug` | 单文件内部逻辑错误，不影响其他文件的行为契约 | fix 分支 -> 改代码 -> 跑 146 测试 -> verify_geom |
| 设计变更 | `design-change` | 改变管线行为（转义规则/临时文件路径/字号公式等） | 先写/改 spec -> spec 确认 -> 测试更新 -> 实现 -> baseline diff |
| 公共接口或兼容影响 | `api-compat` | 改变 argv 顺序/env 默认值/JSON 结构/GMPG 格式/tmp 路径等跨文件契约 | 必须更新 spec/governance/PIPELINE_BEHAVIOR.md -> 全链验证（两条管线 + verify + baseline） |
| 多 issue 同根因 | `root-cause` | 多个表面 issue 源于同一耦合机制 | 先分析根因（coupling_analysis.md）-> 统一方案 -> 分步实施 |

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
| unit 133 | `/usr/bin/python3 -m pytest src/test/unit -v` | 每次 commit | 转义契约 + 纯函数 |
| invariants 13 | `/usr/bin/python3 -m pytest src/test/invariants -v` | 每次 commit | 结构不变量 |
| verify_geom 退出码 | `VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py <out.pdf> <coords> <lines>` | PR 合并前 | pitch/溢出/缺页回归 |
| baseline diff | 重跑快照 -> diff `src/test/snapshots/baseline_*.json` | 重构后 | 量化指标漂移 |

> 系统有两个 python：`python3` 命中 mineru venv（无 fitz），`/usr/bin/python3` 有 fitz/opencc/xelatex。测试必须用 `/usr/bin/python3`。

## 4. spec 对账规则

每个 PR 必须关联至少一条 spec：

1. **新功能**：先写 `spec/<type>/XX_function.md`（状态 planned）-> 实现 -> 状态改 implemented
2. **bug 修复**：关联 `spec/governance/PIPELINE_BEHAVIOR.md` 的相关契约 -> 修 -> 若行为变了则更新契约
3. **重构**：关联 `spec/governance/PIPELINE_BEHAVIOR.md` -> 确认行为不变 -> spec 状态不改

### PR 合并前 spec 对账清单

- [ ] PR 关联了至少一条 spec（spec 文件路径写在 PR 描述）
- [ ] spec 状态已更新（planned -> implemented / implemented 不变 / archived）
- [ ] 146 测试全绿（unit 133 + invariants 13）
- [ ] verify_geom 退出码 PASS（硬约束：页数 1:1 / split 0 / missing 0；或说明为何 FAIL 可接受）
- [ ] baseline diff 无意外漂移（或说明漂移可接受 + 对照 CURRENT_BEHAVIOR_SPEC.md 判断）
- [ ] 如改了公共接口（argv/env/JSON/GMPG/路径）：`spec/governance/PIPELINE_BEHAVIOR.md` 已更新
- [ ] 如改了 `src/utils/` 共享模块：两条管线都验证（不只验一条）
- [ ] 如改了 GMPG 格式：渲染端 + 校验端 + 校准端三方同步验证

## 5. 完成定义（DoD）

一个 issue/PR 算"完成"需满足：

1. 代码改完 + 146 测试全绿
2. verify_geom 退出码 PASS（硬约束：页数 1:1 / split 0 / missing 0）
3. spec 状态已更新（spec/README.md 状态账本）
4. PR 描述含：改了什么 / 为什么 / 影响哪些文件 / 测试结果
5. 如有 baseline diff：人判断可接受（写在 PR 描述，对照 CURRENT_BEHAVIOR_SPEC.md）

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

### 设计变更（design-change）

| # | issue | 影响范围 | 状态 |
|---|---|---|---|
| 10 | `/tmp/seg2_line.*` 并发冲突（geom+classic 同名） | geom L930 + classic L1019 | planned（改路径分 build_name） |
| ~~7~~ | ~~geom `page_pitch` 方差检查含异常值~~ | ~~geom L129~~ | **不修**（设计差异：实测改 inner 后 pitch 89.9%->15.4%，保守策略对现代书正确） |
| 11 | `_esc_chars` 两方分叉（geom 删单反斜杠/classic 删双保留单） | `tex_escape.py` | planned（是否统一需 spec 确认） |

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
