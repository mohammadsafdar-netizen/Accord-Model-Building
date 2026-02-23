# ACORD Insurance Intake Agent — Production Design

**Date:** 2026-02-23
**Status:** Design
**Author:** AI-assisted design session

---

## 1. Vision

Build a **conversational AI agent** for an InsurTech company that:
- **Initiates and drives** natural-language insurance intake conversations
- Accepts input via **email and message channels** (CLI for testing)
- Works with **any PDF** — both fillable AcroForm and scanned documents
- Fills ACORD forms from conversational data with **99%+ accuracy** (no OCR needed for new submissions)
- Extracts from scanned ACORD forms at **81%+ accuracy** using a finetuned VLM
- Produces a **summary + visual form guide** showing customers where their data goes
- Handles customers who **may not know insurance terminology**

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    INTAKE CHANNELS                          │
│   CLI  │  Email API (future)  │  Message API (future)      │
└────┬────────────┬──────────────────┬────────────────────────┘
     │            │                  │
     ▼            ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  INPUT NORMALIZER                           │
│   Strips signatures, headers, HTML; detects language        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              LANGGRAPH AGENT (StateGraph)                   │
│                                                             │
│  State: IntakeState (messages, form_state, phase,           │
│         entities, confidence_scores, session_metadata)      │
│                                                             │
│  ┌──────┐    ┌────────────┐    ┌───────────┐               │
│  │greet │───▶│ understand │───▶│check_gaps │               │
│  └──────┘    └────────────┘    └─────┬─────┘               │
│                                      │                      │
│                    ┌─────────────────┼──────────────┐       │
│                    ▼                 ▼              ▼       │
│              ┌───────────┐   ┌───────────┐  ┌──────────┐   │
│              │ask_question│   │ validate  │  │fill_forms│   │
│              └─────┬─────┘   └─────┬─────┘  └────┬─────┘   │
│                    │               │              │          │
│                    └───────────────┴──────┬───────┘          │
│                                          ▼                  │
│                                    ┌──────────┐             │
│                                    │  review  │             │
│                                    └────┬─────┘             │
│                                         ▼                   │
│                                    ┌──────────┐             │
│                                    │  guide   │             │
│                                    └──────────┘             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    AGENT TOOLS                              │
│                                                             │
│  extract_entities   classify_lobs    assign_forms           │
│  read_form          map_fields       validate_fields        │
│  analyze_gaps       scan_document    save_field             │
│  generate_guide                                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  LLM BACKEND (vLLM)                         │
│                                                             │
│  Qwen3-VL-8B (finetuned) — text + vision + tool calling    │
│  Port 8000, hermes parser, prefix caching, JSON Schema      │
│  RTX 3090 24GB, ~17.5GB model + KV cache                   │
└─────────────────────────────────────────────────────────────┘
```

## 3. LLM Backend — vLLM

### Why vLLM over Ollama
- **19x throughput** at peak (793 vs 41 tok/s)
- **Tool calling** with `--tool-call-parser hermes` for Qwen models
- **JSON Schema enforcement** via XGrammar (exact field names/types, not just "valid JSON")
- **Prefix caching** — system prompt cached across all requests (huge win for agents)
- **Already installed** — vLLM 0.15.1 in the project venv

### Model Serving Strategy
Single multimodal model — the finetuned Qwen3-VL handles both text reasoning and vision:

```bash
vllm serve /home/inevoai/Development/Accord-Model-Building/finetune/export/merged_full \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.90 \
  --enable-prefix-caching \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --port 8000
```

**Memory budget:** ~17.5GB model + ~4.5GB KV cache on 24GB RTX 3090.

### Fallback: Ollama
Keep Ollama as development fallback (`qwen2.5:7b` for text, `qwen3-vl:8b` for vision). The agent framework abstracts the backend — swap via config.

```python
# config.py
LLM_BACKEND = "vllm"  # or "ollama"
VLLM_BASE_URL = "http://localhost:8000/v1"
OLLAMA_BASE_URL = "http://localhost:11434"
```

## 4. Agent Framework — LangGraph

### State Schema

```python
class IntakePhase(Enum):
    GREETING = "greeting"
    APPLICANT_INFO = "applicant_info"
    POLICY_DETAILS = "policy_details"
    BUSINESS_INFO = "business_info"
    FORM_SPECIFIC = "form_specific"
    REVIEW = "review"
    COMPLETE = "complete"

