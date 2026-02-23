"""Stage 4: Map extracted entities to ACORD form field name/value pairs."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from Custom_model_fa_pf.entity_schema import CustomerSubmission
from Custom_model_fa_pf.form_assigner import FormAssignment
from Custom_model_fa_pf.lob_rules import LOB_DEFINITIONS, AVAILABLE_SCHEMAS

logger = logging.getLogger(__name__)

# Import field map modules
from Custom_model_fa_pf.field_maps import form_125, form_127, form_137, form_163

FIELD_MAP_MODULES = {
    "125": form_125,
    "127": form_127,
    "137": form_137,
    "163": form_163,
}


def map_all(
    submission: CustomerSubmission,
    assignments: List[FormAssignment],
    schema_registry=None,
) -> Dict[str, Dict[str, str]]:
    """Map extracted entities to field values for all assigned forms.

    Args:
        submission: Extracted customer submission
        assignments: List of form assignments
        schema_registry: Optional SchemaRegistry for field name validation

    Returns:
        Dict of form_number -> {field_name: value}
    """
    all_mappings: Dict[str, Dict[str, str]] = {}

    # Collect LOB checkboxes for Form 125
    lob_checkboxes = []
    for assignment in assignments:
        for lob_id in assignment.lobs:
            lob_def = LOB_DEFINITIONS.get(lob_id)
            if lob_def and lob_def.lob_checkbox_125:
                if lob_def.lob_checkbox_125 not in lob_checkboxes:
                    lob_checkboxes.append(lob_def.lob_checkbox_125)

    for assignment in assignments:
        form_num = assignment.form_number

        if not assignment.schema_available:
            logger.info(f"Form {form_num}: no schema available, skipping field mapping")
            continue

        mapper = FIELD_MAP_MODULES.get(form_num)
        if not mapper:
            logger.warning(f"Form {form_num}: no field map module found")
            continue

        # Call the form-specific mapper
        if form_num == "125":
            fields = mapper.map_fields(submission, lob_checkboxes=lob_checkboxes)
        else:
            fields = mapper.map_fields(submission)

        # Add completion date
        today = datetime.now().strftime("%m/%d/%Y")
        if form_num in ("125", "137"):
            fields["Form_CompletionDate_A"] = today

        # Validate field names against schema if available
        if schema_registry:
            validated = schema_registry.validate_field_names(form_num, fields)
            invalid = set(fields.keys()) - set(validated.keys())
            if invalid:
                logger.warning(
                    f"Form {form_num}: {len(invalid)} invalid field names removed: "
                    f"{sorted(invalid)[:5]}{'...' if len(invalid) > 5 else ''}"
                )
            fields = validated

        # Remove empty/None values
        fields = {k: str(v) for k, v in fields.items() if v is not None and str(v).strip()}

        all_mappings[form_num] = fields
        logger.info(f"Form {form_num}: mapped {len(fields)} fields")

    return all_mappings
