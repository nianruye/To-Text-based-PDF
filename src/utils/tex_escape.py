#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LaTeX 转义共享模块。保留三管线转义差异（不统一），按 mode 分发。

差异（unit 测试 src/test/unit/test_pure_funcs.py 锁定 classic；geom/v13 待补）：
- v13   escape_tex  : 保留 \\ { }（\\->\\textbackslash{}, {->\\{, }->\\}），转义符单反斜杠 \\%
- geom  _esc_chars  : 删**单**反斜杠 + { }，转义符单反斜杠 r'\\%'，无省略号归一化
- classic _esc_chars: 删**双**反斜杠 \\\\ + { }（单反斜杠保留），转义符双反斜杠 r'\\\\%'（疑似bug，保留现状），有省略号归一化
"""
_CIRC = {'①':'\\textcircled{1}','②':'\\textcircled{2}','③':'\\textcircled{3}','④':'\\textcircled{4}','⑤':'\\textcircled{5}','⑥':'\\textcircled{6}','⑦':'\\textcircled{7}','⑧':'\\textcircled{8}','⑨':'\\textcircled{9}','⑩':'\\textcircled{10}'}

_V13_PAIRS = [('\\','\\textbackslash{}'),('{','\\{'),('}','\\}'),('&','\\&'),('%','\\%'),('#','\\#'),('$','\\$'),('_','\\_'),('~','\\~{}'),('^','\\^{}')]
_GEOM_PAIRS = [('\\',''),('{',''),('}',''),('%',r'\%'),('&',r'\&'),('#',r'\#'),('_',r'\_'),('^',r'\^{}'),('~',r'\textasciitilde{}'),('○','〇'),('【','〔'),('】','〕'),('Ⅱ','II'),('Ⅰ','I'),('Ⅲ','III'),('Ⅳ','IV'),('Ⅴ','V')]
_CLASSIC_PAIRS = [('\\\\',''),('{',''),('}',''),('%',r'\%'),('&',r'\&'),('#',r'\#'),('_',r'\_'),('^',r'\^{}'),('~',r'\textasciitilde{}'),('○','〇'),('【','〔'),('】','〕'),('⋯⋯','…'),('⋯','…'),('……','....'),('…','.'),('Ⅱ','II'),('Ⅰ','I'),('Ⅲ','III'),('Ⅳ','IV'),('Ⅴ','V')]


def escape_latex(text, mode='classic'):
    """通用 LaTeX 转义。mode='v13'/'geom'/'classic'，保留三套差异（不统一）。

    v13 分支不加圈码/○/【】（v13 escape_tex 不处理）；geom/classic 分支加 _CIRC。
    """
    if mode == 'v13':
        for a, b in _V13_PAIRS:
            text = text.replace(a, b)
        return text
    pairs = _CLASSIC_PAIRS if mode == 'classic' else _GEOM_PAIRS
    for a, b in pairs:
        text = text.replace(a, b)
    for c, d in _CIRC.items():
        text = text.replace(c, d)
    return text
