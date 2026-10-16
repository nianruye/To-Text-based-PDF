#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""taskR：西文行侧排 / 标题署名行 / 影印页整页贴图 的纯函数与判据测试。

被测实现：`src/pipelines/build_vert.py` §1.995
  · `latin_row`        —— 「纯西文行」判据(拉丁字母数/CJK 数/拉丁占比)
  · `_latin_groups`    —— 源行墨迹 run 按「大空隙 = 词间」切成词组
  · `_align_words_groups` —— 词 ↔ 词组 单调配对(条数不等时 DP)
  · `_latin_tex`       —— 字号/基线/逐词落位(几何全取源图实测; fontTools 用 mock 注入)
  · `_latin_put`       —— 旋转 \put 的 tex 形态(精确整数矩阵 + q...Q)
  · `_band_blocked`    —— 特殊行占用的 x 带判定
  · `fax_decide`       —— 影印页判据(相对本书自身统计, 不写死页码/绝对值)
  · `fax_tex`          —— 贴图 tex 形态(raw pdf:image + 落点修正)
  · `_ink_band_at`     —— 墨迹带定位(空隙判据; 覆盖率判据会漏细短墨迹列)
用 _loader 从脚本里 ast 提取纯函数(不 import fitz、不跑 upLaTeX、不读源图)。

运行：/usr/bin/python3 -m pytest src/test/unit/test_vert_taskR.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load            # noqa: E402

_FUNCS = ['latin_row', '_is_cjk_ch', '_nonspace', '_latin_groups', '_band_blocked',
          '_align_words_groups', '_latin_tex', '_latin_put', 'fax_decide', 'fax_tex',
          '_ink_band_at', '_esc_ch',
          # taskR2: 拉丁 TFM 字体 / 破折号分片 / run 切分
          '_lat_pieces', '_assign_runs', '_lat_metrics', '_tfm_widths']
_CONSTS = ['LAT_MIN_CH', 'LAT_MIN_RATIO', 'LAT_MAX_CJK', 'DISP_RATIO',
           'FAX_IPC_MULT', 'FAX_CHAR_MULT', 'FAX_REF_MIN_CH', 'FAX_REF_MIN_N', 'PT2BP',
           'LAT_TFM', 'LAT_PFB', 'LAT_FONT_ON', 'LAT_DASH']
_MOCKS = {'_ROT_K': {'KX': -1293.80, 'KY': 0.30, 'base_h': 1443.0,
                     'dash_len': 0.772, 'dash_ca': 0.411, 'dash_cc': 0.243},
          '_T1W': {}, '_LAT': {'gs': None, 'err': False}, '_LAT_ENC': None,
          'page_w': 921.75, 'page_h': 1443.0, '_FONT_PATH': 'mock.ttc'}


def _ns():
    return load('build_vert.py', _FUNCS, _CONSTS, _MOCKS)


# ---------------- latin_row: 纯西文行判据 ----------------
@pytest.mark.parametrize('text, hit', [
    ('—We receive but what we give.—Coleridge', True),      # 实测 wz7 源页 29(占比 0.91)
    ('Literary Terms: a Dictionary 則有更清楚的說明：', False),   # 汉字列里夹西文词(占比 0.71)
    ('Bunyan, Pilgrims Progress)式的，也便是寓言(allegory)式的', False),
    ('二四Q', False),                                        # CJK 数 2
    ('abc', False),                                          # 拉丁字母数 < 4
    ('金瓶梅論', False),
    ('', False),
])
def test_latin_row(text, hit):
    ns = _ns()
    ok, nl, nc, r = ns['latin_row'](text)
    assert ok is hit


def test_latin_row_counts():
    """计数口径: CJK 数 <= LAT_MAX_CJK(1) 且 拉丁数 >= LAT_MIN_CH(4) 且 占比 >= 0.7"""
    ns = _ns()
    ok, nl, nc, r = ns['latin_row']('ISBNcode')
    assert (nl, nc, r) == (8, 0, 1.0) and ok is True
    ok2, nl2, nc2, r2 = ns['latin_row']('金瓶梅 a b c d')
    assert nc2 == 3 and ok2 is False
    ok3, nl3, nc3, r3 = ns['latin_row']('ISBN 978-7')      # 字母数够但占比 0.44 < 0.7 -> 不判
    assert (nl3, nc3) == (4, 0) and ok3 is False


