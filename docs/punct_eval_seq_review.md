# 序列口径终审（t141 → t146 修复 → t147 round-2）

> 审查人：质量审查员（独立第三方，不参与实现）　日期：2026-11-08 21:34–22:20
> 对象：t139（sequence 口径实现）+ t140 验收 + t142/t144 修复 + t145 验收 + **t146 修复轮**
> 依据：`spec/governance/PUNCT_EVAL.md` v1.3（§6.4 口径 B）
> **Round-2 结论：PASS（有条件）** —— t146 已修复首轮 F1（书专属规则）、F3（§6.4.7 输出字段）、F5（order_swaps 口径）、F6（聚类阈值/家具剔除）；主命令可复现、无坐标依赖、抽样判定正确、A/B 并列、32 单测通过。首轮 F2/F4/F7 经系统标记为 **out-of-contract（归用户）**，本报告作为残留记录，不阻断本轮通过。

---

## 1. 复跑与确定性

```bash
/usr/bin/python3 src/tools/punct_eval.py --mode sequence \
  --gold data/punct_eval/content_gold_v1.json --pdf output/wz7_full/wz7_full_v51.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --book wz7 \
  --out tmp_vert/bench/seq_review2.json
# [punct_eval:sequence] pages=8 unscorable=0 tp=652 fp=38 fn=34 P=0.945 R=0.950 swaps=0
# exit 0
```

- **确定性**：两次运行 md5 相同（`1e6b706b5a0b956595993f7f3938089e`）。
- **单测**：`pytest src/test/unit/test_punct_bench.py -q` → **32 passed**。
- **基线**（8 wz7 页）：**TP 652 / FP 38 / FN 34 → P 0.9449 / R 0.9504**，unscorable 0、swaps 0（t145：634/42/52 → t146 修复后 +18 TP、−4 FP、−18 FN）。
- 逐页：p57 61/4/5、p97 120/1/1、p159 24/5/6、p704 61/12/13、p705 67/6/3、p830 113/8/6、p898 116/2/0、p1718 90/0/0。
- 逐类：comma 246/2/2、period 127/8/9、quote_open 65/2/4、quote_close 58/10/8、colon 53/11/5、bracket 31/3/4、ring 23/0/0、question 16/0/0、enumeration 13/1/1、semicolon/exclamation 10/10、dash 0/1/1。

---

## 2. t146 修复项验证（首轮 findings → 现状）

| 首轮 id | 状态 | 证据 |
|---|---|---|
| **F1 high** 书专属页眉规则 | **已修** | `grep 金瓶梅 src/tools/punct_bench.py` **0 命中**（仅测试数据中出现，且测试断言「金瓶梅不再特判」）；改为 `_is_furniture()`：页码（阿拉伯/汉字/圈码/罗马）+ 通用页眉（第X回/章/節/頁/卷、卷X、上/下卷、目錄），长度 ≤6；仅「短家具 span 且中心在 8% 边带」才剔除，正文长列入带保留 |
| **F3 high** §6.4.7 输出字段缺失 | **已修** | 输出含 `method:"B_sequence"`、`dataset_id`、`gold_source:"content_gold(t111/provisional)"`、`normalization:"content-N0"`、`by_class`（=per_class）、`reading_order{pages,unscorable,excluded_furniture}`、`gate{status:"provisional",thresholds_version:"v1.2",auto_enabled:false}`、`errors`、`ab_diff.by_class/gt5pp{delta,causes}`；cell 口径保留 `mode` + `method:"A_cell"` |
| **F5 medium** order_swaps 恒 0 | **已修** | 新增 `order_swaps_definition`（同 gap 多 tokens 按序列配对并计逆序；跨 gap 恒 0）；实测 `甲「」乙` vs `甲」「乙` → **swaps=1**，tp2；文档/JSON 声明口径 |
| **F6 medium** 聚类阈值/边带剔除偏离 spec | **已修** | `tol = max(1.2×中位字高, 0.5×中位 span 高)`（punct_bench.py:515-519）；家具剔除改为「短 span 且中心在 8% 边带」；逐页复核：p57/97/159/704/705/830/898 的 `reading_order` 长度 == PDF 字符数（**无误剔正文**），p1718 剔除 3 字（页码列 `五四八`，excluded_furniture=1，正确） |
| 无坐标依赖 | 保持 | sequence 路径不读 coords/lines；gold 只取 text/axis/exclude 并 `--book` 过滤 |
| A/B 并列 | 保持 | `--mode` 分离；`ab_diff` 默认读 `cell_v51.json`，`page_sets_differ=true`，gt5pp 3 条（quote_open recall −5.8pp、quote_close precision −14.71pp/recall −12.12pp，`causes:["page_set_diff"]`） |

