# battle3 独立验收报告（第二轮 · t17）

> 验收人：验证评审员（独立验证方，t17）　时间：2026-11-05 00:10–00:32
> 基线：HEAD `20d327e` + 未提交工作树；**未 commit / 未 push**；本报告为本轮交付（t14 报告的修订版），不新增其它仓库文件
> 验收对象（t16 修订后）：`src/tools/punct_audit.py`（非正文过滤器收紧）、`src/tools/punct_classify.py`（p1365 末行行盒）、
> `src/test/unit/test_punct_classify.py`（+12 例 F1/F2 回归）、`docs/battle3_qsf_report.md`（v2）；产品侧 `src/pipelines/build_vert.py`
> 与产物 `output/wz7_full/wz7_full_v31.pdf` **本轮未动**（哈希 / md5 已核对）。
> 原则：不采信自述——自己重跑 audit/classify/verify/build，自己开产物/源图，自己复算。

---

## 0. 验收结论（先行）

**结论：PASS（第二轮）。** t14 的 F1–F4 均已按要求修订并**独立复验通过**：
非正文过滤器收紧后 wz4/wz1 全部正文页恢复审计（wz4 B=6 恢复、默认五书 B=33 可复现）、p1365 改判 C_fixed（wz7 B=5）、
五书口径统一为默认 **33** / `--include-nonbody` **38**；p82/p915 误伤已披露并恢复正文。产品侧（QSF/p620/verify/wz6）与字节绑定保持通过。

**低级别残留（不阻塞）**：
- **R1**：`docs/battle3_qsf_report.md` §0 表第 18 行仍写「wz7 B=6 / 剩余 6 条」——与同报告 §0 摘要、§3 表、§6（B=5）及本次实测（5）不一致，属漏改一行（低）。
- **R2**：F2 的回归单测 `TestMarkRowPick::test_misread_yi_tail_not_fallback` 用「无关上一行」样例，未复现 p1365 的「前缀行 vs 末行」冲突；用 t14 旧逻辑（模拟）跑这 6 例仍全绿——F2 修复本身已由行为复验（p1365→C_fixed）证明，但该测试的防回归效力偏弱（低）。
- **R3**：v31 产物的 provenance 已在 t14 证明为「渲染等价」（当前 build_vert 重建的 PDF 逐页文本/bbox 0 差异），本轮未重复全量重建（低，继承 t14 结论）。

---

## 1. PASS/FAIL 总表（8 项验收）

| # | 验收项 | 结论 | 实测（本轮） |
|---|---|---|---|
| 1 | 独立复跑 punct_audit + 分类：B ≤10 且与报告一致；抽样 ≥10 条 B 剩余项 | **PASS**（R1 文档一格漏改） | wz7 默认 B=**5**（p888/p1247×3/p1382）、include B=**10**；五书默认 **33** / include **38**；A 3528 / C 175 / C_fixed 722 / O 360 / K 3/962/30 与报告一致；抽样 13 条（5 wz7 + 8 横排）根因逐条核对 |
| 2 | p620 `！」` 后 `﹂` 补回（产物文本 + 源图墨迹双证）；同类 ≥10 处 | **PASS** | p620 col9 = `你撇的人有上稍來沒下稍！﹂`；源图裁片 22.4×11.2pt（图 `/tmp/acceptance5/p620_3way.png`）；`！/？` 126 处：render_fixed **121/121** 验证有关闭引号、product_missing **5/5** 验证无 = 96.0% |
| 3 | wz7 verify_vert PASS（1748=1748 / 整页丢失 0 / 越界 0+0），字符量逐页可解释 | **PASS** | 1748=1748；931,008/942,935=98.7%；差异>80 字页 18（预期 18/非预期 0）；整页丢失 0；越界 span 0+矢量 0；exit 0。字符量 +254/211 页与 `tmp_vert/battle3/char_diff.json` 逐页一致（t14 已验，本轮产物未变） |
| 4 | wz6 `vert.tex` `ae9d2f52…` 逐字节不变 + verify PASS | **PASS** | 本轮重跑：`/tmp/wz6_b3_r2/vert.tex` = `ae9d2f5259e12cff19e680b2a771b37d`；verify PASS（231=231 / 68,412÷70,373=97.2% / 差异 2 预期 / 丢失 0 / 越界 0+0） |
| 5 | pytest ≥562；分类器仓库可复现；新单测红→绿 | **PASS**（R2 测试弱） | **590 passed**（18.79s）；改名 `tmp_vert/battle2` 后 v31 audit+classify 正常且 JSON md5 与之前**完全相同**（audit `0427f7b7…` / classified `2b4bb02f…`）；F1 旧过滤器模拟 → `TestNonbodyFilter` **3 failed**（红），新实现 28/28 绿；F2 见 R2 |
| 6 | 纪律：产品代码仅 build_vert.py + 新工具/测试；无无关改动；不 commit | **PASS** | 00:00 后改动仅 `punct_audit.py`、`punct_classify.py`、`test_punct_classify.py`、`battle3_qsf_report.md`（+本报告）；`build_vert.py` 哈希仍 `7214fe0d…`；v31 md5 仍 `b062381b…`；HEAD `20d327e` 未 commit |
| 7 | 实现文件开工/收尾 SHA-256 一致并写入报告 | **PASS** | 开工 00:10 与收尾（写完本报告后）三文件哈希一致，见 §2 |
| 8 | 本报告含 PASS/FAIL 表、原始输出、抽样明细、遗留风险、明确结论 | **PASS** | 本文件 |

