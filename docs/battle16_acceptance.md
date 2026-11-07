# battle16 独立验收（t80 · round 2 · v47）

> 验收人：验证评审员（独立验证方，round 2）　日期：2026-11-08 01:08–01:26
> 基线：HEAD `e896f2d`（未 commit 工作树）；**未改实现代码、未改数据/fix JSON、未 commit/push**
> 对象：t76（battle16 修复 → v47）+ **t79（repair-round-2：仅报告重写）**
> 主产物：`output/wz7_full/wz7_full_v47.pdf`（md5 **`5e8d30318737395fe71c0d7434b988bf`**，1748 页；t79 重建后 /ID 变化，内容与 t76 交付 `71decc87…` **0 差异**）
> 方法：自己重跑 build47、自己读 v46/v47 逐页文本与全书 `﹁﹂` 扫描、自己裁 p692 源图核对 t79 的判读、自己跑 wz6/pytest。

---

## 0. 结论

**PASS（round 2 可交付）**，带 1 条中等残留（已按验收「或报告逐条理由」口径登记）：
- **F1（中，残留）**：v47 产品文本中 **p692 仍余 2 处 `﹁﹂`**（t79 仅报告、代码收敛登记下一轮）。t79 报告已给出两处原文 + 源图判读（我自裁核对：源 r12 `…花慵戴。」`、r13 `〔東甌令〕`；r15 `…泪盈腮。」`、r16 `〔感皇恩〕`、r17 `「呀！…`）→ 报告「逐条理由」成立；**产品代码未清，下一轮修**。
- t79 其余目标均达成：F1 口径限定为「`_fix_yi_after_name` 候选内无第二处」；v47 剩余 11 处 `﹁﹂` **逐条列表 + 判读 + 下一轮范围**（我扫描的页/上下文与报告表格完全一致）；p679 r8 qfix 历史遗留登记 §5。

**核心数字**：
- 复跑 build47 → md5 `4ef58972e9c8e0351d139c68bac97ac0` ≠ 当前 `5e8d3031…`（/ID），但 **size 109,995,239 相同、metadata 相同、1748 页文本/行 bbox/内容流逐页 0 差异** → 内容完全等价；已恢复当前交付字节 `5e8d3031…`。
- 当前 v47 与 t76 交付 `71decc87…`（t77 验收时备份）**文本/内容流/bbox 0 差异**；t79 重建只改 /ID。
- verify_vert（--expect-low）**PASS**：1748=1748 / **931,189** / 差异>80 字页 18（预期 18/非预期 0）/ 整页丢失 0 / 越界 span 0+矢量 0。
- **F1（p679 r5）**：v47 `﹁一壁厢舞着…`（一保留、﹁插入），p679 字符 v46→v47 **+1** ✓；p703 `﹁一到如今`(+1)、p704 `﹁一個兒`(+1) ✓；页码行 p148/188/230/1306 与 v46 逐字相同 ✓。
- **F2**：v47 `p833/p888/p984` 行内 `﹁﹂`=0 ✓；**p692 仍 2 处**（`…花慵戴。﹁﹂﹁一東甌令…`、`…泪盈腮。﹂﹁感皇恩﹂﹂﹁﹂﹁呀！…`）；**全书 11 处 / 8 页**（p78/371/474/641/662×2/679/692×2/1652×2）= t79 报告 §2.2 表格逐条一致（v46 18 处/13 页 → v47 11 处/8 页）。
- **字符量**：v46 931,198 → v47 **931,189（−9）**；逐页 9 页（p679 +1 / p692 −2 / p703 +1 / p704 +1 / p831 −2 / p833 −1 / p888 −4 / p900 −1 / p984 −2）与报告 §3 **完全一致**。
- wz6 `vert.tex` **`ae9d2f5259e12cff19e680b2a771b37d`** + verify PASS；pytest **610 passed**；判据未改；无 token。

