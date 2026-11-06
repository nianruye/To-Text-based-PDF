# battle8b 独立验收报告（t35 · 引号类漏识 → v38）

> 验收人：验证评审员（独立验证方，t35）　时间：2026-11-06 01:30–02:05
> 基线：HEAD `9207b2c` + 未提交工作树；**未 commit / 未 push**；本报告为本轮唯一新增文件
> 验收对象（t34）：`docs/vert_taskF_missed_fix.json`（72 条引号落库）、`docs/battle8_quotes.md`、
> `output/wz7_full/wz7_full_v38.pdf`（md5 `6f5b1c6407649181f13ae252e0915a7f`）、`tmp_vert/battle8/` 证据。
> 原则：不采信自述——自己复跑 build38/verify_vert/wz6/pytest/punct_audit，自己从 source_pdf 8× 裁图读引号，自己核对 QSF 决策。

---

## 0. 验收结论（先行）

**结论：PASS（可交付用户）**，但须带两条**报告口径修正**（不阻塞产品）：
① 报告 §2 的「4 页 QSF 侧伴随变化」不准确——QSF **决策记录 925 条与 v37 逐字节相同**（`qsf.json` 925 items 0 差异），
   **文本效果层面实际只有 2 页**（p866 插入一、p928 REPL ﹂→一；p1034 是纯插入），且这两页的新文本与源图（引号+一）一致，属修正而非回归；
② 报告未披露 **B 类 6→17（+11）**：新增 11 条 B 全部是本批插入的**行中闭引号**，源图 11/11 有角形墨迹；
   punct_audit 的 pair_balance 按「行/列」级配对并假设闭引号在行末，故把这 11 条判成 B——**B 增是审计口径假阳性，不是产品缺陷**。

**核心数字**：72 条落库（70 `」` + 2 `「`；其中 43 条由 `——` 重判）；v38 verify PASS（1748=1748 / 931,178 字 / 差异 18 预期 / 整页丢失 0 / 越界 0+0）；
字符量 v37 931,106 → v38 **931,178（+72）**；无双引号（规范文本 `「「/」」/﹁﹁` 0、`﹂﹂` 240→239，72 个插入列无重复引号）；
wz6 `ae9d2f52…` + verify PASS；pytest 590；判据未改；token 未入库。

**残留（不阻塞）**：
- **R1**：build38 非字节可复现——重跑 md5 `cd385f26…` ≠ 报告 `6f5b1c64…`；但**大小相同（109,996,764 B）、metadata 相同（1970-01-01 固定）、1748 页文本/bbox 逐页 0 差异**，内容等价（疑 PDF /ID，与 t33 的 v37 现象一致）。
- **R2**：报告 §2 的 QSF 页面数/页面名不准（见 ①）。
- **R3**：报告未写 B 类变化（见 ②）；建议补一句「pair_balance 行级口径对本批行中引号会 +1，实际以源墨为准」。
- **R4**：11 条 t24 既有 missing_char 无证据字段（非本轮 72 条，t29 R4 已知）。

---

