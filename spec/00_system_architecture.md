# Spec: PDF 排版还原系统 - 总体架构

## 系统目标

将扫描型 PDF（图片格式）转换为文字型 PDF，**完整还原源文档的排版结构**（字号、行距、位置、区域、特殊元素），支持多种文档类型。

## 文档类型分类

| 类型 | 特征 | 管线 | 当前状态 |
|---|---|---|---|
| **古籍（刻本/印本）** | CJK 墨高重叠、夹注本双规制、旁注竖排、校注标记 | `src/pipelines/build_classic.py` | ✅ 已实现 |
| **现代书籍** | 段落缩进、脚注、页眉页码、标题层级 | `src/pipelines/build_geom.py` | ✅ 已实现（wz1） |
| **学术论文** | 公式、表格、图表标题、参考文献、摘要 | 待建 | 🔜 规划中 |
| **合同** | 条款编号、表格、签章区域、固定格式 | 待建 | 🔜 规划中 |
| **标书** | 复杂表格、目录、附件、多层标题 | 待建 | 🔜 规划中 |

## 路由机制

### 输入
- 源 PDF 文件
- OCR 数据（PaddleOCR-VL spotting + layout）
- 模式选择（手动 `mode=ancient/modern/paper/contract/bid` 或自动检测）

### 自动检测（待实现）
```
文档特征 -> 类型判定:
- 有〔X〕校注标记 + aside 旁注 + CJK 竖排 -> 古籍
- 有公式/表格/参考文献 -> 论文
- 有条款编号(第一条) + 签章 -> 合同
- 有复杂表格 + 多层目录 -> 标书
- 其他 -> 现代书籍
```

### 输出
- 文字型 PDF（还原源排版）

## 共享基础（所有类型通用）

### 1. OCR 数据层
- **spotting**（行级）：每行文字 + bbox（主数据）
- **layout**（版面）：image/aside_text/number/paragraph_title 等 block
- 来源：PaddleOCR-VL-1.6（useLayoutDetection=False/True）

### 2. 几何标定
- 字号 = 满行宽 ÷ 满行字数
- 行距 = page_pitch（源行间距，spotting y 差中位）
- 版心 = 满行宽（coords x_max × 72/DPI）

### 3. 位置还原
- POSITIONAL=1：每行按源 y 落位（\vspace）
- 两趟校准：pass1 估高 -> ratio -> pass2 压缩
- 溢出控制：_pos_gscale（压空白）+ _pos_sscale（压行高）

### 4. 文字转义（esc）
- LaTeX 特殊字符转义（% & # _ ^ ~）
- 校注标记 [X]/〔X〕上标
- 符号修正（○->〇、【】->〔〕）
- CJK 标点处理（PunctStyle=kaiming）

### 5. 页码补全
- layout number block + 连续推断
- _lay_numbers[key]（前后页±1）

### 6. 书影/图片处理
- LAYJSON image block -> 裁源图贴回
- in_figure 跳过图内 OCR 行
- 图说明居中

## 各类型专属逻辑

### 古籍（`src/pipelines/build_classic.py`）
- **墨高重叠**：\\[-2pt]（行距=行盒-2，模拟 CJK 行间距<行盒高）
- **字号分类**：正文/注释/前言三类（序号位置识别）
- **注释序号分列**：_note_text_x + 序号统一 x0
- **aside 旁注**：竖排 shortstack + 目录补全
- **CJKglue**：base 0.15em（字距不挨字）
- **附录排版**：标题分开/小标题识别/案注小字/段间留白/缩进对齐（见 [appendix_layout.md](ancient/appendix_layout.md)）
- 详见：[ancient/01-08 分部 Spec](ancient/README.md)

### 现代书籍（`src/pipelines/build_geom.py`）
- **\linespread**：小字生效（pitch=fnt×1.2×linespread）
- **脚注**：① 分界线 + 小字
- **页眉共识**：OCR 拆分校正
- **标题层级**：行高 + toc_map + 居中
- **目录页**：dotfill + 页码右对齐