---

## 2. 字节绑定（实现文件 SHA-256）

| 文件 | 开工（00:10） | 收尾（写报告后 00:18） | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `7214fe0dfa7be5cc0a844ea47b3f3d4d5e62ce59b3878e64480978d973a8313d` | 同左 | **一致（绑定成立）** |
| `src/tools/punct_classify.py` | `2e01d194a760eb0ac11d4f58e3426beb5922a1f3063f1ef86266703012101da7` | 同左 | **一致（绑定成立）** |
| `src/tools/punct_audit.py` | `ab038dcc7144e66e61bba6434261e62b70cd44327f78f017e0fa973d6fb5443b` | 同左 | **一致（绑定成立）** |

> 收尾哈希在写完本报告后记录（任务书允许），若与开工不一致将按 FAIL 报告变化前后值。
> 产品侧 `build_vert.py` 与 t14 相同（`7214fe0d…`），v31 产物 md5 `b062381b4649acbd1ea849a17fbf52d3` 未变。

---

## 3. t14 四项 findings 的关闭验证

### 3.1 F1（blocker）非正文过滤器收紧 —— 已关闭

**代码**：`punct_audit._is_nonbody_page(lines, mode)` —— 仅 `mode='v'` 启用；**≥3 个不同关键词**（`NONBODY_KW` 12 词）；
整页文本 ≤300 字且 ≤12 行。横排 `--mode h` 直接返回 False；`--include-nonbody` 关闭过滤器。

**函数级实测（v31 产物页）**：

| 页 | 字数 | 行数 | 不同关键词 | `_is_nonbody_page` | 期望 |
|---|---|---|---|---|---|
| wz7 p82（註文） | 183 | 8 | 1（出版） | **False** | 正文（t14 误伤） |
| wz7 p554（版權頁） | 136 | 8 | 7 | **True** | 版權頁 |
| wz7 p915（经文） | 777 | 18 | 1（印刷） | **False** | 正文（t14 误伤） |
| wz7 p1163（版權頁） | 170 | 4 | 8 | **True** | 版權頁 |
| wz4 p138 / p190（横排） | — | — | — | **False**（mode h） | 正文 |

**审计级实测（默认口径）**：

| 书 | 审计页数 | 跳过页 | B | A | O | K 3/weak/invalid |
|---|---|---|---|---|---|---|
| wz7 | **1746**/1748 | **仅 p554/p1163** | **5** | 3528 | 360 | 3/962/30 |
| wz1 | **222**/222 | 无 | 1 | 58 | 21 | 0/16/2 |
| wz3 | **850**/850 | 无 | 20 | 798 | 895 | 0/307/32 |
| wz4 | **677**/677 | 无 | **6** | 144 | 278 | 0/155/4 |
| mgfdmg | **407**/407 | 无 | 1 | 38 | 38 | 0/9/5 |
| **合计** | — | — | **33** | — | — | — |

