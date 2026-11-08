# content_eval PDF 口径修复 独立验收（t129 · must-pass 64/54 + CER）

> 验收人：验证评审员（独立验证方）　日期：2026-11-08 19:00–19:25
> 对象：t128（content_eval 口径修复：回归/CER 改读产物 PDF）
> 基线：HEAD `84d6b95`（未 commit）；**未改实现/数据/fix JSON/output、未 commit**
> 证据：`src/tools/content_eval.py`（`1affeb0b…`）、`content_v51_pdf.json`、`/tmp/cev3/`

---

## 0. 结论

**PASS（PDF 口径修复正确）**：

- **两次复跑完全一致**（JSON md5 `a4142a54301ecaf78f4b72d0eed31e41`）：must-pass **64/64 + 54/54 → True**（REGRESSION_BLOCKED 撤销）；with_punct **0.1202** / han_only **0.0259**。
- **15 条 must-pass 独立抽样**（8 缺字 + 7 ring）：自裁源图 + 产物 PDF 坐标邻域均「该有、产物有」→ 15/15 通过。
- **CER 独立手算**：p703 with_punct **0.1202** / han_only **0.0259** = 评测器输出（误差 0）；与 t123 值一致。
- **防回退**：把 p141 的期望字「謄」从输入 lines 中删除（产物 PDF 仍有）→ must-pass 仍 **64/64 + 54/54 = True**、CER 不变（0.1202/0.0259）→ 评测器确实读 PDF，未退回 lines。
- pytest **11 passed**。
- 限制：content gold 仅 **p703 一页**（demo），「2 页手算」无法执行（如实登记，F1）。

---

## 1. PASS/FAIL 总表

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 复跑 t128：must-pass 64/64 + 54/54、BLOCKED 撤销；两次运行一致 | **PASS** | 两次 JSON md5 相同 `a4142a54…`；must True；64/64 + 54/54；CER 0.1202/0.0259 |
| 2 | 抽 ≥15 条 must-pass（8 缺字 + 7 ring）：自裁源图 + 产物 PDF 坐标 | **PASS** | 8 缺字：p634 籤 0.05 / p50 竊 0.04 / p85 峴 0.26 / p105 逕 0.15 / p213 颳 0.15 / p469 青 0.08 / p527 宿 0.38 / p987 於 0.06（格）；7 ring：p1695 ㉜×2、p1696 ㉞、p1698 ㊳/㊴、p1708 ○54/○55（源图同值） |
| 3 | CER 手算 2 页（差 ≤0.5pp） | **PASS（1 页，限制登记）** | gold 仅 p703：eval 0.1202/0.0259 = 手算 0.1202/0.0259（误差 0）；t123 同值；第二页无 gold（F1） |
| 4 | 防回退：产物有字、lines 无 → 必须判通过 | **PASS** | 删 p141 lines 中的「謄」→ must 仍 True、CER 不变（0.1202/0.0259）；旧 lines 口径会 fail |
| 5 | 报告 docs/content_eval_acceptance_v12.md；不改实现/数据；不 commit | **PASS** | 本文件；只读；未 commit（HEAD `84d6b95`） |

---

## 2. 15 条 must-pass 抽样（自裁源图 + 产物 PDF 坐标）

### 2.1 缺字 8 条（64 清单）

| 页 | 期望字 | 源图（自裁 cell 8×） | 产物 PDF 距离（格） | 判定 |
|---|---|---|---|---|
| 634 | 籤 | 籤 | 0.05 | PASS |
| 50 | 竊 | 竊 | 0.04 | PASS |
| 85 | 峴 | 峴 | 0.26 | PASS |
| 105 | 逕 | 逕 | 0.15 | PASS |
| 213 | 颳 | 颳 | 0.15 | PASS |
| 469 | 青 | 青 | 0.08 | PASS |
| 527 | 宿 | 宿 | 0.38 | PASS |
| 987 | 於 | 於 | 0.06 | PASS |

### 2.2 ring 7 条（54 清单）

| 页 | expected number/cp | 源图（自裁 ±22pt） | 产物 PDF 邻域 | 判定 |
|---|---|---|---|---|
| 1695 | 32 / U+3252 | **32** | ㉜ | PASS |
| 1695 | 32 / U+3252 | **32** | ㉜ | PASS |
| 1696 | 34 / U+2463 | **34** | ㉞ | PASS |
| 1698 | 38 / null | **38** | ㊳ | PASS |
| 1698 | 39 / null | **39** | ㊴ | PASS |
| 1708 | 54 / null | **54** | ○５４ | PASS |
| 1708 | 55 / null | — | ○５５ | PASS |

