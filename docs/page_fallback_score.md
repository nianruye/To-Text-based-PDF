# 不可靠页自动降级（t340）

## 规则

- 依据 layout blocks：`vertical_text >= 2` 且 `image >= 1` → 判为手写/影印不可靠页，`_page_img_full=True`，整页贴源图 + 文本 3Tr。
- p5 命中：layout 有 2 个 vertical_text + 1 image；p18 无 vertical_text，且走 structured_toc 特殊路径，不降级。
- fallback 清单写 `<out>.fallback.json`；当前 build 临时路径。

## 样本

| 页 | vertical_text | image | 降级 |
|---|---:|---:|---|
| wz9 p5 | 2 | 1 | 是 |
| wz9 p6/p7/p8 | 0 | 0 | 否 |
| wz9 p18 | 0 | 0 | 否 |
| ghbq p15/p23 | 0 | 0 | 否 |
| wz1 p20 | 0 | 0 | 否 |

## 验收

- 删除 `config/books/wz9.json image_pages` 后，wz9 p5 **1图 + 187字文本层**；p18 41行结构目录；页数82。
- ghbq 104 逐页 diff0。
- 其余书未逐本重跑；规则仅 vertical_text>=2 触发。
- 输出 output/uploaded/wz9_auto.pdf；p5/p18裁片。

未改 gold/punct_eval；未 push/commit。
