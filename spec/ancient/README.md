# 古籍排版 Spec 索引

古籍专用排版还原（`src/pipelines/build_classic.py` + `src/calibration/fit_positional_classic.py`）。

## Spec 文件

| 编号 | 文件 | 功能 | 测试断言 |
|---|---|---|---|
| 01 | [pitch_overlap.md](01_pitch_overlap.md) | 墨高重叠 \\[-2pt]（CJK 行距<行盒） | pitch_p11 / pitch_p26 / no_overflow / pitch_rate |
| 02 | [font_classification.md](02_font_classification.md) | 字号分类 + 序号位置识别 | p11_body_font / p15_note_font / p5_preface_font |
| 03 | [note_sequence_alignment.md](03_note_sequence_alignment.md) | 注释序号-文字分列对齐 | p15_seq_x0 / p15_cont_x0 / p15_no_overlap |
| 04 | [text_rendering.md](04_text_rendering.md) | 正文缩进 + 字距 + 标题续行 | p11_indent / char_spacing |
| 05 | [esc_markers.md](05_esc_markers.md) | 校注标记转义 + 符号修正 | p11_marker_sz / p32_circle / no_wrong_bracket |
| 06 | [aside_page_image.md](06_aside_page_image.md) | 旁注补全 + 页码补全 + 书影带 | p11_aside / p11_pagenum |
| 07 | [positional_calibration.md](07_positional_calibration.md) | 位置还原两趟校准 | （全局，verify_geom） |
| 08 | [appendix_layout.md](appendix_layout.md) | 附录排版：标题分开/小标题识别/案注小字/续行/段间留白/缩进对齐 | （附录区，verify_geom） |

## 架构

```
wz2.pdf -> PaddleOCR-VL spotting(行级) + layout(版面)
  -> src/pipelines/build_classic.py(排版还原)
    -> src/calibration/fit_positional_classic.py(两趟校准)
  -> 输出 PDF
```

## 当前指标

| 指标 | 值 |
|---|---|
| 页数 | 783（=源） |
| 溢出 | 0 |
| pitch 达标（误差<3%） | 59.1% |
| 页高误差<5% | 84.7% |
| 底部占位<8%偏差 | 87.0% |
| 空白页 | 97 |
| 测试 | 17 PASS / 0 FAIL |

## 运行

```bash
cd /opt/test && LAYJSON="data/wz2/wz2.pdf_by_PaddleOCR-VL-1.6.json" \
  PAGE_FONT=1 PER_PAGE_PITCH=1 LAYOUT_HEADINGS=1 \
  python3 src/calibration/fit_positional_classic.py \
  data/wz2/wz2_spotting_lines.json data/wz2/wz2_spotting_coords.json \
  output/out.pdf source_pdf/wz2.pdf

# 测试
python3 src/test/test_cases.py output/out.pdf
# 几何验证
python3 src/test/verify_geom.py output/out.pdf \
  data/wz2/wz2_spotting_coords.json data/wz2/wz2_spotting_lines.json --src-pdf source_pdf/wz2.pdf
```

**参数说明**：
- `LAYJSON`：必须用 `wz2.pdf_by_PaddleOCR-VL-1.6.json`（PaddleOCR-VL，aside_text 1337 非空）；**不能用 pp_doclayout_wz2.json**（aside_text 全空，旁注不渲染）
- `PAGE_FONT=1`：正文/注释两类全局字号（BODY_FONT≈17.3 / NOTE_FONT≈14.7）
- `PER_PAGE_PITCH=1`：per-page 源 pitch 作 baselineskip
- `LAYOUT_HEADINGS=1`：用 PaddleOCR-VL paragraph_title 识别标题（含附录小标题如"司马迁史记"）
- `POSITIONAL=1`：位置还原（fit_positional_classic.py 自动设）

## 共享逻辑（build_geom.py）

build_classic.py 从 build_geom.py 复制，共享：
- esc()/page_pitch()/_esc_chars() 等基础函数
- 书影带处理（LAYJSON image block + detect_fig_bands）
- 页码补全（_lay_numbers + 连续推断）
- aside 补全（目录篇名匹配）

build_geom.py 保留现代书（wz1），build_classic.py 专注古籍（wz2）。
