# battle7 独立验收报告（t29 · 58 处缺字落库 + v37）

> 验收人：验证评审员（独立验证方，t29）　时间：2026-11-06 00:20–00:40
> 基线：HEAD `9207b2c` + 未提交工作树；**未 commit / 未 push**；本报告为本轮唯一新增文件
> 验收对象（t28）：`docs/vert_taskF_missed_fix.json`（58 条 missing_char 落库）、`docs/battle7_missing_chars.md`、
> `output/wz7_full/wz7_full_v37.pdf`（md5 `f4bf3a8d0dfde91eeb3653b2658d664d`）、`tmp_vert/battle7/` 证据。
> 原则：不采信自述——自己复跑 build37、verify_vert、wz6、pytest，自己从源图裁片读字，自己核对去重/计数，自己做字节绑定。

---

## 0. 验收结论（先行）

**结论：PASS（可交付用户）。** 58 条汉字落库核对成立（57 新增 + 1 去重，字段完整、无冲突）；v37 verify_vert PASS
（1748=1748 / 931,106 字 / 差异 18 页全预期 / 整页丢失 0 / 越界 0+0）；字符量 v36→v37 **+57**，55 页逐页可解释；
独立抽 18 条从**源图裁片**读字，18/18 与落库字一致、误插入 0；wz6 逐字节零回归、pytest 590、判据未改、token 未入库；
字节绑定开工=收尾。

**需知悉的残留（不阻塞交付）**：
- **R1（中）**：`build37.sh` **不是字节可复现**——本轮完整重跑得到 md5 `b41f5199…`，与 t28 报告 `f4bf3a8d…` 不同；
  但两 PDF **1748 页文本层逐页 0 差异、行 bbox 逐页 0 差异、全文 text md5 相同**（`1c0679ea…`），差异仅在 PDF 元数据
  `creator/creationDate`（TeX 生成时间 00:18 vs 00:30，文件大小差 2 字节）。故「md5 一致」字面不成立，内容等价成立；
  若要字节复现，需 `SOURCE_DATE_EPOCH` 等固定时间戳（建议下一轮）。
- **R2（低）**：报告 §0 摘要「55 页各 +1（p1337 +2）」与实际不符：实际 **53 页 +1、p1337 +2、p1625 +2**（共 57）；
  §3 逐页表本身是正确的（含 p1625 +2），仅摘要漏写 p1625。
- **R3（低）**：报告 §5 抽样清单把 p779 写作「遮」、p781 写作「紅」，与落库/源图不符（实为 **遞 / 舡**）。
- **R4（低）**：11 条 t24 既有 missing_char（标点/引号/一/媽）无 `crop/cell/strip/shape/complete` 证据字段；
  本轮 58 条均有（属 t24 遗留，不是 t28 的 58 条）。
- **R5（观察）**：fix json 的 mtime（00:20:10）晚于 v37 构建（00:18:49），但用当前 fix json 重跑得到的内容与 v37 逐页一致
  （见 §3），说明该次重写是语义等价的（merge.py 幂等）。

---

