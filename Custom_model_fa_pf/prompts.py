"""LLM prompts for classification, extraction, and gap analysis."""

CLASSIFICATION_SYSTEM = """You are an insurance expert that classifies customer requests into lines of business (LOBs).
You must respond with ONLY valid JSON, no other text."""

CLASSIFICATION_PROMPT = """Analyze the following customer email/message and identify which insurance lines of business (LOBs) are being requested.

Available LOBs:
- commercial_auto: Commercial vehicle insurance (trucks, fleets, business autos, delivery vehicles)
- general_liability: General liability / CGL (bodily injury, property damage, premises, products)
- commercial_property: Commercial property insurance (buildings, equipment, contents, BPP)
- workers_compensation: Workers' compensation (employee injuries, payroll-based)
- commercial_umbrella: Umbrella / excess liability (additional limits above primary policies)
- bop: Business Owners Policy — bundled GL + property for small/mid businesses (restaurants, offices, retail)
- cyber: Cyber & privacy liability (data breach, network security, ransomware, privacy violations, PII/PHI)

Customer message:
---
{email_text}
---

Respond with ONLY this JSON structure:
{{
  "lobs": [
    {{
      "lob_id": "commercial_auto",
      "confidence": 0.95,
      "reasoning": "Customer mentions 3 trucks and needs fleet coverage"
    }}
  ]
}}

Rules:
- Include ALL LOBs that are explicitly or strongly implied in the message
- confidence: 0.0-1.0 (how certain you are this LOB is needed)
- If a LOB is only vaguely hinted at, use lower confidence (0.5-0.7)
- If clearly stated, use high confidence (0.85-1.0)
- Return empty lobs array if no insurance LOBs can be identified"""

EXTRACTION_SYSTEM = """You are an insurance data extraction expert. Extract structured information from customer emails.
You must respond with ONLY valid JSON, no other text. Use null for any field you cannot determine."""

