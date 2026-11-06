# battle10b 独立验收（t48 · v41 引号落库）

> 验收人：验证评审员（独立验证方）　日期：2026-11-06 21:21–21:36
> 基线：HEAD `3fe7f4e`（未 commit 工作树）；**未改实现代码、未改 fix JSON、未 commit/push**
> 对象：t47（battle10b：11 条引号复核 + p563 省略号 → v41）
> 主产物：`output/wz7_full/wz7_full_v41.pdf`（md5 `17ec4bb1eb55f1ab382637dfd5d0c3fa`，1748 页）
> 方法：自己重跑 build41、自己用 fitz 量产物/文本层、自己从 `source_pdf` 8×/10×/12× 裁源图（不采信实现者裁片）、自己重跑 punct_audit 与 wz6/pytest。

---

## 0. 结论

**PASS（可交付）**。v41 在 v40 基础上只加 **7 条引号**（`」` p126/p806/p1178 pos10/p1178 pos22/p551/p818 + `「` p1231）；p563/p1171 点线、8/6/3 圈码均未落文本；门禁全过。

> **t52 复审补记（2026-11-06 22:15）**：t49 复审认定未落的 3 条（p1178 pos38/39、p1291）**应落**（角形为闭引号 ﹂，t47 的自动分类器误判为开角）；p1322 仍不落（U 形）。t52 已在 fix JSON 补 3 条并重建 **v42**（`f964ad71…`，931,200 = v41 +3）—— 本报告的 **PASS 结论对 v41 成立，但当前交付基线应改为 v42**；详见 §8。

**核心数字**：
- 复跑 build41 → `BUILD_EXIT=0/FIXTEXIT=0`；重跑 md5 `da3e7efc5610eb225c7e80d8c58f58dc` ≠ 报告 `17ec4bb1…`（/ID），但 **size 109,997,031 相同、metadata 相同、1748 页文本/行 bbox 逐页 0 差异** → 内容等价；已恢复交付物 `17ec4bb1…`。
- verify_vert（--expect-low）**PASS**：1748=1748 / **931,197**（v40 931,190 + 7）/ 差异>80 字页 **18（预期 18/非预期 0）** / 整页丢失 **0** / 越界 span **0** + 矢量 **0**。
- v40→v41 文本 diff **6 页 +7**（p126/p551/p806/p818/p1231 各 +1，p1178 +2），无其它页变化。
- **11 条引号自裁 13 张**（11 条 + p716/p1568 附带）：7 条落库全部为**闭 ﹂/开 ﹁ 角形**且插入位置列内计数 v40=0/1→v41=+1、上下文正确；4 条未落（p1178 pos38/39、p1291、p1322）源图为**开角/不完整角**，与 API 的 `」` 类型不符，不落正确。
- **无双引号**：全文 `「「`/`」」` 均 0；`﹁﹁` 7、`﹂﹂` 239 与 v40 相同（未增）；7 个插入列内无重复引号。
- **p563/p1171**：源图确认是**目录 leader 点线**（点线下方页脚 五八九/一六七/一九五/二三五/二四七/二五九），文本层无 `……`、fix JSON 无条目 → 不落一致。
- **——/—/8/6/3**：t47 前后 fix JSON diff = **恰好 +7 条 `」`/`「`、0 删除、无其它条目**；本批无 ——/—/8/6/3 文本条目（唯一 `——` 是 battle9 p57 破折号组，t42 已验收，非本批）；ring 页 1693/1696/1729 条目未变（class=ring，非文本数字）。
- **punct_audit**：pair_balance **1993→1990（−3）**；pair_split 495=495、line_start 2582=2582、dash_lead 1=1（均不增）；逐页：p126/p806/p1178/p1231 各 −1（插入的闭引号解掉同上下文未配对开引号），**p551/p818 各 +1**（插入的 ﹂ 与更早开引号跨列/跨页配对，stack depth 18/16 → 行级 pair_balance 的 unmatched_close 假阳性），净 −3。
- wz6 `vert.tex` **ae9d2f5259e12cff19e680b2a771b37d** 逐字节 + verify PASS；pytest **590 passed**；判据未改；无 token 字面。

