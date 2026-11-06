# battle11 · spec 18 技术复核（圈码实现者视角）

> 任务：t54 — 对 `spec/vertical/18_ring_digit_census.md`（243 行）做技术准确性复核
> 复核人：竖排工程师（圈码实现者）　日期：2026-11-06
> 范围：§4 锚点 / §1 判据 / §2 参考基线数字 / §3 换书清单 13 行
> 约束：只写本报告；未改 `spec/`、`src/`、fix JSON；未 commit。

## 0. 三档结论（先行）

| 档 | 数量 | 内容 |
|---|---|---|
| **必须改** | **3** | ① §1.2「situation 1 …文本长度 **0 变化**」**与代码不符**：本书 352 条 situation 1 **全部是 2 位数字**（10–99），代码 `cur[:_tail.start()] + sent` 把 2 位换 1 个占位符 → `sl` 长度 **−1**；渲染层 ≤50（122 条）1 字形 → 净 **−1**，>50（230 条）○+2 位数字 3 字 → 净 **+1**。应改为「1 位 0 / 2 位 −1；渲染层另计」。② §1.3 第 5 步「situation 1 替换 **1 字**→1 圈码字形」是 1 位数字的特例，同样需按位数写清（与 ① 同源）。③ §4 ring 分支写 `L574–598`，实际分支为 **L574–596**（597–598 是统计 print）—— 按「锚点不符列必改」。 |
| **建议改** | **6** | ① §1.3 尺寸窗写 `[w_lo,w_hi]×step`（相对），代码 `P_V2` 是 **pt 绝对值**（14.5/19.5/11.5/19.5），§3 第 1 行已自认「默认值未参数化」——§1.3 应注明「设计目标 / 当前实现为 wz7 pt」；② §1.3 灰度写「由本页灰度分布自标定」，代码是**固定 `median − 20`**（census L154），§3 第 3 行也承认——§1.3 应标 planned；③ §1.2 说容差「按书/列宽参数化，见 §4」，**§4 没有该锚点**，代码实际是固定 **0.6pt**（build_vert L540）；④ §2 成本「367 圈 ≈ **60 页**条带（8 条/页）」与 8 条/页矛盾（367/8 ≈ **46 页**）；⑤ §3 第 9 行序列校验标「已实现」，但 `src/tools/` 里**没有** LNDS/非降的已提交工具（battle4/5 是临时脚本）——应标「battle4/5 已跑通，无复用工具」；⑥ §1.2 不变量「situation=1 ⇒ 文本尾 1–2 位数字」代码**不强制**（situation 1 无尾数字时打日志改走「情形②追加」，见 `_apply_missed_fix`）；（第 ⑦ 条已上调至必改 ③） |
| **接受** | 其余全部 | §4 的 8 组/12 个锚点**全部实测命中**（见 §1 表）；§1 判据主体（v2 尺寸窗/edge/ctr/fill/ar、v1 hole 仅回退、窗口列末一格、step 长列 n≥8 中位、最大连通域、situation 1 尾数字替换/2 追加、>50 ○+数字合成、RING_SIZE 0.95、不横压、格心）与代码一致；§2 参考基线 8 组数字与 battle1/4/5/10 报告**逐项一致**（184→352、367=352+15、331+36、34、21、16→2、66%、78/76/77/76、361/367、4700×7225、6.65px/pt）；§3 清单 13 行**大体属实**（逐行核对见 §4）。 |

## 1. 锚点对照（`grep -n` 实测 vs spec §4）

