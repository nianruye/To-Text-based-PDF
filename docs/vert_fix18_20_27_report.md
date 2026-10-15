# 竖排收尾修复报告（#18 / #20 / #27）

> 任务简报：[docs/vert_fix_task.md](vert_fix_task.md)　完成日期：2026-10-15
> 范围：修掉竖排治理登记的 3 个新 issue —— #18 `build_vert.py` 无退出码 / #20 `VERT_TMP` 并发冲突 / #27 文档数字漂移。
> 硬要求：`verify_vert.py` 实测 PASS（231:1 / 字符量 / 越界不回归）+ 209 测试全绿 —— **两条都过**（第五节）。
> 约束：未改横排管线、未动 `build_vert.py` 渲染逻辑（只改退出码 / 临时目录 / 注释数字）、未动四书数据、未 `git reset`、未 commit（改动已 `git add`）。

## 一、结论速览

| # | issue | 修法 | 实测证据 | 状态 |
|---|---|---|---|---|
| 18 | `build_vert.py` 无 `sys.exit`：编译失败/输入缺失/产物未生成，退出码仍 0 | 分级：输入缺失 -> 显式报错 `exit(1)`；编译失败 -> `exit(1)`；**SRC 缺省的 3 参数调试调用 -> stderr 警告 + 退出码仍 0**；正常路径 `exit(0)` | 19/19 场景实测通过（§2.3）；判据经实测标定（§2.1） | 已修（AGENTS.md §6 已归档） |
| 20 | 并行两次构建共用 `vert.tex/dvi/pdf`（默认临时目录与产物名无关） | 默认临时目录按**输出文件名 stem** 分离：`/tmp/vert_<stem>_run`；显式 `VERT_TMP` 仍可覆盖（空串等同未设） | 并发两实例实测各写各的目录、都退出码 0（§3）；契约 V2/V6 已同步 | 已修（已归档） |
| 27 | 文档数字与实测漂移（页码/边注/纠正处数/右缘注释） | **先独立实测**（不照抄旧报告数字）-> 按真值更正 `build_vert.py` 注释 + `spec/vertical/*` + `docs/vert_v2_report.md` | 真值表与统计脚本见 §4.1；旧值来源已定位（§4.2） | 已修（已归档） |

**顺带**：`AGENTS.md` 测试计数 201 -> **209**（unit 188 -> 196，新增 8 项 `build_vert` 进程级行为测试）；
`AGENTS.md` 两处「竖排契约 V1-V8」-> **V1-V9**（V9 是上次治理任务新增的锚点节，旧引用未同步）。

## 二、#18 退出码分级

### 2.1 关键实测发现：**uplatex 对「正常成功」的编译也返回 rc=1**

修法前先实测编译器在**当前正常路径**下的真实退出码（这是判据设计的前提）：

```bash
cd /tmp/fix_base_tmp && uplatex -interaction=nonstopmode vert.tex; echo $?   # -> 1
grep -n '^!' vert.log                                                        # -> 1 条:
# 16:! LaTeX Error: KANJI Encoding scheme `JT1' unknown.
cd /tmp/fix_base_tmp && dvipdfmx vert.dvi; echo $?                           # -> 0
```

- 唯一报错是**类加载期 JT1**（`tsize10.clo` 内），`build_vert.py` preamble 注释（现 L884）与
  [spec/vertical/01_engine.md](../spec/vertical/01_engine.md) 早已注明「无法在文档内拦截，upLaTeX 下该命令本就被忽略」；
- 该报错行在 **stdout**（`capture_output=True` 能抓到）与 `vert.log` 里各出现 1 次；
- 全书 231 页产物正常（789KB）。

**结论：若照字面用「uplatex rc != 0 -> 失败」，正常路径会被判失败（违反验收标准①）。**
故判据必须标定，且不能用「只看 `vert.pdf` 是否存在」顶替 —— nonstopmode 下真出错也照样出 PDF。

### 2.2 修法与判据（`build_vert.py`）

```python
# ---------- 0) 临时目录 / 输入校验(#20 / #18) ----------
TMP = os.environ.get('VERT_TMP') or '/tmp/vert_%s_run' % os.path.splitext(os.path.basename(OUT))[0]
for _p, _kind in ((SL, 'lines'), (CO, 'coords')):
    if not os.path.exists(_p):
        print('[错误] %s 输入不存在: %s' % (_kind, _p), file=sys.stderr); sys.exit(1)
