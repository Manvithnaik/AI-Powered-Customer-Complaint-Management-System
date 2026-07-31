"""
Phase 4 Standalone Test — LangGraph Workflow

Tests the full 4-node pipeline end-to-end:
  Extraction -> Validation -> Risk Assessment -> Completeness Check

Run from the backend directory:
  .venv\\Scripts\\python test_langgraph.py
"""

import sys
import os
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agent.graph import run_complaint_pipeline

# ─────────────────────────────────────────────────────────
#  Test Complaints
# ─────────────────────────────────────────────────────────

COMPLAINT_CRITICAL = """
From: qualityalert@citygeneral.in
Date: July 31, 2026
Subject: URGENT — Black Particle Contamination in Dextrose IV Bags

Dear QA Team,

We have identified a critical issue with Dextrose Injection 5% W/V bags received
from your company.

Batch Number: DEX-2026-007
Manufacturing Date: May 10, 2026
Expiry Date: May 9, 2029
Quantity Affected: 45 IV bags out of 200 received

Upon preparation for patient administration, nursing staff found visible black particles
floating inside multiple IV infusion bags. We have immediately quarantined the affected
stock and halted usage. Injectable contamination of this nature poses a direct patient
safety risk and may constitute a serious adverse event.

Regards,
City General Hospital — Pharmacy & Quality Department
"""

COMPLAINT_MAJOR = """
Quality Complaint Notification

Organization: Apex Formulations Pvt. Ltd.
Submission Method: Quality Portal

Product: Amoxicillin Trihydrate API
Batch: AMX-99B
Grade: Micronized USP Grade
Quantity Rejected: 50 kg

Assay result: 97.1% against specification of NLT 98.5% (USP).
Yellowish discoloration observed. Date of testing: July 30, 2026.
"""

COMPLAINT_MINOR = """
Hi,

Just letting you know that some of the cartons for Paracetamol 500mg tablets
(Batch: PCM-2026-09) had slightly smudged printing on the lot number area.
The tablets inside were fine and fully intact.
We received 2 cartons with this issue.

Regards,
Metro Pharmacy
"""


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def run_scenario(label: str, text: str) -> bool:
    print_section(f"SCENARIO: {label}")
    print(f"Input ({len(text.strip())} chars):\n{text.strip()[:150]}...\n")

    try:
        result = run_complaint_pipeline(text)
    except Exception as e:
        print(f"[FAIL] Pipeline error: {e}")
        return False

    # ── Extracted Fields ──────────────────────────────
    print("[ Extraction Node ]")
    fields = result.get("extracted_fields", {})
    for key, val in fields.items():
        if val:
            print(f"  {key}: {val}")

    # ── Validation ─────────────────────────────────────
    print("\n[ Validation Node ]")
    print(f"  passed: {result.get('validation_passed')}")
    for w in result.get("validation_warnings", []):
        print(f"  WARNING: {w}")

    # ── Risk Assessment ─────────────────────────────────
    print("\n[ Risk Assessment Node ]")
    print(f"  Severity : {result.get('initial_severity')}")
    print(f"  Priority : {result.get('priority')}")
    print(f"  Rationale: {result.get('ai_risk_rationale')}")

    # ── Completeness ────────────────────────────────────
    print("\n[ Completeness Check Node ]")
    comp = result.get("ai_completeness_check", {})
    print(f"  Score : {comp.get('score')}/100 — {comp.get('completeness_level')}")
    missing = comp.get("missing_fields", [])
    if missing:
        print(f"  Missing fields ({len(missing)}):")
        for m in missing:
            print(f"    - {m['label']} (weight: {m['weight']})")
    else:
        print("  All key fields present!")

    # ── Errors ──────────────────────────────────────────
    errs = result.get("errors", [])
    if errs:
        print("\n[ Errors ]")
        for e in errs:
            print(f"  ERROR: {e}")

    # ── Assertions ──────────────────────────────────────
    assert result.get("initial_severity") in {"Critical", "Major", "Minor", None}, \
        f"Invalid severity: {result.get('initial_severity')}"
    assert result.get("priority") in {"High", "Medium", "Low", None}, \
        f"Invalid priority: {result.get('priority')}"
    assert isinstance(result.get("ai_completeness_check"), dict), \
        "Completeness check must return a dict"
    assert "score" in result.get("ai_completeness_check", {}), \
        "Completeness check must contain a score"

    print(f"\n[PASS] Scenario '{label}' completed.")
    return True


def main():
    print_section("PHASE 4 -- LANGGRAPH WORKFLOW INTEGRATION TEST")

    scenarios = [
        ("Critical — IV Contamination (injectable FDF)", COMPLAINT_CRITICAL),
        ("Major — API OOS Assay Failure", COMPLAINT_MAJOR),
        ("Minor — Cosmetic Carton Printing Defect", COMPLAINT_MINOR),
    ]

    passed = 0
    for label, text in scenarios:
        if run_scenario(label, text):
            passed += 1

    print_section(f"RESULTS: {passed}/{len(scenarios)} scenarios passed")
    sys.exit(0 if passed == len(scenarios) else 1)


if __name__ == "__main__":
    main()
