# battle2 独立验收报告（P1 双管线标点配对/禁则审计）

> 验收人：验证评审员（独立验证方，t5）　时间：2026-11-04
> 基线：HEAD `20d327e` + battle1/battle2 未提交改动（工作树）；**未 commit / 未 push**
> 验收对象：t4 交付 —— `spec/governance/PUNCTUATION.md`、`src/tools/punct_audit.py`、
> `docs/battle2_punct_audit.md`、battle1 两处收尾（`spec/README.md` 账本行 + `census_ring_digit.py` 755）
> 原则：不轻信自述——规则表对照 GB/T 原文、工具亲手重跑、finding 回产物/源图核对、battle1 内容绑定独立验算。

---

## 0. 验收结论（先行）

**不可按现状交付用户作为审计结论，也不可作为后续门禁依据；需修订后复验。**

核心理赔成立的部分（工具可复现、p620 定案、B/C 发现问题、覆盖与纪律）都在，但报告的两项**统计主结论**
（A=4,208 源书自身 / B=36 产物引入）存在系统性归因错误，且规则表漏掉国标的破折号边界；在修订前，
`B`（报告建议的门禁候选指标）是一个**下界**而不是实测值。具体三项必修：

| # | 必修项 | 证据（本报告实测） | 影响 |
|---|---|---|---|
| **F1** | **A/B 归因盲区**：`classify_audit` 只判「违规字符是否在同页 OCR 行里」，不判「是否在源行首」。产物断行把标点甩到行首时，仍记 A | 横排 **15 处**候选（wz3 9 / wz4 6）；**2 处已用源图确证**是产物断行：wz3 p25「，恰与此同」源图同一行连续、wz4 p138「。”③」源图在行中 | **B 被低估**：已确证 ≥2 条应改 B；按对齐位置全书 15 条候选（若全成立 B≥51 而非 36）→ 门禁指标不可直接用 |
| **F2** | **破折号误报**：行首「——」被按 §5.1.6（连接号）计为违规 A；但 §5.1.6 只管连接号，GB/T §4.10.3.9/4.10.3.10 的示例本身就是行首破折号 | 横排 5 处「——」+ wz1 p54 单「—」+ wz7 p29 西文题词 = **≥7 处假阳**（wz3 p542/711/773/824、wz4 p4、wz1 p54、wz7 p29） | A 被高估；报告 §5.1 的 A 抽样 #7/#10/#11 把合法副标题/出处判成「源书自身不合规」 |
| **F3** | **K=1,518「合法 carry」未验证**：`pair_balance` 的 carry 只按「靠近页首/页末」赋值（`idx<=2` / `idx>=len-3`），不做对偶延续检查；与 report §3/§8.1「须构成同一对延续」矛盾 | 1,518 条 K 中：相邻页**完全没有对偶符** 74 条；相邻页边界行首/末命中对偶符仅 **3** 条；1,444 条只是「相邻页某处有对偶符」（弱证据） | K 语义不成立；可能藏真缺陷 |

低级别（不阻塞但应一并修）：F4 spec §8.2 列了未实现的 `quote_continuation`；F5 竖排方括号等形态误挂 §5.2.3
（国标 5.2.3 只规定引号/圆括号）、「19 对」与 spec 表 17 行不一致；F6 报告里两个复现 md5 需默认 label（未注明）；
F7 p620 伴随「多一个 ﹂」是 `punct_diff` 诊断项、不在 B=36/附录 A 内（报告写成「归 B 类」）；F8 抽样 #2 列号 10 vs
实际 11（1-based 差一）。

**一句话实测**：规则表 **12+ 条款号与 GB/T 原文逐字一致**；punct_audit 五书 JSON 与 t4 证据**逐字节相同**、
两次运行 md5 相同；**p620 缺 」判 C 成立**（源图墨条 22.4×11.2pt、产物该列无）；但抽样 **19 条中有 10 条分类错误**
（2 条源图确证的横排断行 A/B 错分 + 8 条合法/同族破折号假阳），
其中 2 条已由源图确证为产物引入。详细见 §2–§9。

---

## 1. PASS/FAIL 总表（逐项 + 实测）

