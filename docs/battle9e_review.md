# battle9 终审报告（t43 · v39/v40：破折号 + 16 条普查）

> 审查人：横排工程师（独立审查）　时间：2026-11-06 15:31–15:5x
> 审查对象：t40（v39：p57 破折号 + p186/p147）、t41（v40：16 条普查复核落库）与 t42 验收报告
> 基线：HEAD `accf3f8`（PR #2 已合并 battle6–8）+ 未提交 battle9 数据/报告
> 本报告是唯一新增文件；未改实现代码 / fix JSON / output，未 commit；所有复跑产物写 `/tmp/t43`。

---

## 0. 结论（先行）

**verdict = pass（v40 可交付、可作 battle9 基线）**。独立复跑与逐条复核全部通过：

| 项 | 结果 |
|---|---|
| build40 复跑 | BUILD/FIX exit 0；重建 md5 `57517c04…` ≠ 交付物 `5214c38e…`，但 1748 页文本/words bbox 逐页 0 差异、text md5 `d11524fb…` 相同、metadata（1970）/size 109,996,941 全同 → **内容等价**（R1=/ID） |
| v40 verify_vert | **PASS**：1748=1748 / **931,190**÷942,935=98.8% / 差异>80 字页 18（18 预期 / 0 非预期）/ 整页丢失 0 / 越界 span 0+矢量 0 |
| wz6 | `vert.tex` `ae9d2f5259e12cff19e680b2a771b37d` 逐字节 + verify **PASS**（231=231 / 68,412÷70,373=97.2% / 差异 2 预期 / 丢失 0 / 越界 0+0） |
| pytest | **590 passed** |
| 字符量 diff | v38→v39 **3 页 +6**（p57/p147/p186 各 +2）；v39→v40 **6 页 +6**（p68/p932/p1219/p1419/p1678/p1703 各 +1）；v38→v40 **9 页 +12**，无其他页变化 |
| v39 三条 | p57 `論金瓶梅這部書——導讀`（468 字、2 个 `—`、恰 1 条竖线）；p186 `餓鬼﹂。蘇東坡`；p147 `吃！﹂，那婦人`；**p1330 未落库**（fix JSON 无 `絃`，v40 无 `分，他每`） |
| v40 16 条 | 6 条落库（p68 尚 / p932 人 / p1219 纖 / p1419 慌 / p1678 步 / p1703 四）上下文全对、无双字；10 条不落理由成立（详见 §4） |
| fix JSON | missing_char **150** = 69（battle7）+72（battle8b）+3（v39）+6（v40）；无 p1330 絃 / 无 p1560 / 0 重复 key |
| 判据 / token | `verify_vert.py` = HEAD（`git diff` 空）；完整 token 及前 12 字符 0 命中；未 commit |

**非阻塞残留**：
- **R1**：build40 非字节可复现（md5 每次不同；text/bbox/metadata/size 全同，差异为 PDF /ID）。
- **R2**：p57 线宽 2.784pt vs 源墨 5.25pt —— spec 15 已知 R2（`VERT_DASH_RULE_W=src` 可切源宽），不影响位置/长度验收。
- **R3**：p1678 源「投步」、产物「抄步」——插入 `步` 正确；`投→抄` 是既有 OCR 误读，不在本轮 missing_char 范围。
- **R4（PR 合并前文档修正，不影响 v40 产物）**：`spec/vertical/16_missing_char_insert.md` 是 t39 按 battle6–8 写的，
  battle9 数据新增了 `ch` 为 **2 字符**的 3 条（`——`、`」。`、`」，`）与两个新 `source`（`api_strip_punct`、`api_strip_census`），
  与 spec 的「ch 只允许单字符」「source 仅 api_strip/api_strip_quote」「插入后长度 +1」「ch 为 —/——/多字符 → 不属于
  missing_char」「fix JSON 无 ch=——」**直接冲突**（spec L33/L35/L38/L82/L98）。建议在 battle9 合并前同步更新 spec 16
  （ch 允许 1–2 字符、按 `len(ch)` 计增量；source 枚举补两项；dash 条款改为「punct 类 `——` 可落 missing_char，由
  dash rule 画一条线」；补 punct 字段族），否则合并后契约与数据矛盾。

---

## 1. 字节绑定（实现文件与报告）

| 文件 | 开工 15:31:43 | 收尾 15:4x | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `9b8f87e21712a425f6a946b2427d3265a9196fafabb32331af9759ceae40c263` | 同左 | 一致（数据-only，t32 后未改） |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致且 = `git show HEAD:src/test/verify_vert.py`（判据未改） |
| `docs/vert_taskF_missed_fix.json` | `28f74a2e8d7f3be3415da058755a8a22dc5c0038bd262a8804e5083e32c1d598` | 同左 | 一致 |
| `docs/battle9_fix.md` | `247cdc6b514bdd225dec7b38e01805597c9e98228edb277974261811439b63f7` | 同左 | 一致 |
| `docs/battle9d_census_fix.md` | `aa3665aada5ea7cd1b79ab7e55ca29ff4e02bf0275fadebcae3c0076335ac9ae` | 同左 | 一致 |
| `docs/battle9e_acceptance.md` | `34eb648ddf55c0a241d80cf07b64063aee85e25bb1e20b7bdc4a66d0c26af2d2` | 同左 | 一致 |
| `tmp_vert/battle9/d_fix/build40.sh` | `495a14e50181c1d093845267b6b2fa652fb84fe52266789473d1534e6253dd15` | 同左 | 一致 |

