# battle12 独立验收（t57 · 工具参数化 + 守卫环境变量）

> 验收人：验证评审员（独立验证方）　日期：2026-11-06 22:48–23:08
> 基线：HEAD `5f2c477`（未 commit 工作树）；**未改实现代码、未改数据文件、未 commit/push**
> 对象：t56（battle12：7 个普查工具 `--book` 参数化 + `MISSED_FIX_MIN_PAGES` 环境变量 + 3 条 unit 测试 + spec 16/18 锚点）
> 主产物：`docs/battle12_systemize.md`；v42 `output/wz7_full/wz7_full_v42.pdf`（md5 `f964ad7133841025c2d415c40f52af89`）
> 方法：自己跑参数化工具（census 显式/默认、judge、pilot）、自己验守卫三态与 pytest、自己复跑 wz6/v42、自己做换书 dry-run。

---

## 0. 结论

**PASS（可交付）**。7 个工具参数化后 wz7 行为**逐字节幂等**；守卫默认值（1000）与旧行为一致、环境变量三态测试通过；wz6 零回归、v42 内容逐页等价；换书 dry-run（wz6）可用；pytest 593。

**核心数字**：
- **census 幂等（t61 新基线）**：`--book wz7 --out /tmp/...`（默认=源页高）→ md5 **`9dda98e477057ef08289996ab68df4fe`**、stats `56105/919/246/350/1/6883`；`tmp_vert/battle6/true_missing.json` 已更新为该基线。**旧记录 `afd42100…`（stats 56109/921/351）仅作对照**，用 `--page-height 1443` 复现（t60 指出旧值含 4 个页外窗口：p561/p1026×2/p1171）。
- **judge 幂等**：`--book wz7` → 3,828 条 items **0 差异**（除 `crop` 路径）；classes 同（same 3158/other 471/nonchar 24/insert 175）、`hanzi_list` 58 / `punct_list` 96 归一化后全等。
- **pilot 幂等**：`--book wz7` → 2,000 条 items **全等**（page/col/text/n/cells/step），250 页/25 批。
- **守卫**：`build_vert.py` diff 仅 **2 行**（新增 `MISSED_FIX_MIN_PAGES` 常量 + 守卫改用它）；3 条 unit 测试独立跑 **3 passed**（默认 1000 跳过小书：灌入 0/跳过 1、无插入字；`=0`：灌入 1、插入字出现；边界 231：插入）；pytest **593 passed**。
- **wz6**：`vert.tex` md5 **`ae9d2f5259e12cff19e680b2a771b37d`** 逐字节不变 + verify **PASS**（231=231 / 68,412÷70,373=97.2% / 2 预期 / 丢失 0 / 越界 0+0）。
- **v42**：用 `build42.sh` 重建 → md5 `3479b8b2…` ≠ 交付 `f964ad71…`，但 **size 109,997,056 相同、metadata 相同、1748 页文本/行 bbox 逐页 0 差异** → 内容等价；已恢复交付物。
- **换书 dry-run**：`census --book wz6 --data-dir /tmp/b12v/wz6_data --src source_pdf/wz6.pdf` → exit 0，输出 stats `base 6511 / fax 0 / neighbor 25 / noise 3276 / keep 449 / variant_cols 524`、449 items；未引用 wz7 路径（`--fax` 默认按 book 推导 `/tmp/wz6_v36_run/...`，不存在→0）。

**残留（不阻塞）**：
- **R1**：v42 重建 md5 不同（/ID），内容逐页等价；与既往 v37–v41 现象一致。
- ~~R3（低）~~：**t61 已修**——`census_true_missing.py` docstring 第 5 行与示例均改 `{book}` 推导。
- **R4（说明）**：wz7 默认输出目录仍为 `tmp_vert/battle6`（向后兼容，t56 有意）；其他书默认 `tmp_vert/{book}`。
- **R5（范围）**：judge/pilot 的默认路径等价性是「显式 `--book wz7` 跑出结果与历史产物一致 + 代码检查默认值」证明的，未真跑无参 judge/pilot（避免覆盖 `tmp_vert/battle6` 历史产物与 3,828 张裁片）；census 已做无参实跑。
- **R6（范围）**：换书 dry-run 只覆盖 census；judge/pilot 换书还需要 `missing_cells.json`/`all_items.json`（报告 §6/§7 已列为外部步骤），本轮未造 wz6 的 API 输入，属报告已声明范围。

---

