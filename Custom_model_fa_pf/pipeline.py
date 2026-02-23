"""Pipeline orchestrator: email → classified LOBs → extracted entities → pre-filled PDFs."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from Custom_model_fa_pf.config import OUTPUT_DIR, SCHEMAS_DIR
from Custom_model_fa_pf import lob_classifier, entity_extractor, form_assigner, pdf_filler, gap_analyzer
from Custom_model_fa_pf import llm_field_mapper, form_reader
from Custom_model_fa_pf import validation_engine
from Custom_model_fa_pf.lob_classifier import LOBClassification
from Custom_model_fa_pf.entity_schema import CustomerSubmission
from Custom_model_fa_pf.form_assigner import FormAssignment
from Custom_model_fa_pf.gap_analyzer import GapReport
from Custom_model_fa_pf.validation_engine import ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    lobs: List[LOBClassification] = field(default_factory=list)
    entities: Optional[CustomerSubmission] = None
    assignments: List[FormAssignment] = field(default_factory=list)
    field_values: Dict[str, Dict[str, str]] = field(default_factory=dict)
    fill_results: list = field(default_factory=list)
    gap_report: Optional[GapReport] = None
    validation_results: Dict[str, ValidationResult] = field(default_factory=dict)
    output_dir: Optional[Path] = None

    def to_dict(self):
        return {
            "lobs": [l.to_dict() for l in self.lobs],
            "entities": self.entities.to_dict() if self.entities else {},
            "assignments": [a.to_dict() for a in self.assignments],
            "field_values": self.field_values,
            "fill_results": [r.to_dict() for r in self.fill_results],
            "gap_report": self.gap_report.to_dict() if self.gap_report else None,
            "validation_results": {k: v.to_dict() for k, v in self.validation_results.items()},
            "output_dir": str(self.output_dir) if self.output_dir else None,
        }


def run(
    email_text: str,
    output_dir: Optional[Path] = None,
    json_only: bool = False,
    show_gaps: bool = False,
    model: str = "qwen3:8b",
    ollama_url: str = "http://localhost:11434",
    confidence_threshold: float = 0.7,
    verbose: bool = False,
) -> PipelineResult:
    """Run the full form assignment & pre-filling pipeline.

    Args:
        email_text: Raw customer email/message text
        output_dir: Where to save results (auto-generated if None)
        json_only: If True, skip PDF filling
        show_gaps: If True, run gap analysis with LLM
        model: Ollama model name
        ollama_url: Ollama API URL
        confidence_threshold: Minimum LOB confidence
        verbose: Enable verbose logging

    Returns:
        PipelineResult with all outputs
    """
    result = PipelineResult()

    # Setup output directory
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_DIR / f"submission_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    result.output_dir = output_dir

    # Initialize LLM engine
    from llm_engine import LLMEngine
    llm = LLMEngine(
        model=model,
        base_url=ollama_url,
        keep_models_loaded=True,
        structured_json=True,
    )

    # Optional: knowledge store
    knowledge_store = None
    try:
        from knowledge.knowledge_store import InsuranceKnowledgeStore
        knowledge_store = InsuranceKnowledgeStore()
    except Exception:
        logger.debug("Knowledge store not available, proceeding without it")

    # Optional: schema registry for validation
    schema_registry = None
    try:
        from schema_registry import SchemaRegistry
        schema_registry = SchemaRegistry(schemas_dir=SCHEMAS_DIR)
    except Exception:
        logger.debug("Schema registry not available, skipping field validation")

    # --- Stage 1: LOB Classification ---
    logger.info("=" * 60)
    logger.info("Stage 1: LOB Classification")
    logger.info("=" * 60)
    result.lobs = lob_classifier.classify(
        email_text, llm, confidence_threshold=confidence_threshold
    )

    if not result.lobs:
        logger.warning("No LOBs classified — cannot proceed")
        _save_results(result, output_dir)
        return result

    # --- Stage 2: Entity Extraction ---
    logger.info("=" * 60)
    logger.info("Stage 2: Entity Extraction")
    logger.info("=" * 60)
    result.entities = entity_extractor.extract(
        email_text, llm, knowledge_store=knowledge_store
    )

    # --- Stage 3: Form Assignment ---
    logger.info("=" * 60)
    logger.info("Stage 3: Form Assignment")
    logger.info("=" * 60)
    result.assignments = form_assigner.assign(result.lobs)

    # --- Stage 4: Dynamic Form Reading + LLM Field Mapping ---
    logger.info("=" * 60)
    logger.info("Stage 4: Dynamic Form Reading + LLM Field Mapping")
    logger.info("=" * 60)

    # Collect LOB IDs
    lob_ids = []
    for assignment in result.assignments:
        for lob_id in assignment.lobs:
            if lob_id not in lob_ids:
                lob_ids.append(lob_id)

    # Read form catalogs and map fields
    result.field_values = llm_field_mapper.map_all(
        submission=result.entities,
        assignments=result.assignments,
        lobs=lob_ids,
        llm_engine=llm,
        schema_registry=schema_registry,
    )

    # --- Stage 5: Validation ---
    logger.info("=" * 60)
    logger.info("Stage 5: Field Validation")
    logger.info("=" * 60)
    for form_num, fields in result.field_values.items():
        vr = validation_engine.validate(fields, entities=result.entities)
        result.validation_results[form_num] = vr
        # Apply auto-corrections
        result.field_values[form_num] = vr.corrected_values
        if vr.auto_corrections:
            logger.info(f"Form {form_num}: {len(vr.auto_corrections)} auto-corrections applied")
        if vr.has_errors:
            logger.warning(f"Form {form_num}: {vr.error_count} validation errors")

    # --- Stage 6: PDF Filling ---
    if not json_only:
        logger.info("=" * 60)
        logger.info("Stage 6: PDF Filling")
        logger.info("=" * 60)
        filled_dir = output_dir / "filled_forms"
        filled_dir.mkdir(exist_ok=True)
        result.fill_results = pdf_filler.fill_all(result.field_values, filled_dir)
    else:
        logger.info("Stage 6: PDF Filling (skipped — json_only mode)")

    # --- Stage 7: Gap Analysis ---
    if show_gaps:
        logger.info("=" * 60)
        logger.info("Stage 7: Gap Analysis")
        logger.info("=" * 60)
        result.gap_report = gap_analyzer.analyze(
            result.entities,
            result.assignments,
            result.field_values,
            llm_engine=llm,
            validation_results=result.validation_results,
        )

    # Save all outputs
    _save_results(result, output_dir)

    # Print summary
    _print_summary(result)

    return result


def _save_results(result: PipelineResult, output_dir: Path):
    """Save all results as JSON files."""
    # Full submission
    with open(output_dir / "submission.json", "w") as f:
        json.dump(result.to_dict(), f, indent=2, default=str)

    # Classification
    with open(output_dir / "classification.json", "w") as f:
        json.dump([l.to_dict() for l in result.lobs], f, indent=2)

    # Extracted entities
    if result.entities:
        with open(output_dir / "extracted_entities.json", "w") as f:
            json.dump(result.entities.to_dict(), f, indent=2)

    # Form assignments
    with open(output_dir / "form_assignments.json", "w") as f:
        json.dump([a.to_dict() for a in result.assignments], f, indent=2)

    # Field mappings per form
    mappings_dir = output_dir / "field_mappings"
    mappings_dir.mkdir(exist_ok=True)
    for form_num, fields in result.field_values.items():
        with open(mappings_dir / f"form_{form_num}.json", "w") as f:
            json.dump(fields, f, indent=2)

    # Validation results
    if result.validation_results:
        with open(output_dir / "validation_results.json", "w") as f:
            json.dump(
                {k: v.to_dict() for k, v in result.validation_results.items()},
                f, indent=2,
            )

    # Gap report
    if result.gap_report:
        with open(output_dir / "gap_report.json", "w") as f:
            json.dump(result.gap_report.to_dict(), f, indent=2)

    logger.info(f"Results saved to {output_dir}")


def _print_summary(result: PipelineResult):
    """Print a human-readable summary."""
    print("\n" + "=" * 60)
    print("PIPELINE RESULTS")
    print("=" * 60)

    print(f"\nLOBs identified: {len(result.lobs)}")
    for lob in result.lobs:
        print(f"  - {lob.display_name} (confidence: {lob.confidence:.0%})")

    print(f"\nForms assigned: {len(result.assignments)}")
    for a in result.assignments:
        status = "fillable" if a.schema_available else "MANUAL"
        print(f"  - Form {a.form_number}: {a.purpose} [{status}]")

    print(f"\nField mappings:")
    for form_num, fields in result.field_values.items():
        print(f"  - Form {form_num}: {len(fields)} fields mapped")

    if result.validation_results:
        print(f"\nValidation:")
        for form_num, vr in result.validation_results.items():
            parts = []
            if vr.error_count:
                parts.append(f"{vr.error_count} errors")
            if vr.warning_count:
                parts.append(f"{vr.warning_count} warnings")
            if vr.auto_corrections:
                parts.append(f"{len(vr.auto_corrections)} auto-corrected")
            summary = ", ".join(parts) if parts else "all valid"
            print(f"  - Form {form_num}: {summary}")

    if result.fill_results:
        print(f"\nPDF filling:")
        for fr in result.fill_results:
            if fr.output_path:
                print(f"  - Form {fr.form_number}: {fr.filled_count} filled, {fr.skipped_count} skipped")
            else:
                print(f"  - Form {fr.form_number}: FAILED ({'; '.join(fr.errors[:2])})")

    if result.gap_report:
        print(f"\nGap analysis: {result.gap_report.completeness_pct:.0f}% complete")
        if result.gap_report.missing_critical:
            print(f"  Critical gaps: {len(result.gap_report.missing_critical)}")
        if result.gap_report.follow_up_questions:
            print(f"  Follow-up questions: {len(result.gap_report.follow_up_questions)}")
            for q in result.gap_report.follow_up_questions[:5]:
                print(f"    [{q.priority}] {q.question}")

    print(f"\nOutput: {result.output_dir}")
    print("=" * 60)
