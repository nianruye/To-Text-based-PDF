# content_eval PDF 口径修复 终审（t130 → t132 → t134 修复 → t135 round-3）

> 审查人：质量审查员（独立第三方，不参与实现）　日期：2026-11-08 19:52–20:05
> 对象：t128 首修 + t132 修复轮 + t134 修复轮（content_eval：回归/CER 读产物 PDF、指标、位置口径、gate）
> 基线：HEAD `84d6b95`（未 commit）　**未改实现/数据/fix JSON/output；未 commit**
> 依据：`spec/governance/CONTENT_EVAL.md`（v1.1）、`docs/content_eval_acceptance.md`（t123）、`docs/content_eval_acceptance_v12.md`（t129）
> **Round-3 结论：needs_revision（FAIL）**——t134 修好了 `?` 同位屏蔽并补了 gate 字段，但 **gate 结论与 CER 阈值矛盾（CER 9.6%/5.7% 却判 CONTENT_AUTO_PASS）**、**ring「position 54/54」是伪口径**（49/54 实为页级 fallback，`_near_ring` 在 (0,0) 也返回命中）、**missing_char 位置公式不可靠**（按 spec ±0.5 格仅 23/64，且 19/64 fallback 仍算通过）。

---

## 0. Round-3：PASS/FAIL 总表（对照验收项）

| # | 验收项 | 结论 | 实测（t134 版） |
|---|---|---|---|
| 1 | 回归/CER 确实读产物 PDF，无 lines 回退 | **PASS** | verify 命令 **exit 0**；with_punct 0.0961（I=109/D=49/S=218）、han_only 0.0570；`normalization_audit` 完整；空 PDF/缺页 exit 3；lines 不参与指标（沿袭 t132，未回退） |
| 2 | 代码审查：邻域匹配/ring 值匹配、t97 假项剔除、单测防回退 | **FAIL（high）** | t97 剔除与 0/3 正确 ✓；`?` 同位屏蔽已修 ✓（见 §2.1）；但 **ring position 54/54 是假的**（真实位置 5/54，49/54 由 `_near_ring` 内部页级 `○+digits` 命中，忽略 x/y）；missing_char 位置公式与 `cell` 口径不一致（p85/p469/p527 已知通过却判 miss、p1330 已知 1.23 格却判 hit）；单测 15 passed 但 **无 gate/位置伪口径用例** |
| 3 | 独立抽样 ≥5 must-pass + ≥3 diagnostic | **PASS（抽样完成）** | 7 条 must-pass：按 fix `cell` 口径 4/7 ≤0.5 格（p634 籤 0.05、p85 峴 0.26、p469 青 0.08、p527 宿 0.38），3/7 超差（p411 粧 0.63、p1330 知 1.23、p1703 四 1.56）；3 条 diagnostic 0/3 正确（V/剌剌/螃 不在对应页），i=26 已剔除 |
| 4 | 输出字段可被 quality_gate 消费（must_pass、missing_ok、ring_ok、cer_*、diagnostic） | **FAIL（blocker）** | 字段已出现（`gate.missing_ok/ring_ok/verdict/by_split`），但 **verdict 错**：CER 0.0961（>drop 0.050）、han_only 0.0570（>drop 0.040）→ spec §6.2 应为 **CONTENT_REJECT**，实输出 **CONTENT_AUTO_PASS**；`by_split` 硬编码 `{'wz7': {must_pass}}`（无 wz6/heldout、无分栏 CER）；无阈值逻辑 |
| 5 | 出具报告 verdict + findings | **PASS** | 本文件 |

### 0.1 复跑（任务给定命令）

```bash
/usr/bin/python3 src/tools/content_eval.py --gold data/punct_eval/content_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --book wz7 \
  --out tmp_vert/bench/content_review_v12.json
# [content_eval] with_punct CER=0.0961 han_only CER=0.0570 | must-pass 64/64 + 54/54 => True
# exit 0；8 页（57/97/159/704/705/830/898/1718）
```

- 输出新增：`gate={missing_ok:true, ring_ok:true, verdict:'CONTENT_AUTO_PASS', by_split:{'wz7':{must_pass:true}}}`；`regression.must_pass_items.missing_char_confirmed.position_hits=45/fallback_hits=19`；`battle4_ring.position_hits=54/fallback_hits=0, calibration_offset=[0.36,-2.54], n_offset_samples=5`。
- **单测**：`pytest src/test/unit/test_content_eval.py -q` → **15 passed**。
- **基线**：`tmp_vert/bench/content_v51_pdf.json`（md5 `5fb31fc4…`）CER 0.0961、must_pass True —— 与输出一致。
- **字节绑定**：`content_eval.py` `54f4286a4692eea32f8c934bbfa64440daf5e4f36993c4b620f70017e08fd6e6`；`test_content_eval.py` `1c8c99552351a6c94fcd6dbde8c532f13e9e1a18d3d90267dee160902c32790b`；`v51.pdf` md5 `38d6656b…`；HEAD `84d6b95`。

