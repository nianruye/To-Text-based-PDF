# battle5 独立验收报告（t22 · 高清圈码判定 → v35）

> 验收人：验证评审员（独立验证方，t22）　时间：2026-11-05 20:15–20:35
> 基线：HEAD `90cd949` + 未提交工作树；**未 commit / 未 push**；本报告为本轮唯一新增文件
> 验收对象（t21）：`docs/vert_taskF_missed_fix.json`（21 处圈码改判落库）、`docs/battle5_ring_hires.md`（报告）、
> `output/wz7_full/wz7_full_v35.pdf`（产物，md5 `c7fba7d49e35ac8fc32c468dcaf2eee0`）、`tmp_vert/battle5/`（证据）。
> 输入高清页 `/mnt/d/Downloads/wz7_hires/提取自wz7/`（60 页，**只读**）。
> 原则：不采信自述——自己对齐、自己从高清页裁图读数字、自己复跑 verify/wz6/pytest、自己复算序列。

---

## 0. 验收结论（先行）

**结论：PASS（t21 的高清判定与 v35 交付通过）。** 60 页对齐独立复测成立（scale 6.66 vs align 6.65，模板相关 0.966–0.972，圈/文字落点正确）；
v35 复跑 verify_vert PASS（1748=1748 / 931,040 字 / 差异 18 页全预期 / 整页丢失 0 / 越界 0+0），md5 与报告一致；
21 处改判**逐条**核对（14 处逐张高清裁片人工读图 + 全部 21 处回 v35 文本层核对，**误判 0**）；
剩余 2 处非降违反的 4 个数字（78/76、77/76）高清读图清晰，**保留原值、不做硬改**的结论成立；wz6 逐字节零回归、pytest 590。

**低级别残留（不阻塞，均在实现者报告/证据登记，不影响产物）**：
- **R1**：报告 §0/§4 称剩余 2 处在判定表里 `confidence=不确定`「单列」，但 `ring_decisions.json` 的 confidence 只有「中/高」，无「不确定」值/字段；实际是报告 §4 表格单列（低）。
- **R2**：报告 §3 注、§6 仍写「18 处」改判（实际 **21** 处，§3 表与判定表均为 21），两处旧计数未同步（低）。
- **R3**：标题与 §0 行沿用「352 处圈码」；实际判定表 367 条 = census 352 + `situation=2` 新增 15（`ring_digit_merge` 已记录），报告未在同一处说明（低）。
- **R4**：报告 §6 称「18 处改判逐处有 3–4× 放大裁片（w_*.png、z_*.png）」，实际 battle5 根目录仅 11 个 w_/z_ 放大图（其余为 contact_sheet/pairs/remaining6/uncertain14 等拼图）；本轮已自行从高清页裁齐 21 处核对（低）。
- **R5**：证据图 `z_p1723_x178_3.png` 名字与内容不符（x178.3 属 p1714，疑命名笔误）（低）。

---

## 1. PASS/FAIL 总表（7 项）

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 60 页对齐抽查 ≥3 页（p1682/p1734/p1741），圈位落点与 align.json 一致 | **PASS** | 独立模板匹配：scale **6.66** vs align **6.65**（Δ0.15%），相关 **0.966/0.972/0.969**，offset 差 ≤1pt；三页按 align 映射裁图，p1682 圈码、p1734/p1741 文字均落在预期位置（图 `/tmp/acceptance7/crops/align_p*.png`） |
| 2 | v35 复跑（带 --expect-low）PASS：1748=1748 / 931,040 / 整页丢失 0 / 越界 0+0；md5 与报告一致 | **PASS** | `exit 0`；1748=1748；931,040÷942,935=98.7%；差异>80 字页 **18（预期 18/非预期 0）**；整页丢失 0；越界 span 0+矢量 0；md5 **`c7fba7d49e35ac8fc32c468dcaf2eee0`** |
| 3 | 21 处改判抽样 ≥10 处，打开高清裁片核对数字，误判 0 | **PASS** | 21 处全部回 v35 文本层核对（新值在/旧值不在，21/21）；其中 **14 处**逐张从 4700×7225 高清页裁图人工读图（p1695×2、p1698×2、p1708×5、p1709×3、p1714×5、p1727×1 中的 14 处），读数与判定表**全部一致，误判 0** |
| 4 | 剩余 2 处非降违反的「页边界合法回退」结论复核成立 | **PASS** | p1720 x97.3=**78** → p1721 x617.6=**76**；p1721 x88.8=**77** → p1723 x578.8=**76**，四张裁片数字清晰；改任一值都会与源图矛盾，保留原值成立（"年序合法回退"是源书事实假设，见 §5） |
| 5 | wz6 `vert.tex` `ae9d2f52…` 逐字节不变 + verify PASS；pytest ≥590 | **PASS** | 本轮重跑：`ae9d2f5259e12cff19e680b2a771b37d`；verify PASS（231=231 / 68,412÷70,373=97.2% / 差异 2 预期 / 丢失 0 / 越界 0+0）；pytest **590 passed**（18.23s） |
| 6 | 字节绑定：实现文件开工/收尾哈希一致 | **PASS** | 开工 20:15 / 收尾 20:33 三文件哈希一致，见 §2 |
| 7 | 纪律：未改 /mnt/d、无无关改动；报告含 PASS/FAIL 表与结论 | **PASS** | /mnt/d 60 文件 mtime 仍 19:14–19:15、目录 mtime 19:15（t21 19:19 后无新文件）；19:19 后非 tmp 新改动仅 fix json/报告/v35（+本报告）；build_vert.py mtime 13:01（早于 t21）、未改；未 commit |

