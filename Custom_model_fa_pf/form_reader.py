"""Dynamic AcroForm PDF reader — reads any PDF form and produces a structured field catalog.

Replaces hardcoded field maps by reading widget metadata directly from the PDF,
including tooltips (/TU key), field types, categories (inferred from ACORD naming),
and suffix indices for array fields.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from Custom_model_fa_pf.config import FORM_TEMPLATES_DIR

logger = logging.getLogger(__name__)

# ACORD field-name prefix → category mapping
_CATEGORY_PREFIXES = {
    "Driver": "driver",
    "Vehicle": "vehicle",
    "Coverage": "coverage",
    "Policy": "policy",
    "Producer": "producer",
    "NamedInsured": "named_insured",
    "Applicant": "named_insured",
    "Business": "business",
    "Location": "location",
    "AdditionalInterest": "additional_interest",
    "LossHistory": "loss_history",
    "Loss": "loss_history",
    "PriorCarrier": "prior_carrier",
    "Insurer": "insurer",
    "Agency": "producer",
    "Agent": "producer",
    "Contact": "contact",
    "Remark": "remarks",
    "Form": "form_meta",
}

# Checkbox-indicating keywords (case-insensitive)
_CHECKBOX_KEYWORDS = {
    "indicator", "checkbox", "chk", "option", "flag",
}

# Suffix pattern: _A, _B, ... _M or _1, _2, etc. at end of field name
_SUFFIX_RE = re.compile(r"_([A-M]|\d+)$")

# Known ACORD form signatures: unique field name prefixes → form number
_FORM_SIGNATURES = {
    "125": {"NamedInsured_FullName", "Policy_EffectiveDate", "LOB_"},
    "127": {"Driver_GivenName", "Vehicle_VIN", "Driver_BirthDate"},
    "137": {"Vehicle_Coverage_", "BusinessAutoSymbol_"},
    "163": {"Text15[0]", "Text13[0]", "marital[0]"},
}


@dataclass
class FormField:
    """A single form field extracted from the PDF."""
    name: str
    field_type: str  # text, checkbox, radio, dropdown, signature, unknown
    tooltip: Optional[str] = None
    page: int = 0
    rect: Optional[Tuple[float, float, float, float]] = None  # (x_min, y_min, x_max, y_max)
    category: str = "general"
    suffix: Optional[str] = None  # _A, _B, _1, etc.
    base_name: Optional[str] = None  # field name without suffix
    default_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"name": self.name, "field_type": self.field_type, "page": self.page, "category": self.category}
        if self.tooltip:
            d["tooltip"] = self.tooltip
        if self.rect:
            d["rect"] = list(self.rect)
        if self.suffix:
            d["suffix"] = self.suffix
        if self.base_name:
            d["base_name"] = self.base_name
        if self.default_value:
            d["default_value"] = self.default_value
        return d


@dataclass
class FormSection:
    """A group of related fields."""
    category: str
    page: int
    fields: List[FormField] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "page": self.page,
            "field_count": len(self.fields),
            "fields": [f.name for f in self.fields],
        }


@dataclass
class FormCatalog:
    """Complete catalog of all fields in a PDF form."""
    pdf_path: str
    form_number: Optional[str] = None
    total_fields: int = 0
    fields: Dict[str, FormField] = field(default_factory=dict)
    sections: List[FormSection] = field(default_factory=list)
    text_fields: List[str] = field(default_factory=list)
    checkbox_fields: List[str] = field(default_factory=list)

    def get_fields_by_category(self, category: str) -> List[FormField]:
        return [f for f in self.fields.values() if f.category == category]

    def get_fields_by_page(self, page: int) -> List[FormField]:
        return [f for f in self.fields.values() if f.page == page]

    def get_unmapped_fields(self, mapped_names: set) -> List[FormField]:
        """Return fields not yet mapped."""
        return [f for f in self.fields.values() if f.name not in mapped_names]

    def get_fields_with_tooltips(self) -> List[FormField]:
        return [f for f in self.fields.values() if f.tooltip]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdf_path": self.pdf_path,
            "form_number": self.form_number,
            "total_fields": self.total_fields,
            "text_field_count": len(self.text_fields),
            "checkbox_field_count": len(self.checkbox_fields),
            "sections": [s.to_dict() for s in self.sections],
            "categories": list({f.category for f in self.fields.values()}),
        }


# ---------------------------------------------------------------------------
# Widget type mapping (PyMuPDF widget.field_type constants)
# ---------------------------------------------------------------------------
_WIDGET_TYPE_MAP = {
    fitz.PDF_WIDGET_TYPE_TEXT: "text",
    fitz.PDF_WIDGET_TYPE_CHECKBOX: "checkbox",
    fitz.PDF_WIDGET_TYPE_RADIOBUTTON: "radio",
    fitz.PDF_WIDGET_TYPE_COMBOBOX: "dropdown",
    fitz.PDF_WIDGET_TYPE_LISTBOX: "dropdown",
    fitz.PDF_WIDGET_TYPE_SIGNATURE: "signature",
}


def _get_tooltip(doc: fitz.Document, widget) -> Optional[str]:
    """Extract tooltip (/TU key) from widget's xref."""
    try:
        xref = widget.xref
        if xref <= 0:
            return None
        # Read the field dictionary
        field_obj = doc.xref_get_key(xref, "TU")
        if field_obj and field_obj[0] == "string":
            # Strip parentheses from PDF string
            text = field_obj[1]
            if text.startswith("(") and text.endswith(")"):
                text = text[1:-1]
            # Unescape PDF string
            text = text.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
            return text.strip() if text.strip() else None
    except Exception:
        pass
    return None


