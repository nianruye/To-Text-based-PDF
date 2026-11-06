# battle9c · p57 真破折号 + p186/p147 落库 → v39

> 任务：t40 — battle9c　执行：竖排工程师　日期：2026-11-06
> 输入：t38 报告 `docs/battle9_dash_p57.md`（源墨测量） + t27 punct_list
> 产物：v39 `output/wz7_full/wz7_full_v39.pdf`；本报告；证据 `tmp_vert/battle9/fix/`
> 本任务**数据-only**：只改 `docs/vert_taskF_missed_fix.json`（+3 条 missing_char），未改 `build_vert.py` / verify 判据；未 commit；token 未入库。

## 0. 结论

| 项 | 证据（t38 源墨） | 处置 | 验证 |
|---|---|---|---|
| **p57 `—`** | 竖线 y 736.5–816.0（79.5pt，阈值 150 时 80.25pt）、线宽 5.25pt、x 中心 829.88；四道 dash-rule 比值全过 | 落 `missing_char` page=57 pos=7 **ch='——'**（两个 `—` 成组，dash rule 画**一条**线） | 单页 test build + v39：**恰好 1 条竖线** x=830.01、y 736.5–816.5、长 80.0；y0 差 **0.00**、x 中心差 **0.13**；y1 差 0.5（阈值 110 边）/ **0.25（阈值 150 边 816.75）**；字符量 +2 |
| **p186 `」。`** | 本格 ﹂ 20.2×9.0pt + 下一格 。7.5×8.2pt；源序 `鬼」。蘇` | 落 `missing_char` page=186 pos=2 **ch='」。'** | test build：文本层 `餓鬼﹂。蘇東坡`（+2 字符）；v39 同 |
| **p147 `」，`** | 本格 ﹂ 18.7×7.7pt（y538.3–546.0）+ 逗号 4.5×6.8pt（y553.5–560.3）；源序 `！﹂，那` | 落 `missing_char` page=147 pos=13 **ch='」，'** | test build：文本层 `吃！﹂，那婦人`（+2 字符）；v39 同 |
| **p1330 `，`** | 仅 3.0×3.0pt 纸面噪点（面积 563/499，已知逗号 ≈2033） | **不落库**（API 误判），登记于此 | — |

**一句话**：p57 在 v39 中是**一条** 80.0pt 的竖线（x 830.01，y 736.5–816.5），与 t38 源墨的线长/线心/线宽口径一致；p186/p147 各 +2 字符且上下文与源序一致；p1330 不落。

## 1. p57 破折号

### 1.1 落库
- 数据：`docs/vert_taskF_missed_fix.json` 新增 `{"class":"missing_char","page":57,"pos":7,"ch":"——","source":"api_strip_punct",...}`。
- 机制：t24 的 missing_char 插入 → 文本层出现两个相邻 `—` → t34 的 `_dash_runs`（R2：相邻两个 `—` = 源图同一墨块）成组 → `_dash_ink_seg` 实测源墨，`_dash_rule_tex` 画**一条** rule；文本层 `—` 以 `3 Tr` 不可见保留（可搜、字符量 +2）。
- 该页是标题行（§1.995 路径）：build 日志确认 `[标题署名] p57 「論金瓶梅這部書——導讀」… 步进66.5`，即走标题路径且文本含 `——`。

### 1.2 单页 test build（VERT_PAGES=57）
- 产物 1 页；`[破折号] 源图实测 1 组 / 兜底 0 组`；`dash_segments.json`：`{page:57, x:830.0, n:2, text:'——', y0:736.5, y1:816.5, len:80.0, ratio:1.255, w_src:5.0, step:63.72}`。
- PDF 竖线：**1 条**（x 830.01，y 736.5–816.5）；字符 466 → **468（+2）**。

