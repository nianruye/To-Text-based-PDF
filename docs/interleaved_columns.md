# 图文混排分列结构（t364 第1步）

## 根因

L1260–1285 同视觉行合并 `else` 大间隙也并进同一 row，图注 text 被拼到正文，x 丢失。

## 修法（仅结构）

- `col_split` 配置（wz10 开启）：同 y 且 gap>80px 的行不合并，生成独立 `is_col_frag` 行，保存 `_src_x0/_src_y0`。
- 分列行不计 `_strut_h/_gap_h`，渲染循环跳过（第2步再做定位）。
- 其余书/未开启 col_split 走原合并。

## 结构证据（COLDBG）

wz10 p58 独立行：
```
p58 x0=683.38 y0=1174.83 '河南洛阳出土隋'
```
命中页 p50/p51/p58（p16 目录不标记）。

## 零回归

- wz10 **60 页**，gate PASS。
- 其他书无 `col_split`，路径不变。
- 产物 output/uploaded/wz10_split.pdf（不含视觉定位改动）。

未改gold/punct_eval；未push/commit。
