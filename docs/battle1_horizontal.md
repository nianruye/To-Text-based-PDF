# battle1 · 横排 local-bug 清零 —— 交付报告

> 任务：`t1 — 横排 local-bug 清零（#1/#2/#3/#5/#6/#7 + #4/#8/#9）`
> 执行：横排工程师　日期：2026-11-04　工作目录：`/opt/test`
> 基线 HEAD：`20d327e`（横排代码最后一笔 `bed0d25`，2026-07-24）
> **改动留在工作树（未 commit / 未 push）**；本文所有数字均为本机实测，命令附在 §7。

**结论一句话**：任务书列的 9 条里有 6 条（#1/#2/#5/#6/#7/#8）在 HEAD 已是修复态/安全形态（文档滞后），
本轮把真实残留的 **#3（identity replace）/#7（异常路径临时目录泄漏）/#9（docstring）/#6（单次 .get 显式化）/ #4（死参已消失，清理文档与未用 import）** 收口；
测试 **516 → 557 全绿（本任务 +41；同工作区竖排工程师并发新增 5 例 → 全量 562 也全绿）**；四书 geom + wz2 classic **改动前后逐页文本/行 bbox 0 差异、verify_geom JSON 逐字节相同**，
页数 1:1 / split 0 / missing 0，pitch 与基线完全一致（**97.8 / 79.7 / 99.6 / 98.7**；wz3 为历史 FAIL，理由见 §4.3）。

---

## 0. 关键前提：任务书/交接报告与 HEAD 的偏差（必须先说明）

`docs/HANDOFF_20261024.md` §2.5、`AGENTS.md` §6、`src/test/unit/PURE_FUNC_SPEC.md` 三处都把 #1/#2 描述成
「当前 unit 测试锁的是 bug 行为」「\\% 双反斜杠」「\textbackslash{} 的 {} 被二次转义」。实测 HEAD **不是这样**：

```bash
$ /usr/bin/python3 -c "import sys; sys.path.insert(0,'src'); from utils.tex_escape import _CLASSIC_PAIRS, escape_latex; \
  print([p for p in _CLASSIC_PAIRS if p[0]=='%']); print(repr(escape_latex('100%','classic')))"
[('%', '\\%')]
'100\\%'          # 单反斜杠（正确）
```

```bash
$ git log --oneline -S "占位反斜杠" -- src/pipelines/build_pdf_v13.py
bed0d25 feat: wz3 pitch优化 + 页眉/页码/分界线 + 甲骨文缺字贴图      # #2 修复在此 commit
$ git log -1 --format='%ci' bed0d25
2026-07-24 23:58:49 +0800
```

- `_CLASSIC_PAIRS` 从 `src/utils/tex_escape.py` 第一次入库（`bed0d25`）起就是 `('%', r'\%')`；
- `escape_tex` 从同一 commit 起就是「`\x00` 占位 → 其它规则 → 还原 `\textbackslash{}`」；
- 对应测试 `TestEscChars`（`a%b -> a\%b`）与 `TestEscapeTex.test_escape_tex_backslash`（`a\b -> a\textbackslash{}b`）
  锁的是**修复后**行为，不是 bug 行为；
- 同理 `line_font`/`FONT_HD`（#5）、`fit_common` 的 `DPI=200`（#8）、classic 的裸 `os.environ[]`（#6）在 HEAD 都不存在/已安全（§1 逐项给证据）。

**一句话**：交接文档停留在 `bed0d25` 之前的代码快照上；本轮以 HEAD 实测为准逐项核销，并把过时契约/账本改正（§5）。

---

## 1. 逐 issue 处置（根因 / HEAD 实测 / 本轮动作 / 证据 / 去向）

