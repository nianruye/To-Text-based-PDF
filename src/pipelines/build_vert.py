#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_vert.py — 竖排繁体书还原 v1 (流式竖排)
用法: /usr/bin/python3 src/pipelines/build_vert.py <lines.json> <coords.json> <out.pdf> [src.pdf]
env:  VERT_PAGES=3-12    只输出指定页(1-based, 如 '3-12' 或 '3,5')
      VERT_SPECIAL=0       关闭书眉/页码渲染(默认开, 需 src.pdf 测墨迹)
      VERT_TMP=/dir        临时目录(默认 /tmp/vert_<输出文件名 stem>_run: 按产物名分离, 并发不共用)
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
PUNCT_SIZE = float(os.environ.get('VERT_PUNCT_SIZE', 0.62))   # 标点字号/正文字号(源书标点墨迹高仅正文的 ~0.17em)
PUNCT_DX = 0.81        # 标点墨心 x = 格左缘 + PUNCT_DX×格距(源书实测)
PUNCT_DY = 0.85        # 标点墨心 y = 前字格顶 + PUNCT_DY×步进(源书实测)

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
    """排版格数 = 字数 - 挤格标点数(标点挤在前字格内, 不占格)"""
    return max(1, sum(1 for c in t if c not in PUNCT_HANG))

def char_cells(t):
    """逐字格号 [(cell, hanging)] —— 挤格标点与前一字同格(hanging=True); 其余各占一格。"""
    out = []
    k = 0
    for i, c in enumerate(t):
        if c in PUNCT_HANG and i > 0:
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

def _put_tex(ch, x_pt, y_pt, F, xs=None):
    """单字 \\put 片段(pt, 页左上原点 y 向下)。xs = 横向压缩(默认 XSCALE)。
    xs<1 时用自带 q/<K> 0 0 1 0 0 cm ... Q 包住该字(只缩 x 保字高, 状态精确还原不污染后续内容,
    见上方 §1.0a 根因说明); 传入的 x_pt 是缩放后字盒左缘的目标页坐标, 内部按 PAGE_ORIGIN_BP 反解。"""
    xs = XSCALE if xs is None else xs
    body = r'\fontsize{%spt}{%spt}\selectfont %s' % (round(F, 1), round(F, 1), _esc_ch(ch))
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
GAP_HANG = 0.85      # 挤格标点墨顶 = 本字格顶 + GAP_HANG x 步进(与 PUNCT_DY 同源, 源书实测)
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

def fit_gaps(runs, t, m, T0, B, h_ink=None, hratio=GAP_HANG, p_merge=P_MERGE, p_punct=P_PUNCT,
             p_skipn=P_SKIPN, p_r=P_SKIPR, p_g=P_GAP, p_t=P_TOT):
    """槽内墨迹 run + 文本 -> [(字符下标, 插入格数)]（taskJ-B 纯函数, DP）。
    runs: [(墨顶, 墨底)] pt(页顶向下); m: 步进 pt; T0/B: 槽实测墨迹顶/底 pt(用于预测与收口)。
    DP 状态 (字符下标 i, run 下标 j, 已插格数 g); 转移:
      m  字符 <- run 匹配    代价 = (|预测墨顶 - 实测墨顶| / m)^2
      e  字符并进上一 run    预测墨顶落在上一 run 的 [顶, 底] 内(相邻字相碰) —— 便宜
      n  普通字无墨         贵(见 P_SKIPN 注释)
      p  挤格标点           便宜(墨小/挤格缝, 且不参与匹配)
      r  跳过 run / g 插一格
    收口: (i=len(t), j=len(runs), g) 最优 + |槽跨度格数 - (文本格数+g)| x p_t。"""
    L = len(t); n = len(runs)
    if not GAP_ON or L < 2 or n < 3 or m <= 1.0:
        return []
    tops = [r[0] for r in runs]
    bots = [r[1] for r in runs]
    cell = char_cells(t)
    ncell = max(c for c, _h in cell) + 1 if cell else 1

    def pred(i, g):
        c, hang = cell[i]
        return T0 + (c + g + (hratio if hang else 0.0)) * m

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
                if i < L and j < n and not cell[i][1]:
                    # 挤格标点不参与「匹配 run」: 它的墨又小又挤在格缝上(源书实测冒号墨心在
                    #   本字格顶 + 1.2-1.4 步进, 与 PUNCT_DY=0.85 的渲染位置并不一致), 拿它做
                    #   匹配依据会把整列对齐带偏(实测 p14 答：列: 空隙被错插到第 17 字处)。
                    c = cur + (abs(pred(i, g) - tops[j]) / m) ** 2
                    if c < dp[i + 1][j + 1][g]:
                        dp[i + 1][j + 1][g] = c; bt[i + 1][j + 1][g] = (i, j, g, 'm')
                if i < L and j >= 1 and cell[i][1]:
                    c = cur + p_punct
                    if c < dp[i + 1][j][g]:
                        dp[i + 1][j][g] = c; bt[i + 1][j][g] = (i, j, g, 'p')
                if i < L and j >= 1 and not cell[i][1] and bots[j - 1] >= pred(i, g):
                    c = cur + p_merge                      # 预测墨顶落在上一 run 内 = 与它粘连
                    if c < dp[i + 1][j][g]:
                        dp[i + 1][j][g] = c; bt[i + 1][j][g] = (i, j, g, 'e')
                if i < L and not cell[i][1] and cur + p_skipn < dp[i + 1][j][g]:
                    dp[i + 1][j][g] = cur + p_skipn; bt[i + 1][j][g] = (i, j, g, 'n')
                if j < n and cur + p_r < dp[i][j + 1][g]:
                    dp[i][j + 1][g] = cur + p_r; bt[i][j + 1][g] = (i, j, g, 'r')
                if i < L and g < GAP_MAX and cur + p_g < dp[i][j][g + 1]:
                    dp[i][j][g + 1] = cur + p_g; bt[i][j][g + 1] = (i, j, g, 'g')
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
    if best == INF or bg == 0:
        return []
    # 回溯: 'g' 转移 = 在该字符之前插一格
    out = {}
    i, j, g = L, n, bg
    while (i or j or g):
        p = bt[i][j][g]
        if p is None:
            break
        pi_, pj_, pg_, act = p
        if act == 'g':
            out[pi_] = out.get(pi_, 0) + 1
        i, j, g = pi_, pj_, pg_
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

