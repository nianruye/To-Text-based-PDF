from app.config import Config
from app.models.schemas import TextBlock, BlockStyle


class OCREngine:
    """Wraps PaddleOCR for text detection and recognition."""

    def __init__(self, config: Config):
        self.config = config
        self._ocr = None

    def _ensure_loaded(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                lang=self.config.ocr_lang,
                use_textline_orientation=self.config.use_angle_cls,
                text_det_thresh=self.config.det_db_thresh,
                text_rec_score_thresh=self.config.min_confidence,
            )

    def ocr_page(self, image_path: str) -> list[TextBlock]:
        """Run text detection + recognition on a single page image."""
        self._ensure_loaded()
        result = self._ocr.predict(image_path)

        blocks = []
        if not result:
            return blocks

        ocr_result = result[0]
        dt_polys = ocr_result.get("dt_polys", [])
        rec_texts = ocr_result.get("rec_texts", [])
        rec_scores = ocr_result.get("rec_scores", [])

        for i in range(len(rec_texts)):
            text = rec_texts[i]
            confidence = rec_scores[i] if i < len(rec_scores) else 0.0

            if confidence < self.config.min_confidence:
                continue

            if i < len(dt_polys):
                bbox = dt_polys[i]
                x0 = float(min(p[0] for p in bbox))
                y0 = float(min(p[1] for p in bbox))
                x1 = float(max(p[0] for p in bbox))
                y1 = float(max(p[1] for p in bbox))
            else:
                x0 = y0 = x1 = y1 = 0.0

            blocks.append(TextBlock(
                bbox=[x0, y0, x1, y1],
                text=text,
                confidence=float(confidence),
                style=BlockStyle.BODY,
            ))

        return blocks


def analyze_layout(image_path: str) -> list:
    """Stub: PPStructure not available in this PaddleOCR version."""
    return []