## 1. PASS/FAIL 总表（6 项）

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 独立复跑 build38 + verify_vert：md5 与报告一致（否则 text/bbox 等价证据）、exit 0、1748 页、丢失 0、越界 0+0、字符量与落库条数对账 | **PASS（附 R1）** | build38：BUILD/FIX exit 0；重跑 md5 `cd385f26…` ≠ 报告 `6f5b1c64…`，但 size/metadata/1748 页文本/bbox 全同 → 内容等价；恢复交付物 `6f5b1c64…` 后 verify **PASS**（1748=1748 / 931,178÷942,935=98.8% / 差异>80 字页 18 预期 / 丢失 0 / 越界 span 0+矢量 0）。字符量 v37 +72，67 页：62 页 +1、p362/p925/p1178/p1500/p1588 各 +2，与 72 条一致 |
| 2 | 逐条核对落库清单（page/pos/ch/源图证据）；自裁 ≥12 条源图确「引号形」；v38 文本层该位置为该引号且无双引号 | **PASS** | 72 条字段 page/col/pos/ch/source/confidence/ratio/exp_len/text/api/crop/cell/feat/verdict 全齐、与 keep 清单一一对应、0 冲突、证据文件 0 缺失；**自裁 19 条**源图 cells（11 个 B 页 + p86/p866/p928/p1034/p119/p391/p345/p664）**全部为角形（L/⌐）**；72/72 在 v38 对应列插入成功；72/72 列无重复引号，全局 `「「/」」/﹁﹁` 0、`﹂﹂` 240→239 |
| 3 | 46 处「——」重判核对：抽 ≥10 自查源图「不是破折号」；确认无 —— 进入落库 | **PASS** | 43 条 `——`→`」` 与 keep/ fix 的 reclass-close **43/43 一一对应**；**自裁 13 条 reclass 源图全部为角形（短横+竖臂）**，无长横破折号；3 条 `——`（p814/p1006/p1180）no-corner 明确不插；fix JSON 中 **ch=—— 0 条** |
| 4 | punct_audit 前后：引号配对违规数（尤其 B）不增、最好下降；给出数字 | **PASS（附 R3 解释）** | 独立重跑：pair_balance **2001→1995（−6）**；pair_split 495=495、line_start 2582=2582、dash_lead 1=1；B **6→17（+11）**、O 359→348、K_weak 960→951、K 3→4、C_fixed 721→723。**63 页变动：34 页变好、29 页变差**（p362 +2、其余 +1）；新增 32 条 pair_balance item：K_weak 16 / B 11 / C_fixed 2 / O 1 / K 1 / A 1；**11 条新 B 均为插入的行中闭引号，源图 11/11 有角墨**；全 70 个插入闭引号在全书阅读序中均 `depth>0`（前面有未闭合开引号）→ 跨行/跨列/跨页合法配对，行级 pair_balance +1 是审计口径假阳性（见 §6） |
| 5 | wz6 `ae9d2f52…` + verify PASS；pytest ≥590；判据未改；token 未入库 | **PASS** | wz6 重跑 `vert.tex` = `ae9d2f5259e12cff19e680b2a771b37d` + verify PASS（231=231 / 97.2% / 2 预期 / 0 / 0+0）；pytest **590 passed**（18.06s）；`git diff src/test/verify_vert.py` 空、sha256 = HEAD；token 字面 0 命中 |
| 6 | 报告 docs/battle8b_acceptance.md 含 PASS/FAIL 总表 + 字节绑定 + 抽样表 + 残留风险；不改实现代码、不 commit | **PASS** | 本文件；未改 src/ 与 fix json；output v38 已恢复原字节 `6f5b1c64…`；未 commit（HEAD `9207b2c`） |

---

## 2. 字节绑定（开工 = 收尾）

| 文件 | 开工（01:30） | 收尾（写报告后 01:48） | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `9b8f87e21712a425f6a946b2427d3265a9196fafabb32331af9759ceae40c263` | 同左 | 一致 |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致（=HEAD） |
| `docs/vert_taskF_missed_fix.json` | `f4e4f7f2e9c03a9d15f2292d6306861eb7b75cacd43ad6253c60f7e75c70106c` | 同左 | 一致 |
| `docs/battle8_quotes.md` | `48a7b6d38cd91464ec45a3caef1be5e40420bf690e76abb2261ed236e659f389` | 同左 | 一致 |
| `tmp_vert/battle8/build38.sh` | `60d66701d0414f93db27431775ae6dfb08cc016d557121736767276d7402f7ef` | 同左 | 一致 |

> build_vert.py mtime 00:49（t32）；fix json 01:17、报告 01:29（t34）；本轮 build38 只读 fix json，未改实现文件。

---

## 3. build38 重跑与 v38 验证

- `bash tmp_vert/battle8/build38.sh`（`SOURCE_DATE_EPOCH=0`/`FORCE_SOURCE_DATE=1`）→ `BUILD_EXIT=0`/`FIXTEXIT=0`；重跑 md5 **`cd385f2624bc8edf628a42fd64216708`**。
- 与交付物 `6f5b1c64…` 对比：**size 109,996,764 = 109,996,764**；metadata 完全相同（creator `TeX output 1970.01.01:0000`、creationDate `D:19700101000000-00'00'`）；**1748 页文本逐页 0 差异、逐页行 bbox/字号 0 差异**；全文 text md5 `0571e02b5a67093ff214dd973241b7bf` 相同 → **内容等价**，md5 差异来自 PDF 内部 /ID（R1）。
- 已把 `output/wz7_full/wz7_full_v38.pdf` 恢复为原交付字节 **`6f5b1c6407649181f13ae252e0915a7f`**。
- 交付 v38 verify_vert（带 --expect-low）：**PASS**：1748=1748；931,178÷942,935=98.8%；差异>80 字页 **18（预期 18/非预期 0）**；整页丢失 **0**；越界 span **0** + 矢量 **0**；exit 0。

---

## 4. 72 条落库核对

- `missing_char` 总数 141 = 69（battle7 及以前）+ **72（本轮 api_strip_quote）**；新条目 ch 计数 **70 `」` + 2 `「`**，无 `——`。
- 字段：page/col/pos/ch/side/source/confidence/ratio/exp_len/text/api/crop/cell/feat/verdict **全齐**；`feat.corner` 72/72 true；
  crop/cell/strip 证据路径 **0 缺失**；无同 pos 异字/同字异 pos 冲突。
