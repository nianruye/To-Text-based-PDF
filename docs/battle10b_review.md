# battle10b 终审报告（t49 · v41 引号落库）

> 审查人：横排工程师（独立审查）　时间：2026-11-06 21:34–21:5x
> 审查对象：t47（battle10b：11 条引号 → v41）与 t48 独立验收报告
> 基线：v40 `output/wz7_full/wz7_full_v40.pdf`（md5 5214c38e…）；v41 17ec4bb1…
> 本报告是唯一新增文件；未改实现代码 / fix JSON / output，未 commit。
> 独立证据：`/tmp/t49/crops/`（13 条引号 8× 裁片、p563/p1171 宽图、p1291/p1178 宽条、v41 ﹂/﹁ 字形对照）

---

## 0. 结论（先行）

**verdict = needs_revision（不能按 v41 交付 / 不宜作 battle10 基线）**。

v41 的三道门禁与 7 条已落引号全部成立；但 **t47/t48 把 3 条闭引号 `」` 误判为「开 ﹁ / 角形不完整」而未落库**：
**p1178 pos38、p1178 pos39、p1291 pos31**。三条源图角形都是 `└`（左竖+底横）= 闭 ﹂，与已落 p126/p1178 pos22 完全相同；
t47 自己的裁片 `q04/q05/q06` 也已是闭角。v41 少这 3 字，故 t49 的验收项「11 条引号是否全部落 / 无错位」不成立。
需 **v42 = v41 + 这 3 条 `」`**（p1322 仍不落；p716/p1568 仍不落），再跑全部门禁与 punct_audit。

| 项 | 结果 |
|---|---|
| v41 verify_vert | **PASS**：1748=1748 / 931,197÷942,935=98.8% / 差异>80 字页 18（18 预期 / 0 非预期）/ 整页丢失 0 / 越界 0+0 |
| build41 复跑 | BUILD/FIX exit 0；重建 md5 `2a6bf3f6…` ≠ 交付物 `17ec4bb1…`，但 1748 页 text/words bbox 逐页 0 差异、text md5 `b364fb80…` 同、metadata（1970）/size 109,997,031 同 → **内容等价**（R1 /ID）；重建物 verify PASS |
| v40→v41 diff | **6 页 +7**（p126/p551/p806/p818/p1231 各 +1，p1178 +2），无其他页变化 |
| wz6 | `vert.tex` `ae9d2f52…` 逐字节 + verify PASS（231=231 / 97.2% / 2 / 0 / 0+0） |
| pytest | **590 passed** |
| punct_audit | pair_balance **1993→1990（−3）**；pair_split 495=495、line_start 2582=2582、dash_lead 1=1 |
| QSF 闭合不补 | **未被破坏**：v40/v41 `qsf.json` md5 **完全相同**（`ed82ca10…`）、925 条 items/stat 逐项相同（append 696、replace 229、pair_skip 32）；`append 696` 未增、`pair_skip` 未减 |
| 无双引号 | `「「`/`」」`=0；`﹁﹁`=7、`﹂﹂`=239，v40→v41 **均未增**（p1231 的 `﹂﹂` 是 v40 已存在，未新增） |
| 字节绑定 | 开工 21:34:34 = 收尾 21:4x：build_vert `9b8f87e2…`、verify_vert `cc8b6937…`（=HEAD）、fix JSON `fb2799e9…`、battle10_quotes `18083133…`、battle10b_acceptance `f22e1779…`、build41.sh `82fe3656…`；v41 md5 `17ec4bb1…` |
| token | 完整 token 及前 12 字符在 docs/battle10* / fix JSON / tmp_vert/battle10 中 **0 命中** |

---

## 1. 字节绑定（实现文件与证据）

| 文件 | 开工 21:34:34 | 收尾 21:4x | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `9b8f87e21712a425f6a946b2427d3265a9196fafabb32331af9759ceae40c263` | 同左 | 一致（数据-only） |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致且 = HEAD（`git diff` 空） |
| `docs/vert_taskF_missed_fix.json` | `fb2799e9bffac74fc8ab0d3b5b472bdc939e0f8fd966464a664245fd237aec61` | 同左 | 一致 |
| `docs/battle10_quotes.md` | `18083133ad9539f02dc0101cf71ab61504266dbd99c1425fb396bc0da29a82ad` | 同左 | 一致 |
| `docs/battle10b_acceptance.md` | `f22e17794af7c79f779d30add8440587a2c25d2fb3fb0d3fbeb2859babd7a8b4` | 同左 | 一致 |
| `tmp_vert/battle10/quotes/build41.sh` | `82fe3656ec3dda4653bd45824594b7fc2c63cc9d2f384c4071e29bab36664a7d` | 同左 | 一致 |

> HEAD `3fe7f4e`；审查期间仓库源文件写入仅 `docs/battle10b_review.md`；未 commit。

---

