"""
AI Endpoints Router — Phase 5

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
  LangGraph (Extraction → Validation → Risk Assessment → Completeness)
       ↓
  Structured JSON Response (extracted fields + severity + completeness)
       ↓
  User reviews / edits fields
       ↓
  FastAPI (/api/complaints/) — save confirmed complaint
       ↓
  PostgreSQL
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..agent.graph import run_complaint_pipeline
from ..agent.date_utils import parse_date
from ..agent.document_parser import extract_text_from_upload

router = APIRouter(prefix="/api/ai", tags=["AI Pipeline"])


# ─────────────────────────────────────────────────────────
#  Request / Response Schemas
# ─────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: str


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


def _build_analyze_response(raw_text: str) -> AnalyzeResponse:
    """
    Run the full LangGraph complaint pipeline and format the result
    into an AnalyzeResponse ready for the frontend / Swagger consumer.
    """
    result = run_complaint_pipeline(raw_text)
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

        # ── Validation ───────────────────────────────────
        validation_passed=result.get("validation_passed", True),
        validation_warnings=result.get("validation_warnings", []),

        # ── Metadata ─────────────────────────────────────
        errors=result.get("errors", []),
        raw_text_length=len(raw_text.strip()),
    )


# ─────────────────────────────────────────────────────────
#  POST /api/ai/analyze
#  Analyze pasted/raw complaint text
# ─────────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze raw complaint text",
    description=(
        "Run the full AI pipeline (Extraction → Validation → Risk Assessment → Completeness) "
        "on raw complaint text. Returns structured fields pre-populated for the complaint form. "
        "Does NOT save to the database — use `POST /api/complaints/` to save after review."
    ),
)
def analyze_text(body: AnalyzeRequest):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="'text' field cannot be empty.")
    if len(body.text.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Complaint text is too short (minimum 20 characters). Please provide the full complaint.",
        )
    return _build_analyze_response(body.text)


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