---

## 1. 本轮的修复确认（PASS）

| 项 | 结论 | 证据 |
|---|---|---|
| `?` 同位屏蔽 | **已修** | `drop={i|gold[i]=='?'}`；实测：`('甲?乙','X甲乙')→('甲乙','X乙')`、`('甲?乙','甲乙丙')→('甲乙','甲丙')`、`('?甲','X甲')→('甲','甲')`、`('甲??乙','甲乙丙丁')→('甲乙','甲丁')`、无 `?` 不变 ✓；单测 #15 断 4 组字符串 ✓ |
| gate 字段 | **字段已出现** | `missing_ok/ring_ok/verdict/by_split` 均输出（但 verdict 逻辑错，见 §2.2） |
| 位置/fallback 单列 | **已输出** | `position_hits/fallback_hits` 逐项 + 汇总（但 ring 计数失真，见 §2.3） |
| PDF-only / 指标 / 审计 | 保持 | I/D/S 拆分、N=0→null、`normalization_audit`、空 PDF/缺页 exit 3、lines 不参与指标 |
| 单测 | 15 passed | 含 #15 doubt mask 字符串用例 |

---

## 2. 关键实测与代码审查（Round-3）

### 2.1 `?` 同位屏蔽（PASS）

见 §1；5 组用例全部符合 spec §3.1-5「gold 删 ?，pred 同序位删一字」。**该 finding 关闭**。

### 2.2 gate verdict 与 spec §6.2 矛盾（**blocker**）

```python
verdict=('CONTENT_AUTO_PASS' if reg and reg['must_pass'] else 'REGRESSION_BLOCKED'),
by_split={'wz7': {'must_pass': bool(reg and reg['must_pass'])}}),
```

- spec §6.2：`CER_with_punct` auto ≤0.020 / manual ≤0.050 / drop >0.050；`CER_han_only` auto ≤0.015 / manual ≤0.040 / drop >0.040；**auto 需要两栏都满足 + must-pass 全过**。
- 实测 CER **0.0961 / 0.0570**：两栏均超 drop 线 → 应为 **CONTENT_REJECT**（且 must-pass 本身的 64/64 是 fallback 抬高，见 §2.3/§2.4）。
- 代码里**没有任何阈值逻辑**（grep `0.020`/`0.050` 无命中）；`by_split` 是字面量 `'wz7'`，不含 wz6/heldout、不含分栏 CER。
- 结论：`gate` 字段虽出现，但**结论错误**——质量门禁若消费会**把 9.6%/5.7% CER 的产物判为 AUTO_PASS**，这是本轮最严重问题。

### 2.3 ring 「position 54/54」是伪口径（**high**）

- 54 条 ring：**number > 50 共 49 条**（92×10、86×8、56×5、78×4、87×3、93×3、99×3、55×2、61/65/66/67/75/81、54 各 1）、**cp 为空 33 条**、**`_ring_candidates` 为空 31 条**（number>50 且 cp 空）。
- `_ring_candidates(number, cp)` 只支持 1–50（①–⑳/㉑–㉟/㊱–㊿）与 cp；对 >50 返回**空集**。`_near_ring(..., x, y)` 的位置分支因此不可能命中，落到内部页级 `○+digits` 搜索且**不受 x/y 约束**。
- 实测反证：`_near_ring(pc[1708], 54, '', 0.0, 0.0)` → **'○54'**（野生坐标也返回命中）；`_near_ring(pc[1696], 34, 'U+2463', 0,0)` → '㉞'；且 fix JSON 的 cp 与 number 不一致（p1695 #32 cp=U+3252=㉒，产物实际是 ㉜），候选集本身不可靠。逐条按「target 字符在 calibrated ±20pt」复算：**真实位置命中 5/54，49/54 为页级 fallback**（与报告 position_hits=54/fallback_hits=0 相反）。
- 标定 offset `(0.36,−2.54)` 只用 **5 个样本**（number≤50/cp 的条目）做中位，且样本来自**同一批被评条目**（循环标定）→ 不能发现全局 ring 位置漂移；对 49 条 >50 的条目也不适用。
- 结论：ring must-pass 仍是「页级存在」而非「位置一致」；`position_hits` 计数把内部 fallback 算成 position，必须修正。

