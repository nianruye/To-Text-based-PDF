#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LaTeX preamble 共享模块。生成 .tex 文件完整文档（preamble + pages_tex + end）。

bit-exact 复制 build_geom/build_classic L930-946 模板（两管线一致）。
_cjk_glue 按 mode 分发（保留差异，else 分支不同）：
- USE_REGION(两管线一致): \\hskip 0pt plus 0.05em minus 0.5em
- geom (非区域): \\hskip 0pt plus 0.5em minus 0.4em
- classic (非区域): \\hskip 0.15em plus 0.35em minus 0.8em（古籍字距更宽，minus 0.8em 充分收缩）

墨高重叠(classic \\[-2pt])/脚注分界(geom \\hrule)在 flush 正文渲染，不在 preamble。
"""


def build_latex(mode, PAGE_W, PAGE_H, MARGIN, USE_REGION, LINESPREAD, pages_tex):
    """生成完整 latex 文档字符串。mode='geom'/'classic' 决定 _cjk_glue。"""
    # 开明制标点(句逗半角占位, 行尾挤压) - 中文出版规范, 全模式开(原生书观感)
    _xeCJKsetup_PunctStyle = '\\xeCJKsetup{PunctStyle=kaiming}'
    if USE_REGION:
        _cjk_glue = '\\hskip 0pt plus 0.05em minus 0.5em'
    elif mode == 'classic':
        _cjk_glue = '\\hskip 0.15em plus 0.35em minus 0.8em'
    else:
        _cjk_glue = '\\hskip 0pt plus 0.5em minus 0.4em'
    return f"""\\documentclass[{PAGE_W}pt,{PAGE_H}pt]{{extarticle}}
\\usepackage[paperwidth={PAGE_W}pt,paperheight={PAGE_H}pt,top=12pt,bottom=30pt,left={MARGIN}pt,right={MARGIN}pt]{{geometry}}
\\setlength{{\\footskip}}{{12pt}}
\\usepackage{{xeCJK}}
\\usepackage{{graphicx}}
\\usepackage{{eso-pic}}   # 边栏旁注(竖排)绝对定位贴回
\\setCJKmainfont{{Noto Serif CJK SC}}   % SC=简体字形(JP 版部分汉字日式写法)
\\setCJKfamilyfont{{heiti}}{{Noto Sans CJK SC}}
\setCJKfamilyfont{{song}}{{Noto Serif CJK SC}}   % song=宋体标题(FONT_TITLE=song 时)
\setCJKfamilyfont{{kai}}{{AR PL KaitiM GB}}   % kai=楷体标题(FONT_TITLE/FONT_SUBTITLE=kai 时, 如 wz1 三级标题)
\\renewcommand{{\\CJKglue}}{{{_cjk_glue}}}   % base 0pt;plus 0em(区域化,不拉伸->字距恒定)或 plus 0.5em(默认,拉伸短行);minus 0.4em 让超长满行收缩齐右不溢出旁注
{_xeCJKsetup_PunctStyle}
\\setlength{{\\parindent}}{{0pt}}\\setlength{{\\parskip}}{{0pt}}
\\pagestyle{{plain}}
\\begin{{document}}
\\linespread{{{LINESPREAD}}}\\selectfont
{chr(10).join(pages_tex)}
\\end{{document}}
"""
