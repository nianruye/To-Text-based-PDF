# punct_eval 序列口径 独立验收（t145 · round 3）

> 验收人：验证评审员（独立验证方）　日期：2026-11-08 23:10–23:40
> 对象：t144（sequence 口径修复：类型错 FP/FN 计数 + 默认 A 对照加载）
> 基线：HEAD `84d6b95`（未 commit）；**未改实现/数据、未 commit**
> 证据：`src/tools/punct_bench.py`（`7becd43d…`）、`src/tools/punct_eval.py`（`3fb10c41…`）、`test_punct_bench.py`（`2f5b8ea5…`）、`/tmp/pseq/`

---

## 0. 结论

**PASS**（round-2 的 F1/F2 已修复，全部验收项成立）：

- 两次复跑完全一致（JSON md5 `699ace6a09550780a91ae18a392ed23c`）：**TP 634 / FP 42 / FN 52 → P 0.9379 / R 0.9242**，unscorable 0、swaps 0。
- 抽 p57/p704 手工重建阅读序：**无页眉/页码**（`金瓶梅一四四`、`三` 等已排除），列序右→左、列内上→下正确；8 页扫描均无 header-like 列。
- 手算 p57 **TP63/FP2/FN3 P0.9692/R0.9545**、p704 **TP60/FP12/FN14 P0.8333/R0.8108**，与工具 by_page **逐类一致（0pp）**。
- 反例全部符合预期：串尾相同 → period TP1；漏 1 开引号 → quote_open FN+1；误插 1 句号 → period FP+1；**换 1 类型 → comma FN+1（FP 0）、period FP+1、confusion `comma>period:1`**（t144 已去掉 gold 类多余 FP）。
- **ab_diff 默认已加载 `tmp_vert/bench/cell_v51.json`**：`gt5pp` 4 条（quote_open P/R −7.46/−10.14pp、quote_close −10.77/−12.12pp），无需显式参数。
- pytest **28 passed**。

残留仅低风险观察（F1–F3），不影响验收结论。

---

## 1. PASS/FAIL 总表

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 两次一致；抽 2 页重建阅读序，无页眉/页码、列序对 | **PASS** | md5 相同；p57/p704 无 header-like；8 页扫描全清；列序正确 |
| 2 | 手算 2 页 P/R 与工具差 ≤2pp | **PASS（0pp）** | p57 63/2/3；p704 60/12/14 —— 与工具逐类一致 |
| 3 | 反例：漏 1 引号、误插 1 句号、换 1 类型 → TP/FP/FN 符合预期 | **PASS** | 漏引号 quote_open fn0→1；插句号 period fp1→2（base tp1）；换类型 comma fp0/fn1、period fp1、confusion 1 |
| 4 | 与 cell 差异 >5pp 类别列出原因 | **PASS** | 默认 ab_diff 4 条（quote_open/close P/R），原因 page_set_diff（A=3 页 demo vs B=8 页 content gold）+ B 对齐/漏检；见 §5 |
| 5 | 报告 docs/punct_eval_seq_acceptance.md；不改实现/数据；不 commit | **PASS** | 本文件；只读；未 commit（HEAD `84d6b95`） |

---

## 2. 阅读序重建（p57 / p704，手工）

方法：v51 PDF `rawdict`；y 边带 8% 过滤字符 + 列级「x 边带 8% 且 header-like」/「header-like 且 ≤6 字」排除（`PAGE_NUM_RE`/`^金瓶梅[数字]*$`）；竖排 x 聚类右→左、列内 y 上→下。

| 页 | 列数（产物/gold） | 首列 | 末列 | 页眉/页码 | 判定 |
|---|---|---|---|---|---|
| p57 | 14 / 16 | `論金瓶梅這部書——導讀` | `…修元記、` | 无（原 `三` 已排除） | 列序对；列数差为短列合并（F2） |
| p704 | 17 / 18 | `吳銀兒唱：` | `…一個兒北去。﹂` | 无（原 `金瓶梅一四四` 已排除） | 列序对（F2） |

8 页扫描（p57/97/159/704/705/830/898/1718）：均无 header-like 列。

---

## 3. 手算 P/R 对照

| 页 | 我（独立实现） | 工具 by_page | 差 |
|---|---|---|---|
| 57 | TP63 / FP2 / FN3，P **0.9692** / R **0.9545** | 同 | 0pp |
| 704 | TP60 / FP12 / FN14，P **0.8333** / R **0.8108** | 同 | 0pp |

