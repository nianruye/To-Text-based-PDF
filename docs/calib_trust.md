# 标定可信度三档（t344）

## 判据（兜底后 calib.json）

- fail：`font.pt ∉ [6,20]` 或 `baseline/font ∉ [1.2,2.0]` 或 `selfcheck.verdict == 'fail'`
- warn：有 warnings 或 selfcheck=warn
- ok：其余

`CALIB_STRICT` 默认 0：fail 只告警；`CALIB_STRICT=1` 时 fail 在发布前 return 非 0，不写产物。

## 各书 trust

| 书 | font | ratio | trust | warnings |
|---|---:|---:|---|---|
| wz9 | 10.5? | — | ok | 无 |
| ghbq | 16.5 | 2.06? | fail | baseline_font_ratio_out,toc_low_sample |
| wz8 | 15.41 | 1.746 | warn | full_sample_low,page_size_overcoverage |

（ghbq 的 ratio warning 来自源书既有 calib；默认 strict0 仍构建。）

## 验收

- wz9 report `calib_trust=ok`，gate.md「标定可信度：ok」；stdout gate PASS。
- ghbq report `calib_trust=fail`（告警），104 页逐页文本 diff=0；默认 strict0 不拒绝。
- strict 构造：
  `HORIZ_FONT_MEASURE=2 FONT_SCALE=1 CALIB_STRICT=1 scan2pdf ... --out /tmp/wz9_strict2.pdf`
  → exit **6**，`标定可信度 fail: font=2.0 ratio=10.3`，**无产物**。
- wz8 font=15.41 → **warn**（非 fail）。
- 产物 output/uploaded/wz9_trust.pdf + report/gate。

未改 gold/punct_eval；未 push/commit。
