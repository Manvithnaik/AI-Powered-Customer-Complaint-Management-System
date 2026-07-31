import os
import sys
from datetime import date
from dotenv import load_dotenv

# Add backend directory to system path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environmental configurations
load_dotenv()

# Import the engine and base to register schema definitions
from app.database import engine, Base, SessionLocal
from app.models import Complaint, generate_next_complaint_number

def run_test():
    print("==================================================")
    print("PHASE 1 - POSTGRESQL CONNECTION & SCHEMA VALIDATION")
    print("==================================================")
    
    # 1. Output connection target (redacting passwords)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        import re
        redacted = re.sub(r":([^/@:]+)@", r":****@", db_url)
        print(f"Connection Target: {redacted}")
    else:
        print("Error: DATABASE_URL is not set in backend/.env!")
        return False
    
    # 2. Synchronize and Create Schema Tables
    print("\nSynchronizing tables and models...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Table 'complaints' verified/created successfully.")
    except Exception as e:
        print(f"Error during schema generation: {e}")
        print("\nEnsure your PostgreSQL instance is running and DATABASE_URL is correct.")
        return False

    # 3. Initialize Session
    print("\nInitializing database session...")
    session = SessionLocal()
    
    # 4. Generate complaint number inside a transaction
    try:
        next_num = generate_next_complaint_number(session)
        print(f"Generated sequential number: {next_num}")
    except Exception as e:
        print(f"Failed to generate complaint number: {e}")
        session.close()
        return False

    # 5. Create the exact mock complaint specified in Phase 1 Success Criteria
    test_complaint = Complaint(
        complaint_number=next_num,
        complaint_source="Email",
        customer_name="ABC Pharma",
        product_name="Paracetamol",
        product_strength_grade="500mg",
        batch_lot_number="PCM123",
        quantity_affected="20 strips",
        detailed_description="Broken tablets reported inside blister packaging.",
        complaint_type="Packaging Defect",
        complaint_date=date.today(),
        status="Pending Triage",
        ai_completeness_check={"score": 100, "missing_fields": []},
        ai_risk_rationale="Extracted packaging issue. Awaiting risk triage node."
    )
    
    # 6. Commit write operation
    print("Writing record to database...")
    try:
        session.add(test_complaint)
        session.commit()
        print(f"Successfully saved record with internal ID: {test_complaint.id}")
    except Exception as e:
        session.rollback()
        print(f"Database write operation failed: {e}")
        session.close()
        return False

    # 7. Read and query record to verify persistence
    print("\nReading record from database to verify persistence...")
    try:
        retrieved = session.query(Complaint).filter_by(complaint_number=next_num).first()
        if retrieved:
            print("SUCCESS: Record found with matching details:")
            print(f" - ID: {retrieved.id}")
            print(f" - Complaint Number: {retrieved.complaint_number}")
            print(f" - Customer Name: {retrieved.customer_name}")
            print(f" - Product Name: {retrieved.product_name}")
            print(f" - Product Strength: {retrieved.product_strength_grade}")
            print(f" - Batch/Lot Number: {retrieved.batch_lot_number}")
            print(f" - Quantity Affected: {retrieved.quantity_affected}")
            print(f" - Description: {retrieved.detailed_description}")
            print(f" - Status: {retrieved.status}")
        else:
            print("FAILED: Inserted record could not be found.")
            session.close()
            return False
    except Exception as e:
        print(f"Database read operation failed: {e}")
        session.close()
        return False

    # 8. Clean up testing residuals (optional, but good for isolated tests)
    # Note: We will delete it to keep test clean, but we can verify it was in PostgreSQL.
    print("\nCleaning up temporary verification record...")
    try:
        session.delete(retrieved)
        session.commit()
        print("Verification record cleaned up successfully.")
    except Exception as e:
        session.rollback()
        print(f"Warning: Cleanup failed. Record might still persist. Error: {e}")
        
    session.close()
    print("\n==================================================")
    print("Phase 1 Integration Test Completed Successfully!")
    print("==================================================")
    return True

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
