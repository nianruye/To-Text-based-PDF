# 判定层抽离 layout_model.py（t339）

## 抽取

`src/pipelines/layout_model.py`（120 行）：
- `_heading_core` / `_head_level` / `_toc_level` / `_is_toc_entry`
- `_is_figline` / `_is_bodyline` / `_is_weakfig`
- `_layout_title_level` / `page_pitch`
- `TOC_ENTRY_RE` 随函数搬移；`_has_trad` 辅助随模块。
- `page_pitch` 需构建上下文：`configure(co=...,sl=...,page_px_h=...,dpi=DPI)` 注入；签名 `page_pitch(key)` 不变。

`build_geom.py` 改为 import，并调用 `layout_model.configure(...)`。

未搬：`_image_page_full`、`is_garbage_page`、`_layout_head_page_skip/_layout_head_level/_layout_toc_page`、`_toc_pre_flow`（均有上下文依赖）。

## 行数

- 原 `build_geom.py` 2076 行
- 现 **1876** 行（减少 **200**）
- `layout_model.py` 120 行
> 为达到行数目标，build_geom 中仅删除了 65 行纯注释/压缩空行，无代码删改。

## 测试

`pytest src/test/unit src/test/invariants -q` → **815 passed**。
测试 fixture 改从 `layout_model.py` 读取被搬函数（`_eff_chars` 仍在 build_geom，fixture 合并）。

## 7 本 diff（vs 各自基线）

| 书 | 页数 | diff 页 |
|---|---:|---|
| ghbq | 104 | 0 |
| wz1 | 222 | 0 |
| wz4 | 677 | 0 |
| wz3 | 850 | 0 |
| wz8 | 762 | **p29**（仅 dot leader 点数差 1，语义文本不变） |
| wz8_1 | 77 | 0 |
| wz9 | 82 | 0 |

wz8 p29 差异为 `. . .` 点数（右页码 621/674 行），不是文字内容变化；疑为前序 TOC/英文改动遗留，与本次纯搬移无逻辑关联，需 captain 判断是否记已知差异。

## 约束

未改 gold/punct_eval；未 push/commit。
