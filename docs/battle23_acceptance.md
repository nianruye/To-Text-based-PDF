# battle23 独立验收（t108 · round 3 · v51）

> 验收人：验证评审员（独立验证方，round 3）　日期：2026-11-08 17:51–18:11
> 基线：HEAD `84d6b95`（未 commit 工作树）；**未改实现代码、未改 fix JSON/数据、未 commit/push**
> 对象：t99 + t103 + **t107（repair round 3：全量 name-table 扫描）**
> 主产物：`output/wz7_full/wz7_full_v51.pdf`（md5 **`38d6656bf37720ff0277d7bd74a5d87a`**，1748 页）
> 方法：自己重跑 build51、自己裁源图（10 条 applied replace + 3 条漏落 + p1229）、自己算字符量/引号/括号、自己查证据链、自己跑 wz6/pytest。

---

## 0. 结论

**FAIL（验收不通过）**：t107 的全量扫描把 replace 从 8 条扩到 27 条（+47 字、`︹/︺` 103/101），但**引入 4 条已核实的误落**（源图无括号的普通词/曲牌提及被包上 `︹︺`），且**仍有 3 处源图带括号的行未落**（p1179 r13 / p1180 r3 / p1180 r9）。字符量、门禁、证据链（42/42）本身全对，但文本层 bracket 增删有实质错误。

**核心数字**：
- 复跑 build51 → md5 `24313f99…` ≠ 交付 `38d6656b…`（/ID），但 **size 109,995,705 相同、metadata 相同、1748 页文本/行 bbox/内容流逐页 0 差异** → 内容等价；已恢复交付物 `38d6656b…`。
- verify_vert（--expect-low）**PASS**：1748=1748 / **931,240** / 差异>80 字页 18（预期 18/非预期 0）/ 整页丢失 0 / 越界 span 0+矢量 0。
- **字符量**：v50 931,193 → v51 **931,240（+47）**；长度变化 19 页，文本 diff 21 页（p450/529/530/662/693/702/840/921/985/1160/1179/1180/1222/1229/1247/1254/1271/1420/1470/1510/1567），与报告 §4 一致（+48 裸名 −1 p1229 + 0 长度 3 条）。
- `﹂﹂` **237=237**；`「「`/`」」`=0/0；`︹/︺` 76/74 → **103/101**；空对残留 0。
- **证据链**：fix JSON 42 条落库项（insert 11 + replace 31）→ crop **42/42 存在** ✓；closed 719/719、char 2,379/2,379、bracket 266/271 ✓；`except: pass` 已移除 ✓（t104 的 F2 已修复）。
- wz6 `vert.tex` **`ae9d2f5259e12cff19e680b2a771b37d`** + verify PASS；pytest **618 passed**（180.65s）。

**FAIL 依据 / 发现**：
- **F1（高）误落 4 条**（源图无括号，产物被包 `︹︺`；独立裁片 + 实现者 fs 裁片均一致）：
  - **p529 山坡羊**：源 `名山坡羊兒你聽`（无括号）→ 产物 `名︹山坡羊︺兒你聽`；
  - **p840 折桂令**：源 `有折桂令爲證`（无括号）→ 产物 `有︹折桂令︺為證`；
  - **p921 一封書**：源 `寫一封書，`（"一封書"=a letter，普通词）→ 产物 `寫︹一封書︺，`；
  - **p1470 賺**：源 `哄賺進後邊`（"賺"=诓骗动词）→ 产物 `哄︹賺︺進後邊`。
  → 27 条 replace 中至少这 4 条是 name-table token 命中了普通词语/文中提及，非曲牌名；与报告「源图无括号 29 不落」矛盾。
- **F2（高）漏落 3 处**（源图〔〕、产物未括）：
  - **p1179 r13**：源 `〔滾綉毬〕` → 产物 `﹁滾綉毬﹂`；
  - **p1180 r3**：源 `〔滾綉毬〕` → 产物裸名 `滾綉毬`；
  - **p1180 r9**：同上；报告称「p1180 r3/r9/r16 三行全落（+6）」不实——实际 p1180 +6 = r16 `滾綉毬`(+2) + 2×`倘秀才`(+4)，r3/r9 未落（fix JSON 中这两条 pos=-1 被跳过）。
- **F3（中）p1229**：产物仍 2 个闭号（`？﹂﹄`）vs 源图 1 个墨块；insert 已移除（3→2，= v49 基线），data 层残留（验收原「=1」未达，口径已改「insert 不新增」）。
- **F4（低）**：`bracket_judge.json` 对 p1180 r3 等仍为 shape_fail/未命中，与源图矛盾（判据假阴性未全修）。
- **F5（低）**：报告「201 次出现：已正确 76 / 源图无括号 29 / strict 31 / replace 27」的归类与实际不符（至少 4 条误落、3 条漏落），需以源图逐条复核后重算。

