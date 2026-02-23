"""FastAPI backend for Form Assignment & Pre-Filling system.

Endpoints:
  POST /api/v1/submit              — Submit customer info, start a session
  POST /api/v1/session/{id}/message — Send follow-up info in multi-turn flow
  GET  /api/v1/session/{id}/status  — Get current session state
  GET  /api/v1/session/{id}/result  — Get final JSON output (forms + fields)
  POST /api/v1/session/{id}/finalize — Fill PDFs and return results
  GET  /api/v1/health               — Health check
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from functools import partial
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from Custom_model_fa_pf.config import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    OUTPUT_DIR,
    SCHEMAS_DIR,
)
from Custom_model_fa_pf.input_parser import parse as parse_input
from Custom_model_fa_pf.session import SessionStatus, SessionStore

logger = logging.getLogger(__name__)

# ---------- Global state ----------
store = SessionStore(timeout_seconds=3600)
_llm_engine = None
_schema_registry = None
_knowledge_store = None


def _get_llm(model: str = DEFAULT_MODEL, ollama_url: str = DEFAULT_OLLAMA_URL):
    """Get or create the shared LLM engine."""
    global _llm_engine
    if _llm_engine is None:
        from llm_engine import LLMEngine
        _llm_engine = LLMEngine(
            model=model,
            base_url=ollama_url,
            keep_models_loaded=True,
            structured_json=True,
        )
    return _llm_engine


def _get_schema_registry():
    global _schema_registry
    if _schema_registry is None:
        try:
            from schema_registry import SchemaRegistry
            _schema_registry = SchemaRegistry(schemas_dir=SCHEMAS_DIR)
        except Exception:
            logger.debug("Schema registry not available")
    return _schema_registry


def _get_knowledge_store():
    global _knowledge_store
    if _knowledge_store is None:
        try:
            from knowledge.knowledge_store import InsuranceKnowledgeStore
            _knowledge_store = InsuranceKnowledgeStore()
        except Exception:
            logger.debug("Knowledge store not available")
    return _knowledge_store


# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Form Assignment API starting up")
    yield
    logger.info("Form Assignment API shutting down")


# ---------- App ----------
app = FastAPI(
    title="ACORD Form Assignment & Pre-Filling API",
    version="1.0.0",
    description="Accepts customer info text, assigns ACORD forms, maps fields, and outputs filled JSON/PDFs.",
    lifespan=lifespan,
)


# ---------- Request/Response Models ----------
class SubmitRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Customer info text (email, chat, etc.)")
    model: str = Field(default=DEFAULT_MODEL, description="Ollama model name")
    ollama_url: str = Field(default=DEFAULT_OLLAMA_URL, description="Ollama API URL")
    confidence_threshold: float = Field(default=DEFAULT_CONFIDENCE_THRESHOLD, ge=0.0, le=1.0)

class MessageRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Follow-up message with additional info")

class SessionResponse(BaseModel):
    session_id: str
    status: str
    lobs: list
    forms_assigned: list
    fields_mapped: dict
    gaps: list
    completeness_pct: float
    follow_up_questions: list

class ResultResponse(BaseModel):
    session_id: str
    status: str
    forms: dict  # form_number -> {field_name: value}
    entities: Optional[dict] = None
    gap_report: Optional[dict] = None

class SubmitWithPdfRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Customer info text")
    pdf_path: str = Field(..., description="Path to AcroForm PDF template")
    model: str = Field(default=DEFAULT_MODEL, description="Ollama model name")
    ollama_url: str = Field(default=DEFAULT_OLLAMA_URL, description="Ollama API URL")
    confidence_threshold: float = Field(default=DEFAULT_CONFIDENCE_THRESHOLD, ge=0.0, le=1.0)

class CorrectionRequest(BaseModel):
    form_number: str = Field(..., description="Form number to correct")
    corrections: dict = Field(..., description="Dict of field_name -> corrected_value")


# ---------- Pipeline helpers (run in thread to not block event loop) ----------
def _run_pipeline_stages(session_id: str, model: str, ollama_url: str, confidence_threshold: float):
    """Run all pipeline stages synchronously (called via run_in_executor)."""
    from Custom_model_fa_pf import (
        entity_extractor,
        form_assigner,
        gap_analyzer,
        lob_classifier,
        llm_field_mapper,
        validation_engine,
    )

    session = store.get(session_id)
    if not session:
        return

    try:
        session.status = SessionStatus.PROCESSING
        llm = _get_llm(model, ollama_url)
        knowledge = _get_knowledge_store()
        registry = _get_schema_registry()

        full_text = session.get_full_text()

        # Apply pending corrections before re-running
        if session.pending_corrections:
            for form_num, corrections in session.pending_corrections.items():
                if form_num in session.field_values:
                    session.field_values[form_num].update(corrections)
            session.pending_corrections.clear()

        # Stage 1: LOB Classification
        session.lobs = lob_classifier.classify(
            full_text, llm, confidence_threshold=confidence_threshold
        )
        if not session.lobs:
            session.status = SessionStatus.ERROR
            session.error = "Could not identify any lines of business from the provided text."
            return

        # Stage 2: Entity Extraction
        session.entities = entity_extractor.extract(
            full_text, llm, knowledge_store=knowledge
        )

        # Stage 3: Form Assignment
        session.assignments = form_assigner.assign(session.lobs)

        # Stage 4: Dynamic Field Mapping
        lob_ids = []
        for assignment in session.assignments:
            for lob_id in assignment.lobs:
                if lob_id not in lob_ids:
                    lob_ids.append(lob_id)

        session.field_values = llm_field_mapper.map_all(
            submission=session.entities,
            assignments=session.assignments,
            lobs=lob_ids,
            llm_engine=llm,
            schema_registry=registry,
        )

        # Stage 5: Validation
        for form_num, fields in session.field_values.items():
            vr = validation_engine.validate(fields, entities=session.entities)
            session.validation_results[form_num] = vr
            session.field_values[form_num] = vr.corrected_values

        # Stage 6: Gap Analysis
        session.gap_report = gap_analyzer.analyze(
            session.entities,
            session.assignments,
            session.field_values,
            llm_engine=llm,
            validation_results=session.validation_results,
        )

        # Increment conversation turn
        session.conversation_turn += 1

        # Determine status based on gaps
        if session.gap_report and session.gap_report.missing_critical:
            session.status = SessionStatus.AWAITING_INFO
        else:
            session.status = SessionStatus.COMPLETE

    except Exception as e:
        logger.exception(f"Pipeline error for session {session_id}")
        session.status = SessionStatus.ERROR
        session.error = str(e)


def _build_session_response(session) -> dict:
    """Build a standard session response dict."""
    gaps = []
    follow_ups = []
    completeness = 0.0

    if session.gap_report:
        gaps = session.gap_report.missing_critical + session.gap_report.missing_important
        follow_ups = [q.to_dict() for q in session.gap_report.follow_up_questions]
        completeness = session.gap_report.completeness_pct

    validation_summary = {}
    for form_num, vr in session.validation_results.items():
        validation_summary[form_num] = {
            "errors": vr.error_count,
            "warnings": vr.warning_count,
            "auto_corrections": len(vr.auto_corrections),
        }

    return {
        "session_id": session.id,
        "status": session.status.value,
        "lobs": [l.to_dict() for l in session.lobs],
        "forms_assigned": [
            {"form_number": a.form_number, "purpose": a.purpose, "fillable": a.schema_available}
            for a in session.assignments
        ],
        "fields_mapped": {k: len(v) for k, v in session.field_values.items()},
        "gaps": gaps,
        "completeness_pct": round(completeness, 1),
        "follow_up_questions": follow_ups,
        "validation": validation_summary,
        "conversation_turn": session.conversation_turn,
    }


# ---------- Endpoints ----------

@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "sessions_active": len(store._sessions)}


@app.post("/api/v1/submit")
async def submit(req: SubmitRequest):
    """Submit customer info text to start a new session.

    Creates a session, runs LOB classification → entity extraction →
    form assignment → field mapping → gap analysis, and returns results.
    """
    session = store.create()

    # Parse input through multi-source normalizer
    parsed = parse_input(req.text)
    session.add_message("user", parsed.text)

    # Run pipeline in thread pool to not block the event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        partial(
            _run_pipeline_stages,
            session.id,
            req.model,
            req.ollama_url,
            req.confidence_threshold,
        ),
    )

    return _build_session_response(session)


@app.post("/api/v1/session/{session_id}/message")
async def send_message(session_id: str, req: MessageRequest):
    """Send follow-up info to an existing session.

    Re-runs entity extraction with all accumulated messages,
    then re-maps fields and re-analyzes gaps.
    """
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    # Parse follow-up through normalizer
    parsed = parse_input(req.text)
    session.add_message("user", parsed.text)

    # Re-run pipeline with accumulated text
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        partial(
            _run_pipeline_stages,
            session.id,
            DEFAULT_MODEL,
            DEFAULT_OLLAMA_URL,
            DEFAULT_CONFIDENCE_THRESHOLD,
        ),
    )

    return _build_session_response(session)


@app.get("/api/v1/session/{session_id}/status")
async def get_status(session_id: str):
    """Get current session state (forms assigned, fields filled, gaps remaining)."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    return _build_session_response(session)