| # | 验收项 | 结论 | 实测（本报告重跑/复核） |
|---|---|---|---|
| 1 | 规则表 ≥6 条条款号与 GB/T 15834—2011 原文一致（含竖排 §5.2） | **PASS**（附 scope 说明） | 独立提取 `docs/15834-2011-gbt-e-300.pdf`（25 页）逐字核对 **14 条**：§5.1.1/5.1.2/5.1.3/5.1.4/5.1.5/5.1.6/5.1.7/5.1.9/5.1.10/5.1.11/5.2.3/5.2.6/4.8.3.5/4.13.2 —— 条款号与规则内容全部一致；但 **§4.10.3.9/4.10.3.10 未纳入**（→F2） |
| 2 | punct_audit 横排/竖排两模式可复现，JSON 与报告数字一致 | **PASS** | 五书重跑 JSON 与 t4 `tmp_vert/battle2/audit/*.json` **逐字节相同**（md5 见 §3.2）；报告 §4.1 逐项计数一致；同输入两次运行 md5 相同（wz1 `4a53d2bf…`、wz7 p619-621 `728fe114…`）；扫描规模 83,300 行/列、704 处源图漏识/485 页 |
| 3 | 抽样 ≥10 条 finding 回产物/源书核对，真伪与分类正确 | **FAIL** | 抽样 **19 条**（§4）：**9 条真伪+分类正确**（p620 C ×2、p760/p922/p623 B、wz1 p222 dash_split、wz7 p621/p31/p32 A）；**10 条分类错误**：wz3 p25「，」与 wz4 p138「。」是产物断行引入却记 A（源图确证，应 B）；wz3 p542/p711/p773/p824、wz4 p4（×2）、wz1 p54 是合法副标题/出处破折号却记 A（应不计违规）；wz7 p29「—」西文题词同理；（另：wz1 p222 行22 是同一 dash_split 的重复项，不计入上述 19 条抽样） |
| 4 | 合法情形（副标题/出处破折号、多段引文）误报检查有结论 | **PASS（有结论，结论为「存在误报」）** | 副标题/出处破折号：**存在误报 ≥7 处**（F2，GB/T §4.10.3.9/4.10.3.10 示例证据见 §5.1）；多段引文 §4.8.3.5：**未误报为违规**（未配对 open 归 O 桶不计违规），但工具并未实现合法判定（F4），O=1,636 是混合残差（§5.2） |
| 5 | 横排四书与竖排 wz7 都有审计数字，三类分类均有抽样证据 | **PASS**（附 A 抽样有效性说明） | 五书数字齐全（§3.3）；A/B/C 各有抽样（A 12、B 14、C 12）；但 t4 报告 §5.1 的 A 抽样 #7/#10/#11 是合法破折号（假阳），A 类代表性受影响（F2）；三类涉及页数 1,871/29/199 与报告一致 |
| 6 | 工作树 diff 仅含 t4 范围文件；两处 battle1 收尾已落实 | **PASS** | `git status` 与 t3 基线比只多 3 个 t4 新文件 + `spec/README.md` 追加 3 行 + `census_ring_digit.py` 权限恢复 755（内容未动）；产品代码（build_vert/verify_vert/verify_geom）零改动；无调试残留；`ruff check` All checks passed |
| 7 | 记录当前工作树 SHA-256 清单，并复述 battle1 验收字节未变（内容绑定） | **PASS** | 23 文件 SHA-256 + 总哈希 **`6d504b041508c0efa75d6c57fde243bf43b2a046192a28e663e508fc622a8d22`**（§8）；battle1 20 文件中 18 个字节未变（mtime 全部停在 battle1 窗口 + t4 四书重建产物与 t3 产物逐页文本/行 bbox **0 差异**）；`spec/README.md` 为追加式修改、`census_ring_digit.py` 仅权限变化 |
| 8 | docs/battle2_acceptance.md 含 PASS/FAIL 总表、原始输出、遗留风险、明确结论 | **PASS** | 本文件 |

---

## 2. 规则表核对（对照 GB/T 原文）

**取数**：本报告作者用 `/usr/bin/python3` + fitz 独立提取 `docs/15834-2011-gbt-e-300.pdf`（25 页、有文本层，
与 t4 的 `tmp_vert/battle2/gbt15834.txt` 同源），逐条比对 `spec/governance/PUNCTUATION.md`。

| 条款 | GB/T 原文（节选） | spec 用法 | 判定 |
|---|---|---|---|
| §5.1.1 | 「句号、逗号、顿号、分号、冒号……不出现在一行之首」 | 行首禁则 S1 | ✔ |
| §5.1.2 | 「问号、叹号……不出现在一行之首」 | S2 | ✔ |
| §5.1.3 | 「前一半不出现在一行之末，后一半不出现在一行之首」 | S3/E1 + `pair_split` | ✔ |
| §5.1.4 | 「破折号……占两个字位置……不能中间断开分处上行之末和下行之首」 | D1 `dash_split` | ✔ |
| §5.1.5 | 「省略号……不能中间断开分处上行之末和下行之首」 | D2 `ellipsis_split` | ✔ |
| §5.1.6 | 「**连接号**……不出现在一行之首」 | S4（连接号字符集） | ✔（条款号/文字一致；**工具把它套到破折号上 → F2**） |
| §5.1.7 | 「间隔号……占半个字位置，上下居中，不出现在一行之首」 | S5 | ✔ |
| §5.1.9 | 「分隔号占半个字位置，不出现在一行之首或一行之末」 | S6/E2 | ✔ |
| §5.1.10 | 「标点符号排在一行末尾时，若为全角字符则应占半角字符的宽度」 | §6 `trail_width` 报告项 | ✔ |
| §5.1.11 | 「……可适当压缩标点符号所占用的空间」 | §6 说明「不是错误」 | ✔ |
| §5.2.3 | 「引号改用……﹃﹄……﹁﹂，括号改用”︵︶“」 | 配对集合竖排形 + V2 | ✔（**但方括号/六角/书名号竖排形国标未规定，挂 §5.2.3 属过度归属 → F5**） |
| §5.2.6 | 「横排……不能居行首或行末的要求，同样适用于竖排」 | V4 | ✔ |
| §4.8.3.5 | 「不止一段时，每段开头仅用前引号，只在最后一段末尾用后引号」 | §0-2 合法性边界 | ✔（规则表述正确；工具未实现判定 → F4） |
| §4.10.3.9 | 「用于副标题之前」示例：`飞向太平洋` / `———我国新型号运载火箭发射目击记` | **未纳入** | **✘（F2：行首破折号是国标示例形态）** |
| §4.10.3.10 | 「用于引文、注文后，标示作者、出处或注释者」示例：`先天下之忧而忧……` / `———范仲淹` | **未纳入** | **✘（同上）** |

