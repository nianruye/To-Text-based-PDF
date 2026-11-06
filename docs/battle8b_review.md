# battle8b 终审报告（t36 · v38 引号落库）

> 审查人：横排工程师（独立审查）　时间：2026-11-06 01:42–02:0x
> 审查对象：t34（引号类漏识落库 → v38）与 t35 验收报告
> 基线：HEAD `9207b2c` + 未提交工作树；本报告是唯一新增文件；未改实现代码、未 commit / push
> 输入：`docs/vert_taskF_missed_fix.json`、`tmp_vert/battle6/api_candidates_all.json`（punct_list 96）、
> `tmp_vert/battle8/verify/{keep,skip}.json`、`output/wz7_full/wz7_full_v38.pdf`、`source_pdf/wz7.pdf`（只读）
> 原则：不采信自述——自己复跑 build38/verify/wz6/pytest/punct_audit/classify，自己从源图裁引号，
> 自己核对 QSF 决策与 72 条逐条位置。

---

## 0. 结论（先行）

**verdict = pass（产品可交付、可作 battle8b 基线）。** 72 条引号落库与 punct_list 96 条一一对应（72 keep + 24 skip），
无多落/漏落；每条有源图裁片+角形证据；43 条「——」全部按闭引号重判，**fix JSON 与 v38 文本层均无 `——`/`—` 落库**；
自裁 12 条源图全部为引号角形；v38 无同一位置双引号（「「/」」/﹁﹁ 0；﹂﹂ 240→239，无新增）；
QSF 决策记录 925 条与 v37 逐条相同（append 696/replace 229），「闭合不补」未被破坏；
v38 verify/wz6/pytest/punct_audit 全部通过，字符量 +72 逐页可解释；判据未改、token 未外泄。

**附带两条报告口径修正（不阻塞产品，t35 已指出、t34 报告尚未改）**：
- **R2**：t34 报告 §2 的「4 页有 QSF 侧伴随变化」及 p1034「REPL ﹂西」不准确——独立 diff 实测
  **QSF 文本效果只有 2 页**（p866 插入「一」、p928 插入「﹂」且 ﹂→一），**p1034 是纯插入「﹂」**。
- **R3**：t34 报告 §3 未披露 **B 类 6→17（+11）**；11 条新 B 全部是本批**行中插入**的闭引号
  （11 页均为 quote item 页、feat.corner=true），pair_balance 的行级判据把它们记成 B，属审计口径假阳性，不是产品缺陷。
