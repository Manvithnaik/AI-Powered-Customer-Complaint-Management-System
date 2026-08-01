"""
LangGraph Node Definitions

Each node is a pure function: (ComplaintState) -> dict
The returned dict is merged into the state by LangGraph.

Node responsibilities:
  1. extraction_node       — Extract facts from raw text (NO inference)
  2. validation_node       — Validate logical consistency (Python-based, no LLM)
  3. risk_assessment_node  — Determine severity + priority + rationale (LLM - llama-3.3-70b)
  4. completeness_check_node — Score completeness + list missing fields (Python-based)
  5. summary_node          — Generate executive QA summary paragraph (LLM - llama-3.1-8b)
  6. rca_node              — Formulate root cause investigation hypotheses (LLM - llama-3.3-70b)
  7. capa_node             — Recommend immediate, corrective, and preventive actions (LLM - llama-3.3-70b)
  8. duplicate_detection_node — Search past DB records & score duplicate similarity (Hybrid SQL + LLM)
"""

import os
import json
import re
from datetime import date
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from .state import ComplaintState
from .extractor import extract_complaint_fields
from .date_utils import parse_date

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Model configuration
FAST_MODEL = "llama-3.1-8b-instant"
REASONING_MODEL = "llama-3.3-70b-versatile"


def _safe_val(fields: dict, key: str) -> str:
    """Helper to safely retrieve a non-empty string field value."""
    v = fields.get(key)
    return str(v).strip() if v and str(v).strip().lower() not in ("", "null", "none") else ""



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
    warnings: List[str] = []
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

SUMMARY_SYSTEM_PROMPT = """You are a pharmaceutical Quality Assurance (QA) executive writing a high-level complaint summary for QA management and reviewers.

Generate a professional, executive-style summary paragraph (60–120 words) that follows this logical flow:

1. Customer / Reporting entity (e.g., "Central Medical Stores reported...")
2. Product name and strength
3. Batch / Lot number (e.g., "Batch CIP-260901")
4. Actual observed physical defect or issue — ALWAYS use the specific physical defect mentioned in the text (e.g., "visible edge chipping", "broken tablets", "powder leakage", "dark brown spots", "foreign particles"). DO NOT use generic category names like "Product Appearance / Discoloration" or "Packaging Defect".
5. Quantity affected (if provided)
6. Patient exposure & quarantine status (if mentioned in the text)
7. Final risk classification statement (e.g., "Based on the available information, the complaint has been initially classified as Major severity with Medium priority.")

STRICT RULES:
- ALWAYS include the complete narrative including patient impact, quarantine status, and final risk classification (severity and priority).
- DO NOT invent, assume, or extrapolate any facts. Omit missing details naturally.
- Use actual observed defect details from the complaint description.
- Write as a single, cohesive, professional executive paragraph (60–120 words).
- DO NOT use bullet points, markdown headings, bold labels, or preamble text. Return ONLY the paragraph text."""


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
    if _val("detailed_description"):
        context_parts.append(f"Observed Defect / Complaint Details: {_val('detailed_description')}")
    if state.get("initial_severity"):
        context_parts.append(f"Assigned Risk: {state['initial_severity']} severity, {state.get('priority', 'Unknown')} priority")

    if not context_parts:
        return {
            "ai_complaint_summary": "Insufficient complaint data to generate a summary.",
            "errors": errors,
        }

    complaint_context = "\n".join(context_parts)

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        temperature=0.2,
        max_tokens=350,
    )

    try:
        response = llm.invoke([
            SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
            HumanMessage(content=f"Generate the executive QA complaint summary for the following complaint details:\n\n{complaint_context}"),
        ])
        summary = response.content.strip()
        # Safety: clamp only if excessively long
        if len(summary) > 1000:
            summary = summary[:1000].rsplit(" ", 1)[0] + "…"
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


# ─────────────────────────────────────────────────────────────────────────────
#  NODE 6 — Root Cause Recommendation (RCA)
#  Generates 2–4 investigation hypotheses for QA engineers.
#  Uses llama-3.3-70b-versatile for pharmaceutical domain reasoning.
# ─────────────────────────────────────────────────────────────────────────────

