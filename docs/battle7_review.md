# battle7 终审报告（t30 · 58 处缺字 + v37）

> 审查人：横排工程师（独立审查）　时间：2026-11-06 00:34–00:5x
> 审查对象：t28（58 处缺字落库 → v37）与 t29 验收报告
> 基线：HEAD `9207b2c` + 未提交工作树；本报告是唯一新增文件；未改实现代码、未 commit / push
> 输入：`docs/vert_taskF_missed_fix.json`、`tmp_vert/battle6/api_candidates_all.json`、`tmp_vert/battle7/*`、
> `output/wz7_full/wz7_full_v37.pdf`、`source_pdf/wz7.pdf`（只读，用于裁图核对）
> 原则：不采信自述——自己数落库、自己开源图裁片、自己复跑 verify / build。

---

## 0. 结论（先行）

**verdict = needs_revision。** 58 条的数量/去重/字段/证据路径/与 API 清单的一一对应均通过，v37 的
`verify_vert` 与 md5 也通过；但**插入位置有 2 处错位**（p1241 `不`、p1399 `筍`），且 **2 条证据
裁片/cell 指向了相邻字**（p1337 `翫` ×2）。前者改变了正文文字顺序，属于任务书要求排除的
「错位插入」，因此 v37 暂不可交付，也不能作为 battle7 基线；修复后需重建 v37 并重跑本报告第 5 节命令。

已确认通过的部分（细节见 §1–§4）：

| 项 | 结果 |
|---|---|
| 58 条落库：数量/去重/字段/证据路径 | ✅ 58/58 与 hanzi_list 一一对应；57 新增 + 1 去重（p634 籤）；字段齐（side 约定为空）；58 crop + 58 strip 文件均存在 |
| v37 门禁 | ✅ md5 `f4bf3a8d0dfde91eeb3653b2658d664d`；verify_vert PASS（1748=1748 / 931,106 / 差异>80 字页 18 预期 / 整页丢失 0 / 越界 0+0） |
| 字符量 | ✅ v36 931,049 → v37 931,106（+57）；55 页变化（53 页 +1、p1337 +2、p1625 +2），与 char_diff 一致 |
| 字节绑定 / 判据 / token | ✅ 三文件开工=收尾；verify_vert.py = HEAD；完整 token 及其前 12 字符均未出现在任何相关文件 |
| 插入位置抽样（≥10） | ❌ 12 张源图裁片 + 58 条列/页文本核对：56/58 位置正确；**p1241、p1399 错位 1 字**（§3.2） |
| 证据有效性 | ❌ p1337 pos11/pos16 的 cell/crop 分别指向「太」「月」，不是「翫」（§3.3） |
| build37 复跑 | ⚠️ 文本/bbox 逐页 0 差异，md5 不同（仅 TeX 时间戳元数据）——t29 R1 复现 |

---

## 1. 字节绑定（实现文件与报告）

| 文件 | 开工 00:34:55 | 收尾 | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `a5326135de89b251b0b013475277a562a37727f4d4de42d8bcdd74c380b78187` | 同左 | 一致（mtime 21:52:51，早于 t28） |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致，且 = `git show HEAD:src/test/verify_vert.py` 哈希（判据未放宽） |
| `docs/vert_taskF_missed_fix.json` | `ec64b51a358ebe83cc279e1991fd6420535eb0cd74d586de6b78c5f0bf7b6c24` | 同左 | 一致 |
| `docs/battle7_missing_chars.md` | `5c25950bc24244f7f89881428da49f3806e9fe282fc0391f6b3e9bd95bc74219` | 同左 | 一致 |
| `docs/battle7_acceptance.md` | `d987f098c111b7e9e55db9649fc95e3ffb85d8edec650bdff864c67031af4d59` | 同左 | 一致 |

- `git status` 中 t28 范围：fix JSON（M）+ battle7 报告（??）+ tmp_vert/battle7 证据；t29 仅新增 acceptance 报告。
  `build_vert.py` 的 M 是 battle3–6 遗留未提交改动（mtime 21:52，早于 t28），非 t28 产物。
