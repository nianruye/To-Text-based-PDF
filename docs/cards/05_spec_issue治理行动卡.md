# /opt/test spec ↔ issue 治理行动卡

> 用在：一次性 spec 和测试已经产生，想让它们跟着项目长期维护。目标是把 spec 变成状态账本，不让它退化成过期文档。本项目已有 `spec/` 目录体系（含总架构 spec + 古籍分部 01-08 + 占位目录），现在要让它活起来。

## 输入

- 已有 spec 体系：`spec/00_system_architecture.md`（总架构）、`spec/ancient/01-08_*.md`（古籍 8 条 spec）、`spec/ancient/appendix_layout.md`（附录排版）、`spec/modern/`、`spec/paper/`、`spec/contract/`、`spec/bid/`（占位空目录）
- 已有测试：`src/test/test_cases.py`（17条，全针对 build_classic + wz2）
- 项目文档：`docs/AGENTS.md`、`docs/CLAUDE.md`、`docs/PROJECT_SUMMARY.md`
- GitHub 仓库：https://github.com/nianruye/To-Text-based-PDF
- 当前 spec 缺口：modern 分部 4 条 spec 缺失、08_appendix_layout 有 spec 无测试、各 spec 之间无状态标注

## AI 动作

### 1. 补齐 Spec 缺口

**modern 分部**（当前空目录，需补 4 条 spec）：

- `spec/modern/01_paragraph_indent.md`：段首缩进行为 spec
  - 描述了 build_geom.py 的段首缩进逻辑（x0 > 续行 x0，差值 ≥ 2em）
  - 目标/输入/输出/约束/测试点
- `spec/modern/02_footnote_separator.md`：脚注分界线 spec
  - 描述了分界线上下方的字号差异、分界线渲染方式
- `spec/modern/03_heading_hierarchy.md`：标题层级 spec
  - 描述了 _head_level 的分级逻辑（part/section/title）+ toc_map 辅助识别
- `spec/modern/04_toc_rendering.md`：目录页渲染 spec
  - 描述了 dotfill + 页码右对齐 + _toc_level 缩进

**paper/contract/bid 占位 spec**：

- 各写一条「当前状态：不支持。预期行为：...」占位 spec，方便后续扩展时不被忘记

### 2. 建立 spec ↔ test ↔ code 三角映射

为每条已有 spec 补上映射：

```
spec/ancient/01_pitch_overlap.md
  → test: test_pitch_p11, test_pitch_p26, test_no_overflow, test_pitch_rate
  → code: build_classic.py:L29-65 (几何标定), L124-160 (page_pitch)
  → 状态: implemented

spec/ancient/02_font_classification.md
  → test: test_p11_body_font, test_p15_note_font, test_p5_preface_font
  → code: build_classic.py:calc_global_fonts() L564
  → 状态: implemented

spec/ancient/03_note_sequence_alignment.md
  → test: test_p15_seq_x0_unified, test_p15_cont_x0_unified, test_p15_no_overlap
  → code: build_classic.py:_note_text_x + 序号分列
  → 状态: implemented

...

spec/ancient/08_appendix_layout.md          ← 有 spec，但缺测试！
  → test: 无 ← 这是 bug，需补测试
  → code: build_classic.py:L690, L773, L798, L919, L932, L996
  → 状态: implemented (但测试缺口)

spec/modern/01_paragraph_indent.md          ← 无 spec，无测试
  → test: 无
  → code: build_geom.py 段首缩进逻辑
  → 状态: planned (spec 待写)
```

### 3. 更新 AGENTS.md 规则

在 `docs/AGENTS.md` 末尾追加 spec 对账规则：

```markdown
## Spec 对账规则

一个改动不算完，直到实现、测试、文档、spec 状态讲的是同一个故事：

1. **新功能**：先写 spec/<type>/XX_function.md（目标/输入/输出/约束/测试点）→ 用户确认 → 实现 → 测试 → spec 状态从 planned 迁移到 implemented
2. **修 bug**：不混在重构 PR 里。修完更新对应 spec 的「已知问题」段。如果是新发现的 bug（spec 未覆盖），先补 spec 再修
3. **重构**：行为不变 → spec 不新增、不改状态。但对应测试必须全绿
4. **PR 合并前 checklist**：
   - [ ] 相关 spec 是否同步更新？
   - [ ] spec 状态是否正确（planned/implemented/archived）？
   - [ ] 测试是否覆盖了 spec 中的测试点？
   - [ ] 如果改了 public API 或命令行参数，spec 的「输入/输出」段是否已更新？
5. **spec 状态定义**：
   - governance/：长期生效的规则（如「API Token 不写入代码」）
   - planned/：已设计、未落地（spec 写了但代码还没实现）
   - implemented/：已落地，带实现锚点（代码行号 + 测试函数名）
   - archived/：废弃或搁置（如「MinerU 方案」已放弃）
```

### 4. 给 issue 分类

