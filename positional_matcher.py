#!/usr/bin/env python3
"""
Positional Matcher: Runtime geometric field matching using schema atlas
========================================================================
Loads the positional atlas from enriched schemas (built by build_field_atlas.py),
aligns atlas positions to the actual scan via anchor labels, and matches OCR
bounding-box data to schema fields by geometric containment and IoU.

This provides AcroForm-equivalent positional knowledge for scanned-only PDFs:
each OCR text block is assigned to the nearest schema field based on where it
physically appears on the page.

Usage:
    from positional_matcher import PositionalMatcher
    matcher = PositionalMatcher()
    fields, metadata = matcher.match(schema, bbox_pages)
"""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from schema_registry import FormSchema, FieldInfo


def _compute_iou(
    ax0: float, ay0: float, ax1: float, ay1: float,
    bx0: float, by0: float, bx1: float, by1: float,
) -> float:
    """Compute intersection-over-union of two rectangles."""
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    intersection = (ix1 - ix0) * (iy1 - iy0)
    area_a = max(0, (ax1 - ax0) * (ay1 - ay0))
    area_b = max(0, (bx1 - bx0) * (by1 - by0))
    union = area_a + area_b - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def _block_center(block: Dict[str, Any]) -> Tuple[float, float]:
    """Get the center point of an OCR block. Handles both x/y and x0/y0/x1/y1 formats."""
    if "x0" in block and "x1" in block:
        cx = (block["x0"] + block["x1"]) / 2
        cy = (block["y0"] + block["y1"]) / 2
    else:
        # Single-point block: use x, y as approximate center
        cx = block.get("x", 0)
        cy = block.get("y", 0)
    return cx, cy


