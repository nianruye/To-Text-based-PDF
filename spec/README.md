# Spec 文档索引

## Spec 状态账本

每条 spec 有四种状态：governance / planned / implemented / archived。PR 合并前必须更新状态（见 [AGENTS.md](../AGENTS.md) spec 对账规则）。

### governance（治理契约，跨管线公共约定）

| spec | 说明 |
|---|---|
| [governance/PIPELINE_BEHAVIOR.md](governance/PIPELINE_BEHAVIOR.md) | 管线行为契约：**横排**（契约 1-6 = argv / env / JSON / GMPG / DPI / 命名）+ **竖排**（「竖排管线（build_vert.py）」章节 = V1-V9 argv/env/JSON/GMPG-N.A./坐标页幅/产物/差异对照/验收/锚点/实测基线）+ 验收标准 + 实现锚点 + 兼容影响矩阵（含竖排行）+ CI 结论 |
| [governance/PUNCTUATION.md](governance/PUNCTUATION.md) | 标点符号用法与禁则（GB/T 15834—2011 可执行规则表，**v2**）：配对集合（17 类 + 2 半角变体 = 工具 19 条；含竖排形态与条款归属）/ 行首·行末禁则条款号 / **破折号（——，行首合法 §4.10.3.9/4.10.3.10）与连接号（§5.1.6）分离** / 破折号·省略号不跨行 / 行末全角标点压缩 / 竖排继承 / 多段引文（§4.8.3.5）合法性与「源图墨迹优先」两条边界；审计口径（**F1 源位置闸门**、**F3 carry 对偶延续验证**）+ 归因（A 源书自身/B 产物引入/C OCR 漏识/C_fixed/K/K_weak/K_invalid/O/D）+ 门禁建议。工具 `src/tools/punct_audit.py`（分类器 `tmp_vert/battle2/punct_classify.py` 随证据目录交付），报告 `docs/battle2_punct_audit.md`（v2） |
| [governance/PUNCT_EVAL.md](governance/PUNCT_EVAL.md) | 标点/结构识别能力评测契约（**v1.3**）：GB/T 16 类映射（12 in-scope / 4 out-of-scope）/ 阅读序重建（竖排右→左、横排上→下，家具剔除书无关）/ 文本锚点对齐（不做标点序列硬配对）/ 口径 A cell（provisional）+ 口径 B sequence（能力主指标）/ 阈值与跨书门禁（wz6/wz7/heldout）/ 基准集构成（20 页最小 + dash 专项扩展 2 页 = 22 页）/ 输出字段契约。实现 `src/tools/punct_bench.py`（`punct_eval.py` 入口），基准集 `src/test/bench/`（heldout 密封本地），报告 `docs/punct_eval_sequence.md` |
| [governance/CONTENT_EVAL.md](governance/CONTENT_EVAL.md) | 内容准确率评测契约（**v1.1**）：CER=(I+D+S)/N、两栏（with_punct / han_only）、N0 归一化口径、回归清单（64 确认缺字 + 54 ring 为 must-pass；118 t97 外推 + 4 样本为 diagnostic）、阈值与跨书门禁、dataset/gold 格式。实现 `src/tools/content_eval.py`，报告 `docs/content_eval_v1.md` |
| [governance/TYPOGRAPHY_EVAL.md](governance/TYPOGRAPHY_EVAL.md) | 排版评测契约（**implemented**）：三层判据（L1 强制 fail / L2 源书保真指标 / L3 GB/T 15834 §5 规范参考 warn）+ 决策 A（仅 render_introduced 升级 fail）+ 三类归因（source_inherent/render_introduced/non_body_page）+ 书型 gating + 合规率/违规分类/保真指标 + 与 verify_geom/PUNCTUATION/PUNCT_EVAL 边界；含 ghbq/wz2/wz4 实测基线（参考值） |

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
| [vertical/](vertical/) | 竖排书排版（engine / tate_layout / marginalia / frame_lines / pagenum_sequence / derot / 07 字模横向压缩+列内空隙 / 08 标点竖排形态 / 09 参数自标定 + 纸型无关化 / 10 西文行侧排+标题署名行+影印页整页贴图 / 15 竖排破折号整格矢量竖线 / 16 missing_char 缺字/标点串 1:1 插入（battle6–9） / 18 圈码普查与读数三层方案）；验证脚本 `src/test/verify_vert.py` |
| [vertical/16_missing_char_insert.md](vertical/16_missing_char_insert.md) | missing_char 缺字/标点串 1:1 插入（battle6–9）：数据契约（page/col/pos/ch/source/confidence/ratio/exp_len/text/api/crop/cell/feat/verdict/strip/shape/complete/note 等；`ch` 1–2 字符、增量 `len(ch)`）/ 重定位三步（上下文 → pos−shift → 跳过）/ 不插条件 / 源图证据 / 与 QSF·fix_split_brackets·dash·ring 的互斥去重 + **dash 边界**（`——` 走 missing_char，dash rule 画一条线）；battle7 58 汉字 → v37、battle8b 72 引号 → v38、battle9 6 普查汉字 + 3 标点串 → v40 |
| [vertical/18_ring_digit_census.md](vertical/18_ring_digit_census.md) | 圈码普查与读数三层方案（battle1/4/5 方法 implemented；参数化/一键化/读数去人工化 planned）：数据契约（fix JSON `class=ring` 的 page/col/source_x/y/number/situation/text/measure 等；situation 1 替换 / 2 追加；占位符 chr(0xE100+n) 不落库）/ 五步流程（检测→读数→序列→落库渲染→验证）/ 读数三层（模板兜底 → **PaddleOCR-VL 带上下文条带** → 序列+人工兜底；孤立裁片会读成 E/ETI 的教训）/ 序列（非降 + LNDS 锚点；页边界合法回退）/ 换书复用清单（阈值相对化、工具路径参数化、一键流程、读数去人工化）；§2 仅列 wz7 参考基线（184→352 / 34 / 21 / 16→2 / LOO 66% / p1720–1723 78/76/77/76），不作判据 |
| [docs/vert_wz7_layout3_report.md](../docs/vert_wz7_layout3_report.md) | 竖排 wz7 300 页版面元素报告（taskR 实现西文行/标题署名/影印页贴图 + taskR2 西文行紧凑化口径：拉丁 TFM 字体、破折号按 run 实测长、bp↔TeX pt 换算、逐片基线；含四项复核的实测对账与影印页普查分离度） |
| [docs/vert_dash_rule_report.md](../docs/vert_dash_rule_report.md) | 竖排破折号源图实测竖线报告（taskD / R2：相邻两 `—` = 同一墨块 -> 一条 rule，线长/线位/线心/线宽全实测 + FG 原点偏移修正；p57 1.255 step（源 1.259）/ Δ≤0.25pt / 空隙 0.00pt；p29 逐字节不变；wz6 默认零回归 + `all` 模式逐书实测 1.85-1.98；含 p57 产物侧间隙不可满足的反证与假破折号数据审计建议） |
| [docs/vert_taskE_census_report.md](../docs/vert_taskE_census_report.md) | 全书普查「OCR 漏识的占整格元素」（taskE：连通域 + y 聚簇 + 首/末格形状 + OCR 边字对账；全书 dash **1 处**（p1683 3.0×28.0）、ring **36 处/15 页**（p1682-1721 句末圈号）、other 0；反例 p1742 異體字表 / p29 西文页 / p100/p400/p1000 = 0；工具 `src/tools/census_missed_cells.py`，交付 JSON `docs/vert_taskE_census.json`；未改渲染端） |
| [docs/pipeline_audit.md](../docs/pipeline_audit.md) | 三管线+两校准代码审计（7 点） |
| [docs/coupling_analysis.md](../docs/coupling_analysis.md) | 暗中耦合分析（依赖图+状态地图+契约+风险因果链） |
| [docs/vert_governance_report.md](../docs/vert_governance_report.md) | 竖排纳入治理门禁报告（竖排契约逐条源码核对含行号 + CI 结论 + 实测基线 + 遗留 R1-R4） |
| [docs/vert_fix18_20_27_report.md](../docs/vert_fix18_20_27_report.md) | 竖排收尾修复报告（#18 退出码分级 + #20 临时目录按产物名分离 + #27 数字实测核对；含验收实测与渲染零变化对照） |
| [docs/vert_width_gap_report.md](../docs/vert_width_gap_report.md) | 竖排字宽压缩收尾报告（taskJ2：`\scalebox` btrans/etrans 数值逆矩阵泄漏根因与 q/cm/Q 精确还原修法 + 列内空隙 DP 检出全书落地 + 独立复核口径失效分析） |
| [docs/vert_calib_report.md](../docs/vert_calib_report.md) | 竖排参数自标定报告（taskM：wz6 硬编码常数 -> 建排前自动标定 + 对账表 + 产物不回退证据 + **换书剩余人工依赖清单**） |
| [docs/battle1_horizontal.md](../docs/battle1_horizontal.md) | 横排 local-bug 清零报告（battle1：#1-#9 逐项实测核销 —— #1/#2/#5/#6/#7/#8 在 HEAD `bed0d25` 已修/已安全，#3/#4/#9 本轮收口；516->557 测试（本任务 +41；全量 562）；四书 geom + wz2 classic 改动前后重跑：逐页文本/行 bbox 0 差异、verify_geom JSON 逐字节相同、hard split 0 / missing 0） |
| [docs/battle1_vertical_ring.md](../docs/battle1_vertical_ring.md) | 竖排两位数圈码判据重标定报告（battle1 P0-a：hole 必要条件证伪 -> 主块尺寸窗+四边墨闸门；184->352 处 / 段外 0 误报；p1704/1705/1706 圈码 49/50/51/52 渲染 + 文本层 ㊾/㊿ 码位；wz7 verify_vert PASS、wz6 md5 逐字节相同、562 测试） |
| [docs/battle2_punct_audit.md](../docs/battle2_punct_audit.md) | 双管线标点禁则/配对审计报告（battle2：GB/T 15834—2011 规则表 + `punct_audit.py`；横排四书重跑 + 竖排 wz7 v30；A/B/C 三类归因 + p620 缺 」的 OCR 漏识定位 + 门禁建议） |
| [docs/battle4_ring_digits.md](../docs/battle4_ring_digits.md) | battle4 圈内数字识别 + 年表序号非降校验报告（t18/t19：352 处圈码识别框架、27 处非降违反清单；7 处高置信落库 + t19 4 处区间唯一解；v33/v34 PASS、wz6 零回归、pytest 590） |
| [docs/battle5_ring_hires.md](../docs/battle5_ring_hires.md) | battle5 圈码高清全量判定报告（t21：60 页 4700×7225 / align 6.65 px/pt；367 条判定、21 处读图改判、余 2 处页边界保留；v35 PASS 931,040、wz6 零回归、pytest 590） |
| [docs/battle5_acceptance.md](../docs/battle5_acceptance.md) | battle5 独立验收报告（t22：对齐独立复测、v35 md5/verify、21 处改判误判 0、2 处页边界 78/76/77/76 清晰保留；wz6/pytest；R1–R5 低级别文档问题） |
| [docs/battle6_missing_chars.md](../docs/battle6_missing_chars.md) | 竖排真实缺字回收报告（battle6：异体字归一化 + 检测加严 F1–F5 + 241 列 API 抽样；列框外整字漏识 ≈1、列内真插入 12（汉字 3）/ 抽样外推 300-400；下一阶段全量 API 计划） |
| [docs/battle7_missing_chars.md](../docs/battle7_missing_chars.md) | battle7 58 处汉字缺字落库报告（t27 hanzi_list → t28：57 新增 + 1 去重（p634 籤），missing_char 12→69；v37 重建 + verify PASS（931,106 字 / +57）；wz6 零回归、pytest 590） |
| [docs/battle8_quotes.md](../docs/battle8_quotes.md) | battle8b 引号类漏识落库报告（t34：96 条 punct_list 全查 → 72 条落库（70 」+2 「；43 条 —— 按角形重判）；v38 重建 + verify PASS（931,178 字 / +72）；无双引号、QSF 925 条决策不变、wz6 零回归） |
| [docs/battle9_census.md](../docs/battle9_census.md) | battle9 非候选列全书普查报告（t37：23,775 列 / 2,972 页 / 100 批；same 18,739 / other 4,934 / nonchar 45 / true_insert 57；16 条完整汉字候选，逐条 page/col/cell/ch/crop；`api_battle9.json` md5 `77327304…`） |
| [docs/battle9_fix.md](../docs/battle9_fix.md) | battle9c 破折号 + 引号落库报告（t40：p57 `——` 走 missing_char 由 dash rule 画一条线（80.0pt/1.255 step）；p186 `」。`、p147 `」，`；p1330 噪点不落；v39 verify PASS 931,184 / +6） |
| [docs/battle9d_census_fix.md](../docs/battle9d_census_fix.md) | battle9d 16 条普查汉字复核落库报告（t41：6 落（p68 尚/p932 人/p1219 纖/p1419 慌/p1678 步/p1703 四）、10 不落（重复/异体/源无/圆圈/泓/OCR 誤读）；v40 verify PASS 931,190 / +12 vs v38） |
| [docs/battle9e_acceptance.md](../docs/battle9e_acceptance.md) | battle9 独立验收报告（t42：v39/v40 复跑、p57 源墨四道比值、16 条自裁、wz6/pytest；内容等价 R1、p57 线宽 R2、p1678 抄/投 R3） |
| [docs/battle9e_review.md](../docs/battle9e_review.md) | battle9 终审报告（t43：verdict pass；独立复跑 build40/verify/wz6/pytest，v39 3 条 + v40 16 条逐条核对，字节绑定/token；R1–R4 残留，R4 spec 16 已在 t44 更新） |
| [docs/pipeline_architecture.html](../docs/pipeline_architecture.html) | 架构图（深色 SVG） |
| [src/test/snapshots/CURRENT_BEHAVIOR_SPEC.md](../src/test/snapshots/CURRENT_BEHAVIOR_SPEC.md) | 回归快照现状 spec（wz1/优化前/wz2 排版现状） |
| [src/test/unit/PURE_FUNC_SPEC.md](../src/test/unit/PURE_FUNC_SPEC.md) | 纯函数行为 spec（14 函数契约；battle1 更正 #1/#2 旧契约、补 is_heading_by_md、刷新行号锚点） |
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

