#!/usr/bin/env python3
"""
Template Registry: ACORD form template anchoring system
========================================================
ACORD forms are standardized with predictable field positions.
This module loads template definitions (field regions with bounding boxes)
and extracts values by matching template regions against OCR bbox data.

Supports resolution independence via DPI scaling and alignment offset
correction using anchor labels.

Usage:
    from template_registry import TemplateRegistry
    registry = TemplateRegistry()
    template = registry.get_template("125")
    fields = registry.extract_from_template(template, bbox_pages)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FieldRegion:
    """A template-defined region where a form field value appears."""
    field_name: str
    page: int           # 0-indexed page number
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    field_type: str     # "text", "date", "number", "checkbox", "naic", "policy_number"
    extraction_hint: str = ""  # Human-readable hint for what to look for

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        return (self.x_min, self.y_min, self.x_max, self.y_max)

    def contains_point(self, x: float, y: float) -> bool:
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    def scale(self, sx: float, sy: float) -> "FieldRegion":
        """Return a new FieldRegion scaled by (sx, sy)."""
        return FieldRegion(
            field_name=self.field_name,
            page=self.page,
            x_min=self.x_min * sx,
            y_min=self.y_min * sy,
            x_max=self.x_max * sx,
            y_max=self.y_max * sy,
            field_type=self.field_type,
            extraction_hint=self.extraction_hint,
        )

    def offset(self, dx: float, dy: float) -> "FieldRegion":
        """Return a new FieldRegion shifted by (dx, dy)."""
        return FieldRegion(
            field_name=self.field_name,
            page=self.page,
            x_min=self.x_min + dx,
            y_min=self.y_min + dy,
            x_max=self.x_max + dx,
            y_max=self.y_max + dy,
            field_type=self.field_type,
            extraction_hint=self.extraction_hint,
        )


@dataclass
class AnchorLabel:
    """A known label position used for alignment correction."""
    text: str       # Label text to search for (e.g., "AGENCY", "CARRIER")
    page: int
    x: float
    y: float


@dataclass
class FormTemplate:
    """Template for one ACORD form type with field regions."""
    form_number: str
    edition: str
    page_width: float   # Reference page width at template DPI
    page_height: float  # Reference page height at template DPI
    template_dpi: int
    regions: Dict[str, FieldRegion] = field(default_factory=dict)
    anchors: List[AnchorLabel] = field(default_factory=list)

    def scale_to_dpi(self, target_dpi: int) -> "FormTemplate":
        """Return a new template scaled to match target DPI."""
        if target_dpi == self.template_dpi:
            return self
        ratio = target_dpi / self.template_dpi
        new_regions = {
            name: region.scale(ratio, ratio)
            for name, region in self.regions.items()
        }
        new_anchors = [
            AnchorLabel(text=a.text, page=a.page, x=a.x * ratio, y=a.y * ratio)
            for a in self.anchors
        ]
        return FormTemplate(
            form_number=self.form_number,
            edition=self.edition,
            page_width=self.page_width * ratio,
            page_height=self.page_height * ratio,
            template_dpi=target_dpi,
            regions=new_regions,
            anchors=new_anchors,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FormTemplate":
        """Load template from JSON dict."""
        regions = {}
        for name, rd in data.get("regions", {}).items():
            regions[name] = FieldRegion(
                field_name=name,
                page=rd.get("page", 0),
                x_min=rd["x_min"],
                y_min=rd["y_min"],
                x_max=rd["x_max"],
                y_max=rd["y_max"],
                field_type=rd.get("field_type", "text"),
                extraction_hint=rd.get("extraction_hint", ""),
            )
        anchors = []
        for ad in data.get("anchors", []):
            anchors.append(AnchorLabel(
                text=ad["text"],
                page=ad.get("page", 0),
                x=ad["x"],
                y=ad["y"],
            ))
        return cls(
            form_number=data["form_number"],
            edition=data.get("edition", ""),
            page_width=data.get("page_width", 2550),
            page_height=data.get("page_height", 3300),
            template_dpi=data.get("template_dpi", 300),
            regions=regions,
            anchors=anchors,
        )


class TemplateRegistry:
    """
    Loads form templates from JSON files and extracts fields
    by matching template regions against OCR bbox data.
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"
        self.templates_dir = templates_dir
        self.templates: Dict[str, FormTemplate] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        if not self.templates_dir.exists():
            return
        for tf in self.templates_dir.glob("acord_*.json"):
            try:
                data = json.loads(tf.read_text())
                template = FormTemplate.from_dict(data)
                self.templates[template.form_number] = template
                n_regions = len(template.regions)
                n_anchors = len(template.anchors)
                print(f"  [Template] ACORD {template.form_number}: {n_regions} regions, {n_anchors} anchors")
            except Exception as e:
                print(f"  Warning: could not load template {tf.name}: {e}")

    def get_template(self, form_number: str) -> Optional[FormTemplate]:
        return self.templates.get(form_number)

    def compute_alignment_offset(
        self,
        template: FormTemplate,
        bbox_pages: List[List[Dict]],
    ) -> Tuple[float, float]:
        """
        Compute (dx, dy) offset to align template to actual scan
        by matching anchor labels to their positions in bbox data.
        """
        if not template.anchors:
            return (0.0, 0.0)

        dx_sum = 0.0
        dy_sum = 0.0
        count = 0

        for anchor in template.anchors:
            if anchor.page >= len(bbox_pages):
                continue
            page_bbox = bbox_pages[anchor.page]
            anchor_lower = anchor.text.lower()

            for b in page_bbox:
                text = b["text"].strip().lower()
                if anchor_lower in text or text in anchor_lower:
                    dx_sum += b["x"] - anchor.x
                    dy_sum += b["y"] - anchor.y
                    count += 1
                    break  # Use first match per anchor

        if count == 0:
            return (0.0, 0.0)

        return (dx_sum / count, dy_sum / count)

    def extract_from_template(
        self,
        template: FormTemplate,
        bbox_pages: List[List[Dict]],
        dpi: int = 300,
    ) -> Dict[str, Any]:
        """
        Extract field values by looking up bbox data in template-defined regions.

        Args:
            template: Form template with field regions.
            bbox_pages: Per-page list of bbox dicts from OCR.
            dpi: DPI of the scanned images.

        Returns:
            Dict of {field_name: value} for fields found in template regions.
        """
        # Scale template to match scan DPI
        scaled = template.scale_to_dpi(dpi)

        # Compute alignment offset from anchors
        dx, dy = self.compute_alignment_offset(scaled, bbox_pages)

        result: Dict[str, Any] = {}

        for field_name, region in scaled.regions.items():
            # Apply alignment offset
            aligned = region.offset(dx, dy)

            if aligned.page >= len(bbox_pages):
                continue

            page_bbox = bbox_pages[aligned.page]

            # Find blocks within the region
            blocks_in_region = []
            for b in page_bbox:
                if aligned.contains_point(b["x"], b["y"]):
                    blocks_in_region.append(b)

            if not blocks_in_region:
                continue

            # Extract value based on field type
            value = self._extract_value(blocks_in_region, aligned.field_type)
            if value:
                result[field_name] = value

        return result

    def _extract_value(
        self,
        blocks: List[Dict],
        field_type: str,
    ) -> Optional[str]:
        """Extract a typed value from blocks within a region."""
        if not blocks:
            return None

        if field_type == "date":
            for b in blocks:
                m = re.search(r"\d{1,2}/\d{1,2}/\d{4}", b["text"].strip())
                if m:
                    return m.group(0)
            return None

        if field_type == "naic":
            for b in blocks:
                text = b["text"].strip()
                if re.match(r"^\d{5}$", text):
                    return text
            return None

        if field_type == "policy_number":
            for b in blocks:
                text = b["text"].strip()
                if re.match(r"^[A-Z]{1,4}-?\d{5,}$", text):
                    return text
            return None

        if field_type == "checkbox":
            checked_markers = {"x", "1", "y", "yes", "$", "s", "checked"}
            for b in blocks:
                text = b["text"].strip().lower()
                if text in checked_markers:
                    return "1"
            return "Off"

        if field_type == "number":
            for b in blocks:
                text = b["text"].strip()
                cleaned = re.sub(r"[^\d.]", "", text)
                if cleaned:
                    return cleaned
            return None

        # Default: text field
        # Sort by position (top-left first), concatenate
        blocks.sort(key=lambda b: (b["y"], b["x"]))

        # Filter out common labels
        _LABELS = {
            "agency", "carrier", "naic code", "naic", "date", "policy number",
            "named insured", "producer", "company", "code",
        }
        value_blocks = [
            b for b in blocks
            if b["text"].strip().lower() not in _LABELS and len(b["text"].strip()) >= 2
        ]

        if not value_blocks:
            return None

        # For single-line fields, use the longest/best block
        if len(value_blocks) == 1:
            return value_blocks[0]["text"].strip()

        # Multiple blocks: join with space (same row) or use best
        best = max(value_blocks, key=lambda b: (len(b["text"].strip()), b.get("confidence", 0)))
        return best["text"].strip()
