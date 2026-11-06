# battle13b · dash 线宽按页启用（只动 p57）→ v44

> 任务：t67 — 实现 `VERT_DASH_RULE_W_PAGES`（默认空=旧行为），让 p57 单独用源墨实测线宽，其余页保持 v42 原样
> 执行：竖排工程师　日期：2026-11-07
> 产物：`output/wz7_full/wz7_full_v44.pdf`；构建脚本 `tmp_vert/battle13b/build44.sh`
> 约束：未改 verify 判据 / fix JSON / 数据；未 commit；token 未入库。**v43 作废（全局 src 会动 8 页），以 v44 为准。**

## 0. 结论

| 项 | 结果 |
|---|---|
| 新开关 | `VERT_DASH_RULE_W_PAGES`（逗号分隔页号；**默认空 = 旧行为**：`src` 时全页生效；非空时**仅列出的页**用源墨实测宽度，其余页仍 0.040×F） |
| v44 | `VERT_DASH_RULE_W=src VERT_DASH_RULE_W_PAGES=57`；md5 **9bc6cb4992f57b319887cb173090e62a**，1748 页 |
| p57 线宽 | **2.784 → 5.0pt**（= 管线 `_dash_ink_seg` 的源墨实测 `w_src=5.0`；按验收口径 **5.0±0.3** 接受） |
| p57 位置 | y **736.497–816.497**（Δ0）、长 **80.0**（Δ0）、x **829.997**（Δ0.008）——与 v42 一致 |
| 影响面 | **v44 vs v42：内容流逐页比较只有 p57 变化**（34679→34675 bytes）；绘图签名 diff 也只有 p57；其余 **1747 页 content-stream 逐字节相同**（含 p1742 的 48 组、以及 p31/37/38/39/60/62/119/262/462/600/686/1157/1683 全部不变） |
| 门禁 | verify_vert **PASS**（1748=1748 / **931,200** 与 v42 同 / 18 预期 / 整页丢失 0 / 越界 0+0）；wz6 `vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节 + verify PASS；pytest **603 passed**（599+4） |
| 单元测试 | `test_dash_w_pages.py` 4 条：默认空=旧行为 / 列页=该页 src / 多页解析 / CSV 容错（中文逗号、空白、非法项） |

## 1. 实现（`build_vert.py`）

- 常量区（L328 起）：`_parse_page_csv(s)`（容忍中文逗号/空白/非法项）+ `DASH_RULE_W_PAGES = _parse_page_csv(os.environ.get('VERT_DASH_RULE_W_PAGES') or '')`。
- 判定函数（L450）：`_dash_w_src_for(page)` = `(not DASH_RULE_W_PAGES) or (int(page) in DASH_RULE_W_PAGES)`（空集 → True = 旧全局行为）。
- `_dash_rule_tex(seg, F, page=None)`（L455）：`use_src = raw == 'src' and (page is None or _dash_w_src_for(page))`；`w = seg['w'] if use_src else DASH_RULE_W*F`。
- 调用点（L4222）：`_dash_rule_tex(_seg, F, page=_dpg)`（逐页传当前页）。
- **默认值不变**：`VERT_DASH_RULE_W` 默认仍 `0.040`；未设 `VERT_DASH_RULE_W_PAGES` 时行为与旧版完全一致（全局 src 或全局默认）。
- fallback 组（无源墨）仍按 `_put_tex` 的 `DASH_RULE_W*F`，不受新开关影响。

## 2. v42 / v43 / v44 三方对照

| 项 | v42（交付基线） | v43（全局 src，**作废**） | v44（按页启用，**交付**） |
|---|---|---|---|
| 构建开关 | 默认 0.040×F | `VERT_DASH_RULE_W=src` | `VERT_DASH_RULE_W=src` + `VERT_DASH_RULE_W_PAGES=57` |
| md5 | `f964ad71…` | `4ad7c202…` | **`9bc6cb49…`** |
| p57 线宽 | 2.784pt | 5.0pt | **5.0pt** |
| 受影响页 | — | **8 页**（31/37/39/57/62/1157/1683/1742） | **仅 p57** |
| p1742 | 48 组 stroke 宽 1.43 | 22 组变宽 1.5–13.0 / 11 组变 filled | **完全不变**（content-stream 逐字节同） |
| 文本层 | 931,200 | 931,200（0 页差异） | 931,200（0 页差异） |

- v43 的问题（t64 发现）：p1742 異體字表 48 组 dash 中 22 组变宽到 1.5–13.0pt、11 组 stroke→filled，13pt 宽线疑似量到邻笔 → 风险不可接受，作废。
- v44 的按页开关只让 p57 走 src，其余页保持默认 → 影响面收敛到 1 页。

## 3. 影响面证明（v44 vs v42）

```text
内容流逐页比较（xref_stream of page contents）: diff pages = [57]（34679 → 34675 bytes；其余 1747 页逐字节相同）
绘图签名逐页比较（type/rect/width）        : diff pages = [57]
p57: v42 's' w2.784 rect(830.005,736.497,830.005,816.497)
     v44 's' w5.000 rect(829.997,736.497,829.997,816.497)
