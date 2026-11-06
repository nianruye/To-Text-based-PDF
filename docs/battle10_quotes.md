# battle10b · 11 条引号（+p563 省略号）落库 → v41

> 任务：t47 — battle10b　执行：竖排工程师　日期：2026-11-06
> 输入：t45 报告 `docs/battle10_punct_census.md`（27 条全查：真漏 10 / 误判 11 / 不确定 6）
> 基线：v40 `output/wz7_full/wz7_full_v40.pdf`（md5 5214c38e…）
> 产物：v41 `output/wz7_full/wz7_full_v41.pdf`；本报告；证据 `tmp_vert/battle10/quotes/`
> 数据-only：只改 `docs/vert_taskF_missed_fix.json`（+7 条 missing_char）；未改 `build_vert.py` / verify 判据；未 commit；token 未入库。

## 0. 结论

| 项 | 结果 |
|---|---|
| 引号 11 条逐条角形复核 | **落库 7 条**：`」` p126/p806/p1178 pos10/p1178 pos22/p551/p818（p551/p818 由 `——` 按角形重判为 `」`）+ `「` p1231 |
| 未落 4 条 | p1178 pos38（角形为开 ﹁，与 API 的 `」` 类型不符）、p1178 pos39（左+顶，角形不完整）、p1291/p1322（开 ﹁ 形，疑为文本已有 `「` 的重复）→ 登记不落 |
| p563 `……` | **不落**：补大窗后确认为**目录点线**（title→page number 的 leader dots，下方是页脚 五八九），不是省略号 |
| p1171×5 `……` | **不落**：同为目录点线（点线下方页脚 一六七/一九五/二三五/二四七/二五九） |
| 8/6/3（p1729×2、p1693/p1696） | **不落文本数字**：源图为圆圈/圈码 ㉞ → 归 **ring/census** 圈码类（登记去向：需另开 ring 轮补 census） |
| v41 | `output/wz7_full/wz7_full_v41.pdf` md5 **17ec4bb1eb55f1ab382637dfd5d0c3fa**，1748 页 |
| verify_vert（--expect-low） | **PASS**：1748=1748 / **931,197**（v40 931,190 +7）/ 差异>80 字页 18（预期 18）/ 整页丢失 0 / 越界 span 0+矢量 0 |
| v40→v41 diff | **6 页 +7**（p126/p551/p806/p818/p1231 各 +1，p1178 +2；无其他页变化） |
| punct_audit | **pair_balance 1993 → 1990（−3，下降）**；pair_split 495=495、line_start 2582=2582、dash_lead 1=1 |
| wz6 零回归 | `vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节相同 + verify PASS |
| pytest | **590 passed** |

## 1. 11 条引号逐条表

| 页 | pos | 原 ch | 落库 ch | 源图角形（8× 复核） | 结论 | 落库 |
|---|---|---|---|---|---|---|
| p126 | 15 | 」 | 」 | 左竖+底横（﹂，close-ok） | 真漏 | ✅ |
| p806 | 10 | 」 | 」 | 左竖+底横（close-ok） | 真漏 | ✅ |
| p1178 | 10 | 」 | 」 | 左竖+底横（close-ok） | 真漏 | ✅ |
| p1178 | 22 | 」 | 」 | 左竖+底横（close-ok） | 真漏 | ✅ |
| p1178 | 38 | 」 | — | 右竖+顶横（﹁ 开形），与 API 的 `」` 类型不符 | 类型不符/不确定 | ❌ |
| p1178 | 39 | 」 | — | 左竖+顶横（角形不完整） | 不确定 | ❌ |
| p1291 | 31 | 」 | — | 右竖+顶横（﹁ 开形），疑为文本已有 `「` 的重复 | 类型不符/疑重复 | ❌ |
| p1322 | 4 | 」 | — | 右竖+顶横（﹁ 开形），疑为文本已有 `「` 的重复 | 类型不符/疑重复 | ❌ |
| p1231 | 6 | 「 | 「 | 右竖+顶横（﹁，open-ok；焦点图见 `「夜迢迢`） | 真漏 | ✅ |
| p551 | 21 | —— | 」 | 左竖+底横（﹂，close-ok；源为引号角非破折号） | 重判为引号 | ✅ |
| p818 | 23 | —— | 」 | 左竖+底横（﹂，close-ok；源为引号角非破折号） | 重判为引号 | ✅ |

- 证据：`tmp_vert/battle10/quotes/sheet_quotes.png`（11 格 8×）、逐条 `q00..q10_*.png`。
- source 枚举：`api_strip_punct`（与既有 `api_strip`/`api_strip_quote`/`api_strip_census` 并列；spec 若要枚举清单，下一轮补）。
- 落库后同位置无双引号：全文 `「「`/`」」` 均 **0**；`﹂﹂` 239（未增）。

## 2. p563 / p1171 点线确认（不落）

- p563：大窗 `p563_dots_wide.png` 显示一条长竖点线，点线**下方是页脚 五八九**，点线上方是目录条目 —— 这是**目录 leader 点线**，不是省略号。
- p1171×5：同样每条点线下方对应页脚（一六七/一九五/二三五/二四七/二五九），为目录点线。
- 结论：**不落** `……`；登记理由（避免把装饰点线做成标点）。

## 3. 8/6/3 圈码（不落文本数字）

- p1693 `6` / p1696 `3`：源图为**圈码 ㉞（34）**；p1729 `8`×2：源图为小圆圈/圈号。
- 处置：**不给文本层插数字**；归 ring/census 圈码路径（`ring` 机制 1:1 占格）。本轮只登记去向：**需另开 ring 轮**把这 4 处补进 census。

## 4. 门禁与 diff

- 构建：`bash tmp_vert/battle10/quotes/build41.sh`，`BUILD_EXIT=0`，md5 **17ec4bb1eb55f1ab382637dfd5d0c3fa**。
- verify_vert（--expect-low）**PASS**：1748=1748 / **931,197**（v40 931,190 +7）/ 差异>80 字页 18（预期 18/非预期 0）/ 整页丢失 0 / 越界 span 0+矢量 0。
- v40→v41 diff：**6 页 +7**（p126 669→670、p551 774→775、p806 757→758、p818 772→773、p1178 738→740、p1231 572→573）。
- 插入落位：p126 `…遇金蓮。﹂`、p551 `…接你娘去。﹂因`、p806 `…串作你。﹂西門慶道`、p818 `…甚麼嘴兒？﹂陳經濟`、p1231 `…〔金字經〕「夜迢迢`（test build 已见）—— 6/6 页上下文正确。
- wz6：`/tmp/vert_wz6_b11/vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节相同 + verify PASS；pytest **590 passed**。