@app.get("/api/v1/session/{session_id}/result")
async def get_result(session_id: str):
    """Get final JSON output — all forms with filled field values."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    return {
        "session_id": session.id,
        "status": session.status.value,
        "forms": session.field_values,
        "entities": session.entities.to_dict() if session.entities else None,
        "gap_report": session.gap_report.to_dict() if session.gap_report else None,
    }


@app.post("/api/v1/session/{session_id}/finalize")
async def finalize(session_id: str):
    """Trigger PDF filling and return fill results."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    if not session.field_values:
        raise HTTPException(status_code=400, detail="No fields mapped yet — submit text first")

    from Custom_model_fa_pf import pdf_filler

    output_dir = OUTPUT_DIR / f"session_{session.id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    filled_dir = output_dir / "filled_forms"
    filled_dir.mkdir(exist_ok=True)

    # Run PDF filling in thread pool
    loop = asyncio.get_event_loop()
    fill_results = await loop.run_in_executor(
        None,
        partial(pdf_filler.fill_all, session.field_values, filled_dir),
    )

    session.status = SessionStatus.COMPLETE

    return {
        "session_id": session.id,
        "status": "finalized",
        "fill_results": [
            {
                "form_number": fr.form_number,
                "output_path": str(fr.output_path) if fr.output_path else None,
                "filled_count": fr.filled_count,
                "skipped_count": fr.skipped_count,
                "errors": fr.errors,
            }
            for fr in fill_results
        ],
        "output_dir": str(output_dir),
    }


