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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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
    build_vlm_extract_prompt,
    build_vlm_extract_driver_prompt,
    build_vlm_extract_vehicle_prompt,
    build_vlm_extract_163_row_prompt,
    build_multimodal_extract_prompt,
    build_checkbox_crop_prompt,
    build_checkbox_grid_prompt,
    build_vlm_ocr_stage2_prompt,
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

# Optional: Image alignment
try:
    from image_aligner import align_to_template, get_template_image
    IMAGE_ALIGNER_AVAILABLE = True
except ImportError:
    IMAGE_ALIGNER_AVAILABLE = False

# Optional: Field validator
try:
    from field_validator import validate_and_fix
    FIELD_VALIDATOR_AVAILABLE = True
except ImportError:
    FIELD_VALIDATOR_AVAILABLE = False
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
        use_vlm_extract: bool = False,
        use_preprocess: bool = False,
        use_align_to_template: bool = False,
        use_smart_ensemble: bool = False,
        use_field_validation: bool = False,
        use_vlm_crop_extract: bool = False,
        use_dual_llm_validate: bool = False,
        parallel_vlm: bool = True,
        vlm_max_workers: int = 3,
        use_multimodal: bool = False,
        confidence_routing: bool = True,
        confidence_threshold: float = 0.90,
        use_checkbox_crops: bool = False,
        use_glm_ocr: bool = False,
        use_nanonets_ocr: bool = False,
        knowledge_store: Optional[Any] = None,
        generate_review: bool = False,
        review_threshold: float = 0.85,
    ):
        self.ocr = ocr_engine
        self.llm = llm_engine
        self.registry = schema_registry
        self.use_vision = use_vision and bool(getattr(llm_engine, "vision_model", None))
        self.use_vlm_extract = use_vlm_extract and bool(getattr(llm_engine, "vlm_extract_model", None))
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
        # Optional knowledge base: semantic context from insurance knowledge collections
        self.knowledge_store = knowledge_store
        # Feature flags for new capabilities
        self.use_semantic_matching = use_semantic_matching and SENTENCE_TRANSFORMERS_AVAILABLE
        self.use_templates = use_templates and TemplateRegistry is not None
        self.use_table_transformer = use_table_transformer and TableTransformerEngine is not None
        self.use_ensemble = use_ensemble and EnsembleFusion is not None
        self.use_batch_categories = use_batch_categories
        self.use_acroform = use_acroform
        self.use_positional = use_positional and PositionalMatcher is not None
        self.use_preprocess = use_preprocess
        self.use_align_to_template = use_align_to_template
        self.use_smart_ensemble = use_smart_ensemble
        self.use_field_validation = use_field_validation
        self.use_vlm_crop_extract = use_vlm_crop_extract and bool(getattr(llm_engine, "vlm_extract_model", None))
        self.use_dual_llm_validate = use_dual_llm_validate
        # Parallel VLM: use ThreadPoolExecutor for concurrent VLM API calls
        self.parallel_vlm = parallel_vlm
        self.vlm_max_workers = vlm_max_workers
        # Multimodal extraction: send both image + OCR text to VLM in single call
        self.use_multimodal = use_multimodal and bool(getattr(llm_engine, "vlm_extract_model", None))
        # Confidence routing: skip high-confidence fields in VLM/LLM passes
        self.confidence_routing = confidence_routing
        self.confidence_threshold = confidence_threshold
        # Checkbox crop extraction: tight crops + enhanced contrast + focused VLM
        self.use_checkbox_crops = use_checkbox_crops and bool(getattr(llm_engine, "vlm_extract_model", None))
        # VLM-OCR two-stage extraction (--glm-ocr / --nanonets-ocr)
        self.use_glm_ocr = use_glm_ocr and bool(getattr(llm_engine, "vlm_ocr_model", None))
        self.use_nanonets_ocr = use_nanonets_ocr and bool(getattr(llm_engine, "vlm_ocr_model", None))
        # Confidence-based human review: flag low-confidence fields for correction
        self.generate_review = generate_review
        self.review_threshold = review_threshold
        # Lazy-initialized components
        self._semantic_matcher_cache: Dict[str, Any] = {}
        self._template_registry: Optional[Any] = None
        self._table_transformer: Optional[Any] = None

    # ==================================================================
    # Knowledge base context helper
    # ==================================================================

    def _get_knowledge_context(
        self, form_type: str, category: str, field_names: list[str]
    ) -> str:
        """Retrieve relevant knowledge context for extraction prompts."""
        if self.knowledge_store is None:
            return ""
        try:
            results = []
            # Field definitions for this form + category
            results.extend(
                self.knowledge_store.query(
                    f"{category} fields ACORD {form_type}",
                    collection="acord_fields",
                    n_results=5,
                    where={"form_type": form_type},
                )
            )
            # Glossary terms related to the category
            results.extend(
                self.knowledge_store.query(
                    category, collection="insurance_glossary", n_results=2
                )
            )
            # Form structure info
            results.extend(
                self.knowledge_store.query(
                    f"ACORD {form_type} {category}",
                    collection="form_structure",
                    n_results=2,
                )
            )
            if not results:
                return ""
            # Sort by relevance and format
            results.sort(key=lambda r: r.get("distance", 999))
            ctx = self.knowledge_store.format_context(results, max_chars=1500)
            return f"\n=== INSURANCE KNOWLEDGE CONTEXT ===\n{ctx}\n"
        except Exception:
            return ""

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

        # ---- Step 2b: Image alignment to canonical template (opt-in) -----
        aligned_image_paths = None
        if self.use_align_to_template and IMAGE_ALIGNER_AVAILABLE and ocr_result.image_paths:
            print("\n  [ALIGN] Aligning scanned images to canonical template ...")
            aligned_dir = output_dir / "aligned"
            aligned_dir.mkdir(parents=True, exist_ok=True)
            aligned_image_paths = []
            for page_idx, img_path in enumerate(ocr_result.image_paths):
                template_path = get_template_image(form_type, page_idx)
                if template_path:
                    out_path = aligned_dir / f"{img_path.stem}_aligned.png"
                    try:
                        aligned_path, H = align_to_template(img_path, template_path, out_path)
                        aligned_image_paths.append(aligned_path)
                    except Exception as e:
                        print(f"    [ALIGN] Page {page_idx} failed: {e}")
                        aligned_image_paths.append(img_path)
                else:
                    aligned_image_paths.append(img_path)
            if any(p != orig for p, orig in zip(aligned_image_paths, ocr_result.image_paths)):
                print(f"    [ALIGN] {sum(1 for p, o in zip(aligned_image_paths, ocr_result.image_paths) if p != o)} pages aligned")
            else:
                print("    [ALIGN] No template images found, using original images")
                aligned_image_paths = None

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
            # Use aligned images for checkbox detection if available
            checkbox_images = aligned_image_paths or getattr(ocr_result, 'clean_image_paths', None) or getattr(ocr_result, 'image_paths', [])
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

        # Initialize ensemble if enabled (--smart-ensemble implies --ensemble)
        ensemble: Optional[Any] = None
        if (self.use_ensemble or self.use_smart_ensemble) and EnsembleFusion is not None:
            ensemble = EnsembleFusion(smart_ensemble=self.use_smart_ensemble)
            # Set field types for smart ensemble weighting and checkbox crop override
            if (self.use_smart_ensemble or self.use_checkbox_crops) and schema:
                field_type_map = {}
                for fname, finfo in schema.fields.items():
                    field_type_map[fname] = getattr(finfo, "field_type", "text") or "text"
                ensemble.set_field_types(field_type_map)
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
        if self.use_vlm_extract and ocr_result.clean_image_paths:
            total_steps += 1  # vlm-extract: direct VLM extraction from page images
        if self.use_vlm_crop_extract and ocr_result.clean_image_paths:
            total_steps += 1  # vlm-crop-extract: cropped VLM extraction
        if self.use_multimodal and ocr_result.clean_image_paths:
            total_steps += 1  # multimodal: combined image + OCR text VLM
        if self.use_checkbox_crops and ocr_result.clean_image_paths:
            total_steps += 1  # checkbox-crops: focused checkbox region VLM
        if (self.use_glm_ocr or self.use_nanonets_ocr) and ocr_result.image_paths:
            total_steps += 1  # vlm-ocr: two-stage VLM-OCR extraction
        if self.use_vision and ocr_result.clean_image_paths:
            total_steps += 1  # vision: single unified pass (image + docling + spatial)
        if self.use_dual_llm_validate:
            total_steps += 1  # dual-llm-validate: second LLM pass for verification
        if self.use_text_llm:
            total_steps += category_steps
            if "driver" in schema.categories and form_type == "127":
                total_steps += 1
            if "vehicle" in schema.categories and form_type in ("127", "137"):
                total_steps += 1
            total_steps += 1  # gap-fill pass

        step = 0
        vision_skipped_404 = False  # set True if VLM model not found
        vlm_extract_skipped_404 = False  # set True if VLM extract model not found

        # ---- Confidence routing: determine which fields to skip in VLM/LLM ----
        high_conf_fields: Set[str] = set()
        if self.confidence_routing and ensemble:
            high_conf_fields = ensemble.get_high_confidence_fields(
                threshold=self.confidence_threshold,
            )
            if high_conf_fields:
                print(f"  [ROUTING] {len(high_conf_fields)} high-confidence fields (>={self.confidence_threshold}) will be skipped in VLM/LLM passes")

        # ---- Step 4-vlm: Direct VLM extraction (--vlm-extract) ----
        # Runs AFTER spatial/positional/template/semantic prefill, BEFORE text LLM.
        # VLM reads page images directly and extracts structured JSON per category batch.
        if self.use_vlm_extract and ocr_result.clean_image_paths:
            self.llm.unload_text_model()
            step += 1
            missing_for_vlm = [n for n in all_field_names if n not in extracted]
            # Confidence routing: skip fields already extracted with high confidence
            if high_conf_fields:
                before_routing = len(missing_for_vlm)
                missing_for_vlm = [n for n in missing_for_vlm if n not in high_conf_fields]
                skipped = before_routing - len(missing_for_vlm)
                if skipped:
                    print(f"    [ROUTING] Skipped {skipped} high-confidence fields from VLM extract")
            print(f"\n  [{step}/{total_steps}] VLM Direct Extract ({len(missing_for_vlm)} remaining fields) ...")
            try:
                vlm_extract_result = self._vlm_extract_pass(
                    form_type=form_type,
                    schema=schema,
                    image_paths=ocr_result.clean_image_paths,
                    extracted=extracted,
                    field_sources=field_sources,
                    CAT_PAGES=CAT_PAGES,
                )
                # Merge: skip fields from spatial/acroform (priority sources)
                vlm_new = 0
                for k, v in vlm_extract_result.items():
                    if field_sources.get(k) in ("spatial", "acroform"):
                        continue
                    if k not in extracted and v is not None:
                        extracted[k] = v
                        field_sources[k] = "vlm_extract"
                        vlm_new += 1
                if ensemble:
                    ensemble.add_results("vlm_extract", vlm_extract_result, confidence=0.88)
                print(f"    -> {vlm_new} new fields from VLM direct extract")
            except VisionModelNotFoundError as e:
                print(f"    [VLM-EXT] Skipping: {e}")
                vlm_extract_skipped_404 = True
            self.llm.unload_vlm_extract_model()
            cleanup_gpu_memory()

        # ---- Step 4-vlm-crop: Cropped VLM extraction (--vlm-crop-extract) ----
        vlm_crop_skipped_404 = False
        if self.use_vlm_crop_extract and ocr_result.clean_image_paths:
            self.llm.unload_text_model()
            step += 1
            missing_for_crop = [n for n in all_field_names if n not in extracted]
            print(f"\n  [{step}/{total_steps}] VLM Cropped Extract ({len(missing_for_crop)} remaining fields) ...")
            try:
                crop_result = self._vlm_crop_extract_pass(
                    form_type=form_type,
                    schema=schema,
                    image_paths=aligned_image_paths or ocr_result.image_paths,
                    extracted=extracted,
                    field_sources=field_sources,
                )
                crop_new = 0
                for k, v in crop_result.items():
                    if field_sources.get(k) in ("spatial", "acroform"):
                        continue
                    if k not in extracted and v is not None:
                        extracted[k] = v
                        field_sources[k] = "vlm_crop_extract"
                        crop_new += 1
                if ensemble:
                    ensemble.add_results("vlm_crop_extract", crop_result, confidence=0.90)
                print(f"    -> {crop_new} new fields from cropped VLM extract")
            except VisionModelNotFoundError as e:
                print(f"    [VLM-CROP] Skipping: {e}")
                vlm_crop_skipped_404 = True
            self.llm.unload_vlm_extract_model()
            cleanup_gpu_memory()

        # ---- Step 4-vlm-ocr: Two-stage VLM-OCR extraction (--glm-ocr / --nanonets-ocr) ----
        vlm_ocr_skipped_404 = False
        if (self.use_glm_ocr or self.use_nanonets_ocr) and ocr_result.image_paths:
            self.llm.unload_text_model()
            step += 1
            backend_name = "GLM-OCR" if self.use_glm_ocr else "Nanonets-OCR"
            missing_for_vlm_ocr = [n for n in all_field_names if n not in extracted]
            # Confidence routing
            if high_conf_fields:
                before_routing = len(missing_for_vlm_ocr)
                missing_for_vlm_ocr = [n for n in missing_for_vlm_ocr if n not in high_conf_fields]
                skipped = before_routing - len(missing_for_vlm_ocr)
                if skipped:
                    print(f"    [ROUTING] Skipped {skipped} high-confidence fields from {backend_name}")
            print(f"\n  [{step}/{total_steps}] {backend_name} Two-Stage Extract ({len(missing_for_vlm_ocr)} remaining fields) ...")
            try:
                vlm_ocr_result = self._vlm_ocr_two_stage_pass(
                    form_type=form_type,
                    schema=schema,
                    image_paths=ocr_result.image_paths,
                    extracted=extracted,
                    field_sources=field_sources,
                    CAT_PAGES=CAT_PAGES,
                    table_markdown=table_markdown,
                )
                vlm_ocr_new = 0
                for k, v in vlm_ocr_result.items():
                    if field_sources.get(k) in ("spatial", "acroform"):
                        continue
                    if k not in extracted and v is not None:
                        extracted[k] = v
                        field_sources[k] = "vlm_ocr"
                        vlm_ocr_new += 1
                if ensemble:
                    ensemble.add_results("vlm_ocr", vlm_ocr_result, confidence=0.87)
                print(f"    -> {vlm_ocr_new} new fields from {backend_name} two-stage extract")
            except VisionModelNotFoundError as e:
                print(f"    [VLM-OCR] Skipping: {e}")
                vlm_ocr_skipped_404 = True
            self.llm.unload_vlm_ocr_model()
            cleanup_gpu_memory()

        # ---- Step 4-multimodal: Multimodal extraction (--multimodal) ----
        multimodal_skipped_404 = False
        if self.use_multimodal and ocr_result.clean_image_paths:
            self.llm.unload_text_model()
            step += 1
            missing_for_mm = [n for n in all_field_names if n not in extracted]
            # Confidence routing: skip high-confidence fields
            if self.confidence_routing and ensemble:
                high_conf = ensemble.get_high_confidence_fields(self.confidence_threshold)
                before_len = len(missing_for_mm)
                missing_for_mm = [n for n in missing_for_mm if n not in high_conf]
                if before_len != len(missing_for_mm):
                    print(f"    [CONF-ROUTE] Skipping {before_len - len(missing_for_mm)} high-confidence fields")
            print(f"\n  [{step}/{total_steps}] Multimodal Extract ({len(missing_for_mm)} fields) ...")
            try:
                mm_result = self._multimodal_extract_pass(
                    form_type=form_type,
                    schema=schema,
                    image_paths=ocr_result.clean_image_paths,
                    extracted=extracted,
                    field_sources=field_sources,
                    CAT_PAGES=CAT_PAGES,
                    page_bbox_text=page_bbox_text,
                    page_docling=page_docling,
                    table_markdown=table_markdown,
                )
                mm_new = 0
                for k, v in mm_result.items():
                    if field_sources.get(k) in ("spatial", "acroform"):
                        continue
                    if k not in extracted and v is not None:
                        extracted[k] = v
                        field_sources[k] = "multimodal"
                        mm_new += 1
                if ensemble:
                    ensemble.add_results("multimodal", mm_result, confidence=0.92)
                print(f"    -> {mm_new} new fields from multimodal extract")
            except VisionModelNotFoundError as e:
                print(f"    [MULTIMODAL] Skipping: {e}")
                multimodal_skipped_404 = True
            self.llm.unload_vlm_extract_model()
            cleanup_gpu_memory()

        # ---- Step 4-checkbox-crops: Checkbox crop extraction (--checkbox-crops) ----
        checkbox_crop_skipped_404 = False
        if self.use_checkbox_crops and ocr_result.clean_image_paths:
            self.llm.unload_text_model()
            step += 1
            print(f"\n  [{step}/{total_steps}] Checkbox Crop Extract ...")
            try:
                cb_crop_result = self._checkbox_crop_pass(
                    form_type=form_type,
                    schema=schema,
                    image_paths=aligned_image_paths or ocr_result.image_paths,
                )
                cb_new = 0
                for k, v in cb_crop_result.items():
                    if field_sources.get(k) in ("spatial", "acroform", "positional_checkbox"):
                        continue
                    if k not in extracted and v is not None:
                        extracted[k] = v
                        field_sources[k] = "vlm_checkbox_crop"
                        cb_new += 1
                if ensemble:
                    ensemble.add_results("vlm_checkbox_crop", cb_crop_result, confidence=0.93)
                print(f"    -> {cb_new} new checkbox fields from crop VLM")
            except VisionModelNotFoundError as e:
                print(f"    [CB-CROP] Skipping: {e}")
                checkbox_crop_skipped_404 = True
            self.llm.unload_vlm_extract_model()
            cleanup_gpu_memory()

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

        # ---- Targeted small-field recovery pass (Task #17) ----
        # For missing small text fields (state codes, Y/N, single-char codes) that have
        # positional data, search OCR bboxes for text blocks overlapping the field region.
        # This catches fields that spatial/LLM passes missed due to narrow widget size.
        if self.use_positional and schema and schema.get_positioned_fields():
            _SMALL_FIELD_PATTERNS = (
                "stateorprovincecode", "broadenednofaultcode", "driverothercarcode",
                "sr22fr44", "usepercent", "symbolcode",
            )
            missing_small = []
            for n in all_field_names:
                if n in extracted:
                    continue
                fi = schema.fields.get(n)
                if not fi or fi.field_type in ("checkbox", "radio"):
                    continue
                if fi.x_min is None or fi.x_max is None:
                    continue
                # Target small fields by widget width (< 80 pixels) or known patterns
                field_width = fi.x_max - fi.x_min
                nl = n.lower()
                if field_width < 80 or any(pat in nl for pat in _SMALL_FIELD_PATTERNS):
                    missing_small.append(fi)

            if missing_small and page_bbox:
                from positional_matcher import PositionalMatcher as _PM_recovery
                _pm_r = _PM_recovery()
                offsets_r = _pm_r.compute_alignment(schema, page_bbox)
                recovered_small = 0
                for fi in missing_small:
                    page_idx = fi.page
                    if page_idx is None or page_idx >= len(page_bbox):
                        continue
                    dx, dy = offsets_r[page_idx] if page_idx < len(offsets_r) else (0.0, 0.0)
                    fx0 = fi.x_min + dx
                    fy0 = fi.y_min + dy
                    fx1 = fi.x_max + dx
                    fy1 = fi.y_max + dy
                    # Expand search region slightly for small fields
                    pad_x = max(5, (fx1 - fx0) * 0.3)
                    pad_y = max(3, (fy1 - fy0) * 0.2)
                    # Search bbox data for text blocks in this region
                    best_text = None
                    best_dist = float("inf")
                    for block in page_bbox[page_idx]:
                        bx, by = block.get("x", 0), block.get("y", 0)
                        bw = block.get("w", 0)
                        bh = block.get("h", 0)
                        bx1 = bx + bw
                        by1 = by + bh
                        # Check if block center is within expanded field region
                        bcx = (bx + bx1) / 2
                        bcy = (by + by1) / 2
                        if fx0 - pad_x <= bcx <= fx1 + pad_x and fy0 - pad_y <= bcy <= fy1 + pad_y:
                            text = block.get("text", "").strip()
                            if not text or len(text) > 20:
                                continue
                            # Prefer blocks closer to field center
                            fcx = (fx0 + fx1) / 2
                            fcy = (fy0 + fy1) / 2
                            dist = ((bcx - fcx) ** 2 + (bcy - fcy) ** 2) ** 0.5
                            if dist < best_dist:
                                best_dist = dist
                                best_text = text
                    if best_text:
                        # Validate: for state codes, must be 2-letter alpha
                        nl = fi.name.lower()
                        if "stateorprovincecode" in nl:
                            if len(best_text) == 2 and best_text.isalpha():
                                extracted[fi.name] = best_text.upper()
                                field_sources[fi.name] = "small_field_recovery"
                                recovered_small += 1
                        elif "usepercent" in nl:
                            digits = re.sub(r"[^\d]", "", best_text)
                            if digits and 0 <= int(digits) <= 100:
                                extracted[fi.name] = digits
                                field_sources[fi.name] = "small_field_recovery"
                                recovered_small += 1
                        else:
                            extracted[fi.name] = best_text
                            field_sources[fi.name] = "small_field_recovery"
                            recovered_small += 1
                if recovered_small:
                    print(f"  [SMALL-FIELD] Recovered {recovered_small} small text fields via positional search")

        # ---- VLM checkbox pass (after text LLM, before ensemble) ----
        # Only for truly missing checkboxes — do NOT override existing positional results
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

        # ---- VLM driver narrow-column field rescue ----
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
            # Use ensemble results — override extracted with fused winners
            pre_ensemble_count = len(extracted)
            overrides = 0
            for k, v in fused_fields.items():
                if v is None:
                    continue
                old_source = field_sources.get(k)
                new_source = ensemble_metadata[k]["source"]
                if k in extracted and old_source != new_source:
                    overrides += 1
                extracted[k] = v
                field_sources[k] = new_source
            disagreements = ensemble.get_disagreements()
            print(f"  [ENSEMBLE] Fused {len(fused_fields)} fields from {len(ensemble._results)} field entries")
            if overrides:
                print(f"    {overrides} field(s) overridden by ensemble winner")
            if disagreements:
                print(f"    {len(disagreements)} field(s) with source disagreements")
            _save_json(ensemble_metadata, output_dir / "ensemble_metadata.json")

        # ---- Dual-LLM validation (second LLM pass to verify extracted values) ----
        if self.use_dual_llm_validate and extracted:
            step += 1
            print(f"\n  [{step}/{total_steps}] Dual-LLM validation ({len(extracted)} fields) ...")
            cleanup_gpu_memory()
            dual_result, dual_warnings = self._dual_llm_validate(
                extracted, bbox_text, docling_text, schema,
            )
            # Apply corrections from second LLM pass
            corrections = 0
            for k, info in dual_result.items():
                if not info.get("correct", True) and info.get("suggested"):
                    suggested = info["suggested"]
                    if k in extracted and suggested and str(suggested).strip():
                        extracted[k] = suggested
                        corrections += 1
            if corrections:
                print(f"    -> {corrections} fields corrected by dual-LLM validation")
            if dual_warnings:
                print(f"    -> {len(dual_warnings)} validation warnings")
                from utils import save_json as _sv
                _sv(dual_warnings, output_dir / "dual_llm_warnings.json")

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

        # ---- Cross-field validation (opt-in) ----
        if self.use_field_validation and FIELD_VALIDATOR_AVAILABLE:
            print("\n  [VALIDATE] Running cross-field validation ...")
            extracted, validation_warnings = validate_and_fix(extracted, form_type, schema)
            if validation_warnings:
                print(f"    -> {len(validation_warnings)} validation warnings:")
                for w in validation_warnings[:5]:
                    print(f"      - {w}")
                if len(validation_warnings) > 5:
                    print(f"      ... and {len(validation_warnings) - 5} more")
                from utils import save_json as _sv2
                _sv2(validation_warnings, output_dir / "validation_warnings.json")
            else:
                print("    -> All cross-field checks passed")

        # Smart checkbox pixel verification with multi-resolution (Task #15):
        # Use pixel analysis at 1x and 2x zoom to verify checkbox states.
        # Ambiguous cases (ratio between clear thresholds) get a 2x zoom re-check.
        if self.use_positional and schema.get_positioned_fields():
            checkbox_images = getattr(ocr_result, 'clean_image_paths', None) or getattr(ocr_result, 'image_paths', [])
            if checkbox_images:
                from positional_matcher import PositionalMatcher as _PM
                _pm = _PM()
                offsets = _pm.compute_alignment(schema, page_bbox)
                defaulted_off = 0
                corrected_off = 0   # "1" overridden to "Off" (clearly empty)
                corrected_on = 0    # "Off" overridden to "1" (clearly checked)
                zoom_resolved = 0   # Ambiguous at 1x, resolved by 2x zoom
                for fi in schema.get_positioned_fields():
                    if fi.field_type not in ("checkbox", "radio"):
                        continue
                    page_idx = fi.page
                    if page_idx >= len(checkbox_images):
                        continue
                    dx, dy = offsets[page_idx] if page_idx < len(offsets) else (0.0, 0.0)
                    fx0 = fi.x_min + dx
                    fy0 = fi.y_min + dy
                    fx1 = fi.x_max + dx
                    fy1 = fi.y_max + dy
                    ratio = _pm._get_checkbox_pixel_ratio(
                        fx0, fy0, fx1, fy1,
                        checkbox_images[page_idx],
                    )
                    if ratio is None:
                        continue

                    current = extracted.get(fi.name)

                    # Multi-resolution: for ambiguous ratios (0.10-0.28), do 2x zoom re-check
                    # by expanding the crop region and using tighter thresholds
                    if 0.10 <= ratio <= 0.28:
                        # Expand crop by 50% in each direction for better context
                        w = fx1 - fx0
                        h = fy1 - fy0
                        zoom_ratio = _pm._get_checkbox_pixel_ratio(
                            fx0 - w * 0.25, fy0 - h * 0.25,
                            fx1 + w * 0.25, fy1 + h * 0.25,
                            checkbox_images[page_idx],
                        )
                        if zoom_ratio is not None:
                            # Use the average of both ratios for more stable decision
                            avg_ratio = (ratio + zoom_ratio) / 2
                            if current is None:
                                if avg_ratio < 0.08:
                                    extracted[fi.name] = "Off"
                                    field_sources[fi.name] = "pixel_empty"
                                    defaulted_off += 1
                                    zoom_resolved += 1
                                elif avg_ratio > 0.20:
                                    extracted[fi.name] = "1"
                                    field_sources[fi.name] = "pixel_zoom"
                                    corrected_on += 1
                                    zoom_resolved += 1
                            elif str(current) == "1" and avg_ratio < 0.08:
                                extracted[fi.name] = "Off"
                                corrected_off += 1
                                zoom_resolved += 1
                            elif str(current) in ("Off", "false", "False") and avg_ratio > 0.20:
                                extracted[fi.name] = "1"
                                corrected_on += 1
                                zoom_resolved += 1
                            continue  # Handled by zoom path

                    if current is None:
                        # Missing checkbox: default to "Off" if clearly empty
                        if ratio < 0.05:
                            extracted[fi.name] = "Off"
                            field_sources[fi.name] = "pixel_empty"
                            defaulted_off += 1
                    elif str(current) == "1" and ratio < 0.10:
                        # Ensemble says checked, but pixel says clearly empty → override
                        extracted[fi.name] = "Off"
                        corrected_off += 1
                    elif str(current) in ("Off", "false", "False") and ratio > 0.28:
                        # Ensemble says unchecked, but pixel says clearly checked → override
                        extracted[fi.name] = "1"
                        corrected_on += 1

                msgs = []
                if defaulted_off:
                    msgs.append(f"{defaulted_off} empty→Off")
                if corrected_off:
                    msgs.append(f"{corrected_off} false-checked→Off")
                if corrected_on:
                    msgs.append(f"{corrected_on} false-unchecked→1")
                if zoom_resolved:
                    msgs.append(f"{zoom_resolved} resolved-by-zoom")
                if msgs:
                    print(f"  [PIXEL-VERIFY] Checkbox pixel verification: {', '.join(msgs)}")

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

        # ---- Effective confidence (always computed) ----
        effective_confidence = self._compute_effective_confidence(
            extracted, field_sources, field_confidence, ensemble_metadata,
        )

        # ---- Human review manifest (opt-in) ----
        review_manifest = None
        if self.generate_review:
            review_manifest = self._generate_review_manifest(
                extracted, effective_confidence, field_sources,
                field_verified, ensemble_metadata, schema, bbox_plain,
            )
            summary = review_manifest["summary"]
            print(f"\n  [REVIEW] {summary['fields_for_review']}/{summary['total_fields']} fields "
                  f"flagged for review ({summary['review_rate_percent']}% review rate, "
                  f"threshold={summary['review_threshold']})")
            _save_json(review_manifest, output_dir / "review_manifest.json")

        # ---- Unload LLM from GPU (done with this form) -------------------
        self.llm.unload_model()

        elapsed = time.time() - start

        print(f"\n{'='*60}")
        print(f"  EXTRACTION COMPLETE")
        print(f"  Fields extracted: {len(extracted)}")
        print(f"  Time: {elapsed:.1f}s")
        print(f"{'='*60}\n")

        metadata = {
            "form_type": form_type,
            "source_pdf": str(pdf_path),
            "fields_extracted": len(extracted),
            "fields_verified": len(verified),
            "field_sources": field_sources,
            "field_verified": field_verified,
            "field_confidence": field_confidence,
            "effective_confidence": effective_confidence,
            "total_schema_fields": schema.total_fields,
            "pages": ocr_result.num_pages,
            "extraction_time_seconds": round(elapsed, 2),
            "model": self.llm.model,
        }
        if review_manifest is not None:
            metadata["review_manifest"] = review_manifest

        return {
            "extracted_fields": extracted,
            "metadata": metadata,
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

        # 1. Docling text per page (markdown or HTML depending on config)
        docling_cache_name = "docling_html_pages.json" if getattr(self.ocr, 'docling_html', False) else "docling_pages.json"
        save_json(ocr_result.docling_pages, output_dir / docling_cache_name)

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

            few_shot = self._get_knowledge_context(form_type, category, batch)
            if self.rag_store is not None:
                few_shot += self.rag_store.retrieve(form_type, category, batch, k=3)
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
                gap_few_shot = self._get_knowledge_context(form_type, category, gap_batch)
                if self.rag_store is not None:
                    gap_few_shot += self.rag_store.retrieve_for_fields(form_type, gap_batch, k=2)
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

    # ==================================================================
    # VLM Direct Extract (--vlm-extract: page image → structured JSON)
    # ==================================================================

    @staticmethod
    def _match_vlm_key(vlm_key: str, batch_keys: List[str]) -> Optional[str]:
        """Fuzzy-match a VLM-returned key to the expected schema keys.

        Handles normalisation (underscores, case) and substring overlap.
        Shared by _vlm_extract_pass and existing vision passes.
        """
        if vlm_key in batch_keys:
            return vlm_key
        vlm_norm = vlm_key.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
        vlm_norm = re.sub(r"_+", "_", vlm_norm).strip("_")
        for b in batch_keys:
            b_norm = b.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
            b_norm = re.sub(r"_+", "_", b_norm).strip("_")
            if b_norm == vlm_norm:
                return b
        # Fuzzy: one key contains the other
        for b in batch_keys:
            b_norm = b.strip().replace(" ", "_").replace("-", "_").replace("/", "_").lower()
            b_norm = re.sub(r"_+", "_", b_norm).strip("_")
            if len(b_norm) < 5:
                continue
            if vlm_norm in b_norm or b_norm in vlm_norm:
                if min(len(vlm_norm), len(b_norm)) / max(len(vlm_norm), len(b_norm)) >= 0.6:
                    return b
        return None

    @staticmethod
    def _crop_row_image(image_path: Path, y_min: float, y_max: float, padding: int = 30) -> Path:
        """Crop a page image to a horizontal band (full width) and save to a temp file.

        Used to isolate individual driver rows for focused VLM extraction.

        Args:
            image_path: Path to the full page image.
            y_min: Top Y coordinate of the row region.
            y_max: Bottom Y coordinate of the row region.
            padding: Extra pixels above and below the row.

        Returns:
            Path to the cropped temporary image file.
        """
        import tempfile
        from PIL import Image

        img = Image.open(image_path)
        w, h = img.size
        top = max(0, int(y_min) - padding)
        bottom = min(h, int(y_max) + padding)
        cropped = img.crop((0, top, w, bottom))

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        cropped.save(tmp.name)
        tmp.close()
        return Path(tmp.name)

    def _exec_vlm_task(
        self,
        prompt: str,
        image_path: Path,
        field_names: List[str],
        checkbox_field_set: set,
        label: str = "",
    ) -> Tuple[Dict[str, Any], bool]:
        """Execute a single VLM extraction call. Thread-safe.

        Returns:
            (result_dict, is_404) — result_dict maps field_name→value,
            is_404 is True if VisionModelNotFoundError was raised.
        """
        result: Dict[str, Any] = {}
        try:
            response = self.llm.generate_vlm_extract(
                prompt, image_path, max_tokens=4096,
            )
            batch_result = self.llm.parse_json(response)
            for k, v in batch_result.items():
                if v is None or (isinstance(v, str) and not v.strip()):
                    continue
                canonical = self._match_vlm_key(k, field_names)
                if canonical:
                    if canonical in checkbox_field_set:
                        result[canonical] = self._normalise_checkbox_value(v)
                    else:
                        result[canonical] = v
            return result, False
        except VisionModelNotFoundError:
            return {}, True
        except Exception as e:
            print(f"    [VLM-EXT] {label} error: {e}")
            return {}, False

    def _vlm_extract_pass(
        self,
        form_type: str,
        schema,
        image_paths: List[Path],
        extracted: Dict[str, Any],
        field_sources: Dict[str, str],
        CAT_PAGES: Dict[str, List[int]],
    ) -> Dict[str, Any]:
        """
        Direct VLM extraction from page images (--vlm-extract).

        Strategy:
        1. Group remaining (not yet extracted) fields by page using FieldInfo.page
        2. Collect all (prompt, image_path, field_names) tuples
        3. Execute all VLM calls — parallel (ThreadPoolExecutor) or sequential
        4. Merge all results
        """
        VLM_BATCH_SIZE = 25  # max fields per VLM call for category batches
        result: Dict[str, Any] = {}
        all_field_names = set(schema.fields.keys())
        remaining = [n for n in all_field_names if n not in extracted]
        if not remaining:
            return result

        paths = [Path(p) for p in image_paths if Path(p).exists()]
        if not paths:
            return result

        num_pages = len(paths)
        tooltips_all = self.registry.get_tooltips(form_type, list(all_field_names))

        # Build checkbox set for normalisation
        checkbox_field_set = set()
        for fname, finfo in schema.fields.items():
            if finfo.field_type in ("checkbox", "radio"):
                checkbox_field_set.add(fname)

        # Group remaining fields by page
        fields_by_page: Dict[int, List[str]] = {}
        for fname in remaining:
            fi = schema.fields.get(fname)
            if fi and fi.page is not None and fi.page < num_pages:
                page_idx = fi.page
            else:
                cat = fi.category if fi else None
                if cat and cat in CAT_PAGES:
                    page_idx = CAT_PAGES[cat][0]
                else:
                    page_idx = 0
            if page_idx not in fields_by_page:
                fields_by_page[page_idx] = []
            fields_by_page[page_idx].append(fname)

        # Collect all VLM tasks: (prompt, image_path, field_names, label)
        vlm_tasks: List[Tuple[str, Path, List[str], str]] = []

        for page_idx in sorted(fields_by_page.keys()):
            page_fields = fields_by_page[page_idx]
            if not page_fields:
                continue

            image_path = paths[page_idx] if page_idx < len(paths) else paths[0]

            driver_fields = []
            vehicle_fields = []
            regular_fields = []

            for fname in page_fields:
                fi = schema.fields.get(fname)
                cat = fi.category if fi else None
                if cat == "driver" and form_type in ("127", "163"):
                    driver_fields.append(fname)
                elif cat in ("vehicle", "coverage"):
                    vehicle_fields.append(fname)
                else:
                    regular_fields.append(fname)

            # --- Regular category fields: batch by CATEGORY_BATCHES ---
            if regular_fields:
                from schema_registry import CATEGORY_BATCHES
                batch_groups: Dict[int, List[str]] = {}
                unbatched: List[str] = []
                for fname in regular_fields:
                    fi = schema.fields.get(fname)
                    cat = fi.category if fi else None
                    placed = False
                    if cat:
                        for bi, batch_cats in enumerate(CATEGORY_BATCHES):
                            if cat in batch_cats:
                                if bi not in batch_groups:
                                    batch_groups[bi] = []
                                batch_groups[bi].append(fname)
                                placed = True
                                break
                    if not placed:
                        unbatched.append(fname)

                if unbatched:
                    max_bi = max(batch_groups.keys()) if batch_groups else 0
                    if max_bi not in batch_groups:
                        batch_groups[max_bi] = []
                    batch_groups[max_bi].extend(unbatched)

                for bi in sorted(batch_groups.keys()):
                    group_fields = batch_groups[bi]
                    cats_in_group = set()
                    for fname in group_fields:
                        fi = schema.fields.get(fname)
                        if fi and fi.category:
                            cats_in_group.add(fi.category)
                    cats_list = sorted(cats_in_group)

                    for ci in range(0, len(group_fields), VLM_BATCH_SIZE):
                        chunk = group_fields[ci:ci + VLM_BATCH_SIZE]
                        chunk_tooltips = {k: v for k, v in tooltips_all.items() if k in chunk}
                        prompt = build_vlm_extract_prompt(
                            form_type=form_type,
                            categories=cats_list,
                            field_names=chunk,
                            tooltips=chunk_tooltips,
                            page_number=page_idx + 1,
                            total_pages=num_pages,
                        )
                        vlm_tasks.append((prompt, image_path, chunk, f"Batch p{page_idx+1}"))

            # --- Driver fields: one VLM call per driver row ---
            if driver_fields and form_type == "127":
                driver_by_suffix: Dict[str, List[str]] = {}
                for fname in driver_fields:
                    fi = schema.fields.get(fname)
                    sfx = fi.suffix if fi else None
                    if sfx:
                        if sfx not in driver_by_suffix:
                            driver_by_suffix[sfx] = []
                        driver_by_suffix[sfx].append(fname)

                total_suffixes = len(driver_by_suffix)
                for si, sfx in enumerate(sorted(driver_by_suffix.keys())):
                    sfx_fields = driver_by_suffix[sfx]
                    driver_num = ord(sfx[0].upper()) - ord('A') + 1 if sfx else 1
                    sfx_tooltips = {k: v for k, v in tooltips_all.items() if k in sfx_fields}

                    # Compute row Y bounds and crop image
                    y_vals = []
                    for fn in sfx_fields:
                        fi = schema.fields.get(fn)
                        if fi and fi.y_min is not None and fi.y_max is not None:
                            y_vals.append((fi.y_min, fi.y_max))
                    if y_vals:
                        row_y_min = min(y for y, _ in y_vals)
                        row_y_max = max(y for _, y in y_vals)
                        cropped_path = self._crop_row_image(image_path, row_y_min, row_y_max)
                        # Determine position hint
                        if si < total_suffixes * 0.33:
                            row_pos = "UPPER"
                        elif si < total_suffixes * 0.67:
                            row_pos = "MIDDLE"
                        else:
                            row_pos = "LOWER"
                    else:
                        cropped_path = image_path
                        row_pos = None

                    prompt = build_vlm_extract_driver_prompt(
                        driver_num=driver_num,
                        suffix=sfx,
                        field_names=sfx_fields,
                        tooltips=sfx_tooltips,
                        row_position=row_pos,
                    )
                    vlm_tasks.append((prompt, cropped_path, sfx_fields, f"Driver _{sfx}"))

            # --- Form 163 driver fields: group by Y position (row), crop per row ---
            if driver_fields and form_type == "163":
                # Form 163 has 24 driver rows, each spanning ~100px vertically.
                # Use marital status fields as row anchors (perfectly spaced at ~100px).
                # Assign each driver field to the nearest row band.
                import re as _re

                # Build row bands from marital fields: marital[0]=row1, maritalstatus1[0]=row2, ...
                row_bands: List[Tuple[int, float, float]] = []  # (row_num, y_min, y_max)
                for fname in driver_fields:
                    m = _re.match(r'^marital(?:status(\d+))?\[0\]$', fname)
                    if m:
                        fi = schema.fields.get(fname)
                        if fi and fi.y_min is not None and fi.y_max is not None:
                            row_idx = int(m.group(1)) + 1 if m.group(1) else 1
                            row_bands.append((row_idx, fi.y_min, fi.y_max))
                row_bands.sort(key=lambda t: t[0])

                if row_bands:
                    # Assign each driver field to a row band by Y overlap
                    rows_163: Dict[int, List[str]] = {}
                    rows_163_bounds: Dict[int, Tuple[float, float]] = {}

                    for fname in driver_fields:
                        fi = schema.fields.get(fname)
                        if not fi or fi.y_min is None or fi.y_max is None:
                            continue
                        f_yc = (fi.y_min + fi.y_max) / 2.0
                        # Find nearest row band
                        best_row = 1
                        best_dist = float('inf')
                        for row_idx, ry_min, ry_max in row_bands:
                            band_center = (ry_min + ry_max) / 2.0
                            dist = abs(f_yc - band_center)
                            if dist < best_dist:
                                best_dist = dist
                                best_row = row_idx
                        if best_row not in rows_163:
                            rows_163[best_row] = []
                            rows_163_bounds[best_row] = (fi.y_min, fi.y_max)
                        rows_163[best_row].append(fname)
                        cur_min, cur_max = rows_163_bounds[best_row]
                        rows_163_bounds[best_row] = (min(cur_min, fi.y_min), max(cur_max, fi.y_max))

                    for row_num in sorted(rows_163.keys()):
                        row_fields = rows_163[row_num]
                        ry_min, ry_max = rows_163_bounds[row_num]
                        row_tooltips = {k: v for k, v in tooltips_all.items() if k in row_fields}
                        cropped_path = self._crop_row_image(image_path, ry_min, ry_max)
                        prompt = build_vlm_extract_163_row_prompt(
                            row_num=row_num,
                            field_names=row_fields,
                            tooltips=row_tooltips,
                        )
                        vlm_tasks.append((prompt, cropped_path, row_fields, f"163 Row {row_num}"))

            # --- Vehicle/coverage fields: one VLM call per suffix ---
            if vehicle_fields:
                vehicle_by_suffix: Dict[str, List[str]] = {}
                for fname in vehicle_fields:
                    fi = schema.fields.get(fname)
                    sfx = fi.suffix if fi else None
                    if sfx:
                        if sfx not in vehicle_by_suffix:
                            vehicle_by_suffix[sfx] = []
                        vehicle_by_suffix[sfx].append(fname)

                for sfx in sorted(vehicle_by_suffix.keys()):
                    sfx_fields = vehicle_by_suffix[sfx]
                    sfx_tooltips = {k: v for k, v in tooltips_all.items() if k in sfx_fields}
                    prompt = build_vlm_extract_vehicle_prompt(
                        form_type=form_type,
                        suffix=sfx,
                        field_names=sfx_fields,
                        tooltips=sfx_tooltips,
                    )
                    vlm_tasks.append((prompt, image_path, sfx_fields, f"Vehicle _{sfx}"))

        # Execute VLM tasks — parallel or sequential
        if not vlm_tasks:
            return result

        mode = "parallel" if self.parallel_vlm and len(vlm_tasks) > 1 else "sequential"
        print(f"    [VLM-EXT] {len(vlm_tasks)} VLM tasks ({mode}, workers={self.vlm_max_workers})")

        if self.parallel_vlm and len(vlm_tasks) > 1:
            workers = min(self.vlm_max_workers, len(vlm_tasks))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(
                        self._exec_vlm_task, prompt, img_path, fields, checkbox_field_set, label
                    ): label
                    for prompt, img_path, fields, label in vlm_tasks
                }
                for future in as_completed(futures):
                    task_result, is_404 = future.result()
                    if is_404:
                        # Cancel remaining futures and propagate
                        for f in futures:
                            f.cancel()
                        raise VisionModelNotFoundError(self.llm.vlm_extract_model or "?")
                    result.update(task_result)
        else:
            for prompt, img_path, fields, label in vlm_tasks:
                task_result, is_404 = self._exec_vlm_task(
                    prompt, img_path, fields, checkbox_field_set, label
                )
                if is_404:
                    raise VisionModelNotFoundError(self.llm.vlm_extract_model or "?")
                result.update(task_result)

        print(f"    [VLM-EXT] {len(vlm_tasks)} VLM calls, {len(result)} fields extracted")
        return result

    # ==================================================================
    # Multimodal extraction (--multimodal: image + OCR text → JSON)
    # ==================================================================

    def _multimodal_extract_pass(
        self,
        form_type: str,
        schema,
        image_paths: List[Path],
        extracted: Dict[str, Any],
        field_sources: Dict[str, str],
        CAT_PAGES: Dict[str, List[int]],
        page_bbox_text: List[str],
        page_docling: List[str],
        table_markdown: str = "",
    ) -> Dict[str, Any]:
        """
        Multimodal extraction: sends BOTH the page image AND OCR text to the VLM.

        The VLM can cross-reference what it sees in the image with the OCR text,
        catching errors in both. Uses the same task collection + parallel execution
        as _vlm_extract_pass.
        """
        VLM_BATCH_SIZE = 25
        result: Dict[str, Any] = {}
        all_field_names = set(schema.fields.keys())
        remaining = [n for n in all_field_names if n not in extracted]
        if not remaining:
            return result

        paths = [Path(p) for p in image_paths if Path(p).exists()]
        if not paths:
            return result

        num_pages = len(paths)
        tooltips_all = self.registry.get_tooltips(form_type, list(all_field_names))

        checkbox_field_set = set()
        for fname, finfo in schema.fields.items():
            if finfo.field_type in ("checkbox", "radio"):
                checkbox_field_set.add(fname)

        # Group remaining fields by page
        fields_by_page: Dict[int, List[str]] = {}
        for fname in remaining:
            fi = schema.fields.get(fname)
            if fi and fi.page is not None and fi.page < num_pages:
                page_idx = fi.page
            else:
                cat = fi.category if fi else None
                if cat and cat in CAT_PAGES:
                    page_idx = CAT_PAGES[cat][0]
                else:
                    page_idx = 0
            if page_idx not in fields_by_page:
                fields_by_page[page_idx] = []
            fields_by_page[page_idx].append(fname)

        # Collect VLM tasks with OCR text context
        vlm_tasks: List[Tuple[str, Path, List[str], str]] = []

        for page_idx in sorted(fields_by_page.keys()):
            page_fields = fields_by_page[page_idx]
            if not page_fields:
                continue

            image_path = paths[page_idx] if page_idx < len(paths) else paths[0]

            # Build OCR context for this page
            ocr_context_parts = []
            if page_idx < len(page_docling) and page_docling[page_idx]:
                ocr_context_parts.append(page_docling[page_idx])
            if page_idx < len(page_bbox_text) and page_bbox_text[page_idx]:
                ocr_context_parts.append(page_bbox_text[page_idx])
            ocr_text = "\n\n".join(ocr_context_parts)

            # Group fields into categories for batching
            from schema_registry import CATEGORY_BATCHES
            batch_groups: Dict[int, List[str]] = {}
            unbatched: List[str] = []
            for fname in page_fields:
                fi = schema.fields.get(fname)
                cat = fi.category if fi else None
                placed = False
                if cat:
                    for bi, batch_cats in enumerate(CATEGORY_BATCHES):
                        if cat in batch_cats:
                            if bi not in batch_groups:
                                batch_groups[bi] = []
                            batch_groups[bi].append(fname)
                            placed = True
                            break
                if not placed:
                    unbatched.append(fname)

            if unbatched:
                max_bi = max(batch_groups.keys()) if batch_groups else 0
                if max_bi not in batch_groups:
                    batch_groups[max_bi] = []
                batch_groups[max_bi].extend(unbatched)

            for bi in sorted(batch_groups.keys()):
                group_fields = batch_groups[bi]
                cats_in_group = set()
                for fname in group_fields:
                    fi = schema.fields.get(fname)
                    if fi and fi.category:
                        cats_in_group.add(fi.category)
                cats_list = sorted(cats_in_group)

                for ci in range(0, len(group_fields), VLM_BATCH_SIZE):
                    chunk = group_fields[ci:ci + VLM_BATCH_SIZE]
                    chunk_tooltips = {k: v for k, v in tooltips_all.items() if k in chunk}
                    prompt = build_multimodal_extract_prompt(
                        form_type=form_type,
                        categories=cats_list,
                        field_names=chunk,
                        tooltips=chunk_tooltips,
                        ocr_text=ocr_text,
                        table_markdown=table_markdown,
                        page_number=page_idx + 1,
                        total_pages=num_pages,
                    )
                    vlm_tasks.append((prompt, image_path, chunk, f"MM p{page_idx+1}"))

        if not vlm_tasks:
            return result

        mode = "parallel" if self.parallel_vlm and len(vlm_tasks) > 1 else "sequential"
        print(f"    [MULTIMODAL] {len(vlm_tasks)} tasks ({mode})")

        if self.parallel_vlm and len(vlm_tasks) > 1:
            workers = min(self.vlm_max_workers, len(vlm_tasks))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(
                        self._exec_vlm_task, prompt, img_path, fields, checkbox_field_set, label
                    ): label
                    for prompt, img_path, fields, label in vlm_tasks
                }
                for future in as_completed(futures):
                    task_result, is_404 = future.result()
                    if is_404:
                        for f in futures:
                            f.cancel()
                        raise VisionModelNotFoundError(self.llm.vlm_extract_model or "?")
                    result.update(task_result)
        else:
            for prompt, img_path, fields, label in vlm_tasks:
                task_result, is_404 = self._exec_vlm_task(
                    prompt, img_path, fields, checkbox_field_set, label
                )
                if is_404:
                    raise VisionModelNotFoundError(self.llm.vlm_extract_model or "?")
                result.update(task_result)

        print(f"    [MULTIMODAL] {len(vlm_tasks)} VLM calls, {len(result)} fields extracted")
        return result

    # (Old _checkbox_crop_pass removed — replaced by grid montage version below)

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

        # Pre-extract driver table rows from spatial index (with column alignment)
        driver_rows = self._extract_driver_table_rows(ocr_result, column_map=column_map)

        for suffix_key in sorted(suffix_groups.keys()):
            if suffix_key == "_NONE":
                continue
            suffix = suffix_key.lstrip("_")
            driver_num = ord(suffix) - ord('A') + 1
            field_names = suffix_groups[suffix_key]
            tooltips = self.registry.get_tooltips(form_type, field_names)

            # Get pre-extracted row data for this driver
            row_data = driver_rows.get(driver_num, "")

            driver_few_shot = self._get_knowledge_context(form_type, "driver", field_names)
            if self.rag_store is not None:
                driver_few_shot += self.rag_store.retrieve(form_type, "driver", field_names, k=3)
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
        self, ocr_result: OCRResult, column_map: Optional[Dict[str, int]] = None,
    ) -> Dict[int, str]:
        """
        Pre-extract driver table rows from spatial data.

        Returns {driver_num: formatted_row_text} for each detected driver row.
        When column_map is provided, labels each value with its column name
        for structured table extraction (Task #18).
        """
        if not ocr_result.spatial_indices:
            return {}

        # Build sorted column boundaries for column-to-value assignment
        sorted_cols: List[Tuple[str, int]] = []
        if column_map:
            sorted_cols = sorted(column_map.items(), key=lambda t: t[1])

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

                sorted_blocks = sorted(row.blocks, key=lambda b: b.x)

                # Enhanced: assign each block to nearest column header
                if sorted_cols:
                    parts = []
                    for block in sorted_blocks:
                        text = block.text.strip()
                        if not text:
                            continue
                        # Find nearest column by X position
                        best_col = None
                        best_dist = float("inf")
                        for col_name, col_x in sorted_cols:
                            dist = abs(block.x - col_x)
                            if dist < best_dist:
                                best_dist = dist
                                best_col = col_name
                        if best_col and best_dist < 150:
                            parts.append(f"{best_col}={text}")
                        else:
                            parts.append(f"{text} [X={block.x}]")
                    row_text = " | ".join(parts)
                else:
                    # Fallback: raw position-based format
                    parts = []
                    for block in sorted_blocks:
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

            vehicle_few_shot = self._get_knowledge_context(form_type, "vehicle", field_names)
            if self.rag_store is not None:
                vehicle_few_shot += self.rag_store.retrieve(form_type, "vehicle", field_names, k=3)
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
            gap_few_shot = self._get_knowledge_context(form_type, "general", batch)
            if self.rag_store is not None:
                gap_few_shot += self.rag_store.retrieve_for_fields(form_type, batch, k=2)
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
    # Confidence-based human review
    # ==================================================================

    def _compute_effective_confidence(
        self,
        extracted: Dict[str, Any],
        field_sources: Dict[str, str],
        field_confidence: Dict[str, float],
        ensemble_metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Compute a unified effective confidence score (0-1) per field.

        Combines ensemble confidence (when available) with BBox verification
        into a single score. Always called; result stored in metadata.
        """
        from ensemble import SOURCE_CONFIDENCE

        effective: Dict[str, float] = {}

        for field_name in extracted:
            bbox_conf = field_confidence.get(field_name, 0.5)

            if ensemble_metadata and field_name in ensemble_metadata:
                # Ensemble was used — start from ensemble confidence
                ens_conf = ensemble_metadata[field_name]["confidence"]
                # Demote if BBox verification disagrees
                if bbox_conf < 0.7:
                    ens_conf = min(ens_conf, 0.80)
                effective[field_name] = round(ens_conf, 3)
            else:
                # No ensemble — synthesize from source confidence + BBox
                source = field_sources.get(field_name, "text_llm")
                src_conf = SOURCE_CONFIDENCE.get(source, 0.5)
                score = src_conf * (0.5 + 0.5 * bbox_conf)
                effective[field_name] = round(score, 3)

        return effective

    def _generate_review_manifest(
        self,
        extracted: Dict[str, Any],
        effective_confidence: Dict[str, float],
        field_sources: Dict[str, str],
        field_verified: Dict[str, bool],
        ensemble_metadata: Optional[Dict[str, Any]],
        schema: Any,
        bbox_plain: str,
    ) -> Dict[str, Any]:
        """
        Generate a review manifest for fields below the review threshold.

        Returns dict with 'summary' and 'fields' (sorted lowest confidence first).
        """
        review_fields = []

        for field_name, value in extracted.items():
            conf = effective_confidence.get(field_name, 0.0)
            if conf >= self.review_threshold:
                continue

            source = field_sources.get(field_name, "unknown")
            verified = field_verified.get(field_name, False)

            # Get field type and category from schema
            field_type = "text"
            category = "general"
            if schema:
                field_info = schema.fields.get(field_name)
                if field_info:
                    field_type = getattr(field_info, "field_type", "text") or "text"
                    category = getattr(field_info, "category", "general") or "general"

            # Ensemble agreement info
            agreement_count = 1
            all_sources = [{"source": source, "value": str(value), "confidence": conf}]
            if ensemble_metadata and field_name in ensemble_metadata:
                em = ensemble_metadata[field_name]
                agreement_count = em.get("agreement_count", 1)
                all_sources = em.get("all_sources", all_sources)

            ocr_snippet = self._find_ocr_snippet(str(value), bbox_plain)

            review_fields.append({
                "field_name": field_name,
                "extracted_value": value,
                "confidence": conf,
                "source": source,
                "verified_against_ocr": verified,
                "field_type": field_type,
                "category": category,
                "ocr_snippet": ocr_snippet,
                "agreement_count": agreement_count,
                "all_sources": all_sources,
            })

        # Sort by confidence ascending (lowest first — most needs review)
        review_fields.sort(key=lambda f: f["confidence"])

        total = len(extracted)
        review_count = len(review_fields)
        review_rate = round(100.0 * review_count / total, 1) if total else 0.0

        return {
            "summary": {
                "total_fields": total,
                "fields_for_review": review_count,
                "review_threshold": self.review_threshold,
                "review_rate_percent": review_rate,
            },
            "fields": review_fields,
        }

    @staticmethod
    def _find_ocr_snippet(value: str, bbox_plain: str, context_chars: int = 40) -> str:
        """Extract ~80 chars of surrounding OCR text around a value match."""
        if not value or not bbox_plain:
            return ""
        val_lower = value.lower().strip()
        text_lower = bbox_plain.lower()
        idx = text_lower.find(val_lower)
        if idx < 0:
            # Try first significant word
            words = [w for w in val_lower.split() if len(w) > 2]
            for w in words:
                idx = text_lower.find(w)
                if idx >= 0:
                    break
        if idx < 0:
            return ""
        start = max(0, idx - context_chars)
        end = min(len(bbox_plain), idx + len(val_lower) + context_chars)
        snippet = bbox_plain[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(bbox_plain):
            snippet = snippet + "..."
        return snippet

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

            # --- OCR post-processing for specific field types ---
            # VIN: common OCR substitutions (I→1, O→0, S→5, Z→2 in digit positions)
            if "vinidentifier" in key_lower and len(str_val) >= 15:
                vin_fixed = self._fix_vin_ocr(str_val)
                normalised[key] = vin_fixed
                continue

            # Email: fix common OCR errors (space before @, missing dots, underscore for dot)
            if "email" in key_lower and "@" in str_val:
                str_val = re.sub(r"\s+@", "@", str_val)  # "adam @foo" -> "adam@foo"
                str_val = re.sub(r"@\s+", "@", str_val)  # "adam@ foo" -> "adam@foo"
                # Fix space/underscore before domain TLD: "humphreyinc com" → "humphreyinc.com"
                str_val = re.sub(r"[\s_](com|org|net|edu|gov|io)$", r".\1", str_val, flags=re.IGNORECASE)
                normalised[key] = str_val
                continue

            # Website URL: fix https:II → https://
            if "website" in key_lower and "https" in str_val.lower():
                str_val = re.sub(r"https?:II", "https://", str_val, flags=re.IGNORECASE)
                str_val = str_val.replace(" com", ".com").replace(" org", ".org").replace(" net", ".net")
                normalised[key] = str_val
                continue

            # FullName: fix semicolons from OCR (Downs; Bruce → Downs, Bruce)
            if "fullname" in key_lower:
                str_val = str_val.replace(";", ",")
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

        # Post-pass: strip date prefix "MM/DD/" from non-date numeric fields
        # e.g. "02/19/150" → "150" for HiredCostAmount, VehicleCount, etc.
        # Also handles "02/20/2026" → "2026" when field expects a simple number
        date_prefix_re = re.compile(r"^(\d{1,2}/\d{1,2}/)(\d+\.?\d*)$")
        for key, value in list(normalised.items()):
            kl = key.lower()
            if "date" in kl or "time" in kl:
                continue  # Skip actual date/time fields
            sv = str(value).strip()
            m = date_prefix_re.match(sv)
            if m:
                normalised[key] = m.group(2)
            else:
                # Also strip state prefix + date: "WI 02/20/150" → "150"
                m2 = re.match(r"^[A-Z]{2}\s+\d{1,2}/\d{1,2}/(\d+\.?\d*)$", sv)
                if m2:
                    normalised[key] = m2.group(1)

        # Post-pass: validate StateOrProvinceCode fields against real US/CA codes
        _VALID_STATE_CODES = {
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
            "DC", "PR", "VI", "GU", "AS", "MP",  # US territories
            "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE",
            "QC", "SK", "YT",  # Canadian provinces
        }
        for key, value in list(normalised.items()):
            if "stateorprovincecode" in key.lower():
                sv = str(value).strip()
                # Keep only valid 2-letter state/province codes
                if sv.upper() not in _VALID_STATE_CODES:
                    del normalised[key]

        # Post-pass: remove "From GT:" debug text from extracted values
        for key, value in list(normalised.items()):
            if isinstance(value, str) and value.startswith("From GT:"):
                del normalised[key]

        # Post-pass: clean single-letter fields with leading pipe/I noise
        # "IN" → "N", "|N" → "N", "In" → "N" for short text fields
        for key, value in list(normalised.items()):
            sv = str(value).strip()
            if len(sv) == 2 and sv[0] in ("I", "|", "i") and sv[1] in ("N", "n", "Y", "y"):
                normalised[key] = sv[1].upper()
            elif len(sv) == 3 and sv.startswith("In "):
                normalised[key] = "N"

        # Post-pass: convert "true"/"false" to "Y"/"N" for non-checkbox text fields
        # that are likely Y/N flag fields (not indicators, not checkboxes)
        for key, value in list(normalised.items()):
            kl = key.lower()
            if key in checkbox_fields or "indicator" in kl or kl.startswith("chk"):
                continue  # Skip actual checkboxes
            sv = str(value).strip().lower()
            if sv in ("true", "false"):
                # Check if schema says this is a text field (not checkbox/radio)
                finfo = schema.fields.get(key) if schema else None
                if finfo and finfo.field_type == "text":
                    normalised[key] = "Y" if sv == "true" else "N"

        # Post-pass: strip label prefix from values (e.g. "FEIN OR SOC SEC #" for NAICSCode)
        for key, value in list(normalised.items()):
            sv = str(value).strip()
            if re.match(r'^[A-Z][A-Z\s#$&/]+$', sv) and len(sv) > 10:
                # All-caps label text with special chars — likely a form label, not a value
                # Only remove if field expects numeric-like content
                kl = key.lower()
                if any(x in kl for x in ("naicscode", "siccode", "naiscode")):
                    del normalised[key]

        # Post-pass: strip trailing "%" from percent/use fields
        # e.g. "80%" → "80" for Driver_Vehicle_UsePercent_*
        for key, value in list(normalised.items()):
            kl = key.lower()
            if "percent" in kl or "usepercent" in kl or "rate" in kl:
                sv = str(value).strip()
                if sv.endswith("%"):
                    normalised[key] = sv[:-1].strip()

        # Post-pass: fix street/city field boundary bleed
        # Pattern: city field contains "street_text CityName" → extract just city
        # Pattern: street field ends with city name appended without separator
        for key, value in list(normalised.items()):
            kl = key.lower()
            sv = str(value).strip()
            if "cityname" in kl or ("city" in kl and "address" not in kl):
                # If city value looks like "1234 Street Name CityName", extract last word(s)
                # Check if value starts with a number (street address pattern)
                if re.match(r'^\d+\s+\w', sv):
                    # Contains a street address — try to extract city from end
                    # Look for common city patterns: word(s) after the last recognizable street element
                    parts = sv.split()
                    if len(parts) >= 3:
                        # Heuristic: if last 1-2 words are alpha-only (no numbers), that's the city
                        city_parts = []
                        for p in reversed(parts):
                            if p.isalpha():
                                city_parts.insert(0, p)
                            else:
                                break
                        if city_parts and len(city_parts) <= 3:
                            normalised[key] = " ".join(city_parts)

        # Post-pass: fix OtherSymbolCode fields that default to "1" incorrectly
        # When a symbol code field has value "1" but is adjacent to checkbox "1" values,
        # the LLM may be reading the checkbox state instead of the actual symbol number
        # We can't easily fix this without spatial data, but we can flag suspicious values

        # Post-pass: use schema default_value for sequential row-number fields
        # (e.g. Driver_ProducerIdentifier_A default "1", _B default "2", etc.)
        # When the extracted value doesn't look like a valid row number, use the default.
        if schema:
            for key, value in list(normalised.items()):
                finfo = schema.fields.get(key)
                if not finfo or not finfo.default_value:
                    continue
                expected_default = str(finfo.default_value)
                # Only apply to simple numeric defaults (sequential row numbers)
                if not expected_default.isdigit() or int(expected_default) > 20:
                    continue
                sv = str(value).strip()
                if sv == expected_default:
                    continue
                # If extracted value is non-numeric garbage, use default
                if not sv.replace(".", "").isdigit():
                    normalised[key] = expected_default
                    continue
                # For ProducerIdentifier fields, the value should be close to
                # the expected sequential number (1-20). If the extracted number
                # is way off (e.g. "31" when expecting "2"), use the default.
                if "produceridentifier" in key.lower():
                    try:
                        extracted_num = int(sv)
                        expected_num = int(expected_default)
                        if extracted_num > 20 or abs(extracted_num - expected_num) > 3:
                            normalised[key] = expected_default
                    except ValueError:
                        normalised[key] = expected_default
                elif len(sv) > len(expected_default) + 2:
                    normalised[key] = expected_default

        # Post-pass: Tooltip/instruction text filtering (Task #12)
        # Detect extracted values that are actually form instructions/tooltips
        # e.g. "Enter Y for Yes or N for No" instead of actual "Y" or "N"
        _INSTRUCTION_PATTERNS = [
            re.compile(r"^enter\s+", re.IGNORECASE),                      # "Enter Y for..."
            re.compile(r"^type\s+or\s+print", re.IGNORECASE),            # "Type or print..."
            re.compile(r"^if\s+(yes|applicable|any)", re.IGNORECASE),     # "If yes, explain..."
            re.compile(r"^please\s+(enter|provide|list)", re.IGNORECASE), # "Please enter..."
            re.compile(r"^check\s+(if|box|all)", re.IGNORECASE),          # "Check if applicable"
            re.compile(r"^see\s+(attached|page|reverse)", re.IGNORECASE), # "See attached..."
            re.compile(r"^complete\s+(if|this|section)", re.IGNORECASE),  # "Complete if..."
            re.compile(r"^describe\s+(the|any|all)", re.IGNORECASE),      # "Describe the..."
            re.compile(r"^attach\s+(a|additional|copy)", re.IGNORECASE),  # "Attach a copy..."
            re.compile(r"^list\s+(all|each|the)", re.IGNORECASE),         # "List all..."
            re.compile(r"^\(?\s*mm\s*/\s*dd\s*/\s*yyyy\s*\)?$", re.IGNORECASE),  # "(MM/DD/YYYY)"
            re.compile(r"^\(?\s*hh\s*:?\s*mm\s*\)?$", re.IGNORECASE),    # "(HH:MM)"
        ]
        for key, value in list(normalised.items()):
            sv = str(value).strip()
            if len(sv) < 8:
                continue  # Short values are unlikely to be instructions
            for pat in _INSTRUCTION_PATTERNS:
                if pat.search(sv):
                    del normalised[key]
                    break

        # Post-pass: Expanded value format normalization (Task #13)
        # Split combined limits like "1000000/2000000" into separate fields
        # Strip ACV suffix, dollar signs from non-amount fields, stray punctuation
        for key, value in list(normalised.items()):
            kl = key.lower()
            sv = str(value).strip()

            # Strip "ACV" or "Actual Cash Value" suffix from limit/deductible fields
            if any(x in kl for x in ("limit", "deductible", "amount")) and "count" not in kl:
                sv_clean = re.sub(r"\s*\(?ACV\)?\s*$", "", sv, flags=re.IGNORECASE)
                sv_clean = re.sub(r"\s*Actual\s+Cash\s+Value\s*$", "", sv_clean, flags=re.IGNORECASE)
                if sv_clean != sv:
                    normalised[key] = sv_clean.strip()

            # Strip stray dollar sign from non-amount text fields
            if "amount" not in kl and "limit" not in kl and "premium" not in kl and "deductible" not in kl:
                if sv.startswith("$"):
                    normalised[key] = sv[1:].strip()

            # Strip "per occurrence" / "per accident" suffixes from limit fields
            if any(x in kl for x in ("limit", "deductible")):
                sv2 = str(normalised.get(key, sv))
                sv2_clean = re.sub(
                    r"\s*\(?\s*per\s+(occurrence|accident|person|claim)\s*\)?\s*$",
                    "", sv2, flags=re.IGNORECASE,
                )
                if sv2_clean != sv2:
                    normalised[key] = sv2_clean.strip()

        # Post-pass: Cross-section plausibility validation (Task #14)
        # Catch implausible values from cross-section bleed (wrong row/column data)
        current_year = 2026  # Avoid import overhead
        for key, value in list(normalised.items()):
            kl = key.lower()
            sv = str(value).strip()

            # Vehicle ModelYear: must be 4 digits, 1950-current_year+2
            if "modelyear" in kl or ("vehicle" in kl and "year" in kl):
                digits = re.sub(r"[^\d]", "", sv)
                if digits and len(digits) == 4:
                    yr = int(digits)
                    if yr < 1950 or yr > current_year + 2:
                        del normalised[key]  # Implausible year — remove
                elif digits and len(digits) != 4:
                    del normalised[key]  # Not a valid year format

            # PostalCode: must be 5 or 9 digits (US) or A1A 1A1 (CA)
            if "postalcode" in kl:
                digits = re.sub(r"[^\d]", "", sv)
                # Allow 5-digit ZIP, 9-digit ZIP+4, or Canadian postal code
                if digits and len(digits) not in (5, 9):
                    # Check for Canadian format
                    if not re.match(r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$', sv, re.IGNORECASE):
                        # Not a valid postal code format — if it's numeric garbage, remove
                        if len(digits) < 5 and digits:
                            del normalised[key]

            # UsePercent: must be 0-100
            if "usepercent" in kl or ("percent" in kl and "use" in kl):
                try:
                    pct = float(sv)
                    if pct < 0 or pct > 100:
                        del normalised[key]
                except ValueError:
                    pass

            # NAIC code: exactly 5 digits
            if "naic" in kl and "code" not in kl:
                # naic field directly
                digits = re.sub(r"[^\d]", "", sv)
                if digits and len(digits) != 5:
                    del normalised[key]

            # Phone: must be 10 or 11 digits
            if any(x in kl for x in ("phone", "fax", "telephone")):
                digits = re.sub(r"[^\d]", "", sv)
                if digits and len(digits) not in (0, 7, 10, 11):
                    # Could be a date or other junk bleeding into phone field
                    if len(digits) < 7:
                        del normalised[key]

        # Post-pass: Positional boundary enforcement for text fields (Task #16)
        # Use schema field positions to detect values that are too long for their
        # widget width — indicating bleed from adjacent fields.
        if schema:
            for key, value in list(normalised.items()):
                finfo = schema.fields.get(key)
                if not finfo or finfo.field_type in ("checkbox", "radio"):
                    continue
                if finfo.x_min is None or finfo.x_max is None:
                    continue
                sv = str(value).strip()
                if not sv:
                    continue
                # Estimate expected max chars from field widget width
                # Typical form field: ~7 pixels per character at 150 DPI
                field_width = finfo.x_max - finfo.x_min
                if field_width <= 0:
                    continue
                estimated_max_chars = int(field_width / 6)  # ~6px per char
                if estimated_max_chars < 5:
                    estimated_max_chars = 5  # Minimum reasonable
                # If value is > 2x expected width, likely contains bleed
                if len(sv) > estimated_max_chars * 2 and len(sv) > 30:
                    kl = key.lower()
                    # Don't trim address/remarks/description fields (naturally long)
                    if any(x in kl for x in ("address", "remark", "description", "lineone",
                                              "linetwo", "fullname", "explanation")):
                        continue
                    # For state codes, take only first 2 chars
                    if "stateorprovincecode" in kl and len(sv) > 2:
                        parts = sv.split()
                        if parts and len(parts[0]) == 2 and parts[0].isalpha():
                            normalised[key] = parts[0].upper()
                            continue
                    # For short-code fields (Y/N, single char), take first char
                    if any(x in kl for x in ("code", "type")) and len(sv) > 10:
                        # Don't trim NAIC codes (5 digits) or policy numbers
                        if "naic" not in kl and "policy" not in kl and "number" not in kl:
                            first_word = sv.split()[0] if sv.split() else sv
                            if len(first_word) <= 5:
                                normalised[key] = first_word

        return normalised

    @staticmethod
    def _fix_vin_ocr(vin: str) -> str:
        """Fix common OCR character substitutions in VINs.
        VINs use digits + uppercase letters but never I, O, Q.
        """
        vin = vin.upper().strip()
        # VIN positions 1-3: WMI (letters+digits), 4-8: VDS, 9: check digit, 10-17: VIS
        # Common OCR confusions in VINs:
        result = []
        for i, c in enumerate(vin):
            if c == 'I':
                result.append('1')  # I→1 (VINs never use I)
            elif c == 'O':
                result.append('0')  # O→0 (VINs never use O)
            elif c == 'Q':
                result.append('0')  # Q→0 (VINs never use Q)
            else:
                result.append(c)
        return "".join(result)

    @staticmethod
    def _normalise_date_str(s: str) -> Optional[str]:
        """Try to parse date and return MM/DD/YYYY; else None."""
        from datetime import datetime
        s = s.strip()
        # Strip common noise: state prefix (e.g. "NC "), trailing Y/N flags, pipe chars
        s_clean = re.sub(r'^[A-Z]{1,2}\s+', '', s)  # "NC 04/01/2022" → "04/01/2022"
        s_clean = re.sub(r'\s*[|/\[\]]+\s*[YNyn]?\s*$', '', s_clean)  # trailing " | N"
        s_clean = re.sub(r'\s*[YNyn]\s*$', '', s_clean)  # trailing " N" or "Y"
        # Fix OCR: leading J/)/1/2 that should be 0 in month (J4 → 04, )2 → 02, 13 → 03)
        m_ocr = re.match(r'^([J)\]]?)(\d)[/\-](\d{1,2})[/\-](\d{4})', s_clean)
        if m_ocr and m_ocr.group(1):
            s_clean = f"0{m_ocr.group(2)}/{m_ocr.group(3)}/{m_ocr.group(4)}"
        # Fix OCR: leading digit that doubled the month (13 → 03, 18 → 08, 25 → 05)
        m_dbl = re.match(r'^(\d)(\d)[/\-](\d{1,2})[/\-](\d{4})', s_clean)
        if m_dbl:
            first, second = int(m_dbl.group(1)), int(m_dbl.group(2))
            candidate_mo = first * 10 + second
            if candidate_mo > 12 and 1 <= second <= 9:
                # The first digit is noise — try "0{second}" as month
                s_clean = f"0{second}/{m_dbl.group(3)}/{m_dbl.group(4)}"
        # Fix OCR: trailing E/C/: in year (201E → 2018? — can't know, just try 4 digits)
        s_clean = re.sub(r'(\d{3})[ECec:;()\[\]]+\s*$', r'\g<1>0', s_clean)

        for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y", "%m/%d/%y"):
            try:
                dt = datetime.strptime(s_clean, fmt)
                return dt.strftime("%m/%d/%Y")
            except ValueError:
                continue
        m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", s_clean)
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
                few_shot = self._get_knowledge_context(form_type, batch_cats[0], chunk_fields)
                if self.rag_store is not None:
                    few_shot += self.rag_store.retrieve(form_type, batch_cats[0], chunk_fields, k=3)

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

    # ==================================================================
    # VLM Cropped Extract (--vlm-crop-extract)
    # ==================================================================

    def _vlm_crop_extract_pass(
        self,
        form_type: str,
        schema,
        image_paths: List[Path],
        extracted: Dict[str, Any],
        field_sources: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Multi-stage cropped VLM extraction.

        Groups remaining fields by spatial proximity using schema positions,
        crops image regions, and sends focused crops + field lists to VLM
        for higher-detail extraction.
        """
        result: Dict[str, Any] = {}
        all_field_names = set(schema.fields.keys())
        remaining = [n for n in all_field_names if n not in extracted]
        if not remaining:
            return result

        paths = [Path(p) for p in image_paths if Path(p).exists()]
        if not paths:
            return result

        try:
            import cv2
            import numpy as np
        except ImportError:
            print("    [VLM-CROP] cv2/numpy not available, skipping")
            return result

        num_pages = len(paths)
        tooltips_all = self.registry.get_tooltips(form_type, list(all_field_names))

        # Build checkbox set for normalisation
        checkbox_field_set = set()
        for fname, finfo in schema.fields.items():
            if finfo.field_type in ("checkbox", "radio"):
                checkbox_field_set.add(fname)

        # Group remaining fields by page, using schema positions
        positioned_by_page: Dict[int, List] = {}
        unpositioned: List[str] = []

        for fname in remaining:
            fi = schema.fields.get(fname)
            if fi and fi.page is not None and fi.x_min is not None:
                page_idx = fi.page
                if page_idx not in positioned_by_page:
                    positioned_by_page[page_idx] = []
                positioned_by_page[page_idx].append(fi)
            else:
                unpositioned.append(fname)

        vlm_calls = 0
        CROP_PADDING = 50  # pixels padding around crop region
        MAX_FIELDS_PER_CROP = 20

        for page_idx in sorted(positioned_by_page.keys()):
            page_fields = positioned_by_page[page_idx]
            if not page_fields or page_idx >= len(paths):
                continue

            image_path = paths[page_idx]
            img = cv2.imread(str(image_path))
            if img is None:
                continue
            img_h, img_w = img.shape[:2]

            # Simple grid-based clustering: divide page into horizontal bands
            # Sort fields by Y position and group into clusters
            page_fields.sort(key=lambda fi: (fi.y_min or 0))

            clusters: List[List] = []
            current_cluster: List = []
            last_y_max = 0

            for fi in page_fields:
                y_min = fi.y_min or 0
                if current_cluster and y_min - last_y_max > 100:
                    clusters.append(current_cluster)
                    current_cluster = []
                current_cluster.append(fi)
                last_y_max = max(last_y_max, fi.y_max or y_min + 30)

            if current_cluster:
                clusters.append(current_cluster)

            # Sub-divide large clusters
            final_clusters = []
            for cluster in clusters:
                if len(cluster) <= MAX_FIELDS_PER_CROP:
                    final_clusters.append(cluster)
                else:
                    for i in range(0, len(cluster), MAX_FIELDS_PER_CROP):
                        final_clusters.append(cluster[i:i + MAX_FIELDS_PER_CROP])

            for cluster in final_clusters:
                field_names = [fi.name for fi in cluster]

                # Compute crop region (union of field bboxes + padding)
                x_min = max(0, min(fi.x_min for fi in cluster) - CROP_PADDING)
                y_min = max(0, min(fi.y_min for fi in cluster) - CROP_PADDING)
                x_max = min(img_w, max(fi.x_max for fi in cluster) + CROP_PADDING)
                y_max = min(img_h, max(fi.y_max for fi in cluster) + CROP_PADDING)

                # Crop image
                crop = img[int(y_min):int(y_max), int(x_min):int(x_max)]
                if crop.size == 0:
                    continue

                # Save crop temporarily
                crop_path = paths[page_idx].parent / f"crop_p{page_idx}_{vlm_calls}.png"
                cv2.imwrite(str(crop_path), crop)

                # Build prompt for this crop
                chunk_tooltips = {k: v for k, v in tooltips_all.items() if k in field_names}
                prompt = build_vlm_extract_prompt(
                    form_type=form_type,
                    categories=list(set(fi.category for fi in cluster if fi.category)),
                    field_names=field_names,
                    tooltips=chunk_tooltips,
                    page_number=page_idx + 1,
                    total_pages=num_pages,
                )

                try:
                    response = self.llm.generate_vlm_extract(
                        prompt, crop_path, max_tokens=4096,
                    )
                    vlm_calls += 1
                    batch_result = self.llm.parse_json(response)
                    for k, v in batch_result.items():
                        if v is None or (isinstance(v, str) and not v.strip()):
                            continue
                        canonical = self._match_vlm_key(k, field_names)
                        if canonical:
                            if canonical in checkbox_field_set:
                                result[canonical] = self._normalise_checkbox_value(v)
                            else:
                                result[canonical] = v
                except VisionModelNotFoundError:
                    raise
                except Exception as e:
                    print(f"    [VLM-CROP] Crop error (page {page_idx + 1}): {e}")

                # Clean up temp crop
                try:
                    crop_path.unlink(missing_ok=True)
                except Exception:
                    pass

        print(f"    [VLM-CROP] {vlm_calls} VLM calls, {len(result)} fields extracted")
        return result

    # ==================================================================
    # Multimodal Extraction (--multimodal: image + OCR text → VLM)
    # ==================================================================

    def _multimodal_extract_pass(
        self,
        form_type: str,
        schema,
        image_paths: List[Path],
        extracted: Dict[str, Any],
        field_sources: Dict[str, str],
        CAT_PAGES: Dict[str, List[int]],
        page_bbox_text: List[str],
        page_docling: List[str],
        table_markdown: str = "",
    ) -> Dict[str, Any]:
        """
        Multimodal extraction: sends BOTH page image AND OCR text to VLM.

        The VLM can cross-reference what it sees in the image with the OCR text,
        catching errors in both. Higher accuracy than VLM-only or text-only.

        Uses same batching and parallelism as _vlm_extract_pass.
        """
        VLM_BATCH_SIZE = 25
        result: Dict[str, Any] = {}
        all_field_names = set(schema.fields.keys())
        remaining = [n for n in all_field_names if n not in extracted]
        if not remaining:
            return result

        paths = [Path(p) for p in image_paths if Path(p).exists()]
        if not paths:
            return result

        num_pages = len(paths)
        tooltips_all = self.registry.get_tooltips(form_type, list(all_field_names))

        checkbox_field_set = set()
        for fname, finfo in schema.fields.items():
            if finfo.field_type in ("checkbox", "radio"):
                checkbox_field_set.add(fname)

        # Group remaining fields by page
        fields_by_page: Dict[int, List[str]] = {}
        for fname in remaining:
            fi = schema.fields.get(fname)
            if fi and fi.page is not None and fi.page < num_pages:
                page_idx = fi.page
            else:
                cat = fi.category if fi else None
                if cat and cat in CAT_PAGES:
                    page_idx = CAT_PAGES[cat][0]
                else:
                    page_idx = 0
            if page_idx not in fields_by_page:
                fields_by_page[page_idx] = []
            fields_by_page[page_idx].append(fname)

        # Collect all VLM tasks (prompt, image_path, field_names, label)
        vlm_tasks: List[tuple] = []

        for page_idx in sorted(fields_by_page.keys()):
            page_fields = fields_by_page[page_idx]
            if not page_fields:
                continue

            image_path = paths[page_idx] if page_idx < len(paths) else paths[0]

            # Build OCR context for this page
            ocr_text_parts = []
            if page_idx < len(page_docling) and page_docling[page_idx]:
                ocr_text_parts.append(page_docling[page_idx])
            if page_idx < len(page_bbox_text) and page_bbox_text[page_idx]:
                ocr_text_parts.append(page_bbox_text[page_idx])
            ocr_text = "\n\n".join(ocr_text_parts)

            # Group by category batch, then chunk
            from schema_registry import CATEGORY_BATCHES
            batch_groups: Dict[int, List[str]] = {}
            unbatched: List[str] = []
            for fname in page_fields:
                fi = schema.fields.get(fname)
                cat = fi.category if fi else None
                placed = False
                if cat:
                    for bi, batch_cats in enumerate(CATEGORY_BATCHES):
                        if cat in batch_cats:
                            if bi not in batch_groups:
                                batch_groups[bi] = []
                            batch_groups[bi].append(fname)
                            placed = True
                            break
                if not placed:
                    unbatched.append(fname)

            if unbatched:
                max_bi = max(batch_groups.keys()) if batch_groups else 0
                if max_bi not in batch_groups:
                    batch_groups[max_bi] = []
                batch_groups[max_bi].extend(unbatched)

            for bi in sorted(batch_groups.keys()):
                group_fields = batch_groups[bi]
                cats_in_group = set()
                for fname in group_fields:
                    fi = schema.fields.get(fname)
                    if fi and fi.category:
                        cats_in_group.add(fi.category)
                cats_list = sorted(cats_in_group)

                for ci in range(0, len(group_fields), VLM_BATCH_SIZE):
                    chunk = group_fields[ci:ci + VLM_BATCH_SIZE]
                    chunk_tooltips = {k: v for k, v in tooltips_all.items() if k in chunk}
                    prompt = build_multimodal_extract_prompt(
                        form_type=form_type,
                        categories=cats_list,
                        field_names=chunk,
                        tooltips=chunk_tooltips,
                        ocr_text=ocr_text,
                        table_markdown=table_markdown,
                        page_number=page_idx + 1,
                        total_pages=num_pages,
                    )
                    vlm_tasks.append((prompt, image_path, chunk, f"MM p{page_idx+1}"))

        if not vlm_tasks:
            return result

        # Execute — parallel or sequential (reuse _exec_vlm_task)
        mode = "parallel" if self.parallel_vlm and len(vlm_tasks) > 1 else "sequential"
        print(f"    [MULTIMODAL] {len(vlm_tasks)} VLM tasks ({mode})")

        if self.parallel_vlm and len(vlm_tasks) > 1:
            workers = min(self.vlm_max_workers, len(vlm_tasks))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(
                        self._exec_vlm_task, prompt, img_path, fields, checkbox_field_set, label
                    ): label
                    for prompt, img_path, fields, label in vlm_tasks
                }
                for future in as_completed(futures):
                    task_result, is_404 = future.result()
                    if is_404:
                        for f in futures:
                            f.cancel()
                        raise VisionModelNotFoundError(self.llm.vlm_extract_model or "?")
                    result.update(task_result)
        else:
            for prompt, img_path, fields, label in vlm_tasks:
                task_result, is_404 = self._exec_vlm_task(
                    prompt, img_path, fields, checkbox_field_set, label
                )
                if is_404:
                    raise VisionModelNotFoundError(self.llm.vlm_extract_model or "?")
                result.update(task_result)

        print(f"    [MULTIMODAL] {len(vlm_tasks)} VLM calls, {len(result)} fields extracted")
        return result

    # ==================================================================
    # Checkbox Crop Extraction (--checkbox-crops) — Grid Montage Batched
    # ==================================================================

    def _checkbox_crop_pass(
        self,
        form_type: str,
        schema,
        image_paths: List[Path],
    ) -> Dict[str, Any]:
        """
        Crop tight regions around checkbox fields, enhance contrast, assemble
        into numbered grid montages, and send batched VLM calls.

        Instead of 1 VLM call per checkbox (slow), this creates NxN grids of
        checkbox crops with numbered labels and classifies all at once.
        164 checkboxes → ~11 grid VLM calls (16 per grid).

        Requires positional atlas data (fields with known page coordinates).
        Uses parallel VLM calls when enabled.
        """
        import tempfile
        try:
            import cv2
            import numpy as np
        except ImportError:
            print("    [CB-CROP] cv2 not available, skipping checkbox crops")
            return {}

        result: Dict[str, Any] = {}
        positioned = schema.get_positioned_fields()
        if not positioned:
            print("    [CB-CROP] No positioned fields in schema, skipping")
            return result

        paths = [Path(p) for p in image_paths if Path(p).exists()]
        if not paths:
            return result

        # Collect checkbox fields with positions
        checkbox_fields = []
        for fi in positioned:
            if fi.field_type not in ("checkbox", "radio"):
                continue
            if fi.page >= len(paths):
                continue
            checkbox_fields.append(fi)

        if not checkbox_fields:
            print("    [CB-CROP] No positioned checkbox fields found")
            return result

        # Grid montage parameters
        GRID_COLS = 4
        GRID_BATCH = 8   # checkboxes per grid (2x4) — smaller for reliable VLM parsing
        PADDING = 20     # pixels around checkbox crop
        CROP_SIZE = 160  # each crop cell size
        LABEL_H = 24     # height for number label above crop
        CELL_W = CROP_SIZE + 4   # cell width (crop + 2px border each side)
        CELL_H = CROP_SIZE + LABEL_H + 4  # cell height (label + crop + border)

        # Crop and enhance all checkboxes
        crops_data: List[tuple] = []  # (fi.name, enhanced_crop_array)
        page_images = {}  # cache loaded page images

        for fi in checkbox_fields:
            if fi.page not in page_images:
                img = cv2.imread(str(paths[fi.page]))
                if img is None:
                    continue
                page_images[fi.page] = img
            img = page_images[fi.page]
            img_h, img_w = img.shape[:2]

            x1 = max(0, int(fi.x_min) - PADDING)
            y1 = max(0, int(fi.y_min) - PADDING)
            x2 = min(img_w, int(fi.x_max) + PADDING)
            y2 = min(img_h, int(fi.y_max) + PADDING)
            if x2 <= x1 or y2 <= y1:
                continue

            crop = img[y1:y2, x1:x2]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
            enhanced = clahe.apply(gray)
            resized = cv2.resize(enhanced, (CROP_SIZE, CROP_SIZE), interpolation=cv2.INTER_CUBIC)
            crops_data.append((fi.name, resized))

        if not crops_data:
            return result

        # Build grid montages in batches of GRID_BATCH
        import math
        temp_files: List[Path] = []
        vlm_tasks: List[tuple] = []  # (prompt, grid_path, field_map)

        for batch_start in range(0, len(crops_data), GRID_BATCH):
            batch = crops_data[batch_start:batch_start + GRID_BATCH]
            n_rows = math.ceil(len(batch) / GRID_COLS)
            grid_w = GRID_COLS * CELL_W
            grid_h = n_rows * CELL_H

            # White background
            grid = np.ones((grid_h, grid_w), dtype=np.uint8) * 255
            field_map = {}  # {number: field_name}
            batch_field_names = []

            for i, (field_name, crop_img) in enumerate(batch):
                num = i + 1
                row = i // GRID_COLS
                col = i % GRID_COLS
                x_off = col * CELL_W + 2
                y_off = row * CELL_H

                # Draw number label
                cv2.putText(
                    grid, str(num),
                    (x_off + 4, y_off + LABEL_H - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, 0, 2,
                )
                # Place crop below label
                cy = y_off + LABEL_H + 2
                grid[cy:cy + CROP_SIZE, x_off:x_off + CROP_SIZE] = crop_img

                field_map[num] = field_name
                batch_field_names.append(field_name)

            # Save grid to temp file
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            cv2.imwrite(tmp.name, grid)
            grid_path = Path(tmp.name)
            temp_files.append(grid_path)

            prompt = build_checkbox_grid_prompt(field_map)
            vlm_tasks.append((prompt, grid_path, field_map, batch_field_names))

        n_grids = len(vlm_tasks)
        mode = "parallel" if self.parallel_vlm and n_grids > 1 else "sequential"
        print(f"    [CB-CROP] {len(crops_data)} checkboxes in {n_grids} grid montages ({mode})")

        checkbox_field_set = {name for name, _ in crops_data}

        def _exec_grid_vlm(prompt, grid_path, field_map, batch_fields, label=""):
            """Execute one grid VLM call. Thread-safe."""
            try:
                response = self.llm.generate_vlm_extract(
                    prompt, grid_path, max_tokens=4096,
                )
                batch_result = self.llm.parse_json(response)
                parsed = {}
                for k, v in batch_result.items():
                    if v is None:
                        continue
                    # Match key to field name (VLM may return number or field name)
                    canonical = None
                    if k in checkbox_field_set:
                        canonical = k
                    else:
                        # Try matching by number
                        try:
                            num = int(k)
                            canonical = field_map.get(num)
                        except (ValueError, TypeError):
                            canonical = self._match_vlm_key(k, batch_fields)
                    if canonical:
                        parsed[canonical] = self._normalise_checkbox_value(v)
                return parsed, False
            except VisionModelNotFoundError:
                return {}, True
            except Exception as e:
                print(f"    [CB-CROP] Grid {label} error: {e}")
                return {}, False

        # Execute grids with retry + individual fallback for failed grids
        failed_grids: List[tuple] = []  # (field_map, batch_fields) for grids that returned empty

        if self.parallel_vlm and n_grids > 1:
            workers = min(self.vlm_max_workers, n_grids)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(
                        _exec_grid_vlm, prompt, gpath, fmap, bfields, f"grid-{idx+1}"
                    ): (idx, fmap, bfields)
                    for idx, (prompt, gpath, fmap, bfields) in enumerate(vlm_tasks)
                }
                for future in as_completed(futures):
                    idx, fmap, bfields = futures[future]
                    grid_result, is_404 = future.result()
                    if is_404:
                        for f in futures:
                            f.cancel()
                        for tf in temp_files:
                            try:
                                tf.unlink(missing_ok=True)
                            except Exception:
                                pass
                        raise VisionModelNotFoundError(self.llm.vlm_extract_model or "?")
                    if grid_result:
                        result.update(grid_result)
                    else:
                        failed_grids.append((fmap, bfields))
        else:
            for idx, (prompt, gpath, fmap, bfields) in enumerate(vlm_tasks):
                grid_result, is_404 = _exec_grid_vlm(
                    prompt, gpath, fmap, bfields, f"grid-{idx+1}"
                )
                if is_404:
                    for tf in temp_files:
                        try:
                            tf.unlink(missing_ok=True)
                        except Exception:
                            pass
                    raise VisionModelNotFoundError(self.llm.vlm_extract_model or "?")
                if grid_result:
                    result.update(grid_result)
                else:
                    failed_grids.append((fmap, bfields))

        # Fallback: individually classify checkboxes from failed grids
        if failed_grids:
            n_fallback = sum(len(fmap) for fmap, _ in failed_grids)
            print(f"    [CB-CROP] {len(failed_grids)} grids failed, falling back to individual crops for {n_fallback} checkboxes")

            # Build name→crop lookup from crops_data
            crop_lookup = {name: crop_img for name, crop_img in crops_data}
            fallback_tasks = []
            fallback_temps = []

            for fmap, bfields in failed_grids:
                for num, fname in fmap.items():
                    if fname in crop_lookup:
                        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                        cv2.imwrite(tmp.name, crop_lookup[fname])
                        crop_path = Path(tmp.name)
                        fallback_temps.append(crop_path)
                        tooltip = self.registry.get_tooltips(form_type, [fname]).get(fname, "")
                        prompt = build_checkbox_crop_prompt(fname, tooltip)
                        fallback_tasks.append((prompt, crop_path, [fname], f"FB {fname}"))

            if fallback_tasks:
                if self.parallel_vlm and len(fallback_tasks) > 1:
                    workers = min(self.vlm_max_workers, len(fallback_tasks))
                    with ThreadPoolExecutor(max_workers=workers) as pool:
                        fb_futures = {
                            pool.submit(
                                self._exec_vlm_task, prompt, img_path, fields, checkbox_field_set, label
                            ): label
                            for prompt, img_path, fields, label in fallback_tasks
                        }
                        for future in as_completed(fb_futures):
                            task_result, is_404 = future.result()
                            if not is_404:
                                for k, v in task_result.items():
                                    result[k] = self._normalise_checkbox_value(v)
                else:
                    for prompt, img_path, fields, label in fallback_tasks:
                        task_result, is_404 = self._exec_vlm_task(
                            prompt, img_path, fields, checkbox_field_set, label
                        )
                        if not is_404:
                            for k, v in task_result.items():
                                result[k] = self._normalise_checkbox_value(v)

                for tf in fallback_temps:
                    try:
                        tf.unlink(missing_ok=True)
                    except Exception:
                        pass

            print(f"    [CB-CROP] Fallback recovered {n_fallback} → {len(result)} total checkboxes")

        # Clean up grid temp files
        for tf in temp_files:
            try:
                tf.unlink(missing_ok=True)
            except Exception:
                pass

        print(f"    [CB-CROP] {n_grids} grids + fallback, {len(result)} checkboxes classified")
        return result

    # ==================================================================
    # VLM-OCR Two-Stage Extraction (--glm-ocr / --nanonets-ocr)
    # ==================================================================

    def _vlm_ocr_two_stage_pass(
        self,
        form_type: str,
        schema,
        image_paths: List[Path],
        extracted: Dict[str, Any],
        field_sources: Dict[str, str],
        CAT_PAGES: Dict[str, List[int]],
        table_markdown: str = "",
    ) -> Dict[str, Any]:
        """
        Two-stage VLM-OCR extraction:
          Stage 1: Send page images to VLM-OCR (GLM-OCR or Nanonets-OCR) → structured text
          Stage 2: Feed structured text to text LLM with ACORD schema prompts → JSON

        Returns dict of {field_name: value}.
        """
        from vlm_ocr_engine import VLMOCREngine, NanonetsOutputParser

        result: Dict[str, Any] = {}

        # Determine backend
        if self.use_glm_ocr:
            backend = "glm-ocr"
        elif self.use_nanonets_ocr:
            backend = "nanonets-ocr"
        else:
            return result

        vlm_ocr = VLMOCREngine(
            llm_engine=self.llm,
            backend=backend,
            model=self.llm.vlm_ocr_model,
        )

        paths = [Path(p) for p in image_paths if Path(p).exists()]
        if not paths:
            return result

        # ---- Stage 1: VLM-OCR → structured text per page ----
        print(f"    [VLM-OCR] Stage 1: {backend} OCR on {len(paths)} pages ...")
        vlm_ocr_pages = vlm_ocr.ocr_pages(
            paths,
            parallel=self.parallel_vlm,
            max_workers=self.vlm_max_workers,
        )

        total_chars = sum(len(p) for p in vlm_ocr_pages)
        print(f"    [VLM-OCR] Stage 1 complete: {total_chars} chars across {len(vlm_ocr_pages)} pages")

        # If Nanonets, extract checkbox states directly from Unicode symbols
        nanonets_checkboxes: Dict[str, str] = {}
        if self.use_nanonets_ocr:
            for page_text in vlm_ocr_pages:
                cb_states = NanonetsOutputParser.extract_checkbox_states(page_text)
                nanonets_checkboxes.update(cb_states)
            # Convert checkbox symbols to text markers for the LLM
            vlm_ocr_pages = [
                NanonetsOutputParser.convert_checkboxes_to_text(p) for p in vlm_ocr_pages
            ]
            if nanonets_checkboxes:
                print(f"    [VLM-OCR] Nanonets found {len(nanonets_checkboxes)} checkbox states directly")

        # Unload VLM-OCR model before loading stage-2 text LLM
        self.llm.unload_vlm_ocr_model()
        cleanup_gpu_memory()

        # ---- Stage 2: Text LLM extraction from structured text ----
        print(f"    [VLM-OCR] Stage 2: Text LLM extraction from VLM-OCR text ...")

        all_field_names = set(schema.fields.keys())
        remaining = [n for n in all_field_names if n not in extracted]
        if not remaining:
            return result

        num_pages = len(paths)
        tooltips_all = self.registry.get_tooltips(form_type, list(all_field_names))

        # Group remaining fields by page
        fields_by_page: Dict[int, List[str]] = {}
        for fname in remaining:
            fi = schema.fields.get(fname)
            if fi and hasattr(fi, "page") and fi.page is not None and fi.page < num_pages:
                page_idx = fi.page
            else:
                cat = getattr(fi, "category", None) if fi else None
                if cat and cat in CAT_PAGES:
                    page_idx = CAT_PAGES[cat][0]
                else:
                    page_idx = 0
            if page_idx not in fields_by_page:
                fields_by_page[page_idx] = []
            fields_by_page[page_idx].append(fname)

        BATCH_SIZE = 50
        for page_idx in sorted(fields_by_page.keys()):
            page_fields = fields_by_page[page_idx]
            if not page_fields:
                continue

            ocr_text = vlm_ocr_pages[page_idx] if page_idx < len(vlm_ocr_pages) else ""
            if not ocr_text.strip():
                continue

            for i in range(0, len(page_fields), BATCH_SIZE):
                batch = page_fields[i:i + BATCH_SIZE]
                batch_tooltips = {k: v for k, v in tooltips_all.items() if k in batch}

                # Determine categories in this batch
                cats_in_batch: set = set()
                for fname in batch:
                    fi = schema.fields.get(fname)
                    cat = getattr(fi, "category", None) if fi else None
                    if cat:
                        cats_in_batch.add(cat)

                prompt = build_vlm_ocr_stage2_prompt(
                    form_type=form_type,
                    categories=sorted(cats_in_batch) if cats_in_batch else ["general"],
                    field_names=batch,
                    tooltips=batch_tooltips,
                    vlm_ocr_text=ocr_text,
                )

                # Use stage2_model if configured, else default model
                response = self.llm.generate_stage2(prompt)
                batch_result = self.llm.parse_json(response)

                for k, v in batch_result.items():
                    matched = self._match_vlm_key(k, batch)
                    if matched and v is not None and str(v).strip():
                        result[matched] = v

        # Merge Nanonets checkbox states (high confidence, from direct Unicode parsing)
        if nanonets_checkboxes:
            checkbox_field_set: set = set()
            for fname, finfo in schema.fields.items():
                ft = getattr(finfo, "field_type", None) or ""
                if ft in ("checkbox", "radio") or "indicator" in fname.lower():
                    checkbox_field_set.add(fname)

            for label, state in nanonets_checkboxes.items():
                matched_field = self._match_nanonets_checkbox(label, checkbox_field_set, schema)
                if matched_field and matched_field not in result:
                    result[matched_field] = state

        print(f"    [VLM-OCR] Stage 2 complete: {len(result)} fields extracted")
        return result

    def _match_nanonets_checkbox(
        self, label: str, checkbox_fields: set, schema
    ) -> Optional[str]:
        """Match a Nanonets checkbox label (e.g. 'Commercial General Liability')
        to a schema field name using tooltip and fuzzy matching."""
        label_norm = label.strip().lower()
        if not label_norm:
            return None

        # Try tooltip-based matching first
        for fname in checkbox_fields:
            fi = schema.fields.get(fname)
            tooltip = (getattr(fi, "tooltip", "") or "").lower() if fi else ""
            if tooltip and (label_norm in tooltip or tooltip in label_norm):
                return fname

        # Fuzzy field name matching
        import re as _re
        label_words = set(_re.findall(r'\w+', label_norm))
        if not label_words:
            return None
        for fname in checkbox_fields:
            fname_words = set(fname.lower().replace("_", " ").split())
            overlap = label_words & fname_words
            if len(overlap) >= 2 or (len(overlap) >= 1 and len(label_words) <= 2):
                return fname
        return None

    # ==================================================================
    # Dual-LLM Validation (--dual-llm-validate)
    # ==================================================================

    def _dual_llm_validate(
        self,
        extracted: Dict[str, Any],
        bbox_text: str,
        docling_text: str,
        schema,
    ) -> tuple:
        """
        Send extracted values + OCR context to a second LLM call for verification.

        Returns:
            (results, warnings) where:
            - results: {field: {"correct": bool, "suggested": value}}
            - warnings: list of warning strings for flagged fields
        """
        results: Dict[str, Dict[str, Any]] = {}
        warnings: List[str] = []

        if not extracted:
            return results, warnings

        # Batch fields for verification (50 at a time to stay within context)
        VERIFY_BATCH = 50
        field_items = list(extracted.items())

        # Limit OCR context for verification prompt
        ocr_context = bbox_text[:5000] if bbox_text else ""
        doc_context = docling_text[:5000] if docling_text else ""

        for i in range(0, len(field_items), VERIFY_BATCH):
            batch = field_items[i:i + VERIFY_BATCH]
            batch_dict = {k: v for k, v in batch}

            # Build verification prompt
            fields_json = "\n".join(f'  "{k}": "{v}"' for k, v in batch)

            prompt = f"""You are verifying extracted field values from an ACORD insurance form.

Given the OCR text below, check if each extracted value appears in or is consistent with the OCR text.
For each field, respond with:
- "correct": true if the value matches the OCR text
- "correct": false if the value seems wrong, with "suggested" containing the correct value from the OCR text
- If you cannot find the field in the OCR text, mark it as "correct": true (don't guess)

OCR TEXT (bbox rows):
{ocr_context}

DOCUMENT TEXT (docling):
{doc_context}

EXTRACTED VALUES TO VERIFY:
{{
{fields_json}
}}

Respond with ONLY a JSON object where keys are field names and values are objects with "correct" (boolean) and optionally "suggested" (string).
Example: {{"FieldName": {{"correct": false, "suggested": "correct value"}}}}"""

            try:
                response = self.llm.generate(prompt)
                verify_result = self.llm.parse_json(response)

                for k, info in verify_result.items():
                    if isinstance(info, dict):
                        results[k] = info
                        if not info.get("correct", True):
                            suggested = info.get("suggested", "")
                            warnings.append(
                                f"{k}: extracted='{extracted.get(k, '')}' -> "
                                f"suggested='{suggested}'"
                            )
            except Exception as e:
                print(f"    [DUAL-LLM] Batch verification error: {e}")

        return results, warnings
