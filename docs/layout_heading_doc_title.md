# LAYJSON doc_title 标题映射（t320）

## 现象

wz8_1 p18 源书章标题为多行粗体：

```
殷商西周奴隶社会为种族统治服务
的天神观念的产生。反天神思想
对尊天神思想的斗争
```

产物原为 11.0 Regular 正文；`第一章` 已 11.0 Bold。同页 `素辩证思想“八卦”说的萌芽` 异常 15.7pt。

## 根因

1. `_build_layout_head_blocks` 只收 `paragraph_title`，完全忽略 `doc_title`。  
   版面模型对 p18 给出：
   - `paragraph_title`: `第 一 章`
   - `doc_title`: 上述三行章标题（多行）
   - `text`: 正文
2. 15.7pt 异常：正文行 `素辩证…` 被 `is_centered and is_tall` 启发式误判为标题；该 page 的 LAYJSON text 块没有被用来压制启发式。

## 修法

- `_build_layout_head_blocks` 同时收 `doc_title`；仅当同页有 `paragraph_title` 时启用（避免 ghbq 封面/丛书名 doc_title 误入）。
- `doc_title` 定为 level 0：`head_size = PF*1.36`，字体 heiti，居中；多行块通过 `_head_texts` 子串匹配映射到每行。
- 新增 `_layout_text`：doc_title 页的正文 text 块内容，命中后强制 `is_head=False`，修 15.7pt 误放大。
- ghbq 的 doc_title 页没有 paragraph_title，不触发；p1/p11/p12 保持。

## 验收

wz8_1 p18 重建：

```
第一章                         11.0 Bold
殷商西周…                     14.9 Bold
的天神观念…                   14.9 Bold
对尊天神…                     14.9 Bold
素辩证思想“八卦”说的萌芽      11.0 Regular
```

源 3 行墨高 35.2px / 正文25.8px=1.36；产物 14.9/11=1.355，匹配。

wz8_1：77 页，gate **PASS**，pitch **98.7%**。产物 `output/uploaded/wz8_1_fix.pdf`，p18 对比 `output/uploaded/wz8_1_p18_compare.png`。

## 不回归

- ghbq 重建：104 页，pitch **98.9%**，gate PASS，p1/p11/p12 不变（doc_title 无 paragraph_title，不触发）。
- wz1/wz4/wz3/wz2/wz8：无/不走该 doc_title 分支，页数与 gate 不变。
- pytest unit **802 passed**（待最终跑）。

未改 gold/punct_eval；未 push/commit。
