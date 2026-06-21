import cv2
import numpy as np
from app.config import Config


def preprocess_for_ocr(image_path: str, output_path: str, config: Config) -> dict:
    """Enhance a scanned page image for better OCR accuracy. Returns preprocessing stats."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(
        clipLimit=config.clahe_clip_limit,
        tileGridSize=(config.clahe_tile_size, config.clahe_tile_size)
    )
    enhanced = clahe.apply(gray)

    denoised = cv2.fastNlMeansDenoising(enhanced, h=config.denoise_strength)

    blurred = cv2.GaussianBlur(denoised, (0, 0), 1.0)
    sharpened = cv2.addWeighted(denoised, config.sharpen_amount, blurred, -(config.sharpen_amount - 1), 0)

    std_dev = float(np.std(sharpened))
    binarized = std_dev < config.binarize_threshold_std

    if binarized:
        result = cv2.adaptiveThreshold(
            sharpened, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
    else:
        result = sharpened

    cv2.imwrite(output_path, result)
    return {"original_std": std_dev, "binarized": binarized}