RCA_SYSTEM_PROMPT = """You are an expert pharmaceutical Quality Assurance (QA) and Root Cause Analysis (RCA) specialist.

Your task is to generate 2 to 4 potential root cause investigation hypotheses to assist QA engineers starting a formal complaint investigation.

CRITICAL RULES:
1. NEVER state "The root cause is..." or claim a definitive cause.
2. ALWAYS use tentative language: "possible", "potential", "may occur", "could be associated with", "likely requires investigation", "cannot be excluded".
3. Reason from pharmaceutical manufacturing domain knowledge based on the observed defect and dosage form:
   - Tablets: compression process variation, coating integrity failure, blister sealing mechanical stress, transportation vibration damage.
   - Injectables/Sterile: container closure integrity breach, fill line particulate contamination, sterilizer cycle drift, vial stopper defect.
   - Capsules: capsule shell moisture sensitivity, dosator filling variation, ambient humidity exposure during storage, gelatin instability.
   - Packaging/Labelling: heat-seal temperature fluctuation, friction damage during cartoning, incorrect printing parameters, label adhesion failure.
4. Base hypotheses ONLY on the physical defect and product information provided. Do NOT invent facts.
5. Assign a confidence level: "High" (clear physical defect with obvious manufacturing linkage), "Medium" (defect present but cause uncertain), or "Low" (insufficient detail).
6. Return ONLY a valid JSON object with this exact structure (no markdown, no code blocks, no preamble):

{
  "confidence": "Medium",
  "possible_root_causes": [
    {
      "cause": "Short title of investigation hypothesis",
      "reason": "Technical rationale explaining how this process or material variation could cause the observed defect."
    }
  ],
  "disclaimer": "These are AI-generated investigation hypotheses and are not confirmed root causes."
}"""


def _parse_rca_json(raw: str) -> Dict[str, Any]:
    """Parse JSON from RCA LLM response, stripping markdown fences."""
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in RCA response: {raw}")
    return json.loads(cleaned[start:end])


def rca_node(state: ComplaintState) -> dict:
    """
    Generate potential root cause investigation hypotheses for QA engineers.
    Runs after summary_node. Uses all available extracted fields + risk classification.
    Returns ai_capa_rca as a structured JSON dict.
    """
    errors = list(state.get("errors", []))
    fields = state.get("extracted_fields", {})

    def _val(key: str) -> str:
        v = fields.get(key)
        return str(v).strip() if v and str(v).strip().lower() not in ("", "null", "none") else ""

    description = _val("detailed_description")
    product_name = _val("product_name")

    # Insufficient data guard — need at least a description with substance
    word_count = len(description.split()) if description else 0
    if not description or word_count < 8:
        return {
            "ai_capa_rca": {
                "confidence": "Low",
                "possible_root_causes": [],
                "disclaimer": "Unable to confidently recommend root causes because insufficient complaint information is available.",
            },
            "errors": errors,
        }

    # Build structured context for the LLM
    context_parts = []
    if product_name:
        pstr = product_name
        if _val("product_strength_grade"):
            pstr += f" {_val('product_strength_grade')}"
        context_parts.append(f"Product: {pstr}")
    if _val("complaint_type"):
        context_parts.append(f"Complaint Type: {_val('complaint_type')}")
    if _val("batch_lot_number"):
        context_parts.append(f"Batch/Lot: {_val('batch_lot_number')}")
    if _val("quantity_affected"):
        context_parts.append(f"Quantity Affected: {_val('quantity_affected')}")
    context_parts.append(f"Observed Defect / Description: {description}")
    if state.get("initial_severity"):
        context_parts.append(
            f"Risk Classification: {state['initial_severity']} severity, "
            f"{state.get('priority', 'Unknown')} priority"
        )

    complaint_context = "\n".join(context_parts)

    llm = ChatGroq(
        model=REASONING_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.3,
        max_tokens=600,
    )

    try:
        response = llm.invoke([
            SystemMessage(content=RCA_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    "Generate 2 to 4 potential root cause investigation hypotheses "
                    "for the following pharmaceutical complaint:\n\n"
                    f"{complaint_context}"
                )
            ),
        ])
        rca = _parse_rca_json(response.content)

        # Enforce disclaimer — always overwrite to ensure consistent wording
        rca["disclaimer"] = (
            "These are AI-generated investigation hypotheses and are not confirmed root causes."
        )

        # Validate minimal structure
        if "possible_root_causes" not in rca:
            rca["possible_root_causes"] = []
        if "confidence" not in rca:
            rca["confidence"] = "Medium"

    except Exception as exc:
        errors.append(f"rca_node LLM error: {exc}")
        rca = {
            "confidence": "Low",
            "possible_root_causes": [],
            "disclaimer": "Root cause recommendation could not be generated. Please investigate manually.",
        }

    return {"ai_capa_rca": rca, "errors": errors}