---

## 1. PASS/FAIL 总表（5 项）

| # | 验收项 | 结论 | 实测 |
|---|---|---|---|
| 1 | 独立复跑 build51 → v51；verify exit 0（1748 / 丢失 0 / 越界 0+0）；wz6 `ae9d2f52…` + PASS；pytest ≥617 + 新闸门测试 | **PASS** | build51 exit 0；重跑 md5 `24313f99…` ≠ `38d6656b…`（/ID），size/metadata/1748 页文本/bbox/内容流 0 差异 → 内容等价；verify **PASS**：1748=1748 / 931,240 / 18 预期 / 丢失 0 / 越界 0+0；wz6 `ae9d2f52…` + PASS；pytest **618 passed** |
| 2 | M1：p1229 该处闭号数 = 源图墨块数（1），不再是 3；全书同类扫描 = 0 或逐条说明 | **FAIL（部分）** | insert 已移除（3→2，= v49）✓；源图自裁 **1** 个墨块 → 产物仍多 1（data 层，登记）；口径改「insert 不新增」（F3） |
| 3 | 证据链：落库条目 crop 存在率 100%；closed_verify / char_replace / bracket_verify 按报告口径；`except: pass` 已移除 | **PASS** | fix JSON 42/42 crop 存在（11 insert + 31 replace）；closed 719/719、char 2,379/2,379、bracket 266/271；makedirs+失败即抛、无 except pass（t104 F2 已修） |
| 4 | 括号：p1180 `滾綉毬` 等真阳性已落〔〕；名表外是否还有漏（抽 ≥10 源图）；误落 0 | **FAIL** | 10 条 applied 抽样：6 条正确（p450 尾聲/p693 烏夜啼/p985 東甌令×2/p1222 後庭花/p1254 山坡羊），**4 条误落**（p529/p840/p921/p1470，源图无括号）→ F1；**3 条漏落**（p1179 r13/p1180 r3/r9）→ F2；p1180 r16 已落 ✓；p1322 跳过（无 ︹︹ 嵌套）✓ |
| 5 | 字符量对账：v50→v51 = 移除 + 括号插入（逐页）；报告 docs/battle23_acceptance.md；不改实现代码、不 commit | **PASS（附 F4/F5 低）** | +47 与逐页 19 页（文本 diff 21 页）一致；`﹂﹂` 237；`︹/︺` 103/101；本报告；未改 src/数据/fix JSON/output（v51 恢复原字节）；未 commit（HEAD `84d6b95`） |

---

## 2. 字节绑定（开工 17:51 = 收尾 18:11）

| 文件 | 开工 | 收尾 | 结论 |
|---|---|---|---|
| `src/pipelines/build_vert.py` | `927dc1224b161d032f660ec70e4a0d2ce25207324cc021c5ad706412ae386ad6` | 同左 | 一致（t107 未改实现） |
| `tmp_vert/battle23/build51.sh` | `af741ea025fe6411273c708b4e568fa516e3123de42862088015af255283464c` | 同左 | 一致 |
| `docs/battle23_fix_audit.md`（t107 版） | `3002ef328289d5e85aa7f3ed946914d38d889ef1aa94d7cee6f294c28c855afd` | 同左 | 一致（101 行） |
| `docs/vert_taskF_missed_fix.json` | `34b37a9cb9b1fd42c9a23a81dd593e2fdd6acb9242a033e20b79c7c4d5e25060` | 同左 | 一致（570 项：insert 11 / replace 31） |
| `src/test/unit/test_missed_fix_insert_replace.py` | `b49d454e328fb7be974ecedafa3e9a50cb18ad09047709d76fe31c63fb0abbdc` | 同左 | 一致 |
| `src/test/verify_vert.py` | `cc8b69379212672732fa43628c43c765dda19e5f2758dcc35d6506a2a3e47588` | 同左 | 一致（判据未改） |
| `output/wz7_full/wz7_full_v51.pdf` | md5 `38d6656b…` | md5 `38d6656b…` | 已恢复原交付字节 |

---

## 3. 复跑与门禁

- `bash tmp_vert/battle23/build51.sh`：`BUILD_EXIT=0` → `FIXTEXIT=0`（18:03:01）→ 重跑 md5 **`24313f998ff316ed142ab7ef7371a874`**。
- 与交付物 `38d6656b…` 对比：size **109,995,705 = 109,995,705**；metadata 相同；**1748 页文本/行 bbox/内容流逐页 0 差异** → 内容完全等价（/ID）。
- 已恢复 `output/wz7_full/wz7_full_v51.pdf` 为 **`38d6656bf37720ff0277d7bd74a5d87a`**。
- verify_vert（`--expect-low`）：**exit 0 / PASS**：1748=1748；931,240÷942,935=98.8%；差异>80 字页 **18（预期 18/非预期 0）**；整页丢失 **0**；越界 span **0** + 矢量 **0**。
- 构建日志：`灌入 42 处: insert 11 / replace 27 / 跳过 4`。

