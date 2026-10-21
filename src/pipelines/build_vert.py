#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_vert.py — 竖排繁体书还原 v1 (流式竖排)
用法: /usr/bin/python3 src/pipelines/build_vert.py <lines.json> <coords.json> <out.pdf> [src.pdf]
env:  VERT_PAGES=3-12    只输出指定页(1-based, 如 '3-12' 或 '3,5')
      VERT_SPECIAL=0       关闭书眉/页码渲染(默认开, 需 src.pdf 测墨迹)
      VERT_TMP=/dir        临时目录(默认 /tmp/vert_<输出文件名 stem>_run: 按产物名分离, 并发不共用)
      VERT_LAT=0           关闭西文(纯拉丁)行侧排渲染; VERT_LATFONT/VERT_LATFONT_PFB=TeX 拉丁字体名/
                           对应 Type1 字形文件(默认 ptmr8t / utmr8a.pfb); VERT_LAT_FONT=0 回到
                           CJK 全角 ASCII 老口径(对照用); VERT_DISP_RATIO=1.4 标题/署名字高倍率判据
      VERT_FAX=0           关闭影印页整页贴图; VERT_FAX_IPC_MULT/VERT_FAX_CHAR_MULT 判据倍率
退出码: 0 = 正常(含 SRC 缺省的 3 参数调试调用); 1 = 输入文件缺失 / 编译失败(#18)
管线: OCR(2x=144dpi px) -> 参数拟合(tarticle 竖排) -> uplatex+dvipdfmx -> PDF
v2: 书眉/页码/边注 —— eso-pic \AddToShipoutPictureFG*(仅本页, 无星号会逐页累积) \put 绝对定位(逐字手工断列),
    坐标取源书墨迹实测(OCR bbox 对边缘小字偏 18-40pt 不可直接用); 边注按实测字列与 OCR 行右到左配对
"""
import json, sys, os, subprocess, statistics, re

SL = sys.argv[1]; CO = sys.argv[2]; OUT = sys.argv[3]
SRC = sys.argv[4] if len(sys.argv) > 4 else None
PAGES_ENV = os.environ.get('VERT_PAGES', '')

# ---------- 0) 临时目录 / 输入校验(#20 / #18) ----------
# 临时目录按「输出文件名 stem」分离(#20): 并行跑不同书/不同产物名时不再共用 vert.tex/dvi/pdf
#   (对标横排 #10 的路径分 build_name 方案)。显式设 VERT_TMP 时用用户给的路径(空串等同未设,
#   同 VERT_NCOL 的 `or` 惯例)。同名产物并发仍会共用目录 -> 属预期(同横排方案: 冲突只在同名时)。
TMP = os.environ.get('VERT_TMP') or '/tmp/vert_%s_run' % os.path.splitext(os.path.basename(OUT))[0]
for _p, _kind in ((SL, 'lines'), (CO, 'coords')):
    if not os.path.exists(_p):
        print('[错误] %s 输入不存在: %s' % (_kind, _p), file=sys.stderr); sys.exit(1)
if SRC is not None and not os.path.exists(SRC):
    print('[错误] 源 PDF 不存在: %s' % SRC, file=sys.stderr); sys.exit(1)
if SRC is None:
    # 3 参数调试调用(无源 PDF)保持兼容: 只显式警告, 退出码仍 0(#18)
    print('[警告] 未给源 PDF(argv[4] 缺省): 以下 4 项依赖源图墨迹的特性将静默关闭 ——\n'
          '        1) 书眉/页码/边注渲染(VERT_SPECIAL)\n'
          '        2) 版框线: 外框双边 + 界行线(VERT_FRAME)\n'
          '        3) 版心右缘墨迹复测(VERT_RIGHT_INK, 回退 OCR 拟合值)\n'
          '        4) 旋转坐标系页还原(VERT_DEROT)', file=sys.stderr)
os.makedirs(TMP, exist_ok=True)

sl = json.load(open(SL)); co = json.load(open(CO))
keys = sorted(sl.keys(), key=int)

# ---------- 0.5) 纸型基准(纸型无关化 taskN) ----------
# 背景(taskN): §1/§1.8/§1.9/§1.95/§1.98 里有一批判据是**在 wz6 纸型上实测的绝对量** —— 2x px
#   (1100px = 550pt)或 pt 区间 —— 只对 595.3x1245.3pt 的开本成立, 换书(开本/字号/列数不同)必失准。
#   本轮把这批量改成「相对页幅/内框」:
#     ① 页幅基准 PW_PX/PH_PX: 优先源 PDF 页幅 x2(精确); 无源 PDF 时退化为 OCR 盒并集高分位
#        (内容不到纸缘 -> 偏小, 日志明示; 该模式下 §1.8/§1.9 本就不渲染, 相对判据只用于正文筛选)。
#     ② 门限 = **wz6 原值 ÷ wz6 页幅** 的比例 x 本页幅(等价换算: wz6 上反算回原值, 偏差 0);
#        每个比例可用 VERT_* env 覆盖(别的书要人工微调时用)。换算基准见下方 _WZ6_*。
#     ③ 有实测内框的书: §1.96a 再用「内框缘」取并集(书眉/页码 = 框外 **或** 页边带内),
#        无版框书(wz7 类)自动退化为纯页幅比例 —— 版框检测不出时不误检、不崩溃。
PT_PER_PX = 2.0                     # OCR 坐标 = 2x px(144dpi); pt = px/2 (§0 管线注)
_WZ6_PW, _WZ6_PH = 1190.6, 2490.6   # wz6 页幅(2x px) = 所有「原绝对值」的换算基准
# 页面尺寸: 从 src.pdf 精确取(pt)
page_w = 595.3; page_h = 1244.1
src_doc = None
if SRC:
    import fitz
    d = fitz.open(SRC)
    page_w = round(d[0].rect.width, 1); page_h = round(d[0].rect.height, 1)
    src_doc = d

def _page_px_fallback():
    """无源 PDF 时的页幅估计: OCR 盒并集的高分位(内容不贴纸缘 -> 偏小; 只用于比例换算)"""
    xs = sorted(q[0] for k in keys for p in co.get(k, []) or [] for q in p)
    ys = sorted(q[1] for k in keys for p in co.get(k, []) or [] for q in p)
    if not xs or not ys: return _WZ6_PW, _WZ6_PH
    return xs[int(0.995 * (len(xs) - 1))], ys[int(0.995 * (len(ys) - 1))]

if src_doc is not None:
    PW_PX, PH_PX = round(page_w * PT_PER_PX, 1), round(page_h * PT_PER_PX, 1)
    _pw_src = '源PDF'
else:
    PW_PX, PH_PX = _page_px_fallback()
    _pw_src = 'OCR盒p99.5(无源PDF, 偏小)'
PW_PX, PH_PX = float(PW_PX), float(PH_PX)

def _frac(env_name, wz6_px, base_px):
    """wz6 绝对 px -> 比例(除以 wz6 页幅基准); env 显式给比例则优先。"""
    v = os.environ.get(env_name)
    return float(v) if v else wz6_px / base_px

def _sc(frac, axis='w'):
    """比例 -> 本页幅上的 px 门限。3 位取整: 「比例 x 页幅」的浮点残差(~1e-13)不得把门限推过
    整数 px 边界(否则 x0=1100 这类边界行的分类会翻转) —— wz6 上反算值与原值逐位相同。"""
    cur = PW_PX if axis == 'w' else PH_PX
    return round(frac * cur, 3)

_WZ6_PW_PT, _WZ6_PH_PT = 595.3, 1245.3   # wz6 页幅(pt) = pt 类绝对量(版框几何区间)的换算基准
def _envfrac(name, frac):
    """env 给**比例**(相对页宽/页高)时优先, 否则用 wz6 换算出来的比例"""
    v = os.environ.get(name)
    return float(v) if v else frac
def _sc_pt(frac, axis='w'):
    """比例 -> 本页幅上的 pt 门限(3 位取整, 同 _sc)"""
    cur = page_w if axis == 'w' else page_h
    return round(frac * cur, 3)
def _fp(v_wz6_pt, axis='w'):
    """wz6 绝对 pt -> 本页同名量(pt), 按页幅比例"""
    return v_wz6_pt / (_WZ6_PW_PT if axis == 'w' else _WZ6_PH_PT)

def _band_union(band_r_px, band_l_px, in_l_pt, in_r_pt):
    """页边带并上「实测内框缘」(pt 入参, px 出参)。判据 = 「在版心框外 **或** 在页幅边带内」,
    故门限取更靠内的那一侧: 右带起点 = min(页幅带, 内框右缘), 左带终点 = max(页幅带, 内框左缘)。
    wz6 实测: 内框右缘 567.8pt(=1135.6px) > 页幅带 1100px、左缘 45.5pt(=91.0px) < 100px
      -> 两翼都不生效(分类与原绝对量逐条相同)。"""
    return (round(min(band_r_px, in_r_pt * 2.0), 3), round(max(band_l_px, in_l_pt * 2.0), 3))

# 页边带 / 长行 / 左边注小字 门限(wz6 原值 -> 页幅比例; env 可覆盖比例)
EDGE_R_FRAC = _frac('VERT_BAND_R_FRAC', 1100.0, _WZ6_PW)     # 右页边带起点 = 页宽 x 该比例
EDGE_L_FRAC = _frac('VERT_BAND_L_FRAC', 100.0, _WZ6_PW)      # 左页边带终点 = 页宽 x 该比例
LONG_H_FRAC = _frac('VERT_LONG_H_FRAC', 300.0, _WZ6_PH)      # 「长行(正文列)」下限 = 页高 x 该比例
SMALL_FS_FRAC = _frac('VERT_SMALL_FS_FRAC', 55.0, _WZ6_PH)   # 左边注小字步进上限 = 页高 x 该比例
BAND_R_PX = _sc(EDGE_R_FRAC, 'w')
BAND_L_PX = _sc(EDGE_L_FRAC, 'w')
LONG_H_PX = _sc(LONG_H_FRAC, 'h')
SMALL_FS_PX = _sc(SMALL_FS_FRAC, 'h')
print('[纸型基准] 页幅 %.1f x %.1f px(2x)=%.1f x %.1f pt [%s]; 页边带 x0>%.1f / x1<%.1f; '
      '长行 h>=%.1f; 左边注小字步进<%.1f (px, 相对化: 原 wz6 %.0f/%.0f/%.0f/%.0f)' % (
          PW_PX, PH_PX, PW_PX / 2.0, PH_PX / 2.0, _pw_src, BAND_R_PX, BAND_L_PX,
          LONG_H_PX, SMALL_FS_PX, 1100.0, 100.0, 300.0, 55.0))

# ---------- 1.0) 挤格标点(任务A: 竖排标点挤格不占格) ----------
# 源书实测(逐字墨迹反推, 探针 tmp_vert/ascii_ink.py + col_gaps.py, wz6 p10):
#   句号/逗号挤在**前一字格的右下区**, 下一字仍在「前字格顶 + 1 格」-> 标点不占格。
#   实测: 标点墨心 = 前字格顶 + 0.85 格(, 0.84/? 1.15), x = 格左缘 + 0.81×格距(格距 43.4pt);
#   p10 列「黨之間…差不」27 字(含 2 标点) = 25 格, 步进 62px(2x)=31pt = 字号(34.4pt 的墨高 30.3pt) ——
#   旧实现按字数排格 -> 28 字列步进压到 28.5pt < 字墨高 30.3pt = 字粘连(用户反馈①)。
# 做法: 排版格数 = 字数 - 挤格标点数; 标点用单独字号(PUNCT_SIZE)绝对定位到前字格右下区。
PUNCT_HANG = set('。，、；：？！︒︑')     # 挤格标点(引号/括号「」（）不挤格: 源书占整格)
# OCR 半角/全角归一化噪声(实测: key47「的努力,更加造成」等 = 中文逗号被读成半角), 渲染前归一化回中文标点;
# 仅当前一字是 CJK 时替换(保护 key230 元数据页的 URL/JSON 里的真半角符号)
PUNCT_ASCII = {',': '，', '.': '。', ':': '：', ';': '；', '!': '！', '?': '？'}
# 标点字形墨心相对 \put 锚点的偏移(em; 探针 tmp_vert/probe_punct_tex2.py 实测, F=34.4pt, Noto Serif CJK)
PUNCT_INK = {'。': (0.481, -0.366), '，': (0.463, -0.390), '、': (0.452, -0.356),
             '；': (0.476, -0.275), '：': (0.480, -0.332), '？': (0.472, -0.362), '！': (0.480, -0.363)}
# ↓ taskM: 下面 3 项原为 wz6 源图实测后硬编码 -> 现由 §1.956 标定趟自动标定;
#   这里的数值 = **兜底/对账基准**(标定不可用时用, 也是书中「现值」列), 显式 env 优先于标定值。
PUNCT_SIZE = float(os.environ.get('VERT_PUNCT_SIZE') or 0.62)   # 标点字号/正文字号(标定: 源书挤格标点墨高÷正文字高)
PUNCT_DX = float(os.environ.get('VERT_PUNCT_DX') or 0.81)       # 标点墨心 x = 格左缘 + PUNCT_DX×格距(标定见 §1.956)
PUNCT_DY = float(os.environ.get('VERT_PUNCT_DY') or 0.85)       # 标点墨心 y = 前字格顶 + PUNCT_DY×步进(标定见 §1.956)

# ---------- 1.0a0) 标点是否独占一格(taskS: 按本书标定) ----------
# 上面 §1.0 的「挤格标点不占格」是**wz6 的排印习惯**(标点挤在前一字格右下角, 下一字仍在
#   「前字格顶 + 1 格」); 换书后这条未必成立 —— 实测 wz7(样本 idx54 = 源页 354)逐 run 反推:
#     列 x763.5-786「沒來由暴叫如雷，…」30 字 4 标点: 字步进 25.75pt(前 6 个无标点字
#     的 run 顶差中位), 逐字格号 = 字序(沒=0,來=1,…,雷=6,，=7,你=8,…,妻=28,！=29) ——
#     残差 <= 0.26 格; 若按挤格(顿号处不占格)则每个标点之后整段错位 1 格(实测残差 0.94-1.03 格)。
#     即**该书的标点独占整格**, 只是字形小、墨迹画在格内(实测墨顶 = 本格顶 + 0.26-0.37 步进)。
#   口径: PUNCT_CELL = 标点占的格数(0 = 挤格/前字格内, 1 = 独占一格), 由 §1.956 标定趟按
#     源书墨迹实测(见 _calib_punct_cell); 兜底 0 = 既有行为(wz6 逐字节不变)。
#   影响面: n_cells(排版格数) / char_cells(逐字格号) / fit_gaps(空隙 DP 的格号预测) /
#     col_puts(标点是否推进格号) 四处 —— 都是「格」的口径, 必须同源。
PUNCT_CELL = float(os.environ.get('VERT_PUNCT_CELL') or 0.0)
CALIB_DEF_PUNCT_CELL = 0.0      # 兜底 = wz6 口径(挤格)
PUNCT_CELL_THR = 0.5            # 标定判据: 估计值 >= 该值 -> 判「占格」(格号是整数, 只能二选一)

def _punct_own():
    """标点是否独占一格(PUNCT_CELL >= 0.5)。§1.956 标定后才为 True(之前恒 False -> 既有行为)"""
    return PUNCT_CELL >= PUNCT_CELL_THR

def _norm_punct(t):
    """OCR 半角标点归一化: 前一字是 CJK 时把 , . : ; ! ? 换成中文标点(1:1 替换, 不改字数)"""
    out = list(t)
    for i, c in enumerate(out):
        if c in PUNCT_ASCII and i > 0 and (0x3400 <= ord(out[i - 1]) <= 0x9FFF
                                           or 0x3000 <= ord(out[i - 1]) <= 0x303F
                                           or 0xFF00 <= ord(out[i - 1]) <= 0xFFEF):
            out[i] = PUNCT_ASCII[c]
    return ''.join(out)

def n_cells(t):
    """排版格数 = 字数 - (1 - PUNCT_CELL) x 挤格标点数。
    PUNCT_CELL = 0(wz6 口径): 标点挤在前字格内, 不占格 —— 与旧实现逐位相同;
    PUNCT_CELL = 1(占格书, 实测 wz7): 标点独占整格 -> 排版格数 = 字数。"""
    np_ = sum(1 for c in t if c in PUNCT_HANG)
    return max(1, len(t) - int(round((1.0 - PUNCT_CELL) * np_)))

def _step_chars(t):
    """步进分类用的「格数」口径(taskCK): **连续拉丁字母串按 1 格计**, 其余字符各 1 格。
    为什么: 竖排里一个西文词是侧排的一片, 沿列方向只占约一格; 但 OCR 文本逐字母计数,
    (y 跨度 / 字数) 会把词多的列步进低估 —— 实测 p35 的 'narrative art）)下,可以分辨的有寓言,
    包括exemplum allegory,moral fable' 57 字 / 2009px -> 17.6pt, 而该列真步进 ~25.7pt,
    于是被 page_rows/note_rows 的「小字注」步进判据误判成边注(渲染到一条 7pt 宽的碎墨列上,
    与同 x 的正文列叠字)。标点/数字仍各计 1 格(wz7 标点占格, PUNCT_CELL=1 同口径)。"""
    n, i, L = 0, 0, len(t)
    while i < L:
        c = t[i]
        if ('a' <= c <= 'z') or ('A' <= c <= 'Z'):
            i += 1
            while i < L and (('a' <= t[i] <= 'z') or ('A' <= t[i] <= 'Z')):
                i += 1
            n += 1
        else:
            i += 1; n += 1
    return max(1, n)

def char_cells(t):
    """逐字格号 [(cell, hanging)]。
    hanging=True 表示「本字墨迹不对齐本格顶」(标点): 标定/拟合的**预测锚点**是**前一字格顶**
      (PUNCT_DY / GAP_HANG 的标定语义, 见 §1.956), 故标点占格时调用方要用 (cell - PUNCT_CELL)。
    挤格(PUNCT_CELL=0): 标点与前一字同格, 格号不推进 —— 与旧实现逐位相同。"""
    own = _punct_own()
    out = []
    k = 0
    for i, c in enumerate(t):
        if c in PUNCT_HANG and i > 0:
            if own:                      # 占格: 标点自占一格
                out.append((k, True))
                k += 1
            else:                        # 挤格: 与前一字同格
                out.append((max(0, k - 1), True))
        else:
            out.append((k, False))
            k += 1
    return out

# ---------- 1.0a) 字模横向压缩(taskJ-A) ----------
# 背景(用户实测反馈①「看着密密麻麻」): 重建页的墨迹覆盖率比源书高 17-25%。
# 实测(探针 tmp_vert/taskJ/measure_char2.py, wz6 p10/p14/p100, 4x 灰度同阈值 150, 逐字墨迹):
#   源书   墨高 29.75pt / 墨宽 20.0pt (宽高比 0.67 —— 长体/窄体宋, 竖排老铅字常态)
#   本项目 Noto Serif CJK TC 墨高 29.25pt / 墨宽 29.25pt (宽高比 1.0, 全角方体)
#   -> 单字墨迹面积 我/源 = 1.13-1.19(页级), 其中 字宽因子 x1.48 / 墨高因子 x0.98 / 填充率 x0.79。
# 修法: 横向压缩字形(保字高) —— 实测墨迹面积随 K 等比缩放(墨宽 = 27.5xK 精确)。
#   K 由三页实测标定: K=0.87 时修后单字墨迹面积与源书差 -4.1%..+0.9%(两种阈值口径都在 ±5% 内)。
#   墨高不变(源书 29.75 vs 我 29.25, 已是 -1.7%), 步进/列距/列位全不动(框驱动基准不受影响)。
#
# ⚠ 实现方式(taskJ2 修泄漏): **不用 \\scalebox**(graphicx), 改用手写 PDF 算子 q/<K> 0 0 1 0 0 cm ... Q。
#   根因(探针 tmp_vert/taskJ2/probe_stream.py / probe_big.py, 实数复现):
#     graphicx(dvipdfmx.def) 把 \\scalebox 编译成 \\special{pdf:btrans}+\\special{x:scale K 1}+\\special{pdf:etrans},
#     dvipdfmx 把它展开为「平移到锚点 · 缩放 · 平移回」并在 etrans 时用**数值逆矩阵**还原 ——
#     逆矩阵只印到 6 位有效数字: 1/0.87 = 1.149425... 印成 1.14943, 于是每字残留
#       0.87 x 1.14943 = 1.0000041 (x 方向, 绕该字锚点)
#     留在 CTM 里。全书累积: N 字后后续内容被 x1.0000041^N 缩放。实测 N=2000 字时页尾规则线
#     从 put 0..574pt(= 页 0..571.86bp)漂到 -2.34..574.29bp —— 左端越出页缘, 正是 p157
#     verify_vert「矢量图形越界 4 个 draw bbox=[-0.8,284.7,572.6,284.7]」的来源(该书 231 页仅 p157
#     越界, 因为它的界行线实测左端 = 0.0pt 且字数最多, 别的页 hx_l 有余量)。
#   为什么 q...Q 不泄漏: PDF 图形状态栈的 Q 是**精确还原**(非数值逆), 累积残差为 0 ——
#     同探针 N=2000: 规则线恒为 0.00..571.86bp, 与不压缩(plain)逐字节相同。
#     用 \\special{pdf:literal direct ...}(dvipdfmx 原样插入算子, 不附加 q/cm/Q, 见 dvipdfmx-special.pdf),
#     它与 xfakebold 的用法同源。
#   锚点语义: dvipdfmx 的 DVI 原点(1in = 72bp)在页面坐标的 x=72 —— q/K 0 0 1 0 0 cm 是相对**该点**缩放,
#     故写入坐标须反解: 目标页坐标 X -> put 值 = (X - 72)/K + 72(探针 probe_literal.py 实测:
#     X=52.697 应写 49.813, 与 span 左缘实测 52.69 一致; K=1 时该式退化为 X)。
#   调用方语义不变(与 \\scalebox 等价): 传进来的 x_pt = 缩放后字盒**左缘**的目标页坐标,
#     墨心 = put + K x (未压缩时的墨心偏移) -> 字心目标 xc 用 x_pt = xc - K x F/2(否则整列左移 (1-K)xF/2)。
PAGE_ORIGIN_BP = 72.0    # dvipdfmx DVI 原点(1in)在页面坐标的 x(bp); 横向缩放绕此点
XSCALE = float(os.environ.get('VERT_XSCALE') or 0.87)   # 字模横向压缩系数(1.0 = 不压缩)

# ---------- 1.0a2) 墨迹加粗(taskL-e: 换楷体后的墨量补偿) ----------
# 背景(任务L 实测): 换楷体后单页墨迹覆盖率明显低于源书 —— 源书 p10 列带覆盖 0.3145,
#   现用 Noto 0.2543, simkai 0.1907 / AR PL 楷 0.2014 / simfang 0.1864(口径见报告 §2)。
# 做法: PDF 文本渲染模式「填充+描边」(2 Tr + w) —— 描边沿字形轮廓外扩 w/2, 笔画变粗,
#   **不做任何缩放**, 故不存在 taskJ-A 的 btrans/etrans 逆矩阵舍入问题;
#   q/<w> w/2 Tr ... Q 与 §1.0a 的 K 压缩同走图形状态栈(精确还原, 累积残差 0)。
# 实测(探针 tmp_vert/taskL/probe/probe_bold2.py, 每段单独一页):
#   w=0.2/0.35/0.5/0.8 时墨量增益 +14%/+23%/+34%/+53%(simkai), 墨迹外接框仅扩 1-2px(笔画原地变粗);
#   加粗段之后的**下一段与基线逐像素相同** -> 证明 Q 精确还原、无状态泄漏。
BOLD_W = float(os.environ.get('VERT_BOLD') or 0)   # 描边线宽(pt); 0 = 关闭(默认, 输出逐字节不变)

def _vb(s):
    """墨迹加粗包装(taskL-e)。BOLD_W=0 时原样返回 -> 既有行为不变。"""
    if not BOLD_W:
        return s
    return (r'\special{pdf:literal direct q %s w 2 Tr}%s\special{pdf:literal direct Q}'
            % (BOLD_W, s))

# ---------- 1.0a3) \put 夹取的「实测文本框」比例(taskP2-①) ----------
# 背景(p104 越界 5.93pt): 夹取原按「em 盒」留边(0.94F) —— 但 PDF 文本层里一个字的 span bbox 并
#   不是 em 盒。探针(tmp_vert/taskP2/probe_box*.py: 用**本管线同款 preamble**真编译 + PyMuPDF 逐
#   span 量 bbox, 6-40pt x {14 个竖排形态 + 标点 + 汉字}):
#     · 盒高恒 = 2.858 x (0.9587F) = 2.740F, 与码位无关(所有样本逐字号完全一致);
#     · 盒相对 \put 锚点 = [锚点 + C + 1.734F (顶), 锚点 + C - 1.006F (底)], C ≈ 4.9pt(Tex 锚点常数,
#       与字号无关 —— 实测 6-40pt 全同一常数; 见 probe_box2.py 的 u/d/sum 表);
#     · 上/下分担 = 字体 ascender/descender(Noto Serif CJK 1.809/1.049) x 0.9587(TeX pt -> 该字体的
#       文本层字号换算, PyMuPDF 报的 size = 0.9587 x 字号)。
#   故夹取改用这套**实测比例**(不再是 em 盒): 盒顶越页 -> 压 put; 盒底越页 -> 抬 put。
#   竖排形态码位(﹁﹂︵︶…)与汉字/标点比例相同(探针实测), 故按「一款字体一张表」即可, 无需逐码位。
#   只作用于 NF 页(_pv_clamp_on); wz6/有版框书不走这里(逐位不变)。
TXTBOX_C = float(os.environ.get('VERT_TXTBOX_C') or 4.9)       # 锚点常数项(pt)
TXTBOX_UP = float(os.environ.get('VERT_TXTBOX_UP') or 1.74)    # 盒顶 = put + C + UP x F
TXTBOX_DN = float(os.environ.get('VERT_TXTBOX_DN') or 1.01)    # 盒底 = put + C - DN x F

def _txtbox_clamp_y(y_pt, F, page_hi):
    """\put 的 y(自页底)按**实测文本框**夹回页内 -> 新 y。见上方 §1.0a3。"""
    return min(max(y_pt, 0.5 - TXTBOX_C + TXTBOX_DN * F), page_hi - 0.5 - TXTBOX_C - TXTBOX_UP * F)

def _put_tex(ch, x_pt, y_pt, F, xs=None, clamp=False):
    """单字 \\put 片段(pt, 页左上原点 y 向下)。xs = 横向压缩(默认 XSCALE)。
    xs<1 时用自带 q/<K> 0 0 1 0 0 cm ... Q 包住该字(只缩 x 保字高, 状态精确还原不污染后续内容,
    见上方 §1.0a 根因说明); 传入的 x_pt 是缩放后字盒左缘的目标页坐标, 内部按 PAGE_ORIGIN_BP 反解。
    括号走 §1.0c 的竖排形态替换(字号/位置一并校正), 其余字不受影响。"""
    xs = XSCALE if xs is None else xs
    ch, F, x_pt, y_pt = _br_put(ch, x_pt, y_pt, F, xs)
    if clamp:
        # 夹回页内(只无框伪槽格页传 True, 见 _pv_clamp_on 注释): 必须在 _br_put **之后** ——
        #   括号走竖排形态时会再改字号/坐标, 夹在之前等于没夹(实测 ﹁﹂ 仍越界 3-6pt)。
        #   y 用**实测文本框**比例(§1.0a3): 原 em 盒留边 0.94F 不够 —— 实测 span bbox 向上可达
        #   1.734F + 4.9pt(p104 那 1 条 ﹁ 越界 5.93pt 即此)。
        y_pt = _txtbox_clamp_y(y_pt, F, page_h)
        x_pt = min(max(x_pt, 0.5), page_w - F - 0.5)
    body = _vb(r'\fontsize{%spt}{%spt}\selectfont %s' % (round(F, 1), round(F, 1), _esc_ch(ch)))
    if abs(xs - 1.0) > 1e-6:
        ks = ('%.4f' % xs).rstrip('0').rstrip('.')
        x_pt = (x_pt - PAGE_ORIGIN_BP) / float(ks) + PAGE_ORIGIN_BP   # 反解: 变换绕页 x=72bp
        body = (r'\special{pdf:literal direct q %s 0 0 1 0 0 cm}%s'
                r'\special{pdf:literal direct Q}') % (ks, body)
    return r'\put(%.1f,%.1f){%s}' % (x_pt * PT2BP, y_pt * PT2BP, body)

# ---------- 1.0b) 列内空隙(源书空一格)对齐(taskJ-B) ----------
# 背景(用户实测反馈②): 源书问答体「問：」「答：」后空一格, OCR 不保留 -> 我们的列里没有这一格,
#   整列后续字被摊开(步进按格子数均分, 少算一格 -> 步进偏大)。空隙只能从**源图墨迹**反推。
# 判据(任务书): 列内相邻字墨迹间距 > 1.3x 中位步进 (单格空隙 = 2x 中位步进)。
# 难点: 相邻字相碰会并成一个 run(顶差也 = 2m), 挤格标点的墨又落在「下一格」的位置(顶差被拆成
#   1.15m + 0.68m) —— 单看顶差两者都会骗过判据。故用**结构对齐**(DP)而不是单点阈值:
#   把 OCR 字符(带「格号 + 是否挤格」)单调对齐到槽内 run 序列, 字符的**预测墨顶** =
#   T0 + (格号 + 累计空格 + 0.85×挤格?) x 步进; 允许「跳过字符」(粘连)/「跳过 run」(标点碎点)/
#   「插一格」(代价 p_gap), 末尾再用「总格数 vs 槽实测墨迹跨度」收口 —— 插格只有在确实解释了
#   墨迹位置偏差时才划算。实测(p14 問：行/答：行, wz6): 插格位置 = 問：之后 1 格, 与源图一致。
GAP_ON = os.environ.get('VERT_GAP', '1') not in ('0', 'false', 'False')
GAP_HANG = float(os.environ.get('VERT_GAP_HANG') or 0.85)   # 挤格标点墨顶 = 本字格顶 + GAP_HANG×步进
# (与 PUNCT_DY 同源, 同一次源图统计: PUNCT_DY 取墨心、GAP_HANG 取墨顶; taskM 起由 §1.956 标定)
P_MERGE = 0.15       # DP 代价: 字符并进上一个 run(相邻字相碰粘连, 预测墨顶落在该 run 内)
P_PUNCT = 0.30       # DP 代价: 挤格标点不匹配 run(墨小且挤在格缝上)
P_SKIPN = 1.20       # DP 代价: 普通字无墨(OCR 多字) —— 必须比「1 格错配」(≈1.0) 贵,
                     #   否则 DP 会用「跳一个字 + 中间插一格」凑出一致的墨迹(实测 p15 問：列:
                     #   空隙被错插到第 11 字处), 那种解与源书排版不符。
P_SKIPR = 0.40       # DP 代价: run 无字符(标点碎点/粘连长 run 的尾部)
P_GAP = 0.55         # DP 代价: 插一格空隙
P_TOT = 1.00         # DP 代价: 末字格号与槽实测墨迹跨度的差(每格)
GAP_MAX = 4          # 单列最多插几格(防异常放大)
_gap_log = []        # 空隙检出记录(全书跑完落盘, VERT_GAP_REPORT)

# —— 插格(空格)必须有源图墨迹依据(taskV) ——
# 旧行为: 'g' 转移代价恒为 p_g, 只按「槽跨度格数 vs 文本格数」的总量约束 -> 只要总格数对得上,
#   空格插在哪都行, DP 会挑代价最小处 -> 实测 wz7 大量 2-3 倍步进的伪空格(p73 x118 CV0.326
#   异常步进 67pt=2.01 倍; p76 x126 99pt=3.0 倍)。
# 新判据: 插格位置的**预测 y** 若落在源图该槽某条墨迹 run 内 -> 那里有墨, 不该插 -> 重罚。
#   VERT_GAP_INK=1 启用(默认 0 = 与旧行为逐位相同, 供 A/B)。
GAP_INK = os.environ.get('VERT_GAP_INK', '0') not in ('0', 'false', 'False', '')
P_GAP_INK = float(os.environ.get('VERT_GAP_INK_PEN') or 50.0)   # 惩罚量级(远大于 p_g≈1)


def fit_gaps(runs, t, m, T0, B, h_ink=None, hratio=None, p_merge=P_MERGE, p_punct=P_PUNCT,
             p_skipn=P_SKIPN, p_r=P_SKIPR, p_g=P_GAP, p_t=P_TOT, _align=None, ink_probe=None):
    """槽内墨迹 run + 文本 -> [(字符下标, 插入格数)]（taskJ-B 纯函数, DP）。
    _align(taskU-A 只读旁路): 传 dict 时填**逐字 -> run 下标**的对齐结果('m' 转移), 不传则
      与旧实现逐位相同(只是把「bg==0 早退」挪到回溯之后 —— 该分支本就无副作用)。
    runs: [(墨顶, 墨底)] pt(页顶向下); m: 步进 pt; T0/B: 槽实测墨迹顶/底 pt(用于预测与收口)。
    DP 状态 (字符下标 i, run 下标 j, 已插格数 g); 转移:
      m  字符 <- run 匹配    代价 = (|预测墨顶 - 实测墨顶| / m)^2
      e  字符并进上一 run    预测墨顶落在上一 run 的 [顶, 底] 内(相邻字相碰) —— 便宜
      n  普通字无墨         贵(见 P_SKIPN 注释)
      p  挤格标点           便宜(墨小/挤格缝, 且不参与匹配)
      r  跳过 run / g 插一格
    收口: (i=len(t), j=len(runs), g) 最优 + |槽跨度格数 - (文本格数+g)| x p_t。
    hratio: 挤格标点墨顶相对本字格顶的偏移(× 步进); 缺省用模块级 GAP_HANG —— 注意必须在此
      处解析(不能写成默认参数): GAP_HANG 由 §1.956 标定趟在函数定义之后才赋值。"""
    if hratio is None:
        hratio = GAP_HANG
    L = len(t); n = len(runs)
    if not GAP_ON or L < 2 or n < 3 or m <= 1.0:
        return []
    tops = [r[0] for r in runs]
    bots = [r[1] for r in runs]
    cell = char_cells(t)
    own = _punct_own()
    ncell = max(c for c, _h in cell) + 1 if cell else 1

    def pred(i, g):
        """本字墨顶预测。标点的锚点是**前一字格顶**(PUNCT_DY/GAP_HANG 的标定语义):
        占格时标点自占一格 -> 锚点格号 = cell - 1; 挤格时标点与前字同格 -> 锚点格号 = cell。"""
        c, hang = cell[i]
        return T0 + (c - (PUNCT_CELL if hang else 0.0) + g + (hratio if hang else 0.0)) * m

    def _matchable(i):
        """本字能否参与「匹配 run」。挤格标点不参与(它的墨又小又挤在格缝上, 源书实测冒号墨心在
        本字格顶 + 1.2-1.4 步进, 与 PUNCT_DY=0.85 的渲染位置并不一致, 拿它做匹配依据会把整列
        对齐带偏 —— 实测 p14 答：列: 空隙被错插到第 17 字处)。
        占格书(实测 wz7)相反: 标点独享一格、墨迹画在**本格内**(实测墨顶 = 本格顶 + 0.26-0.37 步进),
        预测位置稳 -> 参与匹配反而给出对齐证据(该列 30 字里 4 个标点就是 4 个锚点)。"""
        return (not cell[i][1]) or own

    INF = float('inf')
    dp = [[[INF] * (GAP_MAX + 1) for _ in range(n + 1)] for _ in range(L + 1)]
    bt = [[[None] * (GAP_MAX + 1) for _ in range(n + 1)] for _ in range(L + 1)]
    dp[0][0][0] = 0.0
    for i in range(L + 1):
        for j in range(n + 1):
            for g in range(GAP_MAX + 1):
                cur = dp[i][j][g]
                if cur == INF:
                    continue
                if i < L and j < n and _matchable(i):
                    c = cur + (abs(pred(i, g) - tops[j]) / m) ** 2
                    if c < dp[i + 1][j + 1][g]:
                        dp[i + 1][j + 1][g] = c; bt[i + 1][j + 1][g] = (i, j, g, 'm')
                if i < L and j >= 1 and cell[i][1]:
                    c = cur + p_punct
                    if c < dp[i + 1][j][g]:
                        dp[i + 1][j][g] = c; bt[i + 1][j][g] = (i, j, g, 'p')
                if i < L and j >= 1 and _matchable(i) and bots[j - 1] >= pred(i, g):
                    c = cur + p_merge                      # 预测墨顶落在上一 run 内 = 与它粘连
                    if c < dp[i + 1][j][g]:
                        dp[i + 1][j][g] = c; bt[i + 1][j][g] = (i, j, g, 'e')
                if i < L and _matchable(i) and cur + p_skipn < dp[i + 1][j][g]:
                    dp[i + 1][j][g] = cur + p_skipn; bt[i + 1][j][g] = (i, j, g, 'n')
                if j < n and cur + p_r < dp[i][j + 1][g]:
                    dp[i][j + 1][g] = cur + p_r; bt[i][j + 1][g] = (i, j, g, 'r')
                if i < L and g < GAP_MAX:
                    _gc = p_g
                    if ink_probe is not None:
                        # 该插格位置的预测墨顶处若源图有墨 -> 不许在此插空格
                        try:
                            if ink_probe(pred(i, g + 1)):
                                _gc += P_GAP_INK
                        except Exception:
                            pass
                    if cur + _gc < dp[i][j][g + 1]:
                        dp[i][j][g + 1] = cur + _gc; bt[i][j][g + 1] = (i, j, g, 'g')
    # 槽实测墨迹跨度对应的**格数**: 末字墨底 = 首字墨顶 + (N-1) x m + 墨高 -> N = (B-T0-墨高)/m + 1
    #   (漏减墨高会系统性多算 ~0.95 格 -> 每列都误判有一处空隙; 实测 p14: exp 22.89 vs 真值 22)
    if h_ink is None:
        h_ink = statistics.median([b - a for a, b in runs]) if runs else 0.95 * m
    exp = (B - T0 - h_ink) / m + 1.0
    best, bg = INF, 0
    for g in range(GAP_MAX + 1):
        c = dp[L][n][g]
        if c == INF:
            continue
        c += p_t * abs(exp - (ncell + g))
        if c < best:
            best, bg = c, g
    if best == INF:
        return []
    # 回溯: 'g' 转移 = 在该字符之前插一格; 'm' 转移 = 字符 <- run(taskU-A 的 _align 旁路)
    out = {}
    i, j, g = L, n, bg
    while (i or j or g):
        p = bt[i][j][g]
        if p is None:
            break
        pi_, pj_, pg_, act = p
        if act == 'g':
            out[pi_] = out.get(pi_, 0) + 1
        elif act == 'm' and _align is not None:
            _align[pi_] = pj_
        i, j, g = pi_, pj_, pg_
    if bg == 0:
        # 无空隙: 与旧实现同(原地早退, 无副作用)。诊断表挪到早退之前(taskU-A: 该分支也要能看对齐)
        if os.environ.get('VERT_GAP_DEBUG'):
            print('    [DP] T0=%.1f B=%.1f m=%.2f n=%d L=%d ncell=%d exp=%.2f g=%d cost=%.2f'
                  % (T0, B, m, n, L, ncell, exp, bg, best))
            for i2, (c2, h2) in enumerate(cell):
                print('        %2d %s cell%-2d hang%d  pred=%.1f  run=%.1f  al=%s' % (
                    i2, t[i2], c2, h2, T0 + (c2 + (hratio if h2 else 0)) * m,
                    tops[i2] if i2 < n else -1, (i2 in (_align or {})) and _align[i2] or '-'))
        return []
    # 空隙位置修正: 插入点若落在挤格标点之前, 后移到该标点之后 —— 源书标点紧跟上字(墨在上格右下角),
    #   空隙在标点之后(实测 p14 問: 源书冒号墨迹 y380-387 贴着問的字脚, 空格在其后)。
    #   DP 对「标点前/标点后」两种插法代价完全相同(挤格标点不参与匹配), 不修正会随机落成前者。
    fix = {}
    for ci, e in out.items():
        jj = ci
        while jj < L and t[jj] in PUNCT_HANG:
            jj += 1
        if jj >= L:
            continue        # 落点越到列尾(末字全是挤格标点) = 末尾空格, 无视觉含义 -> 丢弃
        fix[jj] = fix.get(jj, 0) + e
    # 逐格校验(任务书判据的等价形式): 该空格格内不得有墨 —— 源书那格确实空着才算空隙。
    #   两类「多出一格」要分开: ①排版空格(格内无墨, 该补); ②OCR 漏字(格内有墨, 补空格只是掩盖
    #   丢字, 且会把后续字挤下) -> 只保留 ①。校验格号 = 字符名义格号 + 之前已插格数。
    out = {}
    cum = 0
    for ci in sorted(fix):
        e_ok = 0
        for k in range(fix[ci]):
            y0 = T0 + (cell[min(ci, L - 1)][0] + cum + k) * m
            if any(y0 + 0.2 * m < tp < y0 + 0.8 * m for tp in tops):
                break
            e_ok += 1
        if e_ok:
            out[ci] = e_ok
        cum += fix[ci]
    if os.environ.get('VERT_GAP_DEBUG') and len(out) != len(fix):
        print('    [DP] 校验剔除 %d 处(格内有墨)' % (len(fix) - len(out)))
    if os.environ.get('VERT_GAP_DEBUG'):
        print('    [DP] T0=%.1f B=%.1f m=%.2f n=%d L=%d ncell=%d exp=%.2f g=%d cost=%.2f' % (
            T0, B, m, n, L, ncell, exp, bg, best))
        for i2, (c2, h2) in enumerate(cell):
            tg = tops[i2] if i2 < n else None
            print('        %2d %s cell%-2d hang%d  pred(0)=%.1f pred(g)=%.1f  run=%.1f  gaps=%s' % (
                i2, t[i2], c2, h2, T0 + (c2 + (hratio if h2 else 0)) * m,
                T0 + (c2 + bg + (hratio if h2 else 0)) * m, tg if tg is not None else -1, out))
    return sorted(out.items())

# ---------- 1.0c) 标点竖排形态(taskK-A: 括号还原) ----------
# 用户反馈①: 源书 p3「（一九三八年五月）」的括号是**旋转 90 度的竖排专用形态**且比旁边字小;
#   我们此前渲染的是未旋转的全角（）(字号=正文, 墨迹 0.936em 高)。
# 实测(探针 tmp_vert/taskK/{shape_census,probe_vertcp}.py; 报告 docs/vert_punct_font_report.md):
#   ① 30 页抽样 176 个「小墨迹块」做**保宽高比**模板匹配: （ -> U+FE35 命中 25 例(IoU 中位 0.596,
#      次优候选 0.11)、） -> U+FE36 命中 27 例(0.574); 「」命中直角形 ﹁/﹂(p7 放大对照确认)。
#      源书 ︵ 墨迹 17.5 x 7.0pt, 同列汉字墨高约 28pt(括号墨高仅 0.23 倍字高)。
#      注: 早先按 OCR 行盒 x 直配墨迹列会错位(OCR 盒 x 与墨迹列差 20-40pt, 有等比缩放),
#      故探针改用 RANSAC 仿射配列 + 连通域 + 保宽高比 IoU(colmap.py / inkcols.py / glyph.py)。
#   ② 尺寸: Noto Serif CJK TC 的 ︵ 墨迹 = 0.936 x 0.286 em, 取 0.66F 时墨迹 18.2 x 6.4pt
#      (源书 17.5 x 7.0 -> 宽 +4% / 高 -9%, 是「宽高同时最接近」的单一缩放); 【】〔〕 源书更小,
#      分类型给 0.55 / 0.49(见 BR_SIZE)。
#   ③ 码位可用性: Noto Serif CJK TC 提供 U+FE17/18/35/36/39/3A/3D/3E/3F/40/41/42/43/44 全套
#      (fontTools cmap 实测), 且用本管线真 preamble 编译实测能正常出字并被 PDF 文本层提取。
#   ④ 不用 \scalebox 旋转: 直接用竖排**码位**(字形本身就是旋转形态), 故无 taskJ2 的
#      btrans/etrans 逆矩阵舍入泄漏问题(压缩仍走 §1.0a 的 q/K 0 0 1 0 0 cm ... Q)。
VERT_FORMS = {'（': '︵', '）': '︶', '「': '﹁', '」': '﹂', '『': '﹃', '』': '﹄',
              '【': '︗', '】': '︘', '〔': '︹', '〕': '︺', '《': '︽', '》': '︾',
              '〈': '︿', '〉': '﹀'}
# 各竖排码位在 em 盒内的墨迹 (墨宽, 墨高, 墨心 x, 墨心 y) —— 下面的数值 = NotoSerifCJK-Regular.ttc
# 第 4 面(TC)实测, 同时是**兜底值**(字体解析失败时用); taskM 起由 §1.956 用 fontTools 从
# VERT_FONT 指向的字体文件自动重算(口径: CFF/TrueType 轮廓 bbox ÷ upem, 与下表同源)。
# 要点: 开口形墨心在盒**下半**(cy≈0.04-0.14) / 闭口形在上半(cy≈0.62-0.72), 直角形 ﹁/﹂ 墨心
# 不在盒中心(cx≈0.62/0.38) —— 不按墨心校正就直接摆到格心的话, 开口形会整格低 ~15pt(实测)。
VERT_METRICS = {
    '︵': (0.936, 0.286, 0.500, 0.087), '︶': (0.936, 0.287, 0.500, 0.673),
    '﹁': (0.713, 0.306, 0.619, 0.070), '﹂': (0.713, 0.306, 0.382, 0.686),
    '﹃': (0.658, 0.348, 0.634, 0.091), '﹄': (0.658, 0.348, 0.366, 0.669),
    '︗': (0.926, 0.351, 0.500, 0.092), '︘': (0.926, 0.351, 0.500, 0.675),
    '︹': (0.936, 0.250, 0.500, 0.042), '︺': (0.936, 0.250, 0.500, 0.718),
    '︽': (0.932, 0.439, 0.500, 0.138), '︾': (0.932, 0.439, 0.500, 0.623),
    '︿': (0.940, 0.431, 0.500, 0.133), '﹀': (0.940, 0.431, 0.500, 0.627),
}
def _parse_br_map(s):
    """'︗:0.55,︘:0.55' -> {'︗':0.55,'︘':0.55}(VERT_BR_SIZE_MAP; 空/非法项跳过)。"""
    out = {}
    for part in (s or '').split(','):
        if ':' not in part:
            continue
        g, v = part.split(':', 1)
        try:
            out[g.strip()] = float(v)
        except ValueError:
            continue
    return out

BR_ON = os.environ.get('VERT_BR', '1') not in ('0', 'false', 'False')
BR_SIZE_DEF = float(os.environ.get('VERT_BR_SIZE') or 0.66)   # 竖排括号字号/正文字号(标定 §1.956; 0.66 = wz6 兜底值)
BR_SIZE = {'︗': 0.55, '︘': 0.55, '︹': 0.49, '︺': 0.49}        # 兜底值 = wz6 实测(【】〔〕 明显更小); 标定覆盖
BR_SIZE.update(_parse_br_map(os.environ.get('VERT_BR_SIZE_MAP')))   # 显式 env 覆盖(每类括号可单独给)

def _br_put(ch, x_pt, y_pt, F, xs=None):
    """括号 -> 竖排形态(§1.0c)。返回 (渲染字, 渲染字号, x_pt', y_pt')。
    非括号(或 VERT_BR=0)原样返回 —— 既有行为不变。
    x_pt = 缩放后字盒左缘的页坐标(pt, 左起); y_pt = \\put 的 y(自页底起 = page_h - 墨基线)。
    校正口径: 正文字号 F 的格心 = 盒左缘 + xs x F/2、基线上方 0.5F; 竖排字形按自身墨心
    (VERT_METRICS 的 cx/cy x 渲染字号)摆回该格心。"""
    if not BR_ON or ch not in VERT_FORMS:
        return ch, F, x_pt, y_pt
    xs = XSCALE if xs is None else xs
    g = VERT_FORMS[ch]
    F2 = round(F * BR_SIZE.get(g, BR_SIZE_DEF), 1)
    _w, _h, cx, cy = VERT_METRICS[g]
    x2 = x_pt + xs * (F / 2.0 - cx * F2)
    y2 = y_pt + 0.5 * F - cy * F2
    return g, F2, x2, y2

# ---------- 1.0d) OCR 列拆分归位(taskK-B: 行首闭括号回上一列) ----------
# 现象(实测, 全书 9 例): OCR 偶发把一列行尾的闭括号挂到**下一列的行首** ——
#   p3「（一九三八年五月 | ）問題的提起」/ p43「「先生之志則大矣 | 」先生的看法」/ p161「（一九三八年十月 | ）同志們」
#   / p193/p201 同型(日期行) —— 这正是用户看到的「同一页两处括号字号不一致(22.4 vs 29.8)」的**根因**:
#   括号对分属两列, 两列字号本就不同(源书日期行是小字: 墨高 22.0pt vs 正文 29.5pt, 我们渲染
#   25.0 vs 33.5 与源书一致), 分开看就像同页括号大小不一。
# 依据: 竖排「行头禁则/行尾禁则」—— 闭括号不得出现在列首、开括号不得出现在列尾, 故「行首闭括号」
#   必是列拆分错位, 该括号属于上一列行尾。
# 做法: 页内按阅读序维护「未闭合开括号」栈; 行首闭括号若与栈顶同类 -> 移到上一行行尾。
#   **只改文本, 不动 OCR 盒**: 实测两行的盒都覆盖该括号墨迹区, 移动后两列 步进 = 盒高/字数 反而
#   更贴源书(p3 例: 8 字 34.75pt -> 9 字 30.9pt, 源书实测 30.5pt); 页内字符总量守恒。
BR_OPEN_OF = {'）': '（', '」': '「', '』': '『', '〕': '〔', '】': '【', '》': '《', '〉': '〈'}

def fix_split_brackets(rows):
    """页内 OCR 行文本(阅读序) -> (新行文本列表, [(行号, 括号)] 归位记录)。
    行首闭括号且页内(含前面的行)存在未闭合的同类开括号时, 该括号归位到上一行行尾。"""
    out = list(rows)
    stack = []                                # 未闭合开括号(按阅读序)
    fixes = []
    for i, t in enumerate(out):
        while t and t[0] in BR_OPEN_OF and stack and stack[-1] == BR_OPEN_OF[t[0]] and i > 0 and out[i - 1]:
            stack.pop()
            out[i - 1] = out[i - 1] + t[0]
            fixes.append((i, t[0]))
            t = t[1:]
            out[i] = t
        for c in t:
            if c in BR_OPEN_OF.values():
                stack.append(c)
            elif c in BR_OPEN_OF and stack and stack[-1] == BR_OPEN_OF[c]:
                stack.pop()
    return out, fixes


# ---------- 1) 参数拟合 ----------
def col_stats(k):
    """每列: (x0,x1,y0,y1,t)"""
    out = []
    for t, p in zip(sl.get(k, []), co.get(k, [])):
        if not p: continue
        xs = [q[0] for q in p]; ys = [q[1] for q in p]
        out.append((min(xs), max(xs), min(ys), max(ys), _norm_punct(t.strip())))
    return out

# §1.0d 应用: 行首闭括号归位上一列(只改文本, 几何/OCR 盒不动; 全书 9 例, 见 §1.0d)
_br_fix = []
for _pi, _k in enumerate(keys):
    _rows2, _fx = fix_split_brackets(sl.get(_k, []))
    if _fx:
        sl[_k] = _rows2
        for _ri, _c in _fx:
            _br_fix.append((_pi + 1, _ri + 1, _c))
if _br_fix:
    print('[禁则归位] 行首闭括号回上一列 %d 处: %s' % (
        len(_br_fix), ', '.join('p%d行%d「%s」' % f for f in _br_fix)))
else:
    print('[禁则归位] 未检出(无行首闭括号待归位)')

all_rows = {k: col_stats(k) for k in keys}

def is_body_col(x0, x1, y0, y1, t):
    """v1.1 列分类: 正文/标题进流; 书眉/页码(右页边带内的短行)与左侧小字边注(左页边带内的小字号)排除。
    门限全部是**相对量**(§0.5): 页边带 = 页宽比例(有实测内框时 §1.96a 再并上内框缘), 长行 = 页高比例,
    小字 = 页高比例 —— wz6 上与原绝对量(1100/100/300/55 px)数值相同。"""
    h = y1 - y0; L = len(t)
    if '\n' in t: return False      # 竖排列 = 单行; 含换行的 OCR 框是多块合并的残片(全书 7 条:
                                    #   p74 图表图例 194 字/p156 注码列/p97·p159·p199·p223 版心「第二卷·抗日戰爭時期」
                                    #   /p90 二天大) —— 当正文排会撑出整页(实测 p74 因此在 231 页里多出 1 页)
    if h < LONG_H_PX or L < 2: return False
    if x0 > BAND_R_PX and h < LONG_H_PX: return False   # 书眉/页码(右页边带内的短行; 长行判据已在前一条
                                    #   返回, 故本支实际不可达 —— 保留以维持原判据的字面结构)
    if x0 < BAND_L_PX and h / L < SMALL_FS_PX: return False      # 左侧小字边注
    return True

# 正文列统计(is_body_col 过滤)
body_h = []; body_fs = []; body_w = []
body_x0 = []; body_top = []; body_right = []
for k in keys:
    for x0,x1,y0,y1,t in all_rows[k]:
        if is_body_col(x0,x1,y0,y1,t):
            h = y1-y0
            body_h.append(h); body_fs.append(h/len(t)); body_w.append(x1-x0)
            body_x0.append(x0); body_top.append(y0); body_right.append(x1)

H_col = statistics.median(body_h) if body_h else 1780          # 列高 px
FS_px = statistics.median(body_fs) if body_fs else 35.5*2       # 字距 px
TOP = statistics.median(body_top) if body_top else 600          # 天头 px
RIGHT = max(body_right) if body_right else 1180                 # 版心右缘 px

# 列距(相邻列 x0 差的中位)
pitches = []
for k in keys[:40]:
    rows_b = [r for r in all_rows[k] if is_body_col(*r)]
    xs = sorted(set(r[0] for r in rows_b), reverse=True)
    for a, b in zip(xs, xs[1:]):
        if 60 < a-b < 160: pitches.append(a-b)
PITCH_px = statistics.median(pitches) if pitches else 94

# 每页列数(容量): 必须覆盖「最密页」而不是中位 —— tate 下累积列数超过 textheight 会触发分页,
# 全书跑实测: 中位 12 列但 13 列页有 44 个 -> 每超出 1 列就多出一页(231 页跑成 286 页)。
ncols = [sum(1 for r in all_rows[k] if is_body_col(*r)) for k in keys]
_nc = sorted(n for n in ncols if n >= 5)
NCOL = int(os.environ.get('VERT_NCOL') or (_nc[min(len(_nc) - 1, int(0.9 * len(_nc)))] if _nc else 11))

FS = round(FS_px/2.0, 1)          # pt
PITCH = round(PITCH_px/2.0, 1)    # pt
HCOL = round(H_col/2.0, 1)
TTOP = round(TOP/2.0, 1)
RIGHT_p = RIGHT/2.0
TW_pt = HCOL                       # textwidth = 列高
TH_pt = round(NCOL*PITCH + 12, 1)  # textheight = 列区横向容量(最大列数×列距+余量)
TM_pt = round(TTOP - 102, 1)       # topmargin = 天头-102
OM_pt = round(RIGHT_p - TH_pt - 70, 1)  # 右缘定位拟合: 右缘 = 70 + om + textheight (e10c/exp13/bv 三点回归)
# 页面尺寸/源文档句柄: §0.5 已取(纸型基准需要先用)

print('[竖排拟合] 字号%.1fpt 列距%.1fpt 列高%.1fpt 天头%.1fpt 右缘%.1fpt 列数%d 页%.1f×%.1f' % (
    FS, PITCH, HCOL, TTOP, RIGHT_p, NCOL, page_w, page_h))

# ---------- 1.05) 小字/碎片判据的相对量(纸型无关化 taskN) ----------
# 下列常数原是 wz6 的 2x px 绝对量(边缘小字组件的尺寸窗/窗口大小/碎片容差), 与开本和字号绑定。
#   本轮改为**相对 OCR 正文字步进 FS_px**(同一本书里「小字组件」相对正文的量级关系才是稳定的):
#     ink_extent 窗口 ±70/±250px   = 1.0175 / 3.6339 x FS_px
#     组件窗 宽 4-40 高 5-90 px    = 0.0581-0.5814 / 0.0727-1.3082 x FS_px; 面积 >=40px² = 0.00845 x FS_px²
#     碎片判据 x 重叠容差 24px     = 0.3488 x FS_px
#     note_rows 步进下限 15px      = 0.2180 x FS_px(挡 OCR 噪声页)
#   round() 后 wz6 上与原整数门限逐项相同(比例 x FS_px ≈ 原值 ±1e-3, 取整回原值)。
#   注意: FS_px 是**正文**步进中位; 边缘小字本身更小, 用正文步进当基准是有意为之(见 spec 09 §8.2)。
_FS_WZ6 = 68.796      # wz6 正文字步进中位(2x px) = 换算基准(实测值, 见 docs/vert_paper_agnostic_report.md)
def _fsf(v_wz6, env=None):
    """wz6 绝对 px -> 按「正文字步进」比例换算到本书(px, 取整)。env 显式给比例时优先。"""
    f = float(os.environ[env]) if (env and os.environ.get(env)) else v_wz6 / _FS_WZ6
    return max(1, int(round(f * FS_px)))

FRAG_OVL_PX = _fsf(24.0, 'VERT_FRAG_OVL_FRAC')         # 碎片判据 x 重叠容差(special_rows)
NOTE_STEP_MIN = _fsf(15.0, 'VERT_NOTE_STEP_MIN_FRAC')  # 边注步进下限(note_rows; 挡 OCR 噪声页: p231 残片 1.1px)
NOTE_LX_TOL_PX = _fsf(2.0, 'VERT_NOTE_LX_TOL_FRAC')    # 边注「在版心左缘外」的容差(note_rows: x1 <= 版心左缘+2)
ZONE_PAD_MIN_PX = _fsf(8.0, 'VERT_ZONE_PAD_MIN_FRAC')  # 边注区带最小外扩(note_cols: max(8, 0.6x步进))
INK_WIN_X = _fsf(70.0, 'VERT_INK_WIN_X_FRAC')          # 边缘小字窗口 x 半宽(ink_extent)
INK_WIN_Y = _fsf(250.0, 'VERT_INK_WIN_Y_FRAC')         # 边缘小字窗口 y 半宽(ink_extent)
INK_CW_LO = _fsf(4.0, 'VERT_INK_CW_LO_FRAC')           # 组件宽下限
INK_CW_HI = _fsf(40.0, 'VERT_INK_CW_HI_FRAC')          # 组件宽上限
INK_CH_LO = _fsf(5.0, 'VERT_INK_CH_LO_FRAC')           # 组件高下限
INK_CH_HI = _fsf(90.0, 'VERT_INK_CH_HI_FRAC')          # 组件高上限
INK_AREA = max(1, int(round(40.0 / _FS_WZ6 ** 2 * FS_px ** 2)))   # 组件面积下限(px²)
print('[小字判据] 正文字步进 %.3f px; 小字窗口 ±%d x ±%d; 组件 宽%d-%d 高%d-%d 面积>=%d px²; '
      '碎片容差 %d px; 边注步进下限 %d px (wz6 原值 70/250/4/40/5/90/40/24/15)' % (
          FS_px, INK_WIN_X, INK_WIN_Y, INK_CW_LO, INK_CW_HI, INK_CH_LO, INK_CH_HI,
          INK_AREA, FRAG_OVL_PX, NOTE_STEP_MIN))

# ---------- 1.06) 无版框书: 逐页门限(定义在 §1.975 之前 —— §1.8/§1.9 起判据就要用) ----------
# NF_MODE 在 §1.975 判定(需要 §1.96a 的 FRAME_REF); 在那之前 _NF['on'] 为 False -> 这些函数原样
# 返回上面的全局门限(有版框书与既有路径逐位不变)。
_NF = {'on': False}             # 无版框路径开关(§1.975 置位)
_nf_cache = {}                  # 逐页伪版心缓存(nf_frame, §1.975)

def _nf_ink_gray(a):
    """灰度页 -> 墨迹二值阈值(Otsu: 纸/墨两簇之间)。纯函数(入参任意灰度序列, 返回 int)。
    为什么无版框书要逐页自适应: 固定阈值 150 是 wz6 的口径(纸 253 / 墨核心 ~50 -> 150 恰是两者中点,
    等价「清晰墨边界」); 换到灰底扫描(实测 wz7 纸 185-199 / 墨核心 ~40 -> 中点 ~120)阈值 150
    会把边缘灰晕算进墨迹 —— 面积口径随阈值变化在 wz6 只有 +36%(110->170), 在 wz7 是 +110%
    (a/h² 0.23->0.47), 后果 XSCALE 1.85(应为 ~0.87)、标点墨高比 +30%。Otsu 与「清晰边界」同口径。"""
    import numpy as np
    h = np.bincount(np.asarray(a).ravel(), minlength=256).astype(float)
    tot = h.sum(); sm = float((np.arange(256) * h).sum())
    best, bk, w0, s0 = -1.0, 128, 0.0, 0.0
    for t in range(256):
        w0 += h[t]; s0 += t * h[t]
        w1 = tot - w0
        if w0 <= 0 or w1 <= 0: continue
        v = w0 * w1 * (s0 / w0 - (sm - s0) / w1) ** 2
        if v > best: best, bk = v, t
    return bk

NF_LINE_CV = float(os.environ.get('VERT_NF_LINE_CV') or 0.75)
# taskCK2: 行↔槽 y 跨度夹取的兜底 —— 槽跨度 > 2.5x 行跨度时无条件夹取
#   (修 p86 那类「邻列墨迹渗入使子槽 top 被拉高 300pt」, 见夹取块内注释)
ROWCLIP_SPAN = os.environ.get('VERT_ROWCLIP_SPAN', '1') not in ('0', 'false', 'False')
# taskCK2: 槽跨度 > N x (字数 x 步进) 时无条件夹取（该行装不满这个槽，说明槽含别的墨）
ROWCLIP_FILL = float(os.environ.get('VERT_ROWCLIP_FILL') or 1.6)
     # 竖线列判据: 列墨占比(印刷直线≈1)
NF_LINE_RV = float(os.environ.get('VERT_NF_LINE_RV') or 0.45)     # 横线行判据(与 frame_geom V_H_COV 同源)
NF_LINE_VLEN = 0.50     # 竖线纵向跨度下限(页高比例; 版框/界行线近乎贯穿, 正文列的字间空隙达不到)
NF_LINE_HLEN = 0.55     # 横线横向跨度下限(纸宽比例; 与 frame_geom 同值)

def _nf_lines(ink):
    """无版框页墨迹 -> (竖线像素区段, 横线像素区段) —— 印刷直线(版框/界行线/表格线)。
    判据见 _nf_delines; 抽出来是因为伪版心(§1.975 ② 框优先)要用线的位置定框。"""
    import numpy as np
    H, W = ink.shape
    if H < 8 or W < 8: return [], []
    colc = ink.mean(axis=0)
    vr = [r for r in _runs(colc > NF_LINE_CV, 1) if r[1] - r[0] + 1 >= 3]
    rowc = ink.mean(axis=1)
    hr = [r for r in _runs(rowc > NF_LINE_RV, 1) if r[1] - r[0] + 1 >= 2]
    vdel = []
    for x0, x1 in vr:
        ys = np.where(ink[:, x0:x1 + 1].any(axis=1))[0]
        if len(ys) and (ys[-1] - ys[0] + 1) >= NF_LINE_VLEN * H: vdel.append((x0, x1))
    hdel = []
    for y0, y1 in hr:
        xs = np.where(ink[y0:y1 + 1, :].any(axis=0))[0]
        if len(xs) and (xs[-1] - xs[0] + 1) >= NF_LINE_HLEN * W: hdel.append((y0, y1))
    return vdel, hdel

def _nf_delines(ink):
    """无版框页墨迹 -> 去「印刷线」(版框外框/界行线/表格线)后的墨迹。纯函数。
    为什么必须去: 伪槽格把「列带」当列、把「柱内 y 投影 run」当字 —— 页面上若印了粗黑版框,
    框线自身就是一条满高 run(覆盖率≈1.0, 而正文列 <=0.30), 会造成两处污染:
      ① 框的左右竖线各成一条列带(cov≈1 远高于 0.12) -> 列带凭空多 2 条, 行/槽配对整体错位;
      ② 框线落进某槽 -> 该槽 hm = 整页高 -> 字号被算成 146pt(真值 ~103pt), 触发基准否决 -> 兜底越界。
    实测(wz7 序/扉页, 源页 5-27): 去线后列带数 8->6 / 13->11 / 7->5, 与源书实际列数吻合。
    判据(与 frame_geom 同源, 只认「又长又直」的线, 不碰文字笔画):
      竖线 = 逐像素列的墨占比 > NF_LINE_CV 且该列连续段跨度 >= NF_LINE_VLEN x 页高;
      横线 = 逐像素行的墨占比 > NF_LINE_RV 且横向跨度 >= NF_LINE_HLEN x 纸宽。
    删除时各向外扩 1px(线的抗锯齿边缘), 仅删线本身。"""
    vdel, hdel = _nf_lines(ink)
    if not vdel and not hdel: return ink
    out = ink.copy()
    for x0, x1 in vdel: out[:, max(0, x0 - 1):x1 + 2] = False
    for y0, y1 in hdel: out[max(0, y0 - 1):y1 + 2, :] = False
    return out

_nf_ink_cache = {}
def _nf_ink(pi):
    """无版框页的源图墨迹布尔图(逐页 Otsu 阈值 + 去印刷线; 与标定样本/渲染同一口径)。"""
    if pi not in _nf_ink_cache:
        a = src_gray(pi)
        _nf_ink_cache[pi] = _nf_delines(a < _nf_ink_gray(a))
        if len(_nf_ink_cache) > 8:
            _nf_ink_cache.pop(next(iter(_nf_ink_cache)))
    return _nf_ink_cache[pi]

NF_BOX_WMIN = float(os.environ.get('VERT_NF_BOX_WMIN') or 0.35)   # 框宽/页宽 下限
NF_BOX_HMIN = float(os.environ.get('VERT_NF_BOX_HMIN') or 0.35)   # 框高/页高 下限
_nf_box_cache = {}
def _nf_box(pi):
    """无版框页的**印刷版框** -> (in_l, in_r, in_t, in_b) pt(框线内缘) 或 None。
    为什么无框书也要找框: 本册正文页确无框, 但「序/凡例/題辭」页印着粗黑方框(无界行线 ——
    frame_geom 要求 >=6 条细竖线, 故版框路径整体测不到, 本册才走 NF)。而 §1.975 的伪版心原取
    「正文 OCR 行盒并集」, OCR 盒带系统缩放/相位漂移(实测该书 x 尺度 1.07-1.20), 框是印刷常数。
    实测: 用 OCR 盒版心, 源页 22-27 的列底越出页幅(30-94pt) 且行/槽配对错位(7 行 -> 1 槽);
      用框版心, 列被框住, 配对与列位同时归位(见 docs/vert_wz7_300_report.md)。
    只认「最外一对竖线 + 最外一对横线」围出的方框(框宽/高 >= 页幅 35%); 无框页 -> None
      (仍走 OCR 盒版心, 正文页一字不改)。"""
    if pi in _nf_box_cache: return _nf_box_cache[pi]
    r = None
    if src_doc is not None and 0 <= pi < src_doc.page_count:
        a = src_gray(pi)
        ink = a < _nf_ink_gray(a)                  # 要的就是线本身, 故用**未去线**的墨迹
        H, W = ink.shape
        vd, hd = _nf_lines(ink)
        if len(vd) >= 2 and len(hd) >= 2:
            v0, v1 = min(vd), max(vd)
            h0, h1 = min(hd), max(hd)
            il, ir = (v0[1] + 1) / 2.0, v1[0] / 2.0        # 竖线内缘(px -> pt)
            it, ib = (h0[1] + 1) / 2.0, h1[0] / 2.0
            if (ir - il) >= NF_BOX_WMIN * W / 2.0 and (ib - it) >= NF_BOX_HMIN * H / 2.0:
                r = (il, ir, it, ib)
    _nf_box_cache[pi] = r
    return r

def _src_ink(pi):
    """标定/无框路径的源图墨迹: NF 页用逐页自适应阈值, 其余(有版框书如 wz6)**固定 150 不变**。"""
    return _nf_ink(pi) if (_NF['on'] and src_doc is not None) else src_gray(pi) < 150

def _frame_ink(pi, g):
    """§1.98/§1.99 路径的源图墨迹: 伪版心(virtual)页用自适应阈值, 有版框页固定 150 不变。"""
    return _nf_ink(pi) if (g and g.get('virtual')) else src_gray(pi) < 150

def _nf_page_px(pi):
    """本页纸型(2x px)。**逐页**取源 PDF 的真实页幅 —— 混纸型书(同一册里有多种开本, 实测 wz7 有
    922x1437 / 892x1323 / 705x1084 三种)用全局基准会把小开本页的门限算错。无源 PDF -> 全局基准。"""
    if src_doc is not None and 0 <= pi < src_doc.page_count:
        r = src_doc[pi].rect
        return round(r.width * PT_PER_PX, 1), round(r.height * PT_PER_PX, 1)
    return PW_PX, PH_PX

def _nf_thr(k):
    """无版框书: 本页门限 (长行下限, 右页边带, 左页边带, 碎片容差)。
    ① 按本页纸型比例缩放(混开本: 全局门限对 705pt 小开本页会差 ~30%);
    ② 页边带再并上**本页伪版心缘**(§1.96a 同口径 —— 实测该书页码在版心右缘之外、但只到 87% 页宽,
       用 wz6 的 92.4% 页宽比例带会漏检; 并上伪版心缘即认到)。
    非 NF(含所有有实测版框的书) -> 返回原全局门限(逐位不变)。"""
    if not _NF['on'] or src_doc is None:
        return LONG_H_PX, BAND_R_PX, BAND_L_PX, FRAG_OVL_PX
    pw, ph = _nf_page_px(keys.index(k))
    sx, sy = pw / PW_PX, ph / PH_PX
    br, bl = BAND_R_PX * sx, BAND_L_PX * sx
    gv = _nf_cache.get(keys.index(k))
    if gv:
        br, bl = _band_union(br, bl, gv['in_l'], gv['in_r'])
    return LONG_H_PX * sy, br, bl, FRAG_OVL_PX * sx

# ---------- 1.8) 书眉/页码(边缘小字) ----------
# 要点(实测, 勿凭直觉):
# 1) OCR bbox 对边缘小字系统性偏移(右页偏右 18pt / 页码偏低 45pt), 渲染坐标必须用源图墨迹实测定;
# 2) tate(FG) 的 \put 坐标轴: 先 \setlength{\paperheight} 为真页高, 锚点才落在「页真左下」;
#    y 向上, 内容参考点≈字墨迹底(baseline), 逐字手工断列(每字一 \put)。
NUM_CHARS = set('0123456789〇零一二三四五六七八九十百千')
SPECIAL = os.environ.get('VERT_SPECIAL', '1') not in ('0', 'false', 'False') and src_doc is not None
X_CAL = 0.0    # \put x 标定: 实测 put x = 字盒左缘(exp_pos4: put 480 -> ink 480.0)
Y_CAL = 0.0    # \put y 标定: 实测 put y = 字墨迹底(baseline); 渲染后按输出墨迹复核微调

def special_rows(k):
    """边缘小字行 -> [(kind, text, x0,x1,y0,y1)] px。kind: 'pn'=页码(纯数字/汉字数字) 'hd'=书眉。
    过滤: 长行(h>=页高比例)/超长文本(>10字)/不在左右页边带; 且剔除「被更长同行竖向包含」的碎片(边注列断行)。
    门限相对量见 §0.5(BAND_R_PX/BAND_L_PX/LONG_H_PX; wz6 上 = 1100/100/300 px)。"""
    rows = all_rows[k]; out = []
    _lh, _br, _bl, _fo = _nf_thr(k)      # 无版框书: 本页纸型/伪版心缘的口径(有版框书 = 原全局门限)
    for r in rows:
        x0, x1, y0, y1, t = r
        if y1 - y0 >= _lh or not (2 <= len(t) <= 10): continue
        _hit_band = (x0 > _br or x1 < _bl)
        if os.environ.get('VERT_SPECIAL_DBG'):
            print('    [特殊行候选] %r x%.1f-%.1f y%.1f-%.1f len%d bl=%.1f br=%.1f -> %s' % (
                t[:12], x0, x1, y0, y1, len(t), _bl, _br, '入带' if _hit_band else '不在边带'))
        if not _hit_band: continue
        frag = False
        for o in rows:
            if o is r: continue
            if o[2] <= y0 and y1 <= o[3] and (o[3] - o[2]) > (y1 - y0) and min(x1, o[1]) - max(x0, o[0]) > -_fo:
                frag = True; break
        if frag: continue      # 边注/正文长列里的断行碎片, 非书眉页码
        # taskCK: **同列成链**的行不是书眉/页码, 而是正文列被 OCR 断开的首/末段。
        #   实测 wz7 每章末页的左缘列 = 「第N回 + 回目上句 + 回目下句」, OCR 拆成 3 行且 x 带相同;
        #   「第N回」在左页边带内(短行) -> 被认成书眉, 由 special_tex 用源墨迹单独画一遍;
        #   其余回目行被 _merge_col_rows 合成正文列, 但槽跨度含「第N回」的墨 -> col_puts 把回目字
        #   摊满整列, 与 special_tex 画的书眉在 y 上交错(文本层乱序, 审计列内叠字)。
        #   判据: 邻近行(上或下)与本站 x 带重叠 >= 60% 小者宽, y 间距 <= 2.5 x 邻行步进,
        #   且邻行像正文/回目(>= 4 字; 页码/短注 2-3 字不算) -> 本站是该列的一段, 不认领。
        _chain = False
        if _NF['on']:                      # 只无版框伪槽格路径(wz6 有版框 -> 逐位不变)
            for o in rows:
                if o is r: continue
                if len(o[4]) < 4: continue      # 邻行须像正文/回目(页码/短注 2-3 字不算)
                ox0, ox1, oy0, oy1, ot = o
                if min(x1, ox1) - max(x0, ox0) < 0.6 * min(x1 - x0, ox1 - ox0): continue
                _so = (oy1 - oy0) / float(_step_chars(ot))
                if _so <= 0: continue
                if 0 <= oy0 - y1 <= 2.5 * _so or 0 <= y0 - oy1 <= 2.5 * _so:
                    _chain = True; break
        if _chain:
            if os.environ.get('VERT_SPECIAL_DBG'):
                print('    [特殊行拒认] p? %r x%.1f-%.1f y%.1f-%.1f -> 同列成链(正文列一段)'
                      % (t[:12], x0, x1, y0, y1))
            continue
        kind = 'pn' if all(c in NUM_CHARS for c in t) else 'hd'
        if os.environ.get('VERT_SPECIAL_DBG'):
            print('    [特殊行认领] %s %r x%.1f-%.1f y%.1f-%.1f' % (kind, t[:12], x0, x1, y0, y1))
        out.append((kind, t, x0, x1, y0, y1))
    return out

_pg_cache = {}
def src_gray(pi):
    """源页 2x 灰度 ndarray(缓存, 只留最近 8 页: 全书 231 页全缓存 = 3MB/页 太占内存)"""
    if pi not in _pg_cache:
        import numpy as np
        pix = src_doc[pi].get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY)
        _pg_cache[pi] = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()
        while len(_pg_cache) > 8:                      # FIFO 淘汰(按插入序, 不能按页号: 抽样会在乱序访问)
            _pg_cache.pop(next(iter(_pg_cache)))
    return _pg_cache[pi]

def ink_extent(pi, x0, x1, y0, y1, others, floor=None):
    """源页墨迹实测: OCR 行邻域内小字组件的并集 bbox(px)。OCR bbox 对边缘小字不可靠(偏 18-180px)。
    门限(相对量, §1.05): 宽 INK_CW_LO-HI(版框线/正文字更宽)、高 INK_CH_LO-HI(版框线更高)、
          面积>=INK_AREA、不贴窗口边缘(裁剪碎片丢弃)、且 y 中心不落在同页其它特殊行的 OCR 区间内
          (p7 第二卷/抗日戰争時期 紧邻, 靠此分离)。wz6 上 = 宽 4-40 / 高 5-90 / 面积 40px²。"""
    from scipy import ndimage
    a = src_gray(pi); H, W = a.shape
    cx = int((x0 + x1) // 2)
    wx0, wx1 = int(max(0, cx - INK_WIN_X)), int(min(W, cx + INK_WIN_X))
    wy0, wy1 = int(max(0, y0 - INK_WIN_Y)), int(min(H, y1 + INK_WIN_Y))
    if wx1 <= wx0 or wy1 <= wy0: return None    # OCR 行 bbox 越出页面时窗口为空(全书跑实测 p159 触发)
    # 阈值: wz6 口径固定 185(略宽于正文阈值 150, 边缘小字墨淡); 无版框书(NF)按本页对比度取阈
    #   —— 灰底扫描(wz7 纸 185-199)用 185 会把整片纸纹当墨迹, 组件窗再滤也挡不住。
    _t = min(185, _nf_ink_gray(a)) if (_NF['on'] and src_doc is not None) else 185
    lab, n = ndimage.label(a[wy0:wy1, wx0:wx1] < _t)
    cs = []
    for i, s in enumerate(ndimage.find_objects(lab), 1):
        h = s[0].stop - s[0].start; w = s[1].stop - s[1].start
        if (lab[s] == i).sum() < INK_AREA: continue
        if not (INK_CW_LO <= w <= INK_CW_HI and INK_CH_LO <= h <= INK_CH_HI): continue
        ya, yb, xa, xb = wy0 + s[0].start, wy0 + s[0].stop, wx0 + s[1].start, wx0 + s[1].stop
        if xa <= wx0 + 1 or xb >= wx1 - 1 or ya <= wy0 + 1 or yb >= wy1 - 1: continue   # 贴边=裁剪碎片
        cy = (ya + yb) / 2.0
        if floor is not None and cy < floor: continue                                    # 上界: 已被上一特殊行占用
        if any(o[2] - 1 <= cy <= o[3] + 1 for o in others): continue                     # 属其它特殊行(y 区间内)
        cs.append((ya, yb, xa, xb))
    if not cs: return None
    iy0 = min(c[0] for c in cs); iy1 = max(c[1] for c in cs)
    cap = 1.3 * (y1 - y0)                       # 上限: 整段墨迹高不得超过 OCR 行长 1.3 倍(防并入邻行)
    if iy1 - iy0 > cap: iy1 = iy0 + cap
    return (min(c[2] for c in cs), iy0, max(c[3] for c in cs), iy1)

def special_tex(k, pi):
    """书眉/页码 tex 片段: 一次 \\AddToShipoutPictureFG* 内多 \\put(逐字), 坐标=源墨迹实测(pt)。
    字号由墨迹高/字数反推, 字步进 = (墨迹高 - 字墨高)/(字数-1) -> 整段墨迹上下缘与源书对齐。
    注意: 必须用带星号的 \\AddToShipoutPictureFG*(仅本页) —— 无星号是"每页累积",
          不加星号会把此前所有页的书眉/页码重画到本页(实测 probe: 第 4 页出现 論持久戰 一八0 論持久戰 一八二)。"""
    out = []
    rows = sorted(special_rows(k), key=lambda r: r[4])
    prev_y1 = None
    for kind, t, x0, x1, y0, y1 in rows:
        if kind == 'pn' and (pi + 1) in PN_FIX:
            t = PN_FIX[pi + 1]      # §1.87 页码序列纠正: 误读按邻页插值纠正; 0 统一成 〇
        ie = ink_extent(pi, x0, x1, y0, y1,
                        [(r[2], r[3], r[4], r[5]) for r in rows if (r[4], r[5]) != (y0, y1)], prev_y1)
        prev_y1 = y1
        if not ie: continue
        ix0, iy0, ix1, iy1 = ie
        n = len(t)
        ink_h = (iy1 - iy0) / 2.0                       # 整段墨迹高 pt
        font = min(20.0, max(9.0, round(ink_h / n / 1.15, 1)))
        gink = 0.88 * font                              # 单字墨高(Noto CJK ink 比)
        step = max(0.98 * font, (ink_h - gink) / max(1, n - 1))
        put = []
        for i, ch in enumerate(t):
            top = iy0 / 2.0 + i * step                  # 该字墨迹顶(pt, 页顶向下)
            y_put = page_h - top - gink + Y_CAL         # \put y 向上, 参考点≈墨迹底
            # 括号走 §1.0c 竖排形态(书眉/页码基本不含括号, 为一致性同样处理; 此处无横向压缩 -> xs=1)
            ch, _f2, _x2, _y2 = _br_put(ch, ix0 / 2.0 + X_CAL, y_put, font, xs=1.0)
            if _NF['on']:                       # ① 实测文本框夹取(taskP2; 书眉/页码路径原无夹取)
                _y2 = _txtbox_clamp_y(_y2, _f2, page_h)
            ch = ch.replace('%', r'\%').replace('#', r'\#').replace('&', r'\&').replace('_', r'\_')
            put.append(r'\put(%.1f,%.1f){%s}' % (_x2, _y2, _vb(
                r'\fontsize{%spt}{%spt}\selectfont %s' % (_f2, _f2, ch))))
        out.append('\\AddToShipoutPictureFG*{%%\n  ' + '%%\n  '.join(put) + '}')
        print('  [%s] p%d %-10s 墨迹x%.1f-%.1f y%.1f-%.1f 字号%.1f 步进%.1f n%d' % (
            '页码' if kind == 'pn' else '书眉', pi + 1, t, ix0 / 2.0, ix1 / 2.0,
            iy0 / 2.0, iy1 / 2.0, font, step, n))
    return out

# ---------- 1.9) 边注(版心外小字注) ----------
# 现象(实测): 左侧小字注字号明显小于正文(步进 47.6px vs 正文 68.9px), 且落在版心左缘之外
#   (如 p4: "*這是毛澤東同志一九三八年五月二十六日至六月三日在延安抗日戰爭研究會上" x54-104,
#    续列 "的講演" x12-60 在左; 源图 x 12-104 为版框内的注栏, 正文列从 x119 起)。
# v1 的 is_body_col 只把它"排除出正文"(不渲染); 本段按墨迹实测定坐落位与字号。
# 判据(全书盘点见 tmp_vert/survey_note2.py): 未被书眉/页码认领 且 步进 ∈ [NOTE_STEP_MIN, NOTE_STEP_RATIO
#   x 正文字步进) 且 (版心外: x0<左页边带终点 且 x1 <= 最左正文列x0+2) 或 (* 开头的题注列)。
# 步进门限全部相对化(§0.5/§1.05): 下限 = 0.218 x FS_px; 上限比 self-calibrated(见 §1.85)。
def _calib_note_ratio(ratios, fallback=0.85):
    """边注/正文 步进比样本 -> (上限值 或 None, 依据)。样本不足返回 (None, 原因) -> 调用方留兜底。
    口径(taskN, 与 §1.954 线宽同思路 —— **找实测分布里的空档**):
      ① 取比值中位以上的样本, 找它们的**最大间隙**(注簇上缘 -> 正文簇下缘);
      ② 上限 = 空档中点, 夹在 [0.5, 0.95](必须 < 1: 正文列的步进 ≈ FS_px; 下限挡噪声);
      ③ 空档太窄(<0.08, 说明注/正文在比值上连续, 分割不可靠)或样本不足 -> 不标定;
      ④ **兜底值若落在同一空档内(分类结果必然相同), 保留兜底值** —— 值面零漂移。
    wz6 实测: 206 条比值 ∈ [0.004, 1.068], 中位 0.549, 注簇上缘 0.833, 正文簇 1.068,
      空档 (0.833, 1.068) 含兜底 0.85 -> 保留 0.85(与原常数分类逐条相同)。"""
    if len(ratios) < 8: return None, '样本 %d 条(需 >=8)' % len(ratios)
    rs = sorted(ratios)
    p50 = rs[len(rs) // 2]
    gap, lo_, hi_ = 0.0, p50, rs[-1]
    prev = p50
    for v in rs:
        if v <= p50: continue
        if v - prev > gap: gap, lo_, hi_ = v - prev, prev, v
        prev = v
    if gap < 0.08:
        return None, '最大空档仅 %.3f(注/正文在比值上连续)' % gap
    if lo_ < fallback <= hi_:
        return fallback, '兜底 %.2f 落在空档 (%.3f, %.3f) 内 -> 保留' % (fallback, lo_, hi_)
    return round(min(0.95, max(0.5, (lo_ + hi_) / 2.0)), 3), '空档 (%.3f, %.3f) 中点' % (lo_, hi_)

_nr_env = os.environ.get('VERT_NOTE_STEP_RATIO')
if _nr_env:
    NOTE_STEP_RATIO = float(_nr_env)
else:
    _nr_rs = []
    for _k in keys:                                    # 左页边带内的短行(排除书眉/页码认领的)
        _claim = set((c[2], c[3], c[4], c[5], c[1]) for c in special_rows(_k))
        for _r in all_rows[_k]:
            if len(_r[4]) < 2 or (_r[3] - _r[2]) >= LONG_H_PX or _r in _claim: continue
            if _r[0] < BAND_L_PX or _r[4].startswith('*'):
                _nr_rs.append(((_r[3] - _r[2]) / float(len(_r[4]))) / FS_px)
    _nr_v, _nr_why = _calib_note_ratio(_nr_rs)
    NOTE_STEP_RATIO = _nr_v if _nr_v else 0.85         # 兜底 0.85(= wz6 原常数)
    _nrs = sorted(_nr_rs)
    print('[标定·边注] 步进比上限: 样本 %d 条 中位 %.3f p95 %.3f max %.3f -> %.3f (%s, 兜底 0.85; env VERT_NOTE_STEP_RATIO)' % (
        len(_nrs), _nrs[len(_nrs) // 2] if _nrs else 0,
        _nrs[min(len(_nrs) - 1, int(0.95 * len(_nrs)))] if _nrs else 0,
        _nrs[-1] if _nrs else 0, NOTE_STEP_RATIO, _nr_why))
NOTE_INK_RATIO = float(os.environ.get('VERT_NOTE_INK_RATIO') or 0.88)   # 单字墨高/字号(中位口径; §1.956 按当前字体标定)
# taskK-C 字号保护: 注释/页外小字按「中位墨高」定字号, 但满字(講/國/戰 这类占满字身的字)真实墨高
#   可达 0.94 em —— 注释步进本来就紧(源书 墨高/步进 ≈ 0.95, 实测 p4 注 步进 20.5 而 字高 19.0),
#   按中位口径定的字号会让满字互相压住(用户反馈②「注释部分字体有点重合」; 实测产物 p4 注
#   「的講演」「這是毛澤」相邻字墨迹间隙 0.25-1.0pt vs 源书同处 1.5-2.0pt, 8x 放大看已粘连)。
#   故按「满字墨高 <= 0.95 x 步进」压字号再重算步进(整段墨迹上下缘仍与源书对齐)。
NOTE_INK_MAX = float(os.environ.get('VERT_NOTE_INK_MAX') or 0.94)   # 满字墨高上限(em; §1.956 按当前字体标定)
# taskCL-1: 边注/页外「行 ↔ 墨迹字列」配对的距离护栏（单位 = 本书实测列距）
NOTE_PAIR_X = os.environ.get('VERT_NOTE_PAIR_X', '1') not in ('0', 'false', 'False')
NOTE_PAIR_TOL = float(os.environ.get('VERT_NOTE_PAIR_TOL') or 0.55)   # x 列距
NOTE_PAIR_TOL_FRAC = float(os.environ.get('VERT_NOTE_PAIR_TOL_FRAC') or 0.030)  # 列距测不出时的页宽比例

def note_rows(k):
    """本页边注行 [(x0,x1,y0,y1,t)]; 书眉/页码优先认领, 剩下的版心外小字才算边注"""
    rows = all_rows[k]
    claimed = set((c[2], c[3], c[4], c[5], c[1]) for c in special_rows(k))
    lx = min([r[0] for r in rows if is_body_col(*r)], default=0)   # 版心左缘 = 最左正文列 x0
    _lh, _br, _bl, _fo = _nf_thr(k)      # 无版框书: 本页口径(有版框书 = 原全局门限)
    out = []
    for r in rows:
        x0, x1, y0, y1, t = r
        if len(t) < 2 or (x0, x1, y0, y1, t) in claimed: continue
        # taskCK: 连续拉丁串按 1 格计(同 page_rows) —— 词多的正文列不因逐字母计数被误判成边注
        step = (y1 - y0) / float(_step_chars(t) if _NF['on'] else len(t))
        if not (NOTE_STEP_MIN <= step < NOTE_STEP_RATIO * FS_px): continue
        if (x0 < _bl and x1 <= lx + NOTE_LX_TOL_PX) or t.startswith('*'):
            out.append(r)
    return out

def note_cols(pi, k, rows=None, zone=None, zone_y=None):
    """本页"边注字列"墨迹实测: [(x0,y0,x1,y1,字高中位)], 按 x 从右到左(竖排阅读序)。
    做法: 边注区(左缘注列 = [0, 版心左缘]; * 题注列 = 自身 x 带 ±0.6步进)内取连通组件,
    剔版框线/界行线/噪点后按"组件 x 中心"聚成字列(阈值 = 0.75×组件宽中位: 同一列内字中心仅差数 px,
    并排子列中心相差约一字宽)。OCR 的 x 对边缘小字偏移可达 40px(p4 注头 OCR x54-104, 实墨 x94-122),
    所以只用组件自身几何定位, OCR 只用来定"是哪些行"。
    rows/zone/zone_y(§1.98 框驱动路径用): 行集与区带由调用方给定(px), 未给则按旧判据自算。"""
    import numpy as np
    from scipy import ndimage
    if rows is None: rows = note_rows(k)
    if not rows: return []
    steps = sorted((r[3] - r[2]) / float(len(r[4])) for r in rows)
    step = steps[len(steps) // 2]
    m = int(max(ZONE_PAD_MIN_PX, step * 0.6))
    if zone is None:
        lx = min([r[0] for r in all_rows[k] if is_body_col(*r)], default=0)
        _bl2 = _nf_thr(k)[2]                           # 无版框书: 本页左页边带
        zx0 = 10 ** 9; zx1 = -1
        for x0, x1, y0, y1, t in rows:
            if x0 < _bl2:                              # 左缘注列: 整条左白边(到版心左缘)
                a_, b_ = 0, lx + NOTE_LX_TOL_PX
            else:                                      # * 题注列(页中): 自身 x 带
                a_, b_ = x0 - m, x1 + m
            zx0 = min(zx0, a_); zx1 = max(zx1, b_)
    else:
        zx0, zx1 = zone
    if zone_y is not None:
        zy0, zy1 = zone_y
    else:
        zy0 = min(r[2] for r in rows) - m; zy1 = max(r[3] for r in rows) + m
    g = src_gray(pi); H, W = g.shape
    wx0, wx1 = int(max(0, zx0)), int(min(W, zx1))
    wy0, wy1 = int(max(0, zy0)), int(min(H, zy1))
    lab, n = ndimage.label(g[wy0:wy1, wx0:wx1] < 185)
    cs = []
    for i, s in enumerate(ndimage.find_objects(lab), 1):
        h = s[0].stop - s[0].start; w = s[1].stop - s[1].start
        if not (0.25 * step <= w <= 2.2 * step and 0.25 * step <= h <= 2.2 * step): continue
        cs.append([wx0 + s[1].start, wy0 + s[0].start, wx0 + s[1].stop, wy0 + s[0].stop,
                   (wx0 + s[1].start + wx0 + s[1].stop) / 2.0, w, h])
    if not cs: return []
    ws = sorted(c[5] for c in cs); gap = 0.75 * ws[len(ws) // 2]
    cs.sort(key=lambda c: c[4])
    cl = [[cs[0]]]
    for c in cs[1:]:
        if c[4] - cl[-1][-1][4] > gap: cl.append([c])
        else: cl[-1].append(c)
    out = []
    for grp in cl:
        if len(grp) < 2: continue                      # 单组件列 = 噪点/装饰, 丢弃
        hs = sorted(c[6] for c in grp)
        gh = hs[len(hs) // 2]
        ys = sorted(c[1] for c in grp)
        ds = sorted(d for d in (ys[i + 1] - ys[i] for i in range(len(ys) - 1)) if d <= 3 * gh)
        st = ds[len(ds) // 2] if ds else gh            # 实测自然步进(组件顶距中位, 跳并块)
        out.append((min(c[0] for c in grp), min(c[1] for c in grp),
                    max(c[2] for c in grp), max(c[3] for c in grp), gh, st))
    out.sort(key=lambda c: -c[0])
    return out

def _pair_rows_cols_x(rows, cols, tag, pi):
    """行 ↔ 墨迹字列 配对（taskCL-1）。返回 [(row, col 或 None)]，col=None 表示
    「本行墨迹没有在区带里成列」-> 调用方退回该行自己的 OCR 坐标。

    判据 = **x 区间重叠**（两侧各放宽半个字高），不依赖任何反推量：
      · 合法: 边缘小字 OCR x 偏 40pt，注文自身宽 100px -> 与自己的墨迹列仍重叠
      · 病态(p444): 行 1212-1269(放宽 1187-1294) vs 隔壁诗列 1299-1329 -> 不重叠 -> 拒
    旧口径（按顺序 zip）零校验；v1（中心距 x 反推列距）实测容差被算成 89.7px 放过 71.4px。
    多条候选时取「重叠量最大」的，其次取中心最近；一对一贪心，行按 x 降序（竖排阅读序）。
    """
    if not rows:
        return []
    if not cols:
        return [(r, None) for r in rows]
    used = set()
    out = []
    for r in sorted(rows, key=lambda r: -(r[0] + r[1])):
        rx0, rx1 = float(r[0]), float(r[1])
        n_ = max(1, len(r[4]))
        hh = (r[3] - r[2]) / float(n_)          # 单字高(px)
        pad = 0.5 * hh
        lo, hi = rx0 - pad, rx1 + pad
        # taskCL-1g: x 与 y 必须**双向**重叠。竖排同一列的上下两段（书眉 + 页码）x 带相同,
        #   只看 x 会把页顶书眉的墨当成页底页码的列（实测 p210 页码 OCR y1148 配到 y315 的墨,
        #   落点错且与书眉共列 -> 列内叠字各 3 处）。打分用重叠面积, 取最大。
        rlo, rhi = float(r[2]) - pad, float(r[3]) + pad
        best, bov, bd = None, -1.0, 1e18
        for i, c in enumerate(cols):
            if i in used:
                continue
            ovx = min(hi, c[2]) - max(lo, c[0])
            if ovx <= 0:
                continue
            ov = ovx
            # taskCL-1i: y 用量级判据, 不要求严格重叠。
            #   「完全在页面另一段」(y 间隙 > 2 x 行高) 才算配错 —— 实测:
            #   wz7 p210 页码(y1148-1250) vs 书眉列(y315-438): 间隙 710pt -> 拒 ✓
            #   wz6 p162 注行 vs 其字列: y 只轻微错开 -> 接受 ✓(硬性重叠会误伤 3 处真边注)
            ovy = min(rhi, c[3]) - max(rlo, c[1])
            if ovy <= 0:
                _ygap = max(rlo - c[3], c[1] - rhi)
                if _ygap > 2.0 * max(1.0, float(r[3]) - float(r[2])):
                    continue
            d = abs((c[0] + c[2]) / 2.0 - (rx0 + rx1) / 2.0)
            if ov > bov + 1e-9 or (abs(ov - bov) <= 1e-9 and d < bd):
                best, bov, bd = i, ov, d
        if os.environ.get('VERT_NOTE_PAIR_DBG'):
            _cands = ' '.join('[%.0f-%.0f y%.0f-%.0f]' % (c[0], c[2], c[1], c[3])
                              for c in cols[:6])
            print('    [配对调试] 「%s」行x%.1f-%.1f y%.1f-%.1f 包容x%.0f-%.0f pad%.1f 列数%d 候选%s -> %s'
                  % (r[4][:10], rx0, rx1, float(r[2]), float(r[3]), lo, hi, pad,
                     len(cols), _cands, '接受' if bov > 0 else '拒'))
        if best is not None and bov > 0:
            used.add(best)
            out.append((r, cols[best]))
        else:
            print('  [%s-自位] p%d 「%s」OCR x%.1f-%.1f 区带内无重叠墨迹列 -> 用本行自身坐标'
                  % (tag, pi + 1, r[4][:16], rx0 / 2.0, rx1 / 2.0))
            out.append((r, None))
    return out

def note_tex(k, pi, rows=None, zone=None, zone_y=None, tag='边注'):
    """边注 tex 片段: 逐字 \\put。OCR 边注行按 x0 降序(竖排阅读序)配对实测字列(同样 x 降序):
    注文太长时会在下一子列续排(如 p4 注头在右子列、末尾 "的講演" 续在左子列), 子列间无白缝, 只能靠结构配对。
    x = 实测字列左缘; 字号 = 实测单字墨高/ink比(不按字数反推: OCR 会漏字, p4 注头实测约 39 字而 OCR 只 35 字);
    字步进 = (整列墨迹高 - 单字墨高)/(字数-1) -> 整列墨迹上下缘仍与源书对齐。
    rows/zone/zone_y(§1.98 框驱动路径): 行集与区带(px)由调用方给定。"""
    out = []
    rows = sorted(note_rows(k) if rows is None else rows, key=lambda r: -r[0])
    cols = note_cols(pi, k, rows=rows, zone=zone, zone_y=zone_y)
    # taskCL-1h: 护栏只对「边注」(版心内小字注, OCR x 可靠)生效。
    #   页外行(书耳/篇名, OCR x 在图像边缘 0-27pt)的 OCR x 天然永远不与墨迹列重叠 ——
    #   旧顺序 zip 在那里是对的(靠墨迹定位), 套护栏会把 wz6 的 12 处书耳全打成自位 -> tex md5 变。
    pairs = (_pair_rows_cols_x(rows, cols, tag, pi)
             if (NOTE_PAIR_X and tag == '边注') else list(zip(rows, cols)))
    for row, col in pairs:
        if col is None:                       # 自位兜底: 本行墨迹未在区带里成列
            x0, x1, y0, y1, t = row
            n_ = max(1, len(t))
            gh = (y1 - y0) / float(n_)
            col = (x0, y0, x1, y1, gh, gh)
        (x0, x1, y0, y1, t) = row
        ix0, iy0, ix1, iy1, gh, st = col
        n = len(t)
        font = round(min(26.0, max(9.0, gh / 2.0 / NOTE_INK_RATIO)), 1)
        gink = NOTE_INK_RATIO * font                          # 渲染单字墨高(pt)
        step = round(min(st / 2.0, ((iy1 - iy0) / 2.0 - gink) / (n - 1)) if n > 1 else gink, 2)
        # taskK-C 字号保护: 满字墨高(0.94 em)不得压过步进(见 NOTE_INK_MAX 说明)
        if n > 1 and NOTE_INK_MAX * font > 0.95 * step:
            font = round(max(9.0, 0.95 * step / NOTE_INK_MAX), 1)
            gink = NOTE_INK_RATIO * font
            step = round(min(st / 2.0, ((iy1 - iy0) / 2.0 - gink) / (n - 1)), 2)
        put = []
        for i, ch in enumerate(t):
            y_put = page_h - (iy0 / 2.0 + i * step) - gink + Y_CAL
            ch, _f2, _x2, _y2 = _br_put(ch, ix0 / 2.0 + X_CAL, y_put, font, xs=1.0)   # §1.0c
            if _NF['on']:                       # ① 实测文本框夹取(taskP2; 边注路径原无夹取)
                _y2 = _txtbox_clamp_y(_y2, _f2, page_h)
            ch = ch.replace('%', r'\%').replace('#', r'\#').replace('&', r'\&').replace('_', r'\_')
            put.append(r'\put(%.1f,%.1f){%s}' % (_x2, _y2, _vb(
                r'\fontsize{%spt}{%spt}\selectfont %s' % (_f2, _f2, ch))))
        out.append('\\AddToShipoutPictureFG*{%%\n  ' + '%%\n  '.join(put) + '}')
        print('  [%s] p%d %-24s 字列x%.1f-%.1f y%.1f-%.1f 字高%.1f 字号%.1f 步进%.2f n%d' % (
            tag, pi + 1, t[:24], ix0 / 2.0, ix1 / 2.0, iy0 / 2.0, iy1 / 2.0, gh / 2.0, font, step, n))
    return out

# ---------- 1.87) 页码序列校验/纠正(数据驱动, 不硬编码任何页号) ----------
# 现象(实测): OCR 页码偶发误读 —— p16 一九二(192) 读成 一九二一(1921); p50 二三六 读成 二二六;
#   p96 二七二 读成 二七三; p97 二七四 读成 二十三; p145 三二一 读成 三一一; p149 三二五 读成 三三五。
# 做法: ①各页页码 OCR 文本解析成整数; ②按页序分段(相邻有效页码的页号差 > PN_GAP 处分段, 容忍缺页码页);
#   ③段内做等差数列拟合 value = a*page + c (a = 相邻页斜率中位; 样本 < 4 的短段借全局斜率);
#   ④与拟合偏差 >= PN_TOL 的项判误读 -> 用左右最近的非误读邻页线性插值(单侧则按斜率外推)纠正;
#   ⑤所有解析成功的页统一规范成源书逐字数码文本(OCR 的 0 -> 〇), 供渲染。
# 注: PN_TOL=2 有意放过 ±1 偏差 —— 源书若有合法的跳号(未编号插页), 收紧到 1 会把它误判成误读。
PN_TOL = 2
PN_GAP = 6
_PN_D = {'〇': 0, '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
         '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9}
_PN_U = {'十': 10, '百': 100, '千': 1000}
_PN_R = '〇一二三四五六七八九'

def pn_parse(t):
    """页码文本 -> int 或 None。
    形态① 逐字数码(源书: 一八〇/一七九; OCR 常把 〇 读成 0): 全数码 -> 按位拼接;
    形态② 计数式(如 三百〇五): 含 十/百/千 -> 逐位累加。"""
    tt = [c for c in t if c != ' ']
    if not tt: return None
    if all(c in _PN_D for c in tt):
        v = 0
        for c in tt: v = v * 10 + _PN_D[c]
        return v
    if any(c in _PN_U for c in tt) and all((c in _PN_D or c in _PN_U) for c in tt):
        v = cur = 0
        for c in tt:
            if c in _PN_D: cur = _PN_D[c]
            else:
                v += (cur if cur else 1) * _PN_U[c]; cur = 0
        return v + cur
    return None

def pn_text(v):
    """整数 -> 源书逐字数码风格文本(0 -> 〇): 321 -> 三二一, 180 -> 一八〇"""
    return ''.join(_PN_R[int(d)] for d in str(v))

def pn_sequence_fix():
    """全书页码序列校验 -> (fix, log, info)
    fix: {页序号(1-based): 渲染文本}; log: [(页, OCR文本, OCR值, 纠正值)];
    info: (有效页数, 全局斜率, 全局截距) 供日志。"""
    recs = []
    for i, k in enumerate(keys):
        for kind, t, x0, x1, y0, y1 in special_rows(k):
            if kind != 'pn': continue
            v = pn_parse(t)
            if v is not None: recs.append((i + 1, t, v))
    if not recs: return {}, [], (0, 1.0, 0.0)

    # —— 页码一致性过滤(防正文数字被当页码污染拟合) ——
    # 真页码满足 p - v ≈ 常数(本书正文从 PDF 第 45 页起编页 -> 44); 假页码(正文里的数字行)
    # 散布。取 (p-v) 的最密集簇: 占比 >= 25% 且 >= 3 个样本才采信, 否则全部保留(保守)。
    # 实测 wz7: p263「二一九」=219 (p-v=44) / p276「二三一」=231 (45) 是真页码;
    #          p265「三一」=31 (234) / p282「三八」=38 (244) 是正文数字。
    _clusters = {}
    for _p, _t, _v in recs:
        _d = _p - _v
        _hit = next((_k for _k in _clusters if abs(_k - _d) <= 3), _d)
        _clusters.setdefault(_hit, []).append((_p, _t, _v))
    _n_all = len(recs)
    _best = max(_clusters.values(), key=len)
    if len(_best) >= 3 and len(_best) >= _n_all * 0.25:
        recs = _best
        print('[页码序列] 一致性过滤: 保留 %d/%d 条(淘汰正文数字/误读)' % (len(recs), _n_all))
    else:
        print('[页码序列] 一致性过滤: 无主簇(最大 %d/%d), 全部保留' % (len(_best), _n_all))

    # 全局斜率(相邻有效页码页的斜率中位; 页码应随页序单调递增)
    # p2 - p1 必须 > 0：同一页可能识别出多个页码行(书眉数字/影印页等) -> 否则除零
    gslopes = [(v2 - v1) / float(p2 - p1)
               for (p1, _, v1), (p2, _, v2) in zip(recs, recs[1:]) if 0 < p2 - p1 <= PN_GAP]
    a_glob = statistics.median(gslopes) if gslopes else 1.0
    c_glob = statistics.median(v - a_glob * p for p, _, v in recs)
    fix = {}; log = []
    segs = []
    for r in recs:
        if segs and r[0] - segs[-1][-1][0] > PN_GAP: segs.append([])
        if not segs: segs.append([])
        segs[-1].append(r)
    for seg in segs:
        if len(seg) >= 4:
            _sl = [(v2 - v1) / float(p2 - p1)
                   for (p1, _, v1), (p2, _, v2) in zip(seg, seg[1:]) if p2 > p1]
            a = statistics.median(_sl) if _sl else a_glob
            c = statistics.median(v - a * p for p, _, v in seg)
        else:
            a, c = a_glob, statistics.median(v - a_glob * p for p, _, v in seg)
        good = [abs(v - (a * p + c)) < PN_TOL for p, _, v in seg]
        for i, (p, t, v) in enumerate(seg):
            if good[i]:
                fix[p] = pn_text(v); continue
            j = max([q for q in range(i) if good[q]], default=None)     # 左邻(非误读)
            k_ = min([q for q in range(i + 1, len(seg)) if good[q]], default=None)
            if j is not None and k_ is not None:
                pj, vj = seg[j][0], seg[j][2]; pk, vk = seg[k_][0], seg[k_][2]
                nv = int(round(vj + (vk - vj) * (p - pj) / float(pk - pj))) if pk != pj else vj   # 邻页线性插值(防同页)
            elif j is not None: nv = int(round(seg[j][2] + a * (p - seg[j][0])))   # 单侧外推
            elif k_ is not None: nv = int(round(seg[k_][2] - a * (seg[k_][0] - p)))
            else: nv = int(round(a * p + c))                                   # 段内无参照: 用拟合
            fix[p] = pn_text(nv); log.append((p, t, v, nv))
    return fix, log, (len(recs), a_glob, c_glob)

PN_FIX, PN_LOG, PN_INFO = pn_sequence_fix()
print('[页码序列] 全书 %d 页有页码, 拟合 value = %.3f*page + %.1f; 误读纠正 %d 处%s' % (
    PN_INFO[0], PN_INFO[1], PN_INFO[2], len(PN_LOG), '' if not PN_LOG else ':'))
for p, t, v, nv in PN_LOG:
    print('    p%-3d OCR %-6s(%d) -> %s(%d)' % (p, t, v, pn_text(nv), nv))

# ---------- 1.95) 版框线(外框双边 + 界行线) ----------
# 实测(源书 p3-p231 抽样, 检测脚本 tmp_vert/frame_detect2.py, line_scan.py):
#   版框 = 双边 —— 外粗线 ~3.4pt + 空隙 ~3.2pt + 内细线 ~1pt; 版心内框 ~521 x 801.5pt = 12 列 x 43.4pt;
#   内框左右两条竖线同时是首/末界行线; 界行线 = 列间 1pt 细竖线, 起止同内框上下线;
#   书眉/页码在「订口侧」框外页边内(版心) -> 该侧扫描里只剩内细线(外粗线被装订边/扫描裁切吞掉);
#   横线(内/外)则横跨整幅纸面(含订口页边) -> 横线按源墨迹实测 x 跨度画。
# 判据(实测): 竖线 = 版心 y 区间内该列墨占比 > V_LINE_COV(源书细线 0.70-0.99, 正文列 < 0.55);
#   外粗线 = 组厚 >= V_THICK_MIN 且落在内细线外侧 12pt 内(源书 2.5-4.0pt, 内框/界行线 0.5-1.5pt);
#   渲染: eso-pic 带星版 + \put + \rule(探针 tmp_vert/probe_rule.py 实测: tate 下 \rule 尺寸不旋转,
#   \put 参考点 = rule 左下角, 原点 = 页真左下角, 坐标 1:1 用源书 pt)。
# 判据类常数(尺度无关, 本轮不改 —— 扫描淡墨质量/墨色阈值, 换书风险低): V_LINE_COV / V_LINE_COV_LO / V_H_COV
V_FRAME = os.environ.get('VERT_FRAME', '1') not in ('0', 'false', 'False') and src_doc is not None
V_LINE_COV = float(os.environ.get('VERT_LINE_COV', 0.55))
V_LINE_COV_LO = float(os.environ.get('VERT_LINE_COV_LO', 0.30))   # 淡界行线兜底阈值(见 §1.95b)
V_H_COV = float(os.environ.get('VERT_H_COV', 0.45))   # 横线判据: 实测源书横线 0.58-0.99, 正文行 <=0.30
# 版框「几何合法性区间」(纸型无关化 taskN): 原为 wz6 绝对值 —— 内框高 700-900pt / 内框宽 400-640pt /
#   列距枚举 40-48pt / 栅格跨度窗 400-640pt / 精修列距 35-52pt —— 全部改成**页幅比例**(§0.5 换算基准),
#   wz6 上反算回原值(偏差 0)。env 可用 VERT_*_FRAC 给比例覆盖。
V_INH_LO = _sc_pt(_envfrac('VERT_INH_LO_FRAC', _fp(700.0, 'h')), 'h')     # 内框高下限(原 700pt)
V_INH_HI = _sc_pt(_envfrac('VERT_INH_HI_FRAC', _fp(900.0, 'h')), 'h')     # 内框高上限(原 900pt)
V_INW_LO = _sc_pt(_envfrac('VERT_INW_LO_FRAC', _fp(400.0, 'w')), 'w')     # 内框宽下限(原 400pt)
V_INW_HI = _sc_pt(_envfrac('VERT_INW_HI_FRAC', _fp(640.0, 'w')), 'w')     # 内框宽上限(原 640pt;
#   注: 原值 640pt 比 wz6 页宽 595.3pt 还大 -> 该上界在 wz6 上**从未生效**, 相对化后同样不生效)
V_GRID_P_LO = _sc_pt(_envfrac('VERT_GRID_P_LO_FRAC', _fp(40.0, 'w')), 'w')   # 栅格枚举列距下限(原 40pt)
V_GRID_P_HI = _sc_pt(_envfrac('VERT_GRID_P_HI_FRAC', _fp(48.0, 'w')), 'w')   #   上限(原 48pt)
V_GRID_SPAN_LO = _sc_pt(_envfrac('VERT_GRID_SPAN_LO_FRAC', _fp(400.0, 'w')), 'w')  # 13 线窗跨度下限(原 400pt)
V_GRID_SPAN_HI = _sc_pt(_envfrac('VERT_GRID_SPAN_HI_FRAC', _fp(640.0, 'w')), 'w')  #   上限(原 640pt, 同 V_INW_HI 未生效)
V_GRID_P_REF_LO = _sc_pt(_envfrac('VERT_GRID_P_REF_LO_FRAC', _fp(35.0, 'w')), 'w')  # 精修列距夹取(原 35pt)
V_GRID_P_REF_HI = _sc_pt(_envfrac('VERT_GRID_P_REF_HI_FRAC', _fp(52.0, 'w')), 'w')  #   上限(原 52pt)
V_PITCH_MIN = _sc_pt(_envfrac('VERT_PITCH_MIN_FRAC', _fp(8.0, 'w')), 'w')     # 「列距有效」下限(原 8pt)
V_P_LO = _sc_pt(_envfrac('VERT_P_LO_FRAC', _fp(36.0, 'w')), 'w')     # _grid_from_bands 列距窗(原 36pt)
V_P_HI = _sc_pt(_envfrac('VERT_P_HI_FRAC', _fp(50.0, 'w')), 'w')     #   上限(原 50pt)
V_BAND_SP_LO = _sc_pt(_envfrac('VERT_BAND_SP_LO_FRAC', _fp(20.0, 'w')), 'w')   # 列带中心间距窗(原 20pt)
V_BAND_SP_HI = _sc_pt(_envfrac('VERT_BAND_SP_HI_FRAC', _fp(100.0, 'w')), 'w')  #   上限(原 100pt)
# 线宽判据(粗细分界 + 外粗线缺测兜底): 原为 wz6 实测常数(2.4/6.5pt, 兜底 3.2/3.4pt) ——
#   本轮改由 §1.954 从**实测线宽分布**自定(见该节); 这里的值 = **兜底/对账基准**。
V_THICK_MIN = 2.4      # 粗线判据(pt, 兜底; §1.954 标定覆盖)
V_THICK_MAX = 6.5      # 粗线上限(pt): 源书外框线 2.5-4.5pt; 更厚的多是扫描黑边残条(8-17pt)
V_FRAME_GAP = float(os.environ.get('VERT_FRAME_GAP') or 3.2)   # 兜底值(wz6 实测): 仅当该侧外粗线缺测时补位用
V_FRAME_TH = float(os.environ.get('VERT_FRAME_TH') or 3.4)     # 兜底值(wz6 实测): 仅当外粗线缺测时补位用
# 注: 这两项是「缺测补位」而非书常数 —— 有实测(外粗线/横线端头)时一律用实测值, 见 frame_geom ③。
#   别的书若外框线更粗/更细且页页都缺测(如订口侧被裁切), 才需要 env 覆盖(§1.954 兜底也会按实测线宽重定)。
JIE_LOG = os.environ.get('VERT_JIE_LOG', '0') not in ('0', 'false', 'False')   # 界行线调试日志
FDBG = os.environ.get('VERT_FRAME_DEBUG', '0') not in ('0', 'false', 'False')  # 版框检测诊断日志
N_COL_FRAME = int(os.environ.get('VERT_NCOL_FRAME') or 12)   # 版框内框列数; 12 = 兜底值(wz6 实测), §1.955 标定覆盖

def _runs(mask, gap=2):
    """布尔序列 -> 连续 True 段 [[start, end], ...](gap = 允许间断的像素数)"""
    out = []
    for i, v in enumerate(mask):
        if not v: continue
        if out and i - out[-1][1] <= gap: out[-1][1] = i
        else: out.append([i, i])
    return out

def _grid_fit(ls):
    """淡界行线栅格拟合(§1.95b 兜底): 候选细线 -> 13 条等距线(= 12 格版框, 界行线即格线)。
    为什么不直接信候选: 低阈值扫描会把正文列竖笔画也算成细线(实测 p32 阈值 0.30 的 12 条候选里
    5 条是碎片), 碎片多到能把「相邻差中位」带偏 -> 单阈值 + 中位列距都不成立。做法:
      ① 枚举 (列距 p ∈ V_GRID_P_LO-HI, 某条候选所在栅格) 下所有跨 13 条线的窗口(相对量, §1.95);
      ② 打分 = (命中候选数, 窗口各线的墨覆盖率之和) —— 命中数优先, 覆盖率解平手: 实测 p22 最左
         一条线淡到漏检时, 栅格可整体右移一格而命中数不变, 但右移后最右那条落在版框外空白上
         (覆盖率 ~0), 靠覆盖率判回正确位置;
      ③ 对命中集合最小二乘精修 p/首线 -> 生成 13 条线(漏检的按栅格位置补, 墨迹参数取中位)。
    返回 (13 条线列表, (首线, 末线)) 或 ([], None)。"""
    if len(ls) < 6: return [], None
    cs = []
    for g in sorted(ls, key=lambda g: g[0]):
        if cs and g[0] - cs[-1] < 4: continue          # 同一条线的碎片并掉
        cs.append(g[0])
    if len(cs) < 6: return [], None
    def cov_at(x):
        c = 0.0
        for g in ls:
            if g[0] - 1.0 <= x <= g[1] + 1.0 and g[3] > c: c = g[3]
        return c
    best = None
    _n_p = 21                                          # 列距枚举: V_GRID_P_LO-HI 等分 21 档(原 40.0-48.0pt 步进 0.4)
    for _i in range(_n_p):
        p = V_GRID_P_LO + (V_GRID_P_HI - V_GRID_P_LO) * _i / (_n_p - 1.0)
        for a in cs:
            g0 = a - p * int(a / p)                    # 含 a 的栅格, 首线在 [0,p)
            n_w = int((cs[-1] + 1.5 * p - g0) / p) + 1
            pos = [g0 + m * p for m in range(n_w)]
            for s in range(0, len(pos) - 12):
                win = pos[s:s + 13]
                if not (V_GRID_SPAN_LO <= win[-1] - win[0] <= V_GRID_SPAN_HI): continue
                hits = 0; csum = 0.0
                for x in win:
                    for c in cs:
                        if abs(c - x) <= 0.2 * p:
                            hits += 1; break
                    csum += cov_at(x)
                sc = (hits, round(csum, 2))
                if best is None or sc > best[0]: best = (sc, p, win)
    if best is None or best[0][0] < 8: return [], None
    _, p, win = best
    hits = []
    for k, x in enumerate(win):                        # 窗口内每条线的最近候选
        c = min(cs, key=lambda v: abs(v - x))
        if abs(c - x) <= 0.2 * p: hits.append((k, c))
    n = len(hits)
    if n >= 4:
        mm = sum(h[0] for h in hits) / n; mx = sum(h[1] for h in hits) / n
        var = sum((h[0] - mm) ** 2 for h in hits)
        if var > 1e-6:
            p2 = sum((h[0] - mm) * (h[1] - mx) for h in hits) / var
            if V_GRID_P_REF_LO <= p2 <= V_GRID_P_REF_HI:
                p = p2; win[0] = mx - p * mm           # 精修: 以首线为基准
    pos = [win[0] + k * p for k in range(13)]
    if not (V_GRID_SPAN_LO <= pos[-1] - pos[0] <= V_GRID_SPAN_HI): return [], None
    covs = sorted(g[3] for g in ls); tops = sorted(g[4] for g in ls); bots = sorted(g[5] for g in ls)
    out = []
    for k, x in enumerate(pos):
        c = min(ls, key=lambda g: abs(g[0] - x))
        if abs(c[0] - x) <= 0.2 * p:
            out.append((x - 0.5, x + 0.5, c[2], c[3], c[4], c[5]))
        else:
            out.append((x - 0.5, x + 0.5, 1.0, covs[len(covs) // 2],
                        tops[len(tops) // 2], bots[len(bots) // 2]))
    return out, (pos[0], pos[-1])

def _bar_px(ink):
    """扫描背景黑边(装订/页边)宽度 px: 两端往内「累计墨占比 > 0.9」的最大宽度。
    不 break(要求前缀全 > 0.9) —— 黑边最外一列常被扫描边缘混色拉灰(实测 0.94>0.9>0.6), 一 break 就漏检。"""
    W = ink.shape[1]; cc = ink.mean(axis=0); bl = br = 0
    for k in range(1, W // 3 + 1):
        if cc[:k].mean() > 0.80: bl = k
    for k in range(1, W // 3 + 1):
        if cc[W - k:].mean() > 0.80: br = k
    return bl, br

def frame_geom(pi, wstat=None):
    """单页版框实测(pt, 页顶向下) -> dict 或 None(封面/插页等无版框页返回 None)。
    key: in_l/in_r/in_t/in_b 内框(pt); out_l/out_r/out_t/out_b 外粗线(缺测为 None);
         thin[] 内框内所有细竖线 x 中心(含内框左右线); hx_l/hx_r 横线 x 跨度。
    wstat: 给了则把本页实测的「竖线组厚度 / 横线组厚度」(pt)追加进去(§1.954 线宽分布标定用)。"""
    import numpy as np
    a = src_gray(pi); H, W = a.shape
    ink = a < 150
    bl, br = _bar_px(ink)
    xa, xb = bl, W - br
    # 1) 横线: 有效纸面内行墨占比 > V_H_COV 的细组(源书横线会断线/发灰: cov 低到 0.58, 而正文行 <=0.30);
    #    再要求墨迹横跨 >0.55 纸宽(挡书眉/页码/装饰行)
    hg = []
    for y0, y1 in _runs(ink[:, xa:xb].mean(axis=1) > V_H_COV, 3):
        if (y1 - y0 + 1) > 24: continue
        xs = np.where(ink[y0:y1 + 1, xa:xb].any(axis=0))[0]
        if len(xs) == 0 or (xs[-1] - xs[0]) < 0.55 * (xb - xa): continue
        hg.append((y0, y1))
    if wstat is not None:
        wstat['h'].extend((g[1] - g[0] + 1) / 2.0 for g in hg)
    if len(hg) < 2:
        if FDBG: print('    [版框跳过] p%d 横线组不足 (%d 条, xa%d xb%d)' % (pi + 1, len(hg), xa, xb))
        return None
    # 2) 上下各取一对(外粗/内细): 同一端 7.5pt 内相邻两组配对, 厚者为外
    def pick_pair(groups, from_top):
        gs = sorted(groups, key=lambda g: g[0], reverse=not from_top)
        if not gs: return None, None
        g0 = gs[0]
        g1 = next((g for g in gs[1:] if abs(g[0] - g0[1]) <= 15 or abs(g0[0] - g[1]) <= 15), None)
        if g1 is not None:
            grp = sorted([g0, g1], key=lambda g: g[0])
            if (grp[0][1] - grp[0][0]) < (grp[1][1] - grp[1][0]): grp.reverse()
            return grp[0], grp[1]          # (外, 内)
        return (g0, None) if (g0[1] - g0[0]) + 1 >= 2 * V_THICK_MIN else (None, g0)
    top_grp = [g for g in hg if g[0] < H * 0.45]; bot_grp = [g for g in hg if g[0] > H * 0.55]
    if not top_grp or not bot_grp:
        if FDBG: print('    [版框跳过] p%d 上下横线带缺 (top%d bot%d)' % (pi + 1, len(top_grp), len(bot_grp)))
        return None
    out_t, in_t = pick_pair(top_grp, True)
    out_b, in_b = pick_pair(bot_grp, False)
    if out_t is None and in_t is None: return None
    if out_b is None and in_b is None: return None
    if in_t is None: in_t = (out_t[1] + 7, out_t[1] + 9)
    if in_b is None: in_b = (out_b[0] - 9, out_b[0] - 7)
    if out_t is None: out_t = (in_t[0] - 9, in_t[0] - 6)
    if out_b is None: out_b = (in_b[1] + 6, in_b[1] + 9)
    it, ib = in_t[1] / 2.0, in_b[0] / 2.0                        # 内框上下缘(pt)
    if not (V_INH_LO <= ib - it <= V_INH_HI):
        if FDBG: print('    [版框跳过] p%d 内框高异常 %.1f' % (pi + 1, ib - it))
        return None
    # 3) 竖线(内框 y 区间内); 剔除贴纸边假线(扫描裁切边缘的暗边: 实测 p172/p210 在页缘 1-3pt 处
    #    有 cov 0.55-0.75 的假竖线) —— 源书版框线离页缘最近也有 ~10pt。
    yb0, yb1 = int(max(0, it * 2 + 6)), int(min(H, ib * 2 - 6))
    colc = ink[yb0:yb1, xa:xb].mean(axis=0)
    # 注: 曾试过加「最长连续墨段」辅助判据(界行线连段长、文字列短)想救 p22/p32/p36 这类淡页
    #   (界行线覆盖率只有 0.35-0.49), 实测反而把正常页 20+ 条界行线判掉(连段被边注/书眉切断) 且没救回淡页
    #   -> 撤回, 只用覆盖率。p22/p32/p36 三页界行线太淡, 现有判据检不出, 该页不画版框(遗留)。
    def scan_v(thr):
        """列墨占比 > thr 的组 -> vg 项(pt): (左缘, 右缘, 厚, 覆盖率, 墨迹上端, 墨迹下端)"""
        out = []
        for x0, x1 in _runs(colc > thr, 2):
            cx = (xa + x0 + xa + x1 + 1) / 4.0
            if cx < xa / 2.0 + 5 or cx > xb / 2.0 - 5: continue
            m = ink[yb0:yb1, xa + x0:xa + x1 + 1].any(axis=1); ys = np.where(m)[0]
            out.append(((xa + x0) / 2.0, (xa + x1 + 1) / 2.0, (x1 - x0 + 1) / 2.0,
                        float(colc[x0:x1 + 1].mean()), (yb0 + ys[0]) / 2.0, (yb0 + ys[-1] + 1) / 2.0))
        return out
    vg = scan_v(V_LINE_COV)
    if wstat is not None:
        wstat['v'].extend(g[2] for g in vg)          # 竖线组厚度(pt) -> §1.954 线宽分布
    if FDBG: print('    [版框诊断] p%d 列覆盖>%.2f 命中 %d 组' % (
        pi + 1, V_LINE_COV, len(vg)))
    thin = [g for g in vg if g[2] <= V_THICK_MIN]
    grid_ends = None                                   # 兜底命中时 = 栅格链首末线(即内框左右线)
    if len(thin) < 6 and V_LINE_COV_LO < V_LINE_COV:
        # §1.95b 淡界行线兜底: 实测 p22/p32/p36 三页界行线墨色很淡(覆盖率 0.35-0.49), 主阈值 0.55
        #   检不出 -> 该页无版框(连带「列距按内框宽封顶」失效, p36 13 列伸到页左外)。低阈值重扫后
        #   「等距栅格」剔碎片: 界行线是 43.4pt 等距栅格(12 格 13 条), 正文列碎片不在栅格上。
        lo = [g for g in scan_v(V_LINE_COV_LO) if g[2] <= V_THICK_MIN]
        gd, gends = _grid_fit(lo)
        if FDBG: print('    [版框兜底诊断] p%d 低阈值%.2f 细线%d条 x=%s -> 链%d条 %s' % (
            pi + 1, V_LINE_COV_LO, len(lo), [round(g[0], 1) for g in lo],
            len(gd), [round(g[0], 1) for g in gd]))
        if len(gd) >= 6:
            thin = gd; grid_ends = gends
            print('    [版框兜底] p%d 淡线: 阈值%.2f 细线%d条 -> 栅格链%d条 (x%.1f-%.1f)' % (
                pi + 1, V_LINE_COV_LO, len(lo), len(gd), gd[0][0], gd[-1][1]))
    # 外粗线候选 = 厚度在「单条框线」量级的粗组(2.4-12pt); 更厚的(扫描黑边 8-17pt)剔除
    thick = [g for g in vg if V_THICK_MIN < g[2] <= V_THICK_MAX]
    if len(thin) < 6:
        if FDBG: print('    [版框跳过] p%d 细竖线不足 %d 条 (xa%d xb%d it%.1f ib%.1f 粗%d)' % (
            pi + 1, len(thin), xa, xb, it, ib, len(thick)))
        return None
    # 横线 x 跨度 = 顶部(外+内)两组在该 y 带内的墨迹 x 范围(源书横线横跨整幅纸面, 含订口页边)
    def xspan(g1, g2):
        sub = ink[min(g1[0], g2[0]):max(g1[1], g2[1]) + 1, xa:xb]
        xs = np.where(sub.any(axis=0))[0]
        return (xa + xs[0]) / 2.0, (xa + xs[-1] + 1) / 2.0
    hx_l, hx_r = xspan(out_t, in_t)
    if hx_r - hx_l < 100: hx_l, hx_r = xspan(out_b, in_b)
    # 列距(细线相邻间隔中位)—— 用来判「跨度是否整数倍列距」以及外粗线是否真属本页版框
    cxs = [(g[0] + g[1]) / 2.0 for g in thin]
    dlt = [b - a for a, b in zip(cxs, cxs[1:]) if b - a > 1]
    pitch = statistics.median(dlt) if dlt else 0.0
    # 4) 内框左右线(结构约束闭合, 三级优先):
    #    a) 外粗线(装订侧没有, 但两侧不会同时缺——见全书盘点)内侧缘 ± 间隙 = 该侧内线;
    #    b) 该侧无粗线时看横线端头: 横线在纸面内收尾 -> 端头 - 粗线厚 - 间隙 = 内线;
    #    c) 兜底用实测最外细线(界行线/框线本身)。
    pw_pt = (W - br) / 2.0; pl_pt = bl / 2.0
    out_l = min([g for g in thick if g[0] < cxs[0]], key=lambda g: cxs[0] - g[1], default=None)
    out_r = min([g for g in thick if g[1] > cxs[-1]], key=lambda g: g[0] - cxs[-1], default=None)
    if out_l is not None and cxs[0] - out_l[1] > 1.2 * pitch: out_l = None
    if out_r is not None and out_r[0] - cxs[-1] > 1.2 * pitch: out_r = None
    il, ir = thin[0][0], thin[-1][1]
    if out_l is not None: il = round(out_l[1] + V_FRAME_GAP, 1)
    elif hx_l > pl_pt + 8: il = round(min(il, hx_l - V_FRAME_TH - V_FRAME_GAP), 1)
    if out_r is not None: ir = round(out_r[0] - V_FRAME_GAP, 1)
    elif hx_r < pw_pt - 8: ir = round(max(ir, hx_r - V_FRAME_TH - V_FRAME_GAP), 1)
    # 5) 装订侧内框线太淡漏检(实测 p115/p191 等): 版框是印版常数, 用「列数 × 列距」从未漏检的一侧补;
    #    实测值与结构估值差 < 半列时优先用实测(每页扫描错位 ±5pt, 实测更贴源书)。
    if pitch > V_PITCH_MIN:
        if out_r is not None and abs((ir - N_COL_FRAME * pitch) - il) > 0.5 * pitch:
            il = round(ir - N_COL_FRAME * pitch, 1)
        if out_l is not None and abs((il + N_COL_FRAME * pitch) - ir) > 0.5 * pitch:
            ir = round(il + N_COL_FRAME * pitch, 1)
    # 栅格兜底命中时: 链首末线就是内框左右线(12 格 = 13 条, 首末即框线), 比上面「横线端头」估值可靠
    #   —— 源书横线横跨整幅纸面(含订口页边), 端头不是框线位置(p36 实测会把右线高估 26pt)。
    if grid_ends is not None: il, ir = round(grid_ends[0], 1), round(grid_ends[1], 1)
    if not (V_INW_LO <= ir - il <= V_INW_HI):
        if FDBG: print('    [版框跳过] p%d 内框宽异常 %.1f (il%.1f ir%.1f)' % (pi + 1, ir - il, il, ir))
        return None
    if pitch > V_PITCH_MIN and abs((ir - il) / pitch - round((ir - il) / pitch)) > 0.22:
        if FDBG: print('    [版框跳过] p%d 跨度非整数倍列距 %.2f (pitch %.1f)' % (pi + 1, (ir - il) / pitch, pitch))
        return None
    jie = [g[0] for g in thin if il - 2 <= g[0] <= ir + 2]      # 界行线(含内框左右线, 绘制时去首末)
    if JIE_LOG: print('    [界行线] p%d pitch %.1f 跨度 %.1f = %.2f 列, 细线 %d 条' % (
        pi + 1, pitch, ir - il, (ir - il) / pitch if pitch else 0, len(jie)))
    return {'in_l': il, 'in_r': ir, 'in_t': it, 'in_b': ib,
            'in_th': (in_t[1] - in_t[0]) / 2.0, 'ib_th': (in_b[1] - in_b[0]) / 2.0,
            'out_t': out_t[0] / 2.0, 'out_t_th': (out_t[1] - out_t[0]) / 2.0,
            'out_b': out_b[1] / 2.0, 'out_b_th': (out_b[1] - out_b[0]) / 2.0,
            'out_l': out_l[0] if out_l else None, 'out_l_th': out_l[2] if out_l else V_FRAME_TH,
            'out_r': out_r[1] if out_r else None, 'out_r_th': out_r[2] if out_r else V_FRAME_TH,
            'thin': jie, 'pitch': pitch, 'hx_l': hx_l, 'hx_r': hx_r,
            'bar': (bl / 2.0, br / 2.0)}

def frame_tex(pi, gm=None):
    """版框线 tex: 内框 4 边(细) + 外框粗线(有实测才画: 订口侧被装订边吞掉则不画) + 界行线。
    gm: §1.98 框驱动路径给的已校正版框(in_l/in_r 用墨迹列带栅格校正过), 缺省现算。"""
    g = frame_geom(pi) if gm is None else gm
    if not g: return []
    if g.get('virtual'):
        return []          # §1.975 无版框书: 伪版心不是印出来的 -> **不凭空画**外框/内框/界行线
    puts = []
    def hl(x0, x1, ytop, th):
        puts.append(r'\put(%.1f,%.1f){\rule{%.2fpt}{%.2fpt}}' % (x0, page_h - ytop - th, x1 - x0, th))
    def vl(x0, ytop, ybot, th):
        puts.append(r'\put(%.1f,%.1f){\rule{%.2fpt}{%.2fpt}}' % (x0, page_h - ybot, th, ybot - ytop))
    hl(g['hx_l'], g['hx_r'], g['out_t'], g['out_t_th'])       # 上外
    hl(g['hx_l'], g['hx_r'], g['in_t'] - g['in_th'], g['in_th'])   # 上内
    hl(g['hx_l'], g['hx_r'], g['in_b'], g['in_th'])           # 下内
    hl(g['hx_l'], g['hx_r'], g['out_b'], g['out_b_th'])       # 下外
    vl(g['in_l'] - g['in_th'], g['in_t'], g['in_b'], g['in_th'])   # 左内
    vl(g['in_r'], g['in_t'], g['in_b'], g['in_th'])           # 右内
    if g['out_l'] is not None: vl(g['out_l'], g['in_t'], g['in_b'], g['out_l_th'])
    if g['out_r'] is not None: vl(g['out_r'] - g['out_r_th'], g['in_t'], g['in_b'], g['out_r_th'])
    n_jie = 0
    for x in g['thin']:                                        # 界行线(内框左右线已单独画)
        if not (g['in_l'] + 2 < x < g['in_r'] - 2): continue
        vl(x, g['in_t'], g['in_b'], 0.8); n_jie += 1
    print('  [版框] p%d 内框 x%.1f-%.1f y%.1f-%.1f 外粗 L%s/R%s 界行线%d 横线x%.1f-%.1f %s' % (
        pi + 1, g['in_l'], g['in_r'], g['in_t'], g['in_b'],
        ('%.1fpt' % g['out_l_th']) if g['out_l'] is not None else '缺(订口侧)',
        ('%.1fpt' % g['out_r_th']) if g['out_r'] is not None else '缺(订口侧)',
        n_jie, g['hx_l'], g['hx_r'],
        ('扫描黑边 L%.1f/R%.1f' % g['bar']) if (g['bar'][0] or g['bar'][1]) else ''))
    return ['\\AddToShipoutPictureFG*{%\n  ' + '%\n  '.join(puts) + '}']

# ---------- 1.954) 版框线粗细判据自标定(taskN 纸型无关化) ----------
# 原常数 V_THICK_MIN=2.4 / V_THICK_MAX=6.5pt 是 wz6 实测(界行线/内框线 0.5-1.5pt, 外粗线 3.5-4.5pt,
#   更厚的多是扫描黑边残条 8-17pt)。别的书线更粗/更细 -> 细线被当粗线(内框缘错)或粗线被当细线(界行线错)。
# 做法: 抽样页扫竖线组厚度 + 横线组厚度(同一套墨占比阈值), 从**实测分布**定分界:
#   ① 在竖线组厚度(半整数 pt)里找「最大间隙」把样本分成细/粗两簇(两簇各 >= 3 条);
#   ② V_THICK_MIN = 0.7 x 粗簇下缘 —— 落在「细簇上缘 .. 粗簇下缘」之间且偏粗侧(细线误判成粗线的
#      代价更大: 粗线候选用来定内框缘); 实测 wz6: 细簇 0.5-1.5 / 粗簇 3.5-4.5 -> 0.7x3.5 = 2.45
#      (原常数 2.4; 厚度只能是半整数, 故 2.45 与 2.4 分类**完全等价**, 见报告对账表);
#   ③ V_THICK_MAX = 1.5 x 粗簇上缘(竖线组与横线组合并取 —— 同一条外框线两个方向同宽), 挡更厚的
#      黑边残条; 实测 wz6: 粗簇上缘 4.5 -> 6.75(原 6.5, 半整数下同样等价);
#   ④ 样本不足(无版框书, wz7 类)/无有效间隙 -> 保留兜底 (2.4, 6.5), 日志明示"未标定"。
#   V_FRAME_GAP/TH(3.2/3.4pt) 是「外粗线缺测时的补位值」, 不是书常数 -> 保留兜底, 可用 env 覆盖。
CALIB_N_PAGE = int(os.environ.get('VERT_CALIB_PAGES') or 16)   # 标定抽样页数(§1.954/§1.955/§1.956 共用)
CALIB_T0 = __import__('time').time()                           # 标定趟计时(日志打印)
THICK_SAMPLE = int(os.environ.get('VERT_THICK_SAMPLE') or 8)   # 线宽标定抽样页数
CALIB_T954 = os.environ.get('VERT_THICK_CALIB', '1') not in ('0', 'false', 'False')

def _calib_line_widths(vws, hws):
    """实测线宽样本(竖线组厚度 / 横线组厚度, pt) -> (V_THICK_MIN, V_THICK_MAX, 依据)。
    样本不足或无有效间隙 -> 返回 (None, None, 原因) 由调用方保留兜底值。"""
    vs = sorted(vws)
    if len(vs) < 6:
        return None, None, '竖线组样本 %d 条(需 >=6)' % len(vs)
    uniq = sorted(set(vs))
    best = None
    for a, b in zip(uniq, uniq[1:]):
        lo = sum(1 for x in vs if x <= a); hi = sum(1 for x in vs if x >= b)
        if lo < 3 or hi < 3: continue
        if best is None or (b - a) > best[0]: best = (b - a, a, b)
    if best is None:
        return None, None, '厚度分布无有效两簇间隙'
    _, thin_hi, thick_lo = best
    thick_hi = max(max(vs), max(hws)) if hws else max(vs)
    return (round(0.7 * thick_lo, 3), round(1.5 * thick_hi, 3),
            '细簇上缘 %.2f / 粗簇 %.2f-%.2f (%d 条 vs %d 条)' % (
                thin_hi, thick_lo, thick_hi,
                sum(1 for x in vs if x <= thin_hi), sum(1 for x in vs if x >= thick_lo)))

# 标定抽样页(1-based, 全书均布): §1.954 线宽 / §1.955 列数 / §1.956 源图侧统计共用同一批页
CALIB_SAMP = sorted(set(list(range(1, len(keys) + 1, max(1, len(keys) // CALIB_N_PAGE)))[:CALIB_N_PAGE]))
if SRC and CALIB_T954 and os.environ.get('VERT_THICK_MIN') is None:
    _wst = {'v': [], 'h': []}
    _nws = 0
    for _pg in CALIB_SAMP[:max(1, THICK_SAMPLE)]:
        if frame_geom(_pg - 1, wstat=_wst) is not None: _nws += 1
    _tmin, _tmax, _why = _calib_line_widths(_wst['v'], _wst['h'])
    if _tmin:
        print('[标定·线宽] 抽 %d 页(有版框 %d): %s -> V_THICK_MIN %.2f V_THICK_MAX %.2f (兜底 %.1f/%.1f)' % (
            min(THICK_SAMPLE, len(CALIB_SAMP)), _nws, _why, _tmin, _tmax, V_THICK_MIN, V_THICK_MAX))
        V_THICK_MIN, V_THICK_MAX = _tmin, _tmax
    else:
        print('[标定·线宽] 未标定(%s) -> 用兜底 V_THICK_MIN %.2f V_THICK_MAX %.2f' % (
            _why, V_THICK_MIN, V_THICK_MAX))
elif os.environ.get('VERT_THICK_MIN') is not None:
    V_THICK_MIN = float(os.environ['VERT_THICK_MIN'])
    V_THICK_MAX = float(os.environ.get('VERT_THICK_MAX') or V_THICK_MAX)
    print('[标定·线宽] 显式 VERT_THICK_MIN/MAX=%.2f/%.2f 优先(跳过标定)' % (V_THICK_MIN, V_THICK_MAX))
else:
    print('[标定·线宽] 无源 PDF -> 用兜底 V_THICK_MIN %.2f V_THICK_MAX %.2f(不标定)' % (
        V_THICK_MIN, V_THICK_MAX))

# ---------- 1.955) 标定趟 A: 版框列数 N_COL_FRAME(taskM) ----------
# 背景(taskM 审计): N_COL_FRAME=12 原是 wz6 印刷版框的常数(12 列 x 43.4pt)。别的书列数不同 ->
#   L1001-1004 用「内框宽 = 列数 x 列距」补漏检侧的框线, 列数错 -> 内框左右缘错 -> 列位整体错位;
#   §1.98 槽格(page_metrics 的 n)与 _grid_from_bands 的 n 同样依赖它。
# 标定(实测优先, 12 仅兜底): 抽样页逐页做三条**互相独立**的估计 ——
#   ① 内框宽 ÷ 列距(取整; 内框已由 frame_geom 结构式收敛, 对漏检侧不敏感)
#   ② 界行线条数 - 1(数细竖线; 源书自身缺线时 ±1, 故取众数)
#   ③ 实测最外两条细线的跨距 ÷ 列距(只用实测线, 不受待标定值影响 —— 标定要独立于被标定量)
#   取「①=③ 一致」的页的众数(两条独立口径互证); 无一致页则退 ② 众数; 都不可测 -> 兜底 12。
#   显式 VERT_NCOL_FRAME 优先于标定值。

def _calib_ncol_page(g, pmin=8.0):
    """单页列数估计 -> (n①, n②, n③) 或 None(该页不可测: 无版框/列距异常/细线太少)。
    pmin: 「列距有效」下限(pt); 默认 8.0 = wz6 兜底, 调用处传相对量 V_PITCH_MIN(§1.95)。"""
    if not g:
        return None
    p = g.get('pitch') or 0.0
    thin = g.get('thin') or []
    if p <= pmin or len(thin) < 6:
        return None
    n1 = int(round((g['in_r'] - g['in_l']) / p))
    n2 = len(thin) - 1
    n3 = int(round((thin[-1] - thin[0]) / p))
    if not (4 <= n1 <= 40 and 4 <= n2 <= 40 and 4 <= n3 <= 40):
        return None
    return (n1, n2, n3)

def _calib_ncol_pick(triples):
    """逐页估计 -> (列数 或 None, 依据字符串)。"""
    if not triples:
        return None, '无可用页'
    def mode(vs):
        c = {}
        for v in vs:
            c[v] = c.get(v, 0) + 1
        return sorted(c, key=lambda k: (-c[k], k))[0], max(c.values())
    both = [a for a, _b, c in triples if a == c]
    if both:
        n, cnt = mode(both)
        return n, '①=③ %d/%d 页一致(众数 %d, 各页 %s)' % (
            len(both), len(triples), n, [t[0] for t in triples])
    n, cnt = mode([b for _a, b, _c in triples])
    return n, '①=③ 无一致页, 退 ②线条数-1 众数 %d(%d/%d 页)' % (n, cnt, len(triples))

# 标定抽样页 CALIB_SAMP 见 §1.954(§1.954/§1.955/§1.956 共用同一批页)
_fr_samp = []                                     # 抽样页的实测版框(§1.96a 内框缘基准 + 列数标定共用一个循环)
if SRC:
    _nc_tri = []
    for _pg in CALIB_SAMP:
        _g = frame_geom(_pg - 1)
        if _g: _fr_samp.append(_g)
        _t = _calib_ncol_page(_g, V_PITCH_MIN)
        if _t:
            _nc_tri.append(_t)
    if os.environ.get('VERT_NCOL_FRAME') is None:
        _nc_new, _nc_why = _calib_ncol_pick(_nc_tri)
        if _nc_new:
            print('[标定A] 版框列数: 抽样 %d 页测到 %d 页 -> %d (兜底 12; %s)' % (
                len(CALIB_SAMP), len(_nc_tri), _nc_new, _nc_why))
            N_COL_FRAME = _nc_new
        else:
            print('[标定A] 版框列数: 实测不可用(%s) -> 用兜底 %d' % (_nc_why, N_COL_FRAME))
    else:
        print('[标定A] 版框列数: 显式 VERT_NCOL_FRAME=%d 优先(跳过标定)' % N_COL_FRAME)
elif os.environ.get('VERT_NCOL_FRAME') is not None:
    print('[标定A] 版框列数: 显式 VERT_NCOL_FRAME=%d 优先(跳过标定)' % N_COL_FRAME)
else:
    print('[标定A] 版框列数: 无源 PDF -> 用兜底 %d(不标定)' % N_COL_FRAME)

# ---------- 1.96a) 页边带并上「内框缘」(纸型无关化 taskN) ----------
# 书眉/页码的语义是「在**版心右缘之外**(订口侧页边内)」, 左边注是「在版心左缘之外」。§0.5 的
#   页宽比例带是**无内框书**的退化口径; 有实测内框时两者取并集 —— 判据是「框外 **或** 页边带内」,
#   故门限取更靠内的那一侧:
#     右: x0 > min(页宽比例带, 内框右缘)   左: x1 < max(页宽比例带, 内框左缘)
#   内框基准 = §1.955 抽样页(16 页均布)实测内框缘的中位(pt -> px x2), 零额外开销。
#   wz6 实测: 内框右缘中位 1116px > 页宽比例带 1100px、左缘中位 73px < 100px -> **两翼都不生效**
#     (分类与产物 tex 逐字节不变); 别的书若版心更宽(右缘更靠右), 右带自动外扩到框缘, 避免框外
#     的书眉/页码漏检; 无版框书(wz7 类) _fr_samp 为空 -> 纯页幅比例, 不误检。
FRAME_REF = None
if _fr_samp:
    FRAME_REF = {'in_l': statistics.median(g['in_l'] for g in _fr_samp),
                 'in_r': statistics.median(g['in_r'] for g in _fr_samp),
                 'pitch': statistics.median(g['pitch'] for g in _fr_samp),
                 'n_page': len(_fr_samp)}
    _br0, _bl0 = BAND_R_PX, BAND_L_PX
    BAND_R_PX, BAND_L_PX = _band_union(BAND_R_PX, BAND_L_PX, FRAME_REF['in_l'], FRAME_REF['in_r'])
    print('[边带基准] 内框(抽 %d 页中位): 左缘 %.1fpt 右缘 %.1fpt 列距 %.2fpt -> 页边带 右%.1f 左%.1f px '
          '(页幅比例带 %.1f/%.1f; %s)' % (
              FRAME_REF['n_page'], FRAME_REF['in_l'], FRAME_REF['in_r'], FRAME_REF['pitch'],
              BAND_R_PX, BAND_L_PX, _br0, _bl0,
              '并用内框缘(框外口径)' if (BAND_R_PX != _br0 or BAND_L_PX != _bl0) else '与页幅比例带相同'))
else:
    print('[边带基准] 无实测版框(抽样 %d 页) -> 页边带只用页幅比例: 右%.1f 左%.1f px' % (
        len(CALIB_SAMP), BAND_R_PX, BAND_L_PX))

# ---------- 1.96) 版心右缘用源图墨迹复测(修 OCR 边缘列 bbox 右扩) ----------
# 现象(实测 tmp_vert/right_fit.py): OCR 对「最右一列」的 bbox 系统性右扩 14-30pt(夹进版框右线/书眉
#   页码带/扫描黑边), 逐页 max(正文列 x1) 中位 1164px 而 p90 1183px、max 1189px(= 扫描黑边右缘)。
#   旧拟合 RIGHT = max(所有页所有正文列 x1) = 1189.8px = 594.9pt, 比版心真右缘(抽样页内框右线中位
#   563.1pt; 单页实例 p4 = 546.0pt)偏右 ~32pt ->
#   后果: 每页第一列被画到版框之外(落进书眉/页码带)。修法: 版心右缘 = 版框内最右一条细竖线
#   (源图墨迹实测, 抽样页中位; 源书正文列墨迹右缘正落在该线上, 实测 p4 列墨右缘 544.5 vs 线 545.5)。
RIGHT_INK = os.environ.get('VERT_RIGHT_INK', '1') not in ('0', 'false', 'False') and src_doc is not None
if RIGHT_INK:
    step = max(1, len(keys) // 12)
    samp = list(range(1, len(keys) + 1, step))
    rs = []
    for pg in samp:
        g = frame_geom(pg - 1)
        if g: rs.append(g['in_r'])
    if rs:
        r_new = round(statistics.median(rs), 1)
        print('[版心右缘] OCR 拟合 %.1f -> 源图墨迹实测 %.1f pt (抽 %d 页版框内右线中位)' % (
            RIGHT_p, r_new, len(rs)))
        RIGHT_p = r_new
        OM_pt = round(RIGHT_p - TH_pt - 70, 1)

# ---------- 1.97) OCR 旋转坐标系页修正 ----------
# 现象(实测 p159 / key "158"): 该页源书是竖排(版框内 4 列小字), 但 OCR 服务把整页当横排识别,
#   返回的坐标落在「页逆时针转 90°」的坐标系里 —— 行框宽 1833px 高 47px(横看; 竖排正文列必是
#   纵长, 高/宽 ~20), 页宽方向的值最大 2411px 远超页宽 1191px(= 2x 595.3pt)。
#   后果: 6 行全部过不了 is_body_col(h<300) 被丢弃 -> 重建 PDF 该页整页空白。
# 印证: 按逆时针 90° 还原后, 行框正落在源图墨迹字列上(残差 ~2px), 且行文连读通顺
#   (…乘機反攻拿 | 破崙軍僅剩…逃去 | …繩捆索綁形同 | 囚犯略為…代替)。
# 判据: 页内「横看」行(宽>300px 且 >2.5x高) >= 3 条, 且所有长行(宽>300px)都横看 —— 正常竖排页的
#   长行必然纵长; 混合页(如 p74 图例行 + 正文列)不满足, 不触发。
# 标定(数据驱动, 不硬编码页号/常数): 源图墨迹字级组件按 x 中心聚类得竖向「字列」(同 note_cols 手法);
#   行(y' 中心升序)与字列按序配对后最小二乘 —— 逆时针 x = kx*y' + bx (字列按 x 降序配)、顺时针
#   (按 x 升序配), 取残差小者定方向(实测 p159: 逆时针 rms 1.7px / 顺时针 400px);
#   文本方向(行高)另用「中位比例 + 中位截距」标定 y = ky*x' + by —— OCR 盒沿文本方向松紧不一
#   (实测盒长比墨迹长 10%-30%), 最小二乘会被带偏, 中位对松紧/离群点鲁棒(实测 ky 0.77)。
# 注: 只在渲染该页时套用(全局拟合/版框检测/页码序列一律仍用原始行), 不影响其它页的任何输出。
DEROT_ON = os.environ.get('VERT_DEROT', '1') not in ('0', 'false', 'False')
DEROT_MIN_ROWS = 3        # 触发所需的最少「横看」行数
DEROT_RMS_MAX = 30.0      # 配对标定的残差上限(px); 超限判为「不是旋转坐标系页」

def _ink_char_cols(pi):
    """源页墨迹「字列」: 字级连通组件(15-130px 见方, 面积>=60px)按 x 中心聚类
    -> [(x0,y0,x1,y1,组件数)] 按 x 降序。只留竖向列(高 > 2.5x宽): 横排文字的字簇是横向的,
    据此把「本来就不是竖排」的页(如末页水印页)挡在标定之外。"""
    from scipy import ndimage
    g = src_gray(pi)
    lab, n = ndimage.label(g < 185)
    cs = []
    for i, s in enumerate(ndimage.find_objects(lab), 1):
        h = s[0].stop - s[0].start; w = s[1].stop - s[1].start
        if (lab[s] == i).sum() < 60: continue
        if not (15 <= w <= 130 and 15 <= h <= 130): continue
        cs.append([s[1].start, s[0].start, s[1].stop, s[0].stop, (s[1].start + s[1].stop) / 2.0, w])
    if len(cs) < 6: return []
    ws = sorted(c[5] for c in cs); gap = 0.75 * ws[len(ws) // 2]
    cs.sort(key=lambda c: c[4])
    cl = [[cs[0]]]
    for c in cs[1:]:
        if c[4] - cl[-1][-1][4] > gap: cl.append([c])
        else: cl[-1].append(c)
    out = []
    for grp in cl:
        if len(grp) < 3: continue
        x0 = min(c[0] for c in grp); y0 = min(c[1] for c in grp)
        x1 = max(c[2] for c in grp); y1 = max(c[3] for c in grp)
        if (y1 - y0) <= 2.5 * (x1 - x0): continue
        out.append((x0, y0, x1, y1, len(grp)))
    out.sort(key=lambda c: -((c[0] + c[2]) / 2.0))
    return out

def _lin_fit(xs, ys):
    """最小二乘 y = k*x + b -> (k, b, rms 残差)"""
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    var = sum((x - mx) ** 2 for x in xs)
    if var <= 1e-9: return 0.0, my, float('inf')
    k = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var
    b = my - k * mx
    rms = (sum((y - (k * x + b)) ** 2 for x, y in zip(xs, ys)) / n) ** 0.5
    return k, b, rms

def derot_rows(k, pi, rows):
    """本页 OCR 是否落在旋转坐标系 -> 还原后的行列表; 非旋转页/标定失败返回 None。
    还原(py 2x px): x = kx*y' + bx, y = ky*x' + by; 行宽/行高按同一尺度(|kx|/|ky|)换算。"""
    if not DEROT_ON or src_doc is None: return None
    hz = [r for r in rows if (r[1] - r[0]) > 300 and (r[1] - r[0]) > 2.5 * (r[3] - r[2])]
    lng = [r for r in rows if (r[1] - r[0]) > 300]
    if len(hz) < DEROT_MIN_ROWS or len(hz) != len(lng): return None
    cols = _ink_char_cols(pi)
    if len(cols) < 3: return None
    rs = sorted(rows, key=lambda r: (r[2] + r[3]) / 2.0)        # 行按 y' 中心升序
    best = None
    for tag, co in (('逆时针', cols), ('顺时针', list(reversed(cols)))):
        pairs = list(zip(rs, co))
        if len(pairs) < 3: continue
        kx, bx, rms = _lin_fit([(r[2] + r[3]) / 2.0 for r, c in pairs],
                               [(c[0] + c[2]) / 2.0 for r, c in pairs])
        if best is None or rms < best[1]: best = (tag, rms, kx, bx, pairs)
    if best is None: return None
    tag, rms, kx, bx, pairs = best
    if rms > DEROT_RMS_MAX: return None                          # 残差大: 判为不是旋转坐标系页
    if not (0.5 <= abs(kx) <= 1.5): return None                  # 尺度不合理(同页坐标比例应 ~1)
    # 文本方向(行高)标定: 中位比例 + 中位截距(抗 OCR 盒松紧/同列离群行)
    sgn = 1.0 if tag == '逆时针' else -1.0
    ratios = []; offs = []
    for r, c in pairs:
        span = r[1] - r[0]
        if span < 100: continue
        t = (c[3] - c[1]) / float(span)
        if not (0.2 <= t <= 2.0): continue                       # 页码行等与长列同列: 比例离谱, 弃
        ratios.append(t)
    if not ratios: return None
    ratios.sort(); ky = sgn * ratios[len(ratios) // 2]
    for r, c in pairs:
        span = r[1] - r[0]
        if span < 100: continue
        if not (0.2 <= (c[3] - c[1]) / float(span) <= 2.0): continue
        offs.append(c[1] - ky * r[0])
    offs.sort(); by = offs[len(offs) // 2]
    out = []
    for x0, x1, y0, y1, t in rows:
        nx = kx * (y0 + y1) / 2.0 + bx; ny = ky * (x0 + x1) / 2.0 + by
        w = abs(kx) * (y1 - y0); h = abs(ky) * (x1 - x0)
        out.append((nx - w / 2.0, nx + w / 2.0, ny - h / 2.0, ny + h / 2.0, t))
    print('  [旋转页修正] p%d 判定%s(配 %d 行 x %d 字列) kx%.3f bx%.1f rms%.2f px  ky%.3f by%.1f' % (
        pi + 1, tag, len(rows), len(cols), kx, bx, rms, ky, by))
    return out

# ---------- 1.975) 无版框书: 伪版心 + 伪槽格(taskO / #29) ----------
# 背景(#29): §1.98/§1.99 的几何全部锚在**版框**上(frame_geom) —— 无版框的书(本册的排印本正文页)
#   取不到版框 -> page_metrics 全 None -> 整页走 v2 流式排版(列位/字号取 OCR 盒的全局拟合),
#   且 §1.956 的源图侧标定样本(XSCALE / PUNCT_* / BR_SIZE* / INK_*)一个也取不到 -> 8 项回落兜底。
# 做法(与 §1.99 同源, 只把「版心」换成**伪版心**):
#   伪版心 = 本页正文 OCR 行并集的墨迹包围盒(正文行 = 本页页高比例的「长行」+ 单行文本);
#   伪槽格 = 伪版心内 _ink_bands(cov=0.12) 的墨迹列带 —— 每带 = 一列; 格边界 = 相邻带心连线的中点
#     (列间空隙中点), 首末格外扩半个列距 -> 格宽 = 列距, 与框驱动槽格同语义(标点摆位 PUNCT_DX 的
#     分母 = 格距; 槽内 run/顶/底/步进/字号全部走 §1.98 同一套统计)。
#   无版框 -> **不画**版框线/界行线(frame_tex 见 'virtual' 直接返回空): 不凭空画框。
# 开关: NF_MODE = 抽样页一个版框都没测到(FRAME_REF is None) 且 VERT_NOFRAME != 0 ——
#   有实测版框的书(wz6) 与「有版框但无槽可配」的页(§1.99)路径**一字不改**。
# OCR 坐标回源图坐标系(taskO 实测, 见 docs/vert_noframe_report.md §3): 该书 OCR 帧相对源页有
#   **系统性各向异性缩放**(p406 拟合 kx 1.20 / ky 1.12, 逐页略异; p407 整页还在 90° 旋转坐标系里,
#   页码 x 因此合法地越出页幅) —— OCR 绝对坐标不能直接与源图门限比较(实测 p406 最左列 OCR x0=76px
#   落进全局「左页边带」被当边注丢弃; 页码行 OCR x 落进版心带 -> 不认作特殊行)。故本路径先做
#   **逐页仿射标定**(OCR 行心 ↔ 墨迹列心; 尺度 = 相邻间距比的中位, 截距 = 中位差; y 尺度 = 字步进比
#   中位), 把本页 OCR 行映射回源图坐标系(只改几何, 文本不动), 再交既有判据(is_body_col/
#   special_rows/page_rows 本就是「源图坐标系」口径) —— 这是「坐标系问题」的处置。
NF_MODE = (FRAME_REF is None) and os.environ.get('VERT_NOFRAME', '1') not in ('0', 'false', 'False')
_NF['on'] = NF_MODE             # 置位 §1.06 的逐页门限(在此之前一律用全局门限)
if NF_MODE and src_doc is not None and RIGHT_p > PW_PX / 2.0 - 0.5:
    # 无版框书: OCR 帧的 x 尺度是 1.07-1.20(见 docs/vert_noframe_report.md §3), 拟合出的「版心右缘」
    #   会超过本页纸宽(实测 923.5pt vs 基准纸宽 921.75pt)。伪槽格路径(self 有源图墨迹约束)不受影响,
    #   但 v2 流式回退页(扉页/版权页等)按该值放最右列 -> 字盒出页 0.57pt(实测源页 1/3 共 9 条 span)。
    #   故无版框时把拟合右缘夹进纸内(留 1pt; 只动 NF, 有版框书与 wz6 不走这里)。
    print('[版心右缘] 无版框: OCR 拟合 %.1fpt 超过基准纸宽 %.1fpt -> 夹到 %.1fpt' % (
        RIGHT_p, PW_PX / 2.0, PW_PX / 2.0 - 1.0))
    RIGHT_p = round(PW_PX / 2.0 - 1.0, 1)
    OM_pt = round(RIGHT_p - TH_pt - 70, 1)
NF_SLOT_DBG = os.environ.get('VERT_NF_SLOT_DBG') == '1'   # 伪槽格逐槽统计诊断打印
# taskCJ: 无框伪槽格「槽窗口锚定」(默认开, =0 回到旧口径做 A/B 对照)。
#   根因(诊断 docs/vert_taskCJ_diagnosis.md): nf_edges 的槽边界 = 相邻墨迹带心中点 ->
#   槽心相对本列带心偏 (G_R-G_L)/4; 本列一侧是空白(章末/诗行/页边书眉列)时 G 达数倍列距,
#   整列被平移约 2 个列距(实测 p159 -88.6pt / p937 -88pt / p721 -85pt / p149 +83pt)。
#   修法: 只对「被拉宽且中点显著偏离本列带心」的槽, 把窗口收到本列带心 ± 半列距
#   (两端仍不小于本列墨迹带 + 4pt, 保证不切墨); 普通槽判据不成立 -> x0/x1 逐位不变。
NF_SLOT_ANCHOR = os.environ.get('VERT_NF_SLOT_ANCHOR', '1') not in ('0', 'false', 'False')
NF_HROW_AR = float(os.environ.get('VERT_NF_HROW_AR') or 2.0)   # 横排行判据: 行盒 宽/高 下限
NF_HROW_CHAR = float(os.environ.get('VERT_NF_HROW_CHAR') or 0.60)   # 横排行字数占本页比下限
# taskU-C: 见 page_puts 里 ok 的注释 —— 目录页走「残余列补救」而非 v2 流式的开关(默认关, 实测净损失字)
TOC_RESCUE_OK = os.environ.get('VERT_TOC_RESCUE_OK', '0') not in ('0', 'false', 'False')
NF_POS_PRIOR = float(os.environ.get('VERT_NF_POS_PRIOR') or 60.0)   # 行/槽配平的位置先验权重
#   (只对伪槽格页生效; 单位与「格数差」同尺度 —— 整段平移 8 行 x 1 槽 = 8/15 x 60 = 32 > 跳行 2x8=16,
#    故 DP 宁可原地跳过剩行, 见 _align_rows_slots 注释)
NF_ROW_FRAC = float(os.environ.get('VERT_NF_ROW_FRAC') or 0.05)   # 槽内「行墨迹下限」= 槽宽 x 该值
#   (只无版框路径用; 目的 = 滤掉槽窗口里混进的印刷细线, 见 _slot_runs 的 row_floor 注释)
# --- taskAB) 行↔槽配对错位修复(书眉/页码共槽 + 列序跳到页首) ---
# 根因(实测 wz7 p86/p513):
#   ① 伪槽格是**纯 x 带**(墨迹列带), 同一条 x 带里 y 方向相距很远的两段(书眉 320-442 /
#      页码 1188-1229, 空白 746pt)仍算一个槽 -> 槽 run 数把两段相加(3+2=5), 行↔槽 1:1 被破坏
#      (19 行 18 槽): 页码那行被 DP 跳过不渲染, 书眉行按整槽跨度算步进(「梅」偏 127pt)。
#   ② _align_rows_slots 只按「格数/run 数」配平, 不知道行/槽的实际位置: p513 两列正文
#      (x 192.6/147.6)被配到 x 766/576 的标题/詩列槽(偏 +574/+429pt)。
# 修法(**默认已开** —— 全书验证完成后翻转, 见 docs/vert_taskAB_report.md;
#   要复现旧行为(无框书 v8 口径)用 VERT_AB_FIX=0):
#   A) 槽按 y 拆子槽: 槽内墨迹 y 投影出现 > K x 字步进的空白 -> 拆(有 OCR 行跨越该空白则**不拆**,
#      目录页/双段列的内空隙仍交 fit_gaps 还原);
#   B) 配对增加位置约束: x 中心距 > XK x 列距 或 y 范围不重叠 -> 禁止配对; 代价加 x/y 中心距离项。
#      只对「无版框书 + OCR 坐标已标定到源图坐标系」(gv['fixed'])的页生效 —— 未标定页 OCR x 有
#      1.07-1.20 的系统缩放, 位置不可信, 仍走原「格数」口径。有版框书(wz6)一字不改。
AB_FIX = os.environ.get('VERT_AB_FIX', '1') not in ('0', 'false', 'False')
AB_YSPLIT = os.environ.get('VERT_AB_YSPLIT', '1' if AB_FIX else '0') not in ('0', 'false', 'False')
AB_ALLSLOTS = os.environ.get('VERT_AB_ALLSLOTS', '1' if AB_FIX else '0') not in ('0', 'false', 'False')
AB_GEOM = os.environ.get('VERT_AB_GEOM', '1' if AB_FIX else '0') not in ('0', 'false', 'False')
AB_YSPLIT_K = float(os.environ.get('VERT_AB_YSPLIT_K') or 2.5)   # 拆槽空白下限(字步进倍数)
AB_XK = float(os.environ.get('VERT_AB_XK') or 2.0)               # 配对 x 硬门限(列距倍数)
AB_YK = float(os.environ.get('VERT_AB_YK') or 1.5)               # y 中心代价权重(字步进倍数)
AB_YSPLIT_MIN_HM = float(os.environ.get('VERT_AB_YSPLIT_MIN_HM') or 0.45)
    # 子槽墨高下限(字步进倍数): 低于此值的子槽视为退化 -> 该槽整体不拆。
    #   背景: 退化子槽会让 col_puts 的 ysplit 分支算出 step=0, 进而字号保护算出 F=0pt
    #   (实测全书 3 处 `! Improper 'at' size (0.0pt)`: 2 字短列 是：/又：/見：/唱：)。
NF_MIN_COL = int(os.environ.get('VERT_NF_MIN_COL') or 2)   # 伪槽格最少列数(更少 -> 该页交回 v2 流式)
#   taskP 由 3 降到 2: 实测本册「题辞」页(源页 22)只有 2 列大字, 降前被挡在 NF 外 -> 掉 v2 流式
#   (几何取 OCR 盒全局拟合, 字号 47.9pt 对源书 ~95pt 明显偏小); 2 列时 nf_edges 用唯一一段
#   列距同样能建槽(见 nf_edges)。
NF_COV = 0.12                   # 墨迹列带覆盖阈值(与 §1.99 同: 带出段尾短列)
# --- §1.976 短列的 OCR 列框检出(taskS: 用户实测 wz7 源页 354 的「又曰：」整列丢失) ---
# 根因: 现有三条列带路径(**检测** _ink_bands cov=0.12 / **补带** nf_fill_bands cov_lo=0.04 /
#   **补救** _ocr_band cov>0.04)的覆盖率分母都是**整页版心高** —— 3 字列的墨迹只占版心高的 2.4%
#   (实测该页 0.024 < 阈值 0.04), 三条路径全部漏检 -> 12 行对 10 槽 -> 两个短列被静默丢弃,
#   且**丢掉的那一列的墨迹落进邻槽**(槽边界=相邻带心中点, 少一条带就把边界推远) -> 邻槽的
#   run 序列/墨迹跨度被污染 -> fit_gaps 为解释多出来的跨度而乱插空格(用户反馈①的另一半)。
# 做法(分母换成**该行自身的墨迹窗**): 版心内的**非长行**(= 短列, 有真实 OCR 文本)自带 x 心与 y 带;
#   在该窗内按 x 投影找墨迹带, 三条证据同时成立才收(两侧都满足, 见 _sb_band)。
NF_SB_OWN = os.environ.get('VERT_NF_SB_OWN', '1') not in ('0', 'false', 'False')   # 短列检出总开关
NF_SB_COV = float(os.environ.get('VERT_NF_SB_COV') or 0.05)   # 窗内 x 投影覆盖率下限(候选生成)
#   (只作**候选**生成: 短列的墨迹在窗内也只占 0.14(又/曰 各 19.5pt / 窗 137pt), 故阈值必须低;
#    挡碎墨/噪点靠下面的密度 + 字证据两道, 不靠这条)
NF_SB_DEN = float(os.environ.get('VERT_NF_SB_DEN') or 0.12)   # 候选带**自身墨迹包围盒**内填充率下限
#   (实测「又曰：」= 0.41; 单个 5x5 噪点斑 = 0.01; 这条把「分母 = 整页版心」换成「分母 = 该列
#    自身的墨迹范围」, 短列与长列同一口径 —— 见 §1.976 注释)
NF_SB_PADX = float(os.environ.get('VERT_NF_SB_PADX') or 0.80)  # x 窗半径(列距倍数)
NF_SB_PADY = float(os.environ.get('VERT_NF_SB_PADY') or 1.50)  # y 窗外扩(本行字步进倍数)
NF_SB_RATIO = (0.5, 1.35)       # 候选字 run 墨高 / 本页列带参照字高 的合法区间(与 _ok_stat 同口径)
NF_FILL_HMIN = float(os.environ.get('VERT_NF_FILL_HMIN') or 3.0)   # 补带「文字列证据」的字高下限(pt)
NF_FILL_NRUN = int(os.environ.get('VERT_NF_FILL_NRUN') or 3)       # 补带「文字列证据」的最少墨迹 run 数
NF_FILL_PAD = float(os.environ.get('VERT_NF_FILL_PAD') or 8.0)     # 补带「文字列证据」的统计窗外扩(pt)
NF_NOTE_CAP = os.environ.get('VERT_NF_NOTE_CAP', '1') not in ('0', 'false', 'False')   # NF 页「注行数<=注槽数+1」加严
#   taskP2: nf_fill_bands 的候选校验用**绝对**下限(不用「相对现有带字高」比例 —— 窄带 run 被横向
#   截短, 比例判据会误杀宽字形列); 6pt < wz7 最小正文字高(小开本页 ~17pt) 且 > 噪点碎墨(2-4pt)。
# 无版框书"字号合理性"区间(页高比例; §1.98 的 10/60pt 是 wz6 绝对量, 见 _metrics_finish 注释):
#   下限 0.80% 页高 = 原 10pt/1254.1pt; 上限 12% 页高(实测 wz7 序页字号 103.6pt = 7.2% 页高;
#   插图页粘连长 run 测出的 ~62% 页高仍被挡)。env 可覆盖(新口径, 有版框书不走这里)。
FONT_MIN_FRAC = _envfrac('VERT_FONT_MIN_FRAC', 0.008)
FONT_MAX_FRAC = float(os.environ.get('VERT_FONT_MAX_FRAC') or 0.12)
NF_FIT_K = (0.7, 1.6)           # OCR/源图 尺度合理区间(实测 1.07-1.20; 超出判标定失败, 保持原坐标)
NF_FIT_RES = 0.5                # 标定残差上限(列距倍数): 超限说明配对错位 -> 不采纳
# taskQ 遗留1: 标定的**映射方向**开关。nf_fit 拟合的是 `OCR = k x 源图 + b`(见 _nf_fix_page 注释),
#   把 OCR 行搬回源图坐标系必须用**逆映射** `源图 = (OCR - b) / k`; 修前该处直接写成 `k x OCR + b`
#   (同向再映射一次 = 尺度被平方) -> 映射后的 x 域普遍越出纸幅, 被下游「映射后正文 x 不符」拒掉
#   (实测 248/250 页) -> 该标定路径实际休眠。1(默认) = 逆映射(修后); 0 = 修前行为(仅 A/B 对照)。
NF_FIX_INV = os.environ.get('VERT_NF_FIX_INV', '1') not in ('0', 'false', 'False')
# taskQ 遗留1 补: 标定「行↔列」对齐的择优判据。1(默认) = 按**映射后的绝对位置**择优(正文行心域
#   应与墨迹列心域相合, 残差仅同分次序); 0 = 只按残差中位(修前行为, 梳状简并时 190/245 页选错列
#   相位, 见 nf_fit_align 注释) —— 仅供 A/B 对照。
NF_FIT_ALIGN_POS = os.environ.get('VERT_NF_FIT_ALIGN_POS', '1') not in ('0', 'false', 'False')
# taskQ 遗留1 补: **标定落地**口径(把标定结果落到本页的那一步, 见 _nf_after_fix)。
#   1(默认) = 本轮口径: ①窗 = 标定后正文行盒并集**外扩 NF_FIT_PAD x 标定前列距**(行盒并集不是
#   墨迹列并集, 边界列会探出窗缘 —— 实测 p254 左端列 43.0-59.0 在行盒窗外 14.6pt, 不外扩则整列
#   检不出 -> 行多槽少 -> p254 少 95 字 / p130 少 84 字); ②列带 = 检测 + 短列补齐(与标定前同口径);
#   ③标定后撑不起伪槽格时**弃用本页标定**(退回未标定坐标系, 见 _nf_frame)。
#   0 = 修前口径(窗 = 行盒并集不外扩 / 只重算检测 / 撑不起就整页 return None) —— 仅 A/B 对照。
NF_FIT_LAND = os.environ.get('VERT_NF_FIT_LAND', '1') not in ('0', 'false', 'False')
NF_FIT_PAD = float(os.environ.get('VERT_NF_FIT_PAD') or 1.0)   # 外扩量(列距倍数, 只在 LAND=1 下生效)
# taskQ 遗留2: 「重试口径」的选择开关。1(默认) = 按**渲染字数择优**(重试口径 vs 该页不采纳重试时
#   实际会走的框内兜底口径, 各算一次取多者, 与 taskP §1 表第 4 行同一机制); 0 = 修前行为(重试口径
#   一旦适配就无条件采纳, 仅 A/B 对照)。
NF_RETRY_BEST = os.environ.get('VERT_NF_RETRY_BEST', '1') not in ('0', 'false', 'False')

# --- taskCD) 特殊版式缺字(默认关 = 保持现行为, 便于 A/B 回退; 只作用于无版框 NF 路径) ---
# ① 多块合并行的拼接口径(taskCD-a, 见 nf_join_rows):
#    修前步进中位只取「无换行」行 -> 目录页/字表页整页都是 OCR 多块合并行(带 \n)时, 中位样本为空
#    或被页上仅有的水印/横排短行(2-4pt/字)带偏 -> 真列(37-67pt/字)判成「不拼」-> 带 \n 的行在
#    下游 page_rows 被当残片整行丢弃。实测 p563 整页 0 字 / p1171 只剩 7 字(仅目录标题)。
NF_JOIN_MED = os.environ.get('VERT_NF_JOIN_MED', '1') not in ('0', 'false', 'False')
NF_JOIN_HI = float(os.environ.get('VERT_NF_JOIN_HI') or 1.5)   # 拼接步进上界(倍数; 修前 1.4)
#   1.5 的依据: 全书 1748 页模拟(JOIN_MED 口径) —— 窗口从 1.4 放宽到 1.5 只多拼 3 行, 全是真列:
#   p400「當局者迷，傍觀者清。」(1.413) / p1511 目录回目(1.488) / p1742 字表「鬢髮…」(1.451);
#   再宽会开始收进 OCR 多块残片, 故不继续放宽。
# ② 正文/小字注分层参照(taskCD-b, 见 _metrics_finish):
#    修前 hmax = max(槽字高): 页内少数大字号标题列把参照撑高 -> 0.75 x hmax 把占多数的正文列整批
#    划出 body(实测 p659: 1 条 38pt 标题 + 14 条 23-26pt 正文 -> 阈值 28.5 -> 正文全被判成注,
#    产物 220 字且字号错乱)。改为「最高四分位的中位」作参照: 离群大字号只有占 >= 25% 槽数时
#    才会抬高参照; 单字号页取值与 max 相同(逐位不变)。
NF_BODY_TIER = os.environ.get('VERT_NF_BODY_TIER', '1') not in ('0', 'false', 'False')
# ③ 伪版心外的扫描水印/馆藏标签剔除(taskCD-c, 见 _nf_margin_artifact):
#    实测 p1171(小开本目录页): 页顶手写编号 859.49/6996/879/v.3 与页底「国家图书馆 + 条码」
#    是扫描件上的馆藏标记, 不是书内容, 却在页边带里被 special_rows 认成书眉/页码画出来
#    (其中条码行还与目录列 x 带重叠, 被行合并并进邻列 -> 整列错字)。判据只认「整行在伪版心
#    y 之外」且「横排(w/h >= NF_MARGIN_AR)或无汉字」—— 真书眉/页码是竖排汉字, 不受影响。
NF_DROP_MARGIN = os.environ.get('VERT_NF_DROP_MARGIN', '1') not in ('0', 'false', 'False')
PARA_MARK = os.environ.get('VERT_PARA_MARK', '1') not in ('0', 'false', 'False')
    # 段首圈点 ⊙(taskCC): 源书段落起首的圈点在 OCR 里被当噪点跳过, 但它占一整格 ->
    #   该列 OCR 框高 = 字数+1 格。不处理的话文字整体上移一格、正好压在圈点上(实测 p43/p44)。
    #   开时: 首格让给圈点(T += 一格), 文字按剩余跨度铺, 圈点用 _put_tex 画出来。
    #   判据见 _slot_lead_mark(VERT_PARA_MARK_LO/HI / _CENTER_MIN / _RING3_MAX / _OUTER_MIN)。
PARA_MARK_LO = float(os.environ.get('VERT_PARA_MARK_LO') or 0.6)
PARA_MARK_HI = float(os.environ.get('VERT_PARA_MARK_HI') or 1.6)
PARA_MARK_MIN_CHARS = int(os.environ.get('VERT_PARA_MARK_MIN_CHARS') or 8)
PARA_MARK_CENTER_MIN = float(os.environ.get('VERT_PARA_MARK_CENTER_MIN') or 90.0)
PARA_MARK_RING3_MAX = float(os.environ.get('VERT_PARA_MARK_RING3_MAX') or 20.0)
PARA_MARK_OUTER_MIN = float(os.environ.get('VERT_PARA_MARK_OUTER_MIN') or 55.0)
PARA_MARK_SIZE = float(os.environ.get('VERT_PARA_MARK_SIZE') or 1.357)
    # ⊙ 的墨高在 F=31.2 时只有 22.1pt, 而源书圈点墨高 30pt(实测 p43) -> 放大 1.357 倍。
PARA_MARK_DY = float(os.environ.get('VERT_PARA_MARK_DY') or 0.855)
    # ⊙(U+2299) 是数学符号, 字形墨心相对 \put 锚点比汉字高得多 —— 实测 p43 直接画时
    #   墨迹 370-388, 而应落在首字格中心 407.6, 偏高 28.6pt = 0.92em(F=31.2)。
    #   本值 = 向下补偿的字号倍数; 换字体/换字号需重标(做法同 PUNCT_INK: 探针渲染实测墨心)。

NF_FRAME_ALLX = os.environ.get('VERT_NF_FRAME_ALLX', '0') not in ('0', 'false', 'False')
    # 伪版心 x 域并上「y 落在正文带内」的所有行(含被判为特殊行的大字号标题/目录标题)。
    #   背景: p43 凡例标题 x750-804 因「大字号特殊行」被从 body 摘出 -> 伪版心 x1 只到 742.9
    #   -> 标题反过来因「在版心之外」被判页边丢弃(循环矛盾), 实测该页少 2 字。
    #   y 域仍由 body 定, 故书眉/页码(在 y 带之外)不受影响。
    # ⚠ **不要启用: 全书实测是净亏**。wz7 1748 页对照已交付 v8(tag v8-fullpass):
    #     总字符 931,773 -> 926,775 (-4,998); 变好 18 页 / 变差 306 页 / 不变 1,424 页;
    #     越界 0 -> 3 span(p958, 最深 0.86pt); verify 从 PASS 掉回 FAIL。
    #   根因: 放宽的是 _ink_bands 的**扫描窗口**, 不只是「多加一个标题槽」—— 窗口变宽后
    #   页边噪声也被算成列, 列数/列距整体改口径 -> 行↔槽配对连带变差(典型 -52 字/页 = 2 列)。
    #   正确做法(未实现): 版心不动, 对「落在版心 x 外但距离 < ~1.5 列距」的大字号短行
    #   **单独补一个槽**(复用 special_rows / 列框兜底那条路径), 只增一槽不改窗口。
    #   本开关保留作为该机制的正向测试载体(见 test_title_row_widens_frame_x)与负面记录。
NF_MARGIN_AR = float(os.environ.get('VERT_NF_MARGIN_AR') or 2.5)   # 水印行判据: 行盒 宽/高 下限
# --- taskCE) 目录页「同 x 多行 y 分段」+ 版心外大字号标题补槽(默认关, 便于 A/B 与回退) ---
# ① 目录页列结构(实测 p53/p55/p561/p1172): 每「回」占一列, 列内自上而下 = 回次 + 回目(1-2 行)
#    + 点线 + 页码, **同 x 不同 y**。page_rows 合并后每列仍是 1-2 行(回次与回目合成一行, 页码因
#    间隔 > 2.5 步进而独立), 于是 R ≈ 1.3-2.3 x C —— 与「双行小字页」(每槽左右两子列, R = 2C)
#    在条数上不可分。现有 _dual 按 x 拆左右子列, 对这些页会把上下分段的行按序塞进左右子列 ->
#    文本交错(实测 p55 产物「第三二十九七九回…」)。判据用**行心 x 聚类**: 真双行小字页的 2C 条
#    行分居 2C 个 x 心; 目录页的行心聚成约 C 组(组均 >= 1.4 行)。命中后不拆 x, 改走 y 拆子槽
#    (_split_slot_y, 过滤点线小 run)+ 位置配对; 子槽 y 窗按本页行 y 范围外扩(回次/页码在伪版心外)。
NF_TOC = os.environ.get('VERT_NF_TOC', '1') not in ('0', 'false', 'False')
# taskCF: 列序单调性守卫 —— 竖排阅读序是**保序双射**(行按 x 递减、槽按 x 递减),
#   位置口径配对(geom=True)允许两侧跳过但**不禁止交叉**, 实测 p54 把
#   第十六/十七/十八回排成 3-循环置换(列内文字自洽、只有 x 位置互换)。
#   开启后: 检出交叉 -> 退回「按序口径」(构造上单调)并打日志。
MONO_FIX = os.environ.get('VERT_MONO', '1') not in ('0', 'false', 'False')
NF_TOC_GROUP = float(os.environ.get('VERT_NF_TOC_GROUP') or 0.5)    # 同行心判据(列距倍数)
NF_TOC_MINRUN = float(os.environ.get('VERT_NF_TOC_MINRUN') or 0.30) # y 拆槽时视为「点线」的 run 高上限(步进倍数)
# --- taskCH) 目录页独立分支: 判定提前到 nf_join_rows 之前, 命中后按 (x 带, y 层) 二维配对 ---
# 背景(用户反馈 p53-p55 目录乱; 见 docs/vert_taskCH_brief.md):
#   旧实现把目录特殊性散在 5 处各打补丁(§1.995 TOC 判据按行数比 R>=1.3C、taskCG5「全列做槽」、
#   taskCG4「补列」、`_split_slot_y` 从墨迹反推层、_nf_rescue_rows 短列补救), 判据互相不知道对方 ->
#   修好 p54 就弄坏 p563。根因是 **page_rows 的 _merge_col_rows 先把「回次/回目上句/回目下句」
#   合并成一行**, 之后任何按「行数」推目录结构的判据都失效(p53 合并后 R=21/C=12, 「導讀」还因
#   步进 100.6 被划进 note 而整行丢失)。
# 现方案:
#   ① 判据只用**原始 OCR 行**(未 join/未 merge)的列内分层结构, 不看行数比:
#      同列 >=2 层 + 首层短(典型「第N回」) + 其余层也是短行(回目/页码, 中位 <= NF_TOC_REST_MAX)
#      + 至少 NF_TOC_MINCOL 条这种列 + 各列首层落在同一水平带(目录「第N回」对齐);
#   ② 命中后 g['toc']=True, page_puts 走独立路径 `_toc_puts`: x 归列、列内按 y 分行, 每行一个
#      **自带 y 跨度**的槽用 col_puts 渲染(不再从墨迹反推层, 不再走 _split_slot_y);
#   ③ 未命中页一字不动(普通正文路径完全不变)。
#   行内 \\n(p563/1171 这类整列被 OCR 合成一个框)按层计; 渲染时整行仍是一个槽(层 y 未知),
#   col_puts 的 fit_gaps 用墨迹 run 还原列内空隙。
NF_TOC_BRANCH = os.environ.get('VERT_NF_TOC_BRANCH', '1') not in ('0', 'false', 'False')
NF_TOC_COL_TOL = float(os.environ.get('VERT_NF_TOC_COL_TOL') or 0.30)   # x 归列容差(列距倍数)
NF_TOC_TOP_MAX = int(os.environ.get('VERT_NF_TOC_TOP_MAX') or 6)        # 首层「第N回」字数上限
NF_TOC_REST_MAX = float(os.environ.get('VERT_NF_TOC_REST_MAX') or 20)   # 其余层字数中位上限
NF_TOC_MINCOL = int(os.environ.get('VERT_NF_TOC_MINCOL') or 6)          # 形态列数下限
NF_TOC_TOP_TOL = float(os.environ.get('VERT_NF_TOC_TOP_TOL') or 0.03)   # 首层 y 对齐跨度上限(页高比例)
# ② 版心外大字号短行单独补槽(taskCE-c, 实测 p43 凡例标题 x749.9-804.4, 伪版心右缘 742.9):
#    版心**不动**, 只把 _page_specials 的候选行心窗口从版心缘外扩 NF_TITLE_OUT_PAD 个列距, 且仅限
#    短行(len <= NF_TITLE_OUT_MAXLEN)、后面仍要过「大字号 + 稀少性」两道既有判据。只多认领这一行
#    (走标题署名路径渲染, x 带进 _SPECIAL_BLOCK), 不放宽 _ink_bands 的扫描窗口。
NF_TITLE_OUT = os.environ.get('VERT_NF_TITLE_OUT', '1') not in ('0', 'false', 'False')
NF_TITLE_OUT_PAD = float(os.environ.get('VERT_NF_TITLE_OUT_PAD') or 1.5)   # 外扩量(列距倍数)
NF_TITLE_OUT_MAXLEN = int(os.environ.get('VERT_NF_TITLE_OUT_MAXLEN') or 8)  # 只收短行(字数上限)

def nf_body_rows(rows, ph):
    """本页正文 OCR 行: 长行(本页页高 x LONG_H_FRAC) + 单行文本。
    比 is_body_col 多两点(都是无版框书必需): ① 页幅用**本页**(混纸型); ② **不**按「左带小字」丢行
    —— 无版框书的左侧就是正文列(实测 p406 最左列 OCR x0=76px < 全局左带 155px 会被误丢)。"""
    return [r for r in rows
            if (r[3] - r[2]) >= LONG_H_FRAC * ph and len(r[4]) >= 2 and '\n' not in r[4]]

def nf_join_rows(rows):
    """无版框书: 把 OCR 在「小字標題/曲牌 + 正文」相接处插进去的换行拼回一行(实测 wz7 多页:
    「甜水令\\n「瓊樹生花，玉龍晚凍…」行盒仍是**一整列** —— y 跨度/字数 = 常列步进)。
    wz6 的换行行是「多块合并的残片」(图例 194 字), 故该规则**只在 NF 路径用**。
    判据: 该行步进 ∈ [0.7, 1.4] × 本页常列步进中位 -> 拼回; 否则保持原样(下游按残片丢弃)。
    taskCD-a 模式(下方注释)下上界默认放宽到 1.5(NF_JOIN_HI): 全书模拟只多拼 3 行, 均为真列。
    taskCD-a(NF_JOIN_MED=1): 中位样本改为「按拼接后字数 >= 8 的行」—— 修前只取**无换行**行:
      目录页(实测 p563/p1171)整页都是多块合并行 -> 中位样本为空或被页上仅有的水印/横排短行
      (2-4pt/字)带偏 -> 真列(37-67pt/字)判成不拼 -> 整页在下游被当残片丢弃。样本不足 3 条时
      退回「>=2 字」的行。默认 0 保持修前口径(单元测试也按默认口径断言)。
    注: 开关用 globals().get —— 单测加载器按 AST 只提取函数体, 不注入本模块新增的全局时仍可用。"""
    _hi = 1.4
    if globals().get('NF_JOIN_MED', False):
        def _js(r):
            t2 = r[4].replace('\n', '')
            return (r[3] - r[2]) / max(1, len(t2)) if len(t2) >= 2 else 0.0
        st = sorted(s for s in (_js(r) for r in rows
                                if len(r[4].replace('\n', '')) >= 8) if s > 0)
        if len(st) < 3:                    # 长行样本过少(整页短行页) -> 退回全部行, 仍比「只看无换行行」稳
            st = sorted(s for s in (_js(r) for r in rows
                                    if len(r[4].replace('\n', '')) >= 2) if s > 0)
        _hi = globals().get('NF_JOIN_HI', 1.4)   # taskCD-a: 修前 1.4; CD 模式默认 1.5(依据见常量注释)
    else:
        st = sorted((r[3] - r[2]) / max(1, len(r[4])) for r in rows if len(r[4]) >= 2 and '\n' not in r[4])
    if not st: return rows
    med = st[len(st) // 2]
    out = []
    for x0, x1, y0, y1, t in rows:
        if '\n' not in t:
            out.append((x0, x1, y0, y1, t)); continue
        t2 = t.replace('\n', '')
        s2 = (y1 - y0) / max(1, len(t2))
        out.append((x0, x1, y0, y1, t2) if 0.7 * med <= s2 <= _hi * med else (x0, x1, y0, y1, t))
    return out

def _toc_seglen(s):
    """目录行文本的「字数」口径: 去空格/全角空格/换行(与字符量统计同口径)。"""
    return len(s.replace('\n', '').replace(' ', '').replace('　', ''))


def _toc_grid_layers(rows, cx, tol):
    """目录网格层数(taskCH2): 原始 OCR 行按 x 心归带(相邻心差 <= tol px 同带)后,
    与 x 心 cx 同带的行数。真标题/署名行自成一带 -> 1; 目录列的回次/上句/下句同带 -> 2-3;
    不在任何带内 -> 0。供 `_page_specials` 判断「这一行是目录列的一层, 不是标题」。"""
    groups = []
    for c, i in sorted(((r[0] + r[1]) / 2.0, i) for i, r in enumerate(rows)):
        if groups and c - groups[-1][-1][0] <= tol:
            groups[-1].append((c, i))
        else:
            groups.append([(c, i)])
    best_d, best_n = tol + 1.0, 0
    for gr in groups:
        d = min(abs(c - cx) for c, _i in gr)
        if d <= tol and d < best_d:
            best_d, best_n = d, len(gr)
    return best_n


def nf_toc_shape(rows, pitch, ph):
    """目录页形态判据(taskCH)。入参 = **原始 OCR 行**(px)、本页列距(pt)、页高(px)。
    返回 {ncol, multi, shorttop, topspread, pitch} 或 None(非目录页)。

    为什么不用旧判据(R >= 1.3 x C): 旧判据在 page_rows 的 _merge_col_rows **之后**跑, 目录页
    「回次/回目上句/回目下句」已被合并 -> R ≈ C(实测 p53 21 行 12 槽), 判据永不成立; 而 p53 的
    「導讀」还因列步进 100.6pt 被划进 note, 根本不参与配对(这就是用户看到的缺列)。

    判据(全部本页相对量, 换书不用改常数):
      ① x 归列: 行心距 <= NF_TOC_COL_TOL x 列距 归为同一列;
      ② 列内分层: 无 \\n 的行是一层(带 y 位置); 含 \\n 的行按内部换行拆层(层 y 未知, 保持文本序);
      ③ **目录形态列**: 层数 >= 2, 首层短(<= NF_TOC_TOP_MAX 字; 典型的「第N回」),
         首层比其余层短, 且其余层字数的中位 <= NF_TOC_REST_MAX(回目/页码都是短行)。
         正文页同列断行(诗行/段落接续)两侧都长; 曲牌页首层虽短(「滾綉毬」)但其余层是 30-40 字
         正文长行 —— 都被 ③ 的后两条挡掉(实测 p640/p969/p1180 不命中)。
      ④ 形态列数 >= NF_TOC_MINCOL, 且这些列的首层 y 顶跨 <= max(NF_TOC_TOP_TOL x 页高, 40pt)
         (目录各列的「第N回」落在同一水平带; 只统计 y 已知的首层 —— 整列 \\n 页无 y, 跳过此项)。
    实测(全书 1748 页, tmp_vert/taskCH/probe_toc.py): 命中 14 页, 全部是真目录页
      p45/47/48/49/50/51/53/54/55/561/562/563/1171/1172; 未命中页的形态列数 <= 5。"""
    if not rows or pitch <= 0:
        return None
    tol = NF_TOC_COL_TOL * pitch * 2.0          # pt -> px
    cs = sorted(((r[0] + r[1]) / 2.0, i) for i, r in enumerate(rows))
    groups = []
    for c, i in cs:
        if groups and c - groups[-1][-1][0] <= tol:
            groups[-1].append((c, i))
        else:
            groups.append([(c, i)])
    multi = shorttop = 0
    tops = []
    for gr in groups:
        # 列内按 y 排序 —— 同一 x 带里可能同时有「第N回」(页顶)和页码(页底), 不排序会把页码
        # 当成首层(实测 p53 的 x488 列: 页码心比回次心略偏左, 排序后才是首层)
        segs = []
        for _c, i in sorted(gr, key=lambda z: (rows[z[1]][2], z[0])):
            r = rows[i]
            if '\n' in r[4]:
                for s in r[4].split('\n'):
                    if s.strip():
                        segs.append((s, None))
            else:
                segs.append((r[4], r[2] / 2.0))
        if len(segs) < 2:
            continue
        multi += 1
        first = _toc_seglen(segs[0][0])
        rest = sorted(_toc_seglen(s[0]) for s in segs[1:])
        restmed = rest[len(rest) // 2]
        if first <= NF_TOC_TOP_MAX and first < restmed and restmed <= NF_TOC_REST_MAX:
            shorttop += 1
            if segs[0][1] is not None:
                tops.append(segs[0][1])
    spread = (max(tops) - min(tops)) if len(tops) >= 2 else 0.0
    if shorttop < NF_TOC_MINCOL:
        return None
    if len(tops) >= 2 and spread > max(NF_TOC_TOP_TOL * ph / 2.0, 40.0):
        return None
    return {'ncol': len(groups), 'multi': multi, 'shorttop': shorttop,
            'topspread': spread, 'pitch': pitch}


def nf_short_cols(rows, body, il, ir, it, ib, ph):
    """版心内**短列**行数(列带补带目标用, taskP2)。
    背景: nf_body_rows 只认「长行」(>= LONG_H_FRAC x 页高)作正文行, 但段尾/年号这类**短列**同样是
    真列(实测 wz7 源页 291 的 `三十歲。` 4 字列) —— 列带补不齐时相邻伪槽格被中点法拉宽 => 一格跨
    两列(见 nf_fill_bands 注释)。故补带目标 = 长行数 + 版心内短列数。
    口径: 非长行 + 单行(无 \\n) + x/y 中心落在版心内(外扩 2pt / 2% 页高); 书眉/页码在版心外不计。"""
    out = 0
    bset = set(id(r) for r in body)
    for r in rows:
        if id(r) in bset: continue
        if not r[4].strip() or '\n' in r[4]: continue
        if r[1] - r[0] <= 0: continue
        if (r[3] - r[2]) >= LONG_H_FRAC * ph: continue     # 长行已在 body 里(保险)
        cx = (r[0] + r[1]) / 2.0
        cy = (r[2] + r[3]) / 2.0
        if ((il - 2.0) * 2 <= cx <= (ir + 2.0) * 2
                and (it - 0.02 * ph) <= cy <= (ib + 0.02 * ph)):
            out += 1
    return out

def nf_fill_bands(ink, bands, il, ir, it, ib, need, cov_lo=0.04):
    """墨迹列带**补齐**(与 §1.99「残余墨迹列」同法): 把已检列带涂掉后, 在残余墨迹的 x 投影上按
    低阈值 cov_lo 补带, 直到条数不少于 need。
    为什么必须补: 段尾/詩行短列的墨迹覆盖度低于 cov=0.12 会漏检(实测 wz7 源页 1205: 真列 18 条
    只检到 15 条), 而列带数 < 正文行数时 page_puts 把配不上的行**整列丢掉**(实测该页丢 78 字:
    「遞畢酒…」44 字 + 「小優彈唱起來…」34 字)。
    taskP2 修正(短列证据 + 碎片合并): 原实现按「残余 run 的宽度」取前 need-len 条 —— 实测 wz7
    源页 291 的短列 `三十歲。`(4 字, 覆盖率 0.05) 被切成两段 7pt/2pt 的碎片, 宽度排在别的候选之后
    -> 该列补不出 -> 相邻伪槽格被中点法拉宽到 1.5-2 倍列距(50pt, 真列距 33) -> 一格跨两列 ->
    槽内 run 统计截半(hm 17.5 -> 9.5/6.0) -> `_metrics_finish` 把该列当小字注, 正文行无处配位。
    现改为: ①碎片先按 <= 4pt 间隙合并; ②只收「像文字列」的候选(_band_stats: run >= 3 条且
    中位字高 >= NF_FILL_HMIN —— 挡扫描噪点/页码/装饰; 不用「相对现有带字高」的比例: 窄带的 run
    会被横向截短, 比例判据会误杀宽字形列(实测 p291 大字年号列 hm 6.0 < 0.5x17.5 被错杀));
    ③按墨迹支撑(run 数 x 字高)排序取, 不再按宽度(宽度偏好会把别条真列挤掉)。
    run 数下限取 3(实测 wz7 源页 291 的正文候选 run 数 8-16, 噪点/页码 <= 2); 字高下限只挡碎墨:
    **窄带的 run 会被横向截短**(实测 p291 大字年号列 hm 5.5-9.5 < 正文字高 17.5), 故不能按字高比例筛。"""
    if len(bands) >= need: return bands
    import numpy as np
    il2, ir2 = int(il * 2), int(ir * 2)
    ya, yb = int((it + 2) * 2), int((ib - 2) * 2)
    if ir2 <= il2 or yb <= ya: return bands
    left = ink[ya:yb, il2:ir2].copy()
    for a, b in bands:
        xa = max(0, int(a * 2) - il2 - 2); xb = min(left.shape[1], int(b * 2) - il2 + 2)
        if xb > xa: left[:, xa:xb] = False
    # ① 碎片合并(<= 4pt 间隙; 原 gap=4px=2pt 会把同列的两段拆成两个候选)
    extra = [((il2 + a) / 2.0, (il2 + b + 1) / 2.0)
             for a, b in _runs(left.mean(axis=0) > cov_lo, 8) if b - a >= 12]
    if not extra: return bands
    # ② 文字列证据: run >= NF_FILL_NRUN 条且中位字高 >= NF_FILL_HMIN(绝对下限, 挡碎墨/噪点)。
    #   口径: 统计窗 = 候选带外扩 NF_FILL_PAD pt 后再夹回「未被现有列带占用」的残余掩膜 ——
    #   候选带常常窄于字形宽(实测 p291 年号大字的 6-17pt 带), 只按带内统计 run 会被横向截成
    #   <4pt 的碎条(实测 hm 6.0/nr 0 -> _band_stats 的 4pt 下限把它们全滤掉)。
    ok = []
    _pad = int(round(NF_FILL_PAD * 2))
    for a, b in extra:
        wa = max(0, int(a * 2) - il2 - _pad); wb = min(left.shape[1], int(b * 2) - il2 + _pad)
        if wb <= wa: continue
        rs = [r for r in _runs(left[:, wa:wb].any(axis=1), 1)]
        hs = sorted(r[1] - r[0] + 1 for r in rs)
        ok.append(((len(rs) * (hs[len(hs) // 2] / 2.0) if hs else 0.0), a, b, len(rs), (hs[len(hs) // 2] / 2.0 if hs else 0.0)))
    ok.sort(key=lambda t: -t[0])                                   # ③ 按带宽取(旧的偏好; 证据校验已挡噪点)
    return sorted(bands + [(a, b) for _s, a, b, _nr, _hm in ok
                           if _nr >= NF_FILL_NRUN and _hm >= NF_FILL_HMIN][:max(0, need - len(bands))])

def _big_hm(rs):
    """墨迹 run 序列 -> **字高**(pt): 取 run 高的 75 分位(不用中位、也不用「最大 run 的某一比例」)。
    为什么不用全 run 中位: 短列里标点占 run 数的比例极大 —— 实测「又曰：」的 4 条 run 里两条是
      冒号的两个点(4.5pt), 全中位 11.75pt 会把字号算成 13.6pt(真值 ~22)。
    为什么不用「>= 0.5 x 最大 run 高」: **并字长 run**(相邻两字相碰被并成一条, 高 ~2 个格)会把
      分母抬高 —— 实测源页 354 的「宿盡閒花…」列: 最大 run 48pt(萬萬并字) -> 门槛 24pt, 而真字
      run 是 22.5pt -> 门槛内只剩那条并字 run, 「字高」算成 48pt(真值 ~23)。
    75 分位的双重稳健: 标点碎片(小, 少数)与并字长 run(大, 少数)都落在下/上四分位之外。
    与「字 run 中位」在长列上等价(差 <= 2%); 短列上取到的就是真字高(实测 19.5 vs 真值 19.25)。"""
    hs = sorted(b - a for a, b in rs)
    if not hs:
        return 0.0
    return hs[(3 * len(hs)) // 4]


def _sb_ref_hm(ink, bands, it, ib):
    """本页「列带参照字高」= 已检列带里**像正文列**的(nr >= 5)字 run 墨高中位。
    短列的字高判据用**页内相对**口径(与 _ok_stat 的「本页字号 0.5-1.35 倍」同源),
    不引入绝对值: 换书/换字号都不用改常数。样本 < 2 条 -> 0(调用方跳过该条证据)。"""
    hs = []
    for a, b in bands:
        st = _band_stats(ink, a, b, it, ib)
        if st['nr'] >= 5:
            v = _big_hm(st['runs'])
            if v > 0:
                hs.append(v)
    return statistics.median(hs) if len(hs) >= 2 else 0.0


def _sb_band(ink, r, used, il, ir, it, ib, pitch, ref_h):
    """一条 OCR 短行 -> 窗内「文字列」墨迹带 (a, b, 字高) 或 None。见 §1.976。
    窗: x = OCR 行 x 心 ± NF_SB_PADX x 列距(夹回版心); y = OCR 行 y 带 ± NF_SB_PADY x 本行字步进
      —— OCR 行盒沿文本方向松紧不一(实测该页「又曰：」行盒 y 偏下 ~30pt), 外扩是必须的。
    三道判据(缺一不可):
      ① 候选 = 窗内 x 投影覆盖率 > NF_SB_COV 的 run(宽 >= 8pt 且 <= 1.6 x 列距);
      ② **密度**: 候选带自身墨迹包围盒内的墨迹填充率 >= NF_SB_DEN(挡碎墨/噪点斑);
      ③ **字证据**: 整版心量该带 -> run >= 2 且 字 run 墨高 ∈ NF_SB_RATIO x 本页列带参照字高
         (挡「页边装饰/表格线残段」这类有墨但不是字的墨迹)。
    与已用列带重叠的候选一律不收(不叠字)。多条候选通过时取**离 OCR x 心最近**的一条(按列框落位)。"""
    import numpy as np
    t = r[4]
    step = (r[3] - r[2]) / (2.0 * max(1, len(t)))          # OCR 行盒的每字步进(pt)
    cx = (r[0] + r[1]) / 4.0
    wa = max(il, cx - NF_SB_PADX * pitch)
    wb = min(ir, cx + NF_SB_PADX * pitch)
    ya = max(it + 2.0, r[2] / 2.0 - NF_SB_PADY * step)
    yb = min(ib - 2.0, r[3] / 2.0 + NF_SB_PADY * step)
    if wb - wa < 8.0 or yb - ya < 8.0:
        return None
    sub = ink[int(ya * 2):int(yb * 2), int(wa * 2):int(wb * 2)]
    if sub.size == 0:
        return None
    colc = sub.mean(axis=0)
    best = None
    for i0, i1 in _runs(colc > NF_SB_COV, 4):
        if i1 - i0 < 16:                                   # 窄于 8pt = 碎片
            continue
        a, b = wa + i0 / 2.0, wa + (i1 + 1) / 2.0
        if b - a > 1.6 * pitch:                            # 宽于 1.6 列距 = 两列粘连, 不是一条短列
            continue
        if any(a < b3 - 1.0 and a3 < b - 1.0 for a3, b3 in used):
            continue                                       # 与已用列带重叠 -> 不收(不叠字)
        yy = np.where(sub[:, i0:i1 + 1].any(axis=1))[0]
        if len(yy) < 4:
            continue
        dens = sub[yy[0]:yy[-1] + 1, i0:i1 + 1].mean()
        if dens < NF_SB_DEN:
            continue
        d = abs((a + b) / 2.0 - cx)
        if best is None or d < best[0]:
            best = (d, a, b)
    if best is None:
        return None
    _d, a, b = best
    st = _band_stats(ink, a, b, it, ib)
    if st['nr'] < 2:
        return None
    hb = _big_hm(st['runs'])
    if hb <= 0 or (ref_h > 0 and not (NF_SB_RATIO[0] * ref_h <= hb <= NF_SB_RATIO[1] * ref_h)):
        return None
    return a, b, hb


def nf_short_bands(pi, rows, body, bands, ink, il, ir, it, ib, ph):
    """版心内**短列**(非长行)的 OCR 列框 -> 补列带 [(a, b, 字高)]。见 §1.976。
    只认「有文本、单行、x/y 中心在版心内」的行(= nf_short_cols 的同一批行), 且每条都要过
    _sb_band 的三道判据 —— 即「短列必渲染」与「不把碎墨/噪点当正文」同时满足。"""
    out = []
    if not NF_SB_OWN:
        return out
    bset = set(id(r) for r in body)
    cand = []
    for r in rows:
        if id(r) in bset or not r[4].strip() or '\n' in r[4] or r[1] - r[0] <= 0:
            continue
        if (r[3] - r[2]) >= LONG_H_FRAC * ph:              # 长行已在 body 里(保险)
            continue
        cx = (r[0] + r[1]) / 2.0
        cy = (r[2] + r[3]) / 2.0
        if not ((il - 2.0) * 2 <= cx <= (ir + 2.0) * 2 and (it - 0.02 * ph) <= cy <= (ib + 0.02 * ph)):
            continue                                       # 书眉/页码在版心外, 不是列
        cand.append(r)
    if not cand:
        return out
    used = list(bands)
    pitch = _sb_pitch(bands, il, ir)
    ref_h = _sb_ref_hm(ink, bands, it, ib)
    for r in sorted(cand, key=lambda r: -r[0]):            # 阅读序(右->左), 与列带同序
        got = _sb_band(ink, r, used, il, ir, it, ib, pitch, ref_h)
        if not got:
            continue
        a, b, hb = got
        used.append((a, b))
        out.append((a, b, hb))
        if NF_SLOT_DBG:
            print('    [短列检出] p%d %-14s -> 墨迹列 x%.1f-%.1f 字高%.1f (参照%.1f)'
                  % (pi + 1, r[4][:14], a, b, hb, ref_h))
    return out


def _sb_pitch(bands, il, ir):
    """已检列带的列距中位(短列窗半径用); 样本不足 -> 版心宽 / N_COL_FRAME(与 §1.95 同源)。"""
    cs = sorted((a + b) / 2.0 for a, b in bands)
    ds = sorted(y - x for x, y in zip(cs, cs[1:]) if 8.0 < y - x < 0.35 * (ir - il))
    if len(ds) >= 3:
        p = _calib_med(ds)
        if 8.0 < p < 0.35 * (ir - il):
            return p
    return (ir - il) / max(2.0, float(N_COL_FRAME))


def nf_edges(bands):
    """墨迹列带 -> (伪槽格边界 edges, 列距中位 pitch)。边界 = 相邻带心中点, 首末外扩 pitch/2;
    格宽因此 = 该处列距(与 §1.98「槽 = 内框等分」同语义: 标点摆位的分母是格距)。
    taskCJ: pitch 取**最小的 60% 差值的中位**(稳健列距)。为什么不能用全体中位: 稀疏页只有
      两三列时, 一条「页边书眉列 <-> 正文列」的大空隙(实测 p149 709.2pt vs 真列距 44.6)
      会把中位整体抬高到 376.9 -> 首末槽外扩 pitch/2 = 188pt, 槽心偏 +83pt。取小差值中位后
      p149 = 44.6(真值)。
      只在稳健值**显著小于**全体中位(< 0.85 x)时替换: 正常页的列距抖动 ±5% 会让小差值中位
      比全体中位小 1-2%, 若无条件替换, 首末槽外缘(pitch/2)跟着漂 0.3-0.5pt -> 普通列的
      \\put x 不再逐位不变(验收硬指标)。0.85 只在「中位被 >= 1.5x 列距的空白污染」时才落上。
    VERT_NF_SLOT_ANCHOR=0 时完全回到旧口径(全体中位), 供 A/B 对照。"""
    cs = sorted((a + b) / 2.0 for a, b in bands)
    if len(cs) < NF_MIN_COL: return None, 0.0
    ds = sorted(y - x for x, y in zip(cs, cs[1:]) if y - x > 4.0)
    if len(ds) < (1 if len(cs) == 2 else 2): return None, 0.0   # 2 列: 唯一一段列距即可定槽
    p = statistics.median(ds)
    if NF_SLOT_ANCHOR:
        _pr = statistics.median(ds[:max(1, int(0.6 * len(ds)))])
        if _pr < 0.85 * p:
            p = _pr
    if p <= 0: return None, 0.0
    return [cs[0] - p / 2.0] + [(a + b) / 2.0 for a, b in zip(cs, cs[1:])] + [cs[-1] + p / 2.0], p

def nf_fit(pairs):
    """(OCR, 源图) 成对坐标(同序) -> (k, b, rms): x_ocr = k*x_src + b; 样本/间距不足 -> None。
    尺度用**相邻间距比的中位**(个别配对错位只是离群值, 不影响中位), 截距用中位差。"""
    if len(pairs) < 4: return None
    rs = [(o2 - o1) / (s2 - s1) for (o1, s1), (o2, s2) in zip(pairs, pairs[1:]) if (s2 - s1) > 8.0]
    if len(rs) < 3: return None
    k = statistics.median(rs)
    b = statistics.median([o - k * s for o, s in pairs])
    res = sorted(abs(o - (k * s + b)) for o, s in pairs)
    return k, b, res[len(res) // 2]

def nf_fit_align(cs, ro, slack=3):
    """源图列心 cs / OCR 行心 ro(各自按 x 升序; 条数可不等 —— 端部多一条残片/漏检) -> (k,b,rms,pairs)。
    做法: 枚举「相对错位 d」把两个序列错开对齐 —— 直接按下标配对在条数不等时会整段错位
    (实测 p1207: 17 带 vs 16 行, 按标配对累计漂移 3 列 -> 拟合出尺度 2.4 的假值)。
    择优判据(taskQ 遗留1 补, 见 NF_FIT_ALIGN_POS): 先看**映射后的绝对位置** —— 正文行心域应与
      墨迹列心域相合(两端失配之和最小者优), 残差中位只作同分次序。为什么残差单独不够: 竖排书的
      「行距」与比它小一个尺度的「列距」在源图/OCR 帧两侧是**同一把梳子的等比放大**(实测 p30
      行距 109px = 1.2224 x 列距 89.5px) -> 任何「整列错位」的解都能把残差压到 1-2px(梳状简并);
      实测 245 页里只有 52 页「最优残差解 = 最优位置解」, 而残差最优解的失配中位 348px(≈4 列)。
      错位的解不是纸面上的小误差: 伪版心的 x 窗直接由映射后的正文行给出, 窗整体搬走会把真列挡在
      窗外(实测 p30 右移 2 列 -> 左边 2 列不在窗内 -> 3 行无处配位 -> 整页少 88 字)。
    尺度/残差合理性由调用方按 NF_FIT_K / NF_FIT_RES 判(这里只给候选)。配对序 = 升序。"""
    best = None
    best_key = None
    for d in range(-slack, slack + 1):
        pr = [(ro[i + d], cs[i]) for i in range(len(cs)) if 0 <= i + d < len(ro)]
        if len(pr) < 4: continue
        f = nf_fit(pr)
        if not f: continue
        k, b, rms = f
        if not (NF_FIT_K[0] <= k <= NF_FIT_K[1]): continue
        if not NF_FIT_ALIGN_POS:
            # 修前口径(逐位复现, 供 A/B 对照): 残差中位优先(1e-9 内同分) -> 再取配对数多者
            if (best is None or rms < best[2] - 1e-9
                    or (rms < best[2] + 1e-9 and len(pr) > len(best[3]))):
                best = (k, b, rms, pr)
            continue
        # 位置失配(px): 映射后行心域 vs 列心域(两端之和)
        mis = abs((min(ro) - b) / k - min(cs)) + abs((max(ro) - b) / k - max(cs))
        key = (round(mis, 1), round(rms, 2), -len(pr))
        if best_key is None or key < best_key:
            best_key, best = key, (k, b, rms, pr)
    return best

_nf_done = set()                # 已标定回源图坐标系的页(避免重复标定)
_nf_fix_stat = {'try': 0, 'ok': 0, 'rej': {}, 'pages': {}}   # taskQ: 标定命中率统计(修前/修后对照)
_nf_fix_aff = {}                # pi -> (kx, bx, ky, by) **未取整**仿射(taskCH: 目录分支要把原始行
                                #   映射到同一坐标系; _nf_fix_stat 里的值按 4/2 位取整, 直接用会差 0.04pt,
                                #   目录分支的特殊行签名对不上 -> p45 标题被画两遍)

def _nf_rej(pi, tag, why):
    """标定被拒: 记一笔分类计数(只统计/打印用, 不改任何判据)。"""
    s = _nf_fix_stat
    s['rej'][tag] = s['rej'].get(tag, 0) + 1
    s['pages'][pi] = {'ok': False, 'tag': tag, 'why': why}
    return None, why

def nf_ocr2src(k, b, v):
    """OCR 坐标 -> 源图坐标(2x px 口径, 与 all_rows 同单位)。
    (k, b) 由 nf_fit 拟合得到, 其语义是 **OCR = k x 源图 + b**(尺度 = 相邻间距比中位, 截距 = 中位差);
    故回源图必须**反解** v_src = (v_ocr - b) / k。
    taskQ 遗留1: 修前此处写成 k x v + b —— 把「OCR->源图」的仿射又**同向**作用在 OCR 坐标上
      (k 被平方, 截距随之翻倍), 映射后的 x 域因此普遍落在纸外 -> 被下面的「映射后正文 x 不符」
      拦下(实测 248/250 页) -> 整条标定路径休眠(300 页样本里真正用上「按本书标定」的只有 2 页:
      源页 182/214 —— 它们的错向映射恰好落回原范围, 属巧合而非该路径在正常工作)。
    开关 VERT_NF_FIX_INV=0 回到修前行为(只作 A/B 对照用)。"""
    if NF_FIX_INV: return (v - b) / k
    return k * v + b

def _nf_fix_page(pi, k, body, bands, ink, it, ib):
    """逐页 OCR 帧 -> 源图坐标系(仿射)。返回 (新 rows, 说明) 或 (None, 原因)。
    尺度/残差不过关 -> 不采纳(宁可留原坐标: 错标定会把整页列搬出页外)。"""
    _nf_fix_stat['try'] += 1
    st = [_band_stats(ink, a, b, it, ib) for a, b in bands]
    ok = sorted([(a + b) / 2.0, s] for (a, b), s in zip(bands, st)
                if s['top'] is not None and s['step'] > 0)            # 源图: 墨迹列(左->右)
    if len(ok) < 4: return _nf_rej(pi, '列带统计不足', '列带统计不足 %d' % len(ok))
    cs = [c for c, _s in ok]
    ro = sorted(body, key=lambda r: (r[0] + r[1]) / 2.0)              # OCR: 行心 左->右
    if abs(len(cs) - len(ro)) > max(1, 0.35 * max(len(cs), len(ro))):
        return _nf_rej(pi, '条数差太大', '列带/行 条数差太大 %d vs %d' % (len(cs), len(ro)))
    # 单位: 墨迹侧是 pt, OCR 侧是 2x px -> 统一到 px(与行坐标同单位, 反解后仍回到 px 口径)
    cs2 = [c * 2.0 for c in cs]
    pitch = statistics.median([y - x for x, y in zip(cs2, cs2[1:])]) if len(cs2) > 1 else 0.0
    fx = nf_fit_align(cs2, [(r[0] + r[1]) / 2.0 for r in ro])
    if not fx: return _nf_rej(pi, 'x 样本不足', 'x 样本不足/尺度不合理')
    kx, bx, rx, pr = fx
    if pitch <= 0 or rx > NF_FIT_RES * pitch:
        return _nf_rej(pi, 'x 残差', 'x 尺度%.3f 残差%.1fpx(>%.1f) 不可信' % (kx, rx, NF_FIT_RES * pitch))
    # y: 尺度 = 字步进比的中位(行高/字数 ÷ 墨迹字步进); 截距 = 行心/列心差的中位
    #   (配对两侧同为「2x px」口径: OCR 行心就是 2x px; 源侧用 (top+bot) = 2 x 列心(pt) 即 2x px)
    smap = dict((round(c, 3), s) for c, s in ok)
    rmap = dict((round((r[0] + r[1]) / 2.0, 3), r) for r in ro)
    bys, yy = [], []
    for o, c in pr:
        r = rmap[round(o, 3)]; s = smap[round(c / 2.0, 3)]
        stp = (r[3] - r[2]) / max(1, len(r[4]))
        if s['step'] > 0 and stp > 0: bys.append(stp / (s['step'] * 2.0))
        yy.append(((r[2] + r[3]) / 2.0, (s['top'] + s['bot'])))
    if len(bys) < 4: return _nf_rej(pi, 'y 样本不足', 'y 样本不足')
    ky = statistics.median(bys)
    if not (NF_FIT_K[0] <= ky <= NF_FIT_K[1]): return _nf_rej(pi, 'y 尺度', 'y 尺度%.3f 不可信' % ky)
    by = statistics.median([o - ky * s for o, s in yy])
    n = len(pr)
    # 采纳前再验一次「映射后正文落点」: 正文 x 带必须落在墨迹列带附近且在页幅内 ——
    #   残差小但整体错位的拟合(配对漂移 1-2 列)会把整页列搬到页外(实测 p1709 映射后 x -516px)。
    pw, ph = _nf_page_px(pi)
    c0 = min(nf_ocr2src(kx, bx, r[0]) for r in body)
    c1 = max(nf_ocr2src(kx, bx, r[1]) for r in body)
    b0, b1 = bands[0][0] * 2.0, bands[-1][1] * 2.0
    if not (-0.02 * pw <= c0 and c1 <= 1.02 * pw
            and abs(c0 - b0) <= 0.25 * pw and abs(c1 - b1) <= 0.25 * pw):
        return _nf_rej(pi, '映射后 x 不符', '映射后正文 x %.0f-%.0f 与墨迹列带 %.0f-%.0f 不符'
                       % (c0, c1, b0, b1))
    out = []
    for x0, x1, y0, y1, t in all_rows[k]:
        out.append((nf_ocr2src(kx, bx, x0), nf_ocr2src(kx, bx, x1),
                    nf_ocr2src(ky, by, y0), nf_ocr2src(ky, by, y1), t))
    _nf_fix_stat['ok'] += 1
    _nf_fix_stat['pages'][pi] = {'ok': True, 'kx': round(kx, 4), 'bx': round(bx, 2),
                                 'ky': round(ky, 4), 'by': round(by, 2),
                                 'rms': round(rx, 2), 'pitch': round(pitch, 2), 'n': n}
    _nf_fix_aff[pi] = (kx, bx, ky, by)
    return out, 'kx%.3f bx%+.1f 残差%.1fpx ky%.3f by%+.1f (配 %d 列)' % (kx, bx, rx, ky, by, n)

def _nf_clamp_box(il, ir, it, ib, pw, ph):
    """伪版心夹回纸幅(taskP2)。OCR 帧未标定的页其行盒可整段越出纸张(实测源页 182: 行盒 y -138.8,
    纸高 1323 -> 墨带/槽统计全在纸外 -> 基准否决 -> 兜底路径把 81 条 span 排到页外 31pt)。
    返回夹取后的 (il, ir, it, ib); 与纸不相交(夹后高/宽 < 8pt)时返回 None。"""
    il = min(max(il, 0.0), pw); ir = min(max(ir, 0.0), pw)
    it = min(max(it, 0.0), ph); ib = min(max(ib, 0.0), ph)
    if ir - il < 8.0 or ib - it < 8.0: return None
    return il, ir, it, ib

def nf_frame(pi, k):
    """无版框页 -> 伪版心 dict(键同 frame_geom, 另加 virtual/cells/page/pitch) 或 None。
    顺带把本页 OCR 坐标标定回源图坐标系(每页一次, 原地改 all_rows[k])。结果按页缓存。"""
    if pi in _nf_cache: return _nf_cache[pi]
    _nf_cache[pi] = _nf_frame(pi, k)
    return _nf_cache[pi]

def _nf_after_fix(pi, fixed, box, pw, ph, ink, pitch0):
    """标定落地(遗留1): 行换到源图坐标系 -> 重算伪版心窗 -> 重算列带。
    ① 窗: 无印刷框时 = 标定后正文行盒的并集, 再**外扩一个列距**(NF_FIT_PAD × 标定前列距)后夹回纸幅
       —— 行盒并集不是墨迹列并集, 边界列会探出窗缘(实测 p254 左端列 43.0-59.0 在窗外 14.6pt),
       窗一窄该列整条检不出 -> 行多于槽 -> 整列不渲染(该页少 95 字 / p130 少 84 字)。
    ② 列带: 与标定前**同口径**(检测 + 短列补齐) —— 只重算检测会白丢补齐出来的列(实测 p254:
       标定前 原带 15 + 补 1 = 16, 只重算检测 -> 14)。
    返回 (rows, body, il, ir, it, ib, bands); 标定后撑不起伪槽格(正文行/列带 < NF_MIN_COL) -> None。
    注: §1.976 的短列**不在这里**补 —— 它要在「页坐标/版心定稿之后」补(见 _nf_frame 末尾),
      否则会混进 _nf_fix_page 的「列带 ↔ 行」配对里把仿射拟合带偏(实测该页 x 尺度 1.416)。"""
    rows = fixed
    body = nf_body_rows(rows, ph)
    if len(body) < NF_MIN_COL: return None
    if box:
        il, ir, it, ib = box
    else:
        il = min(r[0] for r in body) / 2.0; ir = max(r[1] for r in body) / 2.0
        it = min(r[2] for r in body) / 2.0; ib = max(r[3] for r in body) / 2.0
        # 与 _nf_frame 同口径: x 域并上「y 落在正文带内」的所有行(含大字号标题)。
        #   漏了这一处, 标定后重算版心会按 body±pad 覆盖回去 —— 实测 p43 凡例标题
        #   x749.9-804.4 被 body±pad 的 742.9 右缘挡住, 标题整行不渲染(该页少 2 字)。
        if NF_FRAME_ALLX:
            _inner = [r for r in rows
                      if r[2] / 2.0 >= it - 1.0 and r[3] / 2.0 <= ib + 1.0]
            if _inner:
                il = min(il, min(r[0] for r in _inner) / 2.0)
                ir = max(ir, max(r[1] for r in _inner) / 2.0)
        pad = NF_FIT_PAD * pitch0 if NF_FIT_LAND else 0.0
        cb = _nf_clamp_box(il - pad, ir + pad, it - pad, ib + pad, pw / 2.0, ph / 2.0)
        if cb is None: return None
        il, ir, it, ib = cb
    bands = _ink_bands(ink, il, ir, it, ib, cov=NF_COV)
    if NF_FIT_LAND:                       # 列带与标定前同口径(检测 + 短列补齐)
        _nsc = nf_short_cols(rows, body, il, ir, it, ib, ph)
        if NF_SLOT_DBG:
            print('    [补带诊断] p%d 标定后 原带 %d + 长行 %d + 短列 %d -> need %d'
                  % (pi + 1, len(bands), len(body), _nsc, len(body) + _nsc))
        bands = nf_fill_bands(ink, bands, il, ir, it, ib, len(body) + _nsc)
    if len(bands) < NF_MIN_COL: return None
    return rows, body, il, ir, it, ib, bands

def _nf_frame(pi, k):
    pw, ph = _nf_page_px(pi)
    ink = _nf_ink(pi)                       # 自适应阈值(与标定/渲染同口径)
    rows = all_rows.get(k)
    if not rows: return None
    raw_rows = rows                        # taskCH: 目录判定/独立路径用**未 join** 的原始行
    if os.environ.get('VERT_NF_ROWS_DBG') == str(pi + 1):
        print('    [行清单] p%d nf_join_rows 后 %d 行:' % (pi + 1, len(rows)))
        for _i, _r in enumerate(rows):
            print('       [%2d] x%6.1f-%6.1f y%6.1f-%6.1f len%d  %s'
                  % (_i, _r[0] / 2.0, _r[1] / 2.0, _r[2] / 2.0, _r[3] / 2.0,
                     len(str(_r[4])) if len(_r) > 4 else -1,
                     str(_r[4]).replace(chr(10), '|')[:30] if len(_r) > 4 else ''))
    rows = nf_join_rows(rows)               # OCR 插的换行拼回(只 NF: 见 nf_join_rows)
    all_rows[k] = rows
    body = nf_body_rows(rows, ph)
    if len(body) < NF_MIN_COL: return None
    # ② 伪版心: 本页有印刷版框(实测框线)就用**框内缘**(印刷常数, 且列高被框住 -> 不越页);
    #   没有(正文页)才退回「正文 OCR 行盒并集」(与原路径一致)。
    box = _nf_box(pi)
    if box:
        il, ir, it, ib = box
    else:
        il = min(r[0] for r in body) / 2.0; ir = max(r[1] for r in body) / 2.0
        it = min(r[2] for r in body) / 2.0; ib = max(r[3] for r in body) / 2.0
        # taskCC: 版心 x 域并上「y 落在正文带内」的所有行 —— 大字号标题(凡例/章回名/目录标题)
        #   被 nf_body_rows 判成特殊行后从 body 摘出, 若只按 body 求 x 域, 标题会落在版心之外,
        #   反过来又被「页边带」判据丢弃(实测 p43 凡例标题 x750-804 输给版心右缘 742.9, 少 2 字)。
        #   y 域不动: 书眉/页码在 y 带之外, 不会被这条并进来。
        if NF_FRAME_ALLX:
            _inner = [r for r in rows
                      if r[2] / 2.0 >= it - 1.0 and r[3] / 2.0 <= ib + 1.0]
            if _inner:
                _l = min(r[0] for r in _inner) / 2.0
                _r2 = max(r[1] for r in _inner) / 2.0
                if _l < il - 0.5 or _r2 > ir + 0.5:
                    print('    [伪版心扩x] p%d x %.1f-%.1f -> %.1f-%.1f (并入 y 带内行 %d 条)'
                          % (pi + 1, il, ir, min(il, _l), max(ir, _r2), len(_inner)))
                il, ir = min(il, _l), max(ir, _r2)
        # taskP2 护栏: 伪版心**夹回纸幅**(见 _nf_clamp_box 注释)
        _cb = _nf_clamp_box(il, ir, it, ib, pw / 2.0, ph / 2.0)
        if _cb is None: return None
        il, ir, it, ib = _cb
    bands = _ink_bands(ink, il, ir, it, ib, cov=NF_COV)
    _nsc = nf_short_cols(rows, body, il, ir, it, ib, ph)
    if NF_SLOT_DBG:
        print('    [补带诊断] p%d 原带 %d + 长行 %d + 短列 %d -> need %d'
              % (pi + 1, len(bands), len(body), _nsc, len(body) + _nsc))
    bands = nf_fill_bands(ink, bands, il, ir, it, ib,
                          len(body) + _nsc)   # 短列补齐(否则整列被丢)
    if len(bands) < NF_MIN_COL: return None
    fixed = None
    if pi not in _nf_done:                       # ① OCR 坐标 -> 源图坐标系(只做一次)
        _nf_done.add(pi)
        _cs0 = [(a + b) / 2.0 for a, b in bands]         # 标定前列距(pt): 窗缘外扩量的基准
        _pitch0 = statistics.median([y - x for x, y in zip(_cs0, _cs0[1:])]) if len(_cs0) > 1 else 0.0
        fixed, why = _nf_fix_page(pi, k, body, bands, ink, it, ib)
        if fixed:
            _st = _nf_after_fix(pi, fixed, box, pw, ph, ink, _pitch0)
            if _st is None and not NF_FIT_LAND:
                return None                       # 修前口径: 标定落地失败 -> 本页不建伪槽格
            if _st is None:
                # 标定落地后本页撑不起伪槽格 -> **弃用本页标定**(与「尺度/残差不过关」同列, 保留原
                #   坐标与标定前的窗/列带, 该页行为与修前一致): 实测源页 214(小开本残页)的列只占页高
                #   8.9% < 长列门限 12%, 未标定时靠 OCR 帧的 1.27 倍拉伸才勉强算长列 —— 标定后它们
                #   如实变短, 伪槽格路径本就不适用; 若不弃用则该页掉进 v2 流式(62 -> 22 字)。
                _nf_fix_stat['ok'] -= 1
                _r, _why2 = _nf_rej(pi, '标定后撑不起伪槽格',
                                    '标定后正文行/列带不足(长列判据按源图尺度量)')
                print('    [无框-坐标] p%d 标定弃用(%s) -> 用原坐标' % (pi + 1, _why2))
                fixed, why = None, None
            else:
                rows, body, il, ir, it, ib, bands = _st
                all_rows[k] = rows
        elif why:
            print('    [无框-坐标] p%d OCR 帧未标定(%s) -> 用原坐标' % (pi + 1, why))
    # §1.976 短列(taskS): 在「本页坐标系 + 版心」定稿之后补 —— 短列的列带**不进** _nf_fix_page
    #   的「列带 ↔ 行」配对(那里的配对是长行对长列, 混进 3 字列会把仿射尺度拟合带偏:
    #   实测源页 354 的 x 尺度会被拟成 1.416(真值 1.332) -> 整页映射后越界被拒 -> 掉回未标定)。
    _sb = nf_short_bands(pi, rows, body, bands, ink, il, ir, it, ib, ph)
    bands = bands + [(a, b) for a, b, _h in _sb]
    if NF_SLOT_DBG:
        print('    [列带诊断] p%d 列带 %d: %s' % (
            pi + 1, len(bands), ' | '.join('%.1f-%.1f' % b for b in sorted(bands))))
    edges, pitch = nf_edges(bands)
    if not edges: return None
    # taskCH) 目录页判定: 在 nf_join_rows 之后仍用**原始行**判(结构信息没被合并掉)。
    #   命中 -> g['toc']=True + g['toc_rows'](独立路径的输入); 未命中 -> 两项都不影响任何既有路径。
    _tocst = nf_toc_shape(raw_rows, pitch, ph) if NF_TOC_BRANCH else None
    _toc_rows = None
    if _tocst:
        _toc_rows = raw_rows
        if fixed:                           # 本页 OCR 帧已标定回源图坐标系 -> 原始行同法映射
            _aff = _nf_fix_aff.get(pi)
            if _aff:
                _kx, _bx, _ky, _by = _aff
                _toc_rows = [(nf_ocr2src(_kx, _bx, r[0]), nf_ocr2src(_kx, _bx, r[1]),
                              nf_ocr2src(_ky, _by, r[2]), nf_ocr2src(_ky, _by, r[3]), r[4])
                             for r in raw_rows]
        print('    [目录分支] p%d 列%d 形态列%d 首层跨%.1f 列距%.1f -> 独立路径(原始行 %d, 标定%s)'
              % (pi + 1, _tocst['ncol'], _tocst['shorttop'], _tocst['topspread'],
                 _tocst['pitch'], len(_toc_rows), '是' if _toc_rows is not raw_rows else '否'))
    elif os.environ.get('VERT_NF_TOC_DBG'):
        print('    [目录形态] p%d 列距%.1f -> 非目录页' % (pi + 1, pitch))
    return {'in_l': il, 'in_r': ir, 'in_t': it, 'in_b': ib, 'in_th': 0.0, 'ib_th': 0.0,
            'out_t': None, 'out_t_th': V_FRAME_TH, 'out_b': None, 'out_b_th': V_FRAME_TH,
            'out_l': None, 'out_l_th': V_FRAME_TH, 'out_r': None, 'out_r_th': V_FRAME_TH,
            'thin': [], 'pitch': pitch, 'hx_l': il, 'hx_r': ir, 'bar': (0.0, 0.0),
            'virtual': True, 'cells': edges, 'page_px': (pw, ph), 'fixed': bool(fixed),
            # taskCJ: 槽窗口锚定用 —— 最终列带按带心升序(= nf_edges 里 cs 的顺序, 与槽一一对应)。
            #   bands 里含 nf_fill_bands 补齐列 + nf_short_bands 短列, 顺序不定, 故此处显式排序。
            'bands': sorted(bands, key=lambda b: b[0] + b[1]),
            'box': box, 'rows': body, 'sb': _sb,
            'toc': bool(_tocst), 'toc_rows': _toc_rows, 'toc_stat': _tocst}

# ---------- 1.98) 框驱动排版基准(逐页版框/槽格/墨带/字号) ----------
# 背景(实测): v2 的排版基准取自 OCR 盒的全局中位(字号 34.4/列距 47.6/列高 863.7), 但 OCR 坐标
#   逐页有 ~10% 量级的伸缩 + 相位漂移(实测 p100: OCR 相邻列 x0 差 48.0pt vs 源书版框实测 43.5pt;
#   同一页 y 方向同比例拉伸, 列长比墨迹长 10%)。后果: 列长参差(列底极差 80pt)、列区不贴框
#   (p100 左侧空 36pt/右侧空 18pt)、边注(OCR x 偏右)挤进版心。
# 正解: 几何全部以「源图墨迹实测」为准 ——
#   ① 内框(顶/底/左/右): frame_geom(§1.95, 逐页独立, 处理奇偶页交替: 奇页内框顶 290/右 568,
#      偶页 315.5/552 —— 扫描装订错位, 全书实测奇偶中位差 25.5pt 垂直/18.3pt 水平);
#   ② 槽格: 内框 12 等分(界行线是印版常数栅格, 实测 43.5pt; 检测条数 ±1 的 24 页以等分为准);
#   ③ 墨带: 正文槽首/末 run 的上下缘中位 = 该页正文墨迹带(相对内框内缩实测 顶 14.5pt/底 14.0pt,
#      全书 226 页 p10-p90 波动 14.0-15.7, 故用逐页实测而非常数);
#   ④ 字号 = 正文槽 run 高中位 / INK_RATIO; 步进上限 = run 间距中位(源书常规字距);
#   ⑤ 正文行(OCR 文本) ↔ 正文槽: 按「字数」单调动态规划对齐 —— OCR 会漏掉短列(本页首列常是
#      上页段落的续尾, h<300 被旧判据丢弃), 位置法不可靠(OCR x 漂移), 字数法对漏列免疫。
# 渲染: 逐字 \put(eso-pic 带星版) —— 实测(tate 下 FG 图内的文本沿页 x 方向横排, 所以必须逐字定位);
#   put 坐标标定(probe_bp 实测): 列墨迹顶/底与目标偏差 0.00pt, 需 pt->bp 换算 1.00375。
#   逐字 \put 不占版心流(每页正文只是 \null) -> 沿用旧「列数超容量多出页」的隐患一并消除。
INK_RATIO = float(os.environ.get('VERT_INK_RATIO') or 0.88)   # 单字墨高/字号(中位; §1.956 按当前字体探针渲染标定)
INK_ASC = float(os.environ.get('VERT_INK_ASC') or 0.94)       # 墨迹顶距基线 = INK_ASC×字号(其余为基线下的墨迹下沉)
PT2BP = 1.00375         # TeX pt -> PDF bp 换算(dvipdfmx 按 72.27/72; 实测 put y=1000 落 996.3bp)
V_FRAME_LAYOUT = os.environ.get('VERT_FRAME_LAYOUT', '1') not in ('0', 'false', 'False')

def _slot_runs(ink, x0, x1, y0, y1, min_h=4.0, row_floor=1):
    """槽内墨迹 y 投影 -> 字 run [(top, bot)] pt(页顶向下)。
    窗口内缩(实测标定): x 两端 3.5pt —— 界行线组宽可达 2pt, 内缩 2.5pt 时格线偏移 0.6pt 就会
      把整条线的墨带进窗口(实测 p99 右起 3 槽 run 数 23->18, 首 run 变成 290-364 = 格线+首字粘连);
      y 两端 2pt —— 去除版框上下横线(内线组在 [in_t, in_t+th] / [in_b, in_b+th], 下内线取组顶)。
    gap=1px 让同一字的分离笔画(如「二」「門」)并回一个字。
    min_h: run 高下限(pt), 默认 4pt 剔碎片; 取槽顶/槽底时传 0(碎片另按 §1.98 ③ 贴回字 run)。
    row_floor(taskP, 只无版框路径用): 该行墨迹像素数下限 —— 槽窗口里若有**印刷细线**(界行线/
      框线: 宽 1-6px, 但贯穿整列), `.any(axis=1)` 会让它把整列的字 run 连成一条(实测 wz7 p5:
      列内混入一条 3pt 宽的残线 -> 11 个字的 run 合成 1 条 1095pt, 字号被算成 222pt 而非 107pt,
      触发基准否决 -> 兜底 -> 列底越出页幅)。按行计数就能把它滤掉(线只贡献 2-6px, 而字的横画
      跨度是字宽的 0.3-1 倍)。非 NF 路径传默认 1(逐位不变)。"""
    xa = int((x0 + 3.5) * 2); xb = int((x1 - 3.5) * 2)
    ya = int((y0 + 2.0) * 2); yb = int((y1 - 2.0) * 2)
    if xb <= xa or yb <= ya: return []
    m = (ink[ya:yb, xa:xb].sum(axis=1) >= row_floor) if row_floor > 1 else ink[ya:yb, xa:xb].any(axis=1)
    out = []
    for a, b in _runs(m, 1):
        if b - a < 2 * min_h: continue               # 噪声/标点碎片
        out.append(((ya + a) / 2.0, (ya + b + 1) / 2.0))
    return out

_metrics_cache = {}
def _ink_bands(ink, il, ir, it, ib, cov=0.25):
    """内框内墨迹 x 投影 -> 列带 [(x0,x1)] pt(左->右)。cov=0.25: 满列墨迹覆盖 0.5-0.8;
    段尾短列覆盖低至 0.1 会漏检 —— 栅格相位靠多数列定, 漏 1-2 条不影响。"""
    xa, xb = int(il * 2), int(ir * 2)
    ya, yb = int((it + 2) * 2), int((ib - 2) * 2)
    if xb <= xa or yb <= ya: return []
    colc = ink[ya:yb, xa:xb].mean(axis=0)
    out = []
    for a, b in _runs(colc > cov, 4):
        if b - a < 16: continue                       # 窄于 8pt = 碎片
        out.append(((xa + a) / 2.0, (xa + b + 1) / 2.0))
    return out

def _grid_from_bands(bands, il, ir, n=None):
    """墨迹列带 -> 等距槽格 (首线, 列距) 或 None。
    为什么不用版框检测出的内框直接 12 等分: 界行线淡的页(实测 p32, 全书 3 页)版框兜底栅格会把
    内框宽算成 511pt(真值 522), 12 等分后左端偏差 6pt -> 槽切到列缝上(run 数 25 -> 11)。
    墨迹列带是「字」本身, 不受版框检测误差影响。
    n: 列数; 缺省用模块级 N_COL_FRAME(§1.955 标定) —— 同样必须在此解析, 不能写成默认参数。"""
    if n is None:
        n = N_COL_FRAME
    cs = sorted((a + b) / 2.0 for a, b in bands)
    if len(cs) < 6: return None
    ds = [b - a for a, b in zip(cs, cs[1:]) if V_BAND_SP_LO < b - a < V_BAND_SP_HI]
    if len(ds) < 4: return None
    p = statistics.median(ds)
    # 列距合法性窗(原 36-50pt)按页幅比例(§1.95); 书自身的「列距 = 内框宽÷列数」一致性由下一条保证
    if not (V_P_LO <= p <= V_P_HI) or len(cs) - 1 <= n - 3: return None
    ks = [round((c - il) / p - 0.5) for c in cs]
    e = statistics.median([c - p * (k + 0.5) for c, k in zip(cs, ks)])
    if not (0.9 * (ir - il) <= n * p <= 1.1 * (ir - il)): return None
    return e, p

# 引號族(中文侧字形; 竖排形态由 §1.0c 的 VERT_FORMS 映射)。定义在此是因为 §1.976 的 _trim_marks
#   ④ 要用它(§1.997 的引號判别也复用同一常量): 文本首/末字是引號 -> 列首/列尾那条小墨就是该字自己的墨。
QFIX_QFAM = set('「」『』')

def _trim_marks(keep, t, hbig, step):
    """槽首/槽尾的**引號类小墨**剔除 -> (字列顶, 字列底)(只 NF 路径用, 见 _slots_of_edges)。
    实测 wz7 源页 354(诗引號): 引號「 是 9.5pt 的小墨, 紧贴首字上方 7pt(0.27 步进), 而正文字
      run 是 22.5pt —— 它把槽顶抬高一格(该槽实测 t=330.5 而首字墨顶 347.0), 后果两处:
      ① 列位整列上移 0.65 格(渲染 T 取下缘锚点); ② 空隙 DP 的锚点偏一格 -> 空格被插到错的字间
      (实测该列插到「如|歸」之间, 源书是插在「，|不」之间)。
    判据(三条同时成立才剔 —— 挡「一二三」这类**本身墨就小**的正文字):
      ① 该 run 高 < 0.6 x 字 run 中位;
      ② 与邻字 run 的间隙 < 0.5 x 步进(引號在源书里是贴字的小墨, 不是一个整格);
      ③ **文本侧反证**: 本节首/末字不是挤格标点 —— 标点本来就小(实测末字「，」8pt), 不能当引號剔;
         若文本首/末字真是标点(如列末「：」), 该 run 就是那个标点, 保留。
      ④ taskU-A 补(**引號字**): 文本首/末字是 引號「」『』 时**同样保留** —— 这条小墨就是该引號
         自己的墨(竖排引號占一整格、墨是直角细笔画), 剔了会把整列顶/底挪一格(taskU 用户反馈
         「﹁ 占字格 → 不齐」的一半来源)。OCR 把引號**读丢**的列(文本首字是真汉字)仍按 ①-③ 剔。
     尾端只有「」这类闭引號会被剔(实测列 585.5 末 run 812-822.5 是 」, 前一条 789.5 是「，」)。"""
    tp = keep[0][0]; bt = keep[-1][1]
    if len(keep) < 2 or hbig <= 0 or step <= 0:
        return tp, bt
    if (t and t[0] not in PUNCT_HANG and t[0] not in QFIX_QFAM
            and (keep[0][1] - keep[0][0]) < 0.6 * hbig
            and (keep[1][0] - keep[0][1]) < 0.5 * step
            and (keep[1][1] - keep[1][0]) >= 0.6 * hbig):
        tp = keep[1][0]
    if (t and t[-1] not in PUNCT_HANG and t[-1] not in QFIX_QFAM
            and (keep[-1][1] - keep[-1][0]) < 0.6 * hbig
            and (keep[-1][0] - keep[-2][1]) < 0.5 * step
            and (keep[-2][1] - keep[-2][0]) >= 0.6 * hbig):
        bt = keep[-2][1]
    return tp, bt


def _anchor_wins(edges, anchors=None, pitch=0.0):
    """槽格边界 -> 逐槽 x 窗口 [(e0,e1)]; taskCJ 的「病态槽锚定」在这里(纯函数, 便于单测)。
    判据 = 槽被拉宽(宽 > 1.25 x pitch)且槽中点偏离本列带心 > 0.25 x pitch; 命中后窗口收到
    「本列带心 ± 半列距」, 两端仍不小于本列墨迹带 ± 4pt(不切墨)。普通槽判据不成立 ->
    窗口与 edges 逐位相同。"""
    n = len(edges) - 1
    win = [(edges[i], edges[i + 1]) for i in range(n)]
    if anchors is not None and pitch > 0 and len(anchors) == n:
        for i, (a0, a1) in enumerate(anchors):
            e0, e1 = win[i]
            c = (a0 + a1) / 2.0
            if (e1 - e0) > 1.25 * pitch and abs((e0 + e1) / 2.0 - c) > 0.25 * pitch:
                win[i] = (min(c - pitch / 2.0, a0 - 4.0),
                          max(c + pitch / 2.0, a1 + 4.0))
    return win


def _slots_of_edges(ink, dink, edges, it, ib, row_frac=0.0, anchors=None, pitch=0.0):
    """槽格边界 edges(pt) -> 逐槽统计 [{x0,x1,nr,hm,step,runs,top,bot}] 或 None。
    框驱动槽格(§1.98: 内框等分/墨迹列带栅格)与无框伪槽格(§1.975: 墨迹列带)共用同一套口径,
    保证两种来源的槽统计可比(XSCALE/PUNCT_* 的源侧样本即取自这里)。
    row_frac: >0 时按「槽宽 x row_frac」给 _slot_runs 的行墨迹下限(滤印刷细线, 只无版框路径传)。
    anchors/pitch(taskCJ, 只无版框路径传): 本列墨迹带 [(x0,x1)] 与稳健列距。锚定判据 =
      槽被拉宽(宽 > 1.25 x pitch)且槽中点偏离本列带心 > 0.25 x pitch —— 此时槽心被一侧
      空白按 (G_R-G_L)/4 拉偏(见 nf_edges 与 docs/vert_taskCJ_diagnosis.md §3)。命中后窗口
      收到「本列带心 ± 半列距」, 两端仍不小于本列带缘 ± 4pt(不切墨)。普通槽两条判据都
      不成立 -> x0/x1 与旧口径逐位相同。"""
    n = len(edges) - 1
    win = _anchor_wins(edges, anchors, pitch)
    _rf = [max(1, int(round(row_frac * (win[i][1] - win[i][0]) * 2))) if row_frac > 0 else 1
           for i in range(n)]
    raw = [_slot_runs(ink, win[i][0], win[i][1], it, ib, min_h=0.0, row_floor=_rf[i]) for i in range(n)]
    # 异常长 run 剔掉(> 3x 全页 run 高中位): 淡界行线/扫描黑边被并进槽内时会连成一条竖贯 run
    #   (实测 p32: 两槽的 run 高 768pt -> 字号被算成 873pt, 该页判不适配)
    _al = sorted(b - a for rs in raw for a, b in rs if b - a >= 4.0)
    _cap = max(40.0, 3.0 * _al[len(_al) // 2]) if _al else 40.0
    # 槽顶/槽底另走「全墨迹」口径(实测, 全书 2640 槽里 8 槽的底、4 槽的顶被上面的长 run 剔除
    #   截断, 最大 471pt —— 实测 p149 c1 底 611 vs 真值 1082.5、p223 c1 顶 1049.5 vs 真值 305):
    #   ① 只剔「贴扫描窗口边」的 run(版框横线/装订黑边一定贴窗边; 正文字墨离墨带顶 ~12pt);
    #   ② 合并成长 run 的连续字(相邻字墨相碰)不剔 —— 取首 run 顶/末 run 底即为该列墨迹上下缘。
    _ea, _eb = (it + 2.0), (ib - 2.0)
    draw = [_slot_runs(dink, win[i][0], win[i][1], it, ib, min_h=0.0, row_floor=_rf[i]) for i in range(n)]
    slots = []
    for i in range(n):
        rs = [r for r in raw[i] if 4.0 <= r[1] - r[0] <= _cap]
        hs = sorted(b - a for a, b in rs)
        cs = sorted((a + b) / 2.0 for a, b in rs)
        ds = sorted(d for d in (cs[j + 1] - cs[j] for j in range(len(cs) - 1)) if d < 80)
        step0 = ds[len(ds) // 2] if ds else 0.0
        # ③ 细碎 run(高 <4pt: 「三」「一」「二」的分离点画、标点)贴到最近的字 run 上, 再取首/末。
        #    否则列首/列尾是这类字时槽顶/底少算一个字(实测 p50 c12 源列首「三」331.0 被算成 360.0,
        #    列顶偏 29pt; 同类字: 一二三川州)。离最近字 run 超过 0.4 步进(>12pt)的当噪点丢掉。
        ext = [r for r in draw[i] if (r[0] - _ea) > 1.5 and (_eb - r[1]) > 1.5]
        keep = [list(r) for r in ext if r[1] - r[0] >= 4.0]
        _dd = 0.7 * (step0 or 12.0)   # 0.7 格: 省略号点画间距实测 ~16pt(0.4 格会漏, 见 p153 c9)
        for t in [r for r in ext if r[1] - r[0] < 4.0]:
            if not keep: keep.append(list(t)); continue
            j, gap = None, 1e9
            for k, r in enumerate(keep):
                gp = min(abs(r[0] - t[1]), abs(t[0] - r[1]))
                if gp < gap: j, gap = k, gp
            if gap <= _dd:
                keep[j][0] = min(keep[j][0], t[0]); keep[j][1] = max(keep[j][1], t[1])
        slots.append({'x0': win[i][0], 'x1': win[i][1], 'nr': len(rs),
                      'hm': (hs[len(hs) // 2] if hs else 0.0), 'step': step0,
                      'runs': rs,                        # taskJ-B: 空格检测用(逐字墨迹 run)
                      'keep': keep,                      # taskS: 引號修剪用(与文本配对后做)
                      'top': (keep[0][0] if keep else (rs[0][0] if rs else None)),
                      'bot': (keep[-1][1] if keep else (rs[-1][1] if rs else None))})
    return slots

def _metrics_finish(pi, g, slots, it, ib, w):
    """槽统计 -> page_metrics 结果(正文/注槽分类 + 墨带 + 字号 + 步进上限 + 合理性校验)。"""
    # §1.976 短列(taskS): 由 OCR 列框补出来的短列, 其槽内 run 里标点占比极高(实测「又曰：」
    #   4 条 run 中 2 条是冒号点), 全 run 中位 11.75pt < 正文槽门限 0.75 x hmax = 17.6 -> 会被
    #   判成「小字注槽」, 于是 page_rows 把该行划到注、正文槽又配不上它 -> 整列再次丢失。
    #   故这两类槽的字高改用**字 run 中位**(见 _big_hm): 实测 19.25pt >= 17.6 -> 判回正文槽。
    _sbset = set()
    for _s in slots:
        for _a, _b, _hb in ((g or {}).get('sb') or []):
            if _s['x0'] < _b - 1.0 and _a < _s['x1'] - 1.0:
                _s['hm'] = max(_s['hm'], _hb)
                _sbset.add(id(_s))
    if NF_BODY_TIER and (g or {}).get('virtual') and slots:
        # taskCD-b: 参照取「最高四分位的中位」—— 少数大字号标题列不再把正文门槛整体抬高
        #   (实测 p659: 1 条 38pt 标题 / 14 条 23-26pt 正文, max 口径阈值 28.5 -> 正文全被判成注)。
        #   单字号页 top 四分位的中位 == max -> 与修前逐位相同。
        _hs = sorted(s['hm'] for s in slots if s['hm'] > 0)
        hmax = statistics.median(_hs[int(0.75 * (len(_hs) - 1)):]) if _hs else 0.0
    else:
        hmax = max(s['hm'] for s in slots)
    body = [s for s in slots if s['nr'] >= 2 and s['hm'] >= 0.75 * hmax]
    note = [s for s in slots if s['nr'] >= 3 and s['hm'] < 0.75 * hmax]
    m = None
    if body:
        # 墨带顶/底 = 正文块上/下缘: 全槽中位会被「段首缩进列」(顶) / 「段尾短列」(底) 带偏
        #   (实测 p18: 12 槽里 6 个短列 -> 中位底 1068, 而满列底 1099.5, 差 31pt = 1 格)。
        #   取「偏满列的一半」的中位: 顶取上半(小的那一半)中位, 底取下半(大的那一半)中位。
        #   taskS: **§1.976 的短列不进这两列样本** —— 短列按定义就比正文块短(实测源页 354 的
        #     「又曰：」列顶 221 / 底 287, 而正文块是 221-1101), 混进去会把「上半/下半」的取中位
        #     位置整体挪一格 -> 墨带底从 1101 掉到 961(实测), 于是所有满列都被判成短列
        #     (不再拉齐列底) —— 列底参差。它们仍留在 body 里参与配对与渲染。
        _b2 = [s for s in body if id(s) not in _sbset]
        tots = sorted(s['top'] for s in _b2 if s['top'])
        bots = sorted(s['bot'] for s in _b2 if s['bot'])
        band_t = (statistics.median([t for t in tots if t <= tots[len(tots) // 2]])
                  if tots else it)
        band_b = (statistics.median([b for b in bots if b >= bots[len(bots) // 2]])
                  if bots else ib)
        font = round(statistics.median(s['hm'] for s in body) / INK_RATIO, 1)
        caps = [s['step'] for s in body if s['step'] > 0]
        m = {'pi': pi, 'slots': slots, 'body': body, 'note': note, 'g': g,
             'band_t': band_t, 'band_b': band_b, 'block_b': (max(bots) if bots else ib),
             'font': font,
             'step_cap': round(statistics.median(caps), 2) if caps else font * 0.9,
             'w': w}
    elif note:
        # 整页小字(如 p230 尾注页): 全部当正文槽, 字号按实测小字
        nb = [s['bot'] for s in note if s['bot']]
        band_t = statistics.median(s['top'] for s in note)
        band_b = statistics.median(nb)
        font = round(statistics.median(s['hm'] for s in note) / INK_RATIO, 1)
        m = {'pi': pi, 'slots': slots, 'body': slots, 'note': [], 'g': g,
             'band_t': band_t, 'band_b': band_b, 'block_b': max(nb), 'font': font,
             'step_cap': font * 0.95, 'w': w}
    # 合理性校验: 字号 10-60pt(源书正文 34/双行小字 22; 超出即非文字页) 且 墨带高 >= 0.4 版心高
    #   (实测 p229 插图页 12 槽各一条 795pt 竖贯 run -> 字号 896pt; p156 註釋页墨带仅 78pt)
    #   注(taskP): 10/60pt 是 wz6(页高 1254.1pt)实测的**绝对量** —— 页高比例 = 0.80% / 4.78%。
    #     无版框书(NF)的排印风格差异极大: 实测 wz7 序页/扉页正文单字墨高 ~90pt(字号 103.6pt =
    #     本页页高 1435.5pt 的 7.2%), 被 60pt 上限判成「非文字页」-> 掉进 §1.99 兜底 ->
    #     列底越出页幅(实测 p5-p27 共 5+4+2… 条 span 越界 30-94pt)。故 NF 分支改用**本页页高比例**
    #     为界(上限 12% 页高: 容得下大字序页, 仍挡得住插图页的 62% 粘连长 run; 下限 0.8% 页高)。
    #     非 NF(含所有有实测版框的书, 如 wz6)沿用绝对量 —— 该分支逐位不变。
    _fmin, _fmax = 10.0, 60.0
    if _NF['on'] and src_doc is not None:
        _ph_pt = _nf_page_px(pi)[1] / 2.0
        _fmin, _fmax = _ph_pt * FONT_MIN_FRAC, _ph_pt * FONT_MAX_FRAC
    if m and not (_fmin <= m['font'] <= _fmax and (m['band_b'] - m['band_t']) >= 0.4 * (ib - it)):
        print('    [基准否决] p%d 字号 %.1f 墨带 %.1f-%.1f (版心高 %.1f; 字号界 %.1f-%.1f) -> 回退流式' % (
            pi + 1, m['font'], m['band_t'], m['band_b'], ib - it, _fmin, _fmax))
        m = None
    return m

_metrics_cache = {}
_metrics_cache_rf = {}      # 「槽内行墨迹下限」口径的缓存(仅 NF 兜底重试用, 见 page_metrics_rf)
def page_metrics_rf(pi):
    """伪槽格页的**备用口径**统计: _slots_of_edges 带行墨迹下限(NF_ROW_FRAC)。
    只在原口径的槽统计**配不上本页行**时才用(调用方 = 建排主循环的 misalign 重试) —— 实测
    wz7 序/扉页的槽窗口里混进印刷细线(残界行线), 原口径把整列字 run 连成一条 -> 槽数与行数
    严重不匹配(6 行 -> 1 槽) -> 该页掉进兜底; 带下限的口径把细线滤掉后 6 行 -> 6 槽。"""
    if pi in _metrics_cache_rf: return _metrics_cache_rf[pi]
    m = None
    if NF_MODE and src_doc is not None:
        gv = nf_frame(pi, keys[pi])
        if gv:
            ink = _nf_ink(pi)
            dink = src_gray(pi) < 0.75 * _nf_ink_gray(src_gray(pi))
            slots = _slots_of_edges(ink, dink, gv['cells'], gv['in_t'], gv['in_b'], row_frac=NF_ROW_FRAC,
                                    anchors=(gv.get('bands') if NF_SLOT_ANCHOR else None),
                                    pitch=gv.get('pitch', 0.0))
            m = _metrics_finish(pi, gv, slots, gv['in_t'], gv['in_b'], gv['in_r'] - gv['in_l'])
    _metrics_cache_rf[pi] = m
    return m

def page_metrics(pi):
    """逐页框驱动基准 -> dict 或 None(无版框页: 封面/p1-p2/末页)。
    key: slots[](12 槽: x0/x1/nr/hm/step/top/bot), body[](正文槽), note[](小字注槽),
         band_t/band_b 正文墨带(pt), font 字号, step_cap 步进上限, w 内框宽。
    无版框书(§1.975 NF_MODE): frame_geom 测不到版框时走**伪版心/伪槽格**(墨迹列带), 其余口径相同
      —— 该分支只在本册「一个版框都没测到」时启用, 有版框书走上面的原路径一字不改。"""
    if pi in _metrics_cache: return _metrics_cache[pi]
    m = None
    g = frame_geom(pi)
    if g:
        ink = src_gray(pi) < 150
        # 槽顶/槽底另用「深墨」掩膜(实测): 扫描透印(背面文字反透)在 150 阈值下会与本文粘连成
        #   一条竖贯 run(实测 p90 c12: 透印把 315-853 连成一条 -> 真列顶 380 测成 853, 列被排到
        #   版框底部), 用 110 阈值透印即断开。抽样 876 槽: 两阈值下 99.2% 的槽顶/底一致(中位 0.0pt),
        #   差异的 7 槽(0.8%)深墨阈值均给出更完整的列范围。
        dink = src_gray(pi) < 110
        il, ir, it, ib = g['in_l'], g['in_r'], g['in_t'], g['in_b']
        il0, ir0 = il, ir                     # m['w'] 用**原始**内框宽(栅格校正只改槽格, 不改这条)
        n = N_COL_FRAME
        edges = [il + (ir - il) * i / n for i in range(n + 1)]
        bands = _ink_bands(ink, il, ir, it, ib)
        gr = _grid_from_bands(bands, il, ir)
        if gr:
            e, p = gr
            if abs(e - il) > 1.0 or abs(e + n * p - ir) > 1.0:
                print('    [槽格] p%d 内框 %.1f-%.1f -> 墨迹列带栅格 %.1f-%.1f (列距%.2f)' % (
                    pi + 1, il, ir, e, e + n * p, p))
            edges = [e + p * i for i in range(n + 1)]
            g = dict(g); g['in_l'], g['in_r'] = round(e, 1), round(e + n * p, 1)
        slots = _slots_of_edges(ink, dink, edges, it, ib)
        m = _metrics_finish(pi, g, slots, it, ib, ir0 - il0)
    elif NF_MODE and src_doc is not None:
        # ---- §1.975 无版框伪槽格: 版心 = 正文行墨迹包围盒, 槽 = 墨迹列带(格边界 = 相邻带心中点) ----
        gv = nf_frame(pi, keys[pi])
        if gv:
            ink = _nf_ink(pi)
            dink = src_gray(pi) < 0.75 * _nf_ink_gray(src_gray(pi))   # 深墨掩膜(同比例)
            # 槽统计: 先用**原口径**(row_frac=0); 被合理性校验否决时再用「带行墨迹下限」的口径重算
            #   (taskP: 槽窗口里混进印刷细线时, 原口径会把整列的字 run 连成一条 -> 字号虚高 -> 否决;
            #    有下限的口径能滤掉细线。只在原口径失败时启用 —— 正常页两口径取的都是原口径结果,
            #    且实测有页面(源页 9)反而只有原口径对, 故不能无条件替换)。
            # 槽统计: 原口径被合理性校验否决时, 再用「带行墨迹下限」的口径重算一次(taskP):
            #   槽窗口里混进印刷细线(残界行线)时原口径的字 run 会被连成一条 -> 字号虚高被否决;
            #   下限口径能滤掉细线。只在原口径被否决时才换(实测源页 9 反而只有原口径对)。
            slots = _slots_of_edges(ink, dink, gv['cells'], gv['in_t'], gv['in_b'],
                                    anchors=(gv.get('bands') if NF_SLOT_ANCHOR else None),
                                    pitch=gv.get('pitch', 0.0))
            m = _metrics_finish(pi, gv, slots, gv['in_t'], gv['in_b'], gv['in_r'] - gv['in_l'])
            if not m and NF_ROW_FRAC > 0:
                slots = _slots_of_edges(ink, dink, gv['cells'], gv['in_t'], gv['in_b'], row_frac=NF_ROW_FRAC,
                                        anchors=(gv.get('bands') if NF_SLOT_ANCHOR else None),
                                        pitch=gv.get('pitch', 0.0))
                m = _metrics_finish(pi, gv, slots, gv['in_t'], gv['in_b'], gv['in_r'] - gv['in_l'])
                if m: print('    [无框伪槽格·重试] p%d 原口径被否决 -> 行墨迹下限口径采用' % (pi + 1))
            if NF_SLOT_DBG:
                print('    [槽位诊断] p%d 槽 %d: %s' % (
                    pi + 1, len(slots),
                    ' | '.join('x%.1f-%.1f nr%d hm%.1f st%.2f t%s b%s' % (
                        s0['x0'], s0['x1'], s0['nr'], s0['hm'], s0['step'],
                        ('%.1f' % s0['top']) if s0['top'] is not None else '-',
                        ('%.1f' % s0['bot']) if s0['bot'] is not None else '-') for s0 in slots)))
            if m:
                print('    [无框伪槽格] p%d %d 列(列距%.2f) 字号%.1f 墨带 %.1f-%.1f 版心 x%.1f-%.1f y%.1f-%.1f%s' % (
                    pi + 1, len(gv['cells']) - 1, gv['pitch'], m['font'], m['band_t'], m['band_b'],
                    gv['in_l'], gv['in_r'], gv['in_t'], gv['in_b'],
                    '' if gv['fixed'] else ' (OCR 坐标未标定)'))
    _metrics_cache[pi] = m
    return m

def _row_spans_gap(rows, sl, g0, g1):
    """是否有 OCR 行「x 落在本槽内、y 跨过空隙 (g0,g1)」(pt)。用于拆槽保护:
    目录页/双段列的内空隙由 col_puts 的 fit_gaps 还原(该列在 OCR 里仍是**一行**),
    拆成子槽会把它压进其中一段 —— 有行跨越就不拆。"""
    for r in rows:
        if '\n' in r[4]:
            continue
        xc = (r[0] + r[1]) / 4.0
        if xc < sl['x0'] - 2.0 or xc > sl['x1'] + 2.0:
            continue
        if r[2] / 2.0 <= g0 + 1.0 and r[3] / 2.0 >= g1 - 1.0:
            return True
    return False

def _split_slot_y(ink, sl, it, ib, step_ref, rows, rmin=2.0):
    """taskAB-A: 槽内墨迹 y 投影的大空隙 -> 子槽列表(不拆时返回 [sl])。
    判据: 相邻墨迹 run 的空白 > AB_YSPLIT_K x 字步进, 且没有 OCR 行跨越该空白(见 _row_spans_gap)。
    背景(实测 wz7 p86): 书眉「金瓶梅」y320-442 与页码「四二」y1188-1229 的 x 带完全相同,
    纯 x 槽把两段并成一槽(run 3+2=5) -> 槽顶/底跨 909pt, 行↔槽 1:1 破坏。拆开后两段各自成槽,
    步进/上下缘都按本段实测。
    子槽字段与 _slots_of_edges 同口径(nr/hm/step/runs/keep/top/bot), 另加 ysplit=True
    (col_puts 据此按**本子槽实测跨度**铺满, 不套全页常规步进)。
    rmin(taskCE, 默认 2.0 = 原口径): 「像字」run 的高下限(pt)。目录页的回次/回目/页码之间有
    **竖排点线**(点径 4-5pt、间隔 5-10pt)贯穿, 按 2pt 收 run 时点线把整列连成一条, 任何空隙
    都测不出 -> 拆不开。TOC 口径传 0.30 x 字步进(~7.5pt), 点线被当空白、真字 run(20-27pt)保留。"""
    if not sl or sl.get('x0') is None or sl.get('x1') is None:
        return [sl]
    step_ref = step_ref if step_ref and step_ref > 0 else (sl.get('step') or 0.0)
    if step_ref <= 0:
        return [sl]
    rs = _slot_runs(ink, sl['x0'], sl['x1'], it, ib, min_h=0.0)
    # 拆槽只看「像字」的 run(高 >= rmin, 默认 2pt): 扫描噪点(实测 p513 标题两行之间一处 1pt 斑点)
    #   会把 82pt 的空隙截成 34+46 两段, 两段都低于阈值 -> 该拆的槽拆不开。
    if rmin > 2.0:
        # TOC 口径(taskCE): 点线是「小而方」的墨点(高 4-5pt / x 跨度 ~2-3pt)。页码里的
        #   一/二/三 是单条横画, 高也只有 1-3pt —— 只按高度会把整段页码当点线丢掉
        #   (实测 p53 第八回「一三三」3 字漏渲染)。补一条 x 跨度判据: 横画 x 跨度接近字宽
        #   (>= 0.5 x 步进), 点线远小于它。
        import numpy as np
        xa = int((sl['x0'] + 3.5) * 2); xb = int((sl['x1'] - 3.5) * 2)
        _keep = []
        for r in rs:
            if r[1] - r[0] >= rmin:
                _keep.append(r); continue
            ya, yb = int(round(r[0] * 2)), int(round(r[1] * 2))
            seg = ink[ya:yb, xa:xb] if (yb > ya and xb > xa) else None
            if seg is None or not seg.size or not seg.any():
                continue
            xs = np.where(seg.any(axis=0))[0]
            if xs.size and (xs[-1] - xs[0] + 1) / 2.0 >= 0.5 * step_ref:
                _keep.append(r)
        rs = _keep
    else:
        rs = [r for r in rs if r[1] - r[0] >= rmin]
    if len(rs) < 2:
        return [sl]
    gap_th = AB_YSPLIT_K * step_ref
    groups = [[rs[0]]]
    for r in rs[1:]:
        g0 = groups[-1][-1][1]
        if (r[0] - g0) > gap_th and not _row_spans_gap(rows, sl, g0, r[0]):
            groups.append([r])
        else:
            groups[-1].append(r)
    if os.environ.get('VERT_AB_DBG'):
        print('    [AB拆槽] x%.0f-%.0f 步进%.1f 阈%.1f run%d 组%d 空隙:%s' % (
            sl['x0'], sl['x1'], step_ref, gap_th, len(rs), len(groups),
            ','.join('%.0f%s' % (r[0] - p[1], '*' if (r[0] - p[1]) > gap_th else '')
                     for p, r in zip(rs, rs[1:]) if (r[0] - p[1]) > 0.3 * gap_th)))
    if len(groups) < 2:
        return [sl]
    # 退化子槽(只含一条碎墨/半个字) -> **并给最近的邻组**, 不整槽放弃。
    #   教训: 早先写成「整槽不拆」, 实测 p86 书眉「金瓶梅」(3字) + 页码「四二」(2字) 共槽时,
    #   页码那条 5pt 碎墨(hm 5.0 < 0.45x25.5=11.5) 让整槽放弃 -> 书眉/页码都没有独立子槽
    #   -> AB 位置口径配对把它们跳过 -> 两行全丢(671->668); 同一机制全书 88 页丢字(-368),
    #   含 p375 回目「第二十二回」。并组后书眉/页码各自成槽, 字全部保住。
    #   渲染端已有 step<=0 -> cap 与 F=max(4.0,...) 两道兜底, 不会再现 0pt 字号。
    _good, _bad = [], []
    for g in groups:
        _hs0 = sorted(b - a for a, b in g)
        _cap = max(40.0, 3.0 * _hs0[len(_hs0) // 2]) if _hs0 else 40.0
        _runs = [r for r in g if 4.0 <= r[1] - r[0] <= _cap]
        _hs = sorted(b - a for a, b in _runs)
        _hm = _hs[len(_hs) // 2] if _hs else 0.0
        if _runs and _hm >= AB_YSPLIT_MIN_HM * step_ref:
            _good.append([list(g), _hm])
        else:
            _bad.append((list(g), _hm))
            if os.environ.get('VERT_AB_DBG'):
                print('    [AB拆槽·并组] x%.0f-%.0f 退化子槽(run%d hm%.1f < %.1f) -> 并给最近邻组'
                      % (sl['x0'], sl['x1'], len(_runs), _hm, AB_YSPLIT_MIN_HM * step_ref))
    if len(_good) < 2:
        # 有效组不足 2 个 -> 把「退化」组也晋升为有效子槽。
        #   书眉/页码/边注是 **10pt 级小字**(实测 p100 书眉墨高 9.0pt), 天然低于
        #   AB_YSPLIT_MIN_HM x 字步进 这个按正文字号定的下限, 属正常元素而非碎墨。
        #   若照旧整槽放弃, 全书 78 页会把书眉/页码并回正文槽 -> 位置口径配对判给正文行
        #   -> 书眉被跳过 -> 丢 3 字/页。
        #   渲染端已有 step<=0 -> cap 与 F=max(4.0,...) 兜底, 极端子槽也不会产出 0pt 字号。
        for _g, _hm in _bad:
            _good.append([list(_g), _hm])
            if os.environ.get('VERT_AB_DBG'):
                print('    [AB拆槽·晋升] x%.0f-%.0f 小字子槽(nr%d hm%.1f) -> 保留为独立槽'
                      % (sl['x0'], sl['x1'], len(_g), _hm))
        _bad = []
        if len(_good) < 2:
            return [sl]                    # 实在拆不出 2 个 -> 不拆(保持原行为)
    for _g, _hm in _bad:
        _ga = min(a for a, b in _g)
        _gb = max(b for a, b in _g)
        _bi = min(range(len(_good)),
                  key=lambda i: min(abs(_ga - max(b for a, b in _good[i][0])),
                                    abs(_gb - min(a for a, b in _good[i][0]))))
        _good[_bi][0].extend(_g)
        _good[_bi][0].sort()
    groups = [g for g, _hm in _good]
    if os.environ.get('VERT_AB_DBG') and _bad:
        print('    [AB拆槽] x%.0f-%.0f -> 并组后 %d 个子槽'
              % (sl['x0'], sl['x1'], len(groups)))
    out = []
    for g in groups:
        hs0 = sorted(b - a for a, b in g)
        cap = max(40.0, 3.0 * hs0[len(hs0) // 2]) if hs0 else 40.0
        runs = [r for r in g if 4.0 <= r[1] - r[0] <= cap]
        hs = sorted(b - a for a, b in runs)
        cs = sorted((a + b) / 2.0 for a, b in runs)
        ds = sorted(d for d in (cs[j + 1] - cs[j] for j in range(len(cs) - 1)) if d < 80)
        out.append({'x0': sl['x0'], 'x1': sl['x1'], 'nr': len(runs),
                    'hm': (hs[len(hs) // 2] if hs else 0.0),
                    'step': (ds[len(ds) // 2] if ds else 0.0),
                    'runs': runs,
                    'keep': [list(r) for r in g],
                    'top': g[0][0], 'bot': g[-1][1], 'ysplit': True,
                    # taskCJ: 标记「y 拆分子槽」—— col_puts 只对这类槽按本子槽墨高定字号
                    #   (目录分支 _toc_puts 的单行槽也带 ysplit, 但那边的字号已按本行实测算好,
                    #    不能再被这条覆盖)。
                    'absub': True})
    return out

def _align_rows_slots(rows, slots, skip=8.0, prior=0.0, geom=False, pitch=0.0, step=0.0):
    """OCR 行(阅读序, 右->左) x 槽(阅读序) 单调对齐 -> [(行下标, 槽下标)]。
    行数 == 槽数(全书 195/231 页): 按序 1:1 直配 —— 源书阅读序 = 槽序, 任何代价法只会引入噪声
      (实测 p9 12:12 时代价法反而丢 1 行 1 槽, 把 21 字那列认成残片)。
    不等时: 动态规划, 且只允许「多的一方」跳过(少的一方每跳一条, 后面整段跟着错位);
      匹配代价 = |OCR 字数 - 槽 run 数 - infl|, infl = 该页两者中位差(墨迹 run 会把相邻相碰的字
      并掉, 实测 p50 OCR 26 字 vs run 23); 罚 skip 取 8 字 —— 只放明显不符的行/槽走, 实测
      p11 两条 OCR 残片(2 字/3 字)对任何槽的代价都 >8 -> 正确落空, 12 条长行全部归位。
    不按 x 位置匹配: OCR x 逐页有 ~10% 伸缩(p100 末列偏 43pt, 首列偏 +30pt), 位置法会认错槽。
    geom(taskAB-B, 只无版框且 OCR 坐标已标定的页): 位置可信 -> 加位置约束与代价:
      · 硬约束: x 中心距 > AB_XK x 列距 或 y 范围不重叠(容差半步进) -> 禁止配对;
      · 代价: + 行/槽 x 中心距/列距 + 行/槽 y 中心距/字步进;
      · 两侧都可跳过(有位置约束后, 配不上的槽宁可空着也不硬配 —— 实测 p513 的 2 个正文槽
        在页首而 16 条行多在页尾, 原口径强制用满槽 -> 两条行被搬到页首 +574/+429pt)。"""
    R, C = len(rows), len(slots)
    if not R or not C: return []
    if R == C and not geom: return [(i, i) for i in range(R)]
    # 位置先验(taskP, prior>0 时启用): cost += prior x |行序 - 槽序|(各自按阅读序归一化到 [0,1])。
    #   为什么需要: 只按「格数/run 数」配平时, 行数 > 槽数会整段**平移** —— 实测源页 1206(18 行 16 槽)
    #   把两组詩行的 4 个短列错配到左侧 3 个长列的位置上, 而真正的两列(遞畢酒 44 字/小優彈唱 34 字)
    #   成了「多出来的行」被静默丢弃(整列 78 字不渲染)。加位置先验后: 整段平移 8 行 x 1 槽的代价
    #   (8/15 x prior) 高于跳 2 行的代价(2 x skip), DP 改为「原地跳过剩行」-> 4 个詩列回到原位。
    # 代价口径用「排版格数」n_cells(标点不占格): 源槽 run 数 = 源书格数, 与 OCR 字数直接比会
    #   被标点数带偏(§1.0; 全书平均每列 0.51 个挤格标点)
    # geom 口径下 infl 取 0: 位置配对不再要求「两侧全部用满」, 全局中位差会被标题/书眉这类
    #   窄槽(条数 ≠ 字数)带偏 —— 实测 p513 的 infl=10 把正确配对的代价整体抬到 skip 罚以上
    #   (标题行 5 字 vs 槽 15 run -> 代价 20 > 2x8), 正确配对反而被跳过。
    infl = 0.0 if geom else (statistics.median(n_cells(r[4]) for r in rows)
                             - statistics.median(s['nr'] for s in slots))

    def _geom_ok(i, j):
        """taskAB-B 位置硬约束: x 中心距 <= AB_XK x 列距 且 y 范围相交(±半字步进)。"""
        r, s = rows[i], slots[j]
        if pitch > 0:
            if abs((r[0] + r[1]) / 4.0 - (s['x0'] + s['x1']) / 2.0) > AB_XK * pitch:
                return False
        if s.get('top') is not None and s.get('bot') is not None:
            tol = 0.5 * (step or 12.0)
            if r[3] / 2.0 < s['top'] - tol or r[2] / 2.0 > s['bot'] + tol:
                return False
        return True

    def _geom_cost(i, j):
        r, s = rows[i], slots[j]
        c = 0.0
        if pitch > 0:
            c += abs((r[0] + r[1]) / 4.0 - (s['x0'] + s['x1']) / 2.0) / pitch
        if step > 0 and s.get('top') is not None and s.get('bot') is not None:
            c += AB_YK * abs((r[2] + r[3]) / 4.0 - (s['top'] + s['bot']) / 2.0) / step
        return c

    row_can = R > C                       # 只允许多的一方跳过
    col_can = C > R
    if geom:                              # 位置口径: 两侧都可跳过(空槽/空行都是合法结局)
        row_can = col_can = True
    INF = 1e9
    dp = [[INF] * (C + 1) for _ in range(R + 1)]
    bt = [[None] * (C + 1) for _ in range(R + 1)]
    dp[0][0] = 0.0
    for i in range(R + 1):
        for j in range(C + 1):
            if dp[i][j] >= INF: continue
            if i < R and j < C and (not geom or _geom_ok(i, j)):
                c = abs(n_cells(rows[i][4]) - slots[j]['nr'] - infl) + dp[i][j]
                if prior > 0:
                    c += prior * abs(i / float(max(1, R - 1)) - j / float(max(1, C - 1)))
                if geom:
                    c += _geom_cost(i, j)
                if c < dp[i + 1][j + 1]: dp[i + 1][j + 1] = c; bt[i + 1][j + 1] = (i, j, 1)
            if row_can and i < R and dp[i][j] + skip < dp[i + 1][j]:
                dp[i + 1][j] = dp[i][j] + skip; bt[i + 1][j] = (i, j, 0)
            if col_can and j < C and dp[i][j] + skip < dp[i][j + 1]:
                dp[i][j + 1] = dp[i][j] + skip; bt[i][j + 1] = (i, j, 0)
    out = []
    i, j = R, C
    while i > 0 or j > 0:
        p = bt[i][j]
        if p is None: break
        pi_, pj_, took = p
        if took: out.append((pi_, pj_))
        i, j = pi_, pj_
    out.reverse()
    return out

def _merge_col_rows(rows, step, prov=None):
    """同一列的 OCR 断行合并(在分类/对齐之前做)。
    实测 p34: 「優勢兵力，採用包圍迂迴戰術」(y602-1464) 与「不能包圍其全部也包圍其」(y1564-2336)
    x 带 71.5-139.3 / 57.2-139.3 重叠 83% —— 是源书同一列被 OCR 在中间断开, 不合并则第二段
    无槽可归被丢(该页少 11 字)。判据: x 带重叠 >= 60% 小者宽 且 y 相邻间距 <= 2.5 字步进。
    prov(taskU-A): 传 dict 时按合并结果的 id 记「文本顺序的 (源行 id, 该行文本长)」——
      供 §1.997 把改字写回 all_rows 里**原始 OCR 行对象**(合并后的行是新建 tuple, 无法按对象回溯)。"""
    rows = sorted(rows, key=lambda r: -r[0])
    used = [False] * len(rows)
    out = []
    for i, r in enumerate(rows):
        if used[i]: continue
        x0, x1, y0, y1, t = r
        used[i] = True
        pieces = [(id(r), len(r[4]))]
        again = True
        while again:
            again = False
            for j, o in enumerate(rows):
                if used[j]: continue
                ox0, ox1, oy0, oy1, ot = o
                ov = min(x1, ox1) - max(x0, ox0)
                if ov < 0.6 * min(x1 - x0, ox1 - ox0): continue
                if 0 <= oy0 - y1 <= 2.5 * step:                # o 在本行之下
                    t = t + ot; y1 = oy1; pieces.append((id(o), len(ot)))
                elif 0 <= y0 - oy1 <= 2.5 * step:              # o 在本行之上
                    t = ot + t; y0 = oy0; pieces.insert(0, (id(o), len(ot)))
                else:
                    continue
                x0 = min(x0, ox0); x1 = max(x1, ox1)
                used[j] = True; again = True
        rr = (x0, x1, y0, y1, t)
        out.append(rr)
        if prov is not None: prov[id(rr)] = pieces
    return out

def _nf_margin_artifact(r, m):
    """taskCD-c: 伪版心 y 之外的「横排/非汉字」行 = 扫描水印/馆藏条码标签(只 NF 路径, 开关 NF_DROP_MARGIN)。
    判据(两条同时成立):
      ① 整行在伪版心上/下缘之外(r[3] <= in_t 或 r[2] >= in_b; px 与 ink 同单位, in_* 为 pt -> x2);
      ② 行盒横排(w/h >= NF_MARGIN_AR) 或 无汉字 —— 真书眉/页码是竖排汉字且在页边带内, 不受影响。
    背景(实测 p1171): 页顶手写编号 859.49/6996/879/v.3、页底「国家图书馆 + 004757702」是馆藏
    标记; 前者被 special_rows 认成书眉/页码画出, 后者与目录列 x 带重叠被 _merge_col_rows 并进
    邻列 -> 整列错字。判据只用行盒几何/文本, 不写死页号。"""
    if not (NF_DROP_MARGIN and m and m.get('g') and m['g'].get('virtual')):
        return False
    it2, ib2 = m['g']['in_t'] * 2.0, m['g']['in_b'] * 2.0       # pt -> px(2x)
    if not (r[3] <= it2 + 1.0 or r[2] >= ib2 - 1.0):
        return False
    w, h = r[1] - r[0], max(1.0, r[3] - r[2])
    if w / h >= NF_MARGIN_AR:
        return True
    return not any(_is_cjk_ch(c) for c in r[4])

def page_rows(k, m, pi, prov=None):
    """本页 OCR 行分组 -> (正文行, 注/边行, 页外行)。正文/注按「字步进」一维二分(源书正文与
    双行小字注的步进比实测 1.5+: p162 正文 34.4pt vs 注 22.2pt); 页外行 = x 中心在内框外(书耳/篇名)。"""
    claimed = set()
    for c in special_rows(k):
        claimed.add((c[2], c[3], c[4], c[5], c[1]))
    inb = []
    for r in all_rows[k]:
        x0, x1, y0, y1, t = r
        if (x0, x1, y0, y1, t) in claimed: continue
        if len(t) < 1: continue
        if '\n' in t: continue                  # 多块合并残片(同 is_body_col)
        inb.append(r)
    # 页外行(书耳/篇名): OCR 行的 x 带与内框完全不相交(px 对 pt: x2 = 2x); 用「相交」而非
    #   「中心在内」—— OCR x 逐页有漂移(实测 p100 首列偏 +30pt, 末列偏 -43pt), 中心判据会误杀首末列。
    il2, ir2 = m['g']['in_l'] * 2.0, m['g']['in_r'] * 2.0
    ins = [r for r in inb if not (r[1] < il2 - 6 or r[0] > ir2 + 6)]
    out_rows = [r for r in inb if r[1] < il2 - 6 or r[0] > ir2 + 6]
    # 页外行须「框外确有墨迹」才算页外(§1.98b): OCR 对版面边缘列的 x 会外漂(实测 p228 最左列
    #   「合當時反對北洋軍閥段祺瑞的西南軍閥組織反段的政府」 OCR x 5-26pt 落到内框左缘 36.2 之外,
    #   而源墨迹整条在内框里 = 正文), 这类行交回正文参与列对齐 —— 否则整行 26 字被丢弃。
    #   真页外行(书耳/篇名, 实测 p162 x1159-1185px)框外有墨迹, 不受影响。
    if out_rows and src_doc is not None:
        g2 = src_gray(pi); H2, W2 = g2.shape
        # 区带取到「版框最外一条线之外」: 框线本身墨占比 0.4-0.99, 不排除会把空白页边判成有墨迹
        #   (实测 p228 外粗线 28.5pt 处占比 0.38)。
        #   另两侧端头要躲开「扫描黑边」(实测 p162 左缘 0-5px 墨占比 0.69-0.15, 会把空白页边判成有墨)。
        ol = m['g'].get('out_l'); orr = m['g'].get('out_r')
        bar_l, bar_r = int(m['g'].get('bar', (0, 0))[0] * 2), int(m['g'].get('bar', (0, 0))[1] * 2)
        xl_end = int(min(il2, (ol * 2.0) if ol else il2) - 6)
        xr_beg = int(max(ir2, (orr * 2.0) if orr else ir2) + 6)
        keep = []
        for r in out_rows:
            lft2 = (r[0] + r[1]) / 2.0 <= (il2 + ir2) / 2.0
            xa2 = (bar_l + 2) if lft2 else xr_beg
            xb2 = max(0, xl_end) if lft2 else (W2 - bar_r - 2)
            ya2 = max(0, int(r[2] - 10)); yb2 = min(H2, int(r[3] + 10))
            if xb2 <= xa2 or yb2 <= ya2 or (g2[ya2:yb2, xa2:xb2] < 185).mean() <= 0.02:
                ins.append(r)
            else:
                keep.append(r)
        out_rows = keep
    if os.environ.get('VERT_NF_DBG'):
        print('    [行分组] p%d 原始 %d -> 认领后 %d; 版心内 %d 页外 %d' % (
            pi + 1, len(all_rows[k]), len(inb), len(ins), len(out_rows)))
    # taskCK: 步进格数口径只在无版框(NF)路径换成 _step_chars; 有版框书(wz6)仍按 len,
    #   保证既有产物逐字节不变。
    _nstep = _step_chars if (m['g'].get('virtual') or _NF['on']) else len
    step_px = statistics.median([(r[3] - r[2]) / float(_nstep(r[4])) for r in inb]) if inb else 60.0
    ins = _merge_col_rows(ins, step_px, prov)
    out_rows = _merge_col_rows(out_rows, step_px, prov)
    if os.environ.get('VERT_NF_DBG'):
        print('    [行分组] p%d 合并后 版心内 %d 页外 %d (步进中位 %.1f)' % (
            pi + 1, len(ins), len(out_rows), step_px))
    if len(ins) < 2:
        return ins, [], out_rows
    # 短行(n<8)另判: OCR 的 y 跨度对短列松紧不一(实测 p162「問題。」3 字列 span/n 只有 33pt 而
    #   正文 34.4pt -> 被步进法误判成注), 而它的 x 位置可靠 -> 按源图槽区归属(注槽区 ±10pt)。
    note_x = None
    if m['note']:
        note_x = (min(s['x0'] for s in m['note']) - 10.0, max(s['x1'] for s in m['note']) + 10.0)
    lng = [r for r in ins if len(r[4]) >= 8]
    sht = [r for r in ins if len(r[4]) < 8]
    body, note = list(sht), []
    if note_x is not None:
        body = [r for r in sht if not (note_x[0] <= (r[0] + r[1]) / 4.0 <= note_x[1])]
        note = [r for r in sht if note_x[0] <= (r[0] + r[1]) / 4.0 <= note_x[1]]
    st = sorted(((r[3] - r[2]) / float(_nstep(r[4]))) for r in lng)
    gmax, gi = 0.0, -1
    for j in range(len(st) - 1):
        rat = st[j + 1] / max(1e-6, st[j])
        if rat > gmax: gmax, gi = rat, j
    # 阈值 1.18: 单一字号页的最大步进间隙比实测 <= 1.13(全书 196/224 页 <1.20), 而正文/双行小字
    #   注的步进比实测 1.21-1.62(p4 1.246 / p162 1.55) -> 1.18 分隔两类且不误切单字号页。
    # taskCK: 步进口径改用 _step_chars(连续拉丁串算 1 格) —— 词多的列不再被低估成「小字注」;
    #   且 **m['note'] 为空时不做步进分裂**: 槽统计已经给出「本页没有小字号列」的证据,
    #   此时行步进的离群只可能是 OCR 行盒松紧(实测 p1598「，,聽了，,正是：:」10 字/130pt ->
    #   13pt, 被当注排成 9pt/步进5pt, 与正文列叠字), 一律按正文渲染。
    if gmax >= 1.18 and len(st) >= 4 and (m['note'] or not _NF['on']):
        thr = (st[gi] + st[gi + 1]) / 2.0
        b2 = [r for r in lng if (r[3] - r[2]) / float(_nstep(r[4])) > thr]
        n2 = [r for r in lng if (r[3] - r[2]) / float(_nstep(r[4])) <= thr]
        # 交叉验证(源图容量判据): 拆出来的两类都要装得下 —— 注位 = 注槽 x2(双行小字), 正文位 = 正文槽;
        #   不一致则不做拆分(实测 p20 间隙比 1.218 但只有 1 行偏大 -> 是标题行, 不是注页)。
        #   taskP2(NF 伪槽格页加严): 无版框书的伪槽格是**按墨迹列带**建的, 每条列带本就是一条真列,
        #   「注槽 x2」的宽容量会把「行数多于注槽数」的页错放—— 实测 wz7 源页 291(年表页: 年号是大字
        #   12 字/行, 正文是小字 35-39 字/行) 步进分裂把**正文行**(步进 43.5px)判成注、把**大字年号行**
        #   (54px)判成正文, 7 条正文行交给 3 个伪槽格 -> 正文列被当小字注排成 9pt 并错位, 全页 84 字丢。
        #   故 NF 页改判据: 注行数不得超过注槽数 + 1(同列断行容 1 条), 否则整页按单一字号处理(不拆)。
        if m['g'].get('virtual') and NF_NOTE_CAP:
            _cap_ok = (len(n2) <= len(m['note']) + 1 and len(b2) <= len(m['body']) + 2)
        else:
            _cap_ok = (len(n2) + len(note) <= 2 * len(m['note']) + 2
                       and len(b2) + len(body) <= len(m['body']) + 2)
        if _cap_ok:
            body += b2; note += n2
        else:
            body += lng
    else:
        body += lng
    if os.environ.get('VERT_NF_DBG'):
        print('    [行归属] p%d 正文 %d / 注 %d / 页外 %d; 丢弃行:' % (
            pi + 1, len(body), len(note), len(out_rows)))
        for _r in note:
            print('        [注行] x%7.1f n%3d step%6.1f %s' % (
                _r[0] / 2, len(_r[4]), (_r[3] - _r[2]) / max(1, len(_r[4])), _r[4][:24]))
        for _r in body:
            print('        [正文行] x%7.1f n%3d step%6.1f %s' % (
                _r[0] / 2, len(_r[4]), (_r[3] - _r[2]) / max(1, len(_r[4])), _r[4][:24]))
        _kept = set(id(r) for r in body + note + out_rows)
        for r in all_rows[k]:
            if id(r) not in _kept:
                print('        x%7.1f-%7.1f y%7.1f n%3d %s' % (r[0] / 2, r[1] / 2, r[2] / 2, len(r[4]), r[4][:28]))
    return body, note, out_rows

def _esc_ch(t):
    """单字 LaTeX 转义(与旧正文流同一组: % # & _)。"""
    return t.replace('%', r'\%').replace('#', r'\#').replace('&', r'\&').replace('_', r'\_')

def _pv_clamp_on(m):
    """是否对 \put 做「夹回页内」(只无框伪槽格页): 实测竖排字盒的 span bbox 下缘 = 基线 - 字号,
    少数页的标点摆位(PUNCT_DY 标定值 1.244 > 1 格)会把列末标点放到列底之下、括号竖排形态变换
    也会外移 —— 越出页幅(实测「！」越 865pt、多页标点 3-22pt、源页 22 右列 0.57pt)。
    有版框页(含 wz6)不走这里: 其列位受版框约束, 无此现象, 逐位不变。"""
    return bool(m and m['g'].get('virtual'))

def _slot_lead_mark(pi, sl, n_chars, cap):
    """槽首是否压着一个 OCR 漏识的「段首圈点」-> dict 或 None。

    判据(实测标定, 全部相对量):
      几何: (bot-top)/cap - n_chars ∈ [PARA_MARK_LO, PARA_MARK_HI]
            —— 槽内墨迹占了「字数+1」格, 多出的一格就是圈点
      形状: 首格墨迹的径向剖面 中心填充 >= CENTER_MIN 且 第3环(0.4-0.6半径) <= RING3_MAX
            (中空环) 且 最外环 >= OUTER_MIN
            实测真圈点 p43×3 + p44×3: 中心 100%, 第3环 1-14%, 最外环 70-100%
            误报 p77 汉字(中心 73%) / p1699「酒」(中心 32%) 被中心填充排除
    说明: 单靠几何会误判笔画密的汉字(p77/p1699), 单靠形状会漏(普通列首字也密), 两者必须叠加。
    """
    if not PARA_MARK or n_chars < PARA_MARK_MIN_CHARS or cap <= 0:
        return None
    t0, b0 = sl.get('top'), sl.get('bot')
    if t0 is None or b0 is None:
        return None
    extra = (b0 - t0) / cap - n_chars
    if not (PARA_MARK_LO <= extra <= PARA_MARK_HI):
        return None
    try:
        import numpy as _np
        ink = _nf_ink(pi)
        if ink is None:
            return None
        x0, x1 = int(round(sl['x0'] * 2)), int(round(sl['x1'] * 2))
        y0, y1 = int(round(t0 * 2)), int(round((t0 + cap) * 2))
        sub = ink[max(0, y0):max(1, y1), max(0, x0):max(1, x1)]
        ys, xs = _np.where(sub)
        if len(ys) < 8:
            return None
        cell = sub[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        H, W = cell.shape
        if H < 8 or W < 8:
            return None
        cy, cx = H / 2.0, W / 2.0
        yy, xx = _np.mgrid[0:H, 0:W]
        r = _np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        rmax = min(H, W) / 2.0
        band = []
        for k in range(5):
            mk = (r >= rmax * k / 5.0) & (r < rmax * (k + 1) / 5.0)
            band.append(100.0 * cell[mk].sum() / max(1, mk.sum()))
        cmk = r < rmax * 0.22
        center = 100.0 * cell[cmk].sum() / max(1, cmk.sum())
    except Exception:
        return None
    if not (center >= PARA_MARK_CENTER_MIN and band[2] <= PARA_MARK_RING3_MAX
            and band[4] >= PARA_MARK_OUTER_MIN):
        return None
    return {'cell': cap, 'top0': t0, 'extra': round(extra, 2),
            'center': round(center), 'band': [round(v) for v in band]}


def col_puts(t, xc, m, sl=None, prev_bot=None, pi=None):
    """一列正文 -> (逐字 \\put 列表, 本列墨迹底 pt)。列位 = 槽中心(字盒居中于界行线栅格格内)。
    列顶/列底改用**本槽实测**(§1.98 槽实测; 全 222 页 2601 个正文槽统计), 三类:
      ① 列顶 = 本槽实测墨迹顶 —— 源书 87.5% 槽顶 = 墨带顶(0.0 格), 9.9% 是段首缩进列(「空二字」,
         实测缩进中位 2.4 格, 散布 158/222 页), 少数是标题列(p100 标题列顶实测 422.5)。
         旧实现用「上列墨底 + 步进」启发式排接排列: p100 被推低到 453.0(偏 30.5pt) —— 根因是
         源书句号「挤在上字格右下角」不占格(p100 首列「的了。」源墨底 390.5), 本项目按整格排
         句号 -> 上列墨底算成 420.6。改用本槽实测顶后同类列顶命中 0.0pt。
      ② 满列(本槽实测底距墨带底 <= 3 步进, 全书 87.7% 槽): 顶贴本槽实测顶、底拉齐本槽实测底;
         步进 = (槽高 - 单字墨高)/(字数-1), 夹在常规步进的 0.75-1.30 倍(OCR 字数与源书格数
         实测中位差 +0.1 格、p5-p95 为 -0.3…+2.7 格; 夹住是为了 OCR 行字数异常时不把字挤成一团
         或摊得过开, 实测 p9 c2 源列 24 格而 OCR 行 21 字 -> 1.19 倍可铺满, 旧上限 1.15 会短 27pt)。
      ③ 短列(段尾/标题, 本槽底浅于墨带底): 顶贴本槽实测顶 + 源书常规步进, 不拉伸(源书亦然)。
    标点挤格(任务A): 挤格标点(。，、；：？！)不占格 —— 排版格数 = 字数 - 标点数(§1.0 n_cells),
      标点用 PUNCT_SIZE×字号 单独绝对定位到「前一字格右下区」(墨心 = 前格顶 + PUNCT_DY×步进,
      x = 格左缘 + PUNCT_DX×格距; 源书实测见 §1.0)。
    字号保护(任务B): 任何列的墨高 <= 0.95×步进, 越则本列缩字号(防字粘连)。
    列内空隙(任务J-B): 源书「問：/答：」后空一格 —— OCR 不保留。用本槽 run 序列 + DP 反推
      (fit_gaps, §1.0b), 该格只推进不落墨(渲染 = 留白一格)。计入排版格数 nc。
    空子列(双行小字页配对到无墨子列)无实测时用页墨带顶/底。"""
    n = len(t)
    if n == 0: return [], None
    F = m['font']
    # taskCJ: 「y 拆分子槽」(书眉/页码/共槽分段)按**本子槽实测墨高**定字号 —— 它与正文可能不同字号。
    #   修前一律用页字号: 实测 p159 书眉「第六回 西門慶…」墨高 20.0pt 而正文 22.5pt, 页字号 26.0
    #   画出来的字比源书大 13%; 页码子槽 hm=18.0 -> 20.8pt(源书同为小字)。
    #   墨高取 run 高的 75 分位(_big_hm, 与 §1.976 同口径: 排标点碎片/并字长 run)。
    #   细笔画/断裂 run 的兜底(实测 p721 页码「一六一」: 「六」被拆成两条 run, 75 分位只有 10pt,
    #   按墨高会把字号算成 11.5pt, 源书约 20pt): 若字高 < 0.75 x (子槽跨度/字数) —— 字形墨高
    #   远小于该字在列里占的跨度, 说明 run 不可靠 —— 改用**子槽跨度反推**
    #   F = (跨度 - 墨高)/(字数-1)(即每个字占一个前进格)。
    if NF_SLOT_ANCHOR and sl is not None and sl.get('absub'):
        _hb = _big_hm(sl.get('runs') or [])
        _T, _B = sl.get('top'), sl.get('bot')
        _span = (_B - _T) if (_T is not None and _B is not None and _B > _T) else 0.0
        if _hb > 0:
            if _span > 0 and n > 1 and _hb < 0.75 * _span / float(n):
                _hb = max(_hb, (_span - _hb) / float(n - 1) * INK_RATIO)
            F = max(4.0, round(_hb / INK_RATIO, 1))
        # taskCK: **run 高不可靠**的跨度兜底(细笔画数码: 「二/三」的笔画是 2-4pt 横画,
        #   _big_hm 只能测到半字高)。判据(任务书): F_run < 0.5 x 页字号 且 子槽跨度能容纳
        #   n 字(span/n 在页字号 0.6-1.5 倍内) -> F = span/n/0.9; 单字 -> 页字号。
        if _NF['on'] and _span > 0 and _hb / INK_RATIO < 0.5 * m['font']:
            _Fs = _span / float(n) / 0.9
            if n > 1 and 0.6 * m['font'] <= _Fs <= 1.5 * m['font']:
                F = max(4.0, round(_Fs, 1))
            elif n == 1:
                F = m['font']
        if os.environ.get('VERT_SUB_DBG'):
            print('    [SUB-DBG] %s hm=%.1f big=%.1f top=%s bot=%s n=%d -> F=%.1f'
                  % (t[:8], sl.get('hm') or 0.0, _hb, _T, _B, n, F))
    cap = m['step_cap']
    ink_h = INK_RATIO * F
    T = sl['top'] if (sl and sl.get('top') is not None) else m['band_t']
    B = sl['bot'] if (sl and sl.get('bot') is not None) else m['band_b']
    band_b = m['band_b']
    full = (band_b - B) <= 3.0 * cap                         # 满列判据: 源槽墨底贴墨带底
    nc = n_cells(t)                                          # 排版格数(标点不占格)
    # 段首圈点(taskCC): 首格让给圈点, 文字整体下移一格(否则压在圈点上)。
    #   必须在下面算 step/top **之前**改 T —— 让 step 按「少一格」的跨度重新铺。
    _pm = None
    _T0 = T
    if PARA_MARK and sl is not None and m['g'].get('virtual'):
        _pm = _slot_lead_mark(pi, sl, len(t), cap)
        if _pm is not None:
            T = T + _pm['cell']
            if os.environ.get('VERT_PARA_MARK_DBG'):
                print('    [段首圈点] p%s x%.1f-%.1f 多%.2f格 中心%d%% 径向%s -> 首格让给圈点'
                      % (pi + 1 if pi is not None else '?', sl['x0'], sl['x1'],
                         _pm['extra'], _pm['center'],
                         '/'.join(str(v) for v in _pm['band'])))
    # 列内空隙(taskJ-B): 本槽 run 序列 + 文本 -> 额外空格格数(该格不落墨, 只推进)
    _ip1 = (lambda y: any(a - 0.5 <= y <= b + 0.5 for a, b in sl['runs'])) if (GAP_INK and sl.get('runs')) else None
    gaps = (fit_gaps(sl['runs'], t, (sl.get('step') or cap), T, B, h_ink=ink_h, ink_probe=_ip1)
            if (sl and sl.get('runs')) else [])
    gap_at, extra = {}, 0
    for ci, e in gaps:
        gap_at[ci] = gap_at.get(ci, 0) + e; extra += e
    nc += extra
    if extra and pi is not None:
        _gap_log.append({'page': pi + 1, 'x0': round(xc, 1), 'ncell': n_cells(t), 'extra': extra,
                         'step': round(sl.get('step') or 0.0, 2), 'text': t[:24],
                         'at': [[ci, e] for ci, e in gaps]})
    if nc == 1:
        step, top = 0.0, (B - ink_h if full else T)
    elif sl and sl.get('ysplit'):
        # ④ taskAB-A 拆分子槽(书眉/页码/共槽分段): 用**本子槽实测跨度**铺满 —— 该段自身的上下缘
        #    就是这串字的墨迹范围, 套全页常规步进会把「金瓶梅」压成 25.5pt 步进(源书实测 49.8)。
        step = max(0.0, (B - T - ink_h) / (nc - 1))
        if step <= 0.0:
            # 子槽跨度装不下一个字(退化子槽) -> 退回常规步进。留 step=0 会让下面的字号保护
            #   按 0.95*0/INK_RATIO 算出 0pt(LaTeX `! Improper 'at' size`), 且所有字叠在一点。
            step = cap
        top = T
    elif full:                                               # ① 满列: 顶贴槽实测顶, 底拉齐槽实测底
        step = min(1.30 * cap, max(0.75 * cap, (B - T - ink_h) / (nc - 1)))
        top = T
    else:                                                    # ②/③ 短列: 顶贴槽实测顶 + 常规步进
        step, top = cap, T
    # 护栏: 列不越「本列终点」(满列 = 本槽实测底, 短列 = 页正文块下缘 block_b) —— 越则压步进贴住。
    #   不用页墨带底 band_b: 它是「偏满列的一半」中位, 短列多的页(p18 半页短列)会低于满列底,
    #   拿它当界会把满列提前截断(实测 p18 满列被压到 1068, 比源书 1100 短 31pt)。
    guard_b = B if full else m.get('block_b', band_b)
    if nc > 1 and top + ink_h + (nc - 1) * step > guard_b:
        step = (guard_b - top - ink_h) / (nc - 1)
    # 字号保护(任务B): 判据取**墨高**口径 —— 本项目 m['font'] 是 em 字号, 单字墨高 = INK_RATIO×字号;
    #   源书自身墨高/步进实测 0.93-0.95(处于上限内), 正常列不触发; 只兜住 OCR 字数异常(多字)的列。
    for _ in range(3):
        if nc <= 1 or ink_h <= 0.95 * step: break
        # F 下限 4pt: 任何路径都不许产出 0pt 字号(LaTeX 会报 `Improper 'at' size`, 全书构建判失败)
        F = max(4.0, round(0.95 * step / INK_RATIO, 1))
        ink_h = INK_RATIO * F
        if full:
            step = min(1.30 * cap, max(0.75 * cap, (B - T - ink_h) / (nc - 1)))
        if top + ink_h + (nc - 1) * step > guard_b:
            step = (guard_b - top - ink_h) / (nc - 1)
    y0 = top + INK_ASC * F                                   # 首字基线(页顶向下, 墨顶在基线上方 0.94F)
    x_put = xc - XSCALE * F / 2.0                            # taskJ-A: 横向压缩后字心仍居中于槽中心
    pitch = (sl['x1'] - sl['x0']) if sl else m['w'] / N_COL_FRAME    # 本格格距(pt)
    Fp = PUNCT_SIZE * F                                      # 标点字号(源书标点墨迹明显小于正文)
    # taskCM: 列尾闭引号形状纠错(只无版框书)。在算完 step/top 之后、铺字之前判: 只读源图。
    _qsf = None
    if (QSF_ON and _NF['on'] and src_doc is not None and pi is not None and sl is not None
            and t and t[-1] in ('。', '一')):
        _qsf = _qsf_plan(pi, sl, step, m, t[-1])
        if QSF_DBG:
            _qsf_audit(pi, sl, t, step, m)
    out = []
    k = 0                                                    # 当前格号(挤格标点不推进)
    for ci, ch in enumerate(t):
        k += gap_at.get(ci, 0)                               # 该字符前的空格格(taskJ-B): 只推进不落墨
        if ci == n - 1 and _qsf is not None and _qsf['action'] == 'replace':
            ch = '」'                                        # 1:1 码位替换(字数/格数不动; 渲染为 ﹂)
        if ch in PUNCT_HANG and k > 0:                       # 标点: 贴前一字格右下区(单独字号)
            tx = sl['x0'] + PUNCT_DX * pitch if sl else xc - pitch / 2.0 + PUNCT_DX * pitch
            # 锚点 = **前一字格顶**(PUNCT_DY 的标定语义, 见 §1.956): 循环变量 k = **下一个空闲
            #   格号**, 故前一字格号恒为 k-1(挤格时标点就在该格内, 占格时标点自占 k 格 -> 前字仍是
            #   k-1)。位置公式与 PUNCT_CELL 无关, 只有格号推进量不同(占格书: 下一字顺延一格)。
            ty = top + (k - 1) * step + PUNCT_DY * step
            dx, dy = PUNCT_INK.get(ch, (0.47, -0.36))        # 字形墨心相对锚点(em)
            out.append(_put_tex(ch, tx - XSCALE * dx * Fp, page_h - (ty - dy * Fp), Fp,
                                clamp=_pv_clamp_on(m)))
            k += int(round(PUNCT_CELL))
            continue
        y_put = page_h - (y0 + k * step)
        out.append(_put_tex(ch, x_put, y_put, F, clamp=_pv_clamp_on(m)))
        k += 1
    if _pm is not None:
        # 圈点画在让出来的首格(原 T0 起的一格), 字号同正文 —— 源书圈点也是整格大小。
        # y 加 PARA_MARK_DY 补偿: ⊙ 的墨心比汉字锚点高 0.92em(实测), 不补会画高一格。
        # 方向: TeX 的 y **向上增大**(字往下走 y_put = page_h - y_pt 递减),
        #   所以「再往下移动」要**减** DY —— 加号会把圈的墨心又推高一格(实测踩过)。
        _Fm = F * PARA_MARK_SIZE
        out.append(_put_tex('⊙', xc - XSCALE * _Fm / 2.0,
                            page_h - _T0 - PARA_MARK_DY * _Fm, _Fm,
                            clamp=_pv_clamp_on(m)))
    if _qsf is not None and _qsf['action'] == 'append':
        # 补字(taskCM): 源书尾格有引号墨而 OCR 完全没给这个字(末字「。」是源书里**前一个**句号),
        #   故追加一个 \put —— 既有字的 k/step/top 全不变, 只多画这一个引号。
        #   落位用**源图实测墨顶**(run[0]) 而非渲染格位: 合并列被均分压缩, 渲染格位比源墨高 1-2 格。
        out.append(_put_tex('」', x_put, page_h - (_qsf['run'][0] + INK_ASC * F), F,
                            clamp=_pv_clamp_on(m)))
    return out, top + ink_h + (max(k, 1) - 1) * step

def _nf_hrow_page(k, pi):
    """无版框页的**横排页**判据: 行盒「宽扁」(w/h >= NF_HROW_AR)且这样的行 >= 2 条。
    实测 wz7 末段是现代排印附錄(古(俗)今字對照表 / 版權頁): 表格行是**横排**短行(行盒 w/h 7-18),
    §1.975 伪槽格按设计不处理(它要「长竖行」= 竖排列) -> 这类页整页落回 v2 流式, 而 v2 的
    竖排拟合(字号/列距/列高)对它全不适用 -> 实测版權頁 15 条 span 出页 217pt、字表页 0 字。
    返回该页的横排行 (阅读序 = 自上而下), 无则 []。"""
    ph = _nf_page_px(pi)[1]
    rows = [r for r in all_rows.get(k, [])
            if len(r[4]) >= 2 and (r[3] - r[2]) > 0 and (r[1] - r[0]) / (r[3] - r[2]) >= NF_HROW_AR
            and (r[3] - r[2]) / 2.0 >= 6.0 and (r[3] - r[2]) < 0.5 * ph]
    if len(rows) < 2: return []
    # 横排行须占本页字数的 NF_HROW_CHAR 以上 —— 免得把「竖排正文页里夹一两行横排说明」判成横排页
    tot = sum(len(r[4]) for r in all_rows.get(k, []) if r[4].strip())
    if tot <= 0 or sum(len(r[4]) for r in rows) < NF_HROW_CHAR * tot: return []
    return sorted(rows, key=lambda r: r[2])

def _nf_hrow_puts(k, pi):
    """横排页兜底渲染: 每条 OCR 行 -> 一行**横排**文字(逐字 \put, 与竖排同一套字号换算)。
    几何: 字盒左缘 = 行盒左缘 + i x 步进(步进 = 行盒宽 / 字数, 字居中于格); 字号 = 行墨迹高 / INK_RATIO
      (与竖排同口径, 源图墨迹高就是字高); 基线 = 行墨迹顶 + INK_ASC x 字号(与竖排 col_puts 同源)。
    只做「把字放回源书位置」这件事 —— 横排页不做标点挤格/横向压缩(那是竖排列的排版规则)。
    返回 (tex 列表, 渲染行数, 渲染字数)。"""
    rows = _nf_hrow_page(k, pi)
    if not rows: return [], 0, 0
    ph = page_h
    out, nch = [], 0
    for x0, x1, y0, y1, t in rows:
        t2 = t.replace('\n', '')
        n = len(t2)
        if n < 1: continue
        F = max(6.0, min((y1 - y0) / 2.0 / INK_RATIO, 0.12 * ph))
        # 行盒夹回页内(OCR y/x 对本册末段有系统缩放: 实测字表页末行盒底越出页幅 29pt)
        rx0 = max(0.0, min(x0 / 2.0, page_w - 4.0))
        rx1 = min(page_w - 1.0, max(x1 / 2.0, rx0 + 4.0))
        step = (rx1 - rx0) / n
        if step <= 0: continue
        F = min(F, step / 0.98)                      # 字盒不超格宽(否则相邻字叠)
        # 竖直方向同样夹回页内: 实测该页末行行盒底越出页幅 —— 且**竖排字盒的 span bbox 下缘
        #   = 基线 + 字号**(不是基线下沉), 故留 1.95F(墨顶 0.94F + 字盒 1F)才不出页;
        #   行被上移的量 <= 一行高, 观感无损(源行盒 y 也是 OCR 给的, 本就有 ±20pt 漂移)
        ry0 = max(0.0, min(y0 / 2.0, ph - 1.95 * F - 1.0))
        y_put = ph - (ry0 + INK_ASC * F)
        for i, ch in enumerate(t2):
            x_put = rx0 + i * step + max(0.0, (step - F) / 2.0)
            out.append(_put_tex(ch, x_put, y_put, F))
            nch += 1
    print('  [横排页兜底] p%d %d 行 %d 字(源书该页是横排短行: 字表/版权页等)' % (pi + 1, len(rows), nch))
    return out, len(rows), nch

def _nf_rescue_rows(pi, m, rows, slots, pairs, skip=(), placed=None):
    """无版框页: 未配对正文行的**残余墨迹列补救** -> tex 列表。
    背景(taskP): 段尾/詩行这类短列在墨迹列带检测(cov=0.12)里会漏检(nf_fill_bands 补不出的残余),
    于是「行数 > 槽数」, DP 配不上的行被静默丢弃 —— 实测源页 1206 两列 78 字整列不渲染。
    做法(与 §1.99 page_puts_loose 的残余列同源, 几何全部取源图墨迹):
      ① 残余墨迹 = 本页墨迹 - 已配对槽的 x 带(各外扩 1px); 其 x 投影在版心内的列带按阅读序取;
      ② **必须真有墨**: 该带内墨迹 run >= 2 条且字高中位 >= 0.5 x 本页字号(碎墨/扫描噪点达不到);
         字高 > 1.35 x 本页字号 的也不收(粘连长 run, 会把字高测成整列高);
      ③ 列顶/底取带内实测(夹在版心内), 字号 = 带内字高中位/INK_RATIO, 走 col_puts 渲染(标点/压缩同源)。
    返回 tex 列表(未配对行多于残余列时多出的行仍不渲染 —— 有墨才画, 不凭空补位)。

    taskCJ4(R4) 三条口径修正(修前 8 页共丢 23 字, 逐页追踪见 docs/vert_taskCJ4_report.md):
      a) **已占用带带 y 段**: 配对行只占用它自己的 OCR y 带。页码/书眉与正文列同 x 带、不同 y 段
         是竖排常见版式(实测 p1023 四六三 / p1609 四三九 / p1067 五〇七 ...), 旧口径「x 重叠即
         已用」把整行拒掉 -> 丢字。现在 x 重叠但 y 不重叠 -> 允许; 渲染窗取**本行 y 带**
         (不占别的行的 y 段, 与 _split_slot_y 的 y 拆槽同源)。
      b) **y 窗择优**: 旧口径统计窗 = 伪版心 ∪ 本行 y 带(taskU-C) —— 与已用列共 x 时会把别人的
         墨一起统计(列顶/列底/字号全错: v6 的页码被摊满整列, 实测 p1023「四」y267→「三」y1068),
         短列时覆盖率又被整页高稀释(实测 p702「唱：」在整页高上覆盖率 2.2% < 4% -> 带都检不出)。
         现在同时试「本行 y 窗」与「宽窗」, 取 **run 数与排版格数最接近**者(平手取宽窗 = 旧口径)。
      c) **大字号行 / 单字行**: 旧 `_ok_stat` 把 > 1.35x 页字号一律拒(本为挡粘连长 run), 但 run
         数与字数相称的标题/回目行(实测 p1609「第九十六回」5 run / 5 字, 字号 1.40x)是真列;
         单字页码(实测 p1503「三」)又因 nr >= 2 拒。现在前者的判据改为「run 数与格数相称」,
         后者改按「单字墨迹跨度/带宽」定字高。"""
    g = m['g']
    ink = _frame_ink(pi, g)
    il, ir, it, ib = g['in_l'], g['in_r'], g['in_t'], g['in_b']
    # 「已占用」的列带 = 已配对槽内**实测墨迹带** × **该配对行自身的 OCR y 带**(taskCJ4):
    #   槽格是半列距宽、几乎铺满版心, 拿槽格当占用会把所有列判成已用 -> 落在「残余墨迹」上的
    #   补救一个也找不出(实测源页 1206 残余列 = 0); 但只用 x 带又会把「同列不同 y 段」的页码/
    #   书眉误判成已占用。y 带必须取**配对行**而不是槽的 top/bot: 槽 top/bot 是该列全部墨迹
    #   (含未配对行), 会把同列剩余 y 段也标成已用。
    used = []
    for _i, _j in pairs:
        sl = slots[_j]
        _ry0, _ry1 = rows[_i][2] / 2.0, rows[_i][3] / 2.0
        for x0, x1 in _ink_bands(ink, sl['x0'] - 2, sl['x1'] + 2, it, ib, cov=0.05):
            used.append((x0, x1, _ry0, _ry1))
    unmatched = [ri for ri in range(len(rows))
                 if ri not in skip and not any(i == ri for i, _j in pairs)]
    ya, yb = int((it + 2) * 2), int((ib - 2) * 2)
    if NF_SLOT_DBG:
        print('    [补救诊断] p%d 未配对行 %d 已用列带 %d: %s' % (
            pi + 1, len(unmatched), len(used),
            ['%.0f-%.0f/%.0f-%.0f' % b for b in used]))
    hms = sorted(s['hm'] for s in slots if s['hm'] > 0)
    Fmed = (hms[len(hms) // 2] / INK_RATIO) if hms else 0.0
    pitch = g.get('pitch') or (ir - il) / max(1, len(slots))

    def _font_est(st, nc, span):
        """本列字号估计(taskCJ4 + taskCK): run 高中位口径对**多笔画数字**失效 —— 「二/三」的
        run 是横画(高 3-4pt), hm/INK_RATIO 只有 3.5pt, 而整列跨度/字数 ≈ 17pt。故:
          · run 口径可信(F_run >= 0.7 x 页字号) -> 用 F_run(普通正文列, 与修前同值);
          · run 口径不可信 -> 跨度口径, **但仅当跨度能容纳 n 字**(span/nc 在页字号 0.6-1.5 倍内,
            taskCK 判据): F = span/nc/0.9(竖排 n 字跨度 ≈ n x 字号);
          · 跨度也不可信 / 单字 -> 0.9 x 页字号(单字墨迹(一/三)的 run 高与跨度都不反映字号)。"""
        F_run = st['hm'] / INK_RATIO
        if Fmed > 0 and F_run >= 0.7 * Fmed: return F_run
        if nc >= 2 and span > 0:
            _Fs = span / float(nc) / 0.9
            if Fmed <= 0 or (0.6 * Fmed <= _Fs <= 1.5 * Fmed):
                return _Fs
        return 0.9 * Fmed

    def _ok_stat(st, nc, bw, fe):
        """带内墨迹是否「像正文列」(taskCJ4 扩展):
        · 字号必须在页字号 0.5-1.35 倍内; 大字号行(F0 > 1.35x)若 run 数与格数相称
          (每条 run 一个字)则是真标题/回目列, 收(原口径只挡粘连长 run);
        · nc >= 2 要求 run >= 2(挡碎墨); 单字行按带宽像一个字判断(细线/碎片 < 0.4 x 字号)。"""
        if st['nr'] < 1 or st['hm'] <= 0: return False
        if nc == 1:
            return 0.4 * fe <= bw <= 1.6 * fe
        if st['nr'] < 2: return False
        if Fmed <= 0: return True
        if 0.5 * Fmed <= fe <= 1.35 * Fmed: return True
        return fe > 1.35 * Fmed and 0.6 * nc <= st['nr'] <= 1.2 * nc + 1.0

    ph_pt = g['page_px'][1] / 2.0
    def _ynwin(r):
        """本行的 y 统计窗(taskU-C): 伪版心 y 范围 ∪ **该行自带 OCR y 带** —— 短行(目录页的
        「第N回」、段尾短列)在伪版心**之上**时会被 it 截掉(实测源页 45: 伪版心顶 293.6 来自长行
        (回目列), 而「第N回」墨迹在 240-322 -> 截掉后列顶算成 299 -> 整列被压 59pt、源书的两处
        列内空档也检不出)。夹回纸幅内。"""
        y0 = max(0.0, min(r[2] / 2.0 - 2.0, ph_pt)); y1 = max(0.0, min(r[3] / 2.0 + 2.0, ph_pt))
        return min(it + 2.0, y0), max(ib - 2.0, y1)

    def _ocr_band(r, ywin):
        """**OCR 列框兜底**: 行自带 x 带 ± 一列距 -> 窗内最靠窗心的**未被占用**墨迹列带
        (宽 >= 8pt, 覆盖率 >= 0.04)。OCR x 有系统缩放(本书 1.07-1.20)与相位漂移, 故只用它**定邻域**,
        列位仍取窗内实测墨迹带心(自纠偏)。
        ywin(taskCJ4): 本窗的 y 范围(pt) —— 调用方传「本行 y 窗」或「宽窗」两种口径各试一次。
        「已占用」判据(taskCJ4) = x 重叠 **且** y 重叠: 页码/书眉与正文列同 x 带时, 只要 y 段
        不重叠就是该列剩余空间, 允许落位(与 _split_slot_y 的 y 拆槽同源); y 重叠 -> 不叠字。
        返回 (a, b) 或 None。"""
        import numpy as np
        cx = (r[0] + r[1]) / 4.0                     # OCR 行 x 中心(px/2 = pt)
        wa = max(il, cx - pitch); wb = min(ir, cx + pitch)
        if wb - wa < 8: return None
        _y0, _y1 = ywin
        sub = ink[int(_y0 * 2):int(_y1 * 2), int(wa * 2):int(wb * 2)]   # 全墨迹(伪槽格页版心内没有「残余」可言)
        if sub.size == 0: return None
        colc = sub.mean(axis=0)
        _ry0, _ry1 = r[2] / 2.0, r[3] / 2.0
        best = None
        for i0, i1 in _runs(colc > 0.04, 4):
            if i1 - i0 < 16: continue
            a2, b2 = wa + i0 / 2.0, wa + i1 / 2.0
            if any(a2 < b3 - 1 and a3 < b2 - 1 and _ry0 < b4 + 2.0 and a4 < _ry1 + 2.0
                   for a3, b3, a4, b4 in used):
                continue
            c = (i0 + i1) / 2.0
            if best is None or abs(c - (cx - wa) * 2) < abs(best[2] - (cx - wa) * 2):
                best = (i0, i1, c)
        if best is None: return None
        return (wa + best[0] / 2.0, wa + best[1] / 2.0)

    def _band_y_runs(a, b):
        """带内 x 投影 -> 全页 y 墨迹 run [(y0,y1)] pt(笔画级; 不做 x 内缩)。
        用途: 从「整列墨迹」里切出**本行自己的 y 段**(页码/书眉与正文列同 x 时必需)。"""
        xa, xb = int(a * 2), int(b * 2)
        if xb <= xa: return []
        m = ink[:, xa:xb].any(axis=1)
        return [((y0) / 2.0, (y1 + 1) / 2.0) for y0, y1 in _runs(m, 1)]

    def _segment(rs, r):
        """从带内 run 表里取「本行」的墨迹段(taskCJ4): 以**与本行 OCR y 带相交**的 run 为种子,
        向两侧扩到 run 间距 <= 0.5 x 页字号; 无相交 run 时取离行心最近的一条为种子。
        只在种子范围**外**扩, 不在种子内部切 —— 普通正文列(OCR 行盒覆盖整列)种子即全部 run ->
        段 = 整列, 与修前口径逐位相同; 页码/回目首行(行盒只覆盖一段)才被切到本行。"""
        if not rs: return None
        ry0, ry1 = r[2] / 2.0, r[3] / 2.0
        seeds = [i for i, q in enumerate(rs) if q[0] <= ry1 + 2.0 and ry0 - 2.0 <= q[1]]
        if seeds:
            i0, i1 = seeds[0], seeds[-1]
        else:
            c = (ry0 + ry1) / 2.0
            j = min(range(len(rs)), key=lambda k: abs((rs[k][0] + rs[k][1]) / 2.0 - c))
            i0 = i1 = j
        gap = max(4.0, 0.5 * Fmed)
        while i0 > 0 and rs[i0][0] - rs[i0 - 1][1] <= gap: i0 -= 1
        while i1 < len(rs) - 1 and rs[i1 + 1][0] - rs[i1][1] <= gap: i1 += 1
        return rs[i0:i1 + 1]

    puts, nok = [], 0
    for idx, ri in enumerate(unmatched):
        a = b = None; st = None; ywin_sel = None; fe = 0.0
        nc = n_cells(rows[ri][4])
        # taskCJ4: 两种 y 窗各试一次找 x 带 ——
        #   ① 本行 y 窗: 只投影本行自己的墨迹(短列/与已用列共 x 的页码书眉; 覆盖率不被整页高稀释);
        #   ② 宽窗: 伪版心 ∪ 本行 y 带(taskU-C 旧口径; OCR 行盒比墨迹紧时靠它补全列顶/列底)。
        # 找到 x 带后不再直接用窗统计, 而是从**带内整列墨迹**里切出与本行 OCR y 带相交的段
        # (_segment) —— 这样 OCR 行盒偏紧(p1067 第三字 y1133 被行盒切掉)也能补全。
        # 选择 = 段内 run 数与排版格数最接近者(平手取宽窗, 保证普通短列与修前逐位相同)。
        _r_win = (max(0.0, rows[ri][2] / 2.0 - 2.0), min(ph_pt, rows[ri][3] / 2.0 + 2.0))
        _w_win = _ynwin(rows[ri])
        _cands = []
        for _yi, _yw in ((1, _r_win), (0, _w_win)):
            got = _ocr_band(rows[ri], _yw)
            if not got:
                if os.environ.get('VERT_RESCUE_DBG'):
                    print('      [补救候选] p%d 行[%d] %s窗 x带落空' % (
                        pi + 1, ri, '本行' if _yi else '宽'))
                continue
            a2, b2 = got
            _seg = _segment(_band_y_runs(a2, b2), rows[ri])
            if not _seg: continue
            _sy0, _sy1 = _seg[0][0], _seg[-1][1]
            # taskCK: 纯数码行(页码)的笔画是 2-4pt 细横画, 4pt run 下限会把上半字滤掉
            #   -> 只余下半字的 top/bot, 字号被后续字号保护压到 4pt; 数码行用 1pt 下限取全笔画。
            _is_num = bool(rows[ri][4].strip()) and all(
                c in NUM_CHARS for c in rows[ri][4].replace('\n', '').strip())
            st2 = _band_stats(ink, a2, b2, _sy0, _sy1, pad=0.0, min_h=(1.0 if _is_num else 4.0))
            fe2 = _font_est(st2, nc, _sy1 - _sy0)
            _ok = _ok_stat(st2, nc, b2 - a2, fe2)
            if os.environ.get('VERT_RESCUE_DBG'):
                print('      [补救候选] p%d 行[%d] %s窗 带x%.1f-%.1f 段y%.1f-%.1f nr%d hm%.1f '
                      'bw%.1f fe%.1f ok=%s' % (
                          pi + 1, ri, '本行' if _yi else '宽', a2, b2, _sy0, _sy1,
                          st2['nr'], st2['hm'], b2 - a2, fe2, _ok))
            if not _ok: continue
            _cands.append((abs(len(_seg) - nc), _yi, a2, b2, st2, (_sy0, _sy1), fe2))
        if _cands:
            _cands.sort(key=lambda t: (t[0], t[1]))       # run 数差最小; 平手取宽窗(_yi=0)
            _s0 = _cands[0]
            a, b, st, ywin_sel, fe = _s0[2], _s0[3], _s0[4], _s0[5], _s0[6]
        if NF_SLOT_DBG:
            print('    [补救诊断] p%d 行[%d] %-12s -> %s' % (
                pi + 1, ri, rows[ri][4][:12],
                ('x%.1f-%.1f nr%d hm%.1f F%.1f y%.1f-%.1f %s' % (
                    a, b, st['nr'], st['hm'], fe, ywin_sel[0], ywin_sel[1],
                    '本行窗' if ywin_sel == _r_win else '宽窗'))
                if a is not None
                else ('落空(OCR x %.1f-%.1f)' % (rows[ri][0] / 2, rows[ri][1] / 2))))
        if a is None: continue                       # 两条路都没有可信墨迹 -> 不渲染(不凭空补位)
        F = round(max(9.0, fe), 1)
        _yy0, _yy1 = ywin_sel
        Tb = max(st['top'] if st['top'] is not None else _yy0, 2.0)
        Bb = min(st['bot'] if st['bot'] is not None else _yy1, ph_pt - 2.0)
        ink_h0 = INK_RATIO * F
        step = (max(1.0, min((Bb - Tb - ink_h0) / (nc - 1), (ib - it - 4.0 - ink_h0) / (nc - 1)))
                if nc > 1 else 0.0)
        m2 = {'font': F, 'step_cap': max(step, 0.1), 'band_t': Bb, 'band_b': Bb, 'block_b': ib - 2.0,
              'w': ir - il, 'note': [], 'body': [], 'g': g, 'slots': []}
        # taskU-C: 带上**本列墨迹 run 表** -> col_puts 里的 fit_gaps 才能检出列内空隙(源书目录页
        #   「第N回 | 回目上半 | 回目下半」三段之间的空档就靠这条还原); 不带则整列按等格铺满。
        # taskCJ4: run 表按**选中的 y 窗**取 —— 共 x 的页码/书眉不能用整列(含别的行)的 run,
        #   否则 fit_gaps 会把别人的行间空档当成本行的字间空隙。
        sl = {'x0': a, 'x1': max(b, a + 1.0), 'nr': st['nr'], 'hm': st['hm'],
              'step': st['step'], 'top': Tb, 'bot': Bb,
              'runs': _slot_runs(ink, a, b, _yy0, _yy1)}
        p, _ = col_puts(rows[ri][4], (a + b) / 2.0, m2, sl, None, pi)
        puts += p
        nok += 1
        if placed is not None: placed.append(ri)
        print('    [短列补救] p%d %-14s 残余列 x%.1f-%.1f 顶%.1f 底%.1f 字高%.1f -> 字号%.1f 步进%.1f' % (
            pi + 1, rows[ri][4][:14], a, b, Tb, Bb, st['hm'], F, step))
    if nok:
        print('  [短列补救] p%d 未配对行 %d -> 渲染 %d' % (pi + 1, len(unmatched), nok))
    return puts

def _toc_puts(k, pi, m):
    """目录页独立渲染(taskCH): (x 带, y 层) 二维配对 -> 逐字 \\put。
    输入 = g['toc_rows'](**原始 OCR 行**, 未做 nf_join_rows / page_rows 的列内合并)。

    做法:
      ① 行按 x 心归列(容差 NF_TOC_COL_TOL x 列距), 列按阅读序(右->左);
      ② 列内行按 y 升序 —— **每一行就是一层**; 不再用 _split_slot_y 从墨迹反推层;
      ③ 每行建一个**自带 OCR y 跨度**的槽(top/bot = 该行行盒), 用 col_puts 渲染:
         · 逐行字号: 墨迹 run 的 75 分位字高(_big_hm, 滤掉点线/标点碎片) / INK_RATIO;
           不可靠时依次退回: 页码页级中位(全数码短行) -> 本列可靠字高中位 -> 页字号;
         · 行内 \\n(整列被 OCR 合成一个框, 实测 p563/p1171): 整行一个槽, 文本去 \\n,
           槽跨度 = 整列 -> 用 col_puts 的常规步进口径 + fit_gaps(墨迹 run)还原层间空隙;
      ④ 只渲染「整行 y 跨度 >= 4pt」的行; 书眉/页码(special_rows 已认领)与页边水印
         (_nf_margin_artifact)不在这里画(避免与 special_tex 重复); 单字孤立列(非数码)视作
         扫描馆藏标签碎片丢弃(实测 p561「館」是「國家圖書館」条码被 OCR 拆剩的一字)。
    返回 (tex 列表, pairs, ok); ok=False 时调用方自动走兜底。"""
    g = m['g']
    raw = list(g.get('toc_rows') or [])
    ph = g['page_px'][1] / 2.0
    pitch = g.get('pitch') or ((g['in_r'] - g['in_l']) / max(1, len(m['slots'])))
    if not raw or pitch <= 0:
        return [], [], False
    ink = _frame_ink(pi, g)
    REF = m['font']
    claimed = set((c[2], c[3], c[4], c[5], c[1]) for c in special_rows(k))
    _srow = _SPECIAL_ROWS.get(k) or set()
    _ssig = _SPECIAL_SIGS.get(k) or set()
    if os.environ.get('VERT_NF_TOC_DBG') and _ssig:
        print('    [TOC-SIG] p%d 特殊行签名 %d 条(只剔这些行, 不剔整段 x 带)'
              % (pi + 1, len(_ssig)))
    rows = []
    for r in raw:
        x0, x1, y0, y1, t = r
        if not t.strip() or x1 <= x0 or y1 <= y0:
            continue
        if (x0, x1, y0, y1, t) in claimed:
            continue
        if _nf_margin_artifact(r, m):
            continue
        # §1.995 认领的**具体行**不在这里画(由 _sp_puts 渲染); **不按 x 带整段剔** ——
        # 实测 p48「玳安嬉遊蝴蝶巷」被误判成标题(字号 1.65x), 它的 x 带 569-641 覆盖了
        # 第四十九回/第五十回两整列, 按带剔会连丢 30 字。
        if id(r) in _srow or (x0, x1, y0, y1, t) in _ssig:
            continue
        rows.append(r)
    if not rows:
        return [], [], False
    tol = NF_TOC_COL_TOL * pitch * 2.0                 # pt -> px
    cs = sorted(((r[0] + r[1]) / 2.0, i) for i, r in enumerate(rows))
    groups = []
    for c, i in cs:
        if groups and c - groups[-1][-1][0] <= tol:
            groups[-1].append((c, i))
        else:
            groups.append([(c, i)])
    cols = []
    for gr in groups:
        idxs = sorted((i for _c, i in gr), key=lambda i: rows[i][2])
        # 单字孤立列(非数码) = 扫描馆藏标签碎片(实测 p561「館」) -> 不渲染; 数码单字是页码, 保留
        if len(idxs) == 1:
            _t0 = rows[idxs[0]][4].replace('\n', '').strip()
            if len(_t0) == 1 and _t0 not in NUM_CHARS:
                continue
        cols.append({'idx': idxs,
                     'x0': min(rows[i][0] for i in idxs) / 2.0,
                     'x1': max(rows[i][1] for i in idxs) / 2.0,
                     'xc': statistics.median((rows[i][0] + rows[i][1]) / 4.0 for i in idxs)})
    if not cols:
        return [], [], False
    cols.sort(key=lambda c: -c['xc'])

    def _row_ink(r):
        """行框内墨迹 -> (F 可靠值或 None, OCR 步进兜底, 全部 run, 字级 run)。
        「字级 run」= 高 >= 0.45 x 墨高参照的 run: 点线(4-5pt)/标点碎片被滤掉, 否则 p54 的
        「回目……页码」合并且会被几十个点画 run 的中位拉成 4.5pt(实测)。"""
        x0, x1, y0, y1, t = r
        T, B = y0 / 2.0, y1 / 2.0
        rs = _slot_runs(ink, x0 / 2.0, x1 / 2.0, T, B, min_h=0.0)
        big = [q for q in rs if q[1] - q[0] >= 0.45 * INK_RATIO * REF]
        hm = _big_hm(big)
        F = hm / INK_RATIO if hm else 0.0
        n = max(1, _toc_seglen(t))
        Focr = (y1 - y0) / 2.0 / n
        return (F if 0.5 * REF <= F <= 1.5 * REF else None), Focr, rs, big

    info = [_row_ink(r) for r in rows]
    # 页码页级字号: 目录的页码是短数码行(2-3 字), 其墨迹多为横画(「一」「三」) -> _big_hm 测不出;
    #   用全页同类行(墨高法可靠者 + OCR 步进兜底)的中位, 再回填给测不出的数码行。
    _pn = []
    for r, (F, Focr, _rs, _big) in zip(rows, info):
        t = r[4].replace('\n', '').replace(' ', '').replace('　', '')
        if 1 <= len(t) <= 4 and all(c in NUM_CHARS for c in t):
            if F:
                _pn.append(F)
            elif 0.4 * REF <= Focr <= 1.5 * REF:
                _pn.append(Focr)
    Fpn = statistics.median(_pn) if _pn else 0.0
    puts = []
    pairs = []
    for ci, col in enumerate(cols):
        fs = [info[i][0] for i in col['idx'] if info[i][0]]
        Fcol = statistics.median(fs) if fs else REF
        for i in col['idx']:
            r = rows[i]
            x0, x1, y0, y1, t = r
            T = max(0.0, y0 / 2.0)
            B = min(ph, y1 / 2.0)
            if B - T < 4.0:
                continue
            text = t.replace('\n', '').strip()
            if not text:
                continue
            F, Focr, rs, big = info[i]
            if not F:
                _tt = text.replace(' ', '').replace('　', '')
                if 1 <= len(_tt) <= 4 and all(c in NUM_CHARS for c in _tt) and Fpn > 0:
                    F = Fpn
                else:
                    F = Fcol
            F = round(max(4.0, F), 1)
            # 步进参照: 字级 run 的中心差中位(滤掉点线); 无 -> 用字号
            cs2 = sorted((a + b) / 2.0 for a, b in big)
            ds = sorted(d for d in (cs2[j + 1] - cs2[j] for j in range(len(cs2) - 1))
                        if d >= 0.4 * F)
            _step = statistics.median(ds) if ds else F
            hm = _big_hm(big) or _big_hm(rs)
            _ys = '\n' not in t                # 单层行: 按本行 OCR 跨度铺满; 整列行: 常规步进
            sl = {'x0': col['x0'], 'x1': col['x1'], 'nr': len(big), 'hm': hm,
                  'step': _step, 'runs': big or rs, 'keep': [list(q) for q in (big or rs)],
                  'top': T, 'bot': B, 'ysplit': _ys}
            m2 = {'font': F, 'step_cap': F, 'band_t': T, 'band_b': B, 'block_b': B,
                  'w': g['in_r'] - g['in_l'], 'note': [], 'body': [], 'g': g, 'slots': []}
            p, _b = col_puts(text, col['xc'], m2, sl, None, pi)
            puts += p
            pairs.append((i, ci))
    if not puts:
        return [], [], False
    print('  [目录列] p%d %d 行 -> %d 列 %d puts (原始行 %d, 页码字号 %.1f)'
          % (pi + 1, len(rows), len(cols), len(puts), len(raw), Fpn))
    return puts, pairs, True


def page_puts(k, pi, m):
    """本页正文列: OCR 行(阅读序) 对齐 正文槽(阅读序) -> 逐字 \\put。
    返回 (tex 列表, 配对数, 是否适配)。双行小字页(实测 p157/p158/p192/p228: 24 列 = 12 槽 x2,
    每槽内左右两子列)按 2 倍子列重建槽位; 适配判据 = 配上行数 >= 0.8x 行数(不适配的页
    —— 章题页/大字数行页如 p3 9 行 2 槽/p156 23 行 1 槽 —— 交回 v2 流式排版)。"""
    if NF_TOC_BRANCH and m['g'].get('toc'):
        # taskCH: 目录页独立分支 —— 原始行按 (x 带, y 层) 二维配对, 不走下面的任何槽/补丁逻辑。
        return _toc_puts(k, pi, m)
    rows, _nrows, _orows = page_rows(k, m, pi)
    rows = sorted(rows, key=lambda r: -r[0])
    slots = sorted(m['body'], key=lambda s: -s['x1'])
    if _SPECIAL_BLOCK.get(k):                    # §1.995: 已被特殊行占用的 x 带不再参与配对
        slots = [s for s in slots if not _band_blocked(s['x0'], s['x1'], _SPECIAL_BLOCK[k])]
    R, C = len(rows), len(slots)
    # taskCE(默认关, VERT_NF_TOC=1 开): 目录页判据 —— 行心 x 聚成约 C 组、组均 >= 1.4 行,
    #   且行数达到 1.3 x C。真双行小字页的 2C 条行分居 2C 个 x 心, 组均 ~1.0, 不会命中;
    #   目录页每列的回次/回目/页码同 x 不同 y, 组均 ~2。命中后不走 _dual(按 x 拆子列会让
    #   上下分段的行互相串位), 改在 AB 块里按 y 拆子槽(点线不参与空隙判定)+ 位置配对。
    _toc = False
    if NF_TOC and m['g'].get('virtual') and R and C >= 4 and R >= 1.3 * C:
        _p0 = m['g'].get('pitch') or ((m['g']['in_r'] - m['g']['in_l']) / max(1, C))
        _xt = max(6.0, NF_TOC_GROUP * _p0 * 2.0)         # 同行心容差(px; 行心 = (x0+x1)/2 px)
        _sc = sorted((r[0] + r[1]) / 2.0 for r in rows)
        _ng = 1
        for _a, _b in zip(_sc, _sc[1:]):
            if _b - _a > _xt:
                _ng += 1
        _toc = (_ng <= C + 2 and R >= 1.4 * _ng)
        if os.environ.get('VERT_NF_TOC_DBG'):
            print('    [TOC判据] p%d 行%d 槽%d x组%d 组均%.2f 容差%.1f -> %s' % (
                pi + 1, R, C, _ng, R / float(_ng), _xt, 'TOC' if _toc else '否'))
    _dual = False
    if (not _toc) and C and 1.7 * C <= R <= 2.3 * C:     # 双行小字页: 槽内再分左右子列
        ink = _frame_ink(pi, m['g'])
        it, ib = m['g']['in_t'], m['g']['in_b']
        sub = []
        for s in slots:
            c = (s['x0'] + s['x1']) / 2.0
            for x0, x1 in ((c, s['x1']), (s['x0'], c)):  # 竖排: 先右子列
                rs = _slot_runs(ink, x0, x1, it, ib)
                hs = sorted(b - a for a, b in rs)
                # 不带 'runs': 双行小字子列的列几何本身不可靠(同槽双列、step 无实测), taskJ-B
                #   的空隙检测不适用该形态(该形态渲染另有已知遗留, 见 spec/vertical/07 §6)
                sub.append({'x0': x0, 'x1': x1, 'nr': len(rs),
                            'hm': (hs[len(hs) // 2] if hs else 0.0),
                            'step': 0.0,
                            'top': (rs[0][0] if rs else None), 'bot': (rs[-1][1] if rs else None)})
        print('  [双行小字] p%d 槽 %d -> 子列 %d (行 %d)' % (pi + 1, C, len(sub), R))
        slots = sub
        _dual = True
    # taskAB(默认关, VERT_AB_FIX=1 开): 无版框书且本页 OCR 坐标已标定到源图坐标系的页, 位置可信 ->
    #   ① 槽按 y 拆子槽(A); ② 用**全部**伪槽格参与配对(不只 m['body']: 大字号标题页的
    #   m['font'] 被标题带偏, 正文列会被划进 note -> m['body'] 只剩标题槽, 实测 p513 只剩 2 槽);
    #   ③ 位置口径配对(B: x/y 硬约束 + 位置代价, 两侧可跳过)。
    # taskCE: TOC 页即使 OCR 帧未标定也走这里 —— 伪版心由本页正文行盒定, 行与列带同在 OCR 帧,
    #   位置仍可比(实测 p53/p55 行心与列带心差 <= 0.5pt); y 拆槽用 TOC 口径(rmin 滤点线)。
    # taskCH2: 目录页的槽补丁已不存在 —— 目录页在 page_puts 开头由 `_toc_puts` 接管, 走不到这里。
    #   下面这条是**非目录页的槽集补足规则**(原 taskCG5「全列做槽」): 无版框页里页码这类短数码列
    #   墨高小, 会被判进 m['note'] -> m['body'] 少一槽 -> 行数 > 槽数时 DP 把页码行塞进右侧正文槽。
    #   实测删掉它: p969「四〇九」x106.4 -> x738.9、p491「四四七」x104.8 -> x563.1(非目录页,
    #   违反 taskCH2 ④.4「普通正文页一字不动」); p1736 不变。故保留为**非目录页**槽集选择规则,
    #   与目录分支零耦合(目录页永远走不到)。判据: 行数 > body 槽数 且 检测列数 >= 行数 -> 用全部列。
    if (m['g'].get('virtual') and len(rows) > len(slots)
            and len(m['slots']) >= len(rows) and len(m['slots']) > len(slots)):
        _n0 = len(slots)
        slots = sorted(m['slots'], key=lambda x: (-(x['x0'] + x['x1']), x.get('top') or 0.0))
        print('    [槽集补足] p%d 行%d > 槽%d, 检测列%d >= 行数 -> 改用全部列'
              % (pi + 1, len(rows), _n0, len(m['slots'])))
    _ab = (AB_FIX or _toc) and (not _dual) and m['g'].get('virtual') and (m['g'].get('fixed') or _toc)
    if _ab:
        # 行序改按「x 带分组(相邻列心距 < 0.4 列距算同带) + 带内 y 升序」: 同一条 x 带里的
        #   书眉/页码/标题行行心可能差几 pt(实测 p87 差 6pt, p509 差 6pt), 直接按 x0 降序会把
        #   页码排到书眉前面 -> 拆槽后页码顶到书眉子槽上(实测 p87/p509 少了 19 字书眉、多画了页码)。
        #   不做 round 分桶: 桶边界上的 6pt 差会落到相邻两桶(实测 p509)。
        _px_pitch = (m['g'].get('pitch') or 0.0) * 2.0
        _tol = max(8.0, 0.4 * _px_pitch) if _px_pitch > 0 else 24.0
        _sr = sorted(rows, key=lambda r: -(r[0] + r[1]))
        rows = []
        _i = 0
        while _i < len(_sr):
            _c0 = (_sr[_i][0] + _sr[_i][1]) / 2.0
            _j = _i + 1
            while _j < len(_sr) and _c0 - (_sr[_j][0] + _sr[_j][1]) / 2.0 <= _tol:
                _j += 1
            rows.extend(sorted(_sr[_i:_j], key=lambda r: r[2]))
            _i = _j
        if AB_ALLSLOTS or _toc:
            # 位置口径下**不剔除** §1.995 特殊行占用的槽: 特殊行已从 all_rows 摘掉, 对应子槽没有
            #   行可配(会被跳过); 反而要保留被占用的槽去接同列**剩余**的行 —— 实测 p375 标题列
            #   三行里两行被特殊路径认领、剩下的「第二十二回」正需要落回该列(旧过滤把整槽删掉,
            #   该行既无槽可配、又因字高 1.46x 正文被残余列补救的 0.5-1.35x 判据拒绝 -> 整行丢失)。
            #   taskCE/TOC: 目录页的導讀/目錄标题槽常因 hm 偏小被判进 note, 也必须参与(否则
            #   对应行只能走残余列补救)。
            slots = sorted(m['slots'], key=lambda s: (-(s['x0'] + s['x1']), s.get('top') or 0.0))
        _it, _ib = m['g']['in_t'], m['g']['in_b']
        if _toc:
            # TOC: 槽的 y 窗扩到本页 OCR 行的 y 范围(回次在伪版心之上、页码在其下 —— 伪版心由
            #   长行(回目)定, 直接沿用会把这两段切掉, 槽 run 测不到它们 -> 拆不出子槽)。
            _ph = m['g']['page_px'][1] / 2.0
            _it = min(_it, max(0.0, min(r[2] for r in rows) / 2.0 - 2.0))
            _ib = max(_ib, min(_ph - 2.0, max(r[3] for r in rows) / 2.0 + 2.0))
        if AB_YSPLIT or _toc:
            _ink = _frame_ink(pi, m['g'])
            # 字步进参照取 min(槽步进上限, OCR 行 y 跨度/字数的中位): 槽步进在大字号标题页会被
            #   标题槽带偏(实测 p513 m['step_cap']=31.1, 而正文 OCR 步进中位 25.2) ——
            #   用 31.1 时标题三行之间 72.7pt 的空隙(阈 77.8)拆不开。
            _st = sorted((r[3] - r[2]) / 2.0 / len(r[4]) for r in rows if r[4] and '\n' not in r[4])
            _ocr_step = _st[len(_st) // 2] if _st else 0.0
            _caps = [x for x in (m.get('step_cap'), _ocr_step) if x and x > 0]
            _step_ref = min(_caps) if _caps else ((m.get('font') or 0.0) * 0.9)
            _rmin = NF_TOC_MINRUN * _step_ref if _toc else 2.0
            slots = [ss for s in slots for ss in _split_slot_y(
                _ink, s, _it, _ib, _step_ref, rows, rmin=_rmin)]
        _pitch = m['g'].get('pitch') or 0.0
        if _pitch <= 0 and slots:
            _pitch = (m['g']['in_r'] - m['g']['in_l']) / max(1, len(slots))
        pairs = _align_rows_slots(rows, slots, geom=(AB_GEOM or _toc), pitch=_pitch,
                                  step=(m.get('step_cap') or 0.0))
        if MONO_FIX and len(pairs) >= 2:
            _seq = [j for _ri, j in pairs]
            _nx = sum(1 for a, b in zip(_seq, _seq[1:]) if b < a)
            if _nx:
                _alt = _align_rows_slots(rows, slots,
                                         step=(m.get('step_cap') or 0.0))
                _s2 = [j for _ri, j in _alt]
                if _s2 and not any(b < a for a, b in zip(_s2, _s2[1:])):
                    print('    [单调守卫] p%d 位置口径有 %d 处交叉配对 -> 改按序口径(对 %d)'
                          % (pi + 1, _nx, len(_alt)))
                    pairs = _alt
        if os.environ.get('VERT_AB_DBG'):
            print('    [AB配对] p%d 行%d 槽%d -> 对%d | 槽: %s' % (
                pi + 1, R, len(slots), len(pairs),
                ' '.join('x%.0f-%.0f nr%d t%s b%s%s' % (
                    s['x0'], s['x1'], s['nr'],
                    ('%.0f' % s['top']) if s.get('top') is not None else '-',
                    ('%.0f' % s['bot']) if s.get('bot') is not None else '-',
                    'Y' if s.get('ysplit') else '') for s in slots)))
            print('    [AB配对] p%d 对: %s' % (pi + 1, pairs))
    else:
        pairs = _align_rows_slots(rows, slots, prior=(NF_POS_PRIOR if m['g'].get('virtual') else 0.0))
    if (not _ab) and m['g'].get('virtual') and NF_POS_PRIOR > 0 and R != C:
        # 位置先验只在「像本页这样行/槽数不等」时才可能有影响: 两种口径各算一次, **取渲染字数多的那个**
        #   (目标就是少丢字; 纯位置先验会在个别页(实测源页 399/444)把本来配得上的行挤掉, 纯格数口径
        #   又会在源页 1206 那种「版心内有两列无列带(墨迹太少)」的页上整段平移 -> 各有胜负)。
        _p0 = _align_rows_slots(rows, slots, prior=0.0)
        if len(_p0) != len(pairs) or _p0 != pairs:
            _n0 = sum(len(rows[i][4]) for i, _j in _p0)
            _nP = sum(len(rows[i][4]) for i, _j in pairs)
            if _n0 > _nP:
                print('    [配平] p%d 位置先验口径少渲染 %d 字 -> 用纯格数口径(配对 %d vs %d)' % (
                    pi + 1, _n0 - _nP, len(_p0), len(pairs)))
                pairs = _p0
    puts = []
    prev_bot = None
    for ri, si in pairs:
        sl = slots[si]
        # taskCK: **行↔槽 y 跨度夹取**(只无版框伪槽格页)。槽 top/bot 是该 x 带**全部墨迹**的
        #   上下缘; 当同一 x 带里还有**另一条 OCR 行**(页码/书眉与正文列共 x 带, 或回目列被
        #   OCR 断开)时, 槽跨度会包含那条行的墨 —— col_puts 把本行少数字摊满整列, 与另行渲染的
        #   元素在 y 上交错(实测 p997 回目列槽 233-1115 含页码「四三七」墨, 回目 23 字被摊到
        #   1050 处与页码叠字; p705 回目列槽 274-1178 含页码「一四五」墨, 同理)。
        #   判据: 本行 OCR y 带盖不住槽跨度(< 75%) **且** 槽内确有一条与本行 y 段不重叠的
        #   其它 OCR 行(x 带相交) -> 把槽夹到本行 y 带(±半步进)。正常满列两条都不满足, 逐位不变。
        _st0, _sb0 = sl.get('top'), sl.get('bot')
        if (m['g'].get('virtual') and _st0 is not None and _sb0 is not None
                and _sb0 - _st0 > 0):
            _ry0, _ry1 = rows[ri][2] / 2.0, rows[ri][3] / 2.0
            _pad = max(2.0, 0.5 * (sl.get('step') or m.get('step_cap') or 0.0))
            _T1, _B1 = max(_st0, _ry0 - _pad), min(_sb0, _ry1 + _pad)
            if _B1 - _T1 > 0 and (_B1 - _T1) < 0.75 * (_sb0 - _st0):
                _other = False
                for _oj, _o in enumerate(rows):
                    if _oj == ri: continue
                    if min(_o[1], sl['x1'] * 2.0) - max(_o[0], sl['x0'] * 2.0) <= 0: continue
                    _oy0, _oy1 = _o[2] / 2.0, _o[3] / 2.0
                    if (_oy0 < _sb0 and _oy1 > _st0
                            and (_oy1 < _ry0 - _pad or _oy0 > _ry1 + _pad)):
                        _other = True; break
                # taskCK2: `_other` 只覆盖「多出的跨度来自另一条 OCR 行」这一种成因。
                #   实测 p86 的反例: 槽窗口左缘 819.7 恰等于邻列右缘, 邻列墨迹渗入该带,
                #   y 拆子槽的 top 被拉到 832(页码墨实际在 1181-1233), 而 832 处没有对应
                #   任何 OCR 行 -> _other=False -> 夹取不执行 -> 页码被摊到 y898、字号 72pt。
                #   兜底: 槽跨度 > 2.5 x 行跨度 时无条件夹取(正常满列比值 <1.5 不触发;
                #   p100 实测 40/51.7=0.77 逐位不变; p86 396.5/51.9=7.6 触发)。
                # 判据换成「槽跨度 vs 该行正常需要量」（上一版用 2.5x 行 OCR 跨度, 实测只修好
                #   p86 那种 2 字页码; p85 回目 18 字跨度 500pt 而槽 1110pt, 比值仅 2.2 漏掉）。
                #   need = 字数 x 步进(step_cap 已按 source 实测); 槽 > 1.6 x need -> 夹。
                #   正常满列 44 字 need 1122 vs 槽 1110 -> 不夹; p100 页码 51 vs 槽 40 -> 不夹。
                if (not _other) and ROWCLIP_SPAN and (_ry1 - _ry0) > 0:
                    _nc = len([c for c in rows[ri][4] if not c.isspace()])
                    _stp = sl.get('step') or m.get('step_cap') or 0.0
                    if _nc > 0 and _stp > 0 and (_sb0 - _st0) > ROWCLIP_FILL * _nc * _stp:
                        _other = True
                if _other:
                    sl = dict(sl); sl['top'], sl['bot'] = _T1, _B1
                    # run 表同口径夹取: 否则 fit_gaps 仍拿「页码/书眉那一段」的 run 当本列字位,
                    # 把本行文字往下摊(实测 p997 夹取后仍插 4 格、末字「陽」被推到 y1056 与页码叠字)。
                    if sl.get('runs'):
                        sl['runs'] = [r for r in sl['runs'] if r[1] > _T1 - 0.5 and r[0] < _B1 + 0.5]
                    if sl.get('keep'):
                        sl['keep'] = [r for r in sl['keep'] if r[1] > _T1 - 0.5 and r[0] < _B1 + 0.5]
                    if os.environ.get('VERT_ROWCLIP_DBG'):
                        print('    [行槽夹取] p%d 槽 x%.1f-%.1f %.1f-%.1f -> %.1f-%.1f | %s'
                              % (pi + 1, sl['x0'], sl['x1'], _st0, _sb0, _T1, _B1,
                                 rows[ri][4][:16]))
        # taskS: 槽首/槽尾的**引號类小墨**修剪(只 NF 路径; 见 _trim_marks)。放在这里做是因为
        #   它需要**文本反证**(首/末字是不是标点), 而文本要到「行 ↔ 槽配好」才有。
        if m['g'].get('virtual') and sl.get('keep'):
            _tp, _bt = _trim_marks(sl['keep'], rows[ri][4], _big_hm(sl['runs']), sl.get('step') or 0.0)
            if (_tp, _bt) != (sl['top'], sl['bot']):
                sl = dict(sl); sl['top'], sl['bot'] = _tp, _bt
        xc = (sl['x0'] + sl['x1']) / 2.0
        if os.environ.get('VERT_TT_DBG'):
            print('    [TT-DBG] p%d 槽 x%.1f-%.1f top=%s bot=%s step=%s hm=%s | F=%.2f INK_ASC=%.3f '
                  'INK_RATIO=%.3f PUNCT_DY=%.2f PUNCT_SIZE=%.2f | 文本 %s' % (
                      pi + 1, sl['x0'], sl['x1'], sl.get('top'), sl.get('bot'), sl.get('step'),
                      sl.get('hm'), m['font'], INK_ASC, INK_RATIO, PUNCT_DY, PUNCT_SIZE, rows[ri][4][:20]))
        p, prev_bot = col_puts(rows[ri][4], xc, m, sl, prev_bot, pi)
        puts += p
    # §1.975c 列框兜底重排(taskP2, 只无版框伪槽格页): 行数 > 槽数时, 未配对的行先尝试归到本页
    #   **未被正文配平用到的伪槽格**(即 `_metrics_finish` 按墨高判成「小字注」的格) —— 这些格子
    #   同样是源图上一条真列, 只是该列的墨迹 run 偏短被判成了小字。不这么做的话它们只能靠
    #   _nf_rescue_rows 的「残余列」路, 而那条路要求 OCR x 窗内找到未占用的列带 —— 实测源页 35 的
    #   3 条拉丁文正文列(OCR 帧未标定 -> 窗与已用带重叠) 全部落空, 整页少 131 字。
    #   落位后用**页字号**渲染(col_puts 的字号保护会按本列实测步进压字号), 有墨校验同 _nf_rescue_rows。
    #   只在「本页按正文口径已适配(配对 >= 0.8x行数)」时才做 —— 不适配的页会整页交回 v2 流式,
    #   这些 puts 会被丢掉(实测源页 29 大字节版页: 15 行对 5 槽, 兜底把 10 行塞进注格 = 白做且刷屏)。
    _placed_rows = set()
    # taskAB: 位置口径下**不走这条兜底** —— 它的 DP 不带位置约束(只按 run 数配), 会把未配对行
    #   塞进任意注格(实测 p513 把「第三十二回」放到 x480 的正文列上、与正文叠字)。位置口径下
    #   未配对行交 _nf_rescue_rows 按本行 OCR x 窗找源图残余列位。
    if (not _ab) and m['g'].get('virtual') and m['note'] and len(pairs) < R and len(pairs) >= 0.8 * R:
        left_rows = [ri for ri in range(R) if not any(i == ri for i, _j in pairs)]
        cand = sorted(m['note'], key=lambda s: -s['x1'])            # 阅读序(右->左), 与 rows 同序
        ink = _frame_ink(pi, m['g'])
        it, ib = m['g']['in_t'], m['g']['in_b']
        # taskCG: 占用互斥 —— 已被正文行配对的列不得再接第二行(实测 p54 第十八回
        #   被兜底塞进第十六回那列 x554.8-594.0, 整页列序变成 十五/十八/十六/十七)。
        _used_x = [(slots[j]['x0'], slots[j]['x1']) for _ri, j in pairs]

        def _ovl(a0, a1, b0, b1):
            return min(a1, b1) - max(a0, b0) > 0.6 * min(a1 - a0, b1 - b0)

        # taskCG: 空着的正文槽(自身位置优先的落点池)
        _free_slots = [sl2 for j2, sl2 in enumerate(slots)
                       if not any(j2 == j for _r, j in pairs)]
        if os.environ.get('VERT_CG_DBG'):
            print('    [CG-DBG] p%d 已占用列: %s' % (
                pi + 1, ' '.join('%.0f-%.0f' % ab for ab in _used_x)))
            print('    [CG-DBG] p%d 空闲槽: %s' % (
                pi + 1, ' '.join('%.0f-%.0f' % (x['x0'], x['x1']) for x in _free_slots)))
            print('    [CG-DBG] p%d 候选带: %s' % (
                pi + 1, ' '.join('%.0f-%.0f' % (x['x0'], x['x1']) for x in cand)))
            print('    [CG-DBG] p%d 未配对行: %s' % (
                pi + 1, ' | '.join('x%.0f-%.0f %s' % (rows[i][0] / 2.0, rows[i][1] / 2.0,
                                                      rows[i][4][:10]) for i in left_rows)))
        for ri, si in _align_rows_slots([rows[i] for i in left_rows], cand,
                                        prior=(NF_POS_PRIOR if NF_POS_PRIOR > 0 else 0.0)):
            sl = cand[si]
            if any(_ovl(sl['x0'], sl['x1'], a, b) for a, b in _used_x):
                _r0, _r1 = rows[left_rows[ri]][0] / 2.0, rows[left_rows[ri]][1] / 2.0
                _hit = [sl2 for sl2 in _free_slots
                        if _ovl(_r0, _r1, sl2['x0'], sl2['x1'])
                        and not any(_ovl(sl2['x0'], sl2['x1'], a, b) for a, b in _used_x)]
                if not _hit:
                    print('    [兜底互斥] p%d %-12s 目标带 x%.0f-%.0f 已被正文列占用且无空槽'
                          ' -> 不落位(避免串列)' % (pi + 1, rows[left_rows[ri]][4][:12],
                                                    sl['x0'], sl['x1']))
                    continue
                sl = _hit[0]
                _used_x.append((sl['x0'], sl['x1']))
                print('    [兜底互斥] p%d %-12s 改落自身位置 x%.0f-%.0f'
                      % (pi + 1, rows[left_rows[ri]][4][:12], sl['x0'], sl['x1']))
            st = _band_stats(ink, sl['x0'], sl['x1'], it, ib)
            if st['nr'] < 2: continue                              # 无墨/碎墨格: 不落位(不凭空补位)
            p, _b = col_puts(rows[left_rows[ri]][4], (sl['x0'] + sl['x1']) / 2.0, m, sl, None, pi)
            puts += p
            _placed_rows.add(left_rows[ri])
            print('    [列框兜底] p%d %-14s 注格 x%.1f-%.1f -> 按页字号渲染(该格墨高 %.1f < 正文 %.1f)'
                  % (pi + 1, rows[left_rows[ri]][4][:14], sl['x0'], sl['x1'], sl['hm'], m['font']))
        if _placed_rows:
            print('  [列框兜底] p%d 未配对行 %d -> 注格落位 %d' % (pi + 1, len(left_rows), len(_placed_rows)))
    # §1.975 短列补救(taskP, 只无版框路径): 行数 > 槽数时, 配不上的行会被静默丢弃 —— 实测
    #   源页 1206 因两列短列(段尾列)在列带检测(cov=0.12)里漏掉, 整列 78 字不渲染。
    #   补救 = 用「残余墨迹列」(已配对槽涂掉后仍有的墨迹)按阅读序配给未配对行, 有墨才渲染。
    _rescued = []
    if _NF['on'] and len(pairs) < R:
        puts += _nf_rescue_rows(pi, m, rows, slots, pairs, skip=_placed_rows, placed=_rescued)
    # taskU-C: 「残余列补救落位的行」是否计入适配判据 —— **默认关**(VERT_TOC_RESCUE_OK=1 开)。
    #   为什么要它: 目录页(源页 45 类)整页 13 列全由补救路径按源图墨迹列位/字号渲染(实测 12/13 行
    #   落位、字号 29.4 与源书一致 + 列内两处空档检出), 但它 0 对槽 -> 旧判据判「不适配」而整页回退
    #   v2 流式(流式按 OCR 行盒排 -> 「第N回」与回目挤成一列、无空档, 即用户反馈的「目录阅读性差」)。
    #   为什么默认关(**实测净损失**): 开后在 4 页各少 10-30 字(源页 45 -18 / 58 -10 / 230 -12 /
    #   294 -30, 全书字符量 128683 -> 128613)—— 补救路径"有墨才画", 配不上的列/字不渲染, 而 v2 流式
    #   按 OCR 行盒把该页所有行都画出来。**宁可版式差也不丢字**, 故默认关并在报告里如实登记。
    ok = ((not R) or (len(pairs) >= 0.8 * R)
          or (TOC_RESCUE_OK and len(pairs) + len(_rescued) >= 0.8 * R))
    print('  [正文列] p%d %d 行 -> %d 槽 (槽 run %s) 字号 %.1f 墨带 %.1f-%.1f 上限 %.2f %s' % (
        pi + 1, R, len(pairs), [s['nr'] for s in slots],
        m['font'], m['band_t'], m['band_b'], m['step_cap'],
        '' if ok else '<<不适配, 回退流式'))
    return puts, pairs, ok

def _band_stats(ink, x0, x1, it, ib, pad=2.0, min_h=4.0):
    """区带 x0-x1(pt) 内的墨迹 run 统计 -> {nr, hm, step, top, bot}(pt)。
    先剔「竖线列」(该列墨占比 > 0.6: 版框线/界行线 —— 否则长 run 贯穿内框, 字高会被测成框高),
    再按 page_metrics 同口径统计(run 高限 4pt..3×中位)。
    pad: y 窗两端内缩量(pt, 默认 2 = 原口径)。taskCJ4: 残余列补救传 pad=0 —— 它的 y 窗是
      **本行 OCR y 带**(短列/页码), 再内缩 2pt 会把首/末字的墨切掉(实测 p702「唱：」行高 57pt)。
    min_h(taskCK): 「像字 run」的高下限(pt, 默认 4 = 原口径)。**纯数码行(页码)传 1.0** ——
      页码「二/三」的笔画是 2-4pt 的细横画, 4pt 下限会把上半字整段滤掉, 只余下半字:
      实测 p70「二六」原口径 top/bot=1098.5/1116.5 (真值 1077/1116.5), 字号被后继字号保护
      压成 4pt、两字间距 1.3pt(审计列内叠字)。"""
    xa, xb = int(x0 * 2), int(x1 * 2)
    ya, yb = int((it + pad) * 2), int((ib - pad) * 2)
    z = {'nr': 0, 'hm': 0.0, 'step': 0.0, 'top': None, 'bot': None}
    if xb - xa < 2 or yb - ya < 4: return z
    sub = ink[ya:yb, xa:xb]
    sub = sub[:, sub.mean(axis=0) <= 0.6]
    if sub.shape[1] < 2: return z
    rs = [((ya + a) / 2.0, (ya + b + 1) / 2.0) for a, b in _runs(sub.any(axis=1), 1)]
    hs = sorted(b - a for a, b in rs)
    hm0 = hs[len(hs) // 2] if hs else 0.0
    cap = max(40.0, 3.0 * hm0)
    rs = [r for r in rs if min_h <= r[1] - r[0] <= cap]
    hs = sorted(b - a for a, b in rs)
    cs = sorted((a + b) / 2.0 for a, b in rs)
    ds = sorted(d for d in (cs[j + 1] - cs[j] for j in range(len(cs) - 1)) if d < 80)
    return {'nr': len(rs), 'hm': (hs[len(hs) // 2] if hs else hm0),
            'step': (ds[len(ds) // 2] if ds else 0.0),
            'runs': rs,          # taskS: 供 _big_hm 取「字 run 墨高」(排除标点碎片)
            'top': (rs[0][0] if rs else None), 'bot': (rs[-1][1] if rs else None)}

def page_puts_loose(k, pi, g, quiet=False):
    """框内兜底排版(任务D): 有版框但「无槽可配」的页(章题页/註釋页: p3/p156/p199/p210/p229)。
    现象: 这些页走 v2 流式回退(Tex 流动排版) —— 列位/字号取自 OCR 盒(坐标逐页伸缩 +10%),
      列从「版心右缘」起排且列高不受内框约束 -> 列底越过版框(~50-90pt), 首列字号大时还越右框
      (p3 論持久戰 4 处 span 越右框 12.5pt)。
    做法(几何全部以源图墨迹为准, 与 §1.98 同源): 每条 OCR 行 = 一列, 绝对定位:
      ① x: 内框内墨迹「列带」(_ink_bands, 覆盖阈值降到 0.12 以便带出短列/标题列) 按阅读序 + run 数
         走 _align_rows_slots 配对; 没配上的行(如标题列)退回「本行 OCR x 中心夹进内框」;
      ② 列顶/列底 = 内框顶/底内缩 2pt(整列装进版框 —— 修越框); 步进 = 源头自然步进与「装得下内框」
         的步进取小; 字号 = min(源测字号, 由装得下内框反解的上限), 再交 col_puts 渲染
         (标点挤格 §1.0 / 字号保护 一并生效)。
    返回 (tex 列表, 配对数)。
    quiet=True: 只算不打印(taskQ 遗留2 的「两口径择优」要先算一遍本路径的渲染字数, 若最终不采纳
      该口径, 它的诊断行不该出现在日志里 —— 免得日志与「实际走了哪条路」对不上)。"""
    ink = _frame_ink(pi, g)
    il, ir, it, ib = g['in_l'], g['in_r'], g['in_t'], g['in_b']
    T, B = it + 2.0, ib - 2.0
    avail = B - T
    if avail <= 20: return [], 0
    # 列带(源图墨迹) -> 伪槽(统计口径与 page_metrics 同: run 高 4..3×中位)
    slots = []
    for a, b in _ink_bands(ink, il, ir, it, ib, cov=0.12):
        if _SPECIAL_BLOCK.get(k) and _band_blocked(a, b, _SPECIAL_BLOCK[k]):
            continue                             # §1.995: 特殊行占用的带(西文行/标题署名列)
        st = _band_stats(ink, a, b, it, ib)
        slots.append(dict(st, x0=a, x1=b))
    slots.sort(key=lambda s: -s['x1'])                       # 阅读序: 右 -> 左
    rows = page_rows(k, {'g': g, 'note': [], 'body': []}, pi)[0]
    rows = sorted(rows, key=lambda r: -r[0])
    if not rows: return [], 0
    pairs = _align_rows_slots(rows, slots) if slots else []
    # 未配上的行(章题列等): 源图里「未被已配列带覆盖的残余墨迹」按阅读序补带 —— 大字距短列(4 字标题)
    #   的 x 向覆盖度仅 0.05, 列带检测(cov 0.12)抓不到, 但残余墨迹里它还在; 再兜底才用 OCR x 带。
    used = [(slots[j]['x0'], slots[j]['x1']) for _i, j in pairs]
    left = ink.copy()
    for a, b in used:
        left[int(it * 2):int(ib * 2), max(0, int(a * 2) - 2):int(b * 2) + 2] = False
    prof = left[int((it + 2) * 2):int((ib - 2) * 2), int(il * 2):int(ir * 2)].mean(axis=0)
    lb, i0 = [], None
    for i, v in enumerate(prof):
        if v > 0.04 and i0 is None: i0 = i
        elif v <= 0.04 and i0 is not None:
            if i - i0 >= 16: lb.append((il + i0 / 2.0, il + i / 2.0))
            i0 = None
    if i0 is not None and len(prof) - i0 >= 16: lb.append((il + i0 / 2.0, il + len(prof) / 2.0))
    lb.sort(key=lambda b: -b[0])                             # 阅读序: 右 -> 左
    unmatched = [ri for ri in range(len(rows)) if not any(i == ri for i, _j in pairs)]
    # 页级字号参考(配对上的列带字高中位): 兜底行的字号不得超过它的 1.35 倍 —— 粘连长 run(相邻字墨相连)
    #   会把「字高」测成整列高(实测 p210 一条带 hm=795.5 -> 字号 144pt), 用它兜住。
    hms = sorted(slots[j]['hm'] for _i, j in pairs if slots[j]['hm'] > 0)
    Fmed = (hms[len(hms) // 2] / INK_RATIO) if hms else 0.0
    # 未配对行的位置: 优先「残余墨迹列」(章题列不在列带栅格上, 覆盖度低), 异常/不足时退回「未用槽位」
    slot_c = [(il + (ir - il) * (k + 0.5) / N_COL_FRAME) for k in range(N_COL_FRAME)]
    used_c = [any(abs((slots[j]['x0'] + slots[j]['x1']) / 2.0 - c) < 0.6 * (slots[j]['x1'] - slots[j]['x0'])
                  for _i, j in pairs) for c in slot_c]
    free_slots = [c for c, u in zip(slot_c, used_c) if not u][::-1]   # 阅读序: 右 -> 左
    puts, npair, nfree = [], 0, 0
    for ri, r in enumerate(rows):
        t = r[4]; nc = n_cells(t)
        si = [j for i, j in pairs if i == ri]
        if si:
            bx0, bx1 = slots[si[0]]['x0'], slots[si[0]]['x1']
            st = slots[si[0]]; npair += 1
        else:
            idx = unmatched.index(ri)
            bx0, bx1, st = None, None, None
            if idx < len(lb):                                # 残余墨迹列(需通过异常检查)
                a, b = lb[idx]
                s2 = _band_stats(ink, a, b, it, ib)
                if s2['hm'] > 0 and (Fmed <= 0 or s2['hm'] / INK_RATIO <= 1.35 * Fmed):
                    bx0, bx1, st = a, b, s2
                    if not quiet:
                        print('    [兜底-残余列] %-14s x%.1f-%.1f 字高%.1f' % (t[:14], a, b, s2['hm']))
            if bx0 is None and nfree < len(free_slots):      # 未用槽位(等比栅格)
                bx0, bx1 = free_slots[nfree] - 8.0, free_slots[nfree] + 8.0
                nfree += 1
            if bx0 is None:                                  # 最后兜底: 自身 OCR x 带
                bx0, bx1 = r[0] / 2.0, r[1] / 2.0
            if st is None:
                st = _band_stats(ink, bx0, bx1, it, ib)
        # 字号 = 源图墨迹字高中位/ink比 —— 不能用「OCR/墨迹步进」反推: 大字距列(章题「論 持 久 戰」)
        #   步进是字号的 2 倍以上(实测 100pt vs 44pt), 按步进反推字号会撑爆(曾把 4 字标题算成 89pt)。
        # 字号上限还受「列带宽」约束: 源书单字墨宽 ≈ 0.5×字号(实测 35px@2x / 62px 格距) —— 粘连长 run
        #   会把字高测成整列高(实测 p210 hm=61.5-795), 用带宽容不下的大字号一律压回。
        F0 = (st['hm'] / INK_RATIO) if st['hm'] > 0 else max(9.0, (r[3] - r[2]) / 2.0 / max(1, nc) / 0.93)
        if Fmed > 0 and F0 > 1.35 * Fmed:                     # 字高异常(粘连长 run) -> 压回
            F0 = min(max(9.0, (bx1 - bx0) / 0.5), 1.35 * Fmed)   # 带宽容得下的字号 vs 页级字号上限
        F_fit = avail / (INK_RATIO + 0.9263 * max(1, nc - 1))  # 使 墨高 0.88F <= 0.95×步进 且整列装进内框
        F = round(max(9.0, min(F0, F_fit)), 1)
        xc = min(max((bx0 + bx1) / 2.0, il + F / 2.0), ir - F / 2.0)
        # 本列自然步进 = 带内墨迹跨度反推((跨度-墨高)/(格数-1)); 再夹「装得下内框」。
        #   sl.top/bot 一并取本列自然跨度(不是内框上下缘) —— col_puts 的满列判据与步进夹取都以它为准,
        #   否则大字距短列会被 1.30×cap 撑开(标题 4 字被摊到 130pt/字)。
        ink_h0 = INK_RATIO * F
        if st['top'] is not None and nc > 1 and nc - 1 <= st['nr'] <= nc + 2:
            # 带内 run 数与格数相符 -> 用带内墨迹跨度反推自然步进(大字距章题列靠这条还原)
            Tb = st['top']
            step = min(max(st['bot'] - Tb - ink_h0, 0.0) / (nc - 1), (avail - ink_h0) / (nc - 1))
            step = max(step, 1.0)
            Bb = min(Tb + ink_h0 + (nc - 1) * step, B)
        elif st['top'] is not None and nc > 1:
            # run 数与格数不符(粘连/残片) -> 跨度不可信: 顶对齐 + 常规步进(墨高上限内, 字号×1.08)
            Tb = st['top']
            step = min(F * 1.08, (avail - ink_h0) / (nc - 1))
            Bb = min(Tb + ink_h0 + (nc - 1) * step, B)
        else:
            Tb, Bb = T, B
            step = (st['step'] or (r[3] - r[2]) / 2.0 / max(1, nc))
            step = min(step, (avail - ink_h0) / max(1, nc - 1)) if nc > 1 else 0.0
        m2 = {'font': F, 'step_cap': max(step, 0.1), 'band_t': Bb, 'band_b': Bb, 'block_b': B,
              'w': ir - il, 'note': [], 'body': [], 'g': g, 'slots': []}
        sl = {'x0': bx0, 'x1': max(bx1, bx0 + 1.0), 'nr': 0, 'hm': 0.0, 'step': 0.0, 'top': Tb, 'bot': Bb}
        p, _ = col_puts(t, xc, m2, sl, pi=pi)
        puts += p
        if os.environ.get('VERT_LOOSE_DEBUG'):
            print('    [兜底行] %-14s nc=%2d 带x%.1f-%.1f hm%.1f -> F%.1f xc%.1f 列y%.1f-%.1f 步进%.2f %s' % (
                t[:14], nc, bx0, bx1, st['hm'], F, xc, Tb, Bb, step, '' if si else '(残余列)'))
    if not quiet:
        print('  [框内兜底] p%d %d 行 -> %d 列带配对 (内框高 %.1f)' % (pi + 1, len(rows), npair, avail))
    return puts, npair

def note_puts_frame(k, pi, m, nrows, orows):
    """框驱动路径的注/页外行渲染: 注行(版心内小字)区带 = 注槽 x 带(源图实测) + 注行 y 带;
    页外行(书耳/篇名, x 中心在内框外)区带 = 自身 x 带。两者都用旧 note_cols 的墨迹子列聚类
    (OCR x 对小字偏移可达 40pt, 只能用墨迹定位), 行按 x 降序与子列配对。返回 tex 列表。"""
    out = []
    if nrows:
        if m['note']:                                        # 注槽 x 带(源图实测)
            zx0 = (min(s['x0'] for s in m['note']) - 3.0) * 2
            zx1 = (max(s['x1'] for s in m['note']) + 3.0) * 2
            zy0 = (min(s['top'] for s in m['note'] if s['top']) - 3.0) * 2
            zy1 = (max(s['bot'] for s in m['note'] if s['bot']) + 3.0) * 2
        else:
            # 本页没有小字注槽(整页同字号), 但 page_rows 的步进间隙判据仍可能拆出「注行」(本书 1 页触发:
            #   改口径后 key 变化) —— 此时区带退回这些行自身的 x 带(与页外行同法), 不再 IndexError
            zx0 = (min(r[0] for r in nrows) - 6.0)
            zx1 = (max(r[1] for r in nrows) + 6.0)
            zy0 = (min(r[2] for r in nrows) - 6.0)
            zy1 = (max(r[3] for r in nrows) + 6.0)
        out += note_tex(k, pi, rows=nrows, zone=(zx0, zx1), zone_y=(zy0, zy1), tag='边注')
    if orows:
        # 页外行(书耳/篇名)只在内框外缘之外找墨迹渲染 —— OCR 对这类行的 x 会误置(实测 p162
        #   「方面的問題」OCR x 带 525-546pt 落在版心内(内框右缘 557.5), 旧实现按 OCR x 找墨迹
        #   找到的是正文首列, 5 个字压在该列上 = 唯一一处「小字与正文列相交」)。夹到内框外后
        #   区内无墨迹 -> 不渲染(该行实为 OCR 误置的正文残片)。
        c2 = (m['g']['in_l'] + m['g']['in_r'])          # px: 内框左+右(2x)
        rgt = [r for r in orows if (r[0] + r[1]) > c2]
        lft = [r for r in orows if (r[0] + r[1]) <= c2]
        if rgt:
            z0 = max(min(r[0] for r in rgt) - 12.0, m['g']['in_r'] * 2.0 + 4.0)
            z1 = max(r[1] for r in rgt) + 12.0
            if z1 > z0: out += note_tex(k, pi, rows=rgt, zone=(z0, z1), tag='页外')
            else: print('  [页外跳过] p%d %s (OCR x 落在版心内, 无版框外墨迹)' % (
                pi + 1, rgt[0][4][:16]))
        if lft:
            z0 = min(r[0] for r in lft) - 12.0
            z1 = min(max(r[1] for r in lft) + 12.0, m['g']['in_l'] * 2.0 - 4.0)
            if z1 > z0: out += note_tex(k, pi, rows=lft, zone=(z0, z1), tag='页外')
            else: print('  [页外跳过] p%d %s (OCR x 落在版心内, 无版框外墨迹)' % (
                pi + 1, lft[0][4][:16]))
    return out

# ---------- 1.995) 西文行侧排 / 标题署名行 / 影印页整页贴图(taskR / taskR2) ----------
# taskR2 增量(源页 29 逐项复核后修 2 项 + 复核 2 项):
#   · §1.995a 西文行改**拉丁 TFM 字体**(ptmr8t, 见下方 LAT_TFM 一节)—— 改前 tate 模式把 ASCII 映射成
#     CJK 字体的全角字形(文本层 U+FF37/字形 0.745x0.46em 又宽又扁), 源书是半角比例拉丁(0.68x0.66)。
#   · §1.995a 破折号单独成片: 字号由该 run **实测长**反算(源书两条破折号本身不等长 54.0/37.5pt),
#     沿/横位取该 run 墨心实测(探针标定字形长比/墨心偏移)。
#   · §1.995a 单位口径: 源图量出来的是 bp, TeX 坐标/字号是 TeX pt(1bp = 1.00375pt) -> 源坐标 x PT2BP
#     (改前 1:1 塞, 744pt 长的行沿行缩 0.37% = 行尾差 2.8-5pt); 基线也**逐片实测**(源书该行自身
#     不共线: 两条破折号墨心差 3.3pt、逐字横差随 y 从 +3.7 漂到 0.0)。
#   · §1.995b 标题/署名行复核: 用户报「侯健字号偏小 3.45x vs 4.7x / 金瓶梅論位置微偏」—— 实测
#     **源图墨迹**(不用 OCR poly: 该 poly 对 侯健 高估 24%): 侯健 源墨高 76.5/77.2pt vs 产物 78.5
#     (已对, 偏差 +1.7%), 金瓶梅論 列位/字高逐字相符(见 docs/vert_wz7_layout3_report.md §2)。
#     残留 = 竖直落位 +2.0pt(标题)/ +8.3pt(侯健), 根因是 col_puts 的 INK_ASC 是**全库字中位**
#     (0.954em) 而竖排逐字墨顶比例自变(实测 金 0.918 / 侯 0.862), 修法见报告遗留 1。
# 背景(用户拿 wz7 源页 29「金瓶梅論」侯健 著 那页与源书逐项对照, 报 3 类问题):
#   ① 西文整行被当竖排列**逐字竖拆**(每个字母占一格, 破折号竖成一竖线) —— 源书是**整行侧排**
#      (把页面逆时针转 90° 才能正读: 行首在页顶、自上而下读、字头朝页右)。
#      实测(tmp_vert/taskR/m2.py + en_cw/ccw.png 两向对照): 源页 29 该行墨迹带 x 665.2-690.0,
#      y 381.8-1125.0; 把源图**逆时针**转 90° 时该行正读("—We receive but what we give.—Coleridge"),
#      顺时针转 90° 得到镜像倒序 —— 故字形是**顺时针旋转 90°**(等价说法: 页面逆时针转可正读)。
#   ② 标题/署名行(源书字号显著大于正文)**被 clamp 回正文尺寸**: wz7 p29 源书「金瓶梅論」单字墨高
#      44.2pt(正文 22.5pt, 1.96 倍)、「侯健」78.0pt(3.47 倍); 现管线走 §1.99 框内兜底, 其字号上限被
#      压到 1.35 x 本页字号中位(实测日志「残余列 x713.5-724.5 字高33.5 -> 字号38.7」, 真值 50/88)。
#   ③ p5-28 是源书里的**影印页**(翻印旧版, 排版与本书现代排印完全不同), OCR 读不出内容(全书正文页
#      OCR 字数中位 613, 这 24 页只有 0-123), 用户明确要求「整页贴源图, 不重建」。
#
# 判据全部**数据驱动**(不写死页号; 用户给的页号只用于验证判据):
#   · 西文行(§1.995a): 拉丁字母数 >= VERT_LAT_MIN_CH(4) 且 CJK 字数 <= VERT_LAT_MAX_CJK(1)
#     且 拉丁占比 >= VERT_LAT_MIN_RATIO(0.7)。实测 wz7 全书 4029 条 OCR 行: 3990 条拉丁占比 0.0,
#     占比 >= 0.3 的 39 条里**只有 1 条是纯西文行**(源页 29 占比 0.91); 其余 38 条是「中文里夹西文词」
#     (占比 0.30-0.72, 如「Literary Terms: a Dictionary 則有更清楚的說明：」) —— 这类行是**汉字列**,
#     整行旋转会错(源书对夹在汉字列里的西文词也旋转, 但那属「词级侧排」, 不在本任务范围, 见报告遗留)。
#   · 标题/署名行(§1.995b): 该行**源图墨迹实测**字高 / 本页正文行字高中位 >= VERT_DISP_RATIO(1.4)。
#     正文行字高中位取本页「长行(>= 8 字)」逐行实测的中位(不用 m['font']: 伪槽格页的 m['font'] 会被
#     大字号槽带偏, 实测源页 29 m['font']=51.4 而真正文 25.6)。
#   · 影印页(§1.995c): 「每 OCR 字对应的源图墨迹面积」= 墨迹像素 / (OCR 非空白字数+1) 超全书正文页
#     中位 VERT_FAX_IPC_MULT(2.5) 倍 **且** OCR 字数 < VERT_FAX_CHAR_MULT(0.5) 倍全书正文页中位。
#     实测 wz7(0.75x 灰度 Otsu 口径, 正文页中位 110px/字, 正文页 = OCR 字数 >= 100 的 227 页):
#     **命中 70 页**(p1-4 封面/空白+插图, p5-28 影印页, 其余 42 页为插图/空白/图版), 命中页面积比
#     中位 748.7(范围 8.1-2916.3), 未命中页中位 1.00(最大 2.13 @p295) —— 判据线 2.5 两侧余量
#     3.8 倍; 命中页最大字数 123(p24) vs 字数判据线 308.5 -> 未误伤正文(普查脚本
#     tmp_vert/taskR2/fax_stats.py, 与管线落盘 fax_pages.json 逐页一致)。第二个条件(OCR 字数)是
#     **独立**的第二道闸: 只有「读不出内容」的页才贴图, 免得把「OCR 恰好漏字的正文页」也换成图片。
LAT_SP_ON = os.environ.get('VERT_LAT', '1') not in ('0', 'false', 'False')
LAT_MIN_CH = int(os.environ.get('VERT_LAT_MIN_CH') or 4)
LAT_MIN_RATIO = float(os.environ.get('VERT_LAT_MIN_RATIO') or 0.7)
LAT_MAX_CJK = int(os.environ.get('VERT_LAT_MAX_CJK') or 1)
DISP_RATIO = float(os.environ.get('VERT_DISP_RATIO') or 1.4)
FAX_ON = os.environ.get('VERT_FAX', '1') not in ('0', 'false', 'False')
FAX_IPC_MULT = float(os.environ.get('VERT_FAX_IPC_MULT') or 2.5)
FAX_CHAR_MULT = float(os.environ.get('VERT_FAX_CHAR_MULT') or 0.5)
FAX_DPI = int(os.environ.get('VERT_FAX_DPI') or 150)
FAX_SC = float(os.environ.get('VERT_FAX_SC') or 0.75)   # 判据扫描用的渲染倍率(相对 72dpi)

def _is_cjk_ch(c):
    o = ord(c)
    return (0x3400 <= o <= 0x4DBF) or (0x4E00 <= o <= 0x9FFF) or (0xF900 <= o <= 0xFAFF)

def _nonspace(t):
    return ''.join(c for c in t if not c.isspace())

def latin_row(t):
    """该 OCR 行是否「纯西文行」-> (bool, 拉丁数, CJK 数, 拉丁占比)。判据见 §1.995 注释。"""
    s = _nonspace(t)
    if not s:
        return False, 0, 0, 0.0
    nl = sum(1 for c in s if ('a' <= c <= 'z') or ('A' <= c <= 'Z'))
    nc = sum(1 for c in s if _is_cjk_ch(c))
    r = nl / float(len(s))
    return (nl >= LAT_MIN_CH and nc <= LAT_MAX_CJK and r >= LAT_MIN_RATIO), nl, nc, r

# --- 源图墨迹带定位(只定邻域, 列位/跨度量实测) ---
def _ink_band_at(ink, cx_pt, y0_pt, y1_pt, pitch, gmax=1.6, gap_frac=0.25):
    """源图墨迹里「含 x=cx_pt 的列带」+ 带内**真实墨迹 bbox** -> (x0,x1,y0,y1) pt 或 None。
    OCR 坐标对 NF 页有系统性缩放/漂移(本书 1.07-1.20 倍), 故只拿 OCR x 定邻域, 列位与跨度全取实测。
    带的边界用「空隙」判据而非「覆盖率」: 从 cx 向两侧走, 连续空白 > gap_frac x 列距即停 ——
    覆盖率判据会漏掉**又细又短的墨迹列**(实测 p29 英文行的 'b' 升部只占一列 2pt 宽, cov>0.02 判据
    把它切掉, 行带量成 26.0pt, 而真值 30.8pt —— 字号因此偏小 16%)。返回的是带内墨迹的实际 bbox。"""
    import numpy as np
    H, W = ink.shape
    xa = int(max(0.0, (cx_pt - gmax * pitch)) * 2); xb = int(min(W / 2.0, cx_pt + gmax * pitch) * 2)
    ya = int(max(0.0, y0_pt - 10.0) * 2); yb = int(min(H / 2.0, y1_pt + 10.0) * 2)
    if xb - xa < 8 or yb - ya < 8:
        return None
    sub = ink[ya:yb, xa:xb]
    on = sub.any(axis=0)
    if not on.any():
        return None
    gap = max(6, int(gap_frac * pitch * 2))
    ci = int(min(max(cx_pt * 2 - xa, 0), len(on) - 1))
    if not on[ci]:
        idx = np.where(on)[0]
        ci = int(idx[np.argmin(np.abs(idx - ci))])
    a = ci
    z = 0
    while a > 0:
        if on[a - 1]:
            a -= 1; z = 0
        else:
            z += 1
            if z > gap:
                break
            a -= 1
    b = ci
    z = 0
    while b + 1 < len(on):
        if on[b + 1]:
            b += 1; z = 0
        else:
            z += 1
            if z > gap:
                break
            b += 1
    band = sub[:, a:b + 1]
    cols = np.where(band.any(axis=0))[0]
    rows_ = np.where(band.any(axis=1))[0]
    if not cols.size or not rows_.size:
        return None
    return ((xa + a + int(cols.min())) / 2.0, (xa + a + int(cols.max()) + 1) / 2.0,
            (ya + int(rows_.min())) / 2.0, (ya + int(rows_.max()) + 1) / 2.0)

def _band_runs(ink, x0, x1, y0, y1, min_h=2.0):
    """带内 y 向墨迹 run -> [(top,bot)] pt(用于取字高/字距中位)"""
    ya, yb = int(y0 * 2), int(y1 * 2)
    xa, xb = int(x0 * 2), int(x1 * 2)
    if yb <= ya or xb <= xa:
        return []
    m = ink[ya:yb, xa:xb].any(axis=1)
    out = []
    for a, b in _runs(m, 1):
        if (b - a) < 2 * min_h:
            continue
        out.append(((ya + a) / 2.0, (ya + b + 1) / 2.0))
    return out

def _band_runs4(ink, x0, x1, y0, y1, min_h=2.0):
    """同 _band_runs, 但每个 run 连**横向跨度**一起给 -> [(top, bot, x0, x1)] pt。
    破折号要用: 它的横位逐条不同(实测 p29 两条的墨心在行带内分别落在 0.37 / 0.48 带位),
    只能逐 run 实测; 竖排正文的 run 只要 top/bot, 故另立函数(不动 _band_runs 的返回形状 ——
    col_puts/fit_gaps 都按 (top,bot) 二元组解包)。"""
    import numpy as np
    ya, yb = int(y0 * 2), int(y1 * 2)
    xa, xb = int(x0 * 2), int(x1 * 2)
    if yb <= ya or xb <= xa:
        return []
    sub = ink[ya:yb, xa:xb]
    out = []
    for a, b in _runs(sub.any(axis=1), 1):
        if (b - a) < 2 * min_h:
            continue
        seg = sub[a:b + 1, :]
        cols = np.where(seg.any(axis=0))[0]
        out.append(((ya + a) / 2.0, (ya + b + 1) / 2.0,
                    (xa + int(cols.min())) / 2.0, (xa + int(cols.max()) + 1) / 2.0))
    return out

# --- 旋转落点常数(探针实测) ---
# q 0 -1 1 0 0 0 cm 这个 cm 会把 \\put 的坐标**整体重写**: 出图位置只由 (e,f) 与 put 决定, 且
#   ink 左上角(页坐标 pt, 页左上原点) = (put_y + e + KX, put_x - f + KY) —— KX/KY 与纸型有关
#   (实测: 921.8x1443pt 纸 KX=-1297.0; 705x1083.8pt 纸 KX=-939.0), 故**建排前探针实测一次**。
#   探针 = 用本管线真 preamble 编译一页, 单个旋转 40pt 'H'(平直笔画, 左右无侧边空隙), 量墨迹左上角。
# taskR2 扩: 同页再放一个 40pt 破折号(put 沿**横**向偏 150pt, 与 H 的墨迹互不干扰), 量它的
#   ① 沿行墨长 / 字号(em) ② 墨心相对 pen 的沿行偏移(em) ③ 墨心相对 pen 的横向偏移(em) ——
#   破折号必须**按源图该 run 实测长**定字号(源书两条破折号本身不等长: 54.0 / 37.5pt), 且它在
#   行带内的横位逐条不同, 只能逐条实测落位。
_ROT_K = {'KX': None, 'KY': None, 'base_h': None,
          'dash_len': None, 'dash_ca': None, 'dash_cc': None}
def _rot_anchor(preamble, tmp, page_w_pt, page_h_pt, verbose=True):
    """探针标定 (KX, KY) + 破折号几何常数。已在缓存里则直接返回。返回 (KX, KY) 或 None(探针失败)。
    探针落点未知(这正是要标定的量), 故取 (e,f) 的三个候选值各出一页 —— 三者中必有一页把字
    落在纸内(候选按「KX ≈ -页高 + 146」的初估排布, 该初估在 4 种纸型上实测偏差 <= 1.2pt)。"""
    if _ROT_K['KX'] is not None and _ROT_K['base_h'] == round(page_h_pt, 2):
        return _ROT_K['KX'], _ROT_K['KY']
    import numpy as np
    import fitz
    px, py = 0.0, 0.0                           # put 位置(不影响旋转后的落点, 取 0 免混淆)
    tx, ty = 0.28 * page_w_pt, 0.45 * page_h_pt  # 期望落点(页内安全区)
    e0 = round(page_h_pt - 146.0 + tx - py, 1)
    f0 = round(px - ty, 1)
    PS = 40.0                                   # 探针字号(TeX pt)
    py2 = py + 150.0                            # 破折号 put: 沿横向偏开(put 第二坐标 = 页 x)
    pages = []
    for de in (0.0, 130.0, 260.0):
        pages.append('\\AddToShipoutPictureFG*{\n  \\put(%g,%g)'
                     '{\\special{pdf:literal direct q 0 -1 1 0 %g %g cm}'
                     '\\fontsize{40pt}{40pt}\\selectfont H\\special{pdf:literal direct Q}}%%\n}\n\\null\n'
                     '\\AddToShipoutPictureFG*{\n  \\put(%g,%g)'
                     '{\\special{pdf:literal direct q 0 -1 1 0 %g %g cm}'
                     '\\fontsize{40pt}{40pt}\\selectfont —\\special{pdf:literal direct Q}}%%\n}\n\\null\n'
                     % (px, py, e0 + de, f0, px, py2, e0 + de, f0))
    pdir = os.path.join(tmp, 'rot_probe')
    os.makedirs(pdir, exist_ok=True)
    tex = preamble + '\n\\newpage\n'.join(pages) + '\\end{document}\n'
    open(os.path.join(pdir, 'rotprobe.tex'), 'w', encoding='utf8').write(tex)
    r = subprocess.run(['uplatex', '-interaction=nonstopmode', 'rotprobe.tex'],
                       cwd=pdir, capture_output=True, text=True)
    r2 = subprocess.run(['dvipdfmx', 'rotprobe.dvi'], cwd=pdir, capture_output=True, text=True)
    pp = os.path.join(pdir, 'rotprobe.pdf')
    if r2.returncode != 0 or not os.path.exists(pp):
        print('  [西文侧排] 旋转探针编译失败(uplatex rc=%s dvipdfmx rc=%s) -> 西文行不渲染'
              % (r.returncode, r2.returncode))
        return None
    d = fitz.open(pp)
    S = 2.0
    def _bbox(sub):
        ys = np.where(sub.any(axis=1))[0]; xs = np.where(sub.any(axis=0))[0]
        return (xs.min() / S, (xs.max() + 1) / S, ys.min() / S, (ys.max() + 1) / S)
    for i, de in enumerate((0.0, 130.0, 260.0)):
        pix = d[i].get_pixmap(matrix=fitz.Matrix(S, S), colorspace=fitz.csGRAY)
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
        ink = a < 150
        if not ink.any():
            continue
        ys = np.where(ink.any(axis=1))[0]; xs = np.where(ink.any(axis=0))[0]
        x0, y0 = xs.min() / S, ys.min() / S
        kx, ky = round(x0 - py - (e0 + de), 2), round(y0 - px + f0, 2)
        if verbose:
            print('  [西文侧排] 旋转探针: 墨迹左上(%.2f,%.2f) @ put(%.0f,%.0f) e=%.1f f=%.1f -> KX %.2f KY %.2f'
                  % (x0, y0, px, py, e0 + de, f0, kx, ky))
        # 破折号: 只在其 put(横向偏 py2) 的落点附近量(与 H 的墨迹隔开 150pt)
        em = PS * PT2BP
        pen_x0 = py2 + (e0 + de) + kx               # 破折号 put 对应的 pen 坐标(与正文同一映射)
        pen_y0 = px - f0 + ky
        w0 = max(0, int((pen_x0 - 60) * S)); w1 = int((pen_x0 + 60) * S)
        bb = _bbox(ink[:, w0:w1])
        if bb[1] > bb[0]:
            dx0, dx1 = bb[0] + w0 / S, bb[1] + w0 / S
            dy0, dy1 = bb[2], bb[3]
            _ROT_K['dash_len'] = round((dy1 - dy0) / em, 4)
            _ROT_K['dash_ca'] = round(((dy0 + dy1) / 2.0 - pen_y0) / em, 4)
            _ROT_K['dash_cc'] = round(((dx0 + dx1) / 2.0 - pen_x0) / em, 4)
            if verbose:
                print('  [西文侧排] 破折号探针: 墨长 %.1fpt(%.3f em) 沿心 %.1f 横心 %.1f -> 长比 %.3f '
                      '沿偏 %.3f em 横偏 %.3f em'
                      % (dy1 - dy0, (dy1 - dy0) / em, (dy0 + dy1) / 2.0, (dx0 + dx1) / 2.0,
                         _ROT_K['dash_len'], _ROT_K['dash_ca'], _ROT_K['dash_cc']))
        d.close()
        _ROT_K['KX'], _ROT_K['KY'], _ROT_K['base_h'] = kx, ky, round(page_h_pt, 2)
        return kx, ky
    d.close()
    print('  [西文侧排] 旋转探针三页均出纸(纸 %.0fx%.0f 与初估不符) -> 西文行不渲染'
          % (page_w_pt, page_h_pt))
    return None

def _latin_metrics(text, font_path):
    """串的字体几何(em 口径, fontTools 轮廓): {adv 前进总量, x0/x1 墨迹前后缘(相对字首原点), ymin/ymax 墨迹上下缘(相对基线)}。
    口径与渲染一致: 逐字按 hmtx advance 前进(与本管线探针实测 2.3% 内一致), 墨迹取轮廓 bbox 并集。"""
    from fontTools.ttLib import TTFont, TTCollection
    from fontTools.pens.boundsPen import BoundsPen
    if font_path.lower().endswith('.ttc'):
        col = TTCollection(font_path)
        idx = 0
        for i, f in enumerate(col.fonts):
            if 'TC' in (f['name'].getDebugName(4) or ''):
                idx = i
        font = col.fonts[idx]
    else:
        font = TTFont(font_path)
    upem = float(font['head'].unitsPerEm)
    gs = font.getGlyphSet(); cmap = font.getBestCmap()
    x = 0.0
    ymin, ymax, x0, x1 = 1e9, -1e9, 1e9, -1e9
    for ch in text:
        gn = cmap.get(ord(ch))
        if gn is None:
            continue
        bp = BoundsPen(gs); gs[gn].draw(bp)
        if bp.bounds:
            b = [v / upem for v in bp.bounds]
            ymin = min(ymin, b[1]); ymax = max(ymax, b[3])
            x0 = min(x0, x + b[0]); x1 = max(x1, x + b[2])
        x += font['hmtx'][gn][0] / upem
    if ymax < ymin or x1 < x0:
        return None
    return {'adv': x, 'x0': x0, 'x1': x1, 'ymin': ymin, 'ymax': ymax}

def _latin_groups(runs, F_hint):
    """源行墨迹 run 序列 -> 「词组」(按大空隙切) [(y0,y1)] 沿行页坐标。
    判据: 相邻 run 的空隙 >= 0.5 x 字号 即断词 —— 实测 wz7 p29 该行**词间**空隙 26-28pt、
    词内字母间 0.8-4.5pt(字号 28.5), 两类相差 6 倍以上, 阈值取中间不会混。"""
    if not runs:
        return []
    thr = 0.5 * F_hint
    out = []; cur = [runs[0]]
    for a, b in runs[1:]:
        if a - cur[-1][1] >= thr:
            out.append((cur[0][0], cur[-1][1])); cur = []
        cur.append((a, b))
    out.append((cur[0][0], cur[-1][1]))
    return out

def _align_words_groups(words, groups, F):
    """词(按空白切) ↔ 源图词组 单调配对 -> [(词下标, 词组下标)]。
    代价 = |本字体词宽 - 源词组宽| / 源词组宽(fontTools 前进量, 与渲染同字体); 跳过罚 0.45 ——
    只在两边条数不等(OCR 丢/并词)时靠 DP 找最合理的错位, 与 _align_rows_slots 同一路数。"""
    W, G = len(words), len(groups)
    if not W or not G:
        return []
    if W == G:
        return [(i, i) for i in range(W)]
    def w_nat(t):
        m = _lat_metrics(t) if LAT_FONT_ON else _latin_metrics(t, _FONT_PATH)
        return ((m['x1'] - m['x0']) if m else 0.5 * len(t)) * F
    INF = 1e9
    dp = [[INF] * (G + 1) for _ in range(W + 1)]
    bt = [[None] * (G + 1) for _ in range(W + 1)]
    dp[0][0] = 0.0
    for i in range(W + 1):
        for j in range(G + 1):
            if dp[i][j] >= INF:
                continue
            if i < W and j < G:
                gw = max(1.0, groups[j][1] - groups[j][0])
                c = dp[i][j] + abs(w_nat(words[i]) - gw) / gw
                if c < dp[i + 1][j + 1]:
                    dp[i + 1][j + 1] = c; bt[i + 1][j + 1] = (i, j, 1)
            if i < W and dp[i][j] + 0.45 < dp[i + 1][j]:
                dp[i + 1][j] = dp[i][j] + 0.45; bt[i + 1][j] = (i, j, 0)
            if j < G and dp[i][j] + 0.45 < dp[i][j + 1]:
                dp[i][j + 1] = dp[i][j] + 0.45; bt[i][j + 1] = (i, j, 0)
    out = []
    i, j = W, G
    while i > 0 or j > 0:
        p = bt[i][j]
        if p is None:
            break
        pi_, pj_, took = p
        if took:
            out.append((pi_, pj_))
        i, j = pi_, pj_
    out.reverse()
    return out

# --- 西文行的字体(taskR2): 拉丁 TFM(Type1) vs CJK 字体的 tate ASCII ---
# 背景(taskR2 复核实测): tate 模式下 CJK 字体的 ASCII 走 JT2 编码 -> **全角**字形 —— 文本层是
#   U+FF37 等全角码位, 字形 0.745em 宽 x 0.46em 高(又宽又扁); 源书是半角比例拉丁(0.68 x 0.66)。
#   改用 TeX 的 TFM 拉丁字体(默认 ptmr8t = Times/Nimbus Roman, 与源书铅字拉丁同族): ASCII 走
#   TFM 度量 = 半角比例宽度, 文本层码位是 ASCII; 非 ASCII(破折号等)无 TFM 字形 -> 自动回落 CJK。
LAT_TFM = os.environ.get('VERT_LATFONT') or 'ptmr8t'              # 渲染用的 TeX 字体名
LAT_PFB = os.environ.get('VERT_LATFONT_PFB') or 'utmr8a.pfb'      # 对应的 Type1 字形文件(度量用)
LAT_FONT_ON = os.environ.get('VERT_LAT_FONT', '1') not in ('0', 'false', 'False')
LAT_DASH = '—―–'                       # 破折号类(源书为长横线; CJK 字形的竖排形态 = 竖线, 与源书同)
_LAT = {'gs': None, 'err': False}
_LAT_ENC = None

def _lat_gs():
    """拉丁 TFM 对应的 Type1 字形集(kpsewhich 解析, 与 dvipdfmx 同一查找链)。失败 -> None(记一次日志)。"""
    if _LAT['gs'] is not None or _LAT['err']:
        return _LAT['gs']
    p = _calib_font_path(LAT_PFB)
    if not p:
        _LAT['err'] = True
        print('  [西文侧排] 拉丁字形文件 %s 找不到(kpsewhich) -> 西文行不渲染' % LAT_PFB)
        return None
    from fontTools.t1Lib import T1Font
    _LAT['gs'] = T1Font(p).getGlyphSet()
    return _LAT['gs']

def _lat_enc():
    """ASCII -> 字形名(AdobeStandard; 0x20-0x7E 与 TeX T1(8t) 一致, 仅三处引号按 T1 修正 ——
    渲染走 8t 编码, 名字取错会量到别的字形)。"""
    global _LAT_ENC
    if _LAT_ENC is None:
        from fontTools.encodings.StandardEncoding import StandardEncoding as SE
        d = {}
        for c in range(0x20, 0x7F):
            n = SE[c]
            if n and n != '.notdef':
                d[c] = n
        d[ord("'")] = 'quoteright'; d[ord('`')] = 'quoteleft'
        _LAT_ENC = d
    return _LAT_ENC

_T1W = {}
def _tfm_widths():
    """TFM 逐字前进量 {T1 槽位: em} —— TeX 排版**真正**用的宽度(与轮廓 hmtx 略有出入)。
    TFM 结构(全部大端; "字" = 4 字节): 前 12 个 2 字节字段(lf,lh,bc,ec,nw,nh,nd,ni,nl,nk,ne,np)
    = 24 字节, 其中 lh 含前 6 字 -> header 共 lh 字; 接着 char_info(bc..ec 各 4 字节: 首字节 =
    width 表下标), 再 width 表 nw x4 字节(fix_word: 值/2^20 = 占 design size 的比例 = em 数)。
    ASCII 在 T1(8t) 里槽位 = 码位(0x20-0x7E 与 AdobeStandard 同), 故直接按 ord(c) 查。"""
    if _T1W:
        return _T1W
    p = _calib_font_path(LAT_TFM + '.tfm')
    if not p:
        return _T1W
    import struct
    d = open(p, 'rb').read()
    lf, lh, bc, ec, nw, nh, nd, ni, nl, nk, ne, npar = struct.unpack('>12H', d[:24])
    ci0 = 24 + 4 * lh                             # 前 12 个 2 字节字段(24B) + lh 个 4 字节字
    wt0 = ci0 + 4 * (ec - bc + 1)
    if nw and len(d) >= wt0 + 4 * nw:
        wtab = struct.unpack('>%dI' % nw, d[wt0:wt0 + 4 * nw])
        for c in range(bc, min(ec, 255) + 1):
            wi = struct.unpack('>I', d[ci0 + 4 * (c - bc):ci0 + 4 * (c - bc) + 4])[0] >> 24
            if wi < nw:
                _T1W[c] = wtab[wi] / float(1 << 20)
    if not _T1W:
        print('  [西文侧排] TFM 宽度表解析失败(%s) -> 词宽按字形近似' % LAT_TFM)
    return _T1W

def _lat_metrics(text):
    """拉丁字体 em 口径度量 {adv, x0, x1, ymin, ymax}(与 _latin_metrics 同形同口径):
    逐字按 **TFM 前进量**推进(渲染同一份数据), 墨迹取 Type1 轮廓 bbox 并集(单位 1000 em)。
    缺字形的字符(非 ASCII: 破折号等)按 0.8 em 估 —— 它们由调用方拆成单独一片走 CJK 字体。"""
    gs = _lat_gs()
    if gs is None:
        return None
    from fontTools.pens.boundsPen import BoundsPen
    enc = _lat_enc(); wt = _tfm_widths()
    x = 0.0
    ymin, ymax, x0, x1 = 1e9, -1e9, 1e9, -1e9
    for ch in text:
        gn = enc.get(ord(ch))
        if gn is None or gn not in gs:
            x0 = min(x0, x + 0.10); x1 = max(x1, x + 0.70)
            x += 0.80
            continue
        g = gs[gn]; bp = BoundsPen(gs); g.draw(bp)
        if bp.bounds:
            b = [v / 1000.0 for v in bp.bounds]
            ymin = min(ymin, b[1]); ymax = max(ymax, b[3])
            x0 = min(x0, x + b[0]); x1 = max(x1, x + b[2])
        w = wt.get(ord(ch))
        x += w if w is not None else 0.5
    if ymax < ymin or x1 < x0:
        return None
    return {'adv': x, 'x0': x0, 'x1': x1, 'ymin': ymin, 'ymax': ymax}

def _latin_put(text, F, pen_x, pen_y, track=0.0, latin=True):
    """一行(或一个词/一片)西文侧排 -> 单个 \\put 片段。F/pen 单位 = pt(页左上原点; 由调用方换算)。
    track = 片内逐字追加的字距(pt): 本字体词宽比源书窄(源书是铅字拉丁文, 字形更宽),
      逐片把字距补到源书该片的墨迹宽度 —— 片首锚点不动, 片尾也对齐源书。
    latin=True: 用 TeX 拉丁字体(半角比例宽度 + ASCII 文本层); False: 用 CJK 字体(破折号竖排形态)。
    旋转用**精确整数矩阵** 0/-1/1(无任何数值逆/舍入), 图形状态用 q...Q 精确还原(与 §1.0a 同源,
    累积残差 0 —— 不用 graphicx 的 \\scalebox/\\rotatebox: 其 btrans/etrans 走数值逆矩阵, 见 §1.0a)。
    文本按原样输出(空格保留); 字号用 \\fontsize{F}{F} 单倍行距。"""
    if abs(track) > 0.05 and len(text) > 1:
        text = ('\\kern%.2fpt' % track).join(text)
    if latin:
        sel = ('\\font\\vlat=%s at %spt \\fontsize{%spt}{%spt}\\selectfont\\vlat '
               % (LAT_TFM, round(F, 2), round(F, 1), round(F, 1)))
    else:
        sel = '\\fontsize{%spt}{%spt}\\selectfont ' % (round(F, 1), round(F, 1))
    body = ('\\special{pdf:literal direct q 0 -1 1 0 0 0 cm}' + sel + _esc_ch(text)
            + '\\special{pdf:literal direct Q}')
    return '\\put(%.2f,%.2f){%s}' % (pen_y - _ROT_K['KY'], pen_x - _ROT_K['KX'], body)

def _lat_pieces(word):
    """词 -> [('t'|'d', 文本)]: 破折号单独成片(要按源图该 run 实测长定字号、逐条定横位)。"""
    out, cur = [], ''
    for ch in word:
        if ch in LAT_DASH:
            if cur:
                out.append(('t', cur)); cur = ''
            out.append(('d', ch))
        else:
            cur += ch
    if cur:
        out.append(('t', cur))
    return out

def _assign_runs(runs4, widths):
    """源图 run 序列 -> [(i0, i1)]: 按各片自然宽(pt) 单调切分 run 序列的 DP(与 _align_words_groups 同路数)。
    代价 = |该片对应的 run 段墨迹跨度 - 片自然宽| / 片自然宽。用途: 词里有破折号时, 把它在源图 run
    序列里对应的那一段切出来(它的长度与横位都是逐条实测的, 不能靠均值)。"""
    n, k = len(runs4), len(widths)
    if k <= 1 or n <= 1:
        return [(0, max(0, n - 1))]
    INF = 1e9
    sp = [[0.0] * (n + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(i + 1, n + 1):
            sp[i][j] = runs4[j - 1][1] - runs4[i][0]
    dp = [[INF] * (k + 1) for _ in range(n + 1)]
    bt = [[None] * (k + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(n + 1):
        for g in range(k):
            if dp[i][g] >= INF:
                continue
            for j in range(i + 1, n - (k - g - 1) + 1):
                w = max(1.0, widths[g])
                c = dp[i][g] + abs(sp[i][j] - w) / w
                if c < dp[j][g + 1]:
                    dp[j][g + 1] = c; bt[j][g + 1] = (i, g)
    if dp[n][k] >= INF:
        return [(0, n - 1)]
    out, i, g = [], n, k
    while g > 0:
        p0, pg = bt[i][g]
        out.append((p0, i - 1)); i, g = p0, pg
    out.reverse()
    return out

def _latin_tex(k, pi, pen_w, ink_pt, ink, verbose=True):
    """纯西文行 -> 旋转 \\put 列表(逐**片**绝对定位)。几何全取源图墨迹实测:
      ① 字号: 源行墨迹横向(垂直于行)实测宽 / 本字体同串墨迹上下缘比(Type1 轮廓口径);
      ② 基线: 源行墨迹左缘 - 字体墨迹下缘 x 字号(整行共用一条基线);
      ③ 片位: 源行墨迹 run 按「大空隙 = 词间」切成词组, 逐词把**该词的墨迹起点**对齐到源书位置;
         词里有破折号 -> 按 run 序列切出破折号那一段, 破折号单独一片: **字号由该 run 实测长反算**,
         沿/横位取该 run 实测(两条破折号本身不等长: 实测 54.0 / 37.5pt)。
    为什么锚词/锚片而不是「整行等距拉伸」: 实测源书该行**词间空隙 26-28pt / 词内字母空隙 1.0-4.5pt**
    (比值 > 6), 整行等距拉伸会把词的节奏拉平(源书的词界感消失); 锚定后词界与源书逐词对得上。
    taskR2(复核实测): 拉丁走 TFM 字体(ptmr8t) -> 半角比例宽度 + ASCII 文本层(改前是全角 U+FF37)。"""
    if _ROT_K['KX'] is None:
        return []
    if LAT_FONT_ON and _lat_gs() is None:
        return []
    dash_ok = _ROT_K['dash_len'] is not None and _ROT_K['dash_ca'] is not None \
        and _ROT_K['dash_cc'] is not None
    if not dash_ok and any(c in LAT_DASH for c in pen_w):
        print('  [西文侧排] 破折号探针未取到(长比/偏移缺失) -> 破折号按行内字号整词渲染')
    # 整行字号: 只按**拉丁字母**的墨迹上下缘定(破折号另按自身 run 定字号, 不参与)
    lat_txt = ''.join(c for c in pen_w if c not in LAT_DASH)
    m = _lat_metrics(lat_txt) if LAT_FONT_ON else _latin_metrics(lat_txt, _FONT_PATH)
    if not m or m['ymax'] - m['ymin'] <= 0:
        return []
    x0, x1, y0, y1 = ink_pt
    # 单位口径(taskR2): 源图量出来的都是 **bp**(OCR px/2), 而 TeX 坐标/字号是 TeX pt(1bp = 1.00375pt)。
    #   渲染落点 = TeX 坐标 x 0.99627 -> 源坐标要 x PT2BP 才是等价的 TeX 坐标(改前整行按 1:1 塞,
    #   744pt 长的行会**沿行缩 0.37%** = 行尾差 2.8-5pt, 实测逐词递增大致的 -0.8 -> -3.5pt)。
    F = (x1 - x0) / (m['ymax'] - m['ymin']) * PT2BP         # bp 墨高 -> TeX 字号
    pen_x = x0 * PT2BP - m['ymin'] * F
    runs4 = _band_runs4(ink, ink_pt[0], ink_pt[1], ink_pt[2], ink_pt[3])
    runs = [(a, b) for a, b, _x0, _x1 in runs4]
    words = [w for w in re.split(r'[ 　\t]+', pen_w.strip()) if w]
    groups = _latin_groups(runs, F)
    pairs = _align_words_groups(words, groups, F)
    if not pairs:
        return []
    W = _lat_metrics if LAT_FONT_ON else (lambda t: _latin_metrics(t, _FONT_PATH))
    puts = []
    for wi, gj in pairs:
        word = words[wi]
        pieces = _lat_pieces(word) if dash_ok else [('t', word)]
        g0, g1 = groups[gj]
        gruns = [r for r in runs4 if r[0] >= g0 - 0.01 and r[1] <= g1 + 0.01]
        # 各片的自然宽(TeX pt): 破折号按 0.8 em 估(它单列成片, 不参与宽度对齐)
        pwd = []
        for kind, txt in pieces:
            mm = W(txt) if (kind == 't' and txt) else None
            pwd.append(((mm['x1'] - mm['x0']) * F) if mm else 0.8 * len(txt) * F)
        # 词内切分: 片数 > 1 时按自然宽在 run 序列上切(破折号片 = 它自己那一段 run)
        segs = _assign_runs(gruns, pwd) if len(pieces) > 1 else [(0, max(0, len(gruns) - 1))]
        if len(segs) != len(pieces):
            pieces, segs = [('t', word)], [(0, max(0, len(gruns) - 1))]
        for (kind, txt), (i0, i1) in zip(pieces, segs):
            if not gruns or i1 < i0:
                continue
            sub = gruns[i0:i1 + 1]
            s0, s1 = sub[0][0], sub[-1][1]
            if kind == 'd':
                # 破折号: 字号由该 run 实测长反算(字形长比 = 探针实测), 沿/横位 = 该 run 墨心实测
                Fd = (s1 - s0) / _ROT_K['dash_len'] * PT2BP
                cc = _ROT_K['dash_cc']; ca = _ROT_K['dash_ca']
                xc = (min(r[2] for r in sub) + max(r[3] for r in sub)) / 2.0
                puts.append(_latin_put(txt, Fd, xc * PT2BP - cc * Fd,
                                       (s0 + s1) / 2.0 * PT2BP - ca * Fd, 0.0, latin=False))
                if verbose:
                    print('  [西文侧排] p%d 破折号: 源 run %.1f-%.1f(长%.1f) 横心%.1f -> 字号%.1f'
                          % (pi + 1, s0, s1, s1 - s0, xc, Fd))
                continue
            mw = W(txt)
            if not mw:
                continue
            gy0 = s0 * PT2BP - mw['x0'] * F                    # 该片墨迹起点对齐源书(TeX pt 口径)
            # 基线也**逐片实测**(taskR2): 源书该行的横位不是一条直线 —— 实测两条破折号(同一字形)
            #   的墨心在行带内差 3.3pt(p29: 672.7 @y382 / 676.1 @y947), 逐字对的横差也随 y 从 +3.7
            #   漂到 0.0 —— 源书自身有 ~0.3 度的倾斜/逐词排版差。整行共用一条基线会把这个偏移留在
            #   每片身上(±4pt), 故每片按**该片实测墨迹下缘**定自己的基线。
            wx0 = min(r[2] for r in sub)
            pen_xw = wx0 * PT2BP - mw['ymin'] * F
            gw = (s1 - s0) * PT2BP                             # 源书该片墨迹宽
            nw = (mw['x1'] - mw['x0']) * F                     # 本字体该片自然墨迹宽
            # 片内字距: 只补「本字体字形比源书窄」这部分; 逐字字距夹在 +-0.25 em(护栏)。
            tr = 0.0
            if len(txt) > 1:
                tr = max(-0.25 * F, min(0.25 * F, (gw - nw) / (len(txt) - 1)))
            puts.append(_latin_put(txt, F, pen_xw, gy0, tr, latin=LAT_FONT_ON))
    if verbose:
        print('  [西文侧排] p%d 「%s」字号%.1f 基线 x%.1f 源墨迹 %.1fx%.1f(横x沿行) '
              '源墨迹 run %d -> 词组 %d / 文本词 %d -> 落位 %d'
              % (pi + 1, pen_w[:24], F, pen_x, x1 - x0, y1 - y0, len(runs), len(groups), len(words), len(puts)))
    return puts

# --- 特殊行专用渲染(标题/署名: 字号与位置全取源图实测) ---
def _display_put(t, F, xc, top, step, g, sl, pi):
    """标题/署名行: 走 col_puts 同一套逐字渲染(标点挤格/横向压缩同源), 但字号/列位/列顶/步进
    **用源图实测值**(不经 §1.99 的 1.35 x 页字号上限 —— 那条是给「粘连长 run 把字高测成整列高」
    设的兜底, 大字号行会连真值一起被压掉, 实测 wz7 p29 标题被压到 26-38pt 而真值 50/88pt)。"""
    m2 = {'font': F, 'step_cap': max(step, 0.1), 'band_t': top, 'band_b': sl['bot'],
          'block_b': sl['bot'], 'w': g['in_r'] - g['in_l'], 'note': [], 'body': [],
          'g': g, 'slots': []}
    p, _b = col_puts(t, xc, m2, sl, None, pi)
    return p

_FONT_PATH = None      # 由标定趟填(见 §1.956 之后的 _ffile)
_SPECIAL_BLOCK = {}    # k -> [(x0,x1)] 本页已被特殊行占用的 x 带(正常路径不再落位)
_SPECIAL_ROWS = {}     # k -> set(行对象 id) 本页被 §1.995 认领的具体行(taskCH 目录分支只剔这些行,
                       #      不按 x 带整段剔: 目录页可能有一行被误判成标题, 同带的其它回目行仍要渲染)
_SPECIAL_SIGS = {}     # k -> set((x0,x1,y0,y1,text)) 同上, 按**坐标签名**记录: 标定页的行被映射成
                       #      新 tuple, 目录分支拿到的是另一份同值 tuple, id 对不上(实测 p45 双画标题)
_SPECIAL_STAT = {'latin': 0, 'disp': 0, 'pages': {}}

def _band_blocked(x0, x1, blocks):
    """带 (x0,x1) 是否已被特殊行占用(重叠 > 50% 带宽即算占用)。"""
    for a, b in blocks:
        ov = min(x1, b) - max(x0, a)
        if ov > 0.5 * (x1 - x0):
            return True
    return False

def _page_specials(k, pi, g, ink, rows, verbose=True):
    """本页「特殊行」(纯西文行 / 标题署名行)检测 + 渲染 -> (puts, blocked_x, claimed)
    · g   = 本页伪版心/版框 dict(用 in_l/in_r/in_t/in_b 限行, pitch 定邻域窗)
    · ink = 本页墨迹(bool, 2x px); rows = 本页 OCR 行(源图坐标系 2x px, 与 ink 同单位)
    · blocked_x = 已占用 x 带(pt) —— 调用方把它交给正常渲染路径**剔除**(否则行↔槽/带配对会整体错位)
    · claimed   = 已认领的行对象 id 集(调用方从 all_rows 里摘掉)
    只有 NF 路径调用(有版框书/wz6 不走这里)。"""
    if not rows:
        return [], [], set()
    il, ir = g['in_l'] * 2.0, g['in_r'] * 2.0
    it, ib = g['in_t'] * 2.0, g['in_b'] * 2.0
    pitch = g.get('pitch') or (g['in_r'] - g['in_l']) / max(1, N_COL_FRAME)
    # 候选行: 行心在版心 x 带内(页外行/书眉走各自路径), 单块(非合并残片)。
    #   taskCE-c(默认关, VERT_NF_TITLE_OUT=1 开): 版心**不动**, 只把候选窗口向左右外扩
    #   NF_TITLE_OUT_PAD 个列距, 且仅限短行 —— 版心外的大字号短行(实测 p43 凡例 x749.9-804.4,
    #   版心右缘 742.9)由此进入下面「大字号 + 稀少性」两道既有判据; 命中后走标题署名路径
    #   (逐字 \\put 按源图墨迹定位, x 带进 _SPECIAL_BLOCK), 不新建槽、不改 _ink_bands 窗口。
    _outpad = (NF_TITLE_OUT_PAD * pitch * 2.0) if NF_TITLE_OUT else 0.0
    cand = [r for r in rows
            if len(r[4]) >= 1 and '\n' not in r[4]
            and (il - 6 <= (r[0] + r[1]) / 2.0 <= ir + 6
                 or (_outpad > 0 and len(r[4]) <= NF_TITLE_OUT_MAXLEN
                     and il - 6 - _outpad <= (r[0] + r[1]) / 2.0 <= ir + 6 + _outpad))]
    if not cand:
        return [], [], set()
    # ---- 逐行量墨迹带(只定邻域用 OCR x; 带宽/带顶/带底/字高全取源图实测) ----
    info = {}
    for r in cand:
        cx = (r[0] + r[1]) / 4.0                    # OCR 行心 px -> pt
        bd = _ink_band_at(ink, cx, r[2] / 2.0, r[3] / 2.0, pitch)
        if bd is None:
            continue
        runs = _band_runs(ink, bd[0], bd[1], bd[2], bd[3])
        hs = sorted(b - a for a, b in runs if b - a >= 3.0)
        info[id(r)] = {'bd': bd, 'runs': runs, 'hm': (hs[len(hs) // 2] if hs else 0.0)}
    # ---- 正文行字高基准: 长行(>= 8 字)逐行实测字高的中位 ----
    body_hs = sorted(info[id(r)]['hm'] for r in cand
                     if len(r[4]) >= 8 and id(r) in info and info[id(r)]['hm'] > 0)
    if not body_hs:
        return [], [], set()
    body_h = body_hs[len(body_hs) // 2]
    # ---- 分类 ----
    lat_rows, disp_rows = [], []
    for r in cand:
        if id(r) not in info:
            continue
        ok, nl, nc, ratio = latin_row(r[4])
        if LAT_SP_ON and ok:
            lat_rows.append(r); continue
        # 「字高」必须由**逐字 run** 支撑: 粘连长 run(相邻字墨相连/残余印刷线)会把整列连成一条 ->
        #   字高被量成整列高(实测 p157/p282/p294 的正文行被量出 88-757pt, 是正文 26pt 的 3-19 倍)。
        #   判据 = run 数与本行**排版格数**相称(>= 0.6x): 真大字号行(标题 4 字 4 run / 署名 2 字 2 run)
        #   天然满足, 粘连行(16 字 3-6 run)被挡下。run 高另夹 3x 本行 run 高中位(与 _band_stats 同口径)。
        if len(r[4]) >= 2:
            rr = info[id(r)]['runs']
            hh = sorted(b - a for a, b in rr)
            hmed0 = hh[len(hh) // 2] if hh else 0.0
            cap = max(40.0, 3.0 * hmed0)
            kept = [b - a for a, b in rr if 4.0 <= b - a <= cap]
            hm = sorted(kept)[len(kept) // 2] if kept else 0.0
            if (len(rr) >= 0.6 * n_cells(r[4]) and hm >= DISP_RATIO * body_h):
                disp_rows.append(r)
    # taskCH2: 目录页的**网格行不是标题/署名**。目录 p48 这类表格目录每个回占一个 x 带、
    #   三个 y 层(回次 / 回目上句 / 回目下句); 层行被 nf_toc_shape 判为目录后, `_toc_puts`
    #   按层渲染 —— 但若本函数把其中一层(实测 p48「玳安嬉遊蝴蝶巷」, 因邻列墨迹并进邻域窗,
    #   字高被量成正文 1.65 倍)认领成标题, 该行会被 `_toc_puts` 剔除、改由 `_display_put`
    #   画在**墨带中心**, 于是这一层不回原列(实测产物 x588.9, 列应在 x583.7)并与邻列字压字。
    #   判据: 本行所在 x 带(原始 OCR 行、与 nf_toc_shape 同口径 0.30x 列距归带)里 >=2 行 ->
    #   是目录网格行, 不可认领。真标题(「金瓶梅詞話總目錄」/「詞話第二冊目錄」)自成一带
    #   (实测组内 1 行), 不受影响。
    if g.get('toc') and disp_rows:
        _tr = g.get('toc_rows') or []
        _to2 = NF_TOC_COL_TOL * pitch * 2.0          # pt -> px
        _keep = []
        for r in disp_rows:
            _cx = (r[0] + r[1]) / 2.0
            # 页边行(页码/书眉)不属于目录网格, 也不该在这里当标题: 交 special_tex 按页边口径
            #   渲染(实测 p54 右下角页码「一〇」x838.5 在伪版心右缘外, 网格行解锁后会成为唯一
            #   「大字号行」而被标题判据认领)。
            if not (il - 2.0 <= _cx <= ir + 2.0):
                continue
            _nlay = _toc_grid_layers(_tr, _cx, _to2)
            if _nlay >= 2:
                if verbose:
                    print('    [目录网格] p%d 「%s」所在 x 带 %d 层 -> 不作标题(交 _toc_puts)'
                          % (pi + 1, r[4][:14], _nlay))
                continue
            _keep.append(r)
        disp_rows = _keep
    # 标题/署名行**稀少性**护栏: 大字号行只应是页内的少数行(章题页 1-3 条)。实测 wz7 p291 那类
    #   「年号大字 + 小字正文」页若把正文当基准, 会出现大批「大字号行」—— 那是整页字号分层, 不是标题,
    #   交给既有步进分类处理(不在这里动)。判据 = 大字号行数 <= max(1, 25% 长行数)。
    n_long = sum(1 for r in cand if len(r[4]) >= 8)
    if len(disp_rows) > max(1, int(0.25 * n_long)):
        if verbose and disp_rows:
            print('    [特殊行] p%d 大字号行 %d 条 > 上限(长行 %d 的 25%%) -> 不作标题处理'
                  % (pi + 1, len(disp_rows), n_long))
        disp_rows = []
    if not (lat_rows or disp_rows):
        return [], [], set()
    if _ROT_K['KX'] is None and lat_rows:
        if _rot_anchor(preamble, TMP, page_w, page_h, verbose) is None:
            lat_rows = []
            if not disp_rows:
                return [], [], set()
    puts, blocks, claimed = [], [], set()
    for r in lat_rows:
        bd = info[id(r)]['bd']
        p = _latin_tex(k, pi, r[4], bd, ink, verbose)
        if not p:
            continue
        puts += p; blocks.append((bd[0], bd[1])); claimed.add(id(r))
        _SPECIAL_STAT['latin'] += 1
    for r in disp_rows:
        bd = info[id(r)]['bd']
        runs = info[id(r)]['runs']
        if len(runs) < 2:
            continue
        rr0 = info[id(r)]['runs']
        hh0 = sorted(b - a for a, b in rr0)
        hm0 = hh0[len(hh0) // 2] if hh0 else 0.0
        cap0 = max(40.0, 3.0 * hm0)
        kp = sorted(b - a for a, b in rr0 if 4.0 <= b - a <= cap0)
        hm = kp[len(kp) // 2] if kp else info[id(r)]['hm']
        F = round(hm / INK_RATIO, 1)
        ds = sorted(b - a for a, b in zip([x[0] for x in runs], [x[0] for x in runs][1:]) if 0 < b - a < 3 * hm)
        step0 = ds[len(ds) // 2] if ds else F * 0.95
        sl = {'x0': bd[0], 'x1': bd[1], 'nr': len(runs), 'hm': hm, 'step': step0,
              'top': runs[0][0], 'bot': runs[-1][1], 'runs': runs}
        p = _display_put(r[4], F, (bd[0] + bd[1]) / 2.0, runs[0][0], step0, g, sl, pi)
        puts += p; blocks.append((bd[0], bd[1])); claimed.add(id(r))
        _SPECIAL_STAT['disp'] += 1
        if verbose:
            print('  [标题署名] p%d 「%s」字号 %.1f(正文 %.1f 的 %.2f 倍) 列 x%.1f-%.1f 顶%.1f 底%.1f 步进%.1f'
                  % (pi + 1, r[4][:14], F, body_h / INK_RATIO, F / max(1e-6, body_h / INK_RATIO),
                     bd[0], bd[1], runs[0][0], runs[-1][1], step0))
    if claimed:
        _SPECIAL_STAT['pages'][pi] = {'latin': len(lat_rows), 'disp': len(disp_rows),
                                      'body_h': round(body_h, 2)}
    return puts, blocks, claimed

def _special_applies(k):
    return bool(_SPECIAL_BLOCK.get(k))

# --- 影印页整页贴图(§1.995c) ---
def _fax_inkpx(i):
    """该源页的墨迹像素数(FAX_SC 倍灰度 Otsu 口径)。判据只用**比值**(页面积归一化在调用方做),
    故渲染倍率越低越省时: 实测 0.75x 与 1.5x 的判据值同量级(同页线性缩放)。"""
    import numpy as np
    import fitz
    pg = src_doc[i]
    pix = pg.get_pixmap(matrix=fitz.Matrix(FAX_SC, FAX_SC), colorspace=fitz.csGRAY)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    hist = np.bincount(a.ravel(), minlength=256).astype(float)
    tot = hist.sum()
    s_all = (np.arange(256) * hist).sum()
    wB = np.cumsum(hist); sB = np.cumsum(np.arange(256) * hist); wF = tot - wB
    thr = int(np.argmax(np.where((wB > 0) & (wF > 0),
                                 (s_all * wB / tot - sB) ** 2 / (wB * wF + 1e-9), -1)))
    return float((a < thr).sum()), pix.width, pix.height

FAX_REF_MIN_CH = int(os.environ.get('VERT_FAX_REF_MIN_CH') or 100)   # 「正文页」样本下限(OCR 字数)
FAX_REF_MIN_N = int(os.environ.get('VERT_FAX_REF_MIN_N') or 3)        # 参考样本不足此数 -> 不判贴图页
# --- 第三判据(taskV): OCR 重复行幻觉页 ---
# 现象: OCR 模型对表格/图版/复杂版式会陷入**模板循环**, 整页输出同一行几十~几百遍
#   (实测 wz7 p467/p511/p1039 = '1986年1月1日' x 227 行全同; p398/p523 = '1990年…' x 292 行)。
#   这类页**没有真实文字**, 重建只会把假字画出来 —— 且半角数字经 tate 全角化后字宽 0.745em,
#   本页字步进容不下 -> 直接超页幅(实测 p467 span 右缘 944.2pt vs 页宽 921.7 -> 越界 22.5pt)。
# 处置: 与影印页同办 —— 整页贴源图(读者看到的是原书那一页, 不是空白或垃圾字)。
# 判据(只用本书自身分布, 不写死页码/字数):
#   行数 >= FAX_DUP_MIN_ROWS **且** 唯一行占比 <= FAX_DUP_RATIO。
# 敏感性实测(行数门 10/20/30 x 占比 0.2/0.3/0.5 共 9 组): 恒命中 8 页、新增贴图 5 页 —— 判据稳健;
#   且命中的 3 页 p397(李家孫)/p1069(1986年1月1日)/p1127(e) **本就在原影印页列表**, 两者互相印证。
#   开关 VERT_FAX_DUP=0 可退回纯影印页口径。
FAX_DUP_ON = os.environ.get('VERT_FAX_DUP', '1') not in ('0', 'false', 'False')
FAX_DUP_MIN_ROWS = int(os.environ.get('VERT_FAX_DUP_MIN_ROWS') or 20)   # 幻觉页行数下限
FAX_DUP_RATIO = float(os.environ.get('VERT_FAX_DUP_RATIO') or 0.5)      # 唯一行占比上限

def fax_decide(nch, ipc):
    """纯判据: 每页 (OCR 非空白字数, 每字墨迹面积) -> {0based页: (nch, ipc, 倍数)}。
    参考量全部取**本书自身**(不写死页码/绝对值):
      ref_ch = 全书「正文页」(OCR 字数 >= FAX_REF_MIN_CH) 的字数中位
      ref    = 同批页的「每字墨迹面积」中位
    命中 = 每字墨迹面积 > FAX_IPC_MULT x ref **且** OCR 字数 < FAX_CHAR_MULT x ref_ch。
    样本不足(正文页 < FAX_REF_MIN_N)时返回空 —— 无参考量就不判(不硬猜)。"""
    tx = sorted(v for v in nch.values() if v >= FAX_REF_MIN_CH)
    if len(tx) < FAX_REF_MIN_N:
        return {}
    ref_ch = tx[len(tx) // 2]
    vals = sorted(ipc[i] for i in ipc if nch.get(i, 0) >= FAX_REF_MIN_CH)
    if len(vals) < FAX_REF_MIN_N:
        return {}
    ref = vals[len(vals) // 2]
    out = {}
    for i in sorted(ipc):
        if ipc[i] > FAX_IPC_MULT * ref and nch.get(i, 0) < FAX_CHAR_MULT * ref_ch:
            out[i] = (nch.get(i, 0), round(ipc[i], 1), round(ipc[i] / ref, 2))
    return out

_FAX_PAGES = None
def fax_pages(verbose=True):
    """影印页判据 -> {0based页: (nch, ipc, 倍数)}; 无影印页则 {}。判据见 §1.995c 注释 + fax_decide。"""
    global _FAX_PAGES
    if _FAX_PAGES is not None:
        return _FAX_PAGES
    _FAX_PAGES = {}
    if not (FAX_ON and NF_MODE and src_doc is not None):
        return _FAX_PAGES
    nch = {}
    for k in keys:
        nch[int(k)] = sum(1 for t in sl[k] for c in t if not c.isspace())
    ipc = {}
    for i in range(len(keys)):
        inkpx, pw, ph = _fax_inkpx(i)
        ipc[i] = inkpx / (nch.get(i, 0) + 1.0)
    _FAX_PAGES = fax_decide(nch, ipc)
    # 第三判据(taskV): OCR 重复行幻觉页 -> 同影印页一样贴源图(见 FAX_DUP_* 注释)
    if FAX_DUP_ON:
        _dup = {}
        for _k in keys:
            _rs = [str(t).replace('\n', '').strip() for t in sl.get(_k, [])]
            _rs = [t for t in _rs if t]
            _n = len(_rs)
            if _n < FAX_DUP_MIN_ROWS:
                continue
            _u = len(set(_rs))
            if _u / float(_n) <= FAX_DUP_RATIO:
                _i = int(_k)
                _dup[_i] = (nch.get(_i, 0), round(ipc.get(_i, 0.0), 1), round(_u / float(_n), 3))
        if _dup:
            _FAX_PAGES = dict(_FAX_PAGES)
            _FAX_PAGES.update(_dup)
            if verbose:
                print('[影印页] 重复行幻觉页(第三判据) %d 页: %s' % (
                    len(_dup), ', '.join('p%d(%d行/唯一占比%.3f)' % (i + 1, v[0], v[2])
                                         for i, v in sorted(_dup.items()))))
    tx = sorted(v for v in nch.values() if v >= FAX_REF_MIN_CH)
    ref = sorted(v for v in (ipc[i] for i in range(len(keys)) if nch.get(i, 0) >= FAX_REF_MIN_CH))
    ref = ref[len(ref) // 2] if ref else 0.0
    ref_ch = tx[len(tx) // 2] if tx else 0
    if verbose:
        print('[影印页] 判据: 每 OCR 字墨迹面积 > %.1f x 全书正文页中位(%.0fpx) 且 OCR 字数 < %.1f x 中位(%d)'
              % (FAX_IPC_MULT, ref, FAX_CHAR_MULT, ref_ch))
        if _FAX_PAGES:
            print('[影印页] 命中 %d 页: %s' % (
                len(_FAX_PAGES), ', '.join('p%d(%d字,%.1fx)' % (i + 1, v[0], v[2])
                                           for i, v in sorted(_FAX_PAGES.items()))))
        else:
            print('[影印页] 未命中任何页')
    return _FAX_PAGES

_FAX_IMG = {}
def fax_image(i):
    """影印页图: 落 TMP/fax/ 并返回路径。
    口径: 源页本身就是**扫描图**(整页一张 JPEG, 实测 1229x1914 ≈ 96dpi) —— 直接取源页那张图的
    原始字节落盘(dvipdfmx 走 DCTDecode 原样嵌入: 零重编码、零质量损失, 且体积 = 源书自身的图).
    只有源页没有内嵌图(矢量页)时才按 FAX_DPI 渲染一次(FAX_DPI 只在这个分支用到)。"""
    if i in _FAX_IMG:
        return _FAX_IMG[i]
    import fitz
    d = os.path.join(TMP, 'fax')
    os.makedirs(d, exist_ok=True)
    pg = src_doc[i]
    imgs = pg.get_images(full=True)
    if imgs:
        xref = max(imgs, key=lambda im: im[2] * im[3])[0]
        info = src_doc.extract_image(xref)
        p = os.path.join(d, 'p%d.%s' % (i + 1, info['ext']))
        with open(p, 'wb') as f:
            f.write(info['image'])
    else:
        from PIL import Image
        pix = pg.get_pixmap(matrix=fitz.Matrix(FAX_DPI / 72.0, FAX_DPI / 72.0), colorspace=fitz.csGRAY)
        im = Image.frombytes('L', (pix.width, pix.height), pix.samples)
        p = os.path.join(d, 'p%d.jpg' % (i + 1))
        im.save(p, quality=82)
    _FAX_IMG[i] = p
    return p

def fax_tex(i):
    """影印页 -> tex 片段: 整页铺源图(不重建)。页面尺寸由调用方按本页纸型设好。
    用 dvipdfmx 的**原样图片 special**(`pdf:image width ..pt height ..pt (file)`, 与 graphicx 的
    dvipdfmx 驱动同一算子)而不用 \\includegraphics: ① 竖排 preamble 不引入 graphicx
    (本管线的 tarticle+uplatex 下 graphicx 默认装 dvips 驱动, 实测 jpg 直接报 "Cannot determine
    size of graphic"); ② 尺寸/落点可控(见下)。
    落点标定(探针实测): 该算子的 (width,height) 按 **TeX pt -> bp** 折算(×0.99627 即 1/PT2BP),
    故写页幅 x PT2BP; 图片下缘落在 put 点**下方** (纸幅-\\paperheight 之差) = page_h x (PT2BP-1)
    -> put 的 y 取**负**该量。实测 921.8x1443pt 纸: put_y=-5.41 -> 图 bbox (0.00,0.01,921.84,1443.00)
    与页幅逐位相合; 705x1083.8pt 纸: put_y=-4.06 -> (0,-0.04,704.96,1083.80) 同合。"""
    p = fax_image(i)
    dy = -page_h * (PT2BP - 1.0)
    # 必须用**带星**的 \AddToShipoutPictureBG*(只作用于本页): 无星版会逐页累积
    #   (实测: 贴图页之后每页都被铺上该图 —— 与 §2 里 FG* 的注记同因)。
    return ('\\AddToShipoutPictureBG*{\\put(0,%.2f){'
            '\\special{pdf:image width %.1fpt height %.1fpt (%s)}}}'
            % (dy, page_w * PT2BP, page_h * PT2BP, p))

# ---------- 1.997) OCR 把竖排引號读成汉字「一」的源图墨迹判别(taskU-A) ----------
# 现象(用户实测, wz7 源页 354 / 样本 key54): 源书列首的竖排引號 ﹁ 被 OCR 读成汉字「一」
#   (`data/wz7/wz7_spotting_lines.json` key54 行6 = '一女不織兮男不耕，\n全憑賣俏做營生，',
#   而源图那里是 ﹁)。全书 OCR 共 1630 个「一」, 其中一部分是引號误识。
# 判据**只用源图墨迹形状**(不做文本猜测):
#   ① 竖排引號 ﹁/﹂ 是**直角细笔画**(横画 + 竖画), 汉字「一」是**一条横线** —— 源图上实测
#      (wz7 源页 354, 4x 灰度/Otsu 阈值, 逐墨块):
#        ﹁  墨块 19.0 x 9.1pt, 竖画在墨块右端(vpos 0.94), 横画在顶端(hpos 0.07);
#        ﹂  墨块 18.0 x 9.8pt, 竖画在左端(vpos 0.01), 横画在底端(hpos 0.69);
#        一  墨块 15-19 x 2.4-2.9pt(只有一条横线, 高 = 笔画粗);
#        本地字高(同列字 run 的 75 分位)约 23pt -> 「一」的墨高只有字高的 0.11-0.13 倍,
#        而引號是 0.38-0.42 倍, 且**竖画证据**(逐 x 的 y 跨度 vmax 远大于其自身笔画厚 vmed)。
#   ② 定位: 逐字 **复用渲染端的同一套对齐**(fit_gaps 的 DP, 见 _align 旁路) —— 不另立口径。
#   ③ 保守门: 命中 run 必须紧贴前一条 run(间距 ∈ [0.5, 1.6] 步进, 即它确在列内正常格序列上),
#      且形状三判据同时成立才改; 判据不成立一律**不动**(宁少改不误改)。
# 替换是 **1:1 字符替换**(一 -> 「/」/『/』), 字数/格数不变 -> 列位/字距/字号全不变, 只有字形变
#   (竖排形态由 §1.0c 的 VERT_FORMS 渲染)。只走无版框伪槽格页(有版框书如 wz6 一字不改)。
QFIX_ON = os.environ.get('VERT_QFIX', '1') not in ('0', 'false', 'False')
QFIX_MIN_RATIO = float(os.environ.get('VERT_QFIX_MIN_RATIO') or 0.25)   # 引號判据: 墨高/字高 下限
QFIX_W_RATIO = float(os.environ.get('VERT_QFIX_W_RATIO') or 0.45)       # 引號判据: 墨宽/字高 下限(排标点)
QFIX_VPOS = float(os.environ.get('VERT_QFIX_VPOS') or 0.70)             # 竖画位置: >= 该值 = 在右端(开口引號)
QFIX_HPOS = float(os.environ.get('VERT_QFIX_HPOS') or 0.60)             # 横画位置: >= 该值 = 在底端(闭口引號)
# 双引號 ﹃/﹄: 源书全书只有 14 个(OCR 全读对), 其墨高上限未标定(实测候选要么被并字 run 污染、要么
#   与单体 ﹁﹂ 同高) -> **默认关**(宁少改不误改): 命中一律按单体 「/」 替换, 且高度超 QFIX_MAX_RATIO
#   的直接不改。置 1 可开(仅对照用)。
QFIX_DOUBLE = os.environ.get('VERT_QFIX_DOUBLE', '0') not in ('0', 'false', 'False')
# 位置闸门(§1.997 ④): 墨块顶相对「本字渲染格顶」的**格内偏移**合法区间(步进倍数)。
#   引號类小墨画在格内**偏下**处(实测 wz7: 墨顶 = 本格顶 + 0.36-0.42 步进, 与「，」同位), 而相邻格
#   的墨顶会落在 +1.36 附近 —— 故用**非对称**区间把「本格」与「邻格」分开(实测 77 处判定的 dpos
#   全在 [-0.1, 0.72], 而被位置闸门拦下的 1.0-1.5 全是「文本比源书少字 -> 整列错位」的不可信情形)。
QFIX_MAX_RATIO = float(os.environ.get('VERT_QFIX_MAX_RATIO') or 0.60)   # 引號墨高/字高 上限(排除并字长 run)
QFIX_POS_LO = float(os.environ.get('VERT_QFIX_POS_LO') or -0.25)
QFIX_POS_HI = float(os.environ.get('VERT_QFIX_POS_HI') or 0.85)
QFIX_NB = os.environ.get('VERT_QFIX_NB', '0') not in ('0', 'false', 'False')   # 旧「邻字反证」闸门(默认关, 见 §1.997 ④)
_qfix_log = []          # 逐处修正记录(落盘对账)
QFIX_DBG = os.environ.get('VERT_QFIX_DBG') == '1'   # 逐候选打印(判据调参用)
_qfix_stat = {'cand': 0, 'dash': 0, 'fixed': 0, 'skip': 0, 'rej': {}}
_qfix_all = []          # 逐候选记录(含判为「真一」者 —— 双向抽样核对误改率用)
_qfix_recall = {'ocr_ok': 0, 'dropped': 0, 'missed': 0, 'other': 0}   # 召回对账(§1.997, 只统计)
_qfix_miss = []         # 召回对账: 「引號墨对到『一』但未改」明细(上限 400)
_qfix_pend = {}         # ri(id) -> 本列已判为引號的字符下标(召回对账要把它们排除)
_qfix_other = []        # 召回对账: 「引號墨对到其它字」明细(上限 400)

def _qfx_runbox(ink, sub_x0, sub_x1, y0, y1, sc):
    """墨块窗口(pt: x 取该列带, y 取 run 的上下缘) -> 形状统计 dict 或 None。
    形状口径(全部相对本墨块自身, 与扫描分辨率/纸型无关):
      w/h    = 墨迹外接框宽/高(pt)
      vmed   = 逐 x 的 y 跨度中位(= 笔画厚)
      vmax   = 逐 x 的 y 跨度最大(= 竖画长度; 「一」的 vmax 就是笔画厚)
      hmax   = 逐 y 的 x 跨度最大(= 横画长度)
      vpos   = vmax 达到 0.8vmax 的那些 x 的归一化位置(0=左端, 1=右端)
      hpos   = hmax 达到 0.8hmax 的那些 y 的归一化位置(0=顶端, 1=底端)"""
    import numpy as np
    xa, xb = int(sub_x0 * sc), int(sub_x1 * sc)
    ya, yb = int(y0 * sc), int(y1 * sc)
    if xb <= xa or yb <= ya: return None
    sub = ink[ya:yb, xa:xb]
    if sub.size == 0 or not sub.any(): return None
    # x 投影 -> 只留「含本格中心」的那条 x-run(= 该格的墨), 撇掉邻列/邻字侵入的墨与噪点
    _c = sub.any(axis=0)
    _runs = []
    _a = None
    for _i, _v in enumerate(_c):
        if _v and _a is None: _a = _i
        elif not _v and _a is not None: _runs.append((_a, _i)); _a = None
    if _a is not None: _runs.append((_a, len(_c)))
    _mid = len(_c) // 2
    _pick = None
    for _p, _q in _runs:
        if _p <= _mid < _q: _pick = (_p, _q); break
    if _pick is None:
        _pick = max(_runs, key=lambda t: t[1] - t[0])
    sub = sub[:, _pick[0]:_pick[1]]
    if sub.size == 0 or not sub.any(): return None
    ys, xs = np.where(sub)
    h = (ys.max() - ys.min() + 1) / sc
    w = (xs.max() - xs.min() + 1) / sc
    vv = []
    for c in range(sub.shape[1]):
        yy = np.where(sub[:, c])[0]
        vv.append((yy.max() - yy.min() + 1) / sc if len(yy) else 0.0)
    hh = []
    for r in range(sub.shape[0]):
        xx = np.where(sub[r, :])[0]
        hh.append((xx.max() - xx.min() + 1) / sc if len(xx) else 0.0)
    vmax = max(vv); hmaxv = max(hh)
    if vmax <= 0 or hmaxv <= 0: return None
    vh = [i for i, v in enumerate(vv) if v >= 0.8 * vmax]
    hh2 = [i for i, v in enumerate(hh) if v >= 0.8 * hmaxv]
    return {'w': w, 'h': h, 'vmax': vmax, 'vmed': statistics.median(vv),
            'hmax': hmaxv, 'hmed': statistics.median(hh),
            'x0': (xa + _pick[0]) / sc, 'x1': (xa + _pick[1]) / sc,
            'vpos': (sum(vh) / len(vh)) / max(1, len(vv) - 1),
            'hpos': (sum(hh2) / len(hh2)) / max(1, len(hh) - 1)}

def _qfx_class(st, h_char):
    """墨块形状 -> 'dash'(一) / 'open'(﹁/﹃) / 'close'(﹂/﹄) / None(不改)。
    三条同源判据(相对本页本列字高 h_char): ① 墨高 >= 0.25 字高(一条横线只有笔画厚, 达不到);
    ② 墨宽 >= 0.45 字高(排除标点「，。」与小碎墨); ③ 竖画/横画位置定开口闭口。"""
    if not st or h_char <= 0: return None
    if st['h'] < QFIX_MIN_RATIO * h_char: return 'dash'
    if st['w'] < QFIX_W_RATIO * h_char: return None                 # 又小又窄 = 标点/碎墨
    if st['vmax'] < QFIX_MIN_RATIO * h_char: return 'dash'          # 无竖画 = 横线
    # 墨高上限(防「并字长 run」): 引號墨高只有字高的 0.36-0.49(实测 80 处判定), 而**相邻字粘连**
    #   会并成一条高 run(实测 wz7 源页 30 的「……一入陰界者」: 「一」与下一字「入」的墨相碰 = 一条
    #   h=20.0(0.87 x 字高) 的 run) —— 那种 run 的竖/横笔证据会碰巧像引號, 故按**高度上限**直接排除。
    if st['h'] > QFIX_MAX_RATIO * h_char: return None
    if st['vpos'] >= QFIX_VPOS and st['hpos'] <= 1.0 - QFIX_HPOS: return 'open'
    if st['vpos'] <= 1.0 - QFIX_VPOS and st['hpos'] >= QFIX_HPOS: return 'close'
    return None

def _qfx_slot_runs(sl, ink, it, ib):
    """该槽的 (墨迹 run 全表, 字列顶 T, 字列底 B)。
    两点与渲染端**有意不同**:
      ① **不套 _trim_marks**(§1.976): 本判别的目标正是「列首/列尾的引號墨」, 若先把它剔掉, 对齐
         就会把「一」对到**下一个字**上(实测 wz7 页 355 的 ﹁ 被剔后 char0 对到 女 的 run)。
         列顶/底交由 §1.976 用**文本侧证据**处理(引號字不剔, 见 _trim_marks ④)。
      ② **用全高 run 表**(min_h=0, 不套 _slots_of_edges 的 4pt 碎片下限): 汉字「一」的墨高只有
         2.4-2.9pt < 4pt —— 按渲染端的 rs 它根本不入表(实测 wz7 页 55 的「一場」列: run 表里没有
         那条横线, 对齐只能把「一」判成"无墨"), 那样本判别就永远看不到「一」的墨。
         故这里自取 `_slot_runs(min_h=0.0)` 的原表(与 _slots_of_edges 的 raw 同参)。"""
    return _slot_runs(ink, sl['x0'], sl['x1'], it, ib, min_h=0.0), sl['top'], sl['bot']

def nf_fix_quotes(k, pi, m):
    """本页 OCR 文本里的「一」逐处按**源图墨迹形状**判别, 只把形状确为引號者改回 「/」/『/』。
    返回修正处数(原地改 all_rows[k] 的文本; 1:1 替换不动任何几何量)。"""
    if not QFIX_ON or not m or not m['g'].get('virtual'): return 0
    rows_all = all_rows.get(k) or []
    if not any('一' in r[4] for r in rows_all): return 0
    prov = {}
    body, _note, _out = page_rows(k, m, pi, prov=prov)
    if not body: return 0
    rows = sorted(body, key=lambda r: -r[0])
    slots = sorted(m['body'], key=lambda s: -s['x1'])
    if _SPECIAL_BLOCK.get(k):
        slots = [s for s in slots if not _band_blocked(s['x0'], s['x1'], _SPECIAL_BLOCK[k])]
    R, C = len(rows), len(slots)
    if not C: return 0
    if 1.7 * C <= R <= 2.3 * C: return 0            # 双行小字页: 槽内再分左右子列, 对齐口径不同
    ink = _frame_ink(pi, m['g'])
    _sc = 2.0                                        # 源图墨迹像素 = 2x pt(144dpi, §0)
    cap = m['step_cap']
    h_ink = INK_RATIO * m['font']
    pairs = _align_rows_slots(rows, slots,
                              prior=(NF_POS_PRIOR if (m['g'].get('virtual') and NF_POS_PRIOR > 0) else 0.0))
    fixes = {}                                       # ri -> [(字符下标, 新字, 证据 dict)]
    for ri, si in pairs:
        text = rows[ri][4]; sl = slots[si]
        if '一' not in text or len(text) < 2: continue
        runs, T, B = _qfx_slot_runs(sl, ink, m['g']['in_t'], m['g']['in_b'])
        if len(runs) < 3 or T is None or B is None: continue
        step = sl.get('step') or cap
        if step <= 1.0: continue
        al = {}
        _ip2 = (lambda y: any(a - 0.5 <= y <= b + 0.5 for a, b in runs)) if (GAP_INK and runs) else None
        _gaps = fit_gaps(runs, text, step, T, B, h_ink=h_ink, _align=al, ink_probe=_ip2)
        if not al: continue
        # 逐字「渲染格号」(与 col_puts 同口径): 渲染端把 char i 摆在 cell (i + 之前插入的空格格数)
        _gb = [0] * (len(text) + 1)
        for _ci, _e in _gaps:
            if 0 <= _ci <= len(text): _gb[_ci] += _e
        _gpre = []                                   # _gpre[i] = 本字**之前**(含第 i 位)插入的空格格数
        _gpre.append(_gb[0])
        for _k in range(1, len(text) + 1):
            _gpre.append(_gpre[-1] + _gb[_k])
        h_char = _big_hm(runs)
        if h_char <= 0: continue
        # 召回对账(只统计, 不改判据): 本列**所有小墨 run** 里判为引號的, 其对齐到的字符是什么?
        #   「引號字」= 文本里本就有引號(OCR 读对) / 「一」= 本判别的目标 / 无 = OCR 读丢了引號。
        for i, ch in enumerate(text):
            if ch != '一': continue
            j = al.get(i)
            if j is None or j >= len(runs):
                if QFIX_DBG:
                    print('    [QFIX-DBG] p%d 列x%.1f-%.1f 字%d/%d %r 未对齐(run 数 %d) -> 跳过'
                          % (pi + 1, sl['x0'], sl['x1'], i, len(text), text[max(0, i - 5):i + 6],
                             len(runs)))
                continue
            _qfix_stat['cand'] += 1
            # ③ 列内正常格序列证据: 与**相邻字符**对到的 run 间距 ∈ [0.5, 1.6] 步进(该墨块确在列
            #    的字格序列上)。按字符取而非按 run 表取 —— 全高 run 表里有笔画碎片/点画, 相邻 run
            #    可能只是同一字的一部分。
            dgs = []
            for _nb in (i - 1, i + 1):
                _jj = al.get(_nb)
                if _jj is not None and _jj < len(runs):
                    dgs.append(abs(runs[j][0] - runs[_jj][0]) / step)
            if not dgs:
                _qfix_stat['skip'] += 1
                continue
            dg = min(dgs)
            if not (0.5 <= dg <= 1.6):
                _qfix_stat['skip'] += 1
                continue
            st = _qfx_runbox(ink, sl['x0'], sl['x1'], runs[j][0] - 0.5, runs[j][1] + 0.5, _sc)
            cls = _qfx_class(st, h_char)
            if QFIX_DBG:
                print('    [QFIX-DBG] p%d 列x%.1f-%.1f 字%d/%d %r j=%d dg=%.3f char_h=%.2f st=%s -> %s'
                      % (pi + 1, sl['x0'], sl['x1'], i, len(text), text[max(0, i - 4):i + 5], j, dg,
                         h_char, st and dict((kk, round(vv, 2)) for kk, vv in st.items()), cls))
            # ④ **位置闸门**(本判别的正确性依据): 命中墨块必须落在「本字在本列被渲染到的那一格」上。
            #    渲染端 col_puts 是**按格号摆放**的(char i 摆在 cell (i + 之前插入的空格格数), 与
            #    源书格序一一对应), 故只有「墨块 y ≈ 本字的渲染格位」时, 把该字改成引號才等于
            #    「把源图该格的字形改成引號」—— 否则改的是别格的字(实测反例: 文本比源书少一个字的
            #    列, DP 会把 char i 对到 cell i 的墨上, 而该格在源书里是 OCR 读丢的那个引號)。
            #    判据 = |墨块顶 - 本字渲染格顶| <= QFIX_POS_TOL x 步进。
            _pred_i = T + (i + _gpre[i]) * step
            _dpos = (runs[j][0] - _pred_i) / step
            if not (QFIX_POS_LO <= _dpos <= QFIX_POS_HI):
                if QFIX_DBG:
                    print('        [QFIX-DBG·pos] 字%d/%d %r 墨顶%.1f 预测格位%.1f (T%.1f +%d格 x%.1f) '
                          '格内偏移 %.2f 格 越界(%.2f..%.2f)' % (
                              i, len(text), text[max(0, i - 4):i + 5], runs[j][0], _pred_i,
                              T, i + _gpre[i], step, _dpos, QFIX_POS_HI))
                _qfix_stat['skip'] += 1
                continue
            # ④b 旧口径(可选, 默认关): 与它相邻的字不得落在「宽而扁的小墨」上。
            _nb_bad = False
            if QFIX_NB:
                for _nb in (i - 1, i + 1):
                    _jj = al.get(_nb)
                    if _jj is None or _jj >= len(runs): continue
                    _st2 = _qfx_runbox(ink, sl['x0'], sl['x1'], runs[_jj][0] - 0.5, runs[_jj][1] + 0.5, _sc)
                    if _st2 and _st2['h'] < QFIX_MIN_RATIO * h_char and _st2['w'] >= QFIX_W_RATIO * h_char:
                        _nb_bad = True
                        if QFIX_DBG:
                            print('        [QFIX-DBG·nb] 邻字 %r 对到宽扁小墨 h=%.1f w=%.1f' % (
                                text[_nb], _st2['h'], _st2['w']))
                        break
            _rec = {'page': pi + 1, 'key': k, 'idx': i, 'nchar': len(text), 'cls': cls,
                    'ctx': text[max(0, i - 6):i + 7], 'col_cx': round((sl['x0'] + sl['x1']) / 2.0, 1),
                    'mark_x': [round(st['x0'], 1), round(st['x1'], 1)] if st else None,
                    'mark_y': [round(runs[j][0], 1), round(runs[j][1], 1)],
                    'w': round(st['w'], 2) if st else None, 'h': round(st['h'], 2) if st else None,
                    'vpos': round(st['vpos'], 3) if st else None,
                    'hpos': round(st['hpos'], 3) if st else None,
                    'h_char': round(h_char, 2), 'step': round(step, 2), 'dg': round(dg, 3),
                    'dpos': round(_dpos, 3), 'nb_bad': _nb_bad}
            if cls == 'dash':                        # 真「一」: 与反证无关(不改), 先出
                _qfix_all.append(_rec)
                _qfix_stat['dash'] += 1
                continue
            if _nb_bad:
                _rec['cls'] = 'rej_nb'
                _qfix_all.append(_rec)
                _qfix_stat['skip'] += 1
                continue
            if cls is None:
                _qfix_all.append(_rec)
                _qfix_stat['skip'] += 1
                continue
            _rec['cls'] = cls + ('2' if (QFIX_DOUBLE and st['h'] >= 0.55 * h_char) else '')
            _qfix_all.append(_rec)
            dbl = bool(QFIX_DOUBLE and st['h'] >= 0.55 * h_char)     # 双层引號(﹃/﹄)的墨高更大
            new = ('『' if dbl else '「') if cls == 'open' else ('』' if dbl else '」')
            fixes.setdefault(ri, []).append((i, new, st, runs[j], dg, h_char, step, len(text)))
            _qfix_pend.setdefault(id(rows[ri]), []).append(i)
        _used = {}
        for _ci, _ji in al.items():
            _used.setdefault(_ji, _ci)
        _fixed_ci = set(z for z in _qfix_pend.get(id(rows[ri]), []))
        for _j, _r in enumerate(runs):
            if (_r[1] - _r[0]) >= 0.45 * h_char: continue        # 只查「小墨」候选(廉价预筛)
            _ci = _used.get(_j)
            if _ci is not None and text[_ci] in QFIX_QFAM:
                _qfix_recall['ocr_ok'] += 1; continue
            _st3 = _qfx_runbox(ink, sl['x0'], sl['x1'], _r[0] - 0.5, _r[1] + 0.5, _sc)
            if _qfx_class(_st3, h_char) not in ('open', 'close'):
                continue
            if _ci is None:
                _qfix_recall['dropped'] += 1
            elif _ci in _fixed_ci:
                _qfix_recall['ocr_ok'] += 1          # 本轮判为引號并已改(等价于"已读对")
            elif text[_ci] == '一':
                _qfix_recall['missed'] += 1
                if len(_qfix_miss) < 400:
                    _qfix_miss.append({'page': pi + 1, 'idx': _ci, 'nchar': len(text),
                                       'ctx': text[max(0, _ci - 6):_ci + 7],
                                       'col_cx': round((sl['x0'] + sl['x1']) / 2.0, 1),
                                       'mark_x': [round(_st3['x0'], 1), round(_st3['x1'], 1)] if _st3 else None,
                                       'mark_y': [round(_r[0], 1), round(_r[1], 1)],
                                       'w': round(_st3['w'], 2) if _st3 else None,
                                       'h': round(_st3['h'], 2) if _st3 else None,
                                       'vpos': round(_st3['vpos'], 3) if _st3 else None,
                                       'hpos': round(_st3['hpos'], 3) if _st3 else None,
                                       'h_char': round(h_char, 2), 'step': round(step, 2),
                                       'a_cls': _qfx_class(_st3, h_char), 'key': k})
            else:
                _qfix_recall['other'] += 1
                if len(_qfix_other) < 400:
                    _qfix_other.append({'page': pi + 1, 'idx': _ci, 'ch': text[_ci],
                                        'ctx': text[max(0, _ci - 6):_ci + 7],
                                        'mark_x': [round(_st3['x0'], 1), round(_st3['x1'], 1)] if _st3 else None,
                                        'mark_y': [round(_r[0], 1), round(_r[1], 1)],
                                        'w': round(_st3['w'], 2) if _st3 else None,
                                        'h': round(_st3['h'], 2) if _st3 else None,
                                        'vpos': round(_st3['vpos'], 3) if _st3 else None,
                                        'hpos': round(_st3['hpos'], 3) if _st3 else None,
                                        'h_char': round(h_char, 2), 'key': k})
    if not fixes: return 0
    # 写回: 合并行是新建 tuple, 按 prov 拆回**原始 OCR 行对象**再替换(1:1 字符替换, 长度不变)
    widx = dict((id(r), n) for n, r in enumerate(rows_all))
    newrows = list(rows_all)
    nfix = 0
    for ri, items in fixes.items():
        pieces = prov.get(id(rows[ri])) or []
        for (i, new, st, run, dg, h_char, step, ntl) in items:
            acc = 0
            for sid, ln in pieces:
                if acc <= i < acc + ln:
                    o = i - acc
                    n0 = widx.get(sid)
                    if n0 is None: break
                    r0 = newrows[n0]
                    if o >= len(r0[4]) or r0[4][o] != '一': break
                    newrows[n0] = (r0[0], r0[1], r0[2], r0[3], r0[4][:o] + new + r0[4][o + 1:])
                    nfix += 1
                    _qfix_stat['fixed'] += 1
                    _qfix_log.append({'page': pi + 1, 'key': k,
                                      'col_x0': round(sl['x0'], 1), 'col_x1': round(sl['x1'], 1),
                                      'col_cx': round((sl['x0'] + sl['x1']) / 2.0, 1),
                                      'mark_x': [round(st['x0'], 1), round(st['x1'], 1)],
                                      'idx': i, 'nchar': ntl,
                                      'char': new, 'ctx': r0[4][max(0, o - 6):o + 7],
                                      'mark_y': [round(run[0], 1), round(run[1], 1)],
                                      'w': round(st['w'], 2), 'h': round(st['h'], 2),
                                      'vpos': round(st['vpos'], 3), 'hpos': round(st['hpos'], 3),
                                      'h_char': round(h_char, 2), 'step': round(step, 2), 'dg': round(dg, 3)})
                    break
                acc += ln
    if nfix:
        all_rows[k] = newrows
    return nfix

# ---------- 1.998) 竖排闭引号 ﹂ 被 OCR 读成「。」/「一」的格位形状纠错(taskCM) ----------
# 背景(用户实测 wz7 源页 444): 源书诗句列尾「…衙。﹂」的闭引号 ﹂ 被 OCR 读成「。」或「一」
#   (`致死冤魂塞滿衙。` / `溟冷飢鬼揮鍾馗。一` 两列用户看到的都是句号/「一」), 渲染端照 OCR
#   文本画 -> 闭引号整列缺失。本段在**渲染端**做码位纠错: 用源图墨迹形状判「尾格其实是引号」,
#   只改码位/补一个引号, 不动既有字的字数/格数/列位/字号。
# 与 §1.997(taskU-A) 的分工: taskU 处理正文里的「一」(run/DP 对齐 + 竖画位置判据, 已改回 79 处);
#   本段处理**列尾的「。」/「一」**。取样不用 OCR 行盒猜, 用渲染端已算好的槽位 + 源图墨迹 run:
#   实测 wz7 大量诗句列是**上下半句合并列**(OCR 两行 y 间隔 <= 2.5 步进), 渲染端按合并后字数
#   均分步进 -> 列尾格位比源书高 1-2 格; 而列尾引号墨又比正文淡(阈值 185 下仅 1.3-8.5pt),
#   不进 slot 的 top/bot。故取「本列 x 带内、槽底附近的最后一条墨 run」—— 它就是源书该列
#   最末一个字的真实墨迹(窗口天然只含一个字形, 正是外部工具拿不到的那块图)。
# 判据(与 tmp_vert/cj5/shape_clf2.py 逐字相同, 由 8 个已标真值反推; **不要改阈值**):
#   bar    : 宽高比 >= 1.8 且 高 <= 0.30 x 字格   (汉字「一」: 单条长横, 无竖臂)
#   corner : 四角极差 >= 0.35 且 最大角 >= 0.40 且 中心 <= 0.45  (直角引号: 实心交点 + 两臂)
#   ring   : 中心 <= 0.35 且 四边最薄 >= 0.05 且 四角极差 < 0.35 (句号: 闭合圆环, 四角均衡)
#   其余 -> other(不动)
# 动作(见 _qsf_decide): 尾格 corner + 末字「一」-> 1:1 换成闭引号; 末字「。」且**前一条 run
#   是 ring** -> 说明这个「。」是 OCR 读对的句号、尾格那条小墨是 OCR 读丢的引号 -> 追加一个
#   闭引号(QSF_APPEND; 落在源墨迹位置, 不动既有字); 其余 corner -> 1:1 换成闭引号。
#   替换/追加都用 '」'(渲染端 §1.0c 转竖排形态 ﹂ 并按 BR_SIZE 标定字号; 文本层即 U+FE42)。
# 只走无版框书(_NF['on']); 有版框书(wz6)整段不执行 -> 逐字节零回归。
QSF_ON = os.environ.get('VERT_QSF', '1') not in ('0', 'false', 'False')
QSF_DBG = os.environ.get('VERT_QSF_DBG') == '1'
QSF_APPEND = os.environ.get('VERT_QSF_APPEND', '1') not in ('0', 'false', 'False')
QSF_MIN_PIX = int(os.environ.get('VERT_QSF_MIN_PIX') or 24)      # 墨迹像素下限(< = 无墨, 不动)
QSF_TAIL_DN = float(os.environ.get('VERT_QSF_TAIL_DN') or 1.3)   # 槽底向下找 run 的外扩(步进倍数)
QSF_MIN_RUN = float(os.environ.get('VERT_QSF_MIN_RUN') or 2.5)   # 尾 run 高下限(pt, 排扫描噪点)
QSF_BAR_AR = float(os.environ.get('VERT_QSF_BAR_AR') or 1.8)     # bar 判据: 宽高比下限
QSF_BAR_H = float(os.environ.get('VERT_QSF_BAR_H') or 0.30)      # bar 判据: 墨高/字格 上限
QSF_CORNER_SPREAD = float(os.environ.get('VERT_QSF_CORNER_SPREAD') or 0.35)   # corner: 四角极差
QSF_CORNER_MAX = float(os.environ.get('VERT_QSF_CORNER_MAX') or 0.40)         # corner: 最大角
QSF_CORNER_CTR = float(os.environ.get('VERT_QSF_CORNER_CTR') or 0.45)         # corner: 中心上限
QSF_RING_CTR = float(os.environ.get('VERT_QSF_RING_CTR') or 0.35)             # ring: 中心上限
QSF_RING_EDGE = float(os.environ.get('VERT_QSF_RING_EDGE') or 0.05)           # ring: 四边最薄
QSF_PAD_X = float(os.environ.get('VERT_QSF_PAD_X') or 2.0)       # 取样 x 两侧收紧(pt)
QSF_MIN_GLYPH = float(os.environ.get('VERT_QSF_MIN_GLYPH') or 0.20)  # 单字形最小尺寸/字格(排碎墨)
_qsf_stat = {'cand': 0, 'corner': 0, 'replace': 0, 'append': 0, 'ring': 0, 'bar': 0,
             'other': 0, 'norun': 0}
_qsf_log = []

def _qsf_analyze(g):
    """格内墨迹二值图 -> 形状特征 dict 或 None(判据与 tmp_vert/cj5/shape_clf2.py analyze 相同)。"""
    import numpy as np
    ys, xs = np.where(g)
    if len(ys) < QSF_MIN_PIX:
        return None
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    sub = g[y0:y1 + 1, x0:x1 + 1]
    h, w = sub.shape
    if h < 2 or w < 2:
        return None

    def dens(a0, a1, b0, b1):
        r0, r1 = int(a0 * h), max(int(a1 * h), int(a0 * h) + 1)
        c0, c1 = int(b0 * w), max(int(b1 * w), int(b0 * w) + 1)
        blk = sub[r0:r1, c0:c1]
        return float(blk.mean()) if blk.size else 0.0

    return dict(h=h, w=w, fill=float(sub.mean()),
                c1=dens(0, .30, 0, .30), c2=dens(0, .30, .70, 1.),
                c3=dens(.70, 1., 0, .30), c4=dens(.70, 1., .70, 1.),
                ctr=dens(.30, .70, .30, .70),
                top=dens(0, .20, .20, .80), bot=dens(.80, 1., .20, .80),
                lef=dens(.20, .80, 0, .20), rig=dens(.20, .80, .80, 1.))

def _qsf_classify(f, cell_pt, px_per_pt=2.0):
    """形状特征 -> ('bar'|'corner'|'ring'|'other', 说明串)。阈值 = 8 个已标真值反推值。"""
    hpt, wpt = f['h'] / px_per_pt, f['w'] / px_per_pt
    ar = wpt / hpt if hpt else 99.0
    corners = [f['c1'], f['c2'], f['c3'], f['c4']]
    spread = max(corners) - min(corners)
    desc = '四角%.2f/%.2f/%.2f/%.2f 极差%.2f 中心%.2f w%.1f h%.1f' % (
        f['c1'], f['c2'], f['c3'], f['c4'], spread, f['ctr'], wpt, hpt)
    if ar >= QSF_BAR_AR and hpt <= QSF_BAR_H * cell_pt:
        return 'bar', desc
    if spread >= QSF_CORNER_SPREAD and max(corners) >= QSF_CORNER_MAX and f['ctr'] <= QSF_CORNER_CTR:
        return 'corner', desc
    if (f['ctr'] <= QSF_RING_CTR and min(f['top'], f['bot'], f['lef'], f['rig']) >= QSF_RING_EDGE
            and spread < QSF_CORNER_SPREAD):
        return 'ring', desc
    return 'other', desc

def _qsf_decide(ch, tail_cls, prev_cls):
    """尾格形状 + 文本末字 -> 'replace'(1:1 换) / 'append'(补一字) / None(不动)。纯函数。"""
    if tail_cls != 'corner':
        return None
    if ch == '一':
        return 'replace'
    if ch == '。' and prev_cls == 'ring' and QSF_APPEND:
        return 'append'
    return 'replace'

def _qsf_win_x(sl, ink_w):
    """取样 x 窗(px, 2x): 槽中心 ±0.75 x 本槽宽。**不能直接用槽带** —— 实测槽格是标定后的均匀
    栅格, 有整列偏移(源页 444 的列墨迹 x519-543 被排进槽 529-555, 偏 +11pt), 按槽带裁会把
    引号的竖臂切掉(实测四角特征退化成一条横线 -> 误判 bar)。槽中心只当先验, 实际墨迹 run 说了算。"""
    sc = 2.0
    pitch = max(8.0, sl['x1'] - sl['x0'])
    cx = (sl['x0'] + sl['x1']) / 2.0
    rad = pitch
    return int(max(0, round((cx - rad) * sc))), int(min(ink_w, round((cx + rad) * sc))), cx

def _qsf_col_xrun(ink, sl, ylo, yhi):
    """宽 x 窗 + y 窗内, 取**离槽中心最近**的一条墨迹 x-run(px 界) -> (xa, xb) 或 None。
    这一步定的是「本列」的 x 带: 槽格是标定后的均匀栅格, 可能有整列偏移(实测源页 444 列墨迹
    x519-543 被排进槽 529-555), 按槽带裁会切掉引号竖臂; 而直接放宽到整页会把邻列的连续正文
    投影进来(实测列 f 的 y-run 被邻列连成整段, 列尾小墨根本分不出来)。所以先按 x 距离认列,
    再在该列内做 y 投影。"""
    sc = 2.0
    H, W = ink.shape
    xa, xb, cx = _qsf_win_x(sl, W)
    ya = int(max(0, round((ylo + 0.5) * sc)))
    yb = int(min(H, round((yhi - 0.5) * sc)))
    if xb <= xa or yb <= ya:
        return None
    strip = ink[ya:yb, xa:xb]
    rad = max(8.0, sl['x1'] - sl['x0'])
    pick = None
    # x 投影按 4pt 桥接: 同一列不同字的笔画覆盖的 x 子区间之间有缝(实测列 b 被切成
    #   x680-684 一条竖笔, 只有真列宽 653-699 的 1/6); 列间空白 >= 10pt, 不会被桥接跨过。
    for a, b in _runs(strip.any(axis=0), 8):
        if b - a < 4:                                    # 宽 < 2pt = 噪点/列缝渗墨
            continue
        xpa, xpb = (xa + a) / sc, (xa + b + 1) / sc
        d = abs((xpa + xpb) / 2.0 - cx)
        if d <= rad and (pick is None or d < pick[0]):
            pick = (d, a, b)
    if pick is None:
        return None
    return xa + pick[1], xa + pick[2] + 1

def _qsf_runs_wide(ink, sl, ylo, yhi):
    """本列 x 带内的墨迹 y-run 列表(页顶向下 pt, 自上而下)。y 窗不套 QSF_MIN_RUN 过滤 ——
    列尾的引号/句号本身就是小墨(1.3-8.5pt), 过滤掉就看不到它了。"""
    sc = 2.0
    H, _W = ink.shape
    bd = _qsf_col_xrun(ink, sl, ylo, yhi)
    if bd is None:
        return []
    ya = int(max(0, round((ylo + 0.5) * sc)))
    yb = int(min(H, round((yhi - 0.5) * sc)))
    if yb <= ya:
        return []
    sub = ink[ya:yb, bd[0]:bd[1]]
    out = []
    for a, b in _runs(sub.any(axis=1), 1):
        if b - a < 2:
            continue
        out.append(((ya + a) / sc, (ya + b + 1) / sc))
    return out

def _qsf_tail_runs(ink, sl, step):
    """本列槽底附近的源图墨 run 列表(页顶向下 pt), 列表顺序 = 自上而下。
    窗口 = [槽顶 - 0.5 步进, 槽底 + QSF_TAIL_DN 步进]: 向上留余量给「整列只有一两个字」的短列;
    向下外扩是捞**淡墨引号** —— 实测它常落在 slot bot 之下(wz7 p444 列尾 ﹂ 在槽底外 0.8-1.1
    步进; 该墨在阈值 185 下只有 1.3-8.5pt, 不进 _slot_runs 的 dink 统计 -> slot bot 少算一格)。"""
    top, bot = sl.get('top'), sl.get('bot')
    if top is None or bot is None or step <= 0:
        return []
    ylo = max(0.0, top - 0.5 * step)
    yhi = min(page_h, bot + QSF_TAIL_DN * step)
    if yhi <= ylo:
        return []
    return _qsf_runs_wide(ink, sl, ylo, yhi)

def _qsf_run_feat(ink, sl, run, cell_pt):
    """一条墨 run -> 单字形裁剪 -> (cls, 特征 dict, 说明串)。
    取样口径(v2 外部工具 6/9 失败的原因 —— 必须按字形裁, 不能按列/窗口裁):
      ① 在 run 的 y 带内认**本列**的 x 带(_qsf_col_xrun: 离槽中心最近的墨迹 x-run);
      ② 在该 x 带内重算 y 范围 -> 只含一个字形(邻列/上下字的墨都不进包围盒)。"""
    import numpy as np
    sc = 2.0
    H, _W = ink.shape
    bd = _qsf_col_xrun(ink, sl, run[0] - 1.0, run[1] + 1.0)
    if bd is None:
        return None, None, '槽中心 x 窗内无墨'
    ya = int(max(0, round((run[0] - 0.5) * sc)))
    yb = int(min(H, round((run[1] + 0.5) * sc)))
    sub = ink[ya:yb, bd[0]:bd[1]]
    ys = np.where(sub.any(axis=1))[0]
    if len(ys) < 2:
        return None, None, '墨迹不足'
    y0, y1 = ya + ys.min(), ya + ys.max() + 1
    crop = ink[y0:y1, bd[0]:bd[1]]
    f = _qsf_analyze(crop)
    if f is None:
        return None, None, '墨迹不足(%d px)' % int(crop.sum())
    # 单字形尺寸 sanity(不是判据阈值): 真引号/句号/「一」的较长边 >= 0.25 字格; 碎墨(实测
    #   p444 列 b 下方 2 步进处一条 2.5x4.5pt 噪点)不参与分类, 否则会被四角特征误判成 corner。
    if max(f['w'], f['h']) / sc < QSF_MIN_GLYPH * cell_pt:
        return 'other', f, '碎墨(%.1fx%.1fpt)' % (f['w'] / sc, f['h'] / sc)
    cls, desc = _qsf_classify(f, cell_pt, sc)
    return cls, f, desc

def _qsf_pick_tail(ink, sl, step):
    """列尾取样(与判据同源): 从下往上找第一条能给出形状结论(corner/ring/bar)的**小墨** run。
    为什么要遍历候选: 列尾下方可能有扫描噪点/断笔碎点(实测 p444 列 f 环下 2pt 处有一条 4pt 碎墨),
    它判成 other 就放弃会漏掉上面那条真引号/句号。最多看 4 条。
    返回 (runs, idx, cls, feat, desc, prev_cls) 或 None。"""
    runs = _qsf_tail_runs(ink, sl, step)
    if not runs:
        return None
    cands = []
    for j in range(len(runs) - 1, -1, -1):
        _h = runs[j][1] - runs[j][0]
        if QSF_MIN_RUN <= _h < 0.6 * step:          # 小墨 = 标点/引号(正文字高 ~0.9 步进)
            cands.append(j)
    if not cands:
        cands = [len(runs) - 1]
    last = None
    for j in cands[:4]:
        cls, feat, desc = _qsf_run_feat(ink, sl, runs[j], step)
        last = (j, cls, feat, desc)
        if cls in ('corner', 'ring', 'bar'):
            break
    j, cls, feat, desc = last
    prev_cls = None
    if j > 0:
        prev_cls, _pf, _pd = _qsf_run_feat(ink, sl, runs[j - 1], step)
    return runs, j, cls, feat, desc, prev_cls

def _qsf_plan(pi, sl, step, m, ch):
    """列尾闭引号判别 -> {'action','run','cls','prev','feat'} 或 None。只读源图, 不改任何状态。"""
    if not QSF_ON or not _NF['on'] or src_doc is None or sl is None or m is None:
        return None
    ink = _frame_ink(pi, m['g'])
    pick = _qsf_pick_tail(ink, sl, step)
    if pick is None:
        _qsf_stat['norun'] += 1
        return None
    runs, idx, cls, feat, desc, prev_cls = pick
    tail = runs[idx]
    _qsf_stat['cand'] += 1
    if cls in _qsf_stat:
        _qsf_stat[cls] += 1
    act = _qsf_decide(ch, cls, prev_cls)
    if QSF_DBG:
        print('    [QSF] p%d 列x%.1f-%.1f top%.1f bot%.1f step%.2f 末字%r 尾墨y%.1f-%.1f %s 前条=%s -> %s'
              % (pi + 1, sl['x0'], sl['x1'], sl.get('top') or 0.0, sl.get('bot') or 0.0, step,
                 ch, tail[0], tail[1], desc, prev_cls, act))
    if not act:
        return None
    _qsf_stat[act] += 1
    _qsf_log.append({'page': pi + 1, 'col_x': [round(sl['x0'], 1), round(sl['x1'], 1)],
                     'step': round(step, 2), 'char': ch, 'action': act, 'cls': cls, 'prev': prev_cls,
                     'run': [round(tail[0], 1), round(tail[1], 1)],
                     'w': round(feat['w'] / 2.0, 2), 'h': round(feat['h'] / 2.0, 2),
                     'desc': desc})
    return {'action': act, 'run': tail, 'cls': cls, 'prev': prev_cls, 'feat': feat}

def _qsf_audit(pi, sl, text, step, m):
    """诊断(只 QSF_DBG): 列出本列头 2 / 尾 3 条墨 run 的形状判定, 供 8 样本真值逐条对账。"""
    ink = _frame_ink(pi, m['g'])
    runs = _qsf_tail_runs(ink, sl, step)
    if not runs:
        return
    for i in sorted(set([0, 1, len(runs) - 3, len(runs) - 2, len(runs) - 1])):
        if not (0 <= i < len(runs)):
            continue
        cls, _f, desc = _qsf_run_feat(ink, sl, runs[i], step)
        print('[QSF-AUDIT] ' + json.dumps({
            'page': pi + 1, 'x0': round(sl['x0'], 1), 'x1': round(sl['x1'], 1),
            'top': round(sl.get('top') or 0.0, 1), 'bot': round(sl.get('bot') or 0.0, 1),
            'step': round(step, 2),
            'i': i, 'nrun': len(runs), 'run': [round(runs[i][0], 1), round(runs[i][1], 1)],
            'cls': cls, 'desc': desc, 'nchar': len(text), 'text': text[:16]},
            ensure_ascii=False))

# ---------- 2) 每页内容 ----------
def page_tex(k, drop_notes=False):
    """一页: 正文列(从右到左)逐列渲染, \\par 强制断列(列断点=源书)
    drop_notes: 边注已由 note_tex 绝对定位渲染, 从正文流里剔除(* 开头的题注列 is_body_col 会当正文收)"""
    notes = set(note_rows(k)) if drop_notes else set()
    rows = [r for r in all_rows[k] if is_body_col(*r) and r not in notes]
    rows.sort(key=lambda r: -r[0])   # x0 降序 = 右到左
    # 本页列距: 源书有些页是「註釋页」——字号与列距都只有正文的一半(实测 p156: 列距 43px=21.5pt,
    # 正文字步进 42px), 若仍按全局列距 47.6pt 排, 20 列 = 952pt 远超页宽 -> 溢页(全书跑 231->286 页)。
    # 判据: 本页正文列 x0 相邻差中位; 与全局列距差 >15% 时用本页值(数据驱动, 不硬编码页号)。
    pg_pitch = PITCH
    if len(rows) >= 4:
        xs = sorted(set(r[0] for r in rows), reverse=True)
        ds = [a - b for a, b in zip(xs, xs[1:]) if 15 < a - b < 200]
        if ds:
            p_med = statistics.median(ds) / 2.0
            if abs(p_med - PITCH) > 0.15 * PITCH: pg_pitch = round(p_med, 1)
    # 各列字号/占列数(供上面的列块总宽上限用): 字号 = 字步进/2(封顶 列距x0.92, 下限 20pt)。
    #   占列数: 列长(字数x字号) 超 	extwidth 时 tate 折列。实测折列阈值≈1.15x	extwidth:
    #   普通栏 25-28 字 x31-35pt = 850-907pt(<=1.05x) 不折(实测 p5 12 列逐列长度 843-868);
    #   而「字距宽 -> 字间插全角空格」的标题栏长度翻倍(实测 p194 两条 = 1.77/1.94x)必折。
    fmax = PITCH * 0.92                    # 字号上限: 字宽不得超列距(防侵占邻列)
    cols_t = []
    for x0, x1, y0, y1, t in rows:
        cw = max(1.0, x1-x0)               # 字宽 px
        step = (y1-y0)/max(1, len(t))      # 字步进 px
        if step > 1.3 * cw:                # 字距宽(如大标题): 字号≈步进/2(封顶), 字间1全角空格
            t = '　'.join(list(t))
        f = round(max(20.0, min(fmax, step/2.0)), 1)
        nc = 1 if len(t) * f <= 1.15 * TW_pt else int(len(t) * f / TW_pt) + 1
        cols_t.append((f, t, nc))
    # 列块总宽上限: 源书正文列都排在版框内 -> 列块总宽不得超过内框宽(实测「列数>12」的页照全局列距排
    #   会伸到页外)。总宽按「实际推进之和」算: tate 下每列推进 = max(列距, 该列字号)(字号大于列距时
    #   推进被字号撑开, 实测 p194 部分列 39pt 字号 + 2 条插入空格的标题栏折列 -> 实渲染 21 列,
    #   总宽 574pt > 内框 523pt, 越界 -12pt)。
    #   正常页(11-12 列, 字号<列距, 不折)退化为「列数 x 列距 <= 内框宽」, 与旧判据一致。
    if V_FRAME and len(rows) >= 4:
        g = frame_geom(keys.index(k))     # k = OCR key(字符串) -> 页序号
        if g:
            fw = g['in_r'] - g['in_l']
            for _ in range(4):
                wsum = sum(n * max(pg_pitch, f) for f, _t, n in cols_t)
                if wsum <= fw or pg_pitch <= 20.0: break
                pg_pitch = round(max(20.0, pg_pitch * fw / wsum), 1)
    segs = []
    for f, t, _nc in cols_t:
        t = t.replace('%', r'\%').replace('#', r'\#').replace('&', r'\&').replace('_', r'\_')
        segs.append('{\\fontsize{%spt}{%spt}\\selectfont %s\\par}' % (f, pg_pitch, t))
    return '\n'.join(segs)

_FAX = fax_pages()          # §1.995c 影印页判据(建排前跑一次: 判据只依赖源图墨迹 + OCR 字数)
_FAX_DONE = []              # 本次实际出图的影印页(1-based, 落盘/对账用)

sel = []
if PAGES_ENV:
    for part in PAGES_ENV.split(','):
        if '-' in part:
            a, b = part.split('-'); sel += list(range(int(a), int(b)+1))
        else:
            sel.append(int(part))
    sel = [s for s in sel if 1 <= s <= len(keys)]
else:
    sel = list(range(1, len(keys)+1))

w = page_w * 1.00375; h = page_h * 1.00375   # bp 换算
# ---------- 字体选择(taskL: 楷体候选试验) ----------
# 正文字体原本硬编码 Noto Serif CJK TC(宋/明体系)。taskL 要评估换楷体, 故抽出为 env 可覆盖:
#   VERT_FONT = mincho 字体文件(默认 NotoSerifCJK-Regular.ttc = 既有行为, 不设时逐字节不变)
#   VERT_GFONT = gothic 字体文件(默认 NotoSansCJK-Regular.ttc; 只被数学模式的 \mathgt 用到)
# 字体文件按**名**交给 pxchfon, 由 dvipdfmx 经 kpathsea 查找 —— 非 TeX 树内的字体(如 Windows
#   /mnt/c/Windows/Fonts/*.ttf)需设 OSFONTDIR 指向其目录(实测 kpsewhich 能解析)。
# 注意: VERT_METRICS(竖排括号墨心)/ INK_RATIO / NOTE_INK_RATIO / XSCALE 都是**按 Noto 标定**的
#   字体绑定常量, 换字体后这些不随之重测 -> 字形位置/覆盖率会有偏(见 docs/vert_kai_trial_report.md)。
FONT_MC = os.environ.get('VERT_FONT') or 'NotoSerifCJK-Regular.ttc'
FONT_GT = os.environ.get('VERT_GFONT') or 'NotoSansCJK-Regular.ttc'
preamble = r'''\documentclass[10pt,disablejfam]{tarticle}
\usepackage[unicode]{pxchfon}
\setminchofont[3]{%(FONT_MC)s}
\setgothicfont[3]{%(FONT_GT)s}
%% ---- upLaTeX 汉字编码补丁 (v2: 消除 JY1/JT1 报错) ----
%% 现象: tarticle.cls L617-621 硬编码 pTeX 汉字编码 JY1 (数学符号字体 mincho), tsize10.clo L27-28
%%       把 \kanjiencodingdefault 设为 JT1 -> upLaTeX 下两者都未定义, 每页刷
%%       "Encoding scheme `JY1' unknown" / "Unknown symbol font `mincho'" / "KANJI Encoding scheme `JT1' unknown"
%% 依据: upLaTeX 的汉字编码是 JY2/JT2(Unicode), 不是 pTeX 的 JY1/JT1(JIS) --
%%       jsclasses: \def\jsc@JYn{\if@jsc@uplatex JY2\else JY1\fi}; pxchfon L91 同规则。
%% 修法: disablejfam 跳过类里坏掉的 mincho 声明, 再按 jsclasses 的 upLaTeX 分支用 JY2 重建
%%       (等价还原数学模式汉字 \mathmc/\mathgt 能力); \kanjiencodingdefault 改 JY2 消除每页报错。
%%       剩余 1 处(JT1, 类加载期 tsize10.clo 内)无法在文档内拦截, 且 upLaTeX 下该命令本来就被忽略。
\makeatletter
\ifx\ucs\@undefined\else
  \def\kanjiencodingdefault{JY2}
  \DeclareSymbolFont{mincho}{JY2}{mc}{m}{n}
  \DeclareSymbolFontAlphabet{\mathmc}{mincho}
  \SetSymbolFont{mincho}{bold}{JY2}{gt}{m}{n}
  \jfam\symmincho
  \let\mathgt\@undefined
  \DeclareMathAlphabet{\mathgt}{JY2}{gt}{m}{n}
\fi
\makeatother
\usepackage{eso-pic}                 %% 书眉/页码绝对定位(逐字 \put 手工断列)
%% 字模横向压缩(taskJ-A)不用 graphicx 的 \\scalebox: 它的 btrans/etrans 逆矩阵舍入会残留 x1.0000041/字
%%   污染 CTM(见 §1.0a), 改用 \\special{pdf:literal direct q K 0 0 1 0 0 cm ... Q} 故无需 graphicx。
\setlength{\unitlength}{1pt}
\setlength{\parindent}{0pt}
\setlength{\textwidth}{%(TW)spt}
\setlength{\textheight}{%(TH)spt}
\setlength{\topmargin}{%(TM)spt}
\setlength{\oddsidemargin}{%(OM)spt}
\setlength{\evensidemargin}{%(OM)spt}
%% 关键: \paperheight/\paperwidth 设为真页尺寸 -> eso-pic FG 锚点落在页真左下(tate 下否则落在 A4 默认纸左角)
%% 不设则 \put 原点偏移 ~400pt(内容跑到页外); 实测(exp_pos5): 设后 rule(100,200) 落 y_botup≈204
\setlength{\paperheight}{%(PH0)spt}
\setlength{\paperwidth}{%(PW0)spt}
\special{papersize=%(PW)spt,%(PH)spt}
\pagestyle{empty}
\begin{document}
''' % {'TW': TW_pt, 'TH': TH_pt, 'TM': TM_pt, 'OM': OM_pt, 'PW': round(w,1), 'PH': round(h,1),
       'PW0': page_w, 'PH0': page_h, 'FONT_MC': FONT_MC, 'FONT_GT': FONT_GT}

# ---------- 1.956) 标定趟 B: 源图 + 探针渲染 -> 排版参数(taskM) ----------
# 背景(taskM 审计): 下列常数原是从 wz6 源图实测后**硬编码**的 —— 机制通用, 但数值是这本书的:
#   XSCALE 0.87 / PUNCT_SIZE 0.62 / PUNCT_DX 0.81 / PUNCT_DY 0.85 / GAP_HANG 0.85 /
#   BR_SIZE_DEF 0.66 / BR_SIZE{︗︘0.55, ︹︺0.49} / INK_RATIO 0.88 / INK_ASC 0.94 /
#   NOTE_INK_RATIO 0.88 / NOTE_INK_MAX 0.94(后 5 项是「字体绑定」而非「书绑定」)。
# 做法: 建排前标定一趟(结果打印 + 落盘, 可 VERT_CALIB_CACHE 复用), 显式 env 一律优先。
#
# 口径(两侧必须同源, 否则标定无意义):
#   源书侧 —— 2x(144dpi) 灰度 < 150 的墨迹; 逐「槽」用 §1.98 的墨迹 run + OCR 行配对(与渲染同一套几何),
#     逐字量 bbox 与像素面积(单位 px, 2x);
#   渲染侧 —— 用**本管线的真 preamble**(同字体/同 tarticle/同 pxchfon)编译 1-3 页探针, 每字隔离
#     \put, 同样 2x 灰度 < 150 量墨迹, 换算成 em。
#   为什么渲染侧要真编译而不只用 fontTools 的轮廓几何: 「字号 <-> 墨高」的换算必须落在**像素口径**上
#     (源书墨高来自扫描二值化, 渲染墨高同样来自二值化)。轮廓几何口径会系统性偏高: Noto Serif CJK TC
#     轮廓墨高 0.913em 对渲染实测 0.88em(-3.6%) —— 用轮廓值会让全书字号整体偏小(产物回退)。
#     fontTools 只用于**纯几何量**(VERT_METRICS 墨心 / PUNCT_INK 锚点偏移), 与探针结果交叉校验。
#
# 各参数口径(与 §1.0/§1.0a/§1.0c 的实现式一一对应):
#   XSCALE      = 源书正文单字「墨面积/墨高²」中位 ÷ 当前字体同口径中位
#                 (x 向压缩 K 使墨面积 ×K 而墨高不变 -> 面积/高² 比直接给出 K; wz6 应落 0.87±0.05)
#   PUNCT_SIZE  = 源书挤格标点墨高中位/正文墨高 × (渲染正文墨高em / 渲染标点墨高em)
#   PUNCT_DY    = 源书标点墨心相对前字格顶的偏移(以步进为单位)中位;  GAP_HANG 同源, 取墨顶
#   PUNCT_DX    = 源书标点墨心相对槽左缘的偏移(以格距为单位)中位
#   BR_SIZE     = 各类括号「墨高比/墨宽比」反推的字号比, 取「宽高同时最接近」的几何中值(sqrt(s_h×s_w)
#                 —— 与 taskK 当初 0.66 的定法同源; 只用墨高会得到 ~0.77, 见报告对账表)
#   INK_RATIO/INK_ASC/NOTE_INK_RATIO/NOTE_INK_MAX = 探针渲染的正文/注墨高与墨顶(像素口径)
#   VERT_METRICS/PUNCT_INK = fontTools 读 VERT_FONT 的字形轮廓(em 单位, 若字体不可解析则用兜底表)
CALIB_F_DEF = 40.0        # 探针字号(pt): 足够大以压低二值化边缘误差, 又不超页面格位
_CALIB_DBG2 = os.environ.get('VERT_CALIB_DEBUG') == '2'   # 逐槽 run/文本 明细(排障用)
_CALIB_DBG = [0]          # 调试打印配额(逐槽明细最多 8 条)
CALIB_F_MIN = 4           # 一类括号/标点少于此样本数 -> 回落到实测总中位(不硬猜)
CALIB_DEF = {'XSCALE': 0.87, 'PUNCT_SIZE': 0.62, 'PUNCT_DX': 0.81, 'PUNCT_DY': 0.85,
             'GAP_HANG': 0.85, 'BR_SIZE_DEF': 0.66, 'INK_RATIO': 0.88, 'INK_ASC': 0.94,
             'NOTE_INK_RATIO': 0.88, 'NOTE_INK_MAX': 0.94, 'PUNCT_CELL': 0.0}
# 对账表里**不用**「相对差」行打印的参数(兜底值为 0 / 非纯数值): PUNCT_CELL 兜底 0 -> 相对差无意义
CALIB_TXT = ('PUNCT_CELL',)
CALIB_DEF_BR = {'︗': 0.55, '︘': 0.55, '︹': 0.49, '︺': 0.49}    # BR_SIZE 兜底表(wz6 实测; 仅用于对账与兜底)
_CALIB_ENV = {'XSCALE': 'VERT_XSCALE', 'PUNCT_SIZE': 'VERT_PUNCT_SIZE', 'PUNCT_DX': 'VERT_PUNCT_DX',
              'PUNCT_DY': 'VERT_PUNCT_DY', 'GAP_HANG': 'VERT_GAP_HANG', 'BR_SIZE_DEF': 'VERT_BR_SIZE',
              'INK_RATIO': 'VERT_INK_RATIO', 'INK_ASC': 'VERT_INK_ASC', 'PUNCT_CELL': 'VERT_PUNCT_CELL',
              'NOTE_INK_RATIO': 'VERT_NOTE_INK_RATIO', 'NOTE_INK_MAX': 'VERT_NOTE_INK_MAX'}
# 括号族: 同一族的开/闭形是镜像(墨宽墨高一致, 实测 VERT_METRICS 可证) -> 合并取样(样本数翻倍)
BR_FAMILY = {'︵': 'paren', '︶': 'paren', '﹁': 'corner', '﹂': 'corner',
             '﹃': 'wcorner', '﹄': 'wcorner', '︗': 'black', '︘': 'black',
             '︹': 'lent', '︺': 'lent', '︽': 'dbl', '︾': 'dbl', '︿': 'ang', '﹀': 'ang'}
FAM_FORMS = {}            # family -> [竖排码位...](由 BR_FAMILY 生成, 供分档标定/回落取中位)
for _g, _f in sorted(BR_FAMILY.items()):
    FAM_FORMS.setdefault(_f, []).append(_g)
FAM_OF_FORM = dict(BR_FAMILY)          # 竖排码位 -> family(反查)
CALIB_RARE_PAGE = int(os.environ.get('VERT_CALIB_RARE_PAGES') or 8)   # 稀有括号定向补抽页数上限

def _calib_med(v):
    """中位(空列表 -> None)。"""
    return statistics.median(v) if v else None

def _calib_p75(v):
    """75 分位(空列表 -> None)。括号墨迹用 p75 而不是中位: 漏检/断裂只会把标记测**小**
    (弧被阈值切断成两段、淡墨段掉出阈值), 不会测大(上限另有 h<=0.62x中位、w<=0.9x中位 挡着),
    故高分位比中位更接近真值 —— 实测 （ 的样本双峰(0.24 与 0.13 各半), 中位落在两峰之间会偏小。"""
    if not v:
        return None
    s = sorted(v)
    return s[min(len(s) - 1, int(round(0.75 * (len(s) - 1))))]

def _calib_corpus(texts, n, lo=0x3400, hi=0x9FFF):
    """文本集合 -> 按字频取前 n 个目标区段字符(默认 CJK 汉字) —— 探针语料取本书实际用字。"""
    from collections import Counter
    c = Counter()
    for t in texts:
        for ch in t:
            if lo <= ord(ch) <= hi:
                c[ch] += 1
    return [ch for ch, _k in c.most_common(n)]

def _calib_xscale(src_body, probe, corpus):
    """XSCALE = 源书正文单字「墨面积/墨高²」中位 ÷ 当前字体渲染同口径中位。
    为什么用面积/高²而不是墨宽/墨高: x 向压缩 K 不改墨高、把墨面积乘 K, 故该比值就是 K;
    而墨宽/墨高比只反映字形宽窄(源书铅字比 Noto 窄 1.48 倍), 直接当 K 会把字压到 0.67
    -> 墨量比源书少 23%(用户抱怨的正是「密密麻麻」= 墨量偏多), 见报告 §3.1。
    **注意口径适用边界(taskO)**: a/h² 与二值化阈值强相关 —— 墨迹边缘的灰晕对面积的贡献远大于对
    高度的贡献(实测 wz6 110->170 阈值 a/h² +38%, 灰底扫描 wz7 +110%), 故换到软调/灰底扫描的书上
    该口径会系统性偏大(wz7 算出 1.85 = 把字拉宽到列距的 1.8 倍, 直接崩版)。这类书(NF)改用
    `_calib_xscale_w` 的「墨宽/墨高比」口径(同扫描 110->170 只变 ±5%)。样本不足 -> None。
    样本不足 -> None(调用方回落兜底值)。"""
    sa = _calib_med([a / h ** 2 for h, _w, a in src_body])
    ba = _calib_med([probe[c][4] / probe[c][1] ** 2 for c in corpus if c in probe])
    return round(sa / ba, 3) if (sa and ba) else None

def _calib_xscale_w(src_body, probe, corpus):
    """XSCALE(宽高比口径) = 源书正文单字「墨宽/墨高」中位 ÷ 渲染同字「墨宽/墨高」中位。
    只对**宽**、不对墨量: 源书铅字比 Noto 瘦(实测 wz6 0.65 / wz7 0.88 对 Noto ~1.0),
    故该口径把字压得更窄、墨量略少于源书(这是它已知的代价, 见 taskM 报告 §3.1);
    但它对二值化口径稳定(边缘灰晕同比放大墨宽与墨高 -> 比值不变), 换书/换扫描时不会翻车。
    无版框书(NF)用这条。"""
    sr = _calib_med([w / h for h, w, _a in src_body])
    br = _calib_med([probe[c][0] / probe[c][1] for c in corpus if c in probe])
    return round(sr / br, 3) if (sr and br) else None

def _calib_punct_size(src_small, probe, body_h_em):
    """PUNCT_SIZE = 源书「挤格标点墨高 ÷ 正文字高」中位 × (渲染正文墨高em ÷ 渲染标点墨高em)。
    两侧同口径(源书扫描像素 / 探针渲染像素), 故比值直接可比。"""
    pun = [s for s in src_small if s[1] == 'punct']
    ph = _calib_med([probe[c][1] for c in PUNCT_HANG if c in probe])
    rh = _calib_med([s[2] for s in pun])
    if not (pun and ph and body_h_em and rh):
        return None
    return round(rh * body_h_em / ph, 3)

def _calib_punct_pos(src_small):
    """(PUNCT_DY, PUNCT_DX, GAP_HANG) = 源书标点墨心/墨顶相对前字格顶与槽左缘的偏移中位。
    单位: 步进 / 格距 —— 与 col_puts 的 PUNCT_DY/DX、fit_gaps 的 hratio 同一坐标语义。"""
    pun = [s for s in src_small if s[1] == 'punct']
    if not pun:
        return None, None, None
    return (_calib_med([s[5] for s in pun]), _calib_med([s[6] for s in pun]),
            _calib_med([s[4] for s in pun if s[4] is not None]))

def _calib_punct_ink(probe, base):
    """探针实测墨心 -> PUNCT_INK(标点锚点偏移)覆盖表(taskT, 只 NF 用)。纯函数。
    返回 (新表, 覆盖个数, 覆盖项「轮廓 cy vs 渲染 cy」差的**中位**: em)。
    为什么需要: PUNCT_INK 原来只取 fontTools 的**水平字形轮廓**墨心, 而 tate 模式实际画出的字形
      在字盒里另有落位(竖排字体按自身 vertical 原点排版) —— 实测本册差 0.16em 量级
      (。: 轮廓 cy 0.380em vs 渲染实测 0.544em; ，0.404 vs 0.575), 折成 0.16em x 标点字号
      ≈ 5.9pt, 就是「标点贴前字、离后字远」的最后一段残差(PUNCT_DY 修好后仍余 -3.75pt)。
      探针与渲染同 preamble、同 \\put 口径(锚点 = 字盒左缘/基准线), 故实测值可直接用。
    base 里没有的字(探针未跑到)保持原值 —— 不混口径。"""
    out = dict(base)
    dif, n = [], 0
    for ch in sorted(base):
        if ch in probe:
            _w, _h, _cx, _cy, _a, _as = probe[ch]
            out[ch] = (round(_cx, 4), round(-_cy, 4))
            dif.append(abs(_cy + base[ch][1]))         # |渲染 cy - 轮廓 cy|
            n += 1
    return out, n, (statistics.median(dif) if dif else None)


def _calib_punct_cell(srec):
    """标点是否**独占一格**的标定(taskS, §1.956)-> 估计值中位 或 None。
    口径(逐列反推, 不必先知道哪个 run 是标点): 一列的墨迹跨度对应
        N 格 = (墨迹底 - 字 run 墨顶 - 字高) / 步进 + 1        (与 fit_gaps 的 exp 同式)
      该列文本在两种排印习惯下需要的格数: N0 = 字数 - 标点数(挤格) 或 N0 = 字数(占格);
      -> 估计 = (N - (字数 - 标点数)) / 标点数   (0 = 挤格, 1 = 占格)
    为什么取中位: 列里若有**排版空格**(源书标点后空一格/诗句间空), N 会偏大 -> 估计偏高;
      多数列没有空格, 中位对偏高值稳健(实测 wz7 样本 47 列: 中位 0.98, 四分之一分位 0.71)。
    只用「有 >= 6 条 run 且 >= 1 个标点」的列(样本太短时步进/格数估计不稳)。"""
    vals = []
    for n_ch, n_pu, step, T0, B, hbig in srec:
        if n_pu < 1 or n_ch < 6 or step <= 1.0 or hbig <= 1.0:
            continue
        n = (B - T0 - hbig) / step + 1.0
        vals.append((n - (n_ch - n_pu)) / n_pu)
    if len(vals) < 4:
        return None
    return _calib_med(vals)


def _calib_br_forms(forms, src_small, probe, body_h_em, body_w_em, xscale, dbg=False):
    """一类竖排括号(开/闭合并) -> dict(n, s_h, s_w, s, src_hh, src_ww, fh, fw); 无样本时 s=None。
    s_h = 源书墨高比 × 渲染正文墨高em / 渲染括号墨高em(只对高);
    s_w = 源书墨宽比 × 渲染正文墨高em / (渲染括号墨宽em × XSCALE)(对宽, 括号也走横向压缩);
    s   = sqrt(s_h × s_w) = 「宽高同时最接近」的缩放 —— 与 taskK 当初 0.66 的定法同口径
          (只对高会得到 ~0.77, 只对宽 ~0.65, 源书括号比 Noto 的更「高瘦」, 单一缩放无法全中)。"""
    Sall = [s for s in src_small if s[1] == 'brk' and VERT_FORMS.get(s[0]) in forms]
    # 位置质检: 括号墨心应落在本格内 (d_cy = (墨心-格顶)/步进 ∈ [0.05,0.95]); 更紧会误杀
    #   (实测源书 【】 的墨心在格上下缘 0.19/0.81 处, 并非一律居中)
    S = [s for s in Sall if 0.05 <= s[5] <= 0.95]
    P = [probe[f] for f in forms if f in probe]
    if dbg:
        _fams = sorted(set(FAM_OF_FORM.get(VERT_FORMS.get(f)) for f in forms))
        print('        [括号族 %-8s 样本明细] 质检前 %s | 质检后 %s' % (
            '/'.join(f for f in _fams if f),
            ['%s h%.3f w%.3f d_cy%.2f' % (s[0], s[2], s[3], s[5]) for s in Sall],
            ['%s h%.3f w%.3f d_cy%.2f' % (s[0], s[2], s[3], s[5]) for s in S]))
    R = {'n': len(Sall), 's_h': None, 's_w': None, 's': None, 'src_hh': None, 'src_ww': None,
         'fh': None, 'fw': None}
    if not S or not P or not body_h_em or not body_w_em:
        return R
    # 估计量: 样本足取 p75; 样本少(1..MIN-1)取最大值 —— 漏检只会把标记测小(弧被阈值切断/淡墨),
    #   不会测大(上限由 h<=0.62x中位 / w<=0.9x中位 挡着), 故小样本取上界更接近真值
    est = _calib_p75 if len(S) >= CALIB_F_MIN else max
    src_hh = est([s[2] for s in S])          # 已按本槽正文墨高中位归一
    src_ww = est([s[3] for s in S])
    fh = _calib_med([p[1] for p in P]); fw = _calib_med([p[0] for p in P])
    R.update({'src_hh': src_hh, 'src_ww': src_ww, 'fh': fh, 'fw': fw, 'n': len(S)})
    if not fh or not fw:
        return R
    s_h = src_hh * body_h_em / fh
    s_w = src_ww * body_h_em / (fw * xscale)
    R.update({'s_h': s_h, 's_w': s_w, 's': round((s_h * s_w) ** 0.5, 3)})
    return R

def _calib_font_path(name):
    """VERT_FONT 的字体名 -> 文件路径(kpsewhich, 与 dvipdfmx 同一查找链: TeX 树 + OSFONTDIR)。
    找不到返回 None(= 不改字体绑定常量, 全部回落兜底值并记日志)。"""
    if os.path.exists(name):
        return name
    try:
        r = subprocess.run(['kpsewhich', name], capture_output=True, text=True, timeout=30)
        p = (r.stdout or '').strip()
        return p if p and os.path.exists(p) else None
    except Exception:
        return None

def _calib_font_geom(path, chars, maxh_chars=None):
    """字体文件 -> ({字: (墨宽, 墨高, 墨心x, 墨心y, 墨面积)}, 说明, 满字墨高上限) (em, 轮廓口径)。
    .ttc 多面: 优先取名字含 'TC' 的面(与 preamble 的 \\setminchofont[3] 同面), 否则第 0 面。
    maxh_chars: 另给一个更大的字符集 -> 取其中墨高最大值作「满字墨高上限」(只算 bbox, 便宜)。
    解析失败(非 ttc/无 cmap/字体缺字)返回 (None, 原因, None)。"""
    from fontTools.ttLib import TTFont, TTCollection
    from fontTools.pens.areaPen import AreaPen
    from fontTools.pens.boundsPen import BoundsPen
    try:
        if path.lower().endswith('.ttc'):
            col = TTCollection(path)
            desc = []
            idx = 0
            for i, f in enumerate(col.fonts):
                nm = f['name'].getDebugName(4) or ''
                desc.append('#%d %s' % (i, nm))
                if 'TC' in nm:
                    idx = i
            font = col.fonts[idx]
        else:
            font = TTFont(path)
            desc = [os.path.basename(path)]
        upem = float(font['head'].unitsPerEm)
        gs = font.getGlyphSet(); cmap = font.getBestCmap()
        out = {}
        for ch in chars:
            gn = cmap.get(ord(ch))
            if gn is None:
                continue
            bp = BoundsPen(gs); gs[gn].draw(bp)
            if bp.bounds is None:
                continue
            ap = AreaPen(gs); gs[gn].draw(ap)
            x0, y0, x1, y1 = [v / upem for v in bp.bounds]
            out[ch] = (x1 - x0, y1 - y0, (x0 + x1) / 2.0, (y0 + y1) / 2.0, abs(ap.value) / upem ** 2)
        hmax = None
        for ch in (maxh_chars or ()):
            gn = cmap.get(ord(ch))
            if gn is None:
                continue
            bp = BoundsPen(gs); gs[gn].draw(bp)
            if bp.bounds is None:
                continue
            hmax = max(hmax or 0.0, (bp.bounds[3] - bp.bounds[1]) / upem)
        return out, ' + '.join(desc), hmax
    except Exception as e:
        return None, '%s: %s' % (type(e).__name__, e), None

def _calib_match_small(preds, marks, tol):
    """把「小字预测位置」与「实测小标记」单调配对(DP, 与渲染同一套坐标语义)。
    preds: [(kind, idx, ch, y_pred, ref)] —— ref='top'(挤格标点: 预测的是墨顶) / 'center'(括号: 墨心);
    marks: [(top, bot, cx, 墨宽, 墨高, kind)] pt(页顶向下), kind 由形态分类(扁长条=brk / 紧凑块=punct);
    tol:   容差(pt)。返回 [(idx, ch, kind, mark)]。
    只配同类(kind 一致); 代价 = |Δ|/tol(匹配) 与 1.0(跳过) -> 只在确实解释了墨迹位置时才配对, 宁缺勿错配。"""
    P, R = len(preds), len(marks)
    if not P or not R:
        return []
    def delta(i, j):
        k, _i2, _c, y, ref = preds[i]
        t, b, _cx, _w, _h, mk = marks[j]
        if k != mk:
            return None
        return abs(t - y) if ref == 'top' else abs((t + b) / 2.0 - y)
    INF = float('inf')
    dp = [[INF] * (R + 1) for _ in range(P + 1)]
    bt = [[None] * (R + 1) for _ in range(P + 1)]
    dp[0][0] = 0.0
    for i in range(P + 1):
        for j in range(R + 1):
            cur = dp[i][j]
            if cur == INF:
                continue
            if i < P and j < R:
                d = delta(i, j)
                if d is not None and d <= tol and cur + d / tol < dp[i + 1][j + 1]:
                    dp[i + 1][j + 1] = cur + d / tol; bt[i + 1][j + 1] = (i, j, 1)
            if i < P and cur + 1.0 < dp[i + 1][j]:
                dp[i + 1][j] = cur + 1.0; bt[i + 1][j] = (i, j, 0)
            if j < R and cur + 1.0 < dp[i][j + 1]:
                dp[i][j + 1] = cur + 1.0; bt[i][j + 1] = (i, j, 0)
    out = []
    i, j = P, R
    while i > 0 or j > 0:
        p = bt[i][j]
        if p is None:
            break
        pi_, pj_, took = p
        if took:
            k_, idx, ch, _y, _ref = preds[pi_]
            out.append((idx, ch, k_, marks[pj_]))
        i, j = pi_, pj_
    out.reverse()
    return out

def _calib_ink_box(ink, ta, tb, xa, xb):
    """run(y 区间 ta..tb pt) 在槽窗口 [xa,xb) px 内的墨迹 -> (墨宽 pt, 墨面积 pt²)。
    单位统一成 pt(2x px / 2): 面积与「墨高²」必须同单位, 否则 a/h² 会差 4 倍。"""
    import numpy as np
    ya, yb = int(ta * 2.0), int(tb * 2.0)
    if yb <= ya or xb <= xa:
        return 0.0, 0.0
    sub = ink[ya:yb, xa:xb]
    if not sub.any():
        return 0.0, 0.0
    xs = np.where(sub.any(axis=0))[0]
    return (xs[-1] - xs[0] + 1) / 2.0, float(sub.sum()) / 4.0

def _calib_own_marks(cc, t, cells, T0, step, x0, pitch, h_med, np_min=8):
    """**占格书**(PUNCT_CELL>=0.5)的标点样本: 逐标点取「本格中心」的连通域并集 ->
    [(ch, 'punct', 高比, 宽比, d_top, d_cy, d_cx)]。d_* 相对**前一字格顶**(= col_puts 的锚点,
    与 §1.956 的 PUNCT_DY/GAP_HANG/PUNCT_DX 同一坐标语义)。
    为什么不走 DP 配对(_calib_match_small): 那条路靠「预测位置」找标点, 而预测用的 GAP_HANG 本身
      正是待标定量 -> 占格书(标点离锚点 1.5 格)的真标点恰好踩在容差边缘(实测 |Δ|=15.6pt vs 容差
      15.9pt), DP 于是改选**前字笔画碎片**(代价 0.6 ≪ 15.6), 实测 wz7 p43「兩大類。」的量测值
      4.5pt vs 真值 10.0pt(源图墨迹直接探测) -> PUNCT_DY 中位被拉低约 0.35 格(全长 300 页 p43
      24 例: 0.969 vs 真值 1.45)。
    格内取墨为什么不需要预测: 行列栅格(T0/step)只由槽内墨迹 run 定, 与标点无关; 占格书里每个字的
      墨心都在**自己那一格**的中心附近, 标点墨心也在自己那格 -> 按「墨心落在哪一格」分类即可。
    不做尺寸窗筛选: ！：；？ 的墨高与正文相当(字体轮廓 0.62-0.78em), 尺寸窗会把整类滤掉; 并集若
      高过正文墨高(0.98x)判为「本格判据失效」(栅格漂移/两字并作一块) -> 弃样, 不乱收。"""
    out = []
    for i, ch in enumerate(t):
        c, hang = cells[i]
        if not hang:
            continue
        lo, hi = T0 + c * step, T0 + (c + 1) * step
        sel = [z for z in cc if lo <= (z[0] + z[1]) / 2.0 <= hi]
        if not sel:
            continue
        top = min(z[0] for z in sel); bot = max(z[1] for z in sel)
        xs0 = min(z[6] for z in sel); xs1 = max(z[7] for z in sel)
        if sum(z[8] for z in sel) < np_min:
            continue
        h = bot - top
        if h > 0.98 * h_med:                     # 高过正文墨高 -> 本格判据失效, 弃样
            continue
        cy = (top + bot) / 2.0
        cx = (xs0 + xs1) / 2.0
        w = xs1 - xs0
        a_top = T0 + (c - PUNCT_CELL) * step     # 锚点 = 前一字格顶(= col_puts 的 (k-1) 格)
        out.append((ch, 'punct', h / h_med, w / h_med,
                    (top - a_top) / step, (cy - a_top) / step, (cx - x0) / pitch))
    return out


def _calib_src_page(pi, k, marks=True):
    """源书一页的标定样本 -> dict 或 None(无版框/无正文槽)。
    复用 §1.98 的槽/行配对(与渲染同一套几何): 槽 runs + OCR 文本 + char_cells(格号) ->
      · body  = [(墨高px, 墨宽px, 墨面积px)]  逐字(只取「单体字」run: 高 ∈ 0.8-1.25 × 本槽中位;
                 并字(≈2x 高)与标点(≈0.3x)都被这条排除)
      · small = [(ch, kind, 高/正文高中位, 宽/正文高中位, d_top, d_cy, d_cx)] 挤格标点/括号
    d_*: 相对**前字格顶**(标点: 墨顶/墨心)与**槽左缘**(墨心)的偏移, 单位 = 步进/格距
      —— 与 col_puts 的 PUNCT_DX/DY、fit_gaps 的 GAP_HANG 一一对应(同一坐标语义)。
    所有比值都以**本槽正文墨高中位**为尺子 -> 逐页字号差异自动消掉。"""
    import numpy as np
    m = page_metrics(pi)
    if not m or not m['body']:
        return None
    rows = sorted(page_rows(k, m, pi)[0], key=lambda r: -r[0])
    slots = sorted(m['body'], key=lambda s: -s['x1'])
    pairs = _align_rows_slots(rows, slots)
    if not pairs:
        return None
    ink = _src_ink(pi)
    body, small, srec = [], [], []
    for ri, si in pairs:
        t = rows[ri][4]
        sl = slots[si]
        if not t or sl.get('runs') is None:
            continue
        # 窗口内缩 3.5pt 与 _slot_runs 同口径: 槽两侧就是界行线(宽 1-2pt), 不内缩会把整条线
        #   算进「字墨迹」-> 墨宽测成槽宽、面积虚高 30%+(标定值会系统性偏大)
        xa, xb = int((sl['x0'] + 3.5) * 2.0), int((sl['x1'] - 3.5) * 2.0)
        if xb - xa < 4:
            continue
        rs = [r for r in sl['runs'] if r[1] - r[0] >= 4.0]
        if len(rs) < 3:
            continue
        hs = sorted(r[1] - r[0] for r in rs)
        h_med = hs[len(hs) // 2]
        if h_med <= 1.0:
            continue
        step = sl.get('step') or 0.0
        if step <= 1.0:
            cs = sorted((a + b) / 2.0 for a, b in rs)
            ds = sorted(d for d in (cs[i + 1] - cs[i] for i in range(len(cs) - 1)) if d < 80)
            step = ds[len(ds) // 2] if ds else 0.0
        pitch = sl['x1'] - sl['x0']
        T0 = sl.get('top')
        if T0 is None:
            T0 = rs[0][0]
        Bv = sl.get('bot')
        if Bv is None:
            Bv = rs[-1][1]
        if _CALIB_DBG2 and _CALIB_DBG[0] < 8:
            _CALIB_DBG[0] += 1
            print('        [标定调试] p%d 槽 x%.1f-%.1f T0%.1f step%.2f h中位%.1f | runs(pt) %s'
                  % (pi + 1, sl['x0'], sl['x1'], T0, step, h_med,
                     ['%.1f-%.1f' % r for r in rs]))
            print('                  文本 %s | 格 %s' % (t[:30], [(c, h)
                  for c, h in char_cells(t)[:30]]))
        for (ta, tb) in rs:                                  # 逐字墨迹(高/宽/面积)
            h = tb - ta
            if not (0.80 * h_med <= h <= 1.25 * h_med):
                continue
            w, a = _calib_ink_box(ink, ta, tb, xa, xb)
            if a > 0:
                body.append((h, w, a))
        # 本槽的「格数反推」记录(供 PUNCT_CELL 标定, 见 _calib_punct_cell):
        #   (字数, 标点数, 步进, 首字墨顶, 本槽墨迹底, **字 run** 墨高中位)
        #   字 run = 高 >= 0.5 x 最大 run 高的那些 run(排掉标点碎片 —— 短列里标点能占 run 数一半,
        #   全 run 中位会把字高算小; 实测「又曰：」: 全中位 11.75pt vs 字 run 中位 19.25pt)
        _big = sorted(x for x in (r[1] - r[0] for r in rs) if x >= 0.5 * max(r[1] - r[0] for r in rs))
        if len(rs) >= 6:
            srec.append((len(t), sum(1 for c in t if c in PUNCT_HANG), step, T0, Bv,
                         _big[len(_big) // 2] if _big else h_med))
        if not marks:                             # 第一趟(只收槽格记录, 供 PUNCT_CELL 标定)
            continue
        if step <= 1.0:
            continue
        # 小字(挤格标点/括号): 用**二维连通域**而不是槽的 y 投影 —— 挤格标点的 y 区间常落在前一字
        #   的墨迹区间内(实测 p15「問：」: 标点墨迹 x552-554/y357-364 被 問 的 y 投影吞掉, 投影法
        #   只剩一条 run, 于是标点永远配不上, DP 会把下一个字的小笔画当成标点)。连通域才能分开。
        from scipy import ndimage
        zy0, zy1 = int(max(0, (T0 - 5.0) * 2)), int((Bv + 5.0) * 2)
        if zy1 - zy0 < 8:
            continue
        lab, _nn = ndimage.label(ink[zy0:zy1, xa:xb])
        marks, cc = [], []
        for kk, so in enumerate(ndimage.find_objects(lab), 1):
            if so is None:
                continue
            h_ = (so[0].stop - so[0].start) / 2.0
            w_ = (so[1].stop - so[1].start) / 2.0
            npx = int((lab[so] == kk).sum())
            if so[1].start <= 1 or so[1].stop >= xb - xa - 1:     # 贴窗口边 = 被裁的碎片
                continue
            top = (zy0 + so[0].start) / 2.0
            bot = (zy0 + so[0].stop) / 2.0
            cxx = (xa + so[1].start + xa + so[1].stop) / 4.0      # 墨心 x(pt)
            # 形态分类: 括号是「扁长条」(源书 ︵ ≈ 17.5x7pt, w/h≈2.5), 标点是紧凑小块(w/h<=1.8)
            cc.append((top, bot, cxx, w_, h_, 'punct', (xa + so[1].start) / 2.0,
                       (xa + so[1].stop) / 2.0, npx))
            if not (1.5 <= h_ <= 0.62 * h_med and 1.0 <= w_ <= 0.9 * h_med and npx >= 8):
                continue
            marks.append((top, bot, cxx, w_, h_, 'brk' if w_ >= 1.8 * h_ else 'punct'))
        cells = char_cells(t)
        if _punct_own():
            # 占格书(taskT): 标点独占一格 -> 用「格内中心」选墨, 不靠 DP 预测(见 _calib_own_marks);
            #   括号(kind='brk')仍走下面的 DP —— 它们的样本口径不变, 只是不再与标点抢匹配。
            small += _calib_own_marks(cc, t, cells, T0, step, sl['x0'], pitch, h_med)
        preds = []
        for i, ch in enumerate(t):
            c, hang = cells[i]
            # 标点的锚点格号 = 前一字格 (= 本格 - PUNCT_CELL; 与 fit_gaps.pred 同一语义),
            #   让 d_cy/d_top 的口径与 PUNCT_CELL 无关(标定趟本身要在 PUNCT_CELL 定下来之前跑)
            if _punct_own() and hang:
                continue          # 占格书: 标点样本由 _calib_own_marks 出, 这里只留括号(见该函数)
            if hang or ch in VERT_FORMS:
                ref = 'top' if hang else 'center'
                y = (T0 + (c - (PUNCT_CELL if hang else 0.0) + GAP_HANG) * step) if hang \
                    else (T0 + (c + 0.5) * step)
                preds.append(('punct' if hang else 'brk', i, ch, y, ref))
        for idx, ch, kind, mk in _calib_match_small(preds, marks, 0.5 * step):
            ta, _tb, cx, w_, h_, _k = mk
            c, _hang = cells[idx]
            cell_top = T0 + (c - (PUNCT_CELL if _hang else 0.0)) * step
            d_top = ((ta - cell_top) / step) if kind == 'punct' else None
            d_cy = ((ta + _tb) / 2.0 - cell_top) / step
            d_cx = (cx - sl['x0']) / pitch
            small.append((ch, kind, h_ / h_med, w_ / h_med, d_top, d_cy, d_cx))
    return {'page': pi + 1, 'body': body, 'small': small, 'slots': srec}

def _calib_probe(preamble, body_chars, note_chars, tmp, F=None,
                 page_w=None, page_h=None):
    """探针渲染: 用主文档的 preamble(同字体/同 tarticle)编译探针 PDF, 每字隔离 \\put, 2x 灰度<150
    量墨迹 -> {字: (墨宽em, 墨高em, 墨心x_em(相对字盒左缘), 墨心y_em(相对基线, 向上为正), 墨面积em²)}
    返回 (实测 dict, 说明) ; 失败返回 ({}, 原因)。"""
    import numpy as np
    import fitz
    F = F or CALIB_F_DEF
    page_w = page_w or 595.3
    page_h = page_h or 1244.1
    chars = [c for c in (list(body_chars) + list(note_chars)) if c.strip()]
    seen, cu = set(), []
    for c in chars:
        if c not in seen:
            seen.add(c); cu.append(c)
    if not cu:
        return {}, '无可测字符'
    cols = max(2, int(page_w // (2.8 * F)))
    rowsn = max(2, int((page_h - 2 * F) // (2.8 * F)))
    per = cols * rowsn
    dx, dy = page_w / cols, (page_h - 2 * F) / rowsn
    pages, layout = [], []
    for i in range(0, len(cu), per):
        chunk, puts = cu[i:i + per], []
        for j, ch in enumerate(chunk):
            r_, c_ = divmod(j, cols)
            x_pt = (c_ + 0.5) * dx - F / 2.0                 # 字盒左缘(格心 - 半字宽)
            y_base = 2 * F + (r_ + 0.5) * dy                 # 基准线(页顶向下 pt)
            puts.append(_put_tex(ch, x_pt, page_h - y_base, F, xs=1.0))
            layout.append((ch, x_pt, y_base))
        pages.append('\\AddToShipoutPictureFG*{%\n  ' + '%\n  '.join(puts) + '}\n\\null')
    pdir = os.path.join(tmp, 'calib_probe')
    os.makedirs(pdir, exist_ok=True)
    tex = preamble + '\n\\newpage\n'.join(pages) + '\n\\end{document}\n'
    open(os.path.join(pdir, 'probe.tex'), 'w', encoding='utf8').write(tex)
    r = subprocess.run(['uplatex', '-interaction=nonstopmode', 'probe.tex'],
                       cwd=pdir, capture_output=True, text=True)
    r2 = subprocess.run(['dvipdfmx', 'probe.dvi'], cwd=pdir, capture_output=True, text=True)
    ppdf = os.path.join(pdir, 'probe.pdf')
    if r2.returncode != 0 or not os.path.exists(ppdf):
        return {}, '探针编译失败(uplatex rc=%s dvipdfmx rc=%s)' % (r.returncode, r2.returncode)
    d = fitz.open(ppdf)
    S = 2.0                                                  # 与源书同一口径: 2x(144dpi) 灰度
    out = {}
    for i, (ch, x_pt, y_base) in enumerate(layout):
        pg = d[i // per]
        pix = pg.get_pixmap(matrix=fitz.Matrix(S, S), colorspace=fitz.csGRAY)
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
        x0 = int(max(0, (x_pt * PT2BP - 0.35 * F) * S)); x1 = int(min(a.shape[1], (x_pt * PT2BP + 1.35 * F) * S))
        y0 = int(max(0, (y_base * PT2BP - 1.15 * F) * S)); y1 = int(min(a.shape[0], (y_base * PT2BP + 0.35 * F) * S))
        sub = a[y0:y1, x0:x1] < 150
        if not sub.any():
            continue
        ys = np.where(sub.any(axis=1))[0]; xs = np.where(sub.any(axis=0))[0]
        # px -> pt: pt = px / (S x PT2BP); 墨迹坐标一律先回绝对页坐标(加裁剪窗原点 y0/x0)
        to_pt = 1.0 / (S * PT2BP)
        xt0 = (x0 + xs[0]) * to_pt; xt1 = (x0 + xs[-1] + 1) * to_pt
        yt0 = (y0 + ys[0]) * to_pt; yt1 = (y0 + ys[-1] + 1) * to_pt
        w = xt1 - xt0
        h = yt1 - yt0
        cx = ((xt0 + xt1) / 2.0 - x_pt) / F            # 墨心 x 相对字盒左缘(em)
        cy = (y_base - (yt0 + yt1) / 2.0) / F           # 墨心 y 相对基准线, 向上为正(em)
        asc = (y_base - yt0) / F                        # 墨迹顶距基准线(em)
        out[ch] = (w / F, h / F, cx, cy, float(sub.sum()) / (S * PT2BP * F) ** 2, asc)
    d.close()
    return out, '%d 字 / %d 页 (F=%.0fpt, %s)' % (len(out), len(pages), F, os.path.basename(ppdf))

def _calib_apply(name, val):
    """标定值 -> 模块全局(显式 env 优先)。返回 (生效值, 来源标签)。"""
    e = os.environ.get(_CALIB_ENV[name])
    if e not in (None, ''):                 # 定义处已取 env; 这里只标注来源
        return globals()[name], 'env'
    if val is None:
        return CALIB_DEF[name], '兜底'
    globals()[name] = val
    return val, '标定'

_calib_vals, _calib_src = {}, {}
_calib_font_desc = ''
_brdef = []

# (a) 字体文件 + fontTools 纯几何量(VERT_METRICS / PUNCT_INK): 换字体自动重标, 无需真渲染
_ffile = _calib_font_path(FONT_MC)
_FONT_PATH = _ffile          # §1.995: 西文行的字体几何(fontTools)与渲染用的是同一字体文件
_gchars = sorted(set(VERT_FORMS.values())) + sorted(PUNCT_INK)
_fg = None          # 字体几何缓存; 找不到字体文件时保持 None(下游 (c) 括号族对账要用)
_book_chars = sorted(set(ch for kk in keys for r in all_rows[kk] for ch in r[4]
                         if 0x3400 <= ord(ch) <= 0x9FFF))
if _ffile:
    _fg, _fdesc, _fhmax = _calib_font_geom(_ffile, _gchars, maxh_chars=_book_chars)
    _calib_font_desc = '%s -> %s' % (FONT_MC, _fdesc)
    if _fhmax:
        # 满字墨高上限: 取**轮廓口径**下本书全部用字的最大墨高(保守: 轮廓 <= 像素口径实测约 6%,
        #   口径偏松会让「字号保护」失效) -> 用轮廓值; 像素口径的结果在日志里对照。
        _calib_vals['NOTE_INK_MAX'] = round(_fhmax, 3)
    if _fg:
        _vm = {}
        for _ch in sorted(set(VERT_FORMS.values())):
            if _ch in _fg:
                _w, _h, _cx, _cy, _a = _fg[_ch]
                _vm[_ch] = (round(_w, 3), round(_h, 3), round(_cx, 3), round(_cy, 3))
        if len(_vm) == len(VERT_METRICS):
            VERT_METRICS = _vm
        _pi = {}
        for _ch in sorted(PUNCT_INK):
            if _ch in _fg:
                _w, _h, _cx, _cy, _a = _fg[_ch]
                _pi[_ch] = (round(_cx, 4), round(-_cy, 4))    # 锚点偏移: 墨心相对字盒左缘/基准线
        if len(_pi) == len(PUNCT_INK):
            PUNCT_INK = _pi
        print('[标定B] 字体几何: %s; %d 个竖排括号形态 + %d 个标点已按 fontTools 重算'
              % (_calib_font_desc, len(_vm), len(_pi)))
    else:
        print('[标定B] 字体几何: %s 解析失败(%s) -> VERT_METRICS/PUNCT_INK 用兜底表' % (FONT_MC, _fdesc))
else:
    print('[标定B] 字体几何: 找不到字体文件 %s(kpsewhich 未命中) -> VERT_METRICS/PUNCT_INK 用兜底表' % FONT_MC)

# (b) 源图侧统计(只有给了源 PDF 才有)
_src_body, _src_small, _src_pages, _src_slots = [], [], 0, []
def _calib_fam_count(samples):
    """各括号族的样本数(分母 = 源图侧小字样本)。"""
    c = {}
    for s in samples:
        if s[1] == 'brk':
            f = FAM_OF_FORM.get(VERT_FORMS.get(s[0]))
            if f:
                c[f] = c.get(f, 0) + 1
    return c
if SRC and os.environ.get('VERT_CALIB_CACHE') in (None, ''):
    # (b0) 第一趟: **只收槽格记录**(不跑连通域配对) —— PUNCT_CELL 的唯一输入。
    #   为什么必须先定 PUNCT_CELL 再采样本(taskT): 占格书里标点独占一格, 而标定趟起初不知道
    #   PUNCT_CELL(兜底 0 = 挤格) -> 小字配对的预测锚点偏一格, 真标点踩在容差边缘, DP 改选前字
    #   笔画碎片 -> PUNCT_DY/GAP_HANG/PUNCT_SIZE 全被带偏(实测 wz7: d_cy 中位 0.969 vs 真值 1.45,
    #   即标点被摆在离前字太近的位置 -> 用户多轮反馈「标点跟字体重合」)。槽格记录只由墨迹 run 定,
    #   与标点无关, 故可先算。(_calib_src_page 内部按 marks=False 提前返回, page_metrics 有缓存。)
    for _pg in CALIB_SAMP:
        _r = _calib_src_page(_pg - 1, keys[_pg - 1], marks=False)
        if _r:
            _src_slots += _r.get('slots') or []
    if _src_slots:
        _pc_est = _calib_punct_cell(_src_slots)
        if _pc_est is not None:
            _calib_vals['PUNCT_CELL'] = 1.0 if _pc_est >= PUNCT_CELL_THR else 0.0
            PUNCT_CELL = _calib_vals['PUNCT_CELL']        # 第二趟采样前生效(见 §1.0 n_cells 注)
            print('[标定B] 标点占格: 源图侧 %d 槽记录 -> 估计中位 %.3f(阈值 %.1f) -> PUNCT_CELL=%.0f (%s)'
                  % (len(_src_slots), _pc_est, PUNCT_CELL_THR, PUNCT_CELL,
                     '标点独占一格' if PUNCT_CELL else '挤格(与前字同格, wz6 口径)'))
    for _pg in CALIB_SAMP:
        _r = _calib_src_page(_pg - 1, keys[_pg - 1])
        if not _r:
            continue
        _src_pages += 1
        _src_body += _r['body']
        _src_small += _r['small']
        _src_slots += _r.get('slots') or []
    print('[标定B] 源图侧: 抽样 %d 页 -> 可用 %d 页; 单体字样本 %d 个, 小字(标点/括号)样本 %d 个'
          % (len(CALIB_SAMP), _src_pages, len(_src_body), len(_src_small)))
    # 稀有括号(【】〔〕等, 全书可能只出现在少数页)在均布抽样里凑不够样本 -> **定向补抽**:
    #   从 OCR 文本找出含该类括号的页, 再抽最多 CALIB_RARE_PAGE 页。这是「换书也能自动标定」的关键:
    #   别的书的稀有括号出现页更少, 均布抽样必然漏。
    _fc = _calib_fam_count(_src_small)
    _need = set(f for f in FAM_FORMS if _fc.get(f, 0) < CALIB_F_MIN)
    if _need and _src_pages:
        # 按「缺得最多」的族优先; 每族取各自的候选页(不能只按页序取前 N 页: 实测 wz6 的
        #   『』 页排在前面, 会把预算吃光, 【】〔〕 一页也抽不到)
        # 排序键带上族名做**确定性** tie-break: set 的迭代序随 PYTHONHASHSEED 变, 只按样本数排
        #   会让两次构建抽到不同的补抽页 -> 产物不可复现(实测 p192 字号 22.4/22.2 两版)
        _order = sorted(_need, key=lambda f: (_calib_fam_count(_src_small).get(f, 0), f))
        _budget, _got = CALIB_RARE_PAGE, 0
        _used_pg = set(CALIB_SAMP)
        for _fam in _order:
            if _budget <= 0:
                break
            _hx = set(h for h, v in VERT_FORMS.items() if FAM_OF_FORM.get(v) == _fam)
            _cand = []
            for _p2 in range(1, len(keys) + 1):
                if _p2 in _used_pg:
                    continue
                _txt = ''.join(r[4] for r in all_rows[keys[_p2 - 1]])
                if any(ch in _hx for ch in _txt):
                    _cand.append(_p2)
            for _pg in _cand[:max(2, _budget // max(1, len(_order)))]:
                _r = _calib_src_page(_pg - 1, keys[_pg - 1])
                _budget -= 1
                _used_pg.add(_pg)
                if not _r:
                    if os.environ.get('VERT_CALIB_DEBUG'):
                        print('        [补抽] p%d(%s) 无可用槽(无版框/无正文槽) -> 跳过' % (_pg, _fam))
                    continue
                _src_pages += 1
                # 只收小字样本, **不收 body**: 补抽页是为稀有括号挑的(註釋页/索引页等), 不代表全书
                #   正文用字的分布 -> 混进去会把 XSCALE(全书中位)带偏(实测 0.868 -> 0.927)
                _src_small += _r['small']
                _got += 1
                if os.environ.get('VERT_CALIB_DEBUG'):
                    print('        [补抽] p%d(%s) 小字样本 %d: %s' % (
                        _pg, _fam, len(_r['small']), [s[0] for s in _r['small']]))
                if _calib_fam_count(_src_small).get(_fam, 0) >= CALIB_F_MIN:
                    break
        print('[标定B] 稀有括号定向补抽 %d 页(缺样本的族: %s) -> 各族样本 %s'
              % (_got, ','.join(_order), _calib_fam_count(_src_small)))

# (b2) 标点是否**独占一格**(taskS): 逐槽从源图墨迹反推(见 _calib_punct_cell)。
#   为什么单独一步: 它决定「格」的口径(n_cells/char_cells/fit_gaps/col_puts 全用它), 而 wz6 的
#   挤格口径与 wz7 的占格口径在源图上都自洽 —— 只能按本书实测二选一, 不能沿用上一本的常数。
#   taskT 起**提前到采样之前**(见 (b0)): 占格与否决定小字样本怎么取, 不能等采完样再算。

# (c) 探针渲染(源图侧不可用时不跑: 标定值都算不出来, 白白编译一趟)
_probe = {}
_pdesc = '未跑'
if _src_body:
    _body_c = _calib_corpus([r[4] for kk in keys for r in all_rows[kk] if is_body_col(*r)], 24)
    _note_c = _calib_corpus([r[4] for kk in (keys[p - 1] for p in CALIB_SAMP) for r in note_rows(kk)], 12)
    _probe, _pdesc = _calib_probe(preamble, _body_c + sorted(PUNCT_HANG) + sorted(set(VERT_FORMS.values())),
                                  _note_c, TMP, page_w=page_w, page_h=page_h)
    print('[标定B] 探针渲染: %s' % _pdesc)
    # (c2) PUNCT_INK(标点锚点偏移)口径 —— **只 NF 改用探针渲染实测墨心**(taskT)。
    #   为什么: fontTools 读的是**水平字形的轮廓几何**, 而 tate 模式实际画出的字在字盒里另有落位
    #   (竖排字体按自身 vertical 原点排版), 两者墨心差 0.16em(实测本册 。: 轮廓 cy 0.380em vs
    #   渲染实测 0.544em; ，0.404 vs 0.575) —— 差 0.16em x Fp ≈ 5.9pt, 正是「标点贴前字」的最后
    #   一段残差(修 PUNCT_DY 之后仍余 -3.75pt, 见报告 §4)。
    #   探针的口径与 _put_tex 的调用方完全同源(同一 preamble、同一 \put 点=字盒左缘/基准线)。
    #   wz6(有版框书)保持 fontTools 口径不动 —— 逐字节不变。
    if _NF['on'] and _probe:
        PUNCT_INK, _pik_n, _pik_d = _calib_punct_ink(_probe, PUNCT_INK)
        if _pik_n:
            print('[标定B] PUNCT_INK 口径: NF -> 探针渲染实测墨心 %d 个标点(轮廓 vs 渲染 中位差 %.3fem)'
                  % (_pik_n, _pik_d or 0.0))

# (d) 组合出各参数(每一项都写清口径; 样本不足 -> None -> 兜底值)
if _src_body and _probe:
    _bh = _calib_med([_probe[c][1] for c in _body_c if c in _probe])
    _bw = _calib_med([_probe[c][0] for c in _body_c if c in _probe])
    _ba = _calib_med([_probe[c][4] / _probe[c][1] ** 2 for c in _body_c if c in _probe])
    _nh = _calib_med([_probe[c][1] for c in _note_c if c in _probe]) or _bh
    _nmax = max([_probe[c][1] for c in (_body_c + _note_c) if c in _probe] or [0]) or None
    _asc = _calib_med([_probe[c][5] for c in _body_c if c in _probe])
    # XSCALE: 有版框书(wz6 口径, 已验收)用面积口径; 无版框书(NF)改用宽高比口径(见 _calib_xscale_w)
    _xs_a = _calib_xscale(_src_body, _probe, _body_c)
    _xs_w = _calib_xscale_w(_src_body, _probe, _body_c)
    _calib_vals['XSCALE'] = (_xs_w if _NF['on'] else _xs_a) or None
    if _xs_a and _xs_w:
        print('[标定B] XSCALE 口径: 面积/高² %.3f | 宽/高比 %.3f -> 采用%s' % (
            _xs_a, _xs_w, '宽高比(NF: 无版框书, 面积口径随二值化阈值漂移大)' if _NF['on'] else '面积/高²'))
    # 标点(字号 + 摆位三项同源)
    _ps = _calib_punct_size(_src_small, _probe, _bh)
    _py, _px, _pg = _calib_punct_pos(_src_small)
    if _ps:
        _calib_vals['PUNCT_SIZE'] = _ps
    if _py is not None:
        _calib_vals['PUNCT_DY'] = round(_py, 3)
    if _px is not None:
        _calib_vals['PUNCT_DX'] = round(_px, 3)
    if _pg is not None:
        _calib_vals['GAP_HANG'] = round(_pg, 3)
    # 括号: 按族(开/闭合并)分档; 无样本的族 -> 总中位 BR_SIZE_DEF(可 VERT_BR_SIZE_MAP 覆盖)
    _xs = _calib_vals.get('XSCALE') or CALIB_DEF['XSCALE']
    _brv, _brdef = {}, []
    for _fam, _forms in sorted(FAM_FORMS.items()):
        _R = _calib_br_forms(_forms, _src_small, _probe, _bh, _bw, _xs,
                             dbg=bool(os.environ.get('VERT_CALIB_DEBUG')))
        if _R['s'] is None:
            print('        [括号族 %-8s] 无可用样本(%d 原始样本) -> 该族用总中位 BR_SIZE_DEF'
                  '(可用 VERT_BR_SIZE_MAP 人工覆盖)' % (_fam, _R['n']))
            continue
        for _f2 in _forms:
            _brv[_f2] = _R['s']
        _brdef.append(_R['s'])
        _oh = _calib_med([_fg[f][1] for f in _forms if _fg and f in _fg]) if _fg else None
        _ocmp = ''
        if _oh:
            # 对照: taskK 当初的 0.66 是「源书像素口径 x 渲染**轮廓**口径」的混合口径定法, 这里给出
            #   同口径的 s_h 便于对账(轮廓口径的墨高比像素口径大 ~6%, 故该值系统性更小)
            _ocmp = ' | 轮廓口径 墨高%.3fem -> s_h %.3f' % (_oh, _R['src_hh'] * _bh / _oh)
        print('        [括号族 %-8s] %d 样本 源高比%.3f 源宽比%.3f | 渲染墨高%.3fem 墨宽%.3fem'
              ' -> s_h %.3f s_w %.3f 折中 %.3f%s'
              % (_fam, _R['n'], _R['src_hh'], _R['src_ww'], _R['fh'], _R['fw'],
                 _R['s_h'], _R['s_w'], _R['s'], _ocmp))
    if _brdef:
        BR_SIZE = _brv
        _calib_vals['BR_SIZE_DEF'] = round(statistics.median(_brdef), 3)
    # 字体绑定组(像素口径)
    if _bh:
        _calib_vals['INK_RATIO'] = round(_bh, 3)
    if _asc:
        _calib_vals['INK_ASC'] = round(_asc, 3)
    if _nh:
        _calib_vals['NOTE_INK_RATIO'] = round(_nh, 3)
    if _nmax:
        # 满字墨高上限优先用 fontTools 轮廓口径(见 (a)); 这里只在与像素口径差异大时提示
        if 'NOTE_INK_MAX' not in _calib_vals:
            _calib_vals['NOTE_INK_MAX'] = round(_nmax, 3)
        elif abs(_calib_vals['NOTE_INK_MAX'] - _nmax) > 0.03:
            print('        [对照] 满字墨高上限: 轮廓 %.3f vs 像素口径 %.3f (口径差, 取轮廓=保守)'
                  % (_calib_vals['NOTE_INK_MAX'], _nmax))

if os.environ.get('VERT_CALIB_DEBUG'):
    print('[标定B][调试] 探针逐字(em; cx/cy 相对字盒左缘/基准线, asc = 墨顶距基准线):')
    for _c in sorted(_probe):
        _w, _h, _cx, _cy, _a, _as = _probe[_c]
        print('        %s w%.3f h%.3f cx%+.3f cy%+.3f a%.4f asc%.3f  (a/h²=%.4f)'
              % (_c, _w, _h, _cx, _cy, _a, _as, _a / _h ** 2))
    print('[标定B][调试] 源图小字样本(ch, kind, 高比, 宽比, d_top, d_cy, d_cx):')
    for _s in _src_small:
        print('        %s' % (_s,))
    _sb = sorted(a / h ** 2 for h, _w, a in _src_body)
    print('[标定B][调试] 源图单体字 a/h²: n=%d 中位 %.4f p10 %.4f p90 %.4f | 墨高中位 %.1fpx'
          % (len(_sb), _calib_med(_sb), _sb[len(_sb) // 10], _sb[int(0.9 * len(_sb))],
             _calib_med([h for h, _w, _a in _src_body])))

# (e) 缓存复用(显式指定时): 直接读回 values, 跳过 (b)-(d)
_cr = os.environ.get('VERT_CALIB_CACHE')
if _cr:
    try:
        _cj = json.load(open(_cr, encoding='utf8'))
        _calib_vals = dict(_cj.get('values') or {})
        if _cj.get('br_size'):
            BR_SIZE = dict(_cj['br_size'])
        print('[标定B] 缓存复用: %s (%d 项)' % (_cr, len(_calib_vals)))
    except Exception as e:
        print('[标定B] 缓存读取失败(%s) -> 重新标定' % e)

# (f) 生效值 + 对账表 + 落盘
# 先清缓存: §1.98 的 page_metrics 逐页缓存里存着「用**标定前** INK_RATIO/NOTE_INK_RATIO 算出的字号」,
#   而标定趟抽样时会先把这些页算进缓存 -> 不清掉的话, 被抽样的页会用旧字号渲染(实测 p192 22.2 vs 22.4)
_metrics_cache.clear()
for _n in sorted(CALIB_DEF):
    _v = _calib_vals.get(_n)
    _e, _s = _calib_apply(_n, _v)
    _calib_src[_n] = _s
print('[标定B] 对账表(标定值/兜底值/生效值; 相对差 = (标定-兜底)/兜底):')
print('    %-14s %8s %8s %8s %-5s %8s' % ('参数', '兜底值', '标定值', '生效值', '来源', '相对差'))
for _n in sorted(CALIB_DEF):
    if _n in CALIB_TXT:            # 兜底值为 0 / 非纯数值的参数: 下面单列(相对差无意义)
        _v = _calib_vals.get(_n)
        print('    %-14s 兜底 %.3f 标定 %s 生效 %.3f %s' % (
            _n, CALIB_DEF[_n], ('%.3f' % _v) if _v is not None else '-', globals()[_n], _calib_src[_n]))
        continue
    _d = CALIB_DEF[_n]; _v = _calib_vals.get(_n)
    print('    %-14s %8.3f %8s %8.3f %-5s %8s' % (
        _n, _d, ('%.3f' % _v) if _v is not None else '-', globals()[_n], _calib_src[_n],
        ('%+.1f%%' % ((_v - _d) / _d * 100)) if _v else '-'))
print('    %-14s 兜底 %s -> 生效 %s (按族标定 %d 族; 样本 < %d 的族回落总中位)'
      % ('BR_SIZE', CALIB_DEF_BR, BR_SIZE, len(FAM_FORMS), CALIB_F_MIN))
print('    %-14s 兜底 %d -> 生效 %d' % ('N_COL_FRAME', 12, N_COL_FRAME))
_cout = os.environ.get('VERT_CALIB_REPORT') or os.path.join(TMP, 'vert_calib.json')
if os.environ.get('VERT_CALIB_CACHE') in (None, ''):
    json.dump({'src_pdf': SRC, 'pages_sampled': len(CALIB_SAMP), 'pages_used': _src_pages,
               'font': FONT_MC, 'font_resolved': _ffile, 'probe': _pdesc,
               'n_col_frame': N_COL_FRAME, 'br_size': BR_SIZE,
               'values': _calib_vals, 'fallback': CALIB_DEF,
               'effective': dict((n, globals()[n]) for n in CALIB_DEF)},
              open(_cout, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print('[标定B] 落盘 %s' % _cout)
print('[标定] 标定趟耗时 %.1fs(源图侧 %d 页 + 探针 %s)' % (
    __import__('time').time() - CALIB_T0, _src_pages, _pdesc))
if os.environ.get('VERT_CALIB_ONLY') not in (None, '', '0'):
    print('[标定B] VERT_CALIB_ONLY=1 -> 只标定不建排, 退出')
    sys.exit(0)

parts = [preamble]
n_frame_pg = 0
for i, pg in enumerate(sel):
    k = keys[pg-1]
    # §1.995c 影印页: 整页贴源图, **不重建**(用户明确要求)。纸型按本页源页尺寸逐页设(同 §1.975 逐页纸型),
    #   图按本页纸幅铺满; 不加书眉/页码/版框/正文(整页就是那张影印件)。
    if NF_MODE and src_doc is not None and (pg - 1) in _FAX:
        _pw, _ph = _nf_page_px(pg - 1)
        page_w, page_h = _pw / PT_PER_PX, _ph / PT_PER_PX
        parts.append('\\setlength{\\paperheight}{%.1fpt}\\setlength{\\paperwidth}{%.1fpt}\n'
                     '\\special{papersize=%.1fpt,%.1fpt}' % (
                         page_h, page_w, round(page_w * 1.00375, 1), round(page_h * 1.00375, 1)))
        parts.append(fax_tex(pg - 1))
        parts.append('\\null')
        _FAX_DONE.append(pg)
        if pg != sel[-1]:
            parts.append('\\newpage')
        continue
    # §1.975 无版框书: **逐页纸型** —— 同一册里可夹多种开本(实测 wz7 有 922x1437 / 892x1323 /
    #   705x1084 三种)。\put 坐标以「页真左下角」为原点, 故页幅一改, 本页所有绝对定位随之对齐;
    #   \special{papersize} 逐页改媒体框(dvipdfmx 支持文档中途改, 实测 2 页不同纸型输出正确)。
    if NF_MODE and src_doc is not None:
        _pw, _ph = _nf_page_px(pg - 1)
        if (_pw, _ph) != (PW_PX, PH_PX):
            page_w, page_h = _pw / PT_PER_PX, _ph / PT_PER_PX
            parts.append('\\setlength{\\paperheight}{%.1fpt}\\setlength{\\paperwidth}{%.1fpt}\n'
                         '\\special{papersize=%.1fpt,%.1fpt}' % (
                             page_h, page_w, round(page_w * 1.00375, 1), round(page_h * 1.00375, 1)))
            print('  [逐页纸型] p%d %.1f x %.1f pt (基准 %.1f x %.1f pt)' % (
                pg, page_w, page_h, PW_PX / 2.0, PH_PX / 2.0))
    # taskP2: **逐页右缘** —— v2 流式回退页(封面/扉页/不适配页)按全局拟合右缘 RIGHT_p 放最右列
    #   (右缘 = 70 + om + textheight), 该值已夹到**基准**纸宽(§1.975 后), 但小开本页(实测 705pt)
    #   仍会越出本页纸 214pt(实测源页 214: 40 条 span x 887-919)。故按**本页纸宽**再夹一次。
    if NF_MODE and src_doc is not None and page_w < PW_PX / 2.0 - 0.5:
        _rp2 = min(RIGHT_p, page_w - 1.0)
        _om2 = round(_rp2 - TH_pt - 70, 1)
        parts.append('\\setlength{\\oddsidemargin}{%.1fpt}\\setlength{\\evensidemargin}{%.1fpt}'
                     % (_om2, _om2))
    _sp_puts = []                                   # §1.995 本页特殊行 \put(每页重置)
    dr = derot_rows(k, pg - 1, all_rows[k])      # §1.97: OCR 旋转坐标系页还原(只影响本页)
    if dr is not None: all_rows[k] = dr
    parts.append('%% ===== 源第 %d 页 (key %s) =====' % (pg, k))
    # §1.98 框驱动路径: 有版框的页用「逐页版框实测」排版(逐字 \put 绝对定位, 不占版心流);
    #   无版框页(封面/p1-p2/末页)保持 v2 的 OCR 拟合流式排版
    # §1.975b 横排页兜底(taskP): 无版框书里的**横排页**(现代附錄字表/版權頁/說明頁)—— 它们的行盒
    #   是「宽扁」横排行, 竖排管线(伪槽格/兜底/流式)对它们全部错版(实测版權頁 15 条 span 出页 217pt、
    #   字表页 0 字、說明頁被当成 15 列竖排)。这类页直接按源书行盒逐行**横排**重建。
    if NF_MODE and src_doc is not None and _nf_hrow_page(k, pg - 1):
        hp, _nhl, _nch = _nf_hrow_puts(k, pg - 1)
        if hp:
            parts.append('\\AddToShipoutPictureFG*{%\n  ' + '%\n  '.join(hp) + '}')
            parts.append('\\null')
            if SPECIAL:
                parts += special_tex(k, pg - 1)             # 页码/书眉仍按源墨迹定位(可能与本页横排共存)
            if pg != sel[-1]:
                parts.append('\\newpage')
            continue
    pm = page_metrics(pg - 1) if (V_FRAME and V_FRAME_LAYOUT and src_doc is not None) else None
    # taskCD-c: 伪版心外的扫描水印/馆藏标签**整行剔除**(只 NF 路径, 默认关) —— 必须在
    #   _page_specials / page_rows / special_tex 之前: 否则它们会被认成书眉/页码画出来, 或与
    #   目录列 x 带重叠被行合并并进邻列(实测 p1171)。本页伪版心由 page_metrics 给出。
    if NF_MODE and pm is not None and NF_DROP_MARGIN:
        _kept = [r for r in all_rows[k] if not _nf_margin_artifact(r, pm)]
        if len(_kept) != len(all_rows[k]):
            print('  [页边水印] p%d 剔除伪版心外横排/非汉字行 %d 条 -> %s' % (
                pg, len(all_rows[k]) - len(_kept),
                ', '.join('「%s」' % r[4][:12] for r in all_rows[k] if _nf_margin_artifact(r, pm))))
            all_rows[k] = _kept
    # §1.995 特殊行(西文行/标题署名行, 只 NF 路径): 在本页任何渲染之前认领出去 —— 它们既不在
    #   正文列配对里(会被竖拆成逐字一格), 也被「本页正文字号」的兜底上限压住。认领方式:
    #   ① 行对象从 all_rows[k] 摘掉(下游 page_rows 自然看不到); ② x 带记进 _SPECIAL_BLOCK,
    #   正常路径(§1.98 槽 / §1.99 带)不再往这些带里落位 —— 不这么做的话「行↔带」配对会整体错位
    #   (实测 p29 的 3 条特殊带正好是最右 3 条, 12 条正文行会去占前 12 条带 -> 左端 3 列落空)。
    if NF_MODE and src_doc is not None and LAT_SP_ON and (pm is not None):
        _g_sp = pm['g']
        _sp, _blk, _cl = _page_specials(k, pg - 1, _g_sp, _nf_ink(pg - 1), all_rows[k])
        if _cl:
            _SPECIAL_SIGS[k] = set((r[0], r[1], r[2], r[3], r[4])
                                   for r in all_rows[k] if id(r) in _cl)
            all_rows[k] = [r for r in all_rows[k] if id(r) not in _cl]
            _SPECIAL_BLOCK[k] = _blk
            _SPECIAL_ROWS[k] = set(_cl)
        _sp_puts = _sp
    # §1.997 引號误识修正(taskU-A): 在本页任何渲染之前, 按**源图墨迹形状**把 OCR 读成「一」的
    #   竖排引號改回 「/」/『/』(1:1 替换, 不动文本长度/格数/列位); 只无版框伪槽格页走这里。
    if NF_MODE and pm is not None:
        _nq = nf_fix_quotes(k, pg - 1, pm)
        if _nq:
            print('  [引號判别] p%d 源图墨迹判定 %d 处「一」实为引號 -> 已改回' % (pg, _nq))
    ok_ = False
    if pm:
        rows_, nrows_, orows_ = page_rows(k, pm, pg - 1)
        if NF_TOC_BRANCH and pm['g'].get('toc'):
            # taskCH: 目录页的所有行(含旧口径划进 note 的「導讀」/「詞話章回目錄」)都由
            #   `_toc_puts` 独立路径按原始行渲染; 不能再让 note_tex 把同一批行当边注画一遍。
            nrows_, orows_ = [], []
        puts_, _pairs, ok_ = page_puts(k, pg - 1, pm)
        # §1.975 重试(taskP): 伪槽格页「行 ↔ 槽」配不上时(槽里混进印刷细线会把 run 连成一条 ->
        #   槽数/字高统计失真), 换「带行墨迹下限」的口径重算槽统计再试一次; 仍不适配才走兜底。
        if (not ok_) and pm['g'].get('virtual') and NF_ROW_FRAC > 0:
            pm2 = page_metrics_rf(pg - 1)
            if pm2:
                rows2_, nrows2_, orows2_ = page_rows(k, pm2, pg - 1)
                puts2_, _pairs2, ok2_ = page_puts(k, pg - 1, pm2)
                # taskQ 遗留2: 「重试口径」不再无条件采纳 —— 该页若不采纳重试, 实际会走 §1.99 框内兜底
                #   (`page_puts_loose`, 同样是源图坐标系的绝对定位, 与本口径可比), 两口径各算一次
                #   **取渲染字数多者**(与 taskP §1 表第 4 行「位置先验 vs 纯格数」同一机制)。
                #   实测源页 24(2 列大幅题字页): 重试口径 82 字 vs 兜底口径 103 字 -> 采纳兜底。
                #   字数口径 = len(puts): col_puts 与 _nf_rescue_rows 都是「一字符一 \put」。
                #   只与兜底口径比(不与 v2 流式比): 流式是「放弃列位」的路径, 它的字数天然最高,
                #   拿它当基准等于关掉整个重试机制(实测过: 会把 taskP 修好的序/扉页重新交回流式)。
                _nA, _whyA = -1, ''
                if ok2_ and NF_RETRY_BEST:
                    _gl3 = frame_geom(pg - 1) or (nf_frame(pg - 1, k) if NF_MODE else None)
                    if _gl3:
                        _ng0 = len(_gap_log)          # 试算口径若最终不采纳, 它的空隙记录不入账
                        _puts3, _np3 = page_puts_loose(k, pg - 1, _gl3, quiet=True)
                        if len(_gap_log) > _ng0: del _gap_log[_ng0:]
                        _nA, _whyA = len(_puts3), '兜底口径 %d 字(%d 列带)' % (len(_puts3), _np3)
                    if _nA > len(puts2_):
                        ok2_ = False
                if ok2_:
                    print('    [无框伪槽格·重试] p%d 行墨迹下限口径适配成功 (原口径 %d 对 -> 现 %d 对, '
                          '渲染 %d 字%s)' % (pg, len(_pairs), len(_pairs2), len(puts2_),
                                           '' if _nA < 0 else ' >= 对照 %d 字' % _nA))
                    pm, rows_, nrows_, orows_, puts_, ok_ = pm2, rows2_, nrows2_, orows2_, puts2_, True
                elif NF_RETRY_BEST and _nA >= 0:
                    print('    [无框伪槽格·重试] p%d 重试口径适配但渲染 %d 字 < %s -> 不采纳, 走兜底'
                          % (pg, len(puts2_), _whyA.strip()))
    if ok_:
        if puts_ or _sp_puts:
            parts.append('\\AddToShipoutPictureFG*{%\n  ' + '%\n  '.join(puts_ + _sp_puts) + '}')
        parts.append('\\null')
        n_frame_pg += 1
        if SPECIAL:
            parts += special_tex(k, pg - 1)                 # 书眉/页码(源墨迹实测, §1.8)
            parts += note_puts_frame(k, pg - 1, pm, nrows_, orows_)
        if V_FRAME:
            parts += frame_tex(pg - 1, pm['g'])             # 用校正后的版框(与列位同源)
        if pg != sel[-1]:
            parts.append('\\newpage')
        continue
    # §1.99 框内兜底(任务D): 有版框但「无槽可配」的页(章题页/註釋页: 全书 5 页) —— 不走 v2 流式回退
    #   (流式回退的列位/字号取自 OCR 盒、列高不受内框约束 -> 列底越版框, p3 标题列还越右框 12.5pt),
    #   改用「内框内墨迹列带」绝对定位(与 §1.98 同源: 几何全部取源图墨迹实测)。
    if V_FRAME and V_FRAME_LAYOUT and src_doc is not None:
        gl = frame_geom(pg - 1)
        if gl is None and NF_MODE:               # §1.975 无版框书: 兜底路径也锚在伪版心上
            gl = nf_frame(pg - 1, k)
        if gl:
            puts2, _np2 = page_puts_loose(k, pg - 1, gl)
            if puts2 or _sp_puts:
                parts.append('\\AddToShipoutPictureFG*{%\n  ' + '%\n  '.join(puts2 + _sp_puts) + '}')
                parts.append('\\null')
                n_frame_pg += 1
                if SPECIAL:
                    parts += special_tex(k, pg - 1)         # 书眉/页码仍按源墨迹定位
                parts += frame_tex(pg - 1, gl)
                if pg != sel[-1]:
                    parts.append('\\newpage')
                continue
    body = page_tex(k, SPECIAL)
    parts.append('\\null' if not body else body)
    if _sp_puts:                            # 特殊行(西文侧排/标题署名)单开一张 FG 图(该分支原本无 FG 图)
        parts.append('\\AddToShipoutPictureFG*{\n  ' + '%\n  '.join(_sp_puts) + '}')
    if SPECIAL:
        parts += special_tex(k, pg - 1)     # 书眉/页码: eso-pic 绝对定位(shipout 叠加, 不占流)
        parts += note_tex(k, pg - 1)        # 边注: 同上(版心外小字注)
    if V_FRAME:
        parts += frame_tex(pg - 1)          # 版框线: 双边外框 + 界行线(源墨迹实测, §1.95)
    if pg != sel[-1]:
        parts.append('\\newpage')           # 末页不加 \newpage: 否则多出一张空白页(231 页跑成 232 页)
parts.append('\\end{document}\n')

# ---------- 2.5) 列内空隙检出清单落盘(taskJ-B) ----------
# 全书跑 231 页的统计 + 逐条记录(page/x0/文本头/插入位置/格数/步进) -> JSON。
#   默认落 TMP; VERT_GAP_REPORT=<path> 可指定(验收要求落 data/wz6/wz6_gaps_detected.json)。
if _gap_log:
    _rep = os.environ.get('VERT_GAP_REPORT') or os.path.join(TMP, 'gaps_detected.json')
    _pg = sorted(set(g['page'] for g in _gap_log))
    json.dump({'n_gap': len(_gap_log), 'n_cell': sum(g['extra'] for g in _gap_log),
               'npage': len(_pg), 'vscale': XSCALE,
               'items': sorted(_gap_log, key=lambda g: g['page'])},
              open(_rep, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print('[空隙] 检出 %d 处 / %d 格, 落在 %d 页 -> %s' % (
        len(_gap_log), sum(g['extra'] for g in _gap_log), len(_pg), _rep))
else:
    print('[空隙] 未检出(或 VERT_GAP=0)')

# ---------- 2.52) 引號误识修正清单落盘(taskU-A) ----------
# 逐处记录(页/列 x/字序/证据: 墨块 w·h·vpos·hpos·本地字高·步进) -> JSON, 供人工复核误改率。
if _qfix_log or _qfix_stat['cand'] or _qfix_all:
    _qf = os.environ.get('VERT_QFIX_REPORT') or os.path.join(TMP, 'qfix.json')
    json.dump({'on': bool(QFIX_ON), 'stat': _qfix_stat, 'recall': _qfix_recall,
               'crit': {'min_ratio': QFIX_MIN_RATIO, 'w_ratio': QFIX_W_RATIO,
                        'vpos': QFIX_VPOS, 'hpos': QFIX_HPOS, 'double': bool(QFIX_DOUBLE)},
               'items': sorted(_qfix_log, key=lambda g: (g['page'], g['idx'])),
               'cands': sorted(_qfix_all, key=lambda g: (g['page'], g['idx'])),
               'miss': _qfix_miss, 'other': _qfix_other},
              open(_qf, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print('[引號判别] 候选 %d 处 -> 判定为引號并改回 %d / 判为真「一」%d / 证据不足跳过 %d -> %s' % (
        _qfix_stat['cand'], _qfix_stat['fixed'], _qfix_stat['dash'], _qfix_stat['skip'], _qf))
    print('[引號判别·召回] 源图引號墨: 文本已读对 %d / OCR 读丢(文本无此字) %d / 对到「一」但未判为引號 %d / 其它 %d'
          % (_qfix_recall['ocr_ok'], _qfix_recall['dropped'], _qfix_recall['missed'], _qfix_recall['other']))

# ---------- 2.53) 列尾闭引号形状纠错清单落盘(taskCM) ----------
# 逐处记录(页/列 x/末字/尾墨 y·w·h/四角特征/动作) -> JSON, 供人工复核误改率与「追加」样本。
if _qsf_log or _qsf_stat['cand']:
    _qj = os.environ.get('VERT_QSF_REPORT') or os.path.join(TMP, 'qsf.json')
    json.dump({'on': bool(QSF_ON), 'append': bool(QSF_APPEND), 'stat': _qsf_stat,
               'crit': {'bar_ar': QSF_BAR_AR, 'bar_h': QSF_BAR_H,
                        'corner_spread': QSF_CORNER_SPREAD, 'corner_max': QSF_CORNER_MAX,
                        'corner_ctr': QSF_CORNER_CTR, 'ring_ctr': QSF_RING_CTR,
                        'ring_edge': QSF_RING_EDGE},
               'items': sorted(_qsf_log, key=lambda g: (g['page'], g['col_x'][0]))},
              open(_qj, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print('[闭引号纠错] 尾格候选 %d -> 改回 %d (1:1 替换 %d / 补字 %d) / 尾格真句号 %d / 真「一」%d / 其它 %d -> %s'
          % (_qsf_stat['cand'], _qsf_stat['replace'] + _qsf_stat['append'],
             _qsf_stat['replace'], _qsf_stat['append'], _qsf_stat['ring'], _qsf_stat['bar'],
             _qsf_stat['other'], _qj))

# ---------- 2.55) 影印页清单落盘(§1.995c; 验证端 --expect-low 的输入 = 这里的数据驱动结果) ----------
if _FAX:
    _fj = os.environ.get('VERT_FAX_REPORT') or os.path.join(TMP, 'fax_pages.json')
    json.dump({'pages': _FAX_DONE, 'detected': dict((str(i + 1), v) for i, v in sorted(_FAX.items())),
               'crit': {'ipc_mult': FAX_IPC_MULT, 'char_mult': FAX_CHAR_MULT, 'dpi': FAX_DPI}},
              open(_fj, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print('[影印页] 实际贴图 %d 页(检出 %d) -> %s' % (len(_FAX_DONE), len(_FAX), _fj))
    print('[影印页] 这 %d 页按设计**不重建文本** -> verify_vert 请用 --expect-low %s'
          % (len(_FAX_DONE), ','.join(str(x) for x in _FAX_DONE)))

tex_path = os.path.join(TMP, 'vert.tex')
open(tex_path, 'w', encoding='utf8').write('\n'.join(parts))
print('[tex] %s (页 %s)' % (tex_path, sel))

# ---------- 2.6) 无版框标定命中率(taskQ 遗留1 的量化口径 + 逐页明细落盘) ----------
# 只统计不判分: 「尝试」= _nf_fix_page 真正跑过的页(_nf_frame 到了标定那一步),
# 「采纳」= 标定通过全部判据并改写了 all_rows。分子分母都写清楚(报告 §1 的修前/修后对比即取这里)。
if _nf_fix_stat['try']:
    _s = _nf_fix_stat
    _rej = ' / '.join('%s %d' % (k, v) for k, v in sorted(_s['rej'].items(), key=lambda t: -t[1]))
    print('[无框-坐标] 标定命中 %d/%d 页(采纳 %d / 拒 %d; 拒因: %s)%.0f%%' % (
        _s['ok'], _s['try'], _s['ok'], _s['try'] - _s['ok'], _rej, 100.0 * _s['ok'] / _s['try']))
    json.dump({'inv': bool(NF_FIX_INV), 'retry_best': bool(NF_RETRY_BEST),
               'try': _s['try'], 'ok': _s['ok'], 'reject_by_tag': _s['rej'],
               'pages': dict((str(k + 1), v) for k, v in sorted(_s['pages'].items()))},
              open(os.path.join(TMP, 'nf_fix.json'), 'w', encoding='utf8'),
              ensure_ascii=False, indent=1)
    print('[无框-坐标] 逐页明细 -> %s' % os.path.join(TMP, 'nf_fix.json'))

# ---------- 3) 编译 ----------
r = subprocess.run(['uplatex', '-interaction=nonstopmode', 'vert.tex'], cwd=TMP, capture_output=True, text=True)
r2 = subprocess.run(['dvipdfmx', 'vert.dvi'], cwd=TMP, capture_output=True, text=True)
dvi_pdf = os.path.join(TMP, 'vert.pdf')
# 失败判据(#18, 实测标定 —— 不能只看 rc, 也不能只看产物):
#   1) uplatex 对**正常成功**的全书编译也返回 rc=1: 唯一报错是类加载期
#      "KANJI Encoding scheme `JT1' unknown."(preamble L884 已注明: tsize10.clo 内无法在文档内拦截,
#      upLaTeX 下该命令本就被忽略), 实测成功编译恰为 1 行 '!' 且该行是它 -> 列为容忍项;
#   2) nonstopmode 下真出错也照样输出 DVI/PDF -> 只查 vert.pdf 存在会漏判。
#   判据 = dvipdfmx rc != 0 或 vert.pdf 未生成 或 uplatex 输出里有**容忍项之外**的 '!' 报错行。
ERR_TOLERATED = ('KANJI Encoding scheme', 'JT1')     # 已知可容忍报错的特征子串
err_bad = [l for l in r.stdout.splitlines()
           if l.startswith('!') and not all(s in l for s in ERR_TOLERATED)]
if r2.returncode == 0 and not err_bad and os.path.exists(dvi_pdf):
    os.replace(dvi_pdf, OUT)
    print('[完成] %s' % OUT)
    sys.exit(0)
print('[失败] uplatex rc=%s dvipdfmx rc=%s 意外报错 %d 行, %s' % (
    r.returncode, r2.returncode, len(err_bad),
    'vert.pdf 已生成' if os.path.exists(dvi_pdf) else 'vert.pdf 未生成'), file=sys.stderr)
for l in err_bad[:10]:
    print('  ' + l, file=sys.stderr)
print(r.stdout[-1500:], file=sys.stderr)
sys.exit(1)
