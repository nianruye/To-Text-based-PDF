# battle7 · 58 处缺字落库 → v37 重建 + 门禁

> 任务：t28 — battle7　执行：竖排工程师　日期：2026-11-06
> 输入：`tmp_vert/battle6/api_candidates_all.json` 的 hanzi_list（58 条，complete=true）+ 既有 12 条 missing_char
> 产物：v37 `output/wz7_full/wz7_full_v37.pdf`；报告本文件；证据 `tmp_vert/battle7/`
> 未 commit/push；未改 `src/test/verify_vert.py` / 判据；token 不出现在任何文件/报告。

## 0. 结论

| 项 | 结果 |
|---|---|
| 58 条汉字落库 | ✅ 57 条新增 + 1 条与既有重复（p634 籤，证据补全）；missing_char 总数 12 → **69** |
| v37 | ✅ `output/wz7_full/wz7_full_v37.pdf`，md5 **649a7c8a52fe1cb6f81109faf059dea9**（t32 重定位后；1748 页） |
| verify_vert（--expect-low） | ✅ **PASS**：1748=1748 / 931,106÷942,935=98.7% / 差异>80 字页 **18（与 v36 相同）** / 整页丢失 0 / 越界 span 0+矢量 0 |
| 字符量 | v36 931,049 → v37 **931,106（+57）**：**53 页 +1、p1337 +2、p1625 +2**，与 57 条新增一致、无丢失 |
| wz6 零回归 | ✅ `vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节相同 + verify PASS |
| pytest | ✅ **590 passed** |
| 判据 | 未改 verify_vert.py；token 未写入任何文件 |

## 1. 落库格式与去重

每条 `class=missing_char` 字段：`page / col / pos / ch / side('') / source='api_strip' / confidence='high' / ratio / exp_len / crop / cell / strip / shape / complete`。
- 58 条中 **57 条新增**；**1 条与既有 t24 条目重复**：p634 pos22 `籤`（(page, col±2pt, pos, ch) 命中）→ 不重复落库，仅把 t27 的 `crop/cell/strip/shape/complete` 证据补进既有条目。
- 无「同页同列同 pos 但不同字」的冲突；无「同字不同 pos」的冲突。
- 落库后 `missing_char` 共 **69** 条（t24 11 条 + t27 57 条 + 合并 1 条）。

## 2. v37 门禁

- 构建：`bash tmp_vert/battle7/build37.sh`（保留 `fix_tounicode_circled.py` 调用；`SOURCE_DATE_EPOCH=0`/`FORCE_SOURCE_DATE=1`），`BUILD_EXIT=0`，md5 **`649a7c8a52fe1cb6f81109faf059dea9`**。
- **verify_vert（带 --expect-low）PASS**：
  - 页数 1748 = 1748 ✓；字符量 **931,106** ÷ 942,935 = 98.7%；
  - 差异>80 字页 **18（预期 18 / 非预期 0）**，与 v36 相同（新增 57 字均摊到 55 页，每页 +1，不新增超大差异页）；
  - 整页丢失 0；越界 span 0 + 矢量 0。
- **wz6 零回归**：`/tmp/vert_wz6_b7/vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节相同；verify PASS（231=231 / 97.2% / 差异页 2 预期 / 整页丢失 0 / 越界 0+0）。
- **pytest**：590 passed（unit + invariants）。

## 3. 逐页字符量 diff（v36 → v37，55 页共 +57）

| 页 | v36 | v37 | Δ | 页 | v36 | v37 | Δ |
|---|---|---|---|---|---|---|---|
| p50 | 316 | 317 | +1 | p85 | 538 | 539 | +1 |
| p105 | 498 | 499 | +1 | p141 | 495 | 496 | +1 |
| p213 | 493 | 494 | +1 | p231 | 635 | 636 | +1 |
| p247 | 656 | 657 | +1 | p276 | 754 | 755 | +1 |
| p319 | 679 | 680 | +1 | p320 | 684 | 685 | +1 |
| p329 | 770 | 771 | +1 | p404 | 754 | 755 | +1 |
| p411 | 433 | 434 | +1 | p433 | 620 | 621 | +1 |
| p469 | 500 | 501 | +1 | p527 | 721 | 722 | +1 |
| p549 | 767 | 768 | +1 | p608 | 747 | 748 | +1 |
| p654 | 392 | 393 | +1 | p665 | 770 | 771 | +1 |
| p738 | 726 | 727 | +1 | p779 | 702 | 703 | +1 |
| p781 | 662 | 663 | +1 | p830 | 675 | 676 | +1 |
| p857 | 797 | 798 | +1 | p881 | 774 | 775 | +1 |
| p968 | 567 | 568 | +1 | p987 | 769 | 770 | +1 |
| p1114 | 755 | 756 | +1 | p1120 | 756 | 757 | +1 |
| p1188 | 555 | 556 | +1 | p1189 | 615 | 616 | +1 |
| p1196 | 751 | 752 | +1 | p1241 | 502 | 503 | +1 |
| p1242 | 704 | 705 | +1 | p1256 | 481 | 482 | +1 |
| p1293 | 768 | 769 | +1 | p1301 | 770 | 771 | +1 |
| p1330 | 596 | 597 | +1 | p1337 | 467 | 469 | +2 |
| p1342 | 753 | 754 | +1 | p1397 | 622 | 623 | +1 |
| p1399 | 682 | 683 | +1 | p1406 | 717 | 718 | +1 |
| p1419 | 607 | 608 | +1 | p1437 | 668 | 669 | +1 |
| p1468 | 751 | 752 | +1 | p1495 | 737 | 738 | +1 |
| p1499 | 770 | 771 | +1 | p1507 | 504 | 505 | +1 |
| p1555 | 664 | 665 | +1 | p1625 | 630 | 632 | +2 |
| p1642 | 680 | 681 | +1 | p1653 | 741 | 742 | +1 |
| p1689 | 486 | 487 | +1 | — | — | — | — |

