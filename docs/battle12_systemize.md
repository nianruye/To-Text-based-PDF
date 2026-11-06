# battle12 · 普查工具参数化（--book）+ 守卫去魔法数

> 任务：t56 — PR #6「系统化」：把 battle6–11 的普查/落库流程从 wz7 专用脚本改成「换书能直接用」
> 执行：竖排工程师　日期：2026-11-06
> 范围：7 个普查工具 + `build_vert.py` 守卫 + unit 测试 + spec 16/18 锚点同步
> 约束：未改 `verify_vert.py`、未改数据文件（fix JSON 未动）、未 commit；token 未入库。

## 0. 结论

| 项 | 结果 |
|---|---|
| 工具参数化 | **7/7** 工具改为 argparse 显式参数（`--book/--data-dir/--src/--out-dir/--strips-dir/--batches-dir/--cols-per-page/--pages-per-batch` 等），**wz7 默认行为逐字节等价**（默认路径集中到 `--book wz7` 推导；无助记 `/tmp/wz7_v36_run` 硬编码） |
| 守卫去魔法数 | `build_vert.py` L316 新增 `MISSED_FIX_MIN_PAGES = int(os.environ.get('VERT_MISSED_FIX_MIN_PAGES') or 1000)`；L561 守卫改用该值；默认 1000 → 行为不变 |
| 幂等（census） | `--book wz7`（**默认=源页高**）→ `true_missing.json` md5 **9dda98e477057ef08289996ab68df4fe**，stats `base 56105 / fax 919 / noise 350 / keep 1 / variant 6883`、n=1；仓库 `tmp_vert/battle6/true_missing.json` 已更新为该新基线。**旧口径**（t56/t57 记录的 `afd42100a5193ed3c5b237978fd3e86d`，stats 56109/921/351）**仅作对照**，用 `--page-height 1443` 复现（不删） |
| 幂等（judge） | `api_candidates_all_judge --book wz7` → **3,828 列逐条一致**（items 全字段除 crop 路径；classes same 3158/other 471/nonchar 24/insert 175；hanzi 58 / punct 96 清单一致） |
| 幂等（pilot） | `api_pilot_build --book wz7` → **2,000 列集合一致**（page/col/text/n/cells/step 全等；250 页 / 25 批） |
| 单元测试 | 新增 `test_missed_fix_min_pages.py` 3 条：默认跳过小书 / 显式 0 允许 / 边界=页数；pytest **593 passed**（590+3） |
| wz6 零回归 | `vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节不变；verify PASS |
| v42 | 未重建；`output/wz7_full/wz7_full_v42.pdf` md5 **f964ad7133841025c2d415c40f52af89** 不变（工具仅数据准备，不进构建链） |
| spec 同步 | spec 16 守卫行改「环境变量 + 默认 1000」；spec 16/18 的 build_vert 行号锚点全部按当前 8009 行重测更新；spec 18 §3 第 7 行标「部分（通道参数化 implemented；圈码专用条带 planned）」 |

## 1. 工具参数化（7 个文件）

### 1.1 公共约定

- `--book`（默认 `wz7`）：推导 `--data-dir data/{book}_full`、`--src source_pdf/{book}.pdf`、`--fax /tmp/{book}_v36_run/fax_pages.json`（`tempfile.gettempdir()`，不再写死 wz7）。
- wz7 的输出目录默认仍是原 battle 目录（`tmp_vert/battle6`），以保持向后兼容；其他书默认 `tmp_vert/{book}`。所有路径都可显式覆盖。

### 1.2 参数/默认值对照表

| 工具 | 新增/显式参数（默认值） | 输出（默认 wz7） |
|---|---|---|
| `census_true_missing.py` | `--book wz7` / `--data-dir data/{book}_full` / `--src source_pdf/{book}.pdf` / `--fax /tmp/{book}_v36_run/fax_pages.json` / `--out tmp_vert/battle6/true_missing.json` / `--crops` / `--dens-min 0.04` | true_missing.json + crops |
| `api_pilot_build.py` | `--book` / `--data-dir` / `--src` / `--fax` / `--candidates tmp_vert/battle6/missing_cells.json` / `--out-dir tmp_vert/battle6` / `--strips-dir {out}/pilot25/strips` / `--items-out {out}/pilot25_items.json` / `--plan-out {out}/pilot25_plan.json` / `--pilot-cols 2000` / `--cols-per-page 8` / `--pages-per-batch 10` / `--dpi 200` / `--ctx 1.2` / `--jpeg-quality 85` | 2000 items + 250 页 + 25 批 |
| `api_pilot_judge.py` | `--book` / `--out-dir tmp_vert/battle6` / `--items {out}/pilot25_items.json` / `--polys {out}/api_pilot_25_polys.json` / `--out {out}/api_pilot_25.json` | 判定 JSON |
| `api_pilot_run.py` | `--book` / `--out-dir` / `--plan {out}/pilot25_plan.json` / `--out {out}/api_pilot_25_raw.json` | 逐批结果 |
| `api_candidates_all_build.py` | `--book` / `--data-dir` / `--src` / `--fax` / `--candidates` / `--out-dir tmp_vert/battle6` / `--strips-dir {out}/all25/strips` / `--items-out {out}/all_items.json` / `--plan-out {out}/all_plan.json` / `--cols-per-page 8` / `--pages-per-batch 30` / `--dpi 200` / `--ctx 1.2` / `--jpeg-quality 85` | 3828 items + 479 页 + 16 批 |
| `api_candidates_all_judge.py` | `--book` / `--out-dir` / `--items {out}/all_items.json` / `--raw {out}/api_candidates_all_raw.json` / `--out {out}/api_candidates_all.json` / `--src source_pdf/{book}.pdf` / `--crops-dir {out}/all_insert_crops` | 判定 + 清单 + 裁片 |
| `api_candidates_all_run.py` | `--book` / `--out-dir` / `--plan {out}/all_plan.json` / `--out {out}/api_candidates_all_raw.json` | 逐批结果 |

> 全部 7 个工具 `--help` 退出码 0 且含 `--book`（实测）。

## 2. 幂等验证

| 步骤 | 命令 | 结果 |
|---|---|---|
| census（新基线） | `/usr/bin/python3 src/tools/census_true_missing.py --book wz7 --out /tmp/b12/true_missing.json` | md5 **9dda98e477057ef08289996ab68df4fe** = 现 `tmp_vert/battle6/true_missing.json`（**逐字节**）；stats `{base:56105, fax:919, neighbor:246, noise:350, keep:1, variant_cols:6883}`、n=1 |
| census（旧口径对照） | 同命令 + `--page-height 1443` | md5 **afd42100a5193ed3c5b237978fd3e86d**（= t56/t57 旧记录，**仅对照保留**）；stats `{base:56109, fax:921, noise:351}` |
| all judge | `api_candidates_all_judge.py --book wz7 --out /tmp/b12/api_candidates_all.json --crops-dir /tmp/b12/crops` | 3,828 列 **逐条一致**（id/page/col/text/api/cls/ch/pos/ratio/complete/shape 全等；classes/hanzi/punct 一致；仅 `crop` 路径因自定义 crops-dir 不同） |
| pilot build | `api_pilot_build.py --book wz7 --out-dir /tmp/b12/pilot_out --items-out /tmp/b12/pilot25_items.json --plan-out … --strips-dir …` | 2,000 列 **集合一致**（page/col/text/n/cells/step）；250 页 / 25 批 |
| v42 | 未重跑（工具不进构建链） | `f964ad7133841025c2d415c40f52af89` 不变；fix JSON/数据未动 |

## 3. 守卫去魔法数 + 单元测试

- `build_vert.py`：
  - L316 `MISSED_FIX_MIN_PAGES = int(os.environ.get('VERT_MISSED_FIX_MIN_PAGES') or 1000)`
  - L561 `if len(keys) < MISSED_FIX_MIN_PAGES:`（原 `len(keys) < 1000`）
- 新测试 `src/test/unit/test_missed_fix_min_pages.py`（用 wz6 + 合成 fix JSON，子进程跑 build_vert）：
  1. `test_default_skips_small_book`：默认阈值 → `灌入 0 处 / 跳过 1`，页面文本无插入字；
  2. `test_zero_disables_guard`：`VERT_MISSED_FIX_MIN_PAGES=0` → `灌入 1 处 / missing_char 1`，页面出现插入字；
  3. `test_boundary_equal_pages`：`VERT_MISSED_FIX_MIN_PAGES=231`（= wz6 页数）→ 插入（`len(keys) >= 阈值` 分支；大书同源）。
- pytest（unit + invariants）：**593 passed**。

## 4. 门禁

- wz6：`VERT_TMP=/tmp/vert_wz6_b12 … wz6` → `BUILD_EXIT=0`；`vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节不变；verify **PASS**（231=231 / 68,412÷70,373=97.2% / 差异页 2 预期 / 整页丢失 0 / 越界 0+0）。
- pytest：**593 passed**（590+3 新增）。
- spec 16/18 锚点：build_vert 8009 行（+2）；已同步（见 §5）。

