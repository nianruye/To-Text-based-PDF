# content_eval v1.1 独立验收（t126 · must-pass 64+54）

> 验收人：验证评审员（独立验证方）　日期：2026-11-08 19:05–19:35
> 对象：t125（content_eval 口径调整：B 方案：must-pass 64+54，118/4 diagnostic）
> 基线：HEAD `84d6b95`（未 commit）；**未改实现/数据/fix JSON/output、未 commit**
> 证据：`src/tools/content_eval.py`（最终版 sha256 `1affeb0b…`）、`src/test/unit/test_content_eval.py`（`f53bb5d5…`）、`/tmp/cev2/`、`tmp_vert/bench/content_v51_v11.json`

---

## 0. 结论

**PASS（B 方案口径实现正确）**，但发现 t125 的**存档基线/汇报数字与最终实现不一致**（F1）：

- **must-pass 只含 64 缺字 + 54 ring**：`regression.must_pass_items = {missing_char_confirmed, battle4_ring}`，`must_pass` 仅由两者全过决定；**118/4 在 `diagnostics`**，不参与 verdict。
- **最终实现结果**（`content_eval.py` = `1affeb0b…`）：**64/64 + 54/54 → must_pass True**；两栏 CER **0.1202 / 0.0259（PDF 口径）**；pytest **11 passed**。
- **反例**：删 1 条 must-pass 缺字 → `63/63 + 54/54 → must_pass False`（REGRESSION_BLOCKED 生效）；删 1 条 diagnostic（t97 i=36）→ `must_pass True` **不变**。
- **t125 依赖结果/存档基线是旧中间版**：`tmp_vert/bench/content_v51_v11.json` 记录 must False、CER 0.0997/0.0519（lines）、t97 4/1；与最终实现（True、0.1202/0.0259、3/0）不一致 → **基线需用最终版重生成**（F1，中）。
- **10/64 独立核对**：10/10 期望字在产物 PDF 存在（9 条 ≤0.5 格；p1703 四在「四制錢」位置、cell 偏 1.56 格，非缺字）→ v1.1 的 64/64 判定**正确**。
- **两栏 CER**：gold 仅 p703（demo，1 页，无法按「2 页」抽；如实登记）；PDF 手算 **0.1202 / 0.0259** 与最终版 eval **一致**。

---

## 1. PASS/FAIL 总表

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 复跑 t125：must-pass 只含 64 缺字 + 54 ring；118/4 在 diagnostic 且不影响 verdict | **PASS** | `regression.must_pass_items` 仅 64+54；`diagnostics.{typo_t97,missing_char_all}` 独立；最终版 64/64 + 54/54 → True |
| 2 | 独立核对 must-pass 计算：抽 10 条 64 用页内上下文自核 | **PASS** | 10/10 期望字在 PDF 存在（9 ≤0.5 格、p1703 四 1.56 格但上下文「四制錢」正确）；v1.1 64/64 正确 |
| 3 | 反例：must-pass 少 1 → REGRESSION_BLOCKED；diagnostic 少 1 → verdict 不变 | **PASS** | 删 1 缺字：63/63+54/54 → **False**；删 t97 i=36：64/64+54/54 → **True**（diagnostics 3→2） |
| 4 | 两栏 CER 与 t125 输出一致（抽 2 页） | **PASS（1 页，限制登记）** | gold 仅 p703（1 页）：PDF 手算 0.1202/0.0259 = 最终版 eval；t125 存档 0.0997/0.0519 为旧 lines 口径（F1） |
| 5 | 报告 docs/content_eval_acceptance_v11.md；不改实现；不 commit | **PASS** | 本文件；只读；未 commit（HEAD `84d6b95`） |

---

## 2. must-pass 结构与最终结果

- 最终版 CLI：`/usr/bin/python3 src/tools/content_eval.py ... --out /tmp/cev2/real3.json`
  - `regression.must_pass_items.missing_char_confirmed`: **64/64**
  - `regression.must_pass_items.battle4_ring`: **54/54**
  - `regression.must_pass`: **True**
  - `diagnostics.typo_t97`: `status=unmaterialized, count=118, materialized_total=3, materialized_passed=0`（i=1/15/36；i=26 已按 t123 裁定为假项并剔除）
  - `diagnostics.missing_char_all`: 160 条（仅诊断）
- 口径核对：`must_pass` 布尔仅由 `total==passed==64/54` 决定；diagnostic 字段不参与（代码 `must = bool(mc_res['total'] == mc_res['passed'] == 64 and ring_res['total'] == ring_res['passed'] == 54)`）。

---

## 3. 10 条 64 清单独立核对（PDF 字符坐标 + 期望格）

| 页 | 期望字 | 最近距离（格） | 判定 |
|---|---|---|---|
| 634 | 籤 | 0.05 | PASS |
| 50 | 竊 | 0.04 | PASS |
| 85 | 峴 | 0.26 | PASS |
| 105 | 逕 | 0.15 | PASS |
| 213 | 颳 | 0.15 | PASS |
| 411 | 粧 | 0.63 | PASS |
| 469 | 青 | 0.08 | PASS |
| 527 | 宿 | 0.38 | PASS |
| 987 | 於 | 0.06 | PASS |
| 1703 | 四 | 1.56 | PASS（「四制錢」上下文正确；cell/枚举位置偏移，非缺字） |

> 方法：不按 lines/pos 直比；在 v51 PDF `rawdict` 字符坐标中找期望字，量其与 fix JSON `cell` 中心的纵向距离（格高归一）。10/10 均存在；v1.1 的「全过」与之一致。

