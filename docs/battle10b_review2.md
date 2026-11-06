# battle10b 复审（round 2）· v42 补落 3 条引号

> 审查人：横排工程师（独立复审）　时间：2026-11-06 22:10–22:22
> 审查对象：t52 repair-round-2（补落 p1178 pos38/39、p1291 pos31 → v42）与更新后的 t47/t48 报告
> 基线：v41 `17ec4bb1…`；v42 `f964ad71…`；HEAD `3fe7f4e`
> 本报告为唯一新增文件；未改实现代码 / fix JSON / output，未 commit。
> 独立证据：`/tmp/t53/crops/ten_quotes_sheet.png`、`/tmp/t53/crops/p*_pos*.png`、`/tmp/t53/audit/`

---

## 0. 结论

**verdict = pass（v42 可交付、可作 battle10b 基线）**。t49 指出的 3 条闭引号已补落；独立复跑全部门禁通过：

| 项 | 结果 |
|---|---|
| v42 verify_vert | **PASS**：1748=1748 / **931,200**（v41 931,197 +3）/ 差异>80 字页 18（18 预期 / 0 非预期）/ 整页丢失 0 / 越界 span 0 + 矢量 0 |
| build42 复跑 | BUILD/FIX exit 0；重建 md5 `a05b49b2…` ≠ 交付物 `f964ad71…`，但 1748 页 text/words bbox 逐页 0 差异、text md5 `a6a31968…` 同、metadata（1970）/size 109,997,056 同 → **内容等价**（R1 /ID）；重建物 verify PASS |
| v41→v42 diff | **2 页 +3**（p1178 +2、p1291 +1；两条同在 p1178，故页数 2）——与 t52 一致 |
| wz6 | `vert.tex` `ae9d2f52…` 逐字节 + verify PASS（231=231 / 97.2% / 2 / 0 / 0+0） |
| pytest | **590 passed** |
| punct_audit | pair_balance **1990→1987（−3）**；pair_split 495、line_start 2582、dash_lead 1 均不变 |
| QSF 闭合不补 | v41/v42 `qsf.json` md5 **完全相同**（`ed82ca10…`）；925 条 items/stat 逐项相同（append 696、replace 229、pair_skip 32）；`append` 未增 |
| 无双引号 | `「「`/`」」`=0；`﹁﹁`=7、`﹂﹂`=239，v41→v42 **均未增** |
| 字节绑定 | 开工 22:10:08 = 收尾 22:21:34：build_vert `9b8f87e2…`、verify_vert `cc8b6937…`（=HEAD）、fix JSON `ad5c98f1…`、battle10_quotes `49227fef…`、battle10b_acceptance `d68383a6…`；v42 md5 `f964ad71…`；token 0 命中；未 commit |

**非阻塞残留**：
- **R1（数据标注缺口，不阻塞 v42 产物/门禁）**：t52 新增的 3 条 `missing_char` 的 `crop` 为空字符串，而 spec 16 §16.2/§16.5 要求每条有 `crop` 证据；外部裁片其实已存在（t47 `q04_p1178_」.png` / `q05_p1178_」.png` / `q06_p1291_」.png`，即 pos38/39/p1291）。建议补 `crop` 路径或重新裁 8× 闭角，更新 t52 报告；**无需重建 PDF**（只改数据元数据）。
- **R2（报告追踪，低）**：t52 更新了 `docs/battle10_quotes.md` 但未列入其 changedPaths（t52 输出已自述）；建议在交付说明中补登。

---

## 1. 字节绑定

| 文件 | 开工 22:10:08 | 收尾 22:21:34 | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `9b8f87e2…` | 同左 | 一致（数据-only） |
| `src/test/verify_vert.py` | `cc8b6937…` | 同左 | 一致且 = HEAD（`git diff` 空） |
| `docs/vert_taskF_missed_fix.json` | `ad5c98f1…` | 同左 | 一致（+3 条，160 条 missing_char） |
| `docs/battle10_quotes.md` | `49227fef…` | 同左 | 一致（t52 更新） |
| `docs/battle10b_acceptance.md` | `d68383a6…` | 同左 | 一致（t52 更新） |
| `tmp_vert/battle10/quotes/build42.sh` | `6010fd5b…` | 同左 | 一致 |

> v42 md5 `f964ad71…`；HEAD `3fe7f4e`；审查期间仓库源文件写入仅本报告；未 commit。

---

## 2. 独立复跑

- v42 交付物 md5 **`f964ad7133841025c2d415c40f52af89`**；verify PASS（931,200 / 98.8% / 18 预期 / 0 / 0+0）。
- 等价 build42（SOURCE_DATE_EPOCH=0，OUT 重定向 `/tmp/t53/wz7_full_v42.pdf`，不覆盖交付物）：BUILD/FIX exit 0，md5 `a05b49b2487274a19f393661db27a4ce`；
  1748 页 text/words bbox 逐页 0 差异、text md5 `a6a31968b224e665b777369f234f4cde` 相同、metadata（1970）/size 同；重建物 verify PASS
  → **内容等价**（R1 /ID）。
