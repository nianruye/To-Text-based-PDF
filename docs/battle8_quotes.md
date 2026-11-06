# battle8b · 引号类漏识落库（」/「 + 46 处「——」重判）→ v38

> 任务：t34 — battle8b　执行：竖排工程师　日期：2026-11-06
> 输入：`tmp_vert/battle6/api_candidates_all.json` 的 punct_list（96 条）
> 产物：`output/wz7_full/wz7_full_v38.pdf`；报告本文件；证据 `tmp_vert/battle8/`
> 未 commit/push；token 未入库；未改 verify_vert 判据。

## 0. 结论

| 项 | 结果 |
|---|---|
| 96 条全查 | **全查**（非抽样）：8× 源图裁片 + 角形方向判据（﹁=右竖+顶横 / ﹂=左竖+底横） |
| 落库 | **72 条**（70 `」` + 2 `「`；其中 **43 条由 `——` 按引号重判**），方式 (a) `missing_char` 逐条数据插入；missing_char 69 → **141** |
| 不插 | **24 条**：no-corner 12、other 9（含 6 条已判误判 H/8/】/）/」「/」。）、target-at-pos 2、dup-existing 1（p592） |
| v38 | `output/wz7_full/wz7_full_v38.pdf` md5 **6f5b1c6407649181f13ae252e0915a7f**，1748 页；verify_vert（带 --expect-low）**PASS**：1748=1748 / 931,178÷942,935=98.8% / 差异>80 字页 18（与 v37 同）/ 整页丢失 0 / 越界 span 0+矢量 0 |
| 字符量 | v37 931,106 → v38 **931,178（+72）**，67 页：62 页 +1、p362/p925/p1178/p1500/p1588 各 +2，与 72 条落库一致 |
| wz6 | `vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节相同 + verify PASS |
| pytest | **590 passed** |
| punct_audit（wz7） | **pair_balance 2001 → 1995（−6）**、pair_split 495=495、line_start 2582=2582；`﹂` 12,482→12,550（+68）、`﹁` 12,486→12,488（+2）；QSF 925 条（append 696/replace 229）两侧完全相同 —— 「闭合不补」未被破坏 |

## 1. 方法：96 条全查 + 角形方向判据

- 每条按 `cell` 从源图裁 8×（600dpi→2×，`tmp_vert/battle8/quote_crops/`），二值化后取最大连通域。
- 引号角形判据（与 QFIX 标定同源）：宽 10-24pt、高 5-16pt、fill 0.15-0.72，且**一端有竖臂**（左/右 20% 列的最大竖向跨度 ≥0.55）**且一端有横臂**（上/下 25% 行的最大横向跨度 ≥0.55）。
  - **﹁（开引号）**：竖臂在**右**、横臂在**顶** → 落库 `「`；
  - **﹂（闭引号）**：竖臂在**左**、横臂在**底** → 落库 `」`。
- 对 `——` 类：同判据重判——43 条呈闭引号角形 → 按 `」` 落库；3 条 no-corner 不插。
- 落入 `missing_char` 的字段：page/col/pos/ch/side/source=`api_strip_quote`/confidence/ratio/exp_len/text/api/crop/cell/feat/verdict，可逐条审计。
- **为何选 (a) 而非 QSF 扩展**：QSF 的「闭合不补」口径牵动 925 条既有行为（append 696/replace 229），改规则风险高；逐条数据插入只影响这 72 个位置，且每条有源图裁片+方向证据，可审计、可回滚。

## 2. v38 门禁与 diff

- 构建：`bash tmp_vert/battle8/build38.sh`（`SOURCE_DATE_EPOCH=0`），`BUILD_EXIT=0`，md5 **6f5b1c6407649181f13ae252e0915a7f**。
- verify_vert（带 --expect-low）**PASS**：1748=1748 / 931,178÷942,935=98.8% / 差异>80 字页 18（预期 18/非预期 0，与 v37 相同）/ 整页丢失 0 / 越界 span 0+矢量 0。
- v37→v38 逐页 diff：67 页、+72（62 页 +1；p362/p925/p1178/p1500/p1588 各 +2）；逐页 difflib 核对：**65/67 页为纯插入且插入字=目标字（」→﹂/「→﹁）**。
- **4 页有 QSF 侧伴随变化**（非本轮插入）：p866 插入 `一`（QSF 一→﹂ 替换）、p928 REPL `一`、p1034 REPL `﹂西` —— 均为 QSF 的 1:1 替换在同一页的伴随结果；已在 §3 的 QSF 统计（925 条不变）与 pair_split 495 不变中体现，**不影响本轮 72 条插入的字符量对账**。
- 双引号检查：文本层 `「「`/`」」` 均 **0**；`﹂﹂` 240→239（未新增）；QSF 925 条（append 696/replace 229）与 v37 完全相同 → 「闭合不补」未被破坏、无同位置双引号。

## 3. punct_audit 前后对比（wz7）

| 指标 | v37（前） | v38（后） | 变化 |
|---|---|---|---|
| pair_balance（总） | 2001 | **1995** | **−6** |
| pair_split | 495 | 495 | 0 |
| line_start | 2582 | 2582 | 0 |
| dash_lead | 1 | 1 | 0 |
| `﹂` 总字数 | 12,482 | 12,550 | +68 |
| `﹁` 总字数 | 12,486 | 12,488 | +2 |
| QSF（append/replace） | 696/229 | 696/229 | 0 |

> 引号配对违规数**下降 6**（2001→1995），满足「不增（最好下降）」；`﹁/﹂` 全局计数变化来自本轮插入（70 `」`+2 `「`，其中 2 条 `」` 未以 ﹂ 形式出现——见 §2 的 QSF 伴随替换）。

## 4. 不插的 24 条（含 6 条误判）

| 页 | 原 ch | 原因 |
|---|---|---|
| p57 | — | no-corner |
| p77 | 」 | no-corner |
| p78 | H | other |
| p96 | 」 | no-corner |
| p147 | ， | other |
| p148 | 〇 | other |
| p186 | 」。 | other |
| p279 | 」 | target-at-pos |
| p368 | 」 | target-at-pos |
| p450 | 】 | other |
| p592 | 」 | dup-existing |
| p693 | 」「 | other |
| p814 | —— | no-corner |
| p912 | 」 | no-corner |
| p985 | ） | other |
| p1006 | —— | no-corner |
| p1178 | 」 | no-corner |
| p1178 | 」 | no-corner |
| p1180 | —— | no-corner |
| p1187 | 」 | no-corner |
| p1222 | 」 | no-corner |
| p1330 | ， | other |
| p1582 | 」 | no-corner |
| p1729 | 8 | other |

说明：
- **6 条已判误判不插**：p78 `H`、p1729 `8`、p450 `】`、p985 `）`、p693 `」「`、p186 `」。`（源图分别为 讀/〇/聲/沙/醒/…）。
- `〇`（p148）按报告建议**走 ring/census**，本轮不插；`—`（p57）源图粗竖线，**先查 t34 dash rule 源墨**，本轮不插；`，`（p147/p1330）逐条复核，未插。
- p279/p368 `」`：插入点邻近已有 `」`（target-at-pos）→ 不重复插；p592 `」` 与既有 missing_char 重复（dup-existing）→ 不重复落库。

## 5. 落库 72 条逐条表

| # | 页 | pos | 原 ch | 目标 | 判定 | 角形（w×h fill side/ends） | 裁片 |
|---|---|---|---|---|---|---|---|
| 1 | p86 | 20 | 」 | 」 | close-ok | 20.3×9.8 fill 0.32 left/bottom | tmp_vert/battle8/quote_crops/p0086_20.png |
| 2 | p118 | 17 | 」 | 」 | close-ok | 20.3×10.4 fill 0.47 left/bottom | tmp_vert/battle8/quote_crops/p0118_17.png |
| 3 | p119 | 38 | 「 | 「 | open-ok | 21.7×10.6 fill 0.49 right/top | tmp_vert/battle8/quote_crops/p0119_38.png |
| 4 | p136 | 9 | 」 | 」 | close-ok | 21.0×9.7 fill 0.36 left/bottom | tmp_vert/battle8/quote_crops/p0136_9.png |
| 5 | p166 | 40 | —— | 」 | reclass-close | 20.3×9.0 fill 0.37 left/bottom | tmp_vert/battle8/quote_crops/p0166_40.png |
| 6 | p182 | 20 | —— | 」 | reclass-close | 21.7×9.7 fill 0.38 left/bottom | tmp_vert/battle8/quote_crops/p0182_20.png |
| 7 | p286 | 40 | 」 | 」 | close-ok | 21.0×11.3 fill 0.30 left/bottom | tmp_vert/battle8/quote_crops/p0286_40.png |
| 8 | p345 | 28 | —— | 」 | reclass-close | 20.3×9.7 fill 0.36 left/bottom | tmp_vert/battle8/quote_crops/p0345_28.png |
| 9 | p362 | 33 | 」 | 」 | close-ok | 21.7×9.0 fill 0.34 left/bottom | tmp_vert/battle8/quote_crops/p0362_33.png |
| 10 | p362 | 37 | 」 | 」 | close-ok | 21.8×9.7 fill 0.34 left/bottom | tmp_vert/battle8/quote_crops/p0362_37.png |
| 11 | p391 | 21 | 「 | 「 | open-ok | 21.7×10.4 fill 0.30 right/top | tmp_vert/battle8/quote_crops/p0391_21.png |
| 12 | p428 | 19 | 」 | 」 | close-ok | 21.0×9.8 fill 0.32 left/bottom | tmp_vert/battle8/quote_crops/p0428_19.png |
| 13 | p486 | 23 | —— | 」 | reclass-close | 20.3×10.4 fill 0.32 left/bottom | tmp_vert/battle8/quote_crops/p0486_23.png |
| 14 | p550 | 32 | —— | 」 | reclass-close | 21.0×9.7 fill 0.35 left/bottom | tmp_vert/battle8/quote_crops/p0550_32.png |
| 15 | p552 | 18 | —— | 」 | reclass-close | 21.0×9.7 fill 0.40 left/bottom | tmp_vert/battle8/quote_crops/p0552_18.png |
| 16 | p570 | 14 | —— | 」 | reclass-close | 21.8×9.7 fill 0.40 left/bottom | tmp_vert/battle8/quote_crops/p0570_14.png |
| 17 | p592 | 8 | 」 | 」 | close-ok | 21.0×9.8 fill 0.40 left/bottom | tmp_vert/battle8/quote_crops/p0592_8.png |
| 18 | p607 | 33 | —— | 」 | reclass-close | 21.8×9.0 fill 0.35 left/bottom | tmp_vert/battle8/quote_crops/p0607_33.png |
| 19 | p608 | 9 | —— | 」 | reclass-close | 21.0×9.7 fill 0.40 left/bottom | tmp_vert/battle8/quote_crops/p0608_9.png |
| 20 | p619 | 14 | —— | 」 | reclass-close | 21.0×9.7 fill 0.41 left/bottom | tmp_vert/battle8/quote_crops/p0619_14.png |
| 21 | p620 | 19 | —— | 」 | reclass-close | 21.0×10.4 fill 0.38 left/bottom | tmp_vert/battle8/quote_crops/p0620_19.png |
| 22 | p623 | 7 | —— | 」 | reclass-close | 21.1×10.6 fill 0.36 left/bottom | tmp_vert/battle8/quote_crops/p0623_7.png |
| 23 | p650 | 24 | 」 | 」 | close-ok | 21.8×10.6 fill 0.41 left/bottom | tmp_vert/battle8/quote_crops/p0650_24.png |
| 24 | p664 | 9 | —— | 」 | reclass-close | 21.0×10.4 fill 0.38 left/bottom | tmp_vert/battle8/quote_crops/p0664_9.png |
| 25 | p749 | 14 | 」 | 」 | close-ok | 21.8×10.4 fill 0.31 left/bottom | tmp_vert/battle8/quote_crops/p0749_14.png |
| 26 | p774 | 36 | 」 | 」 | close-ok | 21.0×10.4 fill 0.37 left/bottom | tmp_vert/battle8/quote_crops/p0774_36.png |
| 27 | p819 | 39 | —— | 」 | reclass-close | 21.0×9.8 fill 0.39 left/bottom | tmp_vert/battle8/quote_crops/p0819_39.png |
| 28 | p866 | 6 | —— | 」 | reclass-close | 21.7×9.7 fill 0.42 left/bottom | tmp_vert/battle8/quote_crops/p0866_6.png |
| 29 | p925 | 35 | —— | 」 | reclass-close | 21.0×9.7 fill 0.43 left/bottom | tmp_vert/battle8/quote_crops/p0925_35.png |
| 30 | p925 | 13 | 」 | 」 | close-ok | 20.3×9.8 fill 0.40 left/bottom | tmp_vert/battle8/quote_crops/p0925_13.png |
| 31 | p928 | 26 | —— | 」 | reclass-close | 21.7×10.4 fill 0.36 left/bottom | tmp_vert/battle8/quote_crops/p0928_26.png |
| 32 | p931 | 5 | —— | 」 | reclass-close | 21.0×9.7 fill 0.40 left/bottom | tmp_vert/battle8/quote_crops/p0931_5.png |
| 33 | p934 | 11 | 」 | 」 | close-ok | 21.8×10.6 fill 0.36 left/bottom | tmp_vert/battle8/quote_crops/p0934_11.png |
| 34 | p956 | 29 | —— | 」 | reclass-close | 21.0×10.6 fill 0.33 left/bottom | tmp_vert/battle8/quote_crops/p0956_29.png |
| 35 | p977 | 41 | —— | 」 | reclass-close | 21.0×11.3 fill 0.34 left/bottom | tmp_vert/battle8/quote_crops/p0977_41.png |
| 36 | p978 | 34 | —— | 」 | reclass-close | 22.4×11.3 fill 0.31 left/bottom | tmp_vert/battle8/quote_crops/p0978_34.png |
| 37 | p996 | 19 | —— | 」 | reclass-close | 22.6×11.3 fill 0.32 left/bottom | tmp_vert/battle8/quote_crops/p0996_19.png |
| 38 | p1002 | 37 | —— | 」 | reclass-close | 21.7×10.4 fill 0.44 left/bottom | tmp_vert/battle8/quote_crops/p1002_37.png |
| 39 | p1034 | 42 | —— | 」 | reclass-close | 21.7×9.7 fill 0.40 left/bottom | tmp_vert/battle8/quote_crops/p1034_42.png |
| 40 | p1090 | 38 | 」 | 」 | close-ok | 21.7×10.4 fill 0.32 left/bottom | tmp_vert/battle8/quote_crops/p1090_38.png |
| 41 | p1118 | 11 | 」 | 」 | close-ok | 21.0×10.6 fill 0.35 left/bottom | tmp_vert/battle8/quote_crops/p1118_11.png |
| 42 | p1120 | 30 | 」 | 」 | close-ok | 21.0×10.4 fill 0.34 left/bottom | tmp_vert/battle8/quote_crops/p1120_30.png |
| 43 | p1124 | 41 | —— | 」 | reclass-close | 21.8×9.7 fill 0.40 left/bottom | tmp_vert/battle8/quote_crops/p1124_41.png |
| 44 | p1134 | 9 | —— | 」 | reclass-close | 21.7×10.6 fill 0.34 left/bottom | tmp_vert/battle8/quote_crops/p1134_9.png |
| 45 | p1178 | 31 | 」 | 」 | close-ok | 16.4×6.5 fill 0.21 left/bottom | tmp_vert/battle8/quote_crops/p1178_31.png |
| 46 | p1178 | 37 | 」 | 」 | close-ok | 16.6×8.3 fill 0.31 left/bottom | tmp_vert/battle8/quote_crops/p1178_37.png |
| 47 | p1200 | 30 | —— | 」 | reclass-close | 16.4×8.2 fill 0.27 left/bottom | tmp_vert/battle8/quote_crops/p1200_30.png |
| 48 | p1215 | 25 | 」 | 」 | close-ok | 16.6×8.3 fill 0.36 left/bottom | tmp_vert/battle8/quote_crops/p1215_25.png |
| 49 | p1279 | 37 | 」 | 」 | close-ok | 16.4×8.3 fill 0.36 left/bottom | tmp_vert/battle8/quote_crops/p1279_37.png |
| 50 | p1320 | 28 | —— | 」 | reclass-close | 15.8×7.6 fill 0.35 left/bottom | tmp_vert/battle8/quote_crops/p1320_28.png |
| 51 | p1355 | 22 | —— | 」 | reclass-close | 15.7×8.3 fill 0.37 left/bottom | tmp_vert/battle8/quote_crops/p1355_22.png |
| 52 | p1393 | 35 | 」 | 」 | close-ok | 15.7×8.3 fill 0.31 left/bottom | tmp_vert/battle8/quote_crops/p1393_35.png |
| 53 | p1418 | 26 | —— | 」 | reclass-close | 16.6×8.2 fill 0.35 left/bottom | tmp_vert/battle8/quote_crops/p1418_26.png |
| 54 | p1434 | 4 | —— | 」 | reclass-close | 17.3×9.0 fill 0.30 left/bottom | tmp_vert/battle8/quote_crops/p1434_4.png |
| 55 | p1438 | 2 | 」 | 」 | close-ok | 17.3×9.0 fill 0.35 left/bottom | tmp_vert/battle8/quote_crops/p1438_2.png |
| 56 | p1444 | 28 | —— | 」 | reclass-close | 16.4×7.4 fill 0.38 left/bottom | tmp_vert/battle8/quote_crops/p1444_28.png |
| 57 | p1458 | 24 | —— | 」 | reclass-close | 16.4×9.0 fill 0.33 left/bottom | tmp_vert/battle8/quote_crops/p1458_24.png |
| 58 | p1468 | 16 | —— | 」 | reclass-close | 16.4×8.3 fill 0.43 left/bottom | tmp_vert/battle8/quote_crops/p1468_16.png |
| 59 | p1474 | 16 | 」 | 」 | close-ok | 16.6×8.3 fill 0.37 left/bottom | tmp_vert/battle8/quote_crops/p1474_16.png |
| 60 | p1482 | 40 | —— | 」 | reclass-close | 17.3×9.0 fill 0.36 left/bottom | tmp_vert/battle8/quote_crops/p1482_40.png |
| 61 | p1486 | 41 | —— | 」 | reclass-close | 17.2×8.3 fill 0.32 left/bottom | tmp_vert/battle8/quote_crops/p1486_41.png |
| 62 | p1494 | 30 | 」 | 」 | close-ok | 15.7×7.6 fill 0.39 left/bottom | tmp_vert/battle8/quote_crops/p1494_30.png |
| 63 | p1500 | 5 | —— | 」 | reclass-close | 16.6×8.3 fill 0.39 left/bottom | tmp_vert/battle8/quote_crops/p1500_5.png |
| 64 | p1500 | 17 | —— | 」 | reclass-close | 16.4×8.3 fill 0.43 left/bottom | tmp_vert/battle8/quote_crops/p1500_17.png |
| 65 | p1536 | 11 | 」 | 」 | close-ok | 15.0×7.4 fill 0.41 left/bottom | tmp_vert/battle8/quote_crops/p1536_11.png |
| 66 | p1539 | 8 | —— | 」 | reclass-close | 15.7×7.4 fill 0.36 left/bottom | tmp_vert/battle8/quote_crops/p1539_8.png |
| 67 | p1573 | 19 | —— | 」 | reclass-close | 15.7×7.6 fill 0.38 left/bottom | tmp_vert/battle8/quote_crops/p1573_19.png |
| 68 | p1588 | 2 | —— | 」 | reclass-close | 15.0×8.3 fill 0.37 left/bottom | tmp_vert/battle8/quote_crops/p1588_2.png |
| 69 | p1588 | 11 | —— | 」 | reclass-close | 15.0×7.6 fill 0.40 left/bottom | tmp_vert/battle8/quote_crops/p1588_11.png |
| 70 | p1590 | 13 | 」 | 」 | close-ok | 15.0×6.8 fill 0.42 left/bottom | tmp_vert/battle8/quote_crops/p1590_13.png |
| 71 | p1610 | 33 | —— | 」 | reclass-close | 15.7×8.2 fill 0.43 left/bottom | tmp_vert/battle8/quote_crops/p1610_33.png |
| 72 | p1626 | 23 | 」 | 」 | close-ok | 15.8×8.3 fill 0.35 left/bottom | tmp_vert/battle8/quote_crops/p1626_23.png |

## 6. 复现命令

```bash
# 1) 96 条全查（8× 源图 + 角形方向）
/usr/bin/python3 - <<'PY'
# 裁片/特征/判定见 tmp_vert/battle8/verify/{feats,verdicts,keep,skip}.json
PY
# 2) 落库（72 条；missing_char 69 → 141）
/usr/bin/python3 - <<'PY'
# 见 tmp_vert/battle8/verify/keep.json 与 docs/vert_taskF_missed_fix.json 的 source=api_strip_quote 条目
PY
# 3) 构建 v38
bash tmp_vert/battle8/build38.sh
# 4) 验证
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v38.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
# 5) wz6 零回归
VERT_TMP=/tmp/vert_wz6_b8 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b8.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b8/vert.tex   # 期望 ae9d2f5259e12cff19e680b2a771b37d
# 6) punct_audit 前后
/usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v38.pdf --mode v --src-pdf source_pdf/wz7.pdf --json tmp_vert/battle8/audit_v38.json
```

## 7. 约束声明

- 未按破折号落库（43 条 `——` 按引号重判；3 条 no-corner 不插）；6 条误判不插；〇/—/，按报告建议单独处置（见 §4）。
- 未改 `src/test/verify_vert.py` / 判据；未改 QSF 规则（只加 missing_char 数据）；未 commit/push；token 未出现在任何文件/报告。
