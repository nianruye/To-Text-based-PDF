# wz10 目录条目间距（t356）

## 根因

配对后仍按源 y 跳转；被合并的 3 行高度变成空洞 → 77.1pt。改为顺序流式：条目行后固定 `\vspace{16pt}`；未配对标题仍在首。

## 修法

- 特殊目录页 `toc_split_pagenum_pages` 去掉条目间 `\vfill`，改 `\vspace{16pt}`。
- 页顶内容从 `\vspace*{223pt}` 起（产物首 ink 245.8pt）。
- 点线+页码仍单行；副标题独立。

## 实测

- p15 条目 ink 间距中位 **27.6pt**（目标27.9±10%）；首 ink **245.8**。
- p16 间距 **25.9pt**；首 **244.8**；footer `6` 无。
- wz10 60页；p15/p16 条目全部、页码右对齐、章 Bold14.9。
- 其他书无 `toc_split_pagenum_pages`，零回归。
- 产物 output/uploaded/wz10_toc3.pdf；p15/p16裁片。

未改gold/punct_eval；未push/commit。
