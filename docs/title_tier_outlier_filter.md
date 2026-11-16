# 标题字号离群样本过滤（t360）

## 根因

`_lvl_h` 采样只有下限 `h>H_BODY*1.1`，无上限；wz10 part 样本被 p1 h982/p3 h728/p53 h422/p38 h413/p3 h402 等竖排列/图注污染，中位392px→tier_size≈173pt。

## 修法

- 采样加 `_h > H_BODY*4` 直接丢弃（竖排列/合并行/图注）。
- wz10 part 只剩 p17 h86 → tier_size **38.0pt**。
- 删除 `config/books/wz10.json image_pages:[17]`，p17 恢复矢量。

## 实测

- p17 `第三编` **36.3pt** x251.0–359.8；`隋唐五代时期` 36.3pt x196.6–414.1，居中。
- p17 无整页图（images=0）；wz10 60页；无 span >50pt（全页扫描）。
- 8 本中 ghbq 重建 104页逐页文本 diff **0**；其余书无配置/采样变化未逐本重建（需补）。
- 产物 output/uploaded/wz10_tierfix.pdf；p17裁片。

未改gold/punct_eval；未push/commit。