EXTRACTION_PROMPT = """Extract all insurance-relevant information from this customer email/message into structured JSON.

Customer message:
---
{email_text}
---
{knowledge_context}
Respond with ONLY this JSON structure (use null for missing fields, MM/DD/YYYY for dates, 2-letter state codes):
{{
  "business": {{
    "business_name": "Company Name",
    "dba": null,
    "mailing_address": {{
      "line_one": "123 Main St",
      "line_two": null,
      "city": "Springfield",
      "state": "IL",
      "zip_code": "62701"
    }},
    "tax_id": "12-3456789",
    "naics": "484110",
    "sic": null,
    "entity_type": "corporation",
    "operations_description": "Long-haul trucking",
    "annual_revenue": "2500000",
    "employee_count": "15",
    "years_in_business": "10",
    "website": null,
    "business_start_date": "01/15/2015",
    "contacts": [
      {{
        "full_name": "John Smith",
        "phone": "555-123-4567",
        "email": "john@company.com",
        "role": "Owner"
      }}
    ],
    "nature_of_business": "Long-haul trucking",
    "part_time_employees": null,
    "annual_payroll": "850000",
    "subcontractor_cost": null
  }},
  "producer": {{
    "agency_name": "ABC Insurance Agency",
    "contact_name": "Jane Agent",
    "phone": "555-987-6543",
    "fax": null,
    "email": "jane@abcinsurance.com",
    "mailing_address": {{
      "line_one": "789 Broker St",
      "city": "Chicago",
      "state": "IL",
      "zip_code": "60601"
    }},
    "producer_code": "ABC-001",
    "license_number": "AG12345"
  }},
  "policy": {{
    "policy_number": null,
    "effective_date": "03/01/2026",
    "expiration_date": "03/01/2027",
    "status": "new",
    "billing_plan": "direct",
    "payment_plan": "annual",
    "deposit_amount": null,
    "estimated_premium": null
  }},
  "vehicles": [
    {{
      "vin": "1HGCM82633A004352",
      "year": "2024",
      "make": "Ford",
      "model": "F-350",
      "body_type": "PK",
      "gvw": "14000",
      "cost_new": "55000",
      "garaging_address": null,
      "use_type": "commercial",
      "radius_of_travel": null,
      "farthest_zone": null,
      "territory": null,
      "class_code": null,
      "stated_amount": null,
      "deductible_collision": "1000",
      "deductible_comprehensive": "500"
    }}
  ],
  "drivers": [
    {{
      "full_name": "John Smith",
      "first_name": "John",
      "last_name": "Smith",
      "middle_initial": null,
      "dob": "05/15/1985",
      "sex": "M",
      "marital_status": "M",
      "license_number": "S123-4567-8901",
      "license_state": "IL",
      "years_experience": "15",
      "hire_date": "01/15/2020",
      "mailing_address": null,
      "licensed_year": "2003",
      "occupation": null,
      "relationship": "employee",
      "vehicle_assigned": "1",
      "pct_use": "100"
    }}
  ],
  "coverages": [
    {{
      "lob": "commercial_auto",
      "coverage_type": "liability",
      "limit": "1000000",
      "deductible": "1000",
      "per_person_limit": "500000",
      "per_accident_limit": "1000000",
      "aggregate_limit": null,
      "premium": null,
      "symbol": "1"
    }}
  ],
  "locations": [
    {{
      "address": {{
        "line_one": "456 Industrial Dr",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62702"
      }},
      "building_area": "5000",
      "construction_type": "masonry",
      "year_built": "1995",
      "occupancy": "warehouse"
    }}
  ],
  "loss_history": [
    {{
      "date": "06/15/2024",
      "lob": "commercial_auto",
      "description": "Rear-end collision",
      "amount": "15000",
      "claim_status": "closed"
    }}
  ],
  "additional_interests": [
    {{
      "name": "First National Bank",
      "address": {{
        "line_one": "100 Finance Blvd",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62701"
      }},
      "interest_type": "lienholder",
      "account_number": "LOAN-12345",
      "certificate_required": true
    }}
  ],
  "prior_insurance": [
    {{
      "carrier_name": "State Farm",
      "policy_number": "SF-987654",
      "effective_date": "03/01/2025",
      "expiration_date": "03/01/2026",
      "premium": "4500",
      "lob": "commercial_auto"
    }}
  ],
  "cyber_info": null
}}

Rules:
- entity_type must be one of: corporation, partnership, llc, individual, subchapter_s, joint_venture
- sex must be: M or F
- marital_status must be one of: S (single), M (married), W (widowed), D (divorced), P (domestic partner)
- policy.status must be: new, renewal, or rewrite
- billing_plan must be: direct or agency
- payment_plan must be: monthly, quarterly, or annual
- Dates must be MM/DD/YYYY format
- State codes must be 2-letter US state abbreviations
- middle_initial should be a single letter (no period)
- licensed_year should be a 4-digit year
- Split driver names into first_name and last_name when possible; keep full_name too
- The "producer" is the insurance agent/broker/agency submitting the application — NOT the insured business
- producer.agency_name = the agency/brokerage firm name (e.g. "Westside Insurance Brokers")
- producer.contact_name = the individual agent name (e.g. "Rachel Green")
- Do NOT confuse business contacts with the producer — they are separate entities
- employee_count should be a number string (e.g. "24"), strip any suffix like "full-time"
- Omit entire sections (set to null) if no relevant data exists
- For arrays (vehicles, drivers, etc.), return empty array [] if none mentioned
- Extract ALL vehicles and drivers mentioned, even if details are partial
- interest_type must be one of: additional_insured, mortgagee, lienholder, loss_payee, lenders_loss_payable
- additional_interests: lienholders, mortgagees, loss payees, etc. (banks, finance companies holding liens)
- prior_insurance: previous/expiring insurance carriers and policy numbers
- cyber_info: only include if cyber/privacy coverage is discussed (set to null otherwise)
- For BI limits like "500/1000" or "500000/1000000": set per_person_limit and per_accident_limit separately
- For CSL (Combined Single Limit) like "$1M CSL": set limit to the total, coverage_type to "combined_single_limit"
- Driver relationship: employee, owner, family, other
- driver.vehicle_assigned: index (1-based) of the vehicle this driver primarily uses
- driver.pct_use: percentage of vehicle use (e.g. "100", "50")
- business.annual_payroll: total annual payroll amount (for workers' comp)
- business.nature_of_business: brief description (e.g. "trucking", "manufacturing")
- vehicle.territory: rating territory code
- vehicle.class_code: vehicle classification code
- vehicle.stated_amount: agreed/stated value for physical damage
- vehicle.deductible_collision and deductible_comprehensive: deductible amounts per vehicle
- coverage.symbol: auto symbol code (e.g. "1" for Any Auto, "2" for Owned Autos Only)
- coverage.premium: premium amount for this coverage if mentioned"""

