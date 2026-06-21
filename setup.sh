#!/bin/bash
set -e

echo "=== Installing system dependencies ==="
sudo apt update
sudo apt install -y \
    libgomp1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    fonts-noto-cjk \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    poppler-utils

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Setup complete ==="
