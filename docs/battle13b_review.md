# battle13b 终审 · v44 按页线宽

> 审查人：横排工程师（独立终审）　日期：2026-11-07 01:44–01:56
> 对象：t67（`VERT_DASH_RULE_W_PAGES` 按页线宽 → v44）与 t68 验收报告
> 基线：HEAD `a7b8156`（未 commit 工作树）；v44 `9bc6cb49…`；v42 `f964ad71…`
> 本文件为唯一新增；未改实现/数据/fix JSON/output（build44 产物已恢复），未 commit

---

## 0. 结论

**verdict = pass（v44 可交付；无回退必要）**。

- 独立复跑 build44：BUILD/FIX exit 0；重跑 md5 `84005b7f…` ≠ 交付 `9bc6cb49…`（/ID），但 **1748 页 content-stream 逐页 0 差异、文本 0 差异、size/metadata 同** → 内容完全等价；已恢复交付物 `9bc6cb49…`。
- verify_vert **PASS**：1748=1748 / **931,200** / 差异 18 全预期 / 丢失 0 / 越界 0+0。
- 自 diff v42/v44：**content-stream diff=[57]**、**drawing diff=[57]**、text diff=[]；p57 线宽 **2.784→5.0**、x/y/长与 v42 一致；p1742 **48 组全部 EQUAL**，其余 14 个 dash 页均 EQUAL。
- 开关默认空=旧行为；`src`+页集仅列页生效；parser 空/单页/多页/中文逗号/空白/非法项均通过；无全局默认变更。
- wz6 `ae9d2f52…` + PASS；pytest **603**；dash 开关单测 **4 passed**；token 0；无越界文件。

**低残留**：spec 15 §9.2 测试行仍写「506 passed（… 全量 599）」，而当前 v44 行为 **603 passed**（v44 行已写 603）；属文档数字陈旧，不阻塞。

---

## 1. 独立复跑

| 项 | 结果 |
|---|---|
| build44 | exit 0；重跑 md5 **`84005b7f5b69d42eb6a9f5095662ceb1`**；size 109,997,053、metadata 与交付同；1748 页 content-stream/文本 0 差异；已恢复交付 **`9bc6cb49…`** |
| verify_vert v44 | **PASS**：1748=1748 / **931,200** / 差异>80 字页 **18**（预期 18/非预期 0）/ 整页丢失 **0** / 越界 span **0** + 矢量 **0** |
| v42/v44 影响面 | content-stream diff **`[57]`**（其余 1747 页逐字节同）；drawing diff **`[57]`**；text diff **`[]`** |
| p57 drawing | v44 `'s' w=5.000`，x **829.997**、y **736.497–816.497**、长 **80.000**；v42 w=2.784、x 830.005、y/长同（Δx 0.008） |
| p1742 | v42/v44 均 **48 组**，`get_drawings()` **完全相等**（width 1.432×34 / 1.427×14 不变） |
| p1683 | 1 组，v42/v44 相等（0.808 不变） |
| wz6 | `vert.tex` **`ae9d2f52…`** 逐字节；verify **PASS**（231=231 / 97.2% / 2 预期 / 0 / 0+0） |
| pytest | 全量 **603 passed**（74.14s）；`test_dash_w_pages.py` **4 passed**（0.25s） |
| 7 项纪律 | 实现文件开工=收尾：build_vert `9a376a18…`、build44 `dbb6e356…`、spec15 `c6eb3a07…`、test `67c46abb…`、verify_vert `cc8b6937…`（=HEAD）、fix JSON `ffe24f09…`；token 0 命中；无越界改动 |

---

## 2. 代码审查

- **默认空=旧行为**：`DASH_RULE_W_RAW` 默认 `0.040`；`use_src = raw=='src' and ...` → 默认构建 `use_src=False`，线宽仍 `DASH_RULE_W×F`；旧行为不变。
- **`src` + 空页集**：`_dash_w_src_for` 返回 True（空集=全页），保留旧全局 src 语义；非空页集仅列页 True。
- **解析健壮**：`_parse_page_csv` 容忍空/None、单页、多页、中文逗号、空白、非法项；`test_dash_w_pages.py` 4 条覆盖。
- **无全局默认变更**：`VERT_DASH_RULE_W` 默认仍 0.040；新开关只影响 `raw=='src'` 且页面在集合时的 `w` 选择。
- **DASH_W 链路**：`raw → DASH_RULE_W_RAW → DASH_RULE_W`（fallback）；`_dash_rule_tex` 的 `use_src` 取 `seg['w']`，否则 `DASH_RULE_W×F`；唯一调用点 L4222 传 `page=_dpg`，无其它 `_dash_rule_tex` 调用。
- **fallback**：无源墨组仍走 `_put_tex` 的 `DASH_RULE_W×F`，不受新开关影响。

---

## 3. 影响面

- v44 vs v42：**content-stream 仅 p57**（34679→34675 bytes；其余 1747 页逐字节同）；**drawing 仅 p57**；text 无差异。
- p57 线宽 5.0（源墨 `w_src=5.0`；外部阈值 110 的 5.25 为阈值相关测量，Δ0.25 ≤ 0.3，按既定口径接受）；位置/长度/线心与 v42 一致。
- p1742 的 48 组 dash 与 v42 完全相等；p31/37/38/39/60/62/119/262/462/600/686/1157/1683 亦 EQUAL（drawing diff 仅 57）。
- v43 的全局 src 影响 8 页、p1742 22 组变宽；v44 按页启用把影响面收敛到 1 页，符合要求。

---

## 4. spec 15 三层口径

- §9.1 线宽：默认 0.040×F / 全局 src / v44 按页 5.0pt；仅 p57 变——与实测一致。
- §9.2 v44 行：2.784→5.0、content-stream diff 仅 p57、verify PASS——一致；v43 明确作废。
- §9.3 env：`VERT_DASH_RULE_W` 默认 0.040×F；`VERT_DASH_RULE_W_PAGES` 空=全局、逗号页号=按页——与代码一致。
- §9.4 按页用法与物理页号注意——一致。
- **R1（低）**：§9.2 的「测试」行仍写 **506 passed（474+32；2026-11-07 全量 599）**，而当前 v44 全量为 **603 passed**（同节 v44 行已写 603）；建议把该历史行更新为 603 或明确标注为旧记录，避免自相矛盾。

---

## 5. 残留（不阻塞）

- **R1（低）**：spec 15 §9.2 测试计数陈旧（506/599 vs 603），v44 行正确；仅文档。
- **R2（低）**：build44 非字节可复现（本次 `84005b7f…`，t68 `e4eaf3a7…`，交付 `9bc6cb49…`）；content-stream/文本 0 差异，属 /ID。
- **R3（说明）**：线宽 5.0 为管线 src 实测；外部阈值 110 的 5.25 差 0.25，阈值 90–150 波动 4.56–5.28，按 5.0±0.3 接受。
- **R4（说明）**：`VERT_DASH_RULE_W_PAGES` 页号为物理页号，换书需重列（spec 已注明）。

---

## 6. 结论

v44 只改 p57 线宽 2.784→5.0；其余 1747 页 content-stream 逐字节相同、p1742 48 组完全不动；开关默认/全局/按页三态正确；verify/wz6/pytest 603 全过。**通过终审，可交付**。仅建议顺手更新 spec 15 §9.2 的旧测试计数 506/599→603。