## 1. PASS/FAIL 总表

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 独立复跑 build37.sh 得 v37，与报告 md5 一致；verify 退出码 0（1748=1748 / 丢失 0 / 越界 0+0），字符量差值与 58 条对得上（逐页可解释） | **PASS（附 R1）** | 重跑 build37：BUILD/FIX exit 0；md5 `b41f5199…` ≠ 报告 `f4bf3a8d…`（仅 TeX 时间戳元数据；**文本/布局逐页 0 差异**）；已恢复交付产物 `f4bf3a8d…` 并 verify **PASS**（1748=1748 / 931,106÷942,935=98.7% / 差异 18 预期 / 丢失 0 / 越界 span 0+矢量 0）。字符量 v36 931,049 → v37 **931,106（+57）**，55 页：53 页 +1、p1337 +2、p1625 +2，逐页与 `char_diff.json` 及报告 §3 表一致；p634 去重项 0 变化 |
| 2 | 独立核对落库条目：数量、去重、字段完整性；抽 ≥15 条从源图/条带核对「插入位置确有该字」且「OCR 缺该字」，误插入 0 | **PASS** | missing_char 69 = 58 完整（57 新增 + 1 去重 p634 籤）+ 11 条 t24 既有；58 条字段 page/col/pos/ch/side/source/confidence/ratio/exp_len/crop/cell/strip/shape/complete **全齐**、与 t27 清单逐条一致；无同 pos 异字/同字异 pos 冲突；**18 条**独立从 source_pdf 按 cell 裁图读字（p50 竊、p85 峴、p141 謄、p231 人、p247 不、p329 刺、p411 粧、p527 宿、p634 籤、p830 拏、p881 了、p1188 朗、p1256 絹、p1301 咽、p1337 翫、p1397 條、p1507 髫、p1625 遮，另 p779 遞/p781 舡）→ **18/18 一致，误插入 0**；v37 文本层 58/58 在其列多 1 个该字（v36 无/少 1 次） |
| 3 | wz6 零回归：vert.tex `ae9d2f52…` + verify PASS；pytest ≥590 | **PASS** | 本轮重跑 `/tmp/vert_wz6_b7_verify/vert.tex` = `ae9d2f5259e12cff19e680b2a771b37d`；verify PASS（231=231 / 97.2% / 差异 2 预期 / 丢失 0 / 越界 0+0）；pytest **590 passed**（18.51s） |
| 4 | 判据未放宽（git diff 无 verify_vert.py）；token 未进入仓库/报告 | **PASS** | `git diff src/test/verify_vert.py` 为空；verify_vert.py sha256 `cc8b6937…` = HEAD 版本；仓库/报告/fix json/tmp_vert/battle7 无 token 字面（API 工具只读 `/tmp/paddle_token`，不落盘） |
| 5 | 报告 docs/battle7_acceptance.md 含 PASS/FAIL 总表、字节绑定、抽样表、残留风险；不改实现代码、不 commit/push | **PASS** | 本文件；未改 src/ 与 fix json；未 commit（HEAD `9207b2c`） |
| 6 | 字节绑定（build_vert.py / fix json / battle7 报告；附 verify_vert） | **PASS** | 开工 00:20 = 收尾 00:38，见 §2 |

---

## 2. 字节绑定（开工 = 收尾）

| 文件 | 开工（00:20） | 收尾（写报告后 00:34） | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `a5326135de89b251b0b013475277a562a37727f4d4de42d8bcdd74c380b78187` | 同左 | 一致 |
| `docs/vert_taskF_missed_fix.json` | `ec64b51a358ebe83cc279e1991fd6420535eb0cd74d586de6b78c5f0bf7b6c24` | 同左 | 一致 |
| `docs/battle7_missing_chars.md` | `5c25950bc24244f7f89881428da49f3806e9fe282fc0391f6b3e9bd95bc74219` | 同左 | 一致 |
| `src/test/verify_vert.py`（判据） | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致（且 = HEAD） |

> build_vert.py mtime 21:52:51（早于 t28 00:08），t28 未改产品代码；本轮 build37 只读 fix json，未改任何实现文件。

---

## 3. build37 重跑与 v37 验证

- `bash tmp_vert/battle7/build37.sh` → `BUILD_EXIT=0` / `FIXTEXIT=0`；重跑产物 md5 **`b41f51998259b7d6a6357aae0d98f2d1`**。
- 与交付 v37（`f4bf3a8d…`）对比：

| 维度 | 结果 |
|---|---|
| 页数 | 1748 = 1748 |
| 逐页文本 | **0 页差异**（1748/1748 相同），全文 text md5 `1c0679ea80cc2e57f5b9ffc04504706a` **相同** |
| 逐页行 bbox/字号 | **0 页差异** |
| PDF 元数据 | 仅 `creator`（`TeX output …:0018` vs `:0030`）与 `creationDate` 不同；文件大小 109,996,014 vs 109,996,016（+2B） |
| md5 | 不同（R1：时间戳元数据，非内容） |

- 为保证交付物字节不变，已把 `output/wz7_full/wz7_full_v37.pdf` **恢复为原交付文件** `f4bf3a8d0dfde91eeb3653b2658d664d`（重建只用于复现性对比）。
- 对交付 v37 跑 verify_vert（带 --expect-low）：**PASS**：1748=1748；931,106÷942,935=98.7%；差异>80 字页 **18（预期 18/非预期 0）**；整页丢失 **0**；越界 span **0** + 矢量 **0**；exit 0。

