# battle19b 独立验收（t89 · v49）

> 验收人：验证评审员（独立验证方）　日期：2026-11-08 12:10–12:30
> 基线：HEAD `84d6b95`（未 commit 工作树）；**未改实现代码、未改 fix JSON/数据、未 commit/push**
> 对象：t88（battle19b：融合候选落库 → v49）
> 主产物：`output/wz7_full/wz7_full_v49.pdf`（md5 `cef0bb5e8e412e08720435c4a5f328e6`，1748 页）
> 方法：自己重跑 build49、自己裁源图核对 15 条落库条目、逐条核对 12 条待人工/不处理候选、自己算字符量与双引号/空对、自己跑 wz6/pytest。

---

## 0. 结论

**PASS（可交付）**。v49 只落 **3 条 insert**（p308/p967/p1625，各 +1 字），其余 3 条「可落库」候选已由 v48 规则覆盖不重复落；字符量 931,181→**931,184（+3）**，逐页 diff 恰 3 页；门禁全过；4,339 条待人工 + 1,967 条异体字按设计不落。

**核心数字**：
- 复跑 build49 → md5 `25314b71c8944d16277ef83aca06bea0` ≠ 交付 `cef0bb5e…`（/ID），但 **size 109,995,110 相同、metadata 相同、1748 页文本/行 bbox/内容流逐页 0 差异** → 内容完全等价；已恢复交付物 `cef0bb5e…`。
- verify_vert（--expect-low）**PASS**：1748=1748 / **931,184** / 差异>80 字页 18（预期 18/非预期 0）/ 整页丢失 0 / 越界 span 0+矢量 0。
- build 日志：`[漏识元素] 灌入 531 处: dash 1 / ring① 352 / ring② 15 / missing_char 160 / insert 3 / replace 0 / 跳过 0`。
- **落库条目抽检 15 条**：
  - 3 条新 insert：自裁源图 p308 r4 / p967 r0 / p1625 r1 均为 **`﹁` 角形 + 独立「一」**；v49 文本 `正是：﹁一窪…` / `﹁一百萬…` / `正是。﹁一朝…` → **该落、位置正确（列首/pos 0）**；
  - 12 条既有 missing_char（p50 竊 / p85 峴 / p105 逕 / p141 謄 / p213 颳 / p231 人 / p247 不 / p276 人 / p319 前 / p329 刺 / p404 人 / p411 粧）：自裁源图 cell 均见对应字，落点正确；
  - **replace 类 0 条落库**（fix JSON 无 replace 项），无吞字/错位风险。
- **待人工/不处理抽检 12 条**（替换 3、补括号 2、括号类型 2、补闭号 2、补开号 1、推断 1、异体字另计）：理由均成立——替换为 A/B 字符差异（v/V、蓋/葢、于/了於，需源图仲裁）；补括号/括号类型为引用短语/非独立名（`一六一七`、`註一`、`「人的文學」`，不盲转）；补闭号/开号为 A 有 B 无（需源图）；推断闭号为启发式；「不处理」样本为异体字（為/爲、既/旣、厦/廈、繡/綉、別/别）。
- **字符量对账**：v48 931,181 → v49 931,184（**+3**）；逐页仅 p308 +1 / p967 +1 / p1625 +1，其余 1745 页 0 差 = insert 3×1 + replace 0 + 删除 0 ✓。
- **引号/空对**：`「「`/`」」`=0；`﹁﹁`=7、`﹂﹂`=237（与 v48 相同，未增）；全书空对残留 **0**。
- wz6 `vert.tex` **`ae9d2f5259e12cff19e680b2a771b37d`** + verify PASS（231=231 / 97.2% / 2 预期 / 丢失 0 / 越界 0+0）；pytest **616 passed**。

**残留/说明（不阻塞）**：
- **R1（低）**：报告称 wz6「531 项全跳过」不准确——531 项含 dash 1 + ring 367 + missing_char 160 + insert 3；小书守卫只整类跳过 missing_char/insert/replace，ring/dash 仍会尝试列匹配并打「未匹配 → 跳过」（实测 wz6 日志有 p50/p57 未匹配行）。wz6 `vert.tex` 逐字节不变、verify PASS，**零回归成立**，仅报告措辞需修正。
- **R2（说明）**：候选清单 `candidates.json` 的 `row/pos` 基于 **A 整书 OCR 行序**，与产物 `patched_lines` 行序不同；因此待人工候选的**逐条源图裁片**不能直接用产物行坐标（我尝试按产物行裁片出现错位）。本轮待人工核对采用「候选字段（current/suggested/note/tier）+ 产物上下文/同页文本」交叉验证（12 条），理由均成立；若需逐条源图复核，应在 A 行序坐标下裁片（下一轮可补）。
- **R3**：待人工 4,339 + 异体字 1,967 按设计未落；v49 只代表「自动可落库」档（6 条中 3 条落、3 条已覆盖），不是全书 OCR 差异全量修复。

