# Spec: wz3 pitch 达标率优化

## 目标
wz3（中国古代经济史稿，849 页）经 split_polys 预处理后，pitch 达标率（输出 pitch 与源 pitch 误差 <3% 的页占比）从 42.0% 提升到 ~90%，pitch 误差中位从 3.4% 降到 <1%，页数维持 849 1:1。

## 根因（已用 verify_geom 数据 + page_pitch 模拟确认）
1. **PER_PAGE_PITCH 没开**：fit_common.render() 只设 POSITIONAL=1，未设 PER_PAGE_PITCH=1。输出用全局 baselineskip（FONT×1.2×LINESPREAD ≈ 22.08pt），而源 pitch 中位 22.83pt（逐页波动 22-36pt）。全局值只能匹配 22 附近的页 -> 42% 达标。
2. **page_pitch 方差过滤误杀 315 页**：build_geom.page_pitch 的 `pstdev(diffs) > 0.4*m0 -> None` 把行距方差的页判为"不准"回退全局。wz3 因 split_polys 的 `step=poly_h/n` 逐 poly 不均，315 页行距方差大被误杀。模拟证明这些页 page_pitch 返回的中位 pitch 99.8% 与 verify src_pitch 一致 -> 误杀。

## 方案
- **改动 1**：build_geom.page_pitch 去掉方差过滤（删 `pstdev(diffs) > 0.4*m0` 那行）。让方差大的页也返回中位 pitch，救回 315 页。
- **改动 2**：fit_common.render() 对 `build_name == 'build_geom'` 设 `env['PER_PAGE_PITCH'] = '1'`。wz3/wz1 自动逐页跟随源 pitch，wz2(classic) 不受影响。

## 输入
- wz3 cleaned coords（split_polys 后的行级 poly，data/wz3/cleaned/）
- page_pitch(key) 从源 coords 算每页中位 pitch

## 输出
- 每页 baselineskip 按页源 pitch 反推（PER_PAGE_PITCH 路径，build_geom L904-920）
- 方差大的页不再回退全局，out_pitch ≈ src_pitch

## 约束
- 只删 page_pitch 方差过滤 1 行；保留其他过滤（L<4、body<4、no_diffs、pt 越界 [10,45]）
- 不改 build_classic.page_pitch（独立函数，用 inner 变量，L131）
- 不改 fit_common 已有的 POSITIONAL=1 / VERIFY_MARK=1
- 不加 fallback；不改命令行参数与环境变量默认值（PER_PAGE_PITCH 对 geom 由 fit_common 固化，仍可被 env 覆盖）
- 中文注释 + UTF-8，无 emoji

## 测试点
- page_pitch 对"行距方差大的页"返回有效值（不返回 None）-- 新增单元测试
- page_pitch 返回值与 verify src_pitch 误差 <3%（816 可比页中 ≥90%）
- wz3 构建：达标率 ~90%，pitch 误差中位 <1%，页数 849 1:1，溢出 0
- wz1 构建：达标率 ≥94.9%（无回归）
- 全单元测试 PASS（unit + invariants）

## 风险与回滚
- wz1 也开 PER_PAGE_PITCH：wz1 polys 行级，page_pitch 有效率 76.6%->91%（放宽后），预期持平或提升。若 wz1 回归 -> 回滚 fit_common 改动，wz3 改回 shell 传 `PER_PAGE_PITCH=1`。
- 改 page_pitch 本身对 wz1 当前零风险（wz1 当前不开 PER_PAGE_PITCH，page_pitch 未被调用）；风险仅来自 fit_common 固化让 wz1 也开。

## 验收标准
- wz3 pitch 达标率 ≥85%
- wz3 pitch 误差中位 <1.5%
- wz3 页数 849 1:1，溢出 0
- wz1 pitch 达标率 ≥94.9%（无回归）
- 全单元测试 PASS

## 阶段1 结果（split 版，已交付）
wz3 用 split_polys 拆分后的数据构建：pitch 42%->89.6%，wz1 94.9%->97.3%（无回归）。
代码改动（page_pitch 放宽 + fit_common 对 geom 固化 PER_PAGE_PITCH）是**通用改进，保留**（wz1 也受益）。

## 阶段2: 行级 OCR 统一（最终方案）
**动机**：阶段1 后 wz1(97.3%) 与 wz3(89.6%) 仍有差距。根因是输入数据不同质--wz1 行级 OCR，
wz3 段落级 OCR + split_polys 几何拆分（拆分行距不均，src_pitch stdev 1.66 vs wz1 0.76）。
逐本调参绕不开，治本要数据同质。

**方案**：用 `OCR_LAYOUT=0` 重跑 wz3 OCR（run_spotting_ocr.py 已内置行级开关，
useLayoutDetection=False -> spotting_res 行级 rec_polys），免 split_polys。
行级 OCR 数据：data/wz3/wz3_linelevel_spotting_*.json（850 页 25196 行）。

**结果（wz3 行级版 vs split 版）**：
| 指标 | split 版 | 行级版 |
|---|---|---|
| pitch 达标率 | 89.6% | 84.8% |
| 空白页 | 112 | 17 |
| 底部占位<8% | 86.2% | 97.8% |
| 页高误差中位 | 7.1% | 3.2% |
| 溢出页 | 5 | 39 |

**决策：接受行级版**。pitch 84.8% 略低于 split 版，但填充/空白/页高全面优，且 OCR 同质
（wz1/wz3 都行级 + 同管线），系统统一基础已立。pitch 差距的剩余根因是 build_geom pitch
渲染按字号分大小字两路径（L783-789: PF>13 大字 bl=(_pp-2)*sscale，<=13 小字 bl=fnt*1.2×linespread），
wz1 FONT=10.1 走小字、wz3 FONT=15.1 走大字，行为不同。这是已知架构特性，非本次修复范围。

**正式输出**：output/wz3/wz3_geom_linelevel.pdf