| # | 任务书要求 | HEAD 实测 | 本轮动作 | 去向 |
|---|---|---|---|---|
| 1 | `_CLASSIC_PAIRS` 的 `r'\\%'` 应为 `r'\%'` | 已是 `('%', r'\%')`（单反斜杠） | 反向验证（临时改回 bug → 测试红 → 还原 → 绿）；文档更正；测试加强 | **已修（HEAD 前已修）+ 防回归** |
| 2 | `escape_tex` 二次转义 `{}` | 已是 `\x00` 占位（无二次转义） | 同上反向验证；补 `\{\}` 反例断言 | **已修（HEAD 前已修）+ 防回归** |
| 3 | `is_heading_by_md` 两行 identity replace | **仍存在**（L143） | 删除；155 条语料 + 2 万条 fuzz 证明输出 0 差异；新增 `TestIsHeadingByMd` | **本轮修复** |
| 4 | `test_pitch_rate` 死参 | HEAD 已是 `test_pitch_rate(pdf)` / `run_all(pdf_path)`，**无死参** | 删除未用 `import os`；docstring 更正（说明真正的 pitch 率由 verify_geom 判） | **已消失（HEAD 前）+ 清理** |
| 5 | `line_font` 引用未定义 `FONT_HD` | `build_geom.py`/`build_classic.py` **已无** `line_font`/`FONT_HD` | `grep` + `ruff --select F821` 复核；不加代码 | **已删（HEAD 前）** |
| 6 | classic `POS_EST_LOG` 裸 `os.environ[]` | L1009 已有 `if os.environ.get(...)` 守卫，**不会 KeyError** | 改为单次 `.get` 存局部变量（语义不变，消除二次下标）；geom L1343 同模式已核 | **已安全（HEAD 前）+ 本轮显式化** |
| 7 | `fit_common` 临时目录泄漏 | 成功路径已有 `rmtree`；**异常路径仍泄漏**（本轮实测复现） | `main()` 主体包 `try/finally`；新增 `test_fit_common_cleanup.py`（异常路径红→绿） | **本轮修复（失败路径）** |
| 8 | `DPI=200` 死代码（fit_common 定义未引用） | fit_common **已无** DPI 定义；`build_geom.py` L24 / `build_classic.py` L23 的 `DPI=200` 立即传入 `calibrate()`，是活代码 | 不改代码，出证据 | **已消失（HEAD 前）** |
| 9 | classic/fit_common docstring 未改名 | classic 用法行仍写 `python3 build_geom.py`；fit_common 自称「bit-exact 复制原 fit_positional.py」 | 两处 docstring 改为现名 + 正确入口 | **本轮修复** |

### 1.1 #1 classic `_esc_chars` 双反斜杠（真实根因 + 现状）

- 根因（历史）：classic 的替换表把 `%` 映射成 `r'\\%'`（两个反斜杠）。LaTeX 里 `\\` 是换行，`\%` 才是百分号转义，
  所以 `100%` 会渲染成「100 + 换行 + 注释掉后文」。
- HEAD 实测（§0）：`escape_latex('100%','classic') == '100\\%'`（单反斜杠）。
- **同类项一并核对**：`_V13_PAIRS`/`_GEOM_PAIRS`/`_CLASSIC_PAIRS` 三张表里 `% # _ &` 全部是单反斜杠；
  `^`/`~` 引入的 `{}` 都在 `{`/`}` 规则**之后**才产生，不会被吞/二次转义；`_CIRC` 的 `\textcircled{N}` 同理（最后应用）。
- 反向验证（证明测试真能拦住回归）：把该表项临时改回 `r'\\%'` →

```
FAILED src/test/unit/test_pure_funcs.py::TestEscChars::test_esc_chars[a%b-a\\%b]
FAILED src/test/unit/test_pure_funcs.py::TestCrossFuncDivergence::test_escape_tex_vs_esc_chars[a%b]
2 failed, 31 passed, 100 deselected in 0.08s
```

  还原后同命令 33 passed（绿）。
- 本轮加强：新增 `test_esc_chars_percent_single_backslash`（断言输出 == `100\%` 且不含 `\\%`）、
  `test_esc_chars_long` 加 `assert r'\\%' not in out`、`TestEscapeSingleBackslashAllModes`（三模式 × `%#_&` 共 12 例）。
- 剩余分叉（#11，明确不做）：classic 先删 `\\`、保留单 `\`，所以输入本身已是 `\%` 时会被 `%` 规则再转义成 `\\%`。
  本轮对 5 本书 OCR 语料做了普查（82,464 行）：

```
wz1: '\\%'=1  '\\#'=0  '\\_'=0  '\\&'=0  '\\\\'=0
wz3: '\\%'=0  '\\#'=0  '\\_'=0  '\\&'=0  '\\\\'=0
wz4: '\\%'=0  '\\#'=0  '\\_'=0  '\\&'=0  '\\\\'=0
mgfdmg: '\\%'=0  '\\#'=0  '\\_'=0  '\\&'=0  '\\\\'=0
wz2: '\\%'=0  '\\#'=0  '\\_'=2  '\\&'=0  '\\\\'=0
```

  - wz1 那 1 处 `\%` 在 `$ 33\frac{1}{3}\% $` 数学内，走 `esc()` 的 math 分支（`_math_to_plain`），不受影响；
  - wz2 那 2 处 `\_` 是 p782 的 OCR 垃圾 JSON 元数据行（`"filename_decoded": "...\_u76d0..."`），不是正文。
  → 真实正文无「已转义」形态，#11 未触发；见 §6 风险 1。

