# battle13 · p57 破折号线宽切源墨实测 → v43

> 任务：t64 — 用 `VERT_DASH_RULE_W=src` 重建 v43（不改代码默认值）
> 执行：竖排工程师　日期：2026-11-07
> 产物：`output/wz7_full/wz7_full_v43.pdf`；构建脚本 `tmp_vert/battle13/build43.sh`
> 约束：未改 `build_vert.py` 默认（仍 0.040×F）、未改 verify 判据/数据；未 commit；token 未入库。

## 0. 结论（先行）

| 项 | 结果 |
|---|---|
| v43 构建 | ✅ `VERT_DASH_RULE_W=src`（脚本显式；代码默认不变）；md5 **4ad7c2028bd7ee46cdd1798ef447c3db**，1748 页 |
| p57 线宽 | ⚠ **2.784pt → 5.0pt**（`get_drawings` 的 `width`）。**与任务给的 5.25pt 差 0.25pt（>0.2 容差 0.05）**；5.0 = 代码 `_dash_ink_seg` 的源墨实测宽度（`w_src=5.0`）；t42 的 5.25 是阈值 110 的外部测量（阈值相关：4.56–5.28）。**按验收口径此条未满足**，需队长裁决：接受 5.0，或另开代码任务调 ink 宽度阈值（`_dash_ink_seg`，`build_vert.py` 本轮 out-of-scope） |
| 线位/线长/线心 | ✅ 不变：y **736.497–816.497**（长 **80.0**）、x **829.997**（Δ0.01）、线心与 v42 同 |
| 影响面 | **8 页变化**：p31、p37、p39、p57、p62、p1157、p1683、p1742（均为 dash 组线宽变；**不是只有 p57**——全书 63 组 dash-rule 分布在 15 页，任务前提「只有 p57 一组」不成立，见 §3） |
| 门禁 | verify_vert **PASS**（1748=1748 / **931,200** 与 v42 同 / 18 预期 / 整页丢失 0 / 越界 0+0）；wz6 `vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节 + verify PASS（wz6 默认不启用 src）；pytest **599 passed** |

## 1. 构建

`tmp_vert/battle13/build43.sh`（由 build42.sh 复制，仅加 `export VERT_DASH_RULE_W=src` 与 v43 路径）：

```bash
export SOURCE_DATE_EPOCH=0
export VERT_DASH_RULE_W=src      # 本轮唯一行为开关；build_vert.py 默认仍 '0.040'
export FORCE_SOURCE_DATE=1
TMP=/tmp/wz7_v43_run; OUT=output/wz7_full/wz7_full_v43.pdf
```

- 构建日志：`mode nf / w_raw src`；p57 `w_src=5.0`（`/tmp/wz7_v43_run/dash_segments.json`）；`BUILD_EXIT=0/FIXTEXIT=0`。
- v43 md5 **4ad7c2028bd7ee46cdd1798ef447c3db**。

## 2. p57 线宽/位置实测

| 项 | v42 | v43 | 源墨（t42/代码） |
|---|---|---|---|
| 线宽（`get_drawings().width`） | **2.784pt** | **5.0pt** | t42 5.25（阈值 110）；代码 `w_src` **5.0** |
| 线位 y0/y1 | 736.497–816.497 | **736.497–816.497**（Δ0） | 736.5–816.0/816.75（阈值相关） |
| 线长 | 80.0 | **80.0** | 79.5–80.25（阈值相关） |
| 线心 x | 830.005 | **829.997**（Δ0.008） | 829.88（Δ0.12） |
| 线型 | 's'（stroke） | 's'（stroke） | — |

- 源墨宽度多阈值实测（本机 600dpi，p57 x820–845/y725–825）：**阈值 90 → 5.28、110/130 → 4.56、150 → 3.72**；t38 报告为 90→4.5 / 110→5.25 / 170→6.0。源墨「宽度」本身随阈值 ±0.7pt；代码 `_dash_ink_seg` 取 **5.0**（同源口径）。
- 结论：v43 的 5.0 = **管线自己的源墨实测**；与 t42 的 5.25 差 0.25pt（**未达 ≤0.2 验收线 0.05pt**）。不改代码无法从 `src` 模式得到 5.25。

## 3. 影响面（v42 → v43 绘图 diff，文本 0 页差异）

| 页 | dash 组数 | v42 线宽 | v43 线宽 | 说明 |
|---|---|---|---|---|
| p31 | 2 | 1.04 | **2.0** | 源墨实测宽 > 默认 0.040×F |
| p37 | 1 | 1.04 | **2.0** | 同上 |
| p39 | 1 | 1.04 | **2.5** | 同上 |
| p57 | 1 | **2.784** | **5.0** | 本轮目标 |
| p62 | 1 | 1.04 | **2.0** | 同上 |
| p1157 | 1 | 1.04 | **2.5** | 同上 |
| p1683 | 1 | 0.808 | **2.5** | 同上（p1683 是圈码页的 dash 组） |
| p1742 | 48 | 1.43（全部） | 22 组变宽（1.5–13.0）、11 组由 stroke 变 filled | 異體字表页 48 个 `—` 组；`src` 宽度差异大，含 13.0/12.5/12.0 等可疑宽（疑似量到邻笔/并字），需人工复核 |

- 其余 dash 页（p38/p60/p119/p262/p462/p600/p686）**无变化**——这些组的源墨宽度恰好与默认一致（日志 `w_ratio≈0.040`）或为 fallback（保持默认/兜底）。
- **重要更正**：任务前提「全书只有 p57 这一组 `——`」与数据不符——全书 **63 组** dash-rule 分布在 **15 页**（p31/37/38/39/57/60/62/119/262/462/600/686/1157/1683/1742），`VERT_DASH_RULE_W` 是**全局**开关，因此 `src` 会改变所有组的线宽，共 **8 页**受影响。
- 风险：p1742 的 13.0/12.5pt 宽线视觉上可能过粗（源墨测量把相邻笔画并入）；若只想要 p57 的 5.0，需要**按页/按组**的开关（代码改动，out-of-scope），或接受全局面宽。

## 4. 门禁

| 门禁 | 结果 |
|---|---|
| verify_vert（--expect-low） | **PASS**：1748=1748 / **931,200**（= v42，文本 0 页差异）/ 差异>80 字页 18（预期 18）/ 整页丢失 0 / 越界 span 0+矢量 0 |
| wz6 零回归 | `/tmp/vert_wz6_b13/vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节相同 + verify PASS（231=231/97.2%/2 预期/0/0+0）；wz6 默认不启用 src |
| pytest | **599 passed** |
| 文本 | v42↔v43 文本逐页 **0 差异**（字符量 931,200 同） |