**残留（不阻塞）**：
- **R1**：build41 非字节可复现（`da3e7efc…` vs `17ec4bb1…`），size/metadata/文本/bbox 全同 → 内容等价（/ID），与此前 v37–v40 现象一致。
- **R2**：p551/p818 的 pair_balance +1 是**行级口径假阳性**（源图 ﹂ 真实、与更早开引号跨列配对，stack depth 18/16）；净 pair_balance 仍下降 3，pair_split/line_start/dash_lead 不变。
- **R3**：未落的 4 条（p1178 pos38/39、p1291、p1322）本轮按「类型不符」不落；**t52 复审更正**：p1178 pos38/39、p1291 实为闭引号角（自动分类器误判），已补落 v42；p1322（U 形）仍不落。
- **R4**：p716（源图「下」）、p1568（cell 仅撇点）在 t45 已判误判/不确定，本轮未落库，复核一致。

---

## 1. PASS/FAIL 总表（6 项）

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 独立复跑 build41 → v41；md5 一致（否则 text/bbox 等价证据）；verify exit 0（1748 / 丢失 0 / 越界 0+0 / 字符量 = v40+Σlen(ch)） | **PASS（附 R1）** | BUILD/FIX exit 0；重跑 md5 `da3e7efc…` ≠ `17ec4bb1…`，size 109,997,031 同、metadata 同、1748 页文本/bbox 逐页 0 差异 → 内容等价；恢复交付物后 verify **PASS**：1748=1748 / 931,197（931,190+7）/ 18 预期 / 丢失 0 / 越界 0+0 |
| 2 | 11 条引号独立复核：自裁 ≥10 条源图（角形判据），核对插入位置/文本层、无双引号；p563（若落库）与 p1171×5（若未落）结论一致 | **PASS** | 自裁 13 条（11 条 + p716/p1568，8×/10×/12×）：7 条落库均角形正确、列内计数 0/1→+1、上下文对（`人物。﹂西門慶道`/`說罷。﹂西門慶道`/`寒冷些。﹂須臾`/`叫小厮們來。﹂原來`/`接你娘去。﹂因`/`甚麼嘴兒？﹂陳經濟`/`︹金字經︺﹁夜迢迢`）；4 条未落为开角/不完整角；全局 `「「`/`」」`=0、`﹁﹁`7、`﹂﹂`239 未增，7 列无重复；p563/p1171 源图为目录点线、文本无 `……`、fix JSON 无条目 |
| 3 | 确认 ——/—/8/6/3 均未以文本字符落库（fix JSON 无对应条目） | **PASS（附说明）** | t47 前后 fix JSON diff = **+7 条 `」`/`「`，0 删除**；本批无 ——/—/8/6/3 条目；唯一 `——` 是 battle9 p57（t42 已验收的 dash 组，非本批）；p1693/p1696/p1729 仅有既有 class=ring 圈码条目（未变、非文本数字） |
| 4 | punct_audit 前后：pair_split/line_start/dash_lead 不增；pair_balance 变动逐页解释 | **PASS** | pair_balance **1993→1990（−3）**；pair_split 495=495、line_start 2582=2582、dash_lead 1=1；逐页 p126/p806/p1178/p1231 **−1**（解掉未配对开引号）、p551/p818 **+1**（跨列/跨页配对，stack depth 18/16 的行级假阳性）；新增 2 条 unmatched_close、移除 4 条（3 unmatched_open + 1 unmatched_close） |
| 5 | wz6 + verify PASS；pytest ≥590；判据未改；token 未入库 | **PASS** | wz6 `vert.tex` `ae9d2f52…` 逐字节 + verify PASS（231=231 / 68,412÷70,373=97.2% / 2 预期 / 0 / 0+0）；pytest **590 passed**（19.21s）；`git diff src/test/verify_vert.py` 空、sha256=HEAD `cc8b6937…`；无 token 字面 |
| 6 | 报告 docs/battle10b_acceptance.md：PASS/FAIL + 字节绑定 + 抽样表 + 残留；不改实现代码、不 commit | **PASS** | 本文件；未改 `src/`、`data/`、fix JSON、`output/`（v41 已恢复原字节）；未 commit（HEAD `3fe7f4e`） |

---

## 2. 字节绑定（开工 21:21 = 收尾 21:36）

| 文件 | 开工 | 收尾 | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `9b8f87e21712a425f6a946b2427d3265a9196fafabb32331af9759ceae40c263` | 同左 | 一致（未改） |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致（=HEAD，判据未改） |
| `docs/vert_taskF_missed_fix.json` | `fb2799e9bffac74fc8ab0d3b5b472bdc939e0f8fd966464a664245fd237aec61` | 同左 | 一致（v41 数据，mtime 21:07） |
| `docs/battle10_quotes.md` | `18083133ad9539f02dc0101cf71ab61504266dbd99c1425fb396bc0da29a82ad` | 同左 | 一致 |
| `tmp_vert/battle10/quotes/build41.sh` | `82fe3656ec3dda4653bd45824594b7fc2c63cc9d2f384c4071e29bab36664a7d` | 同左 | 一致 |
| `output/wz7_full/wz7_full_v41.pdf` | md5 `17ec4bb1…` | md5 `17ec4bb1…` | 已恢复原交付字节 |