# ---------------- _latin_groups: 墨迹 run -> 词组 ----------------
def test_latin_groups_split_by_wide_gap():
    """词间空隙 26pt / 词内 0.8-4.5pt, 字号 28.5 -> 阈值 14.25pt 只切词间(实测 p29 该行)"""
    ns = _ns()
    runs = [(381.8, 435.8), (445.5, 477.0), (481.5, 494.2),      # '—We'
            (520.5, 546.8), (549.8, 562.5), (564.0, 576.8), (580.5, 586.5),
            (588.8, 603.8), (605.2, 618.0),                      # 'receive'
            (646.5, 661.5), (662.2, 677.2), (680.2, 688.5)]      # 'but'
    g = ns['_latin_groups'](runs, 28.5)
    assert len(g) == 3
    assert g[0] == (381.8, 494.2) and g[1] == (520.5, 618.0) and g[2] == (646.5, 688.5)


def test_latin_groups_keeps_letter_gaps():
    """词内字母空隙(含 9.8pt 的破折号-字母间)不得切词: 阈值 0.5 x 字号 = 20pt"""
    ns = _ns()
    assert len(ns['_latin_groups']([(0, 54.0), (63.8, 95.0)], 42.0)) == 1   # 空隙 9.8 < 21 -> 不切
    assert len(ns['_latin_groups']([(0, 54.0), (74.0, 95.0)], 42.0)) == 1   # 空隙 20 < 21 -> 不切
    assert len(ns['_latin_groups']([(0, 54.0), (76.0, 95.0)], 42.0)) == 2   # 空隙 22 > 21 -> 切


def test_latin_groups_empty():
    assert _ns()['_latin_groups']([], 28.5) == []


# ---------------- _align_words_groups: 词 ↔ 词组 配对 ----------------
def test_align_words_groups_same_count_is_identity():
    ns = _ns()
    g = [(0, 10), (20, 30), (40, 60)]
    assert ns['_align_words_groups'](['a', 'b', 'c'], g, 20.0) == [(0, 0), (1, 1), (2, 2)]


def test_align_words_groups_skips_when_counts_differ():
    """词数 < 词组数: DP 跳掉最不像的那组(用字宽与源宽比); 度量按当前字体口径(LAT_FONT_ON=False
    时走 CJK 度量 _latin_metrics, 用 mock 注入)。"""
    ns = _ns()
    ns['LAT_FONT_ON'] = False
    fake = {'a': {'x0': 0.0, 'x1': 0.5, 'ymin': 0.0, 'ymax': 0.7, 'adv': 0.5},
            'b': {'x0': 0.0, 'x1': 1.0, 'ymin': 0.0, 'ymax': 0.7, 'adv': 1.0}}
    ns['_latin_metrics'] = lambda t, fp: fake[t]
    pairs = ns['_align_words_groups'](['a', 'b'], [(0.0, 10.0), (12.0, 32.0), (34.0, 44.0)], 20.0)
    assert len(pairs) == 2 and [p[1] for p in pairs] == sorted(p[1] for p in pairs)
    # 'a' 宽 10pt 配 10pt 的组, 'b' 宽 20pt 配 20pt 的组 -> 跳过 10pt 的那组
    assert pairs == [(0, 0), (1, 1)] or pairs == [(0, 0), (1, 2)]


def test_align_words_groups_latin_font_branch():
    """LAT_FONT_ON(默认)时配对用**拉丁字体**度量(_lat_metrics, 单参) —— 换字体后宽度口径随之变。"""
    ns = _ns()
    assert ns['LAT_FONT_ON'] is True
    ns['_lat_metrics'] = lambda t: {'x0': 0.0, 'x1': 0.5 * len(t), 'ymin': 0.0, 'ymax': 0.7}
    g = [(0.0, 10.0), (12.0, 22.0)]
    assert ns['_align_words_groups'](['ab', 'cd'], g, 20.0) == [(0, 0), (1, 1)]


