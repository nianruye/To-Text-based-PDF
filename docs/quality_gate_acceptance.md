# 质量门禁 v1 独立验收（t151 · round 3）

> 验收人：验证评审员（独立验证方）　日期：2026-11-08 22:05–22:35
> 对象：t150（quality_gate：punct 定位、data_missing 输入侧判据、must_pass not_applicable、超限页 char/column）
> 基线：HEAD `84d6b95`（未 commit）；**未改实现/数据、未 commit**
> 证据：`src/tools/quality_gate.py`（`4bf0bfc9…`）、`test_quality_gate.py`（`0fea1880…`）、`/tmp/qg3/`、`tmp_vert/gate/gate_wz{7_v51,6}.json`

---

## 0. 结论

**PASS**（t149 的 F1–F4 均已修复，验收项全部成立；仅 3 项低风险观察）：

- **可复现**：wz7 两次 md5 相同 `e716c9b3…`（verify PASS、punct REJECT、content REJECT → **REJECT**）；wz6 两次 `8faead1d…`（verify PASS、punct MANUAL、content REJECT → **MANUAL_ONLY**）；pytest **18 passed**。
- **punct 定位已补**：`pseq` 带 `by_page`（8/10 页）+ `errors`；`pages_with_fn` 每页含 `column/char_pos/gold_char`（wz7 p57 col1/pos9/`—`、p97 col0/pos0/`『`；wz6 p7 col0/pos8/`，`）；failures 带 `pages` 列表。
- **data_missing 输入侧判据已生效**：wz6 `classification=data_missing`（product/input 均 0.5244、anchor 0.9718）→ MANUAL_ONLY；wz7 `ok`（1.0073/0.9796/0.9710）仍 REJECT。
- **product_regression 反例（追加）**：临时 lines 给 wz6 gold 页补标点（input ratio **0.8422 >0.75**），产物仍 0.5244 → `classification=product_regression` → punct REJECT + reason → **REJECT** ✓（F3 修复生效）。
- **阈值入 spec**：PUNCT_EVAL **§6.4.8**（0.75/0.75/0.80 provisional）+ CONTENT_EVAL **§6.4** 已写入；`DATA_MISSING_TIERS` 与 `THRESHOLDS_SOURCE` 同步；无 wz6/wz7 分支。
- **输出可消费**：顶层 `version/metrics/verdict/reasons` 齐全；markdown 结论/分项/top-N 可读。
- **content 定位**：`over_limit_pages` 带 `page/column/char_pos/gold_char/product_char`（wz7 7 页、wz6 10 页）；wz6 `must_pass_status=not_applicable`、`must_pass_fail_items=[]`（F4 修复）。

**低风险观察（不影响 PASS）**：
- **F1（低）**：`punct.failures[*]` 的 `column/char_pos` 仍为 null（只有 `pages` 列表）；列/字格定位在 `pages_with_fn` 里，流水线需自行 join。
- **F2（低）**：`content.over_limit_pages` 的 `column/char_pos` 取「首个差异位置」（常为 0/0），`gold_char` 可能不是标点（如 `論`/`協`）；页级定位可靠，字级仅近似。
- **F3（低）**：`data_missing` 比值在 gold 无标点时无界（CER 反例中 `product_punct_ratio=236.0`）；建议 clamp 或标 N/A。

---

## 1. PASS/FAIL 总表

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 复跑 wz7 v51 与 wz6 各一次，判定/分项可复现 | **PASS** | wz7 md5 `e716c9b3…`×2；wz6 `8faead1d…`×2；pytest 18 passed |
| 2 | 3 反例（verify FAIL / punct recall 退化 / CER 超限）→ REJECT/WARN，明细指向页/列/字格 | **PASS** | verify FAIL→REJECT verify_fail（pages 231/200、p201+）；punct 退化→MANUAL_ONLY（WARN，pages_with_fn 有 col/pos/gold_char）；CER 超限→REJECT（over_limit_pages 有 page/col/pos）；另 product_regression 反例→REJECT |
| 3 | 阈值来自 spec §5/§6，无书专属硬编码；两书同阈值 | **PASS** | PUNCT/CONTENT tiers 与 spec §5.2/§6.2 一致；DATA_MISSING_TIERS 0.75/0.75/0.80 已入 PUNCT_EVAL §6.4.8 + CONTENT_EVAL §6.4；grep wz6/wz7 仅 docstring |
| 4 | 输出可流水线消费：book/version/metrics/verdict/reasons；markdown 可读 | **PASS** | 顶层字段齐全；markdown 可读；定位字段见 §0（F1/F2 低） |
| 5 | 报告 docs/quality_gate_acceptance.md；不改实现/数据；不 commit | **PASS** | 本文件；只读；未 commit（HEAD `84d6b95`） |

---

## 2. 复跑结果

