# 质量门禁 v1 · quality_gate.py

> 任务：t116 — 把 verify_vert + punct_eval + content_eval 接成统一门禁：AUTO_PASS / MANUAL_ONLY / REJECT
> 执行：竖排工程师　日期：2026-11-09
> 证据：`src/tools/quality_gate.py`、`src/test/unit/test_quality_gate.py`、`tmp_vert/gate/`
> 约束：只读评测；不改 verify_vert.py / punct_eval.py / content_eval.py 判据；不 commit；无 token/网络/API。

## 0. 结论（v51 / wz6 实跑）

| 书/产物 | verify_vert | punct（sequence B） | content（两栏 CER） | **门禁** |
|---|---|---|---|---|
| wz7 v51（1748 页） | FAIL（页数 1:1、字符量 98.8%、越界 0；整页丢失 22 页=影印页，verify 未传 `--expect-low`） | REJECT：P 0.9449 / R 0.9504（quote_close R 0.8788、colon P 0.8281 低于 manual） | REJECT：with_punct CER 0.0961、han_only 0.0570（> manual 0.050/0.040），must-pass 64/64+54/54 通过 | **REJECT**（verify_fail） |
| wz6 完整（231 页） | **PASS**（231=231、字符量 97.2%、越界 0、整页丢失 0） | REJECT：P 0.7879 / R 0.4099（产品文本层标点缺失） | REJECT：with_punct CER 0.1371、han_only（> manual），must-pass 不适用（wz7 页号） | **REJECT**（punct/content） |

- 产物文件：`tmp_vert/gate/gate_wz7_v51.json` + `.md`、`tmp_vert/gate/gate_wz6.json` + `.md`；每项含分项指标、三档判定、原因、top-N 失败明细。
- 说明：阈值来自 spec，尚为 **t111 标定前 provisional**；`AUTO_PASS` 目前不会因本 baseline 触发（预期），门禁链路本身已可判定三档。

## 1. 接口

```bash
/usr/bin/python3 src/tools/quality_gate.py \
  --book wz7 --pdf output/wz7_full/wz7_full_v51.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --gold data/punct_eval/punct_gold_v1.json \
  --out tmp_vert/gate/gate_wz7_v51.json
# 可选：--content-gold（默认 data/punct_eval/content_gold_v1.json）、--src-pdf、--top-n
```

- 内部：`verify_vert.py`（subprocess，`--src-pdf source_pdf/<book>.pdf` 存在时传）+ `punct_bench`（sequence B 主、cell A 参考）+ `content_eval`（两栏 CER + must-pass），全部只读。
- 输出：`gate_<book>.json` + 同名 `.md`（可直接贴 PR/交付报告）。
- `--gold` 不存在时回退 `src/test/bench/punct_gold_v1.json`（cell A 同口径，JSON 记 `gold_fallback=true`），不写 data。

## 2. 判定逻辑（spec 阈值，书无关）

| 分项 | AUTO | MANUAL | REJECT |
|---|---|---|---|
| verify_vert | exit 0 且 页数 1:1、越界 span/矢量 0、整页丢失 0 | — | 任一不满足 |
| punct（§5.2） | 每类 P/R 均达 auto（句读 P≥0.98/R≥0.96；引号/括号/ring P≥0.98/R≥0.95） | 每类均达 manual（P≥0.92/R≥0.88；引号/括号 P≥0.90/R≥0.85） | 任一类低于 manual |
| content（CONTENT_EVAL §6.2） | CER_with_punct≤0.020、han_only≤0.015、missing/wrong≤0.010、extra≤0.005、must-pass 64/54 全过 | ≤0.050/0.040、≤0.030/0.030/0.020、must-pass 全过 | 任一超 manual 或 must-pass fail |

