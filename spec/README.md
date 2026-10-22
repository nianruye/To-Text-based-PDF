# Spec 文档索引

## Spec 状态账本

每条 spec 有四种状态：governance / planned / implemented / archived。PR 合并前必须更新状态（见 [AGENTS.md](../AGENTS.md) spec 对账规则）。

### governance（治理契约，跨管线公共约定）

| spec | 说明 |
|---|---|
| [governance/PIPELINE_BEHAVIOR.md](governance/PIPELINE_BEHAVIOR.md) | 管线行为契约：**横排**（契约 1-6 = argv / env / JSON / GMPG / DPI / 命名）+ **竖排**（「竖排管线（build_vert.py）」章节 = V1-V9 argv/env/JSON/GMPG-N.A./坐标页幅/产物/差异对照/验收/锚点/实测基线）+ 验收标准 + 实现锚点 + 兼容影响矩阵（含竖排行）+ CI 结论 |

### planned（已规划，待实现）

| spec | 说明 | 关联 issue |
|---|---|---|
| `/tmp/seg2_line.*` 路径分离 | geom/classic 临时文件分 build_name，消除并发冲突 | AGENTS.md #10 |
| `_esc_chars` 两方分叉统一 | geom/classic 转义规则是否统一（v13 已 archived，不参与） | AGENTS.md #11 |
| ~~geom `page_pitch` inner 过滤~~ | ~~与 classic 统一~~ | **不修**（实测 pitch 89.9%->15.4%，保守策略正确） |

### implemented（已实现，行为已锁定）

| spec | 说明 |
|---|---|
| [governance/PIPELINE_BEHAVIOR.md](governance/PIPELINE_BEHAVIOR.md) | 管线行为契约（横排 6 条契约 + 竖排章节 V1-V9 + 验收 + 锚点 + 兼容影响矩阵含竖排行 + CI 结论） |
| [00_system_architecture.md](00_system_architecture.md) | 系统总体架构 |
| [ancient/](ancient/) | 古籍排版（01-08 + appendix_layout） |
| [modern/](modern/) | 现代书籍排版（footnote / header_pagenum / heading / toc） |
| [vertical/](vertical/) | 竖排书排版（engine / tate_layout / marginalia / frame_lines / pagenum_sequence / derot / 07 字模横向压缩+列内空隙 / 08 标点竖排形态 / 09 参数自标定 + 纸型无关化 / 10 西文行侧排+标题署名行+影印页整页贴图 / 15 竖排破折号整格矢量竖线）；验证脚本 `src/test/verify_vert.py` |
| [docs/vert_wz7_layout3_report.md](../docs/vert_wz7_layout3_report.md) | 竖排 wz7 300 页版面元素报告（taskR 实现西文行/标题署名/影印页贴图 + taskR2 西文行紧凑化口径：拉丁 TFM 字体、破折号按 run 实测长、bp↔TeX pt 换算、逐片基线；含四项复核的实测对账与影印页普查分离度） |
| [docs/vert_dash_rule_report.md](../docs/vert_dash_rule_report.md) | 竖排破折号整格矢量竖线报告（taskD：选项 A 每字满一格 rule 无缝拼接 + 3 Tr 保留文本层；p57 空隙 0.00pt / 2×step / 线心差 0.19pt；p29 西文侧排与 wz6 逐字节零回归；含仍存假破折号数据审计建议） |
| [docs/pipeline_audit.md](../docs/pipeline_audit.md) | 三管线+两校准代码审计（7 点） |
| [docs/coupling_analysis.md](../docs/coupling_analysis.md) | 暗中耦合分析（依赖图+状态地图+契约+风险因果链） |
| [docs/vert_governance_report.md](../docs/vert_governance_report.md) | 竖排纳入治理门禁报告（竖排契约逐条源码核对含行号 + CI 结论 + 实测基线 + 遗留 R1-R4） |
| [docs/vert_fix18_20_27_report.md](../docs/vert_fix18_20_27_report.md) | 竖排收尾修复报告（#18 退出码分级 + #20 临时目录按产物名分离 + #27 数字实测核对；含验收实测与渲染零变化对照） |
| [docs/vert_width_gap_report.md](../docs/vert_width_gap_report.md) | 竖排字宽压缩收尾报告（taskJ2：`\scalebox` btrans/etrans 数值逆矩阵泄漏根因与 q/cm/Q 精确还原修法 + 列内空隙 DP 检出全书落地 + 独立复核口径失效分析） |
| [docs/vert_calib_report.md](../docs/vert_calib_report.md) | 竖排参数自标定报告（taskM：wz6 硬编码常数 -> 建排前自动标定 + 对账表 + 产物不回退证据 + **换书剩余人工依赖清单**） |
| [docs/pipeline_architecture.html](../docs/pipeline_architecture.html) | 架构图（深色 SVG） |
| [src/test/snapshots/CURRENT_BEHAVIOR_SPEC.md](../src/test/snapshots/CURRENT_BEHAVIOR_SPEC.md) | 回归快照现状 spec（wz1/优化前/wz2 排版现状） |
| [src/test/unit/PURE_FUNC_SPEC.md](../src/test/unit/PURE_FUNC_SPEC.md) | 纯函数行为 spec（12 函数契约） |
| [src/test/invariants/INVARIANTS_SPEC.md](../src/test/invariants/INVARIANTS_SPEC.md) | 特征不变量 spec（13 不变量） |
| [architecture_audit.md](architecture_audit.md) | 架构审计（7 点 + 竖排能力缺口，基于 Step 1-6 + 9 bug 修复后代码） |

