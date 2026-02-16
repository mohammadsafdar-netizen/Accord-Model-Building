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

from ocr_engine import OCREngine, OCRResult, cleanup_gpu_memory
from llm_engine import LLMEngine, VisionModelNotFoundError
from schema_registry import (
    SchemaRegistry, EXTRACTION_ORDER, CATEGORY_BATCHES, SPECIAL_CATEGORIES,
    detect_form_type,
)
from prompts import (
    build_extraction_prompt,
    build_batched_extraction_prompt,
    build_driver_row_prompt,
    build_vehicle_prompt,
    build_gap_fill_prompt,
    build_vision_extraction_prompt,
    build_vision_extraction_prompt_with_region_descriptions,
    build_vision_checkbox_prompt,
    build_vision_unified_prompt,
    build_vision_driver_fields_prompt,
)
from spatial_extract import spatial_preextract
from section_config import get_section_ids_for_category

try:
    from rag_examples import ExampleRAGStore
except ImportError:
    ExampleRAGStore = None  # type: ignore

# Optional: Semantic field matcher (MiniLM embeddings)
try:
    from semantic_matcher import SemanticFieldMatcher, SENTENCE_TRANSFORMERS_AVAILABLE
except ImportError:
    SemanticFieldMatcher = None  # type: ignore
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Optional: Template anchoring
try:
    from template_registry import TemplateRegistry
except ImportError:
    TemplateRegistry = None  # type: ignore

# Optional: Table Transformer
try:
    from table_detector import TableTransformerEngine, TRANSFORMERS_AVAILABLE as TT_AVAILABLE
except ImportError:
    TableTransformerEngine = None  # type: ignore
    TT_AVAILABLE = False

# Optional: Ensemble fusion
try:
    from ensemble import EnsembleFusion
except ImportError:
    EnsembleFusion = None  # type: ignore

# Optional: Positional atlas matching
try:
    from positional_matcher import PositionalMatcher
except ImportError:
    PositionalMatcher = None  # type: ignore

# Optional: Label field map (pre-built label→field lookup)
try:
    from label_field_map import LabelFieldMap
except ImportError:
    LabelFieldMap = None  # type: ignore
from form_sections import (
    get_sections_for_form,
    get_section_scoped_bbox_text,
    get_section_scoped_docling,
    crop_sections_to_images,
    FormSection,
)

try:
    from vision_utils import (
        crop_pages_to_tiles,
        layout_regions_from_docling,
        layout_regions_from_ocr_result,
        regions_from_bbox_pages,
        OCR_ENGINE_AVAILABLE as VISION_LAYOUT_AVAILABLE,
    )
    VISION_UTILS_AVAILABLE = True