**回归观察（低）**：p57 由 t145 的 63/2/3 变为 61/4/5（TP−2、FP+2、FN+2），其余页持平或改善；总体净改善 +18 TP。p57 的聚类/家具改动对标题大字号列有轻微影响，建议登记但非阻断。

---

## 3. 抽样复核（6 例，含类型错/顺序换位）

| # | 用例 | gold → pred | 实测 | 判定 |
|---|---|---|---|---|
| 1 | 完美/串尾 | `甲「乙」丙。` → 同 | tp3 | ✓ |
| 2 | 漏开引号 | `甲「乙」` → `甲乙」` | quote_open fn1 | ✓ |
| 3 | 误插句号 | `甲。乙` → `甲。乙。` | period tp1/fp1 | ✓ |
| 4 | 类型错 | `甲，乙。` → `甲。乙。` | comma fn1、period tp1/fp1、confusion comma>period:1 | ✓（t144 修复保持） |
| 5 | 同 gap 顺序换位 | `甲「」乙` → `甲」「乙` | **swaps=1**、tp2 | ✓（t146 修复） |
| 6 | 跨 anchor 换位 | `甲「乙」「丙」` → `甲「丙」「乙」` | swaps=0、tp2/fp2/fn2（anchor 变化 → 计错位） | ✓（符合 §6.4.6 局限 4：同 gap 内错位 B 不可发现；跨 anchor 变化按 FP/FN 计） |

---

## 4. 残留（out-of-contract，系统标记归用户；本轮不阻断）

| id | severity | problem | 建议 |
|---|---|---|---|
| **R1**（原 F2） | medium | §6.4.4 指标缺项：引号/书名号**组级 pair P/R**、**macro**、**by_split**、括号类型/书名号双单/引号单双混淆维度、dash/ellipsis **value_accuracy** 均未实现（dash `value_total=0`；confusion 仅 class→class） | 补齐 §6.4.4；B 作为能力主指标前建议完成 |
| **R2**（原 F4） | medium | sequence CSV 仍不合规：表头 `mode`（spec 要 `method`）、**class 列全空**（rows 写 `cls`，`write_csv` 读 `class`）、split 列空 | 统一 `method/class/split` 键并补 by_split 行 |
| **R3**（原 F7） | low | gold 页在 PDF 缺失时静默全 FN（无 `errors`/unscorable）；`pages` 字段仍为 `[]`；per_class 非固定排序；`ab_diff.gt5pp.causes` 仅 `page_set_diff`（未按 §6.4.5 七类细分） | 缺页进 errors/unscorable 或 exit 3；pages 填 by_page；固定排序；细分 causes |
| **R4** | low | content gold 缺 `exclude` 字段 → p704 书眉列 `金瓶梅一四四` 未被剔除（阅读序文本以它开头；因无标点，对 P/R 影响小，但锚点串含家具） | 给 content gold 补 `exclude`（数据任务），或接受为数据缺口登记 |
| **R5** | low | p57 单页指标较 t145 轻微回退（63/2/3 → 61/4/5），t146 报告未逐页对照 | 报告补逐页对照（总体净改善 +18 TP 可接受） |

---

## 5. 验收对照（t147）

