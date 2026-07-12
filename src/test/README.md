# 测试文档

## 测试体系

### L1 全局指标（verify_geom.py）
- **文件**: `src/test/verify_geom.py`
- **用途**: 全书统计指标（pitch达标率/溢出/空白/占位/页数）
- **运行**:
```bash
python3 src/test/verify_geom.py output/out.pdf data/wz2/wz2_spotting_coords.json data/wz2/wz2_spotting_lines.json --src-pdf source_pdf/wz2.pdf --json /tmp/verify.json
```
- **输出示例**:
```
pitch 误差 <3%  : 57.0%  (样本 769)
溢成多物理页的源页(全量): 0   缺失页: 0
中位: 页高误差 2.9% | pitch 误差 2.1% | 底部占位偏差 +4.2%
```

### L2 功能断言（test_cases.py）
- **文件**: `src/test/test_cases.py`
- **用途**: 具体页 + 具体断言（防功能级回归）
- **运行**:
```bash
python3 src/test/test_cases.py output/成果_wz2_classic_latest.pdf
```
- **输出示例**:
```
测试: output/成果_wz2_classic_latest.pdf (783页)
------------------------------------------------------------
  ✓ 01 pitch_p11          p11 pitch≈35
  ✓ 01 pitch_p26          p26 pitch≈28
  ✓ 01 no_overflow        783页 0溢出
  ✓ 02 p11_body_font      正文 17pt
  ✓ 02 p15_note_font      注释 14.6pt
  ✓ 03 p15_seq_x0         序号x0统一
  ✓ 03 p15_cont_x0        续行x0统一
  ✓ 05 p11_marker_sz      上标 8.6pt
  ✓ 06 p11_aside          aside补全
  ✓ 06 p11_pagenum        页码=1
  ...
------------------------------------------------------------
17 PASS, 0 FAIL
```

## 测试用例说明

### 01 墨高重叠（4个）
| 用例 | 断言 | 对应 Spec |
|---|---|---|
| pitch_p11 | p11 pitch 33-37pt（源35.1） | 01_pitch_overlap |
| pitch_p26 | p26 pitch 26-30pt（源28.0，注释页） | 01_pitch_overlap |
| no_overflow | 页数=783（0溢出） | 01_pitch_overlap |
| pitch_rate | p11/p26/p51 pitch 合理（>25pt） | 01_pitch_overlap |

### 02 字号分类（3个）
| 用例 | 断言 | 对应 Spec |
|---|---|---|
| p11_body_font | p11 正文字号 16-18pt | 02_font_classification |
| p15_note_font | p15 注释字号 13.5-15.5pt | 02_font_classification |
| p5_preface_font | p5 前言字号 15-17pt（非BODY 18/NOTE 14.6） | 02_font_classification |

### 03 序号分列（3个）
| 用例 | 断言 | 对应 Spec |
|---|---|---|
| p15_seq_x0 | p15 序号〔X〕x0 差<=20（统一） | 03_note_sequence_alignment |
| p15_cont_x0 | p15 续行 x0 差<=20（统一，排除frags） | 03_note_sequence_alignment |
| p15_no_overlap | p15 序号+文字 span 间距>=-2（不重叠） | 03_note_sequence_alignment |

### 04 正文缩进（2个）
| 用例 | 断言 | 对应 Spec |
|---|---|---|
| p11_indent | p11 至少1行 x0>85（段首缩进2em） | 04_text_rendering |
| char_spacing | p11 字距>=-8（不重叠，排除上标span） | 04_text_rendering |

### 05 校注标记（3个）
| 用例 | 断言 | 对应 Spec |
|---|---|---|
| p11_marker_sz | p11 〔X〕上标 sz<10pt | 05_esc_markers |
| p32_circle | p32 含〇非￿（○->〇） | 05_esc_markers |
| no_wrong_bracket | 前100页无】（转〔〕） | 05_esc_markers |

### 06 旁注/页码（2个）
| 用例 | 断言 | 对应 Spec |
|---|---|---|
| p11_aside | p11 右栏含"一"（aside补全） | 06_aside_page_image |
| p11_pagenum | p11 页码=1 | 06_aside_page_image |

## 新增测试用例

新增功能时：
1. 在对应 Spec 的"测试点"写断言描述
2. 在 test_cases.py 加 `test_XX_function(pdf)` 函数
3. 在 TESTS 列表注册
4. 运行确认 PASS

```python
# 示例：新增"注释序号分列"测试
def test_p15_seq_text_align(pdf):
    """p15 序号行文字与续行对齐(文字列)"""
    lines = _get_lines(pdf, 14)
    seq_lines = _find_seq_lines(pdf, 14)
    cont_lines = [l for l in lines if 70 < l[0] < 110 and len(l[5]) > 10]
    if seq_lines and cont_lines:
        # 序号行文字 x0 ≈ 续行 x0
        ...
```
