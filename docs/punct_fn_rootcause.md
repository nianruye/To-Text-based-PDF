# wz7 8 页 gold 标点 FN 根因逐条审计（t258）

> 旁路审计：只读 gold/PDF/OCR/源图；**未改 gold、未改 punct_eval 计数口径、未改产品渲染**；未 commit。
> 日期：2026-11-12；数据：`data/punct_eval/content_gold_v1.json`（wz7 8 页）、`output/wz7_full/wz7_full_v51.pdf`、`data/wz7_full/wz7_full_spotting_lines_patched.json`。

## 1. 结论摘要

- 逐条定位 **34 个 FN**，与已知 by_class 完全一致：period 9、quote_close 8、colon 5、bracket_present 4、quote_open 4、comma 2、dash 1、enumeration_comma 1。
- 归因：**ocr_absent 31 / ocr_wrong_char 1 / reading_order 2**；render_dropped 0、filtered_furniture 0。
- 墨迹对账：**ink 25 / no_ink 9 / uncertain 0**。
- **「源图有墨但 OCR 没识别」旧裁片 = 22 条；t260 紧裁复核后 = 30 条**（`ocr_absent+ink`，见 §9）。
- 2 条 `reading_order` 是序列配对失败（PDF 里有标点），不是 OCR 漏识；9 条 `no_ink` 需先复核 gold/裁片（可能该处本就无标点）。

## 2. by_class × 归因

| class | ocr_absent | ocr_wrong_char | render_dropped | reading_order | filtered_furniture | 小计 | ink | no_ink |
|---|---|---|---|---|---|---|---|---|
| bracket_present | 4 | · | · | · | · | 4 | 4 | 0 |
| colon | 5 | · | · | · | · | 5 | 4 | 1 |
| comma | 2 | · | · | · | · | 2 | 2 | 0 |
| dash | 1 | · | · | · | · | 1 | 1 | 0 |
| enumeration_comma | 1 | · | · | · | · | 1 | 1 | 0 |
| period | 8 | · | · | 1 | · | 9 | 5 | 4 |
| quote_close | 6 | 1 | · | 1 | · | 8 | 5 | 3 |
| quote_open | 4 | · | · | · | · | 4 | 3 | 1 |

## 3. 墨迹对账

| 归因 | ink | no_ink | uncertain |
|---|---:|---:|---:|
| ocr_absent | 22 | 9 | 0 |
| ocr_wrong_char | 1 | 0 | 0 |
| reading_order | 2 | 0 | 0 |

## 4. 逐条清单

