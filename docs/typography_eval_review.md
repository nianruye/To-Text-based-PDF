# 排版评测契约 + verify_typography 终审（t241）

> 审查人：质量审查员（第三方，独立复跑/复算）　日期：2026-11-11 20:53–21:40
> 对象：t238 `spec/governance/TYPOGRAPHY_EVAL.md` + t239 `src/test/verify_typography.py`（含 t242/t246 修复、t247 round-3 验收）
> 依据：spec §0–§10、`docs/typography_eval_acceptance.md`、`spec/README.md`、`docs/scan2pdf_review.md`
> **结论：needs_revision（FAIL）** —— 工具**存在系统性放水与误伤**：① `render_introduced` 实际几乎不存在（真违规降为 unknown/warn）；② `non_body_page` 单关键词整页豁免（正文页可被吞）；③ L1 五条强制项只覆盖约两条（M3/M4 完全缺失）；④ p5 CIP 特判与 spec §4.1 相反（红侧证据失效）；⑤ spec 与实现规则 ID/名称大面积不一致、spec 状态/锚点仍 planned。边界上 PUNCTUATION/PUNCT_EVAL 未被误改（干净）。

## 0. 复跑与独立证据

### 0.1 红/绿产品（复跑）

| 产品 | 结果 |
|---|---|
| `output/ghbq_full/acc_title_toc.pdf`（旧红侧） | exit=1、violations=45、hard=39、render=2、waived=7、non_body=1；p5 `gb51_dash_break`+`gb51_dot_line_start` render；p11/p12 TOC overlap/字体/续行/页码；p97 34 hard 越界 |
| `output/ghbq_full/ghbq_title_toc2.pdf` | exit=1、violations=40、hard=36、render=2、waived=7 |
| `output/ghbq_full/ghbq_title_toc3.pdf` / `ghbq_title_toc.pdf` | exit=1、violations=6、hard=2（p12 overlap）、render=2（p5） |
| `output/ghbq_full/ghbq_corrected.pdf` | exit=1、violations=43、hard=39（p11 overlap + p97 越界）、render=2、waived=7 |
| wz4 `tmp_vert/scan2pdf/wz4_calib.pdf` | WARN、violations=277、hard=0、**render=0**、waived=8、compliance=1.0 |
| wz1 `output/wz1/wz1_final.pdf` | WARN、violations=46、hard=0、render=0、waived=14 |
| wz2 `/tmp/t238_wz2_full.pdf` | WARN（默认 horizontal）、violations=59、waived=23、non_body=1；按 ancient 应为统计 |

### 0.2 手工复算（3 条）

1. **p12 overlap gap = −8.14**（`acc_title_toc.pdf`）：手工取 span `1.` bbox x1=106.9、标题 span x0=98.8 → gap = 98.8−106.9 = **−8.14**，与工具一致（2 处）。p11/p12 的 −8.32/−11.65 在旧产品同法可复算。
2. **p97 越界**：p97 span `邓小平同志在` bbox x0=**607.6** > 页宽 600.75；`“坚持四项基本原则”` x0=731.6；工具 34 条 `hard_text_out_of_page` 与实测一致（真实横向越界，非误报）。
3. **p5 源行核对**：`data/ghbq/_ocr_ghbq/ghbq_spotting_lines.json` key `4` 第 3 行为 `—北京:社会科学文献出版社, 2012.7` —— **源书同页同行首就是单个 `—`**；按 spec §4.1 应归 `source_inherent`（waived），工具却判 `render_introduced`（见 F4）。

### 0.3 放水/误伤探针（reviewer 构造 /tmp 合成 PDF，不动数据）

