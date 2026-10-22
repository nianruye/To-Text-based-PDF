# 竖排破折号改成一条连续竖线（不是两个横线，也不是两个竖线拼接）

## 背景一句

竖排繁体书里源书的破折号是**一条连续的竖线**。我们的产物现在是**两个横线**（用了横排字形 U+2014），
换成竖排字形 U+FE31 之后又变成**两条竖线中间有缝**（用户两个都指出来了）。

## 现象与复现

```bash
cd /opt/test
# p57 有真破折号「論金瓶梅這部書——導讀」
rm -rf /tmp/vd && env VERT_PAGES=57 VERT_TMP=/tmp/vd /usr/bin/python3 src/pipelines/build_vert.py \
    data/wz7_full/wz7_full_spotting_lines_patched.json \
    data/wz7_full/wz7_full_spotting_coords.json /tmp/vd.pdf source_pdf/wz7.pdf
```

产物文本层：`論金瓶梅這部書——導讀`（改前）→ `論金瓶梅這部書︱︱導讀`（把 VERT_VERT_DASH 打开后）

**用户的两句原话**（按顺序）：
1. 「但是真的破折号 应该是一个竖线 ，但是你给我的PDF中是两个横线  如p57」
2. 「源书就是一条竖线 而不是两条竖线拼接的」

## 已实测的判据（不需要你再量，直接用）

**字体侧**（`NotoSerifCJK-Regular.ttc`，JP/TC 两个 face 一致，upem 1000）：

| 码位 | 字形 | 墨迹 bbox | 宽高比 |
|---|---|---|---|
| U+2014 `—` | EM DASH | w 0.803em **h 0.051em** | **15.75**（横线） |
| U+FE31 `︱` | VERT EM DASH | w 0.040em **h 0.858em** | **0.05**（竖线） |

**缝隙的量**：`︱` 的墨高只占 **0.858 格**，格宽 1.0em ⇒ 每格上下各留 **0.071em**，
两个叠起来正中间留 **0.142em** 的缝（25pt 字号下 ≈ **3.5pt**，肉眼可见）。

**全书规模**：源书真破折号 1107 对（已用「引号后紧跟 ——」那批 1019 处是 OCR 误读，已删，
不属本任务；剩下的这批是**真破折号**，见下方「不在本任务范围」）。

## 我试过什么、为什么失败（**别重走**）

| 试法 | 结果 |
|---|---|
| ① 单字转义入口 `_esc_ch` 里把 `—` 映射成 `︱` | ✅ 横变竖了，但留 0.142em 缝 —— 用户不接受 |
| ② `\scalebox{1}[1.166]{︱}` 竖向拉满格 | ❌ `! Undefined control sequence`（竖排文档没加载 graphicx） |
| ③ `\char"FE31` | ❌ 同样 undefined；且经 Python 转义层会变成 `\\char`（被当成 LaTeX 换行命令） |

**结论：并在排字形永远消不掉缝**（字形 advance 天然带 side bearing），这类「连续 / 贯穿」要求
只能画矢量。剩下的路就是 plain TeX 的 `\rule`（TeX 原语，不需要宏包）。

## 代码位置与现状

**唯一出字口 = `src/pipelines/build_vert.py` 的 `_put_tex()`（约 L294）**：

```python
def _put_tex(ch, x_pt, y_pt, F, xs=None, clamp=False):
    xs = XSCALE if xs is None else xs
    ch, F, x_pt, y_pt = _br_put(ch, x_pt, y_pt, F, xs)   # 括号换竖排形态（此处不动）
    if clamp: ...
    body = _vb(r'\fontsize{%spt}{%spt}\selectfont %s' % (round(F,1), round(F,1), _esc_ch(ch)))
    if abs(xs - 1.0) > 1e-6:   # 横向压缩包 special pdf:literal
        ...
    return r'\put(%.1f,%.1f){%s}' % (x_pt * PT2BP, y_pt * PT2BP, body)
```

坐标约定（**别搞反**）：`\put` 的 y 自**页底**向上增大；`y_pt` 是「页高 − 墨基线」；
TeX 里要「再往下移」是 **减小** y_pt。

**当前已落地但不完整的东西**（可以复用、也可以删掉重做）：
- `VERT_DASH_MAP = {'—': '{...}', '―': ..., '–': ...}`（约 L3565）
- `VERT_DASH = os.environ.get('VERT_VERT_DASH', '0') != '0'`（**默认 0 = 关**，约 L3570）
- `_esc_ch()` 里按 `globals().get(...)` 做映射（约 L3575）
- 提交 `6238053`

开关默认是关的，所以现在构建行为和改动前一致。你可以在它上面改，也可以推翻重做。

## 修法方向（两个选项，你定实现）

**选项 A（推荐，改动面最小）：每个 `—` 各画一条「满一整格」的竖线，两条相接即无缝**

在 `_put_tex` 里，当 `ch` 属于破折号类且开关打开时，把 `body` 换成 `\rule`：

```python
body = r'\rule{%.4fpt}{%.4fpt}' % (宽度, 高度)
```

