"""
Phase 5 End-to-End Integration Test

Tests the complete backend flow:

  Raw Complaint Text
       ↓
  POST /api/ai/analyze     (FastAPI → LangGraph → Groq)
       ↓
  Structured AI Response   (extracted fields + severity + completeness)
       ↓
  POST /api/complaints/    (user confirms, save to PostgreSQL)
       ↓
  GET  /api/complaints/{id} (verify saved correctly)
       ↓
  DELETE /api/complaints/{id} (cleanup)

IMPORTANT: The FastAPI server must be running before executing this test.
  Start with: .venv\\Scripts\\uvicorn app.main:app --reload --port 8000
"""

import sys
import os
import io
import json
import urllib.request
import urllib.error

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_URL = "http://127.0.0.1:8000"

# ─────────────────────────────────────────────────────────
#  Test complaint text — rich enough to test full extraction
# ─────────────────────────────────────────────────────────
COMPLAINT_TEXT = """
From: quality@mednova.in
Date: July 31, 2026
Subject: Complaint — Contamination in Atorvastatin Tablets

Dear QA Department,

We are formally reporting a quality issue with a recent consignment.

Customer: MedNova Healthcare Pvt. Ltd.
Product: Atorvastatin Tablets
Strength: 40mg
Batch Number: ATV-2026-113
Manufacturing Date: March 1, 2026
Expiry Date: February 28, 2029
Quantity Affected: 30 bottles (out of 150 received)

During incoming quality inspection, our pharmacist found visible white foreign particles
embedded in the film coating of multiple tablets across 30 bottles from the above batch.
The particles appear crystalline and are inconsistent with the tablet's expected appearance.

We have quarantined the affected bottles and request an urgent investigation.

Regards,
Quality Assurance Team
MedNova Healthcare Pvt. Ltd.
"""