## 5. punct_audit 前后对比

| 指标 | v40（前） | v41（后） | 变化 |
|---|---|---|---|
| pair_balance | 1993 | **1990** | **−3（下降）** |
| pair_split | 495 | 495 | 0 |
| line_start | 2582 | 2582 | 0 |
| dash_lead | 1 | 1 | 0 |

- 逐页解释：7 条插入均为**行中/列中合法引号配对**（如 `。﹂`、`？﹂`、`〔…〕「夜…`），使相关页的 open/close 计数更平衡 → pair_balance 下降 3；pair_split/line_start/dash_lead 均未增（无新禁则违规）。
- 前后 JSON：`tmp_vert/battle10/quotes/audit_v40.json` / `audit_v41.json`。

## 6. 复现命令

```bash
# 单页 test（6 页）
VERT_PAGES=126,551,806,818,1178,1231 VERT_TMP=/tmp/wz7_test_q /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz7_full/wz7_full_spotting_lines_patched.json data/wz7_full/wz7_full_spotting_coords.json \
  tmp_vert/battle10/quotes/test_q.pdf source_pdf/wz7.pdf
# 全书 v41
bash tmp_vert/battle10/quotes/build41.sh
# 门禁
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v41.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \\n' < data/wz7_full/wz7_full_expect_low.txt)"
VERT_TMP=/tmp/vert_wz6_b11 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b11.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b11/vert.tex   # ae9d2f5259e12cff19e680b2a771b37d
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
# punct_audit 前后
/usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v40.pdf --mode v --src-pdf source_pdf/wz7.pdf --json tmp_vert/battle10/quotes/audit_v40.json
/usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v41.pdf --mode v --src-pdf source_pdf/wz7.pdf --json tmp_vert/battle10/quotes/audit_v41.json
```

## 7. 约束声明

- 未改 `src/test/verify_vert.py` 判据；未改 `src/pipelines/build_vert.py`；未 commit/push；token 未出现在任何文件/报告。
- `——`/`—` 未按破折号落库（p551/p818 按引号重判）；`……` 未落（目录点线）；8/6/3 未落文本数字（ring 圈码去向已登记）。


---

## 8. t52 补落（v42）

> t49 复审认定本报告 §1 未落的 p1178 pos38/39、p1291 三条为**闭引号角**（自动分类器误判为开角），应落；p1322（U 形）仍不落。t52 已补落 3 条并重建 v42。

- 新增：`missing_char` +3（source=api_strip_punct，ch=`」`；p1178 pos38 cell [415.2,898.6,440.6,918.3]、p1178 pos39 cell [315.1,917.3,339.1,937.1]、p1291 pos31 cell [163.6,759.8,196.0,779.4]）。
- v42：`output/wz7_full/wz7_full_v42.pdf` md5 **f964ad7133841025c2d415c40f52af89**；verify_vert（--expect-low）**PASS**：1748=1748 / **931,200**（v41 931,197 +3）/ 18 预期 / 丢失 0 / 越界 0+0。
- v41→v42 diff：**2 页 +3**（p1178 +2、p1291 +1；两条同在 p1178，故页数为 2 而非 3）。
- punct_audit：pair_balance **1990→1987（−3）**；pair_split 495、line_start 2582、dash_lead 1 均不变；QSF 925（append 696/replace 229）不变；`「「`/`」」` 0、`﹂﹂` 239 未增。
- **「11 条」集合定义**：t47 的 11 行 = 8 真漏 `」` + 1 `「` + p551/p818 重判；t45 的 11 条 = 10 `」` + 1 `「`（含 p716/p1568、不含 p551/p818）—— 两处不是同一集合；t52 后实际落库 10 条（p1322 未落）。