GitHub 上没有现有 issue 的话，从 PROJECT_SUMMARY 的「待完成」列表提取：

| 待完成项 | issue 类型 | 处理方式 |
|---------|-----------|---------|
| wz2 双规制 pitch 优化（59.1% → 目标 90%） | 排版优化 | 先写 planned spec，再实现 |
| 字体识别（宋体/楷体/黑体区分） | 新功能 | 先写 planned spec，再实现 |
| 无序号标题识别 | 局部增强 | 最小实现 + 回归测试 |
| 标点间距处理 | 排版优化 | 按文档类型分类处理 |
| Web 上传 → 自动转换 | 新功能 | 先写架构方案，再实现 |
| 论文/合同/标书支持 | 新文档类型 | 先收集样本，再写 spec |
| build_pdf_v13.py 功能迁移 | 架构清理 | 先架构梳理，再逐功能迁移 |
| fit_positional 重复消除 | 架构清理 | 属于重构，不改变行为 |

如果有多个 issue 是同一根因（如「双规制 pitch」「标点间距」「区域化排版」都指向 wz2 的行距测量问题），先抽象统一方案，别逐个打补丁。

## 人审动作

- 确认哪些规则必须写进 AGENTS.md——不是所有规则都适合，挑「AI 必须遵守」的硬约束
- 判断 spec/modern/ 四条是否准确描述了 build_geom 的实际行为（不是理想行为）
- 判断「待完成」列表中哪些是同一根因——wz2 的 pitch、标点间距、区域化可能都是同一个「多规制行距测量」问题的不同症状
- 确认 spec 的状态迁移是否正确——appendix_layout.md 应该已从 planned 迁到 implemented（代码已实现），但缺测试
- 确认「完成」的定义：实现改了 + 测试全绿 + spec 状态更新，三者缺一不可

## 完成标准

- spec/modern/ 目录补 4 条 spec（段首缩进、脚注分界、标题层级、目录页渲染）
- paper/contract/bid 各有 1 条占位 spec（当前不支持 + 预期行为）
- 每条已有 spec 有对应的 test 和 code 行号映射
- AGENTS.md 已追加 Spec 对账规则
- 待完成事项已按 issue 类型分类
- spec/ancient/08_appendix_layout.md 的测试缺口已标注（可以暂不补测试，但不能不知道缺）

## 禁止事项

- 禁止把重要规则只留在聊天记录里——AGENTS.md 是 agent 每次开工前会读的，聊天记录不会
- 禁止实现改了但 spec 不改——这是 spec 腐烂的第一原因
- 禁止多个同根因 issue 被逐个打补丁——wz2 的 pitch/标点/区域化如果同根，应该一个方案解决
- 禁止分不清影响面时直接开工——涉及 argv 约定、JSON 数据格式、环境变量的改动，先写 spec 再动代码
- 禁止 spec 写得太抽象——每条 spec 必须有具体的输入/输出/约束/测试点，不能只是「优化排版质量」

## 可复制 Prompt

```text
请基于 /opt/test 项目当前状态，帮我建立一个最小 spec 状态账本。

项目现状：
  - 已有 spec/ 目录体系：00_system_architecture.md（总架构）
  - spec/ancient/ 有 01-08 共 8 条已实现 spec + appendix_layout.md
  - spec/modern/、spec/paper/、spec/contract/、spec/bid/ 是空目录
  - 测试仅有 src/test/test_cases.py（17条，全针对 build_classic+wz2）
  - AGENTS.md 已有基础规则，但缺 spec 对账规则

要求：
1. 补齐 spec/modern/ 目录的 4 条 spec：
   - 01_paragraph_indent.md（段首缩进，描述 build_geom.py 的实际行为）
   - 02_footnote_separator.md（脚注分界线）
   - 03_heading_hierarchy.md（标题层级：_head_level + toc_map）
   - 04_toc_rendering.md（目录页 dotfill + 缩进）
   每条 spec 格式：目标/背景/方案/输入/输出/约束/测试点

2. 为 paper/contract/bid 各写 1 条占位 spec，格式：
   "当前状态：不支持。[文档类型]的处理管线待建。预期行为：[简要描述]"

3. 建立 spec ↔ test ↔ code 三角映射表：
   对每条已有 spec，列出：
   - 对应的测试函数名（在 test_cases.py 中）
   - 对应的代码位置（文件名:行号）
   - spec 状态（governance/planned/implemented/archived）
   - 如有测试缺口，标注"⚠ 缺测试"

4. 在 docs/AGENTS.md 末尾追加「Spec 对账规则」段（含 PR checklist）

5. 给 PROJECT_SUMMARY 中的「待完成」列表做 issue 分类：
   - 局部 bug（期望清楚）→ 最小修复
   - 新功能 → 先 spec
   - 公共接口 → 先对齐兼容策略
   - 架构变更 → 先画方案
   - 多个 issue 同根因 → 先抽象统一方案

不要写业务实现，先建立治理结构。
```
