#!/usr/bin/env python3
"""
Form-specific section detection and clustering from bbox/spatial OCR.
=====================================================================
Identifies section headers by keyword match, assigns each bbox block to a section,
computes section crop bboxes, and provides section-scoped text and crop images
for the extractor and VLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from section_config import get_headers_for_form, get_section_ids_for_category

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@dataclass
class FormSection:
    """One detected section on a page."""
    section_id: str
    page: int
    # Blocks in this section (indices into page's bbox list, or the block dicts themselves)
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    # Bounding box for the section (union of blocks + padding): (x_min, y_min, x_max, y_max)
    crop_bbox: Optional[Tuple[int, int, int, int]] = None
    # Optional title from first header-like block
    title: str = ""


def _block_matches_keywords(block: Dict[str, Any], keywords: List[str]) -> bool:
    text = (block.get("text") or "").strip().upper()
    if not text:
        return False
    for kw in keywords:
        if kw.upper() in text:
            return True
    return False


def _find_section_anchors(
    page_blocks: List[Dict[str, Any]],
    headers: List[Dict[str, str]],
) -> List[Tuple[str, float]]:
    """
    For each header config, find the minimum Y among blocks that match its keywords.
    Returns [(section_id, min_y), ...] sorted by min_y ascending.
    """
    anchors: List[Tuple[str, float]] = []
    for h in headers:
        section_id = h["id"]
        keywords = h.get("keywords", [])
        min_y = float("inf")
        for b in page_blocks:
            y = b.get("y") or b.get("y_min", 0)
            if _block_matches_keywords(b, keywords):
                min_y = min(min_y, y)
        if min_y != float("inf"):
            anchors.append((section_id, min_y))
    anchors.sort(key=lambda x: x[1])
    return anchors


def _assign_blocks_to_sections(
    page_blocks: List[Dict[str, Any]],
    anchors: List[Tuple[str, float]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Assign each block to the section whose anchor Y is the largest that is <= block.y.
    Blocks above the first anchor go to the first section.
    """
    section_blocks: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid, _ in anchors}
    if not anchors:
        return section_blocks

    for block in page_blocks:
        y = block.get("y") or block.get("y_min", 0)
        # Which section? Largest anchor_y <= y
        chosen = anchors[0][0]
        for sid, anchor_y in anchors:
            if anchor_y <= y:
                chosen = sid
            else:
                break
        section_blocks[chosen].append(block)

    return section_blocks


def _union_bbox(blocks: List[Dict[str, Any]], padding: int = 15) -> Optional[Tuple[int, int, int, int]]:
    if not blocks:
        return None
    x_min = min(b.get("x_min", b.get("x", 0)) for b in blocks)
    y_min = min(b.get("y_min", b.get("y", 0)) for b in blocks)
    x_max = max(b.get("x_max", b.get("x", 0)) for b in blocks)
    y_max = max(b.get("y_max", b.get("y", 0)) for b in blocks)
    x_min = max(0, x_min - padding)
    y_min = max(0, y_min - padding)
    x_max = x_max + padding
    y_max = y_max + padding
    return (x_min, y_min, x_max, y_max)


def get_sections_for_form(
    form_type: str,
    bbox_pages: List[List[Dict[str, Any]]],
    max_pages: int = 4,
    padding: int = 15,
) -> List[FormSection]:
    """
    Detect form sections per page from bbox data using form-specific headers.
    Returns a flat list of FormSection (one per section per page).
    """
    headers = get_headers_for_form(form_type)
    if not headers:
        return []

    result: List[FormSection] = []
    for page_idx in range(min(max_pages, len(bbox_pages))):
        page_blocks = bbox_pages[page_idx]
        if not page_blocks:
            continue

        anchors = _find_section_anchors(page_blocks, headers)
        if not anchors:
            # No headers found: treat whole page as one section
            section = FormSection(
                section_id="full_page",
                page=page_idx,
                blocks=page_blocks,
                crop_bbox=_union_bbox(page_blocks, padding),
                title="Full page",
            )
            result.append(section)
            continue

        section_blocks = _assign_blocks_to_sections(page_blocks, anchors)
        for section_id, blocks in section_blocks.items():
            if not blocks:
                continue
            crop = _union_bbox(blocks, padding)
            # Title from first block that looks like a header (short, or matches keywords)
            title = ""
            for h in headers:
                if h["id"] == section_id and blocks:
                    for b in blocks[:3]:
                        if _block_matches_keywords(b, h.get("keywords", [])):
                            title = (b.get("text") or "").strip()[:60]
                            break
                    break
            result.append(FormSection(
                section_id=section_id,
                page=page_idx,
                blocks=blocks,
                crop_bbox=crop,
                title=title or section_id,
            ))

    return result