### 1.2 #2 `escape_tex` 二次转义花括号

- 根因（历史）：先 `\` → `\textbackslash{}`，之后 `{`/`}` 规则又把新引入的 `{}` 转义成 `\{\}`。
- HEAD 实测：`escape_tex('a\\b') == r'a\textbackslash{}b'`（`\x00` 占位，末尾还原）。
- 反向验证：临时把 `escape_tex` 回退成「顺序替换」旧实现 →

```
FAILED src/test/unit/test_pure_funcs.py::TestEscapeTex::test_escape_tex_backslash
FAILED src/test/unit/test_pure_funcs.py::TestCrossFuncDivergence::test_escape_tex_vs_esc_chars[a\\b]
2 failed, 18 passed, 113 deselected in 0.08s
```

  还原后 20 passed。
- 本轮加强：`TestEscapeTex` 加 `a\\b`（两反斜杠各自转义）、`a\%`（反斜杠与 % 各转义一次）两组参数；
  新增 `test_escape_tex_backslash_braces_not_double_escaped`（断言输出不含 `\{\}`）与 `TestEscapeSingleBackslashAllModes.test_v13_backslash_not_double_escaped`。
- 影响面：`build_pdf_v13.py` 是归档管线（`spec/README.md` 标注「src/ 内孤立（零调用）」），本项不改变任何产物。

### 1.3 #3 v13 `is_heading_by_md` 引号 replace identity（本轮修复）

- 根因：`h_norm = h_norm.replace('“','“').replace('”','”')` 是恒等替换（无任何归一效果），
  且只作用在 heading 一侧，属"看起来在做引号归一、实际什么也没做"的死代码。
- 修法：**删除**两行（不改真实逻辑）。理由：v13 已归档零调用；若改成 `_QUOTE_MAP` 归一（ASCII `"` ↔ 弯引号）会**改变匹配结果**，
  属行为变更，需 spec/基线，超出 local-bug 范围。
- 行为不变证明（改前源码 = `git show HEAD:src/pipelines/build_pdf_v13.py`，改后 = 工作树）：

```
$ /usr/bin/python3 /tmp/battle1/prove_heading_noop.py /tmp/battle1/v13_before.py src/pipelines/build_pdf_v13.py
语料 155 条 | 前后输出不同 0 条
fuzz 20000 条: identity replace 改变输出 0 条
```

  （语料覆盖：原文/去空白/首尾空白/ `$^{[一]}$` 脚注标记、10×10 引号组合、长度比模糊匹配、不匹配/空串；
  fuzz 为 2 万条含引号随机串——`str.replace(c, c)` 对任意字符串恒等，故两条 identity 行删除前后输出逐字节相同。）
- 新增测试 `TestIsHeadingByMd`（11 条精确匹配/模糊/边界参数 + 4 条引号形态 + 空 headings + None）锁定现状。

### 1.4 #4 `test_pitch_rate` 死参（HEAD 已消失）

- HEAD 实测：`def test_pitch_rate(pdf)`（test_cases.py L72），`run_all(pdf_path)` 只把 `pdf` 传进来；
  `coords_path/lines_path/src_pdf` 三个形参**已不存在**（该简化在 `bed0d25` 已发生）。
- 本轮动作（零行为风险）：删掉未使用的 `import os`（ruff F401）；把 docstring 改成事实描述——
  「真正的 pitch 达标率由 `verify_geom.py` 判，本函数只做 p11/p26/p51 下限检查」。
- 附带：文件头用法示例去掉不存在的 `--src` 参数（脚本只接受 1 个 argv）。

### 1.5 #5 `line_font` / `FONT_HD`（HEAD 已删）

```
$ grep -rn "line_font\|FONT_HD" src/pipelines/build_geom.py src/pipelines/build_classic.py || echo "(none)"
(none)
$ ruff check --select F821 --output-format=concise src/ src/calibration
All checks passed!
```

`line_font` 在 `bed0d25` 之前的 `build_classic.py` L254 存在（`return FONT_HD, True`，`FONT_HD` 从未定义），
`bed0d25` 重写这两个文件时已整体删除；现在 `build_pdf_v13.py` 里的 `line_font_styles` 是同名不同物的另一个变量，不是该函数。

