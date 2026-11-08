# battle20 独立验收（t96 · round 2 · v50 修正版）

> 验收人：验证评审员（独立验证方，round 2）　日期：2026-11-08 14:44–15:01
> 基线：HEAD `84d6b95`（未 commit 工作树）；**未改实现代码、未改 fix JSON/数据、未 commit/push**
> 对象：t91（battle20 复核落库）+ **t95（repair round 2：F1/F2 修复）**
> 主产物：`output/wz7_full/wz7_full_v50.pdf`（md5 **`21216d14e7a085240b0938ad004900bd`**，1748 页）
> 方法：自己重跑 build50、自己裁 9 条闭号 insert + 8 条 missing_char + 5 条不命中 + 8 条括号源图、自己逐页算字符量/引号/QSF、自己跑 wz6/pytest。

---

## 0. 结论

**PASS（round 2 可交付）**：t95 的 F1/F2 修复有效——**p1254 重复插入、p1444 跨列错位均已拒掉**；最终 **9 条闭号 insert** 全部源图角形成立、位置正确；`﹂﹂` 回到 **237**（v49 基线）；字符量 v49 931,184 → v50 **931,193（+9）**，8 页逐页可对；括号 271 条 0 落、抽样 8 条均为引号/圆括号内引用短语；门禁 PASS、wz6 零回归、pytest 617。

**核心数字**：
- 复跑 build50 → md5 `5fd18f4a3063840b4cd6cb3ebdac8ad8` ≠ 交付 `21216d14…`（/ID），但 **size 109,995,282 相同、metadata 相同、1748 页文本/行 bbox/内容流逐页 0 差异** → 内容完全等价；已恢复交付物 `21216d14…`。
- verify_vert（--expect-low）**PASS**：1748=1748 / **931,193** / 差异>80 字页 18（预期 18/非预期 0）/ 整页丢失 0 / 越界 span 0+矢量 0。
- **闭号 9 条**：p230/358×2/898/1122/1229/1234/1256/1354——源图均为闭号角形；v49→v50 文本逐条 `…。﹂` 插入位置正确；**p1254 `君。﹂唱`、p1444 `老婆﹂不一時` 不再重复**（F1/F2 修复生效）。
- **`﹂﹂`**：v49 **237** → v50 **237**（修复前 239）✓；`「「`/`」」`=0/0；空对残留 0。
- **字符量**：v49 931,184 → v50 **931,193（+9）**；8 页（p230 +1 / p358 +2 / p898/1122/1229/1234/1256/1354 各 +1）与报告 §5 一致；insert 9 + replace 0 + 删除 0。
- **括号**：271 条 0 落；抽样 8 条（一六一七/翫物喪志/福善禍淫/人的文學/福醫/倡妓/南西廂記/蘭陵）源图均为**引号/圆括号内引用短语/书名**，无 `〔〕` 竖笔；全书 `︹/︺` 计数 v49=v50（76/74），名表外未被误改。
- **不命中 5 条**：p30（开引号方向）、p63/p64（无角形）、p1254（raw 邻闭号）、p1444（上一列末已闭号）——不落理由成立。
- wz6 `vert.tex` **`ae9d2f5259e12cff19e680b2a771b37d`** + verify PASS；pytest **617 passed**（150.02s）。

**残留/发现（低，不阻塞）**：
- **F1（低，报告口径）**：报告 §9 称 QSF「v49→v50 无差异」，实测 qsf.json **925 vs 926 项**——p1256 少 1 条 `。→replace`（因 insert 改变上下文）；**append 697 不变，「闭合不补」未破**，但措辞应改为「1 条 replace 因上下文消失，append 不变」。
- **F2（低，报告/字段）**：`bracket_verify.json` 271 条 reason 仍**全为 `bracket_shape_fail`**，报告 §4 称有两层 reason（`name_not_in_table` / `bracket_shape_fail`）；0 落结论不受影响，但字段/措辞需一致（名表判定未在 JSON 体现）。
- **F3（说明）**：构建 md5 重跑为 `5fd18f4a…`（与交付 `21216d14…` /ID 不同、内容 0 差异）。

