#!/usr/bin/env python3
"""
Schema Registry: ACORD field schema management
===============================================
Loads and manages field schemas for ACORD forms 125, 127, 137.
Provides field names, tooltips, categories, and suffix grouping
for schema-guided extraction.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ===========================================================================
# Constants
# ===========================================================================

SUPPORTED_FORMS = ("125", "127", "137")

FORM_NAMES = {
    "125": "Commercial Insurance Application",
    "127": "Business Auto Section",
    "137": "Commercial Auto Section",
}

# Categories in extraction order (most important first)
EXTRACTION_ORDER = [
    "header",
    "insurer",
    "producer",
    "named_insured",
    "policy",
    "driver",
    "vehicle",
    "coverage",
    "location",
    "loss_history",
    "checkbox",
    "remarks",
    "general",
]

# Category batching: group small categories into single LLM calls
# Each batch is a list of categories that are extracted together
CATEGORY_BATCHES = [
    ["header", "insurer", "producer"],         # Top-of-form fields
    ["named_insured", "policy"],               # Insured and policy details
    ["location", "loss_history", "remarks", "general"],  # Misc fields
    ["checkbox"],                              # All checkboxes
]

# Categories that are never batched (use specialized extraction paths)
SPECIAL_CATEGORIES = {"driver", "vehicle", "coverage"}


# ===========================================================================
# Data classes
# ===========================================================================

@dataclass
class FieldInfo:
    """Metadata about a single form field."""
    name: str
    field_type: str        # "text", "checkbox", "radio", "dropdown", "signature"
    tooltip: Optional[str] = None
    default_value: Optional[str] = None
    category: Optional[str] = None
    suffix: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.field_type,
            "tooltip": self.tooltip,
            "default_value": self.default_value,
            "category": self.category,
            "suffix": self.suffix,
        }


@dataclass
class FormSchema:
    """Full schema for one ACORD form."""
    form_number: str
    form_name: str
    total_fields: int
    fields: Dict[str, FieldInfo] = field(default_factory=dict)
    categories: Dict[str, List[str]] = field(default_factory=dict)

    # ----- Serialisation -----
    def to_dict(self) -> Dict[str, Any]:
        return {
            "form_number": self.form_number,
            "form_name": self.form_name,
            "total_fields": self.total_fields,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "categories": self.categories,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FormSchema":
        schema = cls(
            form_number=data["form_number"],
            form_name=data["form_name"],
            total_fields=data["total_fields"],
        )
        cats: Dict[str, List[str]] = defaultdict(list)
        for name, fd in data.get("fields", {}).items():
            fi = FieldInfo(
                name=fd["name"],
                field_type=fd["type"],
                tooltip=fd.get("tooltip"),
                default_value=fd.get("default_value"),
                category=fd.get("category"),
                suffix=fd.get("suffix"),
            )
            schema.fields[name] = fi
            cat = fi.category or "general"
            cats[cat].append(name)
        schema.categories = dict(cats)
        return schema


# ===========================================================================
# Registry
# ===========================================================================

class SchemaRegistry:
    """
    Registry of ACORD field schemas for forms 125, 127, 137.

    Usage:
        registry = SchemaRegistry()                 # auto-loads from schemas/
        schema = registry.get_schema("127")
        fields = registry.get_fields_by_category("127", "driver")
        tooltips = registry.get_tooltips("127", field_names)
    """

    def __init__(self, schemas_dir: Optional[Path] = None):
        if schemas_dir is None:
            schemas_dir = Path(__file__).parent / "schemas"
        self.schemas_dir = schemas_dir
        self.schemas: Dict[str, FormSchema] = {}
        self._load_schemas()

    def _load_schemas(self) -> None:
        if not self.schemas_dir.exists():
            print(f"Warning: schemas dir not found: {self.schemas_dir}")
            return
        for sf in self.schemas_dir.glob("*.json"):
            try:
                data = json.loads(sf.read_text())
                schema = FormSchema.from_dict(data)
                if schema.form_number in SUPPORTED_FORMS:
                    self.schemas[schema.form_number] = schema
                    print(f"  [Schema] ACORD {schema.form_number}: {schema.total_fields} fields")
            except Exception as e:
                print(f"  Warning: could not load {sf.name}: {e}")

    # ----- Lookups -----

    def get_schema(self, form_number: str) -> Optional[FormSchema]:
        return self.schemas.get(form_number)

    def get_field_names(self, form_number: str) -> List[str]:
        s = self.schemas.get(form_number)
        return sorted(s.fields.keys()) if s else []

    def get_fields_by_category(self, form_number: str, category: str) -> List[str]:
        s = self.schemas.get(form_number)
        return s.categories.get(category, []) if s else []

    def get_categories(self, form_number: str) -> List[str]:
        s = self.schemas.get(form_number)
        return sorted(s.categories.keys()) if s else []

    def get_field_info(self, form_number: str, field_name: str) -> Optional[FieldInfo]:
        s = self.schemas.get(form_number)
        return s.fields.get(field_name) if s else None

    def get_tooltips(self, form_number: str, field_names: List[str]) -> Dict[str, str]:
        """Return {field_name: tooltip} for the given field names."""
        s = self.schemas.get(form_number)
        if not s:
            return {}
        result: Dict[str, str] = {}
        for name in field_names:
            fi = s.fields.get(name)
            if fi and fi.tooltip:
                result[name] = fi.tooltip
        return result

    def get_suffix_groups(self, form_number: str, category: str) -> Dict[str, List[str]]:
        """Group fields by suffix (_A, _B, ...) within a category."""
        names = self.get_fields_by_category(form_number, category)
        groups: Dict[str, List[str]] = defaultdict(list)
        for name in names:
            suffix = _extract_suffix(name) or "_NONE"
            groups[suffix].append(name)
        return dict(groups)

    def get_all_fields_with_values(self, form_number: str) -> Dict[str, FieldInfo]:
        """Get all fields that have a non-empty default_value (ground truth)."""
        s = self.schemas.get(form_number)
        if not s:
            return {}
        return {
            name: fi for name, fi in s.fields.items()
            if fi.default_value and fi.default_value not in ("", "null", "Off", "None")
        }

    def validate_field_names(self, form_number: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Keep only fields whose names are valid in the schema."""
        s = self.schemas.get(form_number)
        if not s:
            return extracted
        return {k: v for k, v in extracted.items() if k in s.fields}

    # ----- Prompt helpers -----

    def get_schema_summary(self, form_number: str) -> str:
        s = self.schemas.get(form_number)
        if not s:
            return f"No schema for ACORD {form_number}"
        lines = [f"ACORD {s.form_number} - {s.form_name}", f"Total: {s.total_fields} fields", ""]
        for cat, fields in sorted(s.categories.items()):
            lines.append(f"  {cat}: {len(fields)} fields")
        return "\n".join(lines)

    def format_fields_for_prompt(
        self, form_number: str, field_names: List[str], max_fields: int = 50
    ) -> str:
        """Format a field list with tooltips for LLM prompts."""
        s = self.schemas.get(form_number)
        if not s:
            return "\n".join(field_names[:max_fields])
        lines: List[str] = []
        for name in field_names[:max_fields]:
            fi = s.fields.get(name)
            if fi and fi.tooltip:
                lines.append(f"  - {name}: {fi.tooltip[:100]}")
            else:
                lines.append(f"  - {name}")
        if len(field_names) > max_fields:
            lines.append(f"  ... ({len(field_names) - max_fields} more)")
        return "\n".join(lines)


# ===========================================================================
# Helpers
# ===========================================================================

def _extract_suffix(field_name: str) -> Optional[str]:
    m = re.search(r'_([A-Z])$', field_name)
    return f"_{m.group(1)}" if m else None


def detect_form_type(text: str, filename: str = "") -> Optional[str]:
    """Auto-detect ACORD form number from OCR text or filename."""
    combined = f"{filename} {text[:2000]}".lower()
    if "137" in combined or "vehicle schedule" in combined:
        return "137"
    if "127" in combined or "business auto" in combined:
        return "127"
    if "125" in combined or "commercial insurance" in combined or "commercial application" in combined:
        return "125"
    return None