if SRC is not None and not os.path.exists(SRC):
    print('[错误] 源 PDF 不存在: %s' % SRC, file=sys.stderr); sys.exit(1)
if SRC is None:      # 3 参数调试调用保持兼容: 只警告(逐条列出 4 项), 退出码仍 0
    print('[警告] 未给源 PDF(argv[4] 缺省): 以下 4 项依赖源图墨迹的特性将静默关闭 —— ...', file=sys.stderr)
...
# ---------- 3) 编译 ----------
ERR_TOLERATED = ('KANJI Encoding scheme', 'JT1')     # 已知可容忍报错的特征子串
err_bad = [l for l in r.stdout.splitlines()
           if l.startswith('!') and not all(s in l for s in ERR_TOLERATED)]
if r2.returncode == 0 and not err_bad and os.path.exists(dvi_pdf):
    os.replace(dvi_pdf, OUT); print('[完成] %s' % OUT); sys.exit(0)
print('[失败] uplatex rc=%s dvipdfmx rc=%s 意外报错 %d 行, %s' % (...), file=sys.stderr)
for l in err_bad[:10]: print('  ' + l, file=sys.stderr)
print(r.stdout[-1500:], file=sys.stderr)
sys.exit(1)
```

**失败判据（三条任一）**：`dvipdfmx` rc != 0 / `vert.pdf` 未生成 / uplatex 输出里有**已知 JT1 之外**的 `!` 报错行。
失败诊断走 **stderr**（原来是 stdout），且失败**不落 OUT**（即使 `vert.pdf` 已生成 —— 避免把半坏产物交给调用方）。

### 2.3 验收实测（场景脚本 `tmp_vert/fix_verify_18_20.py`，19/19 PASS）

```
[PASS] A 正常跑(4参数) 退出码 0            rc=0
[PASS] A 产物落盘                          /tmp/fix_acc/full_162.pdf (55721 B)
[PASS] #20 默认临时目录 = /tmp/vert_full_162_run   [tex] /tmp/vert_full_162_run/vert.tex
[PASS] B 3参数 退出码 0                    rc=0
[PASS] B stderr 有警告且 4 项逐条列出      4/4: 书眉/页码/边注渲染, 版框线, 版心右缘墨迹复测, 旋转坐标系页还原
[PASS] C 输入缺失 退出码 1                 '[错误] lines 输入不存在: data/wz6/__not_exist__.json'
[PASS] D 源 PDF 缺失 退出码 1              '[错误] 源 PDF 不存在: source_pdf/__not_exist__.pdf'
[PASS] E 意外报错 退出码 1 / 不落 OUT      '[失败] uplatex rc=1 dvipdfmx rc=0 意外报错 1 行, vert.pdf 已生成'
[PASS] F 产物未生成 退出码 1 / 不落 OUT    '[失败] uplatex rc=1 dvipdfmx rc=1 意外报错 1 行, vert.pdf 未生成'
[PASS] G 仅已知 JT1 报错 退出码 0           rc=0 + [完成]
[PASS] H 并发两实例都成功 / 临时路径不同    conc_1=/tmp/vert_conc_1_run/vert.tex | conc_2=/tmp/vert_conc_2_run/vert.tex
[PASS] I 显式 VERT_TMP 生效                [tex] /tmp/fix_acc_explicit_tmp/vert.tex
===== 汇总: 19/19 PASS =====
```

- **正常路径零行为变化**：A 场景的 stdout/stderr 与改动前一致（除临时目录路径），产物 231 页与改动前**逐页文本全等**（§5.3）；
- E/F/G 用**假编译器**（`PATH` 前置 shim：假 `uplatex`/`dvipdfmx`）在无 LaTeX 参与下精确构造三种编译结局；
- 3 参数场景 B 走的是**真编译**（第 162 页单页，无源 PDF -> 4 项墨迹特性关闭），耗时与正常单页构建相同。

**单元测试锁定**：`src/test/unit/test_build_vert_cli.py`（8 项，`/usr/bin/python3 -m pytest src/test/unit/test_build_vert_cli.py -v` -> 8 passed in 0.20s）。
不依赖 upLaTeX/numpy/scipy/fitz/wz6 数据（合成 1 页 JSON + 假编译器），CI 与本地都能跑；
覆盖：3 参数警告且 0 / lines 缺失 1 / src 缺失 1 / 意外报错 1 且不落产物 / 无产物 1 / 只容忍 JT1 仍 0 / 默认临时目录按 stem / 显式 `VERT_TMP` 覆盖。

## 三、#20 临时目录按产物名分离

**改动**（`build_vert.py` L24，原 L16）：

```python
TMP = os.environ.get('VERT_TMP') or '/tmp/vert_%s_run' % os.path.splitext(os.path.basename(OUT))[0]
```

- 原默认 `/opt/test/tmp_vert/run`（项目根绝对路径硬编码，与产物名无关）-> 现默认 `/tmp/vert_<OUT stem>_run`；
- `VERT_TMP` **显式设置时仍用用户给的路径**（保留覆盖能力）；用 `or` 取值 -> **空串等同未设**（与 `VERT_NCOL` 同惯例；
  旧的 `os.environ.get('VERT_TMP', 默认)` 写法下 `VERT_TMP=` 会拿到空串并在 `makedirs` 报错）；
- **同名产物**并发仍共用目录（属预期，与横排 #10「路径分 build_name」同方案），需显式 `VERT_TMP` 分开。

**实测**：H 场景两个实例（`conc_1.pdf` / `conc_2.pdf`，各渲染 160-162 页，同一进程组并发）分别写
`/tmp/vert_conc_1_run/` 与 `/tmp/vert_conc_2_run/`，两者退出码均 0。

**契约同步**：`spec/governance/PIPELINE_BEHAVIOR.md` V2（`VERT_TMP` 行）、V6（产物表「并发」「退出码」两段全部重写为修后事实）；
`spec/vertical/01_engine.md`（输入/输出 + 约束 1：不同产物名可并行）；`spec/vertical/README.md`（env 表）。

## 四、#27 数字实测核对

原则：**先独立实测每一项真值**（不照抄 `docs/vert_governance_report.md` 与任务简报里的数字），再改文档。

### 4.1 真值表（脚本 `tmp_vert/fix_measure_baseline.sh`，全书真跑一次，改动前的 HEAD 代码）

| 项 | 旧文档值 | **实测真值** | 依据 |
|---|---|---|---|
| 书眉条数 | 107 | **107**（一致） | `grep -c '^  \[书眉\] p' tmp_vert/fix_base.log` |
| 页码条数 | 121 | **122** | `grep -c '^  \[页码\] p'` |
| 边注条数 | 64 | **65** | `grep -c '^  \[边注\] p'` |
| 版框页数 | 228 | **228**（一致；兜底 6 页、跳过 0 页） | `grep -c '^  \[版框\] p'` |
| 页码序列纠正 | 19 处 | **18 处** | `[页码序列] 全书 123 页有页码, 拟合 value = 1.000*page + 176.0; 误读纠正 18 处` |
| 有页码页数 | 123（05 spec） | **123**（一致） | 同上（`PN_INFO[0]`） |
| 拟合式 | `1.000*page + 176.0` | **一致** | 同上 |
| 右缘（L666 注释） | 「≈546pt」「偏右 ~49pt」 | **563.1pt / 偏右 ~32pt** | `[版心右缘] OCR 拟合 594.9 -> 源图墨迹实测 563.1 pt (抽 12 页版框内右线中位)`；独立复算见 4.3 |

### 4.2 旧值来源已定位（不是「当时数字写错了」，是**口径变了**）

对照实验 `tmp_vert/fix_derot_control.sh`（唯一变量 `VERT_DEROT=0`，其余同）：

| 配置 | 书眉 | 页码 | 边注 | 版框 | 旋转修正 | 误读纠正 |
|---|---|---|---|---|---|---|
| 默认（`VERT_DEROT=1`） | 107 | **122** | **65** | 228 | 1 | **18** |
| `VERT_DEROT=0` | 107 | **121** | **64** | 228 | 0 | **18** |

- **页码 121 / 边注 64 = 关掉旋转页还原时的计数** —— p159 是 OCR 旋转坐标系页，`derot_rows` 修好后该页多出
  1 条页码 + 1 条边注。文档旧值应是在 p159 修复（commit `ff4b5b7` 的一部分）**之前**测的；
- **误读纠正 18 处与 derot 无关**（两种配置都 18）-> 旧的「19 处」只能是更早版本的 `pn_sequence_fix` 产物或笔误，本报告如实记为 18。

### 4.3 右缘注释（L666「≈546pt」）的更正依据

- `594.9pt` 是「OCR 拟合值」，被 `VERT_RIGHT_INK`（§1.96）替换为**抽样页内框右线中位**；
- 抽样集由代码决定：`step = 231//12 = 19`，`samp = [1,20,39,...,229]`，其中 p1 无版框（`frame_geom` 返回 None）
  -> 有效 12 页，中位 **563.1pt**（脚本 `tmp_vert/fix_analyze_right.py` 从日志逐页复算，与日志汇总行一致）；