**残留**：
- **F1（中，产品）**：p692 两处 `﹁﹂` 未清（报告已判读，代码下轮）；同时 p692 `感皇恩`/`東甌令` 名括号待补。
- **F2（低）**：v47 剩余 11 处 `﹁﹂`（含 p78/371/474 需源图判读「两句相接」）——t79 已逐条列表并给出下一轮范围；本轮不清。
- **F3（低）**：p679 r8 `呀！﹁壁厢` qfix 历史遗留吞字（v44–v47 同），t79 已限定 F1 口径并登记 qfix 轮。
- **F4（低）**：p704 `﹂：`/p705 `：`、p1703 枚举数字未补（既有登记）。
- **F5（说明）**：v47 产物 md5 由 t76 `71decc87…` 变为 t79 重建 `5e8d3031…`（/ID），内容 0 差异；如交付需固定 md5，应在报告中同步（t79 报告已说明 /ID）。

---

## 1. PASS/FAIL 总表（5 项）

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 独立复跑 build47 → v47；verify exit 0（1748 / 丢失 0 / 越界 0+0）；wz6 `ae9d2f52…` + PASS；pytest ≥609 | **PASS** | build47 exit 0；重跑 md5 `4ef58972…` ≠ 当前 `5e8d3031…`，size/metadata/1748 页文本/bbox/内容流 0 差异 → 内容等价；verify **PASS**：1748=1748 / 931,189 / 18 预期 / 丢失 0 / 越界 0+0；wz6 `ae9d2f52…` + PASS；pytest **610 passed** |
| 2 | F1：p679 r5 含 `﹁一壁厢`（一保留、﹁插入）；p679 +1；全书同类复核无第二处吞字 | **PASS** | v47 p679 `﹁一壁厢舞着…` ✓、+1 ✓；p703/p704 同类插入 ✓；页码行不变 ✓；`_fix_yi_after_name` 候选（12 条）内无第二处；t79 已把口径限定为「候选内」，p679 r8 qfix 历史遗留另登记（F3） |
| 3 | F2：p692/p833/p888/p984 行内 `﹂` 已清；全书 `﹁﹂` 残留 0 或报告逐条理由 | **PASS（报告口径，附 F1 残留）** | p833/p888/p984 已清（0）✓；**p692 仍 2 处**（产品未清）；t79 报告已给两处原文+源图判读（自裁核对源 r12/r13/r15/r16/r17 与报告一致），并**逐条列出全书 11 处 + 判读 + 下一轮范围**（与我扫描的页/上下文完全一致）→ 按「或报告逐条理由」通过；产品代码修登记下一轮（F1） |
| 4 | 字符量对账 v46→v47 = 插入 + 删除；逐页 diff 与报告一致（含 p679） | **PASS** | −9；逐页 9 页与报告 §3 完全一致；+3−12=−9；文本 diff 9 页 |
| 5 | 报告 docs/battle16_acceptance.md：PASS/FAIL + 字节绑定 + 抽样表 + 残留；不改实现代码、不 commit | **PASS** | 本文件；未改 `src/`、数据、fix JSON、`output/`（v47 已恢复 `5e8d3031…`）；未 commit（HEAD `e896f2d`） |

---

## 2. 字节绑定（开工 01:08 = 收尾 01:26）

| 文件 | 开工 | 收尾 | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `6bd94b5b214e3ef5704582a1f8556024faa29956e0edd6d90d68e0595f653007` | 同左 | 一致（t79 未改实现） |
| `tmp_vert/battle16/build47.sh` | `99464b5b280863e34a4c80293569b3409cfbfa50f533129a832f575540a1028f` | 同左 | 一致 |
| `docs/battle16_fixups.md`（t79 重写） | `690d052fe63e7a567149fe8753c505892b7df0dad1b817701e7e5adecb580594` | 同左 | 一致（124 行） |
| `src/test/unit/test_cuv_brackets.py` | `fc9bdf650a2b3420f0543345e2be4bf1d01b9510227107e010e9930d41c8c463` | 同左 | 一致 |
| `docs/vert_taskF_missed_fix.json` | `ffe24f09e69b67b0440d8721c83e963aecef928430767dc0a51f84889e72d8c5` | 同左 | 一致（数据未改） |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致（判据未改） |
| `output/wz7_full/wz7_full_v47.pdf` | md5 `5e8d3031…` | md5 `5e8d3031…` | 已恢复当前交付字节 |

---

## 3. t79 报告核对（repair-round-2）

