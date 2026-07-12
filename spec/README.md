# Spec 文档索引

## 总 Spec
- [00_system_architecture.md](00_system_architecture.md) - 系统总体架构（目标/类型/路由/共享基础/技术栈/目录结构/可扩展性）

## 分部 Spec

| 类型 | 目录 | 状态 | 说明 |
|---|---|---|---|
| 古籍 | [ancient/](ancient/) | ✅ 已实现 | CJK 墨高重叠、夹注本双规制、旁注竖排、校注标记 |
| 现代书籍 | [modern/](modern/) | ✅ 已实现 | 段落缩进、脚注、页眉页码、标题层级 |
| 论文 | [paper/](paper/) | 🔜 待建 | 公式、表格、图表标题、参考文献 |
| 合同 | [contract/](contract/) | 🔜 待建 | 条款编号、签章区域、固定格式 |
| 标书 | [bid/](bid/) | 🔜 待建 | 复杂表格、多层目录、附件 |

## 文档类型

| 类型 | 特征 | 管线 | 当前指标 |
|---|---|---|---|
| 古籍 | 墨高重叠、夹注、旁注 | `src/pipelines/build_classic.py` | 783页 pitch 57% 0溢出 |
| 现代书籍 | 段落、脚注、标题 | `src/pipelines/build_geom.py` | 222页 pitch 95% 0溢出 |

## 运行命令

```bash
# 古籍（wz2）
cd /opt/test && LAYJSON="data/wz2/wz2.pdf_by_PaddleOCR-VL-1.6.json" PAGE_FONT=1 PER_PAGE_PITCH=1 \
  python3 src/calibration/fit_positional_classic.py data/wz2/wz2_spotting_lines.json data/wz2/wz2_spotting_coords.json output/out.pdf source_pdf/wz2.pdf

# 现代书籍（wz1）
cd /opt/test && LAYJSON="data/wz1/wz1.pdf_by_PaddleOCR-VL-1.6 .json" PER_PAGE_PITCH=1 PAGENUM_GLOBAL_TABLE=data/wz1/wz1_full_pagenum.json \
  python3 src/calibration/fit_positional.py data/wz1/wz1_spotting_lines.json data/wz1/wz1_spotting_coords.json output/out.pdf source_pdf/wz1.pdf

# 测试
python3 src/test/test_cases.py output/成果_wz2_classic_latest.pdf

# 全局验证
python3 src/test/verify_geom.py output/out.pdf data/wz2/wz2_spotting_coords.json data/wz2/wz2_spotting_lines.json --src-pdf source_pdf/wz2.pdf --json /tmp/verify.json
```

## SDD + TDD 开发流程

新功能按以下流程（Spec-Driven + Test-Driven）：

```
1. Spec    -> 写 spec/<type>/XX_function.md（目标/输入/输出/约束/测试点）-> 用户确认
2. Test    -> 写 src/test/test_cases.py 断言（预期 FAIL，红）
3. Implement -> 实现代码（使测试 PASS，绿）
4. Verify  -> 全部测试 PASS + verify_geom 无回归
```

### 示例：新增"注释序号分列"功能

```
1. spec/ancient/03_note_sequence_alignment.md（已写）
2. test_cases.py 加 test_p15_seq_x0（预期 FAIL）
3. build_classic.py 实现 _note_text_x + 序号分列
4. python3 src/test/test_cases.py -> 17 PASS 0 FAIL ✓
```

## Spec 规范

新增功能/类型时：
1. 在对应类型目录下写 Spec（`XX_function.md`）
2. 格式：目标/背景/方案/输入/输出/约束/测试点
3. 更新本 README 索引
4. 实现后写测试用例（`src/test/test_cases.py` 扩展）
