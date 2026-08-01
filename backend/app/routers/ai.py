"""
AI Endpoints Router — Full 8-Node LangGraph Pipeline

Provides:
  POST /api/ai/analyze       — Analyze raw complaint text via LangGraph pipeline
  POST /api/ai/analyze-file  — Upload a document, extract text, analyze via pipeline

The analyze endpoints do NOT save to the database.
Saving is handled separately via POST /api/complaints/ once the user
reviews and confirms the AI-populated fields.

Full backend flow:
  Raw text / File Upload
       ↓
  FastAPI (/api/ai/analyze)
       ↓
  LangGraph (Extraction → Validation → Risk Assessment → Completeness → Summary → RCA → CAPA → Duplicate Detection)
       ↓
  Structured JSON Response (extracted fields + severity + completeness + bonus insights)
       ↓
  User reviews / edits fields
       ↓
  FastAPI (/api/complaints/) — save confirmed complaint
       ↓
  PostgreSQL
"""

import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud
from ..agent.graph import run_complaint_pipeline
from ..agent.date_utils import parse_date
from ..agent.document_parser import extract_text_from_upload

router = APIRouter(prefix="/api/ai", tags=["AI Pipeline"])


# ─────────────────────────────────────────────────────────
#  Request / Response Schemas
# ─────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: str
    current_state: Optional[Dict[str, Any]] = None


class AnalyzeResponse(BaseModel):
    # ── Form Fields (pre-populated by AI, user may edit) ──
    customer_name: Optional[str] = None
    complaint_source: Optional[str] = None
    product_name: Optional[str] = None
    product_strength_grade: Optional[str] = None
    batch_lot_number: Optional[str] = None
    manufacturing_date: Optional[str] = None   # ISO date string or None
    expiry_date: Optional[str] = None           # ISO date string or None
    quantity_affected: Optional[str] = None
    complaint_type: Optional[str] = None
    complaint_date: Optional[str] = None        # ISO date string or None
    detailed_description: Optional[str] = None

    # ── AI Assessment ─────────────────────────────────────
    initial_severity: Optional[str] = None      # Critical | Major | Minor
    priority: Optional[str] = None             # High | Medium | Low
    ai_risk_rationale: Optional[str] = None
    ai_completeness_check: Optional[Dict[str, Any]] = None
    ai_complaint_summary: Optional[str] = None  # Executive QA summary (Bonus #1)
    ai_capa_rca: Optional[Dict[str, Any]] = None  # Root cause hypotheses (Bonus #2)
    ai_capa_recommendation: Optional[Dict[str, Any]] = None  # CAPA actions (Bonus #3)
    ai_duplicate_check: Optional[Dict[str, Any]] = None  # Duplicate detection (Bonus Feature)

    # ── Validation ────────────────────────────────────────
    validation_passed: bool = True
    validation_warnings: List[str] = []

    # ── Pipeline Metadata ─────────────────────────────────
    errors: List[str] = []
    raw_text_length: int = 0


# ─────────────────────────────────────────────────────────
#  Shared Helper — run pipeline and format response
# ─────────────────────────────────────────────────────────

def _to_iso(raw_date_str: Optional[str]) -> Optional[str]:
    """Normalize raw date string from LLM to ISO format (YYYY-MM-DD) or None."""
    parsed = parse_date(raw_date_str)
    return str(parsed) if parsed else None


def _build_analyze_response(raw_text: str, current_state: Optional[Dict[str, Any]] = None) -> AnalyzeResponse:
    """
    Run the full LangGraph complaint pipeline and format the result
    into an AnalyzeResponse ready for the frontend / Swagger consumer.
    """
    result = run_complaint_pipeline(raw_text, current_state)
    fields = result.get("extracted_fields", {})

    return AnalyzeResponse(
        # ── Extracted Facts ─────────────────────────────
        customer_name=fields.get("customer_name"),
        complaint_source=fields.get("complaint_source"),
        product_name=fields.get("product_name"),
        product_strength_grade=fields.get("product_strength_grade"),
        batch_lot_number=fields.get("batch_lot_number"),
        manufacturing_date=_to_iso(fields.get("manufacturing_date")),
        expiry_date=_to_iso(fields.get("expiry_date")),
        quantity_affected=fields.get("quantity_affected"),
        complaint_type=fields.get("complaint_type"),
        complaint_date=_to_iso(fields.get("complaint_date")),
        detailed_description=fields.get("detailed_description"),

        # ── AI Assessment ────────────────────────────────
        initial_severity=result.get("initial_severity"),
        priority=result.get("priority"),
        ai_risk_rationale=result.get("ai_risk_rationale"),
        ai_completeness_check=result.get("ai_completeness_check"),
        ai_complaint_summary=result.get("ai_complaint_summary"),
        ai_capa_rca=result.get("ai_capa_rca"),
        ai_capa_recommendation=result.get("ai_capa_recommendation"),
        ai_duplicate_check=result.get("ai_duplicate_check"),

        # ── Validation ───────────────────────────────────
        validation_passed=result.get("validation_passed", True),
        validation_warnings=result.get("validation_warnings", []),

        # ── Metadata ─────────────────────────────────────
        errors=result.get("errors", []),
        raw_text_length=len(raw_text.strip()),
    )