- 合成：verify FAIL → **REJECT**；任一分项 REJECT → **REJECT**；任一分项 MANUAL/UNSCORED → **MANUAL_ONLY**；三项全 AUTO → **AUTO_PASS**。
- **must-pass 适用性**：若 must-pass 条目页号在产物页数范围外（如 wz6 评 wz7 的 fix 清单，覆盖率 <90%），标 `must_pass_applicable=false`，不据此判 content fail（笔记仍保留）。
- 阈值集中常量 `PUNCT_TIERS` / `CONTENT_TIERS`，注释 spec 节号；wz6/wz7 同一套（无书专属值）。

## 3. 输出结构

```
schema_version=quality-gate-v1  book  pdf_sha256  thresholds_source  thresholds{punct,content}
verify{exit,pass_,pages,pages_src,chars_ratio,overflow_span,overflow_vec,page_loss,src_pdf,stdout_tail}
punct{verdict,reasons,failures[],sequence{overall,by_class,reading_order},cell{...}}
content{verdict,reasons,failures[],metrics{with_punct,han_only,must_pass,must_pass_applicable,diagnostics}}
gate{verdict,reasons,verify_pass,punct_verdict,content_verdict,top_failures[],note}
```

- `top_failures` 列 top-N 具体条目：verify 失败摘要（页/越界/丢失）、punct 低于 manual 的类（P/R/阈值）、content 超限项（CER/must-pass）。
- markdown 摘要：结论 / 三分项表 / 阈值来源 / top-N 明细。

## 4. 单测（13 passed）

- verify 解析（页数/字符量/越界/整页丢失）。
- punct 三档：auto（P0.99/R0.97）、manual（0.93/0.90）、reject（0.50/0.50）。
- content 三档：auto、manual、CER 超限 reject、must-pass fail reject、must-pass 不适用（仍可 auto）。
- 合成：verify FAIL→REJECT、全 AUTO→AUTO_PASS、MANUAL→MANUAL_ONLY、分项 REJECT→REJECT。

## 5. 已知局限

- **阈值 provisional**：PUNCT §5.2 / CONTENT §6.2 均为 t111 标定前经验值；本次 wz7/wz6 均 REJECT 属预期（verify 影印页 / 内容 CER / 标点缺失），不得据此开启 auto。
- **verify 影印页**：wz7 v51 有 22 页整页贴图（taskR 设计），verify_vert 未传 `--expect-low` 即判 FAIL；正式门禁需在 verify 参数层登记预期低字页（本任务不改 verify 判据，`--verify-extra` 透传未实现）。
- **punct 口径**：B sequence 为能力主指标但 provisional；wz6 产品文本层标点缺失导致 R 0.41（真实缺口，非评测 bug）；A cell 依赖 gold，`data/punct_eval/punct_gold_v1.json` 缺失时回退 demo。
- **must-pass 适用性**：fix JSON 以 wz7 页号为准；wz6 判定自动置不适用，需 v2 gold 提供跨书 selector。
- **性能**：verify 全量 1748 页约 18s；评测 wz6/wz7 各 3-18s。

## 6. 复现

```bash
/usr/bin/python3 src/tools/quality_gate.py --book wz7 --pdf output/wz7_full/wz7_full_v51.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --gold data/punct_eval/punct_gold_v1.json --out tmp_vert/gate/gate_wz7_v51.json
/usr/bin/python3 src/tools/quality_gate.py --book wz6 --pdf output/wz6/wz6_vert_full.pdf \
  --coords data/wz6/wz6_spotting_coords.json --lines data/wz6/wz6_spotting_lines.json \
  --gold data/punct_eval/punct_gold_v1.json --out tmp_vert/gate/gate_wz6.json
/usr/bin/python3 -m pytest src/test/unit/test_quality_gate.py -q   # 13 passed
```

## 7. 约束

- 只写 src/tools/quality_gate.py、src/test/unit/test_quality_gate.py、docs/quality_gate_v1.md、tmp_vert/gate/；未改 verify_vert.py / punct_eval.py / content_eval.py 判据；未 commit。