### 1.3 v39 复核
- 与 test build 相同：1 条竖线（x 830.01，y 736.5–816.5，长 80.0）。
- 与 t38 源墨对照：y0 差 **0.00**（736.5=736.5）；x 中心差 **0.13**（830.01 vs 829.88，≤0.3）；线长 80.0 vs 79.5（阈值 110）/80.25（阈值 150），差 0.5/0.25；**y1 差 0.5（vs 816.0）或 0.25（vs 816.75）** —— t38 §1.2 已注明源墨边随阈值取边 ≤0.75pt，本轮按同一源墨段（阈值 150）计 **≤0.25pt**。
- 四道比值（t34）：线长/step = 80.0/63.72 = **1.255**（参考 1.26）；线宽/step = 5.0/63.72 = 0.078；线心偏 0.01/63.72；线位 ≈1.0 → 与 t38 的四道判据一致。

## 2. p186 `」。`

- 源序（t38）：`鬼」。蘇` —— 本格 ﹂（20.2×9.0pt）+ 下一格 。（7.5×8.2pt）。
- 落库：`ch='」。'` pos=2；test build 文本 `餓鬼﹂。蘇東坡又云`（`﹂` 是 `」` 的竖排形）；v39 同。
- 无重复：全书检索 `」。` 在该页上下文仅 1 处；字符 725 → 727（+2）。

## 3. p147 `」，`

- 源序（t38）：`！﹂，那` —— 本格 ﹂（18.7×7.7pt）+ 逗号（4.5×6.8pt）；t27 条目只含 `，`（漏 ﹂）。
- 复核结论：**确认**（两块墨与 `！` 末点有间隙、与同页逗号同形）。落库 `ch='」，'` pos=13。
- test build 文本 `…吃！﹂，那婦人揭起…`；v39 同；字符 675 → 677（+2）。

## 4. p1330 `，`（不落）

- t38：cell 内仅 3.0×3.0pt 噪点（面积 563/499），已知逗号 ≈4.5×6.8pt/2033 → **API 误判**；本轮**不落库**，登记。

## 5. 门禁与 diff

| 项 | 结果 |
|---|---|
| v38→v39 逐页字符量 diff | **3 页 +6**：p57 +2、p147 +2、p186 +2（无其他页变化） |
| v39 | `output/wz7_full/wz7_full_v39.pdf` md5 **c77037aa288c5f6bf2a19c7ab7fda45d**，1748 页 |
| verify_vert（--expect-low） | **PASS**：1748=1748 / **931,184**（v38 931,178 +6）/ 差异>80 字页 18（预期 18/非预期 0）/ 整页丢失 0 / 越界 span 0+矢量 0 |
| wz6 零回归 | `/tmp/vert_wz6_b9/vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节相同 + verify PASS |
| pytest | **590 passed** |
| 判据 | 未改 `verify_vert.py`；未改 `build_vert.py`（数据-only） |

## 6. 复现命令

```bash
# 单页 test（p57）
VERT_PAGES=57 VERT_TMP=/tmp/wz7_test57 /usr/bin/python3 src/pipelines/build_vert.py \\
  data/wz7_full/wz7_full_spotting_lines_patched.json data/wz7_full/wz7_full_spotting_coords.json \\
  tmp_vert/battle9/fix/test57.pdf source_pdf/wz7.pdf
# 单页 test（p147/p186）
VERT_PAGES=147,186 VERT_TMP=/tmp/wz7_test147 /usr/bin/python3 src/pipelines/build_vert.py \\
  data/wz7_full/wz7_full_spotting_lines_patched.json data/wz7_full/wz7_full_spotting_coords.json \\
  tmp_vert/battle9/fix/test147_186.pdf source_pdf/wz7.pdf
# 全书 v39
bash tmp_vert/battle9/fix/build39.sh
# 门禁
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v39.pdf \\
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \\
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \\n' < data/wz7_full/wz7_full_expect_low.txt)"
VERT_TMP=/tmp/vert_wz6_b9 /usr/bin/python3 src/pipelines/build_vert.py \\
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b9.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b9/vert.tex   # ae9d2f5259e12cff19e680b2a771b37d
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

## 7. 约束声明

- 数据-only：未改 `build_vert.py` / `verify_vert.py` 判据；未 commit/push；token 未出现在任何文件/报告。
- p57 的 y1 严格对 816.0 为 0.5pt，对阈值 150 的源墨边 816.75 为 0.25pt —— 属 t38 §1.2 已注明的「阈值取边 ≤0.75pt」不确定度；线长/线心/线宽与 t34 四道判据一致。
