"""Stage 5: Fill blank ACORD PDF forms with extracted field values using PyMuPDF."""

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from Custom_model_fa_pf.config import FORM_TEMPLATES_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)


@dataclass
class FillResult:
    form_number: str
    output_path: Optional[Path] = None
    filled_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "form_number": self.form_number,
            "output_path": str(self.output_path) if self.output_path else None,
            "filled_count": self.filled_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "errors": self.errors,
        }


def _find_template(form_number: str) -> Optional[Path]:
    """Find a blank PDF template for the given form number."""
    # Look for template in form_templates directory
    patterns = [
        f"acord_{form_number}_blank.pdf",
        f"acord_{form_number}.pdf",
        f"ACORD_{form_number}*.pdf",
        f"*{form_number}*.pdf",
    ]
    for pattern in patterns:
        matches = list(FORM_TEMPLATES_DIR.glob(pattern))
        if matches:
            return matches[0]
    return None


def fill_pdf(
    form_number: str,
    field_values: Dict[str, str],
    output_path: Path,
    template_path: Optional[Path] = None,
) -> FillResult:
    """Fill a single PDF form with field values.

    Args:
        form_number: ACORD form number (e.g., "125")
        field_values: Dict of field_name -> value
        output_path: Where to save the filled PDF
        template_path: Optional override for template PDF location

    Returns:
        FillResult with fill statistics
    """
    result = FillResult(form_number=form_number)

    try:
        import fitz  # PyMuPDF
    except ImportError:
        result.errors.append("PyMuPDF not installed. Run: uv pip install PyMuPDF")
        result.error_count = len(field_values)
        return result

    # Find template
    if template_path is None:
        template_path = _find_template(form_number)

    if template_path is None or not template_path.exists():
        result.errors.append(f"No template PDF found for Form {form_number}")
        result.error_count = len(field_values)
        return result

    # Copy template to output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_path, output_path)

    # Open and fill
    doc = fitz.open(str(output_path))
    filled_fields = set()

    for page in doc:
        for widget in page.widgets():
            fname = widget.field_name
            if fname not in field_values:
                continue

            value = field_values[fname]

            # Skip read-only fields (form metadata, not user-fillable)
            if widget.field_flags & 1:
                result.skipped_count += 1
                continue

            # Skip widgets with empty/degenerate rects (zero-area, invisible)
            if widget.rect.is_empty or widget.rect.width <= 0 or widget.rect.height <= 0:
                result.skipped_count += 1
                continue

            try:
                if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                    # Checkbox: set to True/False based on value
                    if value in ("1", "True", "true", "Yes", "yes", True):
                        widget.field_value = True
                    else:
                        widget.field_value = False
                else:
                    # Text, dropdown, etc.
                    widget.field_value = str(value)

                widget.update()
                filled_fields.add(fname)
                result.filled_count += 1
            except Exception as e:
                result.errors.append(f"Error filling {fname}: {e}")
                result.error_count += 1

    # Count fields not found in PDF (add to skipped_count from read-only/bad-rect)
    not_found = len(field_values) - len(filled_fields) - result.error_count - result.skipped_count
    if not_found > 0:
        result.skipped_count += not_found
        skipped = set(field_values.keys()) - filled_fields
        logger.debug(f"Form {form_number}: {not_found} fields not found in PDF: {sorted(skipped)[:5]}")

    doc.saveIncr()
    doc.close()
    result.output_path = output_path

    logger.info(
        f"Form {form_number}: filled {result.filled_count}/{len(field_values)} fields "
        f"(skipped {result.skipped_count}, errors {result.error_count})"
    )
    return result


def fill_all(
    all_field_values: Dict[str, Dict[str, str]],
    output_dir: Optional[Path] = None,
) -> List[FillResult]:
    """Fill all assigned forms.

    Args:
        all_field_values: Dict of form_number -> {field_name: value}
        output_dir: Directory for output PDFs

    Returns:
        List of FillResult for each form
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR

    results = []
    for form_number, field_values in all_field_values.items():
        output_path = output_dir / f"ACORD_{form_number}_filled.pdf"
        result = fill_pdf(form_number, field_values, output_path)
        results.append(result)

    return results
