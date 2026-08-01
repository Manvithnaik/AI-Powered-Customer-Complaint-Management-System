"""
LangGraph Agent State Definition

The ComplaintState TypedDict is the single source of truth that flows
through every node in the complaint processing graph. Each node receives
the full state and returns a partial dict of keys it modified.

  Flow:
    START
      → extraction_node          (populates extracted_fields)
      → validation_node          (populates validation_passed, validation_warnings)
      → risk_assessment_node     (populates initial_severity, priority, ai_risk_rationale)
      → completeness_check_node  (populates ai_completeness_check)
      → summary_node             (populates ai_complaint_summary)
      → rca_node                 (populates ai_capa_rca)
      → capa_node                (populates ai_capa_recommendation)
      → duplicate_detection_node (populates ai_duplicate_check)
    END
"""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class ComplaintState(TypedDict):
    # ── Input ─────────────────────────────────────────
    raw_text: str                          # Raw complaint text from user
    current_state: Optional[Dict[str, Any]] # Current form draft state (if any)

    # ── Extraction Node Output ─────────────────────────
    extracted_fields: Dict[str, Any]       # Factual fields extracted from text


    # ── Validation Node Output ─────────────────────────
    validation_passed: bool                # True if no blocking logical errors
    validation_warnings: List[str]         # Non-blocking warnings (e.g. suspicious dates)

    # ── Risk Assessment Node Output ────────────────────
    initial_severity: Optional[str]        # Critical | Major | Minor
    priority: Optional[str]               # High | Medium | Low
    ai_risk_rationale: Optional[str]      # QMS reasoning behind the classification

    # ── Completeness Check Node Output ─────────────────
    ai_completeness_check: Optional[Dict[str, Any]]  # {score: int, missing_fields: list}

    # ── Summary Node Output ────────────────────────────
    ai_complaint_summary: Optional[str]              # Executive QA summary paragraph

    # ── Root Cause Recommendation Node Output ──────────
    ai_capa_rca: Optional[Dict[str, Any]]            # {confidence: str, possible_root_causes: list, disclaimer: str}

    # ── CAPA Recommendation Node Output ────────────────
    ai_capa_recommendation: Optional[Dict[str, Any]] # {confidence, corrective_actions[], preventive_actions[], disclaimer}

    # ── Duplicate Detection Node Output ────────────────
    ai_duplicate_check: Optional[Dict[str, Any]]     # {duplicate_found, confidence, recommendation, matches}

    # ── Shared Error Accumulator ───────────────────────
    errors: List[str]                      # Any node can append errors here
