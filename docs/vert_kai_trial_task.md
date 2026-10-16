# taskL：楷体候选试验（单页，不动主产物）

> 项目：/opt/test。**用户判定源书是楷体**（用户看原书，权威——项目原则：视觉模型判楷/宋不可靠，以用户判断为准）。现用字体 Noto Serif CJK TC（宋/明体系）需评估换为楷体的可行性。**本轮只做试验，不全书重跑、不改主产物。**

## 上轮识别（taskK font_id.py）为何判成宋体——三个失效点

1. **IoU 被字面宽度主导**：报告自述"源书是长体窄字，比任何候选窄 1.48 倍"→ 宋体字面窄而"胜出"，并非因为像；
2. **楷体候选只有一个**（AR PL KaitiM GB/Big5），**未试 Windows 楷体（simkai.ttf）与仿宋（simfang.ttf）**——本机就有：`/mnt/c/Windows/Fonts/simkai.ttf`、`/mnt/c/Windows/Fonts/simfang.ttf`；
3. 扫描模糊使源侧墨量膨胀，楷体的"笔锋/细笔画"特征被糊掉。

## 任务：候选字体并排试验（限 p10 正文 + p4 注释 + p3 标题/日期区）

对下列候选，各渲染**同页同内容**的试验 PDF（**竖排管线现编排不变，只换字体**），并与源书同页做**高倍并排对照图**：

| # | 候选 | 路径/说明 |
|---|---|---|
| a | Noto Serif CJK TC（现用·对照） | 现状 |
| b | **simkai（Windows 楷体 KaiTi）** | `/mnt/c/Windows/Fonts/simkai.ttf`——**首次试** |
| c | **AR PL KaitiM Big5（繁体楷）** | `/usr/share/fonts/truetype/arphic-bkai00mp/bkai00mp.ttf` |
| d | **simfang（Windows 仿宋）** | `/mnt/c/Windows/Fonts/simfang.ttf`——**首次试**（老书常用仿宋）|
| e | （可选，若可行）b 或 c 的**墨迹加粗**版本 | 源书墨迹比 AR PL 楷厚（taskK 实测墨量比 0.63）——加粗以逼近源书墨量；**必须用精确方式**（taskJ2 的 `\special{pdf:literal ... q K 0 0 1 0 0 cm}...Q` 一类），**禁止 scalebox 式数值逆** |

### 每候选须报告

1. **并排对照图**（源书 / 候选，同页同区高倍，≥2 页：p10 正文 + p4 注释）
2. **覆盖率影响**：该字体渲染后墨迹覆盖率 vs 源书（用你 taskJ/taskK 的口径，注明脚本与阈值）——**换字体会改变字面宽度，必须量化**
3. **繁体字覆盖检查**：源书用字（可从 `data/wz6/wz6_spotting_lines.json` 取全集）在该字体下**缺字清单**（simkai/simfang 为简体取向，需重点查）
4. **竖排兼容**：竖排码位（︵︶﹁﹂等）在该字体下是否可渲染（缺则说明）；标点挤格/字号保护是否仍工作

## 验收

1. 并排对照图落盘 `tmp_vert/taskL/img/`（**用户将据此选定字体**）
2. `docs/vert_kai_trial_report.md`：每候选的覆盖率数字 / 缺字清单 / 竖排兼容 / 观感描述 + **推荐结论**（哪个最像源书，给依据）
3. **主产物不动**（`output/wz6/wz6_vert_full.pdf` 保持现状）；试验 PDF 放 `tmp_vert/taskL/`
4. 既有功能不回归（跑一次 verify_vert 确认主产物仍 PASS）+ 测试全绿

## 约束

- **不全书重跑**（单页试验）；不动既有功能；数据不变更（只读）
- 不 git reset；完成后 git add 不 commit（若新增脚本/报告）
- 复杂 shell 写脚本文件；分步自测
- **不要再用 IoU 单独下结论**（已知被字面宽度主导）——本轮以**并排目视对照 + 覆盖率/缺字数据**为主，结论留给用户定夺
- 无法达成时如实报告给选项
