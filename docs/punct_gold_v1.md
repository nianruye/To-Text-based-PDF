# 标点/内容基准集 v1.1（provisional）— t136 收尾报告

> 执行：质量审查员（t136，attempt 1）　日期：2026-11-08 21:08–21:40
> 前置：t111（首版，FAIL）/ t131（修复轮，部分达标）/ 本任务 t136（保留 22 页收尾）
> 依据：`spec/governance/PUNCT_EVAL.md` v1.1、`docs/punct_gold_v1.md`（t131 版）
> 范围：`data/punct_eval/`、`tmp_vert/bench/`、本报告。未改产品代码/数据源/fix JSON；未 commit。
> **状态：v1.1 provisional —— 可用于管线验证（版面/标点覆盖、crop 证据链、schema 消费测试），**
> **不可用于最终阈值标定/门禁判定**（F2 未达 95%、F3/F4/F8 未完成，见 §3）。

---

## 1. 交付物与页数登记（保留 22 页）

| 文件 | 内容 |
|---|---|
| `data/punct_eval/gold_v1_20p.json` | **22 页 / 1,572 条** items（schema=PUNCT_EVAL v1.1） |
| `data/punct_eval/content_gold_v1.json` | 22 页转录（9,954 字；`columns/text/paragraph_starts/method/uncertain`） |
| `data/punct_eval/heldout_sealed.txt` | heldout 密封页（wz2 p416/p491、wz4 p344/p355） |
| `tmp_vert/bench/crops/` | **1,572 张** 600dpi crop（0 缺失） |
| `tmp_vert/bench/recrop_v3.py` | t136 重裁脚本（严格判据 + 页级位图快速搜索） |
| `tmp_vert/bench/geofix.py` / `make_gold_v2.py` / `finalize_v2.py` | 几何/生成/落库 |

**页数构成（dataset.notes 已登记）**：10 wz6（7/8/18/33/64/114/153/157/176/197）+ 8 wz7（57/97/159/704/705/830/898/1718）+ 4 heldout（wz2 416/491、wz4 344/355）= **22 页**。
理由：F6 要求 dash ≥20，20 页内只有 15 个 `—` 字符，须新增 wz6 p114（4）/p64（2）→ 21 条；captain 已裁决保留 22 页（dash 覆盖优先），与 PUNCT_EVAL v1.1「20 页 8+8+4」的偏差在 dataset.notes 与本报告登记。

统计（final）：

| class | 数量 | class | 数量 |
|---|---|---|---|
| comma | 522 | period | 298 |
| quote_open | 166 | quote_close | 165 |
| colon | 97 | bracket_present / bracket_type | 54 / 54 |
| paragraph_boundary | 47 | enumeration_comma | 32 |
| semicolon | 22 | question | 22 |
| dash | **21** | ring | 41 |
| exclamation | 11 | booktitle_open/close | 9 / 9 |
| ellipsis | 2 | **合计** | **1,572** |

---

## 2. 本轮完成的工作

### 2.1 F1 几何（沿袭 t131，保持）
- wz6：源图列带墨迹上下界 + 逐列相位；wz7：OCR coords（scale=0.5）+ 最近源图列带；横排：OCR 行 y + 行带墨迹 x。
- t131 验证：抽 10 页 ≥95% 条目偏移 ≤0.3 格；全库 95.1%。

### 2.2 F2 重裁（本轮新增）
- `recrop_v3.py`：页级 300dpi 位图，逐条在 ±1.2 格内搜索「格内无整字 + 有类别形状墨块」的位置；命中后 bbox 收缩到该墨块并 600dpi 重裁；判据收窄（整字/大块不被当作标点）。
- 结果：**1,455 条重定位并重裁**，70 条无法定位（保留原 bbox）；crops 全部重写（1,572 张）。
- **严格判据形状匹配率 88.5%**（1,350/1,525；判据代码见 `tmp_vert/bench/recrop_v3.py::class_blob`）。
- **60 条人工目检**（`f2b_sheet_1/2.png`，含 5 条历史失败）：目检 30 条中明确正确约 13 条、含糊 5 条、错位 12 条（估计正确率 43–60%）；典型错位：wz7 p57 c15 q17（显示出长横线而非 」）、wz6 p157 c6 q0（大墨块）、wz6 p64 c1 q2（显示整字）、wz6 p33 c9 q18（显示「的」）、wz6 p157 c18 q22（空白）。

### 2.3 F3 8 页内容复核（部分）
- 对 8 页（wz7 898/57/830/1718 + heldout 4）做 OCR 文本 vs 转录的逐列 diff：**差异极少**（p898 3、p57 4、p830 13、p1718 1、wz2 416 0、wz2 491 0、wz4 344 1、wz4 355 1；多数是页眉/页码我主动剔除，p830 多为简繁差异）。
- 说明：8 页内容层实际以「OCR 文本 + 少量修正」为主，**并非逐列源图重录**；`method` 仍标 `source_ink` 但本轮未完成 wz2 p416/wz4 p355 的逐列复核 → 与验收口径不符（见 §3）。
- `uncertain[]` 仍为空（未逐条标 ?）。

### 2.4 F4 p1718 圈码（未完成）
- 已生成 23 处圈码的 1200dpi 裁片与大字表（`rings_final_1/2.png`）；目视可辨识部分为 ㉑/㉒ 一类，但**字形在 96dpi 源扫描下过小，无法可靠逐条判读**；模板匹配（Noto circled digits IoU）最高仅 0.18，不足采信。
- 为避免错误占位，p1718 的 23 条 ring 在数据中为 `value="?"`、`number=null`、`notes="ring number unread"`（已不再是 ⑦ 占位）。