- v41→v42 逐页 diff：**2 页 +3**（p1178 +2、p1291 +1），无其他页变化。
- wz6 `ae9d2f52…` + verify PASS；pytest 590。
- punct_audit（v41/v42）：1990→**1987**；pair_split 495、line_start 2582、dash_lead 1 不变。
- QSF：v41/v42 `qsf.json` md5 `ed82ca10…` 相同；925 条 items、stat 逐项相同（append 696、replace 229、pair_skip 32）→ **「闭合不补」未被破坏**。

---

## 3. 引号逐条对账（t45 27 条分类）

### 3.1 落库 10 条（t47 的 7 + t52 补 3）

| 页/pos | ch | v42 上下文（唯一） | 源图角形 |
|---|---|---|---|
| p126 pos15 | 」 | `人物。﹂西門慶道` | 闭 `└` |
| p806 pos10 | 」 | `說罷。﹂西門慶道` | 闭 `└` |
| p1178 pos10 | 」 | `寒冷些。﹂須臾` | 闭 `└` |
| p1178 pos22 | 」 | `小厮們來。﹂原來` | 闭 `└` |
| p1178 pos38 | 」 | `盛服罷。﹂西門慶道` | 闭 `└`（t49 指出的误判，t52 补落） |
| p1178 pos39 | 」 | `遮衣服兒罷。﹂不一时` | 闭 `└`（同上） |
| p551 pos21 | 」 | `接你娘去。﹂因` | 闭 `└`（由 `——` 重判） |
| p818 pos23 | 」 | `甚麼嘴兒？﹂陳經濟` | 闭 `└`（由 `——` 重判） |
| p1231 pos6 | 「 | `︹金字經︺﹁夜迢迢` | 开 `┐` |
| p1291 pos31 | 」 | `明白了。﹂西門慶道` | 闭 `└`（t52 补落） |

- 10 条上下文各出现 **1 次**，无重复；独立裁片见 `/tmp/t53/crops/ten_quotes_sheet.png`（10 格）。
- 3 条补落项的源图角形均为闭 `└`（左竖+底横），与 t49 复审一致；v42 文本层已无缺失。

### 3.2 未落项（p1322 / p716 / p1568）

| 项 | 源图 | 结论 |
|---|---|---|
| p1322 pos4 | U 形，非闭 ﹂ | 不落正确 |
| p716 pos41 | cell 内是「下」字，无角形 | 不落正确（t45 误判） |
| p1568 pos10 | cell 仅撇点/空白 | 不落正确（t45 不确定） |

### 3.3 p563 / p1171 / —— / — / 8 / 6 / 3

- p563、p1171：v42 文本无 `……`；fix JSON 无 p563/p1171 条目；源图为目录 **leader 点线**（t47 大窗），不落正确。
- `——`/`—`：fix JSON 无新增文本条目；p551/p818 已按引号重判为 `」`；唯一 `——` 仍为 battle9 p57 的 dash 组（非本批）。
- `8`/`6`/`3`：fix JSON 无新增文本数字；p1693/p1696/p1729 只有既有 `class=ring` 条目（367 条未变），未给文本插数字。

### 3.4 「11 条」口径

- t47 的 11 行 = 8 条真漏 `」` + 1 条 `「` + p551/p818 两条 `——` 重判；其中 **p1322 不落**，故实际落 **10/11**。
- t45 的 11 条 = 10 条 `」` + 1 条 `「`（含 p716/p1568，不含 p551/p818）；t45 已把 p716 判误判、p1568 判不确定，p1322 为 U 形；t52 的补落集合与 t49 结论一致。
- 结论：**应落的 10 条全部落库**；p1322/p716/p1568 不落正确，不构成漏落。

---

## 4. 无双引号 / QSF / 判据

- `「「`/`」」`=0；`﹁﹁`=7、`﹂﹂`=239，v41→v42 未增；10 个插入列均无连续重复引号。
- QSF：v41/v42 `qsf.json` md5 相同、925 items/stat 相同、append 696/pair_skip 32 不变；punct_audit pair_balance 1987（−3）。
- `verify_vert.py` sha256 `cc8b6937…` = HEAD，`git diff` 空；`build_vert.py` 未改；判据未放宽。
- token：完整 token 及前 12 字符在 docs/battle10* / fix JSON / tmp_vert/battle10 中 0 命中。

---

## 5. 结论与残留

- **通过**：t49 指出的 3 条闭引号已补落；v42 931,200 / 2 页 +3 / 无双引号 / QSF 925 不变 / wz6 零回归 / pytest 590；重建内容等价；字节绑定与 token 合规。
- **R1（非阻塞）**：3 条新增 `missing_char` 的 `crop` 为空；外部裁片已在 t47 `q04/q05/q06` 存在，建议补 crop 路径或重新裁 8× 闭角（元数据-only，无需重建）。
- **R2（低）**：t52 更新 `docs/battle10_quotes.md` 未列入 changedPaths，建议补登。
- 建议：接受 v42 为 battle10b 基线；R1/R2 在合并前顺手修。