def _block_bbox(block: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """Get (x0, y0, x1, y1) for an OCR block, inferring from x/y/w/h if needed."""
    if "x0" in block and "x1" in block:
        return block["x0"], block["y0"], block["x1"], block["y1"]
    # Approximate: use x, y as top-left and estimate width from text length
    x = block.get("x", 0)
    y = block.get("y", 0)
    w = block.get("w", len(block.get("text", "")) * 8)  # rough pixel estimate
    h = block.get("h", 20)
    return x, y, x + w, y + h


def _is_likely_label(text: str) -> bool:
    """Check if text looks like a form label rather than a field value."""
    t = text.strip()
    if not t:
        return False
    # Text ending with colon is a label
    if t.endswith(":"):
        return True
    # Text starting with "LABEL:" pattern (e.g., "RANK: ua Tl", "MODEL: Corolla")
    # but not URLs (https://) or time formats (10:30)
    if ":" in t:
        colon_idx = t.index(":")
        prefix = t[:colon_idx].strip()
        if colon_idx < 12 and prefix.isalpha() and prefix.upper() == prefix and len(prefix) >= 2:
            return True
    # ALL-CAPS with 5+ alpha chars and no digits is likely a header/label
    # (short codes like "NY", "LLC", "BA-123" are real values, not labels)
    alpha = [c for c in t if c.isalpha()]
    has_digit = any(c.isdigit() for c in t)
    if len(alpha) >= 5 and t == t.upper() and not has_digit:
        return True
    # Single character (not a checkbox marker) is noise
    if len(t) == 1 and t.lower() not in {"x", "1", "y", "$", "s"}:
        return True
    # Space-separated single letters (e.g., "N N", "Y N") are form yes/no indicators
    parts = t.split()
    if len(parts) >= 2 and all(len(p) == 1 for p in parts):
        return True
    return False


class PositionalMatcher:
    """
    Geometric field matcher using schema positional atlas.

    Aligns atlas positions to actual scan via anchor labels, then matches
    OCR blocks to fields by containment and IoU.
    """

    # Confidence parameters
    BASE_CONFIDENCE = 0.85
    MAX_CONFIDENCE = 0.93
    IOU_THRESHOLD = 0.15
    CONTAINMENT_BONUS = 0.05

    # Checked markers for checkbox detection
    CHECKED_MARKERS = {"x", "1", "y", "yes", "$", "s", "checked", "✓", "✗"}

    def match(
        self,
        schema: FormSchema,
        bbox_pages: List[List[Dict[str, Any]]],
        image_paths: Optional[List[Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        Match OCR blocks to schema fields using positional atlas.

        Args:
            schema: FormSchema with positional data (from enriched schemas).
            bbox_pages: Per-page list of OCR bbox dicts (with x, y, text, etc.).
            image_paths: Optional page images for checkbox pixel analysis.

        Returns:
            (fields_dict, metadata_dict) where:
            - fields_dict: {field_name: extracted_value}
            - metadata_dict: {field_name: {confidence, method, page}}
        """
        if not schema.anchors and not schema.get_positioned_fields():
            return {}, {}

        # Compute alignment offset per page
        offsets = self.compute_alignment(schema, bbox_pages)

        fields: Dict[str, Any] = {}
        metadata: Dict[str, Dict[str, Any]] = {}

        # Track alignment quality for confidence scaling
        alignment_quality = 1.0
        if schema.anchors:
            matched_anchors = sum(
                1 for page_idx in range(len(bbox_pages))
                if page_idx < len(offsets) and offsets[page_idx] != (0.0, 0.0)
            )
            if matched_anchors > 0:
                alignment_quality = min(1.0, 0.7 + 0.3 * (matched_anchors / max(1, len(schema.anchors))))
            else:
                alignment_quality = 0.7

        # Fixed pixel threshold for checkbox detection
        # 0.22 avoids false positives from border artifacts (0.15-0.22 range)
        # Truly checked checkboxes have ratios 0.25+ at 300 DPI
        PIXEL_THRESHOLD = 0.22

        # Process each page
        for page_idx in range(len(bbox_pages)):
            page_fields = schema.get_positioned_fields(page=page_idx)
            if not page_fields:
                continue

            page_blocks = bbox_pages[page_idx] if page_idx < len(bbox_pages) else []
            if not page_blocks:
                continue

            dx, dy = offsets[page_idx] if page_idx < len(offsets) else (0.0, 0.0)
            has_images = image_paths and page_idx < len(image_paths)

            for fi in page_fields:
                fx0 = fi.x_min + dx
                fy0 = fi.y_min + dy
                fx1 = fi.x_max + dx
                fy1 = fi.y_max + dy

                if fi.field_type in ("checkbox", "radio"):
                    value = None
                    method = "positional_checkbox"

                    # Try pixel-based detection first (crop image, count dark pixels)
                    if has_images:
                        ratio = self._get_checkbox_pixel_ratio(
                            fx0, fy0, fx1, fy1, image_paths[page_idx]
                        )
                        if ratio is not None and ratio >= PIXEL_THRESHOLD:
                            value = "1"
                            method = "positional_checkbox_pixel"

                    # Fall back to OCR text marker detection
                    if value is None:
                        value = self._detect_checkbox_state(fx0, fy0, fx1, fy1, page_blocks)

                    if value is not None:
                        conf = self.BASE_CONFIDENCE * alignment_quality
                        fields[fi.name] = value
                        metadata[fi.name] = {
                            "confidence": round(min(self.MAX_CONFIDENCE, conf), 3),
                            "method": method,
                            "page": page_idx,
                        }
                else:
                    value, method = self._match_text_field(
                        fx0, fy0, fx1, fy1, page_blocks
                    )
                    if value and not self._is_invalid_value_for_field(fi.name, value):
                        fields[fi.name] = value
                        bonus = self.CONTAINMENT_BONUS if method == "containment" else 0
                        conf = self.BASE_CONFIDENCE * alignment_quality + bonus
                        metadata[fi.name] = {
                            "confidence": round(min(self.MAX_CONFIDENCE, conf), 3),
                            "method": f"positional_{method}",
                            "page": page_idx,
                        }

        return fields, metadata

    def compute_alignment(
        self,
        schema: FormSchema,
        bbox_pages: List[List[Dict[str, Any]]],
    ) -> List[Tuple[float, float]]:
        """
        Compute (dx, dy) alignment offset per page by matching anchor labels.

        Anchors are known static text positions on the form (e.g., "AGENCY", "CARRIER").
        We find them in the OCR data and compute the median shift.
        """
        num_pages = len(bbox_pages)
        offsets: List[Tuple[float, float]] = [(0.0, 0.0)] * num_pages

        if not schema.anchors:
            return offsets

        # Group anchors by page
        anchors_by_page: Dict[int, List[Dict[str, Any]]] = {}
        for anchor in schema.anchors:
            page = anchor["page"]
            if page not in anchors_by_page:
                anchors_by_page[page] = []
            anchors_by_page[page].append(anchor)

        for page_idx, page_anchors in anchors_by_page.items():
            if page_idx >= num_pages:
                continue

            page_blocks = bbox_pages[page_idx]
            dx_samples: List[float] = []
            dy_samples: List[float] = []

            for anchor in page_anchors:
                anchor_text = anchor["text"].upper().strip()
                expected_x = anchor["x"]
                expected_y = anchor["y"]

                # Find best matching block
                best_block = None
                best_dist = float("inf")

                for block in page_blocks:
                    block_text = block.get("text", "").upper().strip()
                    if anchor_text not in block_text and block_text not in anchor_text:
                        continue

                    bx, by = _block_center(block)
                    dist = abs(bx - expected_x) + abs(by - expected_y)
                    if dist < best_dist:
                        best_dist = dist
                        best_block = block

                if best_block is not None and best_dist < 500:  # sanity: within 500px
                    bx, by = _block_center(best_block)
                    dx_samples.append(bx - expected_x)
                    dy_samples.append(by - expected_y)

            if dx_samples:
                offsets[page_idx] = (
                    statistics.median(dx_samples),
                    statistics.median(dy_samples),
                )

        return offsets

    def _match_text_field(
        self,
        fx0: float, fy0: float, fx1: float, fy1: float,
        page_blocks: List[Dict[str, Any]],
    ) -> Tuple[Optional[str], str]:
        """
        Match OCR blocks to a text field region.

        Strategy:
        1. Containment: blocks whose center falls inside the field bbox
        2. IoU fallback: blocks with IoU > threshold

        Returns:
            (merged_value, method) or (None, "")
        """
        field_width = fx1 - fx0

        # 1. Containment check
        contained = []
        for block in page_blocks:
            cx, cy = _block_center(block)
            if fx0 <= cx <= fx1 and fy0 <= cy <= fy1:
                text = block.get("text", "").strip()
                if text:
                    # Skip blocks wider than 3x the field (column drift)
                    bx0, by0, bx1, by1 = _block_bbox(block)
                    block_width = bx1 - bx0
                    if field_width > 0 and block_width > 3 * field_width:
                        continue
                    contained.append(block)

        if contained:
            value = self._merge_blocks(contained)
            if value:
                return value, "containment"

        # 2. IoU fallback
        best_iou = 0.0
        best_block = None
        for block in page_blocks:
            bx0, by0, bx1, by1 = _block_bbox(block)
            iou = _compute_iou(fx0, fy0, fx1, fy1, bx0, by0, bx1, by1)
            if iou > best_iou:
                best_iou = iou
                best_block = block

        if best_block is not None and best_iou >= self.IOU_THRESHOLD:
            text = best_block.get("text", "").strip()
            if text and not _is_likely_label(text):
                return text, "iou"

        return None, ""

    def _detect_checkbox_state(
        self,
        fx0: float, fy0: float, fx1: float, fy1: float,
        page_blocks: List[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Detect if a checkbox is checked based on OCR blocks in/near its region.

        Returns "1" if checked, None if no clear signal (we don't default to "Off"
        to avoid hurting accuracy — missing is better than wrong).
        """
        # Expand checkbox region slightly for OCR tolerance
        margin = 5.0
        for block in page_blocks:
            cx, cy = _block_center(block)
            if (fx0 - margin) <= cx <= (fx1 + margin) and (fy0 - margin) <= cy <= (fy1 + margin):
                text = block.get("text", "").strip().lower()
                if text in self.CHECKED_MARKERS:
                    return "1"

        return None

    def _get_checkbox_pixel_ratio(
        self,
        fx0: float, fy0: float, fx1: float, fy1: float,
        page_image_path: Path,
    ) -> Optional[float]:
        """
        Compute dark pixel ratio for a checkbox region.

        Crops the checkbox bounding box from the page image, applies a 20%
        inset to exclude border lines, and returns the dark pixel ratio.

        Returns ratio (0.0-1.0) or None if unable to analyze.
        """
        try:
            from PIL import Image
        except ImportError:
            return None

        try:
            img = Image.open(page_image_path)
        except Exception:
            return None

        w_img, h_img = img.size
        # Clamp bbox to image bounds
        x0 = max(0, int(fx0))
        y0 = max(0, int(fy0))
        x1 = min(w_img, int(fx1))
        y1 = min(h_img, int(fy1))

        if x1 <= x0 or y1 <= y0:
            return None

        crop = img.crop((x0, y0, x1, y1)).convert("L")
        cw, ch = crop.size
        if cw < 4 or ch < 4:
            return None

        # 20% inset to exclude border lines
        inset_x = max(1, int(cw * 0.2))
        inset_y = max(1, int(ch * 0.2))
        inner = crop.crop((inset_x, inset_y, cw - inset_x, ch - inset_y))
        iw, ih = inner.size
        if iw < 2 or ih < 2:
            return None

        # Count dark pixels (threshold 140)
        pixels = list(inner.getdata())
        total = len(pixels)
        dark = sum(1 for p in pixels if p < 140)
        return dark / total if total > 0 else 0.0

    @staticmethod
    def _is_invalid_value_for_field(field_name: str, value: str) -> bool:
        """Reject values that are clearly wrong for a given field (column drift)."""
        v = value.strip()
        # ProducerIdentifier should be a small integer (1-13) or alphanumeric ID,
        # NOT a percentage like "100", "50", "75" from the adjacent UsePercent column
        if "ProducerIdentifier" in field_name:
            if v.isdigit() and int(v) in (100, 50, 75, 80, 30, 25, 20, 60, 40, 70, 90, 10, 15):
                return True
        # UsePercent should be a percentage, not a name or alphanumeric code
        if "UsePercent" in field_name:
            if v and not v.isdigit():
                return True
        return False

    def _merge_blocks(self, blocks: List[Dict[str, Any]]) -> Optional[str]:
        """Merge multiple OCR blocks within a field region into a single value."""
        if not blocks:
            return None

        # Filter out common form labels and column headers
        _LABELS = {
            # Original labels
            "agency", "carrier", "naic code", "naic", "date", "policy number",
            "named insured", "producer", "company", "code", "effective date",
            "expiration date", "type of insurance", "policy type",
            # Column headers
            "premium", "deductible", "limit", "amount", "coverage",
            "symbol", "description", "veh #", "yr", "make", "model",
            "vin", "% use", "% owned", "rank",
            # Form labels
            "fein or soc sec #", "zip", "state", "city", "address",
            "phone", "fax", "email", "signature", "total",
            "street", "county", "sic", "naics", "naic code",
            "sub code", "issue policy", "mailing address",
            # Section titles
            "applicant information", "general information",
            "prior carrier information", "loss history", "remarks",
            "processing instructions", "additional remarks schedule",
            "subsidiary information", "contact information",
        }

        value_blocks = []
        for b in blocks:
            text = b.get("text", "").strip()
            if text.lower() not in _LABELS and len(text) >= 1 and not _is_likely_label(text):
                value_blocks.append(b)

        if not value_blocks:
            return None

        # Sort by position: top-to-bottom, then left-to-right
        value_blocks.sort(key=lambda b: (_block_center(b)[1], _block_center(b)[0]))

        if len(value_blocks) == 1:
            return value_blocks[0]["text"].strip()

        # Multiple blocks: join them
        # Group by approximate row (blocks within 15px vertical are same row)
        rows: List[List[Dict]] = []
        current_row: List[Dict] = [value_blocks[0]]
        for b in value_blocks[1:]:
            _, cy = _block_center(b)
            _, prev_cy = _block_center(current_row[-1])
            if abs(cy - prev_cy) < 15:
                current_row.append(b)
            else:
                rows.append(current_row)
                current_row = [b]
        rows.append(current_row)

        # Within each row, sort left-to-right and join with space
        parts = []
        for row in rows:
            row.sort(key=lambda b: _block_center(b)[0])
            row_text = " ".join(b["text"].strip() for b in row)
            parts.append(row_text)

        return " ".join(parts)
