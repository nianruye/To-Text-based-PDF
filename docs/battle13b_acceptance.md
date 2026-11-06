# battle13b 独立验收（t68 · v44 按页线宽）

> 验收人：验证评审员（独立验证方）　日期：2026-11-07 01:31–01:45
> 基线：HEAD `a7b8156`（未 commit 工作树）；**未改实现代码、未改 fix JSON/数据、未 commit/push**
> 对象：t67（battle13b：`VERT_DASH_RULE_W_PAGES` 按页线宽 → v44；v43 作废）
> 主产物：`output/wz7_full/wz7_full_v44.pdf`（md5 `9bc6cb4992f57b319887cb173090e62a`，1748 页）
> 方法：自己重跑 build44、自己读 `get_drawings()` 量线宽、自己 diff v42/v44 内容流与全部绘图、自己做开关三态单页构建、自己跑 wz6/pytest。

---

## 0. 结论

**PASS（可交付）**。v44 只把 **p57** 的破折号线宽从 2.784pt 改为源墨实测 **5.0pt**；其余 **1747 页 content-stream 逐字节相同**、绘图签名逐页相同；开关默认空=旧行为、按页/多页/全局三态均正确；门禁全过。

**核心数字**：
- 复跑 build44 → md5 `e4eaf3a70d27c793f8c351d5e784bf54` ≠ 交付 `9bc6cb49…`（/ID），但 **size 109,997,053 相同、metadata 相同、1748 页文本/行 bbox 逐页 0 差异、**内容流逐页 0 差异**（比 t67 的「仅 p57 差」更强）→ 内容等价；已恢复交付物 `9bc6cb49…`。
- verify_vert（--expect-low）**PASS**：1748=1748 / **931,200**（与 v42 同）/ 差异>80 字页 **18（预期 18/非预期 0）** / 整页丢失 **0** / 越界 span **0** + 矢量 **0**。
- **p57 线宽**：v44 `get_drawings` = `'s' w=5.000`，**5.0±0.3 口径通过**（源墨外部阈值 110 = 5.25，Δ0.25；管线 `_dash_ink_seg` w_src=5.0）；线位/线长/线心与 v42 一致：y **736.497–816.497**（Δ0）、长 **80.000**（Δ0）、x **829.997 vs 830.005**（Δ0.008）。
- **影响面**：v44 vs v42 **内容流 diff = [57]**（其余 1747 页逐字节相同）；**绘图签名 diff = [57]**；**文本 diff = []**。15 个 dash 页（31/37/38/39/57/60/62/119/262/462/600/686/1157/1683/1742，63 组）中 **其余 14 页逐 drawing EQUAL**，p1742 的 **48 组**（width 1.432×34 / 1.427×14）完全不变。
- **开关三态**（单页构建 VERT_PAGES=57,1683,1742）：
  - 默认空（无 `VERT_DASH_RULE_W`）：p57 **2.784**、p1683 **0.808**、p1742 **1.427/1.432**（= 旧行为）；
  - `VERT_DASH_RULE_W=src`（全局）：p57 **5.0**、p1683 **2.5**、p1742 出现 fills/变宽（旧全局行为，即 v43 口径）；
  - `=src + PAGES=57`：p57 **5.0**、p1683 **0.808**、p1742 **1.427/1.432** 不变（仅 p57）；
  - `=src + PAGES=57,1683`：p57 **5.0**、p1683 **2.5**、p1742 不变（多页解析正确）。
  - `test_dash_w_pages.py` **4 passed**（默认空=全局 / 列页 / 多页 / CSV 容错含中文逗号空白非法项）。
- wz6 `vert.tex` **`ae9d2f5259e12cff19e680b2a771b37d`** 逐字节 + verify PASS（231=231 / 97.2% / 2 预期 / 0 / 0+0）；pytest **603 passed**（71.82s）。

**残留（不阻塞）**：
- **R1**：build44 非字节可复现（`e4eaf3a7…` vs `9bc6cb49…`，/ID）；但本次 **内容流 0 差异**、文本/bbox 0 差异，内容完全等价。
- **R2**：线宽 5.0 是管线 `_dash_ink_seg` 源墨值；外部阈值 110 实测 5.25（Δ0.25，≤0.3）；阈值 90–150 的源墨宽度本身在 4.56–5.28 波动（t67 报告已说明），按「5.0±0.3」口径接受，非阈值判据。
- **R3**：v43（全局 src）作废、不交付；本轮只验 v44，v43 保留作对照（`docs/battle13_dash_width.md`）。
- **R4**：`VERT_DASH_RULE_W_PAGES` 的页号是**物理页号**，换书需按本书重新列页（spec §9.3/§9.4 已写明）。

---

