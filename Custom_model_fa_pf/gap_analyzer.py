"""Stage 6: Analyze gaps in extracted data and generate follow-up questions.

Provides contextual, grouped follow-up questions with progressive disclosure:
- First pass: only critical missing info (3-5 questions max)
- Subsequent passes: remaining gaps in priority order
- Groups related gaps into single questions
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from Custom_model_fa_pf.entity_schema import CustomerSubmission
from Custom_model_fa_pf.form_assigner import FormAssignment
from Custom_model_fa_pf.lob_rules import REQUIRED_FIELDS_BY_LOB
from Custom_model_fa_pf.prompts import GAP_ANALYSIS_SYSTEM, GAP_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

# Maximum questions per priority tier in progressive disclosure
MAX_CRITICAL_QUESTIONS = 5
MAX_IMPORTANT_QUESTIONS = 5


@dataclass
class GapQuestion:
    category: str
    priority: str  # critical, important, optional
    question: str

    def to_dict(self):
        return {
            "category": self.category,
            "priority": self.priority,
            "question": self.question,
        }


@dataclass
class GapReport:
    missing_critical: List[str] = field(default_factory=list)
    missing_important: List[str] = field(default_factory=list)
    follow_up_questions: List[GapQuestion] = field(default_factory=list)
    completeness_pct: float = 0.0
    completeness_assessment: str = ""

    def to_dict(self):
        return {
            "missing_critical": self.missing_critical,
            "missing_important": self.missing_important,
            "follow_up_questions": [q.to_dict() for q in self.follow_up_questions],
            "completeness_pct": round(self.completeness_pct, 1),
            "completeness_assessment": self.completeness_assessment,
        }


# --- Contextual question templates per field category ---
# Groups related fields into natural human-readable questions

_GROUPED_QUESTIONS = {
    # Vehicle info group
    frozenset({"vehicles[].vin", "vehicles[].year", "vehicles[].make", "vehicles[].model"}): GapQuestion(
        category="Vehicle Information",
        priority="critical",
        question="I need the vehicle details for each vehicle to be insured: year, make, model, and VIN number.",
    ),
    # Driver info group
    frozenset({"drivers[].full_name", "drivers[].dob", "drivers[].license_number", "drivers[].license_state"}): GapQuestion(
        category="Driver Information",
        priority="critical",
        question="Please provide details for each driver: full name, date of birth, driver's license number, and state.",
    ),
    # Business address group
    frozenset({"business.mailing_address"}): GapQuestion(
        category="Business Information",
        priority="critical",
        question="What is the business mailing address (street, city, state, ZIP)?",
    ),
    # Location info group
    frozenset({"locations", "locations[].building_area", "locations[].construction_type", "locations[].year_built"}): GapQuestion(
        category="Location Information",
        priority="important",
        question="For each business location, I need: address, building square footage, construction type, and year built.",
    ),
    # Business identity group
    frozenset({"business.tax_id", "business.entity_type"}): GapQuestion(
        category="Business Information",
        priority="important",
        question="What is the business FEIN/Tax ID, and what is the legal entity type (Corporation, LLC, Partnership, etc.)?",
    ),
}

# Individual field → question fallback (when no group matches)
_FIELD_QUESTIONS = {
    "business.business_name": GapQuestion("Business Information", "critical",
        "What is the legal business name?"),
    "business.mailing_address": GapQuestion("Business Information", "critical",
        "What is the business mailing address?"),
    "policy.effective_date": GapQuestion("Policy Information", "critical",
        "What is the desired policy effective date?"),
    "vehicles": GapQuestion("Vehicle Information", "critical",
        "Please provide information for the vehicles to be insured (year, make, model, VIN)."),
    "drivers": GapQuestion("Driver Information", "critical",
        "Please provide information for all drivers (name, DOB, license number/state)."),
    "locations": GapQuestion("Location Information", "critical",
        "Please provide the business location(s) with address details."),
    "business.tax_id": GapQuestion("Business Information", "important",
        "What is the business FEIN/Tax ID number?"),
    "business.entity_type": GapQuestion("Business Information", "important",
        "What is the legal entity type (Corporation, LLC, Partnership, Individual, etc.)?"),
    "business.operations_description": GapQuestion("Business Information", "important",
        "Please describe the nature of your business operations."),
    "business.annual_revenue": GapQuestion("Business Information", "important",
        "What is the approximate annual revenue?"),
    "business.employee_count": GapQuestion("Business Information", "important",
        "How many employees does the business have?"),
    "vehicles[].vin": GapQuestion("Vehicle Information", "important",
        "What are the VIN numbers for each vehicle?"),
    "vehicles[].year": GapQuestion("Vehicle Information", "important",
        "What is the model year for each vehicle?"),
    "vehicles[].make": GapQuestion("Vehicle Information", "important",
        "What is the make for each vehicle?"),
    "vehicles[].model": GapQuestion("Vehicle Information", "important",
        "What is the model for each vehicle?"),
    "drivers[].full_name": GapQuestion("Driver Information", "important",
        "What are the full names of all drivers?"),
    "drivers[].dob": GapQuestion("Driver Information", "important",
        "What are the dates of birth for all drivers?"),
    "drivers[].license_number": GapQuestion("Driver Information", "important",
        "What are the driver's license numbers?"),
    "drivers[].license_state": GapQuestion("Driver Information", "important",
        "What states issued the driver's licenses?"),
    "coverages": GapQuestion("Coverage Information", "important",
        "What coverage limits and deductibles are you looking for?"),
    "locations[].building_area": GapQuestion("Location Information", "important",
        "What is the total square footage of each building?"),
    "locations[].construction_type": GapQuestion("Location Information", "important",
        "What is the construction type for each building (frame, masonry, etc.)?"),
    "locations[].year_built": GapQuestion("Location Information", "important",
        "What year was each building constructed?"),
}


def _check_field(submission: CustomerSubmission, field_path: str) -> bool:
    """Check if a field path has a value in the submission."""
    parts = field_path.split(".")

    # Normalize: strip [] from all parts
    clean_parts = [p.replace("[]", "") for p in parts]

    # Handle list fields (vehicles, drivers, etc.)
    list_names = {"vehicles", "drivers", "coverages", "locations", "loss_history",
                  "additional_interests", "prior_insurance"}
    if clean_parts[0] in list_names:
        items = getattr(submission, clean_parts[0], [])
        if not items:
            return False
        if len(clean_parts) == 1:
            return True
        # Check array element fields like "vehicles[].vin" → check attr on items
        attr_name = clean_parts[1]
        return any(getattr(item, attr_name, None) for item in items)

    # Handle nested fields like "business.business_name"
    obj = submission
    for part in parts:
        if obj is None:
            return False
        obj = getattr(obj, part, None)

    return obj is not None and str(obj).strip() != ""


def _build_contextual_questions(
    missing_critical: List[str],
    missing_important: List[str],
) -> List[GapQuestion]:
    """Build grouped, contextual follow-up questions from missing fields.

    Groups related fields into single questions and prioritizes by importance.
    Uses progressive disclosure: critical first (limited), then important.
    """
    questions: List[GapQuestion] = []
    asked_fields: Set[str] = set()

    # Extract just the field paths (strip "[lob_id] " prefix)
    def _extract_path(missing_str: str) -> str:
        if "] " in missing_str:
            return missing_str.split("] ", 1)[1].replace(" > ", ".").replace(" ", "_")
        return missing_str.replace(" > ", ".").replace(" ", "_")

    critical_paths = {_extract_path(m) for m in missing_critical}
    important_paths = {_extract_path(m) for m in missing_important}
    all_missing = critical_paths | important_paths

    # Phase 1: Try grouped questions first
    for field_group, question in _GROUPED_QUESTIONS.items():
        overlap = field_group & all_missing
        if len(overlap) >= 2:  # Group matches if 2+ fields are missing
            questions.append(question)
            asked_fields.update(field_group)

    # Phase 2: Individual questions for remaining critical fields
    for path in sorted(critical_paths - asked_fields):
        if len(questions) >= MAX_CRITICAL_QUESTIONS:
            break
        if path in _FIELD_QUESTIONS:
            q = _FIELD_QUESTIONS[path]
            questions.append(GapQuestion(q.category, "critical", q.question))
            asked_fields.add(path)

    # Phase 3: Individual questions for remaining important fields
    for path in sorted(important_paths - asked_fields):
        if len(questions) >= MAX_CRITICAL_QUESTIONS + MAX_IMPORTANT_QUESTIONS:
            break
        if path in _FIELD_QUESTIONS:
            q = _FIELD_QUESTIONS[path]
            questions.append(GapQuestion(q.category, "important", q.question))
            asked_fields.add(path)

    # Deduplicate by question text
    seen = set()
    unique = []
    for q in questions:
        if q.question not in seen:
            seen.add(q.question)
            unique.append(q)

    return unique


def analyze(
    submission: CustomerSubmission,
    assignments: List[FormAssignment],
    field_values: Dict[str, Dict[str, str]],
    llm_engine=None,
    validation_results: Optional[Dict] = None,
) -> GapReport:
    """Analyze gaps in extracted data and generate follow-up questions.

    Args:
        submission: Extracted customer submission
        assignments: Form assignments
        field_values: Mapped field values per form
        llm_engine: Optional LLMEngine for generating follow-up questions
        validation_results: Optional validation results per form

    Returns:
        GapReport with missing fields and follow-up questions
    """
    report = GapReport()

    # Collect all LOBs
    all_lobs = set()
    for assignment in assignments:
        all_lobs.update(assignment.lobs)

    # Check required fields per LOB
    total_required = 0
    total_present = 0

    for lob_id in all_lobs:
        requirements = REQUIRED_FIELDS_BY_LOB.get(lob_id, {})

        for field_path in requirements.get("critical", []):
            total_required += 1
            if _check_field(submission, field_path):
                total_present += 1
            else:
                readable = field_path.replace(".", " > ").replace("_", " ")
                report.missing_critical.append(f"[{lob_id}] {readable}")

        for field_path in requirements.get("important", []):
            total_required += 1
            if _check_field(submission, field_path):
                total_present += 1
            else:
                readable = field_path.replace(".", " > ").replace("_", " ")
                report.missing_important.append(f"[{lob_id}] {readable}")

    # Calculate completeness
    if total_required > 0:
        report.completeness_pct = (total_present / total_required) * 100

    # Incorporate validation issues into gap analysis
    if validation_results:
        for form_num, vr in validation_results.items():
            for issue in vr.issues:
                if issue.severity == "error":
                    report.missing_critical.append(
                        f"[validation] Form {form_num}: {issue.message}"
                    )
                elif issue.severity == "warning":
                    report.missing_important.append(
                        f"[validation] Form {form_num}: {issue.message}"
                    )

    # Generate contextual follow-up questions (no LLM needed)
    report.follow_up_questions = _build_contextual_questions(
        report.missing_critical, report.missing_important
    )

    # Optionally enhance with LLM-generated questions
    if llm_engine and (report.missing_critical or report.missing_important):
        try:
            missing_text = ""
            if report.missing_critical:
                missing_text += "CRITICAL missing:\n" + "\n".join(f"- {f}" for f in report.missing_critical) + "\n"
            if report.missing_important:
                missing_text += "IMPORTANT missing:\n" + "\n".join(f"- {f}" for f in report.missing_important)

            prompt = GAP_ANALYSIS_PROMPT.format(
                extracted_json=str(submission.to_dict())[:2000],
                form_list=", ".join(a.form_number for a in assignments),
                lob_list=", ".join(all_lobs),
                missing_fields=missing_text,
            )

            response = llm_engine.generate(prompt=prompt, system=GAP_ANALYSIS_SYSTEM)
            parsed = llm_engine.parse_json(response)

            if parsed:
                # Merge LLM questions (avoid duplicates)
                existing_texts = {q.question for q in report.follow_up_questions}
                for q in parsed.get("follow_up_questions", []):
                    q_text = q.get("question", "")
                    if q_text and q_text not in existing_texts:
                        report.follow_up_questions.append(
                            GapQuestion(
                                category=q.get("category", "General"),
                                priority=q.get("priority", "important"),
                                question=q_text,
                            )
                        )
                        existing_texts.add(q_text)
                report.completeness_assessment = parsed.get("completeness_assessment", "")

        except Exception as e:
            logger.warning(f"LLM gap analysis failed: {e}")

    # Fallback assessment if no LLM
    if not report.completeness_assessment:
        if report.completeness_pct >= 80:
            report.completeness_assessment = "Good data completeness. Minor details may be needed."
        elif report.completeness_pct >= 50:
            report.completeness_assessment = "Moderate data completeness. Several important fields are missing."
        else:
            report.completeness_assessment = "Low data completeness. Critical information is needed before proceeding."

    logger.info(
        f"Gap analysis: {report.completeness_pct:.0f}% complete, "
        f"{len(report.missing_critical)} critical, {len(report.missing_important)} important gaps, "
        f"{len(report.follow_up_questions)} questions"
    )
    return report
