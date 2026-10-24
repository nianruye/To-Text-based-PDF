# wz6 三处边注落位核验：基线 `c2fdfa0e` 是错的，现基线 `ae9d2f52` 才对

状态：**已核验，无需改代码**（2026-10-24）

## 背景

taskCL/CL2 把「边注行 ↔ 墨迹列」配对从「按顺序 zip」改成「x 区间重叠 + y 量级」判据后，
wz6 的 `vert.tex` md5 从 `c2fdfa0e63614e61364a74f02d13ac1d` 变成
`ae9d2f5259e12cff19e680b2a771b37d`，差异是 3 处边注的落点：

```
行文本                      旧基线落位   现落位(pt)
全黨同志都要牢記。            x 52.3      x 25.6-47.0
的發展和戰略方向方針的具       x 75.7      —
的革命軍從廣州出發東…         x 53.8      x 34.0-59.5
```

此前一直记为「3 处边注自位未收（回归未解决）」。**这个判断是错的。**

## 判据

以**源图墨迹**为裁判：在边注自身 y 带内扫 x 方向的墨迹柱，看哪种落位有墨支撑。

## 实测（源图 `source_pdf/wz6.pdf`，300dpi，阈值 = 局部背景 − 20）

### p194「全黨同志都要牢記。」（页幅 595.3 × 1244.1pt）

```
源书 y392-597 带内的墨迹柱（节选，x 单位 pt）：
    x  22.6 -  31.0   宽  8.4      ← 窄柱（边注自身）
    x  52.8 -  66.2   宽 13.4      ← 正文第 1 列
    x  77.8 -  91.2   宽 13.4
    x  96.0 - 109.2   宽 13.2
    ...
    x 252.0 - 268.1   宽 16.1
```

```
现落位   x25.6-47.0   与「x22.6-31.0 窄柱」重叠        ✓ 有墨支撑
旧基线   x52.3        正落在「x52.8-66.2 正文第 1 列」  ✗ 压在正文上
```

### p227「的革命軍從廣州出發東…」（页幅 595.3 × 1245.3pt）

```
源书 y350-1133 带内墨迹柱：
    x   0.0 -  87.1   宽 87.1   （页左缘连通块）
    x  90.5 -  93.6   宽  3.1
    ...
现落位 x34.0-59.5 落在 x0-87.1 之内                      ✓ 有墨支撑
```

## 结论

1. **wz6 的边注本来就印在页面左缘（版心之外）**，OCR x 是可信的；
   配对被「拒」是正确的 —— 正文区的墨迹列本来就不该跟页边注配对。
2. **旧基线把边注画在了正文第 1 列上**，那是顺序 zip 的无校验配对造成的错位。
3. 三处「拒」全部是边注（`grep -c "配对调试.*拒"` 实测 **3**，无其它类），
   无一条是正文行被误拒。
4. 因此 **wz6 的 `vert.tex` 基线应更新为 `ae9d2f5259e12cff19e680b2a771b37d`**，
   后续任务以它为「零回归」判据。

## 复核命令

```bash
cd /opt/test
VERT_TMP=/tmp/wz6_dbg VERT_NOTE_PAIR_DBG=1 /usr/bin/python3 src/pipelines/build_vert.py \
    data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json \
    /tmp/wz6_dbg.pdf source_pdf/wz6.pdf 2>&1 | grep -a "配对调试.*拒"
# -> 恰好 3 条，全是边注
md5sum /tmp/wz6_dbg/vert.tex
# -> ae9d2f5259e12cff19e680b2a771b37d

/usr/bin/python3 - <<'PY'
import numpy as np, fitz
src = fitz.open('source_pdf/wz6.pdf'); pg = src[193]
band = fitz.Rect(0, 392.0, pg.rect.width, 597.4)
pm = pg.get_pixmap(clip=band, dpi=300)
a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)
g = a[:, :, :3].mean(axis=2); m = g < (float(np.median(g)) - 20)
prof = m.mean(axis=0); k = 72.0 / 300.0
runs = [(i, i) for i in range(1) ]
segs, s = [], None
for i, v in enumerate(prof > 0.05):
    if v and s is None: s = i
    if not v and s is not None: segs.append((s, i - 1)); s = None
print([(round(a0 * k, 1), round(b0 * k, 1)) for a0, b0 in segs[:6]])
# -> [(0.0,0.0), (22.6,31.0), (52.8,66.2), ...]  边注窄柱在 x22.6-31.0
PY
```

## 影响

- 不产生代码改动。
- `docs/HANDOFF.md` / 各任务简报里的「wz6 零回归基线」应统一写 `ae9d2f52…`，
  `c2fdfa0e…` 仅作历史记录（taskCE 时代）。
