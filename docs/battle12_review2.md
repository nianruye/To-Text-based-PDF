# battle12 复审（round 2）· t59 修复复核

> 审查人：横排工程师（独立复审）　时间：2026-11-06 23:35–23:46
> 审查对象：t59（F1 页高 1443 / F2 out-dir 候选 / F3 census 文档常量）及更新后的 t56/t57 报告
> 基线：HEAD `5f2c477`（未 commit 工作树）；v42 `f964ad71…`；未改实现/数据/fix JSON/output，未 commit
> 本文件为唯一新增：`docs/battle12_review2.md`

---

## 0. 结论

**verdict = needs_revision（t59 的 F1/F2/F3 代码方向正确，但 census 基线被改而未更新，t59 的「md5 不变」声明与实测不符）**。

- **F1 已修**：三处 1443pt 硬编码改为源页 `rect.height` / `--page-height`（`census_true_missing.py:125`、`api_pilot_build.py:61`、`api_candidates_all_build.py:58`）；代码 grep 已无 1443。
- **F2 已修**：两 build 工具先解析 `out_dir` 再取 `{out_dir}/missing_cells.json`；`test_page_height.py` 的 custom-outdir 用例通过。
- **F3 基本修**：census 模块常量改空占位，usage 改 `{book}`；但 docstring 第 5 行仍写 `data/wz7_full`（低）。
- **但 F1 的默认值改变改变了 wz7 census 输出**：t59 报告称 md5 `afd42100…` **逐字节同**；我实测默认（源页高）为 **`9dda98e4…`**，stats 也变（见 §2）。`--page-height 1443` 才复现旧 `afd42100…`。这是 t56/t57 幂等基线未更新，属阻塞性验收问题（不是产品 PDF 回归，但「数字与 t56/t57 一致」不成立）。

---

## 1. 独立复跑

| 项 | 命令/口径 | 结果 |
|---|---|---|
| 7 个 `--help` | 逐个 | **7/7 exit 0**；census/pilot/all build 均含 `--page-height` |
| census 默认（源页高，t59 新行为） | `census_true_missing.py --book wz7 --out /tmp/b12r2/true_missing.json` | exit 0；md5 **`9dda98e477057ef08289996ab68df4fe`**；stats `base 56105 / fax 919 / neighbor 246 / noise 350 / keep 1 / variant_cols 6883`、n=1 |
| census `--page-height 1443`（旧口径） | 同上 + `--page-height 1443` | exit 0；md5 **`afd42100a5193ed3c5b237978fd3e86d`**；stats `56109 / 921 / 246 / 351 / 1 / 6883`（=仓库旧 `true_missing.json`） |
| pilot 显式 | `api_pilot_build.py --book wz7 --out-dir /tmp/b12r2/pilot ...` | exit 0；**2,000 items / 250 页 / 25 批** |
| judge 显式 | `api_candidates_all_judge.py --book wz7 --out ... --crops-dir ...` | exit 0；**3,828 items**；classes `3158 / 471 / 175 / 24` |
| 新测试（页高/outdir + 守卫） | `pytest test_page_height.py test_missed_fix_min_pages.py -q` | **6 passed**（3+3） |
| 全量测试 | `pytest src/test/unit src/test/invariants -q` | **596 passed**（593+3） |
| wz6 | 参数化 build_vert + verify | `vert.tex` **`ae9d2f52…`**；verify **PASS**（231=231 / 97.2% / 2 预期 / 0 / 0+0） |
| v42 | md5 | **`f964ad71…`** 未变 |

---

## 2. F1 已修，但 census 基线变了（阻塞）

### 2.1 实测差异

| 输出 | md5 | stats |
|---|---|---|
| 仓库旧 `tmp_vert/battle6/true_missing.json` | `afd42100…` | base **56109** / fax **921** / neighbor 246 / noise **351** / keep 1 / variant 6883 |
| t59 默认（源页高） | `9dda98e4…` | base **56105** / fax **919** / neighbor 246 / noise **350** / keep 1 / variant 6883 |
| t59 + `--page-height 1443` | `afd42100…` | 与旧相同 |

### 2.2 原因

wz7 不是单一页高：1748 页有 **12 种高度**，范围 **1083.75–1443.75pt**；**1737 页 <1443**、10 页 =1443、1 页 >1443。旧硬编码 1443 会保留一部分**超出本页纸高**的页底候选；新实现按本页 `rect.height`，正确地排除了它们（4 个 base、2 个 fax 页、1 个 noise 的差异），n=1 的最终条目不变。

### 2.3 为什么阻塞