### 2.4 missing_char 位置公式不可靠（**high**）

t134 用 `col` 列框 x 中心 + `pos×step`（`step=(col 高)/len(row_text)`，`row_text` 由 fix `col` 反查 coords 行）作为期望位置，`_near(...)` 默认 **±20pt**。

- **与 `cell` 口径不一致**：按 fix JSON 的 `cell`（t123/t129 使用的期望格）复算 7 条抽样——p85 峴 0.26 格、p469 青 0.08、p527 宿 0.38 均 ≤0.5 格（应 pass），但 t134 公式判 **miss**（`±20pt 位置=False`）；p1330 知 1.23 格（应 fail）却被判 **hit**。
- 逐条复算（64 条）：
  - t134 公式 + ±20pt：**45/64**（与其报告一致）；
  - 同一公式 + **±0.5 格（step 中位 25.9 → 容差 ~13pt）**：**23/64**；
  - fix `cell` 口径 + ±0.5 格：**57/64**（7 条超差：p411 粧 0.63、p1330 知 1.23、p1689 翫 0.78、p1219 纖 0.88、p1419 慌 0.91、p1678 步 0.51、p1703 四 1.56）；
  - 页级 contains：**64/64**（即 must_pass 的实际依据）。
- 结论：`position_hits=45` 既不是 spec ±0.5 格，也不是 t123 的 `cell` 口径；19 条 fallback 仍被算作 pass → must-pass 64/64 不满足 §4.4.1。

### 2.5 容差 ±20pt ≠ spec ±0.5 格（**medium**）

`_near` 默认 `tol=20.0`（step 22–29pt 时约 0.7–0.9 格），spec §4.4.1 要求 ±0.5 格；`_near_ring` 同样是 ±20pt。应按本书/本页 step 归一。

### 2.6 单测覆盖（low）

15 例全过，但**没有**：gate verdict/阈值用例（AUTO/MANUAL/REJECT/BLOCKED 四档）、ring 伪位置（`_near_ring` 野生坐标）、missing_char 位置公式 vs `cell`、`by_split` 断言。新增的 gate/位置代码实际上未被测试锁定。

### 2.7 `by_split` 硬编码（low）

`by_split={'wz7': {'must_pass': ...}}` 是字面量；gold 条目已带 `split` 字段（t111），可据此生成 wz6/wz7/heldout 分档（含两栏 CER/I/D/S），当前未用。

---

## 3. must-fix 清单（Round-3 findings）

| id | severity | problem | requiredFix |
|---|---|---|---|
| **R3-F1** | **blocker** | gate verdict 与 spec §6.2 矛盾：CER 0.0961/0.0570（两栏均 >drop）却输出 `CONTENT_AUTO_PASS`；代码无阈值逻辑；`by_split` 硬编码 `{'wz7': must_pass}`（无 wz6/heldout、无分栏 CER） | 实现 §6.2 三档阈值（auto/manual/reject）+ 回归 BLOCKED 优先级；两栏都满足才 auto；`by_split` 由 gold `split` 聚合（wz6/wz7/heldout × 两栏 CER/I/D/S），`missing_ok/ring_ok` 不得包含 fallback 命中 |
| **R3-F2** | **high** | ring「position 54/54」为伪：number>50 有 49/54、`_ring_candidates` 为空 31/54、cp 空 33/54 → `_near_ring` 页级 `○+digits` 命中忽略 x/y（实测 `_near_ring(...,0,0)` 返回 '○54'/'㉞'）；真实位置 5/54；offset 由 5 条同批样本中位标定（循环）；cp 与 number 不一致（#32 cp=㉒、实际 ㉜） | 为 >50 与 cp 空实现**位置化**的 `○+digits` 匹配（把 ○ 与数字组成 bbox/位置，按 x/y 邻域判定）；位置不命中一律 fallback_hit，不得计入 position_hits；offset 在独立标定样本上估计（或固定先验），并输出标定样本 id 与残差 |
| **R3-F3** | **high** | missing_char 位置公式（col x 中心 + pos×step）与 `cell` 口径不一致：p85/p469/p527 已知 ≤0.5 格被判 miss、p1330 已知 1.23 格被判 hit；按 spec ±0.5 格仅 23/64（cell 口径 57/64），19/64 fallback 仍算 pass → must_pass 64/64 不满足 §4.4.1 | 期望格改用 fix `cell`（或 coords+pos 与产品实际行文本长度一致的口径）；容差按 step 归一（±0.5 格）；fallback 只作 `fallback_hit`，不得计入 passed；7 条超差输出 `position_shift` 并按 spec 判 fail（或显式 spec 修订） |
| **R3-F4** | **medium** | `_near`/`_near_ring` 容差 ±20pt ≈ 0.7–0.9 格，非 spec ±0.5 格 | 改为 `tol=0.5*step`（step 由列框/行文本或 `cell` 高得到） |
| **R3-F5** | **low** | 单测无 gate 阈值、ring 伪位置、position 公式 vs cell、by_split 用例 | 补 4 类用例（含「CER 超 drop → REJECT」「`_near_ring(...,0,0)` 不得算 position」「cell 口径 57/64」） |
| **R3-F6** | **low** | `by_split` 字面量硬编码，gold `split` 字段未用 | 由 gold 分组生成；缺 split 时 unscored（不得 AUTO） |

