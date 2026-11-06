# battle12 终审（t58）· 工具参数化 + 守卫

> 审查人：横排工程师（独立终审）　日期：2026-11-06 23:07–23:30
> 对象：t56（battle12 系统化：7 个普查工具 `--book` 参数化 + `MISSED_FIX_MIN_PAGES` 守卫 + 3 条 unit）与 t57 验收报告
> 基线：HEAD `5f2c477`（未 commit 工作树）；v42 `f964ad71…`；未改实现代码/数据/fix JSON/output，未 commit
> 本文件为唯一新增：`docs/battle12_review.md`

---

## 0. 结论

**verdict = needs_revision（当前 wz7/wz6 产物可交付，但还不能作为通用换书流程基线）**。

- t56/t57 的核心数字与幂等**独立复跑全部通过**（census/pilot/judge、守卫三态、wz6、pytest、7 个 `--help`）。
- 但代码审查发现 **F1（高）**：三处仍硬编码 wz7 页高 **1443pt**——`census_true_missing.py:120`、`api_pilot_build.py:60`、`api_candidates_all_build.py:55`。比 1443pt 更高的书会在页底**静默丢候选/裁掉条带**；t57 只记了 census 一处（R2），漏了后两个 build 工具。这与 t58 的验收条件「不能有『只有 wz7 能跑』的残留」直接冲突。
- 因此：**接受 wz7/wz6 的本次交付**；**不批准 battle12 作为通用换书流程基线**，需先修 F1（小改动，无需改产品输出）。

---

## 1. 独立复跑（数字与 t56/t57 一致）

