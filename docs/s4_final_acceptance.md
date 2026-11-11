
### 6. t230 最终结论（captain 更正后）

- **wz2 不是 S4 回归，不需要改产品代码。**
- wz2 是**古籍校注本**（3027 处〔〕校注标记、双行夹注小字），行距天然不规则，`VERIFY_PITCH_FLOOR=85` 的 pitch 判据不适用；前端 1-6 是封面/版权/目录/出版缘起，当前树 `--pages 1-6` **PASS 100%**（6=6）。
- t222 的 wz2 REJECT 66.7 来自错误分支/错误样本；`--pages 20-30` 是**校注页**不是正文，且 `--pages` 子集下 verify 的 coords/lines 全量问题与 `_logical_lines` 无关。
- 实测：wz2 20-30 源行高中位28.5→tol14.25；源raw36→logical29，输出raw68→logical29；源pitch28.86 vs 输出29.4（后续页28.8/26.7，p_err≈8%），聚类前后均约29；**没有 17+ 容差污染或20%绝对塌陷**。
- p7/p11/p104：`去空白 + 源优先修正白名单` 登记；p7 `·`、p11 TOC dotfill、p104 DuXiu 断行/连字符；无字面丢失。
- 99.6：**不是硬阈值**；gate 判据是 `VERIFY_PITCH_FLOOR=85`；wz4 99.5 为 PASS 下的 pitch 样本差，登记 low。
- **S4 产品代码零改动**；本附录只更新验收记录。
