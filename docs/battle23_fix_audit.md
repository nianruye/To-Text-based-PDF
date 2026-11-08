# battle23 · 修 t97 审计缺陷 → v51（t107 全量扫描收口版）

> 任务：t99 + t103 + t107（repair round 3）— M1/M3、括号判据、名表全量扫描、证据链
> 执行：竖排工程师　日期：2026-11-08
> 产物：`output/wz7_full/wz7_full_v51.pdf`（md5 **38d6656bf37720ff0277d7bd74a5d87a**）；构建 `tmp_vert/battle23/build51.sh`
> 约束：不改 verify 判据；不 commit；token 不入库。

## 0. 结论

| 项 | 结果 |
|---|---|
| M1 p1229 | 错误 insert 已移除，**insert 不新增**（v51 p1229 `？﹂﹄` 2 个 = v49 基线）；闭号族 `」』﹂﹄` + `src_ink_quotes` 闸门 + 单测；**残留登记**（源图 1 vs 产物 2，第 2 个来自 patched-lines 符号层，data 范围外） |
| 括号判据 | **全量扫描（name-table driven）**：55 条曲牌名 × 全书所有行 = **201 次名字出现**；p1180 r3 假阴性修复（判据加「格内上/下半 + 格外上/下」四窗，宽/高阈值放宽到 0.35 格宽/0.50 步进，ar 1.6–14）；p1180 **r3/r9/r16** 三行全部收口 |
| 全量对账 | 名字出现 **201** / 已正确 **76** / 邻接括号 **3** / 源图无括号 **29** / judge 命中 **93** → strict 过滤（行首或 A 名+句末上下文）**31**（mid-row 62 登记）→ 构建 **replace 27 / 跳过 4**（pos=-1 引号项） |
| 证据链 | fix 项 **42/42 crop 存在**（11 insert + 31 replace）；历史 3 条 **3/3**（p1625 路径改指 `hist_p1625_r01.png`）；replace 31/31 有裁片 |
| v51 | v50 931,193 → **931,240（+47）** = 24 条裸名 ×2（+48）+ 3 条引号名 ×0 − p1229 1；`︹/︺` 76/74 → **103/101**；21 页 diff |
| 门禁 | verify **PASS**（1748=1748 / **931,240** / 18 预期 / 丢失 0 / 越界 0+0）；wz6 **ae9d2f52…** 逐字节 + PASS；pytest **618 passed** |

## 1. M1：p1229（保留登记）

- 事实：p1229 r8 源图 `？」清` 1 个闭号墨块；v49 文本已有 2 个（`﹂﹄`，patched-lines 符号层）；v50 再插 1 → 3 个。
- 修复：移除 p1229 insert；闭号族守卫 `」』﹂﹄`；`src_ink_quotes` 闸门（产物局部闭号数 ≥ 源墨数 → 拒 + 日志）；单测 `test_insert_close_quote_gate`。
- 状态：v51 `？﹂﹄`（2 个，= v49），**insert 不新增**；**残留条目保留**：源图 1 vs 产物 2（第 2 个来自 data 层符号补全，待 data 轮）。

## 2. M3：证据链（全部真实存在）

| 证据集 | 生成数 | 存在率 | 说明 |
|---|---|---|---|
| fix JSON insert/replace | 42 | **42/42** | 11 insert（8 dual_ocr_ink + 3 历史）+ 31 replace；全部有 `crop` 字段且文件存在 |
| 历史 3 条（t88） | 3 | **3/3** | `hist_p0308_r04.png` / `hist_p0967_r00.png` / **`hist_p1625_r01.png`**（p1625 路径已回写 battle23） |
| closed_verify | 719 | 719/719 | 有 row/pos 者；341 token_mismatch 无 row/pos（登记） |
| char_replace | 2,379 | 2,379/2,379 | 全量 |
| bracket_verify | 266 | 266/271 | 5 条 name_not_found |

- `regen_crops.py`：makedirs + cell/行框/外扩三次尝试 + 失败 raise（不吞异常）；replace 裁片用名字所在格（`fs_p####_r##.png`）。

## 3. 括号：全量扫描（t107 收口）

