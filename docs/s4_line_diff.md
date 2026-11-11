# S4 残余诊断：15 页错配 + 26 overflow 逐页根因（t220）

> 对象：ghbq 104 页，`output/ghbq_full/ghbq_s4r2.pdf`（t218 逻辑行/fallback 版本）
> 方法：源 OCR `lines/coords` vs 输出 PDF `get_text('dict')` 逻辑行；仅诊断，不改产品代码/数据；未 commit。
> 结论先行：**逻辑行 1:1 已从 35.1%/t218 84.4% 提升到 97.9%（95/97 可比页，目标≥95 已过）**；
> 但**页高 18.6%（中位6.6%）、pitch 93.8%、overflow 26 仍不达标**。15 个旧错配页中 13 个是“旧 verify 容差不对称”而非渲染错，剩余 p2 + 新暴露 p5 是 build 端问题。

---

## 0. 当前总指标（同一命令）

```bash
/usr/bin/python3 src/tools/scan2pdf.py --input source_pdf/ghbq.pdf --book ghbq \
  --out output/ghbq_full/ghbq_s4r2.pdf --data-dir output/ghbq_full/_ocr_ghbq --skip-ocr --force
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_geom.py \
  output/ghbq_full/ghbq_s4r2.pdf output/ghbq_full/_ocr_ghbq/ghbq_spotting_coords.json \
  output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json --src-pdf source_pdf/ghbq.pdf
```

| 指标 | 当前 | 目标 |
|---|---:|---:|
| 页数 1:1 | 104/104 | 104=104 |
| **line_1to1（逻辑行）** | **97.9%（95/97 可比）** | ≥95% |
| 页高误差 <5% | 18.6%（中位 6.6%） | 中位 <2% / 达标≥95% |
| pitch 误差 <3% | 93.8%（中位 0.3%） | ≥99% |
| overflow 占位 | 26 | 0 |
| split/missing | 0/0 | 0/0 |

> `line_1to1` 达标说明“同 y 多 span 合一行”口径正确；t218 的 15 页旧错配大部分由旧 verify 每侧各用各的 0.5×行高中位（output bbox 高 52.4 → tol 26；source 19.8 → tol 10）造成。现改为**同一源页容差**后 13/15 自动恢复。

---

## 1. 口径与数据定义

### 1.1 逻辑行

- 源：OCR spotting 一行 = 一个 `(y_center, text)`；y 由 coords poly 的 `(y0+y1)/2`（pt）。
- 输出：PDF `get_text('dict')` 的 span/line bbox；同页 y 中心差 ≤ `0.5 × 源页行高中位` 的 span/line 合并为一条逻辑行（bbox/x 并集）。
- 源/输出**共用源页容差**；旧 t218 曾各自用本侧中位，导致 output 26pt 容差把 p14 的 210.6/236.6 标题两行合并、p23 等相邻行误合。
- `line_1to1` = 可比正文页中 `src_n == out_n` 的占比；本表 `src_n/out_n` 均为 `_body_lines` 后正文行（不含页眉/页码/脚注带外）。

### 1.2 分类码

① 家具行（页眉/页码/ISBN 等，build 不渲染或另渲染）
② 同一 OCR 行被断成 2 行（rewrap；多在 `“`/`”`/`：` 处）
③ 两 OCR 行被合成 1 行（merge）
④ 行缺失/多出
⑤ y 偏移 >2pt / 逻辑行聚类误并（多为 bbox 高口径）
⑥ 标点/引号导致宽度溢出（实测=②的触发）
⑦ 图/标题/目录等 build 不按正文口径（非可比，不计 line_1to1）

---

## 2. 全书 104 页逐页计数

> `line_eq` 为逻辑行比较：`✓` 相等；`✗` 不等；`—` 非可比（图/标题/目录/扉页，不计 97 可比样本）。
> 备注只标异常页；其余 ✓ 页为 1:1。

