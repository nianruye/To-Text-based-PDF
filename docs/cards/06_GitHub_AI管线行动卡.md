# /opt/test GitHub AI 管线行动卡

> 用在：AI 产出要进入多人协作和主干合并。目标是用 Git + GitHub workflow 把 AI 的改动变成可追溯、可审查、可阻断的工程对象。本项目目前无任何 CI，代码靠人工记忆跑测试。

## 输入

- GitHub 仓库：https://github.com/nianruye/To-Text-based-PDF
- 当前分支：main（无 branch protection）
- 当前状态：无 `.github/workflows/` 目录、无 CI、无 required check
- 已有测试：
  - `src/test/test_cases.py`（17条，依赖 fitz/pymupdf，需预置输出 PDF）
  - `src/test/verify_geom.py`（全局排版指标验证，耗时 2-10 分钟）
- 项目依赖：Python 3.10 + pymupdf + xelatex（TeX Live）
- 大文件问题：wz2 输出 PDF 783页 ≈ 几十 MB，wz2 spotting JSON 也很大

## AI 动作

### 1. 创建最小可用 CI

创建 `.github/workflows/ci.yml`：

```yaml
name: PDF Layout CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install ruff
      - run: ruff check src/

  test-cases:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install pymupdf
      - name: Run test cases (classic pipeline)
        run: |
          # 基线 PDF 通过 Git LFS 或 Release assets 预置
          # 初期可只跑 lint，逐步加入测试
          if [ -f output/基线_wz2_classic.pdf ]; then
            python3 src/test/test_cases.py output/基线_wz2_classic.pdf
          else
            echo "SKIP: 基线 PDF 未预置，仅跑 lint"
          fi
```

### 2. 测试数据策略

由于 wz2 输出 PDF 783页几十 MB，有几种方案：

| 方案 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| **A: Git LFS** | 基线 PDF + spotting JSON 存 LFS，CI checkout 即可跑 | 每次 PR 完整验证 | 需 LFS 配额，clone 慢 |
| **B: Release assets** | 基线 PDF 作为 GitHub Release 附件，CI wget 下载 | 不占仓库空间 | 额外下载步骤，版本管理麻烦 |
| **C: 只跑 lint（初期）** | PR 只跑 ruff check，全量测试用 scheduled workflow 在 main 上跑 | 零配置，最快启动 | 行为回归延迟到合并后 |
| **D: 小样本** | 从 wz2 截取前 20 页做快速测试，替代全量 783 页 | 快速 + 有效 | 只覆盖部分页 |

**推荐路线**：先用方案 C（只 lint）快速启动，同时准备方案 D（20 页小样本）替代全量测试，一个月后评估是否上方案 A（Git LFS）。

### 3. CI 逐步升级路线

| 阶段 | 能力 | 触发条件 | 预期加的时间 |
|------|------|---------|------------|
| **第 1 天** | ruff check src/ | push + PR | 10 分钟 |
| **第 3 天** | test_cases.py（17条，小样本基线 PDF） | PR | 1 小时 |
| **第 1 周** | test_cases.py 扩展 ≥ 25 条 + build_geom 测试 | PR | 2 小时 |
| **第 2 周** | path filters：只跑变更相关的 job | PR | 30 分钟 |
| **第 1 月** | scheduled workflow：每周全量 wz2 验证（783页）+ verify_geom | cron 周跑 | 2 小时 |
| **第 2 月** | 多 Python 版本矩阵（3.10/3.11/3.12） | PR | 1 小时 |
| **按需** | coverage + security scan（pip-audit） | PR | 1 小时 |

### 4. 配合 Git 工作流

issue → branch → commit → PR → CI 自动跑 lint + 测试 → 人审 → merge

```
commit 信息规范：
  feat: 新功能          → feat(calibration): 抽取 fit_common 消除重复
  fix: 修 bug           → fix(build_classic): 附录五标题丢失
  refactor: 重构         → refactor(utils): 抽取 tex_escape 共享模块
  test: 测试            → test(geom): 补 build_geom 特征测试 8 条
  docs: 文档            → docs(spec): 补 modern 分部 4 条 spec

commit 关联 issue:
  Refs #N   → commit 关联但不关闭
  Closes #N → PR 合并时自动关闭 issue
```

### 5. 设置 Branch Protection

