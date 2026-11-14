#!/usr/bin/env python3
"""本地扫描书还原操作台。

只做壳：所有构建都 subprocess 调用 src/tools/scan2pdf.py，不 import/修改管线。
运行：
  /usr/bin/python3 -m uvicorn tools.local_console:app --host 127.0.0.1 --port 8765
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

ROOT = Path(__file__).resolve().parents[1]
PYTHON = "/usr/bin/python3"
SCAN2PDF = ROOT / "src" / "tools" / "scan2pdf.py"
UPLOAD_DIR = ROOT / "uploads"
UPLOAD_OUT = ROOT / "output" / "uploaded"
BUILD_OUT = ROOT / "output" / "local_console"
MAX_UPLOAD = 500 * 1024 * 1024
TASK_TIMEOUT = 2 * 3600

# 已支持的书。product 是当前验收产物；重建写到 output/local_console/<book>.pdf。
BOOKS: Dict[str, Dict[str, Any]] = {
    "ghbq": dict(source="source_pdf/ghbq.pdf", data="output/ghbq_full/_ocr_ghbq",
                 product="output/ghbq_full/ghbq_final_v30.pdf", layout=True),
    "wz1": dict(source="source_pdf/wz1.pdf", data="data/wz1",
                product="output/wz1/wz1_t303.pdf"),
    "wz2": dict(source="source_pdf/wz2.pdf", data="data/wz2",
                product="output/rebuild_v2/wz2_fix2.pdf"),
    "wz3": dict(source="source_pdf/wz3.pdf", data="data/wz3",
                product="output/wz3/wz3_t304.pdf"),
    "wz4": dict(source="source_pdf/wz4.pdf", data="data/wz4",
                product="output/rebuild_v2/wz4_v2.pdf"),
    "wz6": dict(source="source_pdf/wz6.pdf", data="data/wz6",
                product="output/wz6/wz6_vert_full.pdf"),
    "wz7": dict(source="source_pdf/wz7.pdf", data="data/wz7_full",
                product="output/wz7_full/wz7_full_v51.pdf"),
}

app = FastAPI(title="扫描书还原操作台", version="1.0")
_tasks: Dict[str, Dict[str, Any]] = {}
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="build")


def _clean_book(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", (name or "").strip())[:40].strip("_")
    if not s:
        raise HTTPException(400, "书名清洗后为空；只允许字母/数字/下划线/短横线")
    return s


def _cmd_base(book: str, src: Path, out: Path) -> list[str]:
    return [PYTHON, str(SCAN2PDF), "--input", str(src), "--book", book, "--out", str(out)]


def _meta(out: Path) -> Dict[str, Any]:
    """读 gate/report/PDF 页数/字符量；失败字段给 None。"""
    m: Dict[str, Any] = dict(page_count=None, chars=None, gate="未构建", pitch=None, height=None,
                             gate_path=None, report_path=None)
    if not out.exists():
        return m
    try:
        import fitz
        doc = fitz.open(out)
        m["page_count"] = doc.page_count
        m["chars"] = sum(len(p.get_text().replace("\n", "")) for p in doc)
        doc.close()
    except Exception:
        pass
    gp = Path(str(out) + ".gate.json")
    rp = Path(str(out) + ".report.json")
    g = None
    if gp.exists():
        try: g = json.loads(gp.read_text(encoding="utf-8"))
        except Exception: g = None
    if g is None and rp.exists():
        try: g = json.loads(rp.read_text(encoding="utf-8")).get("gate")
        except Exception: g = None
    if rp.exists():
        m["report_path"] = str(rp.relative_to(ROOT))
    if g:
        m["gate_path"] = str(gp.relative_to(ROOT)) if gp.exists() else None
        m["gate"] = g.get("verdict_effective") or g.get("verdict") or ("PASS" if g.get("pass_") else "REJECT")
        mt = g.get("metrics", g)
        m["pitch"] = mt.get("pitch_ok_pct")
        m["height"] = mt.get("height_ok_pct")
    return m


def _book_view(book: str) -> Dict[str, Any]:
    cfg = BOOKS[book]
    build = BUILD_OUT / f"{book}.pdf"
    out = build if build.exists() else (ROOT / cfg["product"])
    m = _meta(out)
    return dict(book=book, out=str(out.relative_to(ROOT)) if out.exists() else cfg["product"],
                exists=out.exists(), **m)


def _stage_of(line: str) -> str:
    s = line.lower()
    if "ocr" in s or "spotting" in s or "layout" in s:
        return "OCR / 版面分析"
    if "构建" in line or "fit_positional" in s or "xelatex" in s or "pass1" in s or "pass2" in s:
        return "排版 / 校准"
    if "gate" in s or "verify_" in s:
        return "门禁 / 校验"
    if "完成" in line or "exit=0" in s:
        return "收尾"
    return "运行中"


def _append_log(t: Dict[str, Any], line: str) -> None:
    line = line.rstrip("\n")
    t.setdefault("lines", []).append(line)
    # 页面最多保留 600 行；API 取尾部 100 行
    if len(t["lines"]) > 600:
        del t["lines"][:len(t["lines"]) - 600]
    t["log"] = "\n".join(t["lines"][-100:])
    t["last_log_at"] = time.time()
    st = _stage_of(line)
    if st != "运行中":
        t["stage"] = st


def _run_task(tid: str) -> None:
    t = _tasks[tid]
    t["status"] = "构建中"
    t["stage"] = "启动子进程"
    t["started"] = time.time()
    t["last_log_at"] = t["started"]
    t["log"] = ""
    t["lines"] = []
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        _append_log(t, "$ " + " ".join(str(x) for x in t["cmd"]))
        p = subprocess.Popen(t["cmd"], cwd=str(ROOT), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
        t["pid"] = p.pid
        deadline = time.time() + TASK_TIMEOUT
        import selectors
        sel = selectors.DefaultSelector()
        sel.register(p.stdout, selectors.EVENT_READ)
        while True:
            if time.time() > deadline:
                p.kill()
                _append_log(t, "超时（2h），已终止子进程")
                t["exit"] = -9
                break
            events = sel.select(timeout=1.0)
            for _key, _mask in events:
                line = p.stdout.readline()
                if line:
                    _append_log(t, line)
                elif p.poll() is not None:
                    break
            if p.poll() is not None:
                # flush 管道剩余内容
                rest = p.stdout.read()
                if rest:
                    for ln in rest.splitlines():
                        _append_log(t, ln)
                break
        t["exit"] = p.wait()
        out = Path(t["out"])
        if out.exists() and out.stat().st_size > 0:
            t["status"] = "完成" if t["exit"] == 0 else "完成（门禁/构建有警告，可下载）"
        else:
            t["status"] = "失败"
        t["stage"] = "结束"
    except Exception as e:
        t["status"] = "失败"
        t["stage"] = "异常退出"
        _append_log(t, f"{type(e).__name__}: {e}")
    finally:
        t["ended"] = time.time()


def _submit(cmd: list[str], out: Path, kind: str, book: str) -> str:
    tid = uuid.uuid4().hex[:12]
    _tasks[tid] = dict(id=tid, kind=kind, book=book, cmd=cmd, out=str(out),
                       status="排队中", created=time.time(), started=None, ended=None,
                       log="", exit=None)
    _executor.submit(_run_task, tid)
    return tid


def _task_json(t: Dict[str, Any]) -> Dict[str, Any]:
    now = t.get("ended") or time.time()
    start = t.get("started") or now
    return dict(id=t["id"], kind=t["kind"], book=t["book"], status=t["status"],
                stage=t.get("stage", "排队中"),
                elapsed=round(now - (t.get("started") or t["created"]), 1),
                log=t.get("log", ""), exit=t.get("exit"), out=t.get("out"),
                cmd=t.get("cmd", []), pid=t.get("pid"))


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    rows = []
    for b in BOOKS:
        v = _book_view(b)
        pages = v.get("page_count") if v.get("page_count") is not None else "—"
        pitch = "—" if v.get("pitch") is None else f'{v["pitch"]}%'
        chars = "—" if v.get("chars") is None else f'{v["chars"]:,}'
        gate = v.get("gate") or "未构建"
        link = f'<a href="/download/{b}">下载</a>' if v.get("exists") else '<span class="muted">无产物</span>'
        rows.append(f'''<tr><td><b>{b}</b></td><td>{pages}</td><td>{gate}</td><td>{pitch}</td><td>{chars}</td>
<td>{link}</td><td><form method="post" action="/build/{b}"><button>重建</button></form></td></tr>''')
    return HOME.replace("__ROWS__", "\n".join(rows))


@app.post("/build/{book}")
def build(book: str):
    if book not in BOOKS:
        raise HTTPException(404, "未知书名")
    cfg = BOOKS[book]
    out = BUILD_OUT / f"{book}.pdf"
    cmd = _cmd_base(book, ROOT / cfg["source"], out)
    cmd += ["--data-dir", str(ROOT / cfg["data"]), "--skip-ocr", "--force"]
    if cfg.get("layout"):
        cmd.append("--layout")
    tid = _submit(cmd, out, "rebuild", book)
    return RedirectResponse(f"/task/{tid}", status_code=303)


@app.post("/upload")
async def upload(file: UploadFile = File(...), book: str = Form(...),
                 token_file: str = Form("/tmp/paddle_token")):
    book = _clean_book(book)
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "只接受 .pdf")
    tok = Path(token_file)
    if not tok.is_file():
        return HTMLResponse(f'''<h2>缺少 OCR token</h2><p>token 文件不存在：<code>{tok}</code></p>
<p>请先放置 token 文件，或在上传页填写正确路径。</p><p><a href="/">返回</a></p>''', status_code=400)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dst = UPLOAD_DIR / f"{book}.pdf"
    size = 0
    try:
        with dst.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD:
                    f.close(); dst.unlink(missing_ok=True)
                    raise HTTPException(413, "文件超过 500MB")
                f.write(chunk)
    finally:
        await file.close()
    if not dst.exists() or dst.stat().st_size < 5 or dst.open("rb").read(5) != b"%PDF-":
        dst.unlink(missing_ok=True)
        raise HTTPException(400, "不是有效 PDF")
    out = UPLOAD_OUT / f"{book}.pdf"
    cmd = _cmd_base(book, dst, out)
    cmd += ["--token-file", str(tok), "--force"]
    tid = _submit(cmd, out, "upload", book)
    return RedirectResponse(f"/task/{tid}", status_code=303)


@app.get("/task/{tid}", response_class=HTMLResponse)
def task_page(tid: str):
    if tid not in _tasks:
        raise HTTPException(404, "任务不存在")
    return TASK.replace("__ID__", tid)


@app.get("/api/tasks/{tid}")
def task_api(tid: str):
    if tid not in _tasks:
        raise HTTPException(404, "任务不存在")
    return JSONResponse(_task_json(_tasks[tid]))


@app.get("/download/{book}")
def download(book: str):
    if book not in BOOKS:
        raise HTTPException(404, "未知书名")
    v = _book_view(book)
    p = ROOT / v["out"] if v.get("out") else None
    if not p or not p.exists():
        raise HTTPException(404, "尚未构建")
    return FileResponse(p, filename=p.name, media_type="application/pdf")


@app.get("/download/task/{tid}")
def download_task(tid: str):
    if tid not in _tasks:
        raise HTTPException(404, "任务不存在")
    p = Path(_tasks[tid]["out"])
    if not p.exists():
        raise HTTPException(404, "尚未生成")
    return FileResponse(p, filename=p.name, media_type="application/pdf")


HOME = """<!doctype html><html lang="zh"><meta charset="utf-8">
<title>扫描书还原操作台</title>
<style>
body{font-family:-apple-system,Segoe UI,"Noto Sans CJK SC",sans-serif;max-width:1100px;margin:30px auto;padding:0 18px;color:#222}
h1{font-size:22px} table{width:100%;border-collapse:collapse;margin:16px 0}
th,td{padding:9px;border-bottom:1px solid #e5e5e5;text-align:left;font-size:14px}
th{background:#fafafa;color:#666;font-weight:600} .muted{color:#999}
button{padding:5px 12px;border:1px solid #bbb;background:#fff;border-radius:5px;cursor:pointer}
button:hover{background:#f4f4f4} .box{border:1px solid #ddd;border-radius:8px;padding:16px;margin:18px 0}
input[type=file],input[type=text]{padding:7px;border:1px solid #bbb;border-radius:5px}
.note{color:#666;font-size:13px;line-height:1.7} code{background:#f2f2f2;padding:1px 4px;border-radius:3px}
</style>
<h1>扫描书还原操作台</h1>
<p class="note">本机工具：只绑定 127.0.0.1；所有构建串行执行；重建使用已有 OCR 数据，上传新书会跑完整 OCR。</p>
<table><thead><tr><th>书</th><th>页数</th><th>gate</th><th>pitch</th><th>字符量</th><th>产物</th><th>操作</th></tr></thead>
<tbody>__ROWS__</tbody></table>
<div class="box"><h2>上传新书（完整 OCR）</h2>
<form method="post" action="/upload" enctype="multipart/form-data">
<p>PDF：<input type="file" name="file" accept="application/pdf" required></p>
<p>书名：<input type="text" name="book" placeholder="例如 mybook" required></p>
<p>OCR token 文件：<input type="text" name="token_file" value="/tmp/paddle_token" size="40"></p>
<p class="note">token 不存在时会明确拒绝，不会静默失败。上限 500MB。</p>
<button type="submit">上传并开始构建</button></form></div>
<div class="box"><h2>构建状态</h2><div id="last" class="note">提交重建/上传后跳到进度页。</div></div>
"""

TASK = """<!doctype html><html lang="zh"><meta charset="utf-8">
<title>任务 __ID__</title><style>
body{font-family:-apple-system,Segoe UI,"Noto Sans CJK SC",sans-serif;max-width:900px;margin:30px auto;padding:0 18px}
pre{background:#111;color:#ddd;padding:14px;border-radius:7px;overflow:auto;max-height:420px;font-size:12px}
.note{color:#666;font-size:13px} a{color:#1668c1}
</style>
<h1>任务 <code>__ID__</code></h1>
<p>状态：<b id="st">读取中…</b>　阶段：<b id="stage">—</b>　已用：<span id="el">—</span></p>
<p class="note" id="meta">命令/输出读取中…</p>
<p id="dl" class="note"></p>
<h3>执行日志（最近 100 行，实时刷新）</h3><pre id="log">读取中…</pre>
<p><a href="/">← 返回成果列表</a></p>
<script>
async function poll(){
  const r=await fetch('/api/tasks/__ID__'); const d=await r.json();
  document.getElementById('st').textContent=d.status;
  document.getElementById('stage').textContent=d.stage||'—';
  document.getElementById('el').textContent=d.elapsed+' 秒';
  document.getElementById('log').textContent=d.log||'（暂无日志；子进程可能尚未输出，已用时间仍在增加）';
  document.getElementById('meta').textContent='书: '+d.book+' | 类型: '+d.kind+' | PID: '+(d.pid||'—')+' | 输出: '+d.out;
  if(d.status.startsWith('完成')){
    document.getElementById('dl').innerHTML='<a href="/download/task/'+d.id+'">下载产物 PDF</a>';
  }
  if(d.status==='失败'||d.status.startsWith('完成')){ clearInterval(t); }
}
let t=setInterval(poll,2000); poll();
</script>
"""