## 1. PASS/FAIL 总表（6 项）

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 独立复跑 build44 → v44；md5 一致（/ID 差异给 text/bbox 等价）；verify exit 0（1748 / 931,200 / 丢失 0 / 越界 0+0） | **PASS（附 R1）** | build44 exit 0；重跑 md5 `e4eaf3a7…` ≠ `9bc6cb49…`，size 109,997,053 同、metadata 同、1748 页文本/行 bbox 0 差异、**内容流 0 差异** → 内容等价；恢复交付物后 verify **PASS**：1748=1748 / 931,200 / 18 预期 / 丢失 0 / 越界 0+0 |
| 2 | 独立量线宽：v44 p57 = 5.0±0.3（自己读 get_drawings，与源墨对照）；线位/线长/线心与 v42 一致 | **PASS（附 R2）** | v44 p57 `'s' w=5.000`（v42 2.784）；x 829.997 vs 830.005（Δ0.008）、y0 736.497、y1 816.497、长 80.000（Δ0）；源墨（t38）xc 829.88 / y 736.5–816.0(110)–816.75(150) / 长 79.5–80.25 / 宽 5.25(110)；5.0 与 5.25 差 0.25 ≤0.3 |
| 3 | 独立核影响面：v44 vs v42 绘图 diff 只有 p57；其余 14 个 dash 页（含 p1742 48 组）逐字节/逐 drawing 不变 | **PASS** | 自 diff：**内容流 diff=[57]**（其余 1747 页逐字节相同）；**绘图签名 diff=[57]**；**文本 diff=[]**；15 个 dash 页中 14 页逐 drawing EQUAL（p31 2 组、p1742 48 组、其余各 1 组），p1742 48 组 width 1.432×34/1.427×14 全部不变 |
| 4 | 新开关行为独立验证：默认空=旧行为；`PAGES=57` 只 p57 变；多页解析正确；unit 测试真覆盖三态 | **PASS** | 单页构建四态（§0/§6）全部符合：默认 p57 2.784/p1683 0.808/p1742 不变；`src` 全局 p57 5.0/p1683 2.5/p1742 变（v43 口径）；`src+PAGES=57` 仅 p57 5.0；`src+PAGES=57,1683` p57 5.0 + p1683 2.5；`test_dash_w_pages.py` 4 passed（含 CSV 容错） |
| 5 | wz6 `vert.tex` `ae9d2f52…` + verify PASS；pytest ≥599；spec 15 表述准确（默认/全局/按页三层） | **PASS** | wz6 `ae9d2f52…` + verify PASS（231=231 / 97.2% / 2 预期 / 0 / 0+0）；pytest **603 passed**（71.82s）；spec §9.3 三行（默认 0.040×F / `src` / `W_PAGES` 空=全局、逗号页号）、§9.1 线宽行、§9.2 v44 行（含内容流 diff）表述与本轮实测一致 |
| 6 | 报告 docs/battle13b_acceptance.md：PASS/FAIL + 字节绑定 + 线宽/影响面证据 + 残留；不改实现代码、不 commit | **PASS** | 本文件；未改 `src/`、数据、fix JSON、`output/`（v44 已恢复原字节）；未 commit（HEAD `a7b8156`） |

---

## 2. 字节绑定（开工 01:31 = 收尾 01:45）

| 文件 | 开工 | 收尾 | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `9a376a18e1ede74d8987bd6d706554a7563cc2efaeda1a6605e78f48f431f266` | 同左 | 一致（新开关：`_parse_page_csv` / `DASH_RULE_W_PAGES` / `_dash_w_src_for` / `_dash_rule_tex(seg,F,page)`） |
| `tmp_vert/battle13b/build44.sh` | `dbb6e356c1b34625b9e220ca281f0a67841afe0ced728ffafd86cbde13dab8e7` | 同左 | 一致（`VERT_DASH_RULE_W=src` + `VERT_DASH_RULE_W_PAGES=57`） |
| `docs/battle13b_dash_width_pages.md` | `c66095c7b748899b5a667d573769c2197e831e6b587e2a2c431bb1984a9fd9a3` | 同左 | 一致 |
| `spec/vertical/15_vert_dash_rule.md` | `c6eb3a0781e096c29269f6236a8d9b3601b07eb05019b60239d3464dc920917a` | 同左 | 一致 |
| `src/test/unit/test_vert_dash_rule.py` | `3b79d68680187d72e103b58d97933b18f9e2bd98147c328add7c0457d1030984` | 同左 | 一致 |
| `src/test/unit/test_dash_w_pages.py` | `67c46abb9d9929b862041071d104f20807274e53ca26473893570416d4410ba4` | 同左 | 一致（新文件） |
| `docs/vert_taskF_missed_fix.json` | `ffe24f09e69b67b0440d8721c83e963aecef928430767dc0a51f84889e72d8c5` | 同左 | 一致（数据未改） |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致（判据未改） |
| `output/wz7_full/wz7_full_v44.pdf` | md5 `9bc6cb49…` | md5 `9bc6cb49…` | 已恢复原交付字节 |

