# promptLabel='spotting' 影响审计（t269）

> 只读实验 + 文档；未改产品渲染/gold/punct_eval；未 commit。
> 数据：ghbq 8 页（p14/15/23/27/30/50/80/100，`src/test/bench/content_gold_h_v1.json`）。

## 1. 现状复现（P0，`spotting`）

- 请求：`useLayoutDetection=false, promptLabel='spotting'`（当前产品行为，17 字段显式 payload）。
- 输出：`output/ghbq/ocr_promptlabel_exp/P0/lines.json`（=t268 E1 lines），md5 `53d35799e294749356cce14ab867c1b4`。
- 与当前产品 lines `output/ghbq_full/_ocr_ghbq/ghbq_spotting_lines.json` 对应 8 页比对：**6/8 页完全一致；p79/p99 不一致**（另一个批次），说明服务端/数据版本有漂移，后续比较只用同次实验。
- 文本级：TP286/FP53/FN36，P0.8437/R0.8882（t265 旁路口径）。

## 2. 核心对照（P1，`promptLabel='ocr'`）

- 同 8 页、其余参数完全同；只把 promptLabel 改 `ocr`（文档合法值/默认）。
- **输出 lines 全部为空：8/8 页 0 行**（`output/ghbq/ocr_promptlabel_exp/P1/lines.json`）。
- 文本级：TP0/FP0/**FN322**，P0/R0；逐类全部 FN（quote_open 60、quote_close 36、comma 133、period 72…）。
- 原因：`useLayoutDetection=false` + `promptLabel='ocr'` 返回的是文档解析结果，不含 spotting 的 `spotting_res`；我们的 `convert_raw_dir` 只从 spotting schema 取 lines。
- 判定：**改成 `'ocr'` 不是更好，而是把文本行全部丢失** → 不改产品；`'spotting'` 是触发 spotting schema 的内部/未文档化取值，尽管不在官方四枚举内，当前不可替换。

## 3. layout 模式 promptLabel 文档断言（L0/L0b/L1）

同一 8 页、`useLayoutDetection=true`：
| 组 | promptLabel | layout md5 | 备注 |
|---|---|---|---|
| L0 | ocr | `b090ff9f…` | 首次 |
| L0b | ocr | `b9b23d0f…` | **同请求重跑，md5 不同** |
| L1 | table | `b9b23d0f…` | 与 L0b 相同 |

- L0≠L0b（同 promptLabel 两次不同），说明**服务端同请求存在非确定性**（差异为块文本空格/order 细节，语义块基本一致）。
- L1 与 L0b 相同、但 L0 不同 → **不能据此断言 layout 忽略 promptLabel**；本实验只能结论「无法区分 prompt 效应与服务端非确定性」。
- 因服务端非确定性，layout 模式两个 `'ocr'` 是否白费**未证实**；建议用同一请求重复 2-3 次取共识后再判定（本任务只跑 L0/L0b/L1）。

## 4. t265 max_pixels 结论的澄清

- t265 A（maxPixels=2822400）md5 `a6218135…`，B（5644800）md5 `d7c3b1b8…`。
- t268 E0（**同 A 参数 2822400**）md5 `d7c3b1b8…`，与 B 相同。
- 同参数在不同批次出现两种输出，且本次 P0 与产品 lines 也有 2/8 页差异 → **服务端/批次非确定性存在**。
- 因此 t265 的「max_pixels 提高 → R +28pp」**不能归因于 max_pixels，应撤回该因果结论**；t265 的 B/D 提升至少部分是批次随机/服务端变化。需要控制重复（同参数 2-3 次）后再评估 max_pixels。本任务不重做 t265，仅记录判断。

## 5. 代码处理

- **不改 `modes`**：`('spotting', False, 'spotting')` 保留（改成 ocr 会 lines 全空）。
- 不加非法枚举校验（会把当前合法可用的内部值拒绝，导致产品停止）；在代码注释中注明该值是 spotting schema 触发器，非官方四枚举。
- 未改 payload 默认、产品渲染、gold、punct_eval。

## 6. 输出

- P0：`output/ghbq/ocr_promptlabel_exp/P0/lines.json` + request_payload.json
- P1：`output/ghbq/ocr_promptlabel_exp/P1/lines.json`（空）+ request_payload.json
- L0/L0b/L1：`lines.json`（layout JSON）+ request_payload.json；原始 layout 见各组 `ghbq_layout.json`
- jobId：P0=`114057079388958720`（t268 E1），P1=`114058817474052096`，L0/L0b/L1 见各组 jobs.json