| 探针 | 结果 | 说明 |
|---|---|---|
| A 正文页含 `md5` + 行首 `。` 违规 | `non_body=1`、`body_lines=0`、verdict PASS | **正文页被整页吞掉**（单关键词即触发；spec §4.3 要求 ≥3 特征） |
| A2 同文去掉 `md5` | 2 行参与、违规报出（WARN） | 对照证明 A 是豁免逻辑而非提取问题 |
| B 非 TOC 页两 span 重叠（标题+重叠字） | 无 `hard_span_overlap`（仅一条 GB warn） | M1 只对 TOC 数字 span 生效（源码 `_span_violations` 仅 `_is_toc` 调用） |
| C 直接调用 `_attribute_text(0,'ABCDEFGHIJK（',{'0':['ABCDEFGHIJK']},'')` | 返回 `('source_inherent','ABCDEFGHIJK')` | 源行**没有** `（`，仅前 8 字相同即被豁免 → 归因过宽（spec §4.1 要求同位置字符证据） |

## 1. findings

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F1** | **high** | **`render_introduced` 判定路径几乎不存在（放水）**：`_attribute_text` 只做 exact/前 8 字前缀匹配→`source_inherent`，否则 `unknown`；除 CIP 单破折号特判外无任何路径产出 `render_introduced`。实测 wz4 6 条 `。` 行首（spec §8 基线标为 render_introduced）当前全为 **unknown/warn**（by_rule `gb51_dot_line_start:6`、by_attr `unknown:6`），不升级 fail | 按 spec §4.1/§4.2 实现同位置字符/坐标核对（源行存在但字符不同 → 需 coords/源图墨迹证据；无证据 → unknown），前缀匹配仅作中置信且需同位置违规；只有 render_introduced 才 fail。补对应单测（wz4 6 条应为 fail 或明确降级理由） |
| **F2** | **high** | **`non_body_page` 识别过宽**：实现 `any(k in page_text for k in META_KEYS)` —— **单个** `md5`/`filesize`/`total_pages`/`document generated` 即整页豁免 L2/L3；spec §4.3 要求「≥3 特征串同页」或 PAGE_IMAGE/40% 图块+<5 行。探针 A：正文页含 `md5` → body_lines=0、PASS | 按 spec 实现三特征计数（或结构化元数据页签名）；正文页提及 md5/total_pages 不得整页豁免；加单测锁定「1 特征 → 不豁免」 |
| **F3** | **high** | **L1 强制层未按 spec 落地**：M1 仅 TOC 序号 span 负 gap（普通 span 重叠不判）；M2 仅「整段完全越出页幅」（spec 为 bbox 越出可打印区，部分越界不判）；**M3 页码错位、M4 字符丢失/重复完全缺失**（grep 无 `hard_pagenum`/`hard_char_loss`；仅 L2 `toc_pagenum_align`） | 补 M1 通用 span 重叠（面积比 0.02×min）、M2 部分越界（可打印区+容差）、M3 页码序列/页脚带、M4 页/行字符量对 OCR 行；每条配单测 |
| **F4** | **medium** | **p5 CIP 单破折号特判与 spec §4.1 相反（误伤 + 红侧证据失效）**：源行 `—北京:…` 源书同位置同字符，应 `source_inherent`；实现强制 `render_introduced`（代码注释写明「t239 红侧 p5」），单测 `test_attribution_source_inherent_and_render` 固化该行为 | 删除 CIP 特判（按 spec 归 source_inherent）；红侧改用真实 render_introduced 案例（如 wz4 `。`6 若核实源无行首） |
| **F5** | **medium** | **spec §2.1 与实现规则 ID/名称不一致**：spec 5.1.2=`gb51_dot_cell`/5.1.3=`gb51_close_line_start`/5.1.4=`gb51_dash_ellipsis_break`/5.1.5=`gb51_pair_break`/5.1.7=`gb51_open_line_end`/5.1.9=`gb51_punct_hang`；实现分别为 `question_exclaim_cell`/`quote_bracket_break`/`dash_break`/`ellipsis_break`/`interpunct_cell`/`separator_cell`（5.1.10 名称亦不同） | 二选一同步：实现按 spec 表改名/重排，或 spec 按实现重排并说明「编号以实现为准」；报告 `by_rule` 必须能与 spec 对应 |
| **F6** | **medium** | **spec 生命周期/锚点/基线过时**：header `状态：planned`、§10 `实现锚点（planned）`、建议工具路径 `src/tools/typography_eval.py`（实际 `src/test/verify_typography.py`）；README 已 implemented；§8 基线为旧口径（wz4 6 render vs 当前 unknown；当前工具/产品数字与表不符），未冻结版本 | 更新 header/§10 路径与状态；以工具 sha+产品 md5 冻结 v1 基线（或标 archived/参考） |
| **F7** | **low** | **spec 内部矛盾**：§3.1「L1 fail → 门禁退出码非 0」vs §7「typography hard 仅镜像，verify 唯一 fail 源」；实现工具 exit=1（L1 hard）但 scan2pdf/quality_gate 不改 gate（符合 §7） | spec 明确「工具自身 exit 与门禁 verdict 分离」；gate 侧保持 verify 唯一 fail |
| **F8** | **low** | GB52 违规 attribution=`vertical_stat`（spec §4 仅定义 source_inherent/render_introduced/non_body_page/unknown）；且 compliance=1.0 可与 277 条 warn 并存（wz4），指标易误读 | 统一 attribution 取值（或 spec 增列 statistic）；报告增加 warn_rate/unknown_rate |
| **F9** | **note** | 边界：PUNCTUATION/PUNCT_EVAL 文件未被改动（git status 干净）✓；但 t242 为让 p5 变绿改了 `build_geom.py`（CIP 单 `—` 行首去除），与 spec §0.2「只定义评测、不改渲染」边界需在任务/记录中显式分离 | 记录该渲染改动归属与回退开关；评测任务不改渲染 |
| **F10** | **note** | p97 34 条硬越界为既有产品缺陷；t242 决定 L1 暂不升级 gate（captain 裁定） | 单列跟踪 p97 修复；工具正确抓到，无需改判据 |