```

- p57 线宽差异 Δ=2.216pt；线位/线长/线心 Δ≤0.008pt。
- p1742：48 组 stroke 与 v42 完全一致（content-stream 逐字节相同）→ 满足「必须完全不动」。

## 4. 线宽口径说明（5.0 vs 5.25）

- 管线 `_dash_ink_seg` 对 p57 的源墨实测宽度 = **5.0pt**（`dash_segments.json` 的 `w_src`）。
- t42 的 5.25pt 是**阈值 110 的外部测量**；本机 600dpi 多阈值复测：90→5.28 / 110–130→4.56 / 150→3.72（t38 记 90→4.5 / 110→5.25 / 170→6.0）——源墨「宽度」本身随阈值 ±0.7pt。
- 因此按任务更新后的口径 **「src 实测值 5.0±0.3」接受**；不为此改代码阈值。

## 5. 门禁

| 门禁 | 结果 |
|---|---|
| verify_vert（--expect-low） | **PASS**：1748=1748 / **931,200** / 差异>80 字页 18（预期 18/非预期 0）/ 整页丢失 0 / 越界 span 0+矢量 0 |
| wz6 零回归 | `/tmp/vert_wz6_b14/vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节 + verify PASS（231=231 / 97.2% / 2 预期 / 0 / 0+0）；wz6 默认不启用 src |
| pytest | **603 passed**（599+4：`test_dash_w_pages.py` 4 条） |
| 新开关单测 | 4/4：默认空=旧行为 / {57} 仅 57 / {57,1683} 多页 / CSV 容错 |

## 6. 复现命令

```bash
bash tmp_vert/battle13b/build44.sh
md5sum output/wz7_full/wz7_full_v44.pdf          # 9bc6cb4992f57b319887cb173090e62a
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v44.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
# 影响面（只 p57）
/usr/bin/python3 - <<'PY'
import fitz
a=fitz.open('output/wz7_full/wz7_full_v42.pdf'); b=fitz.open('output/wz7_full/wz7_full_v44.pdf')
d=[i+1 for i in range(len(b)) if b''.join(a.xref_stream(x) for x in a[i].get_contents())!=b''.join(b.xref_stream(x) for x in b[i].get_contents())]
print('content-stream diff pages:', d)
p=b[56]
for dr in p.get_drawings():
    r=dr['rect']
    if 820<r.x0<840 and 700<r.y0<830: print('p57', dr['type'], round(float(dr.get('width') or 0),3), round(r.x0,3), round(r.y0,3), round(r.y1,3))
PY
VERT_TMP=/tmp/vert_wz6_b14 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b14.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b14/vert.tex                   # ae9d2f5259e12cff19e680b2a771b37d
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
/usr/bin/python3 -m pytest src/test/unit/test_dash_w_pages.py -v
```

## 7. 约束声明

- 未改 `verify_vert.py` 判据 / `docs/vert_taskF_missed_fix.json` / `data/` / `source_pdf/`；未 commit/push；token 未入库。
- v43（`output/wz7_full/wz7_full_v43.pdf`，全局 src）**作废不交付**；`docs/battle13_dash_width.md` 为 v43 记录，保留作对照。
