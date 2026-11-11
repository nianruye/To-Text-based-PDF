# 形态归一化裁决 + p70 dash 定性（t276）

## 最终判定：**GO（采用 v3；p70/p64/p65/p86/p93 登记已知限制）**

- A（wz4 gold）：归一化前后 **P/R 完全相同 0.7842/0.8187**，by_class 也逐项相同 → 不降，接受 33 页形态 diff。
- B（wz1）：规则收窄后 **wz1 全量 222 页逐页 text diff=[]**，没有可裁决的改动；**0 条改错**。
- p70：4 处 `—` 丢失是 **OCR 上游丢失**（旧 OCR lines 有 `纳—卡`，新 lines 变 `纳一卡`），不是归一化/装配；登记 #54。
- p64/p65/p86/p93：各 1 个单字符 OCR 丢失（不属 ASCII 归一化），登记 #54。
- ghbq v3：104=104、gate PASS、p97 五项达标、GMPG0、typography hard0、产品级 **P0.8468/R0.8758**、worse 页 **5≤5**。
- wz1 222=222 diff0；wz4 677=677 diff33（形态）、P/R 不降；pytest **814 passed**。

## A. wz4 归一化前后

| 产物 | TP | FP | FN | P | R |
|---|---:|---:|---:|---:|---:|
| 归一化前 `wz4_s4.pdf` | 447 | 123 | 99 | 0.7842 | 0.8187 |
| 归一化后 `wz4_norm_regress.pdf` | 447 | 123 | 99 | 0.7842 | 0.8187 |

by_class 逐项相同（comma 244/7/12、period 101/34/31、quote_open16/14/20、quote_close9/25/13、colon20/0/0、bracket7/0/7 等）。
结论：**形态归一化不改变 wz4 的类/位置匹配**，33 页 diff 只是 ASCII→全角的 form 变化；按验收 A 判为可接受。

## B. wz1 全部改动裁决

上一版规则（跳过空格）在 wz1 p4/10/123/127/173/185 产生 15 处改动；逐条看源图后：
- p4 是 CIP/版权页，`著.`、`出版人: 葛海彦`、`杨金海, 李惠斌` 等**源图就是 ASCII 标点/半角字段**；把 `著.`→`著。`、`出版人:`→`出版人：` 属改错。
- p123/p127/p185 是拉丁短语 `studiorum”`/`question”`/`power”` 后的逗号，左邻是闭引号而非 CJK，改为全角属改错。
- 故**收窄规则**：严格相邻（空格视为非 CJK）；引号只有当引号内侧本身是 CJK 时才可作邻字（`开始,“在` 可改，`studiorum”,` 不改）；破折号/省略号/引号后的逗号不因跨行上下文被转换。

收窄后重跑 wz1：`normalize.json total=0`，**222=222、逐页 text diff=[]**。源图裁片：`output/wz1/normalize_adjudicate/p0004/10/123/127/173/185_source.png`（无改动可逐条裁决；原 15 条全部被规则排除）。

## C. p70 em dash 定性

- 旧 OCR lines p70：`纳戈尔诺—卡拉巴赫`、`纳—卡`（4 个 `—`）。
- 新 OCR lines p70：`纳戈尔诺—卡拉巴赫` 保留 1 个，`纳一卡`（4 处变汉字「一」）。
- 源图 p70：`output/ghbq/rebuild_cur/p70_adjudicate/p0070_source.png`，可见地名中的 `—`。
- 结论：**OCR 上游把 `—` 识别成 `一`**，不是渲染/归一化。**无可确定性的通用规则**（`一`→`—` 会误伤正常「一」）；登记已知限制，不修。若未来做地名/实体级校正，可仅在该词表内修。

## D. 最终产物与验收

`output/ghbq_full/ghbq_final_v3.pdf`
- sha256 `eba54007fae8f4739c9778b1c369d943b1dfc3bb703773d9074a67fa90ec570a`
- gold_sha256 `8423a6a8fa2f0a156c8aad1aa45a37d486c30c16c1943b1e6dde02d7352a2df4`
- 104页；gate PASS；pitch97.9；overflow0；split0；missing0；GMPG0；typography hard0/render0
- p97：image1 / 493字 / 全1.0pt / vis0 / 含85
- punct：TP282/FP51/FN40 **P0.8468/R0.8758**
- 逐页计数：diff60；better **1243** / worse **8**；worse 页 **5**：p64/65/70/86/93（p70 4 处 dash，其余单字符）
- sidecar `ghbq_final_v3.pdf.normalize.json`：**99 处**，页 `[5,31,32,33,34,35,36,37,38,39,40,68,78]`，字段 page/line/pos/old/new/before/after 完整。
- 注意：sidecar 是**产物旁审计文件**，未写入 scan2pdf report（scan2pdf 不在本任务 in-scope）；人工复核可直接读该 JSON。

## E. 回归

- wz1：222=222，逐页 diff **[]**；gate PASS（pitch 不降）。
- wz4：677=677，33页 diff 全为 ASCII→全角形态；P/R 不变；gate PASS。
- pytest：`src/test/unit + src/test/invariants` **814 passed**。
- 单测 `test_punct_normalize.py` **7 passed**。

## F. Go 结论与替换清单

**GO**：接受 v3 为 ghbq 交付基线；p70/p64/p65/p86/p93 作为 known limitations，不阻塞（worse 页 5，满足最终验收 ≤5）。

替换/更新清单（供 captain）：
1. `output/ghbq_full/ghbq_final_v3.pdf` → 作为 ghbq 交付产物（替换 `ghbq_p97v2.pdf`）；
2. `docs/ghbq_baseline_v2.md`：更新为 v3 的 P/R、p97、worse 页、sha；
3. `docs/punct_gold_h_v1.md`：ghbq 基线改 0.8468/0.8758、sha；
4. `docs/ghbq_rebuild_gate.md`：补 t276 裁决；
5. `AGENTS.md #54`：p70 + p64/65/86/93 已知限制；
6. 代码/测试：`src/utils/tex_escape.py`、`src/pipelines/build_geom.py`、`src/test/unit/test_punct_normalize.py`；
7. 配置：`data/ghbq/page_image_pages.json`（已落盘，pages=[97]）。
不提交 output/、不 commit。