| 项 | spec §4 值 | 实测 | 判定 |
|---|---|---|---|
| `RING_INS_BASE` | L304 | **L304** | ✅ |
| `RING_SIZE` | L305 | **L305** | ✅ |
| `_ring_ins_num` | L454 | **L454** | ✅ |
| `_ring_put` | L460 | **L460** | ✅ |
| `_apply_missed_fix` | L512 起 | **L512** | ✅ |
| ring 分支 | L574–598 | **L574–596**（597–598 为统计 print） | ❌ 必改（锚点不符：收紧为 574–596） |
| 渲染调用 `_ring_put` | L4176–4178 | **L4176**（`_rn=_ring_ins_num`）/ **L4177**（判空）/ **L4178**（调用） | ✅ |
| `MISSED_FIX` | L313–320 | **L313–320** | ✅ |
| `ring_judge.py` `P_V1` | L19 | **L19** | ✅ |
| `P_V2` | L21 | **L21** | ✅ |
| `judge_v1` | L33 | **L33** | ✅ |
| `judge_v2` | L40 | **L40** | ✅ |
| `census_ring_digit.py` 默认路径 | L59–61 | **L59–61** | ✅ |
| `ring_at` | L141 | **L141** | ✅ |
| 输出 `json.dump(hits)` | L230 | **L230** | ✅ |
| `api_candidates_all_run.py` `JOB` | L7 | **L7** | ✅ |
| `PAYLOAD` | L8 | **L8** | ✅ |
| `submit` | L13 | **L13** | ✅ |
| `poll` | L24 | **L24** | ✅ |
| `parse` | L34 | **L34** | ✅ |
| `api_candidates_all_build.py` `main` | L13 | **L13** | ✅ |
| 文件行数 | 8007 | **8007** | ✅ |

> 复现：`grep -n 'RING_INS_BASE\|RING_SIZE\|def _ring_ins_num\|def _ring_put\|def _apply_missed_fix\|MISSED_FIX' src/pipelines/build_vert.py`；`grep -n 'P_V1\|P_V2\|def judge_v1\|def judge_v2' src/tools/ring_judge.py`；`grep -n 'LINES = \|COORDS = \|SRC = \|def ring_at\|json.dump(hits' src/tools/census_ring_digit.py`；`grep -n '^JOB\|^PAYLOAD\|def submit\|def poll\|def parse' src/tools/api_candidates_all_run.py`；`grep -n 'def main\|PER_PAGE\|PER_BATCH' src/tools/api_candidates_all_build.py`。

## 2. 判据核对（spec §1 vs 代码）

### 2.1 `ring_judge.py`

| 判据 | spec §1.3 描述 | 代码实测 | 判定 |
|---|---|---|---|
| 尺寸窗 | `w∈[w_lo,w_hi]×step`、`h∈[h_lo,h_hi]×step` | `P_V2 w_lo=14.5 w_hi=19.5 h_lo=11.5 h_hi=19.5`（**pt 绝对值**，非 ×step） | ⚠ 建议改（§3 第 1 行已自认；§1.3 应标「设计目标/当前 wz7 pt」） |
| 四边有墨 | `edge ≥ edge_min` | `edge_min=0.20`；`edge = min(四条边带)` | ✅ |
| 圈心有墨 | `ctr ≥ ctr_min` | `ctr_min=0.15`；`ctr=.35–.65` 中心区 | ✅ |
| 非实心 | `fill ≤ fill_max` | `fill_max=0.85` | ✅ |
| 长宽比 | `ar ∈ [ar_lo,ar_hi]` | `ar_lo=0.6 ar_hi=1.7` | ✅ |
| hole | 仅 v1 回归对照、新书不用 | `P_V1 hole_min=0.10`；`judge_v2` **不看 hole** | ✅ |
| v1 | 回退用：hole + 边长 14–23 | `judge_v1`：hole/ctr/fill/ar + `size_lo=14.0 size_hi=23.0`（只量 w） | ✅ |
| 主块 | 仅取面积最大连通域 | `comps.sort(key=lambda d: -d['area'])`；`main=comps[0]` | ✅ |

### 2.2 `census_ring_digit.py`