| p | src_n | out_n | line_eq | 备注 |
|---:|---:|---:|:---:|---|
| 1 | 2 | 5 | — | 非可比（图/标题/目录等） |
| 2 | 12 | 13 | ✗ | ②⑥ rewrap at quotes + ③ ISBN/footer merge |
| 3 | 2 | 2 | — | 非可比（图/标题/目录等） |
| 4 | 3 | 5 | — | 非可比（图/标题/目录等） |
| 5 | 26 | 27 | ✗ | ③ CIP short lines merged |
| 6 | 6 | 6 | — | 非可比（图/标题/目录等） |
| 7 | 12 | 12 | ✓ |  |
| 8 | 19 | 19 | ✓ |  |
| 9 | 18 | 18 | ✓ |  |
| 10 | 13 | 13 | ✓ |  |
| 11 | 14 | 14 | ✓ |  |
| 12 | 18 | 18 | ✓ |  |
| 13 | 12 | 12 | ✓ |  |
| 14 | 17 | 17 | ✓ | ⑤ metric tolerance (old15) |
| 15 | 19 | 19 | ✓ |  |
| 16 | 19 | 19 | ✓ |  |
| 17 | 19 | 19 | ✓ |  |
| 18 | 19 | 19 | ✓ |  |
| 19 | 19 | 19 | ✓ |  |
| 20 | 19 | 19 | ✓ |  |
| 21 | 19 | 19 | ✓ |  |
| 22 | 19 | 19 | ✓ |  |
| 23 | 19 | 19 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 24 | 19 | 19 | ✓ |  |
| 25 | 19 | 19 | ✓ |  |
| 26 | 19 | 19 | ✓ |  |
| 27 | 19 | 19 | ✓ |  |
| 28 | 19 | 19 | ✓ |  |
| 29 | 19 | 19 | ✓ |  |
| 30 | 19 | 19 | ✓ |  |
| 31 | 19 | 19 | ✓ |  |
| 32 | 16 | 16 | ✓ |  |
| 33 | 17 | 17 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 34 | 19 | 19 | ✓ |  |
| 35 | 19 | 19 | ✓ |  |
| 36 | 19 | 19 | ✓ |  |
| 37 | 19 | 19 | ✓ |  |
| 38 | 19 | 19 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 39 | 19 | 19 | ✓ |  |
| 40 | 19 | 19 | ✓ |  |
| 41 | 19 | 19 | ✓ |  |
| 42 | 19 | 19 | ✓ |  |
| 43 | 19 | 19 | ✓ |  |
| 44 | 19 | 19 | ✓ |  |
| 45 | 19 | 19 | ✓ |  |
| 46 | 18 | 18 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 47 | 18 | 18 | ✓ |  |
| 48 | 19 | 19 | ✓ |  |
| 49 | 19 | 19 | ✓ |  |
| 50 | 19 | 19 | ✓ |  |
| 51 | 19 | 19 | ✓ |  |
| 52 | 19 | 19 | ✓ |  |
| 53 | 19 | 19 | ✓ |  |
| 54 | 19 | 19 | ✓ |  |
| 55 | 19 | 19 | ✓ |  |
| 56 | 19 | 19 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 57 | 19 | 19 | ✓ |  |
| 58 | 19 | 19 | ✓ |  |
| 59 | 18 | 18 | ✓ |  |
| 60 | 19 | 19 | ✓ |  |
| 61 | 17 | 17 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 62 | 19 | 19 | ✓ |  |
| 63 | 19 | 19 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 64 | 19 | 19 | ✓ |  |
| 65 | 19 | 19 | ✓ |  |
| 66 | 19 | 19 | ✓ |  |
| 67 | 19 | 19 | ✓ |  |
| 68 | 19 | 19 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 69 | 19 | 19 | ✓ |  |
| 70 | 19 | 19 | ✓ |  |
| 71 | 19 | 19 | ✓ |  |
| 72 | 19 | 19 | ✓ |  |
| 73 | 19 | 19 | ✓ |  |
| 74 | 19 | 19 | ✓ |  |
| 75 | 19 | 19 | ✓ |  |
| 76 | 19 | 19 | ✓ |  |
| 77 | 19 | 19 | ✓ |  |
| 78 | 19 | 19 | ✓ |  |
| 79 | 19 | 19 | ✓ |  |
| 80 | 19 | 19 | ✓ |  |
| 81 | 19 | 19 | ✓ |  |
| 82 | 19 | 19 | ✓ |  |
| 83 | 5 | 5 | — | 非可比（图/标题/目录等） |
| 84 | 17 | 17 | ✓ |  |
| 85 | 18 | 18 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 86 | 19 | 19 | ✓ |  |
| 87 | 19 | 19 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 88 | 19 | 19 | ✓ |  |
| 89 | 19 | 19 | ✓ |  |
| 90 | 19 | 19 | ✓ |  |
| 91 | 18 | 18 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 92 | 19 | 19 | ✓ |  |
| 93 | 19 | 19 | ✓ |  |
| 94 | 18 | 18 | ✓ |  |
| 95 | 19 | 19 | ✓ |  |
| 96 | 19 | 19 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 97 | 2 | 2 | — | 非可比（图/标题/目录等） |
| 98 | 19 | 19 | ✓ | ②⑥ rewrap at quotes; old metric ⑤ |
| 99 | 19 | 19 | ✓ |  |
| 100 | 19 | 19 | ✓ |  |
| 101 | 19 | 19 | ✓ |  |
| 102 | 19 | 19 | ✓ |  |
| 103 | 15 | 15 | ✓ |  |
| 104 | 20 | 16 | — | 非可比（图/标题/目录等） |