> 逐类一致：comma 239/4/9、period 122/8/14、quote_open 62/5/7、quote_close 58/7/8、colon 50/14/8、bracket 31/3/4、ring 23/0/0、enumeration 14/0/0…

---

## 4. 反例（`punct_bench.sequence_eval`）

| 反例 | gold → pred | 期望 | 实测 |
|---|---|---|---|
| 串尾相同 | `甲乙。` → 同 | period TP1 | **tp1/fp0/fn0** ✓ |
| 漏 1 个开引号 | `甲「乙」丙。` → `甲乙」丙。` | quote_open FN+1 | tp0/fn1 ✓ |
| 误插 1 个句号 | `甲「乙」丙。` → `甲「乙」。丙。` | period FP+1 | period tp1/fp1 ✓ |
| 换 1 个类型 | `甲，乙。` → `甲。乙。` | comma FN+1、period FP+1 | comma **tp0/fp0/fn1**、period **tp1/fp1/fn0**、confusion `comma>period:1` ✓ |

> 与 t143 对照：类型错不再给 gold 类多记 FP（comma fp 1→0），overall FP 44→42。

---

## 5. 与 cell 口径差异（ab_diff，默认加载）

| 类/指标 | cell | seq | Δ | 原因 |
|---|---|---|---|---|
| quote_open.precision | 1.0 | 0.9254 | **−7.46pp** | A/B 页集不同（A=3 页 demo；B=8 页 content gold，主因）；B 对齐/漏检（quote_open FN 7） |
| quote_open.recall | 1.0 | 0.8986 | **−10.14pp** | 同上 |
| quote_close.precision | 1.0 | 0.8923 | **−10.77pp** | 同上；B 闭引号漏检/页尾 |
| quote_close.recall | 1.0 | 0.8788 | **−12.12pp** | 同上 |

- `ab_diff.cell_json = tmp_vert/bench/cell_v51.json`、`page_sets_differ=true`；默认命令即输出 4 条，不再需要 `--ab-cell-json`（F1 已修）。
- A/B 页集不同，不能直接比较；B 为主指标（spec v1.3）。

---

## 6. 复现 / 字节绑定

```bash
cd /opt/test
/usr/bin/python3 src/tools/punct_eval.py --mode sequence --gold data/punct_eval/content_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --book wz7 --out /tmp/pseq/t1.json
# -> tp=634 fp=42 fn=52 P=0.9379 R=0.9242；两次 md5 相同
/usr/bin/python3 -m pytest src/test/unit/test_punct_bench.py -q   # 28 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/punct_bench.py` | `7becd43df4eb09e3c724bb73256b797dc3e2bfd04a42e7adbc72f3be44b201d1` |
| `src/tools/punct_eval.py` | `3fb10c41e99f37e6e44724c3f873fc2e10815973a2674c3ecfed1b7084a62312` |
| `src/test/unit/test_punct_bench.py` | `2f5b8ea5d2f6591184b813edb9c5543817933405693039dae7fc05e4b9390370` |
| `output/wz7_full/wz7_full_v51.pdf` | `38d6656bf37720ff0277d7bd74a5d87a` |
| `/tmp/pseq/t1.json` = t2 | md5 `699ace6a09550780a91ae18a392ed23c` |
| HEAD | `84d6b95`（未 commit） |

---

## 7. 残留观察（低）

- **F1（低）**：ab_diff 的 `reason` 统一为 `page_set_diff`；spec §6.4.5 允许的原因枚举还包括对齐/漏检/转录。建议对 quote 类补充「B 对齐/漏检（quote_open FN 7、quote_close FN 8）」说明（报告已列）。
- **F2（低）**：产物列数 p57 14 / p704 17 vs gold 16/18（标题、署名等短列被产品合并）；列序单调、指标不受影响，属版面差异。
- **F3（低）**：B gold 仅 8 页（content gold provisional）且无 heldout；正式标定需 v2 gold（t111）。

## 8. 结论

**t145 验收通过（PASS）**：阅读序（无页眉/页码、列序正确）、手算 P/R（0pp）、反例（含类型错修正）、ab_diff（默认 4 条）均成立；无阻塞问题。低风险观察转入 v2 gold 标定与版面差异登记。