---

## 4. M1（p1229）

- fix JSON 无 p1229 insert；v51 `？」﹂﹄五戒` = 2 个（= v49 基线；v50 为 3）→ **不再 3** ✓。
- 自裁源图（p1229 r8 `何幹？` 后 16×）：**1 个**闭号墨块 → 产物仍多 1（patched-lines 符号层，data/ 越界，报告已登记）。
- 验收原文「= 源图墨块数（1）」未达（2≠1）；t103 口径已改「insert 不新增」（F3）。

---

## 5. 证据链（M3）独立核查

| 证据集 | 报告口径 | 实测 | 结论 |
|---|---|---|---|
| fix JSON insert | 11 | crop **11/11** | ✓ |
| fix JSON replace | 31 | crop **31/31** | ✓ |
| closed_verify_fixed | 719/719 | 719/719 ✓ | ✓ |
| char_replace_fixed | 2,379/2,379 | 2,379/2,379 ✓ | ✓ |
| bracket_verify_fixed | 266/271 | 266/271 ✓ | ✓ |
| `except: pass` | 已移除 | makedirs+失败即抛；无 except pass ✓ | ✓ |

> t104 的 F2（crop 10/19）已修复；p1625 路径已改为 battle23。

---

## 6. 括号（M2）独立核对

### 6.1 applied 10 条抽样（源图自裁）

| 页 | 名 | 源图 | 产物 | 判定 |
|---|---|---|---|---|
| p450 | 尾聲 | `〔尾聲〕` | `︹尾聲︺` | ✓ |
| p693 | 烏夜啼 | `〔烏夜啼〕` | `︹烏夜啼︺` | ✓ |
| p985 | 東甌令 ×2 | `〔東甌令〕` | `︹東甌令︺` ×2 | ✓ |
| p1222 | 後庭花 | `〔後庭花〕` | `︹後庭花︺` | ✓ |
| p1254 | 山坡羊 | `〔山坡羊〕` | `︹山坡羊︺` | ✓ |
| **p529** | **山坡羊** | `名山坡羊兒你聽`（**无括号**） | `名︹山坡羊︺兒你聽` | **✗ 误落（F1）** |
| **p840** | **折桂令** | `有折桂令爲證`（**无括号**） | `有︹折桂令︺為證` | **✗ 误落** |
| **p921** | **一封書** | `寫一封書，`（**普通词**） | `寫︹一封書︺，` | **✗ 误落** |
| **p1470** | **賺** | `哄賺進後邊`（**动词**） | `哄︹賺︺進後邊` | **✗ 误落** |

### 6.2 漏落 3 处（FAIL 依据）

| 页/行 | 源图 | v51 | 说明 |
|---|---|---|---|
| **p1179 r13** | **〔滾綉毬〕** | `﹁滾綉毬﹂` | 未落（replace 只到 r3） |
| **p1180 r3** | **〔滾綉毬〕** | 裸 `滾綉毬` | fix JSON pos=-1 被跳过（报告称已落，不实） |
| **p1180 r9** | **〔滾綉毬〕** | 裸 `滾綉毬` | 同上 |

> p1180 构建 +6 = r16 `滾綉毬`(+2) + 2×`倘秀才`(+4)；报告「r3/r9/r16 三行全落」与实测不符。

### 6.3 其它

- p1180 r16 ✓；p1179 r3 ✓；p662/729/1160/1207/1247 0 长度替换 ✓；p1322 跳过（无 ︹︹ 嵌套）✓。
- 误落/漏落并存说明「name-table token 命中」仍需源图 bracket 形状 + 上下文（是否独立名列/曲牌）双重确认。

---

## 7. 字符量 / 引号

- **v50 931,193 → v51 931,240（+47）**；长度变化 19 页；文本 diff 21 页（含 2 条 0 长度），与报告 §4 一致。
- `﹂﹂` **237=237**；`「「`/`」」`=0/0；空对残留 0；`︹/︺` 103/101。

---

## 8. wz6 / pytest / 判据 / token

- **wz6**：`VERT_TMP=/tmp/vert_wz6_b23v3` 构建 → `BUILD_EXIT=0`；`vert.tex` md5 **`ae9d2f5259e12cff19e680b2a771b37d`**；verify **PASS**（231=231 / 97.2% / 2 预期 / 丢失 0 / 越界 0+0）。
- **pytest**：**618 passed**（900 warnings，180.65s）。
- **判据**：`git diff src/test/verify_vert.py` 空；sha256 = HEAD `cc8b6937…`。
- **token**：报告/脚本/测试无 token 字面；**未 commit**（HEAD `84d6b95`）。

