"""Agent tool definitions — bridge between LangGraph and existing pipeline modules."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

from Custom_model_fa_pf.agent.confidence import ConfidenceScorer
from Custom_model_fa_pf.config import (
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_DOC_EXTENSIONS,
    SUPPORTED_UPLOAD_EXTENSIONS,
)

logger = logging.getLogger(__name__)
_scorer = ConfidenceScorer()

_DOCUMENT_VLM_PROMPT = """You are an insurance document extraction specialist. Analyze this document image and:

1. CLASSIFY the document type as one of: loss_run, drivers_license, prior_declaration, acord_form, business_certificate, vehicle_registration, other

2. EXTRACT all insurance-relevant fields as a flat JSON object using these standard field names:
   - Business: business_name, dba, mailing_address, city, state, zip_code, tax_id, fein
   - Contact: phone, email, fax
   - Driver: driver_name, driver_dob, license_number, license_state, license_expiration
   - Vehicle: vin, vehicle_year, vehicle_make, vehicle_model, vehicle_use
   - Policy: policy_number, effective_date, expiration_date, carrier_name, premium, prior_carrier
   - Loss: loss_date, loss_description, loss_amount, claim_number, claim_status
   - General: entity_type, years_in_business, number_of_employees, annual_revenue, nature_of_business, sic_code, naics_code

3. Write a 1-2 sentence SUMMARY of what this document contains.

Respond with ONLY valid JSON in this format:
{"document_type": "...", "fields": {"field_name": "value", ...}, "summary": "..."}