| 验收项 | 状态 | 证据 |
|---|---|---|
| 对照 v1.3 审查阅读序/对齐/指标；无坐标依赖 | **通过（指标有 R1 残留）** | 阅读序 = spec 公式 + 书无关家具；对齐 = §6.4.3 gap 法；无坐标依赖 ✓；指标缺项见 R1（out-of-contract） |
| 无书专属白名单；gold provisional 如实；与 cell 口径并列 | **通过** | 代码无书名/页号白名单；`gold_source=content_gold(t111/provisional)`、`gate.status=provisional`；A/B 并列 |
| 抽样 ≥5（含顺序换位、类型错） | **通过** | 6 例见 §3 |
| 输出可被 quality_gate 消费（mode/sequence metrics/verdict 字段稳定） | **通过** | `method`/`mode`/`by_class`/`gate.status`/`errors`/`ab_diff` 稳定；`verdict` 以 `gate.status=provisional` 表达（spec §6.4.7 字段），建议后续补 `verdict` 别名（R-低） |
| 出具报告 verdict + findings | **通过** | 本文件 |

---

## 6. 复现命令

```bash
cd /opt/test
# 主命令（§1）
/usr/bin/python3 src/tools/punct_eval.py --mode sequence --gold data/punct_eval/content_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --book wz7 --out tmp_vert/bench/seq_review2.json
# 单测
/usr/bin/python3 -m pytest src/test/unit/test_punct_bench.py -q   # 32 passed
# 抽样（§3）
/usr/bin/python3 - <<'PY'
import sys; sys.path.insert(0,'src/tools')
from punct_bench import sequence_eval
for g,p in [('甲「乙」丙。','甲「乙」丙。'),('甲「乙」','甲乙」'),('甲。乙','甲。乙。'),
            ('甲，乙。','甲。乙。'),('甲「」乙','甲」「乙'),('甲「乙」「丙」','甲「丙」「乙」')]:
    r=sequence_eval(g,p); print(g,p,r['overall'],r['order_swaps'],r['confusion'])
PY
# 书无关确认
grep -n "金瓶梅" src/tools/punct_bench.py || echo "no book-specific rule"
```

| 文件 | sha256 / 说明 |
|---|---|
| `src/tools/punct_eval.py` | `3fb10c41e99f37e6e44724c3f873fc2e10815973a2674c3ecfed1b7084a62312` |
| `src/tools/punct_bench.py` | `d165d90c0a1432de8ba430a83b29a821880b832461a881e5875b3e9bd56416a2`（t146） |
| `src/test/unit/test_punct_bench.py` | `cee895849d2b19b56249d9e81c5042e9e81122bdd77e3bddeb0766475c9585e4`（t146） |
| `output/wz7_full/wz7_full_v51.pdf` | md5 `38d6656bf37720ff0277d7bd74a5d87a` |
| `tmp_vert/bench/seq_review2.json` | md5 `1e6b706b5a0b956595993f7f3938089e`（8 页 / 652/38/34） |
| HEAD | `84d6b95`（未 commit） |

---

## 7. 结论

**Round-2 verdict：PASS（有条件）**。

- **通过**：t146 已按 spec 修复首轮 F1/F3/F5/F6；主命令可复现（652/38/34，P 0.9449/R 0.9504）；无坐标依赖；无书专属规则；A/B 并列；抽样 6 例（含顺序换位/类型错）判定正确；32 单测通过。
- **条件/残留**：R1（§6.4.4 指标缺项：pair/macro/by_split/类型混淆维度/dash 值）、R2（CSV class 列空）、R3（缺页/pages/causes 细分）为系统标记的 out-of-contract 项，归用户决定是否在下一轮处理；R4（content gold 无 exclude → p704 书眉未剔）与 R5（p57 单页轻微回退、报告未逐页对照）为低风险观察。
- **门禁口径**：B 仍为 provisional（`gate.status=provisional`、`auto_enabled=false`）；在 v2 gold 前，B 分数只作能力主指标与回归趋势，不得开启 auto。

---

## 附录：Round-1（t141）结论存档

首轮 verdict=needs_revision（FAIL）：F1 书专属 `HEADER_RE=^金瓶梅…$`；F2 §6.4.4 指标缺项；F3 §6.4.7 输出字段缺失且无 gate/verdict；F4 CSV class 列空；F5 order_swaps 恒 0；F6 阅读序偏离 spec（聚类阈值/边带/罗马数字）；F7 缺页静默全 FN 等。t146 修复 F1/F3/F5/F6，F2/F4/F7 由系统标记为 out-of-contract。