| 项 | spec | 代码 | 判定 |
|---|---|---|---|
| 窗口 | 列末**一格** `[y1−step, y1]`，左右小边距 | `ya=c['y1']-step`；clip `x0−1 … x1+1` | ✅ |
| step | 本页**长列**「框高/字数」中位 | `_page_step`：`len(t) < 8` 跳过，取中位 | ✅（阈值 n≥8 与 spec「字数 ≥ 阈值」一致） |
| 灰度 | 「局部偏移自标定，不写死灰度差」 | **固定** `g < median(g) − 20`（L154） | ⚠ 建议改（§3 第 3 行已承认；§1.3 应标 planned） |
| DPI | 默认 600，可 `VERT_RING_DPI=900` | `DPI=int(env or 600)` | ✅ |
| 默认路径 | 硬编码 wz7 | L59–61 硬编码 `data/wz7_full/...`、`source_pdf/wz7.pdf`；输出 `tmp_vert/cj5/...` | ✅（§3 第 5 行属实） |

### 2.3 `_apply_missed_fix`（ring 分支）

| 行为 | spec §1.2/§1.3 | 代码 | 判定 |
|---|---|---|---|
| 分组 | 按 `(page, col)` 分组；小容差匹配 | `groups[(page, tuple(col))]`；列框 `all(abs(a-b)<=0.6)` | ✅（容差 0.6pt 固定；§1.2 说「见 §4」但 §4 无此锚点 → ⚠ 建议改） |
| situation 1 | 文本尾 1–2 位数字 **1:1 换**占位符 | `re.search(r'[0-9０１２３４５６７８９]{1,2}$')`；`cur[:_tail.start()] + sent` | ✅（行为对；**长度描述错**，见下） |
| 长度 | 「文本长度 **0 变化**」（§1.2） | 1 位 → 0；**2 位 → −1**（本书 352/352 全是 2 位） | ❌ **必须改** |
| situation 1 无尾数字 | 不变量要求尾部数字 | 打日志后**改走情形②追加** | ⚠ 建议改（§1.2 应写明 fallback） |
| situation 2 | 列尾追加 1 个占位符 | `cur + sent`；`st['ring2'] += 1` | ✅ |
| 一个 ring 一个占位符 | 是 | 每条目一次 `+ sent` / 替换 | ✅ |
| 去重 | 数据键 `(page, 列框容差, number)` | 运行时只按 `(page, col)` 分组，**不按 number 去重**（依赖数据已去重） | ✅（§3 第 11 行如实；§1.3 第 4 步可补一句） |
| number 范围 | 1–99 | 数据 8–99；`_ring_ins_num` 接受 `base+1..base+200` | ✅（数据范围对；代码上限更宽，建议注明） |

### 2.4 渲染（`_ring_put`）与验证

| 项 | spec §1.3 第 4/5 步 | 代码 | 判定 |
|---|---|---|---|
| ≤50 | Unicode 圈码字形（①–⑳/㉑–㉟/㊱–㊿），整圆、不横压 | `_CIRCLED_CP` 查表 → `_put_tex(ch, …, Fr, xs=1.0)` | ✅ |
| >50 | `○` + 小号数字合成 | `○` + `digs`（`Fd=F*0.45`，逐位） | ✅ |
| 字号 | `RING_SIZE × 正文字号` | `Fr = max(6.0, round(F*RING_SIZE,1))`；默认 0.95 | ✅ |
| 位置 | 该格中心 | `top + (k+0.5)*step` | ✅ |
| 文本层 | ≤50 圈码字形 / >50 ○+数字 | 同（`_put_tex` 出文本层） | ✅ |
| 验证 | verify 页数/字符量/越界；无 ring 专用自动对比 | `verify_vert.py` 无 ring 分支（grep 0 命中） | ✅（§3 第 12 行如实） |

## 3. 参考基线数字核对（spec §2 vs 来源报告）