### archived（已归档/已修）

| 条目 | 说明 |
|---|---|
| verify_geom 无退出码 | 已修（verify_geom.py L274-298 加退出码） |
| fit_positional/classic 97 行重复 | 已修（合并到 fit_common.py 90+3+3 行） |
| build_pdf_v13.py | src/ 内孤立（零调用），未接入共享模块，无 invariants/verify_geom 保护。12 项独有功能作为参考实现存档，不再维护。如需独有能力，开 issue 提取逻辑 |

---

## 术语表

| 术语 | 含义 |
|---|---|
| **pitch** | 行间距（相邻两行文字基线/中心的垂直距离，pt）。源 pitch 从 OCR spotting y 坐标差中位测量；输出 pitch 从 PDF 行 bbox 测量。pitch 误差 = 输出 vs 源的偏差%，达标率（<3%误差）越高越好 |
| **行盒高** | 单行文字的总高度（含墨色+空白），LaTeX hbox 不重叠时行距=行盒高 |
| **墨高重叠** | CJK 古籍排版特征：行间距 < 行盒高（行间墨色微重叠 2pt），LaTeX 默认不重叠 |
| **spotting** | PaddleOCR-VL 行级 OCR 模式（useLayoutDetection=False），输出每行文字 + bbox |
| **layout** | PaddleOCR-VL 版面分析模式（useLayoutDetection=True），输出 image/aside_text/number 等 block |
| **bl（baselineskip）** | LaTeX 行距参数，\fontsize{fnt}{bl} 的第二参数 |
| **strut** | LaTeX \rule{0pt}{h}，设定 hbox 最小高度（行盒高），不影响文字 |
| **BODY_FONT** | 正文字号（满行26字 -> 18pt） |
| **NOTE_FONT** | 注释字号（满行32字 -> 14.7pt） |
| **cw** | 满行字数（行宽 > 0.8×最大行宽 的行字数中位），用于算字号 |
| **_note_text_x** | 注释页文字列 x0（续行 x0 中位），序号分列对齐基准 |
| **_pp（page_pitch）** | 每页源行间距（spotting y 差中位，px->pt） |
| **_pos_gscale** | 位置还原空白压缩比（top_vs + 段间隙） |
| **_pos_sscale** | 位置还原行高压缩比（strut） |
| **POS_FILL** | 填充目标=版心×POS_FILL（默认1.08，留余量防溢出） |
| **frags** | 多片段行（同行多 poly，如"标题"+"页码"），按源 x 绝对定位 |
| **figrow** | 书影图块行（is_figrow），按源 y 插入贴图 |
| **aside** | 边栏旁注（aside_text），竖排 shortstack 渲染 |
| **verify_geom** | 全局排版测试（pitch/占位/溢出/空白/页数） |
| **test_cases** | 功能断言测试（具体页 + 具体断言，防回归） |
| **tate** | 竖排模式（`tarticle.cls` 默认）；`\textwidth`=列高、`\textheight`=列区横向容量 |
| **列距** | 竖排相邻列的横向间距 = `\fontsize` 第二参数（baselineskip）；源侧 = 相邻列 x0 差中位（wz6 ≈47.6pt） |
| **界行线** | 版框内列间的 1pt 细竖线（源书 12 格 = 13 条等距栅格，列距 43.5pt） |
| **书眉 / 页码 / 边注** | 竖排的边缘小字：订口侧框外篇名 / 汉字数码页码 / 版心外注文（`*` 开头为题注），eso-pic `\put` 逐字绝对定位 |
| **derot** | OCR 返回「旋转坐标系」页（整页逆时针 90°）的还原，见 [vertical/06_derot.md](vertical/06_derot.md) |
| **verify_vert** | 竖排验证脚本（页数 1:1 / 逐页字符量 / 越界 / 页幅 / PASS-FAIL 退出码），对标横排 `verify_geom` |
| **VERT_\*** | 竖排管线环境变量族（12 个，全 `VERT_` 前缀 -> 与横排 env 命名空间零交集），契约见 [governance/PIPELINE_BEHAVIOR.md](governance/PIPELINE_BEHAVIOR.md) V2 |