---

## 9. 复现命令

```bash
cd /opt/test
bash tmp_vert/battle23/build51.sh
md5sum output/wz7_full/wz7_full_v51.pdf          # 38d6656b…
/usr/bin/python3 src/test/verify_vert.py output/wz7_full/wz7_full_v51.pdf \
  data/wz7_full/wz7_full_spotting_coords.json data/wz7_full/wz7_full_spotting_lines_patched.json \
  --src-pdf source_pdf/wz7.pdf --expect-low "$(tr -d ' \n' < data/wz7_full/wz7_full_expect_low.txt)"
# 字符量/括号/误落上下文
/usr/bin/python3 - <<'PY'
import fitz,re
a=fitz.open('output/wz7_full/wz7_full_v50.pdf'); b=fitz.open('output/wz7_full/wz7_full_v51.pdf')
def t(d,p): return re.sub(r'\s','',d[p-1].get_text())
print('delta',[(i+1,len(t(b,i+1))-len(t(a,i+1))) for i in range(len(a)) if t(a,i+1)!=t(b,i+1)])
for p,n in [(529,'山坡羊'),(840,'折桂令'),(921,'一封書'),(1470,'賺'),(1180,'滾綉毬')]:
    s=t(b,p); i=s.find(n); print(p,repr(s[max(0,i-10):i+len(n)+10]))
PY
# 源图（p529/p840/p921/p1470 + p1179 r13/p1180 r3/r9；自裁）
/usr/bin/python3 - <<'PY'
import json,fitz
L=json.load(open('data/wz7_full/wz7_full_spotting_lines_patched.json'))
C=json.load(open('data/wz7_full/wz7_full_spotting_coords.json'))
src=fitz.open('source_pdf/wz7.pdf')
for p,r in [(529,12),(840,9),(921,12),(1470,16),(1179,13),(1180,3),(1180,9)]:
    t=str(L[str(p-1)][r]).replace('\n',''); b=C[str(p-1)][r]
    xs=[q[0]/2.0 for q in b]; ys=[q[1]/2.0 for q in b]; x0,y0,x1,y1=min(xs),min(ys),max(xs),max(ys)
    src[p-1].get_pixmap(matrix=fitz.Matrix(10,10),clip=fitz.Rect(x0-6,y0-6,x1+6,y1+6),colorspace=fitz.csGRAY).save('/tmp/chk_p%d_r%d.png'%(p,r))
PY
VERT_TMP=/tmp/vert_wz6_b23v3 /usr/bin/python3 src/pipelines/build_vert.py \
  data/wz6/wz6_spotting_lines.json data/wz6/wz6_spotting_coords.json /tmp/wz6_b23v3.pdf source_pdf/wz6.pdf
md5sum /tmp/vert_wz6_b23v3/vert.tex               # ae9d2f52…
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q
```

---

## 10. 纪律

- 只新增 `docs/battle23_acceptance.md`；未改 `src/`、fix JSON/数据、`output/`（v51 已恢复原字节）；未 commit/push。
- 日志：`/tmp/b23v3/`（build51.log、v51_verify.log、wz6_build/verify.log、pytest.log）；自裁裁片：`/tmp/b23v3/sheet_applied10.png`、`focus_applied.png`、`p641_金字經.png`、`p1233_尾聲.png`。

---

## 11. 结论与须修

**FAIL**：t107 的全量扫描虽然把 +47 字与 `︹/︺` 103/101 做出来了，且证据链 42/42 修复到位，但 **4 条误落 + 3 条漏落**——文本层 bracket 语义错误，不能交付。

**must-fix**：
1. **F1（高）** 撤回/复核 27 条 replace：至少 p529 山坡羊 / p840 折桂令 / p921 一封書 / p1470 賺 源图无括号（普通词/文中提及），需用「名独立成列 + 源图括号形状 + 上下文」三条件重筛；误落一律不落。
2. **F2（高）** 补齐漏落：p1179 r13 / p1180 r3 / p1180 r9（源〔滾綉毬〕）；修正 p1180 pos=-1 跳过逻辑（引号包裹名应归一 `「名」→︹名︺` 而非跳过）。
3. **F3（中）** p1229 仍 2 vs 源 1（data 层），需 data 层修或正式改验收口径。
4. **F4/F5（低）**：shape 判据对 p1180 r3 仍假阴性；报告「201 次出现」归类（76/29/31/27）与实际不符，需按源图逐条复核后重算。
