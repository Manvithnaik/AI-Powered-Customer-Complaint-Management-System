"""
Phase 3 Standalone Test — Groq AI Extraction
Model: llama-3.1-8b-instant via Groq API (replaces decommissioned gemma2-9b-it)
Tests the extractor against 3 realistic pharma complaint scenarios:

  Scenario 1: FDF Packaging Defect (most fields present)
  Scenario 2: API Impurity Complaint (partial info — tests null handling)
  Scenario 3: Minimal Complaint (very sparse — tests edge case extraction)

Run from the backend directory:
  .venv\\Scripts\\python test_extraction.py
"""

import sys
import os
import json

# Force UTF-8 output on Windows terminals
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agent.extractor import extract_complaint_fields
from app.agent.date_utils import parse_date

# ─────────────────────────────────────────────────────────
#  Test complaints
# ─────────────────────────────────────────────────────────

COMPLAINT_1 = """
From: qualityteam@stlukeshospital.in
Date: July 28, 2026
Subject: Complaint — Broken Tablets in Paracetamol 500mg

Dear QA Department,

We are writing to formally raise a quality complaint regarding Paracetamol Tablets 500mg 
received from your company.

Batch Number: PCM-2026-041B
Manufacturing Date: January 10, 2026
Expiry Date: January 9, 2028

During inspection at our pharmacy dispensing unit, we discovered that approximately 
20 blister strips out of a carton of 100 strips contained broken or crumbled tablets.
The physical integrity of the tablets was severely compromised.

Please investigate this matter urgently as this affects patient safety.

Regards,
St. Luke's Hospital
Procurement & Quality Department
"""

COMPLAINT_2 = """
Quality Complaint Notification

Organization: Apex Formulations Pvt. Ltd.
Submission Method: Quality Portal

Product: Amoxicillin Trihydrate (API)
Batch: AMX-99B
Strength/Grade: Micronized USP Grade
Quantity Rejected: 50 kg

Our in-house analytical laboratory conducted a routine assay test on the above batch.
The result returned 97.1% purity against the specification limit of NLT 98.5% (USP).
Additionally, a slight yellowish discoloration was observed in the off-white powder,
which deviates from the standard appearance specification.

Date of Testing: 30th July 2026
"""

COMPLAINT_3 = """
Hi,

We received some vials from your company and a few of them had visible black particles 
floating inside. This is very concerning. The product is Dextrose Injection 5% W/V.
We have around 12 vials affected from the shipment we received last week.

Please look into this immediately.

Thanks,
City Medical Stores
"""

# ─────────────────────────────────────────────────────────
#  Test runner
# ─────────────────────────────────────────────────────────

def run_scenario(number: int, label: str, text: str) -> bool:
    print(f"\n{'='*55}")
    print(f"  SCENARIO {number}: {label}")
    print(f"{'='*55}")
    print(f"Input text ({len(text.strip())} chars):\n{text.strip()[:200]}...")

    try:
        result = extract_complaint_fields(text)
    except Exception as e:
        print(f"\n[FAIL] Extraction error: {e}")
        return False

    print(f"\nExtracted Fields:")
    print(json.dumps(result, indent=2, default=str))

    # Validate dates can be normalized
    mfg_raw = result.get("manufacturing_date")
    exp_raw = result.get("expiry_date")
    cmp_raw = result.get("complaint_date")

    mfg_date = parse_date(mfg_raw)
    exp_date = parse_date(exp_raw)
    cmp_date = parse_date(cmp_raw)

    print(f"\nDate Normalization:")
    print(f"  manufacturing_date: '{mfg_raw}' => {mfg_date}")
    print(f"  expiry_date:        '{exp_raw}' => {exp_date}")
    print(f"  complaint_date:     '{cmp_raw}' => {cmp_date}")

    # Quick assertions
    assert "customer_name" in result, "Missing customer_name key"
    assert "batch_lot_number" in result, "Missing batch_lot_number key"
    assert "initial_severity" not in result or result.get("initial_severity") is None, \
        "VIOLATION: extractor assigned severity — it must not!"
    assert "priority" not in result or result.get("priority") is None, \
        "VIOLATION: extractor assigned priority — it must not!"

    print(f"\n[PASS] Scenario {number} completed successfully.")
    return True


def main():
    print("\n" + "="*55)
    print("  PHASE 3 -- GROQ EXTRACTION INTEGRATION TEST")
    print("  Model: llama-3.1-8b-instant via Groq API")
    print("="*55)

    scenarios = [
        (1, "FDF Packaging Defect (Full Info)", COMPLAINT_1),
        (2, "API Impurity Complaint (Partial Info)", COMPLAINT_2),
        (3, "Minimal Contamination Report (Sparse)", COMPLAINT_3),
    ]

    passed = 0
    for num, label, text in scenarios:
        if run_scenario(num, label, text):
            passed += 1

    print(f"\n{'='*55}")
    print(f"  RESULTS: {passed}/{len(scenarios)} scenarios passed")
    print(f"{'='*55}\n")

    sys.exit(0 if passed == len(scenarios) else 1)


if __name__ == "__main__":
    main()