---

## 1. PASS/FAIL 总表（5 项）

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 独立复跑 build50 → v50；verify exit 0（1748 / 丢失 0 / 越界 0+0）；wz6 `ae9d2f52…` + PASS；pytest ≥616 | **PASS** | build50 exit 0；重跑 md5 `5fd18f4a…` ≠ `21216d14…`（/ID），size/metadata/1748 页文本/bbox/内容流 0 差异 → 内容等价；verify **PASS**：1748=1748 / 931,193 / 18 预期 / 丢失 0 / 越界 0+0；wz6 `ae9d2f52…` + PASS；pytest **617 passed** |
| 2 | 独立抽检 ≥20 条落库条目（闭号为主）：自裁源图核对角形判据，确认「该落、落对位置」；不命中抽 5 条确认理由 | **PASS（附 F1/F2 低）** | 9 条闭号 insert 源图均角形、产物位置正确（`…。﹂`）；p1254/p1444 已不重复；3 旧 insert（p308/p967/p1625）与 8 missing_char（p50/85/105/141/213/231/247/276）源图正确；5 不命中（p30/p63/p64/p1254/p1444）理由成立 |
| 3 | 括号类：抽 ≥8 条确认〔〕名表+形状判据成立；名表外未被误改 | **PASS（附 F2 低）** | 8/8 源图为引号/圆括号内引用短语/书名，无 `〔〕` 竖笔；271 条 0 落；`︹/︺` 计数 v49=v50（76/74），无越界改动；reason 字段全 bracket_shape_fail（F2 低） |
| 4 | 字符量对账 v49→v50 = 插入数（逐页）；无双引号/空括号新增；QSF「闭合不补」未破 | **PASS（附 F1 低）** | +9 与 8 页逐页一致 ✓；`﹂﹂` **237=237**（修复前 239）✓；`「「`/`」」`=0、空对 0 ✓；QSF append **697 不变**（闭合不补未破）✓；qsf 925 vs 926（1 条 replace 消失，F1 低） |
| 5 | 报告 docs/battle20_acceptance.md：PASS/FAIL + 字节绑定 + 抽样表 + 残留；不改实现代码、不 commit | **PASS** | 本文件；未改 `src/`、fix JSON/数据、`output/`（v50 已恢复原字节）；未 commit（HEAD `84d6b95`） |

---

## 2. 字节绑定（开工 14:44 = 收尾 15:01）

| 文件 | 开工 | 收尾 | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `0a90f6eb9f3138c6ea1909418ac88ba8d3264fe6bf2296b3b23922e2dcf68447` | 同左 | 一致（t95 未改实现代码） |
| `tmp_vert/battle20/build50.sh` | `8c08188c8ba2ae59b9aba082a7f07b3c80c0b15a4fa5e6575c4c247a6182ff5a` | 同左 | 一致 |
| `docs/battle20_ink_verify.md`（t95 版） | `c484d50920b18728d0b8c0ff4e3d2f473c7d67ef61db71b5b60306eb3fddec27` | 同左 | 一致（116 行） |
| `src/test/unit/test_missed_fix_insert_replace.py` | `64c4baa6dcf7449298cce5f6a74c09534e90dd967556ae063cfa249532fb96bc` | 同左 | 一致 |
| `docs/vert_taskF_missed_fix.json` | `b7e7d0067d7fc56b24ec001058badbb7d461e4fba91b48a985fd936a81c16109` | 同左 | 一致（540 项，9 条 dual_ocr_ink insert） |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致（判据未改） |
| `output/wz7_full/wz7_full_v50.pdf` | md5 `21216d14…` | md5 `21216d14…` | 已恢复原交付字节 |

---

## 3. 复跑与门禁