> **53 页各 +1，p1337 +2（同页两条插入）、p1625 +2**。完整机器可读：`tmp_vert/battle7/char_diff.json`。

## 4. 58 条逐条清单

| # | 页 | 字 | pos | 置信 | # | 页 | 字 | pos | 置信 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | p50 | 竊 | 3 | 0.77 | 2 | p85 | 峴 | 42 | 0.97 |
| 3 | p105 | 逕 | 39 | 0.94 | 4 | p141 | 謄 | 17 | 0.99 |
| 5 | p213 | 颳 | 40 | 0.97 | 6 | p231 | 人 | 15 | 0.97 |
| 7 | p247 | 不 | 18 | 0.97 | 8 | p276 | 人 | 2 | 0.99 |
| 9 | p319 | 前 | 37 | 0.99 | 10 | p320 | 了 | 24 | 0.99 |
| 11 | p329 | 刺 | 7 | 0.99 | 12 | p404 | 人 | 30 | 0.96 |
| 13 | p411 | 粧 | 6 | 0.93 | 14 | p433 | 你 | 7 | 0.99 |
| 15 | p469 | 青 | 28 | 0.99 | 16 | p527 | 宿 | 22 | 0.91 |
| 17 | p549 | 他 | 6 | 0.95 | 18 | p608 | 折 | 42 | 0.99 |
| 19 | p634 | 籤 | 22 | 0.99 | 20 | p654 | 粧 | 41 | 0.99 |
| 21 | p665 | 了 | 17 | 0.99 | 22 | p738 | 善 | 25 | 0.98 |
| 23 | p779 | 遞 | 42 | 0.99 | 24 | p781 | 舡 | 36 | 0.99 |
| 25 | p830 | 拏 | 41 | 0.72 | 26 | p857 | 遞 | 42 | 0.99 |
| 27 | p881 | 了 | 18 | 0.97 | 28 | p968 | 官 | 13 | 0.97 |
| 29 | p987 | 於 | 34 | 0.99 | 30 | p1114 | 作 | 42 | 0.99 |
| 31 | p1120 | 的 | 3 | 0.97 | 32 | p1188 | 朗 | 7 | 0.92 |
| 33 | p1189 | 尚 | 28 | 0.99 | 34 | p1196 | 邊 | 4 | 0.97 |
| 35 | p1241 | 不 | 33 | 0.96 | 36 | p1242 | 尋 | 39 | 0.99 |
| 37 | p1256 | 絹 | 36 | 0.93 | 38 | p1293 | 個 | 33 | 0.74 |
| 39 | p1301 | 咽 | 34 | 0.98 | 40 | p1330 | 知 | 1 | 0.93 |
| 41 | p1337 | 翫 | 11 | 0.90 | 42 | p1337 | 翫 | 16 | 0.98 |
| 43 | p1342 | 翠 | 31 | 0.97 | 44 | p1397 | 條 | 1 | 0.93 |
| 45 | p1399 | 筍 | 13 | 0.98 | 46 | p1406 | 人 | 13 | 0.91 |
| 47 | p1419 | 粧 | 28 | 0.97 | 48 | p1437 | 面 | 31 | 0.97 |
| 49 | p1468 | 不 | 21 | 0.97 | 50 | p1495 | 不 | 7 | 0.99 |
| 51 | p1499 | 襯 | 37 | 0.94 | 52 | p1507 | 髫 | 21 | 0.98 |
| 53 | p1555 | 封 | 37 | 0.99 | 54 | p1625 | 遮 | 19 | 0.99 |
| 55 | p1625 | 遮 | 33 | 0.99 | 56 | p1642 | 既 | 8 | 0.95 |
| 57 | p1653 | 蠻 | 5 | 0.97 | 58 | p1689 | 翫 | 27 | 0.95 |

