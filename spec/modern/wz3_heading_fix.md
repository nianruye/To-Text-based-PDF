# Spec: wz3 标题识别修复（p54/p55）

## 目标
修复 wz3 行级版三个标题识别问题：
1. p54 L0 '第四章宗周时期"封建"制度之进展'(页眉,6%边缘) 被当标题
2. p54 L1 '语可知)...'(正文第一行) 被标题续行传播当标题
3. p55 '第二编'/'周代后期'(h=93 超大字) + '序言'(h=58 居中) 没识别成标题

## 根因
1. **is_hdr 边界**：PAGE_H=876, page_px_h=2433.3, 0.06*pph=146.00。p54 L0 y0=146 不<146.00(边界相等) -> is_hdr=False -> 进 flow 被 is_head('宗周时期...' core in toc_map) 当标题
2. **续行传播**：L0 被当标题后,L0 无结尾标点 + L1 x0<=body_left+indent_thr -> L1 被当 L0 续行标题(L720-725)。修问题1后此问题连带解决
3. **is_big/is_tall 阈值**：H_BODY=56, is_big 阈值 56*1.8=100.8('第二编' h=93<100.8 漏判), is_tall 阈值 56*1.1=61.6('序言' h=58<61.6 漏判);且 '第二编' x0=184<body_left(189) 不 is_centered,靠不了 is_centered+is_tall

## 方案

### 改动1: 页眉共识兜底(修问题1+2)
is_hdr(L635) + page_header_raw(L399): `y0<0.06*pph` 或 `y0<0.10*pph 且 _match_canon_hdr(t)`。
新增 `_match_canon_hdr(t)`: difflib SequenceMatcher 与 CANON_HDRS 最高 ratio>0.8(复用 L701-703 共识吸附模式)。
- p54 L0 '第四章...'(6%,匹配共识) -> is_hdr=True 跳过 flow + 渲染页眉; L1 不传播
- wz1 p2 '中央编译局文库'(6.8%,不匹配共识) -> is_hdr=False 进 flow 不丢失

### 改动2: is_big 阈值 H_BODY*1.8 -> H_BODY*1.5(修 '第二编'/'周代后期')
L650: `h > H_BODY*1.8` -> `h > H_BODY*1.5`(100.8->84, '第二编' h=93>84 ✓)。
正文 h~51-63 <84 不误判。

### 改动3: 居中短行标题(修 '序言')
L655 is_head_heur: 加 `or (is_centered and h>H_BODY and len(t.strip())<8 and t 不以句号结尾)`。
'序言' 居中+len=2+h=58>56 -> 标题。正文满宽不 is_centered,不误判。

## 约束
- 只动 is_hdr/page_header_raw(页眉共识) + is_big 阈值 + is_head_heur(居中短标题)
- 不改 _heading_core / _head_level / 续行传播逻辑(问题2 随问题1解决)
- 不加 fallback;中文注释+UTF-8,无 emoji
- wz1 无回归(pitch ≥96.7%,页数 1:1)

## 测试点
- _match_canon_hdr: 匹配共识页眉 True('第四章...'),不匹配 False('中央编译局文库')
- is_big 阈值: h=93>H_BODY*1.5 判大字(h=63 不判)
- 居中短标题: '序言' 居中+len<8+h>H_BODY -> 标题
- p54: L0 页眉(居中小字+hrule), L1 正文
- p55: '第二编'/'周代后期'/'序言' 大字标题
- wz1 无回归

## 验收标准
- wz3 p54 L0 页眉居中+分界线(不当标题), L1 正文
- wz3 p55 '第二编'/'周代后期'/'序言' 识别为标题(大字)
- wz3 pitch ≥85.4%, wz1 pitch ≥96.7%(无回归)
- 全单元测试 PASS
