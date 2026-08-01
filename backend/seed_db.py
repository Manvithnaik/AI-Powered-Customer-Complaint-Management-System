import os
import sys
from datetime import date
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.database import engine, Base, SessionLocal
from app.models import Complaint, generate_next_complaint_number

def seed():
    print("==================================================")
    print("PUSHING SCHEMA & SEED DATA TO SUPABASE POSTGRESQL")
    print("==================================================")

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    print("Table 'complaints' created / verified.")

    session = SessionLocal()

    # Check if seed records already exist
    existing = session.query(Complaint).filter(
        Complaint.batch_lot_number.in_(["PCM123", "AMX-2026-99B"])
    ).count()
    if existing > 0:
        print(f"Seed records already exist in database ({existing} found). Skipping duplicate seed creation.")
        session.close()
        return

    num1 = generate_next_complaint_number(session)
    c1 = Complaint(
        complaint_number=num1,
        complaint_source="Email",
        customer_name="ABC Pharma",
        product_name="Paracetamol Tablets",
        product_strength_grade="500mg",
        batch_lot_number="PCM123",
        manufacturing_date=date(2026, 1, 10),
        expiry_date=date(2028, 1, 9),
        quantity_affected="20 strips",
        complaint_type="Packaging Defect",
        complaint_date=date(2026, 7, 31),
        detailed_description="Broken tablets reported inside blister packaging upon receipt at retail store.",
        initial_severity="Major",
        priority="High",
        status="Pending Triage",
        ai_completeness_check={"score": 100, "missing_fields": []},
        ai_risk_rationale="Physical tablet breakage in FDF. Requires batch retention sample inspection."
    )
    session.add(c1)
    session.commit()
    print(f"Pushed Record 1: {num1} - {c1.product_name}")

    num2 = generate_next_complaint_number(session)
    c2 = Complaint(
        complaint_number=num2,
        complaint_source="Quality Portal",
        customer_name="St. Jude Labs",
        product_name="Amoxicillin Trihydrate API",
        product_strength_grade="Micronized USP",
        batch_lot_number="AMX-2026-99B",
        manufacturing_date=date(2026, 3, 15),
        expiry_date=date(2029, 3, 14),
        quantity_affected="50 kg",
        complaint_type="Impurity / Assay Failure",
        complaint_date=date(2026, 7, 30),
        detailed_description="Assay result 97.2% vs OOS specification limit of 98.5%. Off-white powder showing slight discoloration.",
        initial_severity="Critical",
        priority="High",
        status="Under Investigation",
        ai_completeness_check={"score": 100, "missing_fields": []},
        ai_risk_rationale="OOS Assay in API active raw material. High risk of impacting downstream drug production."
    )
    session.add(c2)
    session.commit()
    print(f"Pushed Record 2: {num2} - {c2.product_name}")

    session.close()
    print("==================================================")
    print("SEED COMPLETED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    seed()
