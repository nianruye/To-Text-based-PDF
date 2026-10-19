# HANDOFF —— 当前状态（CC 每次会话结束必须更新）

> 这是 CC 有 `git reset` 丢改动记录后加的保险。**每次会话结束必须更新本文件。**

## 当前基线

- HEAD：本次 taskCH 提交（`refactor: 目录页排版分支重构`）
- 测试：**424 passed**
- 交付产物：`output/wz7_full/wz7_full_v6.pdf`
  - taskCH：md5 `3c0be39fa02cef9644d1f94070dda0c6`，110,075,788 字节
  - 上一个 v11（tag `v11-toc-order`）：md5 `873fba95619f8bb57edbe30bee33b271`
  - verify：页数 1748=1748 / 字符量 **931,781** = 98.6% / 非预期 0 / 整页丢失 0 / 越界 0
  - 目录列序：p54 ✓ p563 ✓（`check_toc_order.py`）；p69 的 1 处逆序是**v11 就有的**
    正文页误判（导论正文提到「第X回」），非本次引入
- wz6 零回归：`vert.tex` md5 `c2fdfa0e63614e61364a74f02d13ac1d`（A/B/C 三组全等）

## 开关默认值（P1 已翻转，全部默认开）

```
VERT_AB_FIX / VERT_NF_JOIN_MED / VERT_NF_BODY_TIER / VERT_NF_DROP_MARGIN
VERT_NF_TOC / VERT_NF_TITLE_OUT / VERT_PARA_MARK / VERT_MONO
VERT_NF_TOC_BRANCH（taskCH 新增：目录独立分支，默认开；=0 回到旧路径做 A/B）
```
不再需要手打 env。要复现旧行为用 `=0`。

## 已完成（近期）

| 项 | commit | 验收 |
|---|---|---|
| **taskCH 目录页分支重构**：原始行形态判据 + `_toc_puts` 独立路径；删「补列」补丁 | 本次提交 | p53 有「導讀」/ p54 0 逆序 / p55 递增 / p563 180 字 / 全书 931,781 / verify PASS / wz6 md5 不变 |
| 段首圈点 ⊙ 做进渲染端（首格让位，SIZE 1.357 / DY 0.855）| `2ce0570` | p43 ⊙ 394.0-423.9（29.9pt），不叠字 |
| 补列 + 全列做槽（槽数不足根因）| `ed7b74f` | p54 列序 ✓ p563 不回归（taskCH 后目录页不再依赖它们） |
| `check_toc_order.py`（目录列序校验，补 verify 盲区）| `ed7b74f` | p54 精确命中逆序 |
| `check_col_order.py`（通用列序，实验性）| `ed7b74f` | — |
| PP-StructureV3 全书数据（1736 页，1-based）| 数据 | `data/wz7_full/wz7_full_ps3.json` |

## 未完成（按优先级）

1. **墨迹↔文本对账层** —— 1,529 处 / 2,761 字（0.292%），只有圈点一类有处置
2. 目录页列内长点线的格数还原受 `GAP_MAX=4` 限制（p563 页码已更贴近源书，但未逐格精确）
3. `check_toc_order.py` 对正文页 p69（导论提到「第X回」）误报 1 处逆序（v11 同样误报；
   工具判据按治理要求未改）
4. **124+ commit 未 push**

## 已知盲区（验证体系）

`verify_vert.py` 只验「字在不在」，不验「字在哪」：p54 三列互换时字符量 379/381、越界 0，**全部 PASS**。
已加 `check_toc_order.py` 补，但它只覆盖目录页（含「第X回」≥5 的页）。

## 数据口径（别踩）

```
ps3 1-based 页号 / lines+coords 0-based 索引 / 坐标 px = pt×2 / 统计剔空格
```

## PP-StructureV3 结论（别再试换 OCR）

- 框数相当（28,287 vs 29,284 = 96.6%），但**文字量只有 1/3**（308,002 vs 944,251）
- 正文页严重漏字（p500 237 vs 686）
- **只能当「哪里可能有一列」的定位参考，不能当判据** —— 它自己识别噪声太大（21.9% 置信 <0.5）
- p53「導讀」：taskCH 复核发现打补丁后的 spotting 数据**本身就有**这一行
  （key52 行 3，x573.5-608.5 / y234.2-334.8）；旧产物的缺列是 note 误分类导致，不是 OCR 缺数据