## 2. 契约核对汇总

- `spec/README.md`：TYPOGRAPHY_EVAL 已登记 **implemented**（账本 OK），但 spec 文件 header 仍 planned（F6）。
- 15 条机检 + 2 条豁免（GB51 9 + GB52 6 + EXEMPT 2）：**数量**与 t246 声明一致；**语义/编号**与 spec §2.1 不一致（F5）。
- 决策 A：L1 hard / L2 warn / L3 仅 render fail / source waived / non_body 整页豁免 / unknown 不升级 —— 分支逻辑存在，但 render 路径缺失（F1）、non_body 过宽（F2）、L1 不完整（F3）。
- 误伤：p5 CIP 特判（F4）、前缀 8 字豁免（C）；wz4/wz1 输出大量 unknown/L2 warn（277/46），compliance 1.0 掩盖告警（F8）。
- 边界：PUNCTUATION/PUNCT_EVAL 未改 ✓；pitch/overflow/页数仍由 verify 唯一 fail（gate 未变）✓。
- 测试：18 passed（t247），但单测固化了 CIP 特判（F4）且未覆盖 M3/M4/通用 M1/单关键词 non_body（F1–F3 缺口）。

## 3. 结论

**t241 终审：needs_revision（FAIL）**。

- 可交付部分：红侧 TOC 三项/越界/p5 能抓到；绿侧 p10 waived、p104 非正文；wz2 ancient 不 fail；gate 零回归；边界未误改 PUNCTUATION/PUNCT_EVAL。
- **不可交付**：F1（render_introduced 实际缺失 → 真违规不报）、F2（non_body 单关键词吞正文页，探针复现）、F3（L1 M3/M4 缺失、M1/M2 覆盖不足）、F4（CIP 特判与 spec 相反，红侧证据失效）为 must-fix；F5/F6 需 spec 同步；F7/F8 澄清口径。
- 复现命令/证据：见 §0；字节能绑定见下。

## 4. 字节绑定