- 独立统计：全书 228 页内框右线中位 **557.8pt**（最小 536.5 / 最大 577.3）；**奇数页 567.5 / 偶数页 549.4**
  —— 奇偶错位即已登记 issue #23，故「546pt」不是全局真值，而是**个别页**的值（p4 实测 546.0）；
- 任务简报与旧注释里的「≈546pt」应更正为抽样中位 563.1pt，偏差 `594.9 - 563.1 = 31.8 ≈ 32pt`（原写 ~49pt 是拿 546 算的）。

**p4 细节复核**（`tmp_vert/fix_p4_ink.py` / `fix_p4_profile.py`，源图 2x 灰度 + 逐 x 墨迹剖面）：

```
p4 版框 y316.5-1117 内右侧细竖线 x(pt): [501.5(界行线), 545.2(内框右线)]
最右正文列 OCR x1056.4-1119.5 -> 列墨迹右缘 544.5 pt; 内框右线 545.2 pt; 差 0.8 pt
```

-> 注释里 p4 的「列墨右缘 544.5 vs 线 545.5」**实测复现**（544.5 完全一致；线 545.2/代码 in_r 546.0，差 ≤1px）
**不是漂移，予以保留**。（同一窗口若不过滤版框外书眉墨迹，会把右缘顶到书眉上 = 567.0pt —— 这是该测量容易踩的坑，脚本里用「组件 x 中心 <= 内框右线」过滤。）

