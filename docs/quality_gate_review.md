# 质量门禁 v1 终审（t118）— quality_gate 合成判定

> 审查人：质量审查员（独立第三方，不参与实现）　日期：2026-11-08 22:08–22:30
> 对象：t116（quality_gate v1）+ t117 验收 + t148/t150 修复 + t151 round-3 验收
> 依据：`PUNCT_EVAL.md` v1.3（§5.2 阈值、§6.4.8 data_missing）、`CONTENT_EVAL.md` v1.1（§6.2/§6.3、§6.4 data_missing）、`docs/quality_gate_v1.md`
> **结论：PASS（有条件）** —— 门禁判定/阈值与 spec 一致、无书专属分支、verify_vert/punct_eval 判据未被改动、三类反例实测正确、输出字段齐全可序列化；残留为报告呈现层问题（非阻断，见 §5）。

---

## 1. 复跑（任务给定命令）

```bash
/usr/bin/python3 src/tools/quality_gate.py --book wz7 \
  --pdf output/wz7_full/wz7_full_v51.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --gold data/punct_eval/punct_gold_v1.json --out tmp_vert/gate/review_wz7.json
# [quality_gate] wz7: verify=PASS punct=REJECT content=REJECT -> REJECT   (exit 0, 18.4s)
```

- **wz7**：verify PASS（1748/1748、字符量 98.8%、越界 0、整页丢失 0）；punct REJECT（P 0.9449 / R 0.9504，TP 652/FP 38/FN 34）；content REJECT（CER 0.0961 / han_only 0.0570，must_pass=True）→ **REJECT**；reasons `["punct_regression","content_over_manual","component_reject"]`。
- **wz6**（同命令换书）：verify PASS（231/231、97.2%、越界 0、丢失 0）；punct **MANUAL**（P 0.7879/R 0.4099，TP 182/FP 49/FN 262；`data_missing=true`，gold 450 vs input/product 236，ratio 0.5244，anchor 0.9718）；content REJECT（CER 0.1371 / han_only 0.0354；`must_pass_applicable=false`、`must_pass_status=not_applicable`、page coverage 5.93%）→ **MANUAL_ONLY**；reasons `["data_missing","content_over_manual"]`。
- **单测**：`pytest src/test/unit/test_quality_gate.py -q` → **18 passed**。
- 输出 JSON 可 `json.load` 回读；同名 `.md` 摘要已生成（`review_wz7.md` 1.5KB / `review_wz6.md` 2.8KB）。

---

## 2. spec 一致性（阈值/判定）

| spec | 要求 | 实现 | 结论 |
|---|---|---|---|
| PUNCT_EVAL §5.2 | 句读 auto P≥0.98/R≥0.96、manual P≥0.92/R≥0.88；引号/括号/破折号/省略号/书名号/ring auto P≥0.98/R≥0.95、manual P≥0.90/R≥0.85 | `PUNCT_TIERS` 完全一致（sentence 0.98/0.96–0.92/0.88；其余 0.98/0.95–0.90/0.85；bracket_type 0.97/0.95–0.90/0.85） | ✓ |
| PUNCT_EVAL §5.2 判定 | 全部 auto→AUTO；全部 ≥manual→MANUAL；任一低于 manual→REJECT | `judge_punct` 同逻辑（零样本类跳过；data_missing 且未达 auto → MANUAL） | ✓ |
| PUNCT_EVAL §6.4.8 | data_missing：product≤0.75 且 input≤0.75 且 anchor≥0.80 → MANUAL_ONLY；input>0.75 而 product 低 → product_regression REJECT | `DATA_MISSING_TIERS` 0.75/0.75/0.80；wz6 实测 classification=data_missing；代码含 product_regression 分支（t151 已用反例验证） | ✓ |
| CONTENT_EVAL §6.2/§6.3 | CER_with_punct ≤0.020/0.050、CER_han_only ≤0.015/0.040、missing/wrong ≤0.010/0.030、extra ≤0.005/0.020；must-pass 64/54 | `CONTENT_TIERS` 完全一致；must_pass 不适用（`must_pass_applicable=false`）时不误判 | ✓ |
| CONTENT_EVAL §6.4 | data_missing 同判据（内容侧） | 复用 §6.4.8 的检测结果（同一 `detect_data_missing`） | ✓ |
| 组合判定 | verify FAIL→REJECT；分项 REJECT→REJECT；分项 MANUAL/UNSCORED→MANUAL_ONLY；全 AUTO→AUTO_PASS | `combine()` 与之一致 | ✓ |
| 无书专属阈值 | 同一套阈值/无书分支 | `grep 'wz6\|wz7\|book =='` 仅注释；thresholds 块 wz6/wz7 完全相同；阈值来源字符串登记 PUNCT_EVAL §5.2/§6.4.8 + CONTENT_EVAL §6.2/§6.3 | ✓ |

