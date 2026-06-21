from app.models.schemas import TextBlock, BlockStyle, LayoutRegion


def merge_layout_and_ocr(
    ocr_blocks: list[TextBlock],
    layout_regions: list,
    page_height: float,
) -> list[TextBlock]:
    """Fuse OCR results with layout analysis, assign styles, group into paragraphs."""

    if not ocr_blocks:
        return []

    # Match each OCR block to a layout region
    for block in ocr_blocks:
        region = _find_containing_region(block.bbox, layout_regions)
        if region and region.get("type") == "title":
            block.style = BlockStyle.HEADING
        elif region and region.get("type") == "table":
            block.style = BlockStyle.TABLE_CELL
        elif region and region.get("type") == "figure":
            block.style = BlockStyle.FIGURE_LABEL

    # Infer heading style for large font / short text
    _infer_styles(ocr_blocks)

    # Sort by reading order (top-to-bottom, left-to-right)
    ordered = _reading_order_sort(ocr_blocks, page_height)

    # Group into paragraphs
    grouped = _group_paragraphs(ordered)

    # Assign reading order
    for idx, block in enumerate(grouped):
        block.reading_order = idx

    return grouped


def _find_containing_region(bbox: list[float], regions: list) -> dict | None:
    """Find which layout region contains this bbox."""
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    for region in regions:
        rb = region.get("bbox", [])
        if len(rb) == 4 and rb[0] <= cx <= rb[2] and rb[1] <= cy <= rb[3]:
            return region
    return None


def _infer_styles(blocks: list[TextBlock]):
    """Heuristic style inference — detect headings by position and text properties."""
    if not blocks:
        return

    heights = [b.bbox[3] - b.bbox[1] for b in blocks]
    median_h = sorted(heights)[len(heights) // 2] if heights else 20

    # Compute page center from all block x-coordinates
    all_x_centers = [(b.bbox[0] + b.bbox[2]) / 2 for b in blocks]
    page_center_x = sorted(all_x_centers)[len(all_x_centers) // 2] if all_x_centers else 500

    # Sort by vertical position for gap detection
    sorted_by_y = sorted(blocks, key=lambda b: b.bbox[1])
    prev_y1 = 0

    for i, block in enumerate(sorted_by_y):
        block_h = block.bbox[3] - block.bbox[1]
        text_len = len(block.text)
        block_width = block.bbox[2] - block.bbox[0]
        block_center_x = (block.bbox[0] + block.bbox[2]) / 2
        is_centered = abs(block_center_x - page_center_x) < 200
        is_large = block_h > median_h * 1.4
        is_short = text_len < 45
        is_narrow = block_width < 1200
        is_very_short = text_len < 25
        has_cjk = any(0x4E00 <= ord(c) <= 0x9FFF or 0x3400 <= ord(c) <= 0x4DBF for c in block.text)
        # Filter out mid-sentence continuations (text starting with grammatical particles)
        continuation_starters = set('的了是在和与也就但却所被把从对向给为因其这那它他她们着过')
        looks_like_heading = not block.text or block.text[0] not in continuation_starters

        # Gap before this block (detect section/heading breaks)
        gap_before = block.bbox[1] - prev_y1 if prev_y1 > 0 else 0
        has_section_gap = gap_before > median_h * 2.0
        prev_y1 = block.bbox[3]

        if block.style != BlockStyle.HEADING:
            if is_large and is_short and text_len < 25:
                block.style = BlockStyle.HEADING
            elif is_centered and is_narrow and is_short and 2 < text_len < 25 and has_cjk:
                block.style = BlockStyle.HEADING
            elif has_section_gap and is_large and is_short:
                block.style = BlockStyle.HEADING
            # Section gap + very short text = heading even if bbox isn't tall
            elif has_section_gap and is_very_short and has_cjk:
                block.style = BlockStyle.HEADING
            # First blocks at page top with short CJK text are often headings
            elif i <= 1 and is_very_short and is_narrow and has_cjk and looks_like_heading:
                block.style = BlockStyle.HEADING


def _reading_order_sort(blocks: list[TextBlock], page_height: float) -> list[TextBlock]:
    """Sort blocks by reading order: top-to-bottom, then left-to-right within bands."""
    band_threshold = page_height * 0.01

    sorted_blocks = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))
    ordered = []
    current_band = []
    band_top = sorted_blocks[0].bbox[1] if sorted_blocks else 0

    for block in sorted_blocks:
        if block.bbox[1] - band_top > band_threshold:
            current_band.sort(key=lambda b: b.bbox[0])
            ordered.extend(current_band)
            current_band = [block]
            band_top = block.bbox[1]
        else:
            current_band.append(block)

    current_band.sort(key=lambda b: b.bbox[0])
    ordered.extend(current_band)
    return ordered


def _group_paragraphs(blocks: list[TextBlock]) -> list[TextBlock]:
    """Group adjacent text lines into paragraphs, recording original font size and gaps."""
    if not blocks:
        return []

    result = []
    current = blocks[0]
    current_line_heights = [blocks[0].bbox[3] - blocks[0].bbox[1]]
    prev_result_bottom = 0
    line_heights = [b.bbox[3] - b.bbox[1] for b in blocks if b.style == BlockStyle.BODY]
    median_h = sorted(line_heights)[len(line_heights) // 2] if line_heights else 10
    line_gap = median_h * 0.3

    for i in range(1, len(blocks)):
        b = blocks[i]
        gap = b.bbox[1] - (current.bbox[3])
        same_style = current.style == b.style
        not_heading = current.style != BlockStyle.HEADING

        # Vertically adjacent lines
        vert_merge = same_style and 0 < gap < line_gap * 2.5 and (
            not_heading or gap < line_gap * 0.5
        )
        # Horizontally adjacent on same line (overlapping vertical bounds)
        current_h = current.bbox[3] - current.bbox[1]
        h_gap = b.bbox[0] - current.bbox[2]
        same_line = same_style and -current_h < gap <= 0 and 0 < h_gap < line_gap * 8

        if vert_merge or same_line:
            # Merge into same paragraph block
            current.bbox[0] = min(current.bbox[0], b.bbox[0])
            current.bbox[1] = min(current.bbox[1], b.bbox[1])
            current.bbox[2] = max(current.bbox[2], b.bbox[2])
            current.bbox[3] = max(current.bbox[3], b.bbox[3])
            current.text += " " + b.text
            current.confidence = (current.confidence + b.confidence) / 2
            current_line_heights.append(b.bbox[3] - b.bbox[1])
        else:
            _finalize_block(current, current_line_heights, prev_result_bottom)
            result.append(current)
            prev_result_bottom = current.bbox[3]
            current = b
            current_line_heights = [b.bbox[3] - b.bbox[1]]

    _finalize_block(current, current_line_heights, prev_result_bottom)
    result.append(current)
    return result


def _finalize_block(
    block: TextBlock,
    line_heights: list[float],
    prev_bottom: float,
) -> None:
    """Set original_font_size and gap_before on a paragraph block before emitting."""
    sorted_h = sorted(line_heights)
    median_line_h = sorted_h[len(sorted_h) // 2] if sorted_h else 0
    block.original_font_size = median_line_h
    if prev_bottom > 0:
        block.gap_before = block.bbox[1] - prev_bottom
