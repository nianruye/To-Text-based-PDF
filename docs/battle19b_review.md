# battle19b 终审 · v49 融合候选落库

> 审查人：横排工程师（独立终审）　日期：2026-11-08 12:29–12:44
> 对象：t88（battle19b：3 条 insert 落库 → v49）与 t89 验收报告
> 基线：HEAD `84d6b95`（未 commit 工作树）；v48 `44ca6f01…`；v49 `cef0bb5e…`
> 本文件为唯一新增；未改实现/数据/fix JSON/output（build49 候选已恢复），未 commit

---

## 0. 结论

**verdict = pass（v49 可交付；带 2 条低残留/说明）**。

- 独立复跑 build49：BUILD/FIX exit 0；重跑 md5 `11f43b1f…` ≠ 交付 `cef0bb5e…`（/ID），但 **1748 页文本/内容流 0 差异、size 109,995,110/metadata 同** → 内容完全等价；已恢复交付物。
- verify_vert **PASS**：1748=1748 / **931,184** / 差异 18 全预期 / 丢失 0 / 越界 0+0。
- v48→v49 **text diff 恰 3 页**（p308/p967/p1625 各 +1）；drawing diff 0；字符 +3；`「「`/`」」`=0；空对 0。
- 3 条 insert 源图均为 **`﹁` 角形 + 独立「一」**（p308/p967/p1625），v49 文本 `正是：﹁一窪…` / `﹁一百萬…` / `正是。﹁一朝…`；保留一、不吞字。
- QSF **qsf.json v48/v49 md5 完全相同**（`cf8962a6…`），闭合不补未破坏；既有 missing_char 160、ring/dash 未新增/未冲突。
- `replace` 0 项（fix JSON 无 replace），无吞字/错位风险；测试 2 条锁 insert/replace 与 wz6 小书守卫；pytest 616。
- 低残留：R1 报告「wz6 531 项全跳过」措辞不准（ring/dash 会尝试匹配）；R2 待人工候选 row/pos 为 A 行序（无法直接按产物行裁片）；R3 4,339 待人工 +1,967 异体字按设计未落。

---

## 1. 独立复跑

| 项 | 结果 |
|---|---|
| build49 | exit 0；重跑 md5 **`11f43b1ffbf614156d63c47c94595dd0`** ≠ 交付 `cef0bb5e…`（/ID）；size 109,995,110、metadata、1748 页文本/内容流 **0 差异**；已恢复 `cef0bb5e…` |
| verify_vert v49 | **PASS**：1748=1748 / **931,184** / 差异>80 字页 **18**（预期 18/非预期 0）/ 丢失 **0** / 越界 span **0** + 矢量 **0** |
| v48→v49 text | **3 页**：308 +1 / 967 +1 / 1625 +1；其余 1745 页 0 差 |
| v48→v49 drawing | **0 页** |
| 字符量 | 931,181→**931,184（+3）** = insert 3×1 + replace 0 + 删除 0 |
| 引号/空对 | `「「`/`」」`=0；`﹁﹁`=7、`﹂﹂`=237（v48/v49 同）；空对 **0** |
| QSF | `/tmp/wz7_v48_run/qsf.json` 与 `/tmp/wz7_v49_run/qsf.json` md5 **`cf8962a6…` 完全相同** |
| wz6 | `vert.tex` **`ae9d2f52…`** 逐字节 + verify PASS（231=231 / 97.2% / 2 / 0 / 0+0） |
| pytest | **616 passed**；`test_missed_fix_insert_replace.py` **2 passed**（insert/replace 生效 + 小书守卫） |
| 字节绑定 | build_vert `47b8838d…`、build49 `8dd8a605…`、battle19 报告 `0fc8784b…`、dual OCR `0f79fcb3…`、test `b1246268…`、fix JSON `a5fbc417…`、verify_vert `cc8b6937…`（=HEAD）；token 0；v49 恢复 `cef0bb5e…` |

---

## 2. 代码 / 证据链

### 2.1 insert（3 条）