# ─────────────────────────────────────────────────────────────────────────────
#  NODE 7 — CAPA Recommendation
#  Generates corrective and preventive action recommendations for QA engineers.
#  Uses the RCA output from rca_node to produce logically-linked actions.
#  Uses llama-3.3-70b-versatile for pharmaceutical QA reasoning.
# ─────────────────────────────────────────────────────────────────────────────

CAPA_SYSTEM_PROMPT = """You are a senior pharmaceutical Quality Assurance (QA) engineer specialising in Corrective and Preventive Actions (CAPA).

Your task is to generate practical CAPA recommendations for a QA team investigating a customer complaint.

INPUTS YOU WILL RECEIVE:
- Complaint details (product, description, severity, priority)
- Possible root causes identified by a previous AI analysis (use these to drive your CAPA logic)

OUTPUT REQUIREMENTS:
Generate a JSON object with this exact structure:

{
  "confidence": "Medium",
  "corrective_actions": [
    "Suggested corrective action 1",
    "Suggested corrective action 2"
  ],
  "preventive_actions": [
    "Suggested preventive action 1",
    "Suggested preventive action 2"
  ],
  "disclaimer": "These are AI-generated CAPA recommendations intended to support QA investigations and are not approved quality actions."
}

CORRECTIVE ACTIONS — immediate response to this specific complaint:
- Quarantine affected inventory if not already done
- Investigate batch records and manufacturing documentation
- Inspect retained samples from the affected batch
- Perform laboratory investigation (analytical, microbiological as appropriate)
- Notify relevant QA and operations teams
- Conduct customer/field notification if patient safety is at risk

PREVENTIVE ACTIONS — steps to avoid recurrence:
- Review and update relevant Standard Operating Procedures (SOPs)
- Recalibrate or re-qualify equipment involved in the suspected process
- Increase frequency of in-process testing or inspection
- Improve packaging or storage controls
- Review and enhance operator training programs
- Implement additional process monitoring or trend analysis

CRITICAL RULES:
1. Generate 3–5 corrective actions and 3–5 preventive actions.
2. Base actions DIRECTLY on the possible root causes provided — each major root cause should map to at least one corrective and one preventive action.
3. NEVER use mandatory language ("must", "shall", "you must", "the company should"). Use: "suggested", "recommended", "may be considered", "potential action".
4. Do NOT repeat the same action twice. Keep each action specific and practical.
5. Do NOT hallucinate regulatory requirements not mentioned in the complaint.
6. Assign confidence: "High" (clear defect + strong RCA), "Medium" (defect present, cause uncertain), "Low" (insufficient data).
7. Return ONLY the JSON object. No markdown, no code blocks, no preamble or explanation."""


