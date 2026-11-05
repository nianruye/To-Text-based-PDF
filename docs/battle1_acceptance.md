# battle1 独立验收报告（横排 local-bug 批次 + 竖排两位数圈码批次）

> 验收人：验证评审员（独立验证方，t3）
> 时间：2026-11-04　HEAD：`20d327e`（改动全部在工作树，**未 commit / 未 push**）
> 验收对象：t1 `docs/battle1_horizontal.md`、t2 `docs/battle1_vertical_ring.md`
> 原则：不轻信自述——所有门禁本报告作者**亲手重跑**，所有关键数字**自己复算**，产物**自己打开核对**。
> 本报告只写实测；未复现/未验证项单独列在 §10，不混入 PASS。

---

## 0. 验收结论（先行）

**可交用户验收（两批均达成本批目标）**，但必须随交付向用户披露 §9 的 6 项遗留风险，其中
**「圈内数字取自 OCR，抽样 2/12 与源图不符」**和**「p1704 行13 圈位偏高约 11.8pt」**直接影响用户观感，
建议在交付说明里点名，不要等用户自己发现。

一句话数字：测试 **562 passed**（≥516）｜横排四书+classic 五本 1:1、split 0、missing 0、pitch 全等于基线、
改前/改后 verify JSON **逐字节相同**｜wz7 **1748=1748 / 930,754 字（基线 930,670，+84）/ 整页丢失 0 /
越界 span 0 + 矢量 0 / 退出码 0**｜wz6 `vert.tex` md5 **ae9d2f52…**（逐字节相同）+ PASS｜审计 **168/20/1/3 = 基线**。

**没有发现需要打回的问题**；发现 2 处低级别文档/文件模式瑕疵（§7.4），不影响验收，但建议本轮顺手收口。

---

## 1. PASS/FAIL 总表（逐项 + 实测数字）

| # | 验收项 | 结论 | 实测数字（本报告作者重跑） |
|---|---|---|---|
| 1 | pytest 全绿 ≥516 | **PASS** | `562 passed, 836 warnings in 17.65s`，exit 0（原始输出 §2） |
| 2 | 横排四书 verify_geom：页数 1:1 / split 0 / missing 0 / pitch=基线 | **PASS**（wz3 退出码为历史 FAIL，见 §3.2） | wz1 222=222 / 97.8% / exit0；wz3 850=850 / 79.7% / **exit1=基线**（floor=79 复跑 exit0）；wz4 677=677 / 99.6% / exit0；mgfdmg 407=407 / 98.7% / exit0；四书 split 0、missing 0 |
| 3 | wz7 全书 verify_vert + 审计 | **PASS** | 1748=1748；字符量 **930,754**（基线 930,670，+84）；整页丢失 0；越界 span 0 + 矢量 0；差异>80 字页 18（预期 18/非预期 0）；exit **0**；审计 **168/20/1/3**（=基线） |
| 4 | wz6 回归：`vert.tex` md5 + verify_vert PASS | **PASS** | md5 **ae9d2f5259e12cff19e680b2a771b37d**（与基线逐字节相同）；231=231 / 97.2% / 整页丢失 0 / 越界 0+0 / exit **0** |
| 5 | 抽样复算 ≥3 项（圈码真伪 / #1#2 影响 / 新增抽查） | **PASS** | ① p1704/1705/1706 文本层 ㊾4+㊿3 / ㊿1+○５１1 / ○５１5+○５２10，源图逐格核对一致；② 改前/改后五书逐页文本 0 差异、行 bbox 0 差异、verify JSON md5 全等；③ 新增 331 条随机抽 **12 处，12/12 真圈码（误报 0）**，其中 **2/12（16.7%）圈内数字 OCR 误读**（与 t2 的 4/24≈16.7% 独立吻合；p1735r0 与 t2 点名重合） |
| 6 | 纪律审查（diff 范围 / 误改对方管线 / 调试残留 / spec） | **PASS（2 处低级别瑕疵）** | 20 个变化项全部落在两批任务范围内；`build_vert.py`/`verify_vert.py`/`verify_geom.py` 零改动；无调试残留；spec 已更新。瑕疵：竖排报告未进 `spec/README.md` 账本；`census_ring_digit.py` 丢了可执行位（§7.4） |
| 7 | 交付六件套逐项打勾 | **PASS** | md5 ✓（v30 PDF + wz6 tex；横排以 verify JSON md5 等价证明）/ 页数 ✓ / 字符量 ✓ / verify 退出码 ✓ / 另一本书回归 ✓ / 审计数字 ✓（§8） |
| 8 | `docs/battle1_acceptance.md` 含总表/原始输出/风险/结论 | **PASS** | 本文件 |