`--include-nonbody`：wz7 1748 页、B=**10**（+p554 3 +p1163 2），五书合计 **38** —— 与报告 §3/§6.2 一致。

**红→绿**：把 `_is_nonbody_page` 还原为 t14 旧判据（关键词出现次数 ≥3、无 distinct/页型）后跑 `test_punct_classify.py`
→ `TestNonbodyFilter` **3 failed**（`test_body_page_with_publish_words` / `test_wz7_p82_p915_body_pages` / `test_many_lines_not_skipped`）；
新实现 28/28 通过。**F1 关闭。**

### 3.2 F2（medium）p1365 假 B —— 已关闭（测试偏弱，R2）

- 新 `punct_classify._pick_mark_row`：后缀候选 = 原样 / 剥句末标点 / 剥误读 `一0〇` / 两者同剥，取最长命中，全不中回退最相似行。
- 复跑 wz7 默认分类：p1365 已为 **C_fixed**，`why=源图最后一格有宽扁横条 (17.3, 8.3)，OCR 漏、渲染端补`；B 由 6→**5**，C_fixed 721→**722**。
- 旧逻辑（模拟：后缀只剥句末标点）在 p1365 实况（`row9=與其病後能求藥，` / `row10=不若病前能自防。一`）返回 **row9**（错），新逻辑返回 **row10**（对）。
- **R2**：`TestMarkRowPick` 的「not_fallback」样例用 `'上一行文字'`（与产品列完全不像），旧逻辑的回退仍会选对 row1，故该测试对旧逻辑**不红**；建议改用 p1365 真行对（前缀行 + 末行）作样例。

### 3.3 F3（medium）五书口径 —— 已关闭

报告删除旧的「34」，改为两套可复现数字：**默认 33** / `--include-nonbody` **38**；
本轮独立复跑逐书 B：wz7 5/10、wz1 1、wz3 20、wz4 6、mgfdmg 1 → 33 / 38，与报告 §0/§3/§6.2 一致。
**R1**：§0 表第 18 行仍留「B=6 / 剩余 6 条」的旧值（同报告正文均已是 5），属漏改一格。

### 3.4 F4（low）p82/p915 披露 —— 已关闭

报告 §8 已新增「旧版过滤器误伤披露」；本轮实测 p82/p915 回到正文（`_is_nonbody_page`=False）；
A 3525→**3528**（p915 的 3 条 line_start）、O 356→**360**（p82/p915 的 4 条 pair_balance），与报告 §8 一致。

---

## 4. 产品侧核心声明复核（v31 未重建，哈希/md5 已核对）

| 项 | 实测 |
|---|---|
| v31 md5 / 页数 | `b062381b4649acbd1ea849a17fbf52d3` / 1748 |
| p620 | col9 `你撇的人有上稍來沒下稍！﹂`；源图 `﹂` 22.4×11.2pt（裁片）；同页 `李﹂瓶`→`李瓶` 已消失 |
| `！/？` 126 处 | render_fixed 121/121 验证有闭引号、product_missing 5/5 验证无（96.0%） |
| 双 `﹂﹂` / `西﹂門` / `：﹂` | p760/p1100/p1499 = 0；p922 = 0；p230/343/359/630 的列内 `：﹂` 已回源书（`但見：` + 下一列 `﹂：`） |
| wz7 verify | PASS：1748=1748 / 931,008 / 差异 18 预期 / 丢失 0 / 越界 0+0 |
| 字符量 | v30 930,754 → v31 931,008（+254），211 页，与 `char_diff.json` 逐页一致 |
| wz6 | 本轮重跑 `vert.tex` = `ae9d2f52…`；verify PASS（231=231 / 97.2% / 2 预期 / 0 / 0+0） |
| pytest | **590 passed** |

---

## 5. 抽样明细（13 条剩余 B / 已修项）