# ---------- 1) 参数拟合 ----------
def col_stats(k):
    """每列: (x0,x1,y0,y1,t)"""
    out = []
    for t, p in zip(sl.get(k, []), co.get(k, [])):
        if not p: continue
        xs = [q[0] for q in p]; ys = [q[1] for q in p]
        out.append((min(xs), max(xs), min(ys), max(ys), _norm_punct(t.strip())))
    return out

all_rows = {k: col_stats(k) for k in keys}

def is_body_col(x0, x1, y0, y1, t):
    """v1.1 列分类(wz6 规则): 正文/标题进流; 书眉/页码(x0>1100 且短)与左侧小字边注(x0<100 且小字号)排除"""
    h = y1 - y0; L = len(t)
    if '\n' in t: return False      # 竖排列 = 单行; 含换行的 OCR 框是多块合并的残片(全书 7 条:
                                    #   p74 图表图例 194 字/p156 注码列/p97·p159·p199·p223 版心「第二卷·抗日戰爭時期」
                                    #   /p90 二天大) —— 当正文排会撑出整页(实测 p74 因此在 231 页里多出 1 页)
    if h < 300 or L < 2: return False
    if x0 > 1100 and h < 300: return False       # 书眉/页码(最右列短行)
    if x0 < 100 and h / L < 55: return False      # 左侧小字边注
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
page_w = 595.3; page_h = 1244.1
src_doc = None
# 页面尺寸: 从 src.pdf 精确取
if SRC:
    import fitz
    d = fitz.open(SRC)
    page_w = round(d[0].rect.width, 1); page_h = round(d[0].rect.height, 1)
    src_doc = d

