from dataclasses import dataclass, field


@dataclass
class Config:
    # Paths
    upload_dir: str = "/opt/test/uploads"
    output_dir: str = "/opt/test/outputs"
    log_dir: str = "/opt/test/logs"
    font_dir: str = "/usr/share/fonts"

    # Rendering
    render_dpi: int = 300
    render_format: str = "png"

    # Preprocessing
    clahe_clip_limit: float = 2.0
    clahe_tile_size: int = 8
    denoise_strength: int = 10
    sharpen_amount: float = 1.5
    binarize_threshold_std: float = 15.0

    # OCR
    ocr_lang: str = "ch"
    use_angle_cls: bool = True
    min_confidence: float = 0.5
    det_db_thresh: float = 0.3

    # Output
    font_size_ratio: float = 0.45
    cjk_fonts: list = field(default_factory=lambda: [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ])

    # Limits
    max_upload_size_mb: int = 100
    max_pages: int = 500
    job_timeout_seconds: int = 600
    cleanup_age_minutes: int = 60

    # Text detection threshold (chars needed to consider page text-native)
    text_native_threshold: int = 50