- t59 报告 §0/§2 声称「census md5 `afd42100…` 与现文件逐字节相同」；**实测默认是 `9dda98e4…`**，只有加 `--page-height 1443` 才回到旧值。
- t60 的验收要求「数字与 t56/t57 一致」；t56/t57 的幂等基线是 `afd42100…`。现在工具默认输出变了，**没有同步基线和报告**，不能按「wz7 行为不变」验收。
- 新行为在方向上**更正确**（排除超出纸高的候选），但必须二选一并写清楚：
  - **(a) 接受新基线**：更新 `true_missing.json`（如保留）与 t56/t57/t59 报告、幂等数字、stats、md5；说明 4 个被排除候选中哪些在页外；加一条断言新 md5 的回归。
  - **(b) 保留旧 wz7 默认**：为 wz7 设兼容 `page_height=1443`（仅兼容层），新书走源页高；但这会重新引入 wz7 特例，需在报告声明。
- 当前处于「代码改了、基线没改、报告说没变」的状态，**不能通过终审**。

---

## 3. F2/F3 复核

### F2（已修，低残留）

- `api_pilot_build.py:42-44`、`api_candidates_all_build.py:41-43` 已先 `out_dir = a.out_dir or _defaults(...)` 再取 `cand_path`；非 wz7 自定义 `--out-dir` 生效。
- `test_page_height.py::test_custom_out_dir_picks_local_candidates` 通过（`--book wz6 --out-dir custom` 不传 `--candidates` → 读 `custom/missing_cells.json`，输出 1 item）。
- 低残留：该测试只覆盖 pilot build；`api_candidates_all_build` 同代码但无直接测试；建议补一条。

### F3（基本修，低残留）

- census 模块常量已改空占位；usage 用 `{book}`；`--page-height` help 可见。
- docstring 第 5 行仍写 `输入：data/wz7_full ... source_pdf/wz7.pdf`（低，非功能路径）；建议改 `{book}` 推导。
- `api_pilot_judge.py` docstring 仍写 `tmp_vert/battle6`（wz7 示例，非默认回退；低）。

---

## 4. 换书流程 / 范围

- t56 报告 §6 已加「页高（t59）」：census/pilot/all build 缺省源页高，`--page-height` 覆盖；页高≠1443 不再被裁。换书文件/命令清单完整（data/source/fax/missing_cells/fix JSON）；R2 已从 acceptance 删除。
- 未发现 `src/tools` 中残留 1443；但仍需按 §2 同步 census 基线，否则「换书默认可直接跑」与「wz7 旧证据逐字节」二选一未定。
- `git status`：未改 `src/test/verify_vert.py`、`docs/vert_taskF_missed_fix.json`、`data/`、`output/`；v42 `f964ad71…` 未变。t56/t59 的 7 工具 + build_vert + 新测试 + 报告改动均在允许范围；t59 另有 4 个路径未列入其 changedPaths（`api_candidates_all_build.py`、`test_page_height.py`、两份 battle12 报告），属报告追踪，不影响代码。

---

## 5. Findings

| id | severity | problem | requiredFix |
|---|---|---|---|
| F1-census-baseline | **high** | t59 默认 census（源页高）输出 `9dda98e4…`、stats 56105/919/246/350，与旧 `afd42100…`/56109/921/246/351 不同；t59 报告却称 md5 逐字节同，t56/t57 幂等基线未更新 | 二选一并在报告写清：(a) 接受新基线，更新 `true_missing.json`/t56/t57/t59 报告与 md5/stats，解释 4 个被排除候选在页外，并加新 md5 回归；(b) 为 wz7 保留 `--page-height 1443` 兼容层，新书默认源页高。 |
| F2-build-coverage | low | `test_page_height.py` 只覆盖 census 页高与 pilot out-dir；`api_candidates_all_build` 的页高/out-dir 无直接测试 | 补一条 all build 的页高/out-dir 测试（可用合成书或 dry-run）。 |
| F3-census-doc | low | `census_true_missing.py:5` docstring 仍写 `data/wz7_full`/`source_pdf/wz7.pdf` | docstring 改 `{book}` 推导。 |
| F4-changedpaths | low | t59 改了 4 个路径未列入 changedPaths | 补登 `api_candidates_all_build.py`、`test_page_height.py`、`battle12_systemize/acceptance`。 |

---

## 6. 结论

- F1 的**代码修复**（源页高/`--page-height`）正确；F2 代码与测试通过；F3 基本清理；wz6/v42/pytest 596/7 help 均通过。
- **不能通过终审**：census 默认基线与 t56/t57 不一致，t59 的 md5 声明与实测不符；先按 F1-census-baseline 二选一并对齐报告，再复审。F2-build-coverage/F3/F4 为低残留，可顺手修。
