#!/usr/bin/env python3
"""
Build Field Atlas: Enrich schema JSONs with widget positions from AcroForm PDFs
=================================================================================
Extracts widget.rect from reference AcroForm PDFs, converts to 300 DPI pixel
coordinates, and writes positions directly into schemas/*.json.

This gives the pipeline a complete positional atlas so that at runtime, OCR
text blocks can be matched to schema fields by geometric overlap — no LLM needed.

Usage:
    .venv/bin/python build_field_atlas.py --form 125 --pdf test_data/.../form.pdf
    .venv/bin/python build_field_atlas.py --all
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF (fitz) is required. Install: uv pip install PyMuPDF")


# PDF points to pixels at target DPI
POINTS_TO_PIXELS_300DPI = 300.0 / 72.0  # = 4.1667

# Known anchor labels for alignment (static text that appears on every form)
ANCHOR_LABELS_BY_FORM = {
    "125": [
        "AGENCY", "CARRIER", "NAIC CODE", "POLICY NUMBER",
        "DATE", "NAMED INSURED", "PRODUCER",
    ],
    "127": [
        "AGENCY", "CARRIER", "NAIC CODE", "POLICY NUMBER",
        "NAMED INSURED",
    ],
    "137": [
        "AGENCY", "CARRIER", "NAIC CODE", "POLICY NUMBER",
        "NAMED INSURED",
    ],
}

# Default reference PDFs (first PDF found in each test_data subfolder)
FORM_FOLDERS = {
    "125": "ACORD_0125_CommercialInsurance_Acroform",
    "127": "127_Business_Auto_Section_2015_12",
    "137": "ACORD_137",
}


def extract_widget_positions(
    pdf_path: Path,
    target_dpi: int = 300,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extract widget names and bounding boxes from an AcroForm PDF.

    Returns:
        (widget_positions, text_anchors) where:
        - widget_positions: {field_name: {page, x_min, y_min, x_max, y_max}}
        - text_anchors: [{text, page, x, y}] for known label positions
    """
    scale = target_dpi / 72.0
    doc = fitz.open(str(pdf_path))
    positions: Dict[str, Dict[str, Any]] = {}
    text_blocks_by_page: Dict[int, List[Dict[str, Any]]] = {}

    for page_idx in range(len(doc)):
        page = doc[page_idx]

        # Extract widget positions
        try:
            widgets = list(page.widgets())
        except Exception:
            widgets = []

        for widget in widgets:
            try:
                name = widget.field_name
                if not name:
                    continue
                rect = widget.rect
                positions[name] = {
                    "page": page_idx,
                    "x_min": round(rect.x0 * scale, 1),
                    "y_min": round(rect.y0 * scale, 1),
                    "x_max": round(rect.x1 * scale, 1),
                    "y_max": round(rect.y1 * scale, 1),
                }
            except Exception:
                continue

        # Extract text blocks for anchor detection
        try:
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            page_texts = []
            for block in blocks:
                if block.get("type") != 0:  # text block
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            bbox = span.get("bbox", (0, 0, 0, 0))
                            page_texts.append({
                                "text": text,
                                "x": round(bbox[0] * scale, 1),
                                "y": round(bbox[1] * scale, 1),
                                "x1": round(bbox[2] * scale, 1),
                                "y1": round(bbox[3] * scale, 1),
                            })
            text_blocks_by_page[page_idx] = page_texts
        except Exception:
            pass

    doc.close()
    return positions, text_blocks_by_page


def find_anchors(
    text_blocks_by_page: Dict[int, List[Dict[str, Any]]],
    form_number: str,
) -> List[Dict[str, Any]]:
    """Find known anchor label positions in extracted text blocks."""
    anchor_labels = ANCHOR_LABELS_BY_FORM.get(form_number, [])
    anchors: List[Dict[str, Any]] = []
    used_labels = set()

    for page_idx, blocks in sorted(text_blocks_by_page.items()):
        for block in blocks:
            text_upper = block["text"].upper().strip()
            for label in anchor_labels:
                if label in used_labels:
                    continue
                if text_upper == label or text_upper.startswith(label):
                    anchors.append({
                        "text": label,
                        "page": page_idx,
                        "x": block["x"],
                        "y": block["y"],
                    })
                    used_labels.add(label)
                    break

    return anchors


def enrich_schema(
    schema_path: Path,
    widget_positions: Dict[str, Dict[str, Any]],
    anchors: List[Dict[str, Any]],
) -> Tuple[int, int]:
    """
    Write widget positions and anchors into a schema JSON file.

    Returns:
        (matched_count, total_fields) — how many fields got positions.
    """
    data = json.loads(schema_path.read_text())
    fields = data.get("fields", {})
    matched = 0

    for field_name, field_data in fields.items():
        # Try exact match first
        pos = widget_positions.get(field_name)

        # Try with leading space stripped (some schema field names have leading spaces)
        if pos is None:
            stripped = field_name.strip()
            pos = widget_positions.get(stripped)

        # Try stripping leading space from widget name
        if pos is None:
            for wname, wpos in widget_positions.items():
                if wname.strip() == field_name.strip():
                    pos = wpos
                    break

        if pos is not None:
            field_data["page"] = pos["page"]
            field_data["x_min"] = pos["x_min"]
            field_data["y_min"] = pos["y_min"]
            field_data["x_max"] = pos["x_max"]
            field_data["y_max"] = pos["y_max"]
            matched += 1

    data["anchors"] = anchors

    # Write back with consistent formatting
    schema_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return matched, len(fields)