> 说明：判定「PASS」= 该验收项的实质要求满足；退出码例外、历史基线、不可验证项均在正文原样列出，不做美化。

---

## 2. 基线确认：pytest

命令（本报告作者重跑，日志 `/tmp/acceptance/pytest.log`）：

```bash
cd /opt/test
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

原始输出（尾部）：

```
562 passed, 836 warnings in 17.65s
EXIT=0
```

- 实测 **562 passed**，满足 ≥516；构成 = 基准 516 + t1 新增 41 + t2 新增 5（`test_census_ring_judge.py` 5 条）。
- 未出现 failed / error / skipped 影响计数的情况。

---

## 3. 横排四书复验（对象：t1 重建产物 `/tmp/battle1/after/*.pdf`）

### 3.1 门禁命令与结果

```bash
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  /tmp/battle1/after/<book>.pdf <coords> <lines> --src-pdf source_pdf/<src>.pdf
# wz1/wz4：wzN_spotting_*；wz3：wz3_linelevel_spotting_*；mgfdmg：mgfdmg_spotting_*，--src-pdf source_pdf/wz5.pdf
```

完整日志 `/tmp/acceptance/geom_verify.log`。汇总（原文摘录）：

| 书 | 页数 | split（溢成多页） | missing | pitch | 退出码 |
|---|---|---|---|---|---|
| wz1 | 222 = 222 ✓ | 0 | 0 | **97.8%**（基线 97.8） | **0 PASS** |
| wz3 | 850 = 850 ✓ | 0 | 0 | **79.7%**（基线 79.7） | **1 FAIL**[^wz3] |
| wz4 | 677 = 677 ✓ | 0 | 0 | **99.6%**（基线 99.6） | **0 PASS** |
| mgfdmg | 407 = 407 ✓ | 0 | 0 | **98.7%**（基线 98.7） | **0 PASS** |
| wz2（classic，附加） | 783 = 783 ✓ | 0 | 0 | 58.9%（classic 历史值） | 1 FAIL[^wz2] |

[^wz3]: wz3 在 85% 全局下限下退出码 1 是**历史固有**（HANDOFF §2 明写「79.7% 历史固有，不是回归；门槛就是它」）。
本报告作者复核：① pitch 79.7% 与基线**逐 0.1% 相同**；② 页数 1:1 / split 0 / missing 0 硬约束全过；
③ 同一产物用 `VERIFY_PITCH_FLOOR=79` 复跑 → **退出码 0 PASS**（实测，日志 §3.2）；
④ 改动前后 `verify_geom --json` **逐字节相同**（见 §3.3），证明与 t1 改动无关。**该 FAIL 不构成本批回归。**
[^wz2]: wz2 classic 的 58.9% 是 classic 管线自身历史值，不属「横排四书」门禁（四书是 geom）；此处只作共享层/第二条管线的回归证据（页数 1:1 / split 0 / missing 0 全过 + `test_cases.py` 21 PASS，见 §3.4）。

### 3.2 wz3 历史 FAIL 的复核（floor=79 复跑）

```bash
VERIFY_PITCH_FLOOR=79 /usr/bin/python3 src/test/verify_geom.py /tmp/battle1/after/wz3.pdf \
  data/wz3/wz3_linelevel_spotting_coords.json data/wz3/wz3_linelevel_spotting_lines.json \
  --src-pdf source_pdf/wz3.pdf
# -> pitch 误差 <3% : 79.7% (样本 799)；== 退出码 PASS ==；EXIT=0
```

### 3.3 「改动对产物零影响」的独立复核（这是 t1 的核心主张）

**(a) 改前/改后产物 diff**（本报告作者脚本 `/tmp/acceptance/cmp_before_after.py`，逐页 `get_text()` + 逐行 span bbox 保留 2 位小数）：

```
wz1          pages 222=222 | textdiff 0 [] | boxdiff 0 []
wz3          pages 850=850 | textdiff 0 [] | boxdiff 0 []
wz4          pages 677=677 | textdiff 0 [] | boxdiff 0 []
mgfdmg       pages 407=407 | textdiff 0 [] | boxdiff 0 []
wz2_classic  pages 783=783 | textdiff 0 [] | boxdiff 0 []
```

**(b) `verify_geom --json` 逐页指标 md5（改前 vs 改后）** —— 与 t1 报告列出的 5 个 md5 **逐个一致**，且 before/after `cmp` 全 IDENTICAL：

```
wz1          7883b25ca71578c3382b9b4b65d9c69a  IDENTICAL
wz3          7ca85fadb91b0a32e812c8e5ab8ea131  IDENTICAL
wz4          2d8bf97f0f0b246eac21d48927e1d4e1  IDENTICAL
mgfdmg       348a0e9abea61c2e0762ed11d70b9bd3  IDENTICAL
wz2_classic  31173ea47bce22cd883f2101bd39f97b  IDENTICAL
```

**(c) 用「当前工作树」重新构建 wz1（闭合产物来源）**：`fit_positional.py` 按 t1 报告 §7 的 env 重建
`/tmp/acceptance/rebuild/wz1.pdf` → 与 `/tmp/battle1/after/wz1.pdf` **逐页文本 0 差异 / 行 bbox 0 差异**，
verify_geom **PASS（97.8%，1:1，split 0，missing 0）**，JSON md5 同为 `7883b25c…`。
说明：`after/` 产物构建于 00:32–00:36，而 `fit_common.py` 的 try/finally 在 00:37:23 落盘（最后一个改动，只影响异常路径清理）；
本次重建用的是**最终工作树**，产物与 after 完全一致 → 产物来源与最终代码一致，且 try/finally 对输出零影响。

**(d) 收尾检查**：重建后 `/tmp/fitpos_*` 无残留（`ls -d /tmp/fitpos_*` 空）。

### 3.4 wz2 classic 功能断言（共享层第二管线回归）

```bash
/usr/bin/python3 src/test/test_cases.py /tmp/battle1/after/wz2_classic.pdf
# -> 21 PASS, 0 FAIL；EXIT=0
```

---

## 4. 竖排 wz7 全书复验

### 4.1 verify_vert（命令与 HANDOFF §3 一致，本报告作者重跑）

```bash
EL=$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_vert.py \
  output/wz7_full/wz7_full_v30.pdf \
  data/wz7_full/wz7_full_spotting_coords.json \
  data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$EL"
```

原始输出要点（全文 `/tmp/acceptance/wz7_verify_vert.log`）：

```
页数: 源 OCR 1748 页  |  输出 PDF 1748 页  |  ✓ 1:1
字符量: 输出 930754 / OCR 942935 = 98.7%
差异 > 80 字的页: 18 个（预期 18 / 非预期 0）；整页丢失(0 字)页: 0 个
越界: span 0 个 / 矢量图形 0 个（容忍 0.5pt；涉及 0 页）
逐页页幅(众数纸型页, 输出页 i vs 源页 i) 最大相对差 0.01%/0.00%  ✓ 相符
== 退出码 PASS ==
EXIT=0
```

- 字符量 **930,754 ≥ 基线 930,670**（+84），18 个预期差异页全部是 `--expect-low` 声明的影印/噪声页，非预期 0。
- 产物身份：`output/wz7_full/wz7_full_v30.pdf`，**1748 页**，md5 **b8bb2dc49103ee3a72405da194a92d7d**（本报告作者实测，与 t2 自述一致）。

### 4.2 字符量 +84 的独立复算（不依赖 t2 的 cmp 脚本）

本报告作者用 fitz 逐页取文本、去空白后计数：

```
v29 全书非空白字符 930,670
v30 全书非空白字符 930,754        (+84)
有变化的页 31 页，逐页差：
1687 -2  1689 -2  1692 -4  1701 -9  1702 -3  1703 -4  1704 -7  1705 -1
1706 +9  1707 +9  1708 +7  1709 +8  1710 +10 1711 +11 1712 +4  1713 +1
1714 +5  1715 +11 1720 +1  1724 +3  1727 +7  1728 +6  1729 +8  1730 +1
1731 +1  1734 -6  1735 +2  1736 +8  1737 +6  1739 +1  1740 +3
```

- 31 页、逐页数值与 t2 报告 §9.1 **逐页完全一致**；其余 1717 页字符量完全相同。
- 增减口径自洽（本报告按「HEAD 版清单 ↔ 本轮普查」逐条配对复算）：新增 167 处 =
  **40 个 ≤50 两位数（每处 −1 字）+ 3 个 ≤50 一位数（0）+ 124 个 >50（每处 +1 字）→ +84**；
  331 条清单 = 164 条 v29 已有位置 + 167 处新增；另有 21 处人工 ring 覆盖跳过（number 一致）。
- 也就是说：`v29` 的 930,670 正是基线；v30 的 930,754 = 基线 +84。**字符量不低于基线成立。**

### 4.3 版式审计（`vert_layout_audit.py`）

```bash
/usr/bin/python3 src/tools/vert_layout_audit.py --pdf output/wz7_full/wz7_full_v30.pdf
# 日志 /tmp/acceptance/vert_layout_audit_v30.log；耗时 156.3s，EXIT=0
```

```
审计页 1436 / 请求 1748；列 26044 / 段 140540；有源带页 1436；横排页跳过 16
列位异常列: 168（其中强错位 20）| 涉及页 106
列间重合: 1 处（页 1）| 源书自身重合 1 | 列内叠字: 3 处
页级整体偏移(|中位|>4pt): 0 页
列位偏差分布: p50 0.45 / p90 1.11 / p95 1.53 / p99 4.32 / max 60.91 pt
```

**对照基线**：HANDOFF §8 的审计基线即 **168/20/1/3** → 本轮 v30 与基线逐项相同（168 / 20 / 1 / 3），
说明圈码灌入没有引入新的列位错乱（数量级不变；168/20 是既有的竖排列位口径差，见 AGENTS #22/#23）。

---

## 5. wz6 回归（另一本书）

```bash
rm -rf /tmp/wz6
VERT_TMP=/tmp/wz6 /usr/bin/python3 src/pipelines/build_vert.py \
    data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json \
    /tmp/wz6.pdf source_pdf/wz6.pdf
md5sum /tmp/wz6/vert.tex
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_vert.py \
    /tmp/wz6.pdf data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json \
    --src-pdf source_pdf/wz6.pdf
```

原始输出（日志 `/tmp/acceptance/wz6_regression.log`）：

```
BUILD_EXIT=0
ae9d2f5259e12cff19e680b2a771b37d  /tmp/wz6/vert.tex        ← 与基线逐字节相同
8be57f91e3f3a7b03489872b271c9337  /tmp/wz6.pdf
页数: 源 OCR 231 页  |  输出 PDF 231 页  |  ✓ 1:1
字符量: 输出 68412 / OCR 70373 = 97.2%
差异 > 80 字的页: 2 个（预期 2 / 非预期 0）；整页丢失(0 字)页: 0 个
越界: span 0 个 / 矢量图形 0 个（容忍 0.5pt；涉及 0 页）
== 退出码 PASS ==   VERIFY_EXIT=0
```

- 符合「wz6 只有 231 页、368 条 wz7 翻页条目越界跳过」的预期；`vert.tex` 逐字节相同是最强零回归证据。

---

## 6. 抽样复算明细（≥3 项）

### 6.1 ① p1704 / p1705 / p1706 圈码：真检出 + 真渲染

**文本层实测**（本报告作者 `fitz get_text()` 全书扫描；脚本 `/tmp/acceptance/check_ring_pages.py`）：

| 页 | v29（改前） | v30（改后实测） | 与 t2 自述 |
|---|---|---|---|
| p1704 | 无圈码字符 | **㊾ U+32BE ×4 + ㊿ U+32BF ×3** | 一致（49 行5/8/10/13；50 行14/15/16） |
| p1705 | `○`×1（既有 ○51） | **㊿ ×1 + ○５１ ×1** | 一致（50 行0；51 行15） |
| p1706 | `○`×6 | **○５１ ×5 + ○５２ ×10**（`○`×15、`５`×15、`１`×5、`２`×10） | 一致（51 行1/2/4/5/6；52 行7-17 缺 11） |
| p1684 / p1685 | ⑪×2 ⑫×4 / ⑬×2 ⑭×2 | **完全相同**（v1 老正例未回退） | 一致 |

- 全书圈码字符统计：v29 203 个/33 页 → v30 246 个/37 页（**+43**）。
  这 +43 与「331 条清单 = 164 条 v29 已有位置 + **167 处新增**（另有 21 处人工条目覆盖跳过）」
  中「新增 ≤50 的 43 处（40 个两位数 + 3 个一位数）」**精确对应**；其余 124 处新增是 >50，
  走 `○+全角数字`，不计入圈码字符。该拆分由 HEAD 版清单与本轮普查逐条配对复算得到（`git show HEAD:docs/vert_taskF_missed_fix.json`）。
- 「丁巴特」乱码残留：v29/v30 全书均 **0 页**；p1704-1706 文本层也无该字符。

**视觉核对**（本报告作者自己裁图，`/tmp/acceptance/key_cells_3way.png`，900dpi 源图 | v29 | v30 三列）：
逐格看到源图是「圆环+49/50/51/52」，v29 是分开的普通数字/部分已圈，**v30 是圈码**；p1704 r5/r14、
p1705 r15、p1706 r1/r7 圈内数字与源图一致。**p1704 r13 的圈位明显高于源图**（t2 自述 11.8pt，视觉可辨，
属短列既有口径，见 §9-2）。

> 任务书写「p1705 的 51/52」；实测该页是 **50/51**，51/52 在 **p1706**（与 HANDOFF 原始记录一致）。

### 6.2 ② #1/#2 修复对产物的量化影响 = 0（并核清「本来就已修」）

- t1 的核心主张是「#1/#2 在 HEAD 已是修复态，本轮只更正文档/测试」。本报告作者的量化复验：
  五本书改前/改后**逐页文本 0 差异、行 bbox 0 差异、verify JSON 逐字节相同**（§3.3），
  即 **t1 对横排产物的影响 = 0 字符 / 0 行 / 0 页**（这正是预期，不是缺陷）。
- 直接调用函数复核当前实现（不经管线）：
  - classic `escape_latex('a%b','classic')` → `'a\\%b'`（= `a\%b`，**单反斜杠**）；`escape_latex('100%','classic')` → `'100\\%'`；
  - v13 `escape_tex('a\\b')` → `'a\\textbackslash{}b'`（**无 `\{\}` 二次转义**）；`escape_tex('a{}\\b')` → `'a\\{\\}\\textbackslash{}b'`（花括号只转义一次）。
- 语料普查复核（22 个 spotting lines 文件）：「已转义」形态 `\%` 全书仅 **1 处**（wz1 key 144，在 `$…$` 数学内，走 math 分支不触发），
  `\_` 仅 **2 处**（wz2 key 782，OCR 垃圾 JSON 元数据行）——与 t1 报告一致，说明 #11 分叉在真实正文无触发面。
- 人工核对一页真实产物：wz3 输出 p513（OCR key 512，含 `100% / 70% / 60% / 50% / 40%` 的表格）
  → 文本层 `%` 出现 **7 次**、反斜杠 **0 次**，说明转义链在该页产物上是正确的（不是「只跑单测」）。

### 6.3 ③ 新增圈码回源图抽查（随机 12 处，统计误报）

抽样方法：用与 `merge_ring_digit.py` 相同的去重口径复算「新增集合」= **331 条**（与 `docs/vert_taskF_missed_fix.json` 的
`how=ring_digit` 条数一致），`random.Random(20261104)` 抽 12 处，按普查坐标从 `source_pdf/wz7.pdf` 以 900dpi 裁图
（`/tmp/acceptance/ring_sample12_src.png`，另 6 处放大 `/tmp/acceptance/zoom_misread.png`）：

| # | 页/行 | OCR 数字 | 源图判读 | 是否真圈码 | 圈内数字是否与 OCR 一致 |
|---|---|---|---|---|---|
| 1 | p1685 r1 | 13 | 13 | ✔ | ✔ |
| 2 | p1687 r11 | 16 | 16 | ✔ | ✔ |
| 3 | p1706 r5 | 51 | 51 | ✔ | ✔ |
| 4 | p1706 r15 | 52 | 52 | ✔ | ✔ |
| 5 | p1712 r1 | 81 | **61** | ✔ | ✘（OCR 误读） |
| 6 | p1715 r5 | 68 | 68 | ✔ | ✔ |
| 7 | p1716 r1 | 70 | 70 | ✔ | ✔ |
| 8 | p1727 r4 | 82 | 82 | ✔ | ✔ |
| 9 | p1729 r4 | 86 | 86 | ✔ | ✔ |
| 10 | p1735 r0 | 33 | **93** | ✔ | ✘（OCR 误读，t2 已登记） |
| 11 | p1735 r6 | 83 | 83 | ✔ | ✔ |
| 12 | p1737 r10 | 97 | 97 | ✔ | ✔ |

- **误报率（不是圈码却报出）= 0/12**；与 t2 自述「24/24 是圈码」同向。
- **圈内数字误读 = 2/12 ≈ 16.7%**；与 t2 的「4/24 ≈ 16.7%」一致。本报告作者另用放大图逐一复核了 t2 点名的 4 处：
  p1708r7「读 55 实 65」、p1729r5「读 66 实 86」、p1735r0「读 33 实 93」、p1740r4「读 69 实 99」——**4/4 成立**。
  这属于 OCR 数据层面的既有错误（v29 里同样的错数字已按普通数字渲染），**不是本批新引入**，
  但现在以圈码形式呈现更显眼，须向用户披露（§9-1）。

### 6.4 ④ 判据「v1 184 → v2 352」的有界复现（不覆盖 t2 的普查产物）

为验证判据本身（而不只信 JSON），本报告作者在 **1682-1741 年表段内取 1700-1710 共 11 页**重跑普查工具
（跑前备份 `tmp_vert/cj5/ring_digit_census.json`，跑后已还原；备份 `/tmp/acceptance/ring_digit_census.orig.json`）：

```
v2（默认）：列尾数字候选 84 处 / 11 页 -> 圆环 84 处 / 11 页；段外命中 0
v1（回退）：列尾数字候选 84 处 / 11 页 -> 圆环 17 处 / 7 页；段外命中 0
v1 命中集合 ⊆ v2 命中集合：True（v1-only 0 处）
```

- 与「v2 补回两位数圈、v1 整类漏检」的机制方向一致；v1 的 184 是子集也与 t2 主张一致（有界验证）。
- 另用 `merge_ring_digit.py --check` 复核交付清单可复现：`368 项（ring_digit 331 / 保留 37）`、
  `因人工条目覆盖跳过 21 处（number 一致: True）`，**与现文件完全一致、未写盘**。

---

## 7. 纪律审查

### 7.1 工作树 diff 清单（`git status --porcelain`，20 项）

修改（13）：
`AGENTS.md`、`spec/README.md`、`src/test/unit/PURE_FUNC_SPEC.md`、
`src/utils/tex_escape.py`、`src/pipelines/build_pdf_v13.py`、`src/pipelines/build_classic.py`、
`src/calibration/fit_common.py`、`src/test/test_cases.py`、
`src/test/unit/test_pure_funcs.py`、`src/test/unit/test_audit_features.py`、
`src/tools/census_ring_digit.py`、`docs/vert_taskF_missed_fix.json`、`docs/vert_taskH_ring2digit.md`。

新增（6）：`docs/battle1_horizontal.md`、`docs/battle1_vertical_ring.md`、
`src/tools/ring_judge.py`、`src/tools/merge_ring_digit.py`、
`src/test/unit/test_census_ring_judge.py`、`src/test/unit/test_fit_common_cleanup.py`
（另有 `.agent-teams/` 为团队状态，不进交付）。

**结论**：全部落在两批任务范围内；**横排批没有碰竖排文件，竖排批没有碰横排文件**；
`src/pipelines/build_vert.py`、`src/test/verify_vert.py`、`src/test/verify_geom.py` 均零改动
（`git status` 无这些路径，`git diff --stat` 也没有）。**无误改对方管线。**

### 7.2 「无行为变化 / 无未登记接口变更」核对

- `PIPELINE_BEHAVIOR.md` 未改：合理——本批无 argv/env/JSON/GMPG/tmp 路径变更，且横排改前/改后 verify JSON 逐字节相同可证。
- 横排 4 个实现文件的实际 diff 只有：docstring/注释、`try/finally` 清理、两行 identity replace 删除、`os.environ.get` 单次取值。
  逐段看过（`git diff`），**不是**夹带行为修改；#3 的两行删除在 v13（归档、零调用），不影响任何产物。
- 竖排侧唯一会影响产物的是 **数据清单** `docs/vert_taskF_missed_fix.json`（368 项），
  这是既定的灌入机制（渲染端代码未改），并且报告/工具可复现（§6.4）。

### 7.3 调试残留 / 临时开关

- 新增/修改的工具里没有 `TODO`/`FIXME`/`pdb`/`breakpoint`/调试 `print` 残留（grep 过；工具 CLI 正常输出不算）。
- 所有 env 开关（`VERT_RING_CRIT=v1`、`VERT_RING_DPI`、`W/H/EDGE/CTR/FILL/AR`）都在 `census_ring_digit.py`
  docstring 与 `docs/battle1_vertical_ring.md` 登记，**有默认值、有回退路径**，不是临时硬编码。
- v13 / classic / fit_common 的改动没有新增 env。

### 7.4 低级别瑕疵（2 处）与备注

1. **`spec/README.md` 只登记了横排报告**（`docs/battle1_horizontal.md`），**没有登记竖排报告**
   `docs/battle1_vertical_ring.md`。而 t2 在 `docs/vert_taskH_ring2digit.md` 已把 P0-a 标「已解决」，
   账本与报告不一致。→ 建议补一行（这是文档一致性，不是实现问题）。
2. `src/tools/census_ring_digit.py` 的 **文件模式从 100755 变为 100644**（diff 头 `old mode/new mode`）。
   文档里都用 `/usr/bin/python3 src/tools/...` 调用，功能无影响；但若保留可执行位更一致。
3. 备注：`docs/battle1_horizontal.md` 的「四书 pitch」表里 wz3 标注了 FAIL 原因，口径正确；
   本报告与其一致，不重复计为问题。

### 7.5 「未登记 spec 变更」检查

- 改动的 spec 类文件只有 `src/test/unit/PURE_FUNC_SPEC.md`（#1/#2 契约更正 + `is_heading_by_md` + 锚点刷新）
  与 `spec/README.md`（账本行）；两者都在 t1 报告 §5 有说明，属**已登记**。
- 竖排侧没有 spec/vertical 文件被改；AGENTS.md 只改了 §6 #1-#9 状态（与实测一致）。
- 结论：**无未登记 spec 变更**；只有 §7.4-1 的「竖排报告未入账本」这一处遗漏。

---

## 8. 交付六件套逐项打勾

| 六件套 | 横排批（t1） | 竖排批（t2） | 打勾 |
|---|---|---|---|
| md5 | 产物 md5 随 xelatex 时间戳变化（t1 已如实说明）；**等价证据 = 5 份 verify JSON md5 逐字节相同**（本报告重跑复现：7883b25…/7ca85fa…/2d8bf97…/348a0e9…/31173ea…） | v30 PDF **b8bb2dc49103ee3a72405da194a92d7d**（实测）；wz6 `vert.tex` **ae9d2f52…**（实测） | ✓ |
| 页数 | 222/850/677/407/783，全部 1:1（实测） | 1748=1748；wz6 231=231（实测） | ✓ |
| 字符量 | geom 门禁无该指标；改前/改后逐页文本 0 差异（等价「不丢字」） | **930,754**（基线 930,670，+84，独立复算逐页一致）；wz6 68,412/70,373=97.2% | ✓ |
| verify 退出码 | wz1/wz4/mgfdmg = 0；wz3 = 1（历史固有，floor=79 复测 0）；wz2=1（classic 历史值） | wz7 = **0**；wz6 = **0** | ✓（例外已列明） |
| 另一本书回归 | wz2 classic（783 页，21 PASS/0 FAIL）+ 四书本身 | **wz6 `vert.tex` md5 逐字节相同** + verify PASS | ✓ |
| 审计数字 | 不适用（geom 口径另见 verify_geom） | `vert_layout_audit` **168/20/1/3 = 基线**；p50 0.45 / p95 1.53pt；页级偏移 0 页 | ✓ |

---

## 9. 遗留风险（本报告复核后仍然成立，交付时必须披露）

1. **圈内数字准确性 = OCR 原样**（t2 已登记，本报告独立复核）：新增 331 条抽样 12 处，**2/12（16.7%）圈内数字与源图不符**；
   t2 的 4/24（16.7%）与 4 个点名反例（p1708r7 / p1729r5 / p1735r0 / p1740r4）**复核成立**。
   例：p1735 r0 源图 93、产物圈内是 33；p1712 r1 源图 61、产物 81。
   **影响**：v29 里这些格本来就是 OCR 的错误数字（普通排），本轮只是把它们变成圈码；
   **不是新错，但现在更显眼**。建议按 t2 建议另立 **P0-a-2（圈内数字识别/校验）**，本轮不阻塞。
2. **p1704 行13 短列圈位偏高 ~11.8pt**（t2 自述，本报告三列对照图可目视确认）：属任务S「短列按框高居中」的既有口径，
   不是本轮判据/灌入引入；用户若逐页对照会看出来，交付时点名。
3. **>50 无 Unicode 圈码**：51-99 走 `○ + 全角数字`（文本层 `○５１`，可搜「５１」不可搜 ASCII「51」），
   全书 214 处；这是 v29 就有的设计限制，本轮把 51/52 扩到 51-99 后量变大，须向用户说明。
4. **wz3 pitch 79.7% 在 85% 下限下 FAIL**：历史固有（旧 OCR 数据 split 噪声），需要重跑 OCR，属另一条 P0；
   本批零影响（verify JSON 逐字节相同），**不是本批的回归**。
5. **#10 / #11 未修**（任务书明确不做）：`/tmp/seg2_line.*` 并发冲突仍在（t1 本轮实际踩到过，已改串行）；
   classic 对「已是 `\%`」的输入仍会二次转义（5 本语料普查真实正文无此形态）。
6. **复现依赖**：mgfdmg 构建依赖 `/tmp/page_imgs/p{0,1,2}.png` 与 `/tmp/mgfdmg_toc_rules.json`（不在仓库）；
   t2 的产物/普查明细在 `tmp_vert/`（gitignore）；本报告部分证据在 `/tmp/acceptance/`（进程结束后不保证保留）。
   本报告已把**关键原始输出**贴进正文，日志路径仅作溯源。

---

## 10. 未验证 / 不可验证项（如实列出）

- 未重跑**全书 1748 页的 v1 判据**（只做了 1700-1710 有界复现 + t2 的 184 历史值对照）；
  因此「184」这个数本报告只核到「机制方向与子集关系」，没有逐处复算。
- 未逐处人工核对全部 **331 条新增圈码**（抽样 12 处）；也未核对任务E 的 36 条人工 ring（不属本批）。
- 未对全书 168 处「列位异常列」逐列做源图对照（审计数字与基线相同，只证明无新增漂移，不证明这些列本身正确）。
- 未测试 `fix_tounicode_circled.py` 的 CMap 修正过程本身；只核了最终文本层码位（U+32BE/U+32BF 正确、无乱码）。
- 未 commit / 未 push（任务约束）；未修改任何实现代码；本报告是唯一写入仓库的文件。

---

## 11. 复现命令与日志清单

```bash
cd /opt/test

# 1) 测试
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q                  # 562 passed

# 2) 横排四书 verify_geom（t1 产物 /tmp/battle1/after）
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  /tmp/battle1/after/wz1.pdf data/wz1/wz1_spotting_coords.json data/wz1/wz1_spotting_lines.json --src-pdf source_pdf/wz1.pdf
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  /tmp/battle1/after/wz3.pdf data/wz3/wz3_linelevel_spotting_coords.json data/wz3/wz3_linelevel_spotting_lines.json --src-pdf source_pdf/wz3.pdf
#   wz3 若按文档基线复核：VERIFY_PITCH_FLOOR=79 ...（PASS）
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  /tmp/battle1/after/wz4.pdf data/wz4/wz4_spotting_coords.json data/wz4/wz4_spotting_lines.json --src-pdf source_pdf/wz4.pdf
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  /tmp/battle1/after/mgfdmg.pdf data/mgfdmg/mgfdmg_spotting_coords.json data/mgfdmg/mgfdmg_spotting_lines.json --src-pdf source_pdf/wz5.pdf
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  /tmp/battle1/after/wz2_classic.pdf data/wz2/wz2_spotting_coords.json data/wz2/wz2_spotting_lines.json --src-pdf source_pdf/wz2.pdf

# 3) wz7 全书
EL=$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v30.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$EL"
/usr/bin/python3 src/tools/vert_layout_audit.py --pdf output/wz7_full/wz7_full_v30.pdf

# 4) wz6 回归
rm -rf /tmp/wz6
VERT_TMP=/tmp/wz6 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6.pdf source_pdf/wz6.pdf
md5sum /tmp/wz6/vert.tex        # ae9d2f5259e12cff19e680b2a771b37d
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_vert.py \
  /tmp/wz6.pdf data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json --src-pdf source_pdf/wz6.pdf

# 5) 抽样/复算（本报告作者临时脚本，未入库；逻辑已在 §6 写清）
/usr/bin/python3 /tmp/acceptance/cmp_before_after.py       # 改前/改后 逐页文本+行 bbox
/usr/bin/python3 /tmp/acceptance/check_ring_pages.py       # p1704-1706 文本层圈码
/usr/bin/python3 /tmp/acceptance/crop_ring.py              # 900dpi 源图/三列对照裁图
/tmp/acceptance/run_geom_json.sh                            # before/after verify --json md5
```

日志（本轮保留于 `/tmp/acceptance/`，正文已贴关键原文）：
`pytest.log`、`geom_verify.log`、`geom_json.log`、`wz7_verify_vert.log`、`vert_layout_audit_v30.log`、
`wz6_regression.log`、`census_v1_1700_1710.log`、`census_v2_1700_1710.log`、
裁图 `key_cells_3way.png`、`ring_sample12_src.png`、`zoom_misread.png`。

---

## 12. 验收结论

- **t1（横排 local-bug 批次）：可交。** 9 项 issue（#1-#9）全部有实测结论、改动全部落在范围内；四书 + wz2 classic 的硬约束
  （1:1 / split 0 / missing 0）全过，pitch 与基线逐项相同，改前/改后产物逐页文本与行 bbox **0 差异**、
  verify JSON **逐字节相同**，测试 562 全绿。wz3 的 85% 门槛 FAIL 是历史基线、与本批无关。
- **t2（竖排两位数圈码批次）：可交。** p1704/1705/1706 的 49/50/51/52 已真检出并渲染为圈码
  （文本层码位 + 源图三列对照双证）；新增 331 条抽样 12/12 是真圈码（误报 0）；
  wz7 全书 verify_vert PASS（1748=1748 / 930,754 ≥ 930,670 / 整页丢失 0 / 越界 0+0）；
  wz6 `vert.tex` md5 逐字节相同 + PASS；审计 168/20/1/3 与基线一致。
- **交付时必须向用户说明**：§9-1（圈内数字取自 OCR，约 1/6 抽检与源图不符）、§9-2（p1704 r13 圈位偏高 ~11.8pt）、
  §9-3（>50 为 `○+全角数字`，不可按 ASCII 搜索）、§9-4（wz3 历史 FAIL 未在本批修）。
- **建议后续**：另立 P0-a-2 收口圈内数字（可用源图裁图/序号单调性做校验）；顺手补 §7.4 的两处文档/文件模式瑕疵。

> 本报告只写实测；所有命令可用 §11 原样复跑。未 commit、未 push、未改实现代码。