class IntakeState(TypedDict):
    # Conversation
    messages: Annotated[list[BaseMessage], add_messages]
    summary: str                        # Compressed older history

    # Intake progress
    phase: IntakePhase
    form_state: dict                    # field_name -> {value, confidence, source, status}
    entities: dict                      # Structured extracted entities

    # Forms
    lobs: list[str]                     # Identified lines of business
    assigned_forms: list[str]           # ACORD form numbers
    form_catalogs: dict                 # form_number -> FormCatalog

    # Quality
    confidence_scores: dict[str, float] # field_name -> confidence
    validation_issues: list[dict]       # Active validation problems

    # Session
    session_id: str
    conversation_turn: int
    error_count: int
```

### Graph Structure

```python
workflow = StateGraph(IntakeState)

# Nodes
workflow.add_node("greet", greet_node)              # Welcome + detect intent
workflow.add_node("understand", understand_node)     # Extract entities from messages
workflow.add_node("check_gaps", check_gaps_node)     # Analyze completeness
workflow.add_node("ask_question", ask_question_node) # Generate smart follow-up
workflow.add_node("validate", validate_node)         # Run field validation
workflow.add_node("fill_forms", fill_forms_node)     # Map entities to form fields
workflow.add_node("review", review_node)             # Present summary for confirmation
workflow.add_node("guide", guide_node)               # Generate visual form guide

# Edges
workflow.add_edge(START, "greet")
workflow.add_edge("greet", "understand")
workflow.add_edge("understand", "check_gaps")
workflow.add_conditional_edges("check_gaps", route_after_gaps, {
    "ask_question": "ask_question",     # Missing critical info
    "validate": "validate",             # Have enough, validate it
    "review": "review",                 # All complete
})
workflow.add_edge("ask_question", END)  # Wait for user response
workflow.add_edge("validate", "fill_forms")
workflow.add_edge("fill_forms", "check_gaps")        # Re-check after filling
workflow.add_edge("review", "guide")
workflow.add_edge("guide", END)
```

### Multi-Turn Flow
1. **Turn 0 (Agent initiates):** `greet` → `understand` → `check_gaps` → `ask_question` → END (waits)
2. **Turn 1-N (User responds):** Resume from checkpointed state → `understand` → `check_gaps` → (loop until complete)
3. **Final turn:** `check_gaps` → `review` → `guide` → END

### Checkpointing
- **Development:** `MemorySaver()` (in-memory)
- **Production:** `PostgresSaver` with connection pooling
- **Thread ID format:** `user:{uid}:session:{timestamp}`

### Message Management
- **Progressive summarization** when messages exceed 20 turns
- **Form state** always injected as system context (never summarized)
- **Message trimming** to fit 16K context window

## 5. Agent Tools (10 tools)

### Tool 1: `extract_entities`
Extract structured entities from conversational text.
```python
@tool
def extract_entities(text: str) -> str:
    """Extract insurance entities (people, businesses, vehicles, policies) from text.
    Call this after each user message to capture new information."""
```
**Implementation:** Calls the existing `entity_extractor.extract()` with LLM.

### Tool 2: `classify_lobs`
Identify lines of business from customer description.
```python
@tool
def classify_lobs(text: str) -> str:
    """Classify which lines of business (Commercial Auto, GL, WC, etc.)
    are needed based on the customer's description."""
```
**Implementation:** Calls existing `lob_classifier.classify()`.

### Tool 3: `assign_forms`
Determine which ACORD forms are needed.
```python
@tool
def assign_forms(lobs: str) -> str:
    """Given lines of business, determine which ACORD forms are needed.
    Returns form numbers and their purposes."""
```
**Implementation:** Calls existing `form_assigner.assign()`.

### Tool 4: `read_form`
Dynamically read any AcroForm PDF.
```python
@tool
def read_form(pdf_path: str) -> str:
    """Read a fillable PDF form and return all field names, types, and tooltips.
    Works with any AcroForm PDF, not just known ACORD forms."""
