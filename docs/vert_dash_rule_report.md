# 竖排破折号改成一条连续竖线（taskD 报告）

状态：**implemented**（分支 `feat/vert-dash-rule`；spec [spec/vertical/15_vert_dash_rule.md](../spec/vertical/15_vert_dash_rule.md)）

## 1. 问题与用户原话

wz7《金瓶梅詞話》p57 标题「論金瓶梅這部書——導讀」：

1. 改前产物用横排字形 U+2014 -> 画成**两个横线**；
2. 试过的 U+FE31 竖排字形 -> **两条竖线中间有缝**（U+FE31 墨高只占 0.858 格，两格相接正中留 0.142 em）。

用户原话（按顺序）：

> 「但是真的破折号 应该是一个竖线 ，但是你给我的PDF中是两个横线  如p57」
>
> 「源书就是一条竖线 而不是两条竖线拼接的」

结论：并排字形天然带 side bearing，连续/贯穿只能画矢量。采用简报推荐的**选项 A**：
每个破折号在本格画一条**满格高**的矢量竖线，相邻两格首尾相接。

## 2. 实现（§1.0a4）

唯一出字口 `_put_tex()` 新增可选参数 `rule_h`（= 本列 step，bp）；`col_puts` 在逐字循环里按列传参。
`rule_h is None` 时输出与旧实现**逐位相同**。

### 2.1 几何

记 `F` = 字号，`xs` = 横向压缩系数，`step` = 本列排版步进（bp），`INK_ASC` = 墨顶到基线的比例
（默认 0.94，标定趟可覆盖）。

| 量 | 公式 | 说明 |
|---|---|---|
| 线宽 | `w = DASH_RULE_W × F`（默认 0.040） | 字体 U+FE31 墨宽比；`VERT_DASH_RULE_W` 可覆盖 |
| 线长 | `h = step × PT2BP`（TeX pt） | **高度 = 本格 step，不是 F**；两格相接无缝 |
| 竖向偏移 | `lift = (INK_ASC × F − step) × PT2BP` | 基线在格顶下 `INK_ASC·F`，故负 lift 把 rule 底端对齐到格底 |
| 线心 | `xc = x_put + xs × F / 2` | 压缩后字盒中心 = 列心 |
| rule 左缘 | `xr = xc × PT2BP − w / 2` | `\put` 参考点是 rule 左下角 |

竖排第一格的格区间为 `[T + k·step, T + (k+1)·step]`（`T` = 列顶，`k` = 格号）。
两字相邻时第 k 条 rule 的顶端坐标 = 第 k+1 条的底端坐标 -> **几何上无缝**。

### 2.2 文本层

原字 `—` **保留**（不映射 U+FE31），用 PDF 文本渲染模式 `3 Tr` 包住（不可见）：

```
q 3 Tr  <原 _put_tex 的 fontsize/压缩包装> —  Q   +   一条 rule 的 \put
```

- 可搜索 / 可选中；`verify_vert` 的字符量口径不变（**没有丢字**）；
- rule 单开一个 `\put`，与文本层位置互不影响；
- 文本层与改前 **逐字节相同**（实测 p57 `get_text()` 936 字完全相同）。

### 2.3 实测到的两个渲染细节

1. **dvipdfmx 把 `\rule` 画成「描边线」而不是填充矩形**：`page.get_drawings()` 返回 `type='s'`，
   path 长度 = rule 高度、stroke width = rule 宽度。因此两条 rule 的接缝用 path 端点判断，
   实测相邻缝 **−0.001pt**（y 坐标按 `%.2f` 打印，两条各自 ±0.005 的舍入被高度吸收）。
2. **eso-pic FG 的原点跟随 `\paperheight`（TeX pt），而物理页幅是 bp**：p57 的
   `\paperheight=1437pt` 但页真高 1437.01bp = 1442.39TeX pt，整层 FG（正文 + rule）一起上移 5.37bp。
   因 rule 与正文同层、同一 `\put` 参考系，**rule 相对正文格区的位置不受影响**（实测 rule 格顶
   694.19 = 正文格顶 694.19）。

## 3. 验收（逐条对应用户标准）

命令：

```bash
# p57 单页（改后）
rm -rf /tmp/vd_new57c && env VERT_PAGES=57 VERT_TMP=/tmp/vd_new57c /usr/bin/python3 src/pipelines/build_vert.py \
    data/wz7_full/wz7_full_spotting_lines_patched.json \
    data/wz7_full/wz7_full_spotting_coords.json /tmp/new57c.pdf source_pdf/wz7.pdf

# 测量（脚本 tmp_vert/taskD/verify_dash.py，输出存 tmp_vert/taskD/verify_p57.txt）
/usr/bin/python3 tmp_vert/taskD/verify_dash.py /tmp/new57c.pdf source_pdf/wz7.pdf 57
```

### 3.1 p57 连续竖线（最大空隙 ≤ 1pt，总高 ≈ 2 个 step，居中 ±1pt）

```
== 产物: 矢量竖线(rule) 2 条 ==
  x中心 830.00   y 694.19-757.91   长 63.72   线宽 2.77
  x中心 830.00   y 757.91-821.63   长 63.72   线宽 2.77
  合并: y 694.19-821.63 总高 127.44 | 相邻缝: -0.0010
== 产物: 沿 y 逐 0.5pt 墨迹(窄窗 x=830.00±1.5) ==
  有墨 y 694.19-821.69 | 最大空隙 0.00 pt
== 产物文本层 ==
  字符数 936 | "—" 个数 2 | "︱"(U+FE31) 个数 0
== 源书同位置 ==
  竖线 y 736.56-816.81 长 80.25 | 线心 x 829.81 | 粗 5.25
  线心差 0.19 pt | 长度差 47.19 pt
```

