# 本地扫描书还原操作台

## 启动

```bash
cd /opt/test
/usr/bin/python3 -m uvicorn tools.local_console:app --host 127.0.0.1 --port 8765
```

打开 `http://127.0.0.1:8765/`。**只绑定 127.0.0.1**，不对外网开放。

## 页面

### 成果列表

列出 ghbq / wz1 / wz2 / wz3 / wz4 / wz6 / wz7：

- 页数、字符量：从 PDF 读取
- gate / pitch：从 `<out>.gate.json` 或 `<out>.report.json` 读取；缺失显示「未构建」
- 下载链接
- 重建按钮

### 重建

`POST /build/{book}`：

- 调 `src/tools/scan2pdf.py`，使用已有 OCR 数据 + `--skip-ocr --data-dir data/<book>`
- ghbq 额外 `--layout`
- 输出固定到 `output/local_console/<book>.pdf`
- 全局单 worker 队列，任务串行
- 完成后列表显示新 gate

### 上传新书

`POST /upload`（multipart）：

- `file`：PDF，上限 500MB
- `book`：清洗为 `[A-Za-z0-9_-]`，最长 40
- `token_file`：默认 `/tmp/paddle_token`
- 存到 `uploads/<book>.pdf`
- 调 `scan2pdf.py`，**不带** `--skip-ocr` / `--data-dir`，自动跑 OCR + 校准 + 门禁
- 输出固定到 `output/uploaded/<book>.pdf`

token 文件不存在时页面明确返回 400「缺少 OCR token」，不静默失败。

### 任务状态

`GET /task/{id}` 显示四态（排队中/构建中/完成/失败）、已用时长、最后 20 行日志；成功后可下载。

## 安全/限制

- 只支持本机；不提供公网认证/多用户隔离
- 所有构建串行（并发会破坏共享 /tmp 产物；实测 wz4 0 页、wz3 12 页）
- 单任务超时 2 小时
- 上传上限 500MB；输出路径固定，不接受用户任意路径
- 不修改任何管线代码；只新增 shell

## 实测

- 服务：`127.0.0.1:8765` 启动成功，`GET /` 200
- 重建 ghbq：`POST /build/ghbq` → 14.9s 完成，104 页，gate **PASS**，pitch **98.9%**
- 缺 token 上传：`POST /upload` + `token_file=/tmp/no_such_token` → **400**，页面明确提示
- 上传 `/tmp/wz2_p1_6.pdf` + `/tmp/gh_token`：任务 171.7s 后失败，`scan2pdf` 报 `OCR 失败（exit 5）`。`/tmp/gh_token` 内容是 `github_pat_...`，不是 Qianfan OCR token；**成功上传 E2E 需要正确的 Qianfan token，当前环境未提供**。

截图：当前环境无 Chromium/Playwright/wkhtmltoimage，未生成首页截图；`GET /` 的 HTML 已通过 curl 200 验证。请在本机浏览器打开 `http://127.0.0.1:8765/` 查看。

## 为什么不做成公网服务

- 构建是重 CPU/LaTeX 任务，无认证/配额/多租户隔离
- 全局限流为单任务串行，公网会排队
- 上传 PDF 涉及版权与数据安全
- 需要先补认证、对象存储、任务持久化、杀毒/内容校验

## 2026-11-14 追加：实时进度

用户反馈「构建中 117 秒、暂无日志，不知道执行到哪一步」。已改为 **Popen 逐行读取子进程输出**：

- 任务页实时显示：状态 / 阶段 / 已用秒数 / 书 / 类型 / PID / 输出路径
- 阶段由日志动态识别：`OCR / 版面分析`、`排版 / 校准`、`门禁 / 校验`、`收尾`
- 日志从「仅结束后显示」改为 **最近 100 行实时刷新**；页面最多保留 600 行
- 子进程无输出时，页面仍显示「构建中 + 已用时间」，不再空白
- 实测 rebuild ghbq：11.9s 时显示 `构建中 / OCR 版面分析`，13.1s 完成；日志逐行可见
- 更新代码后需重启 uvicorn；重启会丢失内存中的进行中任务，旧任务链接会 404，需重新提交