- 结论：条款号与规则内容**一致**（满足 ≥6 条），但规则表漏了「破折号 vs 连接号」的适用边界；这不是条款号错，
  是**规则映射不完整**，直接导致工具把副标题/出处的行首破折号当违规（F2）。
- 备注：spec §1 已如实注明「PDF 文本层把破折号提取成 3 个 `-`、`〈〉` 提取成 `< >` 属字形/编码还原误差」，该说明与实测一致。

---

## 3. 工具复现（亲手重跑，与 t4 证据逐字节对比）

### 3.1 命令（本报告作者重跑；日志 `/tmp/acceptance2/logs/`）

```bash
cd /opt/test
# 横排四书
/usr/bin/python3 src/tools/punct_audit.py tmp_vert/battle2/rebuild/wz1.pdf --mode h \
    --json /tmp/acceptance2/audit/wz1.json --md /tmp/acceptance2/audit/wz1.md --label wz1
# wz3 / wz4 / mgfdmg 同式（wz3 用 rebuild/wz3.pdf）
# 竖排 wz7 全书（含源图侧 C 类检查）
/usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v30.pdf --mode v \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --src-pdf source_pdf/wz7.pdf \
  --json /tmp/acceptance2/audit/wz7_v30.json --md /tmp/acceptance2/audit/wz7_v30.md --label wz7-v30
# 复现性（默认 label，不传 --label）
/usr/bin/python3 src/tools/punct_audit.py tmp_vert/battle2/rebuild/wz1.pdf --mode h --json /tmp/a.json
/usr/bin/python3 src/tools/punct_audit.py tmp_vert/battle2/rebuild/wz1.pdf --mode h --json /tmp/b.json
md5sum /tmp/a.json /tmp/b.json
```

### 3.2 「五书 JSON 与 t4 证据逐字节相同」实测

| 书 | 我的重跑 md5 | t4 证据 md5 | 结论 |
|---|---|---|---|
| wz1 | `f7b619df1eb7ce6ded6f81866b07571e` | 同 | IDENTICAL |
| wz3 | `be92d412a1528bfef128fbcdd57ddba5` | 同 | IDENTICAL |
| wz4 | `ba30589c60cca17dd35add0a43eeffeb` | 同 | IDENTICAL |
| mgfdmg | `690e0200fda4ef554821731aa39049c9` | 同 | IDENTICAL |
| wz7 | `55a207676f9ddc12873513a559860879` | 同 | IDENTICAL |

- 复现性：wz1 默认 label 两次均 `4a53d2bfcdc969f894c2cde3bc0fc6f9`（与报告 §3 的 `4a53d2bf…` 一致）；
  wz7 `--pages 619-621` 两次均 `728fe1143ef00e0c9161bd112081a857`（与报告 `728fe114…` 一致）。
- 说明：报告里的这两个 md5 **必须用默认 label** 才复现；带 `--label` 时 md5 变成证据文件的
  `f7b619df…` /（p620 旧中间版 `bc2c8cb7…`）。报告没写明这一点（F6，低级别；性质本身成立）。

### 3.3 计数与报告 §4.1 对照（我的重跑）

| 书 | 行/列数 | line_start | line_end | pair_split | dash_split | ellipsis_split | pair_balance | trail_width |
|---|---|---|---|---|---|---|---|---|
| wz1 | 5,676 | 5 | 0 | 1 | 1 | 0 | 94 | 1,248 |
| wz3 | 29,131 | 33 | 0 | 4 | 0 | 1 | 2,018 | 10,271 |
| wz4 | 22,961 | 10 | 0 | 0 | 0 | 0 | 579 | 5,299 |
| mgfdmg | 10,803 | 0 | 0 | 0 | 0 | 0 | 90 | 2,304 |
| wz7 | 24,729 | 2,597 | 2 | 265 | 0 | 0 | 1,841 | — |
| **合计** | **83,300** | **2,645** | **2** | **270** | **1** | **1** | **4,622** | **19,122** |

- 与报告 §4.1 **逐格一致**（含 58,571 横排行 = 5,676+29,131+22,961+10,803；24,729 竖排列）。
- `ocr_miss_punct`：总 **704** 处 / **485** 页，sub 拆分 `product_missing 234` + `render_fixed 470` —— 与报告一致。

### 3.4 三类归因数字（读 t4 的 `*.classified.json`，与报告 §4.2 逐格核对）

```
A 4208 / B 36 / C 234 / C_fixed 613 / K 1518 / O 1636 / R 19122；punct_diff 17734（诊断，不计违规）
逐书：wz1 61/1/0/0/18/21/1248；wz3 815/7/0/0/339/895/10271；wz4 152/0/0/0/159/278/5299；
      mgfdmg 37/1/0/0/14/38/2304；wz7 3143/27/234/613/988/404/—
```