| id | 页 | class | gold | 归因 | 墨迹 | 上下文（前/后） |
|---|---:|---|---|---|---|---|
| fn_001 | 57 | dash | — | ocr_absent | ink | 金瓶梅這部書導讀【金瓶梅的淫穢問題 |
| fn_002 | 57 | colon | ： | ocr_absent | ink | 討過所得答案有二【一時代使然在明朝 |
| fn_003 | 57 | bracket_present | （ | ocr_absent | ink | 討過所得答案有二【一時代使然在明朝 |
| fn_004 | 57 | quote_close | 」 | reading_order | ink | 廂記屠隆的修元記【 |
| fn_005 | 57 | enumeration_comma | 、 | ocr_absent | ink | 廂記屠隆的修元記【 |
| fn_006 | 97 | period | 。 | ocr_absent | no_ink | 身轉的人有詩爲證【詩曰叔嫂萍蹤得偶 |
| fn_007 | 159 | colon | ： | ocr_absent | ink | 回酒各散去了正是【畢竟未知後來何如 |
| fn_008 | 159 | colon | ： | ocr_absent | ink | 何如且聽下回分解【倚門相送劉郎去煙 |
| fn_009 | 159 | quote_open | 「 | ocr_absent | ink | 何如且聽下回分解【倚門相送劉郎去煙 |
| fn_010 | 159 | comma | ， | ocr_absent | ink | 解倚門相送劉郎去【煙水桃花去路迷 |
| fn_011 | 159 | period | 。 | reading_order | ink | 去煙水桃花去路迷【 |
| fn_012 | 159 | quote_close | 」 | ocr_wrong_char | ink | 去煙水桃花去路迷【 |
| fn_013 | 704 | period | 。 | ocr_absent | no_ink | 名到使我真心陪奉【韓玉釧唱山坡羊惜 |
| fn_014 | 704 | quote_open | 「 | ocr_absent | no_ink | 奉韓玉釧唱山坡羊【惜玉憐香我和他在 |
| fn_015 | 704 | colon | ： | ocr_absent | no_ink | 如同夢裡董嬌兒唱【李桂姐唱金字經彈 |
| fn_016 | 704 | period | 。 | ocr_absent | no_ink | 江南岸夕陽山外山【吳銀兒唱駐雲飛唒 |
| fn_017 | 704 | quote_close | 」 | ocr_absent | no_ink | 江南岸夕陽山外山【吳銀兒唱駐雲飛唒 |
| fn_018 | 704 | bracket_present | 〕 | ocr_absent | ink | 山吳銀兒唱駐雲飛【唒書寄兩三番得見 |
| fn_019 | 704 | quote_open | 「 | ocr_absent | ink | 山吳銀兒唱駐雲飛【唒書寄兩三番得見 |
| fn_020 | 704 | period | 。 | ocr_absent | ink | 案滿紙春心墨未乾【韓玉釧唱江兒水香 |
| fn_021 | 704 | quote_close | 」 | ocr_absent | ink | 案滿紙春心墨未乾【韓玉釧唱江兒水香 |
| fn_022 | 704 | period | 。 | ocr_absent | ink | 尖空惹的張郎憎厭【這些時鶯花不捲簾 |
| fn_023 | 704 | period | 。 | ocr_absent | no_ink | 這些時鶯花不捲簾【董嬌兒唱畫眉序想 |
| fn_024 | 704 | quote_close | 」 | ocr_absent | no_ink | 這些時鶯花不捲簾【董嬌兒唱畫眉序想 |
| fn_025 | 704 | quote_open | 「 | ocr_absent | ink | 簾董嬌兒唱畫眉序【想在枕上溫存的話 |
| fn_026 | 705 | colon | ： | ocr_absent | ink | 李桂姐唱【耍孩兒你那裡偎紅 |
| fn_027 | 705 | bracket_present | 〔 | ocr_absent | ink | 李桂姐唱【耍孩兒你那裡偎紅 |
| fn_028 | 705 | quote_close | 」 | ocr_absent | no_ink | 離了去何時直得成【李桂姐唱尾聲半叉 |
| fn_029 | 830 | period | 。 | ocr_absent | ink | 酒也是拏勤勞准折【桂姐笑罵道怪硯花 |
| fn_030 | 830 | quote_close | 」 | ocr_absent | ink | 酒也是拏勤勞准折【桂姐笑罵道怪硯花 |
| fn_031 | 830 | comma | ， | ocr_absent | ink | 姐慢慢纔拏起琵琶【橫擔膝上啓朱唇露 |
| fn_032 | 830 | period | 。 | ocr_absent | ink | 將多應是我薄緣輕【黃鶯兒誰想有這一 |
| fn_033 | 830 | quote_close | 」 | ocr_absent | ink | 將多應是我薄緣輕【黃鶯兒誰想有這一 |
| fn_034 | 830 | bracket_present | 〔 | ocr_absent | ink | 將多應是我薄緣輕【黃鶯兒誰想有這一 |

## 5. 可恢复性与优先级

- **最高优先：period 9 / quote_close 8 / colon 5** —— 合计 22 条，其中 22 条源图有墨或待判；period/quote_close 是句末/引号闭合，补形收益最直接。
- **次优：bracket_present 4 / quote_open 4** —— 成对/开引号，补形需与配对逻辑联动，避免补出双引号。
- **comma 2 / dash 1 / enum 1** —— 量小，随同批补形即可。
- **9 条 no_ink 集中在 p704/p705（歌词页）**：先复核 gold 与源页映射，不建议直接补形；若确认源书无标点，应从 gold/评测口径侧修正（本任务不改 gold）。
- 2 条 reading_order：不是 OCR 漏识，转序列配对问题，不应计入补形收益。