```
GitHub → Settings → Branches → Branch protection rules → Add rule → "main"

必须勾选：
  [x] Require a pull request before merging
  [x] Require status checks to pass before merging
      → 勾选 "lint" 和 "test-cases"（等 job 跑过一次后才会出现在列表里）
  [x] Require conversation resolution before merging
  [ ] Do not allow bypassing the above settings  ← 建议勾选

可选：
  [ ] Require signed commits
  [ ] Require linear history
  [ ] Allow force pushes → 禁止
```

## 人审动作

- 检查 CI YAML 的 Python 版本和依赖是否正确（当前生产用 3.10）
- 检查 lint 规则是否合理——ruff 默认规则可能对 2000 行的 v13 文件报大量 warning，先设 `--select=E,F` 只检查错误
- 检查 test-cases job 是否真的需要 xelatex——test_cases.py 只读 PDF，不需要 xelatex；verify_geom.py 也不需要。只有 build_ 脚本需要
- 检查 Branch Protection 是否生效——在另一个分支上故意改坏一个测试，开 PR，确认 CI 变红且无法 merge
- 最终 merge 由人确认——即使 CI 全绿，也要人审 diff

## Git 管理保障了什么

| Git 动作 | 本项目的作用 |
|---------|------------|
| **issue** | 划边界：AI 不能自由发挥改 wz2 的 pitch 算法——必须先开 issue 写明目标和不要动的范围 |
| **branch** | 隔离风险：`refactor/extract-tex-escape` 分支改坏了不影响 main |
| **commit** | 定位责任：`git bisect` 可以二分查找「pitch 从 59.1% 掉到 40% 是哪次 commit 引入的」 |
| **diff** | 让人审有焦点：PR 里逐行看哪些代码变了，而不是在聊天记录里猜 |
| **blame** | 找上下文：看到 build_classic.py:L690 的 `0<gap<阈值`，blame 显示是「附录五标题丢失修复」引入的，知道这是补丁不是原设计 |
| **revert** | 一键回滚：合并后发现问题 → `git revert <merge-commit>`，比「凭记忆改回去」可靠 |
| **PR** | 形成审查对象：评论、讨论、回退都有载体 |

## 完成标准

- `.github/workflows/ci.yml` 存在且能正常触发
- lint job 全绿（ruff check src/ 无错误）
- test-cases job 至少能跑到「基线 PDF 未预置时 skip」的状态（后续再补基线）
- Branch Protection 已设置，main 分支受保护
- commit 信息规范已写入 AGENTS.md 或 CONTRIBUTING.md
- 团队知道：PR → CI 绿灯 → 人审 → merge 的流程

## 禁止事项

- 禁止 AI 产出绕过 workflow——不要手动在 main 上直接 push
- 禁止红 CI 合并——lint 不绿坚决不能合
- 禁止重构、修 bug、新功能混在一个 PR——一个 PR 只做一件事
- 禁止把 AI review（如 GitHub Copilot PR review）当确定性门禁——AI review 可以辅助，但不能替代 lint + pytest 的确定性检查
- 禁止因为「基线 PDF 太大」就永远不加测试 CI——方案 D（20 页小样本）是折中，现在就做

## 可复制 Prompt

```text
请为 /opt/test 项目创建最小可用 GitHub CI。

项目信息：
  - Python 3.10，依赖 pymupdf (fitz)
  - 测试：src/test/test_cases.py（17条，需预置基线 PDF）
  - 无 lint 工具（需新装 ruff）
  - GitHub 仓库：nianruye/To-Text-based-PDF

要求：
1. 创建 .github/workflows/ci.yml：
   - 触发：push main + pull_request
   - job "lint"：ruff check src/
   - job "test-cases"：pymupdf + 基线 PDF 存在时跑 test_cases.py
   - 如果基线 PDF 不存在，test-cases 应跳过（不报失败）
2. 添加 ruff 基础配置（pyproject.toml 或 ruff.toml）：
   - 先只检查 E/F 规则（error + pyflakes），不检查格式
   - 排除 archive/ 目录
3. 写一份 Branch Protection 设置指南（GitHub Settings 操作步骤）
4. 写 commit 信息规范（feat/fix/refactor/test/docs + Refs/Closes #N）

CI 不要依赖 xelatex（测试只读 PDF），不要依赖 GPU。
基线 PDF 的处理策略：先用「不存在时 skip」方式，后续再加 Git LFS。
```