- `bash tmp_vert/battle20/build50.sh`：`BUILD_EXIT=0` → `FIXTEXIT=0`（14:55:47）→ 重跑 md5 **`5fd18f4a3063840b4cd6cb3ebdac8ad8`**。
- 与交付物 `21216d14…` 对比：size **109,995,282 = 109,995,282**；metadata 相同；**1748 页文本/行 bbox/内容流逐页 0 差异** → 内容完全等价（/ID）。
- 已恢复 `output/wz7_full/wz7_full_v50.pdf` 为 **`21216d14e7a085240b0938ad004900bd`**。
- verify_vert（`--expect-low`）：**exit 0 / PASS**：1748=1748；931,193÷942,935=98.8%；差异>80 字页 **18（预期 18/非预期 0）**；整页丢失 **0**；越界 span **0** + 矢量 **0**。

---

## 4. 落库条目抽检（20 条：9 闭号 + 3 旧 insert + 8 missing_char）

### 4.1 9 条闭号 insert（源图自裁）

| 页 | 源图 | v50 文本 | 判定 |
|---|---|---|---|
| p230 | 列尾闭号角形 | `…不管你。﹂二人` | ✓ |
| p358（2 条） | 角形 ×2 | `…夫妻。﹂一面`、`…隔院聽。﹂這` | ✓ |
| p898 | 角形 | `…銀子。﹂一面收` | ✓ |
| p1122 | 角形 | `…來。﹂一面掌` | ✓ |
| p1229 | 角形 | `…我知道。﹂﹄這` | ✓ |
| p1234 | 列首角形 | `…那里來？﹂春梅道` | ✓ |
| p1256 | 角形 | `…早超身。﹂︵摩訶` | ✓ |
| p1354 | 角形 | `…吃盃。﹂不一時` | ✓ |

- **p1254/p1444 修复核对**：v50 `閻君。﹂唱`（不再 `﹂﹂`）、`老婆﹂不一時`（不再 `﹂﹂`）✓ —— F1/F2 拒插生效（`repair_round2.json` 14 条 rejected，含 p1254 `F1_product_or_raw_adjacent`、p1444 跨列）。

### 4.2 3 条旧 insert + 8 条 missing_char

- p308/p967/p1625：源图 `﹁`+独立「一」，产物 `「一…` ✓。
- p50 竊 / p85 峴 / p105 逕 / p141 謄 / p213 颳 / p231 人 / p247 不 / p276 人：源图 cell **8/8 见对应字** ✓。

### 4.3 不命中 5 条

| 页 | 理由 | 源图核对 |
|---|---|---|
| p30 | no_corner | 开引号方向（竖臂在左），非闭号 ✓ |
| p63 | no_corner | 无角形（`註十`）✓ |
| p64 | no_corner | 无角形（开引号方向）✓ |
| p1254 | F1 相邻闭号 | 源图角形已在 `」` 处，重复插会 `﹂﹂` → 拒 ✓ |
| p1444 | F2 跨列 | 源图角形在上一列末，下一列首无角形 → 拒 ✓ |

---

## 5. 括号类抽检（8 条）

| 页 | 名 | 源图 | 判定 |
|---|---|---|---|
| p29 | 一六一七 | `（一六一七）` | 圆括号年份 → 不落 ✓ |
| p29 | 翫物喪志 | `「翫物喪志」` | 引号引用 → 不落 ✓ |
| p30 | 福善禍淫 | `「福善禍淫」` | 同上 ✓ |
| p30 | 人的文學 | `「人的文學」` | 同上 ✓ |
| p31 | 福醫 | 非方括号 | 不落 ✓ |
| p31 | 倡妓 | 引号内 | 不落 ✓ |
| p57 | 南西廂記 | `「南西廂記」` | 书名引号 → 不落 ✓ |
| p64 | 蘭陵 | `「蘭陵」` | 同上 ✓ |

- `bracket_verify.json`：applied **0** / rejected **271**；reason 全 `bracket_shape_fail`（F2 低：报告称两层 reason，JSON 未体现 `name_not_in_table`）。
- 全书 `︹/︺` 计数 v49 = v50（76/74），**名表外未被误改** ✓。

---

## 6. 字符量 / 引号 / QSF