> 源图裁片见 `/tmp/cev3/sample15.png`；产物坐标邻域取 `fitz rawdict` 字符中心（±20pt）。

---

## 3. 两栏 CER 复核

- **gold 现状**：`data/punct_eval/content_gold_v1.json` 仅 **p703**（363→N0 341）；无第二页（F1）。
- **评测器（PDF 口径）**：with_punct **0.1202**（341/41，miss 3/wrong 38/extra 0）、han_only **0.0259**（270/7，wrong 2/extra 5）。
- **独立手算（PDF 文本，N0）**：with_punct **0.1202**、han_only **0.0259** → 差 **0pp**（≤0.5pp）。
- 与 t123 手算 0.1202/0.0259 一致；旧 lines 值 0.0997/0.0519 已废弃。

---

## 4. 防回退反例

- 构造：复制 lines JSON，将 p141 页面所有行中的期望字「謄」删除（产物 PDF 该字仍在）。
- 运行：`--lines /tmp/cev3/lines_nomissing.json`
- 结果：**must-pass 64/64 + 54/54 = True**；CER 仍 0.1202/0.0259（未变成 lines 口径值）→ **不退回 lines** ✓
- 对照：旧 t122 实现读 lines，会因「謄」不在 lines 判 fail（该条正是旧 35 fails 之一）。

---

## 5. 关键发现（低）

- **F1（低）**：content gold 仅 p703 一页（demo），验收要求的「2 页手算」无法执行；需 t111 的 20 页 gold 到位后补第二页。
- **F2（低）**：`tmp_vert/bench/content_v51_pdf.json` 与最终实现一致（True/0.1202/0.0259）；t126 指出的旧 `content_v51_v11.json`（must False/0.0997）仍是历史中间版，建议删除或标注 deprecated，避免下游误读。
- **F3（低）**：ring 的「○+digits」页级 fallback 仍可能把同页别处同号当命中；本轮 7 条抽样位置邻域均命中，建议 v2 收紧。
- **F4（说明）**：t97 diagnostic 仍为 3 条（#1/#15/#36，i=26 已剔除）0/3；118 条 unmaterialized，不参与 must-pass。

---

## 6. 复现 / 字节绑定

```bash
cd /opt/test
/usr/bin/python3 src/tools/content_eval.py --gold data/punct_eval/content_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --book wz7 \
  --out /tmp/cev3/run1.json
# -> must-pass 64/64 + 54/54 => True; CER 0.1202/0.0259
/usr/bin/python3 src/tools/content_eval.py ... --out /tmp/cev3/run2.json
md5sum /tmp/cev3/run1.json /tmp/cev3/run2.json      # 相同 a4142a54…
# 防回退
/usr/bin/python3 src/tools/content_eval.py ... --lines /tmp/cev3/lines_nomissing.json --out /tmp/cev3/out_nolines.json
# -> must True，CER 不变
/usr/bin/python3 -m pytest src/test/unit/test_content_eval.py -q    # 11 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/content_eval.py` | `1affeb0b41952c97609957d66090eb774451fd506003954accbff00941353aea` |
| `src/test/unit/test_content_eval.py` | `f53bb5d5167a7d3be1b5afe72631194b2125aaa0c71b4e0548fe48064849b7f0` |
| `output/wz7_full/wz7_full_v51.pdf` | `38d6656bf37720ff0277d7bd74a5d87a` |
| `tmp_vert/bench/content_v51_pdf.json` | 基线（True / 0.1202 / 0.0259） |
| HEAD | `84d6b95`（未 commit） |

---

## 7. 结论

**t128 通过（PDF 口径修复有效）**：must-pass 64/64 + 54/54（BLOCKED 撤销）、两次运行一致、15/15 抽样「该有、产物有」、CER 与手算一致（0.1202/0.0259）、防回退反例通过（lines 删除不影响判决）。

**建议**：t111 gold 到位后补第二页 CER；标注/删除旧 `content_v51_v11.json`；ring 页级 fallback 收窄（v2）。