---

## 3. 复跑与 v41 门禁

- `bash tmp_vert/battle10/quotes/build41.sh`（`SOURCE_DATE_EPOCH=0`）：`开始 21:22` → `BUILD_EXIT=0` → `FIXTEXIT=0`（21:31:59）→ 重跑 md5 **`da3e7efc5610eb225c7e80d8c58f58dc`**。
- 与交付物 `17ec4bb1…` 对比：size **109,997,031 = 109,997,031**；metadata 完全相同（creator `TeX output 1970.01.01:0000`）；**1748 页文本逐页 0 差异、行 bbox/字号 0 差异**（全文 text md5 `b364fb80740c7fb9772ea5556c5d0246` 相同）→ 内容等价（R1，/ID）。
- 已把 `output/wz7_full/wz7_full_v41.pdf` 恢复为 **`17ec4bb1eb55f1ab382637dfd5d0c3fa`**。
- verify_vert（`--expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"`）：**exit 0 / PASS**：
  1748=1748；931,197÷942,935=**98.8%**；差异>80 字页 **18（预期 18/非预期 0）**；整页丢失 **0**；越界 span **0** + 矢量 **0**。
- 字符量对账：v40 **931,190** → v41 **931,197**（+7 = 7 条引号各 1 字）。

---

## 4. 11 条引号独立复核（自裁 13 张源图）

| # | 页 | pos | API ch | 我自裁源图（8×/10×/12×） | 判定 | 落库 | 与报告一致 |
|---|---|---|---|---|---|---|---|
| 1 | p126 | 15 | 」 | 闭 ﹂（左竖+底横） | 真漏 | ✅ | ✓ |
| 2 | p806 | 10 | 」 | 闭 ﹂ | 真漏 | ✅ | ✓ |
| 3 | p1178 | 10 | 」 | 闭 ﹂ | 真漏 | ✅ | ✓ |
| 4 | p1178 | 22 | 」 | 闭 ﹂ | 真漏 | ✅ | ✓ |
| 5 | p551 | 21 | ——→」 | 闭 ﹂（源为引号角，非破折号） | 重判为引号 | ✅ | ✓ |
| 6 | p818 | 23 | ——→」 | 闭 ﹂ | 重判为引号 | ✅ | ✓ |
| 7 | p1231 | 6 | 「 | 开 ﹁（角形在 `夜` 上一格，宽图 `「夜迢迢`） | 真漏 | ✅ | ✓ |
| 8 | p1178 | 38 | 」 | 开 ﹁（右竖+顶横），与 `」` 类型不符 | 类型不符 | ❌ | ✓ |
| 9 | p1178 | 39 | 」 | 角形不完整（顶横+左竖） | 不确定 | ❌ | ✓ |
| 10 | p1291 | 31 | 」 | 开 ﹁ + 既有 `「` 语境 | 类型不符/疑重复 | ❌ | ✓ |
| 11 | p1322 | 4 | 」 | 开角（U/﹁ 形），非闭 ﹂ | 类型不符 | ❌ | ✓ |
| 附 | p716 | 41 | 」 | cell 内是「下」字，无角形 | 误判 | ❌ | ✓（t45 已判） |
| 附 | p1568 | 10 | 」 | cell 仅撇点/空白 | 不确定 | ❌ | ✓（t45 已判） |

**插入位置与文本层（列内计数，v40→v41）**：

| 页 | ch | 列内计数 | v41 上下文 |
|---|---|---|---|
| p126 | 」 | 1→2 | `…這一表人物。﹂西門慶道：﹁便是先妻…` |
| p806 | 」 | 1→2 | `…你替他說說罷。﹂西門慶道：﹁如今齊香兒…` |
| p1178 pos10 | 」 | 0→1 | `…今日天氣寒冷些。﹂須臾，左右火池…` |
| p1178 pos22 | 」 | 0→1 | `…何太監道：﹁叫小厮們來。﹂原來家中教了…` |
| p551 | 」 | 0→1 | `…接你娘去。﹂因把手中吃的那蓋木樨芝麻…` |
| p818 | 」 | 0→1 | `…拌的甚麼嘴兒？﹂陳經濟出來，看見二人。` |
| p1231 | 「 | 0→1 | `﹂︹金字經︺﹁夜迢迢，孤另另…` |