- **方法**：55 条曲牌名表（含球/毬、綉/繡变体）× 全书 1748 页所有行；每命中一个名字：
  - 行内已 `︹/〔` → 已正确；两侧已 `︹/〔` 邻接 → judge 阶段拒（含 **p1322 罵玉郎**，左 `〔` 右 `」`）；
  - 引号名/裸名 → 裁名字首/末格，四窗判据（首格上半、首格上格外、末格下半、末格下格外；扁宽横笔 w≥0.35 格宽、h≤0.50 步进、ar 1.6–14）；
  - 命中 → `︹名︺`（引号名 0 长度，裸名 +2）。
- **对账（分母 = 名字出现次数）**：

| 项 | 数量 |
|---|---|
| 名字出现（55 名，全书） | **201** |
| 已正确（产品已有 ︹名︺/〔名〕） | **76** |
| judge 拒·邻接括号 | **3**（p1322 等） |
| judge 拒·源图无括号 | **29** |
| judge 命中 | **93** |
| strict 过滤后保留（行首 pos≤2 或 A 名+句末上下文） | **31** |
| strict 过滤掉（mid-row 名字） | **62**（登记，不落） |
| **构建阶段** replace 应用 / 跳过 | **27 / 4**（跳过：p641 金字經、p1180×2 滾綉毬、p1233 尾聲，pos=-1 引号项） |

- **p1180 收口**：r3/r9/r16 三行 `滾綉毬` 全部识别（v51 p1180 `︹滾綉毬︺` 3 处，+6 字）；p1179 `︹滾綉毬︺`（+2）。
- 抽检 8 条 crop（p450 尾聲 / p529/530 山坡羊 / p641 金字經 / p662 紫花兒序 / p693 烏夜啼/尾聲 / p702 山坡羊）：源图均有 `〔名〕` 扁宽横笔。
- 名表计划：A `〔名〕` ∪ v50 `︹名︺` ∪ 曲牌名单（55）+ 球/毬、綉/繡变体归一；新增名必须先过源图复核（本轮 strict 31 条全部有 crop）。

## 4. v51 字符对账

| 项 | 数量 | Δchar |
|---|---|---|
| 裸名补括号（24 条） | 24 | **+48** |
| 引号名归一（3 条） | 3 | 0 |
| p1229 移除 insert | 1 | **−1** |
| **v50→v51** | | **+47**（931,193 → **931,240**） |

- 逐页 diff：**21 页**（p450/529/530/662/693/702/840/921/985/1160/1179/1180/1222/1229/1247/1254/1271/1420/1470/1510/1567）；其中 p662/1247 0 长度（引号归一）、p1229 −1、其余 +2/+4/+6（多行同名）。
- `︹/︺`：76/74 → **103/101**（+27 对）；`﹂﹂` 237 不变；`「「/」」` 0。

## 5. 门禁

| 门禁 | 结果 |
|---|---|
| verify_vert（--expect-low） | **PASS**：1748=1748 / **931,240**÷942,935=98.8% / 差异>80 字页 18（预期 18/非预期 0）/ 整页丢失 0 / 越界 span 0+矢量 0 |
| wz6 | `vert.tex` **ae9d2f5259e12cff19e680b2a771b37d** 逐字节 + verify PASS |
| pytest | **618 passed** |

## 6. 复现命令

```bash
/usr/bin/python3 tmp_vert/battle23/regen_crops.py            # 证据链（42/42 + 历史 3/3）
/usr/bin/python3 tmp_vert/battle23/full_scan_brackets.py     # 全量扫描（201 名次，judge 93）
bash tmp_vert/battle23/build51.sh
md5sum output/wz7_full/wz7_full_v51.pdf                      # 38d6656b…
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v51.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
VERT_TMP=/tmp/vert_wz6_b30 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b30.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b30/vert.tex                            # ae9d2f52…
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

## 7. 证据与约束

- `tmp_vert/battle23/`：`full_scan_brackets.py`、`full_scan_brackets.json`（201 条对账）、`full_scan_filtered.json`、`bracket_judge.py/json`、`name_table*.json`、`build51.sh`、`regen_crops.py`、`crops/`（42 项 + 历史 3 + 其余 3,577 张）
- 代码：`build_vert.py`（insert 闭号族 + `src_ink_quotes` 闸门）；测试 `test_missed_fix_insert_replace.py`（+1）
- 只写 tmp_vert/battle23/ + 本文档 + fix JSON/build_vert/tests/output；未改 verify 判据/data/source_pdf；未 commit；token 0 命中。
- 残留：p1229 data 层符号重复（待 data 轮）；strict 过滤 62 条 mid-row 名（偏保守，未落）；5 条 bracket name_not_found；4 条构建跳过（pos=-1 引号项，已登记）。