- 与报告 §4.2 完全一致；`punct_diff` = 491+12,647+2,664+368+1,564 = **17,734** 一致。
- **但**：这些数字来自 `tmp_vert/battle2/classify_audit.py`（临时脚本、不在仓库），其 A/B 判定口径存在 F1 盲区；
  数字可复现 ≠ 归因正确。

---

## 4. 抽样核对 ≥10 条（回产物/源书）

**方法**：文本层用 `punct_audit` 的 `extract_h/extract_v` 取产物行/列；源图用 fitz 按普查/OCR 坐标 600–900dpi
裁片对照；GB/T 条款按 §2 原文。

| # | 书/页/位置 | 审计项 | t4 分类 | 本报告核对 | 判定 |
|---|---|---|---|---|---|
| 1 | wz7 p620 列9 `你撇的人…沒下稍！` | `ocr_miss_punct product_missing` `」` mark 22.4×11.2 | C | 源图 `！` 下有 ﹂ 墨条、产物该列无 ﹂（裁图 `p620_B_crops.png` 第 1 组） | **✔ 真，C 正确** |
| 2 | wz7 p620 列1 `一悶把幃屏…` | `ocr_miss_punct render_fixed` | C_fixed | 源图有 ﹂、产物也有（同图第 2 组） | **✔** |
| 3 | wz7 p760 列10 `…個嘴兒。﹂﹂可霎作怪` | `pair_balance` 多出 ﹂ | B | 源图一个 ﹂，产物两个（同图第 3 组） | **✔ 真，B 正确** |
| 4 | wz7 p922 列16 `…號葵軒。﹂西﹂門慶` | `pair_balance` 词中 ﹂ | B | OCR 行 `…西門慶…` 无第二个 ﹂；源图一个（同图第 4 组） | **✔ 真，B 正确** |
| 5 | wz7 p623 列13 `…哄了你不成？﹂正是：﹂` | `pair_balance` 多出 ﹂ | B | OCR 行止于 `正是：`；源图一个 ﹂（同图第 5 组） | **✔ 真，B 正确** |
| 6 | wz1 p222 行21/22 `…貢獻—` / `—《马克思恩格斯全集》…` | `dash_split`（行21） | B | 产物两行分别在 `—`/`—` 处断开；OCR 行内 `——` 相邻 → 产物拆开 | **✔ 真，B 正确**（但行22 另记一条 line_start A，是同一缺陷的重复项 → 归因重复） |
| 7 | wz3 p25 行11 `，恰与此同（见` | `line_start` `，` | A | **源图同一行连续** `…金文耒彝作“”，恰与此同（见`（裁图 `src_rows_examples.png` 第 1 组）→ 断行是产物引入 | **✘ 应为 B（F1 实例）** |
| 8 | wz4 p138 行11 `。3⃝这个思想的表述…` | `line_start` `。` | A | 源图该行 `…无产阶级专政’”。③这个思想…`，`。` 在行中（裁图第 2 组）→ 断行是产物引入 | **✘ 应为 B（F1 实例）** |
| 9 | wz3 p542 行3 `——由租庸调至两税` | `line_start` `—` §5.1.6 | A | 源书章名「唐代赋税制度之演变」下一行副标题「——由租庸调至两税」（GB/T §4.10.3.9 副标题用法） | **✘ 合法破折号，不应计违规（F2）** |
| 10 | wz3 p711 行3 `——海上对外贸易` | 同上 | A | 同上（章副标题） | **✘ F2** |
| 11 | wz3 p773 行3 `——由两税至一条鞭` | 同上 | A | 同上 | **✘ F2** |
| 12 | wz3 p824 行30 `——止纳系官五户丝户：纳` | 同上 | A | 同上（小节标题/列举） | **✘ F2** |
| 13 | wz4 p4 行8 `——马克思主义政治学原理` | `line_start` `—` | A | 封面「政治的逻辑」下一行副标题（§4.10.3.9） | **✘ F2** |
| 14 | wz4 p4 行0 `—上海：上海人民出版社,2016` | `line_start` `—` | A | CIP 出版信息行，破折号引出处（§4.10.3.10 同族；单横线为源书旧式形态） | **✘ F2（形态有差异，位置不违规）** |
| 15 | wz1 p54 行9 `—西方学者对马克思劳动价值论的质疑` | `line_start` `—` | A | 小节标题（前一行「下论题。」），副标题用法 | **✘ F2** |
| 16 | wz7 p29 列3 `—Wereceivebutwhatwegive.—Coleridge` | `line_start` `—` | A | 西文题词，破折号在行首（§4.10.3.10 同族；§5.1.6 只管连接号） | **✘ F2** |
| 17 | wz7 p621 列5 `；﹁一倦倚綉床…` | `line_start` `；` | A | 源图列首确为 `；`，产物同（裁图 `vert_A_crops.png` 第 1 组） | **✔ A 正确** |
| 18 | wz7 p31 列10 `：﹁錢塘汪棣香…` | `line_start` `：` | A | 源图列首 `：`，产物同（第 3 组） | **✔ A 正确** |
| 19 | wz7 p32 列12 `，並不僅…` | `line_start` `，` | A | 源图列首 `，`，产物同（第 4 组） | **✔ A 正确** |