- **宽度** = `0.040 * F`（字体实测的墨宽比，建议做成模块级常量 + env 覆盖）
- **高度** = **该列的格高（step）**，不是 `F` —— 竖排里一格的 advance 是 `step`，各列不同
  （源书各列 step 实测 18-48pt 不等；用 `F` 会在字号与步进不等的地方留缝或超出）
- **位置**：`\rule` 默认坐在基线上向上长，需要用 `\rule[lift]{w}{h}` 的 lift 把这一格
  精确对齐到「第 i 格的 [T+i*step, T+(i+1)*step]」区间，且**横向居中在列心**

  ⚠️ `_put_tex` 现在**拿不到 step**。最省的传递方式 = 给 `_put_tex` 加一个可选参数
  （如 `rule_h=None`），由 `col_puts` 传该列 step；**不要为此改全局状态**。

**选项 B：在 `col_puts` 里把连续两个 `—` 合并成一次调用，画一条高 2×step 的线**

更直接（一条线一次画完，几何天然连续），但要在行文本层面做配对，
`col_puts` 里字符循环的改动面比 A 大，且要考虑 `fit_gaps` 插空格、标点单独定位等交互。

**我倾向 A**：不动文本循环，只在出字口按「本格 = 一整格」画线，两条天然相接。

## 验收标准（逐条，缺一不算完成）

1. **p57 连续竖线**：裁 `x795.7` 附近 `y600-900`，沿 y 逐 0.5pt 量墨迹，
   **最大空隙 ≤ 1pt**（现在是 3.5pt）；且线的**总高度 ≈ 2 个 step**、横向居中在列心 ±1pt。
2. **不能把西文侧排的破折号也竖过来**：源书 p29 那类「整行侧排的拉丁文字」里的破折号
   **本来就是横向长横线**（代码里 `LAT_DASH` / `_ROT_K['dash_*']` 那套专门标定过）。
   验证：p29 单页构建，逐字对比改前改后，**西文行不得有任何位置/字形变化**。
3. **wz6 零回归**（有版框书）：`vert.tex` 与改前**逐字节相同**（基线 md5 见下）。
4. **474 测试全绿**：`/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q`
   - ⚠️ ast 抽取式单测的合成命名空间不认识新增模块级常量 → 在函数里用
     `globals().get('NAME', 默认值)` 取值（别改测试文件，除非常量要被直接断言）
5. **p57 文本层**：`—` 还在不在？**允许两种做法，但要在报告里写明选了哪个**：
   - 保留（`\put` 里同时放一条透明/零宽的 `—` + 一条 rule）→ 可搜，但要多一层
   - 丢弃 → 不可搜。**丢弃必须登记**：全书真破折号 1107 处里有一对是「——」占两格，
     丢掉等于少 2000+ 个字，verify 的字符量会掉 —— 那就属于**数据口径变化**，
     必须同时说明。

## 不在本任务范围（不要顺手做）

1. **冒号后缺开引号 379 处**（另一个机制，需要插到列首，会挤动整列 → 属设计变更，用户要拍板）
2. 列首 `。` 687 处 / 列首 `，` 1348 处 违反避头尾
3. 残余引号失衡 +276
4. append 的 `﹂` 落位偏低约一格
5. 书耳「回目 + 页码」粘成一列
6. 那 1019 处「闭引号后紧跟 `——`」**已经删掉了**（用户核对源图确认源书没破折号），
   `src/tools/fix_vert_dash_misread.py` 是那个补丁，**不要再动它**

## 关键命令

```bash
# 单页构建
rm -rf /tmp/vd && env VERT_PAGES=57 VERT_TMP=/tmp/vd /usr/bin/python3 src/pipelines/build_vert.py \
    data/wz7_full/wz7_full_spotting_lines_patched.json \
    data/wz7_full/wz7_full_spotting_coords.json /tmp/vd.pdf source_pdf/wz7.pdf

# 全量测试
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q

# wz6 零回归基线（有版框书，改完必须逐字节相同）
#   build_vert.py + data/wz6/wz6_spotting_{lines,coords}.json + source_pdf/wz6.pdf
#   基线 vert.tex md5 = c2fdfa0e63614e61364a74f02d13ac1d
#   注：当前工作树在这条上的 md5 是 ae9d2f52（3 处边注自位，是**另一件**遗留，不是你造成的），
#       所以比的是「你改之前」vs「你改之后」两次自己跑的结果，不是跟 c2fdfa0e 比。

# 量墨迹连续性（拿去改成你的验证脚本）
#   裁 x±8pt 的窄窗，沿 y 逐点 (gray<185).mean(axis=1) > 0.02 判有墨，统计最长连续空隙
```

## 纪律

- **每验证一步立刻 commit**，改完先跑全量测试再往下走
- **不要 git reset**，不要动回归基线数据，不要格式化整个文件
- **不要只改注释就以为改了逻辑**；注释里别写反斜杠单词（`\rule` 这类会在转义层塌成控制字符）
- 报告里必须逐条对上「验收标准」的 5 条，贴实测输出
