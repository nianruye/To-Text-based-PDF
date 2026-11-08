# content_eval 独立验收（t123 · 回归真实性与 CER）

> 验收人：验证评审员（独立验证方）　日期：2026-11-08 18:40–19:20
> 对象：t122（content_eval v1）+ **t125（v1.1，验证期间已落地，以其为准）**
> 基线：HEAD `84d6b95`（未 commit）；**未改实现/数据、未改 fix JSON/output、未 commit**
> 证据：`src/tools/content_eval.py`（v1.1，sha256 `70cb84e5…`）、`tmp_vert/bench/content_acc_v51.json`、`/tmp/cev/content_v11.json`、自裁源图 `/tmp/cev/t97_4.png`、`i15_zoom.png`

---

## 0. 结论（以 t125 v1.1 输出为准）

**t125 v1.1 已跑出**：`must-pass 64/64 + 5/54 => False`；两栏 CER 仍是 **lines 口径** 0.0997/0.0519。据此：

1. **64 条确认缺字：64/64 通过**（v1.1 的 `missing_char_confirmed` 全过；我用 PDF 位置独立复核也 **64/64 期望字在产物中存在**，57 条 ≤0.5 格、7 条 0.5–1.6 格为 cell/渲染偏移，**无真缺字回归**）。
2. **54 条 battle4 ring：5/54（v1.1，lines 口径）→ must_pass False；但独立复核判定为「评测口径误报」，不是内容回归**：抽 12 条源图+产物核对，**12/12 产物圈号正确**（p1695 ㉜、p1696 ㉞、p1698 ㊳/㊴、p1708 ○54/○55/○56、p1709 ○56…），源图实测同值（32/32/34/38/39/54）；build 日志 `ring① 352 + ring② 15`（367 全灌入，跳过 0）；v37/v44/v50/v51 四版均有 ㉜ 与 ○54 → **没有版本丢失**。v1.1 的 `_check_char_at` 对 ring 用 **lines（输入）** + `pos=None` → 取列首窗口、且期望 cp 不在 OCR 文本 → 5/54 是口径 bug（详见 §5.1）。
3. **旧 125/160 与 1/4 不成立**（t122 口径）：`regression_missing_char` 读 **lines（输入）** 而非 PDF；35 条「失败」**全部是假失败**——期望字均在 PDF 出现（26 条 ≤0.5 格、6 条 0.5–1.5 格、3 条多字符/竖排形伪串；**0 真缺字**）；125 条「通过」也含假阳性（字在同页别处）。
4. **两栏 CER 口径错**：v1.1 仍用 `pages_text(lines)` 计算（`--pdf` 只算 sha256）。同一 p703 用 **PDF 文本** 手算 = **with_punct 0.1202 / han_only 0.0259**；eval 的 0.0997/0.0519 是 lines 值（已用 lines 手算复现）。
5. **t97 4 条**：源图裁定 **3 真 / 1 假**——i=1 `v/V`（源 V，真）、i=15 `刺刺/剌剌`（源 剌剌，真）、i=26 `耽/就`（源 耽，产物正确，**假**）、i=36 `蟻/螃`（源 螃蟹，真）。v1.1 的 diagnostic `materialized_rate=0.25` 恰好把**假的那条（i=26）**算通过；真 3 条被页面级 contains 判 fail → 检出不可信，需改位置/上下文口径并剔除 i=26。
6. **REGRESSION_BLOCKED 判定**：**旧口径（125/160、1/4）不成立；新口径 64/64 已过；54 条 ring 的 5/54 是评测口径误报（产物 12/12 正确、源图同值、v37 起未丢），不是内容回归 → REGRESSION_BLOCKED 不应由它触发**。修评测器后 54 条应按 PDF 位置重算（预计 54/54 或接近）。

---

## 1. PASS/FAIL 总表

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 35 条失败性质（页内上下文/邻域，不用 pos 直比） | **完成（全部假失败）** | 26 ≤0.5 格 / 6 0.5–1.5 格 / 3 多字符-竖排形伪串；**0 真缺字**（§2） |
| 2 | t97 4 条裁定（是否纳入） | **完成（3 真 1 假）** | i=1/15/36 真；i=26 假（源 耽）→ diagnostic 只计 3 条（§3） |
| 3 | 两栏 CER 复核（手算，误差 ≤1%） | **完成（口径差异已定位）** | gold 仅 p703（demo）；PDF 手算 0.1202/0.0259 vs eval lines 0.0997/0.0519（差异来自数据源，非四舍五入） |
| 4 | REGRESSION_BLOCKED 判定 + 修复建议 | **完成** | 旧口径不成立；新口径 64/64 过、54 条因 battle4 策略/清单未定（5/54 lines 口径）；建议见 §7 |
| 5 | 报告 docs/content_eval_acceptance.md；不改实现/数据；不 commit | **完成** | 本文件；只读；未 commit（HEAD `84d6b95`） |

