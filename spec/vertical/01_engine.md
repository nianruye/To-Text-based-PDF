# 01 引擎链（竖排渲染）

**状态**：implemented（wz6 全书 231 页跑通）
**实现锚点**：`src/pipelines/build_vert.py` L872-912（preamble）、L936-937（编译命令）
**关联**：GitHub commit `ddc8761`（v1.4 引擎链定案）

## 目标

竖排（tate）繁体书的渲染引擎链：横排管线的 xelatex + xeCJK **没有** 竖排能力
（见 `docs/cards/01_架构梳理行动卡.md` L81-82 记录的「竖排能力缺口」），竖排必须换引擎链。

## 背景（4 轮实验，别再换）

| 轮 | 方案 | 结果 | 原因 |
|---|---|---|---|
| 1 | xelatex + bxjscls(`tate`) | ✗ | bxjscls 无 tate 选项（jsclasses 系只有 pLaTeX/upLaTeX 版有 tate） |
| 2 | platex（pTeX） | ✗ | pTeX 汉字编码是 JIS 系（JY1/JT1），**丢繁体字** |
| 3 | **upLaTeX + tarticle.cls** | ✓ | upLaTeX 汉字编码是 Unicode（JY2/JT2）；`tarticle.cls`（jsclasses 竖排版）默认 tate |
| 4 | **+ pxchfon[unicode] + Noto Serif CJK TC（ttc index=3）** | ✓ | 繁体字形（TC），`dvipdfmx` 出 PDF |

**定案引擎链**：

```
upLaTeX(编译) + tarticle.cls(文档类, 默认 tate) + pxchfon[unicode](字体选择)
  + Noto Serif CJK TC (NotoSerifCJK-Regular.ttc 子字体 index=3) + dvipdfmx(输出)
```

字体子字体索引：`\setminchofont[3]{NotoSerifCJK-Regular.ttc}` 的 `[3]` = ttc 内 index，
**JP=0 / SC=2 / TC=3** —— 竖排繁体书必须用 3（用 0 出日文字形，用 2 出简体字形）。
`\setgothicfont[3]{NotoSansCJK-Regular.ttc}` 同理（标题/粗体）。

## JY1/JT1 报错修法（v2 增量）

**现象**：每页刷 3 类报错 —— `Encoding scheme 'JY1' unknown`、`Unknown symbol font 'mincho'`、
`KANJI Encoding scheme 'JT1' unknown`。

**根因**：`tarticle.cls` L617-621 + `tsize10.clo` L27-28 硬编码 **pTeX** 的汉字编码 JY1/JT1（JIS 系），
upLaTeX 下这些编码未定义。依据：jsclasses 自己的写法是
`\def\jsc@JYn{\if@jsc@uplatex JY2\else JY1\fi}`（pxchfon L91 同规则）——
upLaTeX 的正确编码是 JY2/JT2。

**修法**（preamble L885-895）：
1. `\documentclass[10pt,disablejfam]{tarticle}` —— 跳过类里坏掉的 mincho 数学字体声明；
2. 按 jsclasses 的 upLaTeX 分支用 **JY2 重建**：`\DeclareSymbolFont{mincho}{JY2}{mc}{m}{n}` +
   `\DeclareSymbolFontAlphabet{\mathmc}{mincho}` + bold 变体（等价还原数学模式汉字 `\mathmc/\mathgt`）；
3. **先 `\let\mathgt\@undefined` 再 `\DeclareMathAlphabet{\mathgt}{JY2}{gt}{m}{n}`**
   —— 否则 "already defined" 报错；
4. `\kanjiencodingdefault` 改 JY2 消除每页报错。

**证据**：修前/修后渲染**逐像素完全相同（0 差异像素）** —— 修法只消报错，不动字形。
剩余 1 处 JT1 报错发生在类加载期（`tsize10.clo` 内），文档内无法拦截，且 upLaTeX 下该命令本就被忽略。

## 输入 / 输出

- **输入**：OCR lines/coords JSON、源 PDF（取精确页幅、源图墨迹）
- **输出**：`vert.tex`（`$VERT_TMP`，默认 `/tmp/vert_<输出文件名 stem>_run`）→ `uplatex` → `vert.dvi` → `dvipdfmx` → 目标 PDF
- **退出码**：0 = 正常（含 SRC 缺省的 3 参数调试调用）/ 1 = 输入文件缺失或编译失败（#18；判据见
  [governance/PIPELINE_BEHAVIOR.md](../governance/PIPELINE_BEHAVIOR.md) V6 —— uplatex 对正常成功编译也返回 rc=1，只把类加载期 JT1 报错列为容忍项）

## 约束

1. 编译必须在 `VERT_TMP` 目录内执行（`uplatex vert.tex` + `dvipdfmx vert.dvi`，L936-937）；
   临时目录默认按输出文件名 stem 分离（`/tmp/vert_<stem>_run`，#20 已修）-> **不同产物名的实例可并行**；
   **同名产物**仍不能并行（共用 `vert.tex/dvi/pdf`），需显式用不同 `VERT_TMP` 分开。
2. `\pagestyle{empty}`：页码不用 LaTeX 页脚机制，全部由 eso-pic 绝对定位画（见 [03_marginalia.md](03_marginalia.md)）。
3. `\parindent=0pt`：竖排不做段首缩进（缩进由源书列断点自然表达）。
4. 纸型：`\special{papersize=W,H}` 的 W/H = 目标 pt × **1.00375**（dvipdfmx 按 bp 解析，
   见 [02_tate_layout.md](02_tate_layout.md)）；同时 `\setlength{\paperheight/paperwidth}` 设真页尺寸，
   否则 eso-pic 锚点落在 A4 默认纸左角（内容整体偏 ~400pt 出页）。

## 验收方法

1. `uplatex` 日志无 JY1/JT1 报错（除类加载期那 1 处 JT1）；
2. `verify_vert.py` 页数 1:1 且页幅与源书众数纸型一致（相对差 < 0.5%）；
3. 抽查输出字形为 TC（如「説/說」形、"為" 的 TC 写法）——与源书一致。

## 测试点

- 231 页编译成功、无缺页（`verify_vert.py` a 项）
- 引擎链相关 env 关闭（`VERT_SPECIAL=0 VERT_FRAME=0`）仍能出全书（纯文字流基线）
