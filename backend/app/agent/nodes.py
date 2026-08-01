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
from typing import Any, Dict, Optional

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
#  Intent Classification Prompts & Helpers
# ─────────────────────────────────────────────────────────────────────────────

CLASSIFY_INTENT_PROMPT = """You are a pharmaceutical Quality Management System (QMS) intake assistant.

Analyze the user's new message to determine if it is:
1. A FOLLOW_UP / UPDATE / CORRECTION / SUPPLEMENT to the current complaint draft.
2. A completely NEW, unrelated complaint.

Current complaint draft:
- Product: {product_name}
- Customer: {customer_name}
- Batch: {batch_lot_number}

GUIDELINES to classify as FOLLOW_UP (UPDATE):
- User is adding a missing field (e.g. "the manufacturing date is...", "forgot to mention the batch...")
- User is correcting a field (e.g. "it is actually 10 strips, not 8", "change the customer to...")
- User is supplying updates or supplementary details for the product already mentioned in the draft.
- Common trigger words: "Update...", "Small update...", "Correction...", "Actually...", "I forgot...", "Also..."

Otherwise, classify as NEW.

Response MUST be exactly one word: UPDATE or NEW. Do not output anything else."""


def detect_update_intent(text: str, current_state: Optional[Dict[str, Any]]) -> bool:
    """
    Detect if the incoming message is a follow-up/update to the current draft
    or a new complaint.
    """
    if not current_state or not current_state.get("product_name"):
        return False

    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=GROQ_API_KEY,
            temperature=0,
            max_tokens=5,
        )
        product = current_state.get("product_name") or "None"
        customer = current_state.get("customer_name") or "None"
        batch = current_state.get("batch_lot_number") or "None"

        prompt = CLASSIFY_INTENT_PROMPT.format(
            product_name=product,
            customer_name=customer,
            batch_lot_number=batch
        )

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"User Message: \"{text}\""),
        ]

        response = llm.invoke(messages)
        res = response.content.strip().upper()
        return "UPDATE" in res
    except Exception:
        # Fallback to keyword matching if Groq is unavailable
        keywords = ["update", "correct", "change", "forgot", "actually", "received on", "manufacturing", "expiry", "expiration"]
        text_lower = text.lower()
        return any(k in text_lower for k in keywords)


# ─────────────────────────────────────────────────────────────────────────────
#  NODE 1 — Extraction
#  Delegates to the Phase 3 extractor. Wraps in error handling.
# ─────────────────────────────────────────────────────────────────────────────
def extraction_node(state: ComplaintState) -> dict:
    """
    Extract factual fields from the raw complaint text.
    If detected as a follow-up, extracts only the new info and merges it
    with the current state.
    """
    errors = list(state.get("errors", []))
    raw_text = state["raw_text"]
    current_state = state.get("current_state")

    try:
        # Detect intent
        is_update = detect_update_intent(raw_text, current_state)

        # Extract fields from the current message
        newly_extracted = extract_complaint_fields(raw_text)

        if is_update and current_state:
            # Programmatic Patch / Merge
            merged = {**current_state}

            for key, val in newly_extracted.items():
                if val is not None and str(val).strip() != "" and str(val).lower() != "null":
                    # Special description preservation rule
                    if key == "detailed_description":
                        old_desc = current_state.get("detailed_description") or ""
                        new_desc = val.strip()

                        # Check if new_desc is just parameter updates
                        lower_new = new_desc.lower()
                        has_defect_keywords = any(x in lower_new for x in [
                            "defect", "chipped", "cracked", "broken", "dirty", "particle",
                            "contamination", "odor", "smell", "color", "failed", "discoloration",
                            "purity", "active pharmaceutical ingredient", "adverse event"
                        ])
                        is_just_parameters = not has_defect_keywords and any(x in lower_new for x in [
                            "date", "manufacturing", "expiry", "expire", "quantity", "strips",
                            "bottles", "vials", "kg", "batch", "lot", "update", "correct"
                        ])

                        if is_just_parameters:
                            # Keep original defect description
                            merged[key] = old_desc
                        else:
                            # Append supplementary descriptions
                            if old_desc and new_desc and new_desc not in old_desc:
                                merged[key] = f"{old_desc}\n[Update]: {new_desc}"
                            else:
                                merged[key] = new_desc or old_desc
                    else:
                        merged[key] = val

            return {"extracted_fields": merged, "errors": errors}

        else:
            # Genuinely new complaint — return fresh extraction
            return {"extracted_fields": newly_extracted, "errors": errors}

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
  - Product appearance defects on dosage units (discoloration, spots, degradation) of unconfirmed cause

Minor (usually Low or Medium priority):
  - Cosmetic packaging defects (carton printing, label aesthetics, outer shipping box damage)
  - Minor packaging appearance issues not affecting dosage unit integrity
  - Single isolated non-product defect with no safety risk