---

## 1. PASS/FAIL 总表（5 项）

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 独立复跑 build49 → v49；verify exit 0（1748 / 丢失 0 / 越界 0+0）；wz6 `ae9d2f52…` + PASS；pytest ≥614 | **PASS（附 R1）** | build49 exit 0；重跑 md5 `25314b71…` ≠ `cef0bb5e…`，size/metadata/1748 页文本/bbox/内容流 0 差异 → 内容等价；verify **PASS**：1748=1748 / 931,184 / 18 预期 / 丢失 0 / 越界 0+0；wz6 `ae9d2f52…` + PASS；pytest **616 passed**（129.63s） |
| 2 | 独立抽检 ≥15 条落库条目：自裁源图核对（角形/括号/字符）、确认该落且落对位置；替换类核对吞字/错位 | **PASS** | 3 新 insert 源图均 `﹁`+「一」、v49 文本 `「一…` ✓（p308/p967/p1625，pos 0）；12 条 missing_char 源图 cell 均见对应字（竊/峴/逕/謄/颳/人/不/人/前/刺/人/粧）✓；replace 落库 0 条，无吞字/错位 |
| 3 | 抽检 ≥10 条「待人工/未落」候选，确认不落理由成立 | **PASS（附 R2）** | 12 条跨 6 类：替换 A/B 差异（v/V、蓋/葢、于/了於）、补括号引用（一六一七、註一）、括号类型引用短语（「人的文學」「福善禍淫」）、补闭号/开号 A 有 B 无、推断闭号启发式、不处理异体字（為/爲、既/旣、厦/廈 等）——不落/待人工理由均成立 |
| 4 | 字符量对账 v48→v49 = 插入 + 替换 + 删除；逐页 diff 与报告一致；无双引号/空括号新增 | **PASS** | +3（p308/p967/p1625 各 +1，其余 0）；insert 3 + replace 0 + 删除 0；`「「`/`」」`=0、`﹁﹁`=7、`﹂﹂`=237 与 v48 同；空对残留 0 |
| 5 | 报告 docs/battle19b_acceptance.md：PASS/FAIL + 字节绑定 + 抽样表 + 残留；不改实现代码、不 commit | **PASS** | 本文件；未改 `src/`、fix JSON/数据、`output/`（v49 已恢复原字节）；未 commit（HEAD `84d6b95`） |

---

## 2. 字节绑定（开工 12:10 = 收尾 12:30）

| 文件 | 开工 | 收尾 | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `47b8838d76ab06e099cda80a278864563ffcacb0392143bcc41c9dc1aa04066b` | 同左 | 一致（新增 insert/replace） |
| `tmp_vert/battle19/apply/build49.sh` | `8dd8a605d3470102d3b706e6237ca522e9c8232ad80abe7bf338d376e90c1b14` | 同左 | 一致 |
| `docs/battle19_apply.md` | `0fc8784bc0e540db1208299047675c48d759e2c124cb3134bdda31a8d3c67b1f` | 同左 | 一致 |
| `docs/battle19_dual_ocr.md` | `0f79fcb3744524aa3b205e9b18d2be37a93fb4b5068af573d11b981d66ccdb2c` | 同左 | 一致（t87 报告，未改） |
| `src/test/unit/test_missed_fix_insert_replace.py` | `b12462682ee387df7f624eaf09732fc5bd2307f6f31b0899ee1e086ac408a113` | 同左 | 一致（2 条） |
| `docs/vert_taskF_missed_fix.json` | `a5fbc4172846bd271af1d6818cd6d8f7bff29d58c8dcda3702dbb32585457d17` | 同左 | 一致（531 项） |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致（判据未改） |
| `output/wz7_full/wz7_full_v49.pdf` | md5 `cef0bb5e…` | md5 `cef0bb5e…` | 已恢复原交付字节 |

---

## 3. 复跑与门禁