| 书 | 运行 | md5 | verify | punct | content | verdict |
|---|---|---|---|---|---|---|
| wz7 v51 | ×2 | `e716c9b3…` | PASS（1748/1748、98.8%、越界 0、丢失 0；expect_low 30 页） | REJECT（P0.9449/R0.9504；data_missing=ok） | REJECT（CER 0.0961、han 0.057、must_pass True；over_limit 7 页） | **REJECT** |
| wz6 | ×2 | `8faead1d…` | PASS（231/231、97.2%、丢失 0） | MANUAL（data_missing，ratio 0.5244） | REJECT（CER 0.1371；vertical_form 0.1253；over_limit 10 页；must_pass not_applicable） | **MANUAL_ONLY** |

---

## 3. 反例表

| # | 反例 | 结果 | 明细（定位） |
|---|---|---|---|
| 1 | verify FAIL：231 页 PDF + 200 页 coords/lines | **REJECT**（verify_fail） | `pages 231/200`；stdout 含「页数不 1:1」「p201(差230)…」 |
| 2 | punct recall 退化：wz6 gold 8 页各加 40 个 `。` | **MANUAL_ONLY**（WARN；data_missing） | `pages_with_fn` 有 page/column/char_pos/gold_char（p7 col0/pos8/`，`）；failures 有 pages 列表 |
| 3 | CER 超限：wz6 gold 改为无关文本 | **REJECT**（content_over_manual） | `over_limit_pages` p7/p8…（CER 1.0、col/pos） |
| 4 | **product_regression（追加）**：临时 lines 给 wz6 gold 页补标点（input ratio 0.8422） | **REJECT**（punct_regression + product_regression） | data_missing `classification=product_regression`、p=0.5244/i=0.8422 → 按产品回归 REJECT ✓ |

---

## 4. 阈值核对

- PUNCT_TIERS / CONTENT_TIERS 与 spec §5.2/§6.2 全项一致（本轮未改）。
- `DATA_MISSING_TIERS = product 0.75 / input 0.75 / anchor 0.80`；PUNCT_EVAL **§6.4.8**（L726+）与 CONTENT_EVAL **§6.4**（L342+）已明文登记 provisional；`THRESHOLDS_SOURCE` 含 `§6.4.8(data_missing)`。
- 无 `book == wz6/wz7` 分支（grep 仅 docstring）。

---

## 5. 输出结构

顶层：`schema_version, book, pdf_sha256, thresholds_source, thresholds, verify, punct, content, gate, expect_low, version, metrics, verdict, reasons`。

- 有 `version/metrics/verdict/reasons` ✓；markdown 结论/分项表/top-N 可读 ✓。
- 定位：`punct.pages_with_fn[*].column/char_pos/gold_char`、`content.over_limit_pages[*].page/column/char_pos/gold_char/product_char`；`punct.failures[*]` 仅 `pages`（F1 低）。
- `must_pass_status=not_applicable`（wz6）且 `must_pass_fail_items=[]` ✓。

---

## 6. 复现 / 字节绑定

```bash
cd /opt/test
/usr/bin/python3 src/tools/quality_gate.py --book wz7 --pdf output/wz7_full/wz7_full_v51.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --gold data/punct_eval/punct_gold_v1.json --out tmp_vert/gate/gate_wz7_v51.json
# -> verify PASS / punct REJECT / content REJECT -> REJECT
/usr/bin/python3 src/tools/quality_gate.py --book wz6 --pdf output/wz6/wz6_vert_full.pdf \
  --coords data/wz6/wz6_spotting_coords.json --lines data/wz6/wz6_spotting_lines.json \
  --gold data/punct_eval/punct_gold_v1.json --out tmp_vert/gate/gate_wz6.json
# -> verify PASS / punct MANUAL / content REJECT -> MANUAL_ONLY
/usr/bin/python3 -m pytest src/test/unit/test_quality_gate.py -q    # 18 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/quality_gate.py` | `4bf0bfc943954253744e8336503052b45c33fa7878ffe81500ee17fb64fc9d29` |
| `src/test/unit/test_quality_gate.py` | `0fea18804a9a42d947985d240c52b28e1722d649b839e375fa4108e98575b28d` |
| `output/wz7_full/wz7_full_v51.pdf` | `38d6656bf37720ff0277d7bd74a5d87a` |
| `output/wz6/wz6_vert_full.pdf` | `99bef17b73d0afbc2d616e301511a182` |
| wz7 gate JSON | md5 `e716c9b3e1a998b622fb3605235b236b`（×2） |
| wz6 gate JSON | md5 `8faead1d3ac93fb23442d3b82a3678bd`（×2） |
| HEAD | `84d6b95`（未 commit） |

---

## 7. 结论

**t151 通过（PASS）**：复跑一致；三反例判定正确且具备页/列/字定位（产品回归反例另验 REJECT）；data_missing 阈值已入 spec；输出字段与 markdown 可消费；wz7 REJECT、wz6 MANUAL_ONLY 与 t150 声明一致。

**低风险建议**：F1 failures 补齐 column/char（或文档说明用 pages_with_fn）；F2 content 字级定位改为实际首个标点/错字位置；F3 gold 无标点时 data_missing ratio 标 N/A。