```
**Implementation:** Calls `form_reader.read_pdf_form()`.

### Tool 5: `map_fields`
Map extracted entities to form fields using 3-phase mapper.
```python
@tool
def map_fields(form_number: str, entities_json: str) -> str:
    """Map extracted customer data to form fields using deterministic patterns,
    suffix-indexed arrays, and LLM batch mapping."""
```
**Implementation:** Calls `llm_field_mapper.map_fields()`.

### Tool 6: `validate_fields`
Run field validation (VIN, DL, FEIN, dates, phone, state/ZIP).
```python
@tool
def validate_fields(fields_json: str) -> str:
    """Validate form field values. Checks VIN checksum, DL format by state,
    FEIN format, date ordering, phone format, state/ZIP consistency.
    Returns errors, warnings, and auto-corrections."""
```
**Implementation:** Calls `validation_engine.validate()`.

### Tool 7: `analyze_gaps`
Find missing and incomplete fields.
```python
@tool
def analyze_gaps(form_number: str, fields_json: str) -> str:
    """Analyze which required fields are missing or incomplete for a form.
    Returns missing critical fields, missing important fields, and completeness %."""
```
**Implementation:** Calls `gap_analyzer.analyze()`.

### Tool 8: `save_field`
Record a confirmed field value.
```python
@tool
def save_field(field_name: str, value: str, source: str = "user_stated") -> str:
    """Record a confirmed field value from the customer.
    Source: 'user_stated', 'user_confirmed', 'llm_inferred', 'validated'."""
```
**Implementation:** Updates `IntakeState.form_state` with confidence scoring.

### Tool 9: `scan_document`
Extract data from a scanned form image using OCR+VLM.
```python
@tool
def scan_document(image_path: str, form_type: str = "auto") -> str:
    """Extract field values from a scanned ACORD form image using OCR and
    the finetuned VLM. Returns extracted fields with confidence scores."""
```
**Implementation:** Calls the parent project's extraction pipeline (VLM-only mode for speed).

### Tool 10: `generate_guide`
Create a visual form guide showing where data goes.
```python
@tool
def generate_guide(form_number: str, fields_json: str) -> str:
    """Generate a visual guide showing where each piece of data appears on the
    ACORD form. Uses field position coordinates to create an annotated image."""
```
**Implementation:** Uses form_reader rect coordinates to annotate template PDF images.

## 6. Prompting Strategy

### System Prompt Structure

```
[IDENTITY + ROLE]
You are an AI insurance intake assistant for commercial insurance applications.
Professional, patient, clear. Never condescending.

[CORE RULES]
1. Ask ONE question at a time
2. ONLY record explicitly stated information — NEVER assume
3. Clarify ambiguous answers
4. Mark uncertain fields as PENDING
5. Confirm critical data by reading back
6. Stay on insurance intake topics only

[GROUNDING / ANTI-HALLUCINATION]
Every value MUST come from:
1. Customer explicitly stated it
2. External validation confirmed it
3. System default you disclosed to customer

NEVER invent names, addresses, policy numbers, or identifiers.
Self-check: "Did the customer say this, or am I generating it?"

[PHASED COLLECTION ORDER]
Phase 1: Applicant (name, address, phone, FEIN, entity type)
Phase 2: Policy (LOBs, effective date, carrier, renewal?)
Phase 3: Business (nature, SIC/NAICS, employees, revenue)
Phase 4: Form-specific (vehicles, drivers, locations, coverage)
Phase 5: Review + confirmation

[CURRENT FORM STATE]
{form_state_json}    ← Always injected, never summarized

[CONVERSATION SUMMARY]
{summary}            ← Compressed older turns (if any)

[TOOL USAGE INSTRUCTIONS]
Call save_field after each confirmed piece of information.
Call validate_fields when a section is complete.
Call analyze_gaps to check remaining requirements.
```

### Temperature and Decoding
- **Conversation responses:** `temperature=0.3` (slight variation for natural feel)
- **Entity extraction:** `temperature=0.0` (deterministic)
- **Field mapping:** `temperature=0.0` + JSON Schema enforcement
- **Validation:** Deterministic (no LLM — pure Python rules)

### Structured Output Strategy
1. **Primary:** vLLM JSON Schema enforcement (XGrammar) — guarantees valid structure
2. **Fallback:** Instructor + Pydantic with auto-retry on validation failure
3. **Last resort:** Regex JSON extraction + manual validation

### Confidence Scoring

| Source | Base Confidence |
|--------|----------------|
| User explicitly stated | 0.95 |
| User confirmed (read-back) | 1.00 |
| LLM inferred from context | 0.60 |
| External validation passed | 0.98 |
| Default value applied | 0.50 |
| OCR/VLM extracted | 0.80 |

**Routing thresholds:**
- ≥ 0.90: Auto-accept
- 0.70–0.89: Accept with flag
- 0.50–0.69: Flag for review
- < 0.50: Reject, re-ask

## 7. Conversation Flow Example

```
AGENT: "Welcome! I'm here to help set up your commercial insurance.
        Could you start by telling me your business name and what type
        of business you operate?"