- `bash tmp_vert/battle19/apply/build49.sh`：`BUILD_EXIT=0` → `FIXTEXIT=0`（12:20:47）→ 重跑 md5 **`25314b71c8944d16277ef83aca06bea0`**。
- 与交付物 `cef0bb5e…` 对比：size **109,995,110 = 109,995,110**；metadata 相同；**1748 页文本/行 bbox/内容流逐页 0 差异** → 内容完全等价（/ID）。
- 已恢复 `output/wz7_full/wz7_full_v49.pdf` 为 **`cef0bb5e8e412e08720435c4a5f328e6`**。
- verify_vert（`--expect-low`）：**exit 0 / PASS**：1748=1748；931,184÷942,935=98.8%；差异>80 字页 **18（预期 18/非预期 0）**；整页丢失 **0**；越界 span **0** + 矢量 **0**。
- 构建日志：`灌入 531 处: dash 1 / ring① 352 / ring② 15 / missing_char 160 / insert 3 / replace 0 / 跳过 0`。

---

## 4. 落库条目抽检（15 条，自裁源图）

### 4.1 新 insert 3 条

| 页/行 | 源图（自裁） | v49 文本 | 判定 |
|---|---|---|---|
| p308 r4 | `﹁` 角形 + 独立「一」+ 窪死水… | `正是：﹁一窪死水…` | ✓ 落对（insert「、保留一） |
| p967 r0 | `﹁` 角形 + 独立「一」+ 百萬軍中… | `﹁一百萬軍中…` | ✓ |
| p1625 r1 | `﹁` 角形 + 独立「一」+ 朝時運至… | `正是。﹁一朝時運至…` | ✓ |

### 4.2 既有 missing_char 12 条（源图 cell 自裁）

p50 竊 / p85 峴 / p105 逕 / p141 謄 / p213 颳 / p231 人 / p247 不 / p276 人 / p319 前 / p329 刺 / p404 人 / p411 粧 —— **12/12 源图 cell 均见对应字**，文本落点与 col/pos 一致（抽查列内计数 +1）。
> 说明：fix JSON 531 = dash 1 + ring 367 + missing_char 160 + insert 3；**replace 0**（无吞字/错位风险）。ring/dash 为既有机制，本轮未新增条目。

---

## 5. 待人工 / 未落候选抽检（12 条）

| # | 页/行/pos | 类型 | current→suggested | 不落理由（核对） |
|---|---|---|---|---|
| 1 | p5 r1 p4 | 替换 | `v`→`V` | A/B 大小写差异，需源图仲裁 ✓ |
| 2 | p5 r4 p30 | 替换 | `蓋`→`葢` | 异体字形，需源图/字形规范裁决 ✓ |
| 3 | p6 r0 p8 | 替换 | `于`→`了於` | 长度不同（1→2），自动替换会错位 ✓ |
| 4 | p29 r5 p125 | 补括号 | `一六一七`→`〔一六一七〕` | 年份/引用短语，非独立曲牌名（产物上下文 `（一六一七）`）✓ |
| 5 | p58 r1 p21 | 补括号 | `註一`→`〔註一〕` | 注释引用，非独立名列 ✓ |
| 6 | p30 r9 p341 | 括号类型 | `「人的文學」`→`〔人的文學〕` | 引用短语，转方括号会误改 ✓ |
| 7 | p30 r6 p248 | 括号类型 | `「福善禍淫」`→`〔福善禍淫〕` | 同上 ✓ |
| 8 | p30 r16 p597 | 补闭号 | `焉。毛慶`→`」` | A 有闭号/B 无，需源图 ✓ |
| 9 | p63 r5 p229 | 补闭号 | `」（註十`→`」` | A/B 不一致，需源图 ✓ |
| 10 | p66 r1 p4 | 补开号 | `「一金瓶`→`「` | A/B 开号差异，已有 `「` 可能重复 ✓ |
| 11 | p62 r16 p564 | 补开号 | `的一萬曆`→`「` | A 有/B 无，需源图 ✓ |
| 12 | p65 r7 p275 | 补闭号（推断） | `梅詞話）`→`」` | 启发式推断（开>闭），需源图核对 ✓ |
| — | p5/p6/p11/p12 | 不处理 | 為/爲、既/旣、厦/廈、繡/綉、別/别 | 异体字，不改 ✓ |

> 方法说明（R2）：`candidates.json` 的 row/pos 是 **A 整书 OCR 行序**，与产物 `patched_lines` 行序不同；直接按产物行裁片会错位（本轮已试）。故待人工核对采用「候选字段（current/suggested/note/tier）+ 产物同页上下文」交叉验证；12 条理由均成立。若需逐条源图复核，应按 A 行序坐标裁片（建议下一轮补）。

---

## 6. 字符量对账 / 引号 / 空对