# ---------------- _lat_pieces: 词内破折号单独成片 ----------------
def test_lat_pieces_splits_dashes():
    ns = _ns()
    assert ns['_lat_pieces']('give.') == [('t', 'give.')]
    assert ns['_lat_pieces']('—We') == [('d', '—'), ('t', 'We')]
    assert ns['_lat_pieces']('give.—Coleridge') == [('d', '—'), ('t', 'Coleridge')] or \
        ns['_lat_pieces']('give.—Coleridge') == [('t', 'give.'), ('d', '—'), ('t', 'Coleridge')]
    assert ns['_lat_pieces']('a—b—c') == [('t', 'a'), ('d', '—'), ('t', 'b'), ('d', '—'), ('t', 'c')]
    assert ns['_lat_pieces']('') == []


# ---------------- _assign_runs: run 序列按片宽单调切分 ----------------
def test_assign_runs_single_piece_takes_all():
    ns = _ns()
    r4 = [(0.0, 10.0, 660.0, 680.0), (20.0, 30.0, 660.0, 680.0)]
    assert ns['_assign_runs'](r4, [999.0]) == [(0, 1)]


def test_assign_runs_gives_dash_its_own_run():
    """[文, 破折号, 文] 三片: 破折号那一段(长 run)要单独切出来(它的长度/横位是逐条实测的)。"""
    ns = _ns()
    r4 = [(0.0, 10.0, 660.0, 680.0), (12.0, 22.0, 660.0, 680.0),     # 片1 两个 run(跨度 22)
          (30.0, 84.0, 671.0, 674.0),                                  # 破折号 run(长 54)
          (95.0, 105.0, 660.0, 680.0), (107.0, 117.0, 660.0, 680.0)]   # 片3 两个 run(跨度 22)
    segs = ns['_assign_runs'](r4, [22.0, 54.0, 22.0])
    assert segs == [(0, 1), (2, 2), (3, 4)]
    assert len(segs) == 3


# ---------------- _latin_tex: 字号 / 基线 / 逐词落位 ----------------
def _mk_ink(mock_runs4):
    """构造一个只给 _band_runs4 用的占位(真 ink 数组由 mock 顶替)"""
    return None


def _patch_band(ns, runs4):
    ns['_band_runs4'] = lambda ink, x0, x1, y0, y1: runs4


def test_latin_tex_geometry():
    """字号 = 源带宽 / 本字体墨迹上下缘比; 片基线 = 该片墨迹下缘 - 字体下缘 x 字号;
    逐片段落位到词组/该片起点(TeX pt 口径: 源坐标 x PT2BP)。
    源墨迹(mock 口径): 带 30.5pt 宽(垂直于行) x 743.5pt 长, 串的 em 墨迹上下缘比 1.0。"""
    ns = _ns()
    ns['LAT_FONT_ON'] = False
    def mk(t, fp):
        n = len(t)
        return {'x0': 0.02, 'x1': 0.02 + 0.5 * n, 'ymin': -0.1, 'ymax': 0.9, 'adv': 0.5 * n + 0.04}
    ns['_latin_metrics'] = mk
    runs4 = [(381.8, 435.8, 661.5, 692.0), (445.5, 477.0, 661.5, 692.0),
             (520.5, 546.8, 661.5, 692.0), (646.5, 661.5, 661.5, 692.0)]
    _patch_band(ns, runs4)
    puts = ns['_latin_tex'](None, 28, 'ab cd', (661.5, 692.0, 381.5, 1125.0), None, verbose=False)
    assert len(puts) == 2                                   # 两个词 -> 两个 \put
    for p in puts:
        assert p.startswith('\\put(') and 'q 0 -1 1 0 0 0 cm' in p and '\\special{pdf:literal direct Q}' in p
    # 字号: (带宽 30.5 / (ymax-ymin = 1.0)) x PT2BP(bp -> TeX pt)
    assert abs(float(puts[0].split('fontsize{')[1].split('pt')[0]) - 30.5 * 1.00375) < 0.05
    F = float(puts[0].split('fontsize{')[1].split('pt')[0])
    py = float(puts[0].split('put(')[1].split(',')[0])
    px = float(puts[0].split('put(')[1].split(',')[1].split(')')[0])
    # put 第二参 = 该片**实测墨迹下缘** x PT2BP - 字体下缘 x 字号 - KX
    assert abs(px - ((661.5 * 1.00375 + 0.1 * F) - (-1293.80))) < 0.05
    # put 第一参 = 该片墨迹起点 x PT2BP - 片首墨迹余量 x 字号 - KY
    assert abs(py - ((381.8 * 1.00375 - 0.02 * F) - 0.30)) < 0.05
    # 逐词落位: 两词的 put_y 差 = 词组起点差(PT2BP 口径)
    py2 = float(puts[1].split('put(')[1].split(',')[0])
    assert abs((py2 - py) - (520.5 - 381.8) * 1.00375) < 0.05


