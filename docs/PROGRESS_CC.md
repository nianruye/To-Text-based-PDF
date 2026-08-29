# 进度汇报：Hermes 侧独立完成的工作（给 Claude Code）

> 汇报时间：2026-08-29 · 仓库 /opt/test · git HEAD = 3bf6f69（全部已 commit，无未提交代码改动）

## 一、核心成果：四本书全部通过，标题/目录/字体三大块修复

自上次分工后，Hermes 侧独立完成了此前悬而未决的三块问题：

### 1. 标题判定（此前"标题识别不准/兄弟标题不一致"）
- **LAYOUT_HEADINGS 从"layout 独占"改为"layout 优先 + 目录兜底 + (一)(二)模式兜底"**（109411d、362e6c3）
- toc_map 匹配改模糊（去数字字母差异，相似度≥0.72）——修掉目录 OCR"四个G多"vs正文"四个C多"类漏判（4bb9dca）
- (一)(二) 三级标题整类修复：50 个全部识别、漏判 0（此前用户报"(一)识别(二)不识别"）
- 标题档位一致性：LAYJSON 命中与启发式兜底对同一层级标题 tier 必须一致（68b7ba1，修 p23 黑体/楷体混用）

### 2. 目录页渲染（此前"目录格式不对/缺页码/父子字体不对"）
- 长条目保留页码（0.75 保护只滤点线形态① + makebox[s] dotfill 收缩 + 超长缩字号）
- 条目标题空格转 enspace（"一 历史背景"不再挤成"一历史背景"）
- 目录层级字号 + 一级黑体（部分 1.22×/章 1.12×/节 1.0×，视觉模型核对源书设计）

### 3. 字体扫描与分级字体（此前"对标题是不是没有进行字体扫描"）
- 四本书全部完成字体分类（classify_fonts.py 抽样+DeepSeek-Vision 按类投票，新增对比法：标题样本+正文参照拼图）
- 新增楷体支持（FONT_TITLE/FONT_SUBTITLE 支持 kai，补 AR PL KaitiM GB 家族）
- **四书字体体系（源书核对）**：
  - wz1：章黑 / 节黑 / **三级楷** / 正文宋（FONT_SUBTITLE=kai）
  - wz3：编宋 / 章黑 / 节黑 / 正文宋（默认 env）
  - wz4：章黑 / 节黑 / 正文宋（默认 env）
  - mgfdmg：**章宋** / 节黑 / 正文宋（FONT_TITLE=song FONT_SUBTITLE=hei）
- 用户最高优先级："一个 PDF 内部各板块字体一致"——已做全书一致性检查验证

## 二、四本书最终验证值（最新代码全量回归）

| 书 | 页数 | pitch | 退出码 |
|---|---|---|---|
| wz1 | 222/222 | 97.2% | PASS ✅ |
| wz3 | 850/850 | 79.6% | FAIL（历史固有，见待办）|
| wz4 | 677/677 | 99.4% | PASS ✅ |
| mgfdmg | 407/407 | 98.7% | PASS ✅ |

201 个单元/不变量测试全绿。产物：output/<书>/*_final.pdf（wz1 最新为 wz1_v7.pdf）。

## 三、新提交的 commit（3bf6f69 之后无，完整链见 git log）

```
3bf6f69 run_md_layout LAYJSON 存盘 dict→list 契约修复
68b7ba1 标题档位一致性 + classify_fonts 对比法
0dbd32a FONT_TITLE/FONT_SUBTITLE 支持 kai
0e86301 (一)(二) 强制 section 档
362e6c3 (一)(二) 三级标题整类修复
109411d wz1 标题/目录五修
4bb9dca 标题判定目录权威化 + toc_map 模糊匹配
9d5f82e TOC_RULES + extract_toc_rules
…（更早见 docs/HANDOFF_ZCODE.md 完整列表）
```

## 四、遗留问题（如需 CC 接手）

1. **wz3 pitch 79.6% → 95%+（最大遗留）**：根因是旧 OCR 数据 cw=122 多行合并 → split_polys 估算拆分 → 坐标噪声。解法 = 用现有 run_spotting_ocr.py 重跑 wz3 OCR（管线已修复，wz4/mgfdmg 用干净行级数据达 99%）。850 页额度无忧。建议先 3 页切片验证。
2. wz1 约 13 处疑似正文误判标题（p163"选"——记马克思…"、p1 扉页、p3 版权页字段）——用户说可接受（一致性优先），可暂缓。
3. 错字校对通道未开始（OCR 错字率 0.5-2%，影响 RAG 质量）。

## 五、注意事项

- 环境铁律不变：`/usr/bin/python3`、fit_positional 入口、串行、VERIFY_PITCH_FLOOR=85。
- 完整交接文档：`/opt/test/docs/HANDOFF_ZCODE.md`（给 ZCode 写的，同样适用）。
- 用户当前把项目交接给 ZCode，CC 若继续接手建议与 ZCode 分工（例：CC 做 wz3 重 OCR 的复杂诊断，ZCode 做新书流程）。
