#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""punct_eval.py — spec/governance/PUNCT_EVAL.md §7 的 CLI 入口。

实现体在 punct_bench（同一实现，避免两套）：本文件只做入口转发。
用法：punct_eval.py --gold ... --pdf ... --coords ... --lines ... --out-json ... --out-csv ...
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from punct_bench import main
if __name__ == '__main__':
    sys.exit(main())
