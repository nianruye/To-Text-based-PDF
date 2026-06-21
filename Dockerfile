FROM ubuntu:24.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# System dependencies + Python 3.10 from deadsnakes PPA
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    python3-pip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Use python3.10 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

WORKDIR /app

# Install app dependencies first, then override paddlepaddle with GPU wheel
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install GPU PaddlePaddle wheel (overrides CPU version from paddleocr dep)
COPY paddlepaddle_gpu-3.3.0.dev20251209-cp310-cp310-linux_x86_64.whl /tmp/
RUN pip3 install --no-cache-dir --no-deps --force-reinstall \
    /tmp/paddlepaddle_gpu-3.3.0.dev20251209-cp310-cp310-linux_x86_64.whl && \
    rm /tmp/paddlepaddle_gpu-3.3.0.dev20251209-cp310-cp310-linux_x86_64.whl

# Copy application code
COPY app/ ./app/
COPY run.py .

# Create directories
RUN mkdir -p uploads outputs

EXPOSE 8000

CMD ["python3", "run.py"]