---

## 4. 字符量/逐页 diff（独立复算）

- 总数：v36 **931,049** → v37 **931,106**（**+57**）——与 57 条新增一致；去重项 p634 不增字。
- 55 页有变化：**53 页 +1**、**p1337 +2**（两条 翫）、**p1625 +2**（两条 遮）；独立逐页 diff 与
  `tmp_vert/battle7/char_diff.json`（55 条，sum 57）**完全一致**；与报告 §3 表逐格一致。
- 每页的 +1/+2 都能对应到该页的落库条目（页级字符 multiset：55/55 页 = v36 加该页条目字、无其它增删；
  其余 1693 页 multiset 完全不变）；p634 籤 在 v36 已存在，v36=v37 该页无差异（去重成立）。
- 注：报告 §0 摘要「55 页各 +1（p1337 +2）」漏写 p1625 +2（R2）；§3 表正确。

---

## 5. 落库核对（数量/去重/字段）

- `missing_char` 共 **69** 条 = **58 条 complete**（57 新增 + 1 去重 p634 籤）+ **11 条 t24 既有**（标点/引号/一/媽，无 t27 证据字段）。
- 58 条字段：`page/col/pos/ch/side/source/confidence/ratio/exp_len/crop/cell/strip/shape/complete` 全部齐备；
  与 t27 `hanzi_list` 逐条比对：page/col(±2pt)/pos/ch 全命中、`ratio==confidence`、`exp_len==len(text)`、`complete=true`，**0 不一致**。
- 去重：p634 pos22 籤 唯一命中既有 t24 条目（page/pos/ch + col 各维 ≤2pt），仅补 `crop/cell/strip/shape/complete` 证据，不重复落库；
  58 条中其余 57 条与既有 11 条无重复。
- 冲突：全 69 条中无「同页同列同 pos 不同字」、无「同页同列同字不同 pos」。
- 证据文件：58 条 crop/cell/strip 路径全部存在（0 缺失）。

---

## 6. 抽样明细（18 条源图裁片读字）

方法：不读实现者裁片——按 fix 条目 `cell` 坐标，直接从 `source_pdf/wz7.pdf` 以 8×（约 576dpi）裁图，逐张读字。

| # | 页 | 落库字 | 我读到的字 | 结论 | # | 页 | 落库字 | 我读到的字 | 结论 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | p50 | 竊 | 竊（陳經濟**竊**玉偷香） | ✓ | 10 | p830 | 拏 | 拏 | ✓ |
| 2 | p85 | 峴 | 峴 | ✓ | 11 | p881 | 了 | 了 | ✓ |
| 3 | p141 | 謄 | 謄（**謄謄**双字） | ✓ | 12 | p1188 | 朗 | 朗（**朗朗**双字） | ✓ |
| 4 | p231 | 人 | 人 | ✓ | 13 | p1256 | 絹 | 絹 | ✓ |
| 5 | p247 | 不 | 不 | ✓ | 14 | p1301 | 咽 | 咽 | ✓ |
| 6 | p329 | 刺 | 刺（澁**刺刺**） | ✓ | 15 | p1337 | 翫 | 翫 | ✓ |
| 7 | p411 | 粧 | 粧 | ✓ | 16 | p1397 | 條 | 條（赤**條條**） | ✓ |
| 8 | p527 | 宿 | 宿 | ✓ | 17 | p1507 | 髫 | 髫 | ✓ |
| 9 | p634 | 籤 | 籤（既有 t24，去重） | ✓ | 18 | p1625 | 遮 | 遮 | ✓ |

另核 p779 遞、p781 舡（源图字 = 落库字；报告 §5 标签误作 遮/紅，R3）。**18/18 一致，误插入 0。**
OCR 侧：v36 对应列文本 58/58 均比 v37 **少一次该字**（含 4 条「源书双字、OCR 单字」的重复插入：p141 謄、p329 刺、p1188 朗、p1397 條），
与「该列 OCR 确实缺该字（缺一次出现）」一致。

---

## 7. 回归 / 判据 / token

