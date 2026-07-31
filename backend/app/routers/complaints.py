from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ComplaintCreate, ComplaintUpdate, ComplaintResponse, ComplaintListResponse
from .. import crud

router = APIRouter(
    prefix="/api/complaints",
    tags=["Complaints"],
)


# ─────────────────────────────────────────────────────────
#  POST /api/complaints/
#  Create a new complaint. Backend auto-generates complaint_number.
# ─────────────────────────────────────────────────────────
@router.post(
    "/",
    response_model=ComplaintResponse,
    status_code=201,
    summary="Log a new complaint",
    description="Submit a new customer complaint. The backend automatically generates a unique `complaint_number` (e.g. `CMP-2026-0001`).",
)
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db)):
    return crud.create_complaint(db=db, payload=payload)


# ─────────────────────────────────────────────────────────
#  GET /api/complaints/
#  Retrieve a paginated list of complaints with optional status filter.
# ─────────────────────────────────────────────────────────
@router.get(
    "/",
    response_model=ComplaintListResponse,
    summary="List all complaints",
    description="Retrieve all complaints. Optionally filter by `status` and paginate using `skip` and `limit`.",
)
def list_complaints(
    skip: int = Query(0, ge=0, description="Number of records to skip (pagination offset)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. 'Pending Triage', 'Under Investigation', 'Resolved')"),
    db: Session = Depends(get_db),
):
    complaints = crud.get_complaints(db=db, skip=skip, limit=limit, status=status)
    total = crud.count_complaints(db=db, status=status)
    return ComplaintListResponse(total=total, complaints=complaints)


# ─────────────────────────────────────────────────────────
#  GET /api/complaints/{id}
#  Retrieve a single complaint by numeric database ID.
# ─────────────────────────────────────────────────────────
@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse,
    summary="Get complaint by ID",
    description="Fetch a single complaint using its internal numeric `id`.",
)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    complaint = crud.get_complaint_by_id(db=db, complaint_id=complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail=f"Complaint with id={complaint_id} not found.")
    return complaint


@router.get(
    "/by-number/{complaint_number}",
    response_model=ComplaintResponse,
    summary="Get complaint by complaint number",
    description="Fetch a single complaint using its ticket number (e.g. `CMP-2026-0002`).",
)
def get_complaint_by_number(complaint_number: str, db: Session = Depends(get_db)):
    complaint = crud.get_complaint_by_number(db=db, complaint_number=complaint_number.upper())
    if not complaint:
        raise HTTPException(status_code=404, detail=f"Complaint '{complaint_number}' not found.")
    return complaint


# ─────────────────────────────────────────────────────────
#  PATCH /api/complaints/{id}
#  Update specific fields on an existing complaint.
# ─────────────────────────────────────────────────────────
@router.patch(
    "/{complaint_id}",
    response_model=ComplaintResponse,
    summary="Update a complaint",
    description="Partially update an existing complaint's fields. Only fields included in the request body are modified.",
)
def update_complaint(complaint_id: int, payload: ComplaintUpdate, db: Session = Depends(get_db)):
    updated = crud.update_complaint(db=db, complaint_id=complaint_id, payload=payload)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Complaint with id={complaint_id} not found.")
    return updated


# ─────────────────────────────────────────────────────────
#  DELETE /api/complaints/{id}
# ─────────────────────────────────────────────────────────
@router.delete(
    "/{complaint_id}",
    status_code=204,
    summary="Delete a complaint",
    description="Permanently delete a complaint record by its internal numeric `id`.",
)
def delete_complaint(complaint_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_complaint(db=db, complaint_id=complaint_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Complaint with id={complaint_id} not found.")