### 判据 / 数据分离（2026-11-06 治理规则）

spec 是**换书也要能用**的契约；判定条件与本书实测数据必须分离：

1. **判定条件不得使用绝对数字**（如 `14.5–19.5pt`、`0.040×F`、固定 px/页数）。必须写成相对量
   （`×本页字步进` / `×页幅` / 无量纲比值），或注明「由源图/字体自标定」；确属实现默认值的，
   在判据处标注「参数默认（参考值，非判据），换书需参数化」。
2. **本书实测数据只能进「参考基线（本书实测）」小节**（条目计数、耗时、对账百分比、具体 pt 线宽/位置、
   测试数等），每条标注 **书目 + 日期 + 来源报告**；正文判据只引用小节，不复制数字。
3. **确属契约的绝对数字可保留**（如 `ch` 长度 1–2、`source` 枚举、字段名、坐标空间），但必须注明「契约值」。
4. 新增/修改 spec 时按此规则写；发现旧文档混入时，按「原位置 → 新位置」清单归位，**不改判据语义**。

**本轮归位清单（2026-11-06；只移动/加注，不改判据语义）**：

| spec | 原位置 | 新位置 | 内容（保留） |
|---|---|---|---|
| 16 | §16.1 数据总量/构成；§16.2 `ch` 条数、字段族条数、t24 条数；§16.4.1 p57/46/43/3；§16.5 抽样数/倍率；§16.6 QSF 925/696/229、ring 367/150、dash 46/43/3、census/punct 条数；§16.7 +57/+72/+12、925、wz6 md5/231 | **§16.10 参考基线** | 150=69+72+6+3、147 单+3 双、QSF 925、+57/+72/+12、931,190、46→43、p57/p186/p147、p1330/p1560、抽样 24/12/16、wz6 基线 |
| 16 | §16.2 side/confidence 当前值；§16.3 0.6/1000/3 条；§16.5 8×/600dpi/≥10；§16.2 0.55；§16.2 去重 ±2pt | **§16.10.1 参数默认（参考值，非判据）** | 列框容差 0.6pt、上下文 8+8、小书 1000 页、完整字块 0.55×步进、裁片 8×/600dpi、去重 ±2pt |
| 16 | §16.6 `fix_split_brackets` 的 p1241/p1399 例 | **§16.10** | 重定位实测（依依不/茶筍→依不依/筍茶） |
| 09 | §2 耗时 2.3s/0.8s/16.9→17.7；§6 全部实测（12/0.863/0.658/…/68412/1.009/0.960/28/277） | **§13.1 taskM/wz6** | 标定耗时、对账表、verify/覆盖率、测试计数 |
| 09 | §8.2 21 项 0.0000%；§8.3 wz6 内框缘 567.8/45.5；§8.4 线簇 1.50/3.50-4.50→2.45/6.75、206 条 0.833/1.068；§8.7 100 页预检/16 页降级原因；§8.8 零回归/21 项/296 测试 | **§13.2 taskN/wz6+wz7** | 21 项等价性、页边带、线宽自标定、wz7 预检、零回归、测试 |
| 09 | §9.2 混纸型页幅/页宽比例 92.4%/87%；§9.3 p406 1.203/−184/1.12、p407 90°；§9.5 24 页验收 | **§13.3 taskO/wz7** | 922×1437 / 892×1323 / 705×1084、92.4%/87%、p406/p407 仿射例、98.8%/0.01%/列数 17 vs 16/34.1 vs 33.7/316 测试 |
| 09 | §10 验收 300 页 | **§13.4 taskP/wz7** | 98.7%/丢失 0/越界 1/页幅 0.01% |
| 09 | §11 文本框比例、列带证据、伪版心夹回 | **§13.5 taskP2/wz7** | 1.734F/1.006F/2.740F/4.9pt、4pt/3 条/3pt、p182 −138.8/8pt、705pt 页 214pt 越界 |
| 09 | §12.1–12.5 逆映射/梳状/窗外扩/重试例证；§12.6 验收 | **§13.6 taskQ/wz7** | 224/250、193/146、2/250→221/250、p30 109/89.5、245/52/348/39、p254 14.6/95、p130 84、p214 62/52/22、p24 82/103/123、300 页 99.5%/336 测试 |
| 15 | §1 p57 127.44pt/80.2pt/1.26 格；§5 p57 5.37/5.38；§7 验收全表 | **§9.1/§9.2 参考基线** | p57 线长/线位/线宽/空隙/邻字间隙、wz6/wz7/p29 回归、506 测试 |
| 15 | §3 1.26；§4 0.040；§6 env 默认 0.040/1.26；§8 遗留证据 | **§9.3 参数默认（参考值，非判据）/§9.4 证据** | 0.040×F、1.26、线宽 5.25/2.78、间隙 2.093/1.479 step、88/87/1019 条 |

> 扫描范围：`spec/vertical/*.md`。除 16/09/15 外，发现以下**候选**（均在 in-scope 之外，本轮未改，避免扩大改动面）：
> 02_tate_layout §1.9 的 47.6pt 例、03_marginalia 的 4-40px/5-90px、04_frame_lines 的 0.30/36pt/12 列/799pt、
> 06_derot 的 300px、14_quote_shape_fix 的 185 灰度等；它们多为**实现默认参数/实测例**，非本书数据清单。
> 07/10/11/12/13 的实测数字主要位于「验收/实测/报告引用」小节。以上列入后续 backlog，按同规则逐文迁移。

- taskP：wz7《金瓶梅詞話》300 页全量建排（无版框书第二本实战交付）—— 见 [docs/vert_wz7_300_report.md](../docs/vert_wz7_300_report.md) / [spec/vertical/09_calibration.md](vertical/09_calibration.md) §10。状态：implemented（2026-10-16）。