### 1.6 #6 classic `POS_EST_LOG`（HEAD 已安全，本轮显式化）

- HEAD 实测（改前）：`if os.environ.get('POS_EST_LOG'): json.dump(..., open(os.environ['POS_EST_LOG'], 'w'))`
  —— 有 `.get` 守卫，未设置时不会 KeyError（任务书说的"裸 `os.environ[]`"在 HEAD 不成立）。
- 本轮改为单次取值，语义不变（仍只在设置时写文件）：

```python
_pos_est_log = os.environ.get('POS_EST_LOG')   # #6: 单次 .get 取值（未设置时不再二次下标；语义不变）
if _pos_est_log:
    json.dump(_pos_est, open(_pos_est_log, 'w'))
```

- 同类项：`build_geom.py` L1343 是同一模式（已安全，未改以缩小 diff）；`build_pdf_v13.py` 的
  `GEOM_FONT/GEOM_TARGET/GEOM_STRETCH/TOC_HEADING_MAP*/TOC_HEADING_MAP_OUT` 全部在 `.get()` 守卫内（逐行核对）。

### 1.7 #7 `fit_common` 临时目录泄漏（本轮修复异常路径）

- 根因：`main()` 在成功末尾 `rmtree`，但 `render()` 失败（`SystemExit('render 失败')`）、
  `fitz.open` 失败或任意异常都会跳过清理 → 每个失败构建泄漏一个 `/tmp/fitpos_*`。
- **真实复现**（不是构造）：本轮第一次 mgfdmg 重跑（/tmp/page_imgs 缺失 → xelatex 产物损坏 → `measure_heights` 抛
  `FileDataError: cannot open broken document`）后，`/tmp` 留下：

```
drwx------ 2 root root 4096 2026-11-04 00:28 /tmp/fitpos_i09s31qd/
-rw-r--r-- 1 root root 5582 est.json
-rw-r--r-- 1 root root   15 pass1.pdf
```

- 修法：`main()` 主体包 `try: ... finally: shutil.rmtree(tmp, ignore_errors=True)`，成功/异常/`SystemExit` 都清理。
  子进程（`render` 里的 build_geom/xelatex）是同步 `subprocess.run`，返回时已结束，不存在"清理时子进程还在写"的问题。
- 新增 `src/test/unit/test_fit_common_cleanup.py`（2 例：成功路径共用同一 tempdir 且被删；异常路径也被删）。
  红→绿证据：

```
# 回退到 HEAD（无 try/finally）
FAILED src/test/unit/test_fit_common_cleanup.py::test_tmp_cleanup_on_exception
1 failed, 1 passed in 0.03s
      （泄漏目录 /tmp/fitpos_wdx1gzxh）
# 恢复修复后
2 passed in 0.02s
```

### 1.8 #8 `DPI=200` 死代码（HEAD 已消失）

- `fit_common.py` 已无 `DPI` 定义（grep 无命中）。
- `build_geom.py` L24 `DPI = 200` → L29 `calibrate(sl, co, DPI, src_pdf=SRC)` → L30 `DPI = _G['DPI']`（自适应后真实 DPI）；
  `build_classic.py` L23/L28 同构。**是活代码**（四书构建日志首行 `[verify] DPI 自适应: 200` 可证），不动。

### 1.9 #9 docstring 未改名（本轮修复）

- `build_classic.py`：`用法: python3 build_geom.py ...` → 
  `入口: /usr/bin/python3 src/calibration/fit_positional_classic.py <spotting_lines> <spotting_coords> <out.pdf> [src.pdf]（两趟校准薄壳；直接跑本脚本只做单趟）`。
- `fit_common.py`：改为自我命名 + 说明由来（「本模块由原 fit_positional.py / fit_positional_classic.py 的重复实现合并而来（issue #17）；
  两个入口仍保留为 3 行薄壳」）。
- `src/utils/tex_escape.py` 模块 docstring 同步更正 #1/#2 的过时描述（原文写着"疑似bug，保留现状"）。

---

## 2. 改动清单（文件 → 内容 → 行为影响）