### 4.4 按真值更正的文档（只改数字/状态，不改机制描述）

| 文件 | 更正内容 |
|---|---|
| `src/pipelines/build_vert.py` | L685-686 注释：右缘 ≈546pt/偏右 ~49pt -> 563.1pt（抽样页中位，附单页实例 p4 = 546.0）/偏右 ~32pt |
| `spec/vertical/README.md` | 指标表 107/121/64 -> **107/122/65**、纠正 19 -> **18 处** + 口径脚注（121/64 = derot 关闭时）；回归 201 -> 209；`VERT_TMP` 默认值；锚点表 6 行 |
| `spec/vertical/03_marginalia.md` | 状态行与验收方法 1 的 121/64 -> **122/65**；锚点 2 行 |
| `spec/vertical/05_pagenum_sequence.md` | 状态行/验收方法 1 的 19 -> **18 处**；锚点 3 行 |
| `spec/vertical/01_engine.md` | `VERT_TMP` 默认值；并行约束（#20 后可不同产物名并行）；新增退出码说明；锚点 2 行 |
| `spec/vertical/02/04/06_*.md` | 锚点行号全量重算（见下） |
| `docs/vert_v2_report.md` | 书眉/页码/边注 121/64 -> **122/65**；页码纠正 19 -> **18 处**；右缘「偏右 ~49pt」-> **~32pt**（附真右缘 563.1pt） |
| `spec/governance/PIPELINE_BEHAVIOR.md` | 竖排章节 39 处：V1（argv 行号 + SRC 缺省警告化）/V2（12 env 行号 + VERT_TMP 默认值）/V6（产物表 + 并发段 + 退出码段重写）/V7/V9 锚点全表 + 实测基线脚注（R1 关闭） |
| `AGENTS.md` | §3 unit 188 -> 196（拦什么加 build_vert 行为）；§3 备注「不能用 build_vert 退出码当门禁」重写为修后事实；§4/§5 测试计数 201 -> 209；§4「V1-V8」-> 「V1-V9」×2；§6 #18/#20/#27 移入已归档（含修法与证据指针） |
| `spec/README.md` | 报告清单新增本报告条目；`PIPELINE_BEHAVIOR.md` 条目说明补 V9 |