def _infer_category(field_name: str) -> str:
    """Infer field category from ACORD naming conventions."""
    # Check known prefixes
    for prefix, category in _CATEGORY_PREFIXES.items():
        if field_name.startswith(prefix):
            return category

    # Check for checkbox indicators
    name_lower = field_name.lower()
    if any(kw in name_lower for kw in _CHECKBOX_KEYWORDS):
        return "checkbox"

    # Generic field names (Form 163 style: TextNN[0])
    if re.match(r"^Text\d+\[\d+\]$", field_name):
        return "generic_text"
    if re.match(r"^marital", field_name, re.I):
        return "driver"

    return "general"


def _extract_suffix(field_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract suffix and base name from a field name.

    Returns:
        (suffix, base_name) — e.g. ("_A", "Driver_GivenName") or (None, None)
    """
    match = _SUFFIX_RE.search(field_name)
    if match:
        suffix = match.group(0)  # e.g. "_A"
        base_name = field_name[:match.start()]
        return suffix, base_name
    return None, None


def _detect_form_number(field_names: set) -> Optional[str]:
    """Auto-detect ACORD form number from field name patterns."""
    best_match = None
    best_score = 0

    for form_num, signatures in _FORM_SIGNATURES.items():
        score = 0
        for sig in signatures:
            if any(sig in fn for fn in field_names):
                score += 1
        if score > best_score:
            best_score = score
            best_match = form_num

    return best_match if best_score >= 2 else None


def read_pdf_form(pdf_path: Path, scale_dpi: int = 300) -> FormCatalog:
    """Read any AcroForm PDF and produce a structured field catalog.

    Args:
        pdf_path: Path to the PDF file
        scale_dpi: DPI for coordinate scaling (default 300 for consistency with schemas)

    Returns:
        FormCatalog with all fields, sections, and metadata
    """
    pdf_path = Path(pdf_path)
    catalog = FormCatalog(pdf_path=str(pdf_path))

    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return catalog

    scale = scale_dpi / 72.0  # PDF points to pixels

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        logger.error(f"Failed to open PDF {pdf_path}: {e}")
        return catalog

    try:
        all_field_names = set()

        for page_num in range(len(doc)):
            page = doc[page_num]

            for widget in page.widgets():
                name = widget.field_name
                if not name:
                    continue

                # Deduplicate (same field can appear on multiple pages in some PDFs)
                if name in catalog.fields:
                    continue

                all_field_names.add(name)

                # Field type
                field_type = _WIDGET_TYPE_MAP.get(widget.field_type, "unknown")

                # Tooltip
                tooltip = _get_tooltip(doc, widget)

                # Bounding rect (scaled to DPI)
                r = widget.rect
                rect = (
                    round(r.x0 * scale, 1),
                    round(r.y0 * scale, 1),
                    round(r.x1 * scale, 1),
                    round(r.y1 * scale, 1),
                )

                # Category and suffix
                category = _infer_category(name)
                suffix, base_name = _extract_suffix(name)

                # Default value
                default_value = widget.field_value
                if default_value and str(default_value).strip() in ("", "Off"):
                    default_value = None

                form_field = FormField(
                    name=name,
                    field_type=field_type,
                    tooltip=tooltip,
                    page=page_num,
                    rect=rect,
                    category=category,
                    suffix=suffix,
                    base_name=base_name,
                    default_value=str(default_value) if default_value else None,
                )

                catalog.fields[name] = form_field

                # Track by type
                if field_type == "checkbox":
                    catalog.checkbox_fields.append(name)
                else:
                    catalog.text_fields.append(name)

        catalog.total_fields = len(catalog.fields)

        # Auto-detect form number
        catalog.form_number = _detect_form_number(all_field_names)

        # Build sections (group by category + page)
        section_key_map: Dict[Tuple[str, int], FormSection] = {}
        for f in catalog.fields.values():
            key = (f.category, f.page)
            if key not in section_key_map:
                section_key_map[key] = FormSection(category=f.category, page=f.page)
            section_key_map[key].fields.append(f)

        catalog.sections = sorted(
            section_key_map.values(),
            key=lambda s: (s.page, s.category),
        )

        logger.info(
            f"Read {catalog.total_fields} fields from {pdf_path.name} "
            f"({len(catalog.text_fields)} text, {len(catalog.checkbox_fields)} checkbox, "
            f"{len(catalog.sections)} sections)"
        )

    finally:
        doc.close()

    return catalog


def find_template(form_number: str) -> Optional[Path]:
    """Find a blank ACORD template PDF by form number."""
    patterns = [
        f"ACORD_{form_number}*.pdf",
        f"acord_{form_number}*.pdf",
        f"*{form_number}*.pdf",
    ]

    for pattern in patterns:
        matches = list(FORM_TEMPLATES_DIR.glob(pattern))
        if matches:
            return matches[0]

    return None


def read_all_templates() -> Dict[str, FormCatalog]:
    """Read all available ACORD template PDFs and return catalogs keyed by form number."""
    catalogs = {}

    if not FORM_TEMPLATES_DIR.exists():
        logger.warning(f"Template directory not found: {FORM_TEMPLATES_DIR}")
        return catalogs

    for pdf_file in sorted(FORM_TEMPLATES_DIR.glob("*.pdf")):
        catalog = read_pdf_form(pdf_file)
        if catalog.form_number:
            catalogs[catalog.form_number] = catalog
        else:
            # Try to extract form number from filename
            match = re.search(r"(\d{3})", pdf_file.stem)
            if match:
                form_num = match.group(1)
                catalog.form_number = form_num
                catalogs[form_num] = catalog

    return catalogs