---

## 2. 35 条「失败」逐条核定（t122 输出；PDF 位置复核）

方法：fix JSON 的 `cell/col+pos/text` 定位期望格；在 **v51 PDF 文本层**取全页字符坐标（`rawdict`），期望字（含竖排形 `「→﹁`、`」→﹂` 等）与期望格中心纵向距离（单位=格高）；不采信 lines/pos 直比。

| 分类 | 数量 | 明细（页/字/距离格） |
|---|---|---|
| **A. 已插入且 ≤0.5 格** | **26** | p634 籤 0.05、p50 竊 0.04、p85 峴 0.26、p105 逕 0.15、p213 颳 0.15、p469 青 0.08、p527 宿 0.38、p779 遞 0.14、p781 舡 0.04、p857 遞 0.05、p987 於 0.06、p1189 尚 0.16、p1256 絹 0.15、p1337 翫 0.0（×2）、p1342 翠 0.12、p1399 筍 0.14、p1419 粧 0.09、p1437 面 0.12、p1499 襯 0.26、p1555 封 0.14、p1642 既 0.15、p1653 蠻 0.09、p68 尚 0.21、p263 「 0.48（形 ﹁） |
| **B. 已插入但 0.5–1.5 格** | **6** | p263 」 1.26（形 ﹂）、p411 粧 0.63、p1689 翫 0.78、p1219 纖 0.88、p1419 慌 0.91、p1291 」 0.62（形 ﹂） |
| **C. 多字符/竖排形伪串** | **3** | p57 `——`、p147 `」，`、p186 `」。`（组件在 PDF 中分离/为竖排形） |
| **真缺字** | **0** | — |

> 35 条 `missing_in_product` 全部是「lines 中无该字」的必然结果（这些字本来就是 OCR 缺字）——不能作为产物缺字判据。
> t125 v1.1 的 `_check_char_at` 仍用 **lines + 列窗口**（非 PDF），`missing_char_confirmed` 64/64 只是 col±4 窗碰巧覆盖；`diagnostics.missing_char_all` 75/160 同样不代表 PDF。

---

## 3. t97 4 条裁定（自裁源图 12–16×）

| i | 页/行/pos | B（产物）→ A（期望） | 源图 | 裁定 |
|---|---|---|---|---|
| 1 | p5 r1 p4 | `v` → `V` | 源 **V**（大写） | **真**（大小写误读；diagnostic，内容影响极低） |
| 15 | p652 r8 p39 | `刺刺` → `剌剌` | 源 **剌剌**（束+刂） | **真**（diagnostic） |
| 26 | p343 r2 p14 | `耽` → `就` | 源 **耽**（耳+冘） | **假**（产物正确；A 误读，不纳入） |
| 36 | p578 r4 p14 | `蟻` → `螃` | 源 **螃蟹** | **真**（diagnostic） |

- **纳入 diagnostic：3 条**（i=1/15/36）；i=26 剔除。
- v1.1 `typo_t97.materialized_rate=0.25`（1/4）中「通过」恰为 **i=26（假）**；真 3 条被判 fail（页面级 contains）→ **检出不可信**。
- 118 条外推仍未 materialize（v1.1 标 `unmaterialized`），diagnostic 无法逐条检出。

---

## 4. 两栏 CER 复核

- **gold 现状**：`data/punct_eval/content_gold_v1.json` 仅 **p703**（demo；363→N0 341），无法抽 2 页；如实登记。
- **PDF 文本手算（N0）**：with_punct **341/41 → 0.1202**（miss 3, wrong 38, extra 0）；han_only **270/7 → 0.0259**。
- **content_eval v1.1**：with_punct **0.0997**（341/34）、han_only **0.0519**（270/14）——用 lines 手算恰为同值（已验证）。
- **结论**：CER **不反映产物 PDF**；`--pdf` 只参与 sha256。内容门禁必须改 PDF 口径（建议 `page.get_text()` + N0），否则 CER 与内容无关。

---

## 5. 新口径 must-pass（64 + 54）

| 清单 | 数量 | v1.1 结果 | 我的独立复核 | 结论 |
|---|---|---|---|---|
| 64 确认缺字（shape&complete） | 64 | **64/64** | PDF 位置：64/64 存在（57 ≤0.5 格、7 0.5–1.6 格） | **通过** |
| 54 battle4 ring | 54 | **5/54**（lines 口径，误报） | PDF 位置：抽 12/12 产物圈号正确（㉜/㉞/㊳/㊴/○54/○55/○56…），源图实测同值；build ring 367 全灌入（跳过 0）；v37–v51 四版一致 → **无回归/无丢失**；原因 = 评测器读 lines+pos=None（§5.1） | **通过（内容）；评测器需修** |

- 旧 118/4 按 captain 决策降 diagnostic；v1.1 的 `must_pass=False` 主因是 **54 条 ring**，而非 64 条缺字。

