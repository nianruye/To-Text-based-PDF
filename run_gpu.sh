#!/bin/bash
# Launch the OCR server with GPU PaddlePaddle using conda Python + glibc 2.39
export LD_LIBRARY_PATH="/opt/miniconda3/lib:/usr/lib/x86_64-linux-gnu:/usr/lib/wsl/lib:${LD_LIBRARY_PATH}"
exec /opt/glibc239/usr/lib64/ld-linux-x86-64.so.2 \
  --library-path /opt/glibc239/usr/lib/x86_64-linux-gnu:/opt/miniconda3/lib:/usr/lib/x86_64-linux-gnu:/usr/lib/wsl/lib \
  /opt/miniconda3/bin/python3.10 /opt/test/run.py
