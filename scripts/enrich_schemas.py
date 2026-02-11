#!/usr/bin/env python3
"""
Enrich ACORD schemas: add missing tooltips (137) and format hints (125, 127).
Run from best_project: python scripts/enrich_schemas.py
"""
from pathlib import Path
import json
import re

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


def tooltip_for_137_field(name: str, field_type: str) -> str:
    """Generate a tooltip for an ACORD 137 field from its name and type."""
    n = name.replace("_", " ").strip()
    # Checkbox/indicator
    if field_type in ("checkbox", "radio") or "Indicator" in name:
        # Human-readable: Vehicle BusinessAutoSymbol OneIndicator A -> Business Auto symbol 1
        label = re.sub(r"Indicator.*$", "", n)
        label = re.sub(r"Vehicle\s+", "", label)
        label = re.sub(r"\s+([A-Z])$", "", label)  # suffix _A
        label = re.sub(r"(\d+)", r" \1 ", label)
        return f"Checkbox: {label.strip()}. Return 1 if checked, Off if not."
    # Named insured
    if name.startswith("NamedInsured_"):
        if "FullName" in name:
            return "Named insured full name as on policy."
        if "Signature" in name:
            return "Named insured signature (text or 'signed')."
        if "SignatureDate" in name:
            return "Date named insured signed (MM/DD/YYYY)."
    # Policy
    if name.startswith("Policy_"):
        if "Date" in name:
            return "Policy date (MM/DD/YYYY)."
    # Insurer
    if name.startswith("Insurer_"):
        if "FullName" in name:
            return "Insurer full legal name."
        if "NAICCode" in name:
            return "NAIC code (numeric)."
    # Producer
    if name.startswith("Producer_"):
        if "Signature" in name:
            return "Producer/agent signature (text or 'signed')."
        if "NationalIdentifier" in name:
            return "Producer national identifier (e.g. NPN)."
    # Vehicle schedule fields
    if "StateOrProvinceCode" in name:
        return "Two-letter state code (e.g. IN, OH, CA)."
    if "Amount" in name or "LimitAmount" in name or "DeductibleAmount" in name or "CostAmount" in name or "ValueAmount" in name:
        return "Dollar amount (e.g. 50000 or $50,000)."
    if "DayCount" in name:
        return "Number of days (numeric)."
    if "Radius" in name:
        return "Radius value (miles or numeric)."
    if "VehicleCount" in name:
        return "Number of vehicles (numeric)."
    if "Description" in name or "SymbolDescription" in name or "RemarkText" in name:
        return "Text description or remark."
    if "LimitIndicator" in name:
        return "Checkbox: combined single limit. Return 1 or Off."
    if "YesIndicator" in name:
        return "Checkbox: yes if applicable. Return 1 or Off."
    if "PrimaryIndicator" in name:
        return "Checkbox: primary. Return 1 or Off."
    # Generic vehicle
    if name.startswith("Vehicle_"):
        return f"Vehicle schedule: {n.split('_', 1)[1].rsplit('_', 1)[0].replace('_', ' ')}."
    return f"ACORD 137 field: {n}."


def enrich_137(schemas_dir: Path) -> None:
    path = schemas_dir / "137.json"
    data = json.loads(path.read_text())
    for key, fd in data["fields"].items():
        if fd.get("tooltip"):
            continue
        fd["tooltip"] = tooltip_for_137_field(key, fd.get("type") or "text")
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  [137] Added tooltips to {len(data['fields'])} fields.")


def enrich_checkbox_tooltips(schemas_dir: Path, form: str) -> None:
    """Append ' Return 1 if checked, Off if not.' to checkbox/radio tooltips that lack it."""
    path = schemas_dir / f"{form}.json"
    data = json.loads(path.read_text())
    hint = " Return 1 if checked, Off if not."
    count = 0
    for key, fd in data["fields"].items():
        if fd.get("type") not in ("checkbox", "radio"):
            continue
        tip = fd.get("tooltip") or ""
        if hint.strip().lower() in tip.lower() or "1" in tip and "off" in tip.lower():
            continue
        fd["tooltip"] = (tip.strip() + hint) if tip else ("Checkbox." + hint)
        count += 1
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  [{form}] Enriched {count} checkbox/radio tooltips with format hint.")


def add_date_amount_hints(schemas_dir: Path, form: str) -> None:
    """Add format hints to date and amount fields that lack them."""
    path = schemas_dir / f"{form}.json"
    data = json.loads(path.read_text())
    count = 0
    for key, fd in data["fields"].items():
        if fd.get("type") not in ("text",):
            continue
        tip = (fd.get("tooltip") or "").strip()
        name = key.lower()
        if "date" in name and "mm/dd/yyyy" not in tip.lower() and "date" in tip.lower():
            fd["tooltip"] = tip + " (MM/DD/YYYY)." if not tip.endswith(").") else tip
            count += 1
        elif ("amount" in name or "limit" in name) and "dollar" not in tip.lower() and "amount" in tip.lower():
            if not tip.endswith("."):
                fd["tooltip"] = tip + " Use dollar amount."
                count += 1
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  [{form}] Added date/amount hints to {count} fields.")


def main() -> None:
    print("Enriching schemas in", SCHEMAS_DIR)
    enrich_137(SCHEMAS_DIR)
    for form in ("125", "127"):
        enrich_checkbox_tooltips(SCHEMAS_DIR, form)
        add_date_amount_hints(SCHEMAS_DIR, form)
    print("Done.")


if __name__ == "__main__":
    main()
