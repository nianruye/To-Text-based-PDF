from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    PREPROCESSING = "preprocessing"
    OCR = "ocr"
    GENERATING = "generating"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BlockStyle(str, Enum):
    HEADING = "heading"
    BODY = "body"
    TABLE_CELL = "table_cell"
    CAPTION = "caption"
    FIGURE_LABEL = "figure_label"


class TextBlock(BaseModel):
    bbox: list[float]  # [x0, y0, x1, y1] in image pixels
    text: str
    confidence: float
    style: BlockStyle = BlockStyle.BODY
    reading_order: int = 0
    original_font_size: Optional[float] = None  # OCR-detected font size in image pixels
    gap_before: Optional[float] = None  # spacing before this block in image pixels


class LayoutRegion(BaseModel):
    type: str  # text, title, table, figure, list
    bbox: list[float]
    content: list[TextBlock] = []


class PageResult(BaseModel):
    page_num: int
    was_image_based: bool
    is_blank: bool
    width: float
    height: float
    blocks: list[TextBlock] = []
    avg_confidence: float = 0.0
    warnings: list[str] = []


class ProgressMessage(BaseModel):
    job_id: str
    stage: str
    progress: float = 0.0
    page: int = 0
    total_pages: int = 0
    message: str = ""
    download_url: Optional[str] = None


class JobInfo(BaseModel):
    job_id: str
    status: JobStatus
    filename: str
    total_pages: int = 0
    processed_pages: int = 0
    created_at: str = ""
    error_message: Optional[str] = None


class ErrorResponse(BaseModel):
    job_id: Optional[str] = None
    status: str = "error"
    error_code: str
    message: str
    detail: Optional[str] = None
    recoverable: bool = False


class UploadResponse(BaseModel):
    job_id: str
    status: JobStatus
    filename: str
    websocket_url: str
