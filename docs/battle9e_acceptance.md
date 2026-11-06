# battle9 独立验收（t42 · v39/v40）

> 验收人：验证评审员（独立验证方）　日期：2026-11-06 15:18–15:32
> 基线：HEAD `accf3f8`（未 commit 工作树）；**未改实现代码、未改 fix JSON、未 commit/push**
> 对象：t40（v39：p57 破折号 + p186/p147）、t41（v40：16 条普查汉字复核落库）
> 主产物：`output/wz7_full/wz7_full_v40.pdf`（md5 `5214c38e031904e264d131155cfe57d9`，1748 页）
> 方法：自己重跑 build40、自己调 fitz/PyMuPDF 量产物竖线、自己从 `source_pdf` 8× 裁源图（不采信实现者裁片）。

---

## 0. 结论

**PASS（可交付）**。v40 是 v39 + 6 条普查确认字的累加重建；v39 的 3 条在 v40 中仍在，p1330 未落库，16 条候选的落/不落清单与实现者报告一致。

**核心数字**：
- 复跑 build40 → `BUILD_EXIT=0/FIXTEXIT=0`；重跑 md5 `6e4a6b7cc0f7d486f148c468704d82bf` ≠ 报告 `5214c38e…`（/ID），但 **size 109,996,941 相同、metadata 相同、1748 页文本/行 bbox 逐页 0 差异** → 内容等价；已恢复交付物 `5214c38e…`。
- verify_vert（--expect-low）**PASS**：1748=1748 / **931,190**（v38 931,178 + 6 [v39] + 6 [v40]）/ 差异>80 字页 **18（预期 18/非预期 0）** / 整页丢失 **0** / 越界 span **0** + 矢量 **0**。
- v39 三条：p57 产物**恰好 1 条**竖线 x 830.005 / y 736.497–816.497 / 长 80.0 / 线宽 2.784，vs 源墨 xc 829.88 / y 736.5–816.0(阈值110)–816.75(阈值150) / 长 79.5–80.25 / 宽 5.25 → 位置/长度一致（Δ≤0.5pt），**线宽 2.784 vs 5.25 为 spec §15 已知 R2 残留（0.040×F，未按源宽）**；p186 `餓鬼﹂。蘇東坡`、p147 `！﹂，那` 均在文本层；p1330 无落库。
- v40 六条：p68 `多以尚書`、p932 `大人家`、p1219 `用纖手`、p1419 `經濟慌`、p1678 `抄步`、p1703 `四制錢`，v39→v40 6 页 +6 且无其它页变化；v38→v40 9 页 +12。
- **16 条候选自裁 16/16**（8×）：6 条确认真缺字并已落；10 条不落理由全部成立（p195/p877/p990/p1368 重复、p207 异体、p572/p782 源图无、**p1270 源图是 `一○○` 不是 九**、**p1330 源图是「泓」不是 絃**、p1560 OCR 把 媽 误读成 馮）。
- wz6 `vert.tex` **ae9d2f5259e12cff19e680b2a771b37d** 逐字节相同 + verify PASS；pytest **590 passed**；判据未改；无 token 字面。

**残留（不阻塞）**：
- **R1**：build40 非字节可复现（`6e4a6b7c…` vs `5214c38e…`），内容逐页等价（/ID）；与既往 v37/v38 现象一致。
- **R2**：p57 产物线宽 2.784pt vs 源墨 5.25pt（0.040×F 口径，spec §15 已登记「线宽先不动」，`VERT_DASH_RULE_W=src` 可切源宽）；y/长度/线心均在允差内。
- **R3**：p1678 源书为「投步」，产物为「抄步」——插入的 `步` 位置正确，但 `投→抄` 的既有 OCR 误读仍在（t41 报告已注明，不在本轮范围）。
- **R4**：v40 的 6 条插入使字符量 +6（931,184→931,190），属预期；verify 的 18 个预期差异页不变。