- 另：t35 报告称 quote 条目「crop/cell/**strip** 证据 0 缺失」，实际 72 条 quote item **无 `strip` 字段**
  （t34 的字段表本来也只有 crop/cell/feat/verdict；crop 72/72 存在）。低级别表述问题。

其余低级别：R1 build38 非字节可复现（md5 每次不同，text/bbox/metadata 全同）；R4 11 条 t24 既有 missing_char
无证据字段（非本轮 72 条）。

---

## 1. 字节绑定（实现文件与报告）

| 文件 | 开工 01:43:10 | 收尾 | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `9b8f87e21712a425f6a946b2427d3265a9196fafabb32331af9759ceae40c263` | 同左 | 一致（mtime 00:49:xx，t32 后未改） |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致，且 = `git show HEAD:src/test/verify_vert.py`（判据未放宽） |
| `docs/vert_taskF_missed_fix.json` | `f4e4f7f2e9c03a9d15f2292d6306861eb7b75cacd43ad6253c60f7e75c70106c` | 同左 | 一致 |
| `docs/battle8_quotes.md` | `48a7b6d38cd91464ec45a3caef1be5e40420bf690e76abb2261ed236e659f389` | 同左 | 一致 |
| `tmp_vert/battle8/build38.sh` | `60d66701d0414f93db27431775ae6dfb08cc016d557121736767276d7402f7ef` | 同左 | 一致 |

- t34 范围：fix JSON（M）+ battle8 报告（??）+ tmp_vert/battle8 证据；t35 仅新增 acceptance 报告；
  `build_vert.py` 的 M 是 battle3–7 遗留（mtime 00:49，早于 t34），t34 未改实现代码。
- 全程只写 /tmp/t36；本报告只新增 `docs/battle8b_review.md`；HEAD 仍 `9207b2c`，未 commit。

---

## 2. 独立复跑

| 命令 | 结果 |
|---|---|
| `verify_vert` v38（带 `--expect-low`） | **PASS**：1748=1748 / 931,178÷942,935=98.8% / 差异>80 字页 18（18 预期 / 0 非预期）/ 整页丢失 0 / 越界 span 0+矢量 0 / exit 0 |
| 等价 build38（`SOURCE_DATE_EPOCH=0`，OUT 重定向 `/tmp/t36/wz7_full_v38.pdf`，不覆盖交付物） | BUILD/FIX exit 0；重建 md5 `6b9587948ebb4863b5f58d8790aabf16` ≠ 交付物 `6f5b1c64…`；**1748 页文本逐页 0 差异、words bbox 逐页 0 差异、text md5 `0571e02b…` 相同、metadata（1970-01-01）与 size 全同** → 内容等价，差异仅 PDF /ID（R1；t35 重跑得到另一个 md5 `cd385f26…`，同一现象） |
| `punct_audit` v37/v38（同一命令） | pair_balance **2001→1995（−6）**、pair_split 495=495、line_start 2582=2582、dash_lead 1=1；`﹂` 12,482→12,550（+68）、`﹁` 12,486→12,488（+2）——与 t34 §3/t35 完全一致 |
| `punct_classify` v37/v38 | B **6→17（+11）**、O 359→348、K_weak 960→951、K 3→4、C_fixed 721→723、C 175=175、A 3528=3528；与 t35 §6 一致 |
| wz6 | `vert.tex` `ae9d2f5259e12cff19e680b2a771b37d` 逐字节 + verify **PASS**（231=231 / 68,412÷70,373=97.2% / 差异 2 预期 / 整页丢失 0 / 越界 0+0） |
| pytest | **590 passed**（19.47s） |
| QSF 决策 | v37 构建 `/tmp/wz7_v37_run/qsf.json` 与 v38 构建 `/tmp/wz7_v38_run/qsf.json` **items 925 条完全相同（0 差异）**；append 696 / replace 229 相同；stat 仅 `cand 2874→2875`、`bar 654→655` |

字符量：v37 931,106 → v38 **931,178（+72）**；67 页变化 = 62 页 +1、p362/p925/p1178/p1500/p1588 各 +2（源文本原始长度差含换行，归一后即 +72）。

---

## 3. 引号落库清单 ↔ punct_list（通过）

- `punct_list` 96 条；`keep.json` 72 + `skip.json` 24 = **96**（按 (page, ch) 多重集核等，无多落/漏落）。
- `fix` 中 `class=missing_char, source=api_strip_quote` = **72 条**，与 keep 72 条按 (page, pos, target) **一一对应**（0 差异）；
  `ch` = 70 `」` + 2 `「`；verdict = `close-ok` 27 / `reclass-close` 43 / `open-ok` 2。
- 字段：page/col/pos/ch/side/source/confidence/ratio/exp_len/text/api/crop/cell/feat/verdict 全齐；
  `feat.corner=true` 72/72；**crop 72/72 文件存在**（quote_crops），无重复 key、无同 pos 异字。
- **24 条不插**与 t34 报告一致：no-corner 12、other 9（含 H/8/】/）/」「/」。 6 条误判）、target-at-pos 2、dup-existing 1（p592）。
- **无 `——` 落库**：fix JSON 全部 items 的 `ch` 无 `——`/`—`/`–`；43 条 reclass 的 keep 原 ch 为 `——`、target=`」`、
  fix ch=`」`，43/43 对应；p814/p1006/p1180 三条 no-corner 不插。v37→v38 文本 diff 的插入/替换字符只有
  `﹂`×69、`﹁`×2、`一`×2（两个 `一` 分属 p866/p928 的 QSF 伴随），**无 `—`/`——` 插入**。

---

## 4. 抽样：12 条源图裁片（独立自裁，不读实现者裁片）

从 `source_pdf/wz7.pdf` 按 fix JSON `cell` 8× 自裁，结果：

| 页/pos/字 | 源图角形 | 方向/判定 | v38 位置 |
|---|---|---|---|
| p86 pos20 」 | L（左竖+底横） | 闭 | 插入在「休。」与「有」之间（另 taskU 一→「 已还原） |
| p119 pos38 「 | ⌐（顶横+右竖） | 开 | 插入在「却」与「難」之间 |
| p166 pos40 」 | L | 闭（reclass） | 正确 |
| p362 pos33 」 | L | 闭 | 正确 |
| p391 pos21 「 | ⌐ | 开 | 正确 |
| p552 pos18 」 | L | 闭（reclass） | 正确 |
| p607 pos33 」 | L | 闭（reclass） | 正确 |
| p866 pos6 」 | L | 闭（reclass；QSF 伴随） | 源位「！﹂一」，v38 为「！﹂一」 |
| p928 pos26 」 | L | 闭（reclass；QSF 伴随） | 源位「。」+﹂+一，v38「。﹂一」 |
| p1034 pos42 」 | L | 闭（reclass） | 纯插入「。﹂西」 |
| p1118 pos11 」 | L | 闭 | 插入在「。」与「又」之间（源 cell 与产物 y 差约 1 步，文本顺序对） |
| p1590 pos13 」 | L | 闭 | 正确 |

12/12 为角形，无长横破折号；方向（开/闭）与 target 一致。另对全部 72 条做 v38 页文本「OCR+target@pos」核对：
**72/72 命中**（p86 的 1 条需容忍同列 taskU 的 一→「 内部转换；p866/p928 的 QSF 伴随见 §5）。

---

## 5. 双引号 / QSF「闭合不补」

- 全书文本：`「「`/`」」` = 0；`﹁﹁` 7=7；**`﹂﹂` 240→239（未新增）**；72 个插入列内无连续重复引号（0）。
- QSF 决策记录 925 条与 v37 **逐条相同**（append 696/replace 229；pair_skip 32、pos_skip 24 不变）→
  「闭合不补」规则未被破坏；stat 仅 cand/bar 各 +1。
- 文本效果只有 **2 页**：p866（插入「一」，原本 QSF 一→﹂ 的替换被抑制）、p928（插入「﹂」，列尾 ﹂→一 恢复）；
  **p1034 是纯插入**。两页新文本与源图（引号+一）一致，属修正非回归。
- **t34 报告 §2 的「4 页 QSF」与 p1034「REPL ﹂西」不准确（R2）**；报告 §3 未写 B +11（R3），
  11 条新 B 页均含本批 quote item（feat.corner=true），是行级 pair_balance 对行中闭引号的假阳性。

---

## 6. 判据 / 回归 / token / 纪律

- `verify_vert.py` = HEAD（`git diff` 空），判据未放宽；build_vert.py 未改（t32 版本）。
- wz6 `vert.tex` 逐字节相同 + verify PASS（页数 231=231 / 整页丢失 0 / 越界 0+0）。
- pytest 590 passed。
- token：完整 token（40 字符）及前 12 字符在报告/fix JSON/tmp_vert/battle8/build38.sh/api 工具中 **0 命中**；
  api 工具只读 `/tmp/paddle_token`。
- 审查期间仓库源文件写入仅 `docs/battle8b_review.md`；未改实现代码、未 commit（HEAD `9207b2c`）。

---

## 7. 残留（不阻塞交付）

1. **R1**：build38 字节级 md5 非可复现（重建 `6b958794…`/t35 `cd385f26…` vs 交付 `6f5b1c64…`；text/bbox/metadata/size 全同，差异为 PDF /ID）。
2. **R2**：t34 报告 §2 QSF 页数/页名不准（实际 2 页：p866/p928；p1034 纯插入）。
3. **R3**：t34 报告 §3 未披露 B +11 及「行级 pair_balance 假阳性」解释。
4. **R4**：t35 报告称 quote 条目有 `strip` 证据字段，实际无（crop/cell/feat 齐；不影响证据有效性）。
5. **R5**：11 条 t24 既有 missing_char 无证据字段（非本轮 72 条）。
6. 建议下一轮文档整理时把 R2/R3 修入 `docs/battle8_quotes.md`，并把 p1241/p1399/p1337（battle7）/p866/p928/p1034/p1118 加入固定抽样清单。

---

## 8. 结论

- **产品侧通过**：72 条引号（70 」+2 「；43 条 —— 重判）逐条与 punct_list/keep 对应、每条有源图角形证据；
  v38 md5/verify/字符量（+72）符合 t34/t35 记录；无双引号；QSF 决策 925 条不变；wz6 零回归；pytest 590；判据未改、token 未泄。
- **交付判定：pass**（v38 可交付、可作 battle8b 基线）；t34 报告的两处口径（R2/R3）与 t35 的 strip 表述（R4）为
  低级别文档修正项，不影响产品与基线；修文档后可直接沿用本报告数字。