> 说明：§5.2 中 value_accuracy/length/direction/pair F1 等附加判据未被门禁消费——因为 punct_bench（B 口径）未输出这些指标（见 t147 R1，out-of-contract）；门禁当前只消费 P/R，与 `THRESHOLDS_SOURCE` 的注明一致，属已知遗留（F3）。

---

## 3. 判据未被改动 / 只做合成

- `src/test/verify_vert.py` sha256 `cc8b6937…`，`git status` 无修改 → 判据未动；quality_gate 通过 `subprocess.run([python, verify_vert.py, ...])` 调用（punct_eval 不内联重写）。
- `src/tools/punct_eval.py` sha256 `3fb10c41…`（与 t147 相同，thin wrapper → punct_bench.main）。
- `src/tools/punct_bench.py` sha256 `9829cbce…`：t150 为门禁补 `by_page`/`errors`（**输出字段**），序列指标与 t147 基线完全一致（P 0.9449 / R 0.9504，652/38/34）→ 判据未变，仅增加可观测字段。
- `quality_gate.py` 只做：调用三类评测器 + 阈值映射（`judge_punct/judge_content/combine`）+ 报告定位（`locate_punct_missing`/`over_limit_pages`），未重写阅读序/对齐/CER 算法。

---

## 4. 反例复核（每类 ≥1，实测）

| # | 类别 | 构造 | 实测 | 判定 |
|---|---|---|---|---|
| 1 | **verify** | wz6 产物（231 页）配 wz7 coords/lines（1748 页） | verify `pass_=false`，pages 231 / pages_src 1748、字符量 65.9%、page_loss 1 → **REJECT**，reasons `["verify_fail"]` | ✓ |
| 2 | **标点** | wz7（正常） | punct REJECT（dash P/R 0/0、colon P 0.8281<0.92 低于 manual）→ 分项 REJECT | ✓ |
| 3 | **标点-data_missing** | wz6（上游 OCR 缺标点） | punct MANUAL（classification=data_missing，ratio 0.5244，anchor 0.9718）→ 门禁 MANUAL_ONLY | ✓ |
| 4 | **内容** | wz7 / wz6 | content REJECT（CER 0.0961 / 0.1371 > manual 0.050）；over_limit_pages 含 page/column/char_pos/gold_char/product_char | ✓ |
| 5 | **must-pass 不适用** | wz6 用 wz7 must-pass 清单 | coverage 5.93% → `must_pass_applicable=false`、`must_pass_status=not_applicable`、`must_pass_fail_items=[]`，content 判定不被 must-pass 拉低 | ✓ |

---

## 5. 残留 findings（非阻断，报告呈现层）

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F1** | medium | `punct.failures` 含**零样本类**：wz6 报 `booktitle_open/close` P/R 0.0（wz6 无书名号 gold；`judge_punct` 已跳过该类，但报告列表未跳）→ 交付报告会误显示「书名号全错」 | failures 生成时剔除 tp+fp+fn==0 的类（与 judge_punct 一致），或标 `applicable:false` |
| **F2** | low | `content.metrics.must_pass_items` 在 `must_pass_applicable=false` 时仍输出 64 条 wz7 坐标（expected_xy 出现 y=48272 等越界值） | 不适用时置空/省略，或逐条标 not_applicable |
| **F3** | low | §5.2 的 value_accuracy/length/direction/pair F1 判据未入门禁（punct_bench 未输出，t147 R1 out-of-contract） | 待 punct 指标补齐后接入；当前在 `thresholds_source` 注明只消费 P/R |
| **F4** | low | reasons 命名 `punct_regression` 实为「低于 manual 档」，非相对基线回归，易被交付报告误读 | 改名为 `punct_below_manual`（或附加说明） |
| **F5** | low | `punct` 块只有失败类（failures），完整 `by_class` 不在门禁 JSON 顶层（在 punct 子块的 sequence/per_class 内）；交付报告需自取 | 顶层输出 `punct.by_class` 汇总（或文档注明路径） |

