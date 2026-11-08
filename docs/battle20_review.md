# battle20 终审 · v50 源墨复核落库

> 审查人：横排工程师（独立终审）　日期：2026-11-08 15:01–15:16
> 对象：t91（battle20：闭号/括号源墨复核 + t95 F1/F2 修复 → v50）与 t96 验收报告
> 基线：HEAD `84d6b95`（未 commit 工作树）；v49 `cef0bb5e…`；v50 `21216d14…`
> 本文件为唯一新增；未改实现/数据/fix JSON/output（build50 候选已恢复），未 commit

---

## 0. 结论

**verdict = pass（v50 可交付；带 3 条低残留/措辞）**。

- 独立复跑 build50：BUILD/FIX exit 0；重跑 md5 `540955c6…` ≠ 交付 `21216d14…`（/ID），但 **1748 页文本/内容流 0 差异、size 109,995,282/metadata 同** → 内容完全等价；已恢复交付物。
- verify_vert **PASS**：1748=1748 / **931,193** / 差异 18 全预期 / 丢失 0 / 越界 0+0。
- v49→v50 **text diff 8 页**（p230 +1、p358 +2、p898/p1122/p1229/p1234/p1256/p1354 各 +1），字符 **+9**；drawing diff 0；`﹂﹂`=**237**（与 v49 同，修复前 239）。
- 闭号 23→9 条：9 条 insert 均有 source crop + ink 指标（w 16.4–21.8 / h 7.7–16.6 / fill 0.29–0.37）；F1/F2 拒 14 条（相邻闭号/跨列/净 0）；p1254/p1444 不再 `﹂﹂`。
- QSF：**append 697 不变**（闭合不补未破）；qsf items 926→925、replace 229→228（p1256 一条 replace 因 insert 上下文消失）。报告 §9「无差异」不准确（F1 低）。
- 括号 271 条：`bracket_verify.json` applied 0、rejected 271，**reason 全为 `bracket_shape_fail`**；报告称两层 reason（`name_not_in_table`/`bracket_shape_fail`）与实物字段不一致（F2 低）。
- 测试 **617**（含 insert/replace 3 条）；wz6 `vert.tex` `ae9d2f52…` 逐字节 + PASS；无页白名单；token 0；v50 恢复 `21216d14…`。

---

## 1. 独立复跑

| 项 | 结果 |
|---|---|
| build50 | exit 0；重跑 md5 **`540955c67712783e7e33987b98d26556`** ≠ 交付 `21216d14…`（/ID）；size 109,995,282、metadata、1748 页文本/内容流 **0 差异**；已恢复 `21216d14…` |
| verify_vert v50 | **PASS**：1748=1748 / **931,193** / 差异>80 字页 **18**（预期 18/非预期 0）/ 丢失 **0** / 越界 span **0** + 矢量 **0** |
| v49→v50 text | **8 页**：230 +1 / 358 +2 / 898 +1 / 1122 +1 / 1229 +1 / 1234 +1 / 1256 +1 / 1354 +1 |
| v49→v50 drawing | **0 页** |
| 字符量 | 931,184→**931,193（+9）** = 9 insert + 0 replace + 0 删除 |
| 引号/空对 | `「「`/`」」`=0；`﹁﹁`=7、`﹂﹂`=237（v49/v50 同；修复前 239）；空对 **0** |
| QSF | append **697** 不变；items 926→925、replace 229→228（p1256 上下文）；见 F1 |
| wz6 | `vert.tex` **`ae9d2f52…`** 逐字节 + verify PASS（231=231 / 97.2% / 2 / 0 / 0+0） |
| pytest | **617 passed**；`test_missed_fix_insert_replace.py` **3 passed** |
| 字节绑定 | build_vert `0a90f6eb…`、build50 `8c08188c…`、t91 报告 `c484d509…`、test `64c4baa6…`、fix JSON `b7e7d006…`、verify_vert `cc8b6937…`（=HEAD）；token 0；v50 恢复 `21216d14…` |

---

## 2. 代码 / 证据链

### 2.1 闭号 insert（9 条）