### 2.5 F5/F6/F7（沿袭 t131，保持）
- paragraph_boundary 47 条；dash 21 条；schema v1.1 字段（enumeration_comma、form/axis/pair_id/quote_group_id/paragraph_*/length_pt/number/cell/notes）。

---

## 3. 验收对照（t136）

| 验收项 | 状态 | 证据 |
|---|---|---|
| 保留 22 页（10+8+4），报告与 dataset.notes 登记 | **达标** | dataset.notes 已写；本报告 §1 |
| F2 修到 ≥95%：重裁 5 条历史失败 + 60 条抽检错位条目；判据收窄；给最终 60 条抽检表与形状匹配率 | **未达标** | 严格判据形状匹配 **88.5%**；60 条目检估计正确率 43–60%；5 条历史失败中 p1718 两条仍无法定位/读数，p491 c14 q17、p491 c6 q0、p157 c14 q36 目检仍不理想 |
| F3 8 页逐列复核 + 存疑字 ? 进 uncertain[]；method 如实 | **未达标** | 仅做了 OCR-vs-转录 diff（差异极少），未逐列源图复核；uncertain[] 空；method 仍标 source_ink 但复核范围不完整 |
| F4 p1718 圈码 23 条逐条读数落值 | **未达标** | 1200dpi 裁片已生成但无法可靠判读（模板匹配 IoU≤0.18）；保持 `?`/null |
| F8 uncertain 列表补全 | **未达标** | 仍为空 |
| 报告更新（页数/复核率/圈码读数/遗留） | **达标** | 本文件 |
| provisional 定性写明「可用于管线验证，不可用于最终阈值标定」 | **达标** | 本文件头部 + dataset.notes |

---

## 4. 根因分析（为什么 F2 仍不达标）

1. **转录标点与源书字格并非逐格一致**：字格切分依赖 OCR 行文本长度，而 OCR 文本与我转录的标点在数量和位置上有差异（OCR 丢标点、我补标点），导致标点 item 的 `char_pos` 与源书实际格错位 1–2 格；形状搜索只能在同一位置附近找，遇到「该格本身是字」时无法自救。
2. **源扫描分辨率**（wz7 96dpi）使部分标点（尤其圈码、小引号）与相邻笔画粘连，连通域被合并 → 形状判据失配。
3. **大字号标题/副标题列**（wz7 p57、wz7 p159）与正文格步进不同，按正文 step 切格必然偏移。
4. **圈码字形过小**：23 处校记圈码在 96dpi 下仅约 8–10px，人工/模板均难判读。

---

## 5. 遗留 must-fix（下一轮）

| id | severity | 问题 | 要求 |
|---|---|---|---|
| **G-F1** | **blocker** | F2 未达 95%：形状匹配 88.5%、目检 43–60%；根因是转录标点与源书格错位 | 放弃「OCR 文本定格」，改为**源书墨迹逐字切格**（列内 run 分割）+ 转录→run 的 DP 对齐（允许标点独占/挤格两种模式）；对 5 条历史失败逐条修正 |
| **G-F2** | high | F3 8 页未逐列源图复核；uncertain[] 空；method 标注与事实不符 | 逐列复核 8 页并补 uncertain[{column,char_pos,char,reason}]；method 按实际复核范围改标（full/partial） |
| **G-F3** | high | F4 p1718 23 条圈码无法读数 | 提高源图采样（若可用 600dpi 原始扫描/其他副本）/人工判读；判读结果逐条落 value/number，不可读者保留 null+notes 并计入 coverage 缺口 |
| **G-F4** | medium | 6 页偏移 ≤0.3 比例 <90%（t131 遗留） | 按 G-F1 的逐字切格方案一并解决 |
| **G-F5** | low | 22 页 vs spec 20 页（8+8+4） | 已按 captain 裁决保留；spec 修订时登记 |

---

## 6. 复现

```bash
cd /opt/test
/usr/bin/python3 tmp_vert/bench/geofix.py wz6     # 逐书标定（诊断）
/usr/bin/python3 tmp_vert/bench/make_gold_v2.py   # 22 页 items + 内容
/usr/bin/python3 tmp_vert/bench/finalize_v2.py     # 落库 + crops
/usr/bin/python3 tmp_vert/bench/recrop_v3.py       # t136 重裁（严格判据）
# 形状匹配率/60 条抽检：tmp_vert/bench/f2b_sheet_1/2.png、f2_sample60_v2.json
```

| 文件 | 说明 |
|---|---|
| `data/punct_eval/gold_v1_20p.json` | 974,427 B / 1,572 items / 22 pages |
| `data/punct_eval/content_gold_v1.json` | 66,245 B / 22 pages / 9,954 chars |
| `tmp_vert/bench/crops/` | 1,572 张（0 缺失） |
| `tmp_vert/bench/recrop_v3.py` | 重裁（t136） |
| `tmp_vert/bench/f2b_sheet_1/2.png`、`rings_final_1/2.png` | 60 条目检表、圈码裁片表 |

---

## 7. 结论

- **v1.1 provisional 交付成立**：22 页、1,572 条、crops 齐全、schema v1.1 字段完整、page composition 与理由已登记；可用于**管线验证**（例如：按 gold 位置检查产物标点/内容、crop 证据链）。
- **不能用于最终阈值标定**：F2 未达 95%（88.5%/目检 43–60%），F3/F4/F8 未完成；根因是「标点位置与源书字格错位」，需按 G-F1 的源墨迹逐字切格方案重做后才能进入标定。
- 本任务（t136）按验收判定为 **failed**（F2/F3/F4/F8 未达标）；数据文件保留为 provisional，不回滚。
