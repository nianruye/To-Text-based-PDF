# CC 任务简报模板（9 段，缺一段不接受）

> 用法：`cp docs/CC_BRIEF_TEMPLATE.md docs/vert_taskXX_brief.md` 后逐段填写。
> 每一段都来自实战教训，不要删段。

## ① 当前基线（必填）

- 当前 HEAD：`<commit>`
- 测试基线：**必须 424 passed**（`/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q`）
- 上一个交付产物：`output/wz7_full/wz7_full_v6.pdf`，md5 `<...>`

## ② 现象（用户原话 + 实测数字）

> 用户原话直接引用，不要转写。
> 实测数字必须是自己跑出来的，不是推测的。

## ③ 根因证据链

> 代码位置 + 日志原文，逐条引用。
> **没有证据链就不要往下写** —— 先写探针把数值打出来。

## ④ 修法方向

> 明确到函数名 + 行号。允许 CC 提出更好的方案，但必须先说明为什么不按给定方向做。

## ⑤ 禁止事项（必填）

- 不许改 `src/test/verify_vert.py` 的判据或阈值（门禁不许放宽）
- 不许并发跑全书重建（VERT_TMP 冲突 + 抢 CPU）
- 不许 `git reset` / `git checkout --`（历史上丢过改动）
- 不许自行决定数据口径（见 ⑦）
- 不许动横排管线任何文件

## ⑥ 验收命令（可直接复制执行 + 期望输出）

```bash
# 1. 单测
/usr/bin/python3 -m pytest src/test/unit src/test/invariants -q     # 期望 424 passed
# 2. 目标页
...
# 3. 全书
bash src/pipelines/rebuild_v6.sh
```

## ⑦ 数据口径契约（由提出方写死，执行方不许自定）

```
ps3 数据（wz7_full_ps3.json）   = 1-based 页号
lines/coords（spotting）        = 0-based 索引（页 p 用 str(p-1)）
坐标单位                        = px（= pt × 2）
字符量统计                      = 剔除空格/全角空格/换行
```

## ⑧ 反向验证（改完必须验的「另一侧」）

> 修 A 页必须同时验 B 页；修这本书必须同时验第二本书；
> 开一个开关必须验关掉时的行为。
> **这是最贵的一条教训** —— 只验目标页导致过回归。

## ⑨ 交付物 + 预算

- 代码 commit（原子提交，中文描述 + Refs）
- `docs/vert_taskXX_report.md`：**必须含探针数值**（改前/改后各一组）
- `docs/HANDOFF.md` 更新
- `--max-turns 160`；**一次会话只做一个可独立验收的子目标**

---

## 硬性作业规范

**先探针，后改码。** 改代码前必须先写一个探针/自检脚本，把关键数值打出来并写进报告。
**没有数值证据的修改一律不接受。**

---

## 附：CC 启动范式（实测，缺一步启动就失败）

```bash
cd /opt/test
PROMPT="${PREAMBLE}$(cat docs/vert_taskXX_brief.md)"
echo "$PROMPT" > /tmp/cc_xx_prompt.txt

IS_SANDBOX=1 setsid nohup claude -p "$PROMPT" \
  --max-turns 160 \
  --output-format stream-json --verbose \
  --dangerously-skip-permissions \
  > /tmp/vert_taskXX.jsonl 2>&1 < /dev/null &
```

**三个必踩的坑**：

| 坑 | 现象 | 修法 |
|---|---|---|
| root 下 `--dangerously-skip-permissions` 被拒 | `cannot be used with root/sudo privileges` | **前置 `IS_SANDBOX=1`** |
| `$(cat prompt)` 在 `bash -c '...'` 里被吃 | prompt 为空 / 启动即退 | prompt 写脚本文件或先 `echo` 到 `/tmp` 再 `$(cat 该文件)` |
| 前台长 `sleep` 等 CC | terminal 超时 SIGTERM 连带杀掉 CC 进程组 | 只用 `background=true` 且 CC 本身走 `setsid nohup` |

**监控**：`stream-json` 写到 `/tmp/vert_taskXX.jsonl`，`ccwatch` 只 glob `/tmp/vert_task*.jsonl`。

**结束判据**：文件末尾出现 `"subtype":"success"`（成功）或 `"subtype":"error_max_turns"`（撞上限）。

---

## 附：等价性验证口径（踩过）

| 比什么 | 是否有效 | 原因 |
|---|---|---|
| `.tex` 源码 md5 | ✅ | 确定性文本 |
| **PDF md5** | ❌ | 内嵌 CreationDate，每次构建都不同 |
| PDF 逐页文本 / 字符量 | ✅ | 内容等价 |
