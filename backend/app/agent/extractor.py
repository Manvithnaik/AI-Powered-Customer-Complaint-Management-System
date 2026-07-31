"""
Phase 3 — Groq AI Extraction Module

Responsibility: Extract ONLY factual information explicitly present in the
raw complaint text. This module NEVER invents, infers, or predicts:

NOTE on model selection:
  The assignment specifies gemma2-9b-it, however Groq decommissioned this
  model on 2026-07-31. We use llama-3.1-8b-instant as the direct replacement
  — it is Groq's recommended fast/lightweight model for extraction tasks.
  llama-3.3-70b-versatile is retained for deep-reasoning nodes (Phase 4).
  - severity
  - priority
  - root cause
  - CAPA
  - risk assessment

Those responsibilities belong to separate LangGraph nodes (Phase 4).
"""

import os
import json
import re
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

# ─────────────────────────────────────────────────────────
#  Model configuration
# ─────────────────────────────────────────────────────────
# gemma2-9b-it was decommissioned by Groq (2026-07-31).
# llama-3.1-8b-instant is the current recommended fast/lightweight replacement.
PRIMARY_MODEL = "llama-3.1-8b-instant"   # Fast, efficient — primary extraction
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY is missing. Please set it in backend/.env"
    )


# ─────────────────────────────────────────────────────────
#  System prompt — strict extraction only
# ─────────────────────────────────────────────────────────
EXTRACTION_SYSTEM_PROMPT = """You are a pharmaceutical Quality Management System (QMS) data extraction assistant.

Your ONLY job is to extract factual information that is EXPLICITLY stated in the customer complaint text.

STRICT RULES:
1. Extract ONLY information that is directly present in the text. Do NOT infer, guess, or generate any information.
2. If a field is not mentioned in the text, set it to null.
3. Do NOT assign severity, priority, risk level, root cause, or CAPA recommendations. These are handled by separate systems.
4. Return ONLY a valid JSON object. No markdown, no code blocks, no explanation.

Extract the following fields into a JSON object:
{
  "customer_name": "Name of the customer, company, or organization filing the complaint. null if not mentioned.",
  "complaint_source": "How the complaint was received: Email, Phone, Portal, Letter, or Verbal. null if not mentioned.",
  "product_name": "Name of the product. null if not mentioned.",
  "product_strength_grade": "Product strength (e.g. 500mg, 10mg/ml) or grade (e.g. USP, BP, IP). null if not mentioned.",
  "batch_lot_number": "Batch number or lot number. null if not mentioned.",
  "manufacturing_date": "Manufacturing date as found in the text (any format). null if not mentioned.",
  "expiry_date": "Expiry or expiration date as found in the text (any format). null if not mentioned.",
  "quantity_affected": "Quantity of product affected (e.g. 20 strips, 500 vials, 10 kg). null if not mentioned.",
  "complaint_type": "Category of the defect as best described by the text (e.g. Packaging Defect, Contamination, Impurity/Assay Failure, Adverse Event, Labelling Error, Foreign Particle). null if not mentioned.",
  "complaint_date": "Date when the complaint was raised or received (any format). null if not mentioned.",
  "detailed_description": "A clean, concise factual summary of the complaint issue based ONLY on what is written. Do not add any information."
}

Remember: null for anything not explicitly stated. Return ONLY the JSON object."""


def _parse_json_from_response(raw: str) -> Dict[str, Any]:
    """
    Robustly parse JSON from model response.
    Handles cases where the model wraps output in markdown code fences.
    """
    # Strip markdown code fences if present (e.g. ```json ... ```)
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
    cleaned = cleaned.rstrip("`").strip()

    # Find the first { and last } to isolate the JSON object
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in model response:\n{raw}")

    return json.loads(cleaned[start:end])


def extract_complaint_fields(raw_text: str) -> Dict[str, Any]:
    """
    Extract structured complaint fields from raw unstructured text.

    Args:
        raw_text: Raw complaint text (email body, pasted text, parsed document)

    Returns:
        Dictionary with extracted fields. Missing fields are set to None.
        Does NOT include severity, priority, risk assessment, or CAPA.

    Raises:
        ValueError: If the API key is missing or JSON parsing fails.
        Exception:  If Groq API call fails.
    """
    llm = ChatGroq(
        model=PRIMARY_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0,          # Deterministic — we want consistent extraction
        max_tokens=1024,
    )

    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=f"Extract complaint fields from the following text:\n\n{raw_text}"),
    ]

    response = llm.invoke(messages)
    raw_content = response.content.strip()

    extracted = _parse_json_from_response(raw_content)

    # Ensure all expected keys are present (set to None if model omitted them)
    expected_keys = [
        "customer_name", "complaint_source", "product_name",
        "product_strength_grade", "batch_lot_number",
        "manufacturing_date", "expiry_date", "quantity_affected",
        "complaint_type", "complaint_date", "detailed_description",
    ]
    for key in expected_keys:
        if key not in extracted:
            extracted[key] = None

    return extracted