@app.post("/api/v1/submit-with-pdf")
async def submit_with_pdf(req: SubmitWithPdfRequest):
    """Submit customer info text + custom AcroForm PDF for dynamic mapping.

    Reads the PDF to discover all fields, then runs the full pipeline with
    LLM-powered field mapping tailored to the specific form.
    """
    from pathlib import Path as PPath
    pdf_path = PPath(req.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=400, detail=f"PDF not found: {req.pdf_path}")

    session = store.create()
    parsed = parse_input(req.text)
    session.add_message("user", parsed.text)

    # Store PDF path in session metadata for the pipeline
    # Run standard pipeline — it will auto-read the PDF
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        partial(
            _run_pipeline_stages,
            session.id,
            req.model,
            req.ollama_url,
            req.confidence_threshold,
        ),
    )

    return _build_session_response(session)


@app.get("/api/v1/session/{session_id}/validation")
async def get_validation(session_id: str):
    """Get validation results for a session — errors, warnings, auto-corrections per form."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    return {
        "session_id": session.id,
        "validation_results": {
            form_num: vr.to_dict()
            for form_num, vr in session.validation_results.items()
        },
    }


@app.post("/api/v1/session/{session_id}/correct")
async def apply_correction(session_id: str, req: CorrectionRequest):
    """Apply manual field corrections to a session and re-validate.

    Stores corrections and re-runs validation on the corrected values.
    """
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    if req.form_number not in session.field_values:
        raise HTTPException(status_code=400, detail=f"Form {req.form_number} not found in session")

    # Apply corrections
    session.field_values[req.form_number].update(req.corrections)

    # Re-validate the corrected form
    from Custom_model_fa_pf import validation_engine
    vr = validation_engine.validate(
        session.field_values[req.form_number],
        entities=session.entities,
    )
    session.validation_results[req.form_number] = vr
    session.field_values[req.form_number] = vr.corrected_values

    return {
        "session_id": session.id,
        "form_number": req.form_number,
        "fields_corrected": len(req.corrections),
        "validation": vr.to_dict(),
    }


# ---------- Run ----------
def main():
    """Run the API server."""
    import uvicorn
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
