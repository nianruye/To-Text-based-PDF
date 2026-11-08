# battle20 · 候选源墨复核 + 落库 → v50（含 t95 F1/F2 修复）

> 任务：t91 + t95（repair round 2）— 对 t87 的闭号 1,060 条 + 括号 271 条做源墨判据复核，命中落库，重建 v50
> 执行：竖排工程师　日期：2026-11-08
> 产物：`output/wz7_full/wz7_full_v50.pdf`（md5 **21216d14e7a085240b0938ad004900bd**）；构建 `tmp_vert/battle20/build50.sh`
> 约束：不改 verify 判据；不 commit；token 不入库；落库全走 fix JSON（无页白名单）。

## 0. 结论

| 项 | 结果 |
|---|---|
| 闭号候选 | 1,060 条 → token 对齐 719（341 不匹配，多为推断档）→ 角形判据命中 **23**（总 2.2% / 对齐后 3.2%）→ **F1/F2 修复后保留 9 条**（14 条按相邻闭号/跨列/净 0 拒） |
| 补括号 / 括号类型 | 271 条 → **0 条通过**（两层判据：先名表判定，再方括号形状），全部不落并登记（两种 reason：`name_not_in_table` / `bracket_shape_fail`） |
| 字符替换 | 2,379 条**不落**，清单 `tmp_vert/battle20/char_replace_list.json`（page/row/pos/B/A/裁片），留给字符仲裁轮 |
| v50 | v49 931,184 → **931,193（+9）** = **9 条 insert**；8 页 +9 字（p358 两条，余各 1） |
| `﹂﹂` 对账 | v49 **237** → v50 修复前 **239** → **修复后 237**（新增 2 对已由 F1/F2 拒掉） |
| 门禁 | verify **PASS**（1748=1748 / 931,193 / 18 预期 / 丢失 0 / 越界 0+0）；wz6 **ae9d2f52…** 逐字节 + PASS；pytest **617 passed** |
| 映射命中率 | 候选→B 行/pos→源图 cell：**6,273/6,312 = 99.38%** 唯一（ambiguous 10 + unmapped 29 = 39 进待人工；row_mismatch 10 告警） |

## 1. 方法（A 只报可疑，源图像素裁决）

1. **候选→B 行/pos→源图 cell 三级映射**：fusion body 对齐重算引号 token（bp/side），候选 `pos`（±2）匹配 token；由 bp 反推 B 行 `row` 与行内 raw pos；映射不唯一/对不上进待人工，不猜位置；裁片用 **B 行列框（PDF pt）** + cell（±1 格）。
2. **闭号判据**：`_ink_quote_corner`（8–26×4–18pt、fill 0.08–0.80、一竖臂+一横臂、对边臂短）+ 位置闸门；命中 → fix JSON `insert`（`」`，行内 raw pos，保留既有字）。
3. **括号**：先名表（B 独立名列 + A 的〔名〕）判定，再方括号形状判据（名首/名末 cell 细长竖笔 w≤8pt,h≥6pt）；两层都过才 `replace`。
4. **落库顺序**：insert/replace 在 battle14–16 引号清理**之后**应用（否则先插的 `」` 被删）；同列多 insert 按 pos 降序。
5. 全部落库走 fix JSON（`class=insert`，page/col/pos/ch/crop/ink/note），可审计可回滚；无页白名单。

## 2. 闭号复核明细（1,060 条）

| 结果 | 数量 | 说明 |
|---|---|---|
| token 对齐失败 | 341 | 候选 pos 与 A token bp 差 >2（353 条推断档无 A token，占多数） |
| 对齐但无角形 | 696 | cell 裁片无「一竖臂+一横臂」角形 |
| 角形命中 | 23 | w 20–22 / h 9–11 / fill 0.30–0.36（样例 `crops/p0230_r18_pos022.png`） |
| F1 拒（raw pos±1 已有闭号） | 3 | p531（`？?」`）、p1254（`」唱：`）等 |
| F1 拒（产物上下文已有闭号） | 10 | p730/866/966/1206/1322/1444/1514/1524/1611/1668：产物该处前一/后一字符已是 `﹂`，再插会成 `﹂﹂` |
| F1 拒（重建后发现） | 1 | p1458：产物出现 `。﹂﹂春梅道` → 拒 |
| 净 0（列容量顶出） | 1 | p1571：插入 1 字但列满顶出 1 字 → 不落 |
| **最终落库** | **9** | p230/358×2/898/1122/1229/1234/1256/1354（fix JSON `source=dual_ocr_ink`） |

## 3. F1/F2 修复（t95，repair round 2）

- **F1（相邻闭号）**：insert 前检查 **raw pos±1** 与 **产物（v49 文本）插入边界两侧** 是否已有 `」/﹂`；有则跳过并登记（`repair_round2.json`）。修复前 v50 `﹂﹂` = 239（p1254 + p1444 两对新双闭号）；修复后 **237**。
- **F2（跨列边界）**：`pos==0` 时检查产物插入边界前一字符（上一列末）；若已是闭号 → 不插（p1444 = `。﹂﹂不一時`）；另实现「按源图 y 反查上一列末」回填逻辑（F2b，本轮无触发）。**禁止在下一列首插上一列的闭号**。
- 对 **23 条角形候选重新复核**：保留 9、拒 14（逐条理由 `tmp_vert/battle20/repair_round2.json`）；`﹂﹂` 计数纳入字符对账（§5）。