---

## 1. PASS/FAIL 总表（5 项）

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 独立复跑 build40 → v40；md5 一致（否则 text/bbox 等价证据）；verify exit 0（1748 / 丢失 0 / 越界 0+0 / 字符量 = v38+6+落库数） | **PASS（附 R1）** | BUILD/FIX exit 0；重跑 md5 `6e4a6b7c…` ≠ `5214c38e…`，但 size/metadata/1748 页文本/bbox 逐页 0 差异 → 内容等价；恢复交付物后 verify **PASS**：1748=1748 / 931,190（v38 931,178 + 12）/ 18 预期 / 丢失 0 / 越界 0+0 |
| 2 | v39 三条独立复核：p57 产物竖线 vs 源墨（自裁 8×）、p186/p147 文本层、p1330 未落库 | **PASS（附 R2）** | p57：恰好 1 条 drawing，rect x=830.005、y 736.497–816.497（长 80.0）、线宽 2.784；源墨 xc 829.88、y 736.5–816.0/816.75、长 79.5/80.25、宽 5.25 → Δxc 0.125、Δy0 0.003、Δy1 +0.497/−0.253、长 +0.5/+0.25；线宽差为已知 R2。p57 文本层 `論金瓶梅這部書——導讀`（2 个 `—`，字符 468=466+2，可搜）；p186 `餓鬼﹂。蘇東坡` ✓；p147 `！﹂，那` ✓；p1330 文本无 `分，他每`，fix JSON 无条目 ✓ |
| 3 | v40 16 条候选独立复核：自裁 ≥10 条；落/不落清单与报告一致；重点 p1270/p1330/p1419/p1703 | **PASS** | 自裁 **16/16**（8× cell+上下文）：6 条确认（p68 尚/p932 人/p1219 纖/p1419 慌/p1678 步/p1703 四）已落且 v40 上下文正确（v39 该字计数 0→1）；10 条不落理由全部复核成立（见 §4）；p1270 源图 `一○○`（圆圈）、p1330 源图「泓」、p1419 落「經濟慌」、p1703 落「四制錢」均正确 |
| 4 | wz6 + verify PASS；pytest ≥590；判据未改；token 未入库 | **PASS** | wz6 `vert.tex` `ae9d2f52…` 逐字节 + verify PASS（231=231 / 68,412÷70,373=97.2% / 2 预期 / 0 / 0+0）；pytest **590 passed**（18.05s）；`git diff src/test/verify_vert.py` 空、sha256=HEAD `cc8b6937…`；无 token 字面 |
| 5 | 报告 docs/battle9e_acceptance.md：PASS/FAIL 表 + 字节绑定 + 抽样表 + 残留；不改实现代码、不 commit | **PASS** | 本文件；未改 `src/`、`data/`、fix JSON、`output/`（v40 已恢复原字节）；未 commit（HEAD `accf3f8`） |

---

## 2. 字节绑定（开工 15:18 = 收尾 15:32）

| 文件 | 开工 | 收尾 | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `9b8f87e21712a425f6a946b2427d3265a9196fafabb32331af9759ceae40c263` | 同左 | 一致（mtime 12:22，未改） |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致（=HEAD，判据未改） |
| `docs/vert_taskF_missed_fix.json` | `28f74a2e8d7f3be3415da058755a8a22dc5c0038bd262a8804e5083e32c1d598` | 同左 | 一致（mtime 15:07，v40 数据） |
| `docs/battle9_fix.md` | `247cdc6b514bdd225dec7b38e01805597c9e98228edb277974261811439b63f7` | 同左 | 一致 |
| `docs/battle9d_census_fix.md` | `aa3665aada5ea7cd1b79ab7e55ca29ff4e02bf0275fadebcae3c0076335ac9ae` | 同左 | 一致 |
| `tmp_vert/battle9/d_fix/build40.sh` | `495a14e50181c1d093845267b6b2fa652fb84fe52266789473d1534e6253dd15` | 同左 | 一致 |
| `output/wz7_full/wz7_full_v40.pdf` | md5 `5214c38e…` | md5 `5214c38e…` | 已恢复原交付字节 |