- token：`src/tools/api_*_run.py` 只 `open('/tmp/paddle_token').read()`；用完整 token（40 字符）及前 12 字符
  在全部相关文件（报告/fix JSON/tmp_vert/battle7/api 工具）中检索，**0 命中**。
- 本审查只写本文件与 `/tmp/t30/`，未改实现代码，未 commit（HEAD 仍 `9207b2c`）。

---

## 2. 58 条落库核对（通过）

- `api_candidates_all.json` 的 `hanzi_list` = 58 条，全部 `complete=true`；`docs/vert_taskF_missed_fix.json`
  的 `class=missing_char` = 69 条 = 58（本轮）+ 11（t24 既有）。
- **一一对应**：按 (page, pos, ch, col±2pt) 匹配，58/58 每条恰好命中 1 条 fix 条目（无多落、无漏落、无重复 key）；
  58 条内部无「同 page/pos 异字」冲突。
- **57 新增 + 1 去重**：11 条 t24 既有项为 p263/p263/p445/p459/p459/p473/p473/p508/p592/p599/p620
  （`「`×5、`」`×4、`。`×3、`一`、`媽`），加上 p634 pos22 `籤` 即 battle6 报告所述 12 条既有；
  p634 本轮只补证据、不重复落库——v36 与 v37 该列都只有一个 `籤`，无 `籤籤`。
- 字段：`page/col/pos/ch/side/source/confidence/ratio/exp_len/crop/cell/strip/shape/complete` 均存在；
  `side` 按 t28 约定为空串；`source='api_strip'`、`ratio` = API confidence、`exp_len=len(text)`，58/58 一致。
- 证据：58 条 `crop` 与 58 条 `strip` 文件全部存在（2.9KB–708KB）；`complete=true`、`shape` 有 w/h/fill。
  **但** p1337 pos11/pos16 的证据 cell/crop 内容错误（§3.3），属证据有效性而非路径缺失。
- 参照：t29 报告称「58 条字段全齐、与 t27 逐条一致、0 冲突」——数量/字段层面与本次核对一致；t29 未抽查到
  §3.2/§3.3 两组问题。

---

## 3. 源图裁片复核（≥10 条）

### 3.1 抽样（12 条，均从 `source_pdf/wz7.pdf` 8× 自裁，不读实现者裁片）

| 页/pos/字 | 源图读数 | 判定 |
|---|---|---|
| p50 pos3 竊 | 竊 | ✅ |
| p85 pos42 峴 | 峴 | ✅ |
| p141 pos17 謄 | 謄（源书双字，OCR 单字） | ✅ |
| p231 pos15 人 | 人 | ✅ |
| p329 pos7 刺 | 刺（源书双字） | ✅ |
| p411 pos6 粧 | 粧 | ✅ |
| p527 pos22 宿 | 宿 | ✅ |
| p634 pos22 籤 | 籤（去重项，v36 已有） | ✅ |
| p1188 pos7 朗 | 朗（源书双字） | ✅ |
| p1337 pos11 翫 | 源插入位（娘/翫/燈）**有翫**；但给定 cell 处是「太」 | ⚠️ 证据错（插入本身对） |
| p1397 pos1 條 | 條（源书双字） | ✅ |
| p1689 pos27 翫 | 翫 | ✅ |

另查 p1241/p1399 的源图与 v37 文本（见 §3.2）；p1337 pos16 源插入位（月/娘/翫/燈）**有翫**，但证据 cell 处是「月」。

### 3.2 blocker：p1241、p1399 插入位置错 1 字（源图 vs v37 文本）

| 页 | 字 | OCR 原文（节选） | 源图顺序 | v37 实际 | 结论 |
|---|---|---|---|---|---|
| p1241 | 不 | `…央你，依依？」`（行首还有一个 `」`） | `…，依 不 依 ？` | `…依依不？` | ❌ 错位 |
| p1399 | 筍 | `…消坐了。茶來，…`（行首还有一个 `」`） | `」。筍 茶 來` | `…茶筍來…` | ❌ 错位 |