## 4. 括号复核（271 条）

- **两层判据**：① 名表判定（候选名是否 B 独立名列/ A 的〔名〕）→ 未中记 `name_not_in_table`；② 名首/名末 cell 方括号竖笔形状 → 未中记 `bracket_shape_fail`。
- 结果：补括号 148 + 括号类型 123（含 2 条 t87 可落库）→ **0 条通过**；全部保留待人工、不落（`bracket_verify.json` 逐条含两层 reason 与 top/bottom 竖笔数）。

## 5. 字符量对账（v49 → v50）

| 项 | 数量 | Δchar |
|---|---|---|
| 新增 insert（闭号角形，F1/F2 后） | 9 | **+9** |
| replace | 0 | 0 |
| 删除 | 0 | 0 |
| F1/F2/净 0 拒绝（不落） | 14 | 0 |
| **v49→v50** | | **+9**（931,184 → **931,193**） |
| `﹂﹂` 对数 | v49 237 → v50 **237** | 0（修复前 239，已回到基线） |

逐页：p230 +1、p358 +2、p898 +1、p1122 +1、p1229 +1、p1234 +1、p1256 +1、p1354 +1 = **8 页 +9 字**，与 9 条 insert 逐一对应。

## 6. 去重

- 与既有 **160 条 missing_char + 3 条 insert**：同 page/col/pos **0 重复**。
- 160 missing_char / 367 ring / 1 dash 本轮回填行为不变（日志 `灌入 528 处: dash 1 / ring 352+15 / missing_char 160`）。

## 7. 门禁

| 门禁 | 结果 |
|---|---|
| verify_vert（--expect-low） | **PASS**：1748=1748 / **931,193**÷942,935=98.8% / 差异>80 字页 18（预期 18/非预期 0）/ 整页丢失 0 / 越界 span 0+矢量 0 |
| wz6 | `vert.tex` **ae9d2f5259e12cff19e680b2a771b37d** 逐字节 + verify PASS |
| pytest | **617 passed** |

## 8. R1 措辞更正（t89 遗留，本报告口径）

> t88 报告「wz6 531 项全跳过」不准确。wz6 的 531 项 = **367 ring + 160 missing_char + 1 dash + 3 insert**：
> - **ring / dash 走匹配阶段**：按页/列框尝试匹配，wz6 上因页号越界/列不匹配打印「未匹配 -> 跳过」；
> - **missing_char / insert / replace 整类**受 `VERT_MISSED_FIX_MIN_PAGES` 小书守卫（wz6 231<1000）跳过。
> 结论「wz6 vert.tex 逐字节不变 + verify PASS」成立，但原因需按上述两类分开表述。

## 9. 报告字段与 QSF 说明

- 本报告所有计数均按 **fix JSON / closed_verify / repair_round2 的实际字段**（page/col/pos/ch/crop/ink/rect）描述，不引用不存在的字段；括号 reason 为两层判据（§4）。
- **QSF 差异说明**：QSF（引号替换表）v49→v50 **无差异**，「闭合不补」策略未被本轮 insert 破坏；本轮 `replace` 0 项（无因 insert 上下文变化而失效的替换）；若后续启用 replace，其 `current` 匹配会因 insert 上下文变化而跳过（构建日志会打印不匹配原因），这是设计行为而非回归。

## 10. 复现命令

```bash
# 1) 候选映射 + 源墨复核（一次性）
/usr/bin/python3 tmp_vert/battle20/verify_ink.py       # -> closed_verify.json（23 命中/1037 不落）
/usr/bin/python3 tmp_vert/battle20/bracket_verify.py   # -> bracket_verify.json（0 命中/271 不落）
# 2) F1/F2 修复复核（t95）
/usr/bin/python3 tmp_vert/battle20/repair_round2.py    # -> repair_round2.json（9 保留/14 拒）
# 3) 构建 v50
bash tmp_vert/battle20/build50.sh
md5sum output/wz7_full/wz7_full_v50.pdf                 # 21216d14…
# 4) 门禁
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v50.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
VERT_TMP=/tmp/vert_wz6_b26 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b26.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b26/vert.tex                        # ae9d2f52…
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

## 11. 证据与约束

- `tmp_vert/battle20/`：`closed_verify.json`（1,060 条）、`repair_round2.json`（9 保留/14 拒，逐条理由）、`bracket_verify.json`（271 条，两层 reason）、`char_replace_list.json`（2,379 条）、`dropped_inserts.json`（t91 登记）、`crops/`、`build50.sh`、`verify_ink.py`、`bracket_verify.py`、`repair_round2.py`
- fix JSON 540 项（9 条 `dual_ocr_ink` insert）；无页白名单
- 只写 tmp_vert/battle20/ + 本文档 + fix JSON/output；未改 verify 判据/data/source_pdf；未 commit；token 未入库。
- 局限：闭号判据命中率低（2.2%）；括号形状判据 0 命中；14 条角形候选被 F1/F2 拒（其中 10 条因产物已有闭号，说明 battle16 引号修复已覆盖同位置）；替换 2,379 条未仲裁。