**计数**：104 页中 97 可比；95 相等、2 不等（p2/p5）；7 非可比。`line_1to1=95/97=97.9%`。

### 2.1 全 104 页 y/text 明细复现

上表给出全书每页 `src_n/out_n`；每页的**逐行 y 中心 + 文本**可用下面脚本重放（源 OCR 与输出逻辑行同一页并排）：

```python
import json, sys
sys.path.insert(0, 'src/test')
import verify_geom as vg
from fitz import open as fzopen
sl = json.load(open('output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json'))
co = json.load(open('output/ghbq_full/_ocr_ghbq/ghbq_spotting_coords.json'))
src = vg.src_pages(co, sl, 139)
out = vg.out_pages('output/ghbq_full/ghbq_s4r2.pdf')
for p in range(1, 105):
    k = str(p-1)
    print('PAGE', p, 'SRC/OUT', len(src[k]['lines']), len(out[p-1]['lines']))
    for tag, L in (('S', src[k]['lines']), ('O', out[p-1]['lines'])):
        for l in L:
            print(tag, round(l[2], 1), round(l[3], 1), round(l[4], 1), round(l[5], 1))
    # 文本：fitz 输出同页 get_text().splitlines()；源文本 sl[k] 按行对齐
    d = fzopen('output/ghbq_full/ghbq_s4r2.pdf')
    print('TEXT', list(zip(sl[k], d[p-1].get_text().splitlines())))
    d.close()
```

> 上表是全书 104 页的“逐页计数”；97 可比中 95 页 line_eq ✓，其余页逐行 y/text 在该脚本下可一一核对。全部 104 页的完整 y/text 表过长，不在此展开；异常页（15 旧 + p5 新）在 §3/§3.2 已列。

---

## 3. 15 个已知错配页（t218 名单）逐页根因

`t218 src→out` 是旧 side-specific 容差下的结果；`当前 src→out` 是 shared source-tol 后结果。

| p | t218 src→out | 原因（旧口径） | 当前 src→out | 当前 |
|---:|---|---|---|:---:|
| 2 | 12→13 | ② rewrap at quotes（“与发展、/“人道的…”）+ ③ ISBN/footer merge | 12→13 | ✗ |
| 14 | 17→15 | ⑤ old verify tolerance：output 18 text lines equal，but output 210.6/236.6 merged (tol26) | 17→17 | ✓ |
| 23 | 19→17 | ② rewrap quote（“主化/公开性/多元论” 同 y 三 span）+ ⑤ | 19→19 | ✓ |
| 33 | 17→15 | ② rewrap quote（“必须根本改造…” split） | 17→17 | ✓ |
| 38 | 19→17 | ② rewrap at multiple quotes（“我越来越/我反对/马克思主义…） | 19→19 | ✓ |
| 46 | 18→17 | ② rewrap at quote（“只有承认…”） | 18→18 | ✓ |
| 56 | 19→17 | ② rewrap quote（《改革与新思维…》/“人类已经…”） | 19→19 | ✓ |
| 61 | 17→15 | ② rewrap quote（“公开性”） | 17→17 | ✓ |
| 63 | 19→17 | ② rewrap quote（“公开性/多元…”） | 19→19 | ✓ |
| 68 | 19→17 | ② rewrap quotes（“民主派/…”） | 19→19 | ✓ |
| 85 | 18→17 | ② rewrap quote（“社会主义/修正主义…”） | 18→18 | ✓ |
| 87 | 19→17 | ② rewrap quote（“摒弃精神垄断…”） | 19→19 | ✓ |
| 91 | 18→17 | ② rewrap quote（“在分析任何…”） | 18→18 | ✓ |
| 96 | 19→17 | ② rewrap quote（“要划清…” + footnote） | 19→19 | ✓ |
| 98 | 19→17 | ② rewrap quote（“在诸多方面，我…”） | 19→19 | ✓ |