| 文件 | 改动 | 行为影响 |
|---|---|---|
| `src/utils/tex_escape.py` | 仅模块 docstring：#1/#2 已修说明 + #11 已知分叉登记 | **无**（代码 0 行变化） |
| `src/pipelines/build_pdf_v13.py` | `is_heading_by_md` 删 2 行 identity replace + 注释 | **无**（§1.3 证明；v13 归档零调用） |
| `src/pipelines/build_classic.py` | docstring 入口名；`POS_EST_LOG` 单次 `.get` 局部变量 | **无**（语义不变） |
| `src/calibration/fit_common.py` | `main()` 加 `try/finally` 清理；docstring | 成功路径无变化；异常/失败路径现在也清理 tempdir |
| `src/test/test_cases.py` | 删未用 `import os`；`test_pitch_rate` docstring；用法行 | **无**（测试工具文档/静态清理） |
| `src/test/unit/test_pure_funcs.py` | 新增 `TestIsHeadingByMd`；#1/#2 参数与回归断言；v13 fixture 加 `is_heading_by_md` | 测试 |
| `src/test/unit/test_audit_features.py` | 新增 `TestEscapeSingleBackslashAllModes`（三模式 × `%#_&`） | 测试 |
| `src/test/unit/test_fit_common_cleanup.py` | **新增**：tempdir 成功/异常两路径清理 | 测试 |
| `src/test/unit/PURE_FUNC_SPEC.md` | 更正 escape_tex（#2）、classic `_esc_chars`（#1）、对比表；新增 `is_heading_by_md`；刷新行号锚点；12→14 函数 | spec 对账 |
| `AGENTS.md` | §6 #1-#9 状态列全部更新为实测结论 | 治理账本 |
| `spec/README.md` | implemented 表加本报告行；PURE_FUNC_SPEC 描述 12→14 函数 | spec 账本 |
| `docs/battle1_horizontal.md` | 本报告 | — |

> 工作树里另有**竖排工程师**未提交的改动（`src/tools/census_ring_digit.py`、`src/tools/ring_judge.py`、
> `src/tools/merge_ring_digit.py`、`src/test/unit/test_census_ring_judge.py`、`docs/battle1_vertical_ring.md`、
> `docs/vert_taskF_missed_fix.json`），**不是本任务的 changedPaths**，本轮未触碰。

---

## 3. 测试证据

### 3.1 基线（改动前）

```
$ /usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
516 passed, 836 warnings in 18.87s
```

### 3.2 红→绿（证明测试真能拦住回归）

| issue | 回退动作 | 红（结果） | 恢复后 |
|---|---|---|---|
| #1 | `('%',r'\%')` → `('%',r'\\%')` | `2 failed, 31 passed`（TestEscChars[a%b] + CrossFunc[a%b]） | 33 passed |
| #2 | `escape_tex` → 顺序替换旧实现 | `2 failed, 18 passed`（test_escape_tex_backslash + CrossFunc[a\b]） | 20 passed |
| #7 | `fit_common.main` 去掉 `try/finally` | `1 failed, 1 passed`（异常路径泄漏 `/tmp/fitpos_wdx1gzxh`） | 2 passed |

（三次回退均已用 `git checkout --`/备份还原，最终工作树为修复态；见 §1 各条。）

### 3.3 最终（改动后）

```
$ /usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
562 passed, 836 warnings in 18.32s
# 排除同工作区竖排工程师并发新增的 test_census_ring_judge.py（5 例，非本任务）：
$ /usr/bin/python3 -m pytest src/test/unit src/test/invariants -q --ignore=src/test/unit/test_census_ring_judge.py
557 passed, 836 warnings in 18.04s
```

**516 → 557（本任务 +41 例）**：`TestIsHeadingByMd` 17 + `TestEscapeSingleBackslashAllModes` 16 +
`TestEscapeTex` 新增 2 参数 + 1 断言 + `TestEscChars` 新增 1 参数 + 1 断言 + `TestLongInput` 新增 1 + `TestFitCommonCleanup` 2。
全量 562 中的另外 5 例来自竖排工程师的 `test_census_ring_judge.py`（并发工作，不属于本报告改动，见 §2 末注）。

### 3.4 静态复核

```
$ ruff check --select F821 --output-format=concise src/ src/calibration
All checks passed!                      # 无 F821 未定义名（#5 类问题清零）
$ grep -rn "line_font\|FONT_HD" src/pipelines/build_geom.py src/pipelines/build_classic.py
(none)
```

identity replace 扫描（`src/**/*.py` 代码文本）：**0 处**代码级恒等 replace；仅 `test_pure_funcs.py` 的
2 处 docstring 里引用了旧代码原文（说明用）。

---

## 4. 回归证据（四书 geom + wz2 classic，改动前/后各跑一遍）