---

## 4. 反例（门禁语义）

| 反例 | 输入 | 结果 | 结论 |
|---|---|---|---|
| must-pass 少 1 | `/tmp/cev2/fix_mc_minus1.json`（删 1 条 shape&complete missing_char） | mc **63/63**、ring 54/54 → `must_pass=False` | **REGRESSION_BLOCKED 生效** ✓ |
| diagnostic 少 1 | `/tmp/cev2/meta_minus1.json`（删 t97 i=36） | mc 64/64、ring 54/54 → `must_pass=True`；diagnostics materialized 3→2 | **verdict 不变** ✓ |
| 全量（基线） | 原始 fix JSON + 原 meta | 64/64 + 54/54 → True；diagnostics 3 | 基线 PASS |

> 反例输入均在 `/tmp/cev2/`，未改仓库数据。

---

## 5. 两栏 CER 复核

- **gold 现状**：`data/punct_eval/content_gold_v1.json` 仅 **p703**（demo；无法抽 2 页）。
- **最终版 eval（PDF 口径）**：with_punct **0.1202**（341/41，miss 3/wrong 38/extra 0）、han_only **0.0259**（270/7，miss 0/wrong 2/extra 5）。
- **我的独立手算（PDF 文本，N0）**：with_punct **0.1202**、han_only **0.0259** → 与 eval **一致**（误差 0）。
- **t125 存档值**（`content_v51_v11.json`）：0.0997/0.0519 = **lines 口径**（旧中间版），与最终版不一致（F1）。

---

## 6. 关键发现

- **F1（中，t125 交付一致性）**：`tmp_vert/bench/content_v51_v11.json` 与 t125 汇报仍是**旧中间版**（must False、CER lines 0.0997/0.0519、diagnostics 4/1）；最终版（`1affeb0b…`）为 must True、CER 0.1202/0.0259、diagnostics 3/0。**需用最终版重生成基线并更新汇报/PR 数字**，否则下游会误读为 REGRESSION_BLOCKED。
- **F2（低，diagnostic 口径）**：t97 4 条中 i=26（耽/就）经 t123 源图裁定为**假项**（源图 耽、产物正确），v1.1 已剔除（ids={1,15,36}）；口径从「4 条」变为「3 条」应在报告/spec 中注明，118 条仍 unmaterialized。
- **F3（低，CER 抽样）**：gold 仅 1 页（p703 demo），「抽 2 页」无法执行；真实 20 页 gold（t111）到位后按同口径复核。
- **F4（低，ring 判据）**：`_near_ring` 位置邻域 + 页级 `○+digits` 兜底；页级兜底可能把「同页别处同号」当命中。本轮 54/54 与 t123 的 12 条源图/产物抽样一致，但建议 v2 收紧为**位置邻域 only**。

---

## 7. 复现 / 字节绑定

```bash
cd /opt/test
/usr/bin/python3 src/tools/content_eval.py --gold data/punct_eval/content_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --book wz7 \
  --out /tmp/cev2/real3.json
# -> with_punct CER=0.1202 han_only CER=0.0259 | must-pass 64/64 + 54/54 => True
# 反例
/usr/bin/python3 src/tools/content_eval.py ... --regression-fix /tmp/cev2/fix_mc_minus1.json --out /tmp/cev2/out_minus1.json
# -> must-pass 63/63 + 54/54 => False
/usr/bin/python3 src/tools/content_eval.py ... --t97-meta /tmp/cev2/meta_minus1.json --out /tmp/cev2/out_diag.json
# -> must-pass 64/64 + 54/54 => True（diagnostics materialized 3→2）
/usr/bin/python3 -m pytest src/test/unit/test_content_eval.py -q    # 11 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/content_eval.py`（最终版） | `1affeb0b41952c97609957d66090eb774451fd506003954accbff00941353aea` |
| `src/test/unit/test_content_eval.py` | `f53bb5d5167a7d3be1b5afe72631194b2125aaa0c71b4e0548fe48064849b7f0` |
| `output/wz7_full/wz7_full_v51.pdf` | `38d6656bf37720ff0277d7bd74a5d87a` |
| `tmp_vert/bench/content_v51_v11.json` | 旧中间版（must False / 0.0997 / 0.0519）→ **待重生成** |
| HEAD | `84d6b95`（未 commit） |

> 说明：验证期间 `content_eval.py` 多次变动（`70cb84e5 → dfa745f4 → 2acd54e8 → 1affeb0b`），本报告数字均基于**最终 hash `1affeb0b`**；中间版曾出现 5/54、53/54 的 ring 结果（均已消失）。

---

## 8. 结论

**t126 通过（B 方案口径实现正确）**：must-pass 仅 64+54、diagnostic 不影响 verdict、反例语义正确、两栏 CER 与最终实现一致（PDF 口径 0.1202/0.0259）。

**须修（t125 交付一致性问题，不影响口径本身）**：
1. **F1** 用最终版重生成 `content_v51_v11.json`/`.csv` 并更新 t125 汇报（当前存档为旧中间版：must False / 0.0997 / 0.0519 / diag 4/1）。
2. **F2** 在报告/spec 注明 t97 diagnostic 为 3 条（i=26 已剔除），118 unmaterialized。
3. **F3** 真实 20 页 gold 到位后再补「2 页 CER」抽样。
4. **F4** 建议 ring 检查收紧为位置邻域 only（去页级兜底）。