## 5. 复现命令

```bash
bash tmp_vert/battle13/build43.sh
md5sum output/wz7_full/wz7_full_v43.pdf   # 4ad7c2028bd7ee46cdd1798ef447c3db
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v43.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
# p57 线宽
/usr/bin/python3 - <<'PY'
import fitz
p=fitz.open('output/wz7_full/wz7_full_v43.pdf')[56]
for dr in p.get_drawings():
    r=dr['rect']
    if 820<r.x0<840 and 700<r.y0<830:
        print(dr['type'], round(dr['width'],3), round(r.x0,3), round(r.y0,3), round(r.y1,3))
PY
VERT_TMP=/tmp/vert_wz6_b13 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b13.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b13/vert.tex   # ae9d2f5259e12cff19e680b2a771b37d
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

## 6. 约束与待裁决

- 未改 `src/pipelines/build_vert.py`（默认仍 0.040×F）、未改 `verify_vert.py` / 数据 / fix JSON；未 commit/push；token 未入库。
- **待裁决（1 条）**：p57 线宽 5.0 vs 任务给的 5.25（Δ0.25 > 0.2）。选项：
  1. **接受 5.0**（= 管线 `_dash_ink_seg` 的源墨实测，且落在源墨多阈值实测 4.56–5.28 内；v43 其余指标全过）；
  2. 另开**代码任务**改 `_dash_ink_seg` 的线宽阈值/口径，使 src 得 5.25（本任务 out-of-scope）。
- **附带发现**：`src` 为全局开关，影响 8 页（p1742 的 22 组宽线含 13.0/12.5pt 可疑值）；若只想要 p57，需代码加 per-page/per-group 开关（建议下一轮评估）。