## 总 Spec
- [00_system_architecture.md](00_system_architecture.md) - 系统总体架构（目标/类型/路由/共享基础/技术栈/目录结构/可扩展性）

## 分部 Spec

| 类型 | 目录 | 状态 | 说明 |
|---|---|---|---|
| 古籍 | [ancient/](ancient/) | ✅ 已实现 | CJK 墨高重叠、夹注本双规制、旁注竖排、校注标记 |
| 现代书籍 | [modern/](modern/) | ✅ 已实现 | 段落缩进、脚注、页眉页码、标题层级、目录页 |
| 竖排书 | [vertical/](vertical/) | ✅ 已实现 | 列流右起、tate 引擎链、书眉/页码/边注、版框线、页码序列、旋转页还原 |
| 论文 | [paper/](paper/) | 🔜 待建 | 公式、表格、图表标题、参考文献 |
| 合同 | [contract/](contract/) | 🔜 待建 | 条款编号、签章区域、固定格式 |
| 标书 | [bid/](bid/) | 🔜 待建 | 复杂表格、多层目录、附件 |

## 设计文档（docs/superpowers/）

历史设计 doc（深入分析，非规范）：
- [docs/superpowers/specs/2026-06-12-structural-heading-font-design.md](../docs/superpowers/specs/2026-06-12-structural-heading-font-design.md) - 标题检测与字体分配设计
- [docs/superpowers/plans/2026-06-12-structural-heading-font.md](../docs/superpowers/plans/2026-06-12-structural-heading-font.md) - 标题检测实施计划

**文档分工**：
- `spec/` = 设计规范（目标/输入/输出/约束/测试点，SDD）
- `docs/` = 项目总览/使用说明（PROJECT_SUMMARY 等）
- `docs/superpowers/` = 深入设计分析（历史设计 doc）

## 文档类型

| 类型 | 特征 | 管线 | 当前指标 |
|---|---|---|---|
| 古籍 | 墨高重叠、夹注、旁注 | `src/pipelines/build_classic.py` | 783页 pitch 59.1% 0溢出 |
| 现代书籍 | 段落、脚注、标题 | `src/pipelines/build_geom.py` | 222页 pitch 95% 0溢出 |
| 竖排书 | 列流右起、版框线、边注 | `src/pipelines/build_vert.py` | 231页 1:1 字符量97.2% 越界0 |

## 运行命令

```bash
# 古籍（wz2）
cd /opt/test && LAYJSON="data/wz2/wz2.pdf_by_PaddleOCR-VL-1.6.json" PAGE_FONT=1 PER_PAGE_PITCH=1 \
  python3 src/calibration/fit_positional_classic.py data/wz2/wz2_spotting_lines.json data/wz2/wz2_spotting_coords.json output/out.pdf source_pdf/wz2.pdf

# 现代书籍（wz1）
cd /opt/test && LAYJSON="data/wz1/wz1.pdf_by_PaddleOCR-VL-1.6 .json" PER_PAGE_PITCH=1 PAGENUM_GLOBAL_TABLE=data/wz1/wz1_full_pagenum.json \
  python3 src/calibration/fit_positional.py data/wz1/wz1_spotting_lines.json data/wz1/wz1_spotting_coords.json output/out.pdf source_pdf/wz1.pdf

# 竖排（wz6，繁体竖排书）
cd /opt/test && /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json \
  output/wz6/wz6_vert_full.pdf source_pdf/wz6.pdf

# 竖排验证（页数1:1 / 逐页字符量 / 越界 / PASS-FAIL 退出码）
/usr/bin/python3 src/test/verify_vert.py output/wz6/wz6_vert_full.pdf \
  data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json --src-pdf source_pdf/wz6.pdf

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
- taskP：wz7《金瓶梅詞話》300 页全量建排（无版框书第二本实战交付）—— 见 [docs/vert_wz7_300_report.md](../docs/vert_wz7_300_report.md) / [spec/vertical/09_calibration.md](vertical/09_calibration.md) §10。状态：implemented（2026-10-16）。