- 最大空隙 **0.00pt**（改前两个横线沿 y 的间距 60.5pt；U+FE31 方案的理论缝 0.142em）；
- 总高 **127.44pt = 2 × 63.72**（本列 step 63.72）；
- 线心 **830.00** = 列心 830.00；源书竖线 829.81 -> 差 **0.19pt**（±1pt 内）。

> 简报写的裁窗 x=795.7 是**文本层 span 的左缘**（em 盒左缘），不是线的位置。
> 源书竖线实测在 x=829.8，产物列心 x=830.0；本报告按线的真实位置裁窗测量。

### 3.2 西文侧排不得变化（p29）

```bash
rm -rf /tmp/vd_p29_off && env VERT_PAGES=29 VERT_DASH_RULE=0 VERT_TMP=/tmp/vd_p29_off ... /tmp/p29_off.pdf
rm -rf /tmp/vd_p29_on  && env VERT_PAGES=29 VERT_TMP=/tmp/vd_p29_on ... /tmp/p29_on.pdf
diff /tmp/vd_p29_off/vert.tex /tmp/vd_p29_on/vert.tex
```

结果：**逐字节相同**（diff 无输出）。p29 的破折号在「整行侧排拉丁文」里，走 `_latin_put` 旋转路径，
不经过 `_put_tex`；`_esc_ch` 也不再映射破折号字形。

### 3.3 wz6 零回归（有版框书）

```bash
VERT_TMP=/tmp/vd_wz6_new2 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_new2.pdf source_pdf/wz6.pdf
md5sum /tmp/vd_wz6_new2/vert.tex
# ae9d2f5259e12cff19e680b2a771b37d  (= 任务简报给出的改动前基线)
grep -c '\\rule\[' /tmp/vd_wz6_new2/vert.tex
# 0
```

默认 `VERT_DASH_RULE=nf` 只对无版框伪槽格页生效；wz6 是有版框书，19 个 `—`（9 页）仍走旧路径。

### 3.4 测试全绿

```
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
493 passed, 832 warnings in 16.53s
```

= 474（改前）+ 19 新增（`src/test/unit/test_vert_dash_rule.py`）。新增测试锁：

- `_dash_rule_on` 三档模式（nf/all/0）；
- `_esc_ch` 不再改破折号字形；
- 无 `rule_h` 时输出与旧实现一致（无 rule / 无 3 Tr）；
- 线宽/线心/高度/lift 公式；
- **相邻两条 rule 首尾相接**（差 ≤0.011pt，含打印舍入）且总高 = 2 step；
- 文本层保留原 `—` + `3 Tr`，且非破折号传 `rule_h` 不画线。

### 3.5 p57 文本层（选「保留」）

改前 vs 改后：

```
base chars 936   new chars 936   identical True
dash count base 2 new 2 FE31 0
context new : '...\n書\n—\n—\n導\n讀\n...'
```

`—` 保留在文本层（`3 Tr` 不可见），字符量/文本内容与改前完全相同 -> **不涉及数据口径变化**。

## 4. 附带发现（不在本任务范围，已登记）

1. **patched 数据里仍有 OCR 误读的破折号**。全库 `—` 共 263 个字符：88 对 `——` + 87 个单 `—`，
   其中 24 个单 `—` 紧跟在闭引号后。抽查 p59（「枯燥。」—斯」）与 p118（「茶吃。——我便」）源图：
   源书该处**没有破折号**，只有引号 ﹂ 的直角笔画，OCR 把它读成了 `—` / `——`。
   这与用户已让删除的 1019 处同类；本轮只改渲染、不删数据（简报「不在本任务范围」第 6 条）。
   改后这些假破折号会由「横线」变成「长竖线」，更显眼 -> 建议单独做一次数据审计
   （判据可用源图该格墨迹长度，不能用页号/文本特判）。
2. **线长比源书长**：源书 p57 竖线实测 80.25pt，产物 127.44pt（= 2 × step）。
   这是选项 A「每字满一格」的固有结果（验收要求「总高 ≈ 2 个 step」）；源书破折号字形在格内
   自带约 20-26pt/端的 side bearing。若要与源书等长，需要选项 B（run 配对 + 源图定两端），
   属后续可选优化。
3. **线宽比源书细**：产物 2.77pt vs 源书 5.25pt。默认按简报的字体墨宽比 0.040em；产物整体字重
   只有源书约 69%（taskT 遗留），按同比例字画笔换算约 3.6pt。可用 `VERT_DASH_RULE_W=0.052` 调粗。

## 5. 改动文件

| 文件 | 改动 |
|---|---|
| `src/pipelines/build_vert.py` | §1.0a4 新增常量/`_dash_rule_on`/`_put_tex(rule_h=)`；`col_puts` 传 step；删除旧的 `VERT_DASH_MAP`/`VERT_VERT_DASH`（U+FE31 方案，默认关）；`_esc_ch` 恢复纯转义 |
| `src/test/unit/test_vert_dash_rule.py` | 新增 19 项单测 |
| `spec/vertical/15_vert_dash_rule.md` | 本任务 spec |
| `spec/vertical/README.md` / `spec/README.md` / `AGENTS.md` | 锚点/索引/issue 账本 |