---

## 6. 输出可用性（scan2pdf 质量报告）

- 顶层：`version:"quality-gate-v1"`、`book`、`pdf_sha256`、`thresholds`、`thresholds_source`、`expect_low{pages,source}`、`metrics{verify,punct,content}`、`verdict`、`reasons`、`gate{verdict,reasons,verify_pass,punct_verdict,content_verdict,data_missing,top_failures,note}`、`verify/punct/content` 明细；JSON 可序列化、可回读；同名 markdown 摘要已生成。
- 明细可定位：`punct.pages_with_fn` 含 page/column/char_pos/gold_char（wz7 p57 c1 q9 `—`、p97 c0 q0 `『`；wz6 p7 c0 q8 `，`）；`content.over_limit_pages` 含 page/column/char_pos/gold_char/product_char；`content.must_pass_*` 含 page/ch/pos/column/reason。
- **可用于交付报告** ✓（F1/F2 修掉后更干净）。

---

## 7. 结论

**Verdict: PASS（有条件）**。

- **通过**：阈值与 §5.2/§6.2/§6.4.8 一致；判定逻辑与 spec 档位一致；无书专属阈值/分支；verify_vert/punct_eval 判据未动（punct_bench 仅增输出字段，指标不变）；三类反例（verify/punct/content）+ data_missing + must-pass 不适用均实测正确；输出字段齐全可序列化、有 markdown 摘要；18 单测通过。
- **条件/残留**：F1（failures 含零样本类，medium）建议在交付前修；F2–F5 为低风险呈现/命名问题。
- **门禁口径**：punct B 与 content 阈值均为 **provisional**（`thresholds_source` 已注明），v2 gold 标定前只作趋势/交付参考，不得据此开 auto 或作为最终验收。

---

## 8. 复现

```bash
cd /opt/test
# wz7（任务给定）
/usr/bin/python3 src/tools/quality_gate.py --book wz7 --pdf output/wz7_full/wz7_full_v51.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --gold data/punct_eval/punct_gold_v1.json --out tmp_vert/gate/review_wz7.json
# wz6
/usr/bin/python3 src/tools/quality_gate.py --book wz6 --pdf output/wz6/wz6_vert_full.pdf \
  --coords data/wz6/wz6_spotting_coords.json --lines data/wz6/wz6_spotting_lines.json \
  --gold data/punct_eval/punct_gold_v1.json --out tmp_vert/gate/review_wz6.json
# verify 反例（页数不符）
/usr/bin/python3 src/tools/quality_gate.py --book wz7 --pdf output/wz6/wz6_vert_full.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --gold data/punct_eval/punct_gold_v1.json --out /tmp/gate_verifyfail.json
# 单测
/usr/bin/python3 -m pytest src/test/unit/test_quality_gate.py -q   # 18 passed
```

| 文件 | sha256 / 说明 |
|---|---|
| `src/tools/quality_gate.py` | `4bf0bfc943954253744e8336503052b45c33fa7878ffe81500ee17fb64fc9d29` |
| `src/tools/punct_bench.py` | `9829cbce62ebb1baa9e680cde19da8fa447ed3a70535a7faa6190bdf6b4a7a2b` |
| `src/tools/punct_eval.py` | `3fb10c41e99f37e6e44724c3f873fc2e10815973a2674c3ecfed1b7084a62312` |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588`（git 无修改） |
| `output/wz7_full/wz7_full_v51.pdf` | md5 `38d6656bf37720ff0277d7bd74a5d87a` |
| `tmp_vert/gate/review_wz7.json` / `review_wz6.json` | 本次复跑输出（REJECT / MANUAL_ONLY） |
| HEAD | `84d6b95`（未 commit） |