def capa_node(state: ComplaintState) -> dict:
    """
    Generate CAPA recommendations based on complaint details and RCA output.
    Runs after rca_node. Reads ai_capa_rca from state to drive logically-linked actions.
    Returns ai_capa_recommendation as a structured JSON dict.
    """
    errors = list(state.get("errors", []))
    fields = state.get("extracted_fields", {})
    rca = state.get("ai_capa_rca") or {}

    def _val(key: str) -> str:
        v = fields.get(key)
        return str(v).strip() if v and str(v).strip().lower() not in ("", "null", "none") else ""

    description = _val("detailed_description")
    possible_causes = rca.get("possible_root_causes", [])

    # Insufficient data guard — need at least a description or RCA causes
    if not description and not possible_causes:
        return {
            "ai_capa_recommendation": {
                "confidence": "Low",
                "corrective_actions": [],
                "preventive_actions": [],
                "disclaimer": "Unable to generate CAPA recommendations because insufficient complaint information is available.",
            },
            "errors": errors,
        }

    # Build structured context for the LLM
    context_parts = []

    if _val("product_name"):
        pstr = _val("product_name")
        if _val("product_strength_grade"):
            pstr += f" {_val('product_strength_grade')}"
        context_parts.append(f"Product: {pstr}")

    if _val("complaint_type"):
        context_parts.append(f"Complaint Type: {_val('complaint_type')}")

    if _val("batch_lot_number"):
        context_parts.append(f"Batch/Lot: {_val('batch_lot_number')}")

    if _val("quantity_affected"):
        context_parts.append(f"Quantity Affected: {_val('quantity_affected')}")

    if description:
        context_parts.append(f"Observed Defect / Description: {description}")

    if state.get("initial_severity"):
        context_parts.append(
            f"Risk Classification: {state['initial_severity']} severity, "
            f"{state.get('priority', 'Unknown')} priority"
        )

    if possible_causes:
        causes_text = "\n".join(
            f"  - {c.get('cause', '')}: {c.get('reason', '')}"
            for c in possible_causes
        )
        context_parts.append(f"Possible Root Causes (from prior AI analysis):\n{causes_text}")

    complaint_context = "\n".join(context_parts)

    llm = ChatGroq(
        model=REASONING_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.2,
        max_tokens=700,
    )

    try:
        response = llm.invoke([
            SystemMessage(content=CAPA_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    "Generate CAPA recommendations for the following pharmaceutical complaint. "
                    "Use the possible root causes to drive both corrective and preventive actions:\n\n"
                    f"{complaint_context}"
                )
            ),
        ])
        capa = _parse_rca_json(response.content)  # reuse same JSON extractor

        # Enforce disclaimer — always overwrite for consistent wording
        capa["disclaimer"] = (
            "These are AI-generated CAPA recommendations intended to support QA investigations "
            "and are not approved quality actions."
        )

        # Validate structure
        if "corrective_actions" not in capa:
            capa["corrective_actions"] = []
        if "preventive_actions" not in capa:
            capa["preventive_actions"] = []
        if "confidence" not in capa:
            capa["confidence"] = "Medium"

    except Exception as exc:
        errors.append(f"capa_node LLM error: {exc}")
        capa = {
            "confidence": "Low",
            "corrective_actions": [],
            "preventive_actions": [],
            "disclaimer": "CAPA recommendations could not be generated. Please consult your QA team.",
        }

    return {"ai_capa_recommendation": capa, "errors": errors}


# ─────────────────────────────────────────────────────────────────────────────
#  NODE 8 — AI Duplicate Complaint Detection
#  Hybrid Duplicate Detection:
#    1. PostgreSQL deterministic candidate search (top 10 by product/batch/type)
#    2. AI similarity & reasoning on candidates
# ─────────────────────────────────────────────────────────────────────────────

DUPLICATE_SYSTEM_PROMPT = """You are a pharmaceutical Quality Assurance (QA) data analyst comparing a NEW incoming complaint against HISTORICAL candidate complaints from the database.

SCORING HIERARCHY & WEIGHTS (Strict Priority Order):
1. Same Batch Number (Highest Weight)
2. Same Product Name & Strength
3. Same Physical Defect (e.g. discoloration, dark spots, chipping, broken tablets, leakage)
4. Same Complaint Category / Type
5. Same Customer / Reporter
(Lowest Weight: General similarity of text wording)

STRICT SIMILARITY SCORING RULES:
- Same Batch + Same Product + Similar Physical Defect -> MUST score 90%–100% similarity (High Confidence match).
- Same Product + Same Physical Defect + Different/Unknown Batch -> MUST score 65%–85% similarity (Medium Confidence match).
- Same Product + Different Defect OR Different Product -> Score < 50% (Exclude from matches array).

REASON EXPLANATION RULES:
Always list explicit, high-evidence reason tags in order of strength.
PREFER SPECIFIC TAGS:
- "Same Batch"
- "Same Product"
- "Same Physical Defect" (or "Similar Physical Defect")
- "Same Complaint Type"
- "Same Customer"
DO NOT output generic tags like "Similar Customer Description" or "Wording Similarity" when stronger evidence tags (Same Batch, Same Product, Same Physical Defect) exist.

RECOMMENDATION WORDING:
If duplicate matches are found, generate a clear, professional QA recommendation referencing the specific primary complaint number(s), for example:
"A previous complaint has already been logged for the same product and batch. Review complaint CMP-2026-0001 before opening a new investigation to determine whether this report belongs to the existing quality event."

OUTPUT FORMAT REQUIREMENT:
Return ONLY a valid JSON object matching this exact structure (no markdown, no code blocks, no preamble):

{
  "duplicate_found": true,
  "confidence": "High",
  "recommendation": "A previous complaint has already been logged for the same product and batch. Review complaint CMP-2026-0001 before opening a new investigation to determine whether this report belongs to the existing quality event.",
  "matches": [
    {
      "complaint_number": "CMP-2026-0001",
      "similarity": 96,
      "reasons": [
        "Same Batch",
        "Same Product",
        "Similar Physical Defect"
      ]
    }
  ]
}

IF NO CANDIDATE MATCHES >= 55% SIMILARITY:
Return:
{
  "duplicate_found": false,
  "confidence": "High",
  "recommendation": "No similar historical complaints were found.",
  "matches": []
}"""


