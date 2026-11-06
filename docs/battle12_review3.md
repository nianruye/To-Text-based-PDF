# battle12 复审（round 3）· t61 新基线复核

> 审查人：横排工程师（独立复审）　时间：2026-11-07 00:11–00:20
> 审查对象：t61（接受 census 新基线 + t59 F1/F2/F3 收尾）与更新后的 battle12 报告
> 基线：HEAD `5f2c477`（未 commit 工作树）；v42 `f964ad71…`；未改实现/数据/fix JSON/output，未 commit
> 本文件为唯一新增：`docs/battle12_review3.md`

---

## 0. 结论

**verdict = pass（可交付；可作为换书流程基线）**。

t61 按队长指示选择「接受新基线」：census 默认（源页高）新基线 **`9dda98e4…`**，旧 `afd42100…` 仅作 `--page-height 1443` 对照；4 个页外窗口逐条列出，`true_missing.json` 已更新，报告/回归同步。独立复跑：

- census 默认 → **`9dda98e4…`**，与仓库 `tmp_vert/battle6/true_missing.json` **逐字节**；stats `56105/919/246/350/1/6883`、n=1
- census `--page-height 1443` → **`afd42100…`**（旧值，仅对照）
- 7/7 `--help` 0；pilot 2000/250/25；judge 3828/classes；守卫 3；新增/页高测试 9；**pytest 599**
- wz6 `ae9d2f52…` + verify PASS；v42 `f964ad71…` 未变
- out-of-scope 无改动

剩余均为**低级别报告/测试追踪**项（R1–R4），不阻塞。

---

## 1. 独立复跑

| 项 | 命令/口径 | 结果 |
|---|---|---|
| census 默认（新基线） | `census_true_missing.py --book wz7 --out /tmp/b12r3/true_missing.json` | exit 0；md5 **`9dda98e477057ef08289996ab68df4fe`** = 仓库 `true_missing.json` **逐字节**；stats `base 56105 / fax 919 / neighbor 246 / noise 350 / keep 1 / variant 6883`、n=1 |
| census 旧口径对照 | `/tmp/b12r2/true_missing_1443.json`（t60 独立跑，t61 未改 census 代码） | **`afd42100…`**；stats `56109/921/246/351`——仅对照，不作为默认 |
| 7 个 `--help` | 逐个 | **7/7 exit 0**；census/pilot/all build 含 `--page-height` |
| pilot 显式 | t60 独立跑 + t61 未改该工具 | **2,000 items / 250 页 / 25 批** |
| judge 显式 | t60 独立跑 + t61 未改该工具 | **3,828 items**；classes `3158/471/175/24` |
| 新增/守卫测试 | `pytest test_census_baseline.py test_page_height.py test_missed_fix_min_pages.py -q` | **9 passed**（2+4+3） |
| 全量测试 | `pytest src/test/unit src/test/invariants -q` | **599 passed**（593 + 6） |
| wz6 | 参数化 build_vert + verify | `vert.tex` **`ae9d2f52…`**；verify **PASS**（231=231 / 97.2% / 2 预期 / 0 / 0+0） |
| v42 | md5 | **`f964ad71…`** 未变 |

> t56/t57 的旧数字 `afd42100…` 是**旧 1443 口径**，t61 已按队长指示接受新基线 `9dda98e4…`；报告明确标注旧值仅对照，不再要求默认复现旧值。

---

## 2. 代码审查

### F1（已修，通过）

- `census_true_missing.py:125`：`_ph = page_h or src[pg-1].rect.height`；`yb > _ph` 跳过页外窗口。
- `api_pilot_build.py:61` / `api_candidates_all_build.py:58`：`yb = min(src[pg-1].rect.height, ...)`，支持 `--page-height`。
- `grep -R 1443 src/tools/*.py` = **none**；目标三工具无 `/tmp/wz7` / `data/wz7_full` 路径。
- 新基线测试 `test_census_baseline.py`（artifact md5/stats；`B12_CENSUS_SLOW=1` 时实跑）；`test_page_height.py` 补 all_build 页高 + 自定义 out-dir（4 条）；9 条新增/守卫全过。

### F2（已修，通过）

- 两 build 工具先解析 `out_dir`，再取 `{out_dir}/missing_cells.json`；pilot/all build 测试通过。

### F3（已修，通过）

- census 模块常量改空占位；docstring 第 5 行改 `{book}_full`；usage `{book}`。

### 守卫（通过）

- `build_vert.py:316` 模块级只读一次 env；L561 使用；3 条 unit（默认/0/边界）通过。

### 低残留

- `test_census_baseline.py` 的慢测试在未设 `B12_CENSUS_SLOW=1` 时直接 `return`（pytest 计为 passed，而非 skip）；快速测试在 artifact 缺失时也直接 `return`。测试存在但「静默通过」不够显式，建议 `pytest.skip` 或标记 slow。
- `battle12_acceptance.md` §7 复现命令的注释仍是旧 `afd42100…`，且未带 `--page-height 1443` 对照；主报告 `battle12_systemize` §2/§8 已正确，acceptance 的旧注释属低级别误导。
- t61 的 changedPaths 未含 `test_census_baseline.py`、`battle12_acceptance.md`、`tmp_vert/battle6/true_missing.json`（t61 输出已自述）；追踪补登即可。

---

## 3. 换书流程

- `battle12_systemize` §6 已列：`data/wzX_full` lines/coords、`source_pdf`、`--fax`、外部 `missing_cells.json`、最终 fix JSON + census/build/run/judge 命令；§6 页高说明（源页高/`--page-height`）与 §7 修复记录完整；§8 复现使用新基线。
- `--book wzX` 非 wz7：输出 `tmp_vert/{book}`；`--out-dir` 自定义时默认候选取 `{out}/missing_cells.json`；census/pilot 默认已在临时 cwd 跑通；无「只有 wz7 能跑」的代码残留。
- judge/pilot 换书仍需外部 `missing_cells.json`/`all_items.json`（报告 §7 已声明），属预期范围。

---

## 4. out-of-scope / 字节绑定

- `git status`：未改 `src/test/verify_vert.py`、`docs/vert_taskF_missed_fix.json`、`data/`、`output/`；v42 md5 `f964ad71…` 未变。
- t61 改 `tmp_vert/battle6/true_missing.json`（新基线）是本次授权的数据证据更新；不在 t62 的 out-of-scope 四类中。
- 未 commit；HEAD `5f2c477`。

---

## 5. 残留（不阻塞）

- **R1（低）**：`battle12_acceptance.md` §7 旧 md5 注释未改新基线/未标对照。
- **R2（低）**：`test_census_baseline.py` 的慢测试/artifact 缺失路径静默 `return`，建议 `pytest.skip`。
- **R3（低）**：t61 changedPaths 未列 3 个实际改动路径（test_census_baseline、acceptance、true_missing）。
- **R4（低）**：`api_pilot_judge.py` docstring 仍有 `tmp_vert/battle6` 示例（wz7 示例，非默认回退）。

---

## 6. 结论

t61 已把 t60 的「census 基线未更新」收口：默认源页高新基线 `9dda98e4…`、旧 `afd42100…` 仅作 `--page-height 1443` 对照，4 个页外窗口有逐条证据，`true_missing.json` 与报告同步。代码、守卫、wz6、pytest 599、7 help、v42 均通过；**批准 battle12 作为换书流程基线**。R1–R4 为报告/测试追踪级，可顺手修。