---

## 2. 字节绑定（实现文件 SHA-256）

| 文件 | 开工（20:15） | 收尾（写报告后 20:20） | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `b0a8fe8e433fb90d69ed494101ce9ea9f6591d147262e4cb89c2e25a8f8738f6` | 同左 | **一致（绑定成立）** |
| `docs/vert_taskF_missed_fix.json` | `f25d1bf2db44f4b9421d5f35ce622066ae8ab0e1a8d1d10bc7d68ac49f44c936` | 同左 | **一致（绑定成立）** |
| `docs/battle5_ring_hires.md` | `27b8727700a134428ed46367f35a17567558753c9294e625f4640d6e2eef0b7d` | 同左 | **一致（绑定成立）** |

> 收尾哈希在写完本报告后记录（任务书允许）；若不一致按 FAIL 报告前后值。build_vert.py mtime 13:01:44 早于 t21 开工（19:19），t21 未改产品代码。

---

## 3. 对齐复核（独立重测）

- 方法与 t21 同源但独立实现：从 `source_pdf/wz7.pdf` 按 144dpi 渲染 80×80pt 模板，在 `/mnt/d` 高清页灰度图上对 scale 6.55–6.75 做 `cv2.matchTemplate(TM_CCOEFF_NORMED)`。
- 结果：

| 页 | 独立 scale | align scale | 相关 | 独立 offset | align offset |
|---|---|---|---|---|---|
| p1682 | 6.66 | 6.65 | 0.9665 | (2.00, 2.20) | (6.28, 7.82) |
| p1734 | 6.66 | 6.65 | 0.9715 | (3.20, 2.00) | (9.97, 5.43) |
| p1741 | 6.66 | 6.65 | 0.9686 | (2.00, 2.00) | (2.84, 6.43) |

- 说明：offset 绝对差 4–7px ≈ 0.6–1.0pt（< 0.03 个正文步进 44pt），主要来自模板 resize 的栅格相位差；**scale 一致、落点正确**：
  - p1682 按 align 映射到圈码 (346.5,519.5) 裁 55pt 见 §附：圈「8」完整落在窗口内；
  - p1734/p1741 无圈码页按文字坐标映射，裁图见「入月 / 某月」正文，位置正确；
  - 21 处改判的高清裁片（±26pt）全部把目标圈居中/近居中（见 §4），说明 align 偏移在全书一致可用。
- `align.json` 60 页齐全（1682–1741），score 0.961–0.981，与报告 0.96–0.98 一致。

---

## 4. 21 处改判核对（高清读图 + 文本层）

### 4.1 独立读图（14 处逐张，示例）

| # | 页/x | 判定表 前→后 | 我的读数（高清裁片） | 结论 |
|---|---|---|---|---|
| 1 | p1695 x358.1 | 22→32 | **32**（左 3 右 2） | ✓ |
| 2 | p1698 x586.5 | 88→38 | **38**（左 3 右 8） | ✓ |
| 3 | p1698 x251.7 | 99→39 | **39**（左 3 右 9） | ✓ |
| 4 | p1708 x578.1 | 64→54 | **54**（左 5 右 4） | ✓ |
| 5 | p1708 x274.2 | 65→55 | **55** | ✓ |
| 6 | p1708 x75.5 | 58→56 | **56** | ✓ |
| 7 | p1709 x492.1 | 58→56 | **56** | ✓ |
| 8 | p1709 x356.8 | 59→56 | **56** | ✓ |
| 9 | p1714 x446.2 | 55→65 | **65** | ✓ |
| 10 | p1714 x311.6 | 55→65 | **65** | ✓ |
| 11 | p1714 x278.5 | 69→66 | **66** | ✓ |
| 12 | p1714 x210.8 | 85→66 | **66** | ✓ |
| 13 | p1714 x178.3 | 7→67 | **67** | ✓ |
| 14 | p1727 x626.0 | 61→81 | **81** | ✓ |

（另 7 处：p1695 x325=32、p1708 x341.9=55、p1708 x141=56、p1709 x622.5=56、p1720 x97.3=78、p1723 x245.3=78、p1724 x595=78，已在高清拼图中核对一致，见 `/tmp/acceptance7/crops/sheet_all.png`。）
**误判 0 / 21 处。**

### 4.2 文本层核对（21/21）

- 对每处按 `source_x` 找最近列，v35 文本含新值（1–20 用 ㉑…；21–35 用 ㉜…；36–50 用 ㊳…；>50 用「数字+○」）：
  **v35 新值在 21/21、v34 旧值在 21/21、v35 旧值已消失 21/21。**