- 证据：`/tmp/t30/crops/p1241_src.png`（，/依/不/依/？）与 `/tmp/t30/crops/p1399_src.png`（」/。/筍/茶/來）；
  v37 全文检索 `依不依`=0、`依依不`=1；`筍茶`=0、`茶筍`=1。
- 根因（代码级）：
  1. `src/pipelines/build_vert.py:933` 先执行 `fix_split_brackets(sl[...])`，把这两行行首的 `」` 归位到上一列，
     该行文本长度减 1；
  2. `:945` 之后才执行 `_apply_missed_fix()`；`:524-532`（插入语句在 `:532`）直接用 API 的 `pos` 在当前（已缩短的）行上插入
     `sl[k][idx][:pos] + ch + sl[k][idx][pos:]`。
  3. 这两条的 `pos`（p1241 pos33、p1399 pos13）来自 API 对**原始 OCR 行（含行首 」）**的计数；行首 `」`
     被移走后，同一 `pos` 落到后一个字之后 → 1 字错位。其余 56 条不含被归位的行首闭引号，位置不受影响。
- 修复建议（二选一，需重建 v37）：
  - 在 `_apply_missed_fix` 内按当前行文本重定位：若该行行首的闭引号已被 `fix_split_brackets` 移走，
    把 pos 减去被移走的行首字符数（或按「插入点前后各 N 字」匹配）；
  - 或把 missing_char 插入提前到 `fix_split_brackets` 之前执行；
  - 或数据侧把 p1241 pos33→32、p1399 pos13→12（仅修这两条，不解决同类新条目）。
- 验收影响：v37 的文字顺序与源书不一致，属「错位插入」；verify_vert 只查页数/字符量/越界，无法拦截该类错误。

### 3.3 medium：p1337 两条证据 cell/crop 指向相邻字（插入位置本身正确）

| 项 | 给定 cell | 源图插入位 | 证据 crop 内容 | 判定 |
|---|---|---|---|---|
| p1337 pos11 翫 | `[604.9,634.9,641.5,654.3]`（=「太」） | 娘与燈之间（y≈778）有翫 | `all_insert_crops/02788.png` = 太 | ⚠️ 证据错 |
| p1337 pos16 翫 | `[73.3,538.8,98.7,558.3]`（=「月」） | 月与燈之间（y≈585）有翫 | `all_insert_crops/02790.png` = 月 | ⚠️ 证据错 |

- v37 文本两条都正确（`…吳月娘翫燈…`，两处），源图插入位也确有翫；问题只在 `cell`/`crop` 元数据
  （cell 索引比 pos 小 4.1/1.4 字），使报告 §5「其余 34 条沿用的裁片」对这 2 条不成立。
- 影响：不影响 v37 文字，但影响「每条有源墨证据」的可核查性；t29 抽样未覆盖这两条。
- 修复建议：按插入位（v37 中该字所在 y）重裁 `crop/cell` 并更新 §5 抽样；不必改正文。

### 3.4 其余 56 条位置核对

- 对全部 58 条做「v37 页文本应含 OCR+ch@pos（含行首 」 归位、一→「 归一化）」检查：
  56/58 命中；不命中的只有 §3.2 两条。p411/p1330/p1397/p1689 的个别不匹配经复核是**文本提取
  边界/标点归一化**（如 p1397 列首「赤」被列框裁掉、p1689 页码 ⑲），非插入错误：
  v37 全文分别含 `搖拽鞦韆鬪艷粧`、`試知梅花問主人`、`赤條條的見閻王`、`…翫花樓上。⑲`。
- 4 条「源书双字、OCR 单字」项（p141 謄、p329 刺、p1188 朗、p1397 條）v37 均为双字，位置正确。

---

## 4. v37 门禁与复跑

- 交付物：`output/wz7_full/wz7_full_v37.pdf`，md5 **f4bf3a8d0dfde91eeb3653b2658d664d**，1748 页。
- `verify_vert`（带 `--expect-low`）**PASS**：1748=1748 / 931,106÷942,935=98.7% / 差异>80 字页
  **18（预期 18 / 非预期 0）** / 整页丢失 0 / 越界 span 0+矢量 0 / exit 0。
