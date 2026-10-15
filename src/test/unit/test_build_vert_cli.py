#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_vert.py 进程级行为测试（#18 退出码分级 / #20 临时目录按产物名分离）。

约束：
- 不依赖 upLaTeX / numpy / scipy / fitz / wz6 数据：用假 uplatex、dvipdfmx（shim）+
  合成的最小 OCR JSON。走 3 参数（无源 PDF）路径时 special / frame / right-ink / derot
  四项墨迹特性自动关闭，整条脚本可在无 LaTeX、无 pymupdf 的环境里跑完。
- 只锁「进程级行为」（退出码 / stderr 警告 / 默认临时目录名），不触碰渲染逻辑。
- 运行：/usr/bin/python3 -m pytest src/test/unit/test_build_vert_cli.py -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# src/test/unit/test_build_vert_cli.py -> parents[2] = src/
BUILD = Path(__file__).resolve().parents[2] / 'pipelines' / 'build_vert.py'

# 已知可容忍报错（build_vert.py 编译段 ERR_TOLERATED 的特征子串；正常全书编译恰有这一行）
TOLERATED_ERR = "! LaTeX Error: KANJI Encoding scheme `JT1' unknown."


def _tiny_inputs(d):
    """合成最小 OCR 输入（1 页 1 列），返回 (lines.json, coords.json)。"""
    lp = d / 'lines.json'
    cp = d / 'coords.json'
    lp.write_text(json.dumps({'1': ['測試列文']}, ensure_ascii=False), encoding='utf-8')
    cp.write_text(json.dumps({'1': [[[200, 100], [200, 900], [160, 900], [160, 100]]]},
                             ensure_ascii=False), encoding='utf-8')
    return lp, cp


def _make_shims(d, up_body, dv_body):
    """在 d/shim 下生成假 uplatex / dvipdfmx，返回带 shim 目录的 PATH。"""
    sh = d / 'shim'
    sh.mkdir(exist_ok=True)
    for name, body in (('uplatex', up_body), ('dvipdfmx', dv_body)):
        f = sh / name
        f.write_text('#!/bin/sh\n' + body, encoding='utf-8')
        f.chmod(0o755)
    return '%s:%s' % (sh, os.environ['PATH'])


