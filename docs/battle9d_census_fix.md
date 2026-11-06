# battle9d · 全书普查 16 条汉字复核落库 → v40

> 任务：t41 — battle9d　执行：竖排工程师　日期：2026-11-06
> 输入：t37 `tmp_vert/battle9/api_battle9.json` 的 hanzi_list（16 条候选）
> 基线：t40 的 v39（`output/wz7_full/wz7_full_v39.pdf`，md5 c77037aa…）
> 产物：v40 `output/wz7_full/wz7_full_v40.pdf`；本报告；证据 `tmp_vert/battle9/d_fix/`
> 数据-only：只改 `docs/vert_taskF_missed_fix.json`（+6 条 missing_char，移除 1 条误落）；未改 `build_vert.py` / verify 判据；未 commit；token 未入库。

## 0. 结论

| 项 | 结果 |
|---|---|
| 16 条逐条复核 | **全查（不抽样）**：8×/10× 源图 cell + 上下文裁片（`sheet_cell.png` / `sheet_ctx.png` / `sheet_focus*.png`），每条给 verdict |
| 确认落库 | **6 条**：p68 尚、p932 人、p1219 纖、p1419 慌、p1678 步、p1703 四 |
| 不落库 | **10 条**：p195 二（重复）、p207 廝（异体/位置歧义）、p572 苦（源图无）、p782 們（源图无）、p877 了（重复）、p990 看（重复）、p1270 九（源图为圆圈）、p1330 絃（源图为泓形）、p1368 走（重复）、p1560 媽（OCR 馮 误读致重复） |
| v40 | `output/wz7_full/wz7_full_v40.pdf` md5 **5214c38e031904e264d131155cfe57d9**，1748 页 |
| verify_vert（--expect-low） | **PASS**：1748=1748 / **931,190**（v39 931,184 +6）/ 差异>80 字页 18（预期 18）/ 整页丢失 0 / 越界 span 0+矢量 0 |
| v39→v40 diff | **6 页 +6**（p68/p932/p1219/p1419/p1678/p1703 各 +1，无其他页变化） |
| wz6 零回归 | `vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节相同 + verify PASS |
| pytest | **590 passed** |
| 判据 | 未改 `verify_vert.py` / `build_vert.py` |

## 1. 16 条逐条复核表

| # | 页 | 候选字 | pos | 置信 | 源图证据（上下文） | verdict | 处置 |
|---|---|---|---|---|---|---|---|
| 1 | p68 | 尚 | 12 | 0.987 | 源列 `多以尚書`；OCR 为 `多以書`（漏 尚） | **真缺字** | ✅ 落库 |
| 2 | p195 | 二 | 35 | 0.989 | 源列 `武二交跌`；OCR 已有 `武二`，API 多出的 二 为重复 | 重复（非缺字） | ❌ 不落 |
| 3 | p207 | 廝 | 14 | 0.966 | 源列 `一個小廝，`；OCR 为 `小、厮`（异体 厮 + 顿号噪声），插 廝 会与 厮 重复 | 异体/位置歧义 | ❌ 不落 |
| 4 | p572 | 苦 | 1 | 0.972 | 源列 `金葉茶匙`（无 苦） | 非汉字/源图无 | ❌ 不落 |
| 5 | p782 | 們 | 12 | 0.977 | 源列 `你叫我有甚話`（无 們） | 源图无 | ❌ 不落 |
| 6 | p877 | 了 | 26 | 0.955 | 源列 `了不的了` = OCR 文本，无额外 了 | 重复 | ❌ 不落 |
| 7 | p932 | 人 | 16 | 0.944 | 源列 `藏在那大人家，`；OCR 为 `大家，`（漏 人） | **真缺字** | ✅ 落库 |
| 8 | p990 | 看 | 10 | 0.977 | 源列 `來看你看` = OCR 文本（已有两个 看） | 重复 | ❌ 不落 |
| 9 | p1219 | 纖 | 35 | 0.966 | 源列 `用纖手向`；OCR 为 `用手向`（漏 纖） | **真缺字** | ✅ 落库 |
| 10 | p1270 | 九 | 1 | 0.667 | 源列为 `一〇〇`（两个圆圈/圈号），**不是 九** | 非汉字 | ❌ 不落 |
| 11 | p1330 | 絃 | 14 | 0.989 | 源列 `襪如泓，兩`（泓/孤形，非 絃） | 非该字 | ❌ 不落 |
| 12 | p1368 | 走 | 33 | 0.977 | 源列 `娘子走去走` = OCR 文本（已有 走去走） | 重复 | ❌ 不落 |
| 13 | p1419 | 慌 | 32 | 0.977 | 源列 `經濟慌的穿出`；OCR 为 `經濟的穿出`（漏 慌） | **真缺字** | ✅ 落库 |
| 14 | p1560 | 媽 | 17 | 0.975 | 源列 `婦媽金`；OCR 为 `婦馮金`（把 媽 误读成 馮），API 又读成 `媽馮` — 插入会成 `婦媽馮金` 双字 | 重复（OCR 误读） | ❌ 不落（曾试落，v40 文本出现 `婦媽馮金` 后已从数据移除） |
| 15 | p1678 | 步 | 21 | 0.966 | 源列 `投步來到`；OCR 为 `抄來到`（抄=投 的 OCR 误读，漏 步） | **真缺字** | ✅ 落库（`抄步` 位置正确；抄→投 是另一 OCR 错误，不在本轮） |
| 16 | p1703 | 四 | 37 | 0.868 | 源列 `四制錢`；OCR 为 `制錢`（漏 四） | **真缺字** | ✅ 落库 |

> 证据裁片：`tmp_vert/battle9/d_fix/sheet_cell.png`（16 格 10×）、`sheet_ctx.png`（16 格上下文）、`sheet_focus.png`（p195/207/1270/1330/1419/1703）、`sheet_focus2.png`（p572/782/877/990/1368/1678）、逐条 `p{page}_{pos}.png`。

## 2. 落库与去重

- 新增 6 条 `missing_char`（source=`api_strip_census`，字段 page/col/pos/ch/text/api/crop/cell/complete/shape/confidence/ratio/exp_len）。
- 与已落库 141 条按 (page, pos, ch) 去重：**0 重复**。
- 过程记录：p1560 曾在第一版 v40（md5 f743933f…，+7）中落库，复核 v40 文本发现 `婦媽馮金` 双字 → 已从 fix JSON 移除并重建 v40（md5 5214c38e…，+6）；p1560 最终不落。

## 3. v40 门禁与 diff

- 构建：`bash tmp_vert/battle9/d_fix/build40.sh`（SOURCE_DATE_EPOCH=0），`BUILD_EXIT=0`，md5 **5214c38e031904e264d131155cfe57d9**。
- verify_vert（--expect-low）**PASS**：1748=1748 / **931,190**（v39 931,184 +6）/ 差异>80 字页 18（预期 18/非预期 0）/ 整页丢失 0 / 越界 span 0+矢量 0。
- **v39→v40 逐页 diff：6 页 +6**（p68 627→628、p932 754→755、p1219 504→505、p1419 608→609、p1678 718→719、p1703 514→515；无其他页变化）。
- 每条插入在 v40 文本层的落位核对：`多以尚書` / `大人家` / `用纖手` / `經濟慌` / `抄步` / `四制錢` —— 6/6 上下文正确，无错位、无双字。
- wz6：`/tmp/vert_wz6_b10/vert.tex` md5 **ae9d2f5259e12cff19e680b2a771b37d** 逐字节相同 + verify PASS。
- pytest：**590 passed**。

## 4. 与「漏检率 21.6%」的口径说明

- t37 报的 21.6% = **API 候选** 16 /（已落 58 + 候选 16）—— 这是「候选」口径，不是「确认缺字」口径。
- 本轮逐条源图复核后**确认可落 6 条**（另 10 条为重复/异体/非字/位置歧义，不插）：
  - 全书汉字缺字真值（确认口径）= **58 + 6 = 64**（不是 74）；
  - 候选集漏检率的确认口径 = **6 /（58+6）≈ 9.4%**（逐条复核后）；
  - 若按 API 候选上限口径仍是 16/74 ≈ 21.6%（把 10 条不确定项全算作真缺字）。
- 两个口径都写明，避免把「候选」当「确认」；下一轮若继续，可按 6 条确认口径更新全书缺字统计。

## 5. 复现命令

```bash
# 复核裁片
/usr/bin/python3 - <<'PY'
# 见 tmp_vert/battle9/d_fix/ 下 sheet_*.png 与 p{page}_{pos}.png
PY
# 构建 v40
bash tmp_vert/battle9/d_fix/build40.sh
# 门禁
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v40.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \\n' < data/wz7_full/wz7_full_expect_low.txt)"
VERT_TMP=/tmp/vert_wz6_b10 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b10.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b10/vert.tex   # ae9d2f5259e12cff19e680b2a771b37d
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

## 6. 约束声明

- 数据-only：未改 `build_vert.py` / `verify_vert.py` 判据；未 commit/push；token 未出现在任何文件/报告。
- p1560 的试落→移除过程如实记录（第一版 v40 f743933f… +7 → 复核后移除 → 最终 v40 5214c38e… +6）。
