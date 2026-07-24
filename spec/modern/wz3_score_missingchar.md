# Spec: PP-OCRv6 score 检测古字识错行 + 整行贴图

## 目标
用 PP-OCRv6 的 rec_scores(识别置信度)检测 OCR 识错的古字行(甲骨文/金文图),
低 score 行整行贴源图保留原貌。解决 VL 识错字(无 score 信号)无法自动检测的问题。

## 根因
- VL(PaddleOCR-VL-1.6)识古字成错字(如"罗梁尚币""笃"),但 API 不返回 rec_scores
  (spotting_res 只有 rec_polys/rec_texts),无法自动判断哪些是识错字
- PP-OCRv6 返回 rec_scores,且古字识错行 score 低(p68 实测:
  '新郢爰' 0.673, '私郢爰饼金' 0.783, '毛尹梁尚币' 0.827;正常行 0.93-0.99)
- 阈值 ~0.85 能区分古字识错(<0.85)vs 正常文字(>0.9)

## 方案

### 数据采集: PP-OCRv6 跑 wz3 拿 score
`src/ocr/run_ppocrv6_scores.py`: 每页 PNG -> PP-OCRv6 API -> ocrResults[0].prunedResult
(rec_texts/rec_polys/rec_scores) -> 存 {key: [[poly, score, text], ...]} 到
data/wz3/wz3_ppocrv6_scores.json。PP-OCRv6 文字质量差,只用 score,文字仍用 VL。

### build_geom: 低 score 行整行贴图
- 加载 wz3_ppocrv6_scores.json,得每页低 score(<0.85)行的 poly 列表
- 渲染 VL 行时,若 VL 行的 y0 落在任一低 score poly 的 y 范围内 -> 整行贴源图
  (剪源 PDF 该 poly 位置, \includegraphics 替代 VL 文字)
- 高 score 行 -> VL 文字化(不变)

### 行对齐(VL vs PP-OCRv6)
VL 行 y0 在 PP-OCRv6 低 score poly 的 [y_min, y_max] 内 -> 判为同一行 -> 贴图。
两 OCR 都是 200dpi px 坐标,y 对齐可靠。

## 约束
- 只动 build_geom 加载 score 数据 + 低 score 行贴图逻辑
- VL 文字/排版逻辑不变(高 score 行用 VL)
- 不加 fallback;中文注释+UTF-8,无 emoji
- wz1 无回归(无 score 数据时不贴图,行为同前)

## 测试点
- p68 古字表: 低 score 行(郢爰/梁尚币)整行贴图,器物名《骰氏盘》等若高 score 则文字化
- p470/p513 正常表格: 高 score(>0.9)不贴图,文字化
- p15 "笃"(识错古字): 低 score -> 贴图
- wz1 无 score 数据 -> 不贴图(行为同前)

## 验收标准
- p68 古字表识错行贴图(甲骨文保留)
- p470/p513 正常表格不贴图(文字化)
- wz3 pitch 无大回归(>=84%), wz1 无回归
- 全单元测试 PASS

## 已知局限
- PP-OCRv6 识别质量差,低 score 阈值(0.85)可能漏判/误判(某些识错字 score>0.85)
- 行对齐靠 y(VL vs PP-OCRv6 行 poly 可能不完全对齐,偶发错配)
- PP-OCRv6 跑全书 20-30 分钟