---

## 3. 复跑与 v40 门禁

- `bash tmp_vert/battle9/d_fix/build40.sh`（`SOURCE_DATE_EPOCH=0/FORCE_SOURCE_DATE=1`）：`开始 15:19:08` → `BUILD_EXIT=0` → `FIXTEXIT=0`（15:29:18）→ 重跑 md5 **`6e4a6b7cc0f7d486f148c468704d82bf`**。
- 与交付物 `5214c38e…` 对比：size **109,996,941 = 109,996,941**；metadata 完全相同（creator `TeX output 1970.01.01:0000` / creationDate `D:19700101000000-00'00'`）；**1748 页文本逐页 0 差异、行 bbox/字号逐页 0 差异**（全文 text md5 `d11524fbec8b754bd10300a6748c6ac8` 相同）→ 内容等价（R1，/ID）。
- 已把 `output/wz7_full/wz7_full_v40.pdf` 恢复为 **`5214c38e031904e264d131155cfe57d9`**。
- verify_vert（`--expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"`）：**exit 0 / PASS**：
  1748=1748；931,190÷942,935=**98.8%**；差异>80 字页 **18（预期 18/非预期 0）**；整页丢失 **0**；越界 span **0** + 矢量 **0**。
- 字符量对账：v38 **931,178** → v39 **931,184**（+6：p57 2、p186 2、p147 2）→ v40 **931,190**（+6：p68/p932/p1219/p1419/p1678/p1703 各 1）。

---

## 4. v39 三条复核（p57 破折号 / p186 / p147；p1330 未落库）

### 4.1 p57 产物竖线 vs 源墨

用 fitz `get_drawings()` 读 v40 p57（与 v39 同一条）：

| 项 | 产物 | 源墨（我自裁 8×，t38 口径） | Δ |
|---|---|---|---|
| 条数 | **1 条** | 1 条连续墨段 | — |
| x 中心 | **830.005** | 829.88 | **+0.125** |
| y0 | **736.497** | 736.5（阈值 110）/736.5（阈值 150） | **−0.003** |
| y1 | **816.497** | 816.0（阈值 110）/816.75（阈值 150） | **+0.497 / −0.253** |
| 长度 | **80.0** | 79.5（阈值 110）/80.25（阈值 150） | **+0.5 / −0.25** |
| 线宽 | **2.784** | **5.25** | **−2.466（R2 已知：0.040×F，`VERT_DASH_RULE_W=src` 可切源宽）** |

- 文本层：v40 p57 文本含 `論金瓶梅這部書——導讀`（`—` 计数 2，位于 `書` 后；页面字符 468 = v38 466 +2，可搜索），竖线为唯一矢量，无双线。
- 结论：位置/长度/线心与源墨一致（Δ≤0.5pt，阈值取边范围内），**是源书「——」的一条竖线**；线宽差异为 spec §15 已登记的 R2 残留，不阻断交付。

### 4.2 p186 / p147 文本层

- p186 v40 文本：`餓鬼﹂。蘇東坡` ✓（源图 ﹂ 20.2×9.0 + 下一格 。 7.5×8.2）。
- p147 v40 文本：`…吃！﹂，那婦人…` ✓（源图 ﹂ 18.7×7.7 + 逗号 4.5×6.8）。

### 4.3 p1330 未落库

- `docs/vert_taskF_missed_fix.json` 中无 p1330 条目（punct/census 均无）；v40 p1330 文本不含 `分，他每`；p1330 源图 cell 内仅 3×3pt 噪点（t38 复核），**未落库正确**。

---

## 5. v40 16 条普查候选复核（自裁 16/16）