USER:  "We're Acme Trucking LLC, we haul freight across the Midwest."

AGENT: [calls extract_entities → finds business_name="Acme Trucking LLC",
        entity_type="LLC", nature="freight hauling"]
       [calls classify_lobs → "commercial_auto", "motor_truck_cargo"]
       [calls save_field × 3]

       "Great — I have Acme Trucking LLC, a freight hauling company.
        Based on your operations, you'll likely need Commercial Auto
        and Motor Truck Cargo coverage.

        What's the best mailing address for your business?"

USER:  "123 Industrial Blvd, Chicago, IL 60601"

AGENT: [calls save_field for address components]
       [calls validate_fields → state/ZIP check passes]

       "Got it — 123 Industrial Blvd, Chicago, IL 60601.

        When would you like the policy to start?"

... (continues through phases) ...

AGENT: [after all phases complete]
       [calls fill_forms → maps entities to ACORD 125 + 127]
       [calls validate_fields → all pass]
       [calls generate_guide → annotated form images]

       "Here's a summary of everything we've collected:

        Business: Acme Trucking LLC (freight hauling)
        Address: 123 Industrial Blvd, Chicago, IL 60601
        Policy: 03/01/2026 – 03/01/2027
        Vehicles: 3 trucks (VINs verified ✓)
        Drivers: 4 (all licenses verified ✓)
        Coverage: $1M CSL, $50K cargo

        I've filled ACORD Forms 125 and 127. Here's a guide showing
        exactly where each piece of data appears on the forms.

        Does everything look correct?"
```

## 8. Scanned Document Path

When a customer provides a scanned ACORD form instead of typing info:

```
USER: "I have a filled ACORD 125 that I need to transfer to our system."
      [attaches scanned_125.pdf]

AGENT: [calls scan_document(image_path="scanned_125.pdf")]
       → Parent project pipeline: OCR (Surya) → VLM (finetuned Qwen3-VL)
       → Returns extracted fields with confidence scores

       [calls validate_fields on extracted data]
       → VIN checksum, FEIN format, dates, state/ZIP

       [flags low-confidence fields]

       "I've extracted 347 fields from the scanned form.
        A few items need verification:

        1. VIN for Vehicle A reads as '1FTFW1E53N...' — the checksum
           doesn't match. Could you double-check?
        2. The FEIN appears to be '12-345678' — that's only 8 digits.
           Should it be '12-3456789'?

        Everything else looks good. Want me to show you the full
        extraction summary?"
```

## 9. Visual Form Guide

The guide tool uses field rect coordinates from `form_reader.py` to create annotated images:

1. Render template PDF pages as images (PyMuPDF `page.get_pixmap()`)
2. For each filled field, draw a colored overlay on the field rect:
   - Green: confirmed value
   - Yellow: pending / needs review
   - Red: validation error
3. Add a legend / sidebar listing field values
4. Return as PNG images or HTML report

## 10. Project Structure

```
Custom_model_fa_pf/
├── agent/                      # NEW — LangGraph agent
│   ├── __init__.py
│   ├── graph.py                # StateGraph definition + compilation
│   ├── state.py                # IntakeState, IntakePhase
│   ├── nodes.py                # Node functions (greet, understand, etc.)
│   ├── tools.py                # Tool definitions (@tool decorated)
│   ├── prompts.py              # Agent system prompt + templates
│   └── confidence.py           # ConfidenceScorer, HumanReviewRouter
├── cli.py                      # NEW — CLI chat interface
├── config.py                   # MODIFY — add vLLM config, agent config
├── form_reader.py              # EXISTS — dynamic AcroForm reader
├── llm_field_mapper.py         # EXISTS — 3-phase field mapping
├── validation_engine.py        # EXISTS — field validation
├── entity_extractor.py         # EXISTS — NER extraction
├── lob_classifier.py           # EXISTS — LOB classification
├── form_assigner.py            # EXISTS — form assignment
├── gap_analyzer.py             # EXISTS — gap analysis
├── pdf_filler.py               # EXISTS — PDF filling
├── visual_guide.py             # NEW — annotated form images
├── session.py                  # EXISTS — modify for LangGraph integration
├── api.py                      # EXISTS — modify for agent endpoints
└── tests/
    ├── test_agent_graph.py     # NEW — graph structure + routing
    ├── test_agent_tools.py     # NEW — tool definitions + schemas
    ├── test_agent_prompts.py   # NEW — prompt construction
    ├── test_confidence.py      # NEW — scoring + routing
    ├── test_visual_guide.py    # NEW — guide generation
    └── test_cli.py             # NEW — CLI integration