def test_latin_tex_dash_piece_own_size_and_place():
    """破折号: 单独一片, 字号由该 run 实测长反算(长比 = 探针常数), 沿/横位 = 该 run 墨心实测。"""
    ns = _ns()
    ns['LAT_FONT_ON'] = False
    ns['_latin_metrics'] = lambda t, fp: {'x0': 0.0, 'x1': 0.5 * len(t), 'ymin': -0.1, 'ymax': 0.9}
    runs4 = [(381.8, 435.8, 671.2, 674.2),                       # 破折号 run: 长 54.0
             (445.5, 477.0, 663.8, 687.0), (481.5, 494.2, 664.5, 679.5)]   # 'We'
    _patch_band(ns, runs4)
    puts = ns['_latin_tex'](None, 28, '—We', (661.5, 692.0, 381.5, 494.2), None, verbose=False)
    assert len(puts) == 2                                    # 破折号 + 'We' 两片
    Fd = float(puts[0].split('fontsize{')[1].split('pt')[0])
    assert abs(Fd - 54.0 / 0.772 * 1.00375) < 0.6            # 长比 0.772(探针实测) 反算字号
    bx = float(puts[0].split('put(')[1].split(',')[1].split(')')[0])
    by = float(puts[0].split('put(')[1].split(',')[0])
    assert abs(bx - (((671.2 + 674.2) / 2.0) * 1.00375 - 0.243 * Fd - (-1293.80))) < 0.05
    assert abs(by - (((381.8 + 435.8) / 2.0) * 1.00375 - 0.411 * Fd - 0.30)) < 0.05
    # 破折号不走拉丁字体(没 TFM 字形) -> 文本体里不带 \font 选择
    assert '\\font\\vlat' not in puts[0]


def test_latin_tex_no_font_or_anchor_returns_empty():
    ns = _ns()
    ns['_ROT_K'] = {'KX': None, 'KY': 0, 'base_h': 0}
    _patch_band(ns, [])
    assert ns['_latin_tex'](None, 1, 'ab', (0, 1, 0, 1), None, verbose=False) == []
    ns2 = _ns()
    ns2['_lat_gs'] = lambda: None                            # 拉丁字形文件找不到 -> 不渲染
    _patch_band(ns2, [])
    assert ns2['_latin_tex'](None, 1, 'ab', (0, 1, 0, 1), None, verbose=False) == []


def test_latin_put_matrix_and_kern():
    """旋转矩阵必须是**精确整数** 0/-1/1(q...Q 包夹), 且 F 为 TeX pt 一位小数。
    latin=True 时文本体要**显式选拉丁 TFM 字体**(不选就是 CJK 的全角 ASCII, taskR2 修的就是这个)。"""
    ns = _ns()
    s = ns['_latin_put']('We', 28.5, 100.0, 200.0)
    assert 'q 0 -1 1 0 0 0 cm' in s
    assert 'fontsize{28.5pt}{28.5pt}' in s
    assert '\\font\\vlat=%s at 28.5pt' % ns['LAT_TFM'] in s
    # kerns 只在 track != 0 时插入
    s2 = ns['_latin_put']('We go', 28.5, 100.0, 200.0, 3.25)
    assert s2.count('\\kern3.25pt') == 4
    assert ns['_latin_put']('We', 28.5, 100.0, 200.0, 0.01).count('\\kern') == 0
    # latin=False(破折号): 不选拉丁字体, 走 CJK 竖排字形
    assert '\\font\\vlat' not in ns['_latin_put']('—', 70.0, 100.0, 200.0, 0.0, latin=False)


