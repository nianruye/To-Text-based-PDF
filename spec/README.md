# build_classic.py 功能 Spec 索引

古籍专用排版还原（build_classic.py + fit_positional_classic.py）。

## Spec 文件

| 编号 | 文件 | 功能 |
|---|---|---|
| 01 | [pitch_overlap.md](01_pitch_overlap.md) | 墨高重叠 \\[-2pt]（CJK 行距<行盒） |
| 02 | [font_classification.md](02_font_classification.md) | 字号分类 + 序号位置识别 |
| 03 | [note_sequence_alignment.md](03_note_sequence_alignment.md) | 注释序号-文字分列对齐 |
| 04 | [text_rendering.md](04_text_rendering.md) | 正文缩进 + 字距 + 标题续行 |
| 05 | [esc_markers.md](05_esc_markers.md) | 校注标记转义 + 符号修正 |
| 06 | [aside_page_image.md](06_aside_page_image.md) | 旁注补全 + 页码补全 + 书影带 |
| 07 | [positional_calibration.md](07_positional_calibration.md) | 位置还原两趟校准 |

## 架构

```
wz2.pdf -> PaddleOCR-VL spotting(行级) + layout(版面)
  -> build_classic.py(排版还原)
    -> fit_positional_classic.py(两趟校准)
  -> 输出 PDF
```

## 当前指标（v24）

| 指标 | 值 |
|---|---|
| 页数 | 783（=源） |
| 溢出 | 0 |
| pitch 达标 | 53.3% |
| 空白页 | 101 |
| 占位达标 | 86.3% |

## 共享逻辑（build_geom.py）

build_classic.py 从 build_geom.py 复制，共享：
- esc()/page_pitch()/_esc_chars() 等基础函数
- 书影带处理（LAYJSON image block + detect_fig_bands）
- 页码补全（_lay_numbers + 连续推断）
- aside 补全（目录篇名匹配）

build_geom.py 保留现代书（wz1），build_classic.py 专注古籍（wz2）。