- **F1 口径**：报告 §1.3 改为「`_fix_yi_after_name` 候选（12 条）内无第二处被吞」；p679 r8 不在候选内，登记 qfix 轮（正确形态 `﹁呀！一壁厢…`）——与我的全书扫描一致（p679 r8 自 v44 起即 `呀！﹁壁厢`）。
- **F2 逐条**：报告 §2.2 列出 v47 剩余 11 处（页/上下文/判读/下一轮），我逐条对照 v47 文本：
  p78/p371/p474/p641/p662×2/p679/p692×2/p1652×2 —— **页与上下文完全一致**；计数口径 v46 18 处（13 页）→ t76 清 7 处 → v47 11 处（8 页），与我的 v46/v47 扫描一致。
- **p692 两处判读**：报告称源 r12 `…花慵戴。」`、r13 `〔東甌令〕`、r14 `花慵戴…`；r15 `…泪盈腮。」`、r16 `〔感皇恩〕`、r17 `「呀！…`。我自裁 `source_pdf` p692 r12 tail/r13/r15 tail/r16/r17（8×）核对：**r13/r16 方括号清晰、r12/r15 结尾均为单 `」`**——报告判读成立；产品 v47 的 `﹁﹂﹁一` / `﹁﹂﹁﹂` 确为噪声，正确形态如报告。
- **结论**：t79 的「报告修复」目标**达成**（p692 两处原文+判读、11 处逐条、F1 口径限定、qfix 登记）；但**产品代码未清 p692 两处**，属下一轮范围（F1 残留）。

---

## 4. 复跑与门禁

- `bash tmp_vert/battle16/build47.sh`：`BUILD_EXIT=0` → `FIXTEXIT=0`（01:20:06）→ 重跑 md5 **`4ef58972e9c8e0351d139c68bac97ac0`**。
- 与当前交付物 `5e8d3031…` 对比：size **109,995,239 = 109,995,239**；metadata 相同；**1748 页文本/行 bbox/内容流逐页 0 差异** → 内容完全等价（/ID）。
- 另与 t76 交付 `71decc87…`（t77 备份 `/tmp/b16v/v47_orig.pdf`）对比：**文本/内容流/bbox 0 差异**；t79 重建仅 /ID 变化（F5）。
- 已恢复 `output/wz7_full/wz7_full_v47.pdf` 为 **`5e8d30318737395fe71c0d7434b988bf`**。
- verify_vert（`--expect-low`）：**exit 0 / PASS**：1748=1748；931,189÷942,935=98.8%；差异>80 字页 **18（预期 18/非预期 0）**；整页丢失 **0**；越界 span **0** + 矢量 **0**。

---

## 5. F1 / F2 独立核对（产品文本）

### 5.1 F1（p679 r5）

- v47 p679 文本含 `﹁一壁厢舞着…` ✓；p679 字符 v46→v47 **+1** ✓；p703 `﹁一到如今`(+1)、p704 `﹁一個兒`(+1) ✓；页码行 p148/p188/p230/p1306 与 v46 逐字相同 ✓。
- `_fix_yi_after_name` 候选 12 条内无第二处吞字 ✓（t79 已限定口径）。
- 全书另有 qfix 历史遗留 p679 r8（`呀！﹁壁厢`，v44–v47 同）；t79 已登记 qfix 轮（F3）。

### 5.2 F2（行内孤引）

| 页 | v47 `﹁﹂` | 判定 |
|---|---|---|
| p833 / p888 / p984 | 0 / 0 / 0 | ✓ 已清 |
| **p692** | **2**（`…花慵戴。﹁﹂﹁一東甌令…` / `…泪盈腮。﹂﹁感皇恩﹂﹂﹁﹂﹁呀！…`） | 产品未清；t79 已给源图判读（正确形态 `…。」︹東甌令︺…` / `…。」︹感皇恩︺﹁呀！…`），代码下一轮（F1 残留） |
| 全书 | **11 处 / 8 页**：p78(1)/p371(1)/p474(1)/p641(1)/p662(2)/p679(1)/p692(2)/p1652(2) | t79 §2.2 逐条列表与我的扫描一致 → 「报告逐条理由」满足 |

- v46 18 处（13 页）→ v47 11 处（8 页）：t76 清 7 处（p831/p833/p888×2/p900/p984/p692-冷清清）。
- 空对残留 0；`「「`/`」」`=0/0；`﹁﹁`=7、`﹂﹂`=239 未增。

---

## 6. 字符量对账