def api_call(method: str, path: str, body: dict = None) -> dict:
    """Make an HTTP API call and return the parsed JSON response."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code} on {method} {path}: {error_body}")


def print_section(title: str):
    print(f"\n{'='*62}")
    print(f"  {title}")
    print(f"{'='*62}")


def main():
    print_section("PHASE 5 -- COMPLETE BACKEND INTEGRATION TEST")
    print("Testing: Raw Text -> FastAPI -> LangGraph -> PostgreSQL")

    # ── Step 0: Health check ──────────────────────────────
    print("\n[Step 0] Health check...")
    health = api_call("GET", "/health")
    assert health.get("status") == "healthy", f"Server not healthy: {health}"
    print("  Server is running and healthy.")

    # ── Step 1: Analyze raw complaint text ────────────────
    print_section("Step 1: POST /api/ai/analyze")
    print(f"Sending complaint ({len(COMPLAINT_TEXT.strip())} chars)...\n")

    analysis = api_call("POST", "/api/ai/analyze", {"text": COMPLAINT_TEXT})

    print("Extracted Fields:")
    for key in ["customer_name", "complaint_source", "product_name", "product_strength_grade",
                "batch_lot_number", "manufacturing_date", "expiry_date",
                "quantity_affected", "complaint_type", "complaint_date"]:
        val = analysis.get(key)
        status = "OK" if val else "NULL"
        print(f"  [{status}] {key}: {val}")

    print(f"\nAI Assessment:")
    print(f"  Severity   : {analysis.get('initial_severity')}")
    print(f"  Priority   : {analysis.get('priority')}")
    print(f"  Rationale  : {analysis.get('ai_risk_rationale', '')[:120]}...")

    comp = analysis.get("ai_completeness_check", {})
    print(f"\nCompleteness: {comp.get('score')}/100 -- {comp.get('completeness_level')}")
    missing = comp.get("missing_fields", [])
    if missing:
        print(f"  Missing: {[m['label'] for m in missing]}")

    if analysis.get("validation_warnings"):
        for w in analysis["validation_warnings"]:
            print(f"  VALIDATION WARNING: {w}")
    if analysis.get("errors"):
        print(f"  ERRORS: {analysis['errors']}")

    # Assertions
    assert analysis.get("product_name"), "product_name should be extracted"
    assert analysis.get("batch_lot_number"), "batch_lot_number should be extracted"
    assert analysis.get("initial_severity") in {"Critical", "Major", "Minor"}, \
        f"Invalid severity: {analysis.get('initial_severity')}"
    assert isinstance(comp.get("score"), int), "Completeness score must be an int"
    print("\n[PASS] Step 1: AI analysis completed successfully.")

    # ── Step 2: Save the confirmed complaint to PostgreSQL ─
    print_section("Step 2: POST /api/complaints/ (Save to DB)")
    print("Submitting AI-analyzed complaint for storage...\n")

    save_payload = {
        "complaint_source":       analysis.get("complaint_source"),
        "customer_name":          analysis.get("customer_name"),
        "product_name":           analysis.get("product_name"),
        "product_strength_grade": analysis.get("product_strength_grade"),
        "batch_lot_number":       analysis.get("batch_lot_number"),
        "manufacturing_date":     analysis.get("manufacturing_date"),
        "expiry_date":            analysis.get("expiry_date"),
        "quantity_affected":      analysis.get("quantity_affected"),
        "complaint_type":         analysis.get("complaint_type"),
        "complaint_date":         analysis.get("complaint_date"),
        "detailed_description":   analysis.get("detailed_description"),
        "initial_severity":       analysis.get("initial_severity"),
        "priority":               analysis.get("priority"),
        "ai_risk_rationale":      analysis.get("ai_risk_rationale"),
        "ai_completeness_check":  analysis.get("ai_completeness_check"),
        "status":                 "Pending Triage",
    }

    saved = api_call("POST", "/api/complaints/", save_payload)
    complaint_id = saved.get("id")
    complaint_number = saved.get("complaint_number")

    print(f"Saved successfully!")
    print(f"  DB Record ID      : {complaint_id}")
    print(f"  Complaint Number  : {complaint_number}")
    print(f"  Status            : {saved.get('status')}")
    print(f"  Severity in DB    : {saved.get('initial_severity')}")

    assert complaint_id, "Saved complaint must have an ID"
    assert complaint_number and complaint_number.startswith("CMP-"), \
        f"Invalid complaint_number: {complaint_number}"
    print("\n[PASS] Step 2: Complaint saved to PostgreSQL.")

    # ── Step 3: Retrieve and verify from DB ───────────────
    print_section(f"Step 3: GET /api/complaints/{complaint_id} (Verify in DB)")

    retrieved = api_call("GET", f"/api/complaints/{complaint_id}")
    print(f"Retrieved record: {retrieved.get('complaint_number')}")
    print(f"  Product  : {retrieved.get('product_name')}")
    print(f"  Batch    : {retrieved.get('batch_lot_number')}")
    print(f"  Severity : {retrieved.get('initial_severity')}")
    print(f"  Priority : {retrieved.get('priority')}")
    assert retrieved.get("id") == complaint_id, "Retrieved ID must match"
    assert retrieved.get("batch_lot_number") == analysis.get("batch_lot_number"), \
        "Batch number must persist correctly"
    print("\n[PASS] Step 3: Record verified in PostgreSQL.")

    # ── Step 4: Cleanup ───────────────────────────────────
    print_section("Step 4: DELETE (Cleanup test record)")
    req = urllib.request.Request(
        f"{BASE_URL}/api/complaints/{complaint_id}", method="DELETE"
    )
    urllib.request.urlopen(req)
    print(f"  Deleted complaint ID {complaint_id} ({complaint_number})")
    print("\n[PASS] Step 4: Cleanup complete.")

    # ── Summary ───────────────────────────────────────────
    print_section("PHASE 5 INTEGRATION TEST -- ALL STEPS PASSED")
    print(f"""
  Flow verified end-to-end:
    Raw Text ({len(COMPLAINT_TEXT.strip())} chars)
      -> POST /api/ai/analyze    (LangGraph + Groq)
      -> AI Response             (severity={analysis.get('initial_severity')}, score={comp.get('score')}/100)
      -> POST /api/complaints/   (saved as {complaint_number})
      -> GET  /api/complaints/{complaint_id}  (verified in Supabase PostgreSQL)
      -> DELETE                  (cleaned up)
    """)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAIL] {e}")
        sys.exit(1)