- **wz6**：本轮重跑 `/tmp/vert_wz6_b7_verify/vert.tex` = `ae9d2f5259e12cff19e680b2a771b37d`；verify PASS（231=231 / 68,412÷70,373=97.2% / 差异 2 预期 / 丢失 0 / 越界 0+0）。
- **pytest**：590 passed（840 warnings，18.51s）。
- **判据**：`git diff src/test/verify_vert.py` 空；sha256 与 HEAD 相同（`cc8b6937…`）。
- **token**：`docs/battle7_missing_chars.md`、`docs/vert_taskF_missed_fix.json`、`tmp_vert/battle7/`、api 工具源码
  均无 token 字面；`src/tools/api_*_run.py` 只从 `/tmp/paddle_token` 读取（注释「token 只读，不落盘」）。

---

## 8. 纪律

- `/mnt/d` 未写（本轮未访问；目录 mtime 仍 2026-11-05 19:15）。
- 本轮新增/修改：仅 `docs/battle7_acceptance.md`；`docs/vert_taskF_missed_fix.json`、`docs/battle7_missing_chars.md`、
  `src/`、`data/` 均未改（build37 只写 output 与 /tmp，输出已恢复原字节）。
- `git status`：fix json / build_vert.py（21:52 既有改动）/ battle6/7 报告与 api 工具为 t28 及之前既有；**未 commit**。
- 本任务未改实现代码、未 commit/push。

---

## 9. 残留风险

1. **R1（中）**：build37.sh 非字节可复现（TeX 时间戳）；内容逐页等价但 md5 不能跨次复现。建议固定 `SOURCE_DATE_EPOCH` /
   `FORCE_SOURCE_DATE` 后再宣称 md5 复现；否则验收口径应改为「文本/布局等价」。
2. **R2（低）**：报告 §0 摘要漏写 p1625 +2（§3 表正确）；建议改为「53 页 +1、p1337/p1625 各 +2 = 57」。
3. **R3（低）**：报告 §5 抽样标签 p779 遮 / p781 紅 与落库/源图（遞/舡）不符。
4. **R4（低）**：11 条 t24 既有 missing_char 无 t27 证据字段（本轮 58 条齐全；不阻塞）。
5. **R5（观察）**：fix json mtime 晚于 v37 构建 1.5 分钟，但当前 json 重跑内容与 v37 逐页一致 → merge.py 重写为语义等价。

---

## 10. 复现命令

```bash
cd /opt/test
# 1) 重跑（注意：会覆盖 output/wz7_full/wz7_full_v37.pdf；md5 会因 TeX 时间戳变化）
bash tmp_vert/battle7/build37.sh
# 2) v37 验证（交付产物）
EL=$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)
VERIFY_PITCH_FLOOR=85 /usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v37.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$EL"
# 3) 逐页 diff（v36→v37）
/usr/bin/python3 - <<'EOF'
import fitz,re
v36=fitz.open('output/wz7_full/wz7_full_v36.pdf'); v37=fitz.open('output/wz7_full/wz7_full_v37.pdf')
c=lambda d,i: len(re.sub(r'\s','',d[i].get_text()))
print([(i+1,c(v36,i),c(v37,i)) for i in range(len(v36)) if c(v36,i)!=c(v37,i)])
EOF
# 4) wz6 / pytest
VERT_TMP=/tmp/vert_wz6_b7_verify /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b7_verify.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b7_verify/vert.tex
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

---

## 11. 结论

- **t28 通过（可交付）**：58 条汉字落库（57 新增 + 1 去重）数量/去重/字段全部核对成立；v37 门禁 PASS、字符量 +57 逐页可解释；
  18 条源图裁片读字 18/18 一致、误插入 0；wz6 零回归、pytest 590、判据未改、token 未入库；字节绑定开工=收尾。
- **判定：PASS**；唯一需知悉的是 R1——build37.sh 不是字节可复现（md5 随 TeX 时间戳变），但**内容逐页等价**，不影响交付；
  建议下一轮固定时间戳或在验收口径中明确「文本/布局等价」。R2–R5 为低级别文档/证据登记问题。

> 本报告只写实测；未 commit / 未 push / 未改实现代码。
