import math
import fitz
from app.config import Config
from app.models.schemas import PageResult, TextBlock, BlockStyle

BASE_FONT_SIZE = 10.5
MIN_FONT_SIZE = 6.0
MAX_FONT_SIZE = 18.0
PAGE_MARGIN = 50
SECTION_GAP = 14
PARAGRAPH_GAP = 4
LINE_GAP = 2


def _estimate_lines(text: str, rect_width: float, font_size: float, fontname: str) -> float:
    """Estimate number of lines needed for text in a rect of given width."""
    cjk = sum(1 for c in text if ord(c) > 127)
    latin = len(text) - cjk
    if "china" in fontname:
        char_width = cjk * font_size * 1.0 + latin * font_size * 1.5
    else:
        char_width = cjk * font_size * 1.0 + latin * font_size * 0.6
    return max(1, char_width / max(rect_width, 1))


def generate_enhanced_pdf(
    original_pdf_path: str,
    page_results: list[PageResult],
    output_path: str,
    config: Config,
) -> str:
    """Create a clean text-based PDF from OCR results with flowing layout."""
    orig_doc = fitz.open(original_pdf_path)
    out_doc = fitz.open()

    for pr in page_results:
        if pr.page_num > len(orig_doc):
            continue

        orig_page = orig_doc[pr.page_num - 1]
        page_w = orig_page.rect.width
        page_h = orig_page.rect.height
        out_page = out_doc.new_page(width=page_w, height=page_h)

        if not pr.was_image_based or pr.is_blank:
            out_page.show_pdf_page(out_page.rect, orig_doc, pr.page_num - 1)
            continue

        # White background
        out_page.draw_rect(out_page.rect, color=(1, 1, 1), fill=(1, 1, 1))

        scale_x = page_w / pr.width if pr.width > 0 else 1
        scale_y = page_h / pr.height if pr.height > 0 else 1

        # Compute median single-line height in PDF points for body font sizing
        block_heights = []
        for block in pr.blocks:
            if len(block.bbox) != 4:
                continue
            bh = (block.bbox[3] - block.bbox[1]) * scale_y
            if 5 < bh < 100:
                block_heights.append(bh)
        median_h = sorted(block_heights)[len(block_heights) // 2] if block_heights else 20

        # Flow text sequentially from top to bottom
        y_cursor = PAGE_MARGIN
        prev_style = None

        for block in pr.blocks:
            y_cursor = _flow_text_block(
                out_page, block, scale_x, scale_y, median_h,
                page_w, page_h, y_cursor, prev_style,
            )
            prev_style = block.style

    out_doc.save(output_path, garbage=4, deflate=True, clean=True)
    out_doc.close()
    orig_doc.close()
    return output_path


def _flow_text_block(
    page: fitz.Page,
    block: TextBlock,
    scale_x: float,
    scale_y: float,
    median_h: float,
    page_w: float,
    page_h: float,
    y_cursor: float,
    prev_style,
) -> float:
    """Place a text block at y_cursor, return new y_cursor after this block."""
    bbox = block.bbox
    if len(bbox) != 4:
        return y_cursor
    if any(math.isnan(v) or math.isinf(v) for v in bbox):
        return y_cursor

    block_h = (bbox[3] - bbox[1]) * scale_y
    if block_h <= 0:
        return y_cursor

    # Font size: use OCR-detected original size if available, else fall back to block height.
    if block.original_font_size is not None:
        font_size = block.original_font_size * scale_y
    else:
        font_size = block_h * 0.9
    font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, font_size))

    if block.style == BlockStyle.HEADING:
        font_size = max(font_size, BASE_FONT_SIZE * 1.3)

    # Font selection
    cjk_ratio = sum(1 for c in block.text if ord(c) > 127) / max(len(block.text), 1)
    fontname = "china-s" if cjk_ratio > 0.3 else "helv"
    font_args = {"fontname": fontname}

    # Determine horizontal bounds
    pdf_x0 = bbox[0] * scale_x
    pdf_x0 = max(PAGE_MARGIN, min(pdf_x0, page_w - PAGE_MARGIN - 100))

    if block.style == BlockStyle.HEADING:
        left_x = PAGE_MARGIN
        right_x = page_w - PAGE_MARGIN
        align = fitz.TEXT_ALIGN_CENTER
    else:
        left_x = pdf_x0
        right_x = page_w - PAGE_MARGIN
        align = fitz.TEXT_ALIGN_LEFT

    rect_w = right_x - left_x
    if rect_w <= 0:
        return y_cursor

    # Add gap before block — use detected gap if available, else fixed defaults.
    if prev_style is not None:
        if block.style == BlockStyle.HEADING:
            y_cursor += max(SECTION_GAP, (block.gap_before or 0) * scale_y)
        elif block.gap_before is not None:
            y_cursor += max(0, block.gap_before * scale_y)
        else:
            y_cursor += PARAGRAPH_GAP

    # Page break check: estimate if text roughly fits on remaining page
    est_lines_needed = _estimate_lines(block.text, rect_w, font_size, fontname)
    est_height = est_lines_needed * font_size * 1.5 + 2
    if y_cursor + est_height > page_h - PAGE_MARGIN:
        y_cursor = PAGE_MARGIN

    # Use a tall rect to avoid overflow; calculate actual height from result
    rect = fitz.Rect(left_x, y_cursor, right_x, page_h - PAGE_MARGIN)

    result = page.insert_textbox(
        rect,
        block.text,
        fontsize=font_size,
        align=align,
        **font_args,
    )
    # result = remaining space at bottom. actual_used = rect.height - max(result, 0)
    actual_used = rect.height - max(result, 0)
    if result < 0:
        actual_used = rect.height  # text overflowed even the tall rect

    return y_cursor + actual_used + LINE_GAP