> 完整字段（col/crop/strip/cell/shape）见 `tmp_vert/battle7/hanzi58_merged.json` 与 `docs/vert_taskF_missed_fix.json`；裁片在 `tmp_vert/battle6/all_insert_crops/`。

## 5. 抽样核对（≥10）

- 24 条裁片总览 `tmp_vert/battle7/sample58.png`（3× 放大，标签=页+字；t32/F4 已修两处标签为 p779 遞、p781 舡）：p50 竊、p85 峴、p105 逕、p141 謄、p213 颳、p231 人、p247 不、p276 人、p319 前、p320 了、p329 刺、p404 人、p411 粧、p433 你、p469 青、p527 宿、p549 他、p608 折、p634 籤、p654 粧、p665 了、p738 善、p779 遞、p781 舡 —— **24/24 均为完整字块**，与落库字一致。
- 其余 34 条沿用 t27 的裁片（`all_insert_crops/`，同一流程核验）；t27 已逐条做完整字块形状校验（h≥0.55 步进、w≥0.45 步进、fill 0.05-0.70）。
- 误判/失败项：无新增失败；t27 的标点/Latin/破折号项未进入本轮汉字清单（单列待 taskE/F）。

## 6. 复现命令

```bash
# 1) 落库（幂等：57 新增 + 1 去重更新；missing_char 69）
/usr/bin/python3 tmp_vert/battle7/merge.py
# 2) 构建 v37
bash tmp_vert/battle7/build37.sh
# 3) 验证
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v37.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
# 4) wz6 零回归
VERT_TMP=/tmp/vert_wz6_b7 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b7.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b7/vert.tex   # 期望 ae9d2f5259e12cff19e680b2a771b37d
/usr/bin/python3 src/test/verify_vert.py /tmp/wz6_b7.pdf data/wz6/wz6_spotting_coords.json data/wz6/wz6_spotting_lines.json --src-pdf source_pdf/wz6.pdf
# 5) pytest
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

## 7. 下一轮

- 96 处标点/引号/破折号按 taskE/F 符号类处理（`——` 已有 rule 机制；引号与 QSF 去重后处置）。
- 非候选列补充扫描可选（t26 的 96 批全列计划 ≈1.5-2.4h）。


## 8. t32 修复记录（F1–F4）

### F1 代码级重定位（build_vert.py `_apply_missed_fix`）
- 根因：`fix_split_brackets` 先把**行首闭引号**移到上一行，`_apply_missed_fix` 再按**原 pos** 插 missing_char → 行首被移走 1 字时插入点前移 1，p1241 变「依依不」、p1399 变「茶筍」。
- 修复：新增 `_relocate_missing(cur, pos, ch, ctx, shift)`：
  1) 用 item 的 OCR 上下文 `text`（左 8 + 右 8）在当前行做子串匹配；先完整 needle，再左/右单侧；
  2) 匹配不到回退 `pos - shift`（shift = 该行被 fix_split 移走的行首字符数，`_br_shift` 由 `_br_fix` 汇总）；
  3) 回退越界 → 跳过并打日志（宁少插一字，不错位插）。
- 行首未改动时（shift=0、cur==ctx）上下文匹配命中 pos → **no-op**；t24 的 12 条所在 9 页在 v36→v37 文本 diff 中无变化，证明未受影响。
- 验证：p1241 含「依不依」、不含「依依不」；p1399 含「筍茶」、不含「茶筍」；**全书无「依依不」「茶筍」**。
- 逐页 diff 自证：v36→v37 共 55 页 +57（53 页 +1、p1337 +2、p1625 +2），每页的插入字与落库 item 一一对应（脚本逐页 difflib 核对：55/55 页插入字集合 = 期望集合）；t24 的 9 页无 diff（no-op）。

### F2 p1337 两条「翫」cell/crop 重裁
- 按 v37 实际文本 span 的 bbox 重裁（源图 600dpi→2×）：pos11 → (609.1, 739.6, 635.8, 817.1)；pos16 → (79.7, 560.2, 97.2, 610.9)。
- fix JSON 的 `cell`/`crop` 已更新为 `tmp_vert/battle7/p1337_11_crop.png` / `p1337_16_crop.png`（裁片显示「翫」，不再指向「太」「月」）；正文未动（v37 文本不变）。

### F3 构建可复现
- `build37.sh` 已加 `export SOURCE_DATE_EPOCH=0; export FORCE_SOURCE_DATE=1`，固定 TeX 时间戳元数据；验收口径以 **text/bbox** 为准（内容验收不受 PDF 元数据影响）。

### F4 报告修正
- §0 字符量行改为「53 页 +1、p1337 +2、p1625 +2」；§5 两处标签改为 p779 遞、p781 舡；固定抽样清单补入 p1241（依不依）、p1399（筍茶）、p1337（两处翫，含重裁裁片）。
2026-11-06