- 与 `keep.json` 72 条一一对应（page/pos/ch）；skip 24 条 = no-corner 12 / other 9 / target-at-pos 2 / dup-existing 1（p592）。
- v37→v38 逐页 diff：67 页 +72（62 页 +1、p362/p925/p1178/p1500/p1588 各 +2）；**65/67 页为纯插入且插入字=目标引号**（`」`→`﹂`、`「`→`﹁`）；
  2 页有 QSF 侧伴随变化（见 §7），但字符量仍 +72（p866 +1、p928 +1）。
- 无双引号：规范文本 `「「`/`」」`/`﹁﹁` 全 0；`﹂﹂` 240→239（未新增）；**72 个插入列均无重复引号**。

**自裁源图抽样（19 条，8×，从 source_pdf 按 cell 裁）**：

| 页 | ch | 形态（我读） | 页 | ch | 形态 | 页 | ch | 形态 |
|---|---|---|---|---|---|---|---|---|
| p166 | 」 | L 角（闭） | p362 | 」 | L 角 | p428 | 」 | L 角 |
| p552 | 」 | L 角 | p607 | 」 | L 角 | p1090 | 」 | L 角 |
| p1355 | 」 | L 角 | p1444 | 」 | L 角 | p1588 | 」 | L 角 |
| p1590 | 」 | L 角 | p1610 | 」 | L 角 | p86 | 」 | L 角 |
| p866 | 」 | L 角（引号+一） | p928 | 」 | L 角 | p1034 | 」 | L 角 |
| p119 | 「 | ⌐ 角（开） | p391 | 「 | ⌐ 角（开） | p345 | 」 | L 角 |
| p664 | 」 | L 角 | — | — | — | — | — | — |

→ **19/19 为引号角形，无破折号形、无误插入。**

---

## 5. 46 处「——」重判核对

- keep 中 43 条 `——` 与 fix 中 43 条 `verdict=reclass-close` **page/pos 集合完全一致**；3 条 `——`（p814/p1006/p1180）标 no-corner 不插；fix 中 **无任何 ch=——**。
- 自裁源图（含 p166/p552/p607/p1355/p1444/p1588/p1610/p86/p866/p928/p1034/p345/p664）**13/13 为角形**（短横+竖臂，L 形），不是长横破折号；
  若按破折号插入会让 t34 dash rule 在引号位置画长竖线——本批确认未发生。
- 结论：46 条 `——` 无一条按破折号落库；43 条按角形重判为 `」`，3 条明确不插。

---

## 6. pair_balance / B 类解释（重要口径）

独立重跑 punct_audit（v37 与 v38 原交付物，同一命令）：

| 指标 | v37 | v38 | Δ |
|---|---|---|---|
| pair_balance（总） | 2001 | **1995** | **−6** |
| pair_split / line_start / dash_lead | 495 / 2582 / 1 | 495 / 2582 / 1 | 0 |
| **B** | **6** | **17** | **+11** |
| O | 359 | 348 | −11 |
| K_weak / K / K_invalid | 960 / 3 / 30 | 951 / 4 / 30 | −9 / +1 / 0 |
| C_fixed | 182 | 184 | +2 |

- **63 页变动：34 页变好、29 页变差**（p362 +2，其余各 +1）。
- 新增 32 条 pair_balance item 分类：K_weak 16 / **B 11** / C_fixed 2 / O 1（p119 插入开引号）/ K 1（p345）/ A 1（p996）；
  删除 36 条：K_weak 25 / O 10 / A 1（插入后与开引号配对而不计）。
- **11 条新 B 的核对**：全部是**行中插入的闭引号**，逐条核对其所在列与源图 cell：**11/11 有角形墨迹**（见 §4 抽样）；
  punct_audit 的 B 判据是「闭符只在产物行（OCR 行无）且源图**最后一格**无闭引号墨条」——插入的引号在行中（不在行末），
  源图最后一格自然无墨 → 被判 B。**这是审计行级口径的假阳性，不是产品缺陷**。
- **29 个变差页解释**：全 70 个插入闭引号在**全书阅读序**（页序 + 列 x 降序 + 列内自上而下）中，插入点前均存在未闭合开引号
  （stack depth>0，depth 分布 1/2/3/…/33 均有）→ 与更早的「/﹁ 跨行、跨列或跨页配对；pair_balance 按行/列统计，
  会把「开」和「闭」各记 1 条（而不是 0），故 +1。**没有一例是插错列/错位置**（源图 19 条自裁 + feat.corner 72/72）。
- 因此：**pair_balance（以及其 B 子类）不是本批的验收判据**；本批以①逐条源墨证据、②无双引号、③QSF 决策记录不变、
  ④verify/wz6/pytest 门禁为准。pair_balance 仅作参考（净 −6，变差页均可解释为跨行/页配对）。