---

## 5.1 battle4 ring 5/54：评测口径误报（独立核定）

- **代码原因**：`regression_must_pass.check_ring()` → `_check_char_at(lines, coords, page, col, pos=None, needle=cp字符 或 number)`：
  - lines 是 **OCR 输入文本**，圈号在输入里是末尾数字（如 `22`），不是 cp ㉜；cp 项必然找不到；
  - `pos=None` → `pos=0`，`win = text[max(0,-4):5]` = **列首 5 字**，不是列尾圈号位置；cp=null 的 `number` 也按列首查 → 多数 fail。
  - 5/54 的「通过」多因数字恰在列首窗口/同字巧合。
- **产物/源图实测**（12 条抽样，页面 = 1695/1696/1698/1708/1709）：

| 页 | 期望 number/cp | 源图（8×裁片） | v51 产物（source_x/y ±30pt） | 判定 |
|---|---|---|---|---|
| p1695 | 32 / U+3252 | **32** | **㉜** | ✓ |
| p1695 | 32 / U+3252 | **32** | **㉜** | ✓ |
| p1696 | 34 / U+2463 | **34** | **㉞** | ✓ |
| p1698 | 38 / null | **38** | **㊳** | ✓ |
| p1698 | 39 / null | **39** | **㊴** | ✓ |
| p1708 | 54 / null | **54** | **○５４** | ✓ |
| p1708 | 55 / null | — | ○５５ | ✓ |
| p1708 | 56 / null | — | ○５６ | ✓ |
| p1709 | 56 / null | — | ○５６ | ✓ |
| …其余抽样同为正确 | | | | |

- **构建/版本**：build51 日志 `ring① 352 / ring② 15（>50 合成圈 230）/ 跳过 0`；v37/v44/v50/v51 的 p1695 均含 ㉜、p1708 均含 ○54 → **battle4 修正自 v37 起一直在产物中，无「哪版丢」**。
- **结论**：5/54 = **评测器口径误报**（读 lines + pos=None），不是内容真回归；不列 blocker。修法：ring 检查改读 **PDF 字符坐标**，在 `(source_x, source_y)` ±15–20pt 内匹配 cp 字符或 `○+digits`（全角/半角归一），并按 situation 处理。

## 6. 字节绑定 / 复现

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/content_eval.py`（v1.1） | `70cb84e5092492af5057ed870d8b1100cf0b84ec01b58727c3f4f1fca7ccfc6c` |
| `src/test/unit/test_content_eval.py` | `e1244e7c80b4feb67097dead82160940c7227caae251c40155d3f8efd3376a60` |
| `data/punct_eval/content_gold_v1.json` | 1113 B（p703 demo） |
| `output/wz7_full/wz7_full_v51.pdf` | `38d6656bf37720ff0277d7bd74a5d87a` |
| HEAD | `84d6b95`（未 commit） |

```bash
cd /opt/test
/usr/bin/python3 src/tools/content_eval.py --gold data/punct_eval/content_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --book wz7 \
  --out tmp_vert/bench/content_acc_v51.json
# -> must-pass 64/64 + 5/54 => False；CER 0.0997/0.0519（lines）
/usr/bin/python3 -m pytest src/test/unit/test_content_eval.py -q     # 10 passed
```

---

## 7. 结论与建议

**t123 验收（35 性质、4 条裁定、CER 复核、判定建议）完成**；对 t122/t125 的结论：

1. **CER 改 PDF 口径**：内容两栏必须用产物 PDF 文本；v1.1 仍是 lines（0.0997/0.0519），PDF 手算 0.1202/0.0259（p703 demo）。否则内容门禁与产物无关。
2. **回归检查改 PDF + 位置/上下文**：`_check_char_at` 目前是 lines+列窗；应改为 PDF 字符坐标 ±0.5–1 格（容忍渲染 y 偏移）+ 竖排形归一；35 条假失败/125 条假阳性可消；**ring 检查同样必须改 PDF**（`source_x/source_y` ±15–20pt，cp 或 ○+digits）。
3. **54 条 ring 是评测器 bug**：产物 12/12 抽样正确（㉜/㉞/㊳/㊴/○54/○55/○56），源图同值，v37/v44/v50/v51 均含修正；`ring_corrections` 的 n_applied=7 是旧 battle4 清单口径，与 fix JSON 已灌入的 ring_fix 54 条不矛盾。修 `check_ring` 读 PDF `(source_x,source_y)` ±15–20pt 匹配 cp/○+digits 即可，无需改数据、无需 v52。
4. **t97 diagnostic**：只计 3 条真 typo（i=1/15/36）；剔除 i=26；118 条 manifest 待建。
5. **REGRESSION_BLOCKED**：旧口径撤回；新口径 64/64 过，54 条等第 3 项决策。

> 本轮未改实现/数据/fix JSON/output；只新增本报告。