**锚点（行号）同步**：本次改动使 `build_vert.py` 从 924 -> **958 行**（顶部 +19、注释 +1、尾部 +14）。
按 AGENTS.md §4 第 4 条要求，用 `tmp_vert/fix_anchor_map.py`（difflib 逐行映射）重算全部锚点，
再用 `tmp_vert/fix_check_anchors.py` 反查「每个锚点指向的源码行」人工核对（输出示例：`03_marginalia.md L125-141 首: def special_rows(k)`）。
`PIPELINE_BEHAVIOR.md` V9 表的 13 行 + 6 个分部 spec 的 30 余处锚点已全部改到新行号。

## 五、回归验证（硬要求）

### 5.1 `verify_vert.py` 实测 PASS（对**改动后重跑**的产物，不是冻结旧产物）

```bash
/usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json \
  /tmp/fix_new/wz6_vert_full.pdf source_pdf/wz6.pdf        # -> 退出码 0（默认临时目录 /tmp/vert_wz6_vert_full_run）
/usr/bin/python3 src/test/verify_vert.py /tmp/fix_new/wz6_vert_full.pdf \
  data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json \
  --src-pdf source_pdf/wz6.pdf --json /tmp/fix_vert_verify.json
```

```
页数: 源 OCR 231 页  |  输出 PDF 231 页  |  ✓ 1:1
字符量: 输出 68016 / OCR 69998 = 97.2%
越界: span 0 个 / 矢量图形 0 个（容忍 0.5pt；涉及 0 页）
页幅: 源书众数 595.28x1245.31pt（116/231 页）  |  输出 595.27x1245.33pt  |  相对差 0.00%/0.00%
== 退出码 PASS ==      （脚本退出码 = 0）
```

### 5.2 209 测试全绿

```bash
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
# -> 209 passed in 3.00s   （unit 196 + invariants 13；unit 新增 8 项 = test_build_vert_cli.py）
```

### 5.3 渲染零变化（证明本次只碰了退出码/临时目录/注释）

改动前基线（`/tmp/fix_base_out/wz6_vert_full.pdf`，HEAD 代码）vs 改动后（`/tmp/fix_new/wz6_vert_full.pdf`）：

```
页数: 231 vs 231          逐页文本不同的页: 0        页幅不同的页: 0
矢量图形数: 4075 vs 4075   文本字符数: 136924 vs 136924
结论: 渲染零变化(逐页文本/页幅/矢量数全等)
```

日志计数也逐项一致（书眉 107 / 页码 122 / 边注 65 / 版框 228 / 旋转修正 1 / 纠正 18 处 / 右缘 563.1pt）。
（文件字节级差 1 B，为 PDF 元数据，与此前 `docs/vert_governance_report.md` §4.2 记录的现象一致。）