## 5. spec 同步

| 文件 | 改动 |
|---|---|
| `spec/vertical/16_missing_char_insert.md` | 守卫行：「`VERT_MISSED_FIX_MIN_PAGES`（环境变量，默认 1000 页）… 显式 0 关闭保护」；行号锚点按 8009 行重测：MISSED_FIX L314–322（常量 L316）、`_apply_missed_fix` L514、`_miss` L549、`_relocate_missing` L482、missing_char 分支 L558–572、`_br_fix/_br_shift` L971–990、`_MISSED_ST` L990、`fix_split_brackets` L919–957、QSF L6394 起、dash rule `_dash_runs` L349/`_dash_ink_seg` L367/`_dash_rule_tex` L435、`_ring_put` L462、统计 L598 |
| `spec/vertical/18_ring_digit_census.md` | §4 锚点：`_ring_ins_num` L456/`_ring_put` L462、`_apply_missed_fix` L514/ring 分支 L576–598、容差 L542、渲染 L4178–4180、MISSED_FIX L313–322、文件 8009 行；§3 第 7 行（API 条带）标「部分（通道参数化 implemented；圈码专用条带 planned）」 |

## 6. 换书使用示例（`--book wzX` 需要准备什么）

```bash
# 0) 需要的数据：data/wzX_full/wzX_full_spotting_lines_patched.json + wzX_full_spotting_coords.json
#    源图：source_pdf/wzX.pdf；影印页清单可给 --fax（不给则视为无影印页）
# 1) 可信真缺字普查（F1–F5）
/usr/bin/python3 src/tools/census_true_missing.py --book wzX --out tmp_vert/wzX/true_missing.json
# 2) 缺字格候选（外部步骤：missed_cells.json，格式同 wz7；--candidates 指定）
# 3) API 试建 / 全量条带（30 页/批，可调）
/usr/bin/python3 src/tools/api_candidates_all_build.py --book wzX \
  --candidates tmp_vert/wzX/missing_cells.json --out-dir tmp_vert/wzX
# 4) 提交/轮询/解析（token 只从本地文件读取，路径不入库）
/usr/bin/python3 src/tools/api_candidates_all_run.py --book wzX --out-dir tmp_vert/wzX
# 5) 判定 + 清单
/usr/bin/python3 src/tools/api_candidates_all_judge.py --book wzX --out-dir tmp_vert/wzX
# 6) 落库（人工/半自动生成 fix JSON）后构建；小书保护阈值按需：
VERT_MISSED_FIX_MIN_PAGES=0 VERT_MISSED_FIX=docs/vert_taskF_missed_fix.json \
  /usr/bin/python3 src/pipelines/build_vert.py data/wzX_full/... data/wzX_full/... out.pdf source_pdf/wzX.pdf
```