- **v48 931,181 → v49 931,184（+3）**；逐页 **仅 p308 +1 / p967 +1 / p1625 +1**，其余 1745 页 0 差。
- 模型：insert 3×1 + replace 0 + 删除 0 = **+3** ✓（与报告 §5 完全一致）。
- `「「`/`」」` = **0/0**；`﹁﹁`=7、`﹂﹂`=237（与 v48 相同，未增）；全书 `〔〕/（）/︹︺/︵︶` 空对残留 **0**。

---

## 7. wz6 / pytest / 判据 / token

- **wz6**：`VERT_TMP=/tmp/vert_wz6_b19` 构建 → `BUILD_EXIT=0`；`vert.tex` md5 **`ae9d2f5259e12cff19e680b2a771b37d`**（逐字节同基线）；verify **PASS**（231=231 / 68,412÷70,373=97.2% / 2 预期 / 丢失 0 / 越界 0+0）。
  - 注（R1）：wz6 构建日志出现 `p50/p57 … 未匹配 -> 跳过` 的 ring/dash 尝试行；`vert.tex` 逐字节不变、verify PASS，零回归成立。报告「531 项全跳过」应改为「missing_char/insert/replace 整类跳过；ring/dash 尝试未匹配」。
- **pytest**：**616 passed**（900 warnings，129.63s）。
- **判据**：`git diff src/test/verify_vert.py` 空；sha256 = HEAD `cc8b6937…`。
- **token**：报告/构建脚本/测试无 token 字面；**未 commit**（HEAD `84d6b95`）。

---

## 8. 复现命令

```bash
cd /opt/test
bash tmp_vert/battle19/apply/build49.sh
md5sum output/wz7_full/wz7_full_v49.pdf          # cef0bb5e…
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v49.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
# 字符量/引号/空对
/usr/bin/python3 - <<'PY'
import fitz,re
a=fitz.open('output/wz7_full/wz7_full_v48.pdf'); b=fitz.open('output/wz7_full/wz7_full_v49.pdf')
def t(d,p): return re.sub(r'\s','',d[p-1].get_text())
print('delta', sum(len(t(b,i+1))-len(t(a,i+1)) for i in range(len(a))))
print('diff pages',[i+1 for i in range(len(a)) if t(a,i+1)!=t(b,i+1)])
PY
# 新 insert 源图（自裁）
/usr/bin/python3 - <<'PY'
import json,fitz
L=json.load(open('data/wz7_full/wz7_full_spotting_lines_patched.json'))
C=json.load(open('data/wz7_full/wz7_full_spotting_coords.json'))
src=fitz.open('source_pdf/wz7.pdf')
for p,r in [(308,4),(967,0),(1625,1)]:
    b=C[str(p-1)][r]; xs=[q[0]/2.0 for q in b]; ys=[q[1]/2.0 for q in b]
    pm=src[p-1].get_pixmap(matrix=fitz.Matrix(10,10),clip=fitz.Rect(min(xs)-2,min(ys)-2,max(xs)+2,min(ys)+120),colorspace=fitz.csGRAY)
    pm.save('/tmp/insert_p%d.png'%p)
PY
VERT_TMP=/tmp/vert_wz6_b19 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b19.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b19/vert.tex          # ae9d2f52…
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

---

## 9. 纪律

- 只新增 `docs/battle19b_acceptance.md`；未改 `src/`、fix JSON/数据、`output/`（v49 已恢复原字节）；未 commit/push。
- 日志：`/tmp/b19v/`（build49.log、v49_verify.log、wz6_build/verify.log、pytest.log）；自裁裁片：`/tmp/b19v/sheet_missing12.png`、`sheet_inserts.png`、`sheet_pending1/2.png`。

---

## 10. 结论

**t88 通过（可交付）**：3 条 insert 源图证据成立（`﹁`+「一」，插入且保留一）、位置正确；12 条既有 missing_char 与 12 条待人工/不处理候选理由成立；字符量 +3 逐页与报告一致；无双引号/空对新增；门禁 PASS、wz6 零回归、pytest 616、判据未改、未 commit。

**建议下一轮**：
1. 报告措辞修正 R1（wz6「531 项全跳过」→「missing_char/insert/replace 整类跳过；ring/dash 尝试未匹配」）；
2. 待人工 4,339 条按 A 行序坐标逐条裁源图复核（R2），优先替换 2,379 + 补闭号 1,060；
3. 候选「括号类型」121 条已确认多为引用短语，建议直接标「不处理」以减少待人工量。
