# PaddleOCR-VL 知识同步

> 来源：GitHub 仓库 + 官方文档 + Claude Code 会话 4d5994b7 + Hermes 独立爬取
> 日期：2026-06-01
> 最新版本：PaddleOCR 3.6.0 / PaddleOCR-VL-1.6

## 1. prompt_label 枚举值（仅 use_layout_detection=False 时生效）

源码：`paddleocr/_pipelines/paddleocr_vl.py` → PaddleX `pipeline.py:617-624`

| 值 | 用途 | 自动触发 |
|---|---|---|
| `ocr` | 纯文本识别（段落级） | — |
| `spotting` | 文本检测+识别（逐行坐标） | — |
| `formula` | 公式识别（LaTeX） | — |
| `table` | 表格识别（Markdown table） | — |
| `chart` | 图表解析 | **自动开 use_chart_recognition** |
| `seal` | 印章识别 | **自动开 use_seal_recognition** |

### Spotting 模式详解（pipeline.py:467-470, result.py:170-217）

VLM 原始输出格式（每行一个检测框）：
```
x1,y1 x2,y2 x3,y3 x4,y4: 识别文字
```

解析后结构：
```python
spotting_res = {
    "rec_polys": [...],   # (n×4×2)
    "rec_texts": [...],
}
```

特殊参数：
- min_pixels=112896, max_pixels=1605632（比普通 OCR 大 ~60%）
- skip_special_tokens=False（保留坐标解析所需的特殊 token）

## 2. use_layout_detection 行为差异

| 维度 | True（默认） | False |
|------|-------------|-------|
| 处理流程 | DocPreprocessor → LayoutDetection → VLRecognition | DocPreprocessor → VLRecognition（全页） |
| 区域划分 | 自动检测多个 block | 整页一个 block，bbox=[0,0,w,h] |
| 识别 prompt | 自动按 label 匹配 | 由 prompt_label 决定 |
| 输出粒度 | 多个 PaddleOCRVLBlock | 单个 block，label=prompt_label |
| 模型依赖 | 必需 LayoutDetection 模型 | 不需要 |
| prompt_label 可用 | ❌ | ✅ |

## 3. markdown_ignore_labels（pipeline.py:163-173）

默认值：
```python
["number", "footnote", "header", "header_image", "footer", "footer_image", "aside_text"]
```

- footnote 在生成 Markdown 时被跳过，但有特殊路径：convert_md_page() 中通过 `<div class="footnote">` 单独排版
- image/chart/table 也不参与文本排序（SKIP_ORDER_LABELS 控制）

## 4. vlm_extra_args 分辨率控制

```python
vlm_extra_args = {
    "ocr_min_pixels": 1024, "ocr_max_pixels": 4096,
    "table_min_pixels": 2048, "table_max_pixels": 8192,
    "chart_min_pixels": ..., "formula_min_pixels": ..., "seal_min_pixels": ...,
}
```

## 5. AI Studio REST API 要点

- 端点：`https://paddleocr.aistudio-app.com/api/v2/ocr/jobs`
- 认证：`Authorization: Bearer <token>`，token 存 `/tmp/paddle_token`
- 模型：PaddleOCR-VL-1.6
- 配额：40,000 页/天
- 请求方式：异步 jobs → 创建 → 轮询(5s间隔) → jsonUrl → 下载
- spotting 参数组合：
  ```json
  {"model": "PaddleOCR-VL-1.6", "optionalPayload": "{\"useLayoutDetection\": false, \"promptLabel\": \"spotting\", \"temperature\": 0}"}
  ```
- **AI Studio API 支持 promptLabel（已验证可用，旧版 422 问题已修复）**

## 6. API 参数名对照

| AI Studio REST (camelCase) | Python 库 (snake_case) |
|---|---|
| `promptLabel` | `prompt_label` |
| `useLayoutDetection` | `use_layout_detection` |
| `formatBlockContent` | `format_block_content` |
| `markdownIgnoreLabels` | `markdown_ignore_labels` |

注意：`optionalPayload` 内部的参数名遵循 Python 库的 snake_case。

## 7. 版本演进

| 版本 | 日期 | 关键特性 |
|------|------|---------|
| v3.3.0 | 2025.10 | PaddleOCR-VL v1：0.9B VLM，109 语言 |
| v3.4.0 | 2026.01 | VL-1.5：94.5% OmniDocBench，异形框，印章，111 语言 |
| v3.5.0 | 2026.04 | Transformers 集成，Office→Markdown，PaddleOCR.js |
| v3.6.0 | 2026.05 | VL-1.6：96.3% OmniDocBench v1.6，spotting 大幅提升 |

## 8. 项目流水线关键规则（来自现有实践）

- 使用 spotting 模式做行级扫描件 OCR（已验证可行）
- 脚注检测用状态机：遇 ①②③ 开头的行即触发，后续行归脚注
- 页码过滤：block_bbox 底部 8% + 纯数字
- `re.sub(r'</sup>\s+', ...)` 会吞 `\n\n`，必须用 `[ \t]+` 代替 `\s+`
- 缩进用全局 `\parindent=0pt` + 显式 `\hspace{2em}`，不用 `\everypar` hack