**统计**：19 条抽样中 **9 条真伪/分类正确**（#1–6、#17–19），**10 条分类错误**（#7、#8 = F1；
#9–#16 = F2 合法破折号/同族，其中 #14 单横线出处、#16 西文题词属下位边界情形）。
按对齐位置做全书统计：横排 line_start/pair_split **A 共 53 条，其中 15 条字符在 OCR 行中**（wz3 9、wz4 6）
→ 这 15 条是 F1 候选（已确证 2 条应改 B，其余 13 条需逐条回源图，不能直接断言 B≥51）；横排行首破折号 A 共 **9 条**（wz1 3 / wz3 4 / wz4 2，其中 5 条是「——」），
竖排行首破折号 A **1 条**（p29）→ F2 假阳 ≥7。

---

## 5. 合法情形检查结论

### 5.1 副标题/引文出处开头的破折号 —— **存在误报**

- **GB/T 原文**：§4.10.2「破折号的形式是『——』」；§4.10.3.9「用于副标题之前」示例为
  `飞向太平洋` / `———我国新型号运载火箭发射目击记`；§4.10.3.10「用于引文、注文后，标示作者、出处或注释者」
  示例为 `先天下之忧而忧，后天下之乐而乐。` / `———范仲淹`。**这些示例本身就是行首破折号**；
  国标对破折号只有 §5.1.4「不能中间断开」，没有「不能居行首」；「不能居行首」是 **§5.1.6 连接号**。
- **工具现状**：`DASH_CHARS = set('—―–‐-')` 并直接并入 `START_FORBIDDEN`（`punct_audit.py` L71/L76），
  行首「——」的第一字被当连接号报 `line_start §5.1.6`（L385）。规则表 S4 也只写「连接号」字符集
  （`PUNCTUATION.md` L102），**没有要求区分破折号**。
- **实测假阳**：wz3 p542/711/773/824（4 处「——」副标题）、wz4 p4（「——马克思主义政治学原理」）、
  wz1 p54（「—西方学者…」小节标题）、wz7 p29（西文题词「—We receive…」）= **≥7 处**；
  另有 wz1 p222 行22 是 `dash_split`（B）的第二半（重复项），wz4 p4 行0 是 CIP 出处行（形态差异，位置不违规）。
- **结论**：报告 A 抽样 #7/#10/#11 把上述合法用法判为「源书自身不合规」，需要更正；
  规则表/工具应加「破折号（——，含副标题/出处）不在行首禁则内；单字线若无法判定则只报不判违规」。

### 5.2 多段引文（§4.8.3.5）—— **未误报为违规，但工具未实现合法判定**

- 工具把未配对 open 全部归 `pair_balance unmatched_open` → `O` 残差桶，`O` **不计违规**（`classify_audit.py`），
  所以多段引文不会被误报成 A/B；这一点达标。
- 但 spec §8.2 声称实现了 `quote_continuation`（「开引号后下一段是否以开引号开头」），**代码里没有该检查**
  （`grep quote_continuation src/tools/punct_audit.py` 为空；只有 spec L165）。报告 §8.2 局限 4 也承认
  「无法纯文本判定，统一归 O」——spec 与工具/报告口径不一致（F4）。
- 本报告作者对 O=1,636 做过「下一单元是否以同一开引号开头」的独立统计：仅 **17 条**命中（立即下一行/列），
  说明 O 并不是按 §4.8.3.5 规则识别出来的，只是残差；不能声称「合法多段引文已处理」。

---

## 6. 覆盖与统计口径

- **覆盖**：横排四书（wz1 222p / wz3 850p / wz4 677p / mgfdmg 407p）与竖排 wz7（1,748p）都有审计数字；
  产品与 t1 基线一致（报告 §1 的 verify_geom/verify_vert 数字本报告作者未重跑，只核对产物与 t3 `/tmp/battle1/after`
  的关系，见 §8.2——t4 重建产物与 t3 产物逐页文本/行 bbox 0 差异）。
- **三类证据**：A 抽样 12、B 抽样 14、C 抽样 12 都有源图裁片（`tmp_vert/battle2/samples/`）；
  本报告抽验了 C 2 处、B 3 处、A 4 处（横排）+ 3 处（竖排），见 §4。
- **口径写清**（报告 §8.1）：横排 = PDF 文本层 line（同 block 归段）；竖排 = 字符按 x 聚类列（0.45×中位字宽）；
  carry = 页/段边界；归因 = difflib 对齐 OCR 行；`trail_width` 报告项；`punct_diff` 诊断项。
  **缺口**：A/B 归因只判「字符是否在 OCR 行」，未判「位置/边界字符身份」（F1）；K 的 carry 未验证（F3）。

---

## 7. 纪律检查

- `git status --porcelain`：与 t3 结束时相比，只新增 t4 的 3 个文件（`spec/governance/PUNCTUATION.md`、
  `src/tools/punct_audit.py`、`docs/battle2_punct_audit.md`），`spec/README.md` 追加 3 行账本，
  `src/tools/census_ring_digit.py` 权限 644→**755**（`ls -l` = `-rwxr-xr-x`；内容 SHA-256 未变，mtime 仍 00:44）。
- **未误改产品代码**：`build_vert.py` / `build_geom.py` / `verify_vert.py` / `verify_geom.py` 无改动；
  battle1 的 4 个实现文件 mtime 仍为 00:30–00:37（早于 t4 会话 20:04），本报告已用重建产物做功能绑定（§8.2）。