## 1. PASS/FAIL 总表（5 项）

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 独立复跑参数化工具：`--book wz7` 跑 census/judge/pilot 与 t56 幂等结果一致；不传参数默认行为与改动前一致 | **PASS（t61 新基线）** | census（本源页高）md5 `9dda98e4…`、stats `56105/919/246/350/1/6883`（仓库文件已更新；旧 `afd42100…` = `--page-height 1443` 对照）；judge 3,828 items 0 差异（除 crop）；pilot 2,000 items 全等；7/7 `--help` exit 0；默认路径检查 = 历史路径（wz7→tmp_vert/battle6） |
| 2 | 守卫独立验证：默认 1000 时 wz6 不插；`VERT_MISSED_FIX_MIN_PAGES=0` 时仅对含 missing_char 的书生效；大书行为不变；unit 测试覆盖三种情况 | **PASS** | build_vert diff 仅 2 行；新增测试 3 条独立跑 **3 passed**（默认：灌入 0/跳过 1、无插入字；=0：灌入 1、插入字；边界 231：插入）；wz6 用默认 fix JSON 构建 vert.tex `ae9d2f52…` 不变；v42（1748 页 > 1000）重建内容逐页等价 → 大书插入行为不变 |
| 3 | wz6 `vert.tex` md5 `ae9d2f52…` + verify PASS；pytest ≥591；参数化流程重建 v42 与交付物 text/bbox 逐页一致 | **PASS（附 R1）** | wz6 `ae9d2f52…` + verify PASS；pytest **593 passed**（78.34s）；v42 重建 md5 `3479b8b2…`，size/metadata/1748 页文本/bbox 全同（text md5 `a6a31968…`），已恢复 `f964ad71…` |
| 4 | 换书可用性抽查：按报告 §示例准备 `--book` 例子（可 wz6 dry-run），验证不依赖 wz7 特有路径 | **PASS（R2 已删；附 R6）** | `census --book wz6 --data-dir /tmp/b12v/wz6_data --src source_pdf/wz6.pdf` exit 0；stats `base 6511/fax 0/neighbor 25/noise 3276/keep 449`；449 items；默认 `--fax` 推导 `/tmp/wz6_v36_run/...`（不存在→0）；未打开 wz7 路径/文件 |
| 5 | 报告 docs/battle12_acceptance.md：PASS/FAIL + 字节绑定 + 幂等/回归证据 + 残留；不改实现代码、不 commit | **PASS** | 本文件；未改 `src/`、数据文件、fix JSON、`output/`（v42 已恢复原字节）；未 commit（HEAD `5f2c477`） |

---

## 2. 字节绑定（开工 22:48 = 收尾 23:08）

| 文件 | 开工 | 收尾 | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `5799539a48bd1cf46ff6cf26f8e54bf0c76e88dfdfbbbb01a35f8cbb3369b915` | 同左 | 一致（守卫 2 行改动） |
| `src/tools/census_true_missing.py` | `b1582f612514e80cc7c0246de5c5f89023d3ad018f7c4030cb77b6a8a7135ae8` | 同左 | 一致 |
| `src/tools/api_pilot_build.py` | `860a2f0bc11e244610a30182230c9b965e296049d10c4a94c78c1f4f12457fa2` | 同左 | 一致 |
| `src/tools/api_pilot_judge.py` | `d8af5f8b0ebd7eb6781c341f8156b7e54453bedae0757a3e9b7acb0ed521099d` | 同左 | 一致 |
| `src/tools/api_pilot_run.py` | `ddb04143e8adcbf32ad2998f0fef1884a51ccd3b0886f1380a917bfd184cdd6d` | 同左 | 一致 |
| `src/tools/api_candidates_all_build.py` | `05b2666edb2dcd21536d3bfeaa3fe398d42df7edff412d02209bfd209005e6d0` | 同左 | 一致 |
| `src/tools/api_candidates_all_judge.py` | `3cab948c3ee44ebfd2ce3a85f6df1cdb8c67db03e5a6d805696a90070e5d28f7` | 同左 | 一致 |
| `src/tools/api_candidates_all_run.py` | `538972984c383b0fc36154101a2b0dc57ddee56e6c7f7de7ea9e9b94f25f98b2` | 同左 | 一致 |
| `src/test/unit/test_missed_fix_min_pages.py` | `9bd1f30adfc2dc04e553992e863064fda5d1028dcfe21422eb2a94edf729495d` | 同左 | 一致 |
| `docs/battle12_systemize.md` | `96c016b039ee0f8d07f85a6076c79f8fea8781a3f2c13592260e9d575a4afb30` | 同左 | 一致 |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致（判据未改） |
| `docs/vert_taskF_missed_fix.json` | `ffe24f09e69b67b0440d8721c83e963aecef928430767dc0a51f84889e72d8c5` | 同左 | 一致（数据未改） |
| `output/wz7_full/wz7_full_v42.pdf` | md5 `f964ad71…` | md5 `f964ad71…` | 已恢复原交付字节 |