---

## 3. 复跑与门禁

- `bash tmp_vert/battle13b/build44.sh`（`SOURCE_DATE_EPOCH=0` + `VERT_DASH_RULE_W=src` + `VERT_DASH_RULE_W_PAGES=57`）：
  `开始 01:31:22` → `BUILD_EXIT=0` → `FIXTEXIT=0`（01:41:29）→ 重跑 md5 **`e4eaf3a70d27c793f8c351d5e784bf54`**。
- 与交付物 `9bc6cb49…` 对比：size **109,997,053 = 109,997,053**；metadata 相同；**1748 页文本逐页 0 差异、行 bbox/字号 0 差异、内容流逐页 0 差异**（全文 text md5 `a6a31968b224e665b777369f234f4cde` 相同）→ **内容完全等价**（R1，/ID）。
- 已把 `output/wz7_full/wz7_full_v44.pdf` 恢复为 **`9bc6cb4992f57b319887cb173090e62a`**。
- verify_vert（`--expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"`）：**exit 0 / PASS**：
  1748=1748；931,200÷942,935=**98.8%**；差异>80 字页 **18（预期 18/非预期 0）**；整页丢失 **0**；越界 span **0** + 矢量 **0**。
- 字符量与 v42 相同（931,200），符合「只改线宽、不动文本」的预期。

---

## 4. p57 线宽与位置（自己读 get_drawings）

| 项 | v42（基线） | v44（交付） | Δ | 源墨（t38/t42 外部） |
|---|---|---|---|---|
| 类型/线宽 | `'s'` **2.784** | `'s'` **5.000** | +2.216 | 5.25（阈值 110）/ 管线 w_src 5.0 |
| x | 830.005 | **829.997** | **−0.008** | xc 829.88（外部） |
| y0 | 736.497 | **736.497** | **0** | 736.5 |
| y1 | 816.497 | **816.497** | **0** | 816.0(110)/816.75(150) |
| 长度 | 80.000 | **80.000** | **0** | 79.5(110)/80.25(150) |

- **5.0±0.3 口径**：v44=5.0；与管线 `_dash_ink_seg` w_src 完全一致；与 t42 阈值 110 的 5.25 差 0.25；阈值 90–150 源墨宽度 4.56–5.28（阈值相关，见 R2）→ 通过。
- 线位/线长/线心与 v42 一致（y/长 Δ0，x Δ0.008），仅线宽变化。

---

## 5. 影响面（自己 diff）

### 5.1 全页比较（v42 vs v44）

| 维度 | diff 页 | 说明 |
|---|---|---|
| **内容流**（`xref_stream(get_contents())` 拼接） | **[57]** | 其余 **1747 页逐字节相同** |
| **绘图签名**（type/rect/width/color/fill/even_odd/items 数） | **[57]** | 其余页全部相同 |
| **文本**（`get_text()`） | **[]** | 0 页差异（字符量 931,200 同） |

### 5.2 15 个 dash 页（来自 `dash_segments.json`，63 组）

| 页 | 组数 | 绘图比较 |
|---|---|---|
| p31 | 2 | EQUAL |
| p37 / p38 / p39 | 1 / 1 / 1 | EQUAL |
| **p57** | **1** | **DIFF（唯一）**：w 2.784→5.0、x 830.005→829.997 |
| p60 / p62 / p119 / p262 / p462 / p600 / p686 / p1157 / p1683 | 各 1 | EQUAL |
| **p1742** | **48** | **EQUAL**（width 1.432×34、1.427×14 全部不变；无变宽/fill） |

- 结论：**只有 p57 变化，其余 14 个 dash 页（含 p1742 48 组）完全不动**，与 t67 报告一致（且本轮用内容流逐字节 + 全绘图签名双重独立验证）。

---

## 6. 新开关三态（独立单页构建）

命令模板：`VERT_PAGES=57,1683,1742 VERT_TMP=/tmp/vt_X [env] build_vert.py ...`（生成 3 页 PDF，按顺序对应 p57/p1683/p1742）。

| 状态 | 环境 | p57 线宽 | p1683 线宽 | p1742（48 组） |
|---|---|---|---|---|
| 默认（旧行为） | 无 `VERT_DASH_RULE_W` | **2.784** | **0.808** | 1.427/1.432（不变） |
| 全局 src（v43 口径） | `VERT_DASH_RULE_W=src` | **5.0** | **2.5** | 出现 fills/变宽（v43 风险） |
| 按页（交付） | `=src` + `VERT_DASH_RULE_W_PAGES=57` | **5.0** | **0.808** | 1.427/1.432（不变） |
| 多页 | `=src` + `VERT_DASH_RULE_W_PAGES=57,1683` | **5.0** | **2.5** | 1.427/1.432（不变） |

