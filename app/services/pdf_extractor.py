import os
import fitz
import numpy as np
from app.config import Config


def extract_pages_to_images(pdf_path: str, output_dir: str, config: Config) -> tuple:
    """Extract PDF pages to PNG images. Returns (image_paths, page_info_list)."""
    doc = fitz.open(pdf_path)
    os.makedirs(output_dir, exist_ok=True)

    images = []
    page_info = []

    zoom = config.render_dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    for i, page in enumerate(doc):
        text = page.get_text()
        has_text = len(text.strip()) > config.text_native_threshold

        pix = page.get_pixmap(matrix=mat, alpha=False)
        is_blank = _detect_blank(pix)

        img_path = os.path.join(output_dir, f"page_{i + 1:04d}.png")
        pix.save(img_path)

        images.append(img_path)
        page_info.append({
            "page_num": i + 1,
            "width": pix.width,
            "height": pix.height,
            "has_embedded_text": has_text,
            "is_blank": is_blank,
            "original_rect": page.rect,
        })

    doc.close()
    return images, page_info


def _detect_blank(pix) -> bool:
    samples = pix.samples
    if len(samples) < 100:
        return True
    arr = np.frombuffer(samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n >= 3:
        gray = np.mean(arr[:, :, :3], axis=2)
    else:
        gray = arr[:, :, 0].astype(float)

    content_ratio = float(np.mean(gray < 250))
    if content_ratio > 0.00005:
        return False

    return float(np.std(gray)) < 3.0
