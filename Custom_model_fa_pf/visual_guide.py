"""Visual form guide — annotated PDF images showing where data goes."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Status -> RGBA color
STATUS_COLORS = {
    "confirmed": (0, 200, 0, 80),       # Green
    "pending": (255, 200, 0, 80),        # Yellow
    "error": (255, 0, 0, 80),            # Red
    "empty": (200, 200, 200, 40),        # Light gray
}


@dataclass
class FieldHighlight:
    """A field to highlight on the form image."""
    field_name: str
    value: str
    rect: Tuple[float, float, float, float]  # x0, y0, x1, y1
    page: int
    status: str = "confirmed"

    @property
    def color(self) -> Tuple[int, int, int, int]:
        return STATUS_COLORS.get(self.status, STATUS_COLORS["empty"])


def generate_field_overlay(
    pdf_path: Path,
    highlights: List[FieldHighlight],
    dpi: int = 150,
) -> Dict[int, bytes]:
    """Generate annotated PNG images for each page of a PDF.

    Args:
        pdf_path: Path to the template PDF
        highlights: List of FieldHighlight to draw on the pages
        dpi: Resolution for rendering

    Returns:
        Dict of page_number -> PNG bytes
    """
    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return {}

    doc = fitz.open(str(pdf_path))
    page_highlights: Dict[int, List[FieldHighlight]] = {}

    for h in highlights:
        page_highlights.setdefault(h.page, []).append(h)

    result = {}
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Draw highlights for this page
        for h in page_highlights.get(page_num, []):
            r, g, b, a = h.color
            rect = fitz.Rect(h.rect)
            shape = page.new_shape()
            shape.draw_rect(rect)
            shape.finish(
                color=(r / 255, g / 255, b / 255),
                fill=(r / 255, g / 255, b / 255),
                fill_opacity=a / 255,
                width=0.5,
            )
            shape.commit()

        # Render with annotations
        pix = page.get_pixmap(matrix=mat, alpha=False)
        result[page_num] = pix.tobytes("png")

    doc.close()
    return result