- 解析：`_parse_page_csv` 容忍中文逗号/空白/非法项（unit `test_parse_csv`：`' 57 ， 1683 ,x'` → `{57,1683}`、`'57,,57'` → `{57}`）；`_dash_w_src_for`：空集=True（全局）；非空=仅列页。
- 单测 `pytest src/test/unit/test_dash_w_pages.py -v`：**4 passed**（默认空=全局 / 列页 / 多页 / CSV 容错）。

---

## 7. wz6 / pytest / spec

- **wz6**：`VERT_TMP=/tmp/vert_wz6_b13b` 构建 → `BUILD_EXIT=0`；`vert.tex` md5 **`ae9d2f5259e12cff19e680b2a771b37d`**（逐字节同基线）；verify **PASS**（231=231 / 68,412÷70,373=97.2% / 差异 2 预期 / 丢失 0 / 越界 0+0）。
- **pytest**：**603 passed**（856 warnings，71.82s）。
- **spec 15**：§9.1 线宽行（源图 5.25/5.0、产物 v42 2.78→v44 5.0、仅 p57 变）、§9.2 v44 行（含内容流 diff 证明 + v43 作废行）、§9.3 三层（`VERT_DASH_RULE_W` 默认 0.040×F / `src` 全局 / `VERT_DASH_RULE_W_PAGES` 空=全局、逗号页号按页）、§9.4 按页用法与遗留——与实测一致。

---

## 8. 复现命令

```bash
cd /opt/test
# 构建 v44（src 只对 p57）
bash tmp_vert/battle13b/build44.sh
md5sum output/wz7_full/wz7_full_v44.pdf          # 9bc6cb49…
# 门禁
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v44.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
# 线宽/影响面（自己读）
/usr/bin/python3 - <<'PY'
import fitz
a=fitz.open('output/wz7_full/wz7_full_v42.pdf'); b=fitz.open('output/wz7_full/wz7_full_v44.pdf')
def content(d,i): return b''.join(d.xref_stream(x) for x in d[i].get_contents())
print('content diff', [i+1 for i in range(len(a)) if content(a,i)!=content(b,i)])
for t,d in (('v42',a),('v44',b)):
    for dr in d[56].get_drawings():
        r=dr['rect']
        if r.height>40: print(t, dr['type'], round(float(dr.get('width') or 0),3), round(r.x0,3), round(r.y0,3), round(r.y1,3))
PY
# 开关三态（单页）
VERT_PAGES=57,1683,1742 VERT_TMP=/tmp/vt_d VERT_DASH_RULE_W=src VERT_DASH_RULE_W_PAGES=57 \
  /usr/bin/python3 src/pipelines/build_vert.py data/wz7_full/wz7_full_spotting_lines_patched.json \
  data/wz7_full/wz7_full_spotting_coords.json /tmp/switch_p57.pdf source_pdf/wz7.pdf
# wz6 / pytest
VERT_TMP=/tmp/vert_wz6_b13b /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b13b.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b13b/vert.tex          # ae9d2f52…
/usr/bin/python3 -m pytest src/test/unit/test_dash_w_pages.py -v
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

---

## 9. 纪律

- 只新增 `docs/battle13b_acceptance.md`；未改 `src/`、数据、fix JSON、`output/`（v44 已恢复原字节）；未 commit/push。
- 复跑日志：`/tmp/b13bv/`（build44、v44_verify、wz6_build/verify、pytest、switch_*）；单页开关产物：`/tmp/b13bv/switch_{default,src,p57,p57_1683}.pdf`。

---

## 10. 结论

**t67 通过（可交付）**：
1. v44 只改 p57 线宽 **2.784→5.0pt**（5.0±0.3 口径通过），线位/线长/线心与 v42 一致（Δ≤0.008pt）。
2. 影响面收敛：内容流/绘图签名 diff **只有 p57**，其余 1747 页内容流逐字节相同、文本 0 页差异；14 个 dash 页（含 p1742 48 组）完全不动。
3. 开关三态正确：默认空=旧行为（p57 2.784）、按页=只 p57（5.0）、多页解析正确、全局 src=v43 口径；unit 4/4。
4. 门禁：v44 verify PASS（1748 / 931,200 / 18 预期 / 丢失 0 / 越界 0+0）；wz6 `ae9d2f52…` + PASS；pytest 603；spec 15 表述准确；未 commit。
5. v43 作废、不交付；以 v44 为准（R3）。