> 注意：`missing_cells.json`（检测器筛出的候选集）与最终 `fix JSON` 仍由人工/半自动步骤生成；工具只负责「候选 → 条带 → API → 判定」。
>
> **页高（t59/t61）**：census / pilot build / all build 的页高边界缺省取**源页实际高度** `src[pg-1].rect.height`，可用 `--page-height` 显式覆盖；页高 ≠ 1443pt 的开本（更高/更矮）不再被硬编码裁掉页底候选/条带。回归见 `src/test/unit/test_page_height.py`（合成 400×1600 书：缺省检出页底候选；`--page-height 1443` 时 0；all_build 页高 + 自定义 out-dir）。
>
> **wz7 新基线（t61 接受）**：wz7 源页有 **12 种高度（1083.75–1443.75pt）**；旧硬编码 1443 会保留**超出本页纸高**的页底窗口。新实现（源页高）比旧少 **4 个窗口**（stats：base −4、fax −2、noise −1）：
>
> | 页 | 列 | side | y0/y1 | 窗口 ya..yb | 本页纸高 | 旧分类 | 排除理由 |
> |---|---|---|---|---|---|---|---|
> | p561 | ci18 | bot | 1282.0/1311.1 | 1311.1..1340.4 | **1323.0** | base（dens<0.04） | yb=1340.4 > 1323，窗口在页外 |
> | p1026 | ci15 | bot | 1264.8/1321.7 | 1321.7..1328.0 | **1323.0** | fax | 同上（页外） |
> | p1026 | ci16 | bot | 1321.7/1321.7 | 1321.7..1328.0 | **1323.0** | fax | 同上（页外） |
> | p1171 | ci12 | bot | 1062.3/1080.8 | 1080.8..1118.4 | **1083.75** | noise（dens≥0.04） | yb=1118.4 > 1083.75，页外 |
>
> 即：旧 stats 的 `base 56109/fax 921/noise 351` 中，p561（base）、p1026×2（base+fax）、p1171（base+noise）是**页外窗口**；`n=1` 的最终条目两种口径都相同（items 全等）。旧口径可用 `--page-height 1443` 复现，仅作对照。回归断言：`src/test/unit/test_census_baseline.py`（快速断言仓库 `true_missing.json` md5/ stats = 新基线；`B12_CENSUS_SLOW=1` 时实跑断言 md5=9dda98e4…）。

