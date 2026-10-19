# HANDOFF —— 当前状态（CC 每次会话结束必须更新）

> 这是 CC 有 `git reset` 丢改动记录后加的保险。**每次会话结束必须更新本文件。**

## 当前基线

- HEAD：`ed7b74f` + P1 翻转开关（待提交）
- 测试：**424 passed**
- 交付产物：`output/wz7_full/wz7_full_v6.pdf`
  - v11（tag `v11-toc-order`）：md5 `873fba95619f8bb57edbe30bee33b271`，110,076,200 字节
  - verify：页数 1748=1748 / 字符量 931,770 = 98.6% / 非预期 0 / 整页丢失 0 / 越界 0
  - 目录列序：p54 ✓ p563 ✓（`check_toc_order.py`）
- wz6 零回归：`vert.tex` md5 `c2fdfa0e63614e61364a74f02d13ac1d`

## 开关默认值（P1 已翻转，全部默认开）

```
VERT_AB_FIX / VERT_NF_JOIN_MED / VERT_NF_BODY_TIER / VERT_NF_DROP_MARGIN
VERT_NF_TOC / VERT_NF_TITLE_OUT / VERT_PARA_MARK / VERT_MONO
```
不再需要手打 env。要复现旧行为用 `=0`。

## 已完成（近期）

| 项 | commit | 验收 |
|---|---|---|
| 段首圈点 ⊙ 做进渲染端（首格让位，SIZE 1.357 / DY 0.855）| `2ce0570` | p43 ⊙ 394.0-423.9（29.9pt），不叠字 |
| 补列 + 全列做槽（槽数不足根因）| `ed7b74f` | p54 列序 ✓ p563 不回归 |
| `check_toc_order.py`（目录列序校验，补 verify 盲区）| `ed7b74f` | p54 精确命中逆序 |
| `check_col_order.py`（通用列序，实验性）| `ed7b74f` | — |
| PP-StructureV3 全书数据（1736 页，1-based）| 数据 | `data/wz7_full/wz7_full_ps3.json` |

## 未完成（按优先级）

1. **P3 目录分支重构** —— 目录逻辑散在 5 个步骤，判据互相矛盾（见 `docs/vert_taskCH_brief.md`）
2. **p53 缺「導讀」列** / p55 列序 —— 用户直接反馈
3. **墨迹↔文本对账层** —— 1,529 处 / 2,761 字（0.292%），只有圈点一类有处置
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
- 正文页严重漏字（p500 237 vs 686）；稀疏页（目录）反而多检出（p53 的「導讀」）
- **只能当「哪里可能有一列」的定位参考，不能当判据** —— 它自己识别噪声太大（21.9% 置信 <0.5）
