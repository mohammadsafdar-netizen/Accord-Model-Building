"""
RAG (few-shot) feature: retrieve example (field, value) pairs from ground truth.
================================================================================
When enabled with --use-rag, the extractor injects these examples into category,
driver, vehicle, and gap-fill prompts to improve accuracy (format and conventions).

Activation: pass --use-rag to main.py or test_pipeline.py; set --rag-gt-dir or
BEST_PROJECT_RAG_GT for the directory of ground-truth JSONs (default: test_data).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from schema_registry import SchemaRegistry


class ExampleRAGStore:
    """
    In-memory store of (form_type, category) -> list of {field_name: value} from GT.
    Retrieval returns a formatted string of example field->value pairs for prompt injection.
    """

    def __init__(self, schemas_dir: Optional[Path] = None):
        self.schemas_dir = Path(schemas_dir) if schemas_dir else Path(__file__).parent / "schemas"
        self.registry = SchemaRegistry(schemas_dir=self.schemas_dir)
        # (form_type, category) -> list of dicts (one per document)
        self._store: Dict[str, List[Dict[str, Any]]] = {}

    def _category_for_field(self, form_type: str, field_name: str) -> Optional[str]:
        schema = self.registry.get_schema(form_type)
        if not schema:
            return None
        for cat, names in schema.categories.items():
            if field_name in names:
                return cat
        return None

    def add_example(self, form_type: str, category: str, field_values: Dict[str, Any]) -> None:
        """Add one document's field->value map for (form_type, category)."""
        key = f"{form_type}:{category}"
        if key not in self._store:
            self._store[key] = []
        # Keep only non-empty, short values for good examples
        clean = {k: v for k, v in field_values.items() if v is not None and str(v).strip() and len(str(v)) < 200}
        if clean:
            self._store[key].append(clean)

    def retrieve(
        self,
        form_type: str,
        category: str,
        field_names: List[str],
        k: int = 3,
        max_examples_per_field: int = 2,
    ) -> str:
        """
        Retrieve up to k example documents for this (form_type, category),
        then format overlapping field->value pairs for the requested field_names.

        Returns a string like:
          Insurer_FullName_A: Acme Insurance Co.
          Insurer_NAICCode_A: 12345
          ...
        """
        key = f"{form_type}:{category}"
        docs = self._store.get(key, [])[:k]
        if not docs:
            return ""

        lines: List[str] = []
        seen_per_field: Dict[str, int] = {}
        for doc in docs:
            for fname in field_names:
                if fname not in doc:
                    continue
                if seen_per_field.get(fname, 0) >= max_examples_per_field:
                    continue
                val = doc[fname]
                if val is None or str(val).strip() == "":
                    continue
                lines.append(f"  {fname}: {val}")
                seen_per_field[fname] = seen_per_field.get(fname, 0) + 1

        if not lines:
            return ""
        return "Examples of correct extractions (format only; values are from other forms):\n" + "\n".join(lines[:20])

    def retrieve_for_fields(
        self,
        form_type: str,
        field_names: List[str],
        k: int = 2,
        max_total_lines: int = 25,
    ) -> str:
        """
        Retrieve few-shot examples for a mixed list of fields (e.g. gap-fill).
        Groups fields by category, retrieves per category, merges and caps total lines.
        """
        from collections import defaultdict
        by_cat: Dict[str, List[str]] = defaultdict(list)
        for fname in field_names:
            cat = self._category_for_field(form_type, fname) or "general"
            by_cat[cat].append(fname)
        seen: set = set()
        all_lines: List[str] = []
        for cat, names in by_cat.items():
            block = self.retrieve(form_type, cat, names, k=k)
            if not block:
                continue
            # Parse out the lines (skip header line)
            for line in block.split("\n"):
                if not line.strip() or line.startswith("Examples of"):
                    continue
                if line in seen:
                    continue
                seen.add(line)
                all_lines.append(line)
                if len(all_lines) >= max_total_lines:
                    break
            if len(all_lines) >= max_total_lines:
                break
        if not all_lines:
            return ""
        return "Examples of correct extractions (format only; values are from other forms):\n" + "\n".join(all_lines)

    @classmethod
    def from_ground_truth_dir(
        cls,
        gt_root: Path | str,
        schemas_dir: Optional[Path] = None,
        form_type_from_folder: bool = True,
    ) -> "ExampleRAGStore":
        """
        Build store from a directory of ground-truth JSONs.

        Expected layout:
          gt_root/
            125/ or ACORD_0125.../  -> form_type 125
            127/ ...
            137/ ...
          Each subdir can have *.json files; each JSON is one document's field->value.
        """
        gt_root = Path(gt_root)
        if not gt_root.exists():
            return cls(schemas_dir=schemas_dir)

        store = cls(schemas_dir=schemas_dir)
        registry = store.registry

        folder_to_form = {"125": "125", "127": "127", "137": "137", "0125": "125"}

        for subdir in gt_root.iterdir():
            if not subdir.is_dir():
                continue
            form_type = None
            name_lower = subdir.name.lower()
            if "125" in name_lower or "0125" in name_lower:
                form_type = "125"
            elif "127" in name_lower:
                form_type = "127"
            elif "137" in name_lower:
                form_type = "137"
            if form_type is None:
                continue

            schema = registry.get_schema(form_type)
            if not schema:
                continue

            for jpath in subdir.glob("*.json"):
                try:
                    with open(jpath, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    continue
                if not isinstance(data, dict):
                    continue
                # Group fields by category for this document, then add one example per category
                by_cat: Dict[str, Dict[str, Any]] = {}
                for field_name, value in data.items():
                    if field_name.startswith("_"):
                        continue
                    if not isinstance(value, (str, int, float, bool)) and value is not None:
                        if isinstance(value, (dict, list)):
                            continue
                    cat = None
                    for c, names in schema.categories.items():
                        if field_name in names:
                            cat = c
                            break
                    if cat is None:
                        cat = "general"
                    if cat not in by_cat:
                        by_cat[cat] = {}
                    by_cat[cat][field_name] = value
                for cat, field_values in by_cat.items():
                    store.add_example(form_type, cat, field_values)

        return store


def build_example_store(gt_dir: Path | str, schemas_dir: Optional[Path] = None) -> ExampleRAGStore:
    """Convenience: build store from test_data-style directory (form subdirs with JSONs)."""
    return ExampleRAGStore.from_ground_truth_dir(gt_dir, schemas_dir=schemas_dir)