| 文件 | sha256 |
|---|---|
| `src/test/verify_typography.py` | `76dc3a7377966bccde214f0cf02a8c8d4735191960c2e2418cf68323df5adf2c` |
| `spec/governance/TYPOGRAPHY_EVAL.md` | `93de8c1547af6f89ed9ba9cc20537a16b63e9837646a0798fc9ef46a7e3f35b9` |
| `spec/README.md` | `f23465329f2ada6c7e3907a79916bbcdf0a6ef20deb651e1f3b67339088e6db2` |
| HEAD | `fc86ce8`（未 commit） |

## 5. 补充发现（测试复核，2026-11-11 21:40）

- `pytest src/test/unit/test_verify_typography.py -q` 实测 **1 failed / 17 passed**（t247 声称 18 passed）。
- 失败项 `test_real_red_ghbq_title_toc` 读取 **可变的 `output/ghbq_full/ghbq_title_toc.pdf`**（当前已重建为仅 6 条违规/2 hard），却断言旧红侧 gap −8.32/−11.65、p5 render、p10 waived 等；`test_real_wz4_no_fail` 亦读 `output/wz4/wz4_s4.pdf`。
- 结论：**真实产品 fixture 非 hermetic**，测试全绿与否取决于 output/ 重建状态（易漂移）；应把红/绿样例 PDF+lines 冻结到 `src/test/fixtures/`（或合成 fixture），不得依赖 untracked output 产物。

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F11** | medium | 真实产品单测依赖可变 output/ 产物（`ghbq_title_toc.pdf`/`wz4_s4.pdf`），当前 **1 failed/17 passed**，与 t247「18 passed」不符；测试非 hermetic | 冻结 fixtures 到仓库内（小页样本）或合成 fixture；`skip` 条件不能掩盖「有文件但内容已变」 |

---

## 6. round-2 终审（t251，t250 修复 F1/F2/F4/F11）

> 日期：2026-11-11 21:17–22:05　审查人：质量审查员
> 结论：**needs_revision（FAIL）** —— F2（nonbody≥3）、F4（CIP 特判删除/p5 source_inherent）、F11（测试 hermetic）、F5/F6（spec 命名/§7/§12）已实测修复；但 **F1（M1 方向相反+阈值放宽→误伤 wz1/wz2 正常相邻 span）**、**F2（M3/M4 仍缺）** 未解决，另有 §12 基线 hash 不符与「wz4 exit0」声明不实。

### 6.1 已修（实测）

- **F2 nonbody**：`_is_nonbody_page` 改为 `hits>=3`（或 PAGE_IMAGE）；探针：1 特征（md5）→ `non_body=0`；3 特征 → `non_body=1` ✓。
- **F4 CIP/p5**：`verify_typography.py` 无 CIP 特判；red 产品 p5 `—北京` 现为 **source_inherent waived**（rule 5.1.1/5.1.4，source_line=`—北京:…`）✓；wz4_s4 带 lines 出现 **6 条 render_introduced**（`。`行首，p138/p190…）✓。
- **F11 hermetic**：测试不再读 `output/`；`test_verify_typography.py` **17 passed**；无 output/tmp_vert 路径 ✓。
- **F5/F6 spec**：header `implemented`（L3）、§2 增「命名以实现为准」映射、§7「工具 exit 与 gate verdict 分离」、§12 冻结基线/§12.1 p5 归属/§12.2 p97 ✓。