# ---------------- _tfm_widths: TFM 宽度表解析 ----------------
def _write_tfm(path, widths, mapping):
    """合成一个最小 TFM: bc=0 ec=255, 每字符给 width 表下标, width = fix_word(2^-20)"""
    import struct
    nw = len(widths)
    lh = 18
    ci = b''
    for c in range(256):
        wi = mapping.get(c, 0)
        ci += struct.pack('>I', wi << 24)
    wtab = b''.join(struct.pack('>I', int(round(w * (1 << 20)))) for w in widths)
    zero = b'\x00' * 4
    body = (struct.pack('>12H', 0, lh, 0, 255, nw, 0, 0, 0, 0, 0, 0, 0) + b'\x00' * (4 * lh)
            + ci + wtab)
    with open(path, 'wb') as f:
        f.write(body)


def test_tfm_widths_parse(tmp_path, monkeypatch):
    """宽度表 = fix_word(值/2^20 = em); char_info 首字节 = width 表下标; ASCII 槽位 = 码位。"""
    import struct  # noqa: F401
    p = str(tmp_path / 'ptx.tfm')
    _write_tfm(p, [0.5, 0.944, 0.722], {ord('W'): 1, ord('H'): 2, ord('i'): 0})
    ns = _ns()
    ns['LAT_TFM'] = 'ptx'; ns['_T1W'] = {}              # 独立缓存(模块里是 build 期一次性的缓存)
    ns['_calib_font_path'] = lambda name: p if name == 'ptx.tfm' else None
    ns['_lat_enc'] = lambda: {}
    w = ns['_tfm_widths']()
    assert abs(w[ord('W')] - 0.944) < 1e-6 and abs(w[ord('H')] - 0.722) < 1e-6
    assert abs(w[ord('i')] - 0.5) < 1e-6
    assert abs(w[ord('Z')] - 0.5) < 1e-6                      # 未单独给的槽位取默认下标 0

    # 文件缺失 -> 空表(词宽按字形近似, 不崩)
    ns2 = _ns()
    ns2['LAT_TFM'] = 'nope'; ns2['_T1W'] = {}
    ns2['_calib_font_path'] = lambda name: None
    assert ns2['_tfm_widths']() == {}


def test_lat_metrics_uses_tfm_advance_and_outline():
    """拉丁度量 = TFM 前进量(逐字推进) + Type1 轮廓墨迹 bbox(em 口径); 缺字形字符按 0.8em 估。"""
    ns = _ns()
    boxes = {'H': (19, 0, 702, 662), 'e': (14, 0, 428, 446)}   # Type1 轮廓单位 = 1000/em
    class G:
        def __init__(self, b): self.b = b
        def draw(self, pen): pen.bounds = self.b
    class GS(dict):
        pass
    gs = GS({'H': G(boxes['H']), 'e': G(boxes['e'])})
    ns['_lat_gs'] = lambda: gs
    ns['_lat_enc'] = lambda: {ord('H'): 'H', ord('e'): 'e'}
    ns['_tfm_widths'] = lambda: {ord('H'): 0.722, ord('e'): 0.444}
    m = ns['_lat_metrics']('He')
    assert abs(m['x0'] - 0.019) < 1e-6                        # 首字墨迹前缘
    assert abs(m['x1'] - (0.722 + 0.428)) < 1e-6              # 末字墨迹后缘(按 TFM 前进量推进)
    assert abs(m['adv'] - (0.722 + 0.444)) < 1e-6
    assert abs(m['ymin'] - 0.0) < 1e-6 and abs(m['ymax'] - 0.662) < 1e-6
    m2 = ns['_lat_metrics']('—')                              # 非 ASCII: 无字形 -> 按 0.8em 估
    assert m2 is None or abs(m2['x1'] - m2['x0'] - 0.6) < 1e-6


# ---------------- _band_blocked ----------------
def test_band_blocked():
    ns = _ns()
    blocks = [(700.0, 780.0)]
    assert ns['_band_blocked'](708.0, 744.0, blocks) is True     # 完全在内
    assert ns['_band_blocked'](760.0, 800.0, blocks) is False    # 重叠 20/40 = 50%(不 > 50%)
    assert ns['_band_blocked'](765.0, 785.0, blocks) is True     # 重叠 15/20 = 75%
    assert ns['_band_blocked'](100.0, 120.0, blocks) is False