| # | 页 | 候选字 | 我自裁源图（8×） | 判定 | 报告处置 | 与报告一致 |
|---|---|---|---|---|---|---|
| 1 | p68 | 尚 | `以 尚 書` | 真缺字 | 落库 | ✓ |
| 2 | p195 | 二 | `二 交`（OCR 已有 二） | 重复 | 不落 | ✓ |
| 3 | p207 | 廝 | `個 小 廝`（OCR 为异体 厮） | 异体 | 不落 | ✓ |
| 4 | p572 | 苦 | `金 葉 茶 匙`（无 苦） | 源图无 | 不落 | ✓ |
| 5 | p782 | 們 | `我 有 甚 話`（无 們） | 源图无 | 不落 | ✓ |
| 6 | p877 | 了 | `不 的 了`（OCR 已有） | 重复 | 不落 | ✓ |
| 7 | p932 | 人 | `大 人 家` | 真缺字 | 落库 | ✓ |
| 8 | p990 | 看 | `看 你 看`（OCR 已有两 看） | 重复 | 不落 | ✓ |
| 9 | p1219 | 纖 | `用 纖 手 向` | 真缺字 | 落库 | ✓ |
| 10 | p1270 | 九 | **`一 ○ ○`（圆圈）不是 九** | 非汉字 | 不落 | ✓ |
| 11 | p1330 | 絃 | **`如 泓`（泓形）不是 絃** | 非该字 | 不落 | ✓ |
| 12 | p1368 | 走 | `走 去 走`（OCR 已有） | 重复 | 不落 | ✓ |
| 13 | p1419 | 慌 | `經 濟 慌 的 穿` | 真缺字 | 落库 | ✓ |
| 14 | p1560 | 媽 | `婦 媽 金`（OCR 为 馮；插 媽 会成 `婦媽馮金` 双字） | OCR 误读 | 不落 | ✓ |
| 15 | p1678 | 步 | `投 步 來 到` | 真缺字 | 落库 | ✓（`投→抄` 既有 OCR 误读，见 R3） |
| 16 | p1703 | 四 | `四 制 錢` | 真缺字 | 落库 | ✓ |

**落库清单核对**：fix JSON 的 `missing_char` 共 **150** 条 = 69（battle7 及以前）+ 72（battle8b 引号）+ **3（punct：p57/p147/p186）** + **6（census）**；6 条 census = p68 尚、p932 人、p1219 纖、p1419 慌、p1678 步、p1703 四；按 (page,pos,ch) 去重 **0 重复**；无 p1560 条目（t41 过程项已移除）。
**v40 落位核对**：6/6 列内该字计数 **v39=0 → v40=1**，上下文 `多以尚書`/`大人家`/`用纖手`/`經濟慌`/`抄步`/`四制錢` 全对，无错位、无双字。
**diff 核对**：v39→v40 **6 页 +6**（p68/p932/p1219/p1419/p1678/p1703），无其它页变化；v38→v40 **9 页 +12**（加 p57/p186/p147 各 +2）。

裁片：`/tmp/acceptance11/crops/p{page}_{ch}_ctx8x.png`（16 张，本次验收临时目录）；汇总 `census_cells_10x.png`、`census_ctx_6x.png`、`census_rest5.png`。

---

## 6. 回归 / 判据 / token

- **wz6**：`/tmp/vert_wz6_b9_verify/vert.tex` md5 **`ae9d2f5259e12cff19e680b2a771b37d`**（逐字节同基线）；verify **PASS**（231=231 / 68,412÷70,373=97.2% / 差异 2 预期 / 丢失 0 / 越界 0+0）。
- **pytest**：**590 passed**（840 warnings，18.05s）。
- **判据**：`git diff src/test/verify_vert.py` 空；sha256 = HEAD `cc8b6937…`；`build_vert.py` 与开工同哈希（未改）。
- **token**：报告/fix JSON/`tmp_vert/battle9/d_fix/` 无 token 字面（仅「token 未入库」说明文字）。
- **/mnt/d**：未写；**未 commit**（HEAD `accf3f8`）。