- **无调试残留**：`punct_audit.py` 无 TODO/FIXME/pdb/breakpoint；`ruff check --select F821,E9 src/tools/punct_audit.py`
  → `All checks passed!`。
- **spec 账本**：`spec/README.md` 已有 PUNCTUATION（governance 表）、battle1_horizontal、
  battle1_vertical_ring、battle2_punct_audit 四行（L12/L40/L41/L42）；PUNCTUATION 状态 `implemented`。
- **临时证据**：`tmp_vert/battle2/` 下 classify/recheck/src_miss 等为临时脚本（不入库），与报告 §9 声明一致；
  未发现 t4 把调试代码写进仓库。

---

## 8. 内容绑定（响应上一轮交付警告）

### 8.1 当前工作树 SHA-256 清单（23 文件，总哈希）

| 组 | 文件 | SHA-256 |
|---|---|---|
| battle1 | AGENTS.md | `5ae1ab398e97313d6078a7c001877f96ee39a8a6e4285ca648cb1a37731b0ab2` |
| battle1 | docs/vert_taskF_missed_fix.json | `66d31ce8643e9b233edab0d47d1732c55e82782d935e25665fd2ca08bedfaeb1` |
| battle1 | docs/vert_taskH_ring2digit.md | `94ab98c06bf8b2f8db5fbf5aaa30de6f01a9ceb9729ed26f104d2f4b8a864e76` |
| battle1 | spec/README.md（t4 追加 3 行） | `8dff69776236eebba1fac58cf6f76c784cff901eaefe54979501ddf5cf38ffa0` |
| battle1 | src/calibration/fit_common.py | `5403cbd5610563dc6099c81b7955347c9c585e5f61eb61329f1dd4e196682a8c` |
| battle1 | src/pipelines/build_classic.py | `7fadb5607d9f4f79c86133c8edf3fd969900974b0f780d024e7664a2bb2c946f` |
| battle1 | src/pipelines/build_pdf_v13.py | `9f206e3d50374cc51c294a017c0d517eabe88e84a1f801d3fd606fe95c721b61` |
| battle1 | src/test/test_cases.py | `54544be741e5d5b571745235f8403f9bee5777e83c9d3704b61fd717d74688ff` |
| battle1 | src/test/unit/PURE_FUNC_SPEC.md | `a554423811a39af2247d77755ca0d1f6ba46b198476c405e09cc50f0871234b4` |
| battle1 | src/test/unit/test_audit_features.py | `7d0f1f6d83426e0e02a71187a888dbf0a4321d9c6e40f74fc1d93a26a8b03e50` |
| battle1 | src/test/unit/test_pure_funcs.py | `1b49e943c67624424af6675064c9c8ba13b6f8ce9c0b6f4022e66e4276b1a681` |
| battle1 | src/tools/census_ring_digit.py（内容；t4 仅恢复 755） | `e5ac601748d9fb228cb96ca5fd621efce016d46b4ce0e844418a309dc3ad845e` |
| battle1 | src/utils/tex_escape.py | `e10b776c7ddfc6b501f3ba49f096fdda5549a3770a65ff1a4e37a88e06377a07` |
| battle1 | docs/battle1_horizontal.md | `858c9fd2ff584945347b297ef15d4ca1a3194ddec6d09215874805a9e757b416` |
| battle1 | docs/battle1_vertical_ring.md | `16ffd7c038a3a8bf762a6d9b30a8f6852ad0e7455d6b01b5a4438ce894ae17bc` |
| battle1 | src/test/unit/test_census_ring_judge.py | `22797a1a8d2034095a1aee52f111efd1c10366110af162166a99b40580d70dd2` |
| battle1 | src/test/unit/test_fit_common_cleanup.py | `9a3d3175ec32f898bbf0697182779b09e07d7e96f3b0dcfcab62d1b7ec0226f9` |
| battle1 | src/tools/merge_ring_digit.py | `596aed8bcc87a329762f85c05b96230b106b9c27be999840ca5a8ae56dbef79b` |
| battle1 | src/tools/ring_judge.py | `56f819e6f1602f916b7491b96dc43acd7a6e6c92e1f414c72a727a41a8be8e82` |
| battle1 | docs/battle1_acceptance.md | `edbe6e8aac508650635325fb7fba2067d5a888424276f1f4a08e5717500b7b0f` |
| t4 | spec/governance/PUNCTUATION.md | `0ce57354d728f6f1b06c3febfb38f108ab77d29b5397f45a3c0da00814e65bc1` |
| t4 | src/tools/punct_audit.py | `448dd7fc92c7376280f89878377c2eff91f95f478a6d1f529218c058d3dc06ac` |
| t4 | docs/battle2_punct_audit.md | `6949f211cc55df238e75c39de57aae1a5d08ac68512538ba2242ddb2be25c195` |

**总哈希**（按 `sha256  path` 排序后拼接再 sha256）：
`6d504b041508c0efa75d6c57fde243bf43b2a046192a28e663e508fc622a8d22`（23 文件；清单 JSON 见
`/tmp/acceptance2/sha256_manifest.json`）。

### 8.2 「battle1 已验收的 20 个文件字节未变（除 t4 新增/修改的文件外）」

