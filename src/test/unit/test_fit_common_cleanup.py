#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fit_common.main 临时目录清理（issue #7）。

fit_common.py 是脚本式模块（顶层解析 sys.argv），这里用 importlib 在 **打完 argv 补丁**
的隔离状态下加载（顶层只解析 argv + 定义函数，无文件/网络副作用），再 monkeypatch
render / measure_heights 做快速单元测试：

- 成功路径：两趟 render 共用同一临时目录，main 返回前已 rmtree；
- 异常路径：render 抛异常时临时目录也被删除（try/finally，issue #7 的残留泄漏）。

不调用 xelatex / 不读 OCR 数据。
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]          # src/test/unit -> 仓库根
FIT_COMMON = ROOT / 'src' / 'calibration' / 'fit_common.py'


def _load_fit_common():
    """在 argv 补丁下加载 fit_common（避免 pytest 自己的 argv 被当成 SL/CO/OUT）。"""
    old = sys.argv
    sys.argv = ['fit_common.py', 'SL', 'CO', 'OUT']
    try:
        spec = importlib.util.spec_from_file_location('fit_common_under_test', FIT_COMMON)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.argv = old
    return mod


@pytest.fixture(scope='module')
def fc():
    return _load_fit_common()


def _fake_render(seen):
    """模拟 render：pass1 写 est.json，pass2 写产物；记录两次用的临时目录。"""
    def render(out_pdf, est_log=None, ratio_table=None, fill=None, build_name='build_geom'):
        if est_log:                                    # pass1: 导出估高
            seen.append(os.path.dirname(est_log))
            with open(est_log, 'w', encoding='utf-8') as f:
                json.dump({'0': 100.0}, f)
        else:                                          # pass2: 带 ratio 表重渲
            assert ratio_table and os.path.exists(ratio_table)
            seen.append(os.path.dirname(ratio_table))
            with open(out_pdf, 'w', encoding='utf-8') as f:
                f.write('')
    return render


def test_tmp_cleanup_on_success(fc, monkeypatch, tmp_path):
    """成功返回后临时目录已被删除（两趟共用同一目录）。"""
    seen = []
    monkeypatch.setattr(fc, 'OUT', str(tmp_path / 'out.pdf'))   # 不让 pass2 写仓库根的 OUT
    monkeypatch.setattr(fc, 'render', _fake_render(seen))
    monkeypatch.setattr(fc, 'measure_heights', lambda pdf: {})
    fc.main('build_geom')
    assert len(seen) == 2 and seen[0] == seen[1], f'两趟未共用同一临时目录: {seen}'
    assert not os.path.exists(seen[0]), f'tempdir 泄漏: {seen[0]}'


def test_tmp_cleanup_on_exception(fc, monkeypatch, tmp_path):
    """render 抛异常时临时目录也被删除（try/finally 覆盖异常路径）。"""
    monkeypatch.setattr(fc, 'OUT', str(tmp_path / 'out.pdf'))
    created = {}

    def boom(out_pdf, est_log=None, **kw):
        created['dir'] = os.path.dirname(est_log)
        raise RuntimeError('render boom')

    monkeypatch.setattr(fc, 'render', boom)
    with pytest.raises(RuntimeError):
        fc.main('build_geom')
    assert created.get('dir'), '未拿到临时目录路径'
    assert not os.path.exists(created['dir']), f'异常路径 tempdir 泄漏: {created["dir"]}'