def duplicate_detection_node(state: ComplaintState) -> dict:
    """
    Perform hybrid duplicate complaint detection:
      Step 1: Query PostgreSQL for up to 10 candidate complaints matching product, batch, or type.
      Step 2: Use LLM to calculate similarity score, reasons, and recommendation.
    Returns ai_duplicate_check dict.
    """
    errors = list(state.get("errors", []))
    fields = state.get("extracted_fields", {})

    product_name = _safe_val(fields, "product_name")
    batch = _safe_val(fields, "batch_lot_number")
    c_type = _safe_val(fields, "complaint_type")
    description = _safe_val(fields, "detailed_description")

    # If product and description are missing, no duplicate check possible
    if not product_name and not description:
        return {
            "ai_duplicate_check": {
                "duplicate_found": False,
                "confidence": "High",
                "recommendation": "No similar historical complaints were found.",
                "matches": [],
            },
            "errors": errors,
        }

    # ── STEP 1: Query PostgreSQL for Candidate Complaints (Limit 10) ────────
    candidates = []
    try:
        # Deferred imports: imported inside function scope to prevent circular
        # import dependency during graph module initialization.
        from app.database import SessionLocal
        from app.models import Complaint
        from sqlalchemy import or_

        db = SessionLocal()
        try:
            filters = []
            if product_name:
                filters.append(Complaint.product_name.ilike(f"%{product_name}%"))
            if batch:
                filters.append(Complaint.batch_lot_number.ilike(f"%{batch}%"))
            if c_type:
                filters.append(Complaint.complaint_type.ilike(f"%{c_type}%"))

            query = db.query(Complaint)
            if filters:
                query = query.filter(or_(*filters))

            # Fetch top 10 most recent candidates
            db_records = query.order_by(Complaint.id.desc()).limit(10).all()

            for rec in db_records:
                candidates.append({
                    "complaint_number": rec.complaint_number,
                    "product_name": rec.product_name or "",
                    "batch_lot_number": rec.batch_lot_number or "",
                    "complaint_type": rec.complaint_type or "",
                    "customer_name": rec.customer_name or "",
                    "detailed_description": (rec.detailed_description or "")[:300],
                })
        finally:
            db.close()
    except Exception as exc:
        errors.append(f"duplicate_detection DB candidate query error: {exc}")

    # If no database candidates exist at all
    if not candidates:
        return {
            "ai_duplicate_check": {
                "duplicate_found": False,
                "confidence": "High",
                "recommendation": "No similar historical complaints were found.",
                "matches": [],
            },
            "errors": errors,
        }

    # ── STEP 2: Pass Current Complaint + Candidates to LLM for Reasoning ────
    current_info = (
        f"Product: {product_name}\n"
        f"Batch: {batch}\n"
        f"Complaint Type: {c_type}\n"
        f"Description: {description}"
    )

    candidates_text = json.dumps(candidates, indent=2)

    llm = ChatGroq(
        model=REASONING_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.1,
        max_tokens=600,
    )

    try:
        response = llm.invoke([
            SystemMessage(content=DUPLICATE_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"NEW INCOMING COMPLAINT:\n{current_info}\n\n"
                    f"HISTORICAL CANDIDATE COMPLAINTS FROM DATABASE:\n{candidates_text}\n\n"
                    "Analyze similarity and return the JSON output."
                )
            ),
        ])
        result = _parse_rca_json(response.content)

        # Ensure required keys exist
        if "duplicate_found" not in result:
            result["duplicate_found"] = bool(result.get("matches"))
        if "confidence" not in result:
            result["confidence"] = "High"
        if "matches" not in result:
            result["matches"] = []
        if "recommendation" not in result:
            result["recommendation"] = (
                "Review existing investigation before creating a new complaint."
                if result["duplicate_found"]
                else "No similar historical complaints were found."
            )

    except Exception as exc:
        errors.append(f"duplicate_detection LLM error: {exc}")
        result = {
            "duplicate_found": False,
            "confidence": "Low",
            "recommendation": "Duplicate detection check could not be completed.",
            "matches": [],
        }

    return {"ai_duplicate_check": result, "errors": errors}