### 论文（待建）
- **公式**：inline_formula -> LaTeX math（或纯文本兜底）
- **表格**：tabular 结构还原
- **图表标题**：figure_title 居中
- **参考文献**：识别 + 格式化
- **摘要/关键词**：特殊区域

### 合同（待建）
- **条款编号**：第一条/第二条... 自动识别
- **签章区域**：image block + 绝对定位
- **固定格式**：表格 + 条款混排
- **页眉页脚**：合同编号/页码

### 标书（待建）
- **复杂表格**：多级表头 + 合并单元格
- **多层目录**：章节编号
- **附件区域**：图片 + 说明
- **格式规范**：标题字号/行距固定

## 测试体系

### 通用测试（verify_geom.py）
- pitch 误差（行距准确度）
- 页高误差（内容填充度）
- 占位偏差（底部空白）
- 溢出（多物理页）
- 缺失页

### 类型专属测试
- **古籍**：序号对齐（x0 统一）、墨高重叠（pitch=源）、aside 补全、校注上标
- **现代**：段首缩进、脚注分界、标题层级
- **论文**：公式渲染、表格结构
- **合同**：条款编号连续、签章位置
- **标书**：表格完整性、目录层级

### 测试数据
- wz1.pdf（古籍单规制，222页）
- wz2.pdf（古籍夹注本，783页）
- 优化前.pdf（现代简单）
- 优化前2.pdf（现代多级标题）
- 论文/合同/标书样本（待收集）

## 文件结构