- **v49 931,184 → v50 931,193（+9）**；逐页 8 页（p230 +1 / p358 +2 / p898/1122/1229/1234/1256/1354 各 +1）与报告 §5 完全一致。
- `「「`/`」」`=**0/0**；空对残留 **0**；`﹁﹁`=7；**`﹂﹂`=237（v49 237，修复前 239）** ✓。
- **QSF**：`/tmp/wz7_v49_run/qsf.json`（926 项，append 697）vs `/tmp/wz7_v50_run/qsf.json`（925 项，append 697）：**append 不变 = 闭合不补未破**；唯一差异 p1256 少 1 条 `。→replace`（insert 改变上下文）→ 报告 §9「无差异」不准确（F1 低）。

---

## 7. wz6 / pytest / 判据 / token

- **wz6**：`VERT_TMP=/tmp/vert_wz6_b20v2` 构建 → `BUILD_EXIT=0`；`vert.tex` md5 **`ae9d2f5259e12cff19e680b2a771b37d`**；verify **PASS**（231=231 / 97.2% / 2 预期 / 丢失 0 / 越界 0+0）。
- **pytest**：**617 passed**（900 warnings，150.02s）。
- **判据**：`git diff src/test/verify_vert.py` 空；sha256 = HEAD `cc8b6937…`。
- **token**：报告/脚本/测试无 token 字面；**未 commit**（HEAD `84d6b95`）。

---

## 8. 复现命令

```bash
cd /opt/test
bash tmp_vert/battle20/build50.sh
md5sum output/wz7_full/wz7_full_v50.pdf          # 21216d14…
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v50.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
# 字符量/双闭号
/usr/bin/python3 - <<'PY'
import fitz,re
a=fitz.open('output/wz7_full/wz7_full_v49.pdf'); b=fitz.open('output/wz7_full/wz7_full_v50.pdf')
def t(d,p): return re.sub(r'\s','',d[p-1].get_text())
print('delta', sum(len(t(b,i+1))-len(t(a,i+1)) for i in range(len(a))))
print('diff pages',[i+1 for i in range(len(a)) if t(a,i+1)!=t(b,i+1)])
print('﹂﹂', ''.join(t(b,i+1) for i in range(len(b))).count('﹂﹂'))
PY
# 9 条闭号源图（自裁）
/usr/bin/python3 - <<'PY'
import json,fitz
fix=json.load(open('docs/vert_taskF_missed_fix.json'))['items']
src=fitz.open('source_pdf/wz7.pdf')
for x in [q for q in fix if q.get('class')=='insert' and q.get('source')=='dual_ocr_ink']:
    p=x['page']; c=x['col']
    pm=src[p-1].get_pixmap(matrix=fitz.Matrix(11,11),clip=fitz.Rect(c[0]-3,c[1]-3,c[2]+3,c[1]+90),colorspace=fitz.csGRAY)
    pm.save('/tmp/close_p%d.png'%p)
PY
VERT_TMP=/tmp/vert_wz6_b20v2 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b20v2.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b20v2/vert.tex          # ae9d2f52…
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

---

## 9. 纪律

- 只新增 `docs/battle20_acceptance.md`；未改 `src/`、fix JSON/数据、`output/`（v50 已恢复原字节）；未 commit/push。
- 日志：`/tmp/b20v2/`（build50.log、v50_verify.log、wz6_build/verify.log、pytest.log）；自裁裁片：`/tmp/b20v2/sheet_close9.png`、`sheet_missing4.png`、`sheet_bracket8.png`、`sheet_rejected5.png`。

---

## 10. 结论

**round 2 PASS**：t95 的 F1（相邻闭号）与 F2（跨列边界）修复有效——p1254/p1444 两条错误 insert 已拒掉，`﹂﹂` 回到 237；9 条闭号 insert 源图角形 + 位置全部正确；字符量 +9 逐页对得上；括号 271 条 0 落（抽样 8/8 为引用短语）；门禁/wz6/pytest 全过。

**下一轮可选（低）**：
1. **F1**：报告 §9 改为「qsf 925 vs 926：1 条 replace 因 insert 上下文消失，append 697 不变」；
2. **F2**：`bracket_verify.json` 的 reason 区分 `name_not_in_table` / `bracket_shape_fail`，与报告 §4 一致；
3. 闭号判据命中率仍低（9/1060 = 0.85%），替换 2,379 条待字符仲裁轮。