## 2. 独立复跑

- v41 交付物 md5 **`17ec4bb1eb55f1ab382637dfd5d0c3fa`**；verify PASS（931,197 / 98.8% / 18 预期 / 0 / 0+0）。
- 等价 build41（SOURCE_DATE_EPOCH=0，OUT 重定向 `/tmp/t49/wz7_full_v41.pdf`，不覆盖交付物）：BUILD/FIX exit 0，md5 `2a6bf3f6433ef47d4e6c122816b9087d`（t48 为 `da3e7efc…`；/ID 每次不同），
  1748 页 text/words bbox 逐页 0 差异、text md5 `b364fb80740c7fb9772ea5556c5d0246` 相同、metadata（1970）/size 相同；重建物 verify PASS
  → **内容等价**（R1）。
- v40→v41 逐页 diff：**6 页 +7**（p126 669→670、p551 774→775、p806 757→758、p818 772→773、p1178 738→740、p1231 572→573），无其他页。
- wz6 `vert.tex` `ae9d2f52…` + verify PASS；pytest 590。
- punct_audit（v40/v41）：1993→**1990**；pair_split 495、line_start 2582、dash_lead 1 均不变；与 t47/t48 一致。
- QSF：v40/v41 `qsf.json` md5 **`ed82ca10c476edf9fda241bb5f68ecf3` 完全相同**；925 条 items、stat、crit 逐项相同
  （append 696、replace 229、pair_skip 32）；`append` 未增、`pair_skip` 未变 → **「闭合不补」规则未被破坏**（本轮 7 条插入未触发新的补写）。

---

## 3. 已落 7 条核对（全部正确）

| # | 页 | pos | ch | v41 上下文（唯一命中） | 源图角形 | 结论 |
|---|---|---|---|---|---|---|
| 1 | p126 | 15 | 」 | `人物。﹂西門慶道` | 闭 `└`（左竖+底横） | ✅ |
| 2 | p806 | 10 | 」 | `說罷。﹂西門慶道` | 闭 `└` | ✅ |
| 3 | p1178 | 10 | 」 | `寒冷些。﹂須臾` | 闭 `└` | ✅ |
| 4 | p1178 | 22 | 」 | `小厮們來。﹂原來` | 闭 `└` | ✅ |
| 5 | p551 | 21 | 」 | `接你娘去。﹂因` | 闭 `└`（由 `——` 按角形重判） | ✅ |
| 6 | p818 | 23 | 」 | `甚麼嘴兒？﹂陳經濟` | 闭 `└`（由 `——` 按角形重判） | ✅ |
| 7 | p1231 | 6 | 「 | `︹金字經︺﹁夜迢迢` | 开 `┐`（右竖+顶横） | ✅ |

- 7 条均无重复（上下文各 1 次）；`「「`/`」」`=0、`﹁﹁`/`﹂﹂` 未增；p1231 的 `﹂﹂` 在 v40 已有（`。﹂﹂︹金字經︺`），非本轮新增。
- v41 渲染字形核对：已落 p126 的 `﹂` 为 **`└`**、p1231 的 `﹁` 为 **`┐`** → 源图角形方向与 t47 的 7 条一致。

---

## 4. 阻塞发现 F1：3 条闭引号被误判为「开 / 不完整」而未落库

### 4.1 事实

| 页/pos | t47/t48 结论 | 我的 8× 源图（cell 取自 `punct27.json`） | 正确结论 |
|---|---|---|---|
| p1178 pos38 | 「开 ﹁，类型不符」 | **闭 `└`**（左竖+底横），位于 `盛服罷。` 后、`西門慶道` 前 | **应落 `」`** |
| p1178 pos39 | 「角形不完整」 | **闭 `└`**，位于 `遮衣服兒罷。` 后、`不一时` 前 | **应落 `」`** |
| p1291 pos31 | 「开 ﹁，疑重复」 | **闭 `└`**，位于 `明白了。` 后、`西門慶道` 前 | **应落 `」`** |

- 证据：`/tmp/t49/crops/x05_p1178_pos38_close.png`、`x06_p1178_pos39_close.png`、`x04_p1178_pos22_close.png`（对照）、`x08_p1291_pos31_close.png`；
  宽条 `/tmp/t49/crops/p1178_strip.png`、`p1291_strip.png`（可见 `…盛服罷。└西門慶道：┐…`、`…明白了。└西門慶道：┐…`）。
- **t47 自己的裁片也已是闭角**：`tmp_vert/battle10/quotes/q04_p1178_」.png`、`q05_p1178_」.png`、`q06_p1291_」.png` 均为 `└`；
  t47/t48 的「开 ﹁」结论与它们自己的证据相矛盾。