def find_reference_pdf(form_number: str, test_data_dir: Path) -> Optional[Path]:
    """Find the first PDF in the test_data subfolder for a form type."""
    folder_name = FORM_FOLDERS.get(form_number)
    if not folder_name:
        return None
    folder = test_data_dir / folder_name
    if not folder.exists():
        return None
    pdfs = sorted(folder.glob("*.pdf"))
    return pdfs[0] if pdfs else None


def validate_positions(
    positions1: Dict[str, Dict[str, Any]],
    positions2: Dict[str, Dict[str, Any]],
    threshold: float = 5.0,
) -> List[str]:
    """Compare positions from two reference PDFs. Return field names with drift > threshold pixels."""
    drifted = []
    for name in positions1:
        if name not in positions2:
            continue
        p1, p2 = positions1[name], positions2[name]
        if p1["page"] != p2["page"]:
            drifted.append(name)
            continue
        max_drift = max(
            abs(p1["x_min"] - p2["x_min"]),
            abs(p1["y_min"] - p2["y_min"]),
            abs(p1["x_max"] - p2["x_max"]),
            abs(p1["y_max"] - p2["y_max"]),
        )
        if max_drift > threshold:
            drifted.append(name)
    return drifted


def main():
    parser = argparse.ArgumentParser(
        description="Enrich schema JSONs with widget positions from AcroForm PDFs"
    )
    parser.add_argument(
        "--form", choices=["125", "127", "137"],
        help="Form type to enrich",
    )
    parser.add_argument(
        "--pdf", type=Path,
        help="Reference PDF path (default: auto-discover from test_data/)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Enrich all form schemas (125, 127, 137)",
    )
    parser.add_argument(
        "--schemas-dir", type=Path, default=None,
        help="Schema directory (default: ./schemas)",
    )
    parser.add_argument(
        "--test-data-dir", type=Path, default=None,
        help="Test data directory (default: ./test_data)",
    )
    parser.add_argument(
        "--validate", type=Path, default=None,
        help="Second reference PDF to validate position consistency",
    )
    args = parser.parse_args()

    root = Path(__file__).parent
    schemas_dir = args.schemas_dir or root / "schemas"
    test_data_dir = args.test_data_dir or root / "test_data"

    forms_to_process = []
    if args.all:
        forms_to_process = ["125", "127", "137"]
    elif args.form:
        forms_to_process = [args.form]
    else:
        parser.error("Specify --form or --all")

    for form_num in forms_to_process:
        print(f"\n{'='*60}")
        print(f"  ACORD {form_num} - Field Atlas Builder")
        print(f"{'='*60}")

        # Find reference PDF
        pdf_path = args.pdf if args.pdf and args.form == form_num else None
        if pdf_path is None:
            pdf_path = find_reference_pdf(form_num, test_data_dir)
        if pdf_path is None or not pdf_path.exists():
            print(f"  ERROR: No reference PDF found for form {form_num}")
            continue

        print(f"  Reference PDF: {pdf_path.name}")

        # Extract widget positions
        positions, text_blocks = extract_widget_positions(pdf_path)
        print(f"  Widgets extracted: {len(positions)}")

        # Find anchor labels
        anchors = find_anchors(text_blocks, form_num)
        print(f"  Anchors found: {len(anchors)}")
        for a in anchors:
            print(f"    {a['text']:20s} page={a['page']} ({a['x']:.0f}, {a['y']:.0f})")

        # Optional: validate against second PDF
        if args.validate and args.validate.exists():
            positions2, _ = extract_widget_positions(args.validate)
            drifted = validate_positions(positions, positions2)
            if drifted:
                print(f"  WARNING: {len(drifted)} fields drifted >5px between PDFs:")
                for name in drifted[:10]:
                    print(f"    - {name}")
            else:
                print(f"  Positions consistent across both PDFs")

        # Enrich schema
        schema_path = schemas_dir / f"{form_num}.json"
        if not schema_path.exists():
            print(f"  ERROR: Schema not found: {schema_path}")
            continue

        matched, total = enrich_schema(schema_path, positions, anchors)
        print(f"  Schema enriched: {matched}/{total} fields got positions ({matched*100/total:.1f}%)")
        print(f"  Written to: {schema_path}")

        # Summary of pages with positioned fields
        page_counts: Dict[int, int] = {}
        for pos in positions.values():
            p = pos["page"]
            page_counts[p] = page_counts.get(p, 0) + 1
        for p in sorted(page_counts):
            print(f"    Page {p}: {page_counts[p]} widgets")


if __name__ == "__main__":
    main()