### 4.1 构建（串行；同一脚本、同一 env、同一输入）

| 书 | 入口 | 页数 | 改动前耗时 | 改动后耗时 |
|---|---|---|---|---|
| wz1 | `fit_positional.py`（geom）| 222 | 29s | 27s |
| wz3 | `fit_positional.py`（geom，linelevel 数据）| 850 | 77s | 78s |
| wz4 | `fit_positional.py`（geom）| 677 | 100s | 99s |
| mgfdmg | `fit_positional.py`（geom，源=wz5.pdf）| 407 | 28s | 28s |
| wz2 | `fit_positional_classic.py`（classic）| 783 | 15s | 12s |

两趟校准的 ratio 行逐字节相同（例：wz1 `[校准] 210 页 ratio: 中位0.941 [0.76,1.52]`、wz3 `842 页 0.929 [0.53,1.47]`、
wz4 `677 页 0.930 [0.77,1.12]`、mgfdmg `404 页 0.936 [0.78,1.06]`、wz2 `780 页 1.430 [0.52,2.38]`）。

> mgfdmg 说明：文档基线 env 依赖 `/tmp/page_imgs/p{0,1,2}.png` 与 `/tmp/mgfdmg_toc_rules.json`（/tmp 随 WSL 重启已丢）。
> 本机用 `src/tools/make_page_images.py`（源 `source_pdf/wz5.pdf`，`--pages=0,1,2`）与
> `src/tools/extract_toc_rules.py` 重新生成后按文档 env 构建；改动前后**使用同一份资产**，pitch 与基线 98.7 完全一致。

### 4.2 产物 diff（逐页文本 + 逐页行 bbox；脚本 `/tmp/battle1/cmp_pdf.py`）

```
wz1  : pages 222=222 | 文本不同页 0 | 行bbox不同页 0
wz3  : pages 850=850 | 文本不同页 0 | 行bbox不同页 0
wz4  : pages 677=677 | 文本不同页 0 | 行bbox不同页 0
mgfdmg: pages 407=407 | 文本不同页 0 | 行bbox不同页 0
wz2_classic: pages 783=783 | 文本不同页 0 | 行bbox不同页 0
```

（PDF 文件 md5 因 xelatex 写入时间戳而不同，文本层与行几何完全一致。比较行 bbox 保留 2 位小数。）

`verify_geom --json` 的**逐页原始指标 JSON 改动前后逐字节相同**：

```
wz1        verify.json md5 7883b25ca71578c3382b9b4b65d9c69a  IDENTICAL
wz3        verify.json md5 7ca85fadb91b0a32e812c8e5ab8ea131  IDENTICAL
wz4        verify.json md5 2d8bf97f0f0b246eac21d48927e1d4e1  IDENTICAL
mgfdmg     verify.json md5 348a0e9abea61c2e0762ed11d70b9bd3  IDENTICAL
wz2_classic verify.json md5 31173ea47bce22cd883f2101bd39f97b IDENTICAL
```

### 4.3 verify_geom 门禁（`VERIFY_PITCH_FLOOR=85`，命令行见 §7）

| 书 | 页数 1:1 | pitch 达标率 | 溢成多页的源页 | 缺失页 | 退出码 |
|---|---|---|---|---|---|
| wz1 | 222 = 222 | **97.8%**（基线 97.8）| **0** | **0** | PASS |
| wz3 | 850 = 850 | **79.7%**（基线 79.7）| **0** | **0** | **FAIL（历史固有，见下）** |
| wz4 | 677 = 677 | **99.6%**（基线 99.6）| **0** | **0** | PASS |
| mgfdmg | 407 = 407 | **98.7%**（基线 98.7）| **0** | **0** | PASS |
| wz2（classic）| 783 = 783 | 58.9%（classic 历史值）| **0** | **0** | FAIL（classic 非本门禁口径） |

- **wz3 的 FAIL 是历史固有**（交接报告 §2.2 已写明「79.7% 历史固有，不是回归；门槛就是它」；根因是旧 OCR 数据
  `cw=122` 多行合并 → split_polys 拆行坐标噪声，属待重跑 OCR 的 P0 事项）。本轮 pitch 与基线**逐 0.1% 相同**：
  用 `VERIFY_PITCH_FLOOR=79` 复跑同产物 → **退出码 PASS**（0 split / 0 missing / 79.7%），证明 FAIL 仅来自 85% 的全局下限，
  与本次改动无关。