- fix JSON 新增 `class="insert"`：p308/p967/p1625，`pos=0`、`ch="「"`、`col`（PDF pt）、`text`、`crop`；无 `current`/`new`，无 `ch` 多字符。
- `_apply_missed_fix`：列匹配 0.6pt → `insert` 在 `pos` 处插 1 字；大书守卫 `VERT_MISSED_FIX_MIN_PAGES`；日志 `insert 3`；无页白名单。
- 源图裁片（t89 自裁）：3/3 为 `﹁` 角形 + 独立「一」；v49 文本 `﹁一窪/﹁一百萬/﹁一朝`，pos 0 正确，保留一、不吞字。
- 其余 3 条 t87「可落库」已由 v48 规则覆盖：p679 `_fix_yi_after_name`、p692 `_fix_bare_cuv_names`，不重复落；v49 未见双重括号/引号。

### 2.2 replace（0 条）

- 代码：`class="replace"` 仅当 `cur[pos:pos+len(current)] == current` 替换，否则打印跳过；fix JSON **0 项**；测试 `test_insert_and_replace_applied` 用合成 replace 锁生效；无吞字/错位。
- 无页白名单；仍受大书守卫。

### 2.3 兼容 / QSF / 曲牌

- `qsf.json` v48/v49 **md5 相同**：3 条 insert 不改变 QSF 决策（闭合不补）。
- missing_char 160 既有项未变；ring 367/dash 1 未变；曲牌规则 `VERT_CUV_FIX=1` 仍生效，v49 未新增曲牌冲突（p692 已在 v48 覆盖）。
- wz6 231 页 <1000：missing_char/insert/replace 整类跳过；ring/dash 仍尝试列匹配（R1 措辞），`vert.tex` 逐字节不变。

---

## 3. 影响面 / 抽样

- v48→v49：仅 3 页（p308/p967/p1625）文本 +1，绘图 0；字符 +3；无其他页变化。
- 落库抽检：3 条 insert + 12 条既有 missing_char（p50 竊/p85 峴/p105 逕/p141 謄/p213 颳/p231 人/p247 不/p276 人/p319 前/p329 刺/p404 人/p411 粧）源图 cell 均见对应字（t89 自裁 15 条）。
- 待人工/未落抽检 12 条（替换/补括号/括号类型/补闭号/补开号/推断/异体字）理由成立；`candidates.json` row/pos 为 **A 行序**（R2），本轮用字段+上下文交叉核对，未按产物行裁片。
- 逐页 diff 与 t87 候选清单 3 条 applied insert 一致；无新增 `「「`/`」」`/空对。

---

## 4. 残留

- **R1（低）**：t88 报告称「wz6 531 项全跳过」不准确——531 含 `dash 1 / ring 367 / missing_char 160 / insert 3`；小书守卫只整类跳过 missing_char/insert/replace，ring/dash 仍尝试匹配并打印未匹配。`vert.tex` 逐字节 + verify PASS，零回归成立，仅措辞需改。
- **R2（说明）**：待人工候选 `row/pos` 是 A 整书 OCR 行序，与 patched_lines 行序不同；逐条源图裁片需按 A 行序，下一轮补。
- **R3（说明）**：4,339 待人工 + 1,967 异体字按设计未落；v49 是「自动可落库」档（6 条中 3 落、3 已覆盖），不是全书 OCR 差异全量修复。
- **R4（低）**：build49 重跑 md5 与交付 /ID 不同，内容 0 差异；交付说明固定 `cef0bb5e…` 即可。

---

## 5. 结论

v49 只落 3 条有源图证据的 insert（`﹁`+独立一，保留一），其余 3 条已由 v48 覆盖；v48→v49 恰 3 页 +3 字、绘图 0、QSF qsf.json 完全不变、wz6 逐字节、verify/wz6/pytest 616 全过；`replace` 0 项，无吞字/错位。**通过终审，可交付**。R1/R2/R3 为报告措辞/待人工范围说明，下一轮处理。
