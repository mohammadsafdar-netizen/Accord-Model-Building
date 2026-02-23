"""Agent tool definitions — bridge between LangGraph and existing pipeline modules."""

import json
import logging
from typing import Optional

from langchain_core.tools import tool

from Custom_model_fa_pf.agent.confidence import ConfidenceScorer

logger = logging.getLogger(__name__)
_scorer = ConfidenceScorer()


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


# --- Tool aliases for test imports ---
save_field_tool = save_field
validate_fields_tool = validate_fields
classify_lobs_tool = classify_lobs
extract_entities_tool = extract_entities
assign_forms_tool = assign_forms
read_form_tool = read_form
map_fields_tool = map_fields
analyze_gaps_tool = analyze_gaps


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
    ]