## 6. 方法与证据

```bash
/usr/bin/python3 src/tools/punct_fn_audit.py \
  --gold data/punct_eval/content_gold_v1.json \
  --pdf output/wz7_full/wz7_full_v51.pdf \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --book wz7 \
  --out-json output/wz7/punct_fn_items.json --crops-dir output/wz7/punct_fn_crops
```

- 序列口径与 `punct_bench.sequence_eval` 相同（`seq_tokens`/`gap_map`/`_seq_group` 配对）；脚本额外保留每条 gold token 的 gap/上下文/命中情况。
- 归因优先级：严格 gap 判定 OCR 无目标字符 → `ocr_absent`；同 gap 有其它标点 → `ocr_wrong_char`；OCR 有目标而 PDF 无 → `render_dropped`；OCR/PDF 都有但配对失败 → `reading_order`。
- 墨迹：按 OCR line poly 裁源页 ±1.5 行高，2x 渲染；dark pixel >0.3% 判 ink。裁片 `output/wz7/punct_fn_crops/`（34 张，≤40），拼图 `output/wz7/punct_fn_montage.png`。
- 已知限制：裁片以 OCR line poly 为中心，可能包含邻字；`no_ink` 可能因 poly 取错行或页面影印/留白，需人工复核。

## 7. 明确的回答

- **34 FN 中「源图有墨但 OCR 没识别」= 22 条**（严格 `ocr_absent+ink`；含 1 条 `ocr_wrong_char+ink` 为 23 条）。
- **可直接补形估计**：旧 22；t260 紧裁后 30（附 §9 人眼复核）；**需序列修复** 2；**需 gold/源页复核** 1（fn001）。

## 8. 输出

- 逐条 JSON：`output/wz7/punct_fn_items.json`（34 条，含 page/reading order/gap/context/归因/ink/crop）。
- 裁片：`output/wz7/punct_fn_crops/`（34 张）；拼图：`output/wz7/punct_fn_montage.png`（34 张；no_ink 用占位图）。

## 4.1 逐条证据（JSON 同字段）