# --- Field Mapping Prompts (for LLM-powered field mapper) ---

FIELD_MAPPING_SYSTEM = """You are an expert insurance form field mapper. Your job is to map extracted customer data
to PDF form fields. You understand ACORD form conventions, field naming patterns, and insurance terminology.
You must respond with ONLY valid JSON, no other text."""

FIELD_MAPPING_PROMPT = """Map the extracted customer data to the PDF form fields listed below.

EXTRACTED DATA:
{entity_json}

PDF FORM FIELDS (unmapped — need values):
{field_list}

ALREADY MAPPED FIELDS (for context — do NOT re-map these):
{already_mapped_sample}

RULES:
1. Only fill fields where you have clear data — SKIP if unsure
2. Checkboxes: "1" if true, "Off" if false, SKIP if unknown
3. Suffixes: _A = first item, _B = second, _C = third, etc.
4. Dates must be MM/DD/YYYY format
5. States must be 2-letter codes (e.g. "IL", "CA")
6. Use the tooltip to understand each field's purpose
7. For split-limit fields (per_person / per_accident), map each part separately
8. Phone numbers: (XXX) XXX-XXXX format
9. FEIN/Tax ID: XX-XXXXXXX format
10. Do NOT guess values — only map what exists in the extracted data

Respond with ONLY this JSON:
{{
  "mappings": {{
    "FieldName_A": "value",
    "FieldName_B": "value"
  }}
}}"""

# --- Smart Follow-up Prompt (validation-aware) ---

FOLLOW_UP_SYSTEM = """You are a professional insurance underwriting assistant. Generate specific, personalized follow-up
questions based on the extracted data and validation issues found. Reference actual data values when possible.
You must respond with ONLY valid JSON, no other text."""

FOLLOW_UP_PROMPT = """Generate follow-up questions for this insurance application.

WHAT WE HAVE:
{extracted_summary}

MISSING CRITICAL INFORMATION:
{missing_critical}

VALIDATION ISSUES FOUND:
{validation_issues}

RULES:
- Reference actual data values (e.g. "VIN for the 2024 RAM 3500 appears incomplete")
- Do NOT use generic questions (e.g. "Please provide VIN numbers")
- Group related questions naturally
- Prioritize critical issues that block underwriting
- Maximum 10 questions

Respond with ONLY this JSON:
{{
  "questions": [
    {{
      "category": "Vehicle Information",
      "priority": "critical",
      "question": "The VIN for the 2024 RAM 3500 appears to be only 15 characters — can you verify the full 17-character VIN?"
    }}
  ]
}}"""

GAP_ANALYSIS_SYSTEM = """You are an insurance underwriting assistant. Analyze extracted data completeness and generate follow-up questions.
You must respond with ONLY valid JSON, no other text."""

GAP_ANALYSIS_PROMPT = """Given the extracted entities and the required ACORD forms, identify missing critical information
and generate professional follow-up questions.

Extracted data:
{extracted_json}

Required forms: {form_list}

Lines of business: {lob_list}

Missing fields identified:
{missing_fields}

Generate follow-up questions that a producer/agent would ask the insured to complete the application.
Group questions logically and prioritize critical missing information.

Respond with ONLY this JSON:
{{
  "follow_up_questions": [
    {{
      "category": "Vehicle Information",
      "priority": "critical",
      "question": "Please provide the VIN numbers for all vehicles to be insured."
    }}
  ],
  "completeness_assessment": "Brief summary of data completeness and what's needed"
}}

Rules:
- priority: "critical" (blocks underwriting), "important" (affects rating), "optional" (nice to have)
- Questions should be professional and specific
- Group related questions under the same category
- Maximum 15 questions"""