- 硬约束（页数 1:1 / split 0 / missing 0）**四书全部满足**。
- 附：classic 侧另跑 `src/test/test_cases.py`（21 条功能断言）于 wz2 产物：**改动前 21 PASS / 0 FAIL，改动后 21 PASS / 0 FAIL**。

---

## 5. spec / 文档对账

1. `src/test/unit/PURE_FUNC_SPEC.md`（本轮更正，行为契约由此为准）：
   - `escape_tex`：删掉「副作用：`a\b -> a\textbackslash\{\}b`（二次转义）」，改为「`a\textbackslash{}b`（#2 已修）」+ 多反斜杠用例；
   - classic `_esc_chars`：`双反斜杠` → **单反斜杠**（#1 已修），补 `"a\\%b" -> "a\%b"`；
   - 对比表：`a%b`/`#` 由「不一致」改为**一致**（单反斜杠）；
   - 新增 `is_heading_by_md` 契约（含「引号不归一 = #3 现状」）；
   - 全部函数行号锚点按当前源码刷新（`_esc_chars` L174-176、`esc` L178-200、`is_heading_by_md` L136-150 等）；
   - 函数计数 12 → 14（原文档自身也少算）。
2. `AGENTS.md` §6：`#1-#9` 状态列改为实测结论（已修/已核/已删 + 证据摘要），`#10/#11` 保持 planned（本轮明确不做）。
3. `spec/README.md`：implemented 表加入本报告；`PURE_FUNC_SPEC` 描述 12 → 14 函数。
4. `spec/governance/PIPELINE_BEHAVIOR.md`：**未改**——本轮无 argv/env/JSON/GMPG/tmp 路径变更，
   转义行为与改动前逐字节相同（§4.2），契约 1-6 无需变动（符合 AGENTS.md §4「行为不变则 spec 状态不改」）。
5. `docs/HANDOFF_20261024.md` 保持原样（dated snapshot）：其 §2.5 对 #1/#2/#5/#6/#7/#8 的描述已过时，以本报告 + AGENTS.md 为准。

---

## 6. 剩余风险（如实登记）

1. **#11 `_esc_chars` 两方分叉未修（按任务书禁止）**：classic 删 `\\` 保留单 `\`，输入已是 `\%` 时会被再转义成 `\\%`。
   5 本 OCR 语料普查：`\%` 仅 1 处（wz1，在 `$...$` 数学内，走 math 分支不触发）、`\_` 仅 2 处（wz2 p782 OCR 垃圾 JSON 元数据行）。
   真实正文无此形态；是否统一需 spec/用户拍板。
2. **#10 `/tmp/seg2_line.*` 并发冲突未修（按任务书禁止）**：本轮**实际踩到**——为省时间把 wz2 classic 与四书 geom 并行启动，
   两者共用 `/tmp/seg2_line.tex/pdf`，发现后立即 kill 并改为全串行重跑（§4 数据均来自串行运行）。这印证 #10 的真实风险。
3. **wz3 pitch 79.7% FAIL 为历史遗留**：根因是 wz3 旧 OCR 数据（cw=122 多行合并）→ split_polys 拆行噪声，
   需重跑 OCR（交接报告 P0 第 1 条），不属 local-bug 范围。本轮 pitch 与基线相同、硬约束全过。
4. **mgfdmg 复现依赖 /tmp 资产**：`/tmp/page_imgs/p{0,1,2}.png` 与 `/tmp/mgfdmg_toc_rules.json` 不在仓库内（/tmp 易失）。
   本轮已给出重新生成命令（§7）；若缺少资产直接跑会构建失败（历史上就是这次失败暴露了 #7 的泄漏）。
5. **SIGKILL 无法清理 tempdir**：`try/finally` 覆盖异常/`SystemExit`，但 SIGKILL 下 Python 无法执行任何清理
   （本轮 kill 并发构建后残留 2 个 `/tmp/fitpos_*`，已手工删除）。这属 OS 语义，非代码缺陷。
6. **v13 管线仍归档零调用**：#2/#3 的修复不影响任何现有产物；若将来启用 v13，引号归一（#3 的"真实逻辑"）需另开 spec 决定。
7. **文档残留**：`docs/HANDOFF_20261024.md`、`docs/cards/*`、`docs/pipeline_audit.md` 仍有过时行号/描述（历史快照）。
   活账本（AGENTS.md / spec/README.md / PURE_FUNC_SPEC.md）已更新。

---

## 7. 复现命令（全部 `/usr/bin/python3`）