- 字符量：v36 931,049 → v37 931,106（+57）；逐页 55 页变化 = 53 页 +1、p1337 +2、p1625 +2；
  `tmp_vert/battle7/char_diff.json` 55 条与报告 §3 表一致。
- **独立重建**（等价 build37.sh，OUT 改到 `/tmp/t30/v37_rebuild.pdf`，避免覆盖 out-of-scope 的交付物）：
  BUILD/FIX exit 0；md5 `badf5eaf405066a5d20e65177ceef4ce` ≠ 交付物；但
  **1748 页文本逐页 0 差异、words bbox 逐页 0 差异、text md5 均为 `1c0679ea80cc2e57f5b9ffc04504706a`**；
  差异仅 PDF 元数据（creator `TeX output …:0018` vs `:0045`、creationDate、大小 +2B）→ 与 t29 R1 一致：
  build37 **内容可复现、字节不可复现**。重建产物同样含 §3.2 的两处错位（证明不是旧产物残留）。
- pytest：**590 passed**（复核）。
- 说明：未直接执行会覆盖 `output/wz7_full/wz7_full_v37.pdf` 的 `bash build37.sh`；用同一 BUILD+FIX 两条命令
  重定向到 /tmp 并比对，覆盖了「构建可复跑 + 内容一致」这一点。

---

## 5. 修复后需重跑的命令

```bash
# 1) 修复 pos（代码或数据）后重建 v37（覆盖交付物前先留备份）
bash tmp_vert/battle7/build37.sh
# 2) 门禁
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v37.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
# 3) 重点回归（本次两处错位）
/usr/bin/python3 - <<'PY'
import fitz
d=fitz.open('output/wz7_full/wz7_full_v37.pdf')
f=lambda p: ''.join(d[p-1].get_text().split())
assert '依不依' in f(1241) and '依依不' not in f(1241)
assert '筍茶' in f(1399) and '茶筍' not in f(1399)
print('OK')
PY
# 4) 顺带修正 p1337 两条证据 cell/crop，并更新 docs/battle7_missing_chars.md §0/§5 文案
```

---

## 6. 其他低级别问题（不改变本轮 verdict，修复时顺手处理）

1. **build37 非字节可复现**：仅 TeX 时间戳元数据差异（t29 R1）；建议固定 `SOURCE_DATE_EPOCH` 或在校验中
   以 text/bbox 为口径。
2. **报告 §0 字符量文案**：`docs/battle7_missing_chars.md` §0 写「55 页各 +1（p1337 +2）」，漏了
   **p1625 +2**（§3 表与 char_diff 正确）；实际 53 页 +1、p1337 +2、p1625 +2。
3. **报告 §5 抽样标签**：p779 标「遮」实为「遞」、p781 标「紅」实为「舡」（t29 R3）；本轮
   `sample58.png` 仍可见该两格标签与裁片不一致。
4. **11 条 t24 既有 missing_char 无证据字段**（p263 等）：不属本轮 58 条，但同属 `missing_char` 类；
   建议在报告中注明，避免「69 条均有证据」的误读（t29 R4）。
5. **本轮 24 条抽样未覆盖** p1241/p1399（错位）与 p1337（证据错）——修复后建议把「行首含闭引号的条目」
   「源书双字条目」「p1337 两条」加入固定抽样清单。

---

## 7. 结论

- **通过**：58 条与 API hanzi_list 一一对应（57 新增 + 1 去重 p634）、字段齐、证据路径齐、无冲突；
  v37 md5/verify/字符量全部符合报告；字节绑定稳定、`verify_vert.py` 与 HEAD 相同（判据未放宽）、token 未外泄；
  pytest 590。
- **不通过（blocker）**：p1241 `不`、p1399 `筍` 因行首闭引号先归位、`missing_char` 后插入而错位 1 字；
  v37 文字顺序与源书不符，不可交付、不可作 battle7 基线。p1337 两条证据 cell/crop 指向相邻字（medium）。
- **判定：needs_revision。** 修复 §3.2（并顺带修 §3.3 证据、§6 文档项）后重建 v37，重跑 §5 命令即可复审。
