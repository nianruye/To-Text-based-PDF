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
LOGS_DIR = BUILD_OUT / "logs"
TASKS_JSON = BUILD_OUT / "tasks.json"

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


def _save_tasks() -> None:
    BUILD_OUT.mkdir(parents=True, exist_ok=True)
    keep = sorted(_tasks.values(), key=lambda t: t.get("created", 0), reverse=True)[:10]
    data = []
    for t in keep:
        x = {k: v for k, v in t.items() if k not in ("lines",)}
        x["log"] = "\n".join(t.get("lines", [])[-500:])
        data.append(x)
    TASKS_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _load_tasks() -> None:
    if not TASKS_JSON.exists():
        return
    try:
        for t in json.loads(TASKS_JSON.read_text(encoding="utf-8")):
            t["lines"] = (t.get("log") or "").splitlines()
            _tasks[t["id"]] = t
    except Exception:
        pass


_load_tasks()
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
    try:
        lp = t.get("log_path")
        if lp:
            with open(lp, "a", encoding="utf-8") as lf:
                lf.write(line + "\n")
    except Exception:
        pass
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
        try:
            import fitz
            src = Path(t.get("source") or "")
            if src.exists():
                _d = fitz.open(src); t["src_pages"] = _d.page_count; _d.close()
            if out.exists():
                _d = fitz.open(out); t["out_pages"] = _d.page_count; _d.close()
            if t.get("src_pages") is not None and t.get("out_pages") is not None:
                t["page_diff"] = t["out_pages"] - t["src_pages"]
        except Exception:
            pass
        # 从日志抓 scan2pdf 的明确页数错误（比只看 exit 更有信息）
        _pm = re.search(r"页数不 1:1:\s*(\d+)\s*vs\s*(\d+)", t.get("log", ""))
        if _pm:
            t["out_pages"], t["src_pages"] = int(_pm.group(1)), int(_pm.group(2))
            t["page_diff"] = t["out_pages"] - t["src_pages"]
            t["page_note"] = f"页数不 1:1: 源 {t['src_pages']} / 产物 {t['out_pages']} / 差异 {t['page_diff']}"
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
        _save_tasks()


def _submit(cmd: list[str], out: Path, kind: str, book: str, source: Optional[Path] = None) -> str:
    tid = uuid.uuid4().hex[:12]
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logp = LOGS_DIR / f"{tid}.log"
    _tasks[tid] = dict(id=tid, kind=kind, book=book, cmd=cmd, out=str(out), source=str(source or ''),
                       status="排队中", created=time.time(), started=None, ended=None,
                       log="", log_path=str(logp), exit=None)
    _save_tasks()
    _executor.submit(_run_task, tid)
    return tid


def _failure_lines(t: Dict[str, Any]) -> list[str]:
    pat = re.compile(r"页数不 1:1|Traceback|构建失败|OCR 失败|exit [1-9]|Error|FAIL|gate=REJECT")
    out = []
    for ln in (t.get("log") or "").splitlines():
        if ln.lstrip().startswith("$ "):
            continue
        if pat.search(ln) and ln.strip() not in out:
            out.append(ln.strip())
    return out[:10]