```

## 11. Dependencies to Install

```bash
# Agent framework
uv pip install langgraph langgraph-checkpoint-postgres

# LangChain for LLM abstraction
uv pip install langchain-openai langchain-core

# PostgreSQL driver (production checkpointing)
uv pip install "psycopg[binary,pool]"

# Structured output validation
uv pip install instructor

# Already installed: vllm, fastapi, pydantic, pymupdf
```

## 12. Implementation Phases

### Phase 1: Agent Core (graph + state + tools)
- `agent/state.py` — IntakeState, IntakePhase
- `agent/tools.py` — 10 tool definitions wrapping existing modules
- `agent/graph.py` — StateGraph with nodes and edges
- `agent/nodes.py` — Node functions
- `agent/prompts.py` — System prompt + templates
- Tests: graph structure, tool schemas, routing logic

### Phase 2: CLI Interface
- `cli.py` — Interactive chat loop using LangGraph
- Rich/prompt_toolkit for colored output
- MemorySaver for session persistence
- Tests: CLI integration

### Phase 3: Confidence + Validation Integration
- `agent/confidence.py` — ConfidenceScorer, thresholds, review routing
- Wire validation_engine into the agent loop
- Anti-hallucination prompt testing
- Tests: confidence scoring, routing decisions

### Phase 4: Visual Form Guide
- `visual_guide.py` — Annotated form images from rect coordinates
- PDF rendering + overlay drawing
- Guide as PNG images or HTML
- Tests: image generation, field highlighting

### Phase 5: Scanned Document Support
- Wire parent project's VLM extraction pipeline as `scan_document` tool
- vLLM serving of finetuned model
- Confidence-based flagging of OCR results
- Tests: end-to-end scanned form extraction

### Phase 6: API + Production Hardening
- Update `api.py` — WebSocket/SSE for streaming agent responses
- PostgresSaver for persistent sessions
- Retry policies on all LLM-calling nodes
- Rate limiting, auth, logging
- Tests: API integration, persistence

## 13. Success Criteria

| Metric | Target | How to Verify |
|--------|--------|---------------|
| Conversational accuracy | 99%+ on user-provided data | Unit test: save_field confidence scoring |
| Scanned form accuracy | ≥ 81.58% (current baseline) | E2E test with 5 sample forms |
| Field coverage | 500+ fields across 4 forms | Map_fields test with all templates |
| Conversation turns | ≤ 8 turns for complete intake | Integration test with sample scenarios |
| Response latency | < 3s per turn (vLLM) | Benchmark with timer |
| Tool calling reliability | 95%+ correct tool selection | Agent graph test suite |
| Validation catch rate | 100% on known-bad VIN/FEIN/DL | Unit tests in test_validation_engine.py |

## 14. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Qwen3-VL tool calling may have quirks | Test hermes parser thoroughly; fallback to manual JSON extraction |
| 24GB GPU may be tight for vLLM + KV cache | Use `--max-model-len 8192` if needed; fallback to Ollama |
| LangGraph adds complexity | Start with MemorySaver; PostgresSaver in Phase 6 |
| Agent may over-call tools | Limit to 5 tool calls per turn; recursion_limit=25 |
| Long conversations may exceed context | Progressive summarization at 20 turns; form_state always fresh |