def get_section_scoped_bbox_text(
    bbox_pages: List[List[Dict[str, Any]]],
    sections: List[FormSection],
    section_ids: List[str],
    row_tolerance: int = 35,
    max_rows: int = 200,
) -> str:
    """
    Format bbox text only for blocks that belong to the given section_ids.
    Uses same row-based formatting as OCREngine.format_bbox_as_rows.
    """
    want_ids = set(section_ids)
    blocks_by_page: Dict[int, List[Dict]] = {}
    for s in sections:
        if s.section_id not in want_ids or not s.blocks:
            continue
        if s.page not in blocks_by_page:
            blocks_by_page[s.page] = []
        blocks_by_page[s.page].extend(s.blocks)

    if not blocks_by_page:
        return ""

    lines: List[str] = []
    for page_idx in sorted(blocks_by_page.keys()):
        page_blocks = blocks_by_page[page_idx]
        page_blocks.sort(key=lambda x: (x.get("y", 0), x.get("x", 0)))
        rows: List[List[Dict]] = []
        cur_row: List[Dict] = []
        cur_y: float = -9999
        for item in page_blocks:
            y = item.get("y", 0)
            if abs(y - cur_y) <= row_tolerance:
                cur_row.append(item)
                cur_y = (cur_y + y) / 2
            else:
                if cur_row:
                    rows.append(sorted(cur_row, key=lambda x: x.get("x", 0)))
                cur_row = [item]
                cur_y = y
        if cur_row:
            rows.append(sorted(cur_row, key=lambda x: x.get("x", 0)))

        for row in rows[:max_rows]:
            row_str = f"y≈{int(row[0].get('y', 0))}: "
            row_str += " | ".join(f"[x={d.get('x', 0)}]{d.get('text', '')}" for d in row[:15])
            lines.append(row_str)

    return "\n".join(lines)


def get_section_scoped_docling(
    docling_pages: List[str],
    sections: List[FormSection],
    section_ids: List[str],
) -> str:
    """
    Return Docling text for pages that contain the given sections.
    (We don't have Docling block-level bbox yet, so we return full page text for those pages.)
    """
    want_ids = set(section_ids)
    pages_needed: set = set()
    for s in sections:
        if s.section_id in want_ids:
            pages_needed.add(s.page)
    if not pages_needed:
        return ""
    parts = []
    for i in sorted(pages_needed):
        if i < len(docling_pages):
            parts.append(docling_pages[i])
    return "\n\n=== PAGE BREAK ===\n\n".join(parts)


def crop_sections_to_images(
    image_paths: List[Path],
    sections: List[FormSection],
    section_ids: List[str],
    output_dir: Path,
    page_stem: str = "page",
) -> List[Path]:
    """
    Crop page images to section bboxes for the given section_ids.
    Returns list of paths to crop images (one per section that has a crop_bbox).
    """
    if not PIL_AVAILABLE or not image_paths:
        return []

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    want_ids = set(section_ids)
    crop_paths: List[Path] = []

    for s in sections:
        if s.section_id not in want_ids or s.crop_bbox is None or s.page >= len(image_paths):
            continue
        img_path = Path(image_paths[s.page])
        if not img_path.exists():
            continue

        img = Image.open(img_path).convert("RGB")
        w, h = img.size
        x_min, y_min, x_max, y_max = s.crop_bbox
        x_min = max(0, min(x_min, w - 1))
        y_min = max(0, min(y_min, h - 1))
        x_max = max(x_min + 1, min(x_max, w))
        y_max = max(y_min + 1, min(y_max, h))
        cropped = img.crop((x_min, y_min, x_max, y_max))
        out_name = f"{page_stem}_p{s.page + 1}_{s.section_id}.png"
        out_path = output_dir / out_name
        cropped.save(out_path, "PNG")
        crop_paths.append(out_path)

    return crop_paths


def get_sections_for_category(
    form_type: str,
    category: str,
    sections: List[FormSection],
) -> List[FormSection]:
    """Return the subset of sections that should be used when extracting this category."""
    section_ids = get_section_ids_for_category(form_type, category)
    want = set(section_ids)
    return [s for s in sections if s.section_id in want]
