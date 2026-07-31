from typing import List, Optional
from sqlalchemy.orm import Session

from .models import Complaint, generate_next_complaint_number
from .schemas import ComplaintCreate, ComplaintUpdate


# ─────────────────────────────────────────────────────────
#  CREATE
# ─────────────────────────────────────────────────────────
def create_complaint(db: Session, payload: ComplaintCreate) -> Complaint:
    """
    Generate a sequential complaint_number and persist the new complaint.
    complaint_number generation is protected by a row-level lock inside
    generate_next_complaint_number to prevent duplicates under concurrency.
    """
    complaint_number = generate_next_complaint_number(db)

    complaint = Complaint(
        complaint_number=complaint_number,
        **payload.model_dump(exclude_none=False)
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


# ─────────────────────────────────────────────────────────
#  READ — single record
# ─────────────────────────────────────────────────────────
def get_complaint_by_id(db: Session, complaint_id: int) -> Optional[Complaint]:
    return db.query(Complaint).filter(Complaint.id == complaint_id).first()


def get_complaint_by_number(db: Session, complaint_number: str) -> Optional[Complaint]:
    return db.query(Complaint).filter(Complaint.complaint_number == complaint_number).first()


# ─────────────────────────────────────────────────────────
#  READ — list with optional basic filters
# ─────────────────────────────────────────────────────────
def get_complaints(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
) -> List[Complaint]:
    query = db.query(Complaint)
    if status:
        query = query.filter(Complaint.status == status)
    return query.order_by(Complaint.created_at.desc()).offset(skip).limit(limit).all()


def count_complaints(db: Session, status: Optional[str] = None) -> int:
    query = db.query(Complaint)
    if status:
        query = query.filter(Complaint.status == status)
    return query.count()


# ─────────────────────────────────────────────────────────
#  UPDATE (PATCH)
# ─────────────────────────────────────────────────────────
def update_complaint(
    db: Session, complaint_id: int, payload: ComplaintUpdate
) -> Optional[Complaint]:
    complaint = get_complaint_by_id(db, complaint_id)
    if not complaint:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(complaint, field, value)

    db.commit()
    db.refresh(complaint)
    return complaint


# ─────────────────────────────────────────────────────────
#  DELETE
# ─────────────────────────────────────────────────────────
def delete_complaint(db: Session, complaint_id: int) -> bool:
    complaint = get_complaint_by_id(db, complaint_id)
    if not complaint:
        return False
    db.delete(complaint)
    db.commit()
    return True