## 7. 未工具化部分

1. `src/tools/census_ring_digit.py`（圈码检测）**不在本轮 in-scope**，仍硬编码 `data/wz7_full/...`、`source_pdf/wz7.pdf`、`tmp_vert/cj5`；spec 18 §3 第 5 行仍为 planned（下一轮可加 `--book`）。
2. **圈码专用 5 格 API 条带**仍未实现（现有条带是整列上下文；spec 18 §3 第 7 行已标 planned）。
3. **序列非降/LNDS** 仍是 battle4/5 临时脚本，无复用工具（spec 18 §3 第 9 行「部分」）。
4. **一键 wrapper**（`ring_census.py --book ...`）未实现（spec 18 §3 第 6 行 planned）。
5. `missing_cells` 检测器本身（battle6 的候选生成）不在仓库工具链内，换书需自备该 JSON（本报告 §6 已注明）。
6. **t59 修复记录**（不是遗留）：① 三处页高硬编码 1443pt → 源页高/`--page-height`（census、pilot build、all build）；② 两 build 工具的默认候选改为**先解析 `out_dir`** 再 `{out_dir}/missing_cells.json`（自定义 `--out-dir` 生效）；③ census docstring 改 `{book}` 推导、模块级 LINES/COORDS/SRC 改为空占位并注明「main() 覆盖」；④ 新增 `test_page_height.py`（3 条：源页高检出 / `--page-height 1443` 丢弃页底 / 自定义 out-dir 取本地候选）。
7. **t61 修复记录（新基线接受 + F2/F3 收尾）**：① **接受新基线**（源页高）：`true_missing.json` 更新为 md5 **9dda98e4…**、stats `56105/919/350`；旧口径 `afd42100…`（`--page-height 1443`）仅作对照保留；② 逐条列出 4 个被排除窗口（p561/p1026×2/p1171，见 §6 表），均为 **yb > 本页纸高**；③ 新增 `test_census_baseline.py`（2 条：仓库基线 md5/stats 断言 + `B12_CENSUS_SLOW=1` 实跑断言）；④ `test_page_height.py` 补 **all_build** 页高 + 自定义 out-dir 测试（共 4 条）；⑤ census docstring 第 5 行 `data/wz7_full` → `{book}_full`。
8. **changedPaths 追踪（补登 t59 未列路径）**：t56/t59/t61 实际改动文件（含此前未在 changedPaths 声明的）：
   - `src/tools/census_true_missing.py`、`src/tools/api_pilot_build.py`、`src/tools/api_candidates_all_build.py`、`src/tools/api_pilot_judge.py`、`src/tools/api_pilot_run.py`、`src/tools/api_candidates_all_judge.py`、`src/tools/api_candidates_all_run.py`
   - `src/pipelines/build_vert.py`（守卫环境变量；spec 16/18 锚点已同步）
   - `src/test/unit/test_missed_fix_min_pages.py`、`src/test/unit/test_page_height.py`、`src/test/unit/test_census_baseline.py`
   - `spec/vertical/16_missing_char_insert.md`、`spec/vertical/18_ring_digit_census.md`、`docs/battle12_systemize.md`、`docs/battle12_acceptance.md`、`tmp_vert/battle6/true_missing.json`（新基线）

## 8. 复现命令

```bash
cd /opt/test
# 幂等
/usr/bin/python3 src/tools/census_true_missing.py --book wz7 --out /tmp/b12/true_missing.json && md5sum /tmp/b12/true_missing.json
#   期望 9dda98e477057ef08289996ab68df4fe（新基线）；旧口径对照：加 --page-height 1443 -> afd42100…
/usr/bin/python3 -m pytest src/test/unit/test_census_baseline.py -q
B12_CENSUS_SLOW=1 /usr/bin/python3 -m pytest src/test/unit/test_census_baseline.py -q   # 实跑断言
/usr/bin/python3 src/tools/api_candidates_all_judge.py --book wz7 --out /tmp/b12/api_candidates_all.json --crops-dir /tmp/b12/crops
/usr/bin/python3 src/tools/api_pilot_build.py --book wz7 --out-dir /tmp/b12/pilot_out \
  --items-out /tmp/b12/pilot25_items.json --plan-out /tmp/b12/pilot25_plan.json --strips-dir /tmp/b12/pilot_strips
# 门禁
VERT_TMP=/tmp/vert_wz6_b12 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b12.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b12/vert.tex   # ae9d2f5259e12cff19e680b2a771b37d
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

## 9. 约束声明

- 未改 `src/test/verify_vert.py`、未改数据文件（`docs/vert_taskF_missed_fix.json` 等）、未 commit/push；token 未入库。