| spec §2 数字 | 来源报告实测 | 判定 |
|---|---|---|
| 184 处/42 页 → 352 处/50 页（+168） | battle1 L11/L140–142：184→352，+168 全部年表段，段外 0 | ✅ |
| 367 条 = 352 situation 1 + 15 situation 2；331 `how=ring_digit` + 36 人工 | fix JSON：**367 / 352 / 15 / 331 / how 缺省 36**；battle1 L222、battle4 L34 同 | ✅ |
| 34 处（t18 17 + t19 4 + t20 13）；27 处违反，t19 后余 14 | battle4 L17–18：34；27 违反；余 14 | ✅ |
| 60 页 4700×7225（6.65 px/pt）；21 处改判；16 起→2 | battle5 L16–18/L37：60 页、4700×7225、21 改判、16 起→2 | ✅ |
| 模板 LOO top-1 230/348=66%；16/34；361/367 | battle5 L39：230/348=66%、16/34、361/367 | ✅ |
| 独立验收 PASS；21 改判误判 0；78/76/77/76 清晰 | battle5_acceptance L14–17/L35；battle10_backlog L15–20 | ✅ |
| 页边界 p1720 78→p1721 76、p1721 77→p1723 76；页内 76→77、76→78 | battle5_acceptance L35、battle10_backlog L15–20 逐项一致 | ✅ |
| 圈 15.0–18.8 × 12.7–18.0 pt；步进 19.3；0.95×正文 | battle1 §5.5 表（600dpi 15.00–18.84 / 12.72–18.00） | ✅ |
| PaddleOCR-VL 成本 60 页（8 条/页、30 页/批≈2 批；71.6s/批≈2–4 分钟） | battle9 §2/§6：71.6s/批 ✅；但 **367/8 ≈ 46 页**，非 60 页 | ⚠ 建议改（页数算错或口径未写清） |

> 日期/来源：§2 每行都有「日期 + 来源报告」，齐全 ✅；书目 wz7 明确 ✅。
> 唯一数字问题：成本行「60 页」与 8 条/页不自洽（46 页）；其余 8 组全部与来源报告一致。

## 4. §3 换书清单 13 行核对

| # | spec 现状 | 代码/仓库实测 | 判定 |
|---|---|---|---|
| 1 | `P_V2` 默认 wz7 pt | ✅ 绝对值 14.5/19.5/11.5/19.5 | 属实 |
| 2 | 本页长列中位；列末一格 | ✅ `_page_step` n≥8 中位；`ya=y1-step` | 属实 |
| 3 | 代码 `median − 20` | ✅ census L154 `median(g)-20` | 属实 |
| 4 | 默认 600，`VERT_RING_DPI=900` | ✅ L66 env | 属实 |
| 5 | 硬编码 `data/wz7_full/...`、`source_pdf/wz7.pdf`、`tmp_vert/cj5` | ✅ L59–61、L230/233 | 属实 |
| 6 | 无 wrapper，人工搬 JSON | ✅ 仓库无 `ring_census.py` | 属实 |
| 7 | `api_candidates_all_build/run.py` 有 8 条/页、30 页/批；圈码专用 5 格条带 planned | ✅ `PER_PAGE=8 PER_BATCH=30`；无 ring 专用条带构造器 | 属实 |
| 8 | 模板 LOO 66%；battle5 人工 21；API 圈码条带未接 | ✅ 与 battle5/§3 第 7 行一致 | 属实 |
| 9 | 序列非降+LNDS；页边界例外；**已实现** | 方法在 battle4/5 跑通，但 **`src/tools/` 无 LNDS/非降工具**（grep 0 命中） | ⚠ 建议改（状态改「ad-hoc 已跑通，无复用工具」） |
| 10 | class=ring；1 替换/2 追加；≤50 Unicode、>50 合成；RING_SIZE 默认 wz7 比例 | ✅ 全对（RING_SIZE 0.95） | 属实 |
| 11 | 无独立 merge 工具 | ✅ 仓库无 | 属实 |
| 12 | verify 无 ring 专用自动对比 | ✅ `verify_vert.py` 无 ring | 属实 |
| 13 | wz7 367 条；换书必须重新普查 | ✅ 367（本书数据） | 属实 |

## 5. 三档清单（汇总）

