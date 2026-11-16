# _pos_gscale 根因（t355，未交付）

## 实测

- PITCHDBG p69 pass2：total=845.5 cap=792.3 gscale=0.715；p100 total=762.2 gscale=1；p150 total=783.8 gscale=1。
- 失败页确被 gscale 压缩。

## 尝试

1. 估算侧 `_strut_h` 改 `page_pitch(key)-2`：p69 strut_h 580（20/行），pass1 total766.5，但 pass2 `_pos_ratio` 把 total 拉回 845.5，gscale 仍0.715；pitch仍79.1。
2. cap 加大：cap=887.3，p69 gscale=1.000，但 wz3 pitch 仍 **79.5%**，且构建页数出现 936 vs850（build 内部）→ 失败页行距并未因 gscale 解除而修正。
3. 结论：gscale 只压 top_vs/gap，不改逐行 strut；解除压缩不能修正 p69 行距。t355 前提与实测不符。

## 状态

- 所有改动已回退；未交付 wz3_gfix.pdf；未做 wz10/6本回归。
- 未改 gold/punct_eval；未 push/commit。

---

## 9. 2026-11-16 后续：gscale 假设被实验推翻（第 7 轮）

工程师实测：

| 尝试 | 结果 |
|---|---|
| ① 估算侧改 `page_pitch(key)-2` | pass2 的 `_pos_ratio` 把 total 拉回 845.5，gscale 仍 0.715，pitch 仍 79.1% |
| ② cap 加大到 887.3 | p69 **gscale 变 1.000**，但 **pitch 仍 79.5%**；且构建出现 936 vs 850 页漂移 |

**结论：解除压缩不能修行距。**

原因（看渲染代码 L1637-1643）：

```python
if _pp and PF > 13:      # 大字（wz3 PF=14.5）
    bl = round((_pp - 2.0) * _pos_sscale, 1)      # ← 行距由这里定
else:
    bl = round(fnt * 1.34 * _pos_sscale, 1)
_strut = '\\rule{0pt}{%.1fpt}' % round(bl - fnt*0.13, 1)
```

`_pos_gscale` **只作用于 `top_vs` 与段间 `gap`**，不作用于逐行 `bl`/`_strut`。
所以压缩与否不改变行距 —— 行距由 `bl` 单独决定。

**且 `fit_common.py:34` 默认 `env.setdefault('PER_PAGE_PITCH','1')`**，所以 `_pp` 恒生效，
`bl = (_pp − 2.0) × sscale`。

**待确认（下一步唯一未查项）**：`page_pitch('68')` 对 wz3 p69 返回的值。
按 `page_pitch` 实现推：OCR 行中心差中位 ≈63.4px × 72/DPI(200) = **22.8pt** → `bl = 20.8`
→ 预期行距 20.8，但实测 **24.75**。差 3.95pt 无法用现有公式解释。

→ **必须 dump 生成的 TeX**（p69 段的 `\vspace` 与 `\rule` 序列），不能再静态推算。
（`build_geom.py` 由 `fit_common` 以 `capture_output=True` 调用，stdout 被吞，需写文件。）

---

## 10. 七轮假设的完整记录（供后续避免重复）

| 轮 | 假设 | 结果 |
|---|---|---|
| 1 | 标定 baseline 偏差 | ❌ ghbq +3.3% / wz4 +6.0% 都 PASS |
| 2 | 行数不符 | ❌ 10 页差 −5 行 |
| 3 | 交替行距 | ❌ alt_ratio ≤0.14 |
| 4 | OCR 行距噪声 | ❌ wz1 CV 74.6% 都 PASS；wz2 CV 10.7% 最差 |
| 5 | 门禁误判 | ❌ 产物确实有缺陷 |
| 6 | 书眉/首块按源 y | ❌ 不影响 `total`，被 gscale 压回 |
| 7 | **`gscale` 压缩是主因** | ❌ **解除压缩后 pitch 仍 79.5%** |

**唯一已确认为真的**：`total=845.5 > cap=792.3 → gscale=0.715` 确实存在于失败页，
但它影响的是顶部与段间距，**不是行距** —— 所以它是「伴随现象」而非「根因」。