- **v46 931,198 → v47 931,189（−9）**；逐页 9 页：
  `p679 +1 / p692 −2 / p703 +1 / p704 +1 / p831 −2 / p833 −1 / p888 −4 / p900 −1 / p984 −2` —— 与报告 §3 **完全一致**。
- 模型 +3（插入 ﹁）−12（引号串多删 18−6）= −9 ✓；文本 diff 9 页；其余 1739 页 0 差。

---

## 7. wz6 / pytest / 判据 / token

- **wz6**：`VERT_TMP=/tmp/vert_wz6_b16v2` 构建 → `BUILD_EXIT=0`；`vert.tex` md5 **`ae9d2f5259e12cff19e680b2a771b37d`**（默认 `VERT_CUV_FIX=0`）；verify **PASS**（231=231 / 68,412÷70,373=97.2% / 2 预期 / 丢失 0 / 越界 0+0）。
- **pytest**：**610 passed**（884 warnings，76.68s）。
- **判据**：`git diff src/test/verify_vert.py` 空；sha256 = HEAD `cc8b6937…`。
- **token**：报告/构建脚本/测试无 token 字面；**未 commit**（HEAD `e896f2d`）。

---

## 8. 复现命令

```bash
cd /opt/test
bash tmp_vert/battle16/build47.sh
md5sum output/wz7_full/wz7_full_v47.pdf          # 5e8d3031…
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v47.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
# 字符量/﹁﹂ 扫描
/usr/bin/python3 - <<'PY'
import fitz,re
a=fitz.open('output/wz7_full/wz7_full_v46.pdf'); b=fitz.open('output/wz7_full/wz7_full_v47.pdf')
def t(d,p): return re.sub(r'\s','',d[p-1].get_text())
print('delta', sum(len(t(b,i+1))-len(t(a,i+1)) for i in range(len(a))))
pages={i+1:t(b,i+1).count('﹁﹂') for i in range(len(b)) if '﹁﹂' in t(b,i+1)}
print('﹁﹂',sum(pages.values()),pages)
PY
# p692 源图裁片（自裁；只读 source_pdf）
/usr/bin/python3 - <<'PY'
import json,fitz
L=json.load(open('data/wz7_full/wz7_full_spotting_lines_patched.json'))
C=json.load(open('data/wz7_full/wz7_full_spotting_coords.json'))
src=fitz.open('source_pdf/wz7.pdf')
for r in (12,13,15,16):
    b=C['691'][r]; xs=[q[0]/2.0 for q in b]; ys=[q[1]/2.0 for q in b]
    pm=src[691].get_pixmap(matrix=fitz.Matrix(8,8),clip=fitz.Rect(min(xs)-3,min(ys)-3,max(xs)+3,max(ys)+3),colorspace=fitz.csGRAY)
    pm.save('/tmp/p692_r%d.png'%r)
PY
VERT_TMP=/tmp/vert_wz6_b16v2 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b16v2.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b16v2/vert.tex          # ae9d2f52…
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

---

## 9. 纪律

- 只新增 `docs/battle16_acceptance.md`（本轮覆盖重写）；未改 `src/`、数据、fix JSON、`output/`（v47 已恢复当前字节）；未 commit/push。
- 日志：`/tmp/b16v2/`（build47.log、v47_verify.log、wz6_build/verify.log、pytest.log）；自裁裁片：`/tmp/b16v2/p692_src_check2.png`。

---

## 10. 结论

**round 2 PASS**：t79 的报告修复达成（p692 两处原文+源图判读、11 处 `﹁﹂` 逐条、F1 口径限定、qfix 登记）；v47 产品修复（F1、p833/p888/p984、字符量、门禁）保持正确且无回归。

**下一轮仍须（已登记，不阻塞本轮）**：
1. **F1（中）**：p692 两处 `﹁﹂` 代码收敛 + `感皇恩`/`東甌令` 补 `〔〕`；
2. **F2（低）**：其余 9 处 `﹁﹂`（p78/371/474/641/662×2/679/1652×2）按 t79 §2.2 清理/判读；
3. **F3（低）**：p679 r8 qfix 轮修（插 `﹁` 于「呀」前、保留「一」）；
4. **F4（低）**：p704 `﹂：`/p705 `：`、p1703 枚举数字；
5. **F5**：交付 md5 由 `71decc87…` 变为 `5e8d3031…`（/ID，内容 0 差异）——建议交付说明中固定当前 md5。