---

## 7. QSF 侧核对（报告口径修正）

- **决策记录**：比较 v37 与 v38 两次构建的 `/tmp/wz7_v37_run/qsf.json` 与 `/tmp/wz7_v38_run/qsf.json`：
  **925 条 items 完全一致（0 差异）**；`replace=229`、`append=696` 相同。报告「QSF 925 条 append/replace 与 v37 完全相同」**在决策记录层成立**。
  stat 仅 `cand 2874→2875`、`bar 654→655`（多一个候选被归类 bar），未产生新 item。
- **文本效果**：v37→v38 除 65 页纯插入外，**只有 2 页**有伴随变化：
  - p866：插入 `」`（渲染 ﹂）后，源书同一位置的 OCR「一」不再被 QSF 一→﹂ 替换 → 文本为 `！﹂一`；源图裁片 = `！﹂一`（**修正 v37 丢一**）。
  - p928：插入 `」` 后，列尾原本 QSF 替换的 `﹂` 回到「一」→ 文本 `…我知道。﹂一`；源图列尾为 `﹂`+短横（与「一」一致）。
  - **p1034 是纯插入**（v37 `…了他。西` → v38 `…了他。﹂西`），不是报告所说的「REPL ﹂西」。
- **报告 §2 的「4 页有 QSF 侧伴随变化」不准确**：实际 2 页（p866/p928），无第 4 页；p1034 为纯插入。
  两页的新文本均与源图一致（引号+一），**不是回归**；建议报告改为「QSF 决策记录 925 条不变；2 页因插入改变配对状态、伴随恢复源书『一』」。

---

## 8. 回归 / 判据 / token

- **wz6**：`/tmp/vert_wz6_b8_verify/vert.tex` = `ae9d2f5259e12cff19e680b2a771b37d`；verify PASS（231=231 / 68,412÷70,373=97.2% / 差异 2 预期 / 丢失 0 / 越界 0+0）。
- **pytest**：590 passed（840 warnings，18.06s）。
- **判据**：`git diff src/test/verify_vert.py` 空；sha256 = HEAD `cc8b6937…`。
- **token**：报告/fix json/tmp_vert/battle8 无 token 字面（仅「token 未入库」说明文字）；API 工具只读 `/tmp/paddle_token`。

---

## 9. 纪律

- 本轮只新增 `docs/battle8b_acceptance.md`；未改 `src/`、`data/`、fix json；build38 只写 output 与 /tmp，output v38 已恢复原字节。
- `git status`：fix json / build_vert.py / battle6-8 报告与 api 工具为既有未提交项；**未 commit**（HEAD `9207b2c`）。
- 未改实现代码、未 commit/push。

---

## 10. 复现命令

```bash
cd /opt/test
# 1) 重跑（会覆盖 output v38；md5 因 /ID 变化）
bash tmp_vert/battle8/build38.sh
# 2) verify（交付 v38）
EL=$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v38.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$EL"
# 3) punct_audit v37/v38 + classify
/usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v38.pdf --mode v \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --src-pdf source_pdf/wz7.pdf \
  --json /tmp/v38.audit.json
/usr/bin/python3 src/tools/punct_classify.py --audit /tmp/v38.audit.json --pdf output/wz7_full/wz7_full_v38.pdf \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --mode v \
  --coords data/wz7_full/wz7_full_spotting_coords.json --src-pdf source_pdf/wz7.pdf \
  --out /tmp/v38.classified.json
# 4) QSF 决策记录对比
python3 - <<'EOF'
import json
a=json.load(open('/tmp/wz7_v37_run/qsf.json')); b=json.load(open('/tmp/wz7_v38_run/qsf.json'))
print('items equal',a['items']==b['items'],'stat',a['stat'],b['stat'])
EOF
# 5) wz6 / pytest
VERT_TMP=/tmp/vert_wz6_b8_verify /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b8_verify.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b8_verify/vert.tex
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

---

## 11. 结论

- **t34 通过（可交付）**：72 条引号落库（70 `」`+2 `「`；43 条 `——` 重判）逐条有源图角墨证据（自裁 19/19）；无双引号；
  v38 门禁 PASS、字符量 +72 逐页可解释；46 条 `——` 无一作破折号；wz6 零回归、pytest 590、判据未改、token 未入库；
  QSF 决策记录 925 条与 v37 完全相同。
- **判定：PASS**；须修正报告两处口径（R2/R3）：QSF 文本效果页数（2 不是 4、p1034 非 REPL）、B 类 +11 的解释
  （行中插入引号导致行级 pair_balance/B 假阳性；pair_balance 不是本批判据）。R1（md5 非字节复现，内容等价）与 R4 为低级别。
