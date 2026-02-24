# Custom_model_fa_pf Architecture

**Commercial Insurance Intake, Form-Filling, Quoting & Placement Agent**

A LangGraph-powered conversational AI agent that guides customers through the complete commercial insurance pipeline: data collection, ACORD form filling, carrier quoting, and policy binding.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Project Structure](#2-project-structure)
3. [LangGraph Agent Architecture](#3-langgraph-agent-architecture)
4. [State Management](#4-state-management)
5. [Agent Tools (16)](#5-agent-tools)
6. [Node Functions](#6-node-functions)
7. [Prompt System](#7-prompt-system)
8. [Confidence & Review Routing](#8-confidence--review-routing)
9. [Entity Schema & Flattening](#9-entity-schema--flattening)
10. [Data Collection Pipeline](#10-data-collection-pipeline)
11. [Quoting & Placement Pipeline](#11-quoting--placement-pipeline)
12. [Form Filling Pipeline](#12-form-filling-pipeline)
13. [Validation Engine](#13-validation-engine)
14. [Entry Points (CLI, API)](#14-entry-points)
15. [Configuration](#15-configuration)
16. [Testing](#16-testing)
17. [Design Patterns](#17-design-patterns)
18. [Future: Guidewire Integration](#18-future-guidewire-integration)

---

## 1. System Overview

### What It Does

The system provides a complete end-to-end insurance workflow through conversational AI:

```
Customer Message → Entity Extraction → LOB Classification → Form Assignment
    → Gap Analysis → Field Mapping → Validation → PDF Filling
    → Quote Request → Carrier Matching → Premium Estimation → Quote Comparison
    → Quote Selection → Bind Request → Policy Delivery
```

### Two Execution Modes

| Mode | Entry Point | Use Case |
|------|-------------|----------|
| **Conversational Agent** | `cli.py` / `api.py` | Multi-turn chat, step-by-step data collection |
| **Batch Pipeline** | `main.py` / `pipeline.py` | Single-shot: text in → filled forms + gap report out |

### Key Technologies

- **LangGraph** (StateGraph) — Agent orchestration with conditional routing
- **LangChain** (ChatOpenAI, ToolNode) — LLM interface and tool execution
- **Ollama / vLLM** — Local LLM backends (OpenAI-compatible API)
- **PyMuPDF (fitz)** — PDF form reading and filling
- **FastAPI** — REST API backend
- **Python 3.12** + **uv** package manager

---

## 2. Project Structure

```
Custom_model_fa_pf/                     # 8,812 lines across 32 source files
├── agent/                              # LangGraph agent core (2,530 lines)
│   ├── __init__.py
│   ├── _llm_provider.py       (57)    # LLM/VLM engine factory
│   ├── carrier_matcher.py    (202)    # Rules-based carrier eligibility
│   ├── confidence.py         (115)    # Confidence scoring + review routing
│   ├── graph.py              (272)    # StateGraph definition + compilation
│   ├── nodes.py              (787)    # All node functions (9 nodes)
│   ├── premium_estimator.py  (353)    # Factor-based premium rating
│   ├── prompts.py            (263)    # System prompts + context builders
│   ├── quote_builder.py      (158)    # QuoteRequest assembly
│   ├── state.py              (103)    # IntakeState + IntakePhase enum
│   └── tools.py              (816)    # 16 LangChain tools
│
├── field_maps/                         # Static field mapping per form
│   ├── form_125.py                    # ACORD 125 field mappings
│   ├── form_127.py                    # ACORD 127 field mappings
│   ├── form_137.py                    # ACORD 137 field mappings
│   └── form_163.py                    # ACORD 163 field mappings
│
├── form_templates/                     # Blank PDF templates
│   ├── acord_125_blank.pdf
│   ├── acord_127_blank.pdf
│   ├── acord_137_blank.pdf
│   └── acord_163_blank.pdf
│
├── tests/                              # 5,948 lines, 399 tests, 25 files
│
├── main.py               (107)        # CLI entry for batch pipeline
├── cli.py                 (585)        # Interactive chat REPL
├── api.py                 (491)        # FastAPI REST backend
├── config.py               (39)        # All configuration constants
├── pipeline.py            (293)        # Batch pipeline orchestrator
├── entity_schema.py       (601)        # Dataclass hierarchy (CustomerSubmission)
├── entity_extractor.py     (70)        # LLM entity extraction
├── lob_classifier.py       (77)        # LOB classification
├── lob_rules.py           (224)        # LOB definitions & required fields
├── form_assigner.py        (84)        # LOB → form assignment
├── form_reader.py         (378)        # PDF widget reader → FormCatalog
├── field_mapper.py         (90)        # Static entity → form mapping
├── llm_field_mapper.py    (893)        # 3-phase field mapping (regex/index/LLM)
├── gap_analyzer.py        (355)        # Missing field analysis
├── input_parser.py        (230)        # Email/chat/raw text parser
├── validation_engine.py   (402)        # Field validation (VIN, DL, FEIN, etc.)
├── pdf_filler.py          (169)        # PyMuPDF form filling
├── session.py             (151)        # Session lifecycle management
├── visual_guide.py         (86)        # CLI display helpers
└── prompts.py             (359)        # Batch pipeline prompts (not agent)
```

---

## 3. LangGraph Agent Architecture

### Graph Topology

```
                         ┌──────────────────────────────────┐
                         │              START                │
                         └──────────┬───────────────────────┘
                                    │ _route_entry()
                        ┌───────────┼───────────────┐
                        ▼           ▼               ▼
                     [greet]   [maybe_summarize]  [review]
                        │           │               │
                        ▼           │ _should_       ▼
                       END          │  summarize()  END
                             ┌──────┴──────┐
                             ▼             ▼
                        [summarize]     [agent]◄──────────────────┐
                             │             │                      │
                             └─────►       │ _should_use_tools()  │
                                    ┌──────┼──────┐               │
                                    ▼      ▼      ▼               │
                                 [tools] [reflect] END            │
                                    │      │                      │
                                    ▼      │ _route_after_        │
                              [process_    │  reflect()           │
                               tools]      ├──────┐               │
                                    │      ▼      ▼               │
                                    │  "revise"  "pass"           │
                                    │    → agent  → check_gaps    │
                                    │                │            │
                                    └────────►       │ route_     │
                                              ┌──────┤  after_    │
                                              ▼      ▼  gaps()   │
                                          [validate] [review]     │
                                              │      │            │
                                              ▼      ▼            │
                                             END    END           │
                                                                  │
                                         "respond" → END          │
                                                                  │
                          tools → process_tools ──────────────────┘
```

### Nodes (10)

| Node | Function | Purpose |
|------|----------|---------|
| `greet` | `greet_node()` | Welcome message, set phase to APPLICANT_INFO |
| `agent` | `_agent_node()` | Core LLM call with tools bound, retry w/ backoff |
| `tools` | `ToolNode(tools)` | LangGraph built-in tool executor |
| `process_tools` | `process_tool_results_node()` | Parse ToolMessages → update form_state, entities, LOBs, quotes |
| `reflect` | `reflect_node()` | Self-critique agent response, parse text-based tool calls |
| `maybe_summarize` | pass-through | Routing checkpoint for summarization decision |
| `summarize` | `summarize_node()` | Compress old messages, prune via RemoveMessage |
| `check_gaps` | `check_gaps_node()` | Build confidence_scores, run ReviewRouter |
| `validate` | `validate_node()` | Run validation rules, apply auto-corrections |
| `review` | `review_node()` | Generate data summary for customer confirmation |

### Routing Functions (5)

| Function | From | Routes To | Logic |
|----------|------|-----------|-------|
| `_route_entry` | START | greet / maybe_summarize / review | turn=0 → greet; turn>=MAX → review; else → maybe_summarize |
| `_should_summarize` | maybe_summarize | summarize / agent | turn >= 20 AND messages >= 20 → summarize |
| `_should_use_tools` | agent | tools / reflect / END | Has tool_calls? → tools (if under limit); text response? → reflect |
| `_route_after_reflect` | reflect | agent / check_gaps | REVISION NEEDED + reflect_count < 1 → revise (agent); else → pass (check_gaps) |
| `route_after_gaps` | check_gaps | respond(END) / validate / review | Post-intake phases → respond; complete → review; enough data → validate/review |

### Graph Compilation

```python
# Without checkpointing (testing/batch)
graph = create_graph()

# With MemorySaver checkpointing (multi-turn CLI/API)
agent = create_agent(checkpointer=MemorySaver())
```

---

## 4. State Management

### IntakePhase Enum (11 phases)

```python
class IntakePhase(str, Enum):
    # Data collection (phases 1-7)
    GREETING        = "greeting"          # Initial welcome
    APPLICANT_INFO  = "applicant_info"    # Business name, entity type, address
    POLICY_DETAILS  = "policy_details"    # Insurance types, dates
    BUSINESS_INFO   = "business_info"     # Operations, revenue, employees
    FORM_SPECIFIC   = "form_specific"     # Vehicles, drivers, locations
    REVIEW          = "review"            # Summary for confirmation
    COMPLETE        = "complete"          # Data collection done

    # Quoting & placement (phase 6-7 in prompt)
    QUOTING         = "quoting"           # Building quotes
    QUOTE_SELECTION = "quote_selection"   # Customer choosing

    # Binding & delivery (phase 8 in prompt)
    BIND_REQUEST    = "bind_request"      # Submitting to carrier
    POLICY_DELIVERY = "policy_delivery"   # Final steps
```

### IntakeState (TypedDict)

```python
class IntakeState(TypedDict):
    # Conversation
    messages: Annotated[list[BaseMessage], add_messages]  # Auto-appending reducer
    summary: str                    # Compressed older conversation history

    # Intake progress
    phase: str                      # IntakePhase value
    form_state: dict                # field_name → {value, confidence, source, status}
    entities: dict                  # CustomerSubmission.to_dict()

    # Forms
    lobs: list                      # ["commercial_auto", "general_liability", ...]
    assigned_forms: list            # ["125", "127", "137", ...]

    # Quality
    confidence_scores: dict         # field_name → float (0.0-1.0)
    validation_issues: list         # [{field_name, value, rule, severity, message}]

    # Documents
    uploaded_documents: list        # [{file_path, document_type, fields_count, timestamp}]

    # Quoting & placement
    quote_request: dict             # Structured quote request payload
    carrier_matches: list           # [{carrier_id, name, eligible, reasoning, ...}]
    quotes: list                    # [{carrier_id, premiums, coverages, payment_options}]
    selected_quote: dict            # The quote the customer chose

    # Binding
    bind_request: dict              # {bind_request_id, status, carrier, premium, ...}

    # Session metadata
    session_id: str
    conversation_turn: int
    error_count: int
    reflect_count: int              # Max 1 revision per turn
```

### State Hydration (process_tool_results_node)

Tool results are automatically parsed and merged into state:

| Tool Result Pattern | State Field Updated | Phase Transition |
|---------------------|---------------------|------------------|
| `save_field` → `{status: "saved", field_name, value}` | `form_state[field_name]` | — |
| `extract_entities` → `{business, drivers, vehicles}` | `entities` + `form_state` (flattened) | — |
| `classify_lobs` → `[{lob_id, confidence}]` | `lobs` (deduplicated merge) | — |
| `assign_forms` → `[{form_number, purpose}]` | `assigned_forms` (deduplicated merge) | — |
| `process_document` → `{fields, document_type}` | `form_state` + `uploaded_documents` | — |
| `fill_forms` → `{status: "filled", output_dir}` | logged only | — |
| `build_quote_request` → `{request_id, risk_profile}` | `quote_request` | → QUOTING |
| `generate_quotes` → `[{quote_id, total_annual_premium}]` | `quotes` | → QUOTE_SELECTION |
| `select_quote` → `{status: "selected", quote_id}` | `selected_quote` | → BIND_REQUEST |
| `submit_bind_request` → `{status: "submitted", bind_request_id}` | `bind_request` | → POLICY_DELIVERY |

---

## 5. Agent Tools

### Data Collection Tools (10)

| # | Tool | Args | Returns | Delegates To |
|---|------|------|---------|-------------|
| 1 | `save_field` | field_name, value, source | `{status, field_name, value, confidence}` | `ConfidenceScorer` |
| 2 | `validate_fields` | fields_json | `{error_count, warning_count, issues[], corrected_values}` | `validation_engine.validate()` |
| 3 | `classify_lobs` | text | `[{lob_id, confidence, reasoning}]` | `lob_classifier.classify()` |
| 4 | `extract_entities` | text | `CustomerSubmission.to_dict()` | `entity_extractor.extract()` |
| 5 | `assign_forms` | lobs_json | `[{form_number, purpose, schema_available, lobs}]` | `form_assigner.assign()` |
| 6 | `read_form` | pdf_path | `{form_number, total_fields, sections[]}` | `form_reader.read_pdf_form()` |
| 7 | `map_fields` | form_number, entities_json | `{total_mapped, phase1/2/3_count, mappings}` | `llm_field_mapper.map_fields()` |
| 8 | `analyze_gaps` | entities_json, forms_json, values_json | `{missing_critical[], completeness_pct, follow_up_questions[]}` | `gap_analyzer.analyze()` |
| 9 | `process_document` | file_path | `{document_type, fields{}, summary}` | VLM direct extraction |
| 10 | `fill_forms` | entities_json, forms_json | `{status, output_dir, total_fields_filled, fill_results[]}` | Full mapping→validation→fill pipeline |

### Quoting & Placement Tools (6)

| # | Tool | Args | Returns | Delegates To |
|---|------|------|---------|-------------|
| 11 | `build_quote_request` | entities_json, lobs_json, forms_json | `QuoteRequest.to_dict()` | `quote_builder.build_quote_request()` |
| 12 | `match_carriers` | quote_request_json | `[CarrierMatch.to_dict()]` | `carrier_matcher.match_carriers()` |
| 13 | `generate_quotes` | matches_json, lobs_json, profile_json | `[Quote.to_dict()]` | `premium_estimator.generate_quotes_for_matches()` |
| 14 | `compare_quotes` | quotes_json | `{cheapest, most_coverage, quotes[], disclaimer}` | In-tool formatting |
| 15 | `select_quote` | quote_id, payment_plan | `{status: "selected", quote_id, payment_plan}` | In-tool |
| 16 | `submit_bind_request` | quote_id, carrier, premium, plan, ack | `{bind_request_id, bind_status, next_steps[]}` | In-tool + file save |

---

## 6. Node Functions

### greet_node

Outputs a welcome message and advances phase from GREETING → APPLICANT_INFO.

### _agent_node (in graph.py)

The core LLM call:
1. Creates `ChatOpenAI` pointing at Ollama/vLLM
2. Binds all 16 tools via `.bind_tools()`
3. Builds system message with form state, summary, phase, quotes, bind status
4. Prepends system message to conversation
5. Calls LLM with exponential backoff (max 3 retries)
6. Returns AI response + incremented turn + reset reflect_count

### process_tool_results_node

Scans ToolMessages in reverse to extract and merge results:
- **List results** (classify_lobs, assign_forms, carrier matches, quotes) — handled first with dedup merge
- **Dict results** (save_field, extract_entities, fill_forms, quote_request, select_quote, bind_request) — pattern-matched by key presence
- **Text-based tool calls** — regex-parses `save_field("name", "value")` from AIMessage content (fallback for small models)
- **Phase transitions** — automatically advances phase based on tool results

### reflect_node

1. Parses any text-based save_field calls (small model fallback)
2. Calls LLM with REFLECTION_PROMPT to critique the agent's response
3. Checks: hallucination, multiple questions, off-topic, incorrect confirmations, fabricated premiums
4. If "revise" verdict → injects REVISION NEEDED SystemMessage, increments reflect_count
5. If "pass" verdict → lets response through
6. Max 1 revision per turn (enforced by `_route_after_reflect`)

### check_gaps_node

Builds `confidence_scores` from confirmed form_state fields, runs `ReviewRouter.route()` to flag low-confidence fields for human review.

### summarize_node

Triggers when turn >= 20 AND messages >= 20:
1. Keeps last 6 messages for immediate context
2. Summarizes older messages via LLM
3. Uses `RemoveMessage` to prune old messages from the `add_messages` reducer

### validate_node

Runs `validation_engine.validate()` on all confirmed fields. Applies auto-corrections (phone normalization, FEIN formatting) back to form_state.

### review_node

Generates a formatted summary of all confirmed fields + validation notes. Sets phase to COMPLETE.

---

## 7. Prompt System

### INTAKE_SYSTEM_PROMPT

The main system prompt (~140 lines) covering:
- **Identity**: Commercial insurance intake and placement specialist
- **Core Rules**: One question at a time, no hallucination, confirm critical data
- **8 Phases**: Applicant → Policy → Business → Form-Specific → Review → Quoting → Selection → Binding
- **Anti-Hallucination Rules**: Never invent data, never fabricate premiums
- **Tool Usage**: Bulk input mode (extract_entities) vs. conversational mode (save_field)
- **Quoting Tool Sequence**: build_quote_request → match_carriers → generate_quotes → compare_quotes
- **Binding Tool Sequence**: select_quote → submit_bind_request
- **Document Processing**: Per-document-type extraction guidance
- **Form Filling**: When and how to call fill_forms

### build_system_message()

Assembles the full system message by concatenating:
```
INTAKE_SYSTEM_PROMPT
+ CURRENT FORM STATE (confirmed/pending/empty fields)
+ CURRENT PHASE
+ AVAILABLE QUOTES (if in quoting phase)
+ SELECTED QUOTE (if quote chosen)
+ BIND STATUS (if bind submitted)
+ CONVERSATION SUMMARY (if summarized)
```

### REFLECTION_PROMPT

Critiques the agent's response against 6 checks:
1. Hallucinated data
2. Multiple questions in one response
3. Off-topic content
4. Incorrect confirmations
5. Missing tool calls
6. Fabricated premiums

Returns `{"verdict": "pass"}` or `{"verdict": "revise", "issues": [...], "suggestion": "..."}`.

### SUMMARIZE_PROMPT

Compresses conversation history into a factual summary under 500 words, preserving quoting/binding status.

---

## 8. Confidence & Review Routing

### Source Weights

```python
SOURCE_WEIGHTS = {
    "user_stated":         0.95,
    "user_confirmed":      1.00,
    "llm_inferred":        0.60,
    "validated_external":  0.98,
    "defaulted":           0.50,
    "ocr_extracted":       0.80,
    "document_ocr":        0.85,
    "extracted":           0.85,    # From extract_entities
}
```

### ConfidenceScorer

```python
score = SOURCE_WEIGHTS[source]
if validation_passed:  score += 0.10  (capped at 1.0)
if validation_failed:  score -= 0.30  (floor at 0.10)
```

### ConfidenceLevel Thresholds

| Level | Score Range |
|-------|-------------|
| HIGH | >= 0.90 |
| MEDIUM | 0.70 - 0.89 |
| LOW | 0.50 - 0.69 |
| VERY_LOW | < 0.50 |

### ReviewRouter

Thresholds: `auto_threshold=0.90`, `review_threshold=0.70`

| Decision | Condition |
|----------|-----------|
| `auto_process` | All fields >= 0.70 |
| `human_review_required` | Any critical field < 0.70 |
| `human_review_optional` | Non-critical fields < 0.70 |

### Critical Fields

```python
CRITICAL_FIELDS = {
    "business_name", "business.business_name",
    "policy.effective_date", "policy.expiration_date",
    "vehicles[].vin", "vin",
    "tax_id", "business.tax_id", "fein",
    "drivers[].license_number", "license_number",
    "coverage.liability_limit",
}
```

---

## 9. Entity Schema & Flattening

### CustomerSubmission Hierarchy

```
CustomerSubmission
├── business: BusinessInfo
│   ├── business_name, dba, entity_type, tax_id, naics, sic
│   ├── mailing_address: Address (line_one, line_two, city, state, zip_code)
│   ├── contacts: List[Contact] (full_name, phone, email, role)
│   ├── annual_revenue, employee_count, years_in_business, annual_payroll
│   └── nature_of_business, operations_description, website
├── producer: ProducerInfo
│   ├── agency_name, contact_name, phone, fax, email
│   ├── mailing_address: Address
│   └── producer_code, license_number
├── policy: PolicyInfo
│   ├── policy_number, effective_date, expiration_date, status
│   └── billing_plan, payment_plan, deposit_amount, estimated_premium
├── vehicles: List[VehicleInfo]
│   ├── vin, year, make, model, body_type, gvw, cost_new
│   ├── garaging_address: Address
│   └── use_type, radius_of_travel, territory, class_code
├── drivers: List[DriverInfo]
│   ├── full_name, first_name, last_name, dob, sex, marital_status
│   ├── license_number, license_state, years_experience, hire_date
│   └── mailing_address: Address
├── coverages: List[CoverageRequest]
│   └── lob, coverage_type, limit, deductible, premium
├── locations: List[LocationInfo]
│   └── address, building_area, construction_type, year_built
├── loss_history: List[LossHistoryEntry]
│   └── date, lob, description, amount, claim_status
├── prior_insurance: List[PriorInsurance]
│   └── carrier_name, policy_number, effective_date, premium
├── additional_interests: List[AdditionalInterest]
│   └── name, address, interest_type, certificate_required
└── cyber_info: Optional[CyberInfo]
    └── annual_revenue, records_count, has_encryption, has_mfa
```

### Entity Flattening (flatten_entities_to_form_state)

Converts nested `CustomerSubmission.to_dict()` output into flat `form_state` entries:

```
business.business_name      → business_name
business.mailing_address.city → mailing_city
business.tax_id             → fein
vehicles[0].vin             → vehicle_1_vin
vehicles[1].make            → vehicle_2_make
drivers[0].dob              → driver_1_dob
drivers[2].license_number   → driver_3_license_number
prior_insurance[0].carrier  → prior_carrier_1_carrier
policy.effective_date       → effective_date
```

Each entry: `{value: str, confidence: float, source: "extracted", status: "confirmed"}`

User-confirmed values are never overwritten during flattening.

---

## 10. Data Collection Pipeline

### Bulk Input Mode (3+ data points)

```
Customer paragraph/email
    │
    ▼
extract_entities(text) ──► entities dict ──► auto-flatten to form_state
    │
    ▼
classify_lobs(text) ──► LOB list ──► state.lobs
    │
    ▼
assign_forms(lobs) ──► form assignments ──► state.assigned_forms
    │
    ▼
analyze_gaps(entities, forms, fields) ──► missing fields list
    │
    ▼
Agent asks ONLY about missing fields
```

### Conversational Mode (1-2 facts per message)

```
Customer says "My business is Acme LLC"
    │
    ▼
Agent calls save_field("business_name", "Acme LLC", "user_stated")
    │
    ▼
process_tool_results_node updates form_state
    │
    ▼
Agent asks next question based on phase
```

### LOB Classification

7 supported LOBs:
- `commercial_auto` — Vehicles, drivers, fleet
- `general_liability` — Business operations liability
- `workers_compensation` — Employee injury coverage
- `commercial_property` — Building, contents, equipment
- `commercial_umbrella` — Excess liability
- `bop` — Business Owner's Policy (GL + property bundle)
- `cyber` — Data breach, cyber liability

### Form Assignment

LOB → ACORD form mapping:
- Form 125: Always assigned (base commercial application)
- Form 127: commercial_auto
- Form 137: commercial_auto (additional vehicles/drivers)
- Form 163: commercial_umbrella

### 3-Phase Field Mapping

```
Phase 1: Deterministic Regex (80+ patterns, instant)
    NamedInsured_FullName_A$ → business.business_name
    Vehicle_VIN_A$           → vehicles[0].vin
    │
Phase 2: Suffix-Indexed Arrays (drivers/vehicles, instant)
    Driver_LastName_B → drivers[1].last_name  (B = index 1)
    Vehicle_Year_C   → vehicles[2].year       (C = index 2)
    │
Phase 3: LLM Batch (remaining unmapped fields, ~5 API calls)
    Send batches of unmapped field names → LLM suggests entity paths
```

### Gap Analysis

`gap_analyzer.analyze()` checks:
1. Required fields per LOB (from `REQUIRED_FIELDS_BY_LOB`)
2. Critical vs. important classification
3. Generates grouped follow-up questions (max 5 critical, max 5 important)
4. Calculates completeness percentage
5. Progressive disclosure — critical gaps first

---

## 11. Quoting & Placement Pipeline

### Overview

```
form_state + entities + LOBs
    │
    ▼
build_quote_request() ──► QuoteRequest (with RiskProfile)
    │                          ↑ phase → QUOTING
    ▼
match_carriers() ──► CarrierMatch[] (eligible/ineligible with reasoning)
    │
    ▼
generate_quotes() ──► Quote[] (premiums per LOB, payment options)
    │                     ↑ phase → QUOTE_SELECTION
    ▼
compare_quotes() ──► Formatted comparison (cheapest, most coverage)
    │
    ▼
Customer selects ──► select_quote() ──► phase → BIND_REQUEST
    │
    ▼
Customer confirms ──► submit_bind_request() ──► phase → POLICY_DELIVERY
```

### QuoteRequest & RiskProfile

```python
@dataclass
class RiskProfile:
    industry: str               # Nature of business
    naics: str                  # NAICS code
    sic: str                    # SIC code
    years_in_business: int
    employee_count: int
    annual_revenue: float
    annual_payroll: float
    entity_type: str            # LLC, corporation, etc.
    state: str                  # Primary state
    fleet_size: int             # Number of vehicles
    driver_count: int
    total_loss_amount: float    # Total historical losses
    loss_count: int
    prior_carrier: str
    prior_premium: float

@dataclass
class QuoteRequest:
    request_id: str             # "QR-YYYYMMDDHHMMSS"
    business_name: str
    entity_type: str
    state: str
    lobs: List[str]
    assigned_forms: List[str]
    risk_profile: RiskProfile
    vehicles: List[dict]
    drivers: List[dict]
    coverages: List[dict]
    locations: List[dict]
    loss_history: List[dict]
    prior_insurance: List[dict]
    effective_date: str
    expiration_date: str
```

### Carrier Matching (6 carriers)

| Carrier | LOBs | Rules |
|---------|------|-------|
| **Progressive Commercial** | auto only | Max 50 vehicles |
| **The Hartford** | auto, GL, WC, property, BOP | Min 2 years in business |
| **Travelers** | auto, GL, WC, umbrella | Min 3 years, larger fleets |
| **EMC Insurance** | WC, GL, property, BOP | WC specialist, excludes CA/NY/FL |
| **National General** | auto only | Small fleet (max 25 vehicles) |
| **Berkshire Hathaway GUARD** | GL, WC, property, BOP, umbrella, cyber | No commercial auto |

Each carrier match includes:
- `eligible: bool`
- `confidence: float` (0.0-1.0)
- `reasoning: str`
- `decline_reasons: list` (if ineligible)

### Premium Estimation

**Base Rates**:
| LOB | Rate | Unit |
|-----|------|------|
| Commercial Auto | $3,500 | Per vehicle |
| General Liability | $1,200 | Per $100K revenue |
| Workers Comp | $8 | Per $100 payroll |
| Commercial Property | $800 | Per location |
| BOP | $2,500 | Flat |
| Umbrella | $1,500 | Flat ($1M) |
| Cyber | $1,200 | Flat |

**Rating Factors** (multiplicative):
- Territory factor (by state: TX=1.00, CA=1.35, NY=1.30, FL=1.25, ...)
- Experience mod (loss ratio: 0→0.85 credit, >0.7→1.30 surcharge)
- Years in business (10+→0.85, new→1.20)
- Fleet factor (50+→0.80, 1-4→1.00)
- Carrier LOB factor (Progressive auto=0.90, Hartford GL=0.92, ...)

**Payment Plans** per quote:
| Plan | Fee | Installments |
|------|-----|-------------|
| Annual | 0% | 1 |
| Semi-annual | +2% | 2 |
| Quarterly | +4% | 4 |
| Monthly | +8% | 12 |

> Note: All premiums are estimates. The carrier matching rules and premium estimator are designed to be replaced with Guidewire API integration.

---

## 12. Form Filling Pipeline

### fill_forms Tool Execution

```
entities_json + assigned_forms_json
    │
    ├─ Guard: require business_name + at least 1 form
    │
    ▼
CustomerSubmission.from_llm_json(entities)
    │
    ▼
llm_field_mapper.map_all(submission, assignments, lobs, llm)
    │  → Returns {form_number: {field_name: value}}
    │
    ▼
validation_engine.validate(fields) per form
    │  → Auto-corrections applied (phone, FEIN formatting)
    │
    ▼
pdf_filler.fill_all(field_values, output_dir)
    │  → Opens blank PDF templates with PyMuPDF
    │  → Fills widgets (text fields, checkboxes)
    │  → Saves filled PDFs
    │
    ▼
Saves artifacts: entities.json, field_mappings.json, validation.json
    │
    ▼
Returns: {status, output_dir, total_fields_filled, fill_results[]}
```

### PDF Filler (PyMuPDF)

For each widget in the PDF:
1. Skip read-only fields (`field_flags & 1`)
2. Skip bad rects (empty, zero width/height)
3. Match widget field name to field_values dict
4. Fill: checkbox (True/False) or text (string value)
5. Call `widget.update()` to commit
6. Save with incremental changes

### Supported Forms

| Form | Purpose | Template |
|------|---------|----------|
| ACORD 125 | Commercial Insurance Application | `acord_125_blank.pdf` |
| ACORD 127 | Commercial Auto Section | `acord_127_blank.pdf` |
| ACORD 137 | Commercial Auto Additional | `acord_137_blank.pdf` |
| ACORD 163 | Umbrella/Excess Liability | `acord_163_blank.pdf` |

---

## 13. Validation Engine

### Validation Rules

| Rule | Fields | Check |
|------|--------|-------|
| VIN Checksum | `*VIN*`, `*vin*` | ISO 3779 check digit (17 chars) |
| Driver's License | `*license*`, `*dl*` | State-specific regex patterns (50 states + DC) |
| FEIN | `*FEIN*`, `*TaxIdentifier*` | XX-XXXXXXX format (9 digits) |
| Date Format | `*Date*`, `*date*` | MM/DD/YYYY parseable |
| Date Ordering | effective/expiration pairs | effective < expiration |
| State/ZIP | state + zip pairs | State matches ZIP prefix table |
| Phone | `*Phone*`, `*phone*` | 10-digit US number |
| Field Completeness | All required fields | Value is non-empty |

### Auto-Corrections

| Type | Before | After |
|------|--------|-------|
| Phone | `2145550187` | `(214) 555-0187` |
| FEIN | `751234567` | `75-1234567` |
| Date | `2026-03-01` | `03/01/2026` |

### ValidationResult

```python
@dataclass
class ValidationResult:
    issues: List[ValidationIssue]       # All issues found
    corrected_values: Dict[str, str]    # Auto-corrected values
    auto_corrections: Dict[str, str]    # {field: correction_description}
    total_fields: int
    valid_fields: int
    error_count: int
    warning_count: int
    info_count: int
```

---

## 14. Entry Points

### CLI (`cli.py`)

Interactive multi-turn chat REPL with commands:

| Command | Action |
|---------|--------|
| `/quit`, `/exit` | Exit chat |
| `/status` | Full session status (phase, fields, LOBs, forms, quotes, bind) |
| `/fields` | Confirmed fields grouped by category |
| `/forms` | Assigned forms + mapped field counts |
| `/upload <path>` | Process document (PDF/image) via VLM |
| `/finalize` | Trigger fill_forms |
| `/quote` | Start quoting pipeline |
| `/reset` | New session |

Phase descriptions displayed in status:
```python
PHASE_DESCRIPTIONS = {
    "greeting": "Getting started",
    "applicant_info": "Collecting applicant information",
    "policy_details": "Gathering policy details",
    "business_info": "Learning about the business",
    "form_specific": "Collecting form-specific details",
    "review": "Reviewing collected information",
    "complete": "Data collection complete",
    "quoting": "Generating insurance quotes",
    "quote_selection": "Comparing and selecting quotes",
    "bind_request": "Processing bind request",
    "policy_delivery": "Policy delivery in progress",
}
```

### API (`api.py`)

FastAPI REST backend:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/health` | GET | Health check + session count |
| `/api/v1/submit` | POST | Start new session → full pipeline |
| `/api/v1/session/{id}/message` | POST | Follow-up message |
| `/api/v1/session/{id}/status` | GET | Session state |
| `/api/v1/session/{id}/result` | GET | Final: forms + entities + gaps |
| `/api/v1/session/{id}/finalize` | POST | Fill PDFs |
| `/api/v1/session/{id}/validation` | GET | Validation results per form |
| `/api/v1/session/{id}/correct` | POST | Apply corrections, re-validate |
| `/api/v1/submit-with-pdf` | POST | Submit text + custom PDF |

### Batch Pipeline (`main.py` → `pipeline.py`)

Single-shot processing:
```
text → LOB classify → extract entities → assign forms
     → field mapping → validation → gap analysis → fill PDFs
```

---

## 15. Configuration

### `config.py`

```python
# LLM backend
LLM_BACKEND = "ollama"                              # "vllm" or "ollama"
VLLM_BASE_URL = "http://localhost:8000/v1"
OLLAMA_OPENAI_URL = "http://localhost:11434/v1"

# Agent models
AGENT_MODEL = "qwen2.5:7b"                          # Text LLM
AGENT_VLM_MODEL = "qwen3-vl:8b"                     # Vision LLM
AGENT_TEMPERATURE = 0.3
AGENT_MAX_TOKENS = 4096

# Conversation limits
MAX_CONVERSATION_TURNS = 30
MAX_TOOL_CALLS_PER_TURN = 5                          # Round-trip count
SUMMARIZE_AFTER_TURNS = 20

# Paths
SCHEMAS_DIR = ROOT / "schemas"                       # 125.json, 127.json, etc.
FORM_TEMPLATES_DIR = MODULE_DIR / "form_templates"   # Blank PDFs
OUTPUT_DIR = MODULE_DIR / "output"                   # Filled PDFs + artifacts

# File support
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}
SUPPORTED_DOC_EXTENSIONS = {".pdf"}
```

---

## 16. Testing

### Summary

- **399 tests** across **25 test files** (5,948 lines)
- Framework: `pytest` with mocking (`unittest.mock`)
- All tests run offline (no LLM/Ollama required) via mocks

### Test Coverage Map

| Test File | Tests | Focus |
|-----------|-------|-------|
| `test_agent_state.py` | 10 | IntakePhase enum, initial state, phase ordering |
| `test_agent_graph.py` | 20 | Graph routing, node execution, edge conditions |
| `test_agent_tools.py` | 8 | All 16 tools, JSON schemas, error handling |
| `test_agent_prompts.py` | 26 | System prompt content, build_system_message params |
| `test_agent_config.py` | 6 | Agent config, LLM backend selection |
| `test_confidence.py` | 17 | ConfidenceScorer, SOURCE_WEIGHTS, ReviewRouter |
| `test_conversation_e2e.py` | 19 | Multi-turn conversation, tool calling, state flow |
| `test_bulk_input_e2e.py` | 14 | Bulk extraction, entity flattening, gap detection |
| `test_quoting_pipeline.py` | 34 | Quote builder, carrier matcher, premium estimator |
| `test_entity_schema.py` | 15 | CustomerSubmission serialization, from_llm_json |
| `test_field_mapper.py` | 25 | Static field mapping (all 4 forms) |
| `test_llm_field_mapper.py` | 48 | 3-phase mapping (regex, indexed, LLM batch) |
| `test_form_assigner.py` | 10 | LOB → form assignment |
| `test_form_reader.py` | 29 | PDF widget reading, FormCatalog |
| `test_gap_analyzer.py` | 13 | Gap analysis, follow-up questions |
| `test_validation_engine.py` | 40 | VIN, DL, FEIN, dates, phone, state/ZIP |
| `test_input_parser.py` | 12 | Email/chat/raw parsing |
| `test_lob_rules.py` | 11 | LOB definitions, required fields |
| `test_pdf_filler.py` | 5 | PDF filling, field stats |
| `test_session.py` | 13 | Session lifecycle |
| `test_api.py` | 11 | FastAPI endpoints |
| `test_cli.py` | 6 | CLI commands |
| `test_visual_guide.py` | 4 | Display helpers |
| `test_pipeline_e2e.py` | * | Full batch pipeline |
| `test_accuracy_e2e.py` | * | Accuracy metrics |

### Running Tests

```bash
cd /home/inevoai/Development/Accord-Model-Building

# All tests (fast, no LLM needed)
.venv/bin/python -m pytest Custom_model_fa_pf/tests/ -x -q \
  --ignore=Custom_model_fa_pf/tests/test_pipeline_e2e.py \
  --ignore=Custom_model_fa_pf/tests/test_accuracy_e2e.py

# Specific module
.venv/bin/python -m pytest Custom_model_fa_pf/tests/test_quoting_pipeline.py -v

# With coverage
.venv/bin/python -m pytest Custom_model_fa_pf/tests/ --cov=Custom_model_fa_pf
```

---

## 17. Design Patterns

### Pattern 1: LangGraph State Machine
StateGraph with 10 nodes, 5 conditional routing functions, `add_messages` reducer for automatic message list concatenation, and MemorySaver checkpointer for multi-turn persistence.

### Pattern 2: Tool Result Hydration
ToolMessages from LLM tool calls are scanned in reverse order. Results are parsed as JSON and merged into the appropriate state fields. Handles both proper tool calling and text-based fallback parsing.

### Pattern 3: Entity Flattening
Nested `CustomerSubmission` dicts are converted to flat `form_state` entries with indexed arrays (`vehicle_1_vin`, `driver_2_dob`). Confidence scores are applied per field based on source. User-confirmed values are never overwritten.

### Pattern 4: Reflection & Revision
After the agent generates a text response, `reflect_node` self-critiques via a separate LLM call. Checks for hallucination, multiple questions, off-topic content. Max 1 revision per turn prevents infinite loops.

### Pattern 5: Progressive Disclosure
Gap analysis groups missing fields and generates natural-language questions. Critical gaps first (max 5), then important (max 5). Prevents overwhelming the customer.

### Pattern 6: Confidence-Driven Routing
Fields are scored by source reliability. Low-confidence critical fields trigger mandatory human review. Non-critical low-confidence fields trigger optional review. High-confidence fields pass automatically.

### Pattern 7: Memory Management
Conversation is summarized after 20 turns + 20 messages. Last 6 messages retained for immediate context. Old messages pruned via `RemoveMessage`. Summary injected into system prompt.

### Pattern 8: Dual Execution Modes
Same underlying modules (entity_extractor, form_assigner, field_mapper, etc.) power both the batch pipeline and the conversational agent. The agent wraps them as LangChain tools; the pipeline calls them directly.

### Pattern 9: Graceful Degradation
LLM calls include exponential backoff (3 retries). If all retries fail, a friendly error message is returned. If reflection fails, the response passes through unchanged. If VLM extraction fails on a page, remaining pages still process.

---

## 18. Future: Guidewire Integration

The quoting and placement pipeline is designed with replaceable components:

### Current (Dummy)
```
carrier_matcher.py    → Static rules dict, in-memory matching
premium_estimator.py  → Factor-based rating with hardcoded base rates
submit_bind_request   → Saves JSON file locally
```

### Future (Guidewire)
```
carrier_matcher.py    → Guidewire PolicyCenter carrier appetite API
premium_estimator.py  → Guidewire Rating Engine API
submit_bind_request   → Guidewire PolicyCenter submission API
```

### Integration Points

1. **`match_carriers` tool** → Replace `CARRIER_RULES` dict with Guidewire carrier appetite query
2. **`generate_quotes` tool** → Replace `generate_quote()` with Guidewire Rating Engine call
3. **`submit_bind_request` tool** → Replace local JSON save with Guidewire PolicyCenter submission
4. **`select_quote` tool** → Optionally integrate with Guidewire quote selection workflow
5. **RiskProfile dataclass** → Map to Guidewire risk model fields

The `QuoteRequest`, `CarrierMatch`, and `Quote` dataclasses serve as the interface boundary. The agent tools parse JSON in and return JSON out — swapping the backend implementation requires no changes to the agent graph, prompts, or state management.