> HEAD `accf3f8`；审查期间仓库源文件写入仅 `docs/battle9e_review.md`；未 commit。

---

## 2. 独立复跑

- v40 交付物：md5 **`5214c38e031904e264d131155cfe57d9`**；verify PASS（931,190 / 98.8% / 18 预期 / 0 / 0+0）。
- 等价 build40（SOURCE_DATE_EPOCH=0，OUT 重定向 `/tmp/t43/wz7_full_v40.pdf`，不覆盖交付物）：
  BUILD/FIX exit 0，md5 `57517c04ba40655915b5b22a47ed6ffe`（t42 重跑为 `6e4a6b7c…`，每次 /ID 不同）；
  1748 页 text/words bbox 逐页 0 差异、text md5 `d11524fbec8b754bd10300a6748c6ac8` 相同、metadata（1970）与
  size 相同；重建物 verify PASS（931,190 / 18 / 0 / 0+0）→ **内容等价**（R1）。
- v38→v39→v40 逐页 diff：3 页 +6 / 6 页 +6 / 合并 9 页 +12，页码与 t40/t41 记录一致，无其他页变化。
- wz6：`/tmp/t43/wz6_run/vert.tex` = `ae9d2f52…`；verify PASS（231=231 / 97.2% / 2 / 0 / 0+0）。
- pytest：**590 passed**（17.90s）。

---

## 3. v39 三条（p57 / p186 / p147；p1330 未落库）

### 3.1 p57 真破折号

- 数据：`missing_char` page=57 pos=7 `ch='——'`（source=api_strip_punct，2 字符）。
- 文本层：v40 p57 含 `論金瓶梅這部書——導讀`（2 个 `—`，页面 468 字 = v38 466 +2，可搜）。
- 产物竖线（fitz `get_drawings()`）：**恰好 1 条**，`x=830.005`、`y=736.497–816.497`、长 **80.0**、线宽 **2.784**。
- 源墨自裁（8×，cell [792.0,424.3,866.7,449.6] 附近，长游程法）：阈值 150 → xc **829.812**、y0 **736.5**、
  y1 **816.625**、长 **80.125**、宽 **5.25**；阈值 110 → xc 829.438、y1 815.875、长 79.375、宽 4.5。
- 对照：Δxc **0.19**、Δy0 **0.00**、Δy1 **0.13（150 阈值）**、Δlen **0.125**、Δwidth **2.466（R2 已知）**。
- `dash_segments.json`：`{page:57, x:830.0, n:2, text:'——', y0:736.5, y1:816.5, len:80.0, ratio:1.255,
  w_src:5.0, w_ratio:0.0718, xc:830.0, step:63.72}`；四道判据：长度 80/step=**1.255**（参考 1.26）、
  源线宽/step=5.0/63.72=**0.078**（≤0.35）、线心偏 0.65/63.72=**0.010**（≤0.25）、段长在 [0.45,1.70]×step×2 内。**四道全过**。
- 结论：p57 是源书「——」的**一条**竖线，位置/长度/线心与源墨一致；线宽差为 spec 15 已登记 R2。

### 3.2 p186 / p147

- p186 `ch='」。'` pos=2：v40 文本 `餓鬼﹂。蘇東坡`（+2；无重复）；源图 ﹂ 20.2×9.0 + 。7.5×8.2。
- p147 `ch='」，'` pos=13：v40 文本 `吃！﹂，那婦人`（+2；无重复）；源图 ﹂ 18.7×7.7 + 逗号 4.5×6.8。
- 两条在 fix JSON 均为 2 字符 `ch`，插入后上下文正确、无双字。

### 3.3 p1330 未落库

- fix JSON 中 p1330 只有 battle7 既有 `知`（source=api_strip），**无 `絃`**；v40 p1330 无 `分，他每`；
  源图 cell 仅 3×3pt 噪点（t38 复核），不落库正确。

---

## 4. v40 16 条普查候选（6 落 / 10 不落）

### 4.1 落库 6 条（v39=0 → v40=1）

