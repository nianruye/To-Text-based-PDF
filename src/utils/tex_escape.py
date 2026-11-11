#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LaTeX 转义共享模块。保留三管线转义差异（不统一），按 mode 分发。

差异（unit 测试 src/test/unit/test_pure_funcs.py + test_audit_features.py 锁定）：
- v13   escape_tex  : 保留 \\ { }（\\->\\textbackslash{}, {->\\{, }->\\}），转义符单反斜杠 \\%
                      反斜杠先换占位符、最后还原 \\textbackslash{}，防其 {} 被 {/} 规则二次转义（issue #2 已修）
- geom  _esc_chars  : 删**单**反斜杠 + { }，转义符单反斜杠 r'\\%'，无省略号归一化
- classic _esc_chars: 删**双**反斜杠 \\\\ + { }（单反斜杠保留），转义符单反斜杠 r'\\%'（issue #1 已修：
                      原 r'\\\\%' 会输出 LaTeX 换行 \\\\，把后续文字推到下一行），有省略号归一化

已知分叉（issue #11，需 spec 拍板，本轮不动）：geom 删单反斜杠 / classic 删双保留单。
因此输入本身已含 `\\%`（单反斜杠 + %）时，classic 的 % 规则会再转义一次得到 `\\\\%`；
OCR 正文无此形态（v13 因先占位不受影响）。
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

# ── 横排标点形态归一化（t275）────────────────────────────────────────────
# 只处理 CJK 上下文中的 ASCII 标点；数字/拉丁相邻、行首尾、已全角不动。
# 归一化在 build_geom 文本装配阶段调用；本函数幂等，返回 (out, changes)。
_ASCII_TO_FULL = {',': '，', ';': '；', ':': '：', '?': '？', '!': '！', '.': '。'}
_SPACE_CHARS = set(' \t\u3000')


def _cjk_context_char(ch):
    """CJK 字符或全角标点；用于归一化左右邻判断。"""
    if not ch:
        return False
    o = ord(ch)
    if 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:
        return True
    # 全角标点只接受句读/括号类；引号/破折号/省略号作为左邻会把拉丁短语后的
    # 英文逗号误判为中文逗号（wz1 p123/p127/p185），因此不作上下文。
    if ch in '，。；：、！？（）【】〔〕':
        return True
    return False


def _nonzero_neighbor(s, i, step):
    # 严格相邻：空格也视为非 CJK，避免把 CIP/版权页的 ASCII 字段冒号/逗号误转
    j = i + step
    return s[j] if 0 <= j < len(s) else ''


def normalize_cjk_punct(text, left_context='', right_context=''):
    """CJK 上下文 ASCII `, ; : ? ! .` -> 全角；幂等。

    `左右两侧都是 CJK（允许空格；行首/行尾可传上一/下一行邻字）` 才替换；返回
    `(out, changes)`，changes 为逐字 `{pos, old, new}`，供审计写入 report。
    """
    if not text:
        return text, []
    out = list(text)
    changes = []
    for i, ch in enumerate(text):
        full = _ASCII_TO_FULL.get(ch)
        if not full:
            continue
        left = _nonzero_neighbor(text, i, -1) if i > 0 else (left_context or '')
        right = _nonzero_neighbor(text, i, 1) if i < len(text) - 1 else (right_context or '')
        def _ctx_ok(ch, j, step):
            if _cjk_context_char(ch):
                return True
            # 引号本身不是 CJK，但引号内侧是 CJK 时允许（p31 “开始,“在”）；
            # 拉丁短语后的 ” 后逗号（p123/wz1）仍拒绝。
            if ch in '“”‘’':
                k = j + step
                if 0 <= k < len(text):
                    return _cjk_context_char(text[k])
            return False
        left_ok = _ctx_ok(left, i - 1, -1) if i > 0 else _cjk_context_char(left)
        right_ok = _ctx_ok(right, i + 1, 1) if i < len(text) - 1 else _cjk_context_char(right)
        if left_ok and right_ok:
            out[i] = full
            changes.append(dict(pos=i, old=ch, new=full))
    return ''.join(out), changes