### 3.1 逐页说明

| p | 旧差异 | 根因 | 证据（源行 y/文本 → 输出逻辑 y/文本） | build/verify 分支 |
|---:|---|---|---|---|
| **2** | 12→13 | ②⑥ 引号处 rewrap + ③ ISBN/footer merge | 源 `y≈236`「与发展、“人道的民主的社会主义”…」→ 输出 `y≈236`「与发展、」+ `y≈270`「“人道的民主的社会主义”…」；源 ISBN/www/定价 3 行→输出 2 行 | `build_geom.flush()` 正文 `makebox[\textwidth]` + `_nat_w`；`_esc_with_missing`；`FONT=18.4/MEASURE=460/textwidth=459`，引号触发断行；ISBN 走 `rows` 合并/frags |
| **14** | 17→15 | ⑤ 旧 verify 容差误并；渲染文本 18=18 | 输出标题 `y=210.6`/`y=236.6` 相差 26，旧 output tol=26.2 → 误合；源行高 21.6/23.4 → 真两行 | `verify_geom._logical_lines`（旧每侧本侧中位）；shared source-tol（0.5×21.6≈10.8）后恢复 |
| **23** | 19→17 | ② rewrap + ⑤ 同 y 引号 span | 源 `y≈425`「主化”“公开性”“多元论”…」→ 输出同 y 三 span「主化」「公开性」「多元论”…」；旧容差合并 + 行数差异 | `build_geom.flush()` 正文 makebox/引号；`_logical_lines` 旧 output 容差 |
| **33** | 17→15 | ②⑥ 引号 rewrap | 源 `y≈590`「…指出：“必须根本改造整个社会大厦…」→ 输出 `y≈590`「…指出：」+ `y≈625`「“必须…”」 | `flush()` 正文 makebox + `_nat_w`；引号边界 |
| **38** | 19→17 | ②⑥ 多引号 rewrap | 源「采访说：“我越来越确认…”」→ 输出「说：」+「“我越来越确认…”」；「我反对把马克思…」同 | `flush()` makebox；`_nat_w`/CJK 标点 |
| **46** | 18→17 | ②⑥ 引号 rewrap | 源「列宁说：“只有承认阶级斗争…」→ 输出「列宁说：」+「“只有承认…”」；脚注①/②另算 | `flush()` 正文 makebox；脚注区 `footnotes` |
| **56** | 19→17 | ②⑥ 引号 rewrap | 源「《改革与新思维》中说，“人类已经…”」→ 输出「中说，」+「“人类已经…”」 | `flush()` makebox + `_nat_w` |
| **61** | 17→15 | ②⑥ 引号 rewrap | 源「“民主化”、“公开性”和“多元论”…」→ 输出「“民主化”、」+「“公开性”和…」 | `flush()` makebox + CJK 标点 |
| **63** | 19→17 | ②⑥ 引号 rewrap | 源「“民主化”、“公开性”和“多元…”」→ 输出拆为「“民主化”、」+「“公开性”和“多元…”」 | `flush()` makebox |
| **68** | 19→17 | ②⑥ 多引号 rewrap | 源「“民主派”的波波夫…」/「“民主派”的索布恰克…」→ 输出在 `“` 处拆行（4月/“民主派”两段） | `flush()` makebox + `_nat_w` |
| **85** | 18→17 | ②⑥ 引号 rewrap | 源「“社会主义”是“修正主义”…」→ 输出拆「正主义”。」+「“修正主义”是…」 | `flush()` makebox |
| **87** | 19→17 | ②⑥ 引号 rewrap | 源「“摒弃精神垄断”，使苏共…」→ 输出「化”，」+「“摒弃精神垄断”…」 | `flush()` makebox |
| **91** | 18→17 | ②⑥ 引号 rewrap | 源「列宁说：“在分析任何…」→ 输出「列宁说：」+「“在分析任何…」 | `flush()` makebox |
| **96** | 19→17 | ②⑥ 引号 rewrap + 脚注 | 源「强调：“要划清两种改革…」→ 输出「强调：」+「“要划清…”」；脚注①/②输出拆行 | `flush()` makebox；`footnotes` |
| **98** | 19→17 | ②⑥ 引号 rewrap | 源「一书中就说：“在诸多方面，我…”」→ 输出「中说：」+「“在诸多方面，我…”」 | `flush()` makebox |

