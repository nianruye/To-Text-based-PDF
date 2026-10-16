# taskP2：wz7 300 页收尾（把 verify_vert 做到 PASS）

> 项目：/opt/test。承接 taskP（300 页建排，越界 148→1、整页丢失 1→0、3 遗留已收）。**当前 verify_vert 仍 FAIL**，唯一原因是 taskP 报告 §4 里三条自认"未收"的项。本轮把它们收掉，让 300 页产物 **verify_vert PASS**。

## 收尾清单（每条修法已在 taskP 报告中写明）

| # | 项 | 现象 | 根因（taskP 已查明） | 修法 |
|---|---|---|---|---|
| ① | **p104 越界 5.93pt** | 竖排括号「﹁」(U+FE41) 在 y −5.9 | **该类码位的 PDF 字盒远大于 em 盒**（实测 bbox 高 26.8pt / 字号 9.3pt），而 `\put` 页内夹取按 em 盒留边（0.94F）→ 留边不足 | 夹取改用**该类码位的实测字盒比例**（对全部竖排形态码位测一次，或按码位表给比例）；改完 p104 那 1 条应为 0 |
| ② | **p35 缺 143 字**（549/692） | NF 页「行数 ≫ 槽数」且多行为短列（詩行/对话）→ 列带检不全 → 行无处配位 | 同 taskP §3.1（源页 1206 残余 34 字）同一根因 | 实现 **「无墨支撑行剔除」+ 列框兜底重排**（即：不参与配平的行改用 OCR 列框落位，而非静默丢弃）；同时**不得**把噪点/碎墨当正文 |
| ③ | **p291 缺 84 字**（207/291） | 附錄页 OCR 只给 13 行（源书 ~17 列），且 4 行被判为**边注**（小字）渲染 → 正文列少 | 主因判为 OCR 行覆盖不足（数据侧）；但"4 行被判边注"可能是**判据误判** | 先**复核边注判据**在该页是否误判（真误判则修，属代码问题）；若确为 OCR 覆盖不足，如实记录并评估可选补救（如对该页跑 layout 模式补 OCR / 用源图墨迹补列），**不要硬凑字数** |

## 验收（硬）

1. **wz7 300 页 `verify_vert` PASS**：越界 span **0**（容忍 0.5pt）、**非预期缺字页 0**（若 p291 经复核确属 OCR 覆盖不足，需在 `verify_vert` 的**预期差异机制**里按"数据原因 + 证据"登记，且**不得放宽判据**——说明为何该页属于"源侧数据缺失"而非产物缺陷）；整页丢失 0；矢量 0；页数 300=300
2. **wz6 零回归**：`verify_vert` PASS + `vert.tex` 与 taskP 基线逐字节相同
3. **测试全绿**（当前 316 + taskP 新增）+ 本轮新增测试
4. **报告更新**：`docs/vert_wz7_300_report.md` 的 §4 状态改为已收（或说明未收的充分理由），并补本轮改动锚点；`spec/vertical/09_calibration.md` / `spec/vertical/README.md` 锚点表按需更新；`AGENTS.md` #29 状态
5. 不动横排/四书；数据变更前备份 `*.bak_taskP2`；不 git reset；完成后 git add 不 commit（**注意不要 git add tmp_vert**，该目录已 .gitignore）

## 数据与命令

- 300 页：`data/wz7/wz7_spotting_{lines,coords}.json` + 页映射 `tmp_vert/wz7/wz7_sample300_map.json` + 样本 `tmp_vert/wz7/wz7_sample300.pdf`
- taskP 产物与脚本：`tmp_vert/taskP/`（`wz7_300_mid.pdf` 是本轮基线、`verify_final.log/json`、`cmp_*.png`、`survey300.py`、`metrics_nf.py`）
- 复现：`/usr/bin/python3 src/test/verify_vert.py tmp_vert/taskP/wz7_300_mid.pdf data/wz7/wz7_spotting_coords.json data/wz7/wz7_spotting_lines.json --src-pdf tmp_vert/wz7/wz7_sample300.pdf`

## 约束

- 不为过验证而放松判据（唯一允许的例外是上面 ③ 的"源侧数据缺失登记"，且须给证据）；无法达成的如实报告
- 只改 NF 分支/新口径，不损坏 wz6 成果
- 复杂 shell 写脚本文件；分步自测