### 6.2 未修/新发现（must-fix）

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F1'** | **high** | **M1 与 spec 方向相反 + 阈值放宽，且已在 wz1/wz2 误伤**：spec M1 = **跨视觉行** span 对、面积 >`0.02×min`；实现 `_general_overlap` = **同一视觉行** span 对、>`0.50×min`。① 探针：两行 bbox 纵向重叠 → 0 违规（应 hard，漏报）；② wz2 ancient 19 条 `hard_span_overlap`、wz1 4 条，经手工复算均为**正常相邻 span 的宽高盒重叠**（wz2 p110 `‘颜’古读如‘雁’`×`',('` 交叠 = **64.2%** min；wz1 p31 `5.`×《工资…》= **64.9%**）——CJK 行盒/标点盒天然内嵌，非真实压字；wz2 因此 FAIL（t247 时 PASS 0），属回归 | 按 spec 改：跨行 span 对、阈值 0.02×min（并排除同标点组）；同视觉行相邻 span 不得判 L1；补 cross-line/same-line 单测；wz1/wz2 回归为 0 hard |
| **F2'** | **high** | **L1-M3 页码错位、L1-M4 字符丢失/重复仍完全缺失**（grep 仅 L2 `toc_pagenum_align`；无 `hard_pagenum_misplace`/`hard_char_loss_dup`），spec §1 L1 表仍列 5 条；t250 只补了 M1/M2 | 补 M3（页码序列/页脚带）与 M4（页/行字符量对 OCR lines）；各自单测；或明确降级并同步 spec |
| **F3'** | **medium** | **M2 被收窄**：spec = span bbox 越出可打印区（页幅±容差）；实现仅「整段完全越出」或「横向越出 >20% 页宽」。探针：右缘越出 10% 页宽的正文 span → PASS（漏报） | 按 spec 以可打印区+容差判部分越界（横向/纵向），保留 p97 34 条；补单测 |
| **F4'** | **medium** | **§12 冻结基线 hash 不符**：spec 写 `output/wz4/wz4_s4.pdf` md5 `dd011c2a…`，实测 **`80d537e2b54afbcfd90bdf7901559aa7`**（ghbq_title_toc2 的 `beba0f6c…` 符合）→ 冻结基线不可复现 | 以当前产物重算并更新 §12；或注明该产物已重建 |
| **F5'** | **medium** | **t250「wz4 exit0」声明不实**：带 `--lines`（scan2pdf 实际传入 lines）→ WZ4 **FAIL/exit=1**（render 6）；不带 lines 才 WARN/exit=0。冻结产品 `wz4_s4.pdf` 带 lines 同为 FAIL/exit1 | 更正记录：pipeline 路径 typography 为 FAIL（gate 不变）；"exit0" 仅指无源行模式 |
| **F6'** | **low** | `_attribute_text` 前 8 字前缀→source_inherent 仍用于非 edge 规则（5.1.10 等），不做同位置字符核对 | 统一 `_attribute_edge` 语义或加同位置字符校验 |
| **F7'** | **note** | p97 34 条 hard 越界为真实缺陷，保留 ✓；wz2 ancient 现 FAIL 为 M1 误伤所致（非产品回归），但会污染验收 | 随 F1' 修复后 wz2 应回 PASS |

### 6.3 结论

- **通过**：nonbody≥3、p5 source_inherent、wz4 6 条 render 归因、测试 hermetic（17 passed）、spec 命名/§7/§12 结构、p97 34 保留。
- **不通过**：F1'（M1 反向+误伤 wz1/wz2，high）、F2'（M3/M4 缺失，high）为 must-fix；F3'–F6' 需修/更正。
- 复盘：本轮把「误报」修成了「同视觉行判重叠」——虽能避开跨栏误报，却与 spec 的跨行判据相反，并把正常相邻 span 判成 hard；需按 spec 重做并回归 wz1/wz2。

---

## 7. round-3 终审（t256，t255 修复 M2/M1/M3/M4/edge/§12）

> 日期：2026-11-11 21:32–22:20　审查人：质量审查员
> 结论：**needs_revision（FAIL）** —— M1 转诊断、M3/M4 转 v1.1、edge/§12/基线 hash、nonbody≥3、p5 source_inherent、wz2 PASS 均已落地；但 **M2「部分越界」实际仍未实现**（代码只判整段完全越界，探针右缘越出 170pt 仍 PASS），且新增 **CIP/ISBN non_body 启发式未入 spec、吞掉 p2 内容页**；edge 的 `pos` 参数未接线（行末规则仍按行首归因）。

### 7.1 已修/已验证（通过）

- **M1**：`_general_overlap` 改跨行 0.02×min、同视觉行/标点组不判；默认关闭，`TYPOGRAPHY_M1=1` 只写 `diagnostics.M1`/`counts.m1_diagnostic`，不计入 violations/hard/exit（spec §1.2/§12.3 一致；`layers.L1=['M2','M5']`）✓。
- **M3/M4**：spec §1.1 明确 L1 仅 M2/M5，M3/M4 归 verify/v1.1（文档化）✓（覆盖缺口见 F4）。
- **edge**：`_attribute_edge` 增加位置校验；p5 `—北京` 仍 **source_inherent**（red 产品 46/42 hard/0 render/9 waived）✓。
- **nonbody≥3**：1 特征探针→`non_body=0`；3 特征→`non_body=1` ✓（另有 ISBN 启发式，见 F2）。
- **§12**：工具 sha `55329569…`、title_toc2 md5 `beba0f6c…`、wz4_s4 md5 `80d537e2…` 与实际一致；§12.3 更正「pipeline 带 lines → FAIL/exit1；无源行才 exit0」✓。
- **命令**：`ghbq_title_toc.pdf` WARN/exit0（4 violations，hard0）；`wz4_s4` 无 lines WARN/exit0、带 lines FAIL/exit1（render6）；`ghbq_p97v2` hard0；wz2 ancient **PASS/0 hard**；wz1 WARN/60（hard0，见 F7）。
- **测试**：`test_verify_typography.py` **17 passed**（hermetic）；unit **774 passed**（193.96s）；invariants 首次 2 failed、复跑 **13 passed**（见 F6）。
- **边界**：PUNCTUATION/PUNCT_EVAL 未被改动（git status 干净）✓。

### 7.2 未修/新发现（must-fix）

| id | severity | problem | requiredFix |
|---|---|---|---|
| **F1'** | **high** | **M2「部分越界」仍未实现（放水）**：代码判据为 `b[2]<x0−tol`（整段在左）/`b[0]>x1+tol`（整段在右）/`b[3]<y0−tol` /`b[1]>y1+tol`，只覆盖**完全越界**；探针 span `[560, 84.9, 765.4, 104.2]` 对 595×842 页（tol 11.9）右缘越出 **170.4pt** → 工具 **PASS**。p97 同页：`1979` bbox x0=673.3（>612.75）判 hard，`邓小平同志在` bbox [607.6,154.1,673.3,…] 右缘越出 78.3pt 但 x0<612.75 → **未判**。t255「横向/纵向部分越界」声明与代码不符 | 右侧判 `b[2] > x1+tol`、底部 `b[3] > y1+tol`、左侧 `b[0] < x0−tol`、顶部 `b[1] < y0−tol`（并保留整段越界与 short-span 例外）；补「右/下部分越界」单测；p97 部分越界 span 应计入 |
| **F2'** | **medium** | **non_body 额外 ISBN/CIP 启发式未入 spec 且吞内容页**：`_is_nonbody_page` 增 `if 'isbn' and ('图书在版编目' or '上架建议') → True`；spec §4.3 只有 3 类判据（PAGE_IMAGE / ≥3 meta / 40% 图块+<5 行）。实测 ghbq `non_body=[2,5,104]`：p2 是 **内容简介页**（396 字正文 + 底部上架建议/ISBN）、p5 是 CIP 页；p2 被整页排除 L2/L3（虽当前无 GB 违规，但口径过宽/未文档） | 把 ISBN/CIP 判据写入 spec §4.3 并限定为「版权/CIP 页」（`图书在版编目` 单独成立），`上架建议` 不得单独触发；确认 p2 是否应参与评测；加单测 |
| **F3'** | **medium** | **edge 的 `pos` 未接线**：`_attribute_edge(..., pos)` 支持 start/end，但 `_gb51_violations` 调用 `_emit_gb` 未传 pos（恒 start）；行末规则（5.1.3 行末前括号/引号）在**源行完全一致**时被误判 render_introduced（实测 `_attribute_edge(0,'ABC（','（',{'0':['ABC（']},pos='start')` → render；pos='end' → source） | 行末规则传 `pos='end'`；补「行末规则源一致→source_inherent」单测 |
| **F4'** | **medium** | **M3/M4 覆盖缺口**：spec §1.1 称 M3 由 verify_geom/verify_vert 负责，但两者实际不检查页码错位；M4 仅竖排 verify_vert 查字符量，横排无字符量硬校验。M3 目前**无任何门禁覆盖** | 在 spec 明确「M3 暂无门禁（v1.1）」或补 verify 侧页码校验；不得以「verify 负责」表述掩盖缺口 |
| **F5'** | **low** | wz1 WARN 60（45 条 L2 TOC 指标 + 15 条 L3 unknown），hard0；wz2 PASS 0 ✓；「③ 层无 noise」在 wz1 仍有 15 条 unknown warn | 记录为 warn-only/可接受；如需降噪，L2 TOC 指标仅在目录页出 |
| **F6'** | **low** | 测试/声明不一致：unit 实际 **774 passed**（非 784）；invariants 首次 **2 failed**、复跑 13 passed（并行构建下非确定）；t255「全量 784 passed/0 failed」未复现 | 报告按实测计数；invariants 失败需定位（no_replacement_char 等读共享产物/数据）；`src/test` 不得读可变 output |
| **F7'** | **note** | p97 真越界（整段越界 43 条）仍被 hard 抓到 ✓；p97v2 已修复 hard0 ✓；title_toc exit0/wz4 无 lines exit0 声明 ✓ | 保持 |

### 7.3 结论

- **通过**：M1 诊断化、M3/M4 文档化、edge 源侧豁免（p5）、nonbody≥3、§12 基线 hash/§12.3、wz2 PASS、测试 hermetic（typography 17 passed）。
- **不通过**：F1'（M2 仅完全越界，partial overflow 漏报，high）为 must-fix；F2'（nonbody ISBN 启发式吞 p2 内容页，未入 spec）、F3'（edge pos 未接线）需修；F4'–F6' 需说明/修。
- 判断：本轮把「M2 部分越界」写进 spec/声明，但代码仍是 tick 式整段越界；「ghbq_p97v2 hard=0」依赖**重建产物已修**，不能证明 M2 判据正确；p97 同页部分越界 span（右缘 +78pt）仍漏。

### 7.4 复现（本轮新增）

```bash
# M2 partial overflow 探针（构造；右缘越出 170pt）→ PASS（应 FAIL）
/usr/bin/python3 src/test/verify_typography.py /tmp/t251_probe_partial.pdf --json /tmp/p.json
# p97 同页：整段越界判 hard，部分越界不判
/usr/bin/python3 src/test/verify_typography.py output/ghbq_full/ghbq_title_toc2.pdf \
  --src-pdf source_pdf/ghbq.pdf --lines output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json --json /tmp/red3.json
# nonbody: 1 特征不豁免、3 特征豁免；ghbq p2/p5/104 被 ISBN 启发式豁免
/usr/bin/python3 src/test/verify_typography.py /tmp/t251_probe_one.pdf --json /tmp/one.json
/usr/bin/python3 src/test/verify_typography.py output/ghbq_full/ghbq_title_toc.pdf --src-pdf source_pdf/ghbq.pdf \
  --lines output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json --json /tmp/ghbq3.json
```

| 文件 | sha256 |
|---|---|
| `src/test/verify_typography.py` | `55329569785aa3215bb0492a56ff2dbf1eced739c3bdf2c3e7a9e4510b2e5689` |
| `spec/governance/TYPOGRAPHY_EVAL.md` | `a50dcb44de88e5244497fd1ef3e680d516c44e28fcdafcbd8bfd4b3915f66528` |
| HEAD | `fc86ce8`（未 commit） |