Only include fields that are clearly visible in the document. Do not guess or hallucinate values."""


@tool
def save_field(field_name: str, value: str, source: str = "user_stated") -> str:
    """Record a confirmed field value from the customer.

    Call this after the customer provides a piece of information and you have
    confirmed it. The value is stored with a confidence score.

    Args:
        field_name: A descriptive field name (e.g., 'business_name', 'driver_a_dob')
        value: The field value as a string
        source: How the value was obtained ('user_stated', 'user_confirmed', 'llm_inferred')
    """
    if not value or not value.strip():
        return json.dumps({"status": "skipped", "field_name": field_name, "reason": "empty value"})

    confidence = _scorer.score(field_name, value, source=source)
    return json.dumps({
        "status": "saved",
        "field_name": field_name,
        "value": value.strip(),
        "source": source,
        "confidence": confidence,
    })


@tool
def validate_fields(fields_json: str) -> str:
    """Validate form field values against business rules.

    Checks VIN checksum, driver's license format by state, FEIN format,
    date ordering, phone format, and state/ZIP consistency. Returns errors,
    warnings, and auto-corrections.

    Args:
        fields_json: JSON string of {field_name: value} pairs to validate
    """
    from Custom_model_fa_pf.validation_engine import validate

    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    result = validate(fields)
    return json.dumps(result.to_dict())


@tool
def classify_lobs(text: str) -> str:
    """Classify which lines of business are needed based on the customer's description.

    Analyzes the text to identify insurance types: Commercial Auto, General Liability,
    Workers Compensation, Commercial Property, Commercial Umbrella, BOP, Cyber.

    Args:
        text: Customer description of their business and insurance needs
    """
    from Custom_model_fa_pf.lob_classifier import classify
    from Custom_model_fa_pf.agent._llm_provider import get_llm_engine

    try:
        llm = get_llm_engine()
        results = classify(text, llm)
        return json.dumps([r.to_dict() for r in results])
    except Exception as e:
        logger.error("classify_lobs failed: %s", e)
        return json.dumps({"error": str(e), "recoverable": True})


@tool
def extract_entities(text: str) -> str:
    """Extract structured insurance entities from text.

    Extracts business info, policy details, vehicles, drivers, coverage requests,
    locations, and loss history from the provided text.

    Args:
        text: Customer message containing insurance information
    """
    from Custom_model_fa_pf.entity_extractor import extract
    from Custom_model_fa_pf.agent._llm_provider import get_llm_engine

    try:
        llm = get_llm_engine()
        submission = extract(text, llm)
        return json.dumps(submission.to_dict())
    except Exception as e:
        logger.error("extract_entities failed: %s", e)
        return json.dumps({"error": str(e), "recoverable": True})


@tool
def assign_forms(lobs_json: str) -> str:
    """Determine which ACORD forms are needed based on lines of business.

    Args:
        lobs_json: JSON array of LOB classification dicts from classify_lobs
    """
    from Custom_model_fa_pf.lob_classifier import LOBClassification
    from Custom_model_fa_pf.form_assigner import assign

    try:
        lob_dicts = json.loads(lobs_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    lobs = []
    for d in lob_dicts:
        lobs.append(LOBClassification(
            lob_id=d["lob_id"],
            confidence=d.get("confidence", 0.9),
            reasoning=d.get("reasoning", ""),
            display_name=d.get("display_name", ""),
        ))

    assignments = assign(lobs)
    return json.dumps([a.to_dict() for a in assignments])


@tool
def read_form(pdf_path: str) -> str:
    """Read a fillable PDF form and return all field names, types, and tooltips.

    Works with any AcroForm PDF. Returns a catalog of all fields organized
    by category (driver, vehicle, policy, etc.).

    Args:
        pdf_path: Path to the PDF file to read
    """
    from pathlib import Path
    from Custom_model_fa_pf.form_reader import read_pdf_form

    catalog = read_pdf_form(Path(pdf_path))
    summary = {
        "form_number": catalog.form_number,
        "total_fields": catalog.total_fields,
        "text_fields": len(catalog.text_fields),
        "checkbox_fields": len(catalog.checkbox_fields),
        "sections": [s.to_dict() for s in catalog.sections[:5]],
    }
    return json.dumps(summary)


@tool
def map_fields(form_number: str, entities_json: str) -> str:
    """Map extracted customer data to form fields using the 3-phase field mapper.

    Phase 1: Deterministic regex patterns (instant).
    Phase 2: Suffix-indexed array mapping for drivers/vehicles (instant).
    Phase 3: LLM batch mapping for remaining fields.

    Args:
        form_number: ACORD form number (e.g., '125', '127', '137')
        entities_json: JSON string of extracted entities (CustomerSubmission format)
    """
    from Custom_model_fa_pf.entity_schema import CustomerSubmission
    from Custom_model_fa_pf.form_reader import find_template, read_pdf_form
    from Custom_model_fa_pf import llm_field_mapper
    from Custom_model_fa_pf.agent._llm_provider import get_llm_engine

    try:
        entity_dict = json.loads(entities_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    entities = CustomerSubmission.from_llm_json(entity_dict)

    template_path = find_template(form_number)
    if template_path is None:
        return json.dumps({"error": f"No template found for form {form_number}"})

    try:
        catalog = read_pdf_form(template_path)
        llm = get_llm_engine()

        result = llm_field_mapper.map_fields(
            entities=entities, catalog=catalog, llm_engine=llm
        )

        return json.dumps({
            "form_number": form_number,
            "total_mapped": result.total_mapped,
            "phase1_count": result.phase1_count,
            "phase2_count": result.phase2_count,
            "phase3_count": result.phase3_count,
            "mappings": result.mappings,
        })
    except Exception as e:
        logger.error("map_fields failed for form %s: %s", form_number, e)
        return json.dumps({"error": str(e), "recoverable": True})


@tool
def analyze_gaps(entities_json: str, assigned_forms_json: str, field_values_json: str) -> str:
    """Analyze which required fields are still missing or incomplete.

    Returns missing critical fields, missing important fields, completeness
    percentage, and suggested follow-up questions.

    Args:
        entities_json: JSON string of extracted entities
        assigned_forms_json: JSON array of form assignment dicts
        field_values_json: JSON of {form_number: {field_name: value}}
    """
    from Custom_model_fa_pf.entity_schema import CustomerSubmission
    from Custom_model_fa_pf.form_assigner import FormAssignment
    from Custom_model_fa_pf.gap_analyzer import analyze

    try:
        entities = CustomerSubmission.from_llm_json(json.loads(entities_json))
        assignments_dicts = json.loads(assigned_forms_json)
        field_values = json.loads(field_values_json)
    except (json.JSONDecodeError, Exception) as e:
        return json.dumps({"error": f"Parse error: {e}"})

    assignments = []
    for d in assignments_dicts:
        assignments.append(FormAssignment(
            form_number=d["form_number"],
            purpose=d.get("purpose", ""),
            schema_available=d.get("schema_available", False),
            lobs=d.get("lobs", []),
        ))

    report = analyze(entities, assignments, field_values)
    return json.dumps(report.to_dict())


@tool
def fill_forms(entities_json: str, assigned_forms_json: str) -> str:
    """Map collected entities to ACORD form fields and fill blank PDF templates.

    Runs the full mapping→validation→fill pipeline:
    1. Parse entities into a CustomerSubmission
    2. Parse form assignments into FormAssignment objects
    3. Run 3-phase field mapping (regex → indexed arrays → LLM batch)
    4. Validate and auto-correct field values
    5. Fill blank PDF templates and save to output directory

    Call this when all data has been collected and the user wants to generate
    filled ACORD forms.

    Args:
        entities_json: JSON string of extracted entities (CustomerSubmission format
                       from extract_entities)
        assigned_forms_json: JSON array of form assignment dicts (from assign_forms)
    """
    from datetime import datetime

    from Custom_model_fa_pf.entity_schema import CustomerSubmission
    from Custom_model_fa_pf.form_assigner import FormAssignment
    from Custom_model_fa_pf import llm_field_mapper
    from Custom_model_fa_pf.validation_engine import validate
    from Custom_model_fa_pf.pdf_filler import fill_all
    from Custom_model_fa_pf.config import OUTPUT_DIR
    from Custom_model_fa_pf.agent._llm_provider import get_llm_engine

    # --- Parse inputs ---
    try:
        entity_dict = json.loads(entities_json)
    except json.JSONDecodeError as e:
        return json.dumps({"status": "error", "error": f"Invalid entities JSON: {e}"})

    try:
        forms_list = json.loads(assigned_forms_json)
    except json.JSONDecodeError as e:
        return json.dumps({"status": "error", "error": f"Invalid forms JSON: {e}"})

    submission = CustomerSubmission.from_llm_json(entity_dict)

    assignments = []
    for d in forms_list:
        assignments.append(FormAssignment(
            form_number=d["form_number"],
            purpose=d.get("purpose", ""),
            schema_available=d.get("schema_available", False),
            lobs=d.get("lobs", []),
        ))

    # Collect LOB IDs
    lobs = []
    for a in assignments:
        for lob_id in a.lobs:
            if lob_id not in lobs:
                lobs.append(lob_id)

    # --- Stage 4: Field mapping ---
    try:
        llm = get_llm_engine()
    except Exception:
        llm = None
        logger.warning("LLM engine unavailable — Phase 3 mapping will be skipped")

    try:
        all_field_values = llm_field_mapper.map_all(
            submission=submission,
            assignments=assignments,
            lobs=lobs,
            llm_engine=llm,
        )
    except Exception as e:
        logger.error("Field mapping failed: %s", e)
        return json.dumps({"status": "error", "error": f"Field mapping failed: {e}"})

    # --- Stage 5: Validation + auto-correction ---
    validation_results = {}
    for form_num, fields in all_field_values.items():
        try:
            result = validate(fields)
            # Apply auto-corrections
            for fname, corrected in result.corrected_values.items():
                if fname in fields:
                    fields[fname] = corrected
            validation_results[form_num] = result.to_dict()
        except Exception as e:
            logger.warning("Validation failed for form %s: %s", form_num, e)

    # --- Stage 6: Fill PDFs ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filled_dir = OUTPUT_DIR / timestamp / "filled_forms"
    filled_dir.mkdir(parents=True, exist_ok=True)

    try:
        fill_results = fill_all(all_field_values, filled_dir)
    except Exception as e:
        logger.error("PDF filling failed: %s", e)
        return json.dumps({"status": "error", "error": f"PDF filling failed: {e}"})

    # --- Save JSON artifacts ---
    results_dir = OUTPUT_DIR / timestamp
    try:
        (results_dir / "entities.json").write_text(
            json.dumps(entity_dict, indent=2, default=str))
        (results_dir / "field_mappings.json").write_text(
            json.dumps({k: v for k, v in all_field_values.items()}, indent=2, default=str))
        if validation_results:
            (results_dir / "validation.json").write_text(
                json.dumps(validation_results, indent=2, default=str))
    except Exception as e:
        logger.warning("Failed to save JSON results: %s", e)

    # --- Build response ---
    total_filled = sum(r.filled_count for r in fill_results)
    per_form = []
    for r in fill_results:
        per_form.append({
            "form_number": r.form_number,
            "filled_count": r.filled_count,
            "skipped_count": r.skipped_count,
            "error_count": r.error_count,
            "output_path": str(r.output_path) if r.output_path else None,
            "errors": r.errors,
        })

    return json.dumps({
        "status": "filled",
        "output_dir": str(results_dir),
        "total_fields_filled": total_filled,
        "forms_count": len(fill_results),
        "fill_results": per_form,
    })


@tool
def process_document(file_path: str) -> str:
    """Process an uploaded document image or PDF and extract insurance-relevant fields.

    Accepts scanned documents like loss runs, driver's licenses, prior declarations,
    vehicle registrations, business certificates, and partially-filled ACORD forms.
    Uses VLM (vision language model) to read the document directly from the image.

    Args:
        file_path: Absolute path to the document file (PDF, PNG, JPG, TIFF, etc.)
    """
    from Custom_model_fa_pf.agent._llm_provider import get_vlm_engine

    path = Path(file_path).expanduser().resolve()

    # Validate file exists
    if not path.exists():
        return json.dumps({"status": "error", "error": f"File not found: {file_path}"})

    # Validate extension
    ext = path.suffix.lower()
    if ext not in SUPPORTED_UPLOAD_EXTENSIONS:
        return json.dumps({
            "status": "error",
            "error": f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_UPLOAD_EXTENSIONS))}",
        })

    tmp_dir = None
    image_paths = []

    try:
        # Convert PDF to page images, or use image directly
        if ext in SUPPORTED_DOC_EXTENSIONS:
            from ocr_engine import OCREngine
            tmp_dir = tempfile.mkdtemp(prefix="intake_doc_")
            ocr = OCREngine(dpi=200)
            image_paths = ocr.pdf_to_images(path, Path(tmp_dir))
            logger.info("Converted PDF to %d page images", len(image_paths))
        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            image_paths = [path]
        else:
            return json.dumps({"status": "error", "error": f"Unsupported extension: {ext}"})

        if not image_paths:
            return json.dumps({"status": "error", "error": "No pages found in document"})

        # Process up to 3 pages with VLM
        max_pages = 3
        pages_to_process = image_paths[:max_pages]
        vlm = get_vlm_engine()

        all_fields = {}
        document_type = "other"
        summaries = []

        for i, img_path in enumerate(pages_to_process):
            logger.info("VLM extracting page %d/%d: %s", i + 1, len(pages_to_process), img_path.name)
            try:
                raw = vlm.generate_vlm_extract(_DOCUMENT_VLM_PROMPT, img_path)
                parsed = json.loads(raw)

                # Use document_type from first page (most reliable)
                if i == 0 and "document_type" in parsed:
                    document_type = parsed["document_type"]

                # Merge fields (later pages don't overwrite earlier ones)
                page_fields = parsed.get("fields", {})
                for k, v in page_fields.items():
                    if v and k not in all_fields:
                        all_fields[k] = v

                if parsed.get("summary"):
                    summaries.append(parsed["summary"])

            except json.JSONDecodeError:
                logger.warning("VLM returned non-JSON for page %d, skipping", i + 1)
            except Exception as e:
                logger.warning("VLM extraction failed for page %d: %s", i + 1, e)

        summary = " ".join(summaries) if summaries else f"Processed {document_type} document"

        return json.dumps({
            "status": "processed",
            "file_path": str(path),
            "document_type": document_type,
            "fields": all_fields,
            "summary": summary,
            "pages_total": len(image_paths),
            "pages_processed": len(pages_to_process),
        })

    except Exception as e:
        logger.error("process_document failed: %s", e)
        return json.dumps({"status": "error", "error": str(e), "recoverable": True})

    finally:
        # Clean up temp directory for PDF conversions
        if tmp_dir:
            import shutil
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass


# --- Tool aliases for test imports ---
save_field_tool = save_field
validate_fields_tool = validate_fields
classify_lobs_tool = classify_lobs
extract_entities_tool = extract_entities
assign_forms_tool = assign_forms
read_form_tool = read_form
map_fields_tool = map_fields
analyze_gaps_tool = analyze_gaps
process_document_tool = process_document
fill_forms_tool = fill_forms


def get_all_tools():
    """Return all agent tools for binding to the LLM."""
    return [
        save_field,
        validate_fields,
        classify_lobs,
        extract_entities,
        assign_forms,
        read_form,
        map_fields,
        analyze_gaps,
        process_document,
        fill_forms,
    ]