except ImportError:
    crop_pages_to_tiles = None  # type: ignore
    layout_regions_from_docling = None  # type: ignore
    layout_regions_from_ocr_result = None  # type: ignore
    regions_from_bbox_pages = None  # type: ignore
    VISION_LAYOUT_AVAILABLE = False
    VISION_UTILS_AVAILABLE = False


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
        use_vision: bool = False,
        use_text_llm: bool = False,
        use_vision_descriptions: bool = False,
        vision_checkboxes_only: bool = False,
        vision_fast: bool = False,
        vision_batch_size: Optional[int] = None,
        vision_max_tokens: int = 16384,
        strict_verify: bool = False,
        rag_store: Optional[Any] = None,
        use_semantic_matching: bool = True,
        use_templates: bool = False,
        use_table_transformer: bool = False,
        use_ensemble: bool = False,
        use_batch_categories: bool = True,
        use_acroform: bool = False,
        use_positional: bool = False,
    ):
        self.ocr = ocr_engine
        self.llm = llm_engine
        self.registry = schema_registry
        self.use_vision = use_vision and bool(getattr(llm_engine, "vision_model", None))
        self.use_text_llm = use_text_llm
        self.use_vision_descriptions = use_vision_descriptions and self.use_vision
        self.vision_checkboxes_only = vision_checkboxes_only
        self.vision_fast = vision_fast
        # General vision pass: fields per VLM call. Higher = fewer calls, needs higher max_tokens. Default 16 for 30B.
        self.vision_batch_size = vision_batch_size
        # Max tokens per VLM response; 16384 reduces "Batch response empty" truncation and allows larger batches.
        self.vision_max_tokens = vision_max_tokens
        # When True, drop extracted values that do not appear in BBox OCR text (reduces hallucinations, may drop some valid paraphrases).
        self.strict_verify = strict_verify
        # Optional RAG: few-shot examples from ground truth (ExampleRAGStore). Improves accuracy.
        self.rag_store = rag_store
        # Feature flags for new capabilities
        self.use_semantic_matching = use_semantic_matching and SENTENCE_TRANSFORMERS_AVAILABLE
        self.use_templates = use_templates and TemplateRegistry is not None
        self.use_table_transformer = use_table_transformer and TableTransformerEngine is not None
        self.use_ensemble = use_ensemble and EnsembleFusion is not None
        self.use_batch_categories = use_batch_categories
        self.use_acroform = use_acroform
        self.use_positional = use_positional and PositionalMatcher is not None
        # Lazy-initialized components
        self._semantic_matcher_cache: Dict[str, Any] = {}
        self._template_registry: Optional[Any] = None
        self._table_transformer: Optional[Any] = None

    # ==================================================================
    # Main entry point
    # ==================================================================

    def extract(
        self,
        pdf_path: str | Path,
        form_type: Optional[str] = None,
        output_dir: Optional[str | Path] = None,
        ocr_result: Optional[OCRResult] = None,
    ) -> Dict[str, Any]:
        """
        Extract fields from a scanned ACORD form.

        Args:
            pdf_path: Path to the PDF.
            form_type: "125", "127", or "137". Auto-detected if None.
            output_dir: Directory for intermediate files (images, OCR cache).
            ocr_result: If provided, skip OCR and use this result (e.g. from LangGraph OCR node).

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

        print(f"\n{'='*60}")
        print(f"  ACORD FORM EXTRACTION")
        print(f"  PDF: {pdf_path.name}")
        print(f"{'='*60}")

        # ---- Step 0 & 1: OCR (or use provided result) --------------------
        if ocr_result is None:
            self.llm.unload_model()
            ocr_result = self.ocr.process(pdf_path, output_dir)
            # VRAM cleanup after OCR so LLM/VLM can use GPU
            cleanup_gpu_memory()
        else:
            # Use pre-computed OCR from e.g. LangGraph OCR node
            pass

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

        # Category -> pages mapping (which pages to look at for focused context)
        num_pages = len(page_docling)
        if form_type == "125":
            CAT_PAGES = {
                "header": [0], "insurer": [0], "producer": [0],
                "named_insured": [0], "policy": [0], "checkbox": [0],
                "location": [1] if num_pages > 1 else [0],
                "general": [1, 2] if num_pages > 2 else ([1] if num_pages > 1 else [0]),
                "loss_history": ([2, 3] if num_pages > 3 else [2]) if num_pages > 2 else [0],
                "remarks": ([2, 3] if num_pages > 3 else [2]) if num_pages > 2 else [0],
            }
        elif form_type == "127":
            CAT_PAGES = {
                "header": [0], "insurer": [0], "producer": [0],
                "named_insured": [0], "policy": [0],
                "driver": [0], "vehicle": [0, 1] if num_pages > 1 else [0],
            }
        elif form_type == "137":
            CAT_PAGES = {
                "header": [0], "insurer": [0], "producer": [0],
                "named_insured": [0], "policy": [0],
                "vehicle": [0, 1] if num_pages > 1 else [0],
                "coverage": [0, 1] if num_pages > 1 else [0],
            }
        else:
            CAT_PAGES = {
                "header": [0], "insurer": [0], "producer": [0],
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

        # ---- Step 3a': Form-specific section detection (header-based clustering) ----
        sections: List[FormSection] = get_sections_for_form(form_type, page_bbox)
        if sections:
            from utils import save_json as _save_json
            sections_debug = [
                {"section_id": s.section_id, "page": s.page, "title": s.title, "crop_bbox": s.crop_bbox, "block_count": len(s.blocks)}
                for s in sections
            ]
            _save_json(sections_debug, output_dir / "form_sections.json")
            print(f"  [SECTIONS] Detected {len(sections)} form sections (header-based)")

        # ---- Step 3b-pre: AcroForm field extraction (debug + optional use) ------
        acroform_fields: Dict[str, Any] = {}
        if ocr_result.acroform_fields:
            # Filter to only fields in the schema
            schema_keys = set(schema.fields.keys()) if schema else set()
            for k, v in ocr_result.acroform_fields.items():
                if k in schema_keys:
                    acroform_fields[k] = v
            if acroform_fields:
                mode_label = "ACTIVE" if self.use_acroform else "DEBUG ONLY"
                print(f"  [ACROFORM] {len(acroform_fields)} fields matched schema (of {len(ocr_result.acroform_fields)} total) [{mode_label}]")
                _save_json = __import__('utils', fromlist=['save_json']).save_json
                _save_json(acroform_fields, output_dir / "acroform_fields_debug.json")

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

        # ---- Step 3b': Template anchoring (opt-in) ------
        template_fields: Dict[str, Any] = {}
        if self.use_templates:
            template_fields = self._run_template_extraction(form_type, page_bbox, output_dir)

        # ---- Step 3b'-pos: Positional atlas matching (opt-in) ------
        positional_fields: Dict[str, Any] = {}
        positional_metadata: Dict[str, Dict[str, Any]] = {}
        if self.use_positional and schema.get_positioned_fields():
            print("\n  [POSITIONAL] Matching OCR blocks to schema field atlas ...")
            matcher = PositionalMatcher()
            checkbox_images = getattr(ocr_result, 'clean_image_paths', None) or getattr(ocr_result, 'image_paths', [])
            positional_fields, positional_metadata = matcher.match(schema, page_bbox, image_paths=checkbox_images)
            print(f"    -> {len(positional_fields)} fields matched positionally")
            from utils import save_json as _save_pos
            _save_pos(positional_fields, output_dir / "positional_fields.json")
            _save_pos(positional_metadata, output_dir / "positional_metadata.json")

        # ---- Step 3b'': Table Transformer (opt-in) ------
        if self.use_table_transformer and ocr_result.image_paths:
            self._run_table_transformer(ocr_result, page_bbox, output_dir)

        # ---- Step 3b''': Collect table markdown for prompts ------
        table_markdown = ""
        if ocr_result.docling_tables_per_page:
            md_parts = []
            for page_idx, tables in enumerate(ocr_result.docling_tables_per_page):
                for t_idx, table in enumerate(tables):
                    md = table.to_markdown()
                    if md:
                        md_parts.append(f"--- Page {page_idx + 1}, Table {t_idx + 1} ---\n{md}")
            table_markdown = "\n\n".join(md_parts)

        # ---- Step 3c: Build empty JSON, pre-fill from OCR, save for VLM ------
        from form_json_builder import (
            build_empty_form_json_from_schema,
            prefill_form_json_from_ocr,
            label_value_pairs_to_json_list,
            save_empty_form_json,
        )
        from utils import save_json as _save_json

        # Initialize semantic matcher if enabled
        semantic_matcher = None
        if self.use_semantic_matching and SemanticFieldMatcher is not None:
            cache_key = form_type
            if cache_key not in self._semantic_matcher_cache:
                try:
                    self._semantic_matcher_cache[cache_key] = SemanticFieldMatcher(schema)
                    print(f"  [SEMANTIC] MiniLM matcher initialized for form {form_type}")
                except Exception as e:
                    print(f"  [SEMANTIC] Failed to initialize: {e}")
            semantic_matcher = self._semantic_matcher_cache.get(cache_key)

        # Initialize label field map (pre-built label→field lookup)
        label_map_obj = None
        if LabelFieldMap is not None:
            try:
                label_map_obj = LabelFieldMap(form_type)
                if label_map_obj.is_loaded:
                    print(f"  [LABEL-MAP] Loaded {label_map_obj.total_labels} label mappings for form {form_type}")
                else:
                    label_map_obj = None
            except Exception as e:
                print(f"  [LABEL-MAP] Failed to load: {e}")

        empty_json = build_empty_form_json_from_schema(schema, use_defaults=False)
        lv_list = label_value_pairs_to_json_list(ocr_result.spatial_indices)
        prefilled_json, prefill_sources, prefill_details = prefill_form_json_from_ocr(
            empty_json, schema, spatial_fields, lv_list,
            semantic_matcher=semantic_matcher,
            label_map=label_map_obj,
        )
        save_empty_form_json(empty_json, output_dir / "empty_form.json")
        _save_json(prefilled_json, output_dir / "prefilled_form.json")
        _save_json(lv_list, output_dir / "label_value_pairs.json")
        _save_json(prefill_sources, output_dir / "prefill_sources.json")
        _save_json(prefill_details, output_dir / "prefill_details.json")
        prefill_count = len([v for v in prefilled_json.values() if v is not None and str(v).strip()])
        semantic_count = sum(1 for v in prefill_sources.values() if v == "semantic")
        label_map_count = sum(1 for v in prefill_sources.values() if v == "label_map")
        prefill_msg = f"  [PREFILL] Empty form JSON pre-filled from OCR: {prefill_count} fields (spatial + label-value"
        if label_map_count:
            prefill_msg += f" + {label_map_count} label-map"
        if semantic_count:
            prefill_msg += f" + {semantic_count} semantic"
        prefill_msg += ")"
        print(prefill_msg)

        # ---- Step 4: Extracted dict = prefilled JSON (VLM/LLM will fill remaining nulls) ------
        extracted: Dict[str, Any] = {}
        field_sources: Dict[str, str] = {}  # "acroform" | "spatial" | "label_map" | "label_value" | "semantic" | "template" | "positional" | "vision" | "text_llm" | "gap_fill"

        # AcroForm fields first (only when --use-acroform is enabled)
        if self.use_acroform and acroform_fields:
            for k, v in acroform_fields.items():
                if v is not None and str(v).strip():
                    extracted[k] = v
                    field_sources[k] = "acroform"

        # Start from prefilled: all OCR-derived values (spatial + label_value + semantic) already in prefilled_json
        for k, v in prefilled_json.items():
            if v is not None and str(v).strip():
                if k not in extracted:
                    extracted[k] = v
                    field_sources[k] = prefill_sources.get(k, "label_value")
        # Ensure spatial fields are marked as spatial
        for k in spatial_fields:
            if not (self.use_acroform and field_sources.get(k) == "acroform"):
                field_sources[k] = "spatial"

        # Merge template fields (don't overwrite spatial or acroform)
        if template_fields:
            for k, v in template_fields.items():
                if k not in extracted and v is not None and str(v).strip():
                    extracted[k] = v
                    field_sources[k] = "template"
            print(f"  [TEMPLATE] {sum(1 for k in template_fields if k in extracted and field_sources.get(k) == 'template')} fields from template anchoring")

        # Merge positional fields (don't overwrite acroform, spatial, or template)
        if positional_fields:
            pos_new = 0
            for k, v in positional_fields.items():
                if k not in extracted and v is not None and str(v).strip():
                    extracted[k] = v
                    field_sources[k] = "positional"
                    pos_new += 1
            print(f"  [POSITIONAL] {pos_new} new fields from positional atlas matching")

        # Initialize ensemble if enabled
        ensemble: Optional[Any] = None
        if self.use_ensemble and EnsembleFusion is not None:
            ensemble = EnsembleFusion()
            # Add AcroForm results (highest confidence) — only when enabled
            if self.use_acroform and acroform_fields:
                ensemble.add_results("acroform", acroform_fields, confidence=0.99)
            # Add spatial results
            ensemble.add_results("spatial", spatial_fields, confidence=0.95)
            # Add template results
            if template_fields:
                ensemble.add_results("template", template_fields, confidence=0.90)
            # Add positional results — split checkbox (pixel) vs text
            if positional_fields:
                pos_checkbox = {}
                pos_text = {}
                for k, v in positional_fields.items():
                    meta = positional_metadata.get(k, {})
                    if meta.get("method", "").startswith("positional_checkbox"):
                        pos_checkbox[k] = v
                    else:
                        pos_text[k] = v
                if pos_checkbox:
                    ensemble.add_results("positional_checkbox", pos_checkbox, confidence=0.91)
                if pos_text:
                    ensemble.add_results("positional", pos_text, confidence=0.88)
            # Add label_map results
            lm_fields = {k: v for k, v in extracted.items() if field_sources.get(k) == "label_map"}
            if lm_fields:
                ensemble.add_results("label_map", lm_fields, confidence=0.92)
            # Add label_value results
            lv_fields = {k: v for k, v in extracted.items() if field_sources.get(k) == "label_value"}
            if lv_fields:
                ensemble.add_results("label_value", lv_fields, confidence=0.75)
            # Add semantic results
            sem_fields = {k: v for k, v in extracted.items() if field_sources.get(k) == "semantic"}
            if sem_fields:
                ensemble.add_results("semantic", sem_fields, confidence=0.80)

        all_field_names = set(schema.fields.keys())

        # Determine which categories to extract
        categories = [c for c in EXTRACTION_ORDER if c in schema.categories]

        # Special handling categories (extracted separately)
        special = {"driver", "vehicle"}

        category_steps = len([c for c in categories if c not in special])
        total_steps = 0
        if self.use_vision and ocr_result.clean_image_paths:
            total_steps += 1  # vision: single unified pass (image + docling + spatial)
        if self.use_text_llm:
            total_steps += category_steps
            if "driver" in schema.categories and form_type == "127":
                total_steps += 1
            if "vehicle" in schema.categories and form_type in ("127", "137"):
                total_steps += 1
            total_steps += 1  # gap-fill pass

        step = 0
        vision_skipped_404 = False  # set True if VLM model not found

        # ---- Step 4a: Vision-first pass (VLM before text LLM for best accuracy) ----
        # When vision runs, text LLM is used only for gap-fill; when vision is off, category-by-category text runs.
        missing_after_spatial = [n for n in all_field_names if n not in extracted]
        if self.use_vision and missing_after_spatial and ocr_result.clean_image_paths:
            self.llm.unload_text_model()
            step += 1
            n_batches = (len(missing_after_spatial) + (self.vision_batch_size or (20 if self.vision_fast else 16)) - 1) // (self.vision_batch_size or (20 if self.vision_fast else 16))
            print(f"\n  [{step}/{total_steps}] Vision pass (VLM) – image + Docling + spatial/OCR ({len(missing_after_spatial)} remaining fields, {n_batches} batch(es)) ...")
            try:
                vision_result = self._vision_pass_unified(
                    form_type=form_type,
                    missing_fields=missing_after_spatial,
                    image_paths=ocr_result.clean_image_paths,
                    docling_text=docling_text,
                    bbox_text=bbox_text,
                    lv_text=lv_text,
                    schema=schema,
                )
            except VisionModelNotFoundError as e:
                print(f"    [VLM] Skipping vision pass: {e}")
                vision_skipped_404 = True
                vision_result = {}
            else:
                new_count = 0
                for k, v in vision_result.items():
                    if field_sources.get(k) == "spatial":
                        continue  # never overwrite high-confidence spatial
                    if k not in extracted and v is not None:
                        extracted[k] = v
                        field_sources[k] = "vision"
                        new_count += 1
                if ensemble:
                    ensemble.add_results("vision", vision_result, confidence=0.70)
                print(f"    -> {new_count} fields from VLM (unified)")
            self.llm.unload_vision_model()
            # VRAM cleanup after vision pass
            cleanup_gpu_memory()

        # When VLM was used for extraction, skip text-LLM category/driver/vehicle (VLM got all data)
        vision_actually_ran = bool(
            self.use_vision and ocr_result.clean_image_paths and not vision_skipped_404
        )
        if vision_actually_ran:
            total_steps -= category_steps
            if form_type == "127" and "driver" in schema.categories:
                total_steps -= 1
            if form_type in ("127", "137") and "vehicle" in schema.categories:
                total_steps -= 1

        # ---- Step 4b: Category-by-category TEXT LLM extraction ------------
        if self.use_text_llm and not vision_actually_ran:
            if self.use_batch_categories:
                # Batched extraction: group small categories into fewer LLM calls
                self._extract_batched_categories(
                    form_type, schema, categories, special, extracted, field_sources,
                    sections, page_bbox, page_docling, CAT_PAGES,
                    _get_context_for_pages, docling_text, bbox_text, lv_text,
                    table_markdown, step, total_steps, ensemble,
                )
            else:
                # Original: one LLM call per category
                for category in categories:
                    if category in special:
                        continue  # handled separately below

                    step += 1
                    field_names = schema.categories.get(category, [])
                    if not field_names:
                        continue

                    # Use section-scoped context when form sections are detected, else page-focused or full
                    section_ids = get_section_ids_for_category(form_type, category) if sections else []
                    if sections and section_ids:
                        cat_bb = get_section_scoped_bbox_text(page_bbox, sections, section_ids)
                        cat_doc = get_section_scoped_docling(page_docling, sections, section_ids)
                        cat_lv = lv_text
                    elif category in CAT_PAGES:
                        cat_doc, cat_bb, cat_lv = _get_context_for_pages(CAT_PAGES[category])
                    else:
                        cat_doc, cat_bb, cat_lv = docling_text, bbox_text, lv_text

                    # Skip fields already pre-extracted spatially
                    remaining = [f for f in field_names if f not in extracted]
                    if not remaining:
                        print(f"\n  [{step}/{total_steps}] {category}: all {len(field_names)} fields already pre-extracted")
                        continue

                    print(f"\n  [{step}/{total_steps}] Extracting {category} ({len(remaining)}/{len(field_names)} fields) ...")
                    use_section_scoped = bool(sections and section_ids)
                    cat_result = self._extract_category(
                        form_type, category, remaining, cat_doc, cat_bb, cat_lv, use_section_scoped,
                    )
                    # Only add LLM results; never overwrite spatial pre-extraction
                    for k, v in cat_result.items():
                        if field_sources.get(k) == "spatial":
                            continue
                        if k not in extracted:
                            extracted[k] = v
                            field_sources[k] = "text_llm"
                    if ensemble:
                        ensemble.add_results("text_llm", cat_result, confidence=0.65)
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
                driver_section_ids = get_section_ids_for_category(form_type, "driver")
                if sections and driver_section_ids:
                    driver_docling = get_section_scoped_docling(page_docling, sections, driver_section_ids)
                    driver_bbox = get_section_scoped_bbox_text(page_bbox, sections, driver_section_ids)
                else:
                    driver_docling, driver_bbox = docling_text, bbox_text
                driver_result = self._extract_all_drivers(
                    form_type, schema, ocr_result, driver_docling, driver_bbox
                )
                # Only add LLM results; never overwrite spatial pre-extraction
                new_count = 0
                for k, v in driver_result.items():
                    if field_sources.get(k) == "spatial":
                        continue
                    if k not in extracted:
                        extracted[k] = v
                        field_sources[k] = "text_llm"
                        new_count += 1
                if ensemble:
                    ensemble.add_results("text_llm", driver_result, confidence=0.65)
                print(f"    -> {new_count} additional driver fields from LLM")

            # ---- Vehicle extraction (127 / 137) ------------------------------
            if form_type in ("127", "137") and "vehicle" in schema.categories:
                step += 1
                print(f"\n  [{step}/{total_steps}] Extracting vehicles ...")
                vehicle_section_ids = get_section_ids_for_category(form_type, "vehicle")
                if sections and vehicle_section_ids:
                    vehicle_docling = get_section_scoped_docling(page_docling, sections, vehicle_section_ids)
                    vehicle_bbox = get_section_scoped_bbox_text(page_bbox, sections, vehicle_section_ids)
                else:
                    vehicle_docling, vehicle_bbox = docling_text, bbox_text
                vehicle_result = self._extract_all_vehicles(
                    form_type, schema, vehicle_docling, vehicle_bbox
                )
                # Only add LLM results; never overwrite spatial pre-extraction
                new_vehicle = 0
                for k, v in vehicle_result.items():
                    if field_sources.get(k) == "spatial":
                        continue
                    if k not in extracted:
                        extracted[k] = v
                        field_sources[k] = "text_llm"
                        new_vehicle += 1
                if ensemble:
                    ensemble.add_results("text_llm", vehicle_result, confidence=0.65)
                print(f"    -> {new_vehicle} vehicle fields extracted")

        # ---- Gap-fill pass (only when text LLM is enabled) ---------------
        if self.use_text_llm:
            step += 1
        missing = [n for n in all_field_names if n not in extracted]
        if self.use_text_llm and missing:
            # VRAM cleanup before gap-fill so text LLM has a clear GPU
            cleanup_gpu_memory()
            print(f"\n  [{step}/{total_steps}] Gap-fill pass ({len(missing)} missing fields) ...")
            gap_bbox_text = bbox_text
            if sections:
                gap_section_ids: Set[str] = set()
                for f in missing:
                    fi = schema.fields.get(f) if schema else None
                    if fi and getattr(fi, "category", None):
                        gap_section_ids.update(get_section_ids_for_category(form_type, fi.category))
                if gap_section_ids:
                    gap_bbox_text = get_section_scoped_bbox_text(page_bbox, sections, list(gap_section_ids))
            gap_result = self._gap_fill(form_type, missing, gap_bbox_text, lv_text, docling_text=docling_text)
            # Only add fields that weren't already extracted; never overwrite spatial
            new_count = 0
            for k, v in gap_result.items():
                if field_sources.get(k) == "spatial":
                    continue
                if k not in extracted and v:
                    extracted[k] = v
                    field_sources[k] = "gap_fill"
                    new_count += 1
            if ensemble:
                ensemble.add_results("gap_fill", gap_result, confidence=0.50)
            print(f"    -> {new_count} additional fields recovered")

        # ---- VLM checkbox pass (after text LLM, before ensemble) ----
        vlm_loaded = False
        if self.vision_checkboxes_only and ocr_result.clean_image_paths and self.llm.vision_model:
            missing_cb = [
                n for n in all_field_names
                if n not in extracted
                and schema.fields.get(n)
                and getattr(schema.fields[n], "field_type", "") in ("checkbox", "radio")
            ]
            if missing_cb:
                self.llm.unload_text_model()
                vlm_loaded = True
                print(f"\n  [VLM-CB] Vision checkbox pass ({len(missing_cb)} missing checkboxes) ...")
                try:
                    vlm_cb_result = self._vision_pass_checkboxes(
                        form_type=form_type,
                        missing_fields=missing_cb,
                        image_paths=ocr_result.clean_image_paths,
                        schema=schema,
                    )
                    new_cb = 0
                    for k, v in vlm_cb_result.items():
                        norm_v = self._normalise_checkbox_value(v)
                        if k not in extracted:
                            extracted[k] = norm_v
                            field_sources[k] = "vision_checkbox"
                            new_cb += 1
                    if ensemble:
                        ensemble.add_results("vision_checkbox", vlm_cb_result, confidence=0.85)
                    print(f"    -> {new_cb} checkbox fields from VLM")
                except VisionModelNotFoundError as e:
                    print(f"    [VLM-CB] Skipping: {e}")
                except Exception as e:
                    print(f"    [VLM-CB] Error: {e}")

        # ---- VLM driver/narrow-column field rescue ----
        _NARROW_COLUMN_PATTERNS = (
            "UsePercent", "BroadenedNoFaultCode", "DriverOtherCarCode",
            "ProducerIdentifier", "SR22FR44",
        )
        if self.vision_checkboxes_only and ocr_result.clean_image_paths and self.llm.vision_model:
            missing_driver = [
                n for n in all_field_names
                if n not in extracted
                and any(pat in n for pat in _NARROW_COLUMN_PATTERNS)
            ]
            if missing_driver:
                if not vlm_loaded:
                    self.llm.unload_text_model()
                    vlm_loaded = True
                print(f"\n  [VLM-DRV] Vision driver field rescue ({len(missing_driver)} fields) ...")
                try:
                    vlm_drv_result = self._vision_pass_driver_fields(
                        form_type=form_type,
                        missing_fields=missing_driver,
                        image_paths=ocr_result.clean_image_paths,
                        schema=schema,
                    )
                    new_drv = 0
                    for k, v in vlm_drv_result.items():
                        if v is None or (isinstance(v, str) and not v.strip()):
                            continue
                        if k not in extracted:
                            # Normalize checkbox-type fields
                            fi = schema.fields.get(k)
                            if fi and getattr(fi, "field_type", "") in ("checkbox", "radio"):
                                v = self._normalise_checkbox_value(v)
                            extracted[k] = v
                            field_sources[k] = "vision_driver"
                            new_drv += 1
                    if ensemble:
                        ensemble.add_results("vision_driver", vlm_drv_result, confidence=0.82)
                    print(f"    -> {new_drv} driver fields from VLM")
                except VisionModelNotFoundError as e:
                    print(f"    [VLM-DRV] Skipping: {e}")
                except Exception as e:
                    print(f"    [VLM-DRV] Error: {e}")

        if vlm_loaded:
            self.llm.unload_vision_model()
            cleanup_gpu_memory()

        # ---- Ensemble fusion (when enabled) ----
        ensemble_metadata: Optional[Dict[str, Any]] = None
        if ensemble:
            fused_fields, ensemble_metadata = ensemble.fuse()
            # Use ensemble results as the primary extracted dict
            pre_ensemble_count = len(extracted)
            for k, v in fused_fields.items():
                if k not in extracted and v is not None:
                    extracted[k] = v
                    field_sources[k] = ensemble_metadata[k]["source"]
            disagreements = ensemble.get_disagreements()
            print(f"  [ENSEMBLE] Fused {len(fused_fields)} fields from {len(ensemble._results)} field entries")
            if disagreements:
                print(f"    {len(disagreements)} field(s) with source disagreements")
            _save_json(ensemble_metadata, output_dir / "ensemble_metadata.json")

        # ---- Verification (consensus: cross-check LLM/VLM vs BBox OCR) ----
        print("\n  [VERIFY] Cross-checking against BBox OCR text ...")
        verified, field_confidence = self._verify_with_bbox_consensus(extracted, bbox_plain, spatial_fields)
        field_verified = {k: (k in verified) for k in extracted}
        print(f"    {len(verified)}/{len(extracted)} values found in OCR text")

        if self.strict_verify:
            spatial_key_set = set(spatial_fields.keys())
            before = len(extracted)
            extracted = {k: v for k, v in extracted.items() if k in spatial_key_set or k in verified}
            dropped = before - len(extracted)
            if dropped:
                print(f"    [STRICT] Dropped {dropped} values not found in OCR text")

        # ---- Normalise (dedicated normalizer for accuracy + in-extractor rules) ----
        extracted = self._normalise(extracted, form_type)
        from normalizer import normalize_all as normalizer_all
        field_types = {}
        if schema:
            for fname, finfo in schema.fields.items():
                field_types[fname] = getattr(finfo, "field_type", "text") or "text"
        if field_types:
            extracted = normalizer_all(extracted, field_types)

        # Smart checkbox default: only set "Off" for checkboxes where pixel analysis
        # confirms the box is definitely empty (ratio < 0.05). This avoids the old
        # problem of blindly defaulting ALL missing checkboxes to "Off".
        if self.use_positional and schema.get_positioned_fields():
            checkbox_images = getattr(ocr_result, 'clean_image_paths', None) or getattr(ocr_result, 'image_paths', [])
            if checkbox_images:
                from positional_matcher import PositionalMatcher as _PM
                _pm = _PM()
                offsets = _pm.compute_alignment(schema, page_bbox)
                defaulted_off = 0
                for fi in schema.get_positioned_fields():
                    if fi.name in extracted:
                        continue
                    if fi.field_type not in ("checkbox", "radio"):
                        continue
                    page_idx = fi.page
                    if page_idx >= len(checkbox_images):
                        continue
                    dx, dy = offsets[page_idx] if page_idx < len(offsets) else (0.0, 0.0)
                    ratio = _pm._get_checkbox_pixel_ratio(
                        fi.x_min + dx, fi.y_min + dy,
                        fi.x_max + dx, fi.y_max + dy,
                        checkbox_images[page_idx],
                    )
                    if ratio is not None and ratio < 0.05:
                        extracted[fi.name] = "Off"
                        field_sources[fi.name] = "pixel_empty"
                        defaulted_off += 1
                if defaulted_off:
                    print(f"  [PIXEL-OFF] Defaulted {defaulted_off} empty checkboxes to 'Off' (pixel ratio < 0.05)")

        # ---- Validate field names ----------------------------------------
        # Spatial fields are protected from schema validation (they use GT-matching names)
        protected_keys = set(spatial_fields.keys())
        if self.use_acroform:
            protected_keys |= set(acroform_fields.keys())
        pre_validation_count = len(extracted)
        validated = self.registry.validate_field_names(form_type, extracted)
        # Re-add protected fields that were filtered out
        for k, v in extracted.items():
            if k in protected_keys and k not in validated:
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
                "field_sources": field_sources,
                "field_verified": field_verified,
                "field_confidence": field_confidence,
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
        section_scoped: bool = False,
    ) -> Dict[str, Any]:
        """Extract one category of fields using a two-pass strategy.

        Large categories are batched into sub-batches of BATCH_SIZE fields
        to keep LLM context focused and JSON template manageable.
        """
        BATCH_SIZE = 50  # 50 = fewer round-trips; safe on 24GB. Use 30 on low memory.
        tooltips = self.registry.get_tooltips(form_type, field_names)
        result: Dict[str, Any] = {}

        # --- Pass 1: Extract in batches ---
        for i in range(0, len(field_names), BATCH_SIZE):
            batch = field_names[i:i + BATCH_SIZE]
            batch_tooltips = {k: v for k, v in tooltips.items() if k in batch}

            few_shot = ""
            if self.rag_store is not None:
                few_shot = self.rag_store.retrieve(form_type, category, batch, k=3)
            prompt = build_extraction_prompt(
                form_type=form_type,
                category=category,
                field_names=batch,
                tooltips=batch_tooltips,
                docling_text=docling_text,
                bbox_text=bbox_text,
                label_value_text=lv_text,
                section_scoped=section_scoped,
                few_shot_examples=few_shot,
            )
            response = self.llm.generate(prompt)
            batch_result = self.llm.parse_json(response)

            # Only keep fields that match the requested batch
            for k, v in batch_result.items():
                if k in batch and v is not None:
                    result[k] = v

        # --- Pass 2: Gap-fill for missing fields (skip when Pass 1 got almost all) ---
        extracted_keys = set(result.keys())
        missing = [n for n in field_names if n not in extracted_keys]
        GAP_FILL_THRESHOLD = 5  # skip gap-fill when only a few fields missed (saves one LLM call per category)

        if missing and len(missing) >= GAP_FILL_THRESHOLD and len(missing) < len(field_names):
            for i in range(0, len(missing), BATCH_SIZE):
                gap_batch = missing[i:i + BATCH_SIZE]
                gap_tooltips = {k: v for k, v in tooltips.items() if k in gap_batch}
                gap_few_shot = ""
                if self.rag_store is not None:
                    gap_few_shot = self.rag_store.retrieve_for_fields(form_type, gap_batch, k=2)
                gap_prompt = build_gap_fill_prompt(
                    form_type=form_type,
                    missing_fields=gap_batch,
                    tooltips=gap_tooltips,
                    bbox_text=bbox_text,
                    label_value_text=lv_text,
                    few_shot_examples=gap_few_shot,
                    docling_text=docling_text,
                )
                gap_response = self.llm.generate(gap_prompt)
                gap_result = self.llm.parse_json(gap_response)
                for k, v in gap_result.items():
                    if k not in result and k in gap_batch and v is not None:
                        result[k] = v

        return result

    def _vision_pass_unified(
        self,
        form_type: str,
        missing_fields: List[str],
        image_paths: List[Path],
        docling_text: str,
        bbox_text: str,
        lv_text: str,
        schema,
    ) -> Dict[str, Any]:
        """
        Single VLM pass with full context: form image(s) + Docling doc + spatial/bbox OCR + label-value pairs.
        Fills remaining fields using schema-derived field list. Batches by VISION_BATCH to stay within context.
        """
        VISION_BATCH = self.vision_batch_size if self.vision_batch_size is not None else (20 if self.vision_fast else 16)
        MAX_PAGES = 1 if self.vision_fast else 2
        result: Dict[str, Any] = {}
        paths = [Path(p) for p in image_paths[:MAX_PAGES] if Path(p).exists()]
        if not paths:
            return result
        tooltips_all = self.registry.get_tooltips(form_type, missing_fields)

        def _match_key(vlm_key: str, batch_keys: List[str]) -> Optional[str]:
            if vlm_key in batch_keys:
                return vlm_key
            vlm_norm = vlm_key.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
            vlm_norm = re.sub(r"_+", "_", vlm_norm).strip("_")
            for b in batch_keys:
                b_norm = b.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
                b_norm = re.sub(r"_+", "_", b_norm).strip("_")
                if b_norm == vlm_norm:
                    return b
            for b in batch_keys:
                b_norm = b.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
                b_norm = re.sub(r"_+", "_", b_norm).strip("_")
                if len(b_norm) < 5:
                    continue
                if vlm_norm in b_norm or b_norm in vlm_norm:
                    if min(len(vlm_norm), len(b_norm)) / max(len(vlm_norm), len(b_norm)) >= 0.6:
                        return b
            return None

        checkbox_field_set: Set[str] = set()
        if schema:
            for fname, finfo in schema.fields.items():
                if finfo.field_type in ("checkbox", "radio"):
                    checkbox_field_set.add(fname)

        for i in range(0, len(missing_fields), VISION_BATCH):
            batch = missing_fields[i : i + VISION_BATCH]
            batch_tooltips = {k: v for k, v in tooltips_all.items() if k in batch}
            prompt = build_vision_unified_prompt(
                form_type=form_type,
                missing_fields=batch,
                tooltips=batch_tooltips,
                docling_text=docling_text,
                bbox_text=bbox_text,
                label_value_text=lv_text,
            )
            try:
                if len(paths) == 1:
                    response = self.llm.generate_with_image(prompt, paths[0], max_tokens=self.vision_max_tokens)
                else:
                    response = self.llm.generate_with_images(prompt, paths, max_tokens=self.vision_max_tokens)
                batch_result = self.llm.parse_json(response)
                batch_num = i // VISION_BATCH + 1
                if batch_num == 1:
                    preview = (response or "").strip()[:400] or "(empty)"
                    print(f"    [VLM] Batch 1 response preview: {preview!r}")
                for k, v in batch_result.items():
                    if v is None or (isinstance(v, str) and not v.strip()):
                        continue
                    canonical = _match_key(k, batch)
                    if canonical:
                        if canonical in checkbox_field_set:
                            result[canonical] = self._normalise_checkbox_value(v)
                        else:
                            result[canonical] = v
            except Exception as e:
                print(f"    [VLM] Unified batch error: {e}")
        return result

    def _vision_pass(
        self,
        form_type: str,
        missing_fields: List[str],
        image_paths: List[Path],
        schema,
        ocr_result: Any = None,
        output_dir: Optional[Path] = None,
        sections: Optional[List[FormSection]] = None,
    ) -> Dict[str, Any]:
        """
        Use a vision LLM (Ollama VLM) to extract missing fields from form page images.
        When sections are provided, crops page images to section bboxes and sends only
        those section crops to the VLM (form-specific, section-scoped). Otherwise uses
        full pages or describe-then-extract regions.
        """
        VISION_BATCH = self.vision_batch_size if self.vision_batch_size is not None else (20 if self.vision_fast else 16)
        MAX_PAGES = 1 if self.vision_fast else 2
        result: Dict[str, Any] = {}
        paths = [Path(p) for p in image_paths[:MAX_PAGES] if Path(p).exists()]
        if not paths:
            return result
        tooltips_all = self.registry.get_tooltips(form_type, missing_fields)
        section_crop_paths: List[Path] = []

        # Form-specific section crops: when sections and output_dir exist, crop to sections
        # that are relevant to the missing fields' categories (skip when vision_fast to use full pages = faster)
        section_crop_paths: List[Path] = []
        if sections and output_dir is not None and missing_fields and not self.vision_fast:
            categories_needed: Set[str] = set()
            for f in missing_fields:
                fi = schema.fields.get(f) if schema else None
                if fi and getattr(fi, "category", None):
                    categories_needed.add(fi.category)
            section_ids_needed: List[str] = []
            for cat in categories_needed:
                section_ids_needed.extend(get_section_ids_for_category(form_type, cat))
            section_ids_needed = list(dict.fromkeys(section_ids_needed))  # preserve order, dedup
            if section_ids_needed:
                crops_dir = Path(output_dir) / "vision_section_crops"
                section_crop_paths = crop_sections_to_images(
                    paths,
                    sections,
                    section_ids_needed,
                    crops_dir,
                    page_stem=paths[0].stem.rsplit("_", 1)[0] if paths else "page",
                )
                if section_crop_paths:
                    print(f"    [VLM] Using {len(section_crop_paths)} section crop(s) for vision pass")
                    paths = section_crop_paths

        use_section_crops = bool(section_crop_paths)

        def _match_key(vlm_key: str, batch_keys: List[str]) -> Optional[str]:
            if vlm_key in batch_keys:
                return vlm_key
            # Normalise: spaces, dashes, slashes -> underscores (VLM may return "Location/Building_Occupancy_A")
            vlm_norm = vlm_key.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
            # Collapse multiple underscores for comparison
            vlm_norm = re.sub(r"_+", "_", vlm_norm).strip("_")
            for b in batch_keys:
                b_norm = b.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
                b_norm = re.sub(r"_+", "_", b_norm).strip("_")
                if b_norm == vlm_norm:
                    return b
            # Fuzzy: one key contains the other (handles AuthorizedRep vs AuthorizedRepresentative)
            for b in batch_keys:
                b_norm = b.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
                b_norm = re.sub(r"_+", "_", b_norm).strip("_")
                if len(b_norm) < 5:
                    continue
                if vlm_norm in b_norm or b_norm in vlm_norm:
                    ratio = min(len(vlm_norm), len(b_norm)) / max(len(vlm_norm), len(b_norm))
                    if ratio >= 0.6:
                        return b
            return None

        # Describer step removed: use full-page or section crops only (no describe-then-extract).
        use_descriptions = False
        tile_paths: List[Path] = []
        region_descriptions: List[str] = []
        MAX_REGIONS = 16  # Cap total crops (Docling + EasyOCR) to avoid overload
        if use_descriptions:
            try:
                # 1) Docling-based regions (blocks/paragraphs from Docling layout)
                if ocr_result is not None and getattr(ocr_result, "docling_regions_per_page", None) and layout_regions_from_docling is not None:
                    paths_for_crop = getattr(ocr_result, "clean_image_paths", None) or getattr(ocr_result, "image_paths", [])
                    docling_crops = layout_regions_from_docling(
                        ocr_result.docling_regions_per_page,
                        paths_for_crop,
                        max_pages=MAX_PAGES,
                    )
                    if docling_crops:
                        tile_paths.extend(docling_crops)
                        print(f"    [VLM] Using {len(docling_crops)} Docling region(s)")
                # 2) EasyOCR-based regions (spatial index, then raw bbox)
                if ocr_result is not None and VISION_LAYOUT_AVAILABLE and len(tile_paths) < MAX_REGIONS:
                    indices = getattr(ocr_result, "spatial_indices", None)
                    if indices and layout_regions_from_ocr_result is not None:
                        easyocr_crops = layout_regions_from_ocr_result(ocr_result, max_pages=MAX_PAGES)
                        if easyocr_crops:
                            tile_paths.extend(easyocr_crops)
                            print(f"    [VLM] Using {len(easyocr_crops)} EasyOCR layout region(s)")
                    if len(tile_paths) < MAX_REGIONS and getattr(ocr_result, "bbox_pages", None) and regions_from_bbox_pages is not None:
                        easyocr_crops = regions_from_bbox_pages(
                            ocr_result.bbox_pages,
                            getattr(ocr_result, "clean_image_paths", ocr_result.image_paths),
                            max_pages=MAX_PAGES,
                        )
                        if easyocr_crops:
                            tile_paths.extend(easyocr_crops)
                            print(f"    [VLM] Using {len(easyocr_crops)} EasyOCR bbox region(s)")
                if len(tile_paths) > MAX_REGIONS:
                    tile_paths = tile_paths[:MAX_REGIONS]
                # 3) Fallback: fixed 2x2 grid
                if not tile_paths and crop_pages_to_tiles is not None:
                    tile_paths = crop_pages_to_tiles(paths, grid=(2, 2), max_pages=MAX_PAGES)
                    if tile_paths:
                        print(f"    [VLM] Using {len(tile_paths)} grid crop(s) (2x2 per page)")
                if tile_paths:
                    describer = getattr(self.llm, "vision_describer_model", None) or self.llm.vision_model
                    print(f"    [VLM] Describing {len(tile_paths)} region(s) with small VLM ...")
                    for idx, tile in enumerate(tile_paths):
                        desc = self.llm.describe_image(tile, model=describer)
                        region_descriptions.append(f"Region {idx + 1}: {(desc or '').strip() or '(no description)'}")
                    if getattr(self.llm, "unload_describer_model", None):
                        self.llm.unload_describer_model()
                    print(f"    [VLM] Using {len(tile_paths)} crops + descriptions for extraction")
            except Exception as e:
                print(f"    [VLM] Describe-step failed ({e}), falling back to full-page vision")
                use_descriptions = False

        image_paths_to_use = tile_paths if use_descriptions and tile_paths else paths
        for i in range(0, len(missing_fields), VISION_BATCH):
            batch = missing_fields[i : i + VISION_BATCH]
            batch_tooltips = {k: v for k, v in tooltips_all.items() if k in batch}
            if use_descriptions and region_descriptions:
                prompt = build_vision_extraction_prompt_with_region_descriptions(
                    form_type=form_type,
                    missing_fields=batch,
                    tooltips=batch_tooltips,
                    region_descriptions=region_descriptions,
                )
            else:
                prompt = build_vision_extraction_prompt(
                    form_type=form_type,
                    missing_fields=batch,
                    tooltips=batch_tooltips,
                )
            try:
                if len(image_paths_to_use) == 1:
                    response = self.llm.generate_with_image(prompt, image_paths_to_use[0], max_tokens=self.vision_max_tokens)
                else:
                    response = self.llm.generate_with_images(prompt, image_paths_to_use, max_tokens=self.vision_max_tokens)
                batch_result = self.llm.parse_json(response)
                # Debug: log raw VLM response for first batch; log when parse returns 0 keys
                batch_num = i // VISION_BATCH + 1
                if batch_num == 1:
                    preview = (response or "").strip()[:500] or "(empty)"
                    print(f"    [VLM] Batch 1 raw response preview ({len(response or '')} chars): {preview!r}")
                if not batch_result and response and len(response.strip()) > 50:
                    preview = (response or "").strip()[:400]
                    print(f"    [VLM] Batch {batch_num}: response {len(response)} chars but parse_json returned 0 keys. Preview: {preview!r}")
                matched_this_batch = 0
                for k, v in batch_result.items():
                    if v is None or (isinstance(v, str) and not v.strip()):
                        continue
                    canonical = _match_key(k, batch)
                    if canonical:
                        result[canonical] = v
                        matched_this_batch += 1
                if batch_result and matched_this_batch == 0:
                    print(f"    [VLM] Batch {i // VISION_BATCH + 1}: VLM returned {list(batch_result.keys())[:5]}{'...' if len(batch_result) > 5 else ''} but none matched expected keys (exact match required)")
            except Exception as e:
                print(f"    [VLM] Batch error: {e}")
        return result

    def _vision_pass_checkboxes(
        self,
        form_type: str,
        missing_fields: List[str],
        image_paths: List[Path],
        schema,
    ) -> Dict[str, Any]:
        """
        Vision pass for checkbox fields only: VLM looks at form image and returns
        1 (checked) or Off (not checked) for each. Uses a focused checkbox-only prompt.
        Smaller batches reduce empty content / truncation with large VLMs.
        """
        # Checkbox payload is small; batch 18–20 is safe. Override via vision_batch_size for checkbox pass not used.
        cb_batch = 20 if self.vision_fast else 18
        MAX_PAGES = 1 if self.vision_fast else 2
        result: Dict[str, Any] = {}
        paths = [Path(p) for p in image_paths[:MAX_PAGES] if Path(p).exists()]
        if not paths:
            return result
        tooltips_all = self.registry.get_tooltips(form_type, missing_fields)

        def _match_key(vlm_key: str, batch_keys: List[str]) -> Optional[str]:
            if vlm_key in batch_keys:
                return vlm_key
            vlm_norm = vlm_key.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
            vlm_norm = re.sub(r"_+", "_", vlm_norm).strip("_")
            for b in batch_keys:
                b_norm = b.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
                b_norm = re.sub(r"_+", "_", b_norm).strip("_")
                if b_norm == vlm_norm:
                    return b
            for b in batch_keys:
                b_norm = b.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
                b_norm = re.sub(r"_+", "_", b_norm).strip("_")
                if len(b_norm) < 5:
                    continue
                if vlm_norm in b_norm or b_norm in vlm_norm:
                    if min(len(vlm_norm), len(b_norm)) / max(len(vlm_norm), len(b_norm)) >= 0.6:
                        return b
            return None

        for i in range(0, len(missing_fields), cb_batch):
            batch = missing_fields[i : i + cb_batch]
            batch_tooltips = {k: v for k, v in tooltips_all.items() if k in batch}
            prompt = build_vision_checkbox_prompt(
                form_type=form_type,
                missing_fields=batch,
                tooltips=batch_tooltips,
            )
            try:
                if len(paths) == 1:
                    response = self.llm.generate_with_image(prompt, paths[0], max_tokens=self.vision_max_tokens)
                else:
                    response = self.llm.generate_with_images(prompt, paths, max_tokens=self.vision_max_tokens)
                batch_result = self.llm.parse_json(response)
                for k, v in batch_result.items():
                    if v is None or (isinstance(v, str) and not v.strip()):
                        continue
                    canonical = _match_key(k, batch)
                    if canonical:
                        result[canonical] = v
            except Exception as e:
                print(f"    [VLM] Checkbox batch error: {e}")
        return result

    def _vision_pass_driver_fields(
        self,
        form_type: str,
        missing_fields: List[str],
        image_paths: List[Path],
        schema,
    ) -> Dict[str, Any]:
        """
        Vision pass for missing narrow-column driver/vehicle fields.
        These fields (UsePercent, BroadenedNoFaultCode, etc.) live in tiny table cells
        that OCR can't reliably read. The VLM reads directly from the form image.
        """
        drv_batch = 15
        MAX_PAGES = 2
        result: Dict[str, Any] = {}
        paths = [Path(p) for p in image_paths[:MAX_PAGES] if Path(p).exists()]
        if not paths:
            return result
        tooltips_all = self.registry.get_tooltips(form_type, missing_fields)

        def _match_key(vlm_key: str, batch_keys: List[str]) -> Optional[str]:
            if vlm_key in batch_keys:
                return vlm_key
            vlm_norm = vlm_key.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
            vlm_norm = re.sub(r"_+", "_", vlm_norm).strip("_")
            for b in batch_keys:
                b_norm = b.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
                b_norm = re.sub(r"_+", "_", b_norm).strip("_")
                if b_norm == vlm_norm:
                    return b
            for b in batch_keys:
                b_norm = b.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
                b_norm = re.sub(r"_+", "_", b_norm).strip("_")
                if len(b_norm) < 5:
                    continue
                if vlm_norm in b_norm or b_norm in vlm_norm:
                    if min(len(vlm_norm), len(b_norm)) / max(len(vlm_norm), len(b_norm)) >= 0.6:
                        return b
            return None

        for i in range(0, len(missing_fields), drv_batch):
            batch = missing_fields[i : i + drv_batch]
            batch_tooltips = {k: v for k, v in tooltips_all.items() if k in batch}
            prompt = build_vision_driver_fields_prompt(
                form_type=form_type,
                missing_fields=batch,
                tooltips=batch_tooltips,
            )
            try:
                if len(paths) == 1:
                    response = self.llm.generate_with_image(prompt, paths[0], max_tokens=self.vision_max_tokens)
                else:
                    response = self.llm.generate_with_images(prompt, paths, max_tokens=self.vision_max_tokens)
                batch_result = self.llm.parse_json(response)
                for k, v in batch_result.items():
                    if v is None or (isinstance(v, str) and not v.strip()):
                        continue
                    canonical = _match_key(k, batch)
                    if canonical:
                        result[canonical] = v
            except Exception as e:
                print(f"    [VLM] Driver field batch error: {e}")
        return result

    @staticmethod
    def _normalise_checkbox_value(value: Any) -> str:
        """Normalise a single checkbox value from LLM/VLM to '1' or 'Off'."""
        if value is None:
            return "Off"
        s = str(value).strip().lower()
        if s in ("true", "yes", "1", "on", "x", "checked", "y", "s"):
            return "1"
        if re.match(r"^\d{3,}$", s) or re.match(r"\d{1,2}/\d{1,2}/\d{4}", s):
            return "Off"
        return "Off"

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

            driver_few_shot = ""
            if self.rag_store is not None:
                driver_few_shot = self.rag_store.retrieve(form_type, "driver", field_names, k=3)
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
                few_shot_examples=driver_few_shot,
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

            vehicle_few_shot = ""
            if self.rag_store is not None:
                vehicle_few_shot = self.rag_store.retrieve(form_type, "vehicle", field_names, k=3)
            print(f"    Vehicle {suffix} - {len(field_names)} fields ...")
            prompt = build_vehicle_prompt(
                form_type=form_type,
                suffix=suffix,
                field_names=field_names,
                tooltips=tooltips,
                docling_text=docling_text,
                bbox_text=bbox_text,
                few_shot_examples=vehicle_few_shot,
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
        docling_text: str = "",
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
            gap_few_shot = ""
            if self.rag_store is not None:
                gap_few_shot = self.rag_store.retrieve_for_fields(form_type, batch, k=2)
            prompt = build_gap_fill_prompt(
                form_type=form_type,
                missing_fields=batch,
                tooltips=batch_tooltips,
                bbox_text=bbox_text,
                label_value_text=lv_text,
                few_shot_examples=gap_few_shot,
                docling_text=docling_text,
            )
            # Dynamic timeout: base + extra per 100 fields
            field_timeout = self.llm.timeout + (len(batch) // 100) * 60
            response = self.llm.generate(prompt, timeout_override=field_timeout)
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
        verified, _ = self._verify_with_bbox_consensus(extracted, bbox_plain, {})
        return verified

    def _verify_with_bbox_consensus(
        self,
        extracted: Dict[str, Any],
        bbox_plain: str,
        spatial_fields: Dict[str, Any],
    ) -> tuple:
        """
        Consensus verification: cross-check extracted values against BBox OCR.
        Returns (verified_dict, field_confidence_dict).
        High-impact: reduces hallucinations by scoring agreement with OCR.
        """
        bbox_lower = bbox_plain.lower()
        verified: Dict[str, Any] = {}
        field_confidence: Dict[str, float] = {}
        spatial_key_set = set(spatial_fields.keys())

        for key, value in extracted.items():
            if value is None or str(value).strip() == "":
                field_confidence[key] = 0.0
                continue
            str_val = str(value).lower().strip()
            if key in spatial_key_set:
                verified[key] = value
                field_confidence[key] = 1.0
                continue
            if str_val in bbox_lower:
                verified[key] = value
                field_confidence[key] = 1.0
            elif len(str_val) > 3:
                words = [w for w in str_val.split() if len(w) > 2]
                matches = sum(1 for w in words if w in bbox_lower)
                if matches:
                    verified[key] = value
                    field_confidence[key] = 0.7 if matches < len(words) else 0.9
                else:
                    field_confidence[key] = 0.5
            else:
                verified[key] = value
                field_confidence[key] = 0.8

        return verified, field_confidence

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
            key_lower = key.lower()

            # Checkbox normalisation - FORCE to "1" or "Off" only
            is_checkbox = (
                key in checkbox_fields
                or "indicator" in key_lower
                or key_lower.startswith("chk")
            )
            if is_checkbox:
                lower = str_val.lower()
                if re.match(r"^\d{3,}$", str_val) or re.match(r"\d{1,2}/\d{1,2}/\d{4}", str_val):
                    normalised[key] = "Off"
                elif lower in ("true", "yes", "1", "on", "x", "checked", "y", "s"):
                    normalised[key] = "1"
                else:
                    normalised[key] = "Off"
                continue

            # Boolean normalisation for non-checkbox fields
            if isinstance(value, bool):
                normalised[key] = "true" if value else "false"
                continue

            # Normalize Y/N/True/False for "Code" fields (e.g. BroadenedNoFaultCode, DriverOtherCarCode)
            if "code" in key_lower and str_val.lower() in ("y", "n", "yes", "no", "true", "false"):
                normalised[key] = "True" if str_val.lower() in ("y", "yes", "true") else "False"
                continue

            # Time field (HHMM): normalise to 4-digit string only; never put a date in a time field
            if ("effectivetime" in key_lower or "expirationtime" in key_lower) and "indicator" not in key_lower:
                if re.match(r"\d{1,2}/\d{1,2}/\d{4}", str_val) or ("/" in str_val or "-" in str_val) and re.search(r"\d{4}", str_val):
                    continue
                digits = re.sub(r"[^\d]", "", str_val)
                if digits and len(digits) <= 4 and digits.isdigit():
                    normalised[key] = digits.zfill(4)
                    continue

            # Date field: try to normalise to MM/DD/YYYY
            if "date" in key_lower and "update" not in key_lower:
                norm_date = self._normalise_date_str(str_val)
                if norm_date:
                    normalised[key] = norm_date
                    continue

            # Amount-like: strip $ and commas for consistent storage
            if any(x in key_lower for x in ("amount", "limit", "premium", "deductible")) and "count" not in key_lower:
                cleaned = re.sub(r"[^\d.]", "", str_val)
                if cleaned:
                    normalised[key] = cleaned
                    continue

            # Address-like: normalise semicolon to comma (e.g. "Indianapolis; IN" -> "Indianapolis, IN")
            if any(x in key_lower for x in (
                "address", "officeidentifier", "lineone", "cityname",
                "stateorprovincecode", "postalcode",
            )):
                str_val = str_val.replace(";", ",").strip()
                if "postalcode" in key_lower and str_val:
                    digits_only = re.sub(r"[^\d]", "", str_val)
                    if len(digits_only) >= 5 and digits_only.isdigit():
                        str_val = digits_only[:5] if len(digits_only) > 5 else digits_only
                    elif not str_val.isdigit() and len(str_val) > 5:
                        pass
                normalised[key] = str_val
                continue

            normalised[key] = str_val

        # Post-pass: split State+ZIP merged values (e.g. "DC 20016" in StateOrProvinceCode)
        state_zip_splits: Dict[str, str] = {}
        for key, value in list(normalised.items()):
            if "stateorprovincecode" in key.lower():
                m = re.match(r"^([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$", str(value).strip())
                if m:
                    state_part, zip_part = m.group(1), m.group(2)
                    normalised[key] = state_part
                    # Find the corresponding PostalCode field (same suffix)
                    zip_key = key.replace("StateOrProvinceCode", "PostalCode")
                    if zip_key not in normalised:
                        state_zip_splits[zip_key] = zip_part
        if state_zip_splits:
            normalised.update(state_zip_splits)

        return normalised

    @staticmethod
    def _normalise_date_str(s: str) -> Optional[str]:
        """Try to parse date and return MM/DD/YYYY; else None."""
        from datetime import datetime
        s = s.strip()
        for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y", "%m/%d/%y"):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.strftime("%m/%d/%Y")
            except ValueError:
                continue
        m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", s)
        if m:
            try:
                mo, day, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if 1 <= mo <= 12 and 1 <= day <= 31:
                    return f"{mo:02d}/{day:02d}/{yr}"
            except (ValueError, IndexError):
                pass
        return None

    # ==================================================================
    # Batched category extraction (Feature 3)
    # ==================================================================

    def _extract_batched_categories(
        self,
        form_type: str,
        schema: Any,
        categories: List[str],
        special: set,
        extracted: Dict[str, Any],
        field_sources: Dict[str, str],
        sections: list,
        page_bbox: list,
        page_docling: list,
        cat_pages: dict,
        get_context_fn: Any,
        docling_text: str,
        bbox_text: str,
        lv_text: str,
        table_markdown: str,
        step: int,
        total_steps: int,
        ensemble: Optional[Any],
    ) -> None:
        """Extract categories in batches to reduce LLM calls."""
        # Build a set of categories present in this form
        available_cats = {c for c in categories if c not in special}

        for batch in CATEGORY_BATCHES:
            batch_cats = [c for c in batch if c in available_cats]
            if not batch_cats:
                continue

            # Collect all field names from all categories in this batch
            all_batch_fields = []
            for cat in batch_cats:
                fields = schema.categories.get(cat, [])
                all_batch_fields.extend(fields)

            if not all_batch_fields:
                continue

            # Skip already-extracted fields
            remaining = [f for f in all_batch_fields if f not in extracted]
            if not remaining:
                step += 1
                cats_label = "+".join(batch_cats)
                print(f"\n  [{step}/{total_steps}] {cats_label}: all fields already pre-extracted")
                continue

            step += 1
            cats_label = "+".join(batch_cats)

            # Determine context: use most specific available
            # For batches with page-specific categories, use their pages
            batch_pages = set()
            for cat in batch_cats:
                if cat in cat_pages:
                    batch_pages.update(cat_pages[cat])

            # Try section-scoped context first
            batch_section_ids = []
            for cat in batch_cats:
                if sections:
                    batch_section_ids.extend(get_section_ids_for_category(form_type, cat))

            if sections and batch_section_ids:
                cat_bb = get_section_scoped_bbox_text(page_bbox, sections, batch_section_ids)
                cat_doc = get_section_scoped_docling(page_docling, sections, batch_section_ids)
                cat_lv = lv_text
            elif batch_pages:
                cat_doc, cat_bb, cat_lv = get_context_fn(sorted(batch_pages))
            else:
                cat_doc, cat_bb, cat_lv = docling_text, bbox_text, lv_text

            # Chunk large batches to prevent timeouts on slower models
            MAX_FIELDS_PER_BATCH = 150

            if len(remaining) <= MAX_FIELDS_PER_BATCH:
                chunks = [remaining]
            else:
                chunks = [remaining[i:i + MAX_FIELDS_PER_BATCH]
                          for i in range(0, len(remaining), MAX_FIELDS_PER_BATCH)]

            print(f"\n  [{step}/{total_steps}] Extracting {cats_label} ({len(remaining)}/{len(all_batch_fields)} fields, batched{f', {len(chunks)} chunks' if len(chunks) > 1 else ''}) ...")

            total_new = 0
            for chunk_idx, chunk_fields in enumerate(chunks):
                if len(chunks) > 1:
                    print(f"      chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk_fields)} fields) ...")

                tooltips = self.registry.get_tooltips(form_type, chunk_fields)
                few_shot = ""
                if self.rag_store is not None:
                    few_shot = self.rag_store.retrieve(form_type, batch_cats[0], chunk_fields, k=3)

                prompt = build_batched_extraction_prompt(
                    form_type=form_type,
                    categories=batch_cats,
                    field_names=chunk_fields,
                    tooltips=tooltips,
                    docling_text=cat_doc,
                    bbox_text=cat_bb,
                    label_value_text=cat_lv,
                    section_scoped=bool(sections and batch_section_ids),
                    few_shot_examples=few_shot,
                    table_markdown=table_markdown,
                )
                # Scale timeout: base + extra per 100 fields
                field_timeout = self.llm.timeout + (len(chunk_fields) // 100) * 60
                response = self.llm.generate(prompt, timeout_override=field_timeout)
                batch_result = self.llm.parse_json(response)

                # Only add LLM results; never overwrite spatial pre-extraction
                new_count = 0
                for k, v in batch_result.items():
                    if field_sources.get(k) == "spatial":
                        continue
                    if k not in extracted and k in chunk_fields and v is not None:
                        extracted[k] = v
                        field_sources[k] = "text_llm"
                        new_count += 1
                if ensemble:
                    ensemble.add_results("text_llm", batch_result, confidence=0.65)
                total_new += new_count
                if len(chunks) > 1:
                    print(f"        -> {new_count} fields extracted")

            print(f"    -> {total_new} fields extracted (total)")

        # Handle special categories that were in CATEGORY_BATCHES but also special
        # (coverage is a special-ish category that can be batched on its own)
        for cat in available_cats:
            if cat in SPECIAL_CATEGORIES:
                continue
            # Check if this category was already handled in a batch
            in_batch = any(cat in b for b in CATEGORY_BATCHES)
            if in_batch:
                continue
            # Unbatched category: extract individually
            step += 1
            field_names = schema.categories.get(cat, [])
            remaining = [f for f in field_names if f not in extracted]
            if not remaining:
                continue
            print(f"\n  [{step}/{total_steps}] Extracting {cat} ({len(remaining)} fields) ...")
            cat_result = self._extract_category(
                form_type, cat, remaining, docling_text, bbox_text, lv_text
            )
            for k, v in cat_result.items():
                if field_sources.get(k) == "spatial":
                    continue
                if k not in extracted:
                    extracted[k] = v
                    field_sources[k] = "text_llm"
            if ensemble:
                ensemble.add_results("text_llm", cat_result, confidence=0.65)
            print(f"    -> {len(cat_result)} fields extracted")

    # ==================================================================
    # Template extraction (Feature 4)
    # ==================================================================

    def _run_template_extraction(
        self,
        form_type: str,
        page_bbox: List[List[Dict]],
        output_dir: Path,
    ) -> Dict[str, Any]:
        """Run template-based extraction."""
        if self._template_registry is None:
            try:
                self._template_registry = TemplateRegistry()
            except Exception as e:
                print(f"  [TEMPLATE] Failed to load templates: {e}")
                return {}

        template = self._template_registry.get_template(form_type)
        if template is None:
            print(f"  [TEMPLATE] No template for form {form_type}")
            return {}

        template_fields = self._template_registry.extract_from_template(
            template, page_bbox
        )
        if template_fields:
            from utils import save_json as _save_json
            _save_json(template_fields, output_dir / "template_extract.json")
            print(f"  [TEMPLATE] {len(template_fields)} fields from template anchoring")
        return template_fields

    # ==================================================================
    # Table Transformer (Feature 5)
    # ==================================================================

    def _run_table_transformer(
        self,
        ocr_result: OCRResult,
        page_bbox: List[List[Dict]],
        output_dir: Path,
    ) -> None:
        """Run Table Transformer on page images."""
        if self._table_transformer is None:
            try:
                device = "cpu"
                if hasattr(self.ocr, "easyocr_gpu") and self.ocr.easyocr_gpu:
                    device = "cuda"
                self._table_transformer = TableTransformerEngine(device=device)
            except Exception as e:
                print(f"  [TABLE-TRANSFORMER] Failed to initialize: {e}")
                return

        detected_tables: List[List[Any]] = []
        for page_idx, img_path in enumerate(ocr_result.image_paths):
            page_data = page_bbox[page_idx] if page_idx < len(page_bbox) else []
            try:
                tables = self._table_transformer.extract_tables(
                    img_path, page_data, page=page_idx
                )
                detected_tables.append(tables)
                if tables:
                    print(f"  [TABLE-TRANSFORMER] Page {page_idx + 1}: {len(tables)} table(s) detected")
            except Exception as e:
                print(f"  [TABLE-TRANSFORMER] Page {page_idx + 1} error: {e}")
                detected_tables.append([])

        ocr_result.detected_tables_per_page = detected_tables

        # Save table markdown for debugging
        md_parts = []
        for page_idx, tables in enumerate(detected_tables):
            for t_idx, table in enumerate(tables):
                md = table.to_markdown()
                if md:
                    md_parts.append(f"--- Page {page_idx + 1}, Table {t_idx + 1} ---\n{md}")
        if md_parts:
            table_md = "\n\n".join(md_parts)
            with open(output_dir / "detected_tables.md", "w") as f:
                f.write(table_md)

        # Cleanup Table Transformer to free memory before LLM
        self._table_transformer.cleanup()
        self._table_transformer = None
        cleanup_gpu_memory()