> 已关闭：Round-2 的 R2-F4（`?` 同位屏蔽）已修并有用例；R2-F3 的字段名（missing_ok/ring_ok/gate/by_split）已出现但语义/取值错误（并入 R3-F1）。

---

## 4. 复现命令

```bash
cd /opt/test
# 1) 任务给定 verify（exit 0）
/usr/bin/python3 src/tools/content_eval.py --gold data/punct_eval/content_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --book wz7 \
  --out tmp_vert/bench/content_review_v12.json

# 2) 关键反证：ring 伪位置
/usr/bin/python3 - <<'PY'
import sys, json; sys.path.insert(0,'src/tools'); import content_eval as ce
pc=ce.pdf_chars('output/wz7_full/wz7_full_v51.pdf')
print(repr(ce._near_ring(pc[1708],54,'',0.0,0.0)))   # -> '○54'（野生坐标仍命中）
PY

# 3) 7 条 must-pass 抽样与 cell/±0.5 格复算（§2.4 表）

# 4) 单测
/usr/bin/python3 -m pytest src/test/unit/test_content_eval.py -q   # 15 passed
```

| 文件 | sha256 / md5 |
|---|---|
| `src/tools/content_eval.py` | `54f4286a4692eea32f8c934bbfa64440daf5e4f36993c4b620f70017e08fd6e6` |
| `src/test/unit/test_content_eval.py` | `1c8c99552351a6c94fcd6dbde8c532f13e9e1a18d3d90267dee160902c32790b` |
| `output/wz7_full/wz7_full_v51.pdf` | md5 `38d6656bf37720ff0277d7bd74a5d87a` |
| `tmp_vert/bench/content_v51_pdf.json` | md5 `5fb31fc4dbbf72a3e76aad6eb7033fe5`（CER 0.0961 / must True） |
| HEAD | `84d6b95`（未 commit） |

---

## 5. 结论与建议

**Round-3 verdict：needs_revision（FAIL）**。

- **成立**：PDF-only（exit 3、无 lines 回退）、gold 可读+按书过滤、I/D/S、N=0、审计字段、`?` 同位屏蔽、t97 剔除、15 单测、CER 0.0961/0.0570 可复现。
- **不成立（必须修）**：①**gate verdict 错**（CER 超 drop 却 AUTO_PASS；无阈值；by_split 硬编码）；②**ring 位置 54/54 是伪口径**（真实 5/54，49 条页级 fallback，`_near_ring(0,0)` 也命中；offset 循环标定 5 条）；③**missing_char 位置公式不可靠**（±0.5 格仅 23/64，cell 口径 57/64，19 条 fallback 算 pass）→ must-pass 64/64 不满足 §4.4.1；④容差 ±20pt ≠ ±0.5 格；⑤gate/位置无单测。
- **建议顺序**：R3-F1（gate 阈值+by_split+fallback 不计 passed）→ R3-F2（ring 位置化，含 >50 的 ○+digits 与独立标定）→ R3-F3/F4（cell 口径 + ±0.5 step + position_shift 处理）→ R3-F5/F6（测试与 split）；完成后重跑 verify + 单测 + wz6/wz7/heldout 分档表再复验。

---

## 附录：Round-2（t133）与 Round-1（t130）存档

- **Round-2（t132 修复后）**：verdict needs_revision。已修 F1（gold 可读）、F5a（I/D/S、N=0、审计）、F8（PDF-only exit 3）、F9（死代码）；未修 F2（64 位置 57/64）、F3（ring 49/54 页级 fallback）、F4（gate 字段缺失）、F6（manifest）、F7（硬编码）；`?` 屏蔽 bug（R2-F4）→ 本轮已修。
- **Round-1（t128）**：verdict needs_revision；F1 verify 命令 exit 2（gold list 不被接受）、F2 64 位置、F3 ring fallback、F4 门禁字段、F5 指标/审计、F6 manifest、F7 硬编码、F8 静默回退 lines、F9 死代码。