- fix JSON `class="insert"` 9 条 `source=dual_ocr_ink`：p230/p358×2/p898/p1122/p1229/p1234/p1256/p1354；`pos` 行内、`ch="」"`、`col`（PDF pt）、`crop`、`ink {w,h,fill}`；无页白名单。
- 源图裁片 + ink 指标：w 16.4–21.8pt、h 7.7–16.6pt、fill 0.29–0.37，均在角形判据（8–26×4–18、fill 0.08–0.80、臂交角）内；9/9 自裁有角形。
- insert 在 battle14–16 引号清理**之后**应用（同列多 insert pos 降序），避免先插的 `」` 被清理；`VERT_MISSED_FIX_MIN_PAGES` 大书守卫；无页白名单。
- F1/F2：23 角形候选中 14 条被拒（raw pos±1 已有闭号 3、产物上下文已闭 10、p1458 重建后 `﹂﹂` 1、p1571 净 0 1）；保留 9；`repair_round2.json` 逐条。

### 2.2 括号（0 落，证据链）

- 271 条（补括号 148 + 括号类型 123）全部 rejected，`applied=0`；`bracket_verify.json` 271 条 reason 全 `bracket_shape_fail`（F2：报告声称两层 reason，实际字段单层）。
- 8 条抽样源图为 `一六一七`/`翫物喪志`/`福善禍淫`/`人的文學`/`福醫`/`倡妓`/`南西廂記`/`蘭陵` 的引号/圆括号引用短语，无 `〔〕` 竖笔；0 落正确。
- 全书 `︹/︺` 计数 v49=v50（76/74），名表外未改；曲牌规则未冲突。

### 2.3 QSF / missing_char / 替换

- QSF `append` 697 不变（闭合不补）；items 926→925、replace 229→228——p1256 一条 replace 因 insert 上下文消失；**报告 §9「无差异」不准确（F1 低）**。
- missing_char 160 / ring 367 / dash 1 本轮回填不变；与既有 160+3 条无重复。
- 2,379 条替换仍不落，`char_replace_list.json` 留字符仲裁轮；本次 0 replace，无吞字。

---

## 3. 影响面 / 抽样

- v49→v50 仅 8 页 +9 字；drawing 0；p703 这类候选密集页文本不变（无新增改动/空对/双引号）；`「「`/`」」`=0。
- 20 条自裁（t96）：9 闭号 + 3 旧 insert + 8 missing_char 全部正确；5 不命中（p30 开引号方向、p63/p64 无角形、p1254 raw 邻闭号、p1444 上一列末已闭号）理由成立。
- 9 条 insert 产物上下文：p230/p358/p898/p1122/p1229/p1234/p1256/p1354 均 `…。﹂`；p1254 `君。﹂唱`、p1444 `老婆﹂不一時` 不再 `﹂﹂`。
- 字符 +9 逐页与清单一致；`﹂﹂` 237 回到 v49 基线；QSF append 697 不变。

---

## 4. Findings（低）

| id | severity | problem | requiredFix |
|---|---|---|---|
| F1-qsf-wording | low | 报告 §9 称 QSF「无差异」，实际 qsf items 926→925、replace 229→228（p1256 上下文）；append 697 不变 | 报告改为 925/926、replace 差 1、append 697 不变；说明闭合不补未破 |
| F2-bracket-reason | low | `bracket_verify.json` 271 条 reason 全 `bracket_shape_fail`；报告称两层 reason（name_not_in_table/bracket_shape_fail） | 按实际字段改报告，或补 name_not_in_table 判定并重跑 |
| F3-md5 | low | build50 重跑 md5 `540955c6…` 与交付 `21216d14…` 因 /ID 不同，内容 0 差异 | 交付说明固定 `21216d14…`，无需重建 |
| F4-pending | 说明 | 2,379 替换、1,060 闭号中 1,037 未命中等按设计留待人工/字符仲裁 | 下一轮按 `char_replace_list.json`/`candidates.json` 处理 |

---

## 5. 结论

v50 的 9 条闭号 insert 有完整源图/ink 证据，F1/F2 拒 14 条使 `﹂﹂` 回到 237；v49→v50 恰 8 页 +9 字、drawing 0、p703 不变、QSF append 697 不变、wz6 逐字节、verify/wz6/pytest 617 全过；`replace` 0 项，无吞字。**通过终审，可交付**。F1/F2 为报告措辞/字段低残留，下一轮修正；F4 为按设计待人工。