print('[竖排拟合] 字号%.1fpt 列距%.1fpt 列高%.1fpt 天头%.1fpt 右缘%.1fpt 列数%d 页%.1f×%.1f' % (
    FS, PITCH, HCOL, TTOP, RIGHT_p, NCOL, page_w, page_h))

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
    过滤: 长行(h>=300)/超长文本(>10字)/不在左右边缘; 且剔除「被更长同行竖向包含」的碎片(边注列断行)"""
    rows = all_rows[k]; out = []
    for r in rows:
        x0, x1, y0, y1, t = r
        if y1 - y0 >= 300 or not (2 <= len(t) <= 10): continue
        if not (x0 > 1100 or x1 < 100): continue
        frag = False
        for o in rows:
            if o is r: continue
            if o[2] <= y0 and y1 <= o[3] and (o[3] - o[2]) > (y1 - y0) and min(x1, o[1]) - max(x0, o[0]) > -24:
                frag = True; break
        if frag: continue      # 边注/正文长列里的断行碎片, 非书眉页码
        kind = 'pn' if all(c in NUM_CHARS for c in t) else 'hd'
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
    门限: 宽 4-40px(版框线/正文字更宽)、高 5-90px(版框线更高)、不贴窗口边缘(裁剪碎片丢弃)、
          且 y 中心不落在同页其它特殊行的 OCR 区间内(p7 第二卷/抗日戰争時期 紧邻, 靠此分离)。"""
    from scipy import ndimage
    a = src_gray(pi); H, W = a.shape
    cx = int((x0 + x1) // 2)
    wx0, wx1 = int(max(0, cx - 70)), int(min(W, cx + 70))
    wy0, wy1 = int(max(0, y0 - 250)), int(min(H, y1 + 250))
    if wx1 <= wx0 or wy1 <= wy0: return None    # OCR 行 bbox 越出页面时窗口为空(全书跑实测 p159 触发)
    lab, n = ndimage.label(a[wy0:wy1, wx0:wx1] < 185)
    cs = []
    for i, s in enumerate(ndimage.find_objects(lab), 1):
        h = s[0].stop - s[0].start; w = s[1].stop - s[1].start
        if (lab[s] == i).sum() < 40: continue
        if not (4 <= w <= 40 and 5 <= h <= 90): continue
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
            ch = ch.replace('%', r'\%').replace('#', r'\#').replace('&', r'\&').replace('_', r'\_')
            put.append(r'\put(%.1f,%.1f){\fontsize{%spt}{%spt}\selectfont %s}' % (ix0 / 2.0 + X_CAL, y_put, font, font, ch))
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
# 判据(全书盘点见 tmp_vert/survey_note2.py): 未被书眉/页码认领 且 步进 ∈ [15, 0.85*正文字步进)
#   且 (版心外: x0<100 且 x1 <= 最左正文列x0+2) 或 (* 开头的题注列)。
NOTE_STEP_RATIO = 0.85      # 边注/正文 步进比上限
NOTE_STEP_MIN = 15.0        # 步进下限 px(挡 OCR 噪声页: p231 尾部 JSON 残片 步进 1.1px)
NOTE_INK_RATIO = 0.88       # Noto Serif CJK 单字墨高/字号(渲染端 ink 比, 由 probe 实测标定)

def note_rows(k):
    """本页边注行 [(x0,x1,y0,y1,t)]; 书眉/页码优先认领, 剩下的版心外小字才算边注"""
    rows = all_rows[k]
    claimed = set((c[2], c[3], c[4], c[5], c[1]) for c in special_rows(k))
    lx = min([r[0] for r in rows if is_body_col(*r)], default=0)   # 版心左缘 = 最左正文列 x0
    out = []
    for r in rows:
        x0, x1, y0, y1, t = r
        if len(t) < 2 or (x0, x1, y0, y1, t) in claimed: continue
        step = (y1 - y0) / float(len(t))
        if not (NOTE_STEP_MIN <= step < NOTE_STEP_RATIO * FS_px): continue
        if (x0 < 100 and x1 <= lx + 2) or t.startswith('*'):
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
    m = int(max(8, step * 0.6))
    if zone is None:
        lx = min([r[0] for r in all_rows[k] if is_body_col(*r)], default=0)
        zx0 = 10 ** 9; zx1 = -1
        for x0, x1, y0, y1, t in rows:
            if x0 < 100:                               # 左缘注列: 整条左白边(到版心左缘)
                a_, b_ = 0, lx + 2
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

def note_tex(k, pi, rows=None, zone=None, zone_y=None, tag='边注'):
    """边注 tex 片段: 逐字 \\put。OCR 边注行按 x0 降序(竖排阅读序)配对实测字列(同样 x 降序):
    注文太长时会在下一子列续排(如 p4 注头在右子列、末尾 "的講演" 续在左子列), 子列间无白缝, 只能靠结构配对。
    x = 实测字列左缘; 字号 = 实测单字墨高/ink比(不按字数反推: OCR 会漏字, p4 注头实测约 39 字而 OCR 只 35 字);
    字步进 = (整列墨迹高 - 单字墨高)/(字数-1) -> 整列墨迹上下缘仍与源书对齐。
    rows/zone/zone_y(§1.98 框驱动路径): 行集与区带(px)由调用方给定。"""
    out = []
    rows = sorted(note_rows(k) if rows is None else rows, key=lambda r: -r[0])
    cols = note_cols(pi, k, rows=rows, zone=zone, zone_y=zone_y)
    for (x0, x1, y0, y1, t), (ix0, iy0, ix1, iy1, gh, st) in zip(rows, cols):
        n = len(t)
        font = round(min(26.0, max(9.0, gh / 2.0 / NOTE_INK_RATIO)), 1)
        gink = NOTE_INK_RATIO * font                          # 渲染单字墨高(pt)
        step = round(min(st / 2.0, ((iy1 - iy0) / 2.0 - gink) / (n - 1)) if n > 1 else gink, 2)
        put = []
        for i, ch in enumerate(t):
            y_put = page_h - (iy0 / 2.0 + i * step) - gink + Y_CAL
            ch = ch.replace('%', r'\%').replace('#', r'\#').replace('&', r'\&').replace('_', r'\_')
            put.append(r'\put(%.1f,%.1f){\fontsize{%spt}{%spt}\selectfont %s}' % (
                ix0 / 2.0 + X_CAL, y_put, font, font, ch))
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
    # 全局斜率(相邻有效页码页的斜率中位; 页码应随页序单调递增)
    gslopes = [(v2 - v1) / float(p2 - p1)
               for (p1, _, v1), (p2, _, v2) in zip(recs, recs[1:]) if p2 - p1 <= PN_GAP]
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
            a = statistics.median([(v2 - v1) / float(p2 - p1)
                                   for (p1, _, v1), (p2, _, v2) in zip(seg, seg[1:])])
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
                nv = int(round(vj + (vk - vj) * (p - pj) / float(pk - pj)))   # 邻页线性插值
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
V_FRAME = os.environ.get('VERT_FRAME', '1') not in ('0', 'false', 'False') and src_doc is not None
V_LINE_COV = float(os.environ.get('VERT_LINE_COV', 0.55))
V_LINE_COV_LO = float(os.environ.get('VERT_LINE_COV_LO', 0.30))   # 淡界行线兜底阈值(见 §1.95b)
V_H_COV = float(os.environ.get('VERT_H_COV', 0.45))   # 横线判据: 实测源书横线 0.58-0.99, 正文行 <=0.30
V_THICK_MIN = 2.4      # 粗线判据(pt)
V_THICK_MAX = 6.5      # 粗线上限(pt): 源书外框线 2.5-4.5pt; 更厚的多是扫描黑边残条(8-17pt)
V_FRAME_GAP = 3.2      # 外粗线与内细线的空隙(pt, 缺测时的补位量)
V_FRAME_TH = 3.4       # 外粗线厚度(pt, 缺测时用)
JIE_LOG = os.environ.get('VERT_JIE_LOG', '0') not in ('0', 'false', 'False')   # 界行线调试日志
FDBG = os.environ.get('VERT_FRAME_DEBUG', '0') not in ('0', 'false', 'False')  # 版框检测诊断日志
N_COL_FRAME = 12       # 版框内框列数(印版常数; 抽样页按 内框宽/列距 复核)

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
      ① 枚举 (列距 p ∈ 40-48pt, 某条候选所在栅格) 下所有跨 13 条线的窗口;
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
    for p10 in range(400, 481, 4):                     # 列距 40.0-48.0pt 步进 0.4
        p = p10 / 10.0
        for a in cs:
            g0 = a - p * int(a / p)                    # 含 a 的栅格, 首线在 [0,p)
            n_w = int((cs[-1] + 1.5 * p - g0) / p) + 1
            pos = [g0 + m * p for m in range(n_w)]
            for s in range(0, len(pos) - 12):
                win = pos[s:s + 13]
                if not (400 <= win[-1] - win[0] <= 640): continue
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
            if 35.0 <= p2 <= 52.0:
                p = p2; win[0] = mx - p * mm           # 精修: 以首线为基准
    pos = [win[0] + k * p for k in range(13)]
    if not (400 <= pos[-1] - pos[0] <= 640): return [], None
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

def frame_geom(pi):
    """单页版框实测(pt, 页顶向下) -> dict 或 None(封面/插页等无版框页返回 None)。
    key: in_l/in_r/in_t/in_b 内框(pt); out_l/out_r/out_t/out_b 外粗线(缺测为 None);
         thin[] 内框内所有细竖线 x 中心(含内框左右线); hx_l/hx_r 横线 x 跨度。"""
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
    if not (700 <= ib - it <= 900):
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
    if pitch > 8:
        if out_r is not None and abs((ir - N_COL_FRAME * pitch) - il) > 0.5 * pitch:
            il = round(ir - N_COL_FRAME * pitch, 1)
        if out_l is not None and abs((il + N_COL_FRAME * pitch) - ir) > 0.5 * pitch:
            ir = round(il + N_COL_FRAME * pitch, 1)
    # 栅格兜底命中时: 链首末线就是内框左右线(12 格 = 13 条, 首末即框线), 比上面「横线端头」估值可靠
    #   —— 源书横线横跨整幅纸面(含订口页边), 端头不是框线位置(p36 实测会把右线高估 26pt)。
    if grid_ends is not None: il, ir = round(grid_ends[0], 1), round(grid_ends[1], 1)
    if not (400 <= ir - il <= 640):
        if FDBG: print('    [版框跳过] p%d 内框宽异常 %.1f (il%.1f ir%.1f)' % (pi + 1, ir - il, il, ir))
        return None
    if pitch > 8 and abs((ir - il) / pitch - round((ir - il) / pitch)) > 0.22:
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
INK_RATIO = 0.88        # 单字墨高/字号(Noto Serif CJK, probe_bp 标定: 25 字列墨顶/底命中 0.00pt)
INK_ASC = 0.94          # 字盒内墨迹顶距基线 = INK_ASC x 字号(其余 0.06 为基线下的墨迹下沉)
PT2BP = 1.00375         # TeX pt -> PDF bp 换算(dvipdfmx 按 72.27/72; 实测 put y=1000 落 996.3bp)
V_FRAME_LAYOUT = os.environ.get('VERT_FRAME_LAYOUT', '1') not in ('0', 'false', 'False')

def _slot_runs(ink, x0, x1, y0, y1, min_h=4.0):
    """槽内墨迹 y 投影 -> 字 run [(top, bot)] pt(页顶向下)。
    窗口内缩(实测标定): x 两端 3.5pt —— 界行线组宽可达 2pt, 内缩 2.5pt 时格线偏移 0.6pt 就会
      把整条线的墨带进窗口(实测 p99 右起 3 槽 run 数 23->18, 首 run 变成 290-364 = 格线+首字粘连);
      y 两端 2pt —— 去除版框上下横线(内线组在 [in_t, in_t+th] / [in_b, in_b+th], 下内线取组顶)。
    gap=1px 让同一字的分离笔画(如「二」「門」)并回一个字。
    min_h: run 高下限(pt), 默认 4pt 剔碎片; 取槽顶/槽底时传 0(碎片另按 §1.98 ③ 贴回字 run)。"""
    xa = int((x0 + 3.5) * 2); xb = int((x1 - 3.5) * 2)
    ya = int((y0 + 2.0) * 2); yb = int((y1 - 2.0) * 2)
    if xb <= xa or yb <= ya: return []
    m = ink[ya:yb, xa:xb].any(axis=1)
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

def _grid_from_bands(bands, il, ir, n=N_COL_FRAME):
    """墨迹列带 -> 等距槽格 (首线, 列距) 或 None。
    为什么不用版框检测出的内框直接 12 等分: 界行线淡的页(实测 p32, 全书 3 页)版框兜底栅格会把
    内框宽算成 511pt(真值 522), 12 等分后左端偏差 6pt -> 槽切到列缝上(run 数 25 -> 11)。
    墨迹列带是「字」本身, 不受版框检测误差影响。"""
    cs = sorted((a + b) / 2.0 for a, b in bands)
    if len(cs) < 6: return None
    ds = [b - a for a, b in zip(cs, cs[1:]) if 20 < b - a < 100]
    if len(ds) < 4: return None
    p = statistics.median(ds)
    if not (36.0 <= p <= 50.0) or len(cs) - 1 <= n - 3: return None
    ks = [round((c - il) / p - 0.5) for c in cs]
    e = statistics.median([c - p * (k + 0.5) for c, k in zip(cs, ks)])
    if not (0.9 * (ir - il) <= n * p <= 1.1 * (ir - il)): return None
    return e, p

_metrics_cache = {}
def page_metrics(pi):
    """逐页框驱动基准 -> dict 或 None(无版框页: 封面/p1-p2/末页)。
    key: slots[](12 槽: x0/x1/nr/hm/step/top/bot), body[](正文槽), note[](小字注槽),
         band_t/band_b 正文墨带(pt), font 字号, step_cap 步进上限, w 内框宽。"""
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
        raw = [_slot_runs(ink, edges[i], edges[i + 1], it, ib, min_h=0.0) for i in range(n)]
        # 异常长 run 剔掉(> 3x 全页 run 高中位): 淡界行线/扫描黑边被并进槽内时会连成一条竖贯 run
        #   (实测 p32: 两槽的 run 高 768pt -> 字号被算成 873pt, 该页判不适配)
        _al = sorted(b - a for rs in raw for a, b in rs if b - a >= 4.0)
        _cap = max(40.0, 3.0 * _al[len(_al) // 2]) if _al else 40.0
        # 槽顶/槽底另走「全墨迹」口径(实测, 全书 2640 槽里 8 槽的底、4 槽的顶被上面的长 run 剔除
        #   截断, 最大 471pt —— 实测 p149 c1 底 611 vs 真值 1082.5、p223 c1 顶 1049.5 vs 真值 305):
        #   ① 只剔「贴扫描窗口边」的 run(版框横线/装订黑边一定贴窗边; 正文字墨离墨带顶 ~12pt);
        #   ② 合并成长 run 的连续字(相邻字墨相碰)不剔 —— 取首 run 顶/末 run 底即为该列墨迹上下缘。
        _ea, _eb = (it + 2.0), (ib - 2.0)
        draw = [_slot_runs(dink, edges[i], edges[i + 1], it, ib, min_h=0.0) for i in range(n)]
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
            slots.append({'x0': edges[i], 'x1': edges[i + 1], 'nr': len(rs),
                          'hm': (hs[len(hs) // 2] if hs else 0.0), 'step': step0,
                          'runs': rs,                        # taskJ-B: 空格检测用(逐字墨迹 run)
                          'top': (keep[0][0] if keep else (rs[0][0] if rs else None)),
                          'bot': (keep[-1][1] if keep else (rs[-1][1] if rs else None))})
        hmax = max(s['hm'] for s in slots)
        body = [s for s in slots if s['nr'] >= 2 and s['hm'] >= 0.75 * hmax]
        note = [s for s in slots if s['nr'] >= 3 and s['hm'] < 0.75 * hmax]
        if body:
            # 墨带顶/底 = 正文块上/下缘: 全槽中位会被「段首缩进列」(顶) / 「段尾短列」(底) 带偏
            #   (实测 p18: 12 槽里 6 个短列 -> 中位底 1068, 而满列底 1099.5, 差 31pt = 1 格)。
            #   取「偏满列的一半」的中位: 顶取上半(小的那一半)中位, 底取下半(大的那一半)中位。
            tots = sorted(s['top'] for s in body if s['top'])
            bots = sorted(s['bot'] for s in body if s['bot'])
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
                 'w': ir - il}
        elif note:
            # 整页小字(如 p230 尾注页): 全部当正文槽, 字号按实测小字
            nb = [s['bot'] for s in note if s['bot']]
            band_t = statistics.median(s['top'] for s in note)
            band_b = statistics.median(nb)
            font = round(statistics.median(s['hm'] for s in note) / INK_RATIO, 1)
            m = {'pi': pi, 'slots': slots, 'body': slots, 'note': [], 'g': g,
                 'band_t': band_t, 'band_b': band_b, 'block_b': max(nb), 'font': font,
                 'step_cap': font * 0.95, 'w': ir - il}
        # 合理性校验: 字号 10-60pt(源书正文 34/双行小字 22; 超出即非文字页) 且 墨带高 >= 0.4 内框高
        #   (实测 p229 插图页 12 槽各一条 795pt 竖贯 run -> 字号 896pt; p156 註釋页墨带仅 78pt)
        if m and not (10.0 <= m['font'] <= 60.0 and (m['band_b'] - m['band_t']) >= 0.4 * (ib - it)):
            print('    [基准否决] p%d 字号 %.1f 墨带 %.1f-%.1f (内框高 %.1f) -> 回退流式' % (
                pi + 1, m['font'], m['band_t'], m['band_b'], ib - it))
            m = None
    _metrics_cache[pi] = m
    return m

def _align_rows_slots(rows, slots, skip=8.0):
    """OCR 行(阅读序, 右->左) x 槽(阅读序) 单调对齐 -> [(行下标, 槽下标)]。
    行数 == 槽数(全书 195/231 页): 按序 1:1 直配 —— 源书阅读序 = 槽序, 任何代价法只会引入噪声
      (实测 p9 12:12 时代价法反而丢 1 行 1 槽, 把 21 字那列认成残片)。
    不等时: 动态规划, 且只允许「多的一方」跳过(少的一方每跳一条, 后面整段跟着错位);
      匹配代价 = |OCR 字数 - 槽 run 数 - infl|, infl = 该页两者中位差(墨迹 run 会把相邻相碰的字
      并掉, 实测 p50 OCR 26 字 vs run 23); 罚 skip 取 8 字 —— 只放明显不符的行/槽走, 实测
      p11 两条 OCR 残片(2 字/3 字)对任何槽的代价都 >8 -> 正确落空, 12 条长行全部归位。
    不按 x 位置匹配: OCR x 逐页有 ~10% 伸缩(p100 末列偏 43pt, 首列偏 +30pt), 位置法会认错槽。"""
    R, C = len(rows), len(slots)
    if not R or not C: return []
    if R == C: return [(i, i) for i in range(R)]
    # 代价口径用「排版格数」n_cells(标点不占格): 源槽 run 数 = 源书格数, 与 OCR 字数直接比会
    #   被标点数带偏(§1.0; 全书平均每列 0.51 个挤格标点)
    infl = (statistics.median(n_cells(r[4]) for r in rows)
            - statistics.median(s['nr'] for s in slots))
    row_can = R > C                       # 只允许多的一方跳过
    col_can = C > R
    INF = 1e9
    dp = [[INF] * (C + 1) for _ in range(R + 1)]
    bt = [[None] * (C + 1) for _ in range(R + 1)]
    dp[0][0] = 0.0
    for i in range(R + 1):
        for j in range(C + 1):
            if dp[i][j] >= INF: continue
            if i < R and j < C:
                c = abs(n_cells(rows[i][4]) - slots[j]['nr'] - infl) + dp[i][j]
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

def _merge_col_rows(rows, step):
    """同一列的 OCR 断行合并(在分类/对齐之前做)。
    实测 p34: 「優勢兵力，採用包圍迂迴戰術」(y602-1464) 与「不能包圍其全部也包圍其」(y1564-2336)
    x 带 71.5-139.3 / 57.2-139.3 重叠 83% —— 是源书同一列被 OCR 在中间断开, 不合并则第二段
    无槽可归被丢(该页少 11 字)。判据: x 带重叠 >= 60% 小者宽 且 y 相邻间距 <= 2.5 字步进。"""
    rows = sorted(rows, key=lambda r: -r[0])
    used = [False] * len(rows)
    out = []
    for i, r in enumerate(rows):
        if used[i]: continue
        x0, x1, y0, y1, t = r
        used[i] = True
        again = True
        while again:
            again = False
            for j, o in enumerate(rows):
                if used[j]: continue
                ox0, ox1, oy0, oy1, ot = o
                ov = min(x1, ox1) - max(x0, ox0)
                if ov < 0.6 * min(x1 - x0, ox1 - ox0): continue
                if 0 <= oy0 - y1 <= 2.5 * step:                # o 在本行之下
                    t = t + ot; y1 = oy1
                elif 0 <= y0 - oy1 <= 2.5 * step:              # o 在本行之上
                    t = ot + t; y0 = oy0
                else:
                    continue
                x0 = min(x0, ox0); x1 = max(x1, ox1)
                used[j] = True; again = True
        out.append((x0, x1, y0, y1, t))
    return out

def page_rows(k, m, pi):
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
    step_px = statistics.median([(r[3] - r[2]) / float(len(r[4])) for r in inb]) if inb else 60.0
    ins = _merge_col_rows(ins, step_px)
    out_rows = _merge_col_rows(out_rows, step_px)
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
    st = sorted(((r[3] - r[2]) / float(len(r[4]))) for r in lng)
    gmax, gi = 0.0, -1
    for j in range(len(st) - 1):
        rat = st[j + 1] / max(1e-6, st[j])
        if rat > gmax: gmax, gi = rat, j
    # 阈值 1.18: 单一字号页的最大步进间隙比实测 <= 1.13(全书 196/224 页 <1.20), 而正文/双行小字
    #   注的步进比实测 1.21-1.62(p4 1.246 / p162 1.55) -> 1.18 分隔两类且不误切单字号页。
    if gmax >= 1.18 and len(st) >= 4:
        thr = (st[gi] + st[gi + 1]) / 2.0
        b2 = [r for r in lng if (r[3] - r[2]) / float(len(r[4])) > thr]
        n2 = [r for r in lng if (r[3] - r[2]) / float(len(r[4])) <= thr]
        # 交叉验证(源图容量判据): 拆出来的两类都要装得下 —— 注位 = 注槽 x2(双行小字), 正文位 = 正文槽;
        #   不一致则不做拆分(实测 p20 间隙比 1.218 但只有 1 行偏大 -> 是标题行, 不是注页)。
        if len(n2) + len(note) <= 2 * len(m['note']) + 2 and len(b2) + len(body) <= len(m['body']) + 2:
            body += b2; note += n2
        else:
            body += lng
    else:
        body += lng
    return body, note, out_rows

def _esc_ch(t):
    """单字 LaTeX 转义(与旧正文流同一组: % # & _)。"""
    return t.replace('%', r'\%').replace('#', r'\#').replace('&', r'\&').replace('_', r'\_')

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
    cap = m['step_cap']
    ink_h = INK_RATIO * F
    T = sl['top'] if (sl and sl.get('top') is not None) else m['band_t']
    B = sl['bot'] if (sl and sl.get('bot') is not None) else m['band_b']
    band_b = m['band_b']
    full = (band_b - B) <= 3.0 * cap                         # 满列判据: 源槽墨底贴墨带底
    nc = n_cells(t)                                          # 排版格数(标点不占格)
    # 列内空隙(taskJ-B): 本槽 run 序列 + 文本 -> 额外空格格数(该格不落墨, 只推进)
    gaps = (fit_gaps(sl['runs'], t, (sl.get('step') or cap), T, B, h_ink=ink_h)
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
        F = round(0.95 * step / INK_RATIO, 1)
        ink_h = INK_RATIO * F
        if full:
            step = min(1.30 * cap, max(0.75 * cap, (B - T - ink_h) / (nc - 1)))
        if top + ink_h + (nc - 1) * step > guard_b:
            step = (guard_b - top - ink_h) / (nc - 1)
    y0 = top + INK_ASC * F                                   # 首字基线(页顶向下, 墨顶在基线上方 0.94F)
    x_put = xc - XSCALE * F / 2.0                            # taskJ-A: 横向压缩后字心仍居中于槽中心
    pitch = (sl['x1'] - sl['x0']) if sl else m['w'] / N_COL_FRAME    # 本格格距(pt)
    Fp = PUNCT_SIZE * F                                      # 标点字号(源书标点墨迹明显小于正文)
    out = []
    k = 0                                                    # 当前格号(挤格标点不推进)
    for ci, ch in enumerate(t):
        k += gap_at.get(ci, 0)                               # 该字符前的空格格(taskJ-B): 只推进不落墨
        if ch in PUNCT_HANG and k > 0:                       # 挤格标点: 贴前一格右下区(单独字号)
            tx = sl['x0'] + PUNCT_DX * pitch if sl else xc - pitch / 2.0 + PUNCT_DX * pitch
            ty = top + (k - 1) * step + PUNCT_DY * step
            dx, dy = PUNCT_INK.get(ch, (0.47, -0.36))        # 字形墨心相对锚点(em)
            out.append(_put_tex(ch, tx - XSCALE * dx * Fp, page_h - (ty - dy * Fp), Fp))
            continue
        y_put = page_h - (y0 + k * step)
        out.append(_put_tex(ch, x_put, y_put, F))
        k += 1
    return out, top + ink_h + (max(k, 1) - 1) * step

def page_puts(k, pi, m):
    """本页正文列: OCR 行(阅读序) 对齐 正文槽(阅读序) -> 逐字 \\put。
    返回 (tex 列表, 配对数, 是否适配)。双行小字页(实测 p157/p158/p192/p228: 24 列 = 12 槽 x2,
    每槽内左右两子列)按 2 倍子列重建槽位; 适配判据 = 配上行数 >= 0.8x 行数(不适配的页
    —— 章题页/大字数行页如 p3 9 行 2 槽/p156 23 行 1 槽 —— 交回 v2 流式排版)。"""
    rows, _nrows, _orows = page_rows(k, m, pi)
    rows = sorted(rows, key=lambda r: -r[0])
    slots = sorted(m['body'], key=lambda s: -s['x1'])
    R, C = len(rows), len(slots)
    if C and 1.7 * C <= R <= 2.3 * C:                    # 双行小字页: 槽内再分左右子列
        ink = src_gray(pi) < 150
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
    pairs = _align_rows_slots(rows, slots)
    puts = []
    prev_bot = None
    for ri, si in pairs:
        sl = slots[si]
        xc = (sl['x0'] + sl['x1']) / 2.0
        p, prev_bot = col_puts(rows[ri][4], xc, m, sl, prev_bot, pi)
        puts += p
    ok = (not R) or (len(pairs) >= 0.8 * R)
    print('  [正文列] p%d %d 行 -> %d 槽 (槽 run %s) 字号 %.1f 墨带 %.1f-%.1f 上限 %.2f %s' % (
        pi + 1, R, len(pairs), [s['nr'] for s in slots],
        m['font'], m['band_t'], m['band_b'], m['step_cap'],
        '' if ok else '<<不适配, 回退流式'))
    return puts, pairs, ok

def _band_stats(ink, x0, x1, it, ib):
    """区带 x0-x1(pt) 内的墨迹 run 统计 -> {nr, hm, step, top, bot}(pt)。
    先剔「竖线列」(该列墨占比 > 0.6: 版框线/界行线 —— 否则长 run 贯穿内框, 字高会被测成框高),
    再按 page_metrics 同口径统计(run 高限 4pt..3×中位)。"""
    xa, xb = int(x0 * 2), int(x1 * 2)
    ya, yb = int((it + 2) * 2), int((ib - 2) * 2)
    z = {'nr': 0, 'hm': 0.0, 'step': 0.0, 'top': None, 'bot': None}
    if xb - xa < 2 or yb - ya < 4: return z
    sub = ink[ya:yb, xa:xb]
    sub = sub[:, sub.mean(axis=0) <= 0.6]
    if sub.shape[1] < 2: return z
    rs = [((ya + a) / 2.0, (ya + b + 1) / 2.0) for a, b in _runs(sub.any(axis=1), 1)]
    hs = sorted(b - a for a, b in rs)
    hm0 = hs[len(hs) // 2] if hs else 0.0
    cap = max(40.0, 3.0 * hm0)
    rs = [r for r in rs if 4.0 <= r[1] - r[0] <= cap]
    hs = sorted(b - a for a, b in rs)
    cs = sorted((a + b) / 2.0 for a, b in rs)
    ds = sorted(d for d in (cs[j + 1] - cs[j] for j in range(len(cs) - 1)) if d < 80)
    return {'nr': len(rs), 'hm': (hs[len(hs) // 2] if hs else hm0),
            'step': (ds[len(ds) // 2] if ds else 0.0),
            'top': (rs[0][0] if rs else None), 'bot': (rs[-1][1] if rs else None)}

def page_puts_loose(k, pi, g):
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
    返回 (tex 列表, 配对数)。"""
    ink = src_gray(pi) < 150
    il, ir, it, ib = g['in_l'], g['in_r'], g['in_t'], g['in_b']
    T, B = it + 2.0, ib - 2.0
    avail = B - T
    if avail <= 20: return [], 0
    # 列带(源图墨迹) -> 伪槽(统计口径与 page_metrics 同: run 高 4..3×中位)
    slots = []
    for a, b in _ink_bands(ink, il, ir, it, ib, cov=0.12):
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
preamble = r'''\documentclass[10pt,disablejfam]{tarticle}
\usepackage[unicode]{pxchfon}
\setminchofont[3]{NotoSerifCJK-Regular.ttc}
\setgothicfont[3]{NotoSansCJK-Regular.ttc}
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
       'PW0': page_w, 'PH0': page_h}

parts = [preamble]
n_frame_pg = 0
for i, pg in enumerate(sel):
    k = keys[pg-1]
    dr = derot_rows(k, pg - 1, all_rows[k])      # §1.97: OCR 旋转坐标系页还原(只影响本页)
    if dr is not None: all_rows[k] = dr
    parts.append('%% ===== 源第 %d 页 (key %s) =====' % (pg, k))
    # §1.98 框驱动路径: 有版框的页用「逐页版框实测」排版(逐字 \put 绝对定位, 不占版心流);
    #   无版框页(封面/p1-p2/末页)保持 v2 的 OCR 拟合流式排版
    pm = page_metrics(pg - 1) if (V_FRAME and V_FRAME_LAYOUT and src_doc is not None) else None
    ok_ = False
    if pm:
        rows_, nrows_, orows_ = page_rows(k, pm, pg - 1)
        puts_, _pairs, ok_ = page_puts(k, pg - 1, pm)
    if ok_:
        if puts_:
            parts.append('\\AddToShipoutPictureFG*{%\n  ' + '%\n  '.join(puts_) + '}')
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
        if gl:
            puts2, _np2 = page_puts_loose(k, pg - 1, gl)
            if puts2:
                parts.append('\\AddToShipoutPictureFG*{%\n  ' + '%\n  '.join(puts2) + '}')
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

tex_path = os.path.join(TMP, 'vert.tex')
open(tex_path, 'w', encoding='utf8').write('\n'.join(parts))
print('[tex] %s (页 %s)' % (tex_path, sel))

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