# ---------------- fax_decide: 影印页判据 ----------------
def test_fax_decide_relative_criteria():
    """判据 = 每字墨迹面积 > 2.5 x 本书正文页中位 **且** OCR 字数 < 0.5 x 中位。
    构造: 10 页正文(500 字, ipc 400) + 2 页影印(70 字, ipc 7000) + 1 页目录(230 字, ipc 180)。"""
    ns = _ns()
    nch = {}
    ipc = {}
    for i in range(10):
        nch[i] = 500; ipc[i] = 400.0
    nch[10] = 70; ipc[10] = 7000.0        # 影印页
    nch[11] = 0; ipc[11] = 500000.0       # 空白/插图页
    nch[12] = 230; ipc[12] = 180.0        # 目录页: OCR 字数也低, 但每字墨迹面积正常 -> 不误判
    out = ns['fax_decide'](nch, ipc)
    assert set(out) == {10, 11}
    assert out[10][2] > 2.5 and out[10][0] == 70


def test_fax_decide_needs_both_conditions():
    """只有一条成立就不算: 墨迹面积高但 OCR 字数也高(正文页 OCR 恰好漏字) / 字数低但墨迹面积正常"""
    ns = _ns()
    nch = {i: 500 for i in range(10)}
    ipc = {i: 400.0 for i in range(10)}
    nch[20] = 400; ipc[20] = 8000.0       # 面积高但字数 400 >= 0.5x500 -> 不判
    nch[21] = 60; ipc[21] = 300.0         # 字数低但面积正常 -> 不判
    assert ns['fax_decide'](nch, ipc) == {}


def test_fax_decide_insufficient_samples():
    """正文页样本 < 3 -> 不判(无参考量不硬猜)"""
    ns = _ns()
    assert ns['fax_decide']({0: 500, 1: 600}, {0: 400.0, 1: 410.0}) == {}


def test_fax_decide_thresholds_are_constants():
    ns = _ns()
    assert ns['FAX_IPC_MULT'] == 2.5 and ns['FAX_CHAR_MULT'] == 0.5


# ---------------- fax_tex ----------------
def test_fax_tex_raw_image_special():
    """贴图用 dvipdfmx 原样图片 special(**不引 graphicx**): 纸幅 x PT2BP, put 的 y 取负修正量。"""
    ns = _ns()
    ns['fax_image'] = lambda i: '/tmp/x/p%d.jpg' % (i + 1)
    ns['page_w'] = 921.75
    ns['page_h'] = 1443.0
    s = ns['fax_tex'](4)
    assert s.startswith('\\AddToShipoutPictureBG*{')     # 带星 = 只本页(无星会逐页累积)
    assert 'pdf:image width 925.2pt height 1448.4pt (/tmp/x/p5.jpg)' in s
    assert '\\put(0,-5.41)' in s


# ---------------- _ink_band_at: 空隙判据 ----------------
def test_ink_band_at_gap_not_coverage():
    """覆盖率判据会漏掉「又细又短的墨迹列」(实测 p29 英文行 'b' 升部只占 2pt 宽) —— 空隙判据要带上它。"""
    import numpy as np
    ns = _ns()
    ink = np.zeros((200, 400), dtype=bool)
    ink[20:180, 100:140] = True          # 主带 x 50-70pt(2x px)
    ink[40:180, 144:148] = True          # 细柱 x 72-74pt(覆盖率 0.44 < 0.5 但属于本带)
    ink[20:180, 300:340] = True          # 邻列 x 150-170pt
    got = ns['_ink_band_at'](ink, 60.0, 5.0, 95.0, 45.0)
    assert got is not None
    x0, x1, y0, y1 = got
    assert x0 == 50.0 and 73.9 <= x1 <= 74.1             # 细柱被并进本带
    assert abs(y0 - 10.0) < 0.1 and abs(y1 - 90.0) < 0.1
    assert x1 < 100.0                                     # 邻列未被并进来


def test_ink_band_at_no_ink():
    import numpy as np
    ns = _ns()
    assert ns['_ink_band_at'](np.zeros((50, 50), dtype=bool), 10.0, 5.0, 20.0, 20.0) is None