def _find_output(t: Dict[str, Any]) -> Optional[Path]:
    out = Path(t.get("out") or "")
    if out.exists() and out.stat().st_size > 0:
        return out
    try:
        tmp = out.parent / ("_scan2pdf_" + t.get("book", ""))
        cand = sorted(tmp.glob("build_*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        if cand:
            return cand[0]
    except Exception:
        pass
    return None


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _diag(t: Dict[str, Any]) -> Dict[str, Any]:
    out = Path(t.get("out") or "")
    real = _find_output(t)
    # 诊断文件优先看最终 out；失败时退回查找中间目录
    bases = []
    if out.exists():
        bases.append(out)
    if real and real != out:
        bases.append(real)
    calib = gate = report = {}
    for b in bases:
        if not calib:
            calib = _read_json(Path(str(b) + ".calib.json"))
        if not gate:
            gate = _read_json(Path(str(b) + ".gate.json"))
        if not report:
            report = _read_json(Path(str(b) + ".report.json"))
    if not report and out.parent.exists():
        for b in sorted(out.parent.glob("*.report.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            report = _read_json(b)
            break
    g = gate or (report.get("gate") or {})
    gm = g.get("metrics", g)
    src_pages = t.get("src_pages")
    out_pages = t.get("out_pages")
    if out_pages is None and real:
        try:
            import fitz
            d = fitz.open(real); out_pages = d.page_count; d.close()
        except Exception:
            pass
    if src_pages is None and t.get("source"):
        try:
            import fitz
            d = fitz.open(t["source"]); src_pages = d.page_count; d.close()
        except Exception:
            pass
    chars = None
    if real:
        try:
            import fitz
            d = fitz.open(real); chars = sum(len(p.get_text().replace("\n", "")) for p in d); d.close()
        except Exception:
            pass
    bt = report.get("book_type") or {}
    return dict(
        log_path=t.get("log_path"),
        calib=dict(
            font_pt=(calib.get("font") or {}).get("pt"),
            font_source=(calib.get("font") or {}).get("source"),
            cw=calib.get("cw"), measure_pt=(calib.get("measure") or {}).get("pt"),
            dpi=(calib.get("dpi") or {}).get("value"),
            baseline_pt=(calib.get("baseline") or {}).get("pt"),
            baseline_font_ratio=(round(calib["baseline"]["pt"] / calib["font"]["pt"], 3)
                                 if calib.get("baseline", {}).get("pt") and calib.get("font", {}).get("pt") else None),
            warnings=[w.get("code") for w in calib.get("warnings", [])],
            warning_details=[w.get("detail") for w in calib.get("warnings", [])],
            selfcheck_verdict=(calib.get("selfcheck") or {}).get("verdict"),
            ink_pt=(calib.get("font") or {}).get("ink_pt"),
        ),
        gate=dict(verdict=g.get("verdict"), effective=g.get("verdict_effective"),
                  reasons=g.get("reasons", []), pitch_ok_pct=gm.get("pitch_ok_pct"),
                  split=gm.get("split"), overflow_pages=gm.get("overflow_pages")),
        pages=dict(src=src_pages, out=out_pages, diff=(out_pages - src_pages)
                   if src_pages is not None and out_pages is not None else None),
        report=dict(pipeline=report.get("pipeline"), axis=bt.get("axis"),
                    axis_refined_by=bt.get("axis_refined_by"),
                    layout=((report.get("layout") or {}).get("source")),
                    chars=chars, pages_out=report.get("pages_out"),
                    pages_src=report.get("pages_src")),
        output=str(real.relative_to(ROOT)) if real and real.exists() else None,
        log_exists=bool(t.get("log_path") and Path(t["log_path"]).exists()),
        gate_md_exists=bool(out.exists() and Path(str(out) + ".gate.md").exists()),
        artifact=str(real.relative_to(ROOT)) if real and real.exists() else None,
    )


def _task_json(t: Dict[str, Any]) -> Dict[str, Any]:
    now = t.get("ended") or time.time()
    start = t.get("started") or now
    return dict(id=t["id"], kind=t["kind"], book=t["book"], status=t["status"],
                stage=t.get("stage", "排队中"),
                elapsed=round(now - (t.get("started") or t["created"]), 1),
                log=t.get("log", ""), exit=t.get("exit"), out=t.get("out"),
                cmd=t.get("cmd", []), pid=t.get("pid"),
                src_pages=t.get("src_pages"), out_pages=t.get("out_pages"),
                page_diff=t.get("page_diff"), page_note=t.get("page_note"),
                log_url=f"/log/{t['id']}", gate_url=f"/gate/{t['id']}",
                artifact_url=f"/artifact/{t['id']}",
                failure=_failure_lines(t))


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
    hist = []
    for t in sorted(_tasks.values(), key=lambda x: x.get("created", 0), reverse=True)[:10]:
        created = time.strftime("%m-%d %H:%M", time.localtime(t.get("created", 0)))
        hist.append(f'<tr><td><a href="/task/{t["id"]}">{t["id"]}</a></td><td>{t.get("book","")}</td>'
                    f'<td>{t.get("kind","")}</td><td>{t.get("status","")}</td><td>{created}</td></tr>')
    return HOME.replace("__ROWS__", "\n".join(rows)).replace("__HISTORY__", "\n".join(hist))


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
    tid = _submit(cmd, out, "rebuild", book, ROOT / cfg["source"])
    return RedirectResponse(f"/task/{tid}", status_code=303)


@app.post("/upload")
async def upload(file: UploadFile = File(...), book: str = Form(...),
                 token_file: str = Form("/tmp/paddle_token"),
                 pipeline: str = Form("auto"),
                 allow_page_drift: str = Form("5")):
    book = _clean_book(book)
    if pipeline not in ("auto", "geom", "vert"):
        raise HTTPException(400, "pipeline 只能是 auto/geom/vert")
    try:
        drift = max(0, int(allow_page_drift))
    except ValueError:
        raise HTTPException(400, "允许页数漂移必须是整数")
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
    cmd += ["--token-file", str(tok), "--pipeline", pipeline,
            "--allow-page-drift", str(drift), "--force"]
    # 默认启用版面模型：插图/照片 passthrough 是纯增益（标题有 _heading_guard 守卫）
    if os.environ.get("LOCAL_CONSOLE_NO_LAYOUT", "") not in ("1", "true", "True"):
        cmd.append("--layout")
    tid = _submit(cmd, out, "upload", book, dst)
    return RedirectResponse(f"/task/{tid}", status_code=303)


@app.get("/api/diag/{tid}")
def diag_api(tid: str):
    if tid not in _tasks:
        raise HTTPException(404, "任务不存在")
    return JSONResponse(_diag(_tasks[tid]))


@app.get("/log/{tid}")
def log_file(tid: str):
    t = _tasks.get(tid)
    if not t or not t.get("log_path"):
        raise HTTPException(404, "日志不存在")
    p = Path(t["log_path"])
    if not p.exists():
        raise HTTPException(404, "日志不存在")
    return FileResponse(p, filename=p.name, media_type="text/plain")


@app.get("/gate/{tid}")
def gate_file(tid: str):
    t = _tasks.get(tid)
    if not t:
        raise HTTPException(404, "任务不存在")
    out = Path(t.get("out") or "")
    p = Path(str(out) + ".gate.md")
    if not p.exists():
        real = _find_output(t)
        p = Path(str(real) + ".gate.md") if real else p
    if not p.exists():
        raise HTTPException(404, "gate.md 不存在")
    return FileResponse(p, filename=p.name, media_type="text/markdown")


@app.get("/artifact/{tid}")
def artifact_file(tid: str):
    t = _tasks.get(tid)
    if not t:
        raise HTTPException(404, "任务不存在")
    p = _find_output(t)
    if not p or not p.exists():
        raise HTTPException(404, "产物不存在")
    return FileResponse(p, filename=p.name, media_type="application/pdf")


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
<div class="box"><h2>最近 10 个任务</h2>
<table><thead><tr><th>任务</th><th>书</th><th>类型</th><th>状态</th><th>创建</th></tr></thead>
<tbody>__HISTORY__</tbody></table></div>
<div class="box"><h2>上传新书（完整 OCR）</h2>
<form method="post" action="/upload" enctype="multipart/form-data">
<p>PDF：<input type="file" name="file" accept="application/pdf" required></p>
<p>书名：<input type="text" name="book" placeholder="例如 mybook" required></p>
<p>OCR token 文件：<input type="text" name="token_file" value="/tmp/paddle_token" size="40"></p>
<p>排版管线：
<select name="pipeline">
  <option value="auto">自动判断（默认）</option>
  <option value="geom">横排 geom</option>
  <option value="vert">竖排 vert</option>
</select>
<span class="note">横排书若被误判竖排，请选「横排 geom」。</span></p>
<p>允许页数漂移：<input type="number" name="allow_page_drift" value="5" min="0" max="50" style="width:70px">
<span class="note">默认 5；缺省 0 为严格 1:1。漂移成功时 gate 标记 PASS_WITH_DRIFT。</span></p>
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
<div id="failbox" style="display:none;border:1px solid #c00;background:#fff0f0;color:#900;padding:12px;border-radius:6px;margin:12px 0"></div>
<p>状态：<b id="st">读取中…</b>　阶段：<b id="stage">—</b>　已用：<span id="el">—</span></p>
<p class="note" id="meta">命令/输出读取中…</p>
<p id="dl" class="note"></p>
<div class="box"><h3>诊断卡</h3><div id="diag" class="note">读取中…</div></div>
<h3>执行日志（最近 100 行，实时刷新；完整日志见下方）</h3><pre id="log">读取中…</pre>
<p id="links" class="note"></p>
<p><a href="/">← 返回成果列表</a></p>
<script>
async function poll(){
  const r=await fetch('/api/tasks/__ID__'); const d=await r.json();
  document.getElementById('st').textContent=d.status;
  document.getElementById('stage').textContent=d.stage||'—';
  document.getElementById('el').textContent=d.elapsed+' 秒';
  document.getElementById('log').textContent=d.log||'（暂无日志；子进程可能尚未输出，已用时间仍在增加）';
  let pipe='auto'; if(d.cmd){const i=d.cmd.indexOf('--pipeline'); if(i>=0) pipe=d.cmd[i+1];}
  document.getElementById('meta').textContent='书: '+d.book+' | 类型: '+d.kind+' | 管线: '+pipe+' | PID: '+(d.pid||'—')+' | 输出: '+d.out
    + (d.src_pages!==null||d.out_pages!==null ? ' | 源页数: '+(d.src_pages??'—')+' / 产物页数: '+(d.out_pages??'—')+' / 差异: '+(d.page_diff??'—') : '');
  if(d.page_note) document.getElementById('meta').textContent += ' | '+d.page_note;
  const links=[];
  if(d.log_url) links.push('<a href="'+d.log_url+'">完整日志</a>');
  links.push('<a href="'+d.gate_url+'">gate.md</a>');
  if(d.artifact_url) links.push('<a href="'+d.artifact_url+'">中间/最终产物 PDF</a>');
  document.getElementById('links').innerHTML=links.join(' · ');
  if(d.failure && d.failure.length){
    document.getElementById('failbox').style.display='block';
    document.getElementById('failbox').innerHTML='<b>失败原因摘要</b><br>'+d.failure.map(x=>'• '+x.replace(/</g,'&lt;')).join('<br>');
  }
  if(d.status.startsWith('完成')){
    document.getElementById('dl').innerHTML='<a href="/download/task/'+d.id+'">下载产物 PDF</a>';
  }
  if(d.status==='失败'||d.status.startsWith('完成')){ clearInterval(t); }
}
async function loadDiag(){
  try{
    const r=await fetch('/api/diag/__ID__'); const g=await r.json();
    const c=g.calib||{}, gate=g.gate||{}, pg=g.pages||{}, rep=g.report||{};
    const rows=[
      ['font',(c.font_pt??'—')+' / '+(c.font_source??'—')],
      ['cw',c.cw??'—'],['measure',c.measure_pt??'—'],['dpi',c.dpi??'—'],
      ['baseline',(c.baseline_pt??'—')+' / ratio '+(c.baseline_font_ratio??'—')],
      ['selfcheck',c.selfcheck_verdict??'—'],
      ['warnings',(c.warnings||[]).join(', ')||'（无）'],
      ['gate',(gate.verdict??'—')+' / '+(gate.effective??'—')],
      ['gate reasons',(gate.reasons||[]).join(', ')||'（无）'],
      ['pages',(pg.src??'—')+' → '+(pg.out??'—')+' / diff '+(pg.diff??'—')],
      ['pitch/split/overflow',(gate.pitch_ok_pct??'—')+'% / '+(gate.split??'—')+' / '+(gate.overflow_pages??'—')],
      ['report',('pipeline='+(rep.pipeline??'—'))+' axis='+(rep.axis??'—')+' ('+(rep.axis_refined_by??'—')+') layout='+(rep.layout??'—')+' chars='+(rep.chars??'—')]
    ];
    document.getElementById('diag').innerHTML='<table>'+rows.map(x=>'<tr><th>'+x[0]+'</th><td>'+(x[1]+'').replace(/</g,'&lt;')+'</td></tr>').join('')+'</table>';
  }catch(e){document.getElementById('diag').textContent='诊断读取失败: '+e;}
}
let t=setInterval(poll,2000); poll(); loadDiag();
</script>
"""
