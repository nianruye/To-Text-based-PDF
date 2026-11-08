# battle19b · 融合候选落库 → v49

> 任务：t88 — 把 t87 的「可落库」候选落库（数据+规则扩展），重建 v49，过门禁
> 执行：竖排工程师　日期：2026-11-08
> 产物：`output/wz7_full/wz7_full_v49.pdf`（md5 **cef0bb5e8e412e08720435c4a5f328e6**）；构建脚本 `tmp_vert/battle19/apply/build49.sh`
> 约束：只落「可落库」档；「待人工」不落；未硬编码页白名单；未 commit；token 未入库。

## 0. 结论

| 项 | 结果 |
|---|---|
| 落库 | **3 条 insert**（p308/p967/p1625：源图「角形+合法一」→ 插入 `「`、保留 `一`，各 +1 字） |
| 其他可落库候选 | **p679 已覆盖**（v48 `_fix_yi_after_name` 已产 `﹁一壁厢`）；**p692 感皇恩/針線廂 已覆盖**（v48 `_fix_bare_cuv_names` 已产 `︹名︺`）——不重复落 |
| 待人工 | **4,339 条不落**（替换 2,379 / 补闭号 707 / 推断闭号 353 / 补开号 631 / 补括号 148 / 括号类型 121） |
| v49 | **931,181 → 931,184（+3）**；v48→v49 文本 diff **恰 3 页**（p308/p967/p1625 各 +1）；verify **PASS**（1748=1748 / 18 预期 / 丢失 0 / 越界 0+0） |
| wz6 | `vert.tex` **ae9d2f52…** 逐字节不变（小书守卫：231<1000，531 项全跳过）；verify PASS |
| pytest | **616 passed**（614+2 新测试） |

## 1. 落库清单（t87 可落库 6 条逐条处置）

| t87 候选 | 处置 | 说明/证据 |
|---|---|---|
| p308 r4 `是：一窪死水…` | **落库（insert `「`，pos 0）** | 源图裁片 `crops/p0308_r04_q.png`：`「一窪死水全無浪…`（角形 + 合法「一」）；t87 原判 replace `一`→`「` 会吞字，按源图改为**插入并保留一** |
| p967 r0 `一百萬軍中…` | **落库（insert `「`，pos 0）** | 源图 `「一百萬軍中捲白旗…`（同上） |
| p1625 r1 `一朝時運至…` | **落库（insert `「`，pos 0）** | 源图 `「一朝時運至…`（同上） |
| p679 r5 `七兄一壁厢…` | 不落（**已覆盖**） | v48 已由 `_fix_yi_after_name` 产出 `﹁一壁厢`（battle16）；再落会双重插入 |
| p692 r16 `「感皇恩」` | 不落（**已覆盖**） | v48 已由 `_fix_bare_cuv_names` 产出 `︹感皇恩︺`（battle16） |
| p692 r20 `「針線廂」` | 不落（**已覆盖**） | v48 已产 `︹針線廂︺` |

> 落库数据：`docs/vert_taskF_missed_fix.json` 追加 3 条 `class="insert"`（page/col(pt)/pos/ch/text/crop），文件 528→531 项。

## 2. 新机制（可审计，无页白名单）

`build_vert.py` 的 `_apply_missed_fix` 新增两类（与 dash/ring/missing_char 同源分组/列匹配）：

- **`insert`**：`{page, col, pos, ch, text}` → 在该列 `pos` 处插入 `ch`（大书守卫 `VERT_MISSED_FIX_MIN_PAGES`，默认 1000；wz6 231 页自动跳过）；日志计入 `insert N`。
- **`replace`**：`{page, col, pos, current, new}` → 仅当 `text[pos:pos+len(current)] == current` 时替换，否则**跳过并打印**（防错位误改）；日志计入 `replace N`/`跳过`；同样受大书守卫。
- **无页面白名单**：全部由 fix JSON 数据驱动；列匹配沿用 0.6pt 容差（既有 `_apply_missed_fix` 口径）。
- **测试**：`src/test/unit/test_missed_fix_insert_replace.py` 2 条（wz6 + 合成 fix JSON）：
  1. `VERT_MISSED_FIX_MIN_PAGES=0` 时 insert 生效（PDF 文本出现 `﹁`+列首 3 字）且 replace 生效（`毛換東`）；
  2. 默认阈值（wz6 231 页）时 insert **不生效**（小书守卫）。

## 3. 待人工 / 不落（4,339 + 1,967）

- **待人工 4,339**：替换 2,379（A/B 真实字符差异，需源图逐条仲裁）、补闭号 707 + 推断 353（需句末/源墨证据）、补开号 631（源墨角形判据未过）、补括号 148（引用短语/非独立名）、括号类型 121（引用短语）。
- **不处理 1,967**：替换类中的异体字（OpenCC t2s 同简体，如 為/爲、蓋/葢、回/囘）。
- 均留在 `tmp_vert/battle19/candidates.json`（`tier` 字段），不进入 v49。

## 4. 与既有 160 条 missing_char 去重

- **0 条重复**（同 page/col/pos 无交集）。
- p1625 同页有 2 条 missing_char（列 `[411.0,126.8,439.2,986.5]`、`[134.7,126.8,167.1,981.0]`），与本次 insert 列 `[616.9,207.05,640.85,340.4]` **不同列**；其余两页无 missing_char 项。
- missing_char 160 项在 v49 照常灌入（日志 `missing_char 160`），与本轮 3 条 insert 并存。

## 5. 字符量对账

| 项 | 数量 | Δchar |
|---|---|---|
| insert（p308/p967/p1625） | 3 | **+3** |
| replace | 0 | 0 |
| missing_char（既有） | 160 | （v48 已含，不变） |
| 删除 | 0 | 0 |
| **合计 v48→v49** | | **+3**（931,181 → **931,184**） |

逐页 diff：p308 +1（`正是：﹁一窪`）、p967 +1（`﹁一百萬`）、p1625 +1（`正是。﹁一朝`）；其余页 0。**与候选清单完全一致**（3 条 applied insert 对应 3 页）。

## 6. 门禁

| 门禁 | 结果 |
|---|---|
| verify_vert（--expect-low） | **PASS**：1748=1748 / **931,184**÷942,935=98.8% / 差异>80 字页 18（预期 18/非预期 0）/ 整页丢失 0 / 越界 span 0+矢量 0 |
| wz6 | `/tmp/vert_wz6_b22/vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节 + verify PASS（日志 `灌入 0 处… 跳过 531`，小书守卫生效） |
| pytest | **616 passed**（614+2：insert/replace 生效 + 小书守卫） |

## 7. 复现命令

```bash
bash tmp_vert/battle19/apply/build49.sh
md5sum output/wz7_full/wz7_full_v49.pdf          # cef0bb5e8e412e08720435c4a5f328e6
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v49.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
VERT_TMP=/tmp/vert_wz6_b22 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b22.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b22/vert.tex                  # ae9d2f5259e12cff19e680b2a771b37d
/usr/bin/python3 -m pytest src/test/unit/test_missed_fix_insert_replace.py -v
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

## 8. 约束声明

- 只落「可落库」档 3 条（其余 3 条已由 v48 规则覆盖，不重复落）；「待人工」4,339 条未落并登记。
- 新机制无页白名单：数据驱动（fix JSON）+ 列匹配 + 大书守卫 + 逐条日志/跳过原因。
- 未改 `verify_vert.py` 判据 / data / source_pdf / output 之外的产物；未 commit/push；token 未入库。
