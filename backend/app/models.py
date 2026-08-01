import datetime
from sqlalchemy import Column, Integer, String, Date, Text, DateTime, JSON
from sqlalchemy.sql import func
from .database import Base

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    
    # Human-readable unique identifier
    complaint_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # 1. Origin & Customer Details
    complaint_source = Column(String(100), nullable=True)  # e.g., Email, Phone, Portal, Letter
    customer_name = Column(String(255), nullable=True)     # Customer (e.g., pharmacy, hospital, distributor)
    
    # 2. Product & Batch Identification
    product_name = Column(String(255), nullable=True)
    product_strength_grade = Column(String(100), nullable=True)  # e.g., 500mg, Grade A
    batch_lot_number = Column(String(100), index=True, nullable=True)  # Critical for traceability
    manufacturing_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    quantity_affected = Column(String(100), nullable=True)  # e.g., "20 strips", "500 vials", "20 kg"
    
    # 3. Complaint Details
    complaint_type = Column(String(255), nullable=True)  # e.g., Packaging defect, Contamination
    complaint_date = Column(Date, nullable=True)         # Date customer raised complaint
    detailed_description = Column(Text, nullable=True)   # Complete unstructured text/email narration
    
    # 4. Initial Assessment & Priority
    initial_severity = Column(String(50), nullable=True)  # Critical, Major, Minor
    priority = Column(String(50), nullable=True)          # High, Medium, Low
    
    # Triage status
    status = Column(String(50), default="Pending Triage")  # Pending Triage, Under Investigation, Resolved
    
    # AI Copilot Analytics (using JSONB via SQLAlchemy JSON type on PostgreSQL)
    ai_completeness_check = Column(JSON, nullable=True)   # Audits of missing information (score, lists)
    ai_risk_rationale = Column(Text, nullable=True)        # Copilot rationale for severity / priority rating
    ai_complaint_summary = Column(Text, nullable=True)     # Executive QA summary paragraph (Bonus Feature #1)
    ai_capa_rca = Column(JSON, nullable=True)              # Recommended CAPA list and RCA analysis (future phase)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Complaint id={self.id} number={self.complaint_number} product={self.product_name} status={self.status}>"


def generate_next_complaint_number(session) -> str:
    """
    Generates a unique, sequential complaint identifier within a row-locked transaction.
    Format: CMP-YYYY-XXXX (e.g. CMP-2026-0001)
    """
    current_year = datetime.datetime.now().year
    prefix = f"CMP-{current_year}-"
    
    # Acquire a row lock on rows matching this year's prefix to block concurrent inserts
    max_complaint = (
        session.query(Complaint)
        .filter(Complaint.complaint_number.like(f"{prefix}%"))
        .with_for_update()
        .order_by(Complaint.complaint_number.desc())
        .first()
    )
    
    if max_complaint and max_complaint.complaint_number:
        try:
            # Extract serial number from the end (e.g., "0001" from "CMP-2026-0001")
            last_serial_str = max_complaint.complaint_number.split("-")[-1]
            last_serial = int(last_serial_str)
            next_serial = last_serial + 1
        except (ValueError, IndexError):
            next_serial = 1
    else:
        next_serial = 1
        
    return f"{prefix}{next_serial:04d}"
