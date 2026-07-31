"""
LangGraph Node Definitions

Each node is a pure function: (ComplaintState) -> dict
The returned dict is merged into the state by LangGraph.

Node responsibilities:
  1. extraction_node       — Extract facts from raw text (NO inference)
  2. validation_node       — Validate logical consistency (Python-based, no LLM)
  3. risk_assessment_node  — Determine severity + priority + rationale (LLM)
  4. completeness_check_node — Score completeness + list missing fields (Python-based)
"""

import os
import json
import re
from datetime import date
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from .state import ComplaintState
from .extractor import extract_complaint_fields
from .date_utils import parse_date

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# llama-3.3-70b-versatile: used for reasoning-heavy tasks (risk assessment)
REASONING_MODEL = "llama-3.3-70b-versatile"

# ─────────────────────────────────────────────────────────────────────────────
#  NODE 1 — Extraction
#  Delegates to the Phase 3 extractor. Wraps in error handling.
# ─────────────────────────────────────────────────────────────────────────────
def extraction_node(state: ComplaintState) -> dict:
    """
    Extract factual fields from the raw complaint text.
    Uses llama-3.1-8b-instant via Groq (fast, lightweight).
    Returns only facts present in the text — never invents severity/priority.
    """
    errors = list(state.get("errors", []))
    try:
        extracted = extract_complaint_fields(state["raw_text"])
        return {"extracted_fields": extracted, "errors": errors}
    except Exception as e:
        errors.append(f"ExtractionNode error: {str(e)}")
        return {"extracted_fields": {}, "errors": errors}