```bash
cd /opt/test

# 测试
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q          # 557 passed（本任务口径；含竖排并发用例的全量为 562）

# 四书 geom 构建（串行；示例 wz1）
LAYOUT_HEADINGS=1 LAYJSON="data/wz1/wz1.pdf_by_PaddleOCR-VL-1.6 .json" \
PAGENUM_GLOBAL_TABLE=data/wz1/wz1_full_pagenum.json FONT_SUBTITLE=kai \
/usr/bin/python3 src/calibration/fit_positional.py \
  data/wz1/wz1_spotting_lines.json data/wz1/wz1_spotting_coords.json \
  output/wz1/wz1_final.pdf source_pdf/wz1.pdf

# wz3 / wz4（默认 env）
/usr/bin/python3 src/calibration/fit_positional.py \
  data/wz3/wz3_linelevel_spotting_lines.json data/wz3/wz3_linelevel_spotting_coords.json \
  output/wz3/wz3_final.pdf source_pdf/wz3.pdf

# mgfdmg（源是 wz5.pdf；先重建 /tmp 资产）
/usr/bin/python3 src/tools/make_page_images.py source_pdf/wz5.pdf \
  data/mgfdmg/mgfdmg_spotting_lines.json --out=/tmp/page_imgs --pages=0,1,2
/usr/bin/python3 src/tools/extract_toc_rules.py data/mgfdmg/mgfdmg_spotting_lines.json \
  data/mgfdmg/mgfdmg_spotting_coords.json --out=/tmp/mgfdmg_toc_rules.json
LAYOUT_HEADINGS=1 LAYJSON=data/mgfdmg/mgfdmg_layout_raw.json \
PAGE_IMAGE_PAGES=0,1,2 PAGE_IMAGE_PREFIX=/tmp/page_imgs/p \
FONT_TITLE=song FONT_SUBTITLE=hei TOC_RULES=/tmp/mgfdmg_toc_rules.json \
/usr/bin/python3 src/calibration/fit_positional.py \
  data/mgfdmg/mgfdmg_spotting_lines.json data/mgfdmg/mgfdmg_spotting_coords.json \
  output/mgfdmg/mgfdmg_final.pdf source_pdf/wz5.pdf

# wz2 classic（共享层验证：geom + classic 两管线）
LAYJSON=data/wz2/wz2.pdf_by_PaddleOCR-VL-1.6.json PAGE_FONT=1 POSITIONAL=1 \
PER_PAGE_PITCH=1 LAYOUT_HEADINGS=1 \
/usr/bin/python3 src/calibration/fit_positional_classic.py \
  data/wz2/wz2_spotting_lines.json data/wz2/wz2_spotting_coords.json \
  output/wz2/wz2_classic.pdf source_pdf/wz2.pdf

# verify_geom（四书）
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  output/wz1/wz1_final.pdf data/wz1/wz1_spotting_coords.json data/wz1/wz1_spotting_lines.json \
  --src-pdf source_pdf/wz1.pdf
# wz3 用 linelevel 数据、wz4 用 wz4_spotting_*、mgfdmg 用 wz5.pdf 作 --src-pdf

# #1/#2 反向验证（可选）：临时把 _CLASSIC_PAIRS 的 % 改回 r'\\%' / 把 escape_tex 改回顺序替换，
# 跑 pytest src/test/unit/test_pure_funcs.py -q -k "EscChars or EscapeTex or CrossFunc" 应 2 failed，然后还原。

# 说明：/tmp/battle1/cmp_pdf.py（逐页 get_text + 行 bbox(2 位小数) 比较）与
#       /tmp/battle1/prove_heading_noop.py（AST 提取新旧 is_heading_by_md 比对）是本轮临时脚本，
#       未入库；逻辑见 §4.2 / §1.3，可据此复现。

# #3 等价性证明
git show HEAD:src/pipelines/build_pdf_v13.py > /tmp/battle1/v13_before.py
/usr/bin/python3 /tmp/battle1/prove_heading_noop.py /tmp/battle1/v13_before.py src/pipelines/build_pdf_v13.py
```

---

## 8. 明确不做（out of scope，任务书已禁）

- **#11** `_esc_chars` 两方分叉统一（需 spec/用户拍板）；
- **#10** `/tmp/seg2_line.*` 改路径分 build_name（另一批）；
- 任何竖排文件（`build_vert.py`、`src/tools/vert_*`、`verify_vert.py`、`data/wz6`、`data/wz7*`）；
- commit / push / 改 master 历史。