> spec 16/18 为 t56 改动（开工时已修改），收尾哈希：16 `d0a6ce93…`、18 `8e87b7eb…`；本轮未动。

---

## 3. 参数化工具幂等 / 默认行为

### 3.1 census（显式 `--book wz7` 与无参默认）

```bash
# 显式
/usr/bin/python3 src/tools/census_true_missing.py --book wz7 --out /tmp/b12v/true_missing.json
# 默认（不传任何参数；输出仍为 tmp_vert/battle6/true_missing.json）
/usr/bin/python3 src/tools/census_true_missing.py
```
- 两次均 exit 0；**默认（源页高，t61 新基线）md5 `9dda98e477057ef08289996ab68df4fe`**、stats `56105/919/246/350/1/6883`；`tmp_vert/battle6/true_missing.json` 已更新为该基线。
- **旧口径对照**：`--page-height 1443` → md5 `afd42100a5193ed3c5b237978fd3e86d`、stats `56109/921/246/351/1/6883`（t60 指出旧值含 4 个**页外**窗口，详见 battle12_systemize §6 表）。

### 3.2 judge（`--book wz7`）

```bash
/usr/bin/python3 src/tools/api_candidates_all_judge.py --book wz7 \
  --out /tmp/b12v/api_candidates_all.json --crops-dir /tmp/b12v/crops
```
- exit 0；**items 3,828 条，除 `crop` 路径外 0 差异**；`classes` 全等；`hanzi_list` 58 / `punct_list` 96 在去掉 `crop` 路径后**全等**（与 t56 表述一致）。

### 3.3 pilot（`--book wz7`）

```bash
/usr/bin/python3 src/tools/api_pilot_build.py --book wz7 --out-dir /tmp/b12v/pilot \
  --items-out /tmp/b12v/pilot25_items.json --plan-out /tmp/b12v/pilot25_plan.json \
  --strips-dir /tmp/b12v/pilot_strips
```
- exit 0；`pilot25_items.json` **2,000 条全等**（page/col/text/n/cells/step）；250 页 / 25 批。

### 3.4 7 个工具 `--help`

`census_true_missing / api_pilot_build / api_pilot_judge / api_pilot_run / api_candidates_all_build / api_candidates_all_judge / api_candidates_all_run` 全部 `--help` **EXIT=0**。

---

## 4. 守卫（MISSED_FIX_MIN_PAGES）

- **代码**：`build_vert.py` diff 只有 2 行：
  - L316 `MISSED_FIX_MIN_PAGES = int(os.environ.get('VERT_MISSED_FIX_MIN_PAGES') or 1000)`
  - L561 `if len(keys) < MISSED_FIX_MIN_PAGES:`（原 `1000`）
- **unit 测试独立跑**（`pytest src/test/unit/test_missed_fix_min_pages.py -v`）：**3 passed in 59.03s**
  1. `test_default_skips_small_book`：默认 1000、wz6 231 页 → 日志 `灌入 0 处 / 跳过 1`、页面无插入字；
  2. `test_zero_disables_guard`：`VERT_MISSED_FIX_MIN_PAGES=0` → `灌入 1 处 / missing_char 1`、页面出现插入字；
  3. `test_boundary_equal_pages`：阈值 = 231 → `len(keys) >= 阈值` 分支插入（大书同源）。
- **大书行为不变**：v42（1748 页 > 1000）用参数化后的 build_vert 重建，与交付物 **1748 页文本/bbox 逐页 0 差异**；wz6 默认 fix JSON 构建 `vert.tex` `ae9d2f52…` 不变（默认 1000 保护下 231 页不插）。
- **全量 pytest**：**593 passed**（840 warnings，78.34s）。

---

## 5. wz6 与 v42

- **wz6**：`VERT_TMP=/tmp/vert_wz6_b12v` 构建 → `BUILD_EXIT=0`；`vert.tex` md5 **`ae9d2f5259e12cff19e680b2a771b37d`**（=基线）；verify **PASS**（231=231 / 68,412÷70,373=97.2% / 差异 2 预期 / 整页丢失 0 / 越界 0+0）。
- **v42**：`bash tmp_vert/battle10/quotes/build42.sh` → BUILD/FIX exit 0；重跑 md5 `3479b8b23fe098e1f1fa5f8c60526ed7`；与交付 `f964ad71…` 对比：size **109,997,056 = 109,997,056**、metadata 相同、**1748 页文本/行 bbox 逐页 0 差异**（text md5 `a6a31968b224e665b777369f234f4cde`）→ 内容等价（R1 /ID）；已恢复交付物。