# ─────────────────────────────────────────────────────────────────────────────
#  NODE 2 — Validation
#  Pure Python — no LLM call. Checks logical consistency of extracted fields.
# ─────────────────────────────────────────────────────────────────────────────
def validation_node(state: ComplaintState) -> dict:
    """
    Validate extracted fields for logical consistency.

    Checks:
    - expiry_date must not precede manufacturing_date
    - complaint_date must not precede manufacturing_date
    - Warns if batch_lot_number appears suspiciously short (< 3 chars)
    - Warns if description is missing

    Does NOT call any LLM — all deterministic Python logic.
    """
    fields = state.get("extracted_fields", {})
    warnings: list[str] = []
    errors = list(state.get("errors", []))
    passed = True

    # Parse dates
    mfg_date = parse_date(fields.get("manufacturing_date"))
    exp_date  = parse_date(fields.get("expiry_date"))
    cmp_date  = parse_date(fields.get("complaint_date"))

    # Rule 1: expiry must not precede manufacturing
    if mfg_date and exp_date:
        if exp_date <= mfg_date:
            passed = False
            errors.append(
                f"Validation FAILED: expiry_date ({exp_date}) is not after "
                f"manufacturing_date ({mfg_date}). This is logically impossible."
            )

    # Rule 2: complaint_date must not precede manufacturing_date
    if mfg_date and cmp_date:
        if cmp_date < mfg_date:
            warnings.append(
                f"Warning: complaint_date ({cmp_date}) is before "
                f"manufacturing_date ({mfg_date}). Please verify dates."
            )

    # Rule 3: expiry in the past
    if exp_date and exp_date < date.today():
        warnings.append(
            f"Warning: expiry_date ({exp_date}) is in the past. "
            "Product may have already expired."
        )

    # Rule 4: suspiciously short batch number
    batch = fields.get("batch_lot_number")
    if batch and len(str(batch).strip()) < 3:
        warnings.append(
            f"Warning: batch_lot_number '{batch}' is unusually short. Please verify."
        )

    # Rule 5: no description
    if not fields.get("detailed_description"):
        warnings.append(
            "Warning: detailed_description is empty. "
            "Risk assessment may be limited."
        )

    return {
        "validation_passed": passed,
        "validation_warnings": warnings,
        "errors": errors,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  NODE 3 — Risk Assessment
#  Uses llama-3.3-70b-versatile for QMS-aware severity + priority assignment.
# ─────────────────────────────────────────────────────────────────────────────

RISK_SYSTEM_PROMPT = """You are a pharmaceutical Quality Management System (QMS) risk assessment expert.

You will be given structured complaint information and must classify:
1. initial_severity: Choose ONE of: Critical | Major | Minor
2. priority: Choose ONE of: High | Medium | Low
3. ai_risk_rationale: 2-3 sentence explanation referencing pharmaceutical QMS standards.

CLASSIFICATION GUIDELINES:
Critical (always High priority):
  - Contamination (microbial, chemical, foreign particle in sterile/injectable products)
  - Sterility failure
  - Mix-up (wrong product / wrong label)
  - Life-threatening Adverse Events
  - Recall-level failures

Major (usually High or Medium priority):
  - Out-of-specification (OOS) assay / potency results
  - Physical damage affecting dosage integrity
  - Significant packaging failure affecting multiple units
  - API purity failures
  - Non-sterile contamination in oral dosage forms

Minor (usually Low or Medium priority):
  - Cosmetic defects (carton printing, label aesthetics)
  - Minor packaging appearance issues not affecting product
  - Single isolated unit defect with no safety risk

IMPORTANT:
- Consider whether the product is an API (Active Pharmaceutical Ingredient — bulk powder/chemical)
  or FDF (Finished Dosage Form — tablets, capsules, injections, vials) in your assessment.
- Injectable/sterile FDF complaints are treated more critically than oral FDF for the same defect type.
- Return ONLY a valid JSON object with exactly these three keys: initial_severity, priority, ai_risk_rationale.
- No markdown. No code blocks. No explanation outside the JSON."""


def _parse_risk_json(raw: str) -> Dict[str, Any]:
    """Parse JSON from risk assessment response, stripping markdown fences."""
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in risk response: {raw}")
    return json.loads(cleaned[start:end])


def risk_assessment_node(state: ComplaintState) -> dict:
    """
    Classify complaint severity and priority using QMS rules.
    Uses llama-3.3-70b-versatile (reasoning-capable model) via Groq.
    """
    errors = list(state.get("errors", []))
    fields = state.get("extracted_fields", {})

    # Build a compact context string for the LLM
    context_parts = []
    for label, key in [
        ("Product", "product_name"),
        ("Strength/Grade", "product_strength_grade"),
        ("Complaint Type", "complaint_type"),
        ("Batch/Lot", "batch_lot_number"),
        ("Quantity Affected", "quantity_affected"),
        ("Description", "detailed_description"),
        ("Customer", "customer_name"),
    ]:
        val = fields.get(key)
        if val:
            context_parts.append(f"{label}: {val}")

    complaint_context = "\n".join(context_parts) if context_parts else "No structured fields extracted."

    try:
        llm = ChatGroq(
            model=REASONING_MODEL,
            api_key=GROQ_API_KEY,
            temperature=0,
            max_tokens=512,
        )
        messages = [
            SystemMessage(content=RISK_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Assess the risk for the following pharmaceutical complaint:\n\n{complaint_context}"
            ),
        ]
        response = llm.invoke(messages)
        result = _parse_risk_json(response.content.strip())

        severity = result.get("initial_severity", "Minor")
        priority = result.get("priority", "Low")
        rationale = result.get("ai_risk_rationale", "")

        # Normalize values to expected set
        valid_severities = {"Critical", "Major", "Minor"}
        valid_priorities = {"High", "Medium", "Low"}
        if severity not in valid_severities:
            severity = "Minor"
        if priority not in valid_priorities:
            priority = "Low"

        return {
            "initial_severity": severity,
            "priority": priority,
            "ai_risk_rationale": rationale,
            "errors": errors,
        }

    except Exception as e:
        errors.append(f"RiskAssessmentNode error: {str(e)}")
        return {
            "initial_severity": None,
            "priority": None,
            "ai_risk_rationale": None,
            "errors": errors,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  NODE 4 — Completeness Check
#  Pure Python — scores how complete the extracted complaint is.
# ─────────────────────────────────────────────────────────────────────────────

# Fields and their weights (total = 100 points)
FIELD_WEIGHTS = {
    "batch_lot_number":       20,   # Critical for traceability
    "product_name":           15,   # Must know what product
    "customer_name":          10,   # Must know who complained
    "detailed_description":   10,   # Must know what happened
    "complaint_date":         10,   # Must know when
    "quantity_affected":      10,   # Important for scope
    "complaint_type":         10,   # Helps with triage routing
    "product_strength_grade":  5,   # Useful but recoverable
    "manufacturing_date":      5,   # Important for batch tracing
    "expiry_date":             5,   # Important for shelf-life
    "complaint_source":        0,   # Nice to have — zero weight
}

FIELD_LABELS = {
    "batch_lot_number":       "Batch/Lot Number",
    "product_name":           "Product Name",
    "customer_name":          "Customer Name",
    "detailed_description":   "Complaint Description",
    "complaint_date":         "Complaint Date",
    "quantity_affected":      "Quantity Affected",
    "complaint_type":         "Complaint Type",
    "product_strength_grade": "Product Strength/Grade",
    "manufacturing_date":     "Manufacturing Date",
    "expiry_date":            "Expiry Date",
    "complaint_source":       "Complaint Source",
}


def completeness_check_node(state: ComplaintState) -> dict:
    """
    Score the completeness of the extracted complaint (0–100).
    Purely deterministic Python — no LLM required.

    Returns:
      ai_completeness_check = {
        "score": int,
        "missing_fields": [{"field": str, "label": str, "weight": int}],
        "present_fields": [str],
        "completeness_level": "Complete" | "Mostly Complete" | "Incomplete" | "Insufficient"
      }
    """
    fields = state.get("extracted_fields", {})
    errors = list(state.get("errors", []))

    score = 0
    missing = []
    present = []

    for field, weight in FIELD_WEIGHTS.items():
        val = fields.get(field)
        is_present = val is not None and str(val).strip() != "" and str(val).lower() != "null"

        if is_present:
            score += weight
            present.append(field)
        elif weight > 0:  # Only report missing fields that have a weight
            missing.append({
                "field": field,
                "label": FIELD_LABELS.get(field, field),
                "weight": weight,
            })

    # Sort missing by weight descending (most critical missing fields first)
    missing.sort(key=lambda x: x["weight"], reverse=True)

    # Assign a human-readable completeness level
    if score >= 90:
        level = "Complete"
    elif score >= 70:
        level = "Mostly Complete"
    elif score >= 40:
        level = "Incomplete"
    else:
        level = "Insufficient"

    completeness = {
        "score": score,
        "missing_fields": missing,
        "present_fields": present,
        "completeness_level": level,
    }

    return {"ai_completeness_check": completeness, "errors": errors}