| 项 | 命令（摘要） | 结果 |
|---|---|---|
| 7 个 `--help` | 逐个 `--help` | 7/7 **exit 0** |
| census 显式 | `census_true_missing.py --book wz7 --out /tmp/b12r/true_missing.json` | exit 0；md5 **afd42100a5193ed3c5b237978fd3e86d** = 仓库 `tmp_vert/battle6/true_missing.json` **逐字节** |
| census 默认 | 在 `/tmp/b12r/default`（data/source 软链、空 tmp_vert）无参运行 | exit 0；输出 md5 **afd42100…**；未写仓库；stats 同 `base 56109 / fax 921 / neighbor 246 / noise 351 / keep 1 / variant_cols 6883`、n=1 |
| pilot 显式 | `api_pilot_build.py --book wz7 --out-dir /tmp/b12r/pilot ...` | exit 0；**2,000 items / 250 页 / 25 批** |
| pilot 默认 | 在 `/tmp/b12r/defaultpilot`（data/source 软链、battle6/missing_cells 复制）无参运行 | exit 0；**2,000 items / 250 页 / 25 批** |
| judge 显式 | `api_candidates_all_judge.py --book wz7 --out /tmp/b12r/api_candidates_all.json --crops-dir /tmp/b12r/crops` | exit 0；**3,828 items**；classes `same 3158 / other 471 / true_insert 175 / nonchar 24`（与 t56/t57 同） |
| 守卫三态 | `pytest src/test/unit/test_missed_fix_min_pages.py -q` | **3 passed**（默认跳过 / `=0` 插入 / 边界=页数） |
| 全量测试 | `pytest src/test/unit src/test/invariants -q` | **593 passed**（74.09s） |
| wz6 | 参数化后的 `build_vert.py` 构建 + verify | `vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d**；verify **PASS**（231=231 / 97.2% / 2 预期 / 0 / 0+0） |
| v42 | `md5sum` | **f964ad7133841025c2d415c40f52af89** 不变（工具不进构建链） |

> 复跑未覆盖 judge 的**无参默认**（避免覆盖仓库 `tmp_vert/battle6` 历史裁片）；其默认路径由代码检查确认（`out_dir` 条件：wz7→battle6，其他→`tmp_vert/{book}`），与 t57 R5 一致。census/pilot 的默认模式已实跑。

---

## 2. 代码审查

### 2.1 守卫（通过）

- `build_vert.py:316`：`MISSED_FIX_MIN_PAGES = int(os.environ.get('VERT_MISSED_FIX_MIN_PAGES') or 1000)`，**模块级只读一次**；L561 守卫使用该变量。
- 没有每个 item 读 env；默认 1000 与旧行为一致；`=0` 关闭保护；`len(keys) >= 阈值` 时插入。
- 3 条 unit 覆盖默认/关闭/边界；全量 593 通过。

### 2.2 路径参数化（基本通过）

- 7 个工具的 `--book/--data-dir/--src/--fax/--out-dir/...` 均显式；默认路径按 `{book}` 推导；wz7 输出 `tmp_vert/battle6` 是**有意向后兼容**，其他书 `tmp_vert/{book}`。
- 未发现「非 wz7 仍回落到 `data/wz7_full` / `tmp_vert/battle6`」的隐式路径回退（census 的模块常量 L25–27 在 `main()` 内被 `--book` 覆盖，见 F3 的清理建议）。
- 但 **F1** 是比路径更硬的 wz7 依赖：页高 1443 硬编码在三个工具中。

### 2.3 F1（高）· 三处硬编码 wz7 页高 1443

| 文件:行 | 代码 | 影响 |
|---|---|---|
| `census_true_missing.py:120` | `if ya < 0 or yb > 1443: continue` | 页高 >1443 的书，页底候选格被静默跳过 |
| `api_pilot_build.py:60` | `yb = min(1443, y1 + a.ctx * step_pt)` | 页底条带被裁到 1443pt，圈/缺字上下文不完整 |
| `api_candidates_all_build.py:55` | 同上 | 全量条带同样被裁 |

- 1443pt 是 wz7 页高；wz6（1245pt）不受影响，但**任何高于 1443pt 的开本都会静默丢页底候选**。
- 这是「只有 wz7 能跑」的实质残留，t57 只记录了 census 一处（R2），且称为低；实际影响 API 条带与全量判定，必须修。
- **Required fix**：改用源页实际高度（`src[pg-1].rect.height`）或显式 `--page-height`（缺省取源页高）；三处同源修；加一个页高 ≠1443 的回归/ dry-run；更新报告 §6/§7 并删除 R2。

### 2.4 F2（低）· `--out-dir` 未参与默认 `--candidates` 路径

- `api_pilot_build.py:41-43`、`api_candidates_all_build.py:38-40` 在 `out_dir = a.out_dir or out_dir` **之前**计算 `cand_path`；非 wz7 且用户只给自定义 `--out-dir` 时，默认候选仍指向 `tmp_vert/{book}`，不是自定义目录。
- 报告 §6 示例显式传 `--candidates`，所以不影响照做；但参数化语义不完整。**Required fix**：先解析 `out_dir`，再用 `os.path.join(out_dir,'missing_cells.json')`。

### 2.5 F3（低）· census 文档/常量遗留

- `census_true_missing.py:5,14-16` docstring 仍写 `data/wz7_full`、`/tmp/wz7_v36_run`；L25–27 模块常量仍是 wz7（运行时被覆盖，非功能回退）。
- **Required fix**：docstring 改 `{book}`；删除或显式标注 dead 常量；不影响行为。

### 2.6 测试覆盖

- 守卫 3 条到位；工具参数化只有手工幂等（无 unit）；**没有覆盖 1443 页高**，因此 t56/t57 未发现 F1。建议随 F1 增加一个短测试/脚本，断言 crop/candidate 的 y 上界来自源页高。

---

## 3. 换书流程审查

- t56 报告 §6 已列出：`data/wzX_full/wzX_full_spotting_lines_patched.json` + coords、`source_pdf/wzX.pdf`、可选 `--fax`、外部 `missing_cells.json`、最终 fix JSON；命令覆盖 census → build → run → judge → 落库 → build；`missing_cells`/fix JSON 为外部步骤已在 §7 声明。
- 照做**在 wz6/wz7 上可行**（census/pilot 默认已在临时 cwd 跑通；显式 judge 3828）。
- 但 **页高 >1443 的书不能照做**：F1 会静默裁掉页底候选/条带，且报告 §6 未提示；这是「通用换书流程基线」的阻塞项。
- R5（judge 默认未实跑）属验证范围说明，不阻塞；R6（dry-run 仅 census）报告已声明。

---

## 4. outOfScope / 字节绑定

- `git status`：**未改** `src/test/verify_vert.py`、`docs/vert_taskF_missed_fix.json`、`data/`、`output/`；v42 md5 `f964ad71…` 未变。
- 当前工作树改动仅 t56 的 7 工具 + `build_vert.py` + 新增测试 + spec 16/18 + t56/t57 文档；符合 t56 范围，未越界。
- t56/t57 的字节哈希与当前一致（build_vert `5799539a…`、census `b1582f61…`、verify_vert `cc8b6937…`、fix JSON `ffe24f09…`、v42 `f964ad71…`）。

---

## 5. Findings

| id | severity | problem | requiredFix |
|---|---|---|---|
| F1-page-height-1443 | **high** | `census_true_missing.py:120`、`api_pilot_build.py:60`、`api_candidates_all_build.py:55` 硬编码 wz7 页高 1443；页高 >1443 的书静默丢页底候选/条带，违反「不能只有 wz7 能跑」 | 三处改用源页实际高度或 `--page-height`（缺省源页高）；加页高 ≠1443 的回归；更新报告 §6/§7，删除 R2 |
| F2-outdir-candidates | low | pilot/all build 在解析 `--out-dir` 前计算非 wz7 的默认 `--candidates`，自定义 out-dir 时不生效 | 先解析 `out_dir`，再用 `{out_dir}/missing_cells.json` |
| F3-census-doc | low | census docstring 仍写 `/tmp/wz7_v36_run`；L25–27 是死 wz7 常量（运行时覆盖） | docstring 改 `{book}`；删死常量或注明 |

---

## 6. 结论

- **独立数字全部通过**：census 显式/默认 md5 `afd42100…`（逐字节）、pilot 2000/250/25、judge 3828/classes、守卫 3、pytest 593、wz6 `ae9d2f52…` + PASS、v42 `f964ad71…` 未变。
- **不批准为通用换书流程基线**：F1（1443）是实际书高依赖，t57 只记 census 一处且漏了两个 build 工具。修 F1（及顺手 F2/F3）后，battle12 即可作为换书基线；当前 wz7/wz6 产物仍可交付。
