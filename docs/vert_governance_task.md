# 竖排纳入治理门禁任务简报（给 Claude Code）

> 项目：/opt/test。背景：竖排管线已完成 v2（`build_vert.py`，wz6 全书 231 页）+ 架构正式化（`spec/vertical/` 6 分部 spec、`src/test/verify_vert.py`、`spec/00_system_architecture.md` 竖排条目，见 `docs/vert_arch_report.md`）。**最后一块缺口**：竖排尚未纳入项目的**治理门禁**——`spec/governance/PIPELINE_BEHAVIOR.md`（跨管线契约）与根 `AGENTS.md`（分支/测试/spec 对账/DoD）都只覆盖横排。

## 参考材料（先读）

- `spec/governance/PIPELINE_BEHAVIOR.md` — 现有横排契约（argv / env / JSON / GMPG / DPI / 命名 + 验收 + 锚点 + 兼容影响矩阵）——**竖排契约要对齐它的结构与厚度**
- `AGENTS.md`（**项目根**，当前治理文件：§1 issue 分类 / §2 分支命名 / §3 测试要求 / §4 spec 对账 / §5 DoD / §6 issue 清单 / §7 分支保护 / §8 commit 规范）——注意 `docs/AGENTS.md` 是历史副本，**以根为准**
- `spec/README.md` — 状态账本（governance 区当前只有 PIPELINE_BEHAVIOR 一条）
- `src/pipelines/build_vert.py` — **契约的事实来源**：逐条核对 argv 顺序、全部 `os.environ` 调用及默认值、输出产物命名
- `src/test/verify_vert.py` — 竖排验证脚本（用法/参数/退出码/PASS 判据）
- `docs/vert_arch_report.md`、`spec/vertical/` — 竖排机制与遗留
- `.github/workflows/ci.yml`（若存在）— CI 现状（横排 job 怎么跑的）

## 任务（四件）

### 1. `spec/governance/PIPELINE_BEHAVIOR.md` 加竖排契约
- 新增「竖排管线（build_vert.py）」章节，逐条对照源码写：
  - **argv 契约**：`build_vert.py <lines.json> <coords.json> <out.pdf> <src.pdf>`（**以源码为准核对顺序**）
  - **env 契约**：全部 `os.environ` 变量（如 `VERT_PAGES`、`VERT_SPECIAL` 等——**grep 源码列全**，含默认值与缺失后果）
  - **产物命名**：`output/<book>/<book>_vert_*.pdf` 及其他产物
  - **验收标准**：`verify_vert.py` 的判据（页数 1:1 / 字符量 / 越界 / 退出码）
  - **实现锚点**：关键函数名 + 行号
- **兼容影响矩阵**加竖排行（哪些改动会跨管线影响——预期结论：竖排与横排零代码耦合，唯一共享是 OCR 层与数据格式）
- 标注竖排与横排的**有意差异**（引擎链不同、坐标系不同、argv 位置参数顺序是否一致——逐条实测核对，不要假设）

### 2. 根 `AGENTS.md` 更新
- **§3 测试要求表**加竖排行：命令 `/usr/bin/python3 src/test/verify_vert.py <out.pdf> <coords.json> <lines.json> --src-pdf source_pdf/<book>.pdf`、何时跑（竖排 PR 合并前）、拦什么（页数/字符量/越界回归）；如实测过就贴 PASS 证据
- **§4 spec 对账**：确认竖排 spec 路径已可关联（`spec/vertical/`），如需补一句"竖排改动关联 `spec/vertical/<分部>.md`"就补
- **§6 现有 issue 清单**：如竖排有已知遗留（`docs/vert_arch_report.md` 末尾的 3 条），按现有表格格式登记为新 issue 行
- 其他章节如 §1 分类、§5 DoD 若竖排有特殊性（如"竖排验证只能本地跑"）也一并说明

### 3. CI 评估（只评估，不硬改）
- 看 `.github/workflows/ci.yml`：竖排验证能否进 CI？（关键约束：需要 upLaTeX 编译栈 + `data/wz6` + `output/wz6/wz6_vert_full.pdf`——评估这些是否在仓库/是否适合 CI 时长）
- 给出**明确结论 + 建议**（例如："竖排验证本地 PR 前手动跑，不进 CI，原因 X"——写进 PIPELINE_BEHAVIOR.md 与 AGENTS.md §3 备注）。**不要**擅自改 ci.yml（除非结论是"低成本可加"且改动极小，此时给出 diff 供主控决定）

### 4. 报告
- 写 `docs/vert_governance_report.md`：做了什么 / 每条契约的源码核对结果（含行号）/ CI 结论 / 遗留

## 验收标准

1. `PIPELINE_BEHAVIOR.md` 竖排章节：**每一条 argv/env 都与 build_vert.py 源码逐条核对过**（报告里贴核对依据行号）；兼容影响矩阵有竖排行
2. 根 `AGENTS.md` §3 表含竖排验证行（命令可直接复制执行）；§6 如登记遗留 issue 则格式与现有一致
3. CI 结论明确（含理由），未擅自改动 ci.yml（或给出 diff 待批）
4. `spec/README.md` 状态账本 governance 区同步
5. 报告落盘
6. **不动任何代码逻辑**（`build_vert.py` / 横排管线 / 测试代码均不改；本任务纯契约与治理文档）
7. 201 单元/不变量测试保持全绿

## 约束

- 不改横排管线与四书数据；不 git reset；完成后 `git add` 新文件与改动但不 commit（主控统一提交）
- 复杂 shell 写成脚本文件执行
- 事实必须来自源码/实测，禁止凭印象写契约（不确定的标注"待核"并说明）