def _run(args, cwd, env_extra=None):
    """跑 build_vert.py（用当前解释器，与 pytest 同一 python）。"""
    env = dict(os.environ)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(BUILD)] + [str(a) for a in args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


# 假编译器：uplatex 只写 DVI 不真编译；成功场景 rc=1 + 仅已知 JT1 报错（真实环境的实测行为）
_SHIM_UP_OK = ("printf '%%s\\n' \"%s\"\n: > vert.dvi\nexit 1\n" % TOLERATED_ERR.replace('`', '\\`'))
_SHIM_DV_OK = ': > vert.pdf\nexit 0\n'


@pytest.fixture
def workspace(tmp_path):
    """隔离工作区：合成输入 + 假编译器 + 按产物名派生的默认临时目录清理。"""
    lp, cp = _tiny_inputs(tmp_path)
    path = _make_shims(tmp_path, _SHIM_UP_OK, _SHIM_DV_OK)
    stem = 'unit_%s' % tmp_path.name          # 保证默认临时目录唯一（tmp_path 名唯一）
    yield {'dir': tmp_path, 'lines': lp, 'coords': cp, 'path': path,
           'out': tmp_path / ('%s.pdf' % stem), 'stem': stem,
           'default_tmp': Path('/tmp/vert_%s_run' % stem)}
    shutil.rmtree('/tmp/vert_%s_run' % stem, ignore_errors=True)


def test_three_args_warns_and_exit_0(workspace):
    """无源 PDF（3 参数）属调试用法：退出码 0，但 stderr 逐项警告 4 项墨迹特性被关。"""
    p = _run([workspace['lines'], workspace['coords'], workspace['out']],
             cwd=workspace['dir'], env_extra={'PATH': workspace['path']})
    assert p.returncode == 0, p.stderr
    assert '[完成]' in p.stdout
    assert workspace['out'].exists()
    for item in ('书眉/页码/边注渲染', '版框线: 外框双边', '版心右缘墨迹复测', '旋转坐标系页还原'):
        assert item in p.stderr, '缺少警告项: %s' % item


def test_missing_lines_input_exit_1(workspace):
    """lines/coords 输入缺失：显式报错 + 退出码 1（不落到 JSON 解析的 traceback）。"""
    p = _run([workspace['dir'] / 'nope.json', workspace['coords'], workspace['out']],
             cwd=workspace['dir'], env_extra={'PATH': workspace['path']})
    assert p.returncode == 1
    assert '[错误] lines 输入不存在' in p.stderr
    assert 'Traceback' not in p.stderr


def test_missing_src_pdf_exit_1(workspace):
    """源 PDF 缺失（argv[4] 给了但不存在）：显式报错 + 退出码 1。"""
    p = _run([workspace['lines'], workspace['coords'], workspace['out'],
              workspace['dir'] / 'nope.pdf'],
             cwd=workspace['dir'], env_extra={'PATH': workspace['path']})
    assert p.returncode == 1
    assert '[错误] 源 PDF 不存在' in p.stderr


def test_unexpected_compile_error_exit_1(workspace):
    """编译期出现「已知 JT1 之外」的报错行 -> 退出码 1，且不落 OUT（即使 vert.pdf 已生成）。"""
    up = "printf '%s\\n' \"! Undefined control sequence.\"\n: > vert.dvi\nexit 1\n"
    path = _make_shims(workspace['dir'], up, _SHIM_DV_OK)
    p = _run([workspace['lines'], workspace['coords'], workspace['out']],
             cwd=workspace['dir'], env_extra={'PATH': path, 'VERT_TMP': str(workspace['dir'] / 'tmp')})
    assert p.returncode == 1
    assert '[失败]' in p.stderr and '意外报错 1 行' in p.stderr
    assert not workspace['out'].exists()


def test_compile_failure_without_pdf_exit_1(workspace):
    """编译器失败且 vert.pdf 未生成 -> 退出码 1。"""
    up = "printf '%s\\n' \"! Emergency stop.\"\nexit 1\n"
    dv = "exit 1\n"
    path = _make_shims(workspace['dir'], up, dv)
    p = _run([workspace['lines'], workspace['coords'], workspace['out']],
             cwd=workspace['dir'], env_extra={'PATH': path, 'VERT_TMP': str(workspace['dir'] / 'tmp')})
    assert p.returncode == 1
    assert 'vert.pdf 未生成' in p.stderr
    assert not workspace['out'].exists()


def test_only_tolerated_jt1_error_exit_0(workspace):
    """只有已知 JT1 报错（真实全书编译的实测形态，uplatex rc=1）-> 仍判成功、退出码 0。"""
    p = _run([workspace['lines'], workspace['coords'], workspace['out']],
             cwd=workspace['dir'], env_extra={'PATH': workspace['path']})
    assert p.returncode == 0, p.stderr
    assert '[完成]' in p.stdout and workspace['out'].exists()


def test_default_tmp_dir_per_output_stem(workspace):
    """#20：默认临时目录按「输出文件名 stem」派生（/tmp/vert_<stem>_run），并发不同产物不共用。"""
    p = _run([workspace['lines'], workspace['coords'], workspace['out']],
             cwd=workspace['dir'], env_extra={'PATH': workspace['path']})
    m = re.search(r'\[tex\] (\S+) ', p.stdout)
    assert m, p.stdout
    assert Path(m.group(1)) == workspace['default_tmp'] / 'vert.tex'


def test_explicit_vert_tmp_overrides_default(workspace):
    """#20：显式 VERT_TMP 时用用户给的路径（覆盖默认值）。"""
    custom = workspace['dir'] / 'custom_tmp'
    p = _run([workspace['lines'], workspace['coords'], workspace['out']],
             cwd=workspace['dir'], env_extra={'PATH': workspace['path'], 'VERT_TMP': str(custom)})
    m = re.search(r'\[tex\] (\S+) ', p.stdout)
    assert m, p.stdout
    assert Path(m.group(1)) == custom / 'vert.tex'