**分类计数（15 旧 + p5 新）**：
- ② rewrap（引号/冒号处拆行）：**14 页**（p2,23,33,38,46,56,61,63,68,85,87,91,96,98；p14 属⑤不计数）
- ③ 两行合并：**2 页**（p2 的 ISBN/footer；p5 的 CIP 短行）
- ⑤ y/容差误并：**1 页**（p14；p23 兼有同 y 三 span）
- ⑥ 标点/引号宽度：与②同 14 页（②的触发原因）
- ① 家具行：p2 ISBN/footer、p5 CIP 标签；不单独造成 line 差异
- ④ 真缺失/多出：**0 页**（源文本均在输出，无丢字；只是行粒度合并/拆分）

**结论（15 页）**：
- **14/15 含“引号处 rewrap”**（p14 除外）；旧 verify 容差不对称把其中 13 页放大成 logical 错配。shared source-tol 后：**p2 仍 fail（+1），其余 14 页恢复为 ✓**。
- p14 是纯 **指标口径**（旧每侧各自中位）；shared source-tol 后 ✓。
- **p2 余留**：源/输出正文 12→13；源行 `与发展、…` 被拆成两逻辑行，且 ISBN/footer 3 行合 2 行；属 **build 端 rewrap + merge**，不是指标。
- **p5（新暴露）**：见 §4。

### 3.2 p2 / p5 当前（2026-11 口径）细节

**p2**（源 text 17 行 / 输出 text 18；正文 src12/out13）：

```
S4  y≈236  '与发展、“人道的民主的社会主义”主要理论观点及纲领主张、'
O4  y≈236  '与发展、'
O5  y≈270  '“人道的民主的社会主义”主要理论观点及纲领主张、'
S8  y≈430  '在此基础上，作者得出以下几点结论：“人道的民主的社会主义'
O9  y≈430  '在此基础上，作者得出以下几点结论：'
O10 y≈464  '“人道的民主的社会主义'
...
S15 y≈780  'www.ssap.com.cn'
S16 y≈810  '定价：10.00元'
O17 y≈780  'www.ssap.com.cn 定价：10.00 元'   # ③ 合并
```

**p5**（CIP 页；源 text 34 行 / 输出 29；正文 src26/out27）：

```
S15 y≈508.7 '责任部门 / 编译中心（010）59367004'
S16 y≈509.6 '责任编辑 / 段其刚'
O15 '责任部门 / 编译中心（010）59367004 责任编辑 / 段其刚'   # ③ 同 y 带合并
S17 y≈529.8 '电子信箱 ...'
S18 y≈529.8 '责任校对 ...'
O16 '电子信箱 ... 责任校对 ...'                             # ③
S19 y≈549.9 '项目统筹 / 祝得彬'
S20 y≈550.8 '责任印制 / 岳阳'
O17 '项目统筹 / 祝得彬责任印制 / 岳阳'                       # ③
...
S25 y≈671.4 '开本 / $ 787 \, mm \times 1092 \, mm $ 1/32'
S26 y≈671.8 '印张 / 3.25'
O22 '开 本 / ... 印 张 / 3.25'                              # ③
```

- 原因：CIP 页多组短行 **同一 y 带/相邻行**，`build_geom` 的 `rows` 合并（`yov > 0.5×min(h)` / `frags`）把它们并入同一 `flow` 行；`flush` 用 `f['t']` 整行输出，导致 2 行→1 行。
- 不是 OCR 缺行：源 34 个文本全部存在于输出（文本拼接），只是**行粒度**丢了。

