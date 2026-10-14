# 竖排架构正式化报告

> 任务简报：`docs/vert_arch_task.md`　完成日期：2026-10-15
> 范围：把已完成的竖排管线 `src/pipelines/build_vert.py`（v2，wz6 全书 231 页）**扶正为系统一等公民**——
> 架构文档条目、6 份分部 spec、回归验证脚本、OCR 方向参数试验脚本。
> **未改任何渲染逻辑**（未动 `build_vert.py` / `build_geom.py` / `build_classic.py` / 四书数据 / 测试）。

## 一、做了什么

| # | 交付物 | 状态 |
|---|---|---|
| 1 | `spec/00_system_architecture.md`：文档类型表加「竖排书」行 + 「各类型专属逻辑」竖排小节 + 测试体系/测试数据/技术栈/目录结构补充 | 完成 |
| 2 | `spec/vertical/`：`README.md` + 6 份分部 spec（engine / tate_layout / marginalia / frame_lines / pagenum_sequence / derot） | 完成 |
| 3 | `spec/README.md`：implemented 区 + 分部 spec 表 + 文档类型表 + 运行命令 + 术语表 | 完成 |
| 4 | `src/test/verify_vert.py`：竖排回归验证（页数 1:1 / 逐页字符量 / 越界 / PASS-FAIL 退出码），**实测 PASS** | 完成 |
| 5 | `src/tools/test_ocr_orientation.py`：OCR `useDocOrientationClassify` 参数对比脚本（token 缺失，只交付脚本） | 完成（待 token 验证） |
| 6 | 本报告 | 完成 |
| 附 | `spec/architecture_audit.md` 的「竖排能力缺口」加状态更新注（保留审计时点记录） | 完成 |

## 二、关键决策

1. **spec 按「机制」而非「流程」分节**（对齐 ancient/modern 的粒度）：引擎链、tate 参数语义、边缘小字、
   版框线、页码序列、旋转页 —— 每条都写「实测背景 → 方案 → 实现锚点（函数名 + 行号）→ 验收方法 → 遗留」，
   实现锚点全部落到 `build_vert.py` 的具体行号（基于 commit `ff4b5b7`，924 行），后续重构可按锚点对账。
2. **竖排验证不做 pitch/页高**：横排 `verify_geom.py` 的指标（相邻行 y 差、正文块高）在竖排语义下不成立
   （竖排的「行」是列）。竖排改用**与渲染机制无关、对源书 1:1** 的三项硬指标：
   页数 1:1 / 逐页字符量对照 / 全书 span+矢量越界，加可选页幅对照。这也让脚本不依赖坐标尺度
   （竖排 OCR 是 2x px，`verify_geom` 那套 DPI 自适应在这里不需要）。
3. **预期差异页不硬编码页号**：wz6 有 2 页天然不该被"还原"（p74 = OCR 把图例读成 194 字长行、
   p231 = Anna's Archive 水印页）。判定改为**看该页 OCR 内容特征**：
   - OCR 噪声页 = 非空白字符 ≥ 30 且 CJK 占比 < 0.5（命中 p231，占比 0.00）；
   - OCR 幻觉长行页 = 存在单条 OCR 行 ≥ 80 字（命中 p74，最长 137 字；竖排单列满列也就 40 字上下）。
   命令行另给 `--expect-low 74,231` 作为显式声明通道（与自动识别取并集），两者都不写死页号在代码里。
4. **越界检查同时覆盖文本与矢量**：版框线是 `\rule` 画的矢量图形（不是文字），只查 span 会漏掉
   「版框画到页外」这类失败。实测两者都是 0。容忍 0.5pt（PDF 坐标零头/描边半宽不误报）。
5. **页幅对照作为可选硬项**：竖排的右缘公式 `70 + om + textheight` 依赖精确页高，纸型错了整页列位全错。
   比较「输出纸型 vs 源书**众数**页幅」——源书自身有 115 页扫描页高差 1.25pt（奇偶页扫描差异）、
   1 页 Letter 尺寸，不能逐页严比，只能比众数（实测相对差 0.00%）。

## 三、验证结果

### 3.1 `verify_vert.py` 实测（wz6 全书，退出码 0 = PASS）

```bash
/usr/bin/python3 src/test/verify_vert.py output/wz6/wz6_vert_full.pdf \
  data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json --src-pdf source_pdf/wz6.pdf
```

```
页数: 源 OCR 231 页  |  输出 PDF 231 页  |  ✓ 1:1
字符量: 输出 68016 / OCR 69998 = 97.2%
  [预期差异] p74 输出 263 / OCR 405 (差 142) — OCR 幻觉长行页(单行 137 字)
  [预期差异] p231 输出 0 / OCR 896 (差 896) — OCR 噪声页(非中文: CJK 占比 0.00)
  差异 > 80 字的页: 2 个（预期 2 / 非预期 0）；整页丢失(0 字)页: 0 个
越界: span 0 个 / 矢量图形 0 个（容忍 0.5pt；涉及 0 页）
页幅: 源书众数 595.28x1245.31pt（116/231 页）  |  输出 595.27x1245.33pt  |  相对差 0.00%/0.00%

== 字符量差异最大的 12 页 ==
  page key  out_n  src_n  diff  src行数 最长行 CJK占比  标记
   231  230      0    896   896     21   110    0.00  预期
    74   73    263    405   142     14   137    0.99  预期
   227  226    375    423    48     19    35    0.97
   158  157    700    742    42     26    40    0.93
   191  190    235    277    42     16    35    0.95
   228  227    732    771    39     26    38    0.94
   156  155    722    759    37     25    37    0.95
   79   78    255    271    16     15    25    0.98
   101  100    276    292    16     15    27    0.98
    45   44    276    290    14     16    27    0.95
    11   10    241    254    13     17    23    0.96
    46   45    301    313    12     14    25    0.95

== 退出码 PASS ==
```