STRICT RULES ON REASONING AND RATIONALE:
1. OBSERVED FACTS VS UNCONFIRMED CAUSES:
   - Distinguish observed physical facts (e.g., dark brown spots or discoloration on capsule shells) from unconfirmed root causes or impacts.
   - NEVER classify dosage form defects (discoloration, spots, cracking, swelling) as "cosmetic defects" or claim they do not affect potency, purity, or stability before laboratory investigation. Discoloration on dosage units may indicate chemical degradation, moisture ingress, or active instability.
   - Prefer objective language such as: "The observed discoloration represents an appearance-related product quality defect. The underlying cause and potential impact on product quality have not yet been established and require QMS laboratory investigation."

2. NO HALLUCINATED CATEGORIES:
   - Do NOT invent or infer defect categories or root causes not stated in the complaint.
   - Do NOT categorize a dosage form issue as a "Packaging Defect" unless there is explicit evidence of container, bottle, blister, carton, seal, or label damage.
   - Never assume absence of evidence means absence of risk. If information is unknown, explicitly state that it is unknown.

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


# ─────────────────────────────────────────────────────────────────────────────
#  NODE 5 — Complaint Summary
#  Generates a concise executive summary for QA personnel.
#  Uses llama-3.1-8b-instant (fast, sufficient for summarisation).
# ─────────────────────────────────────────────────────────────────────────────

SUMMARY_SYSTEM_PROMPT = """You are a pharmaceutical Quality Assurance specialist writing a complaint summary for a QA reviewer.

Generate a single concise paragraph (60–120 words) that gives a QA engineer an immediate understanding of the complaint.

Include the following elements ONLY if the information is present in the complaint data provided:
• Customer / reporter name
• Product name, strength, and batch/lot number
• Nature of the defect or issue (exactly as described — do not interpret or diagnose)
• Quantity affected
• Patient or end-user impact (only if explicitly mentioned)
• Current risk classification (severity and priority)

STRICT RULES:
- Do NOT invent or infer any information not present in the data.
- If a field is missing or null, simply omit it from the summary.
- Do NOT use bullet points. Write a single flowing paragraph.
- Do NOT include headings, labels, or any text before or after the paragraph.
- Return ONLY the summary paragraph text. No markdown. No preamble."""


def summary_node(state: ComplaintState) -> dict:
    """
    Generate a concise executive QA summary of the complaint.
    Runs after completeness_check_node; has access to fully merged extracted_fields,
    risk assessment, and severity/priority classification.
    """
    errors = list(state.get("errors", []))
    fields = state.get("extracted_fields", {})

    # Build a structured context block for the LLM
    def _val(key: str) -> str:
        v = fields.get(key)
        return str(v).strip() if v and str(v).strip().lower() not in ("", "null", "none") else ""

    context_parts = []
    if _val("customer_name"):
        context_parts.append(f"Customer: {_val('customer_name')}")
    if _val("product_name"):
        product_str = _val("product_name")
        if _val("product_strength_grade"):
            product_str += f" {_val('product_strength_grade')}"
        context_parts.append(f"Product: {product_str}")
    if _val("batch_lot_number"):
        context_parts.append(f"Batch/Lot: {_val('batch_lot_number')}")
    if _val("quantity_affected"):
        context_parts.append(f"Quantity Affected: {_val('quantity_affected')}")
    if _val("complaint_type"):
        context_parts.append(f"Complaint Type: {_val('complaint_type')}")
    if _val("detailed_description"):
        context_parts.append(f"Complaint Description: {_val('detailed_description')}")
    if state.get("initial_severity"):
        context_parts.append(f"Risk Classification: {state['initial_severity']} severity, {state.get('priority', 'Unknown')} priority")

    if not context_parts:
        return {
            "ai_complaint_summary": "Insufficient complaint data to generate a summary.",
            "errors": errors,
        }

    complaint_context = "\n".join(context_parts)

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        temperature=0.3,
        max_tokens=200,
    )

    try:
        response = llm.invoke([
            SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
            HumanMessage(content=f"Generate the QA complaint summary for the following complaint:\n\n{complaint_context}"),
        ])
        summary = response.content.strip()
        # Safety: clamp to avoid runaway responses
        if len(summary) > 800:
            summary = summary[:800].rsplit(" ", 1)[0] + "…"
    except Exception as exc:
        # Graceful fallback: build a minimal templated summary without LLM
        errors.append(f"summary_node LLM error: {exc}")
        parts = []
        if _val("customer_name"):
            parts.append(f"{_val('customer_name')} reported")
        else:
            parts.append("A complaint was reported")
        if _val("product_name"):
            prod = _val("product_name")
            if _val("product_strength_grade"):
                prod += f" {_val('product_strength_grade')}"
            if _val("batch_lot_number"):
                prod += f" (Batch: {_val('batch_lot_number')})"
            parts.append(f"regarding {prod}")
        if _val("detailed_description"):
            parts.append(f"— {_val('detailed_description')[:200]}")
        if state.get("initial_severity"):
            parts.append(
                f"The complaint has been initially classified as {state['initial_severity']} severity "
                f"with {state.get('priority', 'Unknown')} priority."
            )
        summary = " ".join(parts) + "." if parts else "Summary unavailable."

    return {"ai_complaint_summary": summary, "errors": errors}