代码已迁移到 `src/` 下，见 [规范化目录结构](#规范化目录结构)。

## 设计原则

1. **通用性**：共享基础（OCR + 几何 + 位置）通用，各类型专属逻辑隔离
2. **动态适配**：参数从数据动态计算（中位数/满行字数），不硬编码
3. **渐进式**：先古籍/现代（已实现），再论文/合同/标书（待建）
4. **Spec 先行**：新功能先写 Spec（目标/输入/输出/约束/测试点），确认后实现
5. **测试积累**：每功能配套测试用例，防回归
6. **版本控制**：重大改动前备份，git 提交

## 可扩展性

### 新增文档类型
1. 写分部 Spec（`spec/XX_type.md`）
2. 建 `build_XX.py`（从 build_classic.py 或 build_geom.py 复制，改专属逻辑）
3. 建 `fit_positional_XX.py`（两趟校准，调 build_XX.py）
4. 加路由（mode 参数 或 自动检测特征）
5. 加测试（verify_geom 扩展 + 类型专属断言）
6. 收集样本 PDF + OCR 数据

### 新增功能（已有类型内）
1. 写功能 Spec（`spec/XX_function.md`，含目标/输入/输出/约束/测试点）
2. 改 build_XX.py（保留原有逻辑，增量修改）
3. 加测试用例
4. verify_geom 确认无回归

### 新增 OCR 引擎
- 当前：PaddleOCR-VL-1.6（spotting + layout）
- 可扩展：其他 OCR（如 surya、DocLayout-YOLO）-> 适配数据格式（spotting lines/coords + layout JSON）
- 接口：run_spotting_ocr.py 输出标准化 JSON（lines/coords/labels）

## 技术栈

### OCR 层
| 组件 | 版本 | 用途 |
|---|---|---|
| PaddleOCR-VL-1.6 | API（aistudio） | spotting（行级 OCR）+ layout（版面分析） |
| PaddlePaddle | 3.0.0（Docker） | PP-DocLayoutV3 备选（未用，坐标同 PaddleOCR layout） |
| opencc | python-reimplemented | 繁简区分（注释/正文判别） |

### 渲染层
| 组件 | 版本 | 用途 |
|---|---|---|
| xelatex | TeX Live | PDF 渲染引擎 |
| xeCJK | - | CJK 字体/标点处理 |
| Noto Serif CJK JP | - | CJK 主字体 |
| Noto Sans CJK JP | - | heiti 标题字体 |
| eso-pic | - | shipout 叠加（aside/页码/图） |
| graphicx | - | 图片插入 |

### 数据处理
| 组件 | 版本 | 用途 |
|---|---|---|
| Python | 3.10 | 主语言 |
| PyMuPDF (fitz) | - | PDF 读取/渲染/裁图/测量 |
| Pillow (PIL) | - | 图片裁剪 |
| statistics | stdlib | 中位数/方差（几何标定） |
| re | stdlib | 正则（校注标记/序号/页码） |

### 测试
| 组件 | 用途 |
|---|---|
| verify_geom.py | 通用排版测试（pitch/占位/溢出/空白） |
| fitz get_text | 输出 PDF 行级 bbox 测量 |

### 环境
| 组件 | 版本 | 说明 |
|---|---|---|
| OS | Linux (WSL2) | Ubuntu 22.04 |
| GPU | RTX 5060 Ti 16GB | OCR/Docker |
| Docker | 29.2.1 | PP-DocLayoutV3 测试（glibc 兼容） |
| glm-5.2 | API | Claude Code 模型 |

## 规范化目录结构

### 目标结构
```
/opt/test/
├── src/                           # 源代码
│   ├── pipelines/                 # 排版管线
│   │   ├── build_classic.py       # 古籍管线
│   │   ├── build_geom.py          # 现代书籍管线
│   │   ├── build_paper.py         # 论文管线（待建）
│   │   ├── build_contract.py      # 合同管线（待建）
│   │   └── build_bid.py           # 标书管线（待建）
│   ├── calibration/               # 两趟校准
│   │   ├── fit_positional_classic.py
│   │   ├── fit_positional.py
│   │   └── fit_positional_XX.py   # 各类型校准
│   ├── ocr/                       # OCR 数据生成
│   │   └── run_spotting_ocr.py
│   ├── test/                      # 测试
│   │   └── verify_geom.py
│   └── utils/                     # 共享工具（待抽取）
│       ├── esc.py                 # 文字转义
│       ├── geometry.py            # 几何标定
│       └── page_pitch.py          # 行距测量
├── data/                          # 数据文件
│   ├── wz1/                       # wz1（古籍单规制）
│   │   ├── spotting_lines.json
│   │   ├── spotting_coords.json
│   │   └── layout.json
│   ├── wz2/                       # wz2（古籍夹注本）
│   │   ├── spotting_lines.json
│   │   ├── spotting_coords.json
│   │   └── layout.json
│   └── samples/                   # 论文/合同/标书样本（待收集）
├── spec/                          # Spec 文档
│   ├── 00_system_architecture.md  # 总 Spec
│   ├── README.md                  # 索引
│   ├── ancient/                   # 古籍分部（01-08_*.md）
│   ├── modern/                    # 现代分部（待写）
│   └── ...
├── output/                        # 输出 PDF
│   ├── 成果_wz1_rerun8_lay.pdf
│   └── 成果_wz2_classic_vXX.pdf
├── docs/                          # 项目文档
│   ├── PROJECT_SUMMARY.md
│   ├── CLAUDE.md
│   └── AGENTS.md
├── source_pdf/                    # 源 PDF
│   ├── wz1.pdf
│   ├── wz2.pdf
│   └── ...
└── README.md                      # 项目说明
```

### 迁移计划
1. 建 src/ data/ output/ docs/ source_pdf/ 目录
2. 移动 .py -> src/pipelines/ 或 src/calibration/
3. 移动 JSON -> data/wz1/ data/wz2/
4. 移动 PDF 成果 -> output/
5. 移动源 PDF -> source_pdf/
6. 移动文档 -> docs/
7. 更新代码内路径引用（fit_positional 调 build_XX）
8. 更新 spec/ 引用
9. git 提交

### 命名规范
- 管线：`build_<type>.py`（build_classic/build_geom/build_paper）
- 校准：`fit_positional_<type>.py`
- 数据：`<book>_spotting_lines.json` / `<book>_spotting_coords.json` / `<book>_layout.json`
- 输出：`成果_<book>_<version>.pdf`
- Spec：`<编号>_<功能>.md`（01_pitch_overlap / 10_modern / 20_paper）