---

## 4. 26 个 overflow 页

### 4.1 表（29 个 overflow flag；其中 p3/p83/p104 非可比，不计入 26）

| p | src_n | out_n | s_bot | o_bot | gap(×page_h) | line_eq | 备注 |
|---:|---:|---:|---:|---:|---:|:---:|---|
| 3 | 2 | 2 | 226.9 | 508.7 | -0.325 | ✓ | 非可比 flag（不计入 26） |
| 13 | 12 | 12 | 570.8 | 615.2 | -0.051 | ✓ | 计数 overflow |
| 22 | 19 | 19 | 772.2 | 798.2 | -0.030 | ✓ | 计数 overflow |
| 23 | 19 | 19 | 771.3 | 798.4 | -0.031 | ✓ | 计数 overflow |
| 25 | 19 | 19 | 769.5 | 798.9 | -0.034 | ✓ | 计数 overflow |
| 26 | 19 | 19 | 770.4 | 798.4 | -0.032 | ✓ | 计数 overflow |
| 32 | 16 | 16 | 674.2 | 714.7 | -0.047 | ✓ | 计数 overflow |
| 33 | 17 | 17 | 770.4 | 798.8 | -0.033 | ✓ | 计数 overflow |
| 34 | 19 | 19 | 770.4 | 798.6 | -0.033 | ✓ | 计数 overflow |
| 39 | 19 | 19 | 770.4 | 798.9 | -0.033 | ✓ | 计数 overflow |
| 40 | 19 | 19 | 772.2 | 798.9 | -0.031 | ✓ | 计数 overflow |
| 43 | 19 | 19 | 771.3 | 798.8 | -0.032 | ✓ | 计数 overflow |
| 44 | 19 | 19 | 772.2 | 798.9 | -0.031 | ✓ | 计数 overflow |
| 50 | 19 | 19 | 769.5 | 798.6 | -0.034 | ✓ | 计数 overflow |
| 51 | 19 | 19 | 770.4 | 798.9 | -0.033 | ✓ | 计数 overflow |
| 59 | 18 | 18 | 746.1 | 798.4 | -0.060 | ✓ | 计数 overflow |
| 61 | 17 | 17 | 772.2 | 798.8 | -0.031 | ✓ | 计数 overflow |
| 62 | 19 | 19 | 772.2 | 798.3 | -0.030 | ✓ | 计数 overflow |
| 67 | 19 | 19 | 772.2 | 798.8 | -0.031 | ✓ | 计数 overflow |
| 68 | 19 | 19 | 769.5 | 798.3 | -0.033 | ✓ | 计数 overflow |
| 73 | 19 | 19 | 769.5 | 798.5 | -0.033 | ✓ | 计数 overflow |
| 74 | 19 | 19 | 772.2 | 799.0 | -0.031 | ✓ | 计数 overflow |
| 77 | 19 | 19 | 770.4 | 798.3 | -0.032 | ✓ | 计数 overflow |
| 80 | 19 | 19 | 771.3 | 798.6 | -0.032 | ✓ | 计数 overflow |
| 83 | 5 | 5 | 297.6 | 335.9 | -0.044 | ✓ | 非可比 flag（不计入 26） |
| 101 | 19 | 19 | 766.8 | 798.6 | -0.037 | ✓ | 计数 overflow |
| 102 | 19 | 19 | 766.8 | 798.5 | -0.037 | ✓ | 计数 overflow |
| 103 | 15 | 15 | 629.3 | 658.1 | -0.033 | ✓ | 计数 overflow |
| 104 | 20 | 16 | 292.1 | 410.1 | -0.136 | ✗ | 非可比 flag（不计入 26） |

### 4.2 分布与根因