**无双引号**：v40→v41 全文 `「「`=0、`」」`=0、`﹁﹁`=7、`﹂﹂`=239（均未增）；7 个插入列内无 `﹂﹂`/`﹁﹁`。
**diff**：v40→v41 仅 6 页 +7（p126/p551/p806/p818/p1231 各 +1，p1178 +2），无其它页变化。

裁片：`/tmp/acceptance12/crops/p{page}_pos{pos}_{ch}_12x.png`（11 张）+ `/tmp/acceptance12/quotes_cells_10x.png` / `quotes_ctx_6x.png` + `p1231_wide_12x.png`。

---

## 5. p563 / p1171 点线（不落库，结论一致）

- p563：自裁宽窗为**一条长竖点线**（列内等距圆点），下方是页脚 五八九；p1171：5 条点线，下方页脚 一六七/一九五/二三五/二四七/二五九 —— **目录 leader 点线**，不是省略号。
- v41 p563/p1171 文本层无 `……`、无 `..`；fix JSON 无 p563/p1171 条目 → **6 条 `……` 全不落，结论与 t47 一致**。
- 裁片：`/tmp/acceptance12/p563_dots_wide.png`、`p1171_dots_wide.png`。

---

## 6. ——/—/8/6/3 未以文本字符落库

- t47 前后 fix JSON diff（与 t42 备份对比）：**+7 条，全部是 `」`×6 + `「`×1；0 删除；无其它新增条目**。
- 本批 27 条中无 ——/—/8/6/3 文本条目；fix JSON 唯一 `——` 条目是 **battle9 p57**（t42 已验收的「两条 — 成组 + dash rule 画一条竖线」，非本批文本标点）。
- p1693/p1696/p1729 在 fix JSON 中只有**既有 `class=ring` 圈码条目**（t47 前后未变），不是本轮新增文本数字；`8/6/3` 未以文本数字落库（与 t47 登记「归 ring/census」一致）。
- p1729/p1693/p1696 的 ring 条目仍由既有 ring 机制渲染，非本批产物变化（v40→v41 文本 diff 只 6 页 +7，不含这些页）。

---

## 7. punct_audit 前后对比（自跑）

| 指标 | v40 | v41 | Δ |
|---|---|---|---|
| pair_balance | 1993 | **1990** | **−3** |
| pair_split | 495 | 495 | 0 |
| line_start | 2582 | 2582 | 0 |
| dash_lead | 1 | 1 | 0 |

**逐页解释**（pair_balance item diff）：
- **−1**：p126（移除 unmatched_open `﹁`）、p806（移除 unmatched_open `﹁`）、p1178（移除 unmatched_open `﹁`）、p1231（移除 unmatched_close `﹂`）——插入的引号使原本行级未配对的引号配对成功。
- **+1**：p551、p818（新增 unmatched_close `﹂`）——插入的闭引号与**更早的未闭合开引号**跨列/跨页配对（全书阅读序 stack 深度 **18 / 16**）；行级 pair_balance 看不到更早的开引号，故记一条 unmatched_close，属**假阳性**，源图 ﹂ 角形已自裁确认。
- 无新增 pair_split/line_start/dash_lead；净 pair_balance **下降 3**。

---

## 8. 回归 / 判据 / token

- **wz6**：`/tmp/vert_wz6_b10_verify/vert.tex` md5 **`ae9d2f5259e12cff19e680b2a771b37d`**（逐字节同基线）；verify **PASS**（231=231 / 68,412÷70,373=97.2% / 差异 2 预期 / 丢失 0 / 越界 0+0）。
- **pytest**：**590 passed**（840 warnings，19.21s）。
- **判据**：`git diff src/test/verify_vert.py` 空；sha256 = HEAD `cc8b6937…`；`build_vert.py` 未改。
- **token**：报告/fix JSON/`tmp_vert/battle10/` 无 token 字面（仅「token 未入库」说明文字）。
- **/mnt/d**：未写；**未 commit**（HEAD `3fe7f4e`）。

---

## 9. 复现命令