- 方向锚：v41 已落 p126 的 `﹂` = `└`、p1231 的 `﹁` = `┐`（`/tmp/t49/crops/v41_p126_closed.png`、`v41_p1231_open.png`），所以 `└` 是闭角，不存在「左竖+底横 = 开」的读法。
- 三条在 v41 文本层均**无** `」`（`盛服罷。西門慶道`、`遮衣服兒罷。不一时`、`明白了。西門慶道`），插入不会产生双字；
  源图各有一组开 `「` 在前（`「大人請寬了…`、`「大人只顧穿…`、`任醫官道：「我已…`），闭角正好配对。

### 4.2 影响

- t49 验收项「11 条引号是否全部落」不成立：t47 的 11 条中 **7 落 / 4 不落**，但 4 条不落里有 **3 条应落**（仅 p1322 的 U 形不是闭角）。
- t48 的 PASS 结论在「4 条未落」上不成立（它同样把 3 条闭角判为开/不完整）；t48 的其余复跑/回归数字仍有效。
- v41 产物本身无错字/无双字，只是**少 3 条真漏**；可保留 v41 作为 v42 基线，不需要回退。

### 4.3 Required fix（下一轮）

1. 在 fix JSON 加 3 条 `missing_char`（source=`api_strip_punct`，ch=`」`，page/pos 如下）：
   - p1178 pos38（cell [415.2, 898.6, 440.6, 918.3]）
   - p1178 pos39（cell [315.1, 917.3, 339.1, 937.1]）
   - p1291 pos31（cell [163.6, 759.8, 196.0, 779.4]）
   text/api/crop/cell 沿用 `tmp_vert/battle10/punct27.json` 对应条目；crop 重新裁 8× 闭角。
2. 重建 v42（预期 **931,200** = v41 +3；v40→v42 +10；diff 3 页 +3），跑 verify_vert（18 预期）、wz6 逐字节、pytest 590。
3. 复跑 punct_audit：预期 pair_balance 再降（3 条闭合合法配对）；pair_split/line_start/dash_lead 不增；检查 `﹂﹂` 不增、无同列双引号。
4. QSF：v42 的 qsf.json 与 v41 对照，确认 `append` 不增、`pair_skip` 不因这 3 条被破坏（闭合不补）。
5. 报告更新 t47/t48 的「4 条不落」为「p1322 不落；p1178 pos38/39、p1291 应落」，并说明误判根因（角形方向读反/裁片未按 cell）。

---

## 5. 与 t45 27 条分类对账

| 类 | t45 分类 | 本轮核对 |
|---|---|---|
| 引号 `」/「` | t45 的 10 `」` + 1 `「`（含 p716/p1568 误判/不确定，不含 p551/p818 重判） | t47 另把 p551/p818 从 `——` 重判为 `」`；合并后共 13 条引号候选。已落 7；应再落 3（F1）；p1322 U 形不落；p716（`下`字，无角）、p1568（仅撇点）不落 —— 均正确 |
| p563 / p1171 `……` | 真漏/不确定（目录点线） | 自裁 `/tmp/t49/crops/dots_p563_wide.png`、`dots_p1171_wide.png`：列内等距圆点 + 下方页脚（五八九 / 一六七…），**目录 leader 点线**；v41 文本无 `……`、fix JSON 无条目 → **不落正确** |
| `——` / `—` | 5 + 1：p551/p818 重判引号，其余 4 条误判/角形 | fix JSON 仅 +7（`」`×6+`「`×1），**无新增 ——/— 文本条目**；唯一 `——` 是 battle9 p57（t42 已验收的 dash 组），非本轮；p520/p633/p941/p600 未落 ✓ |
| `8`/`6`/`3` | p1729×2 圆圈、p1693/p1696 圈码 ㉞ | fix JSON 无新增文本数字；这些页只有既有 ring 条目（未变）；v40→v41 diff 不含这些页 → **未落文本数字** ✓ |
| QSF | `闭合不补` | qsf.json v40/v41 完全相同（925 条、append 696、pair_skip 32）；`﹂﹂` 239 未增 → **未被破坏** ✓ |

---

## 6. 判据 / token / 纪律

- `verify_vert.py` sha256 `cc8b6937…` = HEAD；`git diff` 空；`build_vert.py` 未改；判据未放宽。
- token：完整 token 及前 12 字符在 docs/battle10* / fix JSON / tmp_vert/battle10 中 0 命中。
- 审查期间仓库源文件写入仅 `docs/battle10b_review.md`；未改实现代码 / fix JSON / output，未 commit（HEAD `3fe7f4e`）。

---

## 7. 结论

- **不能按 v41 最终交付/作 battle10 基线**：7 条已落正确，但 p1178 pos38、p1178 pos39、p1291 pos31 是闭 `」`，t47/t48 的「开/不完整」判断错误；v41 少 3 条真漏。
- **verdict = needs_revision**；建议保留 v41 作为 v42 基线，补 3 条后重跑 verify/wz6/pytest/punct_audit/QSF，再作最终验收。