与 `docs/vert_v2_report.md` 的验收数据完全一致（231:1、字符量 69998/68016 = 97.2%、越界 0），
说明脚本口径与当时的验收方法对得上。

**负例（确认退出码不是恒 0）**：

| 输入 | 结果 | 退出码 |
|---|---|---|
| `output/wz6/wz6_vert_preview.pdf`（8 页预览，应 231 页） | `[FAIL] 页数不 1:1: 源 231 vs 输出 8` + 4 个非预期缺字页 | 1 |
| 正常输出 + `--char-tol 5`（阈值收紧） | `[FAIL] 非预期大幅缺字页 76 个` | 1 |

### 3.2 试验脚本 `test_ocr_orientation.py`

- **无 token 时**：退出码 2 + 明确的三行提示（放 token 的命令、`--render-only` 自检命令）。
- **`--render-only` 实测通过**（不需要 token，验证本地渲染半边）：
  ```
  [render-only] 源 source_pdf/wz6.pdf -> /tmp/vert_orient dpi=200 (坐标口径 = 提交图 px)
    p159  /tmp/vert_orient/wz6_p159_200dpi.png  1654x3460 px  (595.3 x 1245.3 pt)
    p4    /tmp/vert_orient/wz6_p004_200dpi.png  1654x3456 px  (595.3 x 1244.1 pt)
  ```
- **判据已用真实 OCR 数据校准**（拿 wz6 已有的 p159 数据跑脚本里的 `poly_stats`，2x 尺度页宽 1190.6px）：

  | 页 | 行数 | 长行 | 横看行 | 越界行 | 最大 x | 高/宽比中位 |
  |---|---|---|---|---|---|---|
  | p159（旋转页） | 6 | 5 | **5** | **5** | **2411.3**（≈2× 页宽） | 0.037 |
  | p4（正常竖排页，对照） | 15 | 0 | 0 | 0 | 1180.3 | — |

  → 一旦 token 就绪，脚本在 false 档应复现该签名、true 档应转 0；结论逻辑（「参数有效 / 未消除 / 该页不是旋转页」）
  已按此签名写好。
- **结论留白**：`useDocOrientationClassify` 是否真能消除旋转坐标系，**待 token 就绪后跑此脚本验证**：
  ```bash
  echo '<API_TOKEN>' > /tmp/paddle_token
  /usr/bin/python3 src/tools/test_ocr_orientation.py --pages 159,4 --json /tmp/orient.json
  ```

### 3.3 回归（本任务不改渲染逻辑，跑一遍确认无扰动）

```
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q   ->  201 passed in 2.92s
ruff check src/test/verify_vert.py src/tools/test_ocr_orientation.py  ->  All checks passed!
```

## 四、遗留

1. **`useDocOrientationClassify` 未验证**（无 token）：脚本 + 判据已就绪；若验证通过，可**重跑受影响页的
   OCR 数据**从源头消除旋转坐标系，`derot_rows` 作为存量数据的还原层保留（两者不冲突：还原层对已修正的
   数据不会触发 —— 触发判据要求「横看行长行 ≥ 3 且所有长行都横看」）。
2. **竖排验证脚本不覆盖版式保真度**：页数/字符量/越界三项能拦「整页丢失/丢内容/画到页外」，
   但列位偏移、字号偏差、界行线 ±1 条这类**渐进式保真退化**拦不住（需要版框/列位对照，
   见 `docs/vert_v2_report.md` 的「边框复测」方法）。若后续要防这类回归，可在 `verify_vert.py`
   上加一项「版框内框/界行线 vs 源图墨迹」的抽样对照（本次未做，避免脚本依赖 scipy/源图墨迹检测逻辑）。
3. **`spec/vertical` 与实现的同步机制**：spec 的实现锚点是**行号**，`build_vert.py` 改动后行号会漂。
   建议改动该文件时同步更新 `spec/vertical/README.md` 的锚点表（同 AGENTS.md 的 spec 对账规则）。
4. **竖排尚未纳入两份治理文件**（本次未动，属主控决策）：
   - `spec/governance/PIPELINE_BEHAVIOR.md` 只覆盖横排两管线（geom/classic/v13），竖排的
     `SL CO OUT [SRC]` argv + `VERT_*` env 契约本次记在 `spec/vertical/README.md`；
     本任务未改任何接口（不触发 api-compat 对账），下次改竖排接口时应按 AGENTS.md §1 同步该文件。
   - `AGENTS.md` §3「测试要求」目前只列 `verify_geom.py` 作 PR 门禁；建议补一行
     「竖排：`verify_vert.py`（页数 1:1 / 字符量 / 越界）」+ §6 issue 清单登记竖排遗留
     （正文列长于内框、列距口径差 9%、逐页版面错位、界行线 ±1）。
5. `build_vert.py` 自身的预存在遗留（正文列长于内框、列距口径差 9%、逐页版面错位、界行线 ±1）
   **未动**，已如实记入 `spec/vertical/02_tate_layout.md` / `04_frame_lines.md` 的「已知遗留」。