- **18/20 字节未变**（上表前 18 个 battle1 文件，不含 `spec/README.md` 与 `census_ring_digit.py`）：
  ① mtime 全部停在 battle1 交付窗口（00:30–00:54），早于 t4 会话（20:04），t4 未写这些文件；
  ② **功能绑定**：t4 于 20:13–20:17 用当前树重建的四书产物（`tmp_vert/battle2/rebuild/*.pdf`）与 t3 验收时
  的 `/tmp/battle1/after/*.pdf`（00:32–00:36）逐页对比——**textdiff 0 / boxdiff 0**：
  ```
  wz1 222=222 textdiff 0 boxdiff 0 | wz3 850=850 0 0 | wz4 677=677 0 0 | mgfdmg 407=407 0 0
  ```
  即 battle1 代码行为与 t3 验收时**逐页一致**。
- **2/20 为 t4 明确修改的文件**：
  - `spec/README.md`：t4 追加 3 行账本（PUNCTUATION / battle1_vertical_ring / battle2_punct_audit），
    t3 验收时的横排行（battle1_horizontal）与 PURE_FUNC_SPEC 描述**仍在**；属**追加式**修改，无删除。
  - `src/tools/census_ring_digit.py`：内容 SHA-256 `e5ac6017…`（mtime 00:44 未变，与 t2 交付一致），
    t4 只把权限 644→755（`-rwxr-xr-x`），**无字节变化**。
- 限制（如实）：t3 当时未记录文件 SHA-256 快照；本节绑定依据 = **mtime + git diff 内容 + 重建产物 0 差异**。
  除此之外没有其它进程改过这些文件（本报告写入的 `docs/battle2_acceptance.md` 不在上表 23 文件内）。

---

## 9. 需修项（F1–F8，按严重度）

| ID | 级别 | 问题 | 位置 | 建议修法 |
|---|---|---|---|---|
| **F1** | **blocker（门禁指标失真）** | A/B 归因只看「字符是否在 OCR 行」，不看边界位置；产物断行甩到行首的标点被记 A | 报告 §4.2/§8.1 + `tmp_vert/battle2/classify_audit.py`（临时脚本，未入库） | 对 `line_start`/`pair_split` 的 A 判定加位置闸门：违规字符必须对齐到 OCR 行的**首/末字符**（横排且需排除 OCR 行合并）；否则记 B。复算后更新 A/B 数字 |
| **F2** | **high** | 行首破折号被按 §5.1.6 计违规（合法副标题/出处） | `PUNCTUATION.md` L102（S4）+ `punct_audit.py` L71/L76/L385；报告 §4/§5.1 | 规则表加「破折号（——/副标题/出处）行首不违规，§5.1.6 只管连接号」；工具对行首 `—`：若上文/下一字符可判为破折号（如 `——` 或后接书名/作者样式）→ 记报告项（不计 A/B），无法判定则标 `ambiguous`；报告 A 抽样 #7/#10/#11 更正 |
| **F3** | **high** | K=1,518「合法 carry」按位置赋权、无延续检查 | `punct_audit.py` L462–481（`near_start`/`near_end`）；报告 L113/L313；spec §8.4 | 统一口径：要么对 pair_balance 也做对偶延续检查（下一页首/上一页末），要么把 K 改称「页边界未配对（假定 carry）」并在报告/spec 同步；74 条相邻页无对偶符的应列入复核清单 |
| **F4** | medium | spec §8.2 列了 `quote_continuation` 但工具未实现，与报告 §8.2 局限 4 矛盾 | `PUNCTUATION.md` L165 | 删除该行，或实现「开引号后下一段以开引号开头」判定并补进 `counts` |
| **F5** | low | 竖排方括号/六角/书名号/方头括号形态误挂 §5.2.3（国标 5.2.3 只规定引号/圆括号）；「19 对」vs spec 表 17 行 | `PUNCTUATION.md` §1/§2；报告 §2.1 | 这些形态改标「Unicode 竖排形（国标未明示）」；统一「17 类 / 工具 19 条（半角/全角分列）」口径 |
| **F6** | low | 报告「两次运行 JSON md5」未注明默认 label（带 label 时 md5 不同） | 报告 §3 | 复现命令补 `（不传 --label）` 或把 label 写进命令 |
| **F7** | low | p620 伴随「多一个 ﹂」写成「→ B 类」，但它是 `punct_diff` 诊断项，不在 B=36 / 附录 A | 报告 §5.3.2 | 改称「B 类候选（punct_diff 诊断，未计入禁则类 B）」并在统计口径说明 |
| **F8** | low | A 抽样 #2「p29 列10」实际 1-based 列 11（idx10） | 报告 §5.1 表 | 统一列号口径（0/1-based）并校正 |

---

## 10. 未验证 / 不可验证项（如实列出）

- 未逐处复核全部 **36 条 B** 与 **234 条 C**（只抽验 3+2，其余靠报告自述与分类 JSON）；未逐处复核 **704 处**
  源图侧漏识候选。
- 未对全部 **2,595 条 A line_start**（含 14 条竖排「OCR 行首 mid」候选）逐条回源图；竖排 mid 候选
  （p85/230/343/494/554×2/630/631/816/1136/1145/1321/1346/1669）只核了 p230 一处（源图列首为 `」：`，
  产物把 `」` 移到上一列）——其 A/B 归属待 battle3 逐页判。
