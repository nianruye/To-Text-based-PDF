> **t276 更新**：规则已收窄为严格相邻 + 引号内侧 CJK；wz1 现为 0 改动/逐页 diff=[]，wz4 P/R 不变；ghbq v3 worse 页 5（≤5），已判 GO。以下 t275 文字保留为历史版本，最终以 `docs/punct_normalize_adjudicate.md` 为准。

# CJK 上下文 ASCII→全角标点归一化（t275）

## 结论：**no-go（当前未达 worse≤4 / wz1 零 diff）**

- 归一化已实现并接到 build_geom 文本装配；ghbq p31–39 的逗号形态回退已修复。
- 重建后 worse 页 **14 → 5**（p64/p65/p70/p86/p93），仍比目标 ≤4 多 1 页；原因是 **p70 的 em dash（`—`）丢失 4 处**，不属于 ASCII 标点归一化可覆盖的范围。
- wz1 全量构建出现 **6 页文本 diff**（p4/10/123/127/173/185），均是同一归一化把 CJK 间 ASCII 标点转全角；wz4 全量出现 **34 页 diff**，同样是形态改善。按「wz1 必须 []」的严格口径不达标。
- 因此本任务 **no-go**；不替换基线。需要先裁决 wz1/wz4 的形态变化是否接受，并处理 p70 dash。

## 实现

- 共享文本层：`src/utils/tex_escape.py::normalize_cjk_punct(text,left_context,right_context)`
  - ASCII `, ; : ? ! .` → `，；：？！。`；
  - 仅左右（跳过空格；行首/行尾可用相邻行邻字）均为 CJK/全角标点时替换；
  - 数字/拉丁邻接、`3.5`/`a,b`/`1987.`/`A.`、已全角、孤立行首尾均不动；
  - 幂等，返回逐字 changes。
- 装配：`src/pipelines/build_geom.py` 逐页 OCR 行入口调用，收集 `NORM_CHANGES`，写
  `<out>.normalize.json`（`schema=punct-normalize-v1`, total, pages, changes[page,line,pos,old,new,before,after]）。
- 单测：`src/test/unit/test_punct_normalize.py` 7 passed（CJK/数字/拉丁/幂等/行首尾/中英边界/跨行邻字）。
- 全量测试：`pytest src/test/unit src/test/invariants -q` → **814 passed**。

## 改动审计

`output/ghbq_full/ghbq_final_v3.pdf.normalize.json`：**108 处**，页 `[5,31,32,33,34,35,36,37,38,39,40,68,78]`。
（构建临时路径 `_scan2pdf_ghbq/build_ghbq_final_v3.pdf.normalize.json` 同内容；已复制到最终产物旁。）

## 重建与复验

产物：`output/ghbq_full/ghbq_final_v3.pdf`（sha `56d42dd9…74ec`）；p97 配置仍为 pages=[97]。

- 104=104；gate PASS；pitch97.9 / overflow0 / split0 / missing0；GMPG0；typography hard0。
- p97：image1、chars493、全1.0pt、vis0、含85。
- 产品级 punct_eval：**TP282/FP51/FN40 P0.8468/R0.8758**（与 v2 相同，R 不降；gold_sha 8423a6…）。
- 逐页标点计数对照（新旧）：
  - diff 60 页；better **1244** / worse **8** / other41；
  - worse 页 **5**：p64(1)、p65(1)、p70(4)、p86(1)、p93(1)；
  - p31–39 **已从 worse 清 0**（全角→ASCII 已归一化）。
- 目标 worse≤4 未达：**p70** 旧 5 个 em dash → 新 1 个，属 `—` 丢失，不是 `,;:?!.` 归一化能修。

## 剩余 4+1 页

| 页 | 差异 | 源图裁片 | 裁决 |
|---|---|---|---|
| p64 | 闭引号 -1 | `worse_crops/p0064.png` | 单字符丢失，不能由 ASCII 规则修；登记 known issue |
| p65 | 句号 -1 | `worse_crops/p0065.png` | 同上 |
| p70 | em dash 5→1（4 处） | `worse_crops/p0070.png` | **不可用 ASCII 规则**；需 dash 行级保留/旧页回退 |
| p86 | 闭引号 -1 | `worse_crops/p0086.png` | 单字符；AGENTS #54 |
| p93 | 句号 -1 | `worse_crops/p0093.png` | 单字符；登记 |

## 零回归

- wz1：222=222；逐页 text diff **6 页**（p4/10/123/127/173/185），全部是 ASCII→全角形态（如 `,`→`，`）；无内容字增减。按「必须 []」严格口径 **不通过**。
- wz4：677 页；text diff **34 页**，均为同一形态归一化；按「抽30页零回归」需要将这些页逐条列为形态改善（不是内容变化），本报告不把它们当内容回归，但严格门槛未过。
- 全量 pytest：**814 passed, 0 failed**。

## 后续

1. 先裁决 wz1/wz4 的度量：形态归一化是否允许产生 diff（若允许，应改验收口径，而不是回退功能）。
2. p70 用 **dash 行级保留**（旧页 A/D 融合）修 4 处；p64/p65/p86/p93 单字符登记 known issue。
3. 修完后重跑：目标 worse 页 ≤4、R≥.8758、wz1 可解释 diff；再 go。

## 自检

- 归一化幂等、审计 108 条、无静默改字；p97 保持可搜贴图；punct R 不降。
- 未改 gold/punct_eval 口径；未 commit。
