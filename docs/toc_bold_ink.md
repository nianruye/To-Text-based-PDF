# 目录加粗按墨迹（t341）

- 在 `_TOC_PAGE` 上启用 `_ink_bold_lines`，`toc_bold_ink` opts 时：
  - 墨迹判 bold → L1/L2 bold；
  - 灰区/常规 → 不加粗；
  - 章节 `第X章` 作为硬兜底（源书章行粗体）保留。
- 实测 wz9 p12 仍全部 Regular（`第一章` 也 Regular），说明 ink 命中/章节兜底未生效；未达“不一致=0”。
- 未改 ghbq/wz4 的目录路径（opts 仅 wz9），但 7 本未逐页回归。
- 产物 output/uploaded/wz9_tocbold.pdf（82页）；p12裁片。

## t342 更正：源书目录条目全 Regular

- 源图 300dpi 笔画中位：目录4.0（标题），第一章/绪论/第一节/第二节=2.0；比例≈1.0。
- 修法：`toc_bold_ink` 时目录 L1/L2 一律不加粗（保守）；`INK_BOLD_DBG=1` 分支打印 `[toc-bold] ratio=1.00 -> Regular`。
- 实测 p12 全部 Regular（目录标题也不受影响）；wz9 82页。
- ghbq/wz4 无 `toc_bold_ink`，路径不变。
- 产物 output/uploaded/wz9_tb2.pdf；p12裁片。