---

## 7. 复现命令

```bash
cd /opt/test
# 1) 复跑 v40（SOURCE_DATE_EPOCH=0；会覆盖 output v40，md5 因 /ID 变化）
bash tmp_vert/battle9/d_fix/build40.sh
# 2) 门禁
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v40.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
# 3) p57 竖线（读矢量）
/usr/bin/python3 - <<'EOF'
import fitz
d=fitz.open('output/wz7_full/wz7_full_v40.pdf')
for x in d[56].get_drawings():
    r=x['rect']
    if r.height>40 and r.width<15: print(r, x.get('width'))
EOF
# 4) p57/p186/p147 文本层
/usr/bin/python3 - <<'EOF'
import fitz,re
d=fitz.open('output/wz7_full/wz7_full_v40.pdf')
for p in (57,186,147,1330):
    t=re.sub(r'\s','',d[p-1].get_text())
    print(p, '——' in t, '餓鬼﹂。' in t, '！﹂，' in t, '分，他每' in t)
EOF
# 5) 16 条源图裁片（8×，只读 source_pdf）
/usr/bin/python3 /tmp/acceptance11/make_census_sheets.py   # 或按报告 §5 表格逐条裁
# 6) wz6 / pytest
VERT_TMP=/tmp/vert_wz6_b9_verify /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b9_verify.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b9_verify/vert.tex
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_vert.py /tmp/wz6_b9_verify.pdf \
  data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json --src-pdf source_pdf/wz6.pdf
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

---

## 8. 残留（不阻塞）

- **R1**：build40 非字节可复现（`6e4a6b7c…` vs `5214c38e…`），size/metadata/文本/bbox 全同 → 内容等价；与既往 v37/v38 的 /ID 现象一致。
- **R2**：p57 线宽 2.784pt vs 源墨 5.25pt（0.040×F；spec §15 已登记「线宽先不动」；`VERT_DASH_RULE_W=src` 可切源宽）。位置/长度/线心在允差内。
- **R3**：p1678 源书「投步」，产物「抄步」——插入 `步` 正确，`投→抄` 是既有 OCR 误读（t41 报告已注明，属另一类问题）。
- **R4**：v40 字符量 +6（931,184→931,190）为预期；verify 18 个预期差异页不变。

---

## 9. 纪律

- 只新增 `docs/battle9e_acceptance.md`；未改 `src/`、`data/`、`docs/vert_taskF_missed_fix.json`、`output/`（v40 已恢复原字节）；未重建交付物（复跑后恢复）；未 commit/push。
- 复跑日志：`/tmp/acceptance11/logs/`（build40、v40_verify、wz6_build、wz6_verify、pytest）；裁片：`/tmp/acceptance11/crops/`。

---

## 10. 结论

**t40/t41 通过（可交付）**：
1. p57 破折号：源墨确为一条竖线；v39/v40 产物**恰好一条**竖线，x 830.005 / y 736.497–816.497 / 长 80.0，与源墨位置/长度一致（Δ≤0.5pt）；线宽 2.784 为已知 R2；文本层 `——` 可搜、字符 +2。
2. p186 `」。`、p147 `」，` 文本层核对通过；p1330 未落库。
3. v40 六条普查字落位正确（6/6 上下文对、v39→v40 6 页 +6、无其它页变化）；16 条候选自裁 16/16，落/不落清单与报告完全一致（含 p1270 圆圈、p1330 泓、p1419 慌、p1703 四）。
4. 门禁：v40 verify PASS（1748 / 931,190 / 18 预期 / 丢失 0 / 越界 0+0）；wz6 `ae9d2f52…` + PASS；pytest 590；判据未改；无 token；未 commit。