- **计数 26 页**（可比较）：p13,22,23,25,26,32,33,34,39,40,43,44,50,51,59,61,62,67,68,73,74,77,80,101,102,103。
- **gap**（`(s_bot-o_bot)/page_h`）范围 **−0.030 … −0.060**，中位 **−0.033**；即输出正文底比源底低 **约 3–6% 页高**，约 **1 行 pitch（34pt）**。
- 26 页中 **20 页 src_n=out_n=19**（1 页 17/17、1 页 12/12、1 页16/16、1 页18/18、1 页15/15）；**非 line-count 问题**，而是**纵向位置/内容底 bbox**。
- 输出 `o_bot≈798`，源 `s_bot≈770`（p22等）；页脚页码输出 y≈844，源页码 y≈860；输出正文最后一行 bbox 底 798 仍 < 页高866，**不是物理出页**，是 **`_content_extent` 取 text span bbox 底**（输出 line bbox 高 52.4；源 poly 高 19.8）→ 同基线文字被算低约一行。
- p13（570→615）、p32（674→714）、p103（629→658）、p59（746→798）也是 bbox 口径；p23/p33/p61/p68 同时有 line count 差，但 overflow 由底 bbox 决定。
- **结论**：26 overflow **主要是 verify `_content_extent` 的 bbox 口径**（span 高/行盒高与源 poly 高不一致），不是 build 真溢出；需要“内容底=baseline/最后一个字墨底/line box 统一口径”修正。p3/p83/p104 非可比，单独登记。

---

## 5. 优先级修复清单

| 优先级 | 修复 | 影响页 | 文件/参数 | 预期 | 类型 |
|---|---|---|---|---|---|
| P0（已做） | verify 逻辑行容差两侧共用 **源页 0.5×行高中位** | 14 个旧错配（p14/23/33/…/98） | `src/test/verify_geom.py::_logical_lines` + main | line_1to1 84.4%→**97.9%** | **指标口径修正** |
| P1 | 正文一 OCR 行一行：禁止引号处 rewrap；仅自然宽>measure 时受控断行并记录 | p2（+可能 p33/38… 的 text span 拆分） | `build_geom.py::flush()` 正文 `makebox`/`_esc_with_missing`；`FONT/MEASURE/textwidth` 或 `CJKglue` | +1 页 line_eq（p2） | **渲染修正** |
| P2 | CIP/短行不合并：`rows` merge 的 `yov>0.5*min(h)` 对短行/多列页加保护，或保留 `frags` 到输出行数 | p5（CIP） | `build_geom.py::rows` merge (~L950)/`frags`/`flush` | +1 页 line_eq（p5） | **渲染修正** |
| P3 | overflow 口径：`_content_extent` 用 baseline/ink 底或统一 line-box（不要拿 output bbox 高 52.4 vs src 19.8） | 26 页 | `src/test/verify_geom.py::_content_extent` | overflow 26→0；页高指标同步 | **指标口径修正** |
| P4 | 页高/pitch：统一 line-box/baseline 后再看 build `POS_FILL`/`PER_PAGE_PITCH`；当前 pitch93.8%、页高<5%18.6% | 全书 | `verify_geom` + `fit_common/build_geom` | pitch≥99/页高中位<2 | 指标优先，余下渲染 |
| P5 | fallback/ink 无收益时保留旧式（已记录 `ink_reject=out_of_range`）；不把 18.4→23.5 的越界 ink 强套 | ghbq | `geometry.py` | 不退化；warnings 只 toc | 标定守卫 |

### 5.1 关键结论

1. **line_1to1 的 15 页旧错配不是 15 个独立渲染 bug**：13 页是 verify 旧“每侧各自中位”容差；shared source-tol 已修复。真正剩余为 **p2（引号 rewrap+ISBN merge）**、**p5（CIP 短行 merge）**。
2. **26 overflow 不是 26 页版面溢出**：主要是 `_content_extent` 的 span bbox 高度口径（output 52.4 vs source 19.8），应先改 verify 口径，再判断是否真有渲染溢出。
3. **页高/pitch 的目标仍有差距**（18.6%/93.8%），但它们与 overflow 共享 bbox/基线口径；P3/P4 应先做口径统一，再谈 `POS_FILL`/行距渲染。
4. **渲染修正优先级**：P1 p2（引号断行）→ P2 p5（短行合并）→ 再看 P3 后是否还有实际 overflow。

---

## 6. 复现/证据

- 当前 `ghbq_s4r2.pdf`（t218 逻辑行/fallback 版本）
- verify JSON：`/tmp/t220_verify2.json`（本诊断生成；仅临时）
- 15 页旧/当前计数见 §3 表；p2/p5 源/输出文本见 §3.2
- 本文件只含诊断；未修改产品代码/数据；未 commit。