- 逐页字符 multiset 只差圈码替换（9 页）：
  p1695 ㉒㉒→㉜㉜；p1698 ○○８８９９→㊳㊴；p1708 ８８６→５５５；p1709 ９８８→６６６；
  p1714 ９８５５５⑦→７○６６６６６６；p1720/p1723/p1724 ９→８；p1727 ６→８。
  其余 1739 页文本 multiset 完全不变；全文 931,042→931,040（−2，与报告一致：p1698 −4、p1714 +2）。
- 判定表与报告 §3 表：21 行、21 个唯一 (page,x)、前后值**逐行一致**；`ring_decisions.json` 367 条与 `docs/vert_taskF_missed_fix.json` 367 条 ring 的 number **367/367 匹配**（落库成立）。

---

## 5. 剩余 2 处非降违反复核

- 独立按（page 升序、x 降序=竖排阅读序）复算 367 个判定值的非降违反：**恰好 2 处**，与报告一致：
  1. p1720 x97.3 = **78** → p1721 x617.6 = **76**（p1720 末列 → p1721 首列，页边界）
  2. p1721 x88.8 = **77** → p1723 x578.8 = **76**（跨页/分段）
- 四张高清裁片（±26pt）读数：78、76、77、76 均**清晰无歧义**；在此分辨率下没有第二种合理读法。
- 结论：**接受「保留原值、不硬改」**——改动任一数字都会与源图矛盾；「年序在页边界合法回退/分段重置」是对源书事实的合理解释（属于语义假设，不影响"以源图为准"的处置）。
- 备注（R1）：报告称这两处在判定表里标 `confidence=不确定`，但 `ring_decisions.json` 实际 confidence 只有「中/高」；实质结论不受影响。

---

## 6. v35 / 回归原始输出

```
# v35 verify_vert（--expect-low）
页数: 源 OCR 1748 页 | 输出 PDF 1748 页 | ✓ 1:1
字符量: 输出 931040 / OCR 942935 = 98.7%
差异 > 80 字的页: 18 个（预期 18 / 非预期 0）；整页丢失(0 字)页: 0 个
越界: span 0 个 / 矢量图形 0 个（容忍 0.5pt；涉及 0 页）
== 退出码 PASS ==
md5 c7fba7d49e35ac8fc32c468dcaf2eee0

# wz6
vert.tex ae9d2f5259e12cff19e680b2a771b37d（本轮重跑）
231=231 / 68412÷70373=97.2% / 差异 2 预期 / 丢失 0 / 越界 0+0 / PASS

# pytest
590 passed, 840 warnings in 18.23s
```

---

## 7. 纪律与范围

- `/mnt/d/Downloads/wz7_hires/提取自wz7/`：60 个文件 mtime 仍 **19:14–19:15**，目录 mtime 19:15；t21 开工 19:19 后 `find -newermt` 无新文件 → **未写**。
- 19:19 后非 tmp 新改动：`docs/vert_taskF_missed_fix.json`（20:03）、`docs/battle5_ring_hires.md`（20:14）、
  `output/wz7_full/wz7_full_v35.pdf`（20:13），加本报告；`build_vert.py` mtime 13:01（早于 t21）未改；
  `git status` 其余条目为 battle1–battle4 既有交付（含 13:42 的根目录 png，早于 t21，非本轮产物）。
- 未 commit（HEAD `90cd949`）；本轮未改实现代码。

---

## 8. 复现命令

```bash
cd /opt/test
# 对齐独立复测 + 裁片（本报告脚本）
/usr/bin/python3 /tmp/acceptance7/align_check.py
/usr/bin/python3 /tmp/acceptance7/make_crops.py
# v35 验证
EL=$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v35.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$EL"
# 改判落库/序列核对
/usr/bin/python3 - <<'EOF'
import json
rd=json.load(open('tmp_vert/battle5/ring_decisions.json'))['items']
fix=json.load(open('docs/vert_taskF_missed_fix.json'))['items']
print('changed',sum(1 for i in rd if i['changed']))
seq=sorted(rd,key=lambda d:(d['page'],-d['x']))
print('violations',[(seq[i-1]['page'],seq[i-1]['judged'],seq[i]['page'],seq[i]['judged']) for i in range(1,len(seq)) if seq[i]['judged']<seq[i-1]['judged']])
EOF
# wz6 / pytest
VERT_TMP=/tmp/wz6_b5_verify /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b5.pdf source_pdf/wz6.pdf
md5sum /tmp/wz6_b5_verify/vert.tex
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

---

## 9. 结论

- **t21 通过**：60 页对齐（独立重测 scale/score/落点）成立；v35 verify PASS 且 md5 与报告一致；21 处改判高清读图 + 文本层双核对**误判 0**；剩余 2 处读图清晰、保留原值合理；wz6 零回归、pytest 590。
- **判定：PASS**；附 R1–R5 五项低级别文档/证据登记问题（均在实现者报告或证据文件名，不影响 v35 产物与判定落库），建议下次整理时顺手修。

> 本报告只写实测；未 commit / 未 push / 未改实现代码。