- 未重跑四书的 build 与 verify_geom/verify_vert（只核对了 t4 重建产物与 t3 产物 0 差异，以及报告数字与审计 JSON 一致）。
- 未验证「704 处源图漏识候选」的形状启发式在其它书/其它纸张上的误检率（只核了 wz7）。
- 未测试 `punct_audit.py` 对 `--pages` 中间区间的跨页 carry（只测了 619-621 与全书）。

---

## 11. 复现命令与日志

```bash
cd /opt/test
# 1) 五书审计（复现 t4 证据；输出到 /tmp/acceptance2/audit/）
for b in wz1 wz3 wz4 mgfdmg; do
  /usr/bin/python3 src/tools/punct_audit.py tmp_vert/battle2/rebuild/$b.pdf --mode h \
    --json /tmp/acceptance2/audit/$b.json --md /tmp/acceptance2/audit/$b.md --label $b
done
/usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v30.pdf --mode v \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --src-pdf source_pdf/wz7.pdf \
  --json /tmp/acceptance2/audit/wz7_v30.json --md /tmp/acceptance2/audit/wz7_v30.md --label wz7-v30

# 2) 复现性（默认 label）
/usr/bin/python3 src/tools/punct_audit.py tmp_vert/battle2/rebuild/wz1.pdf --mode h --json /tmp/a.json
/usr/bin/python3 src/tools/punct_audit.py tmp_vert/battle2/rebuild/wz1.pdf --mode h --json /tmp/b.json
md5sum /tmp/a.json /tmp/b.json       # 4a53d2bf… 两次相同
/usr/bin/python3 src/tools/punct_audit.py output/wz7_full/wz7_full_v30.pdf --mode v \
  --coords data/wz7_full/wz7_full_spotting_coords.json \
  --lines data/wz7_full/wz7_full_spotting_lines_patched.json --src-pdf source_pdf/wz7.pdf \
  --pages 619-621 --json /tmp/p.json   # 728fe114…（两次相同）

# 3) 本报告作者的复核脚本（未入库，逻辑见正文）
/usr/bin/python3 /tmp/acceptance2/alignment_analysis2.py     # 横/竖 A 的对齐位置（F1）
/usr/bin/python3 /tmp/acceptance2/k_check2.py                # K=1518 的对偶延续核对（F3）
/usr/bin/python3 /tmp/acceptance2/quote_cont.py              # O=1636 的多段引文候选（§5.2）
/usr/bin/python3 /tmp/acceptance2/src_crop.py                # wz3 p25 / wz4 p138 源图裁片（F1）
/usr/bin/python3 /tmp/acceptance2/crop_vertical2.py          # p620 C / p760/p922/p623 B 裁片
/usr/bin/python3 /tmp/acceptance2/manifest.py                # SHA-256 清单（§8）

# 4) 规则表核对
/usr/bin/python3 - <<'PY'
import fitz
d=fitz.open('docs/15834-2011-gbt-e-300.pdf')
print(''.join(p.get_text() for p in d))   # 对照 §5.1.x / §5.2.x / §4.10.3.9-10
PY

# 5) 纪律
git status --porcelain; git diff --stat
ruff check --select F821,E9 src/tools/punct_audit.py
ls -l src/tools/census_ring_digit.py         # -rwxr-xr-x
```

日志/证据（`/tmp/acceptance2/`）：`logs/summary.txt`、`logs/*.log`、`audit/*.json`、
`sha256_manifest.json`；裁图 `src_rows_examples.png`、`midcases_src.png`、`p620_B_crops.png`、
`vert_A_crops.png`、`p230_coltop.png`。

---

## 12. 验收结论

- **不合格（需修订后复验）**：punct_audit 的工具层可复现、p620 的 C 类定案、B 类 QSF 双﹂发现、
  五书覆盖与统计口径都成立；但报告的两项统计主结论（A/B）存在 **F1（B 低估：已确证 2 条、候选 15 条）** 与
  **F2（A 假阳 ≥7）**，以及 **F3（K 未验证）**，在修订前：
  - **不能交用户作为「审计结论」**（A/B 数字会把合法副标题/出处说成源书违规，把产物断行说成源书事实）；
  - **不能作为后续门禁依据**（门禁候选 B 是下界，不是实测值）。
- **最小的放行路径**（建议 captain 让 t4 修订后重验，预计改动集中在 `classify_audit` 临时脚本 + spec 两段 + 报告数字）：
  1. 修 F1：A/B 位置闸门 → 复算 A/B/C，更新报告 §4.2/§5/附录 A；
  2. 修 F2：规则表补破折号边界 + 工具对行首 `—` 加「破折号判定/ambiguous」，更正 A 抽样 #7/#10/#11；
  3. 修 F3：统一 carry 口径（延续检查或改称「假定 carry」），更新 K 的措辞与数字；
  4. F4–F8 顺手收口。
- 修订完成后，本报告 §3/§4/§8 的复现命令可直接重跑；重点看 ① A 的 53 条横排 line_start/pair_split 中
  「OCR 行中」15 条是否已改 B，② 行首破折号是否已不计违规，③ K 的 74 条无对偶符项是否已单列。

> 本报告只写实测；未 commit / 未 push / 未改实现代码。唯一写入仓库的文件是 `docs/battle2_acceptance.md`。