| # | 书/页 | 检查 | 结论 |
|---|---|---|---|
| 1 | wz7 p888 | pair_balance `﹂` | 曲牌行 OCR `」「雁兒落帶得勝令`，产物列 `﹂﹁雁兒落…﹂﹁我則見…` → 真 B（报告 #1） |
| 2 | wz7 p1247 idx9 | pair_balance `﹂` | OCR row10 首 `」（）…`；产物把 `」` 移到 col9 尾 → 归位权衡（报告 #2） |
| 3 | wz7 p1247 idx10 | pair_balance `﹂` | 产物 col10 尾 `俊英﹂！`（OCR 无 `﹂`）→ 多补（报告 #3） |
| 4 | wz7 p1247 idx13 | pair_balance `﹂` | OCR row14 首 `」〔〕…`；`」` 归位到 col13 尾（报告 #4） |
| 5 | wz7 p1382 | line_start `：` | 产物列首 `：證一賢妻…`；OCR row4 `一賢妻…` → 归位边界（报告 #5） |
| 6 | wz1 p222 | dash_split `—` | 产物行尾 `…貢獻—` / 下行首 `—《…`；OCR 行内 `——` 相邻 → 横排断行 |
| 7-10 | wz3 p25/p68/p95/p112 | line_start `，；。` | 产物行首标点，源 OCR 行中 → 横排断行 |
| 11-12 | wz4 p138/p190 | line_start `。` | 产物 `。3⃝…`，OCR `…’”。3…` → 横排断行 |
| 13 | mgfdmg p325 | pair_balance `’` | 英文 `People’s` 撇号被当引号配对（审计噪声） |

p1365 已不在 B（C_fixed，见 §3.2）。

---

## 6. 纪律与范围

- 00:00 后仓库改动：`src/tools/punct_audit.py`、`src/tools/punct_classify.py`、`src/test/unit/test_punct_classify.py`、
  `docs/battle3_qsf_report.md`（t16），`docs/battle3_acceptance.md`（本报告）；**无其它产品代码**。
- `build_vert.py` 哈希 `7214fe0d…`（与 t14 相同）；v31 md5 `b062381b…`（未重建）；HEAD `20d327e`（未 commit）。
- 本任务未改实现代码；所有中间产物只在 `/tmp/acceptance6/`；`tmp_vert/battle2` 改名测试后已恢复。

---

## 7. 复现命令

```bash
cd /opt/test
A=/tmp/acceptance6/audit; L=/tmp/acceptance6/logs
# wz7 默认 / include
/usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v31.pdf --mode v \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --src-pdf source_pdf/wz7.pdf \
  --json $A/wz7_default.audit.json --label wz7-default
/usr/bin/python3 src/tools/punct_classify.py --audit $A/wz7_default.audit.json \
  --pdf output/wz7_full/wz7_full_v31.pdf --lines data/wz7_full/wz7_full_spotting_lines_patched.json --mode v \
  --coords data/wz7_full/wz7_full_spotting_coords.json --src-pdf source_pdf/wz7.pdf \
  --out $A/wz7_default.classified.json --label wz7-default
# include 口径：audit 加 --include-nonbody，其余同
# 横排四书：audit --mode h（无 --include-nonbody 也全页）+ classify --mode h
# 测试 / 回归
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q     # 590 passed
EL=$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v31.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$EL"
VERT_TMP=/tmp/wz6_b3_r2 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_v31_r2.pdf source_pdf/wz6.pdf
md5sum /tmp/wz6_b3_r2/vert.tex          # ae9d2f52…
```

---

## 8. 结论

- **t14 的 F1–F4 全部关闭**：非正文过滤器按「仅竖排 + 多关键词 + 页型特征」收紧，wz4 265 页与 wz1 30 页全部恢复审计（wz4 B=6 恢复、默认五书 B=33）；p1365 改判 C_fixed（B=5）；五书口径统一且可复现（默认 33 / include 38）；p82/p915 误伤披露。
- **产品侧**：p620、`！/？` 96.0%、双 `﹂﹂`/`西﹂門`/`：﹂` 修复、wz7 verify PASS、字符量 +254/211 页、wz6 逐字节零回归、pytest 590 —— 均通过。
- **判定：PASS（第二轮）**，附带 R1（报告 §0 一格漏改 6→5）、R2（F2 回归测试样例偏弱）、R3（v31 provenance 继承 t14 结论）三项低级别残留，均不阻塞交付；建议 R1/R2 在下次文档/测试整理时顺手修。

> 本报告只写实测；未 commit / 未 push / 未改实现代码。
