#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""异体字归一化（battle6/t25）：以 OpenCC t2tw（台湾标准）为主 + 自建补充表。

覆盖：爲/為、裏/裡、綫/線、卻/却、啟/啓、丟/丢、廝/厮、敎/教、趕/赶、眞/真、囑/嘱、
     幷/并、說/説、敘/敍、偽/僞、旣/既、衆/眾、竝/並、况/況、决/決、况/況 等。
用法：
  from variant_norm import norm_char, norm_text, build_map
  python3 variant_norm.py --dump tmp_vert/battle6/variant_map.json
"""
import argparse, json, sys

try:
    from opencc import OpenCC
    _cc = OpenCC('t2tw')
except Exception:
    _cc = None

# 自建补充（opencc 未覆盖或方向不对的常见异体）
EXTRA = {
    '爲': '為', '裏': '裡', '綫': '線', '卻': '卻', '启': '啟', '啓': '啟',
    '丢': '丟', '厮': '廝', '敎': '教', '赶': '趕', '眞': '真', '嘱': '囑',
    '幷': '並', '説': '說', '敍': '敘', '僞': '偽', '旣': '既', '衆': '眾',
    '竝': '並', '况': '況', '决': '決', '减': '減', '凑': '湊', '唇': '脣',
    '寃': '冤', '寳': '寶', '冨': '富', '刦': '劫', '刧': '劫', '刄': '刃',
    '匀': '勻', '匂': '匈', '即': '即', '却': '卻', '厠': '廁', '厦': '廈',
    '厨': '廚', '厩': '廄', '叅': '參', '叠': '疊', '只': '只', '呌': '叫',
    '咏': '詠', '唧': '唧', '啓': '啟', '啾': '啾', '嗞': '嗞', '噉': '啖',
    '嘱': '囑', '囘': '回', '囬': '回', '囪': '窗', '圅': '函', '圗': '圖',
    '埜': '野', '堦': '階', '壊': '壞', '壌': '壤', '壠': '壟', '壻': '婿',
    '夀': '壽', '奨': '獎', '妬': '妒', '姉': '姊', '姗': '姍', '娬': '嫵',
    '媿': '愧', '嫰': '嫩', '嬾': '懶', '孄': '懶', '宁': '寧', '宂': '冗',
    '寉': '鶴', '寛': '寬', '尅': '剋', '尠': '鮮', '尢': '尤', '尲': '尷',
    '屓': '贔', '屛': '屏', '岀': '出', '峯': '峰', '嵗': '歲', '巓': '巔',
}

def norm_char(ch):
    if not ch:
        return ch
    if ch in EXTRA:
        return EXTRA[ch]
    if _cc is not None and ord(ch) > 0x2E80:
        try:
            out = _cc.convert(ch)
            if len(out) == 1:
                return out
        except Exception:
            pass
    return ch

def norm_text(s):
    return ''.join(norm_char(c) for c in s)

def build_map(chars):
    m = {}
    for c in chars:
        n = norm_char(c)
        if n != c:
            m[c] = n
    return m

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dump', default='')
    a = ap.parse_args()
    if a.dump:
        # 以全书 OCR 用字为样本，导出实际生效的映射
        import json as _j
        lines = _j.load(open('data/wz7_full/wz7_full_spotting_lines_patched.json', encoding='utf-8'))
        chars = set(''.join(''.join(str(t) for t in v) for v in lines.values()))
        m = build_map(chars)
        _j.dump({'opencc': 't2tw' if _cc else None, 'extra': EXTRA, 'active': m,
                 'n_active': len(m)}, open(a.dump, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('active mappings', len(m), '->', a.dump)
