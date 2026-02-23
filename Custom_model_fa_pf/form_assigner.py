"""Stage 3: Assign required ACORD forms based on classified LOBs."""

import logging
from dataclasses import dataclass
from typing import List, Set

from Custom_model_fa_pf.lob_classifier import LOBClassification
from Custom_model_fa_pf.lob_rules import LOB_DEFINITIONS, AVAILABLE_SCHEMAS

logger = logging.getLogger(__name__)


@dataclass
class FormAssignment:
    form_number: str
    purpose: str
    schema_available: bool
    lobs: List[str]  # Which LOBs require this form

    def to_dict(self):
        return {
            "form_number": self.form_number,
            "purpose": self.purpose,
            "schema_available": self.schema_available,
            "lobs": self.lobs,
        }


# Form descriptions
FORM_PURPOSES = {
    "125": "Commercial Insurance Application (ACORD 125)",
    "126": "Commercial General Liability Section",
    "127": "Business Auto Section - Drivers & Vehicles",
    "130": "Workers' Compensation Application",
    "137": "Commercial Auto Section - Coverage & Symbols",
    "140": "Commercial Property Section",
    "163": "Commercial Umbrella / Excess Liability",
}


def assign(classifications: List[LOBClassification]) -> List[FormAssignment]:
    """Assign ACORD forms based on LOB classifications.

    Args:
        classifications: List of LOBClassification from the classifier

    Returns:
        Deduplicated list of FormAssignment with schema availability
    """
    # Track which forms are needed and which LOBs require them
    form_lobs: dict[str, list[str]] = {}

    for classification in classifications:
        lob_def = LOB_DEFINITIONS.get(classification.lob_id)
        if not lob_def:
            logger.warning(f"Unknown LOB: {classification.lob_id}")
            continue

        for form_num in lob_def.forms:
            if form_num not in form_lobs:
                form_lobs[form_num] = []
            if classification.lob_id not in form_lobs[form_num]:
                form_lobs[form_num].append(classification.lob_id)

    # Build assignments (Form 125 first, then in numeric order)
    assignments = []
    sorted_forms = sorted(form_lobs.keys(), key=lambda x: (x != "125", x))

    for form_num in sorted_forms:
        assignments.append(
            FormAssignment(
                form_number=form_num,
                purpose=FORM_PURPOSES.get(form_num, f"ACORD Form {form_num}"),
                schema_available=form_num in AVAILABLE_SCHEMAS,
                lobs=form_lobs[form_num],
            )
        )

    logger.info(
        f"Assigned {len(assignments)} forms: "
        f"{[a.form_number for a in assignments]} "
        f"(fillable: {[a.form_number for a in assignments if a.schema_available]})"
    )
    return assignments
