#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""census_true_missing 基线回归（t61/battle12）。

新基线（t61，源页高口径）：md5 **9dda98e477057ef08289996ab68df4fe**，
stats `base 56105 / fax 919 / neighbor 246 / noise 350 / keep 1 / variant_cols 6883`，n=1。
旧口径（`--page-height 1443`，仅作对照）：md5 `afd42100a5193ed3c5b237978fd3e86d`。

本文件两条：
- 快速：若 `tmp_vert/battle6/true_missing.json` 存在，断言 md5/stats = 新基线（防止漂移）；
- 慢速（`B12_CENSUS_SLOW=1` 时）：实跑 `census_true_missing.py --book wz7`，断言 md5 = 新基线。
运行：
  /usr/bin/python3 -m pytest src/test/unit/test_census_baseline.py -q
  B12_CENSUS_SLOW=1 /usr/bin/python3 -m pytest src/test/unit/test_census_baseline.py -q
"""
import hashlib, json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
ARTIFACT = os.path.join(ROOT, 'tmp_vert/battle6/true_missing.json')
CENSUS = os.path.join(ROOT, 'src/tools/census_true_missing.py')
BASELINE_MD5 = '9dda98e477057ef08289996ab68df4fe'
BASELINE_STATS = {'base': 56105, 'fax': 919, 'neighbor': 246, 'noise': 350, 'keep': 1, 'variant_cols': 6883}


def _md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def test_artifact_baseline():
    """仓库内 true_missing.json（新基线）md5/stats 未被意外改动。"""
    if not os.path.exists(ARTIFACT):
        return
    assert _md5(ARTIFACT) == BASELINE_MD5
    j = json.load(open(ARTIFACT, encoding='utf-8'))
    assert j['stats'] == BASELINE_STATS and j['n'] == 1


def test_live_census_default_md5():
    """实跑默认（源页高）census，断言新基线 md5（慢；B12_CENSUS_SLOW=1 时启用）。"""
    if os.environ.get('B12_CENSUS_SLOW') != '1':
        return
    out = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'b12_census_baseline.json')
    r = subprocess.run([sys.executable, CENSUS, '--book', 'wz7', '--out', out],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout[-800:], r.stderr[-800:])
    assert _md5(out) == BASELINE_MD5