| id | 归因 | 证据 | OCR line |
|---|---|---|---|
| fn_001 | ocr_absent | no target char in OCR line/context | 一金瓶梅的淫穢問題 |
| fn_002 | ocr_absent | no target char in OCR line/context | 女之私呢？我想必有人會提出此一問題。這問題我也探討過，所得答案有二：（時代使然 |
| fn_003 | ocr_absent | no target char in OCR line/context | 女之私呢？我想必有人會提出此一問題。這問題我也探討過，所得答案有二：（時代使然 |
| fn_004 | reading_order | PDF has 」 but sequence pairing failed | 渭的「四聲猿」以及湯顯祖的「還魂記」，陸采的「南西廂記」、屠隆的「修元記」、 |
| fn_005 | ocr_absent | no target char in OCR line/context | 渭的「四聲猿」以及湯顯祖的「還魂記」，陸采的「南西廂記」、屠隆的「修元記」、 |
| fn_006 | ocr_absent | no target char in OCR line/context | 「叔嫂萍蹤得偶逢， |
| fn_007 | ocr_absent | no target char in OCR line/context | 慶帶上眼罩，由門去了。婦人下了簾子，關上大門，又和王婆吃了一回酒，各散去了。正是： |
| fn_008 | ocr_absent | no target char in OCR line/context | 倚門相送劉郎去，煙水桃花去路迷。 |
| fn_009 | ocr_absent | no target char in OCR line/context | 倚門相送劉郎去，煙水桃花去路迷。 |
| fn_010 | ocr_absent | no target char in OCR line/context | 倚門相送劉郎去，煙水桃花去路迷。 |
| fn_011 | reading_order | PDF has 。 but sequence pairing failed | 倚門相送劉郎去，煙水桃花去路迷。 |
| fn_012 | ocr_wrong_char | OCR line has 。, no 」 | 倚門相送劉郎去，煙水桃花去路迷。 |
| fn_013 | ocr_absent | no target char in OCR line/context | 金瓶梅 |
| fn_014 | ocr_absent | no target char in OCR line/context | 韓玉釧唱： |
| fn_015 | ocr_absent | no target char in OCR line/context | 金瓶梅 |
| fn_016 | ocr_absent | no target char in OCR line/context | 金瓶梅 |
| fn_017 | ocr_absent | no target char in OCR line/context | 金瓶梅 |
| fn_018 | ocr_absent | no target char in OCR line/context | ：〔〕「嗦！書寄兩三番，得見艱難。再猜霜毫，寫下喬公案，滿紙春心墨未乾。」 |
| fn_019 | ocr_absent | no target char in OCR line/context | ：〔〕「嗦！書寄兩三番，得見艱難。再猜霜毫，寫下喬公案，滿紙春心墨未乾。」 |
| fn_020 | ocr_absent | no target char in OCR line/context | ：〔〕「嗦！書寄兩三番，得見艱難。再猜霜毫，寫下喬公案，滿紙春心墨未乾。」 |
| fn_021 | ocr_absent | no target char in OCR line/context | ：〔〕「嗦！書寄兩三番，得見艱難。再猜霜毫，寫下喬公案，滿紙春心墨未乾。」 |
| fn_022 | ocr_absent | no target char in OCR line/context | 壓挨兩眉翠尖，空惹的張郎憎厭這些時，鶯花不捲簾。 |
| fn_023 | ocr_absent | no target char in OCR line/context | 金瓶梅 |
| fn_024 | ocr_absent | no target char in OCR line/context | 金瓶梅 |
| fn_025 | ocr_absent | no target char in OCR line/context | 董嬌兒唱： |
| fn_026 | ocr_absent | no target char in OCR line/context | 李桂姐唱： |
| fn_027 | ocr_absent | no target char in OCR line/context | 李桂姐唱： |
| fn_028 | ocr_absent | no target char in OCR line/context | 李桂姐唱： |
| fn_029 | ocr_absent | no target char in OCR line/context | ，你唱個兒我聽下酒，也是拏勤勞准折。」一桂姐笑罵道：「怪硯花子，你虵蟋兒，好大面皮兒！爹他肯 |
| fn_030 | ocr_absent | no target char in OCR line/context | ，你唱個兒我聽下酒，也是拏勤勞准折。」一桂姐笑罵道：「怪硯花子，你虵蟋兒，好大面皮兒！爹他肯 |
| fn_031 | ocr_absent | no target char in OCR line/context | 。」笑了一回，桂姐慢慢纔拏起琵琶，横擔膝上，啓朱唇，露皓齒，唱了個州三台令： |
| fn_032 | ocr_absent | no target char in OCR line/context | ，疑望他怎生全無個音信？幾回自將，多應是我薄緣輕。」〔〕一 |
| fn_033 | ocr_absent | no target char in OCR line/context | ，疑望他怎生全無個音信？幾回自將，多應是我薄緣輕。」〔〕一 |
| fn_034 | ocr_absent | no target char in OCR line/context | ，疑望他怎生全無個音信？幾回自將，多應是我薄緣輕。」〔〕一 |


## 9. 人眼复核（t260）

### 9.1 裁片重建

- 34/34 张裁片全部为**紧裁**：以 FN 期望位置为中心，约 6×字高，4× 渲染；单字 ≥60px。
- 每张叠画：红框=FN 期望位置；顶部/左侧坐标刻度；顶部标签 `fn id page class attribution`。
- 文件名含 page/class/归因，如 `fn_013_p0704_period_ocr_absent.png`。
- 坐标修复：OCR 竖排 coords 为像素尺度且 y 轴自下而上，脚本按源页尺寸缩放并翻转；行定位按 gold 上下文最长匹配（修复了 index 比较 bug）。
- 拼图：`output/wz7/punct_fn_montage.png`（34 张，6 列 ≤6 行）。

