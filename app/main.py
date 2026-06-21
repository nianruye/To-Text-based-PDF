import os
import uuid
import asyncio
from datetime import datetime
import os
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from typing import Union

from app.config import Config
from app.services.processor import PDFProcessor
from app.models.schemas import (
    JobStatus, JobInfo, ProgressMessage, ErrorResponse, UploadResponse
)

config = Config()
app = FastAPI(title="PDF Clarity Enhancer", version="1.0.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# In-memory job state
jobs: dict[str, JobInfo] = {}
# WebSocket connections by job_id
ws_connections: dict[str, WebSocket] = {}
# Cancellation flags
cancel_flags: dict[str, bool] = {}
# Progress queues
progress_queues: dict[str, asyncio.Queue] = {}


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/upload", response_model=Union[UploadResponse, ErrorResponse])
async def upload_pdf(file: UploadFile = File(...)):
    # Validate file type
    header = await file.read(5)
    await file.seek(0)

    if not header.startswith(b"%PDF"):
        return ErrorResponse(
            error_code="INVALID_FILE_TYPE",
            message="File is not a valid PDF.",
            recoverable=True,
        )

    # Read full file to check size
    contents = await file.read()
    if len(contents) > config.max_upload_size_mb * 1024 * 1024:
        return ErrorResponse(
            error_code="FILE_TOO_LARGE",
            message=f"File exceeds {config.max_upload_size_mb}MB limit.",
            recoverable=True,
        )

    job_id = str(uuid.uuid4())
    os.makedirs(config.upload_dir, exist_ok=True)

    pdf_path = os.path.join(config.upload_dir, f"{job_id}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(contents)

    jobs[job_id] = JobInfo(
        job_id=job_id,
        status=JobStatus.PENDING,
        filename=file.filename or "untitled.pdf",
        created_at=datetime.now().isoformat(),
    )

    progress_queues[job_id] = asyncio.Queue()
    cancel_flags[job_id] = False

    # Start processing in background
    asyncio.create_task(_process_job(job_id, pdf_path))

    return UploadResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        filename=file.filename or "untitled.pdf",
        websocket_url=f"/ws/{job_id}",
    )


@app.websocket("/ws/{job_id}")
async def websocket_progress(ws: WebSocket, job_id: str):
    await ws.accept()
    ws_connections[job_id] = ws

    # Send current status immediately on connect
    if job_id in jobs:
        job = jobs[job_id]
        await ws.send_json(ProgressMessage(
            job_id=job_id,
            stage=job.status.value,
            progress=job.processed_pages / max(job.total_pages, 1) * 100,
            page=job.processed_pages,
            total_pages=job.total_pages,
            download_url=f"/api/download/{job_id}" if job.status == JobStatus.COMPLETE else None,
            message=f"Status: {job.status.value}",
        ).model_dump())

    try:
        while True:
            data = await ws.receive_text()
            if data == "cancel":
                cancel_flags[job_id] = True
                if job_id in jobs:
                    jobs[job_id].status = JobStatus.CANCELLED
    except WebSocketDisconnect:
        pass
    finally:
        ws_connections.pop(job_id, None)


@app.get("/api/status/{job_id}", response_model=Union[JobInfo, ErrorResponse])
async def job_status(job_id: str):
    if job_id not in jobs:
        return ErrorResponse(
            job_id=job_id,
            error_code="NOT_FOUND",
            message="Job not found.",
            recoverable=False,
        )
    return jobs[job_id]


@app.get("/api/download/{job_id}")
async def download_result(job_id: str):
    if job_id not in jobs:
        return ErrorResponse(
            job_id=job_id,
            error_code="NOT_FOUND",
            message="Job not found.",
            recoverable=False,
        )

    job = jobs[job_id]
    if job.status != JobStatus.COMPLETE:
        return ErrorResponse(
            job_id=job_id,
            error_code="NOT_READY",
            message=f"Job is {job.status.value}, not yet complete.",
            recoverable=True,
        )

    output_path = os.path.join(config.output_dir, f"{job_id}_enhanced.pdf")
    if not os.path.exists(output_path):
        return ErrorResponse(
            job_id=job_id,
            error_code="FILE_MISSING",
            message="Output file not found on disk.",
            recoverable=False,
        )

    return FileResponse(
        output_path,
        filename=f"enhanced_{job.filename}",
        media_type="application/pdf",
    )


async def _process_job(job_id: str, pdf_path: str):
    jobs[job_id].status = JobStatus.EXTRACTING

    async def progress_callback(msg: ProgressMessage):
        jobs[job_id].status = JobStatus(msg.stage)
        if msg.total_pages:
            jobs[job_id].total_pages = msg.total_pages
        if msg.page:
            jobs[job_id].processed_pages = msg.page

        # Send via WebSocket
        ws = ws_connections.get(job_id)
        if ws:
            try:
                await ws.send_json(msg.model_dump())
            except Exception:
                pass

        # Also push to queue for polling fallback
        q = progress_queues.get(job_id)
        if q:
            await q.put(msg)

    try:
        processor = PDFProcessor(config)
        output_path = await processor.process(job_id, pdf_path, progress_callback)
        jobs[job_id].status = JobStatus.COMPLETE
        jobs[job_id].processed_pages = jobs[job_id].total_pages

        # Notify completion
        ws = ws_connections.get(job_id)
        if ws:
            try:
                await ws.send_json(ProgressMessage(
                    job_id=job_id,
                    stage="complete",
                    progress=100,
                    download_url=f"/api/download/{job_id}",
                    message="Processing complete!",
                ).model_dump())
            except Exception:
                pass

    except Exception as e:
        jobs[job_id].status = JobStatus.FAILED
        jobs[job_id].error_message = str(e)
        ws = ws_connections.get(job_id)
        if ws:
            try:
                await ws.send_json(ErrorResponse(
                    job_id=job_id,
                    error_code="PROCESSING_FAILED",
                    message=str(e),
                    recoverable=False,
                ).model_dump())
            except Exception:
                pass

    finally:
        # Schedule cleanup after 1 hour
        asyncio.create_task(_delayed_cleanup(job_id, pdf_path))


async def _delayed_cleanup(job_id: str, pdf_path: str):
    await asyncio.sleep(config.cleanup_age_minutes * 60)
    # Clean up input
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    # Clean up work dir
    work_dir = os.path.join(config.upload_dir, job_id)
    if os.path.exists(work_dir):
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)
    # Clean up output
    output_path = os.path.join(config.output_dir, f"{job_id}_enhanced.pdf")
    if os.path.exists(output_path):
        os.remove(output_path)
    jobs.pop(job_id, None)
    progress_queues.pop(job_id, None)
    cancel_flags.pop(job_id, None)