| 页 | 字 | pos | v40 上下文 | 源图 | 双字检查 |
|---|---|---|---|---|---|
| p68 | 尚 | 12 | `多以尚書` | 尚（源 `多以尚書`，OCR 漏 尚） | 无 `尚尚` |
| p932 | 人 | 16 | `大人家` | 人（源 `大人家`，OCR 漏 人） | 无 `人人` |
| p1219 | 纖 | 35 | `用纖手` | 纖（源 `用纖手`，OCR 漏 纖） | 无 `纖纖` |
| p1419 | 慌 | 32 | `經濟慌` | 慌（源 `經濟慌`，OCR 漏 慌） | 无 `慌慌` |
| p1678 | 步 | 21 | `抄步` | 步（源 `投步`，OCR 漏 步；投→抄 为既有误读） | 无 `步步` |
| p1703 | 四 | 37 | `四制錢` | 四（源 `四制錢`，OCR 漏 四） | 无 `四四` |

6 条均 source=api_strip_census、complete=true、shape/crop 齐全；v39→v40 各 +1，无错位、无双字。

### 4.2 不落 10 条（理由复核）

| 页 | 候选字 | 复核（自裁源图/上下文） | 结论 |
|---|---|---|---|
| p195 | 二 | 源 `武二交跌`；OCR 已有 `二`，插则 `武二二` | 重复，不落 ✓ |
| p207 | 廝 | 源 `小廝`；OCR 为 `小、厮`（异体 厮 + 顿号噪声） | 异体/位置歧义，不落 ✓ |
| p572 | 苦 | 源 `金葉茶匙`（自裁为 茶/香，无 苦） | 源无，不落 ✓ |
| p782 | 們 | 源 `你叫我有甚話`（无 們） | 源无，不落 ✓ |
| p877 | 了 | 源 `了不的了` 即 OCR 文本，无额外 了 | 重复，不落 ✓ |
| p990 | 看 | 源 `來看你看`（已有两个 看） | 重复，不落 ✓ |
| p1270 | 九 | 源为 `一〇〇` 两个圆圈，不是 九 | 非汉字，不落 ✓ |
| p1330 | 絃 | 源为 `泓`（氵+弘），不是 絃 | 非该字，不落 ✓ |
| p1368 | 走 | 源 `走去走` 即 OCR 文本 | 重复，不落 ✓ |
| p1560 | 媽 | 源 `婦媽金`；OCR 误读为 `馮`；插则 `婦媽馮金` 双字 | 重复（OCR 误读），不落 ✓ |

> p1560 曾在第一版 v40 试落并出现 `婦媽馮金`，已从数据移除；最终 v40 无该双字。

### 4.3 与 t37 普查清单对账 / 无 other·nonchar 误落

- t37 `api_battle9.json` 的 `hanzi_list` 共 16 条完整字块（`n_hanzi_complete=16`）；落库 **6**，不落 **10**，与 t41
  `verdicts.json`（land 6 / skip 10）一致；16 条页集合 = {68,195,207,572,782,877,932,990,1219,1270,1330,1368,1419,1560,1678,1703}。
- fix JSON 新增仅 **6 条 api_strip_census + 3 条 api_strip_punct**；`other`（4,934）与 `nonchar`（45）**没有任何一条**
  被写成 missing_char（source 枚举核对：69 api_strip + 72 api_strip_quote + 6 api_strip_census + 3 api_strip_punct = 150）。
- 去重：与既有 141 条按 (page,pos,ch) 0 重复；无同 page/pos 异字；无 p1330 絃、无 p1560、无 `ch=——` 之外的异常。
- 注：t37 任务摘要里「p1219 手」是摘要笔误；`api_battle9.json` 实际候选为 **纖**，t41 落库 `纖` 与之一致。

---

## 5. 判据 / 回归 / token / 纪律

- `verify_vert.py` sha256 `cc8b6937…` = HEAD；`git diff` 空；`build_vert.py` 未改（数据-only）；判据未放宽。
- wz6 `vert.tex` 逐字节 + verify PASS（231=231 / 97.2% / 2 预期 / 0 / 0+0）。
- pytest 590 passed。
- token：完整 token（40 字符）及前 12 字符在 docs/battle9*、fix JSON、tmp_vert/battle9、build40.sh 中 **0 命中**。
- 审查期间仓库源文件写入仅 `docs/battle9e_review.md`；未改实现代码 / fix JSON / output，未 commit（HEAD `accf3f8`）。

---

## 6. 结论

- **产品侧通过**：v39 三条（p57 一条 80.0pt 竖线 + p186/p147 各 +2）与 v40 六条普查汉字逐条有源图证据、
  上下文正确、无双字；16 条候选 6 落 10 不落理由成立；p1330 未落库；无 other/nonchar 误落；
  v40 md5/verify/字符量、wz6 零回归、pytest、判据与 token 全部符合 t40/t41/t42 记录。
- **判定：pass**（v40 可交付、可作 battle9 基线）。R1（字节 md5 /ID）与 R2（p57 线宽）/R3（p1678 既有 OCR 抄/投）
  为已知低级别残留；**R4（spec 16 需补 2 字符 ch / 两个新 source / dash 条款）建议在 battle9 合并前修**，
  不影响 v40 产物与基线。