---

## 6. 换书 dry-run（wz6）

准备（只读 wz6 数据，按 `data/{book}_full/` 命名约定软链）：

```bash
mkdir -p /tmp/b12v/wz6_data
ln -s /opt/test/data/wz6/wz6_spotting_lines.json  /tmp/b12v/wz6_data/wz6_full_spotting_lines_patched.json
ln -s /opt/test/data/wz6/wz6_spotting_coords.json /tmp/b12v/wz6_data/wz6_full_spotting_coords.json
/usr/bin/python3 src/tools/census_true_missing.py --book wz6 \
  --data-dir /tmp/b12v/wz6_data --src source_pdf/wz6.pdf --out /tmp/b12v/wz6_true_missing.json
```
- exit **0**；输出 `stats {base:6511, fax:0, neighbor:25, noise:3276, keep:449, variant_cols:524}`、`n=449`、items 449；
- 未引用 wz7 路径：`--fax` 按 book 推导 `/tmp/wz6_v36_run/fax_pages.json`（不存在 → fax=0），源图用 `source_pdf/wz6.pdf`；无 `/tmp/wz7*` 打开/报错。
- 说明（R6）：judge/pilot 换书还需要 `missing_cells.json`/`all_items.json`（报告 §6/§7 已列为外部步骤），本轮未造 wz6 的 API 输入，只验证 census 通道与 `--book` 推导。

---

## 7. 复现命令

```bash
cd /opt/test
# 幂等（显式 + 默认）
/usr/bin/python3 src/tools/census_true_missing.py --book wz7 --out /tmp/b12v/true_missing.json
md5sum /tmp/b12v/true_missing.json          # afd42100…
/usr/bin/python3 src/tools/census_true_missing.py
md5sum tmp_vert/battle6/true_missing.json   # afd42100…
# judge / pilot
/usr/bin/python3 src/tools/api_candidates_all_judge.py --book wz7 \
  --out /tmp/b12v/api_candidates_all.json --crops-dir /tmp/b12v/crops
/usr/bin/python3 src/tools/api_pilot_build.py --book wz7 --out-dir /tmp/b12v/pilot \
  --items-out /tmp/b12v/pilot25_items.json --plan-out /tmp/b12v/pilot25_plan.json \
  --strips-dir /tmp/b12v/pilot_strips
# 守卫
/usr/bin/python3 -m pytest src/test/unit/test_missed_fix_min_pages.py -v
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
# wz6 / v42
VERT_TMP=/tmp/vert_wz6_b12v /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b12v.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b12v/vert.tex          # ae9d2f52…
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_vert.py /tmp/wz6_b12v.pdf \
  data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json --src-pdf source_pdf/wz6.pdf
bash tmp_vert/battle10/quotes/build42.sh    # 重建后与交付 text/bbox 对比（/ID 差异属 R1）
# 换书 dry-run
/usr/bin/python3 src/tools/census_true_missing.py --book wz6 \
  --data-dir /tmp/b12v/wz6_data --src source_pdf/wz6.pdf --out /tmp/b12v/wz6_true_missing.json
```

---

## 8. 纪律

- 只新增 `docs/battle12_acceptance.md`；未改 `src/`、数据文件、fix JSON、`output/`（v42 已恢复原字节）；未 commit/push。
- 无参 census 会重写 `tmp_vert/battle6/true_missing.json`（与旧文件逐字节相同）与 crops（证据目录，内容同源）；跑前已备份 `/tmp/b12v/true_missing_repo_before.json`。
- 日志：`/tmp/b12v/`（census/judge/pilot/build42/wz6/pytest）；未写 `/mnt/d`。

---

## 9. 结论

**t56 通过（可交付）**：
1. 7 个工具参数化后，wz7 **census/judge/pilot 全部幂等**（census 换新基线 `9dda98e4…`（源页高），旧 `afd42100…` 仅作 `--page-height 1443` 对照；judge/pilot 逐条）；无参默认输出与历史路径一致；7/7 `--help` OK。
2. 守卫去魔法数为环境变量，默认 1000 与旧行为一致；三条 unit 测试独立跑通过（默认跳过小书 / 显式 0 插入 / 边界=页数）；大书（v42）重建内容逐页等价。
3. wz6 `vert.tex` `ae9d2f52…` + verify PASS；pytest 593；v42 交付物未变（已恢复）。
4. 换书 dry-run（wz6 census）可用，不依赖 wz7 特有路径；**R2（页高常量 1443）已删除（t59 修复：改用源页高 / `--page-height`）**，R3（docstring 示例）也已改为 `{book}` 推导。