def check_db_fetch_intent(text: str, db: Session) -> Optional[AnalyzeResponse]:
    """
    Check if the user message is asking to fetch/load/view a saved complaint
    by its complaint_number (e.g., 'fetch data from CMP-2026-0002').
    """
    match = re.search(r"CMP-\d{4}-\d{4}", text, re.IGNORECASE)
    if match:
        cmp_number = match.group(0).upper()
        fetch_keywords = ["fetch", "load", "get", "show", "view", "retrieve", "find", "open", "pull", "data", "search"]
        text_lower = text.lower()
        is_fetch = any(k in text_lower for k in fetch_keywords) or len(text.strip()) < 30

        if is_fetch:
            record = crud.get_complaint_by_number(db=db, complaint_number=cmp_number)
            if record:
                return AnalyzeResponse(
                    customer_name=record.customer_name,
                    complaint_source=record.complaint_source,
                    product_name=record.product_name,
                    product_strength_grade=record.product_strength_grade,
                    batch_lot_number=record.batch_lot_number,
                    manufacturing_date=str(record.manufacturing_date) if record.manufacturing_date else None,
                    expiry_date=str(record.expiry_date) if record.expiry_date else None,
                    quantity_affected=record.quantity_affected,
                    complaint_type=record.complaint_type,
                    complaint_date=str(record.complaint_date) if record.complaint_date else None,
                    detailed_description=record.detailed_description,
                    initial_severity=record.initial_severity,
                    priority=record.priority,
                    ai_risk_rationale=record.ai_risk_rationale or f"Fetched from database record {cmp_number}.",
                    # Completeness and Duplicate Detection are only relevant during
                    # new complaint analysis. For DB fetches, omit them so the
                    # frontend hides those sections entirely.
                    ai_completeness_check=None,
                    ai_complaint_summary=record.ai_complaint_summary,
                    ai_capa_rca=record.ai_capa_rca,
                    ai_capa_recommendation=record.ai_capa_recommendation,
                    ai_duplicate_check=None,
                    validation_passed=True,
                    validation_warnings=[],
                    errors=[],
                    raw_text_length=len(text),
                )
            else:
                return AnalyzeResponse(
                    initial_severity="Minor",
                    priority="Low",
                    ai_risk_rationale=f"Complaint **{cmp_number}** was not found in the database. Please verify the complaint number.",
                    ai_completeness_check=None,
                    validation_passed=False,
                    validation_warnings=[f"Record '{cmp_number}' does not exist."],
                    errors=[f"Complaint '{cmp_number}' not found."],
                    raw_text_length=len(text),
                )
    return None


# ─────────────────────────────────────────────────────────
#  POST /api/ai/analyze
#  Analyze pasted/raw complaint text or fetch by CMP number
# ─────────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze raw complaint text or fetch by CMP number",
    description=(
        "Run the full AI pipeline on raw complaint text, OR fetch an existing complaint "
        "if the message requests a record by ticket number (e.g. 'fetch data from CMP-2026-0002')."
    ),
)
def analyze_text(body: AnalyzeRequest, db: Session = Depends(get_db)):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="'text' field cannot be empty.")

    # Check if this is a database fetch request (e.g. 'fetch data from CMP-2026-0002')
    db_response = check_db_fetch_intent(body.text, db)
    if db_response:
        return db_response

    if len(body.text.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Complaint text is too short (minimum 20 characters). Please provide the full complaint.",
        )
    return _build_analyze_response(body.text, body.current_state)


# ─────────────────────────────────────────────────────────
#  POST /api/ai/analyze-file
#  Upload PDF, DOCX, or TXT — extract text, then analyze
# ─────────────────────────────────────────────────────────

@router.post(
    "/analyze-file",
    response_model=AnalyzeResponse,
    summary="Upload and analyze a complaint document",
    description=(
        "Upload a complaint document (.pdf, .docx, .txt, .eml). "
        "The backend extracts the text and runs the same AI pipeline as `/analyze`. "
        "Note: Only text-based (selectable text) PDFs are supported. Scanned PDFs are not."
    ),
)
async def analyze_file(file: UploadFile = File(...)):
    raw_text = await extract_text_from_upload(file)
    return _build_analyze_response(raw_text)