### 5.4 lint 无新增违规（ruff）

`ruff check src/pipelines/build_vert.py`：改动前后同为 **3 条**且完全同名（`E401` 多 import 同行 / `F401 re` / `F401 numpy`，均为预存在）；
新增测试 `src/test/unit/test_build_vert_cli.py`：`All checks passed!`。

## 六、约束遵守声明

- **未改横排管线**：`build_geom.py` / `build_classic.py` / `build_pdf_v13.py` / `fit_positional*.py` / `fit_common.py` / `src/utils/*` 与横排测试均未触碰。
- **未动 `build_vert.py` 渲染逻辑**：改动仅 3 处 —— 顶部临时目录/输入校验块（+19 行）、编译失败分支（判据与退出码）、L685 注释数字；
  §5.3 的逐页对照证明渲染输出与改动前全等。
- **未动四书数据**（`data/wz*`）与 `source_pdf/`；所有重跑产物写到 `/tmp`，未覆盖 `output/wz6/*`。
- **未 `git reset`、未 commit**；改动与新文件已 `git add`（清单见第七节）。
- 未改 `.github/workflows/ci.yml`（竖排验证不进 CI 的结论沿用，见 PIPELINE_BEHAVIOR.md「CI 结论」）。
- 未改 `src/test/verify_vert.py`。
- 复杂 shell 全部落成脚本文件执行（`tmp_vert/fix_*.sh` / `tmp_vert/fix_*.py`，scratch 目录未入库）。

## 七、改动文件清单

```
M  src/pipelines/build_vert.py                            (退出码分级 + 临时目录分离 + 注释数字)
A  src/test/unit/test_build_vert_cli.py                   (新增, 8 项进程级行为测试)
M  AGENTS.md                                              (测试计数 / 退出码备注 / V1-V9 / §6 issue 归档)
M  spec/governance/PIPELINE_BEHAVIOR.md                   (V1/V2/V6/V7/V9 + 实测基线脚注)
M  spec/vertical/README.md  spec/vertical/01_engine.md
M  spec/vertical/02_tate_layout.md  spec/vertical/03_marginalia.md
M  spec/vertical/04_frame_lines.md  spec/vertical/05_pagenum_sequence.md
M  spec/vertical/06_derot.md                              (数字真值 + 锚点行号)
M  docs/vert_v2_report.md                                 (121/64/19/~49pt -> 真值)
M  docs/vert_governance_report.md                         (R1 标注已关闭)
A  docs/vert_fix18_20_27_report.md                        (本报告)
```

## 八、遗留与建议

1. **preamble 的 JT1 报错仍是「容忍项」**（#18 判据里硬编码特征子串 `('KANJI Encoding scheme', 'JT1')`）。
   根治要在 `tsize10.clo` 加载期拦截（文档内做不到，见 01_engine.md）；若将来 upLaTeX/类文件升级后该报错消失，
   容忍项会自动失效（无害），但**若报错文本变化**会被判为「意外报错」-> 构建退出码 1，需同步 `ERR_TOLERATED`。
2. **`uplatex` 不在 PATH 时**仍是 `FileNotFoundError` traceback（退出码 1，非静默）—— 未纳入本次分级，保持原状。
3. **同名产物并发**仍冲突（设计如此，同横排 #10）；若要连同名也安全，可再加「按进程/时间戳细分」或落锁。
4. `tmp_vert/` 下的历史 scratch 脚本（`build3_9.sh` / `build_notes_extra.sh` 等）仍写死旧默认目录 `tmp_vert/run/`，
   属未入库的调试脚本，本次未动（重跑时需显式设 `VERT_TMP`）。
5. 竖排自身仍有 #19（页码行合并页）/ #21-#24（版式保真）/ #25（OCR 方向参数）/ #26（verify_vert 不覆盖版式保真）未修 ——
   本次只做收尾三项，见 `AGENTS.md` §6。
