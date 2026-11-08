# src/test/bench — 标点/内容评测基准集（base 页）

来源：battle22 系列人工标注（源图裁片为证据，裁片本体在 `tmp_vert/bench/crops/`，不入库）。
- `punct_gold_v1_base.json`：wz6/wz7 两书共 18 页的标点标注（引号/括号/破折号/圈码/句读/书名号/省略号），每条含 page/column/char_pos/class/value/form/bbox/evidence。
- `content_gold_v1_base.json`：同 18 页的全文转录（源图为准）。
- `punct_gold_v1.json`：早期 demo 子集（p57/p703/p1179），仅供单测。
- **heldout 页（wz2/wz4 共 4 页）不在本仓库**：完整 gold 与密封页号保存在本地 `data/punct_eval/`（`data/` 被 .gitignore 忽略），避免公开密封集。

评测口径见 `spec/governance/PUNCT_EVAL.md`（v1.3）与 `spec/governance/CONTENT_EVAL.md`（v1.1）。