```bash
cd /opt/test
# 1) 复跑 v41（SOURCE_DATE_EPOCH=0；会覆盖 output v41，md5 因 /ID 变化）
bash tmp_vert/battle10/quotes/build41.sh
# 2) 门禁
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v41.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
# 3) punct_audit 前后
/usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v40.pdf --mode v \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --src-pdf source_pdf/wz7.pdf \
  --json /tmp/acceptance12/audit_v40.json
/usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v41.pdf --mode v \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --src-pdf source_pdf/wz7.pdf \
  --json /tmp/acceptance12/audit_v41.json
# 4) 引号源图裁片（12×，只读 source_pdf；cell 取自 punct27.json / fix JSON）
python3 - <<'EOF'
import json, fitz
p=json.load(open('tmp_vert/battle10/punct27.json'))
src=fitz.open('source_pdf/wz7.pdf')
for q in p:
    if q.get('ch') in ('」','「'):
        c=q['cell']
        pm=src[q['page']-1].get_pixmap(matrix=fitz.Matrix(12,12),clip=fitz.Rect(c[0]-4,c[1]-4,c[2]+4,c[3]+4),colorspace=fitz.csGRAY)
        pm.save('/tmp/q_%d_%d.png'%(q['page'],q['pos']))
EOF
# 5) wz6 / pytest
VERT_TMP=/tmp/vert_wz6_b10_verify /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b10_verify.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b10_verify/vert.tex
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_vert.py /tmp/wz6_b10_verify.pdf \
  data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json --src-pdf source_pdf/wz6.pdf
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

---

## 10. 纪律

- 只新增 `docs/battle10b_acceptance.md`；未改 `src/`、`data/`、`docs/vert_taskF_missed_fix.json`、`output/`（v41 已恢复原字节）；未重建交付物（复跑后恢复）；未 commit/push。
- 日志：`/tmp/acceptance12/logs/`（build41、v41_verify、audit_v40/v41、wz6_build/verify、pytest）；裁片：`/tmp/acceptance12/crops/`。

---

## 11. 结论

**t47 通过（可交付）**：
1. v41 只加 7 条引号（p126/p806/p1178×2/p551/p818/p1231），自裁 13 条源图全部复核：7 条落库角形/位置正确、4 条未落（开角/不完整）正确；无重复引号；字符量 931,190→**931,197**。
2. p563/p1171 目录点线不落、8/6/3 圈码不落文本，fix JSON 只 +7 条引号（0 删除），与报告一致。
3. punct_audit：pair_balance **−3**、pair_split/line_start/dash_lead 不变；p551/p818 的 +1 已用 stack depth 18/16 解释为行级假阳性。
4. 门禁：v41 verify PASS（1748 / 931,197 / 18 预期 / 丢失 0 / 越界 0+0）；wz6 `ae9d2f52…` + PASS；pytest 590；判据未改；无 token；未 commit。


---

## 8. t52 复审补记（v42）

> t49 复审（review-round）对 §4 的 4 条未落条目重新裁图判定：**p1178 pos38、p1178 pos39、p1291 三条角形为闭引号 ﹂，应落**；p1322 为 U 形，仍不落。t52 据此补落并重建 v42。

| 项 | v41（本报告原验收） | v42（t52 补落） |
|---|---|---|
| 落库条数 | 7 | **10**（+ p1178 pos38/39、p1291） |
| fix JSON missing_char | 157 | **160** |
| md5 | 17ec4bb1… | **f964ad7133841025c2d415c40f52af89** |
| 字符量 | 931,197 | **931,200**（+3） |
| v→next diff | — | **2 页 +3**（p1178 +2、p1291 +1；两条同在 p1178，故非 3 页） |
| verify_vert | PASS | **PASS**（1748=1748 / 931,200 / 18 预期 / 丢失 0 / 越界 0+0） |
| punct_audit | 1993→1990 | 1990→**1987（−3）**；pair_split 495、line_start 2582、dash_lead 1 均不变 |
| QSF | 925（696/229） | **925（696/229）不变** |
| 无双引号 | `「「`/`」」` 0、`﹂﹂` 239 | 同（239 未增） |
| wz6 / pytest | ae9d2f52… / 590 | **同** |

**「11 条」集合定义（避免两报告口径混淆）**：
- **t47 的 11 行** = 8 条真漏 `」`（p126/p806/p1178 pos10/p1178 pos22/p1178 pos38/p1178 pos39/p1291/p1322）+ 1 条 `「`（p1231）+ p551/p818 两条由 `——` 重判的 `」`；其中 p1322 未落。
- **t45 的 11 条** = 10 条 `」`（含 p716/p1568，不含 p551/p818）+ 1 条 `「`。
- 两处「11」不是同一集合；t52 后实际落库 = 10 条（8 真漏 + 1 「 + 2 重判 − p1322 未落 = 10）。
