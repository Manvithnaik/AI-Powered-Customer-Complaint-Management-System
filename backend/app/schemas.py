from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ─────────────────────────────────────────────────────────
#  Base schema (shared fields between create and response)
# ─────────────────────────────────────────────────────────
class ComplaintBase(BaseModel):
    # Origin
    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None

    # Product & Batch
    product_name: Optional[str] = None
    product_strength_grade: Optional[str] = None
    batch_lot_number: Optional[str] = None
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    quantity_affected: Optional[str] = None

    # Complaint Details
    complaint_type: Optional[str] = None
    complaint_date: Optional[date] = None
    detailed_description: Optional[str] = None

    # Assessment
    initial_severity: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = "Pending Triage"

    # AI Outputs
    ai_completeness_check: Optional[Dict[str, Any]] = None
    ai_risk_rationale: Optional[str] = None
    ai_complaint_summary: Optional[str] = None
    ai_capa_rca: Optional[Dict[str, Any]] = None
    ai_capa_recommendation: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────────────────
#  CREATE schema  — what the client sends in POST body
#  complaint_number is excluded: backend generates it
# ─────────────────────────────────────────────────────────
class ComplaintCreate(ComplaintBase):
    pass


# ─────────────────────────────────────────────────────────
#  UPDATE schema  — for future PATCH support (all optional)
# ─────────────────────────────────────────────────────────
class ComplaintUpdate(BaseModel):
    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    product_strength_grade: Optional[str] = None
    batch_lot_number: Optional[str] = None
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    quantity_affected: Optional[str] = None
    complaint_type: Optional[str] = None
    complaint_date: Optional[date] = None
    detailed_description: Optional[str] = None
    initial_severity: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    ai_completeness_check: Optional[Dict[str, Any]] = None
    ai_risk_rationale: Optional[str] = None
    ai_complaint_summary: Optional[str] = None
    ai_capa_rca: Optional[Dict[str, Any]] = None
    ai_capa_recommendation: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────────────────
#  RESPONSE schema  — what the API returns
#  Includes server-generated fields: id, complaint_number,
#  created_at, updated_at
# ─────────────────────────────────────────────────────────
class ComplaintResponse(ComplaintBase):
    id: int
    complaint_number: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
#  LIST response wrapper (for future pagination support)
# ─────────────────────────────────────────────────────────
class ComplaintListResponse(BaseModel):
    total: int
    complaints: List[ComplaintResponse]
