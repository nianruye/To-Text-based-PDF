# 竖排收尾修复任务简报（给 Claude Code）

> 项目：/opt/test。背景：竖排治理门禁已落地（`spec/governance/PIPELINE_BEHAVIOR.md` 契约 V1-V9、根 `AGENTS.md` 已更新、`src/test/verify_vert.py` 竖排回归验证实测 PASS，见 `docs/vert_governance_report.md`）。该任务登记了 3 个新 issue（#18/#20/#27，AGENTS.md §6 可查），**本任务修掉它们**——这是竖排工作的最后收尾。

## 参考材料（先读）

- `AGENTS.md` §6 — issue #18/#20/#27 的登记行（来源与影响）
- `docs/vert_governance_report.md` — 三条 issue 的源码级证据（含行号）
- `spec/governance/PIPELINE_BEHAVIOR.md` — 竖排契约 V1-V9（**改契约字段必须同步此文件**）
- `spec/vertical/` — 竖排机制 spec（#27 的数字漂移涉及这些文档）
- `src/pipelines/build_vert.py` — 待修主体
- `src/test/verify_vert.py` — **回归守门员**（改完必须实测 PASS）

## 任务（三件）

### #18 build_vert.py 无 `sys.exit`（编译失败退出码仍 0）
现状：全文无 `sys.exit` 调用 → 编译失败/输入缺失时退出码仍 0，CI/脚本无法感知失败。
修法（**分级处理，注意保持正常路径行为不变**）：
- **编译失败**（uplatex / dvipdfmx 返回非 0，或预期产物 PDF 未生成）→ 打印错误并 `sys.exit(1)`（**这是行为变化，是修复本身，需实测验证**）
- **输入文件缺失**（lines/coords/src 不存在）→ 显式报错 + `sys.exit(1)`
- **SRC 缺失**（argv[4] 缺省 None）→ **打印显式警告到 stderr**（说明"将静默关闭以下墨迹特性：…" 逐项列出）——**警告不改变退出码**（保持兼容，某些调试调用只用 3 参数）
- 正常路径退出码必须仍为 **0**
- **验收实测**：①正常跑（VERT_PAGES=162-162）退出码 0；②故意给坏输入/坏源 → 退出码非 0；③只给 3 参数 → 警告出现且退出码 0
- 如项目测试框架允许，加一个锁定该行为的单元测试（放 src/test/unit/）

### #20 VERT_TMP 临时文件并发冲突
现状：临时目录路径与输出名无关 → 两个 build_vert 并发（不同书/不同任务）会互相覆盖。
修法：**按 build_name（输出文件名 stem）分离**（对标横排 #10 的方案），例如 `/tmp/vert_<stem>_run/`；保留 `VERT_TMP` 环境变量覆盖能力（显式设置时用用户给的路径）。
- **改默认值 = 契约字段变化** → **同步更新 `spec/governance/PIPELINE_BEHAVIOR.md`** 里 VERT_TMP 的默认值描述
- **验收实测**：两个并发实例（不同输出名）临时路径不同（可跑两个 VERT_PAGES 小范围并发验证）；单实例行为不变

### #27 文档数字与实测漂移
现状（治理报告记录）：页码条目 121→实测 **122**、边注条目 64→实测 **65**、页码纠正 19→**18** 处、`build_vert.py` L666 注释 546pt vs 实测 563.1pt。
修法：
- **先独立实测核对每一项真值**（写脚本从 data/wz6 + build_vert.py 实际输出统计——不要照抄报告里的数字，包括本简报里的数字也要自己核）
- 按真值更正：`build_vert.py` 注释、`spec/vertical/*`、`docs/vert_v2_report.md`（**只改数字，不改机制描述**）
- 若实测发现报告里的"漂移"判断本身有误，如实说明

## 验收标准

1. #18：三项实测全过（正常 0 / 失败非 0 / 3 参数有警告且 0）——**贴实际命令与退出码**
2. #20：并发路径分离实测；`PIPELINE_BEHAVIOR.md` 的 VERT_TMP 描述已同步
3. #27：每项数字都有实测依据（贴统计脚本与输出），文档已按真值更正
4. **`verify_vert.py` 实测 PASS**（退出码 0，全书 231:1/字符量/越界不回归）——**这是硬要求**
5. **201 单元/不变量测试全绿**（改了 build_vert.py 必须重跑）
6. 报告写入 `docs/vert_fix18_20_27_report.md`

## 约束

- **不改横排管线**（build_geom/build_classic/fit_positional 及其测试）、不动四书数据
- **不动 build_vert.py 的渲染逻辑**（本次只改退出码、临时目录路径、注释数字）
- 不 git reset；完成后 `git add` 改动但不 commit
- 复杂 shell 写成脚本文件执行
- 改完必须先自己跑 verify_vert + 201 测试，通过后再报完成
