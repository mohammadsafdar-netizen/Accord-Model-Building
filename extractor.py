#!/usr/bin/env python3
"""
ACORD Extractor: Category-by-category extraction pipeline
==========================================================
The core extraction pipeline for scanned ACORD forms 125, 127, 137.

Architecture:
  1. OCR Engine produces structured text + spatial data
  2. Schema Registry provides field names, tooltips, categories
  3. Extractor walks through categories in order:
     - header -> insurer -> producer -> named_insured -> policy
     - driver (127 only) -> vehicle (127/137) -> coverage (137)
     - remaining fields (gap-fill)
  4. Each category uses a two-pass strategy:
     Pass 1: Docling-guided (structured markdown + tooltips)
     Pass 2: BBox-guided gap-fill (spatial positions for missed fields)
  5. Verification: cross-check values against BBox OCR text
  6. Normalisation: dates, checkboxes, field name validation
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ocr_engine import OCREngine, OCRResult
from llm_engine import LLMEngine
from schema_registry import SchemaRegistry, EXTRACTION_ORDER, detect_form_type
from prompts import (
    build_extraction_prompt,
    build_driver_row_prompt,
    build_vehicle_prompt,
    build_gap_fill_prompt,
)
from spatial_extract import spatial_preextract


class ACORDExtractor:
    """
    High-accuracy extraction pipeline for scanned ACORD forms.

    Usage:
        ocr = OCREngine()
        llm = LLMEngine(model="qwen2.5:7b")
        registry = SchemaRegistry()
        extractor = ACORDExtractor(ocr, llm, registry)
        result = extractor.extract("path/to/form.pdf")
    """

    def __init__(
        self,
        ocr_engine: OCREngine,
        llm_engine: LLMEngine,
        schema_registry: SchemaRegistry,
    ):
        self.ocr = ocr_engine
        self.llm = llm_engine
        self.registry = schema_registry

    # ==================================================================
    # Main entry point
    # ==================================================================

    def extract(
        self,
        pdf_path: str | Path,
        form_type: Optional[str] = None,
        output_dir: Optional[str | Path] = None,
    ) -> Dict[str, Any]:
        """
        Extract fields from a scanned ACORD form.

        Args:
            pdf_path: Path to the PDF.
            form_type: "125", "127", or "137". Auto-detected if None.
            output_dir: Directory for intermediate files (images, OCR cache).

        Returns:
            Dict with keys:
              - extracted_fields: {field_name: value}
              - metadata: timing, counts, form_type, model
        """
        pdf_path = Path(pdf_path)
        if output_dir is None:
            output_dir = pdf_path.parent / "best_project_output" / pdf_path.stem
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        start = time.time()

        # ---- Step 0: Free GPU for OCR ------------------------------------
        print(f"\n{'='*60}")
        print(f"  ACORD FORM EXTRACTION")
        print(f"  PDF: {pdf_path.name}")
        print(f"{'='*60}")
        # Unload LLM from GPU so Docling and EasyOCR can each use it
        self.llm.unload_model()

        # ---- Step 1: OCR (GPU sequenced inside) --------------------------
        # process() does: Docling GPU → unload → EasyOCR GPU → unload
        # After this, GPU is fully free for the LLM
        ocr_result = self.ocr.process(pdf_path, output_dir)

        # ---- Step 2: Detect form type -----------------------------------
        if form_type is None:
            form_type = detect_form_type(
                ocr_result.full_docling_text, pdf_path.name
            )
            if form_type is None:
                raise ValueError(
                    f"Could not auto-detect form type from {pdf_path.name}. "
                    "Pass form_type='125', '127', or '137' explicitly."
                )
        print(f"\n  Form type: ACORD {form_type}")

        schema = self.registry.get_schema(form_type)
        if schema is None:
            raise ValueError(f"No schema loaded for ACORD {form_type}")

        # ---- Step 3: Prepare OCR text ------------------------------------
        docling_text = ocr_result.full_docling_text
        all_bbox = ocr_result.all_bbox_data()
        bbox_text = OCREngine.format_bbox_as_rows(all_bbox)
        bbox_plain = OCREngine.format_bbox_as_text(all_bbox)

        # Page-specific data for focused extraction
        page_docling = ocr_result.docling_pages  # per-page markdown
        page_bbox = ocr_result.bbox_pages  # per-page bbox dicts

        # Format page-specific bbox text
        page_bbox_text: List[str] = []
        for pd in page_bbox:
            page_bbox_text.append(OCREngine.format_bbox_as_rows(pd))

        # Label-value pairs per page
        page_lv_text: List[str] = []
        for si in ocr_result.spatial_indices:
            lv = ""
            for pair in si.label_value_pairs:
                lv += f"{pair.label.text} -> {pair.value.text}\n"
            page_lv_text.append(lv)

        # All-pages label-value text
        lv_text = "\n".join(page_lv_text)

        # Category -> pages mapping (which pages to look at)
        # For forms: header/insurer/producer/named_insured are on page 1
        # Driver tables are on page 1 (127) or pages 1-2
        # Other content may span all pages
        CAT_PAGES = {
            "header": [0],
            "insurer": [0],
            "producer": [0],
            "named_insured": [0],
        }

        def _get_context_for_pages(page_indices: List[int]) -> tuple:
            """Get focused OCR context for specific pages."""
            doc = "\n\n".join(page_docling[i] for i in page_indices if i < len(page_docling))
            bb = "\n".join(page_bbox_text[i] for i in page_indices if i < len(page_bbox_text))
            lv = "\n".join(page_lv_text[i] for i in page_indices if i < len(page_lv_text))
            return doc, bb, lv

        # ---- Step 3a: Save intermediate OCR outputs for monitoring ----------
        self._save_intermediate(ocr_result, page_bbox_text, page_lv_text, output_dir)

        # ---- Step 3b: Spatial pre-extraction (high-confidence fields) ------
        print("\n  [SPATIAL] Pre-extracting from BBox positions ...")
        spatial_fields = spatial_preextract(form_type, page_bbox)
        print(f"    -> {len(spatial_fields)} fields pre-extracted spatially")
        # Save spatial pre-extraction results
        from utils import save_json as _save
        _save(spatial_fields, output_dir / "spatial_preextract.json")

        if spatial_fields:
            # Show key fields found
            for key in ["Insurer_FullName_A", "Insurer_NAICCode_A", 
                        "Producer_FullName_A", "NamedInsured_FullName_A",
                        "Policy_PolicyNumberIdentifier_A", "Form_CompletionDate_A"]:
                if key in spatial_fields:
                    print(f"    {key}: {spatial_fields[key]}")

        # ---- Step 4: Category-by-category extraction ---------------------
        extracted: Dict[str, Any] = {}
        # Start with spatially pre-extracted fields (highest confidence)
        extracted.update(spatial_fields)
        all_field_names = set(schema.fields.keys())

        # Determine which categories to extract
        categories = [c for c in EXTRACTION_ORDER if c in schema.categories]

        # Special handling categories (extracted separately)
        special = {"driver", "vehicle"}

        step = 0
        total_steps = len([c for c in categories if c not in special])
        # Add special steps
        if "driver" in schema.categories and form_type == "127":
            total_steps += 1
        if "vehicle" in schema.categories and form_type in ("127", "137"):
            total_steps += 1
        total_steps += 1  # gap-fill pass

        for category in categories:
            if category in special:
                continue  # handled separately below

            step += 1
            field_names = schema.categories.get(category, [])
            if not field_names:
                continue

            # Use page-focused context for certain categories
            if category in CAT_PAGES:
                cat_doc, cat_bb, cat_lv = _get_context_for_pages(CAT_PAGES[category])
            else:
                cat_doc, cat_bb, cat_lv = docling_text, bbox_text, lv_text

            # Skip fields already pre-extracted spatially
            remaining = [f for f in field_names if f not in extracted]
            if not remaining:
                print(f"\n  [{step}/{total_steps}] {category}: all {len(field_names)} fields already pre-extracted")
                continue

            print(f"\n  [{step}/{total_steps}] Extracting {category} ({len(remaining)}/{len(field_names)} fields) ...")
            cat_result = self._extract_category(
                form_type, category, remaining, cat_doc, cat_bb, cat_lv
            )
            # Only add LLM results for fields not already spatially extracted
            for k, v in cat_result.items():
                if k not in extracted:
                    extracted[k] = v
            print(f"    -> {len(cat_result)} fields extracted")

        # ---- Driver extraction (127 only) --------------------------------
        if form_type == "127" and "driver" in schema.categories:
            step += 1
            # Count how many driver fields are already spatially extracted
            driver_fields = schema.categories.get("driver", [])
            pre_extracted_drivers = [f for f in driver_fields if f in extracted]
            remaining_drivers = [f for f in driver_fields if f not in extracted]
            
            if pre_extracted_drivers:
                print(f"\n  [{step}/{total_steps}] Drivers: {len(pre_extracted_drivers)} pre-extracted, {len(remaining_drivers)} remaining for LLM ...")
            else:
                print(f"\n  [{step}/{total_steps}] Extracting drivers ...")
            
            driver_result = self._extract_all_drivers(
                form_type, schema, ocr_result, docling_text, bbox_text
            )
            # Only add LLM results for fields not already spatially extracted
            new_count = 0
            for k, v in driver_result.items():
                if k not in extracted:
                    extracted[k] = v
                    new_count += 1
            print(f"    -> {new_count} additional driver fields from LLM")

        # ---- Vehicle extraction (127 / 137) ------------------------------
        if form_type in ("127", "137") and "vehicle" in schema.categories:
            step += 1
            print(f"\n  [{step}/{total_steps}] Extracting vehicles ...")
            vehicle_result = self._extract_all_vehicles(
                form_type, schema, docling_text, bbox_text
            )
            # Only add LLM results for fields not already spatially extracted
            new_vehicle = 0
            for k, v in vehicle_result.items():
                if k not in extracted:
                    extracted[k] = v
                    new_vehicle += 1
            print(f"    -> {new_vehicle} vehicle fields extracted")

        # ---- Gap-fill pass -----------------------------------------------
        step += 1
        missing = [n for n in all_field_names if n not in extracted]
        if missing:
            print(f"\n  [{step}/{total_steps}] Gap-fill pass ({len(missing)} missing fields) ...")
            gap_result = self._gap_fill(form_type, missing, bbox_text, lv_text)
            # Only add fields that weren't already extracted
            new_count = 0
            for k, v in gap_result.items():
                if k not in extracted and v:
                    extracted[k] = v
                    new_count += 1
            print(f"    -> {new_count} additional fields recovered")

        # ---- Verification ------------------------------------------------
        print("\n  [VERIFY] Cross-checking against BBox OCR text ...")
        verified = self._verify_with_bbox(extracted, bbox_plain)
        print(f"    {len(verified)}/{len(extracted)} values found in OCR text")

        # ---- Normalise ---------------------------------------------------
        extracted = self._normalise(extracted, form_type)

        # ---- Validate field names ----------------------------------------
        # Spatial fields are protected from schema validation (they use GT-matching names)
        spatial_keys = set(spatial_fields.keys())
        pre_validation_count = len(extracted)
        validated = self.registry.validate_field_names(form_type, extracted)
        # Re-add spatially-extracted fields that were filtered out
        for k, v in extracted.items():
            if k in spatial_keys and k not in validated:
                validated[k] = v
        extracted = validated
        post_validation_count = len(extracted)
        
        if pre_validation_count != post_validation_count:
            print(f"  [DEBUG] {pre_validation_count - post_validation_count} fields removed by schema validation")
            print(f"  [DEBUG] {post_validation_count} fields remaining after validation")

        # ---- Unload LLM from GPU (done with this form) -------------------
        self.llm.unload_model()

        elapsed = time.time() - start

        print(f"\n{'='*60}")
        print(f"  EXTRACTION COMPLETE")
        print(f"  Fields extracted: {len(extracted)}")
        print(f"  Time: {elapsed:.1f}s")
        print(f"{'='*60}\n")

        return {
            "extracted_fields": extracted,
            "metadata": {
                "form_type": form_type,
                "source_pdf": str(pdf_path),
                "fields_extracted": len(extracted),
                "fields_verified": len(verified),
                "total_schema_fields": schema.total_fields,
                "pages": ocr_result.num_pages,
                "extraction_time_seconds": round(elapsed, 2),
                "model": self.llm.model,
            },
        }

    # ==================================================================
    # Intermediate output saving
    # ==================================================================

    def _save_intermediate(
        self,
        ocr_result,
        page_bbox_text: List[str],
        page_lv_text: List[str],
        output_dir: Path,
    ) -> None:
        """Save all intermediate OCR outputs for full monitoring."""
        from utils import save_json

        # 1. Docling markdown per page
        save_json(ocr_result.docling_pages, output_dir / "docling_pages.json")

        # 2. EasyOCR bounding box data per page
        save_json(ocr_result.bbox_pages, output_dir / "bbox_pages.json")

        # 3. Full bbox rows (human-readable)
        all_bbox = ocr_result.all_bbox_data()
        rows_text = OCREngine.format_bbox_as_rows(all_bbox)
        with open(output_dir / "bbox_rows.txt", "w") as f:
            f.write(rows_text)

        # 4. Per-page bbox rows
        for page_num, ptext in enumerate(page_bbox_text, 1):
            with open(output_dir / f"bbox_rows_page{page_num}.txt", "w") as f:
                f.write(ptext)

        # 5. Label-value pairs
        lv_combined = ""
        for page_num, lv in enumerate(page_lv_text, 1):
            lv_combined += f"--- Page {page_num} ---\n{lv}\n"
        with open(output_dir / "label_value_pairs.txt", "w") as f:
            f.write(lv_combined)

        # 6. Spatial index summary per page
        si_summary = []
        for page_num, si in enumerate(ocr_result.spatial_indices, 1):
            si_summary.append({
                "page": page_num,
                "blocks": len(si.blocks),
                "rows": len(si.rows),
                "columns": len(si.columns),
                "tables": len(si.tables),
                "label_value_pairs": len(si.label_value_pairs),
            })
        save_json(si_summary, output_dir / "spatial_index_summary.json")

        print(f"  [SAVE] All intermediate outputs saved to {output_dir}")

    # ==================================================================
    # Category extraction (two-pass)
    # ==================================================================

    def _extract_category(
        self,
        form_type: str,
        category: str,
        field_names: List[str],
        docling_text: str,
        bbox_text: str,
        lv_text: str = "",
    ) -> Dict[str, Any]:
        """Extract one category of fields using a two-pass strategy.
        
        Large categories are batched into sub-batches of BATCH_SIZE fields
        to keep LLM context focused and JSON template manageable.
        """
        BATCH_SIZE = 30
        tooltips = self.registry.get_tooltips(form_type, field_names)
        result: Dict[str, Any] = {}

        # --- Pass 1: Extract in batches ---
        for i in range(0, len(field_names), BATCH_SIZE):
            batch = field_names[i:i + BATCH_SIZE]
            batch_tooltips = {k: v for k, v in tooltips.items() if k in batch}

            prompt = build_extraction_prompt(
                form_type=form_type,
                category=category,
                field_names=batch,
                tooltips=batch_tooltips,
                docling_text=docling_text,
                bbox_text=bbox_text,
                label_value_text=lv_text,
            )
            response = self.llm.generate(prompt)
            batch_result = self.llm.parse_json(response)
            
            # Only keep fields that match the requested batch
            for k, v in batch_result.items():
                if k in batch and v is not None:
                    result[k] = v

        # --- Pass 2: Gap-fill for missing fields ---
        extracted_keys = set(result.keys())
        missing = [n for n in field_names if n not in extracted_keys]

        if missing and len(missing) < len(field_names):  # some but not all missed
            for i in range(0, len(missing), BATCH_SIZE):
                gap_batch = missing[i:i + BATCH_SIZE]
                gap_tooltips = {k: v for k, v in tooltips.items() if k in gap_batch}
                gap_prompt = build_gap_fill_prompt(
                    form_type=form_type,
                    missing_fields=gap_batch,
                    tooltips=gap_tooltips,
                    bbox_text=bbox_text,
                    label_value_text=lv_text,
                )
                gap_response = self.llm.generate(gap_prompt)
                gap_result = self.llm.parse_json(gap_response)
                for k, v in gap_result.items():
                    if k not in result and k in gap_batch and v is not None:
                        result[k] = v

        return result

    # ==================================================================
    # Driver extraction (ACORD 127)
    # ==================================================================

    def _extract_all_drivers(
        self,
        form_type: str,
        schema,
        ocr_result: OCRResult,
        docling_text: str,
        bbox_text: str,
    ) -> Dict[str, Any]:
        """Extract all driver rows from ACORD 127.
        
        Pre-extracts driver table rows from spatial data for accurate
        row-by-row extraction.
        """
        suffix_groups = self.registry.get_suffix_groups(form_type, "driver")
        all_drivers: Dict[str, Any] = {}

        # Build dynamic column map from spatial analysis (page 1)
        column_map = self._detect_driver_columns(ocr_result)

        # Pre-extract driver table rows from spatial index
        driver_rows = self._extract_driver_table_rows(ocr_result)

        for suffix_key in sorted(suffix_groups.keys()):
            if suffix_key == "_NONE":
                continue
            suffix = suffix_key.lstrip("_")
            driver_num = ord(suffix) - ord('A') + 1
            field_names = suffix_groups[suffix_key]
            tooltips = self.registry.get_tooltips(form_type, field_names)

            # Get pre-extracted row data for this driver
            row_data = driver_rows.get(driver_num, "")

            print(f"    Driver {suffix} (#{driver_num}) - {len(field_names)} fields ...")
            prompt = build_driver_row_prompt(
                driver_num=driver_num,
                suffix=suffix,
                field_names=field_names,
                tooltips=tooltips,
                docling_text=docling_text,
                bbox_text=bbox_text,
                column_map=column_map,
                row_data=row_data,
            )
            response = self.llm.generate(prompt)
            result = self.llm.parse_json(response)
            # Only keep fields matching this driver's suffix
            for k, v in result.items():
                if k in field_names and v is not None:
                    all_drivers[k] = v

        return all_drivers

    def _extract_driver_table_rows(
        self, ocr_result: OCRResult
    ) -> Dict[int, str]:
        """
        Pre-extract driver table rows from spatial data.
        
        Returns {driver_num: formatted_row_text} for each detected driver row.
        """
        if not ocr_result.spatial_indices:
            return {}

        # Driver table is typically on page 1 (maybe page 2 for long forms)
        driver_rows: Dict[int, str] = {}

        for page_idx in range(min(2, len(ocr_result.spatial_indices))):
            si = ocr_result.spatial_indices[page_idx]
            if not si.tables:
                continue

            table = si.tables[0]
            data_rows = table.rows[1:] if table.header_row else table.rows

            for row_idx, row in enumerate(data_rows):
                # Check if this row starts with a number (driver #)
                if not row.blocks:
                    continue
                first_text = row.blocks[0].text.strip()
                try:
                    driver_num = int(first_text)
                except ValueError:
                    # Sometimes the row number is embedded in text
                    match = re.match(r'^(\d+)', first_text)
                    if match:
                        driver_num = int(match.group(1))
                    else:
                        driver_num = row_idx + 1

                # Format row as: "text1 [X=pos1] | text2 [X=pos2] | ..."
                parts = []
                for block in sorted(row.blocks, key=lambda b: b.x):
                    parts.append(f"{block.text} [X={block.x}]")
                row_text = " | ".join(parts)
                driver_rows[driver_num] = row_text

        return driver_rows

    def _detect_driver_columns(self, ocr_result: OCRResult) -> Optional[Dict[str, int]]:
        """
        Try to detect driver table column positions dynamically
        from the spatial index of page 1.
        """
        if not ocr_result.spatial_indices:
            return None

        si = ocr_result.spatial_indices[0]  # page 1
        if not si.tables:
            return None

        table = si.tables[0]
        if not table.header_row:
            return None

        # Map header text to column X positions
        col_map: Dict[str, int] = {}
        for block in table.header_row.blocks:
            text = block.text.strip().upper()
            if "NAME" in text and "FIRST" in text:
                col_map["First Name"] = block.x
            elif "NAME" in text and ("LAST" in text or "SURNAME" in text):
                col_map["Last Name"] = block.x
            elif "CITY" in text:
                col_map["City"] = block.x
            elif "STATE" in text:
                col_map["State"] = block.x
            elif "ZIP" in text:
                col_map["Zip"] = block.x
            elif "SEX" in text or "GENDER" in text:
                col_map["Sex"] = block.x
            elif "DOB" in text or "BIRTH" in text:
                col_map["DOB"] = block.x
            elif "LICENSE" in text and "STATE" not in text:
                col_map["License"] = block.x
            elif "MARITAL" in text:
                col_map["Marital"] = block.x

        return col_map if col_map else None

    # ==================================================================
    # Vehicle extraction (ACORD 127 / 137)
    # ==================================================================

    def _extract_all_vehicles(
        self,
        form_type: str,
        schema,
        docling_text: str,
        bbox_text: str,
    ) -> Dict[str, Any]:
        """Extract all vehicle rows."""
        suffix_groups = self.registry.get_suffix_groups(form_type, "vehicle")
        all_vehicles: Dict[str, Any] = {}

        for suffix_key in sorted(suffix_groups.keys()):
            if suffix_key == "_NONE":
                continue
            suffix = suffix_key.lstrip("_")
            field_names = suffix_groups[suffix_key]
            tooltips = self.registry.get_tooltips(form_type, field_names)

            print(f"    Vehicle {suffix} - {len(field_names)} fields ...")
            prompt = build_vehicle_prompt(
                form_type=form_type,
                suffix=suffix,
                field_names=field_names,
                tooltips=tooltips,
                docling_text=docling_text,
                bbox_text=bbox_text,
            )
            response = self.llm.generate(prompt)
            result = self.llm.parse_json(response)
            all_vehicles.update(result)

        return all_vehicles

    # ==================================================================
    # Gap-fill
    # ==================================================================

    def _gap_fill(
        self,
        form_type: str,
        missing_fields: List[str],
        bbox_text: str,
        lv_text: str = "",
    ) -> Dict[str, Any]:
        """Second-pass extraction for fields missed in the first pass."""
        if not missing_fields:
            return {}

        tooltips = self.registry.get_tooltips(form_type, missing_fields)

        # Batch in groups of 30 for focused extraction
        all_result: Dict[str, Any] = {}
        batch_size = 30
        for i in range(0, len(missing_fields), batch_size):
            batch = missing_fields[i:i + batch_size]
            batch_tooltips = {k: v for k, v in tooltips.items() if k in batch}
            prompt = build_gap_fill_prompt(
                form_type=form_type,
                missing_fields=batch,
                tooltips=batch_tooltips,
                bbox_text=bbox_text,
                label_value_text=lv_text,
            )
            response = self.llm.generate(prompt)
            result = self.llm.parse_json(response)
            # Only keep fields matching requested batch
            for k, v in result.items():
                if k in batch and v is not None:
                    all_result[k] = v

        return all_result

    # ==================================================================
    # Verification
    # ==================================================================

    def _verify_with_bbox(
        self,
        extracted: Dict[str, Any],
        bbox_plain: str,
    ) -> Dict[str, Any]:
        """Cross-check extracted values against BBox OCR text."""
        bbox_lower = bbox_plain.lower()
        verified: Dict[str, Any] = {}

        for key, value in extracted.items():
            if value is None or str(value).strip() == "":
                continue
            str_val = str(value).lower().strip()
            if str_val in bbox_lower:
                verified[key] = value
            elif len(str_val) > 3:
                words = str_val.split()
                if any(w in bbox_lower for w in words if len(w) > 2):
                    verified[key] = value
            else:
                # Keep short values (e.g., "M", "F", "1", "Off")
                verified[key] = value

        return verified

    # ==================================================================
    # Normalisation
    # ==================================================================

    def _normalise(self, extracted: Dict[str, Any], form_type: str) -> Dict[str, Any]:
        """Normalise extracted values: dates, checkboxes, empty removal.
        
        Uses schema field types to identify checkboxes (not just name patterns).
        """
        normalised: Dict[str, Any] = {}
        schema = self.registry.get_schema(form_type)

        # Build set of checkbox field names from schema
        checkbox_fields: Set[str] = set()
        if schema:
            for fname, finfo in schema.fields.items():
                if finfo.field_type in ("checkbox", "radio"):
                    checkbox_fields.add(fname)

        for key, value in extracted.items():
            if value is None:
                continue
            str_val = str(value).strip()
            if str_val in ("", "null", "None", "N/A", "n/a"):
                continue

            # Checkbox normalisation - FORCE to "1" or "Off" only
            is_checkbox = (
                key in checkbox_fields
                or "indicator" in key.lower()
                or key.lower().startswith("chk")
            )
            if is_checkbox:
                lower = str_val.lower()
                if lower in ("true", "yes", "1", "on", "x", "checked"):
                    normalised[key] = "1"
                else:
                    # Anything that's not clearly "checked" is treated as unchecked
                    normalised[key] = "Off"
                continue

            # Boolean normalisation for non-checkbox fields
            if isinstance(value, bool):
                normalised[key] = "true" if value else "false"
                continue

            normalised[key] = str_val

        return normalised