### 必须改（3）
1. **§1.2 / §1.3 的 situation 1 文本长度**：从「0 变化」改为「1 位数字 0；2 位数字 `sl` −1；渲染层 ≤50 净 −1、>50（○+2 位）净 +1」。本书 352/352 situation 1 全是 2 位数字，现文与实测（字符量账）矛盾。
2. **§1.3 第 5 步「替换 1 字→1 圈码字形」**：按位数写清（1 位→1；2 位→1（≤50）或 3（>50，○+两位）），否则与 verify 字符量对账口径冲突。
3. **§4 ring 分支锚点**：`L574–598` → `L574–596`（597–598 是统计 print，不属于分支）。

### 建议改（6）
1. §1.3 尺寸窗 `×step` vs 代码 pt 绝对值：标注「设计目标；当前实现为 wz7 pt，见 §3 第 1 行」。
2. §1.3 灰度「自标定」vs 代码固定 `median−20`：标注 planned（与 §3 第 3 行呼应）。
3. §1.2 容差「见 §4」：§4 无该锚点；补「运行时 0.6pt 固定」或加锚点。
4. §2 成本「60 页」：367/8 ≈ 46 页；改为 ~46 页或写清 6 条/页口径。
5. §3 第 9 行「已实现」：sequences 无复用工具，改为「battle4/5 ad-hoc 已跑通，工具待抽出」。
6. §1.2 不变量「situation=1 ⇒ 尾部数字」：代码有 fallback（无尾数字改走追加+日志），补一句。

### 接受
- §4 其余锚点（12 组）全部实测命中；文件行数 8007 ✅。
- §1 判据主体（v2 尺寸/edge/ctr/fill/ar、v1 hole 仅回退、窗口/step/最大连通域、situation 1 替换/2 追加、>50 合成、RING_SIZE 0.95、格心、不横压、文本层）与代码一致。
- §2 参考基线 8 组数字与 battle1/4/5/10 逐项一致（184→352、367=352+15、331+36、34、21、16→2、66%、78/76/77/76、361/367、4700×7225/6.65、圈尺寸/步进、日期/来源齐全）。
- §3 换书清单 13 行除第 9 行状态外全部属实（硬编码路径、DPI、median−20、API 8/30、无 wrapper、无 merge、verify 无 ring、367 数据）。

## 6. 复现命令（复核用）

```bash
cd /opt/test
grep -n 'RING_INS_BASE\|RING_SIZE\|def _ring_ins_num\|def _ring_put\|def _apply_missed_fix\|MISSED_FIX' src/pipelines/build_vert.py
sed -n '574,596p' src/pipelines/build_vert.py
sed -n '4176,4178p' src/pipelines/build_vert.py
grep -n 'P_V1\|P_V2\|def judge_v1\|def judge_v2' src/tools/ring_judge.py
sed -n '14,55p' src/tools/ring_judge.py
grep -n 'LINES = \|COORDS = \|SRC = \|def ring_at\|json.dump(hits\|median(g)' src/tools/census_ring_digit.py
grep -n '^JOB\|^PAYLOAD\|def submit\|def poll\|def parse' src/tools/api_candidates_all_run.py
grep -n 'def main\|PER_PAGE\|PER_BATCH' src/tools/api_candidates_all_build.py
wc -l src/pipelines/build_vert.py
/usr/bin/python3 - <<'PY'
import json
d=json.load(open('docs/vert_taskF_missed_fix.json'))
r=[i for i in d['items'] if i.get('class')=='ring']
print('ring',len(r),'s1',sum(1 for i in r if i['situation']==1),
      's2',sum(1 for i in r if i['situation']==2),
      'how_digit',sum(1 for i in r if i.get('how')=='ring_digit'),
      'no_how',sum(1 for i in r if not i.get('how')),
      '2digit_s1',sum(1 for i in r if i['situation']==1 and len(str(i['number']))==2),
      'gt50',sum(1 for i in r if i['number']>50))
PY
```

## 7. 约束声明

- 本报告只复核、未改 `spec/vertical/18_ring_digit_census.md`、`src/`、`docs/vert_taskF_missed_fix.json`、`output/`；未 commit/push；token 未出现。
