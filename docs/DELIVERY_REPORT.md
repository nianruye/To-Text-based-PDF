# PaddleOCR 逐字置信度 Docker 方案 — 交付报告

> 日期：2026-07-24  
> 目标：在 Docker 容器内获取 PaddleOCR 文字识别（rec）的逐字置信度（per-character score），非行级平均值

---

## 1. 成果

| 项目 | 值 |
|------|-----|
| 镜像名 | `paddleocr-rec:latest` |
| 镜像大小 | 3.08 GB |
| 基座 | ubuntu:22.04, Python 3.10.12 |
| PaddleOCR | 2.7.0.3 |
| Paddle | 3.0.0 (CPU) |
| 模式 | `use_gpu=False` |

**OCR 调用返回值由 2 元素变为 3 元素**：

```python
(text: str, line_score: float, char_scores: list[float])
```

---

## 2. 验证结果

测试图片：中文 "验证测试"（Noto Serif CJK SC 渲染）

```
验 → 1.0000
证 → 0.9994
测 → 0.9999
试 → 0.9998
```

- ✅ 无 SIGILL，CPU 推理稳定
- ✅ 返回值含 3 个元素
- ✅ `char_scores` 长度与 `text` 一致
- ✅ 所有 score 在 [0.0, 1.0] 区间

---

## 3. Patch 详情

### 3.1 `rec_postprocess.py`（10 处修改）

**路径**：`paddleocr/ppocr/postprocess/rec_postprocess.py`

```python
# 改前
result_list.append((text, np.mean(conf_list).tolist()))

# 改后
result_list.append((text, np.mean(conf_list).tolist(), conf_list.tolist()))
```

### 3.2 `predict_system.py`（1 处修改）

**路径**：`paddleocr/tools/infer/predict_system.py`

```python
# 改前
text, score = rec_result

# 改后
text, score, *_ = rec_result
```

> 必须同时改两个文件，否则上游解包会触发 `ValueError: too many values to unpack`。

---

## 4. 使用方式

### Python 调用

```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=False, lang='ch', use_gpu=False)
result = ocr.ocr('your_image.png', cls=False)

for line in result[0]:
    text, line_score, char_scores = line[1]
    for ch, sc in zip(text, char_scores):
        print(f"  {ch} → {sc:.4f}")
```

### Docker 运行

```bash
# 挂载图片目录到容器的 /data
docker run --rm -v /path/to/images:/data paddleocr-rec:latest python3 your_script.py
```

### 模型缓存

首次运行自动下载模型到 `~/.paddleocr/whl/`（容器内 `/root/.paddleocr/whl/`），约 100MB。如需持久化：

```bash
docker run --rm -v /path/to/images:/data -v ~/.paddleocr:/root/.paddleocr paddleocr-rec:latest ...
```

---

## 5. 镜像构建

### Dockerfile

```dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# apt 清华镜像
RUN sed -i 's/archive.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-opencv \
    libgl1 libglib2.0-0 libgomp1 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# pip 清华镜像
RUN pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip3 install --upgrade pip setuptools wheel

# Paddle 3.0.0
RUN pip3 install paddlepaddle==3.0.0

# PaddleOCR deps 先装，再 --no-deps 装 paddleocr（避开 PyMuPDF 构建失败）
RUN pip3 install --no-cache-dir \
    "numpy<2" "opencv-python-headless<4.10" \
    shapely pyclipper scikit-image imgaug lmdb visualdl tqdm \
    attrdict PyYAML matplotlib Pillow rapidfuzz \
    && pip3 install --no-cache-dir --no-deps paddleocr==2.7.0.3 \
    && pip3 install --no-cache-dir PyMuPDF || echo "PyMuPDF skipped"

# Patch
COPY patch_rec_postprocess.py /tmp/
RUN python3 /tmp/patch_rec_postprocess.py

WORKDIR /workspace
CMD ["python3"]
```

### 构建命令

```bash
cd /opt/paddleocr-docker
docker build -t paddleocr-rec:latest .
```

---

## 6. 已知问题 & 规避记录

| 问题 | 现象 | 根因 | 解决 |
|------|------|------|------|
| paddle 2.6.1 不存在 | `No matching distribution` | PyPI 无此版本 | 用 3.0.0 |
| paddle 2.6.2 SIGILL | `Illegal instruction` 崩溃 | binary 含 AVX-512 指令，WSL2 CPU 仅 AVX2 | 用 3.0.0 |
| Docker Hub 超时 | `dial tcp ... i/o timeout` | GFW 阻断 | apt/pip 配清华镜像 |
| PyMuPDF 构建失败 | pip install 报错 | 缺少系统依赖 | `--no-deps` 装 paddleocr，rec 不需要 PyMuPDF |
| 仅改 rec_postprocess.py 不够 | `ValueError: too many values to unpack` | predict_system.py 硬编码 2 元素解包 | 改为 `text, score, *_ = rec_result` |
| RTX 5060 Ti GPU 不可用 | segfault | Blackwell sm_120，paddle 不支持 | CPU 模式（use_gpu=False），对 rec 任务速度影响不大 |

---

## 7. 文件清单

```
C:\Users\xyp\paddleocr-docker\
├── Dockerfile                 # 镜像定义
├── patch_rec_postprocess.py   # 补丁脚本（构建时执行）
├── test_paddle3.py            # 测试脚本
└── DELIVERY_REPORT.md         # 本报告
```

WSL 副本：`/opt/paddleocr-docker/`