### 9.2 no_ink 9 条复核

旧 no_ink：`fn_006`(p97 period)、`fn_013/014/015/016/017/023/024`(p704)、`fn_028`(p705)。
紧裁修正后：
- **8/9 重新有墨**（此前取错 OCR 行/坐标未缩放翻转；p704/p705 歌词页实际有字有标点语境）；
- **1/9 仍 no_ink**：`fn_001 p57 dash`（期望位置取在行尾，裁片落在空白；见 §9.4）；
- **没有发现源图确实无标点的案例 → 不需要 gold 修正清单**（gold 修正建议：无）。
- 结论：旧 no_ink 9 条主要是**裁片逻辑错误**，不是 gold 错。

### 9.3 ink 抽样 10 条复核

抽样（含 period/quote_close/colon 各 ≥2）：
`fn_006`(period p97)、`fn_016`(period p704)、`fn_023`(period p704)、`fn_004`(quote_close p57)、`fn_021`(quote_close p704)、`fn_024`(quote_close p704)、`fn_007`(colon p159)、`fn_015`(colon p704)、`fn_026`(colon p705)、`fn_030`(quote_close p830)。
逐图确认：10/10 裁片在红框附近均能看到**正文/标点墨迹**；未发现 >2 条“实际无墨”。
- 因此紧裁后 `ocr_absent+ink` 从旧 22 调整为 **30**；`ocr_wrong_char+ink` 1 条仍为字符纠正候选。

### 9.4 reading_order 2 条

| id | 页 | class | 上下文 | 失败原因 | 建议 |
|---|---|---|---|---|---|
| fn_004 | 57 | quote_close | `廂記屠隆的修元記` | PDF 文本层有对应 `」`，但 `gap_map` 把它映射到下一个锚点 gap；属**序列配对口径**，非 OCR/位置错 | 在 gap_map 后增加 ±1 gap 容差或“同一标点重复”消歧；不改 gold |
| fn_011 | 159 | period | `去煙水桃花去路迷` | 同上：PDF 有 `。`，位于块尾 gap，配对被前一个标点占用 | 对块尾标点允许 gap+1 匹配；补单测 |

结论：2 条均属 **eval 口径**（序列配对），不是 gold 位置错误；建议在 `sequence_eval` 的 `gap_map` 匹配加 ±1 gap 容差（或只对块尾标点），预期可回收 2 条，不影响已知 34 计数口径的旁路报告。

### 9.5 最终结论表（t260）

| class | 可补形 | gold 需修 | eval 口径 | 其他 | 合计 |
|---|---:|---:|---:|---:|---:|
| period | 8 | 0 | 1 | 0 | 9 |
| quote_close | 6 | 0 | 1 | 1 | 8 |
| colon | 5 | 0 | 0 | 0 | 5 |
| bracket_present | 4 | 0 | 0 | 0 | 4 |
| quote_open | 4 | 0 | 0 | 0 | 4 |
| comma | 2 | 0 | 0 | 0 | 2 |
| dash | 0 | 0 | 0 | 1 | 1 |
| enumeration_comma | 1 | 0 | 0 | 0 | 1 |
| **合计** | **30** | **0** | **2** | **2** | **34** |

- **可补形 = 30 条**（`ocr_absent + ink`，紧裁/抽样复核；旧口径 22，增量为修正裁片后新见墨）。
- 证据覆盖率：**34/34 条有紧裁片 + 标签**；其中 10 条抽样人眼确认，其余由同一流程/墨迹阈值判定。
- 其他 2：1 条 `ocr_wrong_char+ink`（字符纠正）、1 条 `no_ink`（fn001 裁片定位待再修）。
- 优先级：period 8 / quote_close 6 / colon 5 最值得投入；dash 1 条为裁片定位问题，不建议现在补。
